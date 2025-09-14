import 'package:hive_flutter/hive_flutter.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'dart:convert';
import '../models/transaction.dart';
import '../models/user.dart' as auth_user;

class StorageService {
  static const String _transactionsBox = 'transactions';
  static const String _settingsBox = 'settings';
  
  static late Box<Map> _transactions;
  static late Box _settings;

  // Flutter Secure Storage for sensitive data
  static const _secureStorage = FlutterSecureStorage(
    aOptions: AndroidOptions(
      encryptedSharedPreferences: true,
      keyCipherAlgorithm: KeyCipherAlgorithm.RSA_ECB_PKCS1Padding,
      storageCipherAlgorithm: StorageCipherAlgorithm.AES_GCM_NoPadding,
    ),
    iOptions: IOSOptions(
      accessibility: KeychainAccessibility.first_unlock_this_device,
    ),
  );

  // Storage keys for authentication
  static const String _tokenKey = 'auth_token';
  static const String _userKey = 'user_data';
  static const String _rememberLoginKey = 'remember_login';

  static Future<void> initialize() async {
    // Register adapters if needed
    // Hive.registerAdapter(TransactionAdapter());
    
    _transactions = await Hive.openBox<Map>(_transactionsBox);
    _settings = await Hive.openBox(_settingsBox);
  }

  // ==================== AUTHENTICATION STORAGE ==================== //

  /// Store authentication token securely
  Future<void> setToken(String token) async {
    try {
      await _secureStorage.write(key: _tokenKey, value: token);
      print('[StorageService] Token stored successfully');
    } catch (e) {
      print('[StorageService] Error storing token: $e');
      throw Exception('Failed to store authentication token');
    }
  }

  /// Retrieve authentication token
  Future<String?> getToken() async {
    try {
      final token = await _secureStorage.read(key: _tokenKey);
      print('[StorageService] Token retrieved: ${token != null ? 'exists' : 'null'}');
      return token;
    } catch (e) {
      print('[StorageService] Error retrieving token: $e');
      return null;
    }
  }

  /// Clear authentication token
  Future<void> clearToken() async {
    try {
      await _secureStorage.delete(key: _tokenKey);
      print('[StorageService] Token cleared successfully');
    } catch (e) {
      print('[StorageService] Error clearing token: $e');
      throw Exception('Failed to clear authentication token');
    }
  }

  /// Store user profile
  Future<void> setUser(auth_user.User user) async {
    try {
      final userJson = jsonEncode(user.toJson());
      await _secureStorage.write(key: _userKey, value: userJson);
      print('[StorageService] User profile stored successfully');
    } catch (e) {
      print('[StorageService] Error storing user: $e');
      throw Exception('Failed to store user profile');
    }
  }

  /// Retrieve user profile
  Future<auth_user.User?> getUser() async {
    try {
      final userJson = await _secureStorage.read(key: _userKey);
      if (userJson != null) {
        final userMap = jsonDecode(userJson) as Map<String, dynamic>;
        final user = auth_user.User.fromJson(userMap);
        print('[StorageService] User profile retrieved');
        return user;
      }
      return null;
    } catch (e) {
      print('[StorageService] Error retrieving user: $e');
      return null;
    }
  }

  /// Clear user profile
  Future<void> clearUser() async {
    try {
      await _secureStorage.delete(key: _userKey);
      print('[StorageService] User profile cleared successfully');
    } catch (e) {
      print('[StorageService] Error clearing user: $e');
      throw Exception('Failed to clear user profile');
    }
  }

  /// Store remember login preference
  Future<void> setRememberLogin(bool remember) async {
    try {
      await _secureStorage.write(key: _rememberLoginKey, value: remember.toString());
      print('[StorageService] Remember login preference stored: $remember');
    } catch (e) {
      print('[StorageService] Error storing remember login: $e');
      throw Exception('Failed to store remember login preference');
    }
  }

  /// Get remember login preference
  Future<bool> getRememberLogin() async {
    try {
      final rememberString = await _secureStorage.read(key: _rememberLoginKey);
      final remember = rememberString == 'true';
      print('[StorageService] Remember login preference retrieved: $remember');
      return remember;
    } catch (e) {
      print('[StorageService] Error retrieving remember login: $e');
      return false;
    }
  }

