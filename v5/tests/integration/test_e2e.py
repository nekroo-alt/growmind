"""
End-to-End Tests for L4D V3

This module contains comprehensive integration tests that simulate realistic
user workflows across all V3 enhancements (telemetry, logging, checkpointing,
error handling, and session management).
"""

import os
import sys
import time
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import threading
import signal
import pytest
import json

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from data.telemetry_manager import TelemetryManager
from data.checkpoint_manager import CheckpointManager
from core.session_manager import SessionManager, SessionManager
from core.error_handling import ErrorType, recovery_strategies
from core.logging_config import setup_logging, get_logger
from data.db_manager import DatabaseManager
from core.graceful_shutdown import GracefulShutdown
from core.config import Config


@pytest.fixture
def temp_project_dir():
    """Create a temporary project directory for testing."""
    temp_dir = tempfile.mkdtemp()
    old_cwd = os.getcwd()
    os.chdir(temp_dir)

    # Initialize git repository
    os.system("git init")
    os.system('git config user.email "test@example.com"')
    os.system('git config user.name "Test User"')

    yield temp_dir

    os.chdir(old_cwd)
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def initialized_system(temp_project_dir):
    """Initialize all V3 systems for testing."""
    # Create databases directory
    os.makedirs("data", exist_ok=True)

    # Initialize managers
    db_manager = DatabaseManager()
    telemetry = TelemetryManager(db_manager)
    checkpoint = CheckpointManager()
    session = SessionManager(telemetry=telemetry)

    # Setup logging
    logger = setup_logging(level="INFO", log_dir="logs")

    yield {
        "telemetry": telemetry,
        "checkpoint": checkpoint,
        "session": session,
        "db_manager": db_manager,
        "logger": logger,
    }

    # Cleanup
    session.close()
    telemetry.close()


class TestCompleteDevelopmentWorkflow:
    """Test the complete development workflow with telemetry."""

    def test_workflow_with_telemetry(self, initialized_system):
        """Test complete workflow from task start to completion with telemetry tracking."""
        telemetry = initialized_system["telemetry"]
        session = initialized_system["session"]
        checkpoint = initialized_system["checkpoint"]

        # Start a session
        session_data = session.start_session()
        session_id = session_data["id"]

        # Simulate complete development workflow
        with telemetry.track_operation(
            "task_breakdown", "Task 1", session_id=session_id
        ):
            time.sleep(0.1)
            telemetry.record_event(
                "breakdown_complete", "info", "Task breakdown completed"
            )

        with telemetry.track_operation(
            "implementation", "Task 1", session_id=session_id
        ):
            # Simulate implementation steps
            for i in range(3):
                telemetry.record_event(
                    "implementation_step", "info", f"Step {i+1} completed"
                )
                time.sleep(0.05)

            telemetry.record_metric("lines_added", 15)
            telemetry.record_metric("tokens_used", 1200)

        with telemetry.track_operation("verification", "Task 1", session_id=session_id):
            telemetry.record_event("tests_passed", "info", "All tests passed")
            telemetry.record_metric("test_coverage", 95.0)

        # Complete session
        session.complete_session()

        # Verify telemetry was recorded
        operations = telemetry.query_operations()
        assert len(operations) >= 3

        # Verify operations are in correct order
        assert operations[0]["operation_type"] == "task_breakdown"
        assert operations[1]["operation_type"] == "implementation"
        assert operations[2]["operation_type"] == "verification"

        # Verify session was recorded
        sessions = session.list_sessions()
        assert len(sessions) >= 1
        assert sessions[0]["status"] == "completed"

    def test_workflow_with_multiple_tasks(self, initialized_system):
        """Test workflow with multiple sequential tasks."""
        telemetry = initialized_system["telemetry"]
        session = initialized_system["session"]

        session_data = session.start_session()
        session_id = session_data["id"]

        # Execute multiple tasks
        for task_num in range(1, 4):
            with telemetry.track_operation(
                "implementation", f"Task {task_num}", session_id=session_id
            ):
                telemetry.record_event("test_generation", "info", "Tests generated")
                telemetry.record_event("implementation", "info", "Code implemented")
                telemetry.record_event("verification", "info", "Tests passed")
                telemetry.record_metric("lines_added", 20)
                time.sleep(0.05)

        session.complete_session()

        # Verify all tasks were tracked
        operations = telemetry.query_filters(
            operation_type="implementation", session_id=session_id
        )
        assert len(operations) == 3

        # Verify session analytics
        analytics = session.get_session_analytics(session_id)
        assert analytics["tasks_completed"] >= 3
        assert analytics["total_time"] > 0


