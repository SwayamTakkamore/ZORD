"""
ZK Proof Client for Backend Integration

This module provides a client to interact with the ZK proof service
for generating and verifying zero-knowledge proofs of compliance.
"""

import aiohttp
import asyncio
import json
import logging
from typing import Dict, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class ZKProofClient:
    """Client for interacting with ZK proof service"""
    
    def __init__(self, zk_service_url: str = "http://localhost:3001"):
        self.base_url = zk_service_url.rstrip('/')
        self.session = None
        
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
            
    async def _ensure_session(self):
        """Ensure we have an active session"""
        if not self.session:
            self.session = aiohttp.ClientSession()
            
    async def health_check(self) -> Dict:
        """Check if ZK service is healthy"""
        await self._ensure_session()
        
        try:
            async with self.session.get(f"{self.base_url}/health") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise Exception(f"ZK service health check failed: {response.status}")
                    
        except Exception as e:
            logger.error(f"ZK service health check error: {e}")
            raise
            
    async def get_service_info(self) -> Dict:
        """Get ZK service information"""
        await self._ensure_session()
        
        try:
            async with self.session.get(f"{self.base_url}/info") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise Exception(f"Failed to get ZK service info: {response.status}")
                    
        except Exception as e:
            logger.error(f"ZK service info error: {e}")
            raise
            
    async def generate_compliance_proof(
        self,
        transaction_data: Dict,
        compliance_evidence: Dict,
        merkle_proof: Dict
    ) -> Dict:
        """
        Generate a ZK proof for compliance verification
        
        Args:
            transaction_data: Transaction details
            compliance_evidence: Compliance checking results
            merkle_proof: Merkle proof for evidence inclusion
            
        Returns:
            Dict containing proof ID, proof, and public signals
        """
        await self._ensure_session()
        
        request_data = {
            "transactionData": transaction_data,
            "complianceEvidence": compliance_evidence,
            "merkleProof": merkle_proof
        }
        
        try:
            logger.info(f"Generating ZK proof for transaction {transaction_data.get('tx_uuid', 'unknown')}")
            
            async with self.session.post(
                f"{self.base_url}/prove/compliance",
                json=request_data,
                headers={"Content-Type": "application/json"}
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"ZK proof generated successfully: {result.get('proof_id')}")
                    return result
                else:
                    error_text = await response.text()
                    logger.error(f"ZK proof generation failed: {response.status} - {error_text}")
                    raise Exception(f"ZK proof generation failed: {response.status}")
                    
        except Exception as e:
            logger.error(f"ZK proof generation error: {e}")
            raise
            
    async def verify_proof(
        self,
        proof: Optional[Dict] = None,
        public_signals: Optional[list] = None,
        proof_id: Optional[str] = None
    ) -> Dict:
        """
        Verify a ZK proof
        
        Args:
            proof: The proof object (optional if proof_id provided)
            public_signals: Public signals (optional if proof_id provided)
            proof_id: Proof ID to verify (optional if proof/public_signals provided)
            
        Returns:
            Dict containing verification result
        """
        await self._ensure_session()
        
        request_data = {}
        if proof_id:
            request_data["proofId"] = proof_id
        elif proof and public_signals:
            request_data["proof"] = proof
            request_data["publicSignals"] = public_signals
        else:
            raise ValueError("Must provide either proof_id OR (proof AND public_signals)")
            
        try:
            logger.info(f"Verifying ZK proof: {proof_id or 'inline proof'}")
            
            async with self.session.post(
                f"{self.base_url}/verify",
                json=request_data,
                headers={"Content-Type": "application/json"}
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    is_valid = result.get("verification_result", {}).get("isValid", False)
                    logger.info(f"ZK proof verification result: {'VALID' if is_valid else 'INVALID'}")
                    return result
                else:
                    error_text = await response.text()
                    logger.error(f"ZK proof verification failed: {response.status} - {error_text}")
                    raise Exception(f"ZK proof verification failed: {response.status}")
                    
        except Exception as e:
            logger.error(f"ZK proof verification error: {e}")
            raise
            
    async def list_proofs(self) -> Dict:
        """List all generated proofs"""
        await self._ensure_session()
        
        try:
            async with self.session.get(f"{self.base_url}/proofs") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise Exception(f"Failed to list proofs: {response.status}")
                    
        except Exception as e:
            logger.error(f"List proofs error: {e}")
            raise
            
    async def get_proof(self, proof_id: str) -> Dict:
        """Get specific proof by ID"""
        await self._ensure_session()
        
        try:
            async with self.session.get(f"{self.base_url}/proofs/{proof_id}") as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 404:
                    raise Exception(f"Proof not found: {proof_id}")
                else:
                    raise Exception(f"Failed to get proof: {response.status}")
                    
        except Exception as e:
            logger.error(f"Get proof error: {e}")
            raise
            
    async def delete_proof(self, proof_id: str) -> Dict:
        """Delete specific proof by ID"""
        await self._ensure_session()
        
        try:
            async with self.session.delete(f"{self.base_url}/proofs/{proof_id}") as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"ZK proof deleted: {proof_id}")
                    return result
                elif response.status == 404:
                    raise Exception(f"Proof not found: {proof_id}")
                else:
                    raise Exception(f"Failed to delete proof: {response.status}")
                    
        except Exception as e:
            logger.error(f"Delete proof error: {e}")
            raise


