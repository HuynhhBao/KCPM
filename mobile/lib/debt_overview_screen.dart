import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'app_theme.dart';
import 'models/debt.dart';
import 'models/household.dart';
import 'services/api_service.dart';
import 'widgets/app_empty_state.dart';
import 'widgets/app_error_state.dart';
import 'widgets/app_loading_state.dart';
import 'debt_detail_screen.dart';

enum DebtFilter { all, owe, receive }

class DebtOverviewScreen extends StatefulWidget {
  const DebtOverviewScreen({super.key});

  @override
  State<DebtOverviewScreen> createState() => _DebtOverviewScreenState();
}

class _DebtOverviewScreenState extends State<DebtOverviewScreen> {
  bool isLoading = true;
  bool isRefreshing = false;
  bool isSubmittingPayment = false;

  String? errorMessage;
  String currentUserEmail = '';
  int currentUserId = 0;
  String? submittingDebtId;

  DebtFilter selectedFilter = DebtFilter.all;

  bool isLoadingPairDetail = false;
  String? loadingPairKey;

  List<_DebtPairItem> allDebtPairs = [];

  final Map<String, _DebtItem> debtItemsById = {};

  @override
  void initState() {
    super.initState();
    loadDebts();
  }

  Future<void> loadDebts({bool showLoading = true}) async {
    if (showLoading) {
      setState(() {
        isLoading = true;
        errorMessage = null;
      });
    }

    try {
      final profile = await ApiService.getProfile();
      final email = profile['email']?.toString() ?? '';
      final userId = readInt(profile['id'] ?? profile['user_id']);

      final householdResponse = await ApiService.getHouseholds();

      final households = householdResponse
          .whereType<Map>()
          .map((item) => Household.fromJson(Map<String, dynamic>.from(item)))
          .where((household) => household.isActive)
          .toList();

      final loadedPairs = <_DebtPairItem>[];
      final loadedDebtItemsById = <String, _DebtItem>{};

      for (final household in households) {
        final summary = await ApiService.getHouseholdMyDebtSummary(
          household.id,
        );

        final iOwe = readMapList(summary['i_owe']);
        final owedToMe = readMapList(summary['owed_to_me']);

        for (final item in iOwe) {
          loadedPairs.add(
            _DebtPairItem.fromSummary(
              household: household,
              json: item,
              direction: _DebtPairDirection.iOwe,
            ),
          );
        }

        for (final item in owedToMe) {
          loadedPairs.add(
            _DebtPairItem.fromSummary(
              household: household,
              json: item,
              direction: _DebtPairDirection.owedToMe,
            ),
          );
        }

        var page = 1;

        while (true) {
          final response = await ApiService.getHouseholdDebts(
            household.id,
            page: page,
          );

          final results = List<dynamic>.from(response['results'] ?? []);

          for (final item in results) {
            final debt = Debt.fromJson(Map<String, dynamic>.from(item));

            loadedDebtItemsById[debt.id] = _DebtItem(
              household: household,
              debt: debt,
            );
          }

          final next = response['next'];

          if (next == null || next.toString().trim().isEmpty) {
            break;
          }

          page++;

          if (page > 20) {
            break;
          }
        }
      }

      loadedPairs.sort((a, b) => b.amount.compareTo(a.amount));

      if (!mounted) return;

      setState(() {
        currentUserEmail = email.toLowerCase().trim();
        currentUserId = userId;
        allDebtPairs = loadedPairs;

        debtItemsById
          ..clear()
          ..addAll(loadedDebtItemsById);

        isLoading = false;
        isRefreshing = false;
        errorMessage = null;
      });
    } catch (e) {
      if (!mounted) return;

      setState(() {
        isLoading = false;
        isRefreshing = false;
        errorMessage = getErrorMessage(e);
      });
    }
  }

  Future<void> refreshDebts() async {
    if (isRefreshing) return;

    setState(() {
      isRefreshing = true;
    });

    await loadDebts(showLoading: false);
  }

  Future<void> markDebtPaid(Debt debt) async {
    if (isSubmittingPayment) return;

    setState(() {
      isSubmittingPayment = true;
      submittingDebtId = debt.id;
    });

    try {
      await ApiService.markDebtPaid(debt.id);

      if (!mounted) return;

      showSnackBar(
        debt.hasVirtualMember
            ? 'Đã đánh dấu thanh toán ngoài đời.'
            : 'Đã gửi yêu cầu xác nhận thanh toán.',
      );

      await loadDebts(showLoading: false);
    } catch (e) {
      if (!mounted) return;

      showSnackBar(getErrorMessage(e));
    } finally {
      if (mounted) {
        setState(() {
          isSubmittingPayment = false;
          submittingDebtId = null;
        });
      }
    }
  }

