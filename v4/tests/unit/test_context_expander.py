"""
Unit tests for ContextExpander - V4 Adaptive Reasoning System

Tests cover:
- Context expansion with adaptive reasoning
- Sufficiency checking for different task types
- Learning and optimization of optimal levels
- Integration with ContextHierarchyManager
- Edge cases and error handling
"""

import pytest
import time
import tempfile
import os
from unittest.mock import Mock, MagicMock, patch

from v3.logic.context_expander import (
    ContextExpander,
    TaskType,
    ContextSufficiencyResult,
    ExpansionDecision
)
from v3.data.context_hierarchy import ContextHierarchyManager, ContextLevel


@pytest.fixture
def temp_db_path():
    """Create temporary database path."""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    yield path
    try:
        os.unlink(path)
    except:
        pass


@pytest.fixture
def context_manager(temp_db_path):
    """Create ContextHierarchyManager instance."""
    manager = ContextHierarchyManager(db_path=temp_db_path)
    
    # Add some sample context items
    manager.add_context_item(
        level=ContextLevel.L0,
        item_type='action',
        content={
            'action': 'test_action',
            'state': 'running'
        }
    )
    
    manager.add_context_item(
        level=ContextLevel.L1,
        item_type='action',
        content={
            'action': 'recent_action_1',
            'state': 'completed'
        }
    )
    
    manager.add_context_item(
        level=ContextLevel.L1,
        item_type='error',
        content={
            'error': 'test_error',
            'message': 'Test error message'
        }
    )
    
    yield manager


@pytest.fixture
def mock_telemetry_manager():
    """Create mock telemetry manager."""
    manager = Mock()
    manager.record_event = Mock()
    return manager


@pytest.fixture
def context_expander(context_manager, mock_telemetry_manager):
    """Create ContextExpander instance."""
    return ContextExpander(
        context_manager=context_manager,
        telemetry_manager=mock_telemetry_manager,
        learning_rate=0.1
    )


class TestTaskTypeResolution:
    """Test task type resolution and aliases."""
    
    def test_resolve_task_type_enum(self, context_expander):
        """Test resolving valid task type enum."""
        result = context_expander._resolve_task_type("implementation")
        assert result == TaskType.IMPLEMENTATION
    
    def test_resolve_task_type_alias(self, context_expander):
        """Test resolving task type alias."""
        result = context_expander._resolve_task_type("implementor")
        assert result == TaskType.IMPLEMENTATION
        
        result = context_expander._resolve_task_type("planner")
        assert result == TaskType.PLANNING
        
        result = context_expander._resolve_task_type("verifier")
        assert result == TaskType.VERIFICATION
    
    def test_resolve_task_type_unknown(self, context_expander):
        """Test resolving unknown task type defaults to IMPLEMENTATION."""
        result = context_expander._resolve_task_type("unknown_task")
        assert result == TaskType.IMPLEMENTATION
    
    def test_resolve_task_type_case_insensitive(self, context_expander):
        """Test case-insensitive alias resolution."""
        result = context_expander._resolve_task_type("IMPLEMENTOR")
        assert result == TaskType.IMPLEMENTATION
        
        result = context_expander._resolve_task_type("Planner")
        assert result == TaskType.PLANNING


class TestContextRetrieval:
    """Test context retrieval at different levels."""
    
    def test_get_l0_context(self, context_expander):
        """Test retrieving L0 context."""
        ctx = context_expander._get_context_at_level(ContextLevel.L0)
        
        assert ctx['level'] == ContextLevel.L0
        assert 'current_action' in ctx
        assert 'timestamp' in ctx
    
    def test_get_l1_context(self, context_expander):
        """Test retrieving L1 context."""
        ctx = context_expander._get_context_at_level(ContextLevel.L1)
        
        assert ctx['level'] == ContextLevel.L1
        assert 'current_action' in ctx
        assert 'recent_actions' in ctx
        assert 'timestamp' in ctx
    
    def test_get_l2_context(self, context_expander):
        """Test retrieving L2 context."""
        ctx = context_expander._get_context_at_level(ContextLevel.L2)
        
        assert ctx['level'] == ContextLevel.L2
        assert 'actions' in ctx
        assert 'errors' in ctx
    
    def test_get_l3_context(self, context_expander):
        """Test retrieving L3 context."""
        ctx = context_expander._get_context_at_level(ContextLevel.L3)
        
        assert ctx['level'] == ContextLevel.L3
        assert 'state' in ctx
        assert 'architecture' in ctx
        assert 'patterns' in ctx
    
    def test_get_unknown_level(self, context_expander):
        """Test retrieving unknown context level."""
        ctx = context_expander._get_context_at_level("L99")
        
        assert ctx['level'] == "L99"
        assert 'timestamp' in ctx


