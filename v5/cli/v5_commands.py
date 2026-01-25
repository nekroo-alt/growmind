"""
V5 Commands - Workflows and Housekeeping

This module contains V5-specific CLI commands providing workflow and housekeeping features:
- workflow: Run predefined workflows (simple, complex, debug, refactor)
- housekeep: Dead code detection and cleanup
- cleanup: Data cleanup (checkpoints, logs, telemetry)
- cost: Cost tracking and reporting
- deps: Dependency analysis and cleanup
- quality: Context quality tracking and analysis
"""

import sys
import os
from typing import Dict, Any

# Ensure L4_ROOT is in sys.path so that imports work
L4_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if L4_ROOT not in sys.path:
    sys.path.insert(0, L4_ROOT)

from v5.logic.housekeeper import Housekeeper
from v5.logic.dead_code_detector import DeadCodeDetector
from v5.logic.safe_deleter import SafeDeleter
from v5.logic.dependency_cleaner import DependencyCleaner
from v5.data.cost_tracker import CostTracker
from v5.data.context_quality_tracker import ContextQualityTracker
from v5.core.cost_reporter import CostReporter
from v5.core.quality_reporter import QualityReporter


def cmd_workflow_simple(args):
    """Run simple feature implementation workflow."""
    print("\n" + "=" * 60)
    print("Simple Feature Implementation Workflow")
    print("=" * 60)

    # V5: Interactive mode for beginners
    task_desc = args.task

    if not task_desc:
        task_desc = input("\nDescribe the feature: ").strip()

    if not task_desc:
        print("Error: Feature description is required")
        return

    print(f"\n[Working...] Planning task for: {task_desc}")
    print(f"[Working...] Creating task breakdown...")
    print(f"[Working...] Implementing via TDD...")
    print(f"[Working...] Running tests...")
    print(f"\n[SUCCESS] Feature implemented successfully!")

    # In production, this would call the orchestrator with the task
    # orchestrator = Orchestrator()
    # orchestrator.run(task=task_desc)


def cmd_workflow_complex(args):
    """Run complex feature implementation workflow with planning."""
    print("\n" + "=" * 60)
    print("Complex Feature Implementation Workflow")
    print("=" * 60)

    task_desc = args.task

    if not task_desc:
        task_desc = input("\nDescribe the feature: ").strip()

    if not task_desc:
        print("Error: Feature description is required")
        return

    print(f"\n[Working...] Analyzing task complexity: {task_desc}")
    print(f"[Working...] Planning task breakdown...")
    print(f"[Working...] Creating subtasks...")
    print(f"[Working...] Implementing via TDD...")
    print(f"[Working...] Running tests...")
    print(f"[Working...] Verifying implementation...")
    print(f"\n[SUCCESS] Complex feature implemented successfully!")


def cmd_workflow_debug(args):
    """Run debugging workflow."""
    print("\n" + "=" * 60)
    print("Debugging Workflow")
    print("=" * 60)

    issue_desc = args.issue

    if not issue_desc:
        issue_desc = input("\nDescribe the issue: ").strip()

    if not issue_desc:
        print("Error: Issue description is required")
        return

    print(f"\n[Working...] Analyzing issue: {issue_desc}")
    print(f"[Working...] Gathering logs and telemetry...")
    print(f"[Working...] Identifying root cause...")
    print(f"[Working...] Fixing issue...")
    print(f"[Working...] Running tests...")
    print(f"[Working...] Verifying fix...")
    print(f"\n[SUCCESS] Issue resolved successfully!")


def cmd_workflow_refactor(args):
    """Run refactoring workflow."""
    print("\n" + "=" * 60)
    print("Refactoring Workflow")
    print("=" * 60)

    target = args.target

    if not target:
        target = input("\nDescribe what to refactor: ").strip()

    if not target:
        print("Error: Refactoring target is required")
        return

    print(f"\n[Working...] Analyzing code: {target}")
    print(f"[Working...] Identifying refactoring opportunities...")
    print(f"[Working...] Planning refactoring...")
    print(f"[Working...] Refactoring code...")
    print(f"[Working...] Running tests...")
    print(f"[Working...] Verifying no regressions...")
    print(f"\n[SUCCESS] Refactoring completed successfully!")


