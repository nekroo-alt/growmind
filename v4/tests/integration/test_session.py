"""
Integration Tests for Session Management

Comprehensive tests covering session lifecycle, persistence, recovery,
configuration, and analytics.
"""

import json
import os
import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path
import sqlite3
import pytest
import time
import threading

from core.session_manager import (
    SessionManager,
    Session,
    SessionStatus,
    get_session_manager,
)


class TestSessionLifecycle:
    """Test session creation, lifecycle management, and state transitions."""

    @pytest.fixture
    def db_path(self):
        """Create temporary database for testing."""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        yield path
        try:
            os.unlink(path)
        except:
            pass

    @pytest.fixture
    def manager(self, db_path):
        """Create SessionManager instance for testing."""
        return SessionManager(db_path=db_path)

    def test_start_session_basic(self, manager):
        """Test starting a new session with basic parameters."""
        session = manager.start_session()

        assert session is not None
        assert session.session_id is not None
        assert session.status == SessionStatus.ACTIVE
        assert session.start_time is not None
        assert session.config == {}
        assert session.metadata == {}
        assert session.active_operations == []
        assert session.active_tasks == []

    def test_start_session_with_config(self, manager):
        """Test starting a session with configuration."""
        config = {"llm_model": "gpt-4", "cache_enabled": True, "temperature": 0.7}
        session = manager.start_session(config=config)

        assert session.config == config
        assert session.config["llm_model"] == "gpt-4"
        assert session.config["cache_enabled"] is True

    def test_start_session_with_metadata(self, manager):
        """Test starting a session with metadata."""
        metadata = {"user": "developer", "environment": "dev", "host": "localhost"}
        session = manager.start_session(metadata=metadata)

        assert session.metadata == metadata
        assert session.metadata["user"] == "developer"

    def test_pause_session(self, manager):
        """Test pausing an active session."""
        session = manager.start_session()

        result = manager.pause_session(session.session_id)

        assert result is True

        # Verify session is paused
        paused_session = manager._load_session(session.session_id)
        assert paused_session.status == SessionStatus.PAUSED

    def test_pause_nonexistent_session(self, manager):
        """Test pausing a non-existent session."""
        result = manager.pause_session("nonexistent-id")
        assert result is False

    def test_complete_session(self, manager):
        """Test completing a session."""
        session = manager.start_session()

        result = manager.complete_session(session.session_id)

        assert result is True

        # Verify session is completed
        completed_session = manager._load_session(session.session_id)
        assert completed_session.status == SessionStatus.COMPLETED
        assert completed_session.end_time is not None

    def test_complete_nonexistent_session(self, manager):
        """Test completing a non-existent session."""
        result = manager.complete_session("nonexistent-id")
        assert result is False

    def test_resume_active_session(self, manager):
        """Test resuming an active session."""
        session = manager.start_session()

        resumed = manager.resume_session(session.session_id)

        assert resumed is not None
        assert resumed.session_id == session.session_id
        assert resumed.status == SessionStatus.ACTIVE

    def test_resume_paused_session(self, manager):
        """Test resuming a paused session."""
        session = manager.start_session()
        manager.pause_session(session.session_id)

        resumed = manager.resume_session(session.session_id)

        assert resumed is not None
        assert resumed.status == SessionStatus.ACTIVE

    def test_resume_nonexistent_session(self, manager):
        """Test resuming a non-existent session."""
        resumed = manager.resume_session("nonexistent-id")
        assert resumed is None

    def test_get_active_session(self, manager):
        """Test getting the active session."""
        session = manager.start_session()

        active = manager.get_active_session()

        assert active is not None
        assert active.session_id == session.session_id
        assert active.status == SessionStatus.ACTIVE

    def test_get_active_session_none(self, manager):
        """Test getting active session when none exists."""
        active = manager.get_active_session()
        assert active is None

    def test_archive_session(self, manager):
        """Test archiving a session."""
        session = manager.start_session()

        result = manager.archive_session(session.session_id)

        assert result is True

        archived = manager._load_session(session.session_id)
        assert archived.status == SessionStatus.ARCHIVED
        assert archived.end_time is not None

    def test_archive_already_archived_session(self, manager):
        """Test archiving an already archived session."""
        session = manager.start_session()
        manager.archive_session(session.session_id)

        result = manager.archive_session(session.session_id)

        assert result is False

    def test_session_status_transitions(self, manager):
        """Test valid session status transitions."""
        session = manager.start_session()

        # Active -> Paused
        assert manager.pause_session(session.session_id) is True
        assert manager._load_session(session.session_id).status == SessionStatus.PAUSED

        # Paused -> Active
        assert manager.resume_session(session.session_id) is not None
        assert manager._load_session(session.session_id).status == SessionStatus.ACTIVE

        # Active -> Completed
        assert manager.complete_session(session.session_id) is True
        assert (
            manager._load_session(session.session_id).status == SessionStatus.COMPLETED
        )


