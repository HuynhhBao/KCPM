import 'package:flutter/material.dart';

import 'app_theme.dart';
import 'create_household_screen.dart';
import 'household_detail_screen.dart';
import 'models/household.dart';
import 'services/api_service.dart';
import 'widgets/app_empty_state.dart';
import 'widgets/app_error_state.dart';
import 'widgets/app_loading_state.dart';
import 'widgets/home_fintech_widgets.dart';
import 'join_household_screen.dart';

class HomeScreen extends StatefulWidget {
  final VoidCallback? onQuickAddExpense;
  final VoidCallback? onOpenDebts;
  final VoidCallback? onOpenActivities;

  const HomeScreen({
    super.key,
    this.onQuickAddExpense,
    this.onOpenDebts,
    this.onOpenActivities,
  });

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  bool isLoading = true;
  String? errorMessage;

  List<Household> households = [];
  List<Household> filteredHouseholds = [];

  final searchController = TextEditingController();

  String currentEmail = '';

  double totalOwe = 0;
  double totalReceive = 0;

  final List<dynamic> recentActivities = [];
  String? recentActivityError;

  final Map<String, double> groupOweMap = {};
  final Map<String, double> groupReceiveMap = {};
  final Map<String, dynamic> householdSummaryMap = {};

  @override
  void initState() {
    super.initState();
    searchController.addListener(filterHouseholds);
    loadData();
  }

  @override
  void dispose() {
    searchController.dispose();
    super.dispose();
  }

  Future<void> loadData() async {
    try {
      setState(() {
        isLoading = true;
        errorMessage = null;
      });

      final savedEmail = await ApiService.getSavedEmail();
      currentEmail = savedEmail ?? '';

      final householdData = await ApiService.getHouseholds();

      final loadedHouseholds = householdData
          .map<Household>(
            (json) => Household.fromJson(Map<String, dynamic>.from(json)),
          )
          .toList();

      final summaries = await ApiService.getHouseholdSummaries();

      double owe = 0;
      double receive = 0;

      groupOweMap.clear();
      groupReceiveMap.clear();
      householdSummaryMap.clear();

      for (final item in summaries) {
        final summary = Map<String, dynamic>.from(item);

        final householdId = summary['id']?.toString() ?? '';

        final rawGroupOwe =
            double.tryParse(summary['total_owe']?.toString() ?? '0') ?? 0;

        final rawGroupReceive =
            double.tryParse(summary['total_receive']?.toString() ?? '0') ?? 0;
        final groupNet = rawGroupReceive - rawGroupOwe;

        double displayGroupOwe = 0;
        double displayGroupReceive = 0;

        if (groupNet > 0) {
          displayGroupReceive = groupNet;
          receive += groupNet;
        } else if (groupNet < 0) {
          displayGroupOwe = groupNet.abs();
          owe += groupNet.abs();
        }

        groupOweMap[householdId] = displayGroupOwe;
        groupReceiveMap[householdId] = displayGroupReceive;

        householdSummaryMap[householdId] = summary;
      }

      if (!mounted) return;

      setState(() {
        households = loadedHouseholds;
        filteredHouseholds = loadedHouseholds;
        totalOwe = owe;
        totalReceive = receive;
        isLoading = false;
      });
    } catch (e) {
      debugPrint(e.toString());

      if (!mounted) return;

      setState(() {
        errorMessage = 'Không thể tải dữ liệu trang chủ';
        isLoading = false;
      });
    }
  }

  void filterHouseholds() {
    final keyword = searchController.text.trim().toLowerCase();

    if (keyword.isEmpty) {
      setState(() {
        filteredHouseholds = households;
      });
      return;
    }

    setState(() {
      filteredHouseholds = households.where((household) {
        return household.name.toLowerCase().contains(keyword) ||
            household.description.toLowerCase().contains(keyword);
      }).toList();
    });
  }

