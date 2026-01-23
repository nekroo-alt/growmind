"""
User Interface Components for L4D V3

This module provides UI components including progress indicators, status displays,
interactive elements, and error messaging for enhanced user experience.
"""

import sys
import time
import threading
from typing import Optional, Dict, Any, List, Tuple
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime

# Try to import rich for rich terminal output
try:
    from rich.console import Console
    from rich.progress import (
        Progress,
        BarColumn,
        TextColumn,
        TimeRemainingColumn,
        TaskID,
    )
    from rich.text import Text
    from rich.panel import Panel
    from rich.syntax import Syntax
    from rich.table import Table
    from rich.markdown import Markdown

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    Progress = None
    Panel = None
    Syntax = None
    Table = None
    Markdown = None


@dataclass
class ProgressState:
    """State for tracking progress of an operation"""

    total: int = 100
    completed: int = 0
    description: str = ""
    start_time: float = field(default_factory=time.time)
    eta: Optional[float] = None
    cancelled: bool = False
    success: bool = False


class ProgressIndicator:
    """
    Progress indicator for long-running operations.

    Supports both TTY and non-TTY environments with automatic fallback.
    Uses rich library when available for enhanced display.
    """

    def __init__(self, description: str = "Processing"):
        """
        Initialize progress indicator.

        Args:
            description: Description of the operation
        """
        self.description = description
        self.state = ProgressState(description=description)
        self._lock = threading.Lock()
        self._console = Console() if RICH_AVAILABLE else None
        self._rich_progress: Optional[Progress] = None
        self._task_id: Optional[TaskID] = None
        self._is_tty = sys.stdout.isatty()

        # Track operation ID for telemetry correlation
        self.operation_id: Optional[str] = None

    def start(self, total: int = 100) -> None:
        """
        Start progress tracking.

        Args:
            total: Total number of steps (default: 100)
        """
        with self._lock:
            self.state.total = total
            self.state.completed = 0
            self.state.start_time = time.time()
            self.state.cancelled = False
            self.state.success = False
            self.state.eta = None

            if RICH_AVAILABLE and self._is_tty:
                self._rich_progress = Progress(
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                    TextColumn("({task.completed}/{task.total})"),
                    TimeRemainingColumn(),
                    console=self._console,
                    transient=True,
                )
                self._rich_progress.start()
                self._task_id = self._rich_progress.add_task(
                    self.description, total=total
                )
            else:
                # Simple text progress for non-TTY or without rich
                print(f"{self.description} started (0/{total})")

    def update(self, completed: int, description: Optional[str] = None) -> None:
        """
        Update progress.

        Args:
            completed: Number of steps completed
            description: Optional new description
        """
        with self._lock:
            if self.state.cancelled:
                return

            self.state.completed = min(completed, self.state.total)

            # Update ETA
            elapsed = time.time() - self.state.start_time
            if self.state.completed > 0:
                rate = self.state.completed / elapsed
                remaining = self.state.total - self.state.completed
                self.state.eta = remaining / rate if rate > 0 else None

            if description:
                self.state.description = description

            if RICH_AVAILABLE and self._rich_progress and self._task_id is not None:
                update_kwargs = {"completed": completed}
                if description:
                    update_kwargs["description"] = description
                self._rich_progress.update(self._task_id, **update_kwargs)
            elif self._is_tty:
                # Simple progress bar for TTY without rich
                percentage = (self.state.completed / self.state.total) * 100
                bar_length = 40
                filled = int(bar_length * self.state.completed / self.state.total)
                bar = "█" * filled + "░" * (bar_length - filled)
                print(
                    f"\r{self.description}: [{bar}] {percentage:.1f}% ({self.state.completed}/{self.state.total})",
                    end="",
                    flush=True,
                )

    def advance(self, delta: int = 1, description: Optional[str] = None) -> None:
        """
        Advance progress by delta steps.

        Args:
            delta: Number of steps to advance
            description: Optional new description
        """
        with self._lock:
            new_completed = self.state.completed + delta
            self.update(new_completed, description)

    def complete(self, success: bool = True) -> None:
        """
        Mark progress as complete.

        Args:
            success: Whether the operation succeeded
        """
        with self._lock:
            self.state.completed = self.state.total
            self.state.success = success

            if RICH_AVAILABLE and self._rich_progress and self._task_id is not None:
                self._rich_progress.update(self._task_id, completed=self.state.total)
                status = "✓" if success else "✗"
                self._rich_progress.stop()
                print(f"\n{self.description} {status}")
            elif self._is_tty:
                print(f"\n{self.description}: Complete ({'✓' if success else '✗'})")
            else:
                print(f"{self.description} completed ({'✓' if success else '✗'})")

    def cancel(self) -> None:
        """Cancel the operation."""
        with self._lock:
            self.state.cancelled = True

            if RICH_AVAILABLE and self._rich_progress:
                self._rich_progress.stop()
            print(f"\n{self.description} cancelled")

    def set_operation_id(self, operation_id: str) -> None:
        """
        Set operation ID for telemetry correlation.

        Args:
            operation_id: Operation ID from telemetry system
        """
        self.operation_id = operation_id

    def get_status(self) -> Dict[str, Any]:
        """
        Get current progress status.

        Returns:
            Dictionary with current progress state
        """
        with self._lock:
            elapsed = time.time() - self.state.start_time
            return {
                "operation_id": self.operation_id,
                "description": self.state.description,
                "total": self.state.total,
                "completed": self.state.completed,
                "percentage": (
                    (self.state.completed / self.state.total) * 100
                    if self.state.total > 0
                    else 0
                ),
                "elapsed_seconds": elapsed,
                "eta_seconds": self.state.eta,
                "cancelled": self.state.cancelled,
                "success": self.state.success,
            }

    @contextmanager
    def track(self, total: int = 100):
        """
        Context manager for automatic progress tracking.

        Args:
            total: Total number of steps

        Yields:
            ProgressIndicator instance

        Example:
            with progress.track(total=5) as p:
                for i in range(5):
                    do_work()
                    p.advance()
        """
        self.start(total)
        try:
            yield self
            self.complete(success=True)
        except Exception as e:
            self.complete(success=False)
            raise


