import { useState } from 'react';
import { Transaction } from '@/lib/api';

interface TransactionTableProps {
  transactions: Transaction[];
  onOverride: (transaction: Transaction) => void;
  selectedTxs: string[];
  onSelectionChange: (selected: string[]) => void;
}

export default function TransactionTable({
  transactions,
  onOverride,
  selectedTxs,
  onSelectionChange,
}: TransactionTableProps) {
  const [sortField, setSortField] = useState<keyof Transaction>('timestamp');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');

  const handleSort = (field: keyof Transaction) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('asc');
    }
  };

  const sortedTransactions = [...transactions].sort((a, b) => {
    // const aVal = a[sortField];
    // const bVal = b[sortField];

    const aVal = 20;
    const bVal = 30;
    
    if (aVal < bVal) return sortDirection === 'asc' ? -1 : 1;
    if (aVal > bVal) return sortDirection === 'asc' ? 1 : -1;
    return 0;
  });

  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      onSelectionChange(transactions.map(tx => tx.hash));
    } else {
      onSelectionChange([]);
    }
  };

  const handleSelectTx = (hash: string, checked: boolean) => {
    if (checked) {
      onSelectionChange([...selectedTxs, hash]);
    } else {
      onSelectionChange(selectedTxs.filter(h => h !== hash));
    }
  };

  const getStatusBadge = (status: Transaction['status']) => {
    const styles = {
      pending: 'badge-warning',
      confirmed: 'badge-success', 
      flagged: 'badge-danger',
      blocked: 'badge-danger',
    };
    return styles[status] || 'badge-warning';
  };

  const getAnchorStatusBadge = (status: Transaction['anchor_status']) => {
    if (!status || status === 'not_anchored') return null;
    
    const styles = {
      anchored: 'badge-success',
      anchor_pending: 'badge-warning',
    };
    return styles[status];
  };

  const formatAmount = (amount: string) => {
    const num = parseFloat(amount);
    return num.toLocaleString('en-US', { 
      minimumFractionDigits: 2,
      maximumFractionDigits: 6 
    });
  };

  const formatAddress = (address: string) => {
    return `${address.slice(0, 6)}...${address.slice(-4)}`;
  };

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleString();
  };

  const getRiskColor = (score: number) => {
    if (score >= 80) return 'text-red-600';
    if (score >= 60) return 'text-yellow-600';
    if (score >= 40) return 'text-blue-600';
    return 'text-green-600';
  };

  const allSelected = transactions.length > 0 && selectedTxs.length === transactions.length;
  const someSelected = selectedTxs.length > 0 && selectedTxs.length < transactions.length;

  return (
    <div className="card p-0 overflow-hidden">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left">
                <input
                  type="checkbox"
                  checked={allSelected}
                  ref={input => {
                    if (input) input.indeterminate = someSelected;
                  }}
                  onChange={(e) => handleSelectAll(e.target.checked)}
                  className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                />
              </th>
              <th 
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('timestamp')}
              >
                Time {sortField === 'timestamp' && (sortDirection === 'asc' ? '↑' : '↓')}
              </th>
              <th 
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('hash')}
              >
                Transaction {sortField === 'hash' && (sortDirection === 'asc' ? '↑' : '↓')}
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                From → To
              </th>
              <th 
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('amount')}
              >
                Amount {sortField === 'amount' && (sortDirection === 'asc' ? '↑' : '↓')}
              </th>
              <th 
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('risk_score')}
              >
                Risk {sortField === 'risk_score' && (sortDirection === 'asc' ? '↑' : '↓')}
              </th>
              <th 
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('status')}
              >
                Status {sortField === 'status' && (sortDirection === 'asc' ? '↑' : '↓')}
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Anchor
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {sortedTransactions.map((tx) => (
              <tr key={tx.id} className="hover:bg-gray-50">
                <td className="px-6 py-4">
                  <input
                    type="checkbox"
                    checked={selectedTxs.includes(tx.hash)}
                    onChange={(e) => handleSelectTx(tx.hash, e.target.checked)}
                    className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                  />
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {formatTimestamp(tx.timestamp)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-sm text-gray-900 font-mono">
                    {formatAddress(tx.hash)}
                  </div>
                  {tx.block_number && (
                    <div className="text-xs text-gray-500">
                      Block #{tx.block_number.toLocaleString()}
                    </div>
                  )}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-sm text-gray-900 font-mono">
                    {formatAddress(tx.from_address)}
                  </div>
                  <div className="text-xs text-gray-500 flex items-center">
                    <span>→</span>
                    <span className="ml-1">{formatAddress(tx.to_address)}</span>
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {formatAmount(tx.amount)} ETH
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className={`text-sm font-medium ${getRiskColor(tx.risk_score)}`}>
                    {tx.risk_score}%
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getStatusBadge(tx.status)}`}>
                    {tx.status}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  {tx.anchor_status && tx.anchor_status !== 'not_anchored' ? (
                    <div className="space-y-1">
                      <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getAnchorStatusBadge(tx.anchor_status)}`}>
                        {tx.anchor_status.replace('_', ' ')}
                      </span>
                      {tx.anchor_tx_hash && (
                        <div className="text-xs text-gray-500 font-mono">
                          {formatAddress(tx.anchor_tx_hash)}
                        </div>
                      )}
                    </div>
                  ) : (
                    <span className="text-xs text-gray-400">Not anchored</span>
                  )}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium space-x-2">
                  <button
                    onClick={() => onOverride(tx)}
                    className="text-primary-600 hover:text-primary-900 transition-colors"
                  >
                    Override
                  </button>
                  {tx.hash && (
                    <a
                      href={`${process.env.NEXT_PUBLIC_EXPLORER_BASE_URL}/tx/${tx.hash}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-600 hover:text-blue-900 transition-colors"
                    >
                      Explorer ↗
                    </a>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        
        {transactions.length === 0 && (
          <div className="text-center py-12">
            <div className="text-gray-400 text-lg mb-2">No transactions found</div>
            <div className="text-gray-500 text-sm">
              Transactions will appear here when they are detected by the monitoring system.
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
