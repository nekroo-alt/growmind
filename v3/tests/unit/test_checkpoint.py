"""
Comprehensive tests for checkpoint and recovery system.

Tests cover:
- Checkpoint creation for all state types
- Checkpoint restoration
- Checkpoint rollback
- Checkpoint validation
- Session resume from checkpoint
- Automatic checkpoint policy
"""

import os
import shutil
import tempfile
import sqlite3
import time
from pathlib import Path
from datetime import datetime
import pytest

from v2.data.checkpoint_manager import CheckpointManager, Checkpoint, CheckpointError


class TestCheckpointCreation:
    """Test checkpoint creation for all state types."""

    @pytest.fixture
    def checkpoint_manager(self):
        """Create a CheckpointManager instance for testing."""
        temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(temp_dir, "test.db")

        # Create test database
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE test_table (id INTEGER PRIMARY KEY, data TEXT)")
        conn.execute("INSERT INTO test_table VALUES (1, 'original data')")
        conn.commit()
        conn.close()

        manager = CheckpointManager(
            checkpoint_dir=os.path.join(temp_dir, "checkpoints")
        )
        yield manager

        # Cleanup
        shutil.rmtree(temp_dir)

    def test_create_basic_checkpoint(self, checkpoint_manager):
        """Test creating a basic checkpoint."""
        checkpoint_id = checkpoint_manager.create(
            name="test_checkpoint",
            reason="Testing basic checkpoint creation",
            db_paths=[os.path.join(checkpoint_manager.checkpoint_dir, "..", "test.db")],
        )

        assert checkpoint_id is not None
        assert len(checkpoint_id) == 36  # UUID format

        # Verify checkpoint was created
        checkpoints = checkpoint_manager.list_checkpoints()
        assert len(checkpoints) == 1
        assert checkpoints[0].id == checkpoint_id
        assert checkpoints[0].name == "test_checkpoint"

    def test_create_checkpoint_with_metadata(self, checkpoint_manager):
        """Test creating a checkpoint with custom metadata."""
        checkpoint_id = checkpoint_manager.create(
            name="metadata_checkpoint",
            reason="Testing metadata",
            metadata={
                "task_id": 42,
                "user": "test_user",
                "tags": ["critical", "before_refactor"],
            },
            db_paths=[os.path.join(checkpoint_manager.checkpoint_dir, "..", "test.db")],
        )

        checkpoint = checkpoint_manager.get_checkpoint(checkpoint_id)
        assert checkpoint.metadata["task_id"] == 42
        assert checkpoint.metadata["user"] == "test_user"
        assert checkpoint.metadata["tags"] == ["critical", "before_refactor"]

    def test_create_multiple_checkpoints(self, checkpoint_manager):
        """Test creating multiple checkpoints."""
        db_path = os.path.join(checkpoint_manager.checkpoint_dir, "..", "test.db")

        for i in range(3):
            checkpoint_manager.create(
                name=f"checkpoint_{i}",
                reason=f"Test checkpoint {i}",
                db_paths=[db_path],
            )

        checkpoints = checkpoint_manager.list_checkpoints()
        assert len(checkpoints) == 3

        # Verify order (newest first)
        assert checkpoints[0].name == "checkpoint_2"
        assert checkpoints[2].name == "checkpoint_0"

    def test_create_checkpoint_database_state(self, checkpoint_manager):
        """Test creating checkpoint captures database state."""
        db_path = os.path.join(checkpoint_manager.checkpoint_dir, "..", "test.db")

        # Insert test data
        conn = sqlite3.connect(db_path)
        conn.execute("INSERT INTO test_table VALUES (2, 'second row')")
        conn.commit()
        conn.close()

        # Create checkpoint
        checkpoint_id = checkpoint_manager.create(
            name="db_state_checkpoint",
            reason="Testing database state capture",
            db_paths=[db_path],
        )

        # Modify database after checkpoint
        conn = sqlite3.connect(db_path)
        conn.execute("INSERT INTO test_table VALUES (3, 'third row')")
        conn.execute("UPDATE test_table SET data='modified' WHERE id=1")
        conn.commit()
        conn.close()

        # Restore checkpoint
        checkpoint_manager.restore(checkpoint_id)

        # Verify database state is restored
        conn = sqlite3.connect(db_path)
        cursor = conn.execute("SELECT * FROM test_table ORDER BY id")
        rows = cursor.fetchall()
        conn.close()

        assert len(rows) == 2
        assert rows[0] == (1, "original data")
        assert rows[1] == (2, "second row")


