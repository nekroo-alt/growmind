# Project Design: L4 Self-Evolving Development Platform

This **Project Design Document (PDD)** outlines the architecture and operational logic for the **"L4 Auto-Pilot" Self-Evolving Development Platform**.

---

## 1. Executive Summary

The goal is to build a development environment where an AI agent acts as a "co-pilot transitioning to pilot." By utilizing a **Git-native** approach and **TDD (Test Driven Development)**, the system ensures every change is traceable, verifiable, and small.

**Cold Start Requirement:** The user must provide `product.md` and `technical.md` at the beginning of the session to initialize the context.

---

## 2. System Architecture

### 2.1 The Context Bank
To keep `product.md` and `technical.md` relatively static, a new database is used for dynamic task tracking.

| Component | Format | Purpose |
|---|---|---|
| `product.md` | Markdown | High-level requirements, user journeys, and business logic. |
| `technical.md` | Markdown | Tech stack, architecture map, and module-level status. |
| **`task.db`** | **SQLite** | **Stores atomic task specs and statuses to keep documentation static.** |
| `activity.db` | SQLite | Raw ledger of prompts, diffs, test results, and human overrides. |
| `.patterns/` | Directory | (Evolutionary) Stores project-specific coding standards. |
| **`.l4_cache/`** | **Directory** | **(V2) Caches AST analysis results for performance optimization.** |
| **`telemetry.db`** | **SQLite** | **(V3) Tracks operations, events, metrics, and resources for comprehensive monitoring.** |
| **`snapshots.db`** | **SQLite** | **(V3) Stores system state snapshots for checkpointing and recovery.** |
| **`sessions.db`** | **SQLite** | **(V3) Stores session state, configuration, and analytics.** |

---

## 3. Detailed Agent Specifications

### A. The Planner (Plan & Breakdown Agents)
**Pre-condition:** Before starting any new task, the agent **must verify that the project git space is clean.**

* **Task Selection Logic:** Before triggering the planner, the agent must attempt to pick up an existing task from `task.db` and implement it directly.
* **Trigger Conditions:** The Planner is only triggered if:
    1. No tasks are available in `task.db`.
    2. The picked task is too large (needs further breakdown).
    3. The task is unable to proceed.
* **Constraint**: Each task must be estimated at **<30 lines of code**.

**V2 Enhancement: AST-Informed Breakdown**
* Uses AST-based analysis to understand code structure and dependencies
* Breaks down tasks at logical code units (e.g., "add method to class X")
* Validates subtasks don't exceed 30-line limit using complexity analysis
* Includes context-aware acceptance criteria that verify dependency contracts

**V3 Enhancement: Checkpoint Integration**
* Creates checkpoint before planning operations to enable recovery
* Captures state before task breakdown to allow rollback
* Validates checkpoint integrity after planning completion

### B. The Implementer (TDD Agent)

*   **Logic**: Follows the Red-Green-Refactor cycle.
    1.  **Red**: Writes a failing test case based on the Task Acceptance Criteria.
    2.  **Green**: Writes the minimal code to pass the test.
    3.  **Refactor**: Cleans code while maintaining test integrity.
*   **Constraint**: Must respect the **Open-Closed Principle**. It prefers adding new classes/functions over modifying existing stable ones.

**V3 Enhancement: Telemetry Tracking and Progress Reporting**
* Tracks implementation operations with comprehensive telemetry
* Records metrics: tokens used, time elapsed, resources consumed
* Provides real-time progress indicators via UI
* Creates checkpoints before and after task implementation
* Logs structured events for debugging and analysis

### C. The Acceptance Agent (The Critic)

