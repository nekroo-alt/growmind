# L4D V3 Enhancement Tasks: Telemetry, Logging & Robust Resumability

## Overview

This document defines a series of tasks to enhance L4D v2 with comprehensive telemetry, structured logging, and robust resumability capabilities. The goal is to create a production-ready system that can gracefully handle interruptions, errors, and unexpected shutdowns while maintaining full state recovery capabilities.

## Current Limitations in V2

1. **Limited Telemetry**: No systematic tracking of operations, resource usage, or performance metrics
2. **Ad-hoc Logging**: Inconsistent logging across modules, no structured log format
3. **Poor Resumability**: Cannot recover from interrupted operations or unexpected shutdowns
4. **No State Checkpoints**: No way to save and restore system state at critical points
5. **Error Recovery**: Limited ability to recover from errors and continue work
6. **No Rollback**: Cannot undo partial changes when operations fail
7. **Session Isolation**: Each session is isolated, cannot continue previous sessions
8. **Black Box Operations**: Limited visibility into what's happening during execution

## Enhancement Goals

1. **Comprehensive Telemetry**: Track all operations, decisions, and resource usage
2. **Structured Logging**: Consistent, searchable logs with appropriate levels and context
3. **Robust Resumability**: Ability to resume from any checkpoint after interruption
4. **Error Recovery**: Graceful handling of errors with clear recovery paths
5. **State Checkpoints**: Save system state at critical points for recovery
6. **Transaction Support**: Atomic operations with rollback capabilities
7. **Session Management**: Track and resume sessions across multiple runs
8. **User Experience**: Clear feedback, progress indicators, and recovery suggestions

---

## Task Categories

### Phase 1: Telemetry Infrastructure
### Phase 2: Structured Logging System
### Phase 3: State Checkpointing & Recovery
### Phase 4: Error Handling & Resilience
### Phase 5: Session Management & Persistence
### Phase 6: User Experience Enhancements
### Phase 7: Integration and Testing

---

## Phase 1: Telemetry Infrastructure

### Task 1.1: Telemetry Data Schema Design ✅ **COMPLETE**

**Title**: Design telemetry database schema for comprehensive operation tracking

**Acceptance Criteria**:
- ✅ Design `telemetry.db` schema with tables for operations, events, metrics, and resources
- ✅ Define operation types: task_breakdown, implementation, verification, context_collection
- ✅ Define event types: started, completed, failed, interrupted, checkpointed
- ✅ Define metrics: tokens_used, time_elapsed, memory_usage, cache_hits
- ✅ Support hierarchical operations (parent-child relationships)
- ✅ Include foreign key to `activity.db` for correlation

**Module**: `data/db_manager.py` (enhance), new `data/telemetry_manager.py`

**Estimated Lines**: ~100

**Dependencies**: None

**Technical Notes**:
- ✅ SQLite database for telemetry storage
- ✅ Use UUIDs for operation and event IDs
- ✅ Index on timestamp, operation_type, and status for fast queries
- ✅ Include JSON columns for flexible metadata storage
- ✅ Create database migration system for schema evolution

---

### Task 1.2: Telemetry Manager Implementation ✅ **COMPLETE**

**Title**: Implement TelemetryManager for operation tracking

**Acceptance Criteria**:
- ✅ `TelemetryManager` can start, end, and cancel operations
- ✅ Record events with timestamps, severity, and context
- ✅ Capture metrics automatically (time, tokens, resources)
- ✅ Support hierarchical operation tracking
- ✅ Thread-safe operations for concurrent access
- ✅ Query interface for analytics and debugging

**Module**: `data/telemetry_manager.py` (new)

**Estimated Lines**: ~150

**Dependencies**: Task 1.1

**Technical Notes**:
- ✅ Context manager API for automatic operation tracking:
  ```python
  with telemetry.track_operation("implementation", "Task 42") as op:
      op.record_event("test_generation", "info", "Starting test generation")
      # ... perform work ...
      op.record_event("test_generation", "info", "Completed test generation")
      op.record_metric("tokens_used", 1250)
  ```
- ✅ Decorator support for function tracking:
  ```python
  @telemetry.track_decorator()
  def implement_task(task_id):
      ...
  ```
- ✅ Auto-capture timing and resource usage
- ✅ Thread-safe with RLock for concurrent access
- ✅ Query interface: `query_operations()`, `get_operation_stats()`, `search_events()`

---

### Task 1.3: LLM Call Telemetry Integration ✅ **COMPLETE**

**Title**: Integrate telemetry with LLM provider for call tracking

**Acceptance Criteria**:
- ✅ Track all LLM calls with request/response details
- ✅ Record prompt size, response size, and token counts
- ✅ Track latency and retry attempts
- ✅ Log model, temperature, and other parameters
- ✅ Capture errors and fallbacks
- Support streaming call metrics

**Module**: `llm_base/provider.py` (enhance), `data/telemetry_manager.py`

**Estimated Lines**: ~80

**Dependencies**: Task 1.2

**Technical Notes**:
- ✅ Wrap LLM provider methods with telemetry
- ✅ Record call details before and after
- Handle streaming responses differently
- ✅ Track costs (tokens * model pricing)
- ✅ Support multiple LLM providers

---

### Task 1.4: File Operation Telemetry ✅ **COMPLETE**

**Title**: Track file read/write operations for audit trail

**Acceptance Criteria**:
- ✅ Log all file reads with file path and size
- ✅ Log all file writes with file path, size, and diff summary
- ✅ Track file modifications during task execution
- ✅ Record git operations (add, commit, checkout)
- ✅ Support file operation replay for debugging

**Module**: `data/telemetry_manager.py` (enhance)

**Estimated Lines**: ~60

**Dependencies**: Task 1.2

