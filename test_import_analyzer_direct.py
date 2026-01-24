#!/usr/bin/env python3
"""
Direct test for import_analyzer without going through logic/__init__
"""
import sys
import os

# Add v4 to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'v4'))

# Import directly from the module file
import importlib.util

# Load import_analyzer module directly
spec = importlib.util.spec_from_file_location(
    "import_analyzer",
    os.path.join(os.path.dirname(__file__), 'v4/logic/import_analyzer.py')
)
import_analyzer_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(import_analyzer_module)

ImportAnalyzer = import_analyzer_module.ImportAnalyzer
ImportInfo = import_analyzer_module.ImportInfo

print("✓ ImportAnalyzer and ImportInfo imported successfully!")

# Test with sample code
sample_code = """
import os
import sys
from typing import List, Dict, Optional
from dataclasses import dataclass

def example_function():
    pass

class ExampleClass:
    def method(self):
        pass
"""

analyzer = ImportAnalyzer()
imports = analyzer.analyze_imports(sample_code, "test.py")

print(f"\n✓ Analysis complete!")
print(f"  Found {len(imports)} imports")
print(f"  Unused imports: {len(analyzer.find_unused_imports(imports, sample_code))}")

print("\n=== Import Analyzer Test PASSED ===")