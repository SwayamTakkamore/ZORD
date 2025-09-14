import 'package:flutter/material.dart';
import '../config/api_config.dart';
import '../services/api_service.dart';

class DebugScreen extends StatefulWidget {
  const DebugScreen({Key? key}) : super(key: key);

  @override
  State<DebugScreen> createState() => _DebugScreenState();
}

class _DebugScreenState extends State<DebugScreen> {
  final ApiService _apiService = ApiService();

  String _result = '';
  bool _isHealthLoading = false;
  bool _isSubmitLoading = false;
  bool _isListLoading = false;
  bool _isOverrideLoading = false;

  Future<void> _checkHealth() async {
    setState(() {
      _isHealthLoading = true;
      _result = 'Checking health...';
    });

    try {
      final response = await _apiService.getHealth();
      setState(() {
        _result = '✅ HEALTH CHECK SUCCESS\n\nResponse: ${response.toString()}';
      });
      _showSnackBar('Backend is healthy!', isError: false);
    } catch (e) {
      setState(() {
        _result = '❌ HEALTH CHECK FAILED\n\nError: $e';
      });
      _showSnackBar('Backend not reachable at ${ApiConfig.baseUrl}', isError: true);
    } finally {
      setState(() {
        _isHealthLoading = false;
      });
    }
  }

  Future<void> _testSubmit() async {
    setState(() {
      _isSubmitLoading = true;
      _result = 'Testing transaction submission...';
    });

    try {
      final testPayload = {
        "hash": "0x123456789abcdef",
        "from_address": "0x1234567890123456789012345678901234567890",
        "to_address": "0x0987654321098765432109876543210987654321",
        "amount": "100.50",
        "asset": "USDT",
        "memo": "Test transaction"
      };

      final response = await _apiService.submitTransaction(testPayload);

      setState(() {
        _result = '✅ SUBMIT TEST SUCCESS\n\nResponse: ${response.toString()}';
      });
      _showSnackBar('Transaction submitted successfully!', isError: false);
    } catch (e) {
      setState(() {
        _result = '❌ SUBMIT TEST FAILED\n\nError: $e';
      });
      _showSnackBar('Submit failed: $e', isError: true);
    } finally {
      setState(() {
        _isSubmitLoading = false;
      });
    }
  }

  Future<void> _testList() async {
    setState(() {
      _isListLoading = true;
      _result = 'Testing transaction list...';
    });

    try {
      final response = await _apiService.listTransactions();
      final preview = response.toString().length > 500
          ? '${response.toString().substring(0, 500)}...'
          : response.toString();

      setState(() {
        _result = '✅ LIST TEST SUCCESS\n\nResponse Preview: $preview';
      });
      _showSnackBar('Transaction list loaded successfully!', isError: false);
    } catch (e) {
      setState(() {
        _result = '❌ LIST TEST FAILED\n\nError: $e';
      });
      _showSnackBar('List failed: $e', isError: true);
    } finally {
      setState(() {
        _isListLoading = false;
      });
    }
  }

  Future<void> _testOverride() async {
    setState(() {
      _isOverrideLoading = true;
      _result = 'Testing override functionality...';
    });

    try {
      // Test with a sample transaction hash/ID
      final response = await _apiService.overrideTransaction(
        txIdOrHash: '005b076d-test-override-debug',
        newStatus: 'PASS',
        reason: 'Debug test override - testing functionality',
      );

      setState(() {
        _result = '✅ OVERRIDE TEST SUCCESS\n\nResponse: ${response.toString()}';
      });
      _showSnackBar('Override test successful!', isError: false);
    } catch (e) {
      setState(() {
        _result = '❌ OVERRIDE TEST FAILED\n\nError: $e\n\nThis might be expected if the transaction ID doesn\'t exist.';
      });
      _showSnackBar('Override test failed: $e', isError: true);
    } finally {
      setState(() {
        _isOverrideLoading = false;
      });
    }
  }

  void _showSnackBar(String message, {bool isError = false}) {
    if (!mounted) return;

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: isError ? Colors.red[600] : Colors.green[600],
        duration: const Duration(seconds: 4),
        action: SnackBarAction(
          label: 'Dismiss',
          textColor: Colors.white,
          onPressed: () {
            ScaffoldMessenger.of(context).hideCurrentSnackBar();
          },
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Debug Screen'),
      ),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Configuration',
                      style: Theme.of(context).textTheme.headlineSmall,
                    ),
                    const SizedBox(height: 8),
                    Text('Base URL: ${ApiConfig.baseUrl}'),
                    Text('Environment: ${ApiConfig.getCurrentEnvironment()}'),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                Expanded(
                  child: ElevatedButton(
                    onPressed: _isHealthLoading ? null : _checkHealth,
                    child: _isHealthLoading
                        ? const SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                        : const Text('Check Health'),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: ElevatedButton(
                    onPressed: _isSubmitLoading ? null : _testSubmit,
                    child: _isSubmitLoading
                        ? const SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                        : const Text('Test Submit'),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                Expanded(
                  child: ElevatedButton(
                    onPressed: _isListLoading ? null : _testList,
                    child: _isListLoading
                        ? const SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                        : const Text('Test List'),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: ElevatedButton(
                    onPressed: _isOverrideLoading ? null : _testOverride,
                    child: _isOverrideLoading
                        ? const SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                        : const Text('Test Override'),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            Expanded(
              child: Card(
                child: Padding(
                  padding: const EdgeInsets.all(16.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Results',
                        style: Theme.of(context).textTheme.headlineSmall,
                      ),
                      const SizedBox(height: 8),
                      Expanded(
                        child: SingleChildScrollView(
                          child: Text(
                            _result.isEmpty ? 'No tests run yet' : _result,
                            style: const TextStyle(fontFamily: 'monospace'),
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
