from v1.data.db_manager import get_pending_task, log_activity, fcid_mapping

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
            # According to technical.md:
            # If task exists and is <30 lines: Hand off to Implementor.
            # If task exists but is too large: Hand off to Planner (Breakdown).
            
            # Since we don't have a 'size' field yet, we assume all pending tasks 
            # are broken down and ready for implementation. 
            # In the future, complexity checks can be added here.
            
            log_activity(
                summary=f"Task Selected: {task['title']}",
                action="dispatch",
                status="Success",
                cot_blob=f"Found pending task with ID: {task['id']}"
            )
            return "IMPLEMENT", task
        else:
            # If no task exists or current task is blocked: Trigger Planner.
            log_activity(
                summary="No pending tasks found",
                action="dispatch",
                status="Plan Required",
                cot_blob="task.db is empty or no pending tasks available. Triggering Planner."
            )
            return "PLAN", None
