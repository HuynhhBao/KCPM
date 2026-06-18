class ExpenseParticipant {
  final String id;
  final int userId;
  final String userName;
  final String userEmail;
  final String userAvatar;
  final double shareAmount;

  ExpenseParticipant({
    required this.id,
    required this.userId,
    required this.userName,
    required this.userEmail,
    required this.userAvatar,
    required this.shareAmount,
  });

  factory ExpenseParticipant.fromJson(Map<String, dynamic> json) {
    return ExpenseParticipant(
      id: json['id']?.toString() ?? '',
      userId:
          int.tryParse(
            json['user_id']?.toString() ?? json['user']?.toString() ?? '',
          ) ??
          0,
      userName:
          json['user_name']?.toString() ??
          json['user_full_name']?.toString() ??
          '',
      userEmail:
          json['user_email']?.toString() ?? json['email']?.toString() ?? '',
      userAvatar: json['user_avatar']?.toString() ?? '',
      shareAmount:
          double.tryParse(json['share_amount']?.toString() ?? '0') ?? 0,
    );
  }

  String get displayName {
    if (userName.trim().isNotEmpty) {
      return userName;
    }

    return userEmail;
  }
}

class Expense {
  final String id;

  final String household;

  final String title;

  final double amount;

  final int payerId;
  final String payerName;
  final String payerEmail;
  final String payerAvatar;

  final String splitType;

  final List<ExpenseParticipant> participants;

  final String expenseDate;

  final String note;

  final bool canManage;

  final String createdAt;
  final String updatedAt;

  Expense({
    required this.id,
    required this.household,
    required this.title,
    required this.amount,
    required this.payerId,
    required this.payerName,
    required this.payerEmail,
    required this.payerAvatar,
    required this.splitType,
    required this.participants,
    required this.expenseDate,
    required this.note,
    required this.canManage,
    required this.createdAt,
    required this.updatedAt,
  });

  factory Expense.fromJson(Map<String, dynamic> json) {
    String readText(List<dynamic> values) {
      for (final value in values) {
        final text = value?.toString().trim() ?? '';

        if (text.isNotEmpty && text != 'null') {
          return text;
        }
      }

      return '';
    }

    int readIntValue(dynamic value) {
      if (value == null) return 0;

      if (value is int) return value;

      return int.tryParse(value.toString()) ?? 0;
    }

    bool readBoolValue(dynamic value) {
      if (value == null) return false;

      if (value is bool) return value;

      final text = value.toString().trim().toLowerCase();

      return text == 'true' || text == '1';
    }

    Map<String, dynamic>? payerMap;

    final rawPayer = json['payer'];

    if (rawPayer is Map) {
      payerMap = Map<String, dynamic>.from(rawPayer);
    }

    return Expense(
      id: json['id']?.toString() ?? '',

      household: json['household']?.toString() ?? '',

      title: json['title']?.toString() ?? '',

      amount: double.tryParse(json['amount']?.toString() ?? '0') ?? 0,

      payerId: readIntValue(
        json['payer_id'] ??
            json['payer_user_id'] ??
            payerMap?['id'] ??
            json['payer'],
      ),

      payerName: readText([
        json['payer_name'],
        json['payer_full_name'],
        json['payer_user_name'],
        payerMap?['full_name'],
        payerMap?['name'],
        payerMap?['username'],
      ]),

      payerEmail: readText([
        json['payer_email'],
        json['payer_user_email'],
        payerMap?['email'],
      ]),

      payerAvatar: readText([
        json['payer_avatar'],
        json['payer_avatar_url'],
        json['payer_user_avatar'],
        json['payer_user_avatar_url'],
        payerMap?['avatar_url'],
        payerMap?['user_avatar'],
        payerMap?['avatar'],
      ]),

      splitType: json['split_type']?.toString() ?? 'equal',

      participants: (json['participants'] as List? ?? [])
          .map(
            (item) =>
                ExpenseParticipant.fromJson(Map<String, dynamic>.from(item)),
          )
          .toList(),

      expenseDate: json['expense_date']?.toString() ?? '',

      note: json['note']?.toString() ?? '',

      canManage: readBoolValue(json['can_manage']),

      createdAt: json['created_at']?.toString() ?? '',

      updatedAt: json['updated_at']?.toString() ?? '',
    );
  }

  String get displayPayer {
    if (payerName.trim().isNotEmpty) {
      return payerName;
    }

    return payerEmail;
  }

  bool get isEqualSplit {
    return splitType == 'equal';
  }
}
