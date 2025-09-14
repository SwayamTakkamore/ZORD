import 'package:intl/intl.dart';

/// Transaction status for compliance decision mapping
enum TransactionStatus {
  pending,
  confirmed,
  flagged,
  blocked,
}

/// Anchor status for blockchain anchoring
enum AnchorStatus {
  notAnchored,
  anchorPending,
  anchored,
}

class Transaction {
  final String id;
  final String hash;
  final String fromAddress;
  final String toAddress;
  final String amount;
  final TransactionStatus status;
  final double riskScore;
  final DateTime timestamp;
  final AnchorStatus anchorStatus;
  final String? currency;
  final String? decision;
  final String? evidenceHash;
  final String? memo;
  final String? network;
  final String? type;

  const Transaction({
    required this.id,
    required this.hash,
    required this.fromAddress,
    required this.toAddress,
    required this.amount,
    required this.status,
    required this.riskScore,
    required this.timestamp,
    required this.anchorStatus,
    this.currency,
    this.decision,
    this.evidenceHash,
    this.memo,
    this.network,
    this.type,
  });

  factory Transaction.fromJson(Map<String, dynamic> json) {
    // Handle multiple possible ID fields
    final txUuid = json['tx_uuid'] ?? json['tx_id'] ?? json['id'] ?? '';

    // Handle multiple possible address fields
    final walletFrom = json['wallet_from'] ?? json['from_address'] ?? '';
    final walletTo = json['wallet_to'] ?? json['to_address'] ?? '';

    // Handle multiple possible currency fields
    final currencyValue = json['currency'] ?? json['asset'] ?? 'ETH';

    // Robust amount parsing
    final amountRaw = json['amount'] ?? json['value'] ?? '0';
    final amountNum = (amountRaw is num)
        ? amountRaw.toDouble()
        : double.tryParse(amountRaw.toString()) ?? 0.0;
    final amountStr = amountNum.toString();

    // Parse created_at with fallback
    DateTime createdAt = DateTime.now();
    final createdAtStr = json['created_at'] ?? json['timestamp'];
    if (createdAtStr != null) {
      final parsed = DateTime.tryParse(createdAtStr.toString());
      if (parsed != null) createdAt = parsed;
    }

    // Parse decision and map to status
    final decisionValue = json['decision'] ?? 'UNKNOWN';
    TransactionStatus txStatus = TransactionStatus.pending;
    switch (decisionValue.toString().toUpperCase()) {
      case 'PASS':
      case 'CONFIRMED':
        txStatus = TransactionStatus.confirmed;
        break;
      case 'BLOCK':
      case 'BLOCKED':
      case 'REJECT':
        txStatus = TransactionStatus.blocked;
        break;
      case 'FLAGGED':
        txStatus = TransactionStatus.flagged;
        break;
      default:
        txStatus = TransactionStatus.pending;
    }

    final riskScoreRaw = json['risk_score'] ?? json['score'] ?? 0.0;
    final riskScoreValue = (riskScoreRaw is num)
        ? riskScoreRaw.toDouble()
        : double.tryParse(riskScoreRaw.toString()) ?? 0.0;

    print(
        '[Transaction.fromJson] Parsed: id=$txUuid, from=$walletFrom, to=$walletTo, amount=$amountStr, currency=$currencyValue, decision=$decisionValue');

    return Transaction(
      id: txUuid,
      hash: json['hash'] ?? json['tx_hash'] ?? txUuid,
      fromAddress: walletFrom,
      toAddress: walletTo,
      amount: amountStr,
      status: txStatus,
      riskScore: riskScoreValue,
      timestamp: createdAt,
      anchorStatus: AnchorStatus.notAnchored,
      currency: currencyValue,
      decision: decisionValue,
      evidenceHash: json['evidence_hash'],
      memo: json['memo'] ?? json['description'],
      network: json['network'] ?? json['chain'],
      type: json['type'] ?? json['transaction_type'],
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'hash': hash,
      'from_address': fromAddress,
      'to_address': toAddress,
      'amount': amount,
      'status': status.name,
      'risk_score': riskScore,
      'timestamp': timestamp.toIso8601String(),
      'anchor_status': anchorStatus.name,
      'currency': currency,
      'decision': decision,
      'evidence_hash': evidenceHash,
      'memo': memo,
      'network': network,
      'type': type,
    };
  }

