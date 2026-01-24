"""
Unit tests for Token Budget Manager Module (V5)

Tests for adaptive token budget management including:
- Task complexity estimation
- Budget allocation
- Progressive budget expansion
- Budget learning from history
- Token optimization
"""

import unittest
import os
import tempfile
import sqlite3
from datetime import datetime
from v4.logic.token_budget_manager import (
    TokenBudgetManager,
    BudgetAllocation,
    TokenUsageStats,
    TaskComplexity,
    get_token_budget_manager
)


class TestTaskComplexity(unittest.TestCase):
    """Test task complexity estimation."""
    
    def test_simple_task_estimation(self):
        """Test estimation of simple tasks."""
        desc = "Fix a typo in the documentation"
        complexity = TaskComplexity.estimate_complexity(desc)
        self.assertEqual(complexity, TaskComplexity.SIMPLE)
    
    def test_medium_task_estimation(self):
        """Test estimation of medium complexity tasks."""
        desc = "Add a new feature to the user profile"
        complexity = TaskComplexity.estimate_complexity(desc)
        self.assertEqual(complexity, TaskComplexity.MEDIUM)
    
    def test_complex_task_estimation(self):
        """Test estimation of complex tasks."""
        desc = "Refactor the entire architecture for better performance"
        complexity = TaskComplexity.estimate_complexity(desc)
        self.assertEqual(complexity, TaskComplexity.COMPLEX)
    
    def test_bug_fix_estimation(self):
        """Test bug fix task estimation."""
        desc = "Fix critical bug in authentication"
        complexity = TaskComplexity.estimate_complexity(desc, task_type="bug_fix")
        self.assertEqual(complexity, TaskComplexity.SIMPLE)
    
    def test_refactor_estimation(self):
        """Test refactor task estimation."""
        desc = "Refactor codebase"
        complexity = TaskComplexity.estimate_complexity(desc, task_type="refactor")
        self.assertEqual(complexity, TaskComplexity.COMPLEX)
    
    def test_get_default_budget(self):
        """Test default budget retrieval."""
        self.assertEqual(TaskComplexity.get_default_budget(TaskComplexity.SIMPLE), 1000)
        self.assertEqual(TaskComplexity.get_default_budget(TaskComplexity.MEDIUM), 3000)
        self.assertEqual(TaskComplexity.get_default_budget(TaskComplexity.COMPLEX), 5000)
    
    def test_from_string(self):
        """Test string to TaskComplexity conversion."""
        self.assertEqual(TaskComplexity.from_string("simple"), TaskComplexity.SIMPLE)
        self.assertEqual(TaskComplexity.from_string("medium"), TaskComplexity.MEDIUM)
        self.assertEqual(TaskComplexity.from_string("complex"), TaskComplexity.COMPLEX)
        self.assertEqual(TaskComplexity.from_string("unknown"), TaskComplexity.MEDIUM)


class TestBudgetAllocation(unittest.TestCase):
    """Test budget allocation tracking."""
    
    def test_budget_properties(self):
        """Test budget allocation properties."""
        allocation = BudgetAllocation(
            initial_budget=1000,
            current_budget=1000,
            task_type="test"
        )
        
        self.assertEqual(allocation.initial_budget, 1000)
        self.assertEqual(allocation.current_budget, 1000)
        self.assertEqual(allocation.used_tokens, 0)
        self.assertEqual(allocation.remaining_tokens, 1000)
        self.assertEqual(allocation.utilization_percentage, 0.0)
    
    def test_use_tokens(self):
        """Test token usage recording."""
        allocation = BudgetAllocation(
            initial_budget=1000,
            current_budget=1000
        )
        
        allocation.use_tokens(500)
        self.assertEqual(allocation.used_tokens, 500)
        self.assertEqual(allocation.remaining_tokens, 500)
        self.assertEqual(allocation.utilization_percentage, 50.0)
    
    def test_expand_budget(self):
        """Test budget expansion."""
        allocation = BudgetAllocation(
            initial_budget=1000,
            current_budget=1000,
            max_expansions=3
        )
        
        new_budget = allocation.expand_budget(1.5)
        self.assertEqual(new_budget, 1500)
        self.assertEqual(allocation.expansion_count, 1)
        self.assertTrue(allocation.can_expand)
    
    def test_max_expansions(self):
        """Test maximum expansion limit."""
        allocation = BudgetAllocation(
            initial_budget=1000,
            current_budget=1000,
            max_expansions=2
        )
        
        # First expansion
        allocation.expand_budget(1.5)
        self.assertTrue(allocation.can_expand)
        
        # Second expansion
        allocation.expand_budget(1.5)
        self.assertFalse(allocation.can_expand)
        
        # Third expansion should fail
        old_budget = allocation.current_budget
        new_budget = allocation.expand_budget(1.5)
        self.assertEqual(new_budget, old_budget)
    
    def test_to_dict(self):
        """Test budget allocation dictionary conversion."""
        allocation = BudgetAllocation(
            initial_budget=1000,
            current_budget=1500,
            used_tokens=500,
            expansion_count=1,
            task_type="test",
            complexity=TaskComplexity.MEDIUM
        )
        
        data = allocation.to_dict()
        
        self.assertEqual(data['initial_budget'], 1000)
        self.assertEqual(data['current_budget'], 1500)
        self.assertEqual(data['used_tokens'], 500)
        self.assertEqual(data['remaining_tokens'], 1000)
        self.assertEqual(data['expansion_count'], 1)
        self.assertEqual(data['task_type'], "test")
        self.assertEqual(data['complexity'], "medium")