class TestCheckpointRestoration:
    """Test checkpoint restoration."""

    @pytest.fixture
    def checkpoint_manager_with_data(self):
        """Create CheckpointManager with test data."""
        temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(temp_dir, "test.db")

        # Create test database
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE test_table (id INTEGER PRIMARY KEY, data TEXT)")
        conn.execute("INSERT INTO test_table VALUES (1, 'row 1')")
        conn.execute("INSERT INTO test_table VALUES (2, 'row 2')")
        conn.commit()
        conn.close()

        manager = CheckpointManager(
            checkpoint_dir=os.path.join(temp_dir, "checkpoints")
        )

        # Create initial checkpoint
        checkpoint_id = manager.create(
            name="initial", reason="Initial state", db_paths=[db_path]
        )

        yield manager, db_path, checkpoint_id

        # Cleanup
        shutil.rmtree(temp_dir)

    def test_restore_database_checkpoint(self, checkpoint_manager_with_data):
        """Test restoring database from checkpoint."""
        manager, db_path, checkpoint_id = checkpoint_manager_with_data

        # Modify database
        conn = sqlite3.connect(db_path)
        conn.execute("INSERT INTO test_table VALUES (3, 'row 3')")
        conn.execute("DELETE FROM test_table WHERE id=1")
        conn.commit()
        conn.close()

        # Verify modification
        conn = sqlite3.connect(db_path)
        cursor = conn.execute("SELECT COUNT(*) FROM test_table")
        count = cursor.fetchone()[0]
        conn.close()
        assert count == 2

        # Restore checkpoint
        manager.restore(checkpoint_id)

        # Verify restoration
        conn = sqlite3.connect(db_path)
        cursor = conn.execute("SELECT * FROM test_table ORDER BY id")
        rows = cursor.fetchall()
        conn.close()

        assert len(rows) == 2
        assert rows[0] == (1, "row 1")
        assert rows[1] == (2, "row 2")

    def test_restore_nonexistent_checkpoint(self, checkpoint_manager):
        """Test restoring a non-existent checkpoint."""
        with pytest.raises(CheckpointError):
            checkpoint_manager.restore("non-existent-id")

    def test_restore_creates_backup(self, checkpoint_manager_with_data):
        """Test that restore creates a backup of current state."""
        manager, db_path, checkpoint_id = checkpoint_manager_with_data

        # Modify database
        conn = sqlite3.connect(db_path)
        conn.execute("INSERT INTO test_table VALUES (3, 'modified row')")
        conn.commit()
        conn.close()

        # Restore checkpoint
        manager.restore(checkpoint_id, backup_before_restore=True)

        # Verify a pre-restore checkpoint was created
        checkpoints = manager.list_checkpoints()
        pre_restore = [
            c for c in checkpoints if c.reason.startswith("pre-restore backup")
        ]
        assert len(pre_restore) >= 1

    def test_restore_multiple_databases(self, checkpoint_manager):
        """Test restoring multiple databases from checkpoint."""
        temp_dir = os.path.dirname(checkpoint_manager.checkpoint_dir)
        db1_path = os.path.join(temp_dir, "db1.db")
        db2_path = os.path.join(temp_dir, "db2.db")

        # Create databases
        for db_path in [db1_path, db2_path]:
            conn = sqlite3.connect(db_path)
            conn.execute("CREATE TABLE data (id INTEGER PRIMARY KEY, value TEXT)")
            conn.execute("INSERT INTO data VALUES (1, 'original')")
            conn.commit()
            conn.close()

        # Create checkpoint
        checkpoint_id = checkpoint_manager.create(
            name="multi_db", reason="Multiple databases", db_paths=[db1_path, db2_path]
        )

        # Modify both databases
        for db_path in [db1_path, db2_path]:
            conn = sqlite3.connect(db_path)
            conn.execute("UPDATE data SET value='modified' WHERE id=1")
            conn.commit()
            conn.close()

        # Restore checkpoint
        checkpoint_manager.restore(checkpoint_id)

        # Verify both databases restored
        for db_path in [db1_path, db2_path]:
            conn = sqlite3.connect(db_path)
            cursor = conn.execute("SELECT value FROM data WHERE id=1")
            value = cursor.fetchone()[0]
            conn.close()
            assert value == "original"


