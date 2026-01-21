"""
Transaction Support for Multi-Step Operations

Implements transaction-like semantics for operations with automatic rollback
on failure. Uses checkpoints for state persistence and rollback.
"""

import threading
import uuid
import logging
from contextlib import contextmanager
from enum import Enum
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field

from data.checkpoint_manager import CheckpointManager
from data.telemetry_manager import TelemetryManager


logger = logging.getLogger(__name__)


class TransactionState(Enum):
    """Transaction states"""
    PENDING = "pending"
    COMMITTED = "committed"
    ROLLED_BACK = "rolled_back"
    PARTIALLY_COMMITTED = "partially_committed"


@dataclass
class TransactionMetadata:
    """Metadata for a transaction"""
    transaction_id: str
    parent_id: Optional[str] = None
    state: TransactionState = TransactionState.PENDING
    checkpoint_id: Optional[str] = None
    steps_completed: List[str] = field(default_factory=list)
    steps_failed: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    start_time: float = 0.0
    end_time: Optional[float] = None


class Transaction:
    """
    Represents a transaction with rollback capabilities.
    
    A transaction wraps multiple steps and ensures atomicity:
    - All steps succeed: transaction commits
    - Any step fails: transaction rolls back to checkpoint
    
    Supports nested transactions via parent_id.
    """
    
    def __init__(
        self,
        transaction_id: str,
        checkpoint_manager: CheckpointManager,
        telemetry_manager: TelemetryManager,
        parent_id: Optional[str] = None
    ):
        self.id = transaction_id
        self.checkpoint_manager = checkpoint_manager
        self.telemetry_manager = telemetry_manager
        self.parent_id = parent_id
        
        self._metadata = TransactionMetadata(
            transaction_id=transaction_id,
            parent_id=parent_id,
            start_time=0.0
        )
        
        self._lock = threading.RLock()
        self._committed = False
        self._rolled_back = False
        self._current_step: Optional[str] = None
        
    @property
    def state(self) -> TransactionState:
        """Get current transaction state"""
        return self._metadata.state
    
    @property
    def is_active(self) -> bool:
        """Check if transaction is active (not committed or rolled back)"""
        return not self._committed and not self._rolled_back
    
    def _start_transaction(self, reason: str) -> None:
        """Start a transaction by creating a checkpoint"""
        logger.info(f"Starting transaction: {self.id} (parent: {self.parent_id}, reason: {reason})")
        
        # Create checkpoint for rollback
        checkpoint_id = self.checkpoint_manager.create(
            reason=f"transaction_{self.id}_{reason}",
            transaction_id=self.id
        )
        self._metadata.checkpoint_id = checkpoint_id
        
        # Track operation in telemetry
        op = self.telemetry_manager.track_operation(
            "transaction",
            f"Transaction {self.id}"
        )
        op.record_event("started", "info", "Transaction started")
        self._metadata.metadata["telemetry_operation_id"] = op.id
        
    def _commit_transaction(self) -> None:
        """Commit a completed transaction"""
        with self._lock:
            if self._rolled_back:
                raise RuntimeError(f"Cannot commit rolled-back transaction {self.id}")
            if self._committed:
                logger.warning(f"Transaction already committed: {self.id}")
                return
            
            logger.info(f"Committing transaction: {self.id} (steps: {len(self._metadata.steps_completed)})")
            
            self._metadata.state = TransactionState.COMMITTED
            self._metadata.end_time = 0.0  # TODO: Add time tracking
            self._committed = True
            
            # Record commit in telemetry
            op_id = self._metadata.metadata.get("telemetry_operation_id")
            if op_id:
                op = self.telemetry_manager.get_operation(op_id)
                if op:
                    op.record_event("committed", "info", "Transaction committed")
                    op.record_metric("steps_completed", len(self._metadata.steps_completed))
            
            logger.info(f"Transaction committed successfully: {self.id}")
    
    def _rollback_transaction(self, reason: str) -> None:
        """Roll back a failed transaction to checkpoint"""
        with self._lock:
            if self._committed:
                raise RuntimeError(f"Cannot roll back committed transaction {self.id}")
            if self._rolled_back:
                logger.warning(f"Transaction already rolled back: {self.id}")
                return
            
            logger.info(f"Rolling back transaction: {self.id} (checkpoint: {self._metadata.checkpoint_id}, reason: {reason})")
            
            # Restore from checkpoint
            if self._metadata.checkpoint_id:
                try:
                    self.checkpoint_manager.restore(self._metadata.checkpoint_id)
                    logger.info(f"Restored from checkpoint successfully: {self._metadata.checkpoint_id}")
                except Exception as e:
                    logger.error(f"Failed to restore from checkpoint: {self._metadata.checkpoint_id}, transaction: {self.id}, error: {e}")
                    raise
            else:
                logger.warning(f"No checkpoint available for rollback: {self.id}")
            
            self._metadata.state = TransactionState.ROLLED_BACK
            self._metadata.end_time = 0.0  # TODO: Add time tracking
            self._rolled_back = True
            
            # Record rollback in telemetry
            op_id = self._metadata.metadata.get("telemetry_operation_id")
            if op_id:
                op = self.telemetry_manager.get_operation(op_id)
                if op:
                    op.record_event("rolled_back", "warning", f"Rolled back: {reason}")
                    op.record_metric("steps_completed", len(self._metadata.steps_completed))
                    op.record_metric("steps_failed", len(self._metadata.steps_failed))
            
            logger.info(f"Transaction rolled back successfully: {self.id}, reason: {reason}")
    
    def record_step(self, step_name: str, success: bool) -> None:
        """
        Record completion of a transaction step.
        
        Args:
            step_name: Name of the step
            success: Whether the step completed successfully
        """
        with self._lock:
            if success:
                self._metadata.steps_completed.append(step_name)
                logger.debug(f"Transaction step completed: {self.id}, step: {step_name}")
            else:
                self._metadata.steps_failed.append(step_name)
                logger.warning(f"Transaction step failed: {self.id}, step: {step_name}")
    
    def commit(self) -> None:
        """Manually commit the transaction"""
        self._commit_transaction()
    
    def rollback(self, reason: str = "Manual rollback") -> None:
        """Manually roll back the transaction"""
        self._rollback_transaction(reason)
    
    def get_metadata(self) -> TransactionMetadata:
        """Get transaction metadata"""
        return self._metadata


