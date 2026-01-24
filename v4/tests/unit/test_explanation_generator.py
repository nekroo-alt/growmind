"""
Unit tests for Explanation Generator Module

Tests the natural language explanation generation for decisions.
"""

import pytest
import time
from logic.explanation_generator import (
    ExplanationGenerator,
    ExplanationFormat,
    AudienceType,
    Explanation,
    get_explanation_generator
)


class TestExplanationFormat:
    """Test explanation format enum."""
    
    def test_brief_format_exists(self):
        """Test that BRIEF format exists."""
        assert ExplanationFormat.BRIEF.value == "brief"
    
    def test_detailed_format_exists(self):
        """Test that DETAILED format exists."""
        assert ExplanationFormat.DETAILED.value == "detailed"
    
    def test_technical_format_exists(self):
        """Test that TECHNICAL format exists."""
        assert ExplanationFormat.TECHNICAL.value == "technical"


class TestAudienceType:
    """Test audience type enum."""
    
    def test_developer_audience_exists(self):
        """Test that DEVELOPER audience exists."""
        assert AudienceType.DEVELOPER.value == "developer"
    
    def test_manager_audience_exists(self):
        """Test that MANAGER audience exists."""
        assert AudienceType.MANAGER.value == "manager"
    
    def test_user_audience_exists(self):
        """Test that USER audience exists."""
        assert AudienceType.USER.value == "user"


class TestExplanation:
    """Test explanation dataclass."""
    
    def test_explanation_creation(self):
        """Test creating an explanation object."""
        explanation = Explanation(
            decision_id="test-123",
            format=ExplanationFormat.DETAILED,
            audience=AudienceType.DEVELOPER,
            explanation="Test explanation"
        )
        
        assert explanation.decision_id == "test-123"
        assert explanation.format == ExplanationFormat.DETAILED
        assert explanation.audience == AudienceType.DEVELOPER
        assert explanation.explanation == "Test explanation"
        assert explanation.reasoning_steps == []
        assert explanation.alternatives_considered == []
        assert explanation.confidence is None
        assert explanation.uncertainty is None
        assert explanation.expected_outcome is None
    
    def test_explanation_with_all_fields(self):
        """Test creating explanation with all fields."""
        reasoning_steps = [
            {'step': 1, 'thought': 'Analyze', 'conclusion': 'Ready'}
        ]
        alternatives = [
            {'action': 'Alternative A', 'reason_for_rejection': 'Too risky'}
        ]
        
        explanation = Explanation(
            decision_id="test-456",
            format=ExplanationFormat.TECHNICAL,
            audience=AudienceType.MANAGER,
            explanation="Technical explanation",
            reasoning_steps=reasoning_steps,
            alternatives_considered=alternatives,
            confidence=0.85,
            uncertainty="Moderate confidence",
            expected_outcome="Success",
            timestamp=1234567890.0
        )
        
        assert explanation.decision_id == "test-456"
        assert explanation.format == ExplanationFormat.TECHNICAL
        assert explanation.audience == AudienceType.MANAGER
        assert explanation.reasoning_steps == reasoning_steps
        assert explanation.alternatives_considered == alternatives
        assert explanation.confidence == 0.85
        assert explanation.uncertainty == "Moderate confidence"
        assert explanation.expected_outcome == "Success"
        assert explanation.timestamp == 1234567890.0


