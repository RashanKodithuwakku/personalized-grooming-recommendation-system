import 'package:flutter/material.dart';

import '../models/contracts.dart';
import '../theme/app_theme.dart';
import '../utils/style_images.dart';

class RecommendationCard extends StatelessWidget {
  const RecommendationCard({
    super.key,
    required this.item,
    this.gender,
    this.caption,
  });

  final RecommendationItem item;
  final String? gender;
  final String? caption;

  @override
  Widget build(BuildContext context) {
    final score = item.compatibilityScore.round().clamp(0, 100);
    final scoreColor = _scoreColor(score);
    final image = styleImageAsset(
      styleName: item.styleName,
      category: item.category,
      gender: gender,
    );
    final blurb = (caption ?? styleBlurb(item.styleName))?.trim();
    return Container(
      margin: const EdgeInsets.only(bottom: 14),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(22),
        boxShadow: [
          BoxShadow(
            color: AppTheme.primaryDarkBlue.withValues(alpha: 0.06),
            blurRadius: 18,
            offset: const Offset(0, 8),
          ),
        ],
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _photo(image),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(
                      child: Text(
                        item.styleName,
                        style: const TextStyle(
                          fontSize: 16,
                          height: 1.2,
                          fontWeight: FontWeight.w700,
                          letterSpacing: -0.3,
                          color: AppTheme.textPrimary,
                        ),
                      ),
                    ),
                    if (item.rank == 1) ...[
                      const SizedBox(width: 8),
                      const _TopBadge(),
                    ],
                  ],
                ),
                const SizedBox(height: 10),
                Row(
                  children: [
                    const Expanded(
                      child: Text(
                        'Score',
                        style: TextStyle(
                          fontSize: 12,
                          color: AppTheme.textSecondary,
                        ),
                      ),
                    ),
                    Text(
                      '$score%',
                      style: TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.w700,
                        color: scoreColor,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 6),
                ClipRRect(
                  borderRadius: BorderRadius.circular(99),
                  child: LinearProgressIndicator(
                    value: score / 100,
                    minHeight: 6,
                    backgroundColor: const Color(0xFFE8E8ED),
                    color: scoreColor,
                  ),
                ),
                if (blurb != null && blurb.isNotEmpty) ...[
                  const SizedBox(height: 10),
                  Text(
                    blurb,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      fontSize: 12,
                      height: 1.35,
                      color: AppTheme.textSecondary,
                    ),
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }

  Color _scoreColor(int score) {
    if (score >= 85) return const Color(0xFF1F9D55);
    if (score >= 70) return const Color(0xFFE07A1F);
    return AppTheme.accent;
  }

  Widget _photo(String? asset) {
    const width = 92.0;
    const height = 112.0;
    final placeholder = Container(
      width: width,
      height: height,
      color: const Color(0xFFEEF0F3),
      alignment: Alignment.center,
      child: const Icon(
        Icons.face_retouching_natural_outlined,
        color: AppTheme.textSecondary,
      ),
    );
    return ClipRRect(
      borderRadius: BorderRadius.circular(16),
      child: asset == null
          ? placeholder
          : Image.asset(
              asset,
              width: width,
              height: height,
              fit: BoxFit.cover,
              errorBuilder: (context, error, stackTrace) => placeholder,
            ),
    );
  }
}

class _TopBadge extends StatelessWidget {
  const _TopBadge();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: const Color(0xFFE7F8EE),
        borderRadius: BorderRadius.circular(999),
      ),
      child: const Text(
        'TOP',
        style: TextStyle(
          fontSize: 11,
          fontWeight: FontWeight.w700,
          letterSpacing: 0.4,
          color: Color(0xFF178A48),
        ),
      ),
    );
  }
}

class CategorySection extends StatelessWidget {
  const CategorySection({
    super.key,
    required this.result,
    this.skipped,
    this.notRequested = false,
    this.showHeading = true,
    this.gender,
    this.captions = const {},
  });

  final CategoryResult? result;
  final Map<String, dynamic>? skipped;
  final bool notRequested;
  final bool showHeading;
  final String? gender;
  final Map<String, String> captions;

  @override
  Widget build(BuildContext context) {
    if (notRequested && result == null && skipped == null) {
      return const SizedBox.shrink();
    }
    final category = result?.category ?? skipped?['category']?.toString() ?? '';
    final recommendations = result?.status == 'skipped'
        ? const <RecommendationItem>[]
        : result?.recommendations ?? const <RecommendationItem>[];
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (showHeading) ...[
            Text(_title(category), style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 12),
          ],
          if (recommendations.isEmpty)
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(18),
              decoration: BoxDecoration(
                color: AppTheme.card,
                borderRadius: BorderRadius.circular(20),
              ),
              child: Text(
                _emptyMessage(category),
                style: const TextStyle(color: AppTheme.textSecondary),
              ),
            )
          else
            for (final item in recommendations) ...[
              Padding(
                padding: const EdgeInsets.only(left: 4, bottom: 6),
                child: Text(
                  '#${item.rank}',
                  style: const TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w700,
                    color: Color(0xFFB0B4BA),
                  ),
                ),
              ),
              RecommendationCard(
                item: item,
                gender: gender,
                caption: captions[item.styleId] ??
                    captions[item.styleId.toUpperCase()],
              ),
            ],
        ],
      ),
    );
  }

  String _title(String category) {
    switch (category) {
      case 'hair':
        return 'Hair';
      case 'beard':
        return 'Beard';
      case 'grooming':
        return 'Grooming';
      default:
        return category;
    }
  }

  String _emptyMessage(String category) {
    final name = _title(category).toLowerCase();
    if (skipped != null ||
        result?.status == 'skipped' ||
        result?.status == 'empty') {
      return 'No $name recommendations for this profile.';
    }
    return 'No $name recommendations yet.';
  }
}
