from v1.data.db_manager import init_db, update_task_status, log_task, get_db_connection, TASK_DB_PATH
import sqlite3
import os

def test_blocked_reason():
    # Initialize DB (should add column if not exists)
    init_db()
    
    # Add a dummy task
    conn = get_db_connection(TASK_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks WHERE title='Test Task'")
    conn.commit()
    conn.close()
    
    log_task("Test Task", "pending")
    
    # Get the task ID
    conn = get_db_connection(TASK_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM tasks WHERE title='Test Task'")
    task_id = cursor.fetchone()[0]
    conn.close()
    
    # Mark as blocked with a reason
    reason = "Test blocked reason"
    update_task_status(task_id, "blocked", reason=reason)
    
    # Verify
    conn = get_db_connection(TASK_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT status, blocked_reason FROM tasks WHERE id=?", (task_id,))
    row = cursor.fetchone()
    conn.close()
    
    print(f"Status: {row['status']}")
    print(f"Blocked Reason: {row['blocked_reason']}")
    
    assert row['status'] == "blocked"
    assert row['blocked_reason'] == reason
    print("Verification successful!")

if __name__ == "__main__":
    test_blocked_reason()
