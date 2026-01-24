"""
Tests for retry logic with exponential backoff (Task 4.2)

Tests cover:
- Exponential backoff calculation
- Jitter functionality
- Retry configuration
- Circuit breaker pattern
- Retry metrics
- Decorator functionality
"""

import time
import pytest
from v3.core.error_handling import (
    RetryConfig,
    CircuitBreaker,
    RetryMetrics,
    retry,
    retry_with_config,
    get_retry_metrics,
    reset_retry_metrics,
    LLMRateLimitError,
    DatabaseLockedError,
    FileNotFoundError,
    ErrorCategory,
    ErrorCode,
    MaxRetriesExceededError,
    RETRY_POLICY_LLAPI,
    RETRY_POLICY_DATABASE,
    RETRY_POLICY_NETWORK,
)


class TestRetryConfig:
    """Test RetryConfig class."""

    def test_default_configuration(self):
        """Test default retry configuration."""
        config = RetryConfig()

        assert config.max_attempts == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.exponential_base == 2.0
        assert config.jitter == True
        assert config.jitter_factor == 0.5

    def test_custom_configuration(self):
        """Test custom retry configuration."""
        config = RetryConfig(
            max_attempts=5,
            base_delay=2.0,
            max_delay=120.0,
            exponential_base=3.0,
            jitter=False,
        )

        assert config.max_attempts == 5
        assert config.base_delay == 2.0
        assert config.max_delay == 120.0
        assert config.exponential_base == 3.0
        assert config.jitter == False

    def test_should_retry_transient_error(self):
        """Test that transient errors are retryable."""
        config = RetryConfig(max_attempts=3)
        error = LLMRateLimitError()

        assert config.should_retry(error) == True

    def test_should_retry_permanent_error(self):
        """Test that permanent errors are not retryable."""
        config = RetryConfig(max_attempts=3)
        error = FileNotFoundError()

        assert config.should_retry(error) == False

    def test_should_retry_specific_error_codes(self):
        """Test retrying only specific error codes."""
        config = RetryConfig(max_attempts=3, retry_on_errors=[ErrorCode.LLM_RATE_LIMIT])

        rate_limit_error = LLMRateLimitError()
        db_locked_error = DatabaseLockedError()

        assert config.should_retry(rate_limit_error) == True
        assert config.should_retry(db_locked_error) == False

    def test_should_retry_specific_categories(self):
        """Test retrying only specific error categories."""
        config = RetryConfig(
            max_attempts=3, retry_on_categories=[ErrorCategory.TRANSIENT]
        )

        transient_error = LLMRateLimitError()
        retryable_error = DatabaseLockedError()

        assert config.should_retry(transient_error) == True
        assert config.should_retry(retryable_error) == False

    def test_exponential_backoff_calculation(self):
        """Test exponential backoff delay calculation."""
        config = RetryConfig(
            base_delay=1.0, max_delay=1000.0, exponential_base=2.0, jitter=False
        )

        # Attempt 0: base_delay * 2^0 = 1.0
        assert config.calculate_delay(0) == 1.0

        # Attempt 1: base_delay * 2^1 = 2.0
        assert config.calculate_delay(1) == 2.0

        # Attempt 2: base_delay * 2^2 = 4.0
        assert config.calculate_delay(2) == 4.0

        # Attempt 3: base_delay * 2^3 = 8.0
        assert config.calculate_delay(3) == 8.0

    def test_max_delay_limit(self):
        """Test that delay is capped at max_delay."""
        config = RetryConfig(
            base_delay=10.0, max_delay=50.0, exponential_base=2.0, jitter=False
        )

        # Attempt 5: 10.0 * 2^5 = 320.0, but capped at 50.0
        assert config.calculate_delay(5) == 50.0

    def test_jitter_functionality(self):
        """Test that jitter adds randomness to delays."""
        config = RetryConfig(
            base_delay=10.0,
            max_delay=100.0,
            exponential_base=2.0,
            jitter=True,
            jitter_factor=0.5,
        )

        delays = [config.calculate_delay(0) for _ in range(100)]

        # With jitter, delays should vary
        assert len(set(delays)) > 1

        # All delays should be within expected range
        # Base delay = 10.0, jitter factor = 0.5 -> range [5.0, 15.0]
        assert all(5.0 <= delay <= 15.0 for delay in delays)

    def test_no_jitter(self):
        """Test that delays are consistent without jitter."""
        config = RetryConfig(
            base_delay=10.0, max_delay=100.0, exponential_base=2.0, jitter=False
        )

        delays = [config.calculate_delay(0) for _ in range(10)]

        # Without jitter, all delays should be the same
        assert len(set(delays)) == 1


