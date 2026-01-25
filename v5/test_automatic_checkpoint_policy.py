"""
Test automatic checkpoint policy implementation.

Tests the CheckpointPolicy class and automatic checkpoint hooks
in CheckpointManager.
"""

import pytest
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from data.checkpoint_manager import CheckpointManager, CheckpointPolicy


def test_checkpoint_policy_default():
    """Test default checkpoint policy."""
    policy = CheckpointPolicy.default()

    assert policy.before_task is True
    assert policy.after_task is True
    assert policy.before_refactor is True
    assert policy.after_refactor is True
    assert policy.on_error is True
    assert policy.on_interrupt is True
    assert policy.after_n_operations is None
    assert policy.max_count == 10
    assert policy.max_age_hours == 24
    assert policy.keep_critical is True
    assert policy.critical_types == [
        "task_complete",
        "operation_end",
        "refactor_complete",
    ]


def test_checkpoint_policy_aggressive():
    """Test aggressive checkpoint policy."""
    policy = CheckpointPolicy.aggressive()

    assert policy.before_task is True
    assert policy.after_task is True
    assert policy.after_n_operations == 3
    assert policy.max_count == 20
    assert policy.max_age_hours == 48


def test_checkpoint_policy_conservative():
    """Test conservative checkpoint policy."""
    policy = CheckpointPolicy.conservative()

    assert policy.before_task is False
    assert policy.after_task is True
    assert policy.before_refactor is False
    assert policy.after_refactor is True
    assert policy.on_error is True
    assert policy.on_interrupt is True
    assert policy.after_n_operations is None
    assert policy.max_count == 5
    assert policy.max_age_hours == 12


def test_checkpoint_policy_to_dict():
    """Test converting policy to dictionary."""
    policy = CheckpointPolicy(before_task=True, after_task=False, max_count=15)

    policy_dict = policy.to_dict()

    assert policy_dict["before_task"] is True
    assert policy_dict["after_task"] is False
    assert policy_dict["max_count"] == 15


def test_checkpoint_policy_from_dict():
    """Test creating policy from dictionary."""
    policy_dict = {
        "before_task": False,
        "after_task": True,
        "max_count": 20,
        "critical_types": ["task_complete"],
    }

    policy = CheckpointPolicy.from_dict(policy_dict)

    assert policy.before_task is False
    assert policy.after_task is True
    assert policy.max_count == 20
    assert policy.critical_types == ["task_complete"]


def test_checkpoint_manager_policy_property():
    """Test checkpoint manager policy property."""
    default_policy = CheckpointPolicy.default()
    manager = CheckpointManager(policy=default_policy)

    assert manager.policy == default_policy


def test_checkpoint_manager_set_policy():
    """Test setting checkpoint manager policy."""
    manager = CheckpointManager()

    new_policy = CheckpointPolicy.aggressive()
    manager.set_policy(new_policy)

    assert manager.policy == new_policy


def test_auto_checkpoint_before_task():
    """Test automatic checkpoint before task."""
    manager = CheckpointManager(policy=CheckpointPolicy(before_task=True))

    checkpoint_id = manager.auto_checkpoint_before_task(
        task_id=42, operation_id="op-123"
    )

    assert checkpoint_id is not None
    assert checkpoint_id.startswith("chkp_")

    # Verify checkpoint was created
    checkpoint = manager.get(checkpoint_id)
    assert checkpoint is not None
    assert checkpoint["snapshot_type"] == "before_task"
    assert checkpoint["task_id"] == 42
    assert checkpoint["operation_id"] == "op-123"
    assert "Before task 42" in checkpoint["reason"]

    # Cleanup
    manager.delete(checkpoint_id)


def test_auto_checkpoint_before_task_disabled():
    """Test automatic checkpoint before task when disabled."""
    manager = CheckpointManager(policy=CheckpointPolicy(before_task=False))

    checkpoint_id = manager.auto_checkpoint_before_task(task_id=42)

    assert checkpoint_id is None


def test_auto_checkpoint_after_task():
    """Test automatic checkpoint after task."""
    manager = CheckpointManager(policy=CheckpointPolicy(after_task=True))

    checkpoint_id = manager.auto_checkpoint_after_task(
        task_id=42, operation_id="op-123"
    )

    assert checkpoint_id is not None

    # Verify checkpoint was created
    checkpoint = manager.get(checkpoint_id)
    assert checkpoint is not None
    assert checkpoint["snapshot_type"] == "task_complete"
    assert checkpoint["task_id"] == 42
    assert "After task 42" in checkpoint["reason"]

    # Cleanup
    manager.delete(checkpoint_id)


def test_auto_checkpoint_after_task_disabled():
    """Test automatic checkpoint after task when disabled."""
    manager = CheckpointManager(policy=CheckpointPolicy(after_task=False))

    checkpoint_id = manager.auto_checkpoint_after_task(task_id=42)

    assert checkpoint_id is None


