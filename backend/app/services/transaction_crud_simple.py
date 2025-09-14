# backend/app/services/transaction_crud_simple.py
"""
Simplified MongoDB CRUD operations for transactions using Motor async
Works with normalizer utilities for proper serialization
"""
import logging
from typing import Dict, Any, List, Optional
from bson import ObjectId
from bson.decimal128 import Decimal128
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.errors import DuplicateKeyError, PyMongoError

from app.db.mongo import get_database
from app.utils.normalizers import validate_mongo_doc

logger = logging.getLogger(__name__)


async def create_transaction(doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a new transaction in MongoDB
    
    Args:
        doc: Normalized transaction document ready for MongoDB
        
    Returns:
        Dict: Inserted document with _id
        
    Raises:
        ValueError: If document validation fails
        DuplicateKeyError: If duplicate transaction hash
        Exception: For other database errors
    """
    try:
        # Validate document before insertion
        validate_mongo_doc(doc)
        
        # Get database connection
        db: AsyncIOMotorDatabase = await get_database()
        
        # Insert document
        result = await db.transactions.insert_one(doc)
        
        if not result.inserted_id:
            raise RuntimeError("Failed to insert transaction - no ID returned")
        
        # Retrieve the inserted document
        inserted_doc = await db.transactions.find_one({"_id": result.inserted_id})
        
        if not inserted_doc:
            raise RuntimeError(f"Failed to retrieve inserted transaction {result.inserted_id}")
        
        logger.info(f"Successfully created transaction {result.inserted_id}")
        return inserted_doc
        
    except DuplicateKeyError as e:
        logger.error(f"Duplicate transaction hash: {doc.get('tx_hash')}")
        raise
    except ValueError as e:
        logger.error(f"Document validation failed: {e}")
        raise
    except PyMongoError as e:
        logger.error(f"MongoDB error creating transaction: {e}")
        raise Exception(f"Database error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error creating transaction: {e}")
        raise


async def get_transaction_by_id(tx_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a transaction by ObjectId
    
    Args:
        tx_id: MongoDB ObjectId as string
        
    Returns:
        Dict: Transaction document or None if not found
    """
    try:
        if not ObjectId.is_valid(tx_id):
            return None
            
        db: AsyncIOMotorDatabase = await get_database()
        doc = await db.transactions.find_one({"_id": ObjectId(tx_id)})
        
        return doc
        
    except Exception as e:
        logger.error(f"Error getting transaction {tx_id}: {e}")
        raise


async def get_transaction_by_hash(tx_hash: str) -> Optional[Dict[str, Any]]:
    """
    Get a transaction by transaction hash
    
    Args:
        tx_hash: Transaction hash
        
    Returns:
        Dict: Transaction document or None if not found
    """
    try:
        db: AsyncIOMotorDatabase = await get_database()
        doc = await db.transactions.find_one({"tx_hash": tx_hash})
        
        return doc
        
    except Exception as e:
        logger.error(f"Error getting transaction by hash {tx_hash}: {e}")
        raise


async def list_transactions(limit: int = 50, skip: int = 0, decision: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    List transactions with pagination and optional filtering
    
    Args:
        limit: Maximum number of transactions to return
        skip: Number of transactions to skip (for pagination)
        decision: Optional decision filter (PENDING, PASS, HOLD, REJECT)
        
    Returns:
        List[Dict]: List of transaction documents
    """
    try:
        db: AsyncIOMotorDatabase = await get_database()
        
        # Build query filter
        query_filter = {}
        if decision:
            query_filter["decision"] = decision
        
        # Execute query with pagination
        cursor = db.transactions.find(query_filter).sort("created_at", -1).skip(skip).limit(limit)
        
        transactions = []
        async for doc in cursor:
            transactions.append(doc)
        
        logger.info(f"Retrieved {len(transactions)} transactions")
        return transactions
        
    except Exception as e:
        logger.error(f"Error listing transactions: {e}")
        raise


async def count_transactions(decision: Optional[str] = None) -> int:
    """
    Count total transactions with optional filtering
    
    Args:
        decision: Optional decision filter
        
    Returns:
        int: Total count of transactions
    """
    try:
        db: AsyncIOMotorDatabase = await get_database()
        
        query_filter = {}
        if decision:
            query_filter["decision"] = decision
        
        count = await db.transactions.count_documents(query_filter)
        return count
        
    except Exception as e:
        logger.error(f"Error counting transactions: {e}")
        raise


async def update_transaction_by_id(tx_id: str, update_data: Dict[str, Any]) -> bool:
    """
    Update a transaction by ObjectId
    
    Args:
        tx_id: MongoDB ObjectId as string
        update_data: Fields to update
        
    Returns:
        bool: True if update successful
    """
    try:
        if not ObjectId.is_valid(tx_id):
            return False
            
        db: AsyncIOMotorDatabase = await get_database()
        
        # Add updated_at timestamp
        update_data["updated_at"] = datetime.utcnow()
        
        result = await db.transactions.update_one(
            {"_id": ObjectId(tx_id)}, 
            {"$set": update_data}
        )
        
        success = result.modified_count > 0
        if success:
            logger.info(f"Successfully updated transaction {tx_id}")
        else:
            logger.warning(f"No transaction updated for ID {tx_id}")
            
        return success
        
    except Exception as e:
        logger.error(f"Error updating transaction {tx_id}: {e}")
        raise


async def delete_transaction_by_id(tx_id: str) -> bool:
    """
    Delete a transaction by ObjectId
    
    Args:
        tx_id: MongoDB ObjectId as string
        
    Returns:
        bool: True if deletion successful
    """
    try:
        if not ObjectId.is_valid(tx_id):
            return False
            
        db: AsyncIOMotorDatabase = await get_database()
        
        result = await db.transactions.delete_one({"_id": ObjectId(tx_id)})
        
        success = result.deleted_count > 0
        if success:
            logger.info(f"Successfully deleted transaction {tx_id}")
        else:
            logger.warning(f"No transaction deleted for ID {tx_id}")
            
        return success
        
    except Exception as e:
        logger.error(f"Error deleting transaction {tx_id}: {e}")
        raise


# For backward compatibility, create a simple interface
class SimplifiedTransactionCRUD:
    """Simplified interface matching the existing pattern"""
    
    @staticmethod
    async def create_transaction(doc: Dict[str, Any]) -> Dict[str, Any]:
        return await create_transaction(doc)
    
    @staticmethod
    async def list_transactions(limit: int = 50, skip: int = 0, decision: Optional[str] = None) -> List[Dict[str, Any]]:
        return await list_transactions(limit, skip, decision)
    
    @staticmethod
    async def count_transactions(decision: Optional[str] = None) -> int:
        return await count_transactions(decision)
    
    @staticmethod
    async def get_transaction_by_id(tx_id: str) -> Optional[Dict[str, Any]]:
        return await get_transaction_by_id(tx_id)
    
    @staticmethod
    async def update_transaction_by_id(tx_id: str, update_data: Dict[str, Any]) -> bool:
        return await update_transaction_by_id(tx_id, update_data)


# Create instance for import
simplified_transaction_crud = SimplifiedTransactionCRUD()