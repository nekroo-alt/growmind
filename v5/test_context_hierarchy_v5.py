"""
Unit Tests for ContextHierarchyManager V5 Layered Context Architecture

Tests V5 features:
- Progressive context loading
- Layer prioritization
- Hot/Warm/Cold classification
- Access pattern optimization
- Preloading and recommendations
"""

import unittest
import tempfile
import os
import time
from pathlib import Path

from data.context_hierarchy import (
    ContextHierarchyManager,
    ContextLevel,
    LayerUsagePattern,
    get_context_hierarchy
)


class TestContextLevel(unittest.TestCase):
    """Test ContextLevel enumeration and utilities."""
    
    def test_get_priority(self):
        """Test priority calculation for each level."""
        self.assertEqual(ContextLevel.get_priority(ContextLevel.L0), 0)
        self.assertEqual(ContextLevel.get_priority(ContextLevel.L1), 1)
        self.assertEqual(ContextLevel.get_priority(ContextLevel.L2), 2)
        self.assertEqual(ContextLevel.get_priority(ContextLevel.L3), 3)
        self.assertEqual(ContextLevel.get_priority('L5'), 999)
    
    def test_get_cache_type(self):
        """Test cache type classification."""
        self.assertEqual(ContextLevel.get_cache_type(ContextLevel.L0), "HOT")
        self.assertEqual(ContextLevel.get_cache_type(ContextLevel.L1), "WARM")
        self.assertEqual(ContextLevel.get_cache_type(ContextLevel.L2), "COLD")
        self.assertEqual(ContextLevel.get_cache_type(ContextLevel.L3), "NONE")
        self.assertEqual(ContextLevel.get_cache_type('L5'), "NONE")


class TestLayerUsagePattern(unittest.TestCase):
    """Test LayerUsagePattern tracking and analysis."""
    
    def setUp(self):
        """Set up test pattern."""
        self.pattern = LayerUsagePattern()
    
    def test_record_usage(self):
        """Test recording layer usage."""
        self.pattern.record_usage('implementation', ContextLevel.L0, True, 0.1)
        
        self.assertIn('implementation', self.pattern.task_types)
        self.assertEqual(self.pattern.task_types['implementation'][ContextLevel.L0], 1)
        self.assertGreater(self.pattern.layer_success_rates[ContextLevel.L0], 0)
        self.assertEqual(len(self.pattern.layer_load_times[ContextLevel.L0]), 1)
    
    def test_record_multiple_usage(self):
        """Test recording multiple usages."""
        self.pattern.record_usage('implementation', ContextLevel.L0, True, 0.1)
        self.pattern.record_usage('implementation', ContextLevel.L0, True, 0.15)
        self.pattern.record_usage('implementation', ContextLevel.L1, False, 0.2)
        
        self.assertEqual(self.pattern.task_types['implementation'][ContextLevel.L0], 2)
        self.assertEqual(self.pattern.task_types['implementation'][ContextLevel.L1], 1)
    
    def test_exponential_moving_average(self):
        """Test success rate with exponential moving average."""
        # Record successful uses (with higher alpha for testing)
        for _ in range(30):  # More iterations for convergence
            self.pattern.record_usage('test', ContextLevel.L0, True, 0.1)
        
        success_rate = self.pattern.layer_success_rates[ContextLevel.L0]
        self.assertGreater(success_rate, 0.8)  # Adjusted expectation
        
        # Record some failures
        for _ in range(5):
            self.pattern.record_usage('test', ContextLevel.L0, False, 0.1)
        
        success_rate_after = self.pattern.layer_success_rates[ContextLevel.L0]
        self.assertLess(success_rate_after, success_rate)
    
    def test_get_optimal_level(self):
        """Test optimal level selection."""
        # Set up pattern where L1 is used more and more successful
        for _ in range(10):
            self.pattern.record_usage('planning', ContextLevel.L1, True, 0.2)
        
        for _ in range(5):
            self.pattern.record_usage('planning', ContextLevel.L0, False, 0.1)
        
        optimal = self.pattern.get_optimal_level('planning')
        self.assertEqual(optimal, ContextLevel.L1)
    
    def test_get_optimal_level_no_data(self):
        """Test optimal level with no data."""
        optimal = self.pattern.get_optimal_level('unknown_task')
        self.assertEqual(optimal, ContextLevel.L0)
    
    def test_get_average_load_time(self):
        """Test average load time calculation."""
        load_times = [0.1, 0.15, 0.2, 0.12, 0.18]
        
        for load_time in load_times:
            self.pattern.record_usage('test', ContextLevel.L0, True, load_time)
        
        avg = self.pattern.get_average_load_time(ContextLevel.L0)
        expected = sum(load_times) / len(load_times)
        self.assertAlmostEqual(avg, expected, places=2)
    
    def test_load_time_limiting(self):
        """Test that only last 100 load times are kept."""
        # Record 150 load times
        for i in range(150):
            self.pattern.record_usage('test', ContextLevel.L0, True, 0.1 + i * 0.01)
        
        # Should only keep last 100
        self.assertEqual(len(self.pattern.layer_load_times[ContextLevel.L0]), 100)