  Future<void> confirmPayment(Debt debt) async {
    if (isSubmittingPayment || debt.pendingPaymentId == null) {
      return;
    }

    setState(() {
      isSubmittingPayment = true;
      submittingDebtId = debt.id;
    });

    try {
      await ApiService.confirmPayment(debt.pendingPaymentId!);

      if (!mounted) return;

      showSnackBar('Đã xác nhận nhận tiền.');

      await loadDebts(showLoading: false);
    } catch (e) {
      if (!mounted) return;

      showSnackBar(getErrorMessage(e));
    } finally {
      if (mounted) {
        setState(() {
          isSubmittingPayment = false;
          submittingDebtId = null;
        });
      }
    }
  }

  Future<void> rejectPayment(Debt debt) async {
    if (isSubmittingPayment || debt.pendingPaymentId == null) {
      return;
    }

    setState(() {
      isSubmittingPayment = true;
      submittingDebtId = debt.id;
    });

    try {
      await ApiService.rejectPayment(debt.pendingPaymentId!);

      if (!mounted) return;

      showSnackBar('Đã từ chối yêu cầu thanh toán.');

      await loadDebts(showLoading: false);
    } catch (e) {
      if (!mounted) return;

      showSnackBar(getErrorMessage(e));
    } finally {
      if (mounted) {
        setState(() {
          isSubmittingPayment = false;
          submittingDebtId = null;
        });
      }
    }
  }

  void showSnackBar(String message) {
    ScaffoldMessenger.of(context).hideCurrentSnackBar();

    ScaffoldMessenger.of(
      context,
    ).showSnackBar(SnackBar(content: Text(message)));
  }

  List<_DebtPairItem> get visibleDebts {
    if (selectedFilter == DebtFilter.owe) {
      return allDebtPairs
          .where((item) => item.direction == _DebtPairDirection.iOwe)
          .toList();
    }

    if (selectedFilter == DebtFilter.receive) {
      return allDebtPairs
          .where((item) => item.direction == _DebtPairDirection.owedToMe)
          .toList();
    }

    return allDebtPairs;
  }

  double get totalOwe {
    return allDebtPairs
        .where((item) => item.direction == _DebtPairDirection.iOwe)
        .fold<double>(0, (sum, item) => sum + item.amount);
  }

  double get totalReceive {
    return allDebtPairs
        .where((item) => item.direction == _DebtPairDirection.owedToMe)
        .fold<double>(0, (sum, item) => sum + item.amount);
  }

  int readInt(dynamic value) {
    if (value == null) return 0;

    if (value is int) return value;

    return int.tryParse(value.toString()) ?? 0;
  }

  double readDouble(dynamic value) {
    if (value == null) return 0;

    if (value is num) {
      return value.toDouble();
    }

    return double.tryParse(value.toString()) ?? 0;
  }

  List<Map<String, dynamic>> readMapList(dynamic value) {
    if (value is! List) return [];

    return value
        .whereType<Map>()
        .map((item) => Map<String, dynamic>.from(item))
        .toList();
  }

