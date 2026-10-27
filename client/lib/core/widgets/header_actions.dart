// Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
// Proprietary and confidential. See LICENSE in the project root.

import 'package:flutter/material.dart';

import '../theme/app_colors.dart';

class BellButton extends StatelessWidget {
  const BellButton({super.key});

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    return Container(
      width: 36,
      height: 36,
      decoration: BoxDecoration(
        color: c.surface,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: c.border),
      ),
      child: Icon(Icons.notifications_none, size: 18, color: c.textMuted),
    );
  }
}

class HeaderSearch extends StatelessWidget {
  const HeaderSearch({
    super.key,
    required this.hint,
    this.onChanged,
    this.width = 190,
  });

  final String hint;
  final ValueChanged<String>? onChanged;
  final double width;

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    return SizedBox(
      width: width,
      height: 36,
      child: TextField(
        onChanged: onChanged,
        style: const TextStyle(fontSize: 13),
        decoration: InputDecoration(
          hintText: hint,
          isDense: true,
          contentPadding: EdgeInsets.zero,
          prefixIcon: Icon(Icons.search, size: 16, color: c.textMuted),
          prefixIconConstraints: const BoxConstraints(minWidth: 34),
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(10),
            borderSide: BorderSide(color: c.border),
          ),
          enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(10),
            borderSide: BorderSide(color: c.border),
          ),
        ),
      ),
    );
  }
}

class StepBadge extends StatelessWidget {
  const StepBadge(this.label, {super.key});

  final String label;

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
      decoration: BoxDecoration(
        color: c.surfaceMuted,
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(
        label,
        style: TextStyle(
          fontSize: 12,
          fontWeight: FontWeight.w600,
          color: c.textMuted,
        ),
      ),
    );
  }
}
