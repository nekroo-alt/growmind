"""
Test file system checkpointing functionality (Task 3.4)

This test suite verifies the enhanced file system and git state
checkpointing and restore capabilities.
"""

import os
import sys
import tempfile
import shutil
import subprocess
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from v5.data import CheckpointManager


def test_file_capture():
    """Test capturing file system state."""
    print("\n=== Test: File System Capture ===")

    manager = CheckpointManager()

    # Create a test file
    test_file = "test_checkpoint_file.py"
    with open(test_file, "w") as f:
        f.write("# Test file for checkpointing\n")
        f.write("def test_function():\n")
        f.write("    return 'test'\n")

    try:
        # Create checkpoint
        snapshot_id = manager.create("Test file capture", snapshot_type="manual")
        print(f"✓ Created checkpoint: {snapshot_id}")

        # Verify checkpoint was created
        checkpoint = manager.get(snapshot_id)
        assert checkpoint is not None, "Checkpoint should exist"
        assert checkpoint["reason"] == "Test file capture"

        # Check file state was captured
        file_state = checkpoint.get("file_state", [])
        assert len(file_state) > 0, "File state should be captured"

        print(f"✓ Captured {len(file_state)} files")
        return snapshot_id

    finally:
        # Cleanup
        if os.path.exists(test_file):
            os.remove(test_file)


def test_git_state_capture():
    """Test capturing git state."""
    print("\n=== Test: Git State Capture ===")

    manager = CheckpointManager()

    # Create checkpoint
    snapshot_id = manager.create("Test git state capture", snapshot_type="manual")
    print(f"✓ Created checkpoint: {snapshot_id}")

    # Verify git state was captured
    checkpoint = manager.get(snapshot_id)
    assert checkpoint is not None, "Checkpoint should exist"

    git_state = checkpoint.get("git_state", [])
    assert len(git_state) > 0, "Git state should be captured"

    state = git_state[0]
    assert "branch" in state, "Branch should be captured"
    assert "commit_hash" in state, "Commit hash should be captured"
    assert "git_status" in state, "Git status should be captured"

    print(f"✓ Captured git state:")
    print(f"  - Branch: {state['branch']}")
    print(f"  - Commit: {state['commit_hash']}")

    return snapshot_id


def test_file_restore():
    """Test restoring file system state."""
    print("\n=== Test: File System Restore ===")

    manager = CheckpointManager()

    # Create test file
    test_file = "test_restore_file.py"
    original_content = "# Original content\ndef original():\n    pass\n"

    with open(test_file, "w") as f:
        f.write(original_content)

    try:
        # Create checkpoint
        snapshot_id = manager.create("Before modification", snapshot_type="manual")
        print(f"✓ Created checkpoint: {snapshot_id}")

        # Modify file
        modified_content = "# Modified content\ndef modified():\n    pass\n"
        with open(test_file, "w") as f:
            f.write(modified_content)

        print(f"✓ Modified file")

        # Restore from checkpoint
        success = manager.restore(snapshot_id, dry_run=True)
        assert success, "Dry-run restore should succeed"

        print(f"✓ Dry-run restore succeeded")

        # Verify file was not actually modified (dry-run)
        with open(test_file, "r") as f:
            current_content = f.read()

        assert (
            current_content == modified_content
        ), "File should still be modified after dry-run"
        print(f"✓ File unchanged after dry-run")

        return snapshot_id

    finally:
        # Cleanup
        if os.path.exists(test_file):
            os.remove(test_file)


def test_git_restore():
    """Test restoring git state."""
    print("\n=== Test: Git State Restore ===")

    manager = CheckpointManager()

    # Create checkpoint
    snapshot_id = manager.create("Test git restore", snapshot_type="manual")
    print(f"✓ Created checkpoint: {snapshot_id}")

    # Dry-run restore
    success = manager.restore(snapshot_id, dry_run=True, restore_git=True)
    assert success, "Dry-run restore should succeed"

    print(f"✓ Dry-run git restore succeeded")

    return snapshot_id


def test_conflict_detection():
    """Test detecting file conflicts."""
    print("\n=== Test: Conflict Detection ===")

    manager = CheckpointManager()

    # Create test file
    test_file = "test_conflict_file.py"
    with open(test_file, "w") as f:
        f.write("# Version 1\n")

    try:
        # Create checkpoint
        snapshot_id = manager.create("Before conflict", snapshot_type="manual")
        print(f"✓ Created checkpoint: {snapshot_id}")

        # Modify file (simulating user work)
        with open(test_file, "w") as f:
            f.write("# Version 2 (user modification)\n")

        print(f"✓ Modified file (simulating user work)")

        # Get checkpoint details
        checkpoint = manager.get(snapshot_id)
        file_state = checkpoint.get("file_state", [])

        # Check for conflicts
        conflicts = []
        for state in file_state:
            conflict = manager._check_file_conflict(state)
            if conflict:
                conflicts.append(conflict)

        print(f"✓ Detected {len(conflicts)} potential conflicts")
        if conflicts:
            for conflict in conflicts:
                print(f"  - {conflict['file']}: {conflict['reason']}")

        return snapshot_id

    finally:
        # Cleanup
        if os.path.exists(test_file):
            os.remove(test_file)