class TestCheckpointRollback:
    """Test checkpoint rollback functionality."""

    @pytest.fixture
    def checkpoint_manager_for_rollback(self):
        """Create CheckpointManager with test data for rollback."""
        temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(temp_dir, "test.db")

        # Create test database
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE test_table (id INTEGER PRIMARY KEY, data TEXT)")
        conn.execute("INSERT INTO test_table VALUES (1, 'initial')")
        conn.commit()
        conn.close()

        manager = CheckpointManager(
            checkpoint_dir=os.path.join(temp_dir, "checkpoints")
        )
        yield manager, db_path

        # Cleanup
        shutil.rmtree(temp_dir)

    def test_rollback_on_error(self, checkpoint_manager_for_rollback):
        """Test automatic rollback on error."""
        manager, db_path = checkpoint_manager_for_rollback

        # Create checkpoint before operation
        checkpoint_id = manager.create(
            name="before_op", reason="Before operation", db_paths=[db_path]
        )

        # Simulate operation that fails
        with manager.rollback_on_error(checkpoint_id):
            conn = sqlite3.connect(db_path)
            conn.execute("INSERT INTO test_table VALUES (2, 'new row')")
            conn.commit()
            conn.close()

            # Simulate error
            raise ValueError("Operation failed")

        # Verify rollback occurred
        conn = sqlite3.connect(db_path)
        cursor = conn.execute("SELECT COUNT(*) FROM test_table")
        count = cursor.fetchone()[0]
        conn.close()

        assert count == 1, "Should have rolled back to 1 row"

    def test_no_rollback_on_success(self, checkpoint_manager_for_rollback):
        """Test no rollback occurs on successful operation."""
        manager, db_path = checkpoint_manager_for_rollback

        # Create checkpoint before operation
        checkpoint_id = manager.create(
            name="before_op", reason="Before operation", db_paths=[db_path]
        )

        # Simulate successful operation
        with manager.rollback_on_error(checkpoint_id):
            conn = sqlite3.connect(db_path)
            conn.execute("INSERT INTO test_table VALUES (2, 'new row')")
            conn.commit()
            conn.close()

        # Verify no rollback occurred
        conn = sqlite3.connect(db_path)
        cursor = conn.execute("SELECT COUNT(*) FROM test_table")
        count = cursor.fetchone()[0]
        conn.close()

        assert count == 2, "Should have 2 rows after successful operation"

    def test_manual_rollback(self, checkpoint_manager_for_rollback):
        """Test manual rollback to checkpoint."""
        manager, db_path = checkpoint_manager_for_rollback

        # Create checkpoint
        checkpoint_id = manager.create(
            name="checkpoint1", reason="Initial checkpoint", db_paths=[db_path]
        )

        # Make changes
        conn = sqlite3.connect(db_path)
        conn.execute("INSERT INTO test_table VALUES (2, 'row 2')")
        conn.execute("INSERT INTO test_table VALUES (3, 'row 3')")
        conn.commit()
        conn.close()

        # Manual rollback
        manager.rollback_to(checkpoint_id)

        # Verify rollback
        conn = sqlite3.connect(db_path)
        cursor = conn.execute("SELECT COUNT(*) FROM test_table")
        count = cursor.fetchone()[0]
        conn.close()

        assert count == 1