class TestExplanationGenerator:
    """Test explanation generator functionality."""
    
    def test_generator_initialization(self):
        """Test generator initialization."""
        generator = ExplanationGenerator()
        
        assert generator.explanation_cache == {}
        assert generator.templates is not None
        assert len(generator.templates) > 0
    
    def test_generate_brief_explanation(self):
        """Test generating a brief explanation."""
        generator = ExplanationGenerator()
        
        decision_data = {
            'decision_id': 'test-001',
            'action': 'implement feature X',
            'reason': 'it meets requirements',
            'goal': 'complete the task'
        }
        
        explanation = generator.generate_brief(decision_data)
        
        assert explanation.decision_id == 'test-001'
        assert explanation.format == ExplanationFormat.BRIEF
        assert len(explanation.explanation) > 0
        assert explanation.reasoning_steps == []
        assert explanation.alternatives_considered == []
    
    def test_generate_detailed_explanation(self):
        """Test generating a detailed explanation."""
        generator = ExplanationGenerator()
        
        decision_data = {
            'decision_id': 'test-002',
            'action': 'refactor module Y',
            'reasoning': 'code is becoming complex',
            'goal': 'improve maintainability',
            'situation': 'high complexity detected',
            'success_probability': '80%',
            'cost': 'low',
            'risk': 'low',
            'confidence': 0.8
        }
        
        explanation = generator.generate_detailed(decision_data)
        
        assert explanation.decision_id == 'test-002'
        assert explanation.format == ExplanationFormat.DETAILED
        assert len(explanation.explanation) > 0
        assert explanation.confidence == 0.8
        assert explanation.uncertainty is not None
    
    def test_generate_technical_explanation(self):
        """Test generating a technical explanation."""
        generator = ExplanationGenerator()
        
        decision_data = {
            'decision_id': 'test-003',
            'action': 'add caching layer',
            'reasoning': 'performance bottleneck',
            'goal': 'improve response time',
            'situation_type': 'performance issue',
            'success_probability': '90%',
            'cost': 'moderate',
            'risk': 'low',
            'time_to_complete': '2 hours',
            'efficiency': 'high',
            'confidence': 0.9,
            'expected_outcome': '3x performance improvement'
        }
        
        explanation = generator.generate_technical(decision_data)
        
        assert explanation.decision_id == 'test-003'
        assert explanation.format == ExplanationFormat.TECHNICAL
        assert len(explanation.explanation) > 0
        assert 'Decision Analysis' in explanation.explanation
        assert explanation.confidence == 0.9
    
    def test_generate_for_developer_audience(self):
        """Test generating explanation for developer audience."""
        generator = ExplanationGenerator()
        
        decision_data = {
            'decision_id': 'test-004',
            'action': 'fix bug in authentication',
            'reason': 'security vulnerability',
            'goal': 'secure the application'
        }
        
        explanation = generator.generate_explanation(
            decision_data,
            audience=AudienceType.DEVELOPER
        )
        
        assert explanation.audience == AudienceType.DEVELOPER
        assert 'fix bug' in explanation.explanation.lower() or 'security' in explanation.explanation.lower()
    
    def test_generate_for_manager_audience(self):
        """Test generating explanation for manager audience."""
        generator = ExplanationGenerator()
        
        decision_data = {
            'decision_id': 'test-005',
            'action': 'allocate more resources',
            'goal': 'meet deadline'
        }
        
        explanation = generator.generate_explanation(
            decision_data,
            audience=AudienceType.MANAGER
        )
        
        assert explanation.audience == AudienceType.MANAGER
        assert len(explanation.explanation) > 0
    
    def test_generate_for_user_audience(self):
        """Test generating explanation for user audience."""
        generator = ExplanationGenerator()
        
        decision_data = {
            'decision_id': 'test-006',
            'action': 'simplify interface',
            'goal': 'improve usability'
        }
        
        explanation = generator.generate_explanation(
            decision_data,
            audience=AudienceType.USER
        )
        
        assert explanation.audience == AudienceType.USER
        assert len(explanation.explanation) > 0
    
    def test_explanation_with_reasoning_chain(self):
        """Test explanation with reasoning chain."""
        generator = ExplanationGenerator()
        
        reasoning_chain = [
            {'step': 1, 'thought': 'Analyze current state', 'conclusion': 'Need improvement'},
            {'step': 2, 'thought': 'Evaluate options', 'conclusion': 'Option A is best'}
        ]
        
        decision_data = {
            'decision_id': 'test-007',
            'action': 'optimize database',
            'reasoning_chain': reasoning_chain
        }
        
        explanation = generator.generate_detailed(decision_data)
        
        assert len(explanation.reasoning_steps) == 2
        assert explanation.reasoning_steps[0]['step'] == 1
        assert 'Analyze current state' in explanation.reasoning_steps[0]['thought']
    
    def test_explanation_with_alternatives(self):
        """Test explanation with alternatives considered."""
        generator = ExplanationGenerator()
        
        alternatives = [
            {'action': 'Option A', 'reason_for_rejection': 'Too expensive'},
            {'action': 'Option B', 'reason_for_rejection': 'Too slow'}
        ]
        
        decision_data = {
            'decision_id': 'test-008',
            'action': 'Option C',
            'alternatives': alternatives
        }
        
        explanation = generator.generate_detailed(decision_data)
        
        assert len(explanation.alternatives_considered) == 2
        assert explanation.alternatives_considered[0]['action'] == 'Option A'
        assert 'Too expensive' in explanation.alternatives_considered[0]['reason_for_rejection']
    
    def test_explanation_with_context(self):
        """Test explanation with context information."""
        generator = ExplanationGenerator()
        
        context = {
            'current_action': 'implementing feature',
            'recent_errors': ['timeout', 'connection failed'],
            'task_progress': '50%',
            'constraints': ['time limit', 'memory limit']
        }
        
        decision_data = {
            'decision_id': 'test-009',
            'action': 'retry with backoff',
            'context': context
        }
        
        explanation = generator.generate_detailed(decision_data)
        
        assert len(explanation.explanation) > 0
        # Context should be summarized and included
    
    def test_uncertainty_explanation_high_confidence(self):
        """Test uncertainty explanation for high confidence."""
        generator = ExplanationGenerator()
        
        decision_data = {
            'decision_id': 'test-010',
            'action': 'proceed with plan',
            'confidence': 0.95
        }
        
        explanation = generator.generate_detailed(decision_data)
        
        assert explanation.uncertainty is not None
        assert 'high' in explanation.uncertainty.lower()
    
    def test_uncertainty_explanation_low_confidence(self):
        """Test uncertainty explanation for low confidence."""
        generator = ExplanationGenerator()
        
        decision_data = {
            'decision_id': 'test-011',
            'action': 'cautious approach',
            'confidence': 0.4
        }
        
        explanation = generator.generate_detailed(decision_data)
        
        assert explanation.uncertainty is not None
        assert 'low' in explanation.uncertainty.lower()
    
    def test_expected_outcome(self):
        """Test expected outcome in explanation."""
        generator = ExplanationGenerator()
        
        decision_data = {
            'decision_id': 'test-012',
            'action': 'implement caching',
            'expected_outcome': 'reduce load time by 50%'
        }
        
        explanation = generator.generate_detailed(decision_data)
        
        assert explanation.expected_outcome == 'reduce load time by 50%'
    
    def test_explanation_caching(self):
        """Test that explanations are cached."""
        generator = ExplanationGenerator()
        
        decision_data = {
            'decision_id': 'test-013',
            'action': 'test action',
            'reason': 'test reason'
        }
        
        # Generate explanation
        explanation1 = generator.generate_brief(decision_data)
        
        # Retrieve from cache
        explanation2 = generator.get_cached_explanation(
            'test-013',
            format=ExplanationFormat.BRIEF,
            audience=AudienceType.DEVELOPER
        )
        
        assert explanation2 is not None
        assert explanation2.decision_id == 'test-013'
        assert explanation2.explanation == explanation1.explanation
    
    def test_clear_cache(self):
        """Test clearing explanation cache."""
        generator = ExplanationGenerator()
        
        decision_data = {
            'decision_id': 'test-014',
            'action': 'test action'
        }
        
        # Generate and cache explanation
        generator.generate_brief(decision_data)
        assert len(generator.explanation_cache) > 0
        
        # Clear cache
        generator.clear_cache()
        assert len(generator.explanation_cache) == 0
    
    def test_export_explanation(self):
        """Test exporting explanation to dictionary."""
        generator = ExplanationGenerator()
        
        decision_data = {
            'decision_id': 'test-015',
            'action': 'test action',
            'confidence': 0.75
        }
        
        explanation = generator.generate_detailed(decision_data)
        exported = generator.export_explanation(explanation)
        
        assert exported['decision_id'] == 'test-015'
        assert exported['format'] == 'detailed'
        assert exported['audience'] == 'developer'
        assert exported['confidence'] == 0.75
        assert 'explanation' in exported
        assert 'reasoning_steps' in exported
        assert 'alternatives_considered' in exported
    
    def test_validate_valid_explanation(self):
        """Test validation of valid explanation."""
        generator = ExplanationGenerator()
        
        decision_data = {
            'decision_id': 'test-016',
            'action': 'test action',
            'reason': 'test reason'
        }
        
        explanation = generator.generate_detailed(decision_data)
        is_valid = generator.validate_explanation(explanation)
        
        assert is_valid is True
    
    def test_validate_missing_decision_id(self):
        """Test validation fails without decision_id."""
        generator = ExplanationGenerator()
        
        explanation = Explanation(
            decision_id='',
            format=ExplanationFormat.DETAILED,
            audience=AudienceType.DEVELOPER,
            explanation='Test explanation'
        )
        
        is_valid = generator.validate_explanation(explanation)
        assert is_valid is False
    
    def test_validate_missing_explanation_text(self):
        """Test validation fails without explanation text."""
        generator = ExplanationGenerator()
        
        explanation = Explanation(
            decision_id='test-017',
            format=ExplanationFormat.DETAILED,
            audience=AudienceType.DEVELOPER,
            explanation=''
        )
        
        is_valid = generator.validate_explanation(explanation)
        assert is_valid is False
    
    def test_validate_too_short_explanation(self):
        """Test validation fails for too short explanation."""
        generator = ExplanationGenerator()
        
        explanation = Explanation(
            decision_id='test-018',
            format=ExplanationFormat.DETAILED,
            audience=AudienceType.DEVELOPER,
            explanation='Too short'
        )
        
        is_valid = generator.validate_explanation(explanation)
        assert is_valid is False
    
    def test_validate_too_long_explanation(self):
        """Test validation fails for too long explanation."""
        generator = ExplanationGenerator()
        
        explanation = Explanation(
            decision_id='test-019',
            format=ExplanationFormat.DETAILED,
            audience=AudienceType.DEVELOPER,
            explanation='x' * 2500  # Over 2000 char limit
        )
        
        is_valid = generator.validate_explanation(explanation)
        assert is_valid is False
    
    def test_validate_detailed_without_reasoning_steps(self):
        """Test validation fails for detailed format without reasoning steps."""
        generator = ExplanationGenerator()
        
        explanation = Explanation(
            decision_id='test-020',
            format=ExplanationFormat.DETAILED,
            audience=AudienceType.DEVELOPER,
            explanation='A detailed explanation without reasoning steps',
            reasoning_steps=[]
        )
        
        is_valid = generator.validate_explanation(explanation)
        assert is_valid is False
    
    def test_fallback_on_error(self):
        """Test fallback explanation on generation error."""
        generator = ExplanationGenerator()
        
        # Create invalid decision data that might cause errors
        decision_data = {
            'decision_id': 'test-021',
            # Missing action to test fallback
        }
        
        explanation = generator.generate_brief(decision_data)
        
        # Should still generate a fallback explanation
        assert explanation.decision_id == 'test-021'
        assert len(explanation.explanation) > 0


