import 'package:flutter/material.dart';

import 'add_expense_screen.dart';
import 'app_theme.dart';
import 'models/debt.dart';
import 'models/expense.dart';
import 'models/household.dart';
import 'services/api_service.dart';
import 'package:url_launcher/url_launcher.dart';
import 'widgets/app_empty_state.dart';
import 'widgets/app_error_state.dart';
import 'widgets/app_loading_state.dart';
import 'package:flutter/services.dart';
import 'household_members_screen.dart';

class HouseholdDetailScreen extends StatefulWidget {
  final Household household;

  const HouseholdDetailScreen({
    super.key,
    required this.household,
  });

  @override
  State<HouseholdDetailScreen> createState() =>
      _HouseholdDetailScreenState();
}

class _HouseholdDetailScreenState extends State<HouseholdDetailScreen> {
  late Household household;

  bool isLoading = true;
  bool isAddingMember = false;
  bool isLeavingHousehold = false;
  bool isDeletingHousehold = false;
  bool isKickingMember = false;
  String? kickingMemberId;
  String? editingExpenseId;
  String? deletingExpenseId;
  String? errorMessage;

  List<Expense> expenses = [];
  List<Debt> debts = [];

  Map<String, dynamic>? myDebtSummary;
  bool isLoadingDebtDetail = false;
  int? loadingDebtDetailUserId;

  Map<String, dynamic>? virtualDebtSummary;
  int? selectedVirtualUserId;
  bool isLoadingVirtualDebt = false;
  bool isLoadingVirtualDebtDetail = false;
  bool isSettlingVirtualDebt = false;
  int? loadingVirtualDebtDetailUserId;

  double totalExpense = 0;

  String currentUserEmail = '';

  final ScrollController scrollController =
      ScrollController();

  int expensePage = 1;
  bool hasMoreExpenses = true;
  bool isLoadingMoreExpenses = false;
  bool isExpensePageError = false;

  @override
  void initState() {
    super.initState();

    household = widget.household;

    scrollController.addListener(() {
      if (scrollController.position.pixels >=
          scrollController.position.maxScrollExtent - 300) {
        loadMoreExpenses();
      }
    });

    loadData();
  }

  @override
  void dispose() {
    scrollController.dispose();
    super.dispose();
  }

  bool get isCurrentUserOwner {
    return household.members.any(
      (member) =>
          member.role == 'owner' &&
          member.userEmail.trim().toLowerCase() ==
              currentUserEmail,
    );
  }

  bool isVirtualMember(dynamic member) {
    final email = getMemberEmail(member)
        .trim()
        .toLowerCase();

    return email.endsWith('@virtual.chungvi.local');
  }

  int getMemberUserId(dynamic member) {
    try {
      final value = member.user;

      if (value is int) return value;

      return int.tryParse(value.toString()) ?? 0;
    } catch (_) {}

    try {
      final value = member.userId;

      if (value is int) return value;

      return int.tryParse(value.toString()) ?? 0;
    } catch (_) {}

    return 0;
  }

  List<dynamic> get virtualMembers {
    return household.members
        .where((member) => isVirtualMember(member))
        .toList();
  }

  dynamic get selectedVirtualMember {
    if (selectedVirtualUserId == null) {
      return null;
    }

    for (final member in virtualMembers) {
      if (getMemberUserId(member) == selectedVirtualUserId) {
        return member;
      }
    }

    return null;
  }

  Future<void> loadData() async {
    if (!mounted) return;

    setState(() {
      isLoading = true;
      errorMessage = null;
    });

    try {
      final savedEmail = await ApiService.getSavedEmail();

      if (savedEmail != null && savedEmail.isNotEmpty) {
        currentUserEmail =
            savedEmail.trim().toLowerCase();
      } else {
        final profile = await ApiService.getProfile();

        currentUserEmail = profile['email']
                ?.toString()
                .trim()
                .toLowerCase() ??
            '';
      }

      final householdData =
          await ApiService.getHouseholdDetail(
        household.id,
      );

      final freshHousehold =
          Household.fromJson(householdData);

      final expenseResponse =
          await ApiService.getHouseholdExpenses(
        household.id,
        page: 1,
      );

      final debtSummary =
          await ApiService.getHouseholdMyDebtSummary(
        household.id,
      );

      final loadedExpenses = List<dynamic>.from(
        expenseResponse['results'],
      ).map<Expense>(
        (json) => Expense.fromJson(
          Map<String, dynamic>.from(json),
        ),
      ).toList();

      ///final loadedDebts = List<dynamic>.from(
        ///debtResponse['results'],
      ///).map<Debt>(
        ///(json) => Debt.fromJson(
          ///Map<String, dynamic>.from(json),
        ///),
      ///).toList();

      double total = 0;

      for (final expense in loadedExpenses) {
        total += expense.amount;
      }

      if (!mounted) return;

      setState(() {
        household = freshHousehold;

        expenses = loadedExpenses;
        myDebtSummary = debtSummary;
        debts = [];
        totalExpense = total;

        expensePage = 1;
        hasMoreExpenses = expenseResponse['next'] != null;
        isLoadingMoreExpenses = false;
        isExpensePageError = false;

        isLoading = false;
        errorMessage = null;
      });

      await loadVirtualMemberDebtSummary();
    } catch (e) {
      debugPrint(e.toString());

      if (!mounted) return;

      setState(() {
        errorMessage = 'Không thể tải dữ liệu nhóm';
        isLoading = false;
      });
    }
  }

  Future<void> refreshData() async {
    await loadData();
  }

