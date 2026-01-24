"""
Unit tests for SafeDeleter (V5)

Tests safe deletion pipeline including:
- Backup creation and restoration
- Test execution before and after deletion
- Import validation
- Rollback functionality
- Function, class, and file deletion
- Deletion logging
"""

import os
import unittest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime

from logic.safe_deleter import SafeDeleter, DeletionResult, TestResult


class TestDeletionResult(unittest.TestCase):
    """Test DeletionResult dataclass."""
    
    def test_deletion_result_creation(self):
        """Test creating DeletionResult."""
        result = DeletionResult(
            success=True,
            deleted_items=["test_file.py:test_func"],
            rollback_performed=False,
            backup_location="/backup/path",
            test_results_before={"passed": 10},
            test_results_after={"passed": 10},
            errors=[],
            warnings=[],
            dry_run=False
        )
        
        self.assertTrue(result.success)
        self.assertEqual(len(result.deleted_items), 1)
        self.assertFalse(result.rollback_performed)
        self.assertEqual(result.backup_location, "/backup/path")
    
    def test_deletion_result_to_dict(self):
        """Test converting DeletionResult to dict."""
        result = DeletionResult(
            success=True,
            deleted_items=[],
            rollback_performed=False,
            backup_location=None,
            test_results_before={},
            test_results_after={},
            errors=[],
            warnings=[],
            dry_run=False
        )
        
        result_dict = result.to_dict()
        
        self.assertIsInstance(result_dict, dict)
        self.assertTrue(result_dict['success'])
        self.assertFalse(result_dict['dry_run'])


class TestTestResult(unittest.TestCase):
    """Test TestResult dataclass."""
    
    def test_test_result_creation(self):
        """Test creating TestResult."""
        result = TestResult(
            passed=10,
            failed=2,
            errors=1,
            skipped=0,
            total=13,
            output="Test output",
            exit_code=0
        )
        
        self.assertEqual(result.passed, 10)
        self.assertEqual(result.failed, 2)
        self.assertEqual(result.total, 13)
    
    def test_all_passed_property(self):
        """Test all_passed property."""
        result_passing = TestResult(
            passed=10,
            failed=0,
            errors=0,
            skipped=2,
            total=12,
            output="",
            exit_code=0
        )
        self.assertTrue(result_passing.all_passed)
        
        result_failing = TestResult(
            passed=8,
            failed=2,
            errors=0,
            skipped=0,
            total=10,
            output="",
            exit_code=1
        )
        self.assertFalse(result_failing.all_passed)
        
        result_errors = TestResult(
            passed=10,
            failed=0,
            errors=1,
            skipped=0,
            total=11,
            output="",
            exit_code=1
        )
        self.assertFalse(result_errors.all_passed)
    
    def test_test_result_to_dict(self):
        """Test converting TestResult to dict."""
        result = TestResult(
            passed=10,
            failed=0,
            errors=0,
            skipped=0,
            total=10,
            output="",
            exit_code=0
        )
        
        result_dict = result.to_dict()
        
        self.assertIsInstance(result_dict, dict)
        self.assertEqual(result_dict['passed'], 10)
        self.assertEqual(result_dict['total'], 10)


