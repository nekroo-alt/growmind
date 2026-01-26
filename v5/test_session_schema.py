"""
Test session state schema and database functions.
Tests Task 5.1: Session State Schema
"""

import os
import sqlite3
from v5.data import (
    init_db,
    create_session,
    end_session,
    get_session,
    list_sessions,
    get_active_session,
    track_session_operation,
    update_session_operation_status,
    get_session_operations,
    add_session_checkpoint,
    get_session_checkpoints,
    save_session_config,
    load_session_config,
    get_session_config,
    archive_session,
    delete_session,
    get_session_statistics,
    SESSIONS_DB_PATH,
)


def test_session_schema_initialization():
    """Test that sessions database is initialized correctly."""
    print("Testing session schema initialization...")

    # Initialize database
    init_db()

    # Check that sessions.db exists
    assert os.path.exists(SESSIONS_DB_PATH), "sessions.db should exist after init_db()"

    # Check table structure
    conn = sqlite3.connect(SESSIONS_DB_PATH)
    cursor = conn.cursor()

    # Check sessions table
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='sessions'"
    )
    assert cursor.fetchone() is not None, "sessions table should exist"

    # Check session_operations table
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='session_operations'"
    )
    assert cursor.fetchone() is not None, "session_operations table should exist"

    # Check session_checkpoints table
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='session_checkpoints'"
    )
    assert cursor.fetchone() is not None, "session_checkpoints table should exist"

    # Check session_config table
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='session_config'"
    )
    assert cursor.fetchone() is not None, "session_config table should exist"

    # Check indexes
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_sessions_status'"
    )
    assert cursor.fetchone() is not None, "idx_sessions_status index should exist"

    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_session_ops_session'"
    )
    assert cursor.fetchone() is not None, "idx_session_ops_session index should exist"

    conn.close()
    print("✓ Session schema initialization test passed")


def test_create_and_retrieve_session():
    """Test creating and retrieving sessions."""
    print("\nTesting session creation and retrieval...")

    init_db()

    # Create a session
    session_id = create_session(
        user="test_user",
        host="localhost",
        environment="dev",
        metadata={"project": "test_project"},
    )

    assert session_id is not None, "Session ID should be returned"
    assert len(session_id) > 0, "Session ID should not be empty"

    # Retrieve the session
    session = get_session(session_id)
    assert session is not None, "Session should be retrievable"
    assert session["session_id"] == session_id, "Session ID should match"
    assert session["status"] == "active", "New session should be active"
    assert session["user"] == "test_user", "User should match"
    assert session["host"] == "localhost", "Host should match"
    assert session["environment"] == "dev", "Environment should match"
    assert session["metadata"] is not None, "Metadata should be retrievable"
    assert session["metadata"]["project"] == "test_project", "Metadata should match"
    assert session["start_time"] is not None, "Start time should be set"
    assert session["end_time"] is None, "End time should be None for active session"

    print("✓ Session creation and retrieval test passed")


def test_list_and_filter_sessions():
    """Test listing and filtering sessions."""
    print("\nTesting session listing and filtering...")

    init_db()

    # Create multiple sessions
    session_id1 = create_session(user="user1", environment="dev")
    session_id2 = create_session(user="user2", environment="prod")
    session_id3 = create_session(user="user1", environment="dev")

    # End one session
    end_session(session_id1, status="completed")

    # List all sessions
    all_sessions = list_sessions()
    assert len(all_sessions) >= 3, "Should have at least 3 sessions"

    # List only active sessions
    active_sessions = list_sessions(status="active")
    assert len(active_sessions) >= 2, "Should have at least 2 active sessions"
    for session in active_sessions:
        assert session["status"] == "active", "All should be active"

    # List with limit
    limited_sessions = list_sessions(limit=2)
    assert len(limited_sessions) == 2, "Should respect limit"

    # Get active session
    active_session = get_active_session()
    assert active_session is not None, "Should have an active session"
    assert active_session["status"] == "active", "Should be active"

    print("✓ Session listing and filtering test passed")


