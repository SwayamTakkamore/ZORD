# Crypto Compliance Copilot Backend

Modern FastAPI backend with **MongoDB + Motor** for automated compliance checking, blockchain anchoring, and real-time transaction monitoring.

## 🚀 **Features**

- **FastAPI Application**: Modern async Python web framework
- **MongoDB Integration**: Motor async driver with Pydantic models
- **Transaction Management**: Submit, list, and review transactions
- **Enhanced Compliance Engine**: Advanced rules for KYC, amount thresholds, and blacklists
- **Manual Override System**: Admin-authorized transaction decision overrides with audit trail
- **Blockchain Anchoring**: Smart contract integration on Polygon
- **Real-time Monitoring**: Live transaction updates with WebSocket support
- **Comprehensive Testing**: Full test suite with MongoDB mocks

## 📊 **Tech Stack**

| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| **API Framework** | FastAPI | 0.104+ | RESTful API server |
| **Database** | MongoDB | 4.4+ | Document database |
| **Async Driver** | Motor | 3.3+ | MongoDB async operations |
| **Validation** | Pydantic | 2.0+ | Data validation and serialization |
| **Blockchain** | Web3.py | 6.15+ | Ethereum/Polygon integration |
| **Testing** | Pytest + Mongomock | 7.4+ | Unit and integration testing |

## 🏗 **Quick Start**

### 1. Installation
```bash
# Clone and navigate
cd backend

# Install dependencies
pip install -r requirements.txt
```

### 2. MongoDB Setup
```bash
# Option A: MongoDB Atlas (Recommended)
# 1. Create free account at https://cloud.mongodb.com
# 2. Create cluster and get connection string
# 3. Update .env with connection string

# Option B: Local MongoDB
# Install MongoDB locally and use:
# MONGO_URI=mongodb://localhost:27017/compliance
```

### 3. Environment Configuration
```bash
# Copy environment template
cp .env.example .env

# Edit .env with your MongoDB connection
MONGO_URI=mongodb+srv://user:pass@cluster0.mongodb.net/compliance?retryWrites=true&w=majority
MONGO_DB=compliance
```

### 4. Run Application
```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000` with automatic API documentation at `http://localhost:8000/docs`.

## 📋 **API Endpoints**

### Transaction Endpoints

#### POST /v1/tx/submit
Submit a new transaction for compliance checking.

**Request:**
```json
{
    "wallet_from": "0x742d35Cc6634C0532925a3b8D4d0C123456789AB",
    "wallet_to": "0x123d35Cc6634C0532925a3b8D4d0C123456789CD",
    "amount": "100.5",
    "currency": "ETH",
    "kyc_proof_id": "kyc_12345"
}
```

**Response:**
```json
{
    "tx_id": "123e4567-e89b-12d3-a456-426614174000",
    "decision": "PASS",
    "message": "Transaction approved",
    "evidence_hash": "abc123...",
    "created_at": "2025-09-10T12:00:00Z"
}
```

#### GET /v1/tx/list
List transactions with pagination and filtering.

**Parameters:**
- `page`: Page number (default: 1)
- `per_page`: Items per page (default: 20, max: 100)
- `decision`: Filter by decision (PENDING/PASS/HOLD/REJECT)

#### GET /v1/tx/{tx_id}
Get specific transaction by ID or UUID.

#### POST /v1/override
**[NEW]** Enhanced manual transaction decision override with admin authorization and audit trail.

**Authentication:**
- **Header:** `X-Admin-API-Key` (required)
- **Value:** Admin API key for authorization

**Request:**
```json
{
    "hash": "0x123abc... or tx_uuid",
    "status": "pass|hold|reject (or synonyms)",
    "reason": "Detailed reason for override"
}
```

**Status Normalization:**
- **Pass variants:** `pass`, `approved`, `approve`, `accept`, `accepted`, `allow`, `allowed`
- **Hold variants:** `hold`, `pending`, `review`, `suspend`, `suspended`, `pause`, `paused`
- **Reject variants:** `reject`, `rejected`, `deny`, `denied`, `block`, `blocked`, `fail`, `failed`

**Response:**
```json
{
    "success": true,
    "message": "Transaction override applied successfully",
    "transaction_id": "123e4567-e89b-12d3-a456-426614174000",
    "old_decision": "HOLD",
    "new_decision": "PASS",
    "evidence_hash": "abc123def456...",
    "audit_entry": {
        "action": "manual_override",
        "timestamp": "2025-01-27T10:30:00Z",
        "admin_key_prefix": "admin_ke...",
        "old_decision": "HOLD",
        "new_decision": "PASS",
        "reason": "Manual verification completed",
        "evidence_hash": "abc123def456..."
    }
}
```