**Technical Notes**:
- ✅ Wrap file I/O operations with telemetry
- ✅ Use git to track actual file changes
- ✅ Store diff hashes for change verification
- ✅ Monitor file system for external changes

---

### Task 1.5: Resource Usage Monitoring ✅ **COMPLETE**

**Title**: Implement resource usage monitoring (CPU, memory, disk)

**Acceptance Criteria**:
- ✅ Monitor CPU usage during operations
- ✅ Track memory usage and allocation
- ✅ Monitor disk I/O and space usage
- ✅ Track network usage (for LLM API calls)
- ✅ Alert on resource exhaustion
- ✅ Generate resource usage reports

**Module**: `data/telemetry_manager.py` (enhance)

**Estimated Lines**: ~80

**Dependencies**: Task 1.2

**Technical Notes**:
- ✅ Use psutil for cross-platform monitoring
- ✅ Sample at regular intervals (e.g., every 1 second)
- ✅ Track peak and average usage
- ✅ Correlate resource usage with operations
- ✅ Set thresholds for warnings and alerts

---

## Phase 2: Structured Logging System

### Task 2.1: Logger Configuration and Setup ✅ **COMPLETE**

**Title**: Configure structured logger with multiple handlers

**Acceptance Criteria**:
- ✅ Configure Python logging with structured JSON format
- ✅ Setup console handler with color-coded output
- ✅ Setup file handler with rotation (max 10MB, keep 5 files)
- ✅ Setup separate error log file for critical issues
- ✅ Configure log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- ✅ Support log filtering by module and operation

**Module**: `core/logging_config.py` (new)

**Estimated Lines**: ~80

**Dependencies**: None

**Technical Notes**:
- Use structlog for structured logging
- JSON format for machine parsing, colored text for humans
- Configure different levels for development vs production
- Include request/session ID in all log entries
- Support log aggregation (ELK, Splunk, etc.)

---

### Task 2.2: Standardized Log Messages ✅ **COMPLETE**

**Title**: Define standard log message format and conventions

**Acceptance Criteria**:
- ✅ Define log message template for each operation type
- ✅ Include operation_id, timestamp, level, module, function
- ✅ Include context (task_id, file_path, etc.)
- ✅ Use action verbs for consistency (started, completed, failed)
- ✅ Include error details with stack traces
- ✅ Support log message templates with parameters

**Module**: `core/logging_config.py` (enhance)

**Estimated Lines**: ~50

**Dependencies**: Task 2.1

**Technical Notes**:
- ✅ Example format:
  ```json
  {
    "timestamp": "2026-01-21T00:15:36Z",
    "level": "INFO",
    "operation_id": "uuid-123",
    "task_id": 42,
    "module": "logic.implementor",
    "message": "Task implementation started",
    "context": {
      "task_title": "Add user authentication",
      "estimated_lines": 25
    }
  }
  ```
- ✅ Create logging helpers for common patterns
- ✅ Document log message conventions

---

### Task 2.3: Integration with Telemetry

**Title**: Correlate logs with telemetry operations

**Acceptance Criteria**:
- Link log entries to operation IDs
- Include telemetry metrics in log context
- Support querying logs by operation or task
- Generate operation timelines from logs
- Export logs with telemetry for analysis

**Module**: `data/telemetry_manager.py` (enhance), `core/logging_config.py`

**Estimated Lines**: ~60

**Dependencies**: Task 1.2, 2.2

**Technical Notes**:
- Use operation_id as correlation ID
- Store log references in telemetry records
- Create log-telemetry join queries
- Support log export to external systems

---

### Task 2.4: Log Analysis and Search Tools

**Title**: Implement log search and analysis utilities

**Acceptance Criteria**:
- Search logs by operation, task, error, or time range
- Filter logs by level, module, or custom fields
- Generate log summaries and statistics
- Identify common error patterns
- Create operation timelines from logs
- Export logs for external analysis

**Module**: `core/log_analyzer.py` (new), CLI command `l4-dev logs`

**Estimated Lines**: ~100

**Dependencies**: Task 2.3

**Technical Notes**:
- Use SQLite FTS (Full-Text Search) for log queries
- Support complex queries (AND, OR, NOT)
- Generate reports (error frequency, operation duration, etc.)
- Create visualizations (timeline, charts) if possible
- CLI interface for ad-hoc analysis

---

## Phase 3: State Checkpointing & Recovery

### Task 3.1: State Snapshot Schema

**Title**: Design state snapshot schema for checkpointing

**Acceptance Criteria**:
- Design `snapshots.db` schema for storing system state
- Define snapshot types: operation_start, operation_end, task_complete, task_failed
- Include database state (task.db, activity.db) in snapshots
- Include file system state (git status, modified files)
- Include context and cache state
- Support incremental snapshots (delta only)

**Module**: `data/db_manager.py` (enhance), new `data/checkpoint_manager.py`

**Estimated Lines**: ~80

**Dependencies**: None

**Technical Notes**:
- SQLite database for snapshots
- Store as compressed JSON or pickle
- Use file hashes for efficient storage
- Support snapshot chaining (parent-child)
- Include metadata: timestamp, operation_id, reason

---

### Task 3.2: Checkpoint Manager Implementation

**Title**: Implement CheckpointManager for state save/restore

**Acceptance Criteria**:
- `CheckpointManager` can create, list, and restore snapshots
- Create automatic checkpoints before critical operations
- Support manual checkpoint creation
- Restore system state from any checkpoint
- Validate state integrity before/after restore
- Rollback to previous checkpoint on failure

**Module**: `data/checkpoint_manager.py` (new)

**Estimated Lines**: ~150

**Dependencies**: Task 3.1

