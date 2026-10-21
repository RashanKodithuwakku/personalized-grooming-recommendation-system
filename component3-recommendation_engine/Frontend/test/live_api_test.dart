import 'package:component3_frontend/models/contracts.dart';
import 'package:component3_frontend/services/recommendation_api.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  final api = RecommendationApi(baseUrl: 'http://127.0.0.1:8010');
  var backendLive = false;

  setUpAll(() async {
    try {
      backendLive = await api.isLive();
    } on ApiException {
      backendLive = false;
    }
  });

  void requireBackend() {
    if (!backendLive) {
      markTestSkipped('Component 3 is not live on 127.0.0.1:8010');
    }
  }

  RecommendationRequestBody request(
    Map<String, Object> profile, {
    String mode = 'standard',
    Map<String, double>? confidence,
    List<String> excluded = const [],
    bool? includeBeard = true,
    bool facialHairAvailable = true,
  }) {
    return RecommendationRequestBody(
      profile: profile,
      categories: const ['hair', 'beard', 'grooming'],
      topN: 3,
      includeBeard: includeBeard,
      facialHairAvailable: facialHairAvailable,
      excludedStyleIds: excluded,
      attributeConfidence: confidence,
      rankingMode: mode,
      confidenceSource: confidence == null ? 'unspecified' : 'manual',
    );
  }

  Map<String, double> filled(double value) => {
    for (final key in facialConfidenceKeys) key: value,
  };

  test('male demo returns hair, beard, and grooming', () async {
    requireBackend();
    final response = await api.recommend(
      request(Map<String, Object>.from(maleDemoProfile)),
    );
    expect(
      response.categoryResults.map((item) => item.category),
      containsAll(['hair', 'beard', 'grooming']),
    );
    for (final category in response.categoryResults) {
      expect(category.status, 'ok');
      expect(category.recommendations, isNotEmpty);
    }
    expect(response.recommendationConfidence, isNull);
    expect(response.recommendationConfidenceStatus, 'not_calibrated');
  });

  test(
    'female demo keeps hair and grooming and reports beard coverage',
    () async {
      requireBackend();
      final omitted = await api.recommend(
        request(
          Map<String, Object>.from(femaleDemoProfile),
          includeBeard: null,
          facialHairAvailable: false,
        ),
      );
      expect(
        omitted.categoryResults
            .where((item) => item.category != 'beard')
            .map((item) => item.status),
        everyElement('ok'),
      );
      expect(
        omitted.skippedCategories.map((item) => item['status']),
        contains('default_gender_policy'),
      );

      final explicit = await api.recommend(
        request(
          Map<String, Object>.from(femaleDemoProfile),
          includeBeard: true,
          facialHairAvailable: false,
        ),
      );
      expect(
        explicit.skippedCategories.singleWhere(
          (item) => item['category'] == 'beard',
        )['status'],
        'unsupported_model_coverage',
      );
      expect(
        explicit.categoryResults
            .where(
              (item) => item.category == 'hair' || item.category == 'grooming',
            )
            .every((item) => item.recommendations.isNotEmpty),
        isTrue,
      );
    },
  );

  test('all-one and all-zero confidence follow the backend policy', () async {
    requireBackend();
    final standard = await api.recommend(
      request(Map<String, Object>.from(maleDemoProfile), confidence: filled(1)),
    );
    final aware = await api.recommend(
      request(
        Map<String, Object>.from(maleDemoProfile),
        mode: 'confidence_aware',
        confidence: filled(1),
      ),
    );
    expect(standard.policy.activeRankingMode, 'standard');
    expect(aware.policy.policyName, 'hybrid_confidence_adjusted_rules_v1');
    expect(aware.policy.fallbackApplied, isFalse);

    final zeros = await api.recommend(
      request(
        Map<String, Object>.from(maleDemoProfile),
        mode: 'confidence_aware',
        confidence: filled(0),
      ),
    );
    expect(zeros.policy.fallbackApplied, isTrue);
    expect(zeros.policy.activeRankingMode, 'standard');
    expect(
      zeros.categoryResults.every(
        (item) => item.disposition == 'review_required',
      ),
      isTrue,
    );
  });

  test('excluded style is absent from the live ranking', () async {
    requireBackend();
    final response = await api.recommend(
      request(
        Map<String, Object>.from(maleDemoProfile),
        excluded: const ['H001'],
      ),
    );
    final hair = response.categoryResults.singleWhere(
      (item) => item.category == 'hair',
    );
    expect(
      hair.recommendations.map((item) => item.styleId),
      isNot(contains('H001')),
    );
  });
}
