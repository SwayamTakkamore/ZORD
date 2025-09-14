"""MongoDB CRUD operations for transactions using Motor"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Dict, Any
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo.errors import DuplicateKeyError

from app.db.mongo import get_collection
from app.models.transaction import TransactionModel, DecisionEnum

logger = logging.getLogger(__name__)


class TransactionCRUD:
    """CRUD operations for transactions in MongoDB"""
    
    def __init__(self):
        self.collection_name = "transactions"
    
    async def get_collection(self) -> AsyncIOMotorCollection:
        """Get the transactions collection"""
        return await get_collection(self.collection_name)
    
    async def create_transaction(self, transaction_data: dict) -> TransactionModel:
        """
        Create a new transaction in MongoDB
        
        Args:
            transaction_data: Transaction data dictionary
            
        Returns:
            TransactionModel: Created transaction
            
        Raises:
            DuplicateKeyError: If tx_uuid already exists
            Exception: For other database errors
        """
        try:
            collection = await self.get_collection()
            
            # Create transaction model
            transaction = TransactionModel(**transaction_data)
            
            # Convert to dict for MongoDB insertion
            doc = transaction.to_dict()
            
            # Insert into MongoDB
            result = await collection.insert_one(doc)
            
            # Update the model with the inserted ID
            transaction.id = result.inserted_id
            
            logger.info(f"Created transaction: {transaction.tx_uuid}")
            return transaction
            
        except DuplicateKeyError as e:
            logger.error(f"Duplicate transaction UUID: {transaction_data.get('tx_uuid')}")
            raise
        except Exception as e:
            logger.error(f"Failed to create transaction: {e}")
            raise
    
    async def get_transaction(self, transaction_id: str) -> Optional[TransactionModel]:
        """
        Get a transaction by ID (ObjectId or tx_uuid)
        
        Args:
            transaction_id: MongoDB ObjectId or tx_uuid
            
        Returns:
            TransactionModel: Transaction if found, None otherwise
        """
        try:
            collection = await self.get_collection()
            
            # Try to find by ObjectId first
            if ObjectId.is_valid(transaction_id):
                doc = await collection.find_one({"_id": ObjectId(transaction_id)})
            else:
                # Try to find by tx_uuid
                doc = await collection.find_one({"tx_uuid": transaction_id})
            
            if doc:
                return TransactionModel.from_dict(doc)
            return None
            
        except Exception as e:
            logger.error(f"Failed to get transaction {transaction_id}: {e}")
            raise
    
    async def get_transaction_by_uuid(self, tx_uuid: str) -> Optional[TransactionModel]:
        """
        Get a transaction by tx_uuid
        
        Args:
            tx_uuid: Transaction UUID
            
        Returns:
            TransactionModel: Transaction if found, None otherwise
        """
        try:
            collection = await self.get_collection()
            doc = await collection.find_one({"tx_uuid": tx_uuid})
            
            if doc:
                return TransactionModel.from_dict(doc)
            return None
            
        except Exception as e:
            logger.error(f"Failed to get transaction by UUID {tx_uuid}: {e}")
            raise
    
    async def get_transaction_by_hash(self, hash_or_uuid: str) -> Optional[TransactionModel]:
        """
        Get a transaction by hash field or fallback to tx_uuid
        
        Args:
            hash_or_uuid: Transaction hash or UUID to search for
            
        Returns:
            TransactionModel: Transaction if found, None otherwise
        """
        try:
            collection = await self.get_collection()
            
            # First try to find by hash field
            doc = await collection.find_one({"evidence_hash": hash_or_uuid})
            if not doc:
                # Fallback to tx_uuid search
                doc = await collection.find_one({"tx_uuid": hash_or_uuid})
            
            if doc:
                return TransactionModel.from_dict(doc)
            return None
            
        except Exception as e:
            logger.error(f"Failed to get transaction by hash {hash_or_uuid}: {e}")
            raise
    
    async def add_review_audit(self, tx_uuid: str, audit_item: dict) -> bool:
        """
        Add an audit entry to a transaction's reviews array
        
        Args:
            tx_uuid: Transaction UUID
            audit_item: Audit entry to append
            
        Returns:
            bool: True if audit was added successfully
        """
        try:
            collection = await self.get_collection()
            
            # Push to reviews array and update timestamp
            result = await collection.update_one(
                {"tx_uuid": tx_uuid},
                {
                    "$push": {"reviews": audit_item},
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )
            
            success = result.modified_count == 1
            if success:
                logger.info(f"Added audit entry to transaction {tx_uuid}")
            else:
                logger.warning(f"Failed to add audit entry - transaction {tx_uuid} not found")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to add audit entry to transaction {tx_uuid}: {e}")
            raise

    async def list_transactions(
        self, 
        limit: int = 50, 
        skip: int = 0,
        decision: Optional[DecisionEnum] = None,
        wallet_from: Optional[str] = None,
        wallet_to: Optional[str] = None
    ) -> List[TransactionModel]:
        """
        List transactions with optional filtering
        
        Args:
            limit: Maximum number of transactions to return
            skip: Number of transactions to skip
            decision: Filter by decision status
            wallet_from: Filter by source wallet
            wallet_to: Filter by destination wallet
            
        Returns:
            List[TransactionModel]: List of transactions
        """
        try:
            collection = await self.get_collection()
            
            # Build filter query
            filter_query = {}
            if decision:
                filter_query["decision"] = decision.value
            if wallet_from:
                filter_query["wallet_from"] = wallet_from
            if wallet_to:
                filter_query["wallet_to"] = wallet_to
            
            # Execute query with sorting (latest first)
            cursor = collection.find(filter_query).sort("created_at", -1).skip(skip).limit(limit)
            docs = await cursor.to_list(length=limit)
            
            # Convert to models
            transactions = [TransactionModel.from_dict(doc) for doc in docs]
            
            logger.info(f"Retrieved {len(transactions)} transactions")
            return transactions
            
        except Exception as e:
            logger.error(f"Failed to list transactions: {e}")
            raise
    
    async def update_transaction(
        self, 
        transaction_id: str, 
        update_data: dict
    ) -> Optional[TransactionModel]:
        """
        Update a transaction
        
        Args:
            transaction_id: Transaction ID (ObjectId or tx_uuid)
            update_data: Fields to update
            
        Returns:
            TransactionModel: Updated transaction if found, None otherwise
        """
        try:
            collection = await self.get_collection()
            
            # Add updated_at timestamp
            update_data["updated_at"] = datetime.utcnow()
            
            # Determine query based on ID format
            if ObjectId.is_valid(transaction_id):
                query = {"_id": ObjectId(transaction_id)}
            else:
                query = {"tx_uuid": transaction_id}
            
            # Update document
            result = await collection.update_one(
                query,
                {"$set": update_data}
            )
            
            if result.matched_count > 0:
                # Retrieve updated document
                doc = await collection.find_one(query)
                if doc:
                    logger.info(f"Updated transaction: {transaction_id}")
                    return TransactionModel.from_dict(doc)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to update transaction {transaction_id}: {e}")
            raise
    
    async def delete_transaction(self, transaction_id: str) -> bool:
        """
        Delete a transaction
        
        Args:
            transaction_id: Transaction ID (ObjectId or tx_uuid)
            
        Returns:
            bool: True if deleted, False if not found
        """
        try:
            collection = await self.get_collection()
            
            # Determine query based on ID format
            if ObjectId.is_valid(transaction_id):
                query = {"_id": ObjectId(transaction_id)}
            else:
                query = {"tx_uuid": transaction_id}
            
            result = await collection.delete_one(query)
            
            if result.deleted_count > 0:
                logger.info(f"Deleted transaction: {transaction_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to delete transaction {transaction_id}: {e}")
            raise
    
    async def count_transactions(
        self,
        decision: Optional[DecisionEnum] = None
    ) -> int:
        """
        Count transactions with optional filtering
        
        Args:
            decision: Filter by decision status
            
        Returns:
            int: Count of transactions
        """
        try:
            collection = await self.get_collection()
            
            filter_query = {}
            if decision:
                filter_query["decision"] = decision.value
            
            count = await collection.count_documents(filter_query)
            return count
            
        except Exception as e:
            logger.error(f"Failed to count transactions: {e}")
            raise
    
    async def get_transactions_by_wallet(
        self, 
        wallet_address: str, 
        limit: int = 50
    ) -> List[TransactionModel]:
        """
        Get transactions involving a specific wallet
        
        Args:
            wallet_address: Wallet address to search for
            limit: Maximum number of transactions
            
        Returns:
            List[TransactionModel]: Transactions involving the wallet
        """
        try:
            collection = await self.get_collection()
            
            # Find transactions where wallet is either sender or receiver
            query = {
                "$or": [
                    {"wallet_from": wallet_address},
                    {"wallet_to": wallet_address}
                ]
            }
            
            cursor = collection.find(query).sort("created_at", -1).limit(limit)
            docs = await cursor.to_list(length=limit)
            
            transactions = [TransactionModel.from_dict(doc) for doc in docs]
            
            logger.info(f"Retrieved {len(transactions)} transactions for wallet {wallet_address}")
            return transactions
            
        except Exception as e:
            logger.error(f"Failed to get transactions for wallet {wallet_address}: {e}")
            raise
    
    async def get_transactions_for_anchoring(
        self, 
        limit: int = 100
    ) -> List[TransactionModel]:
        """
        Get transactions that need blockchain anchoring
        
        Args:
            limit: Maximum number of transactions
            
        Returns:
            List[TransactionModel]: Transactions ready for anchoring
        """
        try:
            collection = await self.get_collection()
            
            # Find transactions that are decided but not yet anchored
            query = {
                "decision": {"$in": [DecisionEnum.PASS.value, DecisionEnum.HOLD.value, DecisionEnum.REJECT.value]},
                "anchored_root": None
            }
            
            cursor = collection.find(query).sort("updated_at", 1).limit(limit)
            docs = await cursor.to_list(length=limit)
            
            transactions = [TransactionModel.from_dict(doc) for doc in docs]
            
            logger.info(f"Retrieved {len(transactions)} transactions for anchoring")
            return transactions
            
        except Exception as e:
            logger.error(f"Failed to get transactions for anchoring: {e}")
            raise


# Global CRUD instance
transaction_crud = TransactionCRUD()