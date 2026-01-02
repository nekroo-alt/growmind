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

### B. The Implementer (TDD Agent)

*   **Logic**: Follows the Red-Green-Refactor cycle.
    1.  **Red**: Writes a failing test case based on the Task Acceptance Criteria.
    2.  **Green**: Writes the minimal code to pass the test.
    3.  **Refactor**: Cleans code while maintaining test integrity.
*   **Constraint**: Must respect the **Open-Closed Principle**. It prefers adding new classes/functions over modifying existing stable ones.

### C. The Acceptance Agent (The Critic)

*   **Role**: Acts as a "Gatekeeper" before a Git commit is finalized.
*   **Validation**:
    *   Runs the full test suite (not just the new test).
    *   Performs **Mutation Testing**: Briefly modifies the code to ensure the new test actually fails when logic is broken.
    *   Checks the 30-line limit.

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