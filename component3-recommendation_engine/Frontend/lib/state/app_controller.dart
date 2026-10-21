import 'dart:convert';

import 'package:flutter/foundation.dart';

import '../config/api_config.dart';
import '../models/contracts.dart';
import '../services/recommendation_api.dart';

class SubmittedBundle {
  SubmittedBundle({
    required this.baseUrl,
    required this.request,
    required this.response,
    required this.signature,
  });

  final String baseUrl;
  final Map<String, dynamic> request;
  final RecommendationResponse response;
  final String signature;
}

class AppController extends ChangeNotifier {
  AppController({RecommendationApi? api}) : api = api ?? RecommendationApi();

  final RecommendationApi api;

  bool checking = false;
  bool ready = false;

  /// `checking`, `unreachable`, `notReady`, or `ready`.
  /// Ready is true only when the readiness payload says so.
  String connectionStatus = 'unreachable';
  String? connectionError;
  String? urlError;
  String? metadataBaseUrl;
  Map<String, dynamic>? readiness;
  Map<String, dynamic>? capabilities;
  Map<String, dynamic>? modelsInfo;
  List<StyleRecord> styles = const [];
  int maxTopN = 20;

  final profileText = <String, String>{
    'face_length_ratio': '',
    'jaw_width_ratio': '',
    'upper_width_ratio': '',
    'lower_face_ratio': '',
    'symmetry': '',
    'face_shape': 'oval',
    'jawline': 'soft',
    'forehead': 'medium',
    'hairline': 'straight',
    'gender': 'male',
  };
  final fieldErrors = <String, String>{};
  final confidenceText = <String, String>{
    for (final key in facialConfidenceKeys) key: '',
  };
  final confidenceErrors = <String, String>{};

  final categories = <String>{'hair', 'beard', 'grooming'};
  int topN = 3;
  bool? includeBeard;
  bool? facialHairAvailable = true;
  final excludedStyleIds = <String>{};
  String rankingMode = 'standard';
  bool confidenceSectionOpen = false;

  bool submitting = false;
  String? submitError;
  SubmittedBundle? lastResult;
  String? resultSignature;

  bool comparing = false;
  String? compareError;
  SubmittedBundle? compareStandard;
  SubmittedBundle? compareAware;
  String? compareSignature;

  int _generateToken = 0;
  int _compareToken = 0;
  int _connectionToken = 0;
  int formRevision = 0;

  bool get metadataCurrent =>
      metadataBaseUrl != null && metadataBaseUrl == api.baseUrl;

  Future<void> refreshConnection() async {
    final token = ++_connectionToken;
    final origin = api.baseUrl;
    checking = true;
    connectionStatus = 'checking';
    connectionError = null;
    notifyListeners();
    try {
      final live = await api.getJson('/health/live', baseUrl: origin);
      if (!_connectionCurrent(token, origin)) return;
      final service = live['service']?.toString();
      if (live['status'] != 'ok' || service != ApiConfig.serviceName) {
        _markUnreachable(
          'This URL is not the Component 3 style ranking API'
          '${service == null ? '' : ' ($service)'}.',
        );
        return;
      }
      readiness = await api.ready();
      if (!_connectionCurrent(token, origin)) return;
      ready = readiness?['ready'] == true;
      capabilities = await api.capabilities();
      modelsInfo = await api.modelsInfo();
      styles = await api.styles();
      maxTopN = 20;
      final schema = await api.inputSchema();
      final topLimits = schema['top_n_limits'];
      final maxValue = topLimits is Map ? topLimits['max'] : null;
      if (maxValue is num && maxValue >= 1) {
        maxTopN = maxValue.toInt();
      }
      if (topN > maxTopN) topN = maxTopN;
      if (topN < 1) topN = 1;
      metadataBaseUrl = origin;
      if (!ready) {
        connectionStatus = 'notReady';
        final diagnostics = readiness?['diagnostics'];
        connectionError = diagnostics is List && diagnostics.isNotEmpty
            ? 'The API is reachable but not ready. ${diagnostics.join(' ')}'
            : 'The API is reachable but not ready for recommendations.';
      } else {
        connectionStatus = 'ready';
        connectionError = null;
      }
    } on ApiException catch (error) {
      if (!_connectionCurrent(token, origin)) return;
      _markUnreachable(error.message);
    } catch (_) {
      if (!_connectionCurrent(token, origin)) return;
      _markUnreachable('Cannot reach the recommendation API at $origin.');
    } finally {
      if (token == _connectionToken) {
        checking = false;
        notifyListeners();
      }
    }
  }

