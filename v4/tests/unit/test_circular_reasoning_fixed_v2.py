"""
Unit tests for circular reasoning detection (Task 4.4) - FIXED V2

Tests all circular reasoning detection methods:
- Decision cycle detection (A → B → C → A)
- Revisiting rejected options
- Contradictory decisions detection
- Dependency cycles detection
"""

import unittest
from datetime import datetime
from v3.logic.trap_detector import (
    TrapDetector,
    TrapType,
    TrapSeverity
)


class TestCircularReasoningDecisionCycle(unittest.TestCase):
    """Test decision cycle detection."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.detector = TrapDetector()
    
    def test_detect_decision_cycle_simple(self):
        """Test detection of simple decision cycle (A → B → A)."""
        decision_history = [
            {"decision_id": "1", "action": "A", "parent_id": None},
            {"decision_id": "2", "action": "B", "parent_id": "1"},
            {"decision_id": "3", "action": "A", "parent_id": "2"}
        ]
        
        detection = self.detector.detect_circular_reasoning_decision_cycle(
            decision_history,
            cycle_min_length=2
        )
        
        self.assertIsNotNone(detection)
        self.assertEqual(detection.trap_type, TrapType.CIRCULAR_REASONING)
        self.assertEqual(detection.evidence["circular_reasoning_type"], "decision_cycle")
        self.assertGreaterEqual(detection.evidence["cycle_length"], 2)
    
    def test_detect_decision_cycle_longer(self):
        """Test detection of longer decision cycle (A → B → C → D → A)."""
        decision_history = [
            {"decision_id": "1", "action": "A", "parent_id": None},
            {"decision_id": "2", "action": "B", "parent_id": "1"},
            {"decision_id": "3", "action": "C", "parent_id": "2"},
            {"decision_id": "4", "action": "D", "parent_id": "3"},
            {"decision_id": "5", "action": "A", "parent_id": "4"}
        ]
        
        detection = self.detector.detect_circular_reasoning_decision_cycle(
            decision_history,
            cycle_min_length=3
        )
        
        self.assertIsNotNone(detection)
        self.assertEqual(detection.evidence["cycle_length"], 4)
        self.assertGreater(detection.confidence, 0.8)
    
    def test_no_decision_cycle_linear(self):
        """Test that linear chain is not detected as cycle."""
        decision_history = [
            {"decision_id": "1", "action": "A", "parent_id": None},
            {"decision_id": "2", "action": "B", "parent_id": "1"},
            {"decision_id": "3", "action": "C", "parent_id": "2"},
            {"decision_id": "4", "action": "D", "parent_id": "3"}
        ]
        
        detection = self.detector.detect_circular_reasoning_decision_cycle(
            decision_history,
            cycle_min_length=2
        )
        
        self.assertIsNone(detection)
    
    def test_no_decision_cycle_insufficient_decisions(self):
        """Test that insufficient decisions don't trigger cycle detection."""
        decision_history = [
            {"decision_id": "1", "action": "A", "parent_id": None}
        ]
        
        detection = self.detector.detect_circular_reasoning_decision_cycle(
            decision_history,
            cycle_min_length=3
        )
        
        self.assertIsNone(detection)
    
    def test_multiple_cycles_detected(self):
        """Test detection of multiple cycles."""
        decision_history = [
            {"decision_id": "1", "action": "A", "parent_id": None},
            {"decision_id": "2", "action": "B", "parent_id": "1"},
            {"decision_id": "3", "action": "A", "parent_id": "2"},
            {"decision_id": "4", "action": "C", "parent_id": None},
            {"decision_id": "5", "action": "D", "parent_id": "4"},
            {"decision_id": "6", "action": "C", "parent_id": "5"}
        ]
        
        detection = self.detector.detect_circular_reasoning_decision_cycle(
            decision_history,
            cycle_min_length=2
        )
        
        self.assertIsNotNone(detection)
        self.assertGreaterEqual(detection.evidence["total_cycles_found"], 2)
    
    def test_cycle_severity_critical(self):
        """Test that long cycles have CRITICAL severity."""
        # Create repeated action cycle (not parent_id cycle)
        decision_history = [
            {"decision_id": "0", "action": "DecisionA"},
            {"decision_id": "1", "action": "DecisionB"},
            {"decision_id": "2", "action": "DecisionC"},
            {"decision_id": "3", "action": "DecisionD"},
            {"decision_id": "4", "action": "DecisionE"},
            {"decision_id": "5", "action": "DecisionF"},
            {"decision_id": "6", "action": "DecisionA"}  # Repeat first action
        ]
        
        detection = self.detector.detect_circular_reasoning_decision_cycle(
            decision_history,
            cycle_min_length=3
        )
        
        self.assertIsNotNone(detection)
        self.assertEqual(detection.severity, TrapSeverity.CRITICAL)
    
    def test_window_parameter(self):
        """Test that window parameter limits decision analysis."""
        decision_history = []
        # Create cycle in old decisions (repeated action)
        decision_history.append({"decision_id": "old_0", "action": "OldA"})
        decision_history.append({"decision_id": "old_1", "action": "OldB"})
        decision_history.append({"decision_id": "old_2", "action": "OldA"})  # Cycle
        
        # Recent linear decisions (no cycle)
        for i in range(5):
            decision_history.append({
                "decision_id": f"new_{i}",
                "action": f"New{i}"
            })
        
        # With small window, should not detect old cycle
        detection = self.detector.detect_circular_reasoning_decision_cycle(
            decision_history,
            cycle_min_length=2,
            window=5
        )
        
        self.assertIsNone(detection)
        
        # With larger window, should detect old cycle
        detection = self.detector.detect_circular_reasoning_decision_cycle(
            decision_history,
            cycle_min_length=2,
            window=10
        )
        
        self.assertIsNotNone(detection)