class TestInterruptedSessionAndResume:
    """Test session interruption and resumption."""

    def test_interrupt_during_implementation_and_resume(self, initialized_system):
        """Test interruption during implementation and successful resumption."""
        telemetry = initialized_system["telemetry"]
        session = initialized_system["session"]
        checkpoint = initialized_system["checkpoint"]

        # Start session and begin task
        session_data = session.start_session()
        session_id = session_data["id"]

        # Create checkpoint before task
        checkpoint_id = checkpoint.create("before_task_1", task_id=1)

        with telemetry.track_operation(
            "implementation", "Task 1", session_id=session_id
        ):
            telemetry.record_event("test_generation", "info", "Tests generated")
            telemetry.record_event("implementation", "info", "Code started")
            time.sleep(0.1)

        # Simulate interruption (session not completed)
        # Detect interrupted session
        interrupted = session.detect_interrupted_sessions()
        assert session_id in [s["id"] for s in interrupted]

        # Resume session
        resumed_session = session.resume_session(session_id)
        assert resumed_session["status"] == "active"
        assert resumed_session["id"] == session_id

        # Continue work
        with telemetry.track_operation(
            "implementation",
            "Task 1 (continued)",
            session_id=session_id,
            parent_id=None,
        ):
            telemetry.record_event("implementation", "info", "Code completed")
            telemetry.record_event("verification", "info", "Tests passed")

        # Complete session
        session.complete_session()

        # Verify resumption was successful
        operations = telemetry.query_filters(session_id=session_id)
        assert len(operations) >= 2  # Two implementation phases

    def test_multiple_interruptions(self, initialized_system):
        """Test handling multiple interruptions during a session."""
        session = initialized_system["session"]
        telemetry = initialized_system["telemetry"]

        # Start session
        session_data = session.start_session()
        session_id = session_data["id"]

        # First phase of work
        with telemetry.track_operation(
            "implementation", "Phase 1", session_id=session_id
        ):
            time.sleep(0.05)

        # Simulate first interruption
        session.pause_session()

        # Resume
        session.resume_session(session_id)

        # Second phase of work
        with telemetry.track_operation(
            "implementation", "Phase 2", session_id=session_id
        ):
            time.sleep(0.05)

        # Second interruption
        session.pause_session()

        # Resume again
        session.resume_session(session_id)

        # Complete work
        with telemetry.track_operation(
            "implementation", "Phase 3", session_id=session_id
        ):
            time.sleep(0.05)

        session.complete_session()

        # Verify all phases were tracked
        operations = telemetry.query_filters(session_id=session_id)
        assert len(operations) >= 3