  bool _connectionCurrent(int token, String origin) =>
      token == _connectionToken && api.baseUrl == origin;

  void _markUnreachable(String message) {
    ready = false;
    connectionStatus = 'unreachable';
    connectionError = message;
    readiness = null;
    capabilities = null;
    modelsInfo = null;
    styles = const [];
    metadataBaseUrl = null;
    maxTopN = 20;
  }

  /// Returns false when [value] is not a usable base URL.
  bool setBaseUrl(String value) {
    final error = ApiConfig.validateBaseUrl(value);
    if (error != null) {
      urlError = error;
      notifyListeners();
      return false;
    }
    final next = ApiConfig.normalize(value);
    urlError = null;
    if (next == api.baseUrl) {
      notifyListeners();
      return true;
    }
    api.baseUrl = next;
    _connectionToken++;
    _generateToken++;
    _compareToken++;
    submitting = false;
    comparing = false;
    _markUnreachable('Server changed. Checking $next.');
    notifyListeners();
    return true;
  }

  void setProfileField(String key, String value) {
    profileText[key] = value;
    fieldErrors.remove(key);
    notifyListeners();
  }

  void loadDemo(Map<String, Object> demo) {
    for (final entry in demo.entries) {
      profileText[entry.key] = entry.value.toString();
    }
    fieldErrors.clear();
    submitError = null;
    formRevision++;
    notifyListeners();
  }

  void resetProfile() {
    for (final key in profileText.keys) {
      profileText[key] = '';
    }
    profileText['face_shape'] = 'oval';
    profileText['jawline'] = 'soft';
    profileText['forehead'] = 'medium';
    profileText['hairline'] = 'straight';
    profileText['gender'] = 'male';
    fieldErrors.clear();
    submitError = null;
    formRevision++;
    notifyListeners();
  }

  void setTopN(int value) {
    topN = value.clamp(1, maxTopN).toInt();
    notifyListeners();
  }

  void setIncludeBeard(bool? value) {
    includeBeard = value;
    notifyListeners();
  }

  void setFacialHairAvailable(bool? value) {
    facialHairAvailable = value;
    notifyListeners();
  }

  void setRankingMode(String value) {
    rankingMode = value;
    if (value == 'confidence_aware') confidenceSectionOpen = true;
    notifyListeners();
  }

  void setConfidenceOpen(bool open) {
    confidenceSectionOpen = open;
    notifyListeners();
  }

  void toggleCategory(String category, bool selected) {
    if (selected) {
      categories.add(category);
    } else if (categories.length > 1) {
      categories.remove(category);
    }
    notifyListeners();
  }

  void setConfidence(String key, String value) {
    confidenceText[key] = value;
    confidenceErrors.remove(key);
    notifyListeners();
  }

  void applyConfidencePreset(double value, {String? onlyKey}) {
    confidenceSectionOpen = true;
    for (final key in facialConfidenceKeys) {
      confidenceText[key] = onlyKey == null || key == onlyKey
          ? value.toString()
          : (confidenceText[key]!.isEmpty ? '1.0' : confidenceText[key]!);
    }
    if (onlyKey != null) {
      for (final key in facialConfidenceKeys) {
        if (confidenceText[key]!.isEmpty) confidenceText[key] = '1.0';
      }
      confidenceText[onlyKey] = value.toString();
    }
    confidenceErrors.clear();
    formRevision++;
    notifyListeners();
  }

  void toggleExcluded(String styleId) {
    if (excludedStyleIds.contains(styleId)) {
      excludedStyleIds.remove(styleId);
    } else {
      excludedStyleIds.add(styleId);
    }
    notifyListeners();
  }

  /// Future Component 2 can call this with the same profile object.
  void applyUpstreamProfile(Map<String, Object?> profile) {
    for (final entry in profile.entries) {
      if (profileText.containsKey(entry.key) && entry.value != null) {
        profileText[entry.key] = entry.value.toString();
      }
    }
    formRevision++;
    notifyListeners();
  }

  Map<String, Object>? _profileOrErrors() {
    fieldErrors
      ..clear()
      ..addAll(ProfileValidation.validateProfile(profileText));
    if (fieldErrors.isNotEmpty) return null;
    return {
      'face_length_ratio': double.parse(profileText['face_length_ratio']!),
      'jaw_width_ratio': double.parse(profileText['jaw_width_ratio']!),
      'upper_width_ratio': double.parse(profileText['upper_width_ratio']!),
      'lower_face_ratio': double.parse(profileText['lower_face_ratio']!),
      'symmetry': double.parse(profileText['symmetry']!),
      'face_shape': profileText['face_shape']!,
      'jawline': profileText['jawline']!,
      'forehead': profileText['forehead']!,
      'hairline': profileText['hairline']!,
      'gender': profileText['gender']!,
    };
  }

