#!/usr/bin/env python3
"""Debug circular reasoning detection."""

from v3.logic.trap_detector import create_trap_detector

def test_simple():
    """Test detection of simple decision cycle (A → B → A)."""
    detector = create_trap_detector()
    decision_history = [
        {"decision_id": "1", "action": "A", "parent_id": None},
        {"decision_id": "2", "action": "B", "parent_id": "1"},
        {"decision_id": "3", "action": "A", "parent_id": "2"}
    ]
    
    print("Decision history:")
    for d in decision_history:
        print(f"  {d}")
    
    detection = detector.detect_circular_reasoning_decision_cycle(
        decision_history,
        cycle_min_length=2
    )
    
    print(f"\nDetection result: {detection}")
    
    if detection:
        print(f"  Type: {detection.trap_type}")
        print(f"  Severity: {detection.severity}")
        print(f"  Confidence: {detection.confidence}")
        print(f"  Evidence: {detection.evidence}")
        print(f"  Suggestion: {detection.suggestion}")

if __name__ == "__main__":
    test_simple()