**Technical Notes**:
- Checkpoint lifecycle:
  ```python
  # Create checkpoint
  checkpoint_id = checkpoint.create("before_task_42", task_id=42)
  
  # Restore checkpoint
  checkpoint.restore(checkpoint_id)
  
  # Automatic rollback on error
  with checkpoint.rollback_on_error():
      # ... perform operation ...
  ```
- Validate state: check database integrity, file consistency
- Support selective restore (e.g., only task.db)

---

### Task 3.3: Database State Checkpointing

**Title**: Implement database state checkpoint and restore

**Acceptance Criteria**:
- Capture state of task.db and activity.db
- Capture state of telemetry.db and snapshots.db
- Support incremental database dumps
- Restore database to specific state
- Validate database integrity after restore
- Handle foreign key constraints during restore

**Module**: `data/checkpoint_manager.py` (enhance)

**Estimated Lines**: ~100

**Dependencies**: Task 3.2

**Technical Notes**:
- Use SQLite backup API for efficient snapshots
- Store as SQL dumps or binary copies
- Support point-in-time recovery using WAL mode
- Check referential integrity after restore
- Handle large databases efficiently

---

### Task 3.4: File System State Checkpointing

**Title**: Implement file system state checkpointing

**Acceptance Criteria**:
- Capture git state (HEAD, branch, working tree)
- Capture modified and untracked files
- Capture cache state (.l4_cache/)
- Restore file system to checkpoint state
- Handle merge conflicts on restore
- Preserve user work if safe

**Module**: `data/checkpoint_manager.py` (enhance)

**Estimated Lines**: ~120

**Dependencies**: Task 3.2

**Technical Notes**:
- Use git for version control integration
- Store git commit hash and diff
- For non-git files, store full snapshots or deltas
- Implement 3-way merge on restore
- Warn about lost changes
- Support dry-run restore to preview changes

---

### Task 3.5: Context and Cache Checkpointing

**Title**: Implement context and cache state checkpointing

**Acceptance Criteria**:
- Capture context engine state (loaded contexts, memoization)
- Capture cache manager state (AST analysis results)
- Capture LLM conversation history if relevant
- Restore context and cache from checkpoint
- Invalidate stale cache after restore
- Rebuild cache if needed

**Module**: `data/checkpoint_manager.py` (enhance)

**Estimated Lines**: ~80

**Dependencies**: Task 3.2, Task 4.1 (from V2)

**Technical Notes**:
- Serialize context engine state
- Include cache keys and values
- Validate cache consistency after restore
- Rebuild cache if corruption detected
- Handle cache eviction and size limits

---

### Task 3.6: Automatic Checkpoint Policy

**Title**: Define and implement automatic checkpoint policy

**Acceptance Criteria**:
- Create checkpoint before each task implementation
- Create checkpoint after successful task completion
- Create checkpoint before refactoring sprints
- Create checkpoint after N operations (configurable)
- Create checkpoint on error/interruption
- Clean up old checkpoints (keep last N, or time-based)

**Module**: `data/checkpoint_manager.py` (enhance)

**Estimated Lines**: ~70

**Dependencies**: Task 3.2

**Technical Notes**:
- Configurable checkpoint policy:
  ```python
  checkpoint_policy = {
      "before_task": True,
      "after_task": True,
      "before_refactor": True,
      "max_age_hours": 24,
      "max_count": 10
  }
  ```
- Implement checkpoint garbage collection
- Mark critical checkpoints (do not auto-delete)
- Support checkpoint expiration and archival

---

## Phase 4: Error Handling & Resilience

### Task 4.1: Error Classification and Taxonomy

**Title**: Define error taxonomy for better error handling

**Acceptance Criteria**:
- Define error categories: transient, permanent, retryable, user_action_required
- Define error sources: LLM, database, file system, git, user
- Define error severities: info, warning, error, critical
- Create error codes for common scenarios
- Document recovery strategies for each error type

**Module**: `core/error_handling.py` (new)

**Estimated Lines**: ~80

**Dependencies**: None

**Technical Notes**:
- Example error taxonomy:
  ```python
  ErrorType = Enum([
      'LLM_RATE_LIMIT',  # transient, retryable
      'LLM_TIMEOUT',     # transient, retryable
      'DB_LOCKED',       # transient, retryable
      'FILE_NOT_FOUND',   # permanent, user_action_required
      'GIT_CONFLICT',    # permanent, user_action_required
  ])
  ```
- Create error base class with metadata
- Support error chaining and causes

---

### Task 4.2: Retry Logic with Exponential Backoff

**Title**: Implement retry logic for transient errors

**Acceptance Criteria**:
- Automatically retry transient errors with exponential backoff
- Configurable retry count and backoff strategy
- Jitter to avoid thundering herd
- Log retry attempts with metrics
- Stop retrying on permanent errors
- Support custom retry policies per operation

**Module**: `core/error_handling.py` (enhance)

**Estimated Lines**: ~70

**Dependencies**: Task 4.1

**Technical Notes**:
- Use tenacity or retrying library
- Example retry policy:
  ```python
  @retry(
      stop=stop_after_attempt(3),
      wait=wait_exponential(multiplier=1, min=4, max=10),
      retry=retry_if_exception_type(TransientError),
      before_sleep=log_retry_attempt
  )
  def call_llm():
      ...
  ```
- Track retry statistics in telemetry
- Circuit breaker pattern for cascading failures

---

### Task 4.3: Graceful Shutdown Handler

**Title**: Implement graceful shutdown on SIGINT/SIGTERM

**Acceptance Criteria**:
- Handle SIGINT (Ctrl+C) and SIGTERM gracefully
- Save state before shutdown
- Cancel in-progress operations cleanly
- Close database connections properly
- Flush logs and telemetry
- Create checkpoint if in critical operation
- Resume from checkpoint on next start