  Map<String, double>? _confidenceOrErrors() {
    confidenceErrors
      ..clear()
      ..addAll(
        ProfileValidation.validateConfidence(
          rankingMode: rankingMode,
          confidenceText: confidenceText,
          confidenceEnabled:
              confidenceSectionOpen ||
              confidenceText.values.any((value) => value.trim().isNotEmpty),
        ),
      );
    if (confidenceErrors.isNotEmpty) return null;
    final parsed = <String, double>{};
    for (final key in facialConfidenceKeys) {
      final raw = confidenceText[key]?.trim() ?? '';
      if (raw.isEmpty) continue;
      parsed[key] = double.parse(raw);
    }
    return parsed.isEmpty ? null : parsed;
  }

  RecommendationRequestBody? buildRequest({String? rankingModeOverride}) {
    final profile = _profileOrErrors();
    final confidence = _confidenceOrErrors();
    if (profile == null || confidenceErrors.isNotEmpty) {
      notifyListeners();
      return null;
    }
    if (categories.isEmpty) {
      fieldErrors['_categories'] = 'Select at least one category.';
      notifyListeners();
      return null;
    }
    final mode = rankingModeOverride ?? rankingMode;
    if (mode == 'confidence_aware' &&
        (confidence == null ||
            confidence.length != facialConfidenceKeys.length)) {
      confidenceErrors['_form'] =
          'Confidence-aware mode needs all nine facial confidence values.';
      notifyListeners();
      return null;
    }
    return RecommendationRequestBody(
      profile: profile,
      categories: categories.toList(),
      topN: topN,
      includeBeard: includeBeard,
      facialHairAvailable: facialHairAvailable,
      excludedStyleIds: excludedStyleIds.toList()..sort(),
      attributeConfidence: confidence,
      rankingMode: mode,
      confidenceSource: confidence == null ? 'unspecified' : 'manual',
    );
  }

  void _applyApiFieldErrors(ApiException error) {
    if (error.profileErrors.isNotEmpty) {
      fieldErrors.addAll(error.profileErrors);
    }
    if (error.confidenceErrors.isNotEmpty) {
      confidenceErrors.addAll(error.confidenceErrors);
      confidenceSectionOpen = true;
    }
  }

  Future<void> generate() async {
    final request = buildRequest();
    if (request == null) return;
    final token = ++_generateToken;
    final origin = api.baseUrl;
    submitting = true;
    submitError = null;
    notifyListeners();
    try {
      final response = await api.recommend(request, baseUrl: origin);
      if (token != _generateToken || api.baseUrl != origin) return;
      final body = request.toJson();
      lastResult = SubmittedBundle(
        baseUrl: origin,
        request: body,
        response: response,
        signature: jsonEncode(body),
      );
      resultSignature = lastResult!.signature;
    } on ApiException catch (error) {
      if (token != _generateToken || api.baseUrl != origin) return;
      submitError = error.message;
      _applyApiFieldErrors(error);
    } finally {
      if (token == _generateToken) {
        submitting = false;
        notifyListeners();
      }
    }
  }

  Future<void> compareModes() async {
    final standard = buildRequest(rankingModeOverride: 'standard');
    final aware = buildRequest(rankingModeOverride: 'confidence_aware');
    if (standard == null || aware == null) {
      compareError =
          'Comparison needs a valid profile and all nine facial confidence values.';
      notifyListeners();
      return;
    }
    final standardJson = standard.toJson();
    final awareJson = aware.toJson();
    if (!_sameComparisonSnapshot(standardJson, awareJson)) {
      compareError =
          'The two comparison requests did not share the same profile snapshot.';
      notifyListeners();
      return;
    }
    final token = ++_compareToken;
    final origin = api.baseUrl;
    comparing = true;
    compareError = null;
    compareStandard = null;
    compareAware = null;
    compareSignature = null;
    notifyListeners();
    RecommendationResponse? standardResponse;
    RecommendationResponse? awareResponse;
    final failures = <String>[];
    try {
      try {
        standardResponse = await api.recommend(standard, baseUrl: origin);
      } on ApiException catch (error) {
        failures.add('Standard request failed: ${error.message}');
      }
      if (token != _compareToken || api.baseUrl != origin) return;
      try {
        awareResponse = await api.recommend(aware, baseUrl: origin);
      } on ApiException catch (error) {
        failures.add('Confidence-aware request failed: ${error.message}');
      }
      if (token != _compareToken || api.baseUrl != origin) return;
      if (standardResponse != null) {
        compareStandard = SubmittedBundle(
          baseUrl: origin,
          request: standardJson,
          response: standardResponse,
          signature: jsonEncode(standardJson),
        );
      }
      if (awareResponse != null) {
        compareAware = SubmittedBundle(
          baseUrl: origin,
          request: awareJson,
          response: awareResponse,
          signature: jsonEncode(awareJson),
        );
      }
      if (standardResponse != null && awareResponse != null) {
        compareSignature = jsonEncode({
          'profile': standardJson['profile'],
          'categories': standardJson['categories'],
          'top_n': standardJson['top_n'],
          'preferences': standardJson['preferences'],
          'confidence': awareJson['attribute_confidence'],
        });
      }
      compareError = failures.isEmpty ? null : failures.join('\n');
    } finally {
      if (token == _compareToken) {
        comparing = false;
        notifyListeners();
      }
    }
  }

