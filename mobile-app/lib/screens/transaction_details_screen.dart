import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:url_launcher/url_launcher.dart';

import '../models/transaction.dart';
import '../services/api_service.dart';
import '../services/storage_service.dart';

class TransactionDetailsScreen extends ConsumerStatefulWidget {
  final String transactionId;

  const TransactionDetailsScreen({
    super.key,
    required this.transactionId,
  });

  @override
  ConsumerState<TransactionDetailsScreen> createState() =>
      _TransactionDetailsScreenState();
}

class _TransactionDetailsScreenState
    extends ConsumerState<TransactionDetailsScreen> {
  Transaction? _transaction;
  bool _isLoading = true;
  bool _isOverrideLoading = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadTransaction();
  }

  Future<void> _loadTransaction() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      // First try to get from cache
      final cachedTransaction = StorageService.getCachedTransaction(widget.transactionId);
      if (cachedTransaction != null) {
        setState(() {
          _transaction = cachedTransaction;
          _isLoading = false;
        });
        return;
      }

      // If not in cache, fetch from API
      final apiService = ref.read(apiServiceProvider);
      final transaction = await apiService.getTransaction(widget.transactionId);
      
      if (mounted) {
        setState(() {
          _transaction = transaction;
          _isLoading = false;
        });
        
        // Cache the transaction
        await StorageService.cacheTransaction(transaction);
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = e.toString().replaceAll('Exception: ', '');
          _isLoading = false;
        });
      }
      print('[TransactionDetails] Failed to load transaction: $e');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Transaction Details'),
        actions: [
          if (_transaction != null)
            IconButton(
              icon: const Icon(Icons.open_in_new),
              onPressed: _openInExplorer,
              tooltip: 'View in Explorer',
            ),
        ],
      ),
      body: _buildBody(),
    );
  }

  Widget _buildBody() {
    if (_isLoading) {
      return const Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            CircularProgressIndicator(),
            SizedBox(height: 16),
            Text('Loading transaction details...'),
          ],
        ),
      );
    }

    if (_error != null) {
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
              onPressed: _loadTransaction,
              child: const Text('Retry'),
            ),
          ],
        ),
      );
    }

    if (_transaction == null) {
      return const Center(
        child: Text('Transaction not found'),
      );
    }

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildStatusCard(),
          const SizedBox(height: 16),
          _buildTransactionInfo(),
          const SizedBox(height: 16),
          _buildAddressInfo(),
          const SizedBox(height: 16),
          _buildRiskAssessment(),
          if (_transaction!.anchorStatus != AnchorStatus.notAnchored) ...[
            const SizedBox(height: 16),
            _buildAnchorInfo(),
          ],
          const SizedBox(height: 16),
          _buildActionButtons(),
        ],
      ),
    );
  }

  Widget _buildStatusCard() {
    final transaction = _transaction!;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Status',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                _buildStatusChip(transaction.status),
                const SizedBox(width: 12),
                Text(
                  _getStatusDescription(transaction.status),
                  style: TextStyle(
                    color: Colors.grey[600],
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildTransactionInfo() {
    final transaction = _transaction!;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Transaction Information',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 16),
            _buildInfoRow('Hash', transaction.hash, copyable: true),
            _buildInfoRow('Amount', transaction.formattedAmount),
            _buildInfoRow('Timestamp', _formatDateTime(transaction.timestamp)),
            if (transaction.network?.isNotEmpty == true)
              _buildInfoRow('Network', transaction.network!),
            if (transaction.type?.isNotEmpty == true)
              _buildInfoRow('Type', transaction.type!),
            if (transaction.memo?.isNotEmpty == true)
              _buildInfoRow('Memo', transaction.memo!),
            if (transaction.decision?.isNotEmpty == true)
              _buildInfoRow('Decision', transaction.decision!.toUpperCase()),
          ],
        ),
      ),
    );
  }

  Widget _buildAddressInfo() {
    final transaction = _transaction!;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Addresses',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 16),
            _buildInfoRow('From', transaction.fromAddress, copyable: true),
            _buildInfoRow('To', transaction.toAddress, copyable: true),
          ],
        ),
      ),
    );
  }

  Widget _buildRiskAssessment() {
    final transaction = _transaction!;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Risk Assessment',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                Text(
                  'Risk Score: ',
                  style: TextStyle(color: Colors.grey[600]),
                ),
                Text(
                  '${transaction.riskScore.toInt()}%',
                  style: TextStyle(
                    fontWeight: FontWeight.w600,
                    color: _getRiskColor(transaction.riskScore),
                    fontSize: 16,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            LinearProgressIndicator(
              value: transaction.riskScore / 100,
              backgroundColor: Colors.grey[300],
              valueColor: AlwaysStoppedAnimation<Color>(
                _getRiskColor(transaction.riskScore),
              ),
            ),
            const SizedBox(height: 8),
            Text(
              _getRiskDescription(transaction.riskScore),
              style: TextStyle(
                color: Colors.grey[600],
                fontSize: 12,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildAnchorInfo() {
    final transaction = _transaction!;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Blockchain Anchor',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                _buildAnchorStatusChip(transaction.anchorStatus),
                const SizedBox(width: 12),
                Text(
                  _getAnchorDescription(transaction.anchorStatus),
                  style: TextStyle(
                    color: Colors.grey[600],
                  ),
                ),
              ],
            ),
            if (transaction.evidenceHash?.isNotEmpty == true) ...[
              const SizedBox(height: 16),
              _buildInfoRow('Evidence Hash', transaction.evidenceHash!, copyable: true),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildActionButtons() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Actions',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: _openInExplorer,
                    icon: const Icon(Icons.open_in_new),
                    label: const Text('View in Explorer'),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: _isOverrideLoading ? null : _showOverrideDialog,
                    icon: _isOverrideLoading 
                      ? const SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.edit),
                    label: Text(_isOverrideLoading ? 'Processing...' : 'Override'),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildInfoRow(String label, String value, {bool copyable = false}) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 100,
            child: Text(
              '$label:',
              style: TextStyle(
                color: Colors.grey[600],
                fontWeight: FontWeight.w500,
              ),
            ),
          ),
          Expanded(
            child: Row(
              children: [
                Expanded(
                  child: Text(
                    value,
                    style: const TextStyle(
                      fontFamily: 'monospace',
                    ),
                  ),
                ),
                if (copyable)
                  IconButton(
                    icon: const Icon(Icons.copy, size: 16),
                    onPressed: () => _copyToClipboard(value),
                    tooltip: 'Copy',
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildStatusChip(TransactionStatus status) {
    Color color;
    IconData icon;

    switch (status) {
      case TransactionStatus.pending:
        color = Colors.orange;
        icon = Icons.hourglass_empty;
        break;
      case TransactionStatus.confirmed:
        color = Colors.green;
        icon = Icons.check_circle;
        break;
      case TransactionStatus.flagged:
        color = Colors.red;
        icon = Icons.flag;
        break;
      case TransactionStatus.blocked:
        color = Colors.red;
        icon = Icons.block;
        break;
    }

    return Chip(
      avatar: Icon(icon, size: 16, color: color),
      label: Text(
        status.name.toUpperCase(),
        style: TextStyle(
          color: color,
          fontWeight: FontWeight.w600,
        ),
      ),
      backgroundColor: color.withOpacity(0.1),
      side: BorderSide(color: color),
    );
  }

  Widget _buildAnchorStatusChip(AnchorStatus status) {
    Color color;
    IconData icon;

    switch (status) {
      case AnchorStatus.notAnchored:
        color = Colors.grey;
        icon = Icons.link_off;
        break;
      case AnchorStatus.anchorPending:
        color = Colors.orange;
        icon = Icons.hourglass_empty;
        break;
      case AnchorStatus.anchored:
        color = Colors.green;
        icon = Icons.anchor;
        break;
    }

    return Chip(
      avatar: Icon(icon, size: 16, color: color),
      label: Text(
        status.name.replaceAll(RegExp(r'([A-Z])'), ' \$1').trim().toUpperCase(),
        style: TextStyle(
          color: color,
          fontWeight: FontWeight.w600,
        ),
      ),
      backgroundColor: color.withOpacity(0.1),
      side: BorderSide(color: color),
    );
  }

  Color _getRiskColor(double riskScore) {
    if (riskScore >= 80) return Colors.red;
    if (riskScore >= 60) return Colors.orange;
    if (riskScore >= 40) return Colors.blue;
    return Colors.green;
  }

  String _getRiskDescription(double riskScore) {
    if (riskScore >= 80) return 'High risk - Requires immediate attention';
    if (riskScore >= 60) return 'Medium risk - Review recommended';
    if (riskScore >= 40) return 'Low risk - Monitor activity';
    return 'Very low risk - Normal transaction';
  }

  String _getStatusDescription(TransactionStatus status) {
    switch (status) {
      case TransactionStatus.pending:
        return 'Awaiting compliance review';
      case TransactionStatus.confirmed:
        return 'Approved for processing';
      case TransactionStatus.flagged:
        return 'Flagged for manual review';
      case TransactionStatus.blocked:
        return 'Blocked from processing';
    }
  }

  String _getAnchorDescription(AnchorStatus status) {
    switch (status) {
      case AnchorStatus.notAnchored:
        return 'Not anchored to blockchain';
      case AnchorStatus.anchorPending:
        return 'Anchoring in progress';
      case AnchorStatus.anchored:
        return 'Anchored to blockchain';
    }
  }

  String _formatDateTime(DateTime dateTime) {
    return '${dateTime.day}/${dateTime.month}/${dateTime.year} '
           '${dateTime.hour.toString().padLeft(2, '0')}:'
           '${dateTime.minute.toString().padLeft(2, '0')}';
  }

  void _copyToClipboard(String text) {
    Clipboard.setData(ClipboardData(text: text));
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Copied to clipboard'),
        duration: Duration(seconds: 2),
      ),
    );
  }

  void _openInExplorer() async {
    if (_transaction == null) return;

    const explorerUrl = 'https://polygonscan.com';
    final url = '$explorerUrl/tx/${_transaction!.hash}';

    try {
      if (await canLaunchUrl(Uri.parse(url))) {
        await launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication);
      } else {
        _copyToClipboard(url);
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Explorer URL copied to clipboard'),
          ),
        );
      }
    } catch (e) {
      _copyToClipboard(url);
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Explorer URL copied to clipboard'),
        ),
      );
    }
  }

  void _showOverrideDialog() {
    final reasonController = TextEditingController();
    String selectedStatus = 'PASS';
    
    showDialog(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setDialogState) => AlertDialog(
          title: const Text('Override Transaction Decision'),
          content: SizedBox(
            width: double.maxFinite,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Transaction: ${_transaction?.hash?.substring(0, 16) ?? _transaction?.id ?? 'N/A'}...',
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    fontFamily: 'monospace',
                  ),
                ),
                const SizedBox(height: 16),
                Text(
                  'New Status:',
                  style: Theme.of(context).textTheme.titleSmall,
                ),
                const SizedBox(height: 8),
                DropdownButtonFormField<String>(
                  value: selectedStatus,
                  decoration: const InputDecoration(
                    border: OutlineInputBorder(),
                    isDense: true,
                  ),
                  items: const [
                    DropdownMenuItem(value: 'PASS', child: Text('PASS (Approved)')),
                    DropdownMenuItem(value: 'HOLD', child: Text('HOLD (Pending)')),
                    DropdownMenuItem(value: 'REJECT', child: Text('REJECT (Blocked)')),
                  ],
                  onChanged: (value) {
                    if (value != null) {
                      setDialogState(() {
                        selectedStatus = value;
                      });
                    }
                  },
                ),
                const SizedBox(height: 16),
                Text(
                  'Reason (required, min 10 characters):',
                  style: Theme.of(context).textTheme.titleSmall,
                ),
                const SizedBox(height: 8),
                TextField(
                  controller: reasonController,
                  decoration: const InputDecoration(
                    border: OutlineInputBorder(),
                    hintText: 'Enter reason for override...',
                    isDense: true,
                  ),
                  maxLines: 3,
                  maxLength: 500,
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text('Cancel'),
            ),
            ElevatedButton(
              onPressed: _isOverrideLoading ? null : () async {
                final reason = reasonController.text.trim();
                if (reason.length < 10) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(
                      content: Text('Reason must be at least 10 characters'),
                      backgroundColor: Colors.red,
                    ),
                  );
                  return;
                }
                
                Navigator.of(context).pop(); // Close dialog
                await _performOverride(selectedStatus, reason);
              },
              child: _isOverrideLoading 
                ? const SizedBox(
                    width: 16,
                    height: 16,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Text('Override'),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _performOverride(String newStatus, String reason) async {
    if (!mounted) return;
    
    setState(() {
      _isOverrideLoading = true;
    });

    try {
      final apiService = ref.read(apiServiceProvider);
      final txId = _transaction?.id ?? _transaction?.hash;
      
      if (txId == null) {
        throw Exception('Transaction ID not available');
      }

      final result = await apiService.overrideTransaction(
        txIdOrHash: txId,
        newStatus: newStatus,
        reason: reason,
      );

      if (mounted) {
        // Optimistic UI update
        setState(() {
          _transaction = _transaction?.copyWith(
            decision: result['new_decision'] ?? newStatus,
          );
        });

        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Override successful: $newStatus'),
            backgroundColor: Colors.green,
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Override failed: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() {
          _isOverrideLoading = false;
        });
      }
    }
  }
}