class TestContextSufficiency:
    """Test context sufficiency checking."""
    
    def test_l0_sufficient_for_implementation(self, context_expander):
        """Test L0 is sufficient for implementation task."""
        ctx = {
            'level': ContextLevel.L0,
            'current_action': {'action': 'test'},
            'current_state': 'running'
        }
        
        is_sufficient = context_expander._is_context_sufficient(
            ctx, TaskType.IMPLEMENTATION, ContextLevel.L0
        )
        
        assert is_sufficient is True
    
    def test_l0_insufficient_for_implementation_no_action(self, context_expander):
        """Test L0 insufficient for implementation without current_action."""
        ctx = {
            'level': ContextLevel.L0,
            'current_state': 'running'
        }
        
        is_sufficient = context_expander._is_context_sufficient(
            ctx, TaskType.IMPLEMENTATION, ContextLevel.L0
        )
        
        assert is_sufficient is False
    
    def test_l0_insufficient_for_task_breakdown(self, context_expander):
        """Test L0 is insufficient for task breakdown."""
        ctx = {
            'level': ContextLevel.L0,
            'current_action': {'action': 'test'},
            'current_state': 'running'
        }
        
        is_sufficient = context_expander._is_context_sufficient(
            ctx, TaskType.TASK_BREAKDOWN, ContextLevel.L0
        )
        
        assert is_sufficient is False
    
    def test_l1_sufficient_for_task_breakdown(self, context_expander):
        """Test L1 is sufficient for task breakdown."""
        ctx = {
            'level': ContextLevel.L1,
            'current_action': {'action': 'test'},
            'recent_actions': [{'action': 'action1'}, {'action': 'action2'}],
            'recent_errors': []
        }
        
        is_sufficient = context_expander._is_context_sufficient(
            ctx, TaskType.TASK_BREAKDOWN, ContextLevel.L1
        )
        
        assert is_sufficient is True
    
    def test_l1_insufficient_for_verification(self, context_expander):
        """Test L1 is insufficient for verification with few actions."""
        ctx = {
            'level': ContextLevel.L1,
            'current_action': {'action': 'test'},
            'recent_actions': [{'action': 'action1'}],
            'recent_errors': []
        }
        
        is_sufficient = context_expander._is_context_sufficient(
            ctx, TaskType.VERIFICATION, ContextLevel.L0
        )
        
        assert is_sufficient is False
    
    def test_l2_sufficient_for_error_recovery(self, context_expander):
        """Test L2 is sufficient for error recovery."""
        ctx = {
            'level': ContextLevel.L2,
            'actions': [{'action': 'action1'}, {'action': 'action2'}],
            'errors': [{'error': 'error1'}],
            'task_progress': {'completed': 5, 'total': 10}
        }
        
        is_sufficient = context_expander._is_context_sufficient(
            ctx, TaskType.ERROR_RECOVERY, ContextLevel.L2
        )
        
        assert is_sufficient is True


class TestInsufficiencyReasons:
    """Test generation of insufficiency reasons."""
    
    def test_missing_required_elements(self, context_expander):
        """Test reasons for missing required elements."""
        ctx = {
            'level': ContextLevel.L0,
            'current_state': 'running'
        }
        
        reasons = context_expander._get_insufficiency_reasons(
            ctx, TaskType.IMPLEMENTATION, ContextLevel.L0
        )
        
        assert any('Missing required element' in r for r in reasons)
        assert 'current_action' in reasons[0]
    
    def test_task_breakdown_needs_recent_actions(self, context_expander):
        """Test reasons for task breakdown at L0."""
        ctx = {
            'level': ContextLevel.L0,
            'current_action': {'action': 'test'},
            'current_state': 'running'
        }
        
        reasons = context_expander._get_insufficiency_reasons(
            ctx, TaskType.TASK_BREAKDOWN, ContextLevel.L0
        )
        
        assert any('Task breakdown needs recent actions' in r for r in reasons)
    
    def test_verification_needs_more_context(self, context_expander):
        """Test reasons for verification at L0."""
        ctx = {
            'level': ContextLevel.L0,
            'current_action': {'action': 'test'},
            'current_state': 'running'
        }
        
        reasons = context_expander._get_insufficiency_reasons(
            ctx, TaskType.VERIFICATION, ContextLevel.L0
        )
        
        assert any('Verification needs more context' in r for r in reasons)
    
    def test_error_recovery_needs_session_context(self, context_expander):
        """Test reasons for error recovery at L1."""
        ctx = {
            'level': ContextLevel.L1,
            'current_action': {'action': 'test'},
            'recent_actions': [{'action': 'action1'}],
            'recent_errors': []
        }
        
        reasons = context_expander._get_insufficiency_reasons(
            ctx, TaskType.ERROR_RECOVERY, ContextLevel.L1
        )
        
        assert any('Error recovery benefits from session context' in r for r in reasons)