class MultiStepProgress:
    """
    Progress indicator for multi-step operations with named steps.

    Shows current step and overall progress.
    """

    def __init__(self, description: str = "Processing", steps: List[str] = None):
        """
        Initialize multi-step progress.

        Args:
            description: Overall operation description
            steps: List of step names
        """
        self.description = description
        self.steps = steps or []
        self.current_step_index = 0
        self.indicator = ProgressIndicator()
        self.operation_id: Optional[str] = None

    def set_steps(self, steps: List[str]) -> None:
        """
        Set step names.

        Args:
            steps: List of step names
        """
        self.steps = steps
        self.current_step_index = 0

    def start(self) -> None:
        """Start progress tracking."""
        self.indicator.description = self.description
        if self.steps:
            total = len(self.steps)
            self.indicator.start(total)
            self._update_step_description()
        else:
            self.indicator.start()

    def next_step(self) -> None:
        """Advance to next step."""
        if self.current_step_index < len(self.steps):
            self.current_step_index += 1
            self.indicator.advance()
            self._update_step_description()

    def _update_step_description(self) -> None:
        """Update progress description with current step."""
        if self.steps and self.current_step_index < len(self.steps):
            step_name = self.steps[self.current_step_index]
            step_num = self.current_step_index + 1
            total_steps = len(self.steps)
            new_description = (
                f"{self.description}: Step {step_num}/{total_steps} - {step_name}"
            )
            self.indicator.update(self.current_step_index, description=new_description)

    def complete(self, success: bool = True) -> None:
        """
        Mark all steps as complete.

        Args:
            success: Whether the operation succeeded
        """
        self.indicator.complete(success)

    def cancel(self) -> None:
        """Cancel the operation."""
        self.indicator.cancel()

    def set_operation_id(self, operation_id: str) -> None:
        """
        Set operation ID for telemetry correlation.

        Args:
            operation_id: Operation ID from telemetry system
        """
        self.operation_id = operation_id
        self.indicator.set_operation_id(operation_id)

    @contextmanager
    def track(self):
        """
        Context manager for automatic multi-step tracking.

        Yields:
            MultiStepProgress instance

        Example:
            with progress.track() as p:
                for step_name in steps:
                    do_step()
                    p.next_step()
        """
        self.start()
        try:
            yield self
            self.complete(success=True)
        except Exception as e:
            self.complete(success=False)
            raise


def create_progress(description: str = "Processing") -> ProgressIndicator:
    """
    Factory function to create a progress indicator.

    Args:
        description: Description of the operation

    Returns:
        ProgressIndicator instance
    """
    return ProgressIndicator(description)


def create_multi_step_progress(
    description: str = "Processing", steps: List[str] = None
) -> MultiStepProgress:
    """
    Factory function to create a multi-step progress indicator.

    Args:
        description: Overall operation description
        steps: List of step names

    Returns:
        MultiStepProgress instance
    """
    return MultiStepProgress(description, steps)


# ============================================================================
# Interactive Error Messages
# ============================================================================


