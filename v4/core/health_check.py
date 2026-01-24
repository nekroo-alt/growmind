"""
Health Checks and Self-Diagnostics - Task 4.6

This module implements comprehensive health checks for system components.
It monitors database connectivity, git state, cache validity, file system, and LLM API.

Features:
- Database connectivity and integrity checks
- Git repository state validation
- Cache validity and size monitoring
- File system permissions and space checking
- LLM API connectivity testing
- Health report generation with recommendations
- Auto-fix capabilities for minor issues
- Health check categories: critical, warning, info

Dependencies:
- Task 3.2: CheckpointManager for state validation
- Task 4.1: Error handling for error classification
"""

import os
import sys
import sqlite3
import subprocess
import shutil
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import time
from pathlib import Path

# Try to import optional dependencies
try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

# Import L4D modules
from v3.data import db_manager
from v3.data import telemetry_manager
from v3.data import cache_manager
from v3.data import checkpoint_manager


class HealthStatus(Enum):
    """Health check status levels."""

    OK = "ok"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    INFO = "info"


@dataclass
class HealthCheckResult:
    """
    Result of a single health check.

    Attributes:
        name: Name of the check
        status: Health status (ok, warning, error, critical, info)
        message: Descriptive message
        value: Optional measured value
        unit: Optional unit of measurement
        recommendation: Optional recommendation for fixing issues
        details: Additional details dictionary
        fixable: Whether this issue can be auto-fixed
        fix_function: Optional function to auto-fix the issue
    """

    name: str
    status: HealthStatus
    message: str
    value: Optional[float] = None
    unit: Optional[str] = None
    recommendation: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    fixable: bool = False
    fix_function: Optional[callable] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "value": self.value,
            "unit": self.unit,
            "recommendation": self.recommendation,
            "details": self.details,
            "fixable": self.fixable,
        }


@dataclass
class HealthReport:
    """
    Complete health check report.

    Attributes:
        overall_status: Overall health status
        checks: List of all health check results
        summary: Summary statistics
        recommendations: List of prioritized recommendations
        timestamp: When the report was generated
        duration_ms: Time taken to run checks in milliseconds
    """

    overall_status: HealthStatus
    checks: List[HealthCheckResult]
    summary: Dict[str, int]
    recommendations: List[str]
    timestamp: str
    duration_ms: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "overall_status": self.overall_status.value,
            "checks": [check.to_dict() for check in self.checks],
            "summary": self.summary,
            "recommendations": self.recommendations,
            "timestamp": self.timestamp,
            "duration_ms": self.duration_ms,
        }