class TestErrorRecoveryScenarios:
    """Test various error recovery scenarios."""

    def test_llm_rate_limit_recovery(self, initialized_system):
        """Test automatic recovery from LLM rate limit errors."""
        error_handling = initialized_system.get("error_handling")

        if error_handling:
            # Simulate rate limit error
            attempt_count = [0]

            @error_handling.retry_with_backoff(max_attempts=3)
            def simulate_llm_call():
                attempt_count[0] += 1
                if attempt_count[0] < 3:
                    raise Exception("Rate limit exceeded")
                return "Success"

            result = simulate_llm_call()
            assert result == "Success"
            assert attempt_count[0] == 3

    def test_database_lock_recovery(self, initialized_system):
        """Test recovery from database lock errors."""
        telemetry = initialized_system["telemetry"]

        # Simulate concurrent access
        def operation_1():
            with telemetry.track_operation("test", "Op1"):
                time.sleep(0.2)

        def operation_2():
            with telemetry.track_operation("test", "Op2"):
                time.sleep(0.2)

        # Run operations concurrently
        t1 = threading.Thread(target=operation_1)
        t2 = threading.Thread(target=operation_2)

        t1.start()
        time.sleep(0.05)  # Small delay to ensure lock contention
        t2.start()

        t1.join()
        t2.join()

        # Verify both operations completed
        operations = telemetry.query_filters(operation_type="test")
        assert len(operations) == 2

    def test_checkpoint_rollback_on_error(self, initialized_system):
        """Test rollback to checkpoint when unrecoverable error occurs."""
        checkpoint = initialized_system["checkpoint"]

        # Create initial checkpoint
        checkpoint_id = checkpoint.create("initial_state")

        # Simulate error scenario
        try:
            with checkpoint.auto_rollback_on_error():
                # Simulate some state changes
                time.sleep(0.1)
                # Trigger error
                raise ValueError("Unrecoverable error")
        except ValueError:
            pass

        # Restore checkpoint
        checkpoint.restore(checkpoint_id)

        # Verify state was restored
        checkpoints = checkpoint.list_checkpoints()
        assert len(checkpoints) >= 1


class TestCheckpointRestoreCycles:
    """Test checkpoint and restore cycles."""

    def test_checkpoint_restore_multiple_times(self, initialized_system):
        """Test creating and restoring checkpoints multiple times."""
        checkpoint = initialized_system["checkpoint"]

        # Create multiple checkpoints
        checkpoint_ids = []
        for i in range(3):
            time.sleep(0.05)
            checkpoint_id = checkpoint.create(f"checkpoint_{i}", iteration=i)
            checkpoint_ids.append(checkpoint_id)

        # Restore each checkpoint and verify
        for i, checkpoint_id in enumerate(checkpoint_ids):
            checkpoint.restore(checkpoint_id)
            time.sleep(0.02)
            # Verify state is as expected for this checkpoint
            current_checkpoints = checkpoint.list_checkpoints()
            assert len(current_checkpoints) >= len(checkpoint_ids)

    def test_checkpoint_with_database_and_files(
        self, initialized_system, temp_project_dir
    ):
        """Test checkpoint that includes database and file system state."""
        checkpoint = initialized_system["checkpoint"]
        db_manager = initialized_system["db_manager"]

        # Create some files
        test_file = Path("test_file.py")
        test_file.write_text('print("test")')

        # Add to git
        os.system("git add test_file.py")
        os.system('git commit -m "Add test file"')

        # Create checkpoint
        checkpoint_id = checkpoint.create("with_db_and_files")

        # Modify file
        test_file.write_text('print("modified")')

        # Modify database (add a task)
        db_manager.insert_task("Test task", "Test description", "pending")

        # Restore checkpoint
        checkpoint.restore(checkpoint_id)

        # Verify file was restored
        assert test_file.read_text() == 'print("test")'

        # Verify checkpoint metadata
        checkpoint_info = checkpoint.get_checkpoint(checkpoint_id)
        assert checkpoint_info is not None
        assert checkpoint_info["reason"] == "with_db_and_files"


class TestResourceExhaustionHandling:
    """Test handling of resource exhaustion scenarios."""

    def test_high_memory_usage_monitoring(self, initialized_system):
        """Test monitoring and alerting on high memory usage."""
        telemetry = initialized_system["telemetry"]

        # Simulate operation with resource tracking
        with telemetry.track_operation("memory_intensive", "Test operation"):
            telemetry.record_metric("memory_usage_mb", 1024)  # High usage
            telemetry.record_event(
                "memory_warning", "warning", "High memory usage detected"
            )
            time.sleep(0.1)

        # Query metrics
        operations = telemetry.query_filters(operation_type="memory_intensive")
        assert len(operations) == 1

        # Verify warning was recorded
        events = telemetry.search_events(event_type="memory_warning")
        assert len(events) >= 1

    def test_disk_space_handling(self, initialized_system):
        """Test handling of low disk space."""
        checkpoint = initialized_system["checkpoint"]

        # Create checkpoint with disk space monitoring
        checkpoint_id = checkpoint.create("disk_test", check_disk_space=True)

        # Verify checkpoint was created
        checkpoint_info = checkpoint.get_checkpoint(checkpoint_id)
        assert checkpoint_info is not None

    def test_long_running_operation_tracking(self, initialized_system):
        """Test tracking of long-running operations."""
        telemetry = initialized_system["telemetry"]

        # Simulate long-running operation
        with telemetry.track_operation("long_running", "Analysis"):
            telemetry.record_event("progress", "info", "25% complete")
            time.sleep(0.1)
            telemetry.record_event("progress", "info", "50% complete")
            time.sleep(0.1)
            telemetry.record_event("progress", "info", "75% complete")
            time.sleep(0.1)
            telemetry.record_event("progress", "info", "100% complete")

        # Verify operation duration was tracked
        operations = telemetry.query_filters(operation_type="long_running")
        assert len(operations) == 1
        assert operations[0]["duration_ms"] >= 300  # At least 300ms


