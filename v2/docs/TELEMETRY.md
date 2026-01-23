# Telemetry System Documentation

## Overview

The L4D V3 Telemetry System provides comprehensive operation tracking, metrics collection, and analytics capabilities for the development platform. It enables deep visibility into all operations, resource usage, and performance characteristics.

---

## Table of Contents

- [Architecture](#architecture)
- [Database Schema](#database-schema)
- [Telemetry Manager API](#telemetry-manager-api)
- [Integration Guide](#integration-guide)
- [Querying Telemetry](#querying-telemetry)
- [CLI Commands](#cli-commands)
- [Performance Considerations](#performance-considerations)
- [Best Practices](#best-practices)

---

## Architecture

### Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Application Layer                         │
│  (core/start.py, logic/dispatcher.py, logic/implementor.py)  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                 Telemetry Manager API                        │
│  (data/telemetry_manager.py)                                │
│  - start_operation()                                          │
│  - record_event()                                            │
│  - record_metric()                                           │
│  - record_resource_usage()                                   │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                 Telemetry Database                           │
│  (telemetry.db)                                              │
│  - operations                                                │
│  - events                                                    │
│  - metrics                                                   │
│  - resources                                                 │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                 Correlation Layer                             │
│  Links to activity.db, task.db, snapshots.db               │
└─────────────────────────────────────────────────────────────┘
```

### Key Features

- **Hierarchical Operation Tracking**: Parent-child relationships for nested operations
- **Automatic Metrics Collection**: Time, tokens, resources captured automatically
- **Event Logging**: Structured events with severity and context
- **Resource Monitoring**: CPU, memory, disk I/O tracking
- **Thread-Safe**: Supports concurrent operations with RLock
- **Correlation**: Links to task, activity, and checkpoint data

---

## Database Schema

### Operations Table

```sql
CREATE TABLE IF NOT EXISTS operations (
    id TEXT PRIMARY KEY,                    -- UUID
    parent_id TEXT,                         -- Parent operation UUID (nullable)
    operation_type TEXT NOT NULL,           -- task_breakdown, implementation, verification, etc.
    title TEXT NOT NULL,                    -- Human-readable title
    start_time TEXT NOT NULL,               -- ISO 8601 timestamp
    end_time TEXT,                          -- ISO 8601 timestamp (nullable)
    status TEXT NOT NULL,                   -- started, completed, failed, cancelled
    activity_id TEXT,                       -- Foreign key to activity.db
    metadata TEXT,                          -- JSON string
    FOREIGN KEY (parent_id) REFERENCES operations(id)
);

CREATE INDEX IF NOT EXISTS idx_operations_type ON operations(operation_type);
CREATE INDEX IF NOT EXISTS idx_operations_status ON operations(status);
CREATE INDEX IF NOT EXISTS idx_operations_parent ON operations(parent_id);
```

### Events Table

```sql
CREATE TABLE IF NOT EXISTS events (
    id TEXT PRIMARY KEY,                    -- UUID
    operation_id TEXT NOT NULL,             -- Foreign key to operations
    event_type TEXT NOT NULL,               -- started, completed, failed, checkpointed, etc.
    severity TEXT NOT NULL,                 -- info, warning, error, critical
    message TEXT,                          -- Event message
    timestamp TEXT NOT NULL,                -- ISO 8601 timestamp
    context TEXT,                           -- JSON string
    FOREIGN KEY (operation_id) REFERENCES operations(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_events_operation ON events(operation_id);
CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);
CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp);
```

### Metrics Table

```sql
CREATE TABLE IF NOT EXISTS metrics (
    id TEXT PRIMARY KEY,                    -- UUID
    operation_id TEXT NOT NULL,             -- Foreign key to operations
    metric_name TEXT NOT NULL,              -- e.g., tokens_used, time_elapsed
    metric_value REAL NOT NULL,             -- Numeric value
    unit TEXT,                              -- e.g., seconds, tokens, bytes
    timestamp TEXT NOT NULL,                -- ISO 8601 timestamp
    context TEXT,                           -- JSON string
    FOREIGN KEY (operation_id) REFERENCES operations(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_metrics_operation ON metrics(operation_id);
CREATE INDEX IF NOT EXISTS idx_metrics_name ON metrics(metric_name);
```

### Resources Table

```sql
CREATE TABLE IF NOT EXISTS resources (
    id TEXT PRIMARY KEY,                    -- UUID
    operation_id TEXT NOT NULL,             -- Foreign key to operations
    resource_type TEXT NOT NULL,            -- cpu, memory, disk_io, network
    resource_value REAL NOT NULL,           -- Numeric value
    unit TEXT,                              -- e.g., percent, mb, mb/s
    timestamp TEXT NOT NULL,                -- ISO 8601 timestamp
    FOREIGN KEY (operation_id) REFERENCES operations(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_resources_operation ON resources(operation_id);
CREATE INDEX IF NOT EXISTS idx_resources_type ON resources(resource_type);
CREATE INDEX IF NOT EXISTS idx_resources_timestamp ON resources(timestamp);
```

---

## Telemetry Manager API

### Initialization

```python
from data.telemetry_manager import TelemetryManager

# Initialize telemetry manager
telemetry = TelemetryManager(
    db_path="telemetry.db",
    enabled=True
)
```

### Context Manager API

Track operations automatically using Python's context manager:

```python
from data.telemetry_manager import TelemetryManager

telemetry = TelemetryManager()

# Track an operation
with telemetry.track_operation("implementation", "Implement user authentication") as op:
    op.record_event("test_generation", "info", "Starting test generation")
    
    # ... perform work ...
    
    op.record_event("test_generation", "info", "Completed test generation")
    op.record_metric("tokens_used", 1250)
```

The context manager automatically:
- Records operation start and end times
- Sets status to "completed" on success, "failed" on exception
- Captures timing metrics automatically

### Decorator API

Track function calls using decorators:

```python
from data.telemetry_manager import telemetry

@telemetry.track_decorator(operation_type="implementation")
def implement_task(task_id: int):
    # ... implementation ...
    return result

# Optionally specify title
@telemetry.track_decorator(operation_type="planning")
def breakdown_requirements(requirements: str, title: str = "Task breakdown"):
    # ... breakdown ...
    return tasks
```

### Manual API

For fine-grained control, use manual methods:

```python
# Start an operation
op_id = telemetry.start_operation(
    operation_type="implementation",
    title="Implement user authentication",
    parent_id=parent_op_id,  # Optional
    activity_id=activity_id,  # Optional
    metadata={"task_id": 42}
)

# Record events
telemetry.record_event(
    operation_id=op_id,
    event_type="test_generation",
    severity="info",
    message="Starting test generation",
    context={"test_file": "test_auth.py"}
)

# Record metrics
telemetry.record_metric(
    operation_id=op_id,
    metric_name="tokens_used",
    metric_value=1250.0,
    unit="tokens"
)

# Record resource usage
telemetry.record_resource(
    operation_id=op_id,
    resource_type="memory",
    resource_value=145.5,
    unit="mb"
)

# End operation
telemetry.end_operation(
    operation_id=op_id,
    status="completed"  # or "failed", "cancelled"
)
```

### Query API

Query telemetry data for analytics and debugging:

```python
# Query operations
operations = telemetry.query_operations(
    operation_type="implementation",
    status="failed",
    start_time="2026-01-21T00:00:00Z",
    end_time="2026-01-21T23:59:59Z"
)

# Get operation details
op = telemetry.get_operation(operation_id)
print(f"Status: {op['status']}")
print(f"Duration: {op['duration']} seconds")

# Get operation events
events = telemetry.get_events(operation_id)

# Get operation metrics
metrics = telemetry.get_metrics(operation_id)

# Search events
events = telemetry.search_events(
    event_type="failed",
    severity="error",
    keyword="timeout"
)

# Get operation stats
stats = telemetry.get_operation_stats(
    operation_type="implementation"
)
print(f"Average duration: {stats['avg_duration']}")
print(f"Total tokens: {stats['total_tokens']}")
```

---

## Integration Guide

### Integrating with LLM Provider

The telemetry manager is automatically integrated with the LLM provider:

```python
# LLM calls are automatically tracked
# Provider wraps calls with telemetry:
# - Records LLM call details
# - Tracks prompt/response sizes
# - Monitors token usage
# - Captures latency and retry attempts
```

### Integrating with File Operations

File operations are tracked automatically:

```python
# File reads are logged with path and size
# File writes are logged with path, size, and diff summary
# Git operations are recorded (add, commit, checkout)
```

### Integrating with Custom Operations

Add telemetry to your custom operations:

```python
from data.telemetry_manager import telemetry

def my_custom_operation(data):
    with telemetry.track_operation("custom", "Process data") as op:
        op.record_event("validation", "info", "Validating input data")
        
        # Validate
        if not validate(data):
            raise ValueError("Invalid data")
        
        op.record_event("validation", "info", "Data validated")
        op.record_metric("input_size", len(data))
        
        # Process
        result = process(data)
        
        op.record_metric("output_size", len(result))
        op.record_metric("processing_time", time.time() - start)
        
        return result
```

### Thread-Safe Operations

Telemetry is thread-safe and supports concurrent operations:

```python
import concurrent.futures
from data.telemetry_manager import telemetry

def process_task(task_id):
    with telemetry.track_operation("parallel", f"Process task {task_id}") as op:
        # ... process task ...
        return result

# Run multiple operations concurrently
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
    futures = [executor.submit(process_task, i) for i in range(10)]
    results = [f.result() for f in futures]
```

---

## Querying Telemetry

### Basic Queries

```python
# Get all failed implementations
failed_impls = telemetry.query_operations(
    operation_type="implementation",
    status="failed"
)

# Get operations in time range
recent_ops = telemetry.query_operations(
    start_time="2026-01-21T00:00:00Z",
    end_time="2026-01-21T23:59:59Z"
)

# Get child operations
child_ops = telemetry.query_operations(
    parent_id=parent_op_id
)
```

### Complex Queries

```python
# Get failed operations with high token usage
failed_high_tokens = []
for op in telemetry.query_operations(status="failed"):
    metrics = telemetry.get_metrics(op['id'])
    tokens = sum(m['metric_value'] for m in metrics if m['metric_name'] == 'tokens_used')
    if tokens > 5000:
        failed_high_tokens.append({
            'operation': op,
            'tokens': tokens
        })

# Get operations with specific events
ops_with_errors = []
for op in telemetry.query_operations():
    events = telemetry.get_events(op['id'])
    if any(e['severity'] == 'error' for e in events):
        ops_with_errors.append(op)
```

### Analytics Queries

```python
# Get operation statistics by type
stats_by_type = {}
for op_type in ["task_breakdown", "implementation", "verification"]:
    stats = telemetry.get_operation_stats(operation_type=op_type)
    stats_by_type[op_type] = stats

# Get average resource usage
avg_memory = telemetry.get_average_resource(
    resource_type="memory",
    operation_type="implementation"
)
```

### Export Telemetry

```python
# Export operation details to JSON
telemetry.export_operation(
    operation_id=op_id,
    output_path="operation_export.json",
    format="json"
)

# Export all operations to CSV
telemetry.export_operations(
    output_path="operations_export.csv",
    format="csv"
)
```

---

## CLI Commands

### List Operations

```bash
# List all operations
l4-dev telemetry list

# Filter by type
l4-dev telemetry list --operation-type implementation

# Filter by status
l4-dev telemetry list --status failed

# Filter by time range
l4-dev telemetry list --start-time "2026-01-21T00:00:00Z" --end-time "2026-01-21T23:59:59Z"

# Limit results
l4-dev telemetry list --limit 10
```

### Show Operation Details

```bash
# Show operation details
l4-dev telemetry show --id <operation-id>

# Include events
l4-dev telemetry show --id <operation-id> --events

# Include metrics
l4-dev telemetry show --id <operation-id> --metrics

# Include resources
l4-dev telemetry show --id <operation-id> --resources
```

### Export Operation

```bash
# Export to JSON
l4-dev telemetry export --id <operation-id> --export output.json --format json

# Export to CSV
l4-dev telemetry export --id <operation-id> --export output.csv --format csv
```

### Get Statistics

```bash
# Get statistics by type
l4-dev telemetry stats --type implementation

# Get all statistics
l4-dev telemetry stats
```

---

## Performance Considerations

### Telemetry Overhead

The telemetry system is designed for minimal performance impact:

| Operation | Overhead | Notes |
|-----------|----------|-------|
| start_operation() | <1ms | Database insert |
| record_event() | <1ms | Database insert |
| record_metric() | <1ms | Database insert |
| end_operation() | <2ms | Database update + cleanup |
| query_operations() | 10-100ms | Depends on filters and result size |

### Resource Monitoring Overhead

Resource monitoring is sampled at 1-second intervals by default:

| Metric | Overhead per sample |
|--------|---------------------|
| CPU usage | <0.1ms |
| Memory usage | <0.5ms |
| Disk I/O | <1ms |

Total overhead: ~1.6ms per sample (negligible for most operations)

### Database Size

Typical telemetry database growth:

| Operations per day | DB size after 30 days |
|--------------------|----------------------|
| 100 | ~5 MB |
| 500 | ~25 MB |
| 1000 | ~50 MB |

Use database migration and cleanup policies to manage growth.

### Optimization Tips

1. **Disable Telemetry for Performance-Critical Operations**:
   ```python
   telemetry = TelemetryManager(enabled=False)
   ```

2. **Use Batch Inserts for High-Volume Events**:
   ```python
   telemetry.record_events_batch(events_list)
   ```

3. **Archive Old Telemetry Data**:
   ```python
   telemetry.archive_old_data(days_to_keep=30, archive_path="archive/")
   ```

4. **Use Indexes for Fast Queries**:
   - Database indexes are created automatically
   - Add custom indexes for frequent query patterns

---

## Best Practices

### 1. Use Descriptive Operation Titles

```python
# Good
with telemetry.track_operation("implementation", "Implement user authentication JWT token validation") as op:

# Bad
with telemetry.track_operation("implementation", "Do stuff") as op:
```

### 2. Record Relevant Events

```python
# Record meaningful events at key points
op.record_event("validation", "info", "Input validation completed")
op.record_event("processing", "info", "Starting data processing")
op.record_event("error", "error", "Failed to connect to database", context={"error": str(e)})
```

### 3. Track Important Metrics

```python
# Track metrics that matter for your use case
op.record_metric("tokens_used", total_tokens, unit="tokens")
op.record_metric("processing_time", elapsed_time, unit="seconds")
op.record_metric("items_processed", count, unit="items")
op.record_metric("cache_hit_rate", hit_rate, unit="percent")
```

### 4. Use Parent-Child Relationships

```python
# Hierarchical operations for better understanding
with telemetry.track_operation("task_execution", "Execute task 42") as parent:
    with telemetry.track_operation("planning", "Plan task breakdown") as child1:
        # Planning logic
    
    with telemetry.track_operation("implementation", "Implement task") as child2:
        # Implementation logic
    
    with telemetry.track_operation("verification", "Verify implementation") as child3:
        # Verification logic
```

### 5. Include Context in Events and Metrics

```python
# Add context for better debugging
op.record_event(
    "llm_call",
    "info",
    "Called LLM for code generation",
    context={
        "model": "gpt-4",
        "temperature": 0.7,
        "prompt_tokens": 1200,
        "max_tokens": 500
    }
)

op.record_metric(
    "response_time",
    2.5,
    unit="seconds",
    context={"model": "gpt-4", "endpoint": "api.openai.com"}
)
```

### 6. Handle Exceptions Gracefully

```python
# The context manager handles exceptions automatically
try:
    with telemetry.track_operation("implementation", "Implement feature") as op:
        # ... implementation ...
        raise ValueError("Something went wrong")
except ValueError as e:
    # Operation is automatically marked as "failed"
    # Exception details are logged
    logger.error(f"Operation failed: {e}")
```

### 7. Use Decorators for Simple Functions

```python
# Use decorator for functions that don't need custom event tracking
@telemetry.track_decorator(operation_type="validation")
def validate_data(data):
    # ... validation ...
    return is_valid
```

### 8. Regularly Query and Analyze Telemetry

```python
# Monitor operation performance
stats = telemetry.get_operation_stats(operation_type="implementation")
if stats['avg_duration'] > 30:
    logger.warning(f"Implementation operations are slow: {stats['avg_duration']}s average")

# Monitor failure rates
failed_ops = telemetry.query_operations(status="failed")
if len(failed_ops) > 10:
    logger.warning(f"High failure rate: {len(failed_ops)} failed operations")
```

### 9. Archive and Cleanup Old Data

```python
# Archive data older than 30 days
telemetry.archive_old_data(days_to_keep=30, archive_path="archive/")

# Delete archived data
telemetry.delete_archived_data(archive_path="archive/")
```

### 10. Export Telemetry for Analysis

```python
# Export for external analysis tools
telemetry.export_operations(
    output_path="telemetry_export.csv",
    format="csv"
)

# Import into analysis tools (Excel, pandas, etc.)
# pandas.read_csv('telemetry_export.csv')
```

---

## Troubleshooting

### Database Locked Error

**Problem**: Telemetry database is locked by another process.

**Solution**: Ensure only one TelemetryManager instance is running, or use connection pooling.

### Slow Query Performance

**Problem**: Querying telemetry is slow.

**Solution**:
1. Add indexes for frequently queried fields
2. Use time range filters to reduce result size
3. Archive old data to reduce database size

### High Memory Usage

**Problem**: Telemetry manager is using too much memory.

**Solution**:
1. Disable resource monitoring if not needed
2. Reduce monitoring frequency
3. Archive old telemetry data regularly

### Missing Events

**Problem**: Some events are not being recorded.

**Solution**: Check that telemetry is enabled and that the database is writable.

---

## API Reference

### TelemetryManager

#### Constructor

```python
TelemetryManager(db_path: str = "telemetry.db", enabled: bool = True)
```

#### Methods

**start_operation**
```python
start_operation(
    operation_type: str,
    title: str,
    parent_id: Optional[str] = None,
    activity_id: Optional[str] = None,
    metadata: Optional[Dict] = None
) -> str
```

**end_operation**
```python
end_operation(operation_id: str, status: str) -> None
```

**record_event**
```python
record_event(
    operation_id: str,
    event_type: str,
    severity: str,
    message: Optional[str] = None,
    context: Optional[Dict] = None
) -> None
```

**record_metric**
```python
record_metric(
    operation_id: str,
    metric_name: str,
    metric_value: float,
    unit: Optional[str] = None,
    context: Optional[Dict] = None
) -> None
```

**record_resource**
```python
record_resource(
    operation_id: str,
    resource_type: str,
    resource_value: float,
    unit: Optional[str] = None
) -> None
```

**track_operation** (Context Manager)
```python
track_operation(operation_type: str, title: str) -> OperationContext
```

**track_decorator** (Decorator)
```python
track_decorator(operation_type: str)
```

**query_operations**
```python
query_operations(
    operation_type: Optional[str] = None,
    status: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    parent_id: Optional[str] = None
) -> List[Dict]
```

**get_operation**
```python
get_operation(operation_id: str) -> Dict
```

**get_events**
```python
get_events(operation_id: str) -> List[Dict]
```

**get_metrics**
```python
get_metrics(operation_id: str) -> List[Dict]
```

**get_operation_stats**
```python
get_operation_stats(operation_type: Optional[str] = None) -> Dict
```

**search_events**
```python
search_events(
    event_type: Optional[str] = None,
    severity: Optional[str] = None,
    keyword: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None
) -> List[Dict]
```

**export_operation**
```python
export_operation(
    operation_id: str,
    output_path: str,
    format: str = "json"
) -> None
```

**archive_old_data**
```python
archive_old_data(days_to_keep: int, archive_path: str) -> None
```

---

## Conclusion

The L4D V3 Telemetry System provides comprehensive operation tracking and analytics capabilities with minimal performance overhead. By following the best practices outlined in this document, you can gain deep insights into your development operations and improve efficiency and reliability.

For more information, see:
- [LOGGING.md](LOGGING.md) - Structured logging integration
- [RESUMABILITY.md](RESUMABILITY.md) - Checkpoint and recovery
- [SESSION_MANAGEMENT.md](SESSION_MANAGEMENT.md) - Session persistence