def test_session_operations():
    """Test tracking operations within a session."""
    print("\nTesting session operations tracking...")

    init_db()

    # Create a session
    session_id = create_session(user="test_user")

    # Track some operations
    op_id1 = track_session_operation(
        session_id=session_id,
        operation_id="op_001",
        operation_type="implementation",
        task_id=1,
        status="in_progress",
    )

    op_id2 = track_session_operation(
        session_id=session_id,
        operation_id="op_002",
        operation_type="verification",
        task_id=1,
        status="completed",
    )

    assert op_id1 is not None, "Operation ID 1 should be returned"
    assert op_id2 is not None, "Operation ID 2 should be returned"

    # Update operation status
    update_session_operation_status(op_id1, status="completed")

    # Get all operations
    operations = get_session_operations(session_id)
    assert len(operations) >= 2, "Should have at least 2 operations"

    # Filter by operation type
    impl_ops = get_session_operations(session_id, operation_type="implementation")
    assert len(impl_ops) >= 1, "Should have at least 1 implementation operation"

    # Filter by status
    completed_ops = get_session_operations(session_id, status="completed")
    assert len(completed_ops) >= 1, "Should have at least 1 completed operation"

    print("✓ Session operations tracking test passed")


def test_session_checkpoints():
    """Test checkpoint association with sessions."""
    print("\nTesting session checkpoints...")

    init_db()

    # Create a session
    session_id = create_session(user="test_user")

    # Add checkpoints
    add_session_checkpoint(
        session_id=session_id,
        checkpoint_id="chk_001",
        reason="Before task implementation",
        is_auto=True,
    )

    add_session_checkpoint(
        session_id=session_id,
        checkpoint_id="chk_002",
        reason="After task completion",
        is_auto=False,
    )

    # Get all checkpoints
    checkpoints = get_session_checkpoints(session_id)
    assert len(checkpoints) >= 2, "Should have at least 2 checkpoints"

    # Get only automatic checkpoints
    auto_checkpoints = get_session_checkpoints(session_id, auto_only=True)
    assert len(auto_checkpoints) >= 1, "Should have at least 1 auto checkpoint"
    for cp in auto_checkpoints:
        assert cp["is_auto"] == 1, "All should be auto checkpoints"

    print("✓ Session checkpoints test passed")


def test_session_configuration():
    """Test session configuration storage."""
    print("\nTesting session configuration...")

    init_db()

    # Create a session
    session_id = create_session(user="test_user")

    # Save configuration
    save_session_config(session_id, "llm.model", "gpt-4")
    save_session_config(session_id, "llm.temperature", "0.7")
    save_session_config(session_id, "cache.enabled", "true")

    # Load single config value
    model = load_session_config(session_id, "llm.model")
    assert model == "gpt-4", "Model should match"

    temperature = load_session_config(session_id, "llm.temperature")
    assert temperature == "0.7", "Temperature should match"

    # Get all config
    config = get_session_config(session_id)
    assert len(config) >= 3, "Should have at least 3 config values"
    assert config["llm.model"] == "gpt-4", "Config should be complete"
    assert config["llm.temperature"] == "0.7", "Config should be complete"
    assert config["cache.enabled"] == "true", "Config should be complete"

    # Test updating existing config
    save_session_config(session_id, "llm.temperature", "0.8")
    temperature = load_session_config(session_id, "llm.temperature")
    assert temperature == "0.8", "Config should be updated"

    print("✓ Session configuration test passed")


