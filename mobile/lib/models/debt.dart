class Debt {
  final String id;

  final String expenseId;
  final String expenseTitle;

  final String fromUserName;
  final String fromUserEmail;
  final String fromUserAvatar;
  final bool fromUserIsVirtual;

  final String toUserName;
  final String toUserEmail;
  final String toUserAvatar;
  final bool toUserIsVirtual;

  final bool hasVirtualMember;

  final String bankName;
  final String bankAccountNumber;
  final String bankAccountHolder;

  final double amount;

  final bool isPaid;

  final String? pendingPaymentId;
  final String pendingPaymentStatus;

  final bool canMarkPaid;
  final bool canConfirmPayment;

  Debt({
    required this.id,
    required this.expenseId,
    required this.expenseTitle,
    required this.fromUserName,
    required this.fromUserEmail,
    required this.fromUserAvatar,
    required this.fromUserIsVirtual,
    required this.toUserName,
    required this.toUserEmail,
    required this.toUserAvatar,
    required this.toUserIsVirtual,
    required this.hasVirtualMember,
    required this.bankName,
    required this.bankAccountNumber,
    required this.bankAccountHolder,
    required this.amount,
    required this.isPaid,
    required this.pendingPaymentId,
    required this.pendingPaymentStatus,
    required this.canMarkPaid,
    required this.canConfirmPayment,
  });

  bool get hasPendingPayment {
    return pendingPaymentId != null &&
        pendingPaymentId!.trim().isNotEmpty &&
        pendingPaymentStatus == 'pending';
  }

  factory Debt.fromJson(Map<String, dynamic> json) {
    final rawPendingPaymentId = json['pending_payment_id']?.toString();

    final fromVirtual = json['from_user_is_virtual'] ?? false;
    final toVirtual = json['to_user_is_virtual'] ?? false;

    return Debt(
      id: json['id'].toString(),

      expenseId: json['expense_id']?.toString() ?? '',

      expenseTitle: json['expense_title']?.toString() ?? '',

      fromUserName: json['from_user_name']?.toString() ?? '',

      fromUserEmail: json['from_user_email']?.toString() ?? '',

      fromUserAvatar: json['from_user_avatar']?.toString() ?? '',

      fromUserIsVirtual: fromVirtual,

      toUserName: json['to_user_name']?.toString() ?? '',

      toUserEmail: json['to_user_email']?.toString() ?? '',

      toUserAvatar: json['to_user_avatar']?.toString() ?? '',

      toUserIsVirtual: toVirtual,

      hasVirtualMember: json['has_virtual_member'] ?? fromVirtual || toVirtual,

      bankName: json['bank_name']?.toString() ?? '',

      bankAccountNumber: json['bank_account_number']?.toString() ?? '',

      bankAccountHolder: json['bank_account_holder']?.toString() ?? '',

      amount: double.tryParse(json['amount'].toString()) ?? 0,

      isPaid: json['is_paid'] ?? false,

      pendingPaymentId:
          rawPendingPaymentId == null ||
              rawPendingPaymentId.trim().isEmpty ||
              rawPendingPaymentId == 'null'
          ? null
          : rawPendingPaymentId,

      pendingPaymentStatus: json['pending_payment_status']?.toString() ?? '',

      canMarkPaid: json['can_mark_paid'] ?? false,

      canConfirmPayment: json['can_confirm_payment'] ?? false,
    );
  }
}
