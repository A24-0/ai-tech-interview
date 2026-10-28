// Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
// Proprietary and confidential. See LICENSE in the project root.

import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/widgets/common.dart';
import '../../shell/presentation/shells.dart';
import '../data/mock_report_repository.dart';
import '../domain/report_models.dart';
import '../domain/report_repository.dart';

final reportRepositoryProvider = Provider<ReportRepository>(
  (ref) => MockReportRepository(),
);

final reportProvider = FutureProvider.family<AssessmentReport, String>(
  (ref, id) => ref.watch(reportRepositoryProvider).load(id),
);

class ReportPage extends ConsumerWidget {
  const ReportPage({super.key, required this.id});

  final String id;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final report = ref.watch(reportProvider(id));
    return CandidateScaffold(
      title: 'Assessment report',
      subtitle: 'Report #$id',
      activeRoute: '/reports',
      actions: [
        OutlinedButton.icon(
          onPressed: () => ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('PDF export is not available in this build yet.'),
            ),
          ),
          icon: const Icon(Icons.print_outlined, size: 16),
          label: const Text('Print / PDF'),
        ),
        TextButton(
          onPressed: () => context.go('/dashboard'),
          child: const Text('Back to Dashboard'),
        ),
      ],
      child: report.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('Could not load the report: $e')),
        data: (r) => _Body(report: r),
      ),
    );
  }
}

class _Body extends StatelessWidget {
  const _Body({required this.report});