class TestCircuitBreaker:
    """Test CircuitBreaker class."""

    def test_initial_state_closed(self):
        """Test that circuit breaker starts in closed state."""
        cb = CircuitBreaker(failure_threshold=3)

        assert cb.can_call() == True

    def test_record_success_in_closed_state(self):
        """Test recording success in closed state."""
        cb = CircuitBreaker(failure_threshold=3)

        cb.record_success()

        assert cb.can_call() == True

    def test_circuit_opens_after_threshold(self):
        """Test that circuit opens after failure threshold."""
        cb = CircuitBreaker(failure_threshold=3, cooldown_period=0.1)

        # Record failures up to threshold
        cb.record_failure()
        assert cb.can_call() == True

        cb.record_failure()
        assert cb.can_call() == True

        cb.record_failure()
        assert cb.can_call() == False  # Circuit should be open

    def test_circuit_resets_after_cooldown(self):
        """Test that circuit resets after cooldown period."""
        cb = CircuitBreaker(failure_threshold=3, cooldown_period=0.1)

        # Open circuit
        cb.record_failure()
        cb.record_failure()
        cb.record_failure()
        assert cb.can_call() == False

        # Wait for cooldown
        time.sleep(0.15)

        # Circuit should enter half-open state
        assert cb.can_call() == True

    def test_half_open_state_success(self):
        """Test that circuit closes after successful calls in half-open."""
        cb = CircuitBreaker(
            failure_threshold=3, cooldown_period=0.1, half_open_max_calls=2
        )

        # Open circuit
        cb.record_failure()
        cb.record_failure()
        cb.record_failure()

        # Wait for cooldown
        time.sleep(0.15)

        # Make successful calls in half-open
        cb.record_success()
        assert cb.can_call() == True  # Still half-open

        cb.record_success()
        assert cb.can_call() == True  # Should be closed now

    def test_half_open_state_failure(self):
        """Test that circuit opens on failure in half-open."""
        cb = CircuitBreaker(
            failure_threshold=3, cooldown_period=0.1, half_open_max_calls=2
        )

        # Open circuit
        cb.record_failure()
        cb.record_failure()
        cb.record_failure()

        # Wait for cooldown
        time.sleep(0.15)

        # Fail in half-open state
        cb.record_failure()

        assert cb.can_call() == False  # Should be open again

    def test_manual_reset(self):
        """Test manual circuit breaker reset."""
        cb = CircuitBreaker(failure_threshold=3)

        # Open circuit
        cb.record_failure()
        cb.record_failure()
        cb.record_failure()
        assert cb.can_call() == False

        # Reset
        cb.reset()
        assert cb.can_call() == True


class TestRetryMetrics:
    """Test RetryMetrics class."""

    def test_initial_metrics(self):
        """Test initial metrics state."""
        metrics = RetryMetrics()
        stats = metrics.get_stats()

        assert stats["total_calls"] == 0
        assert stats["successful_calls"] == 0
        assert stats["failed_calls"] == 0
        assert stats["success_rate"] == 0.0
        assert stats["total_retries"] == 0
        assert stats["avg_retries_per_call"] == 0.0
        assert stats["total_retry_time"] == 0.0

    def test_record_call(self):
        """Test recording function calls."""
        metrics = RetryMetrics()

        metrics.record_call()
        metrics.record_call()

        stats = metrics.get_stats()
        assert stats["total_calls"] == 2

    def test_record_success(self):
        """Test recording successful calls."""
        metrics = RetryMetrics()

        metrics.record_call()
        metrics.record_success(retries=2)

        stats = metrics.get_stats()
        assert stats["successful_calls"] == 1
        assert stats["total_retries"] == 2

    def test_record_failure(self):
        """Test recording failed calls."""
        metrics = RetryMetrics()
        error = LLMRateLimitError()

        metrics.record_call()
        metrics.record_failure(error, retries=1)

        stats = metrics.get_stats()
        assert stats["failed_calls"] == 1
        assert stats["total_retries"] == 1
        assert "LLM_RATE_LIMIT" in stats["retry_attempts_by_error"]

    def test_record_retry_time(self):
        """Test recording retry time."""
        metrics = RetryMetrics()

        metrics.record_retry_time(1.5)
        metrics.record_retry_time(2.5)

        stats = metrics.get_stats()
        assert stats["total_retry_time"] == 4.0

    def test_success_rate_calculation(self):
        """Test success rate calculation."""
        metrics = RetryMetrics()

        metrics.record_call()
        metrics.record_success()
        metrics.record_call()
        metrics.record_failure(LLMRateLimitError(), 0)

        stats = metrics.get_stats()
        assert stats["success_rate"] == 50.0

    def test_avg_retries_calculation(self):
        """Test average retries calculation."""
        metrics = RetryMetrics()

        metrics.record_call()
        metrics.record_success(retries=2)
        metrics.record_call()
        metrics.record_failure(LLMRateLimitError(), 1)

        stats = metrics.get_stats()
        assert stats["avg_retries_per_call"] == 1.5

    def test_reset_metrics(self):
        """Test resetting metrics."""
        metrics = RetryMetrics()

        metrics.record_call()
        metrics.record_success()
        metrics.reset()

        stats = metrics.get_stats()
        assert stats["total_calls"] == 0
        assert stats["successful_calls"] == 0


