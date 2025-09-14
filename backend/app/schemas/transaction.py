"""Pydantic schemas for transaction API requests and responses"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional, Union
from pydantic import BaseModel, Field, ConfigDict, validator

from app.models.transaction import DecisionEnum


class TransactionSubmitRequest(BaseModel):
    """
    Schema for submitting a new transaction - supports both mobile and web formats
    
    Mobile app format:
    {
        "hash": "0x123...",
        "from_address": "0x742d35Cc6634C0532925a3b8D4d0C123456789AB",
        "to_address": "0x123d35Cc6634C0532925a3b8D4d0C123456789CD",
        "amount": "100.5"
    }
    
    Web format:
    {
        "wallet_from": "0x742d35Cc6634C0532925a3b8D4d0C123456789AB",
        "wallet_to": "0x123d35Cc6634C0532925a3b8D4d0C123456789CD", 
        "amount": "100.5",
        "currency": "ETH",
        "kyc_proof_id": "kyc_12345"
    }
    """
    # Support both field name formats
    wallet_from: Optional[str] = Field(None, description="Source wallet address (web format)")
    wallet_to: Optional[str] = Field(None, description="Destination wallet address (web format)")
    from_address: Optional[str] = Field(None, description="Source wallet address (mobile format)")
    to_address: Optional[str] = Field(None, description="Destination wallet address (mobile format)")
    
    # Transaction details
    hash: Optional[str] = Field(None, description="Transaction hash")
    amount: Union[str, Decimal, float] = Field(..., description="Transaction amount")
    currency: Optional[str] = Field("ETH", max_length=10, description="Currency code")
    asset: Optional[str] = Field(None, max_length=10, description="Asset code (alias for currency)")
    memo: Optional[str] = Field(None, description="Transaction memo")
    kyc_proof_id: Optional[str] = Field(None, max_length=128, description="KYC proof identifier")
    
    @validator('amount', pre=True)
    def convert_amount(cls, v):
        """Convert amount to Decimal for consistent handling"""
        if isinstance(v, str):
            return Decimal(v)
        elif isinstance(v, (int, float)):
            return Decimal(str(v))
        return v
    
    @validator('currency', pre=True, always=True)
    def set_currency(cls, v, values):
        """Use asset field as currency if currency not provided"""
        if not v and 'asset' in values and values['asset']:
            return values['asset']
        return v or "ETH"
    
    def get_wallet_from(self) -> str:
        """Get source wallet address from either field format"""
        return self.wallet_from or self.from_address or ""
    
    def get_wallet_to(self) -> str:
        """Get destination wallet address from either field format"""
        return self.wallet_to or self.to_address or ""


class TransactionSubmitResponse(BaseModel):
    """
    Schema for transaction submission response
    
    Example response:
    {
        "tx_id": "123e4567-e89b-12d3-a456-426614174000",
        "decision": "PASS",
        "message": "Transaction approved",
        "evidence_hash": "abc123...",
        "created_at": "2025-09-10T12:00:00Z"
    }
    """
    model_config = ConfigDict(from_attributes=True)
    
    tx_id: str = Field(..., description="Unique transaction identifier")
    decision: DecisionEnum = Field(..., description="Compliance decision")
    message: str = Field(..., description="Human-readable decision message")
    evidence_hash: Optional[str] = Field(None, description="Hash of compliance evidence")
    created_at: datetime = Field(..., description="Transaction creation timestamp")


class TransactionResponse(BaseModel):
    """
    Schema for full transaction details
    
    Example response:
    {
        "id": "68c411552a024778fad4462d",
        "tx_uuid": "123e4567-e89b-12d3-a456-426614174000",
        "wallet_from": "0x742d35Cc6634C0532925a3b8D4d0C123456789AB",
        "wallet_to": "0x123d35Cc6634C0532925a3b8D4d0C123456789CD",
        "amount": 100.5,
        "currency": "ETH", 
        "kyc_proof_id": "kyc_12345",
        "decision": "PASS",
        "evidence_hash": "abc123...",
        "merkle_leaf": "def456...",
        "anchored_root": null,
        "created_at": "2025-09-10T12:00:00Z",
        "updated_at": "2025-09-10T12:00:00Z"
    }
    """
    model_config = ConfigDict(from_attributes=True)
    
    id: str = Field(..., description="MongoDB ObjectId as string")
    tx_uuid: str = Field(..., description="Unique transaction identifier")
    wallet_from: str = Field(..., description="Source wallet address")
    wallet_to: str = Field(..., description="Destination wallet address")
    amount: float = Field(..., description="Transaction amount as float")
    currency: str = Field(..., description="Currency code")
    kyc_proof_id: Optional[str] = Field(None, description="KYC proof identifier")
    decision: DecisionEnum = Field(..., description="Compliance decision")
    evidence_hash: Optional[str] = Field(None, description="Hash of compliance evidence")
    merkle_leaf: Optional[str] = Field(None, description="Merkle tree leaf value")
    anchored_root: Optional[str] = Field(None, description="Blockchain anchored root hash")
    created_at: datetime = Field(..., description="Transaction creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class TransactionListResponse(BaseModel):
    """
    Schema for paginated transaction list
    
    Example response:
    {
        "transactions": [...],
        "total": 50,
        "page": 1,
        "per_page": 20
    }
    """
    transactions: list[TransactionResponse]
    total: int = Field(..., description="Total number of transactions")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Items per page")


class TransactionReviewRequest(BaseModel):
    """
    Schema for manual transaction review/override
    
    Example request:
    {
        "tx_uuid": "123e4567-e89b-12d3-a456-426614174000",
        "decision": "PASS",
        "reason": "Manual override - customer verified via phone"
    }
    """
    tx_uuid: str = Field(..., description="Transaction UUID to review")
    decision: DecisionEnum = Field(..., description="New decision")
    reason: str = Field(..., min_length=10, max_length=500, description="Reason for manual override")


class TransactionReviewResponse(BaseModel):
    """
    Schema for manual review response
    
    Example response:
    {
        "success": true,
        "message": "Transaction decision updated successfully",
        "tx_uuid": "123e4567-e89b-12d3-a456-426614174000",
        "old_decision": "HOLD",
        "new_decision": "PASS"
    }
    """
    success: bool
    message: str
    tx_uuid: str
    old_decision: DecisionEnum
    new_decision: DecisionEnum


class OverrideRequest(BaseModel):
    """
    Schema for manual transaction override (enhanced version of review)
    
    Example request:
    {
        "hash": "0x123abc...",
        "status": "pass",
        "reason": "Manual verification completed via secondary KYC process"
    }
    """
    hash: str = Field(..., description="Transaction hash or UUID to override")
    status: str = Field(..., description="New status: pass, hold, reject (or synonyms)")
    reason: str = Field(..., min_length=10, max_length=500, description="Detailed reason for override")

    @validator('status')
    def normalize_status(cls, v):
        """Normalize status to standard decision values"""
        status_map = {
            # Pass variants
            'pass': 'PASS',
            'approved': 'PASS', 
            'approve': 'PASS',
            'accept': 'PASS',
            'accepted': 'PASS',
            'allow': 'PASS',
            'allowed': 'PASS',
            
            # Hold variants
            'hold': 'HOLD',
            'pending': 'HOLD',
            'review': 'HOLD',
            'suspend': 'HOLD',
            'suspended': 'HOLD',
            'pause': 'HOLD',
            'paused': 'HOLD',
            
            # Reject variants
            'reject': 'REJECT',
            'rejected': 'REJECT',
            'deny': 'REJECT',
            'denied': 'REJECT',
            'block': 'REJECT',
            'blocked': 'REJECT',
            'fail': 'REJECT',
            'failed': 'REJECT'
        }
        
        normalized = status_map.get(v.lower())
        if not normalized:
            raise ValueError(f"Invalid status '{v}'. Allowed: {list(status_map.keys())}")
        return normalized


class OverrideResponse(BaseModel):
    """
    Schema for override response with audit trail
    
    Example response:
    {
        "success": true,
        "message": "Transaction override applied successfully",
        "transaction_id": "123e4567-e89b-12d3-a456-426614174000",
        "old_decision": "HOLD",
        "new_decision": "PASS", 
        "evidence_hash": "abc123def456...",
        "audit_entry": {
            "action": "manual_override",
            "timestamp": "2025-01-27T10:30:00Z",
            "admin_id": "admin_user_123",
            "reason": "Manual verification completed",
            "evidence_hash": "abc123def456..."
        }
    }
    """
    success: bool
    message: str
    transaction_id: str
    old_decision: DecisionEnum
    new_decision: DecisionEnum
    evidence_hash: str
    audit_entry: dict
