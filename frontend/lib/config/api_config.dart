import 'package:flutter/foundation.dart';

/// The emulator reaches the computer running the Python service at 10.0.2.2.
String defaultApiBaseUrl() {
  if (kIsWeb) return 'http://127.0.0.1:8000';
  if (defaultTargetPlatform == TargetPlatform.android) {
    return 'http://10.0.2.2:8000';
  }
  return 'http://127.0.0.1:8000';
}

String? validateBaseUrl(String raw) {
  final trimmed = raw.trim();
  final uri = Uri.tryParse(trimmed);
  final scheme = uri?.scheme;
  if (uri == null ||
      (scheme != 'http' && scheme != 'https') ||
      uri.host.isEmpty) {
    return 'Enter a full address, such as http://10.0.2.2:8000';
  }
  return null;
}

Uri profileUri(String baseUrl) {
  final problem = validateBaseUrl(baseUrl);
  if (problem != null) {
    throw FormatException(problem);
  }
  final uri = Uri.parse(baseUrl.trim());
  return Uri(
    scheme: uri.scheme,
    host: uri.host,
    port: uri.hasPort ? uri.port : null,
    path: '/v1/profile',
  );
}