  String formatMoney(double amount) {
    return amount
        .toStringAsFixed(0)
        .replaceAllMapped(RegExp(r'\B(?=(\d{3})+(?!\d))'), (match) => '.');
  }

  String moneyText(double amount) => '${formatMoney(amount)}đ';

  String get greetingName {
    final email = currentEmail.trim();
    if (email.isEmpty) return 'bạn';

    final localPart = email.split('@').first.trim();
    if (localPart.isEmpty) return 'bạn';

    return localPart;
  }

  String get avatarInitial {
    final name = greetingName.trim();
    if (name.isEmpty || name == 'bạn') return 'C';

    return name.characters.first.toUpperCase();
  }

  bool get hasGroups => households.isNotEmpty;

  bool get hasPayableDebt => totalOwe > 0;

  bool get hasReceivableDebt => totalReceive > 0;

  double get heroAmount {
    if (hasPayableDebt) return totalOwe;
    if (hasReceivableDebt) return totalReceive;
    return 0;
  }

  String get heroTitle {
    if (hasPayableDebt) return 'Bạn có khoản cần trả';
    if (hasReceivableDebt) return 'Bạn đang chờ nhận tiền';
    return 'Các nhóm đang cân bằng';
  }

  double householdAttentionAmount(Household household) {
    final owe = groupOweMap[household.id] ?? 0;
    final receive = groupReceiveMap[household.id] ?? 0;

    return owe > receive ? owe : receive;
  }

  List<Household> get priorityHouseholds {
    final sorted = [...households];

    sorted.sort((a, b) {
      final amountCompare = householdAttentionAmount(
        b,
      ).compareTo(householdAttentionAmount(a));

      if (amountCompare != 0) return amountCompare;

      return a.name.toLowerCase().compareTo(b.name.toLowerCase());
    });

    return sorted.take(4).toList();
  }

  Future<void> openCreateHousehold() async {
    await Navigator.push(
      context,
      MaterialPageRoute(builder: (_) => const CreateHouseholdScreen()),
    );

    await loadData();
  }

  Future<void> openJoinHousehold() async {
    await Navigator.push(
      context,
      MaterialPageRoute(builder: (_) => const JoinHouseholdScreen()),
    );

    await loadData();
  }