class TestCheckpointValidation:
    """Test checkpoint validation."""

    @pytest.fixture
    def checkpoint_manager(self):
        """Create CheckpointManager for validation tests."""
        temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(temp_dir, "test.db")

        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE test_table (id INTEGER PRIMARY KEY, data TEXT)")
        conn.execute("INSERT INTO test_table VALUES (1, 'data')")
        conn.commit()
        conn.close()

        manager = CheckpointManager(
            checkpoint_dir=os.path.join(temp_dir, "checkpoints")
        )
        yield manager, db_path

        shutil.rmtree(temp_dir)

    def test_validate_checkpoint(self, checkpoint_manager):
        """Test validating a checkpoint."""
        manager, db_path = checkpoint_manager

        checkpoint_id = manager.create(
            name="valid_checkpoint", reason="Valid checkpoint", db_paths=[db_path]
        )

        # Validate checkpoint
        is_valid = manager.validate(checkpoint_id)
        assert is_valid is True

    def test_validate_corrupted_checkpoint(self, checkpoint_manager):
        """Test validating a corrupted checkpoint."""
        manager, db_path = checkpoint_manager

        checkpoint_id = manager.create(
            name="corrupted", reason="Will be corrupted", db_paths=[db_path]
        )

        # Corrupt the checkpoint
        checkpoint_path = os.path.join(
            manager.checkpoint_dir, f"chkp_{checkpoint_id}", "test.db.backup"
        )

        if os.path.exists(checkpoint_path):
            with open(checkpoint_path, "w") as f:
                f.write("corrupted data")

        # Validate checkpoint
        is_valid = manager.validate(checkpoint_id)
        assert is_valid is False

    def test_validate_nonexistent_checkpoint(self, checkpoint_manager):
        """Test validating non-existent checkpoint."""
        is_valid = checkpoint_manager.validate("non-existent-id")
        assert is_valid is False

    def test_get_checkpoint_info(self, checkpoint_manager):
        """Test getting detailed checkpoint information."""
        manager, db_path = checkpoint_manager

        checkpoint_id = manager.create(
            name="info_checkpoint",
            reason="Testing checkpoint info",
            metadata={"task_id": 123},
            db_paths=[db_path],
        )

        info = checkpoint_manager.get_checkpoint_info(checkpoint_id)

        assert info["id"] == checkpoint_id
        assert info["name"] == "info_checkpoint"
        assert info["reason"] == "Testing checkpoint info"
        assert info["metadata"]["task_id"] == 123
        assert "size_mb" in info
        assert "created_at" in info


