import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../config/api_config.dart';
import '../models/transaction.dart';
import 'storage_service.dart';

// Riverpod provider for ApiService
final apiServiceProvider = Provider<ApiService>((ref) => ApiService());

class ApiService {
  static final ApiService _instance = ApiService._internal();
  factory ApiService() => _instance;
  ApiService._internal();

  String? _authToken;

  /// Set authentication token for API requests
  void setAuthToken(String? token) {
    _authToken = token;
  }

  /// Build headers with authentication and admin key
  Future<Map<String, String>> _buildHeaders() async {
    final headers = {'Content-Type': 'application/json'};
    
    // Get token from secure storage
    final storageService = StorageService();
    final token = await storageService.getToken();
    if (token != null && token.isNotEmpty) {
      headers['Authorization'] = 'Bearer $token';
    }
    
    // Add admin API key if available
    final adminKey = ApiConfig.adminApiKey;
    if (adminKey != null && adminKey.isNotEmpty) {
      headers['X-Admin-API-Key'] = adminKey;
    }
    
    return headers;
  }

  /// Enhanced response processing with better error handling
  Map<String, dynamic> _processResponse(http.Response response) {
    print('[ApiService] Response ${response.statusCode}: ${response.body}');
    
    if (response.statusCode == 200 || response.statusCode == 201) {
      return jsonDecode(response.body);
    } else if (response.statusCode == 401) {
      throw AuthenticationException('Authentication failed');
    } else if (response.statusCode == 403) {
      throw AuthorizationException('Access denied');
    } else if (response.statusCode == 409) {
      final body = jsonDecode(response.body);
      final errorMessage = body['error']?['detail'] ?? 'Conflict occurred';
      throw ConflictException(errorMessage);
    } else if (response.statusCode == 422) {
      final body = jsonDecode(response.body);
      final errorMessage = body['detail']?[0]?['msg'] ?? 'Validation failed';
      throw ValidationException(errorMessage);
    } else {
      final body = jsonDecode(response.body);
      final errorMessage = body['error']?['detail'] ?? 'Request failed';
      throw ApiException('Error ${response.statusCode}: $errorMessage');
    }
  }

  // ==================== AUTHENTICATION METHODS ==================== //

  /// User signup
  Future<User> signup({
    required String username,
    required String email,
    required String password,
  }) async {
    final url = Uri.parse(ApiConfig.getUrl('/v1/users/signup'));
    final payload = {
      'username': username,
      'email': email,
      'password': password,
    };
    
    print('[ApiService] POST $url');
    print('[ApiService] Payload: ${jsonEncode(payload)}');
    
    final response = await http.post(
      url,
      headers: await _buildHeaders(),
      body: jsonEncode(payload),
    ).timeout(ApiConfig.requestTimeout);
    
    final data = _processResponse(response);
    
    // Store the token for future requests
    if (data['token'] != null) {
      setAuthToken(data['token']);
    }
    
    return User.fromJson(data);
  }

  /// User login - returns User object with token
  Future<User> login({
    required String email,
    required String password,
  }) async {
    final url = Uri.parse(ApiConfig.getUrl('/v1/users/login'));
    final payload = {
      'email': email,
      'password': password,
    };
    
    print('[ApiService] POST $url');
    print('[ApiService] Payload: ${jsonEncode({'email': email, 'password': '***'})}');
    
    final response = await http.post(
      url,
      headers: await _buildHeaders(),
      body: jsonEncode(payload),
    ).timeout(ApiConfig.requestTimeout);
    
    final data = _processResponse(response);
    
    // Store the token for future requests
    if (data['token'] != null) {
      setAuthToken(data['token']);
    }
    
    return User.fromJson(data);
  }

  /// Get current user profile
  Future<User> getProfile() async {
    final url = Uri.parse(ApiConfig.getUrl('/v1/users/me'));
    print('[ApiService] GET $url');
    
    final response = await http.get(
      url,
      headers: await _buildHeaders(),
    ).timeout(ApiConfig.requestTimeout);
    
    final data = _processResponse(response);
    
    // Add current token to user data since profile endpoint doesn't return token
    data['token'] = _authToken ?? '';
    
    return User.fromJson(data);
  }

  /// Logout - clear token
  Future<void> logout() async {
    setAuthToken(null);
  }

  /// Check if user is authenticated
  Future<bool> isAuthenticated() async {
    try {
      if (_authToken == null) return false;
      
      // Verify token by making a profile request
      await getProfile();
      return true;
    } catch (e) {
      setAuthToken(null);
      return false;
    }
  }

  Future<Map<String, dynamic>> getHealth() async {
    final url = Uri.parse(ApiConfig.getUrl(ApiConfig.healthEndpoint));
    print('[ApiService] GET $url');
    
    final response = await http.get(
      url, 
      headers: await _buildHeaders()
    ).timeout(ApiConfig.requestTimeout);
    
    print('[ApiService] GET $url -> ${response.statusCode}');
    print('[ApiService] Body: ${response.body}');
    
    return _processResponse(response);
  }

  Future<Map<String, dynamic>> submitTransaction(Map<String, dynamic> payload) async {
    final url = Uri.parse(ApiConfig.getUrl(ApiConfig.submitTransactionEndpoint));
    print('[ApiService] POST $url');
    print('[ApiService] Payload: ${jsonEncode(payload)}');
    
    final response = await http.post(
      url,
      headers: await _buildHeaders(),
      body: jsonEncode(payload),
    ).timeout(ApiConfig.requestTimeout);
    
    print('[ApiService] POST $url -> ${response.statusCode}');
    print('[ApiService] Body: ${response.body}');
    
    return _processResponse(response);
  }

