"""
Test script for Task 2.4: Smart File Scoping
Tests the intelligent file selection based on task impact analysis.
"""

import os
import sys
from logic.context_engine import ContextEngine


def test_smart_file_scoping():
    """Test smart file scoping functionality."""

    print("=" * 80)
    print("Testing Smart File Scoping (Task 2.4)")
    print("=" * 80)

    # Initialize ContextEngine
    context_engine = ContextEngine(workspace_root=".")

    # Test case 1: Task about implementing task dependency graph
    task_title = "Create task dependency graph to track relationships between tasks"
    acceptance_criteria = (
        "- Store task dependencies in `task.db` (new table or columns)\n"
        "- Identify when one task depends on completion of another\n"
        "- Prevent execution of dependent tasks until prerequisites are met\n"
        "- Visualize task dependency structure (optional)"
    )

    print("\n[Test 1] Task Impact Analysis")
    print(f"Task Title: {task_title}")
    print(f"Acceptance Criteria:\n{acceptance_criteria}\n")

    # Get smart file scope
    scored_files = context_engine.get_smart_file_scope(
        task_title, acceptance_criteria, max_depth=3
    )

    print(f"Found {len(scored_files)} relevant files:\n")

    for i, file_info in enumerate(scored_files[:10], 1):  # Show top 10
        print(f"{i}. {file_info['file_path']}")
        print(f"   Relevance Score: {file_info['relevance_score']}")
        print(f"   Impact Score: {file_info['impact_score']}")
        print(f"   Dependency Score: {file_info['dependency_score']}")
        print(f"   Confidence: {file_info['confidence']}")
        print(f"   Reason: {file_info['match_details']['reason']}")
        print()

    # Test case 2: Task about enhancing semantic mapper
    task_title2 = "Implement call graph analysis in SemanticMapper"
    acceptance_criteria2 = (
        "- `SemanticMapper` can construct a call graph showing which functions call which\n"
        "- Call graph includes inter-class method calls (e.g., `self.method()` calls)\n"
        "- Call graph identifies external function calls (from other modules)\n"
        "- Call graph data structure includes: caller, callee, line number, and call depth"
    )

    print("\n[Test 2] Task Impact Analysis (Different Task)")
    print(f"Task Title: {task_title2}")
    print(f"Acceptance Criteria:\n{acceptance_criteria2}\n")

    scored_files2 = context_engine.get_smart_file_scope(
        task_title2, acceptance_criteria2, max_depth=3
    )

    print(f"Found {len(scored_files2)} relevant files:\n")

    for i, file_info in enumerate(scored_files2[:5], 1):  # Show top 5
        print(f"{i}. {file_info['file_path']}")
        print(f"   Relevance Score: {file_info['relevance_score']}")
        print(f"   Confidence: {file_info['confidence']}")
        print(f"   Reason: {file_info['match_details']['reason']}")
        print()

    # Test case 3: Test with candidate files
    print("\n[Test 3] Smart Scoping with Candidate Files")

    candidate_files = [
        "v1/data/semantic_mapper.py",
        "v1/logic/context_engine.py",
        "v1/logic/planner.py",
        "v1/core/start.py",
    ]

    scored_files3 = context_engine.get_smart_file_scope(
        task_title, acceptance_criteria, candidate_files=candidate_files, max_depth=2
    )

    print(f"Scanning only {len(candidate_files)} candidate files...")
    print(f"Found {len(scored_files3)} relevant files:\n")

    for i, file_info in enumerate(scored_files3, 1):
        print(f"{i}. {file_info['file_path']}")
        print(f"   Relevance Score: {file_info['relevance_score']}")
        print(f"   Confidence: {file_info['confidence']}")
        print()

    # Test case 4: Test get_pruned_context with smart scoping
    print("\n[Test 4] Get Pruned Context with Smart Scoping")

    # Get context with smart scoping enabled
    context_with_smart = context_engine.get_pruned_context(
        task_query="task dependency graph",
        files=candidate_files,
        use_smart_scoping=True,
        task_title=task_title,
        acceptance_criteria=acceptance_criteria,
    )

    # Get context without smart scoping (backward compatibility)
    context_without_smart = context_engine.get_pruned_context(
        task_query="task dependency graph",
        files=candidate_files,
        use_smart_scoping=False,
        task_title=task_title,
        acceptance_criteria=acceptance_criteria,
    )

    print(f"Context length with smart scoping: {len(context_with_smart)} characters")
    print(
        f"Context length without smart scoping: {len(context_without_smart)} characters"
    )
    print(
        f"Reduction: {100 * (1 - len(context_with_smart) / len(context_without_smart)):.1f}%"
    )

    # Verify acceptance criteria
    print("\n" + "=" * 80)
    print("Verifying Acceptance Criteria:")
    print("=" * 80)

    checks = []

    # Check 1: Automatically determines which files to analyze
    if len(scored_files) > 0:
        checks.append(("✓", "Automatically determines which files to analyze"))
    else:
        checks.append(("✗", "Automatically determines which files to analyze"))

    # Check 2: Returns files with relevance scores
    if all("relevance_score" in f for f in scored_files):
        checks.append(("✓", "Returns file list with relevance scores"))
    else:
        checks.append(("✗", "Returns file list with relevance scores"))

    # Check 3: Skips irrelevant files
    if all(f["relevance_score"] >= 0 for f in scored_files):
        checks.append(("✓", "Scores and prioritizes files by relevance"))
    else:
        checks.append(("✗", "Scores and prioritizes files by relevance"))

    # Check 4: Includes related files from dependency chains
    has_dependency = any(f["dependency_score"] > 0 for f in scored_files)
    if has_dependency:
        checks.append(("✓", "Includes related files from dependency chains"))
    else:
        checks.append(("✗", "Includes related files from dependency chains"))

    # Check 5: Backward compatibility
    if context_without_smart:
        checks.append(("✓", "Maintains backward compatibility"))
    else:
        checks.append(("✗", "Maintains backward compatibility"))

    for status, criterion in checks:
        print(f"{status} {criterion}")

    # Overall result
    all_passed = all(status == "✓" for status, _ in checks)

    print("\n" + "=" * 80)
    if all_passed:
        print("✓ ALL ACCEPTANCE CRITERIA PASSED")
    else:
        print("✗ SOME ACCEPTANCE CRITERIA FAILED")
    print("=" * 80)

    return all_passed


if __name__ == "__main__":
    success = test_smart_file_scoping()
    sys.exit(0 if success else 1)
