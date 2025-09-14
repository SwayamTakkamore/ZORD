import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../models/transaction.dart';
import '../services/api_service.dart';
import '../providers/auth_provider.dart';
import '../services/storage_service.dart';
import '../widgets/transaction_card.dart';
import '../widgets/stats_cards.dart';

class DashboardScreen extends ConsumerStatefulWidget {
  const DashboardScreen({super.key});

  @override
  ConsumerState<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends ConsumerState<DashboardScreen> {
  // final RefreshIndicator _refreshIndicator = RefreshIndicator.createKey();
  final GlobalKey<RefreshIndicatorState> _refreshIndicatorKey = GlobalKey<RefreshIndicatorState>();
  List<Transaction> _transactions = [];
  bool _isLoading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadTransactions();
    _startAutoRefresh();
  }

  void _startAutoRefresh() {
    // Auto-refresh every 30 seconds
    Future.delayed(const Duration(seconds: 30), () {
      if (mounted) {
        _loadTransactions(showLoading: false);
        _startAutoRefresh();
      }
    });
  }

  Future<void> _loadTransactions({bool showLoading = true}) async {
    if (showLoading) {
      setState(() {
        _isLoading = true;
        _error = null;
      });
    }

    try {
      final apiService = ref.read(apiServiceProvider);
      final transactions = await apiService.getTransactions();
      
      // Cache the transactions
      await StorageService.cacheTransactions(transactions);
      
      if (mounted) {
        setState(() {
          _transactions = transactions;
          _isLoading = false;
          _error = null;
        });
        
        // Show success message if this was a manual refresh and we had an error before
        if (!showLoading && _error != null) {
          _showSnackBar('Transactions updated successfully', isError: false);
        }
      }
    } catch (e) {
      // Load cached transactions on error
      final cachedTransactions = StorageService.getCachedTransactions();
      
      if (mounted) {
        setState(() {
          _transactions = cachedTransactions;
          _isLoading = false;
          _error = cachedTransactions.isEmpty ? 'Failed to load transactions' : null;
        });
        
        // Show error notification
        String errorMessage = 'Failed to connect to backend';
        if (e.toString().contains('Cannot connect to backend')) {
          errorMessage = 'Backend not reachable. Using cached data.';
        } else if (e.toString().contains('Network error')) {
          errorMessage = 'Network error. Check your connection.';
        }
        
        if (cachedTransactions.isNotEmpty) {
          _showSnackBar('$errorMessage Using cached data.', isError: true);
        } else {
          _showSnackBar(errorMessage, isError: true);
        }
      }
      
      print('[Dashboard] Failed to load transactions: $e');
    }
  }

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authProvider);
    final stats = DashboardStats.fromTransactions(_transactions);

    return Scaffold(
      backgroundColor: Colors.grey[50],
      appBar: AppBar(
        title: const Text(
          'Dashboard',
          style: TextStyle(fontWeight: FontWeight.w600),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.settings),
            onPressed: () => context.push('/settings'),
          ),
          PopupMenuButton<String>(
            onSelected: (value) {
              if (value == 'logout') {
                _handleLogout();
              }
            },
            itemBuilder: (context) => [
              PopupMenuItem(
                value: 'profile',
                child: Row(
                  children: [
                    const Icon(Icons.person_outline, size: 20),
                    const SizedBox(width: 12),
                    Text(authState.user?.username ?? 'User'),
                  ],
                ),
              ),
              const PopupMenuDivider(),
              const PopupMenuItem(
                value: 'logout',
                child: Row(
                  children: [
                    Icon(Icons.logout, size: 20),
                    SizedBox(width: 12),
                    Text('Logout'),
                  ],
                ),
              ),
            ],
          ),
        ],
      ),
      body: RefreshIndicator(
        key: _refreshIndicatorKey,
        onRefresh: _loadTransactions,
        child: _buildBody(stats),
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () => _loadTransactions(),
        tooltip: 'Refresh',
        child: const Icon(Icons.refresh),
      ),
    );
  }

  Widget _buildBody(DashboardStats stats) {
    if (_isLoading && _transactions.isEmpty) {
      return const Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            CircularProgressIndicator(),
            SizedBox(height: 16),
            Text('Loading transactions...'),
          ],
        ),
      );
    }

    if (_error != null && _transactions.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(
              Icons.error_outline,
              size: 64,
              color: Colors.grey,
            ),
            const SizedBox(height: 16),
            Text(
              _error!,
              style: const TextStyle(fontSize: 16),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: _loadTransactions,
              child: const Text('Retry'),
            ),
          ],
        ),
      );
    }

    return CustomScrollView(
      slivers: [
        // Stats cards
        SliverToBoxAdapter(
          child: Padding(
            padding: const EdgeInsets.all(16.0),
            child: StatsCards(stats: stats),
          ),
        ),
        
        // Transactions header
        SliverToBoxAdapter(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16.0),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text(
                  'Recent Transactions',
                  style: TextStyle(
                    fontSize: 20,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                if (_isLoading)
                  const SizedBox(
                    width: 16,
                    height: 16,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  ),
              ],
            ),
          ),
        ),
        
        const SliverToBoxAdapter(child: SizedBox(height: 16)),
        
        // Transactions list
        if (_transactions.isEmpty)
          const SliverToBoxAdapter(
            child: Padding(
              padding: EdgeInsets.all(32.0),
              child: Center(
                child: Column(
                  children: [
                    Icon(
                      Icons.receipt_long_outlined,
                      size: 48,
                      color: Colors.grey,
                    ),
                    SizedBox(height: 16),
                    Text(
                      'No transactions found',
                      style: TextStyle(
                        fontSize: 16,
                        color: Colors.grey,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          )
        else
          SliverList(
            delegate: SliverChildBuilderDelegate(
              (context, index) {
                final transaction = _transactions[index];
                return Padding(
                  padding: EdgeInsets.only(
                    left: 16,
                    right: 16,
                    bottom: index == _transactions.length - 1 ? 100 : 8,
                  ),
                  child: TransactionCard(
                    transaction: transaction,
                    onTap: () => context.push('/transaction/${transaction.id}'),
                    onOverride: () => _showOverrideDialog(transaction),
                  ),
                );
              },
              childCount: _transactions.length,
            ),
          ),
      ],
    );
  }

  void _handleLogout() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Logout'),
        content: const Text('Are you sure you want to logout?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () {
              Navigator.pop(context);
              ref.read(authProvider.notifier).logout();
            },
            child: const Text('Logout'),
          ),
        ],
      ),
    );
  }

  void _showOverrideDialog(Transaction transaction) {
    showDialog(
      context: context,
      builder: (context) => _OverrideDialog(
        transaction: transaction,
        onOverride: (newStatus, reason) async {
          try {
            final apiService = ref.read(apiServiceProvider);
            final txId = transaction.id;
            
            await apiService.overrideTransaction(
              txIdOrHash: txId,
              newStatus: newStatus.name,
              reason: reason,
            );
            
            // Show success message
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(
                content: Text('Transaction status updated successfully'),
                backgroundColor: Colors.green,
              ),
            );
            
            // Refresh transactions
            _loadTransactions(showLoading: false);
          } catch (e) {
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(
                content: Text('Failed to update transaction: $e'),
                backgroundColor: Colors.red,
              ),
            );
          }
        },
      ),
    );
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
}

