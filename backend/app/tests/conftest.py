"""
Test configuration and fixtures for transaction submission tests
"""
import asyncio
import pytest
import pytest_asyncio
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch
from bson import ObjectId
from bson.decimal128 import Decimal128
from datetime import datetime
from typing import Dict, Any

from app.main import app


@pytest_asyncio.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def client():
    """Create a test client for the FastAPI app"""
    from fastapi.testclient import TestClient
    from app.db.mongo import get_database
    
    # Create mock database
    mock_db = AsyncMock()
    mock_db.transactions = AsyncMock()
    mock_db.transactions.insert_one.return_value = AsyncMock(inserted_id=ObjectId("507f1f77bcf86cd799439011"))
    
    # Override the dependency
    app.dependency_overrides[get_database] = lambda: mock_db
    
    try:
        # For async tests, we need to use the actual AsyncClient
        import httpx
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        # Clean up
        app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def mock_database():
    """Mock MongoDB database for testing"""
    mock_db = AsyncMock()
    
    # Mock collections
    mock_db.transactions = AsyncMock()
    
    # Default successful insert behavior
    mock_db.transactions.insert_one.return_value = AsyncMock(inserted_id=ObjectId("507f1f77bcf86cd799439011"))
    
    # Default find_one behavior
    mock_db.transactions.find_one.return_value = {
        "_id": ObjectId("507f1f77bcf86cd799439011"),
        "tx_hash": "0x123456789abcdef123456789abcdef123456789abcdef123456789abcdef1234",
        "wallet_from": "0x742d35cc6635c0532925a3b8d5c2c17c5865000e",
        "wallet_to": "0x8ba1f109551bd432803012645hac136c2c17c586",
        "amount": Decimal128("100.50"),
        "currency": "USDT",
        "memo": "Test transaction from mobile app",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "decision": "PENDING",
        "trace_id": "test-trace-id"
    }
    
    with patch('app.services.transaction_crud_simple.get_database', return_value=mock_db):
        yield mock_db


@pytest.fixture
def sample_mobile_payload():
    """Sample payload in mobile app format"""
    return {
        "hash": "0x123456789abcdef123456789abcdef123456789abcdef123456789abcdef1234",
        "from_address": "0x742d35Cc6635C0532925a3b8D5c2c17c5865000E", 
        "to_address": "0x8ba1f109551bD432803012645Hac136c2c17c586",
        "amount": "100.50",
        "asset": "USDT",
        "memo": "Test transaction from mobile app"
    }


@pytest.fixture
def sample_invalid_payload():
    """Sample invalid payload for testing validation errors"""
    return {
        "hash": "short",  # Too short
        "from_address": "invalid",  # Invalid address
        "to_address": "0x8ba1f109551bD432803012645Hac136c2c17c586",
        "amount": "invalid_amount",  # Invalid amount
        "asset": "",  # Empty asset
    }


@pytest.fixture
def expected_mongo_doc():
    """Expected MongoDB document structure"""
    return {
        "tx_hash": "0x123456789abcdef123456789abcdef123456789abcdef123456789abcdef1234",
        "wallet_from": "0x742d35cc6635c0532925a3b8d5c2c17c5865000e",
        "wallet_to": "0x8ba1f109551bd432803012645hac136c2c17c586",
        "amount": Decimal128("100.50"),
        "currency": "USDT",
        "memo": "Test transaction from mobile app",
        "decision": "PENDING"
    }
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def mock_mongo_client():
    """Create a mock MongoDB client for testing"""
    # Create mock client
    client = AsyncMongoMockClient()
    
    # Store original client and database
    original_client = mongodb.client
    original_database = mongodb.database
    
    # Set up mock client
    mongodb.client = client
    mongodb.database = client["compliance_test"]
    
    # Create test indexes
    try:
        await mongodb.create_indexes()
    except Exception:
        pass  # Indexes might already exist
    
    yield mongodb.database
    
    # Restore original client
    mongodb.client = original_client
    mongodb.database = original_database


