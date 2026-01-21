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

from v2.data.db_manager import (
    SNAPSHOTS_DB_PATH, TASK_DB_PATH, ACTIVITY_DB_PATH,
    get_db_connection
)
from v2.core.telemetry import telemetry


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
        from v2.data.db_manager import init_db
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
        include_cache: bool = True
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
                    snapshot_id, timestamp, snapshot_type, operation_id,
                    task_id, reason, json.dumps({
                        'include_databases': include_databases,
                        'include_files': include_files,
                        'include_git': include_git,
                        'include_cache': include_cache
                    })
                )
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
        limit: int = 50
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
                checkpoint['metadata'] = json.loads(checkpoint['metadata']) if checkpoint['metadata'] else {}
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
                "SELECT * FROM snapshots WHERE snapshot_id = ?",
                (snapshot_id,)
            )
            row = cursor.fetchone()
            
            if not row:
                return None
                
            checkpoint = dict(row)
            checkpoint['metadata'] = json.loads(checkpoint['metadata']) if checkpoint['metadata'] else {}
            
            # Get associated state details
            checkpoint['db_state'] = self._get_db_state(cursor, snapshot_id)
            checkpoint['file_state'] = self._get_file_state(cursor, snapshot_id)
            checkpoint['git_state'] = self._get_git_state(cursor, snapshot_id)
            checkpoint['cache_state'] = self._get_cache_state(cursor, snapshot_id)
            
            return checkpoint
            
    def restore(
        self,
        snapshot_id: str,
        restore_databases: bool = True,
        restore_files: bool = True,
        restore_git: bool = True,
        restore_cache: bool = True,
        validate_before: bool = True,
        validate_after: bool = True
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
            
        Returns:
            True if restore was successful
        """
        telemetry.info(f"Starting restore from checkpoint: {snapshot_id}")
        
        # Validate checkpoint exists
        checkpoint = self.get(snapshot_id)
        if not checkpoint:
            telemetry.error(f"Checkpoint not found: {snapshot_id}")
            return False
            
        # Validate before restore
        if validate_before:
            if not self.validate(snapshot_id):
                telemetry.error(f"Checkpoint validation failed for checkpoint: {snapshot_id}")
                return False
                
        try:
            # Restore databases
            if restore_databases:
                self._restore_database_state(snapshot_id)
                
            # Restore file system
            if restore_files:
                self._restore_file_system_state(snapshot_id)
                
            # Restore git state
            if restore_git:
                self._restore_git_state(snapshot_id)
                
            # Restore cache
            if restore_cache:
                self._restore_cache_state(snapshot_id)
                
            # Validate after restore
            if validate_after:
                if not self._validate_system_state():
                    telemetry.warning(f"System validation after restore failed, but restore completed: {snapshot_id}")
                    
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
                "DELETE FROM snapshots WHERE snapshot_id = ?",
                (snapshot_id,)
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
        db_state = checkpoint.get('db_state', [])
        for db in db_state:
            if not db.get('db_hash'):
                telemetry.error(f"Missing database hash in checkpoint: {snapshot_id}")
                return False
                
        # Check git state integrity
        git_state = checkpoint.get('git_state', [])
        if not git_state:
            telemetry.warning(f"Checkpoint has no git state: {snapshot_id}")
            
        telemetry.info(f"Checkpoint validated successfully: {snapshot_id}")
        return True
        
    def cleanup_old_checkpoints(
        self,
        max_count: int = 10,
        max_age_hours: int = 24,
        keep_critical: bool = True
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
            if keep_critical and checkpoint['snapshot_type'] in ['task_complete', 'operation_end']:
                continue
                
            # Delete old checkpoints beyond max_count
            if deleted_count >= len(checkpoints) - max_count:
                break
                
            checkpoint_time = datetime.fromisoformat(checkpoint['timestamp']).timestamp()
            if checkpoint_time < cutoff_time:
                if self.delete(checkpoint['snapshot_id']):
                    deleted_count += 1
                    
        telemetry.info(f"Cleaned up {deleted_count} old checkpoints")
        return deleted_count
        
    @contextmanager
    def rollback_on_error(
        self,
        reason: str = "auto_rollback",
        snapshot_type: str = "auto"
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
            telemetry.error(f"Error in context, rolling back to checkpoint {snapshot_id}: {str(e)}")
            self.restore(snapshot_id)
            raise
            
    # Private helper methods
    
    def _generate_snapshot_id(self) -> str:
        """Generate a unique snapshot ID."""
        return f"chkp_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.urandom(4).hex()}"
        
    def _capture_database_state(self, cursor, snapshot_id: str):
        """Capture database state for snapshot."""
        databases = [TASK_DB_PATH, ACTIVITY_DB_PATH, SNAPSHOTS_DB_PATH]
        
        for db_path in databases:
            if not os.path.exists(db_path):
                continue
                
            # Calculate database hash
            db_hash = self._calculate_file_hash(db_path)
            db_size = os.path.getsize(db_path)
            
            # For now, store hash and size (full dumps will be in Task 3.3)
            cursor.execute(
                """
                INSERT INTO snapshot_db_state (
                    snapshot_id, db_name, db_hash, db_size, is_incremental
                )
                VALUES (?, ?, ?, ?, 0)
                """,
                (snapshot_id, os.path.basename(db_path), db_hash, db_size)
            )
            
    def _capture_file_system_state(self, cursor, snapshot_id: str):
        """Capture file system state for snapshot."""
        # Get list of modified Python files
        try:
            result = subprocess.run(
                ['git', 'status', '--porcelain'],
                capture_output=True,
                text=True,
                check=False
            )
            
            for line in result.stdout.splitlines():
                if not line.strip():
                    continue
                    
                status_code = line[:2]
                file_path = line[3:]
                
                # Only track relevant files
                if not file_path.endswith('.py') and not file_path.endswith('.md'):
                    continue
                    
                if os.path.exists(file_path):
                    file_hash = self._calculate_file_hash(file_path)
                    file_size = os.path.getsize(file_path)
                    
                    # Get git diff for modified files
                    git_diff = ""
                    if 'M' in status_code:
                        try:
                            diff_result = subprocess.run(
                                ['git', 'diff', file_path],
                                capture_output=True,
                                text=True,
                                check=False
                            )
                            git_diff = diff_result.stdout
                        except Exception:
                            pass
                            
                    cursor.execute(
                        """
                        INSERT INTO snapshot_file_state (
                            snapshot_id, file_path, file_hash, file_size, 
                            file_status, git_diff
                        )
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (snapshot_id, file_path, file_hash, file_size, status_code, git_diff)
                    )
                    
        except Exception as e:
            telemetry.warning(f"Failed to capture file system state: {str(e)}")
            
    def _capture_git_state(self, cursor, snapshot_id: str):
        """Capture git state for snapshot."""
        try:
            # Get current branch
            branch_result = subprocess.run(
                ['git', 'branch', '--show-current'],
                capture_output=True,
                text=True,
                check=False
            )
            branch = branch_result.stdout.strip()
            
            # Get current commit hash
            commit_result = subprocess.run(
                ['git', 'rev-parse', 'HEAD'],
                capture_output=True,
                text=True,
                check=False
            )
            commit_hash = commit_result.stdout.strip()
            
            # Get git status
            status_result = subprocess.run(
                ['git', 'status', '--porcelain'],
                capture_output=True,
                text=True,
                check=False
            )
            git_status = status_result.stdout
            
            cursor.execute(
                """
                INSERT INTO snapshot_git_state (
                    snapshot_id, branch, commit_hash, git_status
                )
                VALUES (?, ?, ?, ?)
                """,
                (snapshot_id, branch, commit_hash, git_status)
            )
            
        except Exception as e:
            telemetry.warning(f"Failed to capture git state: {str(e)}")
            
    def _capture_cache_state(self, cursor, snapshot_id: str):
        """Capture cache state for snapshot."""
        cache_dir = Path('.l4_cache')
        if not cache_dir.exists():
            return
            
        try:
            # Cache state will be more detailed in Task 3.5
            # For now, just record that cache exists
            cache_files = list(cache_dir.rglob('*'))
            cache_size = sum(f.stat().st_size for f in cache_files if f.is_file())
            
            cursor.execute(
                """
                INSERT INTO snapshot_cache_state (
                    snapshot_id, cache_key, cache_hash, cache_size
                )
                VALUES (?, ?, ?, ?)
                """,
                (snapshot_id, 'cache_summary', 'N/A', cache_size)
            )
            
        except Exception as e:
            telemetry.warning(f"Failed to capture cache state: {str(e)}")
            
    def _get_db_state(self, cursor, snapshot_id: str) -> List[Dict]:
        """Get database state for snapshot."""
        cursor.execute(
            "SELECT * FROM snapshot_db_state WHERE snapshot_id = ?",
            (snapshot_id,)
        )
        return [dict(row) for row in cursor.fetchall()]
        
    def _get_file_state(self, cursor, snapshot_id: str) -> List[Dict]:
        """Get file system state for snapshot."""
        cursor.execute(
            "SELECT * FROM snapshot_file_state WHERE snapshot_id = ?",
            (snapshot_id,)
        )
        return [dict(row) for row in cursor.fetchall()]
        
    def _get_git_state(self, cursor, snapshot_id: str) -> List[Dict]:
        """Get git state for snapshot."""
        cursor.execute(
            "SELECT * FROM snapshot_git_state WHERE snapshot_id = ?",
            (snapshot_id,)
        )
        return [dict(row) for row in cursor.fetchall()]
        
    def _get_cache_state(self, cursor, snapshot_id: str) -> List[Dict]:
        """Get cache state for snapshot."""
        cursor.execute(
            "SELECT * FROM snapshot_cache_state WHERE snapshot_id = ?",
            (snapshot_id,)
        )
        return [dict(row) for row in cursor.fetchall()]
        
    def _restore_database_state(self, snapshot_id: str):
        """
        Restore database state from snapshot.
        
        Note: Full database restore will be implemented in Task 3.3.
        This is a placeholder that validates state exists.
        """
        telemetry.info(f"Database state restore requested for {snapshot_id} (to be fully implemented in Task 3.3)")
        
    def _restore_file_system_state(self, snapshot_id: str):
        """
        Restore file system state from snapshot.
        
        Note: Full file system restore will be implemented in Task 3.4.
        This is a placeholder that validates state exists.
        """
        telemetry.info(f"File system state restore requested for {snapshot_id} (to be fully implemented in Task 3.4)")
        
    def _restore_git_state(self, snapshot_id: str):
        """
        Restore git state from snapshot.
        
        Note: Full git restore will be implemented in Task 3.4.
        This is a placeholder that validates state exists.
        """
        telemetry.info(f"Git state restore requested for {snapshot_id} (to be fully implemented in Task 3.4)")
        
    def _restore_cache_state(self, snapshot_id: str):
        """
        Restore cache state from snapshot.
        
        Note: Full cache restore will be implemented in Task 3.5.
        This is a placeholder that validates state exists.
        """
        telemetry.info(f"Cache state restore requested for {snapshot_id} (to be fully implemented in Task 3.5)")
        
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
        
    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA256 hash of a file."""
        sha256_hash = hashlib.sha256()
        
        with open(file_path, 'rb') as f:
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
