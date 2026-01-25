"""
Action Validator for Adaptive Reasoning System

This module provides action validation capabilities for L4D V4 adaptive reasoning system.
It validates that actions achieve intended results, checks for unintended side effects,
measures progress toward goals, and triggers corrective actions when needed.
"""

from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
from dataclasses import dataclass, field
import logging
from datetime import datetime

# Import from decision_maker
from logic.decision_maker import Decision


logger = logging.getLogger(__name__)


class ValidationCriteria(Enum):
    """Validation criteria for action validation."""
    GOAL_ACHIEVEMENT = "goal_achievement"  # Did action achieve primary goal?
    SIDE_EFFECTS = "side_effects"  # Any negative side effects?
    PROGRESS = "progress"  # Made measurable progress?
    EFFICIENCY = "efficiency"  # Was action efficient?


class ValidationResult(Enum):
    """Result of action validation."""
    PASSED = "passed"  # Action fully validated
    FAILED = "failed"  # Action failed validation
    PARTIAL = "partial"  # Action partially successful
    NEEDS_CORRECTION = "needs_correction"  # Action needs corrective action


class ValidationMethod(Enum):
    """Methods for validating actions."""
    TEST_EXECUTION = "test_execution"  # Run tests to validate
    CODE_REVIEW = "code_review"  # Review code changes
    METRICS_COMPARISON = "metrics_comparison"  # Compare metrics
    USER_FEEDBACK = "user_feedback"  # Get user feedback


@dataclass
class ValidationReport:
    """
    Complete validation report for an action.
    
    This represents the full validation results for an action,
    including criteria checked, results, and recommendations.
    """
    validation_id: str
    timestamp: datetime
    decision: Decision
    criteria_results: Dict[ValidationCriteria, Tuple[bool, str]]
    overall_result: ValidationResult
    confidence: float
    side_effects: List[str]
    progress_made: float
    efficiency_score: float
    recommendations: List[str]
    corrective_actions: List[str]


@dataclass
class ValidationMetrics:
    """Metrics collected during validation."""
    tests_passed: int
    tests_failed: int
    code_coverage: float
    lines_added: int
    lines_removed: int
    execution_time: float
    resource_usage: Dict[str, float]
    user_satisfaction: Optional[float] = None