class TestLevelNavigation:
    """Test level navigation methods."""
    
    def test_get_next_level(self, context_expander):
        """Test getting next higher level."""
        assert context_expander._get_next_level(ContextLevel.L0) == ContextLevel.L1
        assert context_expander._get_next_level(ContextLevel.L1) == ContextLevel.L2
        assert context_expander._get_next_level(ContextLevel.L2) == ContextLevel.L3
        assert context_expander._get_next_level(ContextLevel.L3) is None
    
    def test_get_prev_level(self, context_expander):
        """Test getting previous lower level."""
        assert context_expander._get_prev_level(ContextLevel.L1) == ContextLevel.L0
        assert context_expander._get_prev_level(ContextLevel.L2) == ContextLevel.L1
        assert context_expander._get_prev_level(ContextLevel.L3) == ContextLevel.L2
        assert context_expander._get_prev_level(ContextLevel.L0) is None
    
    def test_get_next_level_invalid(self, context_expander):
        """Test getting next level from invalid level."""
        assert context_expander._get_next_level("L99") is None
    
    def test_get_prev_level_invalid(self, context_expander):
        """Test getting prev level from invalid level."""
        assert context_expander._get_prev_level("L99") is None


class TestContextExpansion:
    """Test context expansion logic."""
    
    def test_get_context_sufficient_at_initial_level(self, context_expander):
        """Test getting context when initial level is sufficient."""
        ctx, final_level = context_expander.get_context(
            task_type="implementation"
        )
        
        assert 'level' in ctx
        assert final_level in [ContextLevel.L0, ContextLevel.L1, ContextLevel.L2, ContextLevel.L3]
    
    def test_get_context_with_expansion(self, context_expander):
        """Test getting context with expansion."""
        # Force expansion by starting at L0 for a task that needs more
        with context_expander._lock:
            context_expander._optimal_levels['implementation'] = ContextLevel.L0
        
        ctx, final_level = context_expander.get_context(
            task_type="implementation",
            force_expand=True
        )
        
        assert 'level' in ctx
    
    def test_get_context_max_levels_limit(self, context_expander):
        """Test max_levels parameter limits expansion."""
        ctx, final_level = context_expander.get_context(
            task_type="error_recovery",
            max_levels=2
        )
        
        assert final_level in [ContextLevel.L0, ContextLevel.L1]
    
    def test_get_context_records_in_telemetry(self, context_expander, mock_telemetry_manager):
        """Test that context expansion is recorded in telemetry."""
        context_expander.get_context(task_type="implementation")
        
        # Check that record_event was called
        assert mock_telemetry_manager.record_event.called
        call_args = mock_telemetry_manager.record_event.call_args
        assert call_args[0][0] == "context_expansion"
        assert 'context' in call_args[1]
    
    def test_get_context_handles_telemetry_error(self, context_expander, mock_telemetry_manager):
        """Test that telemetry errors don't break context expansion."""
        mock_telemetry_manager.record_event.side_effect = Exception("Telemetry error")
        
        # Should not raise exception
        ctx, final_level = context_expander.get_context(
            task_type="implementation"
        )
        
        assert ctx is not None
        assert final_level is not None


