import 'package:flutter/material.dart';

import 'activity_screen.dart';
import 'add_expense_screen.dart';
import 'app_theme.dart';
import 'home_screen.dart';
import 'models/household.dart';
import 'profile_screen.dart';
import 'services/api_service.dart';
import 'debt_overview_screen.dart';

class BottomNavScreen extends StatefulWidget {
  const BottomNavScreen({super.key});

  @override
  State<BottomNavScreen> createState() => _BottomNavScreenState();
}

class _BottomNavScreenState extends State<BottomNavScreen> {
  int currentIndex = 0;

  int unreadNotificationCount = 0;
  bool isOpeningQuickAddExpense = false;

  late final List<Widget> screens;

  @override
  void initState() {
    super.initState();

    screens = const [
      HomeScreen(),
      ActivityScreen(),
      SizedBox.shrink(),
      DebtOverviewScreen(),
      ProfileScreen(),
    ];

    loadUnreadCount();
  }

  Future<void> loadUnreadCount() async {
    try {
      final count = await ApiService.getUnreadNotificationCount();

      if (!mounted) return;

      setState(() {
        unreadNotificationCount = count;
      });
    } catch (_) {}
  }

  Future<void> changeTab(int index) async {
    if (index == 2) {
      await openQuickAddExpense();
      return;
    }

    setState(() {
      currentIndex = index;
    });

    if (index == 1) {
      await loadUnreadCount();
    }
  }

  Future<void> openQuickAddExpense() async {
    if (isOpeningQuickAddExpense) return;

    FocusScope.of(context).unfocus();

    setState(() {
      isOpeningQuickAddExpense = true;
    });

    try {
      final households = await loadHouseholdsForQuickAdd();

      if (!mounted) return;

      if (households.isEmpty) {
        await showNoHouseholdDialog();
        return;
      }

      Household? selectedHousehold;

      if (households.length == 1) {
        selectedHousehold = households.first;
      } else {
        selectedHousehold = await showHouseholdPicker(households);
      }

      if (!mounted || selectedHousehold == null) return;

      final householdData = await ApiService.getHouseholdDetail(
        selectedHousehold.id,
      );

      if (!mounted) return;

      final freshHousehold = Household.fromJson(
        Map<String, dynamic>.from(householdData),
      );

      setState(() {
        isOpeningQuickAddExpense = false;
      });

      final result = await Navigator.push<bool>(
        context,
        MaterialPageRoute(
          builder: (_) => AddExpenseScreen(household: freshHousehold),
        ),
      );

      if (!mounted) return;

      if (result == true) {
        ScaffoldMessenger.of(context).hideCurrentSnackBar();

        ScaffoldMessenger.of(
          context,
        ).showSnackBar(const SnackBar(content: Text('Đã thêm khoản chi')));

        if (currentIndex == 1) {
          await loadUnreadCount();
        }
      }
    } catch (e) {
      if (!mounted) return;

      showQuickAddError(getErrorMessage(e));
    } finally {
      if (mounted && isOpeningQuickAddExpense) {
        setState(() {
          isOpeningQuickAddExpense = false;
        });
      }
    }
  }

  Future<List<Household>> loadHouseholdsForQuickAdd() async {
    final response = await ApiService.getHouseholds();

    return response
        .whereType<Map>()
        .map((item) => Household.fromJson(Map<String, dynamic>.from(item)))
        .where((household) => household.isActive)
        .toList();
  }

