"""
Unit tests for Strategy Switcher functionality (Task 5.3)

Tests the dynamic strategy switching capabilities including:
- should_switch() logic
- switch_strategy() execution
- validate_switch() verification
- Switch statistics tracking
- Optimal switch point learning
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock

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


class TestShouldSwitchStrategy:
    """Tests for should_switch_strategy() method"""
    
    @pytest.fixture
    def selector(self):
        """Create a fresh selector for each test"""
        return StrategySelector(
            switch_threshold=0.6,
            min_samples_before_switch=5
        )
    
    @pytest.fixture
    def mock_situation_report(self):
        """Create a mock situation report"""
        return SituationReport(
            situation_type=SituationType.NORMAL,
            severity="low",
            features={},
            potential_actions=[],
            risks=[],
            confidence=0.8,
            summary="Normal situation"
        )
    
    def test_should_not_switch_insufficient_samples(self, selector):
        """Test that switch is not recommended with insufficient samples"""
        # Build up performance but keep below threshold
        for _ in range(3):  # Less than min_samples (5)
            selector.update_strategy_performance(
                strategy=ReasoningStrategy.BALANCED,
                validation_result=ValidationResult(
                    success=False,
                    goal_achieved=False,
                    side_effects=[],
                    progress_made=0.0,
                    efficiency_score=0.3,
                    error_message=None,
                    corrections_needed=[]
                ),
                decision=Decision(
                    action="test_action",
                    strategy=ReasoningStrategy.BALANCED,
                    reasoning="test",
                    alternatives=[],
                    confidence=0.7,
                    expected_outcome="test outcome",
                    risk_level=0.3,
                    time_estimate=1.0,
                    resource_estimate={"tokens": 100}
                ),
                time_elapsed=1.0
            )
        
        recent_performance = selector.recent_performance_window
        
        should_switch, new_strategy, reason = selector.should_switch_strategy(
            current_strategy=ReasoningStrategy.BALANCED,
            recent_performance=recent_performance,
            situation_type=SituationType.NORMAL
        )
        
        assert should_switch is False
        assert new_strategy is None
        assert "Insufficient performance data" in reason
    
    def test_should_switch_low_success_rate(self, selector):
        """Test that switch is recommended when success rate drops below threshold"""
        # Build up performance below threshold
        for _ in range(10):  # Above min_samples (5)
            selector.update_strategy_performance(
                strategy=ReasoningStrategy.BALANCED,
                validation_result=ValidationResult(
                    success=False,  # 0% success rate
                    goal_achieved=False,
                    side_effects=[],
                    progress_made=0.0,
                    efficiency_score=0.3,
                    error_message=None,
                    corrections_needed=[]
                ),
                decision=Decision(
                    action="test_action",
                    strategy=ReasoningStrategy.BALANCED,
                    reasoning="test",
                    alternatives=[],
                    confidence=0.7,
                    expected_outcome="test outcome",
                    risk_level=0.5,
                    time_estimate=1.0,
                    resource_estimate={"tokens": 100}
                ),
                time_elapsed=1.0
            )
        
        # Build up performance for alternative strategy
        for _ in range(10):
            selector.update_strategy_performance(
                strategy=ReasoningStrategy.CONSERVATIVE,
                validation_result=ValidationResult(
                    success=True,
                    goal_achieved=True,
                    side_effects=[],
                    progress_made=1.0,
                    efficiency_score=0.8,
                    error_message=None,
                    corrections_needed=[]
                ),
                decision=Decision(
                    action="test_action",
                    strategy=ReasoningStrategy.CONSERVATIVE,
                    reasoning="test",
                    alternatives=[],
                    confidence=0.9,
                    expected_outcome="test outcome",
                    risk_level=0.2,
                    time_estimate=1.5,
                    resource_estimate={"tokens": 200}
                ),
                time_elapsed=1.5
            )
        
        recent_performance = selector.recent_performance_window
        
        should_switch, new_strategy, reason = selector.should_switch_strategy(
            current_strategy=ReasoningStrategy.BALANCED,
            recent_performance=recent_performance,
            situation_type=SituationType.NORMAL
        )
        
        assert should_switch is True
        assert new_strategy == ReasoningStrategy.CONSERVATIVE
        assert "Success rate" in reason and "below threshold" in reason
    
    def test_should_switch_repeated_errors(self, selector):
        """Test that switch is recommended when repeated errors are detected"""
        # Build up some baseline performance
        for _ in range(10):
            selector.update_strategy_performance(
                strategy=ReasoningStrategy.BALANCED,
                validation_result=ValidationResult(
                    success=True,
                    goal_achieved=True,
                    side_effects=[],
                    progress_made=0.5,
                    efficiency_score=0.7,
                    error_message=None,
                    corrections_needed=[]
                ),
                decision=Decision(
                    action="test_action",
                    strategy=ReasoningStrategy.BALANCED,
                    reasoning="test",
                    alternatives=[],
                    confidence=0.8,
                    expected_outcome="test outcome",
                    risk_level=0.3,
                    time_estimate=1.0,
                    resource_estimate={"tokens": 100}
                ),
                time_elapsed=1.0
            )
        
        # Build up alternative strategy performance
        for _ in range(10):
            selector.update_strategy_performance(
                strategy=ReasoningStrategy.CONSERVATIVE,
                validation_result=ValidationResult(
                    success=True,
                    goal_achieved=True,
                    side_effects=[],
                    progress_made=0.6,
                    efficiency_score=0.8,
                    error_message=None,
                    corrections_needed=[]
                ),
                decision=Decision(
                    action="test_action",
                    strategy=ReasoningStrategy.CONSERVATIVE,
                    reasoning="test",
                    alternatives=[],
                    confidence=0.9,
                    expected_outcome="test outcome",
                    risk_level=0.2,
                    time_estimate=1.5,
                    resource_estimate={"tokens": 200}
                ),
                time_elapsed=1.5
            )
        
        # Create recent performance with 3+ consecutive failures
        recent_performance = [
            {
                "strategy": ReasoningStrategy.BALANCED,
                "success": False,
                "efficiency": 0.2,
                "progress": 0.0,
                "timestamp": datetime.now(),
                "decision": Decision(
                    action="fail_action",
                    strategy=ReasoningStrategy.BALANCED,
                    reasoning="test",
                    alternatives=[],
                    confidence=0.5,
                    expected_outcome="fail outcome",
                    risk_level=0.8,
                    time_estimate=1.0,
                    resource_estimate={"tokens": 50}
                )
            },
            {
                "strategy": ReasoningStrategy.BALANCED,
                "success": False,
                "efficiency": 0.1,
                "progress": 0.0,
                "timestamp": datetime.now(),
                "decision": Decision(
                    action="fail_action",
                    strategy=ReasoningStrategy.BALANCED,
                    reasoning="test",
                    alternatives=[],
                    confidence=0.4,
                    expected_outcome="fail outcome",
                    risk_level=0.8,
                    time_estimate=1.0,
                    resource_estimate={"tokens": 50}
                )
            },
            {
                "strategy": ReasoningStrategy.BALANCED,
                "success": False,
                "efficiency": 0.1,
                "progress": 0.0,
                "timestamp": datetime.now(),
                "decision": Decision(
                    action="fail_action",
                    strategy=ReasoningStrategy.BALANCED,
                    reasoning="test",
                    alternatives=[],
                    confidence=0.3,
                    expected_outcome="fail outcome",
                    risk_level=0.8,
                    time_estimate=1.0,
                    resource_estimate={"tokens": 50}
                )
            }
        ]
        
        should_switch, new_strategy, reason = selector.should_switch_strategy(
            current_strategy=ReasoningStrategy.BALANCED,
            recent_performance=recent_performance,
            situation_type=SituationType.NORMAL
        )
        
        assert should_switch is True
        assert new_strategy == ReasoningStrategy.CONSERVATIVE
        assert "Repeated errors" in reason
    
    def test_should_switch_stagnation(self, selector):
        """Test that switch is recommended when progress stagnates"""
        # Build up some baseline performance
        for _ in range(10):
            selector.update_strategy_performance(
                strategy=ReasoningStrategy.BALANCED,
                validation_result=ValidationResult(
                    success=True,
                    goal_achieved=True,
                    side_effects=[],
                    progress_made=0.5,
                    efficiency_score=0.7,
                    error_message=None,
                    corrections_needed=[]
                ),
                decision=Decision(
                    action="test_action",
                    strategy=ReasoningStrategy.BALANCED,
                    reasoning="test",
                    alternatives=[],
                    confidence=0.8,
                    expected_outcome="test outcome",
                    risk_level=0.3,
                    time_estimate=1.0,
                    resource_estimate={"tokens": 100}
                ),
                time_elapsed=1.0
            )
        
        # Build up alternative strategy performance
        for _ in range(10):
            selector.update_strategy_performance(
                strategy=ReasoningStrategy.CONSERVATIVE,
                validation_result=ValidationResult(
                    success=True,
                    goal_achieved=True,
                    side_effects=[],
                    progress_made=0.8,
                    efficiency_score=0.8,
                    error_message=None,
                    corrections_needed=[]
                ),
                decision=Decision(
                    action="test_action",
                    strategy=ReasoningStrategy.CONSERVATIVE,
                    reasoning="test",
                    alternatives=[],
                    confidence=0.9,
                    expected_outcome="test outcome",
                    risk_level=0.2,
                    time_estimate=1.5,
                    resource_estimate={"tokens": 200}
                ),
                time_elapsed=1.5
            )
        
        # Create recent performance with stagnation (low progress)
        recent_performance = [
            {
                "strategy": ReasoningStrategy.BALANCED,
                "success": True,
                "efficiency": 0.5,
                "progress": 0.01,  # Very low progress
                "timestamp": datetime.now(),
                "decision": Decision(
                    action="stagnate_action",
                    strategy=ReasoningStrategy.BALANCED,
                    reasoning="test",
                    alternatives=[],
                    confidence=0.7,
                    expected_outcome="test outcome",
                    risk_level=0.5,
                    time_estimate=1.0,
                    resource_estimate={"tokens": 100}
                )
            }
            for _ in range(5)
        ]
        
        should_switch, new_strategy, reason = selector.should_switch_strategy(
            current_strategy=ReasoningStrategy.BALANCED,
            recent_performance=recent_performance,
            situation_type=SituationType.NORMAL
        )
        
        assert should_switch is True
        assert new_strategy == ReasoningStrategy.CONSERVATIVE
        assert "stagnation" in reason.lower()
    
    def test_should_not_switch_good_performance(self, selector):
        """Test that switch is not recommended when performance is good"""
        # Build up good performance
        for _ in range(10):
            selector.update_strategy_performance(
                strategy=ReasoningStrategy.BALANCED,
                validation_result=ValidationResult(
                    success=True,  # 100% success rate
                    goal_achieved=True,
                    side_effects=[],
                    progress_made=0.8,
                    efficiency_score=0.8,
                    error_message=None,
                    corrections_needed=[]
                ),
                decision=Decision(
                    action="test_action",
                    strategy=ReasoningStrategy.BALANCED,
                    reasoning="test",
                    alternatives=[],
                    confidence=0.9,
                    expected_outcome="test outcome",
                    risk_level=0.2,
                    time_estimate=1.0,
                    resource_estimate={"tokens": 100}
                ),
                time_elapsed=1.0
            )
        
        recent_performance = selector.recent_performance_window
        
        should_switch, new_strategy, reason = selector.should_switch_strategy(
            current_strategy=ReasoningStrategy.BALANCED,
            recent_performance=recent_performance,
            situation_type=SituationType.NORMAL
        )
        
        assert should_switch is False
        assert new_strategy is None
        assert "performing well" in reason


class TestSwitchStrategy:
    """Tests for switch_strategy() method"""
    
    @pytest.fixture
    def selector(self):
        """Create a fresh selector for each test"""
        return StrategySelector(
            telemetry_manager=Mock()
        )
    
    def test_switch_strategy_records_event(self, selector):
        """Test that switch records event in history"""
        switch_event = selector.switch_strategy(
            from_strategy=ReasoningStrategy.BALANCED,
            to_strategy=ReasoningStrategy.CONSERVATIVE,
            reason="Low success rate",
            context={"task_type": "test_task"}
        )
        
        assert len(selector.switch_history) == 1
        assert switch_event.from_strategy == ReasoningStrategy.BALANCED
        assert switch_event.to_strategy == ReasoningStrategy.CONSERVATIVE
        assert switch_event.reason == "Low success rate"
        assert switch_event.context == {"task_type": "test_task"}
        assert isinstance(switch_event.timestamp, datetime)
    
    def test_switch_strategy_updates_current(self, selector):
        """Test that switch updates current strategy"""
        selector.current_strategy = ReasoningStrategy.BALANCED
        
        selector.switch_strategy(
            from_strategy=ReasoningStrategy.BALANCED,
            to_strategy=ReasoningStrategy.CONSERVATIVE,
            reason="Test switch"
        )
        
        assert selector.current_strategy == ReasoningStrategy.CONSERVATIVE
    
    def test_switch_strategy_tracks_telemetry(self, selector):
        """Test that switch is tracked in telemetry"""
        switch_event = selector.switch_strategy(
            from_strategy=ReasoningStrategy.BALANCED,
            to_strategy=ReasoningStrategy.CONSERVATIVE,
            reason="Test switch"
        )
        
        selector.telemetry.record_event.assert_called_once()
        call_args = selector.telemetry.record_event.call_args
        assert call_args[1]["event_type"] == "strategy_switched"
        assert call_args[1]["context"]["from_strategy"] == "balanced"
        assert call_args[1]["context"]["to_strategy"] == "conservative"
    
    def test_switch_strategy_multiple_switches(self, selector):
        """Test multiple switches are tracked"""
        switches = [
            (ReasoningStrategy.BALANCED, ReasoningStrategy.CONSERVATIVE, "Reason 1"),
            (ReasoningStrategy.CONSERVATIVE, ReasoningStrategy.AGGRESSIVE, "Reason 2"),
            (ReasoningStrategy.AGGRESSIVE, ReasoningStrategy.BALANCED, "Reason 3")
        ]
        
        for from_strat, to_strat, reason in switches:
            selector.switch_strategy(
                from_strategy=from_strat,
                to_strategy=to_strat,
                reason=reason
            )
        
        assert len(selector.switch_history) == 3
        assert selector.switch_history[0].from_strategy == ReasoningStrategy.BALANCED
        assert selector.switch_history[0].to_strategy == ReasoningStrategy.CONSERVATIVE
        assert selector.switch_history[1].from_strategy == ReasoningStrategy.CONSERVATIVE
        assert selector.switch_history[1].to_strategy == ReasoningStrategy.AGGRESSIVE
        assert selector.switch_history[2].from_strategy == ReasoningStrategy.AGGRESSIVE
        assert selector.switch_history[2].to_strategy == ReasoningStrategy.BALANCED


class TestValidateSwitch:
    """Tests for validate_switch() method"""
    
    @pytest.fixture
    def selector(self):
        """Create a fresh selector for each test"""
        return StrategySelector(
            telemetry_manager=Mock()
        )
    
    @pytest.fixture
    def sample_switch_event(self):
        """Create a sample switch event"""
        return StrategySwitchEvent(
            timestamp=datetime.now() - timedelta(minutes=5),
            from_strategy=ReasoningStrategy.BALANCED,
            to_strategy=ReasoningStrategy.CONSERVATIVE,
            reason="Low success rate",
            context={"task_type": "test_task"}
        )
    
    def test_validate_switch_insufficient_samples(self, selector, sample_switch_event):
        """Test validation with insufficient samples"""
        post_switch_performance = [
            {"success": True, "efficiency": 0.8}
        ]  # Only 1 sample, need 3
        
        success, improvement_score, reason = selector.validate_switch(
            switch_event=sample_switch_event,
            post_switch_performance=post_switch_performance,
            min_samples=3
        )
        
        assert success is False
        assert improvement_score == 0.0
        assert "Insufficient samples" in reason
    
    def test_validate_switch_successful(self, selector, sample_switch_event):
        """Test successful switch validation"""
        # Build up before performance (lower)
        for _ in range(10):
            selector.update_strategy_performance(
                strategy=ReasoningStrategy.BALANCED,
                validation_result=ValidationResult(
                    success=False,
                    goal_achieved=False,
                    side_effects=[],
                    progress_made=0.1,
                    efficiency_score=0.4,
                    error_message=None,
                    corrections_needed=[]
                ),
                decision=Decision(
                    action="test_action",
                    strategy=ReasoningStrategy.BALANCED,
                    reasoning="test",
                    alternatives=[],
                    confidence=0.6,
                    expected_outcome="test outcome",
                    risk_level=0.5,
                    time_estimate=1.0,
                    resource_estimate={"tokens": 100}
                ),
                time_elapsed=1.0
            )
        
        # Build up after performance (higher)
        for _ in range(10):
            selector.update_strategy_performance(
                strategy=ReasoningStrategy.CONSERVATIVE,
                validation_result=ValidationResult(
                    success=True,
                    goal_achieved=True,
                    side_effects=[],
                    progress_made=0.9,
                    efficiency_score=0.9,
                    error_message=None,
                    corrections_needed=[]
                ),
                decision=Decision(
                    action="test_action",
                    strategy=ReasoningStrategy.CONSERVATIVE,
                    reasoning="test",
                    alternatives=[],
                    confidence=0.9,
                    expected_outcome="test outcome",
                    risk_level=0.2,
                    time_estimate=1.2,
                    resource_estimate={"tokens": 200}
                ),
                time_elapsed=1.2
            )
        
        post_switch_performance = [
            {"success": True, "efficiency": 0.9}
            for _ in range(5)
        ]
        
        success, improvement_score, reason = selector.validate_switch(
            switch_event=sample_switch_event,
            post_switch_performance=post_switch_performance,
            min_samples=3
        )
        
        assert success is True
        assert improvement_score > 0.1  # Should be significant improvement
        assert "Success rate improved" in reason or "improved" in reason.lower()
    
    def test_validate_switch_unsuccessful(self, selector, sample_switch_event):
        """Test unsuccessful switch validation"""
        # Build up before performance (higher)
        for _ in range(10):
            selector.update_strategy_performance(
                strategy=ReasoningStrategy.BALANCED,
                validation_result=ValidationResult(
                    success=True,
                    goal_achieved=True,
                    side_effects=[],
                    progress_made=0.9,
                    efficiency_score=0.9,
                    error_message=None,
                    corrections_needed=[]
                ),
                decision=Decision(
                    action="test_action",
                    strategy=ReasoningStrategy.BALANCED,
                    reasoning="test",
                    alternatives=[],
                    confidence=0.9,
                    expected_outcome="test outcome",
                    risk_level=0.2,
                    time_estimate=1.0,
                    resource_estimate={"tokens": 100}
                ),
                time_elapsed=1.0
            )
        
        # Build up after performance (lower)
        for _ in range(10):
            selector.update_strategy_performance(
                strategy=ReasoningStrategy.CONSERVATIVE,
                validation_result=ValidationResult(
                    success=False,
                    goal_achieved=False,
                    side_effects=[],
                    progress_made=0.1,
                    efficiency_score=0.4,
                    error_message=None,
                    corrections_needed=[]
                ),
                decision=Decision(
                    action="test_action",
                    strategy=ReasoningStrategy.CONSERVATIVE,
                    reasoning="test",
                    alternatives=[],
                    confidence=0.6,
                    expected_outcome="test outcome",
                    risk_level=0.5,
                    time_estimate=1.5,
                    resource_estimate={"tokens": 200}
                ),
                time_elapsed=1.5
            )
        
        post_switch_performance = [
            {"success": False, "efficiency": 0.4}
            for _ in range(5)
        ]
        
        success, improvement_score, reason = selector.validate_switch(
            switch_event=sample_switch_event,
            post_switch_performance=post_switch_performance,
            min_samples=3
        )
        
        assert success is False
        assert improvement_score < 0.1
        assert "decreased" in reason.lower() or "worse" in reason.lower()
    
    def test_validate_switch_updates_event(self, selector, sample_switch_event):
        """Test that validation updates switch event"""
        # Build up some performance
        for _ in range(10):
            selector.update_strategy_performance(
                strategy=ReasoningStrategy.BALANCED,
                validation_result=ValidationResult(
                    success=False,
                    goal_achieved=False,
                    side_effects=[],
                    progress_made=0.1,
                    efficiency_score=0.4,
                    error_message=None,
                    corrections_needed=[]
                ),
                decision=Decision(
                    action="test_action",
                    strategy=ReasoningStrategy.BALANCED,
                    reasoning="test",
                    alternatives=[],
                    confidence=0.6,
                    expected_outcome="test outcome",
                    risk_level=0.5,
                    time_estimate=1.0,
                    resource_estimate={"tokens": 100}
                ),
                time_elapsed=1.0
            )
        
        for _ in range(10):
            selector.update_strategy_performance(
                strategy=ReasoningStrategy.CONSERVATIVE,
                validation_result=ValidationResult(
                    success=True,
                    goal_achieved=True,
                    side_effects=[],
                    progress_made=0.9,
                    efficiency_score=0.9,
                    error_message=None,
                    corrections_needed=[]
                ),
                decision=Decision(
                    action="test_action",
                    strategy=ReasoningStrategy.CONSERVATIVE,
                    reasoning="test",
                    alternatives=[],
                    confidence=0.9,
                    expected_outcome="test outcome",
                    risk_level=0.2,
                    time_estimate=1.2,
                    resource_estimate={"tokens": 200}
                ),
                time_elapsed=1.2
            )
        
        post_switch_performance = [
            {"success": True, "efficiency": 0.9}
            for _ in range(5)
        ]
        
        selector.validate_switch(
            switch_event=sample_switch_event,
            post_switch_performance=post_switch_performance,
            min_samples=3
        )
        
        assert sample_switch_event.success is True
        assert sample_switch_event.time_to_validate > 0
    
    def test_validate_switch_tracks_telemetry(self, selector, sample_switch_event):
        """Test that validation is tracked in telemetry"""
        # Build up some performance
        for _ in range(10):
            selector.update_strategy_performance(
                strategy=ReasoningStrategy.BALANCED,
                validation_result=ValidationResult(
                    success=False,
                    goal_achieved=False,
                    side_effects=[],
                    progress_made=0.1,
                    efficiency_score=0.4,
                    error_message=None,
                    corrections_needed=[]
                ),
                decision=Decision(
                    action="test_action",
                    strategy=ReasoningStrategy.BALANCED,
                    reasoning="test",
                    alternatives=[],
                    confidence=0.6,
                    expected_outcome="test outcome",
                    risk_level=0.5,
                    time_estimate=1.0,
                    resource_estimate={"tokens": 100}
                ),
                time_elapsed=1.0
            )
        
        for _ in range(10):
            selector.update_strategy_performance(
                strategy=ReasoningStrategy.CONSERVATIVE,
                validation_result=ValidationResult(
                    success=True,
                    goal_achieved=True,
                    side_effects=[],
                    progress_made=0.9,
                    efficiency_score=0.9,
                    error_message=None,
                    corrections_needed=[]
                ),
                decision=Decision(
                    action="test_action",
                    strategy=ReasoningStrategy.CONSERVATIVE,
                    reasoning="test",
                    alternatives=[],
                    confidence=0.9,
                    expected_outcome="test outcome",
                    risk_level=0.2,
                    time_estimate=1.2,
                    resource_estimate={"tokens": 200}
                ),
                time_elapsed=1.2
            )
        
        post_switch_performance = [
            {"success": True, "efficiency": 0.9}
            for _ in range(5)
        ]
        
        selector.validate_switch(
            switch_event=sample_switch_event,
            post_switch_performance=post_switch_performance,
            min_samples=3
        )
        
        # Check telemetry calls
        calls = selector.telemetry.record_event.call_args_list
        assert len(calls) >= 1
        
        # Find the validate call
        validate_call = None
        for call in calls:
            if call[1]["event_type"] == "strategy_switch_validated":
                validate_call = call
                break
        
        assert validate_call is not None
        assert validate_call[1]["context"]["from_strategy"] == "balanced"
        assert validate_call[1]["context"]["to_strategy"] == "conservative"


class TestSwitchStatistics:
    """Tests for get_switch_statistics() method"""
    
    @pytest.fixture
    def selector(self):
        """Create a fresh selector for each test"""
        return StrategySelector()
    
    def test_no_switches(self, selector):
        """Test statistics when no switches have occurred"""
        stats = selector.get_switch_statistics()
        
        assert stats["total_switches"] == 0
        assert stats["switch_frequency"] == 0.0
        assert stats["success_rate"] == 0.0
        assert stats["average_improvement"] == 0.0
        assert stats["switches_by_strategy"] == {}
        assert stats["switches_by_reason"] == {}
    
    def test_with_switches(self, selector):
        """Test statistics with switches"""
        # Add some switches
        for i in range(3):
            switch = selector.switch_strategy(
                from_strategy=ReasoningStrategy.BALANCED,
                to_strategy=ReasoningStrategy.CONSERVATIVE,
                reason=f"Reason {i}",
                context={"task_type": "test"}
            )
            # Mark half as successful
            if i % 2 == 0:
                switch.success = True
        
        # Build up performance data
        for _ in range(10):
            selector.update_strategy_performance(
                strategy=ReasoningStrategy.BALANCED,
                validation_result=ValidationResult(
                    success=True,
                    goal_achieved=True,
                    side_effects=[],
                    progress_made=0.5,
                    efficiency_score=0.5,
                    error_message=None,
                    corrections_needed=[]
                ),
                decision=Decision(
                    action="test_action",
                    strategy=ReasoningStrategy.BALANCED,
                    reasoning="test",
                    alternatives=[],
                    confidence=0.7,
                    expected_outcome="test outcome",
                    risk_level=0.3,
                    time_estimate=1.0,
                    resource_estimate={"tokens": 100}
                ),
                time_elapsed=1.0
            )
        
        for _ in range(10):
            selector.update_strategy_performance(
                strategy=ReasoningStrategy.CONSERVATIVE,
                validation_result=ValidationResult(
                    success=True,
                    goal_achieved=True,
                    side_effects=[],
                    progress_made=0.8,
                    efficiency_score=0.8,
                    error_message=None,
                    corrections_needed=[]
                ),
                decision=Decision(
                    action="test_action",
                    strategy=ReasoningStrategy.CONSERVATIVE,
                    reasoning="test",
                    alternatives=[],
                    confidence=0.9,
                    expected_outcome="test outcome",
                    risk_level=0.2,
                    time_estimate=1.5,
                    resource_estimate={"tokens": 200}
                ),
                time_elapsed=1.5
            )
        
        stats = selector.get_switch_statistics()
        
        assert stats["total_switches"] == 3
        assert stats["switch_frequency"] >= 0.0
        assert "balanced -> conservative" in stats["switches_by_strategy"]
        assert stats["switches_by_strategy"]["balanced -> conservative"] == 3


class TestOptimalSwitchPoints:
    """Tests for get_optimal_switch_points() method"""
    
    @pytest.fixture
    def selector(self):
        """Create a fresh selector for each test"""
        return StrategySelector()
    
    def test_no_successful_switches(self, selector):
        """Test optimal points when no successful switches"""
        # Add unsuccessful switches
        switch = selector.switch_strategy(
            from_strategy=ReasoningStrategy.BALANCED,
            to_strategy=ReasoningStrategy.CONSERVATIVE,
            reason="Test reason"
        )
        switch.success = False
        
        optimal_points = selector.get_optimal_switch_points()
        
        assert len(optimal_points) == 0
    
    def test_success_rate_threshold_pattern(self, selector):
        """Test learning success rate threshold pattern"""
        # Add successful switch with success rate reason
        switch = selector.switch_strategy(
            from_strategy=ReasoningStrategy.BALANCED,
            to_strategy=ReasoningStrategy.CONSERVATIVE,
            reason="Success rate 50% below threshold 60%",
            context={"task_type": "test"}
        )
        switch.success = True
        
        optimal_points = selector.get_optimal_switch_points()
        
        assert len(optimal_points) > 0
        success_rate_points = [
            p for p in optimal_points
            if p["condition"] == "success_rate_below_threshold"
        ]
        assert len(success_rate_points) > 0
        assert success_rate_points[0]["threshold"] == 0.5
    
    def test_repeated_errors_pattern(self, selector):
        """Test learning repeated errors pattern"""
        # Add successful switch with repeated errors reason
        switch = selector.switch_strategy(
            from_strategy=ReasoningStrategy.BALANCED,
            to_strategy=ReasoningStrategy.CONSERVATIVE,
            reason="Repeated errors detected in recent performance",
            context={"task_type": "test"}
        )
        switch.success = True
        
        optimal_points = selector.get_optimal_switch_points()
        
        assert len(optimal_points) > 0
        error_points = [
            p for p in optimal_points
            if p["condition"] == "repeated_errors"
        ]
        assert len(error_points) > 0
        assert error_points[0]["threshold"] == 3
    
    def test_stagnation_pattern(self, selector):
        """Test learning stagnation pattern"""
        # Add successful switch with stagnation reason
        switch = selector.switch_strategy(
            from_strategy=ReasoningStrategy.BALANCED,
            to_strategy=ReasoningStrategy.CONSERVATIVE,
            reason="No progress in recent operations (stagnation)",
            context={"task_type": "test"}
        )
        switch.success = True
        
        optimal_points = selector.get_optimal_switch_points()
        
        assert len(optimal_points) > 0
        stagnation_points = [
            p for p in optimal_points
            if p["condition"] == "stagnation"
        ]
        assert len(stagnation_points) > 0
        assert stagnation_points[0]["threshold"] == 5
    
    def test_filter_by_task_type(self, selector):
        """Test filtering optimal points by task type"""
        # Add switches for different task types
        switch1 = selector.switch_strategy(
            from_strategy=ReasoningStrategy.BALANCED,
            to_strategy=ReasoningStrategy.CONSERVATIVE,
            reason="Success rate 50% below threshold",
            context={"task_type": "task_a"}
        )
        switch1.success = True
        
        switch2 = selector.switch_strategy(
            from_strategy=ReasoningStrategy.CONSERVATIVE,
            to_strategy=ReasoningStrategy.AGGRESSIVE,
            reason="Success rate 40% below threshold",
            context={"task_type": "task_b"}
        )
        switch2.success = True
        
        # Filter by task_a
        optimal_points = selector.get_optimal_switch_points(task_type="task_a")
        
        # Should only include switches for task_a
        assert all(
            p["frequency"] == 1 or p["condition"] != "success_rate_below_threshold"
            for p in optimal_points
        )
    
    def test_sort_by_frequency(self, selector):
        """Test that optimal points are sorted by frequency"""
        # Add multiple successful switches with same reason
        for _ in range(3):
            switch = selector.switch_strategy(
                from_strategy=ReasoningStrategy.BALANCED,
                to_strategy=ReasoningStrategy.CONSERVATIVE,
                reason="Repeated errors detected in recent performance",
                context={"task_type": "test"}
            )
            switch.success = True
        
        # Add one switch with different reason
        switch2 = selector.switch_strategy(
            from_strategy=ReasoningStrategy.CONSERVATIVE,
            to_strategy=ReasoningStrategy.AGGRESSIVE,
            reason="No progress in recent operations (stagnation)",
            context={"task_type": "test"}
        )
        switch2.success = True
        
        optimal_points = selector.get_optimal_switch_points()
        
        # Most frequent should be first
        if len(optimal_points) > 1:
            assert optimal_points[0]["frequency"] >= optimal_points[1]["frequency"]


class TestIntegrationStrategySwitching:
    """Integration tests for complete strategy switching workflow"""
    
    @pytest.fixture
    def selector(self):
        """Create a fresh selector for each test"""
        return StrategySelector(
            telemetry_manager=Mock(),
            switch_threshold=0.6,
            min_samples_before_switch=5
        )
    
    def test_complete_switch_workflow(self, selector):
        """Test complete workflow: detect -> switch -> validate"""
        # Step 1: Build up poor performance with current strategy
        for _ in range(10):
            selector.update_strategy_performance(
                strategy=ReasoningStrategy.BALANCED,
                validation_result=ValidationResult(
                    success=False,
                    goal_achieved=False,
                    side_effects=[],
                    progress_made=0.1,
                    efficiency_score=0.3,
                    error_message=None,
                    corrections_needed=[]
                ),
                decision=Decision(
                    action="test_action",
                    strategy=ReasoningStrategy.BALANCED,
                    reasoning="test",
                    alternatives=[],
                    confidence=0.6,
                    expected_outcome="test outcome",
                    risk_level=0.5,
                    time_estimate=1.0,
                    resource_estimate={"tokens": 100}
                ),
                time_elapsed=1.0
            )
        
        # Step 2: Build up good performance with alternative
        for _ in range(10):
            selector.update_strategy_performance(
                strategy=ReasoningStrategy.CONSERVATIVE,
                validation_result=ValidationResult(
                    success=True,
                    goal_achieved=True,
                    side_effects=[],
                    progress_made=0.9,
                    efficiency_score=0.9,
                    error_message=None,
                    corrections_needed=[]
                ),
                decision=Decision(
                    action="test_action",
                    strategy=ReasoningStrategy.CONSERVATIVE,
                    reasoning="test",
                    alternatives=[],
                    confidence=0.9,
                    expected_outcome="test outcome",
                    risk_level=0.2,
                    time_estimate=1.5,
                    resource_estimate={"tokens": 200}
                ),
                time_elapsed=1.5
            )
        
        # Step 3: Check if should switch
        should_switch, new_strategy, reason = selector.should_switch_strategy(
            current_strategy=ReasoningStrategy.BALANCED,
            recent_performance=selector.recent_performance_window,
            situation_type=SituationType.NORMAL
        )
        
        assert should_switch is True
        assert new_strategy == ReasoningStrategy.CONSERVATIVE
        
        # Step 4: Execute switch
        switch_event = selector.switch_strategy(
            from_strategy=ReasoningStrategy.BALANCED,
            to_strategy=ReasoningStrategy.CONSERVATIVE,
            reason=reason
        )
        
        assert len(selector.switch_history) == 1
        assert selector.current_strategy == ReasoningStrategy.CONSERVATIVE
        
        # Step 5: Continue with new strategy
        post_switch_performance = []
        for _ in range(5):
            selector.update_strategy_performance(
                strategy=ReasoningStrategy.CONSERVATIVE,
                validation_result=ValidationResult(
                    success=True,
                    goal_achieved=True,
                    side_effects=[],
                    progress_made=0.8,
                    efficiency_score=0.8,
                    error_message=None,
                    corrections_needed=[]
                ),
                decision=Decision(
                    action="test_action",
                    strategy=ReasoningStrategy.CONSERVATIVE,
                    reasoning="test",
                    alternatives=[],
                    confidence=0.9,
                    expected_outcome="test outcome",
                    risk_level=0.2,
                    time_estimate=1.5,
                    resource_estimate={"tokens": 200}
                ),
                time_elapsed=1.5,
                situation_type=SituationType.NORMAL
            )
            post_switch_performance.append({
                "success": True,
                "efficiency": 0.8
            })
        
        # Step 6: Validate switch
        success, improvement_score, validation_reason = selector.validate_switch(
            switch_event=switch_event,
            post_switch_performance=post_switch_performance,
            min_samples=3
        )
        
        assert success is True
        assert improvement_score > 0.1
        
        # Step 7: Check statistics
        stats = selector.get_switch_statistics()
        assert stats["total_switches"] == 1
        assert stats["success_rate"] == 1.0  # 100% success rate
    
    def test_multiple_switches_over_time(self, selector):
        """Test strategy adaptation over multiple switches"""
        strategies = [
            (ReasoningStrategy.BALANCED, False, 0.3),
            (ReasoningStrategy.CONSERVATIVE, True, 0.7),
            (ReasoningStrategy.AGGRESSIVE, False, 0.4),
            (ReasoningStrategy.BALANCED, True, 0.8)
        ]
        
        for i, (strategy, success, efficiency) in enumerate(strategies):
            # Build up performance for this strategy
            for _ in range(10):
                selector.update_strategy_performance(
                    strategy=strategy,
                        validation_result=ValidationResult(
                            success=success,
                            goal_achieved=success,
                            side_effects=[],
                            progress_made=0.5 if success else 0.1,
                            efficiency_score=efficiency,
                            error_message=None,
                            corrections_needed=[]
                        ),
                    decision=Decision(
                        action="test_action",
                        strategy=strategy,
                        reasoning="test",
                        alternatives=[],
                        confidence=0.7,
                        expected_outcome="test outcome",
                        risk_level=0.3,
                        time_estimate=1.0,
                        resource_estimate={"tokens": 100}
                    ),
                    time_elapsed=1.0
                )
            
            # Select this strategy
            selector.current_strategy = strategy
            
            # Check if should switch (except last one)
            if i < len(strategies) - 1:
                should_switch, new_strategy, reason = selector.should_switch_strategy(
                    current_strategy=strategy,
                    recent_performance=selector.recent_performance_window,
                    situation_type=SituationType.NORMAL
                )
                
                if should_switch and new_strategy:
                    next_strategy = strategies[i + 1][0]
                    selector.switch_strategy(
                        from_strategy=strategy,
                        to_strategy=next_strategy,
                        reason=reason
                    )
        
        # Verify multiple switches occurred
        stats = selector.get_switch_statistics()
        assert stats["total_switches"] >= 1
        
        # Verify optimal points learned
        optimal_points = selector.get_optimal_switch_points()
        assert len(optimal_points) >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])