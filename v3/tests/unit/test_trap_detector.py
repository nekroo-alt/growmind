"""
Unit tests for Trap Detector module.

Tests trap type definitions, anti-pattern definitions, detection criteria,
recovery strategies, prevention strategies, and reporting functionality.
"""

import pytest
from v3.logic.trap_detector import (
    TrapType,
    AntiPatternType,
    TrapSeverity,
    TrapDefinition,
    AntiPatternDefinition,
    TrapDetection,
    TrapDetector,
    create_trap_detector
)


class TestTrapTypes:
    """Tests for TrapType enum."""
    
    def test_trap_type_values(self):
        """Test that all trap type values are defined."""
        assert TrapType.INFINITE_LOOP.value == "infinite_loop"
        assert TrapType.DEAD_END.value == "dead_end"
        assert TrapType.CIRCULAR_REASONING.value == "circular_reasoning"
        assert TrapType.SCOPE_CREEP.value == "scope_creep"
    
    def test_trap_type_count(self):
        """Test that we have exactly 4 trap types."""
        assert len(TrapType) == 4


class TestAntiPatternTypes:
    """Tests for AntiPatternType enum."""
    
    def test_anti_pattern_type_values(self):
        """Test that all anti-pattern type values are defined."""
        assert AntiPatternType.OVER_OPTIMIZATION.value == "over_optimization"
        assert AntiPatternType.PREMATURE_OPTIMIZATION.value == "premature_optimization"
        assert AntiPatternType.GOLD_PLATING.value == "gold_plating"
    
    def test_anti_pattern_type_count(self):
        """Test that we have exactly 3 anti-pattern types."""
        assert len(AntiPatternType) == 3


class TestTrapSeverity:
    """Tests for TrapSeverity enum."""
    
    def test_severity_values(self):
        """Test that all severity values are defined."""
        assert TrapSeverity.WARNING.value == "warning"
        assert TrapSeverity.CRITICAL.value == "critical"
        assert TrapSeverity.BLOCKING.value == "blocking"
    
    def test_severity_count(self):
        """Test that we have exactly 3 severity levels."""
        assert len(TrapSeverity) == 3


class TestTrapDetectorInitialization:
    """Tests for TrapDetector initialization."""
    
    def test_create_detector(self):
        """Test that detector can be created."""
        detector = TrapDetector()
        assert detector is not None
        assert isinstance(detector, TrapDetector)
    
    def test_factory_function(self):
        """Test factory function creates detector."""
        detector = create_trap_detector()
        assert detector is not None
        assert isinstance(detector, TrapDetector)
    
    def test_trap_definitions_initialized(self):
        """Test that trap definitions are initialized."""
        detector = TrapDetector()
        assert len(detector.trap_definitions) == 4
    
    def test_anti_pattern_definitions_initialized(self):
        """Test that anti-pattern definitions are initialized."""
        detector = TrapDetector()
        assert len(detector.anti_pattern_definitions) == 3


class TestTrapDefinitions:
    """Tests for individual trap definitions."""
    
    @pytest.fixture
    def detector(self):
        """Create detector for tests."""
        return TrapDetector()
    
    def test_infinite_loop_definition(self, detector):
        """Test infinite loop trap definition."""
        definition = detector.get_trap_definition(TrapType.INFINITE_LOOP)
        
        assert definition is not None
        assert definition.trap_type == TrapType.INFINITE_LOOP
        assert definition.name == "Infinite Loop"
        assert "repetition_threshold" in definition.detection_criteria
        assert definition.detection_criteria["repetition_threshold"] == 3
        assert len(definition.recovery_strategies) > 0
        assert len(definition.prevention_strategies) > 0
        assert len(definition.examples) > 0
    
    def test_dead_end_definition(self, detector):
        """Test dead end trap definition."""
        definition = detector.get_trap_definition(TrapType.DEAD_END)
        
        assert definition is not None
        assert definition.trap_type == TrapType.DEAD_END
        assert definition.name == "Dead End"
        assert "no_progress_threshold" in definition.detection_criteria
        assert definition.detection_criteria["no_progress_threshold"] == 5
        assert len(definition.recovery_strategies) > 0
        assert len(definition.prevention_strategies) > 0
        assert len(definition.examples) > 0
    
    def test_circular_reasoning_definition(self, detector):
        """Test circular reasoning trap definition."""
        definition = detector.get_trap_definition(TrapType.CIRCULAR_REASONING)
        
        assert definition is not None
        assert definition.trap_type == TrapType.CIRCULAR_REASONING
        assert definition.name == "Circular Reasoning"
        assert "decision_cycle_detected" in definition.detection_criteria
        assert len(definition.recovery_strategies) > 0
        assert len(definition.prevention_strategies) > 0
        assert len(definition.examples) > 0
    
    def test_scope_creep_definition(self, detector):
        """Test scope creep trap definition."""
        definition = detector.get_trap_definition(TrapType.SCOPE_CREEP)
        
        assert definition is not None
        assert definition.trap_type == TrapType.SCOPE_CREEP
        assert definition.name == "Scope Creep"
        assert "expansion_count_threshold" in definition.detection_criteria
        assert definition.detection_criteria["expansion_count_threshold"] == 3
        assert len(definition.recovery_strategies) > 0
        assert len(definition.prevention_strategies) > 0
        assert len(definition.examples) > 0