class TestOptimalLevelLearning:
    """Test learning of optimal context levels."""
    
    def test_get_default_optimal_level(self, context_expander):
        """Test getting default optimal level for task type."""
        level = context_expander.get_optimal_level("implementation")
        assert level == ContextLevel.L0
        
        level = context_expander.get_optimal_level("task_breakdown")
        assert level == ContextLevel.L1
    
    def test_get_success_rate_default(self, context_expander):
        """Test getting default success rate."""
        rate = context_expander.get_success_rate("implementation", ContextLevel.L0)
        assert rate == 0.0
    
    def test_report_outcome_updates_success_rate(self, context_expander):
        """Test reporting outcome updates success rate."""
        # Report successful outcome
        context_expander.report_outcome(
            task_type="implementation",
            context_level=ContextLevel.L0,
            success=True,
            time_elapsed=1.0
        )
        
        rate = context_expander.get_success_rate("implementation", ContextLevel.L0)
        assert rate > 0.0
    
    def test_report_outcome_exponential_moving_average(self, context_expander):
        """Test that success rate uses exponential moving average."""
        # Report several outcomes
        for i in range(10):
            context_expander.report_outcome(
                task_type="implementation",
                context_level=ContextLevel.L0,
                success=i < 7,  # 7 success, 3 failure
                time_elapsed=1.0
            )
        
        rate = context_expander.get_success_rate("implementation", ContextLevel.L0)
        # Should be close to 0.7 but not exactly due to EMA
        assert 0.6 < rate < 0.8
    
    def test_reset_optimal_levels(self, context_expander):
        """Test resetting optimal levels to defaults."""
        # Modify optimal level
        with context_expander._lock:
            context_expander._optimal_levels['implementation'] = ContextLevel.L2
        
        # Reset
        context_expander.reset_optimal_levels()
        
        # Should be back to default
        level = context_expander.get_optimal_level("implementation")
        assert level == ContextLevel.L0


class TestExpansionStatistics:
    """Test expansion statistics and history."""
    
    def test_get_expansion_stats_empty(self, context_expander):
        """Test getting expansion stats when empty."""
        stats = context_expander.get_expansion_stats()
        
        assert stats['total_decisions'] == 0
        assert stats['avg_expansions'] == 0.0
        assert stats['expansion_rate'] == 0.0
    
    def test_get_expansion_stats_with_history(self, context_expander):
        """Test getting expansion stats with history."""
        # Generate some expansion decisions
        for i in range(5):
            context_expander.get_context(task_type="implementation")
        
        stats = context_expander.get_expansion_stats()
        
        assert stats['total_decisions'] == 5
        assert 'expansions' in stats
        assert 'expansion_rate' in stats
        assert 'optimal_levels' in stats
        assert 'recent_decisions' in stats
    
    def test_expansion_history_limit(self, context_expander):
        """Test that expansion history is limited."""
        # Generate more than 1000 decisions
        for i in range(1100):
            context_expander.get_context(task_type="implementation")
        
        # Check that history is limited
        with context_expander._lock:
            assert len(context_expander._expansion_history) <= 1000


class TestIntegrationWithHierarchy:
    """Test integration with ContextHierarchyManager."""
    
    def test_integration_with_hierarchy_manager(self, context_expander, context_manager):
        """Test that expander works with hierarchy manager."""
        # Add context at different levels
        context_manager.add_context_item(
            level=ContextLevel.L2,
            item_type='action',
            content={'action': 'session_action', 'state': 'completed'}
        )
        
        # Get context through expander
        ctx, final_level = context_expander.get_context(
            task_type="planning"
        )
        
        assert ctx is not None
        assert final_level is not None


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_empty_context_manager(self, temp_db_path, mock_telemetry_manager):
        """Test behavior with empty context manager."""
        empty_manager = ContextHierarchyManager(db_path=temp_db_path)
        expander = ContextExpander(
            context_manager=empty_manager,
            telemetry_manager=mock_telemetry_manager
        )
        
        # Should still return context, even if empty
        ctx, final_level = expander.get_context(task_type="implementation")
        
        assert ctx is not None
        assert 'level' in ctx
    
    def test_context_at_highest_level(self, context_expander):
        """Test context expansion at highest level."""
        with context_expander._lock:
            context_expander._optimal_levels['implementation'] = ContextLevel.L3
        
        ctx, final_level = context_expander.get_context(
            task_type="implementation"
        )
        
        # Should stay at L3 (highest level)
        assert final_level == ContextLevel.L3
    
    def test_force_expand_to_all_levels(self, context_expander):
        """Test force expansion through all levels."""
        ctx, final_level = context_expander.get_context(
            task_type="implementation",
            force_expand=True,
            max_levels=4
        )
        
        # Should reach L3 with force_expand
        assert final_level == ContextLevel.L3


