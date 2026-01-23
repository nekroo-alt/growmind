"""
Test suite for error classification and taxonomy (Task 4.1)
"""

import pytest
from v2.core.error_handling import (
    ErrorCategory,
    ErrorSource,
    ErrorSeverity,
    ErrorCode,
    L4DError,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMAuthenticationError,
    LLMQuotaExceededError,
    DatabaseLockedError,
    DatabaseConnectionError,
    DatabaseCorruptionError,
    FileNotFoundError,
    FilePermissionDeniedError,
    GitConflictError,
    GitMergeFailedError,
    NetworkConnectionError,
    SystemResourceExhaustedError,
    get_recovery_strategy,
    classify_exception,
    is_retryable,
    is_user_action_required,
    is_critical,
)


class TestErrorEnums:
    """Test error enumeration values."""

    def test_error_categories(self):
        """Test error category enum values."""
        assert ErrorCategory.TRANSIENT.value == "transient"
        assert ErrorCategory.PERMANENT.value == "permanent"
        assert ErrorCategory.RETRYABLE.value == "retryable"
        assert ErrorCategory.USER_ACTION_REQUIRED.value == "user_action_required"

    def test_error_sources(self):
        """Test error source enum values."""
        assert ErrorSource.LLM.value == "llm"
        assert ErrorSource.DATABASE.value == "database"
        assert ErrorSource.FILE_SYSTEM.value == "file_system"
        assert ErrorSource.GIT.value == "git"
        assert ErrorSource.USER.value == "user"
        assert ErrorSource.NETWORK.value == "network"
        assert ErrorSource.SYSTEM.value == "system"
        assert ErrorSource.UNKNOWN.value == "unknown"

    def test_error_severities(self):
        """Test error severity enum values."""
        assert ErrorSeverity.INFO.value == "info"
        assert ErrorSeverity.WARNING.value == "warning"
        assert ErrorSeverity.ERROR.value == "error"
        assert ErrorSeverity.CRITICAL.value == "critical"

    def test_error_codes(self):
        """Test error code enum values."""
        assert ErrorCode.LLM_RATE_LIMIT.value == "LLM_RATE_LIMIT"
        assert ErrorCode.DB_LOCKED.value == "DB_LOCKED"
        assert ErrorCode.FILE_NOT_FOUND.value == "FILE_NOT_FOUND"
        assert ErrorCode.GIT_CONFLICT.value == "GIT_CONFLICT"


class TestL4DError:
    """Test base L4DError class."""

    def test_error_initialization(self):
        """Test basic error initialization."""
        error = L4DError("Test error message")
        assert error.message == "Test error message"
        assert error.code == ErrorCode.UNKNOWN_ERROR
        assert error.category == ErrorCategory.PERMANENT
        assert error.source == ErrorSource.UNKNOWN
        assert error.severity == ErrorSeverity.ERROR

    def test_error_with_all_parameters(self):
        """Test error initialization with all parameters."""
        context = {"task_id": 42, "file_path": "test.py"}
        error = L4DError(
            message="Test error",
            code=ErrorCode.LLM_RATE_LIMIT,
            category=ErrorCategory.TRANSIENT,
            source=ErrorSource.LLM,
            severity=ErrorSeverity.WARNING,
            context=context,
            recovery_strategy="Retry later",
        )
        assert error.message == "Test error"
        assert error.code == ErrorCode.LLM_RATE_LIMIT
        assert error.category == ErrorCategory.TRANSIENT
        assert error.source == ErrorSource.LLM
        assert error.severity == ErrorSeverity.WARNING
        assert error.context == context
        assert error.recovery_strategy == "Retry later"

    def test_error_string_representation(self):
        """Test error string representation."""
        error = L4DError(
            message="Test error",
            code=ErrorCode.LLM_RATE_LIMIT,
            recovery_strategy="Retry later",
        )
        error_str = str(error)
        assert "[LLM_RATE_LIMIT]" in error_str
        assert "Test error" in error_str
        assert "Recovery:" in error_str

    def test_error_to_dict(self):
        """Test error serialization to dictionary."""
        error = L4DError(
            message="Test error", code=ErrorCode.LLM_RATE_LIMIT, context={"task_id": 42}
        )
        error_dict = error.to_dict()
        assert error_dict["message"] == "Test error"
        assert error_dict["code"] == "LLM_RATE_LIMIT"
        assert error_dict["category"] == "permanent"
        assert error_dict["context"] == {"task_id": 42}
        assert "timestamp" in error_dict


