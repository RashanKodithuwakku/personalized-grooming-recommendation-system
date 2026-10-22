import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:groom_app/main.dart';
import 'package:groom_app/models/facial_profile.dart';
import 'package:groom_app/models/landmark_file.dart';
import 'package:groom_app/screens/analyzing_screen.dart';
import 'package:groom_app/screens/face_type_screen.dart';
import 'package:groom_app/theme/groom_theme.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

void main() {
  testWidgets('the opening screen asks for a landmark file', (tester) async {
    await tester.pumpWidget(const GroomApp());
    expect(find.text('Bring a\nlandmark file.'), findsOneWidget);
    expect(find.text('Read this face'), findsOneWidget);
    expect(find.text('Choose a JSON file'), findsOneWidget);
  });

  testWidgets('face shape and harmony screens explain the scores', (tester) async {
    _phone(tester);
    final profile = _sampleProfile();
    await tester.pumpWidget(
      MaterialApp(
        theme: buildGroomTheme(),
        home: FaceTypeScreen(profile: profile, fileName: 'sample.json'),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.text('Oval'), findsWidgets);
    expect(find.text('86%'), findsWidgets);
    expect(find.textContaining('softly rounded jaw'), findsOneWidget);
    expect(find.textContaining('do not need to add up to 100'), findsOneWidget);

    await tester.tap(find.text('See balance and symmetry'));
    await tester.pumpAndSettle();

    expect(find.text('Vertical balance'), findsOneWidget);
    expect(find.text('Horizontal balance'), findsOneWidget);
    expect(find.text('Symmetry'), findsOneWidget);
    expect(find.text('Overall reading'), findsOneWidget);
    expect(find.textContaining('upper, middle, and lower'), findsOneWidget);
    expect(find.textContaining('five bands'), findsOneWidget);
    expect(find.textContaining('left and right sides'), findsOneWidget);
    expect(find.text('82'), findsWidgets);
  });

  testWidgets('a finished service response opens the face shape', (tester) async {
    _phone(tester);
    await tester.pumpWidget(
      MaterialApp(
        theme: buildGroomTheme(),
        home: AnalyzingScreen(
          file: LandmarkFile(name: 'sample.json', bytes: Uint8List.fromList(utf8.encode('{}'))),
          baseUrl: 'http://10.0.2.2:8000',
          minimumVisible: Duration.zero,
          client: MockClient((request) async {
            expect(request.url.path, '/v1/profile');
            return http.Response(jsonEncode(_sampleJson()), 200);
          }),
        ),
      ),
    );
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 50));
    await tester.pump(const Duration(milliseconds: 500));
    await tester.pumpAndSettle();
    expect(find.text('Oval'), findsWidgets);
    expect(find.text('See balance and symmetry'), findsOneWidget);
  });
}

void _phone(WidgetTester tester) {
  tester.view.physicalSize = const Size(1170, 2532);
  tester.view.devicePixelRatio = 3;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
}

FacialProfile _sampleProfile() => FacialProfile.fromJson(_sampleJson());

Map<String, dynamic> _sampleJson() {
  return {
    'status': 'ok',
    'face_shape_label': 'oval',
    'face_shape_class': 'Mesoprosopic',
    'face_shape_confidence': {
      'oval': 0.86,
      'round': 0.22,
      'square': 0.08,
      'oblong': 0.14,
      'heart': 0.05,
      'diamond': 0.03,
    },
    'jawline_category': 'rounded',
    'symmetry_score': 0.91,
    'vertical_balance_score': 0.82,
    'horizontal_balance_score': 0.76,
    'balance_score': 0.79,
    'grooming_suitability_index': 84.5,
    'processing_notes': [],
  };
}
