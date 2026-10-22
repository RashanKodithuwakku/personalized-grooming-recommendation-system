import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../theme/groom_colors.dart';
import '../theme/groom_type.dart';

class GroomButton extends StatelessWidget {
  const GroomButton({
    super.key,
    required this.label,
    required this.onPressed,
    this.filled = true,
    this.height = 56,
  });

  final String label;
  final VoidCallback? onPressed;
  final bool filled;
  final double height;

  @override
  Widget build(BuildContext context) {
    final enabled = onPressed != null;
    return SizedBox(
      width: double.infinity,
      height: height,
      child: DecoratedBox(
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(18),
          color: filled
              ? (enabled
                  ? GroomColors.champagne
                  : GroomColors.champagne.withValues(alpha: 0.16))
              : Colors.transparent,
          border: Border.all(
            color: enabled ? GroomColors.champagne : GroomColors.line,
          ),
        ),
        child: Material(
          color: Colors.transparent,
          child: InkWell(
            borderRadius: BorderRadius.circular(18),
            onTap: onPressed == null
                ? null
                : () {
                    HapticFeedback.lightImpact();
                    onPressed!();
                  },
            child: Center(
              child: Text(
                label,
                style: GroomType.ui(
                  15,
                  weight: FontWeight.w500,
                  color: filled
                      ? (enabled ? GroomColors.ink : GroomColors.mute)
                      : (enabled ? GroomColors.champagne : GroomColors.mute),
                  letterSpacing: 0.2,
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
