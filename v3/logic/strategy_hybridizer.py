"""
Strategy Hybridizer - V4 Adaptive Reasoning System

This module implements strategy hybridization for complex situations, combining multiple
strategies dynamically based on task progress, risk, and other factors.
"""

import uuid
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime
from enum import Enum


class HybridStrategyType(Enum):
    """Types of hybrid strategies."""
    PHASE_BASED = "phase_based"  # Different strategy per phase
    RISK_BASED = "risk_based"    # Conservative for high-risk, aggressive for low-risk
    PROGRESS_BASED = "progress_based"  # Conservative when stuck, aggressive when progressing
    ADAPTIVE_MIX = "adaptive_mix"  # Dynamic mix based on real-time metrics


class StrategyPhase(Enum):
    """Phases for phase-based hybrid strategies."""
    PLANNING = "planning"
    IMPLEMENTATION = "implementation"
    TESTING = "testing"
    DEPLOYMENT = "deployment"
    MAINTENANCE = "maintenance"


class StrategyMix:
    """Represents a mix of strategies with their weights."""
    
    def __init__(self, strategies: List[str], weights: List[float]):
        """
        Initialize strategy mix.
        
        Args:
            strategies: List of strategy names (e.g., ['conservative', 'balanced', 'aggressive'])
            weights: List of weights (should sum to 1.0)
        """
        if len(strategies) != len(weights):
            raise ValueError("Strategies and weights must have the same length")
        
        if not strategies:
            raise ValueError("At least one strategy must be provided")
        
        total_weight = sum(weights)
        if abs(total_weight - 1.0) > 0.001:
            raise ValueError(f"Weights must sum to 1.0, got {total_weight}")
        
        self.strategies = strategies
        self.weights = weights
        self.strategy_dict = dict(zip(strategies, weights))
    
    def get_dominant_strategy(self) -> str:
        """Get the strategy with the highest weight."""
        return self.strategies[self.weights.index(max(self.weights))]
    
    def get_weight(self, strategy: str) -> float:
        """Get weight for a specific strategy."""
        return self.strategy_dict.get(strategy, 0.0)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "strategies": self.strategies,
            "weights": self.weights,
            "dominant_strategy": self.get_dominant_strategy()
        }