class TestAntiPatternDefinitions:
    """Tests for anti-pattern definitions."""
    
    @pytest.fixture
    def detector(self):
        """Create detector for tests."""
        return TrapDetector()
    
    def test_over_optimization_definition(self, detector):
        """Test over-optimization anti-pattern definition."""
        definition = detector.get_anti_pattern_definition(AntiPatternType.OVER_OPTIMIZATION)
        
        assert definition is not None
        assert definition.anti_pattern_type == AntiPatternType.OVER_OPTIMIZATION
        assert definition.name == "Over-Optimization"
        assert len(definition.symptoms) > 0
        assert len(definition.consequences) > 0
        assert len(definition.prevention) > 0
        assert len(definition.examples) > 0
    
    def test_premature_optimization_definition(self, detector):
        """Test premature optimization anti-pattern definition."""
        definition = detector.get_anti_pattern_definition(AntiPatternType.PREMATURE_OPTIMIZATION)
        
        assert definition is not None
        assert definition.anti_pattern_type == AntiPatternType.PREMATURE_OPTIMIZATION
        assert definition.name == "Premature Optimization"
        assert len(definition.symptoms) > 0
        assert len(definition.consequences) > 0
        assert len(definition.prevention) > 0
        assert len(definition.examples) > 0
    
    def test_gold_plating_definition(self, detector):
        """Test gold plating anti-pattern definition."""
        definition = detector.get_anti_pattern_definition(AntiPatternType.GOLD_PLATING)
        
        assert definition is not None
        assert definition.anti_pattern_type == AntiPatternType.GOLD_PLATING
        assert definition.name == "Gold Plating"
        assert len(definition.symptoms) > 0
        assert len(definition.consequences) > 0
        assert len(definition.prevention) > 0
        assert len(definition.examples) > 0


class TestDetectionCriteria:
    """Tests for detection criteria checking."""
    
    @pytest.fixture
    def detector(self):
        """Create detector for tests."""
        return TrapDetector()
    
    def test_check_numeric_criteria_meets_threshold(self, detector):
        """Test checking numeric criteria that meets threshold."""
        result = detector.check_detection_criteria(
            TrapType.INFINITE_LOOP,
            "repetition_threshold",
            3
        )
        assert result is True
    
    def test_check_numeric_criteria_below_threshold(self, detector):
        """Test checking numeric criteria below threshold."""
        result = detector.check_detection_criteria(
            TrapType.INFINITE_LOOP,
            "repetition_threshold",
            2
        )
        assert result is False
    
    def test_check_numeric_criteria_above_threshold(self, detector):
        """Test checking numeric criteria above threshold."""
        result = detector.check_detection_criteria(
            TrapType.INFINITE_LOOP,
            "repetition_threshold",
            5
        )
        assert result is True
    
    def test_check_boolean_criteria_true(self, detector):
        """Test checking boolean criteria with True."""
        result = detector.check_detection_criteria(
            TrapType.DEAD_END,
            "exhausted_options",
            True
        )
        assert result is True
    
    def test_check_boolean_criteria_false(self, detector):
        """Test checking boolean criteria with False."""
        result = detector.check_detection_criteria(
            TrapType.DEAD_END,
            "exhausted_options",
            False
        )
        assert result is False
    
    def test_check_unknown_criteria(self, detector):
        """Test checking unknown criteria returns False."""
        result = detector.check_detection_criteria(
            TrapType.INFINITE_LOOP,
            "unknown_criteria",
            5
        )
        assert result is False
    
    def test_check_unknown_trap_type(self, detector):
        """Test checking criteria for unknown trap type."""
        result = detector.check_detection_criteria(
            None,  # Invalid trap type
            "repetition_threshold",
            5
        )
        assert result is False


