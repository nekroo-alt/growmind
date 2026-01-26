"""
Test suite for Error Recovery Strategies (Task 4.4)

This test suite verifies:
- Automatic recovery for database locks
- Automatic recovery for LLM rate limits and timeouts
- Automatic recovery for transient network errors
- User action suggestions for file system errors
- User action suggestions for git errors
- Rollback to checkpoint on unrecoverable errors
- Recovery report generation
"""

import pytest
import tempfile
import os
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch

from v5.core import (
    L4DError,
    ErrorCode,
    RecoveryManager,
    RecoveryAction,
    RecoveryResult,
    DatabaseLockedError,
    LLMRateLimitError,
    LLMTimeoutError,
    NetworkConnectionError,
    FileNotFoundError,
    FilePermissionDeniedError,
    GitConflictError,
    DatabaseCorruptionError,
    recover_from_error,
    get_recovery_manager,
    set_recovery_manager,
    get_recovery_statistics,
)


class TestRecoveryAction:
    """Test RecoveryAction class."""

    def test_recovery_action_creation(self):
        """Test creating a recovery action."""
        action = RecoveryAction(
            action_type="retry",
            description="Retry the operation",
            automatic=True,
            command="retry",
            requires_user_input=False,
        )

        assert action.action_type == "retry"
        assert action.description == "Retry the operation"
        assert action.automatic is True
        assert action.command == "retry"
        assert action.requires_user_input is False

    def test_recovery_action_to_dict(self):
        """Test converting recovery action to dictionary."""
        action = RecoveryAction(
            action_type="rollback", description="Rollback to checkpoint", automatic=True
        )

        action_dict = action.to_dict()

        assert action_dict["action_type"] == "rollback"
        assert action_dict["description"] == "Rollback to checkpoint"
        assert action_dict["automatic"] is True
        assert action_dict["command"] is None
        assert action_dict["requires_user_input"] is False


class TestRecoveryResult:
    """Test RecoveryResult class."""

    def test_recovery_result_creation(self):
        """Test creating a recovery result."""
        action = RecoveryAction(action_type="retry", description="Retry")
        result = RecoveryResult(
            success=True, action_taken=action, message="Recovery successful"
        )

        assert result.success is True
        assert result.action_taken == action
        assert result.message == "Recovery successful"
        assert result.error is None
        assert isinstance(result.timestamp, datetime)

    def test_recovery_result_with_error(self):
        """Test recovery result with error."""
        action = RecoveryAction(action_type="retry", description="Retry")
        error = Exception("Recovery failed")
        result = RecoveryResult(
            success=False, action_taken=action, error=error, message="Recovery failed"
        )

        assert result.success is False
        assert result.action_taken == action
        assert result.error == error
        assert result.message == "Recovery failed"

    def test_recovery_result_to_dict(self):
        """Test converting recovery result to dictionary."""
        action = RecoveryAction(action_type="retry", description="Retry")
        result = RecoveryResult(success=True, action_taken=action, message="Success")

        result_dict = result.to_dict()

        assert result_dict["success"] is True
        assert result_dict["action_taken"]["action_type"] == "retry"
        assert result_dict["message"] == "Success"
        assert "timestamp" in result_dict


