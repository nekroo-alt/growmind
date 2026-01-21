"""
Error Classification and Taxonomy for L4D V3

This module defines a comprehensive error taxonomy for better error handling,
categorization, and recovery strategies across the L4D system.
"""

from enum import Enum
from typing import Optional, Dict, Any
from datetime import datetime
import traceback


class ErrorCategory(Enum):
    """Error categories based on recovery behavior."""
    TRANSIENT = "transient"  # Temporary errors that can be retried
    PERMANENT = "permanent"  # Permanent errors that require intervention
    RETRYABLE = "retryable"  # Errors that can be automatically retried
    USER_ACTION_REQUIRED = "user_action_required"  # Requires user intervention


class ErrorSource(Enum):
    """Sources of errors in the system."""
    LLM = "llm"  # LLM API errors (rate limits, timeouts, etc.)
    DATABASE = "database"  # Database errors (locks, corruption, etc.)
    FILE_SYSTEM = "file_system"  # File system errors (not found, permissions, etc.)
    GIT = "git"  # Git operation errors (conflicts, merge issues, etc.)
    USER = "user"  # User-induced errors (invalid input, etc.)
    NETWORK = "network"  # Network errors (connection issues, etc.)
    SYSTEM = "system"  # System-level errors (resource exhaustion, etc.)
    UNKNOWN = "unknown"  # Unknown error sources


class ErrorSeverity(Enum):
    """Severity levels for errors."""
    INFO = "info"  # Informational errors (minor issues)
    WARNING = "warning"  # Warning errors (potential issues)
    ERROR = "error"  # Error conditions (problems that need attention)
    CRITICAL = "critical"  # Critical errors (system cannot continue)


class ErrorCode(Enum):
    """Error codes for common scenarios."""
    
    # LLM Errors
    LLM_RATE_LIMIT = "LLM_RATE_LIMIT"
    LLM_TIMEOUT = "LLM_TIMEOUT"
    LLM_AUTHENTICATION_FAILED = "LLM_AUTHENTICATION_FAILED"
    LLM_QUOTA_EXCEEDED = "LLM_QUOTA_EXCEEDED"
    LLM_INVALID_REQUEST = "LLM_INVALID_REQUEST"
    LLM_SERVER_ERROR = "LLM_SERVER_ERROR"
    
    # Database Errors
    DB_LOCKED = "DB_LOCKED"
    DB_CONNECTION_FAILED = "DB_CONNECTION_FAILED"
    DB_CORRUPTION = "DB_CORRUPTION"
    DB_CONSTRAINT_VIOLATION = "DB_CONSTRAINT_VIOLATION"
    DB_QUERY_FAILED = "DB_QUERY_FAILED"
    
    # File System Errors
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    FILE_PERMISSION_DENIED = "FILE_PERMISSION_DENIED"
    FILE_DISK_FULL = "FILE_DISK_FULL"
    FILE_INVALID_PATH = "FILE_INVALID_PATH"
    FILE_ALREADY_EXISTS = "FILE_ALREADY_EXISTS"
    
    # Git Errors
    GIT_CONFLICT = "GIT_CONFLICT"
    GIT_MERGE_FAILED = "GIT_MERGE_FAILED"
    GIT_NOT_REPOSITORY = "GIT_NOT_REPOSITORY"
    GIT_WORKDIR_DIRTY = "GIT_WORKDIR_DIRTY"
    GIT_REMOTE_ERROR = "GIT_REMOTE_ERROR"
    
    # Network Errors
    NETWORK_CONNECTION_FAILED = "NETWORK_CONNECTION_FAILED"
    NETWORK_TIMEOUT = "NETWORK_TIMEOUT"
    NETWORK_DNS_ERROR = "NETWORK_DNS_ERROR"
    
    # System Errors
    SYSTEM_RESOURCE_EXHAUSTED = "SYSTEM_RESOURCE_EXHAUSTED"
    SYSTEM_OUT_OF_MEMORY = "SYSTEM_OUT_OF_MEMORY"
    SYSTEM_DISK_FULL = "SYSTEM_DISK_FULL"
    
    # User Errors
    USER_INVALID_INPUT = "USER_INVALID_INPUT"
    USER_PERMISSION_DENIED = "USER_PERMISSION_DENIED"
    USER_CANCELLED = "USER_CANCELLED"
    
    # Unknown Error
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


