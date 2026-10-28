// Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
// Proprietary and confidential. See LICENSE in the project root.

import 'package:flutter/material.dart';

@immutable
class AppColors extends ThemeExtension<AppColors> {
  const AppColors({
    required this.background,
    required this.surface,
    required this.surfaceMuted,
    required this.border,
    required this.text,
    required this.textMuted,
    required this.textFaint,
    required this.primary,
    required this.primaryTint,
    required this.primaryStrong,
    required this.danger,
    required this.dangerTint,
    required this.warning,
    required this.warningTint,
    required this.codeBackground,
    required this.codeText,
  });

  final Color background;
  final Color surface;
  final Color surfaceMuted;
  final Color border;
  final Color text;
  final Color textMuted;
  final Color textFaint;
  final Color primary;
  final Color primaryTint;
  final Color primaryStrong;
  final Color danger;
  final Color dangerTint;
  final Color warning;
  final Color warningTint;
  final Color codeBackground;
  final Color codeText;

  static const light = AppColors(
    background: Color(0xFFF7F7F5),
    surface: Color(0xFFFFFFFF),
    surfaceMuted: Color(0xFFF1F1EE),
    border: Color(0xFFE8E8E3),
    text: Color(0xFF1A1A1A),
    textMuted: Color(0xFF6B6B66),
    textFaint: Color(0xFF9A9A94),
    primary: Color(0xFF10A37F),
    primaryTint: Color(0xFFE6F4EF),
    primaryStrong: Color(0xFF0B7A5F),
    danger: Color(0xFFC0392B),
    dangerTint: Color(0xFFFBEAE8),
    warning: Color(0xFFB7791F),
    warningTint: Color(0xFFFBF1DC),
    codeBackground: Color(0xFF202224),
    codeText: Color(0xFFD7D9DB),
  );

  static const dark = AppColors(
    background: Color(0xFF111312),
    surface: Color(0xFF1A1D1C),
    surfaceMuted: Color(0xFF232726),
    border: Color(0xFF2D3230),
    text: Color(0xFFF0F1EF),
    textMuted: Color(0xFFA2A7A4),
    textFaint: Color(0xFF727774),
    primary: Color(0xFF19B28D),
    primaryTint: Color(0xFF123229),
    primaryStrong: Color(0xFF5ED3B3),
    danger: Color(0xFFE0675B),
    dangerTint: Color(0xFF3A1C19),
    warning: Color(0xFFE0A84A),
    warningTint: Color(0xFF3A2F14),
    codeBackground: Color(0xFF0C0E0D),
    codeText: Color(0xFFD7D9DB),
  );

  @override
  AppColors copyWith() => this;

  @override
  AppColors lerp(ThemeExtension<AppColors>? other, double t) =>
      t < 0.5 ? this : (other as AppColors? ?? this);
}

extension AppColorsContext on BuildContext {
  AppColors get colors => Theme.of(this).extension<AppColors>()!;
}
