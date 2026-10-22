import 'package:flutter/material.dart';

import 'groom_colors.dart';
import 'groom_type.dart';

ThemeData buildGroomTheme() {
  final base = ThemeData(
    useMaterial3: true,
    brightness: Brightness.dark,
    fontFamily: 'Outfit',
    scaffoldBackgroundColor: GroomColors.ink,
    splashFactory: InkRipple.splashFactory,
    colorScheme: const ColorScheme.dark(
      surface: GroomColors.ink,
      primary: GroomColors.champagne,
      onPrimary: GroomColors.ink,
      secondary: GroomColors.champagneDeep,
      onSurface: GroomColors.ivory,
      error: GroomColors.blush,
    ),
  );

  return base.copyWith(
    textTheme: base.textTheme.apply(
      fontFamily: 'Outfit',
      bodyColor: GroomColors.ivory,
      displayColor: GroomColors.ivory,
    ),
    textSelectionTheme: TextSelectionThemeData(
      cursorColor: GroomColors.champagne,
      selectionColor: GroomColors.champagne.withValues(alpha: 0.28),
      selectionHandleColor: GroomColors.champagne,
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: GroomColors.card,
      hintStyle: GroomType.ui(14, color: GroomColors.mute),
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(16),
        borderSide: const BorderSide(color: GroomColors.line),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(16),
        borderSide: const BorderSide(color: GroomColors.line),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(16),
        borderSide: const BorderSide(color: GroomColors.champagne),
      ),
    ),
    progressIndicatorTheme: const ProgressIndicatorThemeData(
      color: GroomColors.champagne,
    ),
  );
}
