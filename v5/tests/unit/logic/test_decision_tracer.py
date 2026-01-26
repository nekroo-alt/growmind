"""
Unit tests for DecisionTracer module.

Tests decision trace logging, querying, and export functionality.
"""

import json
import os
import pytest
import tempfile
from datetime import datetime, timedelta
from typing import Dict, Any, List

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from v5.data.decision_tracer import DecisionTracer, get_tracer


@pytest.fixture
def tracer():
    """Create a temporary DecisionTracer instance."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    tracer = DecisionTracer(db_path)
    yield tracer
    
    # Cleanup
    try:
        os.unlink(db_path)
    except:
        pass


@pytest.fixture
def sample_decision():
    """Sample decision data for testing."""
    return {
        "operation_id": "op_123",
        "task_id": 42,
        "context_snapshot": {
            "current_state": "implementing_feature",
            "error_type": "LLM_RATE_LIMIT",
            "resource_availability": "high"
        },
        "reasoning_chain": [
            {"step": 1, "thought": "Need to implement feature X", "conclusion": "Start with test"},
            {"step": 2, "thought": "Write failing test first", "conclusion": "Create test file"}
        ],
        "alternatives": [
            {"action": "implement_directly", "reason_for_rejection": "Violates TDD"},
            {"action": "mock_dependencies", "reason_for_rejection": "Hides bugs"}
        ],
        "selected_action": "write_test_first",
        "confidence": 0.85,
        "resources": {
            "time": 1.2,
            "tokens": 1250
        }
    }


class TestDecisionTracerInit:
    """Test DecisionTracer initialization."""
    
    def test_init_creates_database(self, tracer):
        """Test that initialization creates database."""
        assert os.path.exists(tracer.db_path)
    
    def test_init_creates_tables(self, tracer):
        """Test that initialization creates required tables."""
        import sqlite3
        conn = sqlite3.connect(tracer.db_path)
        cursor = conn.cursor()
        
        # Check main table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='decision_traces'
        """)
        assert cursor.fetchone() is not None
        
        # Check FTS table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='decision_fts'
        """)
        assert cursor.fetchone() is not None
        
        conn.close()
    
    def test_init_creates_indexes(self, tracer):
        """Test that initialization creates indexes."""
        import sqlite3
        conn = sqlite3.connect(tracer.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='index' AND name LIKE 'idx_decision_%'
        """)
        indexes = [row[0] for row in cursor.fetchall()]
        
        assert 'idx_decision_timestamp' in indexes
        assert 'idx_decision_operation_id' in indexes
        assert 'idx_decision_task_id' in indexes
        assert 'idx_decision_confidence' in indexes
        
        conn.close()


class TestLogDecision:
    """Test decision logging functionality."""
    
    def test_log_decision_returns_id(self, tracer, sample_decision):
        """Test that logging returns a decision ID."""
        decision_id = tracer.log_decision(**sample_decision)
        assert decision_id is not None
        assert isinstance(decision_id, str)
        assert len(decision_id) == 36  # UUID format
    
    def test_log_decision_persists_data(self, tracer, sample_decision):
        """Test that logging persists decision data."""
        decision_id = tracer.log_decision(**sample_decision)
        
        retrieved = tracer.trace_decision(decision_id)
        assert retrieved is not None
        assert retrieved['decision_id'] == decision_id
        assert retrieved['operation_id'] == sample_decision['operation_id']
        assert retrieved['task_id'] == sample_decision['task_id']
        assert retrieved['selected_action'] == sample_decision['selected_action']
        assert retrieved['confidence'] == sample_decision['confidence']
    
    def test_log_decision_stores_context_snapshot(self, tracer, sample_decision):
        """Test that context snapshot is stored correctly."""
        decision_id = tracer.log_decision(**sample_decision)
        
        retrieved = tracer.trace_decision(decision_id)
        assert retrieved['context_snapshot'] == sample_decision['context_snapshot']
    
    def test_log_decision_stores_reasoning_chain(self, tracer, sample_decision):
        """Test that reasoning chain is stored correctly."""
        decision_id = tracer.log_decision(**sample_decision)
        
        retrieved = tracer.trace_decision(decision_id)
        assert retrieved['reasoning_chain'] == sample_decision['reasoning_chain']
    
    def test_log_decision_stores_alternatives(self, tracer, sample_decision):
        """Test that alternatives are stored correctly."""
        decision_id = tracer.log_decision(**sample_decision)
        
        retrieved = tracer.trace_decision(decision_id)
        assert retrieved['alternatives'] == sample_decision['alternatives']
    
    def test_log_decision_stores_resources(self, tracer, sample_decision):
        """Test that resources are stored correctly."""
        decision_id = tracer.log_decision(**sample_decision)
        
        retrieved = tracer.trace_decision(decision_id)
        assert retrieved['resources'] == sample_decision['resources']
    
    def test_log_decision_without_resources(self, tracer, sample_decision):
        """Test logging decision without resources."""
        sample_decision_no_resources = sample_decision.copy()
        del sample_decision_no_resources['resources']
        
        decision_id = tracer.log_decision(**sample_decision_no_resources)
        retrieved = tracer.trace_decision(decision_id)
        
        assert retrieved['resources'] == {}
    
    def test_log_decision_without_task_id(self, tracer, sample_decision):
        """Test logging decision without task ID."""
        sample_decision_no_task = sample_decision.copy()
        del sample_decision_no_task['task_id']
        
        decision_id = tracer.log_decision(**sample_decision_no_task)
        retrieved = tracer.trace_decision(decision_id)
        
        assert retrieved['task_id'] is None
    
    def test_log_multiple_decisions(self, tracer, sample_decision):
        """Test logging multiple decisions."""
        decision_id1 = tracer.log_decision(**sample_decision)
        decision_id2 = tracer.log_decision(**sample_decision)
        
        assert decision_id1 != decision_id2
        
        retrieved1 = tracer.trace_decision(decision_id1)
        retrieved2 = tracer.trace_decision(decision_id2)
        
        assert retrieved1 is not None
        assert retrieved2 is not None


