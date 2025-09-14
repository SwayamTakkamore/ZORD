import 'package:flutter/material.dart';
import '../models/transaction.dart';

class TransactionCard extends StatelessWidget {
  final Transaction transaction;
  final VoidCallback? onTap;
  final VoidCallback? onOverride;

  const TransactionCard({
    super.key,
    required this.transaction,
    this.onTap,
    this.onOverride,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Header row with status and risk
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  _buildStatusChip(transaction.status),
                  _buildRiskScore(transaction.riskScore),
                ],
              ),
              
              const SizedBox(height: 12),
              
              // Transaction hash
              Text(
                transaction.hash.length > 20
                    ? '${transaction.hash.substring(0, 10)}...${transaction.hash.substring(transaction.hash.length - 10)}'
                    : transaction.hash,
                style: const TextStyle(
                  fontFamily: 'monospace',
                  fontWeight: FontWeight.w600,
                  fontSize: 16,
                ),
              ),
              
              const SizedBox(height: 8),
              
              // Amount and timestamp
              Row(
                children: [
                  Expanded(
                    child: Row(
                      children: [
                        const Icon(
                          Icons.account_balance_wallet,
                          size: 16,
                          color: Colors.grey,
                        ),
                        const SizedBox(width: 4),
                        Text(
                          '${transaction.amount} ETH',
                          style: const TextStyle(
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ],
                    ),
                  ),
                  Text(
                    _formatTime(transaction.timestamp),
                    style: TextStyle(
                      color: Colors.grey[600],
                      fontSize: 12,
                    ),
                  ),
                ],
              ),
              
              const SizedBox(height: 8),
              
              // Addresses
              _buildAddressRow(
                'From',
                transaction.fromAddress,
                Icons.call_made,
              ),
              const SizedBox(height: 4),
              _buildAddressRow(
                'To',
                transaction.toAddress,
                Icons.call_received,
              ),
              
              // Anchor status
              if (transaction.anchorStatus != AnchorStatus.notAnchored) ...[
                const SizedBox(height: 8),
                _buildAnchorStatus(transaction.anchorStatus),
              ],
              
              // Action buttons
              const SizedBox(height: 12),
              Row(
                children: [
                  Expanded(
                    child: OutlinedButton.icon(
                      onPressed: onTap,
                      icon: const Icon(Icons.visibility, size: 16),
                      label: const Text('View Details'),
                      style: OutlinedButton.styleFrom(
                        padding: const EdgeInsets.symmetric(vertical: 8),
                      ),
                    ),
                  ),
                  if (onOverride != null) ...[
                    const SizedBox(width: 8),
                    Expanded(
                      child: ElevatedButton.icon(
                        onPressed: onOverride,
                        icon: const Icon(Icons.edit, size: 16),
                        label: const Text('Override'),
                        style: ElevatedButton.styleFrom(
                          padding: const EdgeInsets.symmetric(vertical: 8),
                        ),
                      ),
                    ),
                  ],
                ],
              ),
            ],
          ),
        ),
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

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 12, color: color),
          const SizedBox(width: 4),
          Text(
            status.name.toUpperCase(),
            style: TextStyle(
              color: color,
              fontSize: 10,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildRiskScore(double riskScore) {
    Color color = _getRiskColor(riskScore);
    
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Text(
        '${riskScore.toInt()}%',
        style: TextStyle(
          color: color,
          fontSize: 12,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }

  Widget _buildAddressRow(String label, String address, IconData icon) {
    final shortAddress = address.length > 20
        ? '${address.substring(0, 6)}...${address.substring(address.length - 4)}'
        : address;

    return Row(
      children: [
        Icon(icon, size: 14, color: Colors.grey),
        const SizedBox(width: 4),
        Text(
          '$label: ',
          style: TextStyle(
            color: Colors.grey[600],
            fontSize: 12,
          ),
        ),
        Text(
          shortAddress,
          style: const TextStyle(
            fontFamily: 'monospace',
            fontSize: 12,
          ),
        ),
      ],
    );
  }

  Widget _buildAnchorStatus(AnchorStatus status) {
    Color color;
    IconData icon;
    String text;

    switch (status) {
      case AnchorStatus.notAnchored:
        return const SizedBox.shrink();
      case AnchorStatus.anchorPending:
        color = Colors.orange;
        icon = Icons.hourglass_empty;
        text = 'Anchoring...';
        break;
      case AnchorStatus.anchored:
        color = Colors.green;
        icon = Icons.anchor;
        text = 'Anchored';
        break;
    }

    return Row(
      children: [
        Icon(icon, size: 14, color: color),
        const SizedBox(width: 4),
        Text(
          text,
          style: TextStyle(
            color: color,
            fontSize: 12,
            fontWeight: FontWeight.w500,
          ),
        ),
      ],
    );
  }

  Color _getRiskColor(double riskScore) {
    if (riskScore >= 80) return Colors.red;
    if (riskScore >= 60) return Colors.orange;
    if (riskScore >= 40) return Colors.blue;
    return Colors.green;
  }

  String _formatTime(DateTime timestamp) {
    final now = DateTime.now();
    final difference = now.difference(timestamp);

    if (difference.inMinutes < 1) {
      return 'Just now';
    } else if (difference.inMinutes < 60) {
      return '${difference.inMinutes}m ago';
    } else if (difference.inHours < 24) {
      return '${difference.inHours}h ago';
    } else {
      return '${difference.inDays}d ago';
    }
  }
}
