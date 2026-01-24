"""
Unit tests for Strategy Hybridizer - V4 Adaptive Reasoning System
"""

import pytest
from v3.logic.strategy_hybridizer import (
    StrategyHybridizer,
    StrategyMix,
    HybridStrategyType,
    StrategyPhase
)


class TestStrategyMix:
    """Test StrategyMix class."""
    
    def test_strategy_mix_valid(self):
        """Test creating a valid strategy mix."""
        mix = StrategyMix(
            strategies=["conservative", "balanced"],
            weights=[0.4, 0.6]
        )
        
        assert mix.strategies == ["conservative", "balanced"]
        assert mix.weights == [0.4, 0.6]
        assert mix.strategy_dict == {"conservative": 0.4, "balanced": 0.6}
    
    def test_strategy_mix_single_strategy(self):
        """Test creating a strategy mix with single strategy."""
        mix = StrategyMix(
            strategies=["balanced"],
            weights=[1.0]
        )
        
        assert mix.strategies == ["balanced"]
        assert mix.weights == [1.0]
        assert mix.get_dominant_strategy() == "balanced"
    
    def test_strategy_mix_length_mismatch(self):
        """Test error when strategies and weights lengths don't match."""
        with pytest.raises(ValueError, match="same length"):
            StrategyMix(
                strategies=["conservative", "balanced"],
                weights=[0.5]
            )
    
    def test_strategy_mix_empty_strategies(self):
        """Test error when no strategies provided."""
        with pytest.raises(ValueError, match="At least one strategy"):
            StrategyMix(
                strategies=[],
                weights=[]
            )
    
    def test_strategy_mix_weights_not_sum_to_one(self):
        """Test error when weights don't sum to 1.0."""
        with pytest.raises(ValueError, match="sum to 1.0"):
            StrategyMix(
                strategies=["conservative", "balanced"],
                weights=[0.3, 0.4]
            )
    
    def test_get_dominant_strategy(self):
        """Test getting dominant strategy."""
        mix = StrategyMix(
            strategies=["conservative", "balanced", "aggressive"],
            weights=[0.2, 0.6, 0.2]
        )
        
        assert mix.get_dominant_strategy() == "balanced"
    
    def test_get_weight(self):
        """Test getting weight for specific strategy."""
        mix = StrategyMix(
            strategies=["conservative", "balanced"],
            weights=[0.4, 0.6]
        )
        
        assert mix.get_weight("conservative") == 0.4
        assert mix.get_weight("balanced") == 0.6
        assert mix.get_weight("aggressive") == 0.0
    
    def test_to_dict(self):
        """Test converting strategy mix to dictionary."""
        mix = StrategyMix(
            strategies=["conservative", "balanced"],
            weights=[0.4, 0.6]
        )
        
        result = mix.to_dict()
        
        assert result["strategies"] == ["conservative", "balanced"]
        assert result["weights"] == [0.4, 0.6]
        assert result["dominant_strategy"] == "balanced"


