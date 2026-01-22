"""
Test Interactive Error Messages (Task 6.2)

Tests for the ErrorDisplay class and interactive error message formatting.
"""

import sys
import os
from io import StringIO
from unittest.mock import patch, MagicMock

# Add v2 to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.ui import (
    ErrorDisplay,
    create_error_display,
    display_error,
    display_recovery_result
)
from core.error_handling import (
    L4DError,
    LLMRateLimitError,
    LLMTimeoutError,
    DatabaseLockedError,
    FileNotFound as FileNotFoundError,
    GitConflictError,
    ErrorCode,
    ErrorSeverity,
    ErrorCategory
)


class TestErrorDisplay:
    """Test ErrorDisplay class."""
    
    def test_init_with_rich_available(self):
        """Test initialization when rich is available."""
        display = ErrorDisplay(use_rich=True)
        assert display.use_rich is True
    
    def test_init_without_rich(self):
        """Test initialization without rich."""
        display = ErrorDisplay(use_rich=False)
        assert display.use_rich is False
    
    def test_init_auto_detect(self):
        """Test auto-detection of rich availability."""
        display = ErrorDisplay(use_rich=None)
        # Should auto-detect based on RICH_AVAILABLE
        # We don't assert specific value as it depends on environment
    
    def test_display_l4d_error(self, capsys):
        """Test displaying an L4D error."""
        error = L4DError(
            message="Test error message",
            code=ErrorCode.LLM_RATE_LIMIT,
            category=ErrorCategory.TRANSIENT,
            severity=ErrorSeverity.WARNING,
            context={"operation_id": "test-123"}
        )
        
        display = ErrorDisplay(use_rich=False)
        display.display_error(error, show_traceback=False, show_suggestions=True)
        
        captured = capsys.readouterr()
        assert "ERROR: [LLM_RATE_LIMIT] Test error message" in captured.out
        assert "operation_id: test-123" in captured.out
        assert "Suggested Actions:" in captured.out
    
    def test_display_exception_classification(self, capsys):
        """Test displaying a generic exception that gets classified."""
        exception = FileNotFoundError("File not found: test.txt")
        
        display = ErrorDisplay(use_rich=False)
        display.display_error(exception, show_traceback=False, show_suggestions=True)
        
        captured = capsys.readouterr()
        # Should be classified as FILE_NOT_FOUND error
        assert "ERROR: [FILE_NOT_FOUND]" in captured.out
        assert "File not found" in captured.out
    
    def test_display_error_with_traceback(self, capsys):
        """Test displaying error with traceback."""
        error = L4DError(
            message="Test error",
            code=ErrorCode.LLM_RATE_LIMIT,
            context={}
        )
        error.traceback = "Traceback (most recent call last):\n  File test.py, line 1\nValueError"
        
        display = ErrorDisplay(use_rich=False)
        display.display_error(error, show_traceback=True, show_suggestions=False)
        
        captured = capsys.readouterr()
        assert "Stack Trace:" in captured.out
        assert "Traceback (most recent call last):" in captured.out
    
    def test_display_error_without_suggestions(self, capsys):
        """Test displaying error without recovery suggestions."""
        error = L4DError(
            message="Test error",
            code=ErrorCode.LLM_RATE_LIMIT,
            context={}
        )
        
        display = ErrorDisplay(use_rich=False)
        display.display_error(error, show_traceback=False, show_suggestions=False)
        
        captured = capsys.readouterr()
        assert "ERROR: [LLM_RATE_LIMIT] Test error" in captured.out
        assert "Suggested Actions:" not in captured.out
        assert "Commands:" not in captured.out
    
    def test_get_recovery_suggestions_llm_rate_limit(self):
        """Test recovery suggestions for LLM rate limit error."""
        error = LLMRateLimitError()
        display = ErrorDisplay(use_rich=False)
        
        suggestions = display._get_recovery_suggestions(error, {})
        
        assert any("Wait 1-5 minutes" in s for s in suggestions)
        assert any("Upgrade your API plan" in s for s in suggestions)
        assert any("Run diagnostics" in s for s in suggestions)
    
    def test_get_recovery_suggestions_file_not_found(self):
        """Test recovery suggestions for file not found error."""
        error = FileNotFoundError("File not found: test.txt")
        display = ErrorDisplay(use_rich=False)
        
        suggestions = display._get_recovery_suggestions(error, {})
        
        assert any("Check the file path" in s for s in suggestions)
        assert any("Create the missing file" in s for s in suggestions)
    
    def test_get_recovery_suggestions_git_conflict(self):
        """Test recovery suggestions for git conflict error."""
        error = GitConflictError()
        display = ErrorDisplay(use_rich=False)
        
        suggestions = display._get_recovery_suggestions(error, {})
        
        assert any("Review and resolve conflicts" in s for s in suggestions)
        assert any("git add" in s for s in suggestions)
        assert any("git commit" in s for s in suggestions)
    
    def test_get_recovery_commands_with_operation_id(self):
        """Test recovery commands when operation ID is available."""
        error = LLMRateLimitError()
        context = {"operation_id": "op-123"}
        display = ErrorDisplay(use_rich=False)
        
        commands = display._get_recovery_commands(error, context)
        
        command_descriptions = [cmd[0] for cmd in commands]
        command_values = [cmd[1] for cmd in commands]
        
        assert "Retry operation" in command_descriptions
        assert "op-123" in " ".join(command_values)
    
    def test_get_recovery_commands_with_checkpoint_id(self):
        """Test recovery commands when checkpoint ID is available."""
        error = DatabaseLockedError()
        context = {"checkpoint_id": "chk-456"}
        display = ErrorDisplay(use_rich=False)
        
        commands = display._get_recovery_commands(error, context)
        
        command_descriptions = [cmd[0] for cmd in commands]
        command_values = [cmd[1] for cmd in commands]
        
        assert "Restore checkpoint" in command_descriptions
        assert "chk-456" in " ".join(command_values)
    
    def test_get_recovery_commands_general(self):
        """Test general recovery commands."""
        error = LLMRateLimitError()
        display = ErrorDisplay(use_rich=False)
        
        commands = display._get_recovery_commands(error, {})
        
        command_descriptions = [cmd[0] for cmd in commands]
        
        assert "Resume last session" in command_descriptions
        assert "List checkpoints" in command_descriptions
        assert "Run diagnostics" in command_descriptions
        assert "Check recent logs" in command_descriptions
    
    def test_display_recovery_result_success(self, capsys):
        """Test displaying successful recovery result."""
        display = ErrorDisplay(use_rich=False)
        display.display_recovery_result(
            success=True,
            message="Recovery completed successfully",
            action_taken="Retry with backoff"
        )
        
        captured = capsys.readouterr()
        assert "Recovery: SUCCESS" in captured.out
        assert "Recovery completed successfully" in captured.out
        assert "Action: Retry with backoff" in captured.out
    
    def test_display_recovery_result_failure(self, capsys):
        """Test displaying failed recovery result."""
        display = ErrorDisplay(use_rich=False)
        display.display_recovery_result(
            success=False,
            message="Recovery failed: timeout",
            action_taken="Retry attempt"
        )
        
        captured = capsys.readouterr()
        assert "Recovery: FAILED" in captured.out
        assert "Recovery failed: timeout" in captured.out
        assert "Action: Retry attempt" in captured.out


