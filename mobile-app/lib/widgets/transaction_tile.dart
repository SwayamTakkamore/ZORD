import 'package:flutter/material.dart';
import '../models/transaction.dart';

class TransactionTile extends StatelessWidget {
  final Transaction transaction;
  final VoidCallback? onTap;

  const TransactionTile({
    Key? key,
    required this.transaction,
    this.onTap,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 2,
      margin: EdgeInsets.zero,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(8),
        child: Padding(
          padding: const EdgeInsets.all(16.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _buildHeader(),
              const SizedBox(height: 12),
              _buildFromToSection(),
              const SizedBox(height: 12),
              _buildDetailsSection(),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildHeader() {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.center,
      children: [
        _buildDecisionChip(),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                transaction.formattedAmount,
                style: const TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                ),
              ),
              Text(
                'ID: ${transaction.shortId}',
                style: TextStyle(
                  fontSize: 12,
                  color: Colors.grey[600],
                  fontFamily: 'monospace',
                ),
              ),
            ],
          ),
        ),
        Text(
          transaction.formattedTimestamp,
          style: TextStyle(
            fontSize: 12,
            color: Colors.grey[600],
          ),
        ),
      ],
    );
  }

  Widget _buildDecisionChip() {
    Color chipColor;
    Color textColor;
    IconData icon;

    switch (transaction.decision?.toLowerCase()) {
      case 'approve':
      case 'approved':
        chipColor = Colors.green;
        textColor = Colors.white;
        icon = Icons.check_circle;
        break;
      case 'reject':
      case 'rejected':
        chipColor = Colors.red;
        textColor = Colors.white;
        icon = Icons.cancel;
        break;
      case 'pending':
        chipColor = Colors.orange;
        textColor = Colors.white;
        icon = Icons.access_time;
        break;
      default:
        chipColor = Colors.grey;
        textColor = Colors.white;
        icon = Icons.help;
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: chipColor,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            icon,
            size: 14,
            color: textColor,
          ),
          const SizedBox(width: 4),
          Text(
            transaction.decision?.toUpperCase() ?? 'UNKNOWN',
            style: TextStyle(
              fontSize: 10,
              fontWeight: FontWeight.bold,
              color: textColor,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildFromToSection() {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.grey[50],
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.grey[200]!),
      ),
      child: Column(
        children: [
          _buildAddressRow(
            label: 'From',
            address: transaction.shortFromAddress,
            icon: Icons.account_balance_wallet,
            iconColor: Colors.blue,
          ),
          const SizedBox(height: 8),
          Icon(
            Icons.arrow_downward,
            size: 16,
            color: Colors.grey[600],
          ),
          const SizedBox(height: 8),
          _buildAddressRow(
            label: 'To',
            address: transaction.shortToAddress,
            icon: Icons.account_balance_wallet_outlined,
            iconColor: Colors.green,
          ),
        ],
      ),
    );
  }

  Widget _buildAddressRow({
    required String label,
    required String address,
    required IconData icon,
    required Color iconColor,
  }) {
    return Row(
      children: [
        Icon(
          icon,
          size: 16,
          color: iconColor,
        ),
        const SizedBox(width: 8),
        Text(
          '$label:',
          style: TextStyle(
            fontSize: 12,
            fontWeight: FontWeight.w500,
            color: Colors.grey[700],
          ),
        ),
        const SizedBox(width: 8),
        Expanded(
          child: Text(
            address,
            style: const TextStyle(
              fontSize: 12,
              fontFamily: 'monospace',
            ),
            overflow: TextOverflow.ellipsis,
          ),
        ),
      ],
    );
  }

  Widget _buildDetailsSection() {
    return Row(
      children: [
        if (transaction.currency?.isNotEmpty == true) ...[
          _buildDetailChip(
            label: 'Currency',
            value: transaction.currency!,
            icon: Icons.currency_exchange,
            color: Colors.purple,
          ),
          const SizedBox(width: 8),
        ],
        if (transaction.network?.isNotEmpty == true) ...[
          _buildDetailChip(
            label: 'Network',
            value: transaction.network!,
            icon: Icons.hub,
            color: Colors.indigo,
          ),
          const SizedBox(width: 8),
        ],
        if (transaction.type?.isNotEmpty == true) ...[
          _buildDetailChip(
            label: 'Type',
            value: transaction.type!,
            icon: Icons.category,
            color: Colors.teal,
          ),
        ],
      ],
    );
  }

  Widget _buildDetailChip({
    required String label,
    required String value,
    required IconData icon,
    required Color color,
  }) {
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
          Icon(
            icon,
            size: 12,
            color: color,
          ),
          const SizedBox(width: 4),
          Text(
            value,
            style: TextStyle(
              fontSize: 10,
              fontWeight: FontWeight.w500,
              color: color,
            ),
          ),
        ],
      ),
    );
  }
}