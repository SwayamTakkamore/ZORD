interface ApiResponse<T> {
  data?: T;
  error?: string;
  status: number;
}

interface Transaction {
  id: string;
  hash: string;
  from_address: string;
  to_address: string;
  amount: string;
  status: 'pending' | 'confirmed' | 'flagged' | 'blocked';
  risk_score: number;
  timestamp: string;
  block_number?: number;
  gas_used?: string;
  anchor_status?: 'not_anchored' | 'anchored' | 'anchor_pending';
  anchor_tx_hash?: string;
}

interface AnchorRequest {
  merkle_root: string;
  transactions: string[];
}

interface AnchorResponse {
  tx_hash: string;
  merkle_root: string;
  block_number: number;
  explorer_url: string;
}

interface OverrideRequest {
  transaction_hash: string;
  new_status: 'confirmed' | 'blocked';
  reason: string;
}

class ApiClient {
  private baseUrl: string;
  private authToken: string | null = null;

  constructor() {
    this.baseUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
    // In a real app, this would come from secure storage
    this.authToken = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    const url = `${this.baseUrl}${endpoint}`;
    const headers = {
      'Content-Type': 'application/json',
      ...(this.authToken && { Authorization: `Bearer ${this.authToken}` }),
      ...options.headers,
    };

    try {
      const response = await fetch(url, {
        ...options,
        headers,
      });

      const data = await response.json();

      if (!response.ok) {
        return {
          error: data.detail || `HTTP ${response.status}`,
          status: response.status,
        };
      }

      return {
        data,
        status: response.status,
      };
    } catch (error) {
      return {
        error: error instanceof Error ? error.message : 'Network error',
        status: 0,
      };
    }
  }

  // Authentication
  async login(username: string, password: string): Promise<ApiResponse<{ token: string }>> {
    // Mock implementation for MVP
    if (username === 'admin' && password === 'admin') {
      const mockToken = 'mock-jwt-token-' + Date.now();
      if (typeof window !== 'undefined') {
        localStorage.setItem('auth_token', mockToken);
      }
      this.authToken = mockToken;
      return {
        data: { token: mockToken },
        status: 200,
      };
    }
    return {
      error: 'Invalid credentials',
      status: 401,
    };
  }

  logout(): void {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('auth_token');
    }
    this.authToken = null;
  }

  isAuthenticated(): boolean {
    return this.authToken !== null;
  }

  // Transactions
  async getTransactions(): Promise<ApiResponse<Transaction[]>> {
    return this.request<Transaction[]>('/api/v1/transactions');
  }

  async getTransaction(hash: string): Promise<ApiResponse<Transaction>> {
    return this.request<Transaction>(`/api/v1/transactions/${hash}`);
  }

  async overrideTransaction(data: OverrideRequest): Promise<ApiResponse<{ success: boolean }>> {
    return this.request<{ success: boolean }>('/api/v1/transactions/override', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // Anchoring
  async anchorTransactions(data: AnchorRequest): Promise<ApiResponse<AnchorResponse>> {
    return this.request<AnchorResponse>('/api/v1/anchor', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getAnchorStatus(merkleRoot: string): Promise<ApiResponse<{ anchored: boolean; tx_hash?: string }>> {
    return this.request<{ anchored: boolean; tx_hash?: string }>(`/api/v1/anchor/status/${merkleRoot}`);
  }

  async verifyAnchor(merkleRoot: string): Promise<ApiResponse<{ verified: boolean; block_number?: number }>> {
    return this.request<{ verified: boolean; block_number?: number }>(`/api/v1/anchor/verify/${merkleRoot}`);
  }

  // Health check
  async healthCheck(): Promise<ApiResponse<{ status: string }>> {
    return this.request<{ status: string }>('/health');
  }
}

// Export singleton instance
export const apiClient = new ApiClient();

// Export types
export type {
  Transaction,
  AnchorRequest,
  AnchorResponse,
  OverrideRequest,
  ApiResponse,
};