class TestCircularReasoningRevisitingRejected(unittest.TestCase):
    """Test revisiting rejected options detection."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.detector = TrapDetector()
    
    def test_detect_revisiting_rejected(self):
        """Test detection of revisiting rejected options."""
        decision_history = [
            {
                "decision_id": "1",
                "action": "Strategy A",
                "alternatives": ["Strategy B", "Strategy C"],
                "rejection_reason": "Strategy B is too slow"
            },
            {
                "decision_id": "2",
                "action": "Strategy B",
                "alternatives": ["Strategy A", "Strategy C"],
                "rejection_reason": "Strategy A doesn't fit requirements"
            },
            {
                "decision_id": "3",
                "action": "Strategy A",  # Revisiting rejected option
                "alternatives": ["Strategy D"],
                "rejection_reason": "Strategy D is complex"
            }
        ]
        
        detection = self.detector.detect_circular_reasoning_revisiting_rejected(
            decision_history,
            threshold=2
        )
        
        self.assertIsNotNone(detection)
        self.assertEqual(detection.trap_type, TrapType.CIRCULAR_REASONING)
        self.assertEqual(detection.evidence["circular_reasoning_type"], "revisiting_rejected")
        self.assertGreaterEqual(detection.evidence["revisit_count"], 1)
    
    def test_multiple_revisits(self):
        """Test detection of multiple revisits."""
        decision_history = []
        options = ["A", "B", "C"]
        
        # Create pattern: reject A, reject B, reject C, revisit A, revisit B, revisit C
        for i in range(6):
            current_option = options[i % 3]
            other_options = [opt for opt in options if opt != current_option]
            
            decision_history.append({
                "decision_id": str(i),
                "action": current_option,
                "alternatives": other_options,
                "rejection_reason": f"Rejected {other_options[0]}"
            })
        
        detection = self.detector.detect_circular_reasoning_revisiting_rejected(
            decision_history,
            threshold=3
        )
        
        self.assertIsNotNone(detection)
        self.assertGreaterEqual(detection.evidence["revisit_count"], 3)
        self.assertGreaterEqual(detection.evidence["unique_options_revisited"], 2)
    
    def test_no_revisits_linear(self):
        """Test that linear decisions don't trigger revisit detection."""
        decision_history = [
            {"decision_id": "1", "action": "A", "alternatives": ["B", "C"]},
            {"decision_id": "2", "action": "D", "alternatives": ["E", "F"]},
            {"decision_id": "3", "action": "G", "alternatives": ["H", "I"]}
        ]
        
        detection = self.detector.detect_circular_reasoning_revisiting_rejected(
            decision_history,
            threshold=2
        )
        
        self.assertIsNone(detection)
    
    def test_revisit_severity_warning(self):
        """Test that few revisits have WARNING severity."""
        decision_history = [
            {"decision_id": "1", "action": "A", "alternatives": ["B"]},
            {"decision_id": "2", "action": "B", "alternatives": ["A"]},
            {"decision_id": "3", "action": "A", "alternatives": ["C"]}  # One revisit
        ]
        
        detection = self.detector.detect_circular_reasoning_revisiting_rejected(
            decision_history,
            threshold=1
        )
        
        self.assertIsNotNone(detection)
        self.assertEqual(detection.severity, TrapSeverity.WARNING)
    
    def test_revisit_severity_critical(self):
        """Test that many revisits have CRITICAL severity."""
        decision_history = []
        for i in range(7):
            decision_history.append({
                "decision_id": str(i),
                "action": "A" if i % 2 == 0 else "B",
                "alternatives": ["B" if i % 2 == 0 else "A"]
            })
        
        detection = self.detector.detect_circular_reasoning_revisiting_rejected(
            decision_history,
            threshold=3
        )
        
        self.assertIsNotNone(detection)
        self.assertEqual(detection.severity, TrapSeverity.CRITICAL)
    
    def test_revisit_details_tracked(self):
        """Test that revisit details are properly tracked."""
        decision_history = [
            {
                "decision_id": "1",
                "action": "Approach A",
                "alternatives": ["Approach B"],
                "rejection_reason": "B is complex"
            },
            {
                "decision_id": "2",
                "action": "Approach B",
                "alternatives": ["Approach C"],
                "timestamp": "2026-01-23T10:00:00Z"
            },
            {
                "decision_id": "3",
                "action": "Approach A",  # Revisit
                "alternatives": ["Approach D"],
                "timestamp": "2026-01-23T10:05:00Z"
            }
        ]
        
        detection = self.detector.detect_circular_reasoning_revisiting_rejected(
            decision_history,
            threshold=1
        )
        
        self.assertIsNotNone(detection)
        revisits = detection.evidence["revisits"]
        self.assertGreater(len(revisits), 0)
        
        # Check revisit details
        revisit = revisits[0]
        self.assertIn("option", revisit)
        self.assertIn("rejected_at", revisit)
        self.assertIn("revisited_at", revisit)
        self.assertIn("rejection_reason", revisit)
        self.assertIn("decisions_between", revisit)