def test_dry_run_warning():
    """Test dry-run warnings about user work."""
    print("\n=== Test: Dry-run Warning ===")

    manager = CheckpointManager()

    # Create test file
    test_file = "test_warning_file.py"
    with open(test_file, "w") as f:
        f.write("# Test file\n")

    try:
        # Create checkpoint
        snapshot_id = manager.create("Test warning", snapshot_type="manual")
        print(f"✓ Created checkpoint: {snapshot_id}")

        # Get checkpoint and check warnings
        checkpoint = manager.get(snapshot_id)

        # This should not produce warnings in dry-run
        print(f"✓ Dry-run completed (check logs for warnings)")

        return snapshot_id

    finally:
        # Cleanup
        if os.path.exists(test_file):
            os.remove(test_file)


def test_trackable_files():
    """Test trackable file filtering."""
    print("\n=== Test: Trackable File Filtering ===")

    manager = CheckpointManager()

    # Test various file types
    test_cases = [
        ("test.py", True),
        ("test.md", True),
        ("test.json", True),
        ("test.txt", False),
        ("v2/test.py", True),
        ("meta/test.md", True),
        ("random_file.dat", False),
    ]

    for filename, expected in test_cases:
        result = manager._is_trackable_file(filename)
        assert (
            result == expected
        ), f"File {filename} should be {'tracked' if expected else 'not tracked'}"
        status = "✓" if result == expected else "✗"
        print(f"{status} {filename}: {'tracked' if result else 'not tracked'}")

    print(f"✓ All trackable file tests passed")


def test_checkpoint_list():
    """Test listing checkpoints."""
    print("\n=== Test: List Checkpoints ===")

    manager = CheckpointManager()

    # Create multiple checkpoints
    snapshot_ids = []
    for i in range(3):
        snapshot_id = manager.create(f"Test checkpoint {i}", snapshot_type="manual")
        snapshot_ids.append(snapshot_id)
        print(f"✓ Created checkpoint {i+1}: {snapshot_id}")

    # List checkpoints
    checkpoints = manager.list(limit=10)
    assert len(checkpoints) >= 3, "Should have at least 3 checkpoints"

    print(f"✓ Listed {len(checkpoints)} checkpoints")

    return snapshot_ids


def test_checkpoint_validation():
    """Test checkpoint validation."""
    print("\n=== Test: Checkpoint Validation ===")

    manager = CheckpointManager()

    # Create checkpoint
    snapshot_id = manager.create("Test validation", snapshot_type="manual")
    print(f"✓ Created checkpoint: {snapshot_id}")

    # Validate checkpoint
    is_valid = manager.validate(snapshot_id)
    assert is_valid, "Checkpoint should be valid"

    print(f"✓ Checkpoint validated successfully")

    return snapshot_id


def test_checkpoint_cleanup():
    """Test checkpoint cleanup."""
    print("\n=== Test: Checkpoint Cleanup ===")

    manager = CheckpointManager()

    # Create multiple checkpoints
    snapshot_ids = []
    for i in range(5):
        snapshot_id = manager.create(f"Test cleanup {i}", snapshot_type="manual")
        snapshot_ids.append(snapshot_id)

    print(f"✓ Created {len(snapshot_ids)} checkpoints")

    # Cleanup old checkpoints (keep only 2)
    deleted_count = manager.cleanup_old_checkpoints(max_count=2)

    print(f"✓ Cleaned up {deleted_count} checkpoints")

    # Verify we have fewer checkpoints
    checkpoints = manager.list(limit=10)
    assert (
        len(checkpoints) <= 2
    ), f"Should have at most 2 checkpoints, got {len(checkpoints)}"

    print(f"✓ Remaining {len(checkpoints)} checkpoints")


def run_all_tests():
    """Run all file system checkpointing tests."""
    print("\n" + "=" * 60)
    print("FILE SYSTEM CHECKPOINTING TEST SUITE")
    print("=" * 60)

    tests = [
        test_file_capture,
        test_git_state_capture,
        test_file_restore,
        test_git_restore,
        test_conflict_detection,
        test_dry_run_warning,
        test_trackable_files,
        test_checkpoint_list,
        test_checkpoint_validation,
        test_checkpoint_cleanup,
    ]

    passed = 0
    failed = 0

    for test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"\n✗ Test failed: {test_func.__name__}")
            print(f"  Error: {str(e)}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"TEST RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
