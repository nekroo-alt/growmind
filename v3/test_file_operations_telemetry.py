"""
Test file operations telemetry (Task 1.4)

Tests for file read/write/delete tracking, git operation tracking,
and file operation queries.
"""

import os
import tempfile
import sqlite3

from data.telemetry_manager import TelemetryManager


def test_file_operations_table_created():
    """Test that file_operations table is created properly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_telemetry.db")
        telemetry = TelemetryManager(db_path)

        # Check if table exists
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='file_operations'"
        )
        result = cursor.fetchone()
        conn.close()

        assert result is not None, "file_operations table should exist"
        print("✓ File operations table created successfully")


def test_record_file_read():
    """Test recording a file read operation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_telemetry.db")
        telemetry = TelemetryManager(db_path)

        # Create a test file
        test_file = os.path.join(tmpdir, "test.txt")
        with open(test_file, "w") as f:
            f.write("test content")

        # Record file read
        operation_id = telemetry.start_operation("test", "Test Operation")
        file_op_id = telemetry.record_file_read(
            operation_id=operation_id, file_path=test_file
        )

        # Verify that file operation was recorded
        file_ops = telemetry.get_file_operations(operation_id)
        assert len(file_ops) == 1, "Should have one file operation"
        assert file_ops[0]["operation_type"] == "read", "Should be a read operation"
        assert file_ops[0]["file_path"] == test_file, "Should have correct file path"
        assert file_ops[0]["file_size"] > 0, "Should have file size recorded"
        assert file_ops[0]["content_hash"] is not None, "Should have content hash"

        print("✓ File read recorded successfully")
        print(f"  - File path: {file_ops[0]['file_path']}")
        print(f"  - File size: {file_ops[0]['file_size']} bytes")
        print(f"  - Content hash: {file_ops[0]['content_hash']}")


def test_record_file_write():
    """Test recording a file write operation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_telemetry.db")
        telemetry = TelemetryManager(db_path)

        # Create a test file
        test_file = os.path.join(tmpdir, "test.txt")
        content = "test content"

        # Record file write
        operation_id = telemetry.start_operation("test", "Test Operation")
        file_op_id = telemetry.record_file_write(
            operation_id=operation_id,
            file_path=test_file,
            file_size=len(content),
            content_hash="abc123",
            diff_summary="Initial file creation",
        )

        # Verify that file operation was recorded
        file_ops = telemetry.get_file_operations(operation_id)
        assert len(file_ops) == 1, "Should have one file operation"
        assert file_ops[0]["operation_type"] == "write", "Should be a write operation"
        assert file_ops[0]["file_path"] == test_file, "Should have correct file path"
        assert file_ops[0]["file_size"] == len(content), "Should have correct file size"
        assert file_ops[0]["content_hash"] == "abc123", "Should have content hash"
        assert (
            file_ops[0]["diff_summary"] == "Initial file creation"
        ), "Should have diff summary"

        print("✓ File write recorded successfully")
        print(f"  - File path: {file_ops[0]['file_path']}")
        print(f"  - File size: {file_ops[0]['file_size']} bytes")
        print(f"  - Content hash: {file_ops[0]['content_hash']}")
        print(f"  - Diff summary: {file_ops[0]['diff_summary']}")


def test_record_file_delete():
    """Test recording a file delete operation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_telemetry.db")
        telemetry = TelemetryManager(db_path)

        # Create and then delete a test file
        test_file = os.path.join(tmpdir, "test.txt")
        with open(test_file, "w") as f:
            f.write("test content")
        os.remove(test_file)

        # Record file delete
        operation_id = telemetry.start_operation("test", "Test Operation")
        file_op_id = telemetry.record_file_delete(
            operation_id=operation_id, file_path=test_file
        )

        # Verify that file operation was recorded
        file_ops = telemetry.get_file_operations(operation_id)
        assert len(file_ops) == 1, "Should have one file operation"
        assert file_ops[0]["operation_type"] == "delete", "Should be a delete operation"
        assert file_ops[0]["file_path"] == test_file, "Should have correct file path"

        print("✓ File delete recorded successfully")
        print(f"  - File path: {file_ops[0]['file_path']}")


def test_record_git_operation():
    """Test recording git operations."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_telemetry.db")
        telemetry = TelemetryManager(db_path)

        # Record various git operations
        operation_id = telemetry.start_operation("test", "Test Operation")

        telemetry.record_git_operation(
            operation_id=operation_id,
            git_op_type="add",
            details={"files": ["file1.py", "file2.py"]},
        )

        telemetry.record_git_operation(
            operation_id=operation_id,
            git_op_type="commit",
            details={"hash": "abc123", "message": "Initial commit"},
        )

        telemetry.record_git_operation(
            operation_id=operation_id,
            git_op_type="checkout",
            details={"branch": "main"},
        )

        # Verify that git operations were recorded
        file_ops = telemetry.get_file_operations(operation_id)
        assert len(file_ops) == 3, "Should have three git operations"

        git_add = [op for op in file_ops if op["operation_type"] == "git_add"]
        git_commit = [op for op in file_ops if op["operation_type"] == "git_commit"]
        git_checkout = [op for op in file_ops if op["operation_type"] == "git_checkout"]

        assert len(git_add) == 1, "Should have git_add operation"
        assert len(git_commit) == 1, "Should have git_commit operation"
        assert len(git_checkout) == 1, "Should have git_checkout operation"

        print("✓ Git operations recorded successfully")
        print(f"  - git_add: {git_add[0]['metadata']}")
        print(f"  - git_commit: {git_commit[0]['metadata']}")
        print(f"  - git_checkout: {git_checkout[0]['metadata']}")


def test_get_file_operations_by_path():
    """Test querying file operations by path."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_telemetry.db")
        telemetry = TelemetryManager(db_path)

        test_file = os.path.join(tmpdir, "test.txt")

        # Record multiple operations on the same file
        operation_id1 = telemetry.start_operation("test", "Test Operation 1")
        telemetry.record_file_read(operation_id1, test_file)
        telemetry.record_file_write(
            operation_id1, test_file, file_size=100, content_hash="hash1"
        )

        operation_id2 = telemetry.start_operation("test", "Test Operation 2")
        telemetry.record_file_read(operation_id2, test_file)
        telemetry.record_file_write(
            operation_id2, test_file, file_size=150, content_hash="hash2"
        )

        # Query by path
        file_ops = telemetry.get_file_operations_by_path(test_file)
        assert len(file_ops) == 4, "Should have four operations for the file"

        # Query by path and type
        write_ops = telemetry.get_file_operations_by_path(
            test_file, operation_type="write"
        )
        assert len(write_ops) == 2, "Should have two write operations"

        print("✓ File operations queried by path successfully")
        print(f"  - Total operations: {len(file_ops)}")
        print(f"  - Write operations: {len(write_ops)}")


