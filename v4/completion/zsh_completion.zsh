# L4D ZSH Completion Script (V5)
# Provides tab completion for l4-dev CLI commands

#compdef __l4_dev_completion
#   _l4_dev_completion()
#
#   Description: Completion function for l4-dev commands
#
#   Arguments:
#     $1 - The command word being completed
#     $2 - The current word in the command line
#     $3 - The previous word in the command line
#
#   Description: Generates completion suggestions based on command context

__l4_dev_completion() {
    local -a commands
    commands=(
        'start:Initiate orchestration loop'
        'status:Show comprehensive status dashboard'
        'retro:Trigger a retrospective on manual changes'
        'doctor:Verify environment and dependencies'
        'init:Initialize project root'
        'reset:Reset all databases'
        'logs:Search and analyze logs'
        'logs-summary:Generate log summary statistics'
        'logs-errors:Show error patterns'
        'logs-timeline:Generate operation timeline'
        'health:Run health checks on system components'
        'resume:Resume a previous session'
        'checkpoints:Manage system checkpoints'
        'sessions:List available sessions'
        'recover:Interactive recovery wizard'
        'telemetry:Query and analyze telemetry data'
        'report:Generate analytics reports'
        'progress:Display progress visualization'
        'decisions:Query and search decision history'
        'explain:Explain and visualize decisions'
        'workflow:Run predefined workflows (V5)'
        'housekeep:Automatic housekeeping and cleanup (V5)'
        'cleanup:Clean up old data (V5)'
        'cost:Track and report LLM costs (V5)'
        'deps:Analyze and manage dependencies (V5)'
        'quality:Track context quality (V5)'
        'profile:Manage configuration profiles (V5)'
    )

    # Main command completion
    if [[ ${CURRENT} == "l4-dev" ]]; then
        _describe -V commands
        return
    fi

    # Subcommand completion
    local -a subcmds subcmd_desc subcmd_action
    case $words[1] in
        start)
            subcmds=('interactive' 'task')
            subcmd_desc=('Run in interactive mode' 'Describe task to work on')
            subcmd_action=('--interactive' '--task')
            ;;
        status)
            subcmds=('verbose' 'watch' 'interval' 'iterations')
            subcmd_desc=('Show detailed information' 'Auto-refresh dashboard' 'Refresh interval' 'Maximum refreshes')
            subcmd_action=('-v' '--watch' '--interval' '--iterations')
            ;;
        logs)
            subcmds=('level' 'module' 'operation-id' 'task-id' 'session-id' 'search' 'last' 'error' 'export' 'log-dir')
            subcmd_desc=('Filter by log level' 'Filter by module name' 'Filter by operation ID' 'Filter by task ID' 'Filter by session ID' 'Full-text search' 'Time range' 'Only show error entries' 'Export to file' 'Log directory')
            subcmd_action=('--level' '--module' '--operation-id' '--task-id' '--session-id' '--search' '--last' '--error' '--export' '--log-dir')
            ;;
        report)
            subcmds=('period' 'export')
            subcmd_desc=('Report period' 'Export report to JSON file')
            subcmd_action=('--period' '--export')
            ;;
        progress)
            subcmds=('task' 'task-id' 'session' 'project' 'alerts')
            subcmd_desc=('Show task progress' 'Show progress for specific task ID' 'Show session progress' 'Show project progress' 'Show progress alerts')
            subcmd_action=('--task' '--task-id' '--session' '--project' '--alerts')
            ;;
        decisions)
            subcmds=('task-id' 'operation-id' 'start' 'end' 'last' 'min-confidence' 'max-confidence' 'action' 'outcome' 'context-key' 'context-value' 'reasoning' 'limit' 'export' 'stats')
            subcmd_desc=('Filter by task ID' 'Filter by operation ID' 'Start time (ISO format)' 'End time (ISO format)' 'Time range' 'Minimum confidence threshold' 'Maximum confidence threshold' 'Filter by action pattern' 'Filter by outcome' 'Search by context key' 'Search by context value' 'Search reasoning by keyword' 'Maximum number to show' 'Export to file' 'Show decision statistics')
            subcmd_action=('--task-id' '--operation-id' '--start' '--end' '--last' '--min-confidence' '--max-confidence' '--action' '--outcome' '--context-key' '--context-value' '--reasoning' '--limit' '--export' '--stats')
            ;;
        explain)
            subcmds=('id' 'last' 'tree' 'reasoning' 'key' 'heatmap' 'operation-id' 'task-id' 'max-depth' 'confidence-threshold' 'limit' 'confidence' 'alternatives' 'context' 'metric' 'export' 'format')
            subcmd_desc=('Decision ID to explain' 'Show last N decisions' 'Display decision tree visualization' 'Display reasoning chain for a decision' 'Display key decisions' 'Display decision heatmap' 'Filter by operation ID' 'Filter by task ID' 'Maximum depth for decision tree' 'Minimum confidence for key decisions' 'Maximum decisions to display' 'Show confidence scores' 'Show considered alternatives' 'Show context in reasoning steps' 'Metric for heatmap' 'Export decisions to file' 'Export format')
            subcmd_action=('--id' '--last' '--tree' '--reasoning' '--key' '--heatmap' '--operation-id' '--task-id' '--max-depth' '--confidence-threshold' '--limit' '--confidence' '--alternatives' '--context' '--metric' '--export' '--format')
            ;;
        profile)
            subcmds=('list' 'show' 'use' 'diff' '--profile' '--profile1' '--profile2')
            subcmd_desc=('List all available profiles' 'Show details of a specific profile' 'Switch to a different profile' 'Compare two configuration profiles' 'Profile name to show' 'Profile name to switch to' 'First profile to compare' 'Second profile to compare')
            subcmd_action=('list' 'show' 'use' 'diff' '--profile' '--profile1' '--profile2')
            ;;
        workflow)
            case $words[2] in
                simple|complex|debug|refactor)
                    subcmds=('task' 'test-path' 'file')
                    subcmd_desc=('Feature description' 'Path to failing test' 'File to refactor')
                    subcmd_action=('--task' '--test-path' '--file')
                    ;;
            esac
            ;;
        housekeep)
            subcmds=('dry-run' 'auto' 'confirm')
            subcmd_desc=('Preview deletions without making changes' 'Automatic safe deletion without confirmation' 'Require confirmation for each deletion')
            subcmd_action=('--dry-run' '--auto' '--confirm')
            ;;
        cleanup)
            subcmds=('dry-run' 'auto' 'policy')
            subcmd_desc=('Preview cleanup without making changes' 'Automatic cleanup without confirmation' 'Path to cleanup policy JSON file')
            subcmd_action=('--dry-run' '--auto' '--policy')
            ;;
        cost)
            subcmds=('report' 'by-task' 'by-session' 'trend' 'predict')
            subcmd_desc=('Show comprehensive cost report' 'Show cost per task' 'Show cost per session' 'Show cost trends over time' 'Predict future costs')
            subcmd_action=('--report' '--by-task' '--by-session' '--trend' '--predict')
            ;;
        deps)
            subcmds=('unused' 'outdated' 'cleanup')
            subcmd_desc=('Show unused dependencies' 'Show outdated dependencies' 'Safe removal of unused dependencies')
            subcmd_action=('--unused' '--outdated' '--cleanup')
            ;;
        quality)
            subcmds=('report' 'trend')
            subcmd_desc=('Show quality report' 'Show quality trends over time')
            subcmd_action=('--report' '--trend')
            ;;
        checkpoints)
            case $words[2] in
                list)
                    subcmds=('type' 'task-id' 'operation-id' 'limit')
                    subcmd_desc=('Filter by snapshot type' 'Filter by task ID' 'Filter by operation ID' 'Maximum number to show')
                    subcmd_action=('--type' '--task-id' '--operation-id' '--limit')
                    ;;
                restore)
                    subcmds=('id' 'databases' 'files' 'git' 'cache' 'no-validate' 'dry-run' 'force' 'start')
                    subcmd_desc=('Checkpoint ID to restore' 'Restore database state' 'Restore file system state' 'Restore git state' 'Restore cache state' 'Skip validation' 'Preview restore without making changes' 'Force restore without confirmation' 'Start orchestrator after restore')
                    subcmd_action=('--id' '--databases' '--files' '--git' '--cache' '--no-validate' '--dry-run' '--force' '--start')
                    ;;
                delete)
                    subcmds=('id' 'force')
                    subcmd_desc=('Checkpoint ID to delete' 'Delete without confirmation')
                    subcmd_action=('--id' '--force')
                    ;;
            esac
            ;;
        telemetry)
            case $words[2] in
                list)
                    subcmds=('type' 'status' 'start' 'end' 'last' 'export' 'format' 'limit')
                    subcmd_desc=('Filter by operation type' 'Filter by status' 'Start time (ISO format)' 'End time (ISO format)' 'Time range' 'Export to file' 'Export format' 'Maximum number to show')
                    subcmd_action=('--type' '--status' '--start' '--end' '--last' '--export' '--format' '--limit')
                    ;;
                show)
                    subcmds=('id' 'logs')
                    subcmd_desc=('Operation ID to show' 'Include associated logs')
                    subcmd_action=('--id' '--logs')
                    ;;
                export)
                    subcmds=('id' 'export' 'format')
                    subcmd_desc=('Operation ID to export' 'Output file path' 'Export format')
                    subcmd_action=('--id' '--export' '--format')
                    ;;
                stats)
                    subcmds=('type')
                    subcmd_desc=('Filter by operation type')
                    subcmd_action=('--type')
                    ;;
            esac
            ;;
        sessions)
            subcmds=('status' 'limit')
            subcmd_desc=('Filter by session status' 'Maximum number to show')
            subcmd_action=('--status' '--limit')
            ;;
        recover)
            subcmds=('dry-run')
            subcmd_desc=('Preview recovery without making changes')
            subcmd_action=('--dry-run')
            ;;
    esac

    _describe -V -t subcmd_desc -a subcmds
}

# Register completion function
compdef __l4_dev_completion __l4_dev_completion