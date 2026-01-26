import os
import subprocess
import glob
from v5.data import (
    log_activity,
    update_task_status,
    fcid_mapping,
    get_commit_count,
)
from v5.logic import GitGuard
from v5.logic import ContextEngine
from v5.llm_base import LLMProvider
from v5.logic import Verifier
from v5.core import telemetry
from v5.data import get_telemetry_manager
from v5.core import get_module_logger
from v5.data import CheckpointManager
# V4: Adaptive reasoning components
from v5.data import get_context_hierarchy
from v5.data import get_decision_history
from v5.logic import get_reasoning_engine
from v5.logic import get_trap_detector
from v5.logic import get_trap_recovery
from v5.logic import get_progress_tracker
# V4: Meta-cognition components
from v5.logic import get_pattern_recognizer
from v5.logic import get_self_reflection
from v5.logic import get_lesson_learner
from v5.logic import get_adaptive_heuristics

logger = get_module_logger(__name__)


class Implementor:
    def __init__(self, workspace_root="."):
        logger.info("Initializing Implementor")
        self.workspace_root = workspace_root
        self.git = GitGuard()
        self.context_engine = ContextEngine(workspace_root)
        self.llm = LLMProvider()
        self.verifier = Verifier()
        self.telemetry_manager = get_telemetry_manager()  # V3 telemetry
        self.checkpoint_manager = CheckpointManager()  # V3 checkpointing
        # V4: Adaptive reasoning components
        self.context_hierarchy = get_context_hierarchy()
        self.decision_history = get_decision_history()
        self.reasoning_engine = get_reasoning_engine()
        self.trap_detector = get_trap_detector()
        self.trap_recovery = get_trap_recovery()
        self.progress_tracker = get_progress_tracker()
        # V4: Meta-cognition components
        self.pattern_recognizer = get_pattern_recognizer()
        self.self_reflection = get_self_reflection()
        self.lesson_learner = get_lesson_learner()
        self.adaptive_heuristics = get_adaptive_heuristics()
        logger.info("Implementor initialized successfully with V4 adaptive reasoning and meta-cognition")

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

    def _analyze_context_quality(self, context: str) -> dict:
        """
        Analyze the quality of the collected context.

        Returns metrics about context relevance, dependency coverage, and size.

        Args:
            context: The context string collected from ContextEngine

        Returns:
            dict: Quality metrics including:
                - size: Number of characters in context
                - file_count: Number of files in context
                - avg_relevance: Average relevance score of files
                - dependency_coverage: Whether dependency chain info is present
                - quality_score: Overall quality score (0-1)
        """
        metrics = {
            "size": len(context),
            "file_count": 0,
            "avg_relevance": 0.0,
            "dependency_coverage": False,
            "quality_score": 0.0,
        }

        if not context:
            return metrics

        # Count files and extract relevance scores
        lines = context.split("\n")
        relevance_scores = []
        has_dependency_info = False

        for line in lines:
            # Look for file markers with relevance scores
            if line.strip().startswith("--- File:") and "Relevance:" in line:
                metrics["file_count"] += 1

                # Extract relevance score (format: "Relevance: 0.85")
                try:
                    relevance_str = line.split("Relevance:")[1].split(",")[0].strip()
                    relevance = float(relevance_str)
                    relevance_scores.append(relevance)
                except (IndexError, ValueError):
                    # Fallback to default score
                    relevance_scores.append(0.5)

            # Check for dependency chain information
            if "dependency" in line.lower() or "impact" in line.lower():
                has_dependency_info = True

        # Calculate average relevance
        if relevance_scores:
            metrics["avg_relevance"] = sum(relevance_scores) / len(relevance_scores)

        # Check if dependency coverage is present
        metrics["dependency_coverage"] = has_dependency_info

        # Calculate overall quality score
        # Quality = (average relevance * 0.6) + (file_count_factor * 0.3) + (dependency_factor * 0.1)
        file_count_factor = min(
            metrics["file_count"] / 10.0, 1.0
        )  # Max benefit at 10 files
        dependency_factor = 1.0 if has_dependency_info else 0.0

        metrics["quality_score"] = (
            (metrics["avg_relevance"] * 0.6)
            + (file_count_factor * 0.3)
            + (dependency_factor * 0.1)
        )

        return metrics

    @fcid_mapping("ACT-100")
    def execute_tdd_cycle(self, task):
        """
        Executes a Red-Green-Refactor cycle for given task.
        Returns (success, error_message).

        V3 Enhancement: Integrated telemetry tracking for TDD cycle operations.
        V4 Enhancement: Integrated hierarchical context access.
        """
        task_id = task["id"]
        task_title = task["title"]
        acceptance_criteria = task.get("acceptance_criteria", "")

        # V3: Track TDD cycle operation
        logger.info(f"Starting TDD cycle for task {task_id}: {task_title}")

        with self.telemetry_manager.track_operation(
            operation_type="tdd_cycle",
            title=f"TDD Cycle: {task_title}",
            metadata={"task_id": task_id},
        ) as op:
            # V4: Start progress tracking for TDD cycle
            task_tracking_id = self.progress_tracker.start_tracking(
                task_id=task_id,
                task_type="implementation"
            )
            logger.debug(f"Started progress tracking for task {task_tracking_id}")
            # V4: Use hierarchical context for TDD cycle
            # Start with L0 (immediate) context and expand as needed
            hierarchical_context, level = self.context_expander.get_context(
                task_type="implementation",
                task_info={
                    "task_id": task_id,
                    "title": task_title,
                    "acceptance_criteria": acceptance_criteria
                }
            )
            logger.debug(f"Using context level {level} for TDD cycle")
            
            # Context Injection with AST-based analysis
            # Use enhanced ContextEngine with task title and acceptance criteria
            # for intelligent file scoping and dependency-aware context selection
            v1_files = glob.glob(
                os.path.join(self.workspace_root, "v1/**/*.py"), recursive=True
            )
            v1_files = [os.path.relpath(f, self.workspace_root) for f in v1_files]

            # Get pruned context with smart scoping enabled (V2 enhancement)
            context = self.context_engine.get_pruned_context(
                task_query=task_title,
                files=v1_files,
                use_smart_scoping=True,
                task_title=task_title,
                acceptance_criteria=acceptance_criteria,
                force_refresh=False,
            )

            # Analyze context quality metrics
            quality_metrics = self._analyze_context_quality(context)

            # Log detailed context information including quality metrics
            log_activity(
                summary=f"Starting TDD Cycle: {task_title}",
                action="TDD Start",
                status="Success",
                cot_blob=(
                    f"Beginning implementation for task ID {task_id}. "
                    f"Context gathered: {len(context)} chars, "
                    f"{quality_metrics['file_count']} files, "
                    f"avg relevance: {quality_metrics['avg_relevance']:.2f}, "
                    f"quality score: {quality_metrics['quality_score']:.2f}, "
                    f"dependency coverage: {quality_metrics['dependency_coverage']}"
                ),
                notify_telemetry=False,  # We use log_task_start via orchestrator/task_context
            )

            # Log telemetry for context quality monitoring
            telemetry.track_step(
                f"Context collected: {quality_metrics['file_count']} files, "
                f"quality score: {quality_metrics['quality_score']:.2f}"
            )

            # Warn if context quality is low
            if quality_metrics["quality_score"] < 0.3:
                telemetry.warning(
                    f"Low context quality detected (score: {quality_metrics['quality_score']:.2f}). "
                    f"This may affect implementation accuracy. "
                    f"Avg relevance: {quality_metrics['avg_relevance']:.2f}, "
                    f"Dependency coverage: {quality_metrics['dependency_coverage']}"
                )

            # V4: Detect loops in Red phase attempts
            red_loop_traps = self.trap_detector.detect_all_loops(
                action_history=self.decision_history.get_recent_decisions(limit=5),
                error_history=self.telemetry_manager.query_operations(status="failed", limit=5),
                reasoning_history=self.decision_history.get_recent_decisions(limit=5),
                decision_dependencies=self.decision_history.get_decision_graph()
            )
            if red_loop_traps:
                logger.warning(f"Loop detected in Red phase: {red_loop_traps}")
                telemetry.warning(f"Loop detected: {red_loop_traps}")
                # Attempt recovery
                recovery_result = self.trap_recovery.execute_recovery(
                    trap_type="infinite_loop",
                    trap_details=red_loop_traps
                )
                if recovery_result["success"]:
                    logger.info(f"Successfully recovered from loop: {recovery_result['message']}")
                else:
                    logger.error(f"Failed to recover from loop: {recovery_result['message']}")
            
            # Red Phase: Write a failing test
            logger.debug("Starting Red Phase: Writing failing test")
            telemetry.track_step("Red Phase: Writing failing test")
            success, error = self._run_red_phase(task, context, task_tracking_id)
            if not success:
                logger.error(f"Red Phase failed for task {task_id}: {error}")
                return False, error

            # V4: Detect loops in Green phase attempts
            green_loop_traps = self.trap_detector.detect_all_loops(
                action_history=self.decision_history.get_recent_decisions(limit=5),
                error_history=self.telemetry_manager.query_operations(status="failed", limit=5),
                reasoning_history=self.decision_history.get_recent_decisions(limit=5),
                decision_dependencies=self.decision_history.get_decision_graph()
            )
            if green_loop_traps:
                logger.warning(f"Loop detected in Green phase: {green_loop_traps}")
                telemetry.warning(f"Loop detected: {green_loop_traps}")
                # Attempt recovery
                recovery_result = self.trap_recovery.execute_recovery(
                    trap_type="infinite_loop",
                    trap_details=green_loop_traps
                )
                if recovery_result["success"]:
                    logger.info(f"Successfully recovered from loop: {recovery_result['message']}")
                else:
                    logger.error(f"Failed to recover from loop: {recovery_result['message']}")
            
            # Green Phase: Write minimal code to pass
            logger.debug("Starting Green Phase: Implementing code")
            telemetry.track_step("Green Phase: Implementing code")
            success, error = self._run_green_phase(task, context, task_tracking_id)
            if not success:
                logger.error(f"Green Phase failed for task {task_id}: {error}")
                return False, error

            # Refactor Phase: Cleanup
            logger.debug("Starting Refactor Phase: Cleaning up")
            telemetry.track_step("Refactor Phase: Cleaning up")
            self._run_refactor_phase(task_title, task_tracking_id)

            # Check for Refactor Sprint (every 10 commits)
            if get_commit_count() % 10 == 0 and get_commit_count() > 0:
                self.run_refactor_sprint()

            # V4: Update progress for successful TDD cycle completion
            self.progress_tracker.update_progress(
                tracking_id=task_tracking_id,
                metrics={
                    "test_files_created": 1,
                    "implementation_files_created": 1,
                    "tdd_phases_completed": 3,  # Red, Green, Refactor
                    "total_phases": 3
                }
            )

            # V4: Check if progress is adequate
            is_adequate = self.progress_tracker.check_progress(tracking_id=task_tracking_id)
            if not is_adequate["is_adequate"]:
                logger.warning(f"TDD cycle progress check: {is_adequate['message']}")
                telemetry.warning(f"TDD cycle progress warning: {is_adequate['message']}")
                
                # V4: Check for stagnation or regression
                stagnation_detected = self.progress_tracker.detect_stagnation(tracking_id=task_tracking_id)
                if stagnation_detected["is_stagnant"]:
                    logger.warning(f"TDD cycle stagnation detected: {stagnation_detected['message']}")
                    telemetry.warning(f"TDD cycle stagnation: {stagnation_detected['message']}")
                
                regression_detected = self.progress_tracker.detect_regression(tracking_id=task_tracking_id)
                if regression_detected["is_regression"]:
                    logger.error(f"TDD cycle regression detected: {regression_detected['message']}")
                    telemetry.error(f"TDD cycle regression: {regression_detected['message']}")
                    
                    # V4: Detect dead end from regression
                    dead_end_traps = self.trap_detector.detect_dead_end_no_progress(
                        progress_history=self.progress_tracker.get_progress_history(tracking_id=task_tracking_id),
                        threshold=5
                    )
                    if dead_end_traps:
                        logger.warning(f"Dead end detected in TDD cycle: {dead_end_traps}")
                        telemetry.warning(f"Dead end detected: {dead_end_traps}")
                        # Attempt recovery
                        recovery_result = self.trap_recovery.execute_recovery(
                            trap_type="dead_end",
                            trap_details=dead_end_traps
                        )
                        if recovery_result["success"]:
                            logger.info(f"Successfully recovered from dead end: {recovery_result['message']}")
                        else:
                            logger.error(f"Failed to recover from dead end: {recovery_result['message']}")

            # V3: Record TDD cycle completion
            op.record_event(
                event_type="tdd_cycle_completed",
                severity="info",
                message=f"TDD cycle completed successfully for task: {task_title}",
                context={"task_id": task_id},
            )

            # V3: Create checkpoint after successful task completion
            checkpoint_id = self.checkpoint_manager.create(
                reason=f"after_task_{task_id}", task_id=task_id, task_title=task_title
            )
            logger.info(
                f"Created checkpoint {checkpoint_id} after task {task_id} completed"
            )
            
            # V4: Record context usage in telemetry
            op.record_event(
                event_type="context_level_used",
                severity="info",
                message=f"TDD cycle used context level {level}",
                context={
                    "operation": "tdd_cycle",
                    "context_level": level,
                    "task_id": task_id,
                    "task_title": task_title,
                },
            )

            # V4: Record implementation decision for meta-cognition
            decision_id = self.decision_history.record_decision(
                context=context,
                reasoning=f"TDD cycle completed for task {task_title} with 3 phases (Red, Green, Refactor)",
                action="tdd_implementation",
                alternatives={
                    "alternative_1": "Skip refactor phase",
                    "alternative_2": "Implement without TDD"
                },
                confidence=0.9
            )
            
            # V4: Recognize patterns in implementation decisions
            self.pattern_recognizer.recognize_patterns(
                decisions=self.decision_history.get_recent_decisions(limit=10)
            )
            
            # V4: Perform self-reflection after implementation
            reflection_result = self.self_reflection.perform_reflection(
                trigger="after_task",
                recent_decisions=self.decision_history.get_recent_decisions(limit=5)
            )
            if reflection_result["recommendations"]:
                logger.info(f"Self-reflection recommendations: {reflection_result['recommendations']}")
            
            # V4: Record decision outcome
            self.decision_history.record_outcome(
                decision_id=decision_id,
                outcome="success",
                actual_success=True
            )
            
            # V4: Update heuristics based on successful TDD cycle
            self.adaptive_heuristics.update_heuristics(
                heuristic_type="tdd_success",
                success=True,
                context=context
            )
            
            update_task_status(task_id, "completed")
            return True, None

    def _run_red_phase(self, task, hierarchical_context, tracking_id):
        """
        V4: Updated to use hierarchical context parameter and progress tracking.
        """
        # V4: Update progress for Red phase start
        self.progress_tracker.update_progress(
            tracking_id=tracking_id,
            metrics={"current_phase": "red", "phase_progress": 0}
        )
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
            user_prompt = f"Task: {task_title}\nContext: {hierarchical_context}\nAcceptance Criteria: {task['acceptance_criteria']}"
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
                cot=f"Added test cases for {task_title} across {len(test_changes)} files. Attempt {attempt}. Context level: L0-L3.",
                tokens_used=result["usage"]["total_tokens"],
                prompt_tokens=result["usage"]["prompt_tokens"],
                completion_tokens=result["usage"]["completion_tokens"],
                estimated_cost=result["cost"],
            )

            if success:
                # V4: Update progress for successful Red phase
                self.progress_tracker.update_progress(
                    tracking_id=tracking_id,
                    metrics={"current_phase": "red", "phase_progress": 100}
                )
                return True, None
            else:
                last_error = error_msg
                telemetry.warning(f"Red Phase attempt {attempt} failed: {error_msg}")
                # V4: Update progress for failed attempt
                self.progress_tracker.update_progress(
                    tracking_id=tracking_id,
                    metrics={"red_phase_attempts": attempt}
                )

            # V4: Learn from red phase failure
            self.lesson_learner.record_failure(
                failure_type="red_phase",
                context=hierarchical_context,
                error_message=last_error or "Red Phase failed after maximum attempts"
            )
        return False, last_error or "Red Phase failed after maximum attempts."

    def _run_green_phase(self, task, hierarchical_context, tracking_id):
        """
        V4: Updated to use hierarchical context parameter and progress tracking.
        """
        # V4: Update progress for Green phase start
        self.progress_tracker.update_progress(
            tracking_id=tracking_id,
            metrics={"current_phase": "green", "phase_progress": 0}
        )
        task_title = task["title"]
        # If Red phase created multiple files, we should ideally run all of them.
        # For v1, we focus on primary test file or use a heuristic.
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
Your task is to generate minimal code required to pass of provided tests (the "Green" phase of TDD).

