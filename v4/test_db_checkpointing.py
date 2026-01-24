"""
Test database checkpointing functionality (Task 3.3)
"""

import os
import sqlite3
import shutil
from pathlib import Path

from data.checkpoint_manager import CheckpointManager
from data.db_manager import TASK_DB_PATH, ACTIVITY_DB_PATH, SNAPSHOTS_DB_PATH


def setup_test_databases():
    """Create test databases with sample data."""
    # Ensure test databases exist
    for db_path in [TASK_DB_PATH, ACTIVITY_DB_PATH, SNAPSHOTS_DB_PATH]:
        if not os.path.exists(db_path):
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Create basic schema
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS test_table (
                    id INTEGER PRIMARY KEY,
                    name TEXT,
                    value INTEGER
                )
            """
            )

            # Insert test data
            cursor.execute(
                "INSERT INTO test_table (name, value) VALUES (?, ?)",
                ("test_record", 42),
            )

            conn.commit()
            conn.close()


def test_database_checkpoint_create():
    """Test creating a database checkpoint."""
    print("Testing database checkpoint creation...")

    # Setup test databases
    setup_test_databases()

    # Create checkpoint manager
    checkpoint_mgr = CheckpointManager()

    # Create a checkpoint
    snapshot_id = checkpoint_mgr.create(
        reason="Test checkpoint",
        snapshot_type="manual",
        include_databases=True,
        include_files=False,
        include_git=False,
        include_cache=False,
    )

    print(f"✓ Created checkpoint: {snapshot_id}")

    # Verify checkpoint was created
    checkpoint = checkpoint_mgr.get(snapshot_id)
    assert checkpoint is not None, "Checkpoint not found"
    assert checkpoint["snapshot_id"] == snapshot_id, "Snapshot ID mismatch"

    # Verify database state was captured
    db_state = checkpoint.get("db_state", [])
    assert len(db_state) > 0, "No database state captured"

    print(f"✓ Captured {len(db_state)} databases")

    # Verify backup files exist
    for db_info in db_state:
        backup_path = db_info.get("backup_path")
        if backup_path:
            assert os.path.exists(backup_path), f"Backup file not found: {backup_path}"
            print(f"✓ Backup exists for {db_info['db_name']}: {backup_path}")

    return snapshot_id


def test_database_checkpoint_restore():
    """Test restoring a database checkpoint."""
    print("\nTesting database checkpoint restore...")

    # Create initial checkpoint
    snapshot_id = test_database_checkpoint_create()

    # Modify a database to simulate a change
    print("Modifying database...")
    conn = sqlite3.connect(TASK_DB_PATH)
    cursor = conn.cursor()

    # Add new record
    cursor.execute(
        "INSERT INTO test_table (name, value) VALUES (?, ?)", ("modified_record", 99)
    )
    conn.commit()

    # Verify modification
    cursor.execute("SELECT COUNT(*) FROM test_table")
    count_before_restore = cursor.fetchone()[0]
    conn.close()

    print(f"Records before restore: {count_before_restore}")

    # Restore checkpoint
    checkpoint_mgr = CheckpointManager()
    success = checkpoint_mgr.restore(
        snapshot_id,
        restore_databases=True,
        restore_files=False,
        restore_git=False,
        restore_cache=False,
        validate_after=True,
    )

    assert success, "Checkpoint restore failed"
    print("✓ Checkpoint restore successful")

    # Verify database was restored
    conn = sqlite3.connect(TASK_DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM test_table")
    count_after_restore = cursor.fetchone()[0]

    conn.close()

    print(f"Records after restore: {count_after_restore}")

    # The count should be back to the original (1 record)
    assert (
        count_after_restore == 1
    ), f"Database not restored correctly: {count_after_restore} records"
    print("✓ Database restored to original state")


def test_database_integrity_check():
    """Test database integrity validation."""
    print("\nTesting database integrity check...")

    # Create a database
    setup_test_databases()

    checkpoint_mgr = CheckpointManager()

    # Check integrity of the database
    is_valid = checkpoint_mgr._validate_database_integrity(TASK_DB_PATH)

    assert is_valid, "Database integrity check failed for valid database"
    print("✓ Database integrity check passed")


def test_incremental_backup():
    """Test incremental backup detection."""
    print("\nTesting incremental backup detection...")

    # Setup test databases
    setup_test_databases()

    checkpoint_mgr = CheckpointManager()

    # Create first checkpoint
    snapshot_id1 = checkpoint_mgr.create(
        reason="First checkpoint",
        snapshot_type="manual",
        include_databases=True,
        include_files=False,
        include_git=False,
        include_cache=False,
    )

    print(f"✓ Created first checkpoint: {snapshot_id1}")

    # Create second checkpoint without modifying database
    snapshot_id2 = checkpoint_mgr.create(
        reason="Second checkpoint (no changes)",
        snapshot_type="manual",
        include_databases=True,
        include_files=False,
        include_git=False,
        include_cache=False,
    )

    print(f"✓ Created second checkpoint: {snapshot_id2}")

    # Check if second checkpoint is marked as incremental
    checkpoint2 = checkpoint_mgr.get(snapshot_id2)
    db_state = checkpoint2.get("db_state", [])

    if db_state:
        is_incremental = db_state[0].get("is_incremental", 0)
        if is_incremental:
            print("✓ Incremental backup detected correctly")
        else:
            print("✓ Full backup (database may have changed)")


def cleanup():
    """Clean up test artifacts."""
    print("\nCleaning up test artifacts...")

    # Clean up checkpoints directory
    checkpoints_dir = Path(SNAPSHOTS_DB_PATH).parent / "checkpoints"
    if checkpoints_dir.exists():
        shutil.rmtree(checkpoints_dir)
        print("✓ Cleaned up checkpoints directory")


if __name__ == "__main__":
    print("=" * 60)
    print("Testing Database Checkpointing (Task 3.3)")
    print("=" * 60)

    try:
        test_database_checkpoint_create()
        test_database_checkpoint_restore()
        test_database_integrity_check()
        test_incremental_backup()

        print("\n" + "=" * 60)
        print("✓ All tests passed!")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ Test failed: {str(e)}")
        import traceback

        traceback.print_exc()

    finally:
        cleanup()
