"""
Test for AST-informed task breakdown in Planner (Task 3.2)
"""

import os
import sys
import json
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from v1.logic.planner import Planner


def test_planner_initialization():
    """Test that Planner initializes with TaskImpactAnalyzer."""
    planner = Planner()
    assert hasattr(planner, 'task_impact_analyzer'), "Planner should have task_impact_analyzer"
    assert hasattr(planner, 'semantic_mappers'), "Planner should have semantic_mappers cache"
    print("✓ Planner initialization test passed")


def test_build_semantic_mappers():
    """Test building semantic mappers for affected files."""
    planner = Planner()
    
    # Create mock affected files
    affected_files = [
        {"file_path": "v1/logic/planner.py", "impact_score": 0.9},
        {"file_path": "v1/data/semantic_mapper.py", "impact_score": 0.8}
    ]
    
    planner._build_semantic_mappers(affected_files)
    
    # Verify that semantic mappers were created
    assert len(planner.semantic_mappers) > 0, "Should have created semantic mappers"
    print(f"✓ Build semantic mappers test passed (created {len(planner.semantic_mappers)} mappers)")


def test_get_relevant_files():
    """Test filtering relevant files by confidence level."""
    planner = Planner()
    
    # Create mock impact analysis
    impact_analysis = {
        "affected_files": [
            {"file_path": "high_impact.py", "impact_score": 0.9, "confidence": "high"},
            {"file_path": "medium_impact.py", "impact_score": 0.5, "confidence": "medium"},
            {"file_path": "low_impact.py", "impact_score": 0.1, "confidence": "low"}
        ]
    }
    
    relevant_files = planner._get_relevant_files(impact_analysis)
    
    # Should only include high and medium confidence files
    assert len(relevant_files) == 2, f"Should include 2 files, got {len(relevant_files)}"
    assert "high_impact.py" in relevant_files, "Should include high confidence file"
    assert "medium_impact.py" in relevant_files, "Should include medium confidence file"
    assert "low_impact.py" not in relevant_files, "Should not include low confidence file"
    print("✓ Get relevant files test passed")


def test_validate_and_estimate_subtasks():
    """Test subtask validation and line estimation."""
    planner = Planner()
    
    # Create mock subtasks
    subtasks_data = [
        {
            "title": "Add method to MyClass",
            "acceptance_criteria": "Method should return string",
            "module": "mymodule.py",
            "target_class": "MyClass"
        },
        {
            "title": "Add method to MyClass",  # Duplicate target
            "acceptance_criteria": "Different criteria",
            "module": "mymodule.py",
            "target_class": "MyClass"
        },
        {
            "title": "Large task",
            "acceptance_criteria": "This is too big",
            "estimated_lines": 50  # Exceeds limit
        },
        {
            "title": "Task without estimate",
            "acceptance_criteria": "Should get default"
        }
    ]
    
    impact_analysis = {
        "target_classes": ["MyClass", "OtherClass"],
        "target_functions": []
    }
    
    validated = planner._validate_and_estimate_subtasks(subtasks_data, impact_analysis)
    
    assert len(validated) == 4, "Should validate all tasks"
    assert validated[1].get("validation_warning") is not None, "Should detect overlap"
    assert validated[2]["estimated_lines"] == 30, "Should cap at 30 lines"
    assert validated[3]["estimated_lines"] == 25, "Should default to 25 lines"
    print("✓ Validate and estimate subtasks test passed")


def test_create_task_key():
    """Test task key creation for overlap detection."""
    planner = Planner()
    
    task = {
        "title": "Add method to MyClass",
        "module": "mymodule.py",
        "target_class": "MyClass",
        "target_function": None
    }
    
    impact_analysis = {
        "target_classes": ["MyClass"],
        "target_functions": []
    }
    
    key = planner._create_task_key(task, impact_analysis)
    
    assert key == ("mymodule.py", "MyClass", None), f"Expected ('mymodule.py', 'MyClass', None), got {key}"
    print("✓ Create task key test passed")


def test_prepare_code_structure_info():
    """Test preparing code structure information."""
    planner = Planner()
    
    # First build semantic mappers
    affected_files = [
        {"file_path": "v1/logic/planner.py", "impact_score": 0.9}
    ]
    planner._build_semantic_mappers(affected_files)
    
    impact_analysis = {
        "target_modules": ["logic"],
        "target_classes": ["Planner"],
        "target_functions": ["breakdown_requirements"],
        "affected_files": affected_files
    }
    
    structure_info = planner._prepare_code_structure_info(impact_analysis)
    
    assert "target_modules" in structure_info
    assert "target_classes" in structure_info
    assert "target_functions" in structure_info
    assert "file_structure" in structure_info
    print("✓ Prepare code structure info test passed")


if __name__ == "__main__":
    print("\n=== Testing AST-Informed Planner (Task 3.2) ===\n")
    
    try:
        test_planner_initialization()
        test_build_semantic_mappers()
        test_get_relevant_files()
        test_validate_and_estimate_subtasks()
        test_create_task_key()
        test_prepare_code_structure_info()
        
        print("\n=== All tests passed! ===\n")
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