class ZKIntegrationService:
    """Service for integrating ZK proofs with compliance engine"""
    
    def __init__(self, zk_client: ZKProofClient):
        self.zk_client = zk_client
        
    async def generate_compliance_proof_from_transaction(
        self,
        transaction_id: str,
        transaction_data: Dict,
        compliance_result: Dict,
        merkle_tree_root: str,
        merkle_proof: Dict
    ) -> Dict:
        """
        Generate a complete compliance proof from transaction processing
        
        Args:
            transaction_id: Transaction UUID
            transaction_data: Original transaction data
            compliance_result: Result from compliance engine
            merkle_tree_root: Merkle tree root hash
            merkle_proof: Merkle proof for evidence inclusion
            
        Returns:
            Dict containing proof details and metadata
        """
        try:
            # Prepare compliance evidence
            compliance_evidence = {
                "decision": compliance_result.get("decision"),
                "risk_score": compliance_result.get("risk_score", 0),
                "rules_evaluated": compliance_result.get("evidence", []),
                "timestamp": datetime.utcnow().isoformat(),
                "transaction_id": transaction_id
            }
            
            # Prepare merkle proof with root
            merkle_proof_data = {
                "root_hash": merkle_tree_root,
                "path_indices": merkle_proof.get("path_indices", []),
                "path_elements": merkle_proof.get("path_elements", [])
            }
            
            # Generate ZK proof
            proof_result = await self.zk_client.generate_compliance_proof(
                transaction_data,
                compliance_evidence,
                merkle_proof_data
            )
            
            return {
                "success": True,
                "proof_id": proof_result.get("proof_id"),
                "proof": proof_result.get("proof"),
                "public_signals": proof_result.get("public_signals"),
                "transaction_id": transaction_id,
                "compliance_decision": compliance_result.get("decision"),
                "merkle_root": merkle_tree_root,
                "generated_at": proof_result.get("timestamp"),
                "zk_service_healthy": True
            }
            
        except Exception as e:
            logger.error(f"Failed to generate compliance proof for {transaction_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "transaction_id": transaction_id,
                "zk_service_healthy": False
            }
            
    async def verify_compliance_proof(self, proof_id: str) -> Dict:
        """
        Verify a compliance proof and return detailed results
        
        Args:
            proof_id: ID of the proof to verify
            
        Returns:
            Dict containing verification results and metadata
        """
        try:
            verification_result = await self.zk_client.verify_proof(proof_id=proof_id)
            
            result = verification_result.get("verification_result", {})
            
            return {
                "success": True,
                "proof_id": proof_id,
                "is_valid": result.get("isValid", False),
                "transaction_id": result.get("transactionId"),
                "compliance_decision": result.get("complianceDecision"),
                "circuit": result.get("circuit"),
                "version": result.get("version"),
                "verified_at": verification_result.get("verified_at"),
                "zk_service_healthy": True
            }
            
        except Exception as e:
            logger.error(f"Failed to verify compliance proof {proof_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "proof_id": proof_id,
                "is_valid": False,
                "zk_service_healthy": False
            }


# Convenience functions for easy integration

async def generate_zk_compliance_proof(
    transaction_data: Dict,
    compliance_result: Dict,
    merkle_tree_root: str,
    merkle_proof: Dict,
    zk_service_url: str = "http://localhost:3001"
) -> Dict:
    """
    Convenience function to generate a ZK compliance proof
    
    Args:
        transaction_data: Transaction details
        compliance_result: Compliance engine result
        merkle_tree_root: Merkle tree root hash
        merkle_proof: Merkle proof for evidence inclusion
        zk_service_url: URL of ZK service
        
    Returns:
        Dict containing proof generation result
    """
    async with ZKProofClient(zk_service_url) as client:
        integration_service = ZKIntegrationService(client)
        return await integration_service.generate_compliance_proof_from_transaction(
            transaction_data.get("tx_uuid", "unknown"),
            transaction_data,
            compliance_result,
            merkle_tree_root,
            merkle_proof
        )


async def verify_zk_compliance_proof(
    proof_id: str,
    zk_service_url: str = "http://localhost:3001"
) -> Dict:
    """
    Convenience function to verify a ZK compliance proof
    
    Args:
        proof_id: ID of the proof to verify
        zk_service_url: URL of ZK service
        
    Returns:
        Dict containing verification result
    """
    async with ZKProofClient(zk_service_url) as client:
        integration_service = ZKIntegrationService(client)
        return await integration_service.verify_compliance_proof(proof_id)


async def check_zk_service_health(zk_service_url: str = "http://localhost:3001") -> Dict:
    """
    Convenience function to check ZK service health
    
    Args:
        zk_service_url: URL of ZK service
        
    Returns:
        Dict containing health status
    """
    try:
        async with ZKProofClient(zk_service_url) as client:
            health = await client.health_check()
            info = await client.get_service_info()
            
            return {
                "healthy": True,
                "service": health.get("service"),
                "version": health.get("version"),
                "circuit": info.get("circuit"),
                "verification_key_loaded": info.get("verification_key_loaded"),
                "timestamp": health.get("timestamp")
            }
    except Exception as e:
        return {
            "healthy": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }
