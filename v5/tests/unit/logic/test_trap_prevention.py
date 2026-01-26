"""
Unit Tests for TrapPrevention Module (Task 4.6)

Tests for trap prevention system which proactively prevents traps before they occur.
"""

import pytest
from datetime import datetime, timedelta

from v5.logic.trap_prevention import (
    TrapPrevention,
    PreventionLevel,
    PreventionType,
    PreventionAction,
    TrapPattern,
    create_trap_prevention
)
from v5.logic.trap_detector import TrapType


class TestTrapPreventionInitialization:
    """Test TrapPrevention initialization."""
    
    def test_initialization_with_defaults(self):
        """Test initialization with default parameters."""
        prevention = TrapPrevention()
        
        assert prevention.max_history_size == 100
        assert prevention.progress_minimal_threshold == 0.1
        assert prevention.progress_expected_threshold == 0.3
        assert prevention.max_scope_expansions == 3
        assert prevention.learning_enabled is True
        assert len(prevention.action_history) == 0
        assert len(prevention.decision_history) == 0
        assert len(prevention.progress_history) == 0
        assert len(prevention.trap_patterns) == 0
    
    def test_initialization_with_custom_params(self):
        """Test initialization with custom parameters."""
        prevention = TrapPrevention(
            max_history_size=50,
            progress_minimal_threshold=0.2,
            progress_expected_threshold=0.4,
            max_scope_expansions=5,
            learning_enabled=False
        )
        
        assert prevention.max_history_size == 50
        assert prevention.progress_minimal_threshold == 0.2
        assert prevention.progress_expected_threshold == 0.4
        assert prevention.max_scope_expansions == 5
        assert prevention.learning_enabled is False
    
    def test_factory_function(self):
        """Test factory function for creating TrapPrevention."""
        prevention = create_trap_prevention()
        
        assert isinstance(prevention, TrapPrevention)
        assert prevention.learning_enabled is True


class TestActionHistoryTracking:
    """Test action history tracking for loop prevention."""
    
    def test_track_action(self):
        """Test tracking an action."""
        prevention = TrapPrevention()
        
        prevention.track_action("write test file")
        
        assert len(prevention.action_history) == 1
        assert prevention.action_history[0]["action"] == "write test file"
        assert "timestamp" in prevention.action_history[0]
    
    def test_track_action_with_metadata(self):
        """Test tracking an action with metadata."""
        prevention = TrapPrevention()
        
        metadata = {"file": "test.py", "lines": 10}
        prevention.track_action("write test file", metadata)
        
        assert prevention.action_history[0]["metadata"] == metadata
    
    def test_action_fingerprint(self):
        """Test action fingerprint calculation."""
        prevention = TrapPrevention()
        
        # Similar actions should have same fingerprint
        fingerprint1 = prevention._calculate_action_fingerprint("add import 2024-01-01")
        fingerprint2 = prevention._calculate_action_fingerprint("add import 2024-01-02")
        
        assert fingerprint1 == fingerprint2  # Dates normalized
    
    def test_check_action_repetition_no_repetition(self):
        """Test checking action repetition when no repetition."""
        prevention = TrapPrevention()
        
        result = prevention.check_action_repetition("new action")
        
        assert result is None
    
    def test_check_action_repetition_warning(self):
        """Test checking action repetition with warning level."""
        prevention = TrapPrevention()
        
        # Track same action 3 times
        for _ in range(3):
            prevention.track_action("add import statement")
        
        result = prevention.check_action_repetition("add import statement")
        
        assert result is not None
        assert result.prevention_type == PreventionType.ACTION_REPETITION
        assert result.level == PreventionLevel.WARNING
        assert result.blocked is False
        assert "3 times" in result.message
    
    def test_check_action_repetition_blocking(self):
        """Test checking action repetition with blocking level."""
        prevention = TrapPrevention()
        
        # Track same action 5 times
        for _ in range(5):
            prevention.track_action("add import statement")
        
        result = prevention.check_action_repetition("add import statement")
        
        assert result is not None
        assert result.level == PreventionLevel.BLOCKING
        assert result.blocked is True
    
    def test_fingerprint_cleanup(self):
        """Test cleanup of old fingerprints."""
        prevention = TrapPrevention()
        
        # Manually add fingerprints with timestamps
        old_time = datetime.now() - timedelta(hours=25)
        new_time = datetime.now()
        
        fingerprint = prevention._calculate_action_fingerprint("action1")
        prevention.action_fingerprints[fingerprint] = [old_time, new_time]
        
        # Cleanup
        prevention._cleanup_old_fingerprints(max_age_hours=24)
        
        # Only new fingerprint should remain
        assert len(prevention.action_fingerprints[fingerprint]) == 1
        assert prevention.action_fingerprints[fingerprint][0] == new_time


class TestProgressValidation:
    """Test progress validation for dead end prevention."""
    
    def test_track_progress(self):
        """Test tracking progress."""
        prevention = TrapPrevention()
        
        prevention.track_progress(0.5)
        
        assert len(prevention.progress_history) == 1
        assert prevention.progress_history[0]["progress"] == 0.5
    
    def test_track_significant_progress(self):
        """Test that significant progress updates timestamp."""
        prevention = TrapPrevention()
        
        prevention.track_progress(0.4)  # Above expected threshold
        
        assert prevention.last_significant_progress is not None
    
    def test_track_no_significant_progress(self):
        """Test that low progress doesn't update significant timestamp."""
        prevention = TrapPrevention()
        
        prevention.track_progress(0.05)  # Below expected threshold
        
        assert prevention.last_significant_progress is None
    
    def test_check_progress_validation_adequate(self):
        """Test progress validation with adequate progress."""
        prevention = TrapPrevention()
        
        result = prevention.check_progress_validation(0.5)
        
        assert result is None
    
    def test_check_progress_validation_insufficient(self):
        """Test progress validation with insufficient progress."""
        prevention = TrapPrevention()
        
        # Track low progress for 5 operations
        for _ in range(5):
            prevention.track_progress(0.05)
        
        result = prevention.check_progress_validation(0.05)
        
        assert result is not None
        assert result.prevention_type == PreventionType.PROGRESS_VALIDATION
        assert result.level == PreventionLevel.BLOCKING
        assert "below minimal threshold" in result.message
    
    def test_check_progress_stagnation(self):
        """Test progress stagnation detection."""
        prevention = TrapPrevention()
        
        # Set significant progress to 20 minutes ago
        old_time = datetime.now() - timedelta(minutes=20)
        prevention.last_significant_progress = old_time
        
        result = prevention.check_progress_stagnation(stagnation_threshold_minutes=15)
        
        assert result is not None
        assert result.prevention_type == PreventionType.PROGRESS_VALIDATION
        assert result.level == PreventionLevel.WARNING
        assert "No significant progress" in result.message
    
    def test_check_progress_stagnation_blocking(self):
        """Test progress stagnation with blocking level."""
        prevention = TrapPrevention()
        
        # Set significant progress to 40 minutes ago
        old_time = datetime.now() - timedelta(minutes=40)
        prevention.last_significant_progress = old_time
        
        result = prevention.check_progress_stagnation(stagnation_threshold_minutes=15)
        
        assert result is not None
        assert result.level == PreventionLevel.BLOCKING
        assert result.blocked is True


class TestDecisionHistory:
    """Test decision history for circular reasoning prevention."""
    
    def test_track_decision(self):
        """Test tracking a decision."""
        prevention = TrapPrevention()
        
        prevention.track_decision(
            decision="use aggressive strategy",
            reasoning={"risk": "high", "speed": "fast"},
            alternatives=["conservative", "balanced"]
        )
        
        assert len(prevention.decision_history) == 1
        assert prevention.decision_history[0]["decision"] == "use aggressive strategy"
        assert prevention.decision_history[0]["reasoning"] == {"risk": "high", "speed": "fast"}
        assert prevention.decision_history[0]["alternatives"] == ["conservative", "balanced"]
    
    def test_track_decision_with_dependencies(self):
        """Test tracking decision with dependencies."""
        prevention = TrapPrevention()
        
        prevention.track_decision(
            decision="task B",
            depends_on=["task A"]
        )
        
        assert "task A" in prevention.decision_dependencies[
            prevention._calculate_decision_fingerprint("task B")
        ]
    
    def test_track_rejected_options(self):
        """Test that rejected alternatives are tracked."""
        prevention = TrapPrevention()
        
        prevention.track_decision(
            decision="choice B",
            alternatives=["choice A", "choice C"]
        )
        
        # Both alternatives should be tracked as rejected
        assert len(prevention.rejected_options) > 0
    
    def test_check_decision_cycle_no_cycle(self):
        """Test decision cycle check with no cycle."""
        prevention = TrapPrevention()
        
        result = prevention.check_decision_cycle(
            decision="new decision",
            depends_on=["decision A"]
        )
        
        assert result is None
    
    def test_check_decision_cycle_with_cycle(self):
        """Test decision cycle check that detects cycle."""
        prevention = TrapPrevention()
        
        # Create a cycle: A -> B, B -> A
        prevention.track_decision(decision="A", depends_on=[])
        fingerprint_a = prevention._calculate_decision_fingerprint("A")
        prevention.track_decision(decision="B", depends_on=[fingerprint_a])
        
        result = prevention.check_decision_cycle(
            decision="A",
            depends_on=[prevention._calculate_decision_fingerprint("B")]
        )
        
        assert result is not None
        assert result.prevention_type == PreventionType.DECISION_CYCLE
        assert result.level == PreventionLevel.BLOCKING
        assert result.blocked is True
    
    def test_check_revisiting_rejected(self):
        """Test checking for revisiting rejected options."""
        prevention = TrapPrevention()
        
        # Track a decision with rejected alternative
        prevention.track_decision(
            decision="choice B",
            alternatives=["choice A"]
        )
        
        # Try to make rejected choice
        result = prevention.check_revisiting_rejected("choice A")
        
        assert result is not None
        assert result.prevention_type == PreventionType.DECISION_CYCLE
        assert result.level == PreventionLevel.WARNING
        assert "rejected" in result.message.lower()
    
    def test_would_create_cycle(self):
        """Test cycle detection in dependency graph."""
        prevention = TrapPrevention()
        
        # Create dependencies: A -> B -> C
        prevention.decision_dependencies = {
            "A": set(),
            "B": {"A"},
            "C": {"B"}
        }
        
        # Check if adding C -> A would create cycle
        # Since B depends on A, and C depends on B, A is reachable from C
        # So adding C -> A would create cycle: A -> B -> C -> A
        would_cycle = prevention._would_create_cycle("C", "A")
        
        assert would_cycle is True
        
        # Check if adding C -> D would create cycle
        would_cycle = prevention._would_create_cycle("C", "D")
        
        assert would_cycle is False


class TestScopeFreeze:
    """Test scope freeze mechanism for scope creep prevention."""
    
    def test_initialize_scope(self):
        """Test initializing task scope."""
        prevention = TrapPrevention()
        
        scope = {"feature": "authentication", "files": 5}
        prevention.initialize_scope(scope)
        
        assert prevention.initial_scope == scope
        assert prevention.current_scope == scope
        assert prevention.scope_expansion_count == 0
    
    def test_check_scope_expansion_no_change(self):
        """Test scope check with no expansion."""
        prevention = TrapPrevention()
        
        scope = {"feature": "auth", "files": 5}
        prevention.initialize_scope(scope)
        
        result = prevention.check_scope_expansion(scope)
        
        assert result is None
    
    def test_check_scope_expansion_detected(self):
        """Test scope check that detects expansion."""
        prevention = TrapPrevention()
        
        initial_scope = {"feature": "auth", "files": 5}
        prevention.initialize_scope(initial_scope)
        
        # First expansion returns INFO level by default
        expanded_scope = {"feature": "auth", "files": 10}  # Added more files
        result = prevention.check_scope_expansion(expanded_scope)
        
        assert result is not None
        assert result.prevention_type == PreventionType.SCOPE_CREEP
        assert result.level == PreventionLevel.INFO
        assert result.blocked is False
        assert "expanded" in result.message.lower()
    
    def test_check_scope_expansion_with_approval(self):
        """Test scope check with require_approval flag."""
        prevention = TrapPrevention()
        
        initial_scope = {"feature": "auth", "files": 5}
        prevention.initialize_scope(initial_scope)
        
        # With require_approval=True, should be WARNING
        expanded_scope = {"feature": "auth", "files": 10}
        result = prevention.check_scope_expansion(expanded_scope, require_approval=True)
        
        assert result is not None
        assert result.level == PreventionLevel.WARNING
    
    def test_check_scope_expansion_blocking(self):
        """Test scope check that blocks excessive expansion."""
        prevention = TrapPrevention(max_scope_expansions=2)
        
        prevention.initialize_scope({"feature": "auth", "files": 5})
        
        # Expand twice
        prevention.check_scope_expansion({"feature": "auth", "files": 7})
        prevention.check_scope_expansion({"feature": "auth", "files": 8})
        
        # Third expansion should be blocked
        result = prevention.check_scope_expansion({"feature": "auth", "files": 10})
        
        assert result is not None
        assert result.level == PreventionLevel.BLOCKING
        assert result.blocked is True
    
    def test_detect_scope_changes_new_key(self):
        """Test detecting new scope keys."""
        prevention = TrapPrevention()
        
        old_scope = {"feature": "auth"}
        new_scope = {"feature": "auth", "files": 5}
        
        changes = prevention._detect_scope_changes(old_scope, new_scope)
        
        assert len(changes) == 1
        assert "Added requirement: files" in changes[0]
    
    def test_detect_scope_changes_value_increase(self):
        """Test detecting value increases."""
        prevention = TrapPrevention()
        
        old_scope = {"files": 5}
        new_scope = {"files": 10}  # 100% increase
        
        changes = prevention._detect_scope_changes(old_scope, new_scope)
        
        assert len(changes) == 1
        assert "Increased requirement: files" in changes[0]


