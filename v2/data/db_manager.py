import sqlite3
import os
import json
from typing import List, Set, Dict
from v2.core.telemetry import telemetry

# Database paths
TASK_DB_PATH = "task.db"
ACTIVITY_DB_PATH = "activity.db"
SNAPSHOTS_DB_PATH = "snapshots.db"


def init_db():
    """
    Initializes the task, activity, and snapshots databases if they don't exist.
    """
    # Initialize activity database
    with sqlite3.connect(ACTIVITY_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            summary TEXT,
            action TEXT,
            status TEXT,
            CoT_blob TEXT,
            commit_hash TEXT,
            tokens_used INTEGER,
            prompt_tokens INTEGER,
            completion_tokens INTEGER,
            estimated_cost REAL
        )
        """
        )

        # Ensure columns exist if table was already created
        try:
            cursor.execute("ALTER TABLE activities ADD COLUMN prompt_tokens INTEGER")
        except sqlite3.OperationalError:
            pass  # Already exists
        try:
            cursor.execute("ALTER TABLE activities ADD COLUMN completion_tokens INTEGER")
        except sqlite3.OperationalError:
            pass  # Already exists

        conn.commit()

    # Initialize task database
    with sqlite3.connect(TASK_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            status TEXT,
            acceptance_criteria TEXT,
            parent_id INTEGER,
            module TEXT,
            blocked_reason TEXT,
            FOREIGN KEY (parent_id) REFERENCES tasks (id)
        )
        """
        )
        # Ensure blocked_reason column exists if table was already created
        try:
            cursor.execute("ALTER TABLE tasks ADD COLUMN blocked_reason TEXT")
        except sqlite3.OperationalError:
            pass  # Already exists

        # Add depends_on column for task dependency tracking
        try:
            cursor.execute("ALTER TABLE tasks ADD COLUMN depends_on TEXT")
        except sqlite3.OperationalError:
            pass  # Already exists

        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS state (
            key TEXT PRIMARY KEY,
            value TEXT
        )
        """
        )
        conn.commit()

    # Initialize snapshots database
    with sqlite3.connect(SNAPSHOTS_DB_PATH) as conn:
        cursor = conn.cursor()
        
        # Main snapshots table
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            snapshot_id TEXT UNIQUE NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            snapshot_type TEXT NOT NULL,
            operation_id TEXT,
            task_id INTEGER,
            reason TEXT,
            is_incremental BOOLEAN DEFAULT 0,
            parent_snapshot_id TEXT,
            metadata TEXT,
            FOREIGN KEY (parent_snapshot_id) REFERENCES snapshots (snapshot_id)
        )
        """
        )
        
        # Database state snapshots
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS snapshot_db_state (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            snapshot_id TEXT NOT NULL,
            db_name TEXT NOT NULL,
            db_hash TEXT NOT NULL,
            db_size INTEGER,
            is_incremental BOOLEAN DEFAULT 0,
            data BLOB,
            backup_path TEXT,
            backup_status TEXT,
            FOREIGN KEY (snapshot_id) REFERENCES snapshots (snapshot_id) ON DELETE CASCADE
        )
        """
        )
        
        # Add new columns if table already exists (migration)
        try:
            cursor.execute("ALTER TABLE snapshot_db_state ADD COLUMN backup_path TEXT")
        except sqlite3.OperationalError:
            pass  # Already exists
        try:
            cursor.execute("ALTER TABLE snapshot_db_state ADD COLUMN backup_status TEXT")
        except sqlite3.OperationalError:
            pass  # Already exists
        
        # File system state snapshots
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS snapshot_file_state (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            snapshot_id TEXT NOT NULL,
            file_path TEXT NOT NULL,
            file_hash TEXT NOT NULL,
            file_size INTEGER,
            file_status TEXT NOT NULL,
            git_diff TEXT,
            FOREIGN KEY (snapshot_id) REFERENCES snapshots (snapshot_id) ON DELETE CASCADE
        )
        """
        )
        
        # Git state snapshots
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS snapshot_git_state (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            snapshot_id TEXT NOT NULL,
            branch TEXT NOT NULL,
            commit_hash TEXT NOT NULL,
            git_status TEXT,
            FOREIGN KEY (snapshot_id) REFERENCES snapshots (snapshot_id) ON DELETE CASCADE
        )
        """
        )
        
        # Cache state snapshots
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS snapshot_cache_state (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            snapshot_id TEXT NOT NULL,
            cache_key TEXT NOT NULL,
            cache_value BLOB,
            cache_hash TEXT,
            cache_size INTEGER,
            FOREIGN KEY (snapshot_id) REFERENCES snapshots (snapshot_id) ON DELETE CASCADE
        )
        """
        )
        
        # Create indexes for efficient queries
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_snapshots_timestamp ON snapshots(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_snapshots_type ON snapshots(snapshot_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_snapshots_operation ON snapshots(operation_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_snapshots_task ON snapshots(task_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_snapshot_db ON snapshot_db_state(snapshot_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_snapshot_file ON snapshot_file_state(snapshot_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_snapshot_git ON snapshot_git_state(snapshot_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_snapshot_cache ON snapshot_cache_state(snapshot_id)")
        
        conn.commit()


def get_db_connection(db_path):
    """
    Establishes a connection to the SQLite database at the given path.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def log_activity(
    summary,
    action,
    status,
    cot_blob=None,
    commit_hash=None,
    tokens_used=None,
    prompt_tokens=None,
    completion_tokens=None,
    estimated_cost=None,
    notify_telemetry=True,
):
    """
    Logs an activity to the activity database.
    """
    if notify_telemetry:
        msg = f"[{action}] {summary} -> {status}"
        if status == "Failed" and cot_blob:
            msg += f" - {cot_blob}"

        if status == "Success":
            telemetry.info(msg)
        elif status == "Failed":
            telemetry.error(msg)
        else:
            telemetry.info(msg)

    # Calculate tokens_used if not provided but prompt/completion are
    if (
        tokens_used is None
        and prompt_tokens is not None
        and completion_tokens is not None
    ):
        tokens_used = prompt_tokens + completion_tokens

    conn = get_db_connection(ACTIVITY_DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO activities (summary, action, status, CoT_blob, commit_hash, tokens_used, prompt_tokens, completion_tokens, estimated_cost)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            summary,
            action,
            status,
            cot_blob,
            commit_hash,
            tokens_used,
            prompt_tokens,
            completion_tokens,
            estimated_cost,
        ),
    )
    conn.commit()
    conn.close()


def log_task(title, status, acceptance_criteria=None, parent_id=None, module=None, depends_on=None):
    """
    Logs a task to the task database.
    
    Args:
        title: Task title
        status: Task status (pending, in_progress, completed, blocked)
        acceptance_criteria: Optional acceptance criteria text
        parent_id: Optional parent task ID for hierarchical tasks
        module: Optional module name
        depends_on: Optional list of task IDs this task depends on
    """
    # Convert depends_on list to JSON string
    depends_on_json = json.dumps(depends_on) if depends_on else None
    
    conn = get_db_connection(TASK_DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO tasks (title, status, acceptance_criteria, parent_id, module, depends_on)
        VALUES (?, ?, ?, ?, ?, ?)
    """,
        (title, status, acceptance_criteria, parent_id, module, depends_on_json),
    )
    conn.commit()
    conn.close()


def get_pending_task(preferred_id=None):
    """
    Fetches the next pending task from the task database.
    If preferred_id is provided and that task is pending, it returns it.
    Only returns tasks whose dependencies are satisfied.
    """
    conn = get_db_connection(TASK_DB_PATH)
    cursor = conn.cursor()
    
    if preferred_id:
        cursor.execute(
            'SELECT * FROM tasks WHERE status = "pending" AND id = ?', (preferred_id,)
        )
        task = cursor.fetchone()
        if task and check_dependencies_satisfied(task["id"], conn):
            conn.close()
            return task
        elif task:
            # Task exists but dependencies not satisfied
            conn.close()
            return None

    # Get all pending tasks and return the first one with satisfied dependencies
    cursor.execute('SELECT * FROM tasks WHERE status = "pending"')
    for task in cursor.fetchall():
        if check_dependencies_satisfied(task["id"], conn):
            conn.close()
            return dict(task)
    
    conn.close()
    return None


def get_blocked_task():
    """
    Fetches the first blocked task from the task database.
    """
    conn = get_db_connection(TASK_DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM tasks WHERE status = "blocked" LIMIT 1')
    task = cursor.fetchone()
    conn.close()
    return task


def get_task_dependencies(task_id):
    """
    Returns the list of task IDs that the given task depends on.
    
    Args:
        task_id: The ID of the task
        
    Returns:
        List of task IDs (integers)
    """
    conn = get_db_connection(TASK_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT depends_on FROM tasks WHERE id = ?", (task_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row and row["depends_on"]:
        try:
            return json.loads(row["depends_on"])
        except json.JSONDecodeError:
            return []
    return []


def check_dependencies_satisfied(task_id, conn=None):
    """
    Checks if all dependencies for a task are satisfied.
    A dependency is satisfied if the prerequisite task has status "completed".
    
    Args:
        task_id: The ID of the task to check
        conn: Optional database connection (if provided, won't close it)
        
    Returns:
        True if all dependencies are satisfied, False otherwise
    """
    should_close = conn is None
    if conn is None:
        conn = get_db_connection(TASK_DB_PATH)
    
    cursor = conn.cursor()
    
    # Get dependencies for this task
    cursor.execute("SELECT depends_on FROM tasks WHERE id = ?", (task_id,))
    row = cursor.fetchone()
    
    if not row or not row["depends_on"]:
        if should_close:
            conn.close()
        return True
    
    dependencies = json.loads(row["depends_on"])
    
    for dep_id in dependencies:
        # Check if dependency task exists and is completed
        cursor.execute(
            "SELECT status FROM tasks WHERE id = ?", (dep_id,)
        )
        dep_row = cursor.fetchone()
        
        if not dep_row or dep_row["status"] != "completed":
            if should_close:
                conn.close()
            return False
    
    if should_close:
        conn.close()
    return True


def validate_no_circular_dependencies(task_id, depends_on, conn=None):
    """
    Validates that adding these dependencies won't create a circular dependency.
    
    Args:
        task_id: The ID of the task
        depends_on: List of task IDs this task depends on
        conn: Optional database connection
        
    Returns:
        (is_valid, message) where is_valid is True if no circular dependency exists
    """
    should_close = conn is None
    if conn is None:
        conn = get_db_connection(TASK_DB_PATH)
    
    cursor = conn.cursor()
    
    # Check if any dependency has a dependency chain back to task_id
    for dep_id in depends_on:
        if has_dependency_chain_to(dep_id, task_id, cursor):
            if should_close:
                conn.close()
            return False, f"Circular dependency detected: task {task_id} depends on {dep_id}, but {dep_id} has a dependency chain back to {task_id}"
    
    if should_close:
        conn.close()
    return True, "No circular dependencies"


def has_dependency_chain_to(from_id, to_id, cursor, visited=None):
    """
    Recursively checks if from_id has a dependency chain to to_id.
    
    Args:
        from_id: Starting task ID
        to_id: Target task ID to find
        cursor: Database cursor
        visited: Set of already visited task IDs (to prevent infinite loops)
        
    Returns:
        True if there's a dependency chain from from_id to to_id
    """
    if visited is None:
        visited = set()
    
    if from_id in visited:
        return False
    
    visited.add(from_id)
    
    # Get dependencies for from_id
    cursor.execute("SELECT depends_on FROM tasks WHERE id = ?", (from_id,))
    row = cursor.fetchone()
    
    if not row or not row["depends_on"]:
        return False
    
    dependencies = json.loads(row["depends_on"])
    
    for dep_id in dependencies:
        if dep_id == to_id:
            return True
        if has_dependency_chain_to(dep_id, to_id, cursor, visited):
            return True
    
    return False


def get_task_dependency_graph():
    """
    Returns the complete task dependency graph.
    
    Returns:
        Dictionary mapping task IDs to their dependencies:
        {
            task_id: {
                'title': str,
                'status': str,
                'depends_on': List[int]
            }
        }
    """
    conn = get_db_connection(TASK_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, status, depends_on FROM tasks")
    rows = cursor.fetchall()
    conn.close()
    
    graph = {}
    for row in rows:
        task_id = row["id"]
        depends_on = json.loads(row["depends_on"]) if row["depends_on"] else []
        graph[task_id] = {
            'title': row["title"],
            'status': row["status"],
            'depends_on': depends_on
        }
    
    return graph


def update_task_dependencies(task_id, depends_on):
    """
    Updates the dependencies for a task.
    
    Args:
        task_id: The ID of the task to update
        depends_on: List of task IDs this task depends on
        
    Returns:
        (success, message) where success is True if update was successful
    """
    # Validate no circular dependencies
    conn = get_db_connection(TASK_DB_PATH)
    is_valid, message = validate_no_circular_dependencies(task_id, depends_on, conn)
    
    if not is_valid:
        conn.close()
        return False, message
    
    # Validate all dependencies exist
    cursor = conn.cursor()
    for dep_id in depends_on:
        cursor.execute("SELECT 1 FROM tasks WHERE id = ?", (dep_id,))
        if not cursor.fetchone():
            conn.close()
            return False, f"Dependency task {dep_id} does not exist"
    
    # Update the task
    depends_on_json = json.dumps(depends_on)
    cursor.execute(
        "UPDATE tasks SET depends_on = ? WHERE id = ?",
        (depends_on_json, task_id)
    )
    conn.commit()
    conn.close()
    
    return True, "Dependencies updated successfully"


def task_exists(title):
    """
    Checks if a task with the given title already exists in the database.
    """
    conn = get_db_connection(TASK_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM tasks WHERE title = ? LIMIT 1", (title,))
    exists = cursor.fetchone() is not None
    conn.close()
    return exists


def update_task_status(task_id, new_status, reason=None):
    """
    Updates the status of a task in the task database.
    """
    conn = get_db_connection(TASK_DB_PATH)
    cursor = conn.cursor()
    if reason:
        cursor.execute(
            "UPDATE tasks SET status = ?, blocked_reason = ? WHERE id = ?",
            (new_status, reason, task_id),
        )
    else:
        cursor.execute(
            "UPDATE tasks SET status = ? WHERE id = ?", (new_status, task_id)
        )
    conn.commit()
    conn.close()


def save_state(key, value):
    """
    Saves or updates a state key-value pair in the task database.
    """
    conn = get_db_connection(TASK_DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO state (key, value)
        VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
    """,
        (key, value),
    )
    conn.commit()
    conn.close()


def load_state(key):
    """
    Loads a state value by key from the task database.
    Returns None if key doesn't exist.
    """
    conn = get_db_connection(TASK_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM state WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    return row["value"] if row else None


def get_commit_count():
    """
    Returns the number of successful git commits recorded in the activity log.
    """
    conn = get_db_connection(ACTIVITY_DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM activities WHERE action = 'Git Commit' AND status = 'Success'"
    )
    count = cursor.fetchone()[0]
    conn.close()
    return count


def get_cost_summary():
    """
    Returns total tokens used and estimated cost from all activities.
    Returns (total_tokens, total_cost, prompt_tokens, completion_tokens)
    """
    conn = get_db_connection(ACTIVITY_DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT SUM(tokens_used), SUM(estimated_cost), SUM(prompt_tokens), SUM(completion_tokens) FROM activities"
    )
    row = cursor.fetchone()
    total_tokens = row[0] if row[0] is not None else 0
    total_cost = row[1] if row[1] is not None else 0.0
    prompt_tokens = row[2] if row[2] is not None else 0
    completion_tokens = row[3] if row[3] is not None else 0
    conn.close()
    return total_tokens, total_cost, prompt_tokens, completion_tokens


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
