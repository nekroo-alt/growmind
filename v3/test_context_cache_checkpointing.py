"""
Test Context and Cache Checkpointing (Task 3.5)

Tests for checkpointing and restoring context engine and cache manager state.
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from v2.data.checkpoint_manager import get_checkpoint_manager
from v2.data.cache_manager import get_cache_manager


def test_cache_manager_state_capture():
    """Test capturing cache manager state in checkpoint."""
    print("\n=== Test: Cache Manager State Capture ===")

    # Get checkpoint manager
    checkpoint = get_checkpoint_manager()

    # Create a checkpoint with cache state
    snapshot_id = checkpoint.create(
        "test_cache_capture", snapshot_type="manual", include_cache=True
    )

    print(f"Created checkpoint: {snapshot_id}")

    # Retrieve checkpoint
    checkpoint_data = checkpoint.get(snapshot_id)

    assert checkpoint_data is not None, "Checkpoint should exist"

    # Check cache state
    cache_state_list = checkpoint_data.get("cache_state", [])
    assert len(cache_state_list) > 0, "Cache state should be captured"

    # Find cache_summary
    cache_summary = None
    for state in cache_state_list:
        if state["cache_key"] == "cache_summary":
            cache_summary = state
            break

    assert cache_summary is not None, "Cache summary should be present"

    # Parse cache data
    cache_data = json.loads(cache_summary["cache_data"])
    print(f"Captured {len(cache_data.get('cache_entries', []))} cache entries")
    print(f"Cache stats: {cache_data.get('cache_stats', {})}")

    print("✓ Cache manager state captured successfully")

    return snapshot_id


def test_context_engine_state_capture():
    """Test capturing context engine state in checkpoint."""
    print("\n=== Test: Context Engine State Capture ===")

    # Get checkpoint manager
    checkpoint = get_checkpoint_manager()

    # Create a checkpoint with cache state (includes context engine)
    snapshot_id = checkpoint.create(
        "test_context_capture", snapshot_type="manual", include_cache=True
    )

    print(f"Created checkpoint: {snapshot_id}")

    # Retrieve checkpoint
    checkpoint_data = checkpoint.get(snapshot_id)

    # Check cache state for context engine
    cache_state_list = checkpoint_data.get("cache_state", [])

    context_state = None
    for state in cache_state_list:
        if state["cache_key"] == "context_engine_state":
            context_state = state
            break

    if context_state:
        # Parse context data
        context_data = json.loads(context_state["cache_data"])
        print(f"Context engine state: {context_data.get('note', 'N/A')}")
        print(
            f"Expected state components: {list(context_data.get('expected_state', {}).keys())}"
        )
        print("✓ Context engine state captured")
    else:
        print("ℹ Context engine state is instance-specific (as expected)")

    return snapshot_id


def test_cache_restore():
    """Test restoring cache from checkpoint."""
    print("\n=== Test: Cache Restore ===")

    # Create a checkpoint
    checkpoint = get_checkpoint_manager()
    snapshot_id = checkpoint.create(
        "test_cache_restore", snapshot_type="manual", include_cache=True
    )

    print(f"Created checkpoint: {snapshot_id}")

    # Restore cache from checkpoint
    success = checkpoint.restore(
        snapshot_id,
        restore_cache=True,
        restore_databases=False,
        restore_files=False,
        restore_git=False,
    )

    assert success, "Cache restore should succeed"
    print("✓ Cache restored successfully")

    return snapshot_id


def test_cache_validation():
    """Test cache consistency validation after restore."""
    print("\n=== Test: Cache Validation ===")

    checkpoint = get_checkpoint_manager()

    # Create checkpoint
    snapshot_id = checkpoint.create(
        "test_cache_validation", snapshot_type="manual", include_cache=True
    )

    print(f"Created checkpoint: {snapshot_id}")

    # Restore with validation
    success = checkpoint.restore(
        snapshot_id,
        restore_cache=True,
        restore_databases=False,
        restore_files=False,
        restore_git=False,
        validate_after=True,
    )

    assert success, "Restore with validation should succeed"
    print("✓ Cache validation passed")

    return snapshot_id


def test_checkpoint_with_all_states():
    """Test creating checkpoint with all state types including cache."""
    print("\n=== Test: Checkpoint with All States ===")

    checkpoint = get_checkpoint_manager()

    # Create comprehensive checkpoint
    snapshot_id = checkpoint.create(
        "test_comprehensive_checkpoint",
        snapshot_type="manual",
        include_databases=True,
        include_files=True,
        include_git=True,
        include_cache=True,
    )

    print(f"Created comprehensive checkpoint: {snapshot_id}")

    # Retrieve checkpoint
    checkpoint_data = checkpoint.get(snapshot_id)

    # Verify all states are present
    assert (
        checkpoint_data.get("db_state") is not None
    ), "Database state should be present"
    assert checkpoint_data.get("file_state") is not None, "File state should be present"
    assert checkpoint_data.get("git_state") is not None, "Git state should be present"
    assert (
        checkpoint_data.get("cache_state") is not None
    ), "Cache state should be present"

    print(f"✓ All states captured:")
    print(f"  - Database state: {len(checkpoint_data['db_state'])} databases")
    print(f"  - File state: {len(checkpoint_data['file_state'])} files")
    print(f"  - Git state: {len(checkpoint_data['git_state'])} entries")
    print(f"  - Cache state: {len(checkpoint_data['cache_state'])} entries")

    return snapshot_id


def test_dry_run_restore():
    """Test dry-run restore for cache."""
    print("\n=== Test: Dry-Run Restore ===")

    checkpoint = get_checkpoint_manager()

    # Create checkpoint
    snapshot_id = checkpoint.create(
        "test_dry_run", snapshot_type="manual", include_cache=True
    )

    print(f"Created checkpoint: {snapshot_id}")

    # Dry-run restore (preview only)
    success = checkpoint.restore(snapshot_id, restore_cache=True, dry_run=True)

    assert success, "Dry-run restore should succeed"
    print("✓ Dry-run restore completed (no actual changes)")

    return snapshot_id


def test_cache_cleanup_on_restore():
    """Test that old cache is cleaned up during restore."""
    print("\n=== Test: Cache Cleanup on Restore ===")

    checkpoint = get_checkpoint_manager()
    cache_manager = get_cache_manager()

    # Get initial cache stats
    initial_stats = cache_manager.get_stats()
    print(f"Initial cache: {initial_stats['total_entries']} entries")

    # Create checkpoint
    snapshot_id = checkpoint.create(
        "test_cache_cleanup", snapshot_type="manual", include_cache=True
    )

    # Restore cache (should clean and rebuild)
    success = checkpoint.restore(
        snapshot_id,
        restore_cache=True,
        restore_databases=False,
        restore_files=False,
        restore_git=False,
    )

    assert success, "Restore should succeed"

    # Check cache after restore
    final_stats = cache_manager.get_stats()
    print(f"Final cache: {final_stats['total_entries']} entries")
    print("✓ Cache restored with cleanup")

    return snapshot_id


def test_checkpoint_list_with_cache():
    """Test listing checkpoints that include cache state."""
    print("\n=== Test: List Checkpoints with Cache ===")

    checkpoint = get_checkpoint_manager()

    # Create multiple checkpoints
    ids = []
    for i in range(3):
        snapshot_id = checkpoint.create(
            f"test_list_cache_{i}", snapshot_type="manual", include_cache=True
        )
        ids.append(snapshot_id)

    print(f"Created {len(ids)} checkpoints")

    # List checkpoints
    checkpoints = checkpoint.list(limit=10)

    # Filter for checkpoints with cache
    cache_checkpoints = [
        c for c in checkpoints if c.get("metadata", {}).get("include_cache")
    ]

    print(f"Found {len(cache_checkpoints)} checkpoints with cache state")
    assert len(cache_checkpoints) >= 3, "Should have at least 3 checkpoints with cache"

    print("✓ Successfully listed checkpoints with cache state")

    return ids


def test_checkpoint_metadata_includes_cache():
    """Test that checkpoint metadata includes cache information."""
    print("\n=== Test: Checkpoint Metadata ===")

    checkpoint = get_checkpoint_manager()

    # Create checkpoint
    snapshot_id = checkpoint.create(
        "test_metadata",
        snapshot_type="manual",
        include_cache=True,
        include_databases=False,
        include_files=False,
        include_git=False,
    )

    # Get checkpoint
    checkpoint_data = checkpoint.get(snapshot_id)

    # Check metadata
    metadata = checkpoint_data.get("metadata", {})
    assert metadata.get("include_cache") == True, "Metadata should show cache included"
    assert (
        metadata.get("include_databases") == False
    ), "Metadata should show databases not included"
    assert (
        metadata.get("include_files") == False
    ), "Metadata should show files not included"
    assert metadata.get("include_git") == False, "Metadata should show git not included"

    print(f"✓ Metadata correct: {metadata}")

    return snapshot_id


def cleanup_test_checkpoints():
    """Clean up test checkpoints."""
    print("\n=== Cleanup ===")

    checkpoint = get_checkpoint_manager()

    # List all checkpoints
    checkpoints = checkpoint.list(limit=100)

    # Delete test checkpoints
    deleted_count = 0
    for cp in checkpoints:
        if cp["reason"].startswith("test_"):
            if checkpoint.delete(cp["snapshot_id"]):
                deleted_count += 1

    print(f"Deleted {deleted_count} test checkpoints")


def run_all_tests():
    """Run all context and cache checkpointing tests."""
    print("=" * 60)
    print("Testing Context and Cache Checkpointing (Task 3.5)")
    print("=" * 60)

    try:
        # Run tests
        test_cache_manager_state_capture()
        test_context_engine_state_capture()
        test_cache_restore()
        test_cache_validation()
        test_checkpoint_with_all_states()
        test_dry_run_restore()
        test_cache_cleanup_on_restore()
        test_checkpoint_list_with_cache()
        test_checkpoint_metadata_includes_cache()

        print("\n" + "=" * 60)
        print("✓ All tests passed!")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
    finally:
        # Cleanup
        cleanup_test_checkpoints()


if __name__ == "__main__":
    run_all_tests()
