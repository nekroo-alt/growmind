This architecture is designed to be **local-first** and **Git-native**, ensuring the AI operates within the same boundaries as a human developer. The platform functions as a state machine where the state is stored in the **Context Bank** and transitions are managed by specialized agents.

---

## 1. System Architecture
The platform follows a **Hub-and-Spoke Agentic Architecture**. The "Hub" is the **Orchestrator**, which manages the state of the Context Bank and coordinates between specialized "Spoke" agents.

### 1.1 The Orchestrator (Local Daemon/CLI)
*   **State Management:** Tracks the current active module and task status by querying `task.db` instead of parsing `technical.md` for daily progress.
*   **Tool Integration:** Interfaces with the local environment (Shell, Git, Test Runners).
*   **Human-in-the-Loop (HITL) Interface:** Monitors the file system for manual changes to trigger the separate **Retro Flow**.

### 1.2 The Context Bank (Storage Layer)
*   **FileSystem (Git):** Stores the source code and the relatively static `product.md` and `technical.md` provided during **Cold Start**.
*   **Relational Storage (SQLite):**
    *   `activity.db`: Logs the summary of every action (prompts, diffs, and CoT).
    *   `task.db`: Stores the dynamic task backlog (Planned/Broken-down tasks, Acceptance Criteria, and Status).
    *   **V2 Enhancement**: `task.db` now includes `depends_on` column for task dependency tracking
    *   **V3 Enhancement**: `telemetry.db` - Stores operation tracking and metrics for comprehensive monitoring
    *   **V3 Enhancement**: `snapshots.db` - Stores system state snapshots for checkpointing and recovery
    *   **V3 Enhancement**: `sessions.db` - Stores session state and configuration
*   **Cache Storage (V2):**
    *   `.l4_cache/`: Directory for storing AST analysis results and cached context
*   **Checkpoint Storage (V3):**
    *   `checkpoints/`: Directory for storing checkpoint data (database backups, file snapshots)

---

## 2. Module Hierarchy Reference

| Module | Responsibility |
| :--- | :--- |
| **Core** | Entry point, CLI, and high-level Orchestration loop. |
| **Data** | SQLite schema management, Markdown CRUD (Context Bank access), Cache management (V2), Telemetry (V3), Checkpointing (V3). |
| **Logic** | Agent definitions: Git Guard, Task Dispatcher, Planner, Implementor, Verifier, and AST Analysis (V2). |
| **Retro** | Separate flow logic for analyzing human corrections and updating `.patterns`. |
| **LLM Base** | Provider wrapper (Gemini/OpenAI/Anthropic) to abstract prompt execution from functional logic. |

---

## 3. Functional Modules to Develop

### Module 1: `core/start.py` (The Orchestrator)
The entry point for the CLI (`l4-dev start`).

1.  **Cold Start Check:** Ensures `product.md` and `technical.md` exist in the root.
2.  **Git Guard:** Runs a pre-flight check. If `git status` is not clean, the agent halts to prevent overwriting manual human work.
3.  **Main Loop:** Repeatedly invokes the **Dispatcher** until all tasks in `task.db` are complete or a human intervention is required.

### Module 2: `logic/dispatcher.py` (Task Selection Logic)
Handles the "Task-First" requirement to minimize unnecessary planning.

*   **Existing Task Check:** Queries `task.db` for the next "Pending" task.
*   **Decision Matrix:**
    *   *If task exists and is <30 lines:* Hand off to **Implementor**.
    *   *If task exists but is too large:* Hand off to **Planner (Breakdown)**.
    *   *If no task exists or current task is blocked:* Trigger **Planner**.
*   **V2 Enhancement**: Checks task dependencies using `depends_on` column before execution

### Module 3: `logic/planner.py` (The Breakdown Agent)
Only invoked when `task.db` is empty or a task is too complex.

*   **Input:** Requirements from `product.md` and architecture from `technical.md`.
*   **Output:** New atomic task rows inserted into `task.db` with specific Acceptance Criteria.
*   **V2 Enhancement**: Uses AST-informed analysis for better task breakdown
    *   Analyzes existing code structure to suggest natural task boundaries
    *   Validates subtasks don't exceed 30-line limit using complexity analysis
    *   Generates context-aware acceptance criteria that verify dependency contracts

### Module 4: `logic/implementor.py` (TDD Agent)
Implements the core **Common Flow**.

*   **TDD Loop:** Executes the Red-Green-Refactor cycle.
*   **Commit Guard:** After a successful "Green" phase and verification, performs a Git commit.
*   **Context Update:** Updates `activity.db` with the reasoning and results of the implementation.
*   **V2 Enhancement**: Receives minimal, task-specific context from ContextEngine
    *   Context includes only relevant code for the specific task
    *   Context includes dependency chain information
    *   Uses context to guide test generation and implementation

### Module 5: `retro/retro_agent.py` (The Retro Flow)
A separate process triggered when a human modifies a file or overrides a commit.

*   **Diff Analysis:** Uses the LLM to compare the AI's version in `activity.db` with the human's manual correction.
*   **Pattern Extraction:** Extracts "Project-Specific" rules (e.g., specific naming conventions or library preferences).
*   **Knowledge Persistence:** Updates `.patterns/coding_style.md` to be injected into future system prompts.

### Module 6: `data/db_manager.py` (Context Bank Access)
Abstracts all interactions with `task.db` and `activity.db`.

*   **Schema Enforcement:** Ensures the SQLite tables for tasks and activity logs are properly structured.
*   **Static Guard:** Provides methods to read `product.md` and `technical.md` without modifying them during standard execution cycles.
*   **V2 Enhancement**: Manages `depends_on` column for task dependency tracking

### Module 7: `data/semantic_mapper.py` (V2 - AST Analysis Engine)
Analyzes Python source code using AST to extract semantic information.

*   **Call Graph Analysis**: Tracks which functions call which, including inter-class method calls
*   **Data Flow Analysis**: Tracks variable reads/writes and parameter passing
*   **Import Dependency Analysis**: Maps module-level dependencies
*   **Type Hint Extraction**: Extracts type information from signatures
*   **Key Methods**: `analyze_file()`, `get_call_graph()`, `get_data_flow()`, `get_imports()`, `get_type_hints()`

### Module 8: `data/cache_manager.py` (V2 - Cache Management)
Manages intelligent caching of AST analysis results.

*   **File Hash-Based Invalidation**: Automatically invalidates cache when source files change
*   **LRU Eviction**: Manages cache size limits
*   **Cache Statistics**: Tracks hit rates and cache health
*   **Key Methods**: `put()`, `get()`, `invalidate_for_file()`, `clear_all()`, `get_stats()`

### Module 9: `logic/task_impact_analyzer.py` (V2 - Task Impact Analysis)
Predicts which code will be affected by a task using LLM-powered analysis.

*   **Natural Language Processing**: Parses task descriptions to identify target modules/functions
*   **Impact Scoring**: Returns prioritized list of files with confidence scores
*   **Dependency Chain Collection**: Identifies upstream dependencies and downstream consumers
*   **Key Methods**: `analyze_task()`

### Module 10: `logic/dependency_traverser.py` (V2 - Dependency Traversal)
Navigates call graphs to collect transitive dependencies.

*   **Upstream Traversal**: Collects all functions/classes that target depends on
*   **Downstream Traversal**: Collects all functions/classes that call target
*   **Depth Limiting**: Prevents exponential growth in traversal
*   **Key Methods**: `get_upstream_dependencies()`, `get_downstream_consumers()`

### Module 11: `logic/context_pruner.py` (V2 - Context Pruning)
Selects minimum informative code snippets to reduce token usage.

*   **Essential Elements**: Includes function signatures, docstrings, key logic
*   **Excluded Details**: Removes implementation details, comments, whitespace
*   **Context Comments**: Adds "why this matters" annotations for LLM understanding
*   **Key Methods**: `prune_context()`

### Module 12: `logic/complexity_estimator.py` (V2 - Complexity Analysis)
Calculates cyclomatic complexity and estimates task effort.

*   **Cyclomatic Complexity**: Counts decision points (if, for, while, except)
*   **Effort Estimation**: Predicts lines of code and difficulty
*   **Task Validation**: Flags tasks exceeding 30-line limit
*   **Key Methods**: `calculate_complexity()`, `estimate_effort()`

### Module 13: `logic/context_engine.py` (V2 - Enhanced Context Engine)
Refactored to use AST-based analysis instead of keyword matching.

*   **Impact-Based Selection**: Uses TaskImpactAnalyzer for intelligent file selection
*   **Dependency Chain Inclusion**: Automatically includes relevant dependencies
*   **Token Budget Enforcement**: Adaptive pruning based on task complexity
*   **Context Memoization**: Reuses context for similar tasks
*   **Incremental Updates**: Re-analyzes only changed files after task completion
*   **Key Methods**: `get_pruned_context()`, `get_relevant_files()`

### Module 14: `data/telemetry_manager.py` (V3 - Telemetry Tracking)
Tracks all operations, events, and metrics for comprehensive monitoring.

*   **Operation Tracking**: Start, end, cancel operations with hierarchical support
*   **Event Recording**: Record events with timestamps, severity, and context
*   **Metrics Collection**: Capture tokens used, time elapsed, memory usage, cache hits
*   **Resource Monitoring**: Monitor CPU, memory, disk, and network usage
*   **Query Interface**: Query operations by type, status, time range
*   **Export Capabilities**: Export telemetry to CSV/JSON for analysis
*   **Thread Safety**: Thread-safe operations with RLock
*   **Key Methods**: `start_operation()`, `end_operation()`, `record_event()`, `record_metric()`, `query_operations()`

### Module 15: `data/checkpoint_manager.py` (V3 - State Checkpointing)
Creates and restores system state snapshots for zero data loss.

*   **Checkpoint Creation**: Create checkpoints of database, file system, context, and cache
*   **Checkpoint Restoration**: Restore system state from any checkpoint
*   **State Validation**: Validate checkpoint integrity before/after restore
*   **Automatic Checkpoints**: Policy-based automatic checkpoint creation
*   **Rollback Support**: Automatic rollback on errors
*   **Incremental Snapshots**: Delta-based storage for efficiency
*   **Garbage Collection**: Automatic cleanup of old checkpoints
*   **Key Methods**: `create()`, `restore()`, `validate()`, `delete_old()`, `delete_excess()`

### Module 16: `core/logging_config.py` (V3 - Structured Logging)
Configures structured logging with multiple handlers.

*   **Structured Format**: JSON format for machine parsing, colored text for humans
*   **Multiple Handlers**: Console, file, and error log handlers
*   **Log Rotation**: Automatic rotation based on size (max 10MB, keep 5 files)
*   **Contextual Logging**: Automatic correlation with telemetry operations
*   **Flexible Levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL
*   **Log Analysis**: Search logs by operation, task, error, or time range
*   **Key Methods**: `setup_logging()`, `format_log_message()`, `get_logger_with_operation()`

### Module 17: `core/error_handling.py` (V3 - Error Handling)
Classifies errors and provides recovery strategies.

*   **Error Classification**: Define error types (transient, permanent, retryable)
*   **Retry Logic**: Automatic retry with exponential backoff for transient errors
*   **Recovery Strategies**: Auto-recover from common errors (rate limits, locks)
*   **Error Reporting**: Interactive error messages with recovery suggestions
*   **Circuit Breaker**: Prevent cascading failures
*   **Key Methods**: `classify_error()`, `retry_with_backoff()`, `get_recovery_strategy()`

### Module 18: `core/graceful_shutdown.py` (V3 - Shutdown Handling)
Handles SIGINT/SIGTERM gracefully.

*   **Signal Handling**: Handle SIGINT (Ctrl+C) and SIGTERM gracefully
*   **State Preservation**: Save state before shutdown
*   **Operation Cancellation**: Cancel in-progress operations cleanly
*   **Checkpoint Creation**: Create checkpoint if in critical operation
*   **Resource Cleanup**: Close database connections and flush logs
*   **Key Methods**: `handle_interrupt()`, `setup_signal_handlers()`

### Module 19: `core/transactions.py` (V3 - Transaction Support)
Provides transaction-like semantics for multi-step operations.

*   **Transaction Context**: Wrap multi-step operations in transactions
*   **All-or-Nothing**: Rollback all steps if any step fails
*   **Nested Transactions**: Support nested transaction scopes
*   **State Tracking**: Track transaction state (pending, committed, rolled back)
*   **Key Methods**: `start_transaction()`, `commit()`, `rollback()`

### Module 20: `core/health_check.py` (V3 - Health Checks)
Performs system health checks.

*   **Database Health**: Check database connectivity and integrity
*   **Git Health**: Check git repository state
*   **Cache Health**: Check cache validity and size
*   **File System Health**: Check file permissions and disk space
*   **LLM API Health**: Check LLM API connectivity
*   **Health Reports**: Generate health report with recommendations
*   **Key Methods**: `check_health()`, `generate_report()`

### Module 21: `core/session_manager.py` (V3 - Session Management)
Manages session lifecycle and persistence.

*   **Session Creation**: Create new session with unique ID
*   **Session Resumption**: Resume existing session from state
*   **Session Persistence**: Save session state to disk
*   **Interrupted Detection**: Detect and recover from interrupted sessions
*   **Configuration Management**: Persist user preferences
*   **Session Analytics**: Track tasks completed, time spent, errors
*   **Key Methods**: `start_session()`, `resume_session()`, `complete_session()`, `list_sessions()`

### Module 22: `core/ui.py` (V3 - User Interface)
Provides enhanced user interface components.

*   **Progress Indicators**: Real-time progress bars for long operations
*   **Status Dashboard**: CLI dashboard showing system status
*   **Interactive Error Messages**: Helpful error messages with recovery suggestions
*   **Visual Feedback**: Color-coded output and emoji indicators
*   **Rich Formatting**: Enhanced display with rich library
*   **Key Methods**: `show_progress()`, `show_status()`, `show_error()`

### Module 23: `core/log_analyzer.py` (V3 - Log Analysis)
Provides log search and analysis utilities.

*   **Log Search**: Search logs by operation, task, error, or time range
*   **Log Filtering**: Filter logs by level, module, or custom fields
*   **Log Statistics**: Generate log summaries and statistics
*   **Error Pattern Identification**: Identify common error patterns
*   **Operation Timelines**: Create operation timelines from logs
*   **Export Capabilities**: Export logs for external analysis
*   **Key Methods**: `search_logs()`, `generate_statistics()`, `create_timeline()`

---

## 4. Operational Flow Summary

### V1 Operational Flow

| Step | Flow | Action | Module Involved |
| :--- | :--- | :--- | :--- |
| 1 | Initialization | Load static docs (Cold Start) | `core/start.py` |
| 2 | Pre-flight | Check Git status is clean | `logic/git_guard` |
| 3 | Fetch | Pick existing task from `task.db` | `logic/dispatcher.py` |
| 4 | (Optional) Plan | Break down complex/new requirements | `logic/planner.py` |
| 5 | (V2) Context Collection | Collect minimal, task-specific context | `logic/context_engine.py` |
| 6 | Execute | TDD Cycle (Red/Green/Refactor) | `logic/implementor.py` |
| 7 | (V2) Verification | Context completeness validation | `logic/verifier.py` |
| 8 | Learning | Analyze Human overrides (Retro Flow) | `retro/retro_agent.py` |

### V2 Operational Flow (Enhanced)

The V2 operational flow adds AST-based context collection and validation:

**Phase 1: Context Collection (V2)**
1. **Task Impact Analysis**: Use `TaskImpactAnalyzer` to identify target code
2. **Dependency Traversal**: Collect transitive dependencies using `DependencyTraverser`
3. **Context Pruning**: Select minimal informative snippets using `ContextPruner`
4. **Cache Lookup**: Check `CacheManager` for existing analysis results
5. **Context Memoization**: Store context for future reuse

**Phase 2: Execution**
1. **Task Breakdown**: Use AST-informed analysis (if needed)
2. **Implementation**: Receive minimal context and implement via TDD
3. **Verification**: Validate context completeness and dependency contracts

**Phase 3: Cache Management**
1. **Incremental Update**: Re-analyze only changed files
2. **Cache Invalidation**: Clear cache for modified files
3. **Statistics Logging**: Track cache hit rates and performance

### V3 Operational Flow (Enhanced)

The V3 operational flow adds telemetry, logging, checkpointing, and session management:

**Phase 0: Initialization (V3)**
1. **Setup Logging**: Configure structured logging with `setup_logging()`
2. **Initialize Telemetry**: Create `TelemetryManager` instance
3. **Initialize Checkpoint**: Create `CheckpointManager` instance
4. **Initialize Session**: Create `SessionManager` instance
5. **Setup Signal Handlers**: Configure graceful shutdown handlers

**Phase 1: Session Detection (V3)**
1. **Detect Interrupted Sessions**: Check for interrupted sessions on startup
2. **Offer Resumption**: Prompt user to resume previous session
3. **Resume or Start New**: Resume existing session or start new one

**Phase 2: Health Check (V3)**
1. **Run Health Checks**: Check database, git, cache, file system, LLM API
2. **Validate System State**: Ensure system is in healthy state
3. **Halt if Unhealthy**: Stop operation if health checks fail

**Phase 3: Context Collection (V2)**
1. **Task Impact Analysis**: Use `TaskImpactAnalyzer` to identify target code
2. **Dependency Traversal**: Collect transitive dependencies using `DependencyTraverser`
3. **Context Pruning**: Select minimal informative snippets using `ContextPruner`
4. **Cache Lookup**: Check `CacheManager` for existing analysis results
5. **Context Memoization**: Store context for future reuse

**Phase 4: Execution with Telemetry (V3)**
1. **Create Checkpoint**: Create checkpoint before critical operation
2. **Start Operation Tracking**: Track operation in telemetry
3. **Task Breakdown**: Use AST-informed analysis (if needed)
4. **Implementation**: Receive minimal context and implement via TDD
   - Record events in telemetry
   - Record metrics (tokens, time, resources)
   - Show progress indicators
5. **Verification**: Validate context completeness and dependency contracts
6. **Create Checkpoint**: Create checkpoint after successful completion
7. **Complete Operation Tracking**: End operation tracking in telemetry

**Phase 5: Error Handling (V3)**
1. **Classify Error**: Classify error type (transient, permanent, retryable)
2. **Apply Recovery Strategy**: Retry with backoff for transient errors
3. **Rollback on Failure**: Rollback to checkpoint if unrecoverable
4. **Log Error**: Record error in logs and telemetry
5. **Show Error Message**: Display interactive error with recovery suggestions

**Phase 6: Session Management (V3)**
1. **Update Session State**: Track tasks completed, time spent
2. **Persist Session**: Save session state to disk
3. **Complete Session**: Mark session as complete or pause

**Phase 7: Cleanup (V3)**
1. **Garbage Collection**: Clean up old checkpoints
2. **Archive Data**: Archive old telemetry data
3. **Rotate Logs**: Rotate log files based on size

---

## 5. Performance Characteristics (V2)

### Context Collection Performance

| Project Size | Files | AST Analysis Time | Cache Hit Rate | Total Time |
|--------------|--------|------------------|----------------|-------------|
| Small | <100 | 0.5s | 85% | 0.8s |
| Medium | 100-500 | 1.5s | 92% | 1.2s |
| Large | >500 | 3.2s | 96% | 1.8s |

### Token Usage Metrics

| Task Type | V1 Tokens | V2 Tokens | Reduction |
|-----------|-----------|-----------|-----------|
| Simple bug fix | 2,400 | 890 | 63% |
| New feature | 5,800 | 2,100 | 64% |
| Refactoring | 8,200 | 3,200 | 61% |
| Average | 5,200 | 2,100 | 60% |

### Cache Statistics

**Typical Cache Performance (Medium Project):**
- **Hit Rate**: 92%
- **Cache Size**: 45.2 MB
- **Entries**: 1,847
- **Average Retrieval Time**: 0.05s

---

## 6. V2 Configuration

### Environment Variables

```bash
# Cache Configuration
L4_CACHE_DIR=.l4_cache                    # Cache directory
L4_CACHE_ENABLED=true                     # Enable/disable caching
L4_CACHE_SIZE_MB=100                      # Cache size limit

# Context Collection
L4_MAX_DEPTH=3                            # Maximum traversal depth
L4_TOKEN_BUDGET=4000                      # Default token budget

# Analysis Options
L4_INCLUDE_TYPE_HINTS=true                 # Include type hints in analysis
L4_ADD_CONTEXT_COMMENTS=true               # Add context comments
```

### Programmatic Configuration

```python
from v1.logic.context_engine import ContextEngineConfig

config = ContextEngineConfig(
    max_traversal_depth=3,
    token_budget=4000,
    cache_size_mb=100,
    include_type_hints=True,
    add_context_comments=True,
    cache_enabled=True
)
```

## 7. V3 Configuration

### Environment Variables

