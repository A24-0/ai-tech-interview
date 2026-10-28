// Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
// Proprietary and confidential. See LICENSE in the project root.

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/domain/level.dart';
import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/widgets/common.dart';
import '../../practice/domain/topic.dart';
import '../../shell/presentation/shells.dart';
import '../domain/question_models.dart';
import 'question_bank_controller.dart';
import 'question_editor.dart';

class QuestionBankPage extends ConsumerWidget {
  const QuestionBankPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(questionBankProvider);
    final controller = ref.read(questionBankProvider.notifier);
    final c = context.colors;
    final selected = state.selected;
    final wide = MediaQuery.sizeOf(context).width >= 1180;
    final table = _TablePane(state: state, controller: controller);
    final editor = selected == null
        ? null
        : QuestionEditor(
            key: ValueKey(selected.id),
            record: selected,
            onClose: () => controller.select(null),
            onSave: (r) {
              controller.save(r);
              controller.select(null);
            },
          );
    return AdminScaffold(
      title: 'Question bank',
      subtitle: 'Manage interview content and evaluation rules',
      actions: [
        const Pill('ADMIN', mono: false),
        ElevatedButton.icon(
          onPressed: controller.create,
          icon: const Icon(Icons.add, size: 18),
          label: const Text('Create Question'),
        ),
      ],
      child: wide
          ? Row(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Expanded(child: table),
                if (editor != null) ...[
                  VerticalDivider(width: 1, color: c.border),
                  SizedBox(width: 444, child: editor),
                ],
              ],
            )
          : (editor ?? table),
    );
  }
}

class _TablePane extends StatelessWidget {
  const _TablePane({required this.state, required this.controller});

  final QuestionBankState state;
  final QuestionBankController controller;

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    final text = Theme.of(context).textTheme;
    final rows = state.visible;
    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(28, 28, 28, 28),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Questions & coding tasks',
            style: text.headlineMedium?.copyWith(fontSize: 30),
          ),
          const SizedBox(height: 8),
          Text(
            '${QuestionBankState.totalRecords} records · ${state.published} published · ${state.drafts} drafts',
            style: text.bodyMedium?.copyWith(color: c.textMuted),
          ),
          const SizedBox(height: 22),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            crossAxisAlignment: WrapCrossAlignment.end,
            children: [
              _Labeled(
                label: 'SEARCH',
                width: 320,
                child: TextFormField(
                  initialValue: state.query,
                  onChanged: controller.setQuery,
                  style: const TextStyle(fontSize: 14),
                  decoration: InputDecoration(
                    isDense: true,
                    contentPadding: const EdgeInsets.symmetric(vertical: 13),
                    prefixIcon: Icon(
                      Icons.search,
                      size: 17,
                      color: c.textMuted,
                    ),
                    suffixIcon: state.query.isEmpty
                        ? null
                        : IconButton(
                            icon: Icon(
                              Icons.close,
                              size: 15,
                              color: c.textMuted,
                            ),
                            onPressed: () => controller.setQuery(''),
                          ),
                  ),
                ),
              ),
              _Labeled(
                label: 'TYPE',
                width: 150,
                child: _Select<QuestionType>(
                  hint: 'All types',
                  value: state.type,
                  options: {
                    for (final t in QuestionType.values)
                      t: t == QuestionType.theory ? 'Theory' : 'Coding',
                  },
                  onChanged: controller.setType,
                ),
              ),
              _Labeled(
                label: 'TOPIC',
                width: 170,
                child: _Select<String>(
                  hint: 'All topics',
                  value: state.topic,
                  options: {for (final t in practiceTopics) t.title: t.title},
                  onChanged: controller.setTopic,
                ),
              ),
              _Labeled(
                label: 'LEVEL',
                width: 150,
                child: _Select<Level>(
                  hint: 'All levels',
                  value: state.level,
                  options: {for (final l in Level.values) l: l.label},
                  onChanged: controller.setLevel,
                ),
              ),
            ],
          ),
          const SizedBox(height: 18),
          AppCard(
            padding: EdgeInsets.zero,
            radius: 14,
            child: LayoutBuilder(
              builder: (context, box) => SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: SizedBox(
                  width: box.maxWidth < 700 ? 700 : box.maxWidth,
                  child: Column(
                    children: [
                      _head(context),
                      for (final r in rows) ...[
                        Divider(color: c.border),
                        _Row(
                          record: r,
                          selected: r.id == state.selectedId,
                          onTap: () => controller.select(r.id),
                        ),
                      ],
                      if (rows.isEmpty)
                        Padding(
                          padding: const EdgeInsets.all(32),
                          child: Text(
                            'No questions match the current filters.',
                            style: text.bodySmall,
                          ),
                        ),
                    ],
                  ),
                ),
              ),
            ),
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(
                child: Text(
                  'Showing ${rows.isEmpty ? 0 : 1}–${rows.length} of ${QuestionBankState.totalRecords}',
                  style: text.bodySmall?.copyWith(fontSize: 13),
                ),
              ),
              OutlinedButton(onPressed: null, child: const Text('Previous')),
              const SizedBox(width: 8),
              Container(
                width: 36,
                height: 36,
                alignment: Alignment.center,
                decoration: BoxDecoration(
                  color: const Color(0xFF111111),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: const Text(
                  '1',
                  style: TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
              const SizedBox(width: 8),
              OutlinedButton(onPressed: null, child: const Text('Next')),
            ],
          ),
        ],
      ),
    );
  }

  Widget _head(BuildContext context) {
    final c = context.colors;
    final style = TextStyle(
      fontSize: 11,
      letterSpacing: 0.6,
      color: c.textMuted,
    );
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 12),
      child: Row(
        children: [
          SizedBox(width: 60, child: Text('ID', style: style)),
          SizedBox(width: 90, child: Text('TYPE', style: style)),
          Expanded(flex: 5, child: Text('QUESTION / TASK', style: style)),
          Expanded(flex: 3, child: Text('TOPIC', style: style)),
          Expanded(flex: 2, child: Text('LEVEL', style: style)),
          SizedBox(width: 120, child: Text('STATUS', style: style)),
          const SizedBox(width: 28),
        ],
      ),
    );
  }
}

