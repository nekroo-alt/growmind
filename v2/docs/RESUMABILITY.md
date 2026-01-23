# Checkpoint and Recovery System Documentation

## Overview

The L4D V3 Checkpoint and Recovery System provides robust state management capabilities, allowing the system to save and restore system state at critical points. This ensures zero data loss from interruptions and enables fast session resumption.

---

## Table of Contents

- [Architecture](#architecture)
- [Database Schema](#database-schema)
- [Checkpoint Manager API](#checkpoint-manager-api)
- [State Components](#state-components)
- [Automatic Checkpoint Policy](#automatic-checkpoint-policy)
- [Recovery Strategies](#recovery-strategies)
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
│                 Checkpoint Manager API                      │
│  (data/checkpoint_manager.py)                               │
│  - create()                                                 │
│  - restore()                                                │
│  - validate()                                                │
│  - rollback_on_error()                                      │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                 State Capture Layer                         │
│  - Database state capture                                   │
│  - File system state capture                                │
│  - Context and cache capture                                │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                 Checkpoint Storage                          │
│  (checkpoints/)                                              │
│  - chkp_<timestamp>_<hash>/                                │
│    - task.db.backup                                         │
│    - activity.db.backup                                    │
│    - telemetry.db.backup                                   │
│    - snapshots.db.backup                                    │
│    - files/                                                │
│      - src/main.py.backup                                   │
│      - test/test_auth.py.backup                             │
└─────────────────────────────────────────────────────────────┘
```

### Key Features

- **Complete State Capture**: Database, file system, context, and cache
- **Fast Restoration**: Restore from checkpoint in <3 seconds
- **Automatic Checkpoints**: Policy-based automatic checkpoint creation
- **Rollback Support**: Automatic rollback on errors
- **Validation**: State integrity checks before/after restore
- **Incremental Snapshots**: Delta-based storage for efficiency

---

## Database Schema

### Snapshots Table

```sql
CREATE TABLE IF NOT EXISTS snapshots (
    id TEXT PRIMARY KEY,                    -- Checkpoint ID (timestamp_hash)
    timestamp TEXT NOT NULL,                -- ISO 8601 timestamp
    snapshot_type TEXT NOT NULL,            -- operation_start, operation_end, task_complete, task_failed, error
    reason TEXT,                           -- Checkpoint reason
    operation_id TEXT,                      -- Foreign key to telemetry.operations
    task_id INTEGER,                        -- Foreign key to task.db
    parent_id TEXT,                        -- Parent checkpoint for chaining
    metadata TEXT,                         -- JSON string with additional info
    is_critical BOOLEAN DEFAULT 0           -- Critical checkpoints are not auto-deleted
);

CREATE INDEX IF NOT EXISTS idx_snapshots_timestamp ON snapshots(timestamp);
CREATE INDEX IF NOT EXISTS idx_snapshots_type ON snapshots(snapshot_type);
CREATE INDEX IF NOT EXISTS idx_snapshots_operation ON snapshots(operation_id);
CREATE INDEX IF NOT EXISTS idx_snapshots_task ON snapshots(task_id);
```

### Snapshot Files Table

```sql
CREATE TABLE IF NOT EXISTS snapshot_files (
    id TEXT PRIMARY KEY,                    -- UUID
    snapshot_id TEXT NOT NULL,             -- Foreign key to snapshots
    file_path TEXT NOT NULL,               -- Relative file path
    file_hash TEXT NOT NULL,              -- SHA-256 hash of file content
    file_size INTEGER,                     -- File size in bytes
    is_modified BOOLEAN DEFAULT 0,         -- Whether file was modified
    backup_path TEXT,                      -- Path to backup file
    FOREIGN KEY (snapshot_id) REFERENCES snapshots(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_snapshot_files_snapshot ON snapshot_files(snapshot_id);
CREATE INDEX IF NOT EXISTS idx_snapshot_files_path ON snapshot_files(file_path);
```

### Snapshot Databases Table

```sql
CREATE TABLE IF NOT EXISTS snapshot_databases (
    id TEXT PRIMARY KEY,                    -- UUID
    snapshot_id TEXT NOT NULL,             -- Foreign key to snapshots
    database_name TEXT NOT NULL,           -- task.db, activity.db, telemetry.db, snapshots.db
    database_hash TEXT NOT NULL,            -- SHA-256 hash of database
    database_size INTEGER,                 -- Database size in bytes
    backup_path TEXT,                      -- Path to backup file
    FOREIGN KEY (snapshot_id) REFERENCES snapshots(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_snapshot_databases_snapshot ON snapshot_databases(snapshot_id);
CREATE INDEX IF NOT EXISTS idx_snapshot_databases_name ON snapshot_databases(database_name);
```

---

## Checkpoint Manager API

### Initialization

```python
from data.checkpoint_manager import CheckpointManager

# Initialize checkpoint manager
checkpoint = CheckpointManager(
    checkpoint_dir="checkpoints/",
    db_path="snapshots.db",
    max_checkpoints=10,                    # Maximum number of checkpoints to keep
    max_age_hours=24                        # Maximum age of checkpoints in hours
)
```

### Creating Checkpoints

```python
# Create a manual checkpoint
checkpoint_id = checkpoint.create(
    reason="Before implementing task 42",
    snapshot_type="task_complete",
    task_id=42,
    operation_id=op_id,
    metadata={
        "task_title": "Add user authentication",
        "files_modified": ["src/auth.py", "test/test_auth.py"]
    },
    is_critical=False
)

# Create a critical checkpoint (won't be auto-deleted)
checkpoint_id = checkpoint.create(
    reason="Before refactoring sprint",
    snapshot_type="refactor",
    is_critical=True
)
```

### Restoring Checkpoints

```python
# Restore from checkpoint
checkpoint.restore(checkpoint_id)

# Restore with dry-run (preview changes)
checkpoint.restore(checkpoint_id, dry_run=True)

# Restore specific components
checkpoint.restore(checkpoint_id, components=["database"])  # Only restore databases
checkpoint.restore(checkpoint_id, components=["files"])     # Only restore files
```

### Validating Checkpoints

```python
# Validate checkpoint integrity
is_valid = checkpoint.validate(checkpoint_id)
if not is_valid:
    logger.warning(f"Checkpoint {checkpoint_id} is invalid")

# Validate and get details
validation_result = checkpoint.validate(checkpoint_id, detailed=True)
if not validation_result['valid']:
    for error in validation_result['errors']:
        logger.error(f"Validation error: {error}")
```

### Listing Checkpoints

```python
# List all checkpoints
checkpoints = checkpoint.list_checkpoints()

# List by type
checkpoints = checkpoint.list_checkpoints(snapshot_type="task_complete")

# List recent checkpoints
checkpoints = checkpoint.list_checkpoints(limit=10)

# List critical checkpoints
checkpoints = checkpoint.list_checkpoints(is_critical=True)
```

### Deleting Checkpoints

```python
# Delete specific checkpoint
checkpoint.delete(checkpoint_id)

# Delete old checkpoints
checkpoint.delete_old(days=7)  # Delete checkpoints older than 7 days

# Delete non-critical checkpoints
checkpoint.delete_non_critical()

# Delete all checkpoints (use with caution)
checkpoint.delete_all()
```

### Rollback on Error

```python
# Automatic rollback on error
with checkpoint.rollback_on_error():
    # Step 1: Modify database
    db.update_tasks(...)
    
    # Step 2: Write files
    write_file("src/feature.py", content)
    
    # Step 3: Run tests
    run_tests()
    
    # If any step fails, automatic rollback occurs

# Manual rollback
try:
    # ... perform operations ...
    pass
except Exception as e:
    logger.error(f"Operation failed: {e}, rolling back")
    checkpoint.rollback()
```

---

## State Components

### Database State

The checkpoint manager captures the state of all databases:

**Databases Captured**:
- `task.db` - Task backlog and status
- `activity.db` - Activity log
- `telemetry.db` - Telemetry data
- `snapshots.db` - Checkpoint metadata

**Capture Method**:
```python
# Database backup uses SQLite backup API for efficient snapshots
def capture_database(db_path: str, backup_path: str) -> None:
    conn = sqlite3.connect(db_path)
    backup = sqlite3.connect(backup_path)
    conn.backup(backup)
    backup.close()
    conn.close()
```

**Restore Method**:
```python
# Restore database from backup
def restore_database(backup_path: str, db_path: str) -> None:
    shutil.copy(backup_path, db_path)
```

### File System State

The checkpoint manager captures file system state including:

**Files Captured**:
- Modified files (detected via git status)
- New files (untracked files)
- Cache files (`.l4_cache/`)
- Configuration files (`.l4_config`)

**Capture Method**:
```python
# Use git to track changes
def capture_file_system(checkpoint_dir: str) -> Dict:
    files = {}
    
    # Get modified files
    modified = git.get_modified_files()
    for file_path in modified:
        backup_path = os.path.join(checkpoint_dir, "files", file_path)
        os.makedirs(os.path.dirname(backup_path), exist_ok=True)
        shutil.copy(file_path, backup_path)
        files[file_path] = {
            'hash': hash_file(file_path),
            'size': os.path.getsize(file_path),
            'backup_path': backup_path,
            'is_modified': True
        }
    
    return files
```

**Restore Method**:
```python
# Restore files from backup
def restore_files(checkpoint_dir: str, files: List[str]) -> None:
    for file_path in files:
        backup_path = os.path.join(checkpoint_dir, "files", file_path)
        if os.path.exists(backup_path):
            shutil.copy(backup_path, file_path)
```

### Context and Cache State

The checkpoint manager captures context engine and cache state:

**State Captured**:
- Context engine memoization cache
- AST analysis results (from `.l4_cache/`)
- LLM conversation history (if applicable)
- Session context

**Capture Method**:
```python
# Capture cache state
def capture_cache_state(cache_dir: str) -> Dict:
    cache_state = {}
    
    for cache_file in os.listdir(cache_dir):
        cache_path = os.path.join(cache_dir, cache_file)
        if os.path.isfile(cache_path):
            cache_state[cache_file] = {
                'hash': hash_file(cache_path),
                'size': os.path.getsize(cache_path),
                'content': read_cache_file(cache_path)
            }
    
    return cache_state
```

**Restore Method**:
```python
# Restore cache state
def restore_cache_state(cache_dir: str, cache_state: Dict) -> None:
    for cache_file, state in cache_state.items():
        cache_path = os.path.join(cache_dir, cache_file)
        write_cache_file(cache_path, state['content'])
```

---

## Automatic Checkpoint Policy

### Policy Configuration

```python
from data.checkpoint_manager import CheckpointPolicy

policy = CheckpointPolicy(
    before_task=True,                    # Checkpoint before each task
    after_task=True,                     # Checkpoint after successful task
    before_refactor=True,                 # Checkpoint before refactoring
    after_refactor=True,                  # Checkpoint after refactoring
    on_error=True,                        # Checkpoint on error/interruption
    max_age_hours=24,                     # Maximum checkpoint age
    max_count=10,                         # Maximum number of checkpoints
    keep_critical=True                     # Keep critical checkpoints
)

checkpoint = CheckpointManager(policy=policy)
```

### Automatic Checkpoint Triggers

**Before Task Implementation**:
```python
# In logic/dispatcher.py
def dispatch(task_id: int):
    # Create checkpoint before task
    checkpoint_id = checkpoint.create(
        reason=f"Before implementing task {task_id}",
        snapshot_type="operation_start",
        task_id=task_id
    )
    
    # Implement task
    result = implementor.execute_tdd_cycle(task_id)
    
    return result
```

**After Task Completion**:
```python
# In logic/implementor.py
def execute_tdd_cycle(task_id: int):
    # ... TDD cycle ...
    
    # Create checkpoint after successful completion
    checkpoint.create(
        reason=f"After completing task {task_id}",
        snapshot_type="task_complete",
        task_id=task_id,
        is_critical=True
    )
    
    return result
```

**Before Refactoring Sprint**:
```python
# In logic/implementor.py
def run_refactor_sprint():
    # Create checkpoint before refactoring
    checkpoint.create(
        reason="Before refactoring sprint",
        snapshot_type="refactor",
        is_critical=True
    )
    
    # ... refactoring ...
    
    return result
```

**On Error**:
```python
# In core/start.py
try:
    # ... main loop ...
    pass
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    
    # Create checkpoint on error
    checkpoint.create(
        reason=f"Error: {str(e)}",
        snapshot_type="error",
        is_critical=True
    )
    
    raise
```

### Checkpoint Garbage Collection

```python
# Automatic cleanup based on policy
checkpoint.cleanup()

# Manual cleanup
checkpoint.delete_old(days=7)  # Delete checkpoints older than 7 days
checkpoint.delete_excess()       # Delete oldest non-critical checkpoints
```

---

## Recovery Strategies

### Error Recovery with Checkpoints

```python
from core.error_handling import ErrorType, RecoveryStrategy

# Define recovery strategies
recovery_strategies = {
    ErrorType.LLM_RATE_LIMIT: RecoveryStrategy(
        action="retry_with_backoff",
        max_attempts=3,
        checkpoint_on_failure=False
    ),
    ErrorType.DB_CORRUPTED: RecoveryStrategy(
        action="restore_from_checkpoint",
        checkpoint_type="most_recent"
    ),
    ErrorType.FILE_SYSTEM_ERROR: RecoveryStrategy(
        action="restore_from_checkpoint",
        checkpoint_type="before_last_operation"
    )
}

# Handle error with recovery
def handle_error(error: Exception, operation_id: str):
    error_type = classify_error(error)
    strategy = recovery_strategies.get(error_type)
    
    if strategy.action == "restore_from_checkpoint":
        checkpoint_id = find_checkpoint(
            operation_id=operation_id,
            checkpoint_type=strategy.checkpoint_type
        )
        checkpoint.restore(checkpoint_id)
        logger.info(f"Restored from checkpoint {checkpoint_id}")
```

### Session Recovery

```python
from core.session_manager import SessionManager

session_manager = SessionManager()

# Detect interrupted sessions
interrupted = session_manager.detect_interrupted_sessions()
if interrupted:
    print("Interrupted sessions detected:")
    for session in interrupted:
        print(f"  - {session['id']}: {session['last_operation']} at {session['end_time']}")
    
    # Ask user if they want to resume
    response = input("Resume last session? [y/n]: ")
    if response.lower() == 'y':
        # Restore session state from checkpoint
        checkpoint_id = interrupted[0]['checkpoint_id']
        checkpoint.restore(checkpoint_id)
        
        # Resume session
        session = session_manager.resume_session(interrupted[0]['id'])
        logger.info(f"Resumed session {session.id}")
```

### Manual Recovery

```python
# List available checkpoints
checkpoints = checkpoint.list_checkpoints()
print("Available checkpoints:")
for chkp in checkpoints:
    print(f"  - {chkp['id']}: {chkp['reason']} at {chkp['timestamp']}")

# Select checkpoint to restore
checkpoint_id = input("Enter checkpoint ID to restore: ")
checkpoint.restore(checkpoint_id)

# Or use CLI
# l4-dev checkpoints restore --id <checkpoint-id>
```

### Dry-Run Restore

```python
# Preview restore changes
changes = checkpoint.restore(checkpoint_id, dry_run=True)

print("Restore preview:")
for change in changes:
    print(f"  - {change['type']}: {change['path']}")
    if change['type'] == 'modify':
        print(f"    Old: {change['old_hash']}")
        print(f"    New: {change['new_hash']}")

# Confirm restore
response = input("Proceed with restore? [y/n]: ")
if response.lower() == 'y':
    checkpoint.restore(checkpoint_id)
```

---

## Best Practices

### 1. Create Checkpoints Before Critical Operations

```python
# Good
checkpoint.create(reason="Before database migration", snapshot_type="operation_start", is_critical=True)
migrate_database()

# Bad
migrate_database()  # No checkpoint, can't rollback if fails
```

### 2. Use Automatic Checkpoint Policy

```python
# Good
policy = CheckpointPolicy(
    before_task=True,
    after_task=True,
    before_refactor=True,
    on_error=True
)
checkpoint = CheckpointManager(policy=policy)

# Bad
checkpoint = CheckpointManager()  # No automatic checkpoints
```

### 3. Validate Checkpoints After Creation

```python
# Good
checkpoint_id = checkpoint.create(reason="Before task 42")
if not checkpoint.validate(checkpoint_id):
    logger.error("Checkpoint validation failed")
    raise RuntimeError("Invalid checkpoint")

# Bad
checkpoint.create(reason="Before task 42")  # No validation
```

### 4. Use Rollback on Error Pattern

```python
# Good
with checkpoint.rollback_on_error():
    modify_database()
    write_files()
    run_tests()

# Bad
modify_database()
write_files()
run_tests()  # No rollback if something fails
```

### 5. Mark Critical Checkpoints

```python
# Good
checkpoint.create(
    reason="Before major refactoring",
    is_critical=True  # Won't be auto-deleted
)

# Bad
checkpoint.create(
    reason="Before major refactoring",
    is_critical=False  # May be auto-deleted
)
```

### 6. Regularly Clean Up Old Checkpoints

```python
# Good
checkpoint.cleanup()  # Automatic cleanup based on policy

# Manual cleanup
checkpoint.delete_old(days=7)
checkpoint.delete_excess()

# Bad
# Never cleanup, checkpoint directory grows unbounded
```

### 7. Use Descriptive Checkpoint Reasons

```python
# Good
checkpoint.create(
    reason="Before implementing task 42: Add JWT authentication",
    snapshot_type="task_complete"
)

# Bad
checkpoint.create(
    reason="Checkpoint",
    snapshot_type="task_complete"
)
```

### 8. Monitor Checkpoint Health

```python
# Good
for checkpoint_id in checkpoint.list_checkpoints():
    if not checkpoint.validate(checkpoint_id):
        logger.warning(f"Invalid checkpoint: {checkpoint_id}")
        checkpoint.delete(checkpoint_id)

# Bad
# Never validate checkpoints
```

### 9. Use Checkpoint Chaining

```python
# Good
# Create parent checkpoint
parent_id = checkpoint.create(
    reason="Before task execution",
    snapshot_type="operation_start"
)

# Create child checkpoint (linked to parent)
child_id = checkpoint.create(
    reason="After task 42",
    snapshot_type="task_complete",
    parent_id=parent_id
)

# Restore entire chain
checkpoint.restore(parent_id)  # Restores parent and all children

# Bad
# No checkpoint chaining, harder to track relationships
```

### 10. Document Checkpoint Usage

```python
# Good
"""
Checkpoints are created:
- Before each task implementation
- After successful task completion
- Before refactoring sprints
- On errors

Critical checkpoints (not auto-deleted):
- Before major refactoring
- Before database migrations
- After completing major features
"""

# Bad
# No documentation, unclear when checkpoints are created
```

---

## Troubleshooting

### Checkpoint Creation Failed

**Problem**: Checkpoint creation fails with file system error.

**Solution**:
1. Check disk space: Ensure sufficient space for checkpoint
2. Check file permissions: Ensure write access to checkpoint directory
3. Check database locks: Ensure databases are not locked by other processes
4. Check git status: Ensure git repository is in a clean state

### Checkpoint Restore Failed

**Problem**: Checkpoint restore fails with validation error.

**Solution**:
1. Validate checkpoint: Use `checkpoint.validate(checkpoint_id, detailed=True)`
2. Check backup files: Ensure backup files exist and are not corrupted
3. Check file permissions: Ensure write access to target files
4. Use dry-run: Preview changes with `checkpoint.restore(checkpoint_id, dry_run=True)`

### Checkpoint Directory Too Large

**Problem**: Checkpoint directory is consuming too much disk space.

**Solution**:
1. Cleanup old checkpoints: `checkpoint.delete_old(days=7)`
2. Delete excess checkpoints: `checkpoint.delete_excess()`
3. Reduce max_count: Set lower maximum checkpoint count in policy
4. Compress checkpoints: Use compression for checkpoint storage

### Missing Checkpoint

**Problem**: Expected checkpoint is not found.

**Solution**:
1. Check checkpoint list: Use `checkpoint.list_checkpoints()`
2. Check checkpoint age: Verify checkpoint is not older than max_age_hours
3. Check critical flag: Verify checkpoint is not marked as non-critical
4. Check deletion logs: Review checkpoint deletion history

### Restore Conflict

**Problem**: Restore fails due to file conflicts.

**Solution**:
1. Use dry-run: Preview conflicts before restore
2. Check git status: Resolve any git conflicts first
3. Use selective restore: Restore only databases or files
4. Manual merge: Manually resolve conflicts and create new checkpoint

---

## CLI Commands

### List Checkpoints

```bash
# List all checkpoints
l4-dev checkpoints list

# List by type
l4-dev checkpoints list --type task_complete

# List recent checkpoints
l4-dev checkpoints list --limit 10

# List critical checkpoints
l4-dev checkpoints list --critical
```

### Restore Checkpoint

```bash
# Restore from checkpoint
l4-dev checkpoints restore --id <checkpoint-id>

# Restore with dry-run
l4-dev checkpoints restore --id <checkpoint-id> --dry-run

# Restore specific components
l4-dev checkpoints restore --id <checkpoint-id> --components database
```

### Delete Checkpoint

```bash
# Delete specific checkpoint
l4-dev checkpoints delete --id <checkpoint-id>

# Delete old checkpoints
l4-dev checkpoints delete --old-days 7

# Delete non-critical checkpoints
l4-dev checkpoints delete --non-critical
```

### Create Checkpoint

```bash
# Create manual checkpoint
l4-dev checkpoints create --reason "Before major change" --critical

# Create checkpoint with metadata
l4-dev checkpoints create --reason "Before task 42" --task-id 42 --type task_complete
```

---

## Performance Considerations

### Checkpoint Creation Time

| State Component | Typical Size | Creation Time |
|----------------|--------------|---------------|
| Database (task.db) | 1-5 MB | <0.5s |
| Database (activity.db) | 5-20 MB | <1s |
| Database (telemetry.db) | 10-50 MB | <2s |
| Database (snapshots.db) | 1-5 MB | <0.5s |
| Files (modified) | 1-10 MB | <0.5s |
| Cache | 10-100 MB | <1s |
| **Total** | **50-200 MB** | **<5s** |

### Checkpoint Restore Time

| State Component | Typical Size | Restore Time |
|----------------|--------------|---------------|
| Database (task.db) | 1-5 MB | <0.3s |
| Database (activity.db) | 5-20 MB | <0.8s |
| Database (telemetry.db) | 10-50 MB | <1.5s |
| Database (snapshots.db) | 1-5 MB | <0.3s |
| Files (modified) | 1-10 MB | <0.5s |
| Cache | 10-100 MB | <0.8s |
| **Total** | **50-200 MB** | **<4s** |

### Disk Space Usage

| Checkpoints per Day | DB Size after 30 Days | Disk Space Used |
|---------------------|----------------------|-----------------|
| 5 | ~150 | ~4.5 GB |
| 10 | ~300 | ~9 GB |
| 20 | ~600 | ~18 GB |

Use automatic cleanup to manage disk space.

---

## Conclusion

The L4D V3 Checkpoint and Recovery System provides robust state management with fast restoration and automatic cleanup. By following best practices outlined in this document, you can ensure zero data loss from interruptions and enable fast session resumption.

For more information, see:
- [TELEMETRY.md](TELEMETRY.md) - Telemetry system documentation
- [LOGGING.md](LOGGING.md) - Structured logging
- [SESSION_MANAGEMENT.md](SESSION_MANAGEMENT.md) - Session persistence
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Common issues and solutions