class TestRecoveryManager:
    """Test RecoveryManager class."""

    def test_recovery_manager_initialization(self):
        """Test initializing recovery manager."""
        manager = RecoveryManager()

        assert manager.checkpoint_manager is None
        assert manager._recovery_history == []

    def test_recovery_manager_with_checkpoint_manager(self):
        """Test recovery manager with checkpoint manager."""
        checkpoint_manager = Mock()
        manager = RecoveryManager(checkpoint_manager=checkpoint_manager)

        assert manager.checkpoint_manager == checkpoint_manager

    def test_recover_database_lock(self):
        """Test recovering from database lock."""
        manager = RecoveryManager()
        error = DatabaseLockedError("Database is locked")

        result = manager.recover(error)

        assert result.success is True
        assert result.action_taken.automatic is True
        assert result.action_taken.action_type == "retry_with_backoff"
        assert "retry" in result.message.lower()

    def test_recover_llm_rate_limit(self):
        """Test recovering from LLM rate limit."""
        manager = RecoveryManager()
        error = LLMRateLimitError("Rate limit exceeded", context={"retry_after": 60})

        result = manager.recover(error)

        assert result.success is False  # Requires user to wait
        assert result.action_taken.requires_user_input is True
        assert result.action_taken.action_type == "wait_and_retry"
        assert "60" in result.message

    def test_recover_llm_rate_limit_default_wait(self):
        """Test recovering from LLM rate limit with default wait time."""
        manager = RecoveryManager()
        error = LLMRateLimitError("Rate limit exceeded (per minute)")

        result = manager.recover(error)

        assert "60" in result.message  # Default 60 seconds for per-minute

    def test_recover_llm_timeout(self):
        """Test recovering from LLM timeout."""
        manager = RecoveryManager()
        error = LLMTimeoutError("LLM timeout")

        result = manager.recover(error)

        assert result.success is True
        assert result.action_taken.automatic is True
        assert result.action_taken.action_type == "retry_with_backoff"
        assert "backoff" in result.message.lower()

    def test_recover_network_error(self):
        """Test recovering from network error."""
        manager = RecoveryManager()
        error = NetworkConnectionError("Network failed")

        result = manager.recover(error)

        assert result.success is True
        assert result.action_taken.automatic is True
        assert result.action_taken.action_type == "retry_with_backoff"
        assert "network" in result.message.lower()

    def test_recover_file_not_found(self):
        """Test recovering from file not found error."""
        manager = RecoveryManager()
        error = FileNotFoundError(
            "File not found", context={"file_path": "/tmp/test.txt"}
        )

        result = manager.recover(error)

        assert result.success is False
        assert result.action_taken.requires_user_input is True
        assert result.action_taken.action_type == "user_action_required"
        assert "file path" in result.message.lower()

    def test_recover_file_permission_denied(self):
        """Test recovering from file permission denied error."""
        manager = RecoveryManager()
        error = FilePermissionDeniedError("Permission denied")

        result = manager.recover(error)

        assert result.success is False
        assert result.action_taken.requires_user_input is True
        assert result.action_taken.action_type == "user_action_required"
        assert "permission" in result.message.lower()

    def test_recover_git_conflict(self):
        """Test recovering from git conflict error."""
        manager = RecoveryManager()
        error = GitConflictError("Merge conflict")

        result = manager.recover(error)

        assert result.success is False
        assert result.action_taken.requires_user_input is True
        assert result.action_taken.action_type == "user_action_required"
        assert "merge conflict" in result.message.lower()

    def test_recover_with_rollback(self):
        """Test recovering with rollback to checkpoint."""
        checkpoint_manager = Mock()
        checkpoint_manager.list_checkpoints.return_value = [
            {"id": "chkp_123", "timestamp": "2024-01-01T00:00:00"}
        ]
        checkpoint_manager.restore = Mock()

        manager = RecoveryManager(checkpoint_manager=checkpoint_manager)
        error = DatabaseCorruptionError("Database corrupted")

        result = manager.recover(error)

        assert result.success is True
        assert result.action_taken.automatic is True
        assert result.action_taken.action_type == "rollback_to_checkpoint"
        checkpoint_manager.restore.assert_called_once_with("chkp_123")

    def test_recover_with_rollback_no_checkpoints(self):
        """Test recovering with rollback when no checkpoints available."""
        checkpoint_manager = Mock()
        checkpoint_manager.list_checkpoints.return_value = []

        manager = RecoveryManager(checkpoint_manager=checkpoint_manager)
        error = DatabaseCorruptionError("Database corrupted")

        result = manager.recover(error)

        assert result.success is False
        assert "no checkpoints" in result.message.lower()

    def test_recover_with_rollback_failure(self):
        """Test recovering with rollback when restore fails."""
        checkpoint_manager = Mock()
        checkpoint_manager.list_checkpoints.return_value = [
            {"id": "chkp_123", "timestamp": "2024-01-01T00:00:00"}
        ]
        checkpoint_manager.restore.side_effect = Exception("Restore failed")

        manager = RecoveryManager(checkpoint_manager=checkpoint_manager)
        error = DatabaseCorruptionError("Database corrupted")

        result = manager.recover(error)

        assert result.success is False
        assert result.error is not None
        assert "rollback" in result.message.lower()

    def test_suggest_manual_recovery(self):
        """Test suggesting manual recovery for unrecoverable errors."""
        manager = RecoveryManager()
        error = L4DError(
            message="Unknown error",
            code=ErrorCode.UNKNOWN_ERROR,
            recovery_strategy="Check logs",
        )

        result = manager.recover(error)

        assert result.success is False
        assert result.action_taken.action_type == "manual_recovery"
        assert "logs" in result.message.lower()

    def test_recovery_history_recording(self):
        """Test that recovery attempts are recorded."""
        manager = RecoveryManager()
        error = DatabaseLockedError("Database is locked")

        manager.recover(error)

        assert len(manager._recovery_history) == 1
        assert manager._recovery_history[0]["error_code"] == "DB_LOCKED"
        assert manager._recovery_history[0]["success"] is True
        assert manager._recovery_history[0]["automatic"] is True

    def test_get_recovery_stats_empty(self):
        """Test getting recovery stats with empty history."""
        manager = RecoveryManager()

        stats = manager.get_recovery_stats()

        assert stats["total_recoveries"] == 0
        assert stats["automatic_recoveries"] == 0
        assert stats["manual_recoveries"] == 0
        assert stats["success_rate"] == 0.0
        assert stats["recoveries_by_error"] == {}

    def test_get_recovery_stats_with_data(self):
        """Test getting recovery stats with data."""
        manager = RecoveryManager()

        # Record some recoveries
        manager.recover(DatabaseLockedError("Database locked"))
        manager.recover(LLMTimeoutError("Timeout"))
        manager.recover(FileNotFoundError("File not found"))

        stats = manager.get_recovery_stats()

        assert stats["total_recoveries"] == 3
        assert stats["automatic_recoveries"] == 2
        assert stats["manual_recoveries"] == 1
        assert stats["success_rate"] > 0
        assert "DB_LOCKED" in stats["recoveries_by_error"]

    def test_generate_recovery_report(self):
        """Test generating recovery report."""
        manager = RecoveryManager()

        # Record some recoveries
        manager.recover(DatabaseLockedError("Database locked"))
        manager.recover(LLMTimeoutError("Timeout"))

        report = manager.generate_recovery_report()

        assert "Error Recovery Report" in report
        assert "Total Recovery Attempts: 2" in report
        assert "DB_LOCKED" in report
        assert "LLM_TIMEOUT" in report

    def test_clear_recovery_history(self):
        """Test clearing recovery history."""
        manager = RecoveryManager()

        manager.recover(DatabaseLockedError("Database locked"))
        assert len(manager._recovery_history) == 1

        manager.clear_history()
        assert len(manager._recovery_history) == 0


