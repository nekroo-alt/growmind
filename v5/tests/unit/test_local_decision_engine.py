"""
Unit tests for LocalDecisionEngine

Tests the rule-based decision engine that makes local decisions without LLM.
"""

import unittest
import tempfile
import json
from pathlib import Path
from datetime import datetime

from logic.local_decision_engine import (
    LocalDecisionEngine,
    DecisionOutcome,
    DecisionRecord,
    DecisionStats
)


class TestLocalDecisionEngine(unittest.TestCase):
    """Test cases for LocalDecisionEngine"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.stats_file = Path(self.temp_dir) / 'decision_stats.json'
        self.engine = LocalDecisionEngine(stats_file=str(self.stats_file))
    
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)
    
    def test_initialization(self):
        """Test engine initialization"""
        engine = LocalDecisionEngine()
        self.assertIsNotNone(engine)
        self.assertEqual(len(engine.decisions), 0)
        self.assertEqual(engine.stats.total_decisions, 0)
    
    def test_initialization_with_stats_file(self):
        """Test engine initialization with stats file"""
        engine = LocalDecisionEngine(stats_file=str(self.stats_file))
        self.assertIsNotNone(engine)
        self.assertEqual(engine.stats_file, str(self.stats_file))
    
    def test_should_retry_transient_error(self):
        """Test retry decision for transient errors"""
        error_msg = "Rate limit exceeded, please try again later"
        
        # Should retry on first attempt
        result = self.engine.should_retry_error(error_msg, 0)
        self.assertTrue(result)
        
        # Should retry on second attempt
        result = self.engine.should_retry_error(error_msg, 1)
        self.assertTrue(result)
        
        # Should not retry after max attempts
        result = self.engine.should_retry_error(error_msg, 3)
        self.assertFalse(result)
    
    def test_should_retry_timeout_error(self):
        """Test retry decision for timeout errors"""
        error_msg = "Connection timed out after 30 seconds"
        
        # Should retry on first attempt
        result = self.engine.should_retry_error(error_msg, 0)
        self.assertTrue(result)
        
        # Should retry on second attempt
        result = self.engine.should_retry_error(error_msg, 1)
        self.assertTrue(result)
    
    def test_should_retry_permanent_error(self):
        """Test retry decision for permanent errors"""
        error_msg = "Authentication failed: Invalid API key"
        
        # Should not retry permanent errors
        result = self.engine.should_retry_error(error_msg, 0)
        self.assertFalse(result)
        
        result = self.engine.should_retry_error(error_msg, 5)
        self.assertFalse(result)
    
    def test_should_retry_network_error(self):
        """Test retry decision for network errors"""
        error_msg = "Connection refused"
        
        # Should retry network errors
        result = self.engine.should_retry_error(error_msg, 0)
        self.assertTrue(result)
        
        # Should retry multiple times for network errors
        result = self.engine.should_retry_error(error_msg, 3)
        self.assertTrue(result)
        
        # Should not retry after max network attempts
        result = self.engine.should_retry_error(error_msg, 5)
        self.assertFalse(result)
    
    def test_should_retry_unknown_error(self):
        """Test retry decision for unknown errors"""
        error_msg = "Some unknown error occurred"
        
        # Should fall back to LLM for unknown errors
        result = self.engine.should_retry_error(error_msg, 0)
        self.assertIsNone(result)
    
    def test_classify_transient_error(self):
        """Test error classification for transient errors"""
        errors = [
            "Rate limit exceeded",
            "Request timeout",
            "Connection refused",
            "Temporary service unavailable",
            "HTTP 429 Too Many Requests",
            "HTTP 503 Service Unavailable"
        ]
        
        for error in errors:
            result = self.engine.classify_error(error)
            self.assertEqual(result, 'transient', f"Failed for: {error}")
    
    def test_classify_permanent_error(self):
        """Test error classification for permanent errors"""
        errors = [
            "Authentication failed",
            "Authorization failed",
            "Invalid API key",
            "Access denied",
            "Permission denied",
            "Resource not found",
            "HTTP 401 Unauthorized",
            "HTTP 403 Forbidden",
            "HTTP 404 Not Found"
        ]
        
        for error in errors:
            result = self.engine.classify_error(error)
            self.assertEqual(result, 'permanent', f"Failed for: {error}")
    
    def test_classify_network_error(self):
        """Test error classification for network errors"""
        errors = [
            "Network unreachable",
            "DNS resolution failed",
            "Connection refused",
            "Connection reset",
            "Broken pipe"
        ]
        
        for error in errors:
            result = self.engine.classify_error(error)
            self.assertEqual(result, 'network', f"Failed for: {error}")
    
    def test_classify_unknown_error(self):
        """Test error classification for unknown errors"""
        error = "Some mysterious error"
        result = self.engine.classify_error(error)
        self.assertIsNone(result)
    
    def test_calculate_retry_delay(self):
        """Test retry delay calculation"""
        # Test exponential backoff
        delay = self.engine.calculate_retry_delay(0, base_delay=1.0)
        self.assertEqual(delay, 1.0)
        
        delay = self.engine.calculate_retry_delay(1, base_delay=1.0)
        self.assertEqual(delay, 2.0)
        
        delay = self.engine.calculate_retry_delay(2, base_delay=1.0)
        self.assertEqual(delay, 4.0)
        
        delay = self.engine.calculate_retry_delay(3, base_delay=1.0)
        self.assertEqual(delay, 8.0)
    
    def test_calculate_retry_delay_with_max(self):
        """Test retry delay calculation with max delay"""
        delay = self.engine.calculate_retry_delay(10, base_delay=1.0, max_delay=10.0)
        self.assertEqual(delay, 10.0)  # Should cap at max delay
    
    def test_is_progress_stagnant(self):
        """Test progress stagnation detection"""
        # Not enough data
        result = self.engine.is_progress_stagnant([0.1, 0.2])
        self.assertFalse(result)
        
        # Progress is improving
        result = self.engine.is_progress_stagnant([0.1, 0.3, 0.5, 0.7, 0.9])
        self.assertFalse(result)
        
        # Progress is stagnant
        result = self.engine.is_progress_stagnant([0.5, 0.51, 0.52, 0.51, 0.50])
        self.assertTrue(result)
    
    def test_is_regression(self):
        """Test regression detection"""
        # No regression
        result = self.engine.is_regression(0.7, 0.6)
        self.assertFalse(result)
        
        # Regression detected
        result = self.engine.is_regression(0.5, 0.7)
        self.assertTrue(result)
        
        # Small decrease (not regression)
        result = self.engine.is_regression(0.68, 0.70, threshold=0.05)
        self.assertFalse(result)
    
    def test_select_token_budget_simple(self):
        """Test token budget selection for simple tasks"""
        budget = self.engine.select_token_budget('simple')
        self.assertEqual(budget, 1000)
    
    def test_select_token_budget_medium(self):
        """Test token budget selection for medium tasks"""
        budget = self.engine.select_token_budget('medium')
        self.assertEqual(budget, 3000)
    
    def test_select_token_budget_complex(self):
        """Test token budget selection for complex tasks"""
        budget = self.engine.select_token_budget('complex')
        self.assertEqual(budget, 5000)
    
    def test_select_token_budget_with_history(self):
        """Test token budget selection with historical data"""
        historical = {
            'simple': 800,
            'medium': 2500,
            'complex': 4500
        }
        
        budget = self.engine.select_token_budget('medium', historical_budgets=historical)
        self.assertEqual(budget, 2500)
    
    def test_select_token_budget_default(self):
        """Test token budget selection with unknown complexity"""
        budget = self.engine.select_token_budget('unknown')
        self.assertEqual(budget, 3000)  # Default
    
    def test_should_expand_context_simple(self):
        """Test context expansion decision for simple tasks"""
        result = self.engine.should_expand_context(
            current_context_level=0,
            task_complexity='simple',
            expansion_count=0
        )
        self.assertFalse(result)
    
    def test_should_expand_context_complex(self):
        """Test context expansion decision for complex tasks"""
        result = self.engine.should_expand_context(
            current_context_level=0,
            task_complexity='complex',
            expansion_count=0
        )
        self.assertTrue(result)
    
    def test_should_expand_context_medium(self):
        """Test context expansion decision for medium tasks"""
        result = self.engine.should_expand_context(
            current_context_level=0,
            task_complexity='medium',
            expansion_count=0
        )
        self.assertTrue(result)
        
        # Should not expand if at level 2
        result = self.engine.should_expand_context(
            current_context_level=2,
            task_complexity='medium',
            expansion_count=1
        )
        self.assertFalse(result)
    
    def test_should_expand_context_max_expansions(self):
        """Test context expansion decision with max expansions"""
        result = self.engine.should_expand_context(
            current_context_level=0,
            task_complexity='complex',
            expansion_count=3
        )
        self.assertFalse(result)
    
    def test_validate_file_selection_valid(self):
        """Test file selection validation - valid"""
        result = self.engine.validate_file_selection(
            task_description="Fix bug in auth module",
            selected_files=['auth.py', 'user.py'],
            available_files=['auth.py', 'user.py', 'main.py']
        )
        self.assertTrue(result)
    
    def test_validate_file_selection_invalid_files(self):
        """Test file selection validation - invalid files"""
        result = self.engine.validate_file_selection(
            task_description="Fix bug",
            selected_files=['auth.py', 'nonexistent.py'],
            available_files=['auth.py', 'user.py']
        )
        self.assertFalse(result)
    
    def test_validate_file_selection_empty(self):
        """Test file selection validation - empty selection"""
        result = self.engine.validate_file_selection(
            task_description="Fix bug",
            selected_files=[],
            available_files=['auth.py', 'user.py']
        )
        self.assertFalse(result)
    
    def test_record_decision(self):
        """Test decision recording"""
        initial_count = len(self.engine.decisions)
        
        self.engine._record_decision(
            decision_type='test_decision',
            context={'key': 'value'},
            local_decision=True,
            used_llm=False,
            outcome=DecisionOutcome.LOCAL_SUCCESS,
            confidence=0.9
        )
        
        self.assertEqual(len(self.engine.decisions), initial_count + 1)
        self.assertEqual(self.engine.stats.total_decisions, initial_count + 1)
        self.assertEqual(self.engine.stats.local_decisions, 1)
    
    def test_record_outcome(self):
        """Test recording decision outcome"""
        # Make a decision
        self.engine._record_decision(
            decision_type='test_decision',
            context={},
            local_decision=True,
            used_llm=False,
            outcome=DecisionOutcome.LOCAL_SUCCESS,
            confidence=0.9
        )
        
        # Record that it was correct
        self.engine.record_outcome(0, was_correct=True)
        self.assertEqual(self.engine.stats.local_correct, 1)
        
        # Record that it was incorrect
        self.engine._record_decision(
            decision_type='test_decision2',
            context={},
            local_decision=False,
            used_llm=False,
            outcome=DecisionOutcome.LOCAL_SUCCESS,
            confidence=0.9
        )
        self.engine.record_outcome(1, was_correct=False)
        self.assertEqual(self.engine.stats.local_incorrect, 1)
    
    def test_get_statistics(self):
        """Test statistics retrieval"""
        # Make some decisions
        self.engine._record_decision(
            decision_type='test1',
            context={},
            local_decision=True,
            used_llm=False,
            outcome=DecisionOutcome.LOCAL_SUCCESS,
            confidence=0.9
        )
        self.engine._record_decision(
            decision_type='test2',
            context={},
            local_decision=None,
            used_llm=True,
            outcome=DecisionOutcome.LLM_ONLY,
            confidence=0.0
        )
        
        stats = self.engine.get_statistics()
        self.assertEqual(stats['total_decisions'], 2)
        self.assertEqual(stats['local_decisions'], 1)
        self.assertEqual(stats['llm_decisions'], 1)
        self.assertEqual(stats['llm_calls_saved'], 2)
    
    def test_get_report(self):
        """Test report generation"""
        self.engine._record_decision(
            decision_type='test_decision',
            context={},
            local_decision=True,
            used_llm=False,
            outcome=DecisionOutcome.LOCAL_SUCCESS,
            confidence=0.9
        )
        
        report = self.engine.get_report()
        self.assertIn('Local Decision Engine Report', report)
        self.assertIn('Total Decisions: 1', report)
        self.assertIn('test_decision', report)
    
    def test_get_local_success_rate(self):
        """Test local success rate calculation"""
        stats = DecisionStats(
            local_decisions=10,
            local_correct=8,
            local_incorrect=2
        )
        
        self.assertEqual(stats.get_local_success_rate(), 0.8)
    
    def test_get_local_success_rate_no_decisions(self):
        """Test local success rate with no decisions"""
        stats = DecisionStats()
        self.assertEqual(stats.get_local_success_rate(), 0.0)
    
    def test_get_llm_savings_rate(self):
        """Test LLM savings rate calculation"""
        stats = DecisionStats(
            total_decisions=100,
            llm_calls_saved=70
        )
        
        self.assertEqual(stats.get_llm_savings_rate(), 0.7)
    
    def test_persist_and_load_stats(self):
        """Test persisting and loading statistics"""
        # Make some decisions
        self.engine._record_decision(
            decision_type='test_decision',
            context={'test': 'value'},
            local_decision=True,
            used_llm=False,
            outcome=DecisionOutcome.LOCAL_SUCCESS,
            confidence=0.9
        )
        
        # Create new engine that should load stats
        new_engine = LocalDecisionEngine(stats_file=str(self.stats_file))
        
        self.assertEqual(new_engine.stats.total_decisions, 1)
        self.assertEqual(new_engine.stats.local_decisions, 1)
        self.assertEqual(len(new_engine.decisions), 1)
        self.assertEqual(new_engine.decisions[0].decision_type, 'test_decision')
    
    def test_clear_history(self):
        """Test clearing decision history"""
        # Make some decisions
        self.engine._record_decision(
            decision_type='test',
            context={},
            local_decision=True,
            used_llm=False,
            outcome=DecisionOutcome.LOCAL_SUCCESS,
            confidence=0.9
        )
        
        self.assertEqual(len(self.engine.decisions), 1)
        
        # Clear history
        self.engine.clear_history()
        
        # History should be cleared but stats should remain
        self.assertEqual(len(self.engine.decisions), 0)
        self.assertEqual(self.engine.stats.total_decisions, 1)
    
    def test_case_insensitive_error_matching(self):
        """Test that error matching is case-insensitive"""
        error1 = "RATE LIMIT EXCEEDED"
        error2 = "rate limit exceeded"
        error3 = "RaTe LiMiT ExCeEdEd"
        
        for error in [error1, error2, error3]:
            result = self.engine.classify_error(error)
            self.assertEqual(result, 'transient')
    
    def test_multiple_error_patterns(self):
        """Test error with multiple matching patterns"""
        # Error matches both transient and network patterns
        error = "Connection refused due to temporary failure"
        
        result = self.engine.classify_error(error)
        # Should match the first matching pattern (transient in this case)
        self.assertIn(result, ['transient', 'network'])
    
    def test_decision_record_to_dict(self):
        """Test DecisionRecord serialization"""
        record = DecisionRecord(
            timestamp=datetime(2025, 1, 24, 10, 0, 0),
            decision_type='test_decision',
            context={'key': 'value'},
            local_decision=True,
            used_llm=False,
            outcome=DecisionOutcome.LOCAL_SUCCESS,
            confidence=0.9
        )
        
        data = record.to_dict()
        self.assertEqual(data['decision_type'], 'test_decision')
        self.assertEqual(data['local_decision'], True)
        self.assertEqual(data['used_llm'], False)
        self.assertEqual(data['outcome'], 'local_success')
        self.assertEqual(data['confidence'], 0.9)
    
    def test_decision_outcome_enum(self):
        """Test DecisionOutcome enum values"""
        self.assertEqual(DecisionOutcome.LOCAL_SUCCESS.value, 'local_success')
        self.assertEqual(DecisionOutcome.LOCAL_FALLBACK.value, 'local_fallback')
        self.assertEqual(DecisionOutcome.LLM_ONLY.value, 'llm_only')
        self.assertEqual(DecisionOutcome.UNKNOWN.value, 'unknown')


class TestDecisionStats(unittest.TestCase):
    """Test cases for DecisionStats"""
    
    def test_initialization(self):
        """Test stats initialization"""
        stats = DecisionStats()
        self.assertEqual(stats.total_decisions, 0)
        self.assertEqual(stats.local_decisions, 0)
        self.assertEqual(stats.llm_decisions, 0)
        self.assertEqual(stats.local_correct, 0)
        self.assertEqual(stats.local_incorrect, 0)
        self.assertEqual(stats.llm_calls_saved, 0)
    
    def test_get_local_success_rate(self):
        """Test success rate calculation"""
        stats = DecisionStats(
            local_decisions=10,
            local_correct=8,
            local_incorrect=2
        )
        self.assertAlmostEqual(stats.get_local_success_rate(), 0.8, places=2)
    
    def test_get_llm_savings_rate(self):
        """Test savings rate calculation"""
        stats = DecisionStats(
            total_decisions=100,
            llm_calls_saved=75
        )
        self.assertAlmostEqual(stats.get_llm_savings_rate(), 0.75, places=2)


if __name__ == '__main__':
    unittest.main()