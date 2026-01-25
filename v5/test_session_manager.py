"""
Tests for Session Manager Module.

Tests session lifecycle management, persistence, and operations.
"""

import os
import json
import pytest
from datetime import datetime
from pathlib import Path
from core.session_manager import (
    Session,
    SessionStatus,
    SessionManager,
    get_session_manager,
)


@pytest.fixture
def db_path(tmp_path):
    """Provide a temporary database path."""
    return str(tmp_path / "test_sessions.db")


@pytest.fixture
def manager(db_path):
    """Provide a SessionManager instance with a temporary database."""
    return SessionManager(db_path)


def test_session_creation(manager):
    """Test creating a new session."""
    config = {"llm_model": "gpt-4", "cache_enabled": True}
    metadata = {"user": "developer", "environment": "dev"}

    session = manager.start_session(config=config, metadata=metadata)

    assert session.session_id is not None
    assert isinstance(session.session_id, str)
    assert session.status == SessionStatus.ACTIVE
    assert session.config == config
    assert session.metadata == metadata
    assert session.start_time is not None
    assert isinstance(session.start_time, datetime)
    assert session.end_time is None


def test_session_persistence(manager):
    """Test that sessions are persisted to database."""
    session = manager.start_session(config={"test": "value"}, metadata={"user": "test"})

    # Load the session from database
    loaded_session = manager._load_session(session.session_id)

    assert loaded_session is not None
    assert loaded_session.session_id == session.session_id
    assert loaded_session.status == session.status
    assert loaded_session.config == session.config
    assert loaded_session.metadata == session.metadata
    assert loaded_session.start_time == session.start_time


def test_resume_session(manager):
    """Test resuming an existing session."""
    # Create and pause a session
    session = manager.start_session()
    assert manager.pause_session(session.session_id) is True

    # Resume the session
    resumed_session = manager.resume_session(session.session_id)

    assert resumed_session is not None
    assert resumed_session.session_id == session.session_id
    assert resumed_session.status == SessionStatus.ACTIVE


def test_resume_invalid_session(manager):
    """Test resuming a non-existent session."""
    resumed = manager.resume_session("non-existent-id")
    assert resumed is None


def test_pause_session(manager):
    """Test pausing an active session."""
    session = manager.start_session()

    result = manager.pause_session(session.session_id)

    assert result is True

    # Verify session is paused
    loaded = manager._load_session(session.session_id)
    assert loaded.status == SessionStatus.PAUSED


def test_pause_invalid_session(manager):
    """Test pausing a non-existent session."""
    result = manager.pause_session("non-existent-id")
    assert result is False


def test_pause_already_paused_session(manager):
    """Test pausing a session that's already paused."""
    session = manager.start_session()
    manager.pause_session(session.session_id)

    # Try to pause again
    result = manager.pause_session(session.session_id)
    assert result is False


def test_complete_session(manager):
    """Test completing a session."""
    session = manager.start_session()

    result = manager.complete_session(session.session_id)

    assert result is True

    # Verify session is completed with end time
    loaded = manager._load_session(session.session_id)
    assert loaded.status == SessionStatus.COMPLETED
    assert loaded.end_time is not None
    assert isinstance(loaded.end_time, datetime)


def test_complete_invalid_session(manager):
    """Test completing a non-existent session."""
    result = manager.complete_session("non-existent-id")
    assert result is False


def test_list_sessions(manager):
    """Test listing sessions."""
    # Create multiple sessions
    session1 = manager.start_session()
    session2 = manager.start_session()
    session3 = manager.start_session()

    manager.pause_session(session2.session_id)
    manager.complete_session(session3.session_id)

    # List all sessions
    all_sessions = manager.list_sessions()
    assert len(all_sessions) == 3

    # List only active sessions
    active_sessions = manager.list_sessions(status=SessionStatus.ACTIVE)
    assert len(active_sessions) == 1
    assert active_sessions[0].session_id == session1.session_id

    # List only paused sessions
    paused_sessions = manager.list_sessions(status=SessionStatus.PAUSED)
    assert len(paused_sessions) == 1
    assert paused_sessions[0].session_id == session2.session_id


def test_list_sessions_with_limit(manager):
    """Test listing sessions with limit."""
    # Create 5 sessions
    for _ in range(5):
        manager.start_session()

    # List with limit
    limited_sessions = manager.list_sessions(limit=3)
    assert len(limited_sessions) == 3