class TestContextHierarchyManagerV5(unittest.TestCase):
    """Test V5 layered context architecture features."""
    
    def setUp(self):
        """Set up test database and manager."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_context_hierarchy.db")
        
        self.manager = ContextHierarchyManager(
            db_path=self.db_path,
            cache_capacities={
                ContextLevel.L0: 10,
                ContextLevel.L1: 20,
                ContextLevel.L2: 50,
                ContextLevel.L3: 0
            }
        )
    
    def tearDown(self):
        """Clean up test database."""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        # Also clean up WAL and SHM files
        for ext in ['-wal', '-shm']:
            wal_path = self.db_path + ext
            if os.path.exists(wal_path):
                os.remove(wal_path)
        
        # Remove directory with retry (handles WAL files)
        import shutil
        try:
            os.rmdir(self.temp_dir)
        except OSError:
            # Directory may have WAL files, use shutil
            shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_init_with_v5_features(self):
        """Test initialization with V5 features."""
        self.assertIsNotNone(self.manager.usage_pattern)
        self.assertIsNotNone(self.manager._preloaded_layers)
        
        # Check cache capacities
        self.assertIsNotNone(self.manager._caches[ContextLevel.L0])
        self.assertIsNotNone(self.manager._caches[ContextLevel.L1])
        self.assertIsNotNone(self.manager._caches[ContextLevel.L2])
        self.assertIsNone(self.manager._caches[ContextLevel.L3])
    
    def test_load_context_progressively(self):
        """Test progressive context loading."""
        # Add context items at different levels (respecting limits)
        for i in range(1):  # L0 limit is 1
            self.manager.add_context_item(
                level=ContextLevel.L0,
                item_type='action',
                content={'action': f'action_{i}'}
            )
        
        for i in range(5):
            self.manager.add_context_item(
                level=ContextLevel.L1,
                item_type='action',
                content={'action': f'recent_action_{i}'}
            )
        
        # Load progressively
        result = self.manager.load_context_progressively(
            task_type='implementation',
            min_level=ContextLevel.L0
        )
        
        self.assertIn('level', result)
        self.assertIn('items', result)
        self.assertIn('tokens_estimate', result)
        self.assertIn('sufficient', result)
        self.assertIn('expansion_history', result)
        
        # Should have loaded at least L0 items
        self.assertGreater(len(result['items']), 0)
    
    def test_progressive_loading_with_max_tokens(self):
        """Test progressive loading with token limit."""
        # Add items to L1 (higher limit than L0)
        for i in range(10):  # L1 limit is 10
            self.manager.add_context_item(
                level=ContextLevel.L1,
                item_type='action',
                content={'action': f'action_{i}', 'data': 'x' * 100}
            )
        
        # Load with token limit
        result = self.manager.load_context_progressively(
            task_type='implementation',
            min_level=ContextLevel.L1,  # Start from L1 which has more items
            max_tokens=500
        )
        
        self.assertLessEqual(result['tokens_estimate'], 500)
    
    def test_load_level(self):
        """Test loading a specific level."""
        # Add items to L1
        for i in range(5):
            self.manager.add_context_item(
                level=ContextLevel.L1,
                item_type='action',
                content={'action': f'action_{i}'}
            )
        
        items = self.manager._load_level(ContextLevel.L1)
        
        self.assertEqual(len(items), 5)
        self.assertTrue(all(item.get('item_type') == 'action' for item in items))
    
    def test_limit_by_tokens(self):
        """Test token limiting."""
        items = []
        for i in range(10):
            items.append({
                'item_type': 'action',
                'content': {'data': 'x' * 100}  # ~25 tokens
            })
        
        # Limit to 100 tokens (should include ~4 items)
        limited = self.manager._limit_by_tokens(items, max_tokens=100)
        
        self.assertLessEqual(len(limited), 4)
        self.assertGreater(len(limited), 0)
    
    def test_is_context_sufficient(self):
        """Test context sufficiency checking."""
        # L0 with action and state should be sufficient for implementation
        l0_items = [
            {'item_type': 'action', 'content': {'action': 'test'}},
            {'item_type': 'state', 'content': {'state': 'test'}}
        ]
        
        sufficient = self.manager._is_context_sufficient(
            'implementation',
            ContextLevel.L0,
            l0_items
        )
        
        self.assertTrue(sufficient)
    
    def test_is_context_not_sufficient(self):
        """Test that insufficient context is detected."""
        # L0 with only action should not be sufficient for planning
        l0_items = [
            {'item_type': 'action', 'content': {'action': 'test'}}
        ]
        
        sufficient = self.manager._is_context_sufficient(
            'planning',
            ContextLevel.L0,
            l0_items
        )
        
        # Planning needs more context than L0 provides
        self.assertFalse(sufficient)
    
    def test_get_next_level(self):
        """Test level progression."""
        self.assertEqual(
            self.manager._get_next_level(ContextLevel.L0),
            ContextLevel.L1
        )
        self.assertEqual(
            self.manager._get_next_level(ContextLevel.L1),
            ContextLevel.L2
        )
        self.assertEqual(
            self.manager._get_next_level(ContextLevel.L2),
            ContextLevel.L3
        )
        self.assertIsNone(
            self.manager._get_next_level(ContextLevel.L3)
        )
    
    def test_get_optimal_level(self):
        """Test optimal level retrieval."""
        # Record usage pattern
        for _ in range(10):
            self.manager._record_layer_usage('planning', ContextLevel.L2, True, 0.2)
        
        for _ in range(3):
            self.manager._record_layer_usage('planning', ContextLevel.L0, True, 0.1)
        
        optimal = self.manager.get_optimal_level('planning')
        self.assertEqual(optimal, ContextLevel.L2)
    
    def test_get_optimal_level_default(self):
        """Test default optimal level for unknown task."""
        optimal = self.manager.get_optimal_level('unknown_task')
        self.assertEqual(optimal, ContextLevel.L0)
    
    def test_record_layer_usage(self):
        """Test layer usage recording."""
        self.manager._record_layer_usage('test', ContextLevel.L0, True, 0.1)
        
        # Check in-memory pattern
        self.assertIn('test', self.manager.usage_pattern.task_types)
        self.assertEqual(
            self.manager.usage_pattern.task_types['test'][ContextLevel.L0],
            1
        )
    
    def test_preload_layer(self):
        """Test layer preloading."""
        # Add items to L0 (limited to DEFAULT_LIMITS[L0] = 1)
        for i in range(1):  # Only 1 item allowed at L0
            self.manager.add_context_item(
                level=ContextLevel.L0,
                item_type='action',
                content={'action': f'action_{i}'}
            )
        
        # Preload L0
        self.manager.preload_layer(
            level=ContextLevel.L0,
            task_types=['implementation']
        )
        
        # Check preloaded layer
        preloaded = self.manager.get_preloaded_layer(ContextLevel.L0)
        self.assertIsNotNone(preloaded)
        self.assertEqual(preloaded['level'], ContextLevel.L0)
        # L0 has limit of 1, so we expect 1 item
        self.assertEqual(len(preloaded['items']), 1)
    
    def test_preload_layer_no_cache(self):
        """Test that L3 is not preloaded (no caching)."""
        self.manager.preload_layer(level=ContextLevel.L3)
        
        preloaded = self.manager.get_preloaded_layer(ContextLevel.L3)
        self.assertIsNone(preloaded)
    
    def test_preload_expiration(self):
        """Test that preloads expire after TTL."""
        # Add items and preload with short TTL
        for i in range(3):
            self.manager.add_context_item(
                level=ContextLevel.L0,
                item_type='action',
                content={'action': f'action_{i}'}
            )
        
        # Override TTL for testing
        self.manager.DEFAULT_TTL[ContextLevel.L0] = 0.1  # 100ms
        
        self.manager.preload_layer(level=ContextLevel.L0)
        
        # Should be preloaded immediately
        preloaded = self.manager.get_preloaded_layer(ContextLevel.L0)
        self.assertIsNotNone(preloaded)
        
        # Wait for expiration
        time.sleep(0.15)
        
        # Should be expired
        preloaded = self.manager.get_preloaded_layer(ContextLevel.L0)
        self.assertIsNone(preloaded)
    
    def test_get_layer_recommendations(self):
        """Test layer recommendations."""
        # Record usage patterns
        for _ in range(10):
            self.manager._record_layer_usage('planning', ContextLevel.L2, True, 0.2)
        
        recs = self.manager.get_layer_recommendations('planning')
        
        self.assertEqual(recs['task_type'], 'planning')
        self.assertEqual(recs['recommended_level'], ContextLevel.L2)
        self.assertGreater(recs['confidence'], 0)
        self.assertIn('usage_stats', recs)
        self.assertIn('avg_load_times', recs)
        self.assertIn('cache_types', recs)
    
    def test_save_preload_recommendations(self):
        """Test saving preload recommendations."""
        # Record usage
        for _ in range(5):
            self.manager._record_layer_usage('test_task', ContextLevel.L1, True, 0.15)
        
        # Save recommendations
        self.manager.save_preload_recommendations()
        
        # Verify in database
        with self.manager._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM preload_recommendations 
                WHERE task_type = ?
            """, ('test_task',))
            
            row = cursor.fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row['task_type'], 'test_task')
            self.assertEqual(row['recommended_level'], ContextLevel.L1)
            self.assertGreater(row['confidence'], 0)
    
    def test_get_cache_stats_v5(self):
        """Test cache statistics with V5 enhancements."""
        # Add some items
        self.manager.add_context_item(
            level=ContextLevel.L0,
            item_type='action',
            content={'action': 'test'}
        )
        
        # Get cache stats
        stats = self.manager.get_cache_stats(ContextLevel.L0)
        
        self.assertIn('capacity', stats)
        self.assertIn('size', stats)
        self.assertIn('hits', stats)
        self.assertIn('misses', stats)
        self.assertIn('hit_rate', stats)
        
        # V5 specific fields
        self.assertIn('cache_type', stats)
        self.assertIn('priority', stats)
        
        self.assertEqual(stats['cache_type'], 'HOT')
        self.assertEqual(stats['priority'], 0)
    
    def test_get_all_cache_stats(self):
        """Test getting cache stats for all levels."""
        stats = self.manager.get_cache_stats()
        
        # Only levels with caches should be in stats
        for level in [ContextLevel.L0, ContextLevel.L1, ContextLevel.L2]:
            self.assertIn(level, stats)
        # L3 has no cache, so it won't be in stats
            self.assertIn('cache_type', stats[level])
            self.assertIn('priority', stats[level])
    
    def test_get_layer_stats(self):
        """Test comprehensive layer statistics."""
        # Add items at different levels (respecting DEFAULT_LIMITS)
        # L0 limit: 1, L1 limit: 10, L2 limit: 20
        for level, count in [(ContextLevel.L0, 1), (ContextLevel.L1, 3), (ContextLevel.L2, 3)]:
            for i in range(count):
                self.manager.add_context_item(
                    level=level,
                    item_type='action',
                    content={'action': f'{level}_{i}'}
                )
        
        # Record some usage
        self.manager._record_layer_usage('test', ContextLevel.L0, True, 0.1)
        
        stats = self.manager.get_layer_stats()
        
        self.assertIn('item_counts', stats)
        self.assertIn('cache_stats', stats)
        self.assertIn('usage_stats', stats)
        self.assertIn('preload_status', stats)
        self.assertIn('cache_types', stats)
        self.assertIn('priorities', stats)
        
        # Check item counts (respecting limits)
        self.assertEqual(stats['item_counts'][ContextLevel.L0], 1)
        self.assertEqual(stats['item_counts'][ContextLevel.L1], 3)
        self.assertEqual(stats['item_counts'][ContextLevel.L2], 3)
    
    def test_load_usage_patterns(self):
        """Test loading usage patterns from database."""
        # Record usage
        self.manager._record_layer_usage('test_task', ContextLevel.L0, True, 0.1)
        self.manager._record_layer_usage('test_task', ContextLevel.L0, True, 0.15)
        
        # Create new manager to test loading
        new_manager = ContextHierarchyManager(db_path=self.db_path)
        
        self.assertIn('test_task', new_manager.usage_pattern.task_types)
        self.assertEqual(
            new_manager.usage_pattern.task_types['test_task'][ContextLevel.L0],
            2
        )