class TestStrategyHybridizer:
    """Test StrategyHybridizer class."""
    
    def test_initialization(self):
        """Test hybridizer initialization."""
        hybridizer = StrategyHybridizer()
        
        assert hybridizer.performance_history == {}
        assert hybridizer.optimal_combinations == {}
        assert len(hybridizer.default_hybrids) == 5
        assert len(hybridizer.phase_strategies) == 5
    
    def test_create_phase_based_hybrid(self):
        """Test creating phase-based hybrid strategy."""
        hybridizer = StrategyHybridizer()
        
        # Test planning phase
        mix = hybridizer.create_phase_based_hybrid(StrategyPhase.PLANNING)
        assert "conservative" in mix.strategies
        assert "balanced" in mix.strategies
        assert mix.get_weight("conservative") > mix.get_weight("balanced")
        
        # Test implementation phase
        mix = hybridizer.create_phase_based_hybrid(StrategyPhase.IMPLEMENTATION)
        assert "balanced" in mix.strategies
        assert "aggressive" in mix.strategies
        
        # Test testing phase
        mix = hybridizer.create_phase_based_hybrid(StrategyPhase.TESTING)
        assert mix.strategies == ["conservative"]
        assert mix.weights == [1.0]
    
    def test_create_phase_based_hybrid_custom(self):
        """Test creating phase-based hybrid with custom mix."""
        hybridizer = StrategyHybridizer()
        
        custom_mix = StrategyMix(
            strategies=["aggressive"],
            weights=[1.0]
        )
        
        mix = hybridizer.create_phase_based_hybrid(
            StrategyPhase.PLANNING,
            custom_mix=custom_mix
        )
        
        assert mix.strategies == ["aggressive"]
    
    def test_create_risk_based_hybrid(self):
        """Test creating risk-based hybrid strategy."""
        hybridizer = StrategyHybridizer()
        
        # High risk
        mix = hybridizer.create_risk_based_hybrid(risk_level=0.8)
        assert mix.get_dominant_strategy() == "conservative"
        assert mix.get_weight("conservative") >= 0.7
        
        # Medium risk
        mix = hybridizer.create_risk_based_hybrid(risk_level=0.5)
        assert mix.strategies == ["balanced"]
        
        # Low risk
        mix = hybridizer.create_risk_based_hybrid(risk_level=0.2)
        assert mix.get_dominant_strategy() == "aggressive"
        assert mix.get_weight("aggressive") >= 0.5
    
    def test_create_risk_based_hybrid_custom(self):
        """Test creating risk-based hybrid with custom mix."""
        hybridizer = StrategyHybridizer()
        
        custom_mix = StrategyMix(
            strategies=["balanced"],
            weights=[1.0]
        )
        
        mix = hybridizer.create_risk_based_hybrid(
            risk_level=0.9,
            custom_mix=custom_mix
        )
        
        assert mix.strategies == ["balanced"]
    
    def test_create_progress_based_hybrid(self):
        """Test creating progress-based hybrid strategy."""
        hybridizer = StrategyHybridizer()
        
        # Excellent progress
        mix = hybridizer.create_progress_based_hybrid(progress_rate=0.6)
        assert mix.get_dominant_strategy() == "aggressive"
        assert mix.get_weight("aggressive") >= 0.6
        
        # Expected progress
        mix = hybridizer.create_progress_based_hybrid(progress_rate=0.3)
        assert mix.strategies == ["balanced"]
        
        # Minimal progress
        mix = hybridizer.create_progress_based_hybrid(progress_rate=0.15)
        assert mix.get_dominant_strategy() == "conservative"
        assert mix.get_weight("conservative") >= 0.5
        
        # No progress
        mix = hybridizer.create_progress_based_hybrid(progress_rate=0.05)
        assert mix.strategies == ["conservative"]
    
    def test_create_progress_based_hybrid_custom(self):
        """Test creating progress-based hybrid with custom mix."""
        hybridizer = StrategyHybridizer()
        
        custom_mix = StrategyMix(
            strategies=["balanced"],
            weights=[1.0]
        )
        
        mix = hybridizer.create_progress_based_hybrid(
            progress_rate=0.8,
            custom_mix=custom_mix
        )
        
        assert mix.strategies == ["balanced"]
    
    def test_create_adaptive_mix(self):
        """Test creating adaptive mix based on multiple metrics."""
        hybridizer = StrategyHybridizer()
        
        # High progress, low risk, low errors, no time pressure
        metrics = {
            "progress_rate": 0.6,
            "risk": 0.2,
            "error_rate": 0.05,
            "time_pressure": 0.3
        }
        
        mix = hybridizer.create_adaptive_mix(metrics)
        
        # Should lean towards aggressive
        assert "aggressive" in mix.strategies or "balanced" in mix.strategies
        
        # Low progress, high risk, high errors
        metrics = {
            "progress_rate": 0.05,
            "risk": 0.8,
            "error_rate": 0.4,
            "time_pressure": 0.5
        }
        
        mix = hybridizer.create_adaptive_mix(metrics)
        
        # Should lean towards conservative
        assert "conservative" in mix.strategies
    
    def test_create_adaptive_mix_with_learned_optimal(self):
        """Test creating adaptive mix with learned optimal combination."""
        hybridizer = StrategyHybridizer()
        
        # Learn an optimal combination
        task_type = "feature_development"
        optimal_mix = StrategyMix(
            strategies=["balanced", "aggressive"],
            weights=[0.6, 0.4]
        )
        hybridizer.optimal_combinations[task_type] = optimal_mix
        
        metrics = {"progress_rate": 0.4}
        
        mix = hybridizer.create_adaptive_mix(metrics, task_type=task_type)
        
        assert mix == optimal_mix
    
    def test_adjust_strategy_mix(self):
        """Test adjusting strategy mix based on metrics."""
        hybridizer = StrategyHybridizer()
        
        current_mix = StrategyMix(
            strategies=["balanced"],
            weights=[1.0]
        )
        
        # Low progress - should shift towards conservative
        metrics = {
            "progress_rate": 0.05,
            "risk": 0.5
        }
        
        adjusted = hybridizer.adjust_strategy_mix(current_mix, metrics)
        
        # Should now include conservative
        assert "conservative" in adjusted.strategies
        
        # High progress - should shift towards aggressive
        metrics = {
            "progress_rate": 0.6,
            "risk": 0.5
        }
        
        adjusted = hybridizer.adjust_strategy_mix(current_mix, metrics)
        
        # Should now include aggressive
        assert "aggressive" in adjusted.strategies
    
    def test_adjust_strategy_mix_custom_factor(self):
        """Test adjusting strategy mix with custom factor."""
        hybridizer = StrategyHybridizer()
        
        current_mix = StrategyMix(
            strategies=["balanced"],
            weights=[1.0]
        )
        
        metrics = {"progress_rate": 0.05, "risk": 0.5}
        
        # Small adjustment
        adjusted_small = hybridizer.adjust_strategy_mix(
            current_mix,
            metrics,
            adjustment_factor=0.1
        )
        
        # Large adjustment
        adjusted_large = hybridizer.adjust_strategy_mix(
            current_mix,
            metrics,
            adjustment_factor=0.5
        )
        
        # Larger factor should result in bigger shift
        cons_weight_small = adjusted_small.get_weight("conservative")
        cons_weight_large = adjusted_large.get_weight("conservative")
        
        assert cons_weight_large > cons_weight_small
    
    def test_validate_hybrid_performance_success(self):
        """Test validating successful hybrid performance."""
        hybridizer = StrategyHybridizer()
        
        hybrid_id = "test_hybrid_001"
        metrics = {
            "progress_rate": 0.4,
            "error_rate": 0.1,
            "resource_efficiency": 0.8
        }
        
        result = hybridizer.validate_hybrid_performance(
            hybrid_id,
            metrics,
            success=True
        )
        
        assert result["hybrid_id"] == hybrid_id
        assert result["success"] is True
        assert result["valid"] is True
        assert len(result["issues"]) == 0
        
        # Should be recorded in history
        assert hybrid_id in hybridizer.performance_history
        assert len(hybridizer.performance_history[hybrid_id]) == 1
    
    def test_validate_hybrid_performance_failure(self):
        """Test validating failed hybrid performance."""
        hybridizer = StrategyHybridizer()
        
        hybrid_id = "test_hybrid_002"
        metrics = {
            "progress_rate": 0.05,
            "error_rate": 0.5,
            "resource_efficiency": 0.3
        }
        
        result = hybridizer.validate_hybrid_performance(
            hybrid_id,
            metrics,
            success=False
        )
        
        assert result["valid"] is False
        assert len(result["issues"]) > 0
        assert "Operation failed" in result["issues"]
        
        # Should provide recommendations
        assert len(result["recommendations"]) > 0
    
    def test_validate_hybrid_performance_low_progress(self):
        """Test validating hybrid with low progress."""
        hybridizer = StrategyHybridizer()
        
        hybrid_id = "test_hybrid_003"
        metrics = {
            "progress_rate": 0.05,
            "error_rate": 0.1,
            "resource_efficiency": 0.8
        }
        
        result = hybridizer.validate_hybrid_performance(
            hybrid_id,
            metrics,
            success=True
        )
        
        assert result["valid"] is False
        assert "Progress rate below minimal threshold" in result["issues"]
    
    def test_validate_hybrid_performance_high_errors(self):
        """Test validating hybrid with high error rate."""
        hybridizer = StrategyHybridizer()
        
        hybrid_id = "test_hybrid_004"
        metrics = {
            "progress_rate": 0.3,
            "error_rate": 0.5,
            "resource_efficiency": 0.8
        }
        
        result = hybridizer.validate_hybrid_performance(
            hybrid_id,
            metrics,
            success=True
        )
        
        assert result["valid"] is False
        assert "High error rate" in result["issues"]
    
    def test_learn_optimal_combination_insufficient_data(self):
        """Test learning optimal combination with insufficient data."""
        hybridizer = StrategyHybridizer()
        
        hybrid_id = "test_hybrid_005"
        
        # Add only 5 records (need 10)
        for _ in range(5):
            hybridizer.validate_hybrid_performance(
                hybrid_id,
                {"progress_rate": 0.4, "error_rate": 0.1},
                success=True
            )
        
        result = hybridizer.learn_optimal_combination("test_task", hybrid_id)
        
        assert result is None
        assert "test_task" not in hybridizer.optimal_combinations
    
    def test_learn_optimal_combination_low_success_rate(self):
        """Test learning optimal combination with low success rate."""
        hybridizer = StrategyHybridizer()
        
        hybrid_id = "test_hybrid_006"
        
        # Add 10 records with only 5 successes (50% rate, need 70%)
        for i in range(10):
            hybridizer.validate_hybrid_performance(
                hybrid_id,
                {"progress_rate": 0.4, "error_rate": 0.1},
                success=(i < 5)  # First 5 succeed
            )
        
        result = hybridizer.learn_optimal_combination("test_task", hybrid_id)
        
        assert result is None
        assert "test_task" not in hybridizer.optimal_combinations
    
    def test_learn_optimal_combination_success(self):
        """Test successful learning of optimal combination."""
        hybridizer = StrategyHybridizer()
        
        hybrid_id = "test_hybrid_007"
        
        # Add 10 records with 9 successes (90% rate)
        for i in range(10):
            hybridizer.validate_hybrid_performance(
                hybrid_id,
                {"progress_rate": 0.4, "error_rate": 0.1, "risk": 0.3},
                success=(i < 9)  # First 9 succeed
            )
        
        result = hybridizer.learn_optimal_combination("test_task", hybrid_id)
        
        assert result is not None
        assert isinstance(result, StrategyMix)
        assert "test_task" in hybridizer.optimal_combinations
    
    def test_get_performance_summary_not_found(self):
        """Test getting performance summary for non-existent hybrid."""
        hybridizer = StrategyHybridizer()
        
        result = hybridizer.get_performance_summary("non_existent")
        
        assert result is None
    
    def test_get_performance_summary(self):
        """Test getting performance summary."""
        hybridizer = StrategyHybridizer()
        
        hybrid_id = "test_hybrid_008"
        
        # Add some performance data
        hybridizer.validate_hybrid_performance(
            hybrid_id,
            {"progress_rate": 0.4, "error_rate": 0.1},
            success=True
        )
        hybridizer.validate_hybrid_performance(
            hybrid_id,
            {"progress_rate": 0.5, "error_rate": 0.05},
            success=True
        )
        hybridizer.validate_hybrid_performance(
            hybrid_id,
            {"progress_rate": 0.3, "error_rate": 0.15},
            success=False
        )
        
        summary = hybridizer.get_performance_summary(hybrid_id)
        
        assert summary is not None
        assert summary["hybrid_id"] == hybrid_id
        assert summary["total_operations"] == 3
        assert summary["successes"] == 2
        assert summary["failures"] == 1
        assert summary["success_rate"] == 2/3
        
        # Check average metrics
        assert "average_metrics" in summary
        assert "progress_rate" in summary["average_metrics"]
        assert abs(summary["average_metrics"]["progress_rate"]["average"] - 0.4) < 0.001
    
    def test_get_default_hybrid(self):
        """Test getting default hybrid for situation type."""
        hybridizer = StrategyHybridizer()
        
        # Normal situation
        mix = hybridizer.get_default_hybrid("normal")
        assert mix.strategies == ["balanced"]
        
        # Complex situation
        mix = hybridizer.get_default_hybrid("complex")
        assert "conservative" in mix.strategies
        assert "balanced" in mix.strategies
        
        # Time critical
        mix = hybridizer.get_default_hybrid("time_critical")
        assert "balanced" in mix.strategies
        assert "aggressive" in mix.strategies
        
        # Unknown situation - should default to "normal"
        mix = hybridizer.get_default_hybrid("unknown")
        assert mix.strategies == ["balanced"]
    
    def test_generate_hybrid_id(self):
        """Test generating unique hybrid IDs."""
        hybridizer = StrategyHybridizer()
        
        id1 = hybridizer.generate_hybrid_id()
        id2 = hybridizer.generate_hybrid_id()
        
        assert id1.startswith("hybrid_")
        assert id2.startswith("hybrid_")
        assert id1 != id2
        assert len(id1) == 19  # "hybrid_" + 12 char uuid
    
    def test_clear_history_specific(self):
        """Test clearing history for specific hybrid."""
        hybridizer = StrategyHybridizer()
        
        hybrid_id = "test_hybrid_009"
        hybridizer.validate_hybrid_performance(
            hybrid_id,
            {"progress_rate": 0.4},
            success=True
        )
        
        assert hybrid_id in hybridizer.performance_history
        
        hybridizer.clear_history(hybrid_id)
        
        assert hybrid_id not in hybridizer.performance_history
    
    def test_clear_history_all(self):
        """Test clearing all history."""
        hybridizer = StrategyHybridizer()
        
        # Add multiple hybrids
        hybridizer.validate_hybrid_performance(
            "h1",
            {"progress_rate": 0.4},
            success=True
        )
        hybridizer.validate_hybrid_performance(
            "h2",
            {"progress_rate": 0.5},
            success=True
        )
        
        assert len(hybridizer.performance_history) == 2
        
        hybridizer.clear_history()
        
        assert len(hybridizer.performance_history) == 0
    
    def test_reset_optimal_combinations_specific(self):
        """Test resetting optimal combination for specific task type."""
        hybridizer = StrategyHybridizer()
        
        task_type = "test_task"
        hybridizer.optimal_combinations[task_type] = StrategyMix(
            strategies=["balanced"],
            weights=[1.0]
        )
        
        assert task_type in hybridizer.optimal_combinations
        
        hybridizer.reset_optimal_combinations(task_type)
        
        assert task_type not in hybridizer.optimal_combinations
    
    def test_reset_optimal_combinations_all(self):
        """Test resetting all optimal combinations."""
        hybridizer = StrategyHybridizer()
        
        hybridizer.optimal_combinations["task1"] = StrategyMix(
            strategies=["balanced"],
            weights=[1.0]
        )
        hybridizer.optimal_combinations["task2"] = StrategyMix(
            strategies=["conservative"],
            weights=[1.0]
        )
        
        assert len(hybridizer.optimal_combinations) == 2
        
        hybridizer.reset_optimal_combinations()
        
        assert len(hybridizer.optimal_combinations) == 0


