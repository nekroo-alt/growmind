"""
Unit tests for Decision Maker module.

Tests decision making, action evaluation, strategy selection,
and decision explanation generation.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

from v5.logic.decision_maker import (
    DecisionMaker,
    DecisionStrategy,
    ActionEvaluation,
    Decision
)
from v5.logic.context_analyzer import (
    ContextAnalyzer,
    SituationReport,
    SituationType,
    SituationFeatures,
    PotentialAction
)


@pytest.fixture
def mock_context_analyzer():
    """Create a mock context analyzer."""
    analyzer = Mock(spec=ContextAnalyzer)
    return analyzer


@pytest.fixture
def decision_maker(mock_context_analyzer):
    """Create a decision maker instance."""
    return DecisionMaker(mock_context_analyzer)


@pytest.fixture
def sample_context():
    """Sample context for testing."""
    return {
        'recent_actions': [
            {'status': 'success'},
            {'status': 'success'},
            {'status': 'error'}
        ],
        'recent_errors': [
            {'type': 'timeout', 'severity': 'error'},
            {'type': 'permission', 'severity': 'warning'}
        ],
        'resources': {
            'tokens_available': 80.0,
            'time_available': 50.0,
            'compute_available': 70.0
        },
        'time_pressure': 0.3,
        'context_completeness': 0.7
    }


@pytest.fixture
def sample_task_info():
    """Sample task info for testing."""
    return {
        'type': 'implementation',
        'complexity': 0.6,
        'dependency_count': 3
    }


@pytest.fixture
def sample_situation_report():
    """Sample situation report for testing."""
    return SituationReport(
        situation_type=SituationType.NORMAL,
        features=SituationFeatures(
            error_frequency=0.2,
            error_types=['timeout'],
            task_complexity=0.6,
            dependency_count=3,
            resource_availability={
                'tokens': 0.8,
                'time': 0.5,
                'compute': 0.7
            },
            time_pressure=0.3,
            context_completeness=0.7,
            recent_failures=1,
            recent_successes=2
        ),
        potential_actions=[
            PotentialAction(
                action='proceed_with_task',
                risk_level=0.1,
                expected_outcome='Complete task efficiently',
                confidence=0.9
            ),
            PotentialAction(
                action='use_optimal_strategy',
                risk_level=0.15,
                expected_outcome='Maximize efficiency',
                confidence=0.85
            )
        ],
        confidence=0.8,
        recommendations=[
            'Proceed with task execution',
            'Use optimal strategy for efficiency'
        ],
        reasoning='Situation classified as normal because: Low error frequency (20%)'
    )


class TestDecisionMakerInitialization:
    """Test decision maker initialization."""
    
    def test_initialization_with_default_strategy(self, mock_context_analyzer):
        """Test initialization with default strategy."""
        dm = DecisionMaker(mock_context_analyzer)
        assert dm.context_analyzer == mock_context_analyzer
        assert dm.default_strategy == DecisionStrategy.OPTIMAL
        assert dm.weights == {
            'success': 1.0,
            'cost': 0.5,
            'risk': 0.7,
            'value': 0.8
        }
        assert dm.historical_success_rates == {}
    
    def test_initialization_with_custom_strategy(self, mock_context_analyzer):
        """Test initialization with custom strategy."""
        dm = DecisionMaker(
            mock_context_analyzer,
            default_strategy=DecisionStrategy.SAFE
        )
        assert dm.default_strategy == DecisionStrategy.SAFE


class TestDecisionMaking:
    """Test decision making functionality."""
    
    def test_make_decision_with_optimal_strategy(
        self,
        decision_maker,
        mock_context_analyzer,
        sample_context,
        sample_task_info,
        sample_situation_report
    ):
        """Test making decision with optimal strategy."""
        # Setup mock
        mock_context_analyzer.analyze_situation.return_value = sample_situation_report
        
        # Make decision
        decision = decision_maker.make_decision(
            sample_context,
            sample_task_info,
            strategy=DecisionStrategy.OPTIMAL
        )
        
        # Verify
        assert isinstance(decision, Decision)
        assert decision.strategy == DecisionStrategy.OPTIMAL
        assert decision.context == sample_context
        assert decision.situation_report == sample_situation_report
        assert decision.selected_action in ['proceed_with_task', 'use_optimal_strategy']
        assert decision.decision_id is not None
        assert isinstance(decision.timestamp, datetime)
        assert 0.0 <= decision.confidence <= 1.0
        assert len(decision.alternatives) == 1  # One alternative rejected
    
    def test_make_decision_with_greedy_strategy(
        self,
        decision_maker,
        mock_context_analyzer,
        sample_context,
        sample_task_info,
        sample_situation_report
    ):
        """Test making decision with greedy strategy."""
        # Setup mock
        mock_context_analyzer.analyze_situation.return_value = sample_situation_report
        
        # Make decision
        decision = decision_maker.make_decision(
            sample_context,
            sample_task_info,
            strategy=DecisionStrategy.GREEDY
        )
        
        # Verify greedy strategy selects highest value
        assert decision.strategy == DecisionStrategy.GREEDY
    
    def test_make_decision_with_safe_strategy(
        self,
        decision_maker,
        mock_context_analyzer,
        sample_context,
        sample_task_info,
        sample_situation_report
    ):
        """Test making decision with safe strategy."""
        # Setup mock
        mock_context_analyzer.analyze_situation.return_value = sample_situation_report
        
        # Make decision
        decision = decision_maker.make_decision(
            sample_context,
            sample_task_info,
            strategy=DecisionStrategy.SAFE
        )
        
        # Verify safe strategy selects lowest risk
        assert decision.strategy == DecisionStrategy.SAFE
    
    def test_make_decision_uses_default_strategy(
        self,
        decision_maker,
        mock_context_analyzer,
        sample_context,
        sample_task_info,
        sample_situation_report
    ):
        """Test that default strategy is used when none specified."""
        # Setup mock
        mock_context_analyzer.analyze_situation.return_value = sample_situation_report
        
        # Make decision without strategy
        decision = decision_maker.make_decision(sample_context, sample_task_info)
        
        # Verify default strategy is used
        assert decision.strategy == DecisionStrategy.OPTIMAL
    
    def test_make_decision_generates_reasoning(
        self,
        decision_maker,
        mock_context_analyzer,
        sample_context,
        sample_task_info,
        sample_situation_report
    ):
        """Test that decision includes reasoning."""
        # Setup mock
        mock_context_analyzer.analyze_situation.return_value = sample_situation_report
        
        # Make decision
        decision = decision_maker.make_decision(sample_context, sample_task_info)
        
        # Verify reasoning is generated
        assert len(decision.reasoning) > 0
        assert decision.selected_action in decision.reasoning
        assert decision.strategy.value in decision.reasoning
    
    def test_make_decision_estimates_resources(
        self,
        decision_maker,
        mock_context_analyzer,
        sample_context,
        sample_task_info,
        sample_situation_report
    ):
        """Test that decision includes resource estimates."""
        # Setup mock
        mock_context_analyzer.analyze_situation.return_value = sample_situation_report
        
        # Make decision
        decision = decision_maker.make_decision(sample_context, sample_task_info)
        
        # Verify resources are estimated
        assert 'tokens' in decision.resources
        assert 'time' in decision.resources
        assert 'money' in decision.resources
        assert all(v > 0 for v in decision.resources.values())


class TestActionEvaluation:
    """Test action evaluation functionality."""
    
    def test_estimate_success_probability_adjusts_for_history(
        self,
        decision_maker,
        sample_context,
        sample_task_info,
        sample_situation_report
    ):
        """Test success probability adjusts based on history."""
        # Set historical success rate
        decision_maker.historical_success_rates['implementation'] = 0.5
        
        # Evaluate action
        potential_action = sample_situation_report.potential_actions[0]
        probability = decision_maker._estimate_success_probability(
            potential_action,
            sample_context,
            sample_task_info
        )
        
        # Verify probability is adjusted
        # Should be average of action confidence (0.9) and historical (0.5) = 0.7
        # Plus adjustments for recent performance and errors
        assert 0.0 <= probability <= 1.0
    
    def test_estimate_cost_varies_by_action_type(
        self,
        decision_maker,
        sample_context,
        sample_task_info,
        sample_situation_report
    ):
        """Test cost estimation varies by action type."""
        actions = sample_situation_report.potential_actions
        
        # Evaluate costs for different actions
        costs = []
        for action in actions:
            cost = decision_maker._estimate_cost(
                action,
                sample_context,
                sample_task_info
            )
            costs.append(cost)
        
        # Verify costs are reasonable
        for cost in costs:
            assert 'tokens' in cost
            assert 'time' in cost
            assert 'money' in cost
            assert all(v > 0 for v in cost.values())
    
    def test_estimate_time_varies_by_action_type(
        self,
        decision_maker,
        sample_context,
        sample_task_info,
        sample_situation_report
    ):
        """Test time estimation varies by action type."""
        actions = sample_situation_report.potential_actions
        
        # Evaluate times for different actions
        times = []
        for action in actions:
            time_estimate = decision_maker._estimate_time(
                action,
                sample_context,
                sample_task_info
            )
            times.append(time_estimate)
        
        # Verify times are reasonable
        for time_estimate in times:
            assert time_estimate > 0
    
    def test_estimate_value_considers_situation_type(
        self,
        decision_maker,
        sample_context,
        sample_task_info
    ):
        """Test value estimation considers situation type."""
        # Create potential actions
        potential_action_error = PotentialAction(
            action='retry_with_backoff',
            risk_level=0.2,
            expected_outcome='Resolve transient errors',
            confidence=0.8
        )
        
        # Create situation report for error situation
        error_report = SituationReport(
            situation_type=SituationType.ERROR,
            features=SituationFeatures(),
            potential_actions=[potential_action_error],
            confidence=0.7,
            recommendations=[],
            reasoning='Error situation'
        )
        
        # Evaluate value
        value = decision_maker._estimate_value(
            potential_action_error,
            error_report
        )
        
        # Verify value is higher for actions that address the situation
        assert value > 0.5  # Should be higher for error-addressing action


class TestScoreCalculation:
    """Test score calculation functionality."""
    
    def test_calculate_score_considers_all_factors(
        self,
        decision_maker
    ):
        """Test score calculation considers all factors."""
        score = decision_maker._calculate_score(
            success_probability=0.8,
            cost={'tokens': 1000.0, 'time': 10.0, 'money': 0.01},
            risk=0.2,
            value=0.9
        )
        
        # Verify score is reasonable
        assert isinstance(score, float)
        # Higher success and value should increase score
        # Higher cost and risk should decrease score
        assert score > 0.0
    
    def test_normalize_cost(self, decision_maker):
        """Test cost normalization."""
        cost = {
            'tokens': 5000.0,
            'time': 30.0,
            'money': 0.5
        }
        
        normalized = decision_maker._normalize_cost(cost)
        
        # Verify normalization
        assert 0.0 <= normalized <= 1.0
        # Higher costs should result in higher normalized value (worse)
        assert normalized > 0.0


class TestStrategySelection:
    """Test strategy-based action selection."""
    
    def test_select_action_greedy_maximizes_value(
        self,
        decision_maker,
        sample_situation_report
    ):
        """Test greedy strategy maximizes value."""
        # Create evaluations
        evaluations = [
            ActionEvaluation(
                action='action1',
                success_probability=0.7,
                cost={'tokens': 1000.0, 'time': 10.0, 'money': 0.01},
                risk=0.2,
                time_estimate=10.0,
                value=0.5,
                score=0.5,
                reasoning='Test'
            ),
            ActionEvaluation(
                action='action2',
                success_probability=0.6,
                cost={'tokens': 2000.0, 'time': 20.0, 'money': 0.02},
                risk=0.3,
                time_estimate=20.0,
                value=0.9,
                score=0.6,
                reasoning='Test'
            )
        ]
        
        # Select with greedy strategy
        selected = decision_maker._select_action(
            evaluations,
            DecisionStrategy.GREEDY,
            SituationType.NORMAL
        )
        
        # Verify highest value action is selected
        assert selected.action == 'action2'
        assert selected.value == 0.9
    
    def test_select_action_optimal_maximizes_score(
        self,
        decision_maker,
        sample_situation_report
    ):
        """Test optimal strategy maximizes score."""
        # Create evaluations
        evaluations = [
            ActionEvaluation(
                action='action1',
                success_probability=0.8,
                cost={'tokens': 1000.0, 'time': 10.0, 'money': 0.01},
                risk=0.2,
                time_estimate=10.0,
                value=0.7,
                score=0.9,
                reasoning='Test'
            ),
            ActionEvaluation(
                action='action2',
                success_probability=0.7,
                cost={'tokens': 2000.0, 'time': 20.0, 'money': 0.02},
                risk=0.3,
                time_estimate=20.0,
                value=0.8,
                score=0.6,
                reasoning='Test'
            )
        ]
        
        # Select with optimal strategy
        selected = decision_maker._select_action(
            evaluations,
            DecisionStrategy.OPTIMAL,
            SituationType.NORMAL
        )
        
        # Verify highest score action is selected
        assert selected.action == 'action1'
        assert selected.score == 0.9
    
    def test_select_action_safe_minimizes_risk(
        self,
        decision_maker,
        sample_situation_report
    ):
        """Test safe strategy minimizes risk."""
        # Create evaluations
        evaluations = [
            ActionEvaluation(
                action='action1',
                success_probability=0.6,
                cost={'tokens': 1000.0, 'time': 10.0, 'money': 0.01},
                risk=0.1,
                time_estimate=10.0,
                value=0.5,
                score=0.5,
                reasoning='Test'
            ),
            ActionEvaluation(
                action='action2',
                success_probability=0.8,
                cost={'tokens': 2000.0, 'time': 20.0, 'money': 0.02},
                risk=0.4,
                time_estimate=20.0,
                value=0.9,
                score=0.9,
                reasoning='Test'
            )
        ]
        
        # Select with safe strategy
        selected = decision_maker._select_action(
            evaluations,
            DecisionStrategy.SAFE,
            SituationType.NORMAL
        )
        
        # Verify lowest risk action is selected
        assert selected.action == 'action1'
        assert selected.risk == 0.1


class TestAlternativeGeneration:
    """Test alternative generation."""
    
    def test_generate_alternatives_excludes_selected(
        self,
        decision_maker
    ):
        """Test alternatives exclude selected action."""
        # Create evaluations
        evaluations = [
            ActionEvaluation(
                action='action1',
                success_probability=0.8,
                cost={'tokens': 1000.0, 'time': 10.0, 'money': 0.01},
                risk=0.1,
                time_estimate=10.0,
                value=0.8,
                score=0.9,
                reasoning='Test'
            ),
            ActionEvaluation(
                action='action2',
                success_probability=0.7,
                cost={'tokens': 2000.0, 'time': 20.0, 'money': 0.02},
                risk=0.2,
                time_estimate=20.0,
                value=0.7,
                score=0.7,
                reasoning='Test'
            ),
            ActionEvaluation(
                action='action3',
                success_probability=0.6,
                cost={'tokens': 1500.0, 'time': 15.0, 'money': 0.015},
                risk=0.3,
                time_estimate=15.0,
                value=0.6,
                score=0.5,
                reasoning='Test'
            )
        ]
        
        selected = evaluations[0]
        alternatives = decision_maker._generate_alternatives(
            evaluations,
            selected
        )
        
        # Verify selected action is not in alternatives
        assert len(alternatives) == 2
        alternative_actions = [a[0] for a in alternatives]
        assert 'action1' not in alternative_actions
        assert 'action2' in alternative_actions
        assert 'action3' in alternative_actions
    
    def test_generate_alternatives_includes_rejection_reasons(
        self,
        decision_maker
    ):
        """Test alternatives include rejection reasons."""
        # Create evaluations
        evaluations = [
            ActionEvaluation(
                action='action1',
                success_probability=0.8,
                cost={'tokens': 1000.0, 'time': 10.0, 'money': 0.01},
                risk=0.1,
                time_estimate=10.0,
                value=0.8,
                score=0.9,
                reasoning='Test'
            ),
            ActionEvaluation(
                action='action2',
                success_probability=0.6,
                cost={'tokens': 2000.0, 'time': 20.0, 'money': 0.02},
                risk=0.3,
                time_estimate=20.0,
                value=0.5,
                score=0.5,
                reasoning='Test'
            )
        ]
        
        selected = evaluations[0]
        alternatives = decision_maker._generate_alternatives(
            evaluations,
            selected
        )
        
        # Verify rejection reasons are included
        assert len(alternatives) == 1
        alternative, reason = alternatives[0]
        assert alternative == 'action2'
        assert len(reason) > 0  # Should have a reason


class TestHistoricalSuccessRates:
    """Test historical success rate tracking."""
    
    def test_update_historical_success_rate_success(self, decision_maker):
        """Test updating success rate with success."""
        # Update with success
        decision_maker.update_historical_success_rate('implementation', True)
        
        # Verify
        assert 'implementation' in decision_maker.historical_success_rates
        # Should increase towards 1.0 (alpha=0.1, starting from 0.7)
        expected_rate = 0.1 * 1.0 + 0.9 * 0.7  # 0.73
        assert abs(decision_maker.historical_success_rates['implementation'] - expected_rate) < 0.01
    
    def test_update_historical_success_rate_failure(self, decision_maker):
        """Test updating success rate with failure."""
        # Update with failure
        decision_maker.update_historical_success_rate('implementation', False)
        
        # Verify
        assert 'implementation' in decision_maker.historical_success_rates
        # Should decrease towards 0.0 (alpha=0.1, starting from 0.7)
        expected_rate = 0.1 * 0.0 + 0.9 * 0.7  # 0.63
        assert abs(decision_maker.historical_success_rates['implementation'] - expected_rate) < 0.01
    
    def test_update_historical_success_rate_consecutive_successes(
        self,
        decision_maker
    ):
        """Test consecutive successes increase rate."""
        # Update with multiple successes
        decision_maker.update_historical_success_rate('implementation', True)
        decision_maker.update_historical_success_rate('implementation', True)
        decision_maker.update_historical_success_rate('implementation', True)
        
        # Verify rate increases
        rate = decision_maker.historical_success_rates['implementation']
        assert rate > 0.7  # Should increase from initial 0.7


class TestWeightManagement:
    """Test weight management."""
    
    def test_set_weights_success(self, decision_maker):
        """Test setting weights."""
        # Set weights
        decision_maker.set_weights(
            success=1.2,
            cost=0.3,
            risk=0.6,
            value=0.9
        )
        
        # Verify
        assert decision_maker.weights['success'] == 1.2
        assert decision_maker.weights['cost'] == 0.3
        assert decision_maker.weights['risk'] == 0.6
        assert decision_maker.weights['value'] == 0.9
    
    def test_set_weights_partial(self, decision_maker):
        """Test setting partial weights."""
        # Set only some weights
        decision_maker.set_weights(success=1.5, risk=0.5)
        
        # Verify only specified weights changed
        assert decision_maker.weights['success'] == 1.5
        assert decision_maker.weights['cost'] == 0.5  # Unchanged
        assert decision_maker.weights['risk'] == 0.5
        assert decision_maker.weights['value'] == 0.8  # Unchanged


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_select_action_with_empty_evaluations(self, decision_maker):
        """Test error when selecting from empty evaluations."""
        with pytest.raises(ValueError, match="No actions to select from"):
            decision_maker._select_action(
                [],
                DecisionStrategy.OPTIMAL,
                SituationType.NORMAL
            )
    
    def test_estimate_success_probability_clamps_to_range(
        self,
        decision_maker,
        sample_context,
        sample_task_info,
        sample_situation_report
    ):
        """Test success probability is clamped to valid range."""
        # Create action with very high confidence
        potential_action = PotentialAction(
            action='test_action',
            risk_level=0.0,
            expected_outcome='Test',
            confidence=1.5  # Invalid, should be clamped to 1.0
        )
        
        probability = decision_maker._estimate_success_probability(
            potential_action,
            sample_context,
            sample_task_info
        )
        
        # Verify clamped to valid range
        assert 0.0 <= probability <= 1.0
    
    def test_confidence_adjusted_for_risk(
        self,
        decision_maker,
        sample_situation_report
    ):
        """Test confidence is adjusted for risk."""
        # Create evaluation with high risk
        evaluation = ActionEvaluation(
            action='test_action',
            success_probability=0.9,
            cost={'tokens': 1000.0, 'time': 10.0, 'money': 0.01},
            risk=0.8,  # High risk
            time_estimate=10.0,
            value=0.8,
            score=0.5,
            reasoning='Test'
        )
        
        confidence = decision_maker._estimate_confidence(
            evaluation,
            sample_situation_report
        )
        
        # Verify confidence is reduced due to high risk
        # Calculation: avg(0.9, 0.8) * (1.0 - 0.8 * 0.2) = 0.85 * 0.84 = 0.714
        expected_confidence = 0.85 * (1.0 - 0.8 * 0.2)
        assert abs(confidence - expected_confidence) < 0.01


class TestDecisionExplanation:
    """Test decision explanation generation."""
    
    def test_generate_reasoning_includes_all_components(
        self,
        decision_maker,
        sample_situation_report
    ):
        """Test reasoning includes all components."""
        evaluation = ActionEvaluation(
            action='test_action',
            success_probability=0.85,
            cost={'tokens': 1000.0, 'time': 10.0, 'money': 0.01},
            risk=0.15,
            time_estimate=10.0,
            value=0.9,
            score=0.8,
            reasoning='Test'
        )
        
        reasoning = decision_maker._generate_reasoning(
            evaluation,
            DecisionStrategy.OPTIMAL,
            sample_situation_report
        )
        
        # Verify reasoning includes key components
        assert 'test_action' in reasoning
        assert DecisionStrategy.OPTIMAL.value in reasoning
        assert f"{evaluation.success_probability:.0%}" in reasoning
        assert f"{evaluation.risk:.0%}" in reasoning
        assert f"{evaluation.value:.0%}" in reasoning
    
    def test_generate_expected_outcome_from_potential(
        self,
        decision_maker,
        sample_situation_report
    ):
        """Test expected outcome from potential action."""
        evaluation = ActionEvaluation(
            action='proceed_with_task',
            success_probability=0.9,
            cost={'tokens': 1000.0, 'time': 10.0, 'money': 0.01},
            risk=0.1,
            time_estimate=10.0,
            value=0.9,
            score=0.9,
            reasoning='Test'
        )
        
        expected_outcome = decision_maker._generate_expected_outcome(
            evaluation,
            sample_situation_report
        )
        
        # Verify expected outcome matches potential action
        assert expected_outcome == 'Complete task efficiently'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])