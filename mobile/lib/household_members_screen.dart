import 'package:flutter/material.dart';

import 'app_theme.dart';
import 'services/api_service.dart';
import 'models/household.dart';

class HouseholdMembersScreen extends StatefulWidget {
  final dynamic household;
  final String currentUserEmail;
  final ValueChanged<dynamic> onHouseholdUpdated;

  const HouseholdMembersScreen({
    super.key,
    required this.household,
    required this.currentUserEmail,
    required this.onHouseholdUpdated,
  });

  @override
  State<HouseholdMembersScreen> createState() => _HouseholdMembersScreenState();
}

class _HouseholdMembersScreenState extends State<HouseholdMembersScreen> {
  late dynamic household;

  bool isAddingMember = false;
  bool isAddingVirtualMember = false;
  bool isKickingMember = false;
  String? kickingMemberId;

  @override
  void initState() {
    super.initState();
    household = widget.household;
  }

  String getMemberId(dynamic member) {
    try {
      return member.id.toString();
    } catch (_) {
      return '';
    }
  }

  int getMemberUserId(dynamic member) {
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

  String getMemberName(dynamic member) {
    try {
      return member.displayName.toString();
    } catch (_) {
      return 'Thành viên';
    }
  }

  String getMemberEmail(dynamic member) {
    try {
      return member.userEmail.toString().toLowerCase();
    } catch (_) {
      try {
        return member.email.toString().toLowerCase();
      } catch (_) {
        return '';
      }
    }
  }

  String getMemberRole(dynamic member) {
    try {
      return member.role.toString().toLowerCase();
    } catch (_) {
      return 'member';
    }
  }

  String getMemberAvatar(dynamic member) {
    final rawAvatar = (() {
      try {
        return member.userAvatar?.toString().trim() ?? '';
      } catch (_) {
        return '';
      }
    })();

    if (rawAvatar.isNotEmpty) {
      return ApiService.resolveMediaUrl(rawAvatar);
    }

    final userId = getMemberUserId(member);

    if (userId <= 0 || getMemberIsVirtual(member)) {
      return '';
    }

    return ApiService.userAvatarUrl(userId);
  }

  bool getMemberIsVirtual(dynamic member) {
    try {
      return member.isVirtual == true;
    } catch (_) {
      return getMemberEmail(member).endsWith('@virtual.chungvi.local');
    }
  }

  bool get isCurrentUserOwner {
    for (final member in household.members) {
      if (getMemberEmail(member) == widget.currentUserEmail.toLowerCase() &&
          getMemberRole(member) == 'owner') {
        return true;
      }
    }

    return false;
  }

  bool canKickMember(dynamic member) {
    if (!isCurrentUserOwner) return false;

    if (!getMemberIsVirtual(member) &&
        getMemberEmail(member) == widget.currentUserEmail.toLowerCase()) {
      return false;
    }

    if (getMemberRole(member) == 'owner') {
      return false;
    }

    return true;
  }

  Widget buildAvatar(dynamic member) {
    final avatar = getMemberAvatar(member);
    final name = getMemberName(member);
    final isVirtual = getMemberIsVirtual(member);

    Widget fallbackAvatar() {
      return CircleAvatar(
        radius: 24,
        backgroundColor: isVirtual
            ? const Color(0xFFE0F2FE)
            : const Color(0xFF087B63),
        child: isVirtual
            ? const Icon(
                Icons.person_outline_rounded,
                color: Color(0xFF0284C7),
                size: 25,
              )
            : Text(
                name.isNotEmpty ? name[0].toUpperCase() : '?',
                style: const TextStyle(
                  color: Colors.white,
                  fontWeight: FontWeight.w900,
                  fontSize: 18,
                ),
              ),
      );
    }

    if (isVirtual || avatar.isEmpty) {
      return fallbackAvatar();
    }

    return ClipOval(
      child: SizedBox(
        width: 48,
        height: 48,
        child: Image.network(
          avatar,
          key: ValueKey(avatar),
          fit: BoxFit.cover,
          errorBuilder: (_, _, _) {
            return fallbackAvatar();
          },
        ),
      ),
    );
  }

  Future<void> showAddMemberDialog() async {
    final emailController = TextEditingController();

    final email = await showDialog<String>(
      context: context,
      builder: (context) {
        return AlertDialog(
          title: const Text('Thêm thành viên dùng app'),
          content: TextField(
            controller: emailController,
            keyboardType: TextInputType.emailAddress,
            decoration: const InputDecoration(
              labelText: 'Email thành viên',
              hintText: 'example@gmail.com',
            ),
          ),
          actions: [
            TextButton(
              onPressed: () {
                Navigator.pop(context);
              },
              child: const Text('Hủy'),
            ),
            ElevatedButton(
              onPressed: () {
                final value = emailController.text.trim().toLowerCase();

                if (value.isEmpty || !value.contains('@')) {
                  return;
                }

                Navigator.pop(context, value);
              },
              child: const Text('Thêm'),
            ),
          ],
        );
      },
    );

    if (email == null || email.isEmpty) return;

    setState(() {
      isAddingMember = true;
    });

    try {
      final response = await ApiService.addMemberToHousehold(
        householdId: household.id,
        email: email,
      );

      if (!mounted) return;

      handleUpdatedHousehold(response);

      ScaffoldMessenger.of(
        context,
      ).showSnackBar(const SnackBar(content: Text('Đã thêm thành viên')));
    } catch (e) {
      if (!mounted) return;

      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(e.toString())));
    } finally {
      if (mounted) {
        setState(() {
          isAddingMember = false;
        });
      }
    }
  }

  Future<void> showCreateVirtualMemberDialog() async {
    final nameController = TextEditingController();
    final noteController = TextEditingController();

    final result = await showDialog<Map<String, String>>(
      context: context,
      builder: (context) {
        return AlertDialog(
          title: const Text('Tạo thành viên ảo'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: nameController,
                textCapitalization: TextCapitalization.words,
                decoration: const InputDecoration(
                  labelText: 'Tên thành viên ảo',
                  hintText: 'Ví dụ: Anh Nam, Bạn của Khánh',
                ),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: noteController,
                maxLines: 2,
                decoration: const InputDecoration(
                  labelText: 'Ghi chú',
                  hintText: 'Không bắt buộc',
                ),
              ),
              const SizedBox(height: 12),
              const Text(
                'Thành viên ảo không đăng nhập và không nhận thông báo. Công nợ liên quan sẽ được người dùng thật đánh dấu đã thanh toán ngoài đời.',
                style: TextStyle(
                  color: Color(0xFF6B7280),
                  fontSize: 12,
                  height: 1.35,
                ),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () {
                Navigator.pop(context);
              },
              child: const Text('Hủy'),
            ),
            ElevatedButton(
              onPressed: () {
                final name = nameController.text.trim();

                if (name.length < 2) {
                  return;
                }

                Navigator.pop(context, {
                  'display_name': name,
                  'note': noteController.text.trim(),
                });
              },
              child: const Text('Tạo'),
            ),
          ],
        );
      },
    );

    if (result == null) return;

    setState(() {
      isAddingVirtualMember = true;
    });

    try {
      final response = await ApiService.createVirtualMember(
        householdId: household.id,
        displayName: result['display_name'] ?? '',
        note: result['note'] ?? '',
      );

      if (!mounted) return;

      handleUpdatedHousehold(response);

      ScaffoldMessenger.of(
        context,
      ).showSnackBar(const SnackBar(content: Text('Đã tạo thành viên ảo')));
    } catch (e) {
      if (!mounted) return;

      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(e.toString())));
    } finally {
      if (mounted) {
        setState(() {
          isAddingVirtualMember = false;
        });
      }
    }
  }

  void handleUpdatedHousehold(Map<String, dynamic> response) {
    if (response['household'] == null) return;

    final updatedHousehold = Household.fromJson(
      Map<String, dynamic>.from(response['household']),
    );

    setState(() {
      household = updatedHousehold;
    });

    widget.onHouseholdUpdated(updatedHousehold);
  }

  Future<void> confirmKickMember(dynamic member) async {
    if (!canKickMember(member) || isKickingMember) return;

    final memberId = getMemberId(member);
    final memberName = getMemberName(member);
    final memberEmail = getMemberEmail(member);
    final isVirtual = getMemberIsVirtual(member);

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) {
        return AlertDialog(
          title: Text(isVirtual ? 'Xóa thành viên ảo?' : 'Xóa thành viên?'),
          content: Text(
            isVirtual
                ? 'Bạn có chắc muốn xóa $memberName khỏi nhóm?\n\nNếu thành viên ảo còn công nợ chưa thanh toán, hệ thống sẽ không cho xóa.'
                : 'Bạn có chắc muốn xóa $memberName khỏi nhóm?\n\n$memberEmail\n\nNếu thành viên còn công nợ chưa thanh toán, hệ thống sẽ không cho xóa.',
          ),
          actions: [
            TextButton(
              onPressed: () {
                Navigator.pop(context, false);
              },
              child: const Text('Hủy'),
            ),
            ElevatedButton(
              style: ElevatedButton.styleFrom(backgroundColor: Colors.red),
              onPressed: () {
                Navigator.pop(context, true);
              },
              child: const Text('Xóa'),
            ),
          ],
        );
      },
    );

    if (confirmed != true) return;

    setState(() {
      isKickingMember = true;
      kickingMemberId = memberId;
    });

    try {
      final response = await ApiService.kickMemberFromHousehold(
        householdId: household.id,
        memberId: memberId,
      );

      if (!mounted) return;

      handleUpdatedHousehold(response);

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            isVirtual ? 'Đã xóa thành viên ảo' : 'Đã xóa thành viên khỏi nhóm',
          ),
        ),
      );
    } catch (e) {
      if (!mounted) return;

      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(e.toString())));
    } finally {
      if (mounted) {
        setState(() {
          isKickingMember = false;
          kickingMemberId = null;
        });
      }
    }
  }

  Widget buildRoleBadge(String label, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.16),
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(
        label,
        style: TextStyle(
          fontSize: 11,
          fontWeight: FontWeight.w900,
          color: color,
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final members = List<dynamic>.from(household.members);

    members.sort((a, b) {
      final roleA = getMemberRole(a);
      final roleB = getMemberRole(b);
      final virtualA = getMemberIsVirtual(a);
      final virtualB = getMemberIsVirtual(b);

      if (roleA == 'owner' && roleB != 'owner') {
        return -1;
      }

      if (roleA != 'owner' && roleB == 'owner') {
        return 1;
      }

      if (!virtualA && virtualB) {
        return -1;
      }

      if (virtualA && !virtualB) {
        return 1;
      }

      return getMemberName(a).compareTo(getMemberName(b));
    });

    final isAdding = isAddingMember || isAddingVirtualMember;

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: const Text('Thành viên'),
        backgroundColor: AppColors.background,
        elevation: 0,
        actions: [
          if (isCurrentUserOwner)
            isAdding
                ? const Padding(
                    padding: EdgeInsets.only(right: 16),
                    child: Center(
                      child: SizedBox(
                        width: 20,
                        height: 20,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      ),
                    ),
                  )
                : PopupMenuButton<String>(
                    icon: const Icon(Icons.person_add_alt_1_rounded),
                    onSelected: (value) {
                      if (value == 'real') {
                        showAddMemberDialog();
                      }

                      if (value == 'virtual') {
                        showCreateVirtualMemberDialog();
                      }
                    },
                    itemBuilder: (context) => const [
                      PopupMenuItem(
                        value: 'real',
                        child: ListTile(
                          leading: Icon(Icons.mail_outline_rounded),
                          title: Text('Thêm bằng email'),
                          dense: true,
                          contentPadding: EdgeInsets.zero,
                        ),
                      ),
                      PopupMenuItem(
                        value: 'virtual',
                        child: ListTile(
                          leading: Icon(Icons.person_outline_rounded),
                          title: Text('Tạo thành viên ảo'),
                          dense: true,
                          contentPadding: EdgeInsets.zero,
                        ),
                      ),
                    ],
                  ),
        ],
      ),
      body: ListView.separated(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 32),
        itemCount: members.length,
        separatorBuilder: (_, _) => const SizedBox(height: 10),
        itemBuilder: (context, index) {
          final member = members[index];
          final role = getMemberRole(member);
          final memberId = getMemberId(member);
          final isVirtual = getMemberIsVirtual(member);
          final isCurrentKicking =
              isKickingMember && kickingMemberId == memberId;

          return Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(18),
              border: Border.all(
                color: isVirtual ? const Color(0xFFBAE6FD) : AppColors.border,
              ),
            ),
            child: Row(
              children: [
                buildAvatar(member),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        getMemberName(member),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          fontSize: 15,
                          fontWeight: FontWeight.w900,
                          color: Color(0xFF111827),
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        isVirtual
                            ? 'Thành viên ảo • không dùng app'
                            : getMemberEmail(member),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.w600,
                          color: Color(0xFF6B7280),
                        ),
                      ),
                    ],
                  ),
                ),
                if (isVirtual) buildRoleBadge('Ảo', const Color(0xFF0284C7)),
                if (role == 'owner') ...[
                  const SizedBox(width: 8),
                  buildRoleBadge('Owner', Colors.amber),
                ],
                if (canKickMember(member))
                  isCurrentKicking
                      ? const Padding(
                          padding: EdgeInsets.all(12),
                          child: SizedBox(
                            width: 18,
                            height: 18,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          ),
                        )
                      : PopupMenuButton<String>(
                          icon: const Icon(Icons.more_horiz_rounded),
                          onSelected: (value) {
                            if (value == 'kick') {
                              confirmKickMember(member);
                            }
                          },
                          itemBuilder: (context) => [
                            PopupMenuItem(
                              value: 'kick',
                              child: Text(
                                isVirtual
                                    ? 'Xóa thành viên ảo'
                                    : 'Xóa khỏi nhóm',
                                style: const TextStyle(
                                  color: Colors.red,
                                  fontWeight: FontWeight.w700,
                                ),
                              ),
                            ),
                          ],
                        ),
              ],
            ),
          );
        },
      ),
    );
  }
}
