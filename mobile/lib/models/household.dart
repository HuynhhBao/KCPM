import 'household_member.dart';

class Household {
  final String id;

  final String name;

  final String description;

  final String inviteCode;

  final String avatarUrl;

  final bool isActive;

  final List<HouseholdMember> members;

  Household({
    required this.id,
    required this.name,
    required this.description,
    required this.inviteCode,
    required this.avatarUrl,
    required this.isActive,
    required this.members,
  });

  factory Household.fromJson(Map<String, dynamic> json) {
    return Household(
      id: json['id']?.toString() ?? '',

      name: json['name']?.toString() ?? '',

      description: json['description']?.toString() ?? '',

      inviteCode: json['invite_code']?.toString() ?? '',

      avatarUrl: json['avatar_url']?.toString() ?? '',

      isActive: json['is_active'] ?? true,

      members: (json['members'] as List? ?? [])
          .map(
            (item) => HouseholdMember.fromJson(Map<String, dynamic>.from(item)),
          )
          .toList(),
    );
  }
}
