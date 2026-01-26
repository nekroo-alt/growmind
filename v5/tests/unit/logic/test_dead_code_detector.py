"""
Unit tests for DeadCodeDetector module (V5 Task 2.1)
"""

import unittest
import os
import tempfile
import shutil
from pathlib import Path

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from v5.logic.dead_code_detector import (
    DeadCodeDetector,
    DeadFunctionInfo,
    DeadClassInfo,
    UnusedVariableInfo
)


class TestDeadCodeDetector(unittest.TestCase):
    """Test cases for DeadCodeDetector class."""

    def setUp(self):
        """Set up test environment."""
        # Create temporary directory for test project
        self.test_dir = tempfile.mkdtemp()
        self.call_graph_db = os.path.join(self.test_dir, "call_graph.db")
        
        # Create test Python files
        self._create_test_files()
        
        # Initialize detector
        self.detector = DeadCodeDetector(
            project_root=self.test_dir,
            call_graph_db=self.call_graph_db,
            low_usage_threshold=3
        )

    def tearDown(self):
        """Clean up test environment."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def _create_test_files(self):
        """Create test Python files with various scenarios."""
        
        # File with dead function
        dead_func_file = os.path.join(self.test_dir, "dead_functions.py")
        with open(dead_func_file, 'w') as f:
            f.write("""
def dead_function():
    '''This function is never called'''
    return 42

def used_function():
    '''This function is called'''
    return 24

def low_usage_function():
    '''This function has low usage'''
    return 12
""")
        
        # File with public API function
        api_file = os.path.join(self.test_dir, "api.py")
        with open(api_file, 'w') as f:
            f.write("""
def public_api_function():
    '''This is part of public API'''
    return "public"

__all__ = ['public_api_function']
""")
        
        # File with dead class
        class_file = os.path.join(self.test_dir, "classes.py")
        with open(class_file, 'w') as f:
            f.write("""
class DeadClass:
    def __init__(self):
        self.value = 0
    
    def method1(self):
        return 1
    
    def method2(self):
        return 2

class UsedClass:
    def __init__(self):
        self.value = 0
    
    def used_method(self):
        return 1
""")
        
        # File with unused variables
        var_file = os.path.join(self.test_dir, "variables.py")
        with open(var_file, 'w') as f:
            f.write("""
def function_with_unused_vars():
    unused_var = 42
    used_var = 24
    return used_var

def another_function():
    x = 1
    y = 2
    z = 3
    return x + y
""")
        
        # Test file
        test_file = os.path.join(self.test_dir, "test_code.py")
        with open(test_file, 'w') as f:
            f.write("""
def test_used_function():
    result = used_function()
    assert result == 24

def test_test_only_function():
    '''This function is only used in tests'''
    return "test"
""")
        
        # Main file
        main_file = os.path.join(self.test_dir, "main.py")
        with open(main_file, 'w') as f:
            f.write("""
def main():
    result = used_function()
    print(result)

if __name__ == '__main__':
    main()
