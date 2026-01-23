"""
Test script for Complexity Estimator module.
"""

from v1.data.semantic_mapper import SemanticMapper
from v1.logic.complexity_estimator import ComplexityEstimator, analyze_file_complexity

# Test code with varying complexity levels
test_code = """
class DataProcessor:
    def __init__(self, data):
        self.data = data
        self.valid = True
    
    def simple_method(self):
        # Simple method with no decision points
        return len(self.data)
    
    def moderate_method(self, threshold):
        # Moderate complexity with one decision point
        if len(self.data) > threshold:
            return "large"
        else:
            return "small"
    
    def complex_method(self, value, options):
        # Complex method with multiple decision points
        if value < 0:
            return "negative"
        elif value == 0:
            if options.get("strict", False):
                return "zero_strict"
            else:
                return "zero"
        elif value < 100:
            for i in range(5):
                if value == i:
                    return f"matched_{i}"
            return "small_positive"
        else:
            try:
                result = self.simple_method() * value
                if result > 1000:
                    return "large_result"
                else:
                    return "normal_result"
            except Exception:
                return "error"
    
    def very_complex_method(self, data, config):
        # Very complex method with many decision points
        if not data:
            return None
        
        if config.get("format") == "json":
            if config.get("pretty"):
                return self._format_json(data, indent=2)
            else:
                return self._format_json(data)
        elif config.get("format") == "xml":
            if config.get("include_header"):
                return self._format_xml(data, header=True)
            else:
                return self._format_xml(data)
        else:
            for item in data:
                if item.get("active", False):
                    if item.get("priority") == "high":
                        return self._process_high_priority(item)
                    elif item.get("priority") == "low":
                        continue
                    else:
                        return self._process_normal(item)
                else:
                    if config.get("include_inactive"):
                        pass
                    else:
                        continue
            return []
    
    def _format_json(self, data, indent=None):
        import json
        return json.dumps(data, indent=indent)
    
    def _format_xml(self, data, header=False):
        return f"<data>{data}</data>"
    
    def _process_high_priority(self, item):
        return {"status": "urgent", "item": item}
    
    def _process_normal(self, item):
        return {"status": "normal", "item": item}

def simple_function(x, y):
    # Simple function with no decision points
    return x + y

def moderate_function(numbers):
    # Moderate complexity with loop and if
    result = []
    for num in numbers:
        if num % 2 == 0:
            result.append(num * 2)
    return result

def complex_function(data, threshold):
    # Complex function with multiple decision points
    if not data:
        return []
    
    processed = []
    for item in data:
        if item.get("value", 0) > threshold:
            if item.get("category") == "A":
                processed.append(item["value"] * 1.5)
            elif item.get("category") == "B":
                if item.get("special", False):
                    processed.append(item["value"] * 2.0)
                else:
                    processed.append(item["value"] * 1.2)
            else:
                processed.append(item["value"])
        else:
            if item.get("include", False):
                processed.append(0)
    return processed
"""


def test_function_complexity():
    print("Testing Function Complexity Calculation")
    print("=" * 70)

    mapper = SemanticMapper(test_code)
    estimator = ComplexityEstimator(mapper)

    # Test simple function
    print("\n1. Testing simple_function():")
    complexity = estimator.calculate_function_complexity("simple_function")
    print(f"   Complexity: {complexity['complexity']}")
    print(f"   Level: {complexity['level']}")
    print(f"   Decision points: {len(complexity['decision_points'])}")
    assert complexity["complexity"] == 1, "Simple function should have complexity 1"
    assert complexity["level"] == "simple", "Should be simple level"
    print("   ✓ Simple function has correct complexity")

    # Test moderate function
    print("\n2. Testing moderate_function():")
    complexity = estimator.calculate_function_complexity("moderate_function")
    print(f"   Complexity: {complexity['complexity']}")
    print(f"   Level: {complexity['level']}")
    print(f"   Decision points: {len(complexity['decision_points'])}")
    assert (
        complexity["complexity"] >= 2
    ), "Moderate function should have complexity >= 2"
    assert complexity["level"] in ["simple", "moderate"], "Should be simple or moderate"
    print("   ✓ Moderate function has reasonable complexity")

    # Test complex function
    print("\n3. Testing complex_function():")
    complexity = estimator.calculate_function_complexity("complex_function")
    print(f"   Complexity: {complexity['complexity']}")
    print(f"   Level: {complexity['level']}")
    print(f"   Decision points: {len(complexity['decision_points'])}")
    for dp in complexity["decision_points"][:5]:  # Show first 5
        print(f"      - {dp['type']} at line {dp['line_number']}")
    assert complexity["complexity"] > 5, "Complex function should have complexity > 5"
    print("   ✓ Complex function has high complexity")

    print("\n" + "=" * 70)