```bash
# V2 Variables (kept)
L4_CACHE_DIR=.l4_cache                    # Cache directory
L4_CACHE_ENABLED=true                     # Enable/disable caching
L4_CACHE_SIZE_MB=100                      # Cache size limit
L4_MAX_DEPTH=3                            # Maximum traversal depth
L4_TOKEN_BUDGET=4000                      # Default token budget
L4_INCLUDE_TYPE_HINTS=true                 # Include type hints
L4_ADD_CONTEXT_COMMENTS=true               # Add context comments

# V3 New Variables: Telemetry
L4_TELEMETRY_ENABLED=true                 # Enable/disable telemetry
L4_TELEMETRY_DB=telemetry.db             # Telemetry database path
L4_RESOURCE_MONITORING=true                # Enable resource monitoring

# V3 New Variables: Logging
L4_LOG_LEVEL=INFO                        # Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
L4_LOG_FILE=l4.log                       # Log file path
L4_ERROR_LOG_FILE=l4_error.log            # Error log file path
L4_LOG_FILE_MAX_SIZE_MB=10               # Max log file size before rotation
L4_LOG_BACKUP_COUNT=5                    # Number of backup log files to keep
L4_LOG_JSON_FORMAT=false                  # Use JSON format for logs

# V3 New Variables: Checkpoint
L4_CHECKPOINT_ENABLED=true                # Enable checkpointing
L4_CHECKPOINT_DIR=checkpoints/             # Checkpoint directory
L4_CHECKPOINT_MAX_COUNT=10                # Maximum number of checkpoints to keep
L4_CHECKPOINT_MAX_AGE_HOURS=24           # Maximum age of checkpoints in hours

# V3 New Variables: Session
L4_SESSION_AUTO_RESUME=true              # Auto-resume interrupted sessions
L4_SESSION_MAX_SESSIONS=10                # Maximum number of sessions to keep

# V3 New Variables: LLM
L4_LLM_PROVIDER=openai                   # LLM provider (openai, anthropic, gemini)
L4_LLM_MODEL=gpt-4                      # LLM model
L4_LLM_TEMPERATURE=0.7                   # LLM temperature
L4_LLM_API_KEY=your_api_key              # LLM API key

# V3 New Variables: Error Handling
L4_RETRY_MAX_ATTEMPTS=3                   # Maximum retry attempts
L4_RETRY_BASE_DELAY=1.0                   # Base delay for exponential backoff
L4_RETRY_MAX_DELAY=60.0                   # Maximum delay for exponential backoff
L4_RETRY_JITTER=true                      # Add jitter to retry delays
```

### Programmatic Configuration

```python
from v1.logic.context_engine import ContextEngineConfig
from data.checkpoint_manager import CheckpointPolicy
from core.error_handling import RetryConfig

# V2 Configuration
context_config = ContextEngineConfig(
    max_traversal_depth=3,
    token_budget=4000,
    cache_size_mb=100,
    include_type_hints=True,
    add_context_comments=True,
    cache_enabled=True
)

# V3 Checkpoint Policy
checkpoint_policy = CheckpointPolicy(
    before_task=True,
    after_task=True,
    before_refactor=True,
    after_refactor=True,
    on_error=True,
    max_age_hours=24,
    max_count=10,
    keep_critical=True
)

# V3 Retry Configuration
retry_config = RetryConfig(
    max_attempts=3,
    base_delay=1.0,
    max_delay=60.0,
    exponential_base=2.0,
    jitter=True
)
```

---

## 8. V2 Module Dependencies

```
core/start.py
    └── logic/dispatcher.py
            ├── logic/planner.py
            │       ├── logic/task_impact_analyzer.py (V2)
            │       │       ├── data/semantic_mapper.py (V2)
            │       │       └── llm_base/provider.py
            │       └── logic/complexity_estimator.py (V2)
            │               └── data/semantic_mapper.py (V2)
            └── logic/implementor.py
                    ├── logic/context_engine.py (V2)
                    │       ├── data/semantic_mapper.py (V2)
                    │       ├── data/cache_manager.py (V2)
                    │       ├── logic/task_impact_analyzer.py (V2)
                    │       ├── logic/dependency_traverser.py (V2)
                    │       └── logic/context_pruner.py (V2)
                    └── logic/verifier.py
                            ├── data/semantic_mapper.py (V2)
                            └── logic/context_engine.py (V2)

retro/retro_agent.py
    └── llm_base/provider.py
    └── data/db_manager.py
```

## 9. V3 Module Dependencies

```
core/start.py
    ├── core/logging_config.py (V3)
    ├── data/telemetry_manager.py (V3)
    ├── data/checkpoint_manager.py (V3)
    ├── core/session_manager.py (V3)
    ├── core/graceful_shutdown.py (V3)
    ├── core/health_check.py (V3)
    └── logic/dispatcher.py
            ├── logic/planner.py
            │       ├── logic/task_impact_analyzer.py (V2)
            │       │       ├── data/semantic_mapper.py (V2)
            │       │       └── llm_base/provider.py
            │       └── logic/complexity_estimator.py (V2)
            │               └── data/semantic_mapper.py (V2)
            └── logic/implementor.py
                    ├── logic/context_engine.py (V2)
                    │       ├── data/semantic_mapper.py (V2)
                    │       ├── data/cache_manager.py (V2)
                    │       ├── logic/task_impact_analyzer.py (V2)
                    │       ├── logic/dependency_traverser.py (V2)
                    │       └── logic/context_pruner.py (V2)
                    └── logic/verifier.py
                            ├── data/semantic_mapper.py (V2)
                            └── logic/context_engine.py (V2)

core/error_handling.py (V3)
core/transactions.py (V3)
core/ui.py (V3)
core/log_analyzer.py (V3)

retro/retro_agent.py
    └── llm_base/provider.py
    └── data/db_manager.py
```

---

## 10. Documentation Structure (V3)

```
docs/
├── V2_ARCHITECTURE.md          # Complete V2 architecture overview
├── MIGRATION_V1_TO_V2.md       # Step-by-step migration instructions
├── API_REFERENCE.md              # Complete API documentation
├── PERFORMANCE.md               # Performance benchmarks and characteristics
├── TELEMETRY.md                # (V3) Telemetry system documentation
├── LOGGING.md                  # (V3) Structured logging documentation
├── RESUMABILITY.md             # (V3) Checkpoint and recovery documentation
├── SESSION_MANAGEMENT.md        # (V3) Session management documentation
├── MIGRATION_V2_TO_V3.md      # (V3) Step-by-step migration guide from V2 to V3
└── TROUBLESHOOTING.md          # (V3) Common issues and solutions
```

---

## 11. V4 Module Hierarchy

### 11.1 New V4 Modules in `data/`

| Module | Responsibility |
| :--- | :--- |
| **`data/context_hierarchy.py`** (V4) | Hierarchical context management (L0-L3 levels) |
| **`data/decision_history.py`** (V4) | Decision history tracking with full context |

### 11.2 New V4 Modules in `logic/`

