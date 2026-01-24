import sys
import os
import sqlite3
import argparse
from datetime import datetime, timedelta
from typing import Dict, Any

# Get__name__ absolute path of the L4 root (parent of v1)
# __file__ is /Users/ken/Desktop/growmind/v1/l4_cli.py
# L4_ROOT is /Users/ken/Desktop/growmind
L4_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Ensure L4_ROOT is in sys.path so that 'import v1' works even after chdir
if L4_ROOT not in sys.path:
    sys.path.insert(0, L4_ROOT)

from core.start import Orchestrator
from data.db_manager import TASK_DB_PATH, ACTIVITY_DB_PATH, init_db, get_cost_summary
from retro.retro_agent import RetroAgent
from core.log_analyzer import LogAnalyzer, LogQuery


def cmd_start(args):
    orchestrator = Orchestrator()
    orchestrator.run()


def cmd_status(args):
    from core.ui import create_status_dashboard
    from core.health_check import run_health_check
    from core.session_manager import SessionManager
    from data.cache_manager import CacheManager
    import psutil

    # Try to use enhanced dashboard first
    try:
        dashboard = create_status_dashboard()

        # Gather session information
        session_info = None
        try:
            session_mgr = SessionManager()
            active_sessions = session_mgr.list_sessions()
            if active_sessions:
                # Get the most recent active session
                latest_session = sorted(
                    active_sessions, key=lambda s: s.get("start_time", ""), reverse=True
                )[0]
                session_info = {
                    "id": latest_session.get("id"),
                    "status": latest_session.get("status"),
                    "start_time": latest_session.get("start_time"),
                    "tasks_completed": latest_session.get("tasks_completed", 0),
                }
        except Exception:
            pass  # Session manager might not be initialized yet

        # Gather active operation information
        active_operation = None
        try:
            from data.telemetry_manager import TelemetryManager

            telemetry_mgr = TelemetryManager()
            in_progress_ops = telemetry_mgr.query_operations(
                status="in_progress", limit=1
            )
            if in_progress_ops:
                op = in_progress_ops[0]
                active_operation = {
                    "operation_type": op.get("operation_type"),
                    "status": op.get("status"),
                    "task_id": op.get("task_id"),
                    "task_title": op.get("task_title"),
                    "progress": {
                        "completed": op.get("completed", 0),
                        "total": op.get("total", 100),
                        "percentage": op.get("percentage", 0),
                    },
                }
        except Exception:
            pass  # Telemetry might not be initialized

        # Gather recent activities
        recent_activities = []
        if os.path.exists(ACTIVITY_DB_PATH):
            conn = sqlite3.connect(ACTIVITY_DB_PATH)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT timestamp, action, status, summary, tokens_used, estimated_cost FROM activities ORDER BY timestamp DESC LIMIT 5"
            )
            rows = cursor.fetchall()
            conn.close()

            for row in rows:
                recent_activities.append(
                    {
                        "timestamp": row[0],
                        "action_type": row[1],
                        "status": row[2],
                        "summary": row[3],
                        "tokens_used": row[4] if row[4] else 0,
                        "estimated_cost": row[5] if row[5] else 0.0,
                    }
                )

        # Gather health report
        health_report = None
        try:
            report = run_health_check(verbose=False, auto_fix=False)
            health_report = {
                "overall_status": report.overall_status.value,
                "checks": {},
            }
            for check_name, check_result in report.checks.items():
                health_report["checks"][check_name] = {
                    "status": check_result.status.value,
                    "details": (
                        check_result.details if hasattr(check_result, "details") else {}
                    ),
                }
        except Exception:
            pass

        # Gather resource usage
        resource_usage = {}
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=0.1)
            resource_usage["cpu"] = cpu_percent

            # Memory usage
            memory = psutil.virtual_memory()
            resource_usage["memory"] = memory.used / (1024**3)  # Convert to GB

            # Cache information
            try:
                cache_mgr = CacheManager()
                stats = cache_mgr.get_stats()
                resource_usage["cache_size"] = stats.get("total_size_mb", 0)
                resource_usage["cache_hit_rate"] = stats.get("hit_rate", 0) * 100
            except Exception:
                pass
        except Exception:
            pass

        # Display the dashboard
        dashboard.display(
            session_info=session_info,
            active_operation=active_operation,
            recent_activities=recent_activities if args.verbose else None,
            health_report=health_report,
            resource_usage=resource_usage,
            verbose=args.verbose,
        )

        # Show cost summary separately
        total_tokens, total_cost = get_cost_summary()
        print(f"\n💰 Cost Summary: {total_tokens:,} tokens | ${total_cost:.4f}")

        # Handle watch mode
        if args.watch:
            dashboard.watch(
                interval=args.interval,
                max_iterations=args.iterations,
                session_info=session_info,
                active_operation=active_operation,
                recent_activities=recent_activities if args.verbose else None,
                health_report=health_report,
                resource_usage=resource_usage,
                verbose=args.verbose,
            )

    except Exception as e:
        # Fallback to original status display if dashboard fails
        print(f"L4 Platform v3.0 Status (Dashboard unavailable: {e})")
        print("\n--- Cost Summary ---")
        total_tokens, total_cost = get_cost_summary()
        print(f"Total Tokens Used: {total_tokens}")
        print(f"Total Estimated Cost: ${total_cost:.4f}")

        # Learned Patterns
        print("\n--- Learned Patterns ---")
        patterns_path = os.path.join(".patterns", "coding_style.md")
        if os.path.exists(patterns_path):
            with open(patterns_path, "r") as f:
                lines = f.readlines()
                # Just show headers as a summary
                headers = [
                    line.strip("# ").strip() for line in lines if line.startswith("##")
                ]
                if headers:
                    # Remove duplicates while preserving order
                    unique_headers = []
                    for h in headers:
                        if h not in unique_headers:
                            unique_headers.append(h)
                    for h in unique_headers:
                        print(f"- {h}")
                else:
                    print("No specific patterns identified yet.")
        else:
            print("No patterns directory found.")

        # Activity Status
        if os.path.exists(ACTIVITY_DB_PATH):
            conn = sqlite3.connect(ACTIVITY_DB_PATH)
            cursor = conn.cursor()
            # Querying with tokens and cost if they exist (Task 0.2)
            cursor.execute(
                "SELECT timestamp, action, status, summary, tokens_used, estimated_cost FROM activities ORDER BY timestamp DESC LIMIT 5"
            )
            rows = cursor.fetchall()
            print("\nRecent Activities (activity.db):")
            for row in rows:
                tokens = row[4] if row[4] is not None else 0
                cost = row[5] if row[5] is not None else 0.0
                print(
                    f"{row[0]} | {row[1]} | {row[2]} | {row[3]} | Tokens: {tokens} | Cost: ${cost:.4f}"
                )
            conn.close()
        else:
            print("Activity database not found.")

        # Task Status
        if os.path.exists(TASK_DB_PATH):
            conn = sqlite3.connect(TASK_DB_PATH)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, title, status, module FROM tasks ORDER BY id DESC LIMIT 5"
            )
            rows = cursor.fetchall()
            print("\nRecent Tasks (task.db):")
            for row in rows:
                print(f"{row[0]} | {row[1]} | {row[2]} | {row[3]}")
            conn.close()
        else:
            print("Task database not found.")


def cmd_retro(args):
    agent = RetroAgent()
    result = agent.analyze_human_override()
    print(result)


def cmd_doctor(args):
    try:
        from core.doctor import run_doctor

        run_doctor()
    except ImportError:
        print("Error: rich library required for doctor. Please install it.")
        # Fallback to basic check if rich is missing (though we checked and it's there)
        print(f"Python Version: {sys.version}")
        print(f"Task DB: {'[OK]' if os.path.exists(TASK_DB_PATH) else '[MISSING]'}")


def cmd_init(args):
    from core.init import run_init

    run_init()


def cmd_reset(args):
    print("Resetting databases...")
    for db_path in [TASK_DB_PATH, ACTIVITY_DB_PATH]:
        if os.path.exists(db_path):
            os.remove(db_path)
            print(f"Removed {db_path}")
    init_db()
    print("Databases re-initialized.")


def cmd_logs(args):
    """Log analysis and search command."""
    analyzer = LogAnalyzer(log_dir=args.log_dir)
    analyzer.load_logs()

    # Build query based on arguments
    query = LogQuery(
        level=args.level,
        module=args.module,
        operation_id=args.operation_id,
        task_id=args.task_id,
        session_id=args.session_id,
        search=args.search,
        has_error=args.error,
    )

    # Parse time range if provided
    if args.last:
        try:
            hours = int(args.last.rstrip("h"))
            start_time = datetime.now() - timedelta(hours=hours)
            query.start_time = start_time
        except ValueError:
            print(f"Invalid time range: {args.last}")
            return

    # Execute query
    entries = analyzer.search(query)

    if not entries:
        print("No matching log entries found.")
        return

    # Display results
    print(f"\nFound {len(entries)} matching log entries:\n")

    for entry in entries:
        timestamp = (
            entry.timestamp.strftime("%Y-%m-%d %H:%M:%S") if entry.timestamp else "N/A"
        )
        print(f"[{timestamp}] [{entry.level}] {entry.message}")
        if entry.module:
            print(f"  Module: {entry.module}:{entry.function}:{entry.line}")
        if entry.operation_id:
            print(f"  Operation: {entry.operation_id}")
        if entry.task_id:
            print(f"  Task: {entry.task_id}")
        if entry.exception:
            print(f"  Exception: {entry.exception[:100]}...")
        print()

    # Export if requested
    if args.export:
        if args.export.endswith(".csv"):
            analyzer.export_to_csv(query, args.export)
        elif args.export.endswith(".json"):
            analyzer.export_to_json(query, args.export)
        else:
            print(f"Unsupported export format: {args.export}")


def cmd_logs_summary(args):
    """Generate log summary statistics."""
    analyzer = LogAnalyzer(log_dir=args.log_dir)
    analyzer.load_logs()

    # Build query if filters provided
    query = None
    if args.level or args.module or args.operation_id or args.task_id:
        query = LogQuery(
            level=args.level,
            module=args.module,
            operation_id=args.operation_id,
            task_id=args.task_id,
        )

    summary = analyzer.generate_summary(query)

    print("\n=== Log Summary ===\n")
    print(f"Total Entries: {summary['total_entries']}")
    print(f"Error Count: {summary['error_count']}")

    if summary["time_range"]["start"]:
        print(f"\nTime Range:")
        print(f"  Start: {summary['time_range']['start']}")
        print(f"  End: {summary['time_range']['end']}")

    print(f"\nBy Level:")
    for level, count in summary["by_level"].items():
        print(f"  {level}: {count}")

    print(f"\nTop 10 Modules:")
    for module, count in summary["by_module"].items():
        print(f"  {module}: {count}")

    if summary["by_operation"]:
        print(f"\nTop 10 Operations:")
        for op_id, count in summary["by_operation"].items():
            print(f"  {op_id}: {count}")


