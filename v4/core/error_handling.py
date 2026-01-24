"""
Error Classification and Taxonomy for L4D V3

This module defines a comprehensive error taxonomy for better error handling,
categorization, and recovery strategies across the L4D system.

It also implements retry logic with exponential backoff for transient errors.
"""

from enum import Enum
from typing import Optional, Dict, Any, Callable, TypeVar, List, Tuple
from datetime import datetime
import traceback
import time
import random
import logging
from functools import wraps
from threading import RLock

# Set up logger
logger = logging.getLogger(__name__)

T = TypeVar("T")


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
        recovery_strategy: Optional[str] = None,
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
            "traceback": self.traceback,
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
            **kwargs,
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
            **kwargs,
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
            **kwargs,
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
            **kwargs,
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
            **kwargs,
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
            **kwargs,
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
            **kwargs,
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
            **kwargs,
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
            **kwargs,
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
            **kwargs,
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
            **kwargs,
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
            **kwargs,
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
            **kwargs,
        )


class MaxRetriesExceededError(L4DError):
    """Error raised when max retry attempts are exceeded."""

    def __init__(self, message: str = "Max retry attempts exceeded", **kwargs):
        super().__init__(
            message=message,
            code=ErrorCode.UNKNOWN_ERROR,
            category=ErrorCategory.PERMANENT,
            source=ErrorSource.SYSTEM,
            severity=ErrorSeverity.ERROR,
            recovery_strategy="Check underlying error and adjust retry policy",
            **kwargs,
        )


# ============================================================================
# Retry Logic with Exponential Backoff
# ============================================================================


