"""
Test Task 5.4: Session Analytics and Reporting

Tests for session analytics, metrics, reporting, and visualization features.
"""

import pytest
import json
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import os

from v2.core.session_manager import SessionManager, SessionStatus
from v2.data.telemetry_manager import TelemetryManager


@pytest.fixture
def session_manager():
    """Create a temporary session manager for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_sessions.db")
        manager = SessionManager(db_path)
        yield manager


@pytest.fixture
def telemetry_manager():
    """Create a temporary telemetry manager for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_telemetry.db")
        manager = TelemetryManager(db_path)
        yield manager


class TestSessionMetrics:
    """Test session metrics calculation."""
    
    def test_get_session_metrics_basic(self, session_manager):
        """Test basic session metrics calculation."""
        session = session_manager.start_session(
            config={"llm_model": "gpt-4"},
            metadata={"user": "test_user"}
        )
        
        # Simulate some activity
        session.active_tasks = [1, 2, 3]
        session.active_operations = ["op1", "op2", "op3"]
        session_manager._save_session(session)
        
        # Get metrics
        metrics = session_manager.get_session_metrics(session.session_id)
        
        assert metrics["session_id"] == session.session_id
        assert metrics["tasks_completed"] == 3
        assert metrics["operations_count"] == 3
        assert metrics["status"] == SessionStatus.ACTIVE.value
        assert "duration_seconds" in metrics
        assert "duration_minutes" in metrics
    
    def test_get_session_metrics_with_telemetry(self, session_manager, telemetry_manager):
        """Test session metrics with telemetry integration."""
        # Start session
        session = session_manager.start_session()
        
        # Create some telemetry operations
        op1_id = telemetry_manager.start_operation("implementation", "Task 1")
        telemetry_manager.end_operation(op1_id, "completed")
        
        op2_id = telemetry_manager.start_operation("implementation", "Task 2")
        telemetry_manager.end_operation(op2_id, "failed")
        
        op3_id = telemetry_manager.start_operation("implementation", "Task 3")
        telemetry_manager.end_operation(op3_id, "completed")
        
        # Get metrics with telemetry
        metrics = session_manager.get_session_metrics(session.session_id, telemetry_manager)
        
        assert metrics["operations_completed"] == 2
        assert metrics["operations_failed"] == 1
        assert metrics["operations_success_rate"] == pytest.approx(66.67, rel=1e-2)
    
    def test_get_session_metrics_not_found(self, session_manager):
        """Test getting metrics for non-existent session."""
        metrics = session_manager.get_session_metrics("nonexistent")
        assert "error" in metrics


class TestSessionProductivity:
    """Test session productivity calculation."""
    
    def test_get_session_productivity(self, session_manager):
        """Test productivity metrics calculation."""
        session = session_manager.start_session()
        session.active_tasks = [1, 2, 3, 4, 5]
        session_manager._save_session(session)
        
        # Wait a bit to simulate session duration
        import time
        time.sleep(0.1)
        
        productivity = session_manager.get_session_productivity(session.session_id)
        
        assert productivity["session_id"] == session.session_id
        assert productivity["tasks_completed"] == 5
        assert "tasks_per_hour" in productivity
        assert "operations_per_hour" in productivity
        assert "productivity_score" in productivity
        assert 0 <= productivity["productivity_score"] <= 100
    
    def test_productivity_score_calculation(self, session_manager):
        """Test productivity score calculation formula."""
        # High productivity session
        session1 = session_manager.start_session()
        session1.active_tasks = [1, 2, 3, 4, 5]
        session_manager._save_session(session1)
        
        productivity1 = session_manager.get_session_productivity(session1.session_id)
        
        # Low productivity session
        session2 = session_manager.start_session()
        session2.active_tasks = [1]
        session_manager._save_session(session2)
        
        productivity2 = session_manager.get_session_productivity(session2.session_id)
        
        # High productivity session should have higher score
        assert productivity1["productivity_score"] > productivity2["productivity_score"]


