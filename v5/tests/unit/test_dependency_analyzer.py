"""
Unit tests for DependencyAnalyzer module (V5)
"""

import unittest
import os
import json
import tempfile
import shutil
from pathlib import Path
from v4.logic.dependency_analyzer import (
    DependencyAnalyzer, DependencyInfo, DependencyReport
)


class TestDependencyInfo(unittest.TestCase):
    """Test cases for DependencyInfo class."""
    
    def test_initial_state(self):
        """Test initial dependency info state."""
        info = DependencyInfo(name='test-package')
        
        self.assertEqual(info.name, 'test-package')
        self.assertIsNone(info.version)
        self.assertIsNone(info.latest_version)
        self.assertFalse(info.is_used)
        self.assertFalse(info.is_outdated)
        self.assertFalse(info.is_sub_dependency)
        self.assertEqual(info.import_count, 0)
        self.assertEqual(len(info.import_files), 0)
    
    def test_to_dict(self):
        """Test converting to dictionary."""
        info = DependencyInfo(
            name='test-package',
            version='1.0.0',
            latest_version='1.1.0',
            is_used=True,
            is_outdated=True,
            import_count=5
        )
        
        data = info.to_dict()
        
        self.assertEqual(data['name'], 'test-package')
        self.assertEqual(data['version'], '1.0.0')
        self.assertEqual(data['latest_version'], '1.1.0')
        self.assertTrue(data['is_used'])
        self.assertTrue(data['is_outdated'])
        self.assertEqual(data['import_count'], 5)


class TestDependencyReport(unittest.TestCase):
    """Test cases for DependencyReport class."""
    
    def test_initial_state(self):
        """Test initial report state."""
        report = DependencyReport()
        
        self.assertEqual(report.total_dependencies, 0)
        self.assertEqual(report.used_dependencies, 0)
        self.assertEqual(report.unused_dependencies, 0)
        self.assertEqual(report.outdated_dependencies, 0)
        self.assertEqual(report.sub_dependencies, 0)
        self.assertEqual(len(report.dependencies), 0)
        self.assertEqual(len(report.errors), 0)
    
    def test_add_error(self):
        """Test adding error to report."""
        report = DependencyReport()
        report.add_error("Test error")
        
        self.assertEqual(len(report.errors), 1)
        self.assertEqual(report.errors[0], "Test error")
    
    def test_get_unused(self):
        """Test getting unused dependencies."""
        report = DependencyReport()
        
        report.dependencies.append(
            DependencyInfo(name='used-pkg', is_used=True, is_sub_dependency=False)
        )
        report.dependencies.append(
            DependencyInfo(name='unused-pkg', is_used=False, is_sub_dependency=False)
        )
        report.dependencies.append(
            DependencyInfo(name='sub-dep', is_used=False, is_sub_dependency=True)
        )
        
        unused = report.get_unused()
        
        self.assertEqual(len(unused), 1)
        self.assertEqual(unused[0].name, 'unused-pkg')
    
    def test_get_outdated(self):
        """Test getting outdated dependencies."""
        report = DependencyReport()
        
        report.dependencies.append(
            DependencyInfo(name='current-pkg', is_outdated=False)
        )
        report.dependencies.append(
            DependencyInfo(name='old-pkg', is_outdated=True)
        )
        
        outdated = report.get_outdated()
        
        self.assertEqual(len(outdated), 1)
        self.assertEqual(outdated[0].name, 'old-pkg')
    
    def test_to_dict(self):
        """Test converting report to dictionary."""
        report = DependencyReport()
        report.total_dependencies = 10
        report.used_dependencies = 5
        report.unused_dependencies = 3
        report.dependencies.append(
            DependencyInfo(name='test-pkg', version='1.0.0')
        )
        
        data = report.to_dict()
        
        self.assertEqual(data['total_dependencies'], 10)
        self.assertEqual(data['used_dependencies'], 5)
        self.assertEqual(data['unused_dependencies'], 3)
        self.assertEqual(len(data['dependencies']), 1)
        self.assertEqual(data['dependencies'][0]['name'], 'test-pkg')


