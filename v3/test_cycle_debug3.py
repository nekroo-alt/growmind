#!/usr/bin/env python3
"""Debug script for cycle detection - using pytest path."""

import sys
import os

# Add v3 to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from v3.logic.trap_prevention import TrapPrevention

prevention = TrapPrevention()

# Create a cycle: A -> B, B -> A
print("=== Tracking Decision A (no dependencies) ===")
prevention.track_decision(decision="A", depends_on=[])
fingerprint_a = prevention._calculate_decision_fingerprint("A")
print(f"Fingerprint A: {fingerprint_a}")
print(f"Decision dependencies after A: {prevention.decision_dependencies}")

print("\n=== Tracking Decision B (depends on A) ===")
prevention.track_decision(decision="B", depends_on=[fingerprint_a])
fingerprint_b = prevention._calculate_decision_fingerprint("B")
print(f"Fingerprint B: {fingerprint_b}")
print(f"Decision dependencies after B: {prevention.decision_dependencies}")

print("\n=== Checking if A depends on B creates cycle ===")
print(f"Checking: {fingerprint_a} -> {fingerprint_b}")
print(f"Would A reach B? {prevention._can_reach(fingerprint_a, fingerprint_b)}")
print(f"Would B reach A? {prevention._can_reach(fingerprint_b, fingerprint_a)}")
print(f"Would A reach A (reverse)? {prevention._can_reach_reverse(fingerprint_a, fingerprint_b)}")
print(f"Would B reach A (reverse)? {prevention._can_reach_reverse(fingerprint_b, fingerprint_a)}")

result = prevention.check_decision_cycle(
    decision="A",
    depends_on=[fingerprint_b]
)

print(f"\nResult: {result}")