class TestSessionResumeFromCheckpoint:
    """Test session resumption from checkpoint."""

    @pytest.fixture
    def session_checkpoint_manager(self):
        """Create CheckpointManager for session tests."""
        temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(temp_dir, "session.db")

        # Create session database
        conn = sqlite3.connect(db_path)
        conn.execute(
            """
            CREATE TABLE session_state (
                id INTEGER PRIMARY KEY,
                task_id INTEGER,
                status TEXT,
                data TEXT
            )
        """
        )
        conn.execute(
            "INSERT INTO session_state VALUES (1, 42, 'in_progress', 'some data')"
        )
        conn.commit()
        conn.close()

        manager = CheckpointManager(
            checkpoint_dir=os.path.join(temp_dir, "checkpoints")
        )
        yield manager, db_path

        shutil.rmtree(temp_dir)

    def test_resume_session_from_checkpoint(self, session_checkpoint_manager):
        """Test resuming session from checkpoint."""
        manager, db_path = session_checkpoint_manager

        # Create session checkpoint
        checkpoint_id = manager.create(
            name="session_checkpoint",
            reason="Session interrupted",
            metadata={
                "session_id": "session-123",
                "task_id": 42,
                "operation": "implementation",
            },
            db_paths=[db_path],
        )

        # Modify session state (simulating interruption)
        conn = sqlite3.connect(db_path)
        conn.execute("UPDATE session_state SET status='interrupted' WHERE id=1")
        conn.commit()
        conn.close()

        # Resume session
        manager.restore(checkpoint_id)

        # Verify session state restored
        conn = sqlite3.connect(db_path)
        cursor = conn.execute("SELECT status FROM session_state WHERE id=1")
        status = cursor.fetchone()[0]
        conn.close()

        assert status == "in_progress"

    def test_find_latest_checkpoint_by_session(self, session_checkpoint_manager):
        """Test finding latest checkpoint for a session."""
        manager, db_path = session_checkpoint_manager

        # Create multiple checkpoints for same session
        for i in range(3):
            manager.create(
                name=f"session_checkpoint_{i}",
                reason=f"Session checkpoint {i}",
                metadata={"session_id": "session-123"},
                db_paths=[db_path],
            )

        # Find latest checkpoint
        latest = manager.find_latest_checkpoint_by_session("session-123")
        assert latest is not None
        assert latest.name == "session_checkpoint_2"

    def test_resume_from_specific_checkpoint(self, session_checkpoint_manager):
        """Test resuming from a specific checkpoint."""
        manager, db_path = session_checkpoint_manager

        # Create checkpoints
        checkpoint1 = manager.create(
            name="checkpoint_1", reason="First checkpoint", db_paths=[db_path]
        )

        # Modify state
        conn = sqlite3.connect(db_path)
        conn.execute("INSERT INTO session_state VALUES (2, 43, 'pending', 'data 2')")
        conn.commit()
        conn.close()

        checkpoint2 = manager.create(
            name="checkpoint_2", reason="Second checkpoint", db_paths=[db_path]
        )

        # Resume from first checkpoint
        manager.restore(checkpoint1)

        # Verify restored to first checkpoint state
        conn = sqlite3.connect(db_path)
        cursor = conn.execute("SELECT COUNT(*) FROM session_state")
        count = cursor.fetchone()[0]
        conn.close()

        assert count == 1