class TransactionManager:
    """
    Manages transactions with support for nesting and tracking.
    
    Thread-safe transaction management with checkpoint-based rollback.
    """
    
    def __init__(
        self,
        checkpoint_manager: CheckpointManager,
        telemetry_manager: TelemetryManager
    ):
        self.checkpoint_manager = checkpoint_manager
        self.telemetry_manager = telemetry_manager
        
        self._transactions: Dict[str, Transaction] = {}
        self._active_transactions: List[str] = []  # Stack for nested transactions
        self._lock = threading.RLock()
        
        logger.info("TransactionManager initialized")
    
    @contextmanager
    def start(
        self,
        reason: str = "transaction",
        transaction_id: Optional[str] = None
    ):
        """
        Start a transaction context manager.
        
        Automatically commits on success or rolls back on failure.
        
        Args:
            reason: Description of why transaction was started
            transaction_id: Optional custom transaction ID (auto-generated if not provided)
        
        Usage:
            with transaction_manager.start("implement_task") as tx:
                # Step 1: Modify database
                # Step 2: Write files
                # Step 3: Run tests
                # If any step raises exception, auto-rollback
                tx.record_step("step1", True)
                tx.record_step("step2", True)
                tx.record_step("step3", True)
            # Auto-commit if no exception
        """
        tx_id = transaction_id or str(uuid.uuid4())
        
        # Get parent transaction (for nesting)
        parent_id = self._active_transactions[-1] if self._active_transactions else None
        
        with self._lock:
            # Create transaction
            tx = Transaction(
                transaction_id=tx_id,
                checkpoint_manager=self.checkpoint_manager,
                telemetry_manager=self.telemetry_manager,
                parent_id=parent_id
            )
            self._transactions[tx_id] = tx
            self._active_transactions.append(tx_id)
        
        # Start transaction
        tx._start_transaction(reason)
        
        try:
            yield tx
            # Auto-commit if no exception and not already committed/rolled back
            if not tx._committed and not tx._rolled_back:
                tx.commit()
        except Exception as e:
            # Auto-rollback on exception if not already rolled back
            if not tx._rolled_back:
                logger.error(f"Transaction failed, rolling back: {tx_id}, error: {e}")
                tx.rollback(reason=f"Exception: {str(e)}")
            raise  # Re-raise exception
        finally:
            # Clean up
            with self._lock:
                if self._active_transactions and self._active_transactions[-1] == tx_id:
                    self._active_transactions.pop()
                # Keep transaction in history for debugging
    
    def get_transaction(self, transaction_id: str) -> Optional[Transaction]:
        """Get a transaction by ID"""
        with self._lock:
            return self._transactions.get(transaction_id)
    
    def get_active_transaction(self) -> Optional[Transaction]:
        """Get the currently active transaction (top of stack)"""
        with self._lock:
            if self._active_transactions:
                tx_id = self._active_transactions[-1]
                return self._transactions.get(tx_id)
            return None
    
    def list_transactions(
        self,
        state: Optional[TransactionState] = None
    ) -> List[Transaction]:
        """
        List transactions, optionally filtered by state.
        
        Args:
            state: Optional filter by transaction state
        
        Returns:
            List of transactions matching criteria
        """
        with self._lock:
            transactions = list(self._transactions.values())
            if state:
                transactions = [tx for tx in transactions if tx.state == state]
            return transactions
    
    def clear_history(self, older_than_seconds: Optional[int] = None) -> None:
        """
        Clear transaction history.
        
        Args:
            older_than_seconds: Only clear transactions older than this many seconds
        """
        with self._lock:
            if older_than_seconds is None:
                # Clear all
                self._transactions.clear()
                logger.info("Cleared all transaction history")
            else:
                # Clear old transactions (TODO: implement time-based filtering)
                logger.warning("Time-based transaction filtering not yet implemented")
    
    def get_transaction_stats(self) -> Dict[str, Any]:
        """Get statistics about transactions"""
        with self._lock:
            stats = {
                "total_transactions": len(self._transactions),
                "by_state": {
                    state.value: sum(
                        1 for tx in self._transactions.values() 
                        if tx.state == state
                    )
                    for state in TransactionState
                },
                "active_transactions": len(self._active_transactions),
                "max_nesting_depth": max(
                    1, 
                    len([
                        tx for tx in self._transactions.values() 
                        if tx.parent_id is None
                    ])
                )
            }
            return stats