class ActionValidator:
    """
    Action validator for result verification in adaptive reasoning system.
    
    This component validates that actions achieve intended results,
    checks for unintended side effects, measures progress, and
    triggers corrective actions when needed.
    """
    
    def __init__(self, telemetry_manager=None):
        """
        Initialize action validator.
        
        Args:
            telemetry_manager: Optional telemetry manager for tracking
        """
        self.telemetry_manager = telemetry_manager
        self.logger = logger
        
        # Validation accuracy tracking
        self.validation_history: List[Dict[str, Any]] = []
        
        # Thresholds for validation
        self.thresholds = {
            'min_progress': 0.1,  # 10% minimum progress
            'expected_progress': 0.3,  # 30% expected progress
            'min_efficiency': 0.5,  # 50% minimum efficiency
            'test_pass_rate': 0.8,  # 80% test pass rate
            'max_side_effects': 2,  # Maximum acceptable side effects
        }
    
    def validate_action(
        self,
        decision: Decision,
        actual_result: Dict[str, Any],
        context: Dict[str, Any],
        validation_methods: Optional[List[ValidationMethod]] = None
    ) -> ValidationReport:
        """
        Validate that an action achieved intended result.
        
        Args:
            decision: Decision that was made
            actual_result: Actual result of action execution
            context: Current context after action
            validation_methods: Methods to use for validation
        
        Returns:
            ValidationReport with full validation results
        """
        # Default validation methods
        if validation_methods is None:
            validation_methods = [
                ValidationMethod.TEST_EXECUTION,
                ValidationMethod.METRICS_COMPARISON
            ]
        
        # Collect validation metrics
        metrics = self._collect_validation_metrics(
            decision,
            actual_result,
            validation_methods
        )
        
        # Check each validation criterion
        criteria_results = {}
        
        # Goal achievement
        goal_achieved, goal_reason = self._check_goal_achievement(
            decision,
            actual_result,
            metrics
        )
        criteria_results[ValidationCriteria.GOAL_ACHIEVEMENT] = (goal_achieved, goal_reason)
        
        # Side effects
        no_side_effects, side_effects_reason = self._check_side_effects(
            decision,
            actual_result,
            context
        )
        criteria_results[ValidationCriteria.SIDE_EFFECTS] = (no_side_effects, side_effects_reason)
        
        # Progress
        progress_made, progress_reason = self._check_progress(
            decision,
            actual_result,
            context
        )
        criteria_results[ValidationCriteria.PROGRESS] = (progress_made, progress_reason)
        
        # Efficiency
        efficient, efficiency_reason = self._check_efficiency(
            decision,
            actual_result,
            metrics
        )
        criteria_results[ValidationCriteria.EFFICIENCY] = (efficient, efficiency_reason)
        
        # Determine overall result
        overall_result = self._determine_overall_result(criteria_results)
        
        # Calculate confidence
        confidence = self._calculate_confidence(criteria_results, metrics)
        
        # Identify side effects
        side_effects = self._identify_side_effects(
            decision,
            actual_result,
            context
        )
        
        # Calculate progress made
        progress_score = self._calculate_progress_score(
            decision,
            actual_result,
            context
        )
        
        # Calculate efficiency score
        efficiency_score = self._calculate_efficiency_score(
            decision,
            actual_result,
            metrics
        )
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            criteria_results,
            overall_result
        )
        
        # Generate corrective actions
        corrective_actions = self._generate_corrective_actions(
            criteria_results,
            overall_result
        )
        
        return ValidationReport(
            validation_id=self._generate_validation_id(),
            timestamp=datetime.now(),
            decision=decision,
            criteria_results=criteria_results,
            overall_result=overall_result,
            confidence=confidence,
            side_effects=side_effects,
            progress_made=progress_score,
            efficiency_score=efficiency_score,
            recommendations=recommendations,
            corrective_actions=corrective_actions
        )
    
    def _collect_validation_metrics(
        self,
        decision: Decision,
        actual_result: Dict[str, Any],
        validation_methods: List[ValidationMethod]
    ) -> ValidationMetrics:
        """
        Collect metrics during validation.
        
        Args:
            decision: Decision that was made
            actual_result: Actual result of action
            validation_methods: Methods to use for validation
        
        Returns:
            ValidationMetrics with collected metrics
        """
        metrics = ValidationMetrics(
            tests_passed=actual_result.get('tests_passed', 0),
            tests_failed=actual_result.get('tests_failed', 0),
            code_coverage=actual_result.get('code_coverage', 0.0),
            lines_added=actual_result.get('lines_added', 0),
            lines_removed=actual_result.get('lines_removed', 0),
            execution_time=actual_result.get('execution_time', 0.0),
            resource_usage=actual_result.get('resource_usage', {}),
            user_satisfaction=actual_result.get('user_satisfaction')
        )
        
        return metrics
    
    def _check_goal_achievement(
        self,
        decision: Decision,
        actual_result: Dict[str, Any],
        metrics: ValidationMetrics
    ) -> Tuple[bool, str]:
        """
        Check if action achieved primary goal.
        
        Args:
            decision: Decision that was made
            actual_result: Actual result of action
            metrics: Validation metrics
        
        Returns:
            Tuple of (achieved, reason)
        """
        # Check if expected outcome matches actual result
        expected_outcome = decision.expected_outcome.lower()
        
        # Check test results
        if metrics.tests_failed > 0:
            total_tests = metrics.tests_passed + metrics.tests_failed
            pass_rate = metrics.tests_passed / total_tests if total_tests > 0 else 0
            
            if pass_rate < self.thresholds['test_pass_rate']:
                return (
                    False,
                    f"Test pass rate {pass_rate:.0%} below threshold {self.thresholds['test_pass_rate']:.0%}"
                )
        
        # Check if result indicates success
        success = actual_result.get('success', True)
        if not success:
            error_msg = actual_result.get('error', 'Unknown error')
            return (False, f"Action failed: {error_msg}")
        
        # Check if expected outcome was achieved
        if 'achieved' not in actual_result.get('status', ''):
            return (True, "Primary goal achieved")
        
        return (True, "Primary goal achieved")
    
    def _check_side_effects(
        self,
        decision: Decision,
        actual_result: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """
        Check for unintended side effects.
        
        Args:
            decision: Decision that was made
            actual_result: Actual result of action
            context: Current context
        
        Returns:
            Tuple of (no_negative_side_effects, reason)
        """
        side_effects = actual_result.get('side_effects', [])
        
        # Check number of side effects
        if len(side_effects) > self.thresholds['max_side_effects']:
            return (
                False,
                f"Too many side effects: {len(side_effects)} "
                f"(threshold: {self.thresholds['max_side_effects']})"
            )
        
        # Check for critical side effects
        critical_effects = [
            se for se in side_effects
            if 'critical' in se.lower() or 'severe' in se.lower()
        ]
        if critical_effects:
            return (
                False,
                f"Critical side effects detected: {critical_effects}"
            )
        
        # Check for regressions
        regressions = actual_result.get('regressions', [])
        if regressions:
            return (
                False,
                f"Regressions detected: {len(regressions)}"
            )
        
        return (True, "No negative side effects detected")
    
    def _check_progress(
        self,
        decision: Decision,
        actual_result: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """
        Check if measurable progress was made.
        
        Args:
            decision: Decision that was made
            actual_result: Actual result of action
            context: Current context
        
        Returns:
            Tuple of (progress_made, reason)
        """
        # Get progress from actual result
        progress = actual_result.get('progress', 0.0)
        
        # Check against thresholds
        if progress < self.thresholds['min_progress']:
            return (
                False,
                f"Insufficient progress: {progress:.0%} "
                f"(minimum: {self.thresholds['min_progress']:.0%})"
            )
        
        # Check if expected progress was made
        expected = decision.expected_outcome
        if 'complete' in expected.lower():
            if progress < 1.0:
                return (
                    True,
                    f"Partial progress: {progress:.0%} "
                    f"(expected completion)"
                )
        
        return (True, f"Progress made: {progress:.0%}")
    
    def _check_efficiency(
        self,
        decision: Decision,
        actual_result: Dict[str, Any],
        metrics: ValidationMetrics
    ) -> Tuple[bool, str]:
        """
        Check if action was efficient.
        
        Args:
            decision: Decision that was made
            actual_result: Actual result of action
            metrics: Validation metrics
        
        Returns:
            Tuple of (efficient, reason)
        """
        # Calculate efficiency score
        efficiency = self._calculate_efficiency_score(decision, actual_result, metrics)
        
        # Check against threshold
        if efficiency < self.thresholds['min_efficiency']:
            return (
                False,
                f"Low efficiency: {efficiency:.0%} "
                f"(minimum: {self.thresholds['min_efficiency']:.0%})"
            )
        
        # Compare expected vs actual resources
        expected_resources = decision.resources
        actual_resources = metrics.resource_usage
        
        for resource_type, expected_value in expected_resources.items():
            actual_value = actual_resources.get(resource_type, 0)
            if actual_value > expected_value * 1.5:  # 50% over budget
                return (
                    False,
                    f"Resource overage: {resource_type} "
                    f"{actual_value:.1f} vs expected {expected_value:.1f}"
                )
        
        return (True, f"Efficient: {efficiency:.0%}")
    
    def _determine_overall_result(
        self,
        criteria_results: Dict[ValidationCriteria, Tuple[bool, str]]
    ) -> ValidationResult:
        """
        Determine overall validation result.
        
        Args:
            criteria_results: Results for each criterion
        
        Returns:
            Overall ValidationResult
        """
        # Count passed and failed criteria
        passed_count = sum(1 for passed, _ in criteria_results.values() if passed)
        total_count = len(criteria_results)
        
        # If all passed, validation succeeded
        if passed_count == total_count:
            return ValidationResult.PASSED
        
        # If goal achievement failed, needs correction (highest priority)
        goal_achieved = criteria_results.get(ValidationCriteria.GOAL_ACHIEVEMENT, (True, ""))[0]
        if not goal_achieved:
            return ValidationResult.NEEDS_CORRECTION
        
        # If most passed, partial success
        if passed_count >= total_count * 0.5:
            return ValidationResult.PARTIAL
        
        # Otherwise, failed
        return ValidationResult.FAILED
    
    def _calculate_confidence(
        self,
        criteria_results: Dict[ValidationCriteria, Tuple[bool, str]],
        metrics: ValidationMetrics
    ) -> float:
        """
        Calculate confidence in validation result.
        
        Args:
            criteria_results: Results for each criterion
            metrics: Validation metrics
        
        Returns:
            Confidence score between 0.0 and 1.0
        """
        # Start with base confidence
        confidence = 0.5
        
        # Adjust based on passed criteria
        passed_count = sum(1 for passed, _ in criteria_results.values() if passed)
        total_count = len(criteria_results)
        confidence += (passed_count / total_count) * 0.4
        
        # Adjust based on test results
        total_tests = metrics.tests_passed + metrics.tests_failed
        if total_tests > 0:
            test_confidence = metrics.tests_passed / total_tests
            confidence = (confidence + test_confidence) / 2
        
        # Adjust based on code coverage
        if metrics.code_coverage > 0.8:
            confidence += 0.1
        
        # Ensure confidence is in valid range
        return max(min(confidence, 1.0), 0.0)
    
    def _identify_side_effects(
        self,
        decision: Decision,
        actual_result: Dict[str, Any],
        context: Dict[str, Any]
    ) -> List[str]:
        """
        Identify side effects of action.
        
        Args:
            decision: Decision that was made
            actual_result: Actual result of action
            context: Current context
        
        Returns:
            List of side effect descriptions
        """
        side_effects = []
        
        # Get side effects from actual result
        side_effects.extend(actual_result.get('side_effects', []))
        
        # Get regressions
        regressions = actual_result.get('regressions', [])
        for regression in regressions:
            side_effects.append(f"Regression: {regression}")
        
        # Check for broken dependencies
        broken_deps = actual_result.get('broken_dependencies', [])
        for dep in broken_deps:
            side_effects.append(f"Broken dependency: {dep}")
        
        # Check for performance degradation
        perf_degradation = actual_result.get('performance_degradation')
        if perf_degradation:
            side_effects.append(f"Performance degradation: {perf_degradation}")
        
        return side_effects
    
    def _calculate_progress_score(
        self,
        decision: Decision,
        actual_result: Dict[str, Any],
        context: Dict[str, Any]
    ) -> float:
        """
        Calculate progress score for action.
        
        Args:
            decision: Decision that was made
            actual_result: Actual result of action
            context: Current context
        
        Returns:
            Progress score between 0.0 and 1.0
        """
        # Get progress from actual result
        progress = actual_result.get('progress', 0.0)
        
        # Adjust based on lines added/removed
        if progress == 0.0:
            # Estimate progress from code changes
            lines_added = actual_result.get('lines_added', 0)
            lines_removed = actual_result.get('lines_removed', 0)
            
            # Simple heuristic: 100 lines = 10% progress
            code_progress = min((lines_added + lines_removed) / 1000, 1.0)
            progress = code_progress * 0.5  # Conservative estimate
        
        return max(min(progress, 1.0), 0.0)
    
    def _calculate_efficiency_score(
        self,
        decision: Decision,
        actual_result: Dict[str, Any],
        metrics: ValidationMetrics
    ) -> float:
        """
        Calculate efficiency score for action.
        
        Args:
            decision: Decision that was made
            actual_result: Actual result of action
            metrics: Validation metrics
        
        Returns:
            Efficiency score between 0.0 and 1.0
        """
        # Start with base efficiency
        efficiency = 0.5
        
        # Adjust based on resource usage
        expected_resources = decision.resources
        actual_resources = metrics.resource_usage
        
        resource_efficiencies = []
        for resource_type, expected_value in expected_resources.items():
            actual_value = actual_resources.get(resource_type, 0)
            if expected_value > 0 and actual_value > 0:
                # Calculate resource efficiency (1 = expected, <1 = over, >1 = under)
                resource_eff = expected_value / actual_value
                resource_efficiencies.append(min(resource_eff, 1.0))
            elif actual_value == 0:
                # If no actual resource used, consider it efficient
                resource_efficiencies.append(1.0)
        
        if resource_efficiencies:
            avg_resource_efficiency = sum(resource_efficiencies) / len(resource_efficiencies)
            efficiency = (efficiency + avg_resource_efficiency) / 2
        
        # Adjust based on execution time (use resources time estimate if available)
        expected_time = decision.resources.get('time', 10.0)
        actual_time = metrics.execution_time
        
        if actual_time > 0:
            time_efficiency = expected_time / actual_time
            efficiency = (efficiency + min(time_efficiency, 1.0)) / 2
        
        # Adjust based on test pass rate
        total_tests = metrics.tests_passed + metrics.tests_failed
        if total_tests > 0:
            test_efficiency = metrics.tests_passed / total_tests
            efficiency = (efficiency + test_efficiency) / 2
        
        return max(min(efficiency, 1.0), 0.0)
    
    def _generate_recommendations(
        self,
        criteria_results: Dict[ValidationCriteria, Tuple[bool, str]],
        overall_result: ValidationResult
    ) -> List[str]:
        """
        Generate recommendations based on validation results.
        
        Args:
            criteria_results: Results for each criterion
            overall_result: Overall validation result
        
        Returns:
            List of recommendation strings
        """
        recommendations = []
        
        # Generate recommendations based on failed criteria
        for criterion, (passed, reason) in criteria_results.items():
            if not passed:
                recommendations.append(f"Improve {criterion.value}: {reason}")
        
        # Generate recommendations based on overall result
        if overall_result == ValidationResult.PARTIAL:
            recommendations.append("Consider additional actions to complete validation")
        elif overall_result == ValidationResult.NEEDS_CORRECTION:
            recommendations.append("Action requires corrective measures")
            recommendations.append("Review and adjust approach")
        elif overall_result == ValidationResult.FAILED:
            recommendations.append("Action failed validation")
            recommendations.append("Consider alternative approach or rollback")
        
        return recommendations
    
    def _generate_corrective_actions(
        self,
        criteria_results: Dict[ValidationCriteria, Tuple[bool, str]],
        overall_result: ValidationResult
    ) -> List[str]:
        """
        Generate corrective actions based on validation results.
        
        Args:
            criteria_results: Results for each criterion
            overall_result: Overall validation result
        
        Returns:
            List of corrective action strings
        """
        corrective_actions = []
        
        # Only generate corrective actions if needed
        if overall_result == ValidationResult.PASSED:
            return corrective_actions
        
        # Generate corrective actions based on failed criteria
        for criterion, (passed, reason) in criteria_results.items():
            if not passed:
                if criterion == ValidationCriteria.GOAL_ACHIEVEMENT:
                    corrective_actions.append("Re-execute action with corrected implementation")
                    corrective_actions.append("Add additional tests to verify goal achievement")
                elif criterion == ValidationCriteria.SIDE_EFFECTS:
                    corrective_actions.append("Review and fix side effects")
                    corrective_actions.append("Add regression tests for affected areas")
                elif criterion == ValidationCriteria.PROGRESS:
                    corrective_actions.append("Break task into smaller steps")
                    corrective_actions.append("Focus on core functionality first")
                elif criterion == ValidationCriteria.EFFICIENCY:
                    corrective_actions.append("Optimize resource usage")
                    corrective_actions.append("Consider alternative implementation approach")
        
        # Add general corrective actions
        if overall_result == ValidationResult.NEEDS_CORRECTION:
            corrective_actions.append("Rollback to previous state if necessary")
            corrective_actions.append("Re-evaluate decision and select alternative action")
        elif overall_result == ValidationResult.FAILED:
            corrective_actions.append("Rollback to previous state")
            corrective_actions.append("Review task requirements and constraints")
            corrective_actions.append("Seek human intervention if needed")
        
        return corrective_actions
    
    def _generate_validation_id(self) -> str:
        """Generate unique validation ID."""
        import uuid
        return str(uuid.uuid4())
    
    def update_context_with_validation(
        self,
        context: Dict[str, Any],
        validation_report: ValidationReport
    ) -> Dict[str, Any]:
        """
        Update context with validation results.
        
        Args:
            context: Current context
            validation_report: Validation report to add
        
        Returns:
            Updated context
        """
        # Add validation report to context
        context['validation_report'] = {
            'validation_id': validation_report.validation_id,
            'timestamp': validation_report.timestamp.isoformat(),
            'overall_result': validation_report.overall_result.value,
            'confidence': validation_report.confidence,
            'progress_made': validation_report.progress_made,
            'efficiency_score': validation_report.efficiency_score,
            'criteria_results': {
                criterion.value: (passed, reason)
                for criterion, (passed, reason) in validation_report.criteria_results.items()
            },
            'side_effects': validation_report.side_effects,
            'recommendations': validation_report.recommendations,
            'corrective_actions': validation_report.corrective_actions
        }
        
        # Update recent actions with validation result
        if 'recent_actions' not in context:
            context['recent_actions'] = []
        
        context['recent_actions'].append({
            'action': validation_report.decision.selected_action,
            'validation_result': validation_report.overall_result.value,
            'confidence': validation_report.confidence,
            'timestamp': validation_report.timestamp.isoformat()
        })
        
        # Update success metrics
        if 'success_metrics' not in context:
            context['success_metrics'] = {}
        
        context['success_metrics']['total_validations'] = (
            context['success_metrics'].get('total_validations', 0) + 1
        )
        
        if validation_report.overall_result == ValidationResult.PASSED:
            context['success_metrics']['passed'] = (
                context['success_metrics'].get('passed', 0) + 1
            )
        
        return context
    
    def track_validation_accuracy(
        self,
        validation_report: ValidationReport,
        actual_outcome: str
    ):
        """
        Track validation accuracy for continuous improvement.
        
        Args:
            validation_report: Validation report
            actual_outcome: Actual outcome of action ('success' or 'failure')
        """
        # Record validation in history
        validation_record = {
            'validation_id': validation_report.validation_id,
            'timestamp': validation_report.timestamp.isoformat(),
            'predicted_result': validation_report.overall_result.value,
            'confidence': validation_report.confidence,
            'actual_outcome': actual_outcome,
            'correct': (
                validation_report.overall_result == ValidationResult.PASSED
                and actual_outcome == 'success'
            ) or (
                validation_report.overall_result != ValidationResult.PASSED
                and actual_outcome == 'failure'
            )
        }
        
        self.validation_history.append(validation_record)
        
        # Calculate accuracy
        if len(self.validation_history) > 0:
            correct_count = sum(1 for record in self.validation_history if record['correct'])
            accuracy = correct_count / len(self.validation_history)
            
            self.logger.info(
                f"Validation accuracy: {accuracy:.0%} "
                f"({correct_count}/{len(self.validation_history)})"
            )
        
        # Log to telemetry if available
        if self.telemetry_manager:
            self.telemetry_manager.record_metric(
                validation_report.validation_id,
                'validation_accuracy',
                accuracy if len(self.validation_history) > 0 else 0.0,
                'percentage'
            )
    
    def get_validation_accuracy(self) -> float:
        """
        Get current validation accuracy.
        
        Returns:
            Accuracy percentage (0.0 to 1.0)
        """
        if not self.validation_history:
            return 0.0
        
        correct_count = sum(1 for record in self.validation_history if record['correct'])
        return correct_count / len(self.validation_history)
    
    def set_thresholds(
        self,
        min_progress: Optional[float] = None,
        expected_progress: Optional[float] = None,
        min_efficiency: Optional[float] = None,
        test_pass_rate: Optional[float] = None,
        max_side_effects: Optional[int] = None
    ):
        """
        Update validation thresholds.
        
        Args:
            min_progress: Minimum progress threshold
            expected_progress: Expected progress threshold
            min_efficiency: Minimum efficiency threshold
            test_pass_rate: Test pass rate threshold
            max_side_effects: Maximum acceptable side effects
        """
        if min_progress is not None:
            self.thresholds['min_progress'] = min_progress
        if expected_progress is not None:
            self.thresholds['expected_progress'] = expected_progress
        if min_efficiency is not None:
            self.thresholds['min_efficiency'] = min_efficiency
        if test_pass_rate is not None:
            self.thresholds['test_pass_rate'] = test_pass_rate
        if max_side_effects is not None:
            self.thresholds['max_side_effects'] = max_side_effects
        
        self.logger.info(f"Updated thresholds: {self.thresholds}")


# Singleton instance for factory pattern
_action_validator_instance = None


def get_action_validator(telemetry_manager=None) -> ActionValidator:
    """
    Get singleton instance of ActionValidator.
    
    Args:
        telemetry_manager: Optional telemetry manager
    
    Returns:
        ActionValidator instance
    """
    global _action_validator_instance
    
    if _action_validator_instance is None:
        _action_validator_instance = ActionValidator(telemetry_manager)
    
    return _action_validator_instance