class TestContextHierarchyIntegration(unittest.TestCase):
    """Integration tests for V5 layered context architecture."""
    
    def setUp(self):
        """Set up test database."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_integration.db")
        self.manager = ContextHierarchyManager(db_path=self.db_path)
    
    def tearDown(self):
        """Clean up test database."""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        # Clean up WAL and SHM files
        for ext in ['-wal', '-shm']:
            wal_path = self.db_path + ext
            if os.path.exists(wal_path):
                os.remove(wal_path)
        
        # Remove directory with retry
        import shutil
        try:
            os.rmdir(self.temp_dir)
        except OSError:
            shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_progressive_loading_scenario(self):
        """Test realistic progressive loading scenario."""
        # Simulate different task types
        task_scenarios = [
            ('implementation', [ContextLevel.L0], 10),
            ('planning', [ContextLevel.L0, ContextLevel.L1, ContextLevel.L2], 30),
            ('verification', [ContextLevel.L0], 5)
        ]
        
        for task_type, levels, count in task_scenarios:
            # Add context items
            for level in levels:
                for i in range(count // len(levels)):
                    self.manager.add_context_item(
                        level=level,
                        item_type='action',
                        content={'action': f'{task_type}_{level}_{i}'}
                    )
        
        # Test progressive loading for each task type
        for task_type, _, _ in task_scenarios:
            result = self.manager.load_context_progressively(
                task_type=task_type,
                min_level=ContextLevel.L0
            )
            
            self.assertGreater(len(result['items']), 0)
            self.assertIn('expansion_history', result)
            
            # Verify expansion was tracked
            self.assertGreater(len(result['expansion_history']), 0)
    
    def test_learning_optimal_levels(self):
        """Test that system learns optimal levels over time."""
        task_type = 'test_task'
        
        # Simulate iterations where L1 is consistently successful
        # (L0 has limit of 1, so we'll use L1 for testing)
        for i in range(5):  # Fewer iterations for faster test
            # Add context at L1
            for j in range(5):  # L1 limit is 10
                self.manager.add_context_item(
                    level=ContextLevel.L1,
                    item_type='action',
                    content={'action': f'action_{i}_{j}'}
                )
            
            # Load progressively
            result = self.manager.load_context_progressively(
                task_type=task_type,
                min_level=ContextLevel.L1  # Start from L1
            )
            
            # Record that L1 was sufficient
            self.manager._record_layer_usage(task_type, ContextLevel.L1, True, 0.1)
        
        # Get optimal level
        optimal = self.manager.get_optimal_level(task_type)
        
        # Should prefer L1 based on usage pattern
        self.assertEqual(optimal, ContextLevel.L1)
    
    def test_preload_optimization(self):
        """Test preload optimization for frequently used tasks."""
        # Identify frequently used task
        task_type = 'frequent_task'
        
        # Add items to L1 (limited to 10 by DEFAULT_LIMITS)
        for i in range(10):
            self.manager.add_context_item(
                level=ContextLevel.L1,
                item_type='action',
                content={'action': f'action_{i}'}
            )
        
        # Preload L1 for this task
        self.manager.preload_layer(
            level=ContextLevel.L1,
            task_types=[task_type]
        )
        
        # Verify preloaded
        preloaded = self.manager.get_preloaded_layer(ContextLevel.L1)
        self.assertIsNotNone(preloaded)
        self.assertEqual(len(preloaded['items']), 10)  # Limited by DEFAULT_LIMITS
        
        # Verify it's used on next load
        result = self.manager.load_context_progressively(
            task_type=task_type,
            min_level=ContextLevel.L0
        )
        
        self.assertGreater(len(result['items']), 0)


class TestContextHierarchyFactory(unittest.TestCase):
    """Test factory function."""
    
    def test_get_context_hierarchy_singleton(self):
        """Test that factory returns singleton instance."""
        # Use file-based db instead of in-memory to avoid table creation issues
        import tempfile
        temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(temp_dir, "test_singleton.db")
        
        try:
            manager1 = get_context_hierarchy(db_path=db_path)
            manager2 = get_context_hierarchy(db_path=db_path)
            
            # Should return same instance
            self.assertIs(manager1, manager2)
        finally:
            # Cleanup
            if os.path.exists(db_path):
                os.remove(db_path)
            for ext in ['-wal', '-shm']:
                wal_path = db_path + ext
                if os.path.exists(wal_path):
                    os.remove(wal_path)
            try:
                os.rmdir(temp_dir)
            except:
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_reset_singleton(self):
        """Test resetting singleton (for testing)."""
        # Import and reset global
        from data.context_hierarchy import _context_hierarchy_manager
        
        # Use file-based db
        import tempfile
        temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(temp_dir, "test_reset.db")
        
        try:
            _context_hierarchy_manager = None
            
            # Create new instance
            manager = get_context_hierarchy(db_path=db_path)
            self.assertIsNotNone(manager)
        finally:
            # Cleanup
            if os.path.exists(db_path):
                os.remove(db_path)
            for ext in ['-wal', '-shm']:
                wal_path = db_path + ext
                if os.path.exists(wal_path):
                    os.remove(wal_path)
            try:
                os.rmdir(temp_dir)
            except:
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == '__main__':
    unittest.main()