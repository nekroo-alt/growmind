"""
Decision Maker for Adaptive Reasoning System

This module provides decision-making capabilities for L4D V4 adaptive reasoning system.
It selects the best action based on context analysis, considering multiple factors
such as success probability, cost, risk, and time. Supports different decision
strategies (greedy, optimal, safe) and provides decision explanations.
"""

from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
from dataclasses import dataclass, field
import logging
from datetime import datetime

# Import from context_analyzer
from v5.logic import (
    ContextAnalyzer,
    SituationReport,
    SituationType,
    PotentialAction
)


logger = logging.getLogger(__name__)


class DecisionStrategy(Enum):
    """Decision strategy for action selection."""
    GREEDY = "greedy"  # Maximize immediate gain
    OPTIMAL = "optimal"  # Maximize long-term gain
    SAFE = "safe"  # Minimize risk


@dataclass
class ActionEvaluation:
    """Evaluation of an action with multiple metrics."""
    action: str
    success_probability: float
    cost: Dict[str, float]  # tokens, time, money
    risk: float
    time_estimate: float
    value: float
    score: float
    reasoning: str


@dataclass
class Decision:
    """
    Complete decision with full context and explanation.
    
    This represents a decision made by the decision maker, including
    the selected action, alternatives considered, confidence, and reasoning.
    """
    decision_id: str
    timestamp: datetime
    context: Dict[str, Any]
    situation_report: SituationReport
    selected_action: str
    strategy: DecisionStrategy
    confidence: float
    reasoning: str
    alternatives: List[Tuple[str, str]]  # (action, reason_for_rejection)
    expected_outcome: str
    resources: Dict[str, float]