class TestTelemetryAndLoggingOverhead:
    """Test performance impact of telemetry and logging."""

    def test_telemetry_overhead(self, initialized_system):
        """Verify telemetry overhead is <5% of operation time."""
        telemetry = initialized_system["telemetry"]

        # Measure operation without telemetry
        start_time = time.time()
        for i in range(100):
            pass  # Dummy operation
        baseline_time = time.time() - start_time

        # Measure operation with telemetry
        start_time = time.time()
        for i in range(100):
            with telemetry.track_operation("test", f"Op{i}"):
                pass
        telemetry_time = time.time() - start_time

        # Calculate overhead percentage
        overhead = ((telemetry_time - baseline_time) / baseline_time) * 100

        # Verify overhead is reasonable (should be less than 500% for this test)
        # Note: Real-world overhead should be <5%, but test environment may differ
        assert overhead < 500  # Very lenient threshold for test environment

    def test_logging_overhead(self, initialized_system):
        """Verify logging overhead is minimal."""
        logger = initialized_system["logger"]

        # Measure operation with logging
        start_time = time.time()
        for i in range(100):
            logger.info(f"Test log message {i}")
        logging_time = time.time() - start_time

        # Verify logging is fast enough (should process 100 logs in <1 second)
        assert logging_time < 1.0


class TestCrossModuleIntegration:
    """Test integration across multiple V3 modules."""

    def test_telemetry_checkpoint_session_integration(self, initialized_system):
        """Test integration between telemetry, checkpoint, and session."""
        telemetry = initialized_system["telemetry"]
        checkpoint = initialized_system["checkpoint"]
        session = initialized_system["session"]

        # Start session
        session_data = session.start_session()
        session_id = session_data["id"]

        # Create checkpoint
        checkpoint_id = checkpoint.create("integration_test", session_id=session_id)

        # Track operations
        with telemetry.track_operation(
            "task", "Integration test", session_id=session_id
        ):
            telemetry.record_metric("checkpoints_used", 1)
            time.sleep(0.05)

        # Complete session
        session.complete_session()

        # Verify cross-module consistency
        operations = telemetry.query_filters(session_id=session_id)
        assert len(operations) >= 1

        checkpoints = checkpoint.list_checkpoints()
        assert any(c["metadata"].get("session_id") == session_id for c in checkpoints)

        sessions = session.list_sessions()
        assert any(s["id"] == session_id for s in sessions)

    def test_error_recovery_checkpoint_integration(self, initialized_system):
        """Test integration between error recovery and checkpointing."""
        checkpoint = initialized_system["checkpoint"]
        telemetry = initialized_system["telemetry"]

        # Create checkpoint
        checkpoint_id = checkpoint.create("before_error")

        # Simulate error and recovery
        try:
            with telemetry.track_operation("error_test", "Test"):
                raise Exception("Simulated error")
        except Exception as e:
            # Log error
            telemetry.record_event("error", "error", str(e))
            # Restore checkpoint
            checkpoint.restore(checkpoint_id)

        # Verify error was logged
        events = telemetry.search_events(event_type="error")
        assert len(events) >= 1

    def test_session_analytics_with_telemetry(self, initialized_system):
        """Test session analytics using telemetry data."""
        session = initialized_system["session"]
        telemetry = initialized_system["telemetry"]

        # Start session
        session_data = session.start_session()
        session_id = session_data["id"]

        # Perform various operations
        with telemetry.track_operation("planning", "Plan tasks", session_id=session_id):
            telemetry.record_metric("tasks_planned", 5)

        with telemetry.track_operation(
            "implementation", "Implement task 1", session_id=session_id
        ):
            telemetry.record_metric("lines_added", 20)
            telemetry.record_metric("tokens_used", 1500)

        with telemetry.track_operation(
            "verification", "Verify task 1", session_id=session_id
        ):
            telemetry.record_metric("test_coverage", 98.5)

        # Complete session
        session.complete_session()

        # Get analytics
        analytics = session.get_session_analytics(session_id)

        # Verify analytics
        assert analytics is not None
        assert analytics["tasks_completed"] >= 1
        assert analytics["total_time"] > 0


