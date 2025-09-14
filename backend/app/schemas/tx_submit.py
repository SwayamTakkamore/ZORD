# backend/app/schemas/tx_submit.py
"""
Pydantic schema for transaction submission endpoint
Handles mobile app format: from_address, to_address, amount, asset, hash, memo
"""
from pydantic import BaseModel, Field, validator
from decimal import Decimal
from typing import Optional


class TxSubmitSchema(BaseModel):
    """
    Schema for /v1/tx/submit endpoint
    Accepts mobile app payload format and validates all fields
    """
    hash: str = Field(..., min_length=10, description="Transaction hash")
    from_address: str = Field(..., description="Source wallet address")
    to_address: str = Field(..., description="Destination wallet address")
    amount: Decimal = Field(..., gt=0, description="Transaction amount (will be coerced from string)")
    asset: str = Field(..., min_length=1, max_length=10, description="Asset/currency code")
    memo: Optional[str] = Field(None, max_length=500, description="Optional transaction memo")

    @validator("from_address", "to_address")
    def validate_address(cls, v):
        """Validate wallet addresses"""
        if not isinstance(v, str) or len(v) < 20:
            raise ValueError("Address must be at least 20 characters")
        # Basic Ethereum address format check
        if not v.startswith("0x") or len(v) != 42:
            raise ValueError("Address must be a valid Ethereum address (0x + 40 hex chars)")
        return v.lower()  # Normalize to lowercase

    @validator("asset")
    def validate_asset(cls, v):
        """Validate asset code"""
        if not v or not v.strip():
            raise ValueError("Asset code cannot be empty")
        return v.upper()  # Normalize to uppercase

    @validator("amount", pre=True)
    def validate_amount(cls, v):
        """Convert amount to Decimal for precise handling"""
        if isinstance(v, str):
            try:
                return Decimal(v)
            except:
                raise ValueError("Amount must be a valid number")
        elif isinstance(v, (int, float)):
            return Decimal(str(v))
        elif isinstance(v, Decimal):
            return v
        else:
            raise ValueError("Amount must be a valid number")

    class Config:
        """Pydantic config"""
        json_encoders = {
            Decimal: str  # Serialize Decimal as string in JSON
        }


class TxSubmitResponse(BaseModel):
    """
    Response schema for successful transaction submission
    """
    tx_id: str = Field(..., description="Unique transaction identifier (MongoDB ObjectId)")
    hash: str = Field(..., description="Transaction hash")
    wallet_from: str = Field(..., description="Source wallet address")
    wallet_to: str = Field(..., description="Destination wallet address")
    amount: str = Field(..., description="Transaction amount as string")
    asset: str = Field(..., description="Asset/currency code")
    decision: str = Field(..., description="Compliance decision")
    memo: Optional[str] = Field(None, description="Transaction memo")
    created_at: str = Field(..., description="Creation timestamp (ISO format)")

    class Config:
        """Pydantic config"""
        schema_extra = {
            "example": {
                "tx_id": "64f9a1c2b4d8e9f1a2b3c4d5",
                "hash": "0x123456789abcdef123456789abcdef123456789abcdef123456789abcdef1234",
                "wallet_from": "0x742d35cc6635c0532925a3b8d5c2c17c5865000e",
                "wallet_to": "0x8ba1f109551bd432803012645hac136c2c17c586",
                "amount": "100.50",
                "asset": "USDT",
                "decision": "PENDING",
                "memo": "Test transaction from mobile app",
                "created_at": "2025-09-12T14:30:00.123456"
            }
        }