class RetryConfig:
    """Configuration for retry behavior."""

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        jitter_factor: float = 0.5,
        retry_on_errors: Optional[List[ErrorCode]] = None,
        retry_on_categories: Optional[List[ErrorCategory]] = None,
    ):
        """
        Initialize retry configuration.

        Args:
            max_attempts: Maximum number of retry attempts (including first attempt)
            base_delay: Base delay in seconds before first retry
            max_delay: Maximum delay in seconds between retries
            exponential_base: Base for exponential backoff (default: 2.0)
            jitter: Whether to add random jitter to delays
            jitter_factor: Jitter factor (0.5 = ±50%)
            retry_on_errors: List of specific error codes to retry on (None = all retryable)
            retry_on_categories: List of error categories to retry on (None = all retryable)
        """
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.jitter_factor = jitter_factor
        self.retry_on_errors = retry_on_errors or []
        self.retry_on_categories = retry_on_categories or []
        self._lock = RLock()

    def should_retry(self, error: L4DError) -> bool:
        """
        Determine if an error should be retried.

        Args:
            error: The error to check

        Returns:
            True if error should be retried, False otherwise
        """
        with self._lock:
            # Check if error is retryable by category
            if self.retry_on_categories:
                if error.category not in self.retry_on_categories:
                    return False
            elif not is_retryable(error):
                return False

            # Check if error code is in retry list
            if self.retry_on_errors:
                return error.code in self.retry_on_errors

            return True

    def calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay for a retry attempt using exponential backoff.

        Args:
            attempt: Attempt number (0-based)

        Returns:
            Delay in seconds
        """
        with self._lock:
            # Calculate exponential backoff delay
            delay = min(
                self.base_delay * (self.exponential_base**attempt), self.max_delay
            )

            # Add jitter if enabled
            if self.jitter:
                jitter_amount = delay * self.jitter_factor
                jittered = delay + random.uniform(-jitter_amount, jitter_amount)
                return max(0, jittered)

            return delay


class CircuitBreaker:
    """
    Circuit breaker pattern to prevent cascading failures.

    Opens the circuit when failure threshold is reached, preventing
    further calls until reset after cooldown period.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        cooldown_period: float = 60.0,
        half_open_max_calls: int = 3,
    ):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            cooldown_period: Time in seconds to wait before attempting recovery
            half_open_max_calls: Number of calls allowed in half-open state
        """
        self.failure_threshold = failure_threshold
        self.cooldown_period = cooldown_period
        self.half_open_max_calls = half_open_max_calls

        self._lock = RLock()
        self._state = "closed"  # closed, open, half-open
        self._failure_count = 0
        self._last_failure_time = 0.0
        self._half_open_call_count = 0

    def can_call(self) -> bool:
        """
        Check if a call can proceed through the circuit breaker.

        Returns:
            True if call can proceed, False if circuit is open
        """
        with self._lock:
            now = time.time()

            if self._state == "closed":
                return True

            elif self._state == "open":
                # Check if cooldown period has elapsed
                if now - self._last_failure_time >= self.cooldown_period:
                    logger.info("Circuit breaker entering half-open state")
                    self._state = "half-open"
                    self._half_open_call_count = 0
                    return True
                return False

            elif self._state == "half-open":
                # Allow limited calls in half-open state
                return self._half_open_call_count < self.half_open_max_calls

            return False

    def record_success(self):
        """Record a successful call."""
        with self._lock:
            if self._state == "half-open":
                self._half_open_call_count += 1
                if self._half_open_call_count >= self.half_open_max_calls:
                    logger.info("Circuit breaker closing after successful calls")
                    self._state = "closed"
                    self._failure_count = 0
            elif self._state == "closed":
                self._failure_count = 0

    def record_failure(self):
        """Record a failed call."""
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()

            if self._state == "half-open":
                logger.warning(
                    "Circuit breaker opening due to failure in half-open state"
                )
                self._state = "open"
                self._half_open_call_count = 0
            elif self._failure_count >= self.failure_threshold:
                logger.warning(
                    f"Circuit breaker opening after {self._failure_count} failures"
                )
                self._state = "open"

    def reset(self):
        """Reset circuit breaker to closed state."""
        with self._lock:
            logger.info("Circuit breaker reset to closed state")
            self._state = "closed"
            self._failure_count = 0
            self._last_failure_time = 0.0
            self._half_open_call_count = 0


class RetryMetrics:
    """Track retry statistics for monitoring and analysis."""

    def __init__(self):
        """Initialize retry metrics."""
        self._lock = RLock()
        self._total_calls: int = 0
        self._successful_calls: int = 0
        self._failed_calls: int = 0
        self._total_retries: int = 0
        self._retry_attempts_by_error: Dict[str, int] = {}
        self._total_retry_time: float = 0.0

    def record_call(self):
        """Record a function call."""
        with self._lock:
            self._total_calls += 1

    def record_success(self, retries: int = 0):
        """Record a successful call."""
        with self._lock:
            self._successful_calls += 1
            self._total_retries += retries

    def record_failure(self, error: L4DError, retries: int):
        """Record a failed call."""
        with self._lock:
            self._failed_calls += 1
            self._total_retries += retries

            # Track retries by error code
            error_key = error.code.value
            self._retry_attempts_by_error[error_key] = (
                self._retry_attempts_by_error.get(error_key, 0) + retries
            )

    def record_retry_time(self, delay: float):
        """Record time spent in retry delays."""
        with self._lock:
            self._total_retry_time += delay

    def get_stats(self) -> Dict[str, Any]:
        """Get retry statistics."""
        with self._lock:
            success_rate = (
                self._successful_calls / self._total_calls * 100
                if self._total_calls > 0
                else 0.0
            )

            avg_retries = (
                self._total_retries / self._total_calls
                if self._total_calls > 0
                else 0.0
            )

            return {
                "total_calls": self._total_calls,
                "successful_calls": self._successful_calls,
                "failed_calls": self._failed_calls,
                "success_rate": round(success_rate, 2),
                "total_retries": self._total_retries,
                "avg_retries_per_call": round(avg_retries, 2),
                "total_retry_time": round(self._total_retry_time, 2),
                "retry_attempts_by_error": self._retry_attempts_by_error.copy(),
            }

    def reset(self):
        """Reset all metrics."""
        with self._lock:
            self._total_calls = 0
            self._successful_calls = 0
            self._failed_calls = 0
            self._total_retries = 0
            self._retry_attempts_by_error.clear()
            self._total_retry_time = 0.0


# Global retry metrics
_global_retry_metrics = RetryMetrics()


def retry_with_config(
    retry_config: Optional[RetryConfig] = None,
    circuit_breaker: Optional[CircuitBreaker] = None,
    on_retry_callback: Optional[Callable[[L4DError, int, float], None]] = None,
    record_metrics: bool = True,
) -> Callable:
    """
    Decorator for retrying functions with exponential backoff.

    Args:
        retry_config: Retry configuration (uses defaults if None)
        circuit_breaker: Circuit breaker instance (disabled if None)
        on_retry_callback: Optional callback called before each retry
        record_metrics: Whether to record retry metrics globally

    Returns:
        Decorator function

    Example:
        @retry_with_config(
            retry_config=RetryConfig(max_attempts=3, base_delay=2.0),
            circuit_breaker=CircuitBreaker(failure_threshold=5)
        )
        def call_llm():
            ...
    """
    if retry_config is None:
        retry_config = RetryConfig()

    metrics = _global_retry_metrics if record_metrics else None

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            if metrics:
                metrics.record_call()

            if circuit_breaker and not circuit_breaker.can_call():
                logger.warning("Circuit breaker is open, rejecting call")
                raise L4DError(
                    message="Circuit breaker is open, call rejected",
                    code=ErrorCode.UNKNOWN_ERROR,
                    category=ErrorCategory.PERMANENT,
                    severity=ErrorSeverity.ERROR,
                    recovery_strategy="Wait for circuit breaker cooldown or reset",
                )

            last_exception = None
            total_delay = 0.0

            for attempt in range(retry_config.max_attempts):
                try:
                    result = func(*args, **kwargs)

                    if circuit_breaker:
                        circuit_breaker.record_success()

                    if metrics:
                        metrics.record_success(retries=attempt)

                    if attempt > 0:
                        logger.info(
                            f"Function '{func.__name__}' succeeded after {attempt} retries"
                        )

                    return result

                except Exception as e:
                    # Classify exception
                    l4d_error = (
                        classify_exception(e) if not isinstance(e, L4DError) else e
                    )
                    last_exception = l4d_error

                    # Check if we should retry
                    if (
                        attempt < retry_config.max_attempts - 1
                        and retry_config.should_retry(l4d_error)
                    ):

                        delay = retry_config.calculate_delay(attempt)
                        total_delay += delay

                        logger.warning(
                            f"Attempt {attempt + 1}/{retry_config.max_attempts} failed "
                            f"for '{func.__name__}': {l4d_error.message}. "
                            f"Retrying in {delay:.2f} seconds..."
                        )

                        # Call retry callback if provided
                        if on_retry_callback:
                            on_retry_callback(l4d_error, attempt, delay)

                        # Record retry time
                        if metrics:
                            metrics.record_retry_time(delay)

                        # Wait before retry
                        time.sleep(delay)
                    else:
                        # Record failure
                        if metrics:
                            metrics.record_failure(l4d_error, attempt)

                        if circuit_breaker:
                            circuit_breaker.record_failure()

                        # Raise error with retry context
                        if attempt > 0:
                            logger.error(
                                f"Function '{func.__name__}' failed after {attempt} retries"
                            )

                        raise l4d_error from e

            # Should not reach here, but just in case
            raise MaxRetriesExceededError(
                message=f"Max retry attempts exceeded for '{func.__name__}'",
                context={
                    "attempts": retry_config.max_attempts,
                    "total_delay": total_delay,
                },
                cause=last_exception,
            )

        return wrapper

    return decorator


def retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    on_retry: Optional[Callable[[L4DError, int, float], None]] = None,
    enable_circuit_breaker: bool = False,
    circuit_failure_threshold: int = 5,
    circuit_cooldown: float = 60.0,
) -> Callable:
    """
    Simplified decorator for retrying functions with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts (including first attempt)
        base_delay: Base delay in seconds before first retry
        max_delay: Maximum delay in seconds between retries
        exponential_base: Base for exponential backoff (default: 2.0)
        jitter: Whether to add random jitter to delays
        on_retry: Optional callback called before each retry
        enable_circuit_breaker: Whether to enable circuit breaker pattern
        circuit_failure_threshold: Failure threshold for circuit breaker
        circuit_cooldown: Cooldown period for circuit breaker

    Returns:
        Decorator function

    Example:
        @retry(max_attempts=3, base_delay=2.0)
        def call_llm():
            ...
    """
    retry_config = RetryConfig(
        max_attempts=max_attempts,
        base_delay=base_delay,
        max_delay=max_delay,
        exponential_base=exponential_base,
        jitter=jitter,
    )

    circuit_breaker = None
    if enable_circuit_breaker:
        circuit_breaker = CircuitBreaker(
            failure_threshold=circuit_failure_threshold,
            cooldown_period=circuit_cooldown,
        )

    return retry_with_config(
        retry_config=retry_config,
        circuit_breaker=circuit_breaker,
        on_retry_callback=on_retry,
    )


def get_retry_metrics() -> Dict[str, Any]:
    """
    Get global retry metrics.

    Returns:
        Dictionary containing retry statistics
    """
    return _global_retry_metrics.get_stats()


def reset_retry_metrics():
    """Reset global retry metrics."""
    _global_retry_metrics.reset()


# Pre-configured retry policies for common use cases
RETRY_POLICY_LLAPI = RetryConfig(
    max_attempts=3,
    base_delay=2.0,
    max_delay=30.0,
    exponential_base=2.0,
    jitter=True,
    retry_on_categories=[ErrorCategory.TRANSIENT, ErrorCategory.RETRYABLE],
)

RETRY_POLICY_DATABASE = RetryConfig(
    max_attempts=3,
    base_delay=0.5,
    max_delay=10.0,
    exponential_base=2.0,
    jitter=True,
    retry_on_categories=[ErrorCategory.RETRYABLE],
)

RETRY_POLICY_NETWORK = RetryConfig(
    max_attempts=5,
    base_delay=1.0,
    max_delay=60.0,
    exponential_base=2.0,
    jitter=True,
    retry_on_categories=[ErrorCategory.TRANSIENT],
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
        code, "Unknown error - check logs for details and contact support if needed"
    )


def classify_exception(
    exception: Exception, context: Optional[Dict[str, Any]] = None
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
    if (
        isinstance(exception, FileNotFoundError)
        or "file not found" in str(exception).lower()
    ):
        return FileNotFoundError(cause=exception, context=context)
    if "permission" in str(exception).lower():
        return FilePermissionDeniedError(cause=exception, context=context)

    # Timeout errors (check before network errors)
    if "timeout" in str(exception).lower() or "timed out" in str(exception).lower():
        if "llm" in str(exception).lower():
            return LLMTimeoutError(cause=exception, context=context)
        return NetworkConnectionError(
            message="Request timed out", cause=exception, context=context
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
        cause=exception,
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


# ============================================================================
# Error Recovery Strategies
# ============================================================================


class RecoveryAction:
    """Represents a recovery action that can be taken."""

    def __init__(
        self,
        action_type: str,
        description: str,
        automatic: bool = False,
        command: Optional[str] = None,
        requires_user_input: bool = False,
    ):
        """
        Initialize a recovery action.

        Args:
            action_type: Type of action (retry, rollback, manual, etc.)
            description: Human-readable description of the action
            automatic: Whether this action can be performed automatically
            command: Optional command to execute for manual recovery
            requires_user_input: Whether this action requires user confirmation
        """
        self.action_type = action_type
        self.description = description
        self.automatic = automatic
        self.command = command
        self.requires_user_input = requires_user_input

    def to_dict(self) -> Dict[str, Any]:
        """Convert recovery action to dictionary."""
        return {
            "action_type": self.action_type,
            "description": self.description,
            "automatic": self.automatic,
            "command": self.command,
            "requires_user_input": self.requires_user_input,
        }


class RecoveryResult:
    """Represents the result of a recovery attempt."""

    def __init__(
        self,
        success: bool,
        action_taken: Optional[RecoveryAction] = None,
        error: Optional[Exception] = None,
        message: str = "",
    ):
        """
        Initialize a recovery result.

        Args:
            success: Whether recovery was successful
            action_taken: The recovery action that was taken
            error: Error that occurred during recovery (if any)
            message: Additional message about the recovery
        """
        self.success = success
        self.action_taken = action_taken
        self.error = error
        self.message = message
        self.timestamp = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert recovery result to dictionary."""
        return {
            "success": self.success,
            "action_taken": self.action_taken.to_dict() if self.action_taken else None,
            "error": str(self.error) if self.error else None,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
        }


