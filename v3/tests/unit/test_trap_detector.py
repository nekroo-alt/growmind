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


class TestLoopDetection:
    """Tests for loop detection algorithms (Task 4.2)."""
    
    @pytest.fixture
    def detector(self):
        """Create detector for tests."""
        return TrapDetector()
    
    # ========== Exact Action Loop Detection ==========
    
    def test_exact_action_loop_detected(self, detector):
        """Test detection of exact action repetition."""
        action_history = [
            {"action": "fix bug in login"},
            {"action": "fix bug in login"},
            {"action": "fix bug in login"}  # 3rd repetition
        ]
        
        detection = detector.detect_exact_action_loop(action_history)
        
        assert detection is not None
        assert detection.trap_type == TrapType.INFINITE_LOOP
        assert detection.severity == TrapSeverity.WARNING
        assert detection.evidence["loop_type"] == "exact_action_loop"
        assert detection.evidence["repetition_count"] == 3
    
    def test_exact_action_loop_below_threshold(self, detector):
        """Test no detection when repetition below threshold."""
        action_history = [
            {"action": "fix bug in login"},
            {"action": "fix bug in login"}  # Only 2 repetitions
        ]
        
        detection = detector.detect_exact_action_loop(action_history)
        
        assert detection is None
    
    def test_exact_action_loop_critical_severity(self, detector):
        """Test critical severity for 5+ repetitions."""
        action_history = [
            {"action": "fix bug in login"} for _ in range(5)
        ]
        
        detection = detector.detect_exact_action_loop(action_history)
        
        assert detection is not None
        assert detection.severity == TrapSeverity.CRITICAL
        assert detection.evidence["repetition_count"] == 5
    
    def test_exact_action_loop_with_window(self, detector):
        """Test detection with custom window."""
        action_history = [
            {"action": "fix bug"} for _ in range(15)
        ]
        
        detection = detector.detect_exact_action_loop(action_history, window=5)
        
        assert detection is not None
        assert detection.evidence["window"] == 5
    
    def test_exact_action_loop_multiple_actions(self, detector):
        """Test detection when only one action repeats."""
        action_history = [
            {"action": "write test"},
            {"action": "write test"},
            {"action": "write test"},
            {"action": "implement feature"},
            {"action": "write code"}
        ]
        
        detection = detector.detect_exact_action_loop(action_history)
        
        assert detection is not None
        assert detection.evidence["action"] == "write test"
    
    # ========== Similar Action Pattern Detection ==========
    
    def test_similar_action_pattern_detected(self, detector):
        """Test detection of similar action patterns."""
        action_history = [
            {"action": "fix login bug"},
            {"action": "fix login bug"},
            {"action": "fix login bug"},
            {"action": "fix login bug"},
            {"action": "fix login bug"}  # 5th identical action
        ]
        
        detection = detector.detect_similar_action_pattern(action_history, similarity_threshold=0.9)
        
        assert detection is not None
        assert detection.trap_type == TrapType.INFINITE_LOOP
        assert detection.evidence["loop_type"] == "similar_action_pattern"
        assert detection.evidence["pattern_count"] >= 5
    
    def test_similar_action_pattern_below_threshold(self, detector):
        """Test no detection when similar actions below threshold."""
        action_history = [
            {"action": "fix login bug"},
            {"action": "fix authentication bug"},
            {"action": "implement feature"}
        ]
        
        detection = detector.detect_similar_action_pattern(action_history)
        
        assert detection is None
    
    def test_similar_action_pattern_custom_threshold(self, detector):
        """Test detection with custom similarity threshold."""
        action_history = [
            {"action": "fix bug"} for _ in range(5)
        ]
        
        detection = detector.detect_similar_action_pattern(
            action_history,
            similarity_threshold=0.9
        )
        
        assert detection is not None
        assert detection.evidence["avg_similarity"] >= 0.9
    
    def test_similar_action_pattern_dissimilar_actions(self, detector):
        """Test no detection for dissimilar actions."""
        action_history = [
            {"action": "write test"},
            {"action": "implement feature"},
            {"action": "refactor code"},
            {"action": "fix bug"},
            {"action": "write documentation"}
        ]
        
        detection = detector.detect_similar_action_pattern(action_history)
        
        assert detection is None
    
    # ========== Error Loop Detection ==========
    
    def test_error_loop_detected(self, detector):
        """Test detection of repeated error from same action."""
        action_history = [
            {"action": "connect to database", "error": "Connection timeout"},
            {"action": "connect to database", "error": "Connection timeout"},
            {"action": "connect to database", "error": "Connection timeout"}
        ]
        
        detection = detector.detect_error_loop(action_history)
        
        assert detection is not None
        assert detection.trap_type == TrapType.INFINITE_LOOP
        assert detection.evidence["loop_type"] == "error_loop"
        assert detection.evidence["error_count"] == 3
        assert "Connection timeout" in detection.suggestion
    
    def test_error_loop_different_errors(self, detector):
        """Test no detection for different errors."""
        action_history = [
            {"action": "connect to database", "error": "Connection timeout"},
            {"action": "connect to database", "error": "Authentication failed"}
        ]
        
        detection = detector.detect_error_loop(action_history)
        
        assert detection is None
    
    def test_error_loop_no_errors(self, detector):
        """Test no detection when no errors present."""
        action_history = [
            {"action": "connect to database"},
            {"action": "connect to database"},
            {"action": "connect to database"}
        ]
        
        detection = detector.detect_error_loop(action_history)
        
        assert detection is None
    
    def test_error_loop_critical_severity(self, detector):
        """Test critical severity for 5+ error repetitions."""
        action_history = [
            {"action": "connect to database", "error": "Connection timeout"}
            for _ in range(5)
        ]
        
        detection = detector.detect_error_loop(action_history)
        
        assert detection is not None
        assert detection.severity == TrapSeverity.CRITICAL
        assert detection.evidence["error_count"] == 5
    
    # ========== Reasoning Loop Detection ==========
    
    def test_reasoning_loop_detected(self, detector):
        """Test detection of repeated reasoning patterns."""
        decision_history = [
            {"reasoning": {"factor1": "high_cost", "factor2": "low_risk"}},
            {"reasoning": {"factor1": "high_cost", "factor2": "low_risk"}},
            {"reasoning": {"factor1": "high_cost", "factor2": "low_risk"}}
        ]
        
        detection = detector.detect_reasoning_loop(decision_history)
        
        assert detection is not None
        assert detection.trap_type == TrapType.CIRCULAR_REASONING
        assert detection.evidence["loop_type"] == "reasoning_loop"
        assert detection.evidence["repetition_count"] == 3
    
    def test_reasoning_loop_with_factors_field(self, detector):
        """Test detection using factors field instead of reasoning."""
        decision_history = [
            {"factors": {"cost": "high", "risk": "low"}},
            {"factors": {"cost": "high", "risk": "low"}},
            {"factors": {"cost": "high", "risk": "low"}}
        ]
        
        detection = detector.detect_reasoning_loop(decision_history)
        
        assert detection is not None
        assert detection.evidence["repetition_count"] == 3
    
    def test_reasoning_loop_empty_reasoning(self, detector):
        """Test no detection for empty reasoning."""
        decision_history = [
            {"reasoning": {}},
            {"reasoning": {}},
            {"reasoning": {}}
        ]
        
        detection = detector.detect_reasoning_loop(decision_history)
        
        assert detection is None
    
    def test_reasoning_loop_different_reasoning(self, detector):
        """Test no detection for different reasoning patterns."""
        decision_history = [
            {"reasoning": {"factor1": "high_cost"}},
            {"reasoning": {"factor2": "low_risk"}},
            {"reasoning": {"factor3": "high_value"}}
        ]
        
        detection = detector.detect_reasoning_loop(decision_history)
        
        assert detection is None
    
    # ========== Infinite Recursion Detection ==========
    
    def test_infinite_recursion_cycle_detected(self, detector):
        """Test detection of circular dependency in decisions."""
        decision_history = [
            {"decision_id": 1, "parent_id": 3},
            {"decision_id": 2, "parent_id": 1},
            {"decision_id": 3, "parent_id": 2}  # Creates cycle: 1→3→2→1
        ]
        
        detection = detector.detect_infinite_recursion(decision_history)
        
        assert detection is not None
        assert detection.trap_type == TrapType.CIRCULAR_REASONING
        assert detection.evidence["loop_type"] == "infinite_recursion"
        assert detection.evidence["cycle_detected"] is True
    
    def test_infinite_recursion_excessive_depth(self, detector):
        """Test detection of excessive decision depth."""
        # Create a chain deeper than max_depth
        decision_history = []
        for i in range(15):  # Deeper than default max_depth=10
            decision_history.append({
                "decision_id": i,
                "parent_id": i - 1 if i > 0 else None
            })
        
        detection = detector.detect_infinite_recursion(decision_history, max_depth=10)
        
        assert detection is not None
        assert detection.evidence["loop_type"] == "excessive_depth"
        # Depth is 14 (0-14 chain length, depth of node 14 is 14)
        assert detection.evidence["depth"] >= 10
    
    def test_infinite_recursion_no_issues(self, detector):
        """Test no detection for normal decision hierarchy."""
        decision_history = [
            {"decision_id": 1, "parent_id": None},
            {"decision_id": 2, "parent_id": 1},
            {"decision_id": 3, "parent_id": 2}
        ]
        
        detection = detector.detect_infinite_recursion(decision_history)
        
        assert detection is None
    
    # ========== Detect All Loops ==========
    
    def test_detect_all_loops_action_history(self, detector):
        """Test running all loop detection on action history."""
        action_history = [
            {"action": "fix bug"} for _ in range(5)
        ]
        
        detections = detector.detect_all_loops(action_history=action_history)
        
        assert len(detections) > 0
        # Should detect exact loop and similar pattern
        loop_types = [d.evidence["loop_type"] for d in detections]
        assert "exact_action_loop" in loop_types
    
    def test_detect_all_loops_decision_history(self, detector):
        """Test running all loop detection on decision history."""
        decision_history = [
            {"reasoning": {"factor": "value"}} for _ in range(5)
        ]
        
        detections = detector.detect_all_loops(decision_history=decision_history)
        
        assert len(detections) > 0
        assert all(d.trap_type in [TrapType.INFINITE_LOOP, TrapType.CIRCULAR_REASONING] 
                  for d in detections)
    
    def test_detect_all_loops_both_histories(self, detector):
        """Test running all loop detection on both histories."""
        action_history = [
            {"action": "fix bug"} for _ in range(3)
        ]
        decision_history = [
            {"reasoning": {"factor": "value"}} for _ in range(3)
        ]
        
        detections = detector.detect_all_loops(
            action_history=action_history,
            decision_history=decision_history
        )
        
        assert len(detections) > 0
    
    def test_detect_all_loops_no_loops(self, detector):
        """Test running all loop detection with no loops."""
        action_history = [
            {"action": f"action {i}"} for i in range(10)
        ]
        decision_history = [
            {"reasoning": {f"factor{i}": f"value{i}"} } for i in range(10)
        ]
        
        detections = detector.detect_all_loops(
            action_history=action_history,
            decision_history=decision_history
        )
        
        assert len(detections) == 0
    
    # ========== Similarity Calculation ==========
    
    def test_similarity_identical_strings(self, detector):
        """Test similarity calculation for identical strings."""
        similarity = detector._calculate_similarity("test string", "test string")
        
        assert similarity == 1.0
    
    def test_similarity_completely_different(self, detector):
        """Test similarity calculation for completely different strings."""
        similarity = detector._calculate_similarity("apple", "zebra")
        
        assert similarity < 0.3
    
    def test_similarity_similar_strings(self, detector):
        """Test similarity calculation for similar strings."""
        similarity = detector._calculate_similarity(
            "fix login bug",
            "fix login issue"
        )

        # These strings share 2 out of 4 unique words ("fix", "login")
        # Jaccard: 0.5, plus n-gram similarity for partial overlap
        # Combined weighted average should be moderate
        assert 0.4 < similarity < 0.7
    
    def test_similarity_empty_strings(self, detector):
        """Test similarity calculation for empty strings."""
        similarity = detector._calculate_similarity("", "")
        
        assert similarity == 1.0
    
    def test_similarity_one_empty_string(self, detector):
        """Test similarity calculation with one empty string."""
        similarity = detector._calculate_similarity("test", "")
        
        assert similarity == 0.0
    
    # ========== Reasoning Normalization ==========
    
    def test_normalize_reasoning_dict(self, detector):
        """Test normalization of reasoning dictionary."""
        reasoning = {"factor2": "value2", "factor1": "value1"}
        normalized = detector._normalize_reasoning(reasoning)
        
        assert "{" in normalized
        assert "factor1:value1" in normalized
        assert "factor2:value2" in normalized
        # Keys should be sorted
        assert normalized.index("factor1") < normalized.index("factor2")
    
    def test_normalize_reasoning_list(self, detector):
        """Test normalization of reasoning list."""
        reasoning = ["value3", "value1", "value2"]
        normalized = detector._normalize_reasoning(reasoning)
        
        assert "[" in normalized
        assert "value1" in normalized
        assert "value2" in normalized
        assert "value3" in normalized
        # Items should be sorted
        assert normalized.index("value1") < normalized.index("value2")
    
    def test_normalize_reasoning_string(self, detector):
        """Test normalization of reasoning string."""
        reasoning = "  Test String  "
        normalized = detector._normalize_reasoning(reasoning)
        
        assert normalized == "test string"
    
    def test_normalize_reasoning_nested_dict(self, detector):
        """Test normalization of nested reasoning dictionary."""
        reasoning = {"factor": {"nested": "value"}}
        normalized = detector._normalize_reasoning(reasoning)
        
        assert "factor:" in normalized
        assert normalized.startswith("{")
        assert normalized.endswith("}")
    
    # ========== Edge Cases ==========
    
    def test_empty_action_history(self, detector):
        """Test detection with empty action history."""
        detection = detector.detect_exact_action_loop([])
        
        assert detection is None
    
    def test_empty_decision_history(self, detector):
        """Test detection with empty decision history."""
        detection = detector.detect_reasoning_loop([])
        
        assert detection is None
    
    def test_action_without_action_field(self, detector):
        """Test action history without action field."""
        action_history = [
            {"operation": "fix bug"} for _ in range(5)
        ]
        
        detection = detector.detect_exact_action_loop(action_history)
        
        # Should still work, using string representation
        assert detection is not None
    
    def test_custom_window_larger_than_history(self, detector):
        """Test with custom window larger than available history."""
        action_history = [
            {"action": "fix bug"} for _ in range(3)
        ]
        
        detection = detector.detect_exact_action_loop(action_history, window=100)
        
        assert detection is not None
        # Should use all available history
        assert detection.evidence["repetition_count"] == 3
    
    def test_confidence_calculation(self, detector):
        """Test confidence calculation increases with repetitions."""
        detection_3 = detector.detect_exact_action_loop([
            {"action": "test"} for _ in range(3)
        ])
        detection_5 = detector.detect_exact_action_loop([
            {"action": "test"} for _ in range(5)
        ])
        
        assert detection_3 is not None
        assert detection_5 is not None
        assert detection_5.confidence > detection_3.confidence