def test_auto_checkpoint_before_refactor():
    """Test automatic checkpoint before refactor."""
    manager = CheckpointManager(policy=CheckpointPolicy(before_refactor=True))

    checkpoint_id = manager.auto_checkpoint_before_refactor(operation_id="op-123")

    assert checkpoint_id is not None

    # Verify checkpoint was created
    checkpoint = manager.get(checkpoint_id)
    assert checkpoint is not None
    assert checkpoint["snapshot_type"] == "before_refactor"
    assert checkpoint["operation_id"] == "op-123"
    assert "Before refactoring sprint" in checkpoint["reason"]

    # Cleanup
    manager.delete(checkpoint_id)


def test_auto_checkpoint_after_refactor():
    """Test automatic checkpoint after refactor."""
    manager = CheckpointManager(policy=CheckpointPolicy(after_refactor=True))

    checkpoint_id = manager.auto_checkpoint_after_refactor(operation_id="op-123")

    assert checkpoint_id is not None

    # Verify checkpoint was created
    checkpoint = manager.get(checkpoint_id)
    assert checkpoint is not None
    assert checkpoint["snapshot_type"] == "refactor_complete"
    assert "After refactoring sprint" in checkpoint["reason"]

    # Cleanup
    manager.delete(checkpoint_id)


def test_auto_checkpoint_on_error():
    """Test automatic checkpoint on error."""
    manager = CheckpointManager(policy=CheckpointPolicy(on_error=True))

    try:
        raise ValueError("Test error")
    except Exception as e:
        checkpoint_id = manager.auto_checkpoint_on_error(
            error=e, operation_id="op-123", task_id=42
        )

    assert checkpoint_id is not None

    # Verify checkpoint was created
    checkpoint = manager.get(checkpoint_id)
    assert checkpoint is not None
    assert checkpoint["snapshot_type"] == "error"
    assert checkpoint["task_id"] == 42
    assert checkpoint["operation_id"] == "op-123"
    assert "ValueError" in checkpoint["reason"]
    assert "Test error" in checkpoint["reason"]

    # Cleanup
    manager.delete(checkpoint_id)


def test_auto_checkpoint_on_error_disabled():
    """Test automatic checkpoint on error when disabled."""
    manager = CheckpointManager(policy=CheckpointPolicy(on_error=False))

    try:
        raise ValueError("Test error")
    except Exception as e:
        checkpoint_id = manager.auto_checkpoint_on_error(error=e)

    assert checkpoint_id is None


def test_auto_checkpoint_on_interrupt():
    """Test automatic checkpoint on interrupt."""
    manager = CheckpointManager(policy=CheckpointPolicy(on_interrupt=True))

    checkpoint_id = manager.auto_checkpoint_on_interrupt(
        signal_name="SIGINT", operation_id="op-123"
    )

    assert checkpoint_id is not None

    # Verify checkpoint was created
    checkpoint = manager.get(checkpoint_id)
    assert checkpoint is not None
    assert checkpoint["snapshot_type"] == "interrupt"
    assert checkpoint["operation_id"] == "op-123"
    assert "SIGINT" in checkpoint["reason"]

    # Cleanup
    manager.delete(checkpoint_id)


def test_auto_checkpoint_after_operation():
    """Test automatic checkpoint after N operations."""
    manager = CheckpointManager(policy=CheckpointPolicy(after_n_operations=3))

    # First operation - no checkpoint
    checkpoint_id = manager.auto_checkpoint_after_operation(
        operation_type="implementation"
    )
    assert checkpoint_id is None

    # Second operation - no checkpoint
    checkpoint_id = manager.auto_checkpoint_after_operation(
        operation_type="implementation"
    )
    assert checkpoint_id is None

    # Third operation - should create checkpoint
    checkpoint_id = manager.auto_checkpoint_after_operation(
        operation_type="implementation", operation_id="op-123"
    )
    assert checkpoint_id is not None

    # Verify checkpoint was created
    checkpoint = manager.get(checkpoint_id)
    assert checkpoint is not None
    assert checkpoint["snapshot_type"] == "periodic"
    assert "After 3 operations" in checkpoint["reason"]

    # Cleanup
    manager.delete(checkpoint_id)


def test_auto_checkpoint_after_operation_disabled():
    """Test automatic checkpoint after operation when disabled."""
    manager = CheckpointManager(policy=CheckpointPolicy(after_n_operations=None))

    # Multiple operations - no checkpoints
    for i in range(5):
        checkpoint_id = manager.auto_checkpoint_after_operation(
            operation_type="implementation"
        )
        assert checkpoint_id is None


