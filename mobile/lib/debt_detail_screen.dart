import 'package:flutter/material.dart';

import 'app_theme.dart';
import 'services/api_service.dart';
import 'widgets/app_empty_state.dart';
import 'widgets/app_error_state.dart';
import 'widgets/app_loading_state.dart';

class DebtDetailScreen extends StatefulWidget {
  final String householdId;
  final int otherUserId;
  final int? virtualUserId;
  final bool isVirtualMode;
  final Map<String, dynamic> initialDetail;

  const DebtDetailScreen({
    super.key,
    required this.householdId,
    required this.otherUserId,
    required this.isVirtualMode,
    required this.initialDetail,
    this.virtualUserId,
  });

  @override
  State<DebtDetailScreen> createState() => _DebtDetailScreenState();
}

class _DebtDetailScreenState extends State<DebtDetailScreen> {
  late Map<String, dynamic> detail;

  bool isLoading = false;
  bool isSubmitting = false;
  bool showQr = false;
  String errorMessage = '';

  final TextEditingController amountController = TextEditingController();

  @override
  void initState() {
    super.initState();
    detail = Map<String, dynamic>.from(widget.initialDetail);

    final amount = readInt(detail['net_amount']);
    if (amount > 0) {
      amountController.text = amount.toString();
    }
  }

  @override
  void dispose() {
    amountController.dispose();
    super.dispose();
  }

  int readInt(dynamic value) {
    if (value == null) return 0;
    if (value is int) return value;
    if (value is num) return value.toInt();

    final clean = value
        .toString()
        .replaceAll('.', '')
        .replaceAll(',', '')
        .trim();

    return int.tryParse(clean) ?? 0;
  }

  String readText(dynamic value) {
    return value?.toString() ?? '';
  }

  List<Map<String, dynamic>> readMapList(dynamic value) {
    if (value is! List) return [];

    return value
        .whereType<Map>()
        .map((item) => Map<String, dynamic>.from(item))
        .toList();
  }

  String formatMoney(int amount) {
    return amount.toString().replaceAllMapped(
      RegExp(r'\B(?=(\d{3})+(?!\d))'),
      (_) => '.',
    );
  }

  String formatDate(dynamic value) {
    final raw = readText(value);
    if (raw.isEmpty) return '';

    final parsed = DateTime.tryParse(raw);
    if (parsed == null) return raw;

    final local = parsed.toLocal();
    final day = local.day.toString().padLeft(2, '0');
    final month = local.month.toString().padLeft(2, '0');

    return '$day/$month/${local.year}';
  }

  Color getAmountColor(bool isIOwe) {
    return isIOwe ? Colors.redAccent : AppColors.primary;
  }

  bool hasReceiverBankInfo() {
    final bankInfo = Map<String, dynamic>.from(
      detail['receiver_bank_info'] ?? {},
    );

    final bankName = readText(bankInfo['bank_name']);
    final accountNumber = readText(bankInfo['bank_account_number']);
    final accountHolder = readText(bankInfo['bank_account_holder']);

    return bankName.isNotEmpty &&
        accountNumber.isNotEmpty &&
        accountHolder.isNotEmpty;
  }

  String buildQrUrl() {
    final bankInfo = Map<String, dynamic>.from(
      detail['receiver_bank_info'] ?? {},
    );

    final bankName = readText(bankInfo['bank_name']);
    final accountNumber = readText(bankInfo['bank_account_number']);
    final accountHolder = readText(bankInfo['bank_account_holder']);
    final amount = readInt(amountController.text);

    if (bankName.isEmpty ||
        accountNumber.isEmpty ||
        accountHolder.isEmpty ||
        amount <= 0) {
      return '';
    }

    return 'https://img.vietqr.io/image/$bankName-$accountNumber-compact2.png?amount=$amount&accountName=$accountHolder';
  }

  Future<void> reloadDetail() async {
    setState(() {
      isLoading = true;
      errorMessage = '';
    });

    try {
      final response = widget.isVirtualMode
          ? await ApiService.getVirtualMemberDebtDetail(
              householdId: widget.householdId,
              virtualUserId: widget.virtualUserId!,
              otherUserId: widget.otherUserId,
            )
          : await ApiService.getHouseholdMyDebtDetail(
              householdId: widget.householdId,
              otherUserId: widget.otherUserId,
            );

      if (!mounted) return;

      setState(() {
        detail = Map<String, dynamic>.from(response);
      });
    } catch (e) {
      if (!mounted) return;

      setState(() {
        errorMessage = e.toString();
      });
    } finally {
      if (mounted) {
        setState(() {
          isLoading = false;
        });
      }
    }
  }

