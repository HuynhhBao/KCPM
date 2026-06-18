import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'app_theme.dart';
import 'models/expense.dart';
import 'models/household.dart';
import 'services/api_service.dart';
import 'widgets/app_empty_state.dart';

class AddExpenseScreen extends StatefulWidget {
  final Household household;
  final Expense? expense;

  const AddExpenseScreen({super.key, required this.household, this.expense});

  @override
  State<AddExpenseScreen> createState() => _AddExpenseScreenState();
}

class _AddExpenseScreenState extends State<AddExpenseScreen> {
  final titleController = TextEditingController();
  final amountController = TextEditingController();
  final noteController = TextEditingController();

  DateTime selectedExpenseDate = DateTime.now();
  final List<dynamic> selectedParticipants = [];

  dynamic selectedPayer;
  String currentEmail = '';
  String? formError;
  bool isLoading = false;

  bool get isEditMode => widget.expense != null;

  @override
  void initState() {
    super.initState();
    amountController.addListener(refreshPreview);

    if (isEditMode) {
      titleController.text = widget.expense!.title;
      amountController.text = formatInputAmount(widget.expense!.amount);
      noteController.text = widget.expense!.note;

      final parsedExpenseDate = DateTime.tryParse(widget.expense!.expenseDate);
      if (parsedExpenseDate != null) {
        selectedExpenseDate = parsedExpenseDate;
      }

      final participantUserIds = widget.expense!.participants
          .map((participant) => participant.userId)
          .where((id) => id != 0)
          .toSet();

      selectedParticipants.addAll(
        widget.household.members.where(
          (member) => participantUserIds.contains(getMemberId(member)),
        ),
      );

      selectedPayer = findMemberByUserId(widget.expense!.payerId);
    }

    if (selectedParticipants.isEmpty && widget.household.members.isNotEmpty) {
      selectedParticipants.addAll(widget.household.members);
    }

    selectedPayer ??= widget.household.members.isNotEmpty
        ? widget.household.members.first
        : null;

    loadCurrentUser();
  }

  @override
  void dispose() {
    amountController.removeListener(refreshPreview);
    titleController.dispose();
    amountController.dispose();
    noteController.dispose();
    super.dispose();
  }

  Future<void> loadCurrentUser() async {
    final savedEmail = await ApiService.getSavedEmail();
    if (!mounted) return;

    final email = savedEmail?.trim().toLowerCase() ?? '';
    final matchedMember = email.isEmpty
        ? null
        : widget.household.members.where((member) {
            return getMemberEmail(member).trim().toLowerCase() == email;
          }).firstOrNull;

    setState(() {
      currentEmail = email;
      if (!isEditMode && matchedMember != null) {
        selectedPayer = matchedMember;
      }
    });
  }

  void refreshPreview() {
    if (mounted) {
      setState(() {
        formError = null;
      });
    }
  }

  String formatInputAmount(double value) {
    if (value <= 0) return '';

    return value.toStringAsFixed(0);
  }

  String formatMoney(double amount) {
    return amount
        .toStringAsFixed(0)
        .replaceAllMapped(RegExp(r'\B(?=(\d{3})+(?!\d))'), (match) => '.');
  }

  String formatApiDate(DateTime date) {
    final year = date.year.toString().padLeft(4, '0');
    final month = date.month.toString().padLeft(2, '0');
    final day = date.day.toString().padLeft(2, '0');

    return '$year-$month-$day';
  }

  String formatDisplayDate(DateTime date) {
    final weekdays = [
      'Thứ hai',
      'Thứ ba',
      'Thứ tư',
      'Thứ năm',
      'Thứ sáu',
      'Thứ bảy',
      'Chủ nhật',
    ];

    return '${weekdays[date.weekday - 1]}, ${date.day}/${date.month}/${date.year}';
  }

  String formatMonth(DateTime date) {
    return 'Tháng ${date.month}/${date.year}';
  }

  DateTime dateOnly(DateTime date) {
    return DateTime(date.year, date.month, date.day);
  }

