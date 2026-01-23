"""
Test script for LogAnalyzer functionality
"""

import sys
import os
import json
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from v2.core.log_analyzer import LogAnalyzer, LogQuery, LogEntry


def create_test_logs():
    """Create test log files for testing."""
    log_dir = "v2/logs"
    os.makedirs(log_dir, exist_ok=True)

    # Create sample log entries
    test_logs = [
        {
            "timestamp": "2026-01-21T10:00:00",
            "level": "INFO",
            "logger": "test.module",
            "message": "Task implementation started",
            "module": "test.module",
            "function": "implement_task",
            "line": 42,
            "operation_id": "op-123",
            "task_id": 1,
        },
        {
            "timestamp": "2026-01-21T10:01:00",
            "level": "DEBUG",
            "logger": "test.module",
            "message": "Context collection completed",
            "module": "test.module",
            "function": "collect_context",
            "line": 56,
            "operation_id": "op-123",
            "task_id": 1,
        },
        {
            "timestamp": "2026-01-21T10:02:00",
            "level": "ERROR",
            "logger": "test.module",
            "message": "Task implementation failed",
            "module": "test.module",
            "function": "implement_task",
            "line": 78,
            "operation_id": "op-123",
            "task_id": 1,
            "exception": "ValueError: Invalid input parameter",
        },
        {
            "timestamp": "2026-01-21T10:03:00",
            "level": "INFO",
            "logger": "another.module",
            "message": "Test generation started",
            "module": "another.module",
            "function": "generate_test",
            "line": 12,
            "operation_id": "op-456",
            "task_id": 2,
        },
    ]

    # Write to main log file
    log_file = os.path.join(log_dir, "l4d.log")
    with open(log_file, "w") as f:
        for log in test_logs:
            f.write(json.dumps(log) + "\n")

    print(f"Created {len(test_logs)} test log entries in {log_file}")
    return test_logs


def test_log_analyzer():
    """Test LogAnalyzer functionality."""
    print("\n=== Testing LogAnalyzer ===\n")

    # Create test logs
    test_logs = create_test_logs()

    # Initialize analyzer
    analyzer = LogAnalyzer(log_dir="v2/logs")
    analyzer.load_logs()

    print(f"Loaded {len(analyzer.entries)} log entries")

    # Test 1: Search by level
    print("\n--- Test 1: Search by level (ERROR) ---")
    query = LogQuery(level="ERROR")
    error_entries = analyzer.search(query)
    print(f"Found {len(error_entries)} error entries")
    for entry in error_entries:
        print(f"  - {entry.message}")

    # Test 2: Search by operation ID
    print("\n--- Test 2: Search by operation ID (op-123) ---")
    op_entries = analyzer.get_entries_by_operation("op-123")
    print(f"Found {len(op_entries)} entries for operation op-123")
    for entry in op_entries:
        print(f"  - [{entry.level}] {entry.message}")

    # Test 3: Search by task ID
    print("\n--- Test 3: Search by task ID (1) ---")
    task_entries = analyzer.get_entries_by_task(1)
    print(f"Found {len(task_entries)} entries for task 1")
    for entry in task_entries:
        print(f"  - [{entry.level}] {entry.message}")

    # Test 4: Full-text search
    print("\n--- Test 4: Full-text search ('implementation') ---")
    query = LogQuery(search="implementation")
    search_entries = analyzer.search(query)
    print(f"Found {len(search_entries)} entries matching 'implementation'")
    for entry in search_entries:
        print(f"  - {entry.message}")

    # Test 5: Get errors
    print("\n--- Test 5: Get all errors ---")
    errors = analyzer.get_errors()
    print(f"Found {len(errors)} error entries")
    for error in errors:
        print(f"  - {error.exception}")

    # Test 6: Generate summary
    print("\n--- Test 6: Generate summary ---")
    summary = analyzer.generate_summary()
    print(f"Total entries: {summary['total_entries']}")
    print(f"Error count: {summary['error_count']}")
    print(f"By level: {summary['by_level']}")

    # Test 7: Identify error patterns
    print("\n--- Test 7: Identify error patterns ---")
    patterns = analyzer.identify_error_patterns()
    print(f"Found {len(patterns)} error patterns")
    for pattern in patterns:
        print(f"  - {pattern['error_type']}: {pattern['count']} occurrences")

    # Test 8: Generate operation timeline
    print("\n--- Test 8: Generate operation timeline ---")
    timeline = analyzer.generate_operation_timeline("op-123")
    print(f"Timeline has {len(timeline)} events")
    for event in timeline:
        print(f"  - [{event['timestamp']}] [{event['level']}] {event['message']}")

    # Test 9: Test boolean search with AND
    print("\n--- Test 9: Boolean search ('task AND implementation') ---")
    query = LogQuery(search="task AND implementation")
    results = analyzer.search(query)
    print(f"Found {len(results)} entries")
    for entry in results:
        print(f"  - {entry.message}")

    # Test 10: Test module wildcard filtering
    print("\n--- Test 10: Module wildcard filter ('test.*') ---")
    query = LogQuery(module="test.*")
    results = analyzer.search(query)
    print(f"Found {len(results)} entries in test.* modules")
    for entry in results:
        print(f"  - {entry.module}: {entry.message}")

    print("\n=== All tests completed successfully! ===\n")


if __name__ == "__main__":
    test_log_analyzer()
