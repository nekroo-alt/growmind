#!/usr/bin/env python3
"""
Test script for TaskImpactAnalyzer.
Verifies that the analyzer can parse task descriptions and identify affected files.
"""

import os
import sys
import json

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from v5.logic import TaskImpactAnalyzer


def test_basic_entity_extraction():
    """Test basic entity extraction from task descriptions."""
    print("Test 1: Basic Entity Extraction")
    print("-" * 50)

    analyzer = TaskImpactAnalyzer(workspace_root=".")

    # Test with a task about SemanticMapper
    task_title = "Enhance SemanticMapper with call graph analysis"
    acceptance_criteria = (
        "SemanticMapper can construct a call graph showing which functions call which. "
        "Call graph includes inter-class method calls (e.g., self.method() calls)."
    )

    entities = analyzer._extract_entities_from_task(task_title, acceptance_criteria)

    print(f"Task: {task_title}")
    print(f"Extracted Entities:")
    print(json.dumps(entities, indent=2))

    # Check that at least some entities were extracted
    assert "modules" in entities
    assert "classes" in entities
    assert "functions" in entities
    assert "keywords" in entities

    print("✓ Entity extraction completed\n")


def test_file_scanning():
    """Test scanning project files for entity matches."""
    print("Test 2: File Scanning")
    print("-" * 50)

    analyzer = TaskImpactAnalyzer(workspace_root=".")

    # Define entities we want to find
    entities = {
        "classes": ["SemanticMapper", "Planner"],
        "functions": ["get_summary", "analyze_task_impact"],
        "modules": ["semantic_mapper", "task_impact_analyzer"],
        "keywords": ["database", "cache"],
    }

    file_matches = analyzer._find_files_with_entities(entities, None)

    print(f"Found matches in {len(file_matches)} files:")
    for file_path, matches in file_matches.items():
        print(f"\n  {file_path}:")
        print(f"    Classes: {matches['classes_matched']}")
        print(f"    Functions: {matches['functions_matched']}")
        print(f"    Modules: {matches['modules_matched']}")
        print(f"    Keywords: {matches['keywords_matched']}")

    # Check that we found at least some matches
    assert len(file_matches) > 0, "Expected to find at least one matching file"

    print("✓ File scanning completed\n")


def test_impact_scoring():
    """Test impact score calculation."""
    print("Test 3: Impact Scoring")
    print("-" * 50)

    analyzer = TaskImpactAnalyzer(workspace_root=".")

    # Create a sample scenario
    entities = {
        "classes": ["SemanticMapper"],
        "functions": ["get_summary", "analyze_task_impact"],
        "modules": [],
        "keywords": [],
    }

    # Get file matches first
    file_matches = analyzer._find_files_with_entities(entities, None)

    if len(file_matches) > 0:
        # Calculate scores
        scored_files = analyzer._calculate_impact_scores(file_matches, entities)

        print("Impact Scores:")
        for file_info in scored_files:
            print(f"\n  {file_info['file_path']}:")
            print(f"    Score: {file_info['impact_score']} ({file_info['confidence']})")
            print(f"    Match Count: {file_info['match_count']}")
            print(f"    Matches: {file_info['matches']}")

        # Verify scores are in [0, 1] range
        for file_info in scored_files:
            assert (
                0 <= file_info["impact_score"] <= 1
            ), "Impact score must be between 0 and 1"

        # Verify sorted order (descending)
        scores = [f["impact_score"] for f in scored_files]
        assert scores == sorted(
            scores, reverse=True
        ), "Files should be sorted by score descending"

        print("✓ Impact scoring completed\n")
    else:
        print("⚠ No file matches found, skipping scoring test\n")


