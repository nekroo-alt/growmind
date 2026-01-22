import sys
import os
import sqlite3
import argparse
from datetime import datetime, timedelta

# Get__name__ absolute path of the L4 root (parent of v1)
# __file__ is /Users/ken/Desktop/growmind/v1/l4_cli.py
# L4_ROOT is /Users/ken/Desktop/growmind
L4_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Ensure L4_ROOT is in sys.path so that 'import v1' works even after chdir
if L4_ROOT not in sys.path:
    sys.path.insert(0, L4_ROOT)

from v2.core.start import Orchestrator
from v2.data.db_manager import TASK_DB_PATH, ACTIVITY_DB_PATH, init_db, get_cost_summary
from v2.retro.retro_agent import RetroAgent
from v2.core.log_analyzer import LogAnalyzer, LogQuery


def cmd_start(args):
    orchestrator = Orchestrator()
    orchestrator.run()


def cmd_status(args):
    from v2.core.ui import create_status_dashboard
    from v2.core.health_check import run_health_check
    from v2.core.session_manager import SessionManager
    from v2.data.cache_manager import CacheManager
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
                latest_session = sorted(active_sessions, key=lambda s: s.get('start_time', ''), reverse=True)[0]
                session_info = {
                    'id': latest_session.get('id'),
                    'status': latest_session.get('status'),
                    'start_time': latest_session.get('start_time'),
                    'tasks_completed': latest_session.get('tasks_completed', 0)
                }
        except Exception:
            pass  # Session manager might not be initialized yet
        
        # Gather active operation information
        active_operation = None
        try:
            from v2.data.telemetry_manager import TelemetryManager
            telemetry_mgr = TelemetryManager()
            in_progress_ops = telemetry_mgr.query_operations(status='in_progress', limit=1)
            if in_progress_ops:
                op = in_progress_ops[0]
                active_operation = {
                    'operation_type': op.get('operation_type'),
                    'status': op.get('status'),
                    'task_id': op.get('task_id'),
                    'task_title': op.get('task_title'),
                    'progress': {
                        'completed': op.get('completed', 0),
                        'total': op.get('total', 100),
                        'percentage': op.get('percentage', 0)
                    }
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
                recent_activities.append({
                    'timestamp': row[0],
                    'action_type': row[1],
                    'status': row[2],
                    'summary': row[3],
                    'tokens_used': row[4] if row[4] else 0,
                    'estimated_cost': row[5] if row[5] else 0.0
                })
        
        # Gather health report
        health_report = None
        try:
            report = run_health_check(verbose=False, auto_fix=False)
            health_report = {
                'overall_status': report.overall_status.value,
                'checks': {}
            }
            for check_name, check_result in report.checks.items():
                health_report['checks'][check_name] = {
                    'status': check_result.status.value,
                    'details': check_result.details if hasattr(check_result, 'details') else {}
                }
        except Exception:
            pass
        
        # Gather resource usage
        resource_usage = {}
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=0.1)
            resource_usage['cpu'] = cpu_percent
            
            # Memory usage
            memory = psutil.virtual_memory()
            resource_usage['memory'] = memory.used / (1024 ** 3)  # Convert to GB
            
            # Cache information
            try:
                cache_mgr = CacheManager()
                stats = cache_mgr.get_stats()
                resource_usage['cache_size'] = stats.get('total_size_mb', 0)
                resource_usage['cache_hit_rate'] = stats.get('hit_rate', 0) * 100
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
            verbose=args.verbose
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
                verbose=args.verbose
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
        from v2.core.doctor import run_doctor

        run_doctor()
    except ImportError:
        print("Error: rich library required for doctor. Please install it.")
        # Fallback to basic check if rich is missing (though we checked and it's there)
        print(f"Python Version: {sys.version}")
        print(f"Task DB: {'[OK]' if os.path.exists(TASK_DB_PATH) else '[MISSING]'}")


