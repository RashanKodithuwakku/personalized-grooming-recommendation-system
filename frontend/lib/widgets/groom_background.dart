import 'package:flutter/material.dart';

import '../theme/groom_colors.dart';

class GroomBackground extends StatelessWidget {
  const GroomBackground({super.key, required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [Color(0xFF1C1612), GroomColors.ink, Color(0xFF0C0B0A)],
          stops: [0, 0.32, 1],
        ),
      ),
      child: Stack(
        fit: StackFit.expand,
        children: [
          const Positioned(
            top: -90,
            right: -70,
            child: _Glow(diameter: 280),
          ),
          const Positioned(
            bottom: 80,
            left: -100,
            child: _Glow(diameter: 220, opacity: 0.08),
          ),
          child,
        ],
      ),
    );
  }
}

class _Glow extends StatelessWidget {
  const _Glow({required this.diameter, this.opacity = 0.16});

  final double diameter;
  final double opacity;

  @override
  Widget build(BuildContext context) {
    return IgnorePointer(
      child: Container(
        width: diameter,
        height: diameter,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          gradient: RadialGradient(
            colors: [
              GroomColors.champagne.withValues(alpha: opacity),
              GroomColors.champagne.withValues(alpha: 0),
            ],
          ),
        ),
      ),
    );
  }
}
