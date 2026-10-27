// Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
// Proprietary and confidential. See LICENSE in the project root.

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/widgets/common.dart';
import '../../auth/presentation/auth_controller.dart';
import '../domain/interview_models.dart';
import 'code_editor.dart';
import 'dialogue_panel.dart';
import 'interview_controller.dart';
import 'test_console.dart';

class InterviewPage extends ConsumerStatefulWidget {
  const InterviewPage({super.key, required this.id});

  final String id;

  @override
  ConsumerState<InterviewPage> createState() => _InterviewPageState();
}

class _InterviewPageState extends ConsumerState<InterviewPage> {
  final _code = TextEditingController();
  final _notes = TextEditingController();
  bool _codeReady = false;
  int _tab = 0;
  int _pane = 0;

  @override
  void dispose() {
    _code.dispose();
    _notes.dispose();
    super.dispose();
  }

  String get _id => widget.id;

  Future<void> _end() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('End the interview?'),
        content: const Text(
          'Your answers and code will be assessed and the report will be generated.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Keep going'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('End interview'),
          ),
        ],
      ),
    );
    if (confirmed == true && mounted) context.go('/reports/IS-8921');
  }

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    final state = ref.watch(interviewControllerProvider(_id));
    final controller = ref.read(interviewControllerProvider(_id).notifier);
    final user = ref.watch(authControllerProvider).user;
    final session = state.session;

    if (session != null && !_codeReady) {
      _code.text = session.task.starterCode;
      _codeReady = true;
    }
    ref.listen(interviewControllerProvider(_id).select((s) => s.error), (
      _,
      error,
    ) {
      if (error != null) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text(error)));
        controller.dismissError();
      }
    });

    final wide = MediaQuery.sizeOf(context).width >= 1000;
    return Scaffold(
      backgroundColor: c.background,
      body: Column(
        children: [
          _TopBar(
            session: session,
            elapsed: state.elapsedSeconds,
            onSave: () => context.go('/dashboard'),
            onEnd: _end,
          ),
          Divider(height: 1, color: c.border),
          if (session == null)
            Expanded(
              child: Center(
                child: state.error == null
                    ? const CircularProgressIndicator()
                    : Text(state.error!),
              ),
            )
          else
            Expanded(
              child: wide
                  ? Row(
                      children: [
                        SizedBox(
                          width: 470,
                          child: _dialogue(
                            state,
                            controller,
                            user?.initials ?? 'YS',
                          ),
                        ),
                        VerticalDivider(width: 1, color: c.border),
                        Expanded(child: _workspace(session, state, controller)),
                      ],
                    )
                  : Column(
                      children: [
                        Padding(
                          padding: const EdgeInsets.all(10),
                          child: SegmentedButton<int>(
                            segments: const [
                              ButtonSegment(
                                value: 0,
                                label: Text('Dialogue'),
                                icon: Icon(Icons.chat_bubble_outline, size: 16),
                              ),
                              ButtonSegment(
                                value: 1,
                                label: Text('Workspace'),
                                icon: Icon(Icons.code, size: 16),
                              ),
                            ],
                            selected: {_pane},
                            onSelectionChanged: (s) =>
                                setState(() => _pane = s.first),
                          ),
                        ),
                        Expanded(
                          child: _pane == 0
                              ? _dialogue(
                                  state,
                                  controller,
                                  user?.initials ?? 'YS',
                                )
                              : _workspace(session, state, controller),
                        ),
                      ],
                    ),
            ),
        ],
      ),
    );
  }

  Widget _dialogue(
    InterviewState state,
    InterviewController controller,
    String initials,
  ) {
    return DialoguePanel(
      messages: state.messages,
      streaming: state.streaming,
      userInitials: initials,
      onSend: controller.send,
    );
  }

  Widget _workspace(
    InterviewSession session,
    InterviewState state,
    InterviewController controller,
  ) {
    final c = context.colors;
    final task = session.task;
    return Column(
      children: [
        Container(
          color: c.surface,
          padding: const EdgeInsets.symmetric(horizontal: 22),
          child: Row(
            children: [
              for (final (i, label) in ['Problem', 'Solution', 'Notes'].indexed)
                InkWell(
                  onTap: () => setState(() => _tab = i),
                  child: Container(
                    padding: const EdgeInsets.fromLTRB(2, 14, 2, 12),
                    margin: const EdgeInsets.only(right: 26),
                    decoration: BoxDecoration(
                      border: Border(
                        bottom: BorderSide(
                          color: _tab == i ? c.primary : Colors.transparent,
                          width: 2,
                        ),
                      ),
                    ),
                    child: Text(
                      label,
                      style: TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.w500,
                        color: _tab == i ? c.primaryStrong : c.textMuted,
                      ),
                    ),
                  ),
                ),
            ],
          ),
        ),
        Divider(height: 1, color: c.border),
        Container(
          color: c.surface,
          padding: const EdgeInsets.fromLTRB(22, 14, 22, 14),
          child: Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Flexible(
                          child: Text(
                            task.title,
                            style: Theme.of(context).textTheme.titleMedium
                                ?.copyWith(fontWeight: FontWeight.w500),
                          ),
                        ),
                        const SizedBox(width: 10),
                        Pill(task.difficulty, tone: PillTone.warning),
                      ],
                    ),
                    const SizedBox(height: 4),
                    Text(
                      task.constraints,
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                  ],
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 14,
                  vertical: 10,
                ),
                decoration: BoxDecoration(
                  color: c.surfaceMuted,
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Row(
                  children: [
                    Text(
                      task.language,
                      style: monoStyle(
                        context,
                        size: 12,
                        weight: FontWeight.w600,
                      ),
                    ),
                    const SizedBox(width: 6),
                    Icon(
                      Icons.keyboard_arrow_down,
                      size: 16,
                      color: c.textMuted,
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 12),
              ElevatedButton.icon(
                onPressed: state.running
                    ? null
                    : () => controller.run(_code.text),
                icon: const Icon(Icons.play_arrow_outlined, size: 18),
                label: const Text('Run Code'),
              ),
            ],
          ),
        ),
        Divider(height: 1, color: c.border),
        Expanded(
          child: switch (_tab) {
            0 => Column(
              children: [
                Expanded(child: CodeEditor(controller: _code)),
                TestConsole(report: state.report, running: state.running),
              ],
            ),
            1 => _Statement(task: task),
            _ => _NotesTab(controller: _notes),
          },
        ),
      ],
    );
  }
}

