from v3.data.db_manager import (
    get_pending_task,
    get_blocked_task,
    log_activity,
    fcid_mapping,
)
from v3.core.telemetry import telemetry
from v3.data.telemetry_manager import get_telemetry_manager
from v3.core.logging_config import get_module_logger
from v3.data.checkpoint_manager import CheckpointManager
# V4: Adaptive reasoning components
from v3.data.context_hierarchy import get_context_hierarchy
from v3.logic.reasoning_engine import get_reasoning_engine
from v3.logic.context_expander import get_context_expander

logger = get_module_logger(__name__)


class Dispatcher:
    def __init__(self):
        logger.info("Initializing Dispatcher")
        self.telemetry_manager = get_telemetry_manager()
        self.checkpoint_manager = CheckpointManager()
        # V4: Adaptive reasoning components
        self.context_hierarchy = get_context_hierarchy()
        self.reasoning_engine = get_reasoning_engine()
        self.context_expander = get_context_expander()
        logger.info("Dispatcher initialized successfully with V4 adaptive reasoning")

    @fcid_mapping("DISP-100")
    def dispatch(self, preferred_id=None):
        """
        Handles task selection logic.
        Queries task.db for next 'pending' task.
        Returns (action, task) where action is 'IMPLEMENT' or 'PLAN'.

        V3 Enhancement: Integrated telemetry tracking for dispatch operations.
        """
        # V3: Track dispatch operation
        with self.telemetry_manager.track_operation(
            operation_type="dispatch",
            title=f"Dispatch task selection (preferred_id={preferred_id})",
        ) as op:
            logger.debug(f"Dispatching task (preferred_id={preferred_id})")
            
            # V4: Use hierarchical context for task selection
            # Start with L0 (immediate) context and expand as needed
            context, level = self.context_expander.get_context(
                task_type="dispatch",
                task_info={"preferred_id": preferred_id}
            )
            logger.debug(f"Using context level {level} for dispatch decision")
            
            task = get_pending_task(preferred_id)

            if task:
                logger.info(f"Task selected: {task['title']} (ID: {task['id']})")
                log_activity(
                    summary=f"Task Selected: {task['title']}",
                    action="dispatch",
                    status="Success",
                    cot_blob=f"Found pending task with ID: {task['id']}",
                )

                # V3: Create checkpoint before task implementation
                checkpoint_id = self.checkpoint_manager.create(
                    reason=f"before_task_{task['id']}",
                    task_id=task["id"],
                    task_title=task["title"],
                )
                logger.info(
                    f"Created checkpoint {checkpoint_id} before task {task['id']}"
                )

                # V3: Record dispatch event
                op.record_event(
                    event_type="task_selected",
                    severity="info",
                    message=f"Selected task: {task['title']} (ID: {task['id']})",
                    context={
                        "task_id": task["id"],
                        "task_title": task["title"],
                        "preferred_id": preferred_id,
                        "checkpoint_id": checkpoint_id,
                    },
                )

                # V4: Record context usage in telemetry
                op.record_event(
                    event_type="context_level_used",
                    severity="info",
                    message=f"Dispatch used context level {level}",
                    context={
                        "operation": "dispatch",
                        "context_level": level,
                        "task_id": task.get("id"),
                    },
                )
                
                telemetry.info(f"Task selected: {task['title']} (ID: {task['id']})")
                return "IMPLEMENT", task
            else:
                logger.debug("No pending tasks found, checking for blocked tasks")
                # Check for blocked tasks
                blocked_task = get_blocked_task()
                if blocked_task:
                    logger.warning(
                        f"Blocked task found: {blocked_task['title']} (ID: {blocked_task['id']})"
                    )
                    log_activity(
                        summary=f"Blocked Task Found: {blocked_task['title']}",
                        action="dispatch",
                        status="Plan Required",
                        cot_blob=f"Task ID {blocked_task['id']} is blocked. Triggering breakdown/fix planning.",
                    )

                    # V3: Record blocked task event
                    op.record_event(
                        event_type="blocked_task_found",
                        severity="warning",
                        message=f"Blocked task found: {blocked_task['title']}",
                        context={
                            "task_id": blocked_task["id"],
                            "task_title": blocked_task["title"],
                        },
                    )

                    # V4: Record context usage for blocked task
                    op.record_event(
                        event_type="context_level_used",
                        severity="info",
                        message=f"Blocked task dispatch used context level {level}",
                        context={
                            "operation": "dispatch_blocked",
                            "context_level": level,
                            "task_id": blocked_task.get("id"),
                        },
                    )
                    
                    telemetry.warning(f"Blocked task found: {blocked_task['title']}")
                    return "PLAN", blocked_task

                # If no task exists: Trigger Planner.
                logger.info("No tasks available, triggering planner")
                log_activity(
                    summary="No tasks found",
                    action="dispatch",
                    status="Plan Required",
                    cot_blob="task.db is empty or no tasks available. Triggering Planner.",
                )

                # V3: Record planner trigger event
                op.record_event(
                    event_type="planner_triggered",
                    severity="info",
                    message="No tasks available, triggering planner",
                    context={"reason": "no_pending_tasks"},
                )

                # V4: Record context usage for planner trigger
                op.record_event(
                    event_type="context_level_used",
                    severity="info",
                    message=f"Planner trigger used context level {level}",
                    context={
                        "operation": "dispatch_plan",
                        "context_level": level,
                    },
                )
                
                telemetry.info("No tasks available, triggering planner")
                return "PLAN", None
