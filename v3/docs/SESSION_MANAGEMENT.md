# Session Management Documentation

## Overview

The L4D V3 Session Management System provides comprehensive session tracking, persistence, and recovery capabilities. It enables seamless continuation of work across multiple runs and tracks developer productivity over time.

---

## Table of Contents

- [Architecture](#architecture)
- [Database Schema](#database-schema)
- [Session Manager API](#session-manager-api)
- [Session Lifecycle](#session-lifecycle)
- [Session Persistence](#session-persistence)
- [Session Analytics](#session-analytics)
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
│                 Session Manager API                         │
│  (core/session_manager.py)                                  │
│  - start_session()                                          │
│  - resume_session()                                         │
│  - pause_session()                                          │
│  - complete_session()                                       │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                 Session State                                │
│  - Task progress                                           │
│  - Active operations                                      │
│  - Checkpoint references                                  │
│  - Configuration                                          │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                 Session Storage                             │
│  (sessions.db)                                              │
│  - sessions table                                           │
│  - session_tasks table                                       │
│  - session_config table                                      │
└─────────────────────────────────────────────────────────────┘
```

### Key Features

- **Session Persistence**: Save and restore session state across runs
- **Automatic Detection**: Detect interrupted sessions on startup
- **Session Resumption**: Resume from any checkpoint
- **Productivity Tracking**: Track tasks completed, time spent, errors
- **Configuration Management**: Persist user preferences
- **Analytics**: Generate session reports and insights

---

## Database Schema

### Sessions Table

```sql
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,                    -- Session UUID
    start_time TEXT NOT NULL,               -- ISO 8601 timestamp
    end_time TEXT,                          -- ISO 8601 timestamp (nullable)
    status TEXT NOT NULL,                   -- active, paused, completed, interrupted
    user TEXT,                              -- User identifier
    host TEXT,                              -- Hostname
    environment TEXT,                       -- Environment name (dev, prod)
    checkpoint_id TEXT,                     -- Last checkpoint ID
    total_duration_seconds REAL DEFAULT 0,    -- Total duration
    tasks_completed INTEGER DEFAULT 0,       -- Tasks completed in session
    errors_count INTEGER DEFAULT 0,          -- Errors encountered
    metadata TEXT                           -- JSON string with additional info
);

CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status);
CREATE INDEX IF NOT EXISTS idx_sessions_start_time ON sessions(start_time);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user);
```

### Session Tasks Table

```sql
CREATE TABLE IF NOT EXISTS session_tasks (
    id TEXT PRIMARY KEY,                    -- UUID
    session_id TEXT NOT NULL,               -- Foreign key to sessions
    task_id INTEGER,                        -- Foreign key to task.db
    task_title TEXT,                        -- Task title
    status TEXT NOT NULL,                   -- pending, in_progress, completed, failed
    start_time TEXT,                        -- ISO 8601 timestamp
    end_time TEXT,                          -- ISO 8601 timestamp
    duration_seconds REAL,                   -- Task duration
    operation_id TEXT,                      -- Related telemetry operation ID
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_session_tasks_session ON session_tasks(session_id);
CREATE INDEX IF NOT EXISTS idx_session_tasks_status ON session_tasks(status);
```

### Session Config Table

```sql
CREATE TABLE IF NOT EXISTS session_config (
    id TEXT PRIMARY KEY,                    -- UUID
    session_id TEXT NOT NULL,               -- Foreign key to sessions
    config_key TEXT NOT NULL,               -- Configuration key
    config_value TEXT,                      -- Configuration value (JSON string)
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_session_config_session ON session_config(session_id);
CREATE INDEX IF NOT EXISTS idx_session_config_key ON session_config(config_key);
```

---

## Session Manager API

### Initialization

```python
from core.session_manager import SessionManager

# Initialize session manager
session_manager = SessionManager(
    db_path="sessions.db",
    checkpoint_dir="checkpoints/",
    auto_resume=True,                      # Auto-resume interrupted sessions
    max_sessions=10                        # Maximum sessions to keep
)
```

### Starting a Session

```python
# Start a new session
session = session_manager.start_session(
    user="developer",
    host="localhost",
    environment="dev",
    metadata={
        "project": "growmind",
        "branch": "main"
    }
)

print(f"Started session {session.id}")
print(f"Session ID: {session.id}")
print(f"Start time: {session.start_time}")
```

### Resuming a Session

```python
# Resume the last interrupted session
session = session_manager.resume_last_session()

# Resume a specific session
session = session_manager.resume_session(session_id="abc-123")

# List interrupted sessions first
interrupted = session_manager.detect_interrupted_sessions()
if interrupted:
    print("Interrupted sessions:")
    for s in interrupted:
        print(f"  - {s['id']}: {s['status']} at {s['end_time']}")
    
    # Resume specific session
    session = session_manager.resume_session(interrupted[0]['id'])
```

### Pausing a Session

```python
# Pause the current session
session_manager.pause_session(session_id)

# Pause with checkpoint
session_manager.pause_session(
    session_id=session.id,
    create_checkpoint=True,
    checkpoint_reason="Manual pause"
)
```

### Completing a Session

```python
# Complete the current session
session_manager.complete_session(
    session_id=session.id,
    summary="Successfully completed 5 tasks",
    create_checkpoint=True
)

print(f"Session {session.id} completed")
print(f"Duration: {session.total_duration_seconds} seconds")
print(f"Tasks completed: {session.tasks_completed}")
```

### Listing Sessions

```python
# List all sessions
sessions = session_manager.list_sessions()

# List by status
active_sessions = session_manager.list_sessions(status="active")
completed_sessions = session_manager.list_sessions(status="completed")

# List recent sessions
recent_sessions = session_manager.list_sessions(limit=10)

# List for specific user
user_sessions = session_manager.list_sessions(user="developer")
```

### Managing Session Tasks

```python
# Add task to session
session_manager.add_session_task(
    session_id=session.id,
    task_id=42,
    task_title="Add user authentication",
    status="in_progress"
)

# Update task status
session_manager.update_session_task(
    session_id=session.id,
    task_id=42,
    status="completed",
    duration_seconds=45.5
)

# Get session tasks
tasks = session_manager.get_session_tasks(session_id=session.id)
for task in tasks:
    print(f"Task {task['task_id']}: {task['task_title']} - {task['status']}")
```

### Managing Session Configuration

```python
# Set configuration
session_manager.set_config(
    session_id=session.id,
    key="llm.model",
    value="gpt-4"
)

session_manager.set_config(
    session_id=session.id,
    key="cache.enabled",
    value="true"
)

# Get configuration
model = session_manager.get_config(session_id=session.id, key="llm.model")
print(f"LLM model: {model}")

# Get all configuration
config = session_manager.get_all_config(session_id=session.id)
```

### Deleting Sessions

```python
# Delete specific session
session_manager.delete_session(session_id)

# Delete old sessions
session_manager.delete_old_sessions(days=7)

# Delete completed sessions
session_manager.delete_completed_sessions()

# Delete all sessions (use with caution)
session_manager.delete_all_sessions()
```

---

## Session Lifecycle

### Session States

```
┌─────────┐
│  START   │
└────┬────┘
     │
     ▼
┌─────────┐
│  ACTIVE  │ <───┐
└────┬────┘     │
     │          │ (pause)
     │          │
     ▼          │
┌─────────┐     │
│ PAUSED  │─────┘
└────┬────┘
     │
     ▼
┌─────────┐
│COMPLETED│
└─────────┘

     │
     │ (interrupt/error)
     ▼
┌─────────────┐
│INTERRUPTED  │
└─────────────┘
     │
     ▼ (resume)
┌─────────┐
│  ACTIVE  │
└─────────┘
```

### State Transitions

| From State | To State | Trigger |
|------------|-----------|----------|
| START | ACTIVE | Session created |
| ACTIVE | PAUSED | User pauses session |
| ACTIVE | COMPLETED | Session completed successfully |
| ACTIVE | INTERRUPTED | Unexpected interruption (error, crash) |
| PAUSED | ACTIVE | User resumes session |
| INTERRUPTED | ACTIVE | User resumes session |

### Session Lifecycle Example

```python
from core.session_manager import SessionManager
from data.checkpoint_manager import CheckpointManager

session_manager = SessionManager()
checkpoint = CheckpointManager()

# 1. Start new session
session = session_manager.start_session(user="developer")
print(f"Session {session.id} started")

# 2. Work on tasks
for task_id in [1, 2, 3, 4, 5]:
    # Add task to session
    session_manager.add_session_task(
        session_id=session.id,
        task_id=task_id,
        task_title=f"Task {task_id}",
        status="in_progress"
    )
    
    # Implement task
    # ... task implementation ...
    
    # Update task status
    session_manager.update_session_task(
        session_id=session.id,
        task_id=task_id,
        status="completed",
        duration_seconds=30.0
    )

# 3. Complete session
session_manager.complete_session(
    session_id=session.id,
    summary="Completed 5 tasks successfully"
)

print(f"Session {session.id} completed")
```

---

## Session Persistence

### Automatic Session Detection

```python
# Detect interrupted sessions on startup
interrupted = session_manager.detect_interrupted_sessions()

if interrupted:
    print("Interrupted sessions detected:")
    for s in interrupted:
        print(f"  Session {s['id']}: {s['status']}")
        print(f"    Last operation: {s['last_operation']}")
        print(f"    End time: {s['end_time']}")
        print(f"    Checkpoint: {s['checkpoint_id']}")
    
    # Auto-resume if enabled
    if session_manager.auto_resume:
        session = session_manager.resume_last_session()
        print(f"Auto-resumed session {session.id}")
```

### Session State Persistence

```python
# Save session state to disk
def save_session_state(session_id: str):
    session = session_manager.get_session(session_id)
    
    # Save session to file
    state = {
        'session_id': session.id,
        'status': session.status,
        'tasks': session_manager.get_session_tasks(session_id),
        'config': session_manager.get_all_config(session_id),
        'checkpoint_id': session.checkpoint_id
    }
    
    with open(f'.l4_session_{session_id}.json', 'w') as f:
        json.dump(state, f, indent=2)

# Load session state from disk
def load_session_state(session_id: str):
    with open(f'.l4_session_{session_id}.json', 'r') as f:
        state = json.load(f)
    
    # Restore session state
    session = session_manager.resume_session(session_id)
    
    # Restore tasks
    for task in state['tasks']:
        session_manager.add_session_task(
            session_id=session_id,
            task_id=task['task_id'],
            task_title=task['task_title'],
            status=task['status']
        )
    
    # Restore configuration
    for key, value in state['config'].items():
        session_manager.set_config(session_id, key, value)
    
    # Restore checkpoint if available
    if state['checkpoint_id']:
        checkpoint.restore(state['checkpoint_id'])
    
    return session
```

### Session Recovery with Checkpoints

```python
# Recover session from checkpoint
def recover_session(session_id: str):
    session = session_manager.get_session(session_id)
    
    if session.checkpoint_id:
        print(f"Restoring from checkpoint {session.checkpoint_id}")
        checkpoint.restore(session.checkpoint_id)
        
        # Resume session
        session = session_manager.resume_session(session_id)
        print(f"Session {session.id} resumed from checkpoint")
    else:
        print("No checkpoint available for session")
```

### Handling External Changes

```python
# Check for external changes before resume
def check_external_changes(session_id: str):
    session = session_manager.get_session(session_id)
    
    if session.checkpoint_id:
        # Get checkpoint metadata
        checkpoint_info = checkpoint.get_info(session.checkpoint_id)
        
        # Check git status
        git_status = git.get_status()
        
        if git_status.has_changes:
            print("Warning: External changes detected")
            print("Files modified:")
            for file in git_status.modified_files:
                print(f"  - {file}")
            
            # Ask user what to do
            response = input("Continue with resume? [y/n]: ")
            if response.lower() != 'y':
                print("Resume cancelled")
                return False
    
    return True
```

---

## Session Analytics

### Generating Session Reports

```python
# Generate session report
report = session_manager.generate_session_report(session_id=session.id)

print(f"Session Report: {session.id}")
print(f"Start time: {report['start_time']}")
print(f"End time: {report['end_time']}")
print(f"Duration: {report['duration']} seconds")
print(f"Tasks completed: {report['tasks_completed']}")
print(f"Errors: {report['errors_count']}")
print(f"Success rate: {report['success_rate']}%")
```

### Session Statistics

```python
# Get session statistics
stats = session_manager.get_session_statistics()

print(f"Total sessions: {stats['total_sessions']}")
print(f"Active sessions: {stats['active_sessions']}")
print(f"Completed sessions: {stats['completed_sessions']}")
print(f"Interrupted sessions: {stats['interrupted_sessions']}")
print(f"Average duration: {stats['avg_duration']} seconds")
print(f"Total tasks completed: {stats['total_tasks_completed']}")
```

### Productivity Metrics

```python
# Get productivity metrics
metrics = session_manager.get_productivity_metrics(user="developer")

print(f"Productivity Metrics for {user}")
print(f"Sessions: {metrics['session_count']}")
print(f"Total time: {metrics['total_time']} hours")
print(f"Tasks per hour: {metrics['tasks_per_hour']}")
print(f"Tasks per session: {metrics['tasks_per_session']}")
print(f"Success rate: {metrics['success_rate']}%")
```

### Session Timeline

```python
# Generate session timeline
timeline = session_manager.generate_timeline(session_id=session.id)

print(f"Session Timeline: {session.id}")
for event in timeline:
    print(f"{event['timestamp']} - {event['type']}: {event['message']}")
```

### Comparing Sessions

```python
# Compare two sessions
comparison = session_manager.compare_sessions(
    session_id_1="abc-123",
    session_id_2="def-456"
)

print(f"Session Comparison:")
print(f"Duration: {comparison['duration_diff']} seconds")
print(f"Tasks: {comparison['tasks_diff']} tasks")
print(f"Errors: {comparison['errors_diff']} errors")
```

---

## Best Practices

### 1. Always Complete Sessions

```python
# Good
try:
    # ... work on tasks ...
    pass
finally:
    session_manager.complete_session(session.id, summary="Session completed")

# Bad
# Session left in active state
```

### 2. Create Checkpoints on Pause

```python
# Good
session_manager.pause_session(
    session_id=session.id,
    create_checkpoint=True,
    checkpoint_reason="Manual pause"
)

# Bad
session_manager.pause_session(session_id)  # No checkpoint
```

### 3. Track Task Progress

```python
# Good
for task_id in tasks:
    session_manager.add_session_task(
        session_id=session.id,
        task_id=task_id,
        task_title=f"Task {task_id}",
        status="in_progress"
    )
    
    # ... implement task ...
    
    session_manager.update_session_task(
        session_id=session.id,
        task_id=task_id,
        status="completed"
    )

# Bad
# No task tracking
```

### 4. Use Session Configuration

```python
# Good
session_manager.set_config(session_id, "llm.model", "gpt-4")
session_manager.set_config(session_id, "cache.enabled", "true")

# Later in session
model = session_manager.get_config(session_id, "llm.model")

# Bad
# Hardcoded configuration
model = "gpt-4"
```

### 5. Handle Interrupted Sessions Gracefully

```python
# Good
interrupted = session_manager.detect_interrupted_sessions()
if interrupted:
    print("Interrupted sessions detected")
    for s in interrupted:
        print(f"  - {s['id']}: {s['status']}")
    
    response = input("Resume last session? [y/n]: ")
    if response.lower() == 'y':
        session = session_manager.resume_last_session()

# Bad
# Ignore interrupted sessions
```

### 6. Monitor Session Health

```python
# Good
if session.errors_count > 10:
    logger.warning(f"High error rate in session {session.id}: {session.errors_count} errors")

if session.total_duration_seconds > 3600:
    logger.info(f"Session {session.id} has been running for over 1 hour")

# Bad
# No monitoring
```

### 7. Regularly Analyze Sessions

```python
# Good
stats = session_manager.get_session_statistics()
print(f"Success rate: {stats['success_rate']}%")

if stats['success_rate'] < 80:
    logger.warning("Low success rate detected, investigate issues")

# Bad
# Never analyze sessions
```

### 8. Archive Old Sessions

```python
# Good
session_manager.delete_old_sessions(days=30)

# Or export to archive
session_manager.export_sessions_to_archive(archive_dir="archive/", days=30)

# Bad
# Sessions accumulate indefinitely
```

### 9. Use Descriptive Metadata

```python
# Good
session = session_manager.start_session(
    user="developer",
    metadata={
        "project": "growmind",
        "branch": "feature/auth",
        "goal": "Implement JWT authentication"
    }
)

# Bad
session = session_manager.start_session(user="developer")
```

### 10. Document Session Usage

```python
# Good
"""
Sessions are used to track:
- Task progress and completion
- Time spent on development
- Error rates and patterns
- User preferences and configuration

Session lifecycle:
1. Start session
2. Add tasks to session
3. Work on tasks
4. Complete session
"""

# Bad
# No documentation
```

---

## CLI Commands

### Session Management

```bash
# List all sessions
l4-dev sessions list

# List active sessions
l4-dev sessions list --status active

# List recent sessions
l4-dev sessions list --limit 10

# Show session details
l4-dev sessions show --id <session-id>

# Resume session
l4-dev resume

# Resume specific session
l4-dev resume --session-id <session-id>

# Pause session
l4-dev sessions pause

# Complete session
l4-dev sessions complete --summary "Session completed"
```

### Session Analytics

```bash
# Get session statistics
l4-dev sessions stats

# Get session report
l4-dev sessions report --id <session-id>

# Compare sessions
l4-dev sessions compare --id1 <session-id-1> --id2 <session-id-2>

# Generate timeline
l4-dev sessions timeline --id <session-id>
```

### Session Configuration

```bash
# Set configuration
l4-dev sessions config set --key llm.model --value gpt-4

# Get configuration
l4-dev sessions config get --key llm.model

# List all configuration
l4-dev sessions config list
```

### Session Cleanup

```bash
# Delete session
l4-dev sessions delete --id <session-id>

# Delete old sessions
l4-dev sessions delete --old-days 7

# Delete completed sessions
l4-dev sessions delete --status completed
```

---

## Troubleshooting

### Session Not Found

**Problem**: Attempting to resume a session that doesn't exist.

**Solution**:
1. List available sessions: `session_manager.list_sessions()`
2. Check session ID for typos
3. Verify session wasn't deleted
4. Check if session was archived

### Session Won't Resume

**Problem**: Session resume fails with error.

**Solution**:
1. Check checkpoint exists: Verify checkpoint_id is valid
2. Validate checkpoint: Use `checkpoint.validate(checkpoint_id)`
3. Check file permissions: Ensure write access to session files
4. Check database integrity: Verify sessions.db is not corrupted

### Stuck in Active State

**Problem**: Session remains in active state after completion.

**Solution**:
1. Manually complete session: `session_manager.complete_session(session_id)`
2. Check for errors in session manager logs
3. Verify no operations are still running
4. Restart session manager if needed

### Missing Session Tasks

**Problem**: Session tasks are not being tracked.

**Solution**:
1. Verify tasks are being added: Check add_session_task() calls
2. Check database integrity: Verify session_tasks table exists
3. Check session ID is correct: Ensure tasks are added to correct session
4. Review session manager logs for errors

### Session Configuration Lost

**Problem**: Session configuration is not being saved.

**Solution**:
1. Verify set_config() is being called correctly
2. Check database integrity: Verify session_config table exists
3. Check for database write errors: Review session manager logs
4. Verify session ID is correct

---

## Performance Considerations

### Session Operations

| Operation | Time Complexity | Notes |
|------------|-----------------|-------|
| start_session() | O(1) | Creates new session |
| resume_session() | O(1) | Updates session status |
| add_session_task() | O(1) | Inserts task record |
| update_session_task() | O(1) | Updates task record |
| get_session() | O(1) | Queries by primary key |
| list_sessions() | O(n) | Scans all sessions |
| delete_session() | O(1) | Deletes session and related tasks |

### Database Size

| Sessions per Day | DB Size after 30 Days | Tasks per Session | DB Size |
|------------------|----------------------|-------------------|---------|
| 5 | ~150 | 10 | ~2 MB |
| 10 | ~300 | 10 | ~4 MB |
| 20 | ~600 | 10 | ~8 MB |

### Memory Usage

| Component | Memory Usage |
|-----------|--------------|
| Session object | ~1 KB |
| Session tasks (10) | ~10 KB |
| Session config (5) | ~5 KB |
| **Total per session** | **~16 KB** |

---

## Conclusion

The L4D V3 Session Management System provides comprehensive session tracking and persistence capabilities. By following best practices outlined in this document, you can ensure seamless continuation of work across multiple runs and track developer productivity over time.

For more information, see:
- [TELEMETRY.md](TELEMETRY.md) - Telemetry system documentation
- [LOGGING.md](LOGGING.md) - Structured logging
- [RESUMABILITY.md](RESUMABILITY.md) - Checkpoint and recovery
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Common issues and solutions