# Convenience functions for transaction management
def create_transaction_manager(
    checkpoint_manager: CheckpointManager,
    telemetry_manager: TelemetryManager
) -> TransactionManager:
    """
    Create a new TransactionManager instance.
    
    Args:
        checkpoint_manager: CheckpointManager for state rollback
        telemetry_manager: TelemetryManager for tracking
    
    Returns:
        Configured TransactionManager instance
    """
    return TransactionManager(
        checkpoint_manager=checkpoint_manager,
        telemetry_manager=telemetry_manager
    )


# Global transaction manager (can be overridden)
_global_transaction_manager: Optional[TransactionManager] = None


def get_transaction_manager() -> Optional[TransactionManager]:
    """Get the global transaction manager"""
    return _global_transaction_manager


def set_transaction_manager(manager: TransactionManager) -> None:
    """Set the global transaction manager"""
    global _global_transaction_manager
    _global_transaction_manager = manager


def with_transaction(
    reason: str = "transaction",
    transaction_id: Optional[str] = None
):
    """
    Decorator to wrap a function in a transaction.
    
    Args:
        reason: Description of transaction
        transaction_id: Optional custom transaction ID
    
    Usage:
        @with_transaction("my_operation")
        def my_function():
            # Do work
            pass
    """
    def decorator(func: Callable):
        def wrapper(*args, **kwargs):
            manager = get_transaction_manager()
            if manager is None:
                raise RuntimeError("TransactionManager not initialized")
            
            with manager.start(reason, transaction_id):
                return func(*args, **kwargs)
        return wrapper
    return decorator
