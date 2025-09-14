import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../services/api_service.dart';
import '../services/auth_service.dart';
import '../services/storage_service.dart';
import '../models/user.dart' as auth_user;

// Authentication state data class
class AuthState {
  final bool isAuthenticated;
  final bool isLoading;
  final auth_user.User? user;
  final String? error;

  const AuthState({
    this.isAuthenticated = false,
    this.isLoading = false,
    this.user,
    this.error,
  });

  AuthState copyWith({
    bool? isAuthenticated,
    bool? isLoading,
    auth_user.User? user,
    String? error,
  }) {
    return AuthState(
      isAuthenticated: isAuthenticated ?? this.isAuthenticated,
      isLoading: isLoading ?? this.isLoading,
      user: user ?? this.user,
      error: error,
    );
  }

  @override
  String toString() {
    return 'AuthState(isAuthenticated: $isAuthenticated, isLoading: $isLoading, user: $user, error: $error)';
  }
}

// Auth Provider using StateNotifier
class AuthNotifier extends StateNotifier<AuthState> {
  final ApiService _apiService;
  final AuthService _authService;
  final StorageService _storageService;

  AuthNotifier(this._apiService, this._authService, this._storageService) : super(const AuthState()) {
    _initializeAuth();
  }

  /// Initialize authentication state on app start
  Future<void> _initializeAuth() async {
    state = state.copyWith(isLoading: true);
    
    try {
      final isAuthenticated = await _authService.isLoggedIn();
      
      if (isAuthenticated) {
        // Get user profile if authenticated
        final userProfile = await _apiService.getProfile();
        final user = auth_user.User.fromJson(userProfile.toJson());
        state = state.copyWith(
          isAuthenticated: true,
          isLoading: false,
          user: user,
          error: null,
        );
        print('[AuthProvider] User authenticated on app start');
      } else {
        state = state.copyWith(
          isAuthenticated: false,
          isLoading: false,
          user: null,
          error: null,
        );
        print('[AuthProvider] User not authenticated on app start');
      }
    } catch (e) {
      print('[AuthProvider] Error initializing auth: $e');
      state = state.copyWith(
        isAuthenticated: false,
        isLoading: false,
        user: null,
        error: null,
      );
    }
  }

  /// User signup
  Future<void> signup({
    required String username,
    required String email,
    required String password,
  }) async {
    state = state.copyWith(isLoading: true, error: null);
    
    try {
      final response = await _apiService.signup(
        username: username,
        email: email,
        password: password,
      );
      
      // Store token
      if (response.token.isNotEmpty) {
        await _storageService.setToken(response.token);
      }
      
      // Create user from response
      final user = auth_user.User.fromJson(response.toJson());
      
      // Update state with authenticated user
      state = state.copyWith(
        isAuthenticated: true,
        isLoading: false,
        user: user,
        error: null,
      );
      
      print('[AuthProvider] Signup successful for user: $username');
    } catch (e) {
      print('[AuthProvider] Signup failed: $e');
      state = state.copyWith(
        isAuthenticated: false,
        isLoading: false,
        user: null,
        error: e.toString(),
      );
      rethrow; // Let the UI handle the error
    }
  }

  /// User login
  Future<void> login({
    required String email,
    required String password,
    bool rememberMe = false,
  }) async {
    state = state.copyWith(isLoading: true, error: null);
    
    try {
      final response = await _apiService.login(
        email: email,
        password: password,
      );
      
      // Store token
      if (response.token.isNotEmpty) {
        await _storageService.setToken(response.token);
      }
      
      // Store remember me preference
      await _storageService.setRememberLogin(rememberMe);
      
      // Create user from response
      final user = auth_user.User.fromJson(response.toJson());
      
      // Update state with authenticated user
      state = state.copyWith(
        isAuthenticated: true,
        isLoading: false,
        user: user,
        error: null,
      );
      
      print('[AuthProvider] Login successful for user: $email');
    } catch (e) {
      print('[AuthProvider] Login failed: $e');
      state = state.copyWith(
        isAuthenticated: false,
        isLoading: false,
        user: null,
        error: e.toString(),
      );
      rethrow; // Let the UI handle the error
    }
  }

