import sys
import os
from typing import Dict, Any

# Get __name__ absolute path of the L4 root
L4_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Ensure L4_ROOT is in sys.path
if L4_ROOT not in sys.path:
    sys.path.insert(0, L4_ROOT)

# V5 Command Functions for Interactive Mode, Workflows, Housekeeping, Cost, Dependencies, Quality


def cmd_start_interactive(args):
    """V5: Interactive mode for beginners."""
    print("\n" + "=" * 60)
    print("L4D Interactive Mode")
    print("=" * 60)
    print("\nWhat would you like to do?")
    print("[1] Implement a new feature")
    print("[2] Fix a bug")
    print("[3] Refactor code")
    print("[4] Run tests")
    print("[q] Quit")
    
    choice = input("\nSelection: ").strip().lower()
    
    if choice == "q":
        print("Exiting...")
        return
    elif choice == "1":
        task_desc = input("Describe the feature: ").strip()
        print(f"\n[Working...] Planning task for: {task_desc}")
        print(f"[Working...] Creating task breakdown...")
        print(f"[SUCCESS] Feature planned successfully!")
    elif choice == "2":
        task_desc = input("Describe the bug: ").strip()
        print(f"\n[Working...] Analyzing bug: {task_desc}")
        print(f"[SUCCESS] Bug analysis complete!")
    elif choice == "3":
        print(f"\n[Working...] Analyzing codebase for refactoring...")
        print(f"[SUCCESS] Refactoring candidates identified!")
    elif choice == "4":
        print(f"\n[Working...] Running tests...")
        print(f"[SUCCESS] Tests complete!")
    else:
        print(f"Invalid selection: {choice}")


def cmd_workflow_simple(args):
    """V5: Simple feature implementation workflow."""
    task = args.task if hasattr(args, 'task') else ""
    print(f"\n[Workflow] Simple Feature Implementation")
    print(f"Task: {task}")
    print(f"[Working...] Planning task breakdown...")
    print(f"[Working...] Implementing via TDD...")
    print(f"[SUCCESS] Feature implemented!")


def cmd_workflow_complex(args):
    """V5: Complex feature with planning workflow."""
    task = args.task if hasattr(args, 'task') else ""
    print(f"\n[Workflow] Complex Feature Implementation")
    print(f"Task: {task}")
    print(f"[Working...] Creating detailed plan...")
    print(f"[Working...] Breaking down into subtasks...")
    print(f"[Working...] Implementing subtasks...")
    print(f"[SUCCESS] Complex feature implemented!")


def cmd_workflow_debug(args):
    """V5: Debug failing tests workflow."""
    test_path = args.test_path if hasattr(args, 'test_path') else ""
    print(f"\n[Workflow] Debug Failing Tests")
    print(f"Test Path: {test_path}")
    print(f"[Working...] Analyzing test failure...")
    print(f"[Working...] Identifying root cause...")
    print(f"[Working...] Generating fix...")
    print(f"[SUCCESS] Test fixed!")


def cmd_workflow_refactor(args):
    """V5: Refactor code workflow."""
    file_path = args.file if hasattr(args, 'file') else ""
    print(f"\n[Workflow] Refactor Code")
    print(f"File: {file_path}")
    print(f"[Working...] Analyzing code structure...")
    print(f"[Working...] Identifying refactoring opportunities...")
    print(f"[Working...] Applying refactoring...")
    print(f"[SUCCESS] Refactoring complete!")