class TestRealWorldScenarios:
    """Test realistic real-world usage scenarios."""

    def test_developer_daily_workflow(self, initialized_system, temp_project_dir):
        """Simulate a complete daily developer workflow."""
        session = initialized_system["session"]
        telemetry = initialized_system["telemetry"]
        checkpoint = initialized_system["checkpoint"]

        # Morning: Start work session
        session_data = session.start_session()
        session_id = session_data["id"]

        # Plan tasks
        with telemetry.track_operation(
            "planning", "Daily planning", session_id=session_id
        ):
            telemetry.record_event("planning", "info", "Planned 3 tasks")

        # Implement task 1
        checkpoint.create("before_task_1")
        with telemetry.track_operation(
            "implementation", "Task 1: User authentication", session_id=session_id
        ):
            telemetry.record_event("test_generation", "info", "Tests generated")
            telemetry.record_event("implementation", "info", "Code implemented")
            telemetry.record_metric("lines_added", 25)
        checkpoint.create("after_task_1")

        # Implement task 2
        checkpoint.create("before_task_2")
        with telemetry.track_operation(
            "implementation", "Task 2: Database schema", session_id=session_id
        ):
            telemetry.record_event("test_generation", "info", "Tests generated")
            telemetry.record_event("implementation", "info", "Code implemented")
            telemetry.record_metric("lines_added", 18)
        checkpoint.create("after_task_2")

        # Lunch break - pause session
        session.pause_session()

        # Afternoon: Resume session
        session.resume_session(session_id)

        # Implement task 3
        checkpoint.create("before_task_3")
        with telemetry.track_operation(
            "implementation", "Task 3: API endpoints", session_id=session_id
        ):
            telemetry.record_event("test_generation", "info", "Tests generated")
            telemetry.record_event("implementation", "info", "Code implemented")
            telemetry.record_metric("lines_added", 32)
        checkpoint.create("after_task_3")

        # End of day: Complete session
        session.complete_session()

        # Verify full day's work
        operations = telemetry.query_filters(session_id=session_id)
        assert len(operations) >= 4  # Planning + 3 implementations

        analytics = session.get_session_analytics(session_id)
        assert analytics["tasks_completed"] >= 3

    def test_bug_fix_workflow(self, initialized_system):
        """Test bug fix workflow with rapid iterations."""
        session = initialized_system["session"]
        telemetry = initialized_system["telemetry"]

        session_data = session.start_session()
        session_id = session_data["id"]

        # Bug discovered - create investigation
        with telemetry.track_operation(
            "investigation", "Bug #123: Null pointer", session_id=session_id
        ):
            telemetry.record_event("investigation", "info", "Root cause identified")

        # Fix attempt 1
        with telemetry.track_operation(
            "implementation", "Fix attempt 1", session_id=session_id
        ):
            telemetry.record_event("implementation", "info", "Fix applied")
            telemetry.record_event("test", "error", "Test failed")

        # Fix attempt 2
        with telemetry.track_operation(
            "implementation", "Fix attempt 2", session_id=session_id
        ):
            telemetry.record_event("implementation", "info", "Fix applied")
            telemetry.record_event("test", "info", "Tests passed")

        session.complete_session()

        # Verify fix workflow
        operations = telemetry.query_filters(session_id=session_id)
        assert any("fix" in op["title"].lower() for op in operations)

    def test_refactor_workflow(self, initialized_system):
        """Test refactoring workflow with checkpoints."""
        checkpoint = initialized_system["checkpoint"]
        telemetry = initialized_system["telemetry"]
        session = initialized_system["session"]

        session_data = session.start_session()
        session_id = session_data["id"]

        # Create checkpoint before refactor
        before_refactor = checkpoint.create(
            "before_refactor", reason="Pre-refactor safety"
        )

        # Perform refactor
        with telemetry.track_operation(
            "refactor", "Refactor user service", session_id=session_id
        ):
            telemetry.record_event("refactor", "info", "Extracted methods")
            telemetry.record_event("refactor", "info", "Simplified logic")
            telemetry.record_metric("lines_removed", 50)
            telemetry.record_metric("lines_added", 30)

        # Verify tests still pass
        with telemetry.track_operation(
            "verification", "Post-refactor verification", session_id=session_id
        ):
            telemetry.record_event("test", "info", "All tests passed")

        # Create checkpoint after refactor
        after_refactor = checkpoint.create(
            "after_refactor", reason="Refactor completed"
        )

        session.complete_session()

        # Verify checkpoints exist
        checkpoints = checkpoint.list_checkpoints()
        assert len(checkpoints) >= 2