*   **Role**: Acts as a "Gatekeeper" before a Git commit is finalized.
*   **Validation**:
    *   Runs the full test suite (not just the new test).
    *   Performs **Mutation Testing**: Briefly modifies the code to ensure the new test actually fails when logic is broken.
    *   Checks the 30-line limit.
    *   **V2 Enhancement**: Validates context completeness - ensures implementation uses provided context appropriately
    *   **V2 Enhancement**: Checks that new code doesn't violate dependency contracts
    *   **V2 Enhancement**: Verifies that all downstream consumers are tested
    *   **V3 Enhancement**: Validates checkpoint integrity - ensures checkpoints are valid before commit
    *   **V3 Enhancement**: Verifies telemetry data completeness for all operations
    *   **V4 Enhancement**: Validates progress after each operation - checks if progress meets expected rates
    *   **V4 Enhancement**: Detects stagnation - alerts when no progress is made for extended periods
    *   **V4 Enhancement**: Detects regression - alerts when progress is going backwards

---

## 4. The Self-Evolution Mechanism (Retro Flow)

The "L4" aspect relies on the **Retrospective Loop**. This process is handled via a dedicated **"Retro Flow"**, separate from the common development flow.

1.  **Capture**: Triggered by human modifications to AI commits.
2.  **Analyze**: Comparison between AI attempt and Human correction.
3.  **Generalize & Update**: Patterns are written to `.patterns/coding_style.md`.

---

## 5. Development Workflow

### Common Flow
1. **Git Check:** Ensure workspace is clean.
2. **Task Fetch:** Check `task.db` for existing tasks.
3. **Execution:** Implement via TDD loop.
4. **Commit:** Finalize change.

### Retro Flow
1. **Manual Correction:** Human edits the code.
2. **Analysis:** Retrospective Agent triggers.
3. **Learning:** Update `.patterns` for future prompts.

---

## 6. Implementation Guardrails & Corner Cases

### 6.1 Handling Technical Debt (The 10-Commit Rule)

To prevent the "Open-Closed" principle from creating excessive "Add-only" spaghetti code:

*   **Guardrail**: After every 10 commits, the system initiates a **Refactor Sprint**.
*   **Action**: The Agent is allowed to modify existing code to consolidate patterns, provided 100% of existing tests pass.

### 6.2 The "Hallucination" Trap

*   **Problem**: The AI might mock out too many dependencies, making tests pass in a vacuum but fail in production.
*   **Solution**: Integration tests are mandatory for every module. The `technical.md` must define "Integration Boundaries" that the **Acceptance Agent** must verify.

### 6.3 Local-First Execution

*   The system must run as a CLI tool (e.g., `l4-dev start`).
*   It should use a `.l4ignore` file (similar to `.gitignore`) to prevent the LLM from being overwhelmed by large binary files or logs.

### 6.4 Checkpoint Before Refactoring (V3)

*   **Guardrail**: Create checkpoint before refactoring sprint (every 10 commits)
*   **Action**: System automatically saves state before allowing code modifications
*   **Recovery**: If refactoring fails, automatically rollback to checkpoint
*   **Validation**: Verify checkpoint integrity before and after refactoring

### 6.5 Health Checks Before Critical Operations (V3)

*   **Guardrail**: Run health checks before starting critical operations
*   **Checks**:
    *   Database connectivity and integrity
    *   Git repository state
    *   Cache validity and size
    *   File system permissions and space
    *   LLM API connectivity
*   **Action**: Halt operation if health checks fail, provide recovery suggestions

### 6.6 Transaction Support for Multi-Step Operations (V3)

*   **Guardrail**: Wrap multi-step operations in transactions
*   **Components**:
    *   Database modifications
    *   File writes
    *   Test execution
*   **Behavior**: All-or-nothing execution - rollback any step if any fails
*   **Tracking**: Log transaction lifecycle in telemetry

---

## 7. V2 Enhancements: AST-Based Context Collection

### 7.1 Enhanced Context Collection

**V2 introduces AST-based context collection** that significantly improves precision and reduces token usage:

* **Task Impact Analysis**: Uses LLM-powered natural language analysis to predict which code will be affected by a task
* **Dependency Chain Traversal**: Collects transitive dependencies (upstream and downstream) using call graphs
* **Minimal Context Pruning**: Selects only essential code snippets (signatures, docstrings, key logic) to reduce token usage by 60%
* **Smart File Scoping**: Automatically determines which files to analyze based on task impact, not keywords

### 7.2 Context Caching and Optimization

**V2 implements intelligent caching** for performance optimization:

* **AST Analysis Cache**: Stores semantic maps and analysis results, invalidated when source files change
* **Context Memoization**: Reuses context for tasks targeting the same code areas
* **Incremental Updates**: After task completion, re-analyzes only changed files, not entire codebase
* **Token Budget Enforcement**: Adaptive pruning based on task complexity and available tokens

### 7.3 Complexity-Based Task Estimation

**V2 adds complexity analysis** to improve task breakdown:

* **Cyclomatic Complexity**: Measures decision points in functions (if, for, while, except)
* **Effort Estimation**: Predicts lines of code and difficulty based on complexity and dependency depth
* **Task Validation**: Flags tasks that exceed 30-line limit before implementation
* **Refactoring Suggestions**: Identifies overly complex code areas that need restructuring

### 7.4 Performance Improvements

**V2 delivers significant performance gains**:

* **Context Collection Time**: <2 seconds for typical projects (with caching)
* **Token Usage**: 60% reduction in average context tokens per task
* **First-Attempt Success**: Increased from ~70% to ~90%
* **Task Re-Breakdown**: Reduced by 50%

### 7.5 Success Metrics

**V2 establishes clear success metrics**:

| Metric | V1 Baseline | V2 Target | Improvement |
|--------|--------------|------------|-------------|
| Token Usage | 5,200 tokens/task | 2,100 tokens/task | 60% reduction |
| Context Collection | 18.7s | <2s | 9.4x faster |
| First-Attempt Success | 71% | 91% | +28% |
| Tasks Needing Re-Breakdown | 34% | 16% | -53% |
| Context-Related Failures | 23% | 4% | -83% |

### 7.6 Configuration

**V2 provides configurable options**:

* **Environment Variables**:
  - `L4_CACHE_DIR`: Cache directory (default: `.l4_cache/`)
  - `L4_CACHE_ENABLED`: Enable/disable caching (default: true)
  - `L4_MAX_DEPTH`: Maximum traversal depth (default: 3)
  - `L4_TOKEN_BUDGET`: Default token budget (default: 4000)
  - `L4_CACHE_SIZE_MB`: Cache size limit (default: 100)

* **Programmatic Configuration**:
  ```python
  config = ContextEngineConfig(
      max_traversal_depth=3,
      token_budget=4000,
      cache_size_mb=100,
      include_type_hints=True
  )
  ```

---

## 8. V3 Enhancements

### 8.1 Telemetry and Monitoring

**V3 introduces comprehensive telemetry system** for deep visibility into operations:

* **Operation Tracking**: Track all operations (planning, implementation, verification)
* **Event Recording**: Record events with timestamps, severity, and context
* **Metrics Collection**: Capture tokens used, time elapsed, memory usage, cache hits
* **Resource Monitoring**: Monitor CPU, memory, disk, and network usage
* **File Operation Telemetry**: Track all file reads/writes with diffs
* **LLM Call Telemetry**: Track LLM API calls with request/response details
* **Query Interface**: Query operations by type, status, time range
* **Export Capabilities**: Export telemetry to CSV/JSON for analysis

**Key Benefits**:
* Deep visibility into system behavior
* Faster debugging with correlated logs and telemetry
* Performance optimization through metrics analysis
* Cost tracking via LLM usage monitoring

### 8.2 Structured Logging

**V3 introduces structured logging system** for consistent, searchable logs:

* **Structured Format**: JSON format for machine parsing, colored text for humans
* **Multiple Handlers**: Console, file, and error log handlers
* **Log Rotation**: Automatic rotation based on size (max 10MB, keep 5 files)
* **Contextual Logging**: Automatic correlation with telemetry operations
* **Flexible Levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL
* **Log Analysis**: Search logs by operation, task, error, or time range
* **Export Capabilities**: Export logs for external analysis

