"""
Unit tests for Action Validator module (Task 2.4)

Tests action validation functionality including:
- Goal achievement validation
- Side effects detection
- Progress measurement
- Efficiency checking
- Validation report generation
- Context updates
- Validation accuracy tracking
"""

import unittest
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch

from v5.logic.action_validator import (
    ActionValidator,
    ValidationCriteria,
    ValidationResult,
    ValidationMethod,
    ValidationReport,
    ValidationMetrics
)
from v5.logic.decision_maker import (
    Decision,
    DecisionStrategy,
    SituationReport,
    SituationType,
    PotentialAction
)


class TestActionValidator(unittest.TestCase):
    """Test cases for ActionValidator class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.validator = ActionValidator()
        
        # Create a sample decision
        self.sample_decision = self._create_sample_decision()
        
        # Create sample actual result
        self.sample_result = {
            'success': True,
            'tests_passed': 8,
            'tests_failed': 2,
            'code_coverage': 0.85,
            'lines_added': 50,
            'lines_removed': 10,
            'execution_time': 15.0,
            'resource_usage': {
                'tokens': 900,
                'time': 15.0,
                'money': 0.009
            },
            'progress': 0.25
        }
        
        # Create sample context
        self.sample_context = {
            'recent_actions': [
                {'action': 'test_action', 'status': 'success'}
            ],
            'recent_errors': []
        }
    
    def _create_sample_decision(self):
        """Create a sample decision for testing."""
        from v5.logic.context_analyzer import SituationFeatures
        
        potential_action = PotentialAction(
            action="implement_feature",
            risk_level=0.1,
            expected_outcome="Feature implemented successfully",
            confidence=0.9
        )
        
        situation_report = SituationReport(
            situation_type=SituationType.NORMAL,
            features=SituationFeatures(),
            potential_actions=[potential_action],
            confidence=0.95,
            recommendations=[],
            reasoning="Normal situation detected"
        )
        
        return Decision(
            decision_id="test-decision-1",
            timestamp=datetime.now(),
            context={},
            situation_report=situation_report,
            selected_action="implement_feature",
            strategy=DecisionStrategy.OPTIMAL,
            confidence=0.9,
            reasoning="Selected for optimal balance",
            alternatives=[],
            expected_outcome="Feature implemented successfully",
            resources={
                'tokens': 1000.0,
                'time': 20.0,
                'money': 0.01
            }
        )
    
    def test_initialization(self):
        """Test validator initialization."""
        self.assertIsNotNone(self.validator)
        self.assertIsNone(self.validator.telemetry_manager)
        self.assertIsInstance(self.validator.validation_history, list)
        self.assertEqual(len(self.validator.validation_history), 0)
        self.assertEqual(self.validator.thresholds['min_progress'], 0.1)
        self.assertEqual(self.validator.thresholds['test_pass_rate'], 0.8)
    
    def test_initialization_with_telemetry(self):
        """Test validator initialization with telemetry manager."""
        telemetry_manager = Mock()
        validator = ActionValidator(telemetry_manager=telemetry_manager)
        
        self.assertIsNotNone(validator.telemetry_manager)
        self.assertEqual(validator.telemetry_manager, telemetry_manager)
    
    def test_validate_action_success(self):
        """Test successful action validation."""
        report = self.validator.validate_action(
            self.sample_decision,
            self.sample_result,
            self.sample_context
        )
        
        self.assertIsInstance(report, ValidationReport)
        self.assertEqual(report.overall_result, ValidationResult.PASSED)
        self.assertGreaterEqual(report.confidence, 0.0)
        self.assertLessEqual(report.confidence, 1.0)
        self.assertGreaterEqual(report.progress_made, 0.0)
        self.assertLessEqual(report.progress_made, 1.0)
        self.assertGreaterEqual(report.efficiency_score, 0.0)
        self.assertLessEqual(report.efficiency_score, 1.0)
    
    def test_validate_action_with_test_failures(self):
        """Test validation with test failures."""
        result = self.sample_result.copy()
        result['tests_passed'] = 2
        result['tests_failed'] = 8  # 20% pass rate - below 80% threshold
        
        report = self.validator.validate_action(
            self.sample_decision,
            result,
            self.sample_context
        )
        
        # Goal achievement failed due to low test pass rate
        self.assertEqual(report.overall_result, ValidationResult.NEEDS_CORRECTION)
        self.assertIn(ValidationCriteria.GOAL_ACHIEVEMENT, report.criteria_results)
        self.assertFalse(report.criteria_results[ValidationCriteria.GOAL_ACHIEVEMENT][0])
    
    def test_validate_action_with_side_effects(self):
        """Test validation with side effects."""
        result = self.sample_result.copy()
        result['side_effects'] = [
            'Minor issue 1',
            'Minor issue 2',
            'Minor issue 3'  # Exceeds threshold
        ]
        
        report = self.validator.validate_action(
            self.sample_decision,
            result,
            self.sample_context
        )
        
        self.assertIn(ValidationCriteria.SIDE_EFFECTS, report.criteria_results)
        self.assertFalse(report.criteria_results[ValidationCriteria.SIDE_EFFECTS][0])
        self.assertGreater(len(report.side_effects), 0)
    
    def test_validate_action_with_insufficient_progress(self):
        """Test validation with insufficient progress."""
        result = self.sample_result.copy()
        result['progress'] = 0.05  # Below 10% threshold
        
        report = self.validator.validate_action(
            self.sample_decision,
            result,
            self.sample_context
        )
        
        self.assertIn(ValidationCriteria.PROGRESS, report.criteria_results)
        self.assertFalse(report.criteria_results[ValidationCriteria.PROGRESS][0])
    
    def test_validate_action_with_low_efficiency(self):
        """Test validation with low efficiency."""
        result = self.sample_result.copy()
        result['resource_usage']['tokens'] = 2000  # 2x expected
        
        report = self.validator.validate_action(
            self.sample_decision,
            result,
            self.sample_context
        )
        
        self.assertIn(ValidationCriteria.EFFICIENCY, report.criteria_results)
        # Should detect resource overage
        self.assertLess(report.efficiency_score, 1.0)
    
    def test_validate_action_partial_success(self):
        """Test validation with partial success."""
        result = self.sample_result.copy()
        result['progress'] = 0.15  # Slightly above minimum
        result['side_effects'] = ['Minor issue']
        
        report = self.validator.validate_action(
            self.sample_decision,
            result,
            self.sample_context
        )
        
        # Should be PASSED or PARTIAL depending on overall assessment
        self.assertIn(
            report.overall_result,
            [ValidationResult.PASSED, ValidationResult.PARTIAL]
        )
    
    def test_validate_action_needs_correction(self):
        """Test validation that needs correction."""
        result = self.sample_result.copy()
        result['success'] = False
        result['error'] = 'Implementation failed'
        result['progress'] = 0.0  # Also no progress
        result['side_effects'] = ['Critical issue', 'Another issue']  # Also side effects
        
        report = self.validator.validate_action(
            self.sample_decision,
            result,
            self.sample_context
        )
        
        # Goal failed + other failures = NEEDS_CORRECTION
        self.assertEqual(report.overall_result, ValidationResult.NEEDS_CORRECTION)
        self.assertGreater(len(report.corrective_actions), 0)
    
    def test_collect_validation_metrics(self):
        """Test validation metrics collection."""
        metrics = self.validator._collect_validation_metrics(
            self.sample_decision,
            self.sample_result,
            [ValidationMethod.TEST_EXECUTION]
        )
        
        self.assertIsInstance(metrics, ValidationMetrics)
        self.assertEqual(metrics.tests_passed, 8)
        self.assertEqual(metrics.tests_failed, 2)
        self.assertEqual(metrics.code_coverage, 0.85)
        self.assertEqual(metrics.lines_added, 50)
        self.assertEqual(metrics.lines_removed, 10)
        self.assertEqual(metrics.execution_time, 15.0)
    
    def test_check_goal_achievement(self):
        """Test goal achievement check."""
        metrics = ValidationMetrics(
            tests_passed=10,
            tests_failed=0,
            code_coverage=0.9,
            lines_added=50,
            lines_removed=0,
            execution_time=10.0,
            resource_usage={},
            user_satisfaction=None
        )
        
        achieved, reason = self.validator._check_goal_achievement(
            self.sample_decision,
            {'success': True},
            metrics
        )
        
        self.assertTrue(achieved)
        self.assertIn('achieved', reason.lower())
    
    def test_check_goal_achievement_with_failures(self):
        """Test goal achievement check with test failures."""
        metrics = ValidationMetrics(
            tests_passed=5,
            tests_failed=5,
            code_coverage=0.5,
            lines_added=50,
            lines_removed=0,
            execution_time=10.0,
            resource_usage={},
            user_satisfaction=None
        )
        
        achieved, reason = self.validator._check_goal_achievement(
            self.sample_decision,
            {'success': True},
            metrics
        )
        
        self.assertFalse(achieved)
        self.assertIn('pass rate', reason.lower())
    
    def test_check_side_effects_none(self):
        """Test side effects check with no side effects."""
        result = {
            'success': True,
            'side_effects': [],
            'regressions': []
        }
        
        passed, reason = self.validator._check_side_effects(
            self.sample_decision,
            result,
            self.sample_context
        )
        
        self.assertTrue(passed)
        self.assertIn('no negative', reason.lower())
    
    def test_check_side_effects_with_critical(self):
        """Test side effects check with critical effects."""
        result = {
            'success': True,
            'side_effects': ['Critical system failure']
        }
        
        passed, reason = self.validator._check_side_effects(
            self.sample_decision,
            result,
            self.sample_context
        )
        
        self.assertFalse(passed)
        self.assertIn('critical', reason.lower())
    
    def test_check_progress_sufficient(self):
        """Test progress check with sufficient progress."""
        result = {'progress': 0.3}
        
        passed, reason = self.validator._check_progress(
            self.sample_decision,
            result,
            self.sample_context
        )
        
        self.assertTrue(passed)
        self.assertIn('progress', reason.lower())
    
    def test_check_progress_insufficient(self):
        """Test progress check with insufficient progress."""
        result = {'progress': 0.05}
        
        passed, reason = self.validator._check_progress(
            self.sample_decision,
            result,
            self.sample_context
        )
        
        self.assertFalse(passed)
        self.assertIn('insufficient', reason.lower())
    
    def test_check_efficiency_good(self):
        """Test efficiency check with good efficiency."""
        metrics = ValidationMetrics(
            tests_passed=10,
            tests_failed=0,
            code_coverage=0.9,
            lines_added=50,
            lines_removed=0,
            execution_time=10.0,
            resource_usage={'tokens': 800, 'time': 10.0}
        )
        
        passed, reason = self.validator._check_efficiency(
            self.sample_decision,
            {'success': True},
            metrics
        )
        
        self.assertTrue(passed)
        self.assertIn('efficient', reason.lower())
    
    def test_check_efficiency_low(self):
        """Test efficiency check with low efficiency."""
        metrics = ValidationMetrics(
            tests_passed=10,
            tests_failed=0,
            code_coverage=0.9,
            lines_added=50,
            lines_removed=0,
            execution_time=10.0,
            resource_usage={'tokens': 2000, 'time': 10.0}  # 2x expected
        )
        
        passed, reason = self.validator._check_efficiency(
            self.sample_decision,
            {'success': True},
            metrics
        )
        
        self.assertFalse(passed)
        self.assertIn('resource', reason.lower())
    
    def test_determine_overall_result_all_passed(self):
        """Test overall result determination with all criteria passed."""
        criteria_results = {
            ValidationCriteria.GOAL_ACHIEVEMENT: (True, "Good"),
            ValidationCriteria.SIDE_EFFECTS: (True, "Good"),
            ValidationCriteria.PROGRESS: (True, "Good"),
            ValidationCriteria.EFFICIENCY: (True, "Good")
        }
        
        result = self.validator._determine_overall_result(criteria_results)
        
        self.assertEqual(result, ValidationResult.PASSED)
    
    def test_determine_overall_result_partial(self):
        """Test overall result determination with partial success."""
        criteria_results = {
            ValidationCriteria.GOAL_ACHIEVEMENT: (True, "Good"),
            ValidationCriteria.SIDE_EFFECTS: (False, "Bad"),
            ValidationCriteria.PROGRESS: (True, "Good"),
            ValidationCriteria.EFFICIENCY: (False, "Bad")
        }
        
        result = self.validator._determine_overall_result(criteria_results)
        
        self.assertEqual(result, ValidationResult.PARTIAL)
    
    def test_determine_overall_result_failed(self):
        """Test overall result determination with failure."""
        criteria_results = {
            ValidationCriteria.GOAL_ACHIEVEMENT: (True, "Good"),  # Goal achieved but all other criteria fail
            ValidationCriteria.SIDE_EFFECTS: (False, "Bad"),
            ValidationCriteria.PROGRESS: (False, "Bad"),
            ValidationCriteria.EFFICIENCY: (False, "Bad")
        }
        
        result = self.validator._determine_overall_result(criteria_results)
        
        # Only 1/4 passed (25% < 50%), so should be FAILED
        self.assertEqual(result, ValidationResult.FAILED)
    
    def test_determine_overall_result_needs_correction(self):
        """Test overall result determination with goal failure and low pass rate."""
        criteria_results = {
            ValidationCriteria.GOAL_ACHIEVEMENT: (False, "Bad"),
            ValidationCriteria.SIDE_EFFECTS: (True, "Good"),
            ValidationCriteria.PROGRESS: (False, "Bad"),  # Also fail progress
            ValidationCriteria.EFFICIENCY: (False, "Bad")  # Also fail efficiency
        }
        
        result = self.validator._determine_overall_result(criteria_results)
        
        # Goal failed and only 2/4 passed (50% = threshold, but goal failed), so NEEDS_CORRECTION
        self.assertEqual(result, ValidationResult.NEEDS_CORRECTION)
    
    def test_calculate_confidence(self):
        """Test confidence calculation."""
        criteria_results = {
            ValidationCriteria.GOAL_ACHIEVEMENT: (True, "Good"),
            ValidationCriteria.SIDE_EFFECTS: (True, "Good"),
            ValidationCriteria.PROGRESS: (True, "Good"),
            ValidationCriteria.EFFICIENCY: (True, "Good")
        }
        
        metrics = ValidationMetrics(
            tests_passed=10,
            tests_failed=0,
            code_coverage=0.9,
            lines_added=50,
            lines_removed=0,
            execution_time=10.0,
            resource_usage={}
        )
        
        confidence = self.validator._calculate_confidence(
            criteria_results,
            metrics
        )
        
        self.assertGreater(confidence, 0.0)
        self.assertLessEqual(confidence, 1.0)
        self.assertGreater(confidence, 0.8)  # Should be high for all passed
    
    def test_identify_side_effects(self):
        """Test side effects identification."""
        result = {
            'side_effects': ['Minor issue'],
            'regressions': ['Feature X broke'],
            'broken_dependencies': ['module_a'],
            'performance_degradation': '50% slower'
        }
        
        side_effects = self.validator._identify_side_effects(
            self.sample_decision,
            result,
            self.sample_context
        )
        
        self.assertEqual(len(side_effects), 4)
        self.assertIn('Minor issue', side_effects)
        self.assertIn('Regression: Feature X broke', side_effects)
        self.assertIn('Broken dependency: module_a', side_effects)
        self.assertIn('Performance degradation: 50% slower', side_effects)
    
    def test_calculate_progress_score(self):
        """Test progress score calculation."""
        result = {'progress': 0.5}
        
        score = self.validator._calculate_progress_score(
            self.sample_decision,
            result,
            self.sample_context
        )
        
        self.assertEqual(score, 0.5)
    
    def test_calculate_progress_score_from_lines(self):
        """Test progress score calculation from code lines."""
        result = {
            'progress': 0.0,
            'lines_added': 200,
            'lines_removed': 50
        }
        
        score = self.validator._calculate_progress_score(
            self.sample_decision,
            result,
            self.sample_context
        )
        
        # Should estimate progress from lines (250 lines / 1000 = 25%)
        self.assertGreater(score, 0.0)
        self.assertLess(score, 0.5)
    
    def test_calculate_efficiency_score(self):
        """Test efficiency score calculation."""
        metrics = ValidationMetrics(
            tests_passed=10,
            tests_failed=0,
            code_coverage=0.9,
            lines_added=50,
            lines_removed=0,
            execution_time=15.0,
            resource_usage={'tokens': 900, 'time': 15.0}
        )
        
        score = self.validator._calculate_efficiency_score(
            self.sample_decision,
            {'success': True},
            metrics
        )
        
        self.assertGreater(score, 0.0)
        self.assertLessEqual(score, 1.0)
    
    def test_generate_recommendations(self):
        """Test recommendation generation."""
        criteria_results = {
            ValidationCriteria.GOAL_ACHIEVEMENT: (False, "Goal not achieved"),
            ValidationCriteria.SIDE_EFFECTS: (True, "No side effects"),
            ValidationCriteria.PROGRESS: (False, "Low progress"),
            ValidationCriteria.EFFICIENCY: (True, "Efficient")
        }
        
        recommendations = self.validator._generate_recommendations(
            criteria_results,
            ValidationResult.PARTIAL
        )
        
        self.assertGreater(len(recommendations), 0)
        self.assertTrue(
            any('goal_achievement' in rec for rec in recommendations)
        )
        self.assertTrue(
            any('progress' in rec for rec in recommendations)
        )
    
    def test_generate_corrective_actions(self):
        """Test corrective actions generation."""
        criteria_results = {
            ValidationCriteria.GOAL_ACHIEVEMENT: (False, "Goal not achieved"),
            ValidationCriteria.SIDE_EFFECTS: (False, "Side effects found"),
            ValidationCriteria.PROGRESS: (True, "Good progress"),
            ValidationCriteria.EFFICIENCY: (True, "Efficient")
        }
        
        actions = self.validator._generate_corrective_actions(
            criteria_results,
            ValidationResult.NEEDS_CORRECTION
        )
        
        self.assertGreater(len(actions), 0)
        self.assertTrue(
            any('re-execute' in action.lower() for action in actions)
        )
        self.assertTrue(
            any('side effect' in action.lower() for action in actions)
        )
    
    def test_update_context_with_validation(self):
        """Test context update with validation results."""
        # Create clean context without existing actions
        clean_context = {}
        
        report = ValidationReport(
            validation_id="test-val-1",
            timestamp=datetime.now(),
            decision=self.sample_decision,
            criteria_results={
                ValidationCriteria.GOAL_ACHIEVEMENT: (True, "Good")
            },
            overall_result=ValidationResult.PASSED,
            confidence=0.9,
            side_effects=[],
            progress_made=0.5,
            efficiency_score=0.8,
            recommendations=[],
            corrective_actions=[]
        )
        
        updated_context = self.validator.update_context_with_validation(
            clean_context,
            report
        )
        
        self.assertIn('validation_report', updated_context)
        self.assertEqual(
            updated_context['validation_report']['validation_id'],
            'test-val-1'
        )
        self.assertIn('recent_actions', updated_context)
        self.assertEqual(len(updated_context['recent_actions']), 1)
        self.assertIn('success_metrics', updated_context)
    
    def test_track_validation_accuracy(self):
        """Test validation accuracy tracking."""
        report = ValidationReport(
            validation_id="test-val-1",
            timestamp=datetime.now(),
            decision=self.sample_decision,
            criteria_results={},
            overall_result=ValidationResult.PASSED,
            confidence=0.9,
            side_effects=[],
            progress_made=0.5,
            efficiency_score=0.8,
            recommendations=[],
            corrective_actions=[]
        )
        
        # Track correct prediction
        self.validator.track_validation_accuracy(report, 'success')
        
        self.assertEqual(len(self.validator.validation_history), 1)
        self.assertTrue(self.validator.validation_history[0]['correct'])
    
    def test_track_validation_accuracy_incorrect(self):
        """Test validation accuracy tracking with incorrect prediction."""
        report = ValidationReport(
            validation_id="test-val-1",
            timestamp=datetime.now(),
            decision=self.sample_decision,
            criteria_results={},
            overall_result=ValidationResult.PASSED,
            confidence=0.9,
            side_effects=[],
            progress_made=0.5,
            efficiency_score=0.8,
            recommendations=[],
            corrective_actions=[]
        )
        
        # Track incorrect prediction (passed but actually failed)
        self.validator.track_validation_accuracy(report, 'failure')
        
        self.assertEqual(len(self.validator.validation_history), 1)
        self.assertFalse(self.validator.validation_history[0]['correct'])
    
    def test_get_validation_accuracy(self):
        """Test getting validation accuracy."""
        # Track multiple validations
        for i in range(10):
            result = 'success' if i < 8 else 'failure'
            self.validator.track_validation_accuracy(
                ValidationReport(
                    validation_id=f"test-val-{i}",
                    timestamp=datetime.now(),
                    decision=self.sample_decision,
                    criteria_results={},
                    overall_result=ValidationResult.PASSED if i < 8 else ValidationResult.FAILED,
                    confidence=0.9,
                    side_effects=[],
                    progress_made=0.5,
                    efficiency_score=0.8,
                    recommendations=[],
                    corrective_actions=[]
                ),
                result
            )
        
        accuracy = self.validator.get_validation_accuracy()
        
        self.assertEqual(accuracy, 1.0)  # All predictions correct
    
    def test_get_validation_accuracy_empty(self):
        """Test getting validation accuracy with no history."""
        accuracy = self.validator.get_validation_accuracy()
        
        self.assertEqual(accuracy, 0.0)
    
    def test_set_thresholds(self):
        """Test setting validation thresholds."""
        self.validator.set_thresholds(
            min_progress=0.2,
            expected_progress=0.4,
            min_efficiency=0.6,
            test_pass_rate=0.9,
            max_side_effects=1
        )
        
        self.assertEqual(self.validator.thresholds['min_progress'], 0.2)
        self.assertEqual(self.validator.thresholds['expected_progress'], 0.4)
        self.assertEqual(self.validator.thresholds['min_efficiency'], 0.6)
        self.assertEqual(self.validator.thresholds['test_pass_rate'], 0.9)
        self.assertEqual(self.validator.thresholds['max_side_effects'], 1)
    
    def test_set_thresholds_partial(self):
        """Test setting partial thresholds."""
        original_min_progress = self.validator.thresholds['min_progress']
        
        self.validator.set_thresholds(min_progress=0.15)
        
        self.assertEqual(self.validator.thresholds['min_progress'], 0.15)
        self.assertEqual(
            self.validator.thresholds['expected_progress'],
            0.3  # Unchanged
        )
    
    def test_validation_report_generation(self):
        """Test validation report contains all required fields."""
        report = self.validator.validate_action(
            self.sample_decision,
            self.sample_result,
            self.sample_context
        )
        
        self.assertIsNotNone(report.validation_id)
        self.assertIsNotNone(report.timestamp)
        self.assertEqual(report.decision, self.sample_decision)
        self.assertIn(ValidationCriteria.GOAL_ACHIEVEMENT, report.criteria_results)
        self.assertIn(ValidationCriteria.SIDE_EFFECTS, report.criteria_results)
        self.assertIn(ValidationCriteria.PROGRESS, report.criteria_results)
        self.assertIn(ValidationCriteria.EFFICIENCY, report.criteria_results)
        self.assertIsNotNone(report.overall_result)
        self.assertGreaterEqual(report.confidence, 0.0)
        self.assertLessEqual(report.confidence, 1.0)
        self.assertIsInstance(report.side_effects, list)
        self.assertGreaterEqual(report.progress_made, 0.0)
        self.assertLessEqual(report.progress_made, 1.0)
        self.assertGreaterEqual(report.efficiency_score, 0.0)
        self.assertLessEqual(report.efficiency_score, 1.0)
        self.assertIsInstance(report.recommendations, list)
        self.assertIsInstance(report.corrective_actions, list)
    
    def test_with_telemetry_manager(self):
        """Test validation with telemetry manager."""
        telemetry_manager = Mock()
        validator = ActionValidator(telemetry_manager=telemetry_manager)
        
        report = ValidationReport(
            validation_id="test-val-1",
            timestamp=datetime.now(),
            decision=self.sample_decision,
            criteria_results={},
            overall_result=ValidationResult.PASSED,
            confidence=0.9,
            side_effects=[],
            progress_made=0.5,
            efficiency_score=0.8,
            recommendations=[],
            corrective_actions=[]
        )
        
        validator.track_validation_accuracy(report, 'success')
        
        # Verify telemetry was called
        telemetry_manager.record_metric.assert_called_once()
        call_args = telemetry_manager.record_metric.call_args
        self.assertEqual(call_args[0][0], 'test-val-1')
        self.assertEqual(call_args[0][1], 'validation_accuracy')


if __name__ == '__main__':
    unittest.main()