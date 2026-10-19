import 'package:flutter/material.dart';

class AppTheme {
  static const Color primaryDarkBlue = Color(0xFF0A2540);
  static const Color backgroundLightGrey = Color(0xFFF5F5F7);
  static const Color textPrimaryColor = Color(0xFF1D1D1F);
  static const Color textSecondaryColor = Color(0xFF86868B);
  static const Color accentColor = Color(0xFF0066CC);

  static ThemeData get lightTheme {
    return ThemeData(
      useMaterial3: true,
      primaryColor: primaryDarkBlue,
      scaffoldBackgroundColor: backgroundLightGrey,
      colorScheme: ColorScheme.fromSeed(
        seedColor: primaryDarkBlue,
        primary: primaryDarkBlue,
        secondary: accentColor,
        surface: backgroundLightGrey,
      ),
      appBarTheme: const AppBarTheme(
        backgroundColor: primaryDarkBlue,
        foregroundColor: Colors.white,
        centerTitle: true,
        elevation: 0,
      ),
      textTheme: const TextTheme(
        displayLarge: TextStyle(fontSize: 32, fontWeight: FontWeight.bold, color: textPrimaryColor),
        displayMedium: TextStyle(fontSize: 28, fontWeight: FontWeight.bold, color: textPrimaryColor),
        titleLarge: TextStyle(fontSize: 22, fontWeight: FontWeight.w600, color: textPrimaryColor),
        bodyLarge: TextStyle(fontSize: 16, color: textPrimaryColor),
        bodyMedium: TextStyle(fontSize: 14, color: textSecondaryColor),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: primaryDarkBlue,
          foregroundColor: Colors.white,
          elevation: 2,
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
          textStyle: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
        ),
      ),
    );
  }
}