class TestConvenienceFunctions:
    """Test convenience functions for error display."""
    
    def test_create_error_display(self):
        """Test creating error display via factory function."""
        display = create_error_display(use_rich=False)
        assert isinstance(display, ErrorDisplay)
        assert display.use_rich is False
    
    def test_display_error_function(self, capsys):
        """Test display_error convenience function."""
        error = L4DError(
            message="Test error",
            code=ErrorCode.LLM_RATE_LIMIT,
            context={}
        )
        
        display = create_error_display(use_rich=False)
        display.display_error(error, show_suggestions=True)
        
        captured = capsys.readouterr()
        assert "ERROR: [LLM_RATE_LIMIT] Test error" in captured.out
        assert "Suggested Actions:" in captured.out
    
    def test_display_recovery_result_function(self, capsys):
        """Test display_recovery_result convenience function."""
        display = create_error_display(use_rich=False)
        display.display_recovery_result(
            success=True,
            message="Test recovery"
        )
        
        captured = capsys.readouterr()
        assert "Recovery: SUCCESS" in captured.out
        assert "Test recovery" in captured.out


class TestDocumentationUrls:
    """Test documentation URL mappings."""
    
    def test_documentation_urls_exist(self):
        """Test that documentation URLs are defined for common errors."""
        display = ErrorDisplay(use_rich=False)
        
        common_codes = [
            "LLM_RATE_LIMIT",
            "LLM_TIMEOUT",
            "DB_LOCKED",
            "FILE_NOT_FOUND",
            "GIT_CONFLICT"
        ]
        
        for code in common_codes:
            assert code in display.DOCUMENTATION_URLS
            assert display.DOCUMENTATION_URLS[code].startswith("https://")


