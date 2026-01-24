"""
Unit tests for CleanupManager module (V5)
"""

import unittest
import os
import sqlite3
import json
import gzip
from datetime import datetime, timedelta
from pathlib import Path
from pathlib import Path
from v4.logic.cleanup_manager import (
    CleanupManager, CleanupPolicy, CleanupResult
)


class TestCleanupPolicy(unittest.TestCase):
    """Test cases for CleanupPolicy class."""
    
    def test_default_policy(self):
        """Test default cleanup policy values."""
        policy = CleanupPolicy()
        
        self.assertEqual(policy.checkpoint_max_age_hours, 24)
        self.assertEqual(policy.checkpoint_max_count, 10)
        self.assertTrue(policy.checkpoint_keep_critical)
        
        self.assertEqual(policy.log_max_size_mb, 10)
        self.assertEqual(policy.log_backup_count, 5)
        self.assertEqual(policy.log_max_age_days, 7)
        
        self.assertEqual(policy.telemetry_archive_age_days, 30)
        self.assertEqual(policy.telemetry_delete_age_days, 90)
        
        self.assertEqual(policy.session_max_sessions, 10)
        self.assertEqual(policy.session_max_age_days, 30)
        
        self.assertEqual(policy.cache_max_age_days, 7)
        self.assertEqual(policy.cache_max_size_mb, 100)
    
    def test_custom_policy(self):
        """Test custom cleanup policy values."""
        policy = CleanupPolicy(
            checkpoint_max_age_hours=48,
            checkpoint_max_count=20,
            log_max_age_days=14
        )
        
        self.assertEqual(policy.checkpoint_max_age_hours, 48)
        self.assertEqual(policy.checkpoint_max_count, 20)
        self.assertEqual(policy.log_max_age_days, 14)
    
    def test_policy_to_dict(self):
        """Test converting policy to dictionary."""
        policy = CleanupPolicy(checkpoint_max_age_hours=12)
        data = policy.to_dict()
        
        self.assertEqual(data['checkpoint_max_age_hours'], 12)
        self.assertEqual(data['log_max_size_mb'], 10)
        self.assertEqual(len(data), 12)  # All 12 fields
    
    def test_policy_from_dict(self):
        """Test creating policy from dictionary."""
        data = {
            'checkpoint_max_age_hours': 36,
            'checkpoint_max_count': 15,
            'log_max_age_days': 10
        }
        policy = CleanupPolicy.from_dict(data)
        
        self.assertEqual(policy.checkpoint_max_age_hours, 36)
        self.assertEqual(policy.checkpoint_max_count, 15)
        self.assertEqual(policy.log_max_age_days, 10)
    
    def test_policy_roundtrip(self):
        """Test policy serialization roundtrip."""
        original = CleanupPolicy(checkpoint_max_age_hours=48)
        data = original.to_dict()
        restored = CleanupPolicy.from_dict(data)
        
        self.assertEqual(original.checkpoint_max_age_hours, restored.checkpoint_max_age_hours)
        self.assertEqual(original.checkpoint_max_count, restored.checkpoint_max_count)


class TestCleanupResult(unittest.TestCase):
    """Test cases for CleanupResult class."""
    
    def test_initial_result(self):
        """Test initial cleanup result state."""
        result = CleanupResult(category='test')
        
        self.assertEqual(result.category, 'test')
        self.assertEqual(result.deleted_items, 0)
        self.assertEqual(result.archived_items, 0)
        self.assertEqual(result.rotated_items, 0)
        self.assertEqual(result.freed_space_bytes, 0)
        self.assertEqual(len(result.errors), 0)
        self.assertEqual(len(result.details), 0)
    
    def test_add_error(self):
        """Test adding error to result."""
        result = CleanupResult(category='test')
        result.add_error("Test error")
        
        self.assertEqual(len(result.errors), 1)
        self.assertEqual(result.errors[0], "Test error")
    
    def test_add_detail(self):
        """Test adding detail to result."""
        result = CleanupResult(category='test')
        result.add_detail("Test detail")
        
        self.assertEqual(len(result.details), 1)
        self.assertEqual(result.details[0], "Test detail")
    
    def test_freed_space_mb(self):
        """Test freed space conversion to MB."""
        result = CleanupResult(category='test')
        result.freed_space_bytes = 10 * 1024 * 1024  # 10 MB
        
        self.assertEqual(result.freed_space_mb, 10.0)


