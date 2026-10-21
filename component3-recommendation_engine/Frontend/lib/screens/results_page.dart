import 'package:flutter/material.dart';

import '../models/contracts.dart';
import '../state/app_controller.dart';
import '../theme/app_theme.dart';
import '../widgets/recommendation_views.dart';

CategoryResult? _firstWhereOrNull(
  List<CategoryResult> items,
  bool Function(CategoryResult item) test,
) {
  for (final item in items) {
    if (test(item)) return item;
  }
  return null;
}

class ResultsPage extends StatefulWidget {
  const ResultsPage({super.key, required this.controller});

  final AppController controller;

  @override
  State<ResultsPage> createState() => _ResultsPageState();
}

class _ResultsPageState extends State<ResultsPage> {
  String selected = 'hair';

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: widget.controller,
      builder: (context, _) {
        final bundle = widget.controller.lastResult;
        if (bundle == null) {
          return const Center(
            child: Padding(
              padding: EdgeInsets.all(36),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(
                    Icons.auto_awesome_rounded,
                    size: 36,
                    color: Color(0xFF1F9D55),
                  ),
                  SizedBox(height: 16),
                  Text(
                    'Your recommendations will appear here.',
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.w600,
                      letterSpacing: -0.3,
                      color: AppTheme.textPrimary,
                    ),
                  ),
                ],
              ),
            ),
          );
        }
        final response = bundle.response;
        final skipped = {
          for (final item in response.skippedCategories)
            item['category'].toString(): item,
        };
        final requested = ((bundle.request['categories'] as List?) ?? const [])
            .map((item) => item.toString())
            .toSet();
        final visible = [
          for (final category in const ['hair', 'beard', 'grooming'])
            if (_visible(response, skipped, requested, category)) category,
        ];
        final current = visible.contains(selected)
            ? selected
            : (visible.isEmpty ? 'hair' : visible.first);
        final faceShape = _profileValue(bundle.request, 'face_shape');
        final gender = _profileValue(bundle.request, 'gender');
        final captions = <String, String>{
          for (final style in widget.controller.styles)
            if ((style.definition ?? '').trim().isNotEmpty)
              style.styleId: style.definition!.trim(),
        };
        return ListView(
          padding: const EdgeInsets.fromLTRB(20, 8, 20, 32),
          children: [
            Text(
              'Style recommendations',
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            const SizedBox(height: 12),
            Wrap(
              spacing: 10,
              runSpacing: 8,
              crossAxisAlignment: WrapCrossAlignment.center,
              children: [
                if (faceShape != null && faceShape.isNotEmpty)
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 12,
                      vertical: 6,
                    ),
                    decoration: BoxDecoration(
                      color: const Color(0xFFE7F6EE),
                      borderRadius: BorderRadius.circular(999),
                    ),
                    child: Text(
                      '${_label(faceShape)} face',
                      style: const TextStyle(
                        color: Color(0xFF178A48),
                        fontWeight: FontWeight.w600,
                        fontSize: 13,
                      ),
                    ),
                  ),
                const Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(
                      Icons.thumb_up_alt_outlined,
                      size: 16,
                      color: AppTheme.textSecondary,
                    ),
                    SizedBox(width: 6),
                    Text(
                      'Ranked for you',
                      style: TextStyle(color: AppTheme.textSecondary),
                    ),
                  ],
                ),
              ],
            ),
            if (visible.isNotEmpty) ...[
              const SizedBox(height: 18),
              Container(
                padding: const EdgeInsets.all(4),
                decoration: BoxDecoration(
                  color: const Color(0xFFECEEF2),
                  borderRadius: BorderRadius.circular(16),
                ),
                child: Row(
                  children: [
                    for (final category in visible)
                      Expanded(
                        child: GestureDetector(
                          onTap: () => setState(() => selected = category),
                          child: AnimatedContainer(
                            duration: const Duration(milliseconds: 180),
                            padding: const EdgeInsets.symmetric(vertical: 10),
                            decoration: BoxDecoration(
                              color: current == category
                                  ? Colors.white
                                  : Colors.transparent,
                              borderRadius: BorderRadius.circular(12),
                              boxShadow: current == category
                                  ? [
                                      BoxShadow(
                                        color: AppTheme.primaryDarkBlue
                                            .withValues(alpha: 0.06),
                                        blurRadius: 8,
                                        offset: const Offset(0, 2),
                                      ),
                                    ]
                                  : null,
                            ),
                            child: Text(
                              _tabLabel(category),
                              textAlign: TextAlign.center,
                              style: TextStyle(
                                fontWeight: FontWeight.w700,
                                fontSize: 13,
                                color: current == category
                                    ? const Color(0xFF178A48)
                                    : AppTheme.textSecondary,
                              ),
                            ),
                          ),
                        ),
                      ),
                  ],
                ),
              ),
              const SizedBox(height: 18),
              CategorySection(
                result: _firstWhereOrNull(
                  response.categoryResults,
                  (item) => item.category == current,
                ),
                skipped: skipped[current],
                notRequested: !requested.contains(current),
                showHeading: false,
                gender: gender,
                captions: captions,
              ),
            ],
          ],
        );
      },
    );
  }

  bool _visible(
    RecommendationResponse response,
    Map<String, Map<String, dynamic>> skipped,
    Set<String> requested,
    String category,
  ) {
    final result = _firstWhereOrNull(
      response.categoryResults,
      (item) => item.category == category,
    );
    return requested.contains(category) ||
        result != null ||
        skipped.containsKey(category);
  }

  String? _profileValue(Map<String, dynamic> request, String key) {
    final profile = request['profile'];
    if (profile is Map && profile[key] != null) {
      final value = profile[key].toString().trim();
      if (value.isNotEmpty) return value;
    }
    return null;
  }

  String _label(String value) {
    return value
        .split(RegExp(r'[_\s]+'))
        .where((part) => part.isNotEmpty)
        .map(
          (part) => '${part[0].toUpperCase()}${part.substring(1).toLowerCase()}',
        )
        .join(' ');
  }

  String _tabLabel(String category) {
    switch (category) {
      case 'hair':
        return 'Hairstyles';
      case 'beard':
        return 'Beard styles';
      case 'grooming':
        return 'Grooming';
      default:
        return _label(category);
    }
  }
}
