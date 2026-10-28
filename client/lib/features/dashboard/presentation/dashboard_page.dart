// Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
// Proprietary and confidential. See LICENSE in the project root.

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/widgets/common.dart';
import '../../../core/widgets/header_actions.dart';
import '../../auth/presentation/auth_controller.dart';
import '../../shell/presentation/shells.dart';
import '../domain/dashboard_data.dart';
import 'dashboard_providers.dart';
import 'trend_chart.dart';

class DashboardPage extends ConsumerWidget {
  const DashboardPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final data = ref.watch(dashboardProvider);
    final user = ref.watch(authControllerProvider).user;
    return CandidateScaffold(
      title: 'Dashboard',
      subtitle: data.value?.today,
      actions: const [
        HeaderSearch(hint: 'Search reports'),
        BellButton(),
      ],
      child: data.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) =>
            Center(child: Text('Could not load the dashboard: $e')),
        data: (d) => _Body(
          data: d,
          name: user?.name ?? 'there',
          headline: user?.headline ?? '',
        ),
      ),
    );
  }
}

class _Body extends StatelessWidget {
  const _Body({required this.data, required this.name, required this.headline});

  final DashboardData data;
  final String name;
  final String headline;

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    final text = Theme.of(context).textTheme;
    final wide = MediaQuery.sizeOf(context).width >= 1180;
    final mastery = _MasteryCard(items: data.mastery);
    final trend = _TrendCard(points: data.trend, delta: data.trendDelta);
    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(38, 28, 38, 36),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Welcome, $name',
                      style: text.headlineMedium?.copyWith(fontSize: 34),
                    ),
                    const SizedBox(height: 8),
                    Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          'Target role',
                          style: text.bodyMedium?.copyWith(color: c.textMuted),
                        ),
                        const SizedBox(width: 10),
                        if (headline.isNotEmpty) Pill(headline),
                      ],
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 16),
              ElevatedButton.icon(
                onPressed: () => context.go('/practice'),
                icon: const Icon(Icons.add, size: 18),
                label: const Text('Start New Interview'),
              ),
            ],
          ),
          const SizedBox(height: 22),
          if (data.draft != null) _DraftBanner(draft: data.draft!),
          const SizedBox(height: 18),
          if (wide)
            IntrinsicHeight(
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Expanded(flex: 14, child: mastery),
                  const SizedBox(width: 16),
                  Expanded(flex: 10, child: trend),
                ],
              ),
            )
          else ...[
            mastery,
            const SizedBox(height: 16),
            trend,
          ],
          const SizedBox(height: 22),
          _HistoryCard(items: data.history),
        ],
      ),
    );
  }
}

class _DraftBanner extends StatelessWidget {
  const _DraftBanner({required this.draft});

  final DraftSession draft;

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    final text = Theme.of(context).textTheme;
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: c.primaryTint,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: c.primary.withValues(alpha: 0.25)),
      ),
      child: Wrap(
        alignment: WrapAlignment.spaceBetween,
        crossAxisAlignment: WrapCrossAlignment.center,
        runSpacing: 12,
        spacing: 16,
        children: [
          Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                width: 44,
                height: 44,
                decoration: BoxDecoration(
                  color: c.surface,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Icon(Icons.code, color: c.primaryStrong, size: 20),
              ),
              const SizedBox(width: 16),
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Text(
                        draft.title,
                        style: text.titleMedium?.copyWith(
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                      const SizedBox(width: 10),
                      Text(
                        'DRAFT',
                        style: TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.w800,
                          color: c.primaryStrong,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 4),
                  Text(
                    'Question ${draft.question} of ${draft.totalQuestions} · ${draft.elapsed} elapsed · Last saved ${draft.savedAgo}',
                    style: text.bodySmall?.copyWith(fontSize: 13),
                  ),
                ],
              ),
            ],
          ),
          ElevatedButton.icon(
            onPressed: () => context.go('/interview/${draft.id}'),
            icon: const Icon(Icons.play_arrow_outlined, size: 18),
            label: const Text('Resume Interview'),
          ),
        ],
      ),
    );
  }
}

class _MasteryCard extends StatelessWidget {
  const _MasteryCard({required this.items});