class TestTokenUsageStats(unittest.TestCase):
    """Test token usage statistics."""
    
    def test_update_stats(self):
        """Test statistics update."""
        stats = TokenUsageStats(
            task_type="test",
            complexity=TaskComplexity.MEDIUM
        )
        
        stats.update_stats(tokens_used=1000, budget_allocated=1500, success=True)
        
        self.assertEqual(stats.total_tasks, 1)
        self.assertEqual(stats.total_tokens_used, 1000)
        self.assertEqual(stats.total_budget_allocated, 1500)
        self.assertEqual(stats.successful_tasks, 1)
        self.assertEqual(stats.avg_tokens_per_task, 1000.0)
        self.assertEqual(stats.success_rate, 100.0)
    
    def test_multiple_updates(self):
        """Test multiple statistics updates."""
        stats = TokenUsageStats(
            task_type="test",
            complexity=TaskComplexity.MEDIUM
        )
        
        # First task - successful
        stats.update_stats(tokens_used=1000, budget_allocated=1500, success=True)
        
        # Second task - failed
        stats.update_stats(tokens_used=2000, budget_allocated=3000, success=False)
        
        self.assertEqual(stats.total_tasks, 2)
        self.assertEqual(stats.total_tokens_used, 3000)
        self.assertEqual(stats.successful_tasks, 1)
        self.assertEqual(stats.avg_tokens_per_task, 1500.0)
        self.assertEqual(stats.success_rate, 50.0)
    
    def test_get_recommended_budget_insufficient_data(self):
        """Test recommended budget with insufficient data."""
        stats = TokenUsageStats(
            task_type="test",
            complexity=TaskComplexity.MEDIUM
        )
        
        stats.update_stats(tokens_used=1000, budget_allocated=1500, success=True)
        stats.update_stats(tokens_used=1200, budget_allocated=1500, success=True)
        
        # Not enough data (< 3 tasks), should return default
        budget = stats.get_recommended_budget(TaskComplexity.MEDIUM)
        self.assertEqual(budget, TaskComplexity.get_default_budget(TaskComplexity.MEDIUM))
    
    def test_get_recommended_budget_with_data(self):
        """Test recommended budget with sufficient data."""
        stats = TokenUsageStats(
            task_type="test",
            complexity=TaskComplexity.MEDIUM
        )
        
        # Add 3 tasks
        stats.update_stats(tokens_used=1000, budget_allocated=1500, success=True)
        stats.update_stats(tokens_used=1200, budget_allocated=1500, success=True)
        stats.update_stats(tokens_used=1100, budget_allocated=1500, success=True)
        
        # Average is 1100, with 20% buffer = 1320
        budget = stats.get_recommended_budget(TaskComplexity.MEDIUM)
        self.assertGreaterEqual(budget, 1320)
    
    def test_recommended_budget_complexity_adjustment(self):
        """Test complexity adjustment in recommended budget."""
        stats = TokenUsageStats(
            task_type="test",
            complexity=TaskComplexity.MEDIUM
        )
        
        # Add 3 tasks
        stats.update_stats(tokens_used=1000, budget_allocated=1500, success=True)
        stats.update_stats(tokens_used=1200, budget_allocated=1500, success=True)
        stats.update_stats(tokens_used=1100, budget_allocated=1500, success=True)
        
        # Complex task should get 1.5x multiplier
        complex_budget = stats.get_recommended_budget(TaskComplexity.COMPLEX)
        medium_budget = stats.get_recommended_budget(TaskComplexity.MEDIUM)
        simple_budget = stats.get_recommended_budget(TaskComplexity.SIMPLE)
        
        self.assertGreater(complex_budget, medium_budget)
        self.assertLess(simple_budget, medium_budget)


