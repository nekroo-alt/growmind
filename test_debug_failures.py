#!/usr/bin/env python3
"""Debug test failures."""

from v3.logic.trap_detector import TrapDetector

def test_no_circular_reasoning():
    """Test that clean decision history returns no detections."""
    detector = TrapDetector()
    decision_history = [
        {"decision_id": "1", "decision": "Start task A", "depends_on": []},
        {"decision_id": "2", "decision": "Complete task A", "depends_on": ["1"]},
        {"decision_id": "3", "decision": "Start task B", "depends_on": []},
        {"decision_id": "4", "decision": "Complete task B", "depends_on": ["3"]}
    ]
    
    detections = detector.detect_all_circular_reasoning(decision_history)
    
    print(f"Number of detections: {len(detections)}")
    for i, detection in enumerate(detections):
        print(f"\nDetection {i+1}:")
        print(f"  Type: {detection.trap_type}")
        print(f"  Evidence: {detection.evidence}")

def test_confidence_scores():
    """Test confidence scores."""
    detector = TrapDetector()
    decision_history_high = []
    for i in range(10):
        decision_history_high.append({
            "decision_id": str(i),
            "decision": f"Decision{i}",
            "depends_on": [str((i + 1) % 10)]
        })
    
    detections_high = detector.detect_all_circular_reasoning(decision_history_high)
    
    print(f"\nNumber of detections: {len(detections_high)}")
    for i, detection in enumerate(detections_high):
        print(f"\nDetection {i+1}:")
        print(f"  Confidence: {detection.confidence}")
        print(f"  Evidence: {detection.evidence}")

if __name__ == "__main__":
    print("=== Testing no_circular_reasoning ===")
    test_no_circular_reasoning()
    print("\n\n=== Testing confidence_scores ===")
    test_confidence_scores()