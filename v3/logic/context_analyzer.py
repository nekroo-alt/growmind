"""
Context Analyzer for Adaptive Reasoning System

This module provides context analysis capabilities for the L4D V4 adaptive reasoning system.
It analyzes current context to identify situation types, extract features, estimate confidence,
and generate situation reports with recommendations.
"""

from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
from dataclasses import dataclass, field
import logging

# Import LLM provider
from llm_base.provider import LLMProvider


logger = logging.getLogger(__name__)


class SituationType(Enum):
    """Classification of different situation types."""
    NORMAL = "normal"
    ERROR = "error"
    BLOCKED = "blocked"
    UNCERTAIN = "uncertain"
    COMPLEX = "complex"


@dataclass
class SituationFeatures:
    """Key features extracted from context."""
    error_frequency: float = 0.0
    error_types: List[str] = field(default_factory=list)
    task_complexity: float = 0.0
    dependency_count: int = 0
    resource_availability: Dict[str, float] = field(default_factory=dict)
    time_pressure: float = 0.0
    context_completeness: float = 0.0
    recent_failures: int = 0
    recent_successes: int = 0


@dataclass
class PotentialAction:
    """A potential action with its characteristics."""
    action: str
    risk_level: float
    expected_outcome: str
    confidence: float


@dataclass
class SituationReport:
    """Complete situation analysis report."""
    situation_type: SituationType
    features: SituationFeatures
    potential_actions: List[PotentialAction]
    confidence: float
    recommendations: List[str]
    reasoning: str


