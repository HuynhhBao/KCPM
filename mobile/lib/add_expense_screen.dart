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

  const AddExpenseScreen({
    super.key,
    required this.household,
    this.expense,
  });

  @override
  State<AddExpenseScreen> createState() => _AddExpenseScreenState();
}

class _AddExpenseScreenState extends State<AddExpenseScreen> {
  final titleController = TextEditingController();
  final amountController = TextEditingController();
  final noteController = TextEditingController();

  DateTime selectedExpenseDate = DateTime.now();
  final List<dynamic> selectedParticipants = [];

  bool isLoading = false;

  bool get isEditMode => widget.expense != null;

  @override
  void initState() {
    super.initState();

    if (isEditMode) {
      titleController.text = widget.expense!.title;
      amountController.text = formatInputAmount(
        widget.expense!.amount,
      );
      noteController.text = widget.expense!.note;

      final parsedExpenseDate = DateTime.tryParse(
        widget.expense!.expenseDate,
      );

      if (parsedExpenseDate != null) {
        selectedExpenseDate = parsedExpenseDate;
      }

      final participantUserIds = widget.expense!.participants
          .map((participant) => participant.userId)
          .where((id) => id != 0)
          .toSet();

      selectedParticipants.addAll(
        widget.household.members.where(
          (member) => participantUserIds.contains(
            getMemberId(member),
          ),
        ),
      );
    }

    if (selectedParticipants.isEmpty &&
        widget.household.members.isNotEmpty) {
      selectedParticipants.addAll(
        widget.household.members,
      );
    }
  }

  @override
  void dispose() {
    titleController.dispose();
    amountController.dispose();
    noteController.dispose();
    super.dispose();
  }

  String formatInputAmount(double value) {
    if (value <= 0) return '';

    return value.toStringAsFixed(0);
  }

  String formatMoney(double amount) {
    return amount.toStringAsFixed(0).replaceAllMapped(
          RegExp(r'\B(?=(\d{3})+(?!\d))'),
          (match) => '.',
        );
  }

  String formatApiDate(DateTime date) {
    final year = date.year.toString().padLeft(4, '0');
    final month = date.month.toString().padLeft(2, '0');
    final day = date.day.toString().padLeft(2, '0');

    return '$year-$month-$day';
  }

  String formatDisplayDate(DateTime date) {
    final day = date.day.toString().padLeft(2, '0');
    final month = date.month.toString().padLeft(2, '0');

    return '$day/$month/${date.year}';
  }