class TestAutomaticCheckpointPolicy:
    """Test automatic checkpoint policy."""

    @pytest.fixture
    def policy_manager(self):
        """Create CheckpointManager with policy configuration."""
        temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(temp_dir, "test.db")

        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY)")
        conn.commit()
        conn.close()

        manager = CheckpointManager(
            checkpoint_dir=os.path.join(temp_dir, "checkpoints"),
            policy={
                "before_task": True,
                "after_task": True,
                "max_age_hours": 24,
                "max_count": 5,
            },
        )
        yield manager, db_path

        shutil.rmtree(temp_dir)

    def test_before_task_checkpoint(self, policy_manager):
        """Test automatic checkpoint before task."""
        manager, db_path = policy_manager

        checkpoint_id = manager.create_before_task(task_id=42, db_paths=[db_path])

        assert checkpoint_id is not None
        checkpoint = manager.get_checkpoint(checkpoint_id)
        assert checkpoint.metadata["task_id"] == 42
        assert checkpoint.reason == "before_task"

    def test_after_task_checkpoint(self, policy_manager):
        """Test automatic checkpoint after task."""
        manager, db_path = policy_manager

        checkpoint_id = manager.create_after_task(task_id=42, db_paths=[db_path])

        assert checkpoint_id is not None
        checkpoint = manager.get_checkpoint(checkpoint_id)
        assert checkpoint.metadata["task_id"] == 42
        assert checkpoint.reason == "after_task"

    def test_checkpoint_cleanup_by_count(self, policy_manager):
        """Test automatic checkpoint cleanup by count."""
        manager, db_path = policy_manager

        # Create more checkpoints than max_count (5)
        for i in range(7):
            manager.create(
                name=f"checkpoint_{i}", reason=f"Checkpoint {i}", db_paths=[db_path]
            )

        # Run cleanup
        manager.cleanup_old_checkpoints()

        # Verify only max_count checkpoints remain
        checkpoints = manager.list_checkpoints()
        assert len(checkpoints) <= 5

    def test_checkpoint_cleanup_by_age(self, policy_manager):
        """Test automatic checkpoint cleanup by age."""
        manager, db_path = policy_manager

        # Create a checkpoint
        manager.create(
            name="old_checkpoint", reason="Old checkpoint", db_paths=[db_path]
        )

        # Manually modify timestamp to simulate old checkpoint
        checkpoints = manager.list_checkpoints()
        if checkpoints:
            old_checkpoint = checkpoints[0]
            # Modify timestamp to be older than max_age_hours
            old_checkpoint.created_at = datetime.fromtimestamp(
                time.time() - (25 * 3600)  # 25 hours ago
            )

        # Run cleanup
        manager.cleanup_old_checkpoints()

        # Verify old checkpoint was removed
        remaining = manager.list_checkpoints()
        old_exists = any(c.name == "old_checkpoint" for c in remaining)
        assert not old_exists

    def test_critical_checkpoint_not_cleaned(self, policy_manager):
        """Test that critical checkpoints are not cleaned up."""
        manager, db_path = policy_manager

        # Create a critical checkpoint
        manager.create(
            name="critical_checkpoint",
            reason="Critical checkpoint",
            metadata={"critical": True},
            db_paths=[db_path],
        )

        # Create many other checkpoints
        for i in range(6):
            manager.create(
                name=f"checkpoint_{i}", reason=f"Checkpoint {i}", db_paths=[db_path]
            )

        # Run cleanup
        manager.cleanup_old_checkpoints()

        # Verify critical checkpoint still exists
        checkpoints = manager.list_checkpoints()
        critical_exists = any(c.name == "critical_checkpoint" for c in checkpoints)
        assert critical_exists

    def test_before_refactor_checkpoint(self, policy_manager):
        """Test checkpoint before refactoring."""
        manager, db_path = policy_manager

        checkpoint_id = manager.create_before_refactor(db_paths=[db_path])

        assert checkpoint_id is not None
        checkpoint = manager.get_checkpoint(checkpoint_id)
        assert checkpoint.reason == "before_refactor"

    def test_on_error_checkpoint(self, policy_manager):
        """Test automatic checkpoint on error."""
        manager, db_path = policy_manager

        try:
            with manager.auto_checkpoint_on_error(db_paths=[db_path]):
                raise ValueError("Simulated error")
        except ValueError:
            pass

        # Verify checkpoint was created
        checkpoints = manager.list_checkpoints()
        error_checkpoint = [c for c in checkpoints if c.reason == "on_error"]
        assert len(error_checkpoint) >= 1