**Module**: `core/graceful_shutdown.py` (new)

**Estimated Lines**: ~80

**Dependencies**: Task 3.2

**Technical Notes**:
- Use signal handlers for SIGINT/SIGTERM
- Implement shutdown flag for operations to check
- Example:
  ```python
  def handle_interrupt(signum, frame):
      logger.info("Received interrupt, shutting down gracefully...")
      shutdown_requested.set()
      if in_critical_operation:
          checkpoint.create("interrupt_shutdown")
      cleanup_and_exit()
  ```
- Support forced shutdown (double Ctrl+C)

---

### Task 4.4: Error Recovery Strategies

**Title**: Implement recovery strategies for common errors

**Acceptance Criteria**:
- Auto-recover from database locks (retry with backoff)
- Auto-recover from LLM rate limits (exponential backoff)
- Auto-recover from transient network errors (retry)
- Suggest recovery steps for user-action errors
- Rollback to last checkpoint on unrecoverable errors
- Generate recovery reports

**Module**: `core/error_handling.py` (enhance)

**Estimated Lines**: ~100

**Dependencies**: Task 4.1, 4.2, 3.2

**Technical Notes**:
- Recovery strategy per error type:
  ```python
  recovery_strategies = {
      'LLM_RATE_LIMIT': retry_with_backoff,
      'DB_LOCKED': retry_with_backoff,
      'FILE_NOT_FOUND': ask_user_action,
      'CORRUPT_STATE': rollback_to_checkpoint
  }
  ```
- Track recovery success rates in telemetry
- Learn from past errors and adjust strategies

---

### Task 4.5: Transaction Support for Multi-Step Operations

**Title**: Implement transaction-like semantics for operations

**Acceptance Criteria**:
- Wrap multi-step operations in transactions
- Rollback all steps if any step fails
- Support nested transactions
- Track transaction state (pending, committed, rolled back)
- Log transaction lifecycle
- Support manual rollback

**Module**: `core/transactions.py` (new)

**Estimated Lines**: ~120

**Dependencies**: Task 3.2, 4.1

**Technical Notes**:
- Transaction API:
  ```python
  with transaction.start() as tx:
      # Step 1: Modify database
      # Step 2: Write files
      # Step 3: Run tests
      tx.commit()  # all-or-nothing
  # If any step fails, auto-rollback
  ```
- Use checkpoints for rollback
- Track rollback operations in telemetry
- Support partial commits with validation

---

### Task 4.6: Health Checks and Self-Diagnostics

**Title**: Implement health checks for system components

**Acceptance Criteria**:
- Check database connectivity and integrity
- Check git repository state
- Check cache validity and size
- Check file system permissions and space
- Check LLM API connectivity
- Generate health report with recommendations

**Module**: `core/health_check.py` (new), CLI command `l4-dev health`

**Estimated Lines**: ~100

**Dependencies**: Task 3.2, 4.1

**Technical Notes**:
- Health check categories: critical, warning, info
- Example health check:
  ```python
  health = {
      'status': 'healthy',
      'checks': {
          'database': {'status': 'ok', 'latency_ms': 12},
          'git': {'status': 'ok', 'branch': 'main'},
          'cache': {'status': 'warning', 'size_mb': 95},
          'llm_api': {'status': 'ok', 'latency_ms': 450}
      }
  }
  ```
- Run health checks before critical operations
- Auto-fix minor issues when possible

---

## Phase 5: Session Management & Persistence

### Task 5.1: Session State Schema

**Title**: Design session state database schema

**Acceptance Criteria**:
- Design `sessions.db` schema for tracking sessions
- Track session start/end times
- Track active operations and tasks
- Track session checkpoints
- Track user preferences and configuration
- Support session resumption

**Module**: `data/db_manager.py` (enhance), new `core/session_manager.py`

**Estimated Lines**: ~70

**Dependencies**: None

**Technical Notes**:
- Session fields: id, start_time, end_time, status, config
- Link sessions to operations and checkpoints
- Store session metadata (user, host, environment)
- Support concurrent sessions (one active, multiple paused)

---

### Task 5.2: Session Manager Implementation

**Title**: Implement SessionManager for session lifecycle

**Acceptance Criteria**:
- Create new session with unique ID
- Resume existing session from state
- List all sessions (active, paused, completed)
- Archive old sessions
- Export/import session state
- Merge sessions if needed

**Module**: `core/session_manager.py` (new)

**Estimated Lines**: ~120

**Dependencies**: Task 5.1

**Technical Notes**:
- Session API:
  ```python
  # Start new session
  session = manager.start_session()
  
  # Resume session
  session = manager.resume_session(session_id)
  
  # List sessions
  sessions = manager.list_sessions()
  ```
- Session state includes: task progress, current operation, checkpoint
- Validate session integrity before resume

---

### Task 5.3: Session Persistence and Recovery

**Title**: Implement session persistence across runs

**Acceptance Criteria**:
- Save session state to disk on shutdown
- Restore session state on startup
- Detect and recover from interrupted sessions
- Offer session resumption to user
- Merge interrupted session if work continued externally
- Clean up stale sessions

**Module**: `core/session_manager.py` (enhance), `core/start.py`

**Estimated Lines**: ~80

**Dependencies**: Task 5.2, 4.3

**Technical Notes**:
- Auto-detect interrupted sessions on startup
- Prompt user: "Resume previous session? [y/n]"
- Use checkpoints for state restoration
- Handle merge conflicts with external work
- Archive sessions after completion

---

### Task 5.4: Session Analytics and Reporting

**Title**: Generate session analytics and reports

**Acceptance Criteria**:
- Track session duration and productivity
- Calculate tasks completed per session
- Generate session timeline with key events
- Identify bottlenecks and errors
- Compare sessions over time
- Export session reports