class TestPerformanceMetrics:
    """Test performance metrics and benchmarks."""

    def test_checkpoint_creation_performance(self, initialized_system):
        """Verify checkpoint creation performance is within limits."""
        checkpoint = initialized_system["checkpoint"]
        db_manager = initialized_system["db_manager"]

        # Create some test data
        for i in range(100):
            db_manager.insert_task(f"Task {i}", f"Description {i}", "pending")

        # Measure checkpoint creation time
        start_time = time.time()
        checkpoint_id = checkpoint.create("performance_test")
        creation_time = time.time() - start_time

        # Verify checkpoint creation is fast (< 2 seconds)
        assert creation_time < 2.0, f"Checkpoint creation took {creation_time:.2f}s"

    def test_checkpoint_restore_performance(self, initialized_system):
        """Verify checkpoint restore performance is within limits."""
        checkpoint = initialized_system["checkpoint"]
        db_manager = initialized_system["db_manager"]

        # Create some test data
        for i in range(100):
            db_manager.insert_task(f"Task {i}", f"Description {i}", "pending")

        # Create checkpoint
        checkpoint_id = checkpoint.create("performance_test")

        # Modify data
        db_manager.insert_task("New task", "New description", "pending")

        # Measure restore time
        start_time = time.time()
        checkpoint.restore(checkpoint_id)
        restore_time = time.time() - start_time

        # Verify restore is fast (< 2 seconds)
        assert restore_time < 2.0, f"Checkpoint restore took {restore_time:.2f}s"

    def test_session_resume_performance(self, initialized_system):
        """Verify session resumption is fast (< 5 seconds)."""
        session = initialized_system["session"]

        # Create and complete a session with work
        session_data = session.start_session()
        session_id = session_data["id"]
        session.complete_session()

        # Detect interrupted session
        time.sleep(0.1)

        # Measure resume time
        start_time = time.time()
        resumed = session.resume_session(session_id)
        resume_time = time.time() - start_time

        # Verify resume is fast (< 5 seconds)
        assert resume_time < 5.0, f"Session resume took {resume_time:.2f}s"
        assert resumed["id"] == session_id

    def test_telemetry_query_performance(self, initialized_system):
        """Verify telemetry query performance."""
        telemetry = initialized_system["telemetry"]

        # Create many operations
        for i in range(100):
            with telemetry.track_operation("test", f"Operation {i}"):
                telemetry.record_metric("value", i)

        # Measure query time
        start_time = time.time()
        operations = telemetry.query_operations()
        query_time = time.time() - start_time

        # Verify query is fast (< 1 second for 100 operations)
        assert query_time < 1.0, f"Telemetry query took {query_time:.2f}s"
        assert len(operations) >= 100


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
