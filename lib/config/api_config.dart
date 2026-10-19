class ApiConfig {
  /// Base URL for the FastAPI backend server.
  /// 
  /// Usage guide:
  /// - Android Emulator: 'http://10.0.2.2:8000' (10.0.2.2 maps to host's localhost inside Android emulator)
  /// - Physical Android / iOS Devices: 'http://`LAPTOP_WIFI_IP`:8000' (e.g. 'http://192.168.1.100:8000')
  /// - iOS Simulator / Web / Desktop: 'http://localhost:8000' or 'http://127.0.0.1:8000'
  static const String baseUrl = 'http://10.0.2.2:8000';
}
