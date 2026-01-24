"""
Tests for Health Check Module - Task 4.6

Tests the health check system including:
- Database connectivity and integrity checks
- Git repository state validation
- Cache validity and size monitoring
- File system permissions and space checking
- LLM API connectivity testing
- Health report generation
- Auto-fix capabilities
"""

import os
import sys
import tempfile
import shutil
import unittest
from unittest.mock import patch, MagicMock
import sqlite3

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from v3.core.health_check import (
    HealthCheckManager,
    HealthStatus,
    HealthCheckResult,
    HealthReport,
    get_health_check_manager,
    run_health_check,
)


class TestHealthCheckManager(unittest.TestCase):
    """Test cases for HealthCheckManager class."""

    def setUp(self):
        """Set up test fixtures."""
        self.manager = HealthCheckManager()
        # Create temporary directory for tests
        self.test_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)

    def tearDown(self):
        """Clean up test fixtures."""
        os.chdir(self.original_cwd)
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_initialization(self):
        """Test HealthCheckManager initialization."""
        self.assertIsNotNone(self.manager)
        self.assertIsNotNone(self.manager.console)

    def test_check_databases_missing(self):
        """Test database check when databases don't exist."""
        results = self.manager._check_databases()
        self.assertGreater(len(results), 0)

        # Should have error for missing databases
        has_error = any(
            r.status == HealthStatus.ERROR and "database" in r.name.lower()
            for r in results
        )
        self.assertTrue(has_error)

    def test_check_databases_with_valid_db(self):
        """Test database check with a valid database."""
        # Create one of the expected databases
        db_path = "task.db"
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE tasks (id INTEGER PRIMARY KEY, title TEXT)")
        conn.execute("INSERT INTO tasks VALUES (1, 'Test task')")
        conn.commit()
        conn.close()

        results = self.manager._check_databases()

        # Should have OK status for valid database
        db_results = [r for r in results if "task_database" in r.name.lower()]
        self.assertGreater(len(db_results), 0)

        # At least one check should be OK (integrity or permissions)
        has_ok = any(r.status == HealthStatus.OK for r in db_results)
        self.assertTrue(has_ok)

        # Clean up
        os.remove(db_path)

    def test_check_git_no_repo(self):
        """Test git check when not in a git repository."""
        results = self.manager._check_git()
        self.assertGreater(len(results), 0)

        # Should have error for missing .git directory
        has_error = any(
            r.name == "git_repository" and r.status == HealthStatus.ERROR
            for r in results
        )
        self.assertTrue(has_error)

    def test_check_cache_missing(self):
        """Test cache check when cache directory doesn't exist."""
        results = self.manager._check_cache()
        self.assertGreater(len(results), 0)

        # Should have warning for missing cache directory
        has_warning = any(
            r.name == "cache_directory" and r.status == HealthStatus.WARNING
            for r in results
        )
        self.assertTrue(has_warning)

    def test_check_cache_with_cache(self):
        """Test cache check with existing cache."""
        # Create cache directory
        cache_dir = ".l4_cache"
        os.makedirs(cache_dir, exist_ok=True)

        # Create a test cache file
        with open(os.path.join(cache_dir, "test.cache"), "w") as f:
            f.write("test cache content")

        results = self.manager._check_cache()

        # Should have cache size check
        size_results = [r for r in results if "cache_size" in r.name]
        self.assertGreater(len(size_results), 0)

        # Clean up
        shutil.rmtree(cache_dir)

    def test_check_filesystem(self):
        """Test file system checks."""
        results = self.manager._check_filesystem()
        self.assertGreater(len(results), 0)

        # Should have disk space check
        has_disk_check = any("disk_space" in r.name for r in results)
        self.assertTrue(has_disk_check)

        # Should have filesystem write check
        has_write_check = any("filesystem_write" in r.name for r in results)
        self.assertTrue(has_write_check)

    def test_check_filesystem_required_files(self):
        """Test file system check with required files."""
        # Create required files
        with open("product.md", "w") as f:
            f.write("# Product\n")
        with open("technical.md", "w") as f:
            f.write("# Technical\n")

        results = self.manager._check_filesystem()

        # Should have OK status for required files
        product_results = [r for r in results if "product.md" in r.name.lower()]
        tech_results = [r for r in results if "technical.md" in r.name.lower()]

        self.assertGreater(len(product_results), 0)
        self.assertGreater(len(tech_results), 0)

        self.assertEqual(product_results[0].status, HealthStatus.OK)
        self.assertEqual(tech_results[0].status, HealthStatus.OK)

        # Clean up
        os.remove("product.md")
        os.remove("technical.md")

    def test_check_llm_api_no_keys(self):
        """Test LLM API check when no API keys are set."""
        # Ensure no API keys are set
        for key in ["GOOGLE_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"]:
            if key in os.environ:
                del os.environ[key]

        results = self.manager._check_llm_api()
        self.assertGreater(len(results), 0)

        # Should have error for no API keys
        has_error = any(
            r.name == "llm_api_keys" and r.status == HealthStatus.ERROR for r in results
        )
        self.assertTrue(has_error)

    def test_check_llm_api_with_keys(self):
        """Test LLM API check when API keys are set."""
        # Set a fake API key
        os.environ["GOOGLE_API_KEY"] = "test_key_12345"

        try:
            results = self.manager._check_llm_api()

            # Should have OK status for API keys
            api_key_results = [r for r in results if r.name == "llm_api_keys"]
            self.assertGreater(len(api_key_results), 0)

            # Should be OK or WARNING (depending on provider initialization)
            self.assertIn(
                api_key_results[0].status, [HealthStatus.OK, HealthStatus.WARNING]
            )
        finally:
            # Clean up
            if "GOOGLE_API_KEY" in os.environ:
                del os.environ["GOOGLE_API_KEY"]

    def test_calculate_summary(self):
        """Test summary calculation from check results."""
        checks = [
            HealthCheckResult(name="check1", status=HealthStatus.OK, message="OK"),
            HealthCheckResult(
                name="check2", status=HealthStatus.WARNING, message="Warning"
            ),
            HealthCheckResult(
                name="check3", status=HealthStatus.ERROR, message="Error"
            ),
            HealthCheckResult(name="check4", status=HealthStatus.OK, message="OK"),
        ]

        summary = self.manager._calculate_summary(checks)

        self.assertEqual(summary["total"], 4)
        self.assertEqual(summary["ok"], 2)
        self.assertEqual(summary["warning"], 1)
        self.assertEqual(summary["error"], 1)
        self.assertEqual(summary["critical"], 0)

    def test_determine_overall_status(self):
        """Test overall status determination."""
        # Test critical
        summary = {"critical": 1, "error": 0, "warning": 0, "ok": 0}
        status = self.manager._determine_overall_status(summary)
        self.assertEqual(status, HealthStatus.CRITICAL)

        # Test error
        summary = {"critical": 0, "error": 1, "warning": 0, "ok": 0}
        status = self.manager._determine_overall_status(summary)
        self.assertEqual(status, HealthStatus.ERROR)

        # Test warning
        summary = {"critical": 0, "error": 0, "warning": 1, "ok": 0}
        status = self.manager._determine_overall_status(summary)
        self.assertEqual(status, HealthStatus.WARNING)

        # Test OK
        summary = {"critical": 0, "error": 0, "warning": 0, "ok": 1}
        status = self.manager._determine_overall_status(summary)
        self.assertEqual(status, HealthStatus.OK)

    def test_generate_recommendations(self):
        """Test recommendation generation."""
        checks = [
            HealthCheckResult(
                name="check1",
                status=HealthStatus.ERROR,
                message="Error",
                recommendation="Fix this",
            ),
            HealthCheckResult(
                name="check2",
                status=HealthStatus.WARNING,
                message="Warning",
                recommendation="Fix that",
            ),
        ]

        recommendations = self.manager._generate_recommendations(checks)

        self.assertGreater(len(recommendations), 0)
        self.assertTrue(any("Fix this" in r for r in recommendations))
        self.assertTrue(any("Fix that" in r for r in recommendations))

    def test_run_all_checks(self):
        """Test running all health checks."""
        report = self.manager.run_all_checks()

        self.assertIsInstance(report, HealthReport)
        self.assertIsNotNone(report.overall_status)
        self.assertIsNotNone(report.summary)
        self.assertIsNotNone(report.timestamp)
        self.assertGreater(len(report.checks), 0)

    def test_auto_fix_issues(self):
        """Test auto-fix functionality."""
        # Create a scenario with fixable issue - initialize git repo (fixable)
        subprocess_result = MagicMock()
        subprocess_result.returncode = 0

        with patch("subprocess.run", return_value=subprocess_result):
            results = [
                HealthCheckResult(
                    name="git_repository",
                    status=HealthStatus.ERROR,
                    message="Not in a git repository",
                    recommendation="Initialize git repository: git init",
                    fixable=True,
                )
            ]

            report = HealthReport(
                overall_status=HealthStatus.ERROR,
                checks=results,
                summary={"total": 1, "error": 1},
                recommendations=[],
                timestamp="2026-01-22 00:00:00",
                duration_ms=100.0,
            )

            fixes_attempted, fix_results = self.manager.auto_fix_issues(report)

            self.assertEqual(fixes_attempted, 1)
            self.assertEqual(len(fix_results), 1)