class TestSessionTimeline:
    """Test session timeline generation."""
    
    def test_generate_session_timeline_basic(self, session_manager):
        """Test basic timeline generation."""
        session = session_manager.start_session()
        session_manager.complete_session(session.session_id)
        
        timeline = session_manager.generate_session_timeline(session.session_id)
        
        assert timeline["session_id"] == session.session_id
        assert len(timeline["events"]) >= 2  # start and end
        assert any(e["event_type"] == "session_start" for e in timeline["events"])
        assert any(e["event_type"] == "session_end" for e in timeline["events"])
    
    def test_generate_session_timeline_with_telemetry(self, session_manager, telemetry_manager):
        """Test timeline with telemetry events."""
        session = session_manager.start_session()
        
        # Create some operations
        op1_id = telemetry_manager.start_operation("implementation", "Task 1")
        telemetry_manager.end_operation(op1_id, "completed")
        
        op2_id = telemetry_manager.start_operation("implementation", "Task 2")
        telemetry_manager.record_event(op2_id, "test_event", "info", "Testing")
        telemetry_manager.end_operation(op2_id, "completed")
        
        timeline = session_manager.generate_session_timeline(session.session_id, telemetry_manager)
        
        # Should have session start/end + operation events
        assert len(timeline["events"]) > 2
        operation_events = [e for e in timeline["events"] if e["event_type"] == "operation_start"]
        assert len(operation_events) >= 2
    
    def test_timeline_events_sorted(self, session_manager, telemetry_manager):
        """Test that timeline events are sorted by timestamp."""
        session = session_manager.start_session()
        
        # Create operations out of order
        op1_id = telemetry_manager.start_operation("task1", "First task")
        op2_id = telemetry_manager.start_operation("task2", "Second task")
        
        telemetry_manager.end_operation(op2_id, "completed")
        telemetry_manager.end_operation(op1_id, "completed")
        
        timeline = session_manager.generate_session_timeline(session.session_id, telemetry_manager)
        
        # Check that events are sorted by timestamp
        timestamps = [e["timestamp"] for e in timeline["events"]]
        assert timestamps == sorted(timestamps)


class TestBottleneckIdentification:
    """Test bottleneck identification."""
    
    def test_identify_bottlenecks_slow_operations(self, session_manager, telemetry_manager):
        """Test identification of slow operations."""
        session = session_manager.start_session()
        
        # Create a fast operation
        fast_op_id = telemetry_manager.start_operation("fast", "Fast operation")
        telemetry_manager.end_operation(fast_op_id, "completed")
        
        # Create a slow operation (simulate by manipulating timestamp)
        slow_op_id = telemetry_manager.start_operation("slow", "Slow operation")
        import time
        time.sleep(0.1)  # Make it take some time
        telemetry_manager.end_operation(slow_op_id, "completed")
        
        bottlenecks = session_manager.identify_bottlenecks(session.session_id, telemetry_manager)
        
        # Should find bottlenecks
        assert len(bottlenecks) > 0
        assert any("slow" in b["operation_title"].lower() for b in bottlenecks)
    
    def test_identify_bottlenecks_failed_operations(self, session_manager, telemetry_manager):
        """Test identification of failed operations as bottlenecks."""
        session = session_manager.start_session()
        
        # Create a failed operation
        failed_op_id = telemetry_manager.start_operation("failed", "Failed operation")
        telemetry_manager.record_event(failed_op_id, "error", "error", "Operation failed")
        telemetry_manager.end_operation(failed_op_id, "failed")
        
        bottlenecks = session_manager.identify_bottlenecks(session.session_id, telemetry_manager)
        
        # Failed operations should be marked as critical
        critical_bottlenecks = [b for b in bottlenecks if b["severity"] == "critical"]
        assert len(critical_bottlenecks) > 0
    
    def test_identify_bottlenecks_without_telemetry(self, session_manager):
        """Test bottleneck identification without telemetry manager."""
        session = session_manager.start_session()
        
        bottlenecks = session_manager.identify_bottlenecks(session.session_id)
        
        assert len(bottlenecks) == 1
        assert "error" in bottlenecks[0]