class TestConcurrency:
    """Test thread-safety and concurrent operations."""
    
    def test_concurrent_get_context(self, context_expander):
        """Test concurrent context retrieval."""
        import threading
        
        results = []
        errors = []
        
        def get_context_task():
            try:
                ctx, level = context_expander.get_context(task_type="implementation")
                results.append((ctx, level))
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads
        threads = [
            threading.Thread(target=get_context_task)
            for _ in range(10)
        ]
        
        # Start all threads
        for t in threads:
            t.start()
        
        # Wait for completion
        for t in threads:
            t.join()
        
        # Check that all operations completed without errors
        assert len(errors) == 0
        assert len(results) == 10
    
    def test_concurrent_report_outcome(self, context_expander):
        """Test concurrent outcome reporting."""
        import threading
        
        errors = []
        
        def report_task(i):
            try:
                context_expander.report_outcome(
                    task_type="implementation",
                    context_level=ContextLevel.L0,
                    success=i % 2 == 0,
                    time_elapsed=1.0
                )
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads
        threads = [
            threading.Thread(target=report_task, args=(i,))
            for i in range(10)
        ]
        
        # Start all threads
        for t in threads:
            t.start()
        
        # Wait for completion
        for t in threads:
            t.join()
        
        # Check that all operations completed without errors
        assert len(errors) == 0


class TestLearningBehavior:
    """Test learning and adaptive behavior."""
    
    def test_optimal_level_update_threshold(self, context_expander):
        """Test that optimal level updates only after consistent need."""
        # Get context multiple times (will record expansion decisions)
        for _ in range(20):
            context_expander.get_context(task_type="implementation", force_expand=True)
        
        # Check that optimal level hasn't changed (not enough consistency)
        level = context_expander.get_optimal_level("implementation")
        assert level == ContextLevel.L0
    
    def test_learning_rate_affects_updates(self, context_expander):
        """Test that learning rate affects success rate updates."""
        # Create expander with different learning rate
        expander_fast = ContextExpander(
            context_manager=context_expander.context_manager,
            telemetry_manager=None,
            learning_rate=0.5  # Faster learning
        )
        
        # Report outcomes
        expander_fast.report_outcome(
            task_type="implementation",
            context_level=ContextLevel.L0,
            success=True,
            time_elapsed=1.0
        )
        
        # Fast learning should result in higher success rate
        rate_fast = expander_fast.get_success_rate("implementation", ContextLevel.L0)
        
        context_expander.report_outcome(
            task_type="implementation",
            context_level=ContextLevel.L0,
            success=True,
            time_elapsed=1.0
        )
        
        rate_slow = context_expander.get_success_rate("implementation", ContextLevel.L0)
        
        # Faster learning rate should result in higher success rate
        assert rate_fast > rate_slow


class TestTaskTypeSpecificBehavior:
    """Test behavior specific to different task types."""
    
    def test_implementation_starts_at_l0(self, context_expander):
        """Test that implementation task starts at L0."""
        level = context_expander.get_optimal_level("implementation")
        assert level == ContextLevel.L0
    
    def test_task_breakdown_starts_at_l1(self, context_expander):
        """Test that task breakdown starts at L1."""
        level = context_expander.get_optimal_level("task_breakdown")
        assert level == ContextLevel.L1
    
    def test_refactoring_starts_at_l2(self, context_expander):
        """Test that refactoring starts at L2."""
        level = context_expander.get_optimal_level("refactoring")
        assert level == ContextLevel.L2
    
    def test_planning_starts_at_l2(self, context_expander):
        """Test that planning starts at L2."""
        level = context_expander.get_optimal_level("planning")
        assert level == ContextLevel.L2
    
    def test_error_recovery_starts_at_l2(self, context_expander):
        """Test that error recovery starts at L2."""
        level = context_expander.get_optimal_level("error_recovery")
        assert level == ContextLevel.L2


class TestExpansionDecision:
    """Test ExpansionDecision dataclass."""
    
    def test_expansion_decision_creation(self):
        """Test creating expansion decision."""
        decision = ExpansionDecision(
            timestamp=time.time(),
            task_type="implementation",
            initial_level=ContextLevel.L0,
            final_level=ContextLevel.L1,
            reasons=["Insufficient context"],
            success=True,
            time_elapsed=0.5
        )
        
        assert decision.timestamp > 0
        assert decision.task_type == "implementation"
        assert decision.initial_level == ContextLevel.L0
        assert decision.final_level == ContextLevel.L1
        assert decision.success is True
        assert decision.time_elapsed == 0.5