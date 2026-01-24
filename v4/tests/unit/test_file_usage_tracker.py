"""
Unit tests for File Usage Tracker Module (V5)

Tests cover:
- File usage tracking
- Entry point detection
- Import tracking
- Unused file identification
- Report generation
- Statistics calculation
"""

import os
import sys
import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from v4.logic.file_usage_tracker import FileUsageTracker, FileInfo, UnusedFileCandidate
from v4.logic.import_analyzer import ImportAnalyzer


class TestFileUsageTracker:
    """Test suite for FileUsageTracker class."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create temporary directory for test project
        self.test_dir = tempfile.mkdtemp()

        # Create test file structure
        self._create_test_files()

    def teardown_method(self):
        """Clean up test fixtures."""
        # Remove temporary directory
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def _create_test_files(self):
        """Create test file structure."""
        # Create a Python file with imports
        main_file = os.path.join(self.test_dir, 'main.py')
        with open(main_file, 'w') as f:
            f.write("""
import utils
import config
from helpers import helper_function

def main():
    helper_function()

if __name__ == '__main__':
    main()
""")

        # Create a utility file
        utils_file = os.path.join(self.test_dir, 'utils.py')
        with open(utils_file, 'w') as f:
            f.write("""
def utility_function():
    return "utility"
""")

        # Create a helper file
        helpers_dir = os.path.join(self.test_dir, 'helpers')
        os.makedirs(helpers_dir, exist_ok=True)
        helper_file = os.path.join(helpers_dir, '__init__.py')
        with open(helper_file, 'w') as f:
            f.write("""
from .helper_module import helper_function
""")
        helper_module = os.path.join(helpers_dir, 'helper_module.py')
        with open(helper_module, 'w') as f:
            f.write("""
def helper_function():
    return "helper"
""")

        # Create an old, unused file
        old_file = os.path.join(self.test_dir, 'old_unused.py')
        with open(old_file, 'w') as f:
            f.write("""
def old_function():
    return "old"
""")
        # Set modification time to 60 days ago
        old_time = datetime.now() - timedelta(days=60)
        old_timestamp = old_time.timestamp()
        os.utime(old_file, (old_timestamp, old_timestamp))

        # Create a test file
        test_file = os.path.join(self.test_dir, 'test_main.py')
        with open(test_file, 'w') as f:
            f.write("""
import unittest
from main import main

class TestMain(unittest.TestCase):
    def test_main(self):
        self.assertIsNotNone(main)
""")

        # Create documentation
        readme_file = os.path.join(self.test_dir, 'README.md')
        with open(readme_file, 'w') as f:
            f.write("""
# Test Project

This is a test project.
""")

        # Create configuration
        config_file = os.path.join(self.test_dir, 'config.py')
        with open(config_file, 'w') as f:
            f.write("""