""")

    def test_detector_initialization(self):
        """Test detector initialization."""
        self.assertIsNotNone(self.detector)
        self.assertEqual(self.detector.project_root, self.test_dir)
        self.assertEqual(self.detector.call_graph_db, self.call_graph_db)
        self.assertEqual(self.detector.low_usage_threshold, 3)

    def test_detect_dead_functions_basic(self):
        """Test basic dead function detection."""
        dead_functions = self.detector.detect_dead_functions(include_test_files=False)
        
        # We should find dead_function
        self.assertIsInstance(dead_functions, list)
        self.assertGreater(len(dead_functions), 0)
        
        # Check that we found dead_function
        dead_func_names = [f.function_name for f in dead_functions]
        self.assertIn('dead_function', dead_func_names)

    def test_detect_dead_functions_excludes_test_files(self):
        """Test that test files are excluded by default."""
        dead_functions = self.detector.detect_dead_functions(include_test_files=False)
        
        # Functions from test files should not be in the list
        test_file_functions = [
            f for f in dead_functions 
            if 'test' in os.path.basename(f.file_path).lower()
        ]
        self.assertEqual(len(test_file_functions), 0)

    def test_detect_dead_functions_includes_test_files(self):
        """Test that test files are included when flag is set."""
        dead_functions_including = self.detector.detect_dead_functions(include_test_files=True)
        dead_functions_excluding = self.detector.detect_dead_functions(include_test_files=False)
        
        # Should have more when including test files
        self.assertGreaterEqual(len(dead_functions_including), len(dead_functions_excluding))

    def test_detect_dead_functions_confidence_levels(self):
        """Test that dead functions have confidence levels."""
        dead_functions = self.detector.detect_dead_functions(include_test_files=False)
        
        for func in dead_functions:
            self.assertIn(func.confidence, ['high', 'medium', 'low'])

    def test_detect_dead_functions_call_count(self):
        """Test that call counts are tracked."""
        dead_functions = self.detector.detect_dead_functions(include_test_files=False)
        
        for func in dead_functions:
            self.assertGreaterEqual(func.call_count, 0)
            self.assertIsInstance(func.call_count, int)

    def test_detect_dead_functions_public_api_check(self):
        """Test that public API functions are identified."""
        dead_functions = self.detector.detect_dead_functions(include_test_files=False)
        
        # Check that we have public_api field
        for func in dead_functions:
            self.assertIsInstance(func.is_public_api, bool)

    def test_detect_dead_classes_basic(self):
        """Test basic dead class detection."""
        dead_classes = self.detector.detect_dead_classes(include_test_files=False)
        
        # We should find DeadClass
        self.assertIsInstance(dead_classes, list)
        
        # Check that we found DeadClass
        dead_class_names = [c.class_name for c in dead_classes]
        self.assertIn('DeadClass', dead_class_names)

    def test_detect_dead_classes_methods_called(self):
        """Test that called methods are tracked."""
        dead_classes = self.detector.detect_dead_classes(include_test_files=False)
        
        for cls in dead_classes:
            self.assertIsInstance(cls.called_methods, set)
            self.assertGreaterEqual(len(cls.called_methods), 0)

    def test_detect_unused_variables_basic(self):
        """Test basic unused variable detection."""
        unused_vars = self.detector.detect_unused_variables(include_test_files=False)
        
        # We should find unused variables
        self.assertIsInstance(unused_vars, list)
        self.assertGreater(len(unused_vars), 0)
        
        # Check that we found unused_var
        var_names = [v.variable_name for v in unused_vars]
        self.assertIn('unused_var', var_names)

    def test_detect_unused_variables_line_numbers(self):
        """Test that line numbers are tracked."""
        unused_vars = self.detector.detect_unused_variables(include_test_files=False)
        
        for var in unused_vars:
            self.assertGreater(var.line_number, 0)
            self.assertIsInstance(var.line_number, int)

    def test_detect_unused_variables_scope(self):
        """Test that variable scope is tracked."""
        unused_vars = self.detector.detect_unused_variables(include_test_files=False)
        
        for var in unused_vars:
            self.assertIn(var.scope, ['local', 'class', 'module'])

    def test_special_variables_not_flagged(self):
        """Test that special variables are not flagged."""
        # Create file with special variables
        special_file = os.path.join(self.test_dir, "special_vars.py")
        with open(special_file, 'w') as f:
            f.write("""
def function():
    self = 1  # Should not be flagged
    cls = 2  # Should not be flagged
    _internal = 3  # Should not be flagged
    return 4