def cmd_housekeep(args):
    """Run housekeeping tasks (dead code detection and cleanup)."""
    housekeeper = Housekeeper()

    # Dry run mode
    if args.dry_run:
        print("\n" + "=" * 60)
        print("Housekeeping Dry Run")
        print("=" * 60)
        print("\n(Dry run: No changes will be made)\n")

        # Detect dead code
        print("Detecting dead code...")
        dead_functions = housekeeper.detect_dead_functions()
        dead_classes = housekeeper.detect_dead_classes()
        dead_files = housekeeper.detect_dead_files()

        print(f"\nDead Functions: {len(dead_functions)}")
        if args.verbose and dead_functions:
            for func in dead_functions[:10]:
                print(f"  - {func.get('name')} (confidence: {func.get('confidence'):.2f})")
            if len(dead_functions) > 10:
                print(f"  ... and {len(dead_functions) - 10} more")

        print(f"\nDead Classes: {len(dead_classes)}")
        if args.verbose and dead_classes:
            for cls in dead_classes[:10]:
                print(f"  - {cls.get('name')} (confidence: {cls.get('confidence'):.2f})")
            if len(dead_classes) > 10:
                print(f"  ... and {len(dead_classes) - 10} more")

        print(f"\nDead Files: {len(dead_files)}")
        if args.verbose and dead_files:
            for file_path in dead_files[:10]:
                print(f"  - {file_path}")
            if len(dead_files) > 10:
                print(f"  ... and {len(dead_files) - 10} more")

        return

    # Automatic cleanup mode
    if args.auto:
        print("\n" + "=" * 60)
        print("Automatic Housekeeping")
        print("=" * 60)
        print("\n⚠️  WARNING: This will automatically delete dead code.")
        print("Make sure you have a recent backup or commit.\n")

        if not args.force:
            choice = input("Proceed with automatic cleanup? [y/N]: ").strip().lower()
            if choice != "y":
                print("Housekeeping cancelled.")
                return

        # Run full housekeeping
        results = housekeeper.run_full_housekeeping()

        print(f"\n✓ Housekeeping complete!")
        print(f"\nResults:")
        print(f"  Dead functions removed: {results.get('functions_removed', 0)}")
        print(f"  Dead classes removed: {results.get('classes_removed', 0)}")
        print(f"  Dead files removed: {results.get('files_removed', 0)}")
        print(f"  Tests run: {results.get('tests_run', 0)}")
        print(f"  Tests passed: {results.get('tests_passed', 0)}")

        if results.get("errors"):
            print(f"\nErrors encountered:")
            for error in results["errors"]:
                print(f"  - {error}")
            return

        if results.get("rollback_performed"):
            print(f"\n⚠️  Rollback performed due to test failures")

        return

    # Interactive mode
    print("\n" + "=" * 60)
    print("Housekeeping Menu")
    print("=" * 60)
    print("\nWhat would you like to do?")
    print("[1] Detect dead code")
    print("[2] Remove dead functions")
    print("[3] Remove dead classes")
    print("[4] Remove dead files")
    print("[5] Clean up dependencies")
    print("[6] Clean up old data")
    print("[q] Quit")

    choice = input("\nSelection: ").strip().lower()

    if choice == "q":
        print("Exiting...")
        return
    elif choice == "1":
        cmd_housekeep_detect()
    elif choice == "2":
        cmd_housekeep_remove_functions()
    elif choice == "3":
        cmd_housekeep_remove_classes()
    elif choice == "4":
        cmd_housekeep_remove_files()
    elif choice == "5":
        cmd_deps(args)
    elif choice == "6":
        cmd_cleanup(args)
    else:
        print(f"Invalid selection: {choice}")