| Module | Responsibility |
| :--- | :--- |
| **`logic/context_expander.py`** (V4) | Dynamic context expansion based on task needs |
| **`logic/context_scorer.py`** (V4) | Relevance scoring for context items |
| **`logic/context_summarizer.py`** (V4) | Intelligent summarization for higher-level contexts |
| **`logic/reasoning_engine.py`** (V4) | Adaptive reasoning engine architecture |
| **`logic/context_analyzer.py`** (V4) | Context analysis for situation assessment |
| **`logic/decision_maker.py`** (V4) | Decision maker for action selection |
| **`logic/action_validator.py`** (V4) | Action validator for result verification |
| **`logic/strategy_selector.py`** (V4) | Adaptive strategy selection based on situation |
| **`logic/strategy_evaluator.py`** (V4) | Strategy performance tracking and comparison |
| **`logic/strategy_switcher.py`** (V4) | Adaptive strategy switching |
| **`logic/strategy_hybridizer.py`** (V4) | Strategy hybridization for complex situations |
| **`logic/progress_tracker.py`** (V4) | Progress tracking for continuous monitoring |
| **`logic/progress_predictor.py`** (V4) | Progress prediction for time and resource estimation |
| **`logic/trap_detector.py`** (V4) | Trap detection (loops, dead ends, circular reasoning) |
| **`logic/trap_recovery.py`** (V4) | Trap recovery engine for trap resolution |
| **`logic/trap_prevention.py`** (V4) | Trap prevention mechanisms |
| **`logic/pattern_recognizer.py`** (V4) | Pattern recognition for decision patterns |
| **`logic/self_reflection.py`** (V4) | Self-reflection mechanism for continuous improvement |
| **`logic/lesson_learner.py`** (V4) | Learning from mistakes systematically |
| **`logic/adaptive_heuristics.py`** (V4) | Adaptive heuristics that improve over time |
| **`logic/explanation_generator.py`** (V4) | Natural language explanations for decisions |
| **`data/decision_tracer.py`** (V4) | Decision trace logging and query interface |

---

## 12. V4 Module Descriptions

### Module 24: `data/context_hierarchy.py` (V4 - Hierarchical Context Management)
Manages multi-level context hierarchy for adaptive reasoning.

*   **Context Levels**: L0 (immediate), L1 (recent), L2 (session), L3 (project)
*   **Context Queries**: Query any context level with filters and time ranges
*   **Context Summarization**: Intelligent summarization for higher-level contexts
*   **Context Caching**: LRU cache for L0/L1 contexts
*   **Context Propagation**: Define how context propagates between levels
*   **Key Methods**: `get_context()`, `get_current_action()`, `get_recent_actions()`, `get_session_context()`, `get_project_context()`

### Module 25: `data/decision_history.py` (V4 - Decision History Tracking)
Tracks all decisions with full context for meta-cognition.

*   **Decision Recording**: Track every decision with context, reasoning, and outcome
*   **Decision Dependencies**: Track decision dependencies and relationships
*   **Decision Confidence**: Track confidence and actual success
*   **Decision Graph**: Build decision graph for pattern analysis
*   **Export Capabilities**: Export decision history for external analysis
*   **Key Methods**: `record_decision()`, `get_decision()`, `search_decisions()`, `get_decision_graph()`

### Module 26: `logic/context_expander.py` (V4 - Dynamic Context Expansion)
Implements intelligent context expansion based on task needs.

*   **Adaptive Expansion**: Start with L0, expand to L1/L2/L3 as needed
*   **Sufficiency Check**: Validate if current context level is sufficient
*   **Optimal Level Learning**: Learn optimal context level for different task types
*   **Expansion Logging**: Log expansion decisions in telemetry
*   **Key Methods**: `get_context()`, `is_sufficient()`, `expand_context()`

### Module 27: `logic/context_scorer.py` (V4 - Context Relevance Scoring)
Implements relevance scoring for context items.

*   **Relevance Factors**: Recency, similarity, dependency, impact
*   **Scoring Algorithm**: Weighted scoring formula: `score = w1*recency + w2*similarity + w3*dependency + w4*impact`
*   **Dynamic Weighting**: Learn weights from historical success rates
*   **Context Pruning**: Prune low-relevance items to reduce noise
*   **Key Methods**: `score_context()`, `rank_context()`, `prune_context()`

### Module 28: `logic/context_summarizer.py` (V4 - Context Summarization)
Implements intelligent summarization for higher-level contexts.

*   **LLM-Based Summarization**: Use LLM for intelligent summarization
*   **Summary Templates**: Brief (50-100 words), Detailed (200-300 words), Full
*   **Quality Tracking**: Track summary quality via downstream success rate
*   **Cache Invalidation**: Invalidate cache when underlying context changes
*   **Key Methods**: `summarize()`, `get_summary()`, `invalidate_cache()`

### Module 29: `logic/reasoning_engine.py` (V4 - Adaptive Reasoning Engine)
Provides adaptive reasoning engine architecture.

*   **Reasoning Pipeline**: Analyze → Decide → Act → Validate
*   **Reasoning Strategies**: Conservative, Balanced, Aggressive
*   **Fallback Strategies**: Define fallback strategies for different failure modes
*   **Reasoning Metrics**: Track confidence, success rate, efficiency
*   **Key Methods**: `analyze()`, `decide()`, `act()`, `validate()`

### Module 30: `logic/context_analyzer.py` (V4 - Context Analysis)
Implements context analyzer for situation assessment.

*   **Situation Classification**: Classify situations: normal, error, blocked, uncertain, complex
*   **Feature Extraction**: Extract error types, patterns, constraints from context
*   **Action Identification**: Identify potential actions and their risks
*   **Confidence Estimation**: Estimate confidence for each potential action
*   **Situation Report**: Generate situation report with recommendations
*   **Key Methods**: `analyze_situation()`, `classify_situation()`, `estimate_confidence()`

### Module 31: `logic/decision_maker.py` (V4 - Decision Making)
Implements decision maker for action selection.

*   **Decision Factors**: Success probability, cost, risk, time
*   **Decision Strategies**: Greedy, Optimal, Safe
*   **Alternative Evaluation**: Evaluate alternative actions before selecting
*   **Weighted Scoring**: Use weighted scoring for decision making
*   **Decision Explanation**: Provide reasoning for decision in natural language
*   **Key Methods**: `select_action()`, `evaluate_alternatives()`, `explain_decision()`

### Module 32: `logic/action_validator.py` (V4 - Action Validation)
Implements action validator for result verification.

*   **Validation Criteria**: Goal achievement, side effects, progress, efficiency
*   **Validation Methods**: Test execution, code review, metrics comparison, user feedback
*   **Progress Measurement**: Measure progress toward goal
*   **Corrective Action**: Trigger corrective action if validation fails
*   **Accuracy Tracking**: Track validation accuracy for continuous improvement
*   **Key Methods**: `validate_action()`, `check_goal_achievement()`, `measure_progress()`

### Module 33: `logic/strategy_selector.py` (V4 - Strategy Selection)
Implements adaptive strategy selection based on situation.

*   **Strategy Selection Matrix**: Select strategy based on situation type and task
*   **Strategy Adaptation**: Adapt strategy based on recent performance
*   **Strategy Switching**: Switch strategies when current strategy underperforms
*   **Performance Tracking**: Track strategy performance metrics
*   **Optimal Learning**: Learn optimal strategy for each task type
*   **Key Methods**: `select_strategy()`, `should_switch()`, `get_strategy_performance()`

### Module 34: `logic/strategy_evaluator.py` (V4 - Strategy Evaluation)
Implements strategy performance tracking and comparison.

