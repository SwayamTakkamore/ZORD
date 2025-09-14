"""
Polygon Anchor Service

This module provides functionality to anchor Merkle roots to the Polygon zkEVM blockchain
using the ComplianceAnchor smart contract. It handles contract interaction, event parsing,
and provides retry logic for reliable operation.
"""

import os
import json
import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from web3 import Web3, HTTPProvider
from web3.contract import Contract
from eth_account import Account
from eth_typing import HexStr
import time

logger = logging.getLogger(__name__)

class PolygonAnchorError(Exception):
    """Custom exception for Polygon anchor operations"""
    pass

class PolygonAnchorService:
    """Service for anchoring compliance evidence to Polygon zkEVM blockchain"""
    
    def __init__(
        self,
        rpc_url: Optional[str] = None,
        private_key: Optional[str] = None,
        contract_address: Optional[str] = None
    ):
        """
        Initialize the Polygon anchor service
        
        Args:
            rpc_url: Polygon zkEVM RPC URL (defaults to env var)
            private_key: Private key for signing transactions (defaults to env var)
            contract_address: ComplianceAnchor contract address (defaults to env var)
        """
        self.rpc_url = rpc_url or os.getenv("POLYGON_RPC_URL", "http://127.0.0.1:8545")
        self.private_key = private_key or os.getenv("ANCHORER_PRIVATE_KEY")
        self.contract_address = contract_address or os.getenv("CONTRACT_ADDRESS")
        
        if not self.private_key:
            raise PolygonAnchorError("ANCHORER_PRIVATE_KEY environment variable required")
            
        if not self.contract_address:
            raise PolygonAnchorError("CONTRACT_ADDRESS environment variable required")
        
        # Initialize Web3
        self.w3 = Web3(HTTPProvider(self.rpc_url))
        
        # Check connection
        if not self.w3.is_connected():
            logger.warning(f"Failed to connect to {self.rpc_url}, will retry on demand")
        
        # Initialize account
        self.account = Account.from_key(self.private_key)
        logger.info(f"Initialized anchor service with account: {self.account.address}")
        
        # Contract ABI (minimal for our needs)
        self.contract_abi = [
            {
                "inputs": [{"internalType": "bytes32", "name": "root", "type": "bytes32"}],
                "name": "anchorRoot",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [],
                "name": "owner",
                "outputs": [{"internalType": "address", "name": "", "type": "address"}],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [],
                "name": "version",
                "outputs": [{"internalType": "string", "name": "", "type": "string"}],
                "stateMutability": "pure",
                "type": "function"
            },
            {
                "anonymous": False,
                "inputs": [
                    {"indexed": True, "internalType": "bytes32", "name": "root", "type": "bytes32"},
                    {"indexed": False, "internalType": "uint256", "name": "timestamp", "type": "uint256"},
                    {"indexed": True, "internalType": "address", "name": "by", "type": "address"}
                ],
                "name": "RootAnchored",
                "type": "event"
            }
        ]
        
        self._contract = None
        
    def get_contract(self) -> Contract:
        """
        Get the contract instance with retry logic
        
        Returns:
            Web3 contract instance
            
        Raises:
            PolygonAnchorError: If contract cannot be loaded
        """
        if self._contract is None:
            try:
                if not self.w3.is_connected():
                    # Try to reconnect
                    self.w3 = Web3(HTTPProvider(self.rpc_url))
                    if not self.w3.is_connected():
                        raise PolygonAnchorError(f"Cannot connect to {self.rpc_url}")
                
                self._contract = self.w3.eth.contract(
                    address=self.contract_address,
                    abi=self.contract_abi
                )
                
                # Test contract by calling version
                try:
                    version = self._contract.functions.version().call()
                    logger.info(f"Connected to ComplianceAnchor contract v{version}")
                except Exception as e:
                    logger.warning(f"Contract version check failed: {e}")
                    
            except Exception as e:
                raise PolygonAnchorError(f"Failed to load contract: {e}")
                
        return self._contract
    
    def _ensure_hex_format(self, root: str) -> str:
        """
        Ensure root is in proper hex format
        
        Args:
            root: Root hash as string
            
        Returns:
            Properly formatted hex string
        """
        if not root.startswith("0x"):
            root = "0x" + root
            
        if len(root) != 66:  # 0x + 64 hex chars
            raise ValueError(f"Invalid root hash length: {len(root)}, expected 66")
            
        return root
    
    def anchor_root(self, root_hex: str, max_retries: int = 3) -> Dict[str, Any]:
        """
        Anchor a Merkle root to the blockchain
        
        Args:
            root_hex: Merkle root hash (with or without 0x prefix)
            max_retries: Maximum number of retry attempts
            
        Returns:
            Dict containing transaction details and event information
            
        Raises:
            PolygonAnchorError: If anchoring fails after retries
        """
        root_hex = self._ensure_hex_format(root_hex)
        logger.info(f"Anchoring root: {root_hex}")
        
        for attempt in range(max_retries + 1):
            try:
                contract = self.get_contract()
                
                # Get current nonce
                nonce = self.w3.eth.get_transaction_count(self.account.address)
                
                # Build transaction
                tx_data = contract.functions.anchorRoot(root_hex).build_transaction({
                    'from': self.account.address,
                    'nonce': nonce,
                    'gas': 100000,  # Conservative gas limit
                    'gasPrice': self.w3.eth.gas_price,
                    'chainId': self.w3.eth.chain_id
                })
                
                # Sign transaction
                signed_tx = self.account.sign_transaction(tx_data)
                
                # Send transaction
                tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
                logger.info(f"Transaction sent: {tx_hash.hex()}")
                
                # Wait for receipt
                receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
                
                if receipt.status != 1:
                    raise PolygonAnchorError(f"Transaction failed: {tx_hash.hex()}")
                
                # Parse events
                events = self._parse_events(contract, receipt)
                
                result = {
                    "success": True,
                    "tx_hash": receipt.transactionHash.hex(),
                    "block_number": receipt.blockNumber,
                    "gas_used": receipt.gasUsed,
                    "root": root_hex,
                    "timestamp": datetime.utcnow().isoformat(),
                    "anchored_by": self.account.address,
                    "events": events
                }
                
                logger.info(f"Root anchored successfully: {tx_hash.hex()}")
                return result
                
            except Exception as e:
                logger.warning(f"Anchor attempt {attempt + 1} failed: {e}")
                
                if attempt < max_retries:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                    self._contract = None  # Force contract reload
                else:
                    raise PolygonAnchorError(f"Failed to anchor root after {max_retries + 1} attempts: {e}")
    
    def get_events(
        self,
        from_block: Optional[int] = None,
        to_block: str = "latest",
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Fetch RootAnchored events from the blockchain
        
        Args:
            from_block: Starting block number (None for earliest)
            to_block: Ending block ("latest" for current)
            limit: Maximum number of events to return
            
        Returns:
            List of event dictionaries
            
        Raises:
            PolygonAnchorError: If event fetching fails
        """
        try:
            contract = self.get_contract()
            
            # Set default from_block if not provided
            if from_block is None:
                current_block = self.w3.eth.block_number
                from_block = max(0, current_block - 10000)  # Last 10k blocks
            
            logger.info(f"Fetching events from block {from_block} to {to_block}")
            
            # Get events
            event_filter = contract.events.RootAnchored.create_filter(
                fromBlock=from_block,
                toBlock=to_block
            )
            
            events = event_filter.get_all_entries()
            
            # Process and format events
            formatted_events = []
            for event in events[-limit:]:  # Take last N events
                formatted_event = {
                    "root": event.args.root.hex(),
                    "timestamp": event.args.timestamp,
                    "anchored_by": event.args.by,
                    "tx_hash": event.transactionHash.hex(),
                    "block_number": event.blockNumber,
                    "log_index": event.logIndex
                }
                formatted_events.append(formatted_event)
            
            logger.info(f"Retrieved {len(formatted_events)} events")
            return formatted_events
            
        except Exception as e:
            raise PolygonAnchorError(f"Failed to fetch events: {e}")
    
    def _parse_events(self, contract: Contract, receipt) -> List[Dict[str, Any]]:
        """
        Parse events from transaction receipt
        
        Args:
            contract: Contract instance
            receipt: Transaction receipt
            
        Returns:
            List of parsed events
        """
        events = []
        
        for log in receipt.logs:
            try:
                decoded_log = contract.events.RootAnchored().processLog(log)
                event_data = {
                    "event": "RootAnchored",
                    "root": decoded_log.args.root.hex(),
                    "timestamp": decoded_log.args.timestamp,
                    "anchored_by": decoded_log.args.by,
                    "block_number": decoded_log.blockNumber,
                    "log_index": decoded_log.logIndex
                }
                events.append(event_data)
            except Exception:
                # Skip logs that don't match our event
                continue
                
        return events
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check service health and connectivity
        
        Returns:
            Health status dictionary
        """
        try:
            # Check Web3 connection
            if not self.w3.is_connected():
                return {
                    "healthy": False,
                    "error": "Web3 connection failed",
                    "rpc_url": self.rpc_url
                }
            
            # Check contract
            contract = self.get_contract()
            
            # Test contract call
            version = contract.functions.version().call()
            owner = contract.functions.owner().call()
            
            # Check account balance
            balance = self.w3.eth.get_balance(self.account.address)
            balance_eth = self.w3.from_wei(balance, 'ether')
            
            return {
                "healthy": True,
                "rpc_url": self.rpc_url,
                "contract_address": self.contract_address,
                "contract_version": version,
                "contract_owner": owner,
                "anchorer_address": self.account.address,
                "anchorer_balance_eth": str(balance_eth),
                "chain_id": self.w3.eth.chain_id,
                "latest_block": self.w3.eth.block_number
            }
            
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e),
                "rpc_url": self.rpc_url
            }