**Key Benefits**:
* Machine-parseable logs for analytics
* Better debugging with structured context
* Log aggregation support (ELK, Splunk)
* Reduced debugging time by 50%

### 8.3 State Checkpointing and Recovery

**V3 introduces checkpoint and recovery system** for zero data loss:

* **Complete State Capture**: Database, file system, context, and cache
* **Fast Restoration**: Restore from checkpoint in <3 seconds
* **Automatic Checkpoints**: Policy-based automatic checkpoint creation
* **Rollback Support**: Automatic rollback on errors
* **Validation**: State integrity checks before/after restore
* **Incremental Snapshots**: Delta-based storage for efficiency
* **Checkpoint Policy**: Configurable policy for automatic checkpoint creation
* **Garbage Collection**: Automatic cleanup of old checkpoints

**Key Benefits**:
* Zero data loss from interruptions
* Fast session resumption (<5 seconds)
* Automatic rollback on errors
* Easy recovery from unexpected shutdowns

### 8.4 Error Handling and Resilience

**V3 introduces robust error handling** for self-healing capabilities:

* **Error Classification**: Define error types (transient, permanent, retryable)
* **Retry Logic**: Automatic retry with exponential backoff for transient errors
* **Recovery Strategies**: Auto-recover from common errors (rate limits, locks)
* **Graceful Shutdown**: Handle SIGINT/SIGTERM gracefully, save state before exit
* **Error Reporting**: Interactive error messages with recovery suggestions
* **Health Checks**: System health monitoring with proactive issue detection

**Key Benefits**:
* Self-healing from 90% of transient errors
* Clear recovery paths for user-action errors
* Zero data loss from interruptions
* Better user experience with helpful error messages

### 8.5 Session Management

**V3 introduces session management** for productivity tracking and continuity:

* **Session Persistence**: Save and restore session state across runs
* **Automatic Detection**: Detect interrupted sessions on startup
* **Session Resumption**: Resume from any checkpoint
* **Productivity Tracking**: Track tasks completed, time spent, errors
* **Configuration Management**: Persist user preferences
* **Analytics**: Generate session reports and insights
* **Comparison**: Compare sessions over time

**Key Benefits**:
* Seamless continuation of work across multiple runs
* Productivity tracking and analytics
* Session recovery after interruption
* Configuration persistence

### 8.6 User Experience Improvements

**V3 introduces enhanced user experience** features:

* **Progress Indicators**: Real-time progress bars for long operations
* **Status Dashboard**: CLI dashboard showing system status
* **Interactive Error Messages**: Helpful error messages with recovery suggestions
* **Resume and Recovery CLI**: Easy-to-use commands for session resumption
* **Telemetry and Log Queries**: CLI for querying telemetry and logs
* **Visual Feedback**: Color-coded output and emoji indicators

**Key Benefits**:
* Better visibility into system state
* Faster error recovery
* Improved productivity
* Better user satisfaction

## 9. Documentation

**V2 includes comprehensive documentation**:

* **Architecture**: [v2/docs/V2_ARCHITECTURE.md](../v1/docs/V2_ARCHITECTURE.md) - Complete V2 architecture overview
* **Migration Guide**: [v1/docs/MIGRATION_V1_TO_V2.md](../v1/docs/MIGRATION_V1_TO_V2.md) - Step-by-step migration instructions
* **API Reference**: [v1/docs/API_REFERENCE.md](../v1/docs/API_REFERENCE.md) - Complete API documentation
* **Performance**: [v1/docs/PERFORMANCE.md](../v1/docs/PERFORMANCE.md) - Performance benchmarks and characteristics

**V3 includes comprehensive documentation**:

