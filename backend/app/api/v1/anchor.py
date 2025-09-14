"""
Anchor API Endpoints with MongoDB support

This module provides FastAPI endpoints for anchoring Merkle roots to blockchain
and retrieving anchor events. Integrates with the PolygonAnchorService.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
import logging
from datetime import datetime

from app.services.polygon_anchor import (
    PolygonAnchorService,
    PolygonAnchorError,
    create_anchor_service
)
from app.services.transaction_crud import transaction_crud

logger = logging.getLogger(__name__)

router = APIRouter()

# Request Models
class AnchorRootRequest(BaseModel):
    root: str = Field(..., description="Merkle root hash (with or without 0x prefix)")
    
    @validator('root')
    def validate_root(cls, v):
        """Validate root hash format"""
        if not v:
            raise ValueError("Root cannot be empty")
        
        # Remove 0x prefix for validation
        clean_root = v[2:] if v.startswith('0x') else v
        
        if len(clean_root) != 64:
            raise ValueError("Root must be 64 hex characters (32 bytes)")
            
        try:
            int(clean_root, 16)
        except ValueError:
            raise ValueError("Root must be valid hex string")
            
        return v

# Response Models
class AnchorRootResponse(BaseModel):
    success: bool
    tx_hash: Optional[str] = None
    block_number: Optional[int] = None
    gas_used: Optional[int] = None
    root: Optional[str] = None
    timestamp: Optional[str] = None
    anchored_by: Optional[str] = None
    events: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None

class AnchorEvent(BaseModel):
    root: str
    timestamp: int
    anchored_by: str
    tx_hash: str
    block_number: int
    log_index: int

class AnchorEventsResponse(BaseModel):
    success: bool
    count: int
    events: List[AnchorEvent]
    from_block: Optional[int] = None
    to_block: Optional[str] = None
    error: Optional[str] = None

class AnchorHealthResponse(BaseModel):
    healthy: bool
    rpc_url: Optional[str] = None
    contract_address: Optional[str] = None
    contract_version: Optional[str] = None
    contract_owner: Optional[str] = None
    anchorer_address: Optional[str] = None
    anchorer_balance_eth: Optional[str] = None
    chain_id: Optional[int] = None
    latest_block: Optional[int] = None
    error: Optional[str] = None


@router.post("/root", response_model=AnchorRootResponse)
async def anchor_root(request: AnchorRootRequest):
    """
    Anchor a Merkle root to the blockchain
    
    This endpoint takes a Merkle root hash and anchors it to the ComplianceAnchor
    smart contract on Polygon zkEVM. The anchoring creates an immutable record
    with timestamp and anchorer information.
    
    Example request:
    ```json
    {
        "root": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
    }
    ```
    
    Returns:
        Anchoring result with transaction details and events
    """
    try:
        logger.info(f"Anchoring root: {request.root}")
        
        # Create anchor service
        anchor_service = create_anchor_service()
        
        # Anchor the root
        result = anchor_service.anchor_root(request.root)
        
        # Convert to response model
        response = AnchorRootResponse(
            success=result.get("success", False),
            tx_hash=result.get("tx_hash"),
            block_number=result.get("block_number"),
            gas_used=result.get("gas_used"),
            root=result.get("root"),
            timestamp=result.get("timestamp"),
            anchored_by=result.get("anchored_by"),
            events=result.get("events", [])
        )
        
        logger.info(f"Root anchored successfully: {response.tx_hash}")
        return response
        
    except PolygonAnchorError as e:
        logger.error(f"Anchor service error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Anchoring failed: {str(e)}"
        )
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid input: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error during anchoring: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/events", response_model=AnchorEventsResponse)
async def get_anchor_events(
    limit: int = Query(50, ge=1, le=1000, description="Maximum number of events to return"),
    from_block: Optional[int] = Query(None, description="Starting block number"),
    to_block: Optional[str] = Query("latest", description="Ending block number or 'latest'")
):
    """
    Get recent anchor events from the blockchain
    
    This endpoint fetches RootAnchored events from the ComplianceAnchor contract,
    providing a history of all Merkle roots that have been anchored.
    
    Query parameters:
    - limit: Maximum number of events to return (1-1000, default 50)
    - from_block: Starting block number (optional)
    - to_block: Ending block number or "latest" (default "latest")
    
    Returns:
        List of anchor events with transaction and block information
    """
    try:
        logger.info(f"Fetching anchor events: limit={limit}, from_block={from_block}, to_block={to_block}")
        
        # Create anchor service
        anchor_service = create_anchor_service()
        
        # Fetch events
        events = anchor_service.get_events(
            from_block=from_block,
            to_block=to_block,
            limit=limit
        )
        
        # Convert to response model
        anchor_events = [AnchorEvent(**event) for event in events]
        
        response = AnchorEventsResponse(
            success=True,
            count=len(anchor_events),
            events=anchor_events,
            from_block=from_block,
            to_block=to_block
        )
        
        logger.info(f"Retrieved {len(anchor_events)} anchor events")
        return response
        
    except PolygonAnchorError as e:
        logger.error(f"Anchor service error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch events: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error fetching events: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/health", response_model=AnchorHealthResponse)
async def check_anchor_health():
    """
    Check anchor service health and connectivity
    
    This endpoint verifies that the anchor service can connect to the blockchain,
    interact with the smart contract, and has sufficient balance for transactions.
    
    Returns:
        Health status with service configuration and blockchain information
    """
    try:
        logger.info("Checking anchor service health")
        
        # Create anchor service
        anchor_service = create_anchor_service()
        
        # Get health status
        health = anchor_service.health_check()
        
        # Convert to response model
        response = AnchorHealthResponse(**health)
        
        if health.get("healthy"):
            logger.info("Anchor service is healthy")
        else:
            logger.warning(f"Anchor service unhealthy: {health.get('error')}")
            
        return response
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return AnchorHealthResponse(
            healthy=False,
            error=str(e)
        )


@router.get("/contract/info")
async def get_contract_info():
    """
    Get smart contract information
    
    Returns basic information about the deployed ComplianceAnchor contract
    including version, owner, and deployment details.
    
    Returns:
        Contract information dictionary
    """
    try:
        anchor_service = create_anchor_service()
        health = anchor_service.health_check()
        
        if not health.get("healthy"):
            raise HTTPException(
                status_code=503,
                detail=f"Anchor service unavailable: {health.get('error')}"
            )
        
        return {
            "contract_address": health.get("contract_address"),
            "version": health.get("contract_version"),
            "owner": health.get("contract_owner"),
            "chain_id": health.get("chain_id"),
            "latest_block": health.get("latest_block"),
            "rpc_url": health.get("rpc_url")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get contract info: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get contract info: {str(e)}"
        )


@router.get("/explorer/{tx_hash}")
async def get_explorer_link(tx_hash: str):
    """
    Get blockchain explorer link for a transaction
    
    Args:
        tx_hash: Transaction hash
        
    Returns:
        Explorer URL for the transaction
    """
    try:
        anchor_service = create_anchor_service()
        health = anchor_service.health_check()
        
        if not health.get("healthy"):
            raise HTTPException(
                status_code=503,
                detail="Anchor service unavailable"
            )
        
        chain_id = health.get("chain_id")
        
        # Determine explorer URL based on chain ID
        if chain_id == 1442:  # Polygon zkEVM Testnet
            explorer_url = f"https://testnet-zkevm.polygonscan.com/tx/{tx_hash}"
        elif chain_id == 1101:  # Polygon zkEVM Mainnet
            explorer_url = f"https://zkevm.polygonscan.com/tx/{tx_hash}"
        else:
            # Local or other network
            explorer_url = f"Local network (chain ID: {chain_id}) - TX: {tx_hash}"
        
        return {
            "tx_hash": tx_hash,
            "explorer_url": explorer_url,
            "chain_id": chain_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate explorer link: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate explorer link: {str(e)}"
        )
