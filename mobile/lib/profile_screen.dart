import 'package:dio/dio.dart';
import 'package:flutter/material.dart';

import 'app_theme.dart';
import 'login_screen.dart';
import 'services/api_service.dart';
import 'widgets/app_empty_state.dart';
import 'widgets/app_error_state.dart';
import 'widgets/app_loading_state.dart';
import 'package:image_picker/image_picker.dart';

class ProfileScreen extends StatefulWidget {
  const ProfileScreen({super.key});

  @override
  State<ProfileScreen> createState() =>
      _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  bool isLoading = true;
  bool isSaving = false;
  bool isLoggingOut = false;
  bool isUploadingAvatar = false;

  String? errorMessage;

  Map<String, dynamic> profile = {};

  bool get isGoogleAccount {
    return profile['auth_provider'] == 'google';
  }

  final fullNameController = TextEditingController();
  final phoneController = TextEditingController();
  final bankNameController = TextEditingController();
  final bankAccountNumberController =
      TextEditingController();
  final bankAccountHolderController =
      TextEditingController();

  @override
  void initState() {
    super.initState();
    loadProfile();
  }

  @override
  void dispose() {
    fullNameController.dispose();
    phoneController.dispose();
    bankNameController.dispose();
    bankAccountNumberController.dispose();
    bankAccountHolderController.dispose();
    super.dispose();
  }

  Future<void> loadProfile() async {
    if (!mounted) return;

    setState(() {
      isLoading = true;
      errorMessage = null;
    });

    try {
      final data = await ApiService.getProfile();

      if (!mounted) return;

      setState(() {
        profile = data;
        isLoading = false;
        errorMessage = null;
      });
    } catch (e) {
      debugPrint(e.toString());

      if (!mounted) return;

      setState(() {
        isLoading = false;
        errorMessage =
            'Không thể tải thông tin tài khoản';
      });
    }
  }

  Future<void> refreshProfile() async {
    await loadProfile();
  }

  Future<void> uploadAvatar() async {
    if (isUploadingAvatar) return;

    try {
      final picker = ImagePicker();

      final image = await picker.pickImage(
        source: ImageSource.gallery,
        maxWidth: 1024,
        maxHeight: 1024,
        imageQuality: 82,
      );

      if (image == null) {
        return;
      }

      final bytes = await image.readAsBytes();

      const maxSize = 2 * 1024 * 1024;

      if (bytes.length > maxSize) {
        showMessage('Ảnh đại diện tối đa 2MB');
        return;
      }

      if (!mounted) return;

      setState(() {
        isUploadingAvatar = true;
      });

      final updated = await ApiService.updateAvatar(
        bytes: bytes,
        fileName: image.name.isNotEmpty ? image.name : 'avatar.jpg',
      );

      if (!mounted) return;

      setState(() {
        profile = updated;
      });

      showMessage('Đã cập nhật ảnh đại diện');
    } catch (e) {
      if (!mounted) return;

      final message = e.toString().trim().isNotEmpty
          ? e.toString()
          : 'Không thể cập nhật ảnh đại diện';

      showMessage(message);
    } finally {
      if (mounted) {
        setState(() {
          isUploadingAvatar = false;
        });
      }
    }
  }

  Future<void> logout() async {
    if (isLoggingOut) return;

    try {
      setState(() {
        isLoggingOut = true;
      });

      await ApiService.logout();

      if (!mounted) return;

      Navigator.pushAndRemoveUntil(
        context,
        MaterialPageRoute(
          builder: (_) => const LoginScreen(),
        ),
        (route) => false,
      );
    } catch (_) {
      showMessage('Không thể đăng xuất');
    } finally {
      if (mounted) {
        setState(() {
          isLoggingOut = false;
        });
      }
    }
  }