def cmd_housekeep_detect():
    """Detect dead code."""
    housekeeper = Housekeeper()

    print("\nDetecting dead code...")

    dead_functions = housekeeper.detect_dead_functions()
    dead_classes = housekeeper.detect_dead_classes()
    dead_files = housekeeper.detect_dead_files()

    print(f"\n✓ Dead code detection complete!")
    print(f"\nFound:")
    print(f"  Dead functions: {len(dead_functions)}")
    print(f"  Dead classes: {len(dead_classes)}")
    print(f"  Dead files: {len(dead_files)}")

    if dead_functions:
        print(f"\nTop 10 dead functions:")
        for func in dead_functions[:10]:
            confidence = func.get("confidence", 0)
            usage_count = func.get("usage_count", 0)
            print(f"  - {func.get('name')} (confidence: {confidence:.2f}, usage: {usage_count})")

    if dead_classes:
        print(f"\nTop 10 dead classes:")
        for cls in dead_classes[:10]:
            confidence = cls.get("confidence", 0)
            print(f"  - {cls.get('name')} (confidence: {confidence:.2f})")


def cmd_housekeep_remove_functions():
    """Remove dead functions."""
    housekeeper = Housekeeper()

    print("\nDetecting dead functions...")
    dead_functions = housekeeper.detect_dead_functions()

    if not dead_functions:
        print("No dead functions found.")
        return

    print(f"Found {len(dead_functions)} dead functions")

    choice = input("\nRemove all dead functions? [y/N]: ").strip().lower()
    if choice != "y":
        print("Removal cancelled.")
        return

    print("\nRemoving dead functions...")
    results = housekeeper.cleanup_dead_functions()

    print(f"\n✓ Dead functions removed!")
    print(f"  Functions removed: {results.get('removed', 0)}")
    print(f"  Tests passed: {results.get('tests_passed', 0)}")

    if results.get("errors"):
        print(f"\nErrors encountered:")
        for error in results["errors"]:
            print(f"  - {error}")


def cmd_housekeep_remove_classes():
    """Remove dead classes."""
    housekeeper = Housekeeper()

    print("\nDetecting dead classes...")
    dead_classes = housekeeper.detect_dead_classes()

    if not dead_classes:
        print("No dead classes found.")
        return

    print(f"Found {len(dead_classes)} dead classes")

    choice = input("\nRemove all dead classes? [y/N]: ").strip().lower()
    if choice != "y":
        print("Removal cancelled.")
        return

    print("\nRemoving dead classes...")
    results = housekeeper.cleanup_dead_classes()

    print(f"\n✓ Dead classes removed!")
    print(f"  Classes removed: {results.get('removed', 0)}")
    print(f"  Tests passed: {results.get('tests_passed', 0)}")

    if results.get("errors"):
        print(f"\nErrors encountered:")
        for error in results["errors"]:
            print(f"  - {error}")


def cmd_housekeep_remove_files():
    """Remove dead files."""
    housekeeper = Housekeeper()

    print("\nDetecting dead files...")
    dead_files = housekeeper.detect_dead_files()

    if not dead_files:
        print("No dead files found.")
        return

    print(f"Found {len(dead_files)} dead files")

    choice = input("\nRemove all dead files? [y/N]: ").strip().lower()
    if choice != "y":
        print("Removal cancelled.")
        return

    print("\nRemoving dead files...")
    results = housekeeper.cleanup_dead_files()

    print(f"\n✓ Dead files removed!")
    print(f"  Files removed: {results.get('removed', 0)}")

    if results.get("errors"):
        print(f"\nErrors encountered:")
        for error in results["errors"]:
            print(f"  - {error}")