def cmd_init(args):
    from v2.core.init import run_init

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
        has_error=args.error
    )
    
    # Parse time range if provided
    if args.last:
        try:
            hours = int(args.last.rstrip('h'))
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
        timestamp = entry.timestamp.strftime("%Y-%m-%d %H:%M:%S") if entry.timestamp else "N/A"
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
        if args.export.endswith('.csv'):
            analyzer.export_to_csv(query, args.export)
        elif args.export.endswith('.json'):
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
            task_id=args.task_id
        )
    
    summary = analyzer.generate_summary(query)
    
    print("\n=== Log Summary ===\n")
    print(f"Total Entries: {summary['total_entries']}")
    print(f"Error Count: {summary['error_count']}")
    
    if summary['time_range']['start']:
        print(f"\nTime Range:")
        print(f"  Start: {summary['time_range']['start']}")
        print(f"  End: {summary['time_range']['end']}")
    
    print(f"\nBy Level:")
    for level, count in summary['by_level'].items():
        print(f"  {level}: {count}")
    
    print(f"\nTop 10 Modules:")
    for module, count in summary['by_module'].items():
        print(f"  {module}: {count}")
    
    if summary['by_operation']:
        print(f"\nTop 10 Operations:")
        for op_id, count in summary['by_operation'].items():
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
        if pattern['first_occurrence']:
            print(f"First: {pattern['first_occurrence']}")
        if pattern['last_occurrence']:
            print(f"Last: {pattern['last_occurrence']}")
        print("\nMessage Patterns:")
        for msg_pattern, count in pattern['message_patterns'].items():
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
        timestamp = event['timestamp'].replace('T', ' ').split('+')[0]
        level = event['level']
        message = event['message']
        
        print(f"[{timestamp}] [{level}] {message}")
        print(f"  Location: {event['module']}:{event['function']}:{event['line']}")
        if 'task_id' in event:
            print(f"  Task: {event['task_id']}")
        if 'exception' in event:
            print(f"  Exception: {event['exception'][:100]}...")
        print()


def cmd_health(args):
    """Run health checks on system components."""
    from v2.core.health_check import run_health_check
    
    report = run_health_check(verbose=args.verbose, auto_fix=args.fix)
    
    # Export to JSON if requested
    if args.export:
        import json
        with open(args.export, 'w') as f:
            json.dump(report.to_dict(), f, indent=2)
        print(f"\nHealth report exported to {args.export}")
    
    # Exit with appropriate code
    import sys
    if report.overall_status.value == "critical":
        sys.exit(2)
    elif report.overall_status.value == "error":
        sys.exit(1)


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
    status_p = subparsers.add_parser("status", help="Show comprehensive status dashboard")
    status_p.add_argument("-v", "--verbose", action="store_true", help="Show detailed information")
    status_p.add_argument("--watch", action="store_true", help="Auto-refresh dashboard")
    status_p.add_argument("--interval", type=int, default=5, help="Refresh interval in seconds (default: 5)")
    status_p.add_argument("--iterations", type=int, help="Maximum number of refreshes (default: infinite)")
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
    logs_p.add_argument("--level", help="Filter by log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)")
    logs_p.add_argument("--module", help="Filter by module name (supports wildcards)")
    logs_p.add_argument("--operation-id", help="Filter by operation ID")
    logs_p.add_argument("--task-id", type=int, help="Filter by task ID")
    logs_p.add_argument("--session-id", help="Filter by session ID")
    logs_p.add_argument("--search", help="Full-text search query (supports AND, OR, NOT)")
    logs_p.add_argument("--last", help="Time range (e.g., 1h, 24h)")
    logs_p.add_argument("--error", action="store_true", help="Only show error entries")
    logs_p.add_argument("--export", help="Export to file (CSV or JSON)")
    logs_p.add_argument("--log-dir", default="v2/logs", help="Log directory")

    # Logs summary command
    logs_summary_p = subparsers.add_parser("logs-summary", help="Generate log summary statistics")
    logs_summary_p.add_argument("--level", help="Filter by log level")
    logs_summary_p.add_argument("--module", help="Filter by module name")
    logs_summary_p.add_argument("--operation-id", help="Filter by operation ID")
    logs_summary_p.add_argument("--task-id", type=int, help="Filter by task ID")
    logs_summary_p.add_argument("--log-dir", default="v2/logs", help="Log directory")

    # Logs errors command
    logs_errors_p = subparsers.add_parser("logs-errors", help="Show error patterns")
    logs_errors_p.add_argument("--log-dir", default="v2/logs", help="Log directory")

    # Logs timeline command
    logs_timeline_p = subparsers.add_parser("logs-timeline", help="Generate operation timeline")
    logs_timeline_p.add_argument("--operation-id", required=True, help="Operation ID to generate timeline for")
    logs_timeline_p.add_argument("--log-dir", default="v2/logs", help="Log directory")

    # Health command
    health_p = subparsers.add_parser("health", help="Run health checks on system components")
    health_p.add_argument("-v", "--verbose", action="store_true", help="Show detailed output")
    health_p.add_argument("--fix", action="store_true", help="Auto-fix fixable issues")
    health_p.add_argument("--export", help="Export health report to JSON file")

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
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