def cmd_logs_errors(args):
    """Show error patterns."""
    analyzer = LogAnalyzer(log_dir=args.log_dir)
    analyzer.load_logs()

    patterns = analyzer.identify_error_patterns()

    if not patterns:
        print("\nNo error patterns found.")
        return

    print("\n=== Error Patterns ===\n")
    for pattern in patterns:
        print(f"Error Type: {pattern['error_type']}")
        print(f"Count: {pattern['count']}")
        if pattern["first_occurrence"]:
            print(f"First: {pattern['first_occurrence']}")
        if pattern["last_occurrence"]:
            print(f"Last: {pattern['last_occurrence']}")
        print("\nMessage Patterns:")
        for msg_pattern, count in pattern["message_patterns"].items():
            print(f"  ({count}x) {msg_pattern}")
        print()


def cmd_logs_timeline(args):
    """Generate operation timeline."""
    analyzer = LogAnalyzer(log_dir=args.log_dir)
    analyzer.load_logs()

    if not args.operation_id:
        print("Error: --operation-id is required for timeline")
        return

    timeline = analyzer.generate_operation_timeline(args.operation_id)

    if not timeline:
        print(f"No logs found for operation {args.operation_id}")
        return

    print(f"\n=== Timeline for Operation {args.operation_id} ===\n")

    for event in timeline:
        timestamp = event["timestamp"].replace("T", " ").split("+")[0]
        level = event["level"]
        message = event["message"]

        print(f"[{timestamp}] [{level}] {message}")
        print(f"  Location: {event['module']}:{event['function']}:{event['line']}")
        if "task_id" in event:
            print(f"  Task: {event['task_id']}")
        if "exception" in event:
            print(f"  Exception: {event['exception'][:100]}...")
        print()


def cmd_health(args):
    """Run health checks on system components."""
    from core.health_check import run_health_check

    report = run_health_check(verbose=args.verbose, auto_fix=args.fix)

    # Export to JSON if requested
    if args.export:
        import json

        with open(args.export, "w") as f:
            json.dump(report.to_dict(), f, indent=2)
        print(f"\nHealth report exported to {args.export}")

    # Exit with appropriate code
    import sys

    if report.overall_status.value == "critical":
        sys.exit(2)
    elif report.overall_status.value == "error":
        sys.exit(1)


def cmd_resume(args):
    """Resume a previous session."""
    from core.session_manager import SessionManager
    from data.checkpoint_manager import CheckpointManager

    session_mgr = SessionManager()
    checkpoint_mgr = CheckpointManager()

    session_id = args.session_id
    checkpoint_id = args.checkpoint_id

    # If no session ID provided, try to detect interrupted sessions
    if not session_id:
        interrupted = session_mgr.detect_interrupted_sessions()
        if not interrupted:
            print("No interrupted sessions found. Starting a new session...")
            cmd_start(args)
            return

        print("\nDetected interrupted sessions:")
        for i, session in enumerate(interrupted, 1):
            print(
                f"{i}. {session.session_id[:8]}... - {session.status.value} - "
                f"{session.start_time.strftime('%Y-%m-%d %H:%M:%S')}"
            )

        if args.auto:
            # Auto-resume the most recent interrupted session
            session = interrupted[0]
            session_id = session.session_id
            print(f"\nAuto-resuming most recent session: {session_id[:8]}...")
        else:
            # Ask user which session to resume
            choice = input(
                "\nSelect session to resume (number, or 'q' to quit): "
            ).strip()
            if choice.lower() == "q":
                print("Resume cancelled.")
                return

            try:
                index = int(choice) - 1
                if 0 <= index < len(interrupted):
                    session_id = interrupted[index].session_id
                else:
                    print("Invalid selection.")
                    return
            except ValueError:
                print("Invalid input.")
                return

    # Resume the session
    print(f"\nResuming session: {session_id[:8]}...")

    # Check for external changes
    session, has_external_changes = session_mgr.restore_session_on_startup(
        session_id, checkpoint_manager=checkpoint_mgr
    )

    if not session:
        print(f"Failed to resume session: {session_id}")
        print("Session may be corrupted or not found.")
        return

    if has_external_changes:
        print("\n⚠️  WARNING: External changes detected in the repository.")
        print("Your manual changes may conflict with the session state.")

        if not args.force:
            choice = input("\nProceed anyway? [y/N]: ").strip().lower()
            if choice != "y":
                print("Resume cancelled.")
                return

    print(f"\n✓ Session resumed successfully!")
    print(f"  Session ID: {session.session_id}")
    print(f"  Status: {session.status.value}")
    print(f"  Started: {session.start_time.strftime('%Y-%m-%d %H:%M:%S')}")

    if session.active_tasks:
        print(f"  Active tasks: {len(session.active_tasks)}")
    if session.checkpoint_id:
        print(f"  Last checkpoint: {session.checkpoint_id[:8]}...")

    # If a specific checkpoint was requested, restore it
    if checkpoint_id:
        print(f"\nRestoring from checkpoint: {checkpoint_id[:8]}...")
        success = checkpoint_mgr.restore(
            checkpoint_id, dry_run=args.dry_run, preserve_user_work=not args.force
        )

        if success:
            print(f"✓ Checkpoint restored successfully!")
        else:
            print(f"✗ Failed to restore checkpoint: {checkpoint_id}")
            return

    # If --start flag is set, start the orchestrator
    if args.start:
        print("\nStarting development loop...")
        cmd_start(args)


def cmd_checkpoints_list(args):
    """List available checkpoints."""
    from data.checkpoint_manager import CheckpointManager

    checkpoint_mgr = CheckpointManager()

    # List checkpoints with optional filters
    checkpoints = checkpoint_mgr.list(
        snapshot_type=args.type,
        task_id=args.task_id,
        operation_id=args.operation_id,
        limit=args.limit,
    )

    if not checkpoints:
        print("No checkpoints found.")
        return

    print(f"\nFound {len(checkpoints)} checkpoints:\n")

    for i, chkp in enumerate(checkpoints, 1):
        timestamp = chkp["timestamp"].replace("T", " ").split(".")[0]
        print(f"{i}. [{chkp['snapshot_type']}] {chkp['snapshot_id'][:16]}...")
        print(f"   Time: {timestamp}")
        print(f"   Reason: {chkp['reason']}")

        if chkp["task_id"]:
            print(f"   Task ID: {chkp['task_id']}")
        if chkp["operation_id"]:
            print(f"   Operation: {chkp['operation_id'][:16]}...")

        # Show metadata
        metadata = chkp.get("metadata", {})
        if metadata:
            included = []
            if metadata.get("include_databases"):
                included.append("databases")
            if metadata.get("include_files"):
                included.append("files")
            if metadata.get("include_git"):
                included.append("git")
            if metadata.get("include_cache"):
                included.append("cache")
            if included:
                print(f"   Includes: {', '.join(included)}")

        print()


def cmd_checkpoints_restore(args):
    """Restore from a specific checkpoint."""
    from data.checkpoint_manager import CheckpointManager

    checkpoint_mgr = CheckpointManager()

    checkpoint_id = args.id

    if not checkpoint_id:
        print("Error: --id is required for checkpoint restore")
        print("Use 'l4-dev checkpoints list' to see available checkpoints")
        return

    # Get checkpoint details
    checkpoint = checkpoint_mgr.get(checkpoint_id)
    if not checkpoint:
        print(f"Error: Checkpoint not found: {checkpoint_id}")
        return

    print(f"\nCheckpoint Details:")
    print(f"  ID: {checkpoint['snapshot_id']}")
    print(f"  Type: {checkpoint['snapshot_type']}")
    print(f"  Time: {checkpoint['timestamp']}")
    print(f"  Reason: {checkpoint['reason']}")

    if checkpoint["task_id"]:
        print(f"  Task ID: {checkpoint['task_id']}")
    if checkpoint["operation_id"]:
        print(f"  Operation: {checkpoint['operation_id']}")

    # Show what will be restored
    print(f"\nWill restore:")
    db_state = checkpoint.get("db_state", [])
    if db_state:
        print(f"  Databases: {len(db_state)} files")
    file_state = checkpoint.get("file_state", [])
    if file_state:
        print(f"  Files: {len(file_state)} files")
    git_state = checkpoint.get("git_state", [])
    if git_state:
        print(
            f"  Git state: branch={git_state[0].get('branch')}, commit={git_state[0].get('commit_hash')[:8]}..."
        )
    cache_state = checkpoint.get("cache_state", [])
    if cache_state:
        print(f"  Cache: {len(cache_state)} entries")

    # Warn about user work
    if not args.dry_run and not args.force:
        print(f"\n⚠️  WARNING: Restoring will overwrite current state.")
        print(f"Any uncommitted changes may be lost.")

        choice = input("\nProceed with restore? [y/N]: ").strip().lower()
        if choice != "y":
            print("Restore cancelled.")
            return

    # Perform restore
    print(f"\nRestoring from checkpoint: {checkpoint_id[:16]}...")

    success = checkpoint_mgr.restore(
        checkpoint_id,
        restore_databases=args.databases,
        restore_files=args.files,
        restore_git=args.git,
        restore_cache=args.cache,
        validate_before=args.validate,
        validate_after=args.validate,
        dry_run=args.dry_run,
        preserve_user_work=not args.force,
    )

    if success:
        print(f"✓ Checkpoint restored successfully!")
        if args.dry_run:
            print(f"  (This was a dry-run, no changes were made)")
    else:
        print(f"✗ Failed to restore checkpoint: {checkpoint_id}")
        return

    # If --start flag is set, start the orchestrator
    if args.start and not args.dry_run:
        print("\nStarting development loop...")
        cmd_start(args)


def cmd_checkpoints_delete(args):
    """Delete a specific checkpoint."""
    from data.checkpoint_manager import CheckpointManager

    checkpoint_mgr = CheckpointManager()

    checkpoint_id = args.id

    if not checkpoint_id:
        print("Error: --id is required for checkpoint delete")
        return

    # Get checkpoint details first
    checkpoint = checkpoint_mgr.get(checkpoint_id)
    if not checkpoint:
        print(f"Error: Checkpoint not found: {checkpoint_id}")
        return

    # Confirm deletion
    if not args.force:
        print(f"\nCheckpoint Details:")
        print(f"  ID: {checkpoint['snapshot_id']}")
        print(f"  Type: {checkpoint['snapshot_type']}")
        print(f"  Time: {checkpoint['timestamp']}")
        print(f"  Reason: {checkpoint['reason']}")

        choice = input(f"\nDelete this checkpoint? [y/N]: ").strip().lower()
        if choice != "y":
            print("Deletion cancelled.")
            return

    # Delete checkpoint
    success = checkpoint_mgr.delete(checkpoint_id)

    if success:
        print(f"✓ Checkpoint deleted successfully: {checkpoint_id[:16]}...")
    else:
        print(f"✗ Failed to delete checkpoint: {checkpoint_id}")