class _OverrideDialog extends StatefulWidget {
  final Transaction transaction;
  final Function(TransactionStatus, String) onOverride;

  const _OverrideDialog({
    required this.transaction,
    required this.onOverride,
  });

  @override
  State<_OverrideDialog> createState() => _OverrideDialogState();
}

class _OverrideDialogState extends State<_OverrideDialog> {
  TransactionStatus _selectedStatus = TransactionStatus.confirmed;
  final _reasonController = TextEditingController();
  bool _isLoading = false;

  @override
  void dispose() {
    _reasonController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Override Transaction'),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Transaction: ${widget.transaction.hash.substring(0, 10)}...',
              style: const TextStyle(fontFamily: 'monospace'),
            ),
            const SizedBox(height: 16),
            const Text('New Status:'),
            const SizedBox(height: 8),
            DropdownButtonFormField<TransactionStatus>(
              value: _selectedStatus,
              items: [
                TransactionStatus.confirmed,
                TransactionStatus.blocked,
              ].map((status) {
                return DropdownMenuItem(
                  value: status,
                  child: Text(status.name.toUpperCase()),
                );
              }).toList(),
              onChanged: (value) {
                setState(() {
                  _selectedStatus = value!;
                });
              },
              decoration: const InputDecoration(
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 16),
            const Text('Reason:'),
            const SizedBox(height: 8),
            TextField(
              controller: _reasonController,
              maxLines: 3,
              decoration: const InputDecoration(
                border: OutlineInputBorder(),
                hintText: 'Explain the reason for override...',
              ),
            ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: _isLoading ? null : () => Navigator.pop(context),
          child: const Text('Cancel'),
        ),
        ElevatedButton(
          onPressed: _isLoading ? null : _handleOverride,
          child: _isLoading
              ? const SizedBox(
                  width: 16,
                  height: 16,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              : const Text('Override'),
        ),
      ],
    );
  }

  void _handleOverride() async {
    if (_reasonController.text.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Please provide a reason for the override'),
          backgroundColor: Colors.orange,
        ),
      );
      return;
    }

    setState(() {
      _isLoading = true;
    });

    try {
      await widget.onOverride(_selectedStatus, _reasonController.text.trim());
      Navigator.pop(context);
    } catch (e) {
      // Error handling is done in the parent
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }
}