class TestGlobalRecoveryManager:
    """Test global recovery manager functions."""

    def test_get_global_recovery_manager(self):
        """Test getting global recovery manager."""
        manager = get_recovery_manager()

        assert isinstance(manager, RecoveryManager)

    def test_set_global_recovery_manager(self):
        """Test setting global recovery manager."""
        custom_manager = RecoveryManager()
        set_recovery_manager(custom_manager)

        assert get_recovery_manager() == custom_manager

    def test_recover_from_error_global(self):
        """Test recovering from error using global function."""
        error = DatabaseLockedError("Database locked")

        result = recover_from_error(error)

        assert result.success is True
        assert result.action_taken.action_type == "retry_with_backoff"

    def test_get_recovery_statistics_global(self):
        """Test getting recovery statistics using global function."""
        # Record some recoveries
        recover_from_error(DatabaseLockedError("Database locked"))
        recover_from_error(LLMTimeoutError("Timeout"))

        stats = get_recovery_statistics()

        assert stats["total_recoveries"] >= 2


class TestUserActionSuggestions:
    """Test user action suggestions for different error types."""

    def test_file_not_found_suggestions(self):
        """Test suggestions for file not found error."""
        manager = RecoveryManager()
        error = FileNotFoundError(
            "File not found", context={"file_path": "/tmp/test.txt"}
        )

        result = manager.recover(error, context={"file_path": "/tmp/test.txt"})

        assert "file path" in result.message.lower()
        assert "l4-dev doctor" in result.message.lower()
        assert "ls -la /tmp/test.txt" in result.message

    def test_permission_denied_suggestions(self):
        """Test suggestions for permission denied error."""
        manager = RecoveryManager()
        error = FilePermissionDeniedError("Permission denied")

        result = manager.recover(error)

        assert "ls -la" in result.message
        assert "chmod" in result.message

    def test_git_conflict_suggestions(self):
        """Test suggestions for git conflict error."""
        manager = RecoveryManager()
        error = GitConflictError("Merge conflict")

        result = manager.recover(error)

        assert "git add" in result.message
        assert "git commit" in result.message
        assert "git merge --abort" in result.message


