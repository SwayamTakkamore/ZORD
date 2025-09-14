"""Pydantic model for MongoDB transactions"""

import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, validator
from bson import ObjectId
from bson.decimal128 import Decimal128

from app.models.pyobjectid import PyObjectId


class DecisionEnum(str, Enum):
    """Transaction decision status"""
    PENDING = "PENDING"
    PASS = "PASS" 
    HOLD = "HOLD"
    REJECT = "REJECT"


class TransactionModel(BaseModel):
    """
    Transaction model representing a compliance-checked transaction for MongoDB
    
    Fields:
        id: MongoDB ObjectId (primary key)
        tx_uuid: Unique transaction identifier
        wallet_from: Source wallet address
        wallet_to: Destination wallet address  
        amount: Transaction amount
        currency: Currency code (e.g., ETH, USDC)
        kyc_proof_id: Optional KYC proof identifier
        decision: Compliance decision (PENDING/PASS/HOLD/REJECT)
        evidence_hash: Hash of compliance evidence
        merkle_leaf: Merkle tree leaf value
        anchored_root: Blockchain anchored root hash
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """
    
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    tx_uuid: str = Field(default_factory=lambda: str(uuid.uuid4()))
    wallet_from: str = Field(..., min_length=1, max_length=64)
    wallet_to: str = Field(..., min_length=1, max_length=64)
    amount: Decimal = Field(..., gt=0)
    currency: str = Field(default="ETH", max_length=10)
    kyc_proof_id: Optional[str] = Field(None, max_length=128)
    decision: DecisionEnum = Field(default=DecisionEnum.PENDING)
    evidence_hash: Optional[str] = Field(None, max_length=64)
    merkle_leaf: Optional[str] = Field(None, max_length=64)
    anchored_root: Optional[str] = Field(None, max_length=64)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        """Pydantic model configuration"""
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {
            ObjectId: str,
            Decimal: float
        }
        
    @validator('updated_at', pre=True, always=True)
    def set_updated_at(cls, v):
        """Always update the updated_at field"""
        return datetime.utcnow()
    
    @validator('wallet_from', 'wallet_to')
    def validate_wallet_address(cls, v):
        """Basic wallet address validation"""
        if not v or len(v.strip()) == 0:
            raise ValueError('Wallet address cannot be empty')
        return v.strip()
    
    @validator('amount')
    def validate_amount(cls, v):
        """Validate transaction amount"""
        if v <= 0:
            raise ValueError('Amount must be greater than 0')
        return v
    
    def dict(self, **kwargs):
        """Custom dict method to handle ObjectId serialization"""
        d = super().dict(**kwargs)
        if '_id' in d:
            d['_id'] = str(d['_id'])
        return d
    
    def to_dict(self) -> dict:
        """Convert model to dictionary for MongoDB insertion"""
        data = self.dict(by_alias=True, exclude_unset=True)
        # Convert Decimal to Decimal128 for MongoDB storage
        if 'amount' in data:
            data['amount'] = Decimal128(str(data['amount']))
        return data
    
    @classmethod
    def from_dict(cls, data: dict) -> 'TransactionModel':
        """Create model from MongoDB document"""
        # Convert Decimal128 back to Decimal for Pydantic validation
        if 'amount' in data:
            amount_value = data['amount']
            if isinstance(amount_value, Decimal128):
                data['amount'] = Decimal(str(amount_value))
            elif isinstance(amount_value, (float, int)):
                data['amount'] = Decimal(str(amount_value))
        return cls(**data)
    
    def __repr__(self):
        return f"<TransactionModel(id={self.id}, tx_uuid={self.tx_uuid}, decision={self.decision})>"
