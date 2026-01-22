"""
Session Manager Module - Handles session lifecycle and persistence.

This module provides session management capabilities for L4D, including:
- Creating new sessions with unique IDs
- Resuming existing sessions from state
- Listing and managing sessions
- Archiving and exporting session state
- Session validation and integrity checks
- Detecting and recovering from interrupted sessions
- Persisting session state across runs
"""

import json
import sqlite3
import uuid
import subprocess
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, List, Any, Tuple
import threading
import logging

logger = logging.getLogger(__name__)


class SessionStatus(Enum):
    """Session status enumeration."""
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"
    CORRUPTED = "corrupted"


class Session:
    """Represents a session with its state and metadata."""
    
    def __init__(
        self,
        session_id: str,
        start_time: datetime,
        status: SessionStatus = SessionStatus.ACTIVE,
        config: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        active_operations: Optional[List[str]] = None,
        active_tasks: Optional[List[int]] = None,
        checkpoint_id: Optional[str] = None,
        end_time: Optional[datetime] = None
    ):
        self.session_id = session_id
        self.start_time = start_time
        self.status = status
        self.config = config or {}
        self.metadata = metadata or {}
        self.active_operations = active_operations or []
        self.active_tasks = active_tasks or []
        self.checkpoint_id = checkpoint_id
        self.end_time = end_time
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary for serialization."""
        return {
            "session_id": self.session_id,
            "start_time": self.start_time.isoformat(),
            "status": self.status.value,
            "config": self.config,
            "metadata": self.metadata,
            "active_operations": self.active_operations,
            "active_tasks": self.active_tasks,
            "checkpoint_id": self.checkpoint_id,
            "end_time": self.end_time.isoformat() if self.end_time else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Session":
        """Create session from dictionary."""
        return cls(
            session_id=data["session_id"],
            start_time=datetime.fromisoformat(data["start_time"]),
            status=SessionStatus(data["status"]),
            config=data.get("config", {}),
            metadata=data.get("metadata", {}),
            active_operations=data.get("active_operations", []),
            active_tasks=data.get("active_tasks", []),
            checkpoint_id=data.get("checkpoint_id"),
            end_time=datetime.fromisoformat(data["end_time"]) if data.get("end_time") else None
        )


class SessionManager:
    """
    Manages session lifecycle, persistence, and operations.
    
    Provides functionality for creating, resuming, listing, and managing
    development sessions with full state persistence.
    """
    
    def __init__(self, db_path: str = "sessions.db"):
        """
        Initialize SessionManager.
        
        Args:
            db_path: Path to sessions database
        """
        self.db_path = db_path
        self.lock = threading.RLock()
        self._initialize_db()
    
    def _initialize_db(self) -> None:
        """Initialize sessions database schema."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Sessions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    status TEXT NOT NULL,
                    config TEXT NOT NULL,
                    metadata TEXT NOT NULL,
                    active_operations TEXT NOT NULL,
                    active_tasks TEXT NOT NULL,
                    checkpoint_id TEXT,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
            """)
            
            # Session checkpoints mapping table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS session_checkpoints (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    checkpoint_id TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
                )
            """)
            
            # Create indexes
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_status 
                ON sessions(status)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_start_time 
                ON sessions(start_time)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_session_checkpoints_session 
                ON session_checkpoints(session_id)
            """)
            
            conn.commit()
    
    def start_session(
        self,
        config: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Session:
        """
        Start a new session with unique ID.
        
        Args:
            config: Session configuration (LLM model, cache settings, etc.)
            metadata: Session metadata (user, host, environment)
            
        Returns:
            New Session object
            
        Example:
            >>> session = manager.start_session(
            ...     config={"llm_model": "gpt-4", "cache_enabled": True},
            ...     metadata={"user": "developer", "environment": "dev"}
            ... )
        """
        session_id = str(uuid.uuid4())
        start_time = datetime.now()
        
        session = Session(
            session_id=session_id,
            start_time=start_time,
            status=SessionStatus.ACTIVE,
            config=config or {},
            metadata=metadata or {}
        )
        
        self._save_session(session)
        return session
    
    def resume_session(self, session_id: str) -> Optional[Session]:
        """
        Resume an existing session from state.
        
        Args:
            session_id: ID of the session to resume
            
        Returns:
            Session object if found and valid, None otherwise
            
        Example:
            >>> session = manager.resume_session("abc-123")
            >>> if session:
            ...     print(f"Resumed session started at {session.start_time}")
        """
        with self.lock:
            session = self._load_session(session_id)
            
            if not session:
                return None
            
            # Validate session integrity
            if not self._validate_session(session):
                session.status = SessionStatus.CORRUPTED
                self._save_session(session)
                return None
            
            # Update session status to active
            session.status = SessionStatus.ACTIVE
            self._save_session(session)
            
            return session
    
    def pause_session(self, session_id: str) -> bool:
        """
        Pause an active session.
        
        Args:
            session_id: ID of the session to pause
            
        Returns:
            True if paused successfully, False otherwise
        """
        with self.lock:
            session = self._load_session(session_id)
            
            if not session or session.status != SessionStatus.ACTIVE:
                return False
            
            session.status = SessionStatus.PAUSED
            self._save_session(session)
            return True
    
    def complete_session(self, session_id: str) -> bool:
        """
        Mark a session as completed.
        
        Args:
            session_id: ID of the session to complete
            
        Returns:
            True if completed successfully, False otherwise
        """
        with self.lock:
            session = self._load_session(session_id)
            
            if not session:
                return False
            
            session.status = SessionStatus.COMPLETED
            session.end_time = datetime.now()
            self._save_session(session)
            return True
    
    def list_sessions(
        self,
        status: Optional[SessionStatus] = None,
        limit: Optional[int] = None
    ) -> List[Session]:
        """
        List sessions with optional filtering.
        
        Args:
            status: Filter by session status (None = all)
            limit: Maximum number of sessions to return (None = all)
            
        Returns:
            List of Session objects
            
        Example:
            >>> # List all active sessions
            >>> active = manager.list_sessions(status=SessionStatus.ACTIVE)
            >>> 
            >>> # List last 10 paused sessions
            >>> paused = manager.list_sessions(status=SessionStatus.PAUSED, limit=10)
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM sessions"
            params = []
            
            if status:
                query += " WHERE status = ?"
                params.append(status.value)
            
            query += " ORDER BY start_time DESC"
            
            if limit:
                query += " LIMIT ?"
                params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            return [self._row_to_session(row) for row in rows]
    
    def archive_session(self, session_id: str) -> bool:
        """
        Archive a session.
        
        Args:
            session_id: ID of the session to archive
            
        Returns:
            True if archived successfully, False otherwise
        """
        with self.lock:
            session = self._load_session(session_id)
            
            if not session or session.status == SessionStatus.ARCHIVED:
                return False
            
            session.status = SessionStatus.ARCHIVED
            if not session.end_time:
                session.end_time = datetime.now()
            
            self._save_session(session)
            return True
    
    def export_session(self, session_id: str, export_path: str) -> bool:
        """
        Export session state to a JSON file.
        
        Args:
            session_id: ID of the session to export
            export_path: Path to export file
            
        Returns:
            True if exported successfully, False otherwise
            
        Example:
            >>> manager.export_session("abc-123", "session_backup.json")
        """
        session = self._load_session(session_id)
        
        if not session:
            return False
        
        export_data = {
            "session": session.to_dict(),
            "exported_at": datetime.now().isoformat(),
            "version": "1.0"
        }
        
        try:
            Path(export_path).parent.mkdir(parents=True, exist_ok=True)
            with open(export_path, 'w') as f:
                json.dump(export_data, f, indent=2)
            return True
        except Exception:
            return False
    
    def import_session(self, import_path: str) -> Optional[Session]:
        """
        Import session state from a JSON file.
        
        Args:
            import_path: Path to import file
            
        Returns:
            Imported Session object if successful, None otherwise
            
        Example:
            >>> session = manager.import_session("session_backup.json")
        """
        try:
            with open(import_path, 'r') as f:
                import_data = json.load(f)
            
            session_data = import_data.get("session")
            if not session_data:
                return None
            
            session = Session.from_dict(session_data)
            
            # Generate new session ID to avoid conflicts
            session.session_id = str(uuid.uuid4())
            session.status = SessionStatus.PAUSED
            
            self._save_session(session)
            return session
        except Exception:
            return None
    
    def merge_sessions(self, source_id: str, target_id: str) -> bool:
        """
        Merge two sessions if they are compatible.
        
        Args:
            source_id: ID of source session to merge from
            target_id: ID of target session to merge into
            
        Returns:
            True if merged successfully, False otherwise
            
        Note:
            This is a basic implementation. In production, you'd want
            more sophisticated merge logic (e.g., conflict resolution).
        """
        with self.lock:
            source = self._load_session(source_id)
            target = self._load_session(target_id)
            
            if not source or not target:
                return False
            
            # Check if sessions are mergeable (basic check)
            if target.status not in [SessionStatus.ACTIVE, SessionStatus.PAUSED]:
                return False
            
            # Merge operations (avoid duplicates)
            for op in source.active_operations:
                if op not in target.active_operations:
                    target.active_operations.append(op)
            
            # Merge tasks (avoid duplicates)
            for task in source.active_tasks:
                if task not in target.active_tasks:
                    target.active_tasks.append(task)
            
            # Merge metadata (only add new keys, don't overwrite existing)
            for key, value in source.metadata.items():
                if key not in target.metadata:
                    target.metadata[key] = value
            
            self._save_session(target)
            return True
    
    def _save_session(self, session: Session) -> None:
        """Save session to database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO sessions 
                (session_id, start_time, end_time, status, config, metadata, 
                 active_operations, active_tasks, checkpoint_id, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            """, (
                session.session_id,
                session.start_time.isoformat(),
                session.end_time.isoformat() if session.end_time else None,
                session.status.value,
                json.dumps(session.config),
                json.dumps(session.metadata),
                json.dumps(session.active_operations),
                json.dumps(session.active_tasks),
                session.checkpoint_id
            ))
            
            conn.commit()
    
    def _load_session(self, session_id: str) -> Optional[Session]:
        """Load session from database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM sessions WHERE session_id = ?
            """, (session_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            return self._row_to_session(row)
    
    def _row_to_session(self, row: tuple) -> Session:
        """Convert database row to Session object."""
        return Session(
            session_id=row[0],
            start_time=datetime.fromisoformat(row[1]),
            end_time=datetime.fromisoformat(row[2]) if row[2] else None,
            status=SessionStatus(row[3]),
            config=json.loads(row[4]),
            metadata=json.loads(row[5]),
            active_operations=json.loads(row[6]),
            active_tasks=json.loads(row[7]),
            checkpoint_id=row[8]
        )
    
    def _validate_session(self, session: Session) -> bool:
        """
        Validate session integrity.
        
        Args:
            session: Session to validate
            
        Returns:
            True if session is valid, False otherwise
        """
        # Basic validation
        if not session.session_id:
            return False
        
        if not session.start_time:
            return False
        
        if session.status == SessionStatus.CORRUPTED:
            return False
        
        # Validate checkpoint if exists
        if session.checkpoint_id:
            # In production, verify checkpoint exists and is valid
            # For now, just check it's not empty
            if not session.checkpoint_id.strip():
                return False
        
        return True
    
    def get_active_session(self) -> Optional[Session]:
        """
        Get the currently active session (if any).
        
        Returns:
            Active Session object or None
            
        Example:
            >>> session = manager.get_active_session()
            >>> if session:
            ...     print(f"Working on session {session.session_id}")
        """
        sessions = self.list_sessions(status=SessionStatus.ACTIVE, limit=1)
        return sessions[0] if sessions else None
    
    def cleanup_old_sessions(self, days: int = 30) -> int:
        """
        Archive sessions older than specified days.
        
        Args:
            days: Number of days after which to archive sessions
            
        Returns:
            Number of sessions archived
            
        Example:
            >>> count = manager.cleanup_old_sessions(days=30)
            >>> print(f"Archived {count} old sessions")
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE sessions 
                SET status = ?, end_time = datetime('now'), updated_at = datetime('now')
                WHERE start_time < datetime('now', '-' || ? || ' days')
                AND status IN (?, ?)
            """, (
                SessionStatus.ARCHIVED.value,
                days,
                SessionStatus.COMPLETED.value,
                SessionStatus.PAUSED.value
            ))
            
            count = cursor.rowcount
            conn.commit()
            
            return count
    
    def detect_interrupted_sessions(self) -> List[Session]:
        """
        Detect sessions that were interrupted (active or recently paused).
        
        Returns:
            List of interrupted sessions
            
        Example:
            >>> interrupted = manager.detect_interrupted_sessions()
            >>> if interrupted:
            ...     print(f"Found {len(interrupted)} interrupted sessions")
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Find sessions that were active or paused in the last hour
            # These are likely interrupted sessions
            cursor.execute("""
                SELECT * FROM sessions 
                WHERE status IN (?, ?)
                AND (end_time IS NULL OR end_time > datetime('now', '-1 hour'))
                ORDER BY start_time DESC
            """, (SessionStatus.ACTIVE.value, SessionStatus.PAUSED.value))
            
            rows = cursor.fetchall()
            return [self._row_to_session(row) for row in rows]
    
    def save_session_on_shutdown(self, session_id: str, checkpoint_id: Optional[str] = None) -> bool:
        """
        Save session state before shutdown (graceful or interrupt).
        
        Args:
            session_id: ID of the session to save
            checkpoint_id: Optional checkpoint ID to associate with session
            
        Returns:
            True if saved successfully, False otherwise
            
        Example:
            >>> manager.save_session_on_shutdown("abc-123", checkpoint_id="chk-456")
        """
        with self.lock:
            session = self._load_session(session_id)
            
            if not session:
                logger.warning(f"Session {session_id} not found for shutdown save")
                return False
            
            # Update session status to paused (not completed, since we're shutting down)
            if session.status == SessionStatus.ACTIVE:
                session.status = SessionStatus.PAUSED
            
            # Associate checkpoint if provided
            if checkpoint_id:
                session.checkpoint_id = checkpoint_id
                self._save_checkpoint_mapping(session_id, checkpoint_id)
            
            # Record shutdown timestamp in metadata
            session.metadata["last_shutdown"] = datetime.now().isoformat()
            
            self._save_session(session)
            logger.info(f"Session {session_id} saved successfully on shutdown")
            return True
    
    def _save_checkpoint_mapping(self, session_id: str, checkpoint_id: str) -> None:
        """Save checkpoint to session mapping."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO session_checkpoints (session_id, checkpoint_id)
                VALUES (?, ?)
            """, (session_id, checkpoint_id))
            
            conn.commit()
    
    def restore_session_on_startup(self, session_id: str, checkpoint_manager=None) -> Tuple[Optional[Session], bool]:
        """
        Restore session on startup, checking for external changes.
        
        Args:
            session_id: ID of the session to restore
            checkpoint_manager: Optional CheckpointManager instance for state restoration
            
        Returns:
            Tuple of (restored Session, has_external_changes)
            
        Example:
            >>> session, has_changes = manager.restore_session_on_startup("abc-123")
            >>> if session:
            ...     if has_changes:
            ...         print("External changes detected - merge needed")
            ...     else:
            ...         print("Session restored cleanly")
        """
        with self.lock:
            session = self._load_session(session_id)
            
            if not session:
                logger.warning(f"Session {session_id} not found for restoration")
                return None, False
            
            # Check for external changes
            has_external_changes = self._check_external_changes()
            
            if has_external_changes:
                logger.warning(f"External changes detected for session {session_id}")
                # Don't automatically restore - let user decide
                return session, True
            
            # Restore from checkpoint if available
            if session.checkpoint_id and checkpoint_manager:
                try:
                    logger.info(f"Restoring session {session_id} from checkpoint {session.checkpoint_id}")
                    success = checkpoint_manager.restore(session.checkpoint_id)
                    if not success:
                        logger.error(f"Failed to restore checkpoint {session.checkpoint_id}")
                        return None, False
                except Exception as e:
                    logger.error(f"Error restoring checkpoint: {e}")
                    return None, False
            
            # Set session to active
            session.status = SessionStatus.ACTIVE
            self._save_session(session)
            
            logger.info(f"Session {session_id} restored successfully")
            return session, False
    
    def _check_external_changes(self) -> bool:
        """
        Check if there are external changes to the git repository.
        
        Returns:
            True if external changes detected, False otherwise
        """
        try:
            # Check if git repository exists
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                # Not a git repository, assume no changes
                return False
            
            # Check for uncommitted changes
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True
            )
            
            # If there are any changes, return True
            if result.stdout.strip():
                logger.info("External changes detected in git repository")
                return True
            
            # Check if HEAD has moved (different commits)
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                current_head = result.stdout.strip()
                
                # Store last known head in session metadata
                # For now, just assume changes if HEAD is different
                # In production, store last HEAD in session metadata
                
            return False
            
        except Exception as e:
            logger.warning(f"Error checking external changes: {e}")
            return False
    
    def handle_merge_conflicts(self, session_id: str, external_session_id: str) -> bool:
        """
        Handle merge conflicts when external work conflicts with session.
        
        Args:
            session_id: ID of the current session
            external_session_id: ID of the session with external changes
            
        Returns:
            True if merge was successful, False otherwise
            
        Example:
            >>> success = manager.handle_merge_conflicts("abc-123", "def-456")
            >>> if success:
            ...     print("Merge completed successfully")
            ... else:
            ...     print("Merge failed - manual resolution needed")
        """
        with self.lock:
            current = self._load_session(session_id)
            external = self._load_session(external_session_id)
            
            if not current or not external:
                logger.error("One or both sessions not found for merge")
                return False
            
            # Basic merge strategy:
            # 1. Preserve user's work if safe
            # 2. Merge tasks and operations
            # 3. Update checkpoint to latest state
            
            try:
                # Check git status for conflicts
                result = subprocess.run(
                    ["git", "status", "--porcelain"],
                    capture_output=True,
                    text=True
                )
                
                # If there are conflicts, warn user
                if "U " in result.stdout:
                    logger.warning("Git merge conflicts detected - manual resolution required")
                    # In production, provide merge tools or interactive resolution
                    return False
                
                # Merge tasks (avoid duplicates)
                for task in external.active_tasks:
                    if task not in current.active_tasks:
                        current.active_tasks.append(task)
                
                # Merge operations (avoid duplicates)
                for op in external.active_operations:
                    if op not in current.active_operations:
                        current.active_operations.append(op)
                
                # Merge metadata
                for key, value in external.metadata.items():
                    if key not in current.metadata:
                        current.metadata[key] = value
                
                # Archive the external session
                self.archive_session(external_session_id)
                
                # Save merged session
                self._save_session(current)
                
                logger.info(f"Successfully merged external session {external_session_id} into {session_id}")
                return True
                
            except Exception as e:
                logger.error(f"Error during merge: {e}")
                return False
    
    def cleanup_stale_sessions(self, hours: int = 24) -> int:
        """
        Clean up stale/interrupted sessions that are too old.
        
        Args:
            hours: Number of hours after which sessions are considered stale
            
        Returns:
            Number of sessions archived
            
        Example:
            >>> count = manager.cleanup_stale_sessions(hours=24)
            >>> print(f"Cleaned up {count} stale sessions")
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE sessions 
                SET status = ?, end_time = datetime('now'), updated_at = datetime('now')
                WHERE status IN (?, ?)
                AND (end_time IS NULL OR updated_at < datetime('now', '-' || ? || ' hours'))
            """, (
                SessionStatus.ARCHIVED.value,
                SessionStatus.ACTIVE.value,
                SessionStatus.PAUSED.value,
                hours
            ))
            
            count = cursor.rowcount
            conn.commit()
            
            logger.info(f"Archived {count} stale sessions")
            return count


# Singleton instance for easy access
_default_manager: Optional[SessionManager] = None


def get_session_manager(db_path: str = "sessions.db") -> SessionManager:
    """
    Get or create the default SessionManager instance.
    
    Args:
        db_path: Path to sessions database (only used on first call)
        
    Returns:
        SessionManager instance
        
    Example:
        >>> manager = get_session_manager()
        >>> session = manager.start_session()
    """
    global _default_manager
    
    if _default_manager is None:
        _default_manager = SessionManager(db_path)
    
    return _default_manager
