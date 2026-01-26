"""
Unit tests for Progress Tracker

Tests for the ProgressTracker class including:
- Real-time progress tracking
- Progress validation against expected rates
- Stagnation detection
- Regression detection
- Alert system
- Report generation
"""

import unittest
import tempfile
import os
import json
from datetime import datetime, timedelta

from v5.logic.progress_tracker import (
    ProgressTracker,
    ProgressMetrics,
    CodeProgressMetrics,
    TaskProgressMetrics,
    SessionProgressMetrics,
    ProjectProgressMetrics,
    ProgressMetricType,
    CustomMetric,
    ProgressThresholds
)


class TestProgressTracker(unittest.TestCase):
    """Test cases for ProgressTracker class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.tracker = ProgressTracker(task_id="test_task_001")
        
    def test_initialization(self):
        """Test tracker initialization"""
        self.assertEqual(self.tracker.task_id, "test_task_001")
        self.assertFalse(self.tracker.is_tracking)
        self.assertEqual(self.tracker.ops_without_progress, 0)
        self.assertEqual(self.tracker.last_progress, 0.0)
        self.assertIsNone(self.tracker.start_time)
        self.assertEqual(len(self.tracker.alerts), 0)
        self.assertIsNone(self.tracker.baseline_metrics)
        self.assertEqual(len(self.tracker.historical_metrics), 0)
        
    def test_start_tracking(self):
        """Test starting progress tracking"""
        self.tracker.start_tracking()
        
        self.assertTrue(self.tracker.is_tracking)
        self.assertIsNotNone(self.tracker.start_time)
        self.assertEqual(self.tracker.ops_without_progress, 0)
        self.assertEqual(self.tracker.last_progress, 0.0)
        self.assertEqual(len(self.tracker.alerts), 0)
        
    def test_start_tracking_with_task_id_override(self):
        """Test starting tracking with task ID override"""
        self.tracker.start_tracking(task_id="override_task")
        
        self.assertEqual(self.tracker.task_id, "override_task")
        
    def test_stop_tracking(self):
        """Test stopping progress tracking"""
        self.tracker.start_tracking()
        self.tracker.stop_tracking()
        
        self.assertFalse(self.tracker.is_tracking)
        
    def test_update_progress_first_call_sets_baseline(self):
        """Test that first update_progress call sets baseline"""
        self.tracker.start_tracking()
        
        code_metrics = CodeProgressMetrics(lines_added=10)
        self.tracker.update_progress(code_metrics=code_metrics)
        
        self.assertIsNotNone(self.tracker.baseline_metrics)
        self.assertEqual(len(self.tracker.historical_metrics), 1)
        
    def test_update_progress_subsequent_calls(self):
        """Test subsequent update_progress calls"""
        self.tracker.start_tracking()
        
        # First call
        code_metrics1 = CodeProgressMetrics(lines_added=10)
        self.tracker.update_progress(code_metrics=code_metrics1)
        
        # Second call
        code_metrics2 = CodeProgressMetrics(lines_added=20)
        self.tracker.update_progress(code_metrics=code_metrics2)
        
        self.assertEqual(len(self.tracker.historical_metrics), 2)
        self.assertEqual(self.tracker.metrics.code_metrics.lines_added, 20)
        
    def test_update_progress_when_not_tracking(self):
        """Test that update_progress does nothing when not tracking"""
        code_metrics = CodeProgressMetrics(lines_added=10)
        self.tracker.update_progress(code_metrics=code_metrics)
        
        self.assertIsNone(self.tracker.baseline_metrics)
        self.assertEqual(len(self.tracker.historical_metrics), 0)
        
    def test_update_progress_all_metric_types(self):
        """Test updating all metric types"""
        self.tracker.start_tracking()
        
        code_metrics = CodeProgressMetrics(lines_added=10, tests_passing=5)
        task_metrics = TaskProgressMetrics(subtasks_completed=2, subtasks_total=5)
        session_metrics = SessionProgressMetrics(tasks_completed=1)
        project_metrics = ProjectProgressMetrics(features_completed=1)
        
        self.tracker.update_progress(
            code_metrics=code_metrics,
            task_metrics=task_metrics,
            session_metrics=session_metrics,
            project_metrics=project_metrics
        )
        
        self.assertEqual(self.tracker.metrics.code_metrics.lines_added, 10)
        self.assertEqual(self.tracker.metrics.task_metrics.subtasks_completed, 2)
        self.assertEqual(self.tracker.metrics.session_metrics.tasks_completed, 1)
        self.assertEqual(self.tracker.metrics.project_metrics.features_completed, 1)
        
    def test_update_progress_with_custom_metrics(self):
        """Test updating with custom metrics"""
        self.tracker.start_tracking()
        
        custom_metric = CustomMetric(
            name="custom_test",
            description="Test custom metric",
            metric_type=ProgressMetricType.CUSTOM,
            value=75.0,
            unit="%"
        )
        
        self.tracker.update_progress(custom_metrics=[custom_metric])
        
        self.assertEqual(len(self.tracker.metrics.custom_metrics), 1)
        self.assertEqual(self.tracker.metrics.custom_metrics[0].name, "custom_test")
        
    def test_check_progress_when_not_tracking(self):
        """Test check_progress when not tracking"""
        result = self.tracker.check_progress()
        
        self.assertEqual(result['status'], 'not_tracking')
        self.assertFalse(result['is_adequate'])
        
    def test_check_progress_adequate(self):
        """Test check_progress with adequate progress"""
        self.tracker.start_tracking()
        
        # Baseline: 10 lines
        code_metrics1 = CodeProgressMetrics(lines_added=10)
        self.tracker.update_progress(code_metrics=code_metrics1)
        
        # Current: 50 lines (400% increase = 100% capped)
        code_metrics2 = CodeProgressMetrics(lines_added=50)
        self.tracker.update_progress(code_metrics=code_metrics2)
        
        result = self.tracker.check_progress()
        
        # Status should be adequate (100% meets expected threshold)
        self.assertEqual(result['status'], 'adequate')
        self.assertTrue(result['is_adequate'])
        self.assertIn('details', result)
        
    def test_check_progress_below_minimal(self):
        """Test check_progress with progress below minimal threshold"""
        self.tracker.start_tracking()
        
        # Very low progress (1 line added)
        code_metrics = CodeProgressMetrics(lines_added=1)
        self.tracker.update_progress(code_metrics=code_metrics)
        
        result = self.tracker.check_progress()
        
        # Should have generated alert for below minimal progress
        self.assertGreater(len(self.tracker.alerts), 0)
        
    def test_check_progress_with_stagnation_warning(self):
        """Test check_progress with stagnation warning"""
        self.tracker.start_tracking()
        
        # Simulate stagnation
        for _ in range(3):
            self.tracker.increment_ops_without_progress()
        
        result = self.tracker.check_progress()
        
        self.assertIn('stagnation', result)
        self.assertEqual(result['stagnation'], 'warning')
        
    def test_check_progress_with_stagnation_critical(self):
        """Test check_progress with critical stagnation"""
        self.tracker.start_tracking()
        
        # Simulate critical stagnation
        for _ in range(5):
            self.tracker.increment_ops_without_progress()
        
        result = self.tracker.check_progress()
        
        self.assertIn('stagnation', result)
        self.assertEqual(result['stagnation'], 'critical')
        self.assertFalse(result['is_adequate'])
        
    def test_detect_stagnation_none(self):
        """Test detect_stagnation with no stagnation"""
        result = self.tracker.detect_stagnation()
        
        self.assertEqual(result['status'], 'none')
        self.assertEqual(result['severity'], 'none')
        self.assertEqual(result['ops_without_progress'], 0)
        
    def test_detect_stagnation_warning(self):
        """Test detect_stagnation with warning level"""
        for _ in range(3):
            self.tracker.increment_ops_without_progress()
        
        result = self.tracker.detect_stagnation()
        
        self.assertEqual(result['status'], 'warning')
        self.assertEqual(result['severity'], 'warning')
        self.assertIn('message', result)
        self.assertGreater(len(self.tracker.alerts), 0)
        
    def test_detect_stagnation_critical(self):
        """Test detect_stagnation with critical level"""
        for _ in range(5):
            self.tracker.increment_ops_without_progress()
        
        result = self.tracker.detect_stagnation()
        
        self.assertEqual(result['status'], 'critical')
        self.assertEqual(result['severity'], 'critical')
        self.assertIn('message', result)
        self.assertGreater(len(self.tracker.alerts), 0)
        
    def test_detect_stagnation_custom_threshold(self):
        """Test detect_stagnation with custom threshold"""
        for _ in range(2):
            self.tracker.increment_ops_without_progress()
        
        result = self.tracker.detect_stagnation(threshold=2)
        
        self.assertEqual(result['status'], 'warning')
        
    def test_detect_regression_no_regression(self):
        """Test detect_regression with no regression"""
        self.tracker.start_tracking()
        
        code_metrics = CodeProgressMetrics(lines_added=10)
        self.tracker.update_progress(code_metrics=code_metrics)
        
        result = self.tracker.detect_regression()
        
        self.assertFalse(result['has_regression'])
        self.assertEqual(len(result['regressions']), 0)
        
    def test_detect_regression_with_regression(self):
        """Test detect_regression detecting regression"""
        self.tracker.start_tracking()
        
        # Baseline: 10 lines
        code_metrics0 = CodeProgressMetrics(lines_added=10)
        self.tracker.update_progress(code_metrics=code_metrics0)
        
        # Progress: 100 lines (900% increase = 100% capped)
        code_metrics1 = CodeProgressMetrics(lines_added=100)
        self.tracker.update_progress(code_metrics=code_metrics1)
        
        # Regression: 50 lines (400% increase from baseline = 100% capped)
        # Wait, this won't show regression. Let me fix the test.
        # Actually: 100 lines is at index 1, 50 lines is at index 2
        # Progress at index 1: (100-10)/10 = 900% = 100%
        # Progress at index 2: (50-10)/10 = 400% = 100%
        # So no regression. The test needs different data.
        
        # Let's use a real regression:
        # Baseline: 10 lines
        # Update 1: 50 lines (400% = 100%)
        # Update 2: 20 lines (100% = 100%)
        # Still no regression because both cap at 100%
        
        # The issue is the capping at 100%. Once we reach 100%, we can't detect regression.
        # This test needs to not reach 100%.
        
        # Let's use:
        # Baseline: 100 lines
        code_metrics0 = CodeProgressMetrics(lines_added=100)
        self.tracker.update_progress(code_metrics=code_metrics0)
        
        # Progress: 150 lines (50% increase)
        code_metrics1 = CodeProgressMetrics(lines_added=150)
        self.tracker.update_progress(code_metrics=code_metrics1)
        
        # Regression: 120 lines (20% decrease from 50%)
        code_metrics2 = CodeProgressMetrics(lines_added=120)
        self.tracker.update_progress(code_metrics=code_metrics2)
        
        result = self.tracker.detect_regression()
        
        # Should detect regression (150 -> 120 lines)
        self.assertTrue(len(result['regressions']) > 0)
        
    def test_detect_regression_specific_metric_type(self):
        """Test detect_regression for specific metric type"""
        self.tracker.start_tracking()
        
        # Baseline: 100 lines
        code_metrics0 = CodeProgressMetrics(lines_added=100)
        self.tracker.update_progress(code_metrics=code_metrics0)
        
        # Progress: 150 lines (50% increase)
        code_metrics1 = CodeProgressMetrics(lines_added=150)
        self.tracker.update_progress(code_metrics=code_metrics1)
        
        # Regression: 120 lines (20% decrease)
        code_metrics2 = CodeProgressMetrics(lines_added=120)
        self.tracker.update_progress(code_metrics=code_metrics2)
        
        result = self.tracker.detect_regression(metric_type=ProgressMetricType.CODE)
        
        self.assertIn('code', [r['metric_type'] for r in result['regressions']])
        
    def test_increment_ops_without_progress(self):
        """Test incrementing ops without progress counter"""
        self.assertEqual(self.tracker.ops_without_progress, 0)
        
        self.tracker.increment_ops_without_progress()
        self.assertEqual(self.tracker.ops_without_progress, 1)
        
        self.tracker.increment_ops_without_progress()
        self.assertEqual(self.tracker.ops_without_progress, 2)
        
    def test_reset_ops_without_progress(self):
        """Test resetting ops without progress counter"""
        self.tracker.increment_ops_without_progress()
        self.tracker.increment_ops_without_progress()
        
        self.tracker.reset_ops_without_progress()
        
        self.assertEqual(self.tracker.ops_without_progress, 0)
        
    def test_generate_alert(self):
        """Test alert generation"""
        self.tracker.start_tracking()
        
        initial_alert_count = len(self.tracker.alerts)
        
        # Generate an alert (private method, but we can trigger it via detect_stagnation)
        for _ in range(3):
            self.tracker.increment_ops_without_progress()
        self.tracker.detect_stagnation()
        
        self.assertGreater(len(self.tracker.alerts), initial_alert_count)
        
        # Check alert structure
        alert = self.tracker.alerts[-1]
        self.assertIn('timestamp', alert)
        self.assertIn('task_id', alert)
        self.assertIn('type', alert)
        self.assertIn('severity', alert)
        self.assertIn('message', alert)
        
    def test_get_alerts_no_filter(self):
        """Test getting alerts without filter"""
        self.tracker.start_tracking()
        
        for _ in range(3):
            self.tracker.increment_ops_without_progress()
        self.tracker.detect_stagnation()
        
        alerts = self.tracker.get_alerts()
        
        self.assertEqual(len(alerts), len(self.tracker.alerts))
        
    def test_get_alerts_with_severity_filter(self):
        """Test getting alerts filtered by severity"""
        self.tracker.start_tracking()
        
        # Generate warning alert
        for _ in range(3):
            self.tracker.increment_ops_without_progress()
        self.tracker.detect_stagnation()
        
        # Generate critical alert
        for _ in range(2):
            self.tracker.increment_ops_without_progress()
        self.tracker.detect_stagnation()
        
        critical_alerts = self.tracker.get_alerts(severity='critical')
        
        for alert in critical_alerts:
            self.assertEqual(alert['severity'], 'critical')
        
    def test_get_alerts_with_type_filter(self):
        """Test getting alerts filtered by type"""
        self.tracker.start_tracking()
        
        for _ in range(3):
            self.tracker.increment_ops_without_progress()
        self.tracker.detect_stagnation()
        
        stagnation_alerts = self.tracker.get_alerts(alert_type='stagnation_warning')
        
        for alert in stagnation_alerts:
            self.assertEqual(alert['type'], 'stagnation_warning')
            
    def test_clear_alerts(self):
        """Test clearing all alerts"""
        self.tracker.start_tracking()
        
        for _ in range(3):
            self.tracker.increment_ops_without_progress()
        self.tracker.detect_stagnation()
        
        self.assertGreater(len(self.tracker.alerts), 0)
        
        self.tracker.clear_alerts()
        
        self.assertEqual(len(self.tracker.alerts), 0)
        
    def test_get_report_basic(self):
        """Test generating basic progress report"""
        self.tracker.start_tracking()
        
        code_metrics = CodeProgressMetrics(lines_added=100)
        self.tracker.update_progress(code_metrics=code_metrics)
        
        report = self.tracker.get_report()
        
        self.assertIn('task_id', report)
        self.assertIn('is_tracking', report)
        self.assertIn('start_time', report)
        self.assertIn('current_time', report)
        self.assertIn('duration_seconds', report)
        self.assertIn('metrics', report)
        self.assertIn('progress_summary', report)
        self.assertIn('stagnation', report)
        self.assertIn('regression', report)
        
    def test_get_report_with_historical(self):
        """Test generating report with historical metrics"""
        self.tracker.start_tracking()
        
        code_metrics1 = CodeProgressMetrics(lines_added=50)
        self.tracker.update_progress(code_metrics=code_metrics1)
        
        code_metrics2 = CodeProgressMetrics(lines_added=100)
        self.tracker.update_progress(code_metrics=code_metrics2)
        
        report = self.tracker.get_report(include_historical=True)
        
        self.assertIn('historical_metrics', report)
        self.assertEqual(len(report['historical_metrics']), 2)
        
    def test_get_report_without_historical(self):
        """Test generating report without historical metrics"""
        self.tracker.start_tracking()
        
        code_metrics = CodeProgressMetrics(lines_added=100)
        self.tracker.update_progress(code_metrics=code_metrics)
        
        report = self.tracker.get_report(include_historical=False)
        
        self.assertNotIn('historical_metrics', report)
        
    def test_get_report_with_alerts(self):
        """Test generating report with alerts"""
        self.tracker.start_tracking()
        
        for _ in range(3):
            self.tracker.increment_ops_without_progress()
        self.tracker.detect_stagnation()
        
        report = self.tracker.get_report(include_alerts=True)
        
        self.assertIn('alerts', report)
        self.assertGreater(len(report['alerts']), 0)
        
    def test_get_report_without_alerts(self):
        """Test generating report without alerts"""
        self.tracker.start_tracking()
        
        report = self.tracker.get_report(include_alerts=False)
        
        self.assertNotIn('alerts', report)
        
    def test_get_summary(self):
        """Test getting progress summary"""
        self.tracker.start_tracking()
        
        for _ in range(3):
            self.tracker.increment_ops_without_progress()
        self.tracker.detect_stagnation()
        
        summary = self.tracker.get_summary()
        
        self.assertIn('task_id', summary)
        self.assertIn('is_tracking', summary)
        self.assertIn('overall_progress', summary)
        self.assertIn('ops_without_progress', summary)
        self.assertIn('total_alerts', summary)
        self.assertIn('critical_alerts', summary)
        self.assertIn('status', summary)
        
    def test_get_summary_status_adequate(self):
        """Test summary status when progress is adequate"""
        self.tracker.start_tracking()
        
        code_metrics = CodeProgressMetrics(lines_added=100)
        self.tracker.update_progress(code_metrics=code_metrics)
        
        summary = self.tracker.get_summary()
        
        self.assertEqual(summary['status'], 'adequate')
        
    def test_get_summary_status_stagnation(self):
        """Test summary status when stagnation detected"""
        self.tracker.start_tracking()
        
        # Add some initial progress
        code_metrics = CodeProgressMetrics(lines_added=100)
        self.tracker.update_progress(code_metrics=code_metrics)
        
        # Simulate stagnation
        for _ in range(3):
            self.tracker.increment_ops_without_progress()
            
        summary = self.tracker.get_summary()
        
        # Status should be warning due to stagnation
        self.assertEqual(summary['status'], 'warning')
        
    def test_export_to_json(self):
        """Test exporting progress to JSON file"""
        self.tracker.start_tracking()
        
        code_metrics = CodeProgressMetrics(lines_added=100)
        self.tracker.update_progress(code_metrics=code_metrics)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            self.tracker.export_to_json(temp_path)
            
            # Verify file exists and is valid JSON
            self.assertTrue(os.path.exists(temp_path))
            
            with open(temp_path, 'r') as f:
                data = json.load(f)
                
            self.assertIn('task_id', data)
            self.assertIn('metrics', data)
            self.assertIn('progress_summary', data)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
    def test_load_from_json(self):
        """Test loading progress from JSON file"""
        self.tracker.start_tracking()
        
        code_metrics = CodeProgressMetrics(lines_added=100, tests_passing=5)
        task_metrics = TaskProgressMetrics(subtasks_completed=2, subtasks_total=5)
        
        self.tracker.update_progress(
            code_metrics=code_metrics,
            task_metrics=task_metrics
        )
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            # Export
            self.tracker.export_to_json(temp_path)
            
            # Create new tracker and load
            new_tracker = ProgressTracker()
            new_tracker.load_from_json(temp_path)
            
            # Verify loaded data
            self.assertEqual(new_tracker.task_id, self.tracker.task_id)
            self.assertTrue(new_tracker.is_tracking)
            self.assertEqual(new_tracker.metrics.code_metrics.lines_added, 100)
            self.assertEqual(new_tracker.metrics.task_metrics.subtasks_completed, 2)
            
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
    def test_calculate_overall_progress(self):
        """Test overall progress calculation"""
        self.tracker.start_tracking()
        
        # Set baseline
        code_metrics1 = CodeProgressMetrics(lines_added=10)
        self.tracker.update_progress(code_metrics=code_metrics1)
        
        # Update with progress
        code_metrics2 = CodeProgressMetrics(lines_added=50)
        self.tracker.update_progress(code_metrics=code_metrics2)
        
        overall = self.tracker._calculate_overall_progress()
        
        # Should be some positive progress
        self.assertGreater(overall, 0)
        
    def test_calculate_progress_for_type_code(self):
        """Test progress calculation for code metrics"""
        self.tracker.start_tracking()
        
        code_metrics1 = CodeProgressMetrics(lines_added=10)
        self.tracker.update_progress(code_metrics=code_metrics1)
        
        code_metrics2 = CodeProgressMetrics(lines_added=50)
        self.tracker.update_progress(code_metrics=code_metrics2)
        
        progress = self.tracker._calculate_progress_for_type(ProgressMetricType.CODE)
        
        self.assertGreater(progress, 0)
        
    def test_calculate_progress_for_type_task(self):
        """Test progress calculation for task metrics"""
        self.tracker.start_tracking()
        
        # Baseline: 2/10 = 20% completion
        task_metrics1 = TaskProgressMetrics(subtasks_total=10, subtasks_completed=2)
        self.tracker.update_progress(task_metrics=task_metrics1)
        
        # Current: 5/10 = 50% completion
        # Progress = 50% - 20% = 30%
        task_metrics2 = TaskProgressMetrics(subtasks_total=10, subtasks_completed=5)
        self.tracker.update_progress(task_metrics=task_metrics2)
        
        progress = self.tracker._calculate_progress_for_type(ProgressMetricType.TASK)
        
        # Should be 30.0 (50% - 20%)
        self.assertEqual(progress, 30.0)
        
    def test_calculate_progress_for_type_session(self):
        """Test progress calculation for session metrics"""
        self.tracker.start_tracking()
        
        session_metrics = SessionProgressMetrics(tasks_completed=2, tasks_failed=0)
        self.tracker.update_progress(session_metrics=session_metrics)
        
        progress = self.tracker._calculate_progress_for_type(ProgressMetricType.SESSION)
        
        # Should be 100% (2 completed out of 2 total)
        self.assertEqual(progress, 100.0)
        
    def test_calculate_progress_for_type_project(self):
        """Test progress calculation for project metrics"""
        self.tracker.start_tracking()
        
        project_metrics = ProjectProgressMetrics(features_total=10, features_completed=3)
        self.tracker.update_progress(project_metrics=project_metrics)
        
        progress = self.tracker._calculate_progress_for_type(ProgressMetricType.PROJECT)
        
        # Should be 30%
        self.assertEqual(progress, 30.0)
        
    def test_check_progress_specific_metric_type(self):
        """Test check_progress for specific metric type"""
        self.tracker.start_tracking()
        
        code_metrics = CodeProgressMetrics(lines_added=100)
        self.tracker.update_progress(code_metrics=code_metrics)
        
        result = self.tracker.check_progress(metric_type=ProgressMetricType.CODE)
        
        self.assertIn('details', result)
        self.assertIn('code', result['details'])
        self.assertNotIn('task', result['details'])
        
    def test_multiple_updates_tracked(self):
        """Test that multiple updates are tracked in history"""
        self.tracker.start_tracking()
        
        for i in range(5):
            code_metrics = CodeProgressMetrics(lines_added=10 * (i + 1))
            self.tracker.update_progress(code_metrics=code_metrics)
        
        # Should have 5 historical entries
        self.assertEqual(len(self.tracker.historical_metrics), 5)
        
    def test_reset_after_stop_and_restart(self):
        """Test that tracker resets after stop and restart"""
        self.tracker.start_tracking()
        
        code_metrics1 = CodeProgressMetrics(lines_added=100)
        self.tracker.update_progress(code_metrics=code_metrics1)
        
        self.tracker.stop_tracking()
        self.tracker.start_tracking()
        
        # Baseline should be reset
        code_metrics2 = CodeProgressMetrics(lines_added=50)
        self.tracker.update_progress(code_metrics=code_metrics2)
        
        self.assertEqual(len(self.tracker.alerts), 0)
        self.assertEqual(self.tracker.ops_without_progress, 0)


if __name__ == '__main__':
    unittest.main()