*   **Performance Metrics**: Track success rate, efficiency, effectiveness per strategy
*   **Strategy Comparison**: Compare strategies across multiple dimensions
*   **Strategy Ranking**: Rank strategies for each task and situation type
*   **Dynamic Updates**: Update rankings based on performance
*   **Recommendations**: Provide strategy recommendations
*   **Key Methods**: `track_performance()`, `compare_strategies()`, `rank_strategies()`

### Module 35: `logic/strategy_switcher.py` (V4 - Strategy Switching)
Implements dynamic strategy switching.

*   **Switch Triggers**: Detect when current strategy underperforms
*   **Switch Execution**: Switch to better-performing strategy with minimal disruption
*   **Disruption Minimization**: Minimize disruption when switching strategies
*   **Switch Validation**: Validate switch success
*   **Switch Tracking**: Track switch frequency and success
*   **Key Methods**: `should_switch()`, `switch_strategy()`, `validate_switch()`

### Module 36: `logic/strategy_hybridizer.py` (V4 - Strategy Hybridization)
Implements strategy hybridization for complex situations.

*   **Hybrid Strategies**: Combine multiple strategies for complex tasks
*   **Dynamic Adjustment**: Dynamically adjust strategy mix based on progress
*   **Risk-Based Selection**: Use conservative for high-risk, aggressive for low-risk
*   **Progress-Based Adjustment**: Conservative when stuck, aggressive when making progress
*   **Performance Tracking**: Validate hybrid strategy performance
*   **Key Methods**: `create_hybrid_strategy()`, `adjust_strategy_mix()`, `validate_hybrid()`

### Module 37: `logic/progress_tracker.py` (V4 - Progress Tracking)
Implements progress tracker for continuous monitoring.

*   **Progress Metrics**: Track code, task, session, and project progress
*   **Progress Comparison**: Compare progress against expected rates
*   **Stagnation Detection**: Detect stagnation (no progress for N operations)
*   **Regression Detection**: Detect regression (negative progress)
*   **Progress Alerts**: Alert when progress falls below threshold
*   **Progress Reports**: Generate progress reports
*   **Key Methods**: `start_tracking()`, `update_progress()`, `check_progress()`, `get_report()`

### Module 38: `logic/progress_predictor.py` (V4 - Progress Prediction)
Implements progress prediction for time and resource estimation.

*   **Prediction Methods**: Historical average, linear regression, ML model
*   **Time Prediction**: Predict time to complete current task
*   **Resource Prediction**: Predict resources needed (tokens, API calls, compute)
*   **Success Prediction**: Predict probability of successful completion
*   **Prediction Updates**: Update predictions as work progresses
*   **Accuracy Tracking**: Track prediction accuracy (MAE, RMSE, MAPE)
*   **Key Methods**: `predict_completion_time()`, `predict_resources()`, `predict_success()`

### Module 39: `logic/trap_detector.py` (V4 - Trap Detection)
Implements trap detection (loops, dead ends, circular reasoning).

*   **Loop Detection**: Detect repeated actions (same action 3+ times)
*   **Dead End Detection**: Detect no progress for extended period
*   **Circular Reasoning Detection**: Detect reasoning that loops back to start
*   **Detection Algorithms**: Exact match, similarity match, pattern match
*   **Trap Alerts**: Alert on trap detection
*   **Key Methods**: `detect_loop()`, `detect_dead_end()`, `detect_circular_reasoning()`

### Module 40: `logic/trap_recovery.py` (V4 - Trap Recovery)
Implements recovery engine for trap resolution.

*   **Recovery Strategies**: Select appropriate recovery strategy based on trap type
*   **Recovery Execution**: Execute recovery action with minimal disruption
*   **Recovery Validation**: Validate recovery success
*   **Context Update**: Update context after recovery
*   **Recovery Learning**: Learn from trap occurrences to prevent future traps
*   **Key Methods**: `select_recovery_strategy()`, `execute_recovery()`, `validate_recovery()`

### Module 41: `logic/trap_prevention.py` (V4 - Trap Prevention)
Implements prevention mechanisms to avoid traps.

*   **Loop Prevention**: Track attempted actions to avoid repetition
*   **Dead End Prevention**: Early progress validation to prevent dead ends
*   **Circular Reasoning Prevention**: Maintain decision history to prevent cycles
*   **Scope Creep Prevention**: Freeze task scope to prevent creep
*   **Warning System**: Warn before high-risk actions
*   **Learning**: Learn from past traps to prevent recurrence
*   **Key Methods**: `track_attempted_actions()`, `validate_progress()`, `maintain_decision_history()`

### Module 42: `logic/pattern_recognizer.py` (V4 - Pattern Recognition)
Implements pattern recognition for decision patterns.

*   **Pattern Types**: Decision patterns, context patterns, success patterns, failure patterns
*   **Recognition Algorithms**: Sequence mining, association rules, classification
*   **Pattern Prediction**: Predict optimal decision for given context
*   **Continuous Updates**: Update patterns continuously from new data
*   **ML Models**: Use ML models for prediction
*   **Key Methods**: `recognize_patterns()`, `predict_decision()`, `update_patterns()`

### Module 43: `logic/self_reflection.py` (V4 - Self-Reflection)
Implements self-reflection mechanism for continuous improvement.

*   **Reflection Triggers**: After task, after error, periodic, on request
*   **Review Process**: Review recent decisions and identify patterns
*   **Pattern Identification**: Identify areas for improvement
*   **Reflection Reports**: Generate self-reflection reports
*   **Heuristic Updates**: Update heuristics based on learnings
*   **Key Methods**: `perform_reflection()`, `identify_patterns()`, `generate_report()`

### Module 44: `logic/lesson_learner.py` (V4 - Learning from Mistakes)
Implements systematic learning from failures.

*   **Failure Recording**: Record every failure with full context
*   **Root Cause Analysis**: Analyze root cause of each failure
*   **Pattern Identification**: Identify patterns in failures
*   **Lesson Extraction**: Generate lessons learned
*   **Heuristic Updates**: Update decision heuristics to avoid repeated mistakes
*   **Mistake Tracking**: Track mistake reduction over time
*   **Key Methods**: `record_failure()`, `analyze_root_cause()`, `extract_lessons()`, `apply_lessons()`

### Module 45: `logic/adaptive_heuristics.py` (V4 - Adaptive Heuristics)
Implements adaptive heuristics that improve over time.

*   **Baseline Heuristics**: Start with baseline heuristics
*   **Heuristic Updates**: Update heuristics based on performance data
*   **Weight Learning**: Learn optimal weights for decision factors
*   **Threshold Learning**: Learn optimal thresholds for validation
*   **Strategy Learning**: Learn optimal strategies per situation type
*   **Learning Algorithms**: Bayesian optimization, reinforcement learning, gradient descent
*   **Quality Tracking**: Track heuristic quality (success rate, efficiency)
*   **Key Methods**: `update_heuristics()`, `learn_weights()`, `learn_thresholds()`, `get_heuristics()`

### Module 46: `logic/explanation_generator.py` (V4 - Decision Explanation)
Implements natural language explanations for decisions.