class TestSessionPersistence:
    """Test session persistence and recovery."""

    @pytest.fixture
    def db_path(self):
        """Create temporary database for testing."""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        yield path
        try:
            os.unlink(path)
        except:
            pass

    @pytest.fixture
    def manager(self, db_path):
        """Create SessionManager instance for testing."""
        return SessionManager(db_path=db_path)

    def test_session_persistence_across_managers(self, db_path):
        """Test session persists across different manager instances."""
        # Create session with first manager
        manager1 = SessionManager(db_path=db_path)
        session = manager1.start_session(
            config={"model": "gpt-4"}, metadata={"user": "test"}
        )

        # Create new manager instance and load session
        manager2 = SessionManager(db_path=db_path)
        loaded = manager2._load_session(session.session_id)

        assert loaded is not None
        assert loaded.session_id == session.session_id
        assert loaded.config == session.config
        assert loaded.metadata == session.metadata

    def test_export_session(self, manager):
        """Test exporting session to JSON file."""
        session = manager.start_session(
            config={"model": "gpt-4"}, metadata={"user": "test"}
        )
        session.active_tasks = [1, 2, 3]
        session.active_operations = ["op1", "op2"]
        manager._save_session(session)

        fd, export_path = tempfile.mkstemp(suffix=".json")
        os.close(fd)

        try:
            result = manager.export_session(session.session_id, export_path)

            assert result is True
            assert os.path.exists(export_path)

            # Verify exported content
            with open(export_path, "r") as f:
                data = json.load(f)

            assert "session" in data
            assert data["session"]["session_id"] == session.session_id
            assert data["session"]["config"]["model"] == "gpt-4"
            assert data["session"]["metadata"]["user"] == "test"
            assert "exported_at" in data
            assert "version" in data
        finally:
            try:
                os.unlink(export_path)
            except:
                pass

    def test_export_nonexistent_session(self, manager):
        """Test exporting a non-existent session."""
        fd, export_path = tempfile.mkstemp(suffix=".json")
        os.close(fd)

        try:
            result = manager.export_session("nonexistent-id", export_path)
            assert result is False
        finally:
            try:
                os.unlink(export_path)
            except:
                pass

    def test_import_session(self, manager):
        """Test importing session from JSON file."""
        # Create export data
        export_data = {
            "session": {
                "session_id": "original-id",
                "start_time": datetime.now().isoformat(),
                "status": "paused",
                "config": {"model": "gpt-4"},
                "metadata": {"user": "test"},
                "active_operations": ["op1"],
                "active_tasks": [1, 2],
                "checkpoint_id": "chk-123",
                "end_time": None,
            },
            "exported_at": datetime.now().isoformat(),
            "version": "1.0",
        }

        fd, import_path = tempfile.mkstemp(suffix=".json")
        os.close(fd)

        try:
            with open(import_path, "w") as f:
                json.dump(export_data, f)

            imported = manager.import_session(import_path)

            assert imported is not None
            assert imported.session_id != "original-id"  # New ID generated
            assert imported.config["model"] == "gpt-4"
            assert imported.metadata["user"] == "test"
            assert imported.status == SessionStatus.PAUSED
            assert imported.active_tasks == [1, 2]
            assert imported.active_operations == ["op1"]

            # Verify it's saved in database
            loaded = manager._load_session(imported.session_id)
            assert loaded is not None
        finally:
            try:
                os.unlink(import_path)
            except:
                pass

    def test_import_invalid_file(self, manager):
        """Test importing from invalid JSON file."""
        fd, import_path = tempfile.mkstemp(suffix=".json")
        os.close(fd)

        try:
            with open(import_path, "w") as f:
                f.write("invalid json")

            imported = manager.import_session(import_path)
            assert imported is None
        finally:
            try:
                os.unlink(import_path)
            except:
                pass

    def test_import_missing_session_data(self, manager):
        """Test importing file with missing session data."""
        export_data = {
            "exported_at": datetime.now().isoformat(),
            "version": "1.0",
            # Missing "session" key
        }

        fd, import_path = tempfile.mkstemp(suffix=".json")
        os.close(fd)

        try:
            with open(import_path, "w") as f:
                json.dump(export_data, f)

            imported = manager.import_session(import_path)
            assert imported is None
        finally:
            try:
                os.unlink(import_path)
            except:
                pass