  Future<bool> submitPairPayment() async {
    final currentDebt = readInt(detail['net_amount']);
    final amount = readInt(amountController.text);

    if (amount <= 0 || amount > currentDebt) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            'Số tiền phải lớn hơn 0 và không vượt quá ${formatMoney(currentDebt)}đ',
          ),
        ),
      );
      return false;
    }

    setState(() {
      isSubmitting = true;
    });

    try {
      await ApiService.createPairPayment(
        householdId: widget.householdId,
        receiverId: widget.otherUserId,
        amount: amount,
        paymentMode: amount == currentDebt ? 'full' : 'custom_amount',
        note: amount == currentDebt
            ? 'Thanh toán toàn bộ công nợ'
            : 'Thanh toán trước công nợ',
      );

      if (!mounted) return false;

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Đã gửi yêu cầu xác nhận thanh toán.')),
      );

      await reloadDetail();
      return true;
    } catch (e) {
      if (!mounted) return false;

      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(e.toString())));

      return false;
    } finally {
      if (mounted) {
        setState(() {
          isSubmitting = false;
        });
      }
    }
  }

  Future<void> confirmPendingPayment() async {
    final payment = Map<String, dynamic>.from(detail['pending_payment'] ?? {});

    final paymentId = readText(payment['id']);
    if (paymentId.isEmpty) return;

    setState(() {
      isSubmitting = true;
    });

    try {
      await ApiService.confirmPayment(paymentId, note: 'Đã nhận tiền');

      if (!mounted) return;

      ScaffoldMessenger.of(
        context,
      ).showSnackBar(const SnackBar(content: Text('Đã xác nhận nhận tiền.')));

      await reloadDetail();
    } catch (e) {
      if (!mounted) return;

      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(e.toString())));
    } finally {
      if (mounted) {
        setState(() {
          isSubmitting = false;
        });
      }
    }
  }

  Future<bool> submitVirtualReceipt() async {
    final currentDebt = readInt(detail['net_amount']);
    final amount = readInt(amountController.text);

    if (amount <= 0 || amount > currentDebt) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            'Số tiền phải lớn hơn 0 và không vượt quá ${formatMoney(currentDebt)}đ',
          ),
        ),
      );
      return false;
    }

    final virtualUserId = widget.isVirtualMode
        ? widget.virtualUserId
        : widget.otherUserId;

    if (virtualUserId == null || virtualUserId <= 0) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Không xác định được thành viên ảo.')),
      );
      return false;
    }

    setState(() {
      isSubmitting = true;
    });

    try {
      await ApiService.recordVirtualReceipt(
        householdId: widget.householdId,
        virtualUserId: virtualUserId,
        amount: amount,
        note: amount == currentDebt
            ? 'Đã nhận đủ tiền ngoài đời'
            : 'Đã nhận trước một phần ngoài đời',
      );

      if (!mounted) return false;

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            amount == currentDebt
                ? 'Đã ghi nhận nhận đủ tiền.'
                : 'Đã ghi nhận nhận trước ${formatMoney(amount)}đ.',
          ),
        ),
      );

      await reloadDetail();
      return true;
    } catch (e) {
      if (!mounted) return false;

      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(e.toString())));

      return false;
    } finally {
      if (mounted) {
        setState(() {
          isSubmitting = false;
        });
      }
    }
  }

  Future<void> settleVirtualDebt() async {
    if (widget.virtualUserId == null) return;

    setState(() {
      isSubmitting = true;
    });

    try {
      await ApiService.settleVirtualMemberDebtPair(
        householdId: widget.householdId,
        virtualUserId: widget.virtualUserId!,
        otherUserId: widget.otherUserId,
      );

      if (!mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Đã đánh dấu xử lý ngoài đời.')),
      );

      await reloadDetail();
    } catch (e) {
      if (!mounted) return;

      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(e.toString())));
    } finally {
      if (mounted) {
        setState(() {
          isSubmitting = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final name = widget.isVirtualMode
        ? readText(detail['virtual_name'])
        : readText(detail['other_name']);

    final avatarUrl = widget.isVirtualMode
        ? ''
        : ApiService.resolveMediaUrl(readText(detail['other_avatar']));

    final netAmount = readInt(detail['net_amount']);
    final netDirection = readText(detail['net_direction']);
    final pendingPayment = detail['pending_payment'];
    final canPayNow = detail['can_pay_now'] == true;
    final isOtherVirtual = detail['is_virtual'] == true || widget.isVirtualMode;
    final unpaidItems = readMapList(detail['unpaid_items']);
    final paidItems = readMapList(detail['paid_items']);

    final isIOwe = netDirection == 'i_owe' || netDirection == 'virtual_owes';

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        backgroundColor: AppColors.background,
        elevation: 0,
        title: Text(
          widget.isVirtualMode ? 'Công nợ thành viên ảo' : 'Chi tiết công nợ',
          style: const TextStyle(
            color: AppColors.textDark,
            fontWeight: FontWeight.w900,
          ),
        ),
        iconTheme: const IconThemeData(color: AppColors.textDark),
      ),
      body: isLoading
          ? const AppLoadingState(message: 'Đang tải chi tiết công nợ...')
          : errorMessage.isNotEmpty
          ? AppErrorState(message: errorMessage, onRetry: reloadDetail)
          : netAmount <= 0
          ? AppEmptyState(
              icon: Icons.check_circle_rounded,
              title: 'Đã thanh toán xong',
              message:
                  'Hiện không còn công nợ cần xử lý giữa hai thành viên này.',
              buttonText: 'Tải lại',
              onPressed: reloadDetail,
            )
          : RefreshIndicator(
              onRefresh: reloadDetail,
              color: AppColors.primary,
              child: ListView(
                padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
                children: [
                  buildHeroCard(
                    name: name,
                    avatarUrl: avatarUrl,
                    netAmount: netAmount,
                    isIOwe: isIOwe,
                    pendingPayment: pendingPayment,
                    canPayNow: canPayNow,
                    isOtherVirtual: isOtherVirtual,
                  ),
                  const SizedBox(height: 14),
                  buildDebtSectionsCard(
                    unpaidItems: unpaidItems,
                    paidItems: paidItems,
                  ),
                ],
              ),
            ),
    );
  }

  Widget buildDebtPersonAvatar({
    required String name,
    required String avatarUrl,
    required bool isVirtual,
    required bool isIOwe,
  }) {
    final letter = name.trim().isNotEmpty ? name.trim()[0].toUpperCase() : '?';

    Widget fallbackAvatar() {
      return Container(
        width: 58,
        height: 58,
        decoration: BoxDecoration(
          color: isVirtual
              ? const Color(0xFFE0F2FE)
              : isIOwe
              ? Colors.redAccent.withValues(alpha: 0.10)
              : AppColors.primary.withValues(alpha: 0.10),
          borderRadius: BorderRadius.circular(22),
        ),
        child: Center(
          child: isVirtual
              ? const Icon(
                  Icons.person_outline_rounded,
                  color: Color(0xFF0284C7),
                  size: 30,
                )
              : Text(
                  letter,
                  style: TextStyle(
                    color: isIOwe ? Colors.redAccent : AppColors.primary,
                    fontSize: 22,
                    fontWeight: FontWeight.w900,
                  ),
                ),
        ),
      );
    }

    if (isVirtual || avatarUrl.trim().isEmpty) {
      return fallbackAvatar();
    }

    return ClipRRect(
      borderRadius: BorderRadius.circular(22),
      child: SizedBox(
        width: 58,
        height: 58,
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

  Widget buildHeroCard({
    required String name,
    required String avatarUrl,
    required int netAmount,
    required bool isIOwe,
    required dynamic pendingPayment,
    required bool canPayNow,
    required bool isOtherVirtual,
  }) {
    final payment = pendingPayment == null
        ? null
        : Map<String, dynamic>.from(pendingPayment);

    final hasPendingPayment = payment != null;
    final titleName = name.isEmpty ? 'thành viên này' : name;

    final headline = widget.isVirtualMode
        ? 'Công nợ với $titleName'
        : isIOwe
        ? 'Bạn còn nợ $titleName'
        : '$titleName còn nợ bạn';

    final amountLabel = widget.isVirtualMode
        ? 'Số tiền cần xử lý'
        : isIOwe
        ? 'Số tiền còn nợ'
        : 'Số tiền được nhận';

    String buttonText;
    VoidCallback? onPressed;
    Color buttonColor;

    if (widget.isVirtualMode) {
      buttonText = isSubmitting ? 'Đang xử lý...' : 'Đánh dấu đã xử lý';
      onPressed = isSubmitting ? null : settleVirtualDebt;
      buttonColor = AppColors.primary;
    } else if (isIOwe) {
      buttonText = hasPendingPayment ? 'Đang chờ xác nhận' : 'Thanh toán ngay';
      onPressed = (!hasPendingPayment && canPayNow && !isSubmitting)
          ? () {
              amountController.text = netAmount.toString();
              showQr = false;
              showPaymentSheet(netAmount);
            }
          : null;
      buttonColor = AppColors.primary;
    } else {
      if (isOtherVirtual) {
        buttonText = isSubmitting
            ? 'Đang ghi nhận...'
            : 'Ghi nhận đã nhận tiền';
        onPressed = isSubmitting
            ? null
            : () {
                amountController.text = netAmount.toString();
                showVirtualReceiptSheet(netAmount);
              };
        buttonColor = AppColors.primary;
      } else {
        buttonText = hasPendingPayment
            ? 'Xác nhận đã nhận tiền'
            : 'Chưa có yêu cầu thanh toán';
        onPressed = (hasPendingPayment && !isSubmitting)
            ? confirmPendingPayment
            : null;
        buttonColor = hasPendingPayment
            ? AppColors.primary
            : AppColors.textLight;
      }
    }

    return Container(
      padding: const EdgeInsets.all(22),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(30),
        border: Border.all(color: AppColors.border),
        boxShadow: [
          BoxShadow(
            color: AppColors.primaryDark.withValues(alpha: 0.045),
            blurRadius: 24,
            offset: const Offset(0, 12),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              buildDebtPersonAvatar(
                name: name,
                avatarUrl: avatarUrl,
                isVirtual: isOtherVirtual,
                isIOwe: isIOwe,
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Text(
                  headline,
                  style: const TextStyle(
                    fontSize: 21,
                    height: 1.25,
                    fontWeight: FontWeight.w900,
                    color: AppColors.textDark,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 18),
          Text(
            amountLabel,
            style: const TextStyle(
              color: AppColors.textLight,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            '${formatMoney(netAmount)}đ',
            style: TextStyle(
              fontSize: 42,
              height: 1.02,
              fontWeight: FontWeight.w900,
              color: getAmountColor(isIOwe),
            ),
          ),
          const SizedBox(height: 22),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton(
              onPressed: onPressed,
              style: ElevatedButton.styleFrom(
                backgroundColor: buttonColor,
                foregroundColor: Colors.white,
                disabledBackgroundColor: AppColors.textLight.withValues(
                  alpha: 0.28,
                ),
                disabledForegroundColor: Colors.white,
                elevation: 0,
                padding: const EdgeInsets.symmetric(vertical: 16),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(18),
                ),
              ),
              child: Text(
                buttonText,
                style: const TextStyle(
                  fontSize: 15.5,
                  fontWeight: FontWeight.w900,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  void showVirtualReceiptSheet(int currentDebt) {
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (sheetContext) {
        return StatefulBuilder(
          builder: (context, setSheetState) {
            final inputAmount = readInt(amountController.text);
            final isFullPayment = inputAmount == currentDebt;

            return Padding(
              padding: EdgeInsets.only(
                left: 14,
                right: 14,
                bottom: MediaQuery.of(context).viewInsets.bottom + 14,
              ),
              child: Container(
                padding: const EdgeInsets.fromLTRB(18, 12, 18, 18),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(30),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withValues(alpha: 0.08),
                      blurRadius: 28,
                      offset: const Offset(0, -6),
                    ),
                  ],
                ),
                child: SingleChildScrollView(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Center(
                        child: Container(
                          width: 44,
                          height: 5,
                          decoration: BoxDecoration(
                            color: AppColors.border,
                            borderRadius: BorderRadius.circular(999),
                          ),
                        ),
                      ),
                      const SizedBox(height: 18),
                      const Text(
                        'Ghi nhận đã nhận tiền',
                        style: TextStyle(
                          fontSize: 20,
                          fontWeight: FontWeight.w900,
                          color: AppColors.textDark,
                        ),
                      ),
                      const SizedBox(height: 6),
                      Text(
                        'Thành viên ảo còn nợ ${formatMoney(currentDebt)}đ. Bạn có thể ghi nhận nhận đủ hoặc nhận trước một phần.',
                        style: const TextStyle(
                          color: AppColors.textLight,
                          fontWeight: FontWeight.w700,
                          height: 1.35,
                        ),
                      ),
                      const SizedBox(height: 18),
                      TextField(
                        controller: amountController,
                        keyboardType: TextInputType.number,
                        decoration: InputDecoration(
                          labelText: 'Số tiền đã nhận',
                          suffixText: 'đ',
                          filled: true,
                          fillColor: AppColors.background,
                          border: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(18),
                            borderSide: const BorderSide(
                              color: AppColors.border,
                            ),
                          ),
                          enabledBorder: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(18),
                            borderSide: const BorderSide(
                              color: AppColors.border,
                            ),
                          ),
                          focusedBorder: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(18),
                            borderSide: const BorderSide(
                              color: AppColors.primary,
                              width: 1.4,
                            ),
                          ),
                        ),
                        onChanged: (_) {
                          setSheetState(() {});
                        },
                      ),
                      const SizedBox(height: 10),
                      OutlinedButton(
                        onPressed: () {
                          amountController.text = currentDebt.toString();
                          setSheetState(() {});
                        },
                        style: OutlinedButton.styleFrom(
                          foregroundColor: AppColors.primary,
                          side: const BorderSide(color: AppColors.primary),
                          padding: const EdgeInsets.symmetric(vertical: 13),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(16),
                          ),
                        ),
                        child: const Text(
                          'Nhận đủ',
                          style: TextStyle(fontWeight: FontWeight.w800),
                        ),
                      ),
                      const SizedBox(height: 16),
                      ElevatedButton(
                        onPressed: isSubmitting
                            ? null
                            : () async {
                                final success = await submitVirtualReceipt();

                                if (success && sheetContext.mounted) {
                                  Navigator.of(sheetContext).pop();
                                }
                              },
                        style: ElevatedButton.styleFrom(
                          backgroundColor: AppColors.primary,
                          foregroundColor: Colors.white,
                          elevation: 0,
                          padding: const EdgeInsets.symmetric(vertical: 15),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(18),
                          ),
                        ),
                        child: Text(
                          isSubmitting
                              ? 'Đang ghi nhận...'
                              : isFullPayment
                              ? 'Ghi nhận đã nhận đủ'
                              : 'Ghi nhận nhận trước',
                          style: const TextStyle(fontWeight: FontWeight.w900),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            );
          },
        );
      },
    );
  }

  void showPaymentSheet(int currentDebt) {
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (sheetContext) {
        return StatefulBuilder(
          builder: (context, setSheetState) {
            final inputAmount = readInt(amountController.text);
            final isFullPayment = inputAmount == currentDebt;
            final hasBankInfo = hasReceiverBankInfo();
            final qrUrl = buildQrUrl();

            return Padding(
              padding: EdgeInsets.only(
                left: 14,
                right: 14,
                bottom: MediaQuery.of(context).viewInsets.bottom + 14,
              ),
              child: Container(
                padding: const EdgeInsets.fromLTRB(18, 12, 18, 18),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(30),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withValues(alpha: 0.08),
                      blurRadius: 28,
                      offset: const Offset(0, -6),
                    ),
                  ],
                ),
                child: SingleChildScrollView(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Center(
                        child: Container(
                          width: 44,
                          height: 5,
                          decoration: BoxDecoration(
                            color: AppColors.border,
                            borderRadius: BorderRadius.circular(999),
                          ),
                        ),
                      ),
                      const SizedBox(height: 18),
                      Row(
                        children: [
                          Container(
                            width: 44,
                            height: 44,
                            decoration: BoxDecoration(
                              color: AppColors.primary.withValues(alpha: 0.1),
                              borderRadius: BorderRadius.circular(16),
                            ),
                            child: const Icon(
                              Icons.account_balance_wallet_rounded,
                              color: AppColors.primary,
                            ),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                const Text(
                                  'Thanh toán công nợ',
                                  style: TextStyle(
                                    fontSize: 20,
                                    fontWeight: FontWeight.w900,
                                    color: AppColors.textDark,
                                  ),
                                ),
                                const SizedBox(height: 3),
                                Text(
                                  'Còn nợ ${formatMoney(currentDebt)}đ',
                                  style: const TextStyle(
                                    color: AppColors.textLight,
                                    fontWeight: FontWeight.w700,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 18),
                      TextField(
                        controller: amountController,
                        keyboardType: TextInputType.number,
                        decoration: InputDecoration(
                          labelText: 'Số tiền thanh toán',
                          suffixText: 'đ',
                          filled: true,
                          fillColor: AppColors.background,
                          border: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(18),
                            borderSide: const BorderSide(
                              color: AppColors.border,
                            ),
                          ),
                          enabledBorder: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(18),
                            borderSide: const BorderSide(
                              color: AppColors.border,
                            ),
                          ),
                          focusedBorder: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(18),
                            borderSide: const BorderSide(
                              color: AppColors.primary,
                              width: 1.4,
                            ),
                          ),
                        ),
                        onChanged: (_) {
                          setSheetState(() {
                            showQr = false;
                          });
                        },
                      ),
                      const SizedBox(height: 10),
                      OutlinedButton(
                        onPressed: () {
                          amountController.text = currentDebt.toString();
                          setSheetState(() {
                            showQr = false;
                          });
                        },
                        style: OutlinedButton.styleFrom(
                          foregroundColor: AppColors.primary,
                          side: const BorderSide(color: AppColors.primary),
                          padding: const EdgeInsets.symmetric(vertical: 13),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(16),
                          ),
                        ),
                        child: const Text(
                          'Thanh toán toàn bộ',
                          style: TextStyle(fontWeight: FontWeight.w800),
                        ),
                      ),
                      const SizedBox(height: 12),
                      OutlinedButton.icon(
                        onPressed: () {
                          if (!hasBankInfo) {
                            ScaffoldMessenger.of(context).showSnackBar(
                              const SnackBar(
                                content: Text(
                                  'Người nhận chưa cập nhật thông tin ngân hàng nên chưa thể tạo QR.',
                                ),
                              ),
                            );
                            return;
                          }

                          if (inputAmount <= 0) {
                            ScaffoldMessenger.of(context).showSnackBar(
                              const SnackBar(
                                content: Text(
                                  'Vui lòng nhập số tiền thanh toán hợp lệ.',
                                ),
                              ),
                            );
                            return;
                          }

                          setSheetState(() {
                            showQr = true;
                          });
                        },
                        icon: const Icon(Icons.qr_code_2_rounded),
                        label: const Text(
                          'Tạo QR thanh toán',
                          style: TextStyle(fontWeight: FontWeight.w800),
                        ),
                        style: OutlinedButton.styleFrom(
                          foregroundColor: AppColors.primary,
                          side: const BorderSide(color: AppColors.primary),
                          padding: const EdgeInsets.symmetric(vertical: 13),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(16),
                          ),
                        ),
                      ),
                      if (showQr && qrUrl.isNotEmpty) ...[
                        const SizedBox(height: 14),
                        buildQrCard(qrUrl, inputAmount),
                      ],
                      const SizedBox(height: 16),
                      ElevatedButton(
                        onPressed: isSubmitting
                            ? null
                            : () async {
                                final success = await submitPairPayment();

                                if (success && sheetContext.mounted) {
                                  Navigator.of(sheetContext).pop();
                                }
                              },
                        style: ElevatedButton.styleFrom(
                          backgroundColor: AppColors.primary,
                          foregroundColor: Colors.white,
                          elevation: 0,
                          padding: const EdgeInsets.symmetric(vertical: 15),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(18),
                          ),
                        ),
                        child: Text(
                          isSubmitting
                              ? 'Đang gửi...'
                              : isFullPayment
                              ? 'Báo đã thanh toán toàn bộ'
                              : 'Báo đã thanh toán trước',
                          style: const TextStyle(fontWeight: FontWeight.w900),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            );
          },
        );
      },
    );
  }

  Widget buildQrCard(String qrUrl, int amount) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppColors.background,
        borderRadius: BorderRadius.circular(22),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        children: [
          Text(
            'QR thanh toán ${formatMoney(amount)}đ',
            style: const TextStyle(
              color: AppColors.textDark,
              fontWeight: FontWeight.w900,
            ),
          ),
          const SizedBox(height: 10),
          ClipRRect(
            borderRadius: BorderRadius.circular(18),
            child: Image.network(qrUrl, height: 220, fit: BoxFit.contain),
          ),
        ],
      ),
    );
  }

  Widget buildDebtSectionsCard({
    required List<Map<String, dynamic>> unpaidItems,
    required List<Map<String, dynamic>> paidItems,
  }) {
    return Container(
      padding: const EdgeInsets.all(22),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(28),
        border: Border.all(color: AppColors.border),
        boxShadow: [
          BoxShadow(
            color: AppColors.primaryDark.withValues(alpha: 0.03),
            blurRadius: 18,
            offset: const Offset(0, 9),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          buildDebtSection(
            title: 'Chưa thanh toán',
            emptyText: 'Không còn khoản chưa thanh toán.',
            items: unpaidItems,
            isPaidSection: false,
          ),
          const SizedBox(height: 24),
          buildDebtSection(
            title: 'Đã thanh toán',
            emptyText: 'Chưa có khoản nào đã thanh toán ở chiều công nợ này.',
            items: paidItems,
            isPaidSection: true,
          ),
        ],
      ),
    );
  }

  Widget buildDebtSection({
    required String title,
    required String emptyText,
    required List<Map<String, dynamic>> items,
    required bool isPaidSection,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Text(
              title,
              style: const TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.w900,
                color: AppColors.textDark,
              ),
            ),
            const SizedBox(width: 8),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
              decoration: BoxDecoration(
                color: AppColors.background,
                borderRadius: BorderRadius.circular(999),
              ),
              child: Text(
                items.length.toString(),
                style: const TextStyle(
                  color: AppColors.textLight,
                  fontWeight: FontWeight.w900,
                  fontSize: 12,
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: 14),
        if (items.isEmpty)
          Text(
            emptyText,
            style: const TextStyle(
              color: AppColors.textLight,
              fontWeight: FontWeight.w600,
            ),
          )
        else
          ...items.asMap().entries.map((entry) {
            final index = entry.key;
            final item = entry.value;
            final isLast = index == items.length - 1;

            return buildDebtItemRow(
              item,
              isLast: isLast,
              isPaidSection: isPaidSection,
            );
          }),
      ],
    );
  }

  Widget buildDebtItemRow(
    Map<String, dynamic> item, {
    required bool isLast,
    required bool isPaidSection,
  }) {
    final title = readText(item['expense_title']);
    final payerName = readText(item['payer_name']);
    final payerAvatar = readText(item['payer_avatar']);
    final isPayerVirtual = item['payer_is_virtual'] == true;

    final originalAmount = readInt(item['original_amount']);
    final paidAmount = readInt(item['paid_amount']);
    final pendingAmount = readInt(item['pending_amount']);
    final remainingAmount = readInt(item['remaining_amount']);
    final status = readText(item['status']);
    final paidAt = readText(item['paid_at']);
    final expenseDate = readText(item['expense_date']);

    final displayDate = isPaidSection
        ? formatDate(paidAt.isNotEmpty ? paidAt : item['updated_at'])
        : formatDate(expenseDate);

    final subtitle = buildDebtItemSubtitle(
      originalAmount: originalAmount,
      paidAmount: paidAmount,
      pendingAmount: pendingAmount,
      remainingAmount: remainingAmount,
      status: status,
      date: displayDate,
      isPaidSection: isPaidSection,
    );

    final initialSource = payerName.isNotEmpty ? payerName : title;

    final initial = initialSource.isNotEmpty
        ? initialSource.characters.first.toUpperCase()
        : 'N';

    final amountText = isPaidSection
        ? '${formatMoney(originalAmount)}đ'
        : '${formatMoney(remainingAmount)}đ';

    return buildHistoryRow(
      initial: initial,
      avatarUrl: payerAvatar,
      isVirtual: isPayerVirtual,
      title: title.isEmpty ? 'Khoản chi' : title,
      subtitle: subtitle,
      amountText: amountText,
      isLast: isLast,
    );
  }

  String buildDebtItemSubtitle({
    required int originalAmount,
    required int paidAmount,
    required int pendingAmount,
    required int remainingAmount,
    required String status,
    required String date,
    required bool isPaidSection,
  }) {
    if (isPaidSection) {
      final parts = <String>[
        'Tổng nợ: ${formatMoney(originalAmount)}đ',
        'Đã thanh toán đủ',
        if (date.isNotEmpty) date,
      ];

      return parts.join(' · ');
    }

    final parts = <String>['Tổng nợ: ${formatMoney(originalAmount)}đ'];

    if (paidAmount > 0) {
      parts.add('Đã trả trước: ${formatMoney(paidAmount)}đ');
    }

    if (pendingAmount > 0) {
      parts.add('Đang chờ xác nhận: ${formatMoney(pendingAmount)}đ');
    }

    if (remainingAmount > 0 && status != 'pending') {
      parts.add('Còn lại: ${formatMoney(remainingAmount)}đ');
    }

    if (date.isNotEmpty) {
      parts.add(date);
    }

    return parts.join(' · ');
  }

  Widget buildTimelineCard(
    List<Map<String, dynamic>> timeline,
    List<Map<String, dynamic>> items,
  ) {
    final historyItems = [
      ...timeline.map((item) => {...item, '_history_type': 'payment'}),
      ...items.map((item) => {...item, '_history_type': 'debt'}),
    ];

    return Container(
      padding: const EdgeInsets.all(22),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(28),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Lịch sử công nợ',
            style: TextStyle(
              fontSize: 20,
              fontWeight: FontWeight.w900,
              color: AppColors.textDark,
            ),
          ),
          const SizedBox(height: 18),
          if (historyItems.isEmpty)
            const Text(
              'Chưa có lịch sử công nợ.',
              style: TextStyle(
                color: AppColors.textLight,
                fontWeight: FontWeight.w600,
              ),
            )
          else
            ...historyItems.asMap().entries.map((entry) {
              final index = entry.key;
              final item = entry.value;
              final isLast = index == historyItems.length - 1;

              if (item['_history_type'] == 'payment') {
                return buildPaymentHistoryRow(item, isLast: isLast);
              }

              return buildDebtHistoryRow(item, isLast: isLast);
            }),
        ],
      ),
    );
  }

  Widget buildPaymentHistoryRow(
    Map<String, dynamic> payment, {
    required bool isLast,
  }) {
    final amount = readInt(payment['amount']);
    final status = readText(payment['status']);
    final date = formatDate(payment['created_at']);

    final statusText = status == 'confirmed'
        ? 'Đã xác nhận'
        : status == 'pending'
        ? 'Chờ xác nhận'
        : 'Đã từ chối';

    return buildHistoryRow(
      initial: 'T',
      avatarUrl: '',
      isVirtual: false,
      title: 'Thanh toán ${formatMoney(amount)}đ',
      subtitle: date.isEmpty ? statusText : '$statusText · $date',
      amountText: status == 'confirmed' ? '+${formatMoney(amount)}đ' : '',
      isLast: isLast,
    );
  }

  Widget buildHistoryAvatar({
    required String initial,
    required String avatarUrl,
    required bool isVirtual,
  }) {
    final resolvedAvatar = avatarUrl.trim().isNotEmpty
        ? ApiService.resolveMediaUrl(avatarUrl.trim())
        : '';

    Widget fallbackAvatar() {
      return CircleAvatar(
        radius: 28,
        backgroundColor: isVirtual
            ? const Color(0xFFE0F2FE)
            : AppColors.primary,
        child: isVirtual
            ? const Icon(
                Icons.person_outline_rounded,
                color: Color(0xFF0284C7),
                size: 28,
              )
            : Text(
                initial,
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 22,
                  fontWeight: FontWeight.w900,
                ),
              ),
      );
    }

    if (isVirtual || resolvedAvatar.isEmpty) {
      return fallbackAvatar();
    }

    return ClipOval(
      child: SizedBox(
        width: 56,
        height: 56,
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

  Widget buildDebtHistoryRow(
    Map<String, dynamic> item, {
    required bool isLast,
  }) {
    final title = readText(item['expense_title']);
    final amount = readInt(item['amount']);
    final paidAmount = readInt(item['paid_amount']);
    final date = formatDate(item['expense_date']);

    final payerName = readText(item['payer_name']);
    final payerAvatar = readText(item['payer_avatar']);
    final isPayerVirtual = item['payer_is_virtual'] == true;

    final subtitleParts = [
      if (payerName.isNotEmpty) 'Người chi: $payerName',
      if (date.isNotEmpty) date,
      if (paidAmount > 0) 'Đã trả ${formatMoney(paidAmount)}đ',
      'Còn ${formatMoney(amount)}đ',
    ];

    final initialSource = payerName.isNotEmpty ? payerName : title;

    final initial = initialSource.isNotEmpty
        ? initialSource.characters.first.toUpperCase()
        : 'N';

    return buildHistoryRow(
      initial: initial,
      avatarUrl: payerAvatar,
      isVirtual: isPayerVirtual,
      title: title.isEmpty ? 'Khoản chi' : title,
      subtitle: subtitleParts.join(' · '),
      amountText: '${formatMoney(amount)}đ',
      isLast: isLast,
    );
  }

  Widget buildHistoryRow({
    required String initial,
    required String avatarUrl,
    required bool isVirtual,
    required String title,
    required String subtitle,
    required String amountText,
    required bool isLast,
  }) {
    return Column(
      children: [
        Row(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            buildHistoryAvatar(
              initial: initial,
              avatarUrl: avatarUrl,
              isVirtual: isVirtual,
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      color: AppColors.textDark,
                      fontSize: 16,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    subtitle,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      color: AppColors.textLight,
                      fontSize: 13.5,
                      fontWeight: FontWeight.w700,
                      height: 1.3,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 12),
            if (amountText.isNotEmpty)
              Text(
                amountText,
                style: const TextStyle(
                  color: AppColors.primary,
                  fontSize: 16,
                  fontWeight: FontWeight.w900,
                ),
              ),
          ],
        ),
        if (!isLast)
          const Padding(
            padding: EdgeInsets.only(left: 72, top: 16, bottom: 16),
            child: Divider(height: 1, color: AppColors.border),
          ),
      ],
    );
  }
}