class TestHealthCheckResult(unittest.TestCase):
    """Test cases for HealthCheckResult dataclass."""

    def test_health_check_result_creation(self):
        """Test creating a HealthCheckResult."""
        result = HealthCheckResult(
            name="test_check",
            status=HealthStatus.OK,
            message="Check passed",
            value=42.5,
            unit="MB",
            recommendation="None needed",
            details={"key": "value"},
            fixable=False,
        )

        self.assertEqual(result.name, "test_check")
        self.assertEqual(result.status, HealthStatus.OK)
        self.assertEqual(result.message, "Check passed")
        self.assertEqual(result.value, 42.5)
        self.assertEqual(result.unit, "MB")
        self.assertFalse(result.fixable)

    def test_to_dict(self):
        """Test converting HealthCheckResult to dictionary."""
        result = HealthCheckResult(
            name="test_check",
            status=HealthStatus.WARNING,
            message="Check warning",
            value=10.0,
            unit="percent",
        )

        result_dict = result.to_dict()

        self.assertEqual(result_dict["name"], "test_check")
        self.assertEqual(result_dict["status"], "warning")
        self.assertEqual(result_dict["message"], "Check warning")
        self.assertEqual(result_dict["value"], 10.0)
        self.assertEqual(result_dict["unit"], "percent")