""")
        
        unused_vars = self.detector.detect_unused_variables(include_test_files=False)
        
        # Special variables should not be in the list
        special_var_names = [v.variable_name for v in unused_vars]
        self.assertNotIn('self', special_var_names)
        self.assertNotIn('cls', special_var_names)
        self.assertNotIn('_internal', special_var_names)

    def test_generate_dead_function_report_text(self):
        """Test text report generation."""
        report = self.detector.generate_dead_function_report(format="text")
        
        self.assertIsInstance(report, str)
        self.assertIn("DEAD FUNCTION DETECTION REPORT", report)
        self.assertIn("Total Dead Functions:", report)

    def test_generate_dead_function_report_json(self):
        """Test JSON report generation."""
        import json
        
        report = self.detector.generate_dead_function_report(format="json")
        
        self.assertIsInstance(report, str)
        data = json.loads(report)
        self.assertIsInstance(data, list)

    def test_generate_dead_function_report_markdown(self):
        """Test markdown report generation."""
        report = self.detector.generate_dead_function_report(format="markdown")
        
        self.assertIsInstance(report, str)
        self.assertIn("# Dead Function Detection Report", report)
        self.assertIn("| Function | File |", report)

    def test_dead_function_info_structure(self):
        """Test DeadFunctionInfo structure."""
        info = DeadFunctionInfo(
            file_path="/path/to/file.py",
            function_name="test_func",
            function_type="function",
            call_count=0,
            is_public_api=False,
            is_test_only=False,
            confidence="high",
            reasons=["Never called"],
            suggestions=["Remove it"]
        )
        
        self.assertEqual(info.file_path, "/path/to/file.py")
        self.assertEqual(info.function_name, "test_func")
        self.assertEqual(info.function_type, "function")
        self.assertEqual(info.call_count, 0)
        self.assertFalse(info.is_public_api)
        self.assertFalse(info.is_test_only)
        self.assertEqual(info.confidence, "high")
        self.assertEqual(len(info.reasons), 1)
        self.assertEqual(len(info.suggestions), 1)

    def test_dead_class_info_structure(self):
        """Test DeadClassInfo structure."""
        info = DeadClassInfo(
            file_path="/path/to/file.py",
            class_name="TestClass",
            instantiation_count=0,
            is_abstract_base=False,
            is_mixin=False,
            has_subclasses=False,
            methods_count=2,
            called_methods=set(),
            confidence="high",
            reasons=["No methods called"],
            suggestions=["Remove it"]
        )
        
        self.assertEqual(info.file_path, "/path/to/file.py")
        self.assertEqual(info.class_name, "TestClass")
        self.assertEqual(info.instantiation_count, 0)
        self.assertFalse(info.is_abstract_base)
        self.assertFalse(info.is_mixin)
        self.assertFalse(info.has_subclasses)
        self.assertEqual(info.methods_count, 2)
        self.assertEqual(len(info.called_methods), 0)
        self.assertEqual(info.confidence, "high")

    def test_unused_variable_info_structure(self):
        """Test UnusedVariableInfo structure."""
        info = UnusedVariableInfo(
            file_path="/path/to/file.py",
            variable_name="unused_var",
            scope="local",
            line_number=10,
            confidence="high",
            reasons=["Never used"],
            suggestions=["Remove it"]
        )
        
        self.assertEqual(info.file_path, "/path/to/file.py")
        self.assertEqual(info.variable_name, "unused_var")
        self.assertEqual(info.scope, "local")
        self.assertEqual(info.line_number, 10)
        self.assertEqual(info.confidence, "high")
        self.assertEqual(len(info.reasons), 1)
        self.assertEqual(len(info.suggestions), 1)

    def test_is_test_file(self):
        """Test test file detection."""
        # Test various test file names
        self.assertTrue(self.detector._is_test_file("test_file.py"))
        self.assertTrue(self.detector._is_test_file("test_code.py"))
        self.assertTrue(self.detector._is_test_file("/path/to/test_module.py"))
        
        # Test non-test files
        self.assertFalse(self.detector._is_test_file("module.py"))
        self.assertFalse(self.detector._is_test_file("api.py"))
        self.assertFalse(self.detector._is_test_file("main.py"))

    def test_find_python_files(self):
        """Test Python file discovery."""
        files = self.detector._find_python_files(self.test_dir, recursive=True)
        
        # Should find all .py files
        self.assertGreater(len(files), 0)
        for file_path in files:
            self.assertTrue(file_path.endswith('.py'))

    def test_get_all_functions(self):
        """Test getting all functions from codebase."""
        all_functions = self.detector._get_all_functions()
        
        self.assertIsInstance(all_functions, list)
        self.assertGreater(len(all_functions), 0)
        
        # Each entry should be a tuple of (file_path, function_name, function_type)
        for func in all_functions:
            self.assertEqual(len(func), 3)
            file_path, func_name, func_type = func
            self.assertIsInstance(file_path, str)
            self.assertIsInstance(func_name, str)
            self.assertIn(func_type, ['function', 'method'])

    def test_get_all_classes(self):
        """Test getting all classes from codebase."""
        all_classes = self.detector._get_all_classes()
        
        self.assertIsInstance(all_classes, list)
        self.assertGreater(len(all_classes), 0)
        
        # Each entry should be a tuple of (file_path, class_name, methods)
        for cls in all_classes:
            self.assertEqual(len(cls), 3)
            file_path, class_name, methods = cls
            self.assertIsInstance(file_path, str)
            self.assertIsInstance(class_name, str)
            self.assertIsInstance(methods, list)

    def test_is_special_variable(self):
        """Test special variable detection."""
        # These should be special
        self.assertTrue(self.detector._is_special_variable('__name__'))
        self.assertTrue(self.detector._is_special_variable('__file__'))
        self.assertTrue(self.detector._is_special_variable('self'))
        self.assertTrue(self.detector._is_special_variable('cls'))
        self.assertTrue(self.detector._is_special_variable('_'))
        
        # These should not be special
        self.assertFalse(self.detector._is_special_variable('my_var'))
        self.assertFalse(self.detector._is_special_variable('data'))
        self.assertFalse(self.detector._is_special_variable('result'))

    def test_detect_unused_class_attributes(self):
        """Test detection of unused class attributes."""
        # Create file with class attributes
        class_attr_file = os.path.join(self.test_dir, "class_attrs.py")
        with open(class_attr_file, 'w') as f:
            f.write("""