class TestHybridStrategyWorkflows:
    """Test complete hybrid strategy workflows."""
    
    def test_phase_based_workflow(self):
        """Test complete phase-based workflow."""
        hybridizer = StrategyHybridizer()
        
        # Start with planning
        planning_mix = hybridizer.create_phase_based_hybrid(
            StrategyPhase.PLANNING
        )
        
        # Move to implementation
        impl_mix = hybridizer.create_phase_based_hybrid(
            StrategyPhase.IMPLEMENTATION
        )
        
        # Move to testing
        testing_mix = hybridizer.create_phase_based_hybrid(
            StrategyPhase.TESTING
        )
        
        # Validate each phase
        assert planning_mix.get_dominant_strategy() == "conservative"
        assert impl_mix.get_dominant_strategy() == "balanced"
        assert testing_mix.get_dominant_strategy() == "conservative"
    
    def test_adaptive_workflow_with_learning(self):
        """Test adaptive workflow with learning."""
        hybridizer = StrategyHybridizer()
        
        hybrid_id = hybridizer.generate_hybrid_id()
        task_type = "feature_development"
        
        # Simulate multiple operations
        for i in range(15):
            success = i < 13  # 13/15 success rate
            metrics = {
                "progress_rate": 0.35 + (0.01 * i),
                "error_rate": 0.1 - (0.005 * i),
                "resource_efficiency": 0.8
            }
            
            hybridizer.validate_hybrid_performance(
                hybrid_id,
                metrics,
                success=success
            )
        
        # Learn optimal combination
        optimal = hybridizer.learn_optimal_combination(task_type, hybrid_id)
        
        assert optimal is not None
        assert task_type in hybridizer.optimal_combinations
        
        # Use learned combination
        new_mix = hybridizer.create_adaptive_mix(
            {"progress_rate": 0.4},
            task_type=task_type
        )
        
        assert new_mix == optimal
    
    def test_risk_and_progress_combined(self):
        """Test combining risk and progress in adaptive mix."""
        hybridizer = StrategyHybridizer()
        
        # High risk but good progress - should balance
        metrics = {
            "progress_rate": 0.6,
            "risk": 0.8,
            "error_rate": 0.1,
            "time_pressure": 0.5
        }
        
        mix = hybridizer.create_adaptive_mix(metrics)
        
        # Should have mix of strategies
        assert len(mix.strategies) >= 2
        
        # Should include both conservative (due to risk) and aggressive (due to progress)
        strategies_set = set(mix.strategies)
        assert "conservative" in strategies_set or "balanced" in strategies_set
        assert "aggressive" in strategies_set or "balanced" in strategies_set