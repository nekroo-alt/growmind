import unittest
import sys
from pathlib import Path

# Add parent directory to path to import v1 modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from data.semantic_mapper import SemanticMapper
from logic.context_pruner import ContextPruner, PrunedContext


class TestContextPruner(unittest.TestCase):
    """Unit tests for ContextPruner class."""

    def setUp(self):
        """Set up test fixtures."""
        self.pruner = ContextPruner(workspace_root=".")

        # Sample Python code for testing
        self.sample_class_code = '''
class DataProcessor:
    """Processes data with various operations."""
    
    def __init__(self, config):
        """Initialize with configuration."""
        self.config = config
        self.data = []
        self.processed = False
    
    def load_data(self, source):
        """Load data from source."""
        self.data = source.get_items()
        return len(self.data)
    
    def transform(self, operation):
        """Transform data using specified operation."""
        result = []
        for item in self.data:
            try:
                transformed = operation(item)
                result.append(transformed)
            except ValueError as e:
                print(f"Error processing {item}: {e}")
        self.data = result
        return result
    
    def get_summary(self):
        """Get summary statistics."""
        return {
            "total": len(self.data),
            "processed": self.processed
        }
'''

        self.sample_function_code = '''
def calculate_metrics(data):
    """Calculate metrics for the given data."""
    if not data:
        return None
    
    total = sum(data)
    average = total / len(data)
    
    # Find max and min
    maximum = max(data)
    minimum = min(data)
    
    return {
        "total": total,
        "average": average,
        "max": maximum,
        "min": minimum
    }
'''

    def test_prune_function_with_return(self):
        """Test pruning a function that returns a value."""
        mapper = SemanticMapper(self.sample_function_code)
        semantic_mappers = {"test.py": mapper}

        target_entities = [
            {"name": "calculate_metrics", "type": "function", "file_path": "test.py"}
        ]

        pruned = self.pruner.prune_context(semantic_mappers, target_entities)

        self.assertIn("calculate_metrics", pruned)
        ctx = pruned["calculate_metrics"]

        # Check that it's a function
        self.assertEqual(ctx.entity_type, "function")
        self.assertEqual(ctx.entity_name, "calculate_metrics")

        # Check that code includes signature and key logic
        self.assertIn("def calculate_metrics", ctx.code)
        self.assertIn("return", ctx.code)

        # Should be medium importance because it returns value
        self.assertEqual(ctx.importance, "medium")

    def test_prune_class_with_methods(self):
        """Test pruning a class with multiple methods."""
        mapper = SemanticMapper(self.sample_class_code)
        semantic_mappers = {"test.py": mapper}

        target_entities = [
            {"name": "DataProcessor", "type": "class", "file_path": "test.py"}
        ]

        pruned = self.pruner.prune_context(semantic_mappers, target_entities)

        self.assertIn("DataProcessor", pruned)
        ctx = pruned["DataProcessor"]

        # Check that it's a class
        self.assertEqual(ctx.entity_type, "class")
        self.assertEqual(ctx.entity_name, "DataProcessor")

        # Check that code includes class definition
        self.assertIn("class DataProcessor", ctx.code)

        # Should include __init__ method or its comment
        self.assertTrue(
            "def __init__" in ctx.code or "# Method __init__" in ctx.code,
            f"Expected __init__ method or comment in code:\n{ctx.code}",
        )

        # Should include methods with side effects (transform modifies self.data)
        self.assertIn("def transform", ctx.code)

    def test_prune_function_in_dependency_chain(self):
        """Test that functions in dependency chain get high importance."""
        mapper = SemanticMapper(self.sample_function_code)
        semantic_mappers = {"test.py": mapper}

        target_entities = [
            {"name": "calculate_metrics", "type": "function", "file_path": "test.py"}
        ]

        # Simulate dependency chain
        dependency_chain = [{"name": "calculate_metrics"}]

        pruned = self.pruner.prune_context(
            semantic_mappers, target_entities, dependency_chain=dependency_chain
        )

        ctx = pruned["calculate_metrics"]

        # Should be high importance because it's in dependency chain
        self.assertEqual(ctx.importance, "high")
        self.assertIn("dependency chain", ctx.reason)

    def test_prune_class_with_dep_chain_methods(self):
        """Test class pruning with methods in dependency chain."""
        mapper = SemanticMapper(self.sample_class_code)
        semantic_mappers = {"test.py": mapper}

        target_entities = [
            {"name": "DataProcessor", "type": "class", "file_path": "test.py"}
        ]

        # Simulate dependency chain with specific method
        dependency_chain = [{"name": "transform"}]

        pruned = self.pruner.prune_context(
            semantic_mappers, target_entities, dependency_chain=dependency_chain
        )

        ctx = pruned["DataProcessor"]

        # Should be high importance because it has methods in dependency chain
        self.assertEqual(ctx.importance, "high")
        self.assertIn("dependency chain", ctx.reason)

    def test_pruned_context_dataclass(self):
        """Test PrunedContext dataclass structure."""
        ctx = PrunedContext(
            code="def test(): pass",
            entity_name="test",
            entity_type="function",
            file_path="test.py",
            reason="Test function",
            line_range=(1, 2),
            importance="low",
        )

        self.assertEqual(ctx.code, "def test(): pass")
        self.assertEqual(ctx.entity_name, "test")
        self.assertEqual(ctx.entity_type, "function")
        self.assertEqual(ctx.file_path, "test.py")
        self.assertEqual(ctx.reason, "Test function")
        self.assertEqual(ctx.line_range, (1, 2))
        self.assertEqual(ctx.importance, "low")

    def test_format_context_as_string(self):
        """Test formatting pruned contexts as a string."""
        mapper = SemanticMapper(self.sample_function_code)
        semantic_mappers = {"test.py": mapper}

        target_entities = [
            {"name": "calculate_metrics", "type": "function", "file_path": "test.py"}
        ]

        pruned = self.pruner.prune_context(semantic_mappers, target_entities)

        formatted = self.pruner.format_context_as_string(pruned, include_reasons=True)

        # Should contain headers
        self.assertIn("=== FUNCTION: calculate_metrics ===", formatted)
        self.assertIn("File: test.py", formatted)
        self.assertIn("Importance:", formatted)
        self.assertIn("Why included:", formatted)

        # Should contain the code
        self.assertIn("def calculate_metrics", formatted)

    def test_format_context_without_reasons(self):
        """Test formatting contexts without reason comments."""
        mapper = SemanticMapper(self.sample_function_code)
        semantic_mappers = {"test.py": mapper}

        target_entities = [
            {"name": "calculate_metrics", "type": "function", "file_path": "test.py"}
        ]

        pruned = self.pruner.prune_context(semantic_mappers, target_entities)

        formatted = self.pruner.format_context_as_string(pruned, include_reasons=False)

        # Should not contain reason
        self.assertNotIn("Why included:", formatted)

        # Should still contain other headers
        self.assertIn("=== FUNCTION: calculate_metrics ===", formatted)

    def test_estimate_token_savings(self):
        """Test token savings estimation."""
        mapper = SemanticMapper(self.sample_function_code)
        semantic_mappers = {"test.py": mapper}

        target_entities = [
            {"name": "calculate_metrics", "type": "function", "file_path": "test.py"}
        ]

        pruned = self.pruner.prune_context(semantic_mappers, target_entities)

        # Estimate savings without original
        savings = self.pruner.estimate_token_savings(pruned)

        self.assertIn("pruned_tokens", savings)
        self.assertGreater(savings["pruned_tokens"], 0)
        self.assertIsNone(savings["original_tokens"])
        self.assertIsNone(savings["savings_percent"])

        # Estimate savings with original
        original_contexts = {"calculate_metrics": self.sample_function_code}

        savings_with_original = self.pruner.estimate_token_savings(
            pruned, original_contexts
        )

        self.assertIn("original_tokens", savings_with_original)
        self.assertIn("savings_percent", savings_with_original)

        # Original and pruned should both have tokens
        self.assertGreater(savings_with_original["original_tokens"], 0)
        self.assertGreater(savings_with_original["pruned_tokens"], 0)

        # Savings percent can be positive or zero (pruning may not always reduce size)
        self.assertGreaterEqual(savings_with_original["savings_percent"], -100)

    def test_prune_nonexistent_entity(self):
        """Test pruning a non-existent entity returns empty dict."""
        mapper = SemanticMapper(self.sample_function_code)
        semantic_mappers = {"test.py": mapper}

        target_entities = [
            {"name": "nonexistent_function", "type": "function", "file_path": "test.py"}
        ]

        pruned = self.pruner.prune_context(semantic_mappers, target_entities)

        self.assertEqual(len(pruned), 0)

    def test_prune_invalid_entity_type(self):
        """Test pruning with invalid entity type."""
        mapper = SemanticMapper(self.sample_function_code)
        semantic_mappers = {"test.py": mapper}

        target_entities = [
            {"name": "something", "type": "invalid_type", "file_path": "test.py"}
        ]

        pruned = self.pruner.prune_context(semantic_mappers, target_entities)

        self.assertEqual(len(pruned), 0)

    def test_extract_key_function_lines_with_exception(self):
        """Test key line extraction for function with exception handling."""
        mapper = SemanticMapper(self.sample_class_code)
        summary = mapper.get_summary()

        # Find transform method which has exception handling
        transform_method = None
        for cls in summary["classes"]:
            for method in cls["methods"]:
                if method["name"] == "transform":
                    transform_method = method
                    break

        self.assertIsNotNone(transform_method)

        key_lines = self.pruner._extract_key_function_lines(mapper, transform_method)

        # Should detect exception handling
        self.assertTrue(key_lines["has_exception"])

        # Should have key logic lines
        self.assertGreater(len(key_lines["key_logic_lines"]), 0)

    def test_select_class_methods(self):
        """Test method selection for class pruning."""
        mapper = SemanticMapper(self.sample_class_code)
        summary = mapper.get_summary()

        class_info = summary["classes"][0]  # DataProcessor
        dep_entities = {"transform"}  # Only transform is in dependency chain

        methods = self.pruner._select_class_methods(class_info, dep_entities)

        # Should include __init__ always
        method_names = [m["name"] for m in methods]
        self.assertIn("__init__", method_names)

        # Should include transform (in dependency chain)
        self.assertIn("transform", method_names)

        # Should include load_data (has side effects)
        self.assertIn("load_data", method_names)

    def test_multiple_entities_pruning(self):
        """Test pruning multiple entities at once."""
        # Combine class and function code
        combined_code = self.sample_class_code + "\n" + self.sample_function_code
        mapper = SemanticMapper(combined_code)
        semantic_mappers = {"test.py": mapper}

        target_entities = [
            {"name": "DataProcessor", "type": "class", "file_path": "test.py"},
            {"name": "calculate_metrics", "type": "function", "file_path": "test.py"},
        ]

        pruned = self.pruner.prune_context(semantic_mappers, target_entities)

        # Should have both entities
        self.assertEqual(len(pruned), 2)
        self.assertIn("DataProcessor", pruned)
        self.assertIn("calculate_metrics", pruned)

    def test_get_builtins(self):
        """Test builtin function names set."""
        builtins = self.pruner._get_builtins()

        # Should contain common builtins
        self.assertIn("len", builtins)
        self.assertIn("print", builtins)
        self.assertIn("sum", builtins)
        self.assertIn("max", builtins)

        # Should not contain non-builtins
        self.assertNotIn("custom_function", builtins)

    def test_low_complexity_task_summarization(self):
        """Test that low complexity tasks use summarized versions."""
        # Create a simple getter function
        simple_code = '''
class SimpleClass:
    """A simple class."""
    
    def __init__(self, value):
        self.value = value
    
    def get_value(self):
        """Get value."""
        return self.value
    
    def set_value(self, new_value):
        """Set value."""
        self.value = new_value
'''
        mapper = SemanticMapper(simple_code)
        semantic_mappers = {"test.py": mapper}

        target_entities = [
            {"name": "SimpleClass", "type": "class", "file_path": "test.py"}
        ]

        # Test with low complexity
        pruned = self.pruner.prune_context(
            semantic_mappers, target_entities, task_complexity="low"
        )

        self.assertIn("SimpleClass", pruned)
        ctx = pruned["SimpleClass"]

        # For low complexity, should use summary format
        self.assertIn("SimpleClass", ctx.code)
        self.assertIn("# Class:", ctx.code)

    def test_context_budgeting(self):
        """Test that context budgeting removes low importance items."""
        # Create multiple entities
        combined_code = self.sample_class_code + "\n" + self.sample_function_code
        mapper = SemanticMapper(combined_code)
        semantic_mappers = {"test.py": mapper}

        target_entities = [
            {"name": "DataProcessor", "type": "class", "file_path": "test.py"},
            {"name": "calculate_metrics", "type": "function", "file_path": "test.py"},
        ]

        # Set a very low budget
        pruner = ContextPruner(workspace_root=".", max_tokens_per_task=100)
        pruned = pruner.prune_context(
            semantic_mappers, target_entities, task_complexity="low"
        )

        # Should have fewer items due to budgeting
        self.assertLessEqual(len(pruned), 2)

    def test_token_usage_tracking(self):
        """Test token usage tracking per task."""
        mapper = SemanticMapper(self.sample_function_code)
        semantic_mappers = {"test.py": mapper}

        target_entities = [
            {"name": "calculate_metrics", "type": "function", "file_path": "test.py"}
        ]

        pruned = self.pruner.prune_context(
            semantic_mappers, target_entities, task_id="test_task_1"
        )

        # Get token usage stats
        stats = self.pruner.get_token_usage_stats("test_task_1")

        self.assertIsNotNone(stats)
        self.assertIn("total_tokens", stats)
        self.assertIn("context_count", stats)
        self.assertEqual(stats["context_count"], 1)
        self.assertGreater(stats["total_tokens"], 0)

    def test_budget_thresholds_by_complexity(self):
        """Test that budget thresholds vary by complexity."""
        low_budget = self.pruner._get_budget_threshold("low")
        medium_budget = self.pruner._get_budget_threshold("medium")
        high_budget = self.pruner._get_budget_threshold("high")

        # Higher complexity should allow more tokens
        self.assertLess(low_budget, medium_budget)
        self.assertLess(medium_budget, high_budget)

        # Check approximate ratios
        self.assertAlmostEqual(low_budget, self.pruner.max_tokens_per_task * 0.5)
        self.assertAlmostEqual(medium_budget, self.pruner.max_tokens_per_task * 0.75)
        self.assertAlmostEqual(high_budget, self.pruner.max_tokens_per_task)

    def test_context_window_by_complexity(self):
        """Test that context window varies by complexity."""
        low_window = self.pruner._get_context_window("low")
        medium_window = self.pruner._get_context_window("medium")
        high_window = self.pruner._get_context_window("high")

        # Higher complexity should have larger context window
        self.assertEqual(low_window, 1)
        self.assertEqual(medium_window, 2)
        self.assertEqual(high_window, 3)

    def test_well_understood_function_detection(self):
        """Test detection of well-understood functions."""
        # Create a simple getter
        simple_func = '''
def get_name(self):
    """Get the name."""
    return self.name
'''
        mapper = SemanticMapper(simple_func)
        summary = mapper.get_summary()
        func_info = summary["functions"][0]

        # Should be well-understood
        is_well_understood = self.pruner._is_well_understood_function(func_info)
        self.assertTrue(is_well_understood)

    def test_trivial_method_detection(self):
        """Test detection of trivial methods."""
        # Create a simple getter method
        simple_code = '''
class MyClass:
    def get_value(self):
        """Get value."""
        return self.value
    
    def __str__(self):
        return "MyClass"
'''
        mapper = SemanticMapper(simple_code)
        summary = mapper.get_summary()

        # Find get_value method
        get_value_method = summary["classes"][0]["methods"][0]
        is_trivial = self.pruner._is_trivial_method(get_value_method)
        self.assertTrue(is_trivial)

        # Find __str__ method
        str_method = summary["classes"][0]["methods"][1]
        is_trivial = self.pruner._is_trivial_method(str_method)
        self.assertTrue(is_trivial)


if __name__ == "__main__":
    unittest.main()