class MyClass:
    def __init__(self):
        self.used_attr = 1
        self.unused_attr = 2  # Should be detected
    
    def method(self):
        return self.used_attr
""")
        
        unused_vars = self.detector.detect_unused_variables(include_test_files=False)
        
        # Should detect unused_attr
        var_names = [v.variable_name for v in unused_vars]
        self.assertIn('unused_attr', var_names)
        
        # Check scope
        unused_attr = [v for v in unused_vars if v.variable_name == 'unused_attr'][0]
        self.assertEqual(unused_attr.scope, 'class')

    def test_detect_unused_module_level_variables(self):
        """Test detection of unused module-level variables."""
        # Create file with module-level variables
        module_file = os.path.join(self.test_dir, "module_vars.py")
        with open(module_file, 'w') as f:
            f.write("""
# Module-level variables
USED_MODULE_VAR = "used"
UNUSED_MODULE_VAR = "unused"  # Should be detected

def function():
    return USED_MODULE_VAR
""")
        
        unused_vars = self.detector.detect_unused_variables(include_test_files=False)
        
        # Should detect UNUSED_MODULE_VAR
        var_names = [v.variable_name for v in unused_vars]
        self.assertIn('UNUSED_MODULE_VAR', var_names)
        
        # Check scope
        unused_var = [v for v in unused_vars if v.variable_name == 'UNUSED_MODULE_VAR'][0]
        self.assertEqual(unused_var.scope, 'module')

    def test_unused_variable_multiple_scopes(self):
        """Test that variables from different scopes are detected."""
        # Create file with variables in all scopes
        multi_file = os.path.join(self.test_dir, "multi_scope.py")
        with open(multi_file, 'w') as f:
            f.write("""
# Module-level
MODULE_UNUSED = "unused"

class TestClass:
    def __init__(self):
        self.CLASS_UNUSED = "unused"
        self.CLASS_USED = "used"
    
    def method(self):
        return self.CLASS_USED

def function():
    LOCAL_UNUSED = "unused"
    LOCAL_USED = "used"
    return LOCAL_USED
""")
        
        unused_vars = self.detector.detect_unused_variables(include_test_files=False)
        
        # Should detect all three
        var_names = [v.variable_name for v in unused_vars]
        self.assertIn('MODULE_UNUSED', var_names)
        self.assertIn('CLASS_UNUSED', var_names)
        self.assertIn('LOCAL_UNUSED', var_names)
        
        # Check scopes
        scopes = {v.variable_name: v.scope for v in unused_vars}
        self.assertEqual(scopes['MODULE_UNUSED'], 'module')
        self.assertEqual(scopes['CLASS_UNUSED'], 'class')
        self.assertEqual(scopes['LOCAL_UNUSED'], 'local')

    def test_used_class_attributes_not_flagged(self):
        """Test that used class attributes are not flagged."""
        # Create file with used class attributes
        used_file = os.path.join(self.test_dir, "used_attrs.py")
        with open(used_file, 'w') as f:
            f.write("""