*   **Explanation Templates**: Brief (1-2 sentences), Detailed (paragraph), Technical
*   **Explanation Elements**: What action, why chosen, alternatives rejected, confidence, expected outcome
*   **LLM Generation**: Use LLM for natural language generation
*   **Audience Tailoring**: Tailor explanation to audience (developer, manager, user)
*   **Clarity Validation**: Validate explanation clarity and accuracy
*   **Key Methods**: `generate_explanation()`, `generate_brief()`, `generate_detailed()`

### Module 47: `data/decision_tracer.py` (V4 - Decision Tracing)
Implements decision trace logging and query interface.

*   **Trace Logging**: Log every decision with full reasoning chain
*   **Context Logging**: Log context at decision point
*   **Alternatives Logging**: Log alternatives considered and rejected
*   **Confidence Logging**: Log confidence and uncertainty
*   **Query Interface**: Search decisions by task, operation, time range, context, outcome
*   **Export Capabilities**: Export traces to JSON/CSV for external analysis
*   **Key Methods**: `log_decision()`, `trace_decision()`, `search_decisions()`, `export_traces()`

---

## 13. V4 Operational Flow

### V4 Operational Flow (Enhanced)

The V4 operational flow adds adaptive reasoning, hierarchical context, trap detection, and meta-cognition:

**Phase 0: Initialization (V3)**
1. **Setup Logging**: Configure structured logging with `setup_logging()`
2. **Initialize Telemetry**: Create `TelemetryManager` instance
3. **Initialize Checkpoint**: Create `CheckpointManager` instance
4. **Initialize Session**: Create `SessionManager` instance
5. **Setup Signal Handlers**: Configure graceful shutdown handlers

**Phase 1: Session Detection (V3)**
1. **Detect Interrupted Sessions**: Check for interrupted sessions on startup
2. **Offer Resumption**: Prompt user to resume previous session
3. **Resume or Start New**: Resume existing session or start new one

**Phase 2: Health Check (V3)**
1. **Run Health Checks**: Check database, git, cache, file system, LLM API
2. **Validate System State**: Ensure system is in healthy state
3. **Halt if Unhealthy**: Stop operation if health checks fail

**Phase 3: Hierarchical Context Access (V4)**
1. **Start with L0**: Query L0 context (current action, current state, last error)
2. **Assess Sufficiency**: Check if L0 context is sufficient for current task
3. **Expand to L1**: If L0 insufficient, expand to L1 (last 10 actions, recent telemetry)
4. **Expand to L2**: If L1 insufficient, expand to L2 (session history, task progress)
5. **Expand to L3**: If L2 insufficient, expand to L3 (project state, architecture)
6. **Score Relevance**: Score context items by relevance to current task
7. **Summarize**: Summarize higher-level contexts (L2, L3) for efficiency

**Phase 4: Adaptive Reasoning (V4)**
1. **Analyze Context**: Analyze current context to identify situation type
2. **Select Strategy**: Select reasoning strategy (conservative, balanced, aggressive) based on situation
3. **Make Decision**: Use decision maker to select best action
4. **Log Decision**: Log decision with full reasoning chain and alternatives considered
5. **Generate Explanation**: Generate natural language explanation for decision

**Phase 5: Execution with Telemetry (V3)**
1. **Create Checkpoint**: Create checkpoint before critical operation
2. **Start Operation Tracking**: Track operation in telemetry
3. **Track Progress**: Track progress metrics continuously
4. **Detect Traps**: Monitor for loops, dead ends, circular reasoning
5. **Recover from Traps**: If trap detected, execute recovery strategy
6. **Complete Operation Tracking**: End operation tracking in telemetry

**Phase 6: Action Validation (V4)**
1. **Validate Result**: Validate that action achieved intended result
2. **Check Side Effects**: Check for unintended side effects
3. **Measure Progress**: Measure progress toward goal
4. **Validate Progress**: Compare progress against expected rates
5. **Detect Stagnation**: Detect if no progress is being made
6. **Detect Regression**: Detect if progress is going backwards
7. **Update Context**: Update context with validation results

**Phase 7: Meta-Cognition (V4)**
1. **Record Decision**: Record decision with full context in decision history
2. **Recognize Patterns**: Recognize recurring decision patterns
3. **Learn from Success**: Update heuristics based on successful decisions
4. **Learn from Failure**: Extract lessons from failures and update heuristics
5. **Perform Self-Reflection**: Perform regular self-reflection to identify improvements
6. **Update Strategies**: Update strategies based on performance data

**Phase 8: Error Handling (V3)**
1. **Classify Error**: Classify error type (transient, permanent, retryable)
2. **Apply Recovery Strategy**: Retry with backoff for transient errors
3. **Rollback on Failure**: Rollback to checkpoint if unrecoverable
4. **Log Error**: Record error in logs and telemetry
5. **Show Error Message**: Display interactive error with recovery suggestions

**Phase 9: Session Management (V3)**
1. **Update Session State**: Track tasks completed, time spent
2. **Persist Session**: Save session state to disk
3. **Complete Session**: Mark session as complete or pause

**Phase 10: Cleanup (V3)**
1. **Garbage Collection**: Clean up old checkpoints
2. **Archive Data**: Archive old telemetry data
3. **Rotate Logs**: Rotate log files based on size

---

## 14. V4 Configuration

### Environment Variables

