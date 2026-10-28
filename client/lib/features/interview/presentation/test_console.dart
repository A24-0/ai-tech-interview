// Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
// Proprietary and confidential. See LICENSE in the project root.

import 'package:flutter/material.dart';

import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_theme.dart';
import '../domain/interview_models.dart';

class TestConsole extends StatefulWidget {
  const TestConsole({super.key, required this.report, required this.running});

  final RunReport? report;
  final bool running;

  @override
  State<TestConsole> createState() => _TestConsoleState();
}

class _TestConsoleState extends State<TestConsole> {
  bool _open = true;

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    final report = widget.report;
    final failed =
        report != null && (report.failed > 0 || report.error != null);
    return Container(
      decoration: BoxDecoration(
        color: c.surface,
        border: Border(top: BorderSide(color: c.border)),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          InkWell(
            onTap: () => setState(() => _open = !_open),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
              child: Row(
                children: [
                  if (widget.running)
                    const SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  else
                    Icon(
                      report == null
                          ? Icons.terminal
                          : (failed
                                ? Icons.error_outline
                                : Icons.check_circle_outline),
                      size: 16,
                      color: report == null
                          ? c.textMuted
                          : (failed ? c.warning : c.primary),
                    ),
                  const SizedBox(width: 10),
                  Text(
                    widget.running
                        ? 'Running tests…'
                        : (report?.summary ??
                              'Run your code to see test results'),
                    style: const TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                  if (report != null &&
                      !widget.running &&
                      report.error == null) ...[
                    const SizedBox(width: 10),
                    Text(
                      '${report.totalMs} ms  ·  ${report.memoryMb} MB',
                      style: monoStyle(context, size: 11, color: c.textMuted),
                    ),
                  ],
                  const Spacer(),
                  Text(
                    'Test console',
                    style: TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.w600,
                      color: c.text,
                    ),
                  ),
                  Icon(
                    _open ? Icons.keyboard_arrow_up : Icons.keyboard_arrow_down,
                    size: 18,
                  ),
                ],
              ),
            ),
          ),
          if (_open && report != null) ...[
            Divider(color: c.border),
            Container(
              color: c.background,
              padding: const EdgeInsets.all(16),
              child: Column(
                children: [
                  if (report.cases.isNotEmpty)
                    LayoutBuilder(
                      builder: (context, box) {
                        final columns = box.maxWidth >= 720 ? 3 : 1;
                        final width =
                            (box.maxWidth - 14 * (columns - 1)) / columns;
                        return Wrap(
                          spacing: 14,
                          runSpacing: 14,
                          children: [
                            for (final t in report.cases)
                              SizedBox(
                                width: width,
                                child: _CaseCard(result: t),
                              ),
                          ],
                        );
                      },
                    ),
                  if (report.cases.isNotEmpty) const SizedBox(height: 14),
                  _MetricsBar(metrics: report.metrics),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _CaseCard extends StatelessWidget {
  const _CaseCard({required this.result});

  final TestCaseResult result;

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    final ok = result.passed;
    final line = monoStyle(context, size: 12, color: c.textMuted);
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: ok ? c.surface : c.dangerTint,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: ok ? c.border : c.danger.withValues(alpha: 0.4),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                ok ? Icons.check_circle_outline : Icons.cancel_outlined,
                size: 15,
                color: ok ? c.primary : c.danger,
              ),
              const SizedBox(width: 8),
              Text(
                result.name,
                style: const TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const Spacer(),
              Text(
                '${result.timeMs} ms',
                style: monoStyle(context, size: 11, color: c.textMuted),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Text('Input: ${result.input}', style: line),
          const SizedBox(height: 4),
          Text('Expected: ${result.expected}', style: line),
          const SizedBox(height: 4),
          Text(
            'Received: ${result.received}',
            style: line.copyWith(color: ok ? c.primaryStrong : c.danger),
          ),
        ],
      ),
    );
  }
}

class _MetricsBar extends StatelessWidget {
  const _MetricsBar({required this.metrics});

  final AstMetrics metrics;

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    Widget item(String label, int value) => Text.rich(
      TextSpan(
        children: [
          TextSpan(
            text: '$label  ',
            style: monoStyle(context, size: 11, color: c.textMuted),
          ),
          TextSpan(
            text: '$value',
            style: monoStyle(context, size: 11, color: c.text),
          ),
        ],
      ),
    );
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      decoration: BoxDecoration(
        color: c.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: c.border),
      ),
      child: Wrap(
        alignment: WrapAlignment.spaceBetween,
        runSpacing: 8,
        spacing: 24,
        children: [
          const Text(
            'AST metrics',
            style: TextStyle(fontSize: 13, fontWeight: FontWeight.w500),
          ),
          item('Complexity', metrics.complexity),
          item('Functions', metrics.functions),
          item('Branches', metrics.branches),
          item('Max depth', metrics.maxDepth),
        ],
      ),
    );
  }
}
