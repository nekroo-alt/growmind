"""
Unit tests for transaction support system.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

from core.transactions import (
    Transaction,
    TransactionManager,
    TransactionState,
    TransactionMetadata,
    create_transaction_manager,
    with_transaction,
    set_transaction_manager,
    get_transaction_manager,
)


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests"""
    temp = tempfile.mkdtemp()
    yield Path(temp)
    shutil.rmtree(temp)


@pytest.fixture
def mock_checkpoint_manager():
    """Create mock checkpoint manager"""
    manager = Mock(spec=object)
    manager.create = Mock(return_value="checkpoint_123")
    manager.restore = Mock()
    return manager


@pytest.fixture
def mock_telemetry_manager():
    """Create mock telemetry manager"""
    manager = Mock(spec=object)

    # Mock operation tracking
    mock_op = Mock()
    mock_op.id = "op_123"
    mock_op.record_event = Mock()
    mock_op.record_metric = Mock()

    manager.track_operation = Mock(return_value=mock_op)
    manager.get_operation = Mock(return_value=mock_op)

    return manager


@pytest.fixture
def transaction_manager(mock_checkpoint_manager, mock_telemetry_manager):
    """Create transaction manager for tests"""
    return create_transaction_manager(mock_checkpoint_manager, mock_telemetry_manager)


class TestTransaction:
    """Test Transaction class"""

    def test_transaction_creation(
        self, mock_checkpoint_manager, mock_telemetry_manager
    ):
        """Test creating a transaction"""
        tx = Transaction(
            transaction_id="test-tx",
            checkpoint_manager=mock_checkpoint_manager,
            telemetry_manager=mock_telemetry_manager,
        )

        assert tx.id == "test-tx"
        assert tx.state == TransactionState.PENDING
        assert tx.is_active
        assert tx.parent_id is None

    def test_transaction_with_parent(
        self, mock_checkpoint_manager, mock_telemetry_manager
    ):
        """Test creating a transaction with parent"""
        tx = Transaction(
            transaction_id="child-tx",
            checkpoint_manager=mock_checkpoint_manager,
            telemetry_manager=mock_telemetry_manager,
            parent_id="parent-tx",
        )

        assert tx.id == "child-tx"
        assert tx.parent_id == "parent-tx"

    def test_record_step_success(self, mock_checkpoint_manager, mock_telemetry_manager):
        """Test recording a successful step"""
        tx = Transaction(
            transaction_id="test-tx",
            checkpoint_manager=mock_checkpoint_manager,
            telemetry_manager=mock_telemetry_manager,
        )

        tx.record_step("step1", True)
        assert "step1" in tx._metadata.steps_completed
        assert "step1" not in tx._metadata.steps_failed

    def test_record_step_failure(self, mock_checkpoint_manager, mock_telemetry_manager):
        """Test recording a failed step"""
        tx = Transaction(
            transaction_id="test-tx",
            checkpoint_manager=mock_checkpoint_manager,
            telemetry_manager=mock_telemetry_manager,
        )

        tx.record_step("step1", False)
        assert "step1" in tx._metadata.steps_failed
        assert "step1" not in tx._metadata.steps_completed

    def test_get_metadata(self, mock_checkpoint_manager, mock_telemetry_manager):
        """Test getting transaction metadata"""
        tx = Transaction(
            transaction_id="test-tx",
            checkpoint_manager=mock_checkpoint_manager,
            telemetry_manager=mock_telemetry_manager,
        )

        tx.record_step("step1", True)
        tx.record_step("step2", False)

        metadata = tx.get_metadata()
        assert isinstance(metadata, TransactionMetadata)
        assert metadata.transaction_id == "test-tx"
        assert len(metadata.steps_completed) == 1
        assert len(metadata.steps_failed) == 1


