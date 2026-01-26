"""
Unit tests for strategy_selector module

Tests cover:
- Strategy selection based on situation type
- Strategy performance tracking
- Adaptive strategy switching
- Strategy recommendations
- Learning optimal strategies
- Performance window management
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch

from v5.logic.reasoning_engine import (
    ReasoningStrategy,
    SituationType,
    SituationReport,
    Decision,
    ValidationResult
)
from v5.logic.strategy_selector import (
    StrategySelector,
    StrategyPerformanceMetrics,
    StrategySwitchEvent
)


class TestStrategyPerformanceMetrics:
    """Test StrategyPerformanceMetrics class"""
    
    def test_initial_metrics(self):
        """Test initial metrics values"""
        metrics = StrategyPerformanceMetrics()
        
        assert metrics.total_usage == 0
        assert metrics.successful_uses == 0
        assert metrics.success_rate == 0.0
        assert metrics.average_time == 0.0
        assert metrics.average_efficiency == 0.0
        assert metrics.average_confidence == 0.0
        assert metrics.last_used is None
    
    def test_calculate_success_rate_zero_usage(self):
        """Test success rate calculation with zero usage"""
        metrics = StrategyPerformanceMetrics()
        
        assert metrics.calculate_success_rate() == 0.0
    
    def test_update_success(self):
        """Test updating metrics with success"""
        metrics = StrategyPerformanceMetrics()
        
        metrics.update(
            success=True,
            time_elapsed=1.0,
            efficiency=0.8,
            confidence=0.7,
            task_type="test_task",
            situation_type=SituationType.NORMAL
        )
        
        assert metrics.total_usage == 1
        assert metrics.successful_uses == 1
        assert metrics.success_rate == 1.0
        assert metrics.average_time == 1.0
        assert metrics.average_efficiency == 0.8
        assert metrics.average_confidence == 0.7
        assert metrics.last_used is not None
    
    def test_update_failure(self):
        """Test updating metrics with failure"""
        metrics = StrategyPerformanceMetrics()
        
        metrics.update(
            success=False,
            time_elapsed=2.0,
            efficiency=0.3,
            confidence=0.4,
            task_type="test_task",
            situation_type=SituationType.ERROR
        )
        
        assert metrics.total_usage == 1
        assert metrics.successful_uses == 0
        assert metrics.success_rate == 0.0
        assert metrics.average_time == 2.0
        assert metrics.average_efficiency == 0.3
        assert metrics.average_confidence == 0.4
    
    def test_update_multiple(self):
        """Test updating metrics multiple times"""
        metrics = StrategyPerformanceMetrics()
        
        # First update
        metrics.update(
            success=True,
            time_elapsed=1.0,
            efficiency=0.8,
            confidence=0.7
        )
        
        # Second update
        metrics.update(
            success=False,
            time_elapsed=2.0,
            efficiency=0.5,
            confidence=0.6
        )
        
        assert metrics.total_usage == 2
        assert metrics.successful_uses == 1
        assert metrics.success_rate == 0.5
        
        # Should use exponential moving average
        assert metrics.average_time > 1.0
        assert metrics.average_time < 2.0
        assert metrics.average_efficiency > 0.5
        assert metrics.average_efficiency < 0.8
    
    def test_task_type_performance(self):
        """Test task type specific performance tracking"""
        metrics = StrategyPerformanceMetrics()
        
        metrics.update(
            success=True,
            time_elapsed=1.0,
            efficiency=0.8,
            confidence=0.7,
            task_type="test_task"
        )
        
        assert "test_task" in metrics.task_type_performance
        assert metrics.task_type_performance["test_task"]["total"] == 1
        assert metrics.task_type_performance["test_task"]["successful"] == 1
        assert metrics.task_type_performance["test_task"]["avg_efficiency"] == 0.8
    
    def test_situation_performance(self):
        """Test situation type specific performance tracking"""
        metrics = StrategyPerformanceMetrics()
        
        metrics.update(
            success=True,
            time_elapsed=1.0,
            efficiency=0.8,
            confidence=0.7,
            situation_type=SituationType.ERROR
        )
        
        assert metrics.situation_performance[SituationType.ERROR]["total"] == 1
        assert metrics.situation_performance[SituationType.ERROR]["successful"] == 1
        assert metrics.situation_performance[SituationType.ERROR]["avg_efficiency"] == 0.8


class TestStrategySelector:
    """Test StrategySelector class"""
    
    def test_initialization(self):
        """Test selector initialization"""
        selector = StrategySelector()
        
        assert selector.switch_threshold == 0.6
        assert selector.min_samples_before_switch == 5
        assert selector.current_strategy is None
        assert len(selector.switch_history) == 0
        assert len(selector.learned_optimal_strategies) == 0
        
        # Check all strategies have performance metrics
        for strategy in ReasoningStrategy:
            assert strategy in selector.strategy_performance
            assert isinstance(
                selector.strategy_performance[strategy],
                StrategyPerformanceMetrics
            )
    
    def test_custom_initialization(self):
        """Test selector initialization with custom parameters"""
        telemetry = Mock()
        selector = StrategySelector(
            telemetry_manager=telemetry,
            switch_threshold=0.7,
            min_samples_before_switch=10
        )
        
        assert selector.telemetry == telemetry
        assert selector.switch_threshold == 0.7
        assert selector.min_samples_before_switch == 10
    
    def test_select_strategy_normal_situation(self):
        """Test strategy selection for normal situation"""
        selector = StrategySelector()
        
        report = SituationReport(
            timestamp=datetime.now(),
            situation_type=SituationType.NORMAL,
            confidence=0.8,
            features={},
            potential_actions=[],
            risks=[],
            constraints=[],
            recommendations=[]
        )
        
        strategy = selector.select_strategy(report)
        
        # Normal should prefer BALANCED
        assert strategy == ReasoningStrategy.BALANCED
        assert selector.current_strategy == ReasoningStrategy.BALANCED
    
    def test_select_strategy_error_situation(self):
        """Test strategy selection for error situation"""
        selector = StrategySelector()
        
        report = SituationReport(
            timestamp=datetime.now(),
            situation_type=SituationType.ERROR,
            confidence=0.6,
            features={},
            potential_actions=[],
            risks=[],
            constraints=[],
            recommendations=[]
        )
        
        strategy = selector.select_strategy(report)
        
        # Error should prefer CONSERVATIVE
        assert strategy == ReasoningStrategy.CONSERVATIVE
    
    def test_select_strategy_time_critical_situation(self):
        """Test strategy selection for time-critical situation"""
        selector = StrategySelector()
        
        report = SituationReport(
            timestamp=datetime.now(),
            situation_type=SituationType.TIME_CRITICAL,
            confidence=0.7,
            features={},
            potential_actions=[],
            risks=[],
            constraints=[],
            recommendations=[]
        )
        
        strategy = selector.select_strategy(report)
        
        # Time critical should prefer AGGRESSIVE
        assert strategy == ReasoningStrategy.AGGRESSIVE
    
    def test_select_strategy_with_task_type(self):
        """Test strategy selection with task type"""
        selector = StrategySelector()
        
        # Set learned optimal strategy
        selector.learned_optimal_strategies["test_task"] = ReasoningStrategy.CONSERVATIVE
        
        report = SituationReport(
            timestamp=datetime.now(),
            situation_type=SituationType.NORMAL,
            confidence=0.8,
            features={},
            potential_actions=[],
            risks=[],
            constraints=[],
            recommendations=[]
        )
        
        strategy = selector.select_strategy(report, task_type="test_task")
        
        # Should use learned optimal strategy
        assert strategy == ReasoningStrategy.CONSERVATIVE
    
    def test_select_strategy_current_good(self):
        """Test that current strategy is kept if it's good"""
        selector = StrategySelector()
        
        # Set current strategy
        selector.current_strategy = ReasoningStrategy.BALANCED
        
        # Add performance data
        for _ in range(6):  # Above min_samples
            selector.strategy_performance[ReasoningStrategy.BALANCED].update(
                success=True,
                time_elapsed=1.0,
                efficiency=0.8,
                confidence=0.7
            )
        
        report = SituationReport(
            timestamp=datetime.now(),
            situation_type=SituationType.NORMAL,
            confidence=0.8,
            features={},
            potential_actions=[],
            risks=[],
            constraints=[],
            recommendations=[]
        )
        
        strategy = selector.select_strategy(report)
        
        # Should keep current strategy
        assert strategy == ReasoningStrategy.BALANCED
    
    def test_should_switch_success_rate_low(self):
        """Test switching when success rate is low"""
        selector = StrategySelector()
        selector.switch_threshold = 0.7
        
        # Add performance data with low success rate
        for i in range(6):
            selector.strategy_performance[ReasoningStrategy.BALANCED].update(
                success=(i < 2),  # Only 2 successes out of 6 = 33%
                time_elapsed=1.0,
                efficiency=0.5,
                confidence=0.6
            )
        
        # Add better performing strategy
        for _ in range(6):
            selector.strategy_performance[ReasoningStrategy.CONSERVATIVE].update(
                success=True,  # 100% success
                time_elapsed=2.0,
                efficiency=0.7,
                confidence=0.8
            )
        
        should_switch, new_strategy, reason = selector.should_switch_strategy(
            ReasoningStrategy.BALANCED,
            []
        )
        
        assert should_switch is True
        assert new_strategy == ReasoningStrategy.CONSERVATIVE
        assert "success rate" in reason.lower()
    
    def test_should_switch_not_enough_samples(self):
        """Test no switch when not enough samples"""
        selector = StrategySelector()
        
        # Add only 3 samples (below min_samples of 5)
        for _ in range(3):
            selector.strategy_performance[ReasoningStrategy.BALANCED].update(
                success=False,
                time_elapsed=1.0,
                efficiency=0.3,
                confidence=0.4
            )
        
        should_switch, new_strategy, reason = selector.should_switch_strategy(
            ReasoningStrategy.BALANCED,
            []
        )
        
        assert should_switch is False
        assert new_strategy is None
        assert "insufficient" in reason.lower()
    
    def test_should_switch_repeated_errors(self):
        """Test switching when there are repeated errors"""
        selector = StrategySelector()
        
        # Add enough samples
        for _ in range(5):
            selector.strategy_performance[ReasoningStrategy.BALANCED].update(
                success=True,
                time_elapsed=1.0,
                efficiency=0.8,
                confidence=0.7
            )
        
        # Add better performing strategy
        for _ in range(5):
            selector.strategy_performance[ReasoningStrategy.CONSERVATIVE].update(
                success=True,
                time_elapsed=2.0,
                efficiency=0.9,
                confidence=0.8
            )
        
        # Recent performance with repeated failures
        recent_perf = [
            {"success": False, "strategy": ReasoningStrategy.BALANCED},
            {"success": False, "strategy": ReasoningStrategy.BALANCED},
            {"success": False, "strategy": ReasoningStrategy.BALANCED}
        ]
        
        should_switch, new_strategy, reason = selector.should_switch_strategy(
            ReasoningStrategy.BALANCED,
            recent_perf
        )
        
        assert should_switch is True
        assert "repeated errors" in reason.lower()
    
    def test_should_switch_stagnation(self):
        """Test switching when stagnating"""
        selector = StrategySelector()
        
        # Add enough samples
        for _ in range(5):
            selector.strategy_performance[ReasoningStrategy.BALANCED].update(
                success=True,
                time_elapsed=1.0,
                efficiency=0.8,
                confidence=0.7
            )
        
        # Add better performing strategy
        for _ in range(5):
            selector.strategy_performance[ReasoningStrategy.CONSERVATIVE].update(
                success=True,
                time_elapsed=2.0,
                efficiency=0.9,
                confidence=0.8
            )
        
        # Recent performance with stagnation
        recent_perf = [
            {"success": True, "progress": 0.01, "strategy": ReasoningStrategy.BALANCED},
            {"success": True, "progress": 0.02, "strategy": ReasoningStrategy.BALANCED},
            {"success": True, "progress": 0.01, "strategy": ReasoningStrategy.BALANCED},
            {"success": True, "progress": 0.02, "strategy": ReasoningStrategy.BALANCED},
            {"success": True, "progress": 0.01, "strategy": ReasoningStrategy.BALANCED}
        ]
        
        should_switch, new_strategy, reason = selector.should_switch_strategy(
            ReasoningStrategy.BALANCED,
            recent_perf
        )
        
        assert should_switch is True
        assert "stagnation" in reason.lower()
    
    def test_switch_strategy(self):
        """Test strategy switching"""
        selector = StrategySelector()
        
        switch_event = selector.switch_strategy(
            from_strategy=ReasoningStrategy.BALANCED,
            to_strategy=ReasoningStrategy.CONSERVATIVE,
            reason="Testing switch"
        )
        
        assert isinstance(switch_event, StrategySwitchEvent)
        assert switch_event.from_strategy == ReasoningStrategy.BALANCED
        assert switch_event.to_strategy == ReasoningStrategy.CONSERVATIVE
        assert switch_event.reason == "Testing switch"
        assert len(selector.switch_history) == 1
        assert selector.current_strategy == ReasoningStrategy.CONSERVATIVE
    
    def test_update_strategy_performance(self):
        """Test updating strategy performance"""
        selector = StrategySelector()
        
        decision = Decision(
            action="test_action",
            strategy=ReasoningStrategy.BALANCED,
            reasoning="Test reasoning",
            confidence=0.8,
            alternatives=[],
            expected_outcome="Test outcome",
            risk_level=0.3,
            time_estimate=1.0,
            resource_estimate={}
        )
        
        validation_result = ValidationResult(
            success=True,
            goal_achieved=True,
            side_effects=[],
            progress_made=0.2,
            efficiency_score=0.8,
            error_message=None,
            corrections_needed=[]
        )
        
        selector.update_strategy_performance(
            strategy=ReasoningStrategy.BALANCED,
            validation_result=validation_result,
            decision=decision,
            time_elapsed=1.5,
            task_type="test_task",
            situation_type=SituationType.NORMAL
        )
        
        perf = selector.strategy_performance[ReasoningStrategy.BALANCED]
        assert perf.total_usage == 1
        assert perf.successful_uses == 1
        assert perf.success_rate == 1.0
        assert "test_task" in perf.task_type_performance
    
    def test_get_strategy_performance(self):
        """Test getting strategy performance metrics"""
        selector = StrategySelector()
        
        # Add some performance data
        for i in range(10):
            selector.strategy_performance[ReasoningStrategy.BALANCED].update(
                success=(i < 8),  # 80% success
                time_elapsed=1.0,
                efficiency=0.8,
                confidence=0.7,
                task_type="test_task"
            )
        
        perf = selector.get_strategy_performance(ReasoningStrategy.BALANCED, task_type="test_task")
        
        assert perf["strategy"] == "balanced"
        assert perf["total_usage"] == 10
        assert perf["success_rate"] == 0.8
        assert "task_type_performance" in perf
        assert perf["task_type_performance"]["total"] == 10
    
    def test_get_strategy_performance_with_situation(self):
        """Test getting strategy performance with situation filter"""
        selector = StrategySelector()
        
        # Add performance data for different situations
        for _ in range(5):
            selector.strategy_performance[ReasoningStrategy.BALANCED].update(
                success=True,
                time_elapsed=1.0,
                efficiency=0.8,
                confidence=0.7,
                situation_type=SituationType.ERROR
            )
        
        perf = selector.get_strategy_performance(
            ReasoningStrategy.BALANCED,
            situation_type=SituationType.ERROR
        )
        
        assert "situation_performance" in perf
        assert perf["situation_performance"]["total"] == 5
        assert perf["situation_performance"]["success_rate"] == 1.0
    
    def test_get_strategy_recommendations(self):
        """Test getting strategy recommendations"""
        selector = StrategySelector()
        
        recommendations = selector.get_strategy_recommendations(
            situation_type=SituationType.NORMAL
        )
        
        assert len(recommendations) == 3  # Three strategies
        assert all(isinstance(r[0], ReasoningStrategy) for r in recommendations)
        assert all(isinstance(r[1], float) for r in recommendations)
        assert all(isinstance(r[2], str) for r in recommendations)
        
        # Should be sorted by score (descending)
        scores = [r[1] for r in recommendations]
        assert scores == sorted(scores, reverse=True)
    
    def test_get_strategy_recommendations_with_task_type(self):
        """Test strategy recommendations with task type"""
        selector = StrategySelector()
        
        # Set learned optimal strategy
        selector.learned_optimal_strategies["test_task"] = ReasoningStrategy.CONSERVATIVE
        
        recommendations = selector.get_strategy_recommendations(
            situation_type=SituationType.NORMAL,
            task_type="test_task"
        )
        
        # CONSERVATIVE should have higher score due to learning
        conservative_rec = [r for r in recommendations if r[0] == ReasoningStrategy.CONSERVATIVE]
        assert len(conservative_rec) == 1
        assert "Learned optimal" in conservative_rec[0][2]
    
    def test_update_learned_optimal_strategy(self):
        """Test updating learned optimal strategy"""
        selector = StrategySelector()
        
        # Add performance data
        for _ in range(6):
            selector.strategy_performance[ReasoningStrategy.CONSERVATIVE].update(
                success=True,
                time_elapsed=2.0,
                efficiency=0.9,
                confidence=0.8,
                task_type="test_task"
            )
        
        decision = Decision(
            action="test_action",
            strategy=ReasoningStrategy.CONSERVATIVE,
            reasoning="Test reasoning",
            confidence=0.8,
            alternatives=[],
            expected_outcome="Test outcome",
            risk_level=0.1,
            time_estimate=2.0,
            resource_estimate={}
        )
        
        validation_result = ValidationResult(
            success=True,
            goal_achieved=True,
            side_effects=[],
            progress_made=0.3,
            efficiency_score=0.9,
            error_message=None,
            corrections_needed=[]
        )
        
        selector.update_strategy_performance(
            strategy=ReasoningStrategy.CONSERVATIVE,
            validation_result=validation_result,
            decision=decision,
            time_elapsed=2.0,
            task_type="test_task"
        )
        
        assert "test_task" in selector.learned_optimal_strategies
        assert selector.learned_optimal_strategies["test_task"] == ReasoningStrategy.CONSERVATIVE
    
    def test_update_learned_optimal_strategy_better(self):
        """Test updating to better learned optimal strategy"""
        selector = StrategySelector()
        
        # Set initial optimal
        selector.learned_optimal_strategies["test_task"] = ReasoningStrategy.BALANCED
        
        # Add performance data for BALANCED (worse)
        for _ in range(6):
            selector.strategy_performance[ReasoningStrategy.BALANCED].update(
                success=(True if _ < 4 else False),  # 4 successes out of 6 = 67%
                time_elapsed=1.0,
                efficiency=0.7,
                confidence=0.6,
                task_type="test_task"
            )
            selector.strategy_performance[ReasoningStrategy.CONSERVATIVE].update(
                success=True,  # 100% success
                time_elapsed=2.0,
                efficiency=0.9,
                confidence=0.8,
                task_type="test_task"
            )
        
        decision = Decision(
            action="test_action",
            strategy=ReasoningStrategy.CONSERVATIVE,
            reasoning="Test reasoning",
            confidence=0.8,
            alternatives=[],
            expected_outcome="Test outcome",
            risk_level=0.1,
            time_estimate=2.0,
            resource_estimate={}
        )
        
        validation_result = ValidationResult(
            success=True,
            goal_achieved=True,
            side_effects=[],
            progress_made=0.3,
            efficiency_score=0.9,
            error_message=None,
            corrections_needed=[]
        )
        
        selector.update_strategy_performance(
            strategy=ReasoningStrategy.CONSERVATIVE,
            validation_result=validation_result,
            decision=decision,
            time_elapsed=2.0,
            task_type="test_task"
        )
        
        # Should update to better strategy
        assert selector.learned_optimal_strategies["test_task"] == ReasoningStrategy.CONSERVATIVE
    
    def test_recent_performance_window(self):
        """Test recent performance window management"""
        selector = StrategySelector()
        
        decision = Decision(
            action="test_action",
            strategy=ReasoningStrategy.BALANCED,
            reasoning="Test reasoning",
            confidence=0.7,
            alternatives=[],
            expected_outcome="Test outcome",
            risk_level=0.3,
            time_estimate=1.0,
            resource_estimate={}
        )
        
        validation_result = ValidationResult(
            success=True,
            goal_achieved=True,
            side_effects=[],
            progress_made=0.2,
            efficiency_score=0.8,
            error_message=None,
            corrections_needed=[]
        )
        
        # Add 15 performance records
        for i in range(15):
            validation_result.progress_made = 0.1 + (i * 0.01)
            selector.update_strategy_performance(
                strategy=ReasoningStrategy.BALANCED,
                validation_result=validation_result,
                decision=decision,
                time_elapsed=1.0
            )
        
        # Should only keep 10 (performance_window_size)
        assert len(selector.recent_performance_window) == 10
    
    def test_telemetry_integration(self):
        """Test telemetry integration"""
        telemetry = Mock()
        selector = StrategySelector(telemetry_manager=telemetry)
        
        report = SituationReport(
            timestamp=datetime.now(),
            situation_type=SituationType.NORMAL,
            confidence=0.8,
            features={},
            potential_actions=[],
            risks=[],
            constraints=[],
            recommendations=[]
        )
        
        selector.select_strategy(report)
        
        # Should record strategy selection event
        telemetry.record_event.assert_called()
        call_args = telemetry.record_event.call_args
        assert call_args[1]["event_type"] == "strategy_selected"
    
    def test_switch_threshold_custom(self):
        """Test custom switch threshold"""
        selector = StrategySelector(switch_threshold=0.5)
        
        assert selector.switch_threshold == 0.5
    
    def test_min_samples_custom(self):
        """Test custom minimum samples"""
        selector = StrategySelector(min_samples_before_switch=10)
        
        assert selector.min_samples_before_switch == 10


class TestStrategySwitchEvent:
    """Test StrategySwitchEvent dataclass"""
    
    def test_switch_event_creation(self):
        """Test creating a switch event"""
        event = StrategySwitchEvent(
            timestamp=datetime.now(),
            from_strategy=ReasoningStrategy.BALANCED,
            to_strategy=ReasoningStrategy.CONSERVATIVE,
            reason="Test reason",
            context={"key": "value"}
        )
        
        assert isinstance(event.timestamp, datetime)
        assert event.from_strategy == ReasoningStrategy.BALANCED
        assert event.to_strategy == ReasoningStrategy.CONSERVATIVE
        assert event.reason == "Test reason"
        assert event.context == {"key": "value"}
        assert event.success is False  # Default value
        assert event.time_to_validate == 0.0  # Default value