def test_archive_session(manager):
    """Test archiving a session."""
    session = manager.start_session()

    result = manager.archive_session(session.session_id)

    assert result is True

    # Verify session is archived
    loaded = manager._load_session(session.session_id)
    assert loaded.status == SessionStatus.ARCHIVED
    assert loaded.end_time is not None


def test_archive_already_archived_session(manager):
    """Test archiving a session that's already archived."""
    session = manager.start_session()
    manager.archive_session(session.session_id)

    # Try to archive again
    result = manager.archive_session(session.session_id)
    assert result is False


def test_archive_invalid_session(manager):
    """Test archiving a non-existent session."""
    result = manager.archive_session("non-existent-id")
    assert result is False


def test_export_session(manager, tmp_path):
    """Test exporting a session to JSON."""
    session = manager.start_session(config={"test": "value"}, metadata={"user": "test"})

    export_path = tmp_path / "session_export.json"

    result = manager.export_session(session.session_id, str(export_path))

    assert result is True
    assert export_path.exists()

    # Verify export content
    with open(export_path, "r") as f:
        data = json.load(f)

    assert "session" in data
    assert "exported_at" in data
    assert "version" in data
    assert data["session"]["session_id"] == session.session_id
    assert data["session"]["config"] == {"test": "value"}


def test_export_invalid_session(manager, tmp_path):
    """Test exporting a non-existent session."""
    export_path = tmp_path / "session_export.json"

    result = manager.export_session("non-existent-id", str(export_path))

    assert result is False
    assert not export_path.exists()


def test_import_session(manager, tmp_path):
    """Test importing a session from JSON."""
    # Create export data
    export_data = {
        "session": {
            "session_id": "original-id",
            "start_time": datetime.now().isoformat(),
            "status": "paused",
            "config": {"test": "value"},
            "metadata": {"user": "test"},
            "active_operations": [],
            "active_tasks": [],
            "checkpoint_id": None,
            "end_time": None,
        },
        "exported_at": datetime.now().isoformat(),
        "version": "1.0",
    }

    export_path = tmp_path / "session_export.json"
    with open(export_path, "w") as f:
        json.dump(export_data, f)

    # Import session
    imported = manager.import_session(str(export_path))

    assert imported is not None
    assert imported.session_id != "original-id"  # Should have new ID
    assert imported.status == SessionStatus.PAUSED
    assert imported.config == {"test": "value"}
    assert imported.metadata == {"user": "test"}


def test_import_invalid_file(manager, tmp_path):
    """Test importing from a non-existent file."""
    result = manager.import_session(str(tmp_path / "nonexistent.json"))
    assert result is None


def test_import_corrupt_file(manager, tmp_path):
    """Test importing from a corrupt JSON file."""
    corrupt_path = tmp_path / "corrupt.json"
    with open(corrupt_path, "w") as f:
        f.write("invalid json")

    result = manager.import_session(str(corrupt_path))
    assert result is None


def test_merge_sessions(manager):
    """Test merging two sessions."""
    session1 = manager.start_session(
        config={"model": "gpt-4"}, metadata={"user": "user1"}
    )
    session1.active_operations = ["op1", "op2"]
    session1.active_tasks = [1, 2]
    manager._save_session(session1)

    session2 = manager.start_session(
        config={"model": "gpt-3"}, metadata={"user": "user2"}
    )
    session2.active_operations = ["op3", "op4"]
    session2.active_tasks = [3, 4]
    session2.metadata["environment"] = "prod"
    manager._save_session(session2)

    # Merge session1 into session2
    result = manager.merge_sessions(session1.session_id, session2.session_id)

    assert result is True

    # Verify merge
    merged = manager._load_session(session2.session_id)
    assert len(merged.active_operations) == 4  # All operations
    assert len(merged.active_tasks) == 4  # All tasks
    assert merged.metadata["user"] == "user2"  # Kept target's user
    assert merged.metadata["environment"] == "prod"  # Merged metadata


def test_merge_invalid_sessions(manager):
    """Test merging with invalid session IDs."""
    result = manager.merge_sessions("invalid1", "invalid2")
    assert result is False


def test_merge_with_completed_session(manager):
    """Test merging with a completed session (should fail)."""
    session1 = manager.start_session()
    session2 = manager.start_session()
    manager.complete_session(session2.session_id)

    # Try to merge into completed session
    result = manager.merge_sessions(session1.session_id, session2.session_id)
    assert result is False


