import { useState } from 'react';
import { Transaction, apiClient } from '@/lib/api';

interface OverrideModalProps {
  transaction: Transaction;
  onClose: () => void;
  onComplete: () => void;
}

export default function OverrideModal({ transaction, onClose, onComplete }: OverrideModalProps) {
  const [newStatus, setNewStatus] = useState<'confirmed' | 'blocked'>('confirmed');
  const [reason, setReason] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!reason.trim()) {
      setError('Reason is required');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const response = await apiClient.overrideTransaction({
        transaction_hash: transaction.hash,
        new_status: newStatus,
        reason: reason.trim(),
      });

      if (response.error) {
        setError(response.error);
      } else {
        onComplete();
      }
    } catch (err) {
      setError('Failed to override transaction');
    } finally {
      setLoading(false);
    }
  };

  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  return (
    <div 
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50"
      onClick={handleBackdropClick}
    >
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-lg font-semibold text-gray-900">
              Override Transaction Status
            </h2>
            <button 
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 transition-colors"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Transaction Details */}
          <div className="bg-gray-50 rounded-lg p-4 mb-6">
            <h3 className="text-sm font-medium text-gray-700 mb-3">Transaction Details</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-500">Hash:</span>
                <span className="font-mono text-gray-900 truncate ml-2">
                  {transaction.hash.slice(0, 10)}...{transaction.hash.slice(-8)}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Current Status:</span>
                <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                  transaction.status === 'pending' ? 'bg-yellow-100 text-yellow-800' :
                  transaction.status === 'confirmed' ? 'bg-green-100 text-green-800' :
                  transaction.status === 'flagged' ? 'bg-red-100 text-red-800' :
                  'bg-gray-100 text-gray-800'
                }`}>
                  {transaction.status}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Risk Score:</span>
                <span className={`font-medium ${
                  transaction.risk_score >= 80 ? 'text-red-600' :
                  transaction.risk_score >= 60 ? 'text-yellow-600' :
                  transaction.risk_score >= 40 ? 'text-blue-600' :
                  'text-green-600'
                }`}>
                  {transaction.risk_score}%
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Amount:</span>
                <span className="text-gray-900">
                  {parseFloat(transaction.amount).toLocaleString()} ETH
                </span>
              </div>
            </div>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            {/* New Status Selection */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-3">
                New Status
              </label>
              <div className="space-y-3">
                <label className="flex items-center">
                  <input
                    type="radio"
                    name="status"
                    value="confirmed"
                    checked={newStatus === 'confirmed'}
                    onChange={(e) => setNewStatus(e.target.value as 'confirmed')}
                    className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300"
                  />
                  <div className="ml-3">
                    <div className="text-sm font-medium text-gray-900">Confirm Transaction</div>
                    <div className="text-sm text-gray-500">Mark as safe and allow processing</div>
                  </div>
                </label>
                <label className="flex items-center">
                  <input
                    type="radio"
                    name="status"
                    value="blocked"
                    checked={newStatus === 'blocked'}
                    onChange={(e) => setNewStatus(e.target.value as 'blocked')}
                    className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300"
                  />
                  <div className="ml-3">
                    <div className="text-sm font-medium text-gray-900">Block Transaction</div>
                    <div className="text-sm text-gray-500">Mark as suspicious and prevent processing</div>
                  </div>
                </label>
              </div>
            </div>

            {/* Reason Input */}
            <div>
              <label htmlFor="reason" className="block text-sm font-medium text-gray-700 mb-2">
                Reason for Override *
              </label>
              <textarea
                id="reason"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                rows={4}
                className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
                placeholder="Explain why you are overriding the automatic decision..."
                required
              />
              <p className="mt-1 text-xs text-gray-500">
                This reason will be logged for audit purposes.
              </p>
            </div>

            {error && (
              <div className="rounded-md bg-red-50 p-4">
                <div className="text-sm text-red-700">{error}</div>
              </div>
            )}

            {/* Action Buttons */}
            <div className="flex space-x-3 pt-4">
              <button
                type="button"
                onClick={onClose}
                className="flex-1 btn-secondary"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={loading || !reason.trim()}
                className={`flex-1 font-medium py-2 px-4 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${
                  newStatus === 'confirmed' 
                    ? 'bg-green-600 hover:bg-green-700 text-white' 
                    : 'bg-red-600 hover:bg-red-700 text-white'
                }`}
              >
                {loading ? 'Processing...' : `${newStatus === 'confirmed' ? 'Confirm' : 'Block'} Transaction`}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
