"""
Unit tests for Strategy Performance Tracking and Evaluation Module
"""

import unittest
import os
import sqlite3
import json
from pathlib import Path
from logic.strategy_evaluator import (
    StrategyEvaluator,
    StrategyType,
    SituationType,
    StrategyPerformanceMetrics,
    StrategyComparison
)


class TestStrategyEvaluator(unittest.TestCase):
    """Test cases for StrategyEvaluator class."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.test_db = "test_strategy_evaluator.db"
        # Clean up any existing test database
        if os.path.exists(self.test_db):
            os.remove(self.test_db)
        self.evaluator = StrategyEvaluator(self.test_db)
        
    def tearDown(self):
        """Clean up test fixtures after each test method."""
        # Close any database connections
        # Delete test database
        if os.path.exists(self.test_db):
            os.remove(self.test_db)
    
    def test_database_initialization(self):
        """Test that database is initialized correctly."""
        # Check that database file exists
        self.assertTrue(os.path.exists(self.test_db))
        
        # Check that tables exist
        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name IN (
                'strategy_performance', 'strategy_operations'
            )
        """)
        tables = cursor.fetchall()
        conn.close()
        
        self.assertEqual(len(tables), 2)
    
    def test_track_performance(self):
        """Test tracking a single strategy operation."""
        # Track a performance record
        self.evaluator.track_performance(
            strategy=StrategyType.BALANCED,
            task_type="implementation",
            situation_type=SituationType.NORMAL,
            success=True,
            time_elapsed=1.5,
            tokens_used=1200,
            quality_score=0.85
        )
        
        # Verify record was logged
        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM strategy_operations")
        count = cursor.fetchone()[0]
        conn.close()
        
        self.assertEqual(count, 1)
        
        # Verify performance metrics were updated
        metrics = self.evaluator.get_performance(
            StrategyType.BALANCED,
            "implementation",
            SituationType.NORMAL
        )
        
        self.assertIsNotNone(metrics)
        self.assertEqual(metrics.strategy, StrategyType.BALANCED)
        self.assertEqual(metrics.task_type, "implementation")
        self.assertEqual(metrics.situation_type, SituationType.NORMAL)
        self.assertEqual(metrics.total_operations, 1)
        self.assertEqual(metrics.successful_operations, 1)
        self.assertEqual(metrics.success_rate, 1.0)
    
    def test_track_multiple_operations(self):
        """Test tracking multiple operations for same strategy."""
        # Track multiple operations
        for i, success in enumerate([True, True, False, True, True]):
            self.evaluator.track_performance(
                strategy=StrategyType.AGGRESSIVE,
                task_type="planning",
                situation_type=SituationType.TIME_CRITICAL,
                success=success,
                time_elapsed=0.8 + i * 0.1,
                tokens_used=800 + i * 50,
                quality_score=0.7 + i * 0.05
            )
        
        # Verify aggregated metrics
        metrics = self.evaluator.get_performance(
            StrategyType.AGGRESSIVE,
            "planning",
            SituationType.TIME_CRITICAL
        )
        
        self.assertIsNotNone(metrics)
        self.assertEqual(metrics.total_operations, 5)
        self.assertEqual(metrics.successful_operations, 4)
        self.assertAlmostEqual(metrics.success_rate, 0.8, places=2)
        self.assertGreater(metrics.efficiency, 0)
    
    def test_get_performance_no_data(self):
        """Test getting performance when no data exists."""
        metrics = self.evaluator.get_performance(
            StrategyType.CONSERVATIVE,
            "testing",
            SituationType.ERROR_RECOVERY
        )
        
        self.assertIsNone(metrics)
    
    def test_get_performance_with_task_type_filter(self):
        """Test getting performance filtered by task type."""
        # Add data for multiple task types
        self.evaluator.track_performance(
            StrategyType.BALANCED,
            "planning",
            SituationType.NORMAL,
            True, 2.0, 1500, 0.9
        )
        
        self.evaluator.track_performance(
            StrategyType.BALANCED,
            "implementation",
            SituationType.NORMAL,
            True, 1.5, 1200, 0.85
        )
        
        # Query for specific task type
        metrics = self.evaluator.get_performance(
            StrategyType.BALANCED,
            task_type="planning"
        )
        
        self.assertIsNotNone(metrics)
        self.assertEqual(metrics.task_type, "planning")
    
    def test_get_performance_without_filters(self):
        """Test getting performance without task/situation filters."""
        # Add data for multiple task types
        self.evaluator.track_performance(
            StrategyType.BALANCED,
            "planning",
            SituationType.NORMAL,
            True, 2.0, 1500, 0.9
        )
        
        self.evaluator.track_performance(
            StrategyType.BALANCED,
            "implementation",
            SituationType.NORMAL,
            True, 1.5, 1200, 0.85
        )
        
        # Query without filters (should return most used)
        metrics = self.evaluator.get_performance(
            StrategyType.BALANCED
        )
        
        self.assertIsNotNone(metrics)
        self.assertEqual(metrics.strategy, StrategyType.BALANCED)
    
    def test_compare_strategies(self):
        """Test comparing multiple strategies."""
        # Add performance data for all strategies
        self.evaluator.track_performance(
            StrategyType.CONSERVATIVE,
            "implementation",
            SituationType.ERROR_RECOVERY,
            True, 2.5, 1600, 0.95
        )
        
        self.evaluator.track_performance(
            StrategyType.BALANCED,
            "implementation",
            SituationType.NORMAL,
            True, 1.5, 1200, 0.85
        )
        
        self.evaluator.track_performance(
            StrategyType.AGGRESSIVE,
            "implementation",
            SituationType.TIME_CRITICAL,
            True, 0.8, 800, 0.75
        )
        
        # Compare strategies
        comparisons = self.evaluator.compare_strategies(
            task_type="implementation"
        )
        
        self.assertEqual(len(comparisons), 3)
        
        # Verify ranking
        ranks = [comp.rank for comp in comparisons]
        self.assertEqual(sorted(ranks), [1, 2, 3])
        
        # Verify each comparison has required fields
        for comp in comparisons:
            self.assertIsInstance(comp, StrategyComparison)
            self.assertIsNotNone(comp.strategy)
            self.assertIsNotNone(comp.score)
            self.assertIsNotNone(comp.metrics)
    
    def test_compare_strategies_with_custom_weights(self):
        """Test comparing strategies with custom weights."""
        # Add performance data
        self.evaluator.track_performance(
            StrategyType.BALANCED,
            "testing",
            SituationType.NORMAL,
            True, 1.0, 1000, 0.8
        )
        
        self.evaluator.track_performance(
            StrategyType.AGGRESSIVE,
            "testing",
            SituationType.TIME_CRITICAL,
            True, 0.5, 800, 0.7
        )
        
        # Compare with efficiency-focused weights
        comparisons = self.evaluator.compare_strategies(
            task_type="testing",
            weights={'success_rate': 0.3, 'efficiency': 0.5, 
                    'effectiveness': 0.1, 'robustness': 0.1}
        )
        
        self.assertEqual(len(comparisons), 2)
    
    def test_compare_strategies_no_data(self):
        """Test comparing strategies when no data exists."""
        comparisons = self.evaluator.compare_strategies()
        
        self.assertEqual(len(comparisons), 0)
    
    def test_get_optimal_strategy(self):
        """Test getting optimal strategy."""
        # Add performance data
        for i in range(5):
            self.evaluator.track_performance(
                StrategyType.BALANCED,
                "planning",
                SituationType.NORMAL,
                True, 1.5 + i * 0.1, 1200 + i * 50, 0.85
            )
        
        for i in range(3):
            self.evaluator.track_performance(
                StrategyType.AGGRESSIVE,
                "planning",
                SituationType.NORMAL,
                True if i < 2 else False, 0.8 + i * 0.1, 800 + i * 50, 0.75
            )
        
        # Get optimal strategy
        optimal = self.evaluator.get_optimal_strategy(
            task_type="planning",
            situation_type=SituationType.NORMAL
        )
        
        self.assertIsNotNone(optimal)
        self.assertIsInstance(optimal, StrategyType)
    
    def test_get_optimal_strategy_no_data(self):
        """Test getting optimal strategy when no data exists."""
        optimal = self.evaluator.get_optimal_strategy()
        
        self.assertIsNone(optimal)
    
    def test_generate_performance_report(self):
        """Test generating performance report."""
        # Add some data
        self.evaluator.track_performance(
            StrategyType.BALANCED,
            "implementation",
            SituationType.NORMAL,
            True, 1.5, 1200, 0.85
        )
        
        # Generate report
        report = self.evaluator.generate_performance_report()
        
        self.assertIn("STRATEGY PERFORMANCE REPORT", report)
        self.assertIn("BALANCED", report)
    
    def test_generate_performance_report_no_data(self):
        """Test generating report when no data exists."""
        report = self.evaluator.generate_performance_report()
        
        self.assertIn("No performance data available", report)
    
    def test_export_performance_data(self):
        """Test exporting performance data to JSON."""
        # Add some data
        self.evaluator.track_performance(
            StrategyType.BALANCED,
            "implementation",
            SituationType.NORMAL,
            True, 1.5, 1200, 0.85
        )
        
        # Export data
        export_file = "test_performance_export.json"
        self.evaluator.export_performance_data(export_file)
        
        # Verify file exists
        self.assertTrue(os.path.exists(export_file))
        
        # Verify JSON format
        with open(export_file, 'r') as f:
            data = json.load(f)
        
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)
        
        # Clean up
        os.remove(export_file)
    
    def test_get_strategy_rankings(self):
        """Test getting strategy rankings."""
        # Add performance data
        self.evaluator.track_performance(
            StrategyType.CONSERVATIVE,
            "testing",
            SituationType.NORMAL,
            True, 2.0, 1500, 0.95
        )
        
        self.evaluator.track_performance(
            StrategyType.BALANCED,
            "testing",
            SituationType.NORMAL,
            True, 1.5, 1200, 0.85
        )
        
        # Get rankings
        rankings = self.evaluator.get_strategy_rankings(task_type="testing")
        
        self.assertIsInstance(rankings, dict)
        self.assertGreater(len(rankings), 0)
        
        # Verify ranks are valid
        for strategy, rank in rankings.items():
            self.assertIsInstance(strategy, StrategyType)
            self.assertIsInstance(rank, int)
            self.assertGreaterEqual(rank, 1)
    
    def test_get_recommendations(self):
        """Test getting strategy recommendations."""
        # Add performance data
        for i in range(10):
            self.evaluator.track_performance(
                StrategyType.BALANCED,
                "implementation",
                SituationType.NORMAL,
                True if i < 9 else False, 1.5, 1200, 0.85
            )
        
        # Get recommendation
        strategy, explanation = self.evaluator.get_recommendations(
            "implementation",
            SituationType.NORMAL
        )
        
        self.assertIsNotNone(strategy)
        self.assertIsInstance(strategy, StrategyType)
        self.assertIsInstance(explanation, str)
        self.assertGreater(len(explanation), 0)
    
    def test_get_recommendations_no_data(self):
        """Test getting recommendations when no data exists."""
        strategy, explanation = self.evaluator.get_recommendations(
            "implementation",
            SituationType.NORMAL
        )
        
        self.assertEqual(strategy, StrategyType.BALANCED)
        self.assertIn("No performance data available", explanation)
    
    def test_error_handling_in_track_performance(self):
        """Test that tracking handles errors gracefully."""
        # Track with missing optional fields
        self.evaluator.track_performance(
            strategy=StrategyType.BALANCED,
            task_type="testing",
            situation_type=SituationType.NORMAL,
            success=True,
            time_elapsed=1.0,
            tokens_used=1000
            # quality_score and error_handled are optional
        )
        
        # Should not raise an error
        metrics = self.evaluator.get_performance(
            StrategyType.BALANCED,
            "testing",
            SituationType.NORMAL
        )
        
        self.assertIsNotNone(metrics)
        self.assertEqual(metrics.total_operations, 1)
    
    def test_robustness_metric_calculation(self):
        """Test that robustness is calculated correctly."""
        # Track operations with error handling
        for i in range(5):
            self.evaluator.track_performance(
                StrategyType.CONSERVATIVE,
                "error_recovery",
                SituationType.ERROR_RECOVERY,
                success=True,
                time_elapsed=2.0,
                tokens_used=1500,
                quality_score=0.9,
                error_handled=True
            )
        
        # Check robustness
        metrics = self.evaluator.get_performance(
            StrategyType.CONSERVATIVE,
            "error_recovery",
            SituationType.ERROR_RECOVERY
        )
        
        self.assertIsNotNone(metrics)
        self.assertEqual(metrics.robustness, 1.0)  # All operations handled errors
    
    def test_efficiency_calculation(self):
        """Test that efficiency is calculated correctly."""
        # Track an operation with known time
        self.evaluator.track_performance(
            StrategyType.AGGRESSIVE,
            "fast_task",
            SituationType.TIME_CRITICAL,
            success=True,
            time_elapsed=0.5,  # 0.5 seconds
            tokens_used=500,
            quality_score=0.8
        )
        
        # Check efficiency (should be 1 / 0.5 = 2.0 ops/sec)
        metrics = self.evaluator.get_performance(
            StrategyType.AGGRESSIVE,
            "fast_task",
            SituationType.TIME_CRITICAL
        )
        
        self.assertIsNotNone(metrics)
        self.assertAlmostEqual(metrics.efficiency, 2.0, places=2)