class TestCheckpointGarbageCollection:
    """Test checkpoint garbage collection."""

    @pytest.fixture
    def gc_manager(self):
        """Create CheckpointManager for garbage collection tests."""
        temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(temp_dir, "test.db")

        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY)")
        conn.commit()
        conn.close()

        manager = CheckpointManager(
            checkpoint_dir=os.path.join(temp_dir, "checkpoints")
        )
        yield manager, db_path

        shutil.rmtree(temp_dir)

    def test_delete_checkpoint(self, gc_manager):
        """Test deleting a specific checkpoint."""
        manager, db_path = gc_manager

        checkpoint_id = manager.create(
            name="to_delete", reason="Will be deleted", db_paths=[db_path]
        )

        # Verify checkpoint exists
        assert len(manager.list_checkpoints()) == 1

        # Delete checkpoint
        manager.delete_checkpoint(checkpoint_id)

        # Verify checkpoint deleted
        assert len(manager.list_checkpoints()) == 0

    def test_delete_multiple_checkpoints(self, gc_manager):
        """Test deleting multiple checkpoints."""
        manager, db_path = gc_manager

        # Create multiple checkpoints
        checkpoint_ids = []
        for i in range(3):
            checkpoint_id = manager.create(
                name=f"checkpoint_{i}", reason=f"Checkpoint {i}", db_paths=[db_path]
            )
            checkpoint_ids.append(checkpoint_id)

        # Delete first two
        manager.delete_checkpoints(checkpoint_ids[:2])

        # Verify only one remains
        checkpoints = manager.list_checkpoints()
        assert len(checkpoints) == 1
        assert checkpoints[0].id == checkpoint_ids[2]

    def test_clear_all_checkpoints(self, gc_manager):
        """Test clearing all checkpoints."""
        manager, db_path = gc_manager

        # Create checkpoints
        for i in range(5):
            manager.create(
                name=f"checkpoint_{i}", reason=f"Checkpoint {i}", db_paths=[db_path]
            )

        # Clear all
        manager.clear_all_checkpoints()

        # Verify all deleted
        assert len(manager.list_checkpoints()) == 0

    def test_archive_old_checkpoints(self, gc_manager):
        """Test archiving old checkpoints instead of deleting."""
        manager, db_path = gc_manager

        # Create old checkpoint
        manager.create(
            name="old_checkpoint",
            reason="Old checkpoint to archive",
            db_paths=[db_path],
        )

        # Archive old checkpoints
        archived = manager.archive_old_checkpoints(max_age_hours=24)

        # Verify checkpoint was archived
        assert archived >= 1

    def test_get_checkpoint_statistics(self, gc_manager):
        """Test getting checkpoint statistics."""
        manager, db_path = gc_manager

        # Create checkpoints
        for i in range(5):
            manager.create(
                name=f"checkpoint_{i}", reason=f"Checkpoint {i}", db_paths=[db_path]
            )

        # Get statistics
        stats = manager.get_statistics()

        assert stats["total_checkpoints"] == 5
        assert stats["total_size_mb"] > 0
        assert "oldest_checkpoint" in stats
        assert "newest_checkpoint" in stats