class TestRecoveryStrategies:
    """Tests for recovery strategies."""
    
    @pytest.fixture
    def detector(self):
        """Create detector for tests."""
        return TrapDetector()
    
    def test_get_recovery_strategies_for_loop(self, detector):
        """Test getting recovery strategies for infinite loop."""
        strategies = detector.get_recovery_strategies(TrapType.INFINITE_LOOP)
        
        assert isinstance(strategies, list)
        assert len(strategies) > 0
        assert "break_loop_change_approach" in strategies
        assert "backtrack_to_checkpoint" in strategies
    
    def test_get_recovery_strategies_for_dead_end(self, detector):
        """Test getting recovery strategies for dead end."""
        strategies = detector.get_recovery_strategies(TrapType.DEAD_END)
        
        assert isinstance(strategies, list)
        assert len(strategies) > 0
        assert "backtrack_to_last_success" in strategies
        assert "break_task_smaller" in strategies
    
    def test_get_recovery_strategies_for_unknown_trap(self, detector):
        """Test getting recovery strategies for unknown trap."""
        strategies = detector.get_recovery_strategies(None)
        
        assert isinstance(strategies, list)
        assert len(strategies) == 0


class TestPreventionStrategies:
    """Tests for prevention strategies."""
    
    @pytest.fixture
    def detector(self):
        """Create detector for tests."""
        return TrapDetector()
    
    def test_get_prevention_strategies_for_loop(self, detector):
        """Test getting prevention strategies for infinite loop."""
        strategies = detector.get_prevention_strategies(TrapType.INFINITE_LOOP)
        
        assert isinstance(strategies, list)
        assert len(strategies) > 0
        assert "track_attempted_actions" in strategies
        assert "warn_before_repetition" in strategies
    
    def test_get_prevention_strategies_for_circular_reasoning(self, detector):
        """Test getting prevention strategies for circular reasoning."""
        strategies = detector.get_prevention_strategies(TrapType.CIRCULAR_REASONING)
        
        assert isinstance(strategies, list)
        assert len(strategies) > 0
        assert "maintain_decision_history" in strategies
        assert "document_decision_rationale" in strategies
    
    def test_get_prevention_strategies_for_unknown_trap(self, detector):
        """Test getting prevention strategies for unknown trap."""
        strategies = detector.get_prevention_strategies(None)
        
        assert isinstance(strategies, list)
        assert len(strategies) == 0


class TestTrapExamples:
    """Tests for trap examples."""
    
    @pytest.fixture
    def detector(self):
        """Create detector for tests."""
        return TrapDetector()
    
    def test_get_examples_for_loop(self, detector):
        """Test getting examples for infinite loop."""
        examples = detector.get_examples(TrapType.INFINITE_LOOP)
        
        assert isinstance(examples, list)
        assert len(examples) > 0
        assert all(isinstance(ex, str) for ex in examples)
    
    def test_get_examples_for_scope_creep(self, detector):
        """Test getting examples for scope creep."""
        examples = detector.get_examples(TrapType.SCOPE_CREEP)
        
        assert isinstance(examples, list)
        assert len(examples) > 0
        assert all(isinstance(ex, str) for ex in examples)
    
    def test_get_examples_for_unknown_trap(self, detector):
        """Test getting examples for unknown trap."""
        examples = detector.get_examples(None)
        
        assert isinstance(examples, list)
        assert len(examples) == 0


class TestTrapReporting:
    """Tests for trap reporting functionality."""
    
    @pytest.fixture
    def detector(self):
        """Create detector for tests."""
        return TrapDetector()
    
    def test_format_trap_report(self, detector):
        """Test formatting trap detection report."""
        report = detector.format_trap_report(
            trap_type=TrapType.INFINITE_LOOP,
            severity=TrapSeverity.CRITICAL,
            confidence=0.85,
            evidence={"repetitions": 4, "window": 10}
        )
        
        assert isinstance(report, str)
        assert "Infinite Loop" in report
        assert "CRITICAL" in report
        assert "85.0%" in report
        assert "Recovery Strategies:" in report
        assert "Prevention Strategies:" in report
        assert "Evidence:" in report
        assert "repetitions: 4" in report
    
    def test_format_trap_report_unknown_trap(self, detector):
        """Test formatting report for unknown trap type."""
        report = detector.format_trap_report(
            trap_type=None,
            severity=TrapSeverity.WARNING,
            confidence=0.5,
            evidence={}
        )
        
        assert isinstance(report, str)
        assert "Unknown trap type" in report
    
    def test_get_trap_summary(self, detector):
        """Test getting trap summary."""
        summary = detector.get_trap_summary(TrapType.DEAD_END)
        
        assert isinstance(summary, str)
        assert "Dead End" in summary
        assert "criteria" in summary
        assert "strategies" in summary
    
    def test_get_trap_summary_unknown_trap(self, detector):
        """Test getting summary for unknown trap."""
        summary = detector.get_trap_summary(None)
        
        assert isinstance(summary, str)
        assert "Unknown trap type" in summary
    
    def test_get_all_trap_summaries(self, detector):
        """Test getting all trap summaries."""
        summaries = detector.get_all_trap_summaries()
        
        assert isinstance(summaries, str)
        assert "Trap Types Summary" in summaries
        assert "Infinite Loop" in summaries
        assert "Dead End" in summaries
        assert "Circular Reasoning" in summaries
        assert "Scope Creep" in summaries
    
    def test_get_all_anti_pattern_summaries(self, detector):
        """Test getting all anti-pattern summaries."""
        summaries = detector.get_all_anti_pattern_summaries()
        
        assert isinstance(summaries, str)
        assert "Anti-Patterns Summary" in summaries
        assert "Over-Optimization" in summaries
        assert "Premature Optimization" in summaries
        assert "Gold Plating" in summaries


