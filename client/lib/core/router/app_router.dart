// Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
// Proprietary and confidential. See LICENSE in the project root.

import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../features/admin/presentation/admin_stub_page.dart';
import '../../features/admin/presentation/question_bank_page.dart';
import '../../features/auth/domain/user_account.dart';
import '../../features/auth/presentation/auth_controller.dart';
import '../../features/auth/presentation/auth_page.dart';
import '../../features/dashboard/presentation/dashboard_page.dart';
import '../../features/interview/presentation/interview_page.dart';
import '../../features/practice/presentation/practice_page.dart';
import '../../features/report/presentation/report_page.dart';
import '../../features/report/presentation/reports_page.dart';
import '../../features/settings/presentation/settings_page.dart';

final routerProvider = Provider<GoRouter>((ref) {
  final refresh = ValueNotifier<int>(0);
  ref.listen(
    authControllerProvider.select((s) => s.user),
    (_, _) => refresh.value++,
  );
  ref.onDispose(refresh.dispose);

  final router = GoRouter(
    initialLocation: '/auth',
    refreshListenable: refresh,
    redirect: (context, state) {
      final user = ref.read(authControllerProvider).user;
      final path = state.uri.path;
      if (user == null) return path == '/auth' ? null : '/auth';
      final home = user.role == UserRole.admin
          ? '/admin/questions'
          : '/dashboard';
      if (path == '/auth' || path == '/') return home;
      final adminArea = path.startsWith('/admin');
      if (adminArea && user.role != UserRole.admin) return '/dashboard';
      if (!adminArea && user.role == UserRole.admin) return home;
      return null;
    },
    routes: [
      GoRoute(path: '/auth', builder: (_, _) => const AuthPage()),
      GoRoute(path: '/dashboard', builder: (_, _) => const DashboardPage()),
      GoRoute(path: '/practice', builder: (_, _) => const PracticePage()),
      GoRoute(
        path: '/interview/:id',
        builder: (_, state) => InterviewPage(id: state.pathParameters['id']!),
      ),
      GoRoute(path: '/reports', builder: (_, _) => const ReportsPage()),
      GoRoute(
        path: '/reports/:id',
        builder: (_, state) => ReportPage(id: state.pathParameters['id']!),
      ),
      GoRoute(path: '/settings', builder: (_, _) => const SettingsPage()),
      GoRoute(
        path: '/admin/questions',
        builder: (_, _) => const QuestionBankPage(),
      ),
      GoRoute(
        path: '/admin/candidates',
        builder: (_, _) => const AdminStubPage(title: 'Candidates'),
      ),
      GoRoute(
        path: '/admin/reports',
        builder: (_, _) => const AdminStubPage(title: 'Reports'),
      ),
      GoRoute(
        path: '/admin/settings',
        builder: (_, _) => const AdminStubPage(title: 'Settings'),
      ),
    ],
  );
  ref.onDispose(router.dispose);
  return router;
});