class RecoveryManager:
    """
    Manages error recovery strategies and automatic recovery.

    This class provides automatic recovery for transient errors and
    suggests recovery steps for user-action errors. It integrates
    with CheckpointManager for rollback on unrecoverable errors.
    """

    def __init__(self, checkpoint_manager=None):
        """
        Initialize recovery manager.

        Args:
            checkpoint_manager: Optional CheckpointManager instance for rollback
        """
        self.checkpoint_manager = checkpoint_manager
        self._lock = RLock()
        self._recovery_history: List[Dict[str, Any]] = []

    def recover(
        self,
        error: L4DError,
        context: Optional[Dict[str, Any]] = None,
        allow_rollback: bool = True,
    ) -> RecoveryResult:
        """
        Attempt to recover from an error.

        Args:
            error: The error to recover from
            context: Additional context for recovery
            allow_rollback: Whether to allow rollback to checkpoint

        Returns:
            RecoveryResult with outcome and action taken
        """
        context = context or {}

        # Log recovery attempt
        logger.info(f"Attempting recovery for error: {error.code.value}")

        # Determine recovery strategy based on error code
        if error.code == ErrorCode.DB_LOCKED:
            return self._recover_database_lock(error, context)
        elif error.code == ErrorCode.LLM_RATE_LIMIT:
            return self._recover_llm_rate_limit(error, context)
        elif error.code == ErrorCode.LLM_TIMEOUT:
            return self._recover_llm_timeout(error, context)
        elif error.code == ErrorCode.NETWORK_CONNECTION_FAILED:
            return self._recover_network_error(error, context)
        elif error.code == ErrorCode.NETWORK_TIMEOUT:
            return self._recover_network_error(error, context)
        elif error.code in [
            ErrorCode.FILE_NOT_FOUND,
            ErrorCode.FILE_PERMISSION_DENIED,
            ErrorCode.GIT_CONFLICT,
            ErrorCode.GIT_MERGE_FAILED,
        ]:
            return self._suggest_user_action(error, context)
        elif is_critical(error) and allow_rollback and self.checkpoint_manager:
            return self._recover_with_rollback(error, context)
        else:
            return self._suggest_manual_recovery(error, context)

    def _recover_database_lock(
        self, error: L4DError, context: Dict[str, Any]
    ) -> RecoveryResult:
        """
        Recover from database lock by retrying with backoff.

        Args:
            error: The database lock error
            context: Additional context

        Returns:
            RecoveryResult
        """
        action = RecoveryAction(
            action_type="retry_with_backoff",
            description="Retry database operation with exponential backoff",
            automatic=True,
        )

        try:
            # Suggest retry with backoff
            logger.info("Database locked, suggest retry with backoff")
            message = (
                f"Database is locked. This is usually temporary. "
                f"Suggested action: Retry the operation. "
                f"Use retry decorator with RETRY_POLICY_DATABASE for automatic retry."
            )

            result = RecoveryResult(success=True, action_taken=action, message=message)

            self._record_recovery(error, result)
            return result

        except Exception as e:
            result = RecoveryResult(
                success=False,
                action_taken=action,
                error=e,
                message=f"Failed to recover from database lock: {e}",
            )
            self._record_recovery(error, result)
            return result

    def _recover_llm_rate_limit(
        self, error: L4DError, context: Dict[str, Any]
    ) -> RecoveryResult:
        """
        Recover from LLM rate limit by waiting and retrying.

        Args:
            error: The LLM rate limit error
            context: Additional context

        Returns:
            RecoveryResult
        """
        action = RecoveryAction(
            action_type="wait_and_retry",
            description="Wait for rate limit to reset and retry",
            automatic=False,
            requires_user_input=True,
        )

        try:
            # Calculate suggested wait time
            wait_time = self._calculate_rate_limit_wait(error)

            message = (
                f"LLM API rate limit exceeded. "
                f"Suggested wait time: {wait_time:.0f} seconds ({wait_time/60:.1f} minutes). "
                f"Retry after waiting, or upgrade your API plan for higher limits. "
                f"Command: sleep {wait_time:.0f} && <retry your command>"
            )

            result = RecoveryResult(
                success=False,  # Requires user to wait and retry
                action_taken=action,
                message=message,
            )

            self._record_recovery(error, result)
            return result

        except Exception as e:
            result = RecoveryResult(
                success=False,
                action_taken=action,
                error=e,
                message=f"Failed to recover from rate limit: {e}",
            )
            self._record_recovery(error, result)
            return result

    def _recover_llm_timeout(
        self, error: L4DError, context: Dict[str, Any]
    ) -> RecoveryResult:
        """
        Recover from LLM timeout by retrying with backoff.

        Args:
            error: The LLM timeout error
            context: Additional context

        Returns:
            RecoveryResult
        """
        action = RecoveryAction(
            action_type="retry_with_backoff",
            description="Retry LLM call with exponential backoff",
            automatic=True,
        )

        try:
            message = (
                f"LLM API request timed out. "
                f"Suggested action: Retry with exponential backoff. "
                f"Check your network connection. "
                f"Use retry decorator with RETRY_POLICY_LLAPI for automatic retry."
            )

            result = RecoveryResult(success=True, action_taken=action, message=message)

            self._record_recovery(error, result)
            return result

        except Exception as e:
            result = RecoveryResult(
                success=False,
                action_taken=action,
                error=e,
                message=f"Failed to recover from LLM timeout: {e}",
            )
            self._record_recovery(error, result)
            return result

    def _recover_network_error(
        self, error: L4DError, context: Dict[str, Any]
    ) -> RecoveryResult:
        """
        Recover from network error by retrying with backoff.

        Args:
            error: The network error
            context: Additional context

        Returns:
            RecoveryResult
        """
        action = RecoveryAction(
            action_type="retry_with_backoff",
            description="Retry network operation with exponential backoff",
            automatic=True,
        )

        try:
            message = (
                f"Network error: {error.message}. "
                f"Suggested action: Retry with exponential backoff. "
                f"Check your network connection. "
                f"Use retry decorator with RETRY_POLICY_NETWORK for automatic retry."
            )

            result = RecoveryResult(success=True, action_taken=action, message=message)

            self._record_recovery(error, result)
            return result

        except Exception as e:
            result = RecoveryResult(
                success=False,
                action_taken=action,
                error=e,
                message=f"Failed to recover from network error: {e}",
            )
            self._record_recovery(error, result)
            return result

    def _suggest_user_action(
        self, error: L4DError, context: Dict[str, Any]
    ) -> RecoveryResult:
        """
        Suggest user action for errors requiring manual intervention.

        Args:
            error: The error requiring user action
            context: Additional context

        Returns:
            RecoveryResult
        """
        action = RecoveryAction(
            action_type="user_action_required",
            description=error.recovery_strategy or "User action required",
            automatic=False,
            requires_user_input=True,
        )

        # Generate specific suggestions based on error code
        suggestions = self._get_user_action_suggestions(error, context)

        message = f"{error.message}\n\n" f"Recovery actions required:\n"

        for i, suggestion in enumerate(suggestions, 1):
            message += f"{i}. {suggestion}\n"

        result = RecoveryResult(
            success=False, action_taken=action, message=message  # Requires user action
        )

        self._record_recovery(error, result)
        return result

    def _get_user_action_suggestions(
        self, error: L4DError, context: Dict[str, Any]
    ) -> List[str]:
        """
        Get user action suggestions for a specific error.

        Args:
            error: The error
            context: Additional context

        Returns:
            List of suggestion strings
        """
        if error.code == ErrorCode.FILE_NOT_FOUND:
            suggestions = [
                "Check the file path in the error message",
                "Create the missing file if it's required",
                "Run: l4-dev doctor to check project integrity",
            ]
            if context and context.get("file_path"):
                suggestions.append(f"Verify file exists: ls -la {context['file_path']}")
            return suggestions

        elif error.code == ErrorCode.FILE_PERMISSION_DENIED:
            suggestions = [
                "Check file permissions and ownership",
                "Run: ls -la <file_path> to see permissions",
                "Try: chmod +r <file_path> to add read permission",
                "Check you have necessary permissions for the directory",
            ]
            return suggestions

        elif error.code == ErrorCode.GIT_CONFLICT:
            suggestions = [
                "Review and resolve merge conflicts in affected files",
                "After resolving conflicts: git add <resolved_files>",
                "Continue with: git commit",
                "Or abort merge: git merge --abort",
            ]
            return suggestions

        elif error.code == ErrorCode.GIT_MERGE_FAILED:
            suggestions = [
                "Check git status to see merge state",
                "Review merge conflicts if any",
                "Try: git status",
                "Try: git merge --abort to cancel the merge",
                "Resolve issues manually and retry",
            ]
            return suggestions

        else:
            return [
                "Review the error message and context",
                "Check system logs for more details",
                "Run: l4-dev doctor to diagnose issues",
                "Contact support if issue persists",
            ]

    def _recover_with_rollback(
        self, error: L4DError, context: Dict[str, Any]
    ) -> RecoveryResult:
        """
        Recover from critical error by rolling back to checkpoint.

        Args:
            error: The critical error
            context: Additional context

        Returns:
            RecoveryResult
        """
        if not self.checkpoint_manager:
            return RecoveryResult(
                success=False, message="Checkpoint manager not available for rollback"
            )

        action = RecoveryAction(
            action_type="rollback_to_checkpoint",
            description="Rollback to last known good checkpoint",
            automatic=True,
        )

        try:
            # Get latest checkpoint
            checkpoints = self.checkpoint_manager.list_checkpoints(limit=1)

            if not checkpoints:
                result = RecoveryResult(
                    success=False,
                    action_taken=action,
                    message="No checkpoints available for rollback",
                )
                self._record_recovery(error, result)
                return result

            latest_checkpoint = checkpoints[0]

            logger.warning(
                f"Critical error encountered: {error.code.value}. "
                f"Rolling back to checkpoint: {latest_checkpoint['id']}"
            )

            # Perform rollback
            self.checkpoint_manager.restore(latest_checkpoint["id"])

            message = (
                f"Rolled back to checkpoint {latest_checkpoint['id']} "
                f"(created at {latest_checkpoint['timestamp']}). "
                f"Error: {error.message}"
            )

            result = RecoveryResult(success=True, action_taken=action, message=message)

            self._record_recovery(error, result)
            return result

        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            result = RecoveryResult(
                success=False,
                action_taken=action,
                error=e,
                message=f"Rollback to checkpoint failed: {e}",
            )
            self._record_recovery(error, result)
            return result

    def _suggest_manual_recovery(
        self, error: L4DError, context: Dict[str, Any]
    ) -> RecoveryResult:
        """
        Suggest manual recovery for unrecoverable errors.

        Args:
            error: The error
            context: Additional context

        Returns:
            RecoveryResult
        """
        action = RecoveryAction(
            action_type="manual_recovery",
            description="Manual recovery required",
            automatic=False,
            requires_user_input=True,
        )

        message = (
            f"Error: {error.message}\n\n"
            f"Suggested recovery steps:\n"
            f"1. Check logs for more details: l4-dev logs --last 1h\n"
            f"2. Run diagnostics: l4-dev doctor\n"
            f"3. Review error context: {error.context}\n"
        )

        if error.recovery_strategy:
            message += f"4. {error.recovery_strategy}\n"

        if self.checkpoint_manager:
            message += f"5. Consider rolling back to checkpoint: l4-dev resume --last-checkpoint\n"

        result = RecoveryResult(success=False, action_taken=action, message=message)

        self._record_recovery(error, result)
        return result

    def _calculate_rate_limit_wait(self, error: L4DError) -> float:
        """
        Calculate suggested wait time for rate limit recovery.

        Args:
            error: The rate limit error

        Returns:
            Suggested wait time in seconds
        """
        # Check if error context contains retry-after
        retry_after = error.context.get("retry_after")
        if retry_after:
            try:
                return float(retry_after)
            except (ValueError, TypeError):
                pass

        # Default wait times based on error severity
        if "per minute" in str(error).lower():
            return 60.0
        elif "per hour" in str(error).lower():
            return 3600.0
        elif "per day" in str(error).lower():
            return 86400.0
        else:
            # Default to 2 minutes
            return 120.0

    def _record_recovery(self, error: L4DError, result: RecoveryResult):
        """
        Record recovery attempt for analytics.

        Args:
            error: The error that was recovered
            result: The recovery result
        """
        with self._lock:
            record = {
                "timestamp": datetime.now().isoformat(),
                "error_code": error.code.value,
                "error_category": error.category.value,
                "error_source": error.source.value,
                "action_taken": (
                    result.action_taken.action_type if result.action_taken else None
                ),
                "success": result.success,
                "automatic": (
                    result.action_taken.automatic if result.action_taken else False
                ),
            }
            self._recovery_history.append(record)

            # Keep only last 1000 records
            if len(self._recovery_history) > 1000:
                self._recovery_history = self._recovery_history[-1000:]

    def get_recovery_stats(self) -> Dict[str, Any]:
        """
        Get recovery statistics.

        Returns:
            Dictionary containing recovery statistics
        """
        with self._lock:
            if not self._recovery_history:
                return {
                    "total_recoveries": 0,
                    "automatic_recoveries": 0,
                    "manual_recoveries": 0,
                    "success_rate": 0.0,
                    "recoveries_by_error": {},
                }

            total = len(self._recovery_history)
            automatic = sum(1 for r in self._recovery_history if r["automatic"])
            successful = sum(1 for r in self._recovery_history if r["success"])

            # Group by error code
            by_error: Dict[str, Dict[str, int]] = {}
            for record in self._recovery_history:
                error_code = record["error_code"]
                if error_code not in by_error:
                    by_error[error_code] = {"count": 0, "success": 0}
                by_error[error_code]["count"] += 1
                if record["success"]:
                    by_error[error_code]["success"] += 1

            # Calculate success rates by error
            for error_code in by_error:
                count = by_error[error_code]["count"]
                success = by_error[error_code]["success"]
                by_error[error_code]["success_rate"] = (
                    round(success / count * 100, 2) if count > 0 else 0.0
                )

            return {
                "total_recoveries": total,
                "automatic_recoveries": automatic,
                "manual_recoveries": total - automatic,
                "successful_recoveries": successful,
                "success_rate": (
                    round(successful / total * 100, 2) if total > 0 else 0.0
                ),
                "recoveries_by_error": by_error,
                "history": self._recovery_history[-100:],  # Last 100 records
            }

    def generate_recovery_report(self) -> str:
        """
        Generate a human-readable recovery report.

        Returns:
            Formatted recovery report string
        """
        stats = self.get_recovery_stats()

        report = [
            "=" * 60,
            "Error Recovery Report",
            "=" * 60,
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "Summary:",
            f"  Total Recovery Attempts: {stats['total_recoveries']}",
            f"  Automatic Recoveries: {stats['automatic_recoveries']}",
            f"  Manual Recoveries: {stats['manual_recoveries']}",
            f"  Successful Recoveries: {stats['successful_recoveries']}",
            f"  Success Rate: {stats['success_rate']}%",
            "",
            "Recoveries by Error Type:",
        ]

        for error_code, error_stats in stats["recoveries_by_error"].items():
            report.append(
                f"  {error_code}: {error_stats['count']} attempts "
                f"({error_stats['success_rate']}% success)"
            )

        if stats["history"]:
            report.append("")
            report.append("Recent Recovery Attempts (last 10):")
            for record in stats["history"][-10:]:
                report.append(
                    f"  [{record['timestamp']}] {record['error_code']}: "
                    f"{record['action_taken']} - "
                    f"{'SUCCESS' if record['success'] else 'FAILED'}"
                )

        report.append("=" * 60)

        return "\n".join(report)

    def clear_history(self):
        """Clear recovery history."""
        with self._lock:
            self._recovery_history.clear()
            logger.info("Recovery history cleared")


# Global recovery manager instance
_global_recovery_manager = RecoveryManager()


def set_recovery_manager(recovery_manager: RecoveryManager):
    """
    Set the global recovery manager.

    Args:
        recovery_manager: RecoveryManager instance to use globally
    """
    global _global_recovery_manager
    _global_recovery_manager = recovery_manager


def get_recovery_manager() -> RecoveryManager:
    """
    Get the global recovery manager.

    Returns:
        Global RecoveryManager instance
    """
    return _global_recovery_manager


def recover_from_error(
    error: L4DError,
    context: Optional[Dict[str, Any]] = None,
    allow_rollback: bool = True,
) -> RecoveryResult:
    """
    Recover from an error using the global recovery manager.

    Args:
        error: The error to recover from
        context: Additional context for recovery
        allow_rollback: Whether to allow rollback to checkpoint

    Returns:
        RecoveryResult with outcome and action taken
    """
    return _global_recovery_manager.recover(error, context, allow_rollback)


def get_recovery_statistics() -> Dict[str, Any]:
    """
    Get recovery statistics from the global recovery manager.

    Returns:
        Dictionary containing recovery statistics
    """
    return _global_recovery_manager.get_recovery_stats()
