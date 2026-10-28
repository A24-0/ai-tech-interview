// Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
// Proprietary and confidential. See LICENSE in the project root.

import '../../../core/domain/level.dart';
import '../domain/auth_repository.dart';
import '../domain/user_account.dart';

class MockAuthRepository implements AuthRepository {
  MockAuthRepository({this.delay = const Duration(milliseconds: 500)});

  final Duration delay;

  static const _accounts = {
    'demo@interview.dev': (
      'demo123',
      'Yuri Sigma',
      'Senior Python Engineer',
      UserRole.candidate,
    ),
    'admin@interview.dev': (
      'admin123',
      'Admin Sigma',
      'Content operations',
      UserRole.admin,
    ),
  };

  @override
  Future<UserAccount> signIn({
    required String email,
    required String password,
    required Level level,
  }) async {
    await Future<void>.delayed(delay);
    final record = _accounts[email.trim().toLowerCase()];
    if (record == null || record.$1 != password) {
      throw const AuthException(
        'Invalid email or password. Please check your credentials and try again.',
      );
    }
    return UserAccount(
      name: record.$2,
      email: email.trim(),
      role: record.$4,
      headline: record.$3,
      level: level,
    );
  }

  @override
  Future<UserAccount> signUp({
    required String email,
    required String password,
    required Level level,
  }) async {
    await Future<void>.delayed(delay);
    final address = email.trim().toLowerCase();
    if (!address.contains('@') || password.length < 8) {
      throw const AuthException(
        'Use a valid email and a password of at least 8 characters.',
      );
    }
    if (_accounts.containsKey(address)) {
      throw const AuthException('An account with this email already exists.');
    }
    final local = address.split('@').first;
    final name = local.isEmpty
        ? 'New User'
        : '${local[0].toUpperCase()}${local.substring(1)}';
    return UserAccount(
      name: name,
      email: address,
      role: UserRole.candidate,
      headline: '${level.label} candidate',
      level: level,
    );
  }
}