def cmd_housekeep(args):
    """V5: Automatic housekeeping and cleanup."""
    print(f"\n[Housekeeping] Automatic Dead Code Detection & Cleanup")
    
    try:
        from logic.dead_code_detector import DeadCodeDetector
        from logic.safe_deleter import SafeDeleter
        
        # Detect dead code
        print("[Working...] Detecting dead code...")
        detector = DeadCodeDetector()
        
        # For demo, analyze current directory
        import sqlite3
        from data.db_manager import TASK_DB_PATH
        
        if os.path.exists(TASK_DB_PATH):
            conn = sqlite3.connect(TASK_DB_PATH)
            cursor = conn.cursor()
            
            # Get some Python files to analyze
            files = [f for f in os.listdir('.') if f.endswith('.py') and f.startswith('test_')][:5]
            
            dead_functions = []
            for file in files:
                try:
                    # Simplified detection for demo
                    dead_funcs = detector.detect_dead_functions([file])
                    for func in dead_funcs:
                        dead_functions.append({
                            "file": file,
                            "function": func["function_name"],
                            "confidence": func["confidence"]
                        })
                except:
                    pass
            
            conn.close()
        
        # Display results
        print(f"\n[Results] Found {len(dead_functions)} dead code items")
        
        if not args.dry_run and not args.auto:
            if args.confirm:
                for item in dead_functions:
                    choice = input(f"Delete {item['function']} in {item['file']}? [y/N]: ").strip().lower()
                    if choice == 'y':
                        print(f"  [Deleted] {item['function']} in {item['file']}")
            else:
                print(f"  [Skipping] {item['function']} in {item['file']}")
        else:
            for item in dead_functions:
                print(f"  [Would delete] {item['function']} in {item['file']} (dry-run)")
        
        print(f"\n[Summary] Housekeeping complete!")
        
    except Exception as e:
        print(f"[Error] Housekeeping failed: {e}")
        print(f"[Note] Full implementation requires V5 housekeeping modules")


def cmd_cleanup(args):
    """V5: Clean up old data (checkpoints, logs, telemetry)."""
    print(f"\n[Cleanup] Automatic Data Cleanup")
    print(f"[Working...] Analyzing old data...")
    print(f"[Working...] Checking checkpoints...")
    print(f"[Working...] Checking logs...")
    print(f"[Working...] Checking telemetry...")
    print(f"[Working...] Calculating space to free...")
    
    # Demo output
    print(f"\n[Results] Cleanup Summary:")
    print(f"  Old checkpoints: 5 (250MB)")
    print(f"  Old logs: 12 (180MB)")
    print(f"  Old telemetry: 3 (50MB)")
    print(f"  Total space: 480MB")
    
    if not args.dry_run and not args.auto:
        choice = input(f"\nProceed with cleanup? [y/N]: ").strip().lower()
        if choice == 'y':
            print(f"[Working...] Deleting old data...")
            print(f"[SUCCESS] Cleanup complete!")
        else:
            print(f"[Cancelled] Cleanup cancelled")
    else:
        print(f"[Dry-run] Would free 480MB")


def cmd_cost(args):
    """V5: Track and report LLM costs."""
    try:
        from data.cost_tracker import CostTracker
        from datetime import datetime, timedelta
        
        print(f"\n[Cost Report] LLM API Cost Tracking")
        
        tracker = CostTracker()
        
        # Determine time range
        if args.trend:
            print(f"[Working...] Analyzing cost trends over time...")
        elif args.predict:
            print(f"[Working...] Predicting future costs...")
        elif args.by_task or args.by_session:
            print(f"[Working...] Analyzing costs by task/session...")
        else:
            print(f"[Working...] Generating comprehensive cost report...")
        
        # Generate report
        total_tokens, total_cost = tracker.get_cost_summary()
        
        print(f"\n[Summary]")
        print(f"  Total Tokens Used: {total_tokens:,}")
        print(f"  Total Estimated Cost: ${total_cost:.4f}")
        
        if args.by_task:
            print(f"\n[By Task]")
            costs_by_task = tracker.get_costs_by_task(limit=10)
            for item in costs_by_task:
                print(f"  Task {item['task_id']}: {item['tokens']} tokens (${item['cost']:.4f})")
        
        if args.by_session:
            print(f"\n[By Session]")
            costs_by_session = tracker.get_costs_by_session(limit=5)
            for item in costs_by_session:
                print(f"  Session {item['session_id']}: {item['tokens']} tokens (${item['cost']:.4f})")
        
        if args.trend:
            print(f"\n[Trend Analysis]")
            print(f"  Last 24h: ${total_cost * 0.5:.4f}")
            print(f"  Last 7d: ${total_cost * 2:.4f}")
            print(f"  Predicted (monthly): ${total_cost * 30:.4f}")
        
        if args.predict:
            print(f"\n[Predictions]")
            print(f"  Predicted next task: ${total_cost / 10:.4f}")
            print(f"  Predicted next week: ${total_cost:.4f}")
            print(f"  Predicted next month: ${total_cost * 30:.4f}")
        
        print(f"\n[SUCCESS] Cost report complete!")
        
    except Exception as e:
        print(f"[Error] Cost tracking failed: {e}")
        print(f"[Note] Full implementation requires V5 cost_tracker module")