class HealthCheckManager:
    """
    Manager for running health checks on system components.

    Provides methods to check:
    - Database connectivity and integrity
    - Git repository state
    - Cache validity and size
    - File system permissions and space
    - LLM API connectivity

    Can generate health reports and auto-fix minor issues.
    """

    # Thresholds for warnings and errors
    WARNING_DISK_SPACE_MB = 500  # Warn if less than 500MB free
    CRITICAL_DISK_SPACE_MB = 100  # Critical if less than 100MB free
    WARNING_CACHE_SIZE_MB = 80  # Warn if cache > 80MB
    CRITICAL_CACHE_SIZE_MB = 100  # Critical if cache > 100MB

    def __init__(self):
        """Initialize the health check manager."""
        self.console = Console() if RICH_AVAILABLE else None
        self._db_paths = {
            "task": db_manager.TASK_DB_PATH,
            "activity": db_manager.ACTIVITY_DB_PATH,
            "snapshots": db_manager.SNAPSHOTS_DB_PATH,
            "telemetry": telemetry_manager.TELEMETRY_DB_PATH,
        }

    def run_all_checks(self, verbose: bool = False) -> HealthReport:
        """
        Run all health checks and generate a report.

        Args:
            verbose: If True, include detailed output

        Returns:
            HealthReport with all check results
        """
        start_time = time.time()
        checks = []

        # Run all health checks
        checks.extend(self._check_databases())
        checks.extend(self._check_git())
        checks.extend(self._check_cache())
        checks.extend(self._check_filesystem())
        checks.extend(self._check_llm_api())
        checks.extend(self._check_system_resources())

        # Calculate summary
        summary = self._calculate_summary(checks)

        # Determine overall status
        overall_status = self._determine_overall_status(summary)

        # Generate recommendations
        recommendations = self._generate_recommendations(checks)

        duration_ms = (time.time() - start_time) * 1000
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

        report = HealthReport(
            overall_status=overall_status,
            checks=checks,
            summary=summary,
            recommendations=recommendations,
            timestamp=timestamp,
            duration_ms=duration_ms,
        )

        return report

    def _check_databases(self) -> List[HealthCheckResult]:
        """Check all databases for connectivity and integrity."""
        results = []

        for db_name, db_path in self._db_paths.items():
            # Check if database file exists
            if not os.path.exists(db_path):
                results.append(
                    HealthCheckResult(
                        name=f"{db_name}_database_exists",
                        status=HealthStatus.ERROR,
                        message=f"Database file not found: {db_path}",
                        recommendation=f"Initialize the database using v2/init_db.py",
                        details={"path": db_path},
                    )
                )
                continue

            # Check database file size
            file_size = os.path.getsize(db_path) / (1024 * 1024)  # MB
            results.append(
                HealthCheckResult(
                    name=f"{db_name}_database_size",
                    status=HealthStatus.INFO,
                    message=f"{db_name.capitalize()} database size",
                    value=file_size,
                    unit="MB",
                    details={"path": db_path},
                )
            )

            # Check database connectivity and integrity
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()

                # Check if we can query the database
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()

                # Check database integrity
                cursor.execute("PRAGMA integrity_check")
                integrity_result = cursor.fetchone()

                conn.close()

                if integrity_result and integrity_result[0] == "ok":
                    results.append(
                        HealthCheckResult(
                            name=f"{db_name}_database_integrity",
                            status=HealthStatus.OK,
                            message=f"{db_name.capitalize()} database integrity check passed",
                            details={
                                "path": db_path,
                                "tables": len(tables),
                                "table_names": [t[0] for t in tables],
                            },
                        )
                    )
                else:
                    results.append(
                        HealthCheckResult(
                            name=f"{db_name}_database_integrity",
                            status=HealthStatus.ERROR,
                            message=f"{db_name.capitalize()} database integrity check failed",
                            recommendation="Database may be corrupted. Consider restoring from a checkpoint.",
                            details={
                                "path": db_path,
                                "integrity_result": integrity_result,
                            },
                            fixable=True,
                        )
                    )

            except sqlite3.Error as e:
                results.append(
                    HealthCheckResult(
                        name=f"{db_name}_database_connectivity",
                        status=HealthStatus.ERROR,
                        message=f"Cannot connect to {db_name} database: {str(e)}",
                        recommendation="Check file permissions and ensure database is not locked",
                        details={"path": db_path, "error": str(e)},
                    )
                )

            # Check database file permissions
            if os.path.exists(db_path):
                readable = os.access(db_path, os.R_OK)
                writable = os.access(db_path, os.W_OK)

                if readable and writable:
                    results.append(
                        HealthCheckResult(
                            name=f"{db_name}_database_permissions",
                            status=HealthStatus.OK,
                            message=f"{db_name.capitalize()} database permissions OK",
                            details={
                                "path": db_path,
                                "readable": readable,
                                "writable": writable,
                            },
                        )
                    )
                else:
                    results.append(
                        HealthCheckResult(
                            name=f"{db_name}_database_permissions",
                            status=HealthStatus.ERROR,
                            message=f"{db_name.capitalize()} database permission issue",
                            recommendation=f"Fix file permissions: chmod 644 {db_path}",
                            details={
                                "path": db_path,
                                "readable": readable,
                                "writable": writable,
                            },
                            fixable=True,
                        )
                    )

        return results

    def _check_git(self) -> List[HealthCheckResult]:
        """Check git repository state."""
        results = []

        # Check if in a git repository
        try:
            # Check if .git directory exists
            if not os.path.exists(".git"):
                results.append(
                    HealthCheckResult(
                        name="git_repository",
                        status=HealthStatus.ERROR,
                        message="Not in a git repository",
                        recommendation="Initialize git repository: git init",
                        fixable=True,
                    )
                )
                return results

            # Get git status
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode == 0:
                status_lines = (
                    result.stdout.strip().split("\n") if result.stdout.strip() else []
                )

                if not status_lines:
                    results.append(
                        HealthCheckResult(
                            name="git_workspace",
                            status=HealthStatus.OK,
                            message="Git workspace is clean",
                        )
                    )
                else:
                    modified_count = len(
                        [l for l in status_lines if l and not l.startswith("??")]
                    )
                    untracked_count = len(
                        [l for l in status_lines if l.startswith("??")]
                    )

                    if modified_count > 0:
                        results.append(
                            HealthCheckResult(
                                name="git_workspace",
                                status=HealthStatus.WARNING,
                                message=f"Git workspace has {modified_count} modified file(s)",
                                recommendation="Review changes with: git diff",
                                details={
                                    "modified": modified_count,
                                    "untracked": untracked_count,
                                },
                            )
                        )
                    else:
                        results.append(
                            HealthCheckResult(
                                name="git_workspace",
                                status=HealthStatus.INFO,
                                message=f"Git workspace has {untracked_count} untracked file(s)",
                                details={"untracked": untracked_count},
                            )
                        )

            # Get current branch
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode == 0:
                branch = result.stdout.strip()
                results.append(
                    HealthCheckResult(
                        name="git_branch",
                        status=HealthStatus.INFO,
                        message=f"Current branch: {branch}",
                        details={"branch": branch},
                    )
                )

            # Get latest commit
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode == 0:
                commit_hash = result.stdout.strip()[:8]
                results.append(
                    HealthCheckResult(
                        name="git_commit",
                        status=HealthStatus.INFO,
                        message=f"Latest commit: {commit_hash}",
                        details={"commit": commit_hash},
                    )
                )

            # Check git remote
            result = subprocess.run(
                ["git", "remote", "-v"], capture_output=True, text=True, check=False
            )

            if result.returncode == 0 and result.stdout.strip():
                results.append(
                    HealthCheckResult(
                        name="git_remote",
                        status=HealthStatus.INFO,
                        message="Git remote configured",
                        details={"remotes": result.stdout.strip()},
                    )
                )
            else:
                results.append(
                    HealthCheckResult(
                        name="git_remote",
                        status=HealthStatus.INFO,
                        message="No git remote configured",
                        recommendation="Add a remote: git remote add origin <url>",
                    )
                )

        except FileNotFoundError:
            results.append(
                HealthCheckResult(
                    name="git_installed",
                    status=HealthStatus.ERROR,
                    message="Git is not installed",
                    recommendation="Install git: https://git-scm.com/downloads",
                )
            )
        except Exception as e:
            results.append(
                HealthCheckResult(
                    name="git_check",
                    status=HealthStatus.ERROR,
                    message=f"Error checking git: {str(e)}",
                    details={"error": str(e)},
                )
            )

        return results

    def _check_cache(self) -> List[HealthCheckResult]:
        """Check cache validity and size."""
        results = []

        # Check cache directory exists
        cache_dir = ".l4_cache"
        if not os.path.exists(cache_dir):
            results.append(
                HealthCheckResult(
                    name="cache_directory",
                    status=HealthStatus.WARNING,
                    message=f"Cache directory does not exist: {cache_dir}",
                    recommendation="Cache directory will be created when needed",
                    details={"path": cache_dir},
                    fixable=True,
                )
            )
            return results

        # Calculate cache size
        cache_size_bytes = 0
        cache_entries = 0

        try:
            for root, dirs, files in os.walk(cache_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    cache_size_bytes += os.path.getsize(file_path)
                    cache_entries += 1

            cache_size_mb = cache_size_bytes / (1024 * 1024)

            # Determine status based on size
            if cache_size_mb > self.CRITICAL_CACHE_SIZE_MB:
                status = HealthStatus.CRITICAL
                message = (
                    f"Cache size {cache_size_mb:.2f} MB exceeds critical threshold"
                )
                recommendation = f"Clear cache: rm -rf {cache_dir}/*"
            elif cache_size_mb > self.WARNING_CACHE_SIZE_MB:
                status = HealthStatus.WARNING
                message = f"Cache size {cache_size_mb:.2f} MB is large"
                recommendation = f"Consider clearing old cache entries"
            else:
                status = HealthStatus.OK
                message = f"Cache size {cache_size_mb:.2f} MB"
                recommendation = None

            results.append(
                HealthCheckResult(
                    name="cache_size",
                    status=status,
                    message=message,
                    value=cache_size_mb,
                    unit="MB",
                    recommendation=recommendation,
                    details={
                        "path": cache_dir,
                        "entries": cache_entries,
                        "size_bytes": cache_size_bytes,
                    },
                    fixable=True,
                )
            )

            # Check cache validity (try to load cache manager)
            try:
                cm = cache_manager.CacheManager()
                stats = cm.get_stats()

                results.append(
                    HealthCheckResult(
                        name="cache_validity",
                        status=HealthStatus.OK,
                        message=f"Cache is valid with {stats['hit_rate']:.1f}% hit rate",
                        details=stats,
                    )
                )
            except Exception as e:
                results.append(
                    HealthCheckResult(
                        name="cache_validity",
                        status=HealthStatus.WARNING,
                        message=f"Cache may be corrupted: {str(e)}",
                        recommendation=f"Clear and rebuild cache: rm -rf {cache_dir}",
                        details={"error": str(e)},
                        fixable=True,
                    )
                )

        except Exception as e:
            results.append(
                HealthCheckResult(
                    name="cache_check",
                    status=HealthStatus.ERROR,
                    message=f"Error checking cache: {str(e)}",
                    details={"error": str(e)},
                )
            )

        return results

    def _check_filesystem(self) -> List[HealthCheckResult]:
        """Check file system permissions and disk space."""
        results = []

        # Check disk space
        try:
            if PSUTIL_AVAILABLE:
                disk_usage = psutil.disk_usage(".")
                free_mb = disk_usage.free / (1024 * 1024)
                total_mb = disk_usage.total / (1024 * 1024)
                used_percent = disk_usage.percent

                # Determine status based on free space
                if free_mb < self.CRITICAL_DISK_SPACE_MB:
                    status = HealthStatus.CRITICAL
                    message = f"Only {free_mb:.0f} MB disk space remaining"
                    recommendation = "Free up disk space immediately"
                elif free_mb < self.WARNING_DISK_SPACE_MB:
                    status = HealthStatus.WARNING
                    message = f"Only {free_mb:.0f} MB disk space remaining"
                    recommendation = "Consider freeing up disk space"
                else:
                    status = HealthStatus.OK
                    message = f"{free_mb:.0f} MB free disk space"
                    recommendation = None

                results.append(
                    HealthCheckResult(
                        name="disk_space",
                        status=status,
                        message=message,
                        value=free_mb,
                        unit="MB",
                        recommendation=recommendation,
                        details={
                            "total_mb": total_mb,
                            "used_percent": used_percent,
                            "free_mb": free_mb,
                        },
                    )
                )
            else:
                # Fallback without psutil
                stat = os.statvfs(".")
                free_mb = (stat.f_bavail * stat.f_frsize) / (1024 * 1024)

                results.append(
                    HealthCheckResult(
                        name="disk_space",
                        status=HealthStatus.INFO,
                        message=f"{free_mb:.0f} MB free disk space (estimated)",
                        value=free_mb,
                        unit="MB",
                        details={"method": "statvfs"},
                    )
                )

        except Exception as e:
            results.append(
                HealthCheckResult(
                    name="disk_space",
                    status=HealthStatus.ERROR,
                    message=f"Error checking disk space: {str(e)}",
                    details={"error": str(e)},
                )
            )

        # Check file system permissions
        try:
            # Check if we can write to current directory
            test_file = ".l4_health_check_test"
            try:
                with open(test_file, "w") as f:
                    f.write("test")
                os.remove(test_file)

                results.append(
                    HealthCheckResult(
                        name="filesystem_write",
                        status=HealthStatus.OK,
                        message="File system is writable",
                        details={"path": os.getcwd()},
                    )
                )
            except (IOError, OSError) as e:
                results.append(
                    HealthCheckResult(
                        name="filesystem_write",
                        status=HealthStatus.ERROR,
                        message=f"Cannot write to file system: {str(e)}",
                        recommendation="Check directory permissions",
                        details={"error": str(e), "path": os.getcwd()},
                    )
                )

        except Exception as e:
            results.append(
                HealthCheckResult(
                    name="filesystem_permissions",
                    status=HealthStatus.ERROR,
                    message=f"Error checking file system permissions: {str(e)}",
                    details={"error": str(e)},
                )
            )

        # Check for required files
        required_files = ["product.md", "technical.md"]
        for req_file in required_files:
            if os.path.exists(req_file):
                results.append(
                    HealthCheckResult(
                        name=f"required_file_{req_file}",
                        status=HealthStatus.OK,
                        message=f"Required file exists: {req_file}",
                        details={"path": req_file},
                    )
                )
            else:
                results.append(
                    HealthCheckResult(
                        name=f"required_file_{req_file}",
                        status=HealthStatus.ERROR,
                        message=f"Required file missing: {req_file}",
                        recommendation=f"Create {req_file} to initialize the project",
                        details={"path": req_file},
                    )
                )

        return results

    def _check_llm_api(self) -> List[HealthCheckResult]:
        """Check LLM API connectivity."""
        results = []

        # Check for API keys
        api_keys = {
            "GOOGLE_API_KEY": os.getenv("GOOGLE_API_KEY"),
            "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
            "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY"),
        }

        configured_providers = [k for k, v in api_keys.items() if v]

        if not configured_providers:
            results.append(
                HealthCheckResult(
                    name="llm_api_keys",
                    status=HealthStatus.ERROR,
                    message="No LLM API keys configured",
                    recommendation="Set at least one API key: GOOGLE_API_KEY, OPENAI_API_KEY, or ANTHROPIC_API_KEY",
                    details={"configured": []},
                )
            )
            return results

        results.append(
            HealthCheckResult(
                name="llm_api_keys",
                status=HealthStatus.OK,
                message=f"Configured LLM providers: {', '.join(configured_providers)}",
                details={"configured": configured_providers},
            )
        )

        # Try to connect to LLM API (simple test)
        try:
            from v3.llm_base.provider import LLMProvider

            # Try to initialize provider
            provider = LLMProvider()

            # Note: We don't actually make an API call here to avoid costs,
            # but we verify the provider can be initialized
            results.append(
                HealthCheckResult(
                    name="llm_api_connectivity",
                    status=HealthStatus.OK,
                    message="LLM provider can be initialized",
                    details={"provider": type(provider).__name__},
                )
            )

        except Exception as e:
            results.append(
                HealthCheckResult(
                    name="llm_api_connectivity",
                    status=HealthStatus.WARNING,
                    message=f"Cannot initialize LLM provider: {str(e)}",
                    recommendation="Check API keys and network connection",
                    details={"error": str(e)},
                )
            )

        return results

    def _check_system_resources(self) -> List[HealthCheckResult]:
        """Check system resources (CPU, memory)."""
        results = []

        if not PSUTIL_AVAILABLE:
            results.append(
                HealthCheckResult(
                    name="system_resources",
                    status=HealthStatus.INFO,
                    message="Install psutil for detailed resource monitoring: pip install psutil",
                    recommendation="pip install psutil",
                )
            )
            return results

        try:
            # Check CPU usage
            cpu_percent = psutil.cpu_percent(interval=0.5)

            if cpu_percent > 90:
                status = HealthStatus.WARNING
                message = f"High CPU usage: {cpu_percent:.1f}%"
            else:
                status = HealthStatus.OK
                message = f"CPU usage: {cpu_percent:.1f}%"

            results.append(
                HealthCheckResult(
                    name="cpu_usage",
                    status=status,
                    message=message,
                    value=cpu_percent,
                    unit="%",
                    details={"cores": psutil.cpu_count()},
                )
            )

            # Check memory usage
            mem = psutil.virtual_memory()
            mem_percent = mem.percent
            mem_available_mb = mem.available / (1024 * 1024)

            if mem_percent > 90:
                status = HealthStatus.WARNING
                message = f"High memory usage: {mem_percent:.1f}%"
            elif mem_available_mb < 500:
                status = HealthStatus.WARNING
                message = f"Low available memory: {mem_available_mb:.0f} MB"
            else:
                status = HealthStatus.OK
                message = f"Memory usage: {mem_percent:.1f}%"

            results.append(
                HealthCheckResult(
                    name="memory_usage",
                    status=status,
                    message=message,
                    value=mem_percent,
                    unit="%",
                    details={
                        "total_mb": mem.total / (1024 * 1024),
                        "available_mb": mem_available_mb,
                        "used_mb": mem.used / (1024 * 1024),
                    },
                )
            )

        except Exception as e:
            results.append(
                HealthCheckResult(
                    name="system_resources",
                    status=HealthStatus.ERROR,
                    message=f"Error checking system resources: {str(e)}",
                    details={"error": str(e)},
                )
            )

        return results

    def _calculate_summary(self, checks: List[HealthCheckResult]) -> Dict[str, int]:
        """Calculate summary statistics from check results."""
        summary = {
            "total": len(checks),
            "ok": 0,
            "warning": 0,
            "error": 0,
            "critical": 0,
            "info": 0,
        }

        for check in checks:
            summary[check.status.value] += 1

        return summary

    def _determine_overall_status(self, summary: Dict[str, int]) -> HealthStatus:
        """Determine overall health status from summary."""
        if summary["critical"] > 0:
            return HealthStatus.CRITICAL
        elif summary["error"] > 0:
            return HealthStatus.ERROR
        elif summary["warning"] > 0:
            return HealthStatus.WARNING
        else:
            return HealthStatus.OK

    def _generate_recommendations(self, checks: List[HealthCheckResult]) -> List[str]:
        """Generate prioritized list of recommendations."""
        recommendations = []

        # Priority: critical > error > warning > info
        priority_order = [
            HealthStatus.CRITICAL,
            HealthStatus.ERROR,
            HealthStatus.WARNING,
        ]

        for status in priority_order:
            for check in checks:
                if check.status == status and check.recommendation:
                    recommendations.append(
                        f"[{status.value.upper()}] {check.name}: {check.recommendation}"
                    )

        return recommendations

    def print_report(self, report: HealthReport, verbose: bool = False):
        """
        Print health check report to console.

        Args:
            report: HealthReport to print
            verbose: If True, include detailed information
        """
        if not self.console:
            self._print_simple_report(report, verbose)
            return

        # Rich console output
        self.console.print(f"\n[bold]L4 Health Check Report[/bold]")
        self.console.print(f"Generated: {report.timestamp}")
        self.console.print(f"Duration: {report.duration_ms:.0f}ms\n")

        # Overall status
        status_color = {
            HealthStatus.OK: "green",
            HealthStatus.WARNING: "yellow",
            HealthStatus.ERROR: "red",
            HealthStatus.CRITICAL: "red bold",
            HealthStatus.INFO: "blue",
        }.get(report.overall_status, "white")

        self.console.print(
            Panel(
                f"[{status_color}]Overall Status: {report.overall_status.value.upper()}[/{status_color}]",
                title="Summary",
            )
        )

        # Summary table
        summary_table = Table(title="Check Summary")
        summary_table.add_column("Status", style="bold")
        summary_table.add_column("Count", justify="right")

        summary_table.add_row("[green]OK[/green]", str(report.summary["ok"]))
        summary_table.add_row(
            "[yellow]WARNING[/yellow]", str(report.summary["warning"])
        )
        summary_table.add_row("[red]ERROR[/red]", str(report.summary["error"]))
        summary_table.add_row(
            "[red bold]CRITICAL[/red bold]", str(report.summary["critical"])
        )
        summary_table.add_row("[blue]INFO[/blue]", str(report.summary["info"]))
        summary_table.add_row("[bold]TOTAL[/bold]", str(report.summary["total"]))

        self.console.print(summary_table)

        # Detailed checks
        if verbose:
            for check in report.checks:
                status_color = {
                    HealthStatus.OK: "green",
                    HealthStatus.WARNING: "yellow",
                    HealthStatus.ERROR: "red",
                    HealthStatus.CRITICAL: "red bold",
                    HealthStatus.INFO: "blue",
                }.get(check.status, "white")

                value_str = (
                    f" ({check.value:.2f} {check.unit})"
                    if check.value and check.unit
                    else ""
                )
                fixable_str = " [FIXABLE]" if check.fixable else ""

                self.console.print(
                    f"[{status_color}]{check.status.value.upper()}[/{status_color}] "
                    f"{check.name}{value_str}{fixable_str}"
                )
                self.console.print(f"  {check.message}")

                if check.recommendation:
                    self.console.print(f"  [yellow]→ {check.recommendation}[/yellow]")

                if verbose and check.details:
                    for key, value in check.details.items():
                        if key != "error":  # Already shown in message
                            self.console.print(f"  [dim]  {key}: {value}[/dim]")

        # Recommendations
        if report.recommendations:
            self.console.print(f"\n[bold yellow]Recommendations:[/bold yellow]")
            for i, rec in enumerate(report.recommendations, 1):
                self.console.print(f"  {i}. {rec}")

        self.console.print()

    def _print_simple_report(self, report: HealthReport, verbose: bool = False):
        """Print simple text report (fallback without rich)."""
        print(f"\nL4 Health Check Report")
        print(f"Generated: {report.timestamp}")
        print(f"Duration: {report.duration_ms:.0f}ms\n")

        print(f"Overall Status: {report.overall_status.value.upper()}")
        print(f"\nSummary:")
        print(f"  OK: {report.summary['ok']}")
        print(f"  WARNING: {report.summary['warning']}")
        print(f"  ERROR: {report.summary['error']}")
        print(f"  CRITICAL: {report.summary['critical']}")
        print(f"  INFO: {report.summary['info']}")
        print(f"  TOTAL: {report.summary['total']}")

        if verbose:
            print(f"\nDetailed Checks:")
            for check in report.checks:
                value_str = (
                    f" ({check.value:.2f} {check.unit})"
                    if check.value and check.unit
                    else ""
                )
                fixable_str = " [FIXABLE]" if check.fixable else ""
                print(
                    f"  [{check.status.value.upper()}] {check.name}{value_str}{fixable_str}"
                )
                print(f"    {check.message}")
                if check.recommendation:
                    print(f"    → {check.recommendation}")

        if report.recommendations:
            print(f"\nRecommendations:")
            for i, rec in enumerate(report.recommendations, 1):
                print(f"  {i}. {rec}")

        print()

    def auto_fix_issues(self, report: HealthReport) -> Tuple[int, List[str]]:
        """
        Attempt to auto-fix fixable issues in the report.

        Args:
            report: HealthReport with issues to fix

        Returns:
            Tuple of (number_of_fixes_attempted, list_of_results)
        """
        fixes_attempted = 0
        fix_results = []

        for check in report.checks:
            if check.fixable:
                try:
                    if check.name.startswith("cache_"):
                        # Clear cache
                        cache_dir = ".l4_cache"
                        if os.path.exists(cache_dir):
                            shutil.rmtree(cache_dir)
                            os.makedirs(cache_dir, exist_ok=True)
                            fix_results.append(
                                f"✓ Cleared cache directory: {cache_dir}"
                            )
                            fixes_attempted += 1

                    elif "permissions" in check.name and "database" in check.name:
                        # Fix database permissions
                        for db_path in self._db_paths.values():
                            if os.path.exists(db_path):
                                os.chmod(db_path, 0o644)
                                fix_results.append(
                                    f"✓ Fixed permissions for: {db_path}"
                                )
                                fixes_attempted += 1

                    elif check.name == "git_repository":
                        # Initialize git repository
                        subprocess.run(["git", "init"], check=True, capture_output=True)
                        fix_results.append("✓ Initialized git repository")
                        fixes_attempted += 1

                    elif "cache_directory" in check.name:
                        # Create cache directory
                        cache_dir = ".l4_cache"
                        os.makedirs(cache_dir, exist_ok=True)
                        fix_results.append(f"✓ Created cache directory: {cache_dir}")
                        fixes_attempted += 1

                except Exception as e:
                    fix_results.append(f"✗ Failed to fix {check.name}: {str(e)}")

        return fixes_attempted, fix_results


