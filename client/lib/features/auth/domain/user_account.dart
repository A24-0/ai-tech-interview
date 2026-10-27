// Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
// Proprietary and confidential. See LICENSE in the project root.

import '../../../core/domain/level.dart';

enum UserRole { candidate, admin }

class UserAccount {
  const UserAccount({
    required this.name,
    required this.email,
    required this.role,
    required this.headline,
    this.level = Level.middle,
  });

  final String name;
  final String email;
  final UserRole role;
  final String headline;
  final Level level;

  String get initials {
    final parts = name
        .trim()
        .split(RegExp(r'\s+'))
        .where((p) => p.isNotEmpty)
        .toList();
    if (parts.isEmpty) return '?';
    if (parts.length == 1) return parts.first[0].toUpperCase();
    return (parts.first[0] + parts.last[0]).toUpperCase();
  }

  String get firstName => name.trim().split(RegExp(r'\s+')).first;

  UserAccount copyWith({Level? level}) {
    return UserAccount(
      name: name,
      email: email,
      role: role,
      headline: headline,
      level: level ?? this.level,
    );
  }
}
