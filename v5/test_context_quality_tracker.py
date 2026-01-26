"""
Comprehensive unit tests for Context Quality Tracker - V5 Quality Enhancement
"""

import os
import unittest
import sqlite3
from datetime import datetime, timedelta
import json
import tempfile
import shutil

from v5.logic import (
    ContextQualityTracker,
    ContextQualityMetrics,
    QualityMetric,
    QualityThreshold,
    QualityReport
)


class TestContextQualityTracker(unittest.TestCase):
    """Test suite for ContextQualityTracker"""
    
    def setUp(self):
        """Set up test environment"""
        # Create temporary directory for test database
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "test_quality.db")
        
        # Initialize tracker
        self.tracker = ContextQualityTracker(db_path=self.db_path)
        self.tracker.connect()
    
    def tearDown(self):
        """Clean up test environment"""
        self.tracker.close()
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_database_creation(self):
        """Test that database and tables are created"""
        # Check that database file exists
        self.assertTrue(os.path.exists(self.db_path))
        
        # Check that tables exist
        cursor = self.tracker.conn.cursor()
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' 
            ORDER BY name
        """)
        tables = [row[0] for row in cursor.fetchall()]
        
        expected_tables = [
            'context_quality',
            'quality_correlation',
            'quality_recommendations'
        ]
        
        for table in expected_tables:
            self.assertIn(table, tables)
    
    def test_calculate_completeness(self):
        """Test completeness calculation"""
        # Perfect completeness (all required provided)
        required = ['file1.py', 'file2.py', 'file3.py']
        provided = ['file1.py', 'file2.py', 'file3.py']
        
        completeness = self.tracker.calculate_completeness(required, provided)
        self.assertEqual(completeness, 1.0)
        
        # Partial completeness
        provided = ['file1.py', 'file2.py']
        completeness = self.tracker.calculate_completeness(required, provided)
        self.assertAlmostEqual(completeness, 2.0/3.0, places=2)
        
        # Zero completeness
        provided = []
        completeness = self.tracker.calculate_completeness(required, provided)
        self.assertEqual(completeness, 0.0)
        
        # Case insensitive
        provided = ['FILE1.py', 'file2.PY']
        completeness = self.tracker.calculate_completeness(required, provided)
        self.assertEqual(completeness, 2.0/3.0)
        
        # Empty requirements (perfect by default)
        required = []
        provided = ['file1.py']
        completeness = self.tracker.calculate_completeness(required, provided)
        self.assertEqual(completeness, 1.0)
    
    def test_calculate_relevance(self):
        """Test relevance calculation"""
        # High relevance
        context_items = [
            {'relevance_score': 0.9},
            {'relevance_score': 0.85},
            {'relevance_score': 0.8}
        ]
        
        relevance = self.tracker.calculate_relevance(context_items)
        self.assertAlmostEqual(relevance, 0.85, places=2)
        
        # Low relevance
        context_items = [
            {'relevance_score': 0.3},
            {'relevance_score': 0.25},
            {'relevance_score': 0.2}
        ]
        
        relevance = self.tracker.calculate_relevance(context_items)
        self.assertAlmostEqual(relevance, 0.25, places=2)
        
        # Empty context
        relevance = self.tracker.calculate_relevance([])
        self.assertEqual(relevance, 0.0)
        
        # Missing relevance scores (default to 0.0)
        context_items = [
            {'relevance_score': 0.5},
            {},
            {'relevance_score': 0.7}
        ]
        
        relevance = self.tracker.calculate_relevance(context_items)
        self.assertAlmostEqual(relevance, 0.4, places=2)
    
    def test_calculate_freshness(self):
        """Test freshness calculation"""
        now = datetime.now()
        
        # Very fresh (created today)
        context_items = [
            {'timestamp': (now - timedelta(hours=1)).isoformat()},
            {'timestamp': (now - timedelta(hours=2)).isoformat()},
            {'timestamp': (now - timedelta(hours=3)).isoformat()}
        ]
        
        freshness = self.tracker.calculate_freshness(context_items, now)
        self.assertGreater(freshness, 0.9)
        
        # Stale (30 days old)
        context_items = [
            {'timestamp': (now - timedelta(days=30)).isoformat()},
            {'timestamp': (now - timedelta(days=30)).isoformat()}
        ]
        
        freshness = self.tracker.calculate_freshness(context_items, now)
        self.assertAlmostEqual(freshness, 0.0, places=2)
        
        # Medium freshness (15 days old)
        context_items = [
            {'timestamp': (now - timedelta(days=15)).isoformat()},
            {'timestamp': (now - timedelta(days=15)).isoformat()}
        ]
        
        freshness = self.tracker.calculate_freshness(context_items, now)
        self.assertAlmostEqual(freshness, 0.5, places=2)
        
        # Empty context
        freshness = self.tracker.calculate_freshness([], now)
        self.assertEqual(freshness, 0.0)
    
    def test_calculate_conciseness(self):
        """Test conciseness calculation"""
        # High conciseness (dense code)
        context_items = [
            {
                'content': 'def f(x): return x*2',
                'token_count': 10,
            },
            {
                'content': 'def g(x): return x+1',
                'token_count': 10,
            }
        ]
        
        conciseness = self.tracker.calculate_conciseness(context_items)
        self.assertGreater(conciseness, 0.5)
        
        # Low conciseness (verbose code with comments)
        context_items = [
            {
                'content': """# This is a function
