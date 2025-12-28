import sqlite3
import os

# Database paths
TASK_DB_PATH = "task.db"
ACTIVITY_DB_PATH = "activity.db"

def init_db():
    """
    Initializes the task and activity databases if they don't exist.
    """
    # Initialize activity database
    with sqlite3.connect(ACTIVITY_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            summary TEXT,
            action TEXT,
            status TEXT,
            CoT_blob TEXT,
            commit_hash TEXT,
            tokens_used INTEGER,
            estimated_cost REAL
        )
        ''')
        conn.commit()

    # Initialize task database
    with sqlite3.connect(TASK_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            status TEXT,
            acceptance_criteria TEXT,
            parent_id INTEGER,
            module TEXT,
            FOREIGN KEY (parent_id) REFERENCES tasks (id)
        )
        ''')
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS state (
            key TEXT PRIMARY KEY,
            value TEXT
        )
        ''')
        conn.commit()

def get_db_connection(db_path):
    """
    Establishes a connection to the SQLite database at the given path.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def log_activity(summary, action, status, cot_blob=None, commit_hash=None, tokens_used=None, estimated_cost=None):
    """
    Logs an activity to the activity database.
    """
    conn = get_db_connection(ACTIVITY_DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO activities (summary, action, status, CoT_blob, commit_hash, tokens_used, estimated_cost)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (summary, action, status, cot_blob, commit_hash, tokens_used, estimated_cost))
    conn.commit()
    conn.close()

def log_task(title, status, acceptance_criteria=None, parent_id=None, module=None):
    """
    Logs a task to the task database.
    """
    conn = get_db_connection(TASK_DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO tasks (title, status, acceptance_criteria, parent_id, module)
        VALUES (?, ?, ?, ?, ?)
    ''', (title, status, acceptance_criteria, parent_id, module))
    conn.commit()
    conn.close()

def get_pending_task(preferred_id=None):
    """
    Fetches the next pending task from the task database.
    If preferred_id is provided and that task is pending, it returns it.
    """
    conn = get_db_connection(TASK_DB_PATH)
    cursor = conn.cursor()
    if preferred_id:
        cursor.execute('SELECT * FROM tasks WHERE status = "pending" AND id = ?', (preferred_id,))
        task = cursor.fetchone()
        if task:
            conn.close()
            return task
            
    cursor.execute('SELECT * FROM tasks WHERE status = "pending" LIMIT 1')
    task = cursor.fetchone()
    conn.close()
    return task

def task_exists(title):
    """
    Checks if a task with the given title already exists in the database.
    """
    conn = get_db_connection(TASK_DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT 1 FROM tasks WHERE title = ? LIMIT 1', (title,))
    exists = cursor.fetchone() is not None
    conn.close()
    return exists

def update_task_status(task_id, new_status):
    """
    Updates the status of a task in the task database.
    """
    conn = get_db_connection(TASK_DB_PATH)
    cursor = conn.cursor()
    cursor.execute('UPDATE tasks SET status = ? WHERE id = ?', (new_status, task_id))
    conn.commit()
    conn.close()

def save_state(key, value):
    """
    Saves or updates a state key-value pair in the task database.
    """
    conn = get_db_connection(TASK_DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO state (key, value)
        VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
    ''', (key, value))
    conn.commit()
    conn.close()

def load_state(key):
    """
    Loads a state value by key from the task database.
    Returns None if key doesn't exist.
    """
    conn = get_db_connection(TASK_DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT value FROM state WHERE key = ?', (key,))
    row = cursor.fetchone()
    conn.close()
    return row['value'] if row else None

def get_commit_count():
    """
    Returns the number of successful git commits recorded in the activity log.
    """
    conn = get_db_connection(ACTIVITY_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM activities WHERE action = 'Git Commit' AND status = 'Success'")
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_cost_summary():
    """
    Returns total tokens used and estimated cost from all activities.
    """
    conn = get_db_connection(ACTIVITY_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(tokens_used), SUM(estimated_cost) FROM activities")
    row = cursor.fetchone()
    total_tokens = row[0] if row[0] is not None else 0
    total_cost = row[1] if row[1] is not None else 0.0
    conn.close()
    return total_tokens, total_cost

def get_completed_tasks_count():
    """
    Returns the number of completed tasks from the task database.
    """
    conn = get_db_connection(TASK_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = 'completed'")
    count = cursor.fetchone()[0]
    conn.close()
    return count

def fcid_mapping(id):
    """
    Decorator to annotate functions with FCIDs.
    """
    def decorator(func):
        func.fcid = id
        return func
    return decorator