class TestLLMErrors:
    """Test LLM-specific error classes."""

    def test_llm_rate_limit_error(self):
        """Test LLM rate limit error."""
        error = LLMRateLimitError()
        assert error.code == ErrorCode.LLM_RATE_LIMIT
        assert error.category == ErrorCategory.TRANSIENT
        assert error.source == ErrorSource.LLM
        assert error.severity == ErrorSeverity.WARNING
        assert "rate limit" in error.recovery_strategy.lower()
        assert is_retryable(error)

    def test_llm_timeout_error(self):
        """Test LLM timeout error."""
        error = LLMTimeoutError()
        assert error.code == ErrorCode.LLM_TIMEOUT
        assert error.category == ErrorCategory.TRANSIENT
        assert error.source == ErrorSource.LLM
        assert error.severity == ErrorSeverity.WARNING
        assert is_retryable(error)

    def test_llm_authentication_error(self):
        """Test LLM authentication error."""
        error = LLMAuthenticationError()
        assert error.code == ErrorCode.LLM_AUTHENTICATION_FAILED
        assert error.category == ErrorCategory.PERMANENT
        assert error.source == ErrorSource.LLM
        assert error.severity == ErrorSeverity.ERROR
        assert not is_retryable(error)

    def test_llm_quota_exceeded_error(self):
        """Test LLM quota exceeded error."""
        error = LLMQuotaExceededError()
        assert error.code == ErrorCode.LLM_QUOTA_EXCEEDED
        assert error.category == ErrorCategory.PERMANENT
        assert error.source == ErrorSource.LLM
        assert error.severity == ErrorSeverity.ERROR
        assert not is_retryable(error)


class TestDatabaseErrors:
    """Test database-specific error classes."""

    def test_database_locked_error(self):
        """Test database locked error."""
        error = DatabaseLockedError()
        assert error.code == ErrorCode.DB_LOCKED
        assert error.category == ErrorCategory.RETRYABLE
        assert error.source == ErrorSource.DATABASE
        assert error.severity == ErrorSeverity.WARNING
        assert is_retryable(error)

    def test_database_connection_error(self):
        """Test database connection error."""
        error = DatabaseConnectionError()
        assert error.code == ErrorCode.DB_CONNECTION_FAILED
        assert error.category == ErrorCategory.TRANSIENT
        assert error.source == ErrorSource.DATABASE
        assert error.severity == ErrorSeverity.ERROR
        assert is_retryable(error)

    def test_database_corruption_error(self):
        """Test database corruption error."""
        error = DatabaseCorruptionError()
        assert error.code == ErrorCode.DB_CORRUPTION
        assert error.category == ErrorCategory.PERMANENT
        assert error.source == ErrorSource.DATABASE
        assert error.severity == ErrorSeverity.CRITICAL
        assert not is_retryable(error)
        assert is_critical(error)


class TestFileSystemErrors:
    """Test file system-specific error classes."""

    def test_file_not_found_error(self):
        """Test file not found error."""
        error = FileNotFoundError()
        assert error.code == ErrorCode.FILE_NOT_FOUND
        assert error.category == ErrorCategory.USER_ACTION_REQUIRED
        assert error.source == ErrorSource.FILE_SYSTEM
        assert error.severity == ErrorSeverity.ERROR
        assert is_user_action_required(error)
        assert not is_retryable(error)

    def test_file_permission_denied_error(self):
        """Test file permission denied error."""
        error = FilePermissionDeniedError()
        assert error.code == ErrorCode.FILE_PERMISSION_DENIED
        assert error.category == ErrorCategory.USER_ACTION_REQUIRED
        assert error.source == ErrorSource.FILE_SYSTEM
        assert error.severity == ErrorSeverity.ERROR
        assert is_user_action_required(error)


class TestGitErrors:
    """Test git-specific error classes."""

    def test_git_conflict_error(self):
        """Test git conflict error."""
        error = GitConflictError()
        assert error.code == ErrorCode.GIT_CONFLICT
        assert error.category == ErrorCategory.USER_ACTION_REQUIRED
        assert error.source == ErrorSource.GIT
        assert error.severity == ErrorSeverity.WARNING
        assert is_user_action_required(error)

    def test_git_merge_failed_error(self):
        """Test git merge failed error."""
        error = GitMergeFailedError()
        assert error.code == ErrorCode.GIT_MERGE_FAILED
        assert error.category == ErrorCategory.PERMANENT
        assert error.source == ErrorSource.GIT
        assert error.severity == ErrorSeverity.ERROR


class TestNetworkErrors:
    """Test network-specific error classes."""

    def test_network_connection_error(self):
        """Test network connection error."""
        error = NetworkConnectionError()
        assert error.code == ErrorCode.NETWORK_CONNECTION_FAILED
        assert error.category == ErrorCategory.TRANSIENT
        assert error.source == ErrorSource.NETWORK
        assert error.severity == ErrorSeverity.WARNING
        assert is_retryable(error)