class ErrorDisplay:
    """
    Interactive error message display with recovery suggestions.

    Provides human-friendly error messages with context, recovery actions,
    command examples, and documentation links.
    """

    # Error severity to color mapping
    SEVERITY_COLORS = {
        "info": "blue",
        "warning": "yellow",
        "error": "red",
        "critical": "bold red",
    }

    # Error code to documentation URLs
    DOCUMENTATION_URLS = {
        "LLM_RATE_LIMIT": "https://docs.l4.dev/errors/rate-limit",
        "LLM_TIMEOUT": "https://docs.l4.dev/errors/timeout",
        "LLM_AUTHENTICATION_FAILED": "https://docs.l4.dev/errors/authentication",
        "LLM_QUOTA_EXCEEDED": "https://docs.l4.dev/errors/quota",
        "DB_LOCKED": "https://docs.l4.dev/errors/database-locked",
        "DB_CONNECTION_FAILED": "https://docs.l4.dev/errors/database-connection",
        "DB_CORRUPTION": "https://docs.l4.dev/errors/database-corruption",
        "FILE_NOT_FOUND": "https://docs.l4.dev/errors/file-not-found",
        "FILE_PERMISSION_DENIED": "https://docs.l4.dev/errors/file-permissions",
        "GIT_CONFLICT": "https://docs.l4.dev/errors/git-conflict",
        "GIT_MERGE_FAILED": "https://docs.l4.dev/errors/git-merge",
        "NETWORK_CONNECTION_FAILED": "https://docs.l4.dev/errors/network",
        "SYSTEM_RESOURCE_EXHAUSTED": "https://docs.l4.dev/errors/resources",
    }

    # Common recovery commands
    RECOVERY_COMMANDS = {
        "retry": "l4-dev retry",
        "retry_operation": "l4-dev retry --operation-id {operation_id}",
        "resume_last": "l4-dev resume",
        "resume_checkpoint": "l4-dev checkpoints restore --id {checkpoint_id}",
        "list_checkpoints": "l4-dev checkpoints list",
        "doctor": "l4-dev doctor",
        "logs_recent": "l4-dev logs --last 1h",
        "logs_error": "l4-dev logs --error",
        "health": "l4-dev health",
    }

    def __init__(self, use_rich: Optional[bool] = None):
        """
        Initialize error display.

        Args:
            use_rich: Force use of rich library (None = auto-detect)
        """
        self.use_rich = (
            RICH_AVAILABLE if use_rich is None else use_rich and RICH_AVAILABLE
        )
        self.console = Console() if self.use_rich else None

    def display_error(
        self,
        error: Any,
        context: Optional[Dict[str, Any]] = None,
        show_traceback: bool = False,
        show_suggestions: bool = True,
    ) -> None:
        """
        Display an error with enhanced formatting.

        Args:
            error: Error object (L4DError, Exception, or string)
            context: Additional context information
            show_traceback: Whether to show stack trace
            show_suggestions: Whether to show recovery suggestions
        """
        # Import here to avoid circular dependency
        from core.error_handling import L4DError, classify_exception

        # Classify error if needed
        if not isinstance(error, L4DError):
            error = classify_exception(error, context)

        context = context or error.context

        # Display based on availability of rich
        if self.use_rich and self.console:
            self._display_rich_error(error, context, show_traceback, show_suggestions)
        else:
            self._display_plain_error(error, context, show_traceback, show_suggestions)

    def _display_rich_error(
        self,
        error: Any,
        context: Dict[str, Any],
        show_traceback: bool,
        show_suggestions: bool,
    ) -> None:
        """Display error with rich formatting."""
        from core.error_handling import ErrorSeverity

        # Create error panel
        severity_color = self.SEVERITY_COLORS.get(error.severity.value, "red")

        # Error header
        error_header = Text()
        error_header.append(f"[{error.code.value}] ", style=f"bold {severity_color}")
        error_header.append(error.message, style=severity_color)

        # Build error content
        content_lines = []

        # Add timestamp
        content_lines.append(f"Time: {error.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")

        # Add context if available
        if context:
            content_lines.append("\nContext:")
            for key, value in context.items():
                if isinstance(value, (list, dict)):
                    value_str = str(value)[:100]  # Truncate long values
                else:
                    value_str = str(value)
                content_lines.append(f"  {key}: {value_str}")

        # Add recovery suggestions
        if show_suggestions:
            suggestions = self._get_recovery_suggestions(error, context)
            if suggestions:
                content_lines.append("\nSuggested Actions:")
                for i, suggestion in enumerate(suggestions, 1):
                    content_lines.append(f"  {i}. {suggestion}")

            # Add command examples
            commands = self._get_recovery_commands(error, context)
            if commands:
                content_lines.append("\nCommands:")
                for cmd_desc, cmd in commands:
                    content_lines.append(f"  {cmd_desc}: {cmd}")

            # Add documentation link
            doc_url = self.DOCUMENTATION_URLS.get(error.code.value)
            if doc_url:
                content_lines.append(f"\nDocumentation: {doc_url}")

        # Show traceback if requested
        if show_traceback and error.traceback:
            content_lines.append("\nStack Trace:")
            content_lines.append(error.traceback)

        # Create panel
        panel = Panel(
            "\n".join(content_lines),
            title=error_header,
            title_align="left",
            border_style=severity_color,
            padding=(1, 2),
        )

        self.console.print(panel)

    def _display_plain_error(
        self,
        error: Any,
        context: Dict[str, Any],
        show_traceback: bool,
        show_suggestions: bool,
    ) -> None:
        """Display error with plain text formatting."""
        # Get severity for prefix
        from core.error_handling import ErrorSeverity

        severity = error.severity.value.upper()
        print(f"\n{'='*60}")
        print(f"ERROR: [{error.code.value}] {error.message}")
        print(f"{'='*60}")

        # Add timestamp
        print(f"\nTime: {error.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Severity: {severity}")
        print(f"Source: {error.source.value}")
        print(f"Category: {error.category.value}")

        # Add context
        if context:
            print("\nContext:")
            for key, value in context.items():
                if isinstance(value, (list, dict)):
                    value_str = str(value)[:100]
                else:
                    value_str = str(value)
                print(f"  {key}: {value_str}")

        # Add recovery suggestions
        if show_suggestions:
            suggestions = self._get_recovery_suggestions(error, context)
            if suggestions:
                print("\nSuggested Actions:")
                for i, suggestion in enumerate(suggestions, 1):
                    print(f"  {i}. {suggestion}")

            # Add command examples
            commands = self._get_recovery_commands(error, context)
            if commands:
                print("\nCommands:")
                for cmd_desc, cmd in commands:
                    print(f"  {cmd_desc}: {cmd}")

            # Add documentation link
            doc_url = self.DOCUMENTATION_URLS.get(error.code.value)
            if doc_url:
                print(f"\nDocumentation: {doc_url}")

        # Show traceback
        if show_traceback and error.traceback:
            print("\nStack Trace:")
            print(error.traceback)

        print(f"{'='*60}\n")

    def _get_recovery_suggestions(
        self, error: Any, context: Dict[str, Any]
    ) -> List[str]:
        """Get recovery suggestions for an error."""
        from core.error_handling import ErrorCode

        suggestions = []

        # Use error's recovery strategy if available
        if hasattr(error, "recovery_strategy") and error.recovery_strategy:
            suggestions.append(error.recovery_strategy)

        # Add specific suggestions based on error code
        error_code = error.code.value if hasattr(error, "code") else None

        if error_code == ErrorCode.LLM_RATE_LIMIT.value:
            suggestions.append("Wait 1-5 minutes for rate limit to reset")
            suggestions.append("Upgrade your API plan for higher limits")
        elif error_code == ErrorCode.LLM_TIMEOUT.value:
            suggestions.append("Check your network connection")
            suggestions.append("Retry with exponential backoff")
        elif error_code == ErrorCode.LLM_AUTHENTICATION_FAILED.value:
            suggestions.append("Verify your API key is correct")
            suggestions.append("Check API key permissions")
        elif error_code == ErrorCode.DB_LOCKED.value:
            suggestions.append("Wait a moment and retry")
            suggestions.append("Check if another process is using the database")
        elif error_code == ErrorCode.DB_CORRUPTION.value:
            suggestions.append("Restore from the latest checkpoint")
            suggestions.append("Reinitialize the database (data loss warning)")
        elif error_code == ErrorCode.FILE_NOT_FOUND.value:
            suggestions.append("Check the file path in the error message")
            suggestions.append("Create the missing file if required")
        elif error_code == ErrorCode.FILE_PERMISSION_DENIED.value:
            suggestions.append("Check file permissions with: ls -la <file_path>")
            suggestions.append("Adjust permissions: chmod +r <file_path>")
        elif error_code == ErrorCode.GIT_CONFLICT.value:
            suggestions.append("Review and resolve conflicts in affected files")
            suggestions.append("After resolving: git add <resolved_files>")
            suggestions.append("Complete merge: git commit")
            suggestions.append("Or abort: git merge --abort")
        elif error_code == ErrorCode.GIT_MERGE_FAILED.value:
            suggestions.append("Check git status for details")
            suggestions.append("Resolve merge conflicts manually")
            suggestions.append("Or cancel: git merge --abort")
        elif error_code == ErrorCode.NETWORK_CONNECTION_FAILED.value:
            suggestions.append("Check your internet connection")
            suggestions.append("Verify network settings and firewall")
            suggestions.append("Retry with exponential backoff")
        elif error_code == ErrorCode.SYSTEM_RESOURCE_EXHAUSTED.value:
            suggestions.append("Close unnecessary applications")
            suggestions.append("Free up disk space")
            suggestions.append("Increase system resources if possible")

        # Add general suggestions
        suggestions.append("Run diagnostics: l4-dev doctor")
        suggestions.append("Check recent logs: l4-dev logs --last 1h")

        return suggestions

    def _get_recovery_commands(
        self, error: Any, context: Dict[str, Any]
    ) -> List[Tuple[str, str]]:
        """Get recovery commands for an error."""
        commands = []

        operation_id = context.get("operation_id")
        checkpoint_id = context.get("checkpoint_id")

        # Add retry command if operation ID available
        if operation_id:
            commands.append(
                (
                    "Retry operation",
                    self.RECOVERY_COMMANDS["retry_operation"].format(
                        operation_id=operation_id
                    ),
                )
            )

        # Add checkpoint commands
        if checkpoint_id:
            commands.append(
                (
                    "Restore checkpoint",
                    self.RECOVERY_COMMANDS["resume_checkpoint"].format(
                        checkpoint_id=checkpoint_id
                    ),
                )
            )

        # Add general commands
        commands.append(("Resume last session", self.RECOVERY_COMMANDS["resume_last"]))
        commands.append(
            ("List checkpoints", self.RECOVERY_COMMANDS["list_checkpoints"])
        )
        commands.append(("Run diagnostics", self.RECOVERY_COMMANDS["doctor"]))
        commands.append(("Check recent logs", self.RECOVERY_COMMANDS["logs_recent"]))
        commands.append(("Check error logs", self.RECOVERY_COMMANDS["logs_error"]))
        commands.append(("System health", self.RECOVERY_COMMANDS["health"]))

        return commands

    def display_recovery_result(
        self, success: bool, message: str, action_taken: Optional[str] = None
    ) -> None:
        """
        Display recovery result.

        Args:
            success: Whether recovery was successful
            message: Recovery message
            action_taken: Action that was taken
        """
        if self.use_rich and self.console:
            status = "✓" if success else "✗"
            style = "green" if success else "red"

            content = [f"{status} Recovery Result"]

            if action_taken:
                content.append(f"Action: {action_taken}")

            content.append(message)

            panel = Panel(
                "\n".join(content), title="Recovery", border_style=style, padding=(1, 2)
            )
            self.console.print(panel)
        else:
            status = "SUCCESS" if success else "FAILED"
            print(f"\n{'='*60}")
            print(f"Recovery: {status}")
            if action_taken:
                print(f"Action: {action_taken}")
            print(message)
            print(f"{'='*60}\n")