class TestTransactionManager:
    """Test TransactionManager class"""

    def test_manager_creation(self, transaction_manager):
        """Test creating transaction manager"""
        assert transaction_manager is not None
        assert len(transaction_manager._transactions) == 0
        assert len(transaction_manager._active_transactions) == 0

    def test_start_transaction(self, transaction_manager):
        """Test starting a transaction"""
        with transaction_manager.start("test_reason") as tx:
            assert tx is not None
            assert tx.state == TransactionState.PENDING
            assert tx.is_active
            assert tx.id in transaction_manager._transactions

    def test_auto_commit_on_success(self, transaction_manager):
        """Test that transaction auto-commits on success"""
        with transaction_manager.start("test_reason") as tx:
            tx.record_step("step1", True)

        assert tx.state == TransactionState.COMMITTED
        assert not tx.is_active
        assert tx.id not in transaction_manager._active_transactions

    def test_auto_rollback_on_exception(
        self, transaction_manager, mock_checkpoint_manager
    ):
        """Test that transaction auto-rolls back on exception"""
        with pytest.raises(ValueError, match="Test error"):
            with transaction_manager.start("test_reason") as tx:
                tx.record_step("step1", True)
                raise ValueError("Test error")

        assert tx.state == TransactionState.ROLLED_BACK
        assert not tx.is_active
        # Verify checkpoint restore was called
        mock_checkpoint_manager.restore.assert_called_once()

    def test_manual_commit(self, transaction_manager):
        """Test manual commit"""
        with transaction_manager.start("test_reason") as tx:
            tx.record_step("step1", True)
            tx.commit()

        assert tx.state == TransactionState.COMMITTED

    def test_manual_rollback(self, transaction_manager, mock_checkpoint_manager):
        """Test manual rollback"""
        with transaction_manager.start("test_reason") as tx:
            tx.record_step("step1", True)
            tx.rollback("Manual reason")

        assert tx.state == TransactionState.ROLLED_BACK
        # Verify checkpoint restore was called
        mock_checkpoint_manager.restore.assert_called_once()

    def test_get_transaction(self, transaction_manager):
        """Test getting a transaction by ID"""
        with transaction_manager.start("test_reason") as tx:
            retrieved = transaction_manager.get_transaction(tx.id)
            assert retrieved is tx

    def test_get_active_transaction(self, transaction_manager):
        """Test getting active transaction"""
        with transaction_manager.start("test_reason"):
            active = transaction_manager.get_active_transaction()
            assert active is not None
            assert active.state == TransactionState.PENDING

    def test_list_transactions_all(self, transaction_manager):
        """Test listing all transactions"""
        with transaction_manager.start("test1") as tx1:
            tx1.record_step("step1", True)

        with transaction_manager.start("test2") as tx2:
            tx2.record_step("step1", True)

        transactions = transaction_manager.list_transactions()
        assert len(transactions) == 2

    def test_list_transactions_filtered(self, transaction_manager):
        """Test listing transactions filtered by state"""
        with transaction_manager.start("test1") as tx1:
            tx1.record_step("step1", True)

        with pytest.raises(ValueError):
            with transaction_manager.start("test2") as tx2:
                raise ValueError("Test error")

        committed = transaction_manager.list_transactions(TransactionState.COMMITTED)
        rolled_back = transaction_manager.list_transactions(
            TransactionState.ROLLED_BACK
        )

        assert len(committed) == 1
        assert len(rolled_back) == 1

    def test_transaction_stats(self, transaction_manager):
        """Test getting transaction statistics"""
        with transaction_manager.start("test1") as tx1:
            tx1.record_step("step1", True)

        with pytest.raises(ValueError):
            with transaction_manager.start("test2") as tx2:
                raise ValueError("Test error")

        stats = transaction_manager.get_transaction_stats()
        assert stats["total_transactions"] == 2
        assert stats["by_state"]["committed"] == 1
        assert stats["by_state"]["rolled_back"] == 1
        assert stats["by_state"]["pending"] == 0


