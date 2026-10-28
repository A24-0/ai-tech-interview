// Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
// Proprietary and confidential. See LICENSE in the project root.

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/widgets/app_shell.dart';
import '../../auth/domain/user_account.dart';
import '../../auth/presentation/auth_controller.dart';

const candidateNav = [
  NavItem('Dashboard', Icons.grid_view_rounded, '/dashboard'),
  NavItem('Practice', Icons.auto_awesome_outlined, '/practice'),
  NavItem('Reports', Icons.description_outlined, '/reports'),
  NavItem('Settings', Icons.settings_outlined, '/settings'),
];

const adminNav = [
  NavItem('Question bank', Icons.storage_outlined, '/admin/questions'),
  NavItem('Candidates', Icons.people_outline, '/admin/candidates'),
  NavItem('Reports', Icons.bar_chart_rounded, '/admin/reports'),
  NavItem('Settings', Icons.settings_outlined, '/admin/settings'),
];

class CandidateScaffold extends ConsumerWidget {
  const CandidateScaffold({
    super.key,
    required this.title,
    required this.child,
    this.subtitle,
    this.actions = const [],
    this.activeRoute,
  });

  final String title;
  final String? subtitle;
  final List<Widget> actions;
  final Widget child;
  final String? activeRoute;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = ref.watch(authControllerProvider).user;
    return AppShell(
      items: candidateNav,
      currentRoute: activeRoute ?? GoRouterState.of(context).uri.path,
      brandSubtitle: 'AI simulator',
      user: _shellUser(user, 'Candidate'),
      title: title,
      subtitle: subtitle,
      actions: actions,
      onUserTap: () => _confirmSignOut(context, ref),
      child: child,
    );
  }
}

class AdminScaffold extends ConsumerWidget {
  const AdminScaffold({
    super.key,
    required this.title,
    required this.child,
    this.subtitle,
    this.actions = const [],
  });

  final String title;
  final String? subtitle;
  final List<Widget> actions;
  final Widget child;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = ref.watch(authControllerProvider).user;
    return AppShell(
      items: adminNav,
      currentRoute: GoRouterState.of(context).uri.path,
      brandSubtitle: 'Admin',
      user: _shellUser(user, 'Admin'),
      title: title,
      subtitle: subtitle,
      actions: actions,
      onUserTap: () => _confirmSignOut(context, ref),
      child: child,
    );
  }
}

ShellUser _shellUser(UserAccount? user, String fallback) {
  return ShellUser(
    name: user?.name ?? fallback,
    subtitle: user?.headline ?? '',
    initials: user?.initials ?? '?',
  );
}

Future<void> _confirmSignOut(BuildContext context, WidgetRef ref) async {
  final confirmed = await showDialog<bool>(
    context: context,
    builder: (context) => AlertDialog(
      title: const Text('Sign out?'),
      content: const Text('You will need to sign in again to continue.'),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context, false),
          child: const Text('Cancel'),
        ),
        TextButton(
          onPressed: () => Navigator.pop(context, true),
          child: const Text('Sign out'),
        ),
      ],
    ),
  );
  if (confirmed == true) ref.read(authControllerProvider.notifier).signOut();
}
