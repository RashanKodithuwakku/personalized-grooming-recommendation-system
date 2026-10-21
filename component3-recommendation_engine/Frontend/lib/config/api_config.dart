import 'package:flutter/foundation.dart';

/// API base URL for the Component 3 style-ranking backend.
///
/// Override at build/run time:
/// `flutter run --dart-define=API_BASE_URL=http://127.0.0.1:8010`
///
/// Defaults:
/// - Windows, desktop, and web on this PC: `http://127.0.0.1:8010`
/// - Android emulator: `http://10.0.2.2:8010`
/// - Physical phone: set the PC LAN address on port 8010 in the app bar.
///   `localhost` on a phone is the phone, not the development machine.
class ApiConfig {
  static const String serviceName = 'Style Recommendation and Ranking Engine';
  static const int componentPort = 8010;

  static const String _defined = String.fromEnvironment('API_BASE_URL');

  static String get baseUrl {
    if (_defined.trim().isNotEmpty) return normalize(_defined);
    if (!kIsWeb && defaultTargetPlatform == TargetPlatform.android) {
      return 'http://10.0.2.2:$componentPort';
    }
    return 'http://127.0.0.1:$componentPort';
  }

  static String normalize(String raw) {
    var value = raw.trim();
    while (value.endsWith('/')) {
      value = value.substring(0, value.length - 1);
    }
    return value;
  }

  /// Returns an error message when [raw] is not an absolute http(s) URL.
  static String? validateBaseUrl(String raw) {
    final value = normalize(raw);
    final uri = Uri.tryParse(value);
    if (uri == null ||
        !uri.hasScheme ||
        (uri.scheme != 'http' && uri.scheme != 'https') ||
        uri.host.isEmpty ||
        uri.hasFragment) {
      return 'Enter a full http or https URL, such as http://127.0.0.1:$componentPort.';
    }
    return null;
  }
}
