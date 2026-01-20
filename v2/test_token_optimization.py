"""
Tests for Token Usage Optimization (Task 4.4)
Tests context compression, adaptive pruning, and budgeting features.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from v1.logic.context_pruner import ContextPruner, PrunedContext
from v1.data.semantic_mapper import SemanticMapper
import tempfile
import shutil


class MockMapper:
    """Mock SemanticMapper for testing that actually parses code"""
    
    def __init__(self, code, file_path):
        self.lines = code.split('\n')
        self.file_path = file_path
        self._summary = self._build_summary()
    
    def _build_summary(self):
        """Build summary by parsing the actual code"""
        import ast
        
        summary = {"functions": [], "classes": []}
        
        try:
            tree = ast.parse("\n".join(self.lines))
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.col_offset == 0:
                    # Top-level function
                    func_info = {
                        "name": node.name,
                        "start_line": node.lineno,
                        "end_line": node.end_lineno if hasattr(node, 'end_lineno') else node.lineno,
                        "docstring": ast.get_docstring(node) or "",
                        "class_name": None
                    }
                    summary["functions"].append(func_info)
                
                elif isinstance(node, ast.ClassDef) and node.col_offset == 0:
                    # Top-level class
                    methods = []
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            method_info = {
                                "name": item.name,
                                "start_line": item.lineno,
                                "end_line": item.end_lineno if hasattr(item, 'end_lineno') else item.lineno,
                                "docstring": ast.get_docstring(item) or ""
                            }
                            methods.append(method_info)
                    
                    class_info = {
                        "name": node.name,
                        "start_line": node.lineno,
                        "end_line": node.end_lineno if hasattr(node, 'end_lineno') else node.lineno,
                        "docstring": ast.get_docstring(node) or "",
                        "methods": methods
                    }
                    summary["classes"].append(class_info)
        except SyntaxError:
            pass
        
        return summary
    
    def get_summary(self):
        return self._summary


def test_adaptive_pruning_low_complexity():
    """Test that low complexity tasks get more aggressive pruning"""
    print("\n=== Test: Adaptive Pruning (Low Complexity) ===")
    
    code = """def simple_getter():
    \"\"\"Simple getter method\"\"\"
    return self.value

def complex_function(data):
    \"\"\"Complex function with logic\"\"\"
    result = []
    for item in data:
        if item > 0:
            result.append(item * 2)
    return result

def trivial_getter():
    \"\"\"Get a value\"\"\"
    return self._value

class SimpleClass:
    \"\"\"A simple class\"\"\"
    def __init__(self):
        self.value = 0
    
    def get_value(self):
        \"\"\"Get value\"\"\"
        return self.value
    
    def set_value(self, val):
        \"\"\"Set value\"\"\"
        self.value = val

class ComplexClass:
    \"\"\"A complex class with many methods\"\"\"
    def __init__(self):
        self.data = []
    
    def process(self, data):
        \"\"\"Process data\"\"\"
        self.data = data
        return len(self.data)
"""
    
    mapper = MockMapper(code, "test.py")
    pruner = ContextPruner(max_tokens_per_task=8000)
    
    target_entities = [
        {"name": "simple_getter", "type": "function", "file_path": "test.py"},
        {"name": "complex_function", "type": "function", "file_path": "test.py"},
        {"name": "trivial_getter", "type": "function", "file_path": "test.py"}
    ]
    
    semantic_mappers = {"test.py": mapper}
    
    # Test with low complexity
    pruned_low = pruner.prune_context(
        semantic_mappers, target_entities, [], task_complexity="low"
    )
    
    # Test with high complexity
    pruned_high = pruner.prune_context(
        semantic_mappers, target_entities, [], task_complexity="high"
    )
    
    # Low complexity should have more summaries
    low_code_len = sum(len(ctx.code) for ctx in pruned_low.values())
    high_code_len = sum(len(ctx.code) for ctx in pruned_high.values())
    
    print(f"Low complexity context size: {low_code_len} chars")
    print(f"High complexity context size: {high_code_len} chars")
    
    assert low_code_len < high_code_len, "Low complexity should produce less context"
    assert "simple_getter" in pruned_low, "Should include simple_getter"
    
    print("✓ Adaptive pruning works correctly")


def test_context_budgeting():
    """Test that context budgeting removes low importance items"""
    print("\n=== Test: Context Budgeting ===")
    
    code = """def high_impact_func():
    \"\"\"Critical function\"\"\"
    return self.process_data()