def test_auto_cleanup():
    """Test automatic cleanup of old checkpoints."""
    manager = CheckpointManager(policy=CheckpointPolicy(max_count=3, max_age_hours=1))

    # Create multiple checkpoints
    checkpoint_ids = []
    for i in range(5):
        checkpoint_id = manager.create(
            reason=f"Test checkpoint {i}", snapshot_type=f"test_{i}"
        )
        checkpoint_ids.append(checkpoint_id)

    # Create a critical checkpoint
    critical_id = manager.create(
        reason="Critical checkpoint", snapshot_type="task_complete"
    )

    # Run auto cleanup
    deleted_count = manager.auto_cleanup()

    # Should have deleted some non-critical checkpoints
    assert deleted_count > 0

    # Critical checkpoint should still exist
    critical_checkpoint = manager.get(critical_id)
    assert critical_checkpoint is not None

    # Cleanup remaining
    for checkpoint_id in checkpoint_ids + [critical_id]:
        try:
            manager.delete(checkpoint_id)
        except:
            pass


def test_cleanup_respects_critical_checkpoints():
    """Test that cleanup respects critical checkpoint types."""
    manager = CheckpointManager(
        policy=CheckpointPolicy(
            max_count=2,
            keep_critical=True,
            critical_types=["task_complete", "refactor_complete"],
        )
    )

    # Create non-critical checkpoints
    checkpoint_ids = []
    for i in range(3):
        checkpoint_id = manager.create(
            reason=f"Test checkpoint {i}", snapshot_type="test"
        )
        checkpoint_ids.append(checkpoint_id)

    # Create critical checkpoints
    critical_id1 = manager.create(reason="Critical 1", snapshot_type="task_complete")
    critical_id2 = manager.create(
        reason="Critical 2", snapshot_type="refactor_complete"
    )

    # Run cleanup
    deleted_count = manager.cleanup_old_checkpoints(max_count=2, keep_critical=True)

    # Critical checkpoints should still exist
    assert manager.get(critical_id1) is not None
    assert manager.get(critical_id2) is not None

    # Some non-critical checkpoints should be deleted
    assert deleted_count >= 1

    # Cleanup
    for checkpoint_id in checkpoint_ids + [critical_id1, critical_id2]:
        try:
            manager.delete(checkpoint_id)
        except:
            pass


def test_custom_policy():
    """Test custom checkpoint policy."""
    custom_policy = CheckpointPolicy(
        before_task=False,
        after_task=True,
        before_refactor=False,
        after_refactor=True,
        on_error=True,
        on_interrupt=True,
        after_n_operations=5,
        max_count=15,
        max_age_hours=48,
        keep_critical=True,
        critical_types=["task_complete", "operation_end"],
    )

    manager = CheckpointManager(policy=custom_policy)

    assert manager.policy.before_task is False
    assert manager.policy.after_task is True
    assert manager.policy.after_n_operations == 5
    assert manager.policy.max_count == 15
    assert manager.policy.critical_types == ["task_complete", "operation_end"]


if __name__ == "__main__":
    # Run tests
    print("Running automatic checkpoint policy tests...")

    test_checkpoint_policy_default()
    print("✓ test_checkpoint_policy_default")

    test_checkpoint_policy_aggressive()
    print("✓ test_checkpoint_policy_aggressive")

    test_checkpoint_policy_conservative()
    print("✓ test_checkpoint_policy_conservative")

    test_checkpoint_policy_to_dict()
    print("✓ test_checkpoint_policy_to_dict")

    test_checkpoint_policy_from_dict()
    print("✓ test_checkpoint_policy_from_dict")

    test_checkpoint_manager_policy_property()
    print("✓ test_checkpoint_manager_policy_property")

    test_checkpoint_manager_set_policy()
    print("✓ test_checkpoint_manager_set_policy")

    test_auto_checkpoint_before_task()
    print("✓ test_auto_checkpoint_before_task")

    test_auto_checkpoint_before_task_disabled()
    print("✓ test_auto_checkpoint_before_task_disabled")

    test_auto_checkpoint_after_task()
    print("✓ test_auto_checkpoint_after_task")

    test_auto_checkpoint_after_task_disabled()
    print("✓ test_auto_checkpoint_after_task_disabled")

    test_auto_checkpoint_before_refactor()
    print("✓ test_auto_checkpoint_before_refactor")

    test_auto_checkpoint_after_refactor()
    print("✓ test_auto_checkpoint_after_refactor")

    test_auto_checkpoint_on_error()
    print("✓ test_auto_checkpoint_on_error")

    test_auto_checkpoint_on_error_disabled()
    print("✓ test_auto_checkpoint_on_error_disabled")

    test_auto_checkpoint_on_interrupt()
    print("✓ test_auto_checkpoint_on_interrupt")

    test_auto_checkpoint_after_operation()
    print("✓ test_auto_checkpoint_after_operation")

    test_auto_checkpoint_after_operation_disabled()
    print("✓ test_auto_checkpoint_after_operation_disabled")

    test_auto_cleanup()
    print("✓ test_auto_cleanup")

    test_cleanup_respects_critical_checkpoints()
    print("✓ test_cleanup_respects_critical_checkpoints")

    test_custom_policy()
    print("✓ test_custom_policy")

    print("\n✅ All tests passed!")
