import 'package:component3_frontend/config/api_config.dart';
import 'package:component3_frontend/models/contracts.dart';
import 'package:component3_frontend/services/recommendation_api.dart';
import 'package:flutter/foundation.dart';
import 'package:component3_frontend/utils/style_images.dart';
import 'package:component3_frontend/widgets/recommendation_views.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

void main() {
  test('style photos follow catalogue names and gender', () {
    expect(
      styleImageAsset(
        styleName: 'Crew cut',
        category: 'hair',
        gender: 'male',
      ),
      'assets/styles/male/hair/crew_cut.jpg',
    );
    expect(
      styleImageAsset(
        styleName: 'Long layers',
        category: 'hair',
        gender: 'female',
      ),
      'assets/styles/female/hair/long_layers.jpg',
    );
    expect(
      styleImageAsset(
        styleName: 'Natural brow maintenance',
        category: 'grooming',
        gender: 'female',
      ),
      'assets/styles/female/grooming/natural_brow_maintenance.jpg',
    );
    expect(
      styleImageAsset(
        styleName: 'Pixie cut',
        category: 'hair',
        gender: 'female',
      ),
      'assets/styles/female/hair/pixie_cut.jpg',
    );
    expect(
      styleImageAsset(styleName: 'Side part', category: 'hair', gender: 'male'),
      'assets/styles/male/hair/side_part.jpg',
    );
    expect(
      styleImageAsset(
        styleName: 'Side part',
        category: 'hair',
        gender: 'female',
      ),
      'assets/styles/female/hair/side_part.jpg',
    );
    expect(
      styleImageAsset(
        styleName: 'Textured crop',
        category: 'hair',
        gender: 'female',
      ),
      'assets/styles/female/hair/textured_crop.jpg',
    );
    expect(
      styleImageAsset(
        styleName: 'Layered cut',
        category: 'hair',
        gender: 'female',
      ),
      'assets/styles/female/hair/layered_cut.jpg',
    );
    expect(
      styleImageAsset(
        styleName: 'Shoulder-length layers',
        category: 'hair',
        gender: 'female',
      ),
      'assets/styles/female/hair/shoulder_length_layers.jpg',
    );
    expect(
      styleImageAsset(
        styleName: 'Long layers',
        category: 'hair',
        gender: 'male',
      ),
      'assets/styles/male/hair/long_layers.jpg',
    );
    expect(
      styleImageAsset(
        styleName: 'Rounded brow styling',
        category: 'grooming',
        gender: 'female',
      ),
      'assets/styles/female/grooming/rounded_brow_styling.jpg',
    );
    expect(
      styleImageAsset(
        styleName: 'Crew cut',
        category: 'hair',
        gender: 'female',
      ),
      isNull,
    );
  });

  testWidgets('recommendation card shows the photo and score', (tester) async {
    final item = RecommendationItem(
      rank: 1,
      styleId: 'H001',
      styleName: 'Crew cut',
      category: 'hair',
      rawRankerScore: 0.9,
      rawPredictedCompatibilityRating: 0.9,
      displayCompatibilityRating: 0.94,
      compatibilityScore: 94,
      rankPercentile: 1,
      normalizedPredictedCompatibility: 0.94,
      hybridScore: 0.9,
      requiresFacialHair: false,
      summary: 'technical summary that should stay hidden',
    );
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: Center(
            child: SizedBox(
              width: 340,
              child: RecommendationCard(item: item, gender: 'male'),
            ),
          ),
        ),
      ),
    );
    await tester.pump();
    expect(find.text('Crew cut'), findsOneWidget);
    expect(find.text('Compatibility score'), findsOneWidget);
    expect(find.text('94%'), findsOneWidget);
    expect(find.text('TOP'), findsOneWidget);
    expect(find.textContaining('technical summary'), findsNothing);
    expect(find.textContaining('Short hair on top'), findsOneWidget);
    expect(find.byType(Image), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  test('default API URL uses Component 3 port 8010', () {
    expect(ApiConfig.baseUrl, isNot(contains(':8000')));
    expect(ApiConfig.baseUrl, endsWith(':8010'));
    if (!kIsWeb && defaultTargetPlatform == TargetPlatform.android) {
      expect(ApiConfig.baseUrl, 'http://10.0.2.2:8010');
    } else {
      expect(ApiConfig.baseUrl, 'http://127.0.0.1:8010');
    }
    expect(
      ApiConfig.normalize('http://127.0.0.1:8010///'),
      'http://127.0.0.1:8010',
    );
    expect(ApiConfig.validateBaseUrl('not-a-url'), isNotNull);
    expect(ApiConfig.validateBaseUrl('http://127.0.0.1:8010'), isNull);
  });

  test('explicit beard opt-out stays false and is not omitted', () {
    final body = RecommendationRequestBody(
      profile: Map<String, Object>.from(maleDemoProfile),
      categories: const ['beard'],
      topN: 3,
      includeBeard: false,
    ).toJson();
    expect(body['preferences']['include_beard'], isFalse);
  });

  test('partial confidence is rejected and zero is accepted', () {
    final partial = ProfileValidation.validateConfidence(
      rankingMode: 'standard',
      confidenceText: {
        for (final key in facialConfidenceKeys)
          key: key == 'symmetry' ? '1' : '',
      },
      confidenceEnabled: true,
    );
    expect(partial['_form'], contains('incomplete'));

    final zeros = ProfileValidation.validateConfidence(
      rankingMode: 'confidence_aware',
      confidenceText: {for (final key in facialConfidenceKeys) key: '0'},
      confidenceEnabled: true,
    );
    expect(zeros, isEmpty);

    final invalid = ProfileValidation.validateProfile({
      ...{
        for (final key in maleDemoProfile.keys) key: '${maleDemoProfile[key]}',
      },
      'symmetry': 'NaN',
    });
    expect(invalid['symmetry'], contains('finite'));
  });

  test('request omits optional preference and confidence fields', () {
    final body = RecommendationRequestBody(
      profile: Map<String, Object>.from(maleDemoProfile),
      categories: const ['hair'],
      topN: 3,
    ).toJson();
    expect(body.containsKey('attribute_confidence'), isFalse);
    expect(body['confidence_source'], 'unspecified');
    expect(body['ranking_mode'], 'standard');
    expect((body['preferences'] as Map).containsKey('include_beard'), isFalse);
  });

  test('confidence-aware mode requires the nine facial values', () {
    final errors = ProfileValidation.validateConfidence(
      rankingMode: 'confidence_aware',
      confidenceText: {for (final key in facialConfidenceKeys) key: ''},
      confidenceEnabled: true,
    );
    expect(errors.length, facialConfidenceKeys.length);

    final complete = ProfileValidation.validateConfidence(
      rankingMode: 'confidence_aware',
      confidenceText: {for (final key in facialConfidenceKeys) key: '1'},
      confidenceEnabled: true,
    );
    expect(complete, isEmpty);
  });

  test('response parser keeps null calibrated confidence and null support', () {
    final response = RecommendationResponse.fromJson({
      'request_id': 'abc',
      'ranking_mode': 'standard',
      'confidence_source': 'unspecified',
      'ranking_policy': {
        'policy_name': 'hybrid_model_rank_rules_v1',
        'description': 'test',
        'weights': {
          'predicted_compatibility': 0.5,
          'rank_percentile': 0.3,
          'rule_compatibility': 0.2,
        },
        'note': 'provisional',
      },
      'input_quality': {
        'confidence_status': 'not_provided',
        'assessment': 'unknown',
        'input_quality_score': null,
        'confidence_coverage': 0,
        'confidence_attributes_missing': facialConfidenceKeys,
      },
      'recommendation_confidence': null,
      'recommendation_confidence_status': 'not_calibrated',
      'category_results': [
        {
          'category': 'hair',
          'status': 'ok',
          'eligible_count': 1,
          'returned_count': 1,
          'recommendation_disposition': 'review_required',
          'recommendations': [
            {
              'rank': 1,
              'style_id': 'H001',
              'style_name': 'Crew cut',
              'category': 'hair',
              'raw_ranker_score': 1.2,
              'raw_predicted_compatibility_rating': 3.4,
              'display_compatibility_rating': 3.4,
              'compatibility_score': 60,
              'rank_percentile': 1,
              'normalized_predicted_compatibility': 0.6,
              'rule_compatibility_score': 0.7,
              'rule_confidence_coverage': null,
              'recommendation_support_score': null,
              'confidence_adjusted_rule_score': null,
              'hybrid_score': 0.64,
              'requires_facial_hair': false,
              'explanation': {
                'summary': 'Selected after eligibility filtering.',
                'rule_contributions': [],
                'notes': [],
              },
            },
          ],
        },
      ],
      'skipped_categories': [
        {
          'category': 'beard',
          'status': 'unsupported_model_coverage',
          'reason': 'Beard ranker trained on male profiles only.',
        },
      ],
    });
    expect(response.recommendationConfidence, isNull);
    expect(response.recommendationConfidenceStatus, 'not_calibrated');
    expect(
      response
          .categoryResults
          .first
          .recommendations
          .first
          .recommendationSupportScore,
      isNull,
    );
    expect(
      response.skippedCategories.single['status'],
      'unsupported_model_coverage',
    );
  });

  testWidgets('skipped category stays visible beside other results', (
    tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: CategorySection(
            result: null,
            skipped: const {
              'category': 'beard',
              'status': 'unsupported_model_coverage',
              'reason': 'Male-only training coverage.',
            },
          ),
        ),
      ),
    );
    expect(find.text('Beard'), findsOneWidget);
    expect(
      find.textContaining('No beard recommendations for this profile.'),
      findsOneWidget,
    );
  });

  test('validation errors map onto profile fields', () async {
    final api = RecommendationApi(
      baseUrl: 'http://127.0.0.1:8010',
      client: MockClient(
        (request) async => http.Response(
          '{"detail":[{"loc":["body","profile","symmetry"],"msg":"Input should be less than or equal to 1"}]}',
          422,
        ),
      ),
    );
    try {
      await api.recommend(
        RecommendationRequestBody(
          profile: Map<String, Object>.from(maleDemoProfile),
          categories: const ['hair'],
          topN: 3,
        ),
      );
      fail('expected ApiException');
    } on ApiException catch (error) {
      expect(error.profileErrors['symmetry'], contains('less than or equal'));
      expect(error.message, contains('less than or equal'));
      expect(error.toString(), isNot(contains('StackTrace')));
    }
  });

  test('API failure becomes an actionable message', () async {
    final api = RecommendationApi(
      baseUrl: 'http://127.0.0.1:9',
      client: MockClient((request) async => throw http.ClientException('down')),
    );
    await expectLater(api.isLive(), throwsA(isA<ApiException>()));
  });
}
