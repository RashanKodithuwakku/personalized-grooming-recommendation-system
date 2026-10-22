import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:http/http.dart' as http;

import '../models/facial_profile.dart';

class AnalysisException implements Exception {
  AnalysisException(this.message);

  final String message;

  @override
  String toString() => message;
}

class AnalysisService {
  AnalysisService({http.Client? client}) : _client = client ?? http.Client();

  final http.Client _client;

  Future<FacialProfile> analyse({
    required Uri endpoint,
    required Uint8List bytes,
  }) async {
    final http.Response response;
    try {
      response = await _client
          .post(
            endpoint,
            headers: const {
              'Content-Type': 'application/json',
              'Accept': 'application/json',
            },
            body: bytes,
          )
          .timeout(const Duration(seconds: 40));
    } on TimeoutException {
      throw AnalysisException(
        'The server took too long to answer. Check that it is running, then try again.',
      );
    } on http.ClientException {
      throw AnalysisException(
        'Nothing answered at ${endpoint.host}. Start the face-shape service on your computer, then try again.',
      );
    }

    if (response.statusCode >= 200 && response.statusCode < 300) {
      final decoded = jsonDecode(utf8.decode(response.bodyBytes));
      if (decoded is! Map) {
        throw AnalysisException('The service returned something unexpected.');
      }
      return FacialProfile.fromJson(Map<String, dynamic>.from(decoded));
    }

    throw AnalysisException(_messageForStatus(response.statusCode, response.body));
  }
}

String _messageForStatus(int code, String body) {
  if (code == 422) {
    final detail = _detail(body);
    if (detail != null) return detail;
    return 'This JSON is missing landmarks the reading needs.';
  }
  if (code >= 500) {
    return 'The analysis service had a problem finishing this reading.';
  }
  return 'The analysis service returned an unexpected response ($code).';
}

String? _detail(String body) {
  try {
    final decoded = jsonDecode(body);
    if (decoded is Map && decoded['detail'] is String) {
      return _plainDetail(decoded['detail'] as String);
    }
  } on FormatException {
    return null;
  }
  return null;
}

String _plainDetail(String detail) {
  final lower = detail.toLowerCase();
  if (lower.contains('missing') && lower.contains('landmark')) {
    return 'This file is missing points the reading needs, such as the chin, cheeks, or jaw corners.';
  }
  if (detail.length > 180) {
    return 'This file does not match the landmark format the service expects.';
  }
  return detail;
}