**Features:**
- ✅ **Admin Authorization**: Secure API key validation
- ✅ **Status Normalization**: Accepts multiple status variants
- ✅ **Audit Trail**: Complete transaction history with timestamps
- ✅ **Merkle Evidence**: Cryptographic proof generation
- ✅ **Error Handling**: Comprehensive validation and error responses
- ✅ **Idempotent**: Safe to retry with same decision

**Error Responses:**
```json
// 401 Unauthorized
{
    "error": {
        "status_code": 401,
        "detail": "Invalid admin API key",
        "timestamp": "2025-01-27T10:30:00Z",
        "trace_id": "unique-trace-id"
    }
}

// 404 Not Found
{
    "error": {
        "status_code": 404,
        "detail": "Transaction not found: hash_or_uuid",
        "timestamp": "2025-01-27T10:30:00Z",
        "trace_id": "unique-trace-id"
    }
}

// 422 Validation Error
{
    "error": {
        "status_code": 422,
        "detail": "Invalid status 'invalid_status'. Allowed: [list of valid statuses]",
        "timestamp": "2025-01-27T10:30:00Z",
        "trace_id": "unique-trace-id"
    }
}
```

#### POST /v1/tx/review
**[DEPRECATED]** Basic manual review endpoint. Use `/v1/override` for enhanced functionality.

**Request:**
```json
{
    "tx_uuid": "123e4567-e89b-12d3-a456-426614174000",
    "decision": "PASS",
    "reason": "Manual override - customer verified via phone"
}
```

## 💡 Usage Examples

### Override Endpoint Examples

#### 1. Approve a Held Transaction
```bash
curl -X POST "http://localhost:8000/v1/override" \
  -H "Content-Type: application/json" \
  -H "X-Admin-API-Key: admin_key_12345" \
  -d '{
    "hash": "123e4567-e89b-12d3-a456-426614174000",
    "status": "approve",
    "reason": "Customer provided additional KYC documentation via email"
  }'
```

#### 2. Reject a Suspicious Transaction
```bash
curl -X POST "http://localhost:8000/v1/override" \
  -H "Content-Type: application/json" \
  -H "X-Admin-API-Key: admin_key_12345" \
  -d '{
    "hash": "0x123abc456def789...",
    "status": "block",
    "reason": "Suspected fraudulent activity - multiple failed verification attempts"
  }'
```

#### 3. Put Transaction on Hold for Review
```bash
curl -X POST "http://localhost:8000/v1/override" \
  -H "Content-Type: application/json" \
  -H "X-Admin-API-Key: admin_key_12345" \
  -d '{
    "hash": "tx_hash_xyz789",
    "status": "suspend",
    "reason": "Requires additional compliance review due to high amount"
  }'
```

### Python Client Example
```python
import httpx

async def override_transaction(hash_value, status, reason, admin_key):
    """Override a transaction decision with audit trail"""
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/v1/override",
            json={
                "hash": hash_value,
                "status": status,
                "reason": reason
            },
            headers={"X-Admin-API-Key": admin_key}
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Transaction {result['transaction_id']} overridden:")
            print(f"   {result['old_decision']} → {result['new_decision']}")
            print(f"   Evidence: {result['evidence_hash'][:16]}...")
            return result
        else:
            error = response.json()
            print(f"❌ Error: {error.get('error', {}).get('detail', 'Unknown error')}")
            return None

# Usage examples
await override_transaction(
    hash_value="123e4567-e89b-12d3-a456-426614174000",
    status="approve",
    reason="Manual verification completed",
    admin_key="admin_key_12345"
)
```

### Integration with Existing Workflow
```python
# 1. Submit transaction
submit_response = await client.post("/v1/tx/submit", json=transaction_data)
tx_id = submit_response.json()["tx_id"]

# 2. Check if manual review needed
if submit_response.json()["decision"] == "HOLD":
    # 3. Override after manual review
    override_response = await client.post(
        "/v1/override",
        json={
            "hash": tx_id,
            "status": "pass",  # or "reject" 
            "reason": "Manual compliance review completed"
        },
        headers={"X-Admin-API-Key": admin_key}
    )
```

### Health Check