def test_get_active_session(manager):
    """Test getting the currently active session."""
    # No active session initially
    active = manager.get_active_session()
    assert active is None

    # Create an active session
    session = manager.start_session()
    active = manager.get_active_session()

    assert active is not None
    assert active.session_id == session.session_id
    assert active.status == SessionStatus.ACTIVE


def test_cleanup_old_sessions(manager):
    """Test cleaning up old sessions."""
    # Create a session and manually set its start time to old date
    session = manager.start_session()
    # Complete the session first
    manager.complete_session(session.session_id)

    old_time = datetime.now().timestamp() - (31 * 24 * 60 * 60)  # 31 days ago

    # Manually update the session in database
    with manager.lock:
        import sqlite3

        conn = sqlite3.connect(manager.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE sessions 
            SET start_time = datetime(?, 'unixepoch')
            WHERE session_id = ?
        """,
            (old_time, session.session_id),
        )
        conn.commit()
        conn.close()

    # Create a recent session
    recent_session = manager.start_session()

    # Cleanup old sessions (older than 30 days)
    archived_count = manager.cleanup_old_sessions(days=30)

    assert archived_count == 1

    # Verify old session is archived
    old_session_loaded = manager._load_session(session.session_id)
    assert old_session_loaded.status == SessionStatus.ARCHIVED

    # Verify recent session is still active
    recent_session_loaded = manager._load_session(recent_session.session_id)
    assert recent_session_loaded.status == SessionStatus.ACTIVE


def test_session_serialization():
    """Test Session to_dict and from_dict methods."""
    session = Session(
        session_id="test-id",
        start_time=datetime.now(),
        status=SessionStatus.ACTIVE,
        config={"test": "value"},
        metadata={"user": "test"},
        active_operations=["op1", "op2"],
        active_tasks=[1, 2],
        checkpoint_id="chkp-123",
        end_time=datetime.now(),
    )

    # Serialize
    data = session.to_dict()
    assert data["session_id"] == "test-id"
    assert data["status"] == "active"
    assert data["config"] == {"test": "value"}
    assert data["active_operations"] == ["op1", "op2"]

    # Deserialize
    restored = Session.from_dict(data)
    assert restored.session_id == session.session_id
    assert restored.status == session.status
    assert restored.config == session.config
    assert restored.active_operations == session.active_operations


def test_session_validation(manager):
    """Test session validation."""
    # Create valid session
    session = manager.start_session()
    assert manager._validate_session(session) is True

    # Test with invalid session (no ID)
    invalid_session = Session(
        session_id="", start_time=datetime.now(), status=SessionStatus.ACTIVE
    )
    assert manager._validate_session(invalid_session) is False

    # Test with corrupted session
    session.status = SessionStatus.CORRUPTED
    assert manager._validate_session(session) is False


def test_thread_safety(manager):
    """Test that SessionManager is thread-safe."""
    import threading

    sessions = []

    def create_session():
        session = manager.start_session()
        sessions.append(session)

    # Create sessions from multiple threads
    threads = [threading.Thread(target=create_session) for _ in range(10)]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    # Verify all sessions were created
    assert len(sessions) == 10
    assert len(set(s.session_id for s in sessions)) == 10  # All unique IDs


def test_get_session_manager_singleton():
    """Test get_session_manager returns singleton instance."""
    manager1 = get_session_manager(":memory:")
    manager2 = get_session_manager(":memory:")

    # Should be the same instance
    assert manager1 is manager2


def test_session_checkpoints_table(manager):
    """Test that session_checkpoints table is created."""
    import sqlite3

    conn = sqlite3.connect(manager.db_path)
    cursor = conn.cursor()

    # Check table exists
    cursor.execute(
        """
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='session_checkpoints'
    """
    )
    result = cursor.fetchone()

    assert result is not None
    assert result[0] == "session_checkpoints"

    conn.close()


def test_database_indexes(manager):
    """Test that database indexes are created."""
    import sqlite3

    conn = sqlite3.connect(manager.db_path)
    cursor = conn.cursor()

    # Check indexes exist
    cursor.execute(
        """
        SELECT name FROM sqlite_master 
        WHERE type='index' AND tbl_name='sessions'
    """
    )
    indexes = [row[0] for row in cursor.fetchall()]

    assert "idx_sessions_status" in indexes
    assert "idx_sessions_start_time" in indexes

    conn.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