def cmd_sessions_list(args):
    """List available sessions."""
    from core.session_manager import SessionManager

    session_mgr = SessionManager()

    # List sessions with optional filter
    from core.session_manager import SessionStatus

    status_filter = None
    if args.status:
        try:
            status_filter = SessionStatus(args.status)
        except ValueError:
            print(f"Invalid status: {args.status}")
            print(f"Valid statuses: {', '.join([s.value for s in SessionStatus])}")
            return

    sessions = session_mgr.list_sessions(status=status_filter, limit=args.limit)

    if not sessions:
        print("No sessions found.")
        return

    print(f"\nFound {len(sessions)} sessions:\n")

    for i, session in enumerate(sessions, 1):
        status_icon = (
            "🟢"
            if session.status == SessionStatus.ACTIVE
            else (
                "🟡"
                if session.status == SessionStatus.PAUSED
                else (
                    "🔵"
                    if session.status == SessionStatus.COMPLETED
                    else "📦" if session.status == SessionStatus.ARCHIVED else "❌"
                )
            )
        )

        print(f"{i}. {status_icon} {session.session_id[:8]}...")
        print(f"   Status: {session.status.value}")
        print(f"   Start: {session.start_time.strftime('%Y-%m-%d %H:%M:%S')}")

        if session.end_time:
            print(f"   End: {session.end_time.strftime('%Y-%m-%d %H:%M:%S')}")

        if session.active_tasks:
            print(f"   Active tasks: {len(session.active_tasks)}")
        if session.active_operations:
            print(f"   Active operations: {len(session.active_operations)}")
        if session.checkpoint_id:
            print(f"   Last checkpoint: {session.checkpoint_id[:8]}...")

        print()


def cmd_telemetry_list(args):
    """List and query telemetry operations."""
    from data.telemetry_manager import get_telemetry_manager
    from datetime import datetime, timedelta

    telemetry_mgr = get_telemetry_manager()

    # Parse time range if provided
    start_time = None
    end_time = None

    if args.last:
        try:
            hours = int(args.last.rstrip("h"))
            start_time = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
        except ValueError:
            print(f"Invalid time range: {args.last}")
            return

    if args.start:
        try:
            start_time = args.start
        except ValueError:
            print(f"Invalid start time format: {args.start}")
            return

    if args.end:
        try:
            end_time = args.end
        except ValueError:
            print(f"Invalid end time format: {args.end}")
            return

    # Query operations
    operations = telemetry_mgr.query_operations(
        operation_type=args.type,
        status=args.status,
        start_time=start_time,
        end_time=end_time,
        limit=args.limit,
    )

    if not operations:
        print("No matching operations found.")
        return

    # Display results
    print(f"\nFound {len(operations)} matching operations:\n")

    for i, op in enumerate(operations, 1):
        op_id = op.get("id", "N/A")[:16]
        op_type = op.get("operation_type", "N/A")
        title = op.get("title", "N/A")
        status = op.get("status", "N/A")
        start = op.get("start_time", "N/A").replace("T", " ").split(".")[0]

        # Format status with emoji
        status_emoji = {
            "started": "🔄",
            "completed": "✅",
            "failed": "❌",
            "interrupted": "⚠️",
            "cancelled": "🚫",
        }.get(status, "")

        print(f"{i}. {status_emoji} [{op_type}] {title}")
        print(f"   ID: {op_id}...")
        print(f"   Status: {status}")
        print(f"   Started: {start}")

        # Show task ID if available
        metadata = op.get("metadata", {})
        if isinstance(metadata, dict) and "task_id" in metadata:
            print(f"   Task ID: {metadata['task_id']}")
            if "task_title" in metadata:
                print(f"   Task: {metadata['task_title']}")

        # Show end time if available
        if op.get("end_time"):
            end = op["end_time"].replace("T", " ").split(".")[0]
            print(f"   Ended: {end}")

        print()

    # Export if requested
    if args.export:
        cmd_telemetry_export_from_ops(operations, args.export, args.format)


def cmd_telemetry_show(args):
    """Show detailed telemetry for an operation."""
    from data.telemetry_manager import get_telemetry_manager

    if not args.id:
        print("Error: --id is required to show operation details")
        return

    telemetry_mgr = get_telemetry_manager()

    # Get operation details
    operation = telemetry_mgr.get_operation(args.id)
    if not operation:
        print(f"Error: Operation not found: {args.id}")
        return

    print("\n" + "=" * 60)
    print("Operation Details")
    print("=" * 60)
    print(f"\nID: {operation.get('id')}")
    print(f"Type: {operation.get('operation_type')}")
    print(f"Title: {operation.get('title')}")
    print(f"Status: {operation.get('status')}")
    print(f"Started: {operation.get('start_time')}")

    if operation.get("end_time"):
        print(f"Ended: {operation.get('end_time')}")

        # Calculate duration
        try:
            from datetime import datetime

            start = datetime.fromisoformat(
                operation["start_time"].replace("Z", "+00:00")
            )
            end = datetime.fromisoformat(operation["end_time"].replace("Z", "+00:00"))
            duration = (end - start).total_seconds()
            print(f"Duration: {duration:.2f} seconds")
        except:
            pass

    if operation.get("parent_id"):
        print(f"Parent: {operation['parent_id'][:16]}...")

    # Show metadata
    metadata = operation.get("metadata")
    if metadata:
        print(f"\nMetadata:")
        for key, value in metadata.items():
            if key not in ["task_id", "task_title"]:  # Already shown
                print(f"  {key}: {value}")

    # Show events
    print(f"\n{'='*60}")
    print("Events")
    print("=" * 60)
    events = telemetry_mgr.get_operation_events(args.id)
    if events:
        for event in events:
            timestamp = event["timestamp"].replace("T", " ").split(".")[0]
            severity = event["severity"]
            event_type = event["event_type"]
            message = event["message"]

            severity_emoji = {
                "info": "ℹ️",
                "warning": "⚠️",
                "error": "❌",
                "critical": "🔴",
            }.get(severity, "")

            print(f"\n[{timestamp}] {severity_emoji} [{event_type}] {message}")
            if event.get("context"):
                print(f"  Context: {event['context']}")
    else:
        print("No events recorded.")

    # Show metrics
    print(f"\n{'='*60}")
    print("Metrics")
    print("=" * 60)
    metrics = telemetry_mgr.get_operation_metrics(args.id)
    if metrics:
        # Group metrics by name
        metric_groups = {}
        for metric in metrics:
            name = metric["metric_name"]
            if name not in metric_groups:
                metric_groups[name] = []
            metric_groups[name].append(metric)

        for metric_name, metric_list in metric_groups.items():
            values = [m["metric_value"] for m in metric_list]
            unit = metric_list[0].get("unit", "")
            avg = sum(values) / len(values)

            print(f"\n{metric_name}:")
            print(f"  Count: {len(values)}")
            print(f"  Average: {avg:.2f} {unit}")
            print(f"  Min: {min(values):.2f} {unit}")
            print(f"  Max: {max(values):.2f} {unit}")
    else:
        print("No metrics recorded.")

    # Show resources
    print(f"\n{'='*60}")
    print("Resources")
    print("=" * 60)
    resources = telemetry_mgr.get_operation_resources(args.id)
    if resources:
        for resource in resources:
            timestamp = resource["timestamp"].replace("T", " ").split(".")[0]
            rtype = resource["resource_type"]
            name = resource.get("resource_name", "")
            value = resource["value"]
            unit = resource["unit"]

            print(f"\n[{timestamp}] {rtype} {name}: {value} {unit}")
    else:
        print("No resource usage recorded.")

    # Show logs
    if args.logs:
        print(f"\n{'='*60}")
        print("Logs")
        print("=" * 60)
        logs = telemetry_mgr.get_operation_logs(args.id)
        if logs:
            for log in logs:
                timestamp = log["timestamp"].replace("T", " ").split(".")[0]
                level = log["log_level"]
                logger = log.get("logger_name", "")
                message = log["message"]

                print(f"\n[{timestamp}] [{level}] {logger}: {message}")
                if log.get("log_data"):
                    print(f"  Data: {log['log_data']}")
        else:
            print("No logs recorded.")


def cmd_telemetry_export(args):
    """Export telemetry data to file."""
    from data.telemetry_manager import get_telemetry_manager

    telemetry_mgr = get_telemetry_manager()

    if not args.id:
        print("Error: --id is required for export")
        return

    # Get operation with logs
    result = telemetry_mgr.export_operation_with_logs(args.id, format="dict")

    if "error" in result:
        print(f"Error: {result['error']}")
        return

    # Export based on format
    if args.format == "json":
        import json

        with open(args.export, "w") as f:
            json.dump(result, f, indent=2, default=str)
        print(f"✓ Telemetry exported to {args.export}")

    elif args.format == "csv":
        import csv

        with open(args.export, "w", newline="") as f:
            writer = csv.writer(f)

            # Write operation summary
            writer.writerow(["Type", "Field", "Value"])
            operation = result.get("operation", {})
            writer.writerow(["Operation", "ID", operation.get("id")])
            writer.writerow(["Operation", "Type", operation.get("operation_type")])
            writer.writerow(["Operation", "Title", operation.get("title")])
            writer.writerow(["Operation", "Status", operation.get("status")])
            writer.writerow(["Operation", "Start", operation.get("start_time")])
            writer.writerow(["Operation", "End", operation.get("end_time")])
            writer.writerow([])

            # Write events
            writer.writerow(["Events"])
            writer.writerow(["Timestamp", "Type", "Severity", "Message"])
            for event in result.get("events", []):
                writer.writerow(
                    [
                        event.get("timestamp"),
                        event.get("event_type"),
                        event.get("severity"),
                        event.get("message"),
                    ]
                )
            writer.writerow([])

            # Write metrics
            writer.writerow(["Metrics"])
            writer.writerow(["Timestamp", "Name", "Value", "Unit"])
            for metric in result.get("metrics", []):
                writer.writerow(
                    [
                        metric.get("timestamp"),
                        metric.get("metric_name"),
                        metric.get("metric_value"),
                        metric.get("unit"),
                    ]
                )
            writer.writerow([])

            # Write resources
            writer.writerow(["Resources"])
            writer.writerow(["Timestamp", "Type", "Name", "Value", "Unit"])
            for resource in result.get("resources", []):
                writer.writerow(
                    [
                        resource.get("timestamp"),
                        resource.get("resource_type"),
                        resource.get("resource_name"),
                        resource.get("value"),
                        resource.get("unit"),
                    ]
                )
            writer.writerow([])

            # Write logs
            writer.writerow(["Logs"])
            writer.writerow(["Timestamp", "Level", "Logger", "Message"])
            for log in result.get("logs", []):
                writer.writerow(
                    [
                        log.get("timestamp"),
                        log.get("log_level"),
                        log.get("logger_name"),
                        log.get("message"),
                    ]
                )

        print(f"✓ Telemetry exported to {args.export}")

    else:
        print(f"Unsupported export format: {args.format}")


