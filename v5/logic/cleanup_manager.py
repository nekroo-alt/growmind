"""
Cleanup Manager Module (V5)

Implements automatic cleanup of old checkpoints, logs, and telemetry data.
Provides policy-based cleanup with configurable rules and comprehensive reporting.
"""

import os
import shutil
import sqlite3
import json
import gzip
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class CleanupPolicy:
    """Defines cleanup policies for different data types."""
    
    # Checkpoint policy
    checkpoint_max_age_hours: int = 24
    checkpoint_max_count: int = 10
    checkpoint_keep_critical: bool = True
    
    # Log policy
    log_max_size_mb: int = 10
    log_backup_count: int = 5
    log_max_age_days: int = 7
    
    # Telemetry policy
    telemetry_archive_age_days: int = 30
    telemetry_delete_age_days: int = 90
    
    # Session policy
    session_max_sessions: int = 10
    session_max_age_days: int = 30
    
    # Cache policy
    cache_max_age_days: int = 7
    cache_max_size_mb: int = 100
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert policy to dictionary."""
        return {
            'checkpoint_max_age_hours': self.checkpoint_max_age_hours,
            'checkpoint_max_count': self.checkpoint_max_count,
            'checkpoint_keep_critical': self.checkpoint_keep_critical,
            'log_max_size_mb': self.log_max_size_mb,
            'log_backup_count': self.log_backup_count,
            'log_max_age_days': self.log_max_age_days,
            'telemetry_archive_age_days': self.telemetry_archive_age_days,
            'telemetry_delete_age_days': self.telemetry_delete_age_days,
            'session_max_sessions': self.session_max_sessions,
            'session_max_age_days': self.session_max_age_days,
            'cache_max_age_days': self.cache_max_age_days,
            'cache_max_size_mb': self.cache_max_size_mb
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CleanupPolicy':
        """Create policy from dictionary."""
        return cls(**data)


@dataclass
class CleanupResult:
    """Represents result of a cleanup operation."""
    
    category: str  # 'checkpoints', 'logs', 'telemetry', 'sessions', 'cache'
    deleted_items: int = 0
    archived_items: int = 0
    rotated_items: int = 0
    freed_space_bytes: int = 0
    errors: List[str] = field(default_factory=list)
    details: List[str] = field(default_factory=list)
    
    def add_error(self, error: str):
        """Add an error to the result."""
        self.errors.append(error)
        logger.error(f"{self.category}: {error}")
    
    def add_detail(self, detail: str):
        """Add a detail to the result."""
        self.details.append(detail)
        logger.info(f"{self.category}: {detail}")
    
    @property
    def freed_space_mb(self) -> float:
        """Get freed space in MB."""
        return self.freed_space_bytes / (1024 * 1024)


class CleanupManager:
    """
    Manages automatic cleanup of old checkpoints, logs, and telemetry.
    
    Implements policy-based cleanup with configurable rules for different data types.
    Provides comprehensive reporting and dry-run support.
    """
    
    def __init__(self, 
                 checkpoint_dir: str = 'checkpoints',
                 log_dir: str = 'logs',
                 telemetry_db: str = 'telemetry.db',
                 sessions_db: str = 'sessions.db',
                 cache_dir: str = '.l4_cache',
                 policy: Optional[CleanupPolicy] = None):
        """
        Initialize cleanup manager.
        
        Args:
            checkpoint_dir: Directory containing checkpoints
            log_dir: Directory containing log files
            telemetry_db: Path to telemetry database
            sessions_db: Path to sessions database
            cache_dir: Directory containing cache
            policy: Cleanup policy (uses default if not provided)
        """
        self.checkpoint_dir = Path(checkpoint_dir)
        self.log_dir = Path(log_dir)
        self.telemetry_db = Path(telemetry_db)
        self.sessions_db = Path(sessions_db)
        self.cache_dir = Path(cache_dir)
        self.policy = policy or CleanupPolicy()
        
        self.results: List[CleanupResult] = []
    
    def cleanup_all(self, dry_run: bool = False) -> Dict[str, Any]:
        """
        Run all cleanup operations.
        
        Args:
            dry_run: If True, preview cleanup without actually deleting
            
        Returns:
            Dictionary with cleanup summary
        """
        logger.info("Starting cleanup operations" + (" (dry run)" if dry_run else ""))
        self.results = []
        
        # Run all cleanup operations
        self.cleanup_checkpoints(dry_run=dry_run)
        self.cleanup_logs(dry_run=dry_run)
        self.cleanup_telemetry(dry_run=dry_run)
        self.cleanup_sessions(dry_run=dry_run)
        self.cleanup_cache(dry_run=dry_run)
        
        return self.generate_report()
    
    def cleanup_checkpoints(self, dry_run: bool = False) -> CleanupResult:
        """
        Clean up old checkpoints based on age and count limits.
        
        Args:
            dry_run: If True, preview cleanup without actually deleting
            
        Returns:
            CleanupResult with details of checkpoint cleanup
        """
        result = CleanupResult(category='checkpoints')
        logger.info(f"Cleaning up checkpoints in {self.checkpoint_dir}")
        
        if not self.checkpoint_dir.exists():
            result.add_detail("Checkpoint directory does not exist")
            return result
        
        # Get all checkpoint directories
        checkpoint_dirs = [d for d in self.checkpoint_dir.iterdir() 
                          if d.is_dir() and d.name.startswith('chkp_')]
        
        if not checkpoint_dirs:
            result.add_detail("No checkpoints found")
            return result
        
        # Sort by modification time (oldest first)
        checkpoint_dirs.sort(key=lambda d: d.stat().st_mtime)
        
        # Check age-based cleanup
        cutoff_time = datetime.now() - timedelta(hours=self.policy.checkpoint_max_age_hours)
        
        for checkpoint_dir in checkpoint_dirs:
            mtime = datetime.fromtimestamp(checkpoint_dir.stat().st_mtime)
            
            # Check if checkpoint is too old
            if mtime < cutoff_time:
                # Check if it's critical (has recent changes)
                if not self._is_critical_checkpoint(checkpoint_dir):
                    size = self._get_dir_size(checkpoint_dir)
                    result.details.append(f"Old checkpoint: {checkpoint_dir.name} "
                                       f"(age: {(datetime.now() - mtime).total_seconds()/3600:.1f}h)")
                    
                    if not dry_run:
                        try:
                            shutil.rmtree(checkpoint_dir)
                            result.deleted_items += 1
                            result.freed_space_bytes += size
                            result.add_detail(f"Deleted: {checkpoint_dir.name}")
                        except Exception as e:
                            result.add_error(f"Failed to delete {checkpoint_dir.name}: {e}")
                    else:
                        result.deleted_items += 1
                        result.freed_space_bytes += size
                        result.add_detail(f"[DRY RUN] Would delete: {checkpoint_dir.name}")
        
        # Check count-based cleanup
        max_keep = self.policy.checkpoint_max_count
        if len(checkpoint_dirs) > max_keep:
            # Keep the most recent ones
            to_delete = checkpoint_dirs[:-max_keep]
            
            for checkpoint_dir in to_delete:
                # Skip if already deleted by age check
                if not checkpoint_dir.exists():
                    continue
                
                # Check if critical
                if not self._is_critical_checkpoint(checkpoint_dir):
                    size = self._get_dir_size(checkpoint_dir)
                    result.details.append(f"Excess checkpoint: {checkpoint_dir.name}")
                    
                    if not dry_run:
                        try:
                            shutil.rmtree(checkpoint_dir)
                            result.deleted_items += 1
                            result.freed_space_bytes += size
                            result.add_detail(f"Deleted: {checkpoint_dir.name}")
                        except Exception as e:
                            result.add_error(f"Failed to delete {checkpoint_dir.name}: {e}")
                    else:
                        result.deleted_items += 1
                        result.freed_space_bytes += size
                        result.add_detail(f"[DRY RUN] Would delete: {checkpoint_dir.name}")
        
        result.add_detail(f"Cleanup complete: {result.deleted_items} deleted, "
                         f"{result.freed_space_mb:.2f} MB freed")
        self.results.append(result)
        return result
    
    def cleanup_logs(self, dry_run: bool = False) -> CleanupResult:
        """
        Rotate and clean up log files based on size and age.
        
        Args:
            dry_run: If True, preview cleanup without actually deleting
            
        Returns:
            CleanupResult with details of log cleanup
        """
        result = CleanupResult(category='logs')
        logger.info(f"Cleaning up logs in {self.log_dir}")
        
        if not self.log_dir.exists():
            result.add_detail("Log directory does not exist")
            return result
        
        # Get all log files
        log_files = list(self.log_dir.glob('*.log')) + list(self.log_dir.glob('*.log.*'))
        
        if not log_files:
            result.add_detail("No log files found")
            return result
        
        cutoff_time = datetime.now() - timedelta(days=self.policy.log_max_age_days)
        
        for log_file in log_files:
            # Check age
            mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
            
            if mtime < cutoff_time:
                size = log_file.stat().st_size
                result.details.append(f"Old log file: {log_file.name}")
                
                if not dry_run:
                    try:
                        log_file.unlink()
                        result.deleted_items += 1
                        result.freed_space_bytes += size
                        result.add_detail(f"Deleted: {log_file.name}")
                    except Exception as e:
                        result.add_error(f"Failed to delete {log_file.name}: {e}")
                else:
                    result.deleted_items += 1
                    result.freed_space_bytes += size
                    result.add_detail(f"[DRY RUN] Would delete: {log_file.name}")
        
        # Check for oversized log files that need rotation
        for log_file in list(self.log_dir.glob('*.log')):
            if not log_file.name.endswith('.gz'):  # Skip compressed logs
                size_mb = log_file.stat().st_size / (1024 * 1024)
                
                if size_mb > self.policy.log_max_size_mb:
                    result.details.append(f"Oversized log: {log_file.name} ({size_mb:.2f} MB)")
                    
                    if not dry_run:
                        try:
                            # Compress the log
                            compressed_path = log_file.with_suffix('.log.gz')
                            with open(log_file, 'rb') as f_in:
                                with gzip.open(compressed_path, 'wb') as f_out:
                                    shutil.copyfileobj(f_in, f_out)
                            
                            # Remove original
                            log_file.unlink()
                            result.rotated_items += 1
                            result.add_detail(f"Compressed: {log_file.name}")
                        except Exception as e:
                            result.add_error(f"Failed to compress {log_file.name}: {e}")
                    else:
                        result.rotated_items += 1
                        result.add_detail(f"[DRY RUN] Would compress: {log_file.name}")
        
        # Check backup count for compressed logs
        compressed_logs = sorted(list(self.log_dir.glob('*.log.gz')),
                              key=lambda f: f.stat().st_mtime,
                              reverse=True)
        
        if len(compressed_logs) > self.policy.log_backup_count:
            to_delete = compressed_logs[self.policy.log_backup_count:]
            
            for log_file in to_delete:
                size = log_file.stat().st_size
                result.details.append(f"Excess backup: {log_file.name}")
                
                if not dry_run:
                    try:
                        log_file.unlink()
                        result.deleted_items += 1
                        result.freed_space_bytes += size
                        result.add_detail(f"Deleted: {log_file.name}")
                    except Exception as e:
                        result.add_error(f"Failed to delete {log_file.name}: {e}")
                else:
                    result.deleted_items += 1
                    result.freed_space_bytes += size
                    result.add_detail(f"[DRY RUN] Would delete: {log_file.name}")
        
        result.add_detail(f"Log cleanup complete: {result.deleted_items} deleted, "
                         f"{result.rotated_items} rotated, {result.freed_space_mb:.2f} MB freed")
        self.results.append(result)
        return result
    
    def cleanup_telemetry(self, dry_run: bool = False) -> CleanupResult:
        """
        Archive and clean up old telemetry data.
        
        Args:
            dry_run: If True, preview cleanup without actually deleting
            
        Returns:
            CleanupResult with details of telemetry cleanup
        """
        result = CleanupResult(category='telemetry')
        logger.info(f"Cleaning up telemetry in {self.telemetry_db}")
        
        if not self.telemetry_db.exists():
            result.add_detail("Telemetry database does not exist")
            return result
        
        try:
            conn = sqlite3.connect(self.telemetry_db)
            cursor = conn.cursor()
            
            # Get database size before cleanup
            db_size_before = self.telemetry_db.stat().st_size
            
            # Archive old telemetry (older than archive_age_days)
            archive_cutoff = datetime.now() - timedelta(days=self.policy.telemetry_archive_age_days)
            archive_cutoff_str = archive_cutoff.strftime('%Y-%m-%d %H:%M:%S')
            
            # Check if there's data to archive
            cursor.execute("SELECT COUNT(*) FROM operations WHERE timestamp < ?", (archive_cutoff_str,))
            old_ops_count = cursor.fetchone()[0]
            
            if old_ops_count > 0:
                result.details.append(f"Found {old_ops_count} old operations to archive")
                
                if not dry_run:
                    try:
                        # Create archive database
                        archive_db = self.telemetry_db.with_name(
                            f"{self.telemetry_db.stem}_archive_{datetime.now().strftime('%Y%m%d')}.db"
                        )
                        
                        # Copy old operations to archive
                        conn.execute(f"ATTACH DATABASE '{archive_db}' AS archive")
                        
                        # Copy operations table
                        conn.execute("""
                            INSERT INTO archive.operations
                            SELECT * FROM operations WHERE timestamp < ?
                        """, (archive_cutoff_str,))
                        
                        # Copy events table
                        conn.execute("""
                            INSERT INTO archive.events
                            SELECT * FROM events WHERE operation_id IN (
                                SELECT id FROM operations WHERE timestamp < ?
                            )
                        """, (archive_cutoff_str,))
                        
                        conn.execute("DETACH DATABASE archive")
                        
                        # Delete from main database
                        cursor.execute("DELETE FROM events WHERE operation_id IN ("
                                     "SELECT id FROM operations WHERE timestamp < ?)", 
                                     (archive_cutoff_str,))
                        cursor.execute("DELETE FROM operations WHERE timestamp < ?", 
                                     (archive_cutoff_str,))
                        
                        conn.commit()
                        result.archived_items = old_ops_count
                        result.add_detail(f"Archived {old_ops_count} operations to {archive_db.name}")
                        
                    except Exception as e:
                        conn.rollback()
                        result.add_error(f"Failed to archive telemetry: {e}")
                else:
                    result.archived_items = old_ops_count
                    result.add_detail(f"[DRY RUN] Would archive {old_ops_count} operations")
            
            # Delete very old telemetry (older than delete_age_days)
            delete_cutoff = datetime.now() - timedelta(days=self.policy.telemetry_delete_age_days)
            delete_cutoff_str = delete_cutoff.strftime('%Y-%m-%d %H:%M:%S')
            
            cursor.execute("SELECT COUNT(*) FROM operations WHERE timestamp < ?", (delete_cutoff_str,))
            very_old_ops_count = cursor.fetchone()[0]
            
            if very_old_ops_count > 0:
                result.details.append(f"Found {very_old_ops_count} very old operations to delete")
                
                if not dry_run:
                    try:
                        cursor.execute("DELETE FROM events WHERE operation_id IN ("
                                     "SELECT id FROM operations WHERE timestamp < ?)", 
                                     (delete_cutoff_str,))
                        cursor.execute("DELETE FROM operations WHERE timestamp < ?", 
                                     (delete_cutoff_str,))
                        
                        conn.commit()
                        result.deleted_items = very_old_ops_count
                        result.add_detail(f"Deleted {very_old_ops_count} old operations")
                        
                    except Exception as e:
                        conn.rollback()
                        result.add_error(f"Failed to delete old telemetry: {e}")
                else:
                    result.deleted_items = very_old_ops_count
                    result.add_detail(f"[DRY RUN] Would delete {very_old_ops_count} operations")
            
            # Vacuum database to reclaim space
            if not dry_run and (result.deleted_items > 0 or result.archived_items > 0):
                try:
                    cursor.execute("VACUUM")
                    conn.commit()
                except Exception as e:
                    result.add_error(f"Failed to vacuum database: {e}")
            
            conn.close()
            
            # Calculate freed space
            db_size_after = self.telemetry_db.stat().st_size
            result.freed_space_bytes = max(0, db_size_before - db_size_after)
            
            result.add_detail(f"Telemetry cleanup complete: {result.deleted_items} deleted, "
                           f"{result.archived_items} archived, {result.freed_space_mb:.2f} MB freed")
            
        except Exception as e:
            result.add_error(f"Failed to cleanup telemetry: {e}")
        
        self.results.append(result)
        return result
    
    def cleanup_sessions(self, dry_run: bool = False) -> CleanupResult:
        """
        Clean up old session data.
        
        Args:
            dry_run: If True, preview cleanup without actually deleting
            
        Returns:
            CleanupResult with details of session cleanup
        """
        result = CleanupResult(category='sessions')
        logger.info(f"Cleaning up sessions in {self.sessions_db}")
        
        if not self.sessions_db.exists():
            result.add_detail("Sessions database does not exist")
            return result
        
        try:
            conn = sqlite3.connect(self.sessions_db)
            cursor = conn.cursor()
            
            # Get database size before cleanup
            db_size_before = self.sessions_db.stat().st_size
            
            # Get all sessions
            cursor.execute("SELECT id, started_at, status FROM sessions ORDER BY started_at DESC")
            sessions = cursor.fetchall()
            
            if not sessions:
                result.add_detail("No sessions found")
                conn.close()
                self.results.append(result)
                return result
            
            # Keep only the most recent sessions
            if len(sessions) > self.policy.session_max_sessions:
                to_delete = sessions[self.policy.session_max_sessions:]
                
                for session_id, started_at, status in to_delete:
                    result.details.append(f"Old session: {session_id} (started: {started_at})")
                    
                    if not dry_run:
                        try:
                            # Delete session data
                            cursor.execute("DELETE FROM session_config WHERE session_id = ?", (session_id,))
                            cursor.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
                            result.deleted_items += 1
                            result.add_detail(f"Deleted session: {session_id}")
                        except Exception as e:
                            result.add_error(f"Failed to delete session {session_id}: {e}")
                    else:
                        result.deleted_items += 1
                        result.add_detail(f"[DRY RUN] Would delete session: {session_id}")
            
            # Delete old sessions by age
            cutoff_time = datetime.now() - timedelta(days=self.policy.session_max_age_days)
            cutoff_str = cutoff_time.strftime('%Y-%m-%d %H:%M:%S')
            
            cursor.execute("SELECT id, started_at FROM sessions WHERE started_at < ?", (cutoff_str,))
            old_sessions = cursor.fetchall()
            
            for session_id, started_at in old_sessions:
                result.details.append(f"Old session by age: {session_id} (started: {started_at})")
                
                if not dry_run:
                    try:
                        cursor.execute("DELETE FROM session_config WHERE session_id = ?", (session_id,))
                        cursor.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
                        result.deleted_items += 1
                        result.add_detail(f"Deleted session: {session_id}")
                    except Exception as e:
                        result.add_error(f"Failed to delete session {session_id}: {e}")
                else:
                    result.deleted_items += 1
                    result.add_detail(f"[DRY RUN] Would delete session: {session_id}")
            
            conn.commit()
            conn.close()
            
            # Calculate freed space
            db_size_after = self.sessions_db.stat().st_size
            result.freed_space_bytes = max(0, db_size_before - db_size_after)
            
            result.add_detail(f"Session cleanup complete: {result.deleted_items} deleted, "
                           f"{result.freed_space_mb:.2f} MB freed")
            
        except Exception as e:
            result.add_error(f"Failed to cleanup sessions: {e}")
        
        self.results.append(result)
        return result
    
    def cleanup_cache(self, dry_run: bool = False) -> CleanupResult:
        """
        Clean up old cache data.
        
        Args:
            dry_run: If True, preview cleanup without actually deleting
            
        Returns:
            CleanupResult with details of cache cleanup
        """
        result = CleanupResult(category='cache')
        logger.info(f"Cleaning up cache in {self.cache_dir}")
        
        if not self.cache_dir.exists():
            result.add_detail("Cache directory does not exist")
            return result
        
        cutoff_time = datetime.now() - timedelta(days=self.policy.cache_max_age_days)
        total_size_before = self._get_dir_size(self.cache_dir)
        
        # Get all files in cache
        cache_files = []
        for root, dirs, files in os.walk(self.cache_dir):
            for file in files:
                file_path = Path(root) / file
                try:
                    mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                    cache_files.append((file_path, mtime, file_path.stat().st_size))
                except Exception as e:
                    result.add_error(f"Failed to stat {file_path}: {e}")
        
        # Clean up old cache files
        for file_path, mtime, size in cache_files:
            if mtime < cutoff_time:
                result.details.append(f"Old cache file: {file_path.name}")
                
                if not dry_run:
                    try:
                        file_path.unlink()
                        result.deleted_items += 1
                        result.freed_space_bytes += size
                    except Exception as e:
                        result.add_error(f"Failed to delete {file_path}: {e}")
                else:
                    result.deleted_items += 1
                    result.freed_space_bytes += size
        
        # Clean up empty directories
        if not dry_run:
            for root, dirs, files in os.walk(self.cache_dir, topdown=False):
                for dir_name in dirs:
                    dir_path = Path(root) / dir_name
                    try:
                        if not any(dir_path.iterdir()):  # Empty directory
                            dir_path.rmdir()
                            result.add_detail(f"Removed empty directory: {dir_path}")
                    except Exception as e:
                        result.add_error(f"Failed to remove {dir_path}: {e}")
        
        result.add_detail(f"Cache cleanup complete: {result.deleted_items} deleted, "
                         f"{result.freed_space_mb:.2f} MB freed")
        self.results.append(result)
        return result
    
    def _is_critical_checkpoint(self, checkpoint_dir: Path) -> bool:
        """
        Check if a checkpoint is critical and should be preserved.
        
        Args:
            checkpoint_dir: Path to checkpoint directory
            
        Returns:
            True if checkpoint is critical
        """
        if not self.policy.checkpoint_keep_critical:
            return False
        
        # Check if checkpoint was created recently (last hour)
        mtime = datetime.fromtimestamp(checkpoint_dir.stat().st_mtime)
        if (datetime.now() - mtime).total_seconds() < 3600:
            return True
        
        # Check if checkpoint has metadata indicating it's critical
        metadata_file = checkpoint_dir / 'metadata.json'
        if metadata_file.exists():
            try:
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                    return metadata.get('critical', False)
            except Exception:
                pass
        
        return False
    
    def _get_dir_size(self, dir_path: Path) -> int:
        """
        Calculate total size of a directory.
        
        Args:
            dir_path: Path to directory
            
        Returns:
            Total size in bytes
        """
        total_size = 0
        try:
            for root, dirs, files in os.walk(dir_path):
                for file in files:
                    file_path = Path(root) / file
                    try:
                        total_size += file_path.stat().st_size
                    except Exception:
                        pass
        except Exception:
            pass
        return total_size
    
    def generate_report(self) -> Dict[str, Any]:
        """
        Generate comprehensive cleanup report.
        
        Returns:
            Dictionary with cleanup summary
        """
        total_deleted = sum(r.deleted_items for r in self.results)
        total_archived = sum(r.archived_items for r in self.results)
        total_rotated = sum(r.rotated_items for r in self.results)
        total_freed = sum(r.freed_space_bytes for r in self.results)
        total_errors = sum(len(r.errors) for r in self.results)
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_deleted': total_deleted,
                'total_archived': total_archived,
                'total_rotated': total_rotated,
                'total_freed_bytes': total_freed,
                'total_freed_mb': total_freed / (1024 * 1024),
                'total_errors': total_errors
            },
            'categories': {}
        }
        
        for result in self.results:
            report['categories'][result.category] = {
                'deleted': result.deleted_items,
                'archived': result.archived_items,
                'rotated': result.rotated_items,
                'freed_bytes': result.freed_space_bytes,
                'freed_mb': result.freed_space_mb,
                'errors': result.errors,
                'details': result.details
            }
        
        return report
    
    def print_report(self, report: Optional[Dict[str, Any]] = None):
        """
        Print cleanup report in human-readable format.
        
        Args:
            report: Cleanup report (generates if not provided)
        """
        if report is None:
            report = self.generate_report()
        
        print("\n" + "="*60)
        print("CLEANUP REPORT")
        print("="*60)
        
        summary = report['summary']
        print(f"\nTotal Deleted:   {summary['total_deleted']} items")
        print(f"Total Archived:  {summary['total_archived']} items")
        print(f"Total Rotated:   {summary['total_rotated']} items")
        print(f"Total Freed:    {summary['total_freed_mb']:.2f} MB")
        print(f"Total Errors:   {summary['total_errors']}")
        
        print("\n" + "-"*60)
        print("DETAILS BY CATEGORY")
        print("-"*60)
        
        for category, data in report['categories'].items():
            print(f"\n{category.upper()}:")
            print(f"  Deleted:  {data['deleted']}")
            print(f"  Archived: {data['archived']}")
            print(f"  Rotated:  {data['rotated']}")
            print(f"  Freed:    {data['freed_mb']:.2f} MB")
            
            if data['errors']:
                print(f"  Errors:")
                for error in data['errors']:
                    print(f"    - {error}")
            
            if data['details'] and logger.level <= logging.INFO:
                print(f"  Details:")
                for detail in data['details'][:5]:  # Show first 5 details
                    print(f"    - {detail}")
                if len(data['details']) > 5:
                    print(f"    ... and {len(data['details']) - 5} more")
        
        print("\n" + "="*60 + "\n")