@pytest.fixture(scope="function")
async def clean_database(mock_mongo_client):
    """Provide a clean database for each test"""
    # Clear all collections before test
    try:
        collections = await mock_mongo_client.list_collection_names()
        for collection_name in collections:
            await mock_mongo_client[collection_name].delete_many({})
    except Exception:
        pass  # Database might not exist yet
    
    yield mock_mongo_client
    
    # Clean up after test
    try:
        collections = await mock_mongo_client.list_collection_names()
        for collection_name in collections:
            await mock_mongo_client[collection_name].delete_many({})
    except Exception:
        pass


@pytest.fixture(scope="function")
async def test_client(clean_database):
    """Create FastAPI test client with clean database"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture(scope="function")
def sync_test_client(clean_database):
    """Create synchronous test client for simple tests"""
    with TestClient(app) as client:
        yield client


class MockTransactionData:
    """Helper class to generate test transaction data"""
    
    @staticmethod
    def create_valid_transaction(**overrides) -> Dict[str, Any]:
        """Create valid transaction data for testing"""
        default_data = {
            "wallet_from": "0x742d35Cc6634C0532925a3b8D4d0C123456789AB",
            "wallet_to": "0x123d35Cc6634C0532925a3b8D4d0C123456789CD",
            "amount": Decimal("100.5"),
            "currency": "ETH",
            "kyc_proof_id": "kyc_12345",
            "decision": DecisionEnum.PENDING
        }
        default_data.update(overrides)
        return default_data
    
    @staticmethod
    def create_api_transaction(**overrides) -> Dict[str, Any]:
        """Create transaction data for API requests (string amounts)"""
        default_data = {
            "wallet_from": "0x742d35Cc6634C0532925a3b8D4d0C123456789AB",
            "wallet_to": "0x123d35Cc6634C0532925a3b8D4d0C123456789CD",
            "amount": "100.5",
            "currency": "ETH",
            "kyc_proof_id": "kyc_12345"
        }
        default_data.update(overrides)
        return default_data
    
    @staticmethod
    def create_multiple_transactions(count: int = 3) -> list:
        """Create multiple test transactions"""
        transactions = []
        for i in range(count):
            tx_data = MockTransactionData.create_valid_transaction(
                wallet_from=f"0x{i:040x}",
                wallet_to=f"0x{i+1000:040x}",
                amount=Decimal(str(100.0 + i * 10)),
                kyc_proof_id=f"kyc_{i}"
            )
            transactions.append(tx_data)
        return transactions
    
    @staticmethod
    def create_blacklisted_transaction() -> Dict[str, Any]:
        """Create transaction with blacklisted wallet"""
        return MockTransactionData.create_valid_transaction(
            wallet_from="0x000000000000000000000000000000000000dead",  # Blacklisted
            amount=Decimal("50.0")
        )
    
    @staticmethod
    def create_high_amount_transaction() -> Dict[str, Any]:
        """Create transaction with high amount (above threshold)"""
        return MockTransactionData.create_valid_transaction(
            amount=Decimal("5000.0"),  # Above typical threshold
            currency="USDC"
        )
    
    @staticmethod
    def create_no_kyc_transaction() -> Dict[str, Any]:
        """Create transaction without KYC proof"""
        return MockTransactionData.create_valid_transaction(
            kyc_proof_id=None,
            amount=Decimal("25.0")
        )


class ComplianceTestData:
    """Test data for compliance engine testing"""
    
    BLACKLISTED_WALLETS = [
        "0x000000000000000000000000000000000000dead",
        "0x1111111111111111111111111111111111111111",
        "0x2222222222222222222222222222222222222222"
    ]
    
    CLEAN_WALLETS = [
        "0x742d35Cc6634C0532925a3b8D4d0C123456789AB",
        "0x123d35Cc6634C0532925a3b8D4d0C123456789CD",
        "0x987fEdCbA9876543210123456789abcDEF012345"
    ]
    
    @staticmethod
    def get_compliance_scenarios():
        """Get various compliance test scenarios"""
        return [
            {
                "name": "clean_small_transaction",
                "wallet_from": ComplianceTestData.CLEAN_WALLETS[0],
                "wallet_to": ComplianceTestData.CLEAN_WALLETS[1], 
                "amount": Decimal("50.0"),
                "kyc_proof_id": "kyc_clean",
                "expected_decision": DecisionEnum.PASS
            },
            {
                "name": "blacklisted_sender",
                "wallet_from": ComplianceTestData.BLACKLISTED_WALLETS[0],
                "wallet_to": ComplianceTestData.CLEAN_WALLETS[1],
                "amount": Decimal("50.0"),
                "kyc_proof_id": "kyc_clean",
                "expected_decision": DecisionEnum.REJECT
            },
            {
                "name": "blacklisted_receiver",
                "wallet_from": ComplianceTestData.CLEAN_WALLETS[0],
                "wallet_to": ComplianceTestData.BLACKLISTED_WALLETS[1],
                "amount": Decimal("50.0"),
                "kyc_proof_id": "kyc_clean",
                "expected_decision": DecisionEnum.REJECT
            },
            {
                "name": "high_amount_with_kyc",
                "wallet_from": ComplianceTestData.CLEAN_WALLETS[0],
                "wallet_to": ComplianceTestData.CLEAN_WALLETS[1],
                "amount": Decimal("5000.0"),
                "kyc_proof_id": "kyc_verified",
                "expected_decision": DecisionEnum.HOLD  # High amount triggers manual review
            },
            {
                "name": "no_kyc_small_amount",
                "wallet_from": ComplianceTestData.CLEAN_WALLETS[0],
                "wallet_to": ComplianceTestData.CLEAN_WALLETS[1],
                "amount": Decimal("25.0"),
                "kyc_proof_id": None,
                "expected_decision": DecisionEnum.HOLD  # No KYC triggers manual review
            }
        ]


@pytest.fixture
def mock_transaction_data():
    """Provide MockTransactionData class"""
    return MockTransactionData


@pytest.fixture
def compliance_test_data():
    """Provide ComplianceTestData class"""
    return ComplianceTestData


# Sample data fixtures
@pytest.fixture
async def sample_transaction(clean_database):
    """Create a sample transaction in the database"""
    tx_data = MockTransactionData.create_valid_transaction()
    created_tx = await transaction_crud.create_transaction(tx_data)
    return created_tx


@pytest.fixture
async def multiple_transactions(clean_database):
    """Create multiple sample transactions in the database"""
    transactions = []
    test_data = MockTransactionData.create_multiple_transactions(5)
    
    for tx_data in test_data:
        created_tx = await transaction_crud.create_transaction(tx_data)
        transactions.append(created_tx)
    
    return transactions


# Environment fixtures
@pytest.fixture
def mock_environment(monkeypatch):
    """Mock environment variables for testing"""
    test_env = {
        "MONGO_URI": "mongodb://localhost:27017/test",
        "MONGO_DB": "compliance_test", 
        "SECRET_KEY": "test_secret_key",
        "DEBUG": "true",
        "AMOUNT_THRESHOLD": "1000.0",
        "BLACKLISTED_WALLETS": ",".join(ComplianceTestData.BLACKLISTED_WALLETS)
    }
    
    for key, value in test_env.items():
        monkeypatch.setenv(key, value)
    
    return test_env


# Utility fixtures
@pytest.fixture
def assert_transaction_equal():
    """Utility function to assert transaction equality"""
    def _assert_equal(tx1, tx2, ignore_fields=None):
        ignore_fields = ignore_fields or ['id', 'created_at', 'updated_at']
        
        for field in ['wallet_from', 'wallet_to', 'amount', 'currency', 'decision']:
            if field not in ignore_fields:
                assert getattr(tx1, field) == getattr(tx2, field), f"Field {field} mismatch"
    
    return _assert_equal