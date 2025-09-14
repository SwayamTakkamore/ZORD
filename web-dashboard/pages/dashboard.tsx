import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import useSWR from 'swr';
import { apiClient, Transaction } from '@/lib/api';
import TransactionTable from '@/components/TransactionTable';
import OverrideModal from '@/components/OverrideModal';
import AnchorModal from '@/components/AnchorModal';

export default function DashboardPage() {
  const router = useRouter();
  const [selectedTx, setSelectedTx] = useState<Transaction | null>(null);
  const [showOverrideModal, setShowOverrideModal] = useState(false);
  const [showAnchorModal, setShowAnchorModal] = useState(false);
  const [selectedTxs, setSelectedTxs] = useState<string[]>([]);

  // Check authentication
  useEffect(() => {
    if (!apiClient.isAuthenticated()) {
      router.push('/');
    }
  }, [router]);

  // Fetch transactions with SWR
  const { data: transactions, error, mutate } = useSWR<Transaction[]>(
    'transactions',
    async () => {
      const response = await apiClient.getTransactions();
      if (response.error) {
        throw new Error(response.error);
      }
      return response.data || [];
    },
    {
      refreshInterval: 5000, // Refresh every 5 seconds
      revalidateOnFocus: true,
    }
  );

  const handleLogout = () => {
    apiClient.logout();
    router.push('/');
  };

  const handleOverride = (transaction: Transaction) => {
    setSelectedTx(transaction);
    setShowOverrideModal(true);
  };

  const handleOverrideComplete = () => {
    setShowOverrideModal(false);
    setSelectedTx(null);
    mutate(); // Refresh data
  };

  const handleBulkAnchor = () => {
    if (selectedTxs.length > 0) {
      setShowAnchorModal(true);
    }
  };

  const handleAnchorComplete = () => {
    setShowAnchorModal(false);
    setSelectedTxs([]);
    mutate(); // Refresh data
  };

  const stats = {
    total: transactions?.length || 0,
    pending: transactions?.filter(tx => tx.status === 'pending').length || 0,
    flagged: transactions?.filter(tx => tx.status === 'flagged').length || 0,
    confirmed: transactions?.filter(tx => tx.status === 'confirmed').length || 0,
    anchored: transactions?.filter(tx => tx.anchor_status === 'anchored').length || 0,
  };

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="card max-w-md w-full">
          <div className="text-center">
            <div className="text-red-600 text-lg font-medium mb-2">Error Loading Dashboard</div>
            <p className="text-gray-600 mb-4">{error.message}</p>
            <button onClick={() => mutate()} className="btn-primary">
              Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center">
              <h1 className="text-xl font-semibold text-gray-900">
                Compliance Dashboard
              </h1>
            </div>
            <div className="flex items-center space-x-4">
              <div className="text-sm text-gray-500">
                Welcome, Compliance Officer
              </div>
              <button
                onClick={handleLogout}
                className="btn-secondary text-sm"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-5 gap-6 mb-8">
          <div className="card">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                  <span className="text-blue-600 font-medium text-sm">{stats.total}</span>
                </div>
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Total</p>
                <p className="text-lg font-semibold text-gray-900">Transactions</p>
              </div>
            </div>
          </div>

          <div className="card">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="w-8 h-8 bg-yellow-100 rounded-full flex items-center justify-center">
                  <span className="text-yellow-600 font-medium text-sm">{stats.pending}</span>
                </div>
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Pending</p>
                <p className="text-lg font-semibold text-gray-900">Review</p>
              </div>
            </div>
          </div>

          <div className="card">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="w-8 h-8 bg-red-100 rounded-full flex items-center justify-center">
                  <span className="text-red-600 font-medium text-sm">{stats.flagged}</span>
                </div>
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Flagged</p>
                <p className="text-lg font-semibold text-gray-900">High Risk</p>
              </div>
            </div>
          </div>

          <div className="card">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="w-8 h-8 bg-green-100 rounded-full flex items-center justify-center">
                  <span className="text-green-600 font-medium text-sm">{stats.confirmed}</span>
                </div>
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Confirmed</p>
                <p className="text-lg font-semibold text-gray-900">Safe</p>
              </div>
            </div>
          </div>

          <div className="card">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="w-8 h-8 bg-purple-100 rounded-full flex items-center justify-center">
                  <span className="text-purple-600 font-medium text-sm">{stats.anchored}</span>
                </div>
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Anchored</p>
                <p className="text-lg font-semibold text-gray-900">On-chain</p>
              </div>
            </div>
          </div>
        </div>

        {/* Actions Bar */}
        <div className="flex justify-between items-center mb-6">
          <div className="flex items-center space-x-4">
            <h2 className="text-lg font-medium text-gray-900">Transaction Monitor</h2>
            <div className="flex items-center space-x-2">
              <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
              <span className="text-sm text-gray-500">Live Updates</span>
            </div>
          </div>
          <div className="flex space-x-3">
            <button
              onClick={handleBulkAnchor}
              disabled={selectedTxs.length === 0}
              className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Anchor Selected ({selectedTxs.length})
            </button>
          </div>
        </div>

        {/* Transaction Table */}
        {transactions ? (
          <TransactionTable
            transactions={transactions}
            onOverride={handleOverride}
            selectedTxs={selectedTxs}
            onSelectionChange={setSelectedTxs}
          />
        ) : (
          <div className="card">
            <div className="animate-pulse">
              <div className="h-8 bg-gray-200 rounded mb-4"></div>
              <div className="space-y-3">
                {[...Array(5)].map((_, i) => (
                  <div key={i} className="h-12 bg-gray-100 rounded"></div>
                ))}
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Modals */}
      {showOverrideModal && selectedTx && (
        <OverrideModal
          transaction={selectedTx}
          onClose={() => setShowOverrideModal(false)}
          onComplete={handleOverrideComplete}
        />
      )}

      {showAnchorModal && (
        <AnchorModal
          transactionHashes={selectedTxs}
          onClose={() => setShowAnchorModal(false)}
          onComplete={handleAnchorComplete}
        />
      )}
    </div>
  );
}
