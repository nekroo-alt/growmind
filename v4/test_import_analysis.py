"""
Test script for import dependency analyzer (Task 1.3)
"""

from v3.data.semantic_mapper import SemanticMapper


def test_basic_imports():
    """Test parsing basic import statements."""
    source_code = """
import os
import sys
from ast import parse
from typing import List, Optional

def example():
    pass
"""

    mapper = SemanticMapper(source_code)
    deps = mapper.get_import_dependencies()

    print("Test 1: Basic Imports")
    print(f"  Modules: {deps['modules']}")
    print(f"  From Imports: {deps['from_imports']}")
    print(f"  Line Numbers: {deps['line_numbers']}")

    # Verify results
    assert "os" in deps["modules"]
    assert "sys" in deps["modules"]
    assert "ast" in deps["from_imports"]
    assert "parse" in deps["from_imports"]["ast"]
    assert "typing" in deps["from_imports"]
    assert "List" in deps["from_imports"]["typing"]

    print("  ✓ Test passed!\n")


def test_star_import():
    """Test detection of star imports."""
    source_code = """
from math import *
from collections import defaultdict

def calculate():
    pass
"""

    mapper = SemanticMapper(source_code)
    deps = mapper.get_import_dependencies()

    print("Test 2: Star Import Detection")
    print(f"  From Imports: {deps['from_imports']}")
    print(f"  Contains star: {'*' in deps['from_imports'].get('math', [])}")

    assert "*" in deps["from_imports"]["math"]
    assert "defaultdict" in deps["from_imports"]["collections"]

    print("  ✓ Test passed!\n")


def test_classify_imports():
    """Test classification of internal vs external imports."""
    source_code = """
import os
import sys
from typing import List
from myproject.utils import helper
from myproject.models import User

def process():
    pass
"""

    mapper = SemanticMapper(source_code)
    project_modules = ["myproject"]
    classified = mapper.classify_imports(project_modules)

    print("Test 3: Import Classification")
    print(f"  External modules: {classified['external']['modules']}")
    print(f"  External from imports: {classified['external']['from_imports']}")
    print(f"  Internal modules: {classified['internal']['modules']}")
    print(f"  Internal from imports: {classified['internal']['from_imports']}")

    # os and sys should be external (stdlib)
    assert "os" in classified["external"]["modules"]
    assert "sys" in classified["external"]["modules"]
    assert "typing" in classified["external"]["from_imports"]

    # myproject modules should be internal
    assert "myproject.utils" in classified["internal"]["from_imports"]
    assert "myproject.models" in classified["internal"]["from_imports"]

    print("  ✓ Test passed!\n")


def test_dependency_graph():
    """Test building a dependency graph."""
    source_code = """
import os
import sys
from typing import List, Optional
from myproject.utils import helper
import requests

def fetch_data():
    pass
"""

    mapper = SemanticMapper(source_code)
    graph = mapper.get_module_dependency_graph()

    print("Test 4: Dependency Graph")
    print(f"  External packages: {graph['external_packages']}")
    print(f"  Has star import: {graph['is_importing_star']}")
    print(
        f"  Total imports: {len(graph['imports']['modules']) + len(graph['imports']['from_imports'])}"
    )

    # requests should be detected as external package
    assert "requests" in graph["external_packages"]

    # os, sys, typing are stdlib, so they shouldn't be in external_packages
    assert "os" not in graph["external_packages"]
    assert "sys" not in graph["external_packages"]

    print("  ✓ Test passed!\n")


def test_stdlib_detection():
    """Test standard library module detection."""
    source_code = """
import os
import sys
import json
import re
from collections import Counter
from typing import List
import requests  # External package
"""

    mapper = SemanticMapper(source_code)
    deps = mapper.get_import_dependencies()

    print("Test 5: Standard Library Detection")

    # Check that stdlib modules are correctly identified
    stdlib_modules = ["os", "sys", "json", "re", "collections", "typing"]
    for module in stdlib_modules:
        is_stdlib = mapper._is_stdlib_module(module.split(".")[0])
        print(f"  {module}: stdlib={is_stdlib}")
        assert is_stdlib, f"{module} should be detected as stdlib"

    # Check that requests is not stdlib
    is_requests_stdlib = mapper._is_stdlib_module("requests")
    print(f"  requests: stdlib={is_requests_stdlib}")
    assert not is_requests_stdlib, "requests should not be detected as stdlib"

    print("  ✓ Test passed!\n")


def test_complex_imports():
    """Test more complex import scenarios."""
    source_code = """
import os.path
from typing import List, Dict, Optional, Union
from collections.abc import Mapping
from myproject.core import config
from myproject import utils

class DataProcessor:
    def __init__(self):
        pass
"""

    mapper = SemanticMapper(source_code)
    deps = mapper.get_import_dependencies()

    print("Test 6: Complex Imports")
    print(f"  Modules: {deps['modules']}")
    print(f"  From Imports: {deps['from_imports']}")

    # Check that submodules are handled correctly
    assert "os.path" in deps["modules"]

    # Check multiple imports from same module
    assert len(deps["from_imports"]["typing"]) == 4

    # Check collections.abc
    assert "collections.abc" in deps["from_imports"]

    print("  ✓ Test passed!\n")


if __name__ == "__main__":
    print("=" * 60)
    print("Testing Import Dependency Analyzer (Task 1.3)")
    print("=" * 60)
    print()

    try:
        test_basic_imports()
        test_star_import()
        test_classify_imports()
        test_dependency_graph()
        test_stdlib_detection()
        test_complex_imports()

        print("=" * 60)
        print("All tests passed! ✓")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        raise
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        raise