class MyClass:
    def __init__(self):
        self.attr1 = 1
        self.attr2 = 2
    
    def method1(self):
        return self.attr1
    
    def method2(self):
        return self.attr2
""")
        
        unused_vars = self.detector.detect_unused_variables(include_test_files=False)
        
        # Should not detect attr1 or attr2
        var_names = [v.variable_name for v in unused_vars]
        self.assertNotIn('attr1', var_names)
        self.assertNotIn('attr2', var_names)

    def test_used_module_variables_not_flagged(self):
        """Test that used module variables are not flagged."""
        # Create file with used module variables
        used_file = os.path.join(self.test_dir, "used_module.py")
        with open(used_file, 'w') as f:
            f.write("""
# Module-level variables
VAR1 = "value1"
VAR2 = "value2"

def func1():
    return VAR1

def func2():
    return VAR2
""")
        
        unused_vars = self.detector.detect_unused_variables(include_test_files=False)
        
        # Should not detect VAR1 or VAR2
        var_names = [v.variable_name for v in unused_vars]
        self.assertNotIn('VAR1', var_names)
        self.assertNotIn('VAR2', var_names)

    def test_unused_variable_confidence_levels(self):
        """Test confidence levels for different scopes."""
        # Create file with various unused variables
        conf_file = os.path.join(self.test_dir, "confidence.py")
        with open(conf_file, 'w') as f:
            f.write("""
MODULE_UNUSED = "unused"

class TestClass:
    def __init__(self):
        self.CLASS_UNUSED = "unused"

def function():
    LOCAL_UNUSED = "unused"
    return 1
""")
        
        unused_vars = self.detector.detect_unused_variables(include_test_files=False)
        
        # Check confidence levels
        for var in unused_vars:
            if var.scope == 'local':
                self.assertEqual(var.confidence, 'high')
            elif var.scope in ('class', 'module'):
                self.assertEqual(var.confidence, 'medium')

    def test_unused_variable_reasons_and_suggestions(self):
        """Test that reasons and suggestions are generated."""
        # Create file with unused variable
        reason_file = os.path.join(self.test_dir, "reasons.py")
        with open(reason_file, 'w') as f:
            f.write("""
def function():
    unused_var = 42
    return 1
""")
        
        unused_vars = self.detector.detect_unused_variables(include_test_files=False)
        
        # Should have at least one unused variable
        self.assertGreater(len(unused_vars), 0)
        
        var = unused_vars[0]
        
        # Should have reasons
        self.assertIsInstance(var.reasons, list)
        self.assertGreater(len(var.reasons), 0)
        
        # Should have suggestions
        self.assertIsInstance(var.suggestions, list)
        self.assertGreater(len(var.suggestions), 0)

    def test_generate_unused_variables_report_text(self):
        """Test text report generation for unused variables."""
        report = self.detector.generate_unused_variables_report(format="text")
        
        self.assertIsInstance(report, str)
        self.assertIn("UNUSED VARIABLE DETECTION REPORT", report)
        self.assertIn("Total Unused Variables:", report)
        self.assertIn("Scope Breakdown:", report)
        self.assertIn("Confidence Breakdown:", report)

    def test_generate_unused_variables_report_json(self):
        """Test JSON report generation for unused variables."""
        import json
        
        report = self.detector.generate_unused_variables_report(format="json")
        
        self.assertIsInstance(report, str)
        data = json.loads(report)
        self.assertIsInstance(data, list)
        
        # Check structure
        if data:
            self.assertIn('file_path', data[0])
            self.assertIn('variable_name', data[0])
            self.assertIn('scope', data[0])
            self.assertIn('line_number', data[0])
            self.assertIn('confidence', data[0])

    def test_generate_unused_variables_report_markdown(self):
        """Test markdown report generation for unused variables."""
        report = self.detector.generate_unused_variables_report(format="markdown")
        
        self.assertIsInstance(report, str)
        self.assertIn("# Unused Variable Detection Report", report)
        self.assertIn("## Summary", report)
        self.assertIn("| Variable | File:Line |", report)

    def test_loop_variables_not_flagged(self):
        """Test that loop variables are not flagged."""
        # Create file with loop variables
        loop_file = os.path.join(self.test_dir, "loops.py")
        with open(loop_file, 'w') as f:
            f.write("""