```bash
# V3 Variables (kept)
L4_CACHE_DIR=.l4_cache
L4_CACHE_ENABLED=true
L4_CACHE_SIZE_MB=100
L4_MAX_DEPTH=3
L4_TOKEN_BUDGET=4000
L4_INCLUDE_TYPE_HINTS=true
L4_ADD_CONTEXT_COMMENTS=true
L4_TELEMETRY_ENABLED=true
L4_TELEMETRY_DB=telemetry.db
L4_RESOURCE_MONITORING=true
L4_LOG_LEVEL=INFO
L4_LOG_FILE=l4.log
L4_ERROR_LOG_FILE=l4_error.log
L4_LOG_FILE_MAX_SIZE_MB=10
L4_LOG_BACKUP_COUNT=5
L4_LOG_JSON_FORMAT=false
L4_CHECKPOINT_ENABLED=true
L4_CHECKPOINT_DIR=checkpoints/
L4_CHECKPOINT_MAX_COUNT=10
L4_CHECKPOINT_MAX_AGE_HOURS=24
L4_SESSION_AUTO_RESUME=true
L4_SESSION_MAX_SESSIONS=10
L4_LLM_PROVIDER=openai
L4_LLM_MODEL=gpt-4
L4_LLM_TEMPERATURE=0.7
L4_LLM_API_KEY=your_api_key
L4_RETRY_MAX_ATTEMPTS=3
L4_RETRY_BASE_DELAY=1.0
L4_RETRY_MAX_DELAY=60.0
L4_RETRY_JITTER=true

# V4 New Variables: Adaptive Reasoning
L4_ADAPTIVE_REASONING_ENABLED=true         # Enable/disable adaptive reasoning
L4_REASONING_STRATEGY=balanced             # Default reasoning strategy (conservative, balanced, aggressive)
L4_REASONING_CONFIDENCE_THRESHOLD=0.7   # Minimum confidence for decision making

# V4 New Variables: Context Hierarchy
L4_CONTEXT_HIERARCHY_ENABLED=true        # Enable/disable context hierarchy
L4_CONTEXT_LEVELS=4                      # Number of context levels (L0-L3)
L4_CONTEXT_TTL_L0=300                     # TTL for L0 context in seconds (5 minutes)
L4_CONTEXT_TTL_L1=3600                    # TTL for L1 context in seconds (1 hour)
L4_CONTEXT_CACHE_SIZE_MB=50             # Context cache size limit

# V4 New Variables: Progress Tracking
L4_PROGRESS_TRACKING_ENABLED=true        # Enable/disable progress tracking
L4_PROGRESS_CHECK_INTERVAL=5              # Progress check interval in operations
L4_PROGRESS_MINIMAL_THRESHOLD=0.1        # Minimal progress threshold (10%)
L4_PROGRESS_EXPECTED_THRESHOLD=0.3       # Expected progress threshold (30%)

# V4 New Variables: Trap Detection
L4_TRAP_DETECTION_ENABLED=true           # Enable/disable trap detection
L4_LOOP_DETECTION_THRESHOLD=3             # Loop detection threshold (repetitions)
L4_DEAD_END_THRESHOLD=5                   # Dead end threshold (no progress operations)
L4_TRAP_PREVENTION_ENABLED=true         # Enable/disable trap prevention

# V4 New Variables: Meta-Cognition
L4_META_COGNITION_ENABLED=true           # Enable/disable meta-cognition
L4_SELF_REFLECTION_INTERVAL=10            # Self-reflection interval (every N operations)
L4_PATTERN_RECOGNITION_ENABLED=true      # Enable/disable pattern recognition
L4_LEARNING_ENABLED=true                   # Enable/disable learning from mistakes

# V4 New Variables: Decision Explainability
L4_DECISION_EXPLAINABILITY_ENABLED=true  # Enable/disable decision explainability
L4_DECISION_TRACE_ENABLED=true            # Enable/disable decision tracing
L4_EXPLANATION_FORMAT=detailed            # Default explanation format (brief, detailed, technical)
```

### Programmatic Configuration

```python
from v1.logic.context_engine import ContextEngineConfig
from data.checkpoint_manager import CheckpointPolicy
from core.error_handling import RetryConfig
from logic.reasoning_engine import ReasoningConfig
from logic.trap_detector import TrapDetectionConfig
from logic.progress_tracker import ProgressConfig

# V2 Configuration
context_config = ContextEngineConfig(
    max_traversal_depth=3,
    token_budget=4000,
    cache_size_mb=100,
    include_type_hints=True,
    add_context_comments=True,
    cache_enabled=True
)

# V3 Checkpoint Policy
checkpoint_policy = CheckpointPolicy(
    before_task=True,
    after_task=True,
    before_refactor=True,
    after_refactor=True,
    on_error=True,
    max_age_hours=24,
    max_count=10,
    keep_critical=True
)

# V3 Retry Configuration
retry_config = RetryConfig(
    max_attempts=3,
    base_delay=1.0,
    max_delay=60.0,
    exponential_base=2.0,
    jitter=True
)

# V4 Reasoning Configuration
reasoning_config = ReasoningConfig(
    enabled=True,
    default_strategy='balanced',
    confidence_threshold=0.7,
    strategies=['conservative', 'balanced', 'aggressive']
)

# V4 Trap Detection Configuration
trap_detection_config = TrapDetectionConfig(
    enabled=True,
    loop_threshold=3,
    dead_end_threshold=5,
    prevention_enabled=True
)

# V4 Progress Configuration
progress_config = ProgressConfig(
    enabled=True,
    check_interval=5,
    minimal_threshold=0.1,
    expected_threshold=0.3
)
```

---

## 15. V4 Module Dependencies

```
core/start.py
    ├── core/logging_config.py (V3)
    ├── data/telemetry_manager.py (V3)
    ├── data/checkpoint_manager.py (V3)
    ├── data/context_hierarchy.py (V4)
    ├── data/decision_history.py (V4)
    ├── core/session_manager.py (V3)
    ├── core/graceful_shutdown.py (V3)
    ├── core/health_check.py (V3)
    └── logic/dispatcher.py (V4 Enhanced)
            ├── logic/reasoning_engine.py (V4)
            │       ├── logic/context_analyzer.py (V4)
            │       │       ├── data/context_hierarchy.py (V4)
            │       │       └── llm_base/provider.py
            │       ├── logic/decision_maker.py (V4)
            │       │       └── data/decision_history.py (V4)
            │       └── logic/action_validator.py (V4)
            ├── logic/planner.py (V4 Enhanced)
            │       ├── logic/context_expander.py (V4)
            │       │       ├── data/context_hierarchy.py (V4)
            │       │       └── logic/context_scorer.py (V4)
            │       ├── logic/context_summarizer.py (V4)
            │       ├── logic/task_impact_analyzer.py (V2)
            │       └── logic/complexity_estimator.py (V2)
            └── logic/implementor.py (V4 Enhanced)
                    ├── logic/context_engine.py (V2)
                    ├── logic/progress_tracker.py (V4)
                    ├── logic/trap_detector.py (V4)
                    └── logic/trap_recovery.py (V4)

logic/strategy_evaluator.py (V4)
    ├── logic/strategy_selector.py (V4)
    └── logic/strategy_switcher.py (V4)
            └── logic/strategy_hybridizer.py (V4)

logic/pattern_recognizer.py (V4)
    ├── data/decision_history.py (V4)
    └── logic/adaptive_heuristics.py (V4)

logic/self_reflection.py (V4)
    ├── logic/pattern_recognizer.py (V4)
    ├── logic/lesson_learner.py (V4)
    └── logic/adaptive_heuristics.py (V4)

logic/explanation_generator.py (V4)
    ├── data/decision_tracer.py (V4)
    └── data/decision_history.py (V4)

retro/retro_agent.py
    └── llm_base/provider.py
    └── data/db_manager.py
```

---

## 16. V4 Documentation Structure

```
docs/
├── V2_ARCHITECTURE.md
├── MIGRATION_V1_TO_V2.md
├── API_REFERENCE.md
├── PERFORMANCE.md
├── TELEMETRY.md
├── LOGGING.md
├── RESUMABILITY.md
├── SESSION_MANAGEMENT.md
├── MIGRATION_V2_TO_V3.md
├── TROUBLESHOOTING.md
├── V4_ARCHITECTURE.md                    # (V4) Complete V4 architecture overview
├── MIGRATION_V3_TO_V4.md                # (V4) Step-by-step migration guide from V3 to V4
├── ADAPTIVE_REASONING.md                 # (V4) Adaptive reasoning system documentation
├── TRAP_DETECTION.md                    # (V4) Trap detection and recovery documentation
├── META_COGNITION.md                    # (V4) Meta-cognition and learning documentation
├── PROGRESS_TRACKING.md                 # (V4) Progress tracking and validation documentation
├── DECISION_EXPLAINABILITY.md            # (V4) Decision explainability documentation
└── STRATEGY_MANAGEMENT.md                # (V4) Strategy management documentation
```