**Module**: `core/session_manager.py` (enhance), `core/log_analyzer.py`

**Estimated Lines**: ~70

**Dependencies**: Task 5.2, 2.4

**Technical Notes**:
- Session metrics: total_time, tasks_completed, errors, retries
- Generate reports: daily, weekly, per project
- Visualize session activity (Gantt chart, timeline)
- Identify patterns: common errors, slow operations
- Support user productivity tracking

---

### Task 5.5: Configuration Persistence

**Title**: Persist user preferences and configuration

**Acceptance Criteria**:
- Save user preferences (LLM model, cache settings, etc.)
- Load preferences on startup
- Support configuration profiles (dev, prod)
- Validate configuration values
- Migrate configuration on version changes
- Reset to defaults if corrupted

**Module**: `core/config.py` (new or enhance existing)

**Estimated Lines**: ~90

**Dependencies**: Task 5.1

**Technical Notes**:
- Store config in JSON/YAML file (`.l4_config`)
- Example config:
  ```yaml
  llm:
    provider: "openai"
    model: "gpt-4"
    temperature: 0.7
  cache:
    enabled: true
    max_size_mb: 100
  logging:
    level: "INFO"
    file: "l4.log"
  ```
- Support environment variable overrides
- Schema validation with defaults

---

## Phase 6: User Experience Enhancements

### Task 6.1: Progress Indicators

**Title**: Implement real-time progress indicators for long operations

**Acceptance Criteria**:
- Show progress bars for multi-step operations
- Display estimated time remaining
- Show current step and total steps
- Update progress in real-time
- Support cancellation of operations
- Visual feedback for success/failure

**Module**: `core/ui.py` (new)

**Estimated Lines**: ~80

**Dependencies**: Task 1.2, 2.1

**Technical Notes**:
- Use tqdm or rich for progress bars
- Example:
  ```
  Implementing task 42: [████████░░] 80% (4/5 steps)
  ```
- Track operation progress from telemetry
- Support TTY and non-TTY environments

---

### Task 6.2: Interactive Error Messages

**Title**: Create helpful error messages with recovery suggestions

**Acceptance Criteria**:
- Display clear error messages in human-friendly language
- Show error context and relevant logs
- Suggest recovery actions
- Provide command examples for manual recovery
- Link to documentation if available
- Support error reporting

**Module**: `core/error_handling.py` (enhance), `core/ui.py`

**Estimated Lines**: ~100

**Dependencies**: Task 4.1

**Technical Notes**:
- Example error message:
  ```
  Error: LLM API rate limit exceeded
  Context: During task implementation (operation_id: abc-123)
  Suggestion: Wait 1 minute and retry, or upgrade your API plan
  Command: l4-dev retry --operation-id abc-123
  Documentation: https://docs.l4.dev/errors/rate-limit
  ```
- Color-coded output (red for errors, yellow for warnings)
- Interactive help for complex errors

---

### Task 6.3: Status Dashboard

**Title**: Implement CLI status dashboard

**Acceptance Criteria**:
- Display current session status
- Show active operations and tasks
- Show recent activity and errors
- Show system health
- Show resource usage
- Refresh automatically or on demand

**Module**: `core/ui.py` (enhance), CLI command `l4-dev status`

**Estimated Lines**: ~100

**Dependencies**: Task 1.2, 2.1, 4.6, 5.2

**Technical Notes**:
- Dashboard layout:
  ```
  Session: abc-123 (running for 2h 15m)
  Task: 42 - Add user authentication (75% complete)
  Operation: Implementing (step 3/5)
  Health: OK (db: ok, git: ok, cache: ok)
  Resources: CPU 45%, Memory 2.1GB, Cache 82MB
  ```
- Support watch mode: `l4-dev status --watch`
- Export status to JSON for monitoring

---

### Task 6.4: Resume and Recovery CLI

**Title**: Implement CLI commands for resume and recovery

**Acceptance Criteria**:
- List available sessions and checkpoints
- Resume from specific session or checkpoint
- Show session history and changes
- Interactive recovery wizard
- Dry-run recovery preview
- Force recovery if needed

**Module**: CLI commands in `l4_cli.py`

**Estimated Lines**: ~120

**Dependencies**: Task 3.2, 5.2

**Technical Notes**:
- Commands:
  ```bash
  l4-dev resume              # Resume last session
  l4-dev resume --session-id abc-123
  l4-dev checkpoints list
  l4-dev checkpoints restore --id xyz-789
  l4-dev recover            # Interactive recovery wizard
  ```
- Support tab completion for session/checkpoint IDs
- Show recovery preview before applying

---

### Task 6.5: Telemetry and Log Queries

**Title**: Implement CLI for querying telemetry and logs

**Acceptance Criteria**:
- Query operations by type, status, time range
- Query logs by level, module, keyword
- Show operation details and metrics
- Export telemetry to CSV/JSON
- Generate analytics reports
- Visualize operation timelines

**Module**: CLI commands in `l4_cli.py`, `core/log_analyzer.py`

**Estimated Lines**: ~100

**Dependencies**: Task 1.2, 2.4

**Technical Notes**:
- Commands:
  ```bash
  l4-dev telemetry list --operation-type implementation --status failed
  l4-dev logs search --error --last 1h
  l4-dev report generate --period week
  ```
- Support filtering, sorting, and aggregation
- Output in table, JSON, or CSV format

---

## Phase 7: Integration and Testing

### Task 7.1: Integrate Telemetry into Core Modules

**Title**: Add telemetry tracking to all core modules

**Acceptance Criteria**:
- Add telemetry to all operations in `core/`
- Add telemetry to all operations in `logic/`
- Add telemetry to all operations in `retro/`
- Ensure consistent operation naming
- Record all critical events
- Achieve >95% telemetry coverage