  Future<void> pickExpenseDate() async {
    if (isLoading) return;

    final now = dateOnly(DateTime.now());
    final firstDate = DateTime(2000);
    var visibleMonth = DateTime(
      selectedExpenseDate.year,
      selectedExpenseDate.month,
    );

    final picked = await showModalBottomSheet<DateTime>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) {
        return StatefulBuilder(
          builder: (context, setSheetState) {
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
                      height: 4,
                      decoration: BoxDecoration(
                        color: AppColors.borderStrong,
                        borderRadius: BorderRadius.circular(99),
                      ),
                    ),
                    const SizedBox(height: 18),
                    Row(
                      children: [
                        const Expanded(
                          child: Text(
                            'Chọn ngày chi',
                            style: TextStyle(
                              color: AppColors.textDark,
                              fontSize: 20,
                              fontWeight: FontWeight.w900,
                            ),
                          ),
                        ),
                        IconButton(
                          onPressed:
                              visibleMonth.year == firstDate.year &&
                                  visibleMonth.month == firstDate.month
                              ? null
                              : () {
                                  setSheetState(() {
                                    visibleMonth = DateTime(
                                      visibleMonth.year,
                                      visibleMonth.month - 1,
                                    );
                                  });
                                },
                          icon: const Icon(Icons.chevron_left_rounded),
                        ),
                        IconButton(
                          onPressed:
                              visibleMonth.year == now.year &&
                                  visibleMonth.month == now.month
                              ? null
                              : () {
                                  setSheetState(() {
                                    visibleMonth = DateTime(
                                      visibleMonth.year,
                                      visibleMonth.month + 1,
                                    );
                                  });
                                },
                          icon: const Icon(Icons.chevron_right_rounded),
                        ),
                      ],
                    ),
                    const SizedBox(height: 4),
                    Align(
                      alignment: Alignment.centerLeft,
                      child: Text(
                        formatMonth(visibleMonth),
                        style: const TextStyle(
                          color: AppColors.primary,
                          fontSize: 15,
                          fontWeight: FontWeight.w900,
                        ),
                      ),
                    ),
                    const SizedBox(height: 14),
                    buildVietnameseCalendar(
                      visibleMonth: visibleMonth,
                      selectedDate: selectedExpenseDate,
                      firstDate: firstDate,
                      lastDate: now,
                      onPicked: (date) {
                        Navigator.pop(context, date);
                      },
                    ),
                  ],
                ),
              ),
            );
          },
        );
      },
    );

    if (picked == null || !mounted) return;

    setState(() {
      selectedExpenseDate = picked;
      formError = null;
    });
  }

  Widget buildVietnameseCalendar({
    required DateTime visibleMonth,
    required DateTime selectedDate,
    required DateTime firstDate,
    required DateTime lastDate,
    required ValueChanged<DateTime> onPicked,
  }) {
    const weekDays = ['T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'CN'];
    final monthStart = DateTime(visibleMonth.year, visibleMonth.month);
    final leadingDays = monthStart.weekday - 1;
    final daysInMonth = DateTime(
      visibleMonth.year,
      visibleMonth.month + 1,
      0,
    ).day;
    final cells = leadingDays + daysInMonth;
    final rowCount = (cells / 7).ceil();
    final totalCells = rowCount * 7;

    return Column(
      children: [
        Row(
          children: weekDays
              .map(
                (day) => Expanded(
                  child: Center(
                    child: Text(
                      day,
                      style: const TextStyle(
                        color: AppColors.textLight,
                        fontSize: 12,
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                  ),
                ),
              )
              .toList(),
        ),
        const SizedBox(height: 8),
        GridView.builder(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          itemCount: totalCells,
          gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
            crossAxisCount: 7,
            mainAxisSpacing: 7,
            crossAxisSpacing: 7,
          ),
          itemBuilder: (context, index) {
            final dayNumber = index - leadingDays + 1;

            if (dayNumber < 1 || dayNumber > daysInMonth) {
              return const SizedBox.shrink();
            }

            final date = DateTime(
              visibleMonth.year,
              visibleMonth.month,
              dayNumber,
            );
            final normalizedDate = dateOnly(date);
            final isSelected = normalizedDate == dateOnly(selectedDate);
            final isToday = normalizedDate == dateOnly(DateTime.now());
            final isDisabled =
                normalizedDate.isBefore(firstDate) ||
                normalizedDate.isAfter(lastDate);

            return Material(
              color: isSelected
                  ? AppColors.primary
                  : isToday
                  ? AppColors.primary.withValues(alpha: 0.08)
                  : AppColors.surfaceTint,
              borderRadius: BorderRadius.circular(13),
              child: InkWell(
                onTap: isDisabled ? null : () => onPicked(normalizedDate),
                borderRadius: BorderRadius.circular(13),
                child: Center(
                  child: Text(
                    dayNumber.toString(),
                    style: TextStyle(
                      color: isDisabled
                          ? AppColors.textMuted
                          : isSelected
                          ? Colors.white
                          : AppColors.textDark,
                      fontSize: 14,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                ),
              ),
            );
          },
        ),
        const SizedBox(height: 14),
        Row(
          children: [
            Expanded(
              child: OutlinedButton(
                onPressed: () => Navigator.pop(context),
                child: const Text('Hủy'),
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: FilledButton(
                onPressed: () =>
                    Navigator.pop(context, dateOnly(DateTime.now())),
                child: const Text('Hôm nay'),
              ),
            ),
          ],
        ),
      ],
    );
  }

  dynamic findMemberByUserId(int userId) {
    if (userId == 0) return null;

    for (final member in widget.household.members) {
      if (getMemberId(member) == userId) {
        return member;
      }
    }

    return null;
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

  bool getMemberIsVirtual(dynamic member) {
    try {
      return member.isVirtual == true;
    } catch (_) {
      return getMemberEmail(member).endsWith('@virtual.chungvi.local');
    }
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
    return email.isNotEmpty ? email : 'Thành viên';
  }

  int getMemberId(dynamic member) {
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

  String getMemberAvatar(dynamic member) {
    String rawAvatar = '';

    try {
      rawAvatar = member.userAvatar?.toString().trim() ?? '';
    } catch (_) {}

    if (rawAvatar.isEmpty) {
      try {
        rawAvatar = member.avatarUrl?.toString().trim() ?? '';
      } catch (_) {}
    }

    if (rawAvatar.isEmpty) {
      try {
        rawAvatar = member.avatar_url?.toString().trim() ?? '';
      } catch (_) {}
    }

    if (rawAvatar.isEmpty) {
      try {
        rawAvatar = member.avatar?.toString().trim() ?? '';
      } catch (_) {}
    }

    if (rawAvatar.isNotEmpty) {
      return ApiService.resolveMediaUrl(rawAvatar);
    }

    final userId = getMemberId(member);

    if (userId <= 0 || getMemberIsVirtual(member)) {
      return '';
    }

    return ApiService.userAvatarUrl(userId);
  }

  Widget buildMemberAvatar({
    required String name,
    required String avatarUrl,
    required bool isVirtual,
    required bool isSelected,
    double size = 42,
  }) {
    final firstLetter = name.trim().isNotEmpty
        ? name.trim().characters.first.toUpperCase()
        : '?';

    Widget fallbackAvatar() {
      return Container(
        width: size,
        height: size,
        decoration: BoxDecoration(
          color: isVirtual
              ? const Color(0xFFE1F3FE)
              : isSelected
              ? AppColors.primary
              : AppColors.primary.withValues(alpha: 0.10),
          borderRadius: BorderRadius.circular(15),
        ),
        alignment: Alignment.center,
        child: isVirtual
            ? const Icon(
                Icons.person_outline_rounded,
                color: Color(0xFF1F6C9F),
                size: 21,
              )
            : Text(
                firstLetter,
                style: TextStyle(
                  color: isSelected ? Colors.white : AppColors.primaryDark,
                  fontWeight: FontWeight.w900,
                ),
              ),
      );
    }

    if (isVirtual || avatarUrl.trim().isEmpty) {
      return fallbackAvatar();
    }

    return ClipRRect(
      borderRadius: BorderRadius.circular(15),
      child: SizedBox(
        width: size,
        height: size,
        child: Image.network(
          avatarUrl,
          key: ValueKey(avatarUrl),
          fit: BoxFit.cover,
          errorBuilder: (_, _, _) {
            return fallbackAvatar();
          },
        ),
      ),
    );
  }

  double? parseAmount(String value) {
    try {
      final result = _AmountExpressionParser(value).parse();
      if (result.isNaN || result.isInfinite) return null;
      return result;
    } catch (_) {
      return null;
    }
  }

  double? get amountValue => parseAmount(amountController.text);

  double get sharePreview {
    final amount = amountValue;

    if (amount == null || amount <= 0 || selectedParticipants.isEmpty) {
      return 0;
    }

    return amount / selectedParticipants.length;
  }

  String get payerText {
    final payer = selectedPayer;
    if (payer != null) {
      final name = getMemberName(payer);
      final email = getMemberEmail(payer);
      if (name.trim().isNotEmpty && name != email) return name;
      if (email.trim().isNotEmpty) return email;
    }

    if (currentEmail.isNotEmpty) return currentEmail;
    return 'Tài khoản hiện tại';
  }

  Future<void> submitExpense() async {
    if (isLoading) return;

    final title = titleController.text.trim();
    final amount = amountValue;

    if (widget.household.members.isEmpty) {
      showValidation('Nhóm chưa có thành viên để chia tiền');
      return;
    }

    if (title.isEmpty) {
      showValidation('Nhập tên khoản chi');
      return;
    }

    if (amount == null || amount <= 0) {
      showValidation('Nhập số tiền hoặc phép tính hợp lệ');
      return;
    }

    if (selectedParticipants.isEmpty) {
      showValidation('Chọn ít nhất một người tham gia');
      return;
    }

    final participantIds = selectedParticipants
        .map<int>((member) => getMemberId(member))
        .where((id) => id != 0)
        .toSet()
        .toList();

    if (participantIds.isEmpty) {
      showValidation('Dữ liệu thành viên không hợp lệ');
      return;
    }

    final expenseDate = formatApiDate(selectedExpenseDate);

    try {
      setState(() {
        isLoading = true;
        formError = null;
      });

      if (isEditMode) {
        await ApiService.updateExpense(
          expenseId: widget.expense!.id,
          title: title,
          amount: amount,
          expenseDate: expenseDate,
          participants: participantIds,
          note: noteController.text.trim(),
        );
      } else {
        await ApiService.createExpense(
          householdId: widget.household.id,
          title: title,
          amount: amount,
          expenseDate: expenseDate,
          participants: participantIds,
          note: noteController.text.trim(),
        );
      }

      if (!mounted) return;

      showMessage(isEditMode ? 'Đã cập nhật khoản chi' : 'Đã thêm khoản chi');
      Navigator.pop(context, true);
    } catch (e) {
      if (!mounted) return;

      showValidation(e.toString());
    } finally {
      if (mounted) {
        setState(() => isLoading = false);
      }
    }
  }

  void showValidation(String message) {
    setState(() {
      formError = message;
    });

    showMessage(message);
  }

  void showMessage(String message) {
    ScaffoldMessenger.of(
      context,
    ).showSnackBar(SnackBar(content: Text(message)));
  }

  Widget buildAmountPanel() {
    final amount = amountValue;
    final hasExpression = amountController.text.trim().isNotEmpty;
    final hasValidAmount = amount != null && amount > 0;
    final hasFormulaHint =
        hasValidAmount &&
        RegExp(r'[+\-*/xX×÷:()]').hasMatch(amountController.text);

    return Container(
      padding: const EdgeInsets.fromLTRB(20, 18, 20, 18),
      decoration: BoxDecoration(
        color: AppColors.primary,
        borderRadius: BorderRadius.circular(28),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Expanded(
                child: Text(
                  'Số tiền',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 18,
                    fontWeight: FontWeight.w900,
                  ),
                ),
              ),
              Text(
                hasValidAmount ? '${formatMoney(amount)}đ' : '0đ',
                style: TextStyle(
                  color: Colors.white.withValues(alpha: 0.76),
                  fontSize: 13,
                  fontWeight: FontWeight.w900,
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          Container(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 8),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(20),
            ),
            child: Row(
              children: [
                const Text(
                  'đ',
                  style: TextStyle(
                    color: AppColors.primary,
                    fontSize: 28,
                    fontWeight: FontWeight.w900,
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: TextField(
                    controller: amountController,
                    enabled: !isLoading,
                    keyboardType: TextInputType.text,
                    inputFormatters: [
                      FilteringTextInputFormatter.allow(
                        RegExp(r'[0-9+\-*/xX×÷:.,()\s]'),
                      ),
                    ],
                    style: const TextStyle(
                      color: AppColors.textDark,
                      fontSize: 31,
                      fontWeight: FontWeight.w900,
                      letterSpacing: 0,
                    ),
                    decoration: const InputDecoration(
                      border: InputBorder.none,
                      enabledBorder: InputBorder.none,
                      focusedBorder: InputBorder.none,
                      filled: false,
                      hintText: '0',
                      hintStyle: TextStyle(
                        color: AppColors.textMuted,
                        fontSize: 31,
                        fontWeight: FontWeight.w800,
                      ),
                      contentPadding: EdgeInsets.zero,
                    ),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 12),
          Text(
            hasFormulaHint
                ? 'Kết quả: ${formatMoney(amount)}đ'
                : hasExpression && !hasValidAmount
                ? 'Có thể nhập phép tính như 120000 + 45000 / 3'
                : 'Có thể nhập phép tính: 120000 + 45000',
            style: TextStyle(
              color: hasExpression && !hasValidAmount
                  ? const Color(0xFFFFB4AE)
                  : Colors.white.withValues(alpha: 0.78),
              fontSize: 13,
              fontWeight: FontWeight.w700,
              height: 1.35,
            ),
          ),
        ],
      ),
    );
  }

  Widget buildDetailsPanel() {
    return buildSurface(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          buildPanelHeader(
            title: 'Thông tin khoản chi',
            subtitle: widget.household.name.trim().isEmpty
                ? 'Nhóm hiện tại'
                : widget.household.name,
          ),
          const SizedBox(height: 16),
          buildTextInput(
            controller: titleController,
            hint: 'Tên khoản chi',
            icon: Icons.receipt_long_rounded,
          ),
          const SizedBox(height: 12),
          buildCategorySuggestions(),
          const SizedBox(height: 12),
          buildExpenseDateCard(),
          const SizedBox(height: 12),
          buildHouseholdCard(),
          const SizedBox(height: 12),
          buildPayerCard(),
          const SizedBox(height: 12),
          buildTextInput(
            controller: noteController,
            hint: 'Ghi chú',
            icon: Icons.notes_rounded,
            maxLines: 3,
          ),
        ],
      ),
    );
  }

  Widget buildCategorySuggestions() {
    const categories = ['Ăn uống', 'Di chuyển', 'Nhà cửa', 'Mua sắm', 'Khác'];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Gợi ý danh mục',
          style: TextStyle(
            color: AppColors.textLight,
            fontSize: 12,
            fontWeight: FontWeight.w800,
          ),
        ),
        const SizedBox(height: 8),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: categories.map((category) {
            final isSelected =
                titleController.text.trim().toLowerCase() ==
                category.toLowerCase();

            return ChoiceChip(
              selected: isSelected,
              label: Text(category),
              onSelected: isLoading
                  ? null
                  : (_) {
                      setState(() {
                        titleController.text = category;
                        formError = null;
                      });
                    },
              showCheckmark: false,
              selectedColor: AppColors.primary.withValues(alpha: 0.12),
              backgroundColor: AppColors.surfaceTint,
              side: BorderSide(
                color: isSelected
                    ? AppColors.primary.withValues(alpha: 0.28)
                    : AppColors.border,
              ),
              labelStyle: TextStyle(
                color: isSelected ? AppColors.primaryDark : AppColors.textDark,
                fontSize: 13,
                fontWeight: FontWeight.w800,
              ),
            );
          }).toList(),
        ),
      ],
    );
  }

  Widget buildTextInput({
    required TextEditingController controller,
    required String hint,
    required IconData icon,
    int maxLines = 1,
  }) {
    final isMultiline = maxLines > 1;

    return TextField(
      controller: controller,
      enabled: !isLoading,
      maxLines: maxLines,
      minLines: maxLines,
      style: const TextStyle(
        fontSize: 15,
        fontWeight: FontWeight.w700,
        color: AppColors.textDark,
      ),
      decoration: InputDecoration(
        hintText: hint,
        fillColor: AppColors.surfaceTint,
        prefixIcon: Padding(
          padding: EdgeInsets.only(
            left: 15,
            right: 10,
            top: isMultiline ? 18 : 0,
          ),
          child: Icon(icon, color: AppColors.textLight, size: 21),
        ),
        prefixIconConstraints: BoxConstraints(
          minWidth: 48,
          minHeight: isMultiline ? 58 : 54,
        ),
        contentPadding: EdgeInsets.symmetric(
          horizontal: 16,
          vertical: isMultiline ? 18 : 16,
        ),
      ),
    );
  }

  Widget buildExpenseDateCard() {
    return buildActionRow(
      icon: Icons.event_rounded,
      label: 'Ngày chi',
      value: formatDisplayDate(selectedExpenseDate),
      onTap: pickExpenseDate,
    );
  }

  Widget buildHouseholdCard() {
    return buildActionRow(
      icon: Icons.groups_rounded,
      label: 'Nhóm ví',
      value: widget.household.name.trim().isEmpty
          ? 'Nhóm hiện tại'
          : widget.household.name.trim(),
      helper: 'Đã chọn từ màn hình trước',
      onTap: null,
    );
  }

  Widget buildPayerCard() {
    final payer = selectedPayer;
    final avatarUrl = payer == null ? '' : getMemberAvatar(payer);
    final isVirtual = payer != null && getMemberIsVirtual(payer);

    return buildActionRow(
      icon: Icons.account_circle_rounded,
      label: 'Người trả',
      value: payerText,
      leading: payer == null
          ? null
          : buildMemberAvatar(
              name: payerText,
              avatarUrl: avatarUrl,
              isVirtual: isVirtual,
              isSelected: false,
              size: 38,
            ),
      helper: 'Theo tài khoản đang đăng nhập',
      onTap: null,
    );
  }

  Widget buildActionRow({
    required IconData icon,
    required String label,
    required String value,
    required VoidCallback? onTap,
    Widget? leading,
    String? helper,
  }) {
    return Material(
      color: AppColors.surfaceTint,
      borderRadius: BorderRadius.circular(18),
      child: InkWell(
        onTap: isLoading ? null : onTap,
        borderRadius: BorderRadius.circular(18),
        child: Container(
          padding: const EdgeInsets.fromLTRB(14, 12, 12, 12),
          child: Row(
            children: [
              leading ??
                  Container(
                    width: 38,
                    height: 38,
                    decoration: BoxDecoration(
                      color: AppColors.primary.withValues(alpha: 0.09),
                      borderRadius: BorderRadius.circular(13),
                    ),
                    child: Icon(icon, color: AppColors.primary, size: 20),
                  ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      label,
                      style: const TextStyle(
                        color: AppColors.textLight,
                        fontSize: 12,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                    const SizedBox(height: 3),
                    Text(
                      value,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        color: AppColors.textDark,
                        fontSize: 15,
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                    if (helper != null) ...[
                      const SizedBox(height: 3),
                      Text(
                        helper,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          color: AppColors.textMuted,
                          fontSize: 11,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ],
                  ],
                ),
              ),
              if (onTap != null)
                const Icon(
                  Icons.keyboard_arrow_down_rounded,
                  color: AppColors.textLight,
                ),
            ],
          ),
        ),
      ),
    );
  }

  Widget buildParticipantSection() {
    final allSelected =
        selectedParticipants.length == widget.household.members.length;

    return buildSurface(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: buildPanelHeader(
                  title: 'Người tham gia',
                  subtitle:
                      '${selectedParticipants.length}/${widget.household.members.length} thành viên được chia đều',
                ),
              ),
              TextButton(
                onPressed: isLoading
                    ? null
                    : () {
                        setState(() {
                          formError = null;
                          if (allSelected) {
                            selectedParticipants.clear();
                          } else {
                            selectedParticipants
                              ..clear()
                              ..addAll(widget.household.members);
                          }
                        });
                      },
                child: Text(allSelected ? 'Bỏ chọn' : 'Chọn tất cả'),
              ),
            ],
          ),
          const SizedBox(height: 14),
          ...widget.household.members.map(buildParticipantTile),
        ],
      ),
    );
  }

  Widget buildParticipantTile(dynamic member) {
    final isSelected = selectedParticipants.contains(member);
    final name = getMemberName(member);
    final email = getMemberEmail(member);
    final isVirtual = getMemberIsVirtual(member);
    final avatarUrl = getMemberAvatar(member);

    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Material(
        color: isSelected
            ? AppColors.primary.withValues(alpha: 0.08)
            : AppColors.surfaceTint,
        borderRadius: BorderRadius.circular(18),
        child: InkWell(
          onTap: isLoading
              ? null
              : () {
                  setState(() {
                    formError = null;
                    if (isSelected) {
                      selectedParticipants.remove(member);
                    } else {
                      selectedParticipants.add(member);
                    }
                  });
                },
          borderRadius: BorderRadius.circular(18),
          child: Container(
            padding: const EdgeInsets.fromLTRB(12, 11, 12, 11),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(18),
              border: Border.all(
                color: isSelected
                    ? AppColors.primary.withValues(alpha: 0.28)
                    : Colors.transparent,
              ),
            ),
            child: Row(
              children: [
                buildMemberAvatar(
                  name: name,
                  avatarUrl: avatarUrl,
                  isVirtual: isVirtual,
                  isSelected: isSelected,
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        isVirtual ? name : (email.isNotEmpty ? email : name),
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          color: AppColors.textDark,
                          fontWeight: FontWeight.w900,
                          fontSize: 14,
                        ),
                      ),
                      const SizedBox(height: 3),
                      Text(
                        isVirtual ? 'Không dùng app' : 'Thành viên',
                        style: const TextStyle(
                          color: AppColors.textLight,
                          fontSize: 12,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ],
                  ),
                ),
                Container(
                  width: 28,
                  height: 28,
                  decoration: BoxDecoration(
                    color: isSelected ? AppColors.primary : Colors.white,
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(
                      color: isSelected
                          ? AppColors.primary
                          : AppColors.borderStrong,
                    ),
                  ),
                  child: Icon(
                    isSelected ? Icons.check_rounded : Icons.add_rounded,
                    color: isSelected ? Colors.white : AppColors.textLight,
                    size: 18,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget buildReviewPanel() {
    final amount = amountValue ?? 0;

    return buildSurface(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          buildPanelHeader(
            title: 'Xem lại trước khi lưu',
            subtitle: 'Đang dùng chế độ chia đều',
          ),
          const SizedBox(height: 16),
          buildReviewRow(
            'Tổng tiền',
            amount > 0 ? '${formatMoney(amount)}đ' : '0đ',
          ),
          buildReviewRow(
            'Mỗi người',
            sharePreview > 0 ? '${formatMoney(sharePreview)}đ' : '0đ',
          ),
          buildReviewRow('Người trả', payerText),
          buildReviewRow(
            'Ngày chi',
            '${selectedExpenseDate.day}/${selectedExpenseDate.month}/${selectedExpenseDate.year}',
          ),
          if (formError != null) ...[
            const SizedBox(height: 12),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: const Color(0xFFFDEBEC),
                borderRadius: BorderRadius.circular(16),
              ),
              child: Text(
                formError!,
                style: const TextStyle(
                  color: Color(0xFF9F2F2D),
                  fontSize: 13,
                  fontWeight: FontWeight.w800,
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget buildReviewRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            child: Text(
              label,
              style: const TextStyle(
                color: AppColors.textLight,
                fontSize: 13,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
          const SizedBox(width: 12),
          Flexible(
            child: Text(
              value,
              textAlign: TextAlign.right,
              style: const TextStyle(
                color: AppColors.textDark,
                fontSize: 13,
                fontWeight: FontWeight.w900,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget buildPanelHeader({required String title, required String subtitle}) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          title,
          style: const TextStyle(
            color: AppColors.textDark,
            fontSize: 18,
            fontWeight: FontWeight.w900,
            height: 1.15,
          ),
        ),
        const SizedBox(height: 5),
        Text(
          subtitle,
          maxLines: 2,
          overflow: TextOverflow.ellipsis,
          style: const TextStyle(
            color: AppColors.textLight,
            fontSize: 13,
            fontWeight: FontWeight.w600,
            height: 1.34,
          ),
        ),
      ],
    );
  }

  Widget buildSurface({required Widget child}) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(24),
      ),
      child: child,
    );
  }

  Widget buildSaveButton() {
    return SizedBox(
      width: double.infinity,
      height: 58,
      child: ElevatedButton(
        onPressed: isLoading ? null : submitExpense,
        child: isLoading
            ? const SizedBox(
                width: 22,
                height: 22,
                child: CircularProgressIndicator(
                  strokeWidth: 2.5,
                  color: Colors.white,
                ),
              )
            : Text(isEditMode ? 'Lưu thay đổi' : 'Lưu khoản chi'),
      ),
    );
  }

  Widget buildContent(double horizontalPadding) {
    return SingleChildScrollView(
      padding: EdgeInsets.fromLTRB(
        horizontalPadding,
        10,
        horizontalPadding,
        24,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            isEditMode ? 'Sửa khoản chi' : 'Thêm chi tiêu',
            style: const TextStyle(
              color: AppColors.textDark,
              fontSize: 28,
              fontWeight: FontWeight.w900,
              letterSpacing: -0.4,
              height: 1.05,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            widget.household.name.trim().isEmpty
                ? 'Ghi lại khoản chi và kiểm tra phần chia trước khi lưu.'
                : 'Nhóm ${widget.household.name}',
            style: const TextStyle(
              color: AppColors.textLight,
              fontSize: 14,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 18),
          buildAmountPanel(),
          const SizedBox(height: 16),
          buildDetailsPanel(),
          const SizedBox(height: 16),
          buildParticipantSection(),
          const SizedBox(height: 16),
          buildReviewPanel(),
          const SizedBox(height: 92),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final hasMembers = widget.household.members.isNotEmpty;
    final width = MediaQuery.sizeOf(context).width;
    final horizontalPadding = width >= 760
        ? (width - 720) / 2
        : width < 380
        ? 16.0
        : 20.0;

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(titleSpacing: 4, title: const SizedBox.shrink()),
      body: SafeArea(
        child: hasMembers
            ? Stack(
                children: [
                  buildContent(horizontalPadding),
                  Align(
                    alignment: Alignment.bottomCenter,
                    child: Container(
                      width: double.infinity,
                      padding: EdgeInsets.fromLTRB(
                        horizontalPadding,
                        10,
                        horizontalPadding,
                        14,
                      ),
                      decoration: BoxDecoration(
                        color: AppColors.background.withValues(alpha: 0.96),
                      ),
                      child: ConstrainedBox(
                        constraints: const BoxConstraints(maxWidth: 720),
                        child: buildSaveButton(),
                      ),
                    ),
                  ),
                ],
              )
            : const AppEmptyState(
                icon: Icons.people_outline_rounded,
                title: 'Chưa có thành viên',
                message: 'Nhóm cần có thành viên trước khi tạo khoản chi.',
              ),
      ),
    );
  }
}

class _AmountExpressionParser {
  final String source;
  int index = 0;

  _AmountExpressionParser(this.source);

  double parse() {
    final normalized = source.trim();
    if (normalized.isEmpty) {
      throw const FormatException('Empty amount');
    }

    final value = parseExpression();
    skipWhitespace();

    if (index != source.length) {
      throw const FormatException('Unexpected input');
    }

    return value;
  }

  double parseExpression() {
    var value = parseTerm();

    while (true) {
      skipWhitespace();

      if (match('+')) {
        value += parseTerm();
      } else if (match('-')) {
        value -= parseTerm();
      } else {
        return value;
      }
    }
  }

  double parseTerm() {
    var value = parseFactor();

    while (true) {
      skipWhitespace();

      if (match('*') || match('x') || match('X') || match('×')) {
        value *= parseFactor();
      } else if (match('/') || match(':') || match('÷')) {
        final divisor = parseFactor();
        if (divisor == 0) {
          throw const FormatException('Division by zero');
        }
        value /= divisor;
      } else {
        return value;
      }
    }
  }

  double parseFactor() {
    skipWhitespace();

    if (match('+')) return parseFactor();
    if (match('-')) return -parseFactor();

    if (match('(')) {
      final value = parseExpression();
      skipWhitespace();
      if (!match(')')) {
        throw const FormatException('Missing closing parenthesis');
      }
      return value;
    }

    return parseNumber();
  }

  double parseNumber() {
    skipWhitespace();
    final start = index;

    while (index < source.length) {
      final char = source[index];
      if (RegExp(r'[0-9.,]').hasMatch(char)) {
        index++;
      } else {
        break;
      }
    }

    if (start == index) {
      throw const FormatException('Expected number');
    }

    final raw = source.substring(start, index);
    final cleaned = raw.replaceAll('.', '').replaceAll(',', '');
    final value = double.tryParse(cleaned);

    if (value == null) {
      throw const FormatException('Invalid number');
    }

    return value;
  }

  bool match(String char) {
    if (index >= source.length || source[index] != char) {
      return false;
    }

    index++;
    return true;
  }

  void skipWhitespace() {
    while (index < source.length && source[index].trim().isEmpty) {
      index++;
    }
  }
}