  final AssessmentReport report;

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    final text = Theme.of(context).textTheme;
    final wide = MediaQuery.sizeOf(context).width >= 1180;
    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(38, 26, 38, 32),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _Hero(report: report),
          const SizedBox(height: 28),
          Row(
            children: [
              Expanded(
                child: Text('Competency rubric', style: text.titleLarge),
              ),
              Text('Weighted overall score', style: text.bodySmall),
            ],
          ),
          const SizedBox(height: 14),
          LayoutBuilder(
            builder: (context, box) {
              final columns = box.maxWidth >= 1000
                  ? 4
                  : (box.maxWidth >= 600 ? 2 : 1);
              final width = (box.maxWidth - 14 * (columns - 1)) / columns;
              return Wrap(
                spacing: 14,
                runSpacing: 14,
                children: [
                  for (final r in report.rubric)
                    SizedBox(
                      width: width,
                      child: _RubricCard(score: r),
                    ),
                ],
              );
            },
          ),
          const SizedBox(height: 28),
          Row(
            children: [
              Expanded(
                child: Text('Coding task review', style: text.titleLarge),
              ),
              Pill(
                '${report.coding.passed} / ${report.coding.total} tests passed',
                tone: PillTone.warning,
              ),
            ],
          ),
          const SizedBox(height: 14),
          if (wide)
            IntrinsicHeight(
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Expanded(flex: 13, child: _CodeCard(review: report.coding)),
                  const SizedBox(width: 14),
                  Expanded(
                    flex: 10,
                    child: _CritiqueCard(review: report.coding),
                  ),
                ],
              ),
            )
          else ...[
            _CodeCard(review: report.coding),
            const SizedBox(height: 14),
            _CritiqueCard(review: report.coding),
          ],
          const SizedBox(height: 18),
          _TheoryCard(review: report.theory, wide: wide),
          const SizedBox(height: 20),
          Wrap(
            alignment: WrapAlignment.spaceBetween,
            crossAxisAlignment: WrapCrossAlignment.center,
            runSpacing: 12,
            children: [
              Text(
                'Report #${report.id} · Generated from ${report.prompts} prompts and ${report.coding.total} test cases',
                style: text.bodySmall?.copyWith(fontSize: 12.5),
              ),
              Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  OutlinedButton(
                    onPressed: () => context.go('/dashboard'),
                    child: const Text('Back to Dashboard'),
                  ),
                  const SizedBox(width: 12),
                  ElevatedButton.icon(
                    onPressed: () => context.go('/practice'),
                    icon: Icon(Icons.refresh, size: 16, color: c.surface),
                    label: const Text('Practice Again'),
                  ),
                ],
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _Hero extends StatelessWidget {
  const _Hero({required this.report});

  final AssessmentReport report;

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    final text = Theme.of(context).textTheme;
    Widget meta(IconData icon, String label) => Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 14, color: c.textMuted),
        const SizedBox(width: 6),
        Text(label, style: text.bodySmall?.copyWith(fontSize: 13)),
      ],
    );
    return AppCard(
      radius: 20,
      padding: const EdgeInsets.fromLTRB(24, 22, 28, 22),
      child: SizedBox(
        width: double.infinity,
        child: Wrap(
          alignment: WrapAlignment.spaceBetween,
          crossAxisAlignment: WrapCrossAlignment.center,
          runSpacing: 20,
          spacing: 24,
          children: [
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Pill('COMPLETED', tone: PillTone.success, dot: true),
                const SizedBox(height: 14),
                Text(
                  report.track,
                  style: text.displaySmall?.copyWith(fontSize: 34),
                ),
                const SizedBox(height: 12),
                Wrap(
                  spacing: 18,
                  runSpacing: 6,
                  children: [
                    meta(Icons.calendar_today_outlined, report.date),
                    meta(Icons.schedule, '${report.durationMinutes} min'),
                    meta(Icons.code, report.format),
                  ],
                ),
              ],
            ),
            Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                _ScoreRing(score: report.score),
                const SizedBox(width: 28),
                ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 230),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'VERDICT',
                        style: TextStyle(
                          fontSize: 11,
                          letterSpacing: 0.6,
                          color: c.textFaint,
                        ),
                      ),
                      const SizedBox(height: 6),
                      Text(
                        report.verdictTitle,
                        style: text.headlineSmall?.copyWith(
                          color: c.primaryStrong,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                      const SizedBox(height: 6),
                      Text(
                        report.verdictText,
                        style: text.bodySmall?.copyWith(fontSize: 13),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _ScoreRing extends StatelessWidget {
  const _ScoreRing({required this.score});

  final double score;

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    return SizedBox(
      width: 112,
      height: 112,
      child: CustomPaint(
        painter: _RingPainter(
          value: score / 10,
          color: c.primary,
          track: c.primaryTint,
        ),
        child: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                score.toStringAsFixed(1),
                style: monoStyle(context, size: 28, weight: FontWeight.w700),
              ),
              Text(
                'out of 10',
                style: TextStyle(fontSize: 11, color: c.textMuted),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _RingPainter extends CustomPainter {
  _RingPainter({required this.value, required this.color, required this.track});

  final double value;
  final Color color;
  final Color track;

  @override
  void paint(Canvas canvas, Size size) {
    const stroke = 9.0;
    final rect = Rect.fromLTWH(
      stroke / 2,
      stroke / 2,
      size.width - stroke,
      size.height - stroke,
    );
    final base = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = stroke
      ..strokeCap = StrokeCap.round;
    canvas.drawArc(rect, 0, math.pi * 2, false, base..color = track);
    canvas.drawArc(
      rect,
      -math.pi / 2,
      math.pi * 2 * value.clamp(0, 1),
      false,
      base..color = color,
    );
  }

  @override
  bool shouldRepaint(_RingPainter old) =>
      old.value != value || old.color != color || old.track != track;
}

class _RubricCard extends StatelessWidget {
  const _RubricCard({required this.score});

  final RubricScore score;

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    final text = Theme.of(context).textTheme;
    return AppCard(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              IconTile(score.icon, size: 30),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  score.name,
                  style: text.titleSmall?.copyWith(fontWeight: FontWeight.w500),
                ),
              ),
              Text(
                score.score.toStringAsFixed(1),
                style: monoStyle(context, size: 16, weight: FontWeight.w700),
              ),
            ],
          ),
          const SizedBox(height: 14),
          ScoreBar(value: score.score / 10),
          const SizedBox(height: 12),
          Text(
            score.note,
            style: text.bodySmall?.copyWith(fontSize: 12.5, color: c.textMuted),
          ),
        ],
      ),
    );
  }
}

class _CodeCard extends StatelessWidget {
  const _CodeCard({required this.review});