  /// Clear all authentication data
  Future<void> clearAuthData() async {
    try {
      await clearToken();
      await clearUser();
      await _secureStorage.delete(key: _rememberLoginKey);
      print('[StorageService] All auth data cleared successfully');
    } catch (e) {
      print('[StorageService] Error clearing auth data: $e');
      throw Exception('Failed to clear authentication data');
    }
  }

  // Transaction caching
  static Future<void> cacheTransactions(List<Transaction> transactions) async {
    try {
      final Map<String, Map<String, dynamic>> transactionMap = {};
      for (final transaction in transactions) {
        transactionMap[transaction.id] = transaction.toJson();
      }
      await _transactions.putAll(transactionMap);
    } catch (e) {
      print('[Storage] Failed to cache transactions: $e');
    }
  }

  static List<Transaction> getCachedTransactions() {
    try {
      final transactions = <Transaction>[];
      for (final value in _transactions.values) {
        try {
          final transaction = Transaction.fromJson(Map<String, dynamic>.from(value));
          transactions.add(transaction);
        } catch (e) {
          print('[Storage] Failed to parse cached transaction: $e');
        }
      }
      
      // Sort by timestamp descending
      transactions.sort((a, b) => b.timestamp.compareTo(a.timestamp));
      return transactions;
    } catch (e) {
      print('[Storage] Failed to get cached transactions: $e');
      return [];
    }
  }

  static Future<void> cacheTransaction(Transaction transaction) async {
    try {
      await _transactions.put(transaction.id, transaction.toJson());
    } catch (e) {
      print('[Storage] Failed to cache transaction: $e');
    }
  }

  static Transaction? getCachedTransaction(String id) {
    try {
      final data = _transactions.get(id);
      if (data != null) {
        return Transaction.fromJson(Map<String, dynamic>.from(data));
      }
      return null;
    } catch (e) {
      print('[Storage] Failed to get cached transaction: $e');
      return null;
    }
  }

  static Future<void> clearTransactionCache() async {
    try {
      await _transactions.clear();
    } catch (e) {
      print('[Storage] Failed to clear transaction cache: $e');
    }
  }

  // Settings
  static Future<void> setSetting(String key, dynamic value) async {
    try {
      await _settings.put(key, value);
    } catch (e) {
      print('[Storage] Failed to set setting $key: $e');
    }
  }

  static T? getSetting<T>(String key, {T? defaultValue}) {
    try {
      return _settings.get(key, defaultValue: defaultValue) as T?;
    } catch (e) {
      print('[Storage] Failed to get setting $key: $e');
      return defaultValue;
    }
  }

  static Future<void> removeSetting(String key) async {
    try {
      await _settings.delete(key);
    } catch (e) {
      print('[Storage] Failed to remove setting $key: $e');
    }
  }

  static Future<void> clearSettings() async {
    try {
      await _settings.clear();
    } catch (e) {
      print('[Storage] Failed to clear settings: $e');
    }
  }

  // App preferences
  static const String _biometricEnabledKey = 'biometric_enabled';
  static const String _notificationsEnabledKey = 'notifications_enabled';
  static const String _darkModeKey = 'dark_mode';
  static const String _refreshIntervalKey = 'refresh_interval';

  static Future<void> setBiometricEnabled(bool enabled) async {
    await setSetting(_biometricEnabledKey, enabled);
  }

  static bool getBiometricEnabled() {
    return getSetting<bool>(_biometricEnabledKey, defaultValue: false) ?? false;
  }

  static Future<void> setNotificationsEnabled(bool enabled) async {
    await setSetting(_notificationsEnabledKey, enabled);
  }

  static bool getNotificationsEnabled() {
    return getSetting<bool>(_notificationsEnabledKey, defaultValue: true) ?? true;
  }

  static Future<void> setDarkMode(bool enabled) async {
    await setSetting(_darkModeKey, enabled);
  }

  static bool getDarkMode() {
    return getSetting<bool>(_darkModeKey, defaultValue: false) ?? false;
  }

  static Future<void> setRefreshInterval(int seconds) async {
    await setSetting(_refreshIntervalKey, seconds);
  }

  static int getRefreshInterval() {
    return getSetting<int>(_refreshIntervalKey, defaultValue: 30) ?? 30;
  }
}

// Riverpod provider for StorageService
final storageServiceProvider = Provider<StorageService>((ref) => StorageService());
