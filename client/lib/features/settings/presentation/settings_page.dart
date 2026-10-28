// Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
// Proprietary and confidential. See LICENSE in the project root.

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/theme/app_colors.dart';
import '../../../core/theme/theme_controller.dart';
import '../../../core/widgets/common.dart';
import '../../auth/presentation/auth_controller.dart';
import '../../shell/presentation/shells.dart';

class SettingsPage extends ConsumerWidget {
  const SettingsPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = ref.watch(authControllerProvider).user;
    final dark = ref.watch(themeModeProvider) == ThemeMode.dark;
    final c = context.colors;
    final text = Theme.of(context).textTheme;
    return CandidateScaffold(
      title: 'Settings',
      subtitle: 'Account and appearance',
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(32),
        child: Align(
          alignment: Alignment.topLeft,
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 640),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                AppCard(
                  child: Row(
                    children: [
                      Avatar(user?.initials ?? '?', size: 44),
                      const SizedBox(width: 16),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(user?.name ?? '', style: text.titleMedium),
                            const SizedBox(height: 2),
                            Text(user?.email ?? '', style: text.bodySmall),
                          ],
                        ),
                      ),
                      Pill(user?.level.label ?? ''),
                    ],
                  ),
                ),
                const SizedBox(height: 16),
                AppCard(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 20,
                    vertical: 8,
                  ),
                  child: SwitchListTile(
                    contentPadding: EdgeInsets.zero,
                    value: dark,
                    activeThumbColor: c.primary,
                    title: const Text('Dark theme'),
                    subtitle: const Text(
                      'Easier on the eyes during long sessions',
                    ),
                    onChanged: (_) =>
                        ref.read(themeModeProvider.notifier).toggle(),
                  ),
                ),
                const SizedBox(height: 16),
                OutlinedButton.icon(
                  onPressed: ref.read(authControllerProvider.notifier).signOut,
                  icon: const Icon(Icons.logout, size: 16),
                  label: const Text('Sign out'),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
