"""Comprehensive API integration tests for FastAPI endpoints with MongoDB backend"""

import pytest
from httpx import AsyncClient
import json
from datetime import datetime
from typing import Dict, Any

from app.main import app
from app.models.transaction import TransactionModel, TransactionStatus


class TestTransactionAPI:
    """Test transaction-related API endpoints"""

    @pytest.mark.asyncio
    async def test_create_transaction_success(self, client: AsyncClient, clean_database, transaction_data):
        """Test successful transaction creation"""
        response = await client.post("/api/v1/transactions/", json=transaction_data)
        
        assert response.status_code == 201
        data = response.json()
        
        assert "id" in data
        assert data["from_wallet"] == transaction_data["from_wallet"]
        assert data["to_wallet"] == transaction_data["to_wallet"]
        assert data["amount"] == transaction_data["amount"]
        assert data["currency"] == transaction_data["currency"]
        assert data["status"] == TransactionStatus.PENDING.value

    @pytest.mark.asyncio
    async def test_create_transaction_invalid_data(self, client: AsyncClient, clean_database):
        """Test transaction creation with invalid data"""
        invalid_data = {
            "from_wallet": "",  # Invalid empty wallet
            "to_wallet": "0x456",
            "amount": -100,  # Invalid negative amount
            "currency": "ETH"
        }
        
        response = await client.post("/api/v1/transactions/", json=invalid_data)
        
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    @pytest.mark.asyncio
    async def test_create_transaction_missing_fields(self, client: AsyncClient, clean_database):
        """Test transaction creation with missing required fields"""
        incomplete_data = {
            "from_wallet": "0x123",
            # Missing to_wallet, amount, currency
        }
        
        response = await client.post("/api/v1/transactions/", json=incomplete_data)
        
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_get_transaction_by_id(self, client: AsyncClient, clean_database, transaction_data):
        """Test retrieving transaction by ID"""
        # Create transaction first
        create_response = await client.post("/api/v1/transactions/", json=transaction_data)
        assert create_response.status_code == 201
        created_data = create_response.json()
        transaction_id = created_data["id"]
        
        # Retrieve transaction
        response = await client.get(f"/api/v1/transactions/{transaction_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == transaction_id
        assert data["from_wallet"] == transaction_data["from_wallet"]
        assert data["to_wallet"] == transaction_data["to_wallet"]

    @pytest.mark.asyncio
    async def test_get_transaction_not_found(self, client: AsyncClient, clean_database):
        """Test retrieving non-existent transaction"""
        fake_id = "507f1f77bcf86cd799439011"  # Valid ObjectId format
        
        response = await client.get(f"/api/v1/transactions/{fake_id}")
        
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data

    @pytest.mark.asyncio
    async def test_get_transaction_invalid_id(self, client: AsyncClient, clean_database):
        """Test retrieving transaction with invalid ID format"""
        invalid_id = "invalid_id_format"
        
        response = await client.get(f"/api/v1/transactions/{invalid_id}")
        
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_list_transactions(self, client: AsyncClient, clean_database):
        """Test listing transactions with pagination"""
        # Create multiple transactions
        transactions_data = []
        for i in range(5):
            tx_data = {
                "from_wallet": f"0x{i:064x}",
                "to_wallet": f"0x{i+1:064x}",
                "amount": 100 + i,
                "currency": "ETH",
                "metadata": {"test": f"transaction_{i}"}
            }
            transactions_data.append(tx_data)
            
            create_response = await client.post("/api/v1/transactions/", json=tx_data)
            assert create_response.status_code == 201
        
        # Test default listing
        response = await client.get("/api/v1/transactions/")
        
        assert response.status_code == 200
        data = response.json()
        assert "transactions" in data
        assert "total" in data
        assert "page" in data
        assert "limit" in data
        assert len(data["transactions"]) == 5
        assert data["total"] == 5

    @pytest.mark.asyncio
    async def test_list_transactions_with_pagination(self, client: AsyncClient, clean_database):
        """Test listing transactions with custom pagination"""
        # Create multiple transactions
        for i in range(10):
            tx_data = {
                "from_wallet": f"0x{i:064x}",
                "to_wallet": f"0x{i+1:064x}",
                "amount": 100 + i,
                "currency": "ETH"
            }
            
            create_response = await client.post("/api/v1/transactions/", json=tx_data)
            assert create_response.status_code == 201
        
        # Test pagination
        response = await client.get("/api/v1/transactions/?page=1&limit=3")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["transactions"]) == 3
        assert data["page"] == 1
        assert data["limit"] == 3
        assert data["total"] == 10

    @pytest.mark.asyncio
    async def test_list_transactions_with_filters(self, client: AsyncClient, clean_database):
        """Test listing transactions with filters"""
        # Create transactions with different statuses
        tx_data_pending = {
            "from_wallet": "0x123",
            "to_wallet": "0x456",
            "amount": 100,
            "currency": "ETH"
        }
        
        tx_data_completed = {
            "from_wallet": "0x789",
            "to_wallet": "0xabc",
            "amount": 200,
            "currency": "BTC"
        }
        
        # Create pending transaction
        create_response = await client.post("/api/v1/transactions/", json=tx_data_pending)
        assert create_response.status_code == 201
        pending_tx = create_response.json()
        
        # Create and complete another transaction
        create_response = await client.post("/api/v1/transactions/", json=tx_data_completed)
        assert create_response.status_code == 201
        completed_tx = create_response.json()
        
        # Update second transaction to completed
        update_response = await client.put(
            f"/api/v1/transactions/{completed_tx['id']}/status",
            json={"status": TransactionStatus.COMPLETED.value}
        )
        assert update_response.status_code == 200
        
        # Filter by status
        response = await client.get(f"/api/v1/transactions/?status={TransactionStatus.PENDING.value}")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["transactions"]) == 1
        assert data["transactions"][0]["id"] == pending_tx["id"]

    @pytest.mark.asyncio
    async def test_update_transaction_status(self, client: AsyncClient, clean_database, transaction_data):
        """Test updating transaction status"""
        # Create transaction
        create_response = await client.post("/api/v1/transactions/", json=transaction_data)
        assert create_response.status_code == 201
        created_data = create_response.json()
        transaction_id = created_data["id"]
        
        # Update status
        update_data = {"status": TransactionStatus.COMPLETED.value}
        response = await client.put(f"/api/v1/transactions/{transaction_id}/status", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == TransactionStatus.COMPLETED.value

    @pytest.mark.asyncio
    async def test_update_transaction_status_invalid(self, client: AsyncClient, clean_database, transaction_data):
        """Test updating transaction with invalid status"""
        # Create transaction
        create_response = await client.post("/api/v1/transactions/", json=transaction_data)
        assert create_response.status_code == 201
        created_data = create_response.json()
        transaction_id = created_data["id"]
        
        # Try invalid status
        update_data = {"status": "INVALID_STATUS"}
        response = await client.put(f"/api/v1/transactions/{transaction_id}/status", json=update_data)
        
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_delete_transaction(self, client: AsyncClient, clean_database, transaction_data):
        """Test deleting a transaction"""
        # Create transaction
        create_response = await client.post("/api/v1/transactions/", json=transaction_data)
        assert create_response.status_code == 201
        created_data = create_response.json()
        transaction_id = created_data["id"]
        
        # Delete transaction
        response = await client.delete(f"/api/v1/transactions/{transaction_id}")
        
        assert response.status_code == 204
        
        # Verify deletion
        get_response = await client.get(f"/api/v1/transactions/{transaction_id}")
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_nonexistent_transaction(self, client: AsyncClient, clean_database):
        """Test deleting a non-existent transaction"""
        fake_id = "507f1f77bcf86cd799439011"
        
        response = await client.delete(f"/api/v1/transactions/{fake_id}")
        
        assert response.status_code == 404


class TestComplianceAPI:
    """Test compliance-related API endpoints"""

    @pytest.mark.asyncio
    async def test_check_compliance_valid_transaction(self, client: AsyncClient, clean_database, transaction_data):
        """Test compliance check for valid transaction"""
        response = await client.post("/api/v1/compliance/check", json=transaction_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "is_compliant" in data
        assert "violations" in data
        assert "compliance_score" in data
        assert isinstance(data["is_compliant"], bool)

    @pytest.mark.asyncio
    async def test_check_compliance_blacklisted_wallet(self, client: AsyncClient, clean_database):
        """Test compliance check with blacklisted wallet"""
        # Create blacklist entry first
        blacklist_data = {
            "wallet_address": "0xBlacklisted123",
            "reason": "Suspicious activity",
            "severity": "HIGH"
        }
        
        blacklist_response = await client.post("/api/v1/compliance/blacklist", json=blacklist_data)
        assert blacklist_response.status_code == 201
        
        # Test transaction with blacklisted wallet
        tx_data = {
            "from_wallet": "0xBlacklisted123",
            "to_wallet": "0x456",
            "amount": 100,
            "currency": "ETH"
        }
        
        response = await client.post("/api/v1/compliance/check", json=tx_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["is_compliant"] is False
        assert len(data["violations"]) > 0

    @pytest.mark.asyncio
    async def test_check_compliance_high_amount(self, client: AsyncClient, clean_database):
        """Test compliance check with high amount transaction"""
        tx_data = {
            "from_wallet": "0x123",
            "to_wallet": "0x456",
            "amount": 1000000,  # High amount
            "currency": "ETH"
        }
        
        response = await client.post("/api/v1/compliance/check", json=tx_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "is_compliant" in data
        assert "violations" in data

    @pytest.mark.asyncio
    async def test_add_blacklist_entry(self, client: AsyncClient, clean_database):
        """Test adding wallet to blacklist"""
        blacklist_data = {
            "wallet_address": "0xSuspicious123",
            "reason": "Money laundering",
            "severity": "HIGH"
        }
        
        response = await client.post("/api/v1/compliance/blacklist", json=blacklist_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["wallet_address"] == blacklist_data["wallet_address"]
        assert data["reason"] == blacklist_data["reason"]
        assert data["severity"] == blacklist_data["severity"]

    @pytest.mark.asyncio
    async def test_get_blacklist(self, client: AsyncClient, clean_database):
        """Test retrieving blacklist entries"""
        # Add entries to blacklist
        entries = [
            {"wallet_address": "0xBad1", "reason": "Fraud", "severity": "HIGH"},
            {"wallet_address": "0xBad2", "reason": "Theft", "severity": "MEDIUM"},
        ]
        
        for entry in entries:
            response = await client.post("/api/v1/compliance/blacklist", json=entry)
            assert response.status_code == 201
        
        # Get blacklist
        response = await client.get("/api/v1/compliance/blacklist")
        
        assert response.status_code == 200
        data = response.json()
        assert "entries" in data
        assert len(data["entries"]) == 2

    @pytest.mark.asyncio
    async def test_remove_blacklist_entry(self, client: AsyncClient, clean_database):
        """Test removing wallet from blacklist"""
        # Add entry first
        blacklist_data = {
            "wallet_address": "0xRemoveMe",
            "reason": "Test entry",
            "severity": "LOW"
        }
        
        create_response = await client.post("/api/v1/compliance/blacklist", json=blacklist_data)
        assert create_response.status_code == 201
        entry_id = create_response.json()["id"]
        
        # Remove entry
        response = await client.delete(f"/api/v1/compliance/blacklist/{entry_id}")
        
        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_get_compliance_rules(self, client: AsyncClient, clean_database):
        """Test retrieving compliance rules"""
        response = await client.get("/api/v1/compliance/rules")
        
        assert response.status_code == 200
        data = response.json()
        assert "rules" in data
        assert isinstance(data["rules"], list)

    @pytest.mark.asyncio
    async def test_update_compliance_rules(self, client: AsyncClient, clean_database):
        """Test updating compliance rules"""
        new_rules = {
            "max_transaction_amount": 500000,
            "daily_transaction_limit": 1000000,
            "kyc_required_amount": 10000,
            "blacklist_enabled": True
        }
        
        response = await client.put("/api/v1/compliance/rules", json=new_rules)
        
        assert response.status_code == 200
        data = response.json()
        assert data["max_transaction_amount"] == new_rules["max_transaction_amount"]


class TestMerkleAPI:
    """Test Merkle tree and evidence API endpoints"""

    @pytest.mark.asyncio
    async def test_create_evidence_tree(self, client: AsyncClient, clean_database):
        """Test creating Merkle tree for evidence"""
        evidence_data = {
            "evidence_hashes": [
                "0x1111111111111111111111111111111111111111111111111111111111111111",
                "0x2222222222222222222222222222222222222222222222222222222222222222",
                "0x3333333333333333333333333333333333333333333333333333333333333333"
            ]
        }
        
        response = await client.post("/api/v1/merkle/create-tree", json=evidence_data)
        
        assert response.status_code == 201
        data = response.json()
        assert "tree_id" in data
        assert "root_hash" in data
        assert "tree_info" in data
        assert data["tree_info"]["total_leaves"] == 3

    @pytest.mark.asyncio
    async def test_get_merkle_proof(self, client: AsyncClient, clean_database):
        """Test getting Merkle proof for evidence"""
        # Create tree first
        evidence_data = {
            "evidence_hashes": [
                "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                "0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
            ]
        }
        
        create_response = await client.post("/api/v1/merkle/create-tree", json=evidence_data)
        assert create_response.status_code == 201
        tree_data = create_response.json()
        tree_id = tree_data["tree_id"]
        
        # Get proof for first evidence
        evidence_hash = evidence_data["evidence_hashes"][0]
        response = await client.get(f"/api/v1/merkle/proof/{tree_id}/{evidence_hash}")
        
        assert response.status_code == 200
        data = response.json()
        assert "proof" in data
        assert data["proof"]["leaf_hash"] == evidence_hash
        assert "proof_hashes" in data["proof"]
        assert "proof_directions" in data["proof"]

    @pytest.mark.asyncio
    async def test_verify_merkle_proof(self, client: AsyncClient, clean_database):
        """Test verifying Merkle proof"""
        # Create tree and get proof
        evidence_data = {
            "evidence_hashes": [
                "0x1111111111111111111111111111111111111111111111111111111111111111",
                "0x2222222222222222222222222222222222222222222222222222222222222222"
            ]
        }
        
        create_response = await client.post("/api/v1/merkle/create-tree", json=evidence_data)
        assert create_response.status_code == 201
        tree_data = create_response.json()
        tree_id = tree_data["tree_id"]
        
        # Get proof
        evidence_hash = evidence_data["evidence_hashes"][0]
        proof_response = await client.get(f"/api/v1/merkle/proof/{tree_id}/{evidence_hash}")
        assert proof_response.status_code == 200
        proof_data = proof_response.json()
        
        # Verify proof
        verify_data = {
            "evidence_hash": evidence_hash,
            "proof": proof_data["proof"],
            "expected_root": tree_data["root_hash"]
        }
        
        response = await client.post("/api/v1/merkle/verify-proof", json=verify_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["is_valid"] is True

    @pytest.mark.asyncio
    async def test_verify_invalid_merkle_proof(self, client: AsyncClient, clean_database):
        """Test verifying invalid Merkle proof"""
        invalid_proof_data = {
            "evidence_hash": "0x1111111111111111111111111111111111111111111111111111111111111111",
            "proof": {
                "leaf_hash": "0x1111111111111111111111111111111111111111111111111111111111111111",
                "leaf_index": 0,
                "proof_hashes": ["0xwrong"],
                "proof_directions": ["right"],
                "root_hash": "0xwrongroot"
            },
            "expected_root": "0xdifferentroot"
        }
        
        response = await client.post("/api/v1/merkle/verify-proof", json=invalid_proof_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["is_valid"] is False

    @pytest.mark.asyncio
    async def test_get_tree_info(self, client: AsyncClient, clean_database):
        """Test getting Merkle tree information"""
        # Create tree first
        evidence_data = {
            "evidence_hashes": [
                "0x1111111111111111111111111111111111111111111111111111111111111111",
                "0x2222222222222222222222222222222222222222222222222222222222222222",
                "0x3333333333333333333333333333333333333333333333333333333333333333",
                "0x4444444444444444444444444444444444444444444444444444444444444444"
            ]
        }
        
        create_response = await client.post("/api/v1/merkle/create-tree", json=evidence_data)
        assert create_response.status_code == 201
        tree_data = create_response.json()
        tree_id = tree_data["tree_id"]
        
        # Get tree info
        response = await client.get(f"/api/v1/merkle/tree/{tree_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert "tree_info" in data
        assert data["tree_info"]["total_leaves"] == 4
        assert "root_hash" in data
        assert data["root_hash"] == tree_data["root_hash"]


class TestHealthAPI:
    """Test health check and status endpoints"""

    @pytest.mark.asyncio
    async def test_health_check(self, client: AsyncClient):
        """Test health check endpoint"""
        response = await client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert data["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_database_health(self, client: AsyncClient):
        """Test database health check"""
        response = await client.get("/health/database")
        
        assert response.status_code == 200
        data = response.json()
        assert "database_status" in data
        assert "connection_info" in data

    @pytest.mark.asyncio
    async def test_api_info(self, client: AsyncClient):
        """Test API information endpoint"""
        response = await client.get("/info")
        
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert "environment" in data


class TestErrorHandling:
    """Test API error handling scenarios"""

    @pytest.mark.asyncio
    async def test_invalid_json_payload(self, client: AsyncClient):
        """Test handling of invalid JSON payload"""
        # Send malformed JSON
        response = await client.post(
            "/api/v1/transactions/",
            content="invalid json content",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_unsupported_content_type(self, client: AsyncClient):
        """Test handling of unsupported content type"""
        response = await client.post(
            "/api/v1/transactions/",
            content="some data",
            headers={"Content-Type": "text/plain"}
        )
        
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_method_not_allowed(self, client: AsyncClient):
        """Test method not allowed error"""
        response = await client.patch("/api/v1/transactions/")
        
        assert response.status_code == 405

    @pytest.mark.asyncio
    async def test_endpoint_not_found(self, client: AsyncClient):
        """Test 404 for non-existent endpoint"""
        response = await client.get("/api/v1/nonexistent")
        
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_internal_server_error_handling(self, client: AsyncClient):
        """Test internal server error handling"""
        # This would test error handling when database is down
        # For now, we test that error responses are properly formatted
        
        # Try to access transaction with invalid ObjectId format that causes server error
        response = await client.get("/api/v1/transactions/invalid_format_that_causes_error")
        
        # Should return 422 for validation error, not 500
        assert response.status_code in [422, 400, 404]


class TestAuthentication:
    """Test authentication and authorization (if implemented)"""

    @pytest.mark.asyncio
    async def test_unauthenticated_access(self, client: AsyncClient):
        """Test access without authentication (if auth is required)"""
        # Note: If your API doesn't require auth, these tests may not be relevant
        
        # Try accessing protected endpoint without auth
        response = await client.get("/api/v1/transactions/")
        
        # Should either succeed (no auth required) or return 401
        assert response.status_code in [200, 401]

    @pytest.mark.asyncio
    async def test_invalid_token(self, client: AsyncClient):
        """Test access with invalid token (if auth is implemented)"""
        headers = {"Authorization": "Bearer invalid_token"}
        
        response = await client.get("/api/v1/transactions/", headers=headers)
        
        # Should either succeed (no auth) or return 401
        assert response.status_code in [200, 401]


class TestConcurrency:
    """Test concurrent API operations"""

    @pytest.mark.asyncio
    async def test_concurrent_transaction_creation(self, client: AsyncClient, clean_database):
        """Test concurrent transaction creation"""
        import asyncio
        
        # Create multiple transactions concurrently
        async def create_transaction(index: int):
            tx_data = {
                "from_wallet": f"0x{index:064x}",
                "to_wallet": f"0x{index+1000:064x}",
                "amount": 100 + index,
                "currency": "ETH",
                "metadata": {"concurrent_test": True, "index": index}
            }
            
            response = await client.post("/api/v1/transactions/", json=tx_data)
            return response.status_code, response.json()
        
        # Run 10 concurrent operations
        tasks = [create_transaction(i) for i in range(10)]
        results = await asyncio.gather(*tasks)
        
        # All should succeed
        for status_code, data in results:
            assert status_code == 201
            assert "id" in data

    @pytest.mark.asyncio
    async def test_concurrent_reads(self, client: AsyncClient, clean_database, transaction_data):
        """Test concurrent read operations"""
        import asyncio
        
        # Create a transaction first
        create_response = await client.post("/api/v1/transactions/", json=transaction_data)
        assert create_response.status_code == 201
        transaction_id = create_response.json()["id"]
        
        # Perform concurrent reads
        async def read_transaction():
            response = await client.get(f"/api/v1/transactions/{transaction_id}")
            return response.status_code, response.json()
        
        tasks = [read_transaction() for _ in range(20)]
        results = await asyncio.gather(*tasks)
        
        # All reads should succeed
        for status_code, data in results:
            assert status_code == 200
            assert data["id"] == transaction_id

    @pytest.mark.asyncio
    async def test_concurrent_compliance_checks(self, client: AsyncClient, clean_database):
        """Test concurrent compliance checks"""
        import asyncio
        
        async def check_compliance(index: int):
            tx_data = {
                "from_wallet": f"0x{index:064x}",
                "to_wallet": f"0x{index+2000:064x}",
                "amount": 100 + index,
                "currency": "ETH"
            }
            
            response = await client.post("/api/v1/compliance/check", json=tx_data)
            return response.status_code, response.json()
        
        tasks = [check_compliance(i) for i in range(15)]
        results = await asyncio.gather(*tasks)
        
        # All compliance checks should succeed
        for status_code, data in results:
            assert status_code == 200
            assert "is_compliant" in data


@pytest.mark.integration
class TestEndToEndScenarios:
    """End-to-end integration test scenarios"""

    @pytest.mark.asyncio
    async def test_full_transaction_lifecycle(self, client: AsyncClient, clean_database):
        """Test complete transaction lifecycle"""
        # 1. Create transaction
        tx_data = {
            "from_wallet": "0x1234567890123456789012345678901234567890",
            "to_wallet": "0xabcdefabcdefabcdefabcdefabcdefabcdefabcd",
            "amount": 1000,
            "currency": "ETH",
            "metadata": {"purpose": "Payment", "reference": "INV-001"}
        }
        
        create_response = await client.post("/api/v1/transactions/", json=tx_data)
        assert create_response.status_code == 201
        created_tx = create_response.json()
        tx_id = created_tx["id"]
        
        # 2. Check compliance
        compliance_response = await client.post("/api/v1/compliance/check", json=tx_data)
        assert compliance_response.status_code == 200
        compliance_data = compliance_response.json()
        
        # 3. Retrieve transaction
        get_response = await client.get(f"/api/v1/transactions/{tx_id}")
        assert get_response.status_code == 200
        retrieved_tx = get_response.json()
        assert retrieved_tx["id"] == tx_id
        
        # 4. Update transaction status
        if compliance_data["is_compliant"]:
            status_update = {"status": TransactionStatus.COMPLETED.value}
            update_response = await client.put(f"/api/v1/transactions/{tx_id}/status", json=status_update)
            assert update_response.status_code == 200
            
            # 5. Verify status update
            final_response = await client.get(f"/api/v1/transactions/{tx_id}")
            assert final_response.status_code == 200
            final_tx = final_response.json()
            assert final_tx["status"] == TransactionStatus.COMPLETED.value

    @pytest.mark.asyncio
    async def test_evidence_anchoring_workflow(self, client: AsyncClient, clean_database):
        """Test complete evidence anchoring workflow"""
        # 1. Create transactions to use as evidence
        evidence_transactions = []
        for i in range(3):
            tx_data = {
                "from_wallet": f"0x{i:064x}",
                "to_wallet": f"0x{i+100:064x}",
                "amount": 100 * (i + 1),
                "currency": "ETH"
            }
            
            response = await client.post("/api/v1/transactions/", json=tx_data)
            assert response.status_code == 201
            evidence_transactions.append(response.json())
        
        # 2. Generate evidence hashes (simulated)
        evidence_hashes = [
            f"0x{i:064x}" for i in range(len(evidence_transactions))
        ]
        
        # 3. Create Merkle tree for evidence
        tree_data = {"evidence_hashes": evidence_hashes}
        tree_response = await client.post("/api/v1/merkle/create-tree", json=tree_data)
        assert tree_response.status_code == 201
        tree_info = tree_response.json()
        tree_id = tree_info["tree_id"]
        
        # 4. Get proofs for each evidence
        proofs = []
        for evidence_hash in evidence_hashes:
            proof_response = await client.get(f"/api/v1/merkle/proof/{tree_id}/{evidence_hash}")
            assert proof_response.status_code == 200
            proofs.append(proof_response.json()["proof"])
        
        # 5. Verify each proof
        for i, proof in enumerate(proofs):
            verify_data = {
                "evidence_hash": evidence_hashes[i],
                "proof": proof,
                "expected_root": tree_info["root_hash"]
            }
            
            verify_response = await client.post("/api/v1/merkle/verify-proof", json=verify_data)
            assert verify_response.status_code == 200
            verify_result = verify_response.json()
            assert verify_result["is_valid"] is True

    @pytest.mark.asyncio
    async def test_high_volume_operations(self, client: AsyncClient, clean_database):
        """Test high-volume operations"""
        import asyncio
        
        # Create many transactions rapidly
        num_transactions = 50
        
        async def create_batch_transaction(batch_id: int, tx_index: int):
            tx_data = {
                "from_wallet": f"0x{batch_id:032x}{tx_index:032x}",
                "to_wallet": f"0x{batch_id+1:032x}{tx_index+1:032x}",
                "amount": 100 + tx_index,
                "currency": "ETH",
                "metadata": {"batch_id": batch_id, "tx_index": tx_index}
            }
            
            response = await client.post("/api/v1/transactions/", json=tx_data)
            return response.status_code == 201
        
        # Create transactions in batches
        batch_size = 10
        all_successful = True
        
        for batch in range(0, num_transactions, batch_size):
            batch_tasks = [
                create_batch_transaction(batch // batch_size, i)
                for i in range(batch, min(batch + batch_size, num_transactions))
            ]
            
            batch_results = await asyncio.gather(*batch_tasks)
            if not all(batch_results):
                all_successful = False
                break
        
        assert all_successful
        
        # Verify all transactions were created
        list_response = await client.get(f"/api/v1/transactions/?limit={num_transactions}")
        assert list_response.status_code == 200
        list_data = list_response.json()
        assert list_data["total"] == num_transactions