def f(x):
    # Multiply by 2
    return x * 2""",
                'token_count': 10,
            }
        ]
        
        conciseness = self.tracker.calculate_conciseness(context_items)
        self.assertLess(conciseness, 0.5)
        
        # Empty context
        conciseness = self.tracker.calculate_conciseness([])
        self.assertEqual(conciseness, 0.0)
    
    def test_calculate_diversity(self):
        """Test diversity calculation"""
        # High diversity (all different sources)
        context_items = [
            {'source': 'file1.py'},
            {'source': 'file2.py'},
            {'source': 'file3.py'}
        ]
        
        diversity = self.tracker.calculate_diversity(context_items)
        self.assertEqual(diversity, 1.0)
        
        # Low diversity (all same source)
        context_items = [
            {'source': 'file1.py'},
            {'source': 'file1.py'},
            {'source': 'file1.py'}
        ]
        
        diversity = self.tracker.calculate_diversity(context_items)
        self.assertAlmostEqual(diversity, 0.33, places=2)
        
        # Medium diversity
        context_items = [
            {'source': 'file1.py'},
            {'source': 'file1.py'},
            {'source': 'file2.py'}
        ]
        
        diversity = self.tracker.calculate_diversity(context_items)
        self.assertAlmostEqual(diversity, 0.67, places=2)
        
        # Empty context
        diversity = self.tracker.calculate_diversity([])
        self.assertEqual(diversity, 0.0)
    
    def test_calculate_overall_quality(self):
        """Test overall quality calculation"""
        # High quality
        metrics = {
            QualityMetric.COMPLETENESS: 0.9,
            QualityMetric.RELEVANCE: 0.85,
            QualityMetric.FRESHNESS: 0.8,
            QualityMetric.CONCISENESS: 0.75,
            QualityMetric.DIVERSITY: 0.7
        }
        
        quality = self.tracker.calculate_overall_quality(metrics)
        self.assertGreater(quality, 0.8)
        
        # Low quality
        metrics = {
            QualityMetric.COMPLETENESS: 0.3,
            QualityMetric.RELEVANCE: 0.4,
            QualityMetric.FRESHNESS: 0.5,
            QualityMetric.CONCISENESS: 0.3,
            QualityMetric.DIVERSITY: 0.4
        }
        
        quality = self.tracker.calculate_overall_quality(metrics)
        self.assertLess(quality, 0.5)
        
        # Empty metrics
        quality = self.tracker.calculate_overall_quality({})
        self.assertEqual(quality, 0.0)
    
    def test_record_context_quality(self):
        """Test recording context quality"""
        now = datetime.now()
        
        # Sample context data
        required_context = ['file1.py', 'file2.py', 'file3.py']
        provided_context = ['file1.py', 'file2.py']
        context_items = [
            {
                'source': 'file1.py',
                'content': 'def f(x): return x',
                'relevance_score': 0.9,
                'timestamp': (now - timedelta(hours=1)).isoformat(),
                'token_count': 10
            },
            {
                'source': 'file2.py',
                'content': 'def g(x): return x*2',
                'relevance_score': 0.85,
                'timestamp': (now - timedelta(hours=2)).isoformat(),
                'token_count': 12
            }
        ]
        
        # Record quality
        metrics = self.tracker.record_context_quality(
            task_id='task_001',
            task_type='implementation',
            required_context=required_context,
            provided_context=provided_context,
            context_items=context_items,
            success=True,
            attempts=1,
            execution_time_seconds=5.0
        )
        
        # Verify metrics object
        self.assertIsInstance(metrics, ContextQualityMetrics)
        self.assertEqual(metrics.task_id, 'task_001')
        self.assertEqual(metrics.task_type, 'implementation')
        self.assertTrue(metrics.success)
        self.assertEqual(metrics.attempts, 1)
        self.assertEqual(metrics.execution_time_seconds, 5.0)
        
        # Verify individual metrics
        self.assertGreater(metrics.completeness, 0.0)
        self.assertLessEqual(metrics.completeness, 1.0)
        self.assertGreater(metrics.relevance, 0.0)
        self.assertLessEqual(metrics.relevance, 1.0)
        
        # Verify metadata
        self.assertEqual(metrics.context_items_count, 2)
        self.assertGreater(metrics.total_tokens, 0)
        self.assertEqual(metrics.unique_sources, 2)
    
    def test_get_quality_metrics(self):
        """Test retrieving quality metrics"""
        # Record some test data
        self.tracker.record_context_quality(
            task_id='task_001',
            task_type='implementation',
            required_context=['file1.py'],
            provided_context=['file1.py'],
            context_items=[{
                'source': 'file1.py',
                'content': 'code',
                'relevance_score': 0.9,
                'timestamp': datetime.now().isoformat(),
                'token_count': 10
            }],
            success=True
        )
        
        self.tracker.record_context_quality(
            task_id='task_002',
            task_type='planning',
            required_context=['file2.py'],
            provided_context=['file2.py'],
            context_items=[{
                'source': 'file2.py',
                'content': 'code',
                'relevance_score': 0.85,
                'timestamp': datetime.now().isoformat(),
                'token_count': 15
            }],
            success=False
        )
        
        # Get all metrics
        all_metrics = self.tracker.get_quality_metrics()
        self.assertEqual(len(all_metrics), 2)
        
        # Filter by task type
        impl_metrics = self.tracker.get_quality_metrics(task_type='implementation')
        self.assertEqual(len(impl_metrics), 1)
        self.assertEqual(impl_metrics[0].task_type, 'implementation')
        
        # Filter by task ID
        task_metrics = self.tracker.get_quality_metrics(task_id='task_001')
        self.assertEqual(len(task_metrics), 1)
        self.assertEqual(task_metrics[0].task_id, 'task_001')
    
    def test_generate_quality_report(self):
        """Test generating quality report"""
        # Record multiple tasks with varying quality
        for i in range(10):
            quality = 0.5 + (i * 0.05)  # 0.5 to 0.95
            success = quality > 0.7  # High quality = success
            
            self.tracker.record_context_quality(
                task_id=f'task_{i:03d}',
                task_type='implementation',
                required_context=['file1.py', 'file2.py'],
                provided_context=['file1.py'] if quality < 0.8 else ['file1.py', 'file2.py'],
                context_items=[{
                    'source': 'file1.py',
                    'content': 'code',
                    'relevance_score': quality,
                    'timestamp': (datetime.now() - timedelta(days=i)).isoformat(),
                    'token_count': 10 + i
                }],
                success=success,
                attempts=1 + (0 if success else 1),
                execution_time_seconds=5.0 + i
            )
        
        # Generate report
        report = self.tracker.generate_quality_report()
        
        # Verify report structure
        self.assertIsInstance(report, QualityReport)
        self.assertEqual(report.total_tasks, 10)
        
        # Verify quality averages
        self.assertGreater(report.avg_overall_quality, 0.0)
        self.assertLessEqual(report.avg_overall_quality, 1.0)
        
        # Verify recommendations exist if quality is low
        if report.avg_completeness < 0.75:
            self.assertGreater(len(report.recommendations), 0)
        
        # Verify trend calculation
        self.assertIn(report.quality_trend, ['IMPROVING', 'STABLE', 'DECLINING'])
    
    def test_quality_threshold_levels(self):
        """Test quality threshold classification"""
        threshold = QualityThreshold()
        
        # Test low quality
        self.assertEqual(threshold.get_quality_level(0.3), "LOW")
        self.assertEqual(threshold.get_quality_level(0.49), "LOW")
        
        # Test medium quality
        self.assertEqual(threshold.get_quality_level(0.5), "MEDIUM")
        self.assertEqual(threshold.get_quality_level(0.7), "MEDIUM")
        
        # Test high quality
        self.assertEqual(threshold.get_quality_level(0.76), "HIGH")
        self.assertEqual(threshold.get_quality_level(0.89), "HIGH")
        
        # Test excellent quality
        self.assertEqual(threshold.get_quality_level(0.9), "EXCELLENT")
        self.assertEqual(threshold.get_quality_level(1.0), "EXCELLENT")
    
    def test_get_correlation_data(self):
        """Test getting quality correlation data"""
        # Record tasks with different quality levels - need multiple tasks per level
        # Low quality (< 0.5): 0.3, 0.4
        self.tracker.record_context_quality(
            task_id='task_low1',
            task_type='implementation',
            required_context=['file1.py'],
            provided_context=['file1.py'],
            context_items=[{
                'source': 'file1.py',
                'content': 'code',
                'relevance_score': 0.3,
                'timestamp': datetime.now().isoformat(),
                'token_count': 10
            }],
            success=False
        )
        
        # Medium quality (0.5 - 0.75): 0.6, 0.7
        self.tracker.record_context_quality(
            task_id='task_medium1',
            task_type='implementation',
            required_context=['file1.py'],
            provided_context=['file1.py'],
            context_items=[{
                'source': 'file1.py',
                'content': 'code',
                'relevance_score': 0.6,
                'timestamp': datetime.now().isoformat(),
                'token_count': 10
            }],
            success=True
        )
        
        # High quality (0.75 - 0.9): 0.8, 0.85
        self.tracker.record_context_quality(
            task_id='task_high1',
            task_type='implementation',
            required_context=['file1.py'],
            provided_context=['file1.py'],
            context_items=[{
                'source': 'file1.py',
                'content': 'code',
                'relevance_score': 0.8,
                'timestamp': datetime.now().isoformat(),
                'token_count': 10
            }],
            success=True
        )
        
        # Excellent quality (> 0.9): 0.95, 0.97
        self.tracker.record_context_quality(
            task_id='task_excellent1',
            task_type='implementation',
            required_context=['file1.py'],
            provided_context=['file1.py'],
            context_items=[{
                'source': 'file1.py',
                'content': 'code',
                'relevance_score': 0.95,
                'timestamp': datetime.now().isoformat(),
                'token_count': 10
            }],
            success=True
        )
        
        # Get correlation data
        correlation = self.tracker.get_correlation_data()
        
        # Verify structure - check that we have some quality levels
        self.assertGreater(len(correlation), 0)
        
        # Verify correlation fields for existing levels
        for level in correlation.values():
            self.assertIn('total_tasks', level)
            self.assertIn('success_rate', level)
            self.assertIn('avg_attempts', level)
            self.assertIn('avg_execution_time', level)
            self.assertGreater(level['total_tasks'], 0)
    
    def test_get_quality_trend(self):
        """Test getting quality trend over time"""
        # Record tasks over several days
        base_time = datetime.now() - timedelta(days=10)
        
        for i in range(10):
            quality = 0.6 + (i * 0.03)  # Improving over time
            
            self.tracker.record_context_quality(
                task_id=f'task_trend_{i}',
                task_type='implementation',
                required_context=['file1.py'],
                provided_context=['file1.py'],
                context_items=[{
                    'source': 'file1.py',
                    'content': 'code',
                    'relevance_score': quality,
                    'timestamp': (base_time + timedelta(days=i)).isoformat(),
                    'token_count': 10
                }],
                success=True
            )
        
        # Get trend data
        trend = self.tracker.get_quality_trend(days=10)
        
        # Verify structure
        self.assertIn('dates', trend)
        self.assertIn('completeness', trend)
        self.assertIn('relevance', trend)
        self.assertIn('freshness', trend)
        self.assertIn('conciseness', trend)
        self.assertIn('diversity', trend)
        self.assertIn('overall_quality', trend)
        
        # Verify data length
        self.assertGreater(len(trend['dates']), 0)
        self.assertEqual(len(trend['dates']), len(trend['overall_quality']))
    
    def test_export_quality_data_json(self):
        """Test exporting quality data to JSON"""
        # Record some test data
        self.tracker.record_context_quality(
            task_id='task_001',
            task_type='implementation',
            required_context=['file1.py'],
            provided_context=['file1.py'],
            context_items=[{
                'source': 'file1.py',
                'content': 'code',
                'relevance_score': 0.9,
                'timestamp': datetime.now().isoformat(),
                'token_count': 10
            }],
            success=True
        )
        
        # Export to JSON
        export_path = os.path.join(self.test_dir, 'export.json')
        self.tracker.export_quality_data(export_path, format='json')
        
        # Verify file exists
        self.assertTrue(os.path.exists(export_path))
        
        # Verify JSON structure
        with open(export_path, 'r') as f:
            data = json.load(f)
        
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)
        self.assertIn('task_id', data[0])
        self.assertIn('overall_quality', data[0])
    
    def test_export_quality_data_csv(self):
        """Test exporting quality data to CSV"""
        # Record some test data
        self.tracker.record_context_quality(
            task_id='task_001',
            task_type='implementation',
            required_context=['file1.py'],
            provided_context=['file1.py'],
            context_items=[{
                'source': 'file1.py',
                'content': 'code',
                'relevance_score': 0.9,
                'timestamp': datetime.now().isoformat(),
                'token_count': 10
            }],
            success=True
        )
        
        # Export to CSV
        export_path = os.path.join(self.test_dir, 'export.csv')
        self.tracker.export_quality_data(export_path, format='csv')
        
        # Verify file exists
        self.assertTrue(os.path.exists(export_path))
        
        # Verify CSV structure
        import csv
        with open(export_path, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        self.assertGreater(len(rows), 0)
        self.assertIn('task_id', rows[0])
        self.assertIn('overall_quality', rows[0])
    
    def test_clear_old_data(self):
        """Test clearing old quality data"""
        # Clear existing data first
        self.tracker.clear_old_data(days=0)
        
        # Record old data - need to force old timestamp by modifying the record
        self.tracker.record_context_quality(
            task_id='old_task',
            task_type='implementation',
            required_context=['file1.py'],
            provided_context=['file1.py'],
            context_items=[{
                'source': 'file1.py',
                'content': 'code',
                'relevance_score': 0.9,
                'timestamp': (datetime.now() - timedelta(days=100)).isoformat(),
                'token_count': 10
            }],
            success=True
        )
        
        # Manually update timestamp to be old
        old_time = (datetime.now() - timedelta(days=100)).isoformat()
        cursor = self.tracker.conn.cursor()
        cursor.execute(
            "UPDATE context_quality SET timestamp = ? WHERE task_id = ?",
            (old_time, 'old_task')
        )
        self.tracker.conn.commit()
        
        # Record recent data
        self.tracker.record_context_quality(
            task_id='recent_task',
            task_type='implementation',
            required_context=['file1.py'],
            provided_context=['file1.py'],
            context_items=[{
                'source': 'file1.py',
                'content': 'code',
                'relevance_score': 0.9,
                'timestamp': datetime.now().isoformat(),
                'token_count': 10
            }],
            success=True
        )
        
        # Clear old data (older than 90 days)
        deleted = self.tracker.clear_old_data(days=90)
        
        # Verify deletion
        self.assertEqual(deleted, 1)
        
        # Verify only recent data remains
        all_metrics = self.tracker.get_quality_metrics()
        self.assertEqual(len(all_metrics), 1)
        self.assertEqual(all_metrics[0].task_id, 'recent_task')
    
    def test_quality_metrics_to_dict(self):
        """Test converting ContextQualityMetrics to dictionary"""
        now = datetime.now()
        
        metrics = ContextQualityMetrics(
            task_id='task_001',
            task_type='implementation',
            timestamp=now,
            completeness=0.8,
            relevance=0.85,
            freshness=0.75,
            conciseness=0.9,
            diversity=0.7,
            overall_quality=0.8,
            context_items_count=5,
            total_tokens=100,
            unique_sources=3,
            success=True,
            attempts=2,
            execution_time_seconds=10.5
        )
        
        # Convert to dict
        data = metrics.to_dict()
        
        # Verify all fields present
        self.assertEqual(data['task_id'], 'task_001')
        self.assertEqual(data['task_type'], 'implementation')
        self.assertEqual(data['overall_quality'], 0.8)
        self.assertEqual(data['success'], True)
        
        # Verify timestamp is ISO format string
        self.assertIsInstance(data['timestamp'], str)
    
    def test_quality_report_to_dict(self):
        """Test converting QualityReport to dictionary"""
        now = datetime.now()
        
        report = QualityReport(
            period_start=now - timedelta(days=30),
            period_end=now,
            total_tasks=10,
            successful_tasks=8,
            avg_completeness=0.8,
            avg_relevance=0.85,
            avg_freshness=0.75,
            avg_conciseness=0.9,
            avg_diversity=0.7,
            avg_overall_quality=0.8,
            success_rate_low_quality=0.5,
            success_rate_medium_quality=0.7,
            success_rate_high_quality=0.9,
            success_rate_excellent_quality=1.0,
            quality_trend="IMPROVING",
            quality_change_rate=15.5,
            recommendations=["Improve freshness", "Add more context"]
        )
        
        # Convert to dict
        data = report.to_dict()
        
        # Verify all fields present
        self.assertEqual(data['total_tasks'], 10)
        self.assertEqual(data['successful_tasks'], 8)
        self.assertEqual(data['quality_trend'], "IMPROVING")
        self.assertEqual(len(data['recommendations']), 2)
        
        # Verify timestamps are ISO format strings
        self.assertIsInstance(data['period_start'], str)
        self.assertIsInstance(data['period_end'], str)


class TestContextQualityTrackerIntegration(unittest.TestCase):
    """Integration tests for ContextQualityTracker"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "integration_test.db")
        
        self.tracker = ContextQualityTracker(db_path=self.db_path)
        self.tracker.connect()
    
    def tearDown(self):
        """Clean up test environment"""
        self.tracker.close()
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_full_workflow(self):
        """Test complete workflow from recording to reporting"""
        # Simulate multiple tasks
        tasks = [
            {
                'task_id': 'task_001',
                'task_type': 'implementation',
                'required': ['file1.py', 'file2.py', 'file3.py'],
                'provided': ['file1.py', 'file2.py'],
                'relevance': 0.7,
                'success': False,
                'attempts': 3
            },
            {
                'task_id': 'task_002',
                'task_type': 'implementation',
                'required': ['file4.py', 'file5.py'],
                'provided': ['file4.py', 'file5.py'],
                'relevance': 0.9,
                'success': True,
                'attempts': 1
            },
            {
                'task_id': 'task_003',
                'task_type': 'planning',
                'required': ['file6.py'],
                'provided': ['file6.py'],
                'relevance': 0.85,
                'success': True,
                'attempts': 1
            }
        ]
        
        # Record all tasks
        for task in tasks:
            self.tracker.record_context_quality(
                task_id=task['task_id'],
                task_type=task['task_type'],
                required_context=task['required'],
                provided_context=task['provided'],
                context_items=[{
                    'source': f['source'],
                    'content': 'code',
                    'relevance_score': task['relevance'],
                    'timestamp': datetime.now().isoformat(),
                    'token_count': 10
                } for f in [
                    {'source': f} for f in task['provided']
                ]],
                success=task['success'],
                attempts=task['attempts'],
                execution_time_seconds=5.0 * task['attempts']
            )
        
        # Generate report
        report = self.tracker.generate_quality_report()
        
        # Verify report
        self.assertEqual(report.total_tasks, 3)
        self.assertEqual(report.successful_tasks, 2)
        
        # Verify success rate is between 0 and 1
        overall_success_rate = report.successful_tasks / report.total_tasks
        self.assertEqual(overall_success_rate, 2.0/3.0)
        
        # Verify quality metrics are reasonable
        self.assertGreater(report.avg_overall_quality, 0.0)
        self.assertLessEqual(report.avg_overall_quality, 1.0)
        
        # Export data
        json_path = os.path.join(self.test_dir, 'full_workflow.json')
        self.tracker.export_quality_data(json_path, format='json')
        self.assertTrue(os.path.exists(json_path))


if __name__ == '__main__':
    unittest.main()