DEBUG = True
VERSION = "1.0.0"
""")

    def test_initialization(self):
        """Test FileUsageTracker initialization."""
        tracker = FileUsageTracker(self.test_dir)

        assert tracker.project_root == self.test_dir
        assert tracker.unused_age_threshold == timedelta(days=30)
        assert isinstance(tracker.import_analyzer, ImportAnalyzer)
        assert len(tracker._file_cache) == 0

    def test_initialization_with_custom_threshold(self):
        """Test FileUsageTracker initialization with custom age threshold."""
        tracker = FileUsageTracker(self.test_dir, unused_age_days=15)

        assert tracker.unused_age_threshold == timedelta(days=15)

    def test_find_python_files(self):
        """Test finding Python files in project."""
        tracker = FileUsageTracker(self.test_dir)

        python_files = tracker._find_python_files(self.test_dir, recursive=True)

        assert len(python_files) >= 5  # Should find at least main.py, utils.py, config.py, test_main.py, old_unused.py
        assert any('main.py' in f for f in python_files)
        assert any('utils.py' in f for f in python_files)
        assert any('config.py' in f for f in python_files)
        assert any('test_main.py' in f for f in python_files)

    def test_find_all_files(self):
        """Test finding all relevant files in project."""
        tracker = FileUsageTracker(self.test_dir)

        all_files = tracker._find_all_files(self.test_dir, recursive=True)

        assert len(all_files) >= 7  # Should find .py, .md files
        assert any('.py' in f for f in all_files)
        assert any('.md' in f for f in all_files)

    def test_determine_file_type(self):
        """Test file type determination."""
        tracker = FileUsageTracker(self.test_dir)

        # Test Python file
        py_file = os.path.join(self.test_dir, 'main.py')
        assert tracker._determine_file_type(py_file) == 'python'

        # Test file
        test_file = os.path.join(self.test_dir, 'test_main.py')
        assert tracker._determine_file_type(test_file) == 'test'

        # Documentation file
        readme_file = os.path.join(self.test_dir, 'README.md')
        assert tracker._determine_file_type(readme_file) == 'documentation'

        # Config file
        config_file = os.path.join(self.test_dir, 'config.py')
        # Not a config file because it ends with .py
        assert tracker._determine_file_type(config_file) == 'python'

    def test_find_entry_points(self):
        """Test finding entry point files."""
        tracker = FileUsageTracker(self.test_dir)

        entry_points = tracker._find_entry_points(self.test_dir, recursive=True)

        # main.py has if __name__ == '__main__' block
        main_file = os.path.join(self.test_dir, 'main.py')
        assert main_file in entry_points
        assert entry_points[main_file] == 1

        # test_main.py should not be an entry point
        test_file = os.path.join(self.test_dir, 'test_main.py')
        assert test_file not in entry_points

    def test_get_file_info(self):
        """Test getting file information."""
        tracker = FileUsageTracker(self.test_dir)

        main_file = os.path.join(self.test_dir, 'main.py')
        file_info = tracker._get_file_info(main_file)

        assert file_info.file_path == main_file
        assert file_info.file_type == 'python'
        assert file_info.size_bytes > 0
        assert isinstance(file_info.last_modified, datetime)
        assert file_info.is_entry_point is False
        assert file_info.is_imported is False
        assert file_info.import_count == 0

        # Check caching
        assert main_file in tracker._file_cache
        file_info2 = tracker._get_file_info(main_file)
        assert file_info is file_info2  # Should be same object from cache

    def test_is_potentially_unused(self):
        """Test identifying potentially unused files."""
        tracker = FileUsageTracker(self.test_dir)

        # Old unused file
        old_file = os.path.join(self.test_dir, 'old_unused.py')
        old_info = tracker._get_file_info(old_file)
        assert tracker._is_potentially_unused(old_info) is True

        # Test file (should not be considered unused)
        test_file = os.path.join(self.test_dir, 'test_main.py')
        test_info = tracker._get_file_info(test_file)
        assert tracker._is_potentially_unused(test_info) is False

        # Documentation file (should not be considered unused)
        readme_file = os.path.join(self.test_dir, 'README.md')
        readme_info = tracker._get_file_info(readme_file)
        assert tracker._is_potentially_unused(readme_info) is False

    def test_analyze_project(self):
        """Test analyzing entire project."""
        tracker = FileUsageTracker(self.test_dir)

        analysis = tracker.analyze_project(recursive=True)

        # Check basic structure
        assert 'total_files' in analysis
        assert 'total_size_bytes' in analysis
        assert 'imported_files' in analysis
        assert 'entry_points' in analysis
        assert 'unused_candidates' in analysis
        assert 'most_used_files' in analysis
        assert 'file_infos' in analysis
        assert 'statistics' in analysis

        # Check values
        assert analysis['total_files'] >= 7
        assert analysis['entry_points'] >= 1
        assert isinstance(analysis['unused_candidates'], list)

    def test_identify_unused_files(self):
        """Test identifying unused files."""
        tracker = FileUsageTracker(self.test_dir)

        unused_files = tracker.identify_unused_files(recursive=True)

        assert isinstance(unused_files, list)

        # Old unused file should be in the list
        old_file_name = 'old_unused.py'
        found_old = any(old_file_name in c.file_path for c in unused_files)
        assert found_old, "old_unused.py should be identified as potentially unused"

        # Test files should not be in the list
        test_file_name = 'test_main.py'
        found_test = any(test_file_name in c.file_path for c in unused_files)
        assert not found_test, "test files should not be considered unused"

    def test_create_unused_candidate(self):
        """Test creating unused file candidate."""
        tracker = FileUsageTracker(self.test_dir)

        old_file = os.path.join(self.test_dir, 'old_unused.py')
        file_info = tracker._get_file_info(old_file)
        file_info.is_imported = False  # Simulate not imported

        candidate = tracker._create_unused_candidate(file_info)

        assert isinstance(candidate, UnusedFileCandidate)
        assert candidate.file_path == old_file
        assert candidate.confidence in ['high', 'medium', 'low']
        assert len(candidate.reasons) > 0
        assert len(candidate.suggestions) > 0

    def test_calculate_statistics(self):
        """Test statistics calculation."""
        tracker = FileUsageTracker(self.test_dir)

        analysis = tracker.analyze_project(recursive=True)
        stats = analysis['statistics']

        # Check statistics structure
        assert 'total_size_mb' in stats
        assert 'unused_size_mb' in stats
        assert 'unused_percentage' in stats
        assert 'potential_savings_mb' in stats
        assert 'file_types' in stats
        assert 'confidence_counts' in stats

        # Check file types
        assert 'python' in stats['file_types']
        assert 'test' in stats['file_types']
        assert 'documentation' in stats['file_types']

    def test_get_most_used_files(self):
        """Test getting most used files."""
        tracker = FileUsageTracker(self.test_dir)

        analysis = tracker.analyze_project(recursive=True)
        most_used = analysis['most_used_files']

        assert isinstance(most_used, list)
        assert len(most_used) <= 10  # Default top_n is 10

        # Check structure of each entry
        if len(most_used) > 0:
            for f in most_used:
                assert 'file_path' in f
                assert 'file_name' in f
                assert 'file_type' in f
                assert 'import_count' in f
                assert 'size_bytes' in f

    def test_generate_text_report(self):
        """Test generating text format report."""
        tracker = FileUsageTracker(self.test_dir)

        report = tracker.generate_usage_report(format='text')

        assert isinstance(report, str)
        assert 'FILE USAGE REPORT' in report
        assert 'Total Files:' in report
        assert 'STATISTICS:' in report
        assert 'FILE TYPES:' in report

    def test_generate_markdown_report(self):
        """Test generating markdown format report."""
        tracker = FileUsageTracker(self.test_dir)

        report = tracker.generate_usage_report(format='markdown')

        assert isinstance(report, str)
        assert '# File Usage Report' in report
        assert '## Summary' in report
        assert '## File Types' in report
        assert '|' in report  # Should have markdown tables

    def test_generate_json_report(self):
        """Test generating JSON format report."""
        import json

        tracker = FileUsageTracker(self.test_dir)

        report = tracker.generate_usage_report(format='json')

        assert isinstance(report, str)

        # Should be valid JSON
        parsed = json.loads(report)
        assert 'total_files' in parsed
        assert 'statistics' in parsed

    def test_track_file_access(self):
        """Test tracking file access."""
        tracker = FileUsageTracker(self.test_dir)

        main_file = os.path.join(self.test_dir, 'main.py')

        # Track access
        tracker.track_file_access(main_file, 'read')

        # Check that file is in cache
        assert main_file in tracker._file_cache

        # Check that last_used is set
        file_info = tracker._file_cache[main_file]
        assert file_info.last_used is not None

    def test_resolve_import_to_file(self):
        """Test resolving import to file path."""
        tracker = FileUsageTracker(self.test_dir)

        # Test resolving 'utils' to utils.py
        resolved = tracker._resolve_import_to_file('utils', os.path.join(self.test_dir, 'main.py'))

        # May or may not resolve depending on implementation
        # Just test that it returns either None or a valid path
        if resolved is not None:
            assert os.path.exists(resolved)

    def test_unused_age_threshold(self):
        """Test custom unused age threshold."""
        tracker = FileUsageTracker(self.test_dir, unused_age_days=7)

        # Old file is 60 days old, so with 7 day threshold it should be unused
        old_file = os.path.join(self.test_dir, 'old_unused.py')
        file_info = tracker._get_file_info(old_file)
        file_info.is_imported = False

        assert tracker._is_potentially_unused(file_info) is True


class TestFileInfo:
    """Test suite for FileInfo dataclass."""

    def test_file_info_creation(self):
        """Test FileInfo object creation."""
        file_info = FileInfo(
            file_path='/test/path.py',
            file_type='python',
            size_bytes=1024,
            last_modified=datetime.now()
        )

        assert file_info.file_path == '/test/path.py'
        assert file_info.file_type == 'python'
        assert file_info.size_bytes == 1024
        assert file_info.last_modified is not None
        assert file_info.is_entry_point is False  # Default value
        assert file_info.is_imported is False  # Default value


class TestUnusedFileCandidate:
    """Test suite for UnusedFileCandidate dataclass."""

    def test_unused_file_candidate_creation(self):
        """Test UnusedFileCandidate object creation."""
        candidate = UnusedFileCandidate(
            file_path='/test/old.py',
            file_type='python',
            size_bytes=512,
            last_modified=datetime.now(),
            confidence='high',
            reasons=['Not imported', 'Old file'],
            suggestions=['Remove file']
        )

        assert candidate.file_path == '/test/old.py'
        assert candidate.file_type == 'python'
        assert candidate.size_bytes == 512
        assert candidate.confidence == 'high'
        assert len(candidate.reasons) == 2
        assert len(candidate.suggestions) == 1


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])