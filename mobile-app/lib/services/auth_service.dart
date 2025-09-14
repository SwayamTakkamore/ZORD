import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'dart:convert';

import '../models/user.dart';
import 'storage_service.dart';

class AuthService {
  final StorageService _storageService;
  
  AuthService(this._storageService);

  /// Check if user is currently logged in
  Future<bool> isLoggedIn() async {
    try {
      final token = await _storageService.getToken();
      return token != null && token.isNotEmpty;
    } catch (e) {
      print('[AuthService] Error checking login status: $e');
      return false;
    }
  }

  /// Get stored authentication token
  Future<String?> getToken() async {
    try {
      return await _storageService.getToken();
    } catch (e) {
      print('[AuthService] Error getting token: $e');
      return null;
    }
  }

  /// Store authentication token
  Future<void> setToken(String token) async {
    try {
      await _storageService.setToken(token);
      print('[AuthService] Token stored successfully');
    } catch (e) {
      print('[AuthService] Error storing token: $e');
      throw Exception('Failed to store authentication token');
    }
  }

  /// Clear authentication state (logout)
  Future<void> logout() async {
    try {
      await _storageService.clearToken();
      await _storageService.clearUser();
      print('[AuthService] Logout successful');
    } catch (e) {
      print('[AuthService] Error during logout: $e');
      throw Exception('Failed to logout');
    }
  }

  /// Store user profile
  Future<void> setUser(User user) async {
    try {
      await _storageService.setUser(user);
      print('[AuthService] User profile stored');
    } catch (e) {
      print('[AuthService] Error storing user: $e');
      throw Exception('Failed to store user profile');
    }
  }

  /// Get stored user profile
  Future<User?> getUser() async {
    try {
      return await _storageService.getUser();
    } catch (e) {
      print('[AuthService] Error getting user: $e');
      return null;
    }
  }

  /// Check if remember login is enabled
  Future<bool> getRememberLogin() async {
    try {
      return await _storageService.getRememberLogin();
    } catch (e) {
      print('[AuthService] Error getting remember login: $e');
      return false;
    }
  }

  /// Set remember login preference
  Future<void> setRememberLogin(bool remember) async {
    try {
      await _storageService.setRememberLogin(remember);
      print('[AuthService] Remember login preference saved: $remember');
    } catch (e) {
      print('[AuthService] Error setting remember login: $e');
      throw Exception('Failed to save remember login preference');
    }
  }
}

// Riverpod provider for AuthService
final authServiceProvider = Provider<AuthService>((ref) {
  final storageService = ref.watch(storageServiceProvider);
  return AuthService(storageService);
});