class TestErrorPatterns:
    """Test error pattern identification."""
    
    def test_identify_error_patterns(self, session_manager, telemetry_manager):
        """Test error pattern identification."""
        session = session_manager.start_session()
        
        # Create multiple errors
        op1_id = telemetry_manager.start_operation("task1", "Task 1")
        telemetry_manager.record_event(op1_id, "error", "error", "File not found")
        telemetry_manager.end_operation(op1_id, "failed")
        
        op2_id = telemetry_manager.start_operation("task2", "Task 2")
        telemetry_manager.record_event(op2_id, "error", "error", "File not found")
        telemetry_manager.end_operation(op2_id, "failed")
        
        op3_id = telemetry_manager.start_operation("task3", "Task 3")
        telemetry_manager.record_event(op3_id, "error", "error", "Network timeout")
        telemetry_manager.end_operation(op3_id, "failed")
        
        patterns = session_manager.identify_error_patterns(session.session_id, telemetry_manager)
        
        assert patterns["total_errors"] == 3
        assert patterns["error_by_operation"]["error"] == 3
        assert "File not found" in [e["message"] for e in patterns["recurring_error_messages"]]
    
    def test_identify_error_patterns_without_telemetry(self, session_manager):
        """Test error pattern identification without telemetry manager."""
        session = session_manager.start_session()
        
        patterns = session_manager.identify_error_patterns(session.session_id)
        
        assert "error" in patterns


class TestSessionComparison:
    """Test session comparison functionality."""
    
    def test_compare_sessions(self, session_manager):
        """Test comparison of multiple sessions."""
        # Create multiple sessions
        session1 = session_manager.start_session()
        session1.active_tasks = [1, 2, 3]
        session_manager._save_session(session1)
        
        session2 = session_manager.start_session()
        session2.active_tasks = [4, 5, 6, 7]
        session_manager._save_session(session2)
        
        session3 = session_manager.start_session()
        session3.active_tasks = [8]
        session_manager._save_session(session3)
        
        comparison = session_manager.compare_sessions([
            session1.session_id,
            session2.session_id,
            session3.session_id
        ])
        
        assert comparison["session_count"] == 3
        assert "avg_tasks_completed" in comparison
        assert comparison["avg_tasks_completed"] == pytest.approx(2.67, rel=1e-2)
        assert comparison["best_session"]["tasks_completed"] == 4
        assert comparison["worst_session"]["tasks_completed"] == 1
    
    def test_compare_sessions_empty_list(self, session_manager):
        """Test comparison with empty session list."""
        comparison = session_manager.compare_sessions([])
        
        assert "error" in comparison
    
    def test_compare_sessions_with_telemetry(self, session_manager, telemetry_manager):
        """Test session comparison with telemetry data."""
        session1 = session_manager.start_session()
        op1_id = telemetry_manager.start_operation("task1", "Task 1")
        telemetry_manager.end_operation(op1_id, "completed")
        
        session2 = session_manager.start_session()
        op2_id = telemetry_manager.start_operation("task2", "Task 2")
        telemetry_manager.end_operation(op2_id, "failed")
        
        comparison = session_manager.compare_sessions(
            [session1.session_id, session2.session_id],
            telemetry_manager
        )
        
        assert comparison["session_count"] == 2
        assert comparison["overall_success_rate"] == 50.0


