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
    ScaffoldMessenger.of(
      context,
    ).showSnackBar(SnackBar(content: Text(message)));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(title: const Text('Tham gia nhóm')),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            children: [
              Container(
                padding: const EdgeInsets.all(20),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(24),
                  border: Border.all(color: AppColors.border),
                  boxShadow: [
                    BoxShadow(
                      color: AppColors.primaryDark.withValues(alpha: 0.04),
                      blurRadius: 18,
                      offset: const Offset(0, 9),
                    ),
                  ],
                ),
                child: Column(
                  children: [
                    const Icon(
                      Icons.group_add_rounded,
                      size: 70,
                      color: AppColors.primary,
                    ),

                    const SizedBox(height: 20),

                    TextField(
                      controller: inviteCodeController,
                      textCapitalization: TextCapitalization.characters,
                      enabled: !isLoading,
                      decoration: const InputDecoration(
                        labelText: 'Mã mời nhóm',
                        hintText: 'Ví dụ: A1B2C3D4',
                      ),
                    ),

                    const SizedBox(height: 24),

                    SizedBox(
                      width: double.infinity,
                      height: 54,
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
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