class _Row extends StatelessWidget {
  const _Row({
    required this.record,
    required this.selected,
    required this.onTap,
  });

  final QuestionRecord record;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    final text = Theme.of(context).textTheme;
    final coding = record.type == QuestionType.coding;
    final published = record.status == QuestionStatus.published;
    return InkWell(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 16),
        decoration: BoxDecoration(
          color: selected ? c.primaryTint : null,
          border: Border(
            left: BorderSide(
              color: selected ? c.primary : Colors.transparent,
              width: 2,
            ),
          ),
        ),
        child: Row(
          children: [
            SizedBox(
              width: 60,
              child: Text(
                '#${record.id}',
                style: monoStyle(context, size: 12, color: c.textMuted),
              ),
            ),
            SizedBox(
              width: 90,
              child: Align(
                alignment: Alignment.centerLeft,
                child: Pill(
                  coding ? 'Coding' : 'Theory',
                  tone: coding ? PillTone.success : PillTone.neutral,
                ),
              ),
            ),
            Expanded(
              flex: 5,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    record.title,
                    style: text.bodyMedium?.copyWith(
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    record.updated,
                    style: text.bodySmall?.copyWith(
                      fontSize: 11.5,
                      color: c.textFaint,
                    ),
                  ),
                ],
              ),
            ),
            Expanded(
              flex: 3,
              child: Text(
                record.topic,
                style: text.bodySmall?.copyWith(fontSize: 13),
              ),
            ),
            Expanded(
              flex: 2,
              child: Text(
                record.level.label,
                style: text.bodySmall?.copyWith(fontSize: 13),
              ),
            ),
            SizedBox(
              width: 120,
              child: Align(
                alignment: Alignment.centerLeft,
                child: Pill(
                  published ? 'Published' : 'Draft',
                  tone: published ? PillTone.success : PillTone.warning,
                ),
              ),
            ),
            SizedBox(
              width: 28,
              child: Icon(Icons.more_vert, size: 16, color: c.textMuted),
            ),
          ],
        ),
      ),
    );
  }
}

class _Labeled extends StatelessWidget {
  const _Labeled({
    required this.label,
    required this.width,
    required this.child,
  });

  final String label;
  final double width;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    return SizedBox(
      width: width,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: TextStyle(
              fontSize: 11,
              letterSpacing: 0.6,
              color: c.textMuted,
            ),
          ),
          const SizedBox(height: 6),
          child,
        ],
      ),
    );
  }
}

class _Select<T> extends StatelessWidget {
  const _Select({
    required this.hint,
    required this.value,
    required this.options,
    required this.onChanged,
  });

  final String hint;
  final T? value;
  final Map<T, String> options;
  final ValueChanged<T?> onChanged;

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    return Container(
      height: 44,
      padding: const EdgeInsets.symmetric(horizontal: 12),
      decoration: BoxDecoration(
        color: c.surface,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: c.border),
      ),
      child: DropdownButtonHideUnderline(
        child: DropdownButton<T?>(
          value: value,
          isExpanded: true,
          icon: Icon(Icons.keyboard_arrow_down, size: 18, color: c.textMuted),
          style: TextStyle(fontSize: 13.5, color: c.text),
          dropdownColor: c.surface,
          items: [
            DropdownMenuItem<T?>(value: null, child: Text(hint)),
            for (final e in options.entries)
              DropdownMenuItem<T?>(value: e.key, child: Text(e.value)),
          ],
          onChanged: onChanged,
        ),
      ),
    );
  }
}