class TestReportGeneration:
    """Test report generation functionality."""
    
    def test_generate_report_basic(self, session_manager):
        """Test basic report generation."""
        session = session_manager.start_session()
        session.active_tasks = [1, 2, 3]
        session_manager.complete_session(session.session_id)
        
        report = session_manager.generate_report(session.session_id)
        
        assert report["session_id"] == session.session_id
        assert "metrics" in report
        assert "productivity" in report
        assert "timeline" in report
        assert report["status"] == SessionStatus.COMPLETED.value
    
    def test_generate_report_without_timeline(self, session_manager):
        """Test report generation without timeline."""
        session = session_manager.start_session()
        
        report = session_manager.generate_report(session.session_id, include_timeline=False)
        
        assert report["session_id"] == session.session_id
        assert "metrics" in report
        assert "timeline" not in report
    
    def test_generate_period_report(self, session_manager):
        """Test period report generation."""
        # Create sessions over the last week
        for i in range(3):
            session = session_manager.start_session()
            session.active_tasks = [i*3 + 1, i*3 + 2, i*3 + 3]
            session_manager.complete_session(session.session_id)
        
        report = session_manager.generate_period_report(days=7)
        
        assert report["session_count"] == 3
        assert report["period_days"] == 7
        assert "comparison" in report
        assert "daily_sessions" in report
    
    def test_generate_period_report_no_sessions(self, session_manager):
        """Test period report with no sessions."""
        report = session_manager.generate_period_report(days=1)
        
        assert report["session_count"] == 0
        assert "message" in report


class TestReportExport:
    """Test report export functionality."""
    
    def test_export_report_json(self, session_manager):
        """Test exporting report to JSON."""
        session = session_manager.start_session()
        session.active_tasks = [1, 2, 3]
        
        with tempfile.TemporaryDirectory() as tmpdir:
            export_path = os.path.join(tmpdir, "report.json")
            success = session_manager.export_report(session.session_id, export_path)
            
            assert success
            assert os.path.exists(export_path)
            
            # Verify file contents
            with open(export_path, 'r') as f:
                data = json.load(f)
            
            assert data["session_id"] == session.session_id
            assert "metrics" in data
    
    def test_export_report_markdown(self, session_manager):
        """Test exporting report to Markdown."""
        session = session_manager.start_session()
        session.active_tasks = [1, 2, 3]
        
        with tempfile.TemporaryDirectory() as tmpdir:
            export_path = os.path.join(tmpdir, "report.md")
            success = session_manager.export_report(session.session_id, export_path, format="markdown")
            
            assert success
            assert os.path.exists(export_path)
            
            # Verify file contents
            with open(export_path, 'r') as f:
                content = f.read()
            
            assert "# Session Report" in content
            assert session.session_id in content
    
    def test_export_report_unsupported_format(self, session_manager):
        """Test exporting report with unsupported format."""
        session = session_manager.start_session()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            export_path = os.path.join(tmpdir, "report.txt")
            success = session_manager.export_report(
                session.session_id,
                export_path,
                format="txt"
            )
            
            assert not success


class TestCheckpointHelpers:
    """Test checkpoint helper methods."""
    
    def test_get_session_checkpoint_count(self, session_manager):
        """Test getting checkpoint count for a session."""
        session = session_manager.start_session()
        
        # Add some checkpoints
        session_manager._save_checkpoint_mapping(session.session_id, "chk1")
        session_manager._save_checkpoint_mapping(session.session_id, "chk2")
        session_manager._save_checkpoint_mapping(session.session_id, "chk3")
        
        count = session_manager._get_session_checkpoint_count(session.session_id)
        assert count == 3
    
    def test_get_session_checkpoints(self, session_manager):
        """Test getting all checkpoints for a session."""
        session = session_manager.start_session()
        
        # Add some checkpoints
        session_manager._save_checkpoint_mapping(session.session_id, "chk1")
        session_manager._save_checkpoint_mapping(session.session_id, "chk2")
        
        checkpoints = session_manager._get_session_checkpoints(session.session_id)
        
        assert len(checkpoints) == 2
        assert "chk1" in checkpoints
        assert "chk2" in checkpoints
        # Checkpoints should be in order
        assert checkpoints == ["chk1", "chk2"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