class TestCleanupManager(unittest.TestCase):
    """Test cases for CleanupManager class."""
    
    def setUp(self):
        """Set up test environment before each test."""
        self.test_dir = Path('test_cleanup_manager_temp')
        self.test_dir.mkdir(exist_ok=True)
        
        # Create subdirectories
        (self.test_dir / 'checkpoints').mkdir()
        (self.test_dir / 'logs').mkdir()
        (self.test_dir / '.l4_cache').mkdir()
        
        # Create test databases
        self.telemetry_db = self.test_dir / 'telemetry.db'
        self.sessions_db = self.test_dir / 'sessions.db'
        self._create_test_databases()
    
    def tearDown(self):
        """Clean up test environment after each test."""
        import shutil
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
    
    def _create_test_databases(self):
        """Create test databases with sample data."""
        # Create telemetry database
        conn = sqlite3.connect(self.telemetry_db)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS operations (
                id INTEGER PRIMARY KEY,
                operation_type TEXT,
                timestamp TEXT,
                status TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY,
                operation_id INTEGER,
                timestamp TEXT,
                event_type TEXT
            )
        """)
        
        # Insert old operations
        old_date = (datetime.now() - timedelta(days=40)).strftime('%Y-%m-%d %H:%M:%S')
        conn.execute("INSERT INTO operations (operation_type, timestamp, status) "
                   "VALUES (?, ?, ?)", ('test_op', old_date, 'completed'))
        op_id = conn.lastrowid
        conn.execute("INSERT INTO events (operation_id, timestamp, event_type) "
                   "VALUES (?, ?, ?)", (op_id, old_date, 'test_event'))
        
        # Insert recent operations
        recent_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn.execute("INSERT INTO operations (operation_type, timestamp, status) "
                   "VALUES (?, ?, ?)", ('recent_op', recent_date, 'completed'))
        conn.commit()
        conn.close()
        
        # Create sessions database
        conn = sqlite3.connect(self.sessions_db)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY,
                started_at TEXT,
                status TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS session_config (
                id INTEGER PRIMARY KEY,
                session_id INTEGER,
                config_key TEXT,
                config_value TEXT
            )
        """)
        
        # Insert old sessions
        old_date = (datetime.now() - timedelta(days=40)).strftime('%Y-%m-%d %H:%M:%S')
        conn.execute("INSERT INTO sessions (started_at, status) VALUES (?, ?)",
                   (old_date, 'completed'))
        session_id = conn.lastrowid
        conn.execute("INSERT INTO session_config (session_id, config_key, config_value) "
                   "VALUES (?, ?, ?)", (session_id, 'test', 'value'))
        
        # Insert recent session
        recent_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn.execute("INSERT INTO sessions (started_at, status) VALUES (?, ?)",
                   (recent_date, 'active'))
        conn.commit()
        conn.close()
    
    def test_init_default_policy(self):
        """Test initialization with default policy."""
        manager = CleanupManager(
            checkpoint_dir=str(self.test_dir / 'checkpoints'),
            log_dir=str(self.test_dir / 'logs'),
            telemetry_db=str(self.telemetry_db),
            sessions_db=str(self.sessions_db),
            cache_dir=str(self.test_dir / '.l4_cache')
        )
        
        self.assertIsInstance(manager.policy, CleanupPolicy)
        self.assertEqual(manager.checkpoint_dir, self.test_dir / 'checkpoints')
    
    def test_init_custom_policy(self):
        """Test initialization with custom policy."""
        custom_policy = CleanupPolicy(checkpoint_max_age_hours=12)
        manager = CleanupManager(
            checkpoint_dir=str(self.test_dir / 'checkpoints'),
            log_dir=str(self.test_dir / 'logs'),
            telemetry_db=str(self.telemetry_db),
            sessions_db=str(self.sessions_db),
            cache_dir=str(self.test_dir / '.l4_cache'),
            policy=custom_policy
        )
        
        self.assertEqual(manager.policy.checkpoint_max_age_hours, 12)
    
    def test_cleanup_checkpoints_none(self):
        """Test cleanup with no checkpoints."""
        manager = CleanupManager(
            checkpoint_dir=str(self.test_dir / 'checkpoints'),
            log_dir=str(self.test_dir / 'logs'),
            telemetry_db=str(self.telemetry_db),
            sessions_db=str(self.sessions_db),
            cache_dir=str(self.test_dir / '.l4_cache')
        )
        
        result = manager.cleanup_checkpoints(dry_run=True)
        
        self.assertEqual(result.category, 'checkpoints')
        self.assertEqual(result.deleted_items, 0)
    
    def test_cleanup_checkpoints_old(self):
        """Test cleanup of old checkpoints."""
        # Create old checkpoint
        old_checkpoint = self.test_dir / 'checkpoints' / 'chkp_20260101_000000_old'
        old_checkpoint.mkdir()
        (old_checkpoint / 'test.txt').write_text('x' * 1000)
        
        # Create recent checkpoint
        recent_checkpoint = self.test_dir / 'checkpoints' / 'chkp_20260124_000000_new'
        recent_checkpoint.mkdir()
        (recent_checkpoint / 'test.txt').write_text('x' * 1000)
        
        # Set old checkpoint to be 25 hours ago
        import time
        old_time = time.time() - (25 * 3600)
        os.utime(old_checkpoint, (old_time, old_time))
        
        policy = CleanupPolicy(checkpoint_max_age_hours=24, checkpoint_max_count=10)
        manager = CleanupManager(
            checkpoint_dir=str(self.test_dir / 'checkpoints'),
            log_dir=str(self.test_dir / 'logs'),
            telemetry_db=str(self.telemetry_db),
            sessions_db=str(self.sessions_db),
            cache_dir=str(self.test_dir / '.l4_cache'),
            policy=policy
        )
        
        result = manager.cleanup_checkpoints(dry_run=True)
        
        self.assertEqual(result.deleted_items, 1)
        self.assertTrue(result.freed_space_bytes > 0)
        self.assertTrue(any('chkp_20260101' in detail for detail in result.details))
        self.assertTrue(old_checkpoint.exists())  # Should still exist in dry run
    
    def test_cleanup_checkpoints_excess(self):
        """Test cleanup of excess checkpoints by count."""
        # Create 15 checkpoints
        for i in range(15):
            checkpoint = self.test_dir / 'checkpoints' / f'chkp_20260124_{i:02d}_0000'
            checkpoint.mkdir()
            (checkpoint / 'test.txt').write_text('x' * 100)
            
            # Make each checkpoint slightly older
            import time
            old_time = time.time() - (i * 100)
            os.utime(checkpoint, (old_time, old_time))
        
        policy = CleanupPolicy(checkpoint_max_age_hours=24, checkpoint_max_count=10)
        manager = CleanupManager(
            checkpoint_dir=str(self.test_dir / 'checkpoints'),
            log_dir=str(self.test_dir / 'logs'),
            telemetry_db=str(self.telemetry_db),
            sessions_db=str(self.sessions_db),
            cache_dir=str(self.test_dir / '.l4_cache'),
            policy=policy
        )
        
        result = manager.cleanup_checkpoints(dry_run=True)
        
        # Should delete 5 oldest (15 - 10 max)
        self.assertEqual(result.deleted_items, 5)
    
    def test_cleanup_logs_none(self):
        """Test cleanup with no log files."""
        manager = CleanupManager(
            checkpoint_dir=str(self.test_dir / 'checkpoints'),
            log_dir=str(self.test_dir / 'logs'),
            telemetry_db=str(self.telemetry_db),
            sessions_db=str(self.sessions_db),
            cache_dir=str(self.test_dir / '.l4_cache')
        )
        
        result = manager.cleanup_logs(dry_run=True)
        
        self.assertEqual(result.category, 'logs')
        self.assertEqual(result.deleted_items, 0)
    
    def test_cleanup_logs_old(self):
        """Test cleanup of old log files."""
        # Create old log file
        old_log = self.test_dir / 'logs' / 'old.log'
        old_log.write_text('x' * 1000)
        
        # Set old log to be 10 days ago
        import time
        old_time = time.time() - (10 * 24 * 3600)
        os.utime(old_log, (old_time, old_time))
        
        policy = CleanupPolicy(log_max_age_days=7)
        manager = CleanupManager(
            checkpoint_dir=str(self.test_dir / 'checkpoints'),
            log_dir=str(self.test_dir / 'logs'),
            telemetry_db=str(self.telemetry_db),
            sessions_db=str(self.sessions_db),
            cache_dir=str(self.test_dir / '.l4_cache'),
            policy=policy
        )
        
        result = manager.cleanup_logs(dry_run=True)
        
        self.assertEqual(result.deleted_items, 1)
        self.assertTrue(result.freed_space_bytes > 0)
    
    def test_cleanup_logs_oversized(self):
        """Test cleanup of oversized log files."""
        # Create large log file (15 MB)
        large_log = self.test_dir / 'logs' / 'large.log'
        large_log.write_text('x' * (15 * 1024 * 1024))
        
        policy = CleanupPolicy(log_max_size_mb=10)
        manager = CleanupManager(
            checkpoint_dir=str(self.test_dir / 'checkpoints'),
            log_dir=str(self.test_dir / 'logs'),
            telemetry_db=str(self.telemetry_db),
            sessions_db=str(self.sessions_db),
            cache_dir=str(self.test_dir / '.l4_cache'),
            policy=policy
        )
        
        result = manager.cleanup_logs(dry_run=True)
        
        self.assertEqual(result.rotated_items, 1)
    
    def test_cleanup_telemetry(self):
        """Test cleanup of telemetry data."""
        policy = CleanupPolicy(telemetry_archive_age_days=30)
        manager = CleanupManager(
            checkpoint_dir=str(self.test_dir / 'checkpoints'),
            log_dir=str(self.test_dir / 'logs'),
            telemetry_db=str(self.telemetry_db),
            sessions_db=str(self.sessions_db),
            cache_dir=str(self.test_dir / '.l4_cache'),
            policy=policy
        )
        
        result = manager.cleanup_telemetry(dry_run=True)
        
        self.assertEqual(result.category, 'telemetry')
        self.assertGreaterEqual(result.archived_items, 1)  # Should archive old operation
    
    def test_cleanup_sessions(self):
        """Test cleanup of session data."""
        policy = CleanupPolicy(session_max_age_days=30)
        manager = CleanupManager(
            checkpoint_dir=str(self.test_dir / 'checkpoints'),
            log_dir=str(self.test_dir / 'logs'),
            telemetry_db=str(self.telemetry_db),
            sessions_db=str(self.sessions_db),
            cache_dir=str(self.test_dir / '.l4_cache'),
            policy=policy
        )
        
        result = manager.cleanup_sessions(dry_run=True)
        
        self.assertEqual(result.category, 'sessions')
        self.assertGreaterEqual(result.deleted_items, 1)  # Should delete old session
    
    def test_cleanup_cache(self):
        """Test cleanup of cache data."""
        # Create old cache file
        old_cache = self.test_dir / '.l4_cache' / 'old.cache'
        old_cache.write_text('x' * 1000)
        
        # Set old cache to be 10 days ago
        import time
        old_time = time.time() - (10 * 24 * 3600)
        os.utime(old_cache, (old_time, old_time))
        
        policy = CleanupPolicy(cache_max_age_days=7)
        manager = CleanupManager(
            checkpoint_dir=str(self.test_dir / 'checkpoints'),
            log_dir=str(self.test_dir / 'logs'),
            telemetry_db=str(self.telemetry_db),
            sessions_db=str(self.sessions_db),
            cache_dir=str(self.test_dir / '.l4_cache'),
            policy=policy
        )
        
        result = manager.cleanup_cache(dry_run=True)
        
        self.assertEqual(result.category, 'cache')
        self.assertEqual(result.deleted_items, 1)
        self.assertTrue(result.freed_space_bytes > 0)
    
    def test_cleanup_all(self):
        """Test running all cleanup operations."""
        manager = CleanupManager(
            checkpoint_dir=str(self.test_dir / 'checkpoints'),
            log_dir=str(self.test_dir / 'logs'),
            telemetry_db=str(self.telemetry_db),
            sessions_db=str(self.sessions_db),
            cache_dir=str(self.test_dir / '.l4_cache')
        )
        
        report = manager.cleanup_all(dry_run=True)
        
        self.assertIn('timestamp', report)
        self.assertIn('summary', report)
        self.assertIn('categories', report)
        self.assertIn('total_deleted', report['summary'])
        self.assertIn('total_freed_mb', report['summary'])
        
        # Check all categories were processed
        self.assertIn('checkpoints', report['categories'])
        self.assertIn('logs', report['categories'])
        self.assertIn('telemetry', report['categories'])
        self.assertIn('sessions', report['categories'])
        self.assertIn('cache', report['categories'])
    
    def test_generate_report(self):
        """Test report generation."""
        manager = CleanupManager(
            checkpoint_dir=str(self.test_dir / 'checkpoints'),
            log_dir=str(self.test_dir / 'logs'),
            telemetry_db=str(self.telemetry_db),
            sessions_db=str(self.sessions_db),
            cache_dir=str(self.test_dir / '.l4_cache')
        )
        
        manager.cleanup_all(dry_run=True)
        report = manager.generate_report()
        
        self.assertIn('timestamp', report)
        self.assertIn('summary', report)
        self.assertIn('categories', report)
        
        # Check summary fields
        summary = report['summary']
        self.assertIn('total_deleted', summary)
        self.assertIn('total_archived', summary)
        self.assertIn('total_rotated', summary)
        self.assertIn('total_freed_bytes', summary)
        self.assertIn('total_freed_mb', summary)
        self.assertIn('total_errors', summary)
    
    def test_is_critical_checkpoint(self):
        """Test critical checkpoint detection."""
        manager = CleanupManager(
            checkpoint_dir=str(self.test_dir / 'checkpoints'),
            log_dir=str(self.test_dir / 'logs'),
            telemetry_db=str(self.telemetry_db),
            sessions_db=str(self.sessions_db),
            cache_dir=str(self.test_dir / '.l4_cache')
        )
        
        # Test non-critical checkpoint
        checkpoint_dir = self.test_dir / 'checkpoints' / 'chkp_test'
        checkpoint_dir.mkdir()
        self.assertFalse(manager._is_critical_checkpoint(checkpoint_dir))
        
        # Test critical checkpoint (recent)
        import time
        recent_time = time.time() - 1800  # 30 minutes ago
        os.utime(checkpoint_dir, (recent_time, recent_time))
        self.assertTrue(manager._is_critical_checkpoint(checkpoint_dir))
        
        # Test critical checkpoint (with metadata)
        metadata_file = checkpoint_dir / 'metadata.json'
        with open(metadata_file, 'w') as f:
            json.dump({'critical': True}, f)
        
        self.assertTrue(manager._is_critical_checkpoint(checkpoint_dir))
    
    def test_get_dir_size(self):
        """Test directory size calculation."""
        # Create test directory with files
        test_dir = self.test_dir / 'size_test'
        test_dir.mkdir()
        
        (test_dir / 'file1.txt').write_text('x' * 1000)
        (test_dir / 'file2.txt').write_text('x' * 2000)
        
        subdir = test_dir / 'subdir'
        subdir.mkdir()
        (subdir / 'file3.txt').write_text('x' * 500)
        
        manager = CleanupManager(
            checkpoint_dir=str(self.test_dir / 'checkpoints'),
            log_dir=str(self.test_dir / 'logs'),
            telemetry_db=str(self.telemetry_db),
            sessions_db=str(self.sessions_db),
            cache_dir=str(self.test_dir / '.l4_cache')
        )
        
        size = manager._get_dir_size(test_dir)
        
        self.assertEqual(size, 3500)  # 1000 + 2000 + 500


if __name__ == '__main__':
    unittest.main()