class TestSafeDeleterInitialization(unittest.TestCase):
    """Test SafeDeleter initialization."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.backup_dir = os.path.join(self.temp_dir, "backups")
        self.project_root = self.temp_dir
        
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_initialization(self):
        """Test SafeDeleter initialization."""
        deleter = SafeDeleter(
            project_root=self.project_root,
            backup_dir=self.backup_dir,
            test_command="pytest",
            git_enabled=False
        )
        
        self.assertEqual(deleter.project_root, Path(self.project_root).resolve())
        self.assertEqual(deleter.test_command, "pytest")
        self.assertFalse(deleter.git_enabled)
        self.assertTrue(deleter.backup_dir.exists())
    
    def test_initialization_creates_backup_dir(self):
        """Test that initialization creates backup directory."""
        deleter = SafeDeleter(
            project_root=self.project_root,
            backup_dir=self.backup_dir,
            git_enabled=False
        )
        
        self.assertTrue(deleter.backup_dir.exists())
        self.assertTrue(deleter.deletion_log_file.exists())


class TestSafeDeleterBackup(unittest.TestCase):
    """Test backup and rollback functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.backup_dir = os.path.join(self.temp_dir, "backups")
        self.project_root = self.temp_dir
        self.deleter = SafeDeleter(
            project_root=self.project_root,
            backup_dir=self.backup_dir,
            git_enabled=False
        )
        
        # Create test file
        self.test_file = os.path.join(self.project_root, "test_file.py")
        with open(self.test_file, 'w') as f:
            f.write("def test_func():\n    pass\n")
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_create_backup(self):
        """Test creating backup."""
        backup_location = self.deleter._create_backup()
        
        self.assertIsNotNone(backup_location)
        self.assertTrue(os.path.exists(backup_location))
    
    def test_backup_file(self):
        """Test backing up a specific file."""
        backup_location = self.deleter._create_backup()
        self.deleter._backup_file(Path(self.test_file), backup_location)
        
        # Check that backup file exists
        backup_file = os.path.join(backup_location, "test_file.py")
        self.assertTrue(os.path.exists(backup_file))
    
    @patch('logic.safe_deleter.subprocess.run')
    def test_git_backup(self, mock_run):
        """Test git-based backup."""
        # Mock git status to return changes
        mock_run.return_value = Mock(stdout="M test_file.py")
        
        deleter = SafeDeleter(
            project_root=self.project_root,
            backup_dir=self.backup_dir,
            git_enabled=True
        )
        
        backup_location = deleter._create_backup()
        
        self.assertTrue(backup_location.startswith("git:"))
        # Verify git commands were called
        self.assertTrue(mock_run.called)
    
    def test_rollback_from_file_backup(self):
        """Test rollback from file backup."""
        # Create backup
        backup_location = self.deleter._create_backup()
        self.deleter._backup_file(Path(self.test_file), backup_location)
        
        # Modify file
        with open(self.test_file, 'w') as f:
            f.write("def modified_func():\n    pass\n")
        
        # Rollback
        self.deleter._rollback_from_backup(backup_location)
        
        # Verify file was restored
        with open(self.test_file, 'r') as f:
            content = f.read()
        
        self.assertIn("test_func", content)
    
    @patch('logic.safe_deleter.subprocess.run')
    def test_rollback_from_git_backup(self, mock_run):
        """Test rollback from git backup."""
        mock_run.return_value = Mock(stdout="", returncode=0)
        
        deleter = SafeDeleter(
            project_root=self.project_root,
            backup_dir=self.backup_dir,
            git_enabled=True
        )
        
        backup_location = "git:20240101_120000"
        deleter._rollback_from_backup(backup_location)
        
        # Verify git reset was called
        calls = mock_run.call_args_list
        reset_calls = [c for c in calls if 'reset' in str(c)]
        self.assertTrue(len(reset_calls) > 0)