#### GET /health
Simple health check endpoint for monitoring.

## Compliance Rules

The simple compliance engine implements these rules:

1. **Blacklist Check**: Rejects transactions from/to blacklisted wallets
2. **Amount Threshold**: Holds transactions above $1000
3. **KYC Requirement**: Holds transactions without KYC proof
4. **Default**: Passes transactions that meet all criteria

## Database Schema

### Transaction Model

- `id`: Primary key
- `tx_uuid`: Unique transaction identifier (UUID)
- `wallet_from`: Source wallet address (42 chars)
- `wallet_to`: Destination wallet address (42 chars)
- `amount`: Transaction amount (Decimal)
- `currency`: Currency code (default: ETH)
- `kyc_proof_id`: Optional KYC proof identifier
- `decision`: Compliance decision (PENDING/PASS/HOLD/REJECT)
- `evidence_hash`: SHA256 hash of transaction evidence
- `merkle_leaf`: Merkle tree leaf (future use)
- `anchored_root`: Blockchain anchored root (future use)
- `created_at`: Creation timestamp
- `updated_at`: Last update timestamp

## Setup and Running

### Prerequisites

- Python 3.11+
- PostgreSQL (or SQLite for testing)

### Installation

1. **Install dependencies:**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. **Set up environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your database credentials
   ```

3. **Run the application:**
   ```bash
   python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

### Testing

Run the complete test suite:

```bash
cd backend
python -m pytest app/tests/ -v
```

Run tests with coverage:

```bash
python -m pytest app/tests/ --cov=app --cov-report=html
```

### Docker

Build and run with Docker:

```bash
cd backend
docker build -t compliance-backend .
docker run -p 8000:8000 compliance-backend
```

## Testing the API

### Using curl

1. **Submit a transaction that should PASS:**
   ```bash
   curl -X POST "http://localhost:8000/v1/tx/submit" \
     -H "Content-Type: application/json" \
     -d '{
       "wallet_from": "0x742d35Cc6634C0532925a3b8D4d0C123456789AB",
       "wallet_to": "0x123d35Cc6634C0532925a3b8D4d0C123456789CD",
       "amount": "100.5",
       "currency": "ETH",
       "kyc_proof_id": "kyc_12345"
     }'
   ```

2. **Submit a transaction that should HOLD (high amount):**
   ```bash
   curl -X POST "http://localhost:8000/v1/tx/submit" \
     -H "Content-Type: application/json" \
     -d '{
       "wallet_from": "0x742d35Cc6634C0532925a3b8D4d0C123456789AB",
       "wallet_to": "0x123d35Cc6634C0532925a3b8D4d0C123456789CD",
       "amount": "1500.0",
       "currency": "ETH",
       "kyc_proof_id": "kyc_12345"
     }'
   ```

3. **Submit a transaction that should REJECT (blacklisted):**
   ```bash
   curl -X POST "http://localhost:8000/v1/tx/submit" \
     -H "Content-Type: application/json" \
     -d '{
       "wallet_from": "0x000000000000000000000000000000000000dead",
       "wallet_to": "0x123d35Cc6634C0532925a3b8D4d0C123456789CD",
       "amount": "100.5",
       "currency": "ETH",
       "kyc_proof_id": "kyc_12345"
     }'
   ```

4. **List transactions:**
   ```bash
   curl "http://localhost:8000/v1/tx/list"
   ```

5. **Review a transaction (replace UUID with actual one):**
   ```bash
   curl -X POST "http://localhost:8000/v1/tx/review" \
     -H "Content-Type: application/json" \
     -d '{
       "tx_uuid": "YOUR_TX_UUID_HERE",
       "decision": "PASS",
       "reason": "Manual review completed"
     }'
   ```

### API Documentation

Once running, visit:
- **Interactive API docs**: http://localhost:8000/docs
- **ReDoc documentation**: http://localhost:8000/redoc

## Next Steps

This backend skeleton provides the foundation for:

1. **Module 2**: Compliance engine and Merkle tree implementation
2. **Module 3**: ZK proof integration
3. **Module 4**: Blockchain anchoring service
4. **Module 5**: Next.js dashboard integration
5. **Module 6**: Flutter mobile app integration

## Security Notes

- Never commit real secrets to version control
- Use environment variables for all sensitive configuration
- Input validation is handled by Pydantic schemas
- SQL injection protection via SQLAlchemy ORM
- CORS is configured for development (restrict in production)