class ContextAnalyzer:
    """
    Analyzes current context to identify situation type and generate recommendations.
    
    This component is part of the adaptive reasoning engine and provides
    situation assessment to inform decision-making.
    """
    
    def __init__(self, llm_provider: LLMProvider):
        """
        Initialize the context analyzer.
        
        Args:
            llm_provider: LLM provider for complex analysis
        """
        self.llm_provider = llm_provider
        self.logger = logger
    
    def analyze_situation(
        self,
        context: Dict[str, Any],
        task_info: Optional[Dict[str, Any]] = None
    ) -> SituationReport:
        """
        Analyze the current context to identify situation type and generate report.
        
        Args:
            context: Current context containing actions, errors, telemetry, etc.
            task_info: Optional task information for context
        
        Returns:
            SituationReport with complete analysis
        """
        # Extract features from context
        features = self._extract_features(context, task_info)
        
        # Classify situation type
        situation_type = self._classify_situation(features)
        
        # Identify potential actions
        potential_actions = self._identify_potential_actions(
            context, features, situation_type
        )
        
        # Estimate overall confidence
        confidence = self._estimate_confidence(features, potential_actions)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            situation_type, features, potential_actions
        )
        
        # Generate reasoning
        reasoning = self._generate_reasoning(
            situation_type, features, recommendations
        )
        
        return SituationReport(
            situation_type=situation_type,
            features=features,
            potential_actions=potential_actions,
            confidence=confidence,
            recommendations=recommendations,
            reasoning=reasoning
        )
    
    def _extract_features(
        self,
        context: Dict[str, Any],
        task_info: Optional[Dict[str, Any]] = None
    ) -> SituationFeatures:
        """
        Extract key features from context.
        
        Args:
            context: Current context
            task_info: Optional task information
        
        Returns:
            SituationFeatures with extracted features
        """
        features = SituationFeatures()
        
        # Extract error information
        errors = context.get('recent_errors', [])
        features.error_frequency = len(errors) / max(len(errors) + len(context.get('recent_actions', [])), 1)
        features.error_types = self._get_error_types(errors)
        features.recent_failures = len([e for e in errors if e.get('severity') == 'error'])
        
        # Extract task complexity
        if task_info:
            features.task_complexity = task_info.get('complexity', 0.0)
            features.dependency_count = task_info.get('dependency_count', 0)
        
        # Extract resource availability
        resources = context.get('resources', {})
        features.resource_availability = {
            'tokens': self._normalize_resource(resources.get('tokens_available', 0)),
            'time': self._normalize_resource(resources.get('time_available', 0)),
            'compute': self._normalize_resource(resources.get('compute_available', 0))
        }
        
        # Extract time pressure
        features.time_pressure = context.get('time_pressure', 0.0)
        
        # Extract context completeness
        features.context_completeness = context.get('context_completeness', 1.0)
        
        # Extract recent successes
        actions = context.get('recent_actions', [])
        features.recent_successes = len([
            a for a in actions if a.get('status') == 'success'
        ])
        
        return features
    
    def _classify_situation(self, features: SituationFeatures) -> SituationType:
        """
        Classify situation type based on features.
        
        Args:
            features: Extracted features
        
        Returns:
            SituationType classification
        """
        # Rule-based classification
        if features.error_frequency > 0.5 or features.recent_failures >= 3:
            return SituationType.ERROR
        
        if features.dependency_count > 5 or features.task_complexity > 0.8:
            return SituationType.COMPLEX
        
        if features.context_completeness < 0.5 or features.recent_successes == 0:
            return SituationType.BLOCKED
        
        if len(features.error_types) > 2:
            return SituationType.UNCERTAIN
        
        return SituationType.NORMAL
    
    def _identify_potential_actions(
        self,
        context: Dict[str, Any],
        features: SituationFeatures,
        situation_type: SituationType
    ) -> List[PotentialAction]:
        """
        Identify potential actions with their characteristics.
        
        Args:
            context: Current context
            features: Extracted features
            situation_type: Current situation type
        
        Returns:
            List of potential actions
        """
        actions = []
        
        # Generate situation-specific actions
        if situation_type == SituationType.ERROR:
            actions.extend([
                PotentialAction(
                    action="retry_with_backoff",
                    risk_level=0.2,
                    expected_outcome="Resolve transient errors",
                    confidence=0.8
                ),
                PotentialAction(
                    action="analyze_error_root_cause",
                    risk_level=0.1,
                    expected_outcome="Understand and fix error",
                    confidence=0.7
                )
            ])
        elif situation_type == SituationType.BLOCKED:
            actions.extend([
                PotentialAction(
                    action="expand_context",
                    risk_level=0.3,
                    expected_outcome="Get more information",
                    confidence=0.6
                ),
                PotentialAction(
                    action="break_task_smaller",
                    risk_level=0.2,
                    expected_outcome="Simplify problem",
                    confidence=0.7
                )
            ])
        elif situation_type == SituationType.COMPLEX:
            actions.extend([
                PotentialAction(
                    action="create_subtasks",
                    risk_level=0.2,
                    expected_outcome="Break down complexity",
                    confidence=0.8
                ),
                PotentialAction(
                    action="use_conservative_strategy",
                    risk_level=0.1,
                    expected_outcome="Minimize risk",
                    confidence=0.9
                )
            ])
        elif situation_type == SituationType.UNCERTAIN:
            actions.extend([
                PotentialAction(
                    action="gather_more_context",
                    risk_level=0.1,
                    expected_outcome="Reduce uncertainty",
                    confidence=0.8
                ),
                PotentialAction(
                    action="use_balanced_strategy",
                    risk_level=0.2,
                    expected_outcome="Balance risk and speed",
                    confidence=0.7
                )
            ])
        else:  # NORMAL
            actions.extend([
                PotentialAction(
                    action="proceed_with_task",
                    risk_level=0.1,
                    expected_outcome="Complete task efficiently",
                    confidence=0.9
                ),
                PotentialAction(
                    action="use_optimal_strategy",
                    risk_level=0.15,
                    expected_outcome="Maximize efficiency",
                    confidence=0.85
                )
            ])
        
        return actions
    
    def _estimate_confidence(
        self,
        features: SituationFeatures,
        potential_actions: List[PotentialAction]
    ) -> float:
        """
        Estimate overall confidence in the situation assessment.
        
        Args:
            features: Extracted features
            potential_actions: List of potential actions
        
        Returns:
            Confidence score between 0.0 and 1.0
        """
        confidence_scores = []
        
        # Confidence from context completeness
        confidence_scores.append(features.context_completeness)
        
        # Confidence from resource availability
        avg_resource = sum(features.resource_availability.values()) / max(
            len(features.resource_availability), 1
        )
        confidence_scores.append(avg_resource)
        
        # Confidence from action confidence
        if potential_actions:
            avg_action_confidence = sum(a.confidence for a in potential_actions) / len(potential_actions)
            confidence_scores.append(avg_action_confidence)
        
        # Confidence from recent success rate
        total_recent = features.recent_successes + features.recent_failures
        if total_recent > 0:
            success_rate = features.recent_successes / total_recent
            confidence_scores.append(success_rate)
        
        # Return average confidence
        return sum(confidence_scores) / max(len(confidence_scores), 1)
    
    def _generate_recommendations(
        self,
        situation_type: SituationType,
        features: SituationFeatures,
        potential_actions: List[PotentialAction]
    ) -> List[str]:
        """
        Generate recommendations based on situation analysis.
        
        Args:
            situation_type: Current situation type
            features: Extracted features
            potential_actions: List of potential actions
        
        Returns:
            List of recommendations
        """
        recommendations = []
        
        # Situation-specific recommendations
        if situation_type == SituationType.ERROR:
            recommendations.append("Analyze recent errors to identify patterns")
            recommendations.append("Consider using retry logic for transient errors")
            if features.error_frequency > 0.7:
                recommendations.append("High error frequency detected - pause and investigate")
        
        elif situation_type == SituationType.BLOCKED:
            recommendations.append("Expand context to gather more information")
            recommendations.append("Consider breaking task into smaller subtasks")
            if features.dependency_count > 5:
                recommendations.append("Many dependencies - consider parallel execution")
        
        elif situation_type == SituationType.COMPLEX:
            recommendations.append("Use conservative strategy to minimize risk")
            recommendations.append("Break down complex task into manageable subtasks")
            if features.task_complexity > 0.8:
                recommendations.append("High complexity - prioritize clear milestones")
        
        elif situation_type == SituationType.UNCERTAIN:
            recommendations.append("Gather additional context before proceeding")
            recommendations.append("Use balanced strategy to manage uncertainty")
            if features.context_completeness < 0.3:
                recommendations.append("Low context completeness - recommend expanding context")
        
        else:  # NORMAL
            recommendations.append("Proceed with task execution")
            recommendations.append("Use optimal strategy for efficiency")
            if len(potential_actions) > 1:
                recommendations.append(f"Select best action from {len(potential_actions)} options")
        
        return recommendations
    
    def _generate_reasoning(
        self,
        situation_type: SituationType,
        features: SituationFeatures,
        recommendations: List[str]
    ) -> str:
        """
        Generate reasoning explanation for the situation assessment.
        
        Args:
            situation_type: Current situation type
            features: Extracted features
            recommendations: Generated recommendations
        
        Returns:
            Reasoning explanation string
        """
        reasoning = f"Situation classified as '{situation_type.value}' because: "
        
        # Add feature-based reasoning
        if situation_type == SituationType.ERROR:
            reasoning += (
                f"Error frequency is {features.error_frequency:.2%} "
                f"with {features.recent_failures} recent failures. "
                f"Error types: {', '.join(features.error_types) or 'None'}."
            )
        elif situation_type == SituationType.BLOCKED:
            reasoning += (
                f"Context completeness is {features.context_completeness:.2%} "
                f"and {features.dependency_count} dependencies detected. "
                f"Recent successes: {features.recent_successes}."
            )
        elif situation_type == SituationType.COMPLEX:
            reasoning += (
                f"Task complexity is {features.task_complexity:.2%} "
                f"with {features.dependency_count} dependencies. "
                f"Resource availability average: {self._avg_resource(features.resource_availability):.2%}."
            )
        elif situation_type == SituationType.UNCERTAIN:
            reasoning += (
                f"Context completeness is {features.context_completeness:.2%} "
                f"and {len(features.error_types)} error types detected. "
                f"Recent success rate: {self._success_rate(features):.2%}."
            )
        else:  # NORMAL
            reasoning += (
                f"Low error frequency ({features.error_frequency:.2%}), "
                f"good context completeness ({features.context_completeness:.2%}), "
                f"and {features.recent_successes} recent successes."
            )
        
        return reasoning
    
    def _get_error_types(self, errors: List[Dict[str, Any]]) -> List[str]:
        """Extract unique error types from error list."""
        error_types = set()
        for error in errors:
            if 'type' in error:
                error_types.add(error['type'])
            elif 'message' in error:
                # Infer type from message
                error_types.add(self._infer_error_type(error['message']))
        return list(error_types)
    
    def _infer_error_type(self, error_message: str) -> str:
        """Infer error type from error message."""
        error_message_lower = error_message.lower()
        
        if 'timeout' in error_message_lower or 'rate limit' in error_message_lower:
            return 'timeout'
        elif 'permission' in error_message_lower or 'access' in error_message_lower:
            return 'permission'
        elif 'not found' in error_message_lower or 'missing' in error_message_lower:
            return 'not_found'
        elif 'syntax' in error_message_lower or 'parse' in error_message_lower:
            return 'syntax_error'
        elif 'type' in error_message_lower:
            return 'type_error'
        else:
            return 'unknown'
    
    def _normalize_resource(self, value: float, max_value: float = 100.0) -> float:
        """Normalize resource value to 0-1 range."""
        return max(min(value / max_value, 1.0), 0.0)
    
    def _avg_resource(self, resources: Dict[str, float]) -> float:
        """Calculate average resource availability."""
        if not resources:
            return 0.0
        return sum(resources.values()) / len(resources)
    
    def _success_rate(self, features: SituationFeatures) -> float:
        """Calculate recent success rate."""
        total = features.recent_successes + features.recent_failures
        if total == 0:
            return 1.0  # Assume success if no data
        return features.recent_successes / total