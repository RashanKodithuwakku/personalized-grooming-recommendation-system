import 'package:flutter/material.dart';

import '../copy/face_copy.dart';
import '../models/facial_profile.dart';
import '../navigation.dart';
import '../theme/groom_colors.dart';
import '../theme/groom_type.dart';
import '../utils/format.dart';
import '../widgets/groom_background.dart';
import '../widgets/groom_button.dart';
import '../widgets/step_header.dart';
import 'scores_screen.dart';

class FaceTypeScreen extends StatelessWidget {
  const FaceTypeScreen({
    super.key,
    required this.profile,
    required this.fileName,
  });

  final FacialProfile profile;
  final String fileName;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: GroomColors.ink,
      body: GroomBackground(
        child: SafeArea(
          child: Column(
            children: [
              StepHeader(
                step: '02',
                onBack: () => Navigator.of(context).popUntil((route) => route.isFirst),
              ),
              Expanded(
                child: profile.failed
                    ? _FailedReading(profile: profile, fileName: fileName)
                    : _ShapeReading(profile: profile, fileName: fileName),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _FailedReading extends StatelessWidget {
  const _FailedReading({required this.profile, required this.fileName});

  final FacialProfile profile;
  final String fileName;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(24, 28, 24, 18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(fileName, style: GroomType.ui(13, color: GroomColors.mute)),
          const SizedBox(height: 18),
          Text('This file\ncould not be read.', style: GroomType.display(42, height: 0.95)),
          const SizedBox(height: 16),
          Text(
            readingFailureCopy(profile.errorCode),
            style: GroomType.ui(15, color: GroomColors.mute, height: 1.5),
          ),
          const Spacer(),
          GroomButton(
            label: 'Choose another file',
            onPressed: () => Navigator.of(context).popUntil((route) => route.isFirst),
          ),
        ],
      ),
    );
  }
}

class _ShapeReading extends StatelessWidget {
  const _ShapeReading({required this.profile, required this.fileName});

  final FacialProfile profile;
  final String fileName;

  @override
  Widget build(BuildContext context) {
    final label = profile.faceShapeLabel!;
    final story = faceShapeStories[label];
    final title = shapeTitle(label);
    final percent = formatUnitPercent(profile.leadingScore);
    final proportion = morphologicalCopy[profile.faceShapeClass];
    final jaw = jawCopy[profile.jawlineCategory];
    final ranked = profile.rankedShapes;

    return Column(
      children: [
        Expanded(
          child: SingleChildScrollView(
            padding: const EdgeInsets.fromLTRB(24, 12, 24, 12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(fileName, style: GroomType.ui(13, color: GroomColors.mute)),
                const SizedBox(height: 18),
                Text('CLOSEST SHAPE', style: GroomType.eyebrow()),
                const SizedBox(height: 8),
                Text(title, style: GroomType.display(64, height: 0.9)),
                if (profile.leadingScore != null) ...[
                  const SizedBox(height: 8),
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.end,
                    children: [
                      Text('$percent%', style: GroomType.display(42, color: GroomColors.champagne)),
                      const SizedBox(width: 10),
                      Padding(
                        padding: const EdgeInsets.only(bottom: 8),
                        child: Text('match', style: GroomType.ui(14, color: GroomColors.mute)),
                      ),
                    ],
                  ),
                ],
                const SizedBox(height: 18),
                Text(
                  story?.summary ?? 'This is the shape the landmarks matched most closely.',
                  style: GroomType.ui(16, height: 1.45),
                ),
                if (story != null) ...[
                  const SizedBox(height: 8),
                  Text(story.detail, style: GroomType.ui(15, color: GroomColors.mute, height: 1.5)),
                ],
                if (proportion != null) ...[
                  const SizedBox(height: 8),
                  Text(proportion, style: GroomType.ui(15, color: GroomColors.mute, height: 1.5)),
                ],
                if (profile.limited) ...[
                  const SizedBox(height: 16),
                  const _Note(
                    text: 'A few landmarks were missing, so this reading is lighter than a full one.',
                  ),
                ],
                const SizedBox(height: 28),
                Text('HOW CLOSE EACH SHAPE IS', style: GroomType.eyebrow()),
                const SizedBox(height: 8),
                Text(
                  'Each percentage is how strongly this face matches that shape. A face can sit near more than one, so the numbers do not need to add up to 100.',
                  style: GroomType.ui(13, color: GroomColors.mute, height: 1.45),
                ),
                const SizedBox(height: 16),
                for (final match in ranked)
                  _ShapeBar(
                    title: shapeTitle(match.name),
                    score: match.score,
                    active: match.name == label,
                  ),
                if (jaw != null) ...[
                  const SizedBox(height: 12),
                  _QuietFact(label: 'Jaw', text: jaw),
                ],
              ],
            ),
          ),
        ),
        Padding(
          padding: const EdgeInsets.fromLTRB(24, 8, 24, 18),
          child: GroomButton(
            label: 'See balance and symmetry',
            onPressed: () {
              Navigator.of(context).push(
                fadeRoute(ScoresScreen(profile: profile, fileName: fileName)),
              );
            },
          ),
        ),
      ],
    );
  }
}

class _ShapeBar extends StatelessWidget {
  const _ShapeBar({
    required this.title,
    required this.score,
    required this.active,
  });

  final String title;
  final double score;
  final bool active;

  @override
  Widget build(BuildContext context) {
    final widthFactor = score.clamp(0.0, 1.0).toDouble();
    return Padding(
      padding: const EdgeInsets.only(bottom: 14),
      child: Column(
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  title,
                  style: GroomType.ui(
                    15,
                    weight: active ? FontWeight.w500 : FontWeight.w400,
                    color: active ? GroomColors.ivory : GroomColors.mute,
                  ),
                ),
              ),
              Text(
                '${formatUnitPercent(score)}%',
                style: GroomType.ui(
                  14,
                  weight: FontWeight.w500,
                  color: active ? GroomColors.champagne : GroomColors.mute,
                ),
              ),
            ],
          ),
          const SizedBox(height: 7),
          TweenAnimationBuilder<double>(
            tween: Tween(begin: 0, end: widthFactor),
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
                        widthFactor: value == 0 ? 0.001 : value,
                        child: const ColoredBox(
                          color: GroomColors.champagne,
                        ),
                      ),
                    ],
                  ),
                ),
              );
            },
          ),
        ],
      ),
    );
  }
}

class _Note extends StatelessWidget {
  const _Note({required this.text});

  final String text;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: GroomColors.line),
      ),
        child: Text(text, style: GroomType.ui(13, color: GroomColors.champagne, height: 1.4)),
    );
  }
}

class _QuietFact extends StatelessWidget {
  const _QuietFact({required this.label, required this.text});

  final String label;
  final String text;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: GroomColors.card,
        borderRadius: BorderRadius.circular(18),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label.toUpperCase(), style: GroomType.eyebrow()),
          const SizedBox(height: 6),
          Text(text, style: GroomType.ui(14, height: 1.4)),
        ],
      ),
    );
  }
}
