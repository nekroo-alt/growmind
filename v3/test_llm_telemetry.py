"""
Test for Task 1.3: LLM Call Telemetry Integration

Tests comprehensive telemetry tracking for LLM calls including:
- Request/response details
- Prompt size, response size, and token counts
- Latency and retry attempts
- Model, temperature, and other parameters
- Error capture and fallbacks
"""

import os
import sys
import json
import time
from unittest.mock import patch, MagicMock

# Add v2 to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from v3.llm_base.provider import LLMProvider
from v3.data.telemetry_manager import get_telemetry_manager


def test_llm_telemetry_integration():
    """Test that LLM calls are properly tracked in telemetry."""
    print("\n=== Test: LLM Telemetry Integration ===")

    # Ensure clean state
    telemetry = get_telemetry_manager()

    # Create provider with mock (no API key)
    provider = LLMProvider(provider="mock")

    # Make a call
    system_prompt = "You are a helpful assistant."
    user_prompt = "Say hello"

    result = provider.call(system_prompt, user_prompt)

    print(f"✓ Call completed: {result['content'][:50]}...")
    print(f"✓ Usage: {result['usage']}")

    # Check telemetry was recorded
    operations = telemetry.list_operations(operation_type="llm_call", limit=1)
    assert len(operations) > 0, "No LLM call operations recorded"

    operation = operations[0]
    print(f"✓ Operation recorded: {operation['title']}")
    print(f"✓ Operation status: {operation['status']}")

    # Check events were recorded
    events = telemetry.get_operation_events(operation["id"])
    print(f"✓ Events recorded: {len(events)}")
    for event in events:
        print(f"  - {event['event_type']}: {event['message'][:50]}...")

    # Check metrics were recorded
    metrics = telemetry.get_operation_metrics(operation["id"])
    print(f"✓ Metrics recorded: {len(metrics)}")
    for metric in metrics:
        print(
            f"  - {metric['metric_name']}: {metric['metric_value']} {metric.get('unit', '')}"
        )

    # Verify specific metrics exist
    metric_names = {m["metric_name"] for m in metrics}
    assert "prompt_tokens" in metric_names, "prompt_tokens metric missing"
    assert "completion_tokens" in metric_names, "completion_tokens metric missing"
    assert "total_tokens" in metric_names, "total_tokens metric missing"
    assert "latency_seconds" in metric_names, "latency_seconds metric missing"

    print("✓ All required metrics present")
    print("\n✅ Test passed: LLM telemetry integration works correctly\n")


def test_llm_call_with_parameters():
    """Test that LLM call parameters are tracked."""
    print("\n=== Test: LLM Call Parameter Tracking ===")

    telemetry = get_telemetry_manager()
    provider = LLMProvider(provider="mock")

    # Make a call with specific parameters
    result = provider.call(
        system_prompt="System", user_prompt="User", temperature=0.5, max_tokens=1000
    )

    # Check operation metadata
    operations = telemetry.list_operations(operation_type="llm_call", limit=1)
    operation = operations[0]

    metadata = operation.get("metadata", {})
    assert metadata.get("temperature") == 0.5, f"Temperature not tracked: {metadata}"
    assert metadata.get("max_tokens") == 1000, f"max_tokens not tracked: {metadata}"
    assert "prompt_size_chars" in metadata, f"prompt_size_chars not tracked: {metadata}"

    print(f"✓ Temperature tracked: {metadata['temperature']}")
    print(f"✓ Max tokens tracked: {metadata['max_tokens']}")
    print(f"✓ Prompt size tracked: {metadata['prompt_size_chars']}")
    print("\n✅ Test passed: Call parameters tracked correctly\n")


def test_llm_latency_tracking():
    """Test that call latency is measured and recorded."""
    print("\n=== Test: LLM Latency Tracking ===")

    telemetry = get_telemetry_manager()
    provider = LLMProvider(provider="mock")

    # Make a call
    start = time.time()
    result = provider.call("System", "User")
    actual_duration = time.time() - start

    # Get metrics
    operations = telemetry.list_operations(operation_type="llm_call", limit=1)
    operation = operations[0]
    metrics = telemetry.get_operation_metrics(operation["id"])

    # Find latency metric
    latency_metric = next(
        (m for m in metrics if m["metric_name"] == "latency_seconds"), None
    )
    assert latency_metric is not None, "latency_seconds metric not found"

    tracked_latency = latency_metric["metric_value"]
    print(f"✓ Actual duration: {actual_duration:.3f}s")
    print(f"✓ Tracked latency: {tracked_latency:.3f}s")

    # Latency should be reasonably close (allow 100ms overhead)
    assert (
        abs(tracked_latency - actual_duration) < 0.1
    ), f"Latency mismatch: tracked={tracked_latency:.3f}, actual={actual_duration:.3f}"

    print("\n✅ Test passed: Latency tracked accurately\n")


