import os
import sys
from v3.data.db_manager import (
    log_activity,
    fcid_mapping,
    init_db,
    get_cost_summary,
    get_completed_tasks_count,
    save_state,
    load_state,
    update_task_status,
)
from v3.llm_base.provider import LLMProvider
from v3.logic.git_guard import GitGuard
from v3.logic.dispatcher import Dispatcher
from v3.logic.planner import Planner
from v3.logic.implementor import Implementor
from v3.logic.verifier import Verifier
from v3.core.telemetry import telemetry
from v3.retro.retro_agent import RetroAgent
from v3.core.session_manager import get_session_manager, SessionStatus
from v3.data.checkpoint_manager import CheckpointManager
from v3.core.logging_config import (
    get_module_logger,
    log_operation_started,
    log_operation_completed,
    log_operation_failed,
    log_task_started,
    log_task_completed,
    log_task_failed,
    log_error_with_context,
)
# V4: Adaptive reasoning components
from v3.data.context_hierarchy import get_context_hierarchy
from v3.data.decision_history import get_decision_history
from v3.logic.reasoning_engine import get_reasoning_engine

logger = get_module_logger(__name__)


class Orchestrator:
    def __init__(self):
        logger.info("Initializing Orchestrator")
        self.git_guard = GitGuard()
        self.dispatcher = Dispatcher()  # Now has __init__ with telemetry_manager
        self.planner = Planner()
        self.implementor = Implementor()
        self.verifier = Verifier()
        self.telemetry = telemetry
        self.retro_agent = RetroAgent()

        # Session management
        self.session_manager = get_session_manager()
        self.checkpoint_manager = CheckpointManager()
        self.current_session = None
        
        # V4: Adaptive reasoning components
        self.context_hierarchy = get_context_hierarchy()
        self.decision_history = get_decision_history()
        self.reasoning_engine = get_reasoning_engine()
        logger.info("Orchestrator initialized successfully with V4 adaptive reasoning")

    @fcid_mapping("CORE-100")
    def cold_start_check(self):
        """
        Ensures databases and required files exist.
        """
        logger.info("Cold start check started")
        self.telemetry.info("Performing cold start check...")
        # 1. Database Initialization
        init_db()
        logger.info("Database initialized")

        # 2. Required Files Check
        required_files = ["product.md", "technical.md"]
        missing_files = [f for f in required_files if not os.path.exists(f)]

        if missing_files:
            error_msg = f"Missing required files: {', '.join(missing_files)}"
            logger.error(error_msg, missing_files=missing_files)
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
        logger.info("Cold start check completed successfully")
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

    def _handle_interrupted_sessions(self):
        """
        Detect and handle interrupted sessions on startup.

        Returns:
            True if resuming a session, False otherwise
        """
        # Detect interrupted sessions
        interrupted = self.session_manager.detect_interrupted_sessions()

        if not interrupted:
            return False

        self.telemetry.info(f"Found {len(interrupted)} interrupted session(s)")

        # For now, just resume the most recent one
        # In production, provide interactive selection
        session = interrupted[0]
        self.telemetry.info(f"Resuming session {session.session_id}")

        # Check for external changes
        restored_session, has_external_changes = (
            self.session_manager.restore_session_on_startup(
                session.session_id, self.checkpoint_manager
            )
        )

        if has_external_changes:
            self.telemetry.warning(
                "External changes detected. Please resolve conflicts manually before proceeding."
            )
            # In production, provide merge options
            return False

        if restored_session:
            self.current_session = restored_session
            self.telemetry.info(
                f"Successfully resumed session {restored_session.session_id}"
            )
            return True

        return False

    def _create_new_session(self):
        """Create a new session for this run."""
        self.current_session = self.session_manager.start_session(
            config={
                "llm_model": os.getenv("L4_LLM_MODEL", "gpt-4"),
                "cache_enabled": os.getenv("L4_CACHE_ENABLED", "true").lower()
                == "true",
            },
            metadata={
                "user": os.getenv("USER", "unknown"),
                "host": os.uname().nodename if hasattr(os, "uname") else "unknown",
                "environment": os.getenv("L4_ENV", "development"),
            },
        )
        self.telemetry.info(f"Started new session {self.current_session.session_id}")

    def _save_session_on_shutdown(self, checkpoint_id=None):
        """Save session state before shutdown."""
        if self.current_session:
            self.session_manager.save_session_on_shutdown(
                self.current_session.session_id, checkpoint_id
            )
            self.telemetry.info("Session saved successfully on shutdown")

    @fcid_mapping("CORE-101")
    def run(self):
        """
        Main orchestration loop.
        """
        logger.info("Orchestrator main loop started")
        self.telemetry.start_dashboard()
        self.telemetry.info("Starting L4 Auto-Pilot Orchestrator...")

        # Start Retro Watcher
        self.retro_agent.start_watcher()

        try:
            # 1. Cold Start Check
            if not self.cold_start_check():
                error_msg = "Cold start check failed. Ensure product.md and technical.md are present."
                logger.error(error_msg)
                self.telemetry.error(error_msg)
                self._save_session_on_shutdown()
                return

            # 2. Handle interrupted sessions
            session_resumed = self._handle_interrupted_sessions()

            if not session_resumed:
                # No session to resume, create new one
                self._create_new_session()

            # State Recovery
            last_state = load_state("orchestrator_phase")
            preferred_id = None
            if last_state:
                self.telemetry.info(f"Detected previous state: {last_state}")
                if last_state == "terminal":
                    self.telemetry.warning(
                        "Last session ended in terminal state (no more tasks)."
                    )
                    logger.warning("Last session ended in terminal state")
                elif last_state.startswith("implementing:"):
                    parts = last_state.split(":")
                    if len(parts) >= 2:
                        try:
                            preferred_id = int(parts[1])
                            self.telemetry.info(
                                f"Attempting to resume task ID: {preferred_id}"
                            )
                            logger.info(f"Attempting to resume task ID: {preferred_id}")
                        except ValueError:
                            self.telemetry.warning(
                                "Could not parse task ID from state."
                            )
                            logger.warning("Could not parse task ID from state")

                log_activity(
                    summary="Orchestrator Resumed",
                    action="resume",
                    status="Success",
                    cot_blob=f"Resuming from state: {last_state}",
                )

            # 3. Git Guard Pre-flight
            if not self.git_guard.is_clean():
                error_msg = (
                    "Git workspace is dirty. Please commit or stash your changes."
                )
                self.telemetry.error(error_msg)
                logger.error(error_msg)
                self._save_session_on_shutdown()
                return

            # 4. Main Loop
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
                        logger.info(
                            f"Starting TDD cycle for task {task_id}: {task_title}"
                        )

                        try:
                            success, error_reason = self.implementor.execute_tdd_cycle(
                                task
                            )

                            if success:
                                logger.info(
                                    f"Task '{task_title}' implementation completed successfully"
                                )
                                self.telemetry.info(
                                    f"Task '{task_title}' implementation finished. Running verification..."
                                )
                                self.telemetry.track_step("Verification")
                                self._update_telemetry_stats()

                                # Verifier check
                                # Note: Ideally verifier.run_tests should also return more info
                                if not self.verifier.run_tests():
                                    reason = f"Final verification tests failed after implementation of '{task_title}'."
                                    self.telemetry.error(
                                        f"{reason} Marking as blocked."
                                    )
                                    logger.error(
                                        f"Verification failed for task {task_id}: {reason}"
                                    )
                                    update_task_status(
                                        task_id, "blocked", reason=reason
                                    )
                                    outcome["success"] = False
                            else:
                                if LLMProvider.is_quota_error(error_reason):
                                    self.telemetry.warning(
                                        f"LLM Quota/Billing issue detected: {error_reason}. Not marking task as blocked."
                                    )
                                    logger.warning(
                                        f"LLM quota error for task {task_id}: {error_reason}"
                                    )
                                else:
                                    self.telemetry.error(
                                        f"TDD cycle failed for '{task_title}': {error_reason}. Marking as blocked."
                                    )
                                    logger.error(
                                        f"TDD cycle failed for task {task_id}: {error_reason}"
                                    )
                                    update_task_status(
                                        task_id, "blocked", reason=error_reason
                                    )
                                outcome["success"] = False
                        except Exception as e:
                            reason = f"Unexpected error during implementation: {str(e)}"
                            log_error_with_context(
                                logger, e, task_id=task_id, task_title=task_title
                            )

                            # V3: Create checkpoint on error
                            checkpoint_id = self.checkpoint_manager.create(
                                reason=f"error_during_task_{task_id}",
                                task_id=task_id,
                                task_title=task_title,
                                error=reason,
                            )
                            logger.info(
                                f"Created checkpoint {checkpoint_id} after error in task {task_id}"
                            )

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
                    logger.warning("Unknown action from dispatcher, exiting loop")
                    break

                self._update_telemetry_stats()

        finally:
            logger.info("Orchestrator shutting down")
            self.retro_agent.stop_watcher()
            self._save_session_on_shutdown()
            self.telemetry.stop_dashboard()
            logger.info("Orchestrator main loop ended")


if __name__ == "__main__":
    orchestrator = Orchestrator()
    orchestrator.run()
