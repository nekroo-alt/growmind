"""
Unit tests for Import Analyzer module (V5 Task 1.2)

Tests import dependency analysis including:
- Import detection (absolute, relative, from imports)
- Unused import detection
- Circular dependency detection
- Import depth calculation
- Report generation
"""

import os
import sys
import unittest
import tempfile
import shutil
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from v5.logic.import_analyzer import ImportAnalyzer, ImportInfo
from v5.data.call_graph_persistence import CallGraphPersistence


class TestImportAnalyzer(unittest.TestCase):
    """Test cases for ImportAnalyzer."""

    def setUp(self):
        """Set up test fixtures."""
        # Create temporary directory for test files
        self.test_dir = tempfile.mkdtemp()
        self.project_root = self.test_dir

        # Create analyzer instance
        self.analyzer = ImportAnalyzer(self.project_root)

        # Create temporary database
        self.db_path = os.path.join(self.test_dir, 'call_graph.db')
        self.call_graph_persistence = CallGraphPersistence(self.db_path)
        self.analyzer.call_graph_persistence = self.call_graph_persistence

    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def _create_test_file(self, filename, content):
        """Helper to create test Python files."""
        filepath = os.path.join(self.test_dir, filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return filepath

    def test_import_analyzer_initialization(self):
        """Test ImportAnalyzer initializes correctly."""
        analyzer = ImportAnalyzer(self.project_root)
        self.assertEqual(analyzer.project_root, self.project_root)
        self.assertIsNotNone(analyzer.call_graph_persistence)

    def test_analyze_simple_import(self):
        """Test analyzing simple import statement."""
        code = """import os
import sys
import json

def main():
    os.path.join('a', 'b')
    print(os.getcwd())
"""
        filepath = self._create_test_file('simple.py', code)
        imports = self.analyzer.analyze_file_imports(filepath)

        self.assertEqual(len(imports), 3)

        # Check os import
        os_import = [imp for imp in imports if imp.module_name == 'os'][0]
        self.assertEqual(os_import.import_type, 'import')
        self.assertEqual(os_import.line_number, 1)

        # Check sys import
        sys_import = [imp for imp in imports if imp.module_name == 'sys'][0]
        self.assertEqual(sys_import.import_type, 'import')
        self.assertEqual(sys_import.line_number, 2)

        # Check json import
        json_import = [imp for imp in imports if imp.module_name == 'json'][0]
        self.assertEqual(json_import.import_type, 'import')
        self.assertEqual(json_import.line_number, 3)

    def test_analyze_from_import(self):
        """Test analyzing from import statement."""
        code = """from os.path import join
from typing import List, Dict, Optional
from ast import parse, walk

def main():
    result = join('a', 'b')
    items: List[str] = []
    tree = parse(code)
"""
        filepath = self._create_test_file('from_import.py', code)
        imports = self.analyzer.analyze_file_imports(filepath)

        self.assertEqual(len(imports), 3)

        # Check os.path import
        os_import = [imp for imp in imports if imp.module_name == 'os.path'][0]
        self.assertEqual(os_import.import_type, 'from')
        self.assertEqual(os_import.imported_names, ['join'])

        # Check typing import
        typing_import = [imp for imp in imports if imp.module_name == 'typing'][0]
        self.assertEqual(typing_import.import_type, 'from')
        self.assertEqual(sorted(typing_import.imported_names), ['Dict', 'List', 'Optional'])

        # Check ast import
        ast_import = [imp for imp in imports if imp.module_name == 'ast'][0]
        self.assertEqual(ast_import.import_type, 'from')
        self.assertEqual(sorted(ast_import.imported_names), ['parse', 'walk'])

    def test_detect_unused_import(self):
        """Test detecting unused imports."""
        code = """import os
import sys
import json  # Unused
from typing import List, Dict  # Dict is unused

def main():
    path = os.path.join('a', 'b')
    items: List[str] = []
    return path
"""
        filepath = self._create_test_file('unused.py', code)
        unused = self.analyzer.detect_unused_imports(filepath)

        # Should detect json as unused
        json_unused = [u for u in unused if u['module_name'] == 'json']
        self.assertEqual(len(json_unused), 1)
        self.assertIn('Remove unused import', json_unused[0]['suggestion'])

        # Should detect Dict as unused from typing import
        dict_unused = [u for u in unused if 'Dict' in u.get('imported_names', [])]
        self.assertEqual(len(dict_unused), 1)

    def test_detect_all_unused_names_in_from_import(self):
        """Test detecting when all names in from import are unused."""
        code = """from typing import List, Dict, Optional  # All unused

def main():
    items = [1, 2, 3]
    return items
"""
        filepath = self._create_test_file('all_unused.py', code)
        unused = self.analyzer.detect_unused_imports(filepath)

        # Should detect the entire import as unused
        self.assertEqual(len(unused), 1)
        self.assertIn('typing', unused[0]['module_name'])
        self.assertIn('Remove unused import', unused[0]['suggestion'])

    def test_detect_partial_unused_in_from_import(self):
        """Test detecting when some names in from import are unused."""
        code = """from typing import List, Dict, Optional  # Dict is unused

def main():
    items: List[str] = []
    value: Optional[int] = None
    return items
"""
        filepath = self._create_test_file('partial_unused.py', code)
        unused = self.analyzer.detect_unused_imports(filepath)

        # Should detect only Dict as unused
        dict_unused = [u for u in unused if 'Dict' in u.get('imported_names', [])]
        self.assertEqual(len(dict_unused), 1)
        self.assertIn('Keep:', dict_unused[0]['suggestion'])

    def test_star_import_not_flagged_unused(self):
        """Test that star imports are not flagged as unused."""
        code = """from module import *

def main():
    some_function()
"""
        filepath = self._create_test_file('star_import.py', code)
        unused = self.analyzer.detect_unused_imports(filepath)

        # Star imports should not be flagged
        module_unused = [u for u in unused if u['module_name'] == 'module']
        self.assertEqual(len(module_unused), 0)

    def test_detect_circular_direct_dependencies(self):
        """Test detecting direct circular dependencies."""
        # Create module_a.py
        code_a = """from growmind.module_b import func_b

def func_a():
    return func_b()
"""
        self._create_test_file('module_a.py', code_a)

        # Create module_b.py
        code_b = """from growmind.module_a import func_a

def func_b():
    return func_a()
"""
        self._create_test_file('module_b.py', code_b)

        # Detect circular dependencies
        cycles = self.analyzer.detect_circular_dependencies()

        # Should find at least one cycle
        self.assertGreater(len(cycles), 0)

        # Check cycle severity
        direct_cycles = [c for c in cycles if c['severity'] == 'direct']
        self.assertGreater(len(direct_cycles), 0)

    def test_detect_circular_indirect_dependencies(self):
        """Test detecting indirect circular dependencies."""
        # Create module_a.py
        code_a = """from growmind.module_b import func_b

def func_a():
    return func_b()
"""
        self._create_test_file('module_a.py', code_a)

        # Create module_b.py
        code_b = """from growmind.module_c import func_c

def func_b():
    return func_c()
"""
        self._create_test_file('module_b.py', code_b)

        # Create module_c.py
        code_c = """from growmind.module_a import func_a

def func_c():
    return func_a()
"""
        self._create_test_file('module_c.py', code_c)

        # Detect circular dependencies
        cycles = self.analyzer.detect_circular_dependencies()

        # Should find at least one cycle
        self.assertGreater(len(cycles), 0)

        # Check cycle length (should be 3 for indirect)
        indirect_cycles = [c for c in cycles if c['severity'] == 'indirect']
        if indirect_cycles:
            self.assertGreaterEqual(indirect_cycles[0]['cycle_length'], 2)

    def test_no_circular_dependencies(self):
        """Test that no circular dependencies are detected when none exist."""
        # Create module_a.py
        code_a = """from growmind.module_b import func_b

def func_a():
    return func_b()
"""
        self._create_test_file('module_a.py', code_a)

        # Create module_b.py (no circular import)
        code_b = """def func_b():
    return 'hello'
"""
        self._create_test_file('module_b.py', code_b)

        # Detect circular dependencies
        cycles = self.analyzer.detect_circular_dependencies()

        # Should find no cycles
        self.assertEqual(len(cycles), 0)

    def test_calculate_import_depth_leaf(self):
        """Test calculating import depth for leaf modules."""
        # Create leaf.py (no imports)
        code_leaf = """def leaf_function():
    return 'leaf'
"""
        self._create_test_file('leaf.py', code_leaf)

        # Calculate depth
        depth = self.analyzer.calculate_import_depth(
            os.path.join(self.test_dir, 'leaf.py')
        )

        # Leaf should have depth 0
        self.assertEqual(depth['depth'], 0)
        self.assertTrue(depth['is_leaf'])

    def test_calculate_import_depth_non_leaf(self):
        """Test calculating import depth for non-leaf modules."""
        # Create leaf.py
        code_leaf = """def leaf_function():
    return 'leaf'
"""
        self._create_test_file('leaf.py', code_leaf)

        # Create root.py (imports leaf)
        code_root = """from growmind.leaf import leaf_function

def root_function():
    return leaf_function()
"""
        self._create_test_file('root.py', code_root)

        # Calculate depth for root
        depth = self.analyzer.calculate_import_depth(
            os.path.join(self.test_dir, 'root.py')
        )

        # Root should have depth > 0
        self.assertGreater(depth['depth'], 0)
        self.assertFalse(depth['is_leaf'])

    def test_generate_text_report(self):
        """Test generating text format report."""
        code = """import os
import sys  # Unused

def main():
    return os.getcwd()
"""
        self._create_test_file('report_test.py', code)

        # Generate report
        report = self.analyzer.generate_import_report(format='text')

        # Check report structure
        self.assertIn('IMPORT DEPENDENCY REPORT', report)
        self.assertIn('Total Files:', report)
        self.assertIn('Total Imports:', report)
        self.assertIn('STATISTICS:', report)
        self.assertIn('Simple Imports:', report)
        self.assertIn('From Imports:', report)

    def test_generate_json_report(self):
        """Test generating JSON format report."""
        code = """import os

def main():
    return os.getcwd()
"""
        self._create_test_file('json_test.py', code)

        # Generate report
        report = self.analyzer.generate_import_report(format='json')

        # Check it's valid JSON
        import json
        data = json.loads(report)

        # Check structure
        self.assertIn('total_files', data)
        self.assertIn('total_imports', data)
        self.assertIn('unused_imports', data)
        self.assertIn('circular_dependencies', data)
        self.assertIn('import_depths', data)
        self.assertIn('statistics', data)

    def test_generate_markdown_report(self):
        """Test generating markdown format report."""
        code = """import os

def main():
    return os.getcwd()
"""
        self._create_test_file('md_test.py', code)

        # Generate report
        report = self.analyzer.generate_import_report(format='markdown')

        # Check markdown structure
        self.assertIn('# Import Dependency Report', report)
        self.assertIn('## Summary', report)
        self.assertIn('## Statistics', report)

    def test_analyze_project(self):
        """Test analyzing entire project."""
        # Create multiple files
        code1 = """import os

def func1():
    return os.getcwd()
"""
        self._create_test_file('file1.py', code1)

        code2 = """import json

def func2():
    return json.dumps({})
"""
        self._create_test_file('file2.py', code2)

        # Analyze project
        analysis = self.analyzer.analyze_project(recursive=True)

        # Check structure
        self.assertIn('total_files', analysis)
        self.assertIn('total_imports', analysis)
        self.assertIn('unused_imports', analysis)
        self.assertIn('circular_dependencies', analysis)
        self.assertIn('import_depths', analysis)
        self.assertIn('statistics', analysis)

        # Check counts
        self.assertEqual(analysis['total_files'], 2)
        self.assertEqual(analysis['total_imports'], 2)

    def test_cache_import_analysis(self):
        """Test that import analysis is cached."""
        code = """import os

def main():
    return os.getcwd()
"""
        filepath = self._create_test_file('cache_test.py', code)

        # First analysis
        imports1 = self.analyzer.analyze_file_imports(filepath)
        self.assertEqual(len(imports1), 1)

        # Modify file
        code2 = """import os
import sys

def main():
    return os.getcwd()
"""
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(code2)

        # Second analysis should return cached results
        imports2 = self.analyzer.analyze_file_imports(filepath)
        self.assertEqual(len(imports2), 1)  # Still 1 from cache

    def test_cache_usage_analysis(self):
        """Test that usage analysis is cached."""
        code = """import os

def main():
    return os.getcwd()
"""
        filepath = self._create_test_file('usage_cache_test.py', code)

        # First usage check
        used1 = self.analyzer._get_used_names(filepath)
        self.assertIn('os', used1)

        # Modify file
        code2 = """import sys

def main():
    return sys.path
"""
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(code2)

        # Second usage check should return cached results
        used2 = self.analyzer._get_used_names(filepath)
        self.assertIn('os', used2)  # Still contains os from cache

    def test_import_info_dataclass(self):
        """Test ImportInfo dataclass."""
        imp = ImportInfo(
            file_path='/test/file.py',
            module_name='os',
            import_type='import',
            imported_names=None,
            line_number=1,
            is_used=True,
            usage_count=5
        )

        self.assertEqual(imp.file_path, '/test/file.py')
        self.assertEqual(imp.module_name, 'os')
        self.assertEqual(imp.import_type, 'import')
        self.assertEqual(imp.imported_names, None)
        self.assertEqual(imp.line_number, 1)
        self.assertEqual(imp.is_used, True)
        self.assertEqual(imp.usage_count, 5)

    def test_find_python_files_recursive(self):
        """Test finding Python files recursively."""
        # Create nested structure
        self._create_test_file('root.py', 'pass')
        self._create_test_file('subdir/module.py', 'pass')
        self._create_test_file('subdir/nested/deep.py', 'pass')

        # Find files
        files = self.analyzer._find_python_files(self.project_root, recursive=True)

        # Should find all files
        self.assertEqual(len(files), 3)
        self.assertIn(os.path.join(self.project_root, 'root.py'), files)
        self.assertIn(os.path.join(self.project_root, 'subdir/module.py'), files)

    def test_find_python_files_non_recursive(self):
        """Test finding Python files non-recursively."""
        # Create nested structure
        self._create_test_file('root.py', 'pass')
        self._create_test_file('subdir/module.py', 'pass')

        # Find files non-recursively
        files = self.analyzer._find_python_files(self.project_root, recursive=False)

        # Should find only root file
        self.assertEqual(len(files), 1)
        self.assertIn(os.path.join(self.project_root, 'root.py'), files)

    def test_skip_ignored_directories(self):
        """Test that ignored directories are skipped."""
        # Create files in various directories
        self._create_test_file('root.py', 'pass')
        self._create_test_file('.git/config', 'pass')
        self._create_test_file('__pycache__/cache.py', 'pass')
        self._create_test_file('venv/lib/module.py', 'pass')

        # Find files
        files = self.analyzer._find_python_files(self.project_root, recursive=True)

        # Should find only root.py
        self.assertEqual(len(files), 1)
        self.assertIn(os.path.join(self.project_root, 'root.py'), files)

    def test_file_to_module_conversion(self):
        """Test converting file path to module name."""
        # Create nested file
        filepath = self._create_test_file('subdir/nested/module.py', 'pass')

        # Convert to module
        module = self.analyzer._file_to_module(filepath)

        # Check module name
        self.assertEqual(module, 'subdir.nested.module')

    def test_statistics_calculation(self):
        """Test statistics calculation."""
        # Create imports
        imports = [
            ImportInfo('file1.py', 'os', 'import', None, 1, True, 5),
            ImportInfo('file2.py', 'json', 'import', None, 2, True, 3),
            ImportInfo('file3.py', 'typing', 'from', ['List', 'Dict'], 3, True, 2),
        ]

        # Create unused imports
        unused = [
            {'module_name': 'sys'},
            {'module_name': 're'},
        ]

        # Create circular dependencies
        circular = [
            {'cycle': ['a', 'b', 'a']},
            {'cycle': ['x', 'y', 'z', 'x']},
        ]

        # Calculate statistics
        stats = self.analyzer._calculate_statistics(imports, unused, circular)

        # Check counts
        self.assertEqual(stats['simple_imports'], 2)
        self.assertEqual(stats['from_imports'], 1)
        self.assertEqual(stats['unused_count'], 2)
        self.assertEqual(stats['circular_count'], 2)


class TestImportAnalyzerIntegration(unittest.TestCase):
    """Integration tests for ImportAnalyzer."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        self.project_root = self.test_dir
        self.analyzer = ImportAnalyzer(self.project_root)

    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def _create_test_file(self, filename, content):
        """Helper to create test Python files."""
        filepath = os.path.join(self.test_dir, filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return filepath

    def test_complete_analysis_workflow(self):
        """Test complete analysis workflow."""
        # Create test project structure
        code_main = """import os
from growmind.utils import helper
from typing import List  # Dict is unused

def main():
    path = os.path.join('a', 'b')
    items: List[str] = []
    return helper(items)
"""
        self._create_test_file('main.py', code_main)

        code_utils = """from growmind.models import Data

def helper(items):
    data = Data(items)
    return data.process()
"""
        self._create_test_file('utils.py', code_utils)

        code_models = """class Data:
    def __init__(self, items):
        self.items = items

    def process(self):
        return self.items
"""
        self._create_test_file('models.py', code_models)

        # Analyze project
        analysis = self.analyzer.analyze_project(recursive=True)

        # Verify structure
        self.assertEqual(analysis['total_files'], 3)
        self.assertGreaterEqual(analysis['total_imports'], 3)

        # Check statistics
        stats = analysis['statistics']
        self.assertIn('simple_imports', stats)
        self.assertIn('from_imports', stats)
        self.assertIn('unused_count', stats)
        self.assertIn('circular_count', stats)

        # Generate reports in all formats
        text_report = self.analyzer.generate_import_report(format='text')
        self.assertIn('IMPORT DEPENDENCY REPORT', text_report)

        json_report = self.analyzer.generate_import_report(format='json')
        self.assertIn('total_files', json_report)

        md_report = self.analyzer.generate_import_report(format='markdown')
        self.assertIn('# Import Dependency Report', md_report)


if __name__ == '__main__':
    unittest.main()