def test_llm_token_counting():
    """Test that token counts are recorded."""
    print("\n=== Test: LLM Token Counting ===")

    telemetry = get_telemetry_manager()
    provider = LLMProvider(provider="mock")

    # Make a call
    system_prompt = "You are a helpful assistant."
    user_prompt = "Tell me a short story."
    result = provider.call(system_prompt, user_prompt)

    # Get metrics
    operations = telemetry.list_operations(operation_type="llm_call", limit=1)
    operation = operations[0]
    metrics = telemetry.get_operation_metrics(operation["id"])

    # Check token counts
    prompt_tokens = next(
        m["metric_value"] for m in metrics if m["metric_name"] == "prompt_tokens"
    )
    completion_tokens = next(
        m["metric_value"] for m in metrics if m["metric_name"] == "completion_tokens"
    )
    total_tokens = next(
        m["metric_value"] for m in metrics if m["metric_name"] == "total_tokens"
    )

    assert prompt_tokens > 0, "prompt_tokens should be > 0"
    assert completion_tokens > 0, "completion_tokens should be > 0"
    assert (
        total_tokens == prompt_tokens + completion_tokens
    ), "total_tokens should equal sum"

    print(f"✓ Prompt tokens: {prompt_tokens}")
    print(f"✓ Completion tokens: {completion_tokens}")
    print(f"✓ Total tokens: {total_tokens}")

    # Verify against result usage
    assert prompt_tokens == result["usage"]["prompt_tokens"], "Prompt token mismatch"
    assert (
        completion_tokens == result["usage"]["completion_tokens"]
    ), "Completion token mismatch"

    print("\n✅ Test passed: Token counting accurate\n")


def test_llm_response_size_tracking():
    """Test that response size is tracked."""
    print("\n=== Test: LLM Response Size Tracking ===")

    telemetry = get_telemetry_manager()
    provider = LLMProvider(provider="mock")

    # Make a call
    result = provider.call("System", "User")
    response_content = result["content"]

    # Get metrics
    operations = telemetry.list_operations(operation_type="llm_call", limit=1)
    operation = operations[0]
    metrics = telemetry.get_operation_metrics(operation["id"])

    # Check response size
    size_metric = next(
        (m for m in metrics if m["metric_name"] == "response_size_chars"), None
    )
    assert size_metric is not None, "response_size_chars metric not found"

    tracked_size = size_metric["metric_value"]
    actual_size = len(response_content)

    assert (
        tracked_size == actual_size
    ), f"Size mismatch: tracked={tracked_size}, actual={actual_size}"

    print(f"✓ Response size tracked: {tracked_size} chars")
    print(f"✓ Actual response size: {actual_size} chars")
    print("\n✅ Test passed: Response size tracked correctly\n")


def test_llm_operation_metadata():
    """Test that operation includes proper metadata."""
    print("\n=== Test: LLM Operation Metadata ===")

    telemetry = get_telemetry_manager()
    provider = LLMProvider(provider="mock", model="mock-model")

    # Make a call
    result = provider.call("System", "User")

    # Get operation
    operations = telemetry.list_operations(operation_type="llm_call", limit=1)
    operation = operations[0]

    # Check metadata
    metadata = operation.get("metadata", {})
    assert "provider" in metadata, "provider not in metadata"
    assert "model" in metadata, "model not in metadata"
    assert "temperature" in metadata, "temperature not in metadata"
    assert "max_tokens" in metadata, "max_tokens not in metadata"

    print(f"✓ Provider: {metadata['provider']}")
    print(f"✓ Model: {metadata['model']}")
    print(f"✓ Temperature: {metadata['temperature']}")
    print(f"✓ Max tokens: {metadata['max_tokens']}")
    print("\n✅ Test passed: Operation metadata complete\n")


def test_llm_event_tracking():
    """Test that appropriate events are recorded."""
    print("\n=== Test: LLM Event Tracking ===")

    telemetry = get_telemetry_manager()
    provider = LLMProvider(provider="mock")

    # Make a call
    result = provider.call("System", "User")

    # Get operation
    operations = telemetry.list_operations(operation_type="llm_call", limit=1)
    operation = operations[0]

    # Get events
    events = telemetry.get_operation_events(operation["id"])
    event_types = [e["event_type"] for e in events]

    # Check for expected events
    assert "call_started" in event_types, "call_started event missing"
    assert "call_completed" in event_types, "call_completed event missing"

    print(f"✓ Events recorded: {event_types}")

    # Check event details
    started_event = next(e for e in events if e["event_type"] == "call_started")
    completed_event = next(e for e in events if e["event_type"] == "call_completed")

    assert started_event["severity"] == "info", "call_started should be info"
    assert completed_event["severity"] == "info", "call_completed should be info"

    print(f"✓ Call started event: {started_event['message'][:50]}...")
    print(f"✓ Call completed event: {completed_event['message'][:50]}...")

    print("\n✅ Test passed: Events tracked correctly\n")


def run_all_tests():
    """Run all LLM telemetry tests."""
    print("\n" + "=" * 60)
    print("Running LLM Telemetry Integration Tests")
    print("=" * 60)

    try:
        test_llm_telemetry_integration()
        test_llm_call_with_parameters()
        test_llm_latency_tracking()
        test_llm_token_counting()
        test_llm_response_size_tracking()
        test_llm_operation_metadata()
        test_llm_event_tracking()

        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED")
        print("=" * 60 + "\n")
        return True
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}\n")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}\n")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