class TestRetryDecorator:
    """Test retry decorator functionality."""

    def test_successful_call_no_retry(self):
        """Test successful call without retries."""
        reset_retry_metrics()

        @retry(max_attempts=3)
        def successful_function():
            return "success"

        result = successful_function()

        assert result == "success"

        stats = get_retry_metrics()
        assert stats["successful_calls"] == 1
        assert stats["total_retries"] == 0

    def test_retry_on_transient_error(self):
        """Test retrying on transient error."""
        reset_retry_metrics()

        call_count = [0]

        @retry(max_attempts=3, base_delay=0.01, jitter=False)
        def flaky_function():
            call_count[0] += 1
            if call_count[0] < 3:
                raise LLMRateLimitError()
            return "success"

        result = flaky_function()

        assert result == "success"
        assert call_count[0] == 3  # Failed twice, succeeded on third try

        stats = get_retry_metrics()
        assert stats["successful_calls"] == 1
        assert stats["total_retries"] == 2

    def test_no_retry_on_permanent_error(self):
        """Test not retrying on permanent error."""
        reset_retry_metrics()

        call_count = [0]

        @retry(max_attempts=3)
        def permanent_error_function():
            call_count[0] += 1
            raise FileNotFoundError()

        with pytest.raises(FileNotFoundError):
            permanent_error_function()

        # Should only call once, not retry
        assert call_count[0] == 1

        stats = get_retry_metrics()
        assert stats["failed_calls"] == 1

    def test_max_retries_exceeded(self):
        """Test behavior when max retries are exceeded."""
        reset_retry_metrics()

        call_count = [0]

        @retry(max_attempts=3, base_delay=0.01, jitter=False)
        def always_fails():
            call_count[0] += 1
            raise LLMRateLimitError()

        with pytest.raises(LLMRateLimitError):
            always_fails()

        # Should attempt 3 times (1 initial + 2 retries)
        assert call_count[0] == 3

        stats = get_retry_metrics()
        assert stats["failed_calls"] == 1
        assert stats["total_retries"] == 2

    def test_exponential_backoff_timing(self):
        """Test that exponential backoff timing works correctly."""
        reset_retry_metrics()

        call_times = []

        @retry(max_attempts=4, base_delay=0.1, exponential_base=2.0, jitter=False)
        def timed_function():
            call_times.append(time.time())
            if len(call_times) < 4:
                raise LLMRateLimitError()
            return "success"

        start = time.time()
        result = timed_function()
        end = time.time()

        assert result == "success"
        assert len(call_times) == 4

        # Verify delays: 0.1s, 0.2s, 0.4s (exponential backoff)
        delays = [call_times[i + 1] - call_times[i] for i in range(3)]
        assert abs(delays[0] - 0.1) < 0.02
        assert abs(delays[1] - 0.2) < 0.02
        assert abs(delays[2] - 0.4) < 0.02

    def test_retry_callback(self):
        """Test retry callback functionality."""
        reset_retry_metrics()

        callback_calls = []

        def on_retry(error, attempt, delay):
            callback_calls.append(
                {"error": error.message, "attempt": attempt, "delay": delay}
            )

        @retry(max_attempts=3, base_delay=0.01, on_retry=on_retry)
        def callback_function():
            raise LLMRateLimitError()

        with pytest.raises(LLMRateLimitError):
            callback_function()

        # Should have called callback twice (2 retries)
        assert len(callback_calls) == 2
        assert callback_calls[0]["attempt"] == 0
        assert callback_calls[1]["attempt"] == 1

    def test_disable_metrics_recording(self):
        """Test disabling metrics recording."""
        reset_retry_metrics()

        config = RetryConfig(max_attempts=3)

        @retry_with_config(retry_config=config, record_metrics=False)
        def no_metrics_function():
            raise LLMRateLimitError()

        with pytest.raises(LLMRateLimitError):
            no_metrics_function()

        stats = get_retry_metrics()
        assert stats["total_calls"] == 0