  Future<void> openChangePasswordDialog() async {
    final oldPasswordController = TextEditingController();
    final newPasswordController = TextEditingController();
    final confirmPasswordController = TextEditingController();

    bool isChangingPassword = false;

    final result = await showDialog<bool>(
      context: context,
      builder: (dialogContext) {
        return StatefulBuilder(
          builder: (dialogContext, setModalState) {
            Future<void> submit() async {
              final oldPassword = oldPasswordController.text.trim();
              final newPassword = newPasswordController.text.trim();
              final confirmPassword =
                  confirmPasswordController.text.trim();

              void showDialogMessage(String message) {
                ScaffoldMessenger.of(dialogContext)
                  ..hideCurrentSnackBar()
                  ..showSnackBar(
                    SnackBar(
                      content: Text(message),
                      behavior: SnackBarBehavior.floating,
                    ),
                  );
              }

              if (oldPassword.isEmpty ||
                  newPassword.isEmpty ||
                  confirmPassword.isEmpty) {
                showDialogMessage('Vui lòng nhập đầy đủ thông tin');
                return;
              }

              if (newPassword.length < 8) {
                showDialogMessage('Mật khẩu mới tối thiểu 8 ký tự');
                return;
              }

              if (newPassword != confirmPassword) {
                showDialogMessage('Mật khẩu xác nhận không khớp');
                return;
              }

              if (oldPassword == newPassword) {
                showDialogMessage(
                  'Mật khẩu mới phải khác mật khẩu hiện tại',
                );
                return;
              }

              try {
                setModalState(() {
                  isChangingPassword = true;
                });

                await ApiService.changePassword(
                  oldPassword: oldPassword,
                  newPassword: newPassword,
                  confirmPassword: confirmPassword,
                );

                if (!dialogContext.mounted) return;

                Navigator.pop(dialogContext, true);
              } on DioException catch (e) {
                final data = e.response?.data;

                String message = 'Đổi mật khẩu thất bại';

                if (data is Map && data['detail'] != null) {
                  message = data['detail'].toString();
                } else if (data is Map &&
                    data['confirm_password'] != null) {
                  message = data['confirm_password'].toString();
                }

                if (dialogContext.mounted) {
                  showDialogMessage(message);

                  setModalState(() {
                    isChangingPassword = false;
                  });
                }
              } catch (_) {
                if (dialogContext.mounted) {
                  showDialogMessage('Không thể kết nối máy chủ');

                  setModalState(() {
                    isChangingPassword = false;
                  });
                }
              }
            }

            return AlertDialog(
              title: const Text('Đổi mật khẩu'),
              content: SizedBox(
                width: 420,
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    TextField(
                      controller: oldPasswordController,
                      obscureText: true,
                      decoration: const InputDecoration(
                        labelText: 'Mật khẩu hiện tại',
                        prefixIcon: Icon(Icons.lock_outline_rounded),
                      ),
                    ),
                    const SizedBox(height: 14),
                    TextField(
                      controller: newPasswordController,
                      obscureText: true,
                      decoration: const InputDecoration(
                        labelText: 'Mật khẩu mới',
                        prefixIcon: Icon(Icons.lock_reset_rounded),
                      ),
                    ),
                    const SizedBox(height: 14),
                    TextField(
                      controller: confirmPasswordController,
                      obscureText: true,
                      decoration: const InputDecoration(
                        labelText: 'Xác nhận mật khẩu',
                        prefixIcon: Icon(Icons.verified_user_rounded),
                      ),
                    ),
                  ],
                ),
              ),
              actions: [
                TextButton(
                  onPressed: isChangingPassword
                      ? null
                      : () {
                          Navigator.pop(dialogContext, false);
                        },
                  child: const Text('Huỷ'),
                ),
                ElevatedButton(
                  onPressed: isChangingPassword ? null : submit,
                  child: isChangingPassword
                      ? const SizedBox(
                          width: 18,
                          height: 18,
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            color: Colors.white,
                          ),
                        )
                      : const Text('Xác nhận'),
                ),
              ],
            );
          },
        );
      },
    );

    oldPasswordController.dispose();
    newPasswordController.dispose();
    confirmPasswordController.dispose();

    if (result == true && mounted) {
      showMessage('Đổi mật khẩu thành công');
    }
  }

  Future<void> openEditProfile() async {
    fullNameController.text =
        profile['full_name']?.toString() ?? '';
    phoneController.text =
        profile['phone_number']?.toString() ?? '';
    bankNameController.text =
        profile['bank_name']?.toString() ?? '';
    bankAccountNumberController.text =
        profile['bank_account_number']?.toString() ?? '';
    bankAccountHolderController.text =
        profile['bank_account_holder']?.toString() ?? '';

    await showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) {
        return StatefulBuilder(
          builder: (sheetContext, setSheetState) {
            Future<void> saveProfile() async {
              if (isSaving) return;

              final fullName = fullNameController.text.trim();
              final phoneNumber = phoneController.text.trim();
              final bankName = bankNameController.text.trim();
              final bankAccountNumber =
                  bankAccountNumberController.text.trim();
              final bankAccountHolder =
                  bankAccountHolderController.text.trim();

              void showSheetMessage(String message) {
                if (!mounted) return;

                ScaffoldMessenger.of(context)
                  ..hideCurrentSnackBar()
                  ..showSnackBar(
                    SnackBar(
                      content: Text(message),
                      behavior: SnackBarBehavior.floating,
                    ),
                  );
              }

              if (fullName.isEmpty) {
                showSheetMessage('Vui lòng nhập họ và tên');
                return;
              }

              if (fullName.length < 2) {
                showSheetMessage('Họ và tên tối thiểu 2 ký tự');
                return;
              }

              if (phoneNumber.isNotEmpty &&
                  !RegExp(r'^\+?[0-9]{9,15}$').hasMatch(phoneNumber)) {
                showSheetMessage('Số điện thoại không hợp lệ');
                return;
              }

              final hasAnyBankInfo = bankName.isNotEmpty ||
                  bankAccountNumber.isNotEmpty ||
                  bankAccountHolder.isNotEmpty;

              final hasAllBankInfo = bankName.isNotEmpty &&
                  bankAccountNumber.isNotEmpty &&
                  bankAccountHolder.isNotEmpty;

              if (hasAnyBankInfo && !hasAllBankInfo) {
                showSheetMessage(
                  'Vui lòng nhập đầy đủ tên ngân hàng, số tài khoản và chủ tài khoản',
                );
                return;
              }

              if (bankAccountNumber.isNotEmpty &&
                  !RegExp(r'^[0-9]{4,30}$').hasMatch(bankAccountNumber)) {
                showSheetMessage(
                  'Số tài khoản chỉ được chứa chữ số, từ 4 đến 30 ký tự',
                );
                return;
              }

              setSheetState(() {
                isSaving = true;
              });

              try {
                final updated = await ApiService.updateProfile(
                  fullName: fullName,
                  phoneNumber: phoneNumber,
                  bankName: bankName,
                  bankAccountNumber: bankAccountNumber,
                  bankAccountHolder: bankAccountHolder,
                );

                if (!mounted || !sheetContext.mounted) {
                  return;
                }

                setState(() {
                  profile = updated;
                });

                Navigator.pop(sheetContext);
                showMessage('Đã cập nhật hồ sơ');
              } catch (e) {
                if (!mounted) return;

                final message = e.toString().trim().isNotEmpty
                    ? e.toString()
                    : 'Cập nhật thất bại';

                showMessage(message);
              } finally {
                if (sheetContext.mounted) {
                  setSheetState(() {
                    isSaving = false;
                  });
                }
              }
            }

            return Container(
              padding: EdgeInsets.only(
                left: 20,
                right: 20,
                top: 20,
                bottom:
                    MediaQuery.of(sheetContext).viewInsets.bottom +
                        20,
              ),
              decoration: const BoxDecoration(
                color: AppColors.background,
                borderRadius: BorderRadius.vertical(
                  top: Radius.circular(32),
                ),
              ),
              child: SingleChildScrollView(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Container(
                      width: 46,
                      height: 5,
                      decoration: BoxDecoration(
                        color: AppColors.border,
                        borderRadius:
                            BorderRadius.circular(999),
                      ),
                    ),
                    const SizedBox(height: 22),
                    const Text(
                      'Chỉnh sửa hồ sơ',
                      style: TextStyle(
                        fontSize: 22,
                        fontWeight: FontWeight.w900,
                        color: AppColors.textDark,
                      ),
                    ),
                    const SizedBox(height: 22),
                    buildInput(
                      controller: fullNameController,
                      label: 'Họ và tên',
                      icon: Icons.badge_rounded,
                    ),
                    buildInput(
                      controller: phoneController,
                      label: 'Số điện thoại',
                      icon: Icons.phone_rounded,
                      keyboardType: TextInputType.phone,
                    ),
                    buildInput(
                      controller: bankNameController,
                      label: 'Tên ngân hàng',
                      icon: Icons.account_balance_rounded,
                    ),
                    buildInput(
                      controller: bankAccountNumberController,
                      label: 'Số tài khoản',
                      icon: Icons.credit_card_rounded,
                      keyboardType: TextInputType.number,
                    ),
                    buildInput(
                      controller: bankAccountHolderController,
                      label: 'Chủ tài khoản',
                      icon: Icons.person_outline_rounded,
                    ),
                    const SizedBox(height: 12),
                    SizedBox(
                      height: 56,
                      width: double.infinity,
                      child: ElevatedButton(
                        onPressed:
                            isSaving ? null : saveProfile,
                        child: isSaving
                            ? const SizedBox(
                                width: 22,
                                height: 22,
                                child: CircularProgressIndicator(
                                  color: Colors.white,
                                  strokeWidth: 2.4,
                                ),
                              )
                            : const Text('Lưu thay đổi'),
                      ),
                    ),
                  ],
                ),
              ),
            );
          },
        );
      },
    );
  }

  Widget buildInput({
    required TextEditingController controller,
    required String label,
    required IconData icon,
    TextInputType? keyboardType,
  }) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 14),
      child: TextField(
        controller: controller,
        keyboardType: keyboardType,
        decoration: InputDecoration(
          labelText: label,
          prefixIcon: Icon(icon),
        ),
      ),
    );
  }

  void showMessage(String message) {
    if (!mounted) return;

    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;

      ScaffoldMessenger.of(context)
        ..hideCurrentSnackBar()
        ..showSnackBar(
          SnackBar(
            content: Text(message),
            behavior: SnackBarBehavior.floating,
          ),
        );
    });
  }

  String valueOf(String key) {
    final value = profile[key];

    if (value == null || value.toString().trim().isEmpty) {
      return 'Chưa cập nhật';
    }

    return value.toString();
  }

  Widget buildSectionTitle(String title) {
    return Text(
      title,
      style: const TextStyle(
        fontSize: 18,
        fontWeight: FontWeight.w900,
        color: AppColors.textDark,
      ),
    );
  }

  Widget buildInfoTile({
    required IconData icon,
    required String title,
    required String value,
  }) {
    return Container(
      margin: const EdgeInsets.only(bottom: 14),
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(24),
      ),
      child: Row(
        children: [
          Container(
            width: 50,
            height: 50,
            decoration: BoxDecoration(
              color:
                  AppColors.primary.withValues(alpha: 0.10),
              borderRadius: BorderRadius.circular(16),
            ),
            child: Icon(
              icon,
              color: AppColors.primary,
            ),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment:
                  CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: const TextStyle(
                    color: AppColors.textLight,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 6),
                Text(
                  value,
                  style: const TextStyle(
                    color: AppColors.textDark,
                    fontWeight: FontWeight.w800,
                    fontSize: 15,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget buildActionTile({
    required IconData icon,
    required String title,
    required String subtitle,
    required VoidCallback onTap,
  }) {
    return Container(
      margin: const EdgeInsets.only(bottom: 14),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(24),
      ),
      child: ListTile(
        onTap: onTap,
        contentPadding: const EdgeInsets.symmetric(
          horizontal: 18,
          vertical: 8,
        ),
        leading: Container(
          width: 48,
          height: 48,
          decoration: BoxDecoration(
            color: AppColors.primary.withValues(alpha: 0.10),
            borderRadius: BorderRadius.circular(16),
          ),
          child: Icon(
            icon,
            color: AppColors.primary,
          ),
        ),
        title: Text(
          title,
          style: const TextStyle(
            color: AppColors.textDark,
            fontWeight: FontWeight.w900,
          ),
        ),
        subtitle: Text(
          subtitle,
          style: const TextStyle(
            color: AppColors.textLight,
            fontWeight: FontWeight.w600,
          ),
        ),
        trailing: const Icon(
          Icons.chevron_right_rounded,
          color: AppColors.textLight,
        ),
      ),
    );
  }

  Widget buildHeader() {
    final fullName = valueOf('full_name');
    final email = valueOf('email');
    final avatarUrl = ApiService.resolveMediaUrl(
      profile['avatar_url']?.toString(),
    );

    return Container(
      padding: const EdgeInsets.all(28),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [
            AppColors.primary,
            AppColors.secondary,
          ],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(32),
      ),
      child: Column(
        children: [
          Stack(
            clipBehavior: Clip.none,
            children: [
              Container(
                width: 96,
                height: 96,
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: 0.18),
                  shape: BoxShape.circle,
                  border: Border.all(
                    color: Colors.white.withValues(alpha: 0.55),
                    width: 2,
                  ),
                ),
                child: ClipOval(
                  child: avatarUrl.isNotEmpty
                      ? Image.network(
                          avatarUrl,
                          fit: BoxFit.cover,
                          errorBuilder: (_,_, _) {
                            return const Icon(
                              Icons.person_rounded,
                              size: 52,
                              color: Colors.white,
                            );
                          },
                        )
                      : const Icon(
                          Icons.person_rounded,
                          size: 52,
                          color: Colors.white,
                        ),
                ),
              ),
              Positioned(
                right: -2,
                bottom: -2,
                child: GestureDetector(
                  onTap: isUploadingAvatar ? null : uploadAvatar,
                  child: Container(
                    width: 34,
                    height: 34,
                    decoration: BoxDecoration(
                      color: Colors.white,
                      shape: BoxShape.circle,
                      boxShadow: [
                        BoxShadow(
                          color: Colors.black.withValues(alpha: 0.16),
                          blurRadius: 12,
                          offset: const Offset(0, 4),
                        ),
                      ],
                    ),
                    child: isUploadingAvatar
                        ? const Padding(
                            padding: EdgeInsets.all(8),
                            child: CircularProgressIndicator(
                              strokeWidth: 2.2,
                            ),
                          )
                        : const Icon(
                            Icons.camera_alt_rounded,
                            size: 18,
                            color: AppColors.primary,
                          ),
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 20),
          Text(
            fullName == 'Chưa cập nhật'
                ? 'Người dùng Chung Ví'
                : fullName,
            textAlign: TextAlign.center,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 24,
              fontWeight: FontWeight.w900,
              letterSpacing: -0.6,
            ),
          ),
          const SizedBox(height: 10),
          Text(
            email,
            style: const TextStyle(
              color: Colors.white70,
              fontWeight: FontWeight.w600,
              fontSize: 15,
            ),
          ),
          const SizedBox(height: 22),
          SizedBox(
            height: 46,
            child: OutlinedButton.icon(
              onPressed: openEditProfile,
              icon: const Icon(Icons.edit_rounded),
              label: const Text('Chỉnh sửa hồ sơ'),
              style: OutlinedButton.styleFrom(
                foregroundColor: Colors.white,
                side: const BorderSide(
                  color: Colors.white70,
                ),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(18),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget buildLogoutButton() {
    return SizedBox(
      height: 58,
      child: ElevatedButton.icon(
        onPressed: isLoggingOut ? null : logout,
        icon: const Icon(Icons.logout_rounded),
        label: isLoggingOut
            ? const SizedBox(
                width: 18,
                height: 18,
                child: CircularProgressIndicator(
                  strokeWidth: 2.2,
                  color: Colors.white,
                ),
              )
            : const Text(
                'Đăng xuất',
                style: TextStyle(
                  fontWeight: FontWeight.w800,
                ),
              ),
        style: ElevatedButton.styleFrom(
          backgroundColor: Colors.red,
          foregroundColor: Colors.white,
          elevation: 0,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(20),
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (isLoading) {
      return const Scaffold(
        backgroundColor: AppColors.background,
        body: AppLoadingState(
          message: 'Đang tải hồ sơ...',
        ),
      );
    }

    if (errorMessage != null) {
      return Scaffold(
        backgroundColor: AppColors.background,
        body: AppErrorState(
          message: errorMessage!,
          onRetry: loadProfile,
        ),
      );
    }

    if (profile.isEmpty) {
      return Scaffold(
        backgroundColor: AppColors.background,
        body: RefreshIndicator(
          onRefresh: refreshProfile,
          child: ListView(
            physics:
                const AlwaysScrollableScrollPhysics(),
            children: [
              SizedBox(
                height:
                    MediaQuery.of(context).size.height *
                    0.72,
                child: const AppEmptyState(
                  icon: Icons.person_off_rounded,
                  title: 'Không có dữ liệu hồ sơ',
                  message:
                      'Thông tin tài khoản hiện chưa khả dụng.',
                ),
              ),
            ],
          ),
        ),
      );
    }

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        titleSpacing: 20,
        title: const Text('Cá nhân'),
      ),
      body: RefreshIndicator(
        onRefresh: refreshProfile,
        child: ListView(
          physics:
              const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(20),
          children: [
            buildHeader(),
            const SizedBox(height: 28),
            buildSectionTitle('Thông tin cá nhân'),
            const SizedBox(height: 16),
            buildInfoTile(
              icon: Icons.badge_rounded,
              title: 'Họ và tên',
              value: valueOf('full_name'),
            ),
            buildInfoTile(
              icon: Icons.email_rounded,
              title: 'Email',
              value: valueOf('email'),
            ),
            buildInfoTile(
              icon: Icons.phone_rounded,
              title: 'Số điện thoại',
              value: valueOf('phone_number'),
            ),
            const SizedBox(height: 14),
            buildSectionTitle('Tài khoản ngân hàng'),
            const SizedBox(height: 16),
            buildInfoTile(
              icon: Icons.account_balance_rounded,
              title: 'Ngân hàng',
              value: valueOf('bank_name'),
            ),
            buildInfoTile(
              icon: Icons.credit_card_rounded,
              title: 'Số tài khoản',
              value: valueOf('bank_account_number'),
            ),
            buildInfoTile(
              icon: Icons.person_outline_rounded,
              title: 'Chủ tài khoản',
              value: valueOf('bank_account_holder'),
            ),
            const SizedBox(height: 14),
            if (!isGoogleAccount) ...[
              const SizedBox(height: 14),
              buildSectionTitle('Bảo mật'),
              const SizedBox(height: 16),
              buildActionTile(
                icon: Icons.lock_reset_rounded,
                title: 'Đổi mật khẩu',
                subtitle:
                    'Cập nhật mật khẩu đăng nhập tài khoản',
                onTap: openChangePasswordDialog,
              ),
            ],
            const SizedBox(height: 14),
            buildLogoutButton(),
            const SizedBox(height: 120),
          ],
        ),
      ),
    );
  }
}