  Future<List<Transaction>> listTransactions({int page = 1, int perPage = 20}) async {
    final url = Uri.parse(ApiConfig.getUrl(ApiConfig.listTransactionsEndpoint));
    print('[ApiService] GET $url (page=$page, perPage=$perPage)');
    
    final response = await http.get(
      url,
      headers: await _buildHeaders(),
    ).timeout(ApiConfig.requestTimeout);
    
    print('[ApiService] GET $url -> ${response.statusCode}');
    print('[ApiService] Body: ${response.body}');
    
    if (response.statusCode != 200) {
      throw Exception('listTransactions failed: ${response.statusCode} ${response.body}');
    }

    final responseRaw = response.body;
    print('[TransactionsList] Raw response: $responseRaw');

    final body = jsonDecode(responseRaw);
    List<dynamic> transactionData = [];
    
    // Handle both array response and object with transactions array
    if (body is List) {
      // Backend returns array directly at top-level
      transactionData = body;
      print('[ApiService] Found direct array with ${transactionData.length} items');
    } else if (body is Map && body.containsKey('transactions')) {
      // Backend returns object with transactions array
      transactionData = body['transactions'] as List<dynamic>;
      final total = body['total'] ?? transactionData.length;
      final currentPage = body['page'] ?? page;
      print('[ApiService] Found transactions array with ${transactionData.length} items (total: $total, page: $currentPage)');
    } else {
      print('[ApiService] Unexpected response format: ${body.runtimeType}');
      throw Exception('Unexpected response format from /v1/tx/list');
    }
    
    // Convert JSON data to Transaction objects
    final transactions = transactionData
        .map((json) => Transaction.fromJson(json as Map<String, dynamic>))
        .toList();
    
    print('[TransactionsList] Parsed ${transactions.length} items');
    return transactions;
  }

  // Legacy compatibility methods for existing code
  Future<List<Transaction>> getTransactions() async {
    return await listTransactions();
  }

  Future<Map<String, dynamic>> healthCheck() async {
    return await getHealth();
  }

  // Legacy single transaction fetch
  Future<Transaction> getTransaction(String hash) async {
    try {
      final url = Uri.parse('${ApiConfig.baseUrl}/v1/tx/$hash');
      print('[ApiService] GET $url');
      
      final response = await http.get(
        url,
        headers: await _buildHeaders(),
      ).timeout(ApiConfig.requestTimeout);
      
      print('[ApiService] GET $url -> ${response.statusCode}');
      print('[ApiService] Body: ${response.body}');
      
      final result = _processResponse(response);
      return Transaction.fromJson(result);
    } catch (e) {
      print('[ApiService] Get transaction failed: $e');
      rethrow;
    }
  }

  /// Normalize client status to backend-acceptable format
  String _normalizeClientStatus(String status) {
    final normalized = status.toLowerCase().trim();
    if (['pass', 'approved', 'approve', 'confirmed', 'confirm'].contains(normalized)) {
      return 'PASS';
    }
    if (['hold', 'pending'].contains(normalized)) {
      return 'HOLD';
    }
    if (['reject', 'rejected', 'block', 'blocked'].contains(normalized)) {
      return 'REJECT';
    }
    return status.toUpperCase();
  }

  // Override transaction status
  Future<Map<String, dynamic>> overrideTransaction({
    required String txIdOrHash,
    required String newStatus,
    required String reason,
  }) async {
    final url = Uri.parse(ApiConfig.getOverrideUrl());
    final normalizedStatus = _normalizeClientStatus(newStatus);
    final payload = {
      'hash': txIdOrHash,
      'status': normalizedStatus.toLowerCase(), // Backend expects lowercase
      'reason': reason,
    };

    print('[ApiService] POST $url');
    print('[ApiService] Payload: ${jsonEncode(payload)}');

    try {
      final headers = await _buildHeaders();
      print('[ApiService] Headers: ${headers.keys.join(', ')}');
      
      final response = await http.post(
        url,
        headers: headers,
        body: jsonEncode(payload),
      ).timeout(const Duration(seconds: 30));

      print('[ApiService] POST $url -> ${response.statusCode}');
      print('[ApiService] Body: ${response.body}');

      if (response.statusCode == 200 || response.statusCode == 201) {
        return jsonDecode(response.body) as Map<String, dynamic>;
      } else if (response.statusCode == 401) {
        throw Exception('Unauthorized (401). Token missing/invalid.');
      } else if (response.statusCode == 404) {
        throw Exception('Not Found (404). Verify API path and server routes.');
      } else if (response.statusCode == 422) {
        final body = jsonDecode(response.body);
        throw Exception('Validation failed: ${body['detail'] ?? response.body}');
      } else {
        throw Exception('Override failed: ${response.statusCode} ${response.body}');
      }
    } catch (e) {
      print('[ApiService] Override transaction failed: $e');
      rethrow;
    }
  }
}

// ==================== CUSTOM EXCEPTIONS ==================== //

class ApiException implements Exception {
  final String message;
  ApiException(this.message);
  
  @override
  String toString() => 'ApiException: $message';
}

class AuthenticationException extends ApiException {
  AuthenticationException(String message) : super(message);
  
  @override
  String toString() => 'AuthenticationException: $message';
}

class AuthorizationException extends ApiException {
  AuthorizationException(String message) : super(message);
  
  @override
  String toString() => 'AuthorizationException: $message';
}

class ConflictException extends ApiException {
  ConflictException(String message) : super(message);
  
  @override
  String toString() => 'ConflictException: $message';
}

class ValidationException extends ApiException {
  ValidationException(String message) : super(message);
  
  @override
  String toString() => 'ValidationException: $message';
}