  String getErrorMessage(Object error) {
    final message = error.toString();

    if (message.startsWith('Exception: ')) {
      return message.replaceFirst('Exception: ', '');
    }

    if (message.trim().isEmpty) {
      return 'Không thể tải danh sách công nợ';
    }

    return message;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        titleSpacing: 20,
        title: const Text('Công nợ'),
        actions: [
          IconButton(
            tooltip: 'Tải lại',
            onPressed: isLoading ? null : refreshDebts,
            icon: const Icon(Icons.refresh_rounded),
          ),
          const SizedBox(width: 8),
        ],
      ),
      body: buildBody(),
    );
  }

  Widget buildBody() {
    if (isLoading) {
      return const AppLoadingState(message: 'Đang tải công nợ...');
    }

    if (errorMessage != null) {
      return AppErrorState(message: errorMessage!, onRetry: loadDebts);
    }

    if (allDebtPairs.isEmpty) {
      return RefreshIndicator(
        onRefresh: refreshDebts,
        color: AppColors.primary,
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          children: const [
            SizedBox(height: 120),
            AppEmptyState(
              icon: Icons.verified_rounded,
              title: 'Không có công nợ',
              message:
                  'Hiện tại bạn chưa có khoản nợ nào cần trả hoặc cần nhận.',
            ),
          ],
        ),
      );
    }

    final debts = visibleDebts;

    return RefreshIndicator(
      onRefresh: refreshDebts,
      color: AppColors.primary,
      child: ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.fromLTRB(20, 12, 20, 120),
        children: [
          buildSummarySection(),
          const SizedBox(height: 18),
          buildFilterSection(),
          const SizedBox(height: 16),
          if (debts.isEmpty)
            Padding(
              padding: const EdgeInsets.only(top: 80),
              child: AppEmptyState(
                icon: selectedFilter == DebtFilter.owe
                    ? Icons.call_made_rounded
                    : Icons.call_received_rounded,
                title: selectedFilter == DebtFilter.owe
                    ? 'Không có khoản phải trả'
                    : 'Không có khoản được nhận',
                message: 'Bạn có thể đổi bộ lọc để xem các công nợ khác.',
              ),
            )
          else
            ...debts.map(
              (item) => Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: buildDebtCard(item),
              ),
            ),
        ],
      ),
    );
  }

  Widget buildSummarySection() {
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            AppColors.primaryDark,
            AppColors.primary,
            AppColors.primary.withValues(alpha: 0.82),
          ],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(28),
        boxShadow: [
          BoxShadow(
            color: AppColors.primary.withValues(alpha: 0.20),
            blurRadius: 28,
            offset: const Offset(0, 16),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Row(
            children: [
              Icon(Icons.sync_alt_rounded, color: Colors.white),
              SizedBox(width: 8),
              Text(
                'Tổng quan công nợ',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 18,
                  fontWeight: FontWeight.w900,
                ),
              ),
            ],
          ),
          const SizedBox(height: 18),
          Row(
            children: [
              Expanded(
                child: buildSummaryCard(
                  label: 'Bạn cần trả',
                  value: formatMoney(totalOwe),
                  icon: Icons.call_made_rounded,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: buildSummaryCard(
                  label: 'Bạn sẽ nhận',
                  value: formatMoney(totalReceive),
                  icon: Icons.call_received_rounded,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget buildSummaryCard({
    required String label,
    required String value,
    required IconData icon,
  }) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.14),
        borderRadius: BorderRadius.circular(22),
        border: Border.all(color: Colors.white.withValues(alpha: 0.18)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: Colors.white, size: 22),
          const SizedBox(height: 10),
          Text(
            label,
            style: TextStyle(
              color: Colors.white.withValues(alpha: 0.82),
              fontSize: 13,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            value,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 20,
              fontWeight: FontWeight.w900,
              letterSpacing: -0.4,
            ),
          ),
        ],
      ),
    );
  }

  Widget buildFilterSection() {
    return Container(
      padding: const EdgeInsets.all(6),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: AppColors.borderStrong),
        boxShadow: [
          BoxShadow(
            color: AppColors.primaryDark.withValues(alpha: 0.035),
            blurRadius: 16,
            offset: const Offset(0, 8),
          ),
        ],
      ),
      child: Row(
        children: [
          buildFilterItem(filter: DebtFilter.all, label: 'Tất cả'),
          buildFilterItem(filter: DebtFilter.owe, label: 'Phải trả'),
          buildFilterItem(filter: DebtFilter.receive, label: 'Được nhận'),
        ],
      ),
    );
  }

  Widget buildFilterItem({required DebtFilter filter, required String label}) {
    final isSelected = selectedFilter == filter;

    return Expanded(
      child: GestureDetector(
        onTap: () {
          setState(() {
            selectedFilter = filter;
          });
        },
        behavior: HitTestBehavior.opaque,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 180),
          padding: const EdgeInsets.symmetric(vertical: 11),
          decoration: BoxDecoration(
            color: isSelected ? AppColors.primary : Colors.transparent,
            borderRadius: BorderRadius.circular(15),
          ),
          child: Text(
            label,
            textAlign: TextAlign.center,
            style: TextStyle(
              color: isSelected ? Colors.white : AppColors.textLight,
              fontSize: 13,
              fontWeight: FontWeight.w900,
            ),
          ),
        ),
      ),
    );
  }

  Widget buildDebtCard(_DebtPairItem item) {
    final isOwe = item.direction == _DebtPairDirection.iOwe;

    final isLoadingThis = isLoadingPairDetail && loadingPairKey == item.key;

    final title = isOwe
        ? 'Bạn nợ ${item.otherName}'
        : '${item.otherName} nợ bạn';

    final subtitle = item.expenseCount <= 0
        ? item.household.name
        : '${item.expenseCount} khoản phát sinh • ${item.household.name}';

    return InkWell(
      onTap: isLoadingPairDetail ? null : () => showDebtDetail(item),
      borderRadius: BorderRadius.circular(24),
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(24),
          border: Border.all(color: AppColors.border),
          boxShadow: [
            BoxShadow(
              color: AppColors.primaryDark.withValues(alpha: 0.04),
              blurRadius: 16,
              offset: const Offset(0, 8),
            ),
          ],
        ),
        child: Row(
          children: [
            buildAvatar(
              name: item.otherName,
              avatarUrl: item.otherAvatar,
              isVirtual: item.isVirtual,
              fallbackIcon: isOwe
                  ? Icons.call_made_rounded
                  : Icons.call_received_rounded,
              isOwe: isOwe,
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          title,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(
                            color: AppColors.textDark,
                            fontSize: 16,
                            fontWeight: FontWeight.w900,
                            letterSpacing: -0.2,
                          ),
                        ),
                      ),
                      if (item.isVirtual)
                        Container(
                          margin: const EdgeInsets.only(left: 8),
                          padding: const EdgeInsets.symmetric(
                            horizontal: 8,
                            vertical: 3,
                          ),
                          decoration: BoxDecoration(
                            color: AppColors.primary.withValues(alpha: 0.10),
                            borderRadius: BorderRadius.circular(999),
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
                  const SizedBox(height: 5),
                  Text(
                    subtitle,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      color: AppColors.textLight,
                      fontSize: 13,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 12),
            Column(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Text(
                  formatMoney(item.amount),
                  style: TextStyle(
                    color: isOwe ? Colors.redAccent : AppColors.primary,
                    fontSize: 16,
                    fontWeight: FontWeight.w900,
                    letterSpacing: -0.2,
                  ),
                ),
                const SizedBox(height: 6),
                if (isLoadingThis)
                  const SizedBox(
                    width: 18,
                    height: 18,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      color: AppColors.primary,
                    ),
                  )
                else
                  const Icon(
                    Icons.chevron_right_rounded,
                    color: AppColors.textLight,
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  String buildDebtSubtitle({required Debt debt, required bool isOwe}) {
    if (debt.hasPendingPayment) {
      return isOwe
          ? 'Đang chờ người nhận xác nhận'
          : 'Đang chờ bạn xác nhận thanh toán';
    }

    if (debt.hasVirtualMember) {
      return 'Công nợ với thành viên ảo • xác nhận ngoài đời';
    }

    if (debt.expenseTitle.trim().isNotEmpty) {
      return 'Khoản chi: ${debt.expenseTitle}';
    }

    return isOwe
        ? 'Cần chuyển cho ${displayName(debt.toUserName, debt.toUserEmail)}'
        : 'Chờ ${displayName(debt.fromUserName, debt.fromUserEmail)} thanh toán';
  }

  Widget buildAvatar({
    required String name,
    required String avatarUrl,
    required bool isVirtual,
    required IconData fallbackIcon,
    required bool isOwe,
  }) {
    final letter = name.trim().isNotEmpty ? name.trim()[0].toUpperCase() : '';

    final resolvedAvatar = avatarUrl.trim().isNotEmpty
        ? ApiService.resolveMediaUrl(avatarUrl.trim())
        : '';

    Widget fallbackAvatar() {
      return Container(
        width: 52,
        height: 52,
        decoration: BoxDecoration(
          color: isVirtual
              ? const Color(0xFFE0F2FE)
              : isOwe
              ? Colors.redAccent.withValues(alpha: 0.10)
              : AppColors.primary.withValues(alpha: 0.10),
          borderRadius: BorderRadius.circular(20),
        ),
        child: Center(
          child: isVirtual
              ? const Icon(
                  Icons.person_outline_rounded,
                  color: Color(0xFF0284C7),
                )
              : letter.isEmpty
              ? Icon(
                  fallbackIcon,
                  color: isOwe ? Colors.redAccent : AppColors.primary,
                )
              : Text(
                  letter,
                  style: TextStyle(
                    color: isOwe ? Colors.redAccent : AppColors.primary,
                    fontSize: 20,
                    fontWeight: FontWeight.w900,
                  ),
                ),
        ),
      );
    }

    if (isVirtual || resolvedAvatar.isEmpty) {
      return fallbackAvatar();
    }

    return ClipRRect(
      borderRadius: BorderRadius.circular(20),
      child: SizedBox(
        width: 52,
        height: 52,
        child: Image.network(
          resolvedAvatar,
          key: ValueKey(resolvedAvatar),
          fit: BoxFit.cover,
          errorBuilder: (_, _, _) {
            return fallbackAvatar();
          },
        ),
      ),
    );
  }

  Future<void> showDebtDetail(_DebtPairItem pair) async {
    if (isLoadingPairDetail) return;

    setState(() {
      isLoadingPairDetail = true;
      loadingPairKey = pair.key;
    });

    try {
      final response = await ApiService.getHouseholdMyDebtDetail(
        householdId: pair.household.id,
        otherUserId: pair.otherUserId,
      );

      if (!mounted) return;

      await Navigator.of(context).push(
        MaterialPageRoute(
          builder: (_) => DebtDetailScreen(
            householdId: pair.household.id,
            otherUserId: pair.otherUserId,
            isVirtualMode: false,
            initialDetail: Map<String, dynamic>.from(response),
          ),
        ),
      );

      if (mounted) {
        await loadDebts(showLoading: false);
      }
    } catch (e) {
      if (!mounted) return;

      showSnackBar(getErrorMessage(e));
    } finally {
      if (mounted) {
        setState(() {
          isLoadingPairDetail = false;
          loadingPairKey = null;
        });
      }
    }
  }

  Widget buildPairDebtDetailSheet({
    required BuildContext sheetContext,
    required _DebtPairItem pair,
    required Map<String, dynamic> detail,
    required List<_DebtDetailRow> rows,
  }) {
    final otherName = detail['other_name']?.toString() ?? pair.otherName;

    final netDirection = detail['net_direction']?.toString() ?? '';

    final netAmount = readDouble(detail['net_amount']);

    final isIOwe = netDirection == 'i_owe';
    final isOwedToMe = netDirection == 'owed_to_me';

    String summaryText;

    if (isIOwe) {
      summaryText = 'Bạn cần trả $otherName ${formatMoney(netAmount)}';
    } else if (isOwedToMe) {
      summaryText = '$otherName cần trả bạn ${formatMoney(netAmount)}';
    } else {
      summaryText = 'Bạn và $otherName không còn chênh lệch công nợ.';
    }

    final summaryColor = isIOwe ? Colors.redAccent : AppColors.primary;

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
        constraints: BoxConstraints(
          maxHeight: MediaQuery.of(context).size.height * 0.86,
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
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
                border: Border.all(color: summaryColor.withValues(alpha: 0.16)),
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
            if (rows.isEmpty)
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
                  itemCount: rows.length,
                  separatorBuilder: (_, _) => const SizedBox(height: 12),
                  itemBuilder: (_, index) {
                    return buildDebtDetailExpenseCard(
                      sheetContext: sheetContext,
                      row: rows[index],
                      otherName: otherName,
                    );
                  },
                ),
              ),
          ],
        ),
      ),
    );
  }

  Widget buildDebtDetailExpenseCard({
    required BuildContext sheetContext,
    required _DebtDetailRow row,
    required String otherName,
  }) {
    final rawDebtItem = debtItemsById[row.debtId];

    final isIOwe = row.direction == 'i_owe';

    final color = isIOwe ? Colors.redAccent : AppColors.primary;

    final label = isIOwe ? 'Bạn nợ $otherName' : '$otherName nợ bạn';

    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppColors.background,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
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
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      row.expenseTitle,
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
                        if (row.payerName.isNotEmpty)
                          'Người trả: ${row.payerName}',
                        if (row.expenseDate.isNotEmpty) row.expenseDate,
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
                formatMoney(row.amount),
                style: TextStyle(
                  color: color,
                  fontSize: 14,
                  fontWeight: FontWeight.w900,
                ),
              ),
            ],
          ),

          if (rawDebtItem != null) ...[
            const SizedBox(height: 12),
            buildBankInfo(rawDebtItem.debt),
            const SizedBox(height: 12),
            buildDetailPaymentActions(
              sheetContext: sheetContext,
              item: rawDebtItem,
            ),
          ],
        ],
      ),
    );
  }

  Widget buildDetailPaymentActions({
    required BuildContext sheetContext,
    required _DebtItem item,
  }) {
    final debt = item.debt;

    final isOwe = item.isCurrentUserDebtor(currentUserEmail);

    final isReceiver = item.isCurrentUserReceiver(currentUserEmail);

    final isSubmitting = isSubmittingPayment && submittingDebtId == debt.id;

    if (debt.hasPendingPayment) {
      if (isReceiver) {
        return Row(
          children: [
            Expanded(
              child: OutlinedButton.icon(
                onPressed: isSubmitting
                    ? null
                    : () async {
                        Navigator.pop(sheetContext);
                        await rejectPayment(debt);
                      },
                icon: const Icon(Icons.close_rounded),
                label: const Text('Từ chối'),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: FilledButton.icon(
                onPressed: isSubmitting
                    ? null
                    : () async {
                        Navigator.pop(sheetContext);
                        await confirmPayment(debt);
                      },
                icon: isSubmitting
                    ? const SizedBox(
                        width: 18,
                        height: 18,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          color: Colors.white,
                        ),
                      )
                    : const Icon(Icons.check_rounded),
                label: const Text('Xác nhận'),
              ),
            ),
          ],
        );
      }

      return Container(
        width: double.infinity,
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: AppColors.primary.withValues(alpha: 0.08),
          borderRadius: BorderRadius.circular(18),
          border: Border.all(color: AppColors.primary.withValues(alpha: 0.18)),
        ),
        child: const Text(
          'Đang chờ người nhận xác nhận thanh toán.',
          style: TextStyle(
            color: AppColors.primary,
            fontWeight: FontWeight.w800,
            height: 1.35,
          ),
        ),
      );
    }

    if (debt.hasVirtualMember && debt.canMarkPaid) {
      return SizedBox(
        width: double.infinity,
        height: 52,
        child: FilledButton.icon(
          onPressed: isSubmitting
              ? null
              : () async {
                  Navigator.pop(sheetContext);
                  await markDebtPaid(debt);
                },
          icon: isSubmitting
              ? const SizedBox(
                  width: 18,
                  height: 18,
                  child: CircularProgressIndicator(
                    strokeWidth: 2,
                    color: Colors.white,
                  ),
                )
              : const Icon(Icons.check_circle_rounded),
          label: Text(
            isSubmitting ? 'Đang xử lý...' : 'Đánh dấu đã thanh toán ngoài đời',
          ),
        ),
      );
    }

    if (isOwe) {
      return Column(
        children: [
          SizedBox(
            width: double.infinity,
            height: 52,
            child: OutlinedButton.icon(
              onPressed: () => showPaymentQrSheet(
                parentSheetContext: sheetContext,
                debt: debt,
              ),
              icon: const Icon(Icons.qr_code_rounded),
              label: const Text('Thanh toán / QR'),
            ),
          ),
          const SizedBox(height: 10),
          SizedBox(
            width: double.infinity,
            height: 52,
            child: FilledButton.icon(
              onPressed: isSubmitting
                  ? null
                  : () async {
                      Navigator.pop(sheetContext);
                      await markDebtPaid(debt);
                    },
              icon: isSubmitting
                  ? const SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        color: Colors.white,
                      ),
                    )
                  : const Icon(Icons.payments_rounded),
              label: Text(isSubmitting ? 'Đang gửi...' : 'Tôi đã thanh toán'),
            ),
          ),
        ],
      );
    }

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: AppColors.border),
      ),
      child: const Text(
        'Chờ người nợ gửi yêu cầu xác nhận thanh toán.',
        style: TextStyle(
          color: AppColors.textLight,
          fontWeight: FontWeight.w700,
          height: 1.35,
        ),
      ),
    );
  }

  String buildVietQrUrl(Debt debt) {
    final encodedMessage = Uri.encodeComponent(
      'Thanh toan Chung Vi - ${debt.expenseTitle}',
    );

    final encodedAccountName = Uri.encodeComponent(debt.bankAccountHolder);

    return 'https://img.vietqr.io/image/'
        '${debt.bankName}-${debt.bankAccountNumber}-compact2.png'
        '?amount=${debt.amount.toInt()}'
        '&addInfo=$encodedMessage'
        '&accountName=$encodedAccountName';
  }

  Future<void> showPaymentQrSheet({
    required BuildContext parentSheetContext,
    required Debt debt,
  }) async {
    if (debt.bankName.trim().isEmpty || debt.bankAccountNumber.trim().isEmpty) {
      showSnackBar('Người nhận chưa cập nhật thông tin ngân hàng.');
      return;
    }

    final qrUrl = buildVietQrUrl(debt);

    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (qrContext) {
        return SafeArea(
          child: Container(
            margin: const EdgeInsets.all(14),
            padding: const EdgeInsets.fromLTRB(18, 16, 18, 18),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(28),
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
                const Text(
                  'QR thanh toán',
                  style: TextStyle(
                    color: AppColors.textDark,
                    fontSize: 20,
                    fontWeight: FontWeight.w900,
                  ),
                ),
                const SizedBox(height: 14),
                ClipRRect(
                  borderRadius: BorderRadius.circular(22),
                  child: Image.network(
                    qrUrl,
                    height: 260,
                    width: 260,
                    fit: BoxFit.cover,
                    errorBuilder: (_, _, _) {
                      return Container(
                        height: 220,
                        width: double.infinity,
                        alignment: Alignment.center,
                        decoration: BoxDecoration(
                          color: AppColors.background,
                          borderRadius: BorderRadius.circular(22),
                        ),
                        child: const Text(
                          'Không thể tải QR. Hãy kiểm tra mã ngân hàng và số tài khoản.',
                          textAlign: TextAlign.center,
                          style: TextStyle(
                            color: AppColors.textLight,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      );
                    },
                  ),
                ),
                const SizedBox(height: 16),
                buildBankRow(label: 'Ngân hàng', value: debt.bankName),
                buildBankRow(
                  label: 'Chủ tài khoản',
                  value: debt.bankAccountHolder,
                ),
                buildBankRow(
                  label: 'Số tài khoản',
                  value: debt.bankAccountNumber,
                  canCopy: true,
                ),
                buildBankRow(label: 'Số tiền', value: formatMoney(debt.amount)),
                const SizedBox(height: 16),
                Row(
                  children: [
                    Expanded(
                      child: OutlinedButton(
                        onPressed: () {
                          Navigator.pop(qrContext);
                        },
                        child: const Text('Đóng'),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: FilledButton.icon(
                        onPressed: () async {
                          Navigator.pop(qrContext);
                          Navigator.pop(parentSheetContext);

                          await markDebtPaid(debt);
                        },
                        icon: const Icon(Icons.check_rounded),
                        label: const Text('Đã thanh toán'),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  Widget buildPaymentActionSection(_DebtItem item) {
    final debt = item.debt;

    final isOwe = item.isCurrentUserDebtor(currentUserEmail);

    final isReceiver = item.isCurrentUserReceiver(currentUserEmail);

    final isSubmitting = isSubmittingPayment && submittingDebtId == debt.id;

    if (debt.hasPendingPayment) {
      if (isReceiver) {
        return Row(
          children: [
            Expanded(
              child: OutlinedButton.icon(
                onPressed: isSubmitting ? null : () => rejectPayment(debt),
                icon: const Icon(Icons.close_rounded),
                label: const Text('Từ chối'),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: FilledButton.icon(
                onPressed: isSubmitting ? null : () => confirmPayment(debt),
                icon: isSubmitting
                    ? const SizedBox(
                        width: 18,
                        height: 18,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          color: Colors.white,
                        ),
                      )
                    : const Icon(Icons.check_rounded),
                label: const Text('Xác nhận'),
              ),
            ),
          ],
        );
      }

      return Container(
        width: double.infinity,
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: AppColors.primary.withValues(alpha: 0.08),
          borderRadius: BorderRadius.circular(18),
          border: Border.all(color: AppColors.primary.withValues(alpha: 0.18)),
        ),
        child: const Row(
          children: [
            Icon(Icons.hourglass_top_rounded, color: AppColors.primary),
            SizedBox(width: 10),
            Expanded(
              child: Text(
                'Đang chờ người nhận xác nhận thanh toán.',
                style: TextStyle(
                  color: AppColors.primary,
                  fontWeight: FontWeight.w800,
                  height: 1.35,
                ),
              ),
            ),
          ],
        ),
      );
    }

    if (debt.hasVirtualMember && debt.canMarkPaid) {
      final label = isOwe && debt.toUserIsVirtual
          ? 'Đã thanh toán ngoài đời'
          : (!isOwe && debt.fromUserIsVirtual
                ? 'Đã nhận ngoài đời'
                : 'Đánh dấu đã thanh toán ngoài đời');

      return SizedBox(
        width: double.infinity,
        height: 52,
        child: FilledButton.icon(
          onPressed: isSubmitting ? null : () => markDebtPaid(debt),
          icon: isSubmitting
              ? const SizedBox(
                  width: 18,
                  height: 18,
                  child: CircularProgressIndicator(
                    strokeWidth: 2,
                    color: Colors.white,
                  ),
                )
              : const Icon(Icons.check_circle_rounded),
          label: Text(isSubmitting ? 'Đang xử lý...' : label),
        ),
      );
    }

    if (debt.hasVirtualMember) {
      return Container(
        width: double.infinity,
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: AppColors.background,
          borderRadius: BorderRadius.circular(18),
          border: Border.all(color: AppColors.border),
        ),
        child: const Text(
          'Công nợ này liên quan thành viên ảo. Người dùng thật trong khoản nợ có thể đánh dấu đã thanh toán ngoài đời.',
          style: TextStyle(
            color: AppColors.textLight,
            fontWeight: FontWeight.w700,
            height: 1.35,
          ),
        ),
      );
    }

    if (isOwe) {
      return SizedBox(
        width: double.infinity,
        height: 52,
        child: FilledButton.icon(
          onPressed: isSubmitting ? null : () => markDebtPaid(debt),
          icon: isSubmitting
              ? const SizedBox(
                  width: 18,
                  height: 18,
                  child: CircularProgressIndicator(
                    strokeWidth: 2,
                    color: Colors.white,
                  ),
                )
              : const Icon(Icons.payments_rounded),
          label: Text(isSubmitting ? 'Đang gửi...' : 'Tôi đã thanh toán'),
        ),
      );
    }

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppColors.background,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: AppColors.border),
      ),
      child: const Text(
        'Chờ người nợ gửi yêu cầu xác nhận thanh toán.',
        style: TextStyle(
          color: AppColors.textLight,
          fontWeight: FontWeight.w700,
          height: 1.35,
        ),
      ),
    );
  }

  Widget buildPendingNotice({required bool isOwe}) {
    return Container(
      width: double.infinity,
      margin: const EdgeInsets.only(top: 6),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppColors.primary.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.primary.withValues(alpha: 0.18)),
      ),
      child: Text(
        isOwe
            ? 'Bạn đã báo thanh toán. Công nợ sẽ được đóng sau khi người nhận xác nhận.'
            : 'Người nợ đã báo thanh toán. Hãy xác nhận nếu bạn đã nhận tiền.',
        style: const TextStyle(
          color: AppColors.primary,
          fontSize: 13,
          fontWeight: FontWeight.w800,
          height: 1.4,
        ),
      ),
    );
  }

  Widget buildPaymentActions({
    required BuildContext sheetContext,
    required Debt debt,
    required bool isOwe,
  }) {
    return const SizedBox.shrink();
  }

  Widget buildDetailRow({
    required IconData icon,
    required String label,
    required String value,
  }) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 11),
      child: Row(
        children: [
          Icon(icon, color: AppColors.primary, size: 20),
          const SizedBox(width: 10),
          SizedBox(
            width: 92,
            child: Text(
              label,
              style: const TextStyle(
                color: AppColors.textLight,
                fontSize: 13,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
          Expanded(
            child: Text(
              value.trim().isEmpty ? 'Chưa có' : value,
              textAlign: TextAlign.right,
              style: const TextStyle(
                color: AppColors.textDark,
                fontSize: 14,
                fontWeight: FontWeight.w900,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget buildBankInfo(Debt debt) {
    if (debt.toUserIsVirtual) {
      return Container(
        width: double.infinity,
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: AppColors.background,
          borderRadius: BorderRadius.circular(18),
          border: Border.all(color: AppColors.border),
        ),
        child: const Text(
          'Người nhận là thành viên ảo, hãy thanh toán ngoài đời theo thỏa thuận nhóm.',
          style: TextStyle(
            color: AppColors.textLight,
            fontWeight: FontWeight.w700,
            height: 1.4,
          ),
        ),
      );
    }

    final hasBankInfo =
        debt.bankName.trim().isNotEmpty ||
        debt.bankAccountNumber.trim().isNotEmpty ||
        debt.bankAccountHolder.trim().isNotEmpty;

    if (!hasBankInfo) {
      return Container(
        width: double.infinity,
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: AppColors.background,
          borderRadius: BorderRadius.circular(18),
          border: Border.all(color: AppColors.border),
        ),
        child: const Text(
          'Người nhận chưa cập nhật thông tin ngân hàng.',
          style: TextStyle(
            color: AppColors.textLight,
            fontWeight: FontWeight.w700,
            height: 1.4,
          ),
        ),
      );
    }

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppColors.background,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        children: [
          buildBankRow(label: 'Ngân hàng', value: debt.bankName),
          buildBankRow(label: 'Chủ tài khoản', value: debt.bankAccountHolder),
          buildBankRow(
            label: 'Số tài khoản',
            value: debt.bankAccountNumber,
            canCopy: debt.bankAccountNumber.trim().isNotEmpty,
          ),
        ],
      ),
    );
  }

  Widget buildBankRow({
    required String label,
    required String value,
    bool canCopy = false,
  }) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 9),
      child: Row(
        children: [
          SizedBox(
            width: 105,
            child: Text(
              label,
              style: const TextStyle(
                color: AppColors.textLight,
                fontSize: 13,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
          Expanded(
            child: Text(
              value.trim().isEmpty ? 'Chưa có' : value,
              textAlign: TextAlign.right,
              style: const TextStyle(
                color: AppColors.textDark,
                fontSize: 14,
                fontWeight: FontWeight.w900,
              ),
            ),
          ),
          if (canCopy) ...[
            const SizedBox(width: 8),
            InkWell(
              borderRadius: BorderRadius.circular(10),
              onTap: () async {
                await Clipboard.setData(ClipboardData(text: value));

                if (!mounted) return;

                ScaffoldMessenger.of(context).hideCurrentSnackBar();

                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('Đã sao chép số tài khoản')),
                );
              },
              child: const Padding(
                padding: EdgeInsets.all(6),
                child: Icon(
                  Icons.copy_rounded,
                  color: AppColors.primary,
                  size: 18,
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }

  String displayName(String name, String email) {
    if (name.trim().isNotEmpty) {
      return name.trim();
    }

    if (email.trim().isNotEmpty) {
      return email.trim();
    }

    return 'Người dùng';
  }

  String formatMoney(double value) {
    final number = value.round().toString();

    final formatted = number.replaceAllMapped(
      RegExp(r'(\d{1,3})(?=(\d{3})+(?!\d))'),
      (match) => '${match[1]}.',
    );

    return '$formattedđ';
  }
}

enum _DebtPairDirection { iOwe, owedToMe }

class _DebtPairItem {
  final Household household;
  final int otherUserId;
  final String otherName;
  final String otherEmail;
  final String otherAvatar;
  final bool isVirtual;
  final double amount;
  final int expenseCount;
  final _DebtPairDirection direction;

  _DebtPairItem({
    required this.household,
    required this.otherUserId,
    required this.otherName,
    required this.otherEmail,
    required this.otherAvatar,
    required this.isVirtual,
    required this.amount,
    required this.expenseCount,
    required this.direction,
  });

  String get key {
    return '${household.id}-$otherUserId-${direction.name}';
  }

  factory _DebtPairItem.fromSummary({
    required Household household,
    required Map<String, dynamic> json,
    required _DebtPairDirection direction,
  }) {
    final rawAmount = json['amount'];
    final rawExpenseCount = json['expense_count'];
    final rawOtherUserId = json['other_user_id'];

    return _DebtPairItem(
      household: household,
      otherUserId: int.tryParse(rawOtherUserId.toString()) ?? 0,
      otherName: json['other_name']?.toString().trim().isNotEmpty == true
          ? json['other_name'].toString()
          : 'Thành viên',
      otherEmail: json['other_email']?.toString() ?? '',
      otherAvatar: json['other_avatar']?.toString() ?? '',
      isVirtual: json['is_virtual'] == true,
      amount: double.tryParse(rawAmount.toString()) ?? 0,
      expenseCount: int.tryParse(rawExpenseCount.toString()) ?? 0,
      direction: direction,
    );
  }
}

class _DebtDetailRow {
  final String debtId;
  final String expenseId;
  final String expenseTitle;
  final String expenseDate;
  final String payerName;
  final String direction;
  final double amount;

  _DebtDetailRow({
    required this.debtId,
    required this.expenseId,
    required this.expenseTitle,
    required this.expenseDate,
    required this.payerName,
    required this.direction,
    required this.amount,
  });
}

class _DebtItem {
  final Household household;
  final Debt debt;

  _DebtItem({required this.household, required this.debt});

  bool isCurrentUserDebtor(String email) {
    return debt.fromUserEmail.toLowerCase().trim() ==
        email.toLowerCase().trim();
  }

  bool isCurrentUserReceiver(String email) {
    return debt.toUserEmail.toLowerCase().trim() == email.toLowerCase().trim();
  }
}