class TestDeadEndDetection:
    """Tests for dead end detection algorithms (Task 4.3)."""
    
    @pytest.fixture
    def detector(self):
        """Create detector for tests."""
        return TrapDetector()
    
    # ========== No Progress Detection ==========
    
    def test_dead_end_no_progress_detected(self, detector):
        """Test detection of no progress for extended period."""
        progress_history = [
            {"progress": 0.0},
            {"progress": 0.01},
            {"progress": 0.02},
            {"progress": 0.01},
            {"progress": 0.03}  # 5th operation, all <5% progress
        ]
        
        detection = detector.detect_dead_end_no_progress(progress_history)
        
        assert detection is not None
        assert detection.trap_type == TrapType.DEAD_END
        assert detection.evidence["dead_end_type"] == "no_progress"
        assert detection.evidence["no_progress_count"] == 5
    
    def test_dead_end_no_progress_critical_severity(self, detector):
        """Test critical severity for 10+ operations with no progress."""
        progress_history = [
            {"progress": 0.0} for _ in range(10)
        ]
        
        detection = detector.detect_dead_end_no_progress(progress_history)
        
        assert detection is not None
        assert detection.severity == TrapSeverity.BLOCKING
        assert detection.evidence["no_progress_count"] >= 10
    
    def test_dead_end_no_progress_below_threshold(self, detector):
        """Test no detection when progress below threshold."""
        progress_history = [
            {"progress": 0.0},
            {"progress": 0.0},
            {"progress": 0.0},
            {"progress": 0.0}  # Only 4 operations
        ]
        
        detection = detector.detect_dead_end_no_progress(progress_history)
        
        assert detection is None
    
    def test_dead_end_no_progress_with_meaningful_progress(self, detector):
        """Test no detection when meaningful progress is made."""
        progress_history = [
            {"progress": 0.0},
            {"progress": 0.0},
            {"progress": 0.15},  # Meaningful progress
            {"progress": 0.0},
            {"progress": 0.0}
        ]
        
        detection = detector.detect_dead_end_no_progress(progress_history)
        
        assert detection is None
    
    def test_dead_end_no_progress_custom_threshold(self, detector):
        """Test detection with custom threshold."""
        progress_history = [
            {"progress": 0.0} for _ in range(3)
        ]
        
        detection = detector.detect_dead_end_no_progress(progress_history, threshold=3)
        
        assert detection is not None
        assert detection.evidence["no_progress_count"] == 3
    
    def test_dead_end_no_progress_empty_history(self, detector):
        """Test no detection with empty progress history."""
        detection = detector.detect_dead_end_no_progress([])
        
        assert detection is None
    
    # ========== Exhausted Options Detection ==========
    
    def test_dead_end_exhausted_options_all_attempted(self, detector):
        """Test detection when all actions have been attempted."""
        action_history = [
            {"action": "approach A", "success": False},
            {"action": "approach B", "success": False},
            {"action": "approach C", "success": False}
        ]
        available_actions = ["approach A", "approach B", "approach C"]
        
        detection = detector.detect_dead_end_exhausted_options(
            action_history,
            available_actions
        )
        
        assert detection is not None
        assert detection.trap_type == TrapType.DEAD_END
        assert detection.evidence["dead_end_type"] == "exhausted_options"
        assert detection.evidence["all_attempted"] is True
    
    def test_dead_end_exhausted_options_near_exhaustion(self, detector):
        """Test detection when approaching action space exhaustion."""
        # Create 20 actions with 95% failure rate
        action_history = [
            {"action": f"approach {i}", "success": i == 0}  # Only 1 success
            for i in range(20)
        ]
        available_actions = [f"approach {i}" for i in range(22)]
        
        detection = detector.detect_dead_end_exhausted_options(
            action_history,
            available_actions
        )
        
        assert detection is not None
        assert detection.evidence["near_exhaustion"] is True
        assert detection.evidence["attempted_ratio"] >= 0.9
    
    def test_dead_end_exhausted_options_not_exhausted(self, detector):
        """Test no detection when actions still available."""
        action_history = [
            {"action": "approach A", "success": False},
            {"action": "approach B", "success": True}
        ]
        available_actions = ["approach A", "approach B", "approach C", "approach D"]
        
        detection = detector.detect_dead_end_exhausted_options(
            action_history,
            available_actions
        )
        
        assert detection is None
    
    def test_dead_end_exhausted_options_no_failure_rate(self, detector):
        """Test no detection when failure rate is low."""
        action_history = [
            {"action": "approach A", "success": True},
            {"action": "approach B", "success": True},
            {"action": "approach C", "success": True}
        ]
        available_actions = ["approach A", "approach B", "approach C"]
        
        detection = detector.detect_dead_end_exhausted_options(
            action_history,
            available_actions
        )
        
        assert detection is None
    
    def test_dead_end_exhausted_options_empty_history(self, detector):
        """Test no detection with empty action history."""
        detection = detector.detect_dead_end_exhausted_options([], ["action A"])
        
        assert detection is None
    
    def test_dead_end_exhausted_options_custom_window(self, detector):
        """Test detection with custom window."""
        action_history = [
            {"action": "approach A", "success": False} for _ in range(25)
        ]
        available_actions = ["approach A"]
        
        detection = detector.detect_dead_end_exhausted_options(
            action_history,
            available_actions,
            window=15
        )
        
        assert detection is not None
        assert detection.evidence["attempts_analyzed"] == 15
    
    # ========== Resource Exhaustion Detection ==========
    
    def test_dead_end_resource_exhaustion_tokens(self, detector):
        """Test detection of token exhaustion."""
        resource_metrics = {
            "tokens_used": 95000,
            "tokens_budget": 100000
        }
        
        detection = detector.detect_dead_end_resource_exhaustion(resource_metrics)
        
        assert detection is not None
        assert detection.trap_type == TrapType.DEAD_END
        assert detection.evidence["dead_end_type"] == "resource_exhaustion"
        assert "tokens" in detection.evidence["exhausted_resources"]
        assert detection.evidence["resource_status"]["tokens_percentage"] <= 5
    
    def test_dead_end_resource_exhaustion_time(self, detector):
        """Test detection of time exhaustion."""
        resource_metrics = {
            "time_elapsed": 28500,  # 475 minutes
            "time_budget": 30000     # 500 minutes
        }
        
        detection = detector.detect_dead_end_resource_exhaustion(resource_metrics)
        
        assert detection is not None
        assert "time" in detection.evidence["exhausted_resources"]
        assert detection.evidence["resource_status"]["time_percentage"] <= 5
    
    def test_dead_end_resource_exhaustion_compute(self, detector):
        """Test detection of compute exhaustion."""
        resource_metrics = {
            "compute_usage": 92
        }
        
        detection = detector.detect_dead_end_resource_exhaustion(resource_metrics)
        
        assert detection is not None
        assert "compute" in detection.evidence["exhausted_resources"]
        assert detection.evidence["resource_status"]["compute_usage"] >= 90
    
    def test_dead_end_resource_exhaustion_multiple(self, detector):
        """Test detection of multiple resource exhaustion."""
        resource_metrics = {
            "tokens_used": 98000,
            "tokens_budget": 100000,
            "time_elapsed": 29000,
            "time_budget": 30000
        }
        
        detection = detector.detect_dead_end_resource_exhaustion(resource_metrics)
        
        assert detection is not None
        assert "tokens" in detection.evidence["exhausted_resources"]
        assert "time" in detection.evidence["exhausted_resources"]
        assert len(detection.evidence["exhausted_resources"]) == 2
    
    def test_dead_end_resource_exhaustion_no_exhaustion(self, detector):
        """Test no detection when resources are adequate."""
        resource_metrics = {
            "tokens_used": 50000,
            "tokens_budget": 100000,
            "time_elapsed": 15000,
            "time_budget": 30000,
            "compute_usage": 45
        }
        
        detection = detector.detect_dead_end_resource_exhaustion(resource_metrics)
        
        assert detection is None
    
    def test_dead_end_resource_exhaustion_custom_thresholds(self, detector):
        """Test detection with custom thresholds."""
        resource_metrics = {
            "tokens_used": 95000,
            "tokens_budget": 100000
        }
        
        detection = detector.detect_dead_end_resource_exhaustion(
            resource_metrics,
            token_threshold=2000,
            time_threshold=600
        )
        
        assert detection is not None
    
    def test_dead_end_resource_exhaustion_empty_metrics(self, detector):
        """Test no detection with empty resource metrics."""
        detection = detector.detect_dead_end_resource_exhaustion({})
        
        assert detection is None
    
    # ========== Goal Unreachable Detection ==========
    
    def test_dead_end_goal_unreachable_large_gap(self, detector):
        """Test detection when state gap is large with no progress."""
        action_history = [
            {
                "action": "implement feature",
                "state_after": {"completed": 0.1}
            },
            {
                "action": "implement feature",
                "state_after": {"completed": 0.12}
            },
            {
                "action": "implement feature",
                "state_after": {"completed": 0.11}
            }
        ]
        goal_state = {"completed": 1.0}
        current_state = {"completed": 0.11}
        
        detection = detector.detect_dead_end_goal_unreachable(
            action_history,
            goal_state,
            current_state
        )
        
        assert detection is not None
        assert detection.trap_type == TrapType.DEAD_END
        assert detection.evidence["dead_end_type"] == "goal_unreachable"
        assert detection.evidence["state_gap"] > 0.5
    
    def test_dead_end_goal_unreachable_no_progress_rate(self, detector):
        """Test detection when progress rate is zero or negative."""
        action_history = [
            {
                "action": "implement feature",
                "state_after": {"completed": 0.2}
            },
            {
                "action": "implement feature",
                "state_after": {"completed": 0.2}
            },
            {
                "action": "implement feature",
                "state_after": {"completed": 0.19}
            },
            {
                "action": "implement feature",
                "state_after": {"completed": 0.18}
            },
            {
                "action": "implement feature",
                "state_after": {"completed": 0.18}
            }
        ]
        goal_state = {"completed": 1.0}
        current_state = {"completed": 0.18}
        
        detection = detector.detect_dead_end_goal_unreachable(
            action_history,
            goal_state,
            current_state
        )
        
        assert detection is not None
        # Recent progress rates should all be <= 0
        assert all(rate <= 0 for rate in detection.evidence["recent_progress_rates"][-5:])
    
    def test_dead_end_goal_unreachable_reachable(self, detector):
        """Test no detection when goal is reachable."""
        action_history = [
            {
                "action": "implement feature",
                "state_after": {"completed": 0.5}
            },
            {
                "action": "implement feature",
                "state_after": {"completed": 0.7}
            },
            {
                "action": "implement feature",
                "state_after": {"completed": 0.85}
            }
        ]
        goal_state = {"completed": 1.0}
        current_state = {"completed": 0.85}
        
        detection = detector.detect_dead_end_goal_unreachable(
            action_history,
            goal_state,
            current_state
        )
        
        assert detection is None
    
    def test_dead_end_goal_unreachable_empty_history(self, detector):
        """Test no detection with empty action history."""
        detection = detector.detect_dead_end_goal_unreachable(
            [],
            {"completed": 1.0},
            {"completed": 0.5}
        )
        
        assert detection is None
    
    def test_dead_end_goal_unreachable_no_goal_state(self, detector):
        """Test no detection when goal state is None."""
        detection = detector.detect_dead_end_goal_unreachable(
            [{"action": "test"}],
            None,
            {"completed": 0.5}
        )
        
        assert detection is None
    
    def test_dead_end_goal_unreachable_no_current_state(self, detector):
        """Test no detection when current state is None."""
        detection = detector.detect_dead_end_goal_unreachable(
            [{"action": "test"}],
            {"completed": 1.0},
            None
        )
        
        assert detection is None
    
    def test_dead_end_goal_unreachable_custom_window(self, detector):
        """Test detection with custom window."""
        action_history = [
            {
                "action": "implement feature",
                "state_after": {"completed": 0.1}
            } for _ in range(20)
        ]
        goal_state = {"completed": 1.0}
        current_state = {"completed": 0.1}
        
        detection = detector.detect_dead_end_goal_unreachable(
            action_history,
            goal_state,
            current_state,
            window=10
        )
        
        # Should analyze only last 10 actions
        assert detection is not None
        assert detection.evidence["actions_analyzed"] == 10
    
    # ========== Detect All Dead Ends ==========
    
    def test_detect_all_dead_ends(self, detector):
        """Test running all dead end detection algorithms."""
        progress_history = [
            {"progress": 0.0} for _ in range(5)
        ]
        action_history = [
            {"action": "approach A", "success": False},
            {"action": "approach B", "success": False},
            {"action": "approach C", "success": False}
        ]
        available_actions = ["approach A", "approach B", "approach C"]
        resource_metrics = {
            "tokens_used": 95000,
            "tokens_budget": 100000
        }
        
        detections = detector.detect_all_dead_ends(
            progress_history=progress_history,
            action_history=action_history,
            available_actions=available_actions,
            resource_metrics=resource_metrics
        )
        
        assert len(detections) > 0
        dead_end_types = [d.evidence["dead_end_type"] for d in detections]
        assert "no_progress" in dead_end_types
        assert "exhausted_options" in dead_end_types
        assert "resource_exhaustion" in dead_end_types
    
    def test_detect_all_dead_ends_partial_input(self, detector):
        """Test running dead end detection with partial input."""
        progress_history = [
            {"progress": 0.0} for _ in range(5)
        ]
        
        detections = detector.detect_all_dead_ends(progress_history=progress_history)
        
        assert len(detections) > 0
        assert all(d.trap_type == TrapType.DEAD_END for d in detections)
    
    def test_detect_all_dead_ends_no_dead_ends(self, detector):
        """Test running all dead end detection with no issues."""
        progress_history = [
            {"progress": 0.2},
            {"progress": 0.4},
            {"progress": 0.6}
        ]
        action_history = [
            {"action": "approach A", "success": True},
            {"action": "approach B", "success": True}
        ]
        available_actions = ["approach A", "approach B", "approach C"]
        resource_metrics = {
            "tokens_used": 20000,
            "tokens_budget": 100000,
            "time_elapsed": 5000,
            "time_budget": 30000,
            "compute_usage": 40
        }
        
        detections = detector.detect_all_dead_ends(
            progress_history=progress_history,
            action_history=action_history,
            available_actions=available_actions,
            resource_metrics=resource_metrics
        )
        
        assert len(detections) == 0
    
    # ========== State Gap Calculation ==========
    
    def test_calculate_state_gap_boolean(self, detector):
        """Test state gap calculation for boolean values."""
        current = {"feature_complete": False}
        goal = {"feature_complete": True}
        
        gap = detector._calculate_state_gap(current, goal)
        
        assert gap == 1.0
    
    def test_calculate_state_gap_boolean_match(self, detector):
        """Test state gap calculation for matching boolean values."""
        current = {"feature_complete": True}
        goal = {"feature_complete": True}
        
        gap = detector._calculate_state_gap(current, goal)
        
        assert gap == 0.0
    
    def test_calculate_state_gap_numeric(self, detector):
        """Test state gap calculation for numeric values."""
        current = {"progress": 0.5}
        goal = {"progress": 1.0}
        
        gap = detector._calculate_state_gap(current, goal)
        
        assert gap == 0.5
    
    def test_calculate_state_gap_numeric_zero(self, detector):
        """Test state gap calculation for zero values."""
        current = {"count": 0}
        goal = {"count": 0}
        
        gap = detector._calculate_state_gap(current, goal)
        
        assert gap == 0.0
    
    def test_calculate_state_gap_set(self, detector):
        """Test state gap calculation for set values."""
        current = {"features": {"feature1", "feature2"}}
        goal = {"features": {"feature1", "feature2", "feature3"}}
        
        gap = detector._calculate_state_gap(current, goal)
        
        assert gap == 1.0 / 3.0  # 1 missing out of 3
    
    def test_calculate_state_gap_list(self, detector):
        """Test state gap calculation for list values."""
        current = {"files": ["file1.py", "file2.py"]}
        goal = {"files": ["file1.py", "file2.py", "file3.py"]}
        
        gap = detector._calculate_state_gap(current, goal)
        
        assert gap == 1.0 / 3.0  # 1 missing out of 3
    
    def test_calculate_state_gap_dict(self, detector):
        """Test state gap calculation for dict values."""
        current = {"config": {"key1": "value1"}}
        goal = {"config": {"key1": "value1", "key2": "value2"}}
        
        gap = detector._calculate_state_gap(current, goal)
        
        # Gap is 1 - (1/2) = 0.5
        assert 0.4 < gap < 0.6
    
    def test_calculate_state_gap_string(self, detector):
        """Test state gap calculation for string values."""
        current = {"status": "in_progress"}
        goal = {"status": "complete"}
        
        gap = detector._calculate_state_gap(current, goal)
        
        assert gap == 1.0
    
    def test_calculate_state_gap_string_match(self, detector):
        """Test state gap calculation for matching string values."""
        current = {"status": "complete"}
        goal = {"status": "complete"}
        
        gap = detector._calculate_state_gap(current, goal)
        
        assert gap == 0.0
    
    def test_calculate_state_gap_multiple_keys(self, detector):
        """Test state gap calculation for multiple keys."""
        current = {
            "feature_complete": False,
            "progress": 0.5,
            "tests_passing": 8
        }
        goal = {
            "feature_complete": True,
            "progress": 1.0,
            "tests_passing": 10
        }
        
        gap = detector._calculate_state_gap(current, goal)
        
        # Average of: 1.0 (bool), 0.5 (numeric), 0.2 (numeric)
        assert 0.5 < gap < 0.7
    
    def test_calculate_state_gap_empty_goal(self, detector):
        """Test state gap calculation with empty goal."""
        gap = detector._calculate_state_gap(
            {"key": "value"},
            {}
        )
        
        assert gap == 0.0
    
    # ========== Resource Exhaustion Message Formatting ==========
    
    def test_format_resource_exhaustion_message_tokens(self, detector):
        """Test formatting token exhaustion message."""
        exhausted = ["tokens"]
        status = {
            "tokens_remaining": 500,
            "tokens_percentage": 0.5
        }
        
        message = detector._format_resource_exhaustion_message(exhausted, status)
        
        assert "Tokens" in message
        assert "500" in message
        assert "0.5%" in message
    
    def test_format_resource_exhaustion_message_time(self, detector):
        """Test formatting time exhaustion message."""
        exhausted = ["time"]
        status = {
            "time_remaining": 300,
            "time_percentage": 1.0
        }
        
        message = detector._format_resource_exhaustion_message(exhausted, status)
        
        assert "Time" in message
        assert "5.0 minutes" in message
        assert "1.0%" in message
    
    def test_format_resource_exhaustion_message_compute(self, detector):
        """Test formatting compute exhaustion message."""
        exhausted = ["compute"]
        status = {
            "compute_usage": 95
        }
        
        message = detector._format_resource_exhaustion_message(exhausted, status)
        
        assert "Compute" in message
        assert "95.0%" in message
    
    def test_format_resource_exhaustion_message_multiple(self, detector):
        """Test formatting multiple resource exhaustion message."""
        exhausted = ["tokens", "time"]
        status = {
            "tokens_remaining": 500,
            "tokens_percentage": 0.5,
            "time_remaining": 300,
            "time_percentage": 1.0
        }
        
        message = detector._format_resource_exhaustion_message(exhausted, status)
        
        assert "Tokens" in message
        assert "Time" in message
        assert "backtracking" in message.lower()
    
    # ========== Edge Cases ==========
    
    def test_dead_end_no_progress_all_zero(self, detector):
        """Test no progress detection when all progress is zero."""
        progress_history = [
            {"progress": 0.0} for _ in range(6)
        ]
        
        detection = detector.detect_dead_end_no_progress(progress_history)
        
        assert detection is not None
        assert detection.evidence["latest_progress"] == 0.0
        assert detection.evidence["avg_progress"] == 0.0
    
    def test_dead_end_exhausted_options_no_available(self, detector):
        """Test exhausted options with no available actions."""
        action_history = [
            {"action": "approach A", "success": False} for _ in range(20)
        ]
        available_actions = []
        
        detection = detector.detect_dead_end_exhausted_options(
            action_history,
            available_actions
        )
        
        assert detection is None


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