**Module**: All modules in `core/`, `logic/`, `retro/`

**Estimated Lines**: ~200 (distributed)

**Dependencies**: Task 1.2

**Technical Notes**:
- Use context managers and decorators
- Track: started, completed, failed, metrics
- Example:
  ```python
  @telemetry.track_operation
  def breakdown_requirements():
      ...
  ```
- Review each module for telemetry opportunities

---

### Task 7.2: Integrate Logging into Core Modules

**Title**: Add structured logging to all core modules

**Acceptance Criteria**:
- Add logging to all functions in `core/`
- Add logging to all functions in `logic/`
- Add logging to all functions in `retro/`
- Use consistent log message format
- Include context (task_id, operation_id)
- Achieve >95% logging coverage

**Module**: All modules in `core/`, `logic/`, `retro/`

**Estimated Lines**: ~150 (distributed)

**Dependencies**: Task 2.1

**Technical Notes**:
- Use appropriate log levels (DEBUG for details, INFO for operations)
- Include structured context in log messages
- Example:
  ```python
  logger.info("Task implementation started", 
              task_id=task.id, 
              operation_id=op.id)
  ```
- Review each module for logging opportunities

---

### Task 7.3: Integrate Checkpointing into Workflow

**Title**: Add checkpointing to critical workflow steps

**Acceptance Criteria**:
- Create checkpoint before each task
- Create checkpoint after successful task
- Create checkpoint before refactoring
- Create checkpoint on error
- Restore checkpoint on resume
- Validate checkpoint integrity

**Module**: `core/start.py`, `logic/dispatcher.py`, `logic/implementor.py`

**Estimated Lines**: ~80

**Dependencies**: Task 3.2, 3.6

**Technical Notes**:
- Wrap critical operations with checkpoints
- Use rollback on error pattern
- Example:
  ```python
  with checkpoint.auto_rollback_on_error():
      task = implement_task(task_id)
      commit_changes()
  ```
- Test checkpoint/restore cycles

---

### Task 7.4: Test Telemetry System

**Title**: Write comprehensive tests for telemetry

**Acceptance Criteria**:
- Test TelemetryManager operations
- Test telemetry tracking for all modules
- Test telemetry queries and filtering
- Test telemetry-database correlation
- Test telemetry export and import
- Achieve >90% code coverage

**Module**: `tests/test_telemetry.py` (new)

**Estimated Lines**: ~150

**Dependencies**: Task 1.2, 7.1

**Technical Notes**:
- Use pytest for testing
- Mock LLM calls and file I/O
- Test concurrent operations
- Test error handling and recovery
- Performance tests for high-volume telemetry

---

### Task 7.5: Test Logging System

**Title**: Write comprehensive tests for logging

**Acceptance Criteria**:
- Test logger configuration and handlers
- Test structured log format
- Test log filtering and querying
- Test log-telemetry correlation
- Test log rotation and cleanup
- Achieve >90% code coverage

**Module**: `tests/test_logging.py` (new)

**Estimated Lines**: ~100

**Dependencies**: Task 2.1, 7.2

**Technical Notes**:
- Test different log levels
- Test log message parsing
- Test log search functionality
- Test log export formats
- Test error logging with stack traces

---

### Task 7.6: Test Checkpoint and Recovery

**Title**: Write comprehensive tests for checkpointing

**Acceptance Criteria**:
- Test checkpoint creation for all state types
- Test checkpoint restoration
- Test checkpoint rollback
- Test checkpoint validation
- Test session resume from checkpoint
- Test automatic checkpoint policy
- Achieve >90% code coverage

**Module**: `tests/test_checkpoint.py` (new)

**Estimated Lines**: ~150

**Dependencies**: Task 3.2, 7.3

**Technical Notes**:
- Test database, file system, and cache checkpoints
- Test checkpoint restoration and validation
- Test rollback scenarios
- Test session resume from various checkpoints
- Test checkpoint garbage collection
- Performance tests for large checkpoints

---

### Task 7.7: Integration Tests for Session Management

**Title**: Write comprehensive tests for session management

**Acceptance Criteria**:
- Test session creation and lifecycle
- Test session persistence and recovery
- Test session resumption after interruption
- Test configuration persistence
- Test session analytics and reporting
- Achieve >90% code coverage

**Module**: `tests/test_session.py` (new)

**Estimated Lines**: ~120

**Dependencies**: Task 5.2, 7.3

**Technical Notes**:
- Test session start, pause, resume, complete
- Test session state persistence
- Test interruption and recovery scenarios
- Test configuration save/load
- Test session analytics calculations
- Test concurrent session handling

---

### Task 7.8: End-to-End Testing

**Title**: Write end-to-end tests for complete workflows

**Acceptance Criteria**:
- Test complete development workflow with telemetry
- Test interrupted session and resume
- Test error recovery scenarios
- Test checkpoint/restore cycles
- Test resource exhaustion handling
- Achieve >80% scenario coverage

**Module**: `tests/integration/test_e2e.py` (new)

**Estimated Lines**: ~200

**Dependencies**: All previous tasks

**Technical Notes**:
- Simulate realistic user workflows
- Test interruption at various points
- Test recovery from different error types
- Measure telemetry and logging overhead
- Test performance with long-running sessions

---

### Task 7.9: Documentation and Migration Guide

**Title**: Document telemetry, logging, and resumability features

**Acceptance Criteria**:
- Document all new telemetry APIs and usage
- Document logging configuration and best practices
- Document checkpoint and recovery workflows
- Document session management features
- Create migration guide from V2 to V3
- Update PRD and tech.md with new architecture
- Add troubleshooting guide

