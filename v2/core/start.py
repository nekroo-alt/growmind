import os
import sys
from v1.data.db_manager import (
    log_activity,
    fcid_mapping,
    init_db,
    get_cost_summary,
    get_completed_tasks_count,
    save_state,
    load_state,
    update_task_status,
)
from v1.llm_base.provider import LLMProvider
from v1.logic.git_guard import GitGuard
from v1.logic.dispatcher import Dispatcher
from v1.logic.planner import Planner
from v1.logic.implementor import Implementor
from v1.logic.verifier import Verifier
from v1.core.telemetry import telemetry
from v1.retro.retro_agent import RetroAgent


class Orchestrator:
    def __init__(self):
        self.git_guard = GitGuard()
        self.dispatcher = Dispatcher()
        self.planner = Planner()
        self.implementor = Implementor()
        self.verifier = Verifier()
        self.telemetry = telemetry
        self.retro_agent = RetroAgent()

    @fcid_mapping("CORE-100")
    def cold_start_check(self):
        """
        Ensures databases and required files exist.
        """
        self.telemetry.info("Performing cold start check...")
        # 1. Database Initialization
        init_db()

        # 2. Required Files Check
        required_files = ["product.md", "technical.md"]
        missing_files = [f for f in required_files if not os.path.exists(f)]

        if missing_files:
            error_msg = f"Missing required files: {', '.join(missing_files)}"
            log_activity(
                summary="Cold Start Check",
                action="initialization",
                status="Failed",
                cot_blob=error_msg,
            )
            self.telemetry.error(error_msg)
            return False

        log_activity(
            summary="Cold Start Check",
            action="initialization",
            status="Success",
            cot_blob="All required static documents found.",
        )
        self.telemetry.info("Cold start check passed.")
        return True

    def _update_telemetry_stats(self, current_task=None):
        tokens, cost, p_tokens, c_tokens = get_cost_summary()
        tasks_done = get_completed_tasks_count()
        self.telemetry.update_dashboard(
            task=current_task,
            tokens=tokens,
            cost=cost,
            tasks_completed=tasks_done,
            prompt_tokens=p_tokens,
            completion_tokens=c_tokens,
        )

    @fcid_mapping("CORE-101")
    def run(self):
        """
        Main orchestration loop.
        """
        self.telemetry.start_dashboard()
        self.telemetry.info("Starting L4 Auto-Pilot Orchestrator...")

        # Start Retro Watcher
        self.retro_agent.start_watcher()

        try:
            # 1. Cold Start Check
            if not self.cold_start_check():
                self.telemetry.error(
                    "Cold start check failed. Ensure product.md and technical.md are present."
                )
                return

            # State Recovery
            last_state = load_state("orchestrator_phase")
            preferred_id = None
            if last_state:
                self.telemetry.info(f"Detected previous state: {last_state}")
                if last_state == "terminal":
                    self.telemetry.warning(
                        "Last session ended in terminal state (no more tasks)."
                    )
                elif last_state.startswith("implementing:"):
                    parts = last_state.split(":")
                    if len(parts) >= 2:
                        try:
                            preferred_id = int(parts[1])
                            self.telemetry.info(
                                f"Attempting to resume task ID: {preferred_id}"
                            )
                        except ValueError:
                            self.telemetry.warning(
                                "Could not parse task ID from state."
                            )

                log_activity(
                    summary="Orchestrator Resumed",
                    action="resume",
                    status="Success",
                    cot_blob=f"Resuming from state: {last_state}",
                )

            # 2. Git Guard Pre-flight
            if not self.git_guard.is_clean():
                self.telemetry.error(
                    "Git workspace is dirty. Please commit or stash your changes."
                )
                return

            # 3. Main Loop
            while True:
                save_state("orchestrator_phase", "dispatching")
                self._update_telemetry_stats("Dispatching next task...")
                action, task = self.dispatcher.dispatch(preferred_id)
                preferred_id = None  # Reset after first use

                if action == "PLAN":
                    save_state("orchestrator_phase", "planning")
                    self.telemetry.log_task_start("Planning Phase")
                    self._update_telemetry_stats("Planning...")

                    with open("product.md", "r") as f:
                        product_content = f.read()
                    with open("technical.md", "r") as f:
                        technical_content = f.read()

                    new_tasks_count = self.planner.breakdown_requirements(
                        product_content, technical_content
                    )
                    if new_tasks_count == 0:
                        self.telemetry.warning(
                            "Planner could not generate new tasks. Hitting terminal state."
                        )
                        save_state("orchestrator_phase", "terminal")
                        break

                    self.telemetry.log_task_success(
                        f"Generated {new_tasks_count} new tasks."
                    )
                    save_state("orchestrator_phase", "idle")

                elif action == "IMPLEMENT":
                    task_id = task["id"]
                    task_title = task["title"]
                    save_state(
                        "orchestrator_phase", f"implementing:{task_id}:{task_title}"
                    )

                    with self.telemetry.task_context(
                        f"Implementing: {task_title}"
                    ) as outcome:
                        self._update_telemetry_stats()

                        try:
                            success, error_reason = self.implementor.execute_tdd_cycle(
                                task
                            )

                            if success:
                                self.telemetry.info(
                                    f"Task '{task_title}' implementation finished. Running verification..."
                                )
                                self.telemetry.track_step("Verification")
                                self._update_telemetry_stats()

                                # Verifier check
                                # Note: Ideally verifier.run_tests should also return more info
                                if not self.verifier.run_tests():
                                    reason = f"Final verification tests failed after implementation of '{task_title}'."
                                    self.telemetry.error(f"{reason} Marking as blocked.")
                                    update_task_status(task_id, "blocked", reason=reason)
                                    outcome["success"] = False
                            else:
                                if LLMProvider.is_quota_error(error_reason):
                                    self.telemetry.warning(
                                        f"LLM Quota/Billing issue detected: {error_reason}. Not marking task as blocked."
                                    )
                                else:
                                    self.telemetry.error(
                                        f"TDD cycle failed for '{task_title}': {error_reason}. Marking as blocked."
                                    )
                                    update_task_status(
                                        task_id, "blocked", reason=error_reason
                                    )
                                outcome["success"] = False
                        except Exception as e:
                            reason = f"Unexpected error during implementation: {str(e)}"
                            if LLMProvider.is_quota_error(reason):
                                self.telemetry.warning(
                                    f"LLM Quota/Billing issue detected: {reason}. Not marking task as blocked."
                                )
                            else:
                                self.telemetry.error(
                                    f"Unexpected error during implementation of '{task_title}': {str(e)}"
                                )
                                update_task_status(task_id, "blocked", reason=reason)
                            outcome["success"] = False

                else:
                    self.telemetry.warning(
                        "Unknown action received from dispatcher or no more tasks."
                    )
                    break

                self._update_telemetry_stats()

        finally:
            self.retro_agent.stop_watcher()
            self.telemetry.stop_dashboard()


if __name__ == "__main__":
    orchestrator = Orchestrator()
    orchestrator.run()
