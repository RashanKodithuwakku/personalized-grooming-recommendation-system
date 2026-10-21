import 'dart:convert';

import 'package:component3_frontend/app.dart';
import 'package:component3_frontend/models/contracts.dart';
import 'package:component3_frontend/services/recommendation_api.dart';
import 'package:component3_frontend/state/app_controller.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

void main() {
  Map<String, dynamic> readyBody({required bool ready}) => {
    'status': ready ? 'ready' : 'not_ready',
    'ready': ready,
    'diagnostics': ready ? [] : ['models missing'],
  };

  RecommendationApi apiFor(Map<String, dynamic> ready) {
    return RecommendationApi(
      baseUrl: 'http://127.0.0.1:8010',
      client: MockClient((request) async {
        final path = request.url.path;
        if (path == '/health/live') {
          return http.Response(
            jsonEncode({
              'status': 'ok',
              'service': 'Style Recommendation and Ranking Engine',
              'version': '1.0.0',
            }),
            200,
          );
        }
        if (path == '/health/ready') {
          return http.Response(jsonEncode(ready), 200);
        }
        if (path == '/api/v1/models/info') {
          return http.Response(
            jsonEncode({
              'models': [
                {'filename': 'hair_ranker_gender_aware.cbm', 'loaded': true},
              ],
            }),
            200,
          );
        }
        if (path == '/api/v1/styles') {
          return http.Response(jsonEncode({'styles': []}), 200);
        }
        if (path == '/api/v1/input-schema') {
          return http.Response(
            jsonEncode({
              'top_n_limits': {'max': 20},
            }),
            200,
          );
        }
        if (request.method == 'POST') {
          return http.Response(_recommendationBody, 200);
        }
        return http.Response(jsonEncode({'rules_available': true}), 200);
      }),
    );
  }

  test('HTTP 200 with ready false is not treated as ready', () async {
    final controller = AppController(api: apiFor(readyBody(ready: false)));
    await controller.refreshConnection();
    expect(controller.ready, isFalse);
    expect(controller.connectionStatus, 'notReady');
    expect(controller.connectionError, contains('not ready'));
    expect(controller.metadataCurrent, isTrue);
  });

  test(
    'changing the base URL drops previous server metadata and results',
    () async {
      final controller = AppController(api: apiFor(readyBody(ready: true)));
      controller.loadDemo(maleDemoProfile);
      await controller.generate();
      expect(controller.lastResult, isNotNull);
      expect(controller.resultsAreCurrent, isTrue);

      final accepted = controller.setBaseUrl('http://127.0.0.1:8020');
      expect(accepted, isTrue);
      expect(controller.resultsAreCurrent, isFalse);
      expect(controller.metadataCurrent, isFalse);
      expect(controller.modelsInfo, isNull);
      expect(controller.profileText['gender'], 'male');
      expect(controller.setBaseUrl('notaurl'), isFalse);
      expect(controller.api.baseUrl, 'http://127.0.0.1:8020');
    },
  );

  testWidgets('phone and desktop layouts do not overflow', (tester) async {
    final controller = AppController(api: apiFor(readyBody(ready: true)));
    await tester.pumpWidget(StyleRankerApp(controller: controller));
    await _pumpSize(tester, const Size(360, 700));
    await _pumpSize(tester, const Size(1280, 800));
    expect(tester.takeException(), isNull);
  });
}

const _recommendationBody = '''
{
  "request_id": "abc",
  "ranking_mode": "standard",
  "confidence_source": "unspecified",
  "ranking_policy": {
    "policy_name": "hybrid_model_rank_rules_v1",
    "description": "test",
    "weights": {"predicted_compatibility": 0.5, "rank_percentile": 0.3, "rule_compatibility": 0.2},
    "note": "provisional"
  },
  "input_quality": {
    "confidence_status": "not_provided",
    "assessment": "unknown",
    "input_quality_score": null,
    "confidence_coverage": 0
  },
  "recommendation_confidence": null,
  "recommendation_confidence_status": "not_calibrated",
  "category_results": [],
  "skipped_categories": []
}
''';

Future<void> _pumpSize(WidgetTester tester, Size size) async {
  tester.view.physicalSize = size;
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
  await tester.pump();
  await tester.pump(const Duration(milliseconds: 50));
  expect(tester.takeException(), isNull);
}