class DecisionMaker:
    """
    Decision maker for action selection in adaptive reasoning system.
    
    This component evaluates potential actions based on multiple factors
    and selects the best action according to the chosen strategy.
    """
    
    def __init__(
        self,
        context_analyzer: ContextAnalyzer,
        default_strategy: DecisionStrategy = DecisionStrategy.OPTIMAL
    ):
        """
        Initialize decision maker.
        
        Args:
            context_analyzer: Context analyzer for situation assessment
            default_strategy: Default decision strategy
        """
        self.context_analyzer = context_analyzer
        self.default_strategy = default_strategy
        self.logger = logger
        
        # Decision weights (can be learned over time)
        self.weights = {
            'success': 1.0,
            'cost': 0.5,
            'risk': 0.7,
            'value': 0.8
        }
        
        # Historical success rates (task_type -> success_rate)
        self.historical_success_rates: Dict[str, float] = {}
    
    def make_decision(
        self,
        context: Dict[str, Any],
        task_info: Optional[Dict[str, Any]] = None,
        strategy: Optional[DecisionStrategy] = None
    ) -> Decision:
        """
        Make a decision based on context analysis.
        
        Args:
            context: Current context containing actions, errors, telemetry, etc.
            task_info: Optional task information for context
            strategy: Decision strategy (uses default if not provided)
        
        Returns:
            Decision with selected action and full explanation
        """
        # Use default strategy if not provided
        if strategy is None:
            strategy = self.default_strategy
        
        # Analyze situation
        situation_report = self.context_analyzer.analyze_situation(
            context, task_info
        )
        
        # Evaluate potential actions
        evaluations = self._evaluate_actions(
            context,
            task_info,
            situation_report
        )
        
        # Select best action based on strategy
        selected_evaluation = self._select_action(
            evaluations,
            strategy,
            situation_report.situation_type
        )
        
        # Generate alternatives with rejection reasons
        alternatives = self._generate_alternatives(
            evaluations,
            selected_evaluation
        )
        
        # Estimate confidence
        confidence = self._estimate_confidence(
            selected_evaluation,
            situation_report
        )
        
        # Generate reasoning
        reasoning = self._generate_reasoning(
            selected_evaluation,
            strategy,
            situation_report
        )
        
        # Generate expected outcome
        expected_outcome = self._generate_expected_outcome(
            selected_evaluation,
            situation_report
        )
        
        # Calculate resources needed
        resources = selected_evaluation.cost
        
        return Decision(
            decision_id=self._generate_decision_id(),
            timestamp=datetime.now(),
            context=context,
            situation_report=situation_report,
            selected_action=selected_evaluation.action,
            strategy=strategy,
            confidence=confidence,
            reasoning=reasoning,
            alternatives=alternatives,
            expected_outcome=expected_outcome,
            resources=resources
        )
    
    def _evaluate_actions(
        self,
        context: Dict[str, Any],
        task_info: Optional[Dict[str, Any]],
        situation_report: SituationReport
    ) -> List[ActionEvaluation]:
        """
        Evaluate all potential actions.
        
        Args:
            context: Current context
            task_info: Optional task information
            situation_report: Situation analysis report
        
        Returns:
            List of action evaluations
        """
        evaluations = []
        
        for potential_action in situation_report.potential_actions:
            evaluation = self._evaluate_single_action(
                context,
                task_info,
                situation_report,
                potential_action
            )
            evaluations.append(evaluation)
        
        return evaluations
    
    def _evaluate_single_action(
        self,
        context: Dict[str, Any],
        task_info: Optional[Dict[str, Any]],
        situation_report: SituationReport,
        potential_action: PotentialAction
    ) -> ActionEvaluation:
        """
        Evaluate a single action across multiple dimensions.
        
        Args:
            context: Current context
            task_info: Optional task information
            situation_report: Situation analysis report
            potential_action: Potential action to evaluate
        
        Returns:
            ActionEvaluation with metrics
        """
        # Estimate success probability
        success_probability = self._estimate_success_probability(
            potential_action,
            context,
            task_info
        )
        
        # Estimate cost
        cost = self._estimate_cost(
            potential_action,
            context,
            task_info
        )
        
        # Risk is from potential action
        risk = potential_action.risk_level
        
        # Estimate time
        time_estimate = self._estimate_time(
            potential_action,
            context,
            task_info
        )
        
        # Estimate value
        value = self._estimate_value(
            potential_action,
            situation_report
        )
        
        # Calculate overall score
        score = self._calculate_score(
            success_probability,
            cost,
            risk,
            value
        )
        
        # Generate reasoning
        reasoning = self._generate_action_reasoning(
            success_probability,
            cost,
            risk,
            value,
            score
        )
        
        return ActionEvaluation(
            action=potential_action.action,
            success_probability=success_probability,
            cost=cost,
            risk=risk,
            time_estimate=time_estimate,
            value=value,
            score=score,
            reasoning=reasoning
        )
    
    def _estimate_success_probability(
        self,
        potential_action: PotentialAction,
        context: Dict[str, Any],
        task_info: Optional[Dict[str, Any]]
    ) -> float:
        """
        Estimate success probability for an action.
        
        Args:
            potential_action: Potential action to evaluate
            context: Current context
            task_info: Optional task information
        
        Returns:
            Success probability between 0.0 and 1.0
        """
        # Start with confidence from potential action
        probability = potential_action.confidence
        
        # Adjust based on historical success rates
        if task_info:
            task_type = task_info.get('type', 'unknown')
            historical_rate = self.historical_success_rates.get(task_type, 0.7)
            probability = (probability + historical_rate) / 2
        
        # Adjust based on recent performance
        recent_actions = context.get('recent_actions', [])
        if recent_actions:
            recent_success_rate = sum(
                1 for a in recent_actions if a.get('status') == 'success'
            ) / len(recent_actions)
            probability = (probability + recent_success_rate) / 2
        
        # Adjust based on error frequency
        errors = context.get('recent_errors', [])
        if errors:
            error_rate = len(errors) / max(len(errors) + len(recent_actions), 1)
            probability *= (1.0 - error_rate * 0.3)  # Reduce probability by up to 30%
        
        # Ensure probability is in valid range
        return max(min(probability, 1.0), 0.0)
    
    def _estimate_cost(
        self,
        potential_action: PotentialAction,
        context: Dict[str, Any],
        task_info: Optional[Dict[str, Any]]
    ) -> Dict[str, float]:
        """
        Estimate cost of an action.
        
        Args:
            potential_action: Potential action to evaluate
            context: Current context
            task_info: Optional task information
        
        Returns:
            Cost dict with tokens, time, money
        """
        # Default costs
        costs = {
            'tokens': 1000.0,
            'time': 10.0,
            'money': 0.01
        }
        
        # Adjust based on action type
        action = potential_action.action.lower()
        
        if 'retry' in action:
            costs['tokens'] *= 0.5  # Less tokens for retry
            costs['time'] *= 0.8  # Less time
        elif 'analyze' in action:
            costs['tokens'] *= 1.5  # More tokens for analysis
            costs['time'] *= 1.2  # More time
        elif 'expand' in action or 'gather' in action:
            costs['tokens'] *= 2.0  # More tokens for context gathering
            costs['time'] *= 1.5  # More time
        elif 'break' in action:
            costs['tokens'] *= 1.2  # Slightly more tokens
            costs['time'] *= 1.3  # More time for planning
        
        # Adjust based on task complexity
        if task_info:
            complexity = task_info.get('complexity', 0.5)
            multiplier = 1.0 + complexity  # Up to 2x cost for complex tasks
            for key in costs:
                costs[key] *= multiplier
        
        return costs
    
    def _estimate_time(
        self,
        potential_action: PotentialAction,
        context: Dict[str, Any],
        task_info: Optional[Dict[str, Any]]
    ) -> float:
        """
        Estimate time to complete an action.
        
        Args:
            potential_action: Potential action to evaluate
            context: Current context
            task_info: Optional task information
        
        Returns:
            Time estimate in minutes
        """
        # Base time estimate
        base_time = 10.0  # 10 minutes default
        
        # Adjust based on action type
        action = potential_action.action.lower()
        
        if 'retry' in action:
            base_time *= 0.5  # Faster for retry
        elif 'analyze' in action:
            base_time *= 1.5  # Slower for analysis
        elif 'expand' in action or 'gather' in action:
            base_time *= 2.0  # Slower for gathering context
        elif 'break' in action:
            base_time *= 1.3  # Moderate time for breaking down
        
        # Adjust based on task complexity
        if task_info:
            complexity = task_info.get('complexity', 0.5)
            base_time *= (1.0 + complexity)
        
        return base_time
    
    def _estimate_value(
        self,
        potential_action: PotentialAction,
        situation_report: SituationReport
    ) -> float:
        """
        Estimate value of an action.
        
        Args:
            potential_action: Potential action to evaluate
            situation_report: Situation analysis report
        
        Returns:
            Value score between 0.0 and 1.0
        """
        # Start with expected outcome quality
        value = 0.5
        
        # Higher value for actions that address the situation
        situation_type = situation_report.situation_type
        
        if situation_type == SituationType.ERROR:
            if 'retry' in potential_action.action.lower() or 'analyze' in potential_action.action.lower():
                value = 0.8
        elif situation_type == SituationType.BLOCKED:
            if 'expand' in potential_action.action.lower() or 'break' in potential_action.action.lower():
                value = 0.85
        elif situation_type == SituationType.COMPLEX:
            if 'create' in potential_action.action.lower() or 'conservative' in potential_action.action.lower():
                value = 0.9
        elif situation_type == SituationType.UNCERTAIN:
            if 'gather' in potential_action.action.lower() or 'balanced' in potential_action.action.lower():
                value = 0.85
        else:  # NORMAL
            if 'proceed' in potential_action.action.lower() or 'optimal' in potential_action.action.lower():
                value = 0.9
        
        # Adjust based on risk (lower risk = higher value)
        value *= (1.0 - potential_action.risk_level * 0.3)
        
        return value
    
    def _calculate_score(
        self,
        success_probability: float,
        cost: Dict[str, float],
        risk: float,
        value: float
    ) -> float:
        """
        Calculate overall score for an action.
        
        Args:
            success_probability: Probability of success
            cost: Cost dict with tokens, time, money
            risk: Risk level
            value: Value score
        
        Returns:
            Overall score (higher is better)
        """
        # Normalize cost (lower is better)
        normalized_cost = self._normalize_cost(cost)
        
        # Calculate weighted score
        # score = w1*success - w2*cost + w3*value - w4*risk
        score = (
            self.weights['success'] * success_probability
            - self.weights['cost'] * normalized_cost
            + self.weights['value'] * value
            - self.weights['risk'] * risk
        )
        
        return score
    
    def _normalize_cost(self, cost: Dict[str, float]) -> float:
        """
        Normalize cost to 0-1 range.
        
        Args:
            cost: Cost dict with tokens, time, money
        
        Returns:
            Normalized cost (0-1, lower is better)
        """
        # Max expected costs
        max_costs = {
            'tokens': 10000.0,
            'time': 60.0,
            'money': 1.0
        }
        
        # Calculate normalized cost
        normalized = 0.0
        for key, max_cost in max_costs.items():
            normalized += cost.get(key, 0.0) / max_cost
        
        return normalized / len(max_costs)
    
    def _select_action(
        self,
        evaluations: List[ActionEvaluation],
        strategy: DecisionStrategy,
        situation_type: SituationType
    ) -> ActionEvaluation:
        """
        Select best action based on strategy.
        
        Args:
            evaluations: List of action evaluations
            strategy: Decision strategy
            situation_type: Current situation type
        
        Returns:
            Selected action evaluation
        """
        if not evaluations:
            raise ValueError("No actions to select from")
        
        if strategy == DecisionStrategy.GREEDY:
            # Maximize immediate value
            selected = max(evaluations, key=lambda e: e.value)
        
        elif strategy == DecisionStrategy.OPTIMAL:
            # Maximize overall score
            selected = max(evaluations, key=lambda e: e.score)
        
        else:  # SAFE
            # Minimize risk
            selected = min(evaluations, key=lambda e: e.risk)
            # If multiple with same risk, choose highest success probability
            min_risk = selected.risk
            same_risk = [e for e in evaluations if abs(e.risk - min_risk) < 0.01]
            selected = max(same_risk, key=lambda e: e.success_probability)
        
        return selected
    
    def _generate_alternatives(
        self,
        evaluations: List[ActionEvaluation],
        selected_evaluation: ActionEvaluation
    ) -> List[Tuple[str, str]]:
        """
        Generate list of alternatives with rejection reasons.
        
        Args:
            evaluations: All action evaluations
            selected_evaluation: Selected action evaluation
        
        Returns:
            List of (action, reason_for_rejection) tuples
        """
        alternatives = []
        
        for evaluation in evaluations:
            if evaluation.action == selected_evaluation.action:
                continue
            
            # Generate rejection reason
            reason = self._generate_rejection_reason(
                evaluation,
                selected_evaluation
            )
            alternatives.append((evaluation.action, reason))
        
        return alternatives
    
    def _generate_rejection_reason(
        self,
        rejected: ActionEvaluation,
        selected: ActionEvaluation
    ) -> str:
        """Generate reason for rejecting an action."""
        reasons = []
        
        # Compare success probability
        if rejected.success_probability < selected.success_probability:
            diff = selected.success_probability - rejected.success_probability
            reasons.append(f"lower success probability ({diff:.1%})")
        
        # Compare cost
        rejected_cost = sum(rejected.cost.values())
        selected_cost = sum(selected.cost.values())
        if rejected_cost > selected_cost:
            diff = (rejected_cost - selected_cost) / selected_cost
            reasons.append(f"higher cost ({diff:.0%})")
        
        # Compare risk
        if rejected.risk > selected.risk:
            diff = rejected.risk - selected.risk
            reasons.append(f"higher risk ({diff:.2%})")
        
        # Compare value
        if rejected.value < selected.value:
            diff = selected.value - rejected.value
            reasons.append(f"lower value ({diff:.2%})")
        
        if not reasons:
            return "slightly lower overall score"
        
        return "; ".join(reasons)
    
    def _estimate_confidence(
        self,
        selected_evaluation: ActionEvaluation,
        situation_report: SituationReport
    ) -> float:
        """
        Estimate confidence in selected decision.
        
        Args:
            selected_evaluation: Selected action evaluation
            situation_report: Situation analysis report
        
        Returns:
            Confidence between 0.0 and 1.0
        """
        # Base confidence from action
        confidence = selected_evaluation.success_probability
        
        # Adjust based on situation confidence
        confidence = (confidence + situation_report.confidence) / 2
        
        # Adjust based on risk (higher risk = lower confidence)
        confidence *= (1.0 - selected_evaluation.risk * 0.2)
        
        return max(min(confidence, 1.0), 0.0)
    
    def _generate_reasoning(
        self,
        selected_evaluation: ActionEvaluation,
        strategy: DecisionStrategy,
        situation_report: SituationReport
    ) -> str:
        """
        Generate reasoning explanation for decision.
        
        Args:
            selected_evaluation: Selected action evaluation
            strategy: Decision strategy used
            situation_report: Situation analysis report
        
        Returns:
            Reasoning string
        """
        reasoning = f"Selected '{selected_evaluation.action}' using {strategy.value} strategy. "
        
        # Add situation context
        reasoning += (
            f"Situation is {situation_report.situation_type.value}. "
            f"Action has {selected_evaluation.success_probability:.0%} success probability, "
            f"{selected_evaluation.risk:.0%} risk, "
            f"and {selected_evaluation.value:.0%} value. "
        )
        
        # Add strategy-specific reasoning
        if strategy == DecisionStrategy.GREEDY:
            reasoning += "Chosen for maximum immediate value."
        elif strategy == DecisionStrategy.OPTIMAL:
            reasoning += "Chosen for best overall balance of factors."
        else:  # SAFE
            reasoning += "Chosen to minimize risk."
        
        return reasoning
    
    def _generate_expected_outcome(
        self,
        selected_evaluation: ActionEvaluation,
        situation_report: SituationReport
    ) -> str:
        """
        Generate expected outcome description.
        
        Args:
            selected_evaluation: Selected action evaluation
            situation_report: Situation analysis report
        
        Returns:
            Expected outcome string
        """
        # Find matching potential action for expected outcome
        for potential in situation_report.potential_actions:
            if potential.action == selected_evaluation.action:
                return potential.expected_outcome
        
        # Fallback
        return f"Complete {selected_evaluation.action} with {selected_evaluation.success_probability:.0%} probability"
    
    def _generate_action_reasoning(
        self,
        success_probability: float,
        cost: Dict[str, float],
        risk: float,
        value: float,
        score: float
    ) -> str:
        """Generate reasoning for single action evaluation."""
        total_cost = sum(cost.values())
        return (
            f"Score: {score:.3f} "
            f"(Success: {success_probability:.2f}, "
            f"Cost: {total_cost:.2f}, "
            f"Risk: {risk:.2f}, "
            f"Value: {value:.2f})"
        )
    
    def _generate_decision_id(self) -> str:
        """Generate unique decision ID."""
        import uuid
        return str(uuid.uuid4())
    
    def update_historical_success_rate(
        self,
        task_type: str,
        success: bool
    ):
        """
        Update historical success rate for a task type.
        
        Args:
            task_type: Type of task
            success: Whether the task was successful
        """
        current_rate = self.historical_success_rates.get(task_type, 0.7)
        
        # Update with exponential moving average (alpha=0.1)
        alpha = 0.1
        new_rate = alpha * (1.0 if success else 0.0) + (1.0 - alpha) * current_rate
        self.historical_success_rates[task_type] = new_rate
        
        self.logger.info(
            f"Updated success rate for {task_type}: "
            f"{current_rate:.2%} -> {new_rate:.2%}"
        )
    
    def set_weights(
        self,
        success: Optional[float] = None,
        cost: Optional[float] = None,
        risk: Optional[float] = None,
        value: Optional[float] = None
    ):
        """
        Update decision weights.
        
        Args:
            success: Weight for success probability
            cost: Weight for cost
            risk: Weight for risk
            value: Weight for value
        """
        if success is not None:
            self.weights['success'] = success
        if cost is not None:
            self.weights['cost'] = cost
        if risk is not None:
            self.weights['risk'] = risk
        if value is not None:
            self.weights['value'] = value
        
        self.logger.info(f"Updated weights: {self.weights}")