import 'package:flutter/material.dart';

import 'app_theme.dart';
import 'household_detail_screen.dart';
import 'models/household.dart';
import 'services/api_service.dart';

class JoinHouseholdScreen extends StatefulWidget {
  const JoinHouseholdScreen({super.key});

  @override
  State<JoinHouseholdScreen> createState() => _JoinHouseholdScreenState();
}

class _JoinHouseholdScreenState extends State<JoinHouseholdScreen> {
  final inviteCodeController = TextEditingController();

  bool isLoading = false;

  @override
  void dispose() {
    inviteCodeController.dispose();
    super.dispose();
  }

  Future<void> joinHousehold() async {
    if (isLoading) return;

    final inviteCode = inviteCodeController.text.trim().toUpperCase();

    if (inviteCode.isEmpty) {
      showMessage('Nhập mã mời');
      return;
    }

    try {
      setState(() {
        isLoading = true;
      });

      final response = await ApiService.joinHousehold(inviteCode: inviteCode);

      final household = Household.fromJson(
        Map<String, dynamic>.from(response['household']),
      );

      if (!mounted) return;

      showMessage('Tham gia nhóm thành công');

      Navigator.pushReplacement(
        context,
        MaterialPageRoute(
          builder: (_) => HouseholdDetailScreen(household: household),
        ),
      );
    } catch (e) {
      showMessage(e.toString());
    } finally {
      if (mounted) {
        setState(() {
          isLoading = false;
        });
      }
    }
  }

  void showMessage(String message) {
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(SnackBar(content: Text(message)));
  }

  Widget buildHeader() {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.fromLTRB(20, 20, 20, 18),
      decoration: BoxDecoration(
        color: AppColors.backgroundWarm,
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: AppColors.primary.withValues(alpha: 0.12)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 52,
            height: 52,
            decoration: BoxDecoration(
              color: AppColors.primary,
              borderRadius: BorderRadius.circular(18),
            ),
            child: const Icon(
              Icons.group_add_rounded,
              color: Colors.white,
              size: 26,
            ),
          ),
          const SizedBox(width: 14),
          const Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Tham gia nhóm',
                  style: TextStyle(
                    color: AppColors.textDark,
                    fontSize: 24,
                    fontWeight: FontWeight.w900,
                    letterSpacing: -0.7,
                    height: 1.05,
                  ),
                ),
                SizedBox(height: 8),
                Text(
                  'Nhập mã mời được chia sẻ để vào ví nhóm.',
                  style: TextStyle(
                    color: AppColors.textLight,
                    fontSize: 14,
                    fontWeight: FontWeight.w600,
                    height: 1.4,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget buildJoinButton() {
    return SizedBox(
      width: double.infinity,
      height: 56,
      child: ElevatedButton(
        onPressed: isLoading ? null : joinHousehold,
        child: isLoading
            ? const SizedBox(
                width: 22,
                height: 22,
                child: CircularProgressIndicator(
                  strokeWidth: 2.4,
                  color: Colors.white,
                ),
              )
            : const Text('Tham gia nhóm'),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(titleSpacing: 20, title: const Text('Tham gia nhóm')),
      body: SafeArea(
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 620),
            child: SingleChildScrollView(
              padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  buildHeader(),
                  const SizedBox(height: 24),
                  const Text(
                    'Mã mời nhóm',
                    style: TextStyle(
                      color: AppColors.textDark,
                      fontSize: 18,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                  const SizedBox(height: 14),
                  TextField(
                    controller: inviteCodeController,
                    textCapitalization: TextCapitalization.characters,
                    enabled: !isLoading,
                    textInputAction: TextInputAction.done,
                    onSubmitted: (_) => joinHousehold(),
                    style: const TextStyle(
                      color: AppColors.textDark,
                      fontSize: 16,
                      fontWeight: FontWeight.w800,
                      letterSpacing: 1,
                    ),
                    decoration: const InputDecoration(
                      labelText: 'Mã mời',
                      hintText: 'Ví dụ: A1B2C3D4',
                      prefixIcon: Icon(Icons.vpn_key_rounded),
                    ),
                  ),
                  const SizedBox(height: 10),
                  const Text(
                    'Mã mời thường do chủ nhóm gửi trong tin nhắn hoặc nhóm chat.',
                    style: TextStyle(
                      color: AppColors.textLight,
                      fontSize: 13,
                      fontWeight: FontWeight.w600,
                      height: 1.4,
                    ),
                  ),
                  const SizedBox(height: 24),
                  buildJoinButton(),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