  String get shortId =>
      id.length > 10 ? '${id.substring(0, 10)}...' : id;
  String get shortFromAddress =>
      fromAddress.length > 10 ? '${fromAddress.substring(0, 10)}...' : fromAddress;
  String get shortToAddress =>
      toAddress.length > 10 ? '${toAddress.substring(0, 10)}...' : toAddress;
  String get formattedTimestamp =>
      DateFormat('yyyy-MM-dd HH:mm').format(timestamp);
  String get formattedAmount => '$amount ${currency ?? 'ETH'}';

  Transaction copyWith({
    String? id,
    String? hash,
    String? fromAddress,
    String? toAddress,
    String? amount,
    TransactionStatus? status,
    double? riskScore,
    DateTime? timestamp,
    AnchorStatus? anchorStatus,
    String? currency,
    String? decision,
    String? evidenceHash,
    String? memo,
    String? network,
    String? type,
  }) {
    return Transaction(
      id: id ?? this.id,
      hash: hash ?? this.hash,
      fromAddress: fromAddress ?? this.fromAddress,
      toAddress: toAddress ?? this.toAddress,
      amount: amount ?? this.amount,
      status: status ?? this.status,
      riskScore: riskScore ?? this.riskScore,
      timestamp: timestamp ?? this.timestamp,
      anchorStatus: anchorStatus ?? this.anchorStatus,
      currency: currency ?? this.currency,
      decision: decision ?? this.decision,
      evidenceHash: evidenceHash ?? this.evidenceHash,
      memo: memo ?? this.memo,
      network: network ?? this.network,
      type: type ?? this.type,
    );
  }
}

/// Anchor request payload
class AnchorRequest {
  final String merkleRoot;
  final List<String> transactions;

  const AnchorRequest({
    required this.merkleRoot,
    required this.transactions,
  });

  Map<String, dynamic> toJson() {
    return {
      'merkle_root': merkleRoot,
      'transactions': transactions,
    };
  }
}

/// Anchor response payload
class AnchorResponse {
  final String txHash;
  final String merkleRoot;
  final int blockNumber;
  final String explorerUrl;

  const AnchorResponse({
    required this.txHash,
    required this.merkleRoot,
    required this.blockNumber,
    required this.explorerUrl,
  });

  factory AnchorResponse.fromJson(Map<String, dynamic> json) {
    return AnchorResponse(
      txHash: json['tx_hash'] as String,
      merkleRoot: json['merkle_root'] as String,
      blockNumber: json['block_number'] as int,
      explorerUrl: json['explorer_url'] as String,
    );
  }
}

/// Manual override request
class OverrideRequest {
  final String transactionHash;
  final TransactionStatus newStatus;
  final String reason;

  const OverrideRequest({
    required this.transactionHash,
    required this.newStatus,
    required this.reason,
  });

  Map<String, dynamic> toJson() {
    return {
      'transaction_hash': transactionHash,
      'new_status': newStatus.name,
      'reason': reason,
    };
  }
}

/// User model
class User {
  final String id;
  final String username;
  final String email;
  final String role;
  final String token;

  const User({
    required this.id,
    required this.username,
    required this.email,
    required this.role,
    required this.token,
  });

  factory User.fromJson(Map<String, dynamic> json) {
    return User(
      id: json['id'] as String,
      username: json['username'] as String,
      email: json['email'] as String,
      role: json['role'] as String,
      token: json['token'] as String,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'username': username,
      'email': email,
      'role': role,
      'token': token,
    };
  }
}

/// Dashboard stats aggregator
class DashboardStats {
  final int totalTransactions;
  final int pendingTransactions;
  final int flaggedTransactions;
  final int confirmedTransactions;
  final int anchoredTransactions;
  final int blockedTransactions;

  const DashboardStats({
    required this.totalTransactions,
    required this.pendingTransactions,
    required this.flaggedTransactions,
    required this.confirmedTransactions,
    required this.anchoredTransactions,
    required this.blockedTransactions,
  });

  factory DashboardStats.fromTransactions(List<Transaction> transactions) {
    return DashboardStats(
      totalTransactions: transactions.length,
      pendingTransactions:
      transactions.where((t) => t.status == TransactionStatus.pending).length,
      flaggedTransactions:
      transactions.where((t) => t.status == TransactionStatus.flagged).length,
      confirmedTransactions:
      transactions.where((t) => t.status == TransactionStatus.confirmed).length,
      anchoredTransactions:
      transactions.where((t) => t.anchorStatus == AnchorStatus.anchored).length,
      blockedTransactions:
      transactions.where((t) => t.status == TransactionStatus.blocked).length
    );
  }
}
