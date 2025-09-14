"""
Tests for Polygon Anchor Service

This module tests the blockchain anchoring functionality including
smart contract interaction, event parsing, and API endpoints.
"""

import pytest
import json
import os
import asyncio
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient

from app.services.polygon_anchor import (
    PolygonAnchorService,
    PolygonAnchorError,
    create_anchor_service
)
from app.api.v1.anchor import router
from app.main import app

# Test constants
TEST_ROOT = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
TEST_CONTRACT_ADDRESS = "0x1234567890123456789012345678901234567890"
TEST_PRIVATE_KEY = "0x" + "1" * 64  # Dummy private key for testing
TEST_RPC_URL = "http://127.0.0.1:8545"

class TestPolygonAnchorService:
    """Test the PolygonAnchorService class"""
    
    @pytest.fixture
    def mock_env_vars(self, monkeypatch):
        """Set up test environment variables"""
        monkeypatch.setenv("POLYGON_RPC_URL", TEST_RPC_URL)
        monkeypatch.setenv("ANCHORER_PRIVATE_KEY", TEST_PRIVATE_KEY)
        monkeypatch.setenv("CONTRACT_ADDRESS", TEST_CONTRACT_ADDRESS)
    
    @pytest.fixture
    def mock_web3(self):
        """Mock Web3 instance"""
        with patch('app.services.polygon_anchor.Web3') as mock_web3_class:
            mock_w3 = Mock()
            mock_web3_class.return_value = mock_w3
            
            # Mock Web3 connection
            mock_w3.is_connected.return_value = True
            mock_w3.eth.chain_id = 31337
            mock_w3.eth.block_number = 1000
            mock_w3.eth.gas_price = 20000000000  # 20 gwei
            mock_w3.from_wei.return_value = "1.0"
            
            # Mock account
            mock_w3.eth.get_transaction_count.return_value = 5
            mock_w3.eth.get_balance.return_value = 1000000000000000000  # 1 ETH
            
            # Mock contract
            mock_contract = Mock()
            mock_contract.functions.version.return_value.call.return_value = "1.0.0"
            mock_contract.functions.owner.return_value.call.return_value = "0x" + "1" * 40
            mock_w3.eth.contract.return_value = mock_contract
            
            yield mock_w3, mock_contract
    
    def test_service_initialization(self, mock_env_vars):
        """Test service initialization with environment variables"""
        service = PolygonAnchorService()
        
        assert service.rpc_url == TEST_RPC_URL
        assert service.contract_address == TEST_CONTRACT_ADDRESS
        assert service.account.address is not None
    
    def test_service_initialization_missing_key(self, monkeypatch):
        """Test service fails without private key"""
        monkeypatch.setenv("CONTRACT_ADDRESS", TEST_CONTRACT_ADDRESS)
        monkeypatch.delenv("ANCHORER_PRIVATE_KEY", raising=False)
        
        with pytest.raises(PolygonAnchorError, match="ANCHORER_PRIVATE_KEY"):
            PolygonAnchorService()
    
    def test_service_initialization_missing_contract(self, monkeypatch):
        """Test service fails without contract address"""
        monkeypatch.setenv("ANCHORER_PRIVATE_KEY", TEST_PRIVATE_KEY)
        monkeypatch.delenv("CONTRACT_ADDRESS", raising=False)
        
        with pytest.raises(PolygonAnchorError, match="CONTRACT_ADDRESS"):
            PolygonAnchorService()
    
    def test_hex_format_validation(self, mock_env_vars, mock_web3):
        """Test hex format validation"""
        service = PolygonAnchorService()
        
        # Test with 0x prefix
        formatted = service._ensure_hex_format("0x1234")
        assert formatted.startswith("0x")
        
        # Test without 0x prefix
        root_without_prefix = "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        formatted = service._ensure_hex_format(root_without_prefix)
        assert formatted == "0x" + root_without_prefix
        
        # Test invalid length
        with pytest.raises(ValueError, match="Invalid root hash length"):
            service._ensure_hex_format("0x1234")
    
    def test_health_check_success(self, mock_env_vars, mock_web3):
        """Test successful health check"""
        mock_w3, mock_contract = mock_web3
        service = PolygonAnchorService()
        
        health = service.health_check()
        
        assert health["healthy"] is True
        assert health["contract_address"] == TEST_CONTRACT_ADDRESS
        assert health["contract_version"] == "1.0.0"
        assert "anchorer_address" in health
        assert "anchorer_balance_eth" in health
    
    def test_health_check_connection_failure(self, mock_env_vars):
        """Test health check with connection failure"""
        with patch('app.services.polygon_anchor.Web3') as mock_web3_class:
            mock_w3 = Mock()
            mock_web3_class.return_value = mock_w3
            mock_w3.is_connected.return_value = False
            
            service = PolygonAnchorService()
            health = service.health_check()
            
            assert health["healthy"] is False
            assert "connection failed" in health["error"].lower()
    
    @patch('app.services.polygon_anchor.Account')
    def test_anchor_root_success(self, mock_account, mock_env_vars, mock_web3):
        """Test successful root anchoring"""
        mock_w3, mock_contract = mock_web3
        
        # Mock account
        mock_account_instance = Mock()
        mock_account_instance.address = "0x" + "1" * 40
        mock_account.from_key.return_value = mock_account_instance
        
        # Mock transaction building and signing
        mock_contract.functions.anchorRoot.return_value.build_transaction.return_value = {
            'from': mock_account_instance.address,
            'nonce': 5,
            'gas': 100000,
            'gasPrice': 20000000000,
            'chainId': 31337
        }
        
        mock_signed_tx = Mock()
        mock_signed_tx.rawTransaction = b"signed_tx_data"
        mock_account_instance.sign_transaction.return_value = mock_signed_tx
        
        # Mock transaction execution
        mock_tx_hash = "0x" + "a" * 64
        mock_w3.eth.send_raw_transaction.return_value = bytes.fromhex(mock_tx_hash[2:])
        
        # Mock receipt
        mock_receipt = Mock()
        mock_receipt.status = 1
        mock_receipt.transactionHash = bytes.fromhex(mock_tx_hash[2:])
        mock_receipt.blockNumber = 1001
        mock_receipt.gasUsed = 50000
        mock_receipt.logs = []
        mock_w3.eth.wait_for_transaction_receipt.return_value = mock_receipt
        
        service = PolygonAnchorService()
        result = service.anchor_root(TEST_ROOT)
        
        assert result["success"] is True
        assert result["tx_hash"] == mock_tx_hash
        assert result["block_number"] == 1001
        assert result["root"] == TEST_ROOT
    
    def test_anchor_root_invalid_format(self, mock_env_vars, mock_web3):
        """Test anchoring with invalid root format"""
        service = PolygonAnchorService()
        
        with pytest.raises(ValueError, match="Invalid root hash length"):
            service.anchor_root("0x1234")  # Too short
    
    def test_get_events_success(self, mock_env_vars, mock_web3):
        """Test successful event retrieval"""
        mock_w3, mock_contract = mock_web3
        
        # Mock event filter
        mock_event_filter = Mock()
        mock_event = Mock()
        mock_event.args.root = bytes.fromhex(TEST_ROOT[2:])
        mock_event.args.timestamp = 1609459200  # 2021-01-01
        mock_event.args.by = "0x" + "1" * 40
        mock_event.transactionHash = bytes.fromhex("a" * 64)
        mock_event.blockNumber = 1000
        mock_event.logIndex = 0
        
        mock_event_filter.get_all_entries.return_value = [mock_event]
        mock_contract.events.RootAnchored.create_filter.return_value = mock_event_filter
        
        service = PolygonAnchorService()
        events = service.get_events(limit=10)
        
        assert len(events) == 1
        assert events[0]["root"] == TEST_ROOT
        assert events[0]["timestamp"] == 1609459200
        assert events[0]["tx_hash"] == "0x" + "a" * 64


