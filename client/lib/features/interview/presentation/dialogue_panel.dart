// Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
// Proprietary and confidential. See LICENSE in the project root.

import 'package:flutter/material.dart';

import '../../../core/theme/app_colors.dart';
import '../../../core/widgets/common.dart';
import '../domain/interview_models.dart';

enum DialogueMode { text, video, audio }

class DialoguePanel extends StatefulWidget {
  const DialoguePanel({
    super.key,
    required this.messages,
    required this.streaming,
    required this.userInitials,
    required this.onSend,
  });

  final List<DialogueMessage> messages;
  final String? streaming;
  final String userInitials;
  final ValueChanged<String> onSend;

  @override
  State<DialoguePanel> createState() => _DialoguePanelState();
}

class _DialoguePanelState extends State<DialoguePanel> {
  final _input = TextEditingController();
  final _scroll = ScrollController();
  DialogueMode _mode = DialogueMode.text;

  @override
  void dispose() {
    _input.dispose();
    _scroll.dispose();
    super.dispose();
  }

  @override
  void didUpdateWidget(DialoguePanel old) {
    super.didUpdateWidget(old);
    if (old.messages.length != widget.messages.length ||
        old.streaming != widget.streaming) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (_scroll.hasClients) {
          _scroll.jumpTo(_scroll.position.maxScrollExtent);
        }
      });
    }
  }

  void _submit() {
    final text = _input.text;
    if (text.trim().isEmpty || widget.streaming != null) return;
    widget.onSend(text);
    _input.clear();
  }

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    final text = Theme.of(context).textTheme;
    return Container(
      color: c.surface,
      child: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 10, 18, 10),
            child: Row(
              children: [
                Expanded(
                  child: Text(
                    'Interview dialogue',
                    style: text.titleSmall?.copyWith(
                      fontWeight: FontWeight.w500,
                      fontSize: 15,
                    ),
                  ),
                ),
                _ModeSwitch(
                  mode: _mode,
                  onChanged: (m) => setState(() => _mode = m),
                ),
              ],
            ),
          ),
          Divider(color: c.border),
          Expanded(
            child: ListView(
              controller: _scroll,
              padding: const EdgeInsets.fromLTRB(20, 22, 20, 12),
              children: [
                for (final m in widget.messages)
                  _Bubble(message: m, initials: widget.userInitials),
                if (widget.streaming != null)
                  _Bubble(
                    message: DialogueMessage(
                      role: MessageRole.interviewer,
                      text: widget.streaming!.isEmpty ? '…' : widget.streaming!,
                      time: '',
                    ),
                    initials: widget.userInitials,
                  ),
                Align(
                  alignment: Alignment.centerLeft,
                  child: Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 12,
                      vertical: 8,
                    ),
                    decoration: BoxDecoration(
                      color: c.surfaceMuted,
                      borderRadius: BorderRadius.circular(999),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(
                          Icons.auto_awesome_outlined,
                          size: 13,
                          color: c.textMuted,
                        ),
                        const SizedBox(width: 8),
                        Text(
                          'The interviewer is following your code',
                          style: TextStyle(fontSize: 12, color: c.textMuted),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 10),
            child: Column(
              children: [
                Container(
                  padding: const EdgeInsets.fromLTRB(14, 4, 10, 10),
                  decoration: BoxDecoration(
                    color: c.surface,
                    borderRadius: BorderRadius.circular(18),
                    border: Border.all(color: c.border),
                  ),
                  child: Column(
                    children: [
                      TextField(
                        controller: _input,
                        minLines: 2,
                        maxLines: 5,
                        onSubmitted: (_) => _submit(),
                        style: const TextStyle(fontSize: 14),
                        decoration: InputDecoration(
                          hintText: 'Explain your reasoning...',
                          filled: false,
                          border: InputBorder.none,
                          enabledBorder: InputBorder.none,
                          focusedBorder: InputBorder.none,
                          contentPadding: const EdgeInsets.fromLTRB(
                            0,
                            12,
                            0,
                            6,
                          ),
                          hintStyle: TextStyle(color: c.textFaint),
                        ),
                      ),
                      Row(
                        children: [
                          Icon(Icons.add, size: 18, color: c.textMuted),
                          const SizedBox(width: 12),
                          Icon(Icons.attach_file, size: 18, color: c.textMuted),
                          const Spacer(),
                          InkWell(
                            customBorder: const CircleBorder(),
                            onTap: _submit,
                            child: Container(
                              width: 32,
                              height: 32,
                              decoration: const BoxDecoration(
                                color: Color(0xFF111111),
                                shape: BoxShape.circle,
                              ),
                              child: const Icon(
                                Icons.arrow_upward,
                                size: 16,
                                color: Colors.white,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  'Your explanation is included in the final assessment.',
                  style: text.bodySmall?.copyWith(
                    fontSize: 11,
                    color: c.textFaint,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _ModeSwitch extends StatelessWidget {
  const _ModeSwitch({required this.mode, required this.onChanged});

  final DialogueMode mode;
  final ValueChanged<DialogueMode> onChanged;

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    Widget item(DialogueMode value, IconData icon, String label) {
      final selected = mode == value;
      return GestureDetector(
        onTap: () => onChanged(value),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
          decoration: BoxDecoration(
            color: selected ? c.surface : Colors.transparent,
            borderRadius: BorderRadius.circular(8),
            border: selected ? Border.all(color: c.border) : null,
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(icon, size: 14, color: selected ? c.text : c.textMuted),
              const SizedBox(width: 6),
              Text(
                label,
                style: TextStyle(
                  fontSize: 12.5,
                  fontWeight: FontWeight.w500,
                  color: selected ? c.text : c.textMuted,
                ),
              ),
            ],
          ),
        ),
      );
    }

    return Container(
      padding: const EdgeInsets.all(3),
      decoration: BoxDecoration(
        color: c.surfaceMuted,
        borderRadius: BorderRadius.circular(10),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          item(DialogueMode.text, Icons.chat_bubble_outline, 'Text'),
          item(DialogueMode.video, Icons.videocam_outlined, 'Video'),
          item(DialogueMode.audio, Icons.mic_none, 'Audio'),
        ],
      ),
    );
  }
}

class _Bubble extends StatelessWidget {
  const _Bubble({required this.message, required this.initials});

  final DialogueMessage message;
  final String initials;

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    final isAi = message.role == MessageRole.interviewer;
    return Padding(
      padding: const EdgeInsets.only(bottom: 22),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (isAi)
            Container(
              width: 30,
              height: 30,
              decoration: const BoxDecoration(
                color: Color(0xFF111111),
                shape: BoxShape.circle,
              ),
              child: const Icon(
                Icons.auto_awesome,
                size: 14,
                color: Colors.white,
              ),
            )
          else
            Avatar(initials),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        isAi ? 'AI interviewer' : 'You',
                        style: TextStyle(fontSize: 12, color: c.textMuted),
                      ),
                    ),
                    Text(
                      message.time,
                      style: TextStyle(fontSize: 11, color: c.textFaint),
                    ),
                  ],
                ),
                const SizedBox(height: 6),
                Text(
                  message.text,
                  style: const TextStyle(fontSize: 14.5, height: 1.55),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
