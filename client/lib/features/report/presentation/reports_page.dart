// Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
// Proprietary and confidential. See LICENSE in the project root.

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/widgets/common.dart';
import '../../dashboard/domain/dashboard_data.dart';
import '../../dashboard/presentation/dashboard_providers.dart';
import '../../shell/presentation/shells.dart';

class ReportsPage extends ConsumerWidget {
  const ReportsPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final data = ref.watch(dashboardProvider);
    final c = context.colors;
    final text = Theme.of(context).textTheme;
    return CandidateScaffold(
      title: 'Reports',
      subtitle: 'Every completed interview with its assessment',
      child: data.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('Could not load reports: $e')),
        data: (d) => ListView.separated(
          padding: const EdgeInsets.all(32),
          itemCount: d.history.length,
          separatorBuilder: (_, _) => const SizedBox(height: 12),
          itemBuilder: (context, i) {
            final r = d.history[i];
            return InkWell(
              borderRadius: BorderRadius.circular(16),
              onTap: () => context.go('/reports/${r.id}'),
              child: AppCard(
                padding: const EdgeInsets.symmetric(
                  horizontal: 20,
                  vertical: 16,
                ),
                child: Row(
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            '${r.track} — ${r.level.label}',
                            style: text.titleSmall,
                          ),
                          const SizedBox(height: 4),
                          Text(
                            '#${r.id} · ${r.date} · ${r.durationMinutes} min',
                            style: text.bodySmall,
                          ),
                        ],
                      ),
                    ),
                    Pill(
                      r.verdictLabel,
                      tone: r.verdict == Verdict.ready
                          ? PillTone.success
                          : PillTone.neutral,
                    ),
                    const SizedBox(width: 20),
                    Text(
                      r.score.toStringAsFixed(1),
                      style: monoStyle(
                        context,
                        size: 16,
                        weight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(width: 12),
                    Icon(Icons.chevron_right, color: c.textMuted),
                  ],
                ),
              ),
            );
          },
        ),
      ),
    );
  }
}
