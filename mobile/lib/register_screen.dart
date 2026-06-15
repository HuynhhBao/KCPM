import 'package:dio/dio.dart';
import 'package:flutter/material.dart';

import 'app_theme.dart';
import 'login_screen.dart';
import 'services/api_service.dart';
import 'verify_register_otp_screen.dart';

class RegisterScreen extends StatefulWidget {
  const RegisterScreen({super.key});

  @override
  State<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends State<RegisterScreen> {
  final emailController = TextEditingController();
  final passwordController = TextEditingController();
  final confirmPasswordController = TextEditingController();

  bool isLoading = false;
  bool hidePassword = true;
  bool hideConfirmPassword = true;

  @override
  void dispose() {
    emailController.dispose();
    passwordController.dispose();
    confirmPasswordController.dispose();
    super.dispose();
  }

  bool isValidEmail(String email) {
    return RegExp(r'^[\w\.-]+@([\w-]+\.)+[\w-]{2,4}$').hasMatch(email);
  }

  Future<void> register() async {
    final email = emailController.text.trim().toLowerCase();
    final password = passwordController.text.trim();
    final confirmPassword = confirmPasswordController.text.trim();

    if (email.isEmpty || password.isEmpty || confirmPassword.isEmpty) {
      showMessage('Vui lòng nhập đầy đủ thông tin');
      return;
    }

    if (!isValidEmail(email)) {
      showMessage('Email không hợp lệ');
      return;
    }

    if (password.length < 8) {
      showMessage('Mật khẩu phải có ít nhất 8 ký tự');
      return;
    }

    if (password != confirmPassword) {
      showMessage('Mật khẩu xác nhận không khớp');
      return;
    }

    try {
      setState(() {
        isLoading = true;
      });

      await ApiService.register(
        email: email,
        username: email,
        password: password,
      );

      if (!mounted) return;

      showMessage('Đăng ký thành công. Vui lòng nhập OTP.');

      Navigator.pushReplacement(
        context,
        MaterialPageRoute(
          builder: (_) => VerifyRegisterOTPScreen(email: email),
        ),
      );
    } on DioException catch (e) {
      debugPrint('REGISTER ERROR: ${e.response?.data}');

      final data = e.response?.data;

      if (data is Map) {
        if (data['detail'] != null) {
          showMessage(data['detail'].toString());
        } else if (data['email'] != null) {
          final emailError = data['email'];

          if (emailError is List && emailError.isNotEmpty) {
            showMessage(emailError.first.toString());
          } else {
            showMessage(emailError.toString());
          }
        } else {
          final firstError = data.values.isNotEmpty
              ? data.values.first.toString()
              : 'Đăng ký thất bại';

          showMessage(firstError);
        }
      } else {
        showMessage('Đăng ký thất bại');
      }
    } catch (e) {
      debugPrint('REGISTER ERROR: $e');

      showMessage('Không thể kết nối máy chủ');
    } finally {
      if (mounted) {
        setState(() {
          isLoading = false;
        });
      }
    }
  }

  void showMessage(String message) {
    if (!mounted) return;

    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(
        SnackBar(content: Text(message), behavior: SnackBarBehavior.floating),
      );
  }

  Widget buildInput({
    required String label,
    required String hint,
    required IconData icon,
    required TextEditingController controller,
    bool obscure = false,
    Widget? suffixIcon,
    TextInputType? keyboardType,
    TextInputAction? textInputAction,
    void Function(String)? onSubmitted,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: const TextStyle(
            color: AppColors.textDark,
            fontSize: 15,
            fontWeight: FontWeight.w900,
          ),
        ),
        const SizedBox(height: 8),
        SizedBox(
          height: 54,
          child: TextField(
            controller: controller,
            obscureText: obscure,
            keyboardType: keyboardType,
            textInputAction: textInputAction,
            onSubmitted: onSubmitted,
            style: const TextStyle(
              fontSize: 15,
              fontWeight: FontWeight.w700,
              color: AppColors.textDark,
            ),
            decoration: InputDecoration(
              hintText: hint,
              filled: true,
              fillColor: const Color(0xFFF7FAFA),
              prefixIcon: Icon(icon, color: AppColors.textLight, size: 21),
              suffixIcon: suffixIcon,
              contentPadding: const EdgeInsets.symmetric(
                horizontal: 16,
                vertical: 14,
              ),
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(19),
                borderSide: const BorderSide(color: Color(0xFFDDE7EA)),
              ),
              enabledBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(19),
                borderSide: const BorderSide(color: Color(0xFFDDE7EA)),
              ),
              focusedBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(19),
                borderSide: const BorderSide(
                  color: AppColors.primary,
                  width: 1.5,
                ),
              ),
            ),
          ),
        ),
      ],
    );
  }

  Widget buildRegisterButton() {
    return SizedBox(
      width: double.infinity,
      height: 56,
      child: ElevatedButton(
        onPressed: isLoading ? null : register,
        style: ElevatedButton.styleFrom(
          elevation: 0,
          backgroundColor: AppColors.primary,
          foregroundColor: Colors.white,
          disabledBackgroundColor: AppColors.primary.withValues(alpha: 0.35),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(20),
          ),
        ),
        child: isLoading
            ? const SizedBox(
                width: 22,
                height: 22,
                child: CircularProgressIndicator(
                  strokeWidth: 2.5,
                  color: Colors.white,
                ),
              )
            : const Text(
                'Tạo tài khoản',
                style: TextStyle(fontSize: 17, fontWeight: FontWeight.w900),
              ),
      ),
    );
  }

  Widget buildBottomText() {
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        const Text(
          'Đã có tài khoản?',
          style: TextStyle(
            color: AppColors.textLight,
            fontWeight: FontWeight.w600,
          ),
        ),
        TextButton(
          onPressed: () {
            Navigator.pushReplacement(
              context,
              MaterialPageRoute(builder: (_) => const LoginScreen()),
            );
          },
          child: const Text(
            'Đăng nhập',
            style: TextStyle(
              color: AppColors.primary,
              fontWeight: FontWeight.w900,
            ),
          ),
        ),
      ],
    );
  }

  Widget buildLogoHeader(bool compact) {
    final logoSize = compact ? 70.0 : 84.0;

    return Column(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        Container(
          width: logoSize,
          height: logoSize,
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(26),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: 0.20),
                blurRadius: 30,
                offset: const Offset(0, 14),
              ),
            ],
          ),
          child: ClipRRect(
            borderRadius: BorderRadius.circular(26),
            child: Image.asset('assets/images/logo.jpg', fit: BoxFit.cover),
          ),
        ),
        SizedBox(height: compact ? 12 : 16),
        const Text(
          'Chung Ví',
          style: TextStyle(
            color: Colors.white,
            fontSize: 34,
            fontWeight: FontWeight.w900,
            letterSpacing: -0.8,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          'Chia tiền nhóm dễ dàng hơn',
          style: TextStyle(
            color: Colors.white.withValues(alpha: 0.76),
            fontSize: 15,
            fontWeight: FontWeight.w600,
          ),
        ),
      ],
    );
  }

  Widget buildRegisterCard(bool compact) {
    return Container(
      width: double.infinity,
      padding: EdgeInsets.fromLTRB(24, compact ? 24 : 30, 24, 18),
      decoration: const BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.vertical(top: Radius.circular(34)),
      ),
      child: SingleChildScrollView(
        physics: const BouncingScrollPhysics(),
        child: Column(
          children: [
            SizedBox(height: compact ? 12 : 16),
            const Text(
              'Tạo tài khoản',
              style: TextStyle(
                fontSize: 28,
                fontWeight: FontWeight.w900,
                color: AppColors.textDark,
                letterSpacing: -0.5,
              ),
            ),
            SizedBox(height: compact ? 12 : 16),
            buildInput(
              label: 'Email',
              hint: 'Nhập email của bạn',
              icon: Icons.mail_outline_rounded,
              controller: emailController,
              keyboardType: TextInputType.emailAddress,
              textInputAction: TextInputAction.next,
            ),
            SizedBox(height: compact ? 12 : 16),
            buildInput(
              label: 'Mật khẩu',
              hint: 'Nhập mật khẩu',
              icon: Icons.lock_outline_rounded,
              controller: passwordController,
              obscure: hidePassword,
              textInputAction: TextInputAction.next,
              suffixIcon: IconButton(
                onPressed: () {
                  setState(() {
                    hidePassword = !hidePassword;
                  });
                },
                icon: Icon(
                  hidePassword
                      ? Icons.visibility_off_outlined
                      : Icons.visibility_outlined,
                  color: AppColors.textLight,
                ),
              ),
            ),
            SizedBox(height: compact ? 12 : 16),
            buildInput(
              label: 'Xác nhận mật khẩu',
              hint: 'Nhập lại mật khẩu',
              icon: Icons.lock_reset_rounded,
              controller: confirmPasswordController,
              obscure: hideConfirmPassword,
              textInputAction: TextInputAction.done,
              onSubmitted: (_) => register(),
              suffixIcon: IconButton(
                onPressed: () {
                  setState(() {
                    hideConfirmPassword = !hideConfirmPassword;
                  });
                },
                icon: Icon(
                  hideConfirmPassword
                      ? Icons.visibility_off_outlined
                      : Icons.visibility_outlined,
                  color: AppColors.textLight,
                ),
              ),
            ),
            SizedBox(height: compact ? 22 : 28),
            buildRegisterButton(),
            SizedBox(height: compact ? 16 : 20),
            buildBottomText(),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final isMobile = MediaQuery.of(context).size.width < 600;

    return Scaffold(
      resizeToAvoidBottomInset: true,
      backgroundColor: AppColors.primaryDark,
      body: GestureDetector(
        onTap: () => FocusScope.of(context).unfocus(),
        child: Container(
          decoration: const BoxDecoration(
            gradient: LinearGradient(
              colors: [
                AppColors.primaryLight,
                AppColors.primary,
                AppColors.primaryDark,
              ],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
          ),
          child: SafeArea(
            bottom: false,
            child: LayoutBuilder(
              builder: (context, constraints) {
                final compact = constraints.maxHeight < 760;

                return AnimatedPadding(
                  duration: const Duration(milliseconds: 250),
                  curve: Curves.easeOut,
                  padding: EdgeInsets.only(
                    bottom: MediaQuery.of(context).viewInsets.bottom * 0.45,
                  ),
                  child: Center(
                    child: ConstrainedBox(
                      constraints: const BoxConstraints(maxWidth: 520),
                      child: Column(
                        children: [
                          Expanded(
                            flex: compact ? 30 : 34,
                            child: buildLogoHeader(compact),
                          ),
                          Expanded(
                            flex: compact ? 70 : 66,
                            child: buildRegisterCard(isMobile),
                          ),
                        ],
                      ),
                    ),
                  ),
                );
              },
            ),
          ),
        ),
      ),
    );
  }
}
