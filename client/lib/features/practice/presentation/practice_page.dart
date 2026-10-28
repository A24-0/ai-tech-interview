// Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
// Proprietary and confidential. See LICENSE in the project root.

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/domain/level.dart';
import '../../../core/theme/app_colors.dart';
import '../../../core/widgets/common.dart';
import '../../../core/widgets/header_actions.dart';
import '../../shell/presentation/shells.dart';
import '../domain/topic.dart';
import 'practice_controller.dart';

class PracticePage extends ConsumerWidget {
  const PracticePage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(practiceControllerProvider);
    final controller = ref.read(practiceControllerProvider.notifier);
    final c = context.colors;
    final text = Theme.of(context).textTheme;
    final wide = MediaQuery.sizeOf(context).width >= 1100;
    final picker = Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'PERSONALIZE YOUR SESSION',
          style: TextStyle(
            fontSize: 12,
            letterSpacing: 0.4,
            color: c.primaryStrong,
          ),
        ),
        const SizedBox(height: 10),
        Text('What should we practice?', style: text.headlineMedium),
        const SizedBox(height: 10),
        Text(
          'Choose one target level and the topic areas you want the interviewer to cover.',
          style: text.bodyLarge?.copyWith(color: c.textMuted),
        ),
        const SizedBox(height: 28),
        Row(
          children: [
            Expanded(
              child: Text(
                'Target level',
                style: text.titleLarge?.copyWith(fontWeight: FontWeight.w500),
              ),
            ),
            Text('Single select', style: text.bodySmall),
          ],
        ),
        const SizedBox(height: 14),
        _Grid(
          columns: wide ? 3 : 1,
          children: [
            for (final l in Level.values)
              _LevelCard(
                level: l,
                selected: state.level == l,
                onTap: () => controller.selectLevel(l),
              ),
          ],
        ),
        const SizedBox(height: 30),
        Row(
          children: [
            Expanded(
              child: Text(
                'Topic areas',
                style: text.titleLarge?.copyWith(fontWeight: FontWeight.w500),
              ),
            ),
            Text('${state.topicIds.length} selected', style: text.bodySmall),
          ],
        ),
        const SizedBox(height: 14),
        _Grid(
          columns: wide ? 3 : 1,
          children: [
            for (final t in practiceTopics)
              _TopicCard(
                topic: t,
                selected: state.topicIds.contains(t.id),
                onTap: () => controller.toggleTopic(t.id),
              ),
          ],
        ),
      ],
    );
    return CandidateScaffold(
      title: 'New interview',
      subtitle: 'Configure a focused practice session',
      actions: const [StepBadge('Step 1 of 2'), BellButton()],
      child: SingleChildScrollView(
        padding: const EdgeInsets.fromLTRB(40, 30, 40, 40),
        child: wide
            ? Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(child: picker),
                  const SizedBox(width: 32),
                  SizedBox(
                    width: 350,
                    child: _Summary(
                      state: state,
                      onStart: () => context.go('/interview/new'),
                    ),
                  ),
                ],
              )
            : Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  picker,
                  const SizedBox(height: 28),
                  _Summary(
                    state: state,
                    onStart: () => context.go('/interview/new'),
                  ),
                ],
              ),
      ),
    );
  }
}

class _Grid extends StatelessWidget {
  const _Grid({required this.columns, required this.children});

  final int columns;
  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, box) {
        const gap = 16.0;
        final width = (box.maxWidth - gap * (columns - 1)) / columns;
        return Wrap(
          spacing: gap,
          runSpacing: gap,
          children: [
            for (final child in children) SizedBox(width: width, child: child),
          ],
        );
      },
    );
  }
}

class _LevelCard extends StatelessWidget {
  const _LevelCard({
    required this.level,
    required this.selected,
    required this.onTap,
  });

