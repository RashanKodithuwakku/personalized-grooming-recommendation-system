import 'package:flutter/material.dart';

import 'groom_colors.dart';

abstract final class GroomType {
  static TextStyle display(
    double size, {
    FontWeight weight = FontWeight.w500,
    Color color = GroomColors.ivory,
    double height = 0.96,
  }) {
    return TextStyle(
      fontFamily: 'Cormorant Garamond',
      fontSize: size,
      fontWeight: weight,
      height: height,
      color: color,
      letterSpacing: -0.6,
    );
  }

  static TextStyle ui(
    double size, {
    FontWeight weight = FontWeight.w400,
    Color color = GroomColors.ivory,
    double height = 1.4,
    double letterSpacing = 0,
  }) {
    return TextStyle(
      fontFamily: 'Outfit',
      fontSize: size,
      fontWeight: weight,
      height: height,
      color: color,
      letterSpacing: letterSpacing,
    );
  }

  static TextStyle eyebrow({Color color = GroomColors.champagne}) {
    return ui(
      11,
      weight: FontWeight.w500,
      color: color,
      height: 1.2,
      letterSpacing: 2.6,
    );
  }
}