def test_full_analysis():
    """Test complete task impact analysis."""
    print("Test 4: Full Task Impact Analysis")
    print("-" * 50)

    analyzer = TaskImpactAnalyzer(workspace_root=".")

    # Real task from v2_tasks.md
    task_title = "Create TaskImpactAnalyzer to predict which code a task will affect"
    acceptance_criteria = (
        "Analyze task title and acceptance criteria to identify target modules. "
        "Parse acceptance criteria for function/class references. "
        "Predict which files will need to be modified based on task description. "
        "Return a prioritized list of files with impact confidence scores."
    )

    analysis = analyzer.analyze_task_impact(task_title, acceptance_criteria)

    print(f"Task: {task_title}")
    print(f"\nExtracted Entities:")
    print(f"  Modules: {analysis['target_modules']}")
    print(f"  Classes: {analysis['target_classes']}")
    print(f"  Functions: {analysis['target_functions']}")

    print(f"\nAffected Files (Top 5):")
    for i, file_info in enumerate(analysis["affected_files"][:5], 1):
        print(f"  {i}. {file_info['file_path']}")
        print(f"     Score: {file_info['impact_score']} ({file_info['confidence']})")
        print(f"     Matches: {file_info['matches']}")

    print(f"\nAnalysis Metadata:")
    print(f"  Entities found: {analysis['analysis_metadata']['entities_found']}")
    print(f"  Files scanned: {analysis['analysis_metadata']['files_scanned']}")
    print(f"  High impact files: {analysis['analysis_metadata']['high_impact_files']}")

    # Verify structure
    assert "affected_files" in analysis
    assert "target_modules" in analysis
    assert "analysis_metadata" in analysis

    print("✓ Full analysis completed\n")


def test_recommended_files():
    """Test getting recommended files with filters."""
    print("Test 5: Recommended Files")
    print("-" * 50)

    analyzer = TaskImpactAnalyzer(workspace_root=".")

    task_title = "Enhance SemanticMapper with data flow analysis"
    acceptance_criteria = "SemanticMapper can track which variables are read and written in each function."

    # Get all recommended files
    all_files = analyzer.get_recommended_files(
        task_title, acceptance_criteria, max_files=10, min_confidence="low"
    )

    print(f"All recommended files (low confidence): {len(all_files)}")
    for i, file_path in enumerate(all_files, 1):
        print(f"  {i}. {file_path}")

    # Get only high confidence files
    high_conf_files = analyzer.get_recommended_files(
        task_title, acceptance_criteria, max_files=10, min_confidence="high"
    )

    print(f"\nHigh confidence files: {len(high_conf_files)}")
    for i, file_path in enumerate(high_conf_files, 1):
        print(f"  {i}. {file_path}")

    print("✓ Recommended files completed\n")


def test_cache_functionality():
    """Test that semantic map caching works."""
    print("Test 6: Cache Functionality")
    print("-" * 50)

    analyzer = TaskImpactAnalyzer(workspace_root=".")

    # First call should populate cache
    print("First analysis (should populate cache)...")
    task_title = "Test caching functionality"
    analysis1 = analyzer.analyze_task_impact(task_title)

    cache_size = len(analyzer.semantic_cache)
    print(f"Cache size after first analysis: {cache_size}")

    # Second call should use cache
    print("\nSecond analysis (should use cache)...")
    task_title2 = "Test cache again"
    analysis2 = analyzer.analyze_task_impact(task_title2)

    cache_size2 = len(analyzer.semantic_cache)
    print(f"Cache size after second analysis: {cache_size2}")

    # Clear cache
    print("\nClearing cache...")
    analyzer.clear_cache()
    cache_size3 = len(analyzer.semantic_cache)
    print(f"Cache size after clearing: {cache_size3}")

    assert cache_size3 == 0, "Cache should be empty after clearing"

    print("✓ Cache functionality verified\n")


def main():
    """Run all tests."""
    print("=" * 60)
    print("TaskImpactAnalyzer Test Suite")
    print("=" * 60)
    print()

    tests = [
        test_basic_entity_extraction,
        test_file_scanning,
        test_impact_scoring,
        test_full_analysis,
        test_recommended_files,
        test_cache_functionality,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"✗ Test failed: {e}\n")
            failed += 1
        except Exception as e:
            print(f"✗ Test error: {e}\n")
            failed += 1

    print("=" * 60)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
