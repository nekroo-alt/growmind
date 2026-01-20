from v1.data.db_manager import (
    get_pending_task,
    get_blocked_task,
    log_activity,
    fcid_mapping,
)


class Dispatcher:
    @fcid_mapping("DISP-100")
    def dispatch(self, preferred_id=None):
        """
        Handles task selection logic.
        Queries task.db for the next 'pending' task.
        Returns (action, task) where action is 'IMPLEMENT' or 'PLAN'.
        """
        task = get_pending_task(preferred_id)

        if task:
            log_activity(
                summary=f"Task Selected: {task['title']}",
                action="dispatch",
                status="Success",
                cot_blob=f"Found pending task with ID: {task['id']}",
            )
            return "IMPLEMENT", task
        else:
            # Check for blocked tasks
            blocked_task = get_blocked_task()
            if blocked_task:
                log_activity(
                    summary=f"Blocked Task Found: {blocked_task['title']}",
                    action="dispatch",
                    status="Plan Required",
                    cot_blob=f"Task ID {blocked_task['id']} is blocked. Triggering breakdown/fix planning.",
                )
                return "PLAN", blocked_task

            # If no task exists: Trigger Planner.
            log_activity(
                summary="No tasks found",
                action="dispatch",
                status="Plan Required",
                cot_blob="task.db is empty or no tasks available. Triggering Planner.",
            )
            return "PLAN", None