def process_items():
    for item in items:  # item should not be flagged
        print(item)
    
    for i in range(10):  # i should not be flagged
        print(i)
    
    for key, value in data.items():  # key, value should not be flagged
        print(key, value)
""")
        
        unused_vars = self.detector.detect_unused_variables(include_test_files=False)
        
        # Loop variables should not be flagged
        var_names = [v.variable_name for v in unused_vars]
        self.assertNotIn('item', var_names)
        self.assertNotIn('i', var_names)
        self.assertNotIn('key', var_names)
        self.assertNotIn('value', var_names)

    def test_comprehension_variables_not_flagged(self):
        """Test that comprehension variables are not flagged."""
        # Create file with comprehension
        comp_file = os.path.join(self.test_dir, "comprehensions.py")
        with open(comp_file, 'w') as f:
            f.write("""
def process():
    squares = [x**2 for x in range(10)]  # x should not be flagged
    doubled = {y: y*2 for y in range(5)}  # y should not be flagged
    return squares
""")
        
        unused_vars = self.detector.detect_unused_variables(include_test_files=False)
        
        # Comprehension variables should not be flagged
        var_names = [v.variable_name for v in unused_vars]
        self.assertNotIn('x', var_names)
        self.assertNotIn('y', var_names)

    def test_multiple_unused_in_same_function(self):
        """Test detection of multiple unused variables in same function."""
        # Create file with multiple unused variables
        multi_file = os.path.join(self.test_dir, "multi_unused.py")
        with open(multi_file, 'w') as f:
            f.write("""
def function():
    unused1 = 1
    unused2 = 2
    unused3 = 3
    used = 4
    return used
""")
        
        unused_vars = self.detector.detect_unused_variables(include_test_files=False)
        
        # Should detect all three unused variables
        var_names = [v.variable_name for v in unused_vars]
        self.assertIn('unused1', var_names)
        self.assertIn('unused2', var_names)
        self.assertIn('unused3', var_names)
        
        # Should not detect 'used'
        self.assertNotIn('used', var_names)

    def test_unused_variable_in_nested_scopes(self):
        """Test detection in nested function scopes."""
        # Create file with nested functions
        nested_file = os.path.join(self.test_dir, "nested.py")
        with open(nested_file, 'w') as f:
            f.write("""
def outer():
    outer_unused = 1
    outer_used = 2
    
    def inner():
        inner_unused = 3
        inner_used = 4
        return inner_used
    
    return outer_used
""")
        
        unused_vars = self.detector.detect_unused_variables(include_test_files=False)
        
        # Should detect both unused variables
        var_names = [v.variable_name for v in unused_vars]
        self.assertIn('outer_unused', var_names)
        self.assertIn('inner_unused', var_names)

    def test_false_positive_prevention(self):
        """Test prevention of false positives."""
        # Create file with edge cases that should not be flagged
        edge_file = os.path.join(self.test_dir, "edge_cases.py")
        with open(edge_file, 'w') as f:
            f.write("""
# Variables used in different contexts
def function1():
    x = 1
    y = 2
    return x + y

def function2():
    result = calculate()
    if result > 0:
        return result
    return 0

class TestClass:
    def __init__(self):
        self.value = 1
    
    def get_value(self):
        return self.value
