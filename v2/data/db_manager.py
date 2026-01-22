import sqlite3
import os
import json
from typing import List, Set, Dict
from core.telemetry import telemetry

# Database paths
TASK_DB_PATH = "task.db"
ACTIVITY_DB_PATH = "activity.db"
SNAPSHOTS_DB_PATH = "snapshots.db"
SESSIONS_DB_PATH = "sessions.db"


def init_db():
    """
    Initializes the task, activity, snapshots, and sessions databases if they don't exist.
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
            backup_path TEXT,
            FOREIGN KEY (snapshot_id) REFERENCES snapshots (snapshot_id) ON DELETE CASCADE
        )
        """
        )
        
        # Add backup_path column if table already exists (migration)
        try:
            cursor.execute("ALTER TABLE snapshot_file_state ADD COLUMN backup_path TEXT")
        except sqlite3.OperationalError:
            pass  # Already exists
        
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
            cache_data TEXT,
            FOREIGN KEY (snapshot_id) REFERENCES snapshots (snapshot_id) ON DELETE CASCADE
        )
        """
        )
        
        # Add cache_data column if table already exists (migration)
        try:
            cursor.execute("ALTER TABLE snapshot_cache_state ADD COLUMN cache_data TEXT")
        except sqlite3.OperationalError:
            pass  # Already exists
        
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

    # Initialize sessions database
    with sqlite3.connect(SESSIONS_DB_PATH) as conn:
        cursor = conn.cursor()
        
        # Main sessions table
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT UNIQUE NOT NULL,
            start_time DATETIME DEFAULT CURRENT_TIMESTAMP,
            end_time DATETIME,
            status TEXT NOT NULL,
            user TEXT,
            host TEXT,
            environment TEXT,
            metadata TEXT,
            FOREIGN KEY (session_id) REFERENCES session_operations(session_id) ON DELETE CASCADE
        )
        """
        )
        
        # Session operations tracking
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS session_operations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            operation_id TEXT NOT NULL,
            task_id INTEGER,
            operation_type TEXT NOT NULL,
            status TEXT NOT NULL,
            start_time DATETIME DEFAULT CURRENT_TIMESTAMP,
            end_time DATETIME,
            FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
        )
        """
        )
        
        # Session checkpoints
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS session_checkpoints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            checkpoint_id TEXT NOT NULL,
            checkpoint_time DATETIME DEFAULT CURRENT_TIMESTAMP,
            reason TEXT,
            is_auto BOOLEAN DEFAULT 0,
            FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
        )
        """
        )
        
        # Session configuration
        # Drop and recreate to ensure proper schema (including unique constraint)
        cursor.execute("DROP TABLE IF EXISTS session_config")
        cursor.execute(
            """
        CREATE TABLE session_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            config_key TEXT NOT NULL,
            config_value TEXT NOT NULL,
            UNIQUE(session_id, config_key),
            FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
        )
        """
        )
        
        # Create indexes for efficient queries
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_start_time ON sessions(start_time)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_session_ops_session ON session_operations(session_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_session_ops_type ON session_operations(operation_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_session_checkpoints_session ON session_checkpoints(session_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_session_config_session ON session_config(session_id)")
        
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


# ==================== SESSION MANAGEMENT FUNCTIONS ====================

def create_session(session_id=None, user=None, host=None, environment=None, metadata=None):
    """
    Creates a new session in the sessions database.
    
    Args:
        session_id: Optional unique session ID (auto-generated if not provided)
        user: Optional username
        host: Optional hostname
        environment: Optional environment name (dev, prod, etc.)
        metadata: Optional metadata dictionary (will be JSON-serialized)
        
    Returns:
        The session_id of the created session
    """
    import uuid
    
    # Generate session_id if not provided
    if session_id is None:
        session_id = str(uuid.uuid4())
    
    # Serialize metadata if provided
    metadata_json = json.dumps(metadata) if metadata else None
    
    conn = get_db_connection(SESSIONS_DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO sessions (session_id, start_time, status, user, host, environment, metadata)
        VALUES (?, CURRENT_TIMESTAMP, 'active', ?, ?, ?, ?)
        """,
        (session_id, user, host, environment, metadata_json)
    )
    conn.commit()
    conn.close()
    
    return session_id


def end_session(session_id, status='completed'):
    """
    Marks a session as ended with the given status.
    
    Args:
        session_id: The session ID to end
        status: Final status of the session (completed, interrupted, error, etc.)
    """
    conn = get_db_connection(SESSIONS_DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE sessions SET end_time = CURRENT_TIMESTAMP, status = ?
        WHERE session_id = ? AND status = 'active'
        """,
        (status, session_id)
    )
    conn.commit()
    conn.close()


def get_session(session_id):
    """
    Retrieves session information by session_id.
    
    Args:
        session_id: The session ID to retrieve
        
    Returns:
        Dictionary with session information or None if not found
    """
    conn = get_db_connection(SESSIONS_DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT * FROM sessions WHERE session_id = ?
        """,
        (session_id,)
    )
    row = cursor.fetchone()
    conn.close()
    
    if row:
        session = dict(row)
        # Deserialize metadata if present
        if session.get('metadata'):
            session['metadata'] = json.loads(session['metadata'])
        return session
    return None


def list_sessions(status=None, limit=None):
    """
    Lists sessions with optional filtering.
    
    Args:
        status: Optional status filter (active, completed, interrupted, etc.)
        limit: Optional maximum number of sessions to return
        
    Returns:
        List of session dictionaries
    """
    conn = get_db_connection(SESSIONS_DB_PATH)
    cursor = conn.cursor()
    
    if status:
        cursor.execute(
            """
            SELECT * FROM sessions WHERE status = ?
            ORDER BY start_time DESC
            """,
            (status,)
        )
    else:
        cursor.execute(
            """
            SELECT * FROM sessions
            ORDER BY start_time DESC
            """
        )
    
    rows = cursor.fetchall()
    if limit:
        rows = rows[:limit]
    
    conn.close()
    
    sessions = []
    for row in rows:
        session = dict(row)
        # Deserialize metadata if present
        if session.get('metadata'):
            session['metadata'] = json.loads(session['metadata'])
        sessions.append(session)
    
    return sessions


def get_active_session():
    """
    Retrieves the currently active session (if any).
    
    Returns:
        Dictionary with session information or None if no active session
    """
    conn = get_db_connection(SESSIONS_DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT * FROM sessions WHERE status = 'active' ORDER BY start_time DESC LIMIT 1
        """
    )
    row = cursor.fetchone()
    conn.close()
    
    if row:
        session = dict(row)
        # Deserialize metadata if present
        if session.get('metadata'):
            session['metadata'] = json.loads(session['metadata'])
        return session
    return None


def track_session_operation(session_id, operation_id, operation_type, task_id=None, status='in_progress'):
    """
    Records an operation within a session.
    
    Args:
        session_id: The session ID
        operation_id: The operation ID (e.g., from telemetry)
        operation_type: Type of operation (implementation, verification, etc.)
        task_id: Optional task ID associated with this operation
        status: Initial status of the operation (in_progress, completed, failed)
        
    Returns:
        The ID of the inserted session operation record
    """
    conn = get_db_connection(SESSIONS_DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO session_operations (session_id, operation_id, task_id, operation_type, status, start_time)
        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """,
        (session_id, operation_id, task_id, operation_type, status)
    )
    op_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return op_id


def update_session_operation_status(session_op_id, status):
    """
    Updates the status of a session operation.
    
    Args:
        session_op_id: The session operation ID
        status: New status (completed, failed, interrupted)
    """
    conn = get_db_connection(SESSIONS_DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE session_operations SET status = ?, end_time = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (status, session_op_id)
    )
    conn.commit()
    conn.close()


def get_session_operations(session_id, operation_type=None, status=None):
    """
    Retrieves operations associated with a session.
    
    Args:
        session_id: The session ID
        operation_type: Optional operation type filter
        status: Optional status filter
        
    Returns:
        List of session operation dictionaries
    """
    conn = get_db_connection(SESSIONS_DB_PATH)
    cursor = conn.cursor()
    
    query = """
        SELECT * FROM session_operations WHERE session_id = ?
    """
    params = [session_id]
    
    if operation_type:
        query += " AND operation_type = ?"
        params.append(operation_type)
    
    if status:
        query += " AND status = ?"
        params.append(status)
    
    query += " ORDER BY start_time DESC"
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


def add_session_checkpoint(session_id, checkpoint_id, reason=None, is_auto=False):
    """
    Records a checkpoint associated with a session.
    
    Args:
        session_id: The session ID
        checkpoint_id: The checkpoint ID
        reason: Optional reason for the checkpoint
        is_auto: Whether this is an automatic checkpoint
    """
    conn = get_db_connection(SESSIONS_DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO session_checkpoints (session_id, checkpoint_id, checkpoint_time, reason, is_auto)
        VALUES (?, ?, CURRENT_TIMESTAMP, ?, ?)
        """,
        (session_id, checkpoint_id, reason, is_auto)
    )
    conn.commit()
    conn.close()


def get_session_checkpoints(session_id, auto_only=False):
    """
    Retrieves checkpoints associated with a session.
    
    Args:
        session_id: The session ID
        auto_only: If True, only return automatic checkpoints
        
    Returns:
        List of session checkpoint dictionaries
    """
    conn = get_db_connection(SESSIONS_DB_PATH)
    cursor = conn.cursor()
    
    if auto_only:
        cursor.execute(
            """
            SELECT * FROM session_checkpoints
            WHERE session_id = ? AND is_auto = 1
            ORDER BY checkpoint_time DESC
            """,
            (session_id,)
        )
    else:
        cursor.execute(
            """
            SELECT * FROM session_checkpoints
            WHERE session_id = ?
            ORDER BY checkpoint_time DESC
            """,
            (session_id,)
        )
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


def save_session_config(session_id, config_key, config_value):
    """
    Saves a configuration value for a session.
    
    Args:
        session_id: The session ID
        config_key: The configuration key
        config_value: The configuration value
    """
    conn = get_db_connection(SESSIONS_DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO session_config (session_id, config_key, config_value)
        VALUES (?, ?, ?)
        ON CONFLICT(session_id, config_key) DO UPDATE SET config_value = excluded.config_value
        """,
        (session_id, config_key, config_value)
    )
    conn.commit()
    conn.close()


def load_session_config(session_id, config_key):
    """
    Loads a configuration value for a session.
    
    Args:
        session_id: The session ID
        config_key: The configuration key
        
    Returns:
        The configuration value or None if not found
    """
    conn = get_db_connection(SESSIONS_DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT config_value FROM session_config
        WHERE session_id = ? AND config_key = ?
        """,
        (session_id, config_key)
    )
    row = cursor.fetchone()
    conn.close()
    
    return row['config_value'] if row else None


def get_session_config(session_id):
    """
    Retrieves all configuration for a session.
    
    Args:
        session_id: The session ID
        
    Returns:
        Dictionary of configuration key-value pairs
    """
    conn = get_db_connection(SESSIONS_DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT config_key, config_value FROM session_config
        WHERE session_id = ?
        """,
        (session_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    
    return {row['config_key']: row['config_value'] for row in rows}


def archive_session(session_id):
    """
    Archives a session by marking it as completed and keeping it for history.
    
    Args:
        session_id: The session ID to archive
    """
    conn = get_db_connection(SESSIONS_DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE sessions SET end_time = CURRENT_TIMESTAMP, status = 'archived'
        WHERE session_id = ? AND status != 'archived'
        """,
        (session_id,)
    )
    conn.commit()
    conn.close()


def delete_session(session_id):
    """
    Deletes a session and all associated data (operations, checkpoints, config).
    
    Args:
        session_id: The session ID to delete
    """
    conn = get_db_connection(SESSIONS_DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        DELETE FROM sessions WHERE session_id = ?
        """,
        (session_id,)
    )
    conn.commit()
    conn.close()


def get_session_statistics(session_id):
    """
    Retrieves statistics for a session.
    
    Args:
        session_id: The session ID
        
    Returns:
        Dictionary with session statistics:
        {
            'duration_seconds': int,
            'total_operations': int,
            'completed_operations': int,
            'failed_operations': int,
            'total_checkpoints': int,
            'auto_checkpoints': int
        }
    """
    conn = get_db_connection(SESSIONS_DB_PATH)
    cursor = conn.cursor()
    
    # Get session duration
    cursor.execute(
        """
        SELECT
            CASE 
                WHEN end_time IS NOT NULL 
                THEN strftime('%s', end_time) - strftime('%s', start_time)
                ELSE strftime('%s', 'now') - strftime('%s', start_time)
            END as duration
        FROM sessions WHERE session_id = ?
        """,
        (session_id,)
    )
    row = cursor.fetchone()
    duration = row['duration'] if row else 0
    
    # Get operation counts
    cursor.execute(
        """
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
            SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed
        FROM session_operations WHERE session_id = ?
        """,
        (session_id,)
    )
    row = cursor.fetchone()
    total_ops = row['total'] if row else 0
    completed_ops = row['completed'] if row else 0
    failed_ops = row['failed'] if row else 0
    
    # Get checkpoint counts
    cursor.execute(
        """
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN is_auto = 1 THEN 1 ELSE 0 END) as auto
        FROM session_checkpoints WHERE session_id = ?
        """,
        (session_id,)
    )
    row = cursor.fetchone()
    total_checkpoints = row['total'] if row else 0
    auto_checkpoints = row['auto'] if row else 0
    
    conn.close()
    
    return {
        'duration_seconds': duration,
        'total_operations': total_ops,
        'completed_operations': completed_ops,
        'failed_operations': failed_ops,
        'total_checkpoints': total_checkpoints,
        'auto_checkpoints': auto_checkpoints
    }