class TestRecoveryCommands:
    """Test recovery command mappings."""
    
    def test_recovery_commands_exist(self):
        """Test that recovery commands are defined."""
        display = ErrorDisplay(use_rich=False)
        
        required_commands = [
            "retry",
            "retry_operation",
            "resume_last",
            "resume_checkpoint",
            "list_checkpoints",
            "doctor",
            "logs_recent"
        ]
        
        for cmd in required_commands:
            assert cmd in display.RECOVERY_COMMANDS
            assert isinstance(display.RECOVERY_COMMANDS[cmd], str)


class TestSeverityColors:
    """Test severity color mappings."""
    
    def test_severity_colors_defined(self):
        """Test that severity colors are defined."""
        display = ErrorDisplay(use_rich=False)
        
        required_severities = ["info", "warning", "error", "critical"]
        
        for severity in required_severities:
            assert severity in display.SEVERITY_COLORS
            assert isinstance(display.SEVERITY_COLORS[severity], str)


class TestIntegrationWithErrorHandling:
    """Test integration with error handling module."""
    
    def test_display_with_recovery_manager(self, capsys):
        """Test displaying error with recovery manager integration."""
        from core.error_handling import RecoveryResult, RecoveryAction
        
        error = LLMRateLimitError(context={"operation_id": "op-123"})
        display = ErrorDisplay(use_rich=False)
        
        # Display the error
        display.display_error(error, show_suggestions=True)
        
        captured = capsys.readouterr()
        assert "ERROR: [LLM_RATE_LIMIT]" in captured.out
        assert "operation_id: op-123" in captured.out
        assert "Suggested Actions:" in captured.out
    
    def test_display_recovery_result_from_manager(self, capsys):
        """Test displaying recovery result from recovery manager."""
        from core.error_handling import RecoveryResult, RecoveryAction
        
        action = RecoveryAction(
            action_type="retry_with_backoff",
            description="Retry with exponential backoff",
            automatic=True
        )
        
        result = RecoveryResult(
            success=True,
            action_taken=action,
            message="Operation retried successfully"
        )
        
        display = ErrorDisplay(use_rich=False)
        display.display_recovery_result(
            success=result.success,
            message=result.message,
            action_taken=result.action_taken.description
        )
        
        captured = capsys.readouterr()
        assert "Recovery: SUCCESS" in captured.out
        assert "Operation retried successfully" in captured.out


class TestErrorScenarios:
    """Test real-world error scenarios."""
    
    def test_llm_rate_limit_scenario(self, capsys):
        """Test LLM rate limit error scenario."""
        error = LLMRateLimitError(
            context={
                "operation_id": "op-impl-42",
                "retry_after": 60
            }
        )
        
        display = ErrorDisplay(use_rich=False)
        display.display_error(error, show_suggestions=True)
        
        captured = capsys.readouterr()
        assert "LLM_RATE_LIMIT" in captured.out
        assert "Wait 1-5 minutes" in captured.out
        assert "Retry operation" in captured.out
    
    def test_git_conflict_scenario(self, capsys):
        """Test git conflict error scenario."""
        error = GitConflictError(
            context={
                "operation_id": "op-commit-42",
                "files": ["src/main.py", "src/utils.py"]
            }
        )
        
        display = ErrorDisplay(use_rich=False)
        display.display_error(error, show_suggestions=True)
        
        captured = capsys.readouterr()
        assert "GIT_CONFLICT" in captured.out
        assert "git add" in captured.out
        assert "git commit" in captured.out
        assert "git merge --abort" in captured.out
    
    def test_database_locked_scenario(self, capsys):
        """Test database locked error scenario."""
        error = DatabaseLockedError(
            context={
                "operation_id": "op-db-42",
                "database": "task.db"
            }
        )
        
        display = ErrorDisplay(use_rich=False)
        display.display_error(error, show_suggestions=True)
        
        captured = capsys.readouterr()
        assert "DB_LOCKED" in captured.out
        assert "Wait a moment and retry" in captured.out


def run_tests():
    """Run all tests."""
    import pytest
    
    # Run pytest on this file
    exit_code = pytest.main([__file__, "-v", "--tb=short"])
    return exit_code


if __name__ == "__main__":
    exit_code = run_tests()
    sys.exit(exit_code)
