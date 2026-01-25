#!/bin/bash
# L4D Bash Completion Script (V5)
# Provides tab completion for l4-dev CLI commands

_l4_dev_completion() {
    local cur prev words cword
    COMPREPLY=()

    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"
    words="${COMP_WORDS[@]}"

    # Main commands
    if [[ ${cur} == "l4-dev" ]] || [[ ${cur} == "l4" ]]; then
        COMPREPLY=($(compgen -W "start status retro doctor init reset logs logs-summary logs-errors logs-timeline health resume checkpoints sessions recover telemetry report progress decisions explain workflow housekeep cleanup cost deps quality profile" -- "${words[@]}"))
        return 0
    fi

    # Determine subcommand
    case "${prev}" in
        start|status|retro|doctor|init|reset|logs|logs-summary|logs-errors|logs-timeline|health|resume|checkpoints|sessions|recover|telemetry|report|progress|decisions|explain)
            # Subcommand arguments
            case "${cur}" in
                --*)
                    # Option completion
                    case "${prev}" in
                        start)
                            COMPREPLY=($(compgen -W "interactive task" -- "${words[@]}"))
                            ;;
                        status)
                            COMPREPLY=($(compgen -W "verbose watch interval iterations" -- "${words[@]}"))
                            ;;
                        logs)
                            COMPREPLY=($(compgen -W "level module operation-id task-id session-id search last error export log-dir" -- "${words[@]}"))
                            ;;
                        report)
                            COMPREPLY=($(compgen -W "period export" -- "${words[@]}"))
                            ;;
                        progress)
                            COMPREPLY=($(compgen -W "task task-id session project alerts" -- "${words[@]}"))
                            ;;
                        decisions)
                            COMPREPLY=($(compgen -W "task-id operation-id start end last min-confidence max-confidence action outcome context-key context-value reasoning limit export stats" -- "${words[@]}"))
                            ;;
                        explain)
                            COMPREPLY=($(compgen -W "id last tree reasoning key heatmap operation-id task-id max-depth confidence-threshold limit confidence alternatives context metric export format" -- "${words[@]}"))
                            ;;
                        profile)
                            COMPREPLY=($(compgen -W "list show use diff" -- "${words[@]}"))
                            ;;
                        workflow)
                            COMPREPLY=($(compgen -W "simple complex debug refactor" -- "${words[@]}"))
                            ;;
                        housekeep)
                            COMPREPLY=($(compgen -W "dry-run auto confirm" -- "${words[@]}"))
                            ;;
                        cleanup)
                            COMPREPLY=($(compgen -W "dry-run auto policy" -- "${words[@]}"))
                            ;;
                        cost)
                            COMPREPLY=($(compgen -W "report by-task by-session trend predict" -- "${words[@]}"))
                            ;;
                        deps)
                            COMPREPLY=($(compgen -W "unused outdated cleanup" -- "${words[@]}"))
                            ;;
                        quality)
                            COMPREPLY=($(compgen -W "report trend" -- "${words[@]}"))
                            ;;
                    esac
                    ;;
            esac
            ;;
        
        # Checkpoints subcommand
        checkpoints)
            case "${cur}" in
                list)
                    COMPREPLY=($(compgen -W "type task-id operation-id limit" -- "${words[@]}"))
                    ;;
                restore)
                    COMPREPLY=($(compgen -W "id databases files git cache no-validate dry-run force start" -- "${words[@]}"))
                    ;;
                delete)
                    COMPREPLY=($(compgen -W "id force" -- "${words[@]}"))
                    ;;
            esac
            ;;
        
        # Telemetry subcommand
        telemetry)
            case "${cur}" in
                list)
                    COMPREPLY=($(compgen -W "type status start end last export format limit" -- "${words[@]}"))
                    ;;
                show)
                    COMPREPLY=($(compgen -W "id logs" -- "${words[@]}"))
                    ;;
                export)
                    COMPREPLY=($(compgen -W "id export format" -- "${words[@]}"))
                    ;;
                stats)
                    COMPREPLY=($(compgen -W "type" -- "${words[@]}"))
                    ;;
            esac
            ;;
        
        # Profile subcommand
        profile)
            case "${cur}" in
                list|show|use|diff)
                    # Profile names completion
                    if [[ ${cur} == "--profile" ]]; then
                        COMPREPLY=($(compgen -W "minimal balanced max" -- "${words[@]}"))
                    elif [[ ${cur} == "--profile1" ]]; then
                        COMPREPLY=($(compgen -W "minimal balanced max" -- "${words[@]}"))
                    elif [[ ${cur} == "--profile2" ]]; then
                        COMPREPLY=($(compgen -W "minimal balanced max" -- "${words[@]}"))
                    fi
                    ;;
            esac
            ;;
        
        # Workflow subcommand
        workflow)
            case "${cur}" in
                simple|complex|debug|refactor)
                    case "${cur}" in
                        --task)
                            COMPREPLY=($(compgen -W "Add feature Fix bug Refactor code Run tests" -- "${words[@]}"))
                            ;;
                        --test-path)
                            COMPREPLY=($(compgen -W "test_*.py" -- "${words[@]}"))
                            ;;
                        --file)
                            COMPREPLY=($(compgen -W "*.py" -- "${words[@]}"))
                            ;;
                    esac
                    ;;
            esac
            ;;
    esac

    return 0
}

complete -F _l4_dev_completion l4-dev