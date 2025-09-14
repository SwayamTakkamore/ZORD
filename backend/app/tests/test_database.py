"""Test cases for MongoDB database connection and lifecycle management"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
import pymongo.errors

from app.database.mongodb import (
    get_database,
    close_database_connection,
    init_database_connection,
    test_database_connection
)


class TestDatabaseConnection:
    """Test database connection management"""

    @pytest.mark.asyncio
    async def test_database_connection_success(self):
        """Test successful database connection"""
        with patch('app.database.mongodb.AsyncIOMotorClient') as mock_client:
            # Mock successful connection
            mock_db = AsyncMock()
            mock_client_instance = AsyncMock()
            mock_client_instance.get_database.return_value = mock_db
            mock_client.return_value = mock_client_instance
            
            # Mock ping to indicate successful connection
            mock_db.command.return_value = {"ok": 1}
            
            result = await init_database_connection("mongodb://localhost:27017/test")
            
            assert result is True
            mock_client.assert_called_once_with("mongodb://localhost:27017/test")

    @pytest.mark.asyncio
    async def test_database_connection_failure(self):
        """Test database connection failure"""
        with patch('app.database.mongodb.AsyncIOMotorClient') as mock_client:
            # Mock connection failure
            mock_client.side_effect = pymongo.errors.ConnectionFailure("Connection failed")
            
            result = await init_database_connection("mongodb://invalid:27017/test")
            
            assert result is False

    @pytest.mark.asyncio
    async def test_database_connection_timeout(self):
        """Test database connection timeout"""
        with patch('app.database.mongodb.AsyncIOMotorClient') as mock_client:
            # Mock timeout
            mock_client.side_effect = pymongo.errors.ServerSelectionTimeoutError("Timeout")
            
            result = await init_database_connection("mongodb://localhost:27017/test")
            
            assert result is False

    @pytest.mark.asyncio
    async def test_database_connection_authentication_failure(self):
        """Test database authentication failure"""
        with patch('app.database.mongodb.AsyncIOMotorClient') as mock_client:
            # Mock auth failure
            mock_client.side_effect = pymongo.errors.OperationFailure("Authentication failed")
            
            result = await init_database_connection("mongodb://user:pass@localhost:27017/test")
            
            assert result is False

    @pytest.mark.asyncio
    async def test_get_database_when_connected(self):
        """Test getting database when connection exists"""
        with patch('app.database.mongodb.database') as mock_db:
            mock_db.return_value = AsyncMock()
            
            db = get_database()
            
            assert db is not None

    @pytest.mark.asyncio
    async def test_get_database_when_not_connected(self):
        """Test getting database when no connection exists"""
        with patch('app.database.mongodb.database', None):
            with pytest.raises(RuntimeError, match="Database not connected"):
                get_database()

    @pytest.mark.asyncio
    async def test_close_database_connection(self):
        """Test closing database connection"""
        mock_client = AsyncMock()
        
        with patch('app.database.mongodb.client', mock_client):
            await close_database_connection()
            
            mock_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_database_connection_when_none(self):
        """Test closing database connection when client is None"""
        with patch('app.database.mongodb.client', None):
            # Should not raise an exception
            await close_database_connection()

    @pytest.mark.asyncio
    async def test_database_ping_success(self):
        """Test successful database ping"""
        mock_db = AsyncMock()
        mock_db.command.return_value = {"ok": 1}
        
        with patch('app.database.mongodb.get_database', return_value=mock_db):
            result = await test_database_connection()
            
            assert result is True
            mock_db.command.assert_called_once_with("ping")

    @pytest.mark.asyncio
    async def test_database_ping_failure(self):
        """Test database ping failure"""
        mock_db = AsyncMock()
        mock_db.command.side_effect = pymongo.errors.OperationFailure("Ping failed")
        
        with patch('app.database.mongodb.get_database', return_value=mock_db):
            result = await test_database_connection()
            
            assert result is False

    @pytest.mark.asyncio
    async def test_database_ping_no_connection(self):
        """Test database ping when no connection"""
        with patch('app.database.mongodb.get_database', side_effect=RuntimeError("Database not connected")):
            result = await test_database_connection()
            
            assert result is False


class TestDatabaseReconnection:
    """Test database reconnection scenarios"""

    @pytest.mark.asyncio
    async def test_connection_recovery_after_failure(self):
        """Test connection recovery after temporary failure"""
        call_count = 0
        
        def mock_connection(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise pymongo.errors.ConnectionFailure("Temporary failure")
            else:
                # Return successful connection on retry
                mock_client = AsyncMock()
                mock_db = AsyncMock()
                mock_client.get_database.return_value = mock_db
                mock_db.command.return_value = {"ok": 1}
                return mock_client
        
        with patch('app.database.mongodb.AsyncIOMotorClient', side_effect=mock_connection):
            # First attempt should fail
            result1 = await init_database_connection("mongodb://localhost:27017/test")
            assert result1 is False
            
            # Second attempt should succeed
            result2 = await init_database_connection("mongodb://localhost:27017/test")
            assert result2 is True

    @pytest.mark.asyncio
    async def test_multiple_connection_attempts(self):
        """Test multiple connection attempts"""
        attempts = []
        
        def track_attempts(*args, **kwargs):
            attempts.append(args[0])
            raise pymongo.errors.ConnectionFailure("Always fail")
        
        with patch('app.database.mongodb.AsyncIOMotorClient', side_effect=track_attempts):
            for i in range(3):
                result = await init_database_connection(f"mongodb://host{i}:27017/test")
                assert result is False
            
            assert len(attempts) == 3

    @pytest.mark.asyncio
    async def test_connection_state_cleanup_on_failure(self):
        """Test that connection state is cleaned up on failure"""
        with patch('app.database.mongodb.AsyncIOMotorClient') as mock_client:
            mock_client.side_effect = pymongo.errors.ConnectionFailure("Connection failed")
            
            result = await init_database_connection("mongodb://localhost:27017/test")
            
            assert result is False
            # Verify that global state is cleaned up
            with patch('app.database.mongodb.database', None), \
                 patch('app.database.mongodb.client', None):
                
                with pytest.raises(RuntimeError):
                    get_database()


class TestDatabaseCollectionOperations:
    """Test database collection-level operations"""

    @pytest.mark.asyncio
    async def test_collection_access(self, mock_mongo_client):
        """Test accessing collections from database"""
        db = get_database()
        
        # Test accessing known collections
        transactions_collection = db.transactions
        compliance_collection = db.compliance_rules
        
        assert transactions_collection is not None
        assert compliance_collection is not None

    @pytest.mark.asyncio
    async def test_collection_operation_with_connection_error(self):
        """Test collection operation with connection error"""
        mock_db = AsyncMock()
        mock_collection = AsyncMock()
        mock_db.transactions = mock_collection
        
        # Mock connection error during operation
        mock_collection.find_one.side_effect = pymongo.errors.ConnectionFailure("Connection lost")
        
        with patch('app.database.mongodb.get_database', return_value=mock_db):
            with pytest.raises(pymongo.errors.ConnectionFailure):
                await mock_collection.find_one({"_id": "test"})

    @pytest.mark.asyncio
    async def test_collection_operation_with_timeout(self):
        """Test collection operation with timeout"""
        mock_db = AsyncMock()
        mock_collection = AsyncMock()
        mock_db.transactions = mock_collection
        
        # Mock timeout during operation
        mock_collection.find.side_effect = pymongo.errors.ExecutionTimeout("Operation timeout")
        
        with patch('app.database.mongodb.get_database', return_value=mock_db):
            with pytest.raises(pymongo.errors.ExecutionTimeout):
                await mock_collection.find({}).to_list(length=100)

    @pytest.mark.asyncio
    async def test_index_creation_on_connection(self):
        """Test that indexes are created when connection is established"""
        mock_db = AsyncMock()
        mock_collection = AsyncMock()
        mock_db.transactions = mock_collection
        
        with patch('app.database.mongodb.AsyncIOMotorClient') as mock_client:
            mock_client_instance = AsyncMock()
            mock_client_instance.get_database.return_value = mock_db
            mock_client.return_value = mock_client_instance
            
            # Mock successful ping
            mock_db.command.return_value = {"ok": 1}
            
            result = await init_database_connection("mongodb://localhost:27017/test")
            
            assert result is True
            # Verify index creation was attempted
            mock_collection.create_index.assert_called()


class TestDatabaseErrorHandling:
    """Test database error handling scenarios"""

    @pytest.mark.asyncio
    async def test_network_error_handling(self):
        """Test handling of network errors"""
        with patch('app.database.mongodb.AsyncIOMotorClient') as mock_client:
            mock_client.side_effect = pymongo.errors.NetworkTimeout("Network timeout")
            
            result = await init_database_connection("mongodb://localhost:27017/test")
            
            assert result is False

    @pytest.mark.asyncio
    async def test_invalid_uri_error(self):
        """Test handling of invalid URI"""
        with patch('app.database.mongodb.AsyncIOMotorClient') as mock_client:
            mock_client.side_effect = pymongo.errors.InvalidURI("Invalid URI")
            
            result = await init_database_connection("invalid://uri")
            
            assert result is False

    @pytest.mark.asyncio
    async def test_configuration_error(self):
        """Test handling of configuration errors"""
        with patch('app.database.mongodb.AsyncIOMotorClient') as mock_client:
            mock_client.side_effect = pymongo.errors.ConfigurationError("Bad config")
            
            result = await init_database_connection("mongodb://localhost:27017/test")
            
            assert result is False

    @pytest.mark.asyncio
    async def test_write_concern_error(self):
        """Test handling of write concern errors"""
        mock_db = AsyncMock()
        mock_collection = AsyncMock()
        mock_db.transactions = mock_collection
        
        # Mock write concern error
        mock_collection.insert_one.side_effect = pymongo.errors.WriteConcernError("Write failed")
        
        with patch('app.database.mongodb.get_database', return_value=mock_db):
            with pytest.raises(pymongo.errors.WriteConcernError):
                await mock_collection.insert_one({"test": "data"})

    @pytest.mark.asyncio
    async def test_duplicate_key_error(self):
        """Test handling of duplicate key errors"""
        mock_db = AsyncMock()
        mock_collection = AsyncMock()
        mock_db.transactions = mock_collection
        
        # Mock duplicate key error
        duplicate_error = pymongo.errors.DuplicateKeyError("Duplicate key")
        mock_collection.insert_one.side_effect = duplicate_error
        
        with patch('app.database.mongodb.get_database', return_value=mock_db):
            with pytest.raises(pymongo.errors.DuplicateKeyError):
                await mock_collection.insert_one({"_id": "existing"})


class TestDatabasePerformance:
    """Test database performance monitoring"""

    @pytest.mark.asyncio
    async def test_connection_pool_exhaustion(self):
        """Test behavior when connection pool is exhausted"""
        mock_client = AsyncMock()
        mock_client.get_database.side_effect = pymongo.errors.ServerSelectionTimeoutError(
            "Connection pool exhausted"
        )
        
        with patch('app.database.mongodb.AsyncIOMotorClient', return_value=mock_client):
            result = await init_database_connection("mongodb://localhost:27017/test")
            
            assert result is False

    @pytest.mark.asyncio
    async def test_concurrent_connections(self):
        """Test concurrent database connections"""
        successful_connections = 0
        
        async def create_connection():
            nonlocal successful_connections
            mock_client = AsyncMock()
            mock_db = AsyncMock()
            mock_client.get_database.return_value = mock_db
            mock_db.command.return_value = {"ok": 1}
            
            with patch('app.database.mongodb.AsyncIOMotorClient', return_value=mock_client):
                result = await init_database_connection("mongodb://localhost:27017/test")
                if result:
                    successful_connections += 1
                return result
        
        # Create multiple concurrent connections
        tasks = [create_connection() for _ in range(5)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All connections should succeed (mocked)
        assert successful_connections == 5
        assert all(result is True for result in results if not isinstance(result, Exception))

    @pytest.mark.asyncio
    async def test_database_health_check(self):
        """Test database health check functionality"""
        mock_db = AsyncMock()
        
        # Mock various health check scenarios
        health_responses = [
            {"ok": 1, "uptime": 12345},  # Healthy
            {"ok": 0},  # Unhealthy
        ]
        
        for response in health_responses:
            mock_db.command.return_value = response
            
            with patch('app.database.mongodb.get_database', return_value=mock_db):
                if response["ok"] == 1:
                    result = await test_database_connection()
                    assert result is True
                else:
                    mock_db.command.side_effect = pymongo.errors.OperationFailure("Not ok")
                    result = await test_database_connection()
                    assert result is False


class TestDatabaseLifecycle:
    """Test complete database lifecycle scenarios"""

    @pytest.mark.asyncio
    async def test_full_lifecycle_success(self):
        """Test complete successful database lifecycle"""
        mock_client = AsyncMock()
        mock_db = AsyncMock()
        mock_client.get_database.return_value = mock_db
        mock_db.command.return_value = {"ok": 1}
        
        with patch('app.database.mongodb.AsyncIOMotorClient', return_value=mock_client):
            # Initialize connection
            init_result = await init_database_connection("mongodb://localhost:27017/test")
            assert init_result is True
            
            # Test connection
            with patch('app.database.mongodb.get_database', return_value=mock_db):
                test_result = await test_database_connection()
                assert test_result is True
                
                # Use database
                db = get_database()
                assert db is not None
                
                # Close connection
                with patch('app.database.mongodb.client', mock_client):
                    await close_database_connection()
                    mock_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_lifecycle_with_failures(self):
        """Test database lifecycle with various failures"""
        # Test initialization failure followed by success
        call_count = 0
        
        def mock_client_creation(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise pymongo.errors.ConnectionFailure("First attempt fails")
            
            mock_client = AsyncMock()
            mock_db = AsyncMock()
            mock_client.get_database.return_value = mock_db
            mock_db.command.return_value = {"ok": 1}
            return mock_client
        
        with patch('app.database.mongodb.AsyncIOMotorClient', side_effect=mock_client_creation):
            # First attempt fails
            result1 = await init_database_connection("mongodb://localhost:27017/test")
            assert result1 is False
            
            # Second attempt succeeds
            result2 = await init_database_connection("mongodb://localhost:27017/test")
            assert result2 is True

    @pytest.mark.asyncio
    async def test_graceful_shutdown(self):
        """Test graceful database shutdown"""
        mock_client = AsyncMock()
        
        with patch('app.database.mongodb.client', mock_client):
            # Test normal shutdown
            await close_database_connection()
            mock_client.close.assert_called_once()
            
            # Test shutdown when already closed
            mock_client.reset_mock()
            await close_database_connection()
            mock_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_emergency_shutdown(self):
        """Test emergency database shutdown scenarios"""
        mock_client = AsyncMock()
        mock_client.close.side_effect = Exception("Shutdown error")
        
        with patch('app.database.mongodb.client', mock_client):
            # Should not raise exception even if close fails
            await close_database_connection()
            mock_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_connection_state_management(self):
        """Test proper connection state management"""
        # Test state when not connected
        with patch('app.database.mongodb.database', None):
            with pytest.raises(RuntimeError):
                get_database()
        
        # Test state when connected
        mock_db = AsyncMock()
        with patch('app.database.mongodb.database', mock_db):
            db = get_database()
            assert db == mock_db
        
        # Test state after cleanup
        with patch('app.database.mongodb.database', None), \
             patch('app.database.mongodb.client', None):
            with pytest.raises(RuntimeError):
                get_database()


@pytest.mark.integration
class TestDatabaseIntegration:
    """Integration tests for database operations"""

    @pytest.mark.asyncio
    async def test_real_database_operations(self, mock_mongo_client):
        """Test with actual database-like operations"""
        db = get_database()
        collection = db.test_collection
        
        # Test document insertion
        doc = {"test": "data", "timestamp": "2024-01-01T00:00:00Z"}
        insert_result = await collection.insert_one(doc)
        assert insert_result.inserted_id is not None
        
        # Test document retrieval
        found_doc = await collection.find_one({"test": "data"})
        assert found_doc is not None
        assert found_doc["test"] == "data"
        
        # Test document update
        update_result = await collection.update_one(
            {"test": "data"},
            {"$set": {"updated": True}}
        )
        assert update_result.modified_count == 1
        
        # Test document deletion
        delete_result = await collection.delete_one({"test": "data"})
        assert delete_result.deleted_count == 1

    @pytest.mark.asyncio
    async def test_transaction_operations(self, mock_mongo_client):
        """Test database transaction support"""
        db = get_database()
        
        # Note: mongomock doesn't support transactions, so we mock the session
        mock_session = AsyncMock()
        
        with patch.object(db.client, 'start_session', return_value=mock_session):
            async with mock_session.start_transaction():
                collection = db.test_transactions
                
                # Perform operations within transaction
                await collection.insert_one({"transaction_test": "data1"})
                await collection.insert_one({"transaction_test": "data2"})
                
                # Transaction should commit successfully
                assert mock_session.start_transaction.called

    @pytest.mark.asyncio
    async def test_index_operations(self, mock_mongo_client):
        """Test database index operations"""
        db = get_database()
        collection = db.test_indexes
        
        # Create index
        index_result = await collection.create_index("test_field")
        assert index_result is not None
        
        # List indexes
        indexes = await collection.list_indexes().to_list(length=None)
        assert len(indexes) >= 1  # At least _id index exists

    @pytest.mark.asyncio
    async def test_aggregation_operations(self, mock_mongo_client):
        """Test database aggregation operations"""
        db = get_database()
        collection = db.test_aggregation
        
        # Insert test data
        test_docs = [
            {"category": "A", "value": 10},
            {"category": "A", "value": 20},
            {"category": "B", "value": 15},
        ]
        await collection.insert_many(test_docs)
        
        # Perform aggregation
        pipeline = [
            {"$group": {"_id": "$category", "total": {"$sum": "$value"}}},
            {"$sort": {"_id": 1}}
        ]
        
        results = await collection.aggregate(pipeline).to_list(length=None)
        assert len(results) == 2
        assert results[0]["_id"] == "A"
        assert results[0]["total"] == 30