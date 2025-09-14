"""
Tests for the transaction listing endpoint
"""
import pytest
from httpx import AsyncClient
from bson import ObjectId
from bson.decimal128 import Decimal128
from datetime import datetime, timezone
from unittest.mock import patch

from app.utils.normalizers import normalize_for_response


class TestListTransactions:
    """Test cases for transaction listing endpoints"""
    
    @pytest.mark.asyncio
    async def test_list_transactions_success(self, client: AsyncClient, mock_database):
        """Test successful transaction listing"""
        # Mock database response with sample transactions
        mock_transactions = [
            {
                "_id": ObjectId("507f1f77bcf86cd799439011"),
                "tx_hash": "0x123456789abcdef123456789abcdef123456789abcdef123456789abcdef1234",
                "wallet_from": "0x742d35cc6635c0532925a3b8d5c2c17c5865000e",
                "wallet_to": "0x8ba1f109551bd432803012645hac136c2c17c586",
                "amount": Decimal128("100.50"),
                "currency": "USDT",
                "decision": "PENDING",
                "memo": "Test transaction",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            },
            {
                "_id": ObjectId("507f1f77bcf86cd799439012"),
                "tx_hash": "0x987654321fedcba987654321fedcba987654321fedcba987654321fedcba9876",
                "wallet_from": "0x8ba1f109551bd432803012645hac136c2c17c586",
                "wallet_to": "0x742d35cc6635c0532925a3b8d5c2c17c5865000e",
                "amount": Decimal128("50.25"),
                "currency": "ETH",
                "decision": "APPROVED",
                "memo": None,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            }
        ]
        
        # Mock the database find operation
        mock_cursor = mock_database.transactions.find.return_value
        mock_cursor.sort.return_value = mock_cursor
        
        response = await client.get("/v1/tx/list")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "transactions" in data
        assert "total" in data
        assert "page" in data
        assert "per_page" in data
        assert "total_pages" in data
        
        # Verify data content
        assert data["total"] == 2
        assert len(data["transactions"]) == 2
        
        # Verify first transaction
        tx1 = data["transactions"][0]
        assert tx1["tx_id"] == "507f1f77bcf86cd799439011"
        assert tx1["hash"] == "0x123456789abcdef123456789abcdef123456789abcdef123456789abcdef1234"
        assert tx1["wallet_from"] == "0x742d35cc6635c0532925a3b8d5c2c17c5865000e"
        assert tx1["wallet_to"] == "0x8ba1f109551bd432803012645hac136c2c17c586"
        assert tx1["amount"] == "100.50"  # String format for JSON
        assert tx1["asset"] == "USDT"
        assert tx1["decision"] == "PENDING"
        assert tx1["memo"] == "Test transaction"
        assert "created_at" in tx1
        
        # Verify second transaction
        tx2 = data["transactions"][1]
        assert tx2["tx_id"] == "507f1f77bcf86cd799439012"
        assert tx2["amount"] == "50.25"
        assert tx2["asset"] == "ETH"
        assert tx2["decision"] == "APPROVED"
        assert tx2["memo"] is None
    
    @pytest.mark.asyncio
    async def test_list_transactions_with_pagination(self, client: AsyncClient, mock_database):
        """Test transaction listing with pagination parameters"""
        mock_transactions = []
        
        mock_cursor = mock_database.transactions.find.return_value
        mock_cursor.sort.return_value = mock_cursor
        mock_cursor.skip.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.to_list.return_value = mock_transactions
        
        mock_database.transactions.count_documents.return_value = 0
        
        response = await client.get("/v1/tx/list?page=2&per_page=5")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["page"] == 2
        assert data["per_page"] == 5
        assert data["total"] == 0
        assert data["total_pages"] == 0
        assert data["transactions"] == []
        
        # Verify database was called with correct pagination
        mock_database.transactions.find.assert_called_once()
        mock_cursor.skip.assert_called_with(5)  # (page-1) * per_page = (2-1) * 5 = 5
        mock_cursor.limit.assert_called_with(5)
    
    @pytest.mark.asyncio
    async def test_list_transactions_filter_by_wallet(self, client: AsyncClient, mock_database):
        """Test transaction listing filtered by wallet address"""
        mock_transactions = []
        
        mock_cursor = mock_database.transactions.find.return_value
        mock_cursor.sort.return_value = mock_cursor
        mock_cursor.skip.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.to_list.return_value = mock_transactions
        
        mock_database.transactions.count_documents.return_value = 0
        
        wallet_address = "0x742d35cc6635c0532925a3b8d5c2c17c5865000e"
        response = await client.get(f"/v1/tx/list?wallet={wallet_address}")
        
        assert response.status_code == 200
        
        # Verify database was called with wallet filter
        mock_database.transactions.find.assert_called_once()
        call_args = mock_database.transactions.find.call_args[0][0]
        
        # Should filter by either wallet_from or wallet_to
        assert "$or" in call_args
        assert {"wallet_from": wallet_address.lower()} in call_args["$or"]
        assert {"wallet_to": wallet_address.lower()} in call_args["$or"]
    
    @pytest.mark.asyncio
    async def test_list_transactions_filter_by_status(self, client: AsyncClient, mock_database):
        """Test transaction listing filtered by decision status"""
        mock_transactions = []
        
        mock_cursor = mock_database.transactions.find.return_value
        mock_cursor.sort.return_value = mock_cursor
        mock_cursor.skip.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.to_list.return_value = mock_transactions
        
        mock_database.transactions.count_documents.return_value = 0
        
        response = await client.get("/v1/tx/list?status=APPROVED")
        
        assert response.status_code == 200
        
        # Verify database was called with status filter
        mock_database.transactions.find.assert_called_once()
        call_args = mock_database.transactions.find.call_args[0][0]
        assert call_args["decision"] == "APPROVED"
    
    @pytest.mark.asyncio
    async def test_list_transactions_database_error(self, client: AsyncClient, mock_database):
        """Test error handling when database query fails"""
        # Make database query fail
        mock_database.transactions.find.side_effect = Exception("Database connection failed")
        
        response = await client.get("/v1/tx/list")
        
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "trace_id" in data["detail"]
        assert data["detail"]["error"] == "Internal server error"
    
    @pytest.mark.asyncio
    async def test_list_transactions_invalid_pagination(self, client: AsyncClient, mock_database):
        """Test error handling for invalid pagination parameters"""
        response = await client.get("/v1/tx/list?page=0&per_page=-1")
        
        # Should handle invalid pagination gracefully
        assert response.status_code in [200, 422]  # Either corrected or validation error
    
    @pytest.mark.asyncio
    async def test_normalize_for_response_function(self):
        """Test the normalize_for_response function directly"""
        # Create a mock MongoDB document
        mongo_doc = {
            "_id": ObjectId("507f1f77bcf86cd799439011"),
            "tx_hash": "0x123456789abcdef123456789abcdef123456789abcdef123456789abcdef1234",
            "wallet_from": "0x742d35cc6635c0532925a3b8d5c2c17c5865000e",
            "wallet_to": "0x8ba1f109551bd432803012645hac136c2c17c586",
            "amount": Decimal128("100.50"),
            "currency": "USDT",
            "decision": "PENDING",
            "memo": "Test transaction",
            "created_at": datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
            "updated_at": datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        }
        
        # Normalize for response
        response_doc = normalize_for_response(mongo_doc)
        
        # Verify transformations
        assert response_doc["tx_id"] == "507f1f77bcf86cd799439011"
        assert "_id" not in response_doc
        assert response_doc["hash"] == mongo_doc["tx_hash"]
        assert response_doc["asset"] == mongo_doc["currency"]
        assert response_doc["amount"] == "100.50"  # String format
        assert isinstance(response_doc["created_at"], str)  # ISO format
        assert isinstance(response_doc["updated_at"], str)  # ISO format
        
        # Verify other fields are preserved
        assert response_doc["wallet_from"] == mongo_doc["wallet_from"]
        assert response_doc["wallet_to"] == mongo_doc["wallet_to"]
        assert response_doc["decision"] == mongo_doc["decision"]
        assert response_doc["memo"] == mongo_doc["memo"]
    
    @pytest.mark.asyncio
    async def test_list_transactions_empty_result(self, client: AsyncClient, mock_database):
        """Test transaction listing when no transactions found"""
        mock_cursor = mock_database.transactions.find.return_value
        mock_cursor.sort.return_value = mock_cursor
        mock_cursor.skip.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.to_list.return_value = []
        
        mock_database.transactions.count_documents.return_value = 0
        
        response = await client.get("/v1/tx/list")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] == 0
        assert data["transactions"] == []
        assert data["total_pages"] == 0
        assert data["page"] == 1
        assert data["per_page"] == 10  # Default value
        response = await client.get("/v1/tx/list?page=0")
        assert response.status_code == 422
        
        # Test invalid per_page number
        response = await client.get("/v1/tx/list?per_page=101")
        assert response.status_code == 422