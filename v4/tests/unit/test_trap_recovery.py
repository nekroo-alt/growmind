"""
Unit tests for Trap Recovery System (V4 Task 4.5)

Tests the trap recovery engine including:
- Recovery strategy selection
- Recovery execution for different action types
- Checkpoint-based recovery
- State change recovery
- Strategy change recovery
- Human intervention recovery
- Recovery history tracking
- Recovery statistics
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

from v3.logic.trap_recovery import (
    RecoveryStrategy,
    RecoveryStatus,
    RecoveryAction,
    RecoveryExecution,
    TrapRecoveryEngine,
    create_trap_recovery_engine
)
from v3.logic.trap_detector import (
    TrapType,
    TrapSeverity,
    TrapDetection,
    TrapDetector
)


class TestRecoveryStrategyEnum:
    """Tests for RecoveryStrategy enumeration."""
    
    def test_all_recovery_strategies_defined(self):
        """Test that all recovery strategies are defined."""
        # Loop recovery strategies
        assert RecoveryStrategy.BREAK_LOOP_CHANGE_APPROACH.value == "break_loop_change_approach"
        assert RecoveryStrategy.BACKTRACK_TO_CHECKPOINT.value == "backtrack_to_checkpoint"
        assert RecoveryStrategy.TRY_DIFFERENT_STRATEGY.value == "try_different_strategy"
        
        # Dead end recovery strategies
        assert RecoveryStrategy.BACKTRACK_TO_LAST_SUCCESS.value == "backtrack_to_last_success"
        assert RecoveryStrategy.BREAK_TASK_SMALLER.value == "break_task_smaller"
        assert RecoveryStrategy.TRY_ALTERNATIVE_APPROACH.value == "try_alternative_approach"
        assert RecoveryStrategy.ASK_HUMAN_INTERVENTION.value == "ask_human_intervention"
        
        # Circular reasoning recovery strategies
        assert RecoveryStrategy.DOCUMENT_DECISIONS.value == "document_decisions"
        assert RecoveryStrategy.INTRODUCE_NEW_CONTEXT.value == "introduce_new_context"
        assert RecoveryStrategy.CHANGE_REASONING_STRATEGY.value == "change_reasoning_strategy"
        
        # Scope creep recovery strategies
        assert RecoveryStrategy.FREEZE_TASK_SCOPE.value == "freeze_task_scope"
        assert RecoveryStrategy.BREAK_INTO_SUBTASKS.value == "break_into_subtasks"
        assert RecoveryStrategy.DEFER_OPTIONAL_FEATURES.value == "defer_optional_features"


class TestRecoveryStatusEnum:
    """Tests for RecoveryStatus enumeration."""
    
    def test_all_recovery_statuses_defined(self):
        """Test that all recovery statuses are defined."""
        assert RecoveryStatus.PENDING.value == "pending"
        assert RecoveryStatus.IN_PROGRESS.value == "in_progress"
        assert RecoveryStatus.SUCCESS.value == "success"
        assert RecoveryStatus.FAILED.value == "failed"
        assert RecoveryStatus.SKIPPED.value == "skipped"


class TestRecoveryAction:
    """Tests for RecoveryAction dataclass."""
    
    def test_create_recovery_action(self):
        """Test creating a recovery action."""
        action = RecoveryAction(
            strategy=RecoveryStrategy.BREAK_LOOP_CHANGE_APPROACH,
            description="Break loop by trying different approach",
            action_type="strategy_change",
            parameters={"preserve_context": True},
            estimated_disruption=0.3,
            expected_success_rate=0.7
        )
        
        assert action.strategy == RecoveryStrategy.BREAK_LOOP_CHANGE_APPROACH
        assert action.description == "Break loop by trying different approach"
        assert action.action_type == "strategy_change"
        assert action.parameters == {"preserve_context": True}
        assert action.estimated_disruption == 0.3
        assert action.expected_success_rate == 0.7
    
    def test_recovery_action_default_values(self):
        """Test recovery action default values."""
        action = RecoveryAction(
            strategy=RecoveryStrategy.BREAK_LOOP_CHANGE_APPROACH,
            description="Test action",
            action_type="strategy_change"
        )
        
        assert action.parameters == {}
        assert action.estimated_disruption == 0.5
        assert action.expected_success_rate == 0.8
    
    def test_recovery_action_repr(self):
        """Test recovery action string representation."""
        action = RecoveryAction(
            strategy=RecoveryStrategy.BREAK_LOOP_CHANGE_APPROACH,
            description="Test",
            action_type="strategy_change",
            estimated_disruption=0.3
        )
        
        repr_str = repr(action)
        assert "break_loop_change_approach" in repr_str
        assert "0.3" in repr_str


class TestRecoveryExecution:
    """Tests for RecoveryExecution dataclass."""
    
    def test_create_recovery_execution(self):
        """Test creating a recovery execution."""
        execution = RecoveryExecution(
            strategy=RecoveryStrategy.BREAK_LOOP_CHANGE_APPROACH,
            status=RecoveryStatus.SUCCESS,
            success=True,
            message="Recovery completed successfully"
        )
        
        assert execution.strategy == RecoveryStrategy.BREAK_LOOP_CHANGE_APPROACH
        assert execution.status == RecoveryStatus.SUCCESS
        assert execution.success is True
        assert execution.message == "Recovery completed successfully"
        assert execution.checkpoint_before is None
        assert execution.checkpoint_after is None
        assert execution.time_elapsed == 0.0
        assert execution.resources_used == {}
        assert execution.recovery_actions == {}
    
    def test_recovery_execution_with_all_fields(self):
        """Test recovery execution with all fields populated."""
        execution = RecoveryExecution(
            strategy=RecoveryStrategy.BACKTRACK_TO_CHECKPOINT,
            status=RecoveryStatus.SUCCESS,
            success=True,
            message="Backtracked successfully",
            checkpoint_before="chkp_123",
            checkpoint_after="chkp_124",
            time_elapsed=2.5,
            resources_used={"tokens": 1000},
            recovery_actions=[{"type": "checkpoint", "details": "Restored"}]
        )
        
        assert execution.checkpoint_before == "chkp_123"
        assert execution.checkpoint_after == "chkp_124"
        assert execution.time_elapsed == 2.5
        assert execution.resources_used == {"tokens": 1000}
        assert execution.recovery_actions == [{"type": "checkpoint", "details": "Restored"}]
    
    def test_recovery_execution_repr(self):
        """Test recovery execution string representation."""
        execution = RecoveryExecution(
            strategy=RecoveryStrategy.BREAK_LOOP_CHANGE_APPROACH,
            status=RecoveryStatus.SUCCESS,
            success=True,
            message="Success"
        )
        
        repr_str = repr(execution)
        assert "break_loop_change_approach" in repr_str
        assert "success" in repr_str
        assert "True" in repr_str


class TestTrapRecoveryEngineInit:
    """Tests for TrapRecoveryEngine initialization."""
    
    def test_init_without_managers(self):
        """Test initialization without checkpoint or telemetry managers."""
        engine = TrapRecoveryEngine()
        
        assert engine.trap_detector is not None
        assert engine.checkpoint_manager is None
        assert engine.telemetry_manager is None
        assert engine.recovery_history == {}
    
    def test_init_with_checkpoint_manager(self):
        """Test initialization with checkpoint manager."""
        mock_checkpoint = Mock()
        engine = TrapRecoveryEngine(checkpoint_manager=mock_checkpoint)
        
        assert engine.checkpoint_manager == mock_checkpoint
        assert engine.telemetry_manager is None
    
    def test_init_with_telemetry_manager(self):
        """Test initialization with telemetry manager."""
        mock_telemetry = Mock()
        engine = TrapRecoveryEngine(telemetry_manager=mock_telemetry)
        
        assert engine.checkpoint_manager is None
        assert engine.telemetry_manager == mock_telemetry
    
    def test_init_with_both_managers(self):
        """Test initialization with both managers."""
        mock_checkpoint = Mock()
        mock_telemetry = Mock()
        engine = TrapRecoveryEngine(
            checkpoint_manager=mock_checkpoint,
            telemetry_manager=mock_telemetry
        )
        
        assert engine.checkpoint_manager == mock_checkpoint
        assert engine.telemetry_manager == mock_telemetry
    
    def test_recovery_strategies_initialized(self):
        """Test that recovery strategies are initialized for all trap types."""
        engine = TrapRecoveryEngine()
        
        assert TrapType.INFINITE_LOOP in engine.recovery_strategies
        assert TrapType.DEAD_END in engine.recovery_strategies
        assert TrapType.CIRCULAR_REASONING in engine.recovery_strategies
        assert TrapType.SCOPE_CREEP in engine.recovery_strategies
        
        # Check that each trap type has strategies
        assert len(engine.recovery_strategies[TrapType.INFINITE_LOOP]) > 0
        assert len(engine.recovery_strategies[TrapType.DEAD_END]) > 0
        assert len(engine.recovery_strategies[TrapType.CIRCULAR_REASONING]) > 0
        assert len(engine.recovery_strategies[TrapType.SCOPE_CREEP]) > 0


class TestSelectRecoveryStrategy:
    """Tests for recovery strategy selection."""
    
    def test_select_strategy_for_infinite_loop(self):
        """Test selecting strategy for infinite loop trap."""
        engine = TrapRecoveryEngine()
        trap_detection = TrapDetection(
            trap_type=TrapType.INFINITE_LOOP,
            severity=TrapSeverity.CRITICAL,
            confidence=0.9,
            evidence={"loop_type": "exact_action_loop"},
            suggestion="Break the loop"
        )
        
        strategy = engine.select_recovery_strategy(trap_detection)
        
        assert strategy is not None
        assert strategy.strategy in [
            RecoveryStrategy.BREAK_LOOP_CHANGE_APPROACH,
            RecoveryStrategy.BACKTRACK_TO_CHECKPOINT,
            RecoveryStrategy.TRY_DIFFERENT_STRATEGY
        ]
    
    def test_select_strategy_for_dead_end(self):
        """Test selecting strategy for dead end trap."""
        engine = TrapRecoveryEngine()
        trap_detection = TrapDetection(
            trap_type=TrapType.DEAD_END,
            severity=TrapSeverity.BLOCKING,
            confidence=0.95,
            evidence={"dead_end_type": "no_progress"},
            suggestion="Backtrack to last success"
        )
        
        strategy = engine.select_recovery_strategy(trap_detection)
        
        assert strategy is not None
        assert strategy.strategy in [
            RecoveryStrategy.BACKTRACK_TO_LAST_SUCCESS,
            RecoveryStrategy.BREAK_TASK_SMALLER,
            RecoveryStrategy.TRY_ALTERNATIVE_APPROACH,
            RecoveryStrategy.ASK_HUMAN_INTERVENTION
        ]
    
    def test_select_strategy_for_circular_reasoning(self):
        """Test selecting strategy for circular reasoning trap."""
        engine = TrapRecoveryEngine()
        trap_detection = TrapDetection(
            trap_type=TrapType.CIRCULAR_REASONING,
            severity=TrapSeverity.CRITICAL,
            confidence=0.85,
            evidence={"circular_reasoning_type": "decision_cycle"},
            suggestion="Document decisions"
        )
        
        strategy = engine.select_recovery_strategy(trap_detection)
        
        assert strategy is not None
        assert strategy.strategy in [
            RecoveryStrategy.DOCUMENT_DECISIONS,
            RecoveryStrategy.INTRODUCE_NEW_CONTEXT,
            RecoveryStrategy.CHANGE_REASONING_STRATEGY,
            RecoveryStrategy.ASK_HUMAN_INTERVENTION
        ]
    
    def test_select_strategy_for_scope_creep(self):
        """Test selecting strategy for scope creep trap."""
        engine = TrapRecoveryEngine()
        trap_detection = TrapDetection(
            trap_type=TrapType.SCOPE_CREEP,
            severity=TrapSeverity.WARNING,
            confidence=0.7,
            evidence={"expansion_count": 3},
            suggestion="Freeze scope"
        )
        
        strategy = engine.select_recovery_strategy(trap_detection)
        
        assert strategy is not None
        assert strategy.strategy in [
            RecoveryStrategy.FREEZE_TASK_SCOPE,
            RecoveryStrategy.BREAK_INTO_SUBTASKS,
            RecoveryStrategy.DEFER_OPTIONAL_FEATURES
        ]
    
    def test_select_strategy_prefer_low_disruption(self):
        """Test strategy selection prefers low disruption."""
        engine = TrapRecoveryEngine()
        trap_detection = TrapDetection(
            trap_type=TrapType.INFINITE_LOOP,
            severity=TrapSeverity.WARNING,
            confidence=0.7,
            evidence={"loop_type": "exact_action_loop"},
            suggestion="Break the loop"
        )
        
        strategy = engine.select_recovery_strategy(
            trap_detection,
            prefer_low_disruption=True
        )
        
        assert strategy is not None
        # Should prefer lower disruption strategies
        assert strategy.estimated_disruption < 0.6
    
    def test_select_strategy_prefer_high_success(self):
        """Test strategy selection prefers high success rate."""
        engine = TrapRecoveryEngine()
        trap_detection = TrapDetection(
            trap_type=TrapType.DEAD_END,
            severity=TrapSeverity.BLOCKING,
            confidence=0.9,
            evidence={"dead_end_type": "exhausted_options"},
            suggestion="Need help"
        )
        
        strategy = engine.select_recovery_strategy(
            trap_detection,
            prefer_high_success=True
        )
        
        assert strategy is not None
        # Should prefer higher success strategies
        assert strategy.expected_success_rate > 0.7
    
    def test_select_strategy_with_historical_data(self):
        """Test strategy selection with historical success data."""
        engine = TrapRecoveryEngine()
        
        # Add historical data
        engine.recovery_history[RecoveryStrategy.BREAK_LOOP_CHANGE_APPROACH] = [True, True, False, True, True]
        
        trap_detection = TrapDetection(
            trap_type=TrapType.INFINITE_LOOP,
            severity=TrapSeverity.CRITICAL,
            confidence=0.9,
            evidence={"loop_type": "exact_action_loop"},
            suggestion="Break the loop"
        )
        
        strategy = engine.select_recovery_strategy(trap_detection)
        
        assert strategy is not None
        # Should favor strategies with good historical success
    
    def test_select_strategy_unknown_trap_type(self):
        """Test strategy selection with unknown trap type."""
        engine = TrapRecoveryEngine()
        
        # Create mock trap detection with unknown type
        trap_detection = TrapDetection(
            trap_type=TrapType.INFINITE_LOOP,  # Use known type but mock missing strategies
            severity=TrapSeverity.CRITICAL,
            confidence=0.9,
            evidence={},
            suggestion="Test"
        )
        
        # Temporarily remove strategies for this trap type
        original_strategies = engine.recovery_strategies[TrapType.INFINITE_LOOP]
        engine.recovery_strategies[TrapType.INFINITE_LOOP] = []
        
        strategy = engine.select_recovery_strategy(trap_detection)
        
        assert strategy is None
        
        # Restore
        engine.recovery_strategies[TrapType.INFINITE_LOOP] = original_strategies


class TestExecuteRecoveryCheckpointBased:
    """Tests for checkpoint-based recovery execution."""
    
    def test_execute_backtrack_to_checkpoint(self):
        """Test executing backtrack to checkpoint recovery."""
        mock_checkpoint = Mock()
        mock_checkpoint.create.return_value = "chkp_123"
        mock_checkpoint.list_checkpoints.return_value = [
            {"checkpoint_id": "chkp_123", "timestamp": datetime.now()}
        ]
        
        engine = TrapRecoveryEngine(checkpoint_manager=mock_checkpoint)
        
        trap_detection = TrapDetection(
            trap_type=TrapType.INFINITE_LOOP,
            severity=TrapSeverity.CRITICAL,
            confidence=0.9,
            evidence={"loop_type": "exact_action_loop"},
            suggestion="Backtrack"
        )
        
        recovery_action = RecoveryAction(
            strategy=RecoveryStrategy.BACKTRACK_TO_CHECKPOINT,
            description="Backtrack to checkpoint",
            action_type="checkpoint",
            parameters={},
            estimated_disruption=0.5,
            expected_success_rate=0.85
        )
        
        execution = engine.execute_recovery(recovery_action, trap_detection)
        
        assert execution.status == RecoveryStatus.SUCCESS
        assert execution.success is True
        assert "checkpoint" in execution.message.lower()
        assert execution.checkpoint_before is not None
        assert execution.checkpoint_after is not None
    
    def test_execute_backtrack_to_last_success(self):
        """Test executing backtrack to last success recovery."""
        mock_checkpoint = Mock()
        mock_checkpoint.create.return_value = "chkp_124"
        mock_checkpoint.list_checkpoints.return_value = [
            {"checkpoint_id": "chkp_124", "timestamp": datetime.now()}
        ]
        
        engine = TrapRecoveryEngine(checkpoint_manager=mock_checkpoint)
        
        trap_detection = TrapDetection(
            trap_type=TrapType.DEAD_END,
            severity=TrapSeverity.BLOCKING,
            confidence=0.95,
            evidence={"dead_end_type": "no_progress"},
            suggestion="Backtrack to success"
        )
        
        recovery_action = RecoveryAction(
            strategy=RecoveryStrategy.BACKTRACK_TO_LAST_SUCCESS,
            description="Backtrack to last success",
            action_type="checkpoint",
            parameters={"last_success": True},
            estimated_disruption=0.6,
            expected_success_rate=0.9
        )
        
        execution = engine.execute_recovery(recovery_action, trap_detection)
        
        assert execution.status == RecoveryStatus.SUCCESS
        assert execution.success is True
        assert "success" in execution.message.lower()
    
    def test_execute_backtrack_no_checkpoint_manager(self):
        """Test backtrack without checkpoint manager."""
        engine = TrapRecoveryEngine(checkpoint_manager=None)
        
        trap_detection = TrapDetection(
            trap_type=TrapType.INFINITE_LOOP,
            severity=TrapSeverity.CRITICAL,
            confidence=0.9,
            evidence={"loop_type": "exact_action_loop"},
            suggestion="Backtrack"
        )
        
        recovery_action = RecoveryAction(
            strategy=RecoveryStrategy.BACKTRACK_TO_CHECKPOINT,
            description="Backtrack to checkpoint",
            action_type="checkpoint",
            parameters={},
            estimated_disruption=0.5,
            expected_success_rate=0.85
        )
        
        execution = engine.execute_recovery(recovery_action, trap_detection)
        
        assert execution.status == RecoveryStatus.FAILED
        assert execution.success is False
        # The error message indicates checkpoint creation failed
        assert "checkpoint" in execution.message.lower()
    
    def test_execute_backtrack_no_checkpoint_available(self):
        """Test backtrack with no checkpoint available."""
        mock_checkpoint = Mock()
        mock_checkpoint.create.return_value = "chkp_125"
        mock_checkpoint.list_checkpoints.return_value = []
        
        engine = TrapRecoveryEngine(checkpoint_manager=mock_checkpoint)
        
        trap_detection = TrapDetection(
            trap_type=TrapType.INFINITE_LOOP,
            severity=TrapSeverity.CRITICAL,
            confidence=0.9,
            evidence={"loop_type": "exact_action_loop"},
            suggestion="Backtrack"
        )
        
        recovery_action = RecoveryAction(
            strategy=RecoveryStrategy.BACKTRACK_TO_CHECKPOINT,
            description="Backtrack to checkpoint",
            action_type="checkpoint",
            parameters={},
            estimated_disruption=0.5,
            expected_success_rate=0.85
        )
        
        execution = engine.execute_recovery(recovery_action, trap_detection)
        
        assert execution.status == RecoveryStatus.FAILED
        assert execution.success is False
        assert "no checkpoint" in execution.message.lower()


class TestExecuteRecoveryStateChange:
    """Tests for state change recovery execution."""
    
    def test_execute_break_task_smaller(self):
        """Test executing break task smaller recovery."""
        engine = TrapRecoveryEngine()
        
        trap_detection = TrapDetection(
            trap_type=TrapType.DEAD_END,
            severity=TrapSeverity.CRITICAL,
            confidence=0.9,
            evidence={"dead_end_type": "no_progress"},
            suggestion="Break task smaller"
        )
        
        recovery_action = RecoveryAction(
            strategy=RecoveryStrategy.BREAK_TASK_SMALLER,
            description="Break task into subtasks",
            action_type="state_change",
            parameters={"task_breakdown": True},
            estimated_disruption=0.4,
            expected_success_rate=0.8
        )
        
        context = {
            "current_task": {"id": "task_1", "description": "Large task"}
        }
        
        execution = engine.execute_recovery(recovery_action, trap_detection, context)
        
        assert execution.status == RecoveryStatus.SUCCESS
        assert execution.success is True
        assert "subtask" in execution.message.lower()
    
    def test_execute_document_decisions(self):
        """Test executing document decisions recovery."""
        engine = TrapRecoveryEngine()
        
        trap_detection = TrapDetection(
            trap_type=TrapType.CIRCULAR_REASONING,
            severity=TrapSeverity.WARNING,
            confidence=0.8,
            evidence={"circular_reasoning_type": "decision_cycle"},
            suggestion="Document decisions"
        )
        
        recovery_action = RecoveryAction(
            strategy=RecoveryStrategy.DOCUMENT_DECISIONS,
            description="Document decisions permanently",
            action_type="state_change",
            parameters={"document_decisions": True},
            estimated_disruption=0.2,
            expected_success_rate=0.85
        )
        
        context = {
            "decision_history": [
                {"id": "d1", "decision": "Option A"},
                {"id": "d2", "decision": "Option B"}
            ]
        }
        
        execution = engine.execute_recovery(recovery_action, trap_detection, context)
        
        assert execution.status == RecoveryStatus.SUCCESS
        assert execution.success is True
        assert "document" in execution.message.lower()
    
    def test_execute_freeze_task_scope(self):
        """Test executing freeze task scope recovery."""
        engine = TrapRecoveryEngine()
        
        trap_detection = TrapDetection(
            trap_type=TrapType.SCOPE_CREEP,
            severity=TrapSeverity.WARNING,
            confidence=0.7,
            evidence={"expansion_count": 3},
            suggestion="Freeze scope"
        )
        
        recovery_action = RecoveryAction(
            strategy=RecoveryStrategy.FREEZE_TASK_SCOPE,
            description="Freeze task scope",
            action_type="state_change",
            parameters={"freeze_scope": True},
            estimated_disruption=0.3,
            expected_success_rate=0.85
        )
        
        context = {
            "task_scope": {
                "requirements": ["req1", "req2", "req3"]
            }
        }
        
        execution = engine.execute_recovery(recovery_action, trap_detection, context)
        
        assert execution.status == RecoveryStatus.SUCCESS
        assert execution.success is True
        assert "frozen" in execution.message.lower()
    
    def test_execute_defer_optional_features(self):
        """Test executing defer optional features recovery."""
        engine = TrapRecoveryEngine()
        
        trap_detection = TrapDetection(
            trap_type=TrapType.SCOPE_CREEP,
            severity=TrapSeverity.WARNING,
            confidence=0.7,
            evidence={"expansion_count": 3},
            suggestion="Defer features"
        )
        
        recovery_action = RecoveryAction(
            strategy=RecoveryStrategy.DEFER_OPTIONAL_FEATURES,
            description="Defer optional features",
            action_type="state_change",
            parameters={"defer_features": True},
            estimated_disruption=0.3,
            expected_success_rate=0.9
        )
        
        context = {
            "optional_features": [
                {"id": "f1", "description": "Nice to have"},
                {"id": "f2", "description": "Bonus feature"}
            ]
        }
        
        execution = engine.execute_recovery(recovery_action, trap_detection, context)
        
        assert execution.status == RecoveryStatus.SUCCESS
        assert execution.success is True
        assert "defer" in execution.message.lower()


class TestExecuteRecoveryStrategyChange:
    """Tests for strategy change recovery execution."""
    
    def test_execute_break_loop_change_approach(self):
        """Test executing break loop change approach recovery."""
        engine = TrapRecoveryEngine()
        
        trap_detection = TrapDetection(
            trap_type=TrapType.INFINITE_LOOP,
            severity=TrapSeverity.CRITICAL,
            confidence=0.9,
            evidence={"loop_type": "exact_action_loop"},
            suggestion="Change approach"
        )
        
        recovery_action = RecoveryAction(
            strategy=RecoveryStrategy.BREAK_LOOP_CHANGE_APPROACH,
            description="Change approach to break loop",
            action_type="strategy_change",
            parameters={"preserve_context": True},
            estimated_disruption=0.3,
            expected_success_rate=0.7
        )
        
        context = {
            "current_approach": {"type": "analytical", "method": "incremental"}
        }
        
        execution = engine.execute_recovery(recovery_action, trap_detection, context)
        
        assert execution.status == RecoveryStatus.SUCCESS
        assert execution.success is True
        assert "approach" in execution.message.lower()
    
    def test_execute_try_different_strategy(self):
        """Test executing try different strategy recovery."""
        engine = TrapRecoveryEngine()
        
        trap_detection = TrapDetection(
            trap_type=TrapType.INFINITE_LOOP,
            severity=TrapSeverity.CRITICAL,
            confidence=0.9,
            evidence={"loop_type": "exact_action_loop"},
            suggestion="Try different strategy"
        )
        
        recovery_action = RecoveryAction(
            strategy=RecoveryStrategy.TRY_DIFFERENT_STRATEGY,
            description="Switch reasoning strategy",
            action_type="strategy_change",
            parameters={"change_strategy": True},
            estimated_disruption=0.4,
            expected_success_rate=0.75
        )
        
        context = {
            "reasoning_strategy": "balanced"
        }
        
        execution = engine.execute_recovery(recovery_action, trap_detection, context)
        
        assert execution.status == RecoveryStatus.SUCCESS
        assert execution.success is True
        assert "strategy" in execution.message.lower()
    
    def test_execute_introduce_new_context(self):
        """Test executing introduce new context recovery."""
        engine = TrapRecoveryEngine()
        
        trap_detection = TrapDetection(
            trap_type=TrapType.CIRCULAR_REASONING,
            severity=TrapSeverity.CRITICAL,
            confidence=0.9,
            evidence={"circular_reasoning_type": "decision_cycle"},
            suggestion="Introduce new context"
        )
        
        recovery_action = RecoveryAction(
            strategy=RecoveryStrategy.INTRODUCE_NEW_CONTEXT,
            description="Introduce new context",
            action_type="strategy_change",
            parameters={"new_context": True},
            estimated_disruption=0.4,
            expected_success_rate=0.7
        )
        
        context = {
            "context": {"key1": "value1", "key2": "value2"}
        }
        
        execution = engine.execute_recovery(recovery_action, trap_detection, context)
        
        assert execution.status == RecoveryStatus.SUCCESS
        assert execution.success is True
        assert "context" in execution.message.lower()
    
    def test_execute_try_alternative_approach(self):
        """Test executing try alternative approach recovery."""
        engine = TrapRecoveryEngine()
        
        trap_detection = TrapDetection(
            trap_type=TrapType.DEAD_END,
            severity=TrapSeverity.BLOCKING,
            confidence=0.95,
            evidence={"dead_end_type": "exhausted_options"},
            suggestion="Try alternative"
        )
        
        recovery_action = RecoveryAction(
            strategy=RecoveryStrategy.TRY_ALTERNATIVE_APPROACH,
            description="Try alternative approach",
            action_type="strategy_change",
            parameters={"alternative_approach": True},
            estimated_disruption=0.5,
            expected_success_rate=0.7
        )
        
        context = {
            "current_approach": {"type": "analytical"}
        }
        
        execution = engine.execute_recovery(recovery_action, trap_detection, context)
        
        assert execution.status == RecoveryStatus.SUCCESS
        assert execution.success is True
        assert "alternative" in execution.message.lower()


class TestExecuteRecoveryIntervention:
    """Tests for human intervention recovery execution."""
    
    def test_execute_ask_human_intervention(self):
        """Test executing ask human intervention recovery."""
        engine = TrapRecoveryEngine()
        
        trap_detection = TrapDetection(
            trap_type=TrapType.DEAD_END,
            severity=TrapSeverity.BLOCKING,
            confidence=0.95,
            evidence={"dead_end_type": "no_progress"},
            suggestion="Ask for help"
        )
        
        recovery_action = RecoveryAction(
            strategy=RecoveryStrategy.ASK_HUMAN_INTERVENTION,
            description="Request human intervention",
            action_type="intervention",
            parameters={"human_help": True},
            estimated_disruption=0.9,
            expected_success_rate=0.95
        )
        
        context = {
            "current_task": {"id": "task_1", "description": "Blocked task"}
        }
        
        execution = engine.execute_recovery(recovery_action, trap_detection, context)
        
        assert execution.status == RecoveryStatus.SUCCESS
        assert execution.success is True
        assert "intervention" in execution.message.lower()
        assert "human" in execution.message.lower()


class TestRecoveryHistory:
    """Tests for recovery history tracking."""
    
    def test_update_recovery_history_new_strategy(self):
        """Test updating recovery history for new strategy."""
        engine = TrapRecoveryEngine()
        
        engine._update_recovery_history(
            RecoveryStrategy.BREAK_LOOP_CHANGE_APPROACH,
            True
        )
        
        assert RecoveryStrategy.BREAK_LOOP_CHANGE_APPROACH in engine.recovery_history
        assert engine.recovery_history[RecoveryStrategy.BREAK_LOOP_CHANGE_APPROACH] == [True]
    
    def test_update_recovery_history_multiple_attempts(self):
        """Test updating recovery history with multiple attempts."""
        engine = TrapRecoveryEngine()
        
        engine._update_recovery_history(RecoveryStrategy.BREAK_LOOP_CHANGE_APPROACH, True)
        engine._update_recovery_history(RecoveryStrategy.BREAK_LOOP_CHANGE_APPROACH, False)
        engine._update_recovery_history(RecoveryStrategy.BREAK_LOOP_CHANGE_APPROACH, True)
        
        assert engine.recovery_history[RecoveryStrategy.BREAK_LOOP_CHANGE_APPROACH] == [True, False, True]
    
    def test_update_recovery_history_limit_to_100(self):
        """Test that recovery history is limited to 100 entries."""
        engine = TrapRecoveryEngine()
        
        # Add 150 attempts
        for i in range(150):
            engine._update_recovery_history(RecoveryStrategy.BREAK_LOOP_CHANGE_APPROACH, i % 2 == 0)
        
        assert len(engine.recovery_history[RecoveryStrategy.BREAK_LOOP_CHANGE_APPROACH]) == 100
    
    def test_get_recovery_statistics_empty(self):
        """Test getting recovery statistics with empty history."""
        engine = TrapRecoveryEngine()
        
        stats = engine.get_recovery_statistics()
        
        assert stats["total_recovery_attempts"] == 0
        assert stats["overall_success_rate"] == 0.0
        assert len(stats["strategy_statistics"]) == 0
    
    def test_get_recovery_statistics_with_data(self):
        """Test getting recovery statistics with data."""
        engine = TrapRecoveryEngine()
        
        # Add some recovery attempts
        engine.recovery_history[RecoveryStrategy.BREAK_LOOP_CHANGE_APPROACH] = [True, True, False, True, True]
        engine.recovery_history[RecoveryStrategy.BACKTRACK_TO_CHECKPOINT] = [True, True, True]
        
        stats = engine.get_recovery_statistics()
        
        assert stats["total_recovery_attempts"] == 8
        assert stats["overall_success_rate"] == 0.875  # 7/8 (4+3 successes / 8 total)
        
        # Check individual strategy statistics
        assert stats["strategy_statistics"]["break_loop_change_approach"]["attempts"] == 5
        assert stats["strategy_statistics"]["break_loop_change_approach"]["successes"] == 4
        assert stats["strategy_statistics"]["break_loop_change_approach"]["success_rate"] == 0.8
        
        assert stats["strategy_statistics"]["backtrack_to_checkpoint"]["attempts"] == 3
        assert stats["strategy_statistics"]["backtrack_to_checkpoint"]["successes"] == 3
        assert stats["strategy_statistics"]["backtrack_to_checkpoint"]["success_rate"] == 1.0
    
    def test_reset_recovery_history(self):
        """Test resetting recovery history."""
        engine = TrapRecoveryEngine()
        
        # Add some history
        engine.recovery_history[RecoveryStrategy.BREAK_LOOP_CHANGE_APPROACH] = [True, True]
        
        engine.reset_recovery_history()
        
        assert engine.recovery_history == {}


class TestRecoveryWithTelemetry:
    """Tests for recovery with telemetry integration."""
    
    def test_execute_recovery_logs_to_telemetry(self):
        """Test that recovery execution logs to telemetry."""
        mock_telemetry = Mock()
        mock_checkpoint = Mock()
        mock_checkpoint.create.return_value = "chkp_126"
        
        engine = TrapRecoveryEngine(
            checkpoint_manager=mock_checkpoint,
            telemetry_manager=mock_telemetry
        )
        
        trap_detection = TrapDetection(
            trap_type=TrapType.INFINITE_LOOP,
            severity=TrapSeverity.CRITICAL,
            confidence=0.9,
            evidence={"loop_type": "exact_action_loop"},
            suggestion="Break the loop"
        )
        
        recovery_action = RecoveryAction(
            strategy=RecoveryStrategy.BREAK_LOOP_CHANGE_APPROACH,
            description="Change approach",
            action_type="strategy_change",
            parameters={},
            estimated_disruption=0.3,
            expected_success_rate=0.7
        )
        
        execution = engine.execute_recovery(recovery_action, trap_detection)
        
        # Verify telemetry calls
        assert mock_telemetry.start_operation.called
        assert mock_telemetry.record_metric.called
        assert mock_telemetry.end_operation.called
    
    def test_execute_recovery_without_telemetry(self):
        """Test that recovery works without telemetry manager."""
        mock_checkpoint = Mock()
        mock_checkpoint.create.return_value = "chkp_127"
        
        engine = TrapRecoveryEngine(
            checkpoint_manager=mock_checkpoint,
            telemetry_manager=None
        )
        
        trap_detection = TrapDetection(
            trap_type=TrapType.INFINITE_LOOP,
            severity=TrapSeverity.CRITICAL,
            confidence=0.9,
            evidence={"loop_type": "exact_action_loop"},
            suggestion="Break the loop"
        )
        
        recovery_action = RecoveryAction(
            strategy=RecoveryStrategy.BREAK_LOOP_CHANGE_APPROACH,
            description="Change approach",
            action_type="strategy_change",
            parameters={},
            estimated_disruption=0.3,
            expected_success_rate=0.7
        )
        
        # Should not raise error
        execution = engine.execute_recovery(recovery_action, trap_detection)
        
        assert execution.status == RecoveryStatus.SUCCESS


class TestRecoveryFailureHandling:
    """Tests for recovery failure handling."""
    
    def test_execute_recovery_rolls_back_on_failure(self):
        """Test that recovery rolls back on failure."""
        mock_checkpoint = Mock()
        mock_checkpoint.create.return_value = "chkp_128"
        mock_checkpoint.restore.return_value = True
        
        engine = TrapRecoveryEngine(checkpoint_manager=mock_checkpoint)
        
        # Create a trap detection that will cause failure
        trap_detection = TrapDetection(
            trap_type=TrapType.INFINITE_LOOP,
            severity=TrapSeverity.CRITICAL,
            confidence=0.9,
            evidence={"loop_type": "exact_action_loop"},
            suggestion="Break the loop"
        )
        
        # Create recovery action with unknown type (will fail)
        recovery_action = RecoveryAction(
            strategy=RecoveryStrategy.BREAK_LOOP_CHANGE_APPROACH,
            description="Test",
            action_type="unknown_type",  # This will cause failure
            parameters={},
            estimated_disruption=0.3,
            expected_success_rate=0.7
        )
        
        execution = engine.execute_recovery(recovery_action, trap_detection)
        
        assert execution.status == RecoveryStatus.FAILED
        assert execution.success is False
        assert "rolled back" in execution.message.lower()
        assert mock_checkpoint.restore.called
    
    def test_execute_recovery_handles_exception(self):
        """Test that recovery execution handles exceptions gracefully."""
        mock_checkpoint = Mock()
        mock_checkpoint.create.side_effect = Exception("Checkpoint creation failed")
        
        engine = TrapRecoveryEngine(checkpoint_manager=mock_checkpoint)
        
        trap_detection = TrapDetection(
            trap_type=TrapType.INFINITE_LOOP,
            severity=TrapSeverity.CRITICAL,
            confidence=0.9,
            evidence={"loop_type": "exact_action_loop"},
            suggestion="Break the loop"
        )
        
        recovery_action = RecoveryAction(
            strategy=RecoveryStrategy.BREAK_LOOP_CHANGE_APPROACH,
            description="Change approach",
            action_type="strategy_change",  # strategy_change actions don't require checkpoints
            parameters={},
            estimated_disruption=0.3,
            expected_success_rate=0.7
        )
        
        # Should not raise exception and should succeed (checkpoint optional for strategy_change)
        execution = engine.execute_recovery(recovery_action, trap_detection)
        
        assert execution.status == RecoveryStatus.SUCCESS
        assert execution.success is True
        assert "approach" in execution.message.lower()


class TestFactoryFunction:
    """Tests for factory function."""
    
    def test_create_trap_recovery_engine(self):
        """Test factory function creates engine."""
        engine = create_trap_recovery_engine()
        
        assert isinstance(engine, TrapRecoveryEngine)
        assert engine.trap_detector is not None
        assert engine.checkpoint_manager is None
        assert engine.telemetry_manager is None
    
    def test_create_trap_recovery_engine_with_managers(self):
        """Test factory function with managers."""
        mock_checkpoint = Mock()
        mock_telemetry = Mock()
        
        engine = create_trap_recovery_engine(
            checkpoint_manager=mock_checkpoint,
            telemetry_manager=mock_telemetry
        )
        
        assert isinstance(engine, TrapRecoveryEngine)
        assert engine.checkpoint_manager == mock_checkpoint
        assert engine.telemetry_manager == mock_telemetry


class TestScoringAlgorithm:
    """Tests for strategy scoring algorithm."""
    
    def test_score_strategy_considers_success_rate(self):
        """Test that scoring considers success rate."""
        engine = TrapRecoveryEngine()
        
        # Add high success history
        engine.recovery_history[RecoveryStrategy.BREAK_LOOP_CHANGE_APPROACH] = [True] * 10
        
        trap_detection = TrapDetection(
            trap_type=TrapType.INFINITE_LOOP,
            severity=TrapSeverity.WARNING,
            confidence=0.7,
            evidence={"loop_type": "exact_action_loop"},
            suggestion="Break"
        )
        
        # Get all strategies and find the one we have history for
        available_strategies = engine.recovery_strategies[TrapType.INFINITE_LOOP]
        target_strategy = next(
            (s for s in available_strategies 
             if s.strategy == RecoveryStrategy.BREAK_LOOP_CHANGE_APPROACH),
            None
        )
        
        if target_strategy:
            score = engine._score_recovery_strategy(
                target_strategy,
                trap_detection.severity,
                prefer_low_disruption=True,
                prefer_high_success=True
            )
            
            # Score should be high due to good history
            assert score > 0.5
    
    def test_score_strategy_considers_disruption(self):
        """Test that scoring considers disruption level."""
        engine = TrapRecoveryEngine()
        
        trap_detection = TrapDetection(
            trap_type=TrapType.INFINITE_LOOP,
            severity=TrapSeverity.WARNING,
            confidence=0.7,
            evidence={"loop_type": "exact_action_loop"},
            suggestion="Break"
        )
        
        available_strategies = engine.recovery_strategies[TrapType.INFINITE_LOOP]
        
        # Score low disruption strategy
        low_disruption = min(available_strategies, key=lambda s: s.estimated_disruption)
        score_low = engine._score_recovery_strategy(
            low_disruption,
            trap_detection.severity,
            prefer_low_disruption=True,
            prefer_high_success=False
        )
        
        # Score high disruption strategy
        high_disruption = max(available_strategies, key=lambda s: s.estimated_disruption)
        score_high = engine._score_recovery_strategy(
            high_disruption,
            trap_detection.severity,
            prefer_low_disruption=True,
            prefer_high_success=False
        )
        
        # Low disruption should score higher when preferring low disruption
        assert score_low > score_high
    
    def test_score_strategy_considers_severity(self):
        """Test that scoring considers trap severity."""
        engine = TrapRecoveryEngine()
        
        recovery_action = RecoveryAction(
            strategy=RecoveryStrategy.BREAK_LOOP_CHANGE_APPROACH,
            description="Test",
            action_type="strategy_change",
            parameters={},
            estimated_disruption=0.5,
            expected_success_rate=0.7
        )
        
        # Score with warning severity
        score_warning = engine._score_recovery_strategy(
            recovery_action,
            TrapSeverity.WARNING,
            prefer_low_disruption=False,
            prefer_high_success=True
        )
        
        # Score with blocking severity
        score_blocking = engine._score_recovery_strategy(
            recovery_action,
            TrapSeverity.BLOCKING,
            prefer_low_disruption=False,
            prefer_high_success=True
        )
        
        # Blocking should get higher score (severity multiplier)
        assert score_blocking > score_warning


if __name__ == "__main__":
    pytest.main([__file__, "-v"])