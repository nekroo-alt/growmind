"""
Unit tests for Context Analyzer module.

Tests context analysis, situation classification, feature extraction,
and report generation.
"""

import pytest
from unittest.mock import Mock, MagicMock
from typing import Dict, Any

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from v5.logic.context_analyzer import (
    ContextAnalyzer,
    SituationType,
    SituationFeatures,
    PotentialAction,
    SituationReport
)


class MockLLMProvider:
    """Mock LLM provider for testing."""
    
    def __init__(self):
        self.calls = []
    
    def generate(self, prompt: str, **kwargs) -> str:
        self.calls.append(prompt)
        return "Mock LLM response"


@pytest.fixture
def mock_llm_provider():
    """Create mock LLM provider."""
    return MockLLMProvider()


@pytest.fixture
def analyzer(mock_llm_provider):
    """Create ContextAnalyzer instance with mock LLM provider."""
    return ContextAnalyzer(mock_llm_provider)


class TestContextAnalyzerInitialization:
    """Test ContextAnalyzer initialization."""
    
    def test_initialization(self, mock_llm_provider):
        """Test that ContextAnalyzer initializes correctly."""
        analyzer = ContextAnalyzer(mock_llm_provider)
        
        assert analyzer.llm_provider is not None
        assert analyzer.logger is not None


class TestFeatureExtraction:
    """Test feature extraction from context."""
    
    def test_extract_features_normal_context(self, analyzer):
        """Test feature extraction from normal context."""
        context = {
            'recent_errors': [],
            'recent_actions': [
                {'status': 'success'},
                {'status': 'success'},
                {'status': 'success'}
            ],
            'resources': {
                'tokens_available': 80.0,
                'time_available': 90.0,
                'compute_available': 85.0
            },
            'time_pressure': 0.2,
            'context_completeness': 0.9
        }
        
        task_info = {
            'complexity': 0.5,
            'dependency_count': 3
        }
        
        features = analyzer._extract_features(context, task_info)
        
        assert features.error_frequency == 0.0
        assert features.error_types == []
        assert features.task_complexity == 0.5
        assert features.dependency_count == 3
        assert features.recent_successes == 3
        assert features.recent_failures == 0
        assert features.time_pressure == 0.2
        assert features.context_completeness == 0.9
        assert features.resource_availability['tokens'] == 0.8
        assert features.resource_availability['time'] == 0.9
        assert features.resource_availability['compute'] == 0.85
    
    def test_extract_features_error_context(self, analyzer):
        """Test feature extraction from error context."""
        context = {
            'recent_errors': [
                {'severity': 'error', 'type': 'timeout'},
                {'severity': 'error', 'type': 'permission'},
                {'severity': 'error', 'type': 'timeout'},
                {'severity': 'error', 'type': 'timeout'}
            ],
            'recent_actions': [
                {'status': 'failure'},
                {'status': 'failure'}
            ],
            'resources': {
                'tokens_available': 30.0,
                'time_available': 40.0,
                'compute_available': 35.0
            },
            'time_pressure': 0.8,
            'context_completeness': 0.4
        }
        
        task_info = {
            'complexity': 0.9,
            'dependency_count': 7
        }
        
        features = analyzer._extract_features(context, task_info)
        
        assert features.error_frequency > 0.5
        assert set(features.error_types) == {'timeout', 'permission'}
        assert features.task_complexity == 0.9
        assert features.dependency_count == 7
        assert features.recent_failures == 4
        assert features.recent_successes == 0
        assert features.time_pressure == 0.8
        assert features.context_completeness == 0.4
    
    def test_extract_features_with_inferred_error_types(self, analyzer):
        """Test feature extraction with inferred error types."""
        context = {
            'recent_errors': [
                {'message': 'Connection timeout after 30s'},
                {'message': 'Permission denied: Access forbidden'},
                {'message': 'File not found: config.json'}
            ],
            'recent_actions': [],
            'resources': {},
            'context_completeness': 0.8
        }
        
        features = analyzer._extract_features(context, None)
        
        error_types_set = set(features.error_types)
        assert 'timeout' in error_types_set
        assert 'permission' in error_types_set
        assert 'not_found' in error_types_set
    
    def test_extract_features_with_message_errors(self, analyzer):
        """Test feature extraction when errors only have messages."""
        context = {
            'recent_errors': [
                {'message': 'Rate limit exceeded'},
                {'message': 'Syntax error in line 42'}
            ],
            'recent_actions': [],
            'resources': {},
            'context_completeness': 0.8
        }
        
        features = analyzer._extract_features(context, None)
        
        # Should infer error types from messages
        assert len(features.error_types) > 0


