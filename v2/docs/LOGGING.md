# Structured Logging System Documentation

## Overview

The L4D V3 Structured Logging System provides consistent, searchable, and machine-parseable logging across all modules. It integrates seamlessly with the telemetry system and provides both human-readable and machine-readable log formats.

---

## Table of Contents

- [Architecture](#architecture)
- [Configuration](#configuration)
- [Log Message Format](#log-message-format)
- [Logging API](#logging-api)
- [Log Levels](#log-levels)
- [Integration with Telemetry](#integration-with-telemetry)
- [Log Analysis](#log-analysis)
- [Best Practices](#best-practices)

---

## Architecture

### Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Application Layer                         │
│  (All modules use the logger)                                 │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                 Structured Logging Layer                     │
│  (core/logging_config.py)                                    │
│  - Logger initialization                                     │
│  - Log message formatting                                    │
│  - Handler management                                         │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                 Output Handlers                              │
│  - Console handler (colored text)                            │
│  - File handler (rotating logs)                              │
│  - Error handler (separate error log)                        │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                 Storage                                      │
│  - Console output                                             │
│  - l4.log (main log)                                         │
│  - l4_error.log (error log)                                  │
└─────────────────────────────────────────────────────────────┘
```

### Key Features

- **Structured Format**: JSON format for machine parsing, colored text for humans
- **Multiple Handlers**: Console, file, and error log handlers
- **Log Rotation**: Automatic rotation based on size (max 10MB, keep 5 files)
- **Contextual Logging**: Automatic correlation with telemetry operations
- **Flexible Levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **Thread-Safe**: Safe for concurrent operations

---

## Configuration

### Programmatic Configuration

```python
from core.logging_config import setup_logging

# Setup logging with custom configuration
setup_logging(
    log_level="INFO",                    # Default log level
    log_file="l4.log",                  # Main log file
    error_log_file="l4_error.log",     # Error log file
    max_file_size_mb=10,                # Max file size before rotation
    backup_count=5,                     # Number of backup files to keep
    json_format=False,                  # Use JSON format (default: False)
    enable_console=True                  # Enable console output (default: True)
)
```

### Environment Variables

```bash
# Logging configuration
export L4_LOG_LEVEL=INFO
export L4_LOG_FILE=l4.log
export L4_ERROR_LOG_FILE=l4_error.log
export L4_MAX_FILE_SIZE_MB=10
export L4_BACKUP_COUNT=5
export L4_JSON_FORMAT=false
export L4_ENABLE_CONSOLE=true
```

### Configuration File

Create a `logging_config.yaml` file:

```yaml
logging:
  level: INFO
  file: l4.log
  error_file: l4_error.log
  max_file_size_mb: 10
  backup_count: 5
  json_format: false
  enable_console: true
```

Load configuration:

```python
import yaml
from core.logging_config import setup_logging

with open('logging_config.yaml', 'r') as f:
    config = yaml.safe_load(f)

setup_logging(**config['logging'])
```

---

## Log Message Format

### Human-Readable Format

```
2026-01-21 00:15:36 [INFO] [core.start] [operation_id: abc-123] Task implementation started
```

### JSON Format

```json
{
  "timestamp": "2026-01-21T00:15:36Z",
  "level": "INFO",
  "logger": "core.start",
  "message": "Task implementation started",
  "operation_id": "abc-123",
  "task_id": 42,
  "context": {
    "task_title": "Add user authentication",
    "estimated_lines": 25
  }
}
```

### Format Fields

| Field | Description | Example |
|-------|-------------|---------|
| `timestamp` | ISO 8601 timestamp | `2026-01-21T00:15:36Z` |
| `level` | Log level | `INFO`, `WARNING`, `ERROR` |
| `logger` | Module name | `core.start`, `logic.implementor` |
| `message` | Log message | `Task implementation started` |
| `operation_id` | Telemetry operation ID (if applicable) | `abc-123` |
| `task_id` | Task ID (if applicable) | `42` |
| `context` | Additional context as JSON | `{"task_title": "...", "estimated_lines": 25}` |

---

## Logging API

### Basic Logging

```python
import logging

# Get logger for current module
logger = logging.getLogger(__name__)

# Log at different levels
logger.debug("Detailed debug information")
logger.info("Informational message")
logger.warning("Warning message")
logger.error("Error occurred")
logger.critical("Critical failure")
```

### Structured Logging with Context

```python
from core.logging_config import format_log_message

# Log with context
context = {
    "task_id": 42,
    "task_title": "Add user authentication",
    "estimated_lines": 25
}

logger.info(
    format_log_message(
        "Task implementation started",
        context=context
    )
)

# Output: Task implementation started [task_id=42, task_title="Add user authentication", estimated_lines=25]
```

### Logging Helper Functions

```python
from core.logging_config import (
    log_operation_start,
    log_operation_complete,
    log_operation_failed,
    log_event,
    log_error
)

# Log operation lifecycle
log_operation_start(
    logger,
    operation_id="abc-123",
    operation_type="implementation",
    title="Implement user authentication"
)

# Log operation completion
log_operation_complete(
    logger,
    operation_id="abc-123",
    duration_seconds=12.5,
    metrics={"tokens_used": 1250}
)

# Log operation failure
log_operation_failed(
    logger,
    operation_id="abc-123",
    error="LLM API timeout",
    duration_seconds=30.0
)

# Log events
log_event(
    logger,
    operation_id="abc-123",
    event_type="test_generation",
    message="Starting test generation",
    context={"test_file": "test_auth.py"}
)

# Log errors
log_error(
    logger,
    operation_id="abc-123",
    error="Database connection failed",
    exception=e,
    context={"database": "postgres://localhost:5432/l4"}
)
```

### Logging with Telemetry Correlation

```python
from data.telemetry_manager import TelemetryManager
from core.logging_config import get_logger_with_operation

telemetry = TelemetryManager()

# Create logger with operation ID
logger = get_logger_with_operation(
    __name__,
    operation_id="abc-123"
)

# All log entries will include operation_id
logger.info("This log is correlated with operation abc-123")

# Or use context manager
with telemetry.track_operation("implementation", "Implement feature") as op:
    logger = get_logger_with_operation(__name__, op.id)
    logger.info("Implementation started")
```

---

## Log Levels

### Log Level Hierarchy

```
DEBUG < INFO < WARNING < ERROR < CRITICAL
```

### When to Use Each Level

| Level | Usage | Example |
|-------|-------|---------|
| **DEBUG** | Detailed diagnostic information | "Context cache hit for file src/main.py" |
| **INFO** | Normal operational events | "Task 42 implementation started" |
| **WARNING** | Unexpected but recoverable situations | "Cache size approaching limit (95%)" |
| **ERROR** | Error that prevented operation | "LLM API call failed: rate limit exceeded" |
| **CRITICAL** | Serious error requiring immediate attention | "Database corruption detected" |

### Setting Log Levels

```python
import logging

# Set log level for specific logger
logging.getLogger('core.start').setLevel(logging.DEBUG)

# Set log level globally
logging.getLogger().setLevel(logging.INFO)

# Set log level via environment
# L4_LOG_LEVEL=DEBUG
```

---

## Integration with Telemetry

### Automatic Correlation

The logging system automatically correlates log entries with telemetry operations:

```python
from data.telemetry_manager import telemetry
import logging

logger = logging.getLogger(__name__)

# This log will be correlated with the operation
with telemetry.track_operation("implementation", "Implement feature") as op:
    logger.info("Operation started")  # Includes operation_id in log
    
    # ... work ...
    
    logger.info("Operation completed")  # Includes operation_id in log
```

### Manual Correlation

```python
from core.logging_config import get_logger_with_operation

# Create logger with operation ID
logger = get_logger_with_operation(__name__, operation_id="abc-123")

logger.info("This log is correlated with operation abc-123")
```

### Querying Logs by Operation

```python
from core.log_analyzer import LogAnalyzer

analyzer = LogAnalyzer()

# Get all logs for an operation
logs = analyzer.query_logs_by_operation(operation_id="abc-123")

# Get logs with specific level
logs = analyzer.query_logs_by_level(level="ERROR")

# Get logs in time range
logs = analyzer.query_logs_by_time_range(
    start_time="2026-01-21T00:00:00Z",
    end_time="2026-01-21T23:59:59Z"
)
```

---

## Log Analysis

### Using LogAnalyzer

```python
from core.log_analyzer import LogAnalyzer

analyzer = LogAnalyzer()

# Search logs by keyword
logs = analyzer.search_logs(keyword="error")

# Search logs by level
logs = analyzer.search_logs(level="ERROR")

# Search logs by module
logs = analyzer.search_logs(module="logic.implementor")

# Get log statistics
stats = analyzer.get_log_statistics()
print(f"Total logs: {stats['total']}")
print(f"Error count: {stats['error_count']}")
print(f"Warning count: {stats['warning_count']}")
```

### Generating Reports

```python
from core.log_analyzer import LogAnalyzer

analyzer = LogAnalyzer()

# Generate error report
error_report = analyzer.generate_error_report()
print(error_report)

# Generate operation timeline
timeline = analyzer.generate_operation_timeline(operation_id="abc-123")
print(timeline)

# Generate log summary
summary = analyzer.generate_log_summary(
    start_time="2026-01-21T00:00:00Z",
    end_time="2026-01-21T23:59:59Z"
)
print(summary)
```

### CLI Commands

```bash
# Search logs
l4-dev logs search --keyword error

# Search by level
l4-dev logs search --level ERROR

# Search by module
l4-dev logs search --module logic.implementor

# Search by operation
l4-dev logs search --operation-id abc-123

# Search in time range
l4-dev logs search --start-time "2026-01-21T00:00:00Z" --end-time "2026-01-21T23:59:59Z"

# Generate error report
l4-dev logs report --type error

# Generate operation timeline
l4-dev logs timeline --operation-id abc-123
```

---

## Best Practices

### 1. Use Appropriate Log Levels

```python
# Good
logger.debug("Context cache hit for file %s", file_path)
logger.info("Task %d implementation started", task_id)
logger.warning("Cache size approaching limit: %.1f%%", cache_usage)
logger.error("LLM API call failed: %s", error_message)
logger.critical("Database corruption detected")

# Bad
logger.info("DEBUG: Cache hit for file")  # Use DEBUG level
logger.error("Info message")  # Use INFO level
```

### 2. Include Context in Logs

```python
# Good
context = {
    "task_id": task.id,
    "task_title": task.title,
    "operation_id": op_id
}
logger.info("Task implementation started", extra={"context": context})

# Bad
logger.info("Task implementation started")  # Missing context
```

### 3. Use Structured Log Messages

```python
# Good
from core.logging_config import format_log_message
logger.info(
    format_log_message(
        "Task implementation started",
        task_id=task.id,
        task_title=task.title
    )
)

# Bad
logger.info(f"Task {task.id} ({task.title}) implementation started")  # Hard to parse
```

### 4. Log Errors with Stack Traces

```python
# Good
try:
    risky_operation()
except Exception as e:
    logger.error(
        format_log_message(
            "Operation failed",
            operation=op_name
        ),
        exc_info=True  # Include stack trace
    )

# Bad
try:
    risky_operation()
except Exception as e:
    logger.error(f"Operation failed: {e}")  # No stack trace
```

### 5. Avoid Logging Sensitive Data

```python
# Bad - logs password
logger.info("Connecting to database with user %s and password %s", user, password)

# Good
logger.info("Connecting to database with user %s", user)
```

### 6. Use Lazy Formatting

```python
# Good - lazy evaluation, only formats if log level is enabled
logger.debug("Processing %d items: %s", len(items), items)

# Bad - always formats even if debug is disabled
logger.debug(f"Processing {len(items)} items: {items}")
```

### 7. Correlate Logs with Operations

```python
# Good
with telemetry.track_operation("implementation", "Implement feature") as op:
    logger = get_logger_with_operation(__name__, op.id)
    logger.info("Implementation started")
    # ... work ...
    logger.info("Implementation completed")

# Bad - no correlation
logger.info("Implementation started")
# ... work ...
logger.info("Implementation completed")
```

### 8. Log Operation Lifecycle Events

```python
# Good
from core.logging_config import (
    log_operation_start,
    log_operation_complete,
    log_operation_failed
)

log_operation_start(logger, operation_id, "implementation", "Implement feature")
# ... work ...
log_operation_complete(logger, operation_id, duration=12.5, metrics={"tokens": 1250})

# Bad - no structured operation logging
logger.info("Starting implementation")
# ... work ...
logger.info("Implementation completed")
```

### 9. Use Log Rotation

```python
# Good - configure rotation
setup_logging(
    log_file="l4.log",
    max_file_size_mb=10,  # Rotate at 10MB
    backup_count=5  # Keep 5 backup files
)

# Bad - no rotation, logs grow indefinitely
setup_logging(log_file="l4.log")
```

### 10. Regularly Analyze Logs

```python
# Good -定期分析日志
analyzer = LogAnalyzer()
error_report = analyzer.generate_error_report()
if error_report['error_count'] > 100:
    logger.warning("High error rate detected: %d errors", error_report['error_count'])

# Bad - never analyze logs
```

---

## Troubleshooting

### Logs Not Appearing

**Problem**: Logs are not being written.

**Solution**:
1. Check that logging is initialized: `setup_logging()`
2. Check log level: Ensure level is set appropriately
3. Check file permissions: Ensure log files are writable
4. Check console output: If JSON format is enabled, console may be disabled

### Log Files Too Large

**Problem**: Log files are growing too large.

**Solution**:
1. Enable log rotation: `setup_logging(max_file_size_mb=10, backup_count=5)`
2. Reduce log level: Use WARNING or ERROR instead of DEBUG
3. Reduce verbosity: Log only essential information
4. Archive old logs: Move old logs to archive directory

### Missing Context in Logs

**Problem**: Log entries are missing context information.

**Solution**:
1. Use `format_log_message()` helper function
2. Include `extra={"context": context}` parameter
3. Use `get_logger_with_operation()` for operation correlation
4. Check logging configuration

### Performance Impact

**Problem**: Logging is impacting performance.

**Solution**:
1. Use lazy formatting: `logger.debug("Processing %d items", len(items))`
2. Increase log level: Use INFO instead of DEBUG
3. Disable console output: `enable_console=False`
4. Use async logging if supported

---

## API Reference

### Logging Configuration Functions

**setup_logging**
```python
setup_logging(
    log_level: str = "INFO",
    log_file: str = "l4.log",
    error_log_file: str = "l4_error.log",
    max_file_size_mb: int = 10,
    backup_count: int = 5,
    json_format: bool = False,
    enable_console: bool = True
) -> None
```

**get_logger**
```python
get_logger(name: str) -> logging.Logger
```

**get_logger_with_operation**
```python
get_logger_with_operation(name: str, operation_id: str) -> logging.Logger
```

### Log Formatting Functions

**format_log_message**
```python
format_log_message(message: str, **context) -> str
```

### Log Helper Functions

**log_operation_start**
```python
log_operation_start(
    logger: logging.Logger,
    operation_id: str,
    operation_type: str,
    title: str,
    **context
) -> None
```

**log_operation_complete**
```python
log_operation_complete(
    logger: logging.Logger,
    operation_id: str,
    duration_seconds: Optional[float] = None,
    metrics: Optional[Dict] = None,
    **context
) -> None
```

**log_operation_failed**
```python
log_operation_failed(
    logger: logging.Logger,
    operation_id: str,
    error: str,
    duration_seconds: Optional[float] = None,
    exception: Optional[Exception] = None,
    **context
) -> None
```

**log_event**
```python
log_event(
    logger: logging.Logger,
    operation_id: str,
    event_type: str,
    message: Optional[str] = None,
    severity: str = "info",
    **context
) -> None
```

**log_error**
```python
log_error(
    logger: logging.Logger,
    operation_id: Optional[str] = None,
    error: str,
    exception: Optional[Exception] = None,
    **context
) -> None
```

---

## Conclusion

The L4D V3 Structured Logging System provides consistent, searchable, and machine-parseable logging across all modules. By following the best practices outlined in this document, you can improve debugging efficiency and gain better insights into system behavior.

For more information, see:
- [TELEMETRY.md](TELEMETRY.md) - Telemetry system documentation
- [RESUMABILITY.md](RESUMABILITY.md) - Checkpoint and recovery
- [SESSION_MANAGEMENT.md](SESSION_MANAGEMENT.md) - Session persistence