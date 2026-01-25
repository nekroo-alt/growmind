"""
L4 CLI Commands Module

This module provides organized CLI commands for L4D, separated by version:
- V3: Basic functionality (status, logs, telemetry, health, sessions, checkpoints, resume, recover)
- V4: Adaptive reasoning (decisions, explain, progress, profile)
- V5: Workflows and housekeeping (workflow, housekeep, cleanup, cost, deps, quality)

The CLI is organized into logical modules for better maintainability.
"""

from v5.cli.v3_commands import (
    cmd_start,
    cmd_status,
    cmd_retro,
    cmd_doctor,
    cmd_init,
    cmd_reset,
    cmd_logs,
    cmd_logs_summary,
    cmd_logs_errors,
    cmd_logs_timeline,
    cmd_health,
    cmd_resume,
    cmd_checkpoints_list,
    cmd_checkpoints_restore,
    cmd_checkpoints_delete,
    cmd_sessions_list,
    cmd_recover,
    cmd_telemetry_list,
    cmd_telemetry_show,
    cmd_telemetry_export,
    cmd_telemetry_export_from_ops,
    cmd_telemetry_stats,
    cmd_report_generate,
)

from v5.cli.v4_commands import (
    cmd_decisions,
    cmd_profile_list,
    cmd_profile_show,
    cmd_profile_use,
    cmd_profile_diff,
    cmd_explain,
    cmd_progress,
)

from v5.cli.v5_commands import (
    cmd_workflow_simple,
    cmd_workflow_complex,
    cmd_workflow_debug,
    cmd_workflow_refactor,
    cmd_housekeep,
    cmd_cleanup,
    cmd_cost,
    cmd_deps,
    cmd_quality,
)

__all__ = [
    # V3 Commands
    "cmd_start",
    "cmd_status",
    "cmd_retro",
    "cmd_doctor",
    "cmd_init",
    "cmd_reset",
    "cmd_logs",
    "cmd_logs_summary",
    "cmd_logs_errors",
    "cmd_logs_timeline",
    "cmd_health",
    "cmd_resume",
    "cmd_checkpoints_list",
    "cmd_checkpoints_restore",
    "cmd_checkpoints_delete",
    "cmd_sessions_list",
    "cmd_recover",
    "cmd_telemetry_list",
    "cmd_telemetry_show",
    "cmd_telemetry_export",
    "cmd_telemetry_export_from_ops",
    "cmd_telemetry_stats",
    "cmd_report_generate",
    # V4 Commands
    "cmd_decisions",
    "cmd_profile_list",
    "cmd_profile_show",
    "cmd_profile_use",
    "cmd_profile_diff",
    "cmd_explain",
    "cmd_progress",
    # V5 Commands
    "cmd_workflow_simple",
    "cmd_workflow_complex",
    "cmd_workflow_debug",
    "cmd_workflow_refactor",
    "cmd_housekeep",
    "cmd_cleanup",
    "cmd_cost",
    "cmd_deps",
    "cmd_quality",
]