class TestSituationClassification:
    """Test situation type classification."""
    
    def test_classify_error_situation(self, analyzer):
        """Test classification of error situation."""
        features = SituationFeatures(
            error_frequency=0.7,
            recent_failures=4,
            task_complexity=0.5,
            context_completeness=0.8
        )
        
        situation = analyzer._classify_situation(features)
        
        assert situation == SituationType.ERROR
    
    def test_classify_complex_situation(self, analyzer):
        """Test classification of complex situation."""
        features = SituationFeatures(
            task_complexity=0.9,
            dependency_count=6,
            error_frequency=0.1,
            recent_failures=0,
            context_completeness=0.8
        )
        
        situation = analyzer._classify_situation(features)
        
        assert situation == SituationType.COMPLEX
    
    def test_classify_blocked_situation(self, analyzer):
        """Test classification of blocked situation."""
        features = SituationFeatures(
            context_completeness=0.3,
            dependency_count=2,
            recent_successes=0,
            recent_failures=0,
            error_frequency=0.1
        )
        
        situation = analyzer._classify_situation(features)
        
        assert situation == SituationType.BLOCKED
    
    def test_classify_uncertain_situation(self, analyzer):
        """Test classification of uncertain situation."""
        features = SituationFeatures(
            context_completeness=0.7,
            error_types=['timeout', 'permission', 'not_found'],
            recent_successes=1,
            recent_failures=1,
            error_frequency=0.2
        )
        
        situation = analyzer._classify_situation(features)
        
        assert situation == SituationType.UNCERTAIN
    
    def test_classify_normal_situation(self, analyzer):
        """Test classification of normal situation."""
        features = SituationFeatures(
            error_frequency=0.1,
            recent_failures=0,
            recent_successes=5,
            task_complexity=0.4,
            dependency_count=2,
            context_completeness=0.9,
            error_types=[]
        )
        
        situation = analyzer._classify_situation(features)
        
        assert situation == SituationType.NORMAL


class TestPotentialActionsIdentification:
    """Test identification of potential actions."""
    
    def test_identify_actions_for_error_situation(self, analyzer):
        """Test action identification for error situation."""
        context = {}
        features = SituationFeatures(error_frequency=0.6, recent_failures=3)
        situation_type = SituationType.ERROR
        
        actions = analyzer._identify_potential_actions(context, features, situation_type)
        
        assert len(actions) > 0
        assert any('retry' in a.action for a in actions)
        assert any('error' in a.action for a in actions)
        assert all(0.0 <= a.risk_level <= 1.0 for a in actions)
        assert all(0.0 <= a.confidence <= 1.0 for a in actions)
    
    def test_identify_actions_for_blocked_situation(self, analyzer):
        """Test action identification for blocked situation."""
        context = {}
        features = SituationFeatures(context_completeness=0.3, dependency_count=4)
        situation_type = SituationType.BLOCKED
        
        actions = analyzer._identify_potential_actions(context, features, situation_type)
        
        assert len(actions) > 0
        assert any('expand' in a.action for a in actions)
        assert any('break' in a.action for a in actions)
    
    def test_identify_actions_for_complex_situation(self, analyzer):
        """Test action identification for complex situation."""
        context = {}
        features = SituationFeatures(task_complexity=0.9, dependency_count=6)
        situation_type = SituationType.COMPLEX
        
        actions = analyzer._identify_potential_actions(context, features, situation_type)
        
        assert len(actions) > 0
        assert any('subtask' in a.action or 'subtask' in a.expected_outcome.lower() for a in actions)
        assert any('conservative' in a.action for a in actions)
    
    def test_identify_actions_for_uncertain_situation(self, analyzer):
        """Test action identification for uncertain situation."""
        context = {}
        features = SituationFeatures(context_completeness=0.5)
        situation_type = SituationType.UNCERTAIN
        
        actions = analyzer._identify_potential_actions(context, features, situation_type)
        
        assert len(actions) > 0
        assert any('context' in a.action or 'context' in a.expected_outcome.lower() for a in actions)
    
    def test_identify_actions_for_normal_situation(self, analyzer):
        """Test action identification for normal situation."""
        context = {}
        features = SituationFeatures(error_frequency=0.1, recent_successes=5)
        situation_type = SituationType.NORMAL
        
        actions = analyzer._identify_potential_actions(context, features, situation_type)
        
        assert len(actions) > 0
        assert any('proceed' in a.action for a in actions)
        assert any('optimal' in a.action for a in actions)