  /// User logout
  Future<void> logout() async {
    state = state.copyWith(isLoading: true);
    
    try {
      // Clear tokens from storage
      await _authService.logout();
      
      // Update state
      state = const AuthState(
        isAuthenticated: false,
        isLoading: false,
        user: null,
        error: null,
      );
      
      print('[AuthProvider] Logout successful');
    } catch (e) {
      print('[AuthProvider] Logout error: $e');
      // Even if logout fails, clear local state
      state = const AuthState(
        isAuthenticated: false,
        isLoading: false,
        user: null,
        error: null,
      );
    }
  }

  /// Refresh user profile
  Future<void> refreshProfile() async {
    if (!state.isAuthenticated) return;
    
    try {
      final userProfile = await _apiService.getProfile();
      final user = auth_user.User.fromJson(userProfile.toJson());
      state = state.copyWith(
        user: user,
        error: null,
      );
      print('[AuthProvider] Profile refreshed successfully');
    } catch (e) {
      print('[AuthProvider] Profile refresh failed: $e');
      // If profile refresh fails due to auth issues, logout
      if (e.toString().contains('401') || e.toString().contains('unauthorized')) {
        await logout();
      } else {
        state = state.copyWith(error: e.toString());
      }
    }
  }

  /// Clear error state
  void clearError() {
    state = state.copyWith(error: null);
  }

  /// Force refresh authentication status
  Future<void> checkAuthStatus() async {
    try {
      final isAuthenticated = await _authService.isLoggedIn();
      
      if (!isAuthenticated && state.isAuthenticated) {
        // User was logged out externally
        await logout();
      } else if (isAuthenticated && !state.isAuthenticated) {
        // User was logged in externally, refresh profile
        await refreshProfile();
      }
    } catch (e) {
      print('[AuthProvider] Auth status check failed: $e');
      if (state.isAuthenticated) {
        await logout();
      }
    }
  }

  /// Get user display name
  String? get userDisplayName {
    final user = state.user;
    if (user == null) return null;
    
    return user.username ?? user.email ?? 'User';
  }

  /// Get user email
  String? get userEmail {
    return state.user?.email;
  }

  /// Get user role
  String? get userRole {
    return state.user?.role;
  }

  /// Check if user has specific role
  bool hasRole(String role) {
    final userRole = state.user?.role;
    return userRole != null && userRole == role;
  }

  /// Check if user is admin
  bool get isAdmin {
    return hasRole('admin');
  }
}

// Riverpod providers
final authProvider = StateNotifierProvider<AuthNotifier, AuthState>((ref) {
  final apiService = ref.watch(apiServiceProvider);
  final authService = ref.watch(authServiceProvider);
  final storageService = ref.watch(storageServiceProvider);
  return AuthNotifier(apiService, authService, storageService);
});

// Convenience providers for specific auth state properties
final isAuthenticatedProvider = Provider<bool>((ref) {
  return ref.watch(authProvider).isAuthenticated;
});

final isAuthLoadingProvider = Provider<bool>((ref) {
  return ref.watch(authProvider).isLoading;
});

final currentUserProvider = Provider<auth_user.User?>((ref) {
  return ref.watch(authProvider).user;
});

final authErrorProvider = Provider<String?>((ref) {
  return ref.watch(authProvider).error;
});

final userDisplayNameProvider = Provider<String?>((ref) {
  return ref.watch(authProvider.notifier).userDisplayName;
});

final userEmailProvider = Provider<String?>((ref) {
  return ref.watch(authProvider.notifier).userEmail;
});

final isAdminProvider = Provider<bool>((ref) {
  return ref.watch(authProvider.notifier).isAdmin;
});

// Auth guard provider for route protection
final authGuardProvider = Provider<bool>((ref) {
  final authState = ref.watch(authProvider);
  return authState.isAuthenticated && !authState.isLoading;
});