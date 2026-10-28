// Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
// Proprietary and confidential. See LICENSE in the project root.

import 'package:flutter/material.dart';

import '../theme/app_colors.dart';
import '../theme/app_theme.dart';

class BrandMark extends StatelessWidget {
  const BrandMark({super.key, this.size = 34});

  final double size;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: size,
      height: size,
      alignment: Alignment.center,
      decoration: BoxDecoration(
        color: const Color(0xFF111111),
        borderRadius: BorderRadius.circular(size * 0.26),
      ),
      child: Text(
        '<>',
        style: monoStyle(
          context,
          size: size * 0.34,
          color: Colors.white,
          weight: FontWeight.w700,
        ),
      ),
    );
  }
}

class AppCard extends StatelessWidget {
  const AppCard({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(20),
    this.color,
    this.borderColor,
    this.radius = 16,
  });

  final Widget child;
  final EdgeInsetsGeometry padding;
  final Color? color;
  final Color? borderColor;
  final double radius;

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    return Container(
      padding: padding,
      decoration: BoxDecoration(
        color: color ?? c.surface,
        borderRadius: BorderRadius.circular(radius),
        border: Border.all(color: borderColor ?? c.border),
      ),
      child: child,
    );
  }
}

enum PillTone { neutral, success, warning, danger }

class Pill extends StatelessWidget {
  const Pill(
    this.label, {
    super.key,
    this.tone = PillTone.neutral,
    this.dot = false,
    this.mono = false,
  });

  final String label;
  final PillTone tone;
  final bool dot;
  final bool mono;

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    final (bg, fg) = switch (tone) {
      PillTone.neutral => (c.surfaceMuted, c.textMuted),
      PillTone.success => (c.primaryTint, c.primaryStrong),
      PillTone.warning => (c.warningTint, c.warning),
      PillTone.danger => (c.dangerTint, c.danger),
    };
    final style = mono
        ? monoStyle(context, size: 11, color: fg, weight: FontWeight.w700)
        : TextStyle(fontSize: 12, color: fg, fontWeight: FontWeight.w600);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(999),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (dot) ...[
            Container(
              width: 6,
              height: 6,
              decoration: BoxDecoration(color: fg, shape: BoxShape.circle),
            ),
            const SizedBox(width: 6),
          ],
          Text(label, style: style),
        ],
      ),
    );
  }
}

class ScoreBar extends StatelessWidget {
  const ScoreBar({super.key, required this.value, this.height = 5});

  final double value;
  final double height;

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    return ClipRRect(
      borderRadius: BorderRadius.circular(height),
      child: Stack(
        children: [
          Container(height: height, color: c.surfaceMuted),
          FractionallySizedBox(
            widthFactor: value.clamp(0, 1).toDouble(),
            child: Container(height: height, color: c.primary),
          ),
        ],
      ),
    );
  }
}

class SectionHeader extends StatelessWidget {
  const SectionHeader(this.title, {super.key, this.trailing});

  final String title;
  final Widget? trailing;

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.center,
      children: [
        Expanded(
          child: Text(title, style: Theme.of(context).textTheme.titleLarge),
        ),
        ?trailing,
      ],
    );
  }
}

class Avatar extends StatelessWidget {
  const Avatar(this.initials, {super.key, this.size = 30});

  final String initials;
  final double size;

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    return Container(
      width: size,
      height: size,
      alignment: Alignment.center,
      decoration: BoxDecoration(color: c.surfaceMuted, shape: BoxShape.circle),
      child: Text(
        initials,
        style: TextStyle(
          fontSize: size * 0.36,
          fontWeight: FontWeight.w700,
          color: c.text,
        ),
      ),
    );
  }
}

class IconTile extends StatelessWidget {
  const IconTile(this.icon, {super.key, this.size = 36, this.active = false});

  final IconData icon;
  final double size;
  final bool active;

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        color: active ? c.surface : c.surfaceMuted,
        borderRadius: BorderRadius.circular(10),
      ),
      child: Icon(
        icon,
        size: size * 0.5,
        color: active ? c.primaryStrong : c.textMuted,
      ),
    );
  }
}
