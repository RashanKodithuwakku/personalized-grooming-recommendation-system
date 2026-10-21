import 'dart:convert';

import 'package:http/http.dart' as http;

import '../config/api_config.dart';
import '../models/contracts.dart';

class ApiException implements Exception {
  ApiException(
    this.message, {
    this.statusCode,
    this.profileErrors = const {},
    this.confidenceErrors = const {},
  });

  final String message;
  final int? statusCode;
  final Map<String, String> profileErrors;
  final Map<String, String> confidenceErrors;

  @override
  String toString() => message;
}

class RecommendationApi {
  RecommendationApi({http.Client? client, String? baseUrl})
    : _client = client ?? http.Client(),
      baseUrl = ApiConfig.normalize(baseUrl ?? ApiConfig.baseUrl);

  final http.Client _client;
  String baseUrl;

  void setBaseUrl(String value) {
    final error = ApiConfig.validateBaseUrl(value);
    if (error != null) {
      throw ApiException(error);
    }
    baseUrl = ApiConfig.normalize(value);
  }

  Future<Map<String, dynamic>> getJson(String path, {String? baseUrl}) async {
    final root = baseUrl ?? this.baseUrl;
    final response = await _send(
      () => _client.get(Uri.parse('$root$path')),
      root: root,
    );
    return _decodeMap(response);
  }

  Future<Map<String, dynamic>> postJson(
    String path,
    Map<String, dynamic> body, {
    String? baseUrl,
  }) async {
    final root = baseUrl ?? this.baseUrl;
    final response = await _send(
      () => _client.post(
        Uri.parse('$root$path'),
        headers: const {'Content-Type': 'application/json'},
        body: jsonEncode(body),
      ),
      root: root,
    );
    return _decodeMap(response);
  }

  Future<bool> isLive() async {
    final body = await getJson('/health/live');
    return body['status'] == 'ok';
  }

  Future<Map<String, dynamic>> ready() => getJson('/health/ready');

  Future<Map<String, dynamic>> capabilities() =>
      getJson('/api/v1/capabilities');

  Future<Map<String, dynamic>> inputSchema() => getJson('/api/v1/input-schema');

  Future<List<StyleRecord>> styles() async {
    final body = await getJson('/api/v1/styles');
    final items = (body['styles'] as List?) ?? const [];
    return items
        .map((e) => StyleRecord.fromJson((e as Map).cast<String, dynamic>()))
        .toList();
  }

  Future<Map<String, dynamic>> modelsInfo() => getJson('/api/v1/models/info');

  Future<RecommendationResponse> recommend(
    RecommendationRequestBody request, {
    String? baseUrl,
  }) async {
    final raw = await postJson(
      '/api/v1/recommendations',
      request.toJson(),
      baseUrl: baseUrl,
    );
    return RecommendationResponse.fromJson(raw);
  }

  Future<http.Response> _send(
    Future<http.Response> Function() call, {
    required String root,
  }) async {
    try {
      final response = await call().timeout(const Duration(seconds: 30));
      if (response.statusCode >= 200 && response.statusCode < 300) {
        return response;
      }
      throw _exceptionFor(response);
    } on ApiException {
      rethrow;
    } catch (_) {
      throw ApiException(
        'Cannot reach the recommendation API at $root. '
        'Start the Component 3 backend and check the base URL, then retry.',
      );
    }
  }

  ApiException _exceptionFor(http.Response response) {
    final parsed = _parseDetail(response);
    return ApiException(
      parsed.message,
      statusCode: response.statusCode,
      profileErrors: parsed.profileErrors,
      confidenceErrors: parsed.confidenceErrors,
    );
  }

  _ParsedDetail _parseDetail(http.Response response) {
    try {
      final decoded = jsonDecode(response.body);
      if (decoded is Map && decoded['detail'] != null) {
        return _detailFrom(decoded['detail'], response.statusCode);
      }
    } catch (_) {}
    return _ParsedDetail('Request failed (${response.statusCode}).');
  }

  _ParsedDetail _detailFrom(Object? detail, int statusCode) {
    if (detail is String && detail.trim().isNotEmpty) {
      return _ParsedDetail(detail.trim());
    }
    final profileErrors = <String, String>{};
    final confidenceErrors = <String, String>{};
    final messages = <String>[];
    if (detail is List) {
      for (final item in detail) {
        if (item is! Map) continue;
        final message = item['msg']?.toString().trim();
        if (message == null || message.isEmpty) continue;
        messages.add(message);
        final loc = item['loc'];
        if (loc is! List || loc.isEmpty) continue;
        final parts = loc.map((part) => part.toString()).toList();
        final field = parts.last;
        if (parts.contains('attribute_confidence') &&
            facialConfidenceKeys.contains(field)) {
          confidenceErrors[field] = message;
        } else if (parts.contains('profile') &&
            _profileFields.contains(field)) {
          profileErrors[field] = message;
        }
      }
    }
    final summary = messages.isEmpty
        ? 'Request was rejected ($statusCode). Check the entered values.'
        : messages.toSet().join(' ');
    return _ParsedDetail(
      summary,
      profileErrors: profileErrors,
      confidenceErrors: confidenceErrors,
    );
  }

  Map<String, dynamic> _decodeMap(http.Response response) {
    final decoded = jsonDecode(response.body);
    if (decoded is Map<String, dynamic>) return decoded;
    if (decoded is Map) return decoded.cast<String, dynamic>();
    throw ApiException('Unexpected response from the API.');
  }
}

class _ParsedDetail {
  _ParsedDetail(
    this.message, {
    this.profileErrors = const {},
    this.confidenceErrors = const {},
  });

  final String message;
  final Map<String, String> profileErrors;
  final Map<String, String> confidenceErrors;
}

const _profileFields = {
  'face_length_ratio',
  'jaw_width_ratio',
  'upper_width_ratio',
  'lower_face_ratio',
  'symmetry',
  'face_shape',
  'jawline',
  'forehead',
  'hairline',
  'gender',
};