def cmd_telemetry_export_from_ops(operations, export_path, format="json"):
    """Helper function to export list of operations."""
    if format == "json":
        import json

        with open(export_path, "w") as f:
            json.dump(operations, f, indent=2, default=str)
        print(f"\n✓ Operations exported to {export_path}")

    elif format == "csv":
        import csv

        with open(export_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["ID", "Type", "Title", "Status", "Start Time", "End Time"])
            for op in operations:
                writer.writerow(
                    [
                        op.get("id"),
                        op.get("operation_type"),
                        op.get("title"),
                        op.get("status"),
                        op.get("start_time"),
                        op.get("end_time"),
                    ]
                )
        print(f"\n✓ Operations exported to {export_path}")

    else:
        print(f"\nUnsupported export format: {format}")


def cmd_telemetry_stats(args):
    """Show telemetry statistics."""
    from data.telemetry_manager import get_telemetry_manager

    telemetry_mgr = get_telemetry_manager()

    # Get statistics
    stats = telemetry_mgr.get_operation_stats(operation_type=args.type)

    print("\n" + "=" * 60)
    print("Telemetry Statistics")
    print("=" * 60)

    if args.type:
        print(f"\nOperation Type: {args.type}")

    print(f"\nTotal Operations: {stats.get('count', 0)}")

    if stats.get("avg_duration_seconds", 0) > 0:
        print(f"Average Duration: {stats['avg_duration_seconds']:.2f} seconds")

    print(f"Success Rate: {stats.get('success_rate_percent', 0):.1f}%")

    # Status breakdown
    breakdown = stats.get("status_breakdown", {})
    if breakdown:
        print(f"\nStatus Breakdown:")
        for status, count in breakdown.items():
            emoji = {
                "started": "🔄",
                "completed": "✅",
                "failed": "❌",
                "interrupted": "⚠️",
                "cancelled": "🚫",
            }.get(status, "")
            print(f"  {emoji} {status}: {count}")

    # Get statistics by operation type if not filtering
    if not args.type:
        print(f"\n{'='*60}")
        print("Statistics by Operation Type")
        print("=" * 60)

        all_ops = telemetry_mgr.list_operations(limit=10000)
        type_counts = {}

        for op in all_ops:
            op_type = op.get("operation_type", "unknown")
            if op_type not in type_counts:
                type_counts[op_type] = {"total": 0, "completed": 0, "failed": 0}
            type_counts[op_type]["total"] += 1
            status = op.get("status")
            if status == "completed":
                type_counts[op_type]["completed"] += 1
            elif status == "failed":
                type_counts[op_type]["failed"] += 1

        for op_type, counts in sorted(type_counts.items()):
            total = counts["total"]
            completed = counts["completed"]
            failed = counts["failed"]
            success_rate = (completed / total * 100) if total > 0 else 0
            print(f"\n{op_type}:")
            print(f"  Total: {total}")
            print(f"  Completed: {completed} ({success_rate:.1f}%)")
            print(f"  Failed: {failed}")


def cmd_decisions(args):
    """Query and search decision history."""
    from data.decision_tracer import get_decision_tracer
    from data.decision_history import get_decision_history
    from datetime import datetime, timedelta

    tracer = get_decision_tracer()
    history_mgr = get_decision_history()

    # Parse time range if provided
    start_time = None
    end_time = None

    if args.last:
        try:
            hours = int(args.last.rstrip("h"))
            start_time = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
        except ValueError:
            print(f"Invalid time range: {args.last}")
            return

    if args.start:
        try:
            start_time = args.start
        except ValueError:
            print(f"Invalid start time format: {args.start}")
            return

    if args.end:
        try:
            end_time = args.end
        except ValueError:
            print(f"Invalid end time format: {args.end}")
            return

    # Search decisions
    decisions = tracer.search(
        task_id=args.task_id,
        operation_id=args.operation_id,
        start_time=start_time,
        end_time=end_time,
        min_confidence=args.min_confidence,
        max_confidence=args.max_confidence,
        action_pattern=args.action,
        limit=args.limit
    )

    # If no filters applied, use decision history for broader search
    if not decisions and not args.task_id and not args.operation_id:
        decisions = history_mgr.list_decisions(
            task_id=args.task_id,
            operation_id=args.operation_id,
            outcome=args.outcome,
            min_confidence=args.min_confidence,
            max_confidence=args.max_confidence,
            limit=args.limit
        )

    # Additional search methods
    if args.context_key and args.context_value:
        context_results = tracer.search_context(
            context_key=args.context_key,
            context_value=args.context_value,
            limit=args.limit
        )
        # Merge results
        seen_ids = {d.get('decision_id') for d in decisions}
        for ctx_dec in context_results:
            if ctx_dec.get('decision_id') not in seen_ids:
                decisions.append(ctx_dec)

    if args.reasoning:
        reasoning_results = tracer.search_reasoning(
            reasoning_keyword=args.reasoning,
            limit=args.limit
        )
        # Merge results
        seen_ids = {d.get('decision_id') for d in decisions}
        for res_dec in reasoning_results:
            if res_dec.get('decision_id') not in seen_ids:
                decisions.append(res_dec)

    # Filter by outcome if specified
    if args.outcome:
        decisions = [d for d in decisions if d.get('outcome') == args.outcome]

    if not decisions:
        print("No matching decisions found.")
        return

    # Display results
    print(f"\nFound {len(decisions)} matching decisions:\n")

    for i, decision in enumerate(decisions, 1):
        decision_id = decision.get('decision_id', 'N/A')[:16]
        action = decision.get('selected_action') or decision.get('action', 'N/A')
        timestamp = decision.get('timestamp', 'N/A').replace('T', ' ').split('.')[0][:19]
        confidence = decision.get('confidence', 0.0)
        outcome = decision.get('outcome', 'N/A')

        # Format status with emoji
        outcome_emoji = {
            'success': '✅',
            'failure': '❌',
            'unknown': '❓'
        }.get(outcome, '')

        print(f"{i}. [{decision_id}...] {action}")
        print(f"   Timestamp: {timestamp}")
        print(f"   Confidence: {confidence:.2f}")
        print(f"   Outcome: {outcome_emoji} {outcome}")

        # Show task/operation IDs
        if decision.get('task_id'):
            print(f"   Task ID: {decision['task_id']}")
        if decision.get('operation_id'):
            print(f"   Operation: {decision['operation_id'][:16]}...")

        # Show reasoning keyword match
        if args.reasoning and decision.get('reasoning_chain'):
            reasoning_chain = decision['reasoning_chain']
            if reasoning_chain:
                first_step = reasoning_chain[0]
                thought = first_step.get('thought', '')[:100]
                print(f"   Reasoning: {thought}...")

        print()

    # Export if requested
    if args.export:
        if args.export.endswith('.json'):
            tracer.export_traces(decisions, format='json', file_path=args.export)
        elif args.export.endswith('.csv'):
            tracer.export_traces(decisions, format='csv', file_path=args.export)
        else:
            print(f"Unsupported export format: {args.export}")

    # Show statistics if requested
    if args.stats:
        stats = tracer.get_statistics()
        print("\n" + "=" * 60)
        print("Decision Statistics")
        print("=" * 60)
        print(f"Total Decisions: {stats['total_decisions']}")
        print(f"Average Confidence: {stats['average_confidence']:.2f}")
        print(f"\nConfidence Distribution:")
        print(f"  High (>=0.9): {stats['confidence_distribution']['high']}")
        print(f"  Medium (0.7-0.9): {stats['confidence_distribution']['medium']}")
        print(f"  Low (<0.7): {stats['confidence_distribution']['low']}")
        print(f"\nTop 10 Tasks by Decision Count:")
        for task in stats['top_tasks']:
            print(f"  Task {task['task_id']}: {task['decisions']} decisions")


def cmd_profile_list(args):
    """List all available configuration profiles."""
    from core.config import get_config

    try:
        config_manager = None
        # Try to get existing config manager
        try:
            from core.config import _config_manager
            if _config_manager is not None:
                config_manager = _config_manager
        except:
            pass

        if config_manager is None:
            from core.config import ConfigManager
            config_manager = ConfigManager()

        profiles = config_manager.list_profiles()

        if not profiles:
            print("No profiles found.")
            return

        print(f"\nFound {len(profiles)} configuration profiles:\n")

        for profile in profiles:
            name = profile["name"]
            description = profile.get("description", "")
            inherits = profile.get("inherits")

            print(f"📋 {name}")
            print(f"   Description: {description}")
            if inherits:
                print(f"   Inherits: {inherits}")
            print()

        # Show current profile
        try:
            config = get_config()
            print(f"Current profile: {config.profile}")
        except:
            pass

    except Exception as e:
        print(f"Error listing profiles: {e}")


def cmd_profile_show(args):
    """Show details of a specific profile."""
    from core.config import ConfigManager

    config_manager = ConfigManager()

    if not args.profile:
        print("Error: --profile is required to show profile details")
        print("Use 'l4-dev profile list' to see available profiles")
        return

    try:
        # Get profile with inheritance
        profile_config = config_manager.get_profile_with_inheritance(args.profile)

        print(f"\nProfile: {args.profile}\n")
        print("=" * 60)

        def print_config_section(config_dict: Dict[str, Any], section_name: str) -> None:
            """Print a configuration section."""
            if section_name in config_dict:
                section = config_dict[section_name]
                print(f"\n[{section_name}]")
                for key, value in section.items():
                    print(f"  {key}: {value}")

        # Print all sections
        print_config_section(profile_config, "llm")
        print_config_section(profile_config, "cache")
        print_config_section(profile_config, "logging")
        print_config_section(profile_config, "telemetry")
        print_config_section(profile_config, "checkpoint")
        print_config_section(profile_config, "session")
        print_config_section(profile_config, "custom")

        print("\n" + "=" * 60)

    except ValueError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"Error showing profile: {e}")


def cmd_profile_use(args):
    """Switch to a different configuration profile."""
    from core.config import ConfigManager

    config_manager = ConfigManager()

    if not args.profile:
        print("Error: --profile is required to switch profiles")
        print("Use 'l4-dev profile list' to see available profiles")
        return

    try:
        print(f"\nSwitching to profile: {args.profile}")

        # Switch profile
        new_config = config_manager.switch_profile(args.profile)

        print(f"✓ Successfully switched to profile '{args.profile}'")
        print(f"  Configuration saved to .l4_config")

        # Show summary
        print(f"\nProfile Summary:")
        print(f"  LLM Model: {new_config.llm.model}")
        print(f"  Cache Size: {new_config.cache.max_size_mb}MB")
        print(f"  Logging Level: {new_config.logging.level}")

        custom_settings = new_config.custom
        if custom_settings:
            print(f"  Adaptive Reasoning: {custom_settings.get('adaptive_reasoning', False)}")
            print(f"  Progress Tracking: {custom_settings.get('progress_tracking', False)}")
            print(f"  Trap Detection: {custom_settings.get('trap_detection', False)}")

        print()

    except ValueError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"Error switching profile: {e}")


