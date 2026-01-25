# L4D Fish Completion Script (V5)
# Provides tab completion for l4-dev CLI commands

function __l4_dev_completion
    set -l cmd
    set -l subcmd
    set -l subsubcmd

    set -l commands "start status retro doctor init reset logs logs-summary logs-errors logs-timeline health resume checkpoints sessions recover telemetry report progress decisions explain workflow housekeep cleanup cost deps quality profile"

    # Main commands
    if test (contains "$commands[1]" $argv[1])
        for cmd in $commands
            if test (contains "$cmd" $argv[2])
                if not test (contains "$subcmd" $argv[3])
                    echo $cmd
                    return
                end
            end
        end

    # Determine subcommand
    set cmd $argv[1]
    set subcmd $argv[2]

    # Main command subcommands
    switch $cmd
        case start
            if test (contains "--interactive" $argv)
                echo "--interactive"
            else if test (contains "--task" $argv)
                echo "--task"
            end
        case status
            if test (contains "-v" $argv)
                echo "-v"
            else if test (contains "--verbose" $argv)
                echo "-v"
            else if test (contains "--watch" $argv)
                echo "--watch"
            else if test (contains "--interval" $argv)
                echo "--interval"
            else if test (contains "--iterations" $argv)
                echo "--iterations"
            end
        case retro
            echo
        case doctor
            echo
        case init
            echo
        case reset
            echo
        case logs
            if test (contains "--level" $argv)
                echo "--level"
            else if test (contains "--module" $argv)
                echo "--module"
            else if test (contains "--operation-id" $argv)
                echo "--operation-id"
            else if test (contains "--task-id" $argv)
                echo "--task-id"
            else if test (contains "--session-id" $argv)
                echo "--session-id"
            else if test (contains "--search" $argv)
                echo "--search"
            else if test (contains "--last" $argv)
                echo "--last"
            else if test (contains "--error" $argv)
                echo "--error"
            else if test (contains "--export" $argv)
                echo "--export"
            else if test (contains "--log-dir" $argv)
                echo "--log-dir"
            end
        case logs-summary
            if test (contains "--level" $argv)
                echo "--level"
            else if test (contains "--module" $argv)
                echo "--module"
            else if test (contains "--operation-id" $argv)
                echo "--operation-id"
            else if test (contains "--task-id" $argv)
                echo "--task-id"
            else if test (contains "--log-dir" $argv)
                echo "--log-dir"
            end
        case logs-errors
            echo "--log-dir"
        case logs-timeline
            echo "--log-dir"
            case health
            if test (contains "-v" $argv)
                echo "-v"
            else if test (contains "--verbose" $argv)
                echo "-v"
            else if test (contains "--fix" $argv)
                echo "--fix"
            else if test (contains "--export" $argv)
                echo "--export"
            end
        case resume
            if test (contains "--session-id" $argv)
                echo "--session-id"
            else if test (contains "--checkpoint-id" $argv)
                echo "--checkpoint-id"
            else if test (contains "--auto" $argv)
                echo "--auto"
            else if test (contains "--force" $argv)
                echo "--force"
            else if test (contains "--dry-run" $argv)
                echo "--dry-run"
            else if test (contains "--start" $argv)
                echo "--start"
            end
        case checkpoints
            if test (contains "list" $subsubcmd)
                if test (contains "--type" $argv)
                    echo "--type"
                else if test (contains "--task-id" $argv)
                    echo "--task-id"
                else if test (contains "--operation-id" $argv)
                    echo "--operation-id"
                else if test (contains "--limit" $argv)
                    echo "--limit"
                end
            else if test (contains "restore" $subsubcmd)
                if test (contains "--id" $argv)
                    echo "--id"
                else if test (contains "--databases" $argv)
                    echo "--databases"
                else if test (contains "--files" $argv)
                    echo "--files"
                else if test (contains "--git" $argv)
                    echo "--git"
                else if test (contains "--cache" $argv)
                    echo "--cache"
                else if test (contains "--no-validate" $argv)
                    echo "--no-validate"
                else if test (contains "--dry-run" $argv)
                    echo "--dry-run"
                else if test (contains "--force" $argv)
                    echo "--force"
                else if test (contains "--start" $argv)
                    echo "--start"
                end
            else if test (contains "delete" $subsubcmd)
                if test (contains "--id" $argv)
                    echo "--id"
                else if test (contains "--force" $argv)
                    echo "--force"
                end
        case sessions
            if test (contains "--status" $argv)
                echo "--status"
            else if test (contains "--limit" $argv)
                echo "--limit"
            end
        case recover
            if test (contains "--dry-run" $argv)
                echo "--dry-run"
            end
        case telemetry
            if test (contains "list" $subsubcmd)
                if test (contains "--type" $argv)
                    echo "--type"
                else if test (contains "--status" $argv)
                    echo "--status"
                else if test (contains "--start" $argv)
                    echo "--start"
                else if test (contains "--end" $argv)
                    echo "--end"
                else if test (contains "--last" $argv)
                    echo "--last"
                else if test (contains "--limit" $argv)
                    echo "--limit"
                else if test (contains "--export" $argv)
                    echo "--export"
                else if test (contains "--format" $argv)
                    echo "--format"
                end
            else if test (contains "show" $subsubcmd)
                echo "--id"
            else if test (contains "--logs" $argv)
                    echo "--logs"
                end
            else if test (contains "export" $subsubcmd)
                if test (contains "--id" $argv)
                    echo "--id"
                else if test (contains "--export" $argv)
                    echo "--export"
                else if test (contains "--format" $argv)
                    echo "--format"
                end
            else if test (contains "stats" $subsubcmd)
                echo "--type"
                end
        case report
            if test (contains "--period" $argv)
                echo "--period"
            else if test (contains "--export" $argv)
                echo "--export"
            end
        case progress
            if test (contains "--task" $argv)
                echo "--task"
            else if test (contains "--task-id" $argv)
                echo "--task-id"
            else if test (contains "--session" $argv)
                echo "--session"
            else if test (contains "--project" $argv)
                echo "--project"
            else if test (contains "--alerts" $argv)
                echo "--alerts"
            end
        case decisions
            if test (contains "--task-id" $argv)
                echo "--task-id"
            else if test (contains "--operation-id" $argv)
                echo "--operation-id"
            else if test (contains "--start" $argv)
                echo "--start"
            else if test (contains "--end" $argv)
                echo "--end"
            else if test (contains "--last" $argv)
                echo "--last"
            else if test (contains "--min-confidence" $argv)
                echo "--min-confidence"
            else if test (contains "--max-confidence" $argv)
                echo "--max-confidence"
            else if test (contains "--action" $argv)
                echo "--action"
            else if test (contains "--outcome" $argv)
                echo "--outcome"
            else if test (contains "--context-key" $argv)
                echo "--context-key"
            else if test (contains "--context-value" $argv)
                echo "--context-value"
            else if test (contains "--reasoning" $argv)
                echo "--reasoning"
            else if test (contains "--limit" $argv)
                echo "--limit"
            else if test (contains "--export" $argv)
                echo "--export"
            else if test (contains "--stats" $argv)
                echo "--stats"
            end
        case explain
            if test (contains "--id" $argv)
                echo "--id"
            else if test (contains "--last" $argv)
                echo "--last"
            else if test (contains "--tree" $argv)
                echo "--tree"
            else if test (contains "--reasoning" $argv)
                echo "--reasoning"
            else if test (contains "--key" $argv)
                echo "--key"
            else if test (contains "--heatmap" $argv)
                echo "--heatmap"
            else if test (contains "--operation-id" $argv)
                echo "--operation-id"
            else if test (contains "--task-id" $argv)
                echo "--task-id"
            else if test (contains "--max-depth" $argv)
                echo "--max-depth"
            else if test (contains "--confidence-threshold" $argv)
                echo "--confidence-threshold"
            else if test (contains "--limit" $argv)
                echo "--limit"
            else if test (contains "--confidence" $argv)
                echo "--confidence"
            else if test (contains "--alternatives" $argv)
                echo "--alternatives"
            else if test (contains "--context" $argv)
                echo "--context"
            else if test (contains "--metric" $argv)
                echo "--metric"
            else if test (contains "--export" $argv)
                echo "--export"
            else if test (contains "--format" $argv)
                echo "--format"
            end
        case workflow
            if test (contains "simple" $subsubcmd)
                if test (contains "--task" $argv)
                    echo "--task"
                end
            else if test (contains "complex" $subsubcmd)
                if test (contains "--task" $argv)
                    echo "--task"
                end
            else if test (contains "debug" $subsubcmd)
                if test (contains "--test-path" $argv)
                    echo "--test-path"
                end
            else if test (contains "refactor" $subsubcmd)
                if test (contains "--file" $argv)
                    echo "--file"
                end
            end
        case housekeep
            if test (contains "--dry-run" $argv)
                echo "--dry-run"
            else if test (contains "--auto" $argv)
                echo "--auto"
            else if test (contains "--confirm" $argv)
                echo "--confirm"
            end
        case cleanup
            if test (contains "--dry-run" $argv)
                echo "--dry-run"
            else if test (contains "--auto" $argv)
                echo "--auto"
            else if test (contains "--policy" $argv)
                echo "--policy"
            end
        case cost
            if test (contains "--report" $argv)
                echo "--report"
            else if test (contains "--by-task" $argv)
                echo "--by-task"
            else if test (contains "--by-session" $argv)
                echo "--by-session"
            else if test (contains "--trend" $argv)
                echo "--trend"
            else if test (contains "--predict" $argv)
                echo "--predict"
            end
        case deps
            if test (contains "--unused" $argv)
                echo "--unused"
            else if test (contains "--outdated" $argv)
                echo "--outdated"
            else if test (contains "--cleanup" $argv)
                echo "--cleanup"
            end
        case quality
            if test (contains "--report" $argv)
                echo "--report"
            else if test (contains "--trend" $argv)
                echo "--trend"
            end
        case profile
            if test (contains "list" $subsubcmd)
                echo
            else if test (contains "show" $subsubcmd)
                if test (contains "--profile" $argv)
                    echo "--profile"
                end
            else if test (contains "use" $subsubcmd)
                if test (contains "--profile" $argv)
                    echo "--profile"
                end
            else if test (contains "diff" $subsubcmd)
                if test (contains "--profile1" $argv)
                    echo "--profile1"
                else if test (contains "--profile2" $argv)
                    echo "--profile2"
                end
            end
    end
end

complete -F -c __l4_dev_completion l4-dev