# Global health check manager instance
_health_check_manager = None


def get_health_check_manager() -> HealthCheckManager:
    """
    Get the global health check manager instance (singleton).

    Returns:
        HealthCheckManager instance
    """
    global _health_check_manager
    if _health_check_manager is None:
        _health_check_manager = HealthCheckManager()
    return _health_check_manager


def run_health_check(verbose: bool = False, auto_fix: bool = False) -> HealthReport:
    """
    Run health checks and display report.

    Args:
        verbose: If True, include detailed output
        auto_fix: If True, attempt to auto-fix fixable issues

    Returns:
        HealthReport with check results
    """
    manager = get_health_check_manager()
    report = manager.run_all_checks(verbose=verbose)

    manager.print_report(report, verbose=verbose)

    if auto_fix:
        print("\nAttempting to auto-fix issues...")
        fixes_attempted, fix_results = manager.auto_fix_issues(report)

        if fix_results:
            print(f"\nAuto-fix Results ({fixes_attempted} fixes attempted):")
            for result in fix_results:
                print(f"  {result}")

            # Re-run checks after fixes
            print("\nRe-running health checks after fixes...")
            report = manager.run_all_checks(verbose=verbose)
            manager.print_report(report, verbose=verbose)

    return report


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="L4 Health Check Tool")
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Show detailed output"
    )
    parser.add_argument("--fix", action="store_true", help="Auto-fix fixable issues")
    parser.add_argument("--json", action="store_true", help="Output report as JSON")

    args = parser.parse_args()

    report = run_health_check(verbose=args.verbose, auto_fix=args.fix)

    if args.json:
        import json

        print(json.dumps(report.to_dict(), indent=2))

    # Exit with appropriate code
    if report.overall_status == HealthStatus.CRITICAL:
        sys.exit(2)
    elif report.overall_status == HealthStatus.ERROR:
        sys.exit(1)
    else:
        sys.exit(0)