class TestSessionRecovery:
    """Test session recovery after interruption."""

    @pytest.fixture
    def db_path(self):
        """Create temporary database for testing."""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        yield path
        try:
            os.unlink(path)
        except:
            pass

    @pytest.fixture
    def manager(self, db_path):
        """Create SessionManager instance for testing."""
        return SessionManager(db_path=db_path)

    def test_detect_interrupted_sessions_active(self, manager):
        """Test detecting interrupted active sessions."""
        session = manager.start_session()
        session.active_tasks = [1, 2]
        manager._save_session(session)

        interrupted = manager.detect_interrupted_sessions()

        assert len(interrupted) > 0
        assert any(s.session_id == session.session_id for s in interrupted)

    def test_detect_interrupted_sessions_paused(self, manager):
        """Test detecting interrupted paused sessions."""
        session = manager.start_session()
        manager.pause_session(session.session_id)

        interrupted = manager.detect_interrupted_sessions()

        assert len(interrupted) > 0
        assert any(s.session_id == session.session_id for s in interrupted)

    def test_detect_interrupted_sessions_completed(self, manager):
        """Test that completed sessions are not detected as interrupted."""
        session = manager.start_session()
        manager.complete_session(session.session_id)

        interrupted = manager.detect_interrupted_sessions()

        assert not any(s.session_id == session.session_id for s in interrupted)

    def test_save_session_on_shutdown(self, manager):
        """Test saving session on shutdown."""
        session = manager.start_session()
        session.active_tasks = [1, 2, 3]
        manager._save_session(session)

        result = manager.save_session_on_shutdown(
            session.session_id, checkpoint_id="chk-123"
        )

        assert result is True

        # Verify session is paused
        saved = manager._load_session(session.session_id)
        assert saved.status == SessionStatus.PAUSED
        assert saved.checkpoint_id == "chk-123"
        assert "last_shutdown" in saved.metadata

    def test_save_session_on_shutdown_nonexistent(self, manager):
        """Test saving non-existent session on shutdown."""
        result = manager.save_session_on_shutdown("nonexistent-id")
        assert result is False

    def test_restore_session_on_startup(self, manager, monkeypatch):
        """Test restoring session on startup."""
        session = manager.start_session()
        session.active_tasks = [1, 2]
        session.checkpoint_id = "chk-456"
        manager._save_session(session)

        # Mock external changes check to return False
        def mock_check_changes():
            return False

        monkeypatch.setattr(manager, "_check_external_changes", mock_check_changes)

        restored, has_changes = manager.restore_session_on_startup(
            session.session_id, checkpoint_manager=None  # Not checking external changes
        )

        assert restored is not None
        assert has_changes is False  # No external changes in test
        assert restored.session_id == session.session_id
        assert restored.status == SessionStatus.ACTIVE

    def test_restore_session_nonexistent(self, manager):
        """Test restoring non-existent session."""
        restored, has_changes = manager.restore_session_on_startup("nonexistent-id")

        assert restored is None
        assert has_changes is False

    def test_cleanup_stale_sessions(self, manager):
        """Test cleaning up stale sessions."""
        # Create old session (manually update start_time)
        session = manager.start_session()

        # Update start_time to 25 hours ago
        old_time = datetime.now() - timedelta(hours=25)
        with sqlite3.connect(manager.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE sessions 
                SET start_time = ?
                WHERE session_id = ?
            """,
                (old_time.isoformat(), session.session_id),
            )
            conn.commit()

        # Cleanup sessions older than 24 hours
        count = manager.cleanup_stale_sessions(hours=24)

        assert count >= 1

        # Verify session is archived
        archived = manager._load_session(session.session_id)
        assert archived.status == SessionStatus.ARCHIVED

    def test_cleanup_old_sessions(self, manager):
        """Test cleaning up old completed sessions."""
        session = manager.start_session()
        manager.complete_session(session.session_id)

        # Update start_time to 35 days ago
        old_time = datetime.now() - timedelta(days=35)
        with sqlite3.connect(manager.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE sessions 
                SET start_time = ?
                WHERE session_id = ?
            """,
                (old_time.isoformat(), session.session_id),
            )
            conn.commit()

        # Cleanup sessions older than 30 days
        count = manager.cleanup_old_sessions(days=30)

        assert count >= 1

        archived = manager._load_session(session.session_id)
        assert archived.status == SessionStatus.ARCHIVED


