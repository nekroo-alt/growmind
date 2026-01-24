"""
Standalone test for File Usage Tracker Module (V5)
Tests the module independently without importing through the package structure.
"""

import os
import sys
import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path

# Add v4 to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'v4'))

# Import modules directly
from logic.file_usage_tracker import FileUsageTracker, FileInfo, UnusedFileCandidate


def test_file_usage_tracker():
    """Test FileUsageTracker basic functionality."""
    print("=" * 60)
    print("Testing File Usage Tracker")
    print("=" * 60)
    
    # Create temporary directory for test project
    test_dir = tempfile.mkdtemp()
    print(f"\nTest directory: {test_dir}")
    
    try:
        # Create test file structure
        print("\nCreating test files...")
        
        # Create a Python file with imports
        main_file = os.path.join(test_dir, 'main.py')
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
        print(f"  Created: main.py")
        
        # Create a utility file
        utils_file = os.path.join(test_dir, 'utils.py')
        with open(utils_file, 'w') as f:
            f.write("""
def utility_function():
    return "utility"
""")
        print(f"  Created: utils.py")
        
        # Create a helper file
        helpers_dir = os.path.join(test_dir, 'helpers')
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
        print(f"  Created: helpers/__init__.py and helpers/helper_module.py")
        
        # Create an old, unused file
        old_file = os.path.join(test_dir, 'old_unused.py')
        with open(old_file, 'w') as f:
            f.write("""
def old_function():
    return "old"
""")
        # Set modification time to 60 days ago
        old_time = datetime.now() - timedelta(days=60)
        old_timestamp = old_time.timestamp()
        os.utime(old_file, (old_timestamp, old_timestamp))
        print(f"  Created: old_unused.py (60 days old)")
        
        # Create a test file
        test_file = os.path.join(test_dir, 'test_main.py')
        with open(test_file, 'w') as f:
            f.write("""
import unittest
from main import main

class TestMain(unittest.TestCase):
    def test_main(self):
        self.assertIsNotNone(main)
""")
        print(f"  Created: test_main.py")
        
        # Create documentation
        readme_file = os.path.join(test_dir, 'README.md')
        with open(readme_file, 'w') as f:
            f.write("""
# Test Project

This is a test project.
""")
        print(f"  Created: README.md")
        
        # Create configuration
        config_file = os.path.join(test_dir, 'config.py')
        with open(config_file, 'w') as f:
            f.write("""
DEBUG = True
VERSION = "1.0.0"
""")
        print(f"  Created: config.py")
        
        # Test 1: Initialization
        print("\n" + "-" * 60)
        print("Test 1: Initialization")
        print("-" * 60)
        tracker = FileUsageTracker(test_dir)
        assert tracker.project_root == test_dir
        assert tracker.unused_age_threshold == timedelta(days=30)
        print("  ✓ Initialization successful")
        
        # Test 2: Find Python files
        print("\n" + "-" * 60)
        print("Test 2: Find Python Files")
        print("-" * 60)
        python_files = tracker._find_python_files(test_dir, recursive=True)
        print(f"  Found {len(python_files)} Python files")
        assert len(python_files) >= 5
        assert any('main.py' in f for f in python_files)
        assert any('utils.py' in f for f in python_files)
        print("  ✓ Python file detection successful")
        
        # Test 3: Find entry points
        print("\n" + "-" * 60)
        print("Test 3: Find Entry Points")
        print("-" * 60)
        entry_points = tracker._find_entry_points(test_dir, recursive=True)
        print(f"  Found {len(entry_points)} entry points")
        assert main_file in entry_points
        print("  ✓ Entry point detection successful")
        
        # Test 4: Get file info
        print("\n" + "-" * 60)
        print("Test 4: Get File Info")
        print("-" * 60)
        file_info = tracker._get_file_info(main_file)
        assert file_info.file_path == main_file
        assert file_info.file_type == 'python'
        assert file_info.size_bytes > 0
        print(f"  File: {file_info.file_name}")
        print(f"  Type: {file_info.file_type}")
        print(f"  Size: {file_info.size_bytes} bytes")
        print("  ✓ File info retrieval successful")
        
        # Test 5: Identify unused files
        print("\n" + "-" * 60)
        print("Test 5: Identify Unused Files")
        print("-" * 60)
        unused_files = tracker.identify_unused_files(recursive=True)
        print(f"  Found {len(unused_files)} potentially unused files:")
        for candidate in unused_files:
            print(f"    - {os.path.basename(candidate.file_path)} ({candidate.confidence} confidence)")
        
        # Check if old unused file is detected
        old_file_name = 'old_unused.py'
        found_old = any(old_file_name in c.file_path for c in unused_files)
        assert found_old, f"{old_file_name} should be identified as potentially unused"
        print("  ✓ Unused file detection successful")
        
        # Test 6: Analyze project
        print("\n" + "-" * 60)
        print("Test 6: Analyze Project")
        print("-" * 60)
        analysis = tracker.analyze_project(recursive=True)
        print(f"  Total files: {analysis['total_files']}")
        print(f"  Total size: {analysis['total_size_bytes']} bytes")
        print(f"  Imported files: {len(analysis['imported_files'])}")
        print(f"  Entry points: {len(analysis['entry_points'])}")
        print(f"  Unused candidates: {len(analysis['unused_candidates'])}")
        assert analysis['total_files'] >= 7
        print("  ✓ Project analysis successful")
        
        # Test 7: Generate reports
        print("\n" + "-" * 60)
        print("Test 7: Generate Reports")
        print("-" * 60)
        
        # Text report
        text_report = tracker.generate_usage_report(format='text')
        assert 'FILE USAGE REPORT' in text_report
        print("  ✓ Text report generated")
        
        # Markdown report
        markdown_report = tracker.generate_usage_report(format='markdown')
        assert '# File Usage Report' in markdown_report
        print("  ✓ Markdown report generated")
        
        # JSON report
        json_report = tracker.generate_usage_report(format='json')
        assert 'total_files' in json_report
        print("  ✓ JSON report generated")
        
        # Test 8: Statistics
        print("\n" + "-" * 60)
        print("Test 8: Statistics")
        print("-" * 60)
        stats = analysis['statistics']
        print(f"  Total size: {stats['total_size_mb']:.2f} MB")
        print(f"  Unused size: {stats['unused_size_mb']:.2f} MB")
        print(f"  Unused percentage: {stats['unused_percentage']:.1f}%")
        print(f"  File types: {stats['file_types']}")
        print("  ✓ Statistics calculation successful")
        
        print("\n" + "=" * 60)
        print("All tests passed! ✓")
        print("=" * 60)
        
    finally:
        # Clean up
        shutil.rmtree(test_dir)
        print(f"\nCleaned up test directory: {test_dir}")


if __name__ == '__main__':
    test_file_usage_tracker()