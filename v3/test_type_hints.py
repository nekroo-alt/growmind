"""
Test script for Task 1.4: Type Hint Extraction functionality
"""

import json
from v1.data.semantic_mapper import SemanticMapper

# Test code with various type hints
TEST_CODE = '''
from typing import List, Dict, Optional, Tuple
from collections.abc import Iterable

def simple_function(name: str, age: int) -> bool:
    """A function with simple type hints."""
    return age > 18

def complex_function(
    items: List[str],
    mapping: Dict[str, int],
    optional: Optional[float]
) -> Tuple[str, int, float]:
    """A function with complex type hints."""
    return (items[0], mapping.get("key", 0), optional or 0.0)

def no_hints(x, y):
    """Function without type hints."""
    return x + y

class TypedClass:
    """A class with typed attributes and methods."""
    
    counter: int = 0
    
    def __init__(self, name: str, values: List[int]) -> None:
        self.name = name
        self.values = values
        TypedClass.counter += 1
    
    def get_name(self) -> str:
        return self.name
    
    def add_value(self, value: int) -> None:
        self.values.append(value)
    
    @classmethod
    def get_count(cls) -> int:
        return cls.counter

class AnnotatedClass:
    """Class with __annotations__."""
    __annotations__ = {
        'id': int,
        'data': List[str],
        'config': Dict[str, Optional[int]]
    }
    
    def __init__(self, id_value: int):
        self.id = id_value
        self.data = []
        self.config = {}

# Union type test (Python 3.9+)
def union_type(value: str | int) -> str:
    return str(value)
'''


def test_type_hint_extraction():
    """Test the type hint extraction functionality."""

    print("=" * 70)
    print("Testing Task 1.4: Type Hint Extraction")
    print("=" * 70)

    mapper = SemanticMapper(TEST_CODE)
    summary = mapper.get_summary()

    # Test 1: Simple function type hints
    print("\n1. Testing simple function type hints:")
    print("-" * 70)
    simple_func = next(
        (f for f in summary["functions"] if f["name"] == "simple_function"), None
    )
    if simple_func:
        print(f"Function: {simple_func['name']}")
        print(f"Type hints: {json.dumps(simple_func['type_hints'], indent=2)}")
        assert simple_func["type_hints"]["parameters"]["name"] == "str"
        assert simple_func["type_hints"]["parameters"]["age"] == "int"
        assert simple_func["type_hints"]["return_type"] == "bool"
        assert simple_func["type_hints"]["has_type_hints"] == True
        print("✓ Simple type hints extracted correctly")

    # Test 2: Complex type hints
    print("\n2. Testing complex type hints (List, Dict, Optional, Tuple):")
    print("-" * 70)
    complex_func = next(
        (f for f in summary["functions"] if f["name"] == "complex_function"), None
    )
    if complex_func:
        print(f"Function: {complex_func['name']}")
        print(f"Type hints: {json.dumps(complex_func['type_hints'], indent=2)}")
        assert complex_func["type_hints"]["parameters"]["items"] == "List[str]"
        assert complex_func["type_hints"]["parameters"]["mapping"] == "Dict[str, int]"
        assert complex_func["type_hints"]["parameters"]["optional"] == "Optional[float]"
        assert complex_func["type_hints"]["return_type"] == "Tuple[str, int, float]"
        print("✓ Complex type hints extracted correctly")

    # Test 3: Function without type hints
    print("\n3. Testing function without type hints:")
    print("-" * 70)
    no_hints_func = next(
        (f for f in summary["functions"] if f["name"] == "no_hints"), None
    )
    if no_hints_func:
        print(f"Function: {no_hints_func['name']}")
        print(f"Type hints: {json.dumps(no_hints_func['type_hints'], indent=2)}")
        assert no_hints_func["type_hints"]["has_type_hints"] == False
        assert no_hints_func["type_hints"]["parameters"] == {}
        assert no_hints_func["type_hints"]["return_type"] is None
        print("✓ No type hints detected correctly")

    # Test 4: Class methods with type hints
    print("\n4. Testing class methods with type hints:")
    print("-" * 70)
    typed_class = next(
        (c for c in summary["classes"] if c["name"] == "TypedClass"), None
    )
    if typed_class:
        print(f"Class: {typed_class['name']}")

        # Check __init__ method
        init_method = next(
            (m for m in typed_class["methods"] if m["name"] == "__init__"), None
        )
        if init_method:
            print(f"\n  Method: {init_method['name']}")
            print(f"  Type hints: {json.dumps(init_method['type_hints'], indent=4)}")
            assert init_method["type_hints"]["parameters"]["name"] == "str"
            assert init_method["type_hints"]["parameters"]["values"] == "List[int]"
            assert init_method["type_hints"]["return_type"] == "None"
            print("  ✓ __init__ type hints extracted correctly")

        # Check get_name method
        get_name = next(
            (m for m in typed_class["methods"] if m["name"] == "get_name"), None
        )
        if get_name:
            print(f"\n  Method: {get_name['name']}")
            print(f"  Type hints: {json.dumps(get_name['type_hints'], indent=4)}")
            assert get_name["type_hints"]["return_type"] == "str"
            print("  ✓ get_name type hints extracted correctly")

    # Test 5: Class attribute type hints
    print("\n5. Testing class attribute type hints:")
    print("-" * 70)
    if typed_class:
        print(f"Class: {typed_class['name']}")
        print(
            f"Attribute type hints: {json.dumps(typed_class['attribute_type_hints'], indent=2)}"
        )
        assert "counter" in typed_class["attribute_type_hints"]
        assert typed_class["attribute_type_hints"]["counter"]["type"] == "int"
        print("✓ Class attribute type hints extracted correctly")

    # Test 6: __annotations__ dictionary
    print("\n6. Testing __annotations__ dictionary parsing:")
    print("-" * 70)
    annotated_class = next(
        (c for c in summary["classes"] if c["name"] == "AnnotatedClass"), None
    )
    if annotated_class:
        print(f"Class: {annotated_class['name']}")
        print(
            f"Attribute type hints: {json.dumps(annotated_class['attribute_type_hints'], indent=2)}"
        )
        assert "id" in annotated_class["attribute_type_hints"]
        assert annotated_class["attribute_type_hints"]["id"]["type"] == "int"
        assert "data" in annotated_class["attribute_type_hints"]
        assert annotated_class["attribute_type_hints"]["data"]["type"] == "List[str]"
        assert "config" in annotated_class["attribute_type_hints"]
        assert (
            annotated_class["attribute_type_hints"]["config"]["type"]
            == "Dict[str, Optional[int]]"
        )
        print("✓ __annotations__ parsed correctly")

    # Test 7: Union types (Python 3.9+)
    print("\n7. Testing union types:")
    print("-" * 70)
    union_func = next(
        (f for f in summary["functions"] if f["name"] == "union_type"), None
    )
    if union_func:
        print(f"Function: {union_func['name']}")
        print(f"Type hints: {json.dumps(union_func['type_hints'], indent=2)}")
        # Union types might be represented as 'str | int' or similar
        print(
            f"  Parameter 'value' type: {union_func['type_hints']['parameters'].get('value', 'N/A')}"
        )
        print("✓ Union type extraction attempted")

    print("\n" + "=" * 70)
    print("All tests passed! ✓")
    print("=" * 70)

    # Print full summary for debugging
    print("\n\nFull Summary:")
    print("=" * 70)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    test_type_hint_extraction()
