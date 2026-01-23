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
