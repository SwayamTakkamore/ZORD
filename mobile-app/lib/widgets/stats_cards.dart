import 'package:flutter/material.dart';
import '../models/transaction.dart';

class StatsCards extends StatelessWidget {
  final DashboardStats stats;

  const StatsCards({
    super.key,
    required this.stats,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Row(
          children: [
            Expanded(
              child: _StatCard(
                title: 'Total',
                value: stats.totalTransactions.toString(),
                icon: Icons.receipt_long,
                color: Colors.blue,
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),
        Row(
          children: [
            Expanded(
              child: _StatCard(
                title: 'Confirmed',
                value: stats.confirmedTransactions.toString(),
                icon: Icons.check_circle,
                color: Colors.green,
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: _StatCard(
                title: 'Blocked',
                value: stats.blockedTransactions.toString(),
                icon: Icons.block,
                color: Colors.red,
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),
        Row(
          children: [
            Expanded(
              child: _StatCard(
                title: 'Pending',
                value: stats.pendingTransactions.toString(),
                icon: Icons.hourglass_empty,
                color: Colors.orange,
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: _StatCard(
                title: 'Flagged',
                value: stats.flaggedTransactions.toString(),
                icon: Icons.flag,
                color: Colors.black,
              ),
            ),
            // Expanded(
            //   child: _StatCard(
            //     title: 'Anchored',
            //     value: stats.anchoredTransactions.toString(),
            //     icon: Icons.anchor,
            //     color: Colors.purple,
            //   ),
            // ),
          ],
        ),

      ],
    );
  }
}

class _StatCard extends StatelessWidget {
  final String title;
  final String value;
  final IconData icon;
  final Color color;
  final bool isWide;

  const _StatCard({
    required this.title,
    required this.value,
    required this.icon,
    required this.color,
    this.isWide = false,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: color.withOpacity(0.1),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Icon(
                icon,
                color: color,
                size: 24,
              ),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    value,
                    style: const TextStyle(
                      fontSize: 24,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  Text(
                    title,
                    style: TextStyle(
                      fontSize: 14,
                      color: Colors.grey[600],
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