**Module**: `meta/`, `docs/` (update existing), new `docs/TELEMETRY.md`

**Estimated Lines**: ~200

**Dependencies**: All previous tasks

**Technical Notes**:
- Document telemetry API with examples
- Document logging configuration options
- Document checkpoint usage patterns
- Document session lifecycle
- Create migration checklist from V2
- Update architecture diagrams
- Add troubleshooting scenarios and solutions

**Documentation to Create**:
- `v2/docs/TELEMETRY.md` - Complete telemetry system documentation
- `v2/docs/LOGGING.md` - Logging configuration and best practices
- `v2/docs/RESUMABILITY.md` - Checkpoint and recovery guide
- `v2/docs/SESSION_MANAGEMENT.md` - Session lifecycle and persistence
- `v2/docs/MIGRATION_V2_TO_V3.md` - Step-by-step migration guide
- `v2/docs/TROUBLESHOOTING.md` - Common issues and solutions
- `meta/prd.md` - Update with V3 enhancements
- `meta/tech.md` - Update with V3 modules and architecture

---

## Implementation Order

### Priority 1 (Core Infrastructure)
- Task 1.1: Telemetry Data Schema Design
- Task 1.2: Telemetry Manager Implementation
- Task 2.1: Logger Configuration and Setup
- Task 3.1: State Snapshot Schema
- Task 3.2: Checkpoint Manager Implementation

### Priority 2 (Telemetry & Logging Integration)
- Task 1.3: LLM Call Telemetry Integration
- Task 1.4: File Operation Telemetry
- Task 1.5: Resource Usage Monitoring
- Task 2.2: Standardized Log Messages
- Task 2.3: Integration with Telemetry
- Task 2.4: Log Analysis and Search Tools

### Priority 3 (State Management)
- Task 3.3: Database State Checkpointing
- Task 3.4: File System State Checkpointing
- Task 3.5: Context and Cache Checkpointing
- Task 3.6: Automatic Checkpoint Policy
- Task 4.1: Error Classification and Taxonomy
- Task 4.2: Retry Logic with Exponential Backoff

### Priority 4 (Resilience & Recovery)
- Task 4.3: Graceful Shutdown Handler
- Task 4.4: Error Recovery Strategies
- Task 4.5: Transaction Support for Multi-Step Operations
- Task 4.6: Health Checks and Self-Diagnostics

### Priority 5 (Session Management)
- Task 5.1: Session State Schema
- Task 5.2: Session Manager Implementation
- Task 5.3: Session Persistence and Recovery
- Task 5.4: Session Analytics and Reporting
- Task 5.5: Configuration Persistence

### Priority 6 (User Experience)
- Task 6.1: Progress Indicators
- Task 6.2: Interactive Error Messages
- Task 6.3: Status Dashboard
- Task 6.4: Resume and Recovery CLI
- Task 6.5: Telemetry and Log Queries

### Priority 7 (Integration)
- Task 7.1: Integrate Telemetry into Core Modules
- Task 7.2: Integrate Logging into Core Modules
- Task 7.3: Integrate Checkpointing into Workflow

### Priority 8 (Testing & Documentation)
- Task 7.4: Test Telemetry System
- Task 7.5: Test Logging System
- Task 7.6: Test Checkpoint and Recovery
- Task 7.7: Integration Tests for Session Management
- Task 7.8: End-to-End Testing
- Task 7.9: Documentation and Migration Guide

---

## Success Metrics

### System Reliability
- **Goal**: Reduce data loss from interruptions to 0%
- **Measurement**: Track successful recoveries after interruption

### Session Resumption
- **Goal**: Resume any interrupted session within 5 seconds
- **Measurement**: Measure session recovery time

### Error Recovery
- **Goal**: Auto-recover from 90% of transient errors without user intervention
- **Measurement**: Track error recovery success rates

### Telemetry Overhead
- **Goal**: <5% performance overhead from telemetry and logging
- **Measurement**: Compare operation times with/without telemetry

### Debugging Efficiency
- **Goal**: Reduce debugging time by 50% with improved logging
- **Measurement**: Track time to root cause analysis

### Checkpoint Performance
- **Goal**: Checkpoint creation <2 seconds, restore <3 seconds
- **Measurement**: Benchmark checkpoint operations

### User Experience
- **Goal**: 95% of users can resume interrupted work without assistance
- **Measurement**: Track successful self-recoveries

---

## Required Updates to Meta Documents

### meta/prd.md Updates Needed

**Section 2.1 (The Context Bank)**:
- Add `telemetry.db` for tracking operations and metrics
- Add `snapshots.db` for state checkpointing
- Add `sessions.db` for session management

**Section 3 (Agent Specifications)**:
- Update Section A (Planner) to include checkpointing before operations
- Update Section B (Implementer) to include telemetry tracking and progress reporting
- Update Section C (Acceptance Agent) to validate checkpoint integrity

**New Section: Telemetry and Monitoring**:
- Describe telemetry system for operation tracking
- Define metrics collected: tokens, time, resources
- Describe resource monitoring and alerts

**New Section: Error Handling and Resilience**:
- Describe error classification and recovery strategies
- Describe retry logic with exponential backoff
- Describe graceful shutdown and state preservation

**New Section: Session Management**:
- Describe session lifecycle and persistence
- Describe session resumption after interruption
- Describe session analytics and reporting

**Section 6 (Implementation Guardrails)**:
- Add checkpoint before refactoring sprints
- Add health checks before critical operations
- Add transaction support for multi-step operations

**New Section 8: V3 Enhancements**:
- Document telemetry infrastructure
- Document structured logging system
- Document state checkpointing and recovery
- Document error handling and resilience
- Document session management
- Document user experience improvements

---