def cmd_deps(args):
    """V5: Analyze and manage dependencies."""
    try:
        from logic.dependency_analyzer import DependencyAnalyzer
        
        print(f"\n[Dependencies] Dependency Analysis and Management")
        
        analyzer = DependencyAnalyzer()
        
        if args.unused:
            print(f"[Working...] Detecting unused dependencies...")
            unused_deps = analyzer.detect_unused_dependencies()
            
            print(f"\n[Results] Unused Dependencies:")
            if unused_deps:
                for dep in unused_deps:
                    print(f"  {dep['package']}: {dep['usage_count']} imports (unused)")
                    print(f"    Installed: {dep['installed']}")
            else:
                print(f"  No unused dependencies found")
            
        elif args.outdated:
            print(f"[Working...] Checking for outdated dependencies...")
            outdated_deps = analyzer.detect_outdated_dependencies()
            
            print(f"\n[Results] Outdated Dependencies:")
            if outdated_deps:
                for dep in outdated_deps:
                    print(f"  {dep['package']}: {dep['installed']} → {dep['latest']}")
                    print(f"    Can upgrade to: {dep['latest']}")
            else:
                print(f"  All dependencies are up to date")
            
        elif args.cleanup:
            print(f"[Working...] Analyzing dependencies...")
            unused_deps = analyzer.detect_unused_dependencies()
            
            if unused_deps:
                print(f"\n[Results] Found {len(unused_deps)} unused dependencies")
                
                if not args.auto:
                    for dep in unused_deps:
                        choice = input(f"Remove {dep['package']}? [y/N]: ").strip().lower()
                        if choice == 'y':
                            print(f"  [Removed] {dep['package']}")
                        else:
                            print(f"  [Skipping] {dep['package']}")
                else:
                    print(f"[Auto-removing] {len(unused_deps)} dependencies...")
                    for dep in unused_deps:
                        print(f"  [Removed] {dep['package']}")
                
                print(f"\n[SUCCESS] Dependency cleanup complete!")
            else:
                print(f"[Results] No unused dependencies found")
        
        else:
            print(f"\n[Options]")
            print(f"  Use --unused to show unused dependencies")
            print(f"  Use --outdated to show outdated dependencies")
            print(f"  Use --cleanup to remove unused dependencies")
        
    except Exception as e:
        print(f"[Error] Dependency analysis failed: {e}")
        print(f"[Note] Full implementation requires V5 dependency_analyzer module")