class TestTraceDecision:
    """Test decision retrieval functionality."""
    
    def test_trace_existing_decision(self, tracer, sample_decision):
        """Test retrieving an existing decision."""
        decision_id = tracer.log_decision(**sample_decision)
        
        retrieved = tracer.trace_decision(decision_id)
        assert retrieved is not None
        assert retrieved['decision_id'] == decision_id
    
    def test_trace_nonexistent_decision(self, tracer):
        """Test retrieving a non-existent decision."""
        retrieved = tracer.trace_decision("nonexistent_id")
        assert retrieved is None
    
    def test_trace_returns_complete_data(self, tracer, sample_decision):
        """Test that trace returns complete decision data."""
        decision_id = tracer.log_decision(**sample_decision)
        
        retrieved = tracer.trace_decision(decision_id)
        
        expected_keys = [
            'decision_id', 'timestamp', 'operation_id', 'task_id',
            'context_snapshot', 'reasoning_chain', 'alternatives',
            'selected_action', 'confidence', 'resources'
        ]
        
        for key in expected_keys:
            assert key in retrieved


class TestSearch:
    """Test decision search functionality."""
    
    def test_search_by_task_id(self, tracer, sample_decision):
        """Test searching by task ID."""
        tracer.log_decision(**sample_decision)
        
        results = tracer.search(task_id=42)
        assert len(results) == 1
        assert results[0]['task_id'] == 42
    
    def test_search_by_operation_id(self, tracer, sample_decision):
        """Test searching by operation ID."""
        tracer.log_decision(**sample_decision)
        
        results = tracer.search(operation_id="op_123")
        assert len(results) == 1
        assert results[0]['operation_id'] == "op_123"
    
    def test_search_by_time_range(self, tracer, sample_decision):
        """Test searching by time range."""
        tracer.log_decision(**sample_decision)
        
        start_time = (datetime.utcnow() - timedelta(minutes=5)).isoformat()
        end_time = (datetime.utcnow() + timedelta(minutes=5)).isoformat()
        
        results = tracer.search(start_time=start_time, end_time=end_time)
        assert len(results) == 1
    
    def test_search_by_confidence_range(self, tracer, sample_decision):
        """Test searching by confidence range."""
        tracer.log_decision(**sample_decision)
        
        results = tracer.search(min_confidence=0.8, max_confidence=0.9)
        assert len(results) == 1
        assert 0.8 <= results[0]['confidence'] <= 0.9
    
    def test_search_by_action_pattern(self, tracer, sample_decision):
        """Test searching by action pattern."""
        tracer.log_decision(**sample_decision)
        
        results = tracer.search(action_pattern="test")
        assert len(results) == 1
        assert "test" in results[0]['selected_action']
    
    def test_search_with_multiple_filters(self, tracer, sample_decision):
        """Test searching with multiple filters."""
        tracer.log_decision(**sample_decision)
        
        results = tracer.search(
            task_id=42,
            operation_id="op_123",
            min_confidence=0.8
        )
        assert len(results) == 1
    
    def test_search_limit(self, tracer, sample_decision):
        """Test search result limit."""
        for i in range(5):
            decision = sample_decision.copy()
            decision['operation_id'] = f"op_{i}"
            tracer.log_decision(**decision)
        
        results = tracer.search(limit=3)
        assert len(results) == 3
    
    def test_search_no_results(self, tracer):
        """Test search with no matching results."""
        results = tracer.search(task_id=999)
        assert len(results) == 0