class StrategyHybridizer:
    """
    Strategy Hybridizer for combining multiple strategies in complex situations.
    
    This class enables:
    - Combining multiple strategies for complex tasks
    - Dynamically adjusting strategy mix based on progress
    - Using conservative strategy for critical steps
    - Using aggressive strategy for routine steps
    - Validating hybrid strategy performance
    - Learning optimal strategy combinations
    """
    
    def __init__(self):
        """Initialize strategy hybridizer."""
        # Track hybrid strategy performance
        self.performance_history: Dict[str, List[Dict[str, Any]]] = {}
        
        # Track optimal combinations learned per task type
        self.optimal_combinations: Dict[str, StrategyMix] = {}
        
        # Default hybrid strategies for different situations
        self.default_hybrids = {
            "normal": StrategyMix(
                strategies=["balanced"],
                weights=[1.0]
            ),
            "complex": StrategyMix(
                strategies=["conservative", "balanced"],
                weights=[0.4, 0.6]
            ),
            "time_critical": StrategyMix(
                strategies=["balanced", "aggressive"],
                weights=[0.3, 0.7]
            ),
            "error_recovery": StrategyMix(
                strategies=["conservative"],
                weights=[1.0]
            ),
            "testing": StrategyMix(
                strategies=["conservative", "balanced"],
                weights=[0.7, 0.3]
            )
        }
        
        # Phase-based strategies
        self.phase_strategies = {
            StrategyPhase.PLANNING: StrategyMix(
                strategies=["conservative", "balanced"],
                weights=[0.6, 0.4]
            ),
            StrategyPhase.IMPLEMENTATION: StrategyMix(
                strategies=["balanced", "aggressive"],
                weights=[0.7, 0.3]
            ),
            StrategyPhase.TESTING: StrategyMix(
                strategies=["conservative"],
                weights=[1.0]
            ),
            StrategyPhase.DEPLOYMENT: StrategyMix(
                strategies=["conservative", "balanced"],
                weights=[0.8, 0.2]
            ),
            StrategyPhase.MAINTENANCE: StrategyMix(
                strategies=["balanced"],
                weights=[1.0]
            )
        }
        
        # Progress thresholds for progress-based adjustment
        self.progress_thresholds = {
            "optimal": 0.5,    # 50% progress per operation
            "expected": 0.3,    # 30% progress per operation
            "minimal": 0.1      # 10% progress per operation
        }
    
    def create_phase_based_hybrid(
        self,
        current_phase: StrategyPhase,
        custom_mix: Optional[StrategyMix] = None
    ) -> StrategyMix:
        """
        Create phase-based hybrid strategy.
        
        Args:
            current_phase: Current phase of task execution
            custom_mix: Optional custom mix to use instead of default
        
        Returns:
            StrategyMix: Strategy mix for current phase
        """
        if custom_mix:
            return custom_mix
        
        return self.phase_strategies.get(
            current_phase,
            self.default_hybrids["normal"]
        )
    
    def create_risk_based_hybrid(
        self,
        risk_level: float,  # 0.0 to 1.0
        custom_mix: Optional[StrategyMix] = None
    ) -> StrategyMix:
        """
        Create risk-based hybrid strategy.
        
        Args:
            risk_level: Risk level (0.0 = low risk, 1.0 = high risk)
            custom_mix: Optional custom mix to use instead of default
        
        Returns:
            StrategyMix: Strategy mix based on risk level
        """
        if custom_mix:
            return custom_mix
        
        # High risk: More conservative
        # Low risk: More aggressive
        if risk_level >= 0.7:
            # High risk: Conservative-heavy
            return StrategyMix(
                strategies=["conservative", "balanced"],
                weights=[0.8, 0.2]
            )
        elif risk_level >= 0.4:
            # Medium risk: Balanced
            return StrategyMix(
                strategies=["balanced"],
                weights=[1.0]
            )
        else:
            # Low risk: Aggressive-leaning
            return StrategyMix(
                strategies=["balanced", "aggressive"],
                weights=[0.4, 0.6]
            )
    
    def create_progress_based_hybrid(
        self,
        progress_rate: float,  # 0.0 to 1.0
        custom_mix: Optional[StrategyMix] = None
    ) -> StrategyMix:
        """
        Create progress-based hybrid strategy.
        
        Args:
            progress_rate: Current progress rate (0.0 to 1.0)
            custom_mix: Optional custom mix to use instead of default
        
        Returns:
            StrategyMix: Strategy mix based on progress
        """
        if custom_mix:
            return custom_mix
        
        # Dynamic adjustment based on progress
        if progress_rate >= self.progress_thresholds["optimal"]:
            # Making excellent progress: Switch to more aggressive
            return StrategyMix(
                strategies=["balanced", "aggressive"],
                weights=[0.3, 0.7]
            )
        elif progress_rate >= self.progress_thresholds["expected"]:
            # Making expected progress: Balanced
            return StrategyMix(
                strategies=["balanced"],
                weights=[1.0]
            )
        elif progress_rate >= self.progress_thresholds["minimal"]:
            # Making minimal progress: More conservative
            return StrategyMix(
                strategies=["conservative", "balanced"],
                weights=[0.6, 0.4]
            )
        else:
            # Not making progress: Fully conservative
            return StrategyMix(
                strategies=["conservative"],
                weights=[1.0]
            )
    
    def create_adaptive_mix(
        self,
        metrics: Dict[str, float],
        task_type: Optional[str] = None
    ) -> StrategyMix:
        """
        Create adaptive hybrid strategy based on multiple metrics.
        
        Args:
            metrics: Dictionary of metrics (e.g., {"progress_rate": 0.4, "risk": 0.3})
            task_type: Optional task type for learned optimal combinations
        
        Returns:
            StrategyMix: Adaptive strategy mix
        """
        # Check if we have a learned optimal combination for this task type
        if task_type and task_type in self.optimal_combinations:
            return self.optimal_combinations[task_type]
        
        # Calculate strategy weights based on metrics
        conservative_weight = 0.0
        balanced_weight = 0.0
        aggressive_weight = 0.0
        
        # Factor 1: Progress rate
        progress_rate = metrics.get("progress_rate", 0.3)
        if progress_rate < self.progress_thresholds["minimal"]:
            conservative_weight += 0.4
        elif progress_rate < self.progress_thresholds["expected"]:
            conservative_weight += 0.2
            balanced_weight += 0.2
        elif progress_rate > self.progress_thresholds["optimal"]:
            aggressive_weight += 0.3
        else:
            balanced_weight += 0.3
        
        # Factor 2: Risk level
        risk = metrics.get("risk", 0.5)
        if risk >= 0.7:
            conservative_weight += 0.3
        elif risk <= 0.3:
            aggressive_weight += 0.2
        else:
            balanced_weight += 0.2
        
        # Factor 3: Error rate
        error_rate = metrics.get("error_rate", 0.1)
        if error_rate > 0.3:
            conservative_weight += 0.3
        elif error_rate < 0.1:
            aggressive_weight += 0.2
        else:
            balanced_weight += 0.2
        
        # Factor 4: Time pressure
        time_pressure = metrics.get("time_pressure", 0.5)
        if time_pressure > 0.7:
            aggressive_weight += 0.3
        elif time_pressure < 0.3:
            conservative_weight += 0.2
        else:
            balanced_weight += 0.2
        
        # Normalize weights to sum to 1.0
        total = conservative_weight + balanced_weight + aggressive_weight
        if total > 0:
            conservative_weight /= total
            balanced_weight /= total
            aggressive_weight /= total
        else:
            # Default to balanced if no factors
            balanced_weight = 1.0
        
        # Create strategy mix
        strategies = []
        weights = []
        
        if conservative_weight > 0.1:
            strategies.append("conservative")
            weights.append(conservative_weight)
        
        if balanced_weight > 0.1:
            strategies.append("balanced")
            weights.append(balanced_weight)
        
        if aggressive_weight > 0.1:
            strategies.append("aggressive")
            weights.append(aggressive_weight)
        
        # Fallback to balanced if no strategies selected
        if not strategies:
            strategies = ["balanced"]
            weights = [1.0]
        
        # Normalize again
        total = sum(weights)
        weights = [w / total for w in weights]
        
        return StrategyMix(strategies=strategies, weights=weights)
    
    def adjust_strategy_mix(
        self,
        current_mix: StrategyMix,
        metrics: Dict[str, float],
        adjustment_factor: float = 0.2
    ) -> StrategyMix:
        """
        Adjust strategy mix based on current metrics.
        
        Args:
            current_mix: Current strategy mix
            metrics: Current metrics
            adjustment_factor: How much to adjust (0.0 to 1.0)
        
        Returns:
            StrategyMix: Adjusted strategy mix
        """
        progress_rate = metrics.get("progress_rate", 0.3)
        risk = metrics.get("risk", 0.5)
        
        # Initialize with all possible strategies
        strategy_weights = {
            "conservative": 0.0,
            "balanced": 0.0,
            "aggressive": 0.0
        }
        
        # Start with current mix weights
        for strategy, weight in zip(current_mix.strategies, current_mix.weights):
            strategy_weights[strategy] = weight
        
        # Adjust based on progress
        if progress_rate < self.progress_thresholds["minimal"]:
            # Shift towards conservative
            strategy_weights["conservative"] += adjustment_factor * 0.5
            strategy_weights["aggressive"] -= adjustment_factor * 0.5
        elif progress_rate > self.progress_thresholds["optimal"]:
            # Shift towards aggressive
            strategy_weights["aggressive"] += adjustment_factor * 0.5
            strategy_weights["conservative"] -= adjustment_factor * 0.5
        
        # Adjust based on risk
        if risk > 0.7:
            # Shift towards conservative
            strategy_weights["conservative"] += adjustment_factor * 0.3
            strategy_weights["aggressive"] -= adjustment_factor * 0.3
        elif risk < 0.3:
            # Shift towards aggressive
            strategy_weights["aggressive"] += adjustment_factor * 0.3
            strategy_weights["conservative"] -= adjustment_factor * 0.3
        
        # Ensure weights are non-negative
        for strategy in strategy_weights:
            strategy_weights[strategy] = max(0.0, strategy_weights[strategy])
        
        # Normalize to sum to 1.0
        total = sum(strategy_weights.values())
        if total > 0:
            for strategy in strategy_weights:
                strategy_weights[strategy] /= total
        else:
            # Fallback to balanced
            strategy_weights["balanced"] = 1.0
        
        # Remove strategies with zero weight (threshold 0.01)
        strategies = [s for s in strategy_weights if strategy_weights[s] > 0.01]
        weights = [strategy_weights[s] for s in strategies]
        
        # Fallback to balanced if no strategies left
        if not strategies:
            strategies = ["balanced"]
            weights = [1.0]
        
        return StrategyMix(strategies=strategies, weights=weights)
    
    def validate_hybrid_performance(
        self,
        hybrid_id: str,
        metrics: Dict[str, float],
        success: bool
    ) -> Dict[str, Any]:
        """
        Validate hybrid strategy performance.
        
        Args:
            hybrid_id: Unique identifier for the hybrid strategy
            metrics: Performance metrics
            success: Whether the operation was successful
        
        Returns:
            Dict with validation results
        """
        validation_result = {
            "hybrid_id": hybrid_id,
            "timestamp": datetime.now().isoformat(),
            "metrics": metrics,
            "success": success,
            "valid": True,
            "issues": [],
            "recommendations": []
        }
        
        # Check success rate
        if not success:
            validation_result["valid"] = False
            validation_result["issues"].append("Operation failed")
            validation_result["recommendations"].append(
                "Consider using more conservative strategy mix"
            )
        
        # Check progress rate
        progress_rate = metrics.get("progress_rate", 0.0)
        if progress_rate < self.progress_thresholds["minimal"]:
            validation_result["valid"] = False
            validation_result["issues"].append("Progress rate below minimal threshold")
            validation_result["recommendations"].append(
                "Increase conservative strategy weight"
            )
        elif progress_rate > self.progress_thresholds["optimal"]:
            validation_result["recommendations"].append(
                "Consider increasing aggressive strategy weight"
            )
        
        # Check error rate
        error_rate = metrics.get("error_rate", 0.0)
        if error_rate > 0.3:
            validation_result["valid"] = False
            validation_result["issues"].append("High error rate")
            validation_result["recommendations"].append(
                "Reduce aggressive strategy weight"
            )
        
        # Check resource efficiency
        resource_efficiency = metrics.get("resource_efficiency", 1.0)
        if resource_efficiency < 0.5:
            validation_result["issues"].append("Low resource efficiency")
            validation_result["recommendations"].append(
                "Consider adjusting strategy mix for better efficiency"
            )
        
        # Record performance
        self._record_performance(hybrid_id, metrics, success, validation_result)
        
        return validation_result
    
    def _record_performance(
        self,
        hybrid_id: str,
        metrics: Dict[str, float],
        success: bool,
        validation_result: Dict[str, Any]
    ):
        """Record performance of a hybrid strategy."""
        if hybrid_id not in self.performance_history:
            self.performance_history[hybrid_id] = []
        
        self.performance_history[hybrid_id].append({
            "timestamp": datetime.now().isoformat(),
            "metrics": metrics,
            "success": success,
            "validation": validation_result
        })
    
    def learn_optimal_combination(
        self,
        task_type: str,
        hybrid_id: str
    ) -> Optional[StrategyMix]:
        """
        Learn optimal strategy combination for a task type.
        
        Args:
            task_type: Type of task
            hybrid_id: Hybrid strategy ID to learn from
        
        Returns:
            Optimal strategy mix if enough data, None otherwise
        """
        if hybrid_id not in self.performance_history:
            return None
        
        history = self.performance_history[hybrid_id]
        
        # Need at least 10 data points
        if len(history) < 10:
            return None
        
        # Calculate success rate
        successes = sum(1 for h in history if h["success"])
        success_rate = successes / len(history)
        
        # Need at least 70% success rate
        if success_rate < 0.7:
            return None
        
        # Get average metrics
        avg_metrics = {}
        for metric_key in history[0]["metrics"].keys():
            values = [h["metrics"][metric_key] for h in history]
            avg_metrics[metric_key] = sum(values) / len(values)
        
        # Create optimal mix based on learned metrics
        optimal_mix = self.create_adaptive_mix(avg_metrics, task_type=None)
        
        # Store as optimal for this task type
        self.optimal_combinations[task_type] = optimal_mix
        
        return optimal_mix
    
    def get_performance_summary(self, hybrid_id: str) -> Optional[Dict[str, Any]]:
        """
        Get performance summary for a hybrid strategy.
        
        Args:
            hybrid_id: Hybrid strategy ID
        
        Returns:
            Performance summary or None if not found
        """
        if hybrid_id not in self.performance_history:
            return None
        
        history = self.performance_history[hybrid_id]
        
        # Calculate statistics
        total_operations = len(history)
        successes = sum(1 for h in history if h["success"])
        success_rate = successes / total_operations
        
        # Average metrics
        avg_metrics = {}
        for metric_key in history[0]["metrics"].keys():
            values = [h["metrics"][metric_key] for h in history]
            avg_metrics[metric_key] = {
                "average": sum(values) / len(values),
                "min": min(values),
                "max": max(values)
            }
        
        return {
            "hybrid_id": hybrid_id,
            "total_operations": total_operations,
            "successes": successes,
            "failures": total_operations - successes,
            "success_rate": success_rate,
            "average_metrics": avg_metrics,
            "is_valid": success_rate >= 0.7
        }
    
    def get_default_hybrid(self, situation_type: str) -> StrategyMix:
        """
        Get default hybrid strategy for a situation type.
        
        Args:
            situation_type: Type of situation (e.g., "normal", "complex", "time_critical")
        
        Returns:
            Default strategy mix
        """
        return self.default_hybrids.get(
            situation_type,
            self.default_hybrids["normal"]
        )
    
    def generate_hybrid_id(self) -> str:
        """Generate a unique hybrid strategy ID."""
        return f"hybrid_{uuid.uuid4().hex[:12]}"
    
    def clear_history(self, hybrid_id: Optional[str] = None):
        """
        Clear performance history.
        
        Args:
            hybrid_id: Specific hybrid ID to clear, or None to clear all
        """
        if hybrid_id:
            self.performance_history.pop(hybrid_id, None)
        else:
            self.performance_history.clear()
    
    def reset_optimal_combinations(self, task_type: Optional[str] = None):
        """
        Reset optimal combinations.
        
        Args:
            task_type: Specific task type to reset, or None to reset all
        """
        if task_type:
            self.optimal_combinations.pop(task_type, None)
        else:
            self.optimal_combinations.clear()