class TestCheckpointPerformance:
    """Performance tests for checkpoint operations."""

    @pytest.fixture
    def performance_manager(self):
        """Create CheckpointManager for performance tests."""
        temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(temp_dir, "test.db")

        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, data TEXT)")
        for i in range(100):
            conn.execute(f"INSERT INTO test VALUES ({i}, 'data {i}')")
        conn.commit()
        conn.close()

        manager = CheckpointManager(
            checkpoint_dir=os.path.join(temp_dir, "checkpoints")
        )
        yield manager, db_path

        shutil.rmtree(temp_dir)

    def test_large_checkpoint_creation_time(self, performance_manager):
        """Test checkpoint creation performance with large database."""
        manager, db_path = performance_manager

        start_time = time.time()
        checkpoint_id = manager.create(
            name="large_checkpoint",
            reason="Large database checkpoint",
            db_paths=[db_path],
        )
        creation_time = time.time() - start_time

        assert checkpoint_id is not None
        # Should complete in reasonable time (< 2 seconds for 100 rows)
        assert creation_time < 2.0

    def test_large_checkpoint_restore_time(self, performance_manager):
        """Test checkpoint restore performance with large database."""
        manager, db_path = performance_manager

        checkpoint_id = manager.create(
            name="restore_test", reason="Test restore performance", db_paths=[db_path]
        )

        # Modify database
        conn = sqlite3.connect(db_path)
        conn.execute("DELETE FROM test WHERE id > 50")
        conn.commit()
        conn.close()

        # Measure restore time
        start_time = time.time()
        manager.restore(checkpoint_id)
        restore_time = time.time() - start_time

        # Verify restored
        conn = sqlite3.connect(db_path)
        cursor = conn.execute("SELECT COUNT(*) FROM test")
        count = cursor.fetchone()[0]
        conn.close()

        assert count == 100
        # Should restore in reasonable time (< 2 seconds)
        assert restore_time < 2.0

    def test_concurrent_checkpoint_creation(self, performance_manager):
        """Test creating checkpoints concurrently."""
        manager, db_path = performance_manager

        import threading

        def create_checkpoint(index):
            manager.create(
                name=f"concurrent_{index}",
                reason=f"Concurrent checkpoint {index}",
                db_paths=[db_path],
            )

        threads = []
        start_time = time.time()

        for i in range(10):
            thread = threading.Thread(target=create_checkpoint, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        elapsed_time = time.time() - start_time

        # Verify all checkpoints created
        assert len(manager.list_checkpoints()) >= 10
        # Should complete in reasonable time (< 5 seconds for 10 concurrent)
        assert elapsed_time < 5.0


class TestCheckpointEdgeCases:
    """Test edge cases and error handling."""

    @pytest.fixture
    def edge_case_manager(self):
        """Create CheckpointManager for edge case tests."""
        temp_dir = tempfile.mkdtemp()
        manager = CheckpointManager(
            checkpoint_dir=os.path.join(temp_dir, "checkpoints")
        )
        yield manager

        shutil.rmtree(temp_dir)

    def test_create_checkpoint_with_invalid_db_path(self, edge_case_manager):
        """Test creating checkpoint with non-existent database path."""
        with pytest.raises(CheckpointError):
            edge_case_manager.create(
                name="invalid",
                reason="Invalid path",
                db_paths=["/nonexistent/path/to/db.db"],
            )

    def test_restore_with_locked_database(self, edge_case_manager):
        """Test restore when database is locked."""
        temp_dir = os.path.dirname(edge_case_manager.checkpoint_dir)
        db_path = os.path.join(temp_dir, "test.db")

        # Create database
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY)")
        conn.commit()

        # Create checkpoint
        checkpoint_id = edge_case_manager.create(
            name="locked", reason="Test locked database", db_paths=[db_path]
        )

        # Lock database (keep connection open)
        # This should work as checkpoint creates its own backup
        edge_case_manager.restore(checkpoint_id)

        conn.close()

    def test_checkpoint_with_empty_metadata(self, edge_case_manager):
        """Test creating checkpoint with empty metadata."""
        temp_dir = os.path.dirname(edge_case_manager.checkpoint_dir)
        db_path = os.path.join(temp_dir, "test.db")

        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY)")
        conn.commit()
        conn.close()

        # Should accept empty metadata
        checkpoint_id = edge_case_manager.create(
            name="empty_metadata",
            reason="Test empty metadata",
            metadata={},
            db_paths=[db_path],
        )

        assert checkpoint_id is not None

    def test_get_nonexistent_checkpoint(self, edge_case_manager):
        """Test getting a non-existent checkpoint."""
        checkpoint = edge_case_manager.get_checkpoint("non-existent-id")
        assert checkpoint is None

    def test_restore_to_same_state(self, edge_case_manager):
        """Test restoring checkpoint when database is already at that state."""
        temp_dir = os.path.dirname(edge_case_manager.checkpoint_dir)
        db_path = os.path.join(temp_dir, "test.db")

        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, data TEXT)")
        conn.execute("INSERT INTO test VALUES (1, 'data')")
        conn.commit()
        conn.close()

        checkpoint_id = edge_case_manager.create(
            name="same_state", reason="Test same state restore", db_paths=[db_path]
        )

        # Restore without making changes
        edge_case_manager.restore(checkpoint_id)

        # Verify state unchanged
        conn = sqlite3.connect(db_path)
        cursor = conn.execute("SELECT data FROM test WHERE id=1")
        data = cursor.fetchone()[0]
        conn.close()

        assert data == "data"
