import 'package:flutter/material.dart';

import 'app_theme.dart';
import 'create_household_screen.dart';
import 'household_detail_screen.dart';
import 'models/household.dart';
import 'services/api_service.dart';
import 'widgets/app_empty_state.dart';
import 'widgets/app_error_state.dart';
import 'widgets/app_loading_state.dart';
import 'join_household_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

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
            (json) => Household.fromJson(
              Map<String, dynamic>.from(json),
            ),
          )
          .toList();

      final summaries =
          await ApiService.getHouseholdSummaries();

      double owe = 0;
      double receive = 0;

      groupOweMap.clear();
      groupReceiveMap.clear();
      householdSummaryMap.clear();

      for (final item in summaries) {
        final summary = Map<String, dynamic>.from(item);

        final householdId = summary['id']?.toString() ?? '';

        final rawGroupOwe = double.tryParse(
              summary['total_owe']?.toString() ?? '0',
            ) ??
            0;

        final rawGroupReceive = double.tryParse(
              summary['total_receive']?.toString() ?? '0',
            ) ??
            0;
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
          errorMessage =
              'Không thể tải dữ liệu trang chủ';
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
    return amount.toStringAsFixed(0).replaceAllMapped(
          RegExp(r'\B(?=(\d{3})+(?!\d))'),
          (match) => '.',
        );
  }

  Future<void> openCreateHousehold() async {
    await Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => const CreateHouseholdScreen(),
      ),
    );

    await loadData();
  }

  Future<void> openJoinHousehold() async {
    await Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) =>
            const JoinHouseholdScreen(),
      ),
    );

    await loadData();
  }

  Widget buildHeader() {
    return Row(
      children: [
        ClipRRect(
          borderRadius: BorderRadius.circular(20),
          child: Image.asset(
            'assets/images/logo.jpg',
            width: 58,
            height: 58,
            fit: BoxFit.cover,
          ),
        ),
        const SizedBox(width: 14),
        const Expanded(
          child: Column(
            crossAxisAlignment:
                CrossAxisAlignment.start,
            children: [
              Text(
                'Chung Ví',
                style: TextStyle(
                  color: AppColors.textDark,
                  fontSize: 28,
                  fontWeight: FontWeight.w900,
                  letterSpacing: -0.8,
                  height: 1,
                ),
              ),
              SizedBox(height: 6),
              Text(
                'Quản lý chi tiêu nhóm',
                style: TextStyle(
                  color: AppColors.textLight,
                  fontSize: 14,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
        ),
        Container(
          width: 46,
          height: 46,
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius:
                BorderRadius.circular(16),
          ),
          child: const Icon(
            Icons.notifications_none_rounded,
            color: AppColors.textDark,
          ),
        ),
      ],
    );
  }

  Widget buildSummaryCard() {
    final netBalance = totalReceive - totalOwe;
    final netAmount = netBalance.abs();

    String netTitle = 'Đã cân bằng';
    IconData netIcon = Icons.check_circle_rounded;

    if (netBalance > 0) {
      netTitle = 'Bạn sẽ nhận thêm';
      netIcon = Icons.arrow_downward_rounded;
    } else if (netBalance < 0) {
      netTitle = 'Bạn cần trả thêm';
      netIcon = Icons.arrow_upward_rounded;
    }

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
              Icon(
                netIcon,
                color: Colors.white70,
                size: 18,
              ),
              const SizedBox(width: 6),
              Text(
                netTitle,
                style: const TextStyle(
                  color: Colors.white70,
                  fontSize: 15,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Text(
            '${formatMoney(netAmount)}đ',
            style: const TextStyle(
              color: Colors.white,
              fontSize: 38,
              fontWeight: FontWeight.w900,
              letterSpacing: -1,
            ),
          ),
          const SizedBox(height: 26),
          Row(
            children: [
              buildMoneyBox(
                title: 'Bạn đang nợ',
                amount: totalOwe,
                icon: Icons.arrow_upward_rounded,
              ),
              const SizedBox(width: 12),
              buildMoneyBox(
                title: 'Bạn sẽ nhận',
                amount: totalReceive,
                icon: Icons.arrow_downward_rounded,
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget buildMoneyBox({
    required String title,
    required double amount,
    required IconData icon,
  }) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: Colors.white.withValues(alpha: 0.14),
          borderRadius: BorderRadius.circular(20),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(
              icon,
              color: Colors.white,
              size: 22,
            ),
            const SizedBox(height: 14),
            Text(
              title,
              style: const TextStyle(
                color: Colors.white70,
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(height: 6),
            Text(
              '${formatMoney(amount)}đ',
              style: const TextStyle(
                color: Colors.white,
                fontSize: 19,
                fontWeight: FontWeight.w900,
                letterSpacing: -0.3,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget buildSearchBar() {
    return TextField(
      controller: searchController,
      style: const TextStyle(
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
      ),
    );
  }

  Widget buildSectionTitle() {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        const Text(
          'Danh sách nhóm',
          style: TextStyle(
            fontSize: 20,
            fontWeight: FontWeight.w800,
          ),
        ),

        Row(
          children: [
            InkWell(
              borderRadius: BorderRadius.circular(999),
              onTap: openCreateHousehold,
              child: Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 14,
                  vertical: 10,
                ),
                decoration: BoxDecoration(
                  color: AppColors.primary.withValues(alpha: 0.08),
                  borderRadius: BorderRadius.circular(999),
                ),
                child: const Row(
                  children: [
                    Icon(
                      Icons.add_rounded,
                      size: 18,
                      color: AppColors.primary,
                    ),
                    SizedBox(width: 6),
                    Text(
                      'Tạo nhóm',
                      style: TextStyle(
                        color: AppColors.primary,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ],
                ),
              ),
            ),

            const SizedBox(width: 8),

            InkWell(
              borderRadius: BorderRadius.circular(999),
              onTap: openJoinHousehold,
              child: Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 14,
                  vertical: 10,
                ),
                decoration: BoxDecoration(
                  color: AppColors.primary.withValues(alpha: 0.08),
                  borderRadius: BorderRadius.circular(999),
                ),
                child: const Row(
                  children: [
                    Icon(
                      Icons.group_add_rounded,
                      size: 18,
                      color: AppColors.primary,
                    ),
                    SizedBox(width: 6),
                    Text(
                      'Join',
                      style: TextStyle(
                        color: AppColors.primary,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget buildHouseholdCard(Household household) {
    final groupOwe = groupOweMap[household.id] ?? 0;
    final groupReceive = groupReceiveMap[household.id] ?? 0;

    String statusText = 'Không có công nợ';
    Color statusColor = AppColors.success;
    IconData statusIcon = Icons.check_circle_rounded;

    if (groupOwe > 0) {
      statusText = 'Sau tất toán, bạn trả ${formatMoney(groupOwe)}đ';
      statusColor = AppColors.danger;
      statusIcon = Icons.arrow_upward_rounded;
    } else if (groupReceive > 0) {
      statusText = 'Sau tất toán, bạn nhận ${formatMoney(groupReceive)}đ';
      statusColor = AppColors.success;
      statusIcon = Icons.arrow_downward_rounded;
    }

    return GestureDetector(
      onTap: () async {
        await Navigator.push(
          context,
          MaterialPageRoute(
            builder: (_) => HouseholdDetailScreen(
              household: household,
            ),
          ),
        );

        await loadData();
      },
      child: Container(
        margin: const EdgeInsets.only(bottom: 16),
        padding: const EdgeInsets.all(18),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(26),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.03),
              blurRadius: 20,
              offset: const Offset(0, 10),
            ),
          ],
        ),
        child: Row(
          children: [
            Container(
              width: 58,
              height: 58,
              decoration: BoxDecoration(
                gradient: const LinearGradient(
                  colors: [
                    AppColors.primary,
                    AppColors.secondary,
                  ],
                ),
                borderRadius: BorderRadius.circular(20),
              ),
              child: const Icon(
                Icons.home_rounded,
                color: Colors.white,
                size: 28,
              ),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    household.name,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      color: AppColors.textDark,
                      fontSize: 18,
                      fontWeight: FontWeight.w900,
                      letterSpacing: -0.4,
                    ),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    '${household.members.length} thành viên',
                    style: const TextStyle(
                      color: AppColors.textLight,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: 10),
                  Row(
                    children: [
                      Icon(
                        statusIcon,
                        color: statusColor,
                        size: 18,
                      ),
                      const SizedBox(width: 6),
                      Expanded(
                        child: Text(
                          statusText,
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(
                            color: statusColor,
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(width: 12),
            const Icon(
              Icons.chevron_right_rounded,
              color: AppColors.textLight,
            ),
          ],
        ),
      ),
    );
  }

  Widget buildEmptyState() {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(34),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(32),
      ),
      child: Column(
        children: [
          Container(
            width: 84,
            height: 84,
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                colors: [
                  AppColors.primary,
                  AppColors.secondary,
                ],
              ),
              borderRadius: BorderRadius.circular(28),
            ),
            child: const Icon(
              Icons.groups_rounded,
              color: Colors.white,
              size: 42,
            ),
          ),
          const SizedBox(height: 24),
          const Text(
            'Chưa có nhóm nào',
            style: TextStyle(
              color: AppColors.textDark,
              fontSize: 22,
              fontWeight: FontWeight.w900,
            ),
          ),
          const SizedBox(height: 12),
          const Text(
            'Tạo nhóm đầu tiên để bắt đầu chia tiền cùng mọi người.',
            textAlign: TextAlign.center,
            style: TextStyle(
              color: AppColors.textLight,
              fontWeight: FontWeight.w600,
              height: 1.5,
            ),
          ),
          const SizedBox(height: 28),
          ElevatedButton(
            onPressed: openCreateHousehold,
            child: const Text('Tạo nhóm ngay'),
          ),
        ],
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
        body: AppLoadingState(
          message: 'Đang tải dữ liệu...',
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
      body: SafeArea(
        child: RefreshIndicator(
          onRefresh: refreshData,
          child: ListView(
            physics:
                const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.all(20),
            children: [
              buildHeader(),
              const SizedBox(height: 26),
              buildSummaryCard(),
              const SizedBox(height: 24),
              buildSearchBar(),
              const SizedBox(height: 28),
              buildSectionTitle(),
              const SizedBox(height: 16),
              if (households.isEmpty)
                SizedBox(
                  height:
                      MediaQuery.of(context).size.height *
                      0.52,
                  child: AppEmptyState(
                    icon: Icons.groups_rounded,
                    title: 'Chưa có nhóm nào',
                    message:
                        'Tạo nhóm đầu tiên để bắt đầu chia chi tiêu cùng bạn bè hoặc gia đình.',
                    buttonText: 'Tạo nhóm',
                    onPressed: openCreateHousehold,
                  ),
                )
              else if (filteredHouseholds.isEmpty)
                SizedBox(
                  height:
                      MediaQuery.of(context).size.height *
                      0.42,
                  child: AppEmptyState(
                    icon: Icons.search_off_rounded,
                    title: 'Không tìm thấy nhóm',
                    message:
                        'Thử nhập từ khóa khác để tìm nhóm bạn cần.',
                  ),
                )
              else
                ...filteredHouseholds.map(
                  buildHouseholdCard,
                ),
              const SizedBox(height: 120),
            ],
          ),
        ),
      ),
    );
  }
}