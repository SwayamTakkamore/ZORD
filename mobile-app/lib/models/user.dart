class User {
  final String? id;
  final String? username;
  final String? email;
  final String? role;
  final DateTime? createdAt;
  final DateTime? updatedAt;

  const User({
    this.id,
    this.username,
    this.email,
    this.role,
    this.createdAt,
    this.updatedAt,
  });

  /// Create User from JSON response
  factory User.fromJson(Map<String, dynamic> json) {
    return User(
      id: json['id']?.toString() ?? json['_id']?.toString(),
      username: json['username']?.toString(),
      email: json['email']?.toString(),
      role: json['role']?.toString(),
      createdAt: json['created_at'] != null 
          ? DateTime.tryParse(json['created_at'].toString())
          : json['createdAt'] != null
              ? DateTime.tryParse(json['createdAt'].toString())
              : null,
      updatedAt: json['updated_at'] != null 
          ? DateTime.tryParse(json['updated_at'].toString())
          : json['updatedAt'] != null
              ? DateTime.tryParse(json['updatedAt'].toString())
              : null,
    );
  }

  /// Convert User to JSON
  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'username': username,
      'email': email,
      'role': role,
      'created_at': createdAt?.toIso8601String(),
      'updated_at': updatedAt?.toIso8601String(),
    };
  }

  /// Create a copy of the user with updated fields
  User copyWith({
    String? id,
    String? username,
    String? email,
    String? role,
    DateTime? createdAt,
    DateTime? updatedAt,
  }) {
    return User(
      id: id ?? this.id,
      username: username ?? this.username,
      email: email ?? this.email,
      role: role ?? this.role,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
    );
  }

  /// Get display name for the user
  String get displayName {
    if (username != null && username!.isNotEmpty) {
      return username!;
    }
    if (email != null && email!.isNotEmpty) {
      return email!;
    }
    return 'User';
  }

  /// Get user initials for avatar
  String get initials {
    String name = displayName;
    if (name.isEmpty) return 'U';
    
    List<String> nameParts = name.split(' ');
    if (nameParts.length >= 2) {
      return '${nameParts[0][0]}${nameParts[1][0]}'.toUpperCase();
    }
    return name[0].toUpperCase();
  }

  /// Check if user has a specific role
  bool hasRole(String targetRole) {
    return role != null && role!.toLowerCase() == targetRole.toLowerCase();
  }

  /// Check if user is admin
  bool get isAdmin {
    return hasRole('admin');
  }

  /// Check if user is moderator
  bool get isModerator {
    return hasRole('moderator');
  }

  /// Check if user is regular user
  bool get isRegularUser {
    return hasRole('user') || role == null;
  }

  @override
  String toString() {
    return 'User(id: $id, username: $username, email: $email, role: $role)';
  }

  @override
  bool operator ==(Object other) {
    if (identical(this, other)) return true;
    
    return other is User &&
        other.id == id &&
        other.username == username &&
        other.email == email &&
        other.role == role &&
        other.createdAt == createdAt &&
        other.updatedAt == updatedAt;
  }

  @override
  int get hashCode {
    return Object.hash(
      id,
      username,
      email,
      role,
      createdAt,
      updatedAt,
    );
  }
}