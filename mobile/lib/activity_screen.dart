import 'package:flutter/material.dart';

import 'app_theme.dart';
import 'services/api_service.dart';
import 'widgets/app_empty_state.dart';
import 'widgets/app_error_state.dart';
import 'widgets/app_loading_state.dart';

class ActivityScreen extends StatefulWidget {
  final String? householdId;

  const ActivityScreen({super.key, this.householdId});

  @override
  State<ActivityScreen> createState() => _ActivityScreenState();
}

class _ActivityScreenState extends State<ActivityScreen>
    with SingleTickerProviderStateMixin {
  late TabController tabController;

  bool isLoadingActivities = true;
  bool isLoadingNotifications = true;

  bool isLoadingMoreActivities = false;
  bool isLoadingMoreNotifications = false;

  bool hasMoreActivities = true;
  bool hasMoreNotifications = true;

  bool isActivityPageError = false;
  bool isNotificationPageError = false;

  int activityPage = 1;
  int notificationPage = 1;

  String? activityError;
  String? notificationError;

  List<dynamic> activities = [];
  List<dynamic> notifications = [];

  final ScrollController activityScrollController = ScrollController();
  final ScrollController notificationScrollController = ScrollController();

  bool get isGroupOnly => widget.householdId != null;

  int get unreadNotificationCount {
    return notifications.where((item) {
      final notification = Map<String, dynamic>.from(item);
      return notification['is_read'] != true;
    }).length;
  }

  @override
  void initState() {
    super.initState();

    tabController = TabController(length: isGroupOnly ? 1 : 2, vsync: this);
    tabController.addListener(() {
      if (!tabController.indexIsChanging && mounted) {
        setState(() {});
      }
    });

    activityScrollController.addListener(() {
      if (activityScrollController.position.pixels >=
          activityScrollController.position.maxScrollExtent - 300) {
        loadMoreActivities();
      }
    });

    notificationScrollController.addListener(() {
      if (notificationScrollController.position.pixels >=
          notificationScrollController.position.maxScrollExtent - 300) {
        loadMoreNotifications();
      }
    });

    loadActivities();

    if (!isGroupOnly) {
      loadNotifications();
    }
  }

  @override
  void dispose() {
    activityScrollController.dispose();
    notificationScrollController.dispose();
    tabController.dispose();
    super.dispose();
  }

  Future<void> loadActivities() async {
    if (!mounted) return;

    setState(() {
      isLoadingActivities = true;
      isLoadingMoreActivities = false;
      hasMoreActivities = true;
      isActivityPageError = false;
      activityPage = 1;
      activityError = null;
    });

    try {
      final response = isGroupOnly
          ? await ApiService.getActivities(widget.householdId!, page: 1)
          : await ApiService.getAllActivities(page: 1);

      final data = List<dynamic>.from(response['results']);

      if (!mounted) return;

      setState(() {
        activities = data;
        hasMoreActivities = response['next'] != null;
        isLoadingActivities = false;
        activityError = null;
      });
    } catch (e) {
      debugPrint(e.toString());

      if (!mounted) return;

      setState(() {
        activityError = 'Không thể tải hoạt động';
        isLoadingActivities = false;
      });
    }
  }

  Future<void> loadMoreActivities() async {
    if (isLoadingActivities ||
        isLoadingMoreActivities ||
        !hasMoreActivities ||
        isActivityPageError) {
      return;
    }

    setState(() {
      isLoadingMoreActivities = true;
      isActivityPageError = false;
    });

    try {
      final nextPage = activityPage + 1;

      final response = isGroupOnly
          ? await ApiService.getActivities(widget.householdId!, page: nextPage)
          : await ApiService.getAllActivities(page: nextPage);

      final newItems = List<dynamic>.from(response['results']);

      if (!mounted) return;

      setState(() {
        activityPage = nextPage;
        activities.addAll(newItems);
        hasMoreActivities = response['next'] != null;
        isLoadingMoreActivities = false;
      });
    } catch (e) {
      debugPrint(e.toString());

      if (!mounted) return;

      setState(() {
        isLoadingMoreActivities = false;
        isActivityPageError = true;
      });
    }
  }

  Future<void> loadNotifications() async {
    if (!mounted) return;

    setState(() {
      isLoadingNotifications = true;
      isLoadingMoreNotifications = false;
      hasMoreNotifications = true;
      isNotificationPageError = false;
      notificationPage = 1;
      notificationError = null;
    });

    try {
      final response = await ApiService.getNotifications(page: 1);

      final data = List<dynamic>.from(response['results']);

      if (!mounted) return;

      setState(() {
        notifications = data;
        hasMoreNotifications = response['next'] != null;
        isLoadingNotifications = false;
        notificationError = null;
      });
    } catch (e) {
      debugPrint(e.toString());

      if (!mounted) return;

      setState(() {
        notificationError = 'Không thể tải thông báo';
        isLoadingNotifications = false;
      });
    }
  }

  Future<void> loadMoreNotifications() async {
    if (isGroupOnly ||
        isLoadingNotifications ||
        isLoadingMoreNotifications ||
        !hasMoreNotifications ||
        isNotificationPageError) {
      return;
    }

    setState(() {
      isLoadingMoreNotifications = true;
      isNotificationPageError = false;
    });

    try {
      final nextPage = notificationPage + 1;

      final response = await ApiService.getNotifications(page: nextPage);

      final newItems = List<dynamic>.from(response['results']);

      if (!mounted) return;

      setState(() {
        notificationPage = nextPage;
        notifications.addAll(newItems);
        hasMoreNotifications = response['next'] != null;
        isLoadingMoreNotifications = false;
      });
    } catch (e) {
      debugPrint(e.toString());

      if (!mounted) return;

      setState(() {
        isLoadingMoreNotifications = false;
        isNotificationPageError = true;
      });
    }
  }

  Future<void> refreshCurrent() async {
    if (isGroupOnly) {
      await loadActivities();
      return;
    }

    if (tabController.index == 0) {
      await loadActivities();
    } else {
      await loadNotifications();
    }
  }

  IconData getIcon(String type) {
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

  Color getIconColor(String type) {
    switch (type) {
      case 'expense_created':
      case 'payment_received':
      case 'payment_sent':
      case 'payment_created':
      case 'payment_confirmed':
        return AppColors.primary;
      case 'expense_updated':
      case 'debt_created':
      case 'debt_reminder_received':
      case 'debt_reminder_sent':
        return AppColors.warning;
      case 'expense_deleted':
        return AppColors.danger;
      case 'group_created':
      case 'member_joined':
      case 'added_to_group':
      case 'member_added_to_group':
        return AppColors.info;
      default:
        return AppColors.textLight;
    }
  }

  String formatMoney(dynamic amount) {
    if (amount == null) return '';

    final value = amount.toString().split('.').first;

    return '${value.replaceAllMapped(RegExp(r'\B(?=(\d{3})+(?!\d))'), (match) => '.')}đ';
  }

  DateTime? parseDate(dynamic value) {
    if (value == null) return null;

    try {
      return DateTime.parse(value.toString()).toLocal();
    } catch (_) {
      return null;
    }
  }

  String formatTime(dynamic value) {
    final date = parseDate(value);
    if (date == null) return value?.toString() ?? '';

    final now = DateTime.now();
    final diff = now.difference(date);

    if (diff.inMinutes < 1) return 'Vừa xong';
    if (diff.inMinutes < 60) return '${diff.inMinutes} phút trước';
    if (diff.inHours < 24) return '${diff.inHours} giờ trước';
    if (diff.inDays < 7) return '${diff.inDays} ngày trước';

    return '${date.day}/${date.month}/${date.year}';
  }

  String formatDayLabel(dynamic value) {
    final date = parseDate(value);
    if (date == null) return 'Trước đó';

    final today = DateTime.now();
    final todayOnly = DateTime(today.year, today.month, today.day);
    final dateOnly = DateTime(date.year, date.month, date.day);
    final diff = todayOnly.difference(dateOnly).inDays;

    if (diff == 0) return 'Hôm nay';
    if (diff == 1) return 'Hôm qua';

    return '${date.day}/${date.month}/${date.year}';
  }

  String currentListTitle() {
    if (isGroupOnly) return 'Hoạt động nhóm';
    return tabController.index == 0 ? 'Hoạt động chung' : 'Thông báo riêng';
  }

  String currentListSubtitle() {
    if (isGroupOnly) return 'Những thay đổi mới trong nhóm này';
    return tabController.index == 0
        ? 'Dòng thời gian từ các nhóm bạn tham gia'
        : unreadNotificationCount > 0
        ? '$unreadNotificationCount thông báo chưa đọc'
        : 'Tất cả thông báo riêng đã được xem';
  }

  int currentItemCount() {
    if (isGroupOnly || tabController.index == 0) return activities.length;
    return notifications.length;
  }

  Widget buildActivityCard(dynamic item) {
    final activity = Map<String, dynamic>.from(item);
    final type = activity['activity_type']?.toString() ?? '';

    return buildTimelineItem(
      icon: getIcon(type),
      iconColor: getIconColor(type),
      title: activity['title']?.toString() ?? 'Hoạt động mới',
      amount: activity['amount'],
      time: activity['created_at'],
      householdName: activity['household_name'],
      isUnread: false,
      level: null,
    );
  }

  Widget buildNotificationCard(dynamic item) {
    final notification = Map<String, dynamic>.from(item);
    final type = notification['notification_type']?.toString() ?? '';
    final isRead = notification['is_read'] == true;

    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      onTap: () async {
        final id = notification['id']?.toString();

        if (id != null && !isRead) {
          await ApiService.markNotificationAsRead(id);

          if (!mounted) return;

          setState(() {
            notification['is_read'] = true;
            final index = notifications.indexOf(item);
            if (index >= 0) {
              notifications[index] = notification;
            }
          });
        }
      },
      child: buildTimelineItem(
        icon: getIcon(type),
        iconColor: getIconColor(type),
        title: notification['title']?.toString() ?? 'Thông báo mới',
        amount: notification['amount'],
        time: notification['created_at'],
        householdName: notification['household_name'],
        isUnread: !isRead,
        level: notification['level']?.toString(),
      ),
    );
  }

  Widget buildTimelineItem({
    required IconData icon,
    required Color iconColor,
    required String title,
    required dynamic amount,
    required dynamic time,
    required dynamic householdName,
    required bool isUnread,
    required String? level,
  }) {
    final isPushLevel = level == 'push';
    final amountText = amount == null ? '' : formatMoney(amount);

    return Container(
      padding: const EdgeInsets.fromLTRB(0, 4, 0, 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Column(
            children: [
              Container(
                width: 42,
                height: 42,
                decoration: BoxDecoration(
                  color: isUnread
                      ? AppColors.primary
                      : iconColor.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(15),
                ),
                child: Icon(
                  icon,
                  color: isUnread ? Colors.white : iconColor,
                  size: 21,
                ),
              ),
              Container(
                width: 2,
                height: 52,
                margin: const EdgeInsets.only(top: 8),
                decoration: BoxDecoration(
                  color: AppColors.border,
                  borderRadius: BorderRadius.circular(99),
                ),
              ),
            ],
          ),
          const SizedBox(width: 13),
          Expanded(
            child: Container(
              padding: const EdgeInsets.fromLTRB(14, 13, 14, 14),
              decoration: BoxDecoration(
                color: isUnread
                    ? AppColors.primary.withValues(alpha: 0.07)
                    : Colors.white,
                borderRadius: BorderRadius.circular(20),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Expanded(
                        child: Text(
                          title,
                          style: TextStyle(
                            color: AppColors.textDark,
                            fontSize: 15,
                            fontWeight: isUnread
                                ? FontWeight.w900
                                : FontWeight.w800,
                            height: 1.28,
                          ),
                        ),
                      ),
                      if (isUnread) ...[
                        const SizedBox(width: 8),
                        Container(
                          width: 8,
                          height: 8,
                          margin: const EdgeInsets.only(top: 6),
                          decoration: const BoxDecoration(
                            color: AppColors.primary,
                            shape: BoxShape.circle,
                          ),
                        ),
                      ],
                    ],
                  ),
                  const SizedBox(height: 8),
                  Wrap(
                    spacing: 8,
                    runSpacing: 6,
                    crossAxisAlignment: WrapCrossAlignment.center,
                    children: [
                      if (householdName != null &&
                          householdName.toString().trim().isNotEmpty)
                        buildMetaText(householdName.toString()),
                      buildMetaText(formatTime(time)),
                      if (isPushLevel) buildLevelChip('Quan trọng'),
                    ],
                  ),
                  if (amountText.isNotEmpty) ...[
                    const SizedBox(height: 10),
                    Text(
                      amountText,
                      style: const TextStyle(
                        color: AppColors.primary,
                        fontSize: 16,
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget buildMetaText(String text) {
    return Text(
      text,
      style: const TextStyle(
        color: AppColors.textLight,
        fontSize: 12,
        fontWeight: FontWeight.w700,
      ),
    );
  }

  Widget buildLevelChip(String text) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: const Color(0xFFFBF3DB),
        borderRadius: BorderRadius.circular(10),
      ),
      child: Text(
        text,
        style: const TextStyle(
          color: Color(0xFF956400),
          fontSize: 11,
          fontWeight: FontWeight.w900,
        ),
      ),
    );
  }

  Widget buildList({
    required bool isLoading,
    required List<dynamic> items,
    required Widget Function(dynamic item) builder,
    required String emptyTitle,
    required String emptyDescription,
    required String? errorMessage,
    required Future<void> Function() onRetry,
    required IconData emptyIcon,
    required ScrollController controller,
    required bool isLoadingMore,
    required bool hasMore,
    required bool isPageError,
    required VoidCallback onLoadMoreRetry,
  }) {
    if (isLoading) {
      return const AppLoadingState(message: 'Đang tải dữ liệu...');
    }

    if (errorMessage != null) {
      return AppErrorState(message: errorMessage, onRetry: onRetry);
    }

    if (items.isEmpty) {
      return RefreshIndicator(
        onRefresh: refreshCurrent,
        child: ListView(
          controller: controller,
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.fromLTRB(20, 0, 20, 120),
          children: [
            SizedBox(
              height: MediaQuery.of(context).size.height * 0.56,
              child: AppEmptyState(
                icon: emptyIcon,
                title: emptyTitle,
                message: emptyDescription,
              ),
            ),
          ],
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: refreshCurrent,
      child: ListView.builder(
        controller: controller,
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.fromLTRB(20, 0, 20, 110),
        itemCount: items.length + 1,
        itemBuilder: (context, index) {
          if (index < items.length) {
            final current = Map<String, dynamic>.from(items[index]);
            final previous = index == 0
                ? null
                : Map<String, dynamic>.from(items[index - 1]);
            final currentDay = formatDayLabel(current['created_at']);
            final previousDay = previous == null
                ? null
                : formatDayLabel(previous['created_at']);
            final showDayHeader = currentDay != previousDay;

            return Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (showDayHeader) buildDayHeader(currentDay),
                builder(items[index]),
              ],
            );
          }

          return buildPaginationFooter(
            isLoadingMore: isLoadingMore,
            hasMore: hasMore,
            isPageError: isPageError,
            onLoadMoreRetry: onLoadMoreRetry,
          );
        },
      ),
    );
  }

  Widget buildDayHeader(String label) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(55, 18, 0, 9),
      child: Text(
        label,
        style: const TextStyle(
          color: AppColors.textDark,
          fontSize: 14,
          fontWeight: FontWeight.w900,
        ),
      ),
    );
  }

  Widget buildPaginationFooter({
    required bool isLoadingMore,
    required bool hasMore,
    required bool isPageError,
    required VoidCallback onLoadMoreRetry,
  }) {
    if (isLoadingMore) {
      return const Padding(
        padding: EdgeInsets.symmetric(vertical: 18),
        child: Center(child: CircularProgressIndicator()),
      );
    }

    if (isPageError) {
      return Padding(
        padding: const EdgeInsets.only(top: 14),
        child: Center(
          child: Column(
            children: [
              const Text(
                'Không tải được dữ liệu tiếp theo',
                style: TextStyle(
                  color: AppColors.textLight,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(height: 8),
              OutlinedButton(
                onPressed: onLoadMoreRetry,
                child: const Text('Thử lại'),
              ),
            ],
          ),
        ),
      );
    }

    if (!hasMore) {
      return const Padding(
        padding: EdgeInsets.symmetric(vertical: 16),
        child: Center(
          child: Text(
            'Đã tải hết dữ liệu',
            style: TextStyle(
              color: AppColors.textLight,
              fontWeight: FontWeight.w600,
            ),
          ),
        ),
      );
    }

    return const SizedBox(height: 20);
  }

  Widget buildHeader(double horizontalPadding) {
    final count = currentItemCount();

    return Padding(
      padding: EdgeInsets.fromLTRB(
        horizontalPadding,
        12,
        horizontalPadding,
        16,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      isGroupOnly ? 'Hoạt động nhóm' : 'Hoạt động',
                      style: const TextStyle(
                        color: AppColors.textDark,
                        fontSize: 28,
                        fontWeight: FontWeight.w900,
                        letterSpacing: -0.5,
                        height: 1.05,
                      ),
                    ),
                    const SizedBox(height: 6),
                    Text(
                      currentListSubtitle(),
                      style: const TextStyle(
                        color: AppColors.textLight,
                        fontSize: 13,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ],
                ),
              ),
              if (!isGroupOnly)
                IconButton.filledTonal(
                  onPressed:
                      isLoadingNotifications || unreadNotificationCount == 0
                      ? null
                      : () async {
                          await ApiService.markAllNotificationsAsRead();
                          await loadNotifications();
                        },
                  icon: const Icon(Icons.done_all_rounded),
                  tooltip: 'Đánh dấu đã đọc',
                ),
            ],
          ),
          const SizedBox(height: 18),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.fromLTRB(18, 18, 18, 16),
            decoration: BoxDecoration(
              color: AppColors.primary,
              borderRadius: BorderRadius.circular(28),
            ),
            child: Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        currentListTitle(),
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 20,
                          fontWeight: FontWeight.w900,
                          height: 1.12,
                        ),
                      ),
                      const SizedBox(height: 7),
                      Text(
                        count == 0
                            ? 'Kéo xuống để làm mới dữ liệu'
                            : '$count mục đang hiển thị',
                        style: TextStyle(
                          color: Colors.white.withValues(alpha: 0.78),
                          fontSize: 13,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ],
                  ),
                ),
                Container(
                  width: 56,
                  height: 56,
                  decoration: BoxDecoration(
                    color: Colors.white.withValues(alpha: 0.16),
                    borderRadius: BorderRadius.circular(18),
                  ),
                  child: Icon(
                    tabController.index == 1
                        ? Icons.notifications_rounded
                        : Icons.timeline_rounded,
                    color: Colors.white,
                    size: 27,
                  ),
                ),
              ],
            ),
          ),
          if (!isGroupOnly) ...[
            const SizedBox(height: 14),
            buildSegmentedTabs(),
          ],
        ],
      ),
    );
  }

  Widget buildSegmentedTabs() {
    return Container(
      padding: const EdgeInsets.all(4),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(18),
      ),
      child: Row(
        children: [
          buildTabButton(index: 0, label: 'Hoạt động'),
          buildTabButton(
            index: 1,
            label: unreadNotificationCount > 0
                ? 'Thông báo ($unreadNotificationCount)'
                : 'Thông báo',
          ),
        ],
      ),
    );
  }

  Widget buildTabButton({required int index, required String label}) {
    final isActive = tabController.index == index;

    return Expanded(
      child: Material(
        color: isActive ? AppColors.primary : Colors.transparent,
        borderRadius: BorderRadius.circular(14),
        child: InkWell(
          onTap: () {
            tabController.animateTo(index);
            setState(() {});
          },
          borderRadius: BorderRadius.circular(14),
          child: Container(
            height: 42,
            alignment: Alignment.center,
            child: Text(
              label,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                color: isActive ? Colors.white : AppColors.textLight,
                fontSize: 13,
                fontWeight: FontWeight.w900,
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget buildBody() {
    if (isGroupOnly) {
      return buildList(
        isLoading: isLoadingActivities,
        items: activities,
        errorMessage: activityError,
        onRetry: loadActivities,
        emptyIcon: Icons.history_rounded,
        controller: activityScrollController,
        isLoadingMore: isLoadingMoreActivities,
        hasMore: hasMoreActivities,
        isPageError: isActivityPageError,
        onLoadMoreRetry: loadMoreActivities,
        builder: buildActivityCard,
        emptyTitle: 'Chưa có hoạt động',
        emptyDescription:
            'Khi nhóm có khoản chi hoặc thành viên mới, hoạt động sẽ hiện ở đây.',
      );
    }

    return TabBarView(
      controller: tabController,
      children: [
        buildList(
          isLoading: isLoadingActivities,
          items: activities,
          errorMessage: activityError,
          onRetry: loadActivities,
          emptyIcon: Icons.history_rounded,
          controller: activityScrollController,
          isLoadingMore: isLoadingMoreActivities,
          hasMore: hasMoreActivities,
          isPageError: isActivityPageError,
          onLoadMoreRetry: loadMoreActivities,
          builder: buildActivityCard,
          emptyTitle: 'Chưa có hoạt động chung',
          emptyDescription: 'Các hoạt động công khai trong nhóm sẽ hiện ở đây.',
        ),
        buildList(
          isLoading: isLoadingNotifications,
          items: notifications,
          errorMessage: notificationError,
          onRetry: loadNotifications,
          emptyIcon: Icons.notifications_none_rounded,
          controller: notificationScrollController,
          isLoadingMore: isLoadingMoreNotifications,
          hasMore: hasMoreNotifications,
          isPageError: isNotificationPageError,
          onLoadMoreRetry: loadMoreNotifications,
          builder: buildNotificationCard,
          emptyTitle: 'Chưa có thông báo riêng',
          emptyDescription:
              'Nhắc nợ, thanh toán và thông báo cá nhân sẽ hiện ở đây.',
        ),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    final width = MediaQuery.sizeOf(context).width;
    final horizontalPadding = width >= 760
        ? (width - 720) / 2
        : width < 380
        ? 16.0
        : 20.0;

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: isGroupOnly ? AppBar(title: const Text('Hoạt động nhóm')) : null,
      body: SafeArea(
        child: Column(
          children: [
            buildHeader(horizontalPadding),
            Expanded(child: buildBody()),
          ],
        ),
      ),
    );
  }
}