  Future<void> loadVirtualMemberDebtSummary() async {
    if (!mounted) return;

    if (!isCurrentUserOwner || virtualMembers.isEmpty) {
      setState(() {
        virtualDebtSummary = null;
        selectedVirtualUserId = null;
        isLoadingVirtualDebt = false;
      });

      return;
    }

    int targetUserId = selectedVirtualUserId ??
        getMemberUserId(virtualMembers.first);

    final exists = virtualMembers.any(
      (member) => getMemberUserId(member) == targetUserId,
    );

    if (!exists) {
      targetUserId = getMemberUserId(virtualMembers.first);
    }

    if (targetUserId <= 0) {
      setState(() {
        virtualDebtSummary = null;
        selectedVirtualUserId = null;
        isLoadingVirtualDebt = false;
      });

      return;
    }

    setState(() {
      selectedVirtualUserId = targetUserId;
      isLoadingVirtualDebt = true;
    });

    try {
      final response = await ApiService.getVirtualMemberDebts(
        householdId: household.id,
        virtualUserId: targetUserId,
      );

      if (!mounted) return;

      setState(() {
        virtualDebtSummary = response;
        isLoadingVirtualDebt = false;
      });
    } catch (e) {
      if (!mounted) return;

      setState(() {
        isLoadingVirtualDebt = false;
      });

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(e.toString()),
        ),
      );
    }
  }

  Future<void> loadMoreExpenses() async {
    if (isLoadingMoreExpenses ||
        !hasMoreExpenses ||
        isLoading ||
        isExpensePageError) {
      return;
    }

    setState(() {
      isLoadingMoreExpenses = true;
      isExpensePageError = false;
    });

    try {
      final nextPage = expensePage + 1;

      final response =
          await ApiService.getHouseholdExpenses(
        household.id,
        page: nextPage,
      );

      final newExpenses = List<dynamic>.from(
        response['results'],
      ).map<Expense>(
        (json) => Expense.fromJson(
          Map<String, dynamic>.from(json),
        ),
      ).toList();

      double addedTotal = 0;

      for (final expense in newExpenses) {
        addedTotal += expense.amount;
      }

      if (!mounted) return;

      setState(() {
        expensePage = nextPage;
        expenses.addAll(newExpenses);
        totalExpense += addedTotal;
        hasMoreExpenses = response['next'] != null;
        isLoadingMoreExpenses = false;
      });
    } catch (e) {
      debugPrint(e.toString());

      if (!mounted) return;

      setState(() {
        isLoadingMoreExpenses = false;
        isExpensePageError = true;
      });
    }
  }

  Future<void> openAddExpenseScreen() async {
    final result = await Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => AddExpenseScreen(
          household: household,
        ),
      ),
    );

    if (result == true) {
      await loadData();
    }
  }

  Future<void> openEditExpenseScreen(
    Expense expense,
  ) async {
    if (editingExpenseId != null ||
        deletingExpenseId != null) {
      return;
    }

    if (!expense.canManage) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text(
            'Bạn không có quyền sửa khoản chi này',
          ),
        ),
      );
      return;
    }

    setState(() {
      editingExpenseId = expense.id;
    });

    try {
      final expenseData =
          await ApiService.getExpenseDetail(
        expense.id,
      );

      if (!mounted) return;

      final detailExpense = Expense.fromJson(
        Map<String, dynamic>.from(expenseData),
      );

      final result = await Navigator.push(
        context,
        MaterialPageRoute(
          builder: (_) => AddExpenseScreen(
            household: household,
            expense: detailExpense,
          ),
        ),
      );

      if (result == true) {
        await loadData();
      }
    } catch (e) {
      if (!mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(e.toString()),
        ),
      );
    } finally {
      if (mounted) {
        setState(() {
          editingExpenseId = null;
        });
      }
    }
  }

  Future<void> confirmDeleteExpense(
    Expense expense,
  ) async {
    if (deletingExpenseId != null ||
        editingExpenseId != null) {
      return;
    }

    if (!expense.canManage) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text(
            'Bạn không có quyền xóa khoản chi này',
          ),
        ),
      );
      return;
    }

    final confirmed = await showDialog<bool>(
      context: context,
      barrierDismissible: deletingExpenseId == null,
      builder: (dialogContext) {
        return AlertDialog(
          title: const Text('Xóa khoản chi?'),
          content: Text(
            'Bạn có chắc muốn xóa khoản "${expense.title}" không?\n\n'
            'Hành động này sẽ xóa công nợ liên quan đến khoản chi.',
          ),
          actions: [
            TextButton(
              onPressed: () {
                Navigator.pop(dialogContext, false);
              },
              child: const Text('Hủy'),
            ),
            ElevatedButton(
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.red,
              ),
              onPressed: () {
                Navigator.pop(dialogContext, true);
              },
              child: const Text('Xóa'),
            ),
          ],
        );
      },
    );

    if (confirmed != true) return;

    setState(() {
      deletingExpenseId = expense.id;
    });

    try {
      await ApiService.deleteExpense(
        expense.id,
      );

      if (!mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Đã xóa khoản chi'),
        ),
      );

      await loadData();
    } catch (e) {
      if (!mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(e.toString()),
        ),
      );
    } finally {
      if (mounted) {
        setState(() {
          deletingExpenseId = null;
        });
      }
    }
  }

  Future<void> showAddMemberDialog() async {
    if (!isCurrentUserOwner) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Chỉ chủ nhóm mới được thêm thành viên'),
        ),
      );
      return;
    }

    final controller = TextEditingController();

    await showDialog(
      context: context,
      barrierDismissible: !isAddingMember,
      builder: (dialogContext) {
        return StatefulBuilder(
          builder: (dialogContext, setDialogState) {
            Future<void> submit() async {
              if (isAddingMember) return;

              final email = controller.text.trim().toLowerCase();

              if (email.isEmpty) {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(
                    content: Text('Nhập email thành viên'),
                  ),
                );
                return;
              }

              if (!email.contains('@')) {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(
                    content: Text('Email không hợp lệ'),
                  ),
                );
                return;
              }

              setDialogState(() => isAddingMember = true);

              try {
                await ApiService.addMemberToHousehold(
                  householdId: household.id,
                  email: email,
                );

                if (!mounted || !dialogContext.mounted) return;

                Navigator.pop(dialogContext);

                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(
                    content: Text('Đã thêm thành viên'),
                  ),
                );

                await loadData();
              } catch (e) {
                if (!mounted) return;

                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(
                    content: Text(e.toString()),
                  ),
                );
              } finally {
                if (mounted) {
                  setDialogState(() => isAddingMember = false);
                }
              }
            }

            return AlertDialog(
              title: const Text('Thêm thành viên'),
              content: TextField(
                controller: controller,
                enabled: !isAddingMember,
                keyboardType: TextInputType.emailAddress,
                textInputAction: TextInputAction.done,
                onSubmitted: (_) => submit(),
                decoration: const InputDecoration(
                  hintText: 'Nhập email...',
                ),
              ),
              actions: [
                TextButton(
                  onPressed: isAddingMember
                      ? null
                      : () {
                          Navigator.pop(dialogContext);
                        },
                  child: const Text('Hủy'),
                ),
                ElevatedButton(
                  onPressed: isAddingMember ? null : submit,
                  child: isAddingMember
                      ? const SizedBox(
                          width: 18,
                          height: 18,
                          child: CircularProgressIndicator(
                            strokeWidth: 2.2,
                            color: Colors.white,
                          ),
                        )
                      : const Text('Thêm'),
                ),
              ],
            );
          },
        );
      },
    );

    controller.dispose();
  }

  Future<void> openMembersScreen() async {
    await Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => HouseholdMembersScreen(
          household: household,
          currentUserEmail: currentUserEmail,
          onHouseholdUpdated: (updatedHousehold) {
            setState(() {
              household = updatedHousehold;
            });
          },
        ),
      ),
    );

    await loadData();
  }

  Future<void> confirmLeaveHousehold() async {
    if (isLeavingHousehold) return;

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) {
        return AlertDialog(
          title: const Text('Rời nhóm?'),
          content: const Text(
            'Bạn sẽ không còn xem được khoản chi và công nợ của nhóm này.',
          ),
          actions: [
            TextButton(
              onPressed: () {
                Navigator.pop(dialogContext, false);
              },
              child: const Text('Hủy'),
            ),
            ElevatedButton(
              onPressed: () {
                Navigator.pop(dialogContext, true);
              },
              child: const Text('Rời nhóm'),
            ),
          ],
        );
      },
    );

    if (confirmed != true) return;

    setState(() {
      isLeavingHousehold = true;
    });

    try {
      await ApiService.leaveHousehold(household.id);

      if (!mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Bạn đã rời nhóm'),
        ),
      );

      Navigator.pop(context, true);
    } catch (e) {
      if (!mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(e.toString()),
        ),
      );
    } finally {
        if (mounted) {
          setState(() {
            isLeavingHousehold = false;
          });
        }
      }
    }

  Future<void> confirmDeleteHousehold() async {
    if (isDeletingHousehold) return;

    if (!isCurrentUserOwner) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Chỉ chủ nhóm mới được xóa nhóm'),
        ),
      );
      return;
    }

    final confirmed = await showDialog<bool>(
      context: context,
      barrierDismissible: !isDeletingHousehold,
      builder: (dialogContext) {
        return AlertDialog(
          title: const Text('Xóa nhóm?'),
          content: Text(
            'Nhóm "${household.name}" sẽ bị xóa khỏi danh sách nhóm của bạn. '
            'Bạn chỉ nên xóa nhóm khi toàn bộ công nợ đã được xử lý.',
          ),
          actions: [
            TextButton(
              onPressed: () {
                Navigator.pop(dialogContext, false);
              },
              child: const Text('Hủy'),
            ),
            ElevatedButton(
              style: ElevatedButton.styleFrom(
                backgroundColor: AppColors.danger,
                foregroundColor: Colors.white,
              ),
              onPressed: () {
                Navigator.pop(dialogContext, true);
              },
              child: const Text('Xóa nhóm'),
            ),
          ],
        );
      },
    );

    if (confirmed != true) return;

    setState(() {
      isDeletingHousehold = true;
    });

    try {
      await ApiService.deleteHousehold(household.id);

      if (!mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Đã xóa nhóm'),
        ),
      );

      Navigator.pop(context, true);
    } catch (e) {
      if (!mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(e.toString()),
        ),
      );
    } finally {
      if (mounted) {
        setState(() {
          isDeletingHousehold = false;
        });
      }
    }
  }

  Future<void> confirmKickMember(dynamic member) async {
    if (isKickingMember) return;

    final memberId = getMemberId(member);
    final memberName = getMemberName(member);
    final memberEmail = getMemberEmail(member);

    if (memberId.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Không tìm thấy ID thành viên'),
        ),
      );
      return;
    }

    if (!canKickMember(member)) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Không thể xóa thành viên này'),
        ),
      );
      return;
    }

    final confirmed = await showDialog<bool>(
      context: context,
      barrierDismissible: !isKickingMember,
      builder: (dialogContext) {
        return AlertDialog(
          title: const Text('Xóa thành viên?'),
          content: Text(
            'Bạn có chắc muốn xóa $memberName khỏi nhóm?\n\n'
            'Email: $memberEmail\n\n'
            'Thành viên còn công nợ chưa thanh toán sẽ không thể bị xóa.',
          ),
          actions: [
            TextButton(
              onPressed: () {
                Navigator.pop(dialogContext, false);
              },
              child: const Text('Hủy'),
            ),
            ElevatedButton(
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.red,
              ),
              onPressed: () {
                Navigator.pop(dialogContext, true);
              },
              child: const Text('Xóa'),
            ),
          ],
        );
      },
    );

    if (confirmed != true) return;

    setState(() {
      isKickingMember = true;
      kickingMemberId = memberId;
    });

    try {
      final response =
          await ApiService.kickMemberFromHousehold(
        householdId: household.id,
        memberId: memberId,
      );

      if (!mounted) return;

      final householdData = Map<String, dynamic>.from(
        response['household'],
      );

      setState(() {
        household = Household.fromJson(householdData);
      });

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Đã xóa thành viên khỏi nhóm'),
        ),
      );
    } catch (e) {
      if (!mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(e.toString()),
        ),
      );
    } finally {
      if (mounted) {
        setState(() {
          isKickingMember = false;
          kickingMemberId = null;
        });
      }
    }
  }

  String formatMoney(double amount) {
    return amount.toStringAsFixed(0).replaceAllMapped(
          RegExp(r'\B(?=(\d{3})+(?!\d))'),
          (match) => '.',
        );
  }

  double readDouble(dynamic value) {
    if (value == null) return 0;

    if (value is num) {
      return value.toDouble();
    }

    return double.tryParse(value.toString()) ?? 0;
  }

  int readInt(dynamic value) {
    if (value == null) return 0;

    if (value is int) return value;

    return int.tryParse(value.toString()) ?? 0;
  }

  List<Map<String, dynamic>> readMapList(dynamic value) {
    if (value is! List) return [];

    return value
        .whereType<Map>()
        .map(
          (item) => Map<String, dynamic>.from(item),
        )
        .toList();
  }

  String readDebtUserName(Map<String, dynamic> item) {
    final name = item['other_name']?.toString() ?? '';
    final email = item['other_email']?.toString() ?? '';

    if (name.trim().isNotEmpty) return name;

    if (email.trim().isNotEmpty) return email;

    return 'Thành viên';
  }

  String displayUserName({
    required String name,
    required String email,
  }) {
    final normalizedEmail = email.trim().toLowerCase();

    if (normalizedEmail.isNotEmpty &&
        normalizedEmail == currentUserEmail) {
      return 'Bạn';
    }

    if (name.trim().isNotEmpty) {
      return name;
    }

    return email;
  }

  Widget buildAvatar({
    required String imageUrl,
    required String name,
    double radius = 24,
  }) {
    if (imageUrl.isNotEmpty) {
      return CircleAvatar(
        radius: radius,
        backgroundImage: NetworkImage(imageUrl),
        backgroundColor: Colors.grey.shade200,
      );
    }

    return CircleAvatar(
      radius: radius,
      backgroundColor: AppColors.primary,
      child: Text(
        name.isNotEmpty
            ? name[0].toUpperCase()
            : '?',
        style: TextStyle(
          color: Colors.white,
          fontWeight: FontWeight.w800,
          fontSize: radius * 0.8,
        ),
      ),
    );
  }

  Future<void> openTransferQR(Debt debt) async {
    if (debt.bankName.isEmpty ||
        debt.bankAccountNumber.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text(
            'Người nhận chưa cập nhật tài khoản ngân hàng',
          ),
        ),
      );

      return;
    }

    final amount = debt.amount.toInt();

    final encodedMessage = Uri.encodeComponent(
      'Thanh toan Chung Vi',
    );

    final encodedAccountName = Uri.encodeComponent(
      debt.bankAccountHolder,
    );

    final url =
        'https://img.vietqr.io/image/'
        '${debt.bankName}-${debt.bankAccountNumber}-compact2.png'
        '?amount=$amount'
        '&addInfo=$encodedMessage'
        '&accountName=$encodedAccountName';

    final uri = Uri.parse(url);

    try {
      final launched = await launchUrl(
        uri,
        mode: LaunchMode.externalApplication,
      );

      if (!launched && mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text(
              'Không thể mở QR chuyển khoản',
            ),
          ),
        );
      }
    } catch (e) {
      if (!mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text(
            'Đã xảy ra lỗi khi mở QR',
          ),
        ),
      );
    }
  }

  String getMemberId(dynamic member) {
    try {
      final value = member.id;

      if (value != null && value.toString().isNotEmpty) {
        return value.toString();
      }
    } catch (_) {}

    return '';
  }

  String getMemberEmail(dynamic member) {
    try {
      final value = member.email;
      if (value != null && value.toString().isNotEmpty) {
        return value.toString();
      }
    } catch (_) {}

    try {
      final value = member.userEmail;
      if (value != null && value.toString().isNotEmpty) {
        return value.toString();
      }
    } catch (_) {}

    try {
      final value = member.user_email;
      if (value != null && value.toString().isNotEmpty) {
        return value.toString();
      }
    } catch (_) {}

    return '';
  }

  String getMemberName(dynamic member) {
    try {
      final value = member.fullName;
      if (value != null && value.toString().isNotEmpty) {
        return value.toString();
      }
    } catch (_) {}

    try {
      final value = member.userFullName;
      if (value != null && value.toString().isNotEmpty) {
        return value.toString();
      }
    } catch (_) {}

    final email = getMemberEmail(member);

    if (email.isNotEmpty) {
      return email;
    }

    return 'Thành viên';
  }

  bool canKickMember(dynamic member) {
    if (!isCurrentUserOwner) return false;

    final email = getMemberEmail(member)
        .trim()
        .toLowerCase();

    final role = member.role
        .toString()
        .trim()
        .toLowerCase();

    if (email == currentUserEmail) return false;

    if (role == 'owner') return false;

    return true;
  }

  Widget buildHeroCard() {
    return Container(
      padding: const EdgeInsets.all(24),
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
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 58,
                height: 58,
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: 0.16),
                  borderRadius: BorderRadius.circular(18),
                ),
                child: const Icon(
                  Icons.groups_rounded,
                  color: Colors.white,
                  size: 30,
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      crossAxisAlignment:
                          CrossAxisAlignment.start,
                      children: [
                        Expanded(
                          child: Text(
                            household.name,
                            style: const TextStyle(
                              color: Colors.white,
                              fontSize: 26,
                              fontWeight: FontWeight.w900,
                              letterSpacing: -0.7,
                            ),
                          ),
                        ),

                        const SizedBox(width: 12),

                        InkWell(
                          borderRadius:
                              BorderRadius.circular(999),
                          onTap: () async {
                            await Clipboard.setData(
                              ClipboardData(
                                text:
                                    household.inviteCode,
                              ),
                            );

                            if (!mounted) return;

                            ScaffoldMessenger.of(context)
                                .showSnackBar(
                              const SnackBar(
                                content: Text(
                                  'Đã copy mã mời',
                                ),
                              ),
                            );
                          },
                          child: Container(
                            padding:
                                const EdgeInsets.symmetric(
                              horizontal: 12,
                              vertical: 8,
                            ),
                            decoration: BoxDecoration(
                              color: Colors.white.withValues(
                                alpha: 0.16,
                              ),
                              borderRadius:
                                  BorderRadius.circular(999),
                              border: Border.all(
                                color: Colors.white.withValues(
                                  alpha: 0.12,
                                ),
                              ),
                            ),
                            child: Row(
                              mainAxisSize:
                                  MainAxisSize.min,
                              children: [
                                const Icon(
                                  Icons.key_rounded,
                                  color: Colors.white,
                                  size: 14,
                                ),

                                const SizedBox(width: 6),

                                Text(
                                  household.inviteCode,
                                  style: const TextStyle(
                                    color: Colors.white,
                                    fontSize: 13,
                                    fontWeight:
                                        FontWeight.w800,
                                    letterSpacing: 0.5,
                                  ),
                                ),

                                const SizedBox(width: 6),

                                const Icon(
                                  Icons.copy_rounded,
                                  color: Colors.white70,
                                  size: 14,
                                ),
                              ],
                            ),
                          ),
                        ),
                      ],
                    ),

                    Text(
                      household.description.isEmpty
                          ? 'Nhóm chia tiền'
                          : household.description,
                      style: const TextStyle(
                        color: Colors.white70,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 30),
          const Text(
            'Tổng chi tiêu',
            style: TextStyle(
              color: Colors.white70,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 10),
          Text(
            '${formatMoney(totalExpense)}đ',
            style: const TextStyle(
              color: Colors.white,
              fontSize: 36,
              fontWeight: FontWeight.w900,
              letterSpacing: -1,
            ),
          ),
          const SizedBox(height: 22),
          Row(
            children: [
              buildMiniInfo(
                icon: Icons.receipt_long,
                label: '${expenses.length} khoản chi',
              ),
              const SizedBox(width: 12),
              buildMiniInfo(
                icon: Icons.people_alt_rounded,
                label: '${household.members.length} thành viên',
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget buildMiniInfo({
    required IconData icon,
    required String label,
  }) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: 14,
        vertical: 10,
      ),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.14),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Row(
        children: [
          Icon(
            icon,
            color: Colors.white,
            size: 18,
          ),
          const SizedBox(width: 8),
          Text(
            label,
            style: const TextStyle(
              color: Colors.white,
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ),
    );
  }

  Widget buildMembersSection() {
    final members = List<dynamic>.from(household.members);

    members.sort((a, b) {
      if (a.role == 'owner' && b.role != 'owner') {
        return -1;
      }

      if (a.role != 'owner' && b.role == 'owner') {
        return 1;
      }

      return a.displayName.toString().compareTo(
            b.displayName.toString(),
          );
    });

    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(28),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Text(
                'Thành viên',
                style: TextStyle(
                  fontSize: 20,
                  fontWeight: FontWeight.w900,
                  color: AppColors.textDark,
                ),
              ),
              const Spacer(),
              TextButton(
                onPressed: openMembersScreen,
                child: const Text('Xem tất cả'),
              ),
            ],
          ),
          const SizedBox(height: 18),

          if (members.isEmpty)
            buildEmptyCard(
              icon: Icons.people_outline_rounded,
              title: 'Chưa có thành viên',
            )
          else
            SizedBox(
              height: 112,
              child: ListView.separated(
                scrollDirection: Axis.horizontal,
                itemCount: members.length,
                separatorBuilder: (_, _) =>
                    const SizedBox(width: 16),
                itemBuilder: (_, index) {
                  final member = members[index];

                  return GestureDetector(
                    onTap: openMembersScreen,
                    child: SizedBox(
                      width: 76,
                      child: Column(
                        children: [
                          Stack(
                            clipBehavior: Clip.none,
                            children: [
                              buildAvatar(
                                imageUrl: member.userAvatar,
                                name: member.displayName,
                                radius: 24,
                              ),

                              if (member.role == 'owner')
                                Positioned(
                                  right: -4,
                                  bottom: -4,
                                  child: Container(
                                    padding:
                                        const EdgeInsets.all(4),
                                    decoration: BoxDecoration(
                                      color: Colors.amber,
                                      borderRadius:
                                          BorderRadius.circular(999),
                                      border: Border.all(
                                        color: Colors.white,
                                        width: 2,
                                      ),
                                    ),
                                    child: const Icon(
                                      Icons.star_rounded,
                                      size: 12,
                                      color: Colors.white,
                                    ),
                                  ),
                                ),
                            ],
                          ),
                          const SizedBox(height: 8),
                          Text(
                            member.displayName,
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                            textAlign: TextAlign.center,
                            style: const TextStyle(
                              fontSize: 11,
                              fontWeight: FontWeight.w700,
                              color: AppColors.textDark,
                            ),
                          ),
                          if (member.role == 'owner')
                            const Text(
                              'Owner',
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: TextStyle(
                                fontSize: 10,
                                fontWeight: FontWeight.w800,
                                color: Colors.amber,
                              ),
                            ),
                        ],
                      ),
                    ),
                  );
                },
              ),
            ),
        ],
      ),
    );
  }

  Widget buildMemberChip(dynamic member) {
    final name = getMemberName(member);
    final email = getMemberEmail(member);

    final firstLetter = name.isNotEmpty ? name[0].toUpperCase() : '?';

    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: 14,
        vertical: 12,
      ),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(18),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          CircleAvatar(
            radius: 16,
            backgroundColor: AppColors.primary,
            child: Text(
              firstLetter,
              style: const TextStyle(
                color: Colors.white,
                fontWeight: FontWeight.w800,
              ),
            ),
          ),
          const SizedBox(width: 10),
          ConstrainedBox(
            constraints: const BoxConstraints(
              maxWidth: 210,
            ),
            child: Text(
              email.isNotEmpty ? email : name,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(
                fontWeight: FontWeight.w700,
                color: AppColors.textDark,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Future<void> openPairDebtDetail(
    Map<String, dynamic> item,
  ) async {
    final otherUserId = readInt(
      item['other_user_id'],
    );

    if (otherUserId <= 0 || isLoadingDebtDetail) {
      return;
    }

    setState(() {
      isLoadingDebtDetail = true;
      loadingDebtDetailUserId = otherUserId;
    });

    try {
      final response =
          await ApiService.getHouseholdMyDebtDetail(
        householdId: household.id,
        otherUserId: otherUserId,
      );

      if (!mounted) return;

      await showModalBottomSheet<void>(
        context: context,
        isScrollControlled: true,
        backgroundColor: Colors.transparent,
        builder: (sheetContext) {
          return buildPairDebtDetailSheet(
            Map<String, dynamic>.from(response),
          );
        },
      );
    } catch (e) {
      if (!mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(e.toString()),
        ),
      );
    } finally {
      if (mounted) {
        setState(() {
          isLoadingDebtDetail = false;
          loadingDebtDetailUserId = null;
        });
      }
    }
  }

  Widget buildDebtSection() {
    final summary = myDebtSummary ?? {};

    final totalIOwe = readDouble(
      summary['total_i_owe'],
    );

    final totalOwedToMe = readDouble(
      summary['total_owed_to_me'],
    );

    final iOwe = readMapList(
      summary['i_owe'],
    );

    final owedToMe = readMapList(
      summary['owed_to_me'],
    );

    final hasDebt =
        iOwe.isNotEmpty || owedToMe.isNotEmpty;

    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(28),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Công nợ của bạn',
            style: TextStyle(
              fontSize: 20,
              fontWeight: FontWeight.w900,
              color: AppColors.textDark,
            ),
          ),
          const SizedBox(height: 6),
          const Text(
            'Chỉ hiển thị công nợ liên quan đến bạn trong nhóm này.',
            style: TextStyle(
              color: AppColors.textLight,
              fontWeight: FontWeight.w600,
              fontSize: 13,
            ),
          ),
          const SizedBox(height: 18),

          Row(
            children: [
              Expanded(
                child: buildDebtSummaryBox(
                  title: 'Bạn cần trả',
                  amount: totalIOwe,
                  icon: Icons.call_made_rounded,
                  color: AppColors.warning,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: buildDebtSummaryBox(
                  title: 'Bạn được nhận',
                  amount: totalOwedToMe,
                  icon: Icons.call_received_rounded,
                  color: AppColors.primary,
                ),
              ),
            ],
          ),

          const SizedBox(height: 20),

          if (!hasDebt)
            buildEmptyCard(
              icon: Icons.check_circle_outline,
              title: 'Không có công nợ',
            )
          else ...[
            if (iOwe.isNotEmpty) ...[
              buildDebtGroupTitle(
                title: 'Bạn đang nợ',
                icon: Icons.call_made_rounded,
                color: AppColors.warning,
              ),
              const SizedBox(height: 10),
              ...iOwe.map(
                (item) => buildPairDebtRow(
                  item,
                  isOwe: true,
                ),
              ),
              const SizedBox(height: 16),
            ],

            if (owedToMe.isNotEmpty) ...[
              buildDebtGroupTitle(
                title: 'Đang nợ bạn',
                icon: Icons.call_received_rounded,
                color: AppColors.primary,
              ),
              const SizedBox(height: 10),
              ...owedToMe.map(
                (item) => buildPairDebtRow(
                  item,
                  isOwe: false,
                ),
              ),
            ],
          ],
        ],
      ),
    );
  }

  Widget buildDebtSummaryBox({
    required String title,
    required double amount,
    required IconData icon,
    required Color color,
  }) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(
          color: color.withValues(alpha: 0.16),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(
            icon,
            color: color,
            size: 22,
          ),
          const SizedBox(height: 10),
          Text(
            title,
            style: const TextStyle(
              color: AppColors.textLight,
              fontSize: 13,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            '${formatMoney(amount)}đ',
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: TextStyle(
              color: color,
              fontSize: 18,
              fontWeight: FontWeight.w900,
              letterSpacing: -0.3,
            ),
          ),
        ],
      ),
    );
  }

  Widget buildDebtGroupTitle({
    required String title,
    required IconData icon,
    required Color color,
  }) {
    return Row(
      children: [
        Icon(
          icon,
          color: color,
          size: 18,
        ),
        const SizedBox(width: 8),
        Text(
          title,
          style: const TextStyle(
            color: AppColors.textDark,
            fontSize: 15,
            fontWeight: FontWeight.w900,
          ),
        ),
      ],
    );
  }

  Widget buildPairDebtRow(
    Map<String, dynamic> item, {
    required bool isOwe,
  }) {
    final name = readDebtUserName(item);
    final avatar = item['other_avatar']?.toString() ?? '';
    final amount = readDouble(item['amount']);
    final expenseCount = readInt(item['expense_count']);
    final otherUserId = readInt(item['other_user_id']);
    final isLoadingThis =
        isLoadingDebtDetail &&
        loadingDebtDetailUserId == otherUserId;

    final color = isOwe
        ? AppColors.warning
        : AppColors.primary;

    return InkWell(
      onTap: isLoadingDebtDetail
          ? null
          : () => openPairDebtDetail(item),
      borderRadius: BorderRadius.circular(20),
      child: Container(
        margin: const EdgeInsets.only(bottom: 10),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: AppColors.background,
          borderRadius: BorderRadius.circular(20),
        ),
        child: Row(
          children: [
            buildAvatar(
              imageUrl: avatar,
              name: name,
              radius: 22,
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment:
                    CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          name,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(
                            color: AppColors.textDark,
                            fontSize: 15,
                            fontWeight: FontWeight.w900,
                          ),
                        ),
                      ),
                      if (item['is_virtual'] == true)
                        Container(
                          margin: const EdgeInsets.only(left: 8),
                          padding: const EdgeInsets.symmetric(
                            horizontal: 8,
                            vertical: 3,
                          ),
                          decoration: BoxDecoration(
                            color: AppColors.primary.withValues(
                              alpha: 0.10,
                            ),
                            borderRadius:
                                BorderRadius.circular(999),
                          ),
                          child: const Text(
                            'Ảo',
                            style: TextStyle(
                              color: AppColors.primary,
                              fontSize: 10,
                              fontWeight: FontWeight.w900,
                            ),
                          ),
                        ),
                    ],
                  ),
                  const SizedBox(height: 4),
                  Text(
                    expenseCount <= 0
                        ? 'Nhấn để xem chi tiết'
                        : '$expenseCount khoản phát sinh',
                    style: const TextStyle(
                      color: AppColors.textLight,
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 10),
            Column(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                if (isLoadingThis)
                  const SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(
                      strokeWidth: 2.2,
                    ),
                  )
                else
                  Text(
                    '${formatMoney(amount)}đ',
                    style: TextStyle(
                      color: color,
                      fontSize: 15,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                const SizedBox(height: 4),
                Icon(
                  Icons.chevron_right_rounded,
                  color: color,
                  size: 20,
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget buildPairDebtDetailSheet(
    Map<String, dynamic> detail,
  ) {
    final otherName =
        detail['other_name']?.toString() ?? 'Thành viên';

    final netDirection =
        detail['net_direction']?.toString() ?? '';

    final netAmount = readDouble(
      detail['net_amount'],
    );

    final items = readMapList(
      detail['items'],
    );

    final isIOwe = netDirection == 'i_owe';
    final isOwedToMe = netDirection == 'owed_to_me';

    String summaryText;

    if (isIOwe) {
      summaryText =
          'Bạn cần trả $otherName ${formatMoney(netAmount)}đ';
    } else if (isOwedToMe) {
      summaryText =
          '$otherName cần trả bạn ${formatMoney(netAmount)}đ';
    } else {
      summaryText =
          'Bạn và $otherName không còn chênh lệch công nợ.';
    }

    final summaryColor = isIOwe
        ? AppColors.warning
        : AppColors.primary;

    return SafeArea(
      child: Container(
        margin: const EdgeInsets.all(14),
        padding: const EdgeInsets.fromLTRB(
          18,
          16,
          18,
          18,
        ),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(28),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.12),
              blurRadius: 30,
              offset: const Offset(0, 12),
            ),
          ],
        ),
        constraints: BoxConstraints(
          maxHeight:
              MediaQuery.of(context).size.height * 0.82,
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment:
              CrossAxisAlignment.start,
          children: [
            Center(
              child: Container(
                width: 42,
                height: 5,
                decoration: BoxDecoration(
                  color: AppColors.border,
                  borderRadius: BorderRadius.circular(999),
                ),
              ),
            ),
            const SizedBox(height: 18),

            Text(
              'Công nợ với $otherName',
              style: const TextStyle(
                color: AppColors.textDark,
                fontSize: 20,
                fontWeight: FontWeight.w900,
                letterSpacing: -0.4,
              ),
            ),

            const SizedBox(height: 12),

            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: summaryColor.withValues(alpha: 0.08),
                borderRadius: BorderRadius.circular(18),
                border: Border.all(
                  color: summaryColor.withValues(alpha: 0.16),
                ),
              ),
              child: Text(
                summaryText,
                style: TextStyle(
                  color: summaryColor,
                  fontSize: 15,
                  fontWeight: FontWeight.w900,
                  height: 1.35,
                ),
              ),
            ),

            const SizedBox(height: 18),

            const Text(
              'Chi tiết phát sinh',
              style: TextStyle(
                color: AppColors.textDark,
                fontSize: 16,
                fontWeight: FontWeight.w900,
              ),
            ),

            const SizedBox(height: 10),

            if (items.isEmpty)
              const Padding(
                padding: EdgeInsets.symmetric(vertical: 20),
                child: Center(
                  child: Text(
                    'Không có khoản phát sinh.',
                    style: TextStyle(
                      color: AppColors.textLight,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
              )
            else
              Flexible(
                child: ListView.separated(
                  shrinkWrap: true,
                  itemCount: items.length,
                  separatorBuilder: (_, _) =>
                      const SizedBox(height: 10),
                  itemBuilder: (_, index) {
                    return buildPairDebtDetailItem(
                      items[index],
                      otherName,
                    );
                  },
                ),
              ),
          ],
        ),
      ),
    );
  }

  Widget buildPairDebtDetailItem(
    Map<String, dynamic> item,
    String otherName,
  ) {
    final title =
        item['expense_title']?.toString() ?? 'Khoản chi';
    final date =
        item['expense_date']?.toString() ?? '';
    final payerName =
        item['payer_name']?.toString() ?? '';
    final direction =
        item['direction']?.toString() ?? '';
    final amount = readDouble(
      item['amount'],
    );

    final isIOwe = direction == 'i_owe';

    final label = isIOwe
        ? 'Bạn nợ $otherName'
        : '$otherName nợ bạn';

    final color = isIOwe
        ? AppColors.warning
        : AppColors.primary;

    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppColors.background,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(
          color: AppColors.border,
        ),
      ),
      child: Row(
        children: [
          Container(
            width: 42,
            height: 42,
            decoration: BoxDecoration(
              color: color.withValues(alpha: 0.10),
              borderRadius: BorderRadius.circular(14),
            ),
            child: Icon(
              isIOwe
                  ? Icons.call_made_rounded
                  : Icons.call_received_rounded,
              color: color,
              size: 22,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment:
                  CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    color: AppColors.textDark,
                    fontSize: 14,
                    fontWeight: FontWeight.w900,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  [
                    if (payerName.isNotEmpty)
                      'Người trả: $payerName',
                    if (date.isNotEmpty) date,
                  ].join(' • '),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    color: AppColors.textLight,
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  label,
                  style: TextStyle(
                    color: color,
                    fontSize: 12,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 10),
          Text(
            '${formatMoney(amount)}đ',
            style: TextStyle(
              color: color,
              fontSize: 14,
              fontWeight: FontWeight.w900,
            ),
          ),
        ],
      ),
    );
  }

  Widget buildVirtualMemberDebtSection() {
    final summary = virtualDebtSummary ?? {};

    final selectedMemberName = selectedVirtualMember == null
        ? 'Thành viên ảo'
        : getMemberName(selectedVirtualMember);

    final virtualName =
        summary['virtual_name']?.toString() ?? selectedMemberName;

    final totalVirtualOwes = readDouble(
      summary['total_virtual_owes'],
    );

    final totalOwedToVirtual = readDouble(
      summary['total_owed_to_virtual'],
    );

    final virtualOwes = readMapList(
      summary['virtual_owes'],
    );

    final owedToVirtual = readMapList(
      summary['owed_to_virtual'],
    );

    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(28),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Quản lý công nợ thành viên ảo',
            style: TextStyle(
              fontSize: 20,
              fontWeight: FontWeight.w900,
              color: AppColors.textDark,
            ),
          ),
          const SizedBox(height: 6),
          const Text(
            'Chủ nhóm có thể xem công nợ giùm từng thành viên ảo.',
            style: TextStyle(
              color: AppColors.textLight,
              fontWeight: FontWeight.w600,
              fontSize: 13,
            ),
          ),
          const SizedBox(height: 16),

          DropdownButtonFormField<int>(
            initialValue: selectedVirtualUserId,
            decoration: InputDecoration(
              labelText: 'Chọn thành viên ảo',
              filled: true,
              fillColor: AppColors.background,
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(18),
                borderSide: BorderSide.none,
              ),
            ),
            items: virtualMembers.map<DropdownMenuItem<int>>(
              (member) {
                return DropdownMenuItem<int>(
                  value: getMemberUserId(member),
                  child: Text(getMemberName(member)),
                );
              },
            ).toList(),
            onChanged: isLoadingVirtualDebt
                ? null
                : (value) async {
                    if (value == null) return;

                    setState(() {
                      selectedVirtualUserId = value;
                    });

                    await loadVirtualMemberDebtSummary();
                  },
          ),

          const SizedBox(height: 18),

          if (isLoadingVirtualDebt)
            const Center(
              child: Padding(
                padding: EdgeInsets.all(20),
                child: CircularProgressIndicator(),
              ),
            )
          else ...[
            Row(
              children: [
                Expanded(
                  child: buildDebtSummaryBox(
                    title: '$virtualName cần trả',
                    amount: totalVirtualOwes,
                    icon: Icons.call_made_rounded,
                    color: AppColors.warning,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: buildDebtSummaryBox(
                    title: '$virtualName được nhận',
                    amount: totalOwedToVirtual,
                    icon: Icons.call_received_rounded,
                    color: AppColors.primary,
                  ),
                ),
              ],
            ),

            const SizedBox(height: 20),

            if (virtualOwes.isEmpty && owedToVirtual.isEmpty)
              buildEmptyCard(
                icon: Icons.check_circle_outline,
                title: '$virtualName chưa có công nợ',
              )
            else ...[
              if (virtualOwes.isNotEmpty) ...[
                buildDebtGroupTitle(
                  title: '$virtualName đang nợ',
                  icon: Icons.call_made_rounded,
                  color: AppColors.warning,
                ),
                const SizedBox(height: 10),
                ...virtualOwes.map(
                  (item) => buildVirtualDebtRow(
                    item,
                    virtualOwes: true,
                  ),
                ),
                const SizedBox(height: 16),
              ],

              if (owedToVirtual.isNotEmpty) ...[
                buildDebtGroupTitle(
                  title: 'Đang nợ $virtualName',
                  icon: Icons.call_received_rounded,
                  color: AppColors.primary,
                ),
                const SizedBox(height: 10),
                ...owedToVirtual.map(
                  (item) => buildVirtualDebtRow(
                    item,
                    virtualOwes: false,
                  ),
                ),
              ],
            ],
          ],
        ],
      ),
    );
  }

  Widget buildVirtualDebtRow(
    Map<String, dynamic> item, {
    required bool virtualOwes,
  }) {
    final name = item['other_name']?.toString() ?? 'Thành viên';
    final avatar = item['other_avatar']?.toString() ?? '';
    final amount = readDouble(item['amount']);
    final expenseCount = readInt(item['expense_count']);
    final otherUserId = readInt(item['other_user_id']);

    final isLoadingThis =
        isLoadingVirtualDebtDetail &&
        loadingVirtualDebtDetailUserId == otherUserId;

    final color = virtualOwes
        ? AppColors.warning
        : AppColors.primary;

    return InkWell(
      onTap: isLoadingVirtualDebtDetail
          ? null
          : () => openVirtualDebtDetail(item),
      borderRadius: BorderRadius.circular(20),
      child: Container(
        margin: const EdgeInsets.only(bottom: 10),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: AppColors.background,
          borderRadius: BorderRadius.circular(20),
        ),
        child: Row(
          children: [
            buildAvatar(
              imageUrl: avatar,
              name: name,
              radius: 22,
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment:
                    CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          name,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(
                            color: AppColors.textDark,
                            fontSize: 15,
                            fontWeight: FontWeight.w900,
                          ),
                        ),
                      ),
                      if (item['other_is_virtual'] == true)
                        Container(
                          margin: const EdgeInsets.only(left: 8),
                          padding: const EdgeInsets.symmetric(
                            horizontal: 8,
                            vertical: 3,
                          ),
                          decoration: BoxDecoration(
                            color: AppColors.primary.withValues(
                              alpha: 0.10,
                            ),
                            borderRadius:
                                BorderRadius.circular(999),
                          ),
                          child: const Text(
                            'Ảo',
                            style: TextStyle(
                              color: AppColors.primary,
                              fontSize: 10,
                              fontWeight: FontWeight.w900,
                            ),
                          ),
                        ),
                    ],
                  ),
                  const SizedBox(height: 4),
                  Text(
                    expenseCount <= 0
                        ? 'Nhấn để xem chi tiết'
                        : '$expenseCount khoản phát sinh',
                    style: const TextStyle(
                      color: AppColors.textLight,
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 10),
            Column(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                if (isLoadingThis)
                  const SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(
                      strokeWidth: 2.2,
                    ),
                  )
                else
                  Text(
                    '${formatMoney(amount)}đ',
                    style: TextStyle(
                      color: color,
                      fontSize: 15,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                const SizedBox(height: 4),
                Icon(
                  Icons.chevron_right_rounded,
                  color: color,
                  size: 20,
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Future<void> openVirtualDebtDetail(
    Map<String, dynamic> item,
  ) async {
    final virtualUserId = selectedVirtualUserId;
    final otherUserId = readInt(item['other_user_id']);

    if (virtualUserId == null ||
        virtualUserId <= 0 ||
        otherUserId <= 0 ||
        isLoadingVirtualDebtDetail) {
      return;
    }

    setState(() {
      isLoadingVirtualDebtDetail = true;
      loadingVirtualDebtDetailUserId = otherUserId;
    });

    try {
      final response =
          await ApiService.getVirtualMemberDebtDetail(
        householdId: household.id,
        virtualUserId: virtualUserId,
        otherUserId: otherUserId,
      );

      if (!mounted) return;

      await showModalBottomSheet<void>(
        context: context,
        isScrollControlled: true,
        backgroundColor: Colors.transparent,
        builder: (_) {
          return buildVirtualDebtDetailSheet(
            Map<String, dynamic>.from(response),
          );
        },
      );
    } catch (e) {
      if (!mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(e.toString()),
        ),
      );
    } finally {
      if (mounted) {
        setState(() {
          isLoadingVirtualDebtDetail = false;
          loadingVirtualDebtDetailUserId = null;
        });
      }
    }
  }

  Widget buildVirtualDebtDetailSheet(
    Map<String, dynamic> detail,
  ) {
    final virtualName =
        detail['virtual_name']?.toString() ?? 'Thành viên ảo';
    final otherName =
        detail['other_name']?.toString() ?? 'Thành viên';

    final netDirection =
        detail['net_direction']?.toString() ?? '';

    final netAmount = readDouble(
      detail['net_amount'],
    );

    final items = readMapList(
      detail['items'],
    );

    final isVirtualOwes = netDirection == 'virtual_owes';
    final isOwedToVirtual =
        netDirection == 'owed_to_virtual';

    String summaryText;

    if (isVirtualOwes) {
      summaryText =
          '$virtualName cần trả $otherName ${formatMoney(netAmount)}đ';
    } else if (isOwedToVirtual) {
      summaryText =
          '$otherName cần trả $virtualName ${formatMoney(netAmount)}đ';
    } else {
      summaryText =
          '$virtualName và $otherName không còn chênh lệch công nợ.';
    }

    final summaryColor = isVirtualOwes
        ? AppColors.warning
        : AppColors.primary;

    return SafeArea(
      child: Container(
        margin: const EdgeInsets.all(14),
        padding: const EdgeInsets.fromLTRB(
          18,
          16,
          18,
          18,
        ),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(28),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.12),
              blurRadius: 30,
              offset: const Offset(0, 12),
            ),
          ],
        ),
        constraints: BoxConstraints(
          maxHeight:
              MediaQuery.of(context).size.height * 0.82,
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment:
              CrossAxisAlignment.start,
          children: [
            Center(
              child: Container(
                width: 42,
                height: 5,
                decoration: BoxDecoration(
                  color: AppColors.border,
                  borderRadius: BorderRadius.circular(999),
                ),
              ),
            ),
            const SizedBox(height: 18),

            Text(
              'Công nợ của $virtualName',
              style: const TextStyle(
                color: AppColors.textDark,
                fontSize: 20,
                fontWeight: FontWeight.w900,
                letterSpacing: -0.4,
              ),
            ),

            const SizedBox(height: 12),

            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: summaryColor.withValues(alpha: 0.08),
                borderRadius: BorderRadius.circular(18),
                border: Border.all(
                  color: summaryColor.withValues(alpha: 0.16),
                ),
              ),
              child: Text(
                summaryText,
                style: TextStyle(
                  color: summaryColor,
                  fontSize: 15,
                  fontWeight: FontWeight.w900,
                  height: 1.35,
                ),
              ),
            ),

            const SizedBox(height: 18),

            const Text(
              'Chi tiết phát sinh',
              style: TextStyle(
                color: AppColors.textDark,
                fontSize: 16,
                fontWeight: FontWeight.w900,
              ),
            ),

            const SizedBox(height: 10),

            if (items.isEmpty)
              const Padding(
                padding: EdgeInsets.symmetric(vertical: 20),
                child: Center(
                  child: Text(
                    'Không có khoản phát sinh.',
                    style: TextStyle(
                      color: AppColors.textLight,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
              )
            else
              Flexible(
                child: ListView.separated(
                  shrinkWrap: true,
                  itemCount: items.length,
                  separatorBuilder: (_, _) =>
                      const SizedBox(height: 10),
                  itemBuilder: (_, index) {
                    return buildVirtualDebtDetailItem(
                      items[index],
                      virtualName,
                      otherName,
                    );
                  },
                ),
              ),

            if (items.isNotEmpty) ...[
              const SizedBox(height: 16),
              SizedBox(
                width: double.infinity,
                height: 52,
                child: FilledButton.icon(
                  onPressed: isSettlingVirtualDebt
                      ? null
                      : () => settleVirtualDebtPair(detail),
                  icon: isSettlingVirtualDebt
                      ? const SizedBox(
                          width: 18,
                          height: 18,
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            color: Colors.white,
                          ),
                        )
                      : const Icon(Icons.done_all_rounded),
                  label: Text(
                    isSettlingVirtualDebt
                        ? 'Đang xử lý...'
                        : 'Đánh dấu đã xử lý ngoài đời',
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget buildVirtualDebtDetailItem(
    Map<String, dynamic> item,
    String virtualName,
    String otherName,
  ) {
    final title =
        item['expense_title']?.toString() ?? 'Khoản chi';
    final date =
        item['expense_date']?.toString() ?? '';
    final payerName =
        item['payer_name']?.toString() ?? '';
    final direction =
        item['direction']?.toString() ?? '';
    final amount = readDouble(
      item['amount'],
    );

    final isVirtualOwes = direction == 'virtual_owes';

    final label = isVirtualOwes
        ? '$virtualName nợ $otherName'
        : '$otherName nợ $virtualName';

    final color = isVirtualOwes
        ? AppColors.warning
        : AppColors.primary;

    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppColors.background,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(
          color: AppColors.border,
        ),
      ),
      child: Row(
        children: [
          Container(
            width: 42,
            height: 42,
            decoration: BoxDecoration(
              color: color.withValues(alpha: 0.10),
              borderRadius: BorderRadius.circular(14),
            ),
            child: Icon(
              isVirtualOwes
                  ? Icons.call_made_rounded
                  : Icons.call_received_rounded,
              color: color,
              size: 22,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment:
                  CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    color: AppColors.textDark,
                    fontSize: 14,
                    fontWeight: FontWeight.w900,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  [
                    if (payerName.isNotEmpty)
                      'Người trả: $payerName',
                    if (date.isNotEmpty) date,
                  ].join(' • '),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    color: AppColors.textLight,
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  label,
                  style: TextStyle(
                    color: color,
                    fontSize: 12,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 10),
          Text(
            '${formatMoney(amount)}đ',
            style: TextStyle(
              color: color,
              fontSize: 14,
              fontWeight: FontWeight.w900,
            ),
          ),
        ],
      ),
    );
  }

  Future<void> settleVirtualDebtPair(
    Map<String, dynamic> detail,
  ) async {
    final virtualUserId = readInt(
      detail['virtual_user_id'],
    );

    final otherUserId = readInt(
      detail['other_user_id'],
    );

    if (virtualUserId <= 0 || otherUserId <= 0) {
      return;
    }

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) {
        return AlertDialog(
          title: const Text('Đã xử lý ngoài đời?'),
          content: const Text(
            'Các khoản công nợ chưa thanh toán giữa hai thành viên này sẽ được đánh dấu là đã xử lý. Hành động này không thể hoàn tác nhanh.',
          ),
          actions: [
            TextButton(
              onPressed: () {
                Navigator.pop(dialogContext, false);
              },
              child: const Text('Hủy'),
            ),
            FilledButton(
              onPressed: () {
                Navigator.pop(dialogContext, true);
              },
              child: const Text('Xác nhận'),
            ),
          ],
        );
      },
    );

    if (confirmed != true) return;

    setState(() {
      isSettlingVirtualDebt = true;
    });

    try {
      await ApiService.settleVirtualMemberDebtPair(
        householdId: household.id,
        virtualUserId: virtualUserId,
        otherUserId: otherUserId,
      );

      if (!mounted) return;

      Navigator.pop(context);

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Đã đánh dấu xử lý ngoài đời'),
        ),
      );

      await loadData();
    } catch (e) {
      if (!mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(e.toString()),
        ),
      );
    } finally {
      if (mounted) {
        setState(() {
          isSettlingVirtualDebt = false;
        });
      }
    }
  }

  Widget buildCompactDebtCard(Debt debt) {
    final fromName = displayUserName(
      name: debt.fromUserName,
      email: debt.fromUserEmail,
    );

    final toName = displayUserName(
      name: debt.toUserName,
      email: debt.toUserEmail,
    );

    return GestureDetector(
      onTap: () => openTransferQR(debt),
      child: Container(
        margin: const EdgeInsets.only(bottom: 12),
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: AppColors.background,
          borderRadius: BorderRadius.circular(22),
        ),
        child: Row(
          children: [
            buildAvatar(
              imageUrl: debt.fromUserAvatar,
              name: fromName,
              radius: 24,
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    fromName,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      fontWeight: FontWeight.w900,
                      color: AppColors.textDark,
                      fontSize: 15,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    'Cần trả ${formatMoney(debt.amount)}đ',
                    style: const TextStyle(
                      color: AppColors.warning,
                      fontWeight: FontWeight.w900,
                      fontSize: 14,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      const Icon(
                        Icons.arrow_downward_rounded,
                        size: 16,
                        color: AppColors.textLight,
                      ),
                      const SizedBox(width: 6),
                      Expanded(
                        child: Text(
                          'Người nhận: $toName',
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(
                            color: AppColors.textLight,
                            fontWeight: FontWeight.w700,
                            fontSize: 12,
                          ),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(width: 12),
            buildAvatar(
              imageUrl: debt.toUserAvatar,
              name: toName,
              radius: 24,
            ),
          ],
        ),
      ),
    );
  }

  Widget buildDebtCard(Debt debt) {
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
            width: 52,
            height: 52,
            decoration: BoxDecoration(
              color: AppColors.warning.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(16),
            ),
            child: const Icon(
              Icons.sync_alt_rounded,
              color: AppColors.warning,
            ),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '${debt.fromUserEmail} → ${debt.toUserEmail}',
                  style: const TextStyle(
                    fontWeight: FontWeight.w800,
                    fontSize: 15,
                    color: AppColors.textDark,
                  ),
                ),
                const SizedBox(height: 6),
                Text(
                  '${formatMoney(debt.amount)}đ',
                  style: const TextStyle(
                    color: AppColors.warning,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget buildExpenseSection() {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(28),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Text(
                'Khoản chi gần đây',
                style: TextStyle(
                  fontSize: 20,
                  fontWeight: FontWeight.w900,
                  color: AppColors.textDark,
                ),
              ),
              const Spacer(),
              TextButton(
                onPressed: () {},
                child: const Text('View all'),
              ),
            ],
          ),
          const SizedBox(height: 16),

          if (expenses.isEmpty)
            buildEmptyCard(
              icon: Icons.receipt_long,
              title: 'Chưa có khoản chi',
            )
          else
            Column(
              children: [
                ...expenses.map(
                  buildCompactExpenseCard,
                ),

                if (isLoadingMoreExpenses)
                  const Padding(
                    padding: EdgeInsets.symmetric(vertical: 18),
                    child: Center(
                      child: CircularProgressIndicator(),
                    ),
                  ),

                if (isExpensePageError)
                  Padding(
                    padding: const EdgeInsets.only(top: 12),
                    child: Column(
                      children: [
                        const Text(
                          'Không tải được thêm khoản chi',
                          style: TextStyle(
                            color: AppColors.textLight,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                        const SizedBox(height: 8),
                        OutlinedButton(
                          onPressed: () {
                            setState(() {
                              isExpensePageError = false;
                            });

                            loadMoreExpenses();
                          },
                          child: const Text('Thử lại'),
                        ),
                      ],
                    ),
                  ),

                if (!hasMoreExpenses &&
                    expenses.isNotEmpty &&
                    !isLoadingMoreExpenses)
                  const Padding(
                    padding: EdgeInsets.symmetric(vertical: 12),
                    child: Text(
                      'Đã tải hết khoản chi',
                      style: TextStyle(
                        color: AppColors.textLight,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
              ],
            ),
        ],
      ),
    );
  }

  Widget buildCompactExpenseCard(
    Expense expense,
  ) {
    final payerName = displayUserName(
      name: expense.payerName,
      email: expense.payerEmail,
    );

    final isBusy = editingExpenseId == expense.id ||
        deletingExpenseId == expense.id;

    return Container(
      margin: const EdgeInsets.only(bottom: 20),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.background,
        borderRadius: BorderRadius.circular(22),
      ),
      child: Row(
        children: [
          buildAvatar(
            imageUrl: expense.payerAvatar,
            name: payerName,
            radius: 24,
          ),
          const SizedBox(width: 14),
          Expanded(
            child: InkWell(
              borderRadius: BorderRadius.circular(18),
              onTap: expense.canManage && !isBusy
                  ? () => openEditExpenseScreen(expense)
                  : null,
              child: Padding(
                padding: const EdgeInsets.symmetric(
                  vertical: 4,
                ),
                child: Column(
                  crossAxisAlignment:
                      CrossAxisAlignment.start,
                  children: [
                    Text(
                      expense.title,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        fontWeight: FontWeight.w800,
                        color: AppColors.textDark,
                      ),
                    ),
                    const SizedBox(height: 6),
                    Text(
                      'Người trả: $payerName',
                      style: const TextStyle(
                        color: AppColors.textLight,
                        fontWeight: FontWeight.w600,
                        fontSize: 13,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      expense.expenseDate,
                      style: const TextStyle(
                        color: AppColors.textLight,
                        fontSize: 12,
                      ),
                    ),
                    if (expense.participants.isNotEmpty) ...[
                      const SizedBox(height: 4),
                      Text(
                        'Chia cho ${expense.participants.length} người',
                        style: const TextStyle(
                          color: AppColors.textLight,
                          fontSize: 12,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ],
                  ],
                ),
              ),
            ),
          ),
          const SizedBox(width: 12),
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text(
                '${formatMoney(expense.amount)}đ',
                style: const TextStyle(
                  fontWeight: FontWeight.w900,
                  color: AppColors.primary,
                ),
              ),
              const SizedBox(height: 8),
              if (isBusy)
                const SizedBox(
                  width: 22,
                  height: 22,
                  child: CircularProgressIndicator(
                    strokeWidth: 2.4,
                  ),
                )
              else if (expense.canManage)
                PopupMenuButton<String>(
                  padding: EdgeInsets.zero,
                  icon: const Icon(
                    Icons.more_horiz_rounded,
                    color: AppColors.textLight,
                  ),
                  onSelected: (value) {
                    if (value == 'edit') {
                      openEditExpenseScreen(expense);
                    }

                    if (value == 'delete') {
                      confirmDeleteExpense(expense);
                    }
                  },
                  itemBuilder: (context) => const [
                    PopupMenuItem(
                      value: 'edit',
                      child: Row(
                        children: [
                          Icon(Icons.edit_rounded),
                          SizedBox(width: 10),
                          Text('Sửa'),
                        ],
                      ),
                    ),
                    PopupMenuItem(
                      value: 'delete',
                      child: Row(
                        children: [
                          Icon(
                            Icons.delete_outline_rounded,
                            color: Colors.red,
                          ),
                          SizedBox(width: 10),
                          Text(
                            'Xóa',
                            style: TextStyle(
                              color: Colors.red,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
            ],
          ),
        ],
      ),
    );
  }

  Widget buildExpenseCard(Expense expense) {
    return Container(
      margin: const EdgeInsets.only(bottom: 14),
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(24),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.02),
            blurRadius: 20,
            offset: const Offset(0, 8),
          ),
        ],
      ),
      child: Row(
        children: [
          Container(
            width: 56,
            height: 56,
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                colors: [
                  AppColors.primary,
                  AppColors.secondary,
                ],
              ),
              borderRadius: BorderRadius.circular(18),
            ),
            child: const Icon(
              Icons.payments_rounded,
              color: Colors.white,
            ),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  expense.title,
                  style: const TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.w800,
                    color: AppColors.textDark,
                  ),
                ),
                const SizedBox(height: 6),
                Text(
                  expense.payerEmail.isEmpty
                      ? 'Người trả đang cập nhật'
                      : expense.payerEmail,
                  style: const TextStyle(
                    color: AppColors.textLight,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 12),
          Text(
            '${formatMoney(expense.amount)}đ',
            style: const TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.w900,
              color: AppColors.primary,
            ),
          ),
        ],
      ),
    );
  }

  Widget buildEmptyCard({
    required IconData icon,
    required String title,
  }) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(28),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(26),
      ),
      child: Column(
        children: [
          Icon(
            icon,
            size: 46,
            color: AppColors.textLight,
          ),
          const SizedBox(height: 16),
          Text(
            title,
            style: const TextStyle(
              color: AppColors.textDark,
              fontWeight: FontWeight.w800,
              fontSize: 16,
            ),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (isLoading) {
      return const Scaffold(
        backgroundColor: AppColors.background,
        body: AppLoadingState(
          message: 'Đang tải dữ liệu nhóm...',
        ),
      );
    }

    if (errorMessage != null) {
      return Scaffold(
        backgroundColor: AppColors.background,
        body: AppErrorState(
          message: errorMessage!,
          onRetry: loadData,
        ),
      );
    }

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        titleSpacing: 20,
        title: Text(household.name),
        actions: [
          PopupMenuButton<String>(
            icon: const Icon(Icons.more_vert_rounded),
            onSelected: (value) {
              if (value == 'add_member') {
                showAddMemberDialog();
              }

              if (value == 'leave') {
                confirmLeaveHousehold();
              }

              if (value == 'delete') {
                confirmDeleteHousehold();
              }
            },
            itemBuilder: (context) => [
              PopupMenuItem(
                value: 'add_member',
                enabled: isCurrentUserOwner &&
                    !isAddingMember &&
                    !isKickingMember,
                child: const Text('Thêm thành viên'),
              ),
              PopupMenuItem(
                  value: 'leave',
                  enabled: !isLeavingHousehold && !isDeletingHousehold,
                  child: Text(
                    isLeavingHousehold ? 'Đang rời nhóm...' : 'Rời nhóm',
                  ),
                ),
                if (isCurrentUserOwner) ...[
                  const PopupMenuDivider(),
                  PopupMenuItem(
                    value: 'delete',
                    enabled: !isDeletingHousehold && !isLeavingHousehold,
                    child: Text(
                      isDeletingHousehold ? 'Đang xóa nhóm...' : 'Xóa nhóm',
                      style: const TextStyle(
                        color: AppColors.danger,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                  ),
                ],
            ],
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        elevation: 0,
        backgroundColor: AppColors.primary,
        onPressed: openAddExpenseScreen,
        icon: const Icon(
          Icons.add_rounded,
          color: Colors.white,
        ),
        label: const Text(
          'Thêm chi',
          style: TextStyle(
            color: Colors.white,
            fontWeight: FontWeight.w800,
          ),
        ),
      ),
      body: RefreshIndicator(
        onRefresh: refreshData,
        child: ListView(
          controller: scrollController,
          physics:
              const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(20),
          children: [
            buildHeroCard(),
            const SizedBox(height: 30),
            buildMembersSection(),
            const SizedBox(height: 30),
            buildDebtSection(),
            if (isCurrentUserOwner && virtualMembers.isNotEmpty) ...[
              const SizedBox(height: 30),
              buildVirtualMemberDebtSection(),
            ],
            const SizedBox(height: 30),
            if (expenses.isEmpty)
              SizedBox(
                height:
                    MediaQuery.of(context).size.height *
                    0.42,
                child: AppEmptyState(
                  icon: Icons.receipt_long_rounded,
                  title: 'Chưa có khoản chi',
                  message:
                      'Thêm khoản chi đầu tiên để Chung Ví tự động tính toán công nợ cho nhóm.',
                  buttonText: 'Thêm khoản chi',
                  onPressed: openAddExpenseScreen,
                ),
              )
            else
              buildExpenseSection(),
            const SizedBox(height: 120),
          ],
        ),
      ),
    );
  }
}