def test_class_complexity():
    print("\nTesting Class Complexity Calculation")
    print("=" * 70)

    mapper = SemanticMapper(test_code)
    estimator = ComplexityEstimator(mapper)

    # Test DataProcessor class
    print("\n1. Testing DataProcessor class:")
    complexity = estimator.calculate_class_complexity("DataProcessor")
    print(f"   Total complexity: {complexity['total_complexity']}")
    print(f"   Average complexity: {complexity['average_complexity']}")
    print(f"   Max complexity: {complexity['max_complexity']}")
    print(f"   Method count: {complexity['method_count']}")
    print(f"   Attribute count: {complexity['attribute_count']}")

    print("\n   Method complexities:")
    for method in complexity["method_complexities"]:
        print(f"      - {method['name']}: {method['complexity']} ({method['level']})")

    assert complexity["method_count"] > 0, "Should have methods"
    assert complexity["total_complexity"] > 0, "Should have positive complexity"
    print("\n   ✓ Class complexity calculated correctly")

    print("\n" + "=" * 70)


def test_task_complexity_estimation():
    print("\nTesting Task Complexity Estimation")
    print("=" * 70)

    mapper = SemanticMapper(test_code)
    estimator = ComplexityEstimator(mapper)

    # Test with simple entities
    print("\n1. Estimating complexity for simple task:")
    estimate = estimator.estimate_task_complexity(["simple_function"])
    print(f"   Total complexity: {estimate['total_complexity']}")
    print(f"   Estimated effort: {estimate['estimated_effort']}")
    print(f"   Likely exceeds limit: {estimate['likely_exceeds_limit']}")
    print(f"   Risk factors: {estimate['risk_factors']}")
    assert estimate["estimated_effort"] in [
        "easy",
        "trivial",
    ], "Simple task should be easy"
    print("   ✓ Simple task estimated correctly")

    # Test with complex entities
    print("\n2. Estimating complexity for complex task:")
    estimate = estimator.estimate_task_complexity(
        ["complex_function", "complex_method"]
    )
    print(f"   Total complexity: {estimate['total_complexity']}")
    print(f"   Estimated effort: {estimate['estimated_effort']}")
    print(f"   Likely exceeds limit: {estimate['likely_exceeds_limit']}")
    print(f"   Risk factors count: {len(estimate['risk_factors'])}")
    for rf in estimate["risk_factors"]:
        print(f"      - {rf}")
    assert estimate["total_complexity"] > 10, "Complex task should have high complexity"
    assert estimate["estimated_effort"] in [
        "hard",
        "very_hard",
    ], "Should be hard or very hard"
    print("   ✓ Complex task estimated correctly")

    print("\n" + "=" * 70)