class TestHealthReport(unittest.TestCase):
    """Test cases for HealthReport dataclass."""

    def test_health_report_creation(self):
        """Test creating a HealthReport."""
        checks = [
            HealthCheckResult(name="check1", status=HealthStatus.OK, message="OK")
        ]

        report = HealthReport(
            overall_status=HealthStatus.OK,
            checks=checks,
            summary={"total": 1, "ok": 1},
            recommendations=[],
            timestamp="2026-01-22 00:00:00",
            duration_ms=150.5,
        )

        self.assertEqual(report.overall_status, HealthStatus.OK)
        self.assertEqual(len(report.checks), 1)
        self.assertEqual(report.summary["total"], 1)
        self.assertEqual(report.duration_ms, 150.5)

    def test_to_dict(self):
        """Test converting HealthReport to dictionary."""
        checks = [
            HealthCheckResult(name="check1", status=HealthStatus.OK, message="OK")
        ]

        report = HealthReport(
            overall_status=HealthStatus.OK,
            checks=checks,
            summary={"total": 1, "ok": 1},
            recommendations=[],
            timestamp="2026-01-22 00:00:00",
            duration_ms=100.0,
        )

        report_dict = report.to_dict()

        self.assertEqual(report_dict["overall_status"], "ok")
        self.assertEqual(len(report_dict["checks"]), 1)
        self.assertEqual(report_dict["summary"]["total"], 1)
        self.assertEqual(report_dict["duration_ms"], 100.0)


class TestHealthStatus(unittest.TestCase):
    """Test cases for HealthStatus enum."""

    def test_health_status_values(self):
        """Test HealthStatus enum values."""
        self.assertEqual(HealthStatus.OK.value, "ok")
        self.assertEqual(HealthStatus.WARNING.value, "warning")
        self.assertEqual(HealthStatus.ERROR.value, "error")
        self.assertEqual(HealthStatus.CRITICAL.value, "critical")
        self.assertEqual(HealthStatus.INFO.value, "info")


class TestGlobalFunctions(unittest.TestCase):
    """Test cases for global health check functions."""

    def test_get_health_check_manager_singleton(self):
        """Test that get_health_check_manager returns singleton."""
        manager1 = get_health_check_manager()
        manager2 = get_health_check_manager()

        self.assertIs(manager1, manager2)

    @patch("v2.core.health_check.get_health_check_manager")
    def test_run_health_check(self, mock_get_manager):
        """Test run_health_check function."""
        # Mock the manager
        mock_manager = MagicMock()
        mock_report = HealthReport(
            overall_status=HealthStatus.OK,
            checks=[],
            summary={"total": 0},
            recommendations=[],
            timestamp="2026-01-22 00:00:00",
            duration_ms=100.0,
        )
        mock_manager.run_all_checks.return_value = mock_report
        mock_manager.print_report = MagicMock()
        mock_get_manager.return_value = mock_manager

        # Run health check
        report = run_health_check(verbose=False, auto_fix=False)

        # Verify manager methods were called
        mock_manager.run_all_checks.assert_called_once_with(verbose=False)
        mock_manager.print_report.assert_called_once()
        self.assertEqual(report, mock_report)


if __name__ == "__main__":
    unittest.main()