""")
        
        unused_vars = self.detector.detect_unused_variables(include_test_files=False)
        
        # These should not be flagged
        var_names = [v.variable_name for v in unused_vars]
        self.assertNotIn('x', var_names)
        self.assertNotIn('y', var_names)
        self.assertNotIn('result', var_names)
        self.assertNotIn('value', var_names)

    def test_all_report_formats_consistency(self):
        """Test that all report formats are consistent."""
        # Generate all report formats
        text_report = self.detector.generate_unused_variables_report(format="text")
        json_report = self.detector.generate_unused_variables_report(format="json")
        markdown_report = self.detector.generate_unused_variables_report(format="markdown")
        
        # All should be strings
        self.assertIsInstance(text_report, str)
        self.assertIsInstance(json_report, str)
        self.assertIsInstance(markdown_report, str)
        
        # All should mention unused variables
        self.assertIn("Unused Variable", text_report)
        self.assertIn("Unused Variable", markdown_report)
        
        # JSON should be valid
        import json
        data = json.loads(json_report)
        self.assertIsInstance(data, list)


class TestDeadCodeDetectorIntegration(unittest.TestCase):
    """Integration tests for DeadCodeDetector."""

    def setUp(self):
        """Set up integration test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.call_graph_db = os.path.join(self.test_dir, "call_graph.db")
        
        # Create more complex test structure
        self._create_complex_test_project()
        
        # Initialize detector
        self.detector = DeadCodeDetector(
            project_root=self.test_dir,
            call_graph_db=self.call_graph_db,
            low_usage_threshold=3
        )

    def tearDown(self):
        """Clean up integration test environment."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def _create_complex_test_project(self):
        """Create a more complex test project structure."""
        
        # Create package structure
        pkg_dir = os.path.join(self.test_dir, "mypackage")
        os.makedirs(pkg_dir, exist_ok=True)
        
        # __init__.py with exports
        with open(os.path.join(pkg_dir, "__init__.py"), 'w') as f:
            f.write("""
from .module1 import public_function
from .module2 import another_public_function

__all__ = ['public_function', 'another_public_function']
""")
        
        # module1.py
        with open(os.path.join(pkg_dir, "module1.py"), 'w') as f:
            f.write("""
def public_function():
    '''Public API function'''
    return "public"

def internal_function():
    '''Internal function, not exported'''
    return "internal"

def unused_internal():
    '''Never used'''
    return "unused"
""")
        
        # module2.py
        with open(os.path.join(pkg_dir, "module2.py"), 'w') as f:
            f.write("""
def another_public_function():
    return "public2"

def helper_function():
    return "helper"
""")
        
        # tests directory
        tests_dir = os.path.join(self.test_dir, "tests")
        os.makedirs(tests_dir, exist_ok=True)
        
        with open(os.path.join(tests_dir, "test_module1.py"), 'w') as f:
            f.write("""
from mypackage.module1 import internal_function

def test_internal_function():
    result = internal_function()
    assert result == "internal"
""")

    def test_dead_function_detection_with_packages(self):
        """Test dead function detection in package structure."""
        dead_functions = self.detector.detect_dead_functions(include_test_files=False)
        
        # Should detect unused_internal
        dead_func_names = [f.function_name for f in dead_functions]
        self.assertIn('unused_internal', dead_func_names)
        
        # Should not detect public_function (it's in __all__)
        public_funcs = [f for f in dead_functions if f.function_name == 'public_function']
        if public_funcs:
            # If found, it should be marked as public API
            self.assertTrue(public_funcs[0].is_public_api)

    def test_report_generation_complex_project(self):
        """Test report generation for complex project."""
        report_text = self.detector.generate_dead_function_report(format="text")
        report_json = self.detector.generate_dead_function_report(format="json")
        report_markdown = self.detector.generate_dead_function_report(format="markdown")
        
        # All reports should be strings
        self.assertIsInstance(report_text, str)
        self.assertIsInstance(report_json, str)
        self.assertIsInstance(report_markdown, str)
        
        # Text report should have sections
        self.assertIn("DEAD FUNCTION DETECTION REPORT", report_text)
        self.assertIn("Confidence Breakdown:", report_text)
        
        # Markdown report should have tables
        self.assertIn("| Function | File |", report_markdown)
        
        # JSON report should be valid JSON
        import json
        data = json.loads(report_json)
        self.assertIsInstance(data, list)


if __name__ == '__main__':
    unittest.main()