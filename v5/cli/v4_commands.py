"""
V4 Commands - Adaptive Reasoning

This module contains V4-specific CLI commands providing adaptive reasoning features:
- decisions: Show decision history and patterns
- profile: Manage configuration profiles (list, show, use, diff)
- explain: Explain a specific decision with natural language
- progress: Show progress tracking and validation
"""

import sys
import os
from typing import Dict, Any

# Ensure L4_ROOT is in sys.path so that imports work
L4_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if L4_ROOT not in sys.path:
    sys.path.insert(0, L4_ROOT)

from v5.data.decision_history import DecisionHistory
from v5.logic.progress_tracker import ProgressTracker
from v5.logic.explanation_generator import ExplanationGenerator
from v5.data.context_hierarchy import ContextHierarchy


def cmd_decisions(args):
    """Show decision history and patterns."""
    from v5.data.decision_tracer import DecisionTracer

    tracer = DecisionTracer()
    decisions = tracer.search_decisions(
        task_id=args.task_id,
        operation_id=args.operation_id,
        start_time=args.start,
        end_time=args.end,
        limit=args.limit,
    )

    if not decisions:
        print("No decisions found.")
        return

    print(f"\nFound {len(decisions)} decisions:\n")

    for i, decision in enumerate(decisions, 1):
        decision_id = decision.get("id", "N/A")[:16]
        timestamp = decision.get("timestamp", "N/A").replace("T", " ").split(".")[0]
        context = decision.get("context", {})
        reasoning = decision.get("reasoning", "N/A")
        alternatives = decision.get("alternatives", [])
        chosen_action = decision.get("chosen_action", "N/A")
        confidence = decision.get("confidence", 0)
        outcome = decision.get("outcome", "N/A")

        print(f"{i}. [{timestamp}] Decision {decision_id}...")
        print(f"   Context: {context.get('situation_type', 'N/A')}")
        print(f"   Reasoning: {reasoning[:100]}...")
        print(f"   Action: {chosen_action}")
        print(f"   Confidence: {confidence:.2f}")
        print(f"   Outcome: {outcome}")

        if alternatives:
            print(f"   Alternatives:")
            for alt in alternatives:
                print(f"     - {alt.get('action')}: {alt.get('reasoning', 'N/A')[:50]}...")

        print()

    # Export if requested
    if args.export:
        tracer.export_decisions(decisions, args.export, format=args.format)


def cmd_profile_list(args):
    """List available configuration profiles."""
    from v5.core.config import get_available_profiles

    profiles = get_available_profiles()

    if not profiles:
        print("No profiles found.")
        return

    print(f"\nAvailable Profiles:\n")

    for profile_name in profiles:
        print(f"- {profile_name}")

    print()


def cmd_profile_show(args):
    """Show details of a specific profile."""
    from v5.core.config import get_profile_config

    profile_name = args.name

    if not profile_name:
        print("Error: --name is required to show profile")
        return

    config = get_profile_config(profile_name)

    if not config:
        print(f"Error: Profile not found: {profile_name}")
        return

    print(f"\nProfile: {profile_name}\n")

    # Display configuration
    for key, value in config.items():
        if isinstance(value, dict):
            print(f"{key}:")
            for subkey, subvalue in value.items():
                print(f"  {subkey}: {subvalue}")
        else:
            print(f"{key}: {value}")

    print()


def cmd_profile_use(args):
    """Switch to a different configuration profile."""
    from v5.core.config import set_active_profile, get_profile_config

    profile_name = args.name

    if not profile_name:
        print("Error: --name is required to switch profile")
        return

    config = get_profile_config(profile_name)

    if not config:
        print(f"Error: Profile not found: {profile_name}")
        return

    # Set active profile
    success = set_active_profile(profile_name)

    if success:
        print(f"✓ Switched to profile: {profile_name}")
    else:
        print(f"✗ Failed to switch to profile: {profile_name}")


def cmd_profile_diff(args):
    """Compare two configuration profiles."""
    from v5.core.config import get_profile_config

    profile1 = args.profile1
    profile2 = args.profile2

    if not profile1 or not profile2:
        print("Error: Both --profile1 and --profile2 are required")
        return

    config1 = get_profile_config(profile1)
    config2 = get_profile_config(profile2)

    if not config1:
        print(f"Error: Profile not found: {profile1}")
        return

    if not config2:
        print(f"Error: Profile not found: {profile2}")
        return

    print(f"\nComparing profiles: {profile1} vs {profile2}\n")

    # Find differences
    all_keys = set(config1.keys()) | set(config2.keys())

    differences = []

    for key in sorted(all_keys):
        value1 = config1.get(key)
        value2 = config2.get(key)

        if value1 != value2:
            differences.append(
                {"key": key, "value1": value1, "value2": value2}
            )

    if not differences:
        print("Profiles are identical.")
        return

    print(f"Found {len(differences)} differences:\n")

    for diff in differences:
        key = diff["key"]
        value1 = diff["value1"]
        value2 = diff["value2"]

        print(f"{key}:")
        if value1 is None:
            print(f"  {profile1}: (not set)")
        else:
            print(f"  {profile1}: {value1}")

        if value2 is None:
            print(f"  {profile2}: (not set)")
        else:
            print(f"  {profile2}: {value2}")

        print()