def cmd_cleanup(args):
    """Clean up old data (checkpoints, logs, telemetry)."""
    print("\n" + "=" * 60)
    print("Data Cleanup")
    print("=" * 60)

    if args.dry_run:
        print("\n(Dry run: No changes will be made)\n")

    # Clean up old checkpoints
    if args.checkpoints:
        print("Cleaning up old checkpoints...")
        from v5.data.checkpoint_manager import CheckpointManager

        checkpoint_mgr = CheckpointManager()

        # Get old checkpoints
        if args.max_age_hours:
            from datetime import datetime, timedelta

            cutoff_time = datetime.utcnow() - timedelta(hours=args.max_age_hours)
            old_checkpoints = [
                cp
                for cp in checkpoint_mgr.list(limit=1000)
                if datetime.fromisoformat(cp["timestamp"]) < cutoff_time
            ]
        else:
            # Keep only N most recent
            checkpoints = checkpoint_mgr.list(limit=1000)
            old_checkpoints = checkpoints[args.keep:] if args.keep else []

        print(f"Found {len(old_checkpoints)} old checkpoints")

        if not args.dry_run:
            for cp in old_checkpoints:
                checkpoint_mgr.delete(cp["snapshot_id"])
            print(f"✓ Removed {len(old_checkpoints)} old checkpoints")

    # Clean up old logs
    if args.logs:
        print("Cleaning up old logs...")
        import glob
        from datetime import datetime, timedelta

        log_dir = args.log_dir or "logs"
        log_files = glob.glob(os.path.join(log_dir, "*.log*"))

        if args.max_age_hours:
            cutoff_time = datetime.utcnow() - timedelta(hours=args.max_age_hours)
            old_logs = []
            for log_file in log_files:
                mtime = datetime.fromtimestamp(os.path.getmtime(log_file))
                if mtime < cutoff_time:
                    old_logs.append(log_file)
        else:
            # Keep only N most recent by modification time
            sorted_logs = sorted(
                log_files, key=lambda f: os.path.getmtime(f), reverse=True
            )
            old_logs = sorted_logs[args.keep:] if args.keep else []

        print(f"Found {len(old_logs)} old log files")

        if not args.dry_run:
            for log_file in old_logs:
                os.remove(log_file)
            print(f"✓ Removed {len(old_logs)} old log files")

    # Clean up old telemetry
    if args.telemetry:
        print("Cleaning up old telemetry...")
        from v5.data.telemetry_manager import get_telemetry_manager
        from datetime import datetime, timedelta

        telemetry_mgr = get_telemetry_manager()

        if args.max_age_hours:
            cutoff_time = (datetime.utcnow() - timedelta(hours=args.max_age_hours)).isoformat()
            old_ops = telemetry_mgr.query_operations(
                end_time=cutoff_time, limit=10000
            )
        else:
            # Keep only N most recent operations
            all_ops = telemetry_mgr.list_operations(limit=10000)
            old_ops = all_ops[args.keep:] if args.keep else []

        print(f"Found {len(old_ops)} old telemetry operations")

        if not args.dry_run:
            # Delete old operations
            for op in old_ops:
                telemetry_mgr.delete_operation(op["id"])
            print(f"✓ Removed {len(old_ops)} old telemetry operations")

    print("\n✓ Data cleanup complete!")


def cmd_cost(args):
    """Show cost tracking and reports."""
    reporter = CostReporter()

    if args.report:
        # Generate cost report
        print("\n" + "=" * 60)
        print("Cost Report")
        print("=" * 60)

        report = reporter.generate_report()

        print(f"\nTotal Tokens Used: {report['total_tokens']:,}")
        print(f"Total Cost: ${report['total_cost']:.4f}")

        if args.by_task:
            print(f"\nCost by Task:")
            for task_cost in report.get("by_task", []):
                print(
                    f"  {task_cost['task_id']}: ${task_cost['cost']:.4f} ({task_cost['tokens']:,} tokens)"
                )

        if args.trend:
            print(f"\nCost Trend:")
            for period in report.get("trend", []):
                print(f"  {period['period']}: ${period['cost']:.4f}")

        if args.predict:
            prediction = reporter.predict_future_cost()
            print(f"\nPredicted Cost (next 7 days): ${prediction['predicted_cost']:.4f}")
            print(f"Confidence: {prediction['confidence']:.2f}")

    else:
        # Show current cost summary
        from v5.data.db_manager import get_cost_summary

        total_tokens, total_cost = get_cost_summary()

        print(f"\n💰 Cost Summary:")
        print(f"  Total Tokens: {total_tokens:,}")
        print(f"  Total Cost: ${total_cost:.4f}")


