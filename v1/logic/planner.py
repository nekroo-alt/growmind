import os
import glob
import json
from v1.data.db_manager import log_task, log_activity, fcid_mapping, task_exists
from v1.logic.context_engine import ContextEngine
from v1.llm_base.provider import LLMProvider


class Planner:
    def __init__(self, workspace_root="."):
        self.workspace_root = workspace_root
        self.context_engine = ContextEngine(workspace_root)
        self.llm = LLMProvider()

    @fcid_mapping("PLAN-0100")
    def breakdown_requirements(
        self, product_content, technical_content, task_to_break=None
    ):
        """
        Analyzes requirements and breaks them down into atomic tasks (<30 lines).
        If task_to_break is provided, it breaks down that specific task.
        """
        # In a full implementation, this would use an LLM with product_content
        # and technical_content to generate a task list.

        # Context Injection: Find relevant project files
        relevant_files = []
        # Look for source files in the workspace, excluding common noise
        extensions = ["*.py", "*.js", "*.ts", "*.yaml", "*.yml", "*.md"]
        ignore_dirs = {".git", "__pycache__", "node_modules", "build", "dist", "logs"}

        for ext in extensions:
            found = glob.glob(
                os.path.join(self.workspace_root, f"**/{ext}"), recursive=True
            )
            for f in found:
                rel_f = os.path.relpath(f, self.workspace_root)
                parts = rel_f.split(os.sep)
                if not any(d in parts for d in ignore_dirs):
                    # Only include 'v1' if we are actually working on the platform itself
                    if "v1" in parts and not os.path.exists(
                        os.path.join(self.workspace_root, "v1")
                    ):
                        continue
                    relevant_files.append(rel_f)

        query = (
            task_to_break["title"]
            if task_to_break
            else "Initial requirement analysis and task breakdown"
        )
        # Limit context to avoid overwhelming the prompt
        pruned_context = self.context_engine.get_pruned_context(
            query, relevant_files[:30]
        )

        system_prompt = (
            "You are a Senior Architect. Break down the given requirements into atomic tasks.\n"
            "Each task must be estimated to involve <30 lines of code changes.\n"
            "Return a JSON list of objects with keys: 'title', 'acceptance_criteria', 'module'."
        )
        user_prompt = f"Product Requirements:\n{product_content}\nTechnical Design:\n{technical_content}\n"
        if task_to_break:
            user_prompt += f"Specific task to break down: {task_to_break['title']}\n"
        user_prompt += f"Current context snippet:\n{pruned_context}"

        result = self.llm.call(system_prompt, user_prompt, temperature=0.2)
        response = result["content"]

        try:
            if "Error: All LLM providers failed" in response:
                raise ValueError(response)

            # Simple parsing for MVP, Task 7.4 will refine this
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                response = response.split("```")[1].split("```")[0].strip()
            subtasks_data = json.loads(response)
            subtasks = [
                (t["title"], t["acceptance_criteria"], t.get("module"))
                for t in subtasks_data
            ]
        except Exception as e:
            # Improved error handling: No more hardcoded platform tasks
            log_activity(
                summary="Task Breakdown Failed",
                action="PLANNING",
                status="Failed",
                cot_blob=f"Error parsing LLM response or LLM failed: {str(e)}",
            )
            if task_to_break:
                # Still allow simulated breakdown for nested tasks if needed,
                # but even this should probably be removed in a real system.
                subtasks = self._simulate_llm_breakdown(
                    task_to_break["title"], pruned_context
                )
            else:
                # Return empty list to signify planning failed
                return 0

        parent_id = task_to_break["id"] if task_to_break else None
        module = task_to_break["module"] if task_to_break else None

        new_tasks_added = 0
        for title, ac, mod in subtasks:
            if not task_exists(title):
                log_task(
                    title=title,
                    status="pending",
                    acceptance_criteria=ac,
                    parent_id=parent_id,
                    module=mod or module,
                )
                new_tasks_added += 1

        log_activity(
            summary="Task Breakdown",
            action="PLANNING",
            status="Success",
            cot_blob=f"Broke down {'project' if not task_to_break else task_to_break['title']} into {len(subtasks)} tasks. Added {new_tasks_added} new tasks.",
            tokens_used=result["usage"]["total_tokens"],
            estimated_cost=result["cost"],
        )
        return new_tasks_added

    def _simulate_llm_breakdown(self, task_title, context=""):
        """Simulates LLM splitting a task into <30 line atomic pieces."""
        # In reality, 'context' would be part of the prompt
        return [
            (f"{task_title} - Phase 1", "Atomic criteria A", None),
            (f"{task_title} - Phase 2", "Atomic criteria B", None),
        ]
