import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:groom_app/config/api_config.dart';
import 'package:groom_app/models/facial_profile.dart';
import 'package:groom_app/services/analysis_service.dart';
import 'package:groom_app/utils/format.dart';
import 'package:groom_app/utils/landmark_validation.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

void main() {
  test('profile endpoint keeps the host and port', () {
    final uri = profileUri('http://10.0.2.2:8000/');
    expect(uri.toString(), 'http://10.0.2.2:8000/v1/profile');
    expect(validateBaseUrl('not a url'), isNotNull);
  });

  test('landmark bytes must be a JSON object', () {
    expect(validateLandmarkBytes(Uint8List.fromList(utf8.encode('{"nasion": 1}'))), isNull);
    expect(validateLandmarkBytes(Uint8List.fromList(utf8.encode('[1]'))), isNotNull);
    expect(validateLandmarkBytes(Uint8List.fromList(utf8.encode('nope'))), isNotNull);
    final bom = Uint8List.fromList([0xEF, 0xBB, 0xBF, ...utf8.encode('{"ok": true}')]);
    expect(validateLandmarkBytes(bom), isNull);
  });

  test('points stay on a 0 to 100 scale', () {
    expect(formatPoints(84.5), '84.5');
    expect(formatPoints(82), '82');
    expect(formatUnitPercent(0.86), '86');
    expect(formatUnitPercent(null), '—');
  });

  test('a profile ranks the closest shape first', () {
    final profile = FacialProfile.fromJson({
      'status': 'limited_analysis',
      'face_shape_label': 'heart',
      'face_shape_confidence': {'heart': 0.4, 'oval': 0.7, 'round': 0.1},
      'symmetry_score': null,
      'grooming_suitability_index': null,
    });
    expect(profile.limited, isTrue);
    expect(profile.rankedShapes.first.name, 'oval');
    expect(profile.rankedShapes.map((match) => match.name), containsAll(['square', 'diamond']));
    expect(profile.symmetryScore, isNull);
  });

  test('the service reads a profile response', () async {
    final client = MockClient((request) async {
      expect(request.headers['Content-Type'], 'application/json');
      expect(utf8.decode(request.bodyBytes), '{"landmarks":true}');
      return http.Response(
        jsonEncode({
          'status': 'error',
          'error_code': 'MISSING_LANDMARKS',
          'face_shape_label': null,
        }),
        200,
      );
    });
    final profile = await AnalysisService(client: client).analyse(
      endpoint: Uri.parse('http://10.0.2.2:8000/v1/profile'),
      bytes: Uint8List.fromList(utf8.encode('{"landmarks":true}')),
    );
    expect(profile.failed, isTrue);
    expect(profile.errorCode, 'MISSING_LANDMARKS');
  });

  test('a rejected file explains the missing landmarks', () async {
    final client = MockClient((request) async {
      return http.Response(
        jsonEncode({'detail': 'missing core landmarks: nasion, menton'}),
        422,
      );
    });
    expect(
      () => AnalysisService(client: client).analyse(
        endpoint: Uri.parse('http://127.0.0.1:8000/v1/profile'),
        bytes: Uint8List.fromList([1]),
      ),
      throwsA(
        isA<AnalysisException>().having(
          (error) => error.message,
          'message',
          contains('missing points'),
        ),
      ),
    );
  });
}