class TestListTrapsAndPatterns:
    """Tests for listing traps and anti-patterns."""
    
    @pytest.fixture
    def detector(self):
        """Create detector for tests."""
        return TrapDetector()
    
    def test_list_all_traps(self, detector):
        """Test listing all trap definitions."""
        traps = detector.list_all_traps()
        
        assert isinstance(traps, list)
        assert len(traps) == 4
        assert all(isinstance(trap, TrapDefinition) for trap in traps)
    
    def test_list_all_anti_patterns(self, detector):
        """Test listing all anti-pattern definitions."""
        patterns = detector.list_all_anti_patterns()
        
        assert isinstance(patterns, list)
        assert len(patterns) == 3
        assert all(isinstance(pattern, AntiPatternDefinition) for pattern in patterns)


class TestTrapDetectionDataclass:
    """Tests for TrapDetection dataclass."""
    
    def test_trap_detection_creation(self):
        """Test creating trap detection result."""
        detection = TrapDetection(
            trap_type=TrapType.INFINITE_LOOP,
            severity=TrapSeverity.CRITICAL,
            confidence=0.9,
            evidence={"repetitions": 5},
            suggestion="Break the loop"
        )
        
        assert detection.trap_type == TrapType.INFINITE_LOOP
        assert detection.severity == TrapSeverity.CRITICAL
        assert detection.confidence == 0.9
        assert detection.evidence == {"repetitions": 5}
        assert detection.suggestion == "Break the loop"
    
    def test_trap_detection_repr(self):
        """Test trap detection string representation."""
        detection = TrapDetection(
            trap_type=TrapType.INFINITE_LOOP,
            severity=TrapSeverity.CRITICAL,
            confidence=0.9,
            evidence={},
            suggestion=""
        )
        
        repr_str = repr(detection)
        assert "infinite_loop" in repr_str
        assert "critical" in repr_str
        assert "0.90" in repr_str


class TestIntegration:
    """Integration tests for trap detector."""
    
    @pytest.fixture
    def detector(self):
        """Create detector for tests."""
        return TrapDetector()
    
    def test_complete_trap_detection_workflow(self, detector):
        """Test complete workflow from detection to reporting."""
        # 1. Get trap definition
        definition = detector.get_trap_definition(TrapType.INFINITE_LOOP)
        assert definition is not None
        
        # 2. Check detection criteria
        meets_criteria = detector.check_detection_criteria(
            TrapType.INFINITE_LOOP,
            "repetition_threshold",
            4
        )
        assert meets_criteria is True
        
        # 3. Get recovery strategies
        strategies = detector.get_recovery_strategies(TrapType.INFINITE_LOOP)
        assert len(strategies) > 0
        
        # 4. Get prevention strategies
        preventions = detector.get_prevention_strategies(TrapType.INFINITE_LOOP)
        assert len(preventions) > 0
        
        # 5. Get examples
        examples = detector.get_examples(TrapType.INFINITE_LOOP)
        assert len(examples) > 0
        
        # 6. Format report
        report = detector.format_trap_report(
            trap_type=TrapType.INFINITE_LOOP,
            severity=TrapSeverity.CRITICAL,
            confidence=0.95,
            evidence={"repetitions": 4, "window": 10}
        )
        assert "Infinite Loop" in report
    
    def test_all_traps_have_required_fields(self, detector):
        """Test that all traps have required fields."""
        traps = detector.list_all_traps()
        
        for trap in traps:
            assert trap.trap_type is not None
            assert trap.name is not None
            assert trap.description is not None
            assert len(trap.detection_criteria) > 0
            assert len(trap.recovery_strategies) > 0
            assert len(trap.prevention_strategies) > 0
            assert len(trap.examples) > 0
    
    def test_all_anti_patterns_have_required_fields(self, detector):
        """Test that all anti-patterns have required fields."""
        patterns = detector.list_all_anti_patterns()
        
        for pattern in patterns:
            assert pattern.anti_pattern_type is not None
            assert pattern.name is not None
            assert pattern.description is not None
            assert len(pattern.symptoms) > 0
            assert len(pattern.consequences) > 0
            assert len(pattern.prevention) > 0
            assert len(pattern.examples) > 0