class TestHighRiskActionWarning:
    """Test high-risk action warning system."""
    
    def test_check_high_risk_no_risk(self):
        """Test high-risk check with no risk factors."""
        prevention = TrapPrevention()
        
        result = prevention.check_high_risk_action("normal action")
        
        assert result is None
    
    def test_check_high_risk_destructive(self):
        """Test high-risk check for destructive action."""
        prevention = TrapPrevention()
        
        risk_factors = {"destructive": True}
        result = prevention.check_high_risk_action("delete database", risk_factors)
        
        assert result is not None
        assert result.prevention_type == PreventionType.HIGH_RISK_ACTION
        assert result.level == PreventionLevel.WARNING
        assert "Destructive operation" in result.suggestion
    
    def test_check_high_risk_multiple_factors(self):
        """Test high-risk check with multiple risk factors."""
        prevention = TrapPrevention()
        
        risk_factors = {
            "destructive": True,
            "irreversible": True,
            "external_resource": True
        }
        result = prevention.check_high_risk_action("delete remote database", risk_factors)
        
        assert result is not None
        assert "Destructive" in result.suggestion
        assert "Irreversible" in result.suggestion
        assert "External resource" in result.suggestion
    
    def test_check_high_risk_blocking(self):
        """Test high-risk check that blocks action."""
        prevention = TrapPrevention()
        
        risk_factors = {
            "destructive": True,
            "irreversible": True,
            "external_resource": True,
            "large_scale": True,
            "complexity": 8
        }
        result = prevention.check_high_risk_action("dangerous operation", risk_factors)
        
        assert result is not None
        assert result.level == PreventionLevel.BLOCKING
        assert result.blocked is True