  Future<Household?> showHouseholdPicker(List<Household> households) {
    return showModalBottomSheet<Household>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (sheetContext) {
        return SafeArea(
          child: Container(
            margin: const EdgeInsets.all(14),
            padding: const EdgeInsets.fromLTRB(18, 16, 18, 18),
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
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(
                  width: 42,
                  height: 5,
                  decoration: BoxDecoration(
                    color: AppColors.border,
                    borderRadius: BorderRadius.circular(999),
                  ),
                ),
                const SizedBox(height: 18),
                const Align(
                  alignment: Alignment.centerLeft,
                  child: Text(
                    'Thêm khoản chi vào nhóm nào?',
                    style: TextStyle(
                      color: AppColors.textDark,
                      fontSize: 20,
                      fontWeight: FontWeight.w900,
                      letterSpacing: -0.5,
                    ),
                  ),
                ),
                const SizedBox(height: 6),
                const Align(
                  alignment: Alignment.centerLeft,
                  child: Text(
                    'Chọn nhóm để tạo khoản chi mới.',
                    style: TextStyle(
                      color: AppColors.textLight,
                      fontSize: 14,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
                const SizedBox(height: 14),
                Flexible(
                  child: ListView.separated(
                    shrinkWrap: true,
                    itemCount: households.length,
                    separatorBuilder: (_, _) => const SizedBox(height: 10),
                    itemBuilder: (_, index) {
                      final household = households[index];

                      return InkWell(
                        borderRadius: BorderRadius.circular(20),
                        onTap: () {
                          Navigator.pop(sheetContext, household);
                        },
                        child: Container(
                          padding: const EdgeInsets.all(14),
                          decoration: BoxDecoration(
                            color: AppColors.background,
                            borderRadius: BorderRadius.circular(20),
                            border: Border.all(color: AppColors.border),
                          ),
                          child: Row(
                            children: [
                              Container(
                                width: 48,
                                height: 48,
                                decoration: BoxDecoration(
                                  color: AppColors.primary.withValues(
                                    alpha: 0.10,
                                  ),
                                  borderRadius: BorderRadius.circular(18),
                                ),
                                child: const Icon(
                                  Icons.groups_rounded,
                                  color: AppColors.primary,
                                  size: 26,
                                ),
                              ),
                              const SizedBox(width: 13),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      household.name.trim().isEmpty
                                          ? 'Nhóm không tên'
                                          : household.name,
                                      maxLines: 1,
                                      overflow: TextOverflow.ellipsis,
                                      style: const TextStyle(
                                        color: AppColors.textDark,
                                        fontSize: 16,
                                        fontWeight: FontWeight.w900,
                                      ),
                                    ),
                                    const SizedBox(height: 4),
                                    Text(
                                      household.members.isEmpty
                                          ? 'Nhấn để chọn nhóm'
                                          : '${household.members.length} thành viên',
                                      style: const TextStyle(
                                        color: AppColors.textLight,
                                        fontSize: 13,
                                        fontWeight: FontWeight.w600,
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                              const SizedBox(width: 8),
                              const Icon(
                                Icons.chevron_right_rounded,
                                color: AppColors.textLight,
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
          ),
        );
      },
    );
  }

  Future<void> showNoHouseholdDialog() async {
    await showDialog<void>(
      context: context,
      builder: (dialogContext) {
        return AlertDialog(
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(24),
          ),
          title: const Text('Bạn chưa có nhóm nào'),
          content: const Text(
            'Hãy tạo hoặc tham gia một nhóm trước khi thêm khoản chi.',
          ),
          actions: [
            TextButton(
              onPressed: () {
                Navigator.pop(dialogContext);
              },
              child: const Text('Để sau'),
            ),
            FilledButton(
              onPressed: () {
                Navigator.pop(dialogContext);

                if (!mounted) return;

                setState(() {
                  currentIndex = 0;
                });
              },
              child: const Text('Về Trang chủ'),
            ),
          ],
        );
      },
    );
  }

  void showQuickAddError(String message) {
    ScaffoldMessenger.of(context).hideCurrentSnackBar();

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        action: SnackBarAction(
          label: 'Thử lại',
          onPressed: openQuickAddExpense,
        ),
      ),
    );
  }

  String getErrorMessage(Object error) {
    final message = error.toString();

    if (message.startsWith('Exception: ')) {
      return message.replaceFirst('Exception: ', '');
    }

    if (message.trim().isEmpty) {
      return 'Không thể mở màn hình thêm khoản chi';
    }

    return message;
  }

  @override
  Widget build(BuildContext context) {
    final width = MediaQuery.of(context).size.width;
    final compact = width < 380;
    final navHeight = compact ? 68.0 : 72.0;

    return Scaffold(
      extendBody: false,
      body: IndexedStack(index: currentIndex, children: screens),
      floatingActionButtonLocation: FloatingActionButtonLocation.centerDocked,
      floatingActionButton: buildQuickAddFab(),
      bottomNavigationBar: SafeArea(
        top: false,
        child: Container(
          height: navHeight,
          margin: EdgeInsets.fromLTRB(
            compact ? 12 : 18,
            0,
            compact ? 12 : 18,
            compact ? 8 : 10,
          ),
          padding: EdgeInsets.symmetric(
            horizontal: compact ? 8 : 10,
            vertical: compact ? 5 : 6,
          ),
          decoration: BoxDecoration(
            color: Colors.white.withValues(alpha: 0.96),
            borderRadius: BorderRadius.circular(24),
            border: Border.all(color: AppColors.border),
            boxShadow: [
              BoxShadow(
                color: AppColors.primaryDark.withValues(alpha: 0.10),
                blurRadius: 22,
                offset: const Offset(0, 10),
              ),
            ],
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              buildNavItem(
                index: 0,
                icon: Icons.home_rounded,
                label: 'Trang chủ',
              ),
              buildNavItem(
                index: 1,
                icon: Icons.receipt_long_rounded,
                label: 'Hoạt động',
                badgeCount: unreadNotificationCount,
              ),
              const SizedBox(width: 64),
              buildNavItem(
                index: 3,
                icon: Icons.sync_alt_rounded,
                label: 'Công nợ',
              ),
              buildNavItem(
                index: 4,
                icon: Icons.person_rounded,
                label: 'Cá nhân',
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget buildQuickAddFab() {
    return SizedBox(
      width: 56,
      height: 56,
      child: FloatingActionButton(
        heroTag: 'quick_add_expense',
        elevation: 0,
        highlightElevation: 0,
        backgroundColor: AppColors.primary,
        foregroundColor: Colors.white,
        shape: const CircleBorder(),
        onPressed: isOpeningQuickAddExpense ? null : openQuickAddExpense,
        child: AnimatedSwitcher(
          duration: const Duration(milliseconds: 180),
          child: isOpeningQuickAddExpense
              ? const SizedBox(
                  key: ValueKey('loading'),
                  width: 22,
                  height: 22,
                  child: CircularProgressIndicator(
                    strokeWidth: 2.5,
                    valueColor: AlwaysStoppedAnimation<Color>(
                      Colors.white,
                    ),
                  ),
                )
              : const Icon(
                  Icons.add_rounded,
                  key: ValueKey('add'),
                  size: 30,
                ),
        ),
      ),
    );
  }

  Widget buildCenterButton() {
    return Expanded(
      child: GestureDetector(
        onTap: openQuickAddExpense,
        behavior: HitTestBehavior.opaque,
        child: Transform.translate(
          offset: const Offset(0, -10),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              AnimatedContainer(
                duration: const Duration(milliseconds: 220),
                width: 58,
                height: 58,
                decoration: BoxDecoration(
                  color: AppColors.primary,
                  shape: BoxShape.circle,
                  boxShadow: [
                    BoxShadow(
                      color: AppColors.primary.withValues(alpha: 0.32),
                      blurRadius: 22,
                      offset: const Offset(0, 10),
                    ),
                  ],
                ),
                child: AnimatedSwitcher(
                  duration: const Duration(milliseconds: 180),
                  child: isOpeningQuickAddExpense
                      ? const SizedBox(
                          key: ValueKey('loading'),
                          width: 22,
                          height: 22,
                          child: CircularProgressIndicator(
                            strokeWidth: 2.6,
                            valueColor: AlwaysStoppedAnimation<Color>(
                              Colors.white,
                            ),
                          ),
                        )
                      : const Icon(
                          Icons.add_rounded,
                          key: ValueKey('add'),
                          color: Colors.white,
                          size: 34,
                        ),
                ),
              ),
              const SizedBox(height: 6),
              const Text(
                'Thêm',
                style: TextStyle(
                  color: AppColors.primary,
                  fontSize: 11,
                  fontWeight: FontWeight.w800,
                  letterSpacing: -0.1,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget buildNavItem({
    required int index,
    required IconData icon,
    required String label,
    int badgeCount = 0,
  }) {
    final isActive = currentIndex == index;

    return Expanded(
      child: GestureDetector(
        onTap: () => changeTab(index),
        behavior: HitTestBehavior.opaque,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Stack(
              clipBehavior: Clip.none,
              children: [
                AnimatedContainer(
                  duration: const Duration(milliseconds: 220),
                  padding: const EdgeInsets.all(7),
                  decoration: BoxDecoration(
                    color: isActive
                        ? AppColors.primary.withValues(alpha: 0.10)
                        : Colors.transparent,
                    borderRadius: BorderRadius.circular(14),
                  ),
                  child: Icon(
                    icon,
                    size: 21,
                    color: isActive ? AppColors.primary : AppColors.textLight,
                  ),
                ),
                if (badgeCount > 0)
                  Positioned(
                    top: -4,
                    right: -6,
                    child: Container(
                      constraints: const BoxConstraints(
                        minWidth: 19,
                        minHeight: 19,
                      ),
                      padding: const EdgeInsets.symmetric(horizontal: 5),
                      decoration: BoxDecoration(
                        color: Colors.red,
                        borderRadius: BorderRadius.circular(999),
                        border: Border.all(color: Colors.white, width: 2),
                      ),
                      child: Center(
                        child: Text(
                          badgeCount > 99 ? '99+' : badgeCount.toString(),
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 10,
                            fontWeight: FontWeight.w900,
                          ),
                        ),
                      ),
                    ),
                  ),
              ],
            ),
            const SizedBox(height: 3),
            AnimatedDefaultTextStyle(
              duration: const Duration(milliseconds: 220),
              style: TextStyle(
                fontSize: 10,
                height: 1.05,
                fontWeight: isActive ? FontWeight.w800 : FontWeight.w600,
                color: isActive ? AppColors.primary : AppColors.textLight,
                letterSpacing: 0,
              ),
              child: Text(label, maxLines: 1, overflow: TextOverflow.ellipsis),
            ),
            const SizedBox(height: 3),
            AnimatedContainer(
              duration: const Duration(milliseconds: 220),
              width: isActive ? 4 : 0,
              height: isActive ? 4 : 0,
              decoration: const BoxDecoration(
                color: AppColors.primary,
                shape: BoxShape.circle,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