class TestExplanationGeneratorTemplates:
    """Test explanation templates for different formats and audiences."""
    
    def test_brief_developer_template(self):
        """Test brief format for developer audience."""
        generator = ExplanationGenerator()
        
        decision_data = {
            'decision_id': 'test-022',
            'action': 'implement X',
            'reason': 'meets requirements'
        }
        
        explanation = generator.generate_explanation(
            decision_data,
            format=ExplanationFormat.BRIEF,
            audience=AudienceType.DEVELOPER
        )
        
        assert 'I chose to' in explanation.explanation
        assert 'implement X' in explanation.explanation
        assert 'because' in explanation.explanation
    
    def test_detailed_developer_template(self):
        """Test detailed format for developer audience."""
        generator = ExplanationGenerator()
        
        decision_data = {
            'decision_id': 'test-023',
            'action': 'implement X',
            'situation': 'requirement identified',
            'success_probability': '85%',
            'efficiency': 'high',
            'risk': 'low',
            'confidence': 0.85,
            'expected_outcome': 'feature completed'
        }
        
        explanation = generator.generate_explanation(
            decision_data,
            format=ExplanationFormat.DETAILED,
            audience=AudienceType.DEVELOPER
        )
        
        assert 'After analyzing' in explanation.explanation
        assert 'success probability' in explanation.explanation.lower()
        assert 'risk' in explanation.explanation.lower()
        assert 'expected to' in explanation.explanation.lower()
    
    def test_technical_developer_template(self):
        """Test technical format for developer audience."""
        generator = ExplanationGenerator()
        
        decision_data = {
            'decision_id': 'test-024',
            'action': 'implement X',
            'situation_type': 'normal',
            'num_alternatives': 3,
            'success_probability': '90%',
            'cost': '1000 tokens',
            'risk': 'low',
            'time_to_complete': '1 hour',
            'confidence': 0.9,
            'reasoning': 'optimal choice',
            'expected_outcome': 'success',
            'context': {'current_action': 'implementing'}
        }
        
        explanation = generator.generate_explanation(
            decision_data,
            format=ExplanationFormat.TECHNICAL,
            audience=AudienceType.DEVELOPER
        )
        
        assert 'Decision Analysis' in explanation.explanation
        assert 'Context:' in explanation.explanation
        assert 'Success Probability:' in explanation.explanation
        assert 'Cost' in explanation.explanation
        assert 'Risk Level:' in explanation.explanation
    
    def test_manager_audience_explanations(self):
        """Test explanations tailored for manager audience."""
        generator = ExplanationGenerator()
        
        decision_data = {
            'decision_id': 'test-025',
            'action': 'allocate resources',
            'goal': 'complete project',
            'situation': 'deadline approaching',
            'confidence': 0.8
        }
        
        explanation = generator.generate_explanation(
            decision_data,
            format=ExplanationFormat.DETAILED,
            audience=AudienceType.MANAGER
        )
        
        # Manager audience should see business-focused language
        assert 'optimal balance' in explanation.explanation.lower()
        assert 'effectiveness' in explanation.explanation.lower()
    
    def test_user_audience_explanations(self):
        """Test explanations tailored for user audience."""
        generator = ExplanationGenerator()
        
        decision_data = {
            'decision_id': 'test-026',
            'action': 'simplify UI',
            'goal': 'make it easier to use',
            'situation': 'user feedback',
            'confidence': 0.75
        }
        
        explanation = generator.generate_explanation(
            decision_data,
            format=ExplanationFormat.DETAILED,
            audience=AudienceType.USER
        )
        
        # User audience should see simple, helpful language
        assert 'I noticed' in explanation.explanation or 'chose' in explanation.explanation.lower()
        assert 'help you' in explanation.explanation.lower()


