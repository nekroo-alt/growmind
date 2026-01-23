# Troubleshooting Guide

## Overview

This guide provides solutions to common issues encountered when using L4D V3. It covers telemetry, logging, checkpoint/recovery, session management, and general troubleshooting.

---

## Table of Contents

- [Telemetry Issues](#telemetry-issues)
- [Logging Issues](#logging-issues)
- [Checkpoint Issues](#checkpoint-issues)
- [Session Management Issues](#session-management-issues)
- [Database Issues](#database-issues)
- [Performance Issues](#performance-issues)
- [Integration Issues](#integration-issues)
- [Getting Help](#getting-help)

---

## Telemetry Issues

### Telemetry Not Recording

**Symptoms**: Operations are not being tracked in telemetry database.

**Possible Causes**:
1. Telemetry is disabled
2. Database is not writable
3. Telemetry manager not initialized
4. Operation tracking not implemented

**Solutions**:

1. **Check telemetry is enabled**:
   ```bash
   export L4_TELEMETRY_ENABLED=true
   ```

2. **Check database permissions**:
   ```bash
   ls -la telemetry.db
   chmod 644 telemetry.db
   ```

3. **Verify telemetry manager is initialized**:
   ```python
   from data.telemetry_manager import TelemetryManager
   telemetry = TelemetryManager()
   print(f"Telemetry enabled: {telemetry.enabled}")
   ```

4. **Check operation tracking**:
   ```python
   # Ensure operations use telemetry.track_operation()
   with telemetry.track_operation("implementation", "Implement task") as op:
       # ... work ...
       pass
   ```

### Telemetry Database Locked

**Symptoms**: Operations fail with "database is locked" error.

**Possible Causes**:
1. Multiple processes accessing database
2. Previous process crashed without closing database
3. Long-running transaction holding lock

**Solutions**:

1. **Check for running processes**:
   ```bash
   ps aux | grep l4-dev
   pkill -f l4-dev  # Stop all l4-dev processes
   ```

2. **Remove lock file** (if exists):
   ```bash
   rm -f telemetry.db-wal
   rm -f telemetry.db-shm
   ```

3. **Use WAL mode** (recommended):
   ```python
   # Initialize telemetry with WAL mode
   telemetry = TelemetryManager(wal_mode=True)
   ```

### Telemetry Queries Slow

**Symptoms**: Querying telemetry data takes a long time.

**Possible Causes**:
1. Large database size
2. Missing indexes
3. Complex queries without filters

**Solutions**:

1. **Archive old telemetry data**:
   ```python
   telemetry.archive_old_data(days_to_keep=30, archive_path="archive/")
   ```

2. **Add indexes for frequently queried fields**:
   ```python
   # Indexes are created automatically, but you can add custom indexes
   telemetry.execute_sql("""
       CREATE INDEX IF NOT EXISTS idx_operations_custom
       ON operations(operation_type, status)
   """)
   ```

3. **Use time range filters**:
   ```python
   # Bad: queries all data
   operations = telemetry.query_operations()
   
   # Good: queries limited time range
   operations = telemetry.query_operations(
       start_time="2026-01-21T00:00:00Z",
       end_time="2026-01-21T23:59:59Z"
   )
   ```

### High Telemetry Overhead

**Symptoms**: Operations are significantly slower with telemetry enabled.

**Possible Causes**:
1. Excessive event recording
2. Resource monitoring enabled
3. Database write operations

**Solutions**:

1. **Disable resource monitoring**:
   ```bash
   export L4_RESOURCE_MONITORING=false
   ```

2. **Reduce event recording**:
   ```python
   # Bad: record every detail
   op.record_event("step1", "info", "Step 1 completed")
   op.record_event("step2", "info", "Step 2 completed")
   op.record_event("step3", "info", "Step 3 completed")
   
   # Good: record only important events
   op.record_event("processing", "info", "Task processing started")
   ```

3. **Disable telemetry for performance-critical operations**:
   ```python
   telemetry = TelemetryManager(enabled=False)
   ```

---

## Logging Issues

### Logs Not Appearing

**Symptoms**: Log entries are not being written to files or console.

**Possible Causes**:
1. Logging not initialized
2. Log level too high
3. File permissions issue
4. Wrong log file path

**Solutions**:

1. **Initialize logging**:
   ```python
   from core.logging_config import setup_logging
   setup_logging()
   ```

2. **Check log level**:
   ```python
   import logging
   logger = logging.getLogger(__name__)
   logger.setLevel(logging.DEBUG)
   ```

3. **Check file permissions**:
   ```bash
   ls -la l4.log
   touch l4.log
   chmod 644 l4.log
   ```

4. **Verify log file path**:
   ```bash
   export L4_LOG_FILE=l4.log
   export L4_ERROR_LOG_FILE=l4_error.log
   ```

### Log Files Too Large

**Symptoms**: Log files are consuming too much disk space.

**Possible Causes**:
1. No log rotation configured
2. Log level too verbose (DEBUG)
3. Excessive logging

**Solutions**:

1. **Enable log rotation**:
   ```python
   from core.logging_config import setup_logging
   setup_logging(
       max_file_size_mb=10,  # Rotate at 10MB
       backup_count=5          # Keep 5 backup files
   )
   ```

2. **Reduce log level**:
   ```python
   setup_logging(log_level="WARNING")  # Only log warnings and errors
   ```

3. **Archive old logs**:
   ```bash
   mv l4.log.1 archive/
   mv l4.log.2 archive/
   ```

### Missing Context in Logs

**Symptoms**: Log entries lack context information (task_id, operation_id, etc.).

**Possible Causes**:
1. Not using structured logging
2. Missing operation correlation
3. Not including context parameters

**Solutions**:

1. **Use structured logging**:
   ```python
   from core.logging_config import format_log_message
   
   # Good
   logger.info(
       format_log_message(
           "Task implementation started",
           task_id=task.id,
           operation_id=op_id
       )
   )
   
   # Bad
   logger.info(f"Task {task.id} implementation started")
   ```

2. **Correlate with operations**:
   ```python
   from core.logging_config import get_logger_with_operation
   
   logger = get_logger_with_operation(__name__, operation_id="abc-123")
   logger.info("This log is correlated with operation abc-123")
   ```

---

## Checkpoint Issues

### Checkpoint Creation Failed

**Symptoms**: Checkpoint creation fails with file system error.

**Possible Causes**:
1. Insufficient disk space
2. File permissions issue
3. Database locked
4. Git repository not clean

**Solutions**:

1. **Check disk space**:
   ```bash
   df -h
   # Ensure at least 1GB free space
   ```

2. **Check file permissions**:
   ```bash
   ls -la checkpoints/
   chmod 755 checkpoints/
   ```

3. **Check database locks**:
   ```bash
   rm -f *.db-wal
   rm -f *.db-shm
   ```

4. **Check git status**:
   ```bash
   git status
   # Commit or stash changes before creating checkpoint
   ```

### Checkpoint Restore Failed

**Symptoms**: Checkpoint restoration fails with validation error.

**Possible Causes**:
1. Checkpoint corrupted
2. Backup files missing
3. Database restore conflict
4. File permissions issue

**Solutions**:

1. **Validate checkpoint**:
   ```python
   is_valid = checkpoint.validate(checkpoint_id)
   if not is_valid:
       logger.error(f"Checkpoint {checkpoint_id} is invalid")
   ```

2. **Check backup files**:
   ```bash
   ls -la checkpoints/chkp_*/
   # Verify all backup files exist
   ```

3. **Use dry-run to preview**:
   ```python
   changes = checkpoint.restore(checkpoint_id, dry_run=True)
   print("Restore preview:")
   for change in changes:
       print(f"  - {change['type']}: {change['path']}")
   ```

4. **Check file permissions**:
   ```bash
   chmod 644 *.db
   chmod 755 checkpoints/chkp_*/
   ```

### Checkpoint Directory Too Large

**Symptoms**: Checkpoint directory is consuming too much disk space.

**Possible Causes**:
1. Too many checkpoints
2. Old checkpoints not cleaned up
3. Large databases

**Solutions**:

1. **Delete old checkpoints**:
   ```python
   checkpoint.delete_old(days=7)
   ```

2. **Delete excess checkpoints**:
   ```python
   checkpoint.delete_excess()
   ```

3. **Reduce checkpoint frequency**:
   ```python
   from data.checkpoint_manager import CheckpointPolicy
   
   policy = CheckpointPolicy(
       max_count=5,          # Keep only 5 checkpoints
       max_age_hours=12        # Keep checkpoints for 12 hours
   )
   ```

---

## Session Management Issues

### Session Not Found

**Symptoms**: Attempting to resume a session that doesn't exist.

**Possible Causes**:
1. Session ID incorrect
2. Session was deleted
3. Session was archived
4. Database corruption

**Solutions**:

1. **List available sessions**:
   ```python
   sessions = session_manager.list_sessions()
   for s in sessions:
       print(f"  - {s['id']}: {s['status']}")
   ```

2. **Check for deleted sessions**:
   ```bash
   sqlite3 sessions.db "SELECT * FROM sessions;"
   ```

3. **Check for archived sessions**:
   ```bash
   ls -la archive/
   ```

### Session Won't Resume

**Symptoms**: Session resume fails with error.

**Possible Causes**:
1. Checkpoint invalid
2. Session corrupted
3. External changes conflict
4. Database locked

**Solutions**:

1. **Validate checkpoint**:
   ```python
   session = session_manager.get_session(session_id)
   if session.checkpoint_id:
       is_valid = checkpoint.validate(session.checkpoint_id)
       if not is_valid:
           logger.error(f"Checkpoint {session.checkpoint_id} is invalid")
   ```

2. **Check for external changes**:
   ```bash
   git status
   # Resolve or stash changes before resuming
   ```

3. **Check database integrity**:
   ```bash
   sqlite3 sessions.db "PRAGMA integrity_check;"
   ```

### Stuck in Active State

**Symptoms**: Session remains in active state after completion.

**Possible Causes**:
1. Session not completed properly
2. Exception during completion
3. Process crashed

**Solutions**:

1. **Manually complete session**:
   ```python
   session_manager.complete_session(
       session_id=session_id,
       summary="Manually completed session"
   )
   ```

2. **Check for errors**:
   ```python
   import logging
   logger = logging.getLogger(__name__)
   logger.info(f"Session status: {session.status}")
   ```

---

## Database Issues

### Database Locked

**Symptoms**: Database operations fail with "database is locked" error.

**Possible Causes**:
1. Multiple processes accessing database
2. Long-running transaction
3. Previous process crashed

**Solutions**:

1. **Stop all processes**:
   ```bash
   ps aux | grep l4-dev
   pkill -f l4-dev
   ```

2. **Remove lock files**:
   ```bash
   rm -f *.db-wal
   rm -f *.db-shm
   ```

3. **Use WAL mode**:
   ```python
   # In db_manager.py
   conn = sqlite3.connect(db_path)
   conn.execute("PRAGMA journal_mode=WAL")
   ```

### Database Corruption

**Symptoms**: Database operations fail with corruption error.

**Possible Causes**:
1. Disk failure
2. Process crash during write
3. Power failure

**Solutions**:

1. **Check database integrity**:
   ```bash
   sqlite3 task.db "PRAGMA integrity_check;"
   sqlite3 activity.db "PRAGMA integrity_check;"
   sqlite3 telemetry.db "PRAGMA integrity_check;"
   sqlite3 sessions.db "PRAGMA integrity_check;"
   sqlite3 snapshots.db "PRAGMA integrity_check;"
   ```

2. **Restore from backup**:
   ```bash
   cp task.db.backup task.db
   cp activity.db.backup activity.db
   ```

3. **Reinitialize database** (last resort):
   ```python
   from data.db_manager import DatabaseManager
   db_manager = DatabaseManager()
   db_manager.initialize_schema()
   ```

---

## Performance Issues

### Slow Operations

**Symptoms**: Operations are slower than expected.

**Possible Causes**:
1. Telemetry overhead
2. Logging overhead
3. Cache misses
4. Database queries

**Solutions**:

1. **Disable telemetry**:
   ```python
   telemetry = TelemetryManager(enabled=False)
   ```

2. **Reduce logging level**:
   ```python
   setup_logging(log_level="WARNING")
   ```

3. **Check cache hit rate**:
   ```python
   stats = cache_manager.get_stats()
   print(f"Cache hit rate: {stats['hit_rate']}%")
   ```

4. **Optimize database queries**:
   ```python
   # Use indexes
   # Limit result size
   # Use time range filters
   ```

### High Memory Usage

**Symptoms**: Process is consuming too much memory.

**Possible Causes**:
1. Cache too large
2. Too many checkpoints loaded
3. Memory leak

**Solutions**:

1. **Reduce cache size**:
   ```python
   cache_manager = CacheManager(max_size_mb=50)
   ```

2. **Clean up checkpoints**:
   ```python
   checkpoint.delete_old(days=7)
   ```

3. **Monitor memory usage**:
   ```python
   import psutil
   process = psutil.Process()
   print(f"Memory usage: {process.memory_info().rss / 1024 / 1024:.2f} MB")
   ```

### High CPU Usage

**Symptoms**: Process is consuming too much CPU.

**Possible Causes**:
1. Resource monitoring
2. Continuous polling
3. Inefficient queries

**Solutions**:

1. **Disable resource monitoring**:
   ```bash
   export L4_RESOURCE_MONITORING=false
   ```

2. **Increase polling interval**:
   ```python
   # In telemetry_manager.py
   RESOURCE_MONITOR_INTERVAL = 2.0  # seconds
   ```

3. **Profile code**:
   ```python
   import cProfile
   cProfile.run('your_function()')
   ```

---

## Integration Issues

### LLM API Errors

**Symptoms**: LLM API calls are failing.

**Possible Causes**:
1. API key invalid
2. Rate limit exceeded
3. Network issue
4. API endpoint changed

**Solutions**:

1. **Check API key**:
   ```bash
   export L4_LLM_API_KEY=your_api_key
   ```

2. **Check rate limit**:
   ```python
   from core.error_handling import retry_with_backoff
   
   @retry_with_backoff(max_attempts=3, base_delay=1.0)
   def call_llm():
       # ... call LLM ...
       pass
   ```

3. **Check network connectivity**:
   ```bash
   ping api.openai.com
   curl https://api.openai.com
   ```

4. **Check telemetry for LLM errors**:
   ```python
   ops = telemetry.query_operations(operation_type="llm_call", status="failed")
   for op in ops:
       events = telemetry.get_events(op['id'])
       for e in events:
           print(f"Error: {e['message']}")
   ```

### Git Integration Issues

**Symptoms**: Git operations are failing.

**Possible Causes**:
1. Git not initialized
2. Git repository not clean
3. Git permission issues
4. Git config issues

**Solutions**:

1. **Initialize git repository**:
   ```bash
   git init
   ```

2. **Check git status**:
   ```bash
   git status
   # Commit or stash changes
   ```

3. **Check git permissions**:
   ```bash
   ls -la .git/
   chmod -R 755 .git/
   ```

4. **Check git config**:
   ```bash
   git config --list
   git config user.name "Your Name"
   git config user.email "your.email@example.com"
   ```

---

## Getting Help

### Diagnostic Information

When seeking help, gather the following information:

1. **System Information**:
   ```bash
   python --version
   sqlite3 --version
   git --version
   uname -a
   ```

2. **L4D Version**:
   ```bash
   cd v2
   git log -1 --oneline
   ```

3. **Configuration**:
   ```bash
   cat .l4_config
   env | grep L4_
   ```

4. **Logs**:
   ```bash
   cat l4.log
   cat l4_error.log
   ```

5. **Database Information**:
   ```bash
   ls -la *.db
   du -sh *.db
   ```

6. **Checkpoint Information**:
   ```bash
   ls -la checkpoints/
   du -sh checkpoints/
   ```

### Reporting Issues

When reporting issues, include:

1. **Description**: Clear description of the issue
2. **Steps to Reproduce**: Detailed steps to reproduce the issue
3. **Expected Behavior**: What you expected to happen
4. **Actual Behavior**: What actually happened
5. **Error Messages**: Full error messages and stack traces
6. **Diagnostic Information**: All diagnostic information listed above
7. **Screenshots**: Relevant screenshots if applicable

### Common Workarounds

If you encounter an issue and need a quick workaround:

1. **Restart the system**:
   ```bash
   pkill -f l4-dev
   # Wait a few seconds
   l4-dev start
   ```

2. **Clear cache**:
   ```bash
   rm -rf .l4_cache/*
   ```

3. **Reinitialize databases**:
   ```bash
   rm -f *.db
   l4-dev init
   ```

4. **Use default configuration**:
   ```bash
   unset L4_*
   l4-dev start
   ```

---

## Prevention

### Best Practices to Avoid Issues

1. **Regular Backups**:
   - Backup databases regularly
   - Archive old checkpoints
   - Keep configuration backups

2. **Monitor Resources**:
   - Monitor disk space
   - Monitor memory usage
   - Monitor CPU usage

3. **Regular Maintenance**:
   - Clean up old checkpoints
   - Archive old telemetry data
   - Rotate log files

4. **Update Regularly**:
   - Keep dependencies updated
   - Apply security patches
   - Test updates before deployment

5. **Document Changes**:
   - Document configuration changes
   - Document custom modifications
   - Keep change logs

---

## Conclusion

This troubleshooting guide covers common issues and their solutions. If you encounter an issue not covered here, gather the diagnostic information and seek help from the community or support team.

For more information, see:
- [TELEMETRY.md](TELEMETRY.md) - Telemetry system documentation
- [LOGGING.md](LOGGING.md) - Structured logging documentation
- [RESUMABILITY.md](RESUMABILITY.md) - Checkpoint and recovery documentation
- [SESSION_MANAGEMENT.md](SESSION_MANAGEMENT.md) - Session management documentation
- [MIGRATION_V2_TO_V3.md](MIGRATION_V2_TO_V3.md) - Migration guide