import 'package:flutter/material.dart';

class AppTheme {
  static const primaryDarkBlue = Color(0xFF0A2540);
  static const backgroundLightGrey = Color(0xFFF5F5F7);
  static const textPrimary = Color(0xFF1D1D1F);
  static const textSecondary = Color(0xFF86868B);
  static const accent = Color(0xFF0066CC);
  static const card = Color(0xFFFFFFFF);
  static const line = Color(0xFFE6E6EA);

  static ThemeData light() {
    final scheme = ColorScheme.fromSeed(
      seedColor: accent,
      brightness: Brightness.light,
      surface: backgroundLightGrey,
    );
    return ThemeData(
      useMaterial3: true,
      colorScheme: scheme.copyWith(
        primary: primaryDarkBlue,
        onPrimary: Colors.white,
        secondary: accent,
        onSecondary: Colors.white,
        surface: backgroundLightGrey,
        error: const Color(0xFFB42318),
      ),
      scaffoldBackgroundColor: backgroundLightGrey,
      splashColor: accent.withValues(alpha: 0.08),
      highlightColor: accent.withValues(alpha: 0.05),
      appBarTheme: const AppBarTheme(
        backgroundColor: backgroundLightGrey,
        foregroundColor: textPrimary,
        elevation: 0,
        scrolledUnderElevation: 0,
        centerTitle: false,
      ),
      cardTheme: CardThemeData(
        color: card,
        elevation: 0,
        margin: EdgeInsets.zero,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(24),
        ),
      ),
      dividerColor: line,
      chipTheme: ChipThemeData(
        backgroundColor: card,
        selectedColor: const Color(0xFFE7F1FB),
        disabledColor: backgroundLightGrey,
        labelStyle: const TextStyle(
          color: textPrimary,
          fontWeight: FontWeight.w600,
        ),
        secondaryLabelStyle: const TextStyle(
          color: accent,
          fontWeight: FontWeight.w600,
        ),
        side: const BorderSide(color: line),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(999),
        ),
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: backgroundLightGrey,
        labelStyle: const TextStyle(color: textSecondary),
        floatingLabelStyle: const TextStyle(color: accent),
        contentPadding: const EdgeInsets.symmetric(
          horizontal: 16,
          vertical: 16,
        ),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: const BorderSide(color: line),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: const BorderSide(color: line),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: const BorderSide(color: accent, width: 1.6),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: const BorderSide(color: Color(0xFFB42318)),
        ),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: accent,
          foregroundColor: Colors.white,
          disabledBackgroundColor: accent.withValues(alpha: 0.35),
          minimumSize: const Size.fromHeight(56),
          textStyle: const TextStyle(
            fontSize: 16,
            fontWeight: FontWeight.w600,
            letterSpacing: -0.2,
          ),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(18),
          ),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: accent,
          side: const BorderSide(color: Color(0xFFD0E4F7)),
          backgroundColor: const Color(0xFFF4F9FD),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(999),
          ),
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        ),
      ),
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(foregroundColor: accent),
      ),
      sliderTheme: const SliderThemeData(
        activeTrackColor: accent,
        thumbColor: accent,
        inactiveTrackColor: Color(0xFFD8D8DE),
      ),
      navigationBarTheme: NavigationBarThemeData(
        backgroundColor: card,
        elevation: 0,
        height: 72,
        indicatorColor: const Color(0xFFE7F1FB),
        labelTextStyle: WidgetStateProperty.resolveWith((states) {
          final selected = states.contains(WidgetState.selected);
          return TextStyle(
            fontSize: 12,
            fontWeight: FontWeight.w600,
            color: selected ? accent : textSecondary,
          );
        }),
        iconTheme: WidgetStateProperty.resolveWith((states) {
          final selected = states.contains(WidgetState.selected);
          return IconThemeData(color: selected ? accent : textSecondary);
        }),
      ),
      navigationRailTheme: const NavigationRailThemeData(
        backgroundColor: card,
        indicatorColor: Color(0xFFE7F1FB),
        selectedIconTheme: IconThemeData(color: accent),
        unselectedIconTheme: IconThemeData(color: textSecondary),
        selectedLabelTextStyle: TextStyle(
          color: accent,
          fontWeight: FontWeight.w600,
        ),
        unselectedLabelTextStyle: TextStyle(color: textSecondary),
      ),
      textTheme: const TextTheme(
        headlineSmall: TextStyle(
          fontSize: 30,
          fontWeight: FontWeight.w700,
          letterSpacing: -0.8,
          height: 1.1,
          color: textPrimary,
        ),
        titleLarge: TextStyle(
          fontSize: 20,
          fontWeight: FontWeight.w700,
          letterSpacing: -0.4,
          color: textPrimary,
        ),
        titleMedium: TextStyle(
          fontSize: 17,
          fontWeight: FontWeight.w600,
          letterSpacing: -0.2,
          color: textPrimary,
        ),
        bodyMedium: TextStyle(
          fontSize: 15,
          height: 1.4,
          color: textPrimary,
        ),
        bodySmall: TextStyle(
          fontSize: 13,
          color: textSecondary,
        ),
      ),
    );
  }
}
