#!/usr/bin/env python3
"""
Test script for Task 3.3: Context-Aware Acceptance Criteria
Tests the enhancement of acceptance criteria with context-aware checks.
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from v1.logic.planner import Planner


def test_enhance_acceptance_criteria():
    """Test the _enhance_acceptance_criteria method."""
    print("Testing context-aware acceptance criteria enhancement...")
    
    # Initialize planner
    planner = Planner(workspace_root=".")
    
    # Create sample subtasks
    subtasks = [
        {
            "title": "Add method to Planner class",
            "acceptance_criteria": "Implement the new method",
            "module": "v1/logic/planner.py",
            "target_class": "Planner",
            "target_function": "_enhance_acceptance_criteria",
            "estimated_lines": 25
        }
    ]
    
    # Create sample impact analysis
    impact_analysis = {
        "target_modules": ["v1/logic/planner.py"],
        "target_classes": ["Planner"],
        "target_functions": ["_enhance_acceptance_criteria"],
        "upstream_dependencies": ["ContextEngine", "TaskImpactAnalyzer"],
        "downstream_consumers": ["Implementor"],
        "affected_files": [
            {
                "file_path": "v1/logic/planner.py",
                "impact_score": 0.95,
                "confidence": "high"
            }
        ]
    }
    
    # Create sample code structure info
    code_structure_info = {
        "target_modules": ["v1/logic/planner.py"],
        "target_classes": [
            {
                "name": "Planner",
                "file": "v1/logic/planner.py",
                "methods": ["breakdown_requirements", "_build_enhanced_system_prompt"],
                "start_line": 14,
                "end_line": 500
            }
        ],
        "target_functions": [
            {
                "name": "_enhance_acceptance_criteria",
                "file": "v1/logic/planner.py",
                "start_line": 280,
                "end_line": 350
            }
        ],
        "file_structure": {
            "v1/logic/planner.py": {
                "classes": ["Planner"],
                "functions": ["breakdown_requirements"],
                "impact_score": 0.95
            }
        }
    }
    
    # Call the method
    enhanced_tasks = planner._enhance_acceptance_criteria(
        subtasks, impact_analysis, code_structure_info
    )
    
    # Verify results
    assert len(enhanced_tasks) == 1, "Should have one enhanced task"
    
    enhanced_task = enhanced_tasks[0]
    print(f"\nOriginal criteria: {subtasks[0]['acceptance_criteria']}")
    print(f"\nEnhanced criteria:\n{enhanced_task['acceptance_criteria']}")
    
    # Check that context-aware requirements were added
    assert "**Context-Aware Requirements:**" in enhanced_task["acceptance_criteria"], \
        "Should include context-aware requirements section"
    
    # Check for specific requirement types
    criteria_text = enhanced_task["acceptance_criteria"]
    assert any("Integration with existing" in line for line in criteria_text.split("\n")), \
        "Should include context integration checks"
    assert any("Integration tests" in line or "Mutation testing" in line for line in criteria_text.split("\n")), \
        "Should include testing requirements"
    
    print("\n✓ Context-aware acceptance criteria enhancement test passed!")
    print(f"✓ Generated {len([line for line in criteria_text.split('\n') if line.strip().startswith('-')])} context-aware checks")
    
    return True


def test_generate_methods():
    """Test individual generation methods."""
    print("\nTesting individual generation methods...")
    
    planner = Planner(workspace_root=".")
    
    # Create sample data
    task = {
        "title": "Add method to Planner",
        "module": "v1/logic/planner.py",
        "target_class": "Planner",
        "target_function": "new_method"
    }
    
    impact_analysis = {
        "upstream_dependencies": ["ContextEngine"],
        "downstream_consumers": ["Implementor"],
        "affected_files": [
            {"file_path": "v1/logic/planner.py", "impact_score": 0.9, "confidence": "high"}
        ]
    }
    
    code_structure_info = {
        "target_classes": [
            {
                "name": "Planner",
                "methods": ["method1", "method2"]
            }
        ]
    }
    
    # Test context integration checks
    checks = planner._generate_context_integration_checks(task, impact_analysis, code_structure_info)
    print(f"\nContext integration checks: {len(checks)}")
    for check in checks:
        print(f"  - {check}")
    assert len(checks) > 0, "Should generate context integration checks"
    
    # Test dependency contract checks
    checks = planner._generate_dependency_contract_checks(task, impact_analysis)
    print(f"\nDependency contract checks: {len(checks)}")
    for check in checks:
        print(f"  - {check}")
    assert len(checks) > 0, "Should generate dependency contract checks"
    
    # Test downstream consumer checks
    checks = planner._generate_downstream_consumer_checks(task, impact_analysis)
    print(f"\nDownstream consumer checks: {len(checks)}")
    for check in checks:
        print(f"  - {check}")
    assert len(checks) > 0, "Should generate downstream consumer checks"
    
    # Test side effect checks
    checks = planner._generate_side_effect_checks(task, impact_analysis)
    print(f"\nSide effect checks: {len(checks)}")
    for check in checks:
        print(f"  - {check}")
    
    # Test integration test requirements
    checks = planner._generate_integration_test_requirements(task, impact_analysis)
    print(f"\nIntegration test requirements: {len(checks)}")
    for check in checks:
        print(f"  - {check}")
    
    # Test mutation test requirements
    checks = planner._generate_mutation_test_requirements(task)
    print(f"\nMutation test requirements: {len(checks)}")
    for check in checks:
        print(f"  - {check}")
    assert len(checks) > 0, "Should generate mutation test requirements"
    
    # Test API change checks
    checks = planner._generate_api_change_checks(task, impact_analysis)
    print(f"\nAPI change checks: {len(checks)}")
    for check in checks:
        print(f"  - {check}")
    assert len(checks) > 0, "Should generate API change checks"
    
    print("\n✓ Individual generation method tests passed!")
    return True


if __name__ == "__main__":
    print("=" * 60)
    print("Task 3.3: Context-Aware Acceptance Criteria Tests")
    print("=" * 60)
    
    try:
        # Run tests
        test_enhance_acceptance_criteria()
        test_generate_methods()
        
        print("\n" + "=" * 60)
        print("All tests passed successfully! ✓")
        print("=" * 60)
        sys.exit(0)
        
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