class TestSafeDeleterTestExecution(unittest.TestCase):
    """Test test execution functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.backup_dir = os.path.join(self.temp_dir, "backups")
        self.project_root = self.temp_dir
        self.deleter = SafeDeleter(
            project_root=self.project_root,
            backup_dir=self.backup_dir,
            test_command="python -m pytest",
            git_enabled=False
        )
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('logic.safe_deleter.subprocess.run')
    def test_run_tests_success(self, mock_run):
        """Test running tests successfully."""
        # Mock pytest output
        mock_run.return_value = Mock(
            stdout="10 passed, 0 failed, 0 errors, 2 skipped",
            stderr="",
            returncode=0
        )
        
        result = self.deleter._run_tests()
        
        self.assertIsInstance(result, TestResult)
        self.assertEqual(result.passed, 10)
        self.assertEqual(result.failed, 0)
        self.assertEqual(result.errors, 0)
        self.assertEqual(result.skipped, 2)
        self.assertTrue(result.all_passed)
    
    @patch('logic.safe_deleter.subprocess.run')
    def test_run_tests_with_failures(self, mock_run):
        """Test running tests with failures."""
        mock_run.return_value = Mock(
            stdout="8 passed, 2 failed, 0 errors",
            stderr="",
            returncode=1
        )
        
        result = self.deleter._run_tests()
        
        self.assertEqual(result.passed, 8)
        self.assertEqual(result.failed, 2)
        self.assertFalse(result.all_passed)
    
    @patch('logic.safe_deleter.subprocess.run')
    def test_run_tests_timeout(self, mock_run):
        """Test test execution timeout."""
        from subprocess import TimeoutExpired
        mock_run.side_effect = TimeoutExpired("pytest", 300)
        
        result = self.deleter._run_tests()
        
        self.assertEqual(result.errors, 1)
        self.assertEqual(result.exit_code, -1)
        self.assertIn("timed out", result.output.lower())


class TestSafeDeleterImportValidation(unittest.TestCase):
    """Test import validation."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.backup_dir = os.path.join(self.temp_dir, "backups")
        self.project_root = self.temp_dir
        self.deleter = SafeDeleter(
            project_root=self.project_root,
            backup_dir=self.backup_dir,
            git_enabled=False
        )
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_validate_imports_valid_file(self):
        """Test validating imports for a valid file."""
        test_file = os.path.join(self.project_root, "valid_file.py")
        with open(test_file, 'w') as f:
            f.write("import os\n\ndef func():\n    pass\n")
        
        errors = self.deleter._validate_imports(Path(test_file))
        
        self.assertEqual(len(errors), 0)
    
    def test_validate_imports_syntax_error(self):
        """Test validating imports for a file with syntax errors."""
        test_file = os.path.join(self.project_root, "invalid_file.py")
        with open(test_file, 'w') as f:
            f.write("def incomplete func(\n")
        
        errors = self.deleter._validate_imports(Path(test_file))
        
        self.assertTrue(len(errors) > 0)
        self.assertTrue(any("syntax" in err.lower() for err in errors))
    
    def test_validate_file_removal_no_imports(self):
        """Test validating file removal when no files import it."""
        # Create test file
        test_file = os.path.join(self.project_root, "module.py")
        with open(test_file, 'w') as f:
            f.write("# Test module\n")
        
        errors = self.deleter._validate_file_removal("module.py")
        
        self.assertEqual(len(errors), 0)
    
    def test_validate_file_removal_with_imports(self):
        """Test validating file removal when files import it."""
        # Create module file
        module_file = os.path.join(self.project_root, "module.py")
        with open(module_file, 'w') as f:
            f.write("# Test module\n")
        
        # Create file that imports module
        importer_file = os.path.join(self.project_root, "importer.py")
        with open(importer_file, 'w') as f:
            f.write("import module\n")
        
        errors = self.deleter._validate_file_removal("module.py")
        
        self.assertTrue(len(errors) > 0)
        self.assertTrue(any("imports module" in err for err in errors))


class TestSafeDeleterFunctionDeletion(unittest.TestCase):
    """Test function deletion."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.backup_dir = os.path.join(self.temp_dir, "backups")
        self.project_root = self.temp_dir
        self.deleter = SafeDeleter(
            project_root=self.project_root,
            backup_dir=self.backup_dir,
            test_command="echo",  # Dummy command
            git_enabled=False
        )
        
        # Create test file with multiple functions
        self.test_file = os.path.join(self.project_root, "test_module.py")
        with open(self.test_file, 'w') as f:
            f.write("""
def func_to_delete():
    pass

def func_to_keep():
    pass
""")
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_delete_function_from_file(self):
        """Test deleting a function from a file."""
        deleted = self.deleter._delete_function_from_file(
            Path(self.test_file),
            "func_to_delete"
        )
        
        self.assertTrue(deleted)
        
        # Verify function was deleted
        with open(self.test_file, 'r') as f:
            content = f.read()
        
        self.assertNotIn("func_to_delete", content)
        self.assertIn("func_to_keep", content)
    
    def test_delete_function_not_found(self):
        """Test deleting a function that doesn't exist."""
        deleted = self.deleter._delete_function_from_file(
            Path(self.test_file),
            "nonexistent_func"
        )
        
        self.assertFalse(deleted)
    
    @patch.object(SafeDeleter, '_run_tests')
    @patch.object(SafeDeleter, '_create_backup')
    def test_safe_delete_function_dry_run(self, mock_backup, mock_tests):
        """Test safe function deletion in dry run mode."""
        mock_tests.return_value = TestResult(
            passed=10, failed=0, errors=0, skipped=0,
            total=10, output="", exit_code=0
        )
        mock_backup.return_value = "/backup/path"
        
        result = self.deleter.safe_delete_function(
            file_path="test_module.py",
            function_name="func_to_delete",
            reason="Test deletion",
            dry_run=True,
            auto_commit=False
        )
        
        self.assertTrue(result.success)
        self.assertTrue(result.dry_run)
        self.assertIn("Dry run", result.warnings[0])
        
        # Verify file was not modified
        with open(self.test_file, 'r') as f:
            content = f.read()
        self.assertIn("func_to_delete", content)
    
    @patch.object(SafeDeleter, '_run_tests')
    @patch.object(SafeDeleter, '_create_backup')
    @patch.object(SafeDeleter, '_rollback_from_backup')
    def test_safe_delete_function_with_test_failure(self, mock_rollback, mock_backup, mock_tests):
        """Test safe function deletion with test failure."""
        # Tests pass before deletion
        mock_tests.side_effect = [
            TestResult(passed=10, failed=0, errors=0, skipped=0, total=10, output="", exit_code=0),
            TestResult(passed=8, failed=2, errors=0, skipped=0, total=10, output="", exit_code=1)
        ]
        mock_backup.return_value = "/backup/path"
        
        result = self.deleter.safe_delete_function(
            file_path="test_module.py",
            function_name="func_to_delete",
            reason="Test deletion",
            auto_commit=False
        )
        
        self.assertFalse(result.success)
        self.assertTrue(result.rollback_performed)
        self.assertTrue(mock_rollback.called)
        
        # Verify rollback was logged
        history = self.deleter.get_deletion_history()
        self.assertTrue(len(history) > 0)
        self.assertFalse(history[-1]['success'])


