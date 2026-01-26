"""
Test Checkpoint Manager Implementation

Tests the CheckpointManager class for Task 3.2
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path

# Add v2 to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from v5.data import CheckpointManager, get_checkpoint_manager
from v5.data import init_db


def test_checkpoint_manager_basic():
    """Test basic checkpoint manager operations."""
    print("Testing CheckpointManager basic operations...")

    # Initialize databases
    init_db()

    # Create checkpoint manager
    checkpoint = CheckpointManager()

    # Test 1: Create a checkpoint
    print("\n1. Testing checkpoint creation...")
    snapshot_id = checkpoint.create(
        reason="Test checkpoint",
        snapshot_type="manual",
        include_databases=True,
        include_files=True,
        include_git=True,
        include_cache=True,
    )
    print(f"   Created checkpoint: {snapshot_id}")
    assert snapshot_id is not None
    assert snapshot_id.startswith("chkp_")

    # Test 2: List checkpoints
    print("\n2. Testing checkpoint listing...")
    checkpoints = checkpoint.list()
    print(f"   Found {len(checkpoints)} checkpoint(s)")
    assert len(checkpoints) > 0
    assert checkpoints[0]["snapshot_id"] == snapshot_id

    # Test 3: Get checkpoint details
    print("\n3. Testing checkpoint retrieval...")
    checkpoint_details = checkpoint.get(snapshot_id)
    print(f"   Retrieved checkpoint: {checkpoint_details['snapshot_id']}")
    assert checkpoint_details is not None
    assert checkpoint_details["snapshot_id"] == snapshot_id
    assert checkpoint_details["reason"] == "Test checkpoint"
    assert "db_state" in checkpoint_details
    assert "file_state" in checkpoint_details
    assert "git_state" in checkpoint_details

    # Test 4: Validate checkpoint
    print("\n4. Testing checkpoint validation...")
    is_valid = checkpoint.validate(snapshot_id)
    print(f"   Checkpoint valid: {is_valid}")
    assert is_valid is True

    # Test 5: Create another checkpoint with different type
    print("\n5. Testing checkpoint with different type...")
    snapshot_id_2 = checkpoint.create(
        reason="Auto checkpoint before task",
        snapshot_type="task_complete",
        task_id=42,
        operation_id="op_123",
    )
    print(f"   Created checkpoint: {snapshot_id_2}")

    # Test 6: List checkpoints with filter
    print("\n6. Testing checkpoint listing with filters...")
    filtered_checkpoints = checkpoint.list(snapshot_type="manual")
    print(f"   Found {len(filtered_checkpoints)} manual checkpoint(s)")
    assert len(filtered_checkpoints) >= 1

    # Test 7: Test rollback context manager (dry run)
    print("\n7. Testing rollback context manager...")
    try:
        with checkpoint.rollback_on_error("test_rollback"):
            print("   Inside rollback context")
            # Simulate success - no exception
            pass
        print("   Rollback context completed successfully (no rollback needed)")
    except Exception as e:
        print(f"   Unexpected error: {e}")
        assert False, "Rollback context should not raise exception when no error occurs"

    # Test 8: Test rollback context manager with error
    print("\n8. Testing rollback context manager with error...")
    try:
        with checkpoint.rollback_on_error("test_rollback_error"):
            print("   Inside rollback context")
            raise ValueError("Test error - should trigger rollback")
    except ValueError as e:
        print(f"   Expected error caught: {e}")
    except Exception as e:
        print(f"   Unexpected error type: {e}")
        assert False, "Should catch ValueError"

    # Test 9: Cleanup old checkpoints
    print("\n9. Testing checkpoint cleanup...")
    deleted_count = checkpoint.cleanup_old_checkpoints(max_count=100, max_age_hours=0)
    print(f"   Cleaned up {deleted_count} checkpoint(s)")

    # Test 10: Delete a checkpoint
    print("\n10. Testing checkpoint deletion...")
    success = checkpoint.delete(snapshot_id)
    print(f"   Deletion successful: {success}")
    assert success is True

    # Verify deletion
    checkpoints_after = checkpoint.list()
    deleted_checkpoint = checkpoint.get(snapshot_id)
    print(f"   Checkpoint exists after deletion: {deleted_checkpoint is not None}")
    assert deleted_checkpoint is None

    print("\n✅ All tests passed!")


def test_global_checkpoint_manager():
    """Test global checkpoint manager instance."""
    print("\nTesting global checkpoint manager instance...")

    # Get global instance
    checkpoint1 = get_checkpoint_manager()
    checkpoint2 = get_checkpoint_manager()

    # Should be same instance
    print(f"   Same instance: {checkpoint1 is checkpoint2}")
    assert checkpoint1 is checkpoint2

    print("✅ Global checkpoint manager test passed!")


def test_checkpoint_with_filters():
    """Test checkpoint filtering capabilities."""
    print("\nTesting checkpoint filtering...")

    init_db()
    checkpoint = CheckpointManager()

    # Create checkpoints with different attributes
    id1 = checkpoint.create("Task 1", snapshot_type="task_complete", task_id=1)
    id2 = checkpoint.create("Task 2", snapshot_type="task_complete", task_id=2)
    id3 = checkpoint.create(
        "Operation 1", snapshot_type="operation_end", operation_id="op1"
    )

    # Filter by task_id
    print("\n   Filtering by task_id=1...")
    task1_checkpoints = checkpoint.list(task_id=1)
    print(f"   Found {len(task1_checkpoints)} checkpoint(s)")
    assert len(task1_checkpoints) >= 1
    assert all(cp["task_id"] == 1 for cp in task1_checkpoints)

    # Filter by snapshot_type
    print("\n   Filtering by snapshot_type=task_complete...")
    task_checkpoints = checkpoint.list(snapshot_type="task_complete")
    print(f"   Found {len(task_checkpoints)} checkpoint(s)")
    assert len(task_checkpoints) >= 2

    # Test limit
    print("\n   Testing limit parameter...")
    limited_checkpoints = checkpoint.list(limit=2)
    print(f"   Found {len(limited_checkpoints)} checkpoint(s) (limit=2)")
    assert len(limited_checkpoints) <= 2

    print("\n✅ Filtering tests passed!")


if __name__ == "__main__":
    print("=" * 60)
    print("Checkpoint Manager Test Suite")
    print("=" * 60)

    try:
        test_checkpoint_manager_basic()
        test_global_checkpoint_manager()
        test_checkpoint_with_filters()

        print("\n" + "=" * 60)
        print("All tests completed successfully! ✅")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
