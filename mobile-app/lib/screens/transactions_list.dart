import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../services/api_service.dart';
import '../models/transaction.dart';
import '../widgets/transaction_tile.dart';

class TransactionsList extends ConsumerStatefulWidget {
  const TransactionsList({Key? key}) : super(key: key);

  @override
  ConsumerState<TransactionsList> createState() => _TransactionsListState();
}

class _TransactionsListState extends ConsumerState<TransactionsList> {
  List<Transaction> _transactions = [];
  bool _isLoading = true;
  String? _error;
  int _currentPage = 1;
  bool _hasMorePages = false;

  @override
  void initState() {
    super.initState();
    _loadTransactions();
  }

  Future<void> _loadTransactions({bool isRefresh = false}) async {
    if (isRefresh) {
      _currentPage = 1;
      _transactions.clear();
    }

    setState(() {
      _isLoading = true;
      if (isRefresh) _error = null;
    });

    try {
      print('[TransactionsList] Loading transactions (page: $_currentPage)');
      final apiService = ref.read(apiServiceProvider);
      final newTransactions = await apiService.listTransactions(
        page: _currentPage,
        perPage: 20,
      );

      print('[TransactionsList] Loaded ${newTransactions.length} transactions');
      
      // Debug: Print raw transaction data
      for (final tx in newTransactions) {
        print('[TransactionsList] Transaction: ${tx.shortId} - ${tx.shortFromAddress} → ${tx.shortToAddress} - ${tx.formattedAmount} - ${tx.decision}');
      }

      setState(() {
        if (isRefresh) {
          _transactions = newTransactions;
        } else {
          _transactions.addAll(newTransactions);
        }
        _isLoading = false;
        _error = null;
        _hasMorePages = newTransactions.length >= 20; // Assume more pages if we got a full page
      });
    } catch (e) {
      print('[TransactionsList] Failed to load transactions: $e');
      setState(() {
        _isLoading = false;
        _error = e.toString().replaceAll('Exception: ', '');
      });
    }
  }

  Future<void> _loadMoreTransactions() async {
    if (_isLoading || !_hasMorePages) return;

    _currentPage++;
    await _loadTransactions();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Transactions'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => _loadTransactions(isRefresh: true),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () => _loadTransactions(isRefresh: true),
        child: _buildBody(),
      ),
    );
  }

  Widget _buildBody() {
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
              onPressed: () => _loadTransactions(isRefresh: true),
              child: const Text('Retry'),
            ),
          ],
        ),
      );
    }

    if (_transactions.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(
              Icons.receipt_long_outlined,
              size: 64,
              color: Colors.grey,
            ),
            const SizedBox(height: 16),
            const Text(
              'No transactions yet',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w500,
                color: Colors.grey,
              ),
            ),
            const SizedBox(height: 8),
            const Text(
              'Transactions will appear here when available',
              style: TextStyle(
                fontSize: 14,
                color: Colors.grey,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 24),
            ElevatedButton(
              onPressed: () => _loadTransactions(isRefresh: true),
              child: const Text('Retry'),
            ),
          ],
        ),
      );
    }

    return ListView.builder(
      itemCount: _transactions.length + (_hasMorePages ? 1 : 0),
      itemBuilder: (context, index) {
        if (index == _transactions.length) {
          // Load more button
          return Padding(
            padding: const EdgeInsets.all(16.0),
            child: Center(
              child: _isLoading
                  ? const CircularProgressIndicator()
                  : ElevatedButton(
                      onPressed: _loadMoreTransactions,
                      child: const Text('Load More'),
                    ),
            ),
          );
        }

        final transaction = _transactions[index];
        return Padding(
          padding: EdgeInsets.only(
            left: 16,
            right: 16,
            bottom: index == _transactions.length - 1 ? 16 : 8,
            top: index == 0 ? 16 : 0,
          ),
          child: TransactionTile(
            transaction: transaction,
            onTap: () {
              // Navigate to transaction details
              print('[TransactionsList] Tapped transaction: ${transaction.id}');
              Navigator.of(context).pushNamed(
                '/transaction-details',
                arguments: transaction.id,
              );
            },
          ),
        );
      },
    );
  }
}