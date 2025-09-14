import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'dart:io';

class ApiConfig {
  // Endpoints - using standard FastAPI patterns
  static const String healthEndpoint = '/health';
  static const String submitTransactionEndpoint = '/v1/tx';
  static const String listTransactionsEndpoint = '/v1/tx/list';
  static const String anchorEndpoint = '/v1/anchor';
  static const String overrideEndpoint = '/v1/override';
  
  // Authentication endpoints
  static const String signupEndpoint = '/auth/signup';
  static const String loginEndpoint = '/auth/login';
  static const String logoutEndpoint = '/auth/logout';
  static const String profileEndpoint = '/auth/profile';

  /// Get the override URL
  static String getOverrideUrl() => '$baseUrl$overrideEndpoint';
  
  /// Optional admin API key for override operations
  static String? get adminApiKey {
    // First try --dart-define
    const dartDefineKey = String.fromEnvironment('ADMIN_API_KEY');
    if (dartDefineKey.isNotEmpty) {
      return dartDefineKey;
    }
    
    // Then try .env file
    return dotenv.env['ADMIN_API_KEY'];
  }

  /// Get the base URL from environment
  static String get baseUrl {
    // First try --dart-define
    const dartDefineUrl = String.fromEnvironment('API_URL');
    if (dartDefineUrl.isNotEmpty) {
      print('[ApiConfig] Using --dart-define API_URL: $dartDefineUrl');
      return dartDefineUrl;
    }
    
    // Then try .env file
    final envUrl = dotenv.env['API_URL'];
    if (envUrl != null && envUrl.isNotEmpty) {
      print('[ApiConfig] Using .env API_URL: $envUrl');
      return envUrl;
    }
    
    // Fallback based on platform
    final fallbackUrl = _getFallbackUrl();
    print('[ApiConfig] Using fallback URL: $fallbackUrl');
    return fallbackUrl;
  }

  /// Get full URL for an endpoint
  static String getUrl(String endpoint) {
    final fullUrl = '$baseUrl$endpoint';
    print('[ApiConfig] Generated URL: $fullUrl');
    return fullUrl;
  }

  /// Get current environment description
  static String getCurrentEnvironment() {
    final url = baseUrl;
    if (url.contains('localhost') || url.contains('127.0.0.1')) {
      return 'Local Development';
    } else if (url.contains('10.0.2.2')) {
      return 'Android Emulator';
    } else if (url.startsWith('http://10.') || url.startsWith('http://192.168.')) {
      return 'Physical Device (LAN)';
    } else if (url.contains('staging')) {
      return 'Staging';
    } else if (url.contains('prod')) {
      return 'Production';
    } else {
      return 'Custom Environment';
    }
  }

  /// Platform-specific fallback URLs
  static String _getFallbackUrl() {
    if (Platform.isAndroid) {
      // Check if running on emulator
      return 'http://10.0.2.2:8000';  // Android emulator host mapping
    } else if (Platform.isIOS) {
      return 'http://localhost:8000';  // iOS simulator
    } else {
      return 'http://localhost:8000';  // Default for other platforms
    }
  }

  /// Validate if URL is reachable (basic format check)
  static bool isValidUrl(String url) {
    try {
      final uri = Uri.parse(url);
      return uri.hasScheme && (uri.hasPort || uri.host.isNotEmpty);
    } catch (e) {
      return false;
    }
  }

  /// Get timeout duration for HTTP requests
  static Duration get requestTimeout => const Duration(seconds: 30);

  /// Get retry count for failed requests
  static int get maxRetries => 3;
}