"""MongoDB connection and database management using Motor"""

import os
import logging
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection
from pymongo.errors import ServerSelectionTimeoutError
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class MongoDB:
    """MongoDB connection manager using Motor async driver"""
    
    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.database: Optional[AsyncIOMotorDatabase] = None
        
    async def connect(self) -> None:
        """Initialize MongoDB connection"""
        try:
            # Get connection string from environment
            mongo_uri = os.getenv("MONGO_URI")
            if not mongo_uri:
                raise ValueError("MONGO_URI environment variable is required")
                
            db_name = os.getenv("MONGO_DB", "compliance")
            
            # Create Motor client
            self.client = AsyncIOMotorClient(
                mongo_uri,
                serverSelectionTimeoutMS=5000,  # 5 second timeout
                retryWrites=True
            )
            
            # Test connection
            await self.client.admin.command('ping')
            logger.info(f"Successfully connected to MongoDB at {mongo_uri}")
            
            # Get database
            self.database = self.client[db_name]
            logger.info(f"Using database: {db_name}")
            
        except ServerSelectionTimeoutError as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error connecting to MongoDB: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            logger.info("Disconnected from MongoDB")
    
    def get_collection(self, collection_name: str) -> AsyncIOMotorCollection:
        """
        Get a MongoDB collection
        
        Args:
            collection_name: Name of the collection
            
        Returns:
            AsyncIOMotorCollection: Collection instance
            
        Raises:
            RuntimeError: If database is not connected
        """
        if self.database is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        
        return self.database[collection_name]
    
    async def create_indexes(self) -> None:
        """Create necessary database indexes for performance"""
        if self.database is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        
        try:
            # Transaction collection indexes
            transactions = self.get_collection("transactions")
            
            # Create indexes for frequently queried fields
            await transactions.create_index("tx_uuid", unique=True)
            await transactions.create_index("wallet_from")
            await transactions.create_index("wallet_to")
            await transactions.create_index("decision")
            await transactions.create_index("created_at")
            await transactions.create_index([("created_at", -1)])  # Descending for latest-first queries
            
            # Composite indexes for common query patterns
            await transactions.create_index([("wallet_from", 1), ("decision", 1)])
            await transactions.create_index([("wallet_to", 1), ("decision", 1)])
            
            # User collection indexes
            users = self.get_collection("users")
            
            # Create unique indexes for user authentication
            await users.create_index("email", unique=True)
            await users.create_index("username", unique=True)
            await users.create_index("created_at")
            await users.create_index("last_login")
            await users.create_index("role")
            
            logger.info("Successfully created database indexes for transactions and users")
            
        except Exception as e:
            logger.error(f"Failed to create indexes: {e}")
            raise

# Global MongoDB instance
mongodb = MongoDB()

async def get_database() -> AsyncIOMotorDatabase:
    """
    Dependency to get database instance
    
    Returns:
        AsyncIOMotorDatabase: Database instance
        
    Raises:
        RuntimeError: If database is not connected
    """
    if mongodb.database is None:
        raise RuntimeError("Database not connected. Ensure MongoDB is initialized.")
    
    return mongodb.database

async def get_collection(collection_name: str) -> AsyncIOMotorCollection:
    """
    Dependency to get collection instance
    
    Args:
        collection_name: Name of the collection
        
    Returns:
        AsyncIOMotorCollection: Collection instance
    """
    return mongodb.get_collection(collection_name)

# Startup and shutdown event handlers
async def connect_to_mongo():
    """Connect to MongoDB on application startup"""
    await mongodb.connect()
    await mongodb.create_indexes()

async def close_mongo_connection():
    """Close MongoDB connection on application shutdown"""
    await mongodb.disconnect()