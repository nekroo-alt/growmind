"""
Test script for Status Dashboard implementation
"""

import sys
import os

# Add v2 to path
sys.path.insert(0, os.path.dirname(__file__))

from core.ui import StatusDashboard, create_status_dashboard, display_status
from datetime import datetime


def test_status_dashboard():
    """Test the StatusDashboard class"""
    print("Testing StatusDashboard...")

    # Create dashboard
    dashboard = create_status_dashboard()
    assert dashboard is not None, "Failed to create dashboard"
    print("✓ Dashboard created successfully")

    # Test display with sample data
    session_info = {
        "id": "session-123",
        "status": "active",
        "start_time": datetime.now().isoformat(),
        "tasks_completed": 5,
    }

    active_operation = {
        "operation_type": "implementation",
        "status": "in_progress",
        "task_id": 42,
        "task_title": "Add user authentication",
        "progress": {"completed": 3, "total": 5, "percentage": 60.0},
    }

    health_report = {
        "overall_status": "healthy",
        "checks": {
            "database": {"status": "ok", "details": {"latency_ms": 12}},
            "git": {"status": "ok", "details": {"branch": "main"}},
            "cache": {"status": "warning", "details": {"size_mb": 95}},
        },
    }

    resource_usage = {
        "cpu": 45.2,
        "memory": 2.1,
        "cache_size": 82.5,
        "cache_hit_rate": 92.3,
    }

    recent_activities = [
        {
            "timestamp": datetime.now(),
            "action_type": "test_generation",
            "status": "success",
            "summary": "Generated tests for auth module",
        },
        {
            "timestamp": datetime.now(),
            "action_type": "implementation",
            "status": "success",
            "summary": "Implemented login function",
        },
    ]

    # Display dashboard
    print("\n" + "=" * 60)
    print("DISPLAYING STATUS DASHBOARD")
    print("=" * 60 + "\n")

    dashboard.display(
        session_info=session_info,
        active_operation=active_operation,
        recent_activities=recent_activities,
        health_report=health_report,
        resource_usage=resource_usage,
        verbose=True,
    )

    print("\n✓ Dashboard displayed successfully")

    # Test convenience function
    print("\n" + "=" * 60)
    print("TESTING CONVENIENCE FUNCTION")
    print("=" * 60 + "\n")

    display_status(
        session_info=session_info,
        active_operation=active_operation,
        health_report=health_report,
        resource_usage=resource_usage,
        verbose=False,
    )

    print("\n✓ Convenience function works correctly")

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    test_status_dashboard()
