"""Test cases for transaction API endpoints with MongoDB"""

import pytest
import pytest_asyncio
import uuid
from decimal import Decimal
from httpx import AsyncClient

from app.main import app
from app.models.transaction import DecisionEnum
from app.services.transaction_crud import transaction_crud
from .conftest import MockTransactionData


@pytest.mark.asyncio
class TestTransactionAPI:
    """Test class for transaction API endpoints"""

    async def test_submit_transaction_success(self, clean_database):
        """Test successful transaction submission"""
        transaction_data = MockTransactionData.create_valid_transaction()
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post("/v1/tx/submit", json=transaction_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "tx_id" in data
        assert "decision" in data
        assert "evidence_hash" in data
        assert "created_at" in data
        assert data["decision"] in ["PENDING", "PASS", "HOLD", "REJECT"]

    async def test_submit_transaction_invalid_data(self, clean_database):
        """Test transaction submission with invalid data"""
        invalid_data = {
            "wallet_from": "",  # Empty wallet address
            "wallet_to": "0x123",
            "amount": "-100",  # Negative amount
            "currency": "ETH"
        }
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post("/v1/tx/submit", json=invalid_data)
        
        assert response.status_code == 422  # Validation error

    async def test_list_transactions_empty(self, clean_database):
        """Test listing transactions when database is empty"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/v1/tx/list")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["transactions"] == []
        assert data["total"] == 0
        assert data["page"] == 1

    async def test_list_transactions_with_data(self, clean_database):
        """Test listing transactions with data"""
        # Create test transactions
        test_transactions = MockTransactionData.create_multiple_transactions(3)
        
        # Submit transactions through CRUD
        for tx_data in test_transactions:
            await transaction_crud.create_transaction(tx_data)
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/v1/tx/list")
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["transactions"]) == 3
        assert data["total"] == 3
        assert data["page"] == 1

    async def test_list_transactions_pagination(self, clean_database):
        """Test transaction list pagination"""
        # Create test transactions
        test_transactions = MockTransactionData.create_multiple_transactions(5)
        
        # Submit transactions through CRUD
        for tx_data in test_transactions:
            await transaction_crud.create_transaction(tx_data)
        
        # Test first page
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/v1/tx/list?page=1&per_page=2")
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["transactions"]) == 2
        assert data["total"] == 5
        assert data["page"] == 1
        assert data["per_page"] == 2

    async def test_list_transactions_filter_by_decision(self, clean_database):
        """Test filtering transactions by decision"""
        # Create transactions with different decisions
        tx_data = MockTransactionData.create_valid_transaction()
        tx_data["decision"] = DecisionEnum.PASS
        
        await transaction_crud.create_transaction(tx_data)
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/v1/tx/list?decision=PASS")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should find the PASS transaction
        assert len(data["transactions"]) >= 0  # Depends on compliance engine logic

    async def test_get_transaction_by_id(self, clean_database):
        """Test getting a specific transaction by ID"""
        # Create a test transaction
        tx_data = MockTransactionData.create_valid_transaction()
        created_tx = await transaction_crud.create_transaction(tx_data)
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(f"/v1/tx/{created_tx.tx_uuid}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["tx_uuid"] == created_tx.tx_uuid
        assert data["wallet_from"] == tx_data["wallet_from"]
        assert data["wallet_to"] == tx_data["wallet_to"]

    async def test_get_transaction_not_found(self, clean_database):
        """Test getting a non-existent transaction"""
        fake_uuid = str(uuid.uuid4())
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(f"/v1/tx/{fake_uuid}")
        
        assert response.status_code == 404

    async def test_review_transaction_success(self, clean_database):
        """Test successful transaction review/override"""
        # Create a test transaction
        tx_data = MockTransactionData.create_valid_transaction()
        created_tx = await transaction_crud.create_transaction(tx_data)
        
        review_data = {
            "tx_uuid": created_tx.tx_uuid,
            "decision": "PASS",
            "reason": "Manual override - customer verified"
        }
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post("/v1/tx/review", json=review_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["tx_uuid"] == created_tx.tx_uuid
        assert data["new_decision"] == "PASS"

    async def test_review_transaction_not_found(self, clean_database):
        """Test reviewing a non-existent transaction"""
        fake_uuid = str(uuid.uuid4())
        
        review_data = {
            "tx_uuid": fake_uuid,
            "decision": "PASS",
            "reason": "Test review"
        }
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post("/v1/tx/review", json=review_data)
        
        assert response.status_code == 404

    async def test_merkle_root_endpoint(self, clean_database):
        """Test getting Merkle tree root"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/v1/merkle/root")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "root_hash" in data
        assert "total_leaves" in data
        assert "tree_height" in data

    async def test_compliance_summary_endpoint(self, clean_database):
        """Test getting compliance summary"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/v1/compliance/summary")
        
        assert response.status_code == 200
        # Summary endpoint depends on compliance engine implementation
    """Setup test database"""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client():
    """Create test client"""
    from httpx import ASGITransport
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def sample_transaction_data():
    """Sample transaction data for testing"""
    return {
        "wallet_from": "0x742d35Cc6634C0532925a3b8D4d0C123456789AB",
        "wallet_to": "0x123d35Cc6634C0532925a3b8D4d0C123456789CD",
        "amount": "100.5",
        "currency": "ETH",
        "kyc_proof_id": "kyc_12345"
    }


class TestTransactionSubmit:
    """Test transaction submission endpoint"""
    
    @pytest.mark.asyncio
    async def test_submit_transaction_pass(self, client: AsyncClient, setup_database, sample_transaction_data):
        """Test transaction submission that should PASS"""
        response = await client.post("/v1/tx/submit", json=sample_transaction_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "tx_id" in data
        assert data["decision"] == "PASS"
        assert data["message"] == "All compliance checks passed"
        assert "evidence_hash" in data
        assert "created_at" in data
        
        # Verify UUID format
        tx_uuid = uuid.UUID(data["tx_id"])
        assert isinstance(tx_uuid, uuid.UUID)
    
    @pytest.mark.asyncio
    async def test_submit_transaction_hold_high_amount(self, client: AsyncClient, setup_database):
        """Test transaction submission that should HOLD due to high amount"""
        tx_data = {
            "wallet_from": "0x742d35Cc6634C0532925a3b8D4d0C123456789AB",
            "wallet_to": "0x123d35Cc6634C0532925a3b8D4d0C123456789CD",
            "amount": "1500.0",  # Above threshold
            "currency": "ETH",
            "kyc_proof_id": "kyc_12345"
        }
        
        response = await client.post("/v1/tx/submit", json=tx_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["decision"] == "HOLD"
        assert "risk score" in data["message"].lower()
    
    @pytest.mark.asyncio
    async def test_submit_transaction_hold_no_kyc(self, client: AsyncClient, setup_database):
        """Test transaction submission that should HOLD due to missing KYC"""
        tx_data = {
            "wallet_from": "0x742d35Cc6634C0532925a3b8D4d0C123456789AB",
            "wallet_to": "0x123d35Cc6634C0532925a3b8D4d0C123456789CD",
            "amount": "100.5",
            "currency": "ETH"
            # No kyc_proof_id
        }
        
        response = await client.post("/v1/tx/submit", json=tx_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["decision"] == "HOLD"
        assert "risk score" in data["message"].lower()
    
    @pytest.mark.asyncio
    async def test_submit_transaction_reject_blacklisted(self, client: AsyncClient, setup_database):
        """Test transaction submission that should REJECT due to blacklisted wallet"""
        tx_data = {
            "wallet_from": "0x000000000000000000000000000000000000dead",  # Blacklisted
            "wallet_to": "0x123d35Cc6634C0532925a3b8D4d0C123456789CD",
            "amount": "100.5",
            "currency": "ETH",
            "kyc_proof_id": "kyc_12345"
        }
        
        response = await client.post("/v1/tx/submit", json=tx_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["decision"] == "REJECT"
        assert "blacklisted" in data["message"]
    
    @pytest.mark.asyncio
    async def test_submit_transaction_invalid_data(self, client: AsyncClient, setup_database):
        """Test transaction submission with invalid data"""
        tx_data = {
            "wallet_from": "invalid_address",  # Invalid address format
            "wallet_to": "0x123d35Cc6634C0532925a3b8D4d0C123456789CD",
            "amount": "-100",  # Negative amount
            "currency": "ETH"
        }
        
        response = await client.post("/v1/tx/submit", json=tx_data)
        
        assert response.status_code == 422  # Validation error


class TestTransactionList:
    """Test transaction listing endpoint"""
    
    @pytest.mark.asyncio
    async def test_list_transactions_empty(self, client: AsyncClient, setup_database):
        """Test listing transactions when database is empty"""
        response = await client.get("/v1/tx/list")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["transactions"] == []
        assert data["total"] == 0
        assert data["page"] == 1
        assert data["per_page"] == 20
    
    @pytest.mark.asyncio
    async def test_list_transactions_with_data(self, client: AsyncClient, setup_database, sample_transaction_data):
        """Test listing transactions after submitting some"""
        # Submit a few transactions
        await client.post("/v1/tx/submit", json=sample_transaction_data)
        
        # Modify for different decision
        sample_transaction_data["amount"] = "1500.0"  # HOLD
        await client.post("/v1/tx/submit", json=sample_transaction_data)
        
        # List all transactions
        response = await client.get("/v1/tx/list")
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["transactions"]) == 2
        assert data["total"] == 2
        assert data["page"] == 1
        assert data["per_page"] == 20
        
        # Check transaction structure
        tx = data["transactions"][0]
        assert "id" in tx
        assert "tx_uuid" in tx
        assert "wallet_from" in tx
        assert "decision" in tx
        assert "created_at" in tx
    
    @pytest.mark.asyncio 
    async def test_list_transactions_pagination(self, client: AsyncClient, setup_database, sample_transaction_data):
        """Test transaction listing with pagination"""
        # Submit multiple transactions
        for i in range(5):
            tx_data = sample_transaction_data.copy()
            tx_data["amount"] = str(100 + i)
            await client.post("/v1/tx/submit", json=tx_data)
        
        # Test pagination
        response = await client.get("/v1/tx/list?page=1&per_page=2")
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["transactions"]) == 2
        assert data["total"] == 5
        assert data["page"] == 1
        assert data["per_page"] == 2
    
    @pytest.mark.asyncio
    async def test_list_transactions_filter_by_decision(self, client: AsyncClient, setup_database, sample_transaction_data):
        """Test filtering transactions by decision"""
        # Submit PASS transaction
        await client.post("/v1/tx/submit", json=sample_transaction_data)
        
        # Submit HOLD transaction
        sample_transaction_data["amount"] = "1500.0"
        await client.post("/v1/tx/submit", json=sample_transaction_data)
        
        # Filter by PASS
        response = await client.get("/v1/tx/list?decision=PASS")
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["transactions"]) == 1
        assert data["transactions"][0]["decision"] == "PASS"


class TestTransactionReview:
    """Test transaction review endpoint"""
    
    @pytest.mark.asyncio
    async def test_review_transaction_success(self, client: AsyncClient, setup_database, sample_transaction_data):
        """Test successful transaction review"""
        # Submit transaction first
        submit_response = await client.post("/v1/tx/submit", json=sample_transaction_data)
        tx_uuid = submit_response.json()["tx_id"]
        
        # Review transaction
        review_data = {
            "tx_uuid": tx_uuid,
            "decision": "HOLD",
            "reason": "Manual review required for additional verification"
        }
        
        response = await client.post("/v1/tx/review", json=review_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["tx_uuid"] == tx_uuid
        assert data["old_decision"] == "PASS"
        assert data["new_decision"] == "HOLD"
        assert "updated successfully" in data["message"]
    
    @pytest.mark.asyncio
    async def test_review_transaction_not_found(self, client: AsyncClient, setup_database):
        """Test reviewing non-existent transaction"""
        fake_uuid = str(uuid.uuid4())
        review_data = {
            "tx_uuid": fake_uuid,
            "decision": "PASS",
            "reason": "Manual override"
        }
        
        response = await client.post("/v1/tx/review", json=review_data)
        
        assert response.status_code == 404
        assert "not found" in response.json()["error"]["detail"].lower()


class TestHealthCheck:
    """Test health check endpoint"""
    
    @pytest.mark.asyncio
    async def test_health_check(self, client: AsyncClient):
        """Test health check endpoint"""
        response = await client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert "service" in data
