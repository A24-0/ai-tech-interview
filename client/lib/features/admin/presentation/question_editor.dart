// Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
// Proprietary and confidential. See LICENSE in the project root.

import 'package:flutter/material.dart';

import '../../../core/domain/level.dart';
import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/widgets/common.dart';
import '../../practice/domain/topic.dart';
import '../domain/question_models.dart';

class QuestionEditor extends StatefulWidget {
  const QuestionEditor({
    super.key,
    required this.record,
    required this.onClose,
    required this.onSave,
  });

  final QuestionRecord record;
  final VoidCallback onClose;
  final ValueChanged<QuestionRecord> onSave;

  @override
  State<QuestionEditor> createState() => _QuestionEditorState();
}

class _QuestionEditorState extends State<QuestionEditor> {
  late final _title = TextEditingController(text: widget.record.title);
  late final _starter = TextEditingController(text: widget.record.starterCode);
  late final _tests = TextEditingController(text: widget.record.tests);
  late String _topic = widget.record.topic;
  late Level _level = widget.record.level;
  late int _seconds = widget.record.timeLimitSeconds;
  late int _memory = widget.record.memoryLimitMb;

  @override
  void dispose() {
    _title.dispose();
    _starter.dispose();
    _tests.dispose();
    super.dispose();
  }

  int get _caseCount => '"expected"'.allMatches(_tests.text).length;

  void _save() {
    widget.onSave(
      widget.record.copyWith(
        title: _title.text.trim().isEmpty
            ? widget.record.title
            : _title.text.trim(),
        topic: _topic,
        level: _level,
        timeLimitSeconds: _seconds,
        memoryLimitMb: _memory,
        starterCode: _starter.text,
        tests: _tests.text,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    final text = Theme.of(context).textTheme;
    final coding = widget.record.type == QuestionType.coding;
    return Container(
      color: c.surface,
      child: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(22, 16, 14, 14),
            child: Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Edit ${coding ? 'Coding Task' : 'Question'} #${widget.record.id}',
                        style: text.titleLarge?.copyWith(
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        'Last updated ${widget.record.updated.replaceFirst('Updated ', '')} by Admin Sigma',
                        style: text.bodySmall,
                      ),
                    ],
                  ),
                ),
                IconButton(
                  onPressed: widget.onClose,
                  icon: const Icon(Icons.close, size: 18),
                ),
              ],
            ),
          ),
          Divider(color: c.border),
          Expanded(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(22),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _label(context, 'Task title'),
                  TextField(controller: _title),
                  const SizedBox(height: 18),
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Expanded(
                        child: _field(
                          context,
                          'TOPIC',
                          DropdownButtonFormField<String>(
                            initialValue: _topic,
                            isExpanded: true,
                            items: [
                              for (final t in practiceTopics)
                                DropdownMenuItem(
                                  value: t.title,
                                  child: Text(t.title),
                                ),
                            ],
                            onChanged: (v) =>
                                setState(() => _topic = v ?? _topic),
                          ),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: _field(
                          context,
                          'LEVEL',
                          DropdownButtonFormField<Level>(
                            initialValue: _level,
                            isExpanded: true,
                            items: [
                              for (final l in Level.values)
                                DropdownMenuItem(
                                  value: l,
                                  child: Text(l.label),
                                ),
                            ],
                            onChanged: (v) =>
                                setState(() => _level = v ?? _level),
                          ),
                        ),
                      ),
                    ],
                  ),
                  if (coding) ...[
                    const SizedBox(height: 18),
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Expanded(
                          child: _field(
                            context,
                            'Time limit',
                            DropdownButtonFormField<int>(
                              initialValue: _seconds,
                              isExpanded: true,
                              items: [
                                for (final s in {1, 2, 3, 5})
                                  DropdownMenuItem(
                                    value: s,
                                    child: Text('$s seconds'),
                                  ),
                              ],
                              onChanged: (v) =>
                                  setState(() => _seconds = v ?? _seconds),
                            ),
                            strong: true,
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: _field(
                            context,
                            'Memory limit',
                            DropdownButtonFormField<int>(
                              initialValue: _memory,
                              isExpanded: true,
                              items: [
                                for (final m in {64, 128, 256})
                                  DropdownMenuItem(
                                    value: m,
                                    child: Text('$m MB'),
                                  ),
                              ],
                              onChanged: (v) =>
                                  setState(() => _memory = v ?? _memory),
                            ),
                            strong: true,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 22),
                    Row(
                      children: [
                        Expanded(
                          child: Text('Starter code', style: text.titleSmall),
                        ),
                        Text(
                          'Python 3.12',
                          style: monoStyle(
                            context,
                            size: 11,
                            color: c.textMuted,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Container(
                      padding: const EdgeInsets.all(14),
                      decoration: BoxDecoration(
                        color: c.codeBackground,
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: TextField(
                        controller: _starter,
                        maxLines: null,
                        minLines: 6,
                        style: monoStyle(context, size: 12, color: c.codeText),
                        decoration: const InputDecoration(
                          filled: false,
                          border: InputBorder.none,
                          enabledBorder: InputBorder.none,
                          focusedBorder: InputBorder.none,
                          contentPadding: EdgeInsets.zero,
                        ),
                      ),
                    ),
                    const SizedBox(height: 22),
                    Row(
                      children: [
                        Expanded(
                          child: Text(
                            'JSON unit tests',
                            style: text.titleSmall,
                          ),
                        ),
                        ListenableBuilder(
                          listenable: _tests,
                          builder: (context, _) => Pill('$_caseCount cases'),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Container(
                      padding: const EdgeInsets.all(14),
                      decoration: BoxDecoration(
                        color: c.surfaceMuted,
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(color: c.border),
                      ),
                      child: TextField(
                        controller: _tests,
                        maxLines: null,
                        minLines: 8,
                        style: monoStyle(context, size: 11.5),
                        decoration: const InputDecoration(
                          filled: false,
                          border: InputBorder.none,
                          enabledBorder: InputBorder.none,
                          focusedBorder: InputBorder.none,
                          contentPadding: EdgeInsets.zero,
                        ),
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ),
          Divider(color: c.border),
          Padding(
            padding: const EdgeInsets.all(18),
            child: Row(
              children: [
                Expanded(
                  child: OutlinedButton(
                    onPressed: widget.onClose,
                    child: const Text('Cancel'),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: _save,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFF111111),
                    ),
                    icon: const Icon(Icons.save_outlined, size: 16),
                    label: const Text('Save'),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _label(BuildContext context, String label) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Text(label, style: Theme.of(context).textTheme.titleSmall),
    );
  }

  Widget _field(
    BuildContext context,
    String label,
    Widget child, {
    bool strong = false,
  }) {
    final c = context.colors;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: strong
              ? Theme.of(context).textTheme.titleSmall
              : TextStyle(fontSize: 11, letterSpacing: 0.6, color: c.textMuted),
        ),
        const SizedBox(height: 8),
        child,
      ],
    );
  }
}
