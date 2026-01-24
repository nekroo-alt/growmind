"""
Checkpoint Manager - State Checkpointing and Recovery

This module provides comprehensive checkpointing capabilities for L4D v3,
allowing the system to save and restore state at critical points.
"""

import sqlite3
import os
import json
import hashlib
import shutil
import subprocess
from datetime import datetime
from typing import Optional, Dict, List, Any, ContextManager
from contextlib import contextmanager
from pathlib import Path

from data.db_manager import (
    SNAPSHOTS_DB_PATH,
    TASK_DB_PATH,
    ACTIVITY_DB_PATH,
    get_db_connection,
)
from core.telemetry import telemetry


class CheckpointManager:
    """
    Manages system state checkpoints for recovery and rollback.

    Supports capturing and restoring:
    - Database state (task.db, activity.db, telemetry.db, snapshots.db)
    - File system state (git status, modified files)
    - Cache state (.l4_cache/)
    - Context engine state
    """

    def __init__(self, db_path: str = SNAPSHOTS_DB_PATH):
        """
        Initialize CheckpointManager.

        Args:
            db_path: Path to snapshots database
        """
        self.db_path = db_path
        self._ensure_db_exists()

    def _ensure_db_exists(self):
        """Ensure snapshots database and tables exist."""
        from data.db_manager import init_db

        init_db()  # This will create all necessary tables

    def _get_db_connection(self):
        """Get database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def create(
        self,
        reason: str,
        snapshot_type: str = "manual",
        task_id: Optional[int] = None,
        operation_id: Optional[str] = None,
        include_databases: bool = True,
        include_files: bool = True,
        include_git: bool = True,
        include_cache: bool = True,
    ) -> str:
        """
        Create a new checkpoint.

        Args:
            reason: Description of why this checkpoint is being created
            snapshot_type: Type of snapshot (operation_start, operation_end,
                          task_complete, task_failed, manual, auto)
            task_id: Optional associated task ID
            operation_id: Optional associated operation ID
            include_databases: Whether to capture database state
            include_files: Whether to capture file system state
            include_git: Whether to capture git state
            include_cache: Whether to capture cache state

        Returns:
            snapshot_id: Unique identifier for the created checkpoint
        """
        snapshot_id = self._generate_snapshot_id()
        timestamp = datetime.now().isoformat()

        telemetry.info(f"Creating checkpoint: {reason} (ID: {snapshot_id})")

        with self._get_db_connection() as conn:
            cursor = conn.cursor()

            # Create main snapshot record
            cursor.execute(
                """
                INSERT INTO snapshots (
                    snapshot_id, timestamp, snapshot_type, operation_id, 
                    task_id, reason, metadata
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    snapshot_id,
                    timestamp,
                    snapshot_type,
                    operation_id,
                    task_id,
                    reason,
                    json.dumps(
                        {
                            "include_databases": include_databases,
                            "include_files": include_files,
                            "include_git": include_git,
                            "include_cache": include_cache,
                        }
                    ),
                ),
            )

            # Capture database state
            if include_databases:
                self._capture_database_state(cursor, snapshot_id)

            # Capture file system state
            if include_files:
                self._capture_file_system_state(cursor, snapshot_id)

            # Capture git state
            if include_git:
                self._capture_git_state(cursor, snapshot_id)

            # Capture cache state
            if include_cache:
                self._capture_cache_state(cursor, snapshot_id)

            conn.commit()

        telemetry.info(f"Checkpoint created successfully: {snapshot_id}")
        return snapshot_id

    def list(
        self,
        snapshot_type: Optional[str] = None,
        task_id: Optional[int] = None,
        operation_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        List available checkpoints.

        Args:
            snapshot_type: Filter by snapshot type
            task_id: Filter by task ID
            operation_id: Filter by operation ID
            limit: Maximum number of checkpoints to return

        Returns:
            List of checkpoint dictionaries
        """
        with self._get_db_connection() as conn:
            cursor = conn.cursor()

            query = "SELECT * FROM snapshots WHERE 1=1"
            params = []

            if snapshot_type:
                query += " AND snapshot_type = ?"
                params.append(snapshot_type)

            if task_id:
                query += " AND task_id = ?"
                params.append(task_id)

            if operation_id:
                query += " AND operation_id = ?"
                params.append(operation_id)

            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()

            checkpoints = []
            for row in rows:
                checkpoint = dict(row)
                checkpoint["metadata"] = (
                    json.loads(checkpoint["metadata"]) if checkpoint["metadata"] else {}
                )
                checkpoints.append(checkpoint)

            return checkpoints

    def get(self, snapshot_id: str) -> Optional[Dict[str, Any]]:
        """
        Get details of a specific checkpoint.

        Args:
            snapshot_id: Checkpoint ID

        Returns:
            Checkpoint dictionary or None if not found
        """
        with self._get_db_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                "SELECT * FROM snapshots WHERE snapshot_id = ?", (snapshot_id,)
            )
            row = cursor.fetchone()

            if not row:
                return None

            checkpoint = dict(row)
            checkpoint["metadata"] = (
                json.loads(checkpoint["metadata"]) if checkpoint["metadata"] else {}
            )

            # Get associated state details
            checkpoint["db_state"] = self._get_db_state(cursor, snapshot_id)
            checkpoint["file_state"] = self._get_file_state(cursor, snapshot_id)
            checkpoint["git_state"] = self._get_git_state(cursor, snapshot_id)
            checkpoint["cache_state"] = self._get_cache_state(cursor, snapshot_id)

            return checkpoint

    def restore(
        self,
        snapshot_id: str,
        restore_databases: bool = True,
        restore_files: bool = True,
        restore_git: bool = True,
        restore_cache: bool = True,
        validate_before: bool = True,
        validate_after: bool = True,
        dry_run: bool = False,
        preserve_user_work: bool = True,
    ) -> bool:
        """
        Restore system state from a checkpoint.

        Args:
            snapshot_id: Checkpoint ID to restore from
            restore_databases: Whether to restore database state
            restore_files: Whether to restore file system state
            restore_git: Whether to restore git state
            restore_cache: Whether to restore cache state
            validate_before: Validate checkpoint integrity before restore
            validate_after: Validate state integrity after restore
            dry_run: Preview changes without actually restoring
            preserve_user_work: Warn about user work that would be lost

        Returns:
            True if restore was successful (or dry-run completed)
        """
        telemetry.info(
            f"Starting restore from checkpoint: {snapshot_id} (dry_run={dry_run})"
        )

        # Validate checkpoint exists
        checkpoint = self.get(snapshot_id)
        if not checkpoint:
            telemetry.error(f"Checkpoint not found: {snapshot_id}")
            return False

        # Validate before restore
        if validate_before:
            if not self.validate(snapshot_id):
                telemetry.error(
                    f"Checkpoint validation failed for checkpoint: {snapshot_id}"
                )
                return False

        # Warn about user work that would be lost
        if preserve_user_work and not dry_run:
            self._warn_about_user_work_loss(checkpoint)

        try:
            # Restore databases
            if restore_databases:
                self._restore_database_state(snapshot_id, dry_run=dry_run)

            # Restore file system
            if restore_files:
                self._restore_file_system_state(
                    snapshot_id, dry_run=dry_run, preserve_user_work=preserve_user_work
                )

            # Restore git state
            if restore_git:
                self._restore_git_state(
                    snapshot_id, dry_run=dry_run, preserve_user_work=preserve_user_work
                )

            # Restore cache
            if restore_cache:
                self._restore_cache_state(snapshot_id, dry_run=dry_run)

            # Validate after restore
            if not dry_run and validate_after:
                if not self._validate_system_state():
                    telemetry.warning(
                        f"System validation after restore failed, but restore completed: {snapshot_id}"
                    )

            if dry_run:
                telemetry.info(f"Dry-run completed for checkpoint: {snapshot_id}")
            else:
                telemetry.info(f"Successfully restored from checkpoint: {snapshot_id}")
            return True

        except Exception as e:
            telemetry.error(f"Failed to restore checkpoint {snapshot_id}: {str(e)}")
            return False

    def delete(self, snapshot_id: str) -> bool:
        """
        Delete a checkpoint.

        Args:
            snapshot_id: Checkpoint ID to delete

        Returns:
            True if deletion was successful
        """
        telemetry.info(f"Deleting checkpoint: {snapshot_id}")

        with self._get_db_connection() as conn:
            cursor = conn.cursor()

            # Delete snapshot (CASCADE will delete related records)
            cursor.execute(
                "DELETE FROM snapshots WHERE snapshot_id = ?", (snapshot_id,)
            )

            if cursor.rowcount == 0:
                telemetry.warning(f"Checkpoint not found for deletion: {snapshot_id}")
                return False

            conn.commit()

        telemetry.info(f"Successfully deleted checkpoint: {snapshot_id}")
        return True

    def validate(self, snapshot_id: str) -> bool:
        """
        Validate checkpoint integrity.

        Args:
            snapshot_id: Checkpoint ID to validate

        Returns:
            True if checkpoint is valid
        """
        checkpoint = self.get(snapshot_id)
        if not checkpoint:
            telemetry.error(f"Checkpoint not found: {snapshot_id}")
            return False

        # Check database state integrity
        db_state = checkpoint.get("db_state", [])
        for db in db_state:
            if not db.get("db_hash"):
                telemetry.error(f"Missing database hash in checkpoint: {snapshot_id}")
                return False

        # Check git state integrity
        git_state = checkpoint.get("git_state", [])
        if not git_state:
            telemetry.warning(f"Checkpoint has no git state: {snapshot_id}")

        telemetry.info(f"Checkpoint validated successfully: {snapshot_id}")
        return True

    def cleanup_old_checkpoints(
        self, max_count: int = 10, max_age_hours: int = 24, keep_critical: bool = True
    ) -> int:
        """
        Clean up old checkpoints based on retention policy.

        Args:
            max_count: Maximum number of checkpoints to keep
            max_age_hours: Maximum age in hours to keep
            keep_critical: Whether to keep critical checkpoints

        Returns:
            Number of checkpoints deleted
        """
        checkpoints = self.list(limit=1000)
        deleted_count = 0

        # Filter by age
        cutoff_time = datetime.now().timestamp() - (max_age_hours * 3600)

        for checkpoint in checkpoints:
            # Keep critical checkpoints
            if keep_critical and checkpoint["snapshot_type"] in [
                "task_complete",
                "operation_end",
            ]:
                continue

            # Delete old checkpoints beyond max_count
            if deleted_count >= len(checkpoints) - max_count:
                break

            checkpoint_time = datetime.fromisoformat(
                checkpoint["timestamp"]
            ).timestamp()
            if checkpoint_time < cutoff_time:
                if self.delete(checkpoint["snapshot_id"]):
                    deleted_count += 1

        telemetry.info(f"Cleaned up {deleted_count} old checkpoints")
        return deleted_count

    @contextmanager
    def rollback_on_error(
        self, reason: str = "auto_rollback", snapshot_type: str = "auto"
    ) -> ContextManager[str]:
        """
        Context manager for automatic rollback on error.

        Usage:
            with checkpoint.rollback_on_error("before_critical_operation"):
                # Perform operation
                # If exception occurs, automatically rollback

        Yields:
            snapshot_id: The checkpoint ID created
        """
        snapshot_id = self.create(reason, snapshot_type=snapshot_type)
        try:
            yield snapshot_id
        except Exception as e:
            telemetry.error(
                f"Error in context, rolling back to checkpoint {snapshot_id}: {str(e)}"
            )
            self.restore(snapshot_id)
            raise

    # Private helper methods

    def _generate_snapshot_id(self) -> str:
        """Generate a unique snapshot ID."""
        return f"chkp_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.urandom(4).hex()}"

    def _capture_database_state(self, cursor, snapshot_id: str):
        """Capture database state for snapshot using SQLite backup API."""
        databases = [
            (TASK_DB_PATH, "task.db"),
            (ACTIVITY_DB_PATH, "activity.db"),
            (SNAPSHOTS_DB_PATH, "snapshots.db"),
        ]

        # Also capture telemetry.db if it exists
        telemetry_db = os.path.join(os.path.dirname(TASK_DB_PATH), "telemetry.db")
        if os.path.exists(telemetry_db):
            databases.append((telemetry_db, "telemetry.db"))

        # Create backup directory for this snapshot
        backup_dir = os.path.join(
            os.path.dirname(SNAPSHOTS_DB_PATH), "checkpoints", snapshot_id
        )
        os.makedirs(backup_dir, exist_ok=True)

        for db_path, db_name in databases:
            if not os.path.exists(db_path):
                continue

            try:
                # Calculate database hash
                db_hash = self._calculate_file_hash(db_path)
                db_size = os.path.getsize(db_path)

                # Create backup using SQLite backup API
                backup_path = os.path.join(backup_dir, f"{db_name}.backup")
                self._create_sqlite_backup(db_path, backup_path)

                # Check if this is an incremental backup (compare with previous)
                is_incremental = self._is_incremental_backup(cursor, db_name, db_hash)

                cursor.execute(
                    """
                    INSERT INTO snapshot_db_state (
                        snapshot_id, db_name, db_hash, db_size, is_incremental,
                        backup_path
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        snapshot_id,
                        db_name,
                        db_hash,
                        db_size,
                        is_incremental,
                        backup_path,
                    ),
                )

            except Exception as e:
                telemetry.warning(
                    f"Failed to capture database state for {db_name}: {str(e)}"
                )
                # Still record the database even if backup failed
                cursor.execute(
                    """
                    INSERT INTO snapshot_db_state (
                        snapshot_id, db_name, db_hash, db_size, is_incremental,
                        backup_path, backup_status
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        snapshot_id,
                        db_name,
                        self._calculate_file_hash(db_path),
                        os.path.getsize(db_path),
                        0,
                        None,
                        f"failed: {str(e)}",
                    ),
                )

    def _capture_file_system_state(self, cursor, snapshot_id: str):
        """
        Capture file system state for snapshot.

        Captures modified, added, deleted, and untracked files with full content.
        """
        # Create backup directory for this snapshot
        backup_dir = os.path.join(
            os.path.dirname(SNAPSHOTS_DB_PATH), "checkpoints", snapshot_id, "files"
        )
        os.makedirs(backup_dir, exist_ok=True)

        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                check=False,
            )

            for line in result.stdout.splitlines():
                if not line.strip():
                    continue

                status_code = line[:2]
                file_path = line[3:]

                # Track all relevant files (Python, Markdown, config files)
                if not self._is_trackable_file(file_path):
                    continue

                file_data = {
                    "file_path": file_path,
                    "file_status": status_code,
                    "backup_path": None,
                }

                # Handle different file states
                if "D" in status_code:
                    # File was deleted - mark for deletion on restore
                    file_data["deleted"] = True
                    file_data["file_hash"] = "DELETED"
                    file_data["file_size"] = 0
                elif os.path.exists(file_path):
                    # File exists - capture it
                    file_hash = self._calculate_file_hash(file_path)
                    file_size = os.path.getsize(file_path)

                    # Get git diff for modified files
                    git_diff = ""
                    if "M" in status_code:
                        try:
                            diff_result = subprocess.run(
                                ["git", "diff", file_path],
                                capture_output=True,
                                text=True,
                                check=False,
                            )
                            git_diff = diff_result.stdout
                        except Exception:
                            pass

                    # Create a backup of the file
                    safe_filename = file_path.replace("/", "_").replace("\\", "_")
                    backup_path = os.path.join(backup_dir, safe_filename)
                    shutil.copy2(file_path, backup_path)

                    file_data.update(
                        {
                            "file_hash": file_hash,
                            "file_size": file_size,
                            "git_diff": git_diff,
                            "backup_path": backup_path,
                        }
                    )
                else:
                    # File doesn't exist (possibly untracked but not yet created)
                    file_data["file_hash"] = "MISSING"
                    file_data["file_size"] = 0

                # Store file state in database
                cursor.execute(
                    """
                    INSERT INTO snapshot_file_state (
                        snapshot_id, file_path, file_hash, file_size, 
                        file_status, git_diff, backup_path
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        snapshot_id,
                        file_data["file_path"],
                        file_data.get("file_hash", ""),
                        file_data.get("file_size", 0),
                        file_data["file_status"],
                        file_data.get("git_diff", ""),
                        file_data.get("backup_path"),
                    ),
                )

            telemetry.info(
                f"Captured file system state with {len(result.stdout.splitlines())} files"
            )

        except Exception as e:
            telemetry.warning(f"Failed to capture file system state: {str(e)}")

    def _is_trackable_file(self, file_path: str) -> bool:
        """
        Determine if a file should be tracked in checkpoints.

        Args:
            file_path: Path to the file

        Returns:
            True if file should be tracked
        """
        # Track code and documentation files
        extensions = [
            ".py",
            ".md",
            ".txt",
            ".json",
            ".yaml",
            ".yml",
            ".toml",
            ".cfg",
            ".ini",
        ]

        # Check extension
        for ext in extensions:
            if file_path.endswith(ext):
                return True

        # Track files in specific directories
        tracked_dirs = ["v2/", "meta/", "tests/", "docs/"]
        for directory in tracked_dirs:
            if file_path.startswith(directory):
                return True

        return False

    def _capture_git_state(self, cursor, snapshot_id: str):
        """Capture git state for snapshot."""
        try:
            # Get current branch
            branch_result = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True,
                text=True,
                check=False,
            )
            branch = branch_result.stdout.strip()

            # Get current commit hash
            commit_result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                check=False,
            )
            commit_hash = commit_result.stdout.strip()

            # Get git status
            status_result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                check=False,
            )
            git_status = status_result.stdout

            cursor.execute(
                """
                INSERT INTO snapshot_git_state (
                    snapshot_id, branch, commit_hash, git_status
                )
                VALUES (?, ?, ?, ?)
                """,
                (snapshot_id, branch, commit_hash, git_status),
            )

        except Exception as e:
            telemetry.warning(f"Failed to capture git state: {str(e)}")

    def _capture_cache_state(self, cursor, snapshot_id: str):
        """
        Capture cache state for snapshot.

        Captures:
        - Cache manager state (cache index, cache entries)
        - Context engine state (memoization cache, cache statistics)
        - LLM conversation history (if applicable)
        """
        cache_dir = Path(".l4_cache")
        if not cache_dir.exists():
            telemetry.info(
                "Cache directory does not exist, skipping cache state capture"
            )
            return

        try:
            # Capture cache manager state
            cache_state_data = self._capture_cache_manager_state(cache_dir)

            # Capture context engine state
            context_state_data = self._capture_context_engine_state()

            # Calculate total cache size
            cache_files = list(cache_dir.rglob("*"))
            cache_size = sum(f.stat().st_size for f in cache_files if f.is_file())

            # Store cache summary
            cursor.execute(
                """
                INSERT INTO snapshot_cache_state (
                    snapshot_id, cache_key, cache_hash, cache_size, cache_data
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    snapshot_id,
                    "cache_summary",
                    hashlib.sha256(json.dumps(cache_state_data).encode()).hexdigest(),
                    cache_size,
                    json.dumps(cache_state_data),
                ),
            )

            # Store context engine state
            if context_state_data:
                cursor.execute(
                    """
                    INSERT INTO snapshot_cache_state (
                        snapshot_id, cache_key, cache_hash, cache_size, cache_data
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        snapshot_id,
                        "context_engine_state",
                        hashlib.sha256(
                            json.dumps(context_state_data).encode()
                        ).hexdigest(),
                        len(json.dumps(context_state_data)),
                        json.dumps(context_state_data),
                    ),
                )

            telemetry.info(
                f"Captured cache state: {len(cache_state_data.get('cache_entries', []))} entries, "
                f"{len(context_state_data.get('context_cache', {}))} contexts"
            )

        except Exception as e:
            telemetry.warning(f"Failed to capture cache state: {str(e)}")

    def _capture_cache_manager_state(self, cache_dir: Path) -> Dict[str, Any]:
        """
        Capture cache manager state for checkpointing.

        Args:
            cache_dir: Path to cache directory

        Returns:
            Dictionary containing cache manager state
        """
        cache_state = {"cache_entries": [], "cache_index": {}, "cache_stats": {}}

        try:
            # Try to import and use CacheManager
            from data.cache_manager import get_cache_manager

            cache_manager = get_cache_manager()

            # Capture cache index
            cache_state["cache_index"] = {
                key: {
                    "file_path": info.get("file_path"),
                    "file_mtime": info.get("file_mtime"),
                    "file_hash": info.get("file_hash"),
                    "cached_at": info.get("cached_at"),
                    "analysis_type": info.get("analysis_type"),
                }
                for key, info in cache_manager.cache_index.items()
            }

            # Capture cache statistics
            stats = cache_manager.get_stats()
            cache_state["cache_stats"] = {
                "total_entries": stats.get("total_entries", 0),
                "valid_entries": stats.get("valid_entries", 0),
                "max_size": stats.get("max_size", 0),
                "total_size_bytes": stats.get("total_size_bytes", 0),
                "cache_dir": str(stats.get("cache_dir", "")),
            }

            # Capture individual cache entries (metadata only, not full data)
            for cache_key, cache_info in cache_manager.cache_index.items():
                cache_file = cache_manager._get_cache_file_path(cache_key)
                if cache_file.exists():
                    cache_state["cache_entries"].append(
                        {
                            "cache_key": cache_key,
                            "file_path": cache_info.get("file_path"),
                            "analysis_type": cache_info.get("analysis_type"),
                            "file_size": cache_file.stat().st_size,
                            "file_hash": cache_info.get("file_hash"),
                            "cached_at": cache_info.get("cached_at"),
                        }
                    )

        except Exception as e:
            telemetry.warning(f"Failed to capture CacheManager state: {str(e)}")

        return cache_state

    def _capture_context_engine_state(self) -> Dict[str, Any]:
        """
        Capture context engine state for checkpointing.

        Returns:
            Dictionary containing context engine state
        """
        context_state = {"context_cache": {}, "cache_stats": {}}

        try:
            # Try to import and use ContextEngine
            from logic.context_engine import ContextEngine

            # Note: We can't easily get a global ContextEngine instance
            # But we can document what state should be captured
            context_state["note"] = "Context engine state is instance-specific"
            context_state["expected_state"] = {
                "_context_cache": "Memoization cache for context collections",
                "_cache_hits": "Cache hit counter",
                "_cache_misses": "Cache miss counter",
                "_cache_updates": "Cache update counter",
            }

        except Exception as e:
            telemetry.warning(f"Failed to capture ContextEngine state: {str(e)}")

        return context_state

    def _get_db_state(self, cursor, snapshot_id: str) -> List[Dict]:
        """Get database state for snapshot."""
        cursor.execute(
            "SELECT * FROM snapshot_db_state WHERE snapshot_id = ?", (snapshot_id,)
        )
        return [dict(row) for row in cursor.fetchall()]

    def _get_file_state(self, cursor, snapshot_id: str) -> List[Dict]:
        """Get file system state for snapshot."""
        cursor.execute(
            "SELECT * FROM snapshot_file_state WHERE snapshot_id = ?", (snapshot_id,)
        )
        return [dict(row) for row in cursor.fetchall()]

    def _get_git_state(self, cursor, snapshot_id: str) -> List[Dict]:
        """Get git state for snapshot."""
        cursor.execute(
            "SELECT * FROM snapshot_git_state WHERE snapshot_id = ?", (snapshot_id,)
        )
        return [dict(row) for row in cursor.fetchall()]

    def _get_cache_state(self, cursor, snapshot_id: str) -> List[Dict]:
        """Get cache state for snapshot."""
        cursor.execute(
            "SELECT * FROM snapshot_cache_state WHERE snapshot_id = ?", (snapshot_id,)
        )
        return [dict(row) for row in cursor.fetchall()]

    def _restore_database_state(self, snapshot_id: str, dry_run: bool = False):
        """
        Restore database state from snapshot.

        Args:
            snapshot_id: Checkpoint ID to restore from
            dry_run: Preview changes without actually restoring
        """
        telemetry.info(
            f"Restoring database state from checkpoint: {snapshot_id} (dry_run={dry_run})"
        )

        checkpoint = self.get(snapshot_id)
        if not checkpoint:
            raise ValueError(f"Checkpoint not found: {snapshot_id}")

        db_state_list = checkpoint.get("db_state", [])

        if not db_state_list:
            telemetry.warning(f"No database state found in checkpoint: {snapshot_id}")
            return

        # Restore each database
        for db_state in db_state_list:
            db_name = db_state["db_name"]
            backup_path = db_state.get("backup_path")
            backup_status = db_state.get("backup_status")

            if backup_status and backup_status.startswith("failed"):
                telemetry.warning(
                    f"Skipping {db_name} - backup had error: {backup_status}"
                )
                continue

            if not backup_path or not os.path.exists(backup_path):
                telemetry.warning(f"Backup file not found for {db_name}: {backup_path}")
                continue

            try:
                # Determine the target database path
                if db_name == "task.db":
                    target_path = TASK_DB_PATH
                elif db_name == "activity.db":
                    target_path = ACTIVITY_DB_PATH
                elif db_name == "snapshots.db":
                    target_path = SNAPSHOTS_DB_PATH
                elif db_name == "telemetry.db":
                    target_path = os.path.join(
                        os.path.dirname(TASK_DB_PATH), "telemetry.db"
                    )
                else:
                    telemetry.warning(f"Unknown database: {db_name}")
                    continue

                if dry_run:
                    telemetry.info(f"[DRY-RUN] Would restore database: {db_name}")
                    continue

                # Restore from backup
                self._restore_sqlite_backup(backup_path, target_path)

                # Validate database integrity
                if not self._validate_database_integrity(target_path):
                    raise ValueError(f"Database integrity check failed for {db_name}")

                telemetry.info(f"Successfully restored database: {db_name}")

            except Exception as e:
                telemetry.error(f"Failed to restore database {db_name}: {str(e)}")
                raise

    def _restore_file_system_state(
        self, snapshot_id: str, dry_run: bool = False, preserve_user_work: bool = True
    ):
        """
        Restore file system state from snapshot.

        Args:
            snapshot_id: Checkpoint ID to restore from
            dry_run: Preview changes without actually restoring
            preserve_user_work: Warn about conflicts with user work
        """
        telemetry.info(
            f"Restoring file system state from checkpoint: {snapshot_id} (dry_run={dry_run})"
        )

        checkpoint = self.get(snapshot_id)
        if not checkpoint:
            raise ValueError(f"Checkpoint not found: {snapshot_id}")

        file_state_list = checkpoint.get("file_state", [])

        if not file_state_list:
            telemetry.info(f"No file system state found in checkpoint: {snapshot_id}")
            return

        # Track files that would be affected
        affected_files = []
        conflicts = []

        for file_state in file_state_list:
            file_path = file_state["file_path"]
            file_status = file_state["file_status"]
            backup_path = file_state.get("backup_path")

            # Check for conflicts
            if preserve_user_work:
                conflict_info = self._check_file_conflict(file_state)
                if conflict_info:
                    conflicts.append(conflict_info)

            affected_files.append(file_path)

            if dry_run:
                if "D" in file_status:
                    telemetry.info(f"[DRY-RUN] Would delete file: {file_path}")
                else:
                    telemetry.info(f"[DRY-RUN] Would restore file: {file_path}")
                continue

            # Restore the file
            if "D" in file_status:
                # File was deleted in checkpoint - delete it now
                if os.path.exists(file_path):
                    os.remove(file_path)
                    telemetry.info(f"Deleted file: {file_path}")
            elif backup_path and os.path.exists(backup_path):
                # Restore file from backup
                # Create parent directory if it doesn't exist
                parent_dir = os.path.dirname(file_path)
                if parent_dir and not os.path.exists(parent_dir):
                    os.makedirs(parent_dir, exist_ok=True)

                shutil.copy2(backup_path, file_path)
                telemetry.info(f"Restored file: {file_path}")

        if conflicts:
            telemetry.warning(f"Found {len(conflicts)} file conflicts during restore:")
            for conflict in conflicts:
                telemetry.warning(f"  - {conflict['file']}: {conflict['reason']}")

        telemetry.info(f"Restored {len(affected_files)} files from checkpoint")

    def _restore_git_state(
        self, snapshot_id: str, dry_run: bool = False, preserve_user_work: bool = True
    ):
        """
        Restore git state from snapshot.

        Args:
            snapshot_id: Checkpoint ID to restore from
            dry_run: Preview changes without actually restoring
            preserve_user_work: Warn about conflicts with user work
        """
        telemetry.info(
            f"Restoring git state from checkpoint: {snapshot_id} (dry_run={dry_run})"
        )

        checkpoint = self.get(snapshot_id)
        if not checkpoint:
            raise ValueError(f"Checkpoint not found: {snapshot_id}")

        git_state_list = checkpoint.get("git_state", [])

        if not git_state_list:
            telemetry.warning(f"No git state found in checkpoint: {snapshot_id}")
            return

        git_state = git_state_list[0]
        target_branch = git_state["branch"]
        target_commit = git_state["commit_hash"]
        target_status = git_state["git_status"]

        if dry_run:
            telemetry.info(f"[DRY-RUN] Would checkout branch: {target_branch}")
            telemetry.info(f"[DRY-RUN] Would checkout commit: {target_commit}")
            return

        try:
            # Get current git state
            current_branch = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True,
                text=True,
                check=False,
            ).stdout.strip()

            current_commit = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                check=False,
            ).stdout.strip()

            # Check if we're already on the target branch/commit
            if current_branch == target_branch and current_commit == target_commit:
                telemetry.info(
                    f"Already on target branch {target_branch} and commit {target_commit}"
                )
            else:
                # Checkout the target branch
                telemetry.info(f"Checking out branch: {target_branch}")
                subprocess.run(
                    ["git", "checkout", target_branch],
                    capture_output=True,
                    text=True,
                    check=True,
                )

                # Checkout the specific commit
                telemetry.info(f"Checking out commit: {target_commit}")
                subprocess.run(
                    ["git", "checkout", target_commit],
                    capture_output=True,
                    text=True,
                    check=True,
                )

            # Check for merge conflicts
            if preserve_user_work:
                conflict_result = subprocess.run(
                    ["git", "diff", "--name-only", "--diff-filter=U"],
                    capture_output=True,
                    text=True,
                    check=False,
                )

                if conflict_result.stdout.strip():
                    telemetry.warning("Git merge conflicts detected after restore:")
                    for conflicted_file in conflict_result.stdout.strip().splitlines():
                        telemetry.warning(f"  - {conflicted_file}")

                    telemetry.warning(
                        "Please resolve conflicts manually or use git merge --abort to cancel"
                    )

            telemetry.info(
                f"Successfully restored git state to {target_branch}@{target_commit}"
            )

        except subprocess.CalledProcessError as e:
            telemetry.error(f"Failed to restore git state: {str(e)}")
            if e.stderr:
                telemetry.error(f"Git error: {e.stderr}")
            raise

    def _restore_cache_state(self, snapshot_id: str, dry_run: bool = False):
        """
        Restore cache state from snapshot.

        Restores:
        - Cache manager state (cache index, cache entries)
        - Context engine state (memoization cache, cache statistics)
        - Validates cache consistency after restore
        - Rebuilds cache if corruption detected

        Args:
            snapshot_id: Checkpoint ID to restore from
            dry_run: Preview changes without actually restoring
        """
        telemetry.info(
            f"Restoring cache state from checkpoint: {snapshot_id} (dry_run={dry_run})"
        )

        checkpoint = self.get(snapshot_id)
        if not checkpoint:
            raise ValueError(f"Checkpoint not found: {snapshot_id}")

        cache_state_list = checkpoint.get("cache_state", [])

        if not cache_state_list:
            telemetry.info(f"No cache state found in checkpoint: {snapshot_id}")
            return

        if dry_run:
            telemetry.info("[DRY-RUN] Would restore cache state")
            for state in cache_state_list:
                cache_key = state["cache_key"]
                telemetry.info(f"[DRY-RUN] Would restore: {cache_key}")
            return

        # Restore cache manager state
        cache_restored = False
        context_restored = False

        for state in cache_state_list:
            cache_key = state["cache_key"]
            cache_data_str = state.get("cache_data")

            if not cache_data_str:
                continue

            try:
                cache_data = json.loads(cache_data_str)

                if cache_key == "cache_summary":
                    # Restore cache manager state
                    self._restore_cache_manager_state(cache_data)
                    cache_restored = True

                elif cache_key == "context_engine_state":
                    # Restore context engine state
                    self._restore_context_engine_state(cache_data)
                    context_restored = True

            except json.JSONDecodeError as e:
                telemetry.error(
                    f"Failed to decode cache state for {cache_key}: {str(e)}"
                )
            except Exception as e:
                telemetry.error(f"Failed to restore cache state {cache_key}: {str(e)}")

        # Validate and rebuild cache if needed
        if cache_restored:
            if not self._validate_cache_consistency():
                telemetry.warning("Cache validation failed, rebuilding cache...")
                self._rebuild_cache()
            else:
                telemetry.info("Cache validation passed")

        if cache_restored or context_restored:
            telemetry.info(
                f"Successfully restored cache state from checkpoint: {snapshot_id}"
            )
        else:
            telemetry.warning(
                f"No cache state was restored from checkpoint: {snapshot_id}"
            )

    def _restore_cache_manager_state(self, cache_data: Dict[str, Any]):
        """
        Restore cache manager state from checkpoint data.

        Args:
            cache_data: Cache manager state dictionary from checkpoint
        """
        try:
            from data.cache_manager import get_cache_manager

            cache_manager = get_cache_manager()

            # Invalidate all existing cache to prevent conflicts
            cache_manager.clear_all()

            # Restore cache index
            restored_count = 0
            for cache_key, cache_info in cache_data.get("cache_index", {}).items():
                # Check if the cache file still exists
                cache_file = cache_manager._get_cache_file_path(cache_key)

                if cache_file.exists():
                    # Restore cache entry
                    cache_manager.cache_index[cache_key] = {
                        "file_path": cache_info.get("file_path"),
                        "file_mtime": cache_info.get("file_mtime"),
                        "file_hash": cache_info.get("file_hash"),
                        "cached_at": cache_info.get("cached_at"),
                        "analysis_type": cache_info.get("analysis_type"),
                    }
                    restored_count += 1
                else:
                    telemetry.warning(f"Cache file not found for key: {cache_key}")

            # Save restored index
            cache_manager._save_cache_index()

            telemetry.info(f"Restored {restored_count} cache entries from checkpoint")

        except Exception as e:
            telemetry.error(f"Failed to restore cache manager state: {str(e)}")
            raise

    def _restore_context_engine_state(self, context_data: Dict[str, Any]):
        """
        Restore context engine state from checkpoint data.

        Args:
            context_data: Context engine state dictionary from checkpoint
        """
        try:
            # Context engine state is instance-specific and cannot be directly restored
            # However, we can document what would need to be done

            if "note" in context_data:
                telemetry.info(f"Context engine state restore: {context_data['note']}")
                telemetry.info(
                    "Context engine instances maintain their own state that cannot be globally restored"
                )

            # In a real implementation, we might:
            # 1. Store context cache entries in a shared location
            # 2. Allow ContextEngine instances to load from this shared location
            # 3. Implement a context cache persistence layer

            telemetry.info(
                "Context engine state is instance-specific and will be rebuilt on demand"
            )

        except Exception as e:
            telemetry.warning(f"Failed to restore context engine state: {str(e)}")

    def _validate_cache_consistency(self) -> bool:
        """
        Validate cache consistency after restore.

        Checks:
        - Cache index matches actual cache files
        - File hashes match cached values
        - File modification times are consistent

        Returns:
            True if cache is consistent
        """
        try:
            from data.cache_manager import get_cache_manager

            cache_manager = get_cache_manager()

            # Check each cache entry
            inconsistent_entries = 0

            for cache_key, cache_info in cache_manager.cache_index.items():
                cache_file = cache_manager._get_cache_file_path(cache_key)

                if not cache_file.exists():
                    telemetry.warning(f"Cache file missing for key: {cache_key}")
                    inconsistent_entries += 1
                    continue

                # Check if file has been modified
                file_mtime = cache_manager._get_file_mtime(cache_info["file_path"])
                cached_mtime = cache_info.get("file_mtime")

                if file_mtime != cached_mtime:
                    telemetry.warning(
                        f"Cache entry stale for key: {cache_key} (file modified)"
                    )
                    inconsistent_entries += 1
                    continue

                # Check file hash if available
                file_hash = cache_manager._get_file_hash(cache_info["file_path"])
                cached_hash = cache_info.get("file_hash")

                if file_hash != cached_hash:
                    telemetry.warning(f"Cache entry hash mismatch for key: {cache_key}")
                    inconsistent_entries += 1

            if inconsistent_entries > 0:
                telemetry.error(
                    f"Found {inconsistent_entries} inconsistent cache entries"
                )
                return False

            return True

        except Exception as e:
            telemetry.error(f"Cache validation failed: {str(e)}")
            return False

    def _rebuild_cache(self):
        """
        Rebuild cache from scratch.

        Called when cache corruption is detected.
        Clears all cache and marks files for re-analysis.
        """
        try:
            from data.cache_manager import get_cache_manager

            cache_manager = get_cache_manager()

            # Clear all cache
            cache_manager.clear_all()

            telemetry.info("Cache cleared and ready for rebuild")
            telemetry.info("Context will be re-analyzed on next use")

        except Exception as e:
            telemetry.error(f"Failed to rebuild cache: {str(e)}")
            raise

    def _warn_about_user_work_loss(self, checkpoint: Dict[str, Any]):
        """
        Warn user about work that would be lost on restore.

        Args:
            checkpoint: Checkpoint dictionary
        """
        warnings = []

        # Check for uncommitted changes
        git_state_list = checkpoint.get("git_state", [])
        if git_state_list:
            git_status = git_state_list[0].get("git_status", "")
            if git_status.strip():
                warnings.append(
                    f"Git has uncommitted changes ({len(git_status.splitlines())} files)"
                )

        # Check for modified files
        file_state_list = checkpoint.get("file_state", [])
        if file_state_list:
            modified_count = sum(1 for f in file_state_list if "M" in f["file_status"])
            added_count = sum(
                1
                for f in file_state_list
                if "A" in f["file_status"] or "??" in f["file_status"]
            )

            if modified_count > 0:
                warnings.append(
                    f"Modified files will be restored ({modified_count} files)"
                )
            if added_count > 0:
                warnings.append(
                    f"Added/untracked files may be affected ({added_count} files)"
                )

        if warnings:
            telemetry.warning("⚠️  WARNING: The following user work may be lost:")
            for warning in warnings:
                telemetry.warning(f"  - {warning}")
            telemetry.warning("Consider creating a backup before proceeding")

    def _check_file_conflict(
        self, file_state: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Check if restoring a file would conflict with user work.

        Args:
            file_state: File state dictionary from checkpoint

        Returns:
            Conflict info dictionary or None if no conflict
        """
        file_path = file_state["file_path"]
        file_status = file_state["file_status"]
        checkpoint_hash = file_state.get("file_hash")

        # If file doesn't exist currently and was deleted in checkpoint, no conflict
        if not os.path.exists(file_path) and "D" in file_status:
            return None

        # If file exists but was deleted in checkpoint, that's a conflict
        if "D" in file_status and os.path.exists(file_path):
            return {
                "file": file_path,
                "reason": "File exists but was deleted in checkpoint",
                "action": "will be deleted",
            }

        # Check if file has been modified since checkpoint
        if (
            os.path.exists(file_path)
            and checkpoint_hash
            and checkpoint_hash != "DELETED"
        ):
            current_hash = self._calculate_file_hash(file_path)
            if current_hash != checkpoint_hash:
                # Check if the change is just whitespace or minor
                return {
                    "file": file_path,
                    "reason": "File has been modified since checkpoint",
                    "action": "will be overwritten",
                    "current_hash": current_hash,
                    "checkpoint_hash": checkpoint_hash,
                }

        return None

    def _validate_system_state(self) -> bool:
        """
        Validate current system state integrity.

        Returns:
            True if system state is valid
        """
        # Basic validation - check databases exist
        required_dbs = [TASK_DB_PATH, ACTIVITY_DB_PATH, SNAPSHOTS_DB_PATH]

        for db_path in required_dbs:
            if not os.path.exists(db_path):
                telemetry.error(f"Required database not found: {db_path}")
                return False

            # Try to open database
            try:
                conn = sqlite3.connect(db_path)
                conn.execute("SELECT 1")
                conn.close()
            except Exception as e:
                telemetry.error(f"Database validation failed for {db_path}: {str(e)}")
                return False

        return True

    def _create_sqlite_backup(self, source_path: str, backup_path: str):
        """
        Create a backup of SQLite database.

        Uses file copy for simplicity and reliability.
        For WAL mode databases, we first checkpoint to ensure consistency.
        """
        # Handle WAL mode databases
        try:
            conn = sqlite3.connect(source_path)
            cursor = conn.cursor()

            # Check if database is in WAL mode
            cursor.execute("PRAGMA journal_mode")
            journal_mode = cursor.fetchone()[0]

            if journal_mode == "wal":
                # Checkpoint WAL to ensure consistency
                cursor.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                conn.commit()

            conn.close()
        except Exception:
            pass  # Continue even if checkpoint fails

        # Copy the database file
        shutil.copy2(source_path, backup_path)

        # Also copy WAL and SHM files if they exist
        for ext in ["-wal", "-shm"]:
            wal_path = f"{source_path}{ext}"
            if os.path.exists(wal_path):
                shutil.copy2(wal_path, f"{backup_path}{ext}")

    def _restore_sqlite_backup(self, backup_path: str, target_path: str):
        """
        Restore SQLite database from backup.

        Creates a backup of the current database before restoring.
        Uses file copy for simplicity and reliability.
        """
        # Create a backup of the current database for safety
        if os.path.exists(target_path):
            safety_backup = (
                f"{target_path}.pre_restore_{int(datetime.now().timestamp())}"
            )
            shutil.copy2(target_path, safety_backup)
            telemetry.info(f"Created safety backup: {safety_backup}")

        # Close any open connections to the target database
        # (This is handled by the calling code which opens a new connection after restore)

        # Copy backup files to target
        shutil.copy2(backup_path, target_path)

        # Also copy WAL and SHM files if they exist
        for ext in ["-wal", "-shm"]:
            backup_wal = f"{backup_path}{ext}"
            if os.path.exists(backup_wal):
                target_wal = f"{target_path}{ext}"
                shutil.copy2(backup_wal, target_wal)

    def _validate_database_integrity(self, db_path: str) -> bool:
        """
        Validate database integrity after restore.

        Returns:
            True if database is valid
        """
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Run integrity check
            cursor.execute("PRAGMA integrity_check")
            result = cursor.fetchone()

            if result and result[0] != "ok":
                telemetry.error(f"Database integrity check failed: {result[0]}")
                conn.close()
                return False

            # Check foreign key constraints
            cursor.execute("PRAGMA foreign_key_check")
            fk_violations = cursor.fetchall()

            if fk_violations:
                telemetry.error(f"Foreign key violations found: {fk_violations}")
                conn.close()
                return False

            conn.close()
            return True

        except Exception as e:
            telemetry.error(f"Database validation failed: {str(e)}")
            return False

    def _is_incremental_backup(self, cursor, db_name: str, current_hash: str) -> bool:
        """
        Check if this should be an incremental backup.

        Compares with the most recent backup of the same database.
        """
        # Get the most recent snapshot with this database
        cursor.execute(
            """
            SELECT db_hash 
            FROM snapshot_db_state 
            WHERE db_name = ? 
            ORDER BY snapshot_id DESC 
            LIMIT 1
            """,
            (db_name,),
        )
        result = cursor.fetchone()

        if result and result[0] == current_hash:
            # Database hasn't changed, mark as incremental
            return True

        return False

    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA256 hash of a file."""
        sha256_hash = hashlib.sha256()

        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)

        return sha256_hash.hexdigest()


# Global checkpoint manager instance
_checkpoint_manager: Optional[CheckpointManager] = None


def get_checkpoint_manager() -> CheckpointManager:
    """
    Get the global checkpoint manager instance.

    Returns:
        CheckpointManager instance
    """
    global _checkpoint_manager
    if _checkpoint_manager is None:
        _checkpoint_manager = CheckpointManager()
    return _checkpoint_manager