### meta/tech.md Updates Needed

**Section 1.2 (The Context Bank)**:
- Add `telemetry.db`: Stores operation tracking and metrics
- Add `snapshots.db`: Stores system state snapshots
- Add `sessions.db`: Stores session state and configuration

**Section 2 (Module Hierarchy Reference)**:
- Add new modules in `core/`:
  - `core/logging_config.py` - Structured logging configuration
  - `core/telemetry.py` - Telemetry interface
  - `core/error_handling.py` - Error classification and recovery
  - `core/graceful_shutdown.py` - Shutdown handling
  - `core/transactions.py` - Transaction support
  - `core/health_check.py` - Health checks
  - `core/session_manager.py` - Session management
  - `core/ui.py` - User interface components
  - `core/log_analyzer.py` - Log analysis utilities
- Add new modules in `data/`:
  - `data/telemetry_manager.py` - Telemetry tracking
  - `data/checkpoint_manager.py` - State checkpointing

**Section 3 (Functional Modules to Develop)**:
- Update `core/start.py` to include session detection and resume
- Update `data/db_manager.py` to manage new databases
- Add new module descriptions:
  - Module 8: `data/telemetry_manager.py` - Telemetry tracking
  - Module 9: `data/checkpoint_manager.py` - State checkpointing
  - Module 10: `core/logging_config.py` - Logging configuration
  - Module 11: `core/error_handling.py` - Error handling
  - Module 12: `core/session_manager.py` - Session management
  - Module 13: `core/health_check.py` - Health checks

**Section 4 (Operational Flow Summary)**:
- Update flow to include telemetry tracking at each step
- Add checkpoint creation before critical operations
- Add health checks before operations
- Add graceful shutdown handling
- Add session resume on startup

**Section 6 (Performance Characteristics)**:
- Add telemetry overhead metrics
- Add checkpoint performance characteristics
- Add logging overhead metrics
- Add session management performance

**New Section 7: Configuration**:
- Document telemetry configuration options
- Document logging configuration options
- Document checkpoint policy configuration
- Document session management configuration

**New Section 8: Module Dependencies**:
- Update dependency graph to include new V3 modules
- Show telemetry, logging, checkpoint dependencies

---

## Risks and Mitigations

### Risk 1: Telemetry Overhead Impacts Performance
- **Mitigation**: Implement efficient data collection, use batch inserts, optimize queries
- **Fallback**: Provide option to disable detailed telemetry
- **Monitoring**: Track operation times with/without telemetry

### Risk 2: Checkpoint Size Grows Unbounded
- **Mitigation**: Implement incremental checkpoints, compress data, automatic cleanup
- **Fallback**: Manual checkpoint management, limit checkpoint retention
- **Monitoring**: Alert on checkpoint size, track cleanup effectiveness

### Risk 3: Log Files Consume Too Much Disk Space
- **Mitigation**: Implement log rotation, limit retention, compress old logs
- **Fallback**: Adjust log levels to reduce verbosity
- **Monitoring**: Alert on disk usage, track log growth

### Risk 4: Checkpoint Restoration Fails
- **Mitigation**: Validate checkpoints before saving, implement robust restore logic
- **Fallback**: Keep multiple checkpoints, manual recovery tools
- **Monitoring**: Track checkpoint restore success rate, alert on failures

### Risk 5: Session State Corruption
- **Mitigation**: Validate session state, implement checksums, use transactions
- **Fallback**: Archive corrupted sessions, manual recovery from checkpoints
- **Monitoring**: Check session integrity on resume, track corruption events

### Risk 6: Error Recovery Strategies Fail
- **Mitigation**: Test recovery strategies extensively, provide manual recovery options
- **Fallback**: Rollback to checkpoint, ask user for intervention
- **Monitoring**: Track recovery success rates, learn from failures

### Risk 7: Too Many Checkpoints Slow Down System
- **Mitigation**: Implement smart checkpoint policy, limit checkpoint frequency
- **Fallback**: Manual checkpoint creation, disable automatic checkpoints
- **Monitoring**: Track checkpoint creation time, system responsiveness

### Risk 8: Session Resumption Creates Inconsistent State
- **Mitigation**: Validate state before resume, detect external changes, merge intelligently
- **Fallback**: Alert user to conflicts, manual resolution
- **Monitoring**: Track resumption success rate, conflict frequency

---

## Future Enhancements (Beyond V3)

1. **Distributed Telemetry**: Support for multi-machine deployments
2. **Telemetry Dashboards**: Web-based visualization of metrics and operations
3. **ML-Based Error Prediction**: Predict and prevent errors before they occur
4. **Advanced Session Analytics**: Machine learning insights into developer productivity
5. **Collaborative Sessions**: Support for multiple developers working on same project
6. **Cloud Backup**: Sync sessions and checkpoints to cloud storage
7. **Real-Time Monitoring**: WebSockets for live status updates
8. **Automated Testing Integration**: Run tests automatically after checkpoints
9. **Git Integration Enhancements**: Better merge conflict resolution
10. **Performance Profiling**: Detailed performance profiling with telemetry correlation

---

## Summary

V3 transforms L4D from a development tool into a production-ready platform with:

**Key Capabilities**:
- Comprehensive telemetry for insights and debugging
- Structured logging for traceability and analysis
- Robust checkpointing for state recovery
- Graceful error handling and recovery
- Session management for continuity
- Enhanced user experience with progress and clarity

**Benefits**:
- Zero data loss from interruptions
- Fast session resumption (<5 seconds)
- Self-healing from common errors
- Deep visibility into operations
- Better debugging with structured logs
- Improved productivity with session persistence

**Architecture**: Built on V2's AST-based context collection, adding telemetry, logging, checkpointing, error handling, and session management layers for production resilience.