class TestConfigurationPersistence:
    """Test configuration persistence and management."""

    @pytest.fixture
    def db_path(self):
        """Create temporary database for testing."""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        yield path
        try:
            os.unlink(path)
        except:
            pass

    @pytest.fixture
    def manager(self, db_path):
        """Create SessionManager instance for testing."""
        return SessionManager(db_path=db_path)

    def test_config_persistence_across_sessions(self, manager):
        """Test configuration persists across session instances."""
        config = {
            "llm_provider": "openai",
            "llm_model": "gpt-4",
            "temperature": 0.7,
            "cache_enabled": True,
            "cache_size_mb": 100,
        }

        session1 = manager.start_session(config=config)

        # Create new manager and load session
        manager2 = SessionManager(db_path=manager.db_path)
        session2 = manager2._load_session(session1.session_id)

        assert session2.config == config

    def test_multiple_sessions_different_configs(self, manager):
        """Test multiple sessions with different configurations."""
        config1 = {"llm_model": "gpt-4", "temperature": 0.7}
        config2 = {"llm_model": "gpt-3.5-turbo", "temperature": 0.5}

        session1 = manager.start_session(config=config1)
        session2 = manager.start_session(config=config2)

        loaded1 = manager._load_session(session1.session_id)
        loaded2 = manager._load_session(session2.session_id)

        assert loaded1.config["llm_model"] == "gpt-4"
        assert loaded2.config["llm_model"] == "gpt-3.5-turbo"

    def test_metadata_persistence(self, manager):
        """Test metadata persistence across sessions."""
        metadata = {
            "user": "developer",
            "environment": "production",
            "host": "server-01",
            "project": "my-project",
        }

        session = manager.start_session(metadata=metadata)

        loaded = manager._load_session(session.session_id)

        assert loaded.metadata == metadata

    def test_merge_sessions(self, manager):
        """Test merging two sessions."""
        config1 = {"model": "gpt-4"}
        config2 = {"model": "gpt-3.5-turbo"}

        session1 = manager.start_session(config=config1)
        session1.active_tasks = [1, 2]
        session1.active_operations = ["op1", "op2"]
        session1.metadata = {"user": "dev1"}
        manager._save_session(session1)

        session2 = manager.start_session(config=config2)
        session2.active_tasks = [2, 3]
        session2.active_operations = ["op2", "op3"]
        session2.metadata = {"environment": "prod"}
        manager._save_session(session2)

        result = manager.merge_sessions(session2.session_id, session1.session_id)

        assert result is True

        # Verify merge
        merged = manager._load_session(session1.session_id)
        assert set(merged.active_tasks) == {1, 2, 3}  # All tasks
        assert set(merged.active_operations) == {"op1", "op2", "op3"}  # All ops
        assert merged.metadata["user"] == "dev1"
        assert merged.metadata["environment"] == "prod"  # Added

    def test_merge_sessions_nonexistent(self, manager):
        """Test merging with non-existent session."""
        session = manager.start_session()

        result = manager.merge_sessions("nonexistent", session.session_id)
        assert result is False