class TestSafeDeleterClassDeletion(unittest.TestCase):
    """Test class deletion."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.backup_dir = os.path.join(self.temp_dir, "backups")
        self.project_root = self.temp_dir
        self.deleter = SafeDeleter(
            project_root=self.project_root,
            backup_dir=self.backup_dir,
            test_command="echo",
            git_enabled=False
        )
        
        # Create test file with multiple classes
        self.test_file = os.path.join(self.project_root, "test_module.py")
        with open(self.test_file, 'w') as f:
            f.write("""
class ClassToDelete:
    pass

class ClassToKeep:
    pass
""")
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_delete_class_from_file(self):
        """Test deleting a class from a file."""
        deleted = self.deleter._delete_class_from_file(
            Path(self.test_file),
            "ClassToDelete"
        )
        
        self.assertTrue(deleted)
        
        # Verify class was deleted
        with open(self.test_file, 'r') as f:
            content = f.read()
        
        self.assertNotIn("ClassToDelete", content)
        self.assertIn("ClassToKeep", content)
    
    def test_delete_class_not_found(self):
        """Test deleting a class that doesn't exist."""
        deleted = self.deleter._delete_class_from_file(
            Path(self.test_file),
            "NonexistentClass"
        )
        
        self.assertFalse(deleted)
    
    @patch.object(SafeDeleter, '_run_tests')
    @patch.object(SafeDeleter, '_create_backup')
    def test_safe_delete_class_dry_run(self, mock_backup, mock_tests):
        """Test safe class deletion in dry run mode."""
        mock_tests.return_value = TestResult(
            passed=10, failed=0, errors=0, skipped=0,
            total=10, output="", exit_code=0
        )
        mock_backup.return_value = "/backup/path"
        
        result = self.deleter.safe_delete_class(
            file_path="test_module.py",
            class_name="ClassToDelete",
            reason="Test deletion",
            dry_run=True,
            auto_commit=False
        )
        
        self.assertTrue(result.success)
        self.assertTrue(result.dry_run)


class TestSafeDeleterFileDeletion(unittest.TestCase):
    """Test file deletion."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.backup_dir = os.path.join(self.temp_dir, "backups")
        self.project_root = self.temp_dir
        self.deleter = SafeDeleter(
            project_root=self.project_root,
            backup_dir=self.backup_dir,
            test_command="echo",
            git_enabled=False
        )
        
        # Create test file
        self.test_file = os.path.join(self.project_root, "test_file.py")
        with open(self.test_file, 'w') as f:
            f.write("# Test file\n")
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch.object(SafeDeleter, '_run_tests')
    @patch.object(SafeDeleter, '_create_backup')
    @patch.object(SafeDeleter, '_validate_file_removal')
    def test_safe_delete_file_success(self, mock_validate, mock_backup, mock_tests):
        """Test successful file deletion."""
        mock_tests.return_value = TestResult(
            passed=10, failed=0, errors=0, skipped=0,
            total=10, output="", exit_code=0
        )
        mock_backup.return_value = "/backup/path"
        mock_validate.return_value = []
        
        result = self.deleter.safe_delete_file(
            file_path="test_file.py",
            reason="Test deletion",
            auto_commit=False
        )
        
        self.assertTrue(result.success)
        self.assertFalse(os.path.exists(self.test_file))
    
    @patch.object(SafeDeleter, '_run_tests')
    @patch.object(SafeDeleter, '_create_backup')
    def test_safe_delete_file_not_found(self, mock_backup, mock_tests):
        """Test deleting a file that doesn't exist."""
        mock_tests.return_value = TestResult(
            passed=10, failed=0, errors=0, skipped=0,
            total=10, output="", exit_code=0
        )
        
        result = self.deleter.safe_delete_file(
            file_path="nonexistent.py",
            reason="Test",
            auto_commit=False
        )
        
        self.assertFalse(result.success)
        self.assertTrue(any("not found" in err for err in result.errors))