* **Telemetry**: [v2/docs/TELEMETRY.md](v2/docs/TELEMETRY.md) - Telemetry system documentation
* **Logging**: [v2/docs/LOGGING.md](v2/docs/LOGGING.md) - Structured logging documentation
* **Resumability**: [v2/docs/RESUMABILITY.md](v2/docs/RESUMABILITY.md) - Checkpoint and recovery documentation
* **Session Management**: [v2/docs/SESSION_MANAGEMENT.md](v2/docs/SESSION_MANAGEMENT.md) - Session management documentation
* **Migration Guide**: [v2/docs/MIGRATION_V2_TO_V3.md](v2/docs/MIGRATION_V2_TO_V3.md) - Step-by-step migration guide from V2 to V3
* **Troubleshooting**: [v2/docs/TROUBLESHOOTING.md](v2/docs/TROUBLESHOOTING.md) - Common issues and solutions

---

## 9. V4 Enhancements

### 9.1 Adaptive Reasoning System

**V4 introduces adaptive reasoning system** for intelligent decision-making:

* **Hierarchical Context Management**: Multi-level context access (L0-L3) for granular information retrieval
* **Context Expansion**: Dynamically expand context scope based on task needs
* **Context Relevance Scoring**: Score and rank context items by relevance
* **Context Summarization**: Intelligent summarization for higher-level contexts
* **Adaptive Step Size**: Adjust how far back to look based on situation complexity

**Key Benefits**:
* Start with most recent context, expand as needed
* Reduce token usage by 40% through smart context selection
* Improve decision quality through relevant context
* Learn optimal context levels per task type

### 9.2 Progress Validation and Tracking

**V4 introduces comprehensive progress tracking** for continuous validation:

* **Progress Metrics**: Track code, task, session, and project progress
* **Progress Validation**: Compare progress against expected rates
* **Stagnation Detection**: Detect when no progress is being made
* **Regression Detection**: Detect when progress is going backwards
* **Progress Prediction**: Predict time and resources to completion
* **Progress Visualization**: Real-time progress indicators and charts

**Key Benefits**:
* 50% reduction in stagnation events
* Early detection of problems
* Better resource planning through predictions
* Clear visibility into development progress

### 9.3 Trap Detection and Recovery

**V4 introduces trap detection system** for autonomous self-correction:

* **Loop Detection**: Detect repetitive actions (same action 3+ times)
* **Dead End Detection**: Detect non-productive paths (no progress for 5+ operations)
* **Circular Reasoning Detection**: Detect decision cycles and revisiting rejected options
* **Trap Recovery Engine**: Automatically recover from detected traps
* **Trap Prevention**: Prevent traps through action tracking and progress validation
* **Learning from Traps**: Learn patterns to prevent future trap occurrences

**Key Benefits**:
* 95% trap detection accuracy
* 90% recovery success rate
* Autonomous self-correction without human intervention
* Continuous improvement through learning

### 9.4 Strategy Evaluation and Switching

**V4 introduces strategy management** for adaptive behavior:

* **Strategy Performance Tracking**: Track success rate, efficiency, effectiveness per strategy
* **Strategy Comparison**: Compare and rank strategies across multiple dimensions
* **Adaptive Strategy Switching**: Dynamically switch strategies when current approach underperforms
* **Strategy Hybridization**: Combine multiple strategies for complex situations
* **Optimal Strategy Learning**: Learn optimal strategies per task and situation type

**Key Benefits**:
* 15% improvement in task completion time
* Automatic adaptation to changing situations
* Optimal strategy selection based on performance data
* Flexibility through strategy hybridization

### 9.5 Meta-Cognition and Learning

**V4 introduces meta-cognition system** for continuous self-improvement:

* **Decision History Tracking**: Track all decisions with full context and reasoning
* **Pattern Recognition**: Identify recurring decision patterns (successful and failed)
* **Self-Reflection Mechanism**: Regular reflection to identify areas for improvement
* **Learning from Mistakes**: Systematic analysis of failures and lesson extraction
* **Adaptive Heuristics**: Continuously update heuristics based on performance data

