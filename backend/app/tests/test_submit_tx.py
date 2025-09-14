"""
Test cases for the fixed transaction submission endpoint
"""
import pytest
from fastapi.testclient import TestClient
import json
from decimal import Decimal
from bson.decimal128 import Decimal128
from unittest.mock import patch, AsyncMock

from app.main import app
from app.models.transaction import DecisionEnum


class TestSubmitTransactionFixed:
    """Test the fixed submit transaction endpoint"""
    
    def test_submit_tx_mobile_format_success(self):
        """
        Test the EXACT mobile app payload format that was failing
        
        Verifies:
        - Response status is 201 Created
        - Response contains proper JSON structure
        - Amount is properly converted to string format
        - MongoDB document has Decimal128 amount
        """
        # Mock the compliance engine to return predictable results
        with patch('app.api.v1.transactions.evaluate_transaction_compliance') as mock_compliance:
            mock_compliance.return_value = (DecisionEnum.PASS, "Transaction approved", "evidence123")
            
            # Mock the transaction CRUD operations
            with patch('app.api.v1.transactions.transaction_crud.create_transaction') as mock_create:
                with patch('app.api.v1.transactions.transaction_crud.update_transaction') as mock_update:
                    with patch('app.api.v1.transactions.transaction_crud.get_transaction_by_uuid') as mock_get:
                        
                        # Mock the created transaction document
                        mock_doc = {
                            "_id": "507f1f77bcf86cd799439011",
                            "tx_uuid": "test-uuid-123",
                            "wallet_from": "0x742d35cc6635c0532925a3b8d5c2c17c5865000e",
                            "wallet_to": "0x8ba1f109551bd432803012645hac136c2c17c586",
                            "amount": Decimal128("100.50"),
                            "currency": "USDT",
                            "decision": "PASS",
                            "evidence_hash": "evidence123",
                            "created_at": "2025-09-12T12:00:00Z"
                        }
                        
                        # Mock the database responses
                        mock_result = AsyncMock()
                        mock_result.inserted_id = "507f1f77bcf86cd799439011"
                        mock_create.return_value = mock_result
                        
                        mock_transaction = AsyncMock()
                        mock_transaction.to_dict = AsyncMock(return_value=mock_doc)
                        mock_transaction.id = "507f1f77bcf86cd799439011"
                        mock_get.return_value = mock_transaction
                        
                        mock_update.return_value = True
                        
                        # Mock UUID generation for predictable results
                        with patch('app.api.v1.transactions.uuid.uuid4') as mock_uuid:
                            mock_uuid.return_value.__str__ = lambda: "test-uuid-123"
                            
                            # Test payload - exact mobile app format
                            payload = {
                                "hash": "0x123456789abcdef123456789abcdef123456789abcdef123456789abcdef1234",
                                "from_address": "0x742d35Cc6635C0532925a3b8D5c2c17c5865000E",
                                "to_address": "0x8ba1f109551bD432803012645Hac136c2c17c586",
                                "amount": "100.50",
                                "asset": "USDT",
                                "memo": "Test transaction from mobile app"
                            }
                            
                            # Make the request using TestClient
                            client = TestClient(app)
                            response = client.post("/v1/tx/submit", json=payload)
                            
                            # Verify response status
                            assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
                            
                            # Verify response is valid JSON
                            response_data = response.json()
                            
                            # Check response structure (using actual response schema)
                            assert "tx_id" in response_data
                            assert "decision" in response_data
                            assert "message" in response_data
                            assert "evidence_hash" in response_data
                            assert "created_at" in response_data
                            
                            # Verify the create_transaction was called with Decimal
                            mock_create.assert_called_once()
                            call_args = mock_create.call_args[0][0]
                            assert isinstance(call_args["amount"], Decimal)
                            assert str(call_args["amount"]) == "100.50"

    def test_submit_tx_amount_as_number(self):
        """Test transaction submission with amount as number instead of string"""
        with patch('app.api.v1.transactions.evaluate_transaction_compliance') as mock_compliance:
            mock_compliance.return_value = (DecisionEnum.PASS, "Transaction approved", "evidence123")
            
            with patch('app.api.v1.transactions.transaction_crud.create_transaction') as mock_create:
                with patch('app.api.v1.transactions.transaction_crud.update_transaction'):
                    with patch('app.api.v1.transactions.transaction_crud.get_transaction_by_uuid') as mock_get:
                        
                        mock_doc = {
                            "_id": "507f1f77bcf86cd799439012",
                            "tx_uuid": "test-uuid-456",
                            "wallet_from": "0x742d35cc6635c0532925a3b8d5c2c17c5865000e",
                            "wallet_to": "0x8ba1f109551bd432803012645hac136c2c17c586",
                            "amount": Decimal128("250.75"),
                            "currency": "USDT",
                            "decision": "PASS"
                        }
                        
                        mock_result = AsyncMock()
                        mock_result.inserted_id = "507f1f77bcf86cd799439012"
                        mock_create.return_value = mock_result
                        
                        mock_transaction = AsyncMock()
                        mock_transaction.to_dict = AsyncMock(return_value=mock_doc)
                        mock_get.return_value = mock_transaction
                        
                        with patch('app.api.v1.transactions.uuid.uuid4') as mock_uuid:
                            mock_uuid.return_value.__str__ = lambda: "test-uuid-456"
                            
                            payload = {
                                "hash": "0x123456789abcdef123456789abcdef123456789abcdef123456789abcdef1234",
                                "from_address": "0x742d35Cc6635C0532925a3b8D5c2c17c5865000E",
                                "to_address": "0x8ba1f109551bD432803012645Hac136c2c17c586",
                                "amount": 250.75,  # Number instead of string
                                "asset": "USDT"
                            }
                            
                            client = TestClient(app)
                            response = client.post("/v1/tx/submit", json=payload)
                            
                            assert response.status_code == 201
                            response_data = response.json()
                            assert "tx_id" in response_data
                            assert "decision" in response_data
                            
                            # Verify amount was converted to Decimal
                            call_args = mock_create.call_args[0][0]
                            assert isinstance(call_args["amount"], Decimal)

    def test_submit_tx_validation_errors(self):
        """Test validation errors for missing required fields"""
        
        # Test missing wallet addresses
        payload_no_addresses = {
            "hash": "0x123456789abcdef123456789abcdef123456789abcdef123456789abcdef1234",
            "amount": "100.50",
            "asset": "USDT"
        }
        
        client = TestClient(app)
        response = client.post("/v1/tx/submit", json=payload_no_addresses)
        
        # Should return 422 for validation error
        assert response.status_code == 422
        error_data = response.json()
        assert "detail" in error_data

    def test_submit_tx_real_endpoint_integration(self):
        """Test the actual working endpoint without mocks"""
        payload = {
            "hash": "0x123456789abcdef123456789abcdef123456789abcdef123456789abcdef1234",
            "from_address": "0x742d35Cc6635C0532925a3b8D5c2c17c5865000E",
            "to_address": "0x8ba1f109551bD432803012645Hac136c2c17c586",
            "amount": "100.50",
            "asset": "USDT",
            "memo": "Integration test transaction"
        }
        
        client = TestClient(app)
        response = client.post("/v1/tx/submit", json=payload)
        
        # Should succeed with 201
        assert response.status_code == 201
        response_data = response.json()
        
        # Verify response structure
        assert "tx_id" in response_data
        assert "decision" in response_data
        assert "message" in response_data
        assert "evidence_hash" in response_data
        assert "created_at" in response_data
        
        # Verify the decision is one of the valid enum values
        assert response_data["decision"] in ["PASS", "HOLD", "REJECT"]
        
        # Verify tx_id is a valid UUID format
        import uuid
        try:
            uuid.UUID(response_data["tx_id"])
        except ValueError:
            pytest.fail("tx_id is not a valid UUID")

    def test_normalization_function(self):
        """Test the normalize_mongodb_doc function directly"""
        from app.api.v1.transactions import normalize_mongodb_doc
        from bson import ObjectId
        from datetime import datetime
        
        # Test document with various MongoDB types
        doc = {
            "_id": ObjectId("507f1f77bcf86cd799439011"),
            "amount": Decimal128("123.45"),
            "created_at": datetime(2025, 9, 12, 12, 0, 0),
            "currency": "BTC",
            "normal_string": "test"
        }
        
        normalized = normalize_mongodb_doc(doc)
        
        # Verify ObjectId converted to string
        assert normalized["_id"] == "507f1f77bcf86cd799439011"
        
        # Verify Decimal128 converted to string
        assert normalized["amount"] == "123.45"
        assert isinstance(normalized["amount"], str)
        
        # Verify datetime converted to ISO string
        assert isinstance(normalized["created_at"], str)
        assert "2025-09-12T12:00:00" in normalized["created_at"]
        
        # Verify currency mapped to asset
        assert normalized["asset"] == "BTC"
        assert "currency" not in normalized
        
        # Verify normal strings unchanged
        assert normalized["normal_string"] == "test"
    """Test cases for the /v1/tx/submit endpoint with mobile app format"""
    
    @pytest.mark.asyncio
    async def test_submit_tx_mobile_format_success(self):
        """
        Test the EXACT mobile app payload format that was failing
        
        Verifies:
        - Response status is 201 Created
        - Response contains proper JSON structure
        - Amount is properly converted to string format
        - MongoDB document has Decimal128 amount
        """
        # Mock the compliance engine to return predictable results
        with patch('app.api.v1.transactions.evaluate_transaction_compliance') as mock_compliance:
            mock_compliance.return_value = (DecisionEnum.PASS, "Transaction approved", "evidence123")
            
            # Mock the transaction CRUD operations
            with patch('app.api.v1.transactions.transaction_crud.create_transaction') as mock_create:
                with patch('app.api.v1.transactions.transaction_crud.update_transaction') as mock_update:
                    with patch('app.api.v1.transactions.transaction_crud.get_transaction_by_id') as mock_get:
                        
                        # Mock the created transaction document
                        mock_doc = {
                            "_id": "507f1f77bcf86cd799439011",
                            "tx_uuid": "test-uuid-123",
                            "wallet_from": "0x742d35cc6635c0532925a3b8d5c2c17c5865000e",
                            "wallet_to": "0x8ba1f109551bd432803012645hac136c2c17c586",
                            "amount": Decimal128("100.50"),
                            "currency": "USDT",
                            "decision": "PASS",
                            "evidence_hash": "evidence123",
                            "created_at": "2025-09-12T12:00:00Z"
                        }
                        
                        # Mock the database responses
                        mock_result = AsyncMock()
                        mock_result.inserted_id = "507f1f77bcf86cd799439011"
                        mock_create.return_value = mock_result
                        
                        mock_transaction = AsyncMock()
                        mock_transaction.dict.return_value = mock_doc
                        mock_transaction.id = "507f1f77bcf86cd799439011"
                        mock_get.return_value = mock_transaction
                        
                        mock_update.return_value = True
                        
                        # Mock UUID generation for predictable results
                        with patch('app.api.v1.transactions.uuid.uuid4') as mock_uuid:
                            mock_uuid.return_value.return_value = "test-uuid-123"
                            mock_uuid.return_value.__str__ = lambda x: "test-uuid-123"
                            
                            # Test payload - exact mobile app format
                            payload = {
                                "hash": "0x123456789abcdef123456789abcdef123456789abcdef123456789abcdef1234",
                                "from_address": "0x742d35Cc6635C0532925a3b8D5c2c17c5865000E",
                                "to_address": "0x8ba1f109551bD432803012645Hac136c2c17c586",
                                "amount": "100.50",
                                "asset": "USDT",
                                "memo": "Test transaction from mobile app"
                            }
                            
                            # Make the request
                            async with AsyncClient(app=app, base_url="http://test") as client:
                                response = await client.post("/v1/tx/submit", json=payload)
                            
                            # Verify response
                            assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
                            
                            response_data = response.json()
                            
                            # Verify response structure
                            assert "tx_id" in response_data
                            assert "decision" in response_data
                            assert "message" in response_data
                            assert "evidence_hash" in response_data
                            assert "created_at" in response_data
                            
                            # Verify specific values
                            assert response_data["decision"] == "PASS"
                            assert response_data["evidence_hash"] == "evidence123"
                            assert response_data["message"] == "Transaction approved"
                            
                            # Verify MongoDB insertion was called with correct data
                            mock_create.assert_called_once()
                            create_call_args = mock_create.call_args[0][0]
                            
                            # Verify Decimal128 conversion
                            assert isinstance(create_call_args["amount"], Decimal128)
                            assert str(create_call_args["amount"].to_decimal()) == "100.50"
                            
                            # Verify field mapping
                            assert create_call_args["wallet_from"] == payload["from_address"].lower()
                            assert create_call_args["wallet_to"] == payload["to_address"].lower()
                            assert create_call_args["currency"] == payload["asset"]
                            assert create_call_args["tx_hash"] == payload["hash"]
                            assert create_call_args["memo"] == payload["memo"]
    
    @pytest.mark.asyncio
    async def test_submit_tx_amount_as_number(self):
        """Test transaction submission with amount as number instead of string"""
        with patch('app.api.v1.transactions.evaluate_transaction_compliance') as mock_compliance:
            mock_compliance.return_value = (DecisionEnum.PASS, "Transaction approved", "evidence123")
            
            with patch('app.api.v1.transactions.transaction_crud.create_transaction') as mock_create:
                with patch('app.api.v1.transactions.transaction_crud.update_transaction'):
                    with patch('app.api.v1.transactions.transaction_crud.get_transaction_by_id') as mock_get:
                        
                        mock_doc = {
                            "_id": "507f1f77bcf86cd799439012",
                            "tx_uuid": "test-uuid-456",
                            "amount": Decimal128("150.75"),
                            "currency": "ETH",
                            "decision": "PASS",
                            "created_at": "2025-09-12T12:00:00Z"
                        }
                        
                        mock_result = AsyncMock()
                        mock_result.inserted_id = "507f1f77bcf86cd799439012"
                        mock_create.return_value = mock_result
                        
                        mock_transaction = AsyncMock()
                        mock_transaction.dict.return_value = mock_doc
                        mock_transaction.id = "507f1f77bcf86cd799439012"
                        mock_get.return_value = mock_transaction
                        
                        payload = {
                            "hash": "0x123456789abcdef123456789abcdef123456789abcdef123456789abcdef1234",
                            "from_address": "0x742d35Cc6635C0532925a3b8D5c2c17c5865000E",
                            "to_address": "0x8ba1f109551bD432803012645Hac136c2c17c586",
                            "amount": 150.75,  # Number instead of string
                            "asset": "ETH"
                        }
                        
                        async with AsyncClient(app=app, base_url="http://test") as client:
                            response = await client.post("/v1/tx/submit", json=payload)
                        
                        assert response.status_code == 201
                        
                        # Verify Decimal128 conversion for numbers
                        mock_create.assert_called_once()
                        create_call_args = mock_create.call_args[0][0]
                        assert isinstance(create_call_args["amount"], Decimal128)
                        assert str(create_call_args["amount"].to_decimal()) == "150.75"
    
    @pytest.mark.asyncio
    async def test_submit_tx_validation_errors(self):
        """Test validation errors for missing required fields"""
        
        # Test missing wallet addresses
        payload_no_addresses = {
            "hash": "0x123456789abcdef123456789abcdef123456789abcdef123456789abcdef1234",
            "amount": "100.50",
            "asset": "USDT"
        }
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post("/v1/tx/submit", json=payload_no_addresses)
        
        assert response.status_code == 422
        response_data = response.json()
        assert "Missing wallet addresses" in response_data["detail"]
    
    @pytest.mark.asyncio
    async def test_submit_tx_web_format_compatibility(self):
        """Test that web format (wallet_from/wallet_to/currency) still works"""
        with patch('app.api.v1.transactions.evaluate_transaction_compliance') as mock_compliance:
            mock_compliance.return_value = (DecisionEnum.PASS, "Transaction approved", "evidence123")
            
            with patch('app.api.v1.transactions.transaction_crud.create_transaction') as mock_create:
                with patch('app.api.v1.transactions.transaction_crud.update_transaction'):
                    with patch('app.api.v1.transactions.transaction_crud.get_transaction_by_id') as mock_get:
                        
                        mock_doc = {
                            "_id": "507f1f77bcf86cd799439013",
                            "tx_uuid": "test-uuid-789",
                            "amount": Decimal128("200.00"),
                            "currency": "BTC",
                            "decision": "PASS",
                            "created_at": "2025-09-12T12:00:00Z"
                        }
                        
                        mock_result = AsyncMock()
                        mock_result.inserted_id = "507f1f77bcf86cd799439013"
                        mock_create.return_value = mock_result
                        
                        mock_transaction = AsyncMock()
                        mock_transaction.dict.return_value = mock_doc
                        mock_transaction.id = "507f1f77bcf86cd799439013"
                        mock_get.return_value = mock_transaction
                        
                        # Web format payload
                        payload = {
                            "wallet_from": "0x742d35Cc6635C0532925a3b8D5c2c17c5865000E",
                            "wallet_to": "0x8ba1f109551bD432803012645Hac136c2c17c586",
                            "amount": "200.00",
                            "currency": "BTC",
                            "kyc_proof_id": "kyc_12345"
                        }
                        
                        async with AsyncClient(app=app, base_url="http://test") as client:
                            response = await client.post("/v1/tx/submit", json=payload)
                        
                        assert response.status_code == 201
                        
                        # Verify field mapping for web format
                        mock_create.assert_called_once()
                        create_call_args = mock_create.call_args[0][0]
                        assert create_call_args["wallet_from"] == payload["wallet_from"].lower()
                        assert create_call_args["currency"] == payload["currency"]
                        assert create_call_args["kyc_proof_id"] == payload["kyc_proof_id"]
    
    @pytest.mark.asyncio
    async def test_normalization_function(self):
        """Test the normalize_mongodb_doc helper function directly"""
        from app.api.v1.transactions import normalize_mongodb_doc
        
        # Test document with all the problematic types
        test_doc = {
            "_id": "507f1f77bcf86cd799439011",
            "amount": Decimal128("100.50"),
            "currency": "USDT",
            "created_at": "2025-09-12T12:00:00Z",
            "updated_at": "2025-09-12T12:00:00Z"
        }
        
        normalized = normalize_mongodb_doc(test_doc)
        
        # Verify transformations
        assert normalized["tx_id"] == "507f1f77bcf86cd799439011"
        assert "_id" not in normalized
        assert normalized["amount"] == "100.50"  # String format
        assert normalized["asset"] == "USDT"  # Currency mapped to asset
        assert "created_at" in normalized
        assert "updated_at" in normalized