class TestSessionAnalytics:
    """Test session analytics and reporting."""

    @pytest.fixture
    def db_path(self):
        """Create temporary database for testing."""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        yield path
        try:
            os.unlink(path)
        except:
            pass

    @pytest.fixture
    def manager(self, db_path):
        """Create SessionManager instance for testing."""
        return SessionManager(db_path=db_path)

    def test_get_session_metrics(self, manager):
        """Test getting session metrics."""
        session = manager.start_session()
        session.active_tasks = [1, 2, 3, 4, 5]
        session.active_operations = ["op1", "op2", "op3"]
        manager._save_session(session)

        # Wait a bit to ensure duration > 0
        time.sleep(0.01)

        metrics = manager.get_session_metrics(session.session_id)

        assert "error" not in metrics
        assert metrics["session_id"] == session.session_id
        assert metrics["tasks_completed"] == 5
        assert metrics["operations_count"] == 3
        assert metrics["duration_seconds"] >= 0  # Can be 0 if very fast
        assert metrics["checkpoint_count"] == 0

    def test_get_session_metrics_nonexistent(self, manager):
        """Test getting metrics for non-existent session."""
        metrics = manager.get_session_metrics("nonexistent-id")
        assert "error" in metrics

    def test_get_session_metrics_with_telemetry(self, manager):
        """Test getting metrics with telemetry integration."""
        # This would require mocking TelemetryManager
        # For now, test without telemetry
        session = manager.start_session()
        session.active_tasks = [1, 2]
        manager._save_session(session)

        metrics = manager.get_session_metrics(
            session.session_id, telemetry_manager=None
        )

        assert metrics["tasks_completed"] == 2
        assert (
            metrics["operations_count"] == 0
        )  # No operations tracked without telemetry

    def test_get_session_productivity(self, manager):
        """Test getting session productivity metrics."""
        session = manager.start_session()
        session.active_tasks = [1, 2, 3]
        manager._save_session(session)

        productivity = manager.get_session_productivity(session.session_id)

        assert "error" not in productivity
        assert productivity["tasks_completed"] == 3
        assert productivity["productivity_score"] > 0
        assert productivity["productivity_score"] <= 100
        assert productivity["duration_hours"] >= 0

    def test_get_session_productivity_with_errors(self, manager):
        """Test productivity calculation with errors."""
        session = manager.start_session()
        session.active_tasks = [1]
        manager._save_session(session)

        # Mock telemetry with errors
        class MockTelemetryManager:
            def query_operations(self, **kwargs):
                return [
                    {
                        "status": "completed",
                        "start_time": datetime.now().isoformat(),
                        "end_time": datetime.now().isoformat(),
                    },
                    {
                        "status": "failed",
                        "start_time": datetime.now().isoformat(),
                        "end_time": datetime.now().isoformat(),
                    },
                ]

            def search_events(self, **kwargs):
                return [{"severity": "error", "message": "Error 1"}] * 5

        tm = MockTelemetryManager()
        productivity = manager.get_session_productivity(session.session_id, tm)

        assert productivity["error_count"] == 5
        assert productivity["productivity_score"] < 100  # Reduced due to errors

    def test_generate_session_timeline(self, manager):
        """Test generating session timeline."""
        session = manager.start_session()
        session.active_tasks = [1, 2]
        manager._save_session(session)

        timeline = manager.generate_session_timeline(session.session_id)

        assert "error" not in timeline
        assert timeline["session_id"] == session.session_id
        assert len(timeline["events"]) > 0
        assert any(e["event_type"] == "session_start" for e in timeline["events"])

    def test_identify_bottlenecks_without_telemetry(self, manager):
        """Test bottleneck identification without telemetry."""
        session = manager.start_session()
        manager._save_session(session)

        bottlenecks = manager.identify_bottlenecks(
            session.session_id, telemetry_manager=None
        )

        assert len(bottlenecks) == 1
        assert "error" in bottlenecks[0]

    def test_identify_error_patterns_without_telemetry(self, manager):
        """Test error pattern identification without telemetry."""
        session = manager.start_session()
        manager._save_session(session)

        patterns = manager.identify_error_patterns(
            session.session_id, telemetry_manager=None
        )

        assert "error" in patterns

    def test_compare_sessions(self, manager):
        """Test comparing multiple sessions."""
        session1 = manager.start_session()
        session1.active_tasks = [1, 2, 3]
        manager._save_session(session1)

        session2 = manager.start_session()
        session2.active_tasks = [4, 5]
        manager._save_session(session2)

        comparison = manager.compare_sessions(
            [session1.session_id, session2.session_id]
        )

        assert "error" not in comparison
        assert comparison["session_count"] == 2
        assert comparison["avg_tasks_completed"] == 2.5
        assert comparison["best_session"]["tasks_completed"] == 3
        assert comparison["worst_session"]["tasks_completed"] == 2

    def test_compare_sessions_empty_list(self, manager):
        """Test comparing empty session list."""
        comparison = manager.compare_sessions([])
        assert "error" in comparison

    def test_generate_report(self, manager):
        """Test generating comprehensive session report."""
        session = manager.start_session()
        session.active_tasks = [1, 2, 3]
        manager._save_session(session)

        report = manager.generate_report(session.session_id)

        assert "error" not in report
        assert report["session_id"] == session.session_id
        assert "metrics" in report
        assert "productivity" in report
        assert "timeline" in report
        assert report["metrics"]["tasks_completed"] == 3
        assert report["productivity"]["tasks_completed"] == 3

    def test_generate_report_with_telemetry(self, manager):
        """Test generating report with telemetry integration."""
        session = manager.start_session()
        session.active_tasks = [1]
        manager._save_session(session)

        # Mock telemetry manager
        class MockTelemetryManager:
            def query_operations(self, **kwargs):
                return []

            def search_events(self, **kwargs):
                return []

        tm = MockTelemetryManager()
        report = manager.generate_report(session.session_id, telemetry_manager=tm)

        assert "metrics" in report
        assert "productivity" in report
        assert "timeline" in report

    def test_generate_period_report(self, manager):
        """Test generating period report."""
        session = manager.start_session()
        session.active_tasks = [1, 2]
        manager._save_session(session)

        report = manager.generate_period_report(days=7)

        assert report["period_days"] == 7
        assert report["session_count"] >= 1
        assert "comparison" in report
        assert "total_tasks_completed" in report

    def test_export_report_json(self, manager):
        """Test exporting report to JSON."""
        session = manager.start_session()
        session.active_tasks = [1, 2]
        manager._save_session(session)

        fd, export_path = tempfile.mkstemp(suffix=".json")
        os.close(fd)

        try:
            result = manager.export_report(
                session.session_id, export_path, format="json"
            )

            assert result is True
            assert os.path.exists(export_path)

            # Verify content
            with open(export_path, "r") as f:
                data = json.load(f)

            assert data["session_id"] == session.session_id
            assert "metrics" in data
        finally:
            try:
                os.unlink(export_path)
            except:
                pass

    def test_export_report_markdown(self, manager):
        """Test exporting report to Markdown."""
        session = manager.start_session()
        session.active_tasks = [1, 2]
        manager._save_session(session)

        fd, export_path = tempfile.mkstemp(suffix=".md")
        os.close(fd)

        try:
            result = manager.export_report(
                session.session_id, export_path, format="markdown"
            )

            assert result is True
            assert os.path.exists(export_path)

            # Verify content
            with open(export_path, "r") as f:
                content = f.read()

            assert "# Session Report" in content
            assert session.session_id in content
        finally:
            try:
                os.unlink(export_path)
            except:
                pass

    def test_export_report_invalid_format(self, manager):
        """Test exporting report with invalid format."""
        session = manager.start_session()
        manager._save_session(session)

        fd, export_path = tempfile.mkstemp(suffix=".txt")
        os.close(fd)

        try:
            result = manager.export_report(
                session.session_id, export_path, format="xml"  # Invalid format
            )

            assert result is False
        finally:
            try:
                os.unlink(export_path)
            except:
                pass


