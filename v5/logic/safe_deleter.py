"""
Safe Deletion Pipeline (V5)

This module implements safe deletion of dead code with backup,
testing, validation, and rollback capabilities.

Key Features:
- Create backup before any deletion (git commit or file copy)
- Run all tests before and after deletion
- Validate that deletion doesn't break imports
- Validate that deletion doesn't break tests
- Rollback automatically if tests fail
- Log all deletions with reason and outcome

Usage:
    from logic.safe_deleter import SafeDeleter
    
    deleter = SafeDeleter(project_root="/path/to/project")
    
    # Delete a function safely
    result = deleter.safe_delete_function(
        file_path="module.py",
        function_name="unused_func",
        reason="Never called, not in public API"
    )
    
    # Delete with dry-run mode
    result = deleter.safe_delete_function(
        file_path="module.py",
        function_name="unused_func",
        reason="Never called",
        dry_run=True
    )
"""

import os
import shutil
import subprocess
import tempfile
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

from v5.logic import GitGuard
from v5.core import get_logger


@dataclass
class DeletionResult:
    """Result of a safe deletion operation."""
    success: bool
    deleted_items: List[str]
    rollback_performed: bool
    backup_location: Optional[str]
    test_results_before: Dict
    test_results_after: Dict
    errors: List[str]
    warnings: List[str]
    dry_run: bool
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "deleted_items": self.deleted_items,
            "rollback_performed": self.rollback_performed,
            "backup_location": self.backup_location,
            "test_results_before": self.test_results_before,
            "test_results_after": self.test_results_after,
            "errors": self.errors,
            "warnings": self.warnings,
            "dry_run": self.dry_run
        }


@dataclass
class TestResult:
    """Result of test execution."""
    passed: int
    failed: int
    errors: int
    skipped: int
    total: int
    output: str
    exit_code: int
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "passed": self.passed,
            "failed": self.failed,
            "errors": self.errors,
            "skipped": self.skipped,
            "total": self.total,
            "exit_code": self.exit_code
        }
    
    @property
    def all_passed(self) -> bool:
        """Check if all tests passed."""
        return self.failed == 0 and self.errors == 0