class _TopBar extends StatelessWidget {
  const _TopBar({
    required this.session,
    required this.elapsed,
    required this.onSave,
    required this.onEnd,
  });

  final InterviewSession? session;
  final int elapsed;
  final VoidCallback onSave;
  final VoidCallback onEnd;

  String get _clock {
    final m = (elapsed ~/ 60).toString().padLeft(2, '0');
    final s = (elapsed % 60).toString().padLeft(2, '0');
    return '$m:$s';
  }

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    final text = Theme.of(context).textTheme;
    return Container(
      color: c.surface,
      padding: const EdgeInsets.symmetric(horizontal: 22, vertical: 12),
      child: Row(
        children: [
          const BrandMark(size: 32),
          const SizedBox(width: 14),
          Flexible(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Flexible(
                      child: Text(
                        session?.title ?? 'Interview',
                        overflow: TextOverflow.ellipsis,
                        style: text.titleMedium?.copyWith(
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ),
                    const SizedBox(width: 12),
                    const Pill('LIVE', tone: PillTone.success, dot: true),
                  ],
                ),
                if (session != null)
                  Text(
                    'Adaptive interview · Question ${session!.question} of ${session!.totalQuestions}',
                    style: text.bodySmall?.copyWith(fontSize: 11.5),
                  ),
              ],
            ),
          ),
          const Spacer(),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            decoration: BoxDecoration(
              color: c.surfaceMuted,
              borderRadius: BorderRadius.circular(12),
            ),
            child: Row(
              children: [
                Icon(Icons.timer_outlined, size: 15, color: c.textMuted),
                const SizedBox(width: 10),
                Text(
                  _clock,
                  style: monoStyle(context, size: 14, weight: FontWeight.w600),
                ),
              ],
            ),
          ),
          const SizedBox(width: 10),
          OutlinedButton(
            onPressed: onSave,
            child: const Text('Save Draft & Exit'),
          ),
          const SizedBox(width: 10),
          ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: c.danger),
            onPressed: onEnd,
            child: const Text('End Interview'),
          ),
        ],
      ),
    );
  }
}

class _Statement extends StatelessWidget {
  const _Statement({required this.task});

  final CodingTask task;

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    return Container(
      color: c.surface,
      width: double.infinity,
      padding: const EdgeInsets.all(24),
      child: SingleChildScrollView(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              task.statement,
              style: const TextStyle(fontSize: 15, height: 1.6),
            ),
            const SizedBox(height: 20),
            Text(
              'Starting point',
              style: Theme.of(context).textTheme.titleSmall,
            ),
            const SizedBox(height: 10),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: c.codeBackground,
                borderRadius: BorderRadius.circular(12),
              ),
              child: Text(
                task.starterCode,
                style: monoStyle(context, size: 12.5, color: c.codeText),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _NotesTab extends StatelessWidget {
  const _NotesTab({required this.controller});

  final TextEditingController controller;

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    return Container(
      color: c.surface,
      padding: const EdgeInsets.all(24),
      child: TextField(
        controller: controller,
        expands: true,
        maxLines: null,
        minLines: null,
        textAlignVertical: TextAlignVertical.top,
        decoration: const InputDecoration(
          hintText:
              'Scratchpad: jot down edge cases and ideas. Notes stay private.',
        ),
      ),
    );
  }
}