class TestNestedTransactions:
    """Test nested transaction support"""

    def test_nested_transactions(self, transaction_manager):
        """Test nested transactions"""
        with transaction_manager.start("outer") as outer_tx:
            outer_tx.record_step("outer_step", True)

            with transaction_manager.start("inner") as inner_tx:
                assert inner_tx.parent_id == outer_tx.id
                inner_tx.record_step("inner_step", True)

            assert inner_tx.state == TransactionState.COMMITTED

        assert outer_tx.state == TransactionState.COMMITTED

    def test_inner_rollback_does_not_affect_outer(self, transaction_manager):
        """Test that inner transaction rollback doesn't affect outer"""
        with transaction_manager.start("outer") as outer_tx:
            outer_tx.record_step("outer_step", True)

            with pytest.raises(ValueError):
                with transaction_manager.start("inner") as inner_tx:
                    raise ValueError("Inner error")

            assert inner_tx.state == TransactionState.ROLLED_BACK
            assert outer_tx.state == TransactionState.PENDING
            outer_tx.record_step("outer_step2", True)

        assert outer_tx.state == TransactionState.COMMITTED


class TestTransactionDecorator:
    """Test transaction decorator"""

    def test_with_transaction_decorator(self, transaction_manager):
        """Test using @with_transaction decorator"""
        set_transaction_manager(transaction_manager)

        @with_transaction("decorated_function")
        def my_function(value):
            return value * 2

        result = my_function(5)
        assert result == 10

    def test_decorator_handles_exceptions(self, transaction_manager):
        """Test that decorator handles exceptions and rolls back"""
        set_transaction_manager(transaction_manager)

        @with_transaction("decorated_function")
        def failing_function():
            raise ValueError("Function failed")

        with pytest.raises(ValueError, match="Function failed"):
            failing_function()

        # Check that transaction was rolled back
        stats = transaction_manager.get_transaction_stats()
        assert stats["by_state"]["rolled_back"] >= 1


class TestTransactionMetadata:
    """Test TransactionMetadata dataclass"""

    def test_metadata_creation(self):
        """Test creating transaction metadata"""
        metadata = TransactionMetadata(
            transaction_id="test-tx",
            parent_id="parent-tx",
            state=TransactionState.PENDING,
        )

        assert metadata.transaction_id == "test-tx"
        assert metadata.parent_id == "parent-tx"
        assert metadata.state == TransactionState.PENDING
        assert len(metadata.steps_completed) == 0
        assert len(metadata.steps_failed) == 0

    def test_metadata_with_steps(self):
        """Test metadata with steps"""
        metadata = TransactionMetadata(transaction_id="test-tx")
        metadata.steps_completed.append("step1")
        metadata.steps_completed.append("step2")
        metadata.steps_failed.append("step3")

        assert len(metadata.steps_completed) == 2
        assert len(metadata.steps_failed) == 1


class TestTransactionIntegration:
    """Integration tests for transaction system"""

    def test_multi_step_transaction_success(self, transaction_manager):
        """Test multi-step transaction that succeeds"""
        steps_completed = []

        def step1():
            steps_completed.append("step1")

        def step2():
            steps_completed.append("step2")

        def step3():
            steps_completed.append("step3")

        with transaction_manager.start("multi_step") as tx:
            step1()
            tx.record_step("step1", True)

            step2()
            tx.record_step("step2", True)

            step3()
            tx.record_step("step3", True)

        assert len(steps_completed) == 3
        assert tx.state == TransactionState.COMMITTED
        assert len(tx._metadata.steps_completed) == 3

    def test_multi_step_transaction_failure(self, transaction_manager):
        """Test multi-step transaction that fails midway"""
        steps_completed = []

        def step1():
            steps_completed.append("step1")

        def step2():
            steps_completed.append("step2")

        def step3():
            raise RuntimeError("Step 3 failed")

        with pytest.raises(RuntimeError, match="Step 3 failed"):
            with transaction_manager.start("multi_step") as tx:
                step1()
                tx.record_step("step1", True)

                step2()
                tx.record_step("step2", True)

                step3()
                tx.record_step("step3", True)

        # Only first two steps should have completed
        assert len(steps_completed) == 2
        assert tx.state == TransactionState.ROLLED_BACK
        assert len(tx._metadata.steps_completed) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
