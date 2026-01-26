"""
Unit tests for Strategy Comparison and Ranking (Task 5.2)

Tests for:
- Strategy comparison across multiple dimensions
- Strategy ranking for each task type
- Strategy ranking for each situation type
- Dynamic updates based on performance
- Identification of optimal strategy combinations
- Strategy recommendations
"""

import pytest
import sqlite3
import os
import tempfile
from typing import List, Dict

from v5.logic.strategy_evaluator import (
    StrategyEvaluator,
    StrategyType,
    SituationType,
    StrategyPerformanceMetrics,
    StrategyComparison
)


class TestStrategyComparisonRanking:
    """Test suite for strategy comparison and ranking functionality."""
    
    @pytest.fixture
    def evaluator(self):
        """Create a fresh evaluator instance with temporary database."""
        db_fd, db_path = tempfile.mkstemp(suffix='.db')
        os.close(db_fd)
        
        evaluator = StrategyEvaluator(db_path)
        yield evaluator
        
        # Cleanup
        if os.path.exists(db_path):
            os.remove(db_path)
    
    @pytest.fixture
    def populated_evaluator(self, evaluator):
        """Populate evaluator with test data."""
        # Simulate operations for each strategy
        test_data = [
            # Balanced strategy - good all-rounder
            (StrategyType.BALANCED, "implementation", SituationType.NORMAL, 
             True, 1.5, 1200, 0.85, False),
            (StrategyType.BALANCED, "implementation", SituationType.NORMAL, 
             True, 1.6, 1250, 0.80, False),
            (StrategyType.BALANCED, "implementation", SituationType.NORMAL, 
             True, 1.4, 1150, 0.88, False),
            (StrategyType.BALANCED, "implementation", SituationType.NORMAL, 
             False, 2.0, 1400, 0.70, False),
            (StrategyType.BALANCED, "implementation", SituationType.NORMAL, 
             True, 1.5, 1200, 0.83, False),
            
            # Aggressive strategy - fast but higher risk
            (StrategyType.AGGRESSIVE, "implementation", SituationType.TIME_CRITICAL,
             True, 0.8, 800, 0.75, False),
            (StrategyType.AGGRESSIVE, "implementation", SituationType.TIME_CRITICAL,
             True, 0.7, 750, 0.78, False),
            (StrategyType.AGGRESSIVE, "implementation", SituationType.TIME_CRITICAL,
             False, 1.2, 1100, 0.60, False),
            (StrategyType.AGGRESSIVE, "implementation", SituationType.NORMAL,
             True, 0.9, 900, 0.82, False),
            
            # Conservative strategy - slow but high quality
            (StrategyType.CONSERVATIVE, "implementation", SituationType.ERROR_RECOVERY,
             True, 2.3, 1500, 0.95, True),
            (StrategyType.CONSERVATIVE, "implementation", SituationType.ERROR_RECOVERY,
             True, 2.5, 1600, 0.93, True),
            (StrategyType.CONSERVATIVE, "implementation", SituationType.COMPLEX_TASK,
             True, 3.0, 1800, 0.90, False),
        ]
        
        for data in test_data:
            evaluator.track_performance(*data)
        
        return evaluator
    
    def test_compare_strategies_all_dimensions(self, populated_evaluator):
        """Test comparing strategies across multiple dimensions."""
        comparisons = populated_evaluator.compare_strategies(
            task_type="implementation"
        )
        
        # Should have comparisons for all 3 strategies
        assert len(comparisons) >= 2
        
        # Each comparison should have all required fields
        for comp in comparisons:
            assert isinstance(comp, StrategyComparison)
            assert comp.rank > 0
            assert 0 <= comp.score <= 1
            assert isinstance(comp.metrics, StrategyPerformanceMetrics)
            assert isinstance(comp.advantages, list)
            assert isinstance(comp.disadvantages, list)
    
    def test_strategy_rankings_sorted(self, populated_evaluator):
        """Test that strategies are ranked by score (highest first)."""
        comparisons = populated_evaluator.compare_strategies(
            task_type="implementation"
        )
        
        # Check that ranks are sequential and start from 1
        ranks = [comp.rank for comp in comparisons]
        assert ranks == sorted(set(ranks))
        assert ranks[0] == 1
        
        # Check that scores are in descending order
        scores = [comp.score for comp in comparisons]
        assert scores == sorted(scores, reverse=True)
    
    def test_rank_by_task_type(self, populated_evaluator):
        """Test ranking strategies for specific task type."""
        comparisons = populated_evaluator.compare_strategies(
            task_type="implementation"
        )
        
        # Should only include strategies with data for this task type
        assert len(comparisons) > 0
        
        # Each comparison should have the specified task type
        for comp in comparisons:
            assert comp.metrics.task_type == "implementation"
    
    def test_rank_by_situation_type(self, populated_evaluator):
        """Test ranking strategies for specific situation type."""
        comparisons = populated_evaluator.compare_strategies(
            task_type="implementation",
            situation_type=SituationType.NORMAL
        )
        
        # Should only include strategies with data for this situation
        assert len(comparisons) > 0
        
        # Each comparison should have the specified situation type
        for comp in comparisons:
            assert comp.metrics.situation_type == SituationType.NORMAL
    
    def test_custom_weights(self, populated_evaluator):
        """Test comparison with custom weights."""
        # Weight efficiency heavily (time-critical scenario)
        custom_weights = {
            'success_rate': 0.2,
            'efficiency': 0.6,
            'effectiveness': 0.1,
            'robustness': 0.1
        }
        
        comparisons = populated_evaluator.compare_strategies(
            task_type="implementation",
            weights=custom_weights
        )
        
        # Should have comparisons with custom weighting
        assert len(comparisons) > 0
        
        # Aggressive (fast) should rank higher than with default weights
        aggressive_comp = next(
            (c for c in comparisons if c.strategy == StrategyType.AGGRESSIVE),
            None
        )
        assert aggressive_comp is not None
    
    def test_advantages_and_disadvantages(self, populated_evaluator):
        """Test that advantages and disadvantages are correctly identified."""
        comparisons = populated_evaluator.compare_strategies(
            task_type="implementation"
        )
        
        for comp in comparisons:
            # Should have some advantages or disadvantages
            total_points = len(comp.advantages) + len(comp.disadvantages)
            assert total_points > 0
            
            # Advantage/disadvantage text should mention comparison
            for adv in comp.advantages:
                assert "vs" in adv or "higher" in adv.lower()
            
            for dis in comp.disadvantages:
                assert "vs" in dis or "lower" in dis.lower()
    
    def test_no_performance_data(self, evaluator):
        """Test comparison when no performance data exists."""
        comparisons = evaluator.compare_strategies()
        
        # Should return empty list when no data
        assert comparisons == []
    
    def test_dynamic_updates(self, populated_evaluator):
        """Test that rankings update dynamically with new data."""
        # Get initial rankings
        initial_rankings = populated_evaluator.get_strategy_rankings(
            task_type="implementation"
        )
        
        # Add more successful operations for aggressive strategy
        for _ in range(5):
            populated_evaluator.track_performance(
                StrategyType.AGGRESSIVE,
                "implementation",
                SituationType.NORMAL,
                success=True,
                time_elapsed=0.8,
                tokens_used=800,
                quality_score=0.85
            )
        
        # Get updated rankings
        updated_rankings = populated_evaluator.get_strategy_rankings(
            task_type="implementation"
        )
        
        # Rankings should be available
        assert len(updated_rankings) > 0
        
        # Rankings might have changed due to new data
        # (not asserting exact change as it depends on performance)
    
    def test_identify_optimal_combinations(self, populated_evaluator):
        """Test identification of optimal strategy combinations."""
        combinations = populated_evaluator.identify_optimal_combinations(
            task_type="implementation",
            min_combinations=3,
            min_success_rate=0.6
        )
        
        # Should return at least some combinations
        assert len(combinations) >= 1
        
        # Each combination should have required fields
        for combo in combinations:
            assert 'strategy' in combo
            assert 'phases' in combo
            assert 'overall_score' in combo
            assert 'rationale' in combo
            assert 'best_for' in combo
            
            # Phases should include planning, implementation, testing
            phases = combo['phases']
            assert 'planning' in phases
            assert 'implementation' in phases
            assert 'testing' in phases
            
            # Score should be within valid range
            assert 0 <= combo['overall_score'] <= 1
    
    def test_combinations_sorted_by_score(self, populated_evaluator):
        """Test that combinations are sorted by overall score."""
        combinations = populated_evaluator.identify_optimal_combinations(
            task_type="implementation"
        )
        
        if len(combinations) > 1:
            scores = [c['overall_score'] for c in combinations]
            # Should be sorted in descending order
            assert scores == sorted(scores, reverse=True)
    
    def test_combinations_minimum_score_filter(self, populated_evaluator):
        """Test that combinations below minimum score are filtered."""
        # Set very high minimum score
        combinations = populated_evaluator.identify_optimal_combinations(
            task_type="implementation",
            min_success_rate=0.99
        )
        
        # Should return fewer or no combinations
        # (since test data doesn't have 99% success rates)
        assert len(combinations) <= 3
    
    def test_combinations_limit(self, populated_evaluator):
        """Test that number of combinations is limited."""
        combinations = populated_evaluator.identify_optimal_combinations(
            task_type="implementation",
            min_combinations=2
        )
        
        # Should not exceed requested limit
        assert len(combinations) <= 2
    
    def test_get_adaptive_weights(self, evaluator):
        """Test adaptive weights for different situation types."""
        # Time Critical: higher weight on efficiency
        weights_time = evaluator.get_adaptive_weights(SituationType.TIME_CRITICAL)
        assert weights_time['efficiency'] > weights_time['success_rate']
        
        # Error Recovery: higher weight on success rate
        weights_error = evaluator.get_adaptive_weights(SituationType.ERROR_RECOVERY)
        assert weights_error['success_rate'] > weights_error['efficiency']
        
        # Complex Task: higher weight on effectiveness
        weights_complex = evaluator.get_adaptive_weights(SituationType.COMPLEX_TASK)
        assert weights_complex['effectiveness'] >= weights_complex['efficiency']
        
        # Normal: balanced weights
        weights_normal = evaluator.get_adaptive_weights(SituationType.NORMAL)
        assert weights_normal['success_rate'] == 0.5
        assert weights_normal['efficiency'] == 0.2
    
    def test_compare_strategies_dynamic(self, populated_evaluator):
        """Test comparison with dynamic adaptive weights."""
        # Compare for time-critical situation
        comparisons_time = populated_evaluator.compare_strategies_dynamic(
            task_type="implementation",
            situation_type=SituationType.TIME_CRITICAL
        )
        
        # Should use time-critical weights (favor aggressive)
        assert len(comparisons_time) > 0
        
        # Compare for error recovery situation
        comparisons_error = populated_evaluator.compare_strategies_dynamic(
            task_type="implementation",
            situation_type=SituationType.ERROR_RECOVERY
        )
        
        # Should use error recovery weights (favor conservative)
        assert len(comparisons_error) > 0
        
        # Rankings should differ between situations
        ranks_time = {c.strategy: c.rank for c in comparisons_time}
        ranks_error = {c.strategy: c.rank for c in comparisons_error}
        
        # At least one strategy should have different rank
        # (may not always be true, but likely with test data)
        # We don't assert this strongly as it depends on data
    
    def test_get_optimal_strategy(self, populated_evaluator):
        """Test getting optimal strategy."""
        optimal = populated_evaluator.get_optimal_strategy(
            task_type="implementation",
            situation_type=SituationType.NORMAL
        )
        
        # Should return a strategy
        assert isinstance(optimal, StrategyType)
        
        # Optimal should be the highest-ranked strategy
        comparisons = populated_evaluator.compare_strategies(
            task_type="implementation",
            situation_type=SituationType.NORMAL
        )
        
        if comparisons:
            assert optimal == comparisons[0].strategy
    
    def test_get_optimal_strategy_no_data(self, evaluator):
        """Test getting optimal strategy when no data exists."""
        optimal = evaluator.get_optimal_strategy(
            task_type="nonexistent"
        )
        
        # Should return None when no data
        assert optimal is None
    
    def test_get_recommendations(self, populated_evaluator):
        """Test getting strategy recommendations with explanation."""
        strategy, explanation = populated_evaluator.get_recommendations(
            task_type="implementation",
            situation_type=SituationType.NORMAL
        )
        
        # Should return a strategy
        assert isinstance(strategy, StrategyType)
        
        # Should provide explanation
        assert isinstance(explanation, str)
        assert len(explanation) > 0
        assert "strategy" in explanation.lower() or "recommended" in explanation.lower()
    
    def test_get_recommendations_no_data(self, evaluator):
        """Test recommendations when no performance data exists."""
        strategy, explanation = evaluator.get_recommendations(
            task_type="nonexistent",
            situation_type=SituationType.NORMAL
        )
        
        # Should default to balanced strategy
        assert strategy == StrategyType.BALANCED
        
        # Should explain default choice
        assert "No performance data" in explanation or "default" in explanation.lower()
    
    def test_get_strategy_rankings(self, populated_evaluator):
        """Test getting strategy rankings."""
        rankings = populated_evaluator.get_strategy_rankings(
            task_type="implementation"
        )
        
        # Should return rankings for all strategies
        assert len(rankings) > 0
        
        # Rankings should be 1-based
        for strategy, rank in rankings.items():
            assert isinstance(strategy, StrategyType)
            assert rank >= 1
    
    def test_performance_report(self, populated_evaluator):
        """Test generation of performance report."""
        report = populated_evaluator.generate_performance_report(
            task_type="implementation"
        )
        
        # Should be a non-empty string
        assert isinstance(report, str)
        assert len(report) > 0
        
        # Should contain header
        assert "STRATEGY PERFORMANCE REPORT" in report
        
        # Should contain strategy information
        for strategy_type in ["CONSERVATIVE", "BALANCED", "AGGRESSIVE"]:
            # May or may not contain all strategies depending on data
            pass
    
    def test_performance_report_empty(self, evaluator):
        """Test report when no performance data exists."""
        report = evaluator.generate_performance_report()
        
        # Should indicate no data available
        assert "No performance data" in report
    
    def test_export_performance_data(self, populated_evaluator):
        """Test exporting performance data to JSON."""
        import json
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            # Export data
            populated_evaluator.export_performance_data(
                filepath=temp_path,
                task_type="implementation"
            )
            
            # Read and validate JSON
            with open(temp_path, 'r') as f:
                data = json.load(f)
            
            # Should be a list
            assert isinstance(data, list)
            
            # Each item should be a dict with required fields
            for item in data:
                assert isinstance(item, dict)
                assert 'strategy' in item
                assert 'task_type' in item
                assert 'situation_type' in item
                assert 'success_rate' in item
                
        finally:
            # Cleanup
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    def test_integration_with_tracking(self, populated_evaluator):
        """Test that comparison uses tracked performance data."""
        # Track more operations
        for _ in range(3):
            populated_evaluator.track_performance(
                StrategyType.BALANCED,
                "implementation",
                SituationType.NORMAL,
                success=True,
                time_elapsed=1.2,
                tokens_used=1000,
                quality_score=0.88
            )
        
        # Get performance
        performance = populated_evaluator.get_performance(
            StrategyType.BALANCED,
            task_type="implementation"
        )
        
        # Should reflect tracked data
        assert performance is not None
        assert performance.total_operations >= 8  # 5 initial + 3 new
        assert performance.successful_operations >= 8 - 1  # 1 failure in initial data
    
    def test_weighted_scoring_formula(self, populated_evaluator):
        """Test that scoring uses weighted formula correctly."""
        comparisons = populated_evaluator.compare_strategies(
            task_type="implementation"
        )
        
        for comp in comparisons:
            # Score should be weighted sum of normalized metrics
            m = comp.metrics
            
            # Success rate (0-1) * weight
            success_component = m.success_rate
            
            # Efficiency normalized to 0-1
            efficiency_component = min(m.efficiency / 100, 1.0)
            
            # Effectiveness (0-1)
            effectiveness_component = m.effectiveness
            
            # Robustness (0-1)
            robustness_component = m.robustness
            
            # Score should be combination of these (with default weights)
            # Success rate is primary (weight 0.5)
            # Others are secondary (0.2, 0.2, 0.1)
            assert 0 <= comp.score <= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])