class TestTokenBudgetManager(unittest.TestCase):
    """Test token budget manager."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create temporary database
        self.temp_db = tempfile.NamedTemporaryFile(
            suffix='.db',
            delete=False
        )
        self.db_path = self.temp_db.name
        self.temp_db.close()
        
        # Create manager
        self.manager = TokenBudgetManager(
            db_path=self.db_path,
            max_total_budget=10000,
            alert_threshold=0.8,
            expansion_factor=1.5
        )
    
    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
    
    def test_database_initialization(self):
        """Test database table creation."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check token_usage_history table
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='token_usage_history'"
        )
        self.assertIsNotNone(cursor.fetchone())
        
        # Check budget_recommendations table
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='budget_recommendations'"
        )
        self.assertIsNotNone(cursor.fetchone())
        
        conn.close()
    
    def test_allocate_budget_simple(self):
        """Test budget allocation for simple task."""
        allocation = self.manager.allocate_budget(
            task_description="Fix a typo",
            task_type="bug_fix"
        )
        
        self.assertEqual(allocation.task_type, "bug_fix")
        self.assertEqual(allocation.complexity, TaskComplexity.SIMPLE)
        self.assertEqual(allocation.initial_budget, 1000)
        self.assertEqual(allocation.current_budget, 1000)
        self.assertEqual(allocation.used_tokens, 0)
    
    def test_allocate_budget_complex(self):
        """Test budget allocation for complex task."""
        allocation = self.manager.allocate_budget(
            task_description="Refactor entire architecture",
            task_type="refactor"
        )
        
        self.assertEqual(allocation.task_type, "refactor")
        self.assertEqual(allocation.complexity, TaskComplexity.COMPLEX)
        self.assertGreaterEqual(allocation.initial_budget, 5000)
    
    def test_custom_budget(self):
        """Test custom budget override."""
        allocation = self.manager.allocate_budget(
            task_description="Test task",
            custom_budget=2500
        )
        
        self.assertEqual(allocation.initial_budget, 2500)
        self.assertEqual(allocation.current_budget, 2500)
    
    def test_max_total_budget(self):
        """Test maximum total budget constraint."""
        allocation = self.manager.allocate_budget(
            task_description="Complex task that would exceed budget",
            task_type="refactor"
        )
        
        # Should be capped at max_total_budget
        self.assertLessEqual(allocation.initial_budget, 10000)
    
    def test_record_token_usage(self):
        """Test token usage recording."""
        allocation = self.manager.allocate_budget(
            task_description="Test task",
            task_type="test"
        )
        
        self.manager.record_token_usage(500)
        self.assertEqual(allocation.used_tokens, 500)
        
        self.manager.record_token_usage(300)
        self.assertEqual(allocation.used_tokens, 800)
    
    def test_check_budget_alert(self):
        """Test budget alert checking."""
        allocation = self.manager.allocate_budget(
            task_description="Test task",
            task_type="test"
        )
        
        # Use less than threshold (80%)
        allocation.use_tokens(700)  # 70% of 1000
        alert = self.manager.check_budget_alert()
        self.assertIsNone(alert)
        
        # Use more than threshold
        allocation.use_tokens(100)  # 80% of 1000
        alert = self.manager.check_budget_alert()
        self.assertIsNotNone(alert)
        self.assertIn("BUDGET ALERT", alert)
    
    def test_should_expand_budget(self):
        """Test budget expansion decision."""
        allocation = self.manager.allocate_budget(
            task_description="Test task",
            task_type="test"
        )
        
        # Slow progress (30%) but high token usage rate
        should_expand = self.manager.should_expand_budget(
            task_progress=0.3,
            token_usage_rate=2000  # Would need 1400 tokens to complete
        )
        
        # Should expand because need > remaining tokens * 1.5
        self.assertTrue(should_expand)
    
    def test_should_not_expand_budget(self):
        """Test budget not needed for expansion."""
        allocation = self.manager.allocate_budget(
            task_description="Test task",
            task_type="test"
        )
        
        # Good progress (80%) with reasonable token usage
        should_expand = self.manager.should_expand_budget(
            task_progress=0.8,
            token_usage_rate=500  # Only need 100 more tokens
        )
        
        # Should not expand
        self.assertFalse(should_expand)
    
    def test_expand_budget(self):
        """Test budget expansion."""
        allocation = self.manager.allocate_budget(
            task_description="Test task",
            task_type="test"
        )
        
        old_budget = allocation.current_budget
        new_budget = self.manager.expand_budget("Running low on tokens")
        
        self.assertEqual(new_budget, int(old_budget * 1.5))
        self.assertEqual(allocation.expansion_count, 1)
    
    def test_expand_budget_max_limit(self):
        """Test budget expansion limit."""
        allocation = self.manager.allocate_budget(
            task_description="Test task",
            task_type="test",
            custom_budget=1000
        )
        
        # Expand to max
        allocation.expand_budget()
        allocation.expand_budget()
        allocation.expand_budget()  # 3rd expansion (max_expansions=3)
        
        self.assertFalse(allocation.can_expand)
        
        # Should raise error
        with self.assertRaises(ValueError):
            self.manager.expand_budget()
    
    def test_complete_task(self):
        """Test task completion and recording."""
        allocation = self.manager.allocate_budget(
            task_description="Test task",
            task_type="test"
        )
        
        allocation.use_tokens(800)
        self.manager.complete_task("task_001", success=True)
        
        # Check database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT * FROM token_usage_history WHERE task_id = 'task_001'"
        )
        row = cursor.fetchone()
        
        self.assertIsNotNone(row)
        self.assertEqual(row[1], "task_001")  # task_id
        self.assertEqual(row[6], 800)  # tokens_used
        self.assertEqual(row[8], 1)  # success
        
        conn.close()
    
    def test_budget_learning(self):
        """Test budget learning from completed tasks."""
        # Complete several tasks with similar complexity
        for i in range(5):
            allocation = self.manager.allocate_budget(
                task_description="Test task",
                task_type="test"
            )
            allocation.use_tokens(1500)  # Consistently use 1500 tokens
            self.manager.complete_task(f"task_{i}", success=True)
        
        # Next allocation should use learned budget
        allocation = self.manager.allocate_budget(
            task_description="Another test task",
            task_type="test"
        )
        
        # Should recommend around 1500 * 1.2 = 1800
        self.assertGreaterEqual(allocation.initial_budget, 1500)
        self.assertLessEqual(allocation.initial_budget, 2000)
    
    def test_get_usage_report(self):
        """Test usage report generation."""
        # Add some tasks
        allocation1 = self.manager.allocate_budget(
            task_description="Task 1",
            task_type="bug_fix"
        )
        allocation1.use_tokens(800)
        self.manager.complete_task("task_001", success=True)
        
        allocation2 = self.manager.allocate_budget(
            task_description="Task 2",
            task_type="feature"
        )
        allocation2.use_tokens(2500)
        self.manager.complete_task("task_002", success=False)
        
        # Get report
        report = self.manager.get_usage_report()
        
        self.assertEqual(report['total_tasks'], 2)
        self.assertEqual(report['total_tokens'], 3300)
        self.assertEqual(report['success_rate'], 50.0)
        self.assertEqual(len(report['history']), 2)
    
    def test_get_usage_report_filtered(self):
        """Test usage report with filters."""
        # Add tasks with different types
        for i in range(3):
            allocation = self.manager.allocate_budget(
                task_description=f"Bug fix {i}",
                task_type="bug_fix"
            )
            allocation.use_tokens(800)
            self.manager.complete_task(f"task_{i}", success=True)
        
        for i in range(2):
            allocation = self.manager.allocate_budget(
                task_description=f"Feature {i}",
                task_type="feature"
            )
            allocation.use_tokens(2500)
            self.manager.complete_task(f"task_feature_{i}", success=True)
        
        # Filter by task_type
        report = self.manager.get_usage_report(task_type="bug_fix")
        
        self.assertEqual(report['total_tasks'], 3)
        self.assertEqual(report['total_tokens'], 2400)
    
    def test_optimize_context_tokens(self):
        """Test context token optimization."""
        context_items = [
            {'name': 'item1', 'tokens': 500, 'relevance': 0.9},
            {'name': 'item2', 'tokens': 800, 'relevance': 0.7},
            {'name': 'item3', 'tokens': 400, 'relevance': 0.5},
            {'name': 'item4', 'tokens': 300, 'relevance': 0.3},
            {'name': 'item5', 'tokens': 200, 'relevance': 0.2},
        ]
        
        max_tokens = 1200
        
        # Optimize: should keep high relevance items first
        optimized = self.manager.optimize_context_tokens(
            context_items,
            max_tokens
        )
        
        # Should keep item1 (500, 0.9) and item2 (800, 0.7) = 1300 tokens
        # But max is 1200, so might not fit item2
        # Item3 (400, 0.5) should fit after item1
        total_tokens = sum(item['tokens'] for item in optimized)
        
        self.assertLessEqual(total_tokens, max_tokens)
        
        # High relevance items should be included
        relevance_scores = [item['relevance'] for item in optimized]
        self.assertIn(0.9, relevance_scores)
    
    def test_get_recommendations_report(self):
        """Test recommendations report."""
        # Complete some tasks to build recommendations
        for i in range(3):
            allocation = self.manager.allocate_budget(
                task_description="Test task",
                task_type="test"
            )
            allocation.use_tokens(1500)
            self.manager.complete_task(f"task_{i}", success=True)
        
        report = self.manager.get_recommendations_report()
        
        self.assertIsInstance(report, dict)
        self.assertIn("test:medium", report)


