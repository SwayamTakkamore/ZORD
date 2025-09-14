"""Transaction API endpoints with MongoDB support"""

import uuid
import hashlib
import logging
from typing import Optional
from decimal import Decimal
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query, Header
from bson import ObjectId
from bson.decimal128 import Decimal128

from app.models.transaction import TransactionModel, DecisionEnum
from app.services.transaction_crud import transaction_crud
from app.schemas.transaction import (
    TransactionSubmitRequest,
    TransactionSubmitResponse, 
    TransactionResponse,
    TransactionListResponse,
    TransactionReviewRequest,
    TransactionReviewResponse,
    OverrideRequest,
    OverrideResponse
)
from app.core.compliance_engine import evaluate_transaction_compliance
from app.core.merkle import MerkleTree

router = APIRouter()
logger = logging.getLogger(__name__)

# Global Merkle tree for evidence aggregation
evidence_tree = MerkleTree()


def normalize_mongodb_doc(doc: dict) -> dict:
    """
    Normalize MongoDB document for JSON-safe response
    
    Converts:
    - _id (ObjectId) to tx_id (string)
    - Decimal128 amount to string
    - datetime objects to ISO8601 strings
    """
    try:
        normalized = doc.copy()
        
        # Convert ObjectId to string
        if "_id" in normalized:
            normalized["tx_id"] = str(normalized.pop("_id"))
        
        # Convert Decimal128 to string for JSON safety
        if "amount" in normalized and isinstance(normalized["amount"], Decimal128):
            normalized["amount"] = str(normalized["amount"].to_decimal())
        
        # Ensure datetime fields are ISO8601 strings
        for field in ["created_at", "updated_at"]:
            if field in normalized and isinstance(normalized[field], datetime):
                normalized[field] = normalized[field].isoformat()
        
        # Map currency to asset for mobile app compatibility
        if "currency" in normalized:
            normalized["asset"] = normalized["currency"]
        
        return normalized
        
    except Exception as e:
        logger.error(f"Failed to normalize MongoDB document: {str(e)}")
        raise ValueError(f"Document normalization failed: {str(e)}")