class TestCircularReasoningContradictoryDecisions(unittest.TestCase):
    """Test contradictory decisions detection."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.detector = TrapDetector()
    
    def test_detect_strategy_contradiction(self):
        """Test detection of strategy contradictions."""
        decision_history = [
            {
                "decision_id": "1",
                "decision": "Use conservative strategy",
                "factors": {"strategy": "conservative"}
            },
            {
                "decision_id": "2",
                "decision": "Use aggressive strategy",
                "factors": {"strategy": "aggressive"}
            }
        ]
        
        detection = self.detector.detect_circular_reasoning_contradictory_decisions(
            decision_history
        )
        
        self.assertIsNotNone(detection)
        self.assertEqual(detection.trap_type, TrapType.CIRCULAR_REASONING)
        self.assertEqual(detection.evidence["circular_reasoning_type"], "contradictory_decisions")
        self.assertGreater(len(detection.evidence["contradictions"]), 0)
    
    def test_detect_toggle_contradiction(self):
        """Test detection of boolean toggle contradictions."""
        decision_history = [
            {
                "decision_id": "1",
                "decision": "Enable feature X",
                "factors": {"feature_x": "enabled"}
            },
            {
                "decision_id": "2",
                "decision": "Disable feature X",
                "factors": {"feature_x": "disabled"}
            }
        ]
        
        detection = self.detector.detect_circular_reasoning_contradictory_decisions(
            decision_history
        )
        
        self.assertIsNotNone(detection)
        contradictions = detection.evidence["contradictions"]
        self.assertEqual(contradictions[0]["pattern_type"], "toggle")
    
    def test_detect_direction_contradiction(self):
        """Test detection of direction contradictions."""
        decision_history = [
            {
                "decision_id": "1",
                "decision": "Increase resource allocation",
                "factors": {"resource_direction": "increase"}
            },
            {
                "decision_id": "2",
                "decision": "Decrease resource allocation",
                "factors": {"resource_direction": "decrease"}
            }
        ]
        
        detection = self.detector.detect_circular_reasoning_contradictory_decisions(
            decision_history
        )
        
        self.assertIsNotNone(detection)
        contradictions = detection.evidence["contradictions"]
        self.assertEqual(contradictions[0]["pattern_type"], "direction")
    
    def test_multiple_contradiction_types(self):
        """Test detection of multiple contradiction types."""
        decision_history = [
            {
                "decision_id": "1",
                "decision": "Use conservative strategy",
                "factors": {"strategy": "conservative", "priority": "high"}
            },
            {
                "decision_id": "2",
                "decision": "Use aggressive strategy",
                "factors": {"strategy": "aggressive", "priority": "low"}
            }
        ]
        
        detection = self.detector.detect_circular_reasoning_contradictory_decisions(
            decision_history
        )
        
        self.assertIsNotNone(detection)
        contradictions = detection.evidence["contradictions"]
        pattern_types = set(c["pattern_type"] for c in contradictions)
        self.assertIn("strategy", pattern_types)
        self.assertIn("priority", pattern_types)
    
    def test_no_contradictions_consistent(self):
        """Test that consistent decisions don't trigger contradiction detection."""
        decision_history = [
            {
                "decision_id": "1",
                "decision": "Use conservative strategy",
                "factors": {"strategy": "conservative"}
            },
            {
                "decision_id": "2",
                "decision": "Continue conservative approach",
                "factors": {"strategy": "conservative"}
            },
            {
                "decision_id": "3",
                "decision": "Maintain conservative strategy",
                "factors": {"strategy": "conservative"}
            }
        ]
        
        detection = self.detector.detect_circular_reasoning_contradictory_decisions(
            decision_history
        )
        
        self.assertIsNone(detection)
    
    def test_contradiction_severity_warning(self):
        """Test that few contradictions have WARNING severity."""
        decision_history = [
            {"decision_id": "1", "decision": "Enable X", "factors": {"x": "enabled"}},
            {"decision_id": "2", "decision": "Disable X", "factors": {"x": "disabled"}}
        ]
        
        detection = self.detector.detect_circular_reasoning_contradictory_decisions(
            decision_history
        )
        
        self.assertIsNotNone(detection)
        self.assertEqual(detection.severity, TrapSeverity.WARNING)
    
    def test_contradiction_severity_critical(self):
        """Test that many contradictions have CRITICAL severity."""
        # Use strategy toggles (conservative vs aggressive) which are in patterns
        decision_history = []
        for i in range(5):
            decision_history.append({
                "decision_id": str(i),
                "decision": "Use conservative" if i % 2 == 0 else "Use aggressive",
                "factors": {"strategy": "conservative" if i % 2 == 0 else "aggressive"}
            })
        
        detection = self.detector.detect_circular_reasoning_contradictory_decisions(
            decision_history
        )
        
        self.assertIsNotNone(detection)
        self.assertEqual(detection.severity, TrapSeverity.CRITICAL)
    
    def test_contradiction_details(self):
        """Test that contradiction details are properly tracked."""
        decision_history = [
            {
                "decision_id": "1",
                "decision": "First decision",
                "factors": {"approach": "conservative"}
            },
            {
                "decision_id": "5",
                "decision": "Last decision",
                "factors": {"approach": "aggressive"}
            }
        ]
        
        detection = self.detector.detect_circular_reasoning_contradictory_decisions(
            decision_history
        )
        
        self.assertIsNotNone(detection)
        contradictions = detection.evidence["contradictions"]
        self.assertGreater(len(contradictions), 0)
        
        # Check contradiction details
        contradiction = contradictions[0]
        self.assertIn("key", contradiction)
        self.assertIn("decision1_index", contradiction)
        self.assertIn("decision2_index", contradiction)
        self.assertIn("value1", contradiction)
        self.assertIn("value2", contradiction)
        self.assertIn("pattern_type", contradiction)