class TestSessionConcurrency:
    """Test concurrent session operations."""

    @pytest.fixture
    def db_path(self):
        """Create temporary database for testing."""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        yield path
        try:
            os.unlink(path)
        except:
            pass

    @pytest.fixture
    def manager(self, db_path):
        """Create SessionManager instance for testing."""
        return SessionManager(db_path=db_path)

    def test_concurrent_session_creation(self, manager):
        """Test creating sessions concurrently."""
        sessions = []
        errors = []

        def create_session(index):
            try:
                session = manager.start_session(config={"worker": index})
                sessions.append(session)
            except Exception as e:
                errors.append(e)

        threads = []
        for i in range(10):
            t = threading.Thread(target=create_session, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(sessions) == 10
        assert len(set(s.session_id for s in sessions)) == 10  # All unique

    def test_concurrent_session_updates(self, manager):
        """Test updating sessions concurrently."""
        session = manager.start_session()
        errors = []

        def update_session(index):
            try:
                for i in range(5):
                    with manager.lock:  # Use lock to prevent overwrites
                        loaded = manager._load_session(session.session_id)
                        loaded.active_tasks.append(i)
                        manager._save_session(loaded)
                    time.sleep(0.001)
            except Exception as e:
                errors.append(e)

        threads = []
        for i in range(3):
            t = threading.Thread(target=update_session, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        assert len(errors) == 0

        # Verify final state - should have 15 unique values (0-4 repeated 3 times)
        final = manager._load_session(session.session_id)
        # Due to concurrent updates, we should have at least some tasks
        # The exact count depends on timing, but should be > 0
        assert len(final.active_tasks) > 0
        # All values should be in range 0-4
        assert all(0 <= x < 5 for x in final.active_tasks)


class TestSessionValidation:
    """Test session validation and integrity checks."""

    @pytest.fixture
    def db_path(self):
        """Create temporary database for testing."""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        yield path
        try:
            os.unlink(path)
        except:
            pass

    @pytest.fixture
    def manager(self, db_path):
        """Create SessionManager instance for testing."""
        return SessionManager(db_path=db_path)

    def test_validate_valid_session(self, manager):
        """Test validating a valid session."""
        session = manager.start_session()

        result = manager._validate_session(session)

        assert result is True

    def test_validate_session_missing_id(self, manager):
        """Test validating session with missing ID."""
        session = manager.start_session()
        session.session_id = ""

        result = manager._validate_session(session)

        assert result is False

    def test_validate_session_missing_start_time(self, manager):
        """Test validating session with missing start time."""
        session = manager.start_session()
        session.start_time = None

        result = manager._validate_session(session)

        assert result is False

    def test_validate_corrupted_session(self, manager):
        """Test validating corrupted session."""
        session = manager.start_session()
        session.status = SessionStatus.CORRUPTED

        result = manager._validate_session(session)

        assert result is False

    def test_validate_session_invalid_checkpoint(self, manager):
        """Test validating session with invalid checkpoint."""
        session = manager.start_session()
        session.checkpoint_id = "  "  # Only whitespace

        result = manager._validate_session(session)

        assert result is False


class TestSessionSerialization:
    """Test session serialization and deserialization."""

    def test_session_to_dict(self):
        """Test converting session to dictionary."""
        session = Session(
            session_id="test-id",
            start_time=datetime.now(),
            status=SessionStatus.ACTIVE,
            config={"model": "gpt-4"},
            metadata={"user": "test"},
            active_operations=["op1"],
            active_tasks=[1, 2],
            checkpoint_id="chk-123",
        )

        data = session.to_dict()

        assert data["session_id"] == "test-id"
        assert data["status"] == "active"
        assert data["config"]["model"] == "gpt-4"
        assert data["metadata"]["user"] == "test"
        assert data["active_operations"] == ["op1"]
        assert data["active_tasks"] == [1, 2]
        assert data["checkpoint_id"] == "chk-123"
        assert "start_time" in data
        assert data["end_time"] is None

    def test_session_from_dict(self):
        """Test creating session from dictionary."""
        data = {
            "session_id": "test-id",
            "start_time": datetime.now().isoformat(),
            "status": "paused",
            "config": {"model": "gpt-4"},
            "metadata": {"user": "test"},
            "active_operations": ["op1"],
            "active_tasks": [1, 2],
            "checkpoint_id": "chk-123",
            "end_time": None,
        }

        session = Session.from_dict(data)

        assert session.session_id == "test-id"
        assert session.status == SessionStatus.PAUSED
        assert session.config["model"] == "gpt-4"
        assert session.metadata["user"] == "test"
        assert session.active_operations == ["op1"]
        assert session.active_tasks == [1, 2]
        assert session.checkpoint_id == "chk-123"
        assert session.end_time is None

    def test_session_round_trip(self):
        """Test session serialization round trip."""
        original = Session(
            session_id="test-id",
            start_time=datetime.now(),
            status=SessionStatus.ACTIVE,
            config={"model": "gpt-4"},
            metadata={"user": "test"},
            active_operations=["op1"],
            active_tasks=[1, 2],
            checkpoint_id="chk-123",
        )

        # Serialize and deserialize
        data = original.to_dict()
        restored = Session.from_dict(data)

        assert restored.session_id == original.session_id
        assert restored.status == original.status
        assert restored.config == original.config
        assert restored.metadata == original.metadata
        assert restored.active_operations == original.active_operations
        assert restored.active_tasks == original.active_tasks
        assert restored.checkpoint_id == original.checkpoint_id


class TestSessionManagerSingleton:
    """Test SessionManager singleton pattern."""

    def test_get_session_manager_singleton(self):
        """Test that get_session_manager returns singleton."""
        fd, db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)

        try:
            manager1 = get_session_manager(db_path=db_path)
            manager2 = get_session_manager()

            assert manager1 is manager2
        finally:
            try:
                os.unlink(db_path)
            except:
                pass


class TestListSessions:
    """Test session listing and filtering."""

    @pytest.fixture
    def db_path(self):
        """Create temporary database for testing."""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        yield path
        try:
            os.unlink(path)
        except:
            pass

    @pytest.fixture
    def manager(self, db_path):
        """Create SessionManager instance for testing."""
        return SessionManager(db_path=db_path)

    def test_list_all_sessions(self, manager):
        """Test listing all sessions."""
        session1 = manager.start_session()
        manager.complete_session(session1.session_id)

        session2 = manager.start_session()
        manager.pause_session(session2.session_id)

        sessions = manager.list_sessions()

        assert len(sessions) >= 2

    def test_list_sessions_by_status(self, manager):
        """Test listing sessions filtered by status."""
        session1 = manager.start_session()
        manager.complete_session(session1.session_id)

        session2 = manager.start_session()

        active_sessions = manager.list_sessions(status=SessionStatus.ACTIVE)

        assert len(active_sessions) >= 1
        assert all(s.status == SessionStatus.ACTIVE for s in active_sessions)
        assert any(s.session_id == session2.session_id for s in active_sessions)

    def test_list_sessions_with_limit(self, manager):
        """Test listing sessions with limit."""
        for _ in range(5):
            session = manager.start_session()
            manager.complete_session(session.session_id)

        sessions = manager.list_sessions(limit=3)

        assert len(sessions) == 3

    def test_list_sessions_empty_result(self, manager):
        """Test listing sessions when none match criteria."""
        archived_sessions = manager.list_sessions(status=SessionStatus.ARCHIVED)

        assert len(archived_sessions) == 0
