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
*   **Cache Storage (V2):**
    *   `.l4_cache/`: Directory for storing AST analysis results and cached context

---

## 2. Module Hierarchy Reference

| Module | Responsibility |
| :--- | :--- |
| **Core** | Entry point, CLI, and high-level Orchestration loop. |
| **Data** | SQLite schema management, Markdown CRUD (Context Bank access), and Cache management (V2). |
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

---

## 7. V2 Module Dependencies

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

---

## 8. Documentation Structure (V2)

```
docs/
├── V2_ARCHITECTURE.md          # Complete V2 architecture overview
├── MIGRATION_V1_TO_V2.md       # Step-by-step migration instructions
├── API_REFERENCE.md              # Complete API documentation
└── PERFORMANCE.md               # Performance benchmarks and characteristics
```
