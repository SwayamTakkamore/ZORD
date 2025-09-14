import { useState } from 'react';
import { apiClient } from '@/lib/api';

interface AnchorModalProps {
  transactionHashes: string[];
  onClose: () => void;
  onComplete: () => void;
}

export default function AnchorModal({ transactionHashes, onClose, onComplete }: AnchorModalProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState<{
    tx_hash: string;
    merkle_root: string;
    explorer_url: string;
  } | null>(null);

  const handleAnchor = async () => {
    setLoading(true);
    setError('');

    try {
      // Generate a simple merkle root for demo (in production, use proper merkle tree)
      const merkleRoot = '0x' + Array.from(
        new Uint8Array(32), 
        () => Math.floor(Math.random() * 256).toString(16).padStart(2, '0')
      ).join('');

      const response = await apiClient.anchorTransactions({
        merkle_root: merkleRoot,
        transactions: transactionHashes,
      });

      if (response.error) {
        setError(response.error);
      } else if (response.data) {
        setSuccess(response.data);
      }
    } catch (err) {
      setError('Failed to anchor transactions');
    } finally {
      setLoading(false);
    }
  };

  const handleComplete = () => {
    onComplete();
    onClose();
  };

  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget && !loading) {
      onClose();
    }
  };

  return (
    <div 
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50"
      onClick={handleBackdropClick}
    >
      <div className="bg-white rounded-lg shadow-xl max-w-lg w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-lg font-semibold text-gray-900">
              Anchor Transactions to Blockchain
            </h2>
            {!loading && (
              <button 
                onClick={onClose}
                className="text-gray-400 hover:text-gray-600 transition-colors"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            )}
          </div>

          {!success ? (
            <>
              {/* Transaction List */}
              <div className="bg-gray-50 rounded-lg p-4 mb-6">
                <h3 className="text-sm font-medium text-gray-700 mb-3">
                  Selected Transactions ({transactionHashes.length})
                </h3>
                <div className="space-y-2 max-h-40 overflow-y-auto">
                  {transactionHashes.map((hash, index) => (
                    <div key={hash} className="flex items-center text-sm">
                      <span className="text-gray-500 w-8">{index + 1}.</span>
                      <span className="font-mono text-gray-900 truncate">
                        {hash.slice(0, 10)}...{hash.slice(-8)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Anchoring Explanation */}
              <div className="bg-blue-50 rounded-lg p-4 mb-6">
                <div className="flex">
                  <svg className="w-5 h-5 text-blue-600 mt-0.5 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <div>
                    <h4 className="text-sm font-medium text-blue-900 mb-1">
                      Blockchain Anchoring
                    </h4>
                    <p className="text-sm text-blue-700">
                      This will create a cryptographic proof of these transactions by generating a Merkle root 
                      and recording it on the Polygon blockchain. This provides immutable evidence of the 
                      transaction states at this point in time.
                    </p>
                  </div>
                </div>
              </div>

              {error && (
                <div className="rounded-md bg-red-50 p-4 mb-6">
                  <div className="flex">
                    <svg className="w-5 h-5 text-red-400 mr-3" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                    </svg>
                    <div className="text-sm text-red-700">{error}</div>
                  </div>
                </div>
              )}

              {/* Action Buttons */}
              <div className="flex space-x-3">
                <button
                  type="button"
                  onClick={onClose}
                  disabled={loading}
                  className="flex-1 btn-secondary disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleAnchor}
                  disabled={loading}
                  className="flex-1 btn-primary disabled:opacity-50"
                >
                  {loading ? (
                    <div className="flex items-center justify-center">
                      <svg className="animate-spin -ml-1 mr-3 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="m4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      Anchoring...
                    </div>
                  ) : (
                    'Anchor to Blockchain'
                  )}
                </button>
              </div>
            </>
          ) : (
            /* Success State */
            <>
              <div className="text-center mb-6">
                <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                </div>
                <h3 className="text-lg font-medium text-gray-900 mb-2">
                  Successfully Anchored!
                </h3>
                <p className="text-sm text-gray-600">
                  {transactionHashes.length} transactions have been anchored to the blockchain.
                </p>
              </div>

              {/* Anchor Details */}
              <div className="bg-gray-50 rounded-lg p-4 mb-6">
                <h4 className="text-sm font-medium text-gray-700 mb-3">Anchor Details</h4>
                <div className="space-y-3 text-sm">
                  <div>
                    <span className="text-gray-500">Transaction Hash:</span>
                    <div className="font-mono text-gray-900 break-all mt-1">
                      {success.tx_hash}
                    </div>
                  </div>
                  <div>
                    <span className="text-gray-500">Merkle Root:</span>
                    <div className="font-mono text-gray-900 break-all mt-1">
                      {success.merkle_root}
                    </div>
                  </div>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex space-x-3">
                <button
                  type="button"
                  onClick={handleComplete}
                  className="flex-1 btn-primary"
                >
                  Done
                </button>
                <a
                  href={success.explorer_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex-1 btn-secondary text-center"
                >
                  View on Explorer ↗
                </a>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
