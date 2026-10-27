// Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
// Proprietary and confidential. See LICENSE in the project root.

import 'package:flutter/material.dart';

import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_theme.dart';

class CodeEditor extends StatelessWidget {
  const CodeEditor({super.key, required this.controller});

  final TextEditingController controller;

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    final style = monoStyle(context, size: 13).copyWith(height: 1.7);
    return Container(
      color: c.surface,
      child: ListenableBuilder(
        listenable: controller,
        builder: (context, _) {
          final lines = '\n'.allMatches(controller.text).length + 1;
          return SingleChildScrollView(
            padding: const EdgeInsets.symmetric(vertical: 18),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                SizedBox(
                  width: 48,
                  child: Text(
                    [for (var i = 1; i <= lines; i++) '$i'].join('\n'),
                    textAlign: TextAlign.right,
                    style: style.copyWith(color: c.textFaint),
                  ),
                ),
                const SizedBox(width: 18),
                Expanded(
                  child: TextField(
                    controller: controller,
                    maxLines: null,
                    style: style,
                    cursorColor: c.primary,
                    keyboardType: TextInputType.multiline,
                    decoration: const InputDecoration(
                      isDense: true,
                      filled: false,
                      border: InputBorder.none,
                      enabledBorder: InputBorder.none,
                      focusedBorder: InputBorder.none,
                      contentPadding: EdgeInsets.zero,
                    ),
                  ),
                ),
              ],
            ),
          );
        },
      ),
    );
  }
}
