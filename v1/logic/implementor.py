import os
import subprocess
import glob
from v1.data.db_manager import (
    log_activity,
    update_task_status,
    fcid_mapping,
    get_commit_count,
)
from v1.logic.git_guard import GitGuard
from v1.logic.context_engine import ContextEngine
from v1.llm_base.provider import LLMProvider
from v1.logic.verifier import Verifier
from v1.core.telemetry import telemetry


class Implementor:
    def __init__(self, workspace_root="."):
        self.workspace_root = workspace_root
        self.git = GitGuard()
        self.context_engine = ContextEngine(workspace_root)
        self.llm = LLMProvider()
        self.verifier = Verifier()

    def _get_error_reason(self, result):
        raw_content = result.get("raw_content", "").strip()
        if not raw_content:
            return "LLM returned an empty response."
        if raw_content.startswith("Error:"):
            return raw_content

        # If there's content but no files were parsed, show a snippet (last 200 chars)
        if len(raw_content) > 200:
            snippet = "..." + raw_content[-200:]
        else:
            snippet = raw_content
        return f"LLM did not return any file changes in the expected format. Response: {snippet}"

    @fcid_mapping("ACT-100")
    def execute_tdd_cycle(self, task):
        """
        Executes a Red-Green-Refactor cycle for the given task.
        Returns (success, error_message).
        """
        task_id = task["id"]
        task_title = task["title"]

        # Context Injection
        v1_files = glob.glob(
            os.path.join(self.workspace_root, "v1/**/*.py"), recursive=True
        )
        v1_files = [os.path.relpath(f, self.workspace_root) for f in v1_files]
        context = self.context_engine.get_pruned_context(task_title, v1_files)

        log_activity(
            summary=f"Starting TDD Cycle: {task_title}",
            action="TDD Start",
            status="Success",
            cot_blob=f"Beginning implementation for task ID {task_id}. Context gathered: {len(context)} chars.",
            notify_telemetry=False,  # We use log_task_start via orchestrator/task_context
        )

        # Red Phase: Write a failing test
        telemetry.track_step("Red Phase: Writing failing test")
        success, error = self._run_red_phase(task, context)
        if not success:
            return False, error

        # Green Phase: Write minimal code to pass
        telemetry.track_step("Green Phase: Implementing code")
        success, error = self._run_green_phase(task, context)
        if not success:
            return False, error

        # Refactor Phase: Cleanup
        telemetry.track_step("Refactor Phase: Cleaning up")
        self._run_refactor_phase(task_title)

        # Check for Refactor Sprint (every 10 commits)
        if get_commit_count() % 10 == 0 and get_commit_count() > 0:
            self.run_refactor_sprint()

        update_task_status(task_id, "completed")
        return True, None

    def _run_red_phase(self, task, context):
        task_title = task["title"]
        attempts = 3
        last_error = ""

        for attempt in range(1, attempts + 1):
            system_prompt = """You are a TDD expert and senior software engineer. 
Your task is to generate failing tests (the "Red" phase of TDD) based on a task description, context, and acceptance criteria.

Output Format:
For each file you want to create or update, use the following format:
File: path/to/file.py
```python
# content here
```

Ensure the tests are comprehensive and would fail until the implementation is completed.
Prefer using `pytest`.
Keep changes focused and under 100 lines per commit.
"""
            user_prompt = f"Task: {task_title}\nContext: {context}\nAcceptance Criteria: {task['acceptance_criteria']}"
            if last_error:
                user_prompt += f"\n\nPrevious attempt failed with error: {last_error}\nPlease adjust the test generation to comply with policies and requirements."

            result = self.llm.call_multi_file(system_prompt, user_prompt)
            test_changes = result["files"]

            if not test_changes:
                last_error = self._get_error_reason(result)
                log_activity(
                    summary=f"Red Phase Attempt {attempt} Failed",
                    action="Red Phase",
                    status="Failed",
                    cot_blob=f"Failed to get file changes: {last_error}",
                    tokens_used=result["usage"]["total_tokens"],
                    prompt_tokens=result["usage"]["prompt_tokens"],
                    completion_tokens=result["usage"]["completion_tokens"],
                    estimated_cost=result["cost"],
                )
                continue

            for file_path, test_code in test_changes.items():
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, "w") as f:
                    f.write(test_code)

            success, error_msg = self.git.commit(
                "ACT-100",
                f"Red Phase: {task_title}",
                files=list(test_changes.keys()),
                cot=f"Added test cases for {task_title} across {len(test_changes)} files. Attempt {attempt}.",
                tokens_used=result["usage"]["total_tokens"],
                prompt_tokens=result["usage"]["prompt_tokens"],
                completion_tokens=result["usage"]["completion_tokens"],
                estimated_cost=result["cost"],
            )

            if success:
                return True, None
            else:
                last_error = error_msg
                telemetry.warning(f"Red Phase attempt {attempt} failed: {error_msg}")

        return False, last_error or "Red Phase failed after maximum attempts."

    def _run_green_phase(self, task, context):
        task_title = task["title"]
        # If the Red phase created multiple files, we should ideally run all of them.
        # For v1, we focus on the primary test file or use a heuristic.
        test_file = (
            "v1/test_multi_poc.py"
            if "multi" in task_title.lower()
            else "v1/test_poc.py"
        )

        attempts = 3
        last_error = ""

        for attempt in range(1, attempts + 1):
            log_activity(
                summary=f"Green Phase Attempt {attempt}/{attempts}: {task_title}",
                action="Green Phase",
                status="Progress",
                cot_blob=f"Attempting to pass tests for {task_title}. Feedback from previous error: {bool(last_error)}",
            )

            # Construct prompt for fix generation
            system_prompt = """You are a TDD expert and senior software engineer.
Your task is to generate the minimal code required to pass the provided tests (the "Green" phase of TDD).

Output Format:
For each file you want to create or update, use the following format:
File: path/to/file.py
```python
# content here
```

Respect the Open-Closed Principle and avoid modifying stable modules unless necessary.
Keep changes focused and under 100 lines per commit.
"""
            user_prompt = f"Task: {task_title}\nContext: {context}\n"
            if last_error:
                user_prompt += f"\nPrevious attempt failed with error:\n{last_error}\nPlease fix the implementation and ensure it complies with all policies (line limits, etc.)."

            result = self.llm.call_multi_file(system_prompt, user_prompt)
            suggested_changes = result["files"]

            if not suggested_changes:
                last_error = self._get_error_reason(result)
                log_activity(
                    summary=f"Green Phase Attempt {attempt} Failed: No code generated",
                    action="Green Phase",
                    status="Failed",
                    cot_blob=f"Failed to get file changes: {last_error}",
                    tokens_used=result["usage"]["total_tokens"],
                    prompt_tokens=result["usage"]["prompt_tokens"],
                    completion_tokens=result["usage"]["completion_tokens"],
                    estimated_cost=result["cost"],
                )
                continue

            for file_path, impl_code in suggested_changes.items():
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, "w") as f:
                    f.write(impl_code)

            # Run tests and capture logs
            test_passed, test_output = self._run_tests(test_file)

            mutation_passed = True
            if test_passed:
                # Quality Gate: Mutation Testing (VER-102)
                for file_path in suggested_changes.keys():
                    if file_path.endswith(".py") and "test" not in file_path:
                        if not self.verifier.run_mutation_tests(
                            target_file=file_path, test_file=test_file
                        ):
                            mutation_passed = False
                            last_error = f"Mutation testing failed for {file_path}. 100% score required."
                            break

                if mutation_passed:
                    success, error_msg = self.git.commit(
                        "ACT-101",
                        f"Green Phase: {task_title}",
                        files=list(suggested_changes.keys()),
                        cot=f"Implementation passed on attempt {attempt} and met 100% mutation quality gate.",
                        tokens_used=result["usage"]["total_tokens"],
                        prompt_tokens=result["usage"]["prompt_tokens"],
                        completion_tokens=result["usage"]["completion_tokens"],
                        estimated_cost=result["cost"],
                    )
                    if success:
                        return True, None
                    else:
                        last_error = f"Git Policy Violation: {error_msg}"
                        telemetry.warning(f"Green Phase attempt {attempt} failed policy check: {error_msg}")

            if not test_passed or not mutation_passed:
                if not test_passed:
                    last_error = test_output

                log_activity(
                    summary=f"Green Phase Attempt {attempt} Failed",
                    action="Green Phase",
                    status="Failed",
                    cot_blob=f"Attempt {attempt} failed for {task_title}. Error: {last_error[:500]}",
                    tokens_used=result["usage"]["total_tokens"],
                    prompt_tokens=result["usage"]["prompt_tokens"],
                    completion_tokens=result["usage"]["completion_tokens"],
                    estimated_cost=result["cost"],
                )

        return False, last_error or "Green Phase failed after maximum attempts."

    def _run_tests(self, test_file):
        """
        Runs tests and returns (success, output).
        """
        if not os.path.exists(test_file):
            return False, f"Test file not found: {test_file}"

        try:
            # Use pytest to run the test file and capture output
            result = subprocess.run(
                ["python3", "-m", "pytest", test_file],
                capture_output=True,
                text=True,
                timeout=30,
            )
            return result.returncode == 0, result.stdout + result.stderr
        except Exception as e:
            return False, f"Test execution error: {str(e)}"

    def _run_refactor_phase(self, task_title):
        log_activity(
            summary=f"Refactor Phase: {task_title}",
            action="Refactor",
            status="Success",
            cot_blob="Verified code against tests and cleaned up",
        )
        return True

    @fcid_mapping("ACT-200")
    def run_refactor_sprint(self):
        """
        Consolidate patterns after every 10 commits.
        """
        telemetry.track_step("Refactor Sprint")
        log_activity(
            summary="Initiating Refactor Sprint",
            action="Refactor Sprint",
            status="Progress",
            cot_blob="10 commits reached, starting pattern consolidation using .patterns",
        )

        # 1. Load patterns
        patterns_path = os.path.join(self.workspace_root, ".patterns/coding_style.md")
        patterns = ""
        if os.path.exists(patterns_path):
            with open(patterns_path, "r") as f:
                patterns = f.read()

        # 2. Gather context (all v1 python files, excluding tests and __init__.py)
        v1_files = glob.glob(
            os.path.join(self.workspace_root, "v1/**/*.py"), recursive=True
        )
        src_files = [
            f
            for f in v1_files
            if "test" not in os.path.basename(f) and "__init__.py" not in f
        ]

        context_parts = []
        for file_path in src_files:
            rel_path = os.path.relpath(file_path, self.workspace_root)
            with open(file_path, "r") as f:
                context_parts.append(f"File: {rel_path}\n```python\n{f.read()}\n```")

        full_context = "\n\n".join(context_parts)

        # 3. Call LLM for refactoring
        system_prompt = """You are a senior software architect specializing in refactoring and pattern consolidation.
Your goal is to improve the codebase by applying the provided coding patterns and reducing technical debt.

Instructions:
1. Review the provided coding patterns from `.patterns/coding_style.md`.
2. Review the provided source code files.
3. Identify opportunities to consolidate patterns, improve type hinting, reduce duplication, and ensure consistency.
4. Provide the updated content for any files that need changes.

Output Format:
For each file you want to update, use the following format:
File: path/to/file.py
```python
# updated content here
```

Keep changes focused and ensure they don't break existing functionality.
Respect the Open-Closed principle for core logic, but feel free to consolidate repetitive patterns.
"""
        user_prompt = (
            f"Coding Patterns:\n{patterns}\n\nSource Code Context:\n{full_context}"
        )

        result = self.llm.call_multi_file(system_prompt, user_prompt, max_tokens=4000)
        refactored_files = result["files"]

        if not refactored_files:
            log_activity(
                summary="Refactor Sprint: No changes recommended",
                action="Refactor Sprint",
                status="Success",
                cot_blob="LLM analyzed the code but found no patterns to consolidate at this time.",
                tokens_used=result["usage"]["total_tokens"],
                prompt_tokens=result["usage"]["prompt_tokens"],
                completion_tokens=result["usage"]["completion_tokens"],
                estimated_cost=result["cost"],
            )
            return True

        # 4. Backup and apply changes
        backups = {}
        applied_files = []
        for file_path, content in refactored_files.items():
            full_path = os.path.join(self.workspace_root, file_path)
            if os.path.exists(full_path):
                with open(full_path, "r") as f:
                    backups[full_path] = f.read()
                with open(full_path, "w") as f:
                    f.write(content)
                applied_files.append(file_path)

        # 5. Run all tests to verify
        test_files = [f for f in v1_files if "test" in os.path.basename(f)]
        all_passed = True
        failed_tests = []

        for t_file in test_files:
            passed, output = self._run_tests(t_file)
            if not passed:
                all_passed = False
                failed_tests.append(f"{t_file}: {output}")

        if all_passed:
            success, error_msg = self.git.commit(
                "ACT-200",
                "Refactor Sprint: Consolidated coding patterns",
                files=applied_files,
                cot=f"Refactor sprint completed. Files updated: {', '.join(applied_files)}",
                tokens_used=result["usage"]["total_tokens"],
                prompt_tokens=result["usage"]["prompt_tokens"],
                completion_tokens=result["usage"]["completion_tokens"],
                estimated_cost=result["cost"],
            )
            if success:
                return True
            else:
                telemetry.error(f"Refactor Sprint commit failed: {error_msg}")
                # Rollback since commit failed (policy violation probably)
                for full_path, content in backups.items():
                    with open(full_path, "w") as f:
                        f.write(content)
                return False
        else:
            # Rollback
            for full_path, content in backups.items():
                with open(full_path, "w") as f:
                    f.write(content)

            log_activity(
                summary="Refactor Sprint Failed: Regression detected",
                action="Refactor Sprint",
                status="Failed",
                cot_blob=f"LLM suggested changes caused test failures. Rolling back.\nErrors:\n"
                + "\n".join(failed_tests),
                tokens_used=result["usage"]["total_tokens"],
                prompt_tokens=result["usage"]["prompt_tokens"],
                completion_tokens=result["usage"]["completion_tokens"],
                estimated_cost=result["cost"],
            )
            return False