def create_error_display(use_rich: Optional[bool] = None) -> ErrorDisplay:
    """
    Factory function to create an error display.

    Args:
        use_rich: Force use of rich library (None = auto-detect)

    Returns:
        ErrorDisplay instance
    """
    return ErrorDisplay(use_rich)


def display_error(
    error: Any,
    context: Optional[Dict[str, Any]] = None,
    show_traceback: bool = False,
    show_suggestions: bool = True,
) -> None:
    """
    Convenience function to display an error.

    Args:
        error: Error object (L4DError, Exception, or string)
        context: Additional context information
        show_traceback: Whether to show stack trace
        show_suggestions: Whether to show recovery suggestions
    """
    display = create_error_display()
    display.display_error(error, context, show_traceback, show_suggestions)


def display_recovery_result(
    success: bool, message: str, action_taken: Optional[str] = None
) -> None:
    """
    Convenience function to display recovery result.

    Args:
        success: Whether recovery was successful
        message: Recovery message
        action_taken: Action that was taken
    """
    display = create_error_display()
    display.display_recovery_result(success, message, action_taken)


# ============================================================================
# Status Dashboard
# ============================================================================


class StatusDashboard:
    """
    CLI status dashboard for monitoring system state.

    Displays current session status, active operations, recent activity,
    system health, and resource usage with support for auto-refresh.
    """

    def __init__(self, use_rich: Optional[bool] = None):
        """
        Initialize status dashboard.

        Args:
            use_rich: Force use of rich library (None = auto-detect)
        """
        self.use_rich = (
            RICH_AVAILABLE if use_rich is None else use_rich and RICH_AVAILABLE
        )
        self.console = Console() if self.use_rich else None

    def display(
        self,
        session_info: Optional[Dict[str, Any]] = None,
        active_operation: Optional[Dict[str, Any]] = None,
        recent_activities: Optional[List[Dict[str, Any]]] = None,
        health_report: Optional[Dict[str, Any]] = None,
        resource_usage: Optional[Dict[str, Any]] = None,
        verbose: bool = False,
    ) -> None:
        """
        Display comprehensive status dashboard.

        Args:
            session_info: Session information (id, status, duration, etc.)
            active_operation: Currently active operation (type, task, progress)
            recent_activities: Recent activity list
            health_report: Health check results
            resource_usage: Resource usage metrics (CPU, memory, cache)
            verbose: Show detailed information
        """
        if self.use_rich and self.console:
            self._display_rich_dashboard(
                session_info,
                active_operation,
                recent_activities,
                health_report,
                resource_usage,
                verbose,
            )
        else:
            self._display_plain_dashboard(
                session_info,
                active_operation,
                recent_activities,
                health_report,
                resource_usage,
                verbose,
            )

    def _display_rich_dashboard(
        self,
        session_info: Optional[Dict[str, Any]],
        active_operation: Optional[Dict[str, Any]],
        recent_activities: Optional[List[Dict[str, Any]]],
        health_report: Optional[Dict[str, Any]],
        resource_usage: Optional[Dict[str, Any]],
        verbose: bool,
    ) -> None:
        """Display dashboard with rich formatting."""
        from datetime import datetime

        # Session panel
        if session_info:
            session_text = Text()
            session_id = session_info.get("id", "N/A")
            session_status = session_info.get("status", "unknown")

            # Color code status
            status_color = {
                "active": "green",
                "paused": "yellow",
                "completed": "blue",
                "failed": "red",
            }.get(session_status, "white")

            session_text.append(f"ID: {session_id}\n", style="cyan")
            session_text.append(f"Status: ", style="white")
            session_text.append(
                f"{session_status.upper()}\n", style=f"bold {status_color}"
            )

            if "start_time" in session_info:
                start_time = session_info["start_time"]
                if isinstance(start_time, str):
                    start_time = datetime.fromisoformat(
                        start_time.replace("Z", "+00:00")
                    )
                elapsed = (datetime.now() - start_time).total_seconds()
                hours = int(elapsed // 3600)
                minutes = int((elapsed % 3600) // 60)
                session_text.append(f"Duration: {hours}h {minutes}m\n")

            if "tasks_completed" in session_info:
                session_text.append(
                    f"Tasks Completed: {session_info['tasks_completed']}\n"
                )

            self.console.print(
                Panel(session_text, title="📊 Session", border_style="cyan")
            )

        # Active operation panel
        if active_operation:
            op_text = Text()
            op_type = active_operation.get("operation_type", "N/A")
            op_status = active_operation.get("status", "unknown")

            op_text.append(f"Type: {op_type}\n", style="cyan")
            op_text.append(f"Status: ", style="white")
            op_text.append(
                f"{op_status.upper()}\n",
                style="green" if op_status == "in_progress" else "yellow",
            )

            if "task_id" in active_operation:
                op_text.append(f"Task: {active_operation['task_id']}\n")
            if "task_title" in active_operation:
                op_text.append(f"Title: {active_operation['task_title']}\n")
            if "progress" in active_operation:
                progress = active_operation["progress"]
                op_text.append(
                    f"Progress: {progress.get('completed', 0)}/{progress.get('total', 0)}"
                )
                if "percentage" in progress:
                    op_text.append(f" ({progress['percentage']:.1f}%)\n")

            self.console.print(
                Panel(op_text, title="⚡ Active Operation", border_style="green")
            )

        # Health report panel
        if health_report:
            health_text = Text()
            overall_status = health_report.get("overall_status", "unknown")

            status_emoji = {
                "healthy": "✅",
                "warning": "⚠️",
                "error": "❌",
                "critical": "🔴",
            }.get(overall_status, "❓")

            health_text.append(
                f"{status_emoji} {overall_status.upper()}\n\n",
                style="bold green" if overall_status == "healthy" else "bold red",
            )

            checks = health_report.get("checks", {})
            for check_name, check_info in checks.items():
                check_status = check_info.get("status", "unknown")
                status_icon = "✓" if check_status == "ok" else "✗"
                status_color = "green" if check_status == "ok" else "red"

                health_text.append(f"{status_icon} {check_name}: ", style="white")
                health_text.append(f"{check_status}\n", style=status_color)

                if verbose and "details" in check_info:
                    for detail_key, detail_value in check_info["details"].items():
                        health_text.append(
                            f"  {detail_key}: {detail_value}\n", style="dim"
                        )

            self.console.print(
                Panel(health_text, title="🏥 System Health", border_style="blue")
            )

        # Resource usage panel
        if resource_usage:
            resource_text = Text()

            if "cpu" in resource_usage:
                cpu = resource_usage["cpu"]
                resource_text.append(f"CPU: {cpu:.1f}%\n", style="cyan")

            if "memory" in resource_usage:
                memory = resource_usage["memory"]
                resource_text.append(f"Memory: {memory:.2f} GB\n", style="cyan")

            if "cache_size" in resource_usage:
                cache = resource_usage["cache_size"]
                resource_text.append(f"Cache: {cache:.2f} MB\n", style="cyan")

            if "cache_hit_rate" in resource_usage:
                hit_rate = resource_usage["cache_hit_rate"]
                resource_text.append(
                    f"Cache Hit Rate: {hit_rate:.1f}%\n", style="green"
                )

            self.console.print(
                Panel(resource_text, title="💻 Resources", border_style="yellow")
            )

        # Recent activities panel
        if recent_activities and verbose:
            activities_table = Table(title="📝 Recent Activity")
            activities_table.add_column("Time", style="dim")
            activities_table.add_column("Type", style="cyan")
            activities_table.add_column("Status")
            activities_table.add_column("Summary")

            for activity in recent_activities[:5]:  # Show last 5
                timestamp = activity.get("timestamp", "")
                if isinstance(timestamp, datetime):
                    timestamp = timestamp.strftime("%H:%M:%S")

                status = activity.get("status", "")
                status_color = "green" if status == "success" else "red"

                activities_table.add_row(
                    str(timestamp),
                    activity.get("action_type", ""),
                    f"[{status_color}]{status}[/{status_color}]",
                    activity.get("summary", "")[:50],
                )

            self.console.print(activities_table)

    def _display_plain_dashboard(
        self,
        session_info: Optional[Dict[str, Any]],
        active_operation: Optional[Dict[str, Any]],
        recent_activities: Optional[List[Dict[str, Any]]],
        health_report: Optional[Dict[str, Any]],
        resource_usage: Optional[Dict[str, Any]],
        verbose: bool,
    ) -> None:
        """Display dashboard with plain text formatting."""
        from datetime import datetime

        print("\n" + "=" * 60)
        print("L4 PLATFORM STATUS DASHBOARD")
        print("=" * 60 + "\n")

        # Session info
        if session_info:
            print("📊 SESSION")
            print("-" * 60)
            session_id = session_info.get("id", "N/A")
            session_status = session_info.get("status", "unknown")
            print(f"ID: {session_id}")
            print(f"Status: {session_status.upper()}")

            if "start_time" in session_info:
                start_time = session_info["start_time"]
                if isinstance(start_time, str):
                    start_time = datetime.fromisoformat(
                        start_time.replace("Z", "+00:00")
                    )
                elapsed = (datetime.now() - start_time).total_seconds()
                hours = int(elapsed // 3600)
                minutes = int((elapsed % 3600) // 60)
                print(f"Duration: {hours}h {minutes}m")

            if "tasks_completed" in session_info:
                print(f"Tasks Completed: {session_info['tasks_completed']}")

            print()

        # Active operation
        if active_operation:
            print("⚡ ACTIVE OPERATION")
            print("-" * 60)
            op_type = active_operation.get("operation_type", "N/A")
            op_status = active_operation.get("status", "unknown")
            print(f"Type: {op_type}")
            print(f"Status: {op_status.upper()}")

            if "task_id" in active_operation:
                print(f"Task: {active_operation['task_id']}")
            if "task_title" in active_operation:
                print(f"Title: {active_operation['task_title']}")
            if "progress" in active_operation:
                progress = active_operation["progress"]
                completed = progress.get("completed", 0)
                total = progress.get("total", 0)
                print(f"Progress: {completed}/{total}")
                if "percentage" in progress:
                    print(f"Progress: {progress['percentage']:.1f}%")

            print()

        # Health report
        if health_report:
            print("🏥 SYSTEM HEALTH")
            print("-" * 60)
            overall_status = health_report.get("overall_status", "unknown")
            status_emoji = {
                "healthy": "✅",
                "warning": "⚠️",
                "error": "❌",
                "critical": "🔴",
            }.get(overall_status, "❓")
            print(f"Overall: {status_emoji} {overall_status.upper()}")
            print()

            checks = health_report.get("checks", {})
            for check_name, check_info in checks.items():
                check_status = check_info.get("status", "unknown")
                status_icon = "✓" if check_status == "ok" else "✗"
                print(f"  {status_icon} {check_name}: {check_status}")

                if verbose and "details" in check_info:
                    for detail_key, detail_value in check_info["details"].items():
                        print(f"    {detail_key}: {detail_value}")

            print()

        # Resource usage
        if resource_usage:
            print("💻 RESOURCES")
            print("-" * 60)

            if "cpu" in resource_usage:
                cpu = resource_usage["cpu"]
                print(f"CPU: {cpu:.1f}%")

            if "memory" in resource_usage:
                memory = resource_usage["memory"]
                print(f"Memory: {memory:.2f} GB")

            if "cache_size" in resource_usage:
                cache = resource_usage["cache_size"]
                print(f"Cache: {cache:.2f} MB")

            if "cache_hit_rate" in resource_usage:
                hit_rate = resource_usage["cache_hit_rate"]
                print(f"Cache Hit Rate: {hit_rate:.1f}%")

            print()

        # Recent activities
        if recent_activities and verbose:
            print("📝 RECENT ACTIVITY")
            print("-" * 60)

            for activity in recent_activities[:5]:  # Show last 5
                timestamp = activity.get("timestamp", "")
                if isinstance(timestamp, datetime):
                    timestamp = timestamp.strftime("%H:%M:%S")

                status = activity.get("status", "")
                action_type = activity.get("action_type", "")
                summary = activity.get("summary", "")[:50]

                print(f"[{timestamp}] {action_type} | {status} | {summary}")

            print()

        print("=" * 60 + "\n")

    def watch(
        self, interval: int = 5, max_iterations: Optional[int] = None, **kwargs
    ) -> None:
        """
        Watch mode - auto-refresh dashboard at interval.

        Args:
            interval: Refresh interval in seconds
            max_iterations: Maximum number of refreshes (None = infinite)
            **kwargs: Arguments passed to display()
        """
        import time

        iteration = 0
        try:
            while True:
                # Clear screen (works on most terminals)
                if self.use_rich:
                    self.console.clear()
                else:
                    import os

                    os.system("cls" if os.name == "nt" else "clear")

                # Display dashboard
                self.display(**kwargs)

                iteration += 1
                if max_iterations and iteration >= max_iterations:
                    break

                print(f"\nRefreshing in {interval}s... (Press Ctrl+C to stop)")
                time.sleep(interval)

        except KeyboardInterrupt:
            print("\nWatch mode stopped.")


def create_status_dashboard(use_rich: Optional[bool] = None) -> StatusDashboard:
    """
    Factory function to create a status dashboard.

    Args:
        use_rich: Force use of rich library (None = auto-detect)

    Returns:
        StatusDashboard instance
    """
    return StatusDashboard(use_rich)


def display_status(
    session_info: Optional[Dict[str, Any]] = None,
    active_operation: Optional[Dict[str, Any]] = None,
    recent_activities: Optional[List[Dict[str, Any]]] = None,
    health_report: Optional[Dict[str, Any]] = None,
    resource_usage: Optional[Dict[str, Any]] = None,
    verbose: bool = False,
) -> None:
    """
    Convenience function to display status dashboard.

    Args:
        session_info: Session information
        active_operation: Currently active operation
        recent_activities: Recent activity list
        health_report: Health check results
        resource_usage: Resource usage metrics
        verbose: Show detailed information
    """
    dashboard = create_status_dashboard()
    dashboard.display(
        session_info=session_info,
        active_operation=active_operation,
        recent_activities=recent_activities,
        health_report=health_report,
        resource_usage=resource_usage,
        verbose=verbose,
    )


# ============================================================================
# Progress Visualization (V4)
# ============================================================================


class ProgressVisualizer:
    """
    Progress visualization for user feedback.

    Displays progress for tasks, sessions, and projects with charts,
    predictions, and alerts for stagnation or regression.
    """

    def __init__(self, use_rich: Optional[bool] = None):
        """
        Initialize progress visualizer.

        Args:
            use_rich: Force use of rich library (None = auto-detect)
        """
        self.use_rich = (
            RICH_AVAILABLE if use_rich is None else use_rich and RICH_AVAILABLE
        )
        self.console = Console() if self.use_rich else None

    def display_task_progress(
        self,
        task_id: str,
        progress: float,
        metrics: Optional[Dict[str, Any]] = None,
        predicted_completion: Optional[float] = None,
        stagnation: Optional[str] = None,
        regression: bool = False,
    ) -> None:
        """
        Display progress for current task.

        Args:
            task_id: Task identifier
            progress: Progress percentage (0-100)
            metrics: Optional task metrics (lines, tests, etc.)
            predicted_completion: Optional predicted completion time in seconds
            stagnation: Optional stagnation status (none, warning, critical)
            regression: Whether regression detected
        """
        if self.use_rich and self.console:
            self._display_rich_task_progress(
                task_id, progress, metrics, predicted_completion, stagnation, regression
            )
        else:
            self._display_plain_task_progress(
                task_id, progress, metrics, predicted_completion, stagnation, regression
            )

    def _display_rich_task_progress(
        self,
        task_id: str,
        progress: float,
        metrics: Optional[Dict[str, Any]],
        predicted_completion: Optional[float],
        stagnation: Optional[str],
        regression: bool,
    ) -> None:
        """Display task progress with rich formatting."""
        # Color code based on status
        status_color = "green"
        if stagnation == "warning":
            status_color = "yellow"
        elif stagnation == "critical" or regression:
            status_color = "red"

        # Create progress text
        progress_text = Text()
        progress_text.append(f"Task: {task_id}\n", style="cyan bold")
        progress_text.append(f"Progress: {progress:.1f}%\n", style=f"{status_color} bold")

        # Add metrics if available
        if metrics:
            progress_text.append("\nMetrics:\n", style="white")
            if "lines_added" in metrics:
                progress_text.append(
                    f"  Lines Added: {metrics['lines_added']}\n", style="cyan"
                )
            if "tests_passing" in metrics:
                progress_text.append(
                    f"  Tests Passing: {metrics['tests_passing']}", style="cyan"
                )
                if "tests_total" in metrics:
                    progress_text.append(
                        f"/{metrics['tests_total']}", style="dim"
                    )
                progress_text.append("\n")

        # Add prediction if available
        if predicted_completion:
            from datetime import timedelta

            eta_seconds = predicted_completion
            hours = int(eta_seconds // 3600)
            minutes = int((eta_seconds % 3600) // 60)
            progress_text.append(
                f"\nEstimated Time: {hours}h {minutes}m remaining\n", style="blue"
            )

        # Add alerts
        if stagnation == "warning":
            progress_text.append(
                f"\n⚠️  Stagnation Warning: No progress for multiple operations\n",
                style="yellow",
            )
        elif stagnation == "critical":
            progress_text.append(
                f"\n🔴 Critical Stagnation: No progress for extended period\n",
                style="bold red",
            )

        if regression:
            progress_text.append(
                f"\n🔴 Regression Detected: Progress has decreased\n",
                style="bold red",
            )

        # Create panel
        panel = Panel(
            progress_text,
            title="📊 Task Progress",
            border_style=status_color,
            padding=(1, 2),
        )

        self.console.print(panel)

    def _display_plain_task_progress(
        self,
        task_id: str,
        progress: float,
        metrics: Optional[Dict[str, Any]],
        predicted_completion: Optional[float],
        stagnation: Optional[str],
        regression: bool,
    ) -> None:
        """Display task progress with plain text formatting."""
        print("\n" + "=" * 60)
        print("TASK PROGRESS")
        print("=" * 60)
        print(f"Task: {task_id}")
        print(f"Progress: {progress:.1f}%")

        # Add metrics if available
        if metrics:
            print("\nMetrics:")
            if "lines_added" in metrics:
                print(f"  Lines Added: {metrics['lines_added']}")
            if "tests_passing" in metrics:
                test_str = f"  Tests Passing: {metrics['tests_passing']}"
                if "tests_total" in metrics:
                    test_str += f"/{metrics['tests_total']}"
                print(test_str)

        # Add prediction if available
        if predicted_completion:
            hours = int(predicted_completion // 3600)
            minutes = int((predicted_completion % 3600) // 60)
            print(f"\nEstimated Time: {hours}h {minutes}m remaining")

        # Add alerts
        if stagnation == "warning":
            print("\n⚠️  Stagnation Warning: No progress for multiple operations")
        elif stagnation == "critical":
            print("\n🔴 Critical Stagnation: No progress for extended period")

        if regression:
            print("\n🔴 Regression Detected: Progress has decreased")

        print("=" * 60 + "\n")

    def display_session_progress(
        self,
        session_metrics: Dict[str, Any],
        historical: Optional[List[Dict[str, Any]]] = None,
        predicted_completion: Optional[float] = None,
    ) -> None:
        """
        Display progress for session.

        Args:
            session_metrics: Session progress metrics
            historical: Optional historical progress data for trends
            predicted_completion: Optional predicted completion time in seconds
        """
        if self.use_rich and self.console:
            self._display_rich_session_progress(
                session_metrics, historical, predicted_completion
            )
        else:
            self._display_plain_session_progress(
                session_metrics, historical, predicted_completion
            )

    def _display_rich_session_progress(
        self,
        session_metrics: Dict[str, Any],
        historical: Optional[List[Dict[str, Any]]],
        predicted_completion: Optional[float],
    ) -> None:
        """Display session progress with rich formatting."""
        session_text = Text()

        # Task metrics
        tasks_completed = session_metrics.get("tasks_completed", 0)
        tasks_failed = session_metrics.get("tasks_failed", 0)
        total_tasks = tasks_completed + tasks_failed
        success_rate = (
            (tasks_completed / total_tasks * 100) if total_tasks > 0 else 100.0
        )

        session_text.append("Tasks: ", style="white")
        session_text.append(f"{tasks_completed} completed", style="green")
        session_text.append(
            f" | {tasks_failed} failed\n", style="red"
        )
        session_text.append(f"Success Rate: {success_rate:.1f}%\n", style="cyan")

        # Error metrics
        errors_encountered = session_metrics.get("errors_encountered", 0)
        errors_resolved = session_metrics.get("errors_resolved", 0)
        session_text.append(
            f"Errors: {errors_resolved}/{errors_encountered} resolved\n", style="cyan"
        )

        # Efficiency metrics
        operations_per_hour = session_metrics.get("operations_per_hour", 0.0)
        session_text.append(f"Operations/Hour: {operations_per_hour:.1f}\n", style="cyan")

        # Code metrics
        lines_written = session_metrics.get("total_lines_written", 0)
        tests_added = session_metrics.get("total_tests_added", 0)
        session_text.append(f"Lines Written: {lines_written}\n", style="cyan")
        session_text.append(f"Tests Added: {tests_added}\n", style="cyan")

        # Add prediction if available
        if predicted_completion:
            hours = int(predicted_completion // 3600)
            minutes = int((predicted_completion % 3600) // 60)
            session_text.append(
                f"\nEstimated Completion: {hours}h {minutes}m\n", style="blue"
            )

        # Create panel
        panel = Panel(
            session_text,
            title="📊 Session Progress",
            border_style="blue",
            padding=(1, 2),
        )

        self.console.print(panel)

        # Display historical trends if available
        if historical and len(historical) > 1:
            self._display_rich_historical_trends(historical)

    def _display_plain_session_progress(
        self,
        session_metrics: Dict[str, Any],
        historical: Optional[List[Dict[str, Any]]],
        predicted_completion: Optional[float],
    ) -> None:
        """Display session progress with plain text formatting."""
        print("\n" + "=" * 60)
        print("SESSION PROGRESS")
        print("=" * 60)

        # Task metrics
        tasks_completed = session_metrics.get("tasks_completed", 0)
        tasks_failed = session_metrics.get("tasks_failed", 0)
        total_tasks = tasks_completed + tasks_failed
        success_rate = (
            (tasks_completed / total_tasks * 100) if total_tasks > 0 else 100.0
        )

        print(f"Tasks: {tasks_completed} completed | {tasks_failed} failed")
        print(f"Success Rate: {success_rate:.1f}%")

        # Error metrics
        errors_encountered = session_metrics.get("errors_encountered", 0)
        errors_resolved = session_metrics.get("errors_resolved", 0)
        print(f"Errors: {errors_resolved}/{errors_encountered} resolved")

        # Efficiency metrics
        operations_per_hour = session_metrics.get("operations_per_hour", 0.0)
        print(f"Operations/Hour: {operations_per_hour:.1f}")

        # Code metrics
        lines_written = session_metrics.get("total_lines_written", 0)
        tests_added = session_metrics.get("total_tests_added", 0)
        print(f"Lines Written: {lines_written}")
        print(f"Tests Added: {tests_added}")

        # Add prediction if available
        if predicted_completion:
            hours = int(predicted_completion // 3600)
            minutes = int((predicted_completion % 3600) // 60)
            print(f"\nEstimated Completion: {hours}h {minutes}m")

        print("=" * 60 + "\n")

        # Display historical trends if available
        if historical and len(historical) > 1:
            self._display_plain_historical_trends(historical)

    def display_project_progress(
        self,
        project_metrics: Dict[str, Any],
        historical: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """
        Display progress for project.

        Args:
            project_metrics: Project progress metrics
            historical: Optional historical progress data for trends
        """
        if self.use_rich and self.console:
            self._display_rich_project_progress(project_metrics, historical)
        else:
            self._display_plain_project_progress(project_metrics, historical)

    def _display_rich_project_progress(
        self,
        project_metrics: Dict[str, Any],
        historical: Optional[List[Dict[str, Any]]],
    ) -> None:
        """Display project progress with rich formatting."""
        project_text = Text()

        # Feature metrics
        features_total = project_metrics.get("features_total", 0)
        features_completed = project_metrics.get("features_completed", 0)
        feature_pct = (
            (features_completed / features_total * 100)
            if features_total > 0
            else 100.0
        )

        project_text.append("Features: ", style="white")
        project_text.append(f"{features_completed}/{features_total}", style="cyan")
        project_text.append(f" ({feature_pct:.1f}%)\n", style="green")

        # Issue metrics
        issues_total = project_metrics.get("issues_total", 0)
        issues_resolved = project_metrics.get("issues_resolved", 0)
        issue_pct = (
            (issues_resolved / issues_total * 100) if issues_total > 0 else 100.0
        )
        project_text.append(f"Issues: {issues_resolved}/{issues_total} ({issue_pct:.1f}%)\n", style="cyan")

        # Milestone metrics
        milestones_total = project_metrics.get("milestones_total", 0)
        milestones_completed = project_metrics.get("milestones_completed", 0)
        milestone_pct = (
            (milestones_completed / milestones_total * 100)
            if milestones_total > 0
            else 100.0
        )
        project_text.append(f"Milestones: {milestones_completed}/{milestones_total} ({milestone_pct:.1f}%)\n", style="cyan")

        # Quality metrics
        code_coverage = project_metrics.get("overall_code_coverage", 0.0)
        bug_rate = project_metrics.get("bug_rate", 0.0)
        health_score = project_metrics.get("health_score", 0.0)

        project_text.append(f"\nCode Coverage: {code_coverage:.1f}%\n", style="cyan")
        project_text.append(f"Bug Rate: {bug_rate:.1f}%\n", style="cyan")
        project_text.append(f"Health Score: {health_score:.1f}/100\n", style="cyan")

        # Color code health score
        health_color = "green" if health_score >= 80 else "yellow" if health_score >= 60 else "red"
        project_text.append(f"Status: ", style="white")
        project_text.append(
            f"{'Excellent' if health_score >= 80 else 'Good' if health_score >= 60 else 'Needs Improvement'}\n",
            style=f"bold {health_color}",
        )

        # Create panel
        panel = Panel(
            project_text,
            title="📊 Project Progress",
            border_style="cyan",
            padding=(1, 2),
        )

        self.console.print(panel)

        # Display historical trends if available
        if historical and len(historical) > 1:
            self._display_rich_historical_trends(historical)

    def _display_plain_project_progress(
        self,
        project_metrics: Dict[str, Any],
        historical: Optional[List[Dict[str, Any]]],
    ) -> None:
        """Display project progress with plain text formatting."""
        print("\n" + "=" * 60)
        print("PROJECT PROGRESS")
        print("=" * 60)

        # Feature metrics
        features_total = project_metrics.get("features_total", 0)
        features_completed = project_metrics.get("features_completed", 0)
        feature_pct = (
            (features_completed / features_total * 100)
            if features_total > 0
            else 100.0
        )
        print(f"Features: {features_completed}/{features_total} ({feature_pct:.1f}%)")

        # Issue metrics
        issues_total = project_metrics.get("issues_total", 0)
        issues_resolved = project_metrics.get("issues_resolved", 0)
        issue_pct = (
            (issues_resolved / issues_total * 100) if issues_total > 0 else 100.0
        )
        print(f"Issues: {issues_resolved}/{issues_total} ({issue_pct:.1f}%)")

        # Milestone metrics
        milestones_total = project_metrics.get("milestones_total", 0)
        milestones_completed = project_metrics.get("milestones_completed", 0)
        milestone_pct = (
            (milestones_completed / milestones_total * 100)
            if milestones_total > 0
            else 100.0
        )
        print(f"Milestones: {milestones_completed}/{milestones_total} ({milestone_pct:.1f}%)")

        # Quality metrics
        code_coverage = project_metrics.get("overall_code_coverage", 0.0)
        bug_rate = project_metrics.get("bug_rate", 0.0)
        health_score = project_metrics.get("health_score", 0.0)

        print(f"\nCode Coverage: {code_coverage:.1f}%")
        print(f"Bug Rate: {bug_rate:.1f}%")
        print(f"Health Score: {health_score:.1f}/100")

        # Color code health status
        health_status = (
            "Excellent" if health_score >= 80 else "Good" if health_score >= 60 else "Needs Improvement"
        )
        print(f"Status: {health_status}")

        print("=" * 60 + "\n")

        # Display historical trends if available
        if historical and len(historical) > 1:
            self._display_plain_historical_trends(historical)

    def _display_rich_historical_trends(
        self, historical: List[Dict[str, Any]]
    ) -> None:
        """Display historical progress trends with rich formatting."""
        if not historical or len(historical) < 2:
            return

        table = Table(title="📈 Historical Trends", show_header=True, header_style="bold cyan")
        table.add_column("Time", style="dim")
        table.add_column("Progress", style="cyan")
        table.add_column("Trend", justify="center")

        for i, entry in enumerate(historical[-10:]):  # Show last 10 entries
            timestamp = entry.get("timestamp", "")
            if isinstance(timestamp, str):
                from datetime import datetime

                try:
                    dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                    timestamp = dt.strftime("%H:%M:%S")
                except:
                    timestamp = timestamp[:8] if len(timestamp) >= 8 else timestamp

            progress = entry.get("progress", 0.0)
            progress_str = f"{progress:.1f}%"

            # Determine trend
            if i == 0:
                trend = "—"
                trend_color = "dim"
            else:
                prev_progress = historical[-10:][i - 1].get("progress", 0.0)
                if progress > prev_progress:
                    trend = "↑"
                    trend_color = "green"
                elif progress < prev_progress:
                    trend = "↓"
                    trend_color = "red"
                else:
                    trend = "→"
                    trend_color = "yellow"

            table.add_row(str(timestamp), progress_str, f"[{trend_color}]{trend}[/{trend_color}]")

        self.console.print(table)

    def _display_plain_historical_trends(
        self, historical: List[Dict[str, Any]]
    ) -> None:
        """Display historical progress trends with plain text formatting."""
        if not historical or len(historical) < 2:
            return

        print("\n" + "-" * 60)
        print("HISTORICAL TRENDS")
        print("-" * 60)

        for i, entry in enumerate(historical[-10:]):  # Show last 10 entries
            timestamp = entry.get("timestamp", "")
            if isinstance(timestamp, str):
                try:
                    from datetime import datetime

                    dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                    timestamp = dt.strftime("%H:%M:%S")
                except:
                    timestamp = timestamp[:8] if len(timestamp) >= 8 else timestamp

            progress = entry.get("progress", 0.0)

            # Determine trend
            if i == 0:
                trend = "—"
            else:
                prev_progress = historical[-10:][i - 1].get("progress", 0.0)
                if progress > prev_progress:
                    trend = "↑"
                elif progress < prev_progress:
                    trend = "↓"
                else:
                    trend = "→"

            print(f"{timestamp}: {progress:.1f}% {trend}")

        print("-" * 60 + "\n")

    def display_alerts(
        self, alerts: List[Dict[str, Any]], severity: Optional[str] = None
    ) -> None:
        """
        Display progress alerts.

        Args:
            alerts: List of alert dictionaries
            severity: Optional severity filter (info, warning, error, critical)
        """
        if not alerts:
            return

        filtered_alerts = alerts
        if severity:
            filtered_alerts = [a for a in alerts if a.get("severity") == severity]

        if not filtered_alerts:
            return

        if self.use_rich and self.console:
            self._display_rich_alerts(filtered_alerts)
        else:
            self._display_plain_alerts(filtered_alerts)

    def _display_rich_alerts(self, alerts: List[Dict[str, Any]]) -> None:
        """Display alerts with rich formatting."""
        table = Table(title="⚠️  Alerts", show_header=True, header_style="bold cyan")
        table.add_column("Time", style="dim")
        table.add_column("Severity")
        table.add_column("Type")
        table.add_column("Message")

        for alert in alerts[-10:]:  # Show last 10 alerts
            timestamp = alert.get("timestamp", "")
            if isinstance(timestamp, str):
                from datetime import datetime

                try:
                    dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                    timestamp = dt.strftime("%H:%M:%S")
                except:
                    timestamp = timestamp[:8] if len(timestamp) >= 8 else timestamp

            severity = alert.get("severity", "info")
            alert_type = alert.get("type", "")
            message = alert.get("message", "")

            # Color code severity
            severity_color = {
                "info": "blue",
                "warning": "yellow",
                "error": "red",
                "critical": "bold red",
            }.get(severity, "white")

            table.add_row(
                str(timestamp), f"[{severity_color}]{severity}[/{severity_color}]", alert_type, message
            )

        self.console.print(table)

    def _display_plain_alerts(self, alerts: List[Dict[str, Any]]) -> None:
        """Display alerts with plain text formatting."""
        print("\n" + "=" * 60)
        print("ALERTS")
        print("=" * 60)

        for alert in alerts[-10:]:  # Show last 10 alerts
            timestamp = alert.get("timestamp", "")
            if isinstance(timestamp, str):
                try:
                    from datetime import datetime

                    dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                    timestamp = dt.strftime("%H:%M:%S")
                except:
                    timestamp = timestamp[:8] if len(timestamp) >= 8 else timestamp

            severity = alert.get("severity", "info").upper()
            alert_type = alert.get("type", "")
            message = alert.get("message", "")

            print(f"[{timestamp}] {severity}: {alert_type}")
            print(f"  {message}")

        print("=" * 60 + "\n")


def create_progress_visualizer(use_rich: Optional[bool] = None) -> ProgressVisualizer:
    """
    Factory function to create a progress visualizer.

    Args:
        use_rich: Force use of rich library (None = auto-detect)

    Returns:
        ProgressVisualizer instance
    """
    return ProgressVisualizer(use_rich)