# Convenience functions for easy integration

def create_anchor_service() -> PolygonAnchorService:
    """
    Create anchor service with environment configuration
    
    Returns:
        Configured PolygonAnchorService instance
    """
    return PolygonAnchorService()

async def anchor_merkle_root(root_hex: str) -> Dict[str, Any]:
    """
    Convenience function to anchor a Merkle root
    
    Args:
        root_hex: Merkle root hash
        
    Returns:
        Anchoring result
    """
    service = create_anchor_service()
    return service.anchor_root(root_hex)

async def get_anchor_events(limit: int = 50) -> List[Dict[str, Any]]:
    """
    Convenience function to get recent anchor events
    
    Args:
        limit: Maximum number of events to return
        
    Returns:
        List of anchor events
    """
    service = create_anchor_service()
    return service.get_events(limit=limit)

# CLI interface for testing
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python polygon_anchor.py <command> [args]")
        print("Commands:")
        print("  health - Check service health")
        print("  anchor_root --root <root_hex> - Anchor a root")
        print("  get_events [--limit <n>] - Get recent events")
        sys.exit(1)
    
    command = sys.argv[1]
    service = create_anchor_service()
    
    if command == "health":
        health = service.health_check()
        print(json.dumps(health, indent=2))
        
    elif command == "anchor_root":
        if "--root" not in sys.argv:
            print("Error: --root argument required")
            sys.exit(1)
        
        root_index = sys.argv.index("--root") + 1
        if root_index >= len(sys.argv):
            print("Error: --root requires a value")
            sys.exit(1)
            
        root = sys.argv[root_index]
        result = service.anchor_root(root)
        print(json.dumps(result, indent=2))
        
    elif command == "get_events":
        limit = 50
        if "--limit" in sys.argv:
            limit_index = sys.argv.index("--limit") + 1
            if limit_index < len(sys.argv):
                limit = int(sys.argv[limit_index])
        
        events = service.get_events(limit=limit)
        print(json.dumps(events, indent=2))
        
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