def cmd_profile_diff(args):
    """Compare two configuration profiles."""
    from core.config import ConfigManager

    config_manager = ConfigManager()

    if not args.profile1 or not args.profile2:
        print("Error: --profile1 and --profile2 are required to compare profiles")
        print("Usage: l4-dev profile diff --profile1 <name> --profile2 <name>")
        return

    try:
        comparison = config_manager.compare_profiles(args.profile1, args.profile2)

        print(f"\nComparing profiles: {args.profile1} vs {args.profile2}\n")
        print("=" * 60)

        # Show summary
        summary = comparison["summary"]
        print(f"\nSummary:")
        print(f"  Total Differences: {summary['total']}")
        print(f"  Added in {args.profile2}: {summary['added']}")
        print(f"  Removed from {args.profile2}: {summary['removed']}")
        print(f"  Changed: {summary['changed']}")

        # Show detailed differences
        if comparison["differences"]:
            print(f"\nDetailed Differences:\n")

            # Group differences by type
            by_type = {}
            for diff in comparison["differences"]:
                diff_type = diff["type"]
                if diff_type not in by_type:
                    by_type[diff_type] = []
                by_type[diff_type].append(diff)

            # Print each type
            for diff_type in ["added", "removed", "changed"]:
                if diff_type in by_type:
                    diff_list = by_type[diff_type]
                    emoji = "➕" if diff_type == "added" else ("➖" if diff_type == "removed" else "🔄")
                    print(f"{emoji} {diff_type.title()} ({len(diff_list)}):")

                    for diff in diff_list:
                        key = diff["key"]
                        v1 = diff.get("profile1")
                        v2 = diff.get("profile2")

                        if diff_type == "changed":
                            print(f"  {key}:")
                            print(f"    {args.profile1}: {v1}")
                            print(f"    {args.profile2}: {v2}")
                        else:
                            print(f"  {key}: {v2}")
                    print()

        else:
            print("\nNo differences found. Profiles are identical.")

        print("=" * 60 + "\n")

    except ValueError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"Error comparing profiles: {e}")


def cmd_explain(args):
    """Display decision explanation and visualization."""
    from core.ui import create_decision_visualizer
    from data.decision_tracer import get_decision_tracer
    from data.decision_history import get_decision_history

    visualizer = create_decision_visualizer()
    tracer = get_decision_tracer()
    history_mgr = get_decision_history()

    # Decision tree visualization
    if args.tree:
        decisions = []
        
        if args.last:
            # Get last N decisions
            all_decisions = history_mgr.list_decisions(limit=args.last)
            decisions.extend(all_decisions)
        elif args.operation_id:
            # Get decisions for specific operation
            all_decisions = history_mgr.list_decisions(operation_id=args.operation_id)
            decisions.extend(all_decisions)
        elif args.task_id:
            # Get decisions for specific task
            all_decisions = history_mgr.list_decisions(task_id=args.task_id)
            decisions.extend(all_decisions)
        else:
            # Get recent decisions
            all_decisions = history_mgr.list_decisions(limit=50)
            decisions.extend(all_decisions)
        
        # Add parent-child relationships
        for decision in decisions:
            # Get dependencies
            decision_id = decision.get("decision_id")
            dependencies = history_mgr.get_decision_graph(decision_id)
            
            # Set parent_id from dependencies
            upstream = dependencies.get("upstream", [])
            if upstream:
                decision["parent_id"] = upstream[0].get("decision_id")
            else:
                decision["parent_id"] = None
        
        visualizer.display_decision_tree(
            decisions,
            max_depth=args.max_depth,
            show_confidence=args.confidence,
            show_alternatives=args.alternatives
        )

    # Reasoning chain visualization
    elif args.reasoning and args.id:
        decision = history_mgr.get_decision(args.id)
        if decision:
            visualizer.display_reasoning_chain(
                decision,
                show_steps=True,
                show_context=args.context
            )
        else:
            print(f"Decision not found: {args.id}")

    # Key decisions visualization
    elif args.key:
        decisions = history_mgr.list_decisions(limit=100)
        
        if args.operation_id:
            decisions = [d for d in decisions if d.get("operation_id") == args.operation_id]
        elif args.task_id:
            decisions = [d for d in decisions if d.get("task_id") == args.task_id]
        
        visualizer.display_key_decisions(
            decisions,
            confidence_threshold=args.confidence_threshold,
            limit=args.limit
        )

    # Decision heatmap
    elif args.heatmap:
        decisions = history_mgr.list_decisions(limit=200)
        
        if args.operation_id:
            decisions = [d for d in decisions if d.get("operation_id") == args.operation_id]
        elif args.task_id:
            decisions = [d for d in decisions if d.get("task_id") == args.task_id]
        
        visualizer.display_decision_heatmap(
            decisions,
            metric=args.metric
        )

    # Default: show last decision explanation
    elif args.last:
        decisions = history_mgr.list_decisions(limit=1)
        if decisions:
            decision = decisions[0]
            print(f"\n{'='*60}")
            print(f"LAST DECISION EXPLANATION")
            print("=" * 60)
            print(f"Decision ID: {decision.get('decision_id', 'N/A')}")
            print(f"Action: {decision.get('action', 'N/A')}")
            print(f"Timestamp: {decision.get('timestamp', 'N/A')}")
            print(f"Confidence: {decision.get('confidence', 0.0):.2f}")
            print(f"Outcome: {decision.get('outcome', 'N/A')}")
            
            # Show reasoning if available
            reasoning_chain = decision.get('reasoning_chain', [])
            if reasoning_chain:
                print(f"\nReasoning Chain:")
                for step in reasoning_chain[:5]:  # Show first 5 steps
                    thought = step.get('thought', '')
                    conclusion = step.get('conclusion', '')
                    print(f"  Step {step.get('step', '?')}: {thought}")
                    if conclusion:
                        print(f"    Conclusion: {conclusion}")
            
            # Show alternatives if available
            alternatives = decision.get('alternatives', [])
            if alternatives:
                print(f"\nAlternatives Considered:")
                for alt in alternatives[:5]:
                    alt_action = alt.get('action', 'N/A')
                    alt_reason = alt.get('reason_for_rejection', '')
                    print(f"  • {alt_action}")
                    if alt_reason:
                        print(f"    Rejected: {alt_reason}")
            
            print("=" * 60 + "\n")
        else:
            print("No decisions found.")
    
    # Export decisions
    if args.export:
        decisions = history_mgr.list_decisions(limit=1000)
        
        if args.operation_id:
            decisions = [d for d in decisions if d.get("operation_id") == args.operation_id]
        elif args.task_id:
            decisions = [d for d in decisions if d.get("task_id") == args.task_id]
        
        visualizer.export_visualization(
            decisions,
            export_path=args.export,
            format=args.format
        )


