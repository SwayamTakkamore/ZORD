# Module 4: On-chain Anchoring (Polygon zkEVM)

## Overview

Module 4 implements blockchain anchoring functionality that allows the Crypto Compliance Copilot backend to anchor Merkle roots to a Solidity smart contract deployed on Polygon zkEVM testnet or local Hardhat node. This provides immutable proof that compliance evidence existed at a specific point in time.

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   FastAPI       │    │   Polygon        │    │   Smart         │
│   Backend       │───▶│   Anchor         │───▶│   Contract      │
│                 │    │   Service        │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   REST API      │    │   Web3           │    │   Polygon       │
│   Endpoints     │    │   Integration    │    │   zkEVM         │
│                 │    │                  │    │   Network       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Components

### 1. Smart Contract (`contracts/ComplianceAnchor.sol`)

A minimal, gas-efficient Solidity contract that:
- Accepts Merkle root submissions via `anchorRoot(bytes32 root)`
- Emits `RootAnchored` events with root, timestamp, and anchorer address
- Provides owner-only functions for restricted access
- Includes version information for debugging

**Key Features:**
- ✅ Gas optimized (< 50k gas per anchor)
- ✅ Event-based architecture (no storage overhead)
- ✅ Owner access control (optional)
- ✅ Zero root validation

### 2. Polygon Anchor Service (`backend/app/services/polygon_anchor.py`)

Python service that handles all blockchain interactions:
- Web3.py integration for Ethereum/Polygon networks
- Transaction signing with private key management
- Event parsing and retrieval
- Retry logic and error handling
- Health monitoring and diagnostics

**Key Features:**
- ✅ Async-ready architecture
- ✅ Comprehensive error handling
- ✅ Configurable retry logic
- ✅ CLI interface for testing
- ✅ Environment variable configuration

### 3. FastAPI Endpoints (`backend/app/api/v1/anchor.py`)

REST API endpoints for anchoring operations:
- `POST /v1/anchor/root` - Anchor a Merkle root
- `GET /v1/anchor/events` - Retrieve anchor events
- `GET /v1/anchor/health` - Service health check
- `GET /v1/anchor/contract/info` - Contract information
- `GET /v1/anchor/explorer/{tx_hash}` - Explorer links

**Key Features:**
- ✅ Pydantic request/response models
- ✅ Input validation and sanitization
- ✅ Comprehensive error handling
- ✅ Explorer integration
- ✅ OpenAPI documentation

## Installation & Setup

### 1. Install Dependencies

```bash
# Backend dependencies
cd backend
pip install web3 eth-account --break-system-packages

# Smart contract dependencies
cd ../contracts
npm install
```

### 2. Environment Configuration

Copy `.env.example` to `.env` and configure:

```bash
# Blockchain Configuration
POLYGON_RPC_URL=http://127.0.0.1:8545          # Local Hardhat node
# POLYGON_RPC_URL=https://rpc.public.zkevm-test.net  # Polygon zkEVM Testnet

# Private key for signing transactions (TEST KEY ONLY!)
ANCHORER_PRIVATE_KEY=0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef

# Contract address (set after deployment)
CONTRACT_ADDRESS=0x1234567890123456789012345678901234567890
```

**⚠️ SECURITY WARNING:** Never commit real private keys! Use test keys only.

### 3. Smart Contract Deployment

#### Option A: Local Hardhat Node (Recommended for Development)

```bash
# Terminal 1: Start Hardhat node
cd contracts
npx hardhat node

# Terminal 2: Deploy contract
npx hardhat run scripts/deploy.js --network localhost

# Expected output:
# ✅ ComplianceAnchor deployed successfully!
# 📍 Contract Address: 0x5FbDB2315678afecb367f032d93F642f64180aa3
# 👤 Owner Address: 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266
```

#### Option B: Polygon zkEVM Testnet

```bash
# Ensure you have testnet MATIC for gas fees
npx hardhat run scripts/deploy.js --network polygonZkEvmTestnet
```

### 4. Update Environment

After deployment, update your `.env` file:

```bash
CONTRACT_ADDRESS=0x5FbDB2315678afecb367f032d93F642f64180aa3  # Use actual deployed address
```

## Usage Examples

### 1. Health Check

```bash
# Check service health
curl http://localhost:8000/v1/anchor/health | json_pp

# Expected response:
{
   "healthy" : true,
   "contract_address" : "0x5FbDB2315678afecb367f032d93F642f64180aa3",
   "contract_version" : "1.0.0",
   "anchorer_address" : "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266",
   "anchorer_balance_eth" : "10000.0",
   "chain_id" : 31337,
   "latest_block" : 1
}
```

### 2. Anchor a Merkle Root

```bash
# Anchor via API
curl -X POST http://localhost:8000/v1/anchor/root \
  -H "Content-Type: application/json" \
  -d '{
    "root": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
  }' | json_pp

# Expected response:
{
   "success" : true,
   "tx_hash" : "0xa1b2c3d4e5f6...",
   "block_number" : 2,
   "gas_used" : 43234,
   "root" : "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
   "anchored_by" : "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266",
   "timestamp" : "2025-09-10T19:30:00",
   "events" : [...]
}
```

### 3. Retrieve Anchor Events

