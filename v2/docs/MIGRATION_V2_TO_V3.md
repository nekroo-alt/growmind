# Migration Guide: V2 to V3

## Overview

This guide provides step-by-step instructions for migrating from L4D V2 to V3. V3 adds comprehensive telemetry, structured logging, checkpoint/recovery, and session management capabilities.

---

## Table of Contents

- [What's New in V3](#whats-new-in-v3)
- [Prerequisites](#prerequisites)
- [Migration Steps](#migration-steps)
- [Configuration Changes](#configuration-changes)
- [Code Changes](#code-changes)
- [Testing Your Migration](#testing-your-migration)
- [Rollback Plan](#rollback-plan)
- [Troubleshooting](#troubleshooting)

---

## What's New in V3

### New Features

| Feature | Description | Benefits |
|---------|-------------|-----------|
| **Telemetry System** | Comprehensive operation tracking and metrics | Deep visibility into operations, debugging efficiency |
| **Structured Logging** | Consistent, searchable logs with JSON format | Machine-parseable logs, better analytics |
| **Checkpoint/Recovery** | Save and restore system state | Zero data loss, fast session resumption |
| **Session Management** | Track and resume sessions across runs | Productivity tracking, seamless continuity |
| **Error Handling** | Automatic retry with exponential backoff | Self-healing from transient errors |
| **Graceful Shutdown** | Save state on interruption | Clean shutdown, data preservation |
| **Health Checks** | System health monitoring | Proactive issue detection |
| **Progress Indicators** | Real-time progress feedback | Better user experience |

### New Databases

| Database | Purpose |
|----------|---------|
| `telemetry.db` | Stores operation tracking and metrics |
| `sessions.db` | Stores session state and configuration |
| `snapshots.db` | Stores checkpoint metadata |

### New Modules

| Module | Purpose |
|--------|---------|
| `data/telemetry_manager.py` | Telemetry tracking |
| `data/checkpoint_manager.py` | State checkpointing |
| `core/logging_config.py` | Structured logging |
| `core/error_handling.py` | Error classification and recovery |
| `core/graceful_shutdown.py` | Shutdown handling |
| `core/transactions.py` | Transaction support |
| `core/health_check.py` | Health checks |
| `core/session_manager.py` | Session management |
| `core/ui.py` | User interface components |
| `core/log_analyzer.py` | Log analysis utilities |

---

## Prerequisites

### System Requirements

- Python 3.8 or higher
- SQLite 3.25 or higher
- Git 2.20 or higher
- Sufficient disk space for checkpoints and logs (recommended: 10 GB free)

### Backup Data

Before migrating, backup your existing data:

```bash
# Backup databases
cp task.db task.db.v2_backup
cp activity.db activity.db.v2_backup

# Backup cache
cp -r .l4_cache .l4_cache.v2_backup

# Backup configuration
cp .l4_config .l4_config.v2_backup  # if exists
```

### Check Current V2 Version

```bash
# Check V2 version
cd v2
python -c "import sys; print(sys.version)"

# Verify V2 modules exist
ls -la data/ logic/ core/
```

---

## Migration Steps

### Step 1: Update Dependencies

Install V3 dependencies:

```bash
# Update requirements.txt
cat > requirements.txt << EOF
# Core dependencies
python-dotenv==1.0.0
pydantic==2.5.0

# V2 dependencies
ast>=0.9.0
networkx>=3.2.0

# V3 new dependencies
psutil==5.9.0          # Resource monitoring
rich==13.7.0           # Enhanced UI
structlog==24.1.0       # Structured logging

# Testing
pytest==7.4.0
pytest-cov==4.1.0
pytest-asyncio==0.21.0
EOF

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Initialize New Databases

Initialize V3 databases:

```bash
# Run initialization script
python -c "
from data.db_manager import DatabaseManager
from data.telemetry_manager import TelemetryManager
from data.checkpoint_manager import CheckpointManager
from core.session_manager import SessionManager

# Initialize telemetry
telemetry = TelemetryManager()

# Initialize checkpoint manager
checkpoint = CheckpointManager()

# Initialize session manager
session_manager = SessionManager()

print('V3 databases initialized successfully')
"
```

### Step 3: Migrate Configuration

Update your configuration file (`.l4_config` or `config.yaml`):

**V2 Configuration**:
```yaml
# V2 config
cache:
  enabled: true
  dir: .l4_cache

context:
  max_depth: 3
  token_budget: 4000
```

**V3 Configuration**:
```yaml
# V3 config (enhanced)
cache:
  enabled: true
  dir: .l4_cache
  max_size_mb: 100

context:
  max_depth: 3
  token_budget: 4000
  include_type_hints: true
  add_context_comments: true

# V3 new sections
telemetry:
  enabled: true
  db_path: telemetry.db

logging:
  level: INFO
  file: l4.log
  error_file: l4_error.log
  max_file_size_mb: 10
  backup_count: 5
  json_format: false

checkpoint:
  enabled: true
  dir: checkpoints/
  max_checkpoints: 10
  max_age_hours: 24

session:
  auto_resume: true
  max_sessions: 10

llm:
  provider: openai
  model: gpt-4
  temperature: 0.7
  retry:
    max_attempts: 3
    base_delay: 1.0
    max_delay: 60.0
```

### Step 4: Update Environment Variables

Update your environment variables:

```bash
# V2 variables (keep)
export L4_CACHE_DIR=.l4_cache
export L4_CACHE_ENABLED=true
export L4_MAX_DEPTH=3
export L4_TOKEN_BUDGET=4000

# V3 new variables
export L4_TELEMETRY_ENABLED=true
export L4_TELEMETRY_DB=telemetry.db

export L4_LOG_LEVEL=INFO
export L4_LOG_FILE=l4.log
export L4_ERROR_LOG_FILE=l4_error.log

export L4_CHECKPOINT_DIR=checkpoints/
export L4_CHECKPOINT_ENABLED=true

export L4_SESSION_AUTO_RESUME=true
export L4_SESSION_MAX_SESSIONS=10

export L4_LLM_PROVIDER=openai
export L4_LLM_MODEL=gpt-4
export L4_LLM_TEMPERATURE=0.7
```

### Step 5: Update Code Imports

Update your code to use V3 modules:

**V2 Imports**:
```python
from data.db_manager import DatabaseManager
from data.cache_manager import CacheManager
from logic.context_engine import ContextEngine
```

**V3 Imports**:
```python
from data.db_manager import DatabaseManager
from data.cache_manager import CacheManager
from data.telemetry_manager import TelemetryManager
from data.checkpoint_manager import CheckpointManager
from logic.context_engine import ContextEngine
from core.session_manager import SessionManager
from core.logging_config import setup_logging
```

### Step 6: Initialize V3 Systems

Update your startup code:

**V2 Startup**:
```python
from data.db_manager import DatabaseManager
from data.cache_manager import CacheManager
from logic.context_engine import ContextEngine

# Initialize systems
db_manager = DatabaseManager()
cache_manager = CacheManager()
context_engine = ContextEngine(db_manager, cache_manager)

# Start main loop
main_loop()
```

**V3 Startup**:
```python
from data.db_manager import DatabaseManager
from data.cache_manager import CacheManager
from logic.context_engine import ContextEngine
from data.telemetry_manager import TelemetryManager
from data.checkpoint_manager import CheckpointManager
from core.session_manager import SessionManager
from core.logging_config import setup_logging
from core.graceful_shutdown import GracefulShutdown

# Initialize logging
setup_logging()

# Initialize systems
db_manager = DatabaseManager()
cache_manager = CacheManager()
context_engine = ContextEngine(db_manager, cache_manager)
telemetry = TelemetryManager()
checkpoint = CheckpointManager()
session_manager = SessionManager()

# Initialize graceful shutdown
shutdown_handler = GracefulShutdown(
    telemetry=telemetry,
    checkpoint=checkpoint,
    session_manager=session_manager
)

# Start main loop
try:
    main_loop()
except KeyboardInterrupt:
    shutdown_handler.handle_interrupt()
```

### Step 7: Add Telemetry Tracking

Add telemetry to your operations:

**V2 Code**:
```python
def implement_task(task_id: int):
    task = db_manager.get_task(task_id)
    
    # Implementation logic
    result = implement(task)
    
    return result
```

**V3 Code**:
```python
from data.telemetry_manager import telemetry

def implement_task(task_id: int):
    with telemetry.track_operation("implementation", f"Implement task {task_id}") as op:
        task = db_manager.get_task(task_id)
        op.record_event("fetch", "info", "Fetched task from database")
        
        # Implementation logic
        result = implement(task)
        
        op.record_metric("tokens_used", result.tokens_used)
        op.record_event("complete", "info", "Task implementation completed")
    
    return result
```

### Step 8: Add Logging

Add structured logging to your operations:

**V2 Code**:
```python
def implement_task(task_id: int):
    print(f"Implementing task {task_id}")
    # ...
```

**V3 Code**:
```python
import logging
from core.logging_config import format_log_message

logger = logging.getLogger(__name__)

def implement_task(task_id: int):
    logger.info(format_log_message(
        "Implementing task",
        task_id=task_id
    ))
    # ...
```

### Step 9: Add Checkpoints

Add checkpoints to critical operations:

**V2 Code**:
```python
def implement_task(task_id: int):
    # Implementation logic
    result = implement(task)
    return result
```

**V3 Code**:
```python
from data.checkpoint_manager import checkpoint

def implement_task(task_id: int):
    # Create checkpoint before task
    checkpoint_id = checkpoint.create(
        reason=f"Before implementing task {task_id}",
        snapshot_type="operation_start",
        task_id=task_id
    )
    
    try:
        # Implementation logic
        result = implement(task)
        
        # Create checkpoint after successful task
        checkpoint.create(
            reason=f"After completing task {task_id}",
            snapshot_type="task_complete",
            task_id=task_id,
            is_critical=True
        )
        
        return result
    except Exception as e:
        logger.error(f"Task implementation failed: {e}")
        # Rollback to checkpoint
        checkpoint.restore(checkpoint_id)
        raise
```

### Step 10: Add Session Management

Add session tracking:

**V2 Code**:
```python
def main():
    # Main loop
    while True:
        task = get_next_task()
        implement_task(task.id)
```

**V3 Code**:
```python
from core.session_manager import session_manager

def main():
    # Detect interrupted sessions
    interrupted = session_manager.detect_interrupted_sessions()
    if interrupted:
        print("Interrupted sessions detected:")
        for s in interrupted:
            print(f"  - {s['id']}: {s['status']}")
        
        response = input("Resume last session? [y/n]: ")
        if response.lower() == 'y':
            session = session_manager.resume_last_session()
    
    # Start new session if no resume
    if not interrupted or response.lower() != 'y':
        session = session_manager.start_session(
            user="developer",
            environment="dev"
        )
    
    # Main loop
    try:
        while True:
            task = get_next_task()
            implement_task(task.id)
    finally:
        session_manager.complete_session(session.id)
```

---

## Configuration Changes

### Logging Configuration

V3 introduces structured logging with multiple handlers:

```python
from core.logging_config import setup_logging

setup_logging(
    log_level="INFO",
    log_file="l4.log",
    error_log_file="l4_error.log",
    max_file_size_mb=10,
    backup_count=5,
    json_format=False,
    enable_console=True
)
```

### Checkpoint Policy Configuration

V3 introduces automatic checkpoint policy:

```python
from data.checkpoint_manager import CheckpointPolicy, CheckpointManager

policy = CheckpointPolicy(
    before_task=True,
    after_task=True,
    before_refactor=True,
    after_refactor=True,
    on_error=True,
    max_age_hours=24,
    max_count=10,
    keep_critical=True
)

checkpoint = CheckpointManager(policy=policy)
```

### Error Handling Configuration

V3 introduces retry configuration:

```python
from core.error_handling import RetryConfig

retry_config = RetryConfig(
    max_attempts=3,
    base_delay=1.0,
    max_delay=60.0,
    exponential_base=2.0,
    jitter=True
)
```

---

## Code Changes

### Minimal Changes (Required)

1. **Initialize logging**: Call `setup_logging()` at startup
2. **Initialize telemetry**: Create `TelemetryManager` instance
3. **Initialize checkpoint**: Create `CheckpointManager` instance
4. **Initialize session**: Create `SessionManager` instance
5. **Add graceful shutdown**: Add signal handlers for SIGINT/SIGTERM

### Optional Enhancements

1. **Add telemetry tracking**: Use `telemetry.track_operation()` for operations
2. **Add structured logging**: Use `format_log_message()` for log messages
3. **Add checkpoints**: Use `checkpoint.create()` for critical operations
4. **Add session tracking**: Use `session_manager` for session management
5. **Add error handling**: Use `@retry` decorator for retry logic

---

## Testing Your Migration

### Run V3 Tests

```bash
# Run all V3 tests
pytest v2/tests/

# Run specific test suites
pytest v2/tests/unit/test_telemetry.py
pytest v2/tests/unit/test_logging.py
pytest v2/tests/unit/test_checkpoint.py
pytest v2/tests/integration/test_session.py

# Run with coverage
pytest --cov=v2 --cov-report=html
```

### Manual Testing

1. **Test telemetry tracking**:
   ```bash
   # Start a session
   l4-dev start
   
   # Implement a task
   # Check telemetry.db for operation records
   
   # Query telemetry
   l4-dev telemetry list
   ```

2. **Test checkpoint creation**:
   ```bash
   # List checkpoints
   l4-dev checkpoints list
   
   # Restore checkpoint
   l4-dev checkpoints restore --id <checkpoint-id>
   ```

3. **Test session management**:
   ```bash
   # List sessions
   l4-dev sessions list
   
   # Resume session
   l4-dev resume
   ```

4. **Test logging**:
   ```bash
   # Check log files
   cat l4.log
   cat l4_error.log
   
   # Search logs
   l4-dev logs search --keyword error
   ```

### Performance Testing

Verify V3 performance meets expectations:

```bash
# Run performance tests
pytest v2/tests/integration/test_e2e.py::test_performance

# Check telemetry overhead
# Compare operation times with/without telemetry
```

---

## Rollback Plan

If you need to rollback to V2:

### Step 1: Stop V3 System

```bash
# Stop any running processes
pkill -f "l4-dev"

# Backup V3 data
cp task.db task.db.v3_backup
cp activity.db activity.db.v3_backup
cp telemetry.db telemetry.db.v3_backup
cp sessions.db sessions.db.v3_backup
cp snapshots.db snapshots.db.v3_backup
```

### Step 2: Restore V2 Data

```bash
# Restore V2 databases
cp task.db.v2_backup task.db
cp activity.db.v2_backup activity.db

# Restore V2 cache
rm -rf .l4_cache
cp -r .l4_cache.v2_backup .l4_cache

# Restore V2 configuration
cp .l4_config.v2_backup .l4_config  # if exists
```

### Step 3: Revert Code Changes

```bash
# Checkout V2 code
git checkout <v2-commit-hash>

# Reinstall V2 dependencies
pip install -r requirements.v2.txt
```

### Step 4: Verify V2 Works

```bash
# Run V2 tests
pytest v2/tests/

# Run V2 application
python v2/core/start.py
```

---

## Troubleshooting

### Database Migration Errors

**Problem**: V3 database initialization fails.

**Solution**:
1. Check SQLite version: `sqlite3 --version` (must be >= 3.25)
2. Check file permissions: Ensure write access to database files
3. Check for existing V3 databases: Delete and reinitialize
   ```bash
   rm -f telemetry.db sessions.db snapshots.db
   python -c "from data.telemetry_manager import TelemetryManager; TelemetryManager()"
   ```

### Telemetry Not Recording

**Problem**: Telemetry data is not being recorded.

**Solution**:
1. Check telemetry is enabled: `export L4_TELEMETRY_ENABLED=true`
2. Check database is writable: Ensure write access to `telemetry.db`
3. Check telemetry manager is initialized: Verify `TelemetryManager()` is called
4. Check operation tracking: Verify `telemetry.track_operation()` is used

### Checkpoint Creation Fails

**Problem**: Checkpoint creation fails with file system error.

**Solution**:
1. Check disk space: Ensure sufficient space for checkpoints
2. Check checkpoint directory: Ensure `checkpoints/` exists and is writable
3. Check git status: Ensure git repository is in a clean state
4. Check database locks: Ensure databases are not locked by other processes

### Session Resumption Fails

**Problem**: Session resumption fails with error.

**Solution**:
1. Check checkpoint exists: Verify checkpoint_id is valid
2. Validate checkpoint: Use `checkpoint.validate(checkpoint_id)`
3. Check file permissions: Ensure write access to session files
4. Check database integrity: Verify `sessions.db` is not corrupted

### Logging Not Working

**Problem**: Logs are not being written.

**Solution**:
1. Check logging is initialized: Verify `setup_logging()` is called
2. Check log level: Ensure level is set appropriately
3. Check file permissions: Ensure write access to log files
4. Check log files: Verify `l4.log` and `l4_error.log` are writable

### Performance Degradation

**Problem**: V3 is slower than V2.

**Solution**:
1. Disable telemetry: Set `L4_TELEMETRY_ENABLED=false`
2. Reduce log level: Use `WARNING` or `ERROR` instead of `INFO`
3. Reduce checkpoint frequency: Adjust `max_checkpoints` in policy
4. Disable resource monitoring: Set `resource_monitoring=false` in telemetry config

### Migration Test Failures

**Problem**: V3 tests are failing.

**Solution**:
1. Run tests with verbose output: `pytest -v`
2. Check for missing dependencies: `pip install -r requirements.txt`
3. Check for database issues: Reinitialize databases
4. Check for code conflicts: Verify all code changes are applied

---

## Post-Migration Checklist

- [ ] Backup V2 data completed
- [ ] V3 dependencies installed
- [ ] V3 databases initialized
- [ ] Configuration updated
- [ ] Code imports updated
- [ ] Telemetry tracking added
- [ ] Structured logging added
- [ ] Checkpoints added to critical operations
- [ ] Session management added
- [ ] V3 tests passing
- [ ] Manual testing completed
- [ ] Performance verified
- [ ] Documentation reviewed
- [ ] Team trained on V3 features

---

## Additional Resources

- [TELEMETRY.md](TELEMETRY.md) - Telemetry system documentation
- [LOGGING.md](LOGGING.md) - Structured logging documentation
- [RESUMABILITY.md](RESUMABILITY.md) - Checkpoint and recovery documentation
- [SESSION_MANAGEMENT.md](SESSION_MANAGEMENT.md) - Session management documentation
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Common issues and solutions
- [API_REFERENCE.md](API_REFERENCE.md) - Complete API documentation

---

## Getting Help

If you encounter issues during migration:

1. Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common issues
2. Review test outputs for specific error messages
3. Check logs for detailed error information:
   ```bash
   cat l4.log
   cat l4_error.log
   ```
4. Enable debug logging for more information:
   ```bash
   export L4_LOG_LEVEL=DEBUG
   ```
5. Contact support with:
   - Migration step where issue occurred
   - Error messages and stack traces
   - Log files
   - System information (OS, Python version, etc.)

---

## Conclusion

Migrating to V3 provides comprehensive telemetry, logging, checkpoint/recovery, and session management capabilities. Follow this guide step-by-step to ensure a smooth migration. Test thoroughly before deploying to production.

For questions or issues, refer to the additional resources or contact support.