def test_get_modified_files():
    """Test getting list of modified files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_telemetry.db")
        telemetry = TelemetryManager(db_path)

        file1 = os.path.join(tmpdir, "file1.txt")
        file2 = os.path.join(tmpdir, "file2.txt")
        file3 = os.path.join(tmpdir, "file3.txt")

        # Record operations on multiple files
        operation_id = telemetry.start_operation("test", "Test Operation")
        telemetry.record_file_read(operation_id, file1)
        telemetry.record_file_write(operation_id, file2, file_size=100)
        telemetry.record_file_delete(operation_id, file3)
        telemetry.record_git_operation(operation_id, "add", {"files": [file1, file2]})

        # Get modified files
        modified_files = telemetry.get_modified_files(operation_id)
        assert len(modified_files) == 3, "Should have three modified files"
        assert file1 in modified_files, "Should include file1"
        assert file2 in modified_files, "Should include file2"
        assert file3 in modified_files, "Should include file3"

        print("✓ Modified files retrieved successfully")
        print(f"  - Modified files: {modified_files}")


def test_track_file_read_context_manager():
    """Test track_file_read context manager."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_telemetry.db")
        telemetry = TelemetryManager(db_path)

        test_file = os.path.join(tmpdir, "test.txt")
        with open(test_file, "w") as f:
            f.write("test content")

        # Use context manager to track file read
        operation_id = telemetry.start_operation("test", "Test Operation")
        with telemetry.track_file_read(operation_id, test_file) as f:
            content = f.read()

        # Verify that file operation was recorded
        file_ops = telemetry.get_file_operations(operation_id)
        assert len(file_ops) == 1, "Should have one file operation"
        assert file_ops[0]["operation_type"] == "read", "Should be a read operation"
        assert content == "test content", "Should have read correct content"

        print("✓ File read tracked with context manager successfully")
        print(f"  - Content read: {content}")


def test_tracked_write_file():
    """Test tracked_write_file function."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_telemetry.db")
        telemetry = TelemetryManager(db_path)

        test_file = os.path.join(tmpdir, "test.txt")
        content = "test content"

        # Use tracked_write_file
        operation_id = telemetry.start_operation("test", "Test Operation")
        telemetry.tracked_write_file(operation_id, test_file, content)

        # Verify that file was written and tracked
        file_ops = telemetry.get_file_operations(operation_id)
        assert len(file_ops) == 1, "Should have one file operation"
        assert file_ops[0]["operation_type"] == "write", "Should be a write operation"

        # Verify file content
        with open(test_file, "r") as f:
            assert f.read() == content, "File should contain correct content"

        print("✓ File write tracked successfully")
        print(f"  - Content written: {content}")
        print(f"  - Content hash: {file_ops[0]['content_hash']}")


def test_file_operations_with_metadata():
    """Test file operations with custom metadata."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_telemetry.db")
        telemetry = TelemetryManager(db_path)

        test_file = os.path.join(tmpdir, "test.txt")

        # Record file read with metadata
        operation_id = telemetry.start_operation("test", "Test Operation")
        telemetry.record_file_read(
            operation_id=operation_id,
            file_path=test_file,
            metadata={"purpose": "testing", "user": "test_user"},
        )

        # Verify that metadata was recorded
        file_ops = telemetry.get_file_operations(operation_id)
        assert len(file_ops) == 1, "Should have one file operation"
        assert file_ops[0]["metadata"] is not None, "Should have metadata"
        assert (
            file_ops[0]["metadata"]["purpose"] == "testing"
        ), "Should have purpose metadata"
        assert (
            file_ops[0]["metadata"]["user"] == "test_user"
        ), "Should have user metadata"

        print("✓ File operations with metadata recorded successfully")
        print(f"  - Metadata: {file_ops[0]['metadata']}")


def run_all_tests():
    """Run all file operations telemetry tests."""
    print("\n" + "=" * 60)
    print("Running File Operations Telemetry Tests (Task 1.4)")
    print("=" * 60 + "\n")

    tests = [
        test_file_operations_table_created,
        test_record_file_read,
        test_record_file_write,
        test_record_file_delete,
        test_record_git_operation,
        test_get_file_operations_by_path,
        test_get_modified_files,
        test_track_file_read_context_manager,
        test_tracked_write_file,
        test_file_operations_with_metadata,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
            print()
        except Exception as e:
            failed += 1
            print(f"✗ {test.__name__} FAILED: {e}\n")
            import traceback

            traceback.print_exc()

    print("=" * 60)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 60 + "\n")

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
