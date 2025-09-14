# backend/app/utils/normalizers.py
"""
Utilities for normalizing data between client format, MongoDB storage, and JSON responses
Handles ObjectId, Decimal128, and datetime serialization properly
"""
from decimal import Decimal
from bson.decimal128 import Decimal128
from bson import ObjectId
from datetime import datetime
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


def normalize_for_mongo(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert client payload to MongoDB document format
    
    Input (mobile app format):
    {
        "hash": "0x123...",
        "from_address": "0x742d...",
        "to_address": "0x8ba1...",
        "amount": "100.50" or 100.50,
        "asset": "USDT",
        "memo": "optional"
    }
    
    Output (MongoDB format):
    {
        "tx_hash": "0x123...",
        "wallet_from": "0x742d...",
        "wallet_to": "0x8ba1...",
        "amount": Decimal128("100.50"),
        "currency": "USDT",
        "memo": "optional",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "decision": "PENDING"
    }
    """
    try:
        doc = {
            "tx_hash": payload.get("hash"),
            "wallet_from": payload.get("from_address"),
            "wallet_to": payload.get("to_address"),
            "currency": payload.get("asset"),
            "memo": payload.get("memo"),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "decision": "PENDING",  # Default decision
        }
        
        # Handle amount conversion to Decimal128 for MongoDB
        amount = payload.get("amount")
        if amount is None:
            doc["amount"] = None
        else:
            # Ensure proper Decimal128 conversion
            if isinstance(amount, Decimal):
                doc["amount"] = Decimal128(str(amount))
            elif isinstance(amount, (str, int, float)):
                # Convert to Decimal first, then to Decimal128
                decimal_amount = Decimal(str(amount))
                doc["amount"] = Decimal128(str(decimal_amount))
            else:
                raise ValueError(f"Invalid amount type: {type(amount)}")
        
        logger.debug(f"Normalized for MongoDB: {doc}")
        return doc
        
    except Exception as e:
        logger.error(f"Error normalizing for MongoDB: {e}")
        raise ValueError(f"Failed to normalize payload for MongoDB: {str(e)}")


def normalize_for_response(mongo_doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert MongoDB document to JSON-safe response format
    
    Input (MongoDB format):
    {
        "_id": ObjectId("64f9a1c2b4d8e9f1a2b3c4d5"),
        "tx_hash": "0x123...",
        "wallet_from": "0x742d...",
        "wallet_to": "0x8ba1...",
        "amount": Decimal128("100.50"),
        "currency": "USDT",
        "created_at": datetime(2025, 9, 12, 14, 30, 0),
        "decision": "PENDING"
    }
    
    Output (JSON-safe format):
    {
        "tx_id": "64f9a1c2b4d8e9f1a2b3c4d5",
        "hash": "0x123...",
        "wallet_from": "0x742d...",
        "wallet_to": "0x8ba1...",
        "amount": "100.50",
        "asset": "USDT",
        "created_at": "2025-09-12T14:30:00.000000",
        "decision": "PENDING"
    }
    """
    try:
        if not mongo_doc:
            return {}
            
        # Create a copy to avoid modifying the original
        out = dict(mongo_doc)
        
        # Convert ObjectId to string
        if "_id" in out:
            out["tx_id"] = str(out["_id"])
            out.pop("_id", None)
        
        # Convert Decimal128 to string
        if "amount" in out and out["amount"] is not None:
            if hasattr(out["amount"], "to_decimal"):
                # Decimal128 object
                out["amount"] = str(out["amount"].to_decimal())
            elif isinstance(out["amount"], (Decimal, float, int)):
                out["amount"] = str(out["amount"])
        
        # Convert datetime to ISO format string
        for field in ["created_at", "updated_at"]:
            if field in out and out[field] is not None:
                if isinstance(out[field], datetime):
                    out[field] = out[field].isoformat()
        
        # Map internal field names to client format
        field_mapping = {
            "tx_hash": "hash",
            "currency": "asset",
        }
        
        for internal_field, client_field in field_mapping.items():
            if internal_field in out:
                out[client_field] = out[internal_field]
                if internal_field != client_field:
                    out.pop(internal_field, None)
        
        logger.debug(f"Normalized for response: {out}")
        return out
        
    except Exception as e:
        logger.error(f"Error normalizing for response: {e}")
        raise ValueError(f"Failed to normalize document for response: {str(e)}")


def sanitize_for_logging(data: Dict[str, Any], sensitive_fields: Optional[set] = None) -> Dict[str, Any]:
    """
    Sanitize data for logging by redacting sensitive fields
    
    Args:
        data: Dictionary to sanitize
        sensitive_fields: Set of field names to redact (default: common sensitive fields)
    
    Returns:
        Sanitized dictionary safe for logging
    """
    if sensitive_fields is None:
        sensitive_fields = {
            "password", "secret", "token", "key", "private", "aadhar", "pan", "ssn",
            "credit_card", "card_number", "cvv", "pin"
        }
    
    def _redact_recursive(obj):
        if isinstance(obj, dict):
            return {
                k: "<REDACTED>" if k.lower() in sensitive_fields else _redact_recursive(v)
                for k, v in obj.items()
            }
        elif isinstance(obj, list):
            return [_redact_recursive(item) for item in obj]
        else:
            return obj
    
    return _redact_recursive(data)


def validate_mongo_doc(doc: Dict[str, Any]) -> bool:
    """
    Validate that a document is ready for MongoDB insertion
    
    Args:
        doc: Document to validate
        
    Returns:
        True if valid, raises ValueError if invalid
    """
    required_fields = ["wallet_from", "wallet_to", "amount", "currency"]
    
    for field in required_fields:
        if field not in doc or doc[field] is None:
            raise ValueError(f"Missing required field: {field}")
    
    # Validate amount is Decimal128
    if not isinstance(doc["amount"], Decimal128):
        raise ValueError(f"Amount must be Decimal128, got {type(doc['amount'])}")
    
    # Validate addresses
    for addr_field in ["wallet_from", "wallet_to"]:
        addr = doc[addr_field]
        if not isinstance(addr, str) or len(addr) < 20:
            raise ValueError(f"Invalid address format for {addr_field}: {addr}")
    
    return True