"""Comprehensive test cases for the transaction override endpoint"""

import pytest
import pytest_asyncio
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, patch
import httpx
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.models.transaction import TransactionModel, DecisionEnum
from app.services.transaction_crud import transaction_crud
from .conftest import MockTransactionData


@pytest.mark.asyncio
class TestOverrideEndpoint:
    """Test class for transaction override endpoint"""

    @pytest_asyncio.fixture
    async def mock_transaction(self):
        """Create a mock transaction for testing"""
        return TransactionModel(
            tx_uuid="123e4567-e89b-12d3-a456-426614174000",
            wallet_from="0x742d35Cc6634C0532925a3b8D4d0C123456789AB",
            wallet_to="0x123d35Cc6634C0532925a3b8D4d0C123456789CD",
            amount=100.5,
            currency="ETH",
            decision=DecisionEnum.HOLD,
            evidence_hash="original_evidence_123",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

    async def test_override_success_pass(self, mock_transaction):
        """Test successful override from HOLD to PASS"""
        with patch.object(transaction_crud, 'get_transaction_by_hash', return_value=mock_transaction), \
             patch.object(transaction_crud, 'add_review_audit', return_value=True), \
             patch.object(transaction_crud, 'update_transaction', return_value=True), \
             patch('app.api.v1.transactions.evidence_tree') as mock_evidence_tree:
            
            mock_evidence_tree.add_leaf.return_value = "merkle_leaf_123"
            
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/v1/override",
                    json={
                        "hash": "123e4567-e89b-12d3-a456-426614174000",
                        "status": "pass",
                        "reason": "Manual verification completed via secondary KYC process"
                    },
                    headers={"X-Admin-API-Key": "admin_key_12345"}
                )
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["success"] is True
            assert data["message"] == "Transaction override applied successfully"
            assert data["transaction_id"] == "123e4567-e89b-12d3-a456-426614174000"
            assert data["old_decision"] == "HOLD"
            assert data["new_decision"] == "PASS"
            assert "evidence_hash" in data
            assert "audit_entry" in data
            
            # Verify audit entry structure
            audit_entry = data["audit_entry"]
            assert audit_entry["action"] == "manual_override"
            assert audit_entry["old_decision"] == "HOLD"
            assert audit_entry["new_decision"] == "PASS"
            assert audit_entry["reason"] == "Manual verification completed via secondary KYC process"

    async def test_override_success_reject(self, mock_transaction):
        """Test successful override from HOLD to REJECT"""
        with patch.object(transaction_crud, 'get_transaction_by_hash', return_value=mock_transaction), \
             patch.object(transaction_crud, 'add_review_audit', return_value=True), \
             patch.object(transaction_crud, 'update_transaction', return_value=True), \
             patch('app.api.v1.transactions.evidence_tree') as mock_evidence_tree:
            
            mock_evidence_tree.add_leaf.return_value = "merkle_leaf_456"
            
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/v1/override",
                    json={
                        "hash": "tx_hash_456",
                        "status": "reject",
                        "reason": "Fraudulent activity detected during manual review"
                    },
                    headers={"X-Admin-API-Key": "admin_key_12345"}
                )
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["success"] is True
            assert data["old_decision"] == "HOLD"
            assert data["new_decision"] == "REJECT"

    async def test_override_unauthorized_invalid_key(self):
        """Test override with invalid admin API key"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/v1/override",
                json={
                    "hash": "123e4567-e89b-12d3-a456-426614174000",
                    "status": "pass",
                    "reason": "Should fail due to invalid key"
                },
                headers={"X-Admin-API-Key": "invalid_key"}
            )
        
        assert response.status_code == 401
        assert "Invalid admin API key" in response.json()["error"]["detail"]

    async def test_override_unauthorized_missing_key(self):
        """Test override without admin API key header"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/v1/override",
                json={
                    "hash": "123e4567-e89b-12d3-a456-426614174000",
                    "status": "pass",
                    "reason": "Should fail due to missing key"
                }
                # Missing X-Admin-API-Key header
            )
        
        assert response.status_code == 422  # Validation error for missing required header

    async def test_override_transaction_not_found(self):
        """Test override with non-existent transaction"""
        with patch.object(transaction_crud, 'get_transaction_by_hash', return_value=None):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/v1/override",
                    json={
                        "hash": "nonexistent_transaction",
                        "status": "pass",
                        "reason": "Should fail - transaction not found"
                    },
                    headers={"X-Admin-API-Key": "admin_key_12345"}
                )
        
        assert response.status_code == 404
        assert "Transaction not found" in response.json()["error"]["detail"]

    async def test_override_status_normalization(self, mock_transaction):
        """Test various status normalization scenarios"""
        test_cases = [
            ("approve", "PASS"),
            ("approved", "PASS"),
            ("accept", "PASS"),
            ("allow", "PASS"),
            ("pending", "HOLD"),
            ("review", "HOLD"),
            ("suspend", "HOLD"),
            ("pause", "HOLD"),
            ("deny", "REJECT"),
            ("block", "REJECT"),
            ("fail", "REJECT"),
        ]
        
        for input_status, expected_decision in test_cases:
            # Create transaction with different decision to ensure change
            test_transaction = TransactionModel(
                tx_uuid=f"test_{input_status}_{uuid.uuid4()}",
                wallet_from="0x742d35Cc6634C0532925a3b8D4d0C123456789AB",
                wallet_to="0x123d35Cc6634C0532925a3b8D4d0C123456789CD",
                amount=100.5,
                currency="ETH",
                decision=DecisionEnum.PENDING,  # Different from expected
                evidence_hash="test_evidence",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            with patch.object(transaction_crud, 'get_transaction_by_hash', return_value=test_transaction), \
                 patch.object(transaction_crud, 'add_review_audit', return_value=True), \
                 patch.object(transaction_crud, 'update_transaction', return_value=True), \
                 patch('app.api.v1.transactions.evidence_tree') as mock_evidence_tree:
                
                mock_evidence_tree.add_leaf.return_value = "merkle_leaf_test"
                
                async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                    response = await client.post(
                        "/v1/override",
                        json={
                            "hash": test_transaction.tx_uuid,
                            "status": input_status,
                            "reason": f"Testing {input_status} normalization"
                        },
                        headers={"X-Admin-API-Key": "admin_key_12345"}
                    )
                
                assert response.status_code == 200
                data = response.json()
                assert data["new_decision"] == expected_decision

    async def test_override_invalid_status(self):
        """Test override with invalid status value"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/v1/override",
                json={
                    "hash": "123e4567-e89b-12d3-a456-426614174000",
                    "status": "invalid_status",
                    "reason": "Should fail due to invalid status"
                },
                headers={"X-Admin-API-Key": "admin_key_12345"}
            )
        
        assert response.status_code == 422  # Validation error

    async def test_override_validation_errors(self):
        """Test various validation errors"""
        test_cases = [
            # Missing hash
            {
                "status": "pass",
                "reason": "Missing hash field"
            },
            # Missing status
            {
                "hash": "123e4567-e89b-12d3-a456-426614174000",
                "reason": "Missing status field"
            },
            # Missing reason
            {
                "hash": "123e4567-e89b-12d3-a456-426614174000",
                "status": "pass"
            },
            # Reason too short
            {
                "hash": "123e4567-e89b-12d3-a456-426614174000",
                "status": "pass",
                "reason": "Too short"
            },
            # Reason too long
            {
                "hash": "123e4567-e89b-12d3-a456-426614174000",
                "status": "pass",
                "reason": "x" * 501  # Over 500 character limit
            }
        ]
        
        for test_case in test_cases:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/v1/override",
                    json=test_case,
                    headers={"X-Admin-API-Key": "admin_key_12345"}
                )
            
            assert response.status_code == 422  # Validation error

    async def test_override_same_decision(self, mock_transaction):
        """Test override when new decision is same as current"""
        # Set transaction to PASS already
        mock_transaction.decision = DecisionEnum.PASS
        
        with patch.object(transaction_crud, 'get_transaction_by_hash', return_value=mock_transaction):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/v1/override",
                    json={
                        "hash": "123e4567-e89b-12d3-a456-426614174000",
                        "status": "pass",  # Same as current
                        "reason": "Testing same decision override"
                    },
                    headers={"X-Admin-API-Key": "admin_key_12345"}
                )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "already has decision" in data["message"]
        assert data["old_decision"] == "PASS"
        assert data["new_decision"] == "PASS"

    async def test_override_audit_failure(self, mock_transaction):
        """Test override when audit entry fails to add"""
        with patch.object(transaction_crud, 'get_transaction_by_hash', return_value=mock_transaction), \
             patch.object(transaction_crud, 'add_review_audit', return_value=False):  # Audit fails
            
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/v1/override",
                    json={
                        "hash": "123e4567-e89b-12d3-a456-426614174000",
                        "status": "pass",
                        "reason": "Should fail on audit"
                    },
                    headers={"X-Admin-API-Key": "admin_key_12345"}
                )
        
        assert response.status_code == 500
        assert "Failed to add audit entry" in response.json()["error"]["detail"]

    async def test_override_update_failure(self, mock_transaction):
        """Test override when transaction update fails"""
        with patch.object(transaction_crud, 'get_transaction_by_hash', return_value=mock_transaction), \
             patch.object(transaction_crud, 'add_review_audit', return_value=True), \
             patch.object(transaction_crud, 'update_transaction', return_value=False):  # Update fails
            
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/v1/override",
                    json={
                        "hash": "123e4567-e89b-12d3-a456-426614174000",
                        "status": "pass",
                        "reason": "Should fail on update"
                    },
                    headers={"X-Admin-API-Key": "admin_key_12345"}
                )
        
        assert response.status_code == 500
        assert "Failed to update transaction decision" in response.json()["error"]["detail"]

    async def test_override_merkle_integration(self, mock_transaction):
        """Test that Merkle tree integration works correctly"""
        with patch.object(transaction_crud, 'get_transaction_by_hash', return_value=mock_transaction), \
             patch.object(transaction_crud, 'add_review_audit', return_value=True), \
             patch.object(transaction_crud, 'update_transaction', return_value=True), \
             patch('app.api.v1.transactions.evidence_tree') as mock_evidence_tree:
            
            mock_evidence_tree.add_leaf.return_value = "merkle_leaf_evidence_123"
            
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/v1/override",
                    json={
                        "hash": "123e4567-e89b-12d3-a456-426614174000",
                        "status": "pass",
                        "reason": "Testing Merkle integration"
                    },
                    headers={"X-Admin-API-Key": "admin_key_12345"}
                )
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify Merkle tree was called
            mock_evidence_tree.add_leaf.assert_called_once()
            
            # Verify evidence hash was generated
            assert data["evidence_hash"]
            assert len(data["evidence_hash"]) == 64  # SHA256 hex length

    async def test_override_multiple_scenarios(self, mock_transaction):
        """Test multiple override scenarios in sequence"""
        scenarios = [
            {"status": "hold", "expected": "HOLD"},
            {"status": "reject", "expected": "REJECT"},
            {"status": "pass", "expected": "PASS"},
        ]
        
        for i, scenario in enumerate(scenarios):
            # Create unique transaction for each scenario
            test_transaction = TransactionModel(
                tx_uuid=f"multi_test_{i}_{uuid.uuid4()}",
                wallet_from="0x742d35Cc6634C0532925a3b8D4d0C123456789AB",
                wallet_to="0x123d35Cc6634C0532925a3b8D4d0C123456789CD",
                amount=100.5,
                currency="ETH",
                decision=DecisionEnum.PENDING,
                evidence_hash="multi_test_evidence",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            with patch.object(transaction_crud, 'get_transaction_by_hash', return_value=test_transaction), \
                 patch.object(transaction_crud, 'add_review_audit', return_value=True), \
                 patch.object(transaction_crud, 'update_transaction', return_value=True), \
                 patch('app.api.v1.transactions.evidence_tree') as mock_evidence_tree:
                
                mock_evidence_tree.add_leaf.return_value = f"merkle_leaf_{i}"
                
                async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                    response = await client.post(
                        "/v1/override",
                        json={
                            "hash": test_transaction.tx_uuid,
                            "status": scenario["status"],
                            "reason": f"Multi-scenario test {i+1}"
                        },
                        headers={"X-Admin-API-Key": "admin_key_12345"}
                    )
                
                assert response.status_code == 200
                data = response.json()
                assert data["new_decision"] == scenario["expected"]
                assert data["success"] is True