@router.post("/tx/submit", response_model=TransactionSubmitResponse)
async def submit_transaction(
    request: TransactionSubmitRequest
) -> TransactionSubmitResponse:
    """
    Submit a new transaction for compliance checking
    
    Supports both mobile app format (from_address/to_address/asset) and web format (wallet_from/wallet_to/currency)
    
    Example mobile app request:
    {
        "hash": "0x123...",
        "from_address": "0x742d35Cc...",
        "to_address": "0x8ba1f109...",
        "amount": "100.50",
        "asset": "USDT",
        "memo": "Test transaction"
    }
    """
    try:
        # Extract wallet addresses directly from TxSubmitSchema fields
        wallet_from = request.from_address
        wallet_to = request.to_address
        
        # Validate addresses exist
        if not wallet_from or not wallet_to:
            raise HTTPException(
                status_code=422, 
                detail="Missing wallet addresses. Both from_address and to_address are required"
            )
        
        # Generate unique transaction UUID
        tx_uuid = str(uuid.uuid4())
        
        # Convert amount to Decimal for Pydantic model validation
        amount_decimal = request.amount
        if isinstance(amount_decimal, str):
            amount_decimal = Decimal(amount_decimal)
        elif isinstance(amount_decimal, float):
            amount_decimal = Decimal(str(amount_decimal))
        elif isinstance(amount_decimal, Decimal128):
            amount_decimal = Decimal(str(amount_decimal))
        
        # Determine currency - use asset field from mobile app format
        currency = request.asset
        
        # Run enhanced compliance check with Decimal for compatibility
        decision, reason, evidence_hash = evaluate_transaction_compliance(
            wallet_from=wallet_from,
            wallet_to=wallet_to,
            amount=amount_decimal,  # Use Decimal for compliance engine
            currency=currency,
            kyc_proof_id=None,  # TxSubmitSchema doesn't include KYC proof
            metadata={
                "source": "api_submission", 
                "hash": request.hash,
                "memo": getattr(request, 'memo', None)
            }
        )
        
        # Create transaction record with Decimal (will be converted to Decimal128 in to_dict)
        transaction_data = {
            "tx_uuid": tx_uuid,
            "wallet_from": wallet_from.lower(),  # Normalize to lowercase
            "wallet_to": wallet_to.lower(),      # Normalize to lowercase
            "amount": amount_decimal,            # Store as Decimal (Pydantic will validate)
            "currency": currency,
            "tx_hash": request.hash,
            "memo": getattr(request, 'memo', None),
            "kyc_proof_id": None,  # TxSubmitSchema doesn't include KYC proof
            "decision": decision.value,
            "evidence_hash": evidence_hash,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        logger.info(f"Creating transaction {tx_uuid} with decision {decision}")
        
        # Create transaction in MongoDB
        result = await transaction_crud.create_transaction(transaction_data)
        
        # Fetch the created document using the UUID to get the complete record
        created_doc = await transaction_crud.get_transaction_by_uuid(tx_uuid)
        if not created_doc:
            raise Exception(f"Failed to retrieve created transaction with UUID {tx_uuid}")
        
        # Convert MongoDB model to dict for normalization
        doc_dict = created_doc.to_dict() if hasattr(created_doc, 'to_dict') else created_doc.dict() if hasattr(created_doc, 'dict') else dict(created_doc)
        
        # Add evidence to Merkle tree
        merkle_leaf = evidence_tree.add_leaf(evidence_hash)
        
        # Update transaction with merkle leaf  
        await transaction_crud.update_transaction(
            tx_uuid,
            {"merkle_leaf": merkle_leaf}
        )
        
        # Normalize document for JSON response
        try:
            normalized_doc = normalize_mongodb_doc(doc_dict)
            logger.info(f"Transaction {tx_uuid} submitted successfully with decision {decision}")
        except Exception as norm_error:
            logger.error(f"Failed to normalize transaction document for response: {str(norm_error)}")
            logger.error(f"Original document: {doc_dict}")
            # Fallback to basic response if normalization fails
            normalized_doc = {
                "tx_uuid": tx_uuid,
                "amount": str(amount_decimal),
                "currency": currency,
                "decision": decision.value,
                "evidence_hash": evidence_hash,
                "created_at": datetime.utcnow().isoformat()
            }
        
        # Return response with normalized values - use tx_uuid from doc or fallback
        return TransactionSubmitResponse(
            tx_id=normalized_doc.get("tx_uuid", tx_uuid),
            decision=decision,
            message=reason,
            evidence_hash=normalized_doc.get("evidence_hash", evidence_hash),
            created_at=normalized_doc.get("created_at", datetime.utcnow().isoformat())
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions without modification
        raise
    except Exception as e:
        # Generate trace ID for debugging
        trace_id = str(uuid.uuid4())
        error_msg = f"Failed to submit transaction: {str(e)}"
        
        logger.exception(f"Error submitting transaction [trace_id: {trace_id}]: {str(e)}")
        
        raise HTTPException(
            status_code=500, 
            detail={
                "error": "Internal server error",
                "message": "Transaction submission failed", 
                "trace_id": trace_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.get("/tx/list", response_model=TransactionListResponse)
async def list_transactions(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    decision: Optional[DecisionEnum] = Query(None, description="Filter by decision")
) -> TransactionListResponse:
    """
    List transactions with pagination and optional filtering
    
    Example request:
    GET /v1/tx/list?page=1&per_page=20&decision=PASS
    
    Example response:
    {
        "transactions": [...],
        "total": 50,
        "page": 1, 
        "per_page": 20
    }
    """
    try:
        # Calculate pagination
        skip = (page - 1) * per_page
        
        # Get transactions with filtering
        transactions = await transaction_crud.list_transactions(
            limit=per_page,
            skip=skip,
            decision=decision
        )
        
        # Get total count
        total = await transaction_crud.count_transactions(decision=decision)
        
        # Convert to response models with proper serialization
        transaction_responses = []
        for tx in transactions:
            # Safely convert ObjectId to string
            tx_id = str(tx.id) if tx.id else ""
            
            # Ensure amount is properly converted
            amount = float(tx.amount) if tx.amount else 0.0
            
            tx_response = TransactionResponse(
                id=tx_id,
                tx_uuid=tx.tx_uuid,
                wallet_from=tx.wallet_from,
                wallet_to=tx.wallet_to,
                amount=amount,
                currency=tx.currency,
                kyc_proof_id=tx.kyc_proof_id,
                decision=tx.decision,
                evidence_hash=tx.evidence_hash,
                merkle_leaf=tx.merkle_leaf,
                anchored_root=tx.anchored_root,
                created_at=tx.created_at,
                updated_at=tx.updated_at
            )
            transaction_responses.append(tx_response)
        
        return TransactionListResponse(
            transactions=transaction_responses,
            total=total,
            page=page,
            per_page=per_page
        )
        
    except Exception as e:
        logger.exception(f"Error listing transactions: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to list transactions")


@router.post("/tx/review", response_model=TransactionReviewResponse)
async def review_transaction(
    request: TransactionReviewRequest
) -> TransactionReviewResponse:
    """
    Manual review/override of a transaction decision
    
    Example request:
    POST /v1/tx/review
    {
        "tx_uuid": "123e4567-e89b-12d3-a456-426614174000",
        "decision": "PASS",
        "reason": "Manual override - customer verified via phone"
    }
    
    Example response:
    {
        "success": true,
        "message": "Transaction decision updated successfully",
        "tx_uuid": "123e4567-e89b-12d3-a456-426614174000", 
        "old_decision": "HOLD",
        "new_decision": "PASS"
    }
    """
    try:
        # Find transaction by UUID
        tx = await transaction_crud.get_transaction_by_uuid(request.tx_uuid)
        
        if not tx:
            raise HTTPException(status_code=404, detail="Transaction not found")
        
        old_decision = tx.decision
        
        # Update transaction decision
        update_data = {
            "decision": request.decision.value,
            # Store review reason in evidence_hash field for now
            # In production, you might want a separate reviews collection
            "review_reason": request.reason
        }
        
        updated_tx = await transaction_crud.update_transaction(
            request.tx_uuid, 
            update_data
        )
        
        if not updated_tx:
            raise HTTPException(status_code=404, detail="Failed to update transaction")
        
        # Create new evidence hash for the manual override
        override_evidence = f"manual_override:{request.tx_uuid}:{request.decision.value}:{request.reason}"
        override_hash = hashlib.sha256(override_evidence.encode()).hexdigest()
        
        # Add override evidence to Merkle tree
        evidence_tree.add_leaf(override_hash)
        
        logger.info(f"Transaction {request.tx_uuid} reviewed: {old_decision} -> {request.decision}, reason: {request.reason}")
        
        return TransactionReviewResponse(
            success=True,
            message="Transaction decision updated successfully",
            tx_uuid=request.tx_uuid,
            old_decision=old_decision,
            new_decision=request.decision
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reviewing transaction {request.tx_uuid}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to review transaction")


@router.get("/merkle/root")
async def get_merkle_root():
    """
    Get the current Merkle root of all evidence
    
    Example response:
    {
        "root_hash": "abc123...",
        "total_leaves": 42,
        "tree_height": 6,
        "last_updated": "2025-09-10T12:00:00Z"
    }
    """
    try:
        root_hash = evidence_tree.get_root()
        tree_info = evidence_tree.get_tree_info()
        
        return {
            "root_hash": root_hash,
            "total_leaves": tree_info["total_leaves"],
            "tree_height": tree_info["tree_height"],
            "last_updated": "2025-09-10T12:00:00Z"  # In production, track actual timestamp
        }
        
    except Exception as e:
        logger.error(f"Error getting Merkle root: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get Merkle root")


@router.get("/merkle/proof/{evidence_hash}")
async def get_merkle_proof(evidence_hash: str):
    """
    Get Merkle proof for a specific evidence hash
    
    Example response:
    {
        "leaf_hash": "abc123...",
        "leaf_index": 5,
        "proof_hashes": ["def456...", "ghi789..."],
        "proof_directions": ["left", "right"],
        "root_hash": "xyz999...",
        "verified": true
    }
    """
    try:
        proof = evidence_tree.get_proof(evidence_hash)
        
        if not proof:
            raise HTTPException(status_code=404, detail="Evidence hash not found in tree")
        
        # Verify the proof
        is_valid = evidence_tree.verify_proof(proof)
        
        response = proof.to_dict()
        response["verified"] = is_valid
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting Merkle proof for {evidence_hash}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get Merkle proof")


@router.get("/compliance/summary")
async def get_compliance_summary():
    """
    Get compliance engine configuration and statistics
    
    Example response:
    {
        "blacklisted_wallets_count": 3,
        "amount_threshold_usd": "1000.0",
        "kyc_required": true,
        "max_risk_score": 100,
        "supported_rules": ["BLACKLIST_CHECK", "AMOUNT_THRESHOLD", ...]
    }
    """
    try:
        from app.core.compliance_engine import compliance_engine
        
        summary = compliance_engine.get_compliance_summary()
        return summary
        
    except Exception as e:
        logger.error(f"Error getting compliance summary: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get compliance summary")


@router.post("/override", response_model=OverrideResponse)
async def override_transaction_decision(
    request: OverrideRequest,
    x_admin_api_key: str = Header(..., description="Admin API key for authorization")
):
    """
    Override transaction decision with admin authorization
    
    This endpoint allows authorized admins to manually override transaction decisions
    with full audit trail and Merkle evidence integration.
    
    Headers:
    - X-Admin-API-Key: Required admin API key for authorization
    
    Request body:
    {
        "hash": "0x123abc... or tx_uuid",
        "status": "pass|hold|reject (or synonyms)",
        "reason": "Detailed reason for override"
    }
    
    Response:
    {
        "success": true,
        "message": "Transaction override applied successfully",
        "transaction_id": "123e4567-e89b-12d3-a456-426614174000",
        "old_decision": "HOLD",
        "new_decision": "PASS",
        "evidence_hash": "abc123def456...",
        "audit_entry": {...}
    }
    """
    try:
        # Admin authorization check
        # TODO: Replace with proper admin key validation from config/database
        expected_admin_key = "admin_key_12345"  # This should come from environment/config
        if x_admin_api_key != expected_admin_key:
            logger.warning(f"Unauthorized override attempt with key: {x_admin_api_key[:8]}...")
            raise HTTPException(status_code=401, detail="Invalid admin API key")
        
        # Find transaction by hash or UUID
        transaction = await transaction_crud.get_transaction_by_hash(request.hash)
        if not transaction:
            raise HTTPException(status_code=404, detail=f"Transaction not found: {request.hash}")
        
        # Store old decision for audit
        old_decision = transaction.decision
        new_decision = DecisionEnum(request.status)  # request.status is already normalized by validator
        
        # Check if decision actually changed
        if old_decision == new_decision:
            return OverrideResponse(
                success=True,
                message=f"Transaction already has decision {new_decision}",
                transaction_id=transaction.tx_uuid,
                old_decision=old_decision,
                new_decision=new_decision,
                evidence_hash=transaction.evidence_hash or "",
                audit_entry={}
            )
        
        # Create audit entry
        audit_entry = {
            "action": "manual_override",
            "timestamp": datetime.utcnow().isoformat(),
            "admin_key_prefix": x_admin_api_key[:8] + "...",  # Store partial key for audit
            "old_decision": old_decision.value,
            "new_decision": new_decision.value,
            "reason": request.reason,
            "evidence_hash": transaction.evidence_hash
        }
        
        # Add audit entry to transaction reviews
        audit_added = await transaction_crud.add_review_audit(transaction.tx_uuid, audit_entry)
        if not audit_added:
            raise HTTPException(status_code=500, detail="Failed to add audit entry")
        
        # Update transaction decision
        update_success = await transaction_crud.update_transaction(
            transaction.tx_uuid,
            {"decision": new_decision, "updated_at": datetime.utcnow()}
        )
        
        if not update_success:
            raise HTTPException(status_code=500, detail="Failed to update transaction decision")
        
        # Generate new evidence for the override
        override_evidence = {
            "override_timestamp": datetime.utcnow().isoformat(),
            "original_decision": old_decision.value,
            "new_decision": new_decision.value,
            "admin_action": True,
            "reason": request.reason
        }
        
        # Add to Merkle tree for evidence integrity
        evidence_hash = hashlib.sha256(str(override_evidence).encode()).hexdigest()
        merkle_leaf = evidence_tree.add_leaf(evidence_hash)
        
        # Update transaction with new evidence hash
        await transaction_crud.update_transaction(
            transaction.tx_uuid,
            {
                "evidence_hash": evidence_hash,
                "merkle_leaf": merkle_leaf,
                "updated_at": datetime.utcnow()
            }
        )
        
        logger.info(f"Transaction {transaction.tx_uuid} overridden: {old_decision} -> {new_decision}")
        
        return OverrideResponse(
            success=True,
            message="Transaction override applied successfully",
            transaction_id=transaction.tx_uuid,
            old_decision=old_decision,
            new_decision=new_decision,
            evidence_hash=evidence_hash,
            audit_entry=audit_entry
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error overriding transaction {request.hash}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to override transaction")
