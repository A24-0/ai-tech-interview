// Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
// Proprietary and confidential. See LICENSE in the project root.

import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import 'app_colors.dart';

const monoFamily = 'Menlo';
const monoFallback = ['SF Mono', 'Consolas', 'Courier New', 'monospace'];

class AppFonts {
  static bool enabled = false;
}

TextStyle monoStyle(
  BuildContext context, {
  double size = 12,
  Color? color,
  FontWeight? weight,
}) {
  final resolved = color ?? context.colors.text;
  if (AppFonts.enabled) {
    return GoogleFonts.jetBrainsMono(
      fontSize: size,
      color: resolved,
      fontWeight: weight,
      height: 1.5,
    );
  }
  return TextStyle(
    fontFamily: monoFamily,
    fontFamilyFallback: monoFallback,
    fontSize: size,
    color: resolved,
    fontWeight: weight,
    height: 1.5,
  );
}

ThemeData buildTheme(AppColors c, Brightness brightness) {
  final scheme =
      ColorScheme.fromSeed(
        seedColor: c.primary,
        brightness: brightness,
      ).copyWith(
        primary: c.primary,
        onPrimary: Colors.white,
        surface: c.surface,
        onSurface: c.text,
        error: c.danger,
        outline: c.border,
      );
  final base = ThemeData(
    brightness: brightness,
    useMaterial3: true,
    colorScheme: scheme,
  );
  final fontBase = AppFonts.enabled
      ? GoogleFonts.interTextTheme(base.textTheme)
      : base.textTheme;
  final text = fontBase.apply(bodyColor: c.text, displayColor: c.text);
  return base.copyWith(
    scaffoldBackgroundColor: c.background,
    canvasColor: c.surface,
    dividerColor: c.border,
    extensions: [c],
    textTheme: text.copyWith(
      displaySmall: text.displaySmall?.copyWith(
        fontSize: 40,
        fontWeight: FontWeight.w600,
        height: 1.1,
        letterSpacing: -1,
      ),
      headlineMedium: text.headlineMedium?.copyWith(
        fontSize: 32,
        fontWeight: FontWeight.w600,
        letterSpacing: -0.6,
      ),
      headlineSmall: text.headlineSmall?.copyWith(
        fontSize: 26,
        fontWeight: FontWeight.w600,
        letterSpacing: -0.4,
      ),
      titleLarge: text.titleLarge?.copyWith(
        fontSize: 20,
        fontWeight: FontWeight.w600,
      ),
      titleMedium: text.titleMedium?.copyWith(
        fontSize: 16,
        fontWeight: FontWeight.w600,
      ),
      titleSmall: text.titleSmall?.copyWith(
        fontSize: 14,
        fontWeight: FontWeight.w600,
      ),
      bodyLarge: text.bodyLarge?.copyWith(fontSize: 15, height: 1.5),
      bodyMedium: text.bodyMedium?.copyWith(fontSize: 14, height: 1.5),
      bodySmall: text.bodySmall?.copyWith(
        fontSize: 12,
        color: c.textMuted,
        height: 1.4,
      ),
      labelLarge: text.labelLarge?.copyWith(
        fontSize: 14,
        fontWeight: FontWeight.w600,
      ),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: c.surface,
      contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
      hintStyle: TextStyle(color: c.textFaint),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(10),
        borderSide: BorderSide(color: c.border),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(10),
        borderSide: BorderSide(color: c.border),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(10),
        borderSide: BorderSide(color: c.primary, width: 1.4),
      ),
      errorBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(10),
        borderSide: BorderSide(color: c.danger),
      ),
      focusedErrorBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(10),
        borderSide: BorderSide(color: c.danger, width: 1.4),
      ),
    ),
    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        backgroundColor: c.primary,
        foregroundColor: Colors.white,
        elevation: 0,
        minimumSize: const Size(0, 46),
        padding: const EdgeInsets.symmetric(horizontal: 18),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
        textStyle: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600),
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        foregroundColor: c.text,
        minimumSize: const Size(0, 44),
        padding: const EdgeInsets.symmetric(horizontal: 16),
        side: BorderSide(color: c.border),
        backgroundColor: c.surface,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
        textStyle: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600),
      ),
    ),
    textButtonTheme: TextButtonThemeData(
      style: TextButton.styleFrom(
        foregroundColor: c.primaryStrong,
        textStyle: const TextStyle(fontWeight: FontWeight.w600),
      ),
    ),
    dividerTheme: DividerThemeData(color: c.border, thickness: 1, space: 1),
  );
}

ThemeData get lightTheme => buildTheme(AppColors.light, Brightness.light);
ThemeData get darkTheme => buildTheme(AppColors.dark, Brightness.dark);