  bool _sameComparisonSnapshot(
    Map<String, dynamic> standard,
    Map<String, dynamic> aware,
  ) {
    return jsonEncode(standard['profile']) == jsonEncode(aware['profile']) &&
        jsonEncode(standard['categories']) == jsonEncode(aware['categories']) &&
        standard['top_n'] == aware['top_n'] &&
        jsonEncode(standard['preferences']) ==
            jsonEncode(aware['preferences']) &&
        jsonEncode(standard['attribute_confidence']) ==
            jsonEncode(aware['attribute_confidence']);
  }

  bool get resultsAreCurrent =>
      lastResult != null &&
      lastResult!.baseUrl == api.baseUrl &&
      resultSignature == silentRequestJson();

  bool get comparisonIsCurrent =>
      compareStandard != null &&
      compareAware != null &&
      compareStandard!.baseUrl == api.baseUrl &&
      compareAware!.baseUrl == api.baseUrl &&
      compareSignature != null &&
      compareSignature == silentComparisonJson();

  String? silentRequestJson({String rankingModeOverride = ''}) {
    final body = _silentBody(rankingModeOverride: rankingModeOverride);
    if (body == null) return null;
    return jsonEncode(body);
  }

  String? silentComparisonJson() {
    final standard = _silentBody(rankingModeOverride: 'standard');
    final aware = _silentBody(rankingModeOverride: 'confidence_aware');
    if (standard == null || aware == null) return null;
    return jsonEncode({
      'profile': standard['profile'],
      'categories': standard['categories'],
      'top_n': standard['top_n'],
      'preferences': standard['preferences'],
      'confidence': aware['attribute_confidence'],
    });
  }

  Map<String, dynamic>? _silentBody({String rankingModeOverride = ''}) {
    if (ProfileValidation.validateProfile(profileText).isNotEmpty) return null;
    final mode = rankingModeOverride.isEmpty
        ? rankingMode
        : rankingModeOverride;
    final confidenceErrorsNow = ProfileValidation.validateConfidence(
      rankingMode: mode,
      confidenceText: confidenceText,
      confidenceEnabled:
          confidenceSectionOpen ||
          confidenceText.values.any((value) => value.trim().isNotEmpty),
    );
    if (confidenceErrorsNow.isNotEmpty) return null;
    final confidence = <String, double>{};
    for (final key in facialConfidenceKeys) {
      final raw = confidenceText[key]?.trim() ?? '';
      if (raw.isEmpty) continue;
      confidence[key] = double.parse(raw);
    }
    if (mode == 'confidence_aware' &&
        confidence.length != facialConfidenceKeys.length) {
      return null;
    }
    return RecommendationRequestBody(
      profile: {
        'face_length_ratio': double.parse(profileText['face_length_ratio']!),
        'jaw_width_ratio': double.parse(profileText['jaw_width_ratio']!),
        'upper_width_ratio': double.parse(profileText['upper_width_ratio']!),
        'lower_face_ratio': double.parse(profileText['lower_face_ratio']!),
        'symmetry': double.parse(profileText['symmetry']!),
        'face_shape': profileText['face_shape']!,
        'jawline': profileText['jawline']!,
        'forehead': profileText['forehead']!,
        'hairline': profileText['hairline']!,
        'gender': profileText['gender']!,
      },
      categories: categories.toList(),
      topN: topN,
      includeBeard: includeBeard,
      facialHairAvailable: facialHairAvailable,
      excludedStyleIds: excludedStyleIds.toList()..sort(),
      attributeConfidence: confidence.isEmpty ? null : confidence,
      rankingMode: mode,
      confidenceSource: confidence.isEmpty ? 'unspecified' : 'manual',
    ).toJson();
  }
}
