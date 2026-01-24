"""
Unit Tests for Decision History Manager - Task 6.1

Tests the decision history tracking functionality including:
- Decision recording with full context
- Decision dependency tracking
- Decision alternatives tracking
- Decision graph building
- Search and query interface
- Export functionality
"""

import pytest
import tempfile
import os
import json
from datetime import datetime, timedelta
from data.decision_history import DecisionHistoryManager, get_decision_history_manager


@pytest.fixture
def temp_db_path():
    """Create a temporary database path for testing."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    # Cleanup
    if os.path.exists(path):
        os.remove(path)


@pytest.fixture
def decision_history(temp_db_path):
    """Create a DecisionHistoryManager instance with temporary database."""
    manager = DecisionHistoryManager(db_path=temp_db_path)
    return manager


class TestDecisionRecording:
    """Test decision recording functionality."""

    def test_record_decision_basic(self, decision_history):
        """Test recording a basic decision."""
        decision_id = decision_history.record_decision(
            reasoning="Fix the bug in the authentication module",
            action="Implement JWT token validation",
            confidence=0.85,
        )

        assert decision_id is not None
        assert len(decision_id) == 36  # UUID format

    def test_record_decision_with_full_context(self, decision_history):
        """Test recording a decision with all parameters."""
        context = {
            "error_type": "JWTValidationError",
            "module": "authentication",
            "file": "auth.py",
            "line": 42,
        }

        alternatives = [
            {
                "action": "Use OAuth2 instead",
                "reason_for_rejection": "Too complex for current requirements",
                "estimated_success": 0.6,
            },
            {
                "action": "Add simple token check",
                "reason_for_rejection": "Not secure enough",
                "estimated_success": 0.5,
            },
        ]

        decision_id = decision_history.record_decision(
            reasoning="Need to validate JWT tokens for authentication",
            action="Implement JWT token validation",
            confidence=0.85,
            context=context,
            operation_id="op_123",
            task_id=42,
            metadata={"priority": "high", "assignee": "AI"},
            alternatives=alternatives,
        )

        # Retrieve decision
        decision = decision_history.get_decision(decision_id)
        assert decision is not None
        assert decision["reasoning"] == "Need to validate JWT tokens for authentication"
        assert decision["action"] == "Implement JWT token validation"
        assert decision["confidence"] == 0.85
        assert decision["operation_id"] == "op_123"
        assert decision["task_id"] == 42
        assert decision["context"] == context
        assert decision["metadata"] == {"priority": "high", "assignee": "AI"}

        # Check alternatives
        alts = decision_history.get_decision_alternatives(decision_id)
        assert len(alts) == 2
        assert alts[0]["alternative_action"] == "Use OAuth2 instead"
        assert alts[1]["alternative_action"] == "Add simple token check"

    def test_record_decision_with_dependencies(self, decision_history):
        """Test recording a decision with dependencies."""
        # Create prerequisite decision
        dep1_id = decision_history.record_decision(
            reasoning="First decision",
            action="Action 1",
            confidence=0.9,
        )

        dep2_id = decision_history.record_decision(
            reasoning="Second decision",
            action="Action 2",
            confidence=0.8,
        )

        # Create decision that depends on previous decisions
        decision_id = decision_history.record_decision(
            reasoning="Dependent decision",
            action="Action 3",
            confidence=0.85,
            dependencies=[dep1_id, dep2_id],
        )

        # Check dependencies
        deps = decision_history.get_decision_dependencies(decision_id)
        assert len(deps) == 2
        assert deps[0]["depends_on_decision_id"] == dep1_id
        assert deps[1]["depends_on_decision_id"] == dep2_id

    def test_record_outcome(self, decision_history):
        """Test recording outcome of a decision."""
        decision_id = decision_history.record_decision(
            reasoning="Test decision",
            action="Test action",
            confidence=0.9,
        )

        # Record outcome
        decision_history.record_outcome(
            decision_id=decision_id,
            outcome="success",
            time_elapsed=12.5,
            resources={"tokens": 1250, "api_calls": 3},
        )

        # Verify outcome was recorded
        decision = decision_history.get_decision(decision_id)
        assert decision["outcome"] == "success"
        assert decision["time_elapsed"] == 12.5
        assert decision["resources"] == {"tokens": 1250, "api_calls": 3}

    def test_record_alternative(self, decision_history):
        """Test recording an alternative for a decision."""
        decision_id = decision_history.record_decision(
            reasoning="Main decision",
            action="Main action",
            confidence=0.9,
        )

        alt_id = decision_history.record_alternative(
            decision_id=decision_id,
            alternative_action="Alternative action",
            reason_for_rejection="Not efficient enough",
            estimated_success=0.7,
        )

        assert alt_id is not None

        # Retrieve alternatives
        alts = decision_history.get_decision_alternatives(decision_id)
        assert len(alts) == 1
        assert alts[0]["alternative_action"] == "Alternative action"
        assert alts[0]["reason_for_rejection"] == "Not efficient enough"
        assert alts[0]["estimated_success"] == 0.7

    def test_record_dependency(self, decision_history):
        """Test recording a dependency between decisions."""
        dep_id = decision_history.record_decision(
            reasoning="Dependency",
            action="Dep action",
            confidence=0.9,
        )

        decision_id = decision_history.record_decision(
            reasoning="Main decision",
            action="Main action",
            confidence=0.9,
        )

        dep_relation_id = decision_history.record_dependency(
            decision_id=decision_id,
            depends_on_decision_id=dep_id,
            dependency_type="prerequisite",
        )

        assert dep_relation_id is not None

        # Verify dependency
        deps = decision_history.get_decision_dependencies(decision_id)
        assert len(deps) == 1
        assert deps[0]["depends_on_decision_id"] == dep_id
        assert deps[0]["dependency_type"] == "prerequisite"


class TestDecisionRetrieval:
    """Test decision retrieval functionality."""

    def test_get_decision(self, decision_history):
        """Test retrieving a decision by ID."""
        decision_id = decision_history.record_decision(
            reasoning="Test reasoning",
            action="Test action",
            confidence=0.85,
        )

        decision = decision_history.get_decision(decision_id)
        assert decision is not None
        assert decision["id"] == decision_id
        assert decision["reasoning"] == "Test reasoning"
        assert decision["action"] == "Test action"

    def test_get_nonexistent_decision(self, decision_history):
        """Test retrieving a non-existent decision."""
        decision = decision_history.get_decision("nonexistent_id")
        assert decision is None

    def test_list_decisions_no_filter(self, decision_history):
        """Test listing all decisions."""
        # Create multiple decisions
        decision_history.record_decision(
            reasoning="Decision 1", action="Action 1", confidence=0.9
        )
        decision_history.record_decision(
            reasoning="Decision 2", action="Action 2", confidence=0.8
        )
        decision_history.record_decision(
            reasoning="Decision 3", action="Action 3", confidence=0.85
        )

        decisions = decision_history.list_decisions()
        assert len(decisions) == 3

    def test_list_decisions_with_operation_filter(self, decision_history):
        """Test listing decisions filtered by operation ID."""
        decision_history.record_decision(
            reasoning="Decision 1",
            action="Action 1",
            confidence=0.9,
            operation_id="op_1",
        )
        decision_history.record_decision(
            reasoning="Decision 2",
            action="Action 2",
            confidence=0.8,
            operation_id="op_2",
        )
        decision_history.record_decision(
            reasoning="Decision 3",
            action="Action 3",
            confidence=0.85,
            operation_id="op_1",
        )

        decisions = decision_history.list_decisions(operation_id="op_1")
        assert len(decisions) == 2
        assert all(d["operation_id"] == "op_1" for d in decisions)

    def test_list_decisions_with_task_filter(self, decision_history):
        """Test listing decisions filtered by task ID."""
        decision_history.record_decision(
            reasoning="Decision 1",
            action="Action 1",
            confidence=0.9,
            task_id=1,
        )
        decision_history.record_decision(
            reasoning="Decision 2",
            action="Action 2",
            confidence=0.8,
            task_id=2,
        )
        decision_history.record_decision(
            reasoning="Decision 3",
            action="Action 3",
            confidence=0.85,
            task_id=1,
        )

        decisions = decision_history.list_decisions(task_id=1)
        assert len(decisions) == 2
        assert all(d["task_id"] == 1 for d in decisions)

    def test_list_decisions_with_outcome_filter(self, decision_history):
        """Test listing decisions filtered by outcome."""
        id1 = decision_history.record_decision(
            reasoning="Decision 1", action="Action 1", confidence=0.9
        )
        id2 = decision_history.record_decision(
            reasoning="Decision 2", action="Action 2", confidence=0.8
        )

        decision_history.record_outcome(id1, "success")
        decision_history.record_outcome(id2, "failure")

        decisions = decision_history.list_decisions(outcome="success")
        assert len(decisions) == 1
        assert decisions[0]["id"] == id1

    def test_list_decisions_with_pagination(self, decision_history):
        """Test listing decisions with pagination."""
        # Create 5 decisions
        for i in range(5):
            decision_history.record_decision(
                reasoning=f"Decision {i}", action=f"Action {i}", confidence=0.9
            )

        # Get first page (limit 2, offset 0)
        page1 = decision_history.list_decisions(limit=2, offset=0)
        assert len(page1) == 2

        # Get second page (limit 2, offset 2)
        page2 = decision_history.list_decisions(limit=2, offset=2)
        assert len(page2) == 2

        # Get third page (limit 2, offset 4)
        page3 = decision_history.list_decisions(limit=2, offset=4)
        assert len(page3) == 1


class TestDecisionGraph:
    """Test decision graph building functionality."""

    def test_get_decision_graph_simple(self, decision_history):
        """Test building a simple decision graph."""
        decision_id = decision_history.record_decision(
            reasoning="Root decision",
            action="Root action",
            confidence=0.9,
        )

        graph = decision_history.get_decision_graph(decision_id, max_depth=3)
        assert "nodes" in graph
        assert "edges" in graph
        assert decision_id in graph["nodes"]
        assert graph["nodes"][decision_id]["action"] == "Root action"

    def test_get_decision_graph_with_dependencies(self, decision_history):
        """Test building a decision graph with dependencies."""
        # Create prerequisite decisions
        dep1 = decision_history.record_decision(
            reasoning="Dependency 1", action="Dep action 1", confidence=0.9
        )
        dep2 = decision_history.record_decision(
            reasoning="Dependency 2", action="Dep action 2", confidence=0.8
        )

        # Create decision that depends on both
        decision_id = decision_history.record_decision(
            reasoning="Main decision",
            action="Main action",
            confidence=0.85,
            dependencies=[dep1, dep2],
        )

        # Build graph
        graph = decision_history.get_decision_graph(decision_id, max_depth=2)

        # Check nodes
        assert len(graph["nodes"]) == 3
        assert decision_id in graph["nodes"]
        assert dep1 in graph["nodes"]
        assert dep2 in graph["nodes"]

        # Check edges (dependencies point from dep -> decision)
        assert len(graph["edges"]) == 2
        edge_from = [e["from"] for e in graph["edges"]]
        edge_to = [e["to"] for e in graph["edges"]]
        assert decision_id in edge_to
        assert dep1 in edge_from
        assert dep2 in edge_from

    def test_get_decision_graph_with_dependents(self, decision_history):
        """Test building a decision graph with dependent decisions."""
        # Create root decision
        root_id = decision_history.record_decision(
            reasoning="Root decision",
            action="Root action",
            confidence=0.9,
        )

        # Create decisions that depend on root
        dep1 = decision_history.record_decision(
            reasoning="Dependent 1",
            action="Dep action 1",
            confidence=0.85,
            dependencies=[root_id],
        )
        dep2 = decision_history.record_decision(
            reasoning="Dependent 2",
            action="Dep action 2",
            confidence=0.8,
            dependencies=[root_id],
        )

        # Build graph
        graph = decision_history.get_decision_graph(root_id, max_depth=2)

        # Check nodes
        assert len(graph["nodes"]) == 3
        assert root_id in graph["nodes"]
        assert dep1 in graph["nodes"]
        assert dep2 in graph["nodes"]

        # Check edges (dependencies point from root -> dep)
        assert len(graph["edges"]) == 2
        edge_from = [e["from"] for e in graph["edges"]]
        edge_to = [e["to"] for e in graph["edges"]]
        assert root_id in edge_from
        assert dep1 in edge_to
        assert dep2 in edge_to

    def test_get_decision_graph_depth_limit(self, decision_history):
        """Test that graph traversal respects depth limit."""
        # Create chain: d1 -> d2 -> d3 -> d4
        d1 = decision_history.record_decision(
            reasoning="Decision 1", action="Action 1", confidence=0.9
        )
        d2 = decision_history.record_decision(
            reasoning="Decision 2",
            action="Action 2",
            confidence=0.85,
            dependencies=[d1],
        )
        d3 = decision_history.record_decision(
            reasoning="Decision 3",
            action="Action 3",
            confidence=0.8,
            dependencies=[d2],
        )
        d4 = decision_history.record_decision(
            reasoning="Decision 4",
            action="Action 4",
            confidence=0.75,
            dependencies=[d3],
        )

        # Build graph with depth limit of 2
        graph = decision_history.get_decision_graph(d4, max_depth=2)

        # Should only include d4, d3, d2 (not d1)
        assert len(graph["nodes"]) == 3
        assert d4 in graph["nodes"]
        assert d3 in graph["nodes"]
        assert d2 in graph["nodes"]
        assert d1 not in graph["nodes"]


class TestSearchInterface:
    """Test search and query functionality."""

    def test_search_decisions_by_action(self, decision_history):
        """Test searching decisions by action content."""
        decision_history.record_decision(
            reasoning="Test 1", action="Implement feature X", confidence=0.9
        )
        decision_history.record_decision(
            reasoning="Test 2", action="Fix bug in module Y", confidence=0.85
        )
        decision_history.record_decision(
            reasoning="Test 3", action="Refactor feature X", confidence=0.8
        )

        results = decision_history.search_decisions(action_contains="feature")
        assert len(results) == 2

    def test_search_decisions_by_reasoning(self, decision_history):
        """Test searching decisions by reasoning content."""
        decision_history.record_decision(
            reasoning="Need to fix authentication bug",
            action="Fix auth",
            confidence=0.9,
        )
        decision_history.record_decision(
            reasoning="Implement user profile feature",
            action="Add profile",
            confidence=0.85,
        )
        decision_history.record_decision(
            reasoning="Refactor authentication code",
            action="Refactor auth",
            confidence=0.8,
        )

        results = decision_history.search_decisions(reasoning_contains="authentication")
        assert len(results) == 2

    def test_search_decisions_by_confidence(self, decision_history):
        """Test searching decisions by confidence range."""
        decision_history.record_decision(
            reasoning="High confidence", action="Action 1", confidence=0.95
        )
        decision_history.record_decision(
            reasoning="Medium confidence", action="Action 2", confidence=0.75
        )
        decision_history.record_decision(
            reasoning="Low confidence", action="Action 3", confidence=0.55
        )

        results = decision_history.search_decisions(
            min_confidence=0.7, max_confidence=0.9
        )
        assert len(results) == 1
        assert results[0]["confidence"] == 0.75

    def test_search_decisions_combined_filters(self, decision_history):
        """Test searching with multiple filters."""
        decision_history.record_decision(
            reasoning="Test 1",
            action="Implement feature",
            confidence=0.9,
            task_id=1,
        )
        decision_history.record_decision(
            reasoning="Test 2",
            action="Fix bug",
            confidence=0.85,
            task_id=2,
        )
        decision_history.record_decision(
            reasoning="Test 3",
            action="Implement feature",
            confidence=0.8,
            task_id=1,
        )

        results = decision_history.search_decisions(
            action_contains="Implement", task_id=1, min_confidence=0.85
        )
        assert len(results) == 1
        assert results[0]["task_id"] == 1
        assert results[0]["confidence"] == 0.9


class TestStatisticsAndAnalytics:
    """Test statistics and analytics functionality."""

    def test_get_decision_statistics_empty(self, decision_history):
        """Test statistics when no decisions exist."""
        stats = decision_history.get_decision_statistics()
        assert stats["total_decisions"] == 0
        assert stats["success_rate"] == 0.0
        assert stats["avg_confidence"] == 0.0

    def test_get_decision_statistics_basic(self, decision_history):
        """Test basic decision statistics."""
        # Create decisions with outcomes
        id1 = decision_history.record_decision(
            reasoning="Decision 1", action="Action 1", confidence=0.9
        )
        id2 = decision_history.record_decision(
            reasoning="Decision 2", action="Action 2", confidence=0.8
        )
        id3 = decision_history.record_decision(
            reasoning="Decision 3", action="Action 3", confidence=0.85
        )
        id4 = decision_history.record_decision(
            reasoning="Decision 4", action="Action 4", confidence=0.75
        )

        decision_history.record_outcome(id1, "success", time_elapsed=10.0)
        decision_history.record_outcome(id2, "failure", time_elapsed=15.0)
        decision_history.record_outcome(id3, "success", time_elapsed=20.0)
        decision_history.record_outcome(id4, "failure", time_elapsed=12.0)

        stats = decision_history.get_decision_statistics()

        assert stats["total_decisions"] == 4
        assert stats["successful"] == 2
        assert stats["failed"] == 2
        assert stats["success_rate"] == 50.0
        assert stats["avg_confidence"] == pytest.approx(0.825, rel=1e-2)
        assert stats["avg_time_elapsed_seconds"] == pytest.approx(14.25, rel=1e-2)

    def test_get_decision_statistics_with_filters(self, decision_history):
        """Test statistics with filters."""
        # Create decisions for different tasks
        id1 = decision_history.record_decision(
            reasoning="Decision 1",
            action="Action 1",
            confidence=0.9,
            task_id=1,
        )
        id2 = decision_history.record_decision(
            reasoning="Decision 2",
            action="Action 2",
            confidence=0.8,
            task_id=1,
        )
        id3 = decision_history.record_decision(
            reasoning="Decision 3",
            action="Action 3",
            confidence=0.85,
            task_id=2,
        )

        decision_history.record_outcome(id1, "success")
        decision_history.record_outcome(id2, "success")
        decision_history.record_outcome(id3, "failure")

        # Get stats for task 1
        stats = decision_history.get_decision_statistics(task_id=1)
        assert stats["total_decisions"] == 2
        assert stats["success_rate"] == 100.0


class TestExport:
    """Test export functionality."""

    def test_export_decisions_json(self, decision_history):
        """Test exporting decisions as JSON."""
        decision_id = decision_history.record_decision(
            reasoning="Test decision",
            action="Test action",
            confidence=0.9,
            alternatives=[
                {"action": "Alternative 1", "reason_for_rejection": "Not good"}
            ],
        )

        result = decision_history.export_decisions(format="json")
        assert isinstance(result, str)

        # Parse and verify
        data = json.loads(result)
        assert "decisions" in data
        assert "exported_at" in data
        assert "total_count" in data
        assert data["total_count"] == 1
        assert len(data["decisions"]) == 1

    def test_export_decisions_dict(self, decision_history):
        """Test exporting decisions as dictionary."""
        decision_history.record_decision(
            reasoning="Test decision",
            action="Test action",
            confidence=0.9,
        )

        result = decision_history.export_decisions(format="dict")
        assert isinstance(result, dict)
        assert "decisions" in result
        assert "exported_at" in result

    def test_export_decisions_with_graph(self, decision_history):
        """Test exporting decisions with decision graph."""
        decision_id = decision_history.record_decision(
            reasoning="Test decision",
            action="Test action",
            confidence=0.9,
        )

        result = decision_history.export_decisions(format="dict", include_graph=True)
        assert "decisions" in result
        assert "graph" in result["decisions"][0]
        assert "nodes" in result["decisions"][0]["graph"]
        assert "edges" in result["decisions"][0]["graph"]

    def test_export_decisions_with_filters(self, decision_history):
        """Test exporting decisions with filters."""
        decision_history.record_decision(
            reasoning="Decision 1",
            action="Action 1",
            confidence=0.9,
            task_id=1,
        )
        decision_history.record_decision(
            reasoning="Decision 2",
            action="Action 2",
            confidence=0.8,
            task_id=2,
        )

        result = decision_history.export_decisions(format="dict", task_id=1)
        assert result["total_count"] == 1
        assert result["decisions"][0]["task_id"] == 1


class TestCleanup:
    """Test cleanup functionality."""

    def test_delete_old_decisions(self, decision_history):
        """Test deleting old decisions."""
        # Create a decision
        decision_id = decision_history.record_decision(
            reasoning="Test decision",
            action="Test action",
            confidence=0.9,
        )

        # Verify decision exists
        decision = decision_history.get_decision(decision_id)
        assert decision is not None

        # Delete decisions older than 0 days (all decisions)
        count = decision_history.delete_old_decisions(days=0)
        assert count == 1

        # Verify decision is deleted
        decision = decision_history.get_decision(decision_id)
        assert decision is None


class TestThreadSafety:
    """Test thread safety of DecisionHistoryManager."""

    def test_concurrent_record_decisions(self, decision_history):
        """Test recording decisions from multiple threads."""
        import threading

        results = []
        errors = []

        def record_decision(idx):
            try:
                decision_id = decision_history.record_decision(
                    reasoning=f"Thread decision {idx}",
                    action=f"Action {idx}",
                    confidence=0.9,
                )
                results.append(decision_id)
            except Exception as e:
                errors.append(e)

        # Create 10 threads
        threads = [
            threading.Thread(target=record_decision, args=(i,))
            for i in range(10)
        ]

        # Start all threads
        for t in threads:
            t.start()

        # Wait for all threads to complete
        for t in threads:
            t.join()

        # Verify no errors occurred
        assert len(errors) == 0
        assert len(results) == 10
        assert len(set(results)) == 10  # All IDs are unique


class TestSingleton:
    """Test singleton pattern for global manager."""

    def test_get_decision_history_manager_singleton(self, temp_db_path):
        """Test that get_decision_history_manager returns same instance."""
        # Note: This test uses a custom db_path, but the singleton
        # will use the default path. We'll just test the pattern.

        manager1 = get_decision_history_manager()
        manager2 = get_decision_history_manager()

        # Should be the same instance
        assert manager1 is manager2