  final Level level;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    final text = Theme.of(context).textTheme;
    return InkWell(
      borderRadius: BorderRadius.circular(16),
      onTap: onTap,
      child: Container(
        height: 126,
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: selected ? c.primaryTint : c.surface,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(
            color: selected ? c.primary : c.border,
            width: selected ? 1.4 : 1,
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    level.label,
                    style: text.titleMedium?.copyWith(
                      fontWeight: FontWeight.w500,
                      color: selected ? c.primaryStrong : c.text,
                    ),
                  ),
                ),
                _Radio(selected: selected),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              level.description,
              style: text.bodySmall?.copyWith(fontSize: 12.5),
            ),
            const Spacer(),
            Text(
              level.experience,
              style: TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.w600,
                color: selected ? c.primaryStrong : c.textFaint,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _Radio extends StatelessWidget {
  const _Radio({required this.selected});

  final bool selected;

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    return Container(
      width: 20,
      height: 20,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        border: Border.all(
          color: selected ? c.primary : c.border,
          width: selected ? 0 : 1.4,
        ),
        color: selected ? c.primary : c.surface,
      ),
      child: selected
          ? const Center(
              child: CircleAvatar(radius: 4, backgroundColor: Colors.white),
            )
          : null,
    );
  }
}

class _TopicCard extends StatelessWidget {
  const _TopicCard({
    required this.topic,
    required this.selected,
    required this.onTap,
  });

  final Topic topic;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    final text = Theme.of(context).textTheme;
    return InkWell(
      borderRadius: BorderRadius.circular(16),
      onTap: onTap,
      child: Container(
        height: 132,
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: selected ? c.primaryTint : c.surface,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(
            color: selected ? c.primary : c.border,
            width: selected ? 1.4 : 1,
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                IconTile(topic.icon, size: 32, active: selected),
                const Spacer(),
                Container(
                  width: 20,
                  height: 20,
                  decoration: BoxDecoration(
                    color: selected ? c.primary : c.surface,
                    borderRadius: BorderRadius.circular(5),
                    border: Border.all(
                      color: selected ? c.primary : c.border,
                      width: 1.4,
                    ),
                  ),
                  child: selected
                      ? const Icon(Icons.check, size: 14, color: Colors.white)
                      : null,
                ),
              ],
            ),
            const SizedBox(height: 10),
            Text(
              topic.title,
              style: text.titleSmall?.copyWith(
                fontWeight: FontWeight.w500,
                fontSize: 15,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              topic.description,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: text.bodySmall?.copyWith(fontSize: 12),
            ),
          ],
        ),
      ),
    );
  }
}

class _Summary extends StatelessWidget {
  const _Summary({required this.state, required this.onStart});

  final PracticeState state;
  final VoidCallback onStart;

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    final text = Theme.of(context).textTheme;
    Widget row(String label, String value) => Padding(
      padding: const EdgeInsets.symmetric(vertical: 12),
      child: Row(
        children: [
          Expanded(
            child: Text(label, style: text.bodySmall?.copyWith(fontSize: 13)),
          ),
          Text(value, style: text.bodyMedium?.copyWith(fontSize: 13.5)),
        ],
      ),
    );
    return AppCard(
      radius: 20,
      padding: const EdgeInsets.all(22),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Interview summary',
            style: text.titleLarge?.copyWith(fontWeight: FontWeight.w500),
          ),
          const SizedBox(height: 6),
          Text(
            'Your session adapts as you answer.',
            style: text.bodySmall?.copyWith(fontSize: 13),
          ),
          const SizedBox(height: 14),
          Divider(color: c.border),
          row('Track', state.track),
          Divider(color: c.border),
          row('Target level', state.level.label),
          Divider(color: c.border),
          row('Format', 'Theory + Coding'),
          Divider(color: c.border),
          row('Duration', '45 minutes'),
          Divider(color: c.border),
          row('Questions', '8 adaptive prompts'),
          const SizedBox(height: 16),
          Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: c.primaryTint,
              borderRadius: BorderRadius.circular(14),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Icon(
                      Icons.auto_awesome_outlined,
                      size: 14,
                      color: c.primaryStrong,
                    ),
                    const SizedBox(width: 8),
                    Text(
                      'Ready when you are',
                      style: TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w600,
                        color: c.primaryStrong,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Text(
                  'Camera and microphone are optional. You can switch modes during the session.',
                  style: TextStyle(
                    fontSize: 12,
                    color: c.primaryStrong,
                    height: 1.45,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 18),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton.icon(
              onPressed: state.canStart ? onStart : null,
              icon: const Icon(Icons.arrow_forward, size: 16),
              label: const Text('Start Interview'),
            ),
          ),
          const SizedBox(height: 14),
          Center(
            child: Text(
              'A session draft is saved automatically.',
              style: text.bodySmall?.copyWith(color: c.textFaint),
            ),
          ),
        ],
      ),
    );
  }
}
