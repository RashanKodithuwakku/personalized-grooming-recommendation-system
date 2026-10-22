import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../models/facial_profile.dart';
import '../theme/groom_colors.dart';
import '../theme/groom_type.dart';
import '../utils/format.dart';
import '../widgets/groom_background.dart';
import '../widgets/groom_button.dart';
import '../widgets/step_header.dart';

class ScoresScreen extends StatelessWidget {
  const ScoresScreen({
    super.key,
    required this.profile,
    required this.fileName,
  });

  final FacialProfile profile;
  final String fileName;

  @override
  Widget build(BuildContext context) {
    final composite = profile.groomingSuitabilityIndex;
    return Scaffold(
      backgroundColor: GroomColors.ink,
      body: GroomBackground(
        child: SafeArea(
          child: Column(
            children: [
              StepHeader(
                step: '03',
                onBack: () => Navigator.of(context).maybePop(),
              ),
              Expanded(
                child: SingleChildScrollView(
                  padding: const EdgeInsets.fromLTRB(24, 12, 24, 12),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(fileName, style: GroomType.ui(13, color: GroomColors.mute)),
                      const SizedBox(height: 18),
                      Text('HARMONY', style: GroomType.eyebrow()),
                      const SizedBox(height: 8),
                      Text(
                        'How the face\nis balanced.',
                        style: GroomType.display(40, height: 0.94),
                      ),
                      const SizedBox(height: 14),
                      Text(
                        'These numbers describe how evenly the face is arranged. A higher score means closer to even.',
                        style: GroomType.ui(15, color: GroomColors.mute, height: 1.5),
                      ),
                      const SizedBox(height: 18),
                      _HeroScore(points: composite),
                      const SizedBox(height: 14),
                      _ScoreBlock(
                        title: 'Vertical balance',
                        points: _points(profile.verticalBalanceScore),
                        explanation:
                            'Compares the upper, middle, and lower parts of the face. A higher score means those three bands sit closer to a balanced split.',
                      ),
                      _ScoreBlock(
                        title: 'Horizontal balance',
                        points: _points(profile.horizontalBalanceScore),
                        explanation:
                            'Looks across the face in five bands, from one cheek to the other. A higher score means those bands are closer to even.',
                      ),
                      _ScoreBlock(
                        title: 'Symmetry',
                        points: _points(profile.symmetryScore),
                        explanation:
                            'Compares the left and right sides against the center of the face. A higher score means the eyes, nose, mouth, and jaw match more closely.',
                      ),
                    ],
                  ),
                ),
              ),
              Padding(
                padding: const EdgeInsets.fromLTRB(24, 8, 24, 8),
                child: GroomButton(
                  label: 'New reading',
                  onPressed: () => Navigator.of(context).popUntil((route) => route.isFirst),
                ),
              ),
              Padding(
                padding: const EdgeInsets.fromLTRB(24, 0, 24, 8),
                child: GroomButton(
                  label: 'Back to face shape',
                  filled: false,
                  height: 48,
                  onPressed: () => Navigator.of(context).maybePop(),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  double? _points(double? unit) => unit == null ? null : unit * 100;
}

class _HeroScore extends StatelessWidget {
  const _HeroScore({required this.points});

  final double? points;

  @override
  Widget build(BuildContext context) {
    final missing = points == null;
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.fromLTRB(20, 22, 20, 20),
      decoration: BoxDecoration(
        color: GroomColors.card,
        borderRadius: BorderRadius.circular(28),
        border: Border.all(color: GroomColors.champagne.withValues(alpha: 0.45)),
      ),
      child: Column(
        children: [
          Text('COMPOSITE', style: GroomType.eyebrow()),
          const SizedBox(height: 10),
          SizedBox(
            width: 120,
            height: 120,
            child: CustomPaint(
              painter: _RingPainter(progress: missing ? 0 : (points! / 100).clamp(0, 1)),
              child: Center(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      formatPoints(points),
                      style: GroomType.display(36, color: GroomColors.champagne),
                    ),
                    Text('out of 100', style: GroomType.ui(12, color: GroomColors.mute)),
                  ],
                ),
              ),
            ),
          ),
          const SizedBox(height: 16),
          Text(
            'Overall reading',
            style: GroomType.ui(16, weight: FontWeight.w500),
          ),
          const SizedBox(height: 6),
          Text(
            missing
                ? 'This file did not include enough points to calculate an overall reading.'
                : 'One summary of this reading. It blends how clearly the face shape stood out with the symmetry and balance scores.',
            textAlign: TextAlign.center,
            style: GroomType.ui(14, color: GroomColors.mute, height: 1.45),
          ),
        ],
      ),
    );
  }
}

class _ScoreBlock extends StatelessWidget {
  const _ScoreBlock({
    required this.title,
    required this.points,
    required this.explanation,
  });

  final String title;
  final double? points;
  final String explanation;

  @override
  Widget build(BuildContext context) {
    final missing = points == null;
    final progress = missing ? 0.0 : (points! / 100).clamp(0, 1).toDouble();
    return Padding(
      padding: const EdgeInsets.only(top: 12),
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.fromLTRB(18, 16, 18, 16),
        decoration: BoxDecoration(
          color: GroomColors.card.withValues(alpha: 0.72),
          borderRadius: BorderRadius.circular(22),
          border: Border.all(color: GroomColors.line),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Text(
                  formatPoints(points),
                  style: GroomType.display(40, color: GroomColors.ivory),
                ),
                const SizedBox(width: 8),
                Padding(
                  padding: const EdgeInsets.only(bottom: 6),
                  child: Text('/ 100', style: GroomType.ui(13, color: GroomColors.mute)),
                ),
              ],
            ),
            const SizedBox(height: 8),
            TweenAnimationBuilder<double>(
              tween: Tween(begin: 0, end: progress),
              duration: const Duration(milliseconds: 900),
              curve: Curves.easeOutCubic,
              builder: (context, value, child) {
                return ClipRRect(
                  borderRadius: BorderRadius.circular(99),
                  child: SizedBox(
                    height: 3,
                    child: Stack(
                      fit: StackFit.expand,
                      children: [
                        const ColoredBox(color: GroomColors.track),
                        FractionallySizedBox(
                          alignment: Alignment.centerLeft,
                          widthFactor: value <= 0 ? 0.001 : value,
                          child: const ColoredBox(color: GroomColors.champagne),
                        ),
                      ],
                    ),
                  ),
                );
              },
            ),
            const SizedBox(height: 12),
            Text(title, style: GroomType.ui(16, weight: FontWeight.w500)),
            const SizedBox(height: 4),
            Text(
              missing
                  ? 'This file did not include enough points to calculate it.'
                  : explanation,
              style: GroomType.ui(14, color: GroomColors.mute, height: 1.45),
            ),
          ],
        ),
      ),
    );
  }
}

class _RingPainter extends CustomPainter {
  _RingPainter({required this.progress});

  final double progress;

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = size.width / 2 - 6;
    final base = Paint()
      ..color = GroomColors.track
      ..style = PaintingStyle.stroke
      ..strokeWidth = 3;
    final arc = Paint()
      ..color = GroomColors.champagne
      ..style = PaintingStyle.stroke
      ..strokeWidth = 3
      ..strokeCap = StrokeCap.round;
    final rect = Rect.fromCircle(center: center, radius: radius);
    canvas.drawArc(rect, 0, math.pi * 2, false, base);
    if (progress > 0) {
      canvas.drawArc(rect, -math.pi / 2, math.pi * 2 * progress, false, arc);
    }
  }

  @override
  bool shouldRepaint(_RingPainter oldDelegate) => oldDelegate.progress != progress;
}