def test_line_limit_prediction():
    print("\nTesting Line Limit Prediction")
    print("=" * 70)

    mapper = SemanticMapper(test_code)
    estimator = ComplexityEstimator(mapper)

    # Test with simple function (should not exceed)
    print("\n1. Predicting for simple_function (threshold=30):")
    prediction = estimator.will_exceed_line_limit(["simple_function"], threshold=30)
    print(f"   Will exceed: {prediction['will_exceed']}")
    print(f"   Confidence: {prediction['confidence']}")
    print(f"   Estimated lines: {prediction['estimated_lines']}")
    print(f"   Reasoning: {prediction['reasoning']}")
    print(f"   Suggested action: {prediction['suggested_action']}")
    assert prediction["will_exceed"] == False, "Simple function should not exceed limit"
    assert prediction["suggested_action"] == "proceed", "Should suggest proceeding"
    print("   ✓ Correct prediction for simple function")

    # Test with complex method (should exceed)
    print("\n2. Predicting for very_complex_method (threshold=30):")
    prediction = estimator.will_exceed_line_limit(["very_complex_method"], threshold=30)
    print(f"   Will exceed: {prediction['will_exceed']}")
    print(f"   Confidence: {prediction['confidence']}")
    print(f"   Estimated lines: {prediction['estimated_lines']}")
    print(f"   Reasoning: {prediction['reasoning']}")
    print(f"   Suggested action: {prediction['suggested_action']}")
    assert prediction["will_exceed"] == True, "Complex method should exceed limit"
    assert (
        prediction["suggested_action"] == "break_down"
    ), "Should suggest breaking down"
    assert prediction["confidence"] in [
        "medium",
        "high",
    ], "Should have medium or high confidence"
    print("   ✓ Correct prediction for complex method")

    print("\n" + "=" * 70)


def test_refactoring_suggestions():
    print("\nTesting Refactoring Suggestions")
    print("=" * 70)

    mapper = SemanticMapper(test_code)
    estimator = ComplexityEstimator(mapper)

    print("\n1. Getting suggestions with threshold=5:")
    suggestions = estimator.get_refactoring_suggestions(complexity_threshold=5)
    print(f"   Found {len(suggestions)} suggestions")

    for i, suggestion in enumerate(suggestions[:5], 1):  # Show first 5
        print(f"\n   Suggestion {i}:")
        print(f"      Type: {suggestion['type']}")
        print(f"      Name: {suggestion['name']}")
        print(f"      Suggestion: {suggestion['suggestion']}")
        print(f"      Reason: {suggestion['reason']}")

    assert (
        len(suggestions) > 0
    ), "Should find at least one suggestion for this threshold"
    print("\n   ✓ Refactoring suggestions generated correctly")

    print("\n" + "=" * 70)


def test_convenience_function():
    print("\nTesting File Analysis Convenience Function")
    print("=" * 70)

    # Write test code to a temporary file
    import tempfile
    import os

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(test_code)
        temp_file = f.name

    try:
        analysis = analyze_file_complexity(temp_file)

        print(f"\nFile: {analysis['file_path']}")
        print(f"Function count: {analysis['function_count']}")
        print(f"Class count: {analysis['class_count']}")
        print(f"Refactoring suggestions: {len(analysis['refactoring_suggestions'])}")

        print("\nFunction complexities:")
        for fc in analysis["function_complexities"][:3]:
            print(f"   - {fc['name']}: {fc['complexity']} ({fc['level']})")

        print("\nClass complexities:")
        for cc in analysis["class_complexities"][:3]:
            print(f"   - {cc['name']}: {cc['total_complexity']}")

        assert analysis["function_count"] == 3, "Should have 3 functions"
        assert analysis["class_count"] == 1, "Should have 1 class"
        print("\n   ✓ File analysis works correctly")

    finally:
        os.unlink(temp_file)

    print("\n" + "=" * 70)


def run_all_tests():
    """Run all complexity estimator tests."""
    print("\n" + "=" * 70)
    print("COMPLEXITY ESTIMATOR TEST SUITE")
    print("=" * 70)

    test_function_complexity()
    test_class_complexity()
    test_task_complexity_estimation()
    test_line_limit_prediction()
    test_refactoring_suggestions()
    test_convenience_function()

    print("\n" + "=" * 70)
    print("ALL TESTS PASSED! ✓")
    print("=" * 70)
    print("\nComplexity Estimator is working correctly:")
    print("  - Calculates cyclomatic complexity for functions and classes")
    print("  - Estimates task effort levels")
    print("  - Predicts line limit violations")
    print("  - Generates refactoring suggestions")
    print("=" * 70)


if __name__ == "__main__":
    run_all_tests()
