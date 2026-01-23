"""
Test script for standardized logging implementation (Task 2.2)
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from core.logging_config import (
    get_logger,
    LogMessageTemplates,
    format_log_message,
    log_operation_started,
    log_operation_completed,
    log_operation_failed,
    log_task_started,
    log_task_completed,
    log_task_failed,
    log_error_with_context,
)


def test_message_templates():
    """Test log message templates."""
    print("Testing message templates...")

    # Test operation templates
    msg = format_log_message(
        LogMessageTemplates.OPERATION_STARTED, operation_type="implementation"
    )
    assert (
        msg == "implementation started"
    ), f"Expected 'implementation started', got '{msg}'"
    print(f"✓ Operation started template: {msg}")

    msg = format_log_message(
        LogMessageTemplates.OPERATION_COMPLETED, operation_type="implementation"
    )
    assert (
        msg == "implementation completed"
    ), f"Expected 'implementation completed', got '{msg}'"
    print(f"✓ Operation completed template: {msg}")

    msg = format_log_message(
        LogMessageTemplates.OPERATION_FAILED,
        operation_type="implementation",
        error="File not found",
    )
    assert (
        msg == "implementation failed: File not found"
    ), f"Expected 'implementation failed: File not found', got '{msg}'"
    print(f"✓ Operation failed template: {msg}")

    # Test task templates
    msg = format_log_message(
        LogMessageTemplates.TASK_STARTED, task_id=42, task_title="Add authentication"
    )
    assert (
        msg == "Task 42 started: Add authentication"
    ), f"Expected 'Task 42 started: Add authentication', got '{msg}'"
    print(f"✓ Task started template: {msg}")

    msg = format_log_message(LogMessageTemplates.TASK_COMPLETED, task_id=42)
    assert msg == "Task 42 completed", f"Expected 'Task 42 completed', got '{msg}'"
    print(f"✓ Task completed template: {msg}")

    # Test context collection templates
    msg = format_log_message(
        LogMessageTemplates.CONTEXT_COLLECTION_COMPLETED, num_files=5, num_tokens=1200
    )
    assert (
        msg == "Context collection completed: 5 files, 1200 tokens"
    ), f"Expected 'Context collection completed: 5 files, 1200 tokens', got '{msg}'"
    print(f"✓ Context collection template: {msg}")

    # Test telemetry templates
    msg = format_log_message(
        LogMessageTemplates.TELEMETRY_OPERATION_TRACKED,
        operation_type="implementation",
        operation_id="abc-123",
    )
    assert (
        msg == "Telemetry tracked: implementation (id: abc-123)"
    ), f"Expected 'Telemetry tracked: implementation (id: abc-123)', got '{msg}'"
    print(f"✓ Telemetry template: {msg}")

    print("\nAll template tests passed! ✓\n")


def test_helper_functions():
    """Test logging helper functions."""
    print("Testing logging helper functions...")

    logger = get_logger(__name__)

    # Test operation logging
    print("Testing log_operation_started...")
    log_operation_started(logger, "implementation", operation_id="abc-123", task_id=42)
    print("✓ Operation started logged")

    print("Testing log_operation_completed...")
    log_operation_completed(
        logger, "implementation", operation_id="abc-123", task_id=42
    )
    print("✓ Operation completed logged")

    # Test task logging
    print("Testing log_task_started...")
    log_task_started(
        logger, task_id=42, task_title="Add authentication", operation_id="abc-123"
    )
    print("✓ Task started logged")

    print("Testing log_task_completed...")
    log_task_completed(logger, task_id=42, operation_id="abc-123")
    print("✓ Task completed logged")

    # Test error logging
    print("Testing log_operation_failed...")
    log_operation_failed(
        logger, "implementation", "File not found", operation_id="abc-123", task_id=42
    )
    print("✓ Operation failed logged")

    print("Testing log_error_with_context...")
    try:
        raise ValueError("Test error")
    except Exception as e:
        log_error_with_context(logger, e, operation_id="abc-123", task_id=42)
        print("✓ Error with context logged")

    print("\nAll helper function tests passed! ✓\n")


def test_context_injection():
    """Test context injection into log messages."""
    print("Testing context injection...")

    logger = get_logger(__name__)

    # Log with context using extra parameter
    logger.info(
        "Test message with context",
        extra={
            "operation_id": "abc-123",
            "task_id": 42,
            "file_path": "v2/core/logging_config.py",
        },
    )
    print("✓ Context injected via extra parameter")

    # Test with standard context keys
    logger.info(
        "Another test message",
        extra={"operation_id": "xyz-789", "session_id": "session-1"},
    )
    print("✓ Session context injected")

    print("\nContext injection tests passed! ✓\n")


def test_error_handling():
    """Test error handling with context."""
    print("Testing error handling...")

    logger = get_logger(__name__)

    # Test with different exception types
    test_exceptions = [
        ValueError("Invalid value"),
        FileNotFoundError("File not found"),
        RuntimeError("Runtime error occurred"),
        Exception("Generic error"),
    ]

    for i, exc in enumerate(test_exceptions):
        try:
            raise exc
        except Exception as e:
            log_error_with_context(
                logger,
                e,
                operation_id=f"op-{i}",
                task_id=i,
                file_path=f"test_file_{i}.py",
            )
            print(f"✓ Error {i+1} logged: {type(e).__name__}")

    print("\nError handling tests passed! ✓\n")


if __name__ == "__main__":
    print("=" * 60)
    print("Testing Standardized Logging (Task 2.2)")
    print("=" * 60)
    print()

    test_message_templates()
    test_helper_functions()
    test_context_injection()
    test_error_handling()

    print("=" * 60)
    print("All tests passed successfully! ✓")
    print("=" * 60)