class TestCircularReasoningDependencies(unittest.TestCase):
    """Test dependency cycle detection."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.detector = TrapDetector()
    
    def test_detect_simple_dependency_cycle(self):
        """Test detection of simple dependency cycle."""
        decision_history = [
            {"decision_id": "1", "depends_on": ["2"]},
            {"decision_id": "2", "depends_on": ["3"]},
            {"decision_id": "3", "depends_on": ["1"]}
        ]
        
        detection = self.detector.detect_circular_reasoning_dependencies(
            decision_history,
            cycle_min_length=2
        )
        
        self.assertIsNotNone(detection)
        self.assertEqual(detection.trap_type, TrapType.CIRCULAR_REASONING)
        self.assertEqual(detection.evidence["circular_reasoning_type"], "dependency_cycle")
        self.assertGreaterEqual(detection.evidence["cycle_length"], 2)
    
    def test_detect_complex_dependency_cycle(self):
        """Test detection of complex dependency cycle."""
        decision_history = [
            {"decision_id": "1", "depends_on": ["2"]},
            {"decision_id": "2", "depends_on": ["3"]},
            {"decision_id": "3", "depends_on": ["4"]},
            {"decision_id": "4", "depends_on": ["5"]},
            {"decision_id": "5", "depends_on": ["1"]}
        ]
        
        detection = self.detector.detect_circular_reasoning_dependencies(
            decision_history,
            cycle_min_length=3
        )
        
        self.assertIsNotNone(detection)
        # Cycle has 5 nodes (1→2→3→4→5→1)
        self.assertEqual(detection.evidence["cycle_length"], 5)
        self.assertGreaterEqual(detection.confidence, 0.85)
    
    def test_no_dependency_chain(self):
        """Test that dependency chains without cycles don't trigger detection."""
        decision_history = [
            {"decision_id": "1", "depends_on": []},
            {"decision_id": "2", "depends_on": ["1"]},
            {"decision_id": "3", "depends_on": ["2"]},
            {"decision_id": "4", "depends_on": ["3"]}
        ]
        
        detection = self.detector.detect_circular_reasoning_dependencies(
            decision_history,
            cycle_min_length=2
        )
        
        self.assertIsNone(detection)
    
    def test_multiple_dependency_cycles(self):
        """Test detection of multiple dependency cycles."""
        decision_history = [
            {"decision_id": "1", "depends_on": ["2"]},
            {"decision_id": "2", "depends_on": ["1"]},
            {"decision_id": "3", "depends_on": ["4"]},
            {"decision_id": "4", "depends_on": ["3"]}
        ]
        
        detection = self.detector.detect_circular_reasoning_dependencies(
            decision_history,
            cycle_min_length=2
        )
        
        self.assertIsNotNone(detection)
        self.assertGreaterEqual(detection.evidence["total_cycles_found"], 2)
    
    def test_partial_dependencies_not_cycle(self):
        """Test that partial dependencies don't create false positives."""
        decision_history = [
            {"decision_id": "1", "depends_on": ["2"]},
            {"decision_id": "2", "depends_on": ["3", "4"]},
            {"decision_id": "3", "depends_on": []},
            {"decision_id": "4", "depends_on": []}
        ]
        
        detection = self.detector.detect_circular_reasoning_dependencies(
            decision_history,
            cycle_min_length=2
        )
        
        self.assertIsNone(detection)
    
    def test_dependency_cycle_severity(self):
        """Test severity calculation for dependency cycles."""
        # Short cycle (2 nodes)
        decision_history_short = [
            {"decision_id": "1", "depends_on": ["2"]},
            {"decision_id": "2", "depends_on": ["1"]}
        ]
        
        detection_short = self.detector.detect_circular_reasoning_dependencies(
            decision_history_short,
            cycle_min_length=2
        )
        
        self.assertIsNotNone(detection_short)
        self.assertEqual(detection_short.severity, TrapSeverity.WARNING)
        
        # Long cycle (4+ nodes)
        decision_history_long = []
        for i in range(5):
            decision_history_long.append({
                "decision_id": str(i),
                "depends_on": [str((i + 1) % 5)]
            })
        
        detection_long = self.detector.detect_circular_reasoning_dependencies(
            decision_history_long,
            cycle_min_length=2
        )
        
        self.assertIsNotNone(detection_long)
        self.assertEqual(detection_long.severity, TrapSeverity.CRITICAL)


