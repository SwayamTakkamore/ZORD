"""
ZK Proof API Endpoints

This module provides API endpoints for zero-knowledge proof operations
integrated with the compliance engine.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
import logging

from app.core.zk_client import (
    ZKProofClient, 
    ZKIntegrationService,
    generate_zk_compliance_proof,
    verify_zk_compliance_proof,
    check_zk_service_health
)
from app.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter()

# Response Models
class ZKProofGenerationResponse(BaseModel):
    success: bool
    proof_id: Optional[str] = None
    transaction_id: str
    compliance_decision: Optional[str] = None
    merkle_root: Optional[str] = None
    generated_at: Optional[str] = None
    zk_service_healthy: bool
    error: Optional[str] = None

class ZKProofVerificationResponse(BaseModel):
    success: bool
    proof_id: str
    is_valid: bool
    transaction_id: Optional[str] = None
    compliance_decision: Optional[str] = None
    circuit: Optional[str] = None
    version: Optional[str] = None
    verified_at: Optional[str] = None
    zk_service_healthy: bool
    error: Optional[str] = None

class ZKServiceHealthResponse(BaseModel):
    healthy: bool
    service: Optional[str] = None
    version: Optional[str] = None
    circuit: Optional[str] = None
    verification_key_loaded: Optional[bool] = None
    timestamp: str
    error: Optional[str] = None

class ZKProofListResponse(BaseModel):
    success: bool
    count: int
    proofs: list
    error: Optional[str] = None

# Request Models
class ZKProofGenerationRequest(BaseModel):
    transaction_data: Dict[str, Any] = Field(..., description="Transaction details")
    compliance_evidence: Dict[str, Any] = Field(..., description="Compliance checking results")
    merkle_proof: Dict[str, Any] = Field(..., description="Merkle proof for evidence inclusion")

class ZKProofVerificationRequest(BaseModel):
    proof_id: Optional[str] = Field(None, description="Proof ID to verify")
    proof: Optional[Dict[str, Any]] = Field(None, description="Proof object")
    public_signals: Optional[list] = Field(None, description="Public signals")


@router.get("/health", response_model=ZKServiceHealthResponse)
async def check_zk_service():
    """
    Check ZK proof service health and status
    
    Returns:
        ZK service health information including version and circuit details
    """
    try:
        health_info = await check_zk_service_health()
        
        return ZKServiceHealthResponse(
            healthy=health_info.get("healthy", False),
            service=health_info.get("service"),
            version=health_info.get("version"),
            circuit=health_info.get("circuit"),
            verification_key_loaded=health_info.get("verification_key_loaded"),
            timestamp=health_info.get("timestamp"),
            error=health_info.get("error")
        )
        
    except Exception as e:
        logger.error(f"ZK service health check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"ZK service health check failed: {str(e)}"
        )


@router.post("/prove", response_model=ZKProofGenerationResponse)
async def generate_proof(request: ZKProofGenerationRequest):
    """
    Generate a zero-knowledge proof for compliance verification
    
    Example request:
    ```json
    {
        "transaction_data": {
            "tx_uuid": "123e4567-e89b-12d3-a456-426614174000",
            "wallet_from": "0x742d35Cc6634C0532925a3b8D4d0C123456789AB",
            "wallet_to": "0x123d35Cc6634C0532925a3b8D4d0C123456789CD",
            "amount": "1000.5",
            "currency": "ETH",
            "kyc_proof_id": "kyc_12345"
        },
        "compliance_evidence": {
            "decision": "PASS",
            "risk_score": 10,
            "rules_evaluated": [
                {"rule_type": "BLACKLIST_CHECK", "passed": true},
                {"rule_type": "AMOUNT_THRESHOLD", "passed": true}
            ]
        },
        "merkle_proof": {
            "root_hash": "0x1234...",
            "path_indices": [0, 1, 0],
            "path_elements": ["0xabc...", "0xdef...", "0x123..."]
        }
    }
    ```
    
    Returns:
        ZK proof generation result with proof ID and metadata
    """
    try:
        # Extract transaction ID
        transaction_id = request.transaction_data.get("tx_uuid", "unknown")
        
        # Generate ZK proof
        result = await generate_zk_compliance_proof(
            request.transaction_data,
            request.compliance_evidence,
            request.merkle_proof.get("root_hash", ""),
            request.merkle_proof
        )
        
        return ZKProofGenerationResponse(
            success=result.get("success", False),
            proof_id=result.get("proof_id"),
            transaction_id=transaction_id,
            compliance_decision=result.get("compliance_decision"),
            merkle_root=result.get("merkle_root"),
            generated_at=result.get("generated_at"),
            zk_service_healthy=result.get("zk_service_healthy", False),
            error=result.get("error")
        )
        
    except Exception as e:
        logger.error(f"ZK proof generation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"ZK proof generation failed: {str(e)}"
        )


@router.post("/verify", response_model=ZKProofVerificationResponse)
async def verify_proof(request: ZKProofVerificationRequest):
    """
    Verify a zero-knowledge proof
    
    Example request (by proof ID):
    ```json
    {
        "proof_id": "abc123def456"
    }
    ```
    
    Example request (by proof data):
    ```json
    {
        "proof": {
            "pi_a": ["...", "...", "1"],
            "pi_b": [["...", "..."], ["...", "..."], ["1", "0"]],
            "pi_c": ["...", "...", "1"],
            "protocol": "groth16",
            "curve": "bn128"
        },
        "public_signals": ["123456...", "789012..."]
    }
    ```
    
    Returns:
        ZK proof verification result with validity status
    """
    try:
        if request.proof_id:
            # Verify by ID
            result = await verify_zk_compliance_proof(request.proof_id)
            
            return ZKProofVerificationResponse(
                success=result.get("success", False),
                proof_id=request.proof_id,
                is_valid=result.get("is_valid", False),
                transaction_id=result.get("transaction_id"),
                compliance_decision=result.get("compliance_decision"),
                circuit=result.get("circuit"),
                version=result.get("version"),
                verified_at=result.get("verified_at"),
                zk_service_healthy=result.get("zk_service_healthy", False),
                error=result.get("error")
            )
            
        elif request.proof and request.public_signals:
            # Verify by proof data
            async with ZKProofClient() as client:
                result = await client.verify_proof(
                    proof=request.proof,
                    public_signals=request.public_signals
                )
                
                verification_result = result.get("verification_result", {})
                
                return ZKProofVerificationResponse(
                    success=True,
                    proof_id="inline",
                    is_valid=verification_result.get("isValid", False),
                    verified_at=result.get("verified_at"),
                    zk_service_healthy=True
                )
                
        else:
            raise HTTPException(
                status_code=400,
                detail="Must provide either proof_id OR (proof AND public_signals)"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"ZK proof verification failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"ZK proof verification failed: {str(e)}"
        )


@router.get("/proofs", response_model=ZKProofListResponse)
async def list_proofs():
    """
    List all generated ZK proofs
    
    Returns:
        List of all ZK proofs with metadata
    """
    try:
        async with ZKProofClient() as client:
            result = await client.list_proofs()
            
            return ZKProofListResponse(
                success=result.get("success", False),
                count=result.get("count", 0),
                proofs=result.get("proofs", [])
            )
            
    except Exception as e:
        logger.error(f"Failed to list ZK proofs: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list ZK proofs: {str(e)}"
        )


@router.get("/proofs/{proof_id}")
async def get_proof(proof_id: str):
    """
    Get specific ZK proof by ID
    
    Args:
        proof_id: The proof identifier
        
    Returns:
        ZK proof details and verification status
    """
    try:
        async with ZKProofClient() as client:
            result = await client.get_proof(proof_id)
            return result
            
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=404,
                detail=f"ZK proof not found: {proof_id}"
            )
        else:
            logger.error(f"Failed to get ZK proof {proof_id}: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get ZK proof: {str(e)}"
            )


@router.delete("/proofs/{proof_id}")
async def delete_proof(proof_id: str):
    """
    Delete specific ZK proof by ID
    
    Args:
        proof_id: The proof identifier
        
    Returns:
        Deletion confirmation
    """
    try:
        async with ZKProofClient() as client:
            result = await client.delete_proof(proof_id)
            return result
            
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=404,
                detail=f"ZK proof not found: {proof_id}"
            )
        else:
            logger.error(f"Failed to delete ZK proof {proof_id}: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to delete ZK proof: {str(e)}"
            )


@router.get("/integration/compliance/{transaction_id}")
async def get_compliance_proof_for_transaction(
    transaction_id: str,
    db: Session = Depends(get_db)
):
    """
    Get ZK compliance proof for a specific transaction
    
    This endpoint links transaction records with their ZK proofs
    and provides a complete compliance audit trail.
    
    Args:
        transaction_id: Transaction UUID
        
    Returns:
        Complete compliance information including ZK proof
    """
    try:
        # This would typically query the database for transaction details
        # and associated proof information. For now, we'll demonstrate
        # the structure that would be returned.
        
        return {
            "transaction_id": transaction_id,
            "compliance_status": "Compliance proof integration would be implemented here",
            "note": "This endpoint demonstrates the structure for full integration",
            "features": [
                "Link transactions to ZK proofs",
                "Provide complete audit trail",
                "Verify compliance with privacy",
                "Generate compliance reports"
            ]
        }
        
    except Exception as e:
        logger.error(f"Failed to get compliance proof for transaction {transaction_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get compliance proof: {str(e)}"
        )