class TestSystemErrors:
    """Test system-specific error classes."""

    def test_system_resource_exhausted_error(self):
        """Test system resource exhausted error."""
        error = SystemResourceExhaustedError()
        assert error.code == ErrorCode.SYSTEM_RESOURCE_EXHAUSTED
        assert error.category == ErrorCategory.PERMANENT
        assert error.source == ErrorSource.SYSTEM
        assert error.severity == ErrorSeverity.CRITICAL
        assert is_critical(error)
        assert not is_retryable(error)


class TestRecoveryStrategies:
    """Test recovery strategy functionality."""

    def test_get_recovery_strategy_known_error(self):
        """Test getting recovery strategy for known error."""
        strategy = get_recovery_strategy(ErrorCode.LLM_RATE_LIMIT)
        assert "retry" in strategy.lower()
        assert "backoff" in strategy.lower()

    def test_get_recovery_strategy_unknown_error(self):
        """Test getting recovery strategy for unknown error."""
        strategy = get_recovery_strategy(ErrorCode.UNKNOWN_ERROR)
        assert "unknown" in strategy.lower()
        assert "contact support" in strategy.lower()


class TestErrorClassification:
    """Test exception classification functionality."""

    def test_classify_database_locked_error(self):
        """Test classification of database locked error."""
        exception = Exception("database is locked")
        error = classify_exception(exception)
        assert isinstance(error, DatabaseLockedError)
        assert error.code == ErrorCode.DB_LOCKED

    def test_classify_database_connection_error(self):
        """Test classification of database connection error."""
        exception = Exception("database connection failed")
        error = classify_exception(exception)
        assert isinstance(error, DatabaseConnectionError)
        assert error.code == ErrorCode.DB_CONNECTION_FAILED

    def test_classify_file_not_found_error(self):
        """Test classification of file not found error."""
        exception = FileNotFoundError("File not found")
        error = classify_exception(exception)
        assert isinstance(error, FileNotFoundError)
        assert error.code == ErrorCode.FILE_NOT_FOUND

    def test_classify_file_not_found_string(self):
        """Test classification of file not found from string."""
        exception = Exception("file not found: test.py")
        error = classify_exception(exception)
        assert isinstance(error, FileNotFoundError)
        assert error.code == ErrorCode.FILE_NOT_FOUND

    def test_classify_permission_error(self):
        """Test classification of permission error."""
        exception = Exception("Permission denied")
        error = classify_exception(exception)
        assert isinstance(error, FilePermissionDeniedError)
        assert error.code == ErrorCode.FILE_PERMISSION_DENIED

    def test_classify_network_error(self):
        """Test classification of network error."""
        exception = Exception("Network connection failed")
        error = classify_exception(exception)
        assert isinstance(error, NetworkConnectionError)
        assert error.code == ErrorCode.NETWORK_CONNECTION_FAILED

    def test_classify_timeout_error(self):
        """Test classification of timeout error."""
        exception = Exception("Request timed out")
        error = classify_exception(exception)
        assert error.code == ErrorCode.NETWORK_CONNECTION_FAILED
        assert "timed out" in error.message.lower()

    def test_classify_unknown_error(self):
        """Test classification of unknown error."""
        exception = Exception("Unknown error occurred")
        error = classify_exception(exception)
        assert isinstance(error, L4DError)
        assert error.code == ErrorCode.UNKNOWN_ERROR
        assert error.category == ErrorCategory.PERMANENT

    def test_classify_with_context(self):
        """Test classification with context."""
        exception = Exception("database is locked")
        context = {"task_id": 42, "operation": "save"}
        error = classify_exception(exception, context)
        assert error.context == context


class TestErrorUtilityFunctions:
    """Test error utility functions."""

    def test_is_retryable_transient_error(self):
        """Test is_retryable with transient error."""
        error = LLMRateLimitError()
        assert is_retryable(error) is True

    def test_is_retryable_retryable_error(self):
        """Test is_retryable with retryable error."""
        error = DatabaseLockedError()
        assert is_retryable(error) is True

    def test_is_retryable_permanent_error(self):
        """Test is_retryable with permanent error."""
        error = LLMAuthenticationError()
        assert is_retryable(error) is False

    def test_is_user_action_required(self):
        """Test is_user_action_required."""
        error = FileNotFoundError()
        assert is_user_action_required(error) is True

        error = LLMRateLimitError()
        assert is_user_action_required(error) is False

    def test_is_critical(self):
        """Test is_critical."""
        error = DatabaseCorruptionError()
        assert is_critical(error) is True

        error = LLMRateLimitError()
        assert is_critical(error) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