class TestLearningFromTraps:
    """Test learning from past trap occurrences."""
    
    def test_record_trap_occurrence_new_pattern(self):
        """Test recording a new trap occurrence."""
        prevention = TrapPrevention()
        
        prevention.record_trap_occurrence(
            trap_type=TrapType.INFINITE_LOOP,
            task_type="implementation",
            context={"action_type": "write_file", "error_type": "file_locked"}
        )
        
        assert len(prevention.trap_patterns) == 1
        assert prevention.task_trap_stats["implementation"][TrapType.INFINITE_LOOP] == 1
    
    def test_record_trap_occurrence_existing_pattern(self):
        """Test recording occurrence of existing pattern."""
        prevention = TrapPrevention()
        
        context = {"action_type": "write_file"}
        
        # Record first occurrence
        prevention.record_trap_occurrence(
            trap_type=TrapType.INFINITE_LOOP,
            task_type="implementation",
            context=context
        )
        
        # Record second occurrence
        prevention.record_trap_occurrence(
            trap_type=TrapType.INFINITE_LOOP,
            task_type="implementation",
            context=context
        )
        
        # Should have same pattern with higher count and confidence
        assert len(prevention.trap_patterns) == 1
        pattern = list(prevention.trap_patterns.values())[0]
        assert pattern.occurrence_count == 2
        assert pattern.confidence > 0.5  # Should have increased
    
    def test_check_pattern_match_no_match(self):
        """Test pattern check with no match."""
        prevention = TrapPrevention()
        
        result = prevention.check_pattern_match(
            task_type="implementation",
            current_context={"action_type": "read_file"}
        )
        
        assert result is None
    
    def test_check_pattern_match_with_multiple_occurrences(self):
        """Test pattern check that finds match after multiple occurrences."""
        prevention = TrapPrevention()
        
        context = {"action_type": "write_file"}
        
        # Record trap occurrence 3 times to increase confidence
        for _ in range(3):
            prevention.record_trap_occurrence(
                trap_type=TrapType.INFINITE_LOOP,
                task_type="implementation",
                context=context
            )
        
        # Check same context (should match with higher confidence)
        result = prevention.check_pattern_match(
            task_type="implementation",
            current_context=context
        )
        
        assert result is not None
        assert result.prevention_type == PreventionType.PATTERN_DETECTED
        assert "known trap pattern" in result.message.lower()
    
    def test_learning_disabled(self):
        """Test that learning can be disabled."""
        prevention = TrapPrevention(learning_enabled=False)
        
        # Record trap occurrence
        prevention.record_trap_occurrence(
            trap_type=TrapType.INFINITE_LOOP,
            task_type="implementation",
            context={"action_type": "write_file"}
        )
        
        # Pattern check should not work when learning disabled
        result = prevention.check_pattern_match(
            task_type="implementation",
            current_context={"action_type": "write_file"}
        )
        
        assert result is None
    
    def test_extract_context_features(self):
        """Test context feature extraction."""
        prevention = TrapPrevention()
        
        context = {
            "task_type": "implementation",
            "action_type": "write_file",
            "error_type": "file_locked",
            "custom_value": 42
        }
        
        features = prevention._extract_context_features(context)
        
        assert features["task_type"] == "implementation"
        assert features["action_type"] == "write_file"
        assert features["custom_value"] == 42


class TestWarningSystem:
    """Test warning system for prevention actions."""
    
    def test_add_warning_callback(self):
        """Test adding warning callback."""
        prevention = TrapPrevention()
        
        callback = lambda action: None
        prevention.add_warning_callback(callback)
        
        assert len(prevention.warning_callbacks) == 1
    
    def test_trigger_prevention_action(self):
        """Test triggering prevention action."""
        prevention = TrapPrevention()
        
        callback_called = []
        
        def callback(action):
            callback_called.append(action)
        
        prevention.add_warning_callback(callback)
        
        action = PreventionAction(
            prevention_type=PreventionType.HIGH_RISK_ACTION,
            level=PreventionLevel.WARNING,
            message="Test warning",
            suggestion="Test suggestion"
        )
        
        prevention.trigger_prevention_action(action)
        
        assert len(callback_called) == 1
        assert callback_called[0] == action
    
    def test_trigger_prevention_action_with_exception(self):
        """Test triggering action handles callback exceptions."""
        prevention = TrapPrevention()
        
        def bad_callback(action):
            raise Exception("Test exception")
        
        prevention.add_warning_callback(bad_callback)
        
        action = PreventionAction(
            prevention_type=PreventionType.HIGH_RISK_ACTION,
            level=PreventionLevel.WARNING,
            message="Test",
            suggestion="Test"
        )
        
        # Should not raise exception
        prevention.trigger_prevention_action(action)


class TestUtilityMethods:
    """Test utility methods."""
    
    def test_get_statistics(self):
        """Test getting statistics."""
        prevention = TrapPrevention()
        
        prevention.track_action("action1")
        prevention.track_progress(0.5)
        prevention.initialize_scope({"files": 5})
        
        stats = prevention.get_statistics()
        
        assert stats["action_history_size"] == 1
        assert stats["progress_history_size"] == 1
        assert stats["scope_expansion_count"] == 0
    
    def test_reset(self):
        """Test resetting prevention system."""
        prevention = TrapPrevention()
        
        # Add some data
        prevention.track_action("action1")
        prevention.track_progress(0.5)
        prevention.initialize_scope({"files": 5})
        
        # Reset
        prevention.reset()
        
        assert len(prevention.action_history) == 0
        assert len(prevention.progress_history) == 0
        assert prevention.current_scope is None
        assert len(prevention.trap_patterns) == 0