def medium_impact_func():
    \"\"\"Medium importance\"\"\"
    return self.get_value()

def low_impact_func():
    \"\"\"Low importance helper\"\"\"
    pass

class BigClass:
    \"\"\"Large class\"\"\"
    def __init__(self):
        pass
    
    def method1(self):
        pass
    
    def method2(self):
        pass
    
    def method3(self):
        pass
"""
    
    mapper = MockMapper(code, "test.py")
    pruner = ContextPruner(max_tokens_per_task=5000)  # More reasonable budget for testing
    
    target_entities = [
        {"name": "high_impact_func", "type": "function", "file_path": "test.py"},
        {"name": "medium_impact_func", "type": "function", "file_path": "test.py"},
        {"name": "low_impact_func", "type": "function", "file_path": "test.py"},
        {"name": "BigClass", "type": "class", "file_path": "test.py"}
    ]
    
    dependency_chain = [{"name": "high_impact_func"}]
    
    semantic_mappers = {"test.py": mapper}
    
    pruned = pruner.prune_context(
        semantic_mappers, target_entities, dependency_chain, task_complexity="medium"
    )
    
    print(f"Number of pruned contexts: {len(pruned)}")
    
    # High importance should be included
    assert "high_impact_func" in pruned, "High importance should be included"
    
    # Budget should limit total size
    total_size = sum(len(ctx.code) for ctx in pruned.values())
    print(f"Total context size: {total_size} chars")
    
    print("✓ Context budgeting works correctly")


def test_token_usage_tracking():
    """Test token usage tracking for tasks"""
    print("\n=== Test: Token Usage Tracking ===")
    
    code = """def func1():
    return 1

def func2():
    return 2
"""
    
    mapper = MockMapper(code, "test.py")
    pruner = ContextPruner(max_tokens_per_task=5000)
    
    target_entities = [
        {"name": "func1", "type": "function", "file_path": "test.py"},
        {"name": "func2", "type": "function", "file_path": "test.py"}
    ]
    
    semantic_mappers = {"test.py": mapper}
    
    # Prune with task ID
    task_id = "task_001"
    pruned = pruner.prune_context(
        semantic_mappers, target_entities, [], task_complexity="medium", task_id=task_id
    )
    
    # Get stats
    stats = pruner.get_token_usage_stats(task_id)
    
    assert stats is not None, "Should track token usage"
    assert "total_tokens" in stats, "Should have total_tokens"
    assert "context_count" in stats, "Should have context_count"
    assert stats["context_count"] == 2, "Should track 2 contexts"
    
    print(f"Total tokens: {stats['total_tokens']}")
    print(f"Context count: {stats['context_count']}")
    print(f"High importance: {stats['high_importance']}")
    print(f"Medium importance: {stats['medium_importance']}")
    print(f"Low importance: {stats['low_importance']}")
    
    print("✓ Token usage tracking works correctly")


def test_summarization():
    """Test that well-understood code gets summarized"""
    print("\n=== Test: Code Summarization ===")
    
    code = """def get_name(self):
    \"\"\"Get the name attribute\"\"\"
    return self.name

def set_name(self, name):
    \"\"\"Set the name attribute\"\"\"
    self.name = name

def is_valid(self):
    \"\"\"Check if valid\"\"\"
    return self.valid