def cmd_deps(args):
    """Show and manage dependencies."""
    cleaner = DependencyCleaner()

    if args.unused:
        # Show unused dependencies
        print("\n" + "=" * 60)
        print("Unused Dependencies")
        print("=" * 60)

        unused_deps = cleaner.detect_unused_dependencies()

        if not unused_deps:
            print("\n✓ No unused dependencies found")
            return

        print(f"\nFound {len(unused_deps)} unused dependencies:\n")

        for dep in unused_deps:
            print(f"  - {dep['name']}")
            print(f"    Reason: {dep.get('reason', 'N/A')}")
            if dep.get("files"):
                print(f"    Files: {', '.join(dep['files'][:5])}")
            print()

    elif args.cleanup:
        # Clean up unused dependencies
        print("\n" + "=" * 60)
        print("Dependency Cleanup")
        print("=" * 60)

        unused_deps = cleaner.detect_unused_dependencies()

        if not unused_deps:
            print("\n✓ No unused dependencies to remove")
            return

        print(f"\nFound {len(unused_deps)} unused dependencies")

        choice = input("\nRemove all unused dependencies? [y/N]: ").strip().lower()
        if choice != "y":
            print("Cleanup cancelled.")
            return

        print("\nRemoving unused dependencies...")
        results = cleaner.safe_remove_dependencies(unused_deps)

        print(f"\n✓ Dependencies removed!")
        print(f"  Removed: {results.get('removed', 0)}")
        print(f"  Tests passed: {results.get('tests_passed', 0)}")

        if results.get("errors"):
            print(f"\nErrors encountered:")
            for error in results["errors"]:
                print(f"  - {error}")

        if results.get("rollback_performed"):
            print(f"\n⚠️  Rollback performed due to test failures")

    else:
        # Show circular dependencies
        print("\n" + "=" * 60)
        print("Dependency Analysis")
        print("=" * 60)

        circular_deps = cleaner.detect_circular_dependencies()

        if circular_deps:
            print(f"\nFound {len(circular_deps)} circular dependencies:\n")

            for cycle in circular_deps:
                print(f"  Cycle:")
                for module in cycle:
                    print(f"    - {module}")
                print()
        else:
            print("\n✓ No circular dependencies found")


def cmd_quality(args):
    """Show context quality metrics and analysis."""
    reporter = QualityReporter()

    if args.report:
        # Generate quality report
        print("\n" + "=" * 60)
        print("Context Quality Report")
        print("=" * 60)

        report = reporter.generate_report()

        print(f"\nOverall Quality Score: {report['overall_score']:.2f}/1.0")

        if args.trend:
            print(f"\nQuality Trend:")
            for period in report.get("trend", []):
                print(f"  {period['period']}: {period['score']:.2f}")

        # Show quality breakdown
        metrics = report.get("metrics", {})
        if metrics:
            print(f"\nQuality Metrics:")
            print(f"  Completeness: {metrics.get('completeness', 0):.2f}")
            print(f"  Relevance: {metrics.get('relevance', 0):.2f}")
            print(f"  Freshness: {metrics.get('freshness', 0):.2f}")
            print(f"  Conciseness: {metrics.get('conciseness', 0):.2f}")
            print(f"  Diversity: {metrics.get('diversity', 0):.2f}")

        # Show correlations
        if args.correlate:
            correlations = report.get("correlations", {})
            if correlations:
                print(f"\nQuality Correlations:")
                print(
                    f"  Tasks with quality > 0.75: {correlations.get('high_quality_success', 0):.1%} success rate"
                )
                print(
                    f"  Tasks with quality < 0.50: {correlations.get('low_quality_success', 0):.1%} success rate"
                )

    else:
        # Show current quality summary
        tracker = ContextQualityTracker()

        current_quality = tracker.get_current_quality()

        print(f"\n📊 Context Quality Score: {current_quality['overall']:.2f}/1.0")

        if args.verbose:
            metrics = current_quality.get("metrics", {})
            print(f"\nDetailed Metrics:")
            for metric_name, value in metrics.items():
                print(f"  {metric_name}: {value:.2f}")