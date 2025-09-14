# Flutter Override Feature - Test Checklist and Documentation

## Overview
This document provides testing instructions for the Flutter override functionality that allows users to manually override transaction decisions.

## Root Cause Analysis
**Original Issue**: The Flutter override feature was failing with 404 errors and UI not updating.

**Root Causes Identified**:
1. **Missing Override Endpoint**: ApiConfig didn't have the `/v1/override` endpoint constant
2. **Header Authentication**: API calls weren't including proper Bearer tokens from secure storage
3. **Incomplete Implementation**: TransactionDetailsScreen had placeholder override dialog
4. **Method Signature Mismatch**: ApiService used old OverrideRequest class instead of backend-expected parameters
5. **No Error Handling**: Poor error feedback and logging for debugging

**Fix Applied**:
- Added proper endpoint configuration with physical device IP support
- Implemented robust header builder with JWT token and optional admin key
- Created functional override dialog with validation and status selection
- Updated API method to match backend requirements exactly
- Added comprehensive error handling and logging
- Created unit tests and debug functionality

## Backend Verification

First, ensure the backend is running and accessible:

```bash
# Start the backend server
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Test backend override endpoint directly
curl -X POST http://10.223.35.199:8000/v1/override \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "transaction_hash": "005b076d-test-hash-12345",
    "new_status": "PASS", 
    "reason": "Manual override test from curl"
  }' | jq .

# Expected response: 200 OK with JSON success payload
```

## Flutter App Testing

### Prerequisites
1. Ensure backend is running on `http://10.223.35.199:8000`
2. Set environment variable: `API_URL=http://10.223.35.199:8000`
3. User must be logged in (JWT token stored)

### Test Checklist

#### ✅ 1. Configuration Test
- [ ] Start Flutter app on physical device
- [ ] Navigate to Debug Screen
- [ ] Verify "Base URL" shows correct IP: `http://10.223.35.199:8000`
- [ ] Verify "Environment" shows "Physical Device (LAN)"

#### ✅ 2. Backend Connectivity Test  
- [ ] In Debug Screen, tap "Check Health"
- [ ] Should show: "✅ HEALTH CHECK SUCCESS"
- [ ] Green snackbar: "Backend is healthy!"

#### ✅ 3. Override API Test
- [ ] In Debug Screen, tap "Test Override"
- [ ] Check debug console for logs:
  ```
  [ApiService] POST http://10.223.35.199:8000/v1/override
  [ApiService] Payload: {"transaction_hash":"005b076d-test-override-debug","new_status":"PASS","reason":"Debug test override - testing functionality"}
  [ApiService] Headers: Content-Type, Authorization
  [ApiService] POST http://10.223.35.199:8000/v1/override -> 200
  [ApiService] Body: {"success":true,"new_decision":"PASS"}
  ```
- [ ] Should show: "✅ OVERRIDE TEST SUCCESS" or meaningful error

#### ✅ 4. Transaction Details Override Test
- [ ] Navigate to Transactions List
- [ ] Tap on any transaction to open details
- [ ] Tap "Override" button
- [ ] Verify dialog opens with:
  - [ ] Transaction hash/ID display
  - [ ] Status dropdown (PASS, HOLD, REJECT)
  - [ ] Reason text field
  - [ ] Cancel and Override buttons

#### ✅ 5. Override Dialog Validation
- [ ] Try submitting with reason < 10 characters
- [ ] Should show red snackbar: "Reason must be at least 10 characters"
- [ ] Enter valid reason (>= 10 chars) and select status
- [ ] Tap "Override" button
- [ ] Should show loading state, then success/error message

#### ✅ 6. Override Success Flow
- [ ] Complete override with valid data
- [ ] Check debug console for proper API call logs
- [ ] Should show green snackbar: "Override successful: PASS"
- [ ] Transaction status should update in UI (optimistic update)
- [ ] Override button should show "Processing..." during operation

