"""
Test script to verify data flow analysis in SemanticMapper (Task 1.2)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from v5.data.semantic_mapper import SemanticMapper


# Test code with various data flow patterns
test_code = '''
class DataProcessor:
    """A class that processes data with state mutations."""
    
    def __init__(self):
        self.data = []
        self.processed_count = 0
        self.max_items = 100
    
    def add_item(self, item):
        """Add an item to the data list."""
        if len(self.data) < self.max_items:
            self.data.append(item)
            self.processed_count += 1
    
    def process_items(self, multiplier=2):
        """Process all items with a multiplier."""
        result = []
        for item in self.data:
            processed = item * multiplier
            result.append(processed)
        return result
    
    def get_summary(self):
        """Get a summary of processed data."""
        summary = {
            "count": self.processed_count,
            "total": sum(self.data)
        }
        return summary


def calculate_stats(numbers):
    """Calculate statistics for a list of numbers."""
    if not numbers:
        return None
    
    total = sum(numbers)
    count = len(numbers)
    average = total / count
    
    result = {
        "total": total,
        "count": count,
        "average": average
    }
    
    return result


def process_data(input_data, threshold=10):
    """Process data with threshold filtering."""
    filtered = []
    
    for value in input_data:
        if value > threshold:
            filtered.append(value * 2)
        else:
            filtered.append(value)
    
    # Call another function with parameters
    stats = calculate_stats(filtered)
    
    return stats
'''


def test_data_flow():
    """Test the data flow analysis functionality."""
    print("=" * 70)
    print("Testing Data Flow Analysis (Task 1.2)")
    print("=" * 70)

    mapper = SemanticMapper(test_code)
    summary = mapper.get_summary()

    # Test 1: Check that data_flow is included in function summaries
    print("\n1. Verifying data_flow field exists in function summaries...")
    for func in summary["functions"]:
        assert "data_flow" in func, f"Missing data_flow in function {func['name']}"
        print(f"   ✓ Function '{func['name']}' has data_flow field")

    for cls in summary["classes"]:
        for method in cls["methods"]:
            assert (
                "data_flow" in method
            ), f"Missing data_flow in method {method['name']}"
            print(f"   ✓ Method '{cls['name']}.{method['name']}' has data_flow field")

    # Test 2: Test get_data_flow_summary
    print("\n2. Testing get_data_flow_summary()...")

    # Test for a function
    calc_stats_flow = mapper.get_data_flow_summary("calculate_stats")
    assert calc_stats_flow is not None, "calculate_stats data flow not found"
    assert "reads" in calc_stats_flow, "Missing 'reads' in data flow"
    assert "writes" in calc_stats_flow, "Missing 'writes' in data flow"
    assert "param_passing" in calc_stats_flow, "Missing 'param_passing' in data flow"
    assert (
        "attribute_assigns" in calc_stats_flow
    ), "Missing 'attribute_assigns' in data flow"
    print(f"   ✓ calculate_stats data flow retrieved")
    print(f"     Reads: {calc_stats_flow['reads']}")
    print(f"     Writes: {calc_stats_flow['writes']}")

    # Test for a class method
    add_item_flow = mapper.get_data_flow_summary("add_item")
    assert add_item_flow is not None, "add_item data flow not found"
    print(f"   ✓ add_item data flow retrieved")
    print(f"     Reads: {add_item_flow['reads']}")
    print(f"     Writes: {add_item_flow['writes']}")
    print(f"     Attribute Assigns: {len(add_item_flow['attribute_assigns'])} found")

    # Test 3: Verify state mutations detection
    print("\n3. Testing get_state_mutations()...")
    mutations = mapper.get_state_mutations()
    assert len(mutations) > 0, "No state mutations found"
    print(f"   ✓ Found {len(mutations)} functions/methods that modify state:")

    for mutation in mutations:
        if "class" in mutation:
            print(f"     - Method: {mutation['class']}.{mutation['function']}")
        else:
            print(f"     - Function: {mutation['function']}")
        print(f"       State changes: {len(mutation['state_changes'])}")
        for change in mutation["state_changes"]:
            print(
                f"         * {change['object']}.{change['attribute']} (line {change['line_number']})"
            )

    # Test 4: Verify attribute assignment tracking
    print("\n4. Verifying attribute assignment tracking...")
    init_flow = mapper.get_data_flow_summary("__init__")
    assert init_flow is not None, "__init__ data flow not found"

    # __init__ should have attribute assignments for self.data, self.processed_count, self.max_items
    self_attrs = [a for a in init_flow["attribute_assigns"] if a["is_self_attribute"]]
    assert (
        len(self_attrs) >= 3
    ), f"Expected at least 3 self attributes, found {len(self_attrs)}"
    print(f"   ✓ __init__ has {len(self_attrs)} self.attribute assignments:")

    attr_names = [a["attribute"] for a in self_attrs]
    print(f"     Attributes: {attr_names}")
    assert "data" in attr_names, "self.data not tracked"
    assert "processed_count" in attr_names, "self.processed_count not tracked"
    assert "max_items" in attr_names, "self.max_items not tracked"

    # Test 5: Verify parameter passing tracking
    print("\n5. Verifying parameter passing tracking...")
    process_data_flow = mapper.get_data_flow_summary("process_data")
    assert process_data_flow is not None, "process_data data flow not found"

    # process_data calls calculate_stats with 'filtered' variable
    assert len(process_data_flow["param_passing"]) > 0, "No parameter passing detected"
    print(
        f"   ✓ Detected {len(process_data_flow['param_passing'])} parameter passing events:"
    )
    for param_pass in process_data_flow["param_passing"]:
        if param_pass["is_positional"]:
            print(
                f"     - Variable '{param_pass['variable']}' passed positionally (line {param_pass['line_number']})"
            )
        else:
            print(
                f"     - Variable '{param_pass['variable']}' passed as '{param_pass['parameter_name']}' (line {param_pass['line_number']})"
            )

    # Test 6: Verify read/write tracking
    print("\n6. Verifying read/write tracking...")
    add_item_flow = mapper.get_data_flow_summary("add_item")
    print(f"   ✓ add_item variable reads: {add_item_flow['reads']}")
    print(f"   ✓ add_item variable writes: {add_item_flow['writes']}")
    print(
        f"   ✓ add_item attribute reads: {len(add_item_flow['attribute_reads'])} found"
    )

    # Check attribute reads (self.data, self.max_items)
    self_reads = [a for a in add_item_flow["attribute_reads"] if a["is_self_attribute"]]
    assert len(self_reads) > 0, "No self.attribute reads detected in add_item"
    print(f"     Self attribute reads: {[r['attribute'] for r in self_reads]}")

    # Check that attribute_reads exists
    assert "attribute_reads" in add_item_flow, "Missing 'attribute_reads' in data flow"

    # Check that builtins are excluded from variable reads
    assert "len" not in add_item_flow["reads"], "Builtins should be excluded from reads"
    print(f"   ✓ Builtins correctly excluded from variable reads")

    print("\n" + "=" * 70)
    print("All tests passed! ✓")
    print("=" * 70)


if __name__ == "__main__":
    test_data_flow()