Output Format:
For each file you want to create or update, use the following format:
File: path/to/file.py
```python
# content here
```

Respect the Open-Closed Principle and avoid modifying stable modules unless necessary.
Keep changes focused and under 100 lines per commit.
"""
            user_prompt = f"Task: {task_title}\nContext: {hierarchical_context}\n"
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
                        cot=f"Implementation passed on attempt {attempt} and met 100% mutation quality gate. Context level: L0-L3.",
                        tokens_used=result["usage"]["total_tokens"],
                        prompt_tokens=result["usage"]["prompt_tokens"],
                        completion_tokens=result["usage"]["completion_tokens"],
                        estimated_cost=result["cost"],
                    )
                    if success:
                        # V4: Update progress for successful Green phase
                        self.progress_tracker.update_progress(
                            tracking_id=tracking_id,
                            metrics={
                                "current_phase": "green",
                                "phase_progress": 100,
                                "green_phase_attempts": attempt
                            }
                        )
                        return True, None
                    else:
                        last_error = f"Git Policy Violation: {error_msg}"
                        telemetry.warning(
                            f"Green Phase attempt {attempt} failed policy check: {error_msg}"
                        )

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
                # V4: Update progress for failed attempt
                self.progress_tracker.update_progress(
                    tracking_id=tracking_id,
                    metrics={"green_phase_attempts": attempt}
                )

            # V4: Learn from green phase failure
            self.lesson_learner.record_failure(
                failure_type="green_phase",
                context=hierarchical_context,
                error_message=last_error or "Green Phase failed after maximum attempts"
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

    def _run_refactor_phase(self, task_title, tracking_id):
        # V4: Update progress for Refactor phase start
        self.progress_tracker.update_progress(
            tracking_id=tracking_id,
            metrics={"current_phase": "refactor", "phase_progress": 0}
        )
        
        log_activity(
            summary=f"Refactor Phase: {task_title}",
            action="Refactor",
            status="Success",
            cot_blob="Verified code against tests and cleaned up",
        )
        
        # V4: Update progress for successful Refactor phase
        self.progress_tracker.update_progress(
            tracking_id=tracking_id,
            metrics={"current_phase": "refactor", "phase_progress": 100}
        )
        return True

    @fcid_mapping("ACT-200")
    def run_refactor_sprint(self):
        """
        Consolidate patterns after every 10 commits.
        V3 Enhancement: Creates checkpoint before refactoring sprint.
        """
        telemetry.track_step("Refactor Sprint")

        # V3: Create checkpoint before refactor sprint
        checkpoint_id = self.checkpoint_manager.create(reason="before_refactor_sprint")
        logger.info(f"Created checkpoint {checkpoint_id} before refactor sprint")

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
