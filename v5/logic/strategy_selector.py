"""
Adaptive Strategy Selection Module

This module implements intelligent strategy selection and adaptive switching
for reasoning engine, enabling dynamic optimization based on situation
type, task characteristics, and recent performance.

Strategy Selection Matrix:
    - Select reasoning strategy based on situation type and task
    - Adapt strategy based on recent performance
    - Switch strategies when current strategy underperforms
    - Track strategy performance metrics
    - Learn optimal strategy for each task type
"""

from enum import Enum
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
import logging
from datetime import datetime, timedelta
import random

from v5.logic.reasoning_engine import (
    ReasoningStrategy,
    SituationType,
    SituationReport,
    Decision,
    ValidationResult
)

logger = logging.getLogger(__name__)


@dataclass
class StrategyPerformanceMetrics:
    """Performance metrics for a reasoning strategy"""
    total_usage: int = 0
    successful_uses: int = 0
    success_rate: float = 0.0
    average_time: float = 0.0
    average_efficiency: float = 0.0
    average_confidence: float = 0.0
    last_used: Optional[datetime] = None
    
    # Performance by task type
    task_type_performance: Dict[str, Dict[str, float]] = field(default_factory=dict)
    
    # Performance by situation type
    situation_performance: Dict[SituationType, Dict[str, float]] = field(
        default_factory=lambda: {
            sit: {"total": 0, "successful": 0, "avg_efficiency": 0.0}
            for sit in SituationType
        }
    )
    
    def calculate_success_rate(self) -> float:
        """Calculate current success rate"""
        if self.total_usage == 0:
            return 0.0
        return self.successful_uses / self.total_usage
    
    def update(
        self,
        success: bool,
        time_elapsed: float,
        efficiency: float,
        confidence: float,
        task_type: Optional[str] = None,
        situation_type: Optional[SituationType] = None
    ):
        """Update metrics with new performance data"""
        self.total_usage += 1
        
        if success:
            self.successful_uses += 1
        
        # Update success rate
        self.success_rate = self.calculate_success_rate()
        
        # Update averages with exponential moving average
        alpha = 0.3  # Smoothing factor
        
        self.average_time = (
            alpha * time_elapsed + (1 - alpha) * self.average_time
            if self.total_usage > 1
            else time_elapsed
        )
        
        self.average_efficiency = (
            alpha * efficiency + (1 - alpha) * self.average_efficiency
            if self.total_usage > 1
            else efficiency
        )
        
        self.average_confidence = (
            alpha * confidence + (1 - alpha) * self.average_confidence
            if self.total_usage > 1
            else confidence
        )
        
        self.last_used = datetime.now()
        
        # Update task type performance
        if task_type:
            if task_type not in self.task_type_performance:
                self.task_type_performance[task_type] = {
                    "total": 0, "successful": 0, "avg_efficiency": 0.0
                }
            
            task_perf = self.task_type_performance[task_type]
            task_perf["total"] += 1
            if success:
                task_perf["successful"] += 1
            task_perf["avg_efficiency"] = (
                alpha * efficiency + (1 - alpha) * task_perf["avg_efficiency"]
                if task_perf["total"] > 1
                else efficiency
            )
        
        # Update situation type performance
        if situation_type:
            sit_perf = self.situation_performance[situation_type]
            sit_perf["total"] += 1
            if success:
                sit_perf["successful"] += 1
            sit_perf["avg_efficiency"] = (
                alpha * efficiency + (1 - alpha) * sit_perf["avg_efficiency"]
                if sit_perf["total"] > 1
                else efficiency
            )


@dataclass
class StrategySwitchEvent:
    """Record of a strategy switch"""
    timestamp: datetime
    from_strategy: ReasoningStrategy
    to_strategy: ReasoningStrategy
    reason: str
    context: Dict[str, Any]
    success: bool = False
    time_to_validate: float = 0.0