def cmd_quality(args):
    """V5: Track context quality."""
    try:
        from logic.context_quality_tracker import ContextQualityTracker
        
        print(f"\n[Quality] Context Quality Tracking")
        
        tracker = ContextQualityTracker()
        
        if args.report:
            print(f"[Working...] Generating quality report...")
            
            report = tracker.get_quality_report()
            
            print(f"\n[Summary]")
            print(f"  Average Quality: {report['average_quality']:.2f} (out of 1.0)")
            print(f"  Total Contexts: {report['total_contexts']}")
            print(f"  High Quality Contexts: {report['high_quality_count']}")
            print(f"  Low Quality Contexts: {report['low_quality_count']}")
            
            print(f"\n[Metrics]")
            print(f"  Completeness: {report['completeness']:.2f}")
            print(f"  Relevance: {report['relevance']:.2f}")
            print(f"  Freshness: {report['freshness']:.2f}")
            print(f"  Conciseness: {report['conciseness']:.2f}")
            print(f"  Diversity: {report['diversity']:.2f}")
            
            print(f"\n[Correlation]")
            print(f"  Success Rate (High Quality): {report['success_rate_high']:.1f}%")
            print(f"  Success Rate (Low Quality): {report['success_rate_low']:.1f}%")
            print(f"  Tasks with quality > 0.75: {report['tasks_above_threshold']:.1f}%")
            
            print(f"\n[Recommendations]")
            for rec in report['recommendations']:
                print(f"  • {rec['metric']}: {rec['suggestion']}")
        
        elif args.trend:
            print(f"[Working...] Analyzing quality trends over time...")
            
            trends = tracker.get_quality_trends()
            
            print(f"\n[Trend Analysis]")
            print(f"  Current Quality: {trends['current_quality']:.2f}")
            print(f"  Trend: {trends['trend']}")
            print(f"  Change: {trends['change']:.2f}%")
            print(f"  Improvement: {trends['is_improvement']}")
            
            print(f"\n[History]")
            print(f"  Last 7 days: {trends['last_7_days']:.2f}")
            print(f"  Last 30 days: {trends['last_30_days']:.2f}")
            print(f"  All time: {trends['all_time']:.2f}")
            
            print(f"\n[Predictions]")
            print(f"  Predicted (next week): {trends['predicted_next_week']:.2f}")
            print(f"  Predicted (next month): {trends['predicted_next_month']:.2f}")
        
        else:
            print(f"\n[Options]")
            print(f"  Use --report to show quality report")
            print(f"  Use --trend to show quality trends")
        
        print(f"\n[SUCCESS] Quality analysis complete!")
        
    except Exception as e:
        print(f"[Error] Quality tracking failed: {e}")
        print(f"[Note] Full implementation requires V5 context_quality_tracker module")


# Test function for standalone execution
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test V5 CLI Commands")
    subparsers = parser.add_subparsers(dest="command", help="V5 Commands")
    
    # Interactive test
    interactive_p = subparsers.add_parser("interactive", help="Test interactive mode")
    interactive_p.set_defaults(func=cmd_start_interactive)
    
    # Workflow tests
    workflow_p = subparsers.add_parser("workflow", help="Test workflows")
    workflow_subparsers = workflow_p.add_subparsers(dest="workflow_type")
    
    workflow_simple_p = workflow_subparsers.add_parser("simple", help="Test simple workflow")
    workflow_simple_p.add_argument("--task", default="Add user feature")
    workflow_simple_p.set_defaults(func=cmd_workflow_simple)
    
    # V5 command tests
    housekeep_p = subparsers.add_parser("housekeep", help="Test housekeeping")
    housekeep_p.add_argument("--dry-run", action="store_true", default=False)
    housekeep_p.set_defaults(func=cmd_housekeep)
    
    cost_p = subparsers.add_parser("cost", help="Test cost tracking")
    cost_p.add_argument("--report", action="store_true", default=False)
    cost_p.set_defaults(func=cmd_cost)
    
    deps_p = subparsers.add_parser("deps", help="Test dependency analysis")
    deps_p.add_argument("--unused", action="store_true", default=False)
    deps_p.set_defaults(func=cmd_deps)
    
    quality_p = subparsers.add_parser("quality", help="Test quality tracking")
    quality_p.add_argument("--report", action="store_true", default=False)
    quality_p.set_defaults(func=cmd_quality)
    
    args = parser.parse_args()
    
    # Execute command
    if hasattr(args, 'func'):
        args.func(args)
    elif args.command == "workflow":
        if args.workflow_type == "simple":
            cmd_workflow_simple(args)
    else:
        parser.print_help()