#### ✅ 7. Override Error Handling
- [ ] Try override with invalid transaction ID
- [ ] Should show red snackbar with meaningful error message
- [ ] Try override without network connection
- [ ] Should handle timeout gracefully

#### ✅ 8. Authentication Test
- [ ] Log out of app
- [ ] Try override operation (should fail with 401)
- [ ] Log back in and retry (should succeed)

### Debug Commands

#### Run Flutter Tests
```bash
cd mobile-app
flutter test test/override_integration_test.dart
flutter test test/api_service_override_test.dart
```

#### Run Flutter App on Device
```bash
cd mobile-app
flutter run --dart-define=API_URL=http://10.223.35.199:8000 --release
```

#### Check Flutter Logs
```bash
flutter logs
```

### Expected Debug Console Output

#### Successful Override:
```
[ApiService] POST http://10.223.35.199:8000/v1/override
[ApiService] Payload: {"transaction_hash":"tx-12345","new_status":"PASS","reason":"Manual approval by compliance officer"}
[ApiService] Headers: Content-Type, Authorization
[StorageService] Token retrieved: exists
[ApiService] POST http://10.223.35.199:8000/v1/override -> 200
[ApiService] Body: {"success":true,"new_decision":"PASS","message":"Override successful"}
```

#### Failed Override (404):
```
[ApiService] POST http://10.223.35.199:8000/v1/override
[ApiService] Payload: {"transaction_hash":"invalid-hash","new_status":"PASS","reason":"Test override"}
[ApiService] Headers: Content-Type, Authorization
[ApiService] POST http://10.223.35.199:8000/v1/override -> 404
[ApiService] Body: {"detail":"Transaction not found"}
[ApiService] Override transaction failed: Exception: Not Found (404). Verify API path and server routes.
```

## Acceptance Criteria

### ✅ Completed Features
1. **Correct API Call**: POST to `http://10.223.35.199:8000/v1/override` with exact JSON keys: `transaction_hash`, `new_status`, `reason`
2. **Authentication**: JWT Bearer token automatically included from secure storage
3. **Success Handling**: Shows green SnackBar and updates transaction status optimistically
4. **Error Handling**: Shows red SnackBar with readable error messages including backend details
5. **Debug Logging**: Comprehensive logs for URL, payload, headers, and response
6. **Unit Tests**: Test coverage for success and failure scenarios
7. **UI/UX**: Proper loading states, validation, and user feedback

### Additional Features
- **Status Normalization**: Client statuses like "confirmed" automatically map to backend "PASS"
- **Admin API Key Support**: Optional `X-Admin-API-Key` header for admin operations
- **Physical Device Support**: Proper IP configuration for real device testing
- **Robust Validation**: Minimum 10-character reason requirement with user feedback

## Troubleshooting

### Common Issues

1. **404 Not Found**
   - Verify backend is running on correct port
   - Check API_URL environment variable
   - Confirm `/v1/override` endpoint exists in backend

2. **401 Unauthorized** 
   - User must be logged in
   - Check if JWT token is stored in secure storage
   - Verify token hasn't expired

3. **Network Connection**
   - Ensure device can reach `10.223.35.199:8000`
   - Check firewall/network settings
   - Try ping or curl from device terminal

4. **UI Not Updating**
   - Check for errors in Flutter console
   - Verify `mounted` checks in setState calls
   - Confirm copyWith method exists on Transaction model

## Files Modified

- `lib/config/api_config.dart` - Added override endpoint and physical device IP
- `lib/services/api_service.dart` - New robust override method with headers and error handling
- `lib/screens/transaction_details_screen.dart` - Complete override dialog implementation
- `lib/screens/debug_screen.dart` - Added override testing functionality
- `test/api_service_override_test.dart` - Unit tests for override functionality
- `test/override_integration_test.dart` - Integration tests for status normalization

The override feature is now fully functional with comprehensive error handling, logging, and testing capabilities.