def cmd_progress(args):
    """Display progress visualization."""
    from core.ui import create_progress_visualizer
    from core.session_manager import SessionManager
    from data.telemetry_manager import get_telemetry_manager
    from logic.progress_tracker import ProgressTracker

    visualizer = create_progress_visualizer()

    # Task progress
    if args.task:
        from data.db_manager import TASK_DB_PATH
        import sqlite3

        if os.path.exists(TASK_DB_PATH):
            conn = sqlite3.connect(TASK_DB_PATH)
            cursor = conn.cursor()
            
            if args.task_id:
                # Get specific task
                cursor.execute(
                    "SELECT id, title, status FROM tasks WHERE id = ?",
                    (args.task_id,)
                )
                task = cursor.fetchone()
                if task:
                    # Get progress from progress tracker if available
                    task_id, title, status = task
                    progress = 50.0 if status == "in_progress" else 100.0 if status == "completed" else 0.0
                    
                    metrics = {}
                    try:
                        # Try to get metrics from telemetry
                        telemetry_mgr = get_telemetry_manager()
                        ops = telemetry_mgr.query_operations(
                            status="completed",
                            task_id=args.task_id,
                            limit=10
                        )
                        if ops:
                            metrics = {
                                "lines_added": sum(
                                    op.get("metrics", {}).get("lines_added", 0)
                                    for op in ops
                                ),
                                "tests_passing": sum(
                                    op.get("metrics", {}).get("tests_passing", 0)
                                    for op in ops
                                ),
                                "tests_total": sum(
                                    op.get("metrics", {}).get("tests_total", 0)
                                    for op in ops
                                )
                            }
                    except:
                        pass

                    # Check for stagnation and regression
                    stagnation = None
                    regression = False

                    try:
                        telemetry_mgr = get_telemetry_manager()
                        recent_ops = telemetry_mgr.query_operations(
                            status="in_progress",
                            task_id=args.task_id,
                            limit=10
                        )
                        
                        # Check for stagnation (multiple operations without progress)
                        if recent_ops and len(recent_ops) > 3:
                            stagnation = "warning"
                        
                        # Check for regression (would need historical comparison)
                        # For now, simplified check
                        if status == "failed":
                            regression = True
                    except:
                        pass

                    # Predict completion time
                    predicted_completion = None
                    try:
                        telemetry_mgr = get_telemetry_manager()
                        ops = telemetry_mgr.query_operations(
                            task_id=args.task_id,
                            limit=10
                        )
                        if ops and len(ops) >= 2:
                            # Simple linear prediction
                            durations = []
                            for op in ops:
                                if op.get("start_time") and op.get("end_time"):
                                    try:
                                        start = datetime.fromisoformat(op["start_time"])
                                        end = datetime.fromisoformat(op["end_time"])
                                        durations.append((end - start).total_seconds())
                                    except:
                                        pass
                            if durations:
                                avg_duration = sum(durations) / len(durations)
                                predicted_completion = avg_duration
                    except:
                        pass

                    visualizer.display_task_progress(
                        task_id=str(task_id),
                        progress=progress,
                        metrics=metrics if metrics else None,
                        predicted_completion=predicted_completion,
                        stagnation=stagnation,
                        regression=regression
                    )
                else:
                    print(f"Task not found: {args.task_id}")
            else:
                # Show recent tasks
                cursor.execute(
                    "SELECT id, title, status FROM tasks ORDER BY id DESC LIMIT 10"
                )
                tasks = cursor.fetchall()
                
                if args.session:
                    # Show session-level progress
                    completed = len([t for t in tasks if t[2] == "completed"])
                    failed = len([t for t in tasks if t[2] == "failed"])
                    
                    session_metrics = {
                        "tasks_completed": completed,
                        "tasks_failed": failed,
                        "operations_per_hour": (completed + failed) / 2.0  # Simplified
                    }
                    
                    visualizer.display_session_progress(session_metrics)
                elif args.project:
                    # Show project-level progress
                    total = len(tasks)
                    completed = len([t for t in tasks if t[2] == "completed"])
                    
                    project_metrics = {
                        "features_total": total,
                        "features_completed": completed,
                        "overall_code_coverage": 85.0,  # Placeholder
                        "bug_rate": 5.0,  # Placeholder
                        "health_score": (completed / total * 100) if total > 0 else 100.0
                    }
                    
                    visualizer.display_project_progress(project_metrics)
                else:
                    # List tasks
                    print("\n" + "=" * 60)
                    print("RECENT TASKS")
                    print("=" * 60 + "\n")
                    for task in tasks:
                        task_id, title, status = task
                        status_icon = {
                            "completed": "✅",
                            "in_progress": "🔄",
                            "pending": "⏳",
                            "failed": "❌"
                        }.get(status, "❓")
                        print(f"{status_icon} [{task_id}] {title} - {status}")
                    print()
            
            conn.close()
        else:
            print("Task database not found. Run 'l4-dev init' first.")

    # Session progress
    elif args.session:
        try:
            session_mgr = SessionManager()
            sessions = session_mgr.list_sessions(limit=1)
            
            if sessions:
                session = sessions[0]
                session_metrics = {
                    "tasks_completed": session.get("tasks_completed", 0),
                    "tasks_failed": 0,  # Would need to track this
                    "errors_encountered": 0,  # Would need to track this
                    "errors_resolved": 0,  # Would need to track this
                    "operations_per_hour": 2.0,  # Placeholder
                    "total_lines_written": 0,  # Would need to track this
                    "total_tests_added": 0  # Would need to track this
                }
                
                visualizer.display_session_progress(session_metrics)
            else:
                print("No active session found.")
        except Exception as e:
            print(f"Error loading session progress: {e}")

    # Project progress
    elif args.project:
        from data.db_manager import TASK_DB_PATH
        import sqlite3

        if os.path.exists(TASK_DB_PATH):
            conn = sqlite3.connect(TASK_DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM tasks")
            total_tasks = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = 'completed'")
            completed_tasks = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = 'failed'")
            failed_tasks = cursor.fetchone()[0]
            
            conn.close()
            
            project_metrics = {
                "features_total": total_tasks,
                "features_completed": completed_tasks,
                "issues_total": failed_tasks,
                "issues_resolved": 0,  # Would need to track this
                "milestones_total": 5,  # Placeholder
                "milestones_completed": 2,  # Placeholder
                "overall_code_coverage": 85.0,  # Placeholder
                "bug_rate": 5.0,  # Placeholder
                "health_score": (completed_tasks / total_tasks * 100) if total_tasks > 0 else 100.0
            }
            
            visualizer.display_project_progress(project_metrics)
        else:
            print("Task database not found. Run 'l4-dev init' first.")

    # Show alerts
    if args.alerts:
        try:
            telemetry_mgr = get_telemetry_manager()
            # Get recent errors as alerts
            recent_errors = telemetry_mgr.query_operations(
                status="failed",
                limit=10
            )
            
            if recent_errors:
                alerts = []
                for op in recent_errors:
                    alerts.append({
                        "timestamp": op.get("start_time", ""),
                        "severity": "error",
                        "type": "operation_failed",
                        "message": f"{op.get('operation_type')}: {op.get('title', 'Unknown error')}"
                    })
                
                visualizer.display_alerts(alerts)
            else:
                print("No recent alerts.")
        except Exception as e:
            print(f"Error loading alerts: {e}")


def cmd_report_generate(args):
    """Generate analytics reports."""
    from data.telemetry_manager import get_telemetry_manager
    from data.db_manager import get_cost_summary
    from datetime import datetime, timedelta
    import json

    telemetry_mgr = get_telemetry_manager()

    # Determine time range
    if args.period == "day":
        start_time = (datetime.utcnow() - timedelta(days=1)).isoformat()
        period_label = "Last 24 Hours"
    elif args.period == "week":
        start_time = (datetime.utcnow() - timedelta(days=7)).isoformat()
        period_label = "Last 7 Days"
    elif args.period == "month":
        start_time = (datetime.utcnow() - timedelta(days=30)).isoformat()
        period_label = "Last 30 Days"
    else:
        start_time = None
        period_label = "All Time"

    print("\n" + "=" * 60)
    print("L4D Analytics Report")
    print("=" * 60)
    print(f"\nPeriod: {period_label}")
    print(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}")

    # Operation Statistics
    print(f"\n{'='*60}")
    print("Operation Statistics")
    print("=" * 60)

    ops = telemetry_mgr.query_operations(start_time=start_time, limit=10000)
    print(f"\nTotal Operations: {len(ops)}")

    if ops:
        # Group by type
        type_counts = {}
        status_counts = {}

        for op in ops:
            op_type = op.get("operation_type", "unknown")
            status = op.get("status", "unknown")

            if op_type not in type_counts:
                type_counts[op_type] = 0
            type_counts[op_type] += 1

            if status not in status_counts:
                status_counts[status] = 0
            status_counts[status] += 1

        print(f"\nBy Operation Type:")
        for op_type, count in sorted(
            type_counts.items(), key=lambda x: x[1], reverse=True
        ):
            print(f"  {op_type}: {count} ({count/len(ops)*100:.1f}%)")

        print(f"\nBy Status:")
        for status, count in sorted(
            status_counts.items(), key=lambda x: x[1], reverse=True
        ):
            emoji = {
                "started": "🔄",
                "completed": "✅",
                "failed": "❌",
                "interrupted": "⚠️",
                "cancelled": "🚫",
            }.get(status, "")
            print(f"  {emoji} {status}: {count} ({count/len(ops)*100:.1f}%)")

        # Calculate success rate
        success_count = status_counts.get("completed", 0)
        success_rate = (success_count / len(ops) * 100) if len(ops) > 0 else 0
        print(f"\nSuccess Rate: {success_rate:.1f}%")

    # Cost Summary
    print(f"\n{'='*60}")
    print("Cost Summary")
    print("=" * 60)

    total_tokens, total_cost = get_cost_summary()
    print(f"\nTotal Tokens Used: {total_tokens:,}")
    print(f"Total Estimated Cost: ${total_cost:.4f}")

    # Resource Usage
    print(f"\n{'='*60}")
    print("Resource Usage Summary")
    print("=" * 60)

    # Get recent resource usage
    try:
        import psutil

        cpu = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage(".")

        print(f"\nCurrent System Resources:")
        print(f"  CPU Usage: {cpu}%")
        print(
            f"  Memory: {memory.used / (1024**3):.2f} GB / {memory.total / (1024**3):.2f} GB"
        )
        print(f"  Memory Usage: {memory.percent}%")
        print(
            f"  Disk: {disk.used / (1024**3):.2f} GB / {disk.total / (1024**3):.2f} GB"
        )
        print(f"  Disk Usage: {disk.percent}%")
    except ImportError:
        print("\n(psutil not available for resource monitoring)")

    # Error Analysis
    print(f"\n{'='*60}")
    print("Error Analysis")
    print("=" * 60)

    failed_ops = [op for op in ops if op.get("status") == "failed"]
    if failed_ops:
        print(
            f"\nFailed Operations: {len(failed_ops)} ({len(failed_ops)/len(ops)*100:.1f}%)"
        )

        # Analyze failure patterns
        failure_types = {}
        for op in failed_ops:
            metadata = op.get("metadata", {})
            error_type = metadata.get("error_type", "unknown")
            if error_type not in failure_types:
                failure_types[error_type] = 0
            failure_types[error_type] += 1

        if failure_types:
            print(f"\nFailure Types:")
            for error_type, count in sorted(
                failure_types.items(), key=lambda x: x[1], reverse=True
            ):
                print(f"  {error_type}: {count}")
    else:
        print("\nNo failed operations in this period.")

    # Log Statistics
    print(f"\n{'='*60}")
    print("Log Statistics")
    print("=" * 60)

    log_stats = telemetry_mgr.get_log_statistics(start_time=start_time)
    print(f"\nTotal Logs: {log_stats.get('total_logs', 0)}")
    print(f"Errors: {log_stats.get('error_count', 0)}")
    print(f"Warnings: {log_stats.get('warning_count', 0)}")
    print(f"Critical: {log_stats.get('critical_count', 0)}")

    # Export if requested
    if args.export:
        report_data = {
            "period": period_label,
            "generated_at": datetime.utcnow().isoformat(),
            "operation_statistics": {
                "total_operations": len(ops),
                "by_type": type_counts if ops else {},
                "by_status": status_counts if ops else {},
                "success_rate": success_rate if ops else 0,
            },
            "cost_summary": {"total_tokens": total_tokens, "total_cost": total_cost},
            "error_analysis": {
                "failed_count": len(failed_ops),
                "failure_types": failure_types,
            },
            "log_statistics": log_stats,
        }

        with open(args.export, "w") as f:
            json.dump(report_data, f, indent=2, default=str)
        print(f"\n✓ Report exported to {args.export}")

    print("\n" + "=" * 60)
    print("Report Complete")
    print("=" * 60 + "\n")


def cmd_recover(args):
    """Interactive recovery wizard."""
    from core.session_manager import SessionManager
    from data.checkpoint_manager import CheckpointManager

    session_mgr = SessionManager()
    checkpoint_mgr = CheckpointManager()

    print("\n" + "=" * 60)
    print("L4D Recovery Wizard")
    print("=" * 60)

    # Step 1: Detect interrupted sessions
    print("\n[1/4] Detecting interrupted sessions...")
    interrupted = session_mgr.detect_interrupted_sessions()

    if interrupted:
        print(f"Found {len(interrupted)} interrupted session(s):\n")
        for i, session in enumerate(interrupted, 1):
            print(f"{i}. {session.session_id[:8]}... - {session.status.value}")
            print(f"   Started: {session.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            if session.active_tasks:
                print(f"   Tasks: {len(session.active_tasks)}")
            print()
    else:
        print("No interrupted sessions found.")
        print("You can start a new session with: l4-dev start")
        return

    # Step 2: Select session to recover
    print("Select a session to recover:")
    print("[1-{}] Resume from session".format(len(interrupted)))
    print("[c]   Choose a specific checkpoint")
    print("[q]   Quit")

    choice = input("\nYour choice: ").strip().lower()

    if choice == "q":
        print("Recovery cancelled.")
        return

    session_id = None
    checkpoint_id = None

    if choice.isdigit():
        index = int(choice) - 1
        if 0 <= index < len(interrupted):
            session_id = interrupted[index].session_id
        else:
            print("Invalid selection.")
            return
    elif choice == "c":
        # Step 3: Select checkpoint
        print("\n[2/4] Loading available checkpoints...")
        checkpoints = checkpoint_mgr.list(limit=50)

        if not checkpoints:
            print("No checkpoints found.")
            return

        print(f"\nFound {len(checkpoints)} checkpoint(s):\n")
        for i, chkp in enumerate(checkpoints, 1):
            timestamp = chkp["timestamp"].replace("T", " ").split(".")[0]
            print(f"{i}. [{chkp['snapshot_type']}] {chkp['snapshot_id'][:16]}...")
            print(f"   Time: {timestamp}")
            print(f"   Reason: {chkp['reason']}")
            print()

        print(f"Select a checkpoint (1-{len(checkpoints)}) or 'q' to go back:")
        choice = input("\nYour choice: ").strip().lower()

        if choice == "q":
            print("Going back...")
            return cmd_recover(args)

        try:
            index = int(choice) - 1
            if 0 <= index < len(checkpoints):
                checkpoint_id = checkpoints[index]["snapshot_id"]
            else:
                print("Invalid selection.")
                return
        except ValueError:
            print("Invalid input.")
            return
    else:
        print("Invalid choice.")
        return

    # Step 4: Review and confirm
    print("\n[3/4] Review recovery plan:")

    if session_id:
        session = session_mgr._load_session(session_id)
        if session:
            print(f"\nSession: {session.session_id[:8]}...")
            print(f"  Status: {session.status.value}")
            print(f"  Started: {session.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            if session.checkpoint_id:
                print(f"  Checkpoint: {session.checkpoint_id[:8]}...")

    if checkpoint_id:
        checkpoint = checkpoint_mgr.get(checkpoint_id)
        if checkpoint:
            print(f"\nCheckpoint: {checkpoint['snapshot_id'][:16]}...")
            print(f"  Type: {checkpoint['snapshot_type']}")
            print(f"  Time: {checkpoint['timestamp']}")
            print(f"  Reason: {checkpoint['reason']}")

    # Check for external changes
    print("\n[4/4] Checking for external changes...")
    has_external = session_mgr._check_external_changes()

    if has_external:
        print("⚠️  WARNING: External changes detected!")
        print("You have uncommitted changes in the repository.")
        print("Recovering may overwrite your work.")

    # Confirm
    print("\n" + "-" * 60)
    if args.dry_run:
        print("DRY RUN MODE: No changes will be made")
    print("-" * 60)

    choice = input("\nProceed with recovery? [y/N]: ").strip().lower()
    if choice != "y":
        print("Recovery cancelled.")
        return

    # Perform recovery
    print("\nRecovering...")

    if checkpoint_id:
        success = checkpoint_mgr.restore(
            checkpoint_id, dry_run=args.dry_run, preserve_user_work=True
        )
        if success:
            print(f"✓ Checkpoint restored successfully!")
        else:
            print(f"✗ Failed to restore checkpoint")
            return
    elif session_id:
        session, has_ext = session_mgr.restore_session_on_startup(
            session_id, checkpoint_manager=checkpoint_mgr
        )
        if session:
            print(f"✓ Session restored successfully!")
            if has_ext:
                print("⚠️  External changes were detected - review carefully")
        else:
            print(f"✗ Failed to restore session")
            return

    # Offer to start orchestrator
    if not args.dry_run:
        choice = input("\nStart development loop? [y/N]: ").strip().lower()
        if choice == "y":
            print("\nStarting development loop...")
            cmd_start(args)

    print("\n✓ Recovery complete!")


def main():
    parser = argparse.ArgumentParser(
        description="L4 Self-Evolving Development Platform CLI"
    )
    parser.add_argument(
        "--project_root", help="Path to the project folder to develop", default="."
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Helper to add common arguments to subparsers without overwriting top-level defaults
    def add_common_args(sub_p):
        sub_p.add_argument(
            "--project_root",
            help="Path to the project folder to develop",
            default=argparse.SUPPRESS,
        )

    # Start command
    start_p = subparsers.add_parser("start", help="Initiate orchestration loop")
    add_common_args(start_p)

    # Status command
    status_p = subparsers.add_parser(
        "status", help="Show comprehensive status dashboard"
    )
    status_p.add_argument(
        "-v", "--verbose", action="store_true", help="Show detailed information"
    )
    status_p.add_argument("--watch", action="store_true", help="Auto-refresh dashboard")
    status_p.add_argument(
        "--interval",
        type=int,
        default=5,
        help="Refresh interval in seconds (default: 5)",
    )
    status_p.add_argument(
        "--iterations", type=int, help="Maximum number of refreshes (default: infinite)"
    )
    add_common_args(status_p)

    # Retro command
    retro_p = subparsers.add_parser(
        "retro", help="Trigger a retrospective on manual changes"
    )
    add_common_args(retro_p)

    # Doctor command
    doctor_p = subparsers.add_parser(
        "doctor", help="Verify environment and dependencies"
    )
    add_common_args(doctor_p)

    # Init command
    init_p = subparsers.add_parser("init", help="Initialize project root")
    add_common_args(init_p)

    # Reset command
    reset_p = subparsers.add_parser("reset", help="Reset all databases")
    add_common_args(reset_p)

    # Logs command
    logs_p = subparsers.add_parser("logs", help="Search and analyze logs")
    logs_p.add_argument(
        "--level", help="Filter by log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )
    logs_p.add_argument("--module", help="Filter by module name (supports wildcards)")
    logs_p.add_argument("--operation-id", help="Filter by operation ID")
    logs_p.add_argument("--task-id", type=int, help="Filter by task ID")
    logs_p.add_argument("--session-id", help="Filter by session ID")
    logs_p.add_argument(
        "--search", help="Full-text search query (supports AND, OR, NOT)"
    )
    logs_p.add_argument("--last", help="Time range (e.g., 1h, 24h)")
    logs_p.add_argument("--error", action="store_true", help="Only show error entries")
    logs_p.add_argument("--export", help="Export to file (CSV or JSON)")
    logs_p.add_argument("--log-dir", default="v2/logs", help="Log directory")

    # Logs summary command
    logs_summary_p = subparsers.add_parser(
        "logs-summary", help="Generate log summary statistics"
    )
    logs_summary_p.add_argument("--level", help="Filter by log level")
    logs_summary_p.add_argument("--module", help="Filter by module name")
    logs_summary_p.add_argument("--operation-id", help="Filter by operation ID")
    logs_summary_p.add_argument("--task-id", type=int, help="Filter by task ID")
    logs_summary_p.add_argument("--log-dir", default="v2/logs", help="Log directory")

    # Logs errors command
    logs_errors_p = subparsers.add_parser("logs-errors", help="Show error patterns")
    logs_errors_p.add_argument("--log-dir", default="v2/logs", help="Log directory")

    # Logs timeline command
    logs_timeline_p = subparsers.add_parser(
        "logs-timeline", help="Generate operation timeline"
    )
    logs_timeline_p.add_argument(
        "--operation-id", required=True, help="Operation ID to generate timeline for"
    )
    logs_timeline_p.add_argument("--log-dir", default="v2/logs", help="Log directory")

    # Health command
    health_p = subparsers.add_parser(
        "health", help="Run health checks on system components"
    )
    health_p.add_argument(
        "-v", "--verbose", action="store_true", help="Show detailed output"
    )
    health_p.add_argument("--fix", action="store_true", help="Auto-fix fixable issues")
    health_p.add_argument("--export", help="Export health report to JSON file")

    # Resume command
    resume_p = subparsers.add_parser("resume", help="Resume a previous session")
    resume_p.add_argument("--session-id", help="Specific session ID to resume")
    resume_p.add_argument("--checkpoint-id", help="Restore from specific checkpoint")
    resume_p.add_argument(
        "--auto",
        action="store_true",
        help="Auto-resume most recent interrupted session",
    )
    resume_p.add_argument(
        "--force", action="store_true", help="Force resume even with external changes"
    )
    resume_p.add_argument(
        "--dry-run", action="store_true", help="Preview resume without making changes"
    )
    resume_p.add_argument(
        "--start", action="store_true", help="Start orchestrator after resume"
    )
    add_common_args(resume_p)

    # Checkpoints subcommand group
    checkpoints_p = subparsers.add_parser(
        "checkpoints", help="Manage system checkpoints"
    )
    checkpoints_subparsers = checkpoints_p.add_subparsers(
        dest="checkpoints_command", help="Checkpoint commands"
    )

    # Checkpoints list command
    checkpoints_list_p = checkpoints_subparsers.add_parser(
        "list", help="List available checkpoints"
    )
    checkpoints_list_p.add_argument("--type", help="Filter by snapshot type")
    checkpoints_list_p.add_argument("--task-id", type=int, help="Filter by task ID")
    checkpoints_list_p.add_argument("--operation-id", help="Filter by operation ID")
    checkpoints_list_p.add_argument(
        "--limit", type=int, default=50, help="Maximum number to show (default: 50)"
    )
    add_common_args(checkpoints_list_p)

    # Checkpoints restore command
    checkpoints_restore_p = checkpoints_subparsers.add_parser(
        "restore", help="Restore from a checkpoint"
    )
    checkpoints_restore_p.add_argument(
        "--id", required=True, help="Checkpoint ID to restore"
    )
    checkpoints_restore_p.add_argument(
        "--databases", action="store_true", help="Restore database state"
    )
    checkpoints_restore_p.add_argument(
        "--files", action="store_true", help="Restore file system state"
    )
    checkpoints_restore_p.add_argument(
        "--git", action="store_true", help="Restore git state"
    )
    checkpoints_restore_p.add_argument(
        "--cache", action="store_true", help="Restore cache state"
    )
    checkpoints_restore_p.add_argument(
        "--no-validate",
        dest="validate",
        action="store_false",
        default=True,
        help="Skip validation",
    )
    checkpoints_restore_p.add_argument(
        "--dry-run", action="store_true", help="Preview restore without making changes"
    )
    checkpoints_restore_p.add_argument(
        "--force", action="store_true", help="Force restore without confirmation"
    )
    checkpoints_restore_p.add_argument(
        "--start", action="store_true", help="Start orchestrator after restore"
    )
    add_common_args(checkpoints_restore_p)

    # Checkpoints delete command
    checkpoints_delete_p = checkpoints_subparsers.add_parser(
        "delete", help="Delete a checkpoint"
    )
    checkpoints_delete_p.add_argument(
        "--id", required=True, help="Checkpoint ID to delete"
    )
    checkpoints_delete_p.add_argument(
        "--force", action="store_true", help="Delete without confirmation"
    )
    add_common_args(checkpoints_delete_p)

    # Sessions list command
    sessions_list_p = subparsers.add_parser("sessions", help="List available sessions")
    sessions_list_p.add_argument(
        "--status",
        help="Filter by session status (active, paused, completed, archived)",
    )
    sessions_list_p.add_argument(
        "--limit", type=int, default=50, help="Maximum number to show (default: 50)"
    )
    add_common_args(sessions_list_p)

    # Recover command (interactive wizard)
    recover_p = subparsers.add_parser("recover", help="Interactive recovery wizard")
    recover_p.add_argument(
        "--dry-run", action="store_true", help="Preview recovery without making changes"
    )
    add_common_args(recover_p)

    # Telemetry subcommand group
    telemetry_p = subparsers.add_parser(
        "telemetry", help="Query and analyze telemetry data"
    )
    telemetry_subparsers = telemetry_p.add_subparsers(
        dest="telemetry_command", help="Telemetry commands"
    )

    # Telemetry list command
    telemetry_list_p = telemetry_subparsers.add_parser(
        "list", help="List and query operations"
    )
    telemetry_list_p.add_argument(
        "--type", help="Filter by operation type (e.g., implementation, task_breakdown)"
    )
    telemetry_list_p.add_argument(
        "--status",
        help="Filter by status (started, completed, failed, interrupted, cancelled)",
    )
    telemetry_list_p.add_argument("--start", help="Start time (ISO format)")
    telemetry_list_p.add_argument("--end", help="End time (ISO format)")
    telemetry_list_p.add_argument("--last", help="Time range (e.g., 1h, 24h, 7d)")
    telemetry_list_p.add_argument(
        "--limit", type=int, default=50, help="Maximum number to show (default: 50)"
    )
    telemetry_list_p.add_argument("--export", help="Export to file (JSON or CSV)")
    telemetry_list_p.add_argument(
        "--format", choices=["json", "csv"], default="json", help="Export format"
    )

    # Telemetry show command
    telemetry_show_p = telemetry_subparsers.add_parser(
        "show", help="Show detailed operation telemetry"
    )
    telemetry_show_p.add_argument("--id", required=True, help="Operation ID to show")
    telemetry_show_p.add_argument(
        "--logs", action="store_true", help="Include associated logs"
    )

    # Telemetry export command
    telemetry_export_p = telemetry_subparsers.add_parser(
        "export", help="Export operation telemetry to file"
    )
    telemetry_export_p.add_argument(
        "--id", required=True, help="Operation ID to export"
    )
    telemetry_export_p.add_argument("--export", required=True, help="Output file path")
    telemetry_export_p.add_argument(
        "--format", choices=["json", "csv"], default="json", help="Export format"
    )

    # Telemetry stats command
    telemetry_stats_p = telemetry_subparsers.add_parser(
        "stats", help="Show telemetry statistics"
    )
    telemetry_stats_p.add_argument("--type", help="Filter by operation type")

    # Report command
    report_p = subparsers.add_parser("report", help="Generate analytics reports")
    report_p.add_argument(
        "--period",
        choices=["day", "week", "month", "all"],
        default="all",
        help="Report period (default: all)",
    )
    report_p.add_argument("--export", help="Export report to JSON file")

    # Progress command (V4)
    progress_p = subparsers.add_parser("progress", help="Display progress visualization")
    progress_p.add_argument(
        "--task", action="store_true", help="Show task progress"
    )
    progress_p.add_argument(
        "--task-id", type=int, help="Show progress for specific task ID"
    )
    progress_p.add_argument(
        "--session", action="store_true", help="Show session progress"
    )
    progress_p.add_argument(
        "--project", action="store_true", help="Show project progress"
    )
    progress_p.add_argument(
        "--alerts", action="store_true", help="Show progress alerts"
    )
    add_common_args(progress_p)

    # Decisions command (V4 - Decision Query)
    decisions_p = subparsers.add_parser("decisions", help="Query and search decision history")
    decisions_p.add_argument(
        "--task-id", type=int, help="Filter by task ID"
    )
    decisions_p.add_argument(
        "--operation-id", help="Filter by operation ID"
    )
    decisions_p.add_argument(
        "--start", help="Start time (ISO format)"
    )
    decisions_p.add_argument(
        "--end", help="End time (ISO format)"
    )
    decisions_p.add_argument(
        "--last", help="Time range (e.g., 1h, 24h)"
    )
    decisions_p.add_argument(
        "--min-confidence", type=float, help="Minimum confidence threshold"
    )
    decisions_p.add_argument(
        "--max-confidence", type=float, help="Maximum confidence threshold"
    )
    decisions_p.add_argument(
        "--action", help="Filter by action pattern"
    )
    decisions_p.add_argument(
        "--outcome", choices=["success", "failure"], help="Filter by outcome"
    )
    decisions_p.add_argument(
        "--context-key", help="Search by context key"
    )
    decisions_p.add_argument(
        "--context-value", help="Search by context value"
    )
    decisions_p.add_argument(
        "--reasoning", help="Search reasoning by keyword"
    )
    decisions_p.add_argument(
        "--limit", type=int, default=50, help="Maximum number to show (default: 50)"
    )
    decisions_p.add_argument(
        "--export", help="Export to file (CSV or JSON)"
    )
    decisions_p.add_argument(
        "--stats", action="store_true", help="Show decision statistics"
    )
    add_common_args(decisions_p)

    # Profile command (V5 - Configuration Profiles)
    profile_p = subparsers.add_parser("profile", help="Manage configuration profiles")
    profile_subparsers = profile_p.add_subparsers(
        dest="profile_command", help="Profile commands"
    )

    # Profile list command
    profile_list_p = profile_subparsers.add_parser(
        "list", help="List all available profiles"
    )
    add_common_args(profile_list_p)

    # Profile show command
    profile_show_p = profile_subparsers.add_parser(
        "show", help="Show details of a specific profile"
    )
    profile_show_p.add_argument(
        "--profile", required=True, help="Profile name to show"
    )
    add_common_args(profile_show_p)

    # Profile use command
    profile_use_p = profile_subparsers.add_parser(
        "use", help="Switch to a different profile"
    )
    profile_use_p.add_argument(
        "--profile", required=True, help="Profile name to switch to"
    )
    add_common_args(profile_use_p)

    # Profile diff command
    profile_diff_p = profile_subparsers.add_parser(
        "diff", help="Compare two configuration profiles"
    )
    profile_diff_p.add_argument(
        "--profile1", required=True, help="First profile to compare"
    )
    profile_diff_p.add_argument(
        "--profile2", required=True, help="Second profile to compare"
    )
    add_common_args(profile_diff_p)

    # Explain command (V4 - Decision Visualization)
    explain_p = subparsers.add_parser("explain", help="Explain and visualize decisions")
    explain_p.add_argument(
        "--id", help="Decision ID to explain"
    )
    explain_p.add_argument(
        "--last", type=int, help="Show last N decisions (default: show last decision with details)"
    )
    explain_p.add_argument(
        "--tree", action="store_true", help="Display decision tree visualization"
    )
    explain_p.add_argument(
        "--reasoning", action="store_true", help="Display reasoning chain for a decision"
    )
    explain_p.add_argument(
        "--key", action="store_true", help="Display key decisions"
    )
    explain_p.add_argument(
        "--heatmap", action="store_true", help="Display decision heatmap"
    )
    explain_p.add_argument(
        "--operation-id", help="Filter by operation ID"
    )
    explain_p.add_argument(
        "--task-id", type=int, help="Filter by task ID"
    )
    explain_p.add_argument(
        "--max-depth", type=int, default=5, help="Maximum depth for decision tree (default: 5)"
    )
    explain_p.add_argument(
        "--confidence-threshold", type=float, default=0.7, help="Minimum confidence for key decisions (default: 0.7)"
    )
    explain_p.add_argument(
        "--limit", type=int, default=10, help="Maximum decisions to display (default: 10)"
    )
    explain_p.add_argument(
        "--confidence", action="store_true", help="Show confidence scores"
    )
    explain_p.add_argument(
        "--alternatives", action="store_true", help="Show considered alternatives"
    )
    explain_p.add_argument(
        "--context", action="store_true", help="Show context in reasoning steps"
    )
    explain_p.add_argument(
        "--metric", choices=["confidence", "time", "tokens"], default="confidence", help="Metric for heatmap (default: confidence)"
    )
    explain_p.add_argument(
        "--export", help="Export decisions to file"
    )
    explain_p.add_argument(
        "--format", choices=["json", "pdf", "png"], default="json", help="Export format (default: json)"
    )
    add_common_args(explain_p)

    args = parser.parse_args()

    # Change CWD to project root
    project_root = os.path.abspath(args.project_root)
    if not os.path.exists(project_root):
        print(f"Project root '{project_root}' does not exist. Creating it...")
        os.makedirs(project_root, exist_ok=True)

    os.chdir(project_root)

    if args.command == "start":
        cmd_start(args)
    elif args.command == "status":
        cmd_status(args)
    elif args.command == "retro":
        cmd_retro(args)
    elif args.command == "doctor":
        cmd_doctor(args)
    elif args.command == "init":
        cmd_init(args)
    elif args.command == "reset":
        cmd_reset(args)
    elif args.command == "logs":
        cmd_logs(args)
    elif args.command == "logs-summary":
        cmd_logs_summary(args)
    elif args.command == "logs-errors":
        cmd_logs_errors(args)
    elif args.command == "logs-timeline":
        cmd_logs_timeline(args)
    elif args.command == "health":
        cmd_health(args)
    elif args.command == "resume":
        cmd_resume(args)
    elif args.command == "checkpoints":
        if args.checkpoints_command == "list":
            cmd_checkpoints_list(args)
        elif args.checkpoints_command == "restore":
            cmd_checkpoints_restore(args)
        elif args.checkpoints_command == "delete":
            cmd_checkpoints_delete(args)
        else:
            print("Please specify a checkpoints command: list, restore, delete")
    elif args.command == "sessions":
        cmd_sessions_list(args)
    elif args.command == "recover":
        cmd_recover(args)
    elif args.command == "telemetry":
        if args.telemetry_command == "list":
            cmd_telemetry_list(args)
        elif args.telemetry_command == "show":
            cmd_telemetry_show(args)
        elif args.telemetry_command == "export":
            cmd_telemetry_export(args)
        elif args.telemetry_command == "stats":
            cmd_telemetry_stats(args)
        else:
            print("Please specify a telemetry command: list, show, export, stats")
    elif args.command == "report":
        cmd_report_generate(args)
    elif args.command == "progress":
        cmd_progress(args)
    elif args.command == "decisions":
        cmd_decisions(args)
    elif args.command == "profile":
        if args.profile_command == "list":
            cmd_profile_list(args)
        elif args.profile_command == "show":
            cmd_profile_show(args)
        elif args.profile_command == "use":
            cmd_profile_use(args)
        elif args.profile_command == "diff":
            cmd_profile_diff(args)
        else:
            print("Please specify a profile command: list, show, use, diff")
    elif args.command == "explain":
        cmd_explain(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