class TestConfidenceEstimation:
    """Test confidence estimation."""
    
    def test_estimate_confidence_high(self, analyzer):
        """Test confidence estimation with high quality context."""
        features = SituationFeatures(
            context_completeness=0.9,
            resource_availability={'tokens': 0.9, 'time': 0.9, 'compute': 0.9},
            recent_successes=5,
            recent_failures=0
        )
        actions = [
            PotentialAction(action='test', risk_level=0.1, expected_outcome='ok', confidence=0.9)
        ]
        
        confidence = analyzer._estimate_confidence(features, actions)
        
        assert confidence > 0.8
    
    def test_estimate_confidence_low(self, analyzer):
        """Test confidence estimation with low quality context."""
        features = SituationFeatures(
            context_completeness=0.3,
            resource_availability={'tokens': 0.3, 'time': 0.3, 'compute': 0.3},
            recent_successes=0,
            recent_failures=5
        )
        actions = [
            PotentialAction(action='test', risk_level=0.7, expected_outcome='ok', confidence=0.4)
        ]
        
        confidence = analyzer._estimate_confidence(features, actions)
        
        assert confidence < 0.6
    
    def test_estimate_confidence_no_actions(self, analyzer):
        """Test confidence estimation when no actions available."""
        features = SituationFeatures(
            context_completeness=0.7,
            resource_availability={'tokens': 0.8, 'time': 0.8, 'compute': 0.8},
            recent_successes=3,
            recent_failures=1
        )
        
        confidence = analyzer._estimate_confidence(features, [])
        
        # Should still calculate confidence from other factors
        assert 0.0 <= confidence <= 1.0


class TestRecommendationGeneration:
    """Test recommendation generation."""
    
    def test_generate_recommendations_for_error(self, analyzer):
        """Test recommendations for error situation."""
        features = SituationFeatures(error_frequency=0.7, recent_failures=4)
        actions = [PotentialAction(action='retry', risk_level=0.2, expected_outcome='ok', confidence=0.8)]
        
        recommendations = analyzer._generate_recommendations(
            SituationType.ERROR, features, actions
        )
        
        assert len(recommendations) > 0
        assert any('error' in r.lower() for r in recommendations)
        assert any('pattern' in r.lower() for r in recommendations)
    
    def test_generate_recommendations_for_blocked(self, analyzer):
        """Test recommendations for blocked situation."""
        features = SituationFeatures(context_completeness=0.3, dependency_count=6)
        actions = [PotentialAction(action='expand', risk_level=0.3, expected_outcome='ok', confidence=0.6)]
        
        recommendations = analyzer._generate_recommendations(
            SituationType.BLOCKED, features, actions
        )
        
        assert len(recommendations) > 0
        assert any('expand' in r.lower() or 'context' in r.lower() for r in recommendations)
        assert any('break' in r.lower() for r in recommendations)
    
    def test_generate_recommendations_for_complex(self, analyzer):
        """Test recommendations for complex situation."""
        features = SituationFeatures(task_complexity=0.9, dependency_count=7)
        actions = [PotentialAction(action='subtask', risk_level=0.2, expected_outcome='ok', confidence=0.8)]
        
        recommendations = analyzer._generate_recommendations(
            SituationType.COMPLEX, features, actions
        )
        
        assert len(recommendations) > 0
        assert any('conservative' in r.lower() for r in recommendations)
    
    def test_generate_recommendations_for_uncertain(self, analyzer):
        """Test recommendations for uncertain situation."""
        features = SituationFeatures(context_completeness=0.4)
        actions = [PotentialAction(action='gather', risk_level=0.1, expected_outcome='ok', confidence=0.8)]
        
        recommendations = analyzer._generate_recommendations(
            SituationType.UNCERTAIN, features, actions
        )
        
        assert len(recommendations) > 0
        assert any('context' in r.lower() or 'gather' in r.lower() for r in recommendations)
    
    def test_generate_recommendations_for_normal(self, analyzer):
        """Test recommendations for normal situation."""
        features = SituationFeatures(error_frequency=0.1, recent_successes=5)
        actions = [PotentialAction(action='proceed', risk_level=0.1, expected_outcome='ok', confidence=0.9)]
        
        recommendations = analyzer._generate_recommendations(
            SituationType.NORMAL, features, actions
        )
        
        assert len(recommendations) > 0
        assert any('proceed' in r.lower() for r in recommendations)