class StrategySelector:
    """
    Adaptive Strategy Selector
    
    This selector provides intelligent strategy selection by:
    1. Selecting strategy based on situation type and task
    2. Adapting strategy based on recent performance
    3. Switching strategies when current approach underperforms
    4. Tracking strategy performance metrics
    5. Learning optimal strategies for each task type
    """
    
    def __init__(
        self,
        telemetry_manager=None,
        switch_threshold: float = 0.6,
        min_samples_before_switch: int = 5,
        strategy_selection_matrix: Optional[Dict[SituationType, Dict[ReasoningStrategy, float]]] = None
    ):
        """
        Initialize strategy selector
        
        Args:
            telemetry_manager: Manager for tracking strategy operations
            switch_threshold: Success rate threshold below which to consider switching
            min_samples_before_switch: Minimum samples before allowing switch
            strategy_selection_matrix: Custom selection matrix (uses default if None)
        """
        self.telemetry = telemetry_manager
        self.switch_threshold = switch_threshold
        self.min_samples_before_switch = min_samples_before_switch
        
        # Strategy selection matrix (situation -> strategy probabilities)
        if strategy_selection_matrix is None:
            self.strategy_selection_matrix = {
                SituationType.NORMAL: {
                    ReasoningStrategy.CONSERVATIVE: 0.2,
                    ReasoningStrategy.BALANCED: 0.6,
                    ReasoningStrategy.AGGRESSIVE: 0.2
                },
                SituationType.ERROR: {
                    ReasoningStrategy.CONSERVATIVE: 0.7,
                    ReasoningStrategy.BALANCED: 0.25,
                    ReasoningStrategy.AGGRESSIVE: 0.05
                },
                SituationType.BLOCKED: {
                    ReasoningStrategy.CONSERVATIVE: 0.7,
                    ReasoningStrategy.BALANCED: 0.25,
                    ReasoningStrategy.AGGRESSIVE: 0.05
                },
                SituationType.UNCERTAIN: {
                    ReasoningStrategy.CONSERVATIVE: 0.4,
                    ReasoningStrategy.BALANCED: 0.5,
                    ReasoningStrategy.AGGRESSIVE: 0.1
                },
                SituationType.COMPLEX: {
                    ReasoningStrategy.CONSERVATIVE: 0.4,
                    ReasoningStrategy.BALANCED: 0.5,
                    ReasoningStrategy.AGGRESSIVE: 0.1
                },
                SituationType.TIME_CRITICAL: {
                    ReasoningStrategy.CONSERVATIVE: 0.1,
                    ReasoningStrategy.BALANCED: 0.3,
                    ReasoningStrategy.AGGRESSIVE: 0.6
                },
                SituationType.RECOVERY: {
                    ReasoningStrategy.CONSERVATIVE: 0.7,
                    ReasoningStrategy.BALANCED: 0.25,
                    ReasoningStrategy.AGGRESSIVE: 0.05
                }
            }
        else:
            self.strategy_selection_matrix = strategy_selection_matrix
        
        # Performance tracking for each strategy
        self.strategy_performance: Dict[ReasoningStrategy, StrategyPerformanceMetrics] = {
            strategy: StrategyPerformanceMetrics()
            for strategy in ReasoningStrategy
        }
        
        # Current active strategy
        self.current_strategy: Optional[ReasoningStrategy] = None
        
        # Strategy switch history
        self.switch_history: List[StrategySwitchEvent] = []
        
        # Learned optimal strategies by task type
        self.learned_optimal_strategies: Dict[str, ReasoningStrategy] = {}
        
        # Recent performance window (last N decisions)
        self.recent_performance_window: List[Dict[str, Any]] = []
        self.performance_window_size = 10
        
        logger.info(
            f"StrategySelector initialized (switch_threshold={switch_threshold}, min_samples={min_samples_before_switch})"
        )
    
    def select_strategy(
        self,
        situation_report: SituationReport,
        task_type: Optional[str] = None,
        force_new_selection: bool = False
    ) -> ReasoningStrategy:
        """
        Select reasoning strategy based on situation and performance
        
        Args:
            situation_report: Report from context analysis
            task_type: Type of task being performed
            force_new_selection: Force selection even if current strategy is good
            
        Returns:
            Selected reasoning strategy
        """
        logger.debug(
            "Selecting strategy",
            situation_type=situation_report.situation_type.value,
            task_type=task_type,
            force_new=force_new_selection
        )
        
        # Check if current strategy is still good
        if not force_new_selection and self.current_strategy:
            if self._is_current_strategy_good(
                self.current_strategy,
                situation_report.situation_type,
                task_type
            ):
                logger.debug(
                    "Current strategy still good",
                    strategy=self.current_strategy.value
                )
                return self.current_strategy
        
        # Select new strategy based on situation
        strategy = self._select_strategy_for_situation(
            situation_report.situation_type,
            task_type
        )
        
        # Update current strategy
        if strategy != self.current_strategy:
            logger.info(
                f"Strategy selected (from={self.current_strategy.value if self.current_strategy else 'None'}, to={strategy.value}, situation={situation_report.situation_type.value})"
            )
            self.current_strategy = strategy
        
        # Track in telemetry
        if self.telemetry:
            self.telemetry.record_event(
                event_type="strategy_selected",
                severity="info",
                context={
                    "strategy": strategy.value,
                    "situation_type": situation_report.situation_type.value,
                    "task_type": task_type
                }
            )
        
        return strategy
    
    def should_switch_strategy(
        self,
        current_strategy: ReasoningStrategy,
        recent_performance: List[Dict[str, Any]],
        situation_type: Optional[SituationType] = None
    ) -> Tuple[bool, Optional[ReasoningStrategy], str]:
        """
        Determine if strategy should be switched
        
        Args:
            current_strategy: Currently active strategy
            recent_performance: List of recent performance data
            situation_type: Current situation type
            
        Returns:
            Tuple of (should_switch, new_strategy, reason)
        """
        perf_metrics = self.strategy_performance[current_strategy]
        
        # Check if we have enough samples
        if perf_metrics.total_usage < self.min_samples_before_switch:
            logger.debug(
                "Not enough samples to switch",
                current_strategy=current_strategy.value,
                samples=perf_metrics.total_usage,
                required=self.min_samples_before_switch
            )
            return False, None, "Insufficient performance data"
        
        # Check success rate
        if perf_metrics.success_rate < self.switch_threshold:
            logger.info(
                f"Success rate below threshold, consider switching (current={current_strategy.value}, rate={perf_metrics.success_rate:.2%}, threshold={self.switch_threshold:.2%})"
            )
            new_strategy = self._find_better_strategy(
                current_strategy,
                situation_type
            )
            if new_strategy:
                return (
                    True,
                    new_strategy,
                    f"Success rate {perf_metrics.success_rate:.2%} below threshold {self.switch_threshold:.2%}"
                )
        
        # Check for repeated errors
        if self._has_repeated_errors(recent_performance):
            logger.info(
                f"Repeated errors detected, consider switching (current={current_strategy.value})"
            )
            new_strategy = self._find_better_strategy(
                current_strategy,
                situation_type
            )
            if new_strategy:
                return (
                    True,
                    new_strategy,
                    "Repeated errors detected in recent performance"
                )
        
        # Check for stagnation (no progress)
        if self._is_stagnating(recent_performance):
            logger.info(
                f"Stagnation detected, consider switching (current={current_strategy.value})"
            )
            new_strategy = self._find_better_strategy(
                current_strategy,
                situation_type
            )
            if new_strategy:
                return (
                    True,
                    new_strategy,
                    "No progress in recent operations (stagnation)"
                )
        
        logger.debug("No need to switch strategy", strategy=current_strategy.value)
        return False, None, "Current strategy performing well"
    
    def switch_strategy(
        self,
        from_strategy: ReasoningStrategy,
        to_strategy: ReasoningStrategy,
        reason: str,
        context: Optional[Dict[str, Any]] = None
    ) -> StrategySwitchEvent:
        """
        Switch to a different strategy
        
        Args:
            from_strategy: Strategy to switch from
            to_strategy: Strategy to switch to
            reason: Reason for the switch
            context: Additional context for the switch
            
        Returns:
            StrategySwitchEvent recording the switch
        """
        logger.info(
            f"Switching strategy (from={from_strategy.value}, to={to_strategy.value}, reason={reason})"
        )
        
        # Record switch event
        switch_event = StrategySwitchEvent(
            timestamp=datetime.now(),
            from_strategy=from_strategy,
            to_strategy=to_strategy,
            reason=reason,
            context=context or {}
        )
        
        self.switch_history.append(switch_event)
        self.current_strategy = to_strategy
        
        # Track in telemetry
        if self.telemetry:
            self.telemetry.record_event(
                event_type="strategy_switched",
                severity="info",
                context={
                    "from_strategy": from_strategy.value,
                    "to_strategy": to_strategy.value,
                    "reason": reason
                }
            )
        
        return switch_event
    
    def update_strategy_performance(
        self,
        strategy: ReasoningStrategy,
        validation_result: ValidationResult,
        decision: Decision,
        time_elapsed: float,
        task_type: Optional[str] = None,
        situation_type: Optional[SituationType] = None
    ):
        """
        Update strategy performance metrics
        
        Args:
            strategy: Strategy that was used
            validation_result: Result of validation
            decision: Decision that was made
            time_elapsed: Time elapsed for operation
            task_type: Type of task
            situation_type: Type of situation
        """
        perf_metrics = self.strategy_performance[strategy]
        
        perf_metrics.update(
            success=validation_result.success,
            time_elapsed=time_elapsed,
            efficiency=validation_result.efficiency_score,
            confidence=decision.confidence,
            task_type=task_type,
            situation_type=situation_type
        )
        
        # Update recent performance window
        self._update_recent_performance_window(
            strategy=strategy,
            success=validation_result.success,
            efficiency=validation_result.efficiency_score,
            progress=validation_result.progress_made,
            decision=decision
        )
        
        # Update learned optimal strategies
        if task_type and validation_result.success:
            self._update_learned_optimal_strategy(task_type, strategy)
        
        logger.debug(
            "Strategy performance updated",
            strategy=strategy.value,
            success=validation_result.success,
            success_rate=perf_metrics.success_rate,
            efficiency=validation_result.efficiency_score
        )
        
        # Track in telemetry
        if self.telemetry:
            self.telemetry.record_metric(
                metric_name=f"strategy_success_rate_{strategy.value}",
                metric_value=perf_metrics.success_rate
            )
            self.telemetry.record_metric(
                metric_name=f"strategy_efficiency_{strategy.value}",
                metric_value=perf_metrics.average_efficiency
            )
    
    def get_strategy_performance(
        self,
        strategy: ReasoningStrategy,
        task_type: Optional[str] = None,
        situation_type: Optional[SituationType] = None
    ) -> Dict[str, Any]:
        """
        Get performance metrics for a strategy
        
        Args:
            strategy: Strategy to get metrics for
            task_type: Optional task type to filter by
            situation_type: Optional situation type to filter by
            
        Returns:
            Dictionary with performance metrics
        """
        metrics = self.strategy_performance[strategy]
        
        result = {
            "strategy": strategy.value,
            "total_usage": metrics.total_usage,
            "success_rate": metrics.success_rate,
            "average_time": metrics.average_time,
            "average_efficiency": metrics.average_efficiency,
            "average_confidence": metrics.average_confidence,
            "last_used": metrics.last_used.isoformat() if metrics.last_used else None
        }
        
        # Add task type specific performance
        if task_type and task_type in metrics.task_type_performance:
            task_perf = metrics.task_type_performance[task_type]
            result["task_type_performance"] = {
                "total": task_perf["total"],
                "success_rate": (
                    task_perf["successful"] / task_perf["total"]
                    if task_perf["total"] > 0
                    else 0.0
                ),
                "average_efficiency": task_perf["avg_efficiency"]
            }
        
        # Add situation type specific performance
        if situation_type:
            sit_perf = metrics.situation_performance[situation_type]
            result["situation_performance"] = {
                "total": sit_perf["total"],
                "success_rate": (
                    sit_perf["successful"] / sit_perf["total"]
                    if sit_perf["total"] > 0
                    else 0.0
                ),
                "average_efficiency": sit_perf["avg_efficiency"]
            }
        
        return result
    
    def get_strategy_recommendations(
        self,
        situation_type: SituationType,
        task_type: Optional[str] = None
    ) -> List[Tuple[ReasoningStrategy, float, str]]:
        """
        Get strategy recommendations for a given situation
        
        Args:
            situation_type: Type of situation
            task_type: Optional task type
            
        Returns:
            List of (strategy, score, reason) tuples sorted by score
        """
        recommendations = []
        
        for strategy in ReasoningStrategy:
            score = 0.0
            reasons = []
            
            # Base score from selection matrix
            base_prob = self.strategy_selection_matrix.get(
                situation_type,
                self.strategy_selection_matrix[SituationType.NORMAL]
            ).get(strategy, 0.0)
            score += base_prob * 0.4
            reasons.append(f"Base probability: {base_prob:.1%}")
            
            # Performance score
            perf = self.strategy_performance[strategy]
            if perf.total_usage >= self.min_samples_before_switch:
                score += perf.success_rate * 0.4
                reasons.append(f"Success rate: {perf.success_rate:.1%}")
            else:
                reasons.append("Insufficient performance data")
            
            # Task type learning
            if task_type and task_type in self.learned_optimal_strategies:
                if self.learned_optimal_strategies[task_type] == strategy:
                    score += 0.2
                    reasons.append("Learned optimal for task type")
            
            recommendations.append((strategy, score, "; ".join(reasons)))
        
        # Sort by score (descending)
        recommendations.sort(key=lambda x: x[1], reverse=True)
        
        return recommendations
    
    def _select_strategy_for_situation(
        self,
        situation_type: SituationType,
        task_type: Optional[str] = None
    ) -> ReasoningStrategy:
        """
        Select strategy based on situation type and learned preferences
        
        Args:
            situation_type: Type of situation
            task_type: Optional task type
            
        Returns:
            Selected strategy
        """
        # Check if we have learned optimal strategy for this task type
        if task_type and task_type in self.learned_optimal_strategies:
            learned_strategy = self.learned_optimal_strategies[task_type]
            logger.debug(
                "Using learned optimal strategy",
                task_type=task_type,
                strategy=learned_strategy.value
            )
            return learned_strategy
        
        # Use strategy selection matrix
        strategy_probs = self.strategy_selection_matrix.get(
            situation_type,
            self.strategy_selection_matrix[SituationType.NORMAL]
        )
        
        # Select strategy with highest probability
        # In future, could use weighted random selection
        best_strategy = max(strategy_probs.items(), key=lambda x: x[1])[0]
        
        logger.debug(
            "Strategy selected from matrix",
            situation_type=situation_type.value,
            strategy=best_strategy.value,
            probability=strategy_probs[best_strategy]
        )
        
        return best_strategy
    
    def _is_current_strategy_good(
        self,
        strategy: ReasoningStrategy,
        situation_type: SituationType,
        task_type: Optional[str] = None
    ) -> bool:
        """
        Check if current strategy is still performing well
        
        Args:
            strategy: Current strategy
            situation_type: Current situation type
            task_type: Optional task type
            
        Returns:
            True if strategy is still good, False otherwise
        """
        perf = self.strategy_performance[strategy]
        
        # Not enough data yet, assume good
        if perf.total_usage < self.min_samples_before_switch:
            return True
        
        # Check success rate
        if perf.success_rate < self.switch_threshold:
            return False
        
        # Check recent performance
        if self.recent_performance_window:
            recent_success = sum(
                1 for p in self.recent_performance_window
                if p["strategy"] == strategy and p["success"]
            )
            recent_total = sum(
                1 for p in self.recent_performance_window
                if p["strategy"] == strategy
            )
            
            if recent_total > 0:
                recent_rate = recent_success / recent_total
                if recent_rate < self.switch_threshold:
                    return False
        
        return True
    
    def _find_better_strategy(
        self,
        current_strategy: ReasoningStrategy,
        situation_type: Optional[SituationType] = None
    ) -> Optional[ReasoningStrategy]:
        """
        Find a better strategy to switch to
        
        Args:
            current_strategy: Current strategy
            situation_type: Optional situation type
            
        Returns:
            Better strategy if found, None otherwise
        """
        current_perf = self.strategy_performance[current_strategy]
        best_strategy = None
        
        for strategy in ReasoningStrategy:
            if strategy == current_strategy:
                continue
            
            perf = self.strategy_performance[strategy]
            
            # Skip if not enough samples
            if perf.total_usage < self.min_samples_before_switch:
                continue
            
            # Check if this strategy has better success rate
            if perf.success_rate > current_perf.success_rate:
                return strategy
            
            # If success rates are equal, check efficiency as tiebreaker
            if (
                perf.success_rate == current_perf.success_rate
                and perf.average_efficiency > current_perf.average_efficiency
            ):
                return strategy
        
        return best_strategy
    
    def _has_repeated_errors(self, recent_performance: List[Dict[str, Any]]) -> bool:
        """
        Check if there are repeated errors in recent performance
        
        Args:
            recent_performance: List of recent performance data
            
        Returns:
            True if repeated errors detected
        """
        # Check for 3+ consecutive failures
        consecutive_failures = 0
        for perf in reversed(recent_performance):
            if not perf["success"]:
                consecutive_failures += 1
                if consecutive_failures >= 3:
                    return True
            else:
                break
        
        return False
    
    def _is_stagnating(self, recent_performance: List[Dict[str, Any]]) -> bool:
        """
        Check if progress has stagnated
        
        Args:
            recent_performance: List of recent performance data
            
        Returns:
            True if stagnating
        """
        if len(recent_performance) < 5:
            return False
        
        # Check if average progress in last 5 operations is very low
        recent_progress = [p["progress"] for p in recent_performance[-5:]]
        avg_progress = sum(recent_progress) / len(recent_progress)
        
        return avg_progress < 0.05  # Less than 5% progress on average
    
    def _update_recent_performance_window(
        self,
        strategy: ReasoningStrategy,
        success: bool,
        efficiency: float,
        progress: float,
        decision: Decision
    ):
        """Update recent performance window"""
        self.recent_performance_window.append({
            "strategy": strategy,
            "success": success,
            "efficiency": efficiency,
            "progress": progress,
            "timestamp": datetime.now(),
            "decision": decision
        })
        
        # Keep only recent N performances
        if len(self.recent_performance_window) > self.performance_window_size:
            self.recent_performance_window = self.recent_performance_window[
                -self.performance_window_size:
            ]
    
    def _update_learned_optimal_strategy(
        self,
        task_type: str,
        strategy: ReasoningStrategy
    ):
        """
        Update learned optimal strategy for a task type
        
        Args:
            task_type: Type of task
            strategy: Strategy that succeeded
        """
        # Only update if we don't have a learned strategy yet,
        # or if current one has performed worse than this one
        current_optimal = self.learned_optimal_strategies.get(task_type)
        
        if current_optimal is None:
            self.learned_optimal_strategies[task_type] = strategy
            logger.info(
                f"Learned optimal strategy (task_type={task_type}, strategy={strategy.value})"
            )
            return
        
        # Compare performance
        current_perf = self.strategy_performance[current_optimal]
        new_perf = self.strategy_performance[strategy]
        
        if (
            new_perf.success_rate > current_perf.success_rate
            and new_perf.total_usage >= self.min_samples_before_switch
        ):
            self.learned_optimal_strategies[task_type] = strategy
            logger.info(
                f"Updated optimal strategy (task_type={task_type}, from={current_optimal.value}, to={strategy.value}, new_rate={new_perf.success_rate:.2%}, old_rate={current_perf.success_rate:.2%})"
            )
    
    def validate_switch(
        self,
        switch_event: StrategySwitchEvent,
        post_switch_performance: List[Dict[str, Any]],
        min_samples: int = 3
    ) -> Tuple[bool, float, str]:
        """
        Validate that a strategy switch was successful
        
        Args:
            switch_event: The switch event to validate
            post_switch_performance: Performance data after the switch
            min_samples: Minimum samples needed for validation
            
        Returns:
            Tuple of (success, improvement_score, reason)
        """
        logger.info(
            f"Validating strategy switch (from={switch_event.from_strategy.value}, to={switch_event.to_strategy.value})"
        )
        
        # Need minimum samples for validation
        if len(post_switch_performance) < min_samples:
            return (
                False,
                0.0,
                f"Insufficient samples for validation ({len(post_switch_performance)} < {min_samples})"
            )
        
        # Get performance before and after switch
        before_perf = self.strategy_performance[switch_event.from_strategy]
        after_perf = self.strategy_performance[switch_event.to_strategy]
        
        # Calculate improvement metrics
        # 1. Success rate improvement
        success_rate_improvement = (
            after_perf.success_rate - before_perf.success_rate
        )
        
        # 2. Efficiency improvement
        efficiency_improvement = (
            after_perf.average_efficiency - before_perf.average_efficiency
        )
        
        # 3. Calculate recent success rate (post-switch)
        recent_successes = sum(
            1 for p in post_switch_performance if p["success"]
        )
        recent_total = len(post_switch_performance)
        recent_success_rate = recent_successes / recent_total
        
        # Calculate improvement score (weighted combination)
        improvement_score = (
            0.5 * success_rate_improvement +
            0.3 * efficiency_improvement +
            0.2 * recent_success_rate
        )
        
        # Determine if switch was successful
        success = improvement_score > 0.1  # At least 10% improvement
        
        # Generate reason
        if success:
            reason_parts = [
                f"Success rate improved by {success_rate_improvement:.2%}"
            ]
            if efficiency_improvement > 0:
                reason_parts.append(
                    f"efficiency improved by {efficiency_improvement:.2%}"
                )
            reason_parts.append(
                f"recent success rate: {recent_success_rate:.2%}"
            )
            reason = ", ".join(reason_parts)
        else:
            reason_parts = []
            if success_rate_improvement < 0:
                reason_parts.append(
                    f"Success rate decreased by {abs(success_rate_improvement):.2%}"
                )
            if efficiency_improvement < 0:
                reason_parts.append(
                    f"efficiency decreased by {abs(efficiency_improvement):.2%}"
                )
            if recent_success_rate < before_perf.success_rate:
                reason_parts.append(
                    f"recent success rate ({recent_success_rate:.2%}) worse than before ({before_perf.success_rate:.2%})"
                )
            reason = ", ".join(reason_parts) if reason_parts else "No significant improvement"
        
        # Update switch event with validation results
        switch_event.success = success
        time_elapsed = (
            datetime.now() - switch_event.timestamp
        ).total_seconds()
        switch_event.time_to_validate = time_elapsed
        
        logger.info(
            f"Switch validation complete (success={success}, improvement_score={improvement_score:.3f}, reason={reason})"
        )
        
        # Track validation in telemetry
        if self.telemetry:
            self.telemetry.record_event(
                event_type="strategy_switch_validated",
                severity="info",
                context={
                    "from_strategy": switch_event.from_strategy.value,
                    "to_strategy": switch_event.to_strategy.value,
                    "success": success,
                    "improvement_score": improvement_score,
                    "reason": reason,
                    "time_to_validate": time_elapsed
                }
            )
        
        return success, improvement_score, reason
    
    def get_switch_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about strategy switches
        
        Returns:
            Dictionary with switch statistics
        """
        if not self.switch_history:
            return {
                "total_switches": 0,
                "switch_frequency": 0.0,
                "success_rate": 0.0,
                "average_improvement": 0.0,
                "switches_by_strategy": {},
                "switches_by_reason": {}
            }
        
        total_switches = len(self.switch_history)
        
        # Calculate switch frequency (switches per hour in last 24h)
        now = datetime.now()
        recent_switches = [
            s for s in self.switch_history
            if (now - s.timestamp).total_seconds() <= 86400  # 24 hours
        ]
        switch_frequency = len(recent_switches) / 24.0  # switches per hour
        
        # Calculate success rate of switches
        successful_switches = sum(1 for s in self.switch_history if s.success)
        switch_success_rate = (
            successful_switches / total_switches
            if total_switches > 0
            else 0.0
        )
        
        # Calculate average improvement (for successful switches)
        successful_switches_with_perf = [
            s for s in self.switch_history if s.success
        ]
        if successful_switches_with_perf:
            # Estimate improvement from performance metrics
            improvements = []
            for switch in successful_switches_with_perf:
                before_perf = self.strategy_performance[switch.from_strategy]
                after_perf = self.strategy_performance[switch.to_strategy]
                improvement = after_perf.success_rate - before_perf.success_rate
                improvements.append(improvement)
            average_improvement = sum(improvements) / len(improvements)
        else:
            average_improvement = 0.0
        
        # Count switches by strategy
        switches_by_strategy = {}
        for switch in self.switch_history:
            key = f"{switch.from_strategy.value} -> {switch.to_strategy.value}"
            switches_by_strategy[key] = switches_by_strategy.get(key, 0) + 1
        
        # Count switches by reason
        switches_by_reason = {}
        for switch in self.switch_history:
            reason = switch.reason
            switches_by_reason[reason] = switches_by_reason.get(reason, 0) + 1
        
        return {
            "total_switches": total_switches,
            "switch_frequency": switch_frequency,
            "success_rate": switch_success_rate,
            "average_improvement": average_improvement,
            "switches_by_strategy": switches_by_strategy,
            "switches_by_reason": switches_by_reason
        }
    
    def get_optimal_switch_points(
        self,
        task_type: Optional[str] = None,
        situation_type: Optional[SituationType] = None
    ) -> List[Dict[str, Any]]:
        """
        Get learned optimal switch points based on historical data
        
        Args:
            task_type: Optional task type to filter by
            situation_type: Optional situation type to filter by
            
        Returns:
            List of optimal switch points with conditions
        """
        optimal_points = []
        
        # Analyze successful switches to find patterns
        successful_switches = [
            s for s in self.switch_history
            if s.success
        ]
        
        if not successful_switches:
            return optimal_points
        
        # Group by task type if specified
        if task_type:
            successful_switches = [
                s for s in successful_switches
                if s.context.get("task_type") == task_type
            ]
        
        # Group by situation type if specified
        if situation_type:
            successful_switches = [
                s for s in successful_switches
                if s.context.get("situation_type") == situation_type.value
            ]
        
        # Find common patterns in successful switches
        # Pattern 1: Success rate threshold
        success_rate_switches = [
            s for s in successful_switches
            if "Success rate" in s.reason or "success rate" in s.reason.lower()
        ]
        if success_rate_switches:
            # Extract success rate threshold from reasons
            threshold_matches = []
            for switch in success_rate_switches:
                import re
                match = re.search(r'(\d+(?:\.\d+)?)%', switch.reason)
                if match:
                    threshold_matches.append(float(match.group(1)) / 100)
            
            if threshold_matches:
                avg_threshold = sum(threshold_matches) / len(threshold_matches)
                optimal_points.append({
                    "condition": "success_rate_below_threshold",
                    "threshold": avg_threshold,
                    "frequency": len(success_rate_switches),
                    "description": f"Switch when success rate drops below {avg_threshold:.1%}"
                })
        
        # Pattern 2: Repeated errors
        error_switches = [
            s for s in successful_switches
            if "Repeated errors" in s.reason or "repeated" in s.reason.lower()
        ]
        if error_switches:
            optimal_points.append({
                "condition": "repeated_errors",
                "threshold": 3,
                "frequency": len(error_switches),
                "description": "Switch after 3+ consecutive errors"
            })
        
        # Pattern 3: Stagnation
        stagnation_switches = [
            s for s in successful_switches
            if "Stagnation" in s.reason or "stagnation" in s.reason.lower()
        ]
        if stagnation_switches:
            optimal_points.append({
                "condition": "stagnation",
                "threshold": 5,
                "frequency": len(stagnation_switches),
                "description": "Switch when no progress for 5+ operations"
            })
        
        # Sort by frequency (most common first)
        optimal_points.sort(key=lambda x: x["frequency"], reverse=True)
        
        return optimal_points