class TestCircularReasoningIntegration(unittest.TestCase):
    """Integration tests for all circular reasoning detection methods."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.detector = TrapDetector()
    
    def test_detect_all_circular_reasoning(self):
        """Test that detect_all_circular_reasoning runs all detectors."""
        decision_history = [
            # Create dependency cycle (detected by dependency_cycle)
            {"decision_id": "1", "depends_on": ["3"]},
            {"decision_id": "2", "depends_on": []},
            {"decision_id": "3", "depends_on": ["1"]},
            # Create contradictory decisions
            {
                "decision_id": "4",
                "decision": "Use conservative",
                "factors": {"strategy": "conservative"}
            },
            {
                "decision_id": "5",
                "decision": "Use aggressive",
                "factors": {"strategy": "aggressive"}
            }
        ]
        
        detections = self.detector.detect_all_circular_reasoning(decision_history)
        
        # Should detect multiple types of circular reasoning
        self.assertGreater(len(detections), 0)
        
        # Check that different types are detected
        detected_types = set()
        for d in detections:
            type_key = d.evidence.get("circular_reasoning_type") or d.evidence.get("loop_type")
            detected_types.add(type_key)
        
        # Should detect dependency_cycle and contradictory_decisions
        self.assertIn("dependency_cycle", detected_types)
        self.assertIn("contradictory_decisions", detected_types)
    
    def test_no_circular_reasoning(self):
        """Test that clean decision history returns no detections."""
        decision_history = [
            {"decision_id": "1", "decision": "Start task A", "depends_on": []},
            {"decision_id": "2", "decision": "Complete task A", "depends_on": ["1"]},
            {"decision_id": "3", "decision": "Start task B", "depends_on": []},
            {"decision_id": "4", "decision": "Complete task B", "depends_on": ["3"]}
        ]
        
        detections = self.detector.detect_all_circular_reasoning(decision_history)
        
        self.assertEqual(len(detections), 0)
    
    def test_empty_decision_history(self):
        """Test that empty decision history doesn't crash."""
        detections = self.detector.detect_all_circular_reasoning([])
        
        self.assertEqual(len(detections), 0)
    
    def test_confidence_scores(self):
        """Test that confidence scores are reasonable."""
        # Create obvious circular reasoning (high confidence)
        decision_history_high = []
        for i in range(10):
            decision_history_high.append({
                "decision_id": str(i),
                "decision": f"Decision{i}",
                "depends_on": [str((i + 1) % 10)]
            })
        
        detections_high = self.detector.detect_all_circular_reasoning(decision_history_high)
        
        self.assertGreater(len(detections_high), 0)
        for detection in detections_high:
            self.assertGreater(detection.confidence, 0.7)
    
    def test_suggestions_provided(self):
        """Test that suggestions are provided for all detections."""
        decision_history = [
            {"decision_id": "1", "depends_on": ["2"]},
            {"decision_id": "2", "depends_on": ["3"]},
            {"decision_id": "3", "depends_on": ["1"]}  # Cycle
        ]
        
        detections = self.detector.detect_all_circular_reasoning(decision_history)
        
        for detection in detections:
            self.assertIsNotNone(detection.suggestion)
            self.assertGreater(len(detection.suggestion), 10)
            self.assertIn("cycle", detection.suggestion.lower())


if __name__ == "__main__":
    unittest.main()