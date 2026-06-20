import 'household_member.dart';

class Household {
  final String id;

  final String name;

  final String description;

  final String inviteCode;

  final String avatarUrl;

  final bool isActive;

  final List<HouseholdMember> members;
  final int memberCount;

  Household({
    required this.id,
    required this.name,
    required this.description,
    required this.inviteCode,
    required this.avatarUrl,
    required this.isActive,
    required this.members,
    required this.memberCount,
  });

  factory Household.fromJson(Map<String, dynamic> json) {
    final rawMembers = json['members'];
    final members = rawMembers is List
        ? rawMembers
              .whereType<Map>()
              .map(
                (item) =>
                    HouseholdMember.fromJson(Map<String, dynamic>.from(item)),
              )
              .toList()
        : <HouseholdMember>[];

    int parseInt(dynamic value) {
      if (value is int) return value;
      if (value is num) return value.toInt();
      return int.tryParse(value?.toString() ?? '') ?? 0;
    }

    return Household(
      id: json['id']?.toString() ?? '',

      name: json['name']?.toString() ?? '',

      description: json['description']?.toString() ?? '',

      inviteCode: json['invite_code']?.toString() ?? '',

      avatarUrl: json['avatar_url']?.toString() ?? '',

      isActive: json['is_active'] ?? true,

      members: members,

      memberCount: parseInt(json['member_count']) > 0
          ? parseInt(json['member_count'])
          : members.length,
    );
  }
}
