#!/usr/bin/env python3
"""Debug script for cycle detection logic."""

from collections import defaultdict

def _can_reach(decision_dependencies, start_id: str, target_id: str) -> bool:
    """
    Check if start_id can reach target_id through dependencies.
    """
    # If start_id doesn't exist in dependencies, can't reach anything
    if start_id not in decision_dependencies:
        return False
    
    if start_id == target_id:
        return True
    
    visited = set()
    
    def dfs(current_id: str) -> bool:
        """Depth-first search to find path."""
        if current_id == target_id:
            return True
        if current_id in visited:
            return False
        
        visited.add(current_id)
        
        # Follow all dependencies from current_id
        for next_id in decision_dependencies.get(current_id, set()):
            if dfs(next_id):
                return True
        
        return False
    
    return dfs(start_id)

def _would_create_cycle(decision_dependencies, decision_id: str, dep_id: str) -> bool:
    """
    Check if adding dependency would create a cycle.
    """
    # The dependencies dict represents: X -> Y means "X depends on Y"
    # We're adding: decision_id depends on dep_id
    # This would create a cycle if dep_id can already reach decision_id
    
    # Check if dep_id can reach decision_id through existing dependencies
    return _can_reach(decision_dependencies, dep_id, decision_id)

# Test case from unit test
decision_dependencies = {
    'A': set(),
    'B': {'A'},
    'C': {'B'}
}

print('Dependencies:')
for key, deps in decision_dependencies.items():
    print(f'  {key} depends on: {deps}')

print()
print('Path analysis:')
print(f'  Can A reach A? {_can_reach(decision_dependencies, "A", "A")}')
print(f'  Can B reach A? {_can_reach(decision_dependencies, "B", "A")}')
print(f'  Can C reach A? {_can_reach(decision_dependencies, "C", "A")}')
print(f'  Can A reach C? {_can_reach(decision_dependencies, "A", "C")}')
print(f'  Can C reach B? {_can_reach(decision_dependencies, "C", "B")}')

print()
print('Cycle detection:')
print('  Adding C -> A would mean: C depends on A')
print('  Current graph: A <- B <- C')
print('  After adding: A <- B <- C <- A (CYCLE!)')
print(f'  Would adding C -> A create cycle? {_would_create_cycle(decision_dependencies, "C", "A")}')

print()
print('Expected: True')
print('Actual:', _would_create_cycle(decision_dependencies, "C", "A"))
print('Status:', 'PASS' if _would_create_cycle(decision_dependencies, "C", "A") else 'FAIL')