  final List<TopicMastery> items;

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    final text = Theme.of(context).textTheme;
    return AppCard(
      padding: const EdgeInsets.fromLTRB(18, 18, 18, 22),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Topic mastery',
                      style: text.titleMedium?.copyWith(
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text('Based on your last 90 days', style: text.bodySmall),
                  ],
                ),
              ),
              Text(
                'View breakdown',
                style: TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                  color: c.primaryStrong,
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          for (final m in items) ...[
            Row(
              children: [
                Text(
                  m.topic,
                  style: text.bodyMedium?.copyWith(fontWeight: FontWeight.w500),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    '${m.questionsPracticed} questions practiced',
                    style: text.bodySmall?.copyWith(color: c.textFaint),
                  ),
                ),
                Text(
                  m.score.toStringAsFixed(1),
                  style: monoStyle(context, size: 13, weight: FontWeight.w600),
                ),
              ],
            ),
            const SizedBox(height: 8),
            ScoreBar(value: m.score / 10),
            const SizedBox(height: 16),
          ],
        ],
      ),
    );
  }
}

class _TrendCard extends StatelessWidget {
  const _TrendCard({required this.points, required this.delta});

  final List<TrendPoint> points;
  final double delta;

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    final text = Theme.of(context).textTheme;
    return AppCard(
      padding: const EdgeInsets.fromLTRB(18, 18, 18, 14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  'Performance trend',
                  style: text.titleMedium?.copyWith(
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ),
              Icon(Icons.trending_up, size: 14, color: c.primaryStrong),
              const SizedBox(width: 4),
              Text(
                '+${delta.toStringAsFixed(1)}',
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                  color: c.primaryStrong,
                ),
              ),
            ],
          ),
          const SizedBox(height: 2),
          Text('Last five completed sessions', style: text.bodySmall),
          const SizedBox(height: 10),
          SizedBox(height: 190, child: TrendChart(points: points)),
        ],
      ),
    );
  }
}

class _HistoryCard extends StatelessWidget {
  const _HistoryCard({required this.items});

  final List<ReportSummary> items;

  static const _columns = <(String, int)>[
    ('REPORT', 2),
    ('TRACK', 4),
    ('LEVEL', 2),
    ('DATE', 3),
    ('DURATION', 2),
    ('SCORE', 2),
    ('STATUS', 3),
  ];

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    final text = Theme.of(context).textTheme;
    return AppCard(
      padding: EdgeInsets.zero,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(18, 18, 18, 14),
            child: Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Recent interview history',
                        style: text.titleMedium?.copyWith(
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        'Your latest completed sessions',
                        style: text.bodySmall,
                      ),
                    ],
                  ),
                ),
                InkWell(
                  onTap: () => context.go('/reports'),
                  child: Text(
                    'View all reports',
                    style: TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.w600,
                      color: c.text,
                    ),
                  ),
                ),
              ],
            ),
          ),
          Divider(color: c.border),
          LayoutBuilder(
            builder: (context, box) => SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: SizedBox(
                width: box.maxWidth < 820 ? 820 : box.maxWidth,
                child: Column(
                  children: [
                    _row(
                      context,
                      header: true,
                      cells: [
                        for (final col in _columns)
                          Text(col.$1, style: _headStyle(c)),
                      ],
                    ),
                    for (final r in items) ...[
                      Divider(color: c.border),
                      InkWell(
                        onTap: () => context.go('/reports/${r.id}'),
                        child: _row(
                          context,
                          cells: [
                            Text(
                              '#${r.id}',
                              style: monoStyle(
                                context,
                                size: 12,
                                color: c.textMuted,
                              ),
                            ),
                            Text(
                              r.track,
                              style: text.bodyMedium?.copyWith(
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                            Text(
                              r.level.label,
                              style: text.bodySmall?.copyWith(fontSize: 13),
                            ),
                            Text(
                              r.date,
                              style: text.bodySmall?.copyWith(fontSize: 13),
                            ),
                            Text(
                              '${r.durationMinutes} min',
                              style: text.bodySmall?.copyWith(fontSize: 13),
                            ),
                            Text(
                              r.score.toStringAsFixed(1),
                              style: monoStyle(
                                context,
                                size: 13,
                                weight: FontWeight.w700,
                              ),
                            ),
                            Align(
                              alignment: Alignment.centerLeft,
                              child: Pill(
                                r.verdictLabel,
                                tone: r.verdict == Verdict.ready
                                    ? PillTone.success
                                    : PillTone.neutral,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                    const SizedBox(height: 72),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  TextStyle _headStyle(AppColors c) =>
      TextStyle(fontSize: 11, letterSpacing: 0.6, color: c.textMuted);

  Widget _row(
    BuildContext context, {
    required List<Widget> cells,
    bool header = false,
  }) {
    return Padding(
      padding: EdgeInsets.symmetric(horizontal: 18, vertical: header ? 12 : 16),
      child: Row(
        children: [
          for (var i = 0; i < cells.length; i++)
            Expanded(flex: _columns[i].$2, child: cells[i]),
          SizedBox(
            width: 24,
            child: header ? null : const Icon(Icons.chevron_right, size: 18),
          ),
        ],
      ),
    );
  }
}