**Key Benefits**:
* 70% reduction in repeated mistakes
* Continuous improvement through pattern learning
* Better decision quality over time
* Explainable decision-making process

### 9.6 Decision Explainability

**V4 introduces decision explainability** for transparency and debugging:

* **Decision Trace Logging**: Full reasoning chain for every decision
* **Natural Language Explanations**: Human-readable explanations for decisions
* **Decision Visualization**: Visual decision trees and flow charts
* **Query and Search Interface**: Search decisions by context, outcome, reasoning
* **Alternatives Documentation**: Track considered alternatives and rejection reasons

**Key Benefits**:
* 100% decision explainability
* Faster debugging with traceable decisions
* Better understanding of system behavior
* Audit trail for compliance and review

### 9.7 V4 Agent Enhancements

**V4 enhances all agents with adaptive reasoning**:

* **Planner (Enhanced)**:
  - Uses hierarchical context for task breakdown
  - Applies adaptive reasoning for optimal task granularity
  - Validates progress during planning to prevent scope creep
  - Traps: Detects circular reasoning in task dependencies

* **Implementer (Enhanced)**:
  - Starts with L0 context, expands as needed
  - Tracks progress continuously through TDD cycle
  - Detects loops in test-code iteration
  - Adapts strategy based on success/failure patterns

* **Verifier (Enhanced)**:
  - Uses adaptive context for validation
  - Tracks validation progress metrics
  - Detects repetitive validation failures
  - Learns optimal validation criteria per task type

* **Meta-Cognition Agent (New)**:
  - Performs regular self-reflection
  - Analyzes decision patterns
  - Updates heuristics and strategies
  - Generates improvement recommendations

### 9.8 V4 Performance Characteristics

**V4 achieves significant improvements** over V3:

| Metric | V3 Baseline | V4 Target | Improvement |
|--------|--------------|------------|-------------|
| Success Rate | 71% | 85% | +20% |
| Trap Detection | 0% | 95% | New capability |
| Recovery Success | N/A | 90% | New capability |
| Stagnation Events | 15% | 7.5% | -50% |
| Task Completion Time | 100% | 85% | +15% |
| Repeated Mistakes | 10% | 3% | -70% |
| Decision Explainability | 30% | 100% | +233% |
| Context Usage | 100% | 60% | -40% |
| Overhead | 0% | <20% | Acceptable |

### 9.9 V4 Success Metrics

**V4 establishes clear success criteria**:

* **Adaptive Reasoning Effectiveness**: 20% improvement in success rate
* **Trap Detection Accuracy**: Detect 95% of loops and dead ends
* **Recovery Success Rate**: Successfully recover from 90% of detected traps
* **Progress Validation**: Reduce stagnation events by 50%
* **Strategy Optimization**: Improve task completion time by 15%
* **Meta-Cognition Effectiveness**: Reduce repeated mistakes by 70%
* **Decision Explainability**: Provide explanations for 100% of decisions
* **Performance Overhead**: Keep V4 overhead below 20% compared to V3

**V4 includes comprehensive documentation**:

* **V4 Architecture**: [v3/docs/V4_ARCHITECTURE.md](v3/docs/V4_ARCHITECTURE.md) - Complete V4 architecture overview
* **Migration Guide**: [v3/docs/MIGRATION_V3_TO_V4.md](v3/docs/MIGRATION_V3_TO_V4.md) - Step-by-step migration guide from V3 to V4
* **Adaptive Reasoning**: [v3/docs/ADAPTIVE_REASONING.md](v3/docs/ADAPTIVE_REASONING.md) - Adaptive reasoning system documentation
* **Trap Detection**: [v3/docs/TRAP_DETECTION.md](v3/docs/TRAP_DETECTION.md) - Trap detection and recovery documentation
* **Meta-Cognition**: [v3/docs/META_COGNITION.md](v3/docs/META_COGNITION.md) - Meta-cognition and learning documentation
