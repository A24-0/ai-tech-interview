// Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
// Proprietary and confidential. See LICENSE in the project root.

import '../../../core/domain/level.dart';
import 'user_account.dart';

class AuthException implements Exception {
  const AuthException(this.message);

  final String message;

  @override
  String toString() => message;
}

abstract class AuthRepository {
  Future<UserAccount> signIn({
    required String email,
    required String password,
    required Level level,
  });

  Future<UserAccount> signUp({
    required String email,
    required String password,
    required Level level,
  });
}
