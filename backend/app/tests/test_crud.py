"""Test cases for MongoDB CRUD operations in transaction_crud.py"""

import pytest
import uuid
from decimal import Decimal
from bson import ObjectId
from pymongo.errors import DuplicateKeyError

from app.services.transaction_crud import transaction_crud
from app.models.transaction import TransactionModel, DecisionEnum


@pytest.mark.asyncio
class TestTransactionCRUD:
    """Test class for transaction CRUD operations"""

    async def test_create_transaction_success(self, clean_database, mock_transaction_data):
        """Test successful transaction creation"""
        tx_data = mock_transaction_data.create_valid_transaction()
        
        created_tx = await transaction_crud.create_transaction(tx_data)
        
        assert created_tx.id is not None
        assert isinstance(created_tx.id, ObjectId)
        assert created_tx.wallet_from == tx_data["wallet_from"]
        assert created_tx.wallet_to == tx_data["wallet_to"]
        assert created_tx.amount == tx_data["amount"]
        assert created_tx.currency == tx_data["currency"]
        assert created_tx.decision == tx_data["decision"]
        assert created_tx.created_at is not None
        assert created_tx.updated_at is not None

    async def test_create_transaction_with_minimal_data(self, clean_database):
        """Test transaction creation with minimal required data"""
        minimal_data = {
            "wallet_from": "0x1111111111111111111111111111111111111111",
            "wallet_to": "0x2222222222222222222222222222222222222222", 
            "amount": Decimal("50.0")
        }
        
        created_tx = await transaction_crud.create_transaction(minimal_data)
        
        assert created_tx.currency == "ETH"  # Default value
        assert created_tx.decision == DecisionEnum.PENDING  # Default value
        assert created_tx.kyc_proof_id is None

    async def test_create_transaction_duplicate_uuid(self, clean_database, mock_transaction_data):
        """Test handling of duplicate transaction UUID"""
        tx_data = mock_transaction_data.create_valid_transaction()
        fixed_uuid = str(uuid.uuid4())
        tx_data["tx_uuid"] = fixed_uuid
        
        # Create first transaction
        await transaction_crud.create_transaction(tx_data)
        
        # Try to create second transaction with same UUID
        with pytest.raises(DuplicateKeyError):
            await transaction_crud.create_transaction(tx_data)

    async def test_get_transaction_by_id(self, clean_database, sample_transaction):
        """Test retrieving transaction by ObjectId"""
        retrieved_tx = await transaction_crud.get_transaction(str(sample_transaction.id))
        
        assert retrieved_tx is not None
        assert retrieved_tx.id == sample_transaction.id
        assert retrieved_tx.tx_uuid == sample_transaction.tx_uuid

    async def test_get_transaction_by_uuid(self, clean_database, sample_transaction):
        """Test retrieving transaction by tx_uuid"""
        retrieved_tx = await transaction_crud.get_transaction(sample_transaction.tx_uuid)
        
        assert retrieved_tx is not None
        assert retrieved_tx.id == sample_transaction.id
        assert retrieved_tx.tx_uuid == sample_transaction.tx_uuid

    async def test_get_transaction_not_found(self, clean_database):
        """Test retrieving non-existent transaction"""
        fake_id = str(ObjectId())
        fake_uuid = str(uuid.uuid4())
        
        # Test with ObjectId
        result1 = await transaction_crud.get_transaction(fake_id)
        assert result1 is None
        
        # Test with UUID
        result2 = await transaction_crud.get_transaction(fake_uuid)
        assert result2 is None

    async def test_get_transaction_by_uuid_specific(self, clean_database, sample_transaction):
        """Test get_transaction_by_uuid method specifically"""
        retrieved_tx = await transaction_crud.get_transaction_by_uuid(sample_transaction.tx_uuid)
        
        assert retrieved_tx is not None
        assert retrieved_tx.tx_uuid == sample_transaction.tx_uuid

    async def test_list_transactions_empty(self, clean_database):
        """Test listing transactions when database is empty"""
        transactions = await transaction_crud.list_transactions()
        
        assert transactions == []

    async def test_list_transactions_with_data(self, clean_database, multiple_transactions):
        """Test listing transactions with data"""
        transactions = await transaction_crud.list_transactions()
        
        assert len(transactions) == len(multiple_transactions)
        # Should be ordered by created_at descending (newest first)
        assert transactions[0].created_at >= transactions[-1].created_at

    async def test_list_transactions_pagination(self, clean_database, multiple_transactions):
        """Test transaction listing with pagination"""
        # Test limit
        limited_txs = await transaction_crud.list_transactions(limit=2)
        assert len(limited_txs) == 2
        
        # Test skip
        skipped_txs = await transaction_crud.list_transactions(limit=2, skip=2)
        assert len(skipped_txs) == 2
        
        # Ensure different results
        assert limited_txs[0].id != skipped_txs[0].id

    async def test_list_transactions_filter_by_decision(self, clean_database, mock_transaction_data):
        """Test filtering transactions by decision"""
        # Create transactions with different decisions
        tx_pass = mock_transaction_data.create_valid_transaction(decision=DecisionEnum.PASS)
        tx_hold = mock_transaction_data.create_valid_transaction(decision=DecisionEnum.HOLD)
        
        await transaction_crud.create_transaction(tx_pass)
        await transaction_crud.create_transaction(tx_hold)
        
        # Filter by PASS
        pass_txs = await transaction_crud.list_transactions(decision=DecisionEnum.PASS)
        assert len(pass_txs) == 1
        assert pass_txs[0].decision == DecisionEnum.PASS
        
        # Filter by HOLD
        hold_txs = await transaction_crud.list_transactions(decision=DecisionEnum.HOLD)
        assert len(hold_txs) == 1
        assert hold_txs[0].decision == DecisionEnum.HOLD

    async def test_list_transactions_filter_by_wallet(self, clean_database, mock_transaction_data):
        """Test filtering transactions by wallet addresses"""
        wallet_a = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        wallet_b = "0xBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB"
        
        # Create transactions with specific wallets
        tx1 = mock_transaction_data.create_valid_transaction(wallet_from=wallet_a)
        tx2 = mock_transaction_data.create_valid_transaction(wallet_to=wallet_b)
        
        await transaction_crud.create_transaction(tx1)
        await transaction_crud.create_transaction(tx2)
        
        # Filter by wallet_from
        from_txs = await transaction_crud.list_transactions(wallet_from=wallet_a)
        assert len(from_txs) == 1
        assert from_txs[0].wallet_from == wallet_a
        
        # Filter by wallet_to
        to_txs = await transaction_crud.list_transactions(wallet_to=wallet_b)
        assert len(to_txs) == 1
        assert to_txs[0].wallet_to == wallet_b

    async def test_update_transaction_by_id(self, clean_database, sample_transaction):
        """Test updating transaction by ObjectId"""
        update_data = {
            "decision": DecisionEnum.PASS.value,
            "review_reason": "Approved after manual review"
        }
        
        updated_tx = await transaction_crud.update_transaction(
            str(sample_transaction.id), 
            update_data
        )
        
        assert updated_tx is not None
        assert updated_tx.decision == DecisionEnum.PASS
        assert updated_tx.updated_at > sample_transaction.updated_at

    async def test_update_transaction_by_uuid(self, clean_database, sample_transaction):
        """Test updating transaction by tx_uuid"""
        update_data = {
            "decision": DecisionEnum.REJECT.value,
            "evidence_hash": "new_evidence_hash"
        }
        
        updated_tx = await transaction_crud.update_transaction(
            sample_transaction.tx_uuid,
            update_data
        )
        
        assert updated_tx is not None
        assert updated_tx.decision == DecisionEnum.REJECT
        assert updated_tx.evidence_hash == "new_evidence_hash"

    async def test_update_transaction_not_found(self, clean_database):
        """Test updating non-existent transaction"""
        fake_uuid = str(uuid.uuid4())
        update_data = {"decision": DecisionEnum.PASS.value}
        
        result = await transaction_crud.update_transaction(fake_uuid, update_data)
        
        assert result is None

    async def test_delete_transaction_by_id(self, clean_database, sample_transaction):
        """Test deleting transaction by ObjectId"""
        success = await transaction_crud.delete_transaction(str(sample_transaction.id))
        
        assert success is True
        
        # Verify deletion
        deleted_tx = await transaction_crud.get_transaction(str(sample_transaction.id))
        assert deleted_tx is None

    async def test_delete_transaction_by_uuid(self, clean_database, sample_transaction):
        """Test deleting transaction by tx_uuid"""
        success = await transaction_crud.delete_transaction(sample_transaction.tx_uuid)
        
        assert success is True
        
        # Verify deletion
        deleted_tx = await transaction_crud.get_transaction_by_uuid(sample_transaction.tx_uuid)
        assert deleted_tx is None

    async def test_delete_transaction_not_found(self, clean_database):
        """Test deleting non-existent transaction"""
        fake_uuid = str(uuid.uuid4())
        
        success = await transaction_crud.delete_transaction(fake_uuid)
        
        assert success is False

    async def test_count_transactions_empty(self, clean_database):
        """Test counting transactions when database is empty"""
        count = await transaction_crud.count_transactions()
        
        assert count == 0

    async def test_count_transactions_with_data(self, clean_database, multiple_transactions):
        """Test counting transactions with data"""
        count = await transaction_crud.count_transactions()
        
        assert count == len(multiple_transactions)

    async def test_count_transactions_filter_by_decision(self, clean_database, mock_transaction_data):
        """Test counting transactions filtered by decision"""
        # Create transactions with different decisions
        for decision in [DecisionEnum.PASS, DecisionEnum.HOLD, DecisionEnum.PASS]:
            tx_data = mock_transaction_data.create_valid_transaction(decision=decision)
            await transaction_crud.create_transaction(tx_data)
        
        total_count = await transaction_crud.count_transactions()
        pass_count = await transaction_crud.count_transactions(DecisionEnum.PASS)
        hold_count = await transaction_crud.count_transactions(DecisionEnum.HOLD)
        
        assert total_count == 3
        assert pass_count == 2
        assert hold_count == 1

    async def test_get_transactions_by_wallet(self, clean_database, mock_transaction_data):
        """Test getting transactions involving a specific wallet"""
        target_wallet = "0x1234567890123456789012345678901234567890"
        
        # Create transactions with target wallet as sender and receiver
        tx1 = mock_transaction_data.create_valid_transaction(wallet_from=target_wallet)
        tx2 = mock_transaction_data.create_valid_transaction(wallet_to=target_wallet)
        tx3 = mock_transaction_data.create_valid_transaction()  # Unrelated transaction
        
        await transaction_crud.create_transaction(tx1)
        await transaction_crud.create_transaction(tx2)
        await transaction_crud.create_transaction(tx3)
        
        wallet_txs = await transaction_crud.get_transactions_by_wallet(target_wallet)
        
        assert len(wallet_txs) == 2
        for tx in wallet_txs:
            assert tx.wallet_from == target_wallet or tx.wallet_to == target_wallet

    async def test_get_transactions_for_anchoring(self, clean_database, mock_transaction_data):
        """Test getting transactions ready for blockchain anchoring"""
        # Create transactions with different statuses
        pending_tx = mock_transaction_data.create_valid_transaction(decision=DecisionEnum.PENDING)
        pass_tx = mock_transaction_data.create_valid_transaction(decision=DecisionEnum.PASS)
        hold_tx = mock_transaction_data.create_valid_transaction(decision=DecisionEnum.HOLD)
        anchored_tx = mock_transaction_data.create_valid_transaction(
            decision=DecisionEnum.PASS,
            anchored_root="0x1234567890abcdef"
        )
        
        await transaction_crud.create_transaction(pending_tx)
        await transaction_crud.create_transaction(pass_tx)
        await transaction_crud.create_transaction(hold_tx)
        await transaction_crud.create_transaction(anchored_tx)
        
        anchor_ready_txs = await transaction_crud.get_transactions_for_anchoring()
        
        # Should only include decided transactions that aren't yet anchored
        assert len(anchor_ready_txs) == 2  # pass_tx and hold_tx
        for tx in anchor_ready_txs:
            assert tx.decision in [DecisionEnum.PASS, DecisionEnum.HOLD, DecisionEnum.REJECT]
            assert tx.anchored_root is None

    async def test_transaction_model_serialization(self, clean_database, sample_transaction):
        """Test transaction model serialization methods"""
        # Test to_dict method
        tx_dict = sample_transaction.to_dict()
        assert isinstance(tx_dict, dict)
        assert "_id" in tx_dict
        assert isinstance(tx_dict["amount"], float)  # Decimal converted to float
        
        # Test from_dict method
        recreated_tx = TransactionModel.from_dict(tx_dict)
        assert recreated_tx.id == sample_transaction.id
        assert recreated_tx.tx_uuid == sample_transaction.tx_uuid
        assert isinstance(recreated_tx.amount, Decimal)  # Float converted back to Decimal

    async def test_concurrent_operations(self, clean_database, mock_transaction_data):
        """Test concurrent CRUD operations"""
        import asyncio
        
        # Create multiple transactions concurrently
        tasks = []
        for i in range(10):
            tx_data = mock_transaction_data.create_valid_transaction(
                wallet_from=f"0x{i:040x}",
                amount=Decimal(str(100 + i))
            )
            tasks.append(transaction_crud.create_transaction(tx_data))
        
        created_txs = await asyncio.gather(*tasks)
        
        assert len(created_txs) == 10
        assert len(set(tx.tx_uuid for tx in created_txs)) == 10  # All unique UUIDs
        
        # Verify all transactions were created
        total_count = await transaction_crud.count_transactions()
        assert total_count == 10