  final CodingReview review;

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    final lines = review.code.split('\n');
    return AppCard(
      padding: EdgeInsets.zero,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.all(14),
            child: Row(
              children: [
                const Expanded(
                  child: Text(
                    'Submitted solution',
                    style: TextStyle(fontSize: 13, fontWeight: FontWeight.w500),
                  ),
                ),
                Text(
                  review.language,
                  style: monoStyle(context, size: 11, color: c.textMuted),
                ),
              ],
            ),
          ),
          Divider(color: c.border),
          Padding(
            padding: const EdgeInsets.fromLTRB(14, 14, 14, 18),
            child: SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  SizedBox(
                    width: 28,
                    child: Text(
                      [for (var i = 1; i <= lines.length; i++) '$i'].join('\n'),
                      textAlign: TextAlign.right,
                      style: monoStyle(
                        context,
                        size: 12,
                        color: c.textFaint,
                      ).copyWith(height: 1.9),
                    ),
                  ),
                  const SizedBox(width: 16),
                  Text(
                    review.code,
                    style: monoStyle(context, size: 12).copyWith(height: 1.9),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _CritiqueCard extends StatelessWidget {
  const _CritiqueCard({required this.review});

  final CodingReview review;

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    return AppCard(
      padding: const EdgeInsets.all(18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                Icons.auto_awesome_outlined,
                size: 15,
                color: c.primaryStrong,
              ),
              const SizedBox(width: 8),
              const Expanded(
                child: Text(
                  'AI critique',
                  style: TextStyle(fontSize: 14, fontWeight: FontWeight.w500),
                ),
              ),
              Pill(review.complexity, tone: PillTone.success),
            ],
          ),
          const SizedBox(height: 14),
          for (final f in review.findings) ...[
            FindingRow(finding: f),
            const SizedBox(height: 14),
          ],
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: c.surfaceMuted,
              borderRadius: BorderRadius.circular(12),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'RUNTIME PROFILING',
                  style: TextStyle(
                    fontSize: 10.5,
                    letterSpacing: 0.6,
                    color: c.textFaint,
                  ),
                ),
                const SizedBox(height: 8),
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        '${review.timeMs} ms',
                        style: monoStyle(context, size: 12),
                      ),
                    ),
                    Expanded(
                      child: Text(
                        '${review.memoryMb} MB',
                        style: monoStyle(context, size: 12),
                      ),
                    ),
                    Text(
                      '${review.percentile}nd percentile',
                      style: monoStyle(context, size: 12),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class FindingRow extends StatelessWidget {
  const FindingRow({super.key, required this.finding});

  final Finding finding;

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    final positive = finding.tone == FindingTone.positive;
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          width: 24,
          height: 24,
          decoration: BoxDecoration(
            color: positive ? c.primaryTint : c.warningTint,
            shape: BoxShape.circle,
          ),
          child: Icon(
            positive ? Icons.check : Icons.warning_amber_rounded,
            size: 13,
            color: positive ? c.primaryStrong : c.warning,
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                finding.title,
                style: const TextStyle(
                  fontSize: 13.5,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 3),
              Text(
                finding.text,
                style: TextStyle(
                  fontSize: 12.5,
                  height: 1.45,
                  color: c.textMuted,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _TheoryCard extends StatelessWidget {
  const _TheoryCard({required this.review, required this.wide});

  final TheoryReview review;
  final bool wide;

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    final text = Theme.of(context).textTheme;
    final dialogue = Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          width: double.infinity,
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: c.surfaceMuted,
            borderRadius: BorderRadius.circular(12),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'AI INTERVIEWER',
                style: TextStyle(
                  fontSize: 10.5,
                  letterSpacing: 0.6,
                  color: c.textFaint,
                ),
              ),
              const SizedBox(height: 6),
              Text(review.question, style: const TextStyle(fontSize: 13.5)),
            ],
          ),
        ),
        const SizedBox(height: 10),
        Container(
          width: double.infinity,
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: c.primaryTint,
            borderRadius: BorderRadius.circular(12),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'YOU',
                style: TextStyle(
                  fontSize: 10.5,
                  letterSpacing: 0.6,
                  color: c.primaryStrong,
                ),
              ),
              const SizedBox(height: 6),
              Text(
                review.answer,
                style: const TextStyle(fontSize: 13.5, height: 1.45),
              ),
            ],
          ),
        ),
      ],
    );
    final critique = Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        for (final f in review.findings) ...[
          FindingRow(finding: f),
          const SizedBox(height: 14),
        ],
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
          decoration: BoxDecoration(
            color: c.surfaceMuted,
            borderRadius: BorderRadius.circular(12),
          ),
          child: Row(
            children: [
              Expanded(
                child: Text(
                  'Theory score',
                  style: text.bodySmall?.copyWith(fontSize: 13),
                ),
              ),
              Text(
                '${review.score} / 10',
                style: monoStyle(context, size: 13, weight: FontWeight.w700),
              ),
            ],
          ),
        ),
      ],
    );
    return AppCard(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Theory dialogue critique',
            style: text.titleMedium?.copyWith(fontWeight: FontWeight.w500),
          ),
          const SizedBox(height: 14),
          if (wide)
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(child: dialogue),
                const SizedBox(width: 28),
                Expanded(child: critique),
              ],
            )
          else ...[
            dialogue,
            const SizedBox(height: 18),
            critique,
          ],
        ],
      ),
    );
  }
}
