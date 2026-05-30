class HouseholdMember {
  final String id;

  final int user;

  final String userEmail;
  final String userFullName;
  final String userAvatar;

  final String role;
  final bool isVirtual;

  HouseholdMember({
    required this.id,
    required this.user,
    required this.userEmail,
    required this.userFullName,
    required this.userAvatar,
    required this.role,
    required this.isVirtual,
  });

  factory HouseholdMember.fromJson(
    Map<String, dynamic> json,
  ) {
    return HouseholdMember(
      id: json['id']?.toString() ?? '',

      user: json['user'] is int
          ? json['user']
          : int.tryParse(json['user']?.toString() ?? '') ?? 0,

      userEmail: json['user_email']?.toString() ??
          json['email']?.toString() ??
          '',

      userFullName: json['user_full_name']?.toString() ??
          json['full_name']?.toString() ??
          '',

      userAvatar: json['user_avatar']?.toString() ??
          json['avatar_url']?.toString() ??
          json['avatar']?.toString() ??
          '',

      role: json['role']?.toString() ?? '',

      isVirtual: json['is_virtual'] == true ||
          json['is_virtual']?.toString().toLowerCase() == 'true',
    );
  }

  String get displayName {
    if (userFullName.trim().isNotEmpty) {
      return userFullName;
    }

    if (isVirtual) {
      return 'Thành viên ảo';
    }

    return userEmail;
  }
}