class TestRateLimitWaitTime:
    """Test rate limit wait time calculation."""

    def test_retry_after_in_context(self):
        """Test wait time calculation with retry-after in context."""
        manager = RecoveryManager()
        error = LLMRateLimitError("Rate limit exceeded", context={"retry_after": 120})

        result = manager.recover(error)

        assert "120" in result.message

    def test_per_minute_rate_limit(self):
        """Test wait time for per-minute rate limit."""
        manager = RecoveryManager()
        error = LLMRateLimitError("Rate limit exceeded (per minute)")

        result = manager.recover(error)

        assert "60 seconds" in result.message

    def test_per_hour_rate_limit(self):
        """Test wait time for per-hour rate limit."""
        manager = RecoveryManager()
        error = LLMRateLimitError("Rate limit exceeded (per hour)")

        result = manager.recover(error)

        assert "3600 seconds" in result.message or "60.0 minutes" in result.message

    def test_per_day_rate_limit(self):
        """Test wait time for per-day rate limit."""
        manager = RecoveryManager()
        error = LLMRateLimitError("Rate limit exceeded (per day)")

        result = manager.recover(error)

        assert "86400 seconds" in result.message or "1440.0 minutes" in result.message

    def test_default_wait_time(self):
        """Test default wait time when no specific info available."""
        manager = RecoveryManager()
        error = LLMRateLimitError("Rate limit exceeded")

        result = manager.recover(error)

        assert "120 seconds" in result.message or "2.0 minutes" in result.message


class TestRecoveryWithCheckpoints:
    """Test recovery integration with checkpoint manager."""

    def test_rollback_allowed(self):
        """Test rollback when allow_rollback is True."""
        checkpoint_manager = Mock()
        checkpoint_manager.list_checkpoints.return_value = [
            {"id": "chkp_123", "timestamp": "2024-01-01T00:00:00"}
        ]

        manager = RecoveryManager(checkpoint_manager=checkpoint_manager)
        error = DatabaseCorruptionError("Database corrupted")

        result = manager.recover(error, allow_rollback=True)

        assert result.success is True
        checkpoint_manager.restore.assert_called_once()

    def test_rollback_disabled(self):
        """Test no rollback when allow_rollback is False."""
        checkpoint_manager = Mock()
        checkpoint_manager.list_checkpoints.return_value = [
            {"id": "chkp_123", "timestamp": "2024-01-01T00:00:00"}
        ]

        manager = RecoveryManager(checkpoint_manager=checkpoint_manager)
        error = DatabaseCorruptionError("Database corrupted")

        result = manager.recover(error, allow_rollback=False)

        assert result.success is False
        assert "manual_recovery" in result.action_taken.action_type
        checkpoint_manager.restore.assert_not_called()

    def test_no_checkpoint_manager(self):
        """Test recovery when no checkpoint manager is available."""
        manager = RecoveryManager(checkpoint_manager=None)
        error = DatabaseCorruptionError("Database corrupted")

        result = manager.recover(error)

        assert result.success is False
        assert "manual_recovery" in result.action_taken.action_type


class TestRecoveryHistory:
    """Test recovery history management."""

    def test_history_limit(self):
        """Test that history is limited to 1000 records."""
        manager = RecoveryManager()

        # Add more than 1000 recoveries
        for i in range(1500):
            manager.recover(DatabaseLockedError(f"Database locked {i}"))

        # Should only keep last 1000
        assert len(manager._recovery_history) == 1000

    def test_history_includes_timestamp(self):
        """Test that recovery records include timestamp."""
        manager = RecoveryManager()
        error = DatabaseLockedError("Database locked")

        manager.recover(error)

        assert "timestamp" in manager._recovery_history[0]
        assert isinstance(manager._recovery_history[0]["timestamp"], str)

    def test_history_includes_all_fields(self):
        """Test that recovery records include all required fields."""
        manager = RecoveryManager()
        error = DatabaseLockedError("Database locked")

        manager.recover(error)

        record = manager._recovery_history[0]

        assert "timestamp" in record
        assert "error_code" in record
        assert "error_category" in record
        assert "error_source" in record
        assert "action_taken" in record
        assert "success" in record
        assert "automatic" in record


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