  Future<void> pickExpenseDate() async {
    if (isLoading) return;

    final now = DateTime.now();

    final picked = await showDatePicker(
      context: context,
      initialDate: selectedExpenseDate.isAfter(now)
          ? now
          : selectedExpenseDate,
      firstDate: DateTime(2000),
      lastDate: now,
      helpText: 'Chọn ngày chi',
      cancelText: 'Hủy',
      confirmText: 'Chọn',
    );

    if (picked == null || !mounted) return;

    setState(() {
      selectedExpenseDate = picked;
    });
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
  }) {
    final firstLetter = name.trim().isNotEmpty
        ? name.trim()[0].toUpperCase()
        : '?';

    Widget fallbackAvatar() {
      return CircleAvatar(
        radius: 20,
        backgroundColor: isVirtual
            ? const Color(0xFFE0F2FE)
            : isSelected
                ? AppColors.primary
                : AppColors.primary.withValues(alpha: 0.12),
        child: isVirtual
            ? const Icon(
                Icons.person_outline_rounded,
                color: Color(0xFF0284C7),
                size: 21,
              )
            : Text(
                firstLetter,
                style: TextStyle(
                  color: isSelected ? Colors.white : AppColors.primary,
                  fontWeight: FontWeight.w900,
                ),
              ),
      );
    }

    if (isVirtual || avatarUrl.trim().isEmpty) {
      return fallbackAvatar();
    }

    return ClipOval(
      child: SizedBox(
        width: 40,
        height: 40,
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
    final cleaned = value
        .replaceAll('.', '')
        .replaceAll(',', '')
        .replaceAll('đ', '')
        .trim();

    return double.tryParse(cleaned);
  }

  double get sharePreview {
    final amount = parseAmount(amountController.text);

    if (amount == null ||
        amount <= 0 ||
        selectedParticipants.isEmpty) {
      return 0;
    }

    return amount / selectedParticipants.length;
  }

  Future<void> submitExpense() async {
    if (isLoading) return;

    final title = titleController.text.trim();
    final amount = parseAmount(amountController.text);

    if (widget.household.members.isEmpty) {
      showMessage('Nhóm chưa có thành viên để chia tiền');
      return;
    }

    if (title.isEmpty) {
      showMessage('Nhập tên khoản chi');
      return;
    }

    if (amount == null || amount <= 0) {
      showMessage('Nhập số tiền hợp lệ');
      return;
    }

    if (selectedParticipants.isEmpty) {
      showMessage('Chọn người tham gia');
      return;
    }

    final participantIds = selectedParticipants
        .map<int>((member) => getMemberId(member))
        .where((id) => id != 0)
        .toSet()
        .toList();

    if (participantIds.isEmpty) {
      showMessage('Dữ liệu thành viên không hợp lệ');
      return;
    }

    final expenseDate = formatApiDate(selectedExpenseDate);

    try {
      setState(() => isLoading = true);

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

      showMessage(
        isEditMode
            ? 'Đã cập nhật khoản chi'
            : 'Đã thêm khoản chi',
      );

      Navigator.pop(context, true);
    } catch (e) {
      if (!mounted) return;

      showMessage(e.toString());
    } finally {
      if (mounted) {
        setState(() => isLoading = false);
      }
    }
  }

  void showMessage(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message)),
    );
  }

  Widget buildAmountCard() {
    return Container(
      padding: const EdgeInsets.all(22),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [
            AppColors.primary,
            AppColors.secondary,
          ],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(30),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Số tiền',
            style: TextStyle(
              color: Colors.white70,
              fontSize: 15,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 14),
          Container(
            height: 72,
            padding: const EdgeInsets.symmetric(horizontal: 18),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(22),
            ),
            child: Row(
              children: [
                const Text(
                  '₫',
                  style: TextStyle(
                    color: AppColors.primary,
                    fontSize: 30,
                    fontWeight: FontWeight.w900,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: TextField(
                    controller: amountController,
                    enabled: !isLoading,
                    keyboardType: TextInputType.number,
                    inputFormatters: [
                      FilteringTextInputFormatter.digitsOnly,
                    ],
                    onChanged: (_) => setState(() {}),
                    style: const TextStyle(
                      color: AppColors.textDark,
                      fontSize: 30,
                      fontWeight: FontWeight.w900,
                      letterSpacing: -0.7,
                    ),
                    decoration: const InputDecoration(
                      border: InputBorder.none,
                      enabledBorder: InputBorder.none,
                      focusedBorder: InputBorder.none,
                      filled: false,
                      hintText: '0',
                      hintStyle: TextStyle(
                        color: AppColors.textLight,
                        fontSize: 30,
                        fontWeight: FontWeight.w800,
                      ),
                      contentPadding: EdgeInsets.zero,
                    ),
                  ),
                ),
              ],
            ),
          ),
          if (sharePreview > 0) ...[
            const SizedBox(height: 12),
            Text(
              'Chia đều: khoảng ${formatMoney(sharePreview)}đ / người',
              style: const TextStyle(
                color: Colors.white,
                fontWeight: FontWeight.w800,
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget buildInput({
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
        fontWeight: FontWeight.w600,
        color: AppColors.textDark,
      ),
      decoration: InputDecoration(
        hintText: hint,
        prefixIcon: Padding(
          padding: EdgeInsets.only(
            left: 16,
            right: 12,
            top: isMultiline ? 18 : 0,
          ),
          child: Icon(
            icon,
            color: AppColors.textLight,
            size: 22,
          ),
        ),
        prefixIconConstraints: BoxConstraints(
          minWidth: 50,
          minHeight: isMultiline ? 56 : 52,
        ),
        contentPadding: EdgeInsets.symmetric(
          horizontal: 16,
          vertical: isMultiline ? 18 : 16,
        ),
      ),
    );
  }

  Widget buildSectionTitle(String title) {
    return Align(
      alignment: Alignment.centerLeft,
      child: Text(
        title,
        style: const TextStyle(
          fontSize: 19,
          fontWeight: FontWeight.w900,
          color: AppColors.textDark,
          letterSpacing: -0.4,
        ),
      ),
    );
  }

  Widget buildExpenseDateCard() {
    return InkWell(
      onTap: pickExpenseDate,
      borderRadius: BorderRadius.circular(22),
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(22),
          border: Border.all(color: AppColors.border),
        ),
        child: Row(
          children: [
            Container(
              width: 42,
              height: 42,
              decoration: BoxDecoration(
                color: AppColors.primary.withValues(alpha: 0.10),
                borderRadius: BorderRadius.circular(14),
              ),
              child: const Icon(
                Icons.event_rounded,
                color: AppColors.primary,
              ),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Ngày chi',
                    style: TextStyle(
                      color: AppColors.textLight,
                      fontSize: 13,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    formatDisplayDate(selectedExpenseDate),
                    style: const TextStyle(
                      color: AppColors.textDark,
                      fontSize: 16,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                ],
              ),
            ),
            const Icon(
              Icons.keyboard_arrow_down_rounded,
              color: AppColors.textLight,
            ),
          ],
        ),
      ),
    );
  }

  Widget buildSplitTypeCard() {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.primary.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(22),
        border: Border.all(
          color: AppColors.primary.withValues(alpha: 0.16),
        ),
      ),
      child: const Row(
        children: [
          Icon(
            Icons.call_split_rounded,
            color: AppColors.primary,
          ),
          SizedBox(width: 12),
          Expanded(
            child: Text(
              'Đang dùng chế độ chia đều cho các thành viên được chọn.',
              style: TextStyle(
                color: AppColors.textDark,
                fontWeight: FontWeight.w700,
                height: 1.35,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget buildParticipantSection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        buildSectionTitle('Người tham gia chia tiền'),
        const SizedBox(height: 14),
        ...widget.household.members.map(buildParticipantTile),
      ],
    );
  }

  Widget buildParticipantTile(dynamic member) {
    final isSelected = selectedParticipants.contains(member);
    final name = getMemberName(member);
    final email = getMemberEmail(member);
    final isVirtual = getMemberIsVirtual(member);
    final avatarUrl = getMemberAvatar(member);

    return GestureDetector(
      onTap: isLoading
          ? null
          : () {
              setState(() {
                if (isSelected) {
                  selectedParticipants.remove(member);
                } else {
                  selectedParticipants.add(member);
                }
              });
            },
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 180),
        margin: const EdgeInsets.only(bottom: 10),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: isSelected ? AppColors.primary : AppColors.border,
            width: isSelected ? 1.4 : 1,
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
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          isVirtual ? name : (email.isNotEmpty ? email : name),
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(
                            color: AppColors.textDark,
                            fontWeight: FontWeight.w800,
                            fontSize: 15,
                          ),
                        ),
                      ),
                      if (isVirtual) ...[
                        const SizedBox(width: 8),
                        Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 8,
                            vertical: 3,
                          ),
                          decoration: BoxDecoration(
                            color: Colors.blue.withValues(alpha: 0.12),
                            borderRadius: BorderRadius.circular(999),
                          ),
                          child: const Text(
                            'Ảo',
                            style: TextStyle(
                              color: Colors.blue,
                              fontSize: 11,
                              fontWeight: FontWeight.w900,
                            ),
                          ),
                        ),
                      ],
                    ],
                  ),
                  if (isVirtual)
                    const Padding(
                      padding: EdgeInsets.only(top: 3),
                      child: Text(
                        'Không dùng app',
                        style: TextStyle(
                          color: AppColors.textLight,
                          fontSize: 12,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ),
                ],
              ),
            ),
            Icon(
              isSelected
                  ? Icons.check_circle_rounded
                  : Icons.add_circle_outline_rounded,
              color: isSelected ? AppColors.primary : AppColors.textLight,
            ),
          ],
        ),
      ),
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
            : Text(
                isEditMode
                    ? 'Lưu thay đổi'
                    : 'Lưu khoản chi',
              ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final hasMembers = widget.household.members.isNotEmpty;

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        titleSpacing: 20,
        title: Text(
          isEditMode
              ? 'Sửa khoản chi'
              : 'Thêm khoản chi',
        ),
      ),
      body: SafeArea(
        child: hasMembers
            ? Column(
                children: [
                  Expanded(
                    child: SingleChildScrollView(
                      padding: const EdgeInsets.all(20),
                      child: Column(
                        children: [
                          buildAmountCard(),
                          const SizedBox(height: 22),
                          buildInput(
                            controller: titleController,
                            hint: 'Tên khoản chi',
                            icon: Icons.receipt_long_rounded,
                          ),
                          const SizedBox(height: 16),
                          buildExpenseDateCard(),
                          const SizedBox(height: 16),
                          buildInput(
                            controller: noteController,
                            hint: 'Ghi chú',
                            icon: Icons.notes_rounded,
                            maxLines: 2,
                          ),
                          const SizedBox(height: 20),
                          buildSplitTypeCard(),
                          const SizedBox(height: 28),
                          buildParticipantSection(),
                          const SizedBox(height: 24),
                        ],
                      ),
                    ),
                  ),
                  Container(
                    padding:
                        const EdgeInsets.fromLTRB(20, 12, 20, 20),
                    decoration: BoxDecoration(
                      color: AppColors.background,
                      boxShadow: [
                        BoxShadow(
                          color: Colors.black.withValues(alpha: 0.04),
                          blurRadius: 18,
                          offset: const Offset(0, -6),
                        ),
                      ],
                    ),
                    child: buildSaveButton(),
                  ),
                ],
              )
            : const AppEmptyState(
                icon: Icons.people_outline_rounded,
                title: 'Chưa có thành viên',
                message:
                    'Nhóm cần có thành viên trước khi tạo khoản chi.',
              ),
      ),
    );
  }
}
