#!/usr/bin/env python3
"""Debug script for cycle detection test."""

import sys
sys.path.insert(0, '/Users/ken/Desktop/inno/growmind/v3')

from logic.trap_prevention import TrapPrevention

prevention = TrapPrevention()

# Create a cycle: A -> B, B -> A
prevention.track_decision(decision="A", depends_on=[])
fingerprint_a = prevention._calculate_decision_fingerprint("A")
prevention.track_decision(decision="B", depends_on=[fingerprint_a])

print("Dependencies:")
for key, deps in prevention.decision_dependencies.items():
    print(f"  {key} depends on: {deps}")

print()
print("Testing: decision A depends on B")
decision_id = prevention._calculate_decision_fingerprint("A")
dep_id = prevention._calculate_decision_fingerprint("B")

print(f"  decision_id (A): {decision_id}")
print(f"  dep_id (B): {dep_id}")
print()
print("Can A reach B?", prevention._can_reach(decision_id, dep_id))
print("Can B reach A?", prevention._can_reach(dep_id, decision_id))
print("Can A reach A (reverse)?", prevention._can_reach_reverse(decision_id, dep_id))
print("Can B reach A (reverse)?", prevention._can_reach_reverse(dep_id, decision_id))

result = prevention.check_decision_cycle(
    decision="A",
    depends_on=[prevention._calculate_decision_fingerprint("B")]
)

print()
print("Result:", result)
print("Expected: PreventionAction (cycle detected)")
print("Status:", "PASS" if result is not None else "FAIL")