class L4DError(Exception):
    """
    Base class for all L4D errors.
    
    Provides rich metadata for error classification and recovery.
    """
    
    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.UNKNOWN_ERROR,
        category: ErrorCategory = ErrorCategory.PERMANENT,
        source: ErrorSource = ErrorSource.UNKNOWN,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
        recovery_strategy: Optional[str] = None
    ):
        """
        Initialize an L4D error.
        
        Args:
            message: Human-readable error message
            code: Error code from ErrorCode enum
            category: Error category from ErrorCategory enum
            source: Error source from ErrorSource enum
            severity: Error severity from ErrorSeverity enum
            context: Additional context information (task_id, file_path, etc.)
            cause: The underlying exception that caused this error
            recovery_strategy: Suggested recovery strategy
        """
        super().__init__(message)
        self.message = message
        self.code = code
        self.category = category
        self.source = source
        self.severity = severity
        self.context = context or {}
        self.cause = cause
        self.recovery_strategy = recovery_strategy
        self.timestamp = datetime.now()
        self.traceback = traceback.format_exc() if cause else None
    
    def __str__(self) -> str:
        """String representation of the error."""
        parts = [f"[{self.code.value}] {self.message}"]
        if self.context:
            parts.append(f"Context: {self.context}")
        if self.recovery_strategy:
            parts.append(f"Recovery: {self.recovery_strategy}")
        return " | ".join(parts)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for serialization."""
        return {
            "message": self.message,
            "code": self.code.value,
            "category": self.category.value,
            "source": self.source.value,
            "severity": self.severity.value,
            "context": self.context,
            "recovery_strategy": self.recovery_strategy,
            "timestamp": self.timestamp.isoformat(),
            "traceback": self.traceback
        }


# LLM Error Classes
class LLMRateLimitError(L4DError):
    """Error raised when LLM API rate limit is exceeded."""
    
    def __init__(self, message: str = "LLM API rate limit exceeded", **kwargs):
        super().__init__(
            message=message,
            code=ErrorCode.LLM_RATE_LIMIT,
            category=ErrorCategory.TRANSIENT,
            source=ErrorSource.LLM,
            severity=ErrorSeverity.WARNING,
            recovery_strategy="Retry after waiting for rate limit to reset, or upgrade API plan",
            **kwargs
        )


class LLMTimeoutError(L4DError):
    """Error raised when LLM API request times out."""
    
    def __init__(self, message: str = "LLM API request timed out", **kwargs):
        super().__init__(
            message=message,
            code=ErrorCode.LLM_TIMEOUT,
            category=ErrorCategory.TRANSIENT,
            source=ErrorSource.LLM,
            severity=ErrorSeverity.WARNING,
            recovery_strategy="Retry with exponential backoff, check network connection",
            **kwargs
        )


class LLMAuthenticationError(L4DError):
    """Error raised when LLM API authentication fails."""
    
    def __init__(self, message: str = "LLM API authentication failed", **kwargs):
        super().__init__(
            message=message,
            code=ErrorCode.LLM_AUTHENTICATION_FAILED,
            category=ErrorCategory.PERMANENT,
            source=ErrorSource.LLM,
            severity=ErrorSeverity.ERROR,
            recovery_strategy="Check API key configuration and permissions",
            **kwargs
        )


class LLMQuotaExceededError(L4DError):
    """Error raised when LLM API quota is exceeded."""
    
    def __init__(self, message: str = "LLM API quota exceeded", **kwargs):
        super().__init__(
            message=message,
            code=ErrorCode.LLM_QUOTA_EXCEEDED,
            category=ErrorCategory.PERMANENT,
            source=ErrorSource.LLM,
            severity=ErrorSeverity.ERROR,
            recovery_strategy="Upgrade API plan or wait for quota reset",
            **kwargs
        )


# Database Error Classes
class DatabaseLockedError(L4DError):
    """Error raised when database is locked."""
    
    def __init__(self, message: str = "Database is locked", **kwargs):
        super().__init__(
            message=message,
            code=ErrorCode.DB_LOCKED,
            category=ErrorCategory.RETRYABLE,
            source=ErrorSource.DATABASE,
            severity=ErrorSeverity.WARNING,
            recovery_strategy="Retry with exponential backoff",
            **kwargs
        )


class DatabaseConnectionError(L4DError):
    """Error raised when database connection fails."""
    
    def __init__(self, message: str = "Database connection failed", **kwargs):
        super().__init__(
            message=message,
            code=ErrorCode.DB_CONNECTION_FAILED,
            category=ErrorCategory.TRANSIENT,
            source=ErrorSource.DATABASE,
            severity=ErrorSeverity.ERROR,
            recovery_strategy="Retry connection, check database server status",
            **kwargs
        )


class DatabaseCorruptionError(L4DError):
    """Error raised when database is corrupted."""
    
    def __init__(self, message: str = "Database is corrupted", **kwargs):
        super().__init__(
            message=message,
            code=ErrorCode.DB_CORRUPTION,
            category=ErrorCategory.PERMANENT,
            source=ErrorSource.DATABASE,
            severity=ErrorSeverity.CRITICAL,
            recovery_strategy="Restore from backup or rollback to checkpoint",
            **kwargs
        )


# File System Error Classes
class FileNotFoundError(L4DError):
    """Error raised when file is not found."""
    
    def __init__(self, message: str = "File not found", **kwargs):
        super().__init__(
            message=message,
            code=ErrorCode.FILE_NOT_FOUND,
            category=ErrorCategory.USER_ACTION_REQUIRED,
            source=ErrorSource.FILE_SYSTEM,
            severity=ErrorSeverity.ERROR,
            recovery_strategy="Check file path or create missing file",
            **kwargs
        )


class FilePermissionDeniedError(L4DError):
    """Error raised when file permission is denied."""
    
    def __init__(self, message: str = "File permission denied", **kwargs):
        super().__init__(
            message=message,
            code=ErrorCode.FILE_PERMISSION_DENIED,
            category=ErrorCategory.USER_ACTION_REQUIRED,
            source=ErrorSource.FILE_SYSTEM,
            severity=ErrorSeverity.ERROR,
            recovery_strategy="Check file permissions and ownership",
            **kwargs
        )


# Git Error Classes
class GitConflictError(L4DError):
    """Error raised when git merge conflict occurs."""
    
    def __init__(self, message: str = "Git merge conflict", **kwargs):
        super().__init__(
            message=message,
            code=ErrorCode.GIT_CONFLICT,
            category=ErrorCategory.USER_ACTION_REQUIRED,
            source=ErrorSource.GIT,
            severity=ErrorSeverity.WARNING,
            recovery_strategy="Resolve merge conflicts manually or abort merge",
            **kwargs
        )


class GitMergeFailedError(L4DError):
    """Error raised when git merge fails."""
    
    def __init__(self, message: str = "Git merge failed", **kwargs):
        super().__init__(
            message=message,
            code=ErrorCode.GIT_MERGE_FAILED,
            category=ErrorCategory.PERMANENT,
            source=ErrorSource.GIT,
            severity=ErrorSeverity.ERROR,
            recovery_strategy="Check merge conflicts or revert merge",
            **kwargs
        )


# Network Error Classes
class NetworkConnectionError(L4DError):
    """Error raised when network connection fails."""
    
    def __init__(self, message: str = "Network connection failed", **kwargs):
        super().__init__(
            message=message,
            code=ErrorCode.NETWORK_CONNECTION_FAILED,
            category=ErrorCategory.TRANSIENT,
            source=ErrorSource.NETWORK,
            severity=ErrorSeverity.WARNING,
            recovery_strategy="Retry with exponential backoff, check network",
            **kwargs
        )


# System Error Classes
class SystemResourceExhaustedError(L4DError):
    """Error raised when system resources are exhausted."""
    
    def __init__(self, message: str = "System resources exhausted", **kwargs):
        super().__init__(
            message=message,
            code=ErrorCode.SYSTEM_RESOURCE_EXHAUSTED,
            category=ErrorCategory.PERMANENT,
            source=ErrorSource.SYSTEM,
            severity=ErrorSeverity.CRITICAL,
            recovery_strategy="Free up resources or close other applications",
            **kwargs
        )


# Recovery Strategies
RECOVERY_STRATEGIES = {
    ErrorCode.LLM_RATE_LIMIT: "Retry with exponential backoff (wait 1-5 minutes)",
    ErrorCode.LLM_TIMEOUT: "Retry with exponential backoff, check network connection",
    ErrorCode.LLM_AUTHENTICATION_FAILED: "Check API key configuration and permissions",
    ErrorCode.LLM_QUOTA_EXCEEDED: "Upgrade API plan or wait for quota reset",
    ErrorCode.DB_LOCKED: "Retry with exponential backoff (max 3 attempts)",
    ErrorCode.DB_CONNECTION_FAILED: "Retry connection, check database server status",
    ErrorCode.DB_CORRUPTION: "Restore from backup or rollback to checkpoint",
    ErrorCode.FILE_NOT_FOUND: "Check file path or create missing file",
    ErrorCode.FILE_PERMISSION_DENIED: "Check file permissions and ownership",
    ErrorCode.GIT_CONFLICT: "Resolve merge conflicts manually or abort merge",
    ErrorCode.GIT_MERGE_FAILED: "Check merge conflicts or revert merge",
    ErrorCode.NETWORK_CONNECTION_FAILED: "Retry with exponential backoff, check network",
    ErrorCode.SYSTEM_RESOURCE_EXHAUSTED: "Free up resources or close other applications",
}


def get_recovery_strategy(code: ErrorCode) -> str:
    """
    Get recovery strategy for an error code.
    
    Args:
        code: Error code from ErrorCode enum
        
    Returns:
        Recovery strategy string
    """
    return RECOVERY_STRATEGIES.get(
        code,
        "Unknown error - check logs for details and contact support if needed"
    )


def classify_exception(
    exception: Exception,
    context: Optional[Dict[str, Any]] = None
) -> L4DError:
    """
    Classify a generic exception into L4D error taxonomy.
    
    Args:
        exception: The exception to classify
        context: Additional context information
        
    Returns:
        L4DError with appropriate classification
    """
    # Database errors
    if "database is locked" in str(exception).lower():
        return DatabaseLockedError(cause=exception, context=context)
    if "database" in str(exception).lower() and "connection" in str(exception).lower():
        return DatabaseConnectionError(cause=exception, context=context)
    
    # File system errors
    if isinstance(exception, FileNotFoundError) or "file not found" in str(exception).lower():
        return FileNotFoundError(cause=exception, context=context)
    if "permission" in str(exception).lower():
        return FilePermissionDeniedError(cause=exception, context=context)
    
    # Timeout errors (check before network errors)
    if "timeout" in str(exception).lower() or "timed out" in str(exception).lower():
        if "llm" in str(exception).lower():
            return LLMTimeoutError(cause=exception, context=context)
        return NetworkConnectionError(
            message="Request timed out",
            cause=exception,
            context=context
        )
    
    # Network errors
    if "connection" in str(exception).lower() or "network" in str(exception).lower():
        return NetworkConnectionError(cause=exception, context=context)
    
    # Default to unknown error
    return L4DError(
        message=str(exception),
        code=ErrorCode.UNKNOWN_ERROR,
        category=ErrorCategory.PERMANENT,
        source=ErrorSource.UNKNOWN,
        severity=ErrorSeverity.ERROR,
        context=context,
        cause=exception
    )


def is_retryable(error: L4DError) -> bool:
    """
    Check if an error is retryable.
    
    Args:
        error: L4DError instance
        
    Returns:
        True if error is retryable, False otherwise
    """
    return error.category in [ErrorCategory.TRANSIENT, ErrorCategory.RETRYABLE]


def is_user_action_required(error: L4DError) -> bool:
    """
    Check if an error requires user action.
    
    Args:
        error: L4DError instance
        
    Returns:
        True if user action is required, False otherwise
    """
    return error.category == ErrorCategory.USER_ACTION_REQUIRED


def is_critical(error: L4DError) -> bool:
    """
    Check if an error is critical.
    
    Args:
        error: L4DError instance
        
    Returns:
        True if error is critical, False otherwise
    """
    return error.severity == ErrorSeverity.CRITICAL