  void openQuickAddExpense() {
    if (widget.onQuickAddExpense != null) {
      widget.onQuickAddExpense!();
      return;
    }

    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Dùng nút + để thêm khoản chi')),
    );
  }

  void openDebtOverview() {
    widget.onOpenDebts?.call();
  }

  void openActivities() {
    widget.onOpenActivities?.call();
  }

  Widget buildHeader() {
    return Row(
      children: [
        Container(
          width: 50,
          height: 50,
          padding: const EdgeInsets.all(4),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(18),
          ),
          child: ClipRRect(
            borderRadius: BorderRadius.circular(14),
            child: Image.asset('assets/images/logo.jpg', fit: BoxFit.cover),
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Chào $greetingName',
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(
                  color: AppColors.textDark,
                  fontSize: 22,
                  fontWeight: FontWeight.w900,
                  letterSpacing: 0,
                  height: 1.05,
                ),
              ),
              const SizedBox(height: 5),
              const Text(
                'Cùng xem ví nhóm hôm nay',
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                  color: AppColors.textLight,
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
        ),
        const SizedBox(width: 10),
        Material(
          color: Colors.white,
          borderRadius: BorderRadius.circular(16),
          child: InkWell(
            onTap: openActivities,
            borderRadius: BorderRadius.circular(16),
            child: const SizedBox(
              width: 44,
              height: 44,
              child: Icon(
                Icons.notifications_none_rounded,
                color: AppColors.textDark,
              ),
            ),
          ),
        ),
        const SizedBox(width: 8),
        Container(
          width: 44,
          height: 44,
          decoration: BoxDecoration(
            color: AppColors.primary,
            borderRadius: BorderRadius.circular(16),
          ),
          alignment: Alignment.center,
          child: Text(
            avatarInitial,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 16,
              fontWeight: FontWeight.w900,
            ),
          ),
        ),
      ],
    );
  }

  Widget buildSummaryCard() {
    final needToPay = totalOwe > totalReceive ? totalOwe - totalReceive : 0.0;
    const softDanger = Color(0xFFB94355);
    const softSuccess = Color(0xFF2C7C5F);
    final mainAmountColor = needToPay > 0 ? softDanger : AppColors.textDark;
    final netLabel = totalReceive >= totalOwe
        ? 'Bạn đang cân bằng tốt'
        : 'Ưu tiên xử lý các khoản cần trả';

    return Container(
      padding: const EdgeInsets.fromLTRB(18, 18, 18, 16),
      decoration: BoxDecoration(
        color: const Color(0xFFECF8F2),
        borderRadius: BorderRadius.circular(24),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Tổng quan dòng tiền',
                      style: TextStyle(
                        color: AppColors.textDark,
                        fontSize: 15,
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                    SizedBox(height: 4),
                    Text(
                      'Sau khi tất toán giữa các nhóm',
                      style: TextStyle(
                        color: AppColors.textLight,
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ),
              ),
              Container(
                width: 38,
                height: 38,
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: 0.82),
                  borderRadius: BorderRadius.circular(14),
                ),
                child: const Icon(
                  Icons.account_balance_wallet_rounded,
                  color: AppColors.primary,
                  size: 20,
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          const Text(
            'Bạn cần trả',
            style: TextStyle(
              color: AppColors.textLight,
              fontSize: 13,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 5),
          FittedBox(
            fit: BoxFit.scaleDown,
            alignment: Alignment.centerLeft,
            child: Text(
              moneyText(needToPay),
              style: TextStyle(
                color: mainAmountColor,
                fontSize: 36,
                fontWeight: FontWeight.w900,
                letterSpacing: 0,
                height: 1,
              ),
            ),
          ),
          const SizedBox(height: 8),
          Text(
            netLabel,
            style: const TextStyle(
              color: AppColors.textLight,
              fontSize: 13,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 16),
          IntrinsicHeight(
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                HomeMetricTile(
                  label: 'Tôi đang nợ',
                  value: moneyText(totalOwe),
                  icon: Icons.arrow_upward_rounded,
                  valueColor: softDanger,
                ),
                const SizedBox(width: 12),
                HomeMetricTile(
                  label: 'Nợ tôi',
                  value: moneyText(totalReceive),
                  icon: Icons.arrow_downward_rounded,
                  valueColor: softSuccess,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget buildSearchBar() {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: AppColors.border),
      ),
      child: TextField(
        controller: searchController,
        style: const TextStyle(
          color: AppColors.textDark,
          fontWeight: FontWeight.w700,
        ),
        decoration: InputDecoration(
          hintText: 'Tìm nhóm...',
          prefixIcon: const Icon(Icons.search_rounded),
          suffixIcon: searchController.text.isNotEmpty
              ? IconButton(
                  onPressed: () => searchController.clear(),
                  icon: const Icon(Icons.close_rounded),
                )
              : null,
          border: InputBorder.none,
          enabledBorder: InputBorder.none,
          focusedBorder: InputBorder.none,
          contentPadding: const EdgeInsets.symmetric(
            horizontal: 14,
            vertical: 15,
          ),
        ),
      ),
    );
  }

  Widget buildQuickActions() {
    return GridView.count(
      crossAxisCount: 2,
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      crossAxisSpacing: 12,
      mainAxisSpacing: 12,
      childAspectRatio: 2.0,
      children: [
        HomeActionTile(
          title: 'Thêm chi',
          subtitle: 'Ghi khoản mới',
          icon: Icons.add_rounded,
          onTap: openQuickAddExpense,
          primary: true,
        ),
        HomeActionTile(
          title: 'Thanh toán',
          subtitle: 'Xử lý công nợ',
          icon: Icons.payments_rounded,
          onTap: openDebtOverview,
        ),
        HomeActionTile(
          title: 'Tạo nhóm',
          subtitle: 'Ví mới',
          icon: Icons.group_add_rounded,
          onTap: openCreateHousehold,
        ),
        HomeActionTile(
          title: 'Tham gia',
          subtitle: 'Nhập mã mời',
          icon: Icons.login_rounded,
          onTap: openJoinHousehold,
        ),
      ],
    );
  }

  Widget buildSectionTitle() {
    return HomeSectionHeader(
      title: 'Nhóm ví',
      subtitle: '${households.length} nhóm đang tham gia',
    );
  }

  Widget buildHouseholdCard(Household household) {
    final groupOwe = groupOweMap[household.id] ?? 0;
    final groupReceive = groupReceiveMap[household.id] ?? 0;
    final name = household.name.trim().isEmpty
        ? 'Nhóm không tên'
        : household.name.trim();
    const softDanger = Color(0xFFB94355);
    const softSuccess = Color(0xFF2C7C5F);

    String statusText = 'Đã cân bằng';
    String amountPrefix = '';
    double amount = 0;
    Color amountColor = AppColors.textLight;
    Color statusColor = AppColors.primaryDark;
    Color statusBackground = const Color(0xFFEFF8F4);

    if (groupOwe > 0) {
      statusText = 'Bạn cần trả';
      amountPrefix = '-';
      amount = groupOwe;
      amountColor = softDanger;
      statusColor = AppColors.textLight;
      statusBackground = AppColors.background;
    } else if (groupReceive > 0) {
      statusText = 'Bạn sẽ nhận';
      amountPrefix = '+';
      amount = groupReceive;
      amountColor = softSuccess;
      statusColor = AppColors.textLight;
      statusBackground = AppColors.background;
    }

    return GestureDetector(
      onTap: () async {
        await Navigator.push(
          context,
          MaterialPageRoute(
            builder: (_) => HouseholdDetailScreen(household: household),
          ),
        );

        await loadData();
      },
      child: Container(
        margin: const EdgeInsets.only(bottom: 12),
        padding: const EdgeInsets.fromLTRB(14, 14, 12, 14),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: AppColors.border),
        ),
        child: Row(
          children: [
            Container(
              width: 48,
              height: 48,
              decoration: BoxDecoration(
                color: AppColors.primary.withValues(alpha: 0.10),
                borderRadius: BorderRadius.circular(16),
              ),
              child: const Icon(
                Icons.groups_rounded,
                color: AppColors.primary,
                size: 24,
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    name,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      color: AppColors.textDark,
                      fontSize: 17,
                      fontWeight: FontWeight.w900,
                      letterSpacing: 0,
                    ),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    '${household.memberCount} thành viên',
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      color: AppColors.textLight,
                      fontSize: 13,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 10),
            ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 124),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  FittedBox(
                    fit: BoxFit.scaleDown,
                    alignment: Alignment.centerRight,
                    child: Text(
                      '$amountPrefix${formatMoney(amount)}đ',
                      style: TextStyle(
                        color: amountColor,
                        fontSize: 16,
                        fontWeight: FontWeight.w900,
                        letterSpacing: 0,
                      ),
                    ),
                  ),
                  const SizedBox(height: 6),
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 8,
                      vertical: 4,
                    ),
                    decoration: BoxDecoration(
                      color: statusBackground,
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: Text(
                      statusText,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        color: statusColor,
                        fontSize: 11,
                        fontWeight: FontWeight.w800,
                        height: 1,
                      ),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 4),
            const Icon(
              Icons.chevron_right_rounded,
              color: AppColors.textLight,
              size: 22,
            ),
          ],
        ),
      ),
    );
  }

  IconData getActivityIcon(String type) {
    switch (type) {
      case 'group_created':
        return Icons.group_add_rounded;
      case 'expense_created':
        return Icons.receipt_long_rounded;
      case 'expense_updated':
        return Icons.edit_note_rounded;
      case 'expense_deleted':
        return Icons.delete_outline_rounded;
      case 'member_joined':
      case 'added_to_group':
      case 'member_added_to_group':
        return Icons.person_add_alt_1_rounded;
      case 'member_left':
        return Icons.person_remove_alt_1_rounded;
      case 'member_kicked':
        return Icons.person_off_rounded;
      case 'virtual_member_created':
        return Icons.person_outline_rounded;
      case 'household_deleted':
        return Icons.delete_forever_rounded;
      case 'debt_created':
        return Icons.account_balance_wallet_rounded;
      case 'payment_received':
      case 'payment_sent':
      case 'payment_created':
      case 'payment_confirmed':
        return Icons.payments_rounded;
      case 'debt_reminder_received':
      case 'debt_reminder_sent':
        return Icons.notifications_active_rounded;
      default:
        return Icons.history_rounded;
    }
  }

  Color getActivityColor(String type) {
    switch (type) {
      case 'expense_deleted':
      case 'member_kicked':
      case 'household_deleted':
        return const Color(0xFFB94355);
      case 'payment_received':
      case 'payment_sent':
      case 'payment_created':
      case 'payment_confirmed':
        return const Color(0xFF2C7C5F);
      case 'expense_created':
        return AppColors.primary;
      case 'debt_created':
      case 'debt_reminder_received':
      case 'debt_reminder_sent':
        return AppColors.warning;
      case 'member_left':
      case 'virtual_member_created':
        return AppColors.info;
      default:
        return AppColors.info;
    }
  }

  String formatActivityMoney(dynamic amount) {
    if (amount == null) return '';

    final value = double.tryParse(amount.toString()) ?? 0;
    if (value == 0) return '';

    return moneyText(value);
  }

  String formatActivityTime(dynamic value) {
    if (value == null) return '';

    try {
      final date = DateTime.parse(value.toString()).toLocal();
      final now = DateTime.now();
      final diff = now.difference(date);

      if (diff.inMinutes < 1) return 'Vừa xong';
      if (diff.inMinutes < 60) return '${diff.inMinutes} phút trước';
      if (diff.inHours < 24) return '${diff.inHours} giờ trước';
      if (diff.inDays < 7) return '${diff.inDays} ngày trước';

      return '${date.day}/${date.month}/${date.year}';
    } catch (_) {
      return value.toString();
    }
  }

  Widget buildRecentActivitySection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        HomeSectionHeader(
          title: 'Hoạt động gần đây',
          subtitle: 'Những thay đổi mới trong các nhóm',
          actionLabel: recentActivities.isEmpty ? null : 'Xem tất cả',
          onAction: recentActivities.isEmpty ? null : openActivities,
        ),
        const SizedBox(height: 12),
        if (recentActivityError != null)
          HomeInlineEmpty(
            icon: Icons.wifi_off_rounded,
            title: 'Chưa tải được hoạt động',
            message: recentActivityError!,
          )
        else if (recentActivities.isEmpty)
          const HomeInlineEmpty(
            icon: Icons.history_rounded,
            title: 'Chưa có hoạt động',
            message: 'Các khoản chi và thanh toán mới sẽ xuất hiện tại đây.',
          )
        else
          Container(
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(22),
            ),
            child: Column(
              children: [
                for (var index = 0; index < recentActivities.length; index++)
                  buildActivityRow(
                    Map<String, dynamic>.from(recentActivities[index]),
                    showDivider: index < recentActivities.length - 1,
                  ),
              ],
            ),
          ),
      ],
    );
  }

  Widget buildActivityRow(
    Map<String, dynamic> activity, {
    required bool showDivider,
  }) {
    final type = activity['activity_type']?.toString() ?? '';
    final color = getActivityColor(type);
    final amount = formatActivityMoney(activity['amount']);
    final householdName = activity['household_name']?.toString() ?? '';
    final time = formatActivityTime(activity['created_at']);

    return Container(
      padding: const EdgeInsets.fromLTRB(14, 13, 14, 13),
      decoration: BoxDecoration(
        border: showDivider
            ? const Border(bottom: BorderSide(color: AppColors.border))
            : null,
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
            child: Icon(getActivityIcon(type), color: color, size: 21),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  activity['title']?.toString() ?? 'Hoạt động mới',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    color: AppColors.textDark,
                    fontSize: 14,
                    fontWeight: FontWeight.w900,
                  ),
                ),
                const SizedBox(height: 5),
                Text(
                  [
                    if (householdName.isNotEmpty) householdName,
                    if (time.isNotEmpty) time,
                  ].join(' • '),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    color: AppColors.textLight,
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
          ),
          if (amount.isNotEmpty) ...[
            const SizedBox(width: 8),
            Text(
              amount,
              style: const TextStyle(
                color: AppColors.primary,
                fontSize: 13,
                fontWeight: FontWeight.w900,
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget buildFinancialHero() {
    return Container(
      padding: const EdgeInsets.fromLTRB(20, 17, 20, 17),
      decoration: BoxDecoration(
        color: AppColors.primary,
        borderRadius: BorderRadius.circular(28),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          Text(
            heroTitle,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            textAlign: TextAlign.center,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 18,
              fontWeight: FontWeight.w900,
              height: 1.12,
            ),
          ),
          const SizedBox(height: 10),
          FittedBox(
            fit: BoxFit.scaleDown,
            alignment: Alignment.center,
            child: Text(
              moneyText(heroAmount),
              textAlign: TextAlign.center,
              style: const TextStyle(
                color: Colors.white,
                fontSize: 44,
                fontWeight: FontWeight.w900,
                letterSpacing: 0,
                height: 0.98,
              ),
            ),
          ),
          const SizedBox(height: 20),
          Row(
            children: [
              Expanded(
                child: buildHeroMetric(
                  label: 'Tôi đang nợ',
                  value: moneyText(totalOwe),
                  color: const Color(0xFFFFB4AE),
                ),
              ),
              Container(
                width: 1,
                height: 38,
                margin: const EdgeInsets.symmetric(horizontal: 12),
                color: Colors.white.withValues(alpha: 0.14),
              ),
              Expanded(
                child: buildHeroMetric(
                  label: 'Nợ tôi',
                  value: moneyText(totalReceive),
                  color: const Color(0xFF9FE8C4),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget buildHeroMetric({
    required String label,
    required String value,
    required Color color,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.center,
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        Text(
          label,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          textAlign: TextAlign.center,
          style: TextStyle(
            color: Colors.white.withValues(alpha: 0.64),
            fontSize: 11,
            fontWeight: FontWeight.w800,
          ),
        ),
        const SizedBox(height: 4),
        FittedBox(
          fit: BoxFit.scaleDown,
          alignment: Alignment.center,
          child: Text(
            value,
            textAlign: TextAlign.center,
            style: TextStyle(
              color: color,
              fontSize: 15,
              fontWeight: FontWeight.w900,
              height: 1,
            ),
          ),
        ),
      ],
    );
  }

  Widget buildFinancialStatusLine() {
    final label = hasPayableDebt
        ? 'Việc cần xử lý ngay'
        : hasReceivableDebt
        ? 'Khoản cần theo dõi'
        : hasGroups
        ? 'Trạng thái hôm nay'
        : 'Bắt đầu Chung Ví';
    final message = hasPayableDebt
        ? 'Bạn đang có khoản cần trả trong nhóm.'
        : hasReceivableDebt
        ? 'Có khoản người khác đang nợ bạn.'
        : hasGroups
        ? 'Các nhóm hiện không có chênh lệch cần xử lý.'
        : 'Tạo hoặc tham gia nhóm để ghi chi tiêu thật.';

    return Container(
      padding: const EdgeInsets.fromLTRB(14, 13, 14, 13),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: AppColors.border),
      ),
      child: Row(
        children: [
          Container(
            width: 38,
            height: 38,
            decoration: BoxDecoration(
              color: AppColors.primary.withValues(alpha: 0.09),
              borderRadius: BorderRadius.circular(13),
            ),
            child: const Icon(
              Icons.priority_high_rounded,
              color: AppColors.primary,
              size: 20,
            ),
          ),
          const SizedBox(width: 11),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  label,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    color: AppColors.textDark,
                    fontSize: 14,
                    fontWeight: FontWeight.w900,
                  ),
                ),
                const SizedBox(height: 3),
                Text(
                  message,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    color: AppColors.textLight,
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget buildCommandStrip() {
    return Row(
      children: [
        Expanded(
          child: HomeCommandButton(
            label: 'Tạo nhóm',
            icon: Icons.group_add_rounded,
            onTap: openCreateHousehold,
          ),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: HomeCommandButton(
            label: 'Tham gia',
            icon: Icons.login_rounded,
            onTap: openJoinHousehold,
          ),
        ),
      ],
    );
  }

  Widget buildContextualActions() {
    return buildCommandStrip();
  }

  Widget buildPriorityHouseholdsSection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        HomeSectionHeader(
          title: 'Nhóm cần chú ý',
          subtitle: households.isEmpty
              ? 'Chưa có nhóm ví nào'
              : '${priorityHouseholds.length} nhóm nổi bật từ dữ liệu hiện có',
        ),
        const SizedBox(height: 12),
        if (households.isEmpty)
          const HomeInlineEmpty(
            icon: Icons.groups_rounded,
            title: 'Chưa có nhóm nào',
            message:
                'Tạo nhóm đầu tiên để bắt đầu chia chi tiêu cùng bạn bè hoặc gia đình.',
          )
        else
          Container(
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(24),
              border: Border.all(color: AppColors.border),
            ),
            child: Column(
              children: [
                for (var index = 0; index < priorityHouseholds.length; index++)
                  buildHouseholdLedgerRow(
                    priorityHouseholds[index],
                    showDivider: index < priorityHouseholds.length - 1,
                    compact: true,
                  ),
              ],
            ),
          ),
      ],
    );
  }

  Widget buildAllHouseholdsSection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        HomeSectionHeader(
          title: 'Tất cả nhóm ví',
          subtitle: '${households.length} nhóm đang tham gia',
        ),
        const SizedBox(height: 12),
        buildSearchBar(),
        const SizedBox(height: 14),
        if (filteredHouseholds.isEmpty)
          SizedBox(
            height: MediaQuery.of(context).size.height * 0.32,
            child: AppEmptyState(
              icon: Icons.search_off_rounded,
              title: 'Không tìm thấy nhóm',
              message: 'Thử nhập từ khóa khác để tìm nhóm bạn cần.',
            ),
          )
        else
          Container(
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(24),
              border: Border.all(color: AppColors.border),
            ),
            child: Column(
              children: [
                for (var index = 0; index < filteredHouseholds.length; index++)
                  buildHouseholdLedgerRow(
                    filteredHouseholds[index],
                    showDivider: index < filteredHouseholds.length - 1,
                  ),
              ],
            ),
          ),
      ],
    );
  }

  Widget buildHouseholdLedgerRow(
    Household household, {
    required bool showDivider,
    bool compact = false,
  }) {
    final groupOwe = groupOweMap[household.id] ?? 0;
    final groupReceive = groupReceiveMap[household.id] ?? 0;
    final name = household.name.trim().isEmpty
        ? 'Nhóm không tên'
        : household.name.trim();
    final initial = name.characters.first.toUpperCase();
    const softDanger = Color(0xFFB94355);
    const softSuccess = Color(0xFF2C7C5F);

    String statusText = 'Đã cân bằng';
    String amountPrefix = '';
    double amount = 0;
    Color amountColor = AppColors.textMuted;
    Color statusColor = AppColors.primaryDark;
    IconData statusIcon = Icons.check_rounded;

    if (groupOwe > 0) {
      statusText = 'Cần trả';
      amountPrefix = '-';
      amount = groupOwe;
      amountColor = softDanger;
      statusColor = softDanger;
      statusIcon = Icons.north_east_rounded;
    } else if (groupReceive > 0) {
      statusText = 'Sẽ nhận';
      amountPrefix = '+';
      amount = groupReceive;
      amountColor = softSuccess;
      statusColor = softSuccess;
      statusIcon = Icons.south_west_rounded;
    }

    return InkWell(
      onTap: () async {
        await Navigator.push(
          context,
          MaterialPageRoute(
            builder: (_) => HouseholdDetailScreen(household: household),
          ),
        );

        await loadData();
      },
      child: Container(
        padding: EdgeInsets.fromLTRB(
          14,
          compact ? 13 : 15,
          10,
          compact ? 13 : 15,
        ),
        decoration: BoxDecoration(
          border: showDivider
              ? const Border(bottom: BorderSide(color: AppColors.border))
              : null,
        ),
        child: Row(
          children: [
            Container(
              width: compact ? 42 : 46,
              height: compact ? 42 : 46,
              decoration: BoxDecoration(
                color: AppColors.primary.withValues(alpha: 0.09),
                borderRadius: BorderRadius.circular(15),
              ),
              alignment: Alignment.center,
              child: Text(
                initial,
                style: const TextStyle(
                  color: AppColors.primaryDark,
                  fontSize: 16,
                  fontWeight: FontWeight.w900,
                ),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    name,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      color: AppColors.textDark,
                      fontSize: compact ? 15 : 16,
                      fontWeight: FontWeight.w900,
                      letterSpacing: 0,
                    ),
                  ),
                  const SizedBox(height: 5),
                  Row(
                    children: [
                      Icon(statusIcon, color: statusColor, size: 14),
                      const SizedBox(width: 5),
                      Flexible(
                        child: Text(
                          '$statusText • ${household.memberCount} thành viên',
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(
                            color: AppColors.textLight,
                            fontSize: 12,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(width: 10),
            ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 116),
              child: FittedBox(
                fit: BoxFit.scaleDown,
                alignment: Alignment.centerRight,
                child: Text(
                  '$amountPrefix${formatMoney(amount)}đ',
                  style: TextStyle(
                    color: amountColor,
                    fontSize: compact ? 15 : 16,
                    fontWeight: FontWeight.w900,
                    letterSpacing: 0,
                  ),
                ),
              ),
            ),
            const SizedBox(width: 3),
            const Icon(
              Icons.chevron_right_rounded,
              color: AppColors.textMuted,
              size: 22,
            ),
          ],
        ),
      ),
    );
  }

  Future<void> refreshData() async {
    await loadData();
  }

  @override
  Widget build(BuildContext context) {
    if (isLoading) {
      return const Scaffold(
        backgroundColor: AppColors.background,
        body: AppLoadingState(message: 'Đang tải dữ liệu...'),
      );
    }

    if (errorMessage != null) {
      return Scaffold(
        backgroundColor: AppColors.background,
        body: AppErrorState(message: errorMessage!, onRetry: loadData),
      );
    }

    final width = MediaQuery.sizeOf(context).width;
    final horizontalPadding = width >= 760
        ? (width - 720) / 2
        : width < 380
        ? 16.0
        : 20.0;

    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: RefreshIndicator(
          onRefresh: refreshData,
          child: ListView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: EdgeInsets.fromLTRB(
              horizontalPadding,
              18,
              horizontalPadding,
              0,
            ),
            children: [
              buildHeader(),
              const SizedBox(height: 20),
              buildFinancialHero(),
              const SizedBox(height: 14),
              buildContextualActions(),
              const SizedBox(height: 26),
              if (households.isNotEmpty) buildAllHouseholdsSection(),
              const SizedBox(height: 112),
            ],
          ),
        ),
      ),
    );
  }
}