class TestAnchorAPI:
    """Test the anchor API endpoints"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)
    
    @pytest.fixture
    def mock_anchor_service(self):
        """Mock the anchor service"""
        with patch('app.api.v1.anchor.create_anchor_service') as mock_create:
            mock_service = Mock()
            mock_create.return_value = mock_service
            yield mock_service
    
    def test_anchor_root_endpoint_success(self, client, mock_anchor_service):
        """Test successful root anchoring via API"""
        # Mock service response
        mock_anchor_service.anchor_root.return_value = {
            "success": True,
            "tx_hash": "0x" + "a" * 64,
            "block_number": 1001,
            "gas_used": 50000,
            "root": TEST_ROOT,
            "timestamp": "2021-01-01T00:00:00",
            "anchored_by": "0x" + "1" * 40,
            "events": []
        }
        
        response = client.post(
            "/v1/anchor/root",
            json={"root": TEST_ROOT}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["tx_hash"] == "0x" + "a" * 64
        assert data["root"] == TEST_ROOT
    
    def test_anchor_root_endpoint_invalid_root(self, client, mock_anchor_service):
        """Test API with invalid root format"""
        response = client.post(
            "/v1/anchor/root",
            json={"root": "0x1234"}  # Too short
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_anchor_root_endpoint_service_error(self, client, mock_anchor_service):
        """Test API with service error"""
        mock_anchor_service.anchor_root.side_effect = PolygonAnchorError("Service error")
        
        response = client.post(
            "/v1/anchor/root",
            json={"root": TEST_ROOT}
        )
        
        assert response.status_code == 500
        assert "Anchoring failed" in response.json()["detail"]
    
    def test_get_events_endpoint_success(self, client, mock_anchor_service):
        """Test successful event retrieval via API"""
        mock_anchor_service.get_events.return_value = [
            {
                "root": TEST_ROOT,
                "timestamp": 1609459200,
                "anchored_by": "0x" + "1" * 40,
                "tx_hash": "0x" + "a" * 64,
                "block_number": 1000,
                "log_index": 0
            }
        ]
        
        response = client.get("/v1/anchor/events?limit=10")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["count"] == 1
        assert len(data["events"]) == 1
        assert data["events"][0]["root"] == TEST_ROOT
    
    def test_health_endpoint_success(self, client, mock_anchor_service):
        """Test successful health check via API"""
        mock_anchor_service.health_check.return_value = {
            "healthy": True,
            "contract_address": TEST_CONTRACT_ADDRESS,
            "contract_version": "1.0.0",
            "anchorer_address": "0x" + "1" * 40,
            "chain_id": 31337
        }
        
        response = client.get("/v1/anchor/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["healthy"] is True
        assert data["contract_address"] == TEST_CONTRACT_ADDRESS
    
    def test_health_endpoint_unhealthy(self, client, mock_anchor_service):
        """Test health check with unhealthy service"""
        mock_anchor_service.health_check.return_value = {
            "healthy": False,
            "error": "Connection failed"
        }
        
        response = client.get("/v1/anchor/health")
        
        assert response.status_code == 200  # Health endpoint should always return 200
        data = response.json()
        assert data["healthy"] is False
        assert "Connection failed" in data["error"]
    
    def test_contract_info_endpoint(self, client, mock_anchor_service):
        """Test contract info endpoint"""
        mock_anchor_service.health_check.return_value = {
            "healthy": True,
            "contract_address": TEST_CONTRACT_ADDRESS,
            "contract_version": "1.0.0",
            "contract_owner": "0x" + "1" * 40,
            "chain_id": 31337,
            "latest_block": 1000,
            "rpc_url": TEST_RPC_URL
        }
        
        response = client.get("/v1/anchor/contract/info")
        
        assert response.status_code == 200
        data = response.json()
        assert data["contract_address"] == TEST_CONTRACT_ADDRESS
        assert data["version"] == "1.0.0"
        assert data["chain_id"] == 31337
    
    def test_explorer_link_endpoint(self, client, mock_anchor_service):
        """Test explorer link generation"""
        mock_anchor_service.health_check.return_value = {
            "healthy": True,
            "chain_id": 1442  # Polygon zkEVM Testnet
        }
        
        test_tx_hash = "0x" + "a" * 64
        response = client.get(f"/v1/anchor/explorer/{test_tx_hash}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["tx_hash"] == test_tx_hash
        assert "testnet-zkevm.polygonscan.com" in data["explorer_url"]
        assert data["chain_id"] == 1442


class TestConvenienceFunctions:
    """Test convenience functions"""
    
    @patch('app.services.polygon_anchor.PolygonAnchorService')
    def test_create_anchor_service(self, mock_service_class):
        """Test anchor service creation"""
        from app.services.polygon_anchor import create_anchor_service
        
        service = create_anchor_service()
        
        mock_service_class.assert_called_once()
        assert service is not None
    
    @pytest.mark.asyncio
    @patch('app.services.polygon_anchor.create_anchor_service')
    async def test_anchor_merkle_root_convenience(self, mock_create_service):
        """Test convenience function for anchoring"""
        from app.services.polygon_anchor import anchor_merkle_root
        
        mock_service = Mock()
        mock_service.anchor_root.return_value = {"success": True}
        mock_create_service.return_value = mock_service
        
        result = await anchor_merkle_root(TEST_ROOT)
        
        assert result["success"] is True
        mock_service.anchor_root.assert_called_once_with(TEST_ROOT)
    
    @pytest.mark.asyncio
    @patch('app.services.polygon_anchor.create_anchor_service')
    async def test_get_anchor_events_convenience(self, mock_create_service):
        """Test convenience function for getting events"""
        from app.services.polygon_anchor import get_anchor_events
        
        mock_service = Mock()
        mock_service.get_events.return_value = [{"root": TEST_ROOT}]
        mock_create_service.return_value = mock_service
        
        events = await get_anchor_events(limit=10)
        
        assert len(events) == 1
        assert events[0]["root"] == TEST_ROOT
        mock_service.get_events.assert_called_once_with(limit=10)


@pytest.mark.integration
class TestHardhatIntegration:
    """Integration tests with Hardhat local node (optional)"""
    
    @pytest.fixture(autouse=True)
    def skip_if_no_hardhat(self):
        """Skip integration tests if Hardhat is not available"""
        try:
            import requests
            response = requests.get("http://127.0.0.1:8545", timeout=1)
            # If we get here, Hardhat node is running
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            pytest.skip("Hardhat node not available (run 'npx hardhat node' to enable integration tests)")
    
    def test_real_contract_deployment(self):
        """Test with real contract deployment (requires Hardhat node)"""
        # This test would deploy a real contract and test anchoring
        # Implementation depends on having Hardhat node running
        pytest.skip("Real contract testing requires manual setup")
    
    def test_real_anchoring_flow(self):
        """Test complete anchoring flow with real blockchain"""
        # This test would perform end-to-end anchoring
        # Implementation depends on deployed contract
        pytest.skip("Full integration testing requires manual setup")
