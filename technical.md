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

---

## 2. Module Hierarchy Reference

| Module | Responsibility |
| :--- | :--- |
| **Core** | Entry point, CLI, and high-level Orchestration loop. |
| **Data** | SQLite schema management and Markdown CRUD (Context Bank access). |
| **Logic** | Agent definitions: Git Guard, Task Dispatcher, Planner, Implementor, and Verifier. |
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

### Module 3: `logic/planner.py` (The Breakdown Agent)
Only invoked when `task.db` is empty or a task is too complex.

*   **Input:** Requirements from `product.md` and architecture from `technical.md`.
*   **Output:** New atomic task rows inserted into `task.db` with specific Acceptance Criteria.

### Module 4: `logic/implementor.py` (TDD Agent)
Implements the core **Common Flow**.

*   **TDD Loop:** Executes the Red-Green-Refactor cycle.
*   **Commit Guard:** After a successful "Green" phase and verification, performs a Git commit.
*   **Context Update:** Updates `activity.db` with the reasoning and results of the implementation.

### Module 5: `retro/retro_agent.py` (The Retro Flow)
A separate process triggered when a human modifies a file or overrides a commit.

*   **Diff Analysis:** Uses the LLM to compare the AI's version in `activity.db` with the human's manual correction.
*   **Pattern Extraction:** Extracts "Project-Specific" rules (e.g., specific naming conventions or library preferences).
*   **Knowledge Persistence:** Updates `.patterns/coding_style.md` to be injected into future system prompts.

### Module 6: `data/db_manager.py` (Context Bank Access)
Abstracts all interactions with `task.db` and `activity.db`.

*   **Schema Enforcement:** Ensures the SQLite tables for tasks and activity logs are properly structured.
*   **Static Guard:** Provides methods to read `product.md` and `technical.md` without modifying them during standard execution cycles.

---

## 4. Operational Flow Summary

| Step | Flow | Action | Module Involved |
| :--- | :--- | :--- | :--- |
| 1 | Initialization | Load static docs (Cold Start) | `core/start.py` |
| 2 | Pre-flight | Check Git status is clean | `logic/git_guard` |
| 3 | Fetch | Pick existing task from `task.db` | `logic/dispatcher.py` |
| 4 | (Optional) Plan | Break down complex/new requirements | `logic/planner.py` |
| 5 | Execute | TDD Cycle (Red/Green/Refactor) | `logic/implementor.py` |
| 6 | Learning | Analyze Human overrides (Retro Flow) | `retro/retro_agent.py` |