class TestReasoningGeneration:
    """Test reasoning generation."""
    
    def test_generate_reasoning_for_error(self, analyzer):
        """Test reasoning generation for error situation."""
        features = SituationFeatures(
            error_frequency=0.7,
            recent_failures=4,
            error_types=['timeout', 'permission']
        )
        
        reasoning = analyzer._generate_reasoning(
            SituationType.ERROR, features, []
        )
        
        assert 'error' in reasoning.lower()
        assert 'frequency' in reasoning.lower()
        assert 'failures' in reasoning.lower()
    
    def test_generate_reasoning_for_blocked(self, analyzer):
        """Test reasoning generation for blocked situation."""
        features = SituationFeatures(
            context_completeness=0.3,
            dependency_count=6,
            recent_successes=0
        )
        
        reasoning = analyzer._generate_reasoning(
            SituationType.BLOCKED, features, []
        )
        
        assert 'context' in reasoning.lower()
        assert 'completeness' in reasoning.lower()
        assert 'dependencies' in reasoning.lower()
    
    def test_generate_reasoning_for_complex(self, analyzer):
        """Test reasoning generation for complex situation."""
        features = SituationFeatures(
            task_complexity=0.9,
            dependency_count=7,
            resource_availability={'tokens': 0.6, 'time': 0.6, 'compute': 0.6}
        )
        
        reasoning = analyzer._generate_reasoning(
            SituationType.COMPLEX, features, []
        )
        
        assert 'complexity' in reasoning.lower()
        assert 'dependencies' in reasoning.lower()
        assert 'resource' in reasoning.lower()
    
    def test_generate_reasoning_for_normal(self, analyzer):
        """Test reasoning generation for normal situation."""
        features = SituationFeatures(
            error_frequency=0.1,
            context_completeness=0.9,
            recent_successes=5
        )
        
        reasoning = analyzer._generate_reasoning(
            SituationType.NORMAL, features, []
        )
        
        assert 'error frequency' in reasoning.lower()
        assert 'context completeness' in reasoning.lower()
        assert 'successes' in reasoning.lower()