class TestGlobalTokenBudgetManager(unittest.TestCase):
    """Test global token budget manager instance."""
    
    def test_get_singleton_instance(self):
        """Test singleton pattern."""
        manager1 = get_token_budget_manager()
        manager2 = get_token_budget_manager()
        
        self.assertIs(manager1, manager2)


class TestTokenBudgetIntegration(unittest.TestCase):
    """Integration tests for token budget manager."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_db = tempfile.NamedTemporaryFile(
            suffix='.db',
            delete=False
        )
        self.db_path = self.temp_db.name
        self.temp_db.close()
    
    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
    
    def test_full_task_lifecycle(self):
        """Test complete task lifecycle."""
        manager = TokenBudgetManager(db_path=self.db_path)
        
        # 1. Allocate budget
        allocation = manager.allocate_budget(
            task_description="Implement user authentication",
            task_type="feature"
        )
        
        self.assertIsNotNone(allocation)
        self.assertEqual(allocation.complexity, TaskComplexity.MEDIUM)
        
        # 2. Use tokens progressively
        manager.record_token_usage(500)
        self.assertEqual(allocation.used_tokens, 500)
        
        manager.record_token_usage(1000)
        self.assertEqual(allocation.used_tokens, 1500)
        
        # 3. Check for alerts
        if allocation.utilization_percentage >= 80:
            alert = manager.check_budget_alert()
            self.assertIsNotNone(alert)
        
        # 4. Complete task
        manager.complete_task("task_auth_001", success=True)
        
        # 5. Verify recording
        report = manager.get_usage_report(task_type="feature")
        self.assertEqual(report['total_tasks'], 1)
    
    def test_progressive_expansion(self):
        """Test progressive budget expansion during task."""
        manager = TokenBudgetManager(db_path=self.db_path)
        
        # Allocate small budget intentionally
        manager.allocate_budget(
            task_description="Complex task",
            task_type="feature",
            custom_budget=1000
        )
        
        # Use tokens quickly
        manager.record_token_usage(800)
        
        # Check if should expand
        allocation = manager.get_current_allocation()
        if manager.should_expand_budget(task_progress=0.2, token_usage_rate=4000):
            manager.expand_budget("Complex task requires more tokens")
        
        # Verify expansion
        allocation = manager.get_current_allocation()
        self.assertGreater(allocation.current_budget, 1000)
    
    def test_learning_over_time(self):
        """Test budget learning over multiple tasks."""
        manager = TokenBudgetManager(db_path=self.db_path)
        
        # Phase 1: Initial tasks (use default budgets)
        for i in range(3):
            allocation = manager.allocate_budget(
                task_description="Test task",
                task_type="test"
            )
            allocation.use_tokens(1800)  # Consistently use 1800
            manager.complete_task(f"task_{i}", success=True)
        
        # Phase 2: Next task should use learned budget
        allocation = manager.allocate_budget(
            task_description="Another test task",
            task_type="test"
        )
        
        # Should recommend higher than default (3000)
        self.assertGreaterEqual(allocation.initial_budget, 1800)


if __name__ == '__main__':
    unittest.main()