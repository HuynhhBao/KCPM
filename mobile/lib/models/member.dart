class HouseholdMember {
  final String id;
  final int user;

  final String email;
  final String fullName;
  final String userAvatar;

  final String role;
  final bool isVirtual;

  HouseholdMember({
    required this.id,
    required this.user,
    required this.email,
    required this.fullName,
    required this.userAvatar,
    required this.role,
    required this.isVirtual,
  });

  factory HouseholdMember.fromJson(Map<String, dynamic> json) {
    return HouseholdMember(
      id: json['id']?.toString() ?? '',
      user: json['user'] is int
          ? json['user']
          : int.tryParse(json['user']?.toString() ?? '') ?? 0,
      email: json['user_email']?.toString() ?? json['email']?.toString() ?? '',
      fullName:
          json['user_full_name']?.toString() ??
          json['full_name']?.toString() ??
          '',
      userAvatar:
          json['user_avatar']?.toString() ??
          json['avatar_url']?.toString() ??
          json['avatar']?.toString() ??
          '',
      role: json['role']?.toString() ?? 'member',
      isVirtual: json['is_virtual'] ?? false,
    );
  }

  String get displayName {
    if (fullName.trim().isNotEmpty) {
      return fullName;
    }

    if (isVirtual) {
      return 'Thành viên ảo';
    }

    return email;
  }
}