def cmd_explain(args):
    """Explain a specific decision with natural language."""
    from v5.data.decision_tracer import DecisionTracer

    if not args.id:
        print("Error: --id is required to explain a decision")
        return

    tracer = DecisionTracer()
    decision = tracer.get_decision(args.id)

    if not decision:
        print(f"Error: Decision not found: {args.id}")
        return

    generator = ExplanationGenerator()

    # Generate explanation based on format
    if args.format == "brief":
        explanation = generator.generate_brief_explanation(decision)
    elif args.format == "detailed":
        explanation = generator.generate_detailed_explanation(decision)
    elif args.format == "technical":
        explanation = generator.generate_technical_explanation(decision)
    else:
        explanation = generator.generate_brief_explanation(decision)

    print("\n" + "=" * 60)
    print("Decision Explanation")
    print("=" * 60)
    print("\n" + explanation)
    print()

    # Show decision details if verbose
    if args.verbose:
        print("\n" + "=" * 60)
        print("Decision Details")
        print("=" * 60)

        print(f"\nDecision ID: {decision.get('id')}")
        print(f"Timestamp: {decision.get('timestamp')}")
        print(f"Context: {decision.get('context', {})}")
        print(f"Reasoning: {decision.get('reasoning', 'N/A')}")
        print(f"Alternatives: {decision.get('alternatives', [])}")
        print(f"Chosen Action: {decision.get('chosen_action', 'N/A')}")
        print(f"Confidence: {decision.get('confidence', 0):.2f}")
        print(f"Outcome: {decision.get('outcome', 'N/A')}")
        print()


def cmd_progress(args):
    """Show progress tracking and validation."""
    tracker = ProgressTracker()

    if args.task_id:
        # Show progress for specific task
        progress = tracker.get_task_progress(args.task_id)

        if not progress:
            print(f"No progress found for task: {args.task_id}")
            return

        print(f"\nProgress for Task {args.task_id}\n")

        print(f"Status: {progress.get('status', 'N/A')}")
        print(f"Completed: {progress.get('completed', 0)}/{progress.get('total', 100)}")

        percentage = progress.get('percentage', 0)
        print(f"Percentage: {percentage:.1f}%")

        # Progress bar
        bar_length = 50
        filled = int(bar_length * percentage / 100)
        bar = "█" * filled + "░" * (bar_length - filled)
        print(f"\n[{bar}]")

        print(f"\nStarted: {progress.get('start_time', 'N/A')}")
        print(f"Last Update: {progress.get('last_update', 'N/A')}")

        if progress.get("estimated_completion"):
            print(f"Estimated Completion: {progress['estimated_completion']}")

        # Check for issues
        issues = []
        if progress.get("stagnation_detected", False):
            issues.append("⚠️  Stagnation detected - no progress for extended period")
        if progress.get("regression_detected", False):
            issues.append("❌ Regression detected - progress going backwards")

        if issues:
            print("\nIssues:")
            for issue in issues:
                print(f"  {issue}")

    else:
        # Show overall progress summary
        summary = tracker.get_progress_summary()

        print(f"\nOverall Progress Summary\n")

        print(f"Active Tasks: {summary.get('active_tasks', 0)}")
        print(f"Completed Tasks: {summary.get('completed_tasks', 0)}")
        print(f"Total Progress: {summary.get('overall_percentage', 0):.1f}%")

        # Progress bar
        percentage = summary.get('overall_percentage', 0)
        bar_length = 50
        filled = int(bar_length * percentage / 100)
        bar = "█" * filled + "░" * (bar_length - filled)
        print(f"\n[{bar}]\n")

        # Show recent progress updates
        recent = summary.get("recent_updates", [])
        if recent:
            print("Recent Updates:")
            for update in recent:
                timestamp = update.get("timestamp", "N/A").replace("T", " ").split(".")[0]
                task_id = update.get("task_id", "N/A")
                progress = update.get("progress", 0)
                print(f"  [{timestamp}] Task {task_id}: {progress:.1f}%")
            print()

        # Check for issues
        issues = []
        if summary.get("stagnation_count", 0) > 0:
            issues.append(
                f"⚠️  {summary['stagnation_count']} task(s) stagnating"
            )
        if summary.get("regression_count", 0) > 0:
            issues.append(
                f"❌ {summary['regression_count']} task(s) regressing"
            )

        if issues:
            print("Issues:")
            for issue in issues:
                print(f"  {issue}")
            print()

    # Validate progress
    if args.validate:
        print("\nValidating progress...\n")

        if args.task_id:
            validation = tracker.validate_progress(args.task_id)
        else:
            validation = tracker.validate_all_progress()

        print(f"Validation Result: {validation.get('status', 'N/A')}")

        if validation.get("issues"):
            print("\nIssues Found:")
            for issue in validation["issues"]:
                print(f"  - {issue}")
        else:
            print("\n✓ Progress validation passed")

    # Show predictions
    if args.predict and args.task_id:
        print("\nProgress Prediction\n")

        prediction = tracker.predict_completion(args.task_id)

        if prediction:
            print(f"Predicted Completion: {prediction.get('estimated_completion', 'N/A')}")
            print(f"Confidence: {prediction.get('confidence', 0):.2f}")

            if prediction.get("predicted_remaining_hours"):
                print(
                    f"Estimated Time Remaining: {prediction['predicted_remaining_hours']:.1f} hours"
                )
        else:
            print("Unable to predict completion time")

    print()