class SafeDeleter:
    """
    Safe deletion pipeline for dead code removal.
    
    Implements the following workflow:
    1. Create backup (git commit or file copy)
    2. Run test suite to establish baseline
    3. Delete identified dead code
    4. Run test suite again
    5. If tests pass: Commit changes
    6. If tests fail: Rollback from backup
    """
    
    def __init__(
        self,
        project_root: str,
        backup_dir: str = ".l4_cache/backups",
        test_command: str = "pytest",
        git_enabled: bool = True,
        logger=None
    ):
        """
        Initialize SafeDeleter.
        
        Args:
            project_root: Root directory of project
            backup_dir: Directory for backups
            test_command: Command to run tests (e.g., "pytest", "python -m pytest")
            git_enabled: Whether to use git for backups
            logger: Logger instance (optional)
        """
        self.project_root = Path(project_root).resolve()
        self.backup_dir = self.project_root / backup_dir
        self.test_command = test_command
        self.git_enabled = git_enabled
        self.logger = logger or get_logger(__name__)
        self.git_guard = GitGuard()
        
        # Create backup directory
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Deletion log
        self.deletion_log_file = self.backup_dir / "deletion_log.csv"
        self._init_deletion_log()
    
    def safe_delete_function(
        self,
        file_path: str,
        function_name: str,
        reason: str,
        dry_run: bool = False,
        auto_commit: bool = True
    ) -> DeletionResult:
        """
        Safely delete a function from a file.
        
        Args:
            file_path: Path to file containing function
            function_name: Name of function to delete
            reason: Reason for deletion
            dry_run: If True, only preview deletion without executing
            auto_commit: If True, commit changes after successful deletion
        
        Returns:
            DeletionResult: Result of deletion operation
        """
        self.logger.info(f"Starting safe deletion of function: {function_name} in {file_path}")
        self.logger.info(f"Reason: {reason}")
        
        full_file_path = self.project_root / file_path
        
        try:
            # Check if file exists
            if not full_file_path.exists():
                return DeletionResult(
                    success=False,
                    deleted_items=[],
                    rollback_performed=False,
                    backup_location=None,
                    test_results_before={},
                    test_results_after={},
                    errors=[f"File not found: {file_path}"],
                    warnings=[],
                    dry_run=dry_run
                )
            
            # Step 1: Run tests before deletion (baseline)
            self.logger.info("Step 1: Running tests before deletion...")
            test_result_before = self._run_tests()
            
            if not test_result_before.all_passed:
                self.logger.warning(f"Tests before deletion: {test_result_before.failed} failed, {test_result_before.errors} errors")
            
            if dry_run:
                self.logger.info("DRY RUN: Would delete function")
                return DeletionResult(
                    success=True,
                    deleted_items=[f"{file_path}:{function_name}"],
                    rollback_performed=False,
                    backup_location=None,
                    test_results_before=test_result_before.to_dict(),
                    test_results_after={},
                    errors=[],
                    warnings=["Dry run - no actual deletion performed"],
                    dry_run=True
                )
            
            # Step 2: Create backup
            self.logger.info("Step 2: Creating backup...")
            backup_location = self._create_backup()
            
            # Step 3: Backup the specific file
            self._backup_file(full_file_path, backup_location)
            
            # Step 4: Delete the function
            self.logger.info("Step 3: Deleting function...")
            deleted = self._delete_function_from_file(full_file_path, function_name)
            
            if not deleted:
                return DeletionResult(
                    success=False,
                    deleted_items=[],
                    rollback_performed=False,
                    backup_location=backup_location,
                    test_results_before=test_result_before.to_dict(),
                    test_results_after={},
                    errors=[f"Failed to delete function {function_name} from {file_path}"],
                    warnings=[],
                    dry_run=dry_run
                )
            
            # Step 5: Validate imports
            self.logger.info("Step 4: Validating imports...")
            import_errors = self._validate_imports(full_file_path)
            
            if import_errors:
                self.logger.warning(f"Import validation errors: {import_errors}")
                # Rollback if import errors
                self.logger.info("Rolling back due to import errors...")
                self._rollback_from_backup(backup_location)
                return DeletionResult(
                    success=False,
                    deleted_items=[f"{file_path}:{function_name}"],
                    rollback_performed=True,
                    backup_location=backup_location,
                    test_results_before=test_result_before.to_dict(),
                    test_results_after={},
                    errors=import_errors,
                    warnings=[],
                    dry_run=dry_run
                )
            
            # Step 6: Run tests after deletion
            self.logger.info("Step 5: Running tests after deletion...")
            test_result_after = self._run_tests()
            
            # Step 7: Check if tests still pass
            if not test_result_after.all_passed:
                self.logger.warning(f"Tests after deletion: {test_result_after.failed} failed, {test_result_after.errors} errors")
                self.logger.info("Rolling back due to test failures...")
                self._rollback_from_backup(backup_location)
                
                # Log deletion
                self._log_deletion(
                    item_type="function",
                    item_name=f"{file_path}:{function_name}",
                    reason=reason,
                    success=False,
                    rollback=True
                )
                
                return DeletionResult(
                    success=False,
                    deleted_items=[f"{file_path}:{function_name}"],
                    rollback_performed=True,
                    backup_location=backup_location,
                    test_results_before=test_result_before.to_dict(),
                    test_results_after=test_result_after.to_dict(),
                    errors=["Tests failed after deletion"],
                    warnings=[],
                    dry_run=dry_run
                )
            
            # Step 8: Success - commit if auto_commit
            if auto_commit:
                self.logger.info("Step 6: Committing changes...")
                commit_result = self._commit_changes(
                    f"Delete unused function {function_name} in {file_path}\n\nReason: {reason}"
                )
                if not commit_result:
                    self.logger.warning("Failed to commit changes")
            
            # Log deletion
            self._log_deletion(
                item_type="function",
                item_name=f"{file_path}:{function_name}",
                reason=reason,
                success=True,
                rollback=False
            )
            
            return DeletionResult(
                success=True,
                deleted_items=[f"{file_path}:{function_name}"],
                rollback_performed=False,
                backup_location=backup_location,
                test_results_before=test_result_before.to_dict(),
                test_results_after=test_result_after.to_dict(),
                errors=[],
                warnings=[],
                dry_run=dry_run
            )
            
        except Exception as e:
            self.logger.error(f"Error during safe deletion: {e}", exc_info=True)
            return DeletionResult(
                success=False,
                deleted_items=[],
                rollback_performed=False,
                backup_location=None,
                test_results_before={},
                test_results_after={},
                errors=[str(e)],
                warnings=[],
                dry_run=dry_run
            )
    
    def safe_delete_class(
        self,
        file_path: str,
        class_name: str,
        reason: str,
        dry_run: bool = False,
        auto_commit: bool = True
    ) -> DeletionResult:
        """
        Safely delete a class from a file.
        
        Args:
            file_path: Path to file containing class
            class_name: Name of class to delete
            reason: Reason for deletion
            dry_run: If True, only preview deletion without executing
            auto_commit: If True, commit changes after successful deletion
        
        Returns:
            DeletionResult: Result of deletion operation
        """
        self.logger.info(f"Starting safe deletion of class: {class_name} in {file_path}")
        self.logger.info(f"Reason: {reason}")
        
        full_file_path = self.project_root / file_path
        
        try:
            # Check if file exists
            if not full_file_path.exists():
                return DeletionResult(
                    success=False,
                    deleted_items=[],
                    rollback_performed=False,
                    backup_location=None,
                    test_results_before={},
                    test_results_after={},
                    errors=[f"File not found: {file_path}"],
                    warnings=[],
                    dry_run=dry_run
                )
            
            # Step 1: Run tests before deletion (baseline)
            self.logger.info("Step 1: Running tests before deletion...")
            test_result_before = self._run_tests()
            
            if dry_run:
                self.logger.info("DRY RUN: Would delete class")
                return DeletionResult(
                    success=True,
                    deleted_items=[f"{file_path}:{class_name}"],
                    rollback_performed=False,
                    backup_location=None,
                    test_results_before=test_result_before.to_dict(),
                    test_results_after={},
                    errors=[],
                    warnings=["Dry run - no actual deletion performed"],
                    dry_run=True
                )
            
            # Step 2: Create backup
            self.logger.info("Step 2: Creating backup...")
            backup_location = self._create_backup()
            self._backup_file(full_file_path, backup_location)
            
            # Step 3: Delete the class
            self.logger.info("Step 3: Deleting class...")
            deleted = self._delete_class_from_file(full_file_path, class_name)
            
            if not deleted:
                return DeletionResult(
                    success=False,
                    deleted_items=[],
                    rollback_performed=False,
                    backup_location=backup_location,
                    test_results_before=test_result_before.to_dict(),
                    test_results_after={},
                    errors=[f"Failed to delete class {class_name} from {file_path}"],
                    warnings=[],
                    dry_run=dry_run
                )
            
            # Step 4: Validate imports
            self.logger.info("Step 4: Validating imports...")
            import_errors = self._validate_imports(full_file_path)
            
            if import_errors:
                self.logger.warning(f"Import validation errors: {import_errors}")
                self._rollback_from_backup(backup_location)
                return DeletionResult(
                    success=False,
                    deleted_items=[f"{file_path}:{class_name}"],
                    rollback_performed=True,
                    backup_location=backup_location,
                    test_results_before=test_result_before.to_dict(),
                    test_results_after={},
                    errors=import_errors,
                    warnings=[],
                    dry_run=dry_run
                )
            
            # Step 5: Run tests after deletion
            self.logger.info("Step 5: Running tests after deletion...")
            test_result_after = self._run_tests()
            
            if not test_result_after.all_passed:
                self.logger.warning(f"Tests after deletion: {test_result_after.failed} failed")
                self.logger.info("Rolling back due to test failures...")
                self._rollback_from_backup(backup_location)
                
                self._log_deletion(
                    item_type="class",
                    item_name=f"{file_path}:{class_name}",
                    reason=reason,
                    success=False,
                    rollback=True
                )
                
                return DeletionResult(
                    success=False,
                    deleted_items=[f"{file_path}:{class_name}"],
                    rollback_performed=True,
                    backup_location=backup_location,
                    test_results_before=test_result_before.to_dict(),
                    test_results_after=test_result_after.to_dict(),
                    errors=["Tests failed after deletion"],
                    warnings=[],
                    dry_run=dry_run
                )
            
            # Step 6: Commit if auto_commit
            if auto_commit:
                self.logger.info("Step 6: Committing changes...")
                self._commit_changes(
                    f"Delete unused class {class_name} in {file_path}\n\nReason: {reason}"
                )
            
            self._log_deletion(
                item_type="class",
                item_name=f"{file_path}:{class_name}",
                reason=reason,
                success=True,
                rollback=False
            )
            
            return DeletionResult(
                success=True,
                deleted_items=[f"{file_path}:{class_name}"],
                rollback_performed=False,
                backup_location=backup_location,
                test_results_before=test_result_before.to_dict(),
                test_results_after=test_result_after.to_dict(),
                errors=[],
                warnings=[],
                dry_run=dry_run
            )
            
        except Exception as e:
            self.logger.error(f"Error during safe deletion: {e}", exc_info=True)
            return DeletionResult(
                success=False,
                deleted_items=[],
                rollback_performed=False,
                backup_location=None,
                test_results_before={},
                test_results_after={},
                errors=[str(e)],
                warnings=[],
                dry_run=dry_run
            )
    
    def safe_delete_file(
        self,
        file_path: str,
        reason: str,
        dry_run: bool = False,
        auto_commit: bool = True
    ) -> DeletionResult:
        """
        Safely delete a file.
        
        Args:
            file_path: Path to file to delete
            reason: Reason for deletion
            dry_run: If True, only preview deletion without executing
            auto_commit: If True, commit changes after successful deletion
        
        Returns:
            DeletionResult: Result of deletion operation
        """
        self.logger.info(f"Starting safe deletion of file: {file_path}")
        self.logger.info(f"Reason: {reason}")
        
        full_file_path = self.project_root / file_path
        
        try:
            # Check if file exists
            if not full_file_path.exists():
                return DeletionResult(
                    success=False,
                    deleted_items=[],
                    rollback_performed=False,
                    backup_location=None,
                    test_results_before={},
                    test_results_after={},
                    errors=[f"File not found: {file_path}"],
                    warnings=[],
                    dry_run=dry_run
                )
            
            # Step 1: Run tests before deletion (baseline)
            self.logger.info("Step 1: Running tests before deletion...")
            test_result_before = self._run_tests()
            
            if dry_run:
                self.logger.info("DRY RUN: Would delete file")
                return DeletionResult(
                    success=True,
                    deleted_items=[file_path],
                    rollback_performed=False,
                    backup_location=None,
                    test_results_before=test_result_before.to_dict(),
                    test_results_after={},
                    errors=[],
                    warnings=["Dry run - no actual deletion performed"],
                    dry_run=True
                )
            
            # Step 2: Create backup
            self.logger.info("Step 2: Creating backup...")
            backup_location = self._create_backup()
            self._backup_file(full_file_path, backup_location)
            
            # Step 3: Delete the file
            self.logger.info("Step 3: Deleting file...")
            full_file_path.unlink()
            
            # Step 4: Validate imports (check for files importing this file)
            self.logger.info("Step 4: Validating imports...")
            import_errors = self._validate_file_removal(file_path)
            
            if import_errors:
                self.logger.warning(f"Import validation errors: {import_errors}")
                self._rollback_from_backup(backup_location)
                return DeletionResult(
                    success=False,
                    deleted_items=[file_path],
                    rollback_performed=True,
                    backup_location=backup_location,
                    test_results_before=test_result_before.to_dict(),
                    test_results_after={},
                    errors=import_errors,
                    warnings=[],
                    dry_run=dry_run
                )
            
            # Step 5: Run tests after deletion
            self.logger.info("Step 5: Running tests after deletion...")
            test_result_after = self._run_tests()
            
            if not test_result_after.all_passed:
                self.logger.warning(f"Tests after deletion: {test_result_after.failed} failed")
                self.logger.info("Rolling back due to test failures...")
                self._rollback_from_backup(backup_location)
                
                self._log_deletion(
                    item_type="file",
                    item_name=file_path,
                    reason=reason,
                    success=False,
                    rollback=True
                )
                
                return DeletionResult(
                    success=False,
                    deleted_items=[file_path],
                    rollback_performed=True,
                    backup_location=backup_location,
                    test_results_before=test_result_before.to_dict(),
                    test_results_after=test_result_after.to_dict(),
                    errors=["Tests failed after deletion"],
                    warnings=[],
                    dry_run=dry_run
                )
            
            # Step 6: Commit if auto_commit
            if auto_commit:
                self.logger.info("Step 6: Committing changes...")
                self._commit_changes(
                    f"Delete unused file {file_path}\n\nReason: {reason}"
                )
            
            self._log_deletion(
                item_type="file",
                item_name=file_path,
                reason=reason,
                success=True,
                rollback=False
            )
            
            return DeletionResult(
                success=True,
                deleted_items=[file_path],
                rollback_performed=False,
                backup_location=backup_location,
                test_results_before=test_result_before.to_dict(),
                test_results_after=test_result_after.to_dict(),
                errors=[],
                warnings=[],
                dry_run=dry_run
            )
            
        except Exception as e:
            self.logger.error(f"Error during safe deletion: {e}", exc_info=True)
            return DeletionResult(
                success=False,
                deleted_items=[],
                rollback_performed=False,
                backup_location=None,
                test_results_before={},
                test_results_after={},
                errors=[str(e)],
                warnings=[],
                dry_run=dry_run
            )
    
    def _create_backup(self) -> str:
        """
        Create a backup of the current state.
        
        Returns:
            str: Path to backup location
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"backup_{timestamp}"
        backup_path = self.backup_dir / backup_name
        backup_path.mkdir(exist_ok=True)
        
        if self.git_enabled:
            # Try to use git for backup
            try:
                result = self._git_status()
                if result and result.strip():
                    # There are changes, create a commit
                    commit_msg = f"Backup before safe deletion: {timestamp}"
                    self._git_add_all()
                    self._git_commit(commit_msg)
                    self.logger.info(f"Created git backup: {commit_msg}")
                    return f"git:{timestamp}"
            except Exception as e:
                self.logger.warning(f"Git backup failed: {e}, using file backup instead")
        
        # File-based backup
        return str(backup_path)
    
    def _backup_file(self, file_path: Path, backup_location: str):
        """
        Backup a specific file to the backup location.
        
        Args:
            file_path: Path to file to backup
            backup_location: Backup location path
        """
        if backup_location.startswith("git:"):
            # Git already backed up
            return
        
        backup_dir = Path(backup_location)
        rel_path = file_path.relative_to(self.project_root)
        backup_file = backup_dir / rel_path
        
        backup_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file_path, backup_file)
        
        self.logger.info(f"Backed up {file_path} to {backup_file}")
    
    def _rollback_from_backup(self, backup_location: str):
        """
        Rollback changes from backup.
        
        Args:
            backup_location: Backup location path
        """
        self.logger.info(f"Rolling back from backup: {backup_location}")
        
        if backup_location.startswith("git:"):
            # Git rollback
            try:
                timestamp = backup_location.split(":")[1]
                self._git_reset_hard()
                self.logger.info(f"Rolled back from git backup: {timestamp}")
            except Exception as e:
                self.logger.error(f"Git rollback failed: {e}")
        else:
            # File-based rollback
            backup_dir = Path(backup_location)
            if not backup_dir.exists():
                self.logger.error(f"Backup directory not found: {backup_location}")
                return
            
            # Restore all files from backup
            for backup_file in backup_dir.rglob("*"):
                if backup_file.is_file():
                    rel_path = backup_file.relative_to(backup_dir)
                    original_file = self.project_root / rel_path
                    original_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(backup_file, original_file)
                    self.logger.info(f"Restored {original_file} from {backup_file}")
    
    def _run_tests(self) -> TestResult:
        """
        Run the test suite.
        
        Returns:
            TestResult: Test execution results
        """
        try:
            self.logger.info(f"Running test command: {self.test_command}")
            
            result = subprocess.run(
                self.test_command.split(),
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            # Parse test results
            passed = 0
            failed = 0
            errors = 0
            skipped = 0
            
            output = result.stdout + result.stderr
            
            # Try to parse pytest output
            lines = output.split('\n')
            for line in lines:
                if ' passed' in line:
                    parts = line.split()
                    for part in parts:
                        if part.isdigit():
                            passed = int(part)
                if ' failed' in line:
                    parts = line.split()
                    for part in parts:
                        if part.isdigit():
                            failed = int(part)
                if ' error' in line:
                    parts = line.split()
                    for part in parts:
                        if part.isdigit():
                            errors = int(part)
                if ' skipped' in line:
                    parts = line.split()
                    for part in parts:
                        if part.isdigit():
                            skipped = int(part)
            
            total = passed + failed + errors + skipped
            
            test_result = TestResult(
                passed=passed,
                failed=failed,
                errors=errors,
                skipped=skipped,
                total=total,
                output=output,
                exit_code=result.returncode
            )
            
            self.logger.info(
                f"Test results: {passed} passed, {failed} failed, "
                f"{errors} errors, {skipped} skipped"
            )
            
            return test_result
            
        except subprocess.TimeoutExpired:
            self.logger.error("Test execution timed out")
            return TestResult(
                passed=0,
                failed=0,
                errors=1,
                skipped=0,
                total=0,
                output="Test execution timed out",
                exit_code=-1
            )
        except Exception as e:
            self.logger.error(f"Error running tests: {e}", exc_info=True)
            return TestResult(
                passed=0,
                failed=0,
                errors=1,
                skipped=0,
                total=0,
                output=str(e),
                exit_code=-1
            )
    
    def _validate_imports(self, file_path: Path) -> List[str]:
        """
        Validate that imports in a file resolve correctly.
        
        Args:
            file_path: Path to file to validate
        
        Returns:
            List[str]: List of import errors
        """
        errors = []
        
        try:
            # Try to compile the file
            with open(file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()
            
            compile(source_code, str(file_path), 'exec')
            
            # Try to import the module
            import importlib.util
            spec = importlib.util.spec_from_file_location("test_module", file_path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
        except SyntaxError as e:
            errors.append(f"Syntax error in {file_path}: {e}")
        except ImportError as e:
            errors.append(f"Import error in {file_path}: {e}")
        except Exception as e:
            errors.append(f"Error validating {file_path}: {e}")
        
        return errors
    
    def _validate_file_removal(self, file_path: str) -> List[str]:
        """
        Validate that removing a file won't break imports.
        
        Args:
            file_path: Path to file being removed
        
        Returns:
            List[str]: List of validation errors
        """
        errors = []
        
        # Convert file path to module name
        module_name = file_path.replace('/', '.').replace('\\', '.').replace('.py', '')
        
        # Find all Python files that might import this module
        for py_file in self.project_root.rglob("*.py"):
            if py_file == self.project_root / file_path:
                continue
            
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check if file imports the module
                if module_name in content or file_path in content:
                    # Check if it's a comment or docstring
                    if f'import {module_name}' in content or \
                       f'from {module_name}' in content:
                        errors.append(
                            f"{py_file.relative_to(self.project_root)} imports {module_name}"
                        )
            except Exception:
                continue
        
        return errors
    
    def _delete_function_from_file(self, file_path: Path, function_name: str) -> bool:
        """
        Delete a function from a file using AST.
        
        Args:
            file_path: Path to file
            function_name: Name of function to delete
        
        Returns:
            bool: True if deleted successfully
        """
        try:
            import ast
            
            with open(file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()
            
            tree = ast.parse(source_code, filename=str(file_path))
            
            # Find and remove the function
            new_body = []
            for node in tree.body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if node.name != function_name:
                        new_body.append(node)
                else:
                    new_body.append(node)
            
            # Check if function was found
            found = len(tree.body) > len(new_body)
            
            if not found:
                self.logger.warning(f"Function {function_name} not found in {file_path}")
                return False
            
            # Reconstruct the file
            tree.body = new_body
            new_code = ast.unparse(tree)
            
            # Write back to file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_code)
            
            self.logger.info(f"Deleted function {function_name} from {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error deleting function: {e}", exc_info=True)
            return False
    
    def _delete_class_from_file(self, file_path: Path, class_name: str) -> bool:
        """
        Delete a class from a file using AST.
        
        Args:
            file_path: Path to file
            class_name: Name of class to delete
        
        Returns:
            bool: True if deleted successfully
        """
        try:
            import ast
            
            with open(file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()
            
            tree = ast.parse(source_code, filename=str(file_path))
            
            # Find and remove the class
            new_body = []
            for node in tree.body:
                if isinstance(node, ast.ClassDef):
                    if node.name != class_name:
                        new_body.append(node)
                else:
                    new_body.append(node)
            
            # Check if class was found
            found = len(tree.body) > len(new_body)
            
            if not found:
                self.logger.warning(f"Class {class_name} not found in {file_path}")
                return False
            
            # Reconstruct the file
            tree.body = new_body
            new_code = ast.unparse(tree)
            
            # Write back to file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_code)
            
            self.logger.info(f"Deleted class {class_name} from {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error deleting class: {e}", exc_info=True)
            return False
    
    def _commit_changes(self, message: str) -> bool:
        """
        Commit changes to git.
        
        Args:
            message: Commit message
        
        Returns:
            bool: True if committed successfully
        """
        if not self.git_enabled:
            return False
        
        try:
            self._git_add_all()
            self._git_commit(message)
            self.logger.info(f"Committed changes: {message}")
            return True
        except Exception as e:
            self.logger.error(f"Error committing changes: {e}", exc_info=True)
            return False
    
    def _git_status(self) -> str:
        """Get git status."""
        result = subprocess.run(
            ['git', 'status', '--porcelain'],
            cwd=self.project_root,
            capture_output=True,
            text=True
        )
        return result.stdout
    
    def _git_add_all(self):
        """Stage all changes."""
        subprocess.run(
            ['git', 'add', '-A'],
            cwd=self.project_root,
            check=True
        )
    
    def _git_commit(self, message: str):
        """Commit staged changes."""
        subprocess.run(
            ['git', 'commit', '-m', message],
            cwd=self.project_root,
            check=True
        )
    
    def _git_reset_hard(self):
        """Reset to last commit."""
        subprocess.run(
            ['git', 'reset', '--hard', 'HEAD'],
            cwd=self.project_root,
            check=True
        )
    
    def _init_deletion_log(self):
        """Initialize deletion log file with headers."""
        if not self.deletion_log_file.exists():
            with open(self.deletion_log_file, 'w', encoding='utf-8') as f:
                f.write("timestamp,item_type,item_name,reason,success,rollback,backup_location\n")
    
    def _log_deletion(
        self,
        item_type: str,
        item_name: str,
        reason: str,
        success: bool,
        rollback: bool,
        backup_location: str = ""
    ):
        """
        Log a deletion operation.
        
        Args:
            item_type: Type of item (function, class, file)
            item_name: Name of item deleted
            reason: Reason for deletion
            success: Whether deletion was successful
            rollback: Whether rollback was performed
            backup_location: Backup location
        """
        timestamp = datetime.now().isoformat()
        
        with open(self.deletion_log_file, 'a', encoding='utf-8') as f:
            f.write(
                f"{timestamp},{item_type},{item_name},{reason},"
                f"{success},{rollback},{backup_location}\n"
            )
    
    def get_deletion_history(self) -> List[Dict]:
        """
        Get deletion history from log.
        
        Returns:
            List[Dict]: List of deletion records
        """
        if not self.deletion_log_file.exists():
            return []
        
        history = []
        with open(self.deletion_log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            # Skip header
            for line in lines[1:]:
                parts = line.strip().split(',')
                if len(parts) >= 6:
                    history.append({
                        "timestamp": parts[0],
                        "item_type": parts[1],
                        "item_name": parts[2],
                        "reason": parts[3],
                        "success": parts[4] == "True",
                        "rollback": parts[5] == "True",
                        "backup_location": parts[6] if len(parts) > 6 else ""
                    })
        
        return history