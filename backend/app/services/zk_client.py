"""
ZK Proof Service Client

This module provides a client for communicating with the ZK proof service
to generate and verify zero-knowledge proofs for compliance verification.
"""

import aiohttp
import asyncio
import logging
from typing import Dict, Any, Optional, List
import json

logger = logging.getLogger(__name__)

class ZKProofClient:
    """Client for ZK Proof Service"""
    
    def __init__(self, base_url: str = "http://localhost:3001"):
        self.base_url = base_url.rstrip('/')
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
        """Ensure session is available"""
        if not self.session:
            self.session = aiohttp.ClientSession()
    
    async def health_check(self) -> Dict[str, Any]:
        """Check if ZK service is healthy"""
        try:
            await self._ensure_session()
            async with self.session.get(f"{self.base_url}/health") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise Exception(f"Health check failed: {response.status}")
        except Exception as e:
            logger.error(f"ZK service health check failed: {e}")
            raise
    
    async def get_service_info(self) -> Dict[str, Any]:
        """Get ZK service information"""
        try:
            await self._ensure_session()
            async with self.session.get(f"{self.base_url}/info") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise Exception(f"Failed to get service info: {response.status}")
        except Exception as e:
            logger.error(f"Failed to get ZK service info: {e}")
            raise
    
    async def generate_compliance_proof(
        self, 
        transaction_data: Dict[str, Any],
        compliance_evidence: Dict[str, Any],
        merkle_proof: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate a ZK proof for compliance verification
        
        Args:
            transaction_data: Transaction details
            compliance_evidence: Compliance checking results
            merkle_proof: Merkle proof for evidence inclusion
            
        Returns:
            Dictionary containing proof ID, proof, and public signals
        """
        try:
            await self._ensure_session()
            
            payload = {
                "transactionData": transaction_data,
                "complianceEvidence": compliance_evidence,
                "merkleProof": merkle_proof
            }
            
            logger.info(f"Generating ZK proof for transaction: {transaction_data.get('tx_uuid', 'unknown')}")
            
            async with self.session.post(
                f"{self.base_url}/prove/compliance",
                json=payload,
                headers={'Content-Type': 'application/json'}
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"ZK proof generated successfully: {result.get('proof_id')}")
                    return result
                else:
                    error_text = await response.text()
                    logger.error(f"ZK proof generation failed: {response.status} - {error_text}")
                    raise Exception(f"Proof generation failed: {response.status} - {error_text}")
                    
        except Exception as e:
            logger.error(f"ZK proof generation error: {e}")
            raise
    
    async def verify_proof(
        self, 
        proof: Optional[Dict[str, Any]] = None,
        public_signals: Optional[List[str]] = None,
        proof_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Verify a ZK proof
        
        Args:
            proof: The proof object (optional if proof_id provided)
            public_signals: Public signals (optional if proof_id provided)
            proof_id: Proof ID to verify (optional if proof and public_signals provided)
            
        Returns:
            Dictionary containing verification result
        """
        try:
            await self._ensure_session()
            
            if proof_id:
                payload = {"proofId": proof_id}
            elif proof and public_signals:
                payload = {
                    "proof": proof,
                    "publicSignals": public_signals
                }
            else:
                raise ValueError("Either proof_id OR (proof AND public_signals) must be provided")
            
            logger.info(f"Verifying ZK proof: {proof_id or 'direct verification'}")
            
            async with self.session.post(
                f"{self.base_url}/verify",
                json=payload,
                headers={'Content-Type': 'application/json'}
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"ZK proof verification completed: {result.get('verification_result', {}).get('isValid')}")
                    return result
                else:
                    error_text = await response.text()
                    logger.error(f"ZK proof verification failed: {response.status} - {error_text}")
                    raise Exception(f"Proof verification failed: {response.status} - {error_text}")
                    
        except Exception as e:
            logger.error(f"ZK proof verification error: {e}")
            raise
    
    async def list_proofs(self) -> Dict[str, Any]:
        """List all generated proofs"""
        try:
            await self._ensure_session()
            async with self.session.get(f"{self.base_url}/proofs") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    raise Exception(f"Failed to list proofs: {response.status} - {error_text}")
        except Exception as e:
            logger.error(f"Failed to list ZK proofs: {e}")
            raise
    
    async def get_proof(self, proof_id: str) -> Dict[str, Any]:
        """Get specific proof by ID"""
        try:
            await self._ensure_session()
            async with self.session.get(f"{self.base_url}/proofs/{proof_id}") as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 404:
                    raise Exception(f"Proof not found: {proof_id}")
                else:
                    error_text = await response.text()
                    raise Exception(f"Failed to get proof: {response.status} - {error_text}")
        except Exception as e:
            logger.error(f"Failed to get ZK proof {proof_id}: {e}")
            raise
    
    async def delete_proof(self, proof_id: str) -> Dict[str, Any]:
        """Delete specific proof by ID"""
        try:
            await self._ensure_session()
            async with self.session.delete(f"{self.base_url}/proofs/{proof_id}") as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"ZK proof deleted: {proof_id}")
                    return result
                elif response.status == 404:
                    raise Exception(f"Proof not found: {proof_id}")
                else:
                    error_text = await response.text()
                    raise Exception(f"Failed to delete proof: {response.status} - {error_text}")
        except Exception as e:
            logger.error(f"Failed to delete ZK proof {proof_id}: {e}")
            raise

# Convenience function for generating compliance proofs
async def generate_transaction_compliance_proof(
    transaction_data: Dict[str, Any],
    compliance_evidence: Dict[str, Any],
    merkle_proof: Dict[str, Any],
    zk_service_url: str = "http://localhost:3001"
) -> Dict[str, Any]:
    """
    Convenience function to generate a compliance proof for a transaction
    
    Args:
        transaction_data: Transaction details
        compliance_evidence: Compliance checking results
        merkle_proof: Merkle proof for evidence inclusion
        zk_service_url: ZK service URL
        
    Returns:
        Dictionary containing proof details
    """
    async with ZKProofClient(zk_service_url) as client:
        return await client.generate_compliance_proof(
            transaction_data,
            compliance_evidence,
            merkle_proof
        )

# Convenience function for verifying proofs
async def verify_transaction_compliance_proof(
    proof_id: str,
    zk_service_url: str = "http://localhost:3001"
) -> Dict[str, Any]:
    """
    Convenience function to verify a compliance proof by ID
    
    Args:
        proof_id: Proof identifier
        zk_service_url: ZK service URL
        
    Returns:
        Dictionary containing verification result
    """
    async with ZKProofClient(zk_service_url) as client:
        return await client.verify_proof(proof_id=proof_id)