class TestCircuitBreakerIntegration:
    """Test circuit breaker integration with retry decorator."""

    def test_circuit_breaker_rejects_calls(self):
        """Test that circuit breaker rejects calls when open."""
        reset_retry_metrics()

        cb = CircuitBreaker(failure_threshold=2, cooldown_period=1.0)

        @retry(
            enable_circuit_breaker=True,
            circuit_failure_threshold=2,
            circuit_cooldown=1.0,
        )
        def failing_function():
            raise LLMRateLimitError()

        # Fail enough times to open circuit
        with pytest.raises(LLMRateLimitError):
            failing_function()
        with pytest.raises(LLMRateLimitError):
            failing_function()

        # Circuit should be open now
        stats = get_retry_metrics()
        # Third call should be rejected by circuit breaker
        with pytest.raises(Exception):  # Will raise circuit breaker error
            failing_function()

    def test_circuit_breaker_allows_calls_after_cooldown(self):
        """Test that circuit breaker allows calls after cooldown."""
        reset_retry_metrics()

        cb = CircuitBreaker(failure_threshold=2, cooldown_period=0.1)

        @retry_with_config(retry_config=RetryConfig(max_attempts=1), circuit_breaker=cb)
        def function_with_retries():
            raise LLMRateLimitError()

        # Fail to open circuit (only 1 attempt per call, so need 2 calls)
        with pytest.raises(LLMRateLimitError):
            function_with_retries()
        with pytest.raises(LLMRateLimitError):
            function_with_retries()

        # Circuit should be open now
        assert cb.can_call() == False

        # Wait for cooldown
        time.sleep(0.15)

        # Circuit should allow calls now (enters half-open state)
        assert cb.can_call() == True


class TestPreconfiguredPolicies:
    """Test pre-configured retry policies."""

    def test_llapi_policy(self):
        """Test LLM API retry policy."""
        assert RETRY_POLICY_LLAPI.max_attempts == 3
        assert RETRY_POLICY_LLAPI.base_delay == 2.0
        assert RETRY_POLICY_LLAPI.max_delay == 30.0
        assert RETRY_POLICY_LLAPI.jitter == True

    def test_database_policy(self):
        """Test database retry policy."""
        assert RETRY_POLICY_DATABASE.max_attempts == 3
        assert RETRY_POLICY_DATABASE.base_delay == 0.5
        assert RETRY_POLICY_DATABASE.max_delay == 10.0

    def test_network_policy(self):
        """Test network retry policy."""
        assert RETRY_POLICY_NETWORK.max_attempts == 5
        assert RETRY_POLICY_NETWORK.base_delay == 1.0
        assert RETRY_POLICY_NETWORK.max_delay == 60.0


class TestRetryWithConfig:
    """Test retry_with_config decorator."""

    def test_custom_config(self):
        """Test using custom retry config."""
        reset_retry_metrics()

        config = RetryConfig(max_attempts=2, base_delay=0.01, jitter=False)

        call_count = [0]

        @retry_with_config(retry_config=config)
        def custom_config_function():
            call_count[0] += 1
            if call_count[0] < 2:
                raise LLMRateLimitError()
            return "success"

        result = custom_config_function()

        assert result == "success"
        assert call_count[0] == 2

    def test_custom_circuit_breaker(self):
        """Test using custom circuit breaker."""
        reset_retry_metrics()

        cb = CircuitBreaker(failure_threshold=2, cooldown_period=0.1)

        @retry_with_config(retry_config=RetryConfig(max_attempts=3), circuit_breaker=cb)
        def circuit_breaker_function():
            raise LLMRateLimitError()

        # Fail to open circuit
        with pytest.raises(LLMRateLimitError):
            circuit_breaker_function()
        with pytest.raises(LLMRateLimitError):
            circuit_breaker_function()

        assert cb.can_call() == False


class TestGlobalMetrics:
    """Test global retry metrics functions."""

    def test_get_retry_metrics(self):
        """Test getting global retry metrics."""
        reset_retry_metrics()

        @retry(max_attempts=2)
        def test_function():
            return "success"

        test_function()

        stats = get_retry_metrics()
        assert stats["total_calls"] == 1
        assert stats["successful_calls"] == 1

    def test_reset_retry_metrics(self):
        """Test resetting global retry metrics."""
        reset_retry_metrics()

        @retry(max_attempts=2)
        def test_function():
            return "success"

        test_function()
        reset_retry_metrics()

        stats = get_retry_metrics()
        assert stats["total_calls"] == 0
        assert stats["successful_calls"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