class TestIntegrationAnalyzeSituation:
    """Integration tests for analyze_situation method."""
    
    def test_analyze_situation_normal(self, analyzer):
        """Test complete situation analysis for normal scenario."""
        context = {
            'recent_errors': [],
            'recent_actions': [
                {'status': 'success'},
                {'status': 'success'}
            ],
            'resources': {
                'tokens_available': 80.0,
                'time_available': 90.0,
                'compute_available': 85.0
            },
            'time_pressure': 0.2,
            'context_completeness': 0.9
        }
        
        task_info = {
            'complexity': 0.4,
            'dependency_count': 2
        }
        
        report = analyzer.analyze_situation(context, task_info)
        
        assert isinstance(report, SituationReport)
        assert report.situation_type == SituationType.NORMAL
        assert report.confidence > 0.7
        assert len(report.potential_actions) > 0
        assert len(report.recommendations) > 0
        assert len(report.reasoning) > 0
        assert isinstance(report.features, SituationFeatures)
    
    def test_analyze_situation_error(self, analyzer):
        """Test complete situation analysis for error scenario."""
        context = {
            'recent_errors': [
                {'severity': 'error', 'type': 'timeout'},
                {'severity': 'error', 'type': 'timeout'},
                {'severity': 'error', 'type': 'timeout'},
                {'severity': 'error', 'type': 'timeout'}
            ],
            'recent_actions': [
                {'status': 'failure'},
                {'status': 'failure'}
            ],
            'resources': {
                'tokens_available': 30.0,
                'time_available': 40.0,
                'compute_available': 35.0
            },
            'time_pressure': 0.8,
            'context_completeness': 0.5
        }
        
        task_info = {
            'complexity': 0.6,
            'dependency_count': 4
        }
        
        report = analyzer.analyze_situation(context, task_info)
        
        assert isinstance(report, SituationReport)
        assert report.situation_type == SituationType.ERROR
        assert report.features.recent_failures >= 3
        assert report.features.error_frequency > 0.5
        assert len(report.potential_actions) > 0
        assert len(report.recommendations) > 0
    
    def test_analyze_situation_complex(self, analyzer):
        """Test complete situation analysis for complex scenario."""
        context = {
            'recent_errors': [],
            'recent_actions': [{'status': 'success'}],
            'resources': {
                'tokens_available': 60.0,
                'time_available': 70.0,
                'compute_available': 65.0
            },
            'time_pressure': 0.5,
            'context_completeness': 0.7
        }
        
        task_info = {
            'complexity': 0.9,
            'dependency_count': 7
        }
        
        report = analyzer.analyze_situation(context, task_info)
        
        assert isinstance(report, SituationReport)
        assert report.situation_type == SituationType.COMPLEX
        assert report.features.task_complexity == 0.9
        assert report.features.dependency_count == 7
    
    def test_analyze_situation_without_task_info(self, analyzer):
        """Test situation analysis without task information."""
        context = {
            'recent_errors': [],
            'recent_actions': [
                {'status': 'success'},
                {'status': 'success'}
            ],
            'resources': {
                'tokens_available': 80.0,
                'time_available': 90.0,
                'compute_available': 85.0
            },
            'time_pressure': 0.2,
            'context_completeness': 0.9
        }
        
        report = analyzer.analyze_situation(context, None)
        
        assert isinstance(report, SituationReport)
        assert report.features.task_complexity == 0.0
        assert report.features.dependency_count == 0
        # Should still classify based on available information
        assert report.situation_type in SituationType


class TestHelperMethods:
    """Test helper methods."""
    
    def test_infer_error_type_timeout(self, analyzer):
        """Test error type inference for timeout."""
        assert analyzer._infer_error_type('Connection timeout') == 'timeout'
        assert analyzer._infer_error_type('Rate limit exceeded') == 'timeout'
    
    def test_infer_error_type_permission(self, analyzer):
        """Test error type inference for permission."""
        assert analyzer._infer_error_type('Permission denied') == 'permission'
        assert analyzer._infer_error_type('Access forbidden') == 'permission'
    
    def test_infer_error_type_not_found(self, analyzer):
        """Test error type inference for not found."""
        assert analyzer._infer_error_type('File not found') == 'not_found'
        assert analyzer._infer_error_type('Missing file') == 'not_found'
    
    def test_infer_error_type_syntax(self, analyzer):
        """Test error type inference for syntax."""
        assert analyzer._infer_error_type('Syntax error') == 'syntax_error'
        assert analyzer._infer_error_type('Parse error') == 'syntax_error'
    
    def test_normalize_resource(self, analyzer):
        """Test resource normalization."""
        assert analyzer._normalize_resource(50, 100) == 0.5
        assert analyzer._normalize_resource(80, 100) == 0.8
        assert analyzer._normalize_resource(150, 100) == 1.0  # Max out at 1.0
        assert analyzer._normalize_resource(-10, 100) == 0.0  # Min out at 0.0
    
    def test_avg_resource(self, analyzer):
        """Test average resource calculation."""
        resources = {'tokens': 0.8, 'time': 0.9, 'compute': 0.7}
        avg = analyzer._avg_resource(resources)
        assert abs(avg - 0.8) < 0.01  # (0.8 + 0.9 + 0.7) / 3 = 0.8
    
    def test_success_rate(self, analyzer):
        """Test success rate calculation."""
        features = SituationFeatures(recent_successes=7, recent_failures=3)
        rate = analyzer._success_rate(features)
        assert abs(rate - 0.7) < 0.01  # 7 / 10 = 0.7
    
    def test_success_rate_no_data(self, analyzer):
        """Test success rate with no data."""
        features = SituationFeatures(recent_successes=0, recent_failures=0)
        rate = analyzer._success_rate(features)
        assert rate == 1.0  # Assume success if no data


if __name__ == '__main__':
    pytest.main([__file__, '-v'])