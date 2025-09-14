# Mobile App

A Flutter application for transaction monitoring and compliance management.

## Features

- **Transaction List**: View and browse through transactions with pagination
- **Robust API Integration**: Handles multiple backend response formats with fallback parsing
- **Error Handling**: Comprehensive error states and retry mechanisms
- **Debug Screen**: Testing interface for backend connectivity
- **Pull-to-Refresh**: Easy data reload functionality
- **Responsive UI**: Clean, user-friendly interface for transaction management

## Backend Integration

The app connects to a FastAPI backend at the URL specified in the `.env` file. It supports:

- Health check endpoint (`/health`)
- Transaction listing endpoint (`/v1/tx/list`)
- Robust parsing for different field name formats:
  - `tx_uuid` or `tx_id`
  - `wallet_from` or `from_address`
  - `wallet_to` or `to_address`
  - `currency` or `asset`

## Setup and Installation

### Prerequisites

- Flutter SDK (version 3.0.0 or higher)
- Dart SDK
- Android Studio / VS Code with Flutter extensions
- Android emulator or physical device for testing

### Installation Steps

1. **Clone and navigate to the project:**
   ```bash
   cd mobile-app
   ```

2. **Install dependencies:**
   ```bash
   flutter pub get
   ```

3. **Configure environment:**
   - Copy `.env.example` to `.env` (if exists) or create `.env`:
   ```bash
   # .env
   API_URL=http://172.31.185.73:8000
   ```

4. **Generate mock files for testing:**
   ```bash
   flutter packages pub run build_runner build
   ```

## Running the Application

### Development Mode

```bash
# Run on connected device/emulator
flutter run

# Run with specific device
flutter devices  # List available devices
flutter run -d <device_id>

# Run in debug mode (default)
flutter run --debug

# Run in release mode for better performance
flutter run --release
```

### Build Commands

```bash
# Build APK for Android
flutter build apk

# Build app bundle for Google Play Store
flutter build appbundle

# Build for iOS (macOS only)
flutter build ios
```

## Testing

### Run All Tests

```bash
# Run all tests
flutter test

# Run tests with coverage
flutter test --coverage

# Run specific test file
flutter test test/api_service_test.dart
flutter test test/transactions_list_widget_test.dart
```

### Test Categories

- **Unit Tests**: `test/api_service_test.dart` - API service functionality
- **Widget Tests**: `test/transactions_list_widget_test.dart` - UI component testing
- **Integration Tests**: Coming soon

## Project Structure

```
lib/
├── config/
│   └── api_config.dart          # API configuration and URL management
├── models/
│   └── transaction.dart         # Transaction model with robust parsing
├── screens/
│   ├── debug_screen.dart        # Debug interface for testing
│   ├── dashboard_screen.dart    # Main dashboard
│   └── transactions_list.dart   # Transaction listing screen
├── services/
│   └── api_service.dart         # API service with error handling
├── widgets/
│   └── transaction_tile.dart    # Individual transaction display widget
└── main.dart                    # Application entry point

test/
├── api_service_test.dart               # API service unit tests
└── transactions_list_widget_test.dart  # Transaction list widget tests
```

## Key Features Implementation

### Transaction Model (`lib/models/transaction.dart`)
- Robust JSON parsing with multiple fallback keys
- Handles string/numeric amounts and date formats
- Helper methods for UI display (shortened addresses, formatted timestamps)

### API Service (`lib/services/api_service.dart`)
- Comprehensive error handling and logging
- Support for both array and object response formats
- Timeout management and retry logic
- Riverpod provider integration

### Transaction List Screen (`lib/screens/transactions_list.dart`)
- Loading states and error handling
- Pull-to-refresh functionality
- Pagination with "Load More" button
- Empty state management

### Transaction Tile Widget (`lib/widgets/transaction_tile.dart`)
- Clean, card-based transaction display
- Status indicators with color coding
- Shortened address display for readability
- Additional transaction details (network, type, currency)

## Environment Configuration

The app uses environment variables for configuration:

```bash
# .env
API_URL=http://172.31.185.73:8000  # Backend API URL
```

The app will fall back to compile-time constants if environment variables are not available.

## Debugging

### Debug Screen
Access the debug screen in the app to test:
- Backend connectivity (health check)
- API endpoints
- Sample transaction submission

### Logging
The app provides detailed console logging for:
- API requests and responses
- Transaction parsing
- Error states and recovery

### Common Issues

1. **Connection refused**: Check if backend is running and accessible
2. **Parse errors**: Backend response format might have changed
3. **Test failures**: Run `flutter packages pub run build_runner build` to regenerate mocks

## Contributing

1. Follow Flutter/Dart style guidelines
2. Add tests for new features
3. Update documentation for API changes
4. Use the debug screen to verify backend connectivity

## Dependencies

### Core Dependencies
- `flutter_riverpod`: State management
- `http`: HTTP client for API calls
- `flutter_dotenv`: Environment variable management
- `intl`: Date/time formatting

### Development Dependencies
- `flutter_test`: Testing framework
- `mockito`: Mocking for unit tests
- `build_runner`: Code generation for mocks

## Backend Compatibility

This app is designed to work with the existing FastAPI backend without requiring any backend changes. It handles:

- Multiple response formats (array vs object wrapping)
- Different field naming conventions
- Robust error recovery and user feedback
- Comprehensive logging for debugging