import 'package:flutter/material.dart';

import 'app_theme.dart';
import 'services/api_service.dart';

class CreateHouseholdScreen extends StatefulWidget {
  final VoidCallback? onCreated;
  final bool popOnSuccess;

  const CreateHouseholdScreen({
    super.key,
    this.onCreated,
    this.popOnSuccess = true,
  });

  @override
  State<CreateHouseholdScreen> createState() => _CreateHouseholdScreenState();
}

class _CreateHouseholdScreenState extends State<CreateHouseholdScreen> {
  final nameController = TextEditingController();
  final descriptionController = TextEditingController();

  bool isLoading = false;

  @override
  void dispose() {
    nameController.dispose();
    descriptionController.dispose();
    super.dispose();
  }

  Future<void> createHousehold() async {
    final name = nameController.text.trim();
    final description = descriptionController.text.trim();

    if (isLoading) return;

    if (name.isEmpty) {
      showMessage('Nhập tên nhóm');
      return;
    }

    if (name.length < 3) {
      showMessage('Tên nhóm tối thiểu 3 ký tự');
      return;
    }

    try {
      setState(() => isLoading = true);

      await ApiService.createHousehold(name: name, description: description);

      if (!mounted) return;

      showMessage('Tạo nhóm thành công');

      nameController.clear();
      descriptionController.clear();

      if (widget.popOnSuccess) {
        Navigator.pop(context, true);
      } else {
        widget.onCreated?.call();
      }
    } catch (e) {
      debugPrint(e.toString());
      showMessage('Không thể tạo nhóm');
    } finally {
      if (mounted) {
        setState(() => isLoading = false);
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
              Icons.groups_rounded,
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
                  'Tạo nhóm mới',
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
                  'Đặt tên dễ nhớ để mọi người cùng theo dõi chi tiêu.',
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

  Widget buildInput({
    required TextEditingController controller,
    required String hint,
    required IconData icon,
    int maxLines = 1,
  }) {
    final isMultiline = maxLines > 1;

    return TextField(
      controller: controller,
      maxLines: maxLines,
      minLines: maxLines,
      style: const TextStyle(
        fontSize: 15,
        fontWeight: FontWeight.w600,
        color: AppColors.textDark,
      ),
      decoration: InputDecoration(
        hintText: hint,
        fillColor: AppColors.surfaceTint,
        prefixIcon: Padding(
          padding: EdgeInsets.only(
            left: 16,
            right: 12,
            top: isMultiline ? 18 : 0,
          ),
          child: Icon(icon, color: AppColors.textLight, size: 22),
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

  Widget buildSaveButton() {
    return SizedBox(
      width: double.infinity,
      height: 56,
      child: ElevatedButton(
        onPressed: isLoading ? null : createHousehold,
        child: isLoading
            ? const SizedBox(
                width: 22,
                height: 22,
                child: CircularProgressIndicator(
                  strokeWidth: 2.5,
                  color: Colors.white,
                ),
              )
            : const Text('Tạo nhóm'),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(titleSpacing: 20, title: const Text('Nhóm mới')),
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
                    'Thông tin nhóm',
                    style: TextStyle(
                      color: AppColors.textDark,
                      fontSize: 18,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                  const SizedBox(height: 14),
                  buildInput(
                    controller: nameController,
                    hint: 'Tên nhóm',
                    icon: Icons.edit_rounded,
                  ),
                  const SizedBox(height: 14),
                  buildInput(
                    controller: descriptionController,
                    hint: 'Mô tả nhóm',
                    icon: Icons.notes_rounded,
                    maxLines: 3,
                  ),
                  const SizedBox(height: 24),
                  buildSaveButton(),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
