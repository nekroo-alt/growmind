#!/usr/bin/env python3
"""Debug test for no circular reasoning."""

import sys
sys.path.insert(0, '/Users/ken/Desktop/inno/growmind')

# Import directly to avoid __init__.py issues
exec(open('/Users/ken/Desktop/inno/growmind/v3/logic/trap_detector.py').read())

detector = TrapDetector()

# Test case from test_no_circular_reasoning
decision_history = [
    {"decision_id": "1", "decision": "Start task A", "depends_on": []},
    {"decision_id": "2", "decision": "Complete task A", "depends_on": ["1"]},
    {"decision_id": "3", "decision": "Start task B", "depends_on": []},
    {"decision_id": "4", "decision": "Complete task B", "depends_on": ["3"]}
]

print("=== Testing individual detection methods ===\n")

# Test decision cycle
result = detector.detect_circular_reasoning_decision_cycle(decision_history)
cycle_str = "DETECTED" if result else "NONE"
print(f"Decision cycle: {cycle_str}")
if result:
    print(f"  Type: {result.evidence.get('circular_reasoning_type')}")
    print(f"  Confidence: {result.confidence}")

# Test revisiting rejected
result = detector.detect_circular_reasoning_revisiting_rejected(decision_history)
revisit_str = "DETECTED" if result else "NONE"
print(f"\nRevisiting rejected: {revisit_str}")
if result:
    print(f"  Type: {result.evidence.get('circular_reasoning_type')}")
    print(f"  Confidence: {result.confidence}")

# Test contradictory decisions
result = detector.detect_circular_reasoning_contradictory_decisions(decision_history)
contrad_str = "DETECTED" if result else "NONE"
print(f"\nContradictory decisions: {contrad_str}")
if result:
    print(f"  Type: {result.evidence.get('circular_reasoning_type')}")
    print(f"  Confidence: {result.confidence}")

# Test dependency cycles
result = detector.detect_circular_reasoning_dependencies(decision_history)
dep_str = "DETECTED" if result else "NONE"
print(f"\nDependency cycles: {dep_str}")
if result:
    print(f"  Type: {result.evidence.get('circular_reasoning_type')}")
    print(f"  Confidence: {result.confidence}")
    print(f"  Cycle: {result.evidence.get('cycle_ids')}")

print("\n=== All detections ===")
detections = detector.detect_all_circular_reasoning(decision_history)
print(f"Total: {len(detections)}")
for i, det in enumerate(detections):
    print(f"\n{i+1}. Type: {det.evidence.get('circular_reasoning_type')}")
    print(f"   Confidence: {det.confidence}")