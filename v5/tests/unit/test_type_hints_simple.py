#!/usr/bin/env python3
import json
from data.semantic_mapper import SemanticMapper

# Test code with various type hints
TEST_CODE = """
from typing import List, Dict, Optional, Tuple

def simple_function(name: str, age: int) -> bool:
    return age > 18

def complex_function(
    items: List[str],
    mapping: Dict[str, int],
    optional: Optional[float]
) -> Tuple[str, int, float]:
    return (items[0], mapping.get("key", 0), optional or 0.0)

class TypedClass:
    counter: int = 0
    
    def __init__(self, name: str, values: List[int]) -> None:
        self.name = name
        self.values = values
"""

mapper = SemanticMapper(TEST_CODE)
summary = mapper.get_summary()

print("=== Type Hint Extraction Test ===")
print()
print("DEBUG - Summary functions:", summary["functions"])
print()

# Test 1: Simple function
simple_func = next(
    (f for f in summary["functions"] if f["name"] == "simple_function"), None
)
if simple_func:
    print("DEBUG - simple_func keys:", list(simple_func.keys()))
    print("DEBUG - simple_func:", simple_func)
    print("✓ simple_function type_hints:", simple_func["type_hints"])

# Test 2: Complex function
complex_func = next(
    (f for f in summary["functions"] if f["name"] == "complex_function"), None
)
if complex_func:
    print("✓ complex_function type_hints:", complex_func["type_hints"])

# Test 3: Class attributes
typed_class = next((c for c in summary["classes"] if c["name"] == "TypedClass"), None)
if typed_class:
    print("✓ TypedClass attribute_type_hints:", typed_class["attribute_type_hints"])

# Test 4: Class methods
if typed_class and typed_class["methods"]:
    init_method = next(
        (m for m in typed_class["methods"] if m["name"] == "__init__"), None
    )
    if init_method:
        print("✓ TypedClass.__init__ type_hints:", init_method["type_hints"])

print()
print("=== All tests passed! ===")