class TestPreventionAction:
    """Test PreventionAction dataclass."""
    
    def test_prevention_action_creation(self):
        """Test creating a prevention action."""
        action = PreventionAction(
            prevention_type=PreventionType.ACTION_REPETITION,
            level=PreventionLevel.WARNING,
            message="Test message",
            suggestion="Test suggestion"
        )
        
        assert action.prevention_type == PreventionType.ACTION_REPETITION
        assert action.level == PreventionLevel.WARNING
        assert action.message == "Test message"
        assert action.suggestion == "Test suggestion"
        assert action.blocked is False
    
    def test_prevention_action_blocked(self):
        """Test creating a blocked prevention action."""
        action = PreventionAction(
            prevention_type=PreventionType.HIGH_RISK_ACTION,
            level=PreventionLevel.BLOCKING,
            message="Test",
            suggestion="Test",
            blocked=True
        )
        
        assert action.blocked is True
    
    def test_prevention_action_repr(self):
        """Test PreventionAction string representation."""
        action = PreventionAction(
            prevention_type=PreventionType.ACTION_REPETITION,
            level=PreventionLevel.WARNING,
            message="Test",
            suggestion="Test",
            blocked=False
        )
        
        repr_str = repr(action)
        assert "ACTION_REPETITION" in repr_str
        assert "WARNING" in repr_str
        assert "ALLOWED" in repr_str


class TestTrapPattern:
    """Test TrapPattern dataclass."""
    
    def test_trap_pattern_creation(self):
        """Test creating a trap pattern."""
        pattern = TrapPattern(
            pattern_id="test_id",
            trap_type=TrapType.INFINITE_LOOP,
            task_type="implementation",
            pattern_signature="sig123",
            occurrence_count=3,
            confidence=0.8
        )
        
        assert pattern.pattern_id == "test_id"
        assert pattern.trap_type == TrapType.INFINITE_LOOP
        assert pattern.occurrence_count == 3
        assert pattern.confidence == 0.8
    
    def test_trap_pattern_repr(self):
        """Test TrapPattern string representation."""
        pattern = TrapPattern(
            pattern_id="test_id",
            trap_type=TrapType.INFINITE_LOOP,
            task_type="test",
            pattern_signature="sig"
        )
        
        repr_str = repr(pattern)
        assert "infinite_loop" in repr_str  # Lowercase enum value
        assert "count=" in repr_str
        assert "conf=" in repr_str


class TestIntegration:
    """Integration tests for trap prevention."""
    
    def test_full_prevention_workflow(self):
        """Test complete prevention workflow."""
        prevention = TrapPrevention()
        
        # Initialize scope
        scope = {"feature": "auth", "files": 5}
        prevention.initialize_scope(scope)
        
        # Track some progress
        prevention.track_progress(0.3)
        
        # Track some actions
        for _ in range(2):
            prevention.track_action("add test")
        
        # Check for action repetition (should not trigger yet)
        result = prevention.check_action_repetition("add test")
        assert result is None
        
        # Add third action (should trigger warning)
        prevention.track_action("add test")
        result = prevention.check_action_repetition("add test")
        assert result is not None
        assert result.level == PreventionLevel.WARNING
    
    def test_multiple_prevention_checks(self):
        """Test running multiple prevention checks."""
        prevention = TrapPrevention()
        
        # Track actions with low progress
        for _ in range(3):  # Only 3 times for warning level
            prevention.track_action("same action")
            prevention.track_progress(0.05)
        
        # Check action repetition (should be WARNING with 3 repetitions)
        action_result = prevention.check_action_repetition("same action")
        assert action_result is not None
        assert action_result.level == PreventionLevel.WARNING
        
        # Check progress validation (5 low progress operations = BLOCKING)
        progress_result = prevention.check_progress_validation(0.05)
        assert progress_result is not None
        assert progress_result.level == PreventionLevel.BLOCKING
    
    def test_learning_integration(self):
        """Test learning integration with prevention."""
        prevention = TrapPrevention()
        
        # Record trap occurrence 3 times for sufficient confidence
        context = {"action_type": "write_file", "complexity": 8}
        for _ in range(3):
            prevention.record_trap_occurrence(
                trap_type=TrapType.INFINITE_LOOP,
                task_type="implementation",
                context=context
            )
        
        # Later, check for pattern match
        result = prevention.check_pattern_match(
            task_type="implementation",
            current_context=context
        )
        
        assert result is not None
        assert result.prevention_type == PreventionType.PATTERN_DETECTED


if __name__ == "__main__":
    pytest.main([__file__, "-v"])