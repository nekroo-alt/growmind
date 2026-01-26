#!/usr/bin/env python
"""
Script to organize test files into subdirectories matching code structure.

Maps test files to their target subdirectories based on what they test.
"""

import os
import shutil
from pathlib import Path

# Mapping of test files to their target subdirectories
# Based on imports in each test file
TEST_MAPPING = {
    # Core tests
    "test_logging.py": "core",
    "test_telemetry.py": "core",
    
    # Data tests
    "test_call_graph.py": "data",
    "test_data_flow.py": "data",
    
    # Logic tests
    "test_action_validator.py": "logic",
    "test_adaptive_heuristics.py": "logic",
    "test_context_analyzer.py": "logic",
    "test_context_expander.py": "logic",
    "test_context_scorer.py": "logic",
    "test_context_summarizer.py": "logic",
    "test_dead_code_detector.py": "logic",
    "test_decision_maker.py": "logic",
    "test_decision_history.py": "logic",
    "test_decision_tracer.py": "logic",
    "test_dependency_analyzer.py": "logic",
    "test_explanation_generator.py": "logic",
    "test_file_usage_tracker.py": "logic",
    "test_import_analysis.py": "logic",
    "test_import_analyzer.py": "logic",
    "test_lesson_learner.py": "logic",
    "test_local_decision_engine.py": "logic",
    "test_pattern_recognizer.py": "logic",
    "test_progress_predictor.py": "logic",
    "test_progress_tracker.py": "logic",
    "test_safe_deleter.py": "logic",
    "test_self_reflection.py": "logic",
    "test_strategy_comparison_ranking.py": "logic",
    "test_strategy_evaluator.py": "logic",
    "test_strategy_hybridizer.py": "logic",
    "test_strategy_selector.py": "logic",
    "test_strategy_switcher.py": "logic",
    "test_trap_detector.py": "logic",
    "test_trap_prevention.py": "logic",
    "test_trap_recovery.py": "logic",
    "test_type_hints_simple.py": "logic",
    "test_type_hints.py": "logic",
    
    # Misc tests (stay in unit/ root)
    "test_circular_reasoning.py": "unit",
    "test_checkpoint.py": "unit",
    "test_cleanup_manager.py": "unit",
    "test_config_validator.py": "unit",
    "test_cost_tracker.py": "unit",
}


def organize_tests(dry_run=True):
    """Organize test files into subdirectories."""
    # Get script directory and navigate to tests/unit
    script_dir = Path(__file__).parent
    tests_dir = script_dir / "tests" / "unit"
    
    if not tests_dir.exists():
        print(f"Tests directory not found: {tests_dir}")
        return
    
    moved = []
    skipped = []
    
    for test_file, target_dir in TEST_MAPPING.items():
        source_path = tests_dir / test_file
        
        if not source_path.exists():
            skipped.append((test_file, "File not found"))
            continue
        
        # Skip if file should stay in unit/ root
        if target_dir == "unit":
            skipped.append((test_file, "Stays in unit/ root"))
            continue
        
        target_path = tests_dir / target_dir / test_file
        
        # Create target directory if it doesn't exist
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        if dry_run:
            moved.append((test_file, target_dir))
        else:
            try:
                shutil.move(str(source_path), str(target_path))
                moved.append((test_file, target_dir))
                print(f"Moved: {test_file} -> {target_dir}/")
            except Exception as e:
                skipped.append((test_file, str(e)))
    
    # Print summary
    print("\n" + "="*60)
    print("TEST ORGANIZATION SUMMARY")
    print("="*60)
    
    if moved:
        print(f"\nFiles to move ({len(moved)}):")
        for test_file, target_dir in sorted(moved):
            print(f"  {test_file} -> {target_dir}/")
    
    if skipped:
        print(f"\nSkipped ({len(skipped)}):")
        for test_file, reason in sorted(skipped):
            print(f"  {test_file}: {reason}")
    
    print("\n" + "="*60)
    
    return moved, skipped


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Organize test files into subdirectories")
    parser.add_argument("--dry-run", action="store_true", default=True,
                       help="Show what would be done without actually moving files")
    parser.add_argument("--execute", action="store_true",
                       help="Actually move the files (disables dry-run)")
    
    args = parser.parse_args()
    
    if args.execute:
        dry_run = False
        print("EXECUTING TEST ORGANIZATION")
    else:
        dry_run = True
        print("DRY RUN - Use --execute to actually move files")
    
    organize_tests(dry_run=dry_run)