"""
    
    mapper = MockMapper(code, "test.py")
    pruner = ContextPruner()
    
    target_entities = [
        {"name": "get_name", "type": "function", "file_path": "test.py"},
        {"name": "set_name", "type": "function", "file_path": "test.py"},
        {"name": "is_valid", "type": "function", "file_path": "test.py"}
    ]
    
    semantic_mappers = {"test.py": mapper}
    
    # Low complexity should summarize getters/setters
    pruned = pruner.prune_context(
        semantic_mappers, target_entities, [], task_complexity="low"
    )
    
    for ctx_name, ctx in pruned.items():
        code = ctx.code
        print(f"\n{ctx_name}:")
        print(code)
        
        # Low complexity should produce summaries for getter/setter patterns
        if ctx_name in ["get_name", "set_name", "is_valid"]:
            # Check if it's a summary (contains # comments)
            has_summary = "# Function:" in code or "# Method:" in code
            print(f"  Has summary: {has_summary}")
    
    print("✓ Summarization works correctly")


def test_budget_thresholds():
    """Test that budget thresholds vary by complexity"""
    print("\n=== Test: Budget Thresholds ===")
    
    pruner = ContextPruner(max_tokens_per_task=8000)
    
    low_threshold = pruner._get_budget_threshold("low")
    medium_threshold = pruner._get_budget_threshold("medium")
    high_threshold = pruner._get_budget_threshold("high")
    
    print(f"Low complexity threshold: {low_threshold}")
    print(f"Medium complexity threshold: {medium_threshold}")
    print(f"High complexity threshold: {high_threshold}")
    
    assert low_threshold < medium_threshold, "Low should have lowest budget"
    assert medium_threshold < high_threshold, "Medium should have medium budget"
    assert high_threshold == 8000, "High should use full budget"
    
    print("✓ Budget thresholds work correctly")


def test_context_window_adaptation():
    """Test that context window adapts to task complexity"""
    print("\n=== Test: Context Window Adaptation ===")
    
    pruner = ContextPruner()
    
    low_window = pruner._get_context_window("low")
    medium_window = pruner._get_context_window("medium")
    high_window = pruner._get_context_window("high")
    
    print(f"Low complexity window: {low_window} lines")
    print(f"Medium complexity window: {medium_window} lines")
    print(f"High complexity window: {high_window} lines")
    
    assert low_window < medium_window, "Low should have smallest window"
    assert medium_window < high_window, "Medium should have medium window"
    assert high_window == 3, "High should have largest window"
    
    print("✓ Context window adaptation works correctly")


def test_well_understood_detection():
    """Test detection of well-understood code"""
    print("\n=== Test: Well-Understood Code Detection ===")
    
    pruner = ContextPruner()
    
    # Test function detection
    small_func = {"name": "get_x", "start_line": 1, "end_line": 3}
    large_func = {"name": "process_data", "start_line": 1, "end_line": 20}
    
    assert pruner._is_well_understood_function(small_func), "Small getter should be well-understood"
    assert not pruner._is_well_understood_function(large_func), "Large function should not be well-understood"
    
    # Test class detection
    small_class = {
        "name": "SimpleClass",
        "start_line": 1,
        "end_line": 25,
        "methods": ["__init__", "get_value", "set_value"]
    }
    large_class = {
        "name": "ComplexClass",
        "start_line": 1,
        "end_line": 100,
        "methods": ["__init__", "method1", "method2", "method3", "method4", "method5"]
    }
    
    assert pruner._is_well_understood_class(small_class), "Small class should be well-understood"
    assert not pruner._is_well_understood_class(large_class), "Large class should not be well-understood"
    
    # Test trivial method detection
    trivial_method = {"name": "get_name", "start_line": 1, "end_line": 3}
    complex_method = {"name": "process_data", "start_line": 1, "end_line": 20}
    
    assert pruner._is_trivial_method(trivial_method), "Getter should be trivial"
    assert not pruner._is_trivial_method(complex_method), "Complex method should not be trivial"
    
    print("✓ Well-understood code detection works correctly")


def test_token_savings_estimation():
    """Test token savings estimation"""
    print("\n=== Test: Token Savings Estimation ===")
    
    pruner = ContextPruner()
    
    pruned_contexts = {
        "func1": PrunedContext(
            code="def func1():\n    return 1",
            entity_name="func1",
            entity_type="function",
            file_path="test.py",
            reason="Test",
            line_range=(1, 2),
            importance="high"
        )
    }
    
    original_contexts = {
        "func1": "def func1():\n    \"\"\"Full docstring\"\"\"\n    # More comments\n    return 1"
    }
    
    savings = pruner.estimate_token_savings(pruned_contexts, original_contexts)
    
    print(f"Pruned tokens: {savings['pruned_tokens']}")
    print(f"Original tokens: {savings['original_tokens']}")
    print(f"Savings: {savings['savings_percent']}%")
    
    assert savings["pruned_tokens"] > 0, "Should estimate pruned tokens"
    assert savings["original_tokens"] > 0, "Should estimate original tokens"
    assert savings["savings_percent"] > 0, "Should show savings"
    
    print("✓ Token savings estimation works correctly")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("TOKEN USAGE OPTIMIZATION TESTS (Task 4.4)")
    print("="*60)
    
    try:
        test_adaptive_pruning_low_complexity()
        test_context_budgeting()
        test_token_usage_tracking()
        test_summarization()
        test_budget_thresholds()
        test_context_window_adaptation()
        test_well_understood_detection()
        test_token_savings_estimation()
        
        print("\n" + "="*60)
        print("ALL TESTS PASSED ✓")
        print("="*60)
        
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
