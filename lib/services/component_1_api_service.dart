import 'dart:convert';
import 'dart:io';

import 'package:http/http.dart' as http;

import '../config/api_config.dart';
import '../models/analysis_result.dart';

/// Sends the selected image to POST /analyze_face and returns a typed
/// [AnalysisResult].
///
/// On network error or non-200 response the method returns an
/// [AnalysisResult] with is_success = false and a descriptive message
/// so the UI can show actionable feedback without leaking stack traces.
class Component1ApiService {
  Future<AnalysisResult?> analyzeFace(File imageFile) async {
    try {
      final uri = Uri.parse('${ApiConfig.baseUrl}/analyze_face');

      final request = http.MultipartRequest('POST', uri);
      request.files.add(
        await http.MultipartFile.fromPath('image', imageFile.path),
      );

      final streamedResponse = await request.send().timeout(
        const Duration(seconds: 60),
        onTimeout: () => throw const SocketException('Request timed out'),
      );
      final response = await http.Response.fromStream(streamedResponse);

      if (response.statusCode == 200) {
        final Map<String, dynamic> jsonMap =
            json.decode(response.body) as Map<String, dynamic>;
        return AnalysisResult.fromJson(jsonMap);
      } else {
        // Parse the backend error body; it may contain a "detail" or "message" key.
        String reason = 'Server error (${response.statusCode}).';
        try {
          final body = json.decode(response.body) as Map<String, dynamic>;
          reason = (body['detail'] as String?) ??
              (body['message'] as String?) ??
              reason;
        } catch (_) {}

        return AnalysisResult(
          hairlineResult: '',
          hairlineConfidence: 0.0,
          jawlineResult: '',
          jawlineConfidence: 0.0,
          message: reason,
          isSuccess: false,
        );
      }
    } on SocketException catch (e) {
      return AnalysisResult(
        hairlineResult: '',
        hairlineConfidence: 0.0,
        jawlineResult: '',
        jawlineConfidence: 0.0,
        message: 'Cannot reach the server. Check your connection. ($e)',
        isSuccess: false,
      );
    } catch (e) {
      return AnalysisResult(
        hairlineResult: '',
        hairlineConfidence: 0.0,
        jawlineResult: '',
        jawlineConfidence: 0.0,
        message: 'Unexpected error while sending the image: $e',
        isSuccess: false,
      );
    }
  }
}