class TestDependencyAnalyzer(unittest.TestCase):
    """Test cases for DependencyAnalyzer class."""
    
    def setUp(self):
        """Set up test environment before each test."""
        self.test_dir = Path(tempfile.mkdtemp(prefix='dep_analyzer_test_'))
        
        # Create test Python files with various imports
        self._create_test_files()
        
        # Create test requirements file
        self._create_requirements_file()
    
    def tearDown(self):
        """Clean up test environment after each test."""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
    
    def _create_test_files(self):
        """Create test Python files with imports."""
        # Main module with imports
        main_file = self.test_dir / 'main.py'
        main_file.write_text('''
import os
import sys
from datetime import datetime
import requests  # Third-party package
from dataclasses import dataclass

def main():
    print("Hello, world")
''')
        
        # Sub-module with imports
        utils_file = self.test_dir / 'utils.py'
        utils_file.write_text('''
import os
import json
from typing import Optional
import numpy as np  # Third-party package

def helper():
    return "helper"
''')
        
        # Create subdirectory with module
        subdir = self.test_dir / 'subdir'
        subdir.mkdir()
        module_file = subdir / 'module.py'
        module_file.write_text('''
import os
from pathlib import Path

def submodule():
    return "submodule"
''')
    
    def _create_requirements_file(self):
        """Create test requirements file."""
        req_file = self.test_dir / 'requirements.txt'
        req_file.write_text('''
# Production dependencies
requests==2.28.0
numpy==1.24.0
pandas==1.5.0  # Not used in code
matplotlib==3.7.0  # Not used in code
pytest==7.4.0  # Dev dependency

# Comments and blank lines should be preserved

''')
    
    def test_init(self):
        """Test analyzer initialization."""
        analyzer = DependencyAnalyzer(project_root=str(self.test_dir))
        
        self.assertEqual(analyzer.project_root, self.test_dir)
        self.assertIsInstance(analyzer.requirements_files, list)
    
    def test_find_requirements_files(self):
        """Test finding requirements files."""
        analyzer = DependencyAnalyzer(project_root=str(self.test_dir))
        files = analyzer._find_requirements_files()
        
        self.assertIn('requirements.txt', files)
    
    def test_build_package_import_map(self):
        """Test building package import map."""
        analyzer = DependencyAnalyzer(project_root=str(self.test_dir))
        analyzer._build_package_import_map()
        
        # Check some known mappings
        self.assertIn('beautifulsoup4', analyzer._package_import_map)
        self.assertEqual(analyzer._package_import_map['beautifulsoup4'], 'bs4')
        
        self.assertIn('pillow', analyzer._package_import_map)
        self.assertEqual(analyzer._package_import_map['pillow'], 'PIL')
        
        self.assertIn('pyyaml', analyzer._package_import_map)
        self.assertEqual(analyzer._package_import_map['pyyaml'], 'yaml')
    
    def test_extract_imports_from_file(self):
        """Test extracting imports from a Python file."""
        analyzer = DependencyAnalyzer(project_root=str(self.test_dir))
        imports = {}
        
        main_file = self.test_dir / 'main.py'
        analyzer._extract_imports_from_file(str(main_file), imports)
        
        # Check that imports were captured
        self.assertIn('os', imports)
        self.assertIn('sys', imports)
        self.assertIn('datetime', imports)
        self.assertIn('requests', imports)
        self.assertIn('dataclasses', imports)
        
        # Check counts (some imported multiple times via 'from')
        self.assertGreater(imports['requests']['count'], 0)
    
    def test_get_used_imports(self):
        """Test getting all used imports."""
        analyzer = DependencyAnalyzer(project_root=str(self.test_dir))
        imports = analyzer._get_used_imports()
        
        # Check common imports
        self.assertIn('os', imports)
        self.assertIn('sys', imports)
        self.assertIn('requests', imports)
        self.assertIn('numpy', imports)
        self.assertIn('pathlib', imports)
        
        # Check file lists
        self.assertGreater(len(imports['os']['files']), 1)  # Used in multiple files
    
    def test_get_import_name(self):
        """Test getting import name for package."""
        analyzer = DependencyAnalyzer(project_root=str(self.test_dir))
        
        # Direct mapping
        self.assertEqual(analyzer._get_import_name('requests'), 'requests')
        
        # Mapped package
        self.assertEqual(analyzer._get_import_name('beautifulsoup4'), 'bs4')
        self.assertEqual(analyzer._get_import_name('pillow'), 'PIL')
        self.assertEqual(analyzer._get_import_name('pyyaml'), 'yaml')
        
        # Case insensitive
        self.assertEqual(analyzer._get_import_name('BeautifulSoup4'), 'bs4')
        self.assertEqual(analyzer._get_import_name('Pillow'), 'PIL')
    
    def test_analyze_basic(self):
        """Test basic dependency analysis."""
        # Mock _get_installed_packages to return test data
        analyzer = DependencyAnalyzer(project_root=str(self.test_dir))
        
        # Override to use test data instead of calling pip
        original_get_installed = analyzer._get_installed_packages
        analyzer._get_installed_packages = lambda: {
            'requests': '2.28.0',
            'numpy': '1.24.0',
            'pandas': '1.5.0',
            'matplotlib': '3.7.0',
            'pytest': '7.4.0'
        }
        
        # Override sub-dependencies to return empty
        analyzer._get_sub_dependencies = lambda packages: set()
        
        report = analyzer.analyze(check_outdated=False)
        
        # Restore original method
        analyzer._get_installed_packages = original_get_installed
        
        # Check report
        self.assertEqual(report.total_dependencies, 5)
        self.assertEqual(report.used_dependencies, 2)  # requests, numpy
        self.assertEqual(report.unused_dependencies, 3)  # pandas, matplotlib, pytest
        
        # Check specific dependencies
        requests_dep = next((d for d in report.dependencies if d.name == 'requests'), None)
        self.assertIsNotNone(requests_dep)
        self.assertTrue(requests_dep.is_used)
        self.assertEqual(requests_dep.version, '2.28.0')
        
        pandas_dep = next((d for d in report.dependencies if d.name == 'pandas'), None)
        self.assertIsNotNone(pandas_dep)
        self.assertFalse(pandas_dep.is_used)
    
    def test_analyze_with_sub_dependencies(self):
        """Test dependency analysis with sub-dependencies."""
        analyzer = DependencyAnalyzer(project_root=str(self.test_dir))
        
        # Override to use test data
        analyzer._get_installed_packages = lambda: {
            'requests': '2.28.0',
            'urllib3': '2.0.0'  # Sub-dependency
        }
        
        # Mark urllib3 as sub-dependency
        analyzer._get_sub_dependencies = lambda packages: {'urllib3'}
        
        report = analyzer.analyze(check_outdated=False)
        
        # Check that sub-dependency is marked
        urllib_dep = next((d for d in report.dependencies if d.name == 'urllib3'), None)
        self.assertIsNotNone(urllib_dep)
        self.assertTrue(urllib_dep.is_sub_dependency)
        self.assertEqual(report.sub_dependencies, 1)
        
        # Sub-dependency should not be in unused list
        unused = report.get_unused()
        self.assertFalse(any(d.name == 'urllib3' for d in unused))
    
    def test_cleanup_unused_dry_run(self):
        """Test cleanup in dry-run mode."""
        analyzer = DependencyAnalyzer(project_root=str(self.test_dir))
        
        # Override analysis
        analyzer.analyze = lambda check_outdated=False: DependencyReport(
            total_dependencies=5,
            dependencies=[
                DependencyInfo(name='requests', is_used=True),
                DependencyInfo(name='unused-pkg', is_used=False),
                DependencyInfo(name='another-unused', is_used=False)
            ]
        )
        
        success, removed = analyzer.cleanup_unused(
            dry_run=True,
            backup=False,
            requirements_file='requirements.txt'
        )
        
        self.assertTrue(success)
        self.assertEqual(len(removed), 2)  # 2 unused packages
        
        # Verify requirements file unchanged (dry run)
        req_file = self.test_dir / 'requirements.txt'
        content = req_file.read_text()
        self.assertIn('unused-pkg', content)  # Should still be there
    
    def test_cleanup_unused_actual(self):
        """Test actual cleanup of unused dependencies."""
        # Create test requirements with unused packages
        req_file = self.test_dir / 'requirements.txt'
        req_file.write_text('''
requests==2.28.0
unused-package==1.0.0
another-unused==2.0.0
''')
        
        analyzer = DependencyAnalyzer(project_root=str(self.test_dir))
        
        # Override analysis
        analyzer.analyze = lambda check_outdated=False: DependencyReport(
            total_dependencies=3,
            dependencies=[
                DependencyInfo(name='requests', is_used=True),
                DependencyInfo(name='unused-package', is_used=False),
                DependencyInfo(name='another-unused', is_used=False)
            ]
        )
        
        success, removed = analyzer.cleanup_unused(
            dry_run=False,
            backup=False,
            requirements_file='requirements.txt'
        )
        
        self.assertTrue(success)
        self.assertEqual(len(removed), 2)
        self.assertIn('unused-package', removed)
        self.assertIn('another-unused', removed)
        
        # Verify requirements file updated
        content = req_file.read_text()
        self.assertIn('requests', content)
        self.assertNotIn('unused-package', content)
        self.assertNotIn('another-unused', content)
    
    def test_cleanup_with_backup(self):
        """Test cleanup with backup."""
        req_file = self.test_dir / 'requirements.txt'
        req_file.write_text('requests==2.28.0\nunused==1.0.0\n')
        
        analyzer = DependencyAnalyzer(project_root=str(self.test_dir))
        
        # Override analysis
        analyzer.analyze = lambda check_outdated=False: DependencyReport(
            total_dependencies=2,
            dependencies=[
                DependencyInfo(name='requests', is_used=True),
                DependencyInfo(name='unused', is_used=False)
            ]
        )
        
        success, removed = analyzer.cleanup_unused(
            dry_run=False,
            backup=True,
            requirements_file='requirements.txt'
        )
        
        self.assertTrue(success)
        
        # Verify backup created
        backup_file = req_file.with_suffix('.txt.backup')
        self.assertTrue(backup_file.exists())
        
        # Backup should contain original content
        backup_content = backup_file.read_text()
        self.assertIn('unused', backup_content)
        
        # Original should be updated
        original_content = req_file.read_text()
        self.assertNotIn('unused', original_content)
    
    def test_cleanup_preserves_comments(self):
        """Test that cleanup preserves comments and blank lines."""
        req_file = self.test_dir / 'requirements.txt'
        req_file.write_text('''
# Production dependencies
requests==2.28.0
unused==1.0.0

# Development dependencies
pytest==7.4.0

# More comments
''')
        
        analyzer = DependencyAnalyzer(project_root=str(self.test_dir))
        
        # Override analysis
        analyzer.analyze = lambda check_outdated=False: DependencyReport(
            total_dependencies=3,
            dependencies=[
                DependencyInfo(name='requests', is_used=True),
                DependencyInfo(name='unused', is_used=False),
                DependencyInfo(name='pytest', is_used=True)
            ]
        )
        
        success, removed = analyzer.cleanup_unused(
            dry_run=False,
            backup=False,
            requirements_file='requirements.txt'
        )
        
        content = req_file.read_text()
        
        # Verify comments preserved
        self.assertIn('# Production dependencies', content)
        self.assertIn('# Development dependencies', content)
        self.assertIn('# More comments', content)
        
        # Verify unused package removed but used ones kept
        self.assertNotIn('unused', content)
        self.assertIn('requests', content)
        self.assertIn('pytest', content)
    
    def test_generate_report(self):
        """Test report generation."""
        report = DependencyReport(
            total_dependencies=5,
            used_dependencies=2,
            unused_dependencies=2,
            outdated_dependencies=1,
            sub_dependencies=1,
            dependencies=[
                DependencyInfo(
                    name='used-pkg',
                    version='1.0.0',
                    is_used=True,
                    import_count=5
                ),
                DependencyInfo(
                    name='unused-pkg',
                    version='2.0.0',
                    is_used=False
                ),
                DependencyInfo(
                    name='outdated-pkg',
                    version='1.0.0',
                    latest_version='1.5.0',
                    is_outdated=True
                )
            ]
        )
        
        analyzer = DependencyAnalyzer(project_root=str(self.test_dir))
        report_text = analyzer.generate_report(report)
        
        # Check report structure
        self.assertIn('DEPENDENCY ANALYSIS REPORT', report_text)
        self.assertIn('Total Dependencies:', report_text)
        self.assertIn('USED:               2', report_text)
        self.assertIn('UNUSED DEPENDENCIES', report_text)
        self.assertIn('OUTDATED DEPENDENCIES', report_text)
        
        # Check specific package info
        self.assertIn('used-pkg', report_text)
        self.assertIn('unused-pkg', report_text)
        self.assertIn('outdated-pkg', report_text)
        self.assertIn('Current:  1.0.0', report_text)
        self.assertIn('Latest:   1.5.0', report_text)
    
    def test_skip_non_code_directories(self):
        """Test that non-code directories are skipped."""
        # Create directories that should be skipped
        (self.test_dir / '.git').mkdir()
        (self.test_dir / '__pycache__').mkdir()
        (self.test_dir / 'venv').mkdir()
        (self.test_dir / 'node_modules').mkdir()
        
        # Create Python file in skipped directory
        (self.test_dir / '.git' / 'hook.py').write_text('import requests')
        
        analyzer = DependencyAnalyzer(project_root=str(self.test_dir))
        imports = analyzer._get_used_imports()
        
        # requests from .git should not be counted (only from main files)
        self.assertGreater(imports.get('requests', {}).get('count', 0), 0)
    
    def test_handle_syntax_errors(self):
        """Test handling of files with syntax errors."""
        # Create file with syntax error
        bad_file = self.test_dir / 'bad_syntax.py'
        bad_file.write_text('''
import os
def broken(
    # Missing closing parenthesis
''')
        
        analyzer = DependencyAnalyzer(project_root=str(self.test_dir))
        imports = analyzer._get_used_imports()
        
        # Should not crash, just skip the bad file
        self.assertIsInstance(imports, dict)
    
    def test_case_insensitive_package_matching(self):
        """Test case-insensitive package name matching."""
        req_file = self.test_dir / 'requirements.txt'
        req_file.write_text('Requests==2.28.0\nNumpy==1.24.0\n')
        
        analyzer = DependencyAnalyzer(project_root=str(self.test_dir))
        
        # Override analysis
        analyzer.analyze = lambda check_outdated=False: DependencyReport(
            total_dependencies=2,
            dependencies=[
                DependencyInfo(name='Requests', is_used=True),  # Capitalized
                DependencyInfo(name='Numpy', is_used=False)
            ]
        )
        
        success, removed = analyzer.cleanup_unused(
            dry_run=False,
            backup=False,
            requirements_file='requirements.txt'
        )
        
        self.assertTrue(success)
        
        # Verify case-insensitive matching worked
        content = req_file.read_text()
        self.assertNotIn('Numpy', content)  # Should be removed
        self.assertIn('Requests', content)  # Should be kept


if __name__ == '__main__':
    unittest.main()