class TestStrategyPerformanceMetrics(unittest.TestCase):
    """Test cases for StrategyPerformanceMetrics dataclass."""
    
    def test_metrics_initialization(self):
        """Test that metrics can be initialized."""
        metrics = StrategyPerformanceMetrics(
            strategy=StrategyType.BALANCED,
            task_type="testing",
            situation_type=SituationType.NORMAL,
            success_rate=0.9,
            efficiency=1.5,
            effectiveness=0.85,
            robustness=0.7,
            total_operations=10,
            successful_operations=9,
            avg_time_per_operation=1.2,
            avg_tokens_per_operation=1100
        )
        
        self.assertEqual(metrics.strategy, StrategyType.BALANCED)
        self.assertEqual(metrics.success_rate, 0.9)
        self.assertEqual(metrics.total_operations, 10)


class TestStrategyComparison(unittest.TestCase):
    """Test cases for StrategyComparison dataclass."""
    
    def test_comparison_initialization(self):
        """Test that comparison can be initialized."""
        metrics = StrategyPerformanceMetrics(
            strategy=StrategyType.BALANCED,
            task_type="testing",
            situation_type=SituationType.NORMAL
        )
        
        comparison = StrategyComparison(
            strategy=StrategyType.BALANCED,
            rank=1,
            score=0.85,
            metrics=metrics,
            advantages=["High success rate"],
            disadvantages=["Slower execution"]
        )
        
        self.assertEqual(comparison.strategy, StrategyType.BALANCED)
        self.assertEqual(comparison.rank, 1)
        self.assertEqual(comparison.score, 0.85)
        self.assertEqual(len(comparison.advantages), 1)
        self.assertEqual(len(comparison.disadvantages), 1)


if __name__ == '__main__':
    unittest.main()