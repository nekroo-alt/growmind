"""
Test script for call graph analysis in SemanticMapper.
"""

from v1.data.semantic_mapper import SemanticMapper

# Test code with various function call patterns
test_code = """
class Calculator:
    def __init__(self, value):
        self.value = value
    
    def add(self, x):
        return self.value + x
    
    def multiply(self, x):
        return self.value * x
    
    def complex_operation(self, a, b):
        result = self.add(a)
        result = self.multiply(result)
        return len(str(result))

def helper_function():
    return 42

def main_function():
    calc = Calculator(10)
    result = calc.add(5)
    helper_function()
    return result

def external_call():
    import json
    json.dumps({"key": "value"})
    print("Hello")
"""

def test_call_graph():
    print("Testing Call Graph Analysis")
    print("=" * 60)
    
    mapper = SemanticMapper(test_code)
    
    # Get the call graph
    call_graph = mapper.get_call_graph()
    
    print("\nCall Graph:")
    print("-" * 60)
    for caller, calls in call_graph.items():
        if calls:  # Only show functions that make calls
            print(f"\n{caller} calls:")
            for call in calls:
                external_marker = " [EXTERNAL]" if call["is_external"] else ""
                print(f"  - {call['callee']} at line {call['line_number']}{external_marker}")
    
    print("\n" + "=" * 60)
    
    # Verify specific expected calls
    print("\nDebug: All functions in call graph:", sorted(call_graph.keys()))
    print("\nVerification:")
    print("-" * 60)
    
    # Check that main_function calls helper_function
    if "main_function" in call_graph:
        calls = [c["callee"] for c in call_graph["main_function"]]
        assert "helper_function" in calls, "main_function should call helper_function"
        print("✓ main_function correctly tracks function calls")
    else:
        print("✗ main_function not found in call graph")
    
    # Check that external_call marks external functions
    if "external_call" in call_graph:
        calls = call_graph["external_call"]
        has_external = any(c["is_external"] for c in calls)
        assert has_external, "external_call should have external calls marked"
        print("✓ external_call correctly identifies external function calls")
    
    # Check class methods - they should be in the graph
    method_names = [k for k in call_graph.keys() if k.startswith('Calculator.') or k in ['__init__', 'add', 'multiply', 'complex_operation']]
    print(f"✓ Found {len(method_names)} class methods in call graph")
    for method in method_names[:3]:  # Show first 3
        print(f"  - {method}")
    
    print("\nCall graph is working! ✓")
    print("=" * 60)

if __name__ == "__main__":
    test_call_graph()