```bash
# Get recent anchor events
curl "http://localhost:8000/v1/anchor/events?limit=10" | json_pp

# Expected response:
{
   "success" : true,
   "count" : 1,
   "events" : [
      {
         "root" : "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
         "timestamp" : 1694360400,
         "anchored_by" : "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266",
         "tx_hash" : "0xa1b2c3d4e5f6...",
         "block_number" : 2,
         "log_index" : 0
      }
   ]
}
```

### 4. CLI Usage

```bash
# Health check via CLI
cd backend
python -m app.services.polygon_anchor health

# Anchor root via CLI
python -m app.services.polygon_anchor anchor_root --root 0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef

# Get events via CLI
python -m app.services.polygon_anchor get_events --limit 10
```

### 5. Smart Contract Direct Interaction

```bash
# Test anchoring via script
cd contracts
node scripts/anchor.js --root 0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef

# Expected output:
# ⚓ Anchoring Merkle root to blockchain...
# 📤 Transaction sent: 0xa1b2c3d4e5f6...
# ✅ Root anchored successfully!
# 🔗 Transaction Hash: 0xa1b2c3d4e5f6...
```

## Testing

### 1. Run Smart Contract Tests

```bash
cd contracts
npx hardhat test

# Expected output:
#   ComplianceAnchor
#     Deployment
#       ✓ Should set the right owner
#       ✓ Should return correct version
#     Root Anchoring
#       ✓ Should anchor a root and emit RootAnchored event
#       ✓ Should allow any address to anchor a root
#       ✓ Should reject zero root hash
```

### 2. Run Backend Tests

```bash
cd backend
python -m pytest app/tests/test_anchor.py -v

# Expected output:
# test_service_initialization PASSED
# test_hex_format_validation PASSED
# test_health_check_success PASSED
# test_anchor_root_endpoint_success PASSED
```

### 3. Integration Testing

```bash
# Run integration test (requires Hardhat node)
cd backend
python -m pytest app/tests/test_anchor.py::TestHardhatIntegration -v
```

## Integration with Existing Modules

### With Compliance Engine (Module 2)

```python
from app.services.polygon_anchor import anchor_merkle_root
from app.core.merkle import create_evidence_tree

# After compliance checking
evidence_tree = create_evidence_tree(compliance_results)
merkle_root = evidence_tree.root

# Anchor to blockchain
anchor_result = await anchor_merkle_root(merkle_root.hex())
print(f"Anchored to blockchain: {anchor_result['tx_hash']}")
```

### With ZK Proofs (Module 3)

```python
# Generate ZK proof with anchored evidence
zk_proof_request = {
    "transaction_data": transaction_data,
    "compliance_evidence": compliance_evidence,
    "merkle_proof": {
        "root_hash": anchored_root,
        "path_indices": merkle_proof["path_indices"],
        "path_elements": merkle_proof["path_elements"]
    }
}

# The anchored root provides additional integrity guarantees
zk_proof = await generate_zk_compliance_proof(**zk_proof_request)
```

## Production Considerations

### 1. Gas Optimization

- **Current gas usage:** ~43k gas per anchor
- **Optimization strategies:**
  - Batch multiple roots in single transaction
  - Use CREATE2 for deterministic addresses
  - Consider layer 2 solutions for reduced costs

### 2. Security

- **Private key management:** Use hardware wallets or key management services
- **Access control:** Enable owner-only anchoring for production
- **Monitoring:** Set up alerts for failed transactions

### 3. Reliability

- **RPC endpoint redundancy:** Configure multiple RPC providers
- **Transaction monitoring:** Implement transaction status tracking
- **Retry strategies:** Exponential backoff with jitter

### 4. Scalability

- **Event indexing:** Use The Graph Protocol for efficient event queries
- **Archival:** Store historical events in database for fast access
- **Caching:** Cache recent events to reduce RPC calls

## Explorer Links

### Polygon zkEVM Testnet
- **Explorer:** https://testnet-zkevm.polygonscan.com/
- **Contract verification:** Automatic via Hardhat verify plugin
- **Transaction tracking:** Direct links from API responses

### Local Development
- **Hardhat console:** Interactive contract testing
- **Local explorer:** Hardhat network dashboard
- **Debug traces:** Transaction execution details

## Error Handling

### Common Issues

1. **"Web3 connection failed"**
   - Check `POLYGON_RPC_URL` configuration
   - Verify network connectivity
   - Ensure Hardhat node is running (for local development)

2. **"Root cannot be zero"**
   - Ensure Merkle root is not 0x0000...
   - Validate root hash format (64 hex characters)

3. **"Insufficient funds"**
   - Check ETH/MATIC balance on anchorer account
   - Fund account with testnet tokens

4. **"Contract not found"**
   - Verify `CONTRACT_ADDRESS` is correct
   - Ensure contract is deployed on target network

### Monitoring

```bash
# Monitor service health
watch -n 30 'curl -s http://localhost:8000/v1/anchor/health | json_pp'

# Monitor latest events
watch -n 60 'curl -s "http://localhost:8000/v1/anchor/events?limit=5" | json_pp'
```

## API Documentation

Full API documentation is available at:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **OpenAPI JSON:** http://localhost:8000/openapi.json

## Next Steps

After Module 4 is deployed:

1. **Module 5:** Web dashboard will display anchor events and provide explorer links
2. **Module 6:** Mobile app will show anchoring status for transactions
3. **Integration:** Complete end-to-end workflow from transaction to blockchain anchor