def test_session_lifecycle():
    """Test complete session lifecycle."""
    print("\nTesting session lifecycle...")

    init_db()

    # Create session
    session_id = create_session(user="test_user", environment="dev")

    # Add operations and checkpoints
    track_session_operation(session_id, "op_001", "implementation", 1, "completed")
    add_session_checkpoint(session_id, "chk_001", "Test checkpoint", True)

    # End session
    end_session(session_id, status="completed")

    # Verify session is ended
    session = get_session(session_id)
    assert session is not None, "Session should still exist"
    assert session["status"] == "completed", "Session should be completed"
    assert session["end_time"] is not None, "End time should be set"

    # Archive session
    archive_session(session_id)

    session = get_session(session_id)
    assert session["status"] == "archived", "Session should be archived"

    # Create another session for delete test
    session_id2 = create_session(user="test_user2")

    # Delete session
    delete_session(session_id2)

    session2 = get_session(session_id2)
    assert session2 is None, "Deleted session should not exist"

    print("✓ Session lifecycle test passed")


def test_session_statistics():
    """Test session statistics calculation."""
    print("\nTesting session statistics...")

    init_db()

    # Create a session
    session_id = create_session(user="test_user")

    # Track operations
    op1 = track_session_operation(
        session_id, "op_001", "implementation", 1, "in_progress"
    )
    update_session_operation_status(op1, "completed")

    op2 = track_session_operation(
        session_id, "op_002", "verification", 1, "in_progress"
    )
    update_session_operation_status(op2, "completed")

    op3 = track_session_operation(
        session_id, "op_003", "implementation", 2, "in_progress"
    )
    update_session_operation_status(op3, "failed")

    # Add checkpoints
    add_session_checkpoint(session_id, "chk_001", "Auto checkpoint 1", True)
    add_session_checkpoint(session_id, "chk_002", "Manual checkpoint", False)
    add_session_checkpoint(session_id, "chk_003", "Auto checkpoint 2", True)

    # Get statistics
    stats = get_session_statistics(session_id)

    assert stats["total_operations"] >= 3, "Should have at least 3 operations"
    assert stats["completed_operations"] >= 2, "Should have at least 2 completed"
    assert stats["failed_operations"] >= 1, "Should have at least 1 failed"
    assert stats["total_checkpoints"] >= 3, "Should have at least 3 checkpoints"
    assert stats["auto_checkpoints"] >= 2, "Should have at least 2 auto checkpoints"
    assert stats["duration_seconds"] >= 0, "Duration should be non-negative"

    print("✓ Session statistics test passed")


def test_session_with_multiple_concurrent():
    """Test handling multiple concurrent sessions."""
    print("\nTesting multiple concurrent sessions...")

    init_db()

    # Clean up any existing sessions from previous test runs
    existing_sessions = list_sessions()
    for sess in existing_sessions:
        if sess["status"] == "active":
            end_session(sess["session_id"], status="completed")

    # Create multiple sessions
    session_id1 = create_session(user="user1")
    session_id2 = create_session(user="user2")
    session_id3 = create_session(user="user1")

    # Verify they're all active
    session1 = get_session(session_id1)
    session2 = get_session(session_id2)
    session3 = get_session(session_id3)

    assert session1["status"] == "active", "Session 1 should be active"
    assert session2["status"] == "active", "Session 2 should be active"
    assert session3["status"] == "active", "Session 3 should be active"

    # End session 2
    end_session(session_id2, status="completed")

    # Get active session - should return the most recent active one
    active = get_active_session()
    assert active is not None, "Should have an active session"
    # Note: Since we cleaned up all sessions first, we should only have our test sessions

    print("✓ Multiple concurrent sessions test passed")


def run_all_tests():
    """Run all session schema tests."""
    print("=" * 60)
    print("Testing Task 5.1: Session State Schema")
    print("=" * 60)

    test_session_schema_initialization()
    test_create_and_retrieve_session()
    test_list_and_filter_sessions()
    test_session_operations()
    test_session_checkpoints()
    test_session_configuration()
    test_session_lifecycle()
    test_session_statistics()
    test_session_with_multiple_concurrent()

    print("\n" + "=" * 60)
    print("All tests passed! ✓")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