class TestSingletonInstance:
    """Test global singleton instance."""
    
    def test_get_explanation_generator_singleton(self):
        """Test that get_explanation_generator returns singleton."""
        generator1 = get_explanation_generator()
        generator2 = get_explanation_generator()
        
        assert generator1 is generator2
    
    def test_singleton_persists_cache(self):
        """Test that cache persists in singleton."""
        generator = get_explanation_generator()
        
        decision_data = {
            'decision_id': 'test-027',
            'action': 'test action'
        }
        
        # Generate explanation
        generator.generate_brief(decision_data)
        
        # Get singleton again and check cache
        generator2 = get_explanation_generator()
        cached = generator2.get_cached_explanation(
            'test-027',
            format=ExplanationFormat.BRIEF,
            audience=AudienceType.DEVELOPER
        )
        
        assert cached is not None


class TestContextSummarization:
    """Test context summarization in explanations."""
    
    def test_summarize_empty_context(self):
        """Test summarizing empty context."""
        generator = ExplanationGenerator()
        
        summary = generator._summarize_context({})
        
        assert summary == "no specific context"
    
    def test_summarize_context_with_current_action(self):
        """Test summarizing context with current action."""
        generator = ExplanationGenerator()
        
        context = {'current_action': 'implementing feature'}
        summary = generator._summarize_context(context)
        
        assert 'current action' in summary
        assert 'implementing feature' in summary
    
    def test_summarize_context_with_errors(self):
        """Test summarizing context with recent errors."""
        generator = ExplanationGenerator()
        
        context = {
            'recent_errors': ['error1', 'error2', 'error3']
        }
        summary = generator._summarize_context(context)
        
        assert 'recent errors' in summary
        assert '3' in summary
    
    def test_summarize_context_with_progress(self):
        """Test summarizing context with progress."""
        generator = ExplanationGenerator()
        
        context = {'task_progress': '75%'}
        summary = generator._summarize_context(context)
        
        assert 'progress' in summary
        assert '75%' in summary
    
    def test_summarize_context_with_constraints(self):
        """Test summarizing context with constraints."""
        generator = ExplanationGenerator()
        
        context = {
            'constraints': ['time limit', 'memory limit', 'api limit']
        }
        summary = generator._summarize_context(context)
        
        assert 'constraints' in summary
    
    def test_summarize_complex_context(self):
        """Test summarizing complex context."""
        generator = ExplanationGenerator()
        
        context = {
            'current_action': 'optimizing database',
            'recent_errors': ['timeout', 'slow query'],
            'task_progress': '60%',
            'constraints': ['memory limit', 'time limit']
        }
        
        summary = generator._summarize_context(context)
        
        assert 'current action' in summary
        assert 'recent errors' in summary
        assert 'progress' in summary
        assert 'constraints' in summary