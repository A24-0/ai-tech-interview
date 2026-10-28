// Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
// Proprietary and confidential. See LICENSE in the project root.

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/domain/level.dart';
import '../data/mock_auth_repository.dart';
import '../domain/auth_repository.dart';
import '../domain/user_account.dart';

final authRepositoryProvider = Provider<AuthRepository>(
  (ref) => MockAuthRepository(),
);

class AuthState {
  const AuthState({this.user, this.loading = false, this.error});

  final UserAccount? user;
  final bool loading;
  final String? error;
}

class AuthController extends Notifier<AuthState> {
  @override
  AuthState build() => const AuthState();

  Future<void> signIn(String email, String password, Level level) {
    return _run(
      () => ref
          .read(authRepositoryProvider)
          .signIn(email: email, password: password, level: level),
    );
  }

  Future<void> signUp(String email, String password, Level level) {
    return _run(
      () => ref
          .read(authRepositoryProvider)
          .signUp(email: email, password: password, level: level),
    );
  }

  void clearError() {
    if (state.error != null) state = AuthState(user: state.user);
  }

  void signOut() => state = const AuthState();

  Future<void> _run(Future<UserAccount> Function() action) async {
    state = const AuthState(loading: true);
    try {
      state = AuthState(user: await action());
    } on AuthException catch (e) {
      state = AuthState(error: e.message);
    }
  }
}

final authControllerProvider = NotifierProvider<AuthController, AuthState>(
  AuthController.new,
);