class TestSafeDeleterDeletionLogging(unittest.TestCase):
    """Test deletion logging."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.backup_dir = os.path.join(self.temp_dir, "backups")
        self.project_root = self.temp_dir
        self.deleter = SafeDeleter(
            project_root=self.project_root,
            backup_dir=self.backup_dir,
            git_enabled=False
        )
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_log_deletion(self):
        """Test logging a deletion."""
        self.deleter._log_deletion(
            item_type="function",
            item_name="test.py:func",
            reason="Test reason",
            success=True,
            rollback=False,
            backup_location="/backup/path"
        )
        
        history = self.deleter.get_deletion_history()
        
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]['item_type'], 'function')
        self.assertEqual(history[0]['item_name'], 'test.py:func')
        self.assertEqual(history[0]['reason'], 'Test reason')
        self.assertTrue(history[0]['success'])
        self.assertFalse(history[0]['rollback'])
    
    def test_get_deletion_history_empty(self):
        """Test getting deletion history when empty."""
        history = self.deleter.get_deletion_history()
        
        self.assertEqual(len(history), 0)
    
    def test_get_deletion_history_multiple(self):
        """Test getting deletion history with multiple entries."""
        # Log multiple deletions
        for i in range(3):
            self.deleter._log_deletion(
                item_type="function",
                item_name=f"test.py:func{i}",
                reason=f"Reason {i}",
                success=(i < 2),
                rollback=(i == 1),
                backup_location=f"/backup/{i}"
            )
        
        history = self.deleter.get_deletion_history()
        
        self.assertEqual(len(history), 3)
        self.assertEqual(history[0]['item_name'], 'test.py:func0')
        self.assertEqual(history[2]['item_name'], 'test.py:func2')
        self.assertFalse(history[1]['success'])
        self.assertTrue(history[1]['rollback'])


class TestSafeDeleterGitOperations(unittest.TestCase):
    """Test git operations."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.backup_dir = os.path.join(self.temp_dir, "backups")
        self.project_root = self.temp_dir
        self.deleter = SafeDeleter(
            project_root=self.project_root,
            backup_dir=self.backup_dir,
            git_enabled=True
        )
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('logic.safe_deleter.subprocess.run')
    def test_git_status(self, mock_run):
        """Test getting git status."""
        mock_run.return_value = Mock(stdout="M test.py\nA new.py")
        
        status = self.deleter._git_status()
        
        self.assertEqual(status, "M test.py\nA new.py")
        mock_run.assert_called_with(
            ['git', 'status', '--porcelain'],
            cwd=self.project_root,
            capture_output=True,
            text=True
        )
    
    @patch('logic.safe_deleter.subprocess.run')
    def test_git_add_all(self, mock_run):
        """Test staging all changes."""
        self.deleter._git_add_all()
        
        mock_run.assert_called_with(
            ['git', 'add', '-A'],
            cwd=self.project_root,
            check=True
        )
    
    @patch('logic.safe_deleter.subprocess.run')
    def test_git_commit(self, mock_run):
        """Test committing changes."""
        self.deleter._git_commit("Test commit message")
        
        mock_run.assert_called_with(
            ['git', 'commit', '-m', 'Test commit message'],
            cwd=self.project_root,
            check=True
        )
    
    @patch('logic.safe_deleter.subprocess.run')
    def test_git_reset_hard(self, mock_run):
        """Test hard reset."""
        self.deleter._git_reset_hard()
        
        mock_run.assert_called_with(
            ['git', 'reset', '--hard', 'HEAD'],
            cwd=self.project_root,
            check=True
        )


if __name__ == '__main__':
    unittest.main()