class TestSearchContext:
    """Test context search functionality."""
    
    def test_search_by_context_key_value(self, tracer, sample_decision):
        """Test searching by context key-value pair."""
        tracer.log_decision(**sample_decision)
        
        results = tracer.search_context("error_type", "LLM_RATE_LIMIT")
        assert len(results) == 1
    
    def test_search_context_no_results(self, tracer, sample_decision):
        """Test context search with no results."""
        tracer.log_decision(**sample_decision)
        
        results = tracer.search_context("nonexistent_key", "value")
        assert len(results) == 0


class TestSearchReasoning:
    """Test reasoning search functionality."""
    
    def test_search_by_reasoning_keyword(self, tracer, sample_decision):
        """Test searching by reasoning keyword."""
        tracer.log_decision(**sample_decision)
        
        results = tracer.search_reasoning("implement")
        assert len(results) >= 1
    
    def test_search_reasoning_no_results(self, tracer, sample_decision):
        """Test reasoning search with no results."""
        tracer.log_decision(**sample_decision)
        
        results = tracer.search_reasoning("nonexistent_keyword_xyz")
        # FTS may return partial matches, so we expect 0 or very few results
        assert len(results) == 0


class TestGetLastDecision:
    """Test getting last decision functionality."""
    
    def test_get_last_decision_unfiltered(self, tracer, sample_decision):
        """Test getting most recent decision."""
        decision_id = tracer.log_decision(**sample_decision)
        
        last = tracer.get_last_decision()
        assert last is not None
        assert last['decision_id'] == decision_id
    
    def test_get_last_decision_by_operation_id(self, tracer, sample_decision):
        """Test getting last decision filtered by operation ID."""
        decision_id = tracer.log_decision(**sample_decision)
        
        last = tracer.get_last_decision(operation_id="op_123")
        assert last is not None
        assert last['decision_id'] == decision_id
        assert last['operation_id'] == "op_123"
    
    def test_get_last_decision_by_task_id(self, tracer, sample_decision):
        """Test getting last decision filtered by task ID."""
        decision_id = tracer.log_decision(**sample_decision)
        
        last = tracer.get_last_decision(task_id=42)
        assert last is not None
        assert last['decision_id'] == decision_id
        assert last['task_id'] == 42
    
    def test_get_last_decision_no_decisions(self, tracer):
        """Test getting last decision when no decisions exist."""
        last = tracer.get_last_decision()
        assert last is None


class TestExportTraces:
    """Test decision trace export functionality."""
    
    def test_export_json_format(self, tracer, sample_decision):
        """Test exporting in JSON format."""
        decision_id = tracer.log_decision(**sample_decision)
        decisions = [tracer.trace_decision(decision_id)]
        
        exported = tracer.export_traces(decisions, format="json")
        
        assert isinstance(exported, str)
        exported_data = json.loads(exported)
        assert len(exported_data) == 1
        assert exported_data[0]['decision_id'] == decision_id
    
    def test_export_csv_format(self, tracer, sample_decision):
        """Test exporting in CSV format."""
        decision_id = tracer.log_decision(**sample_decision)
        decisions = [tracer.trace_decision(decision_id)]
        
        exported = tracer.export_traces(decisions, format="csv")
        
        assert isinstance(exported, str)
        assert "decision_id" in exported
        assert "selected_action" in exported
        assert decision_id in exported
    
    def test_export_to_file(self, tracer, sample_decision):
        """Test exporting to file."""
        decision_id = tracer.log_decision(**sample_decision)
        decisions = [tracer.trace_decision(decision_id)]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            file_path = f.name
        
        try:
            tracer.export_traces(decisions, format="json", file_path=file_path)
            
            assert os.path.exists(file_path)
            
            with open(file_path, 'r') as f:
                exported_data = json.load(f)
                assert len(exported_data) == 1
        finally:
            try:
                os.unlink(file_path)
            except:
                pass
    
    def test_export_unsupported_format(self, tracer, sample_decision):
        """Test exporting with unsupported format."""
        decision_id = tracer.log_decision(**sample_decision)
        decisions = [tracer.trace_decision(decision_id)]
        
        with pytest.raises(ValueError, match="Unsupported format"):
            tracer.export_traces(decisions, format="xml")


class TestGetStatistics:
    """Test statistics functionality."""
    
    def test_get_statistics_with_decisions(self, tracer, sample_decision):
        """Test getting statistics with decisions."""
        tracer.log_decision(**sample_decision)
        
        stats = tracer.get_statistics()
        
        assert 'total_decisions' in stats
        assert 'average_confidence' in stats
        assert 'confidence_distribution' in stats
        assert 'top_tasks' in stats
        
        assert stats['total_decisions'] == 1
        assert stats['average_confidence'] == sample_decision['confidence']
    
    def test_get_statistics_confidence_distribution(self, tracer, sample_decision):
        """Test confidence distribution in statistics."""
        # Log decisions with different confidence levels
        sample_decision['confidence'] = 0.95  # High
        tracer.log_decision(**sample_decision)
        sample_decision['confidence'] = 0.75  # Medium
        tracer.log_decision(**sample_decision)
        sample_decision['confidence'] = 0.5  # Low
        tracer.log_decision(**sample_decision)
        
        stats = tracer.get_statistics()
        dist = stats['confidence_distribution']
        
        assert dist['high'] == 1
        assert dist['medium'] == 1
        assert dist['low'] == 1
    
    def test_get_statistics_top_tasks(self, tracer, sample_decision):
        """Test top tasks in statistics."""
        # Log multiple decisions for same task
        for i in range(3):
            tracer.log_decision(**sample_decision)
        
        stats = tracer.get_statistics()
        
        assert len(stats['top_tasks']) > 0
        assert stats['top_tasks'][0]['task_id'] == 42
        assert stats['top_tasks'][0]['decisions'] == 3
    
    def test_get_statistics_no_decisions(self, tracer):
        """Test getting statistics with no decisions."""
        stats = tracer.get_statistics()
        
        assert stats['total_decisions'] == 0
        assert stats['average_confidence'] == 0.0
        assert stats['confidence_distribution']['high'] == 0
        assert stats['confidence_distribution']['medium'] == 0
        assert stats['confidence_distribution']['low'] == 0
        assert len(stats['top_tasks']) == 0


class TestDeleteOldTraces:
    """Test deletion of old traces."""
    
    def test_delete_old_traces(self, tracer, sample_decision):
        """Test deleting traces older than specified days."""
        # Log a decision
        decision_id = tracer.log_decision(**sample_decision)
        
        # Manually update timestamp to be old
        import sqlite3
        conn = sqlite3.connect(tracer.db_path)
        cursor = conn.cursor()
        old_timestamp = (datetime.utcnow() - timedelta(days=35)).isoformat()
        cursor.execute(
            "UPDATE decision_traces SET timestamp = ? WHERE decision_id = ?",
            (old_timestamp, decision_id)
        )
        conn.commit()
        conn.close()
        
        # Delete traces older than 30 days
        deleted = tracer.delete_old_traces(days=30)
        
        assert deleted == 1
        
        # Verify decision is gone
        retrieved = tracer.trace_decision(decision_id)
        assert retrieved is None
    
    def test_delete_old_traces_keeps_recent(self, tracer, sample_decision):
        """Test that recent traces are not deleted."""
        decision_id = tracer.log_decision(**sample_decision)
        
        # Delete traces older than 30 days
        deleted = tracer.delete_old_traces(days=30)
        
        assert deleted == 0
        
        # Verify decision still exists
        retrieved = tracer.trace_decision(decision_id)
        assert retrieved is not None


class TestGetTracer:
    """Test global tracer instance."""
    
    def test_get_tracer_creates_instance(self):
        """Test that get_tracer creates an instance."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        try:
            tracer = get_tracer(db_path=db_path)
            assert tracer is not None
            assert isinstance(tracer, DecisionTracer)
        finally:
            try:
                os.unlink(db_path)
            except:
                pass
    
    def test_get_tracer_returns_same_instance(self):
        """Test that get_tracer returns same instance."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        try:
            # Reset global tracer
            import data.decision_tracer as dt_module
            dt_module._global_tracer = None
            
            tracer1 = get_tracer(db_path=db_path)
            tracer2 = get_tracer(db_path=db_path)
            
            assert tracer1 is tracer2
        finally:
            try:
                os.unlink(db_path)
            except:
                pass


class TestThreadSafety:
    """Test thread safety of DecisionTracer."""
    
    def test_concurrent_log_decisions(self, tracer, sample_decision):
        """Test logging decisions concurrently."""
        import threading
        
        results = []
        errors = []
        
        def log_decision():
            try:
                decision_id = tracer.log_decision(**sample_decision)
                results.append(decision_id)
            except Exception as e:
                errors.append(e)
        
        threads = [threading.Thread(target=log_decision) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert len(errors) == 0
        assert len(results) == 10
        assert len(set(results)) == 10  # All unique IDs


if __name__ == '__main__':
    pytest.main([__file__, '-v'])