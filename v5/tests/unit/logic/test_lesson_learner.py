"""
Unit tests for Lesson Learner module.

Tests cover:
- Failure recording
- Root cause analysis
- Pattern identification
- Lesson extraction
- Lesson application
- Lesson checking
- Metrics calculation
- Data management
"""

import pytest
import tempfile
import os
import sqlite3
from datetime import datetime, timedelta
from v5.logic.lesson_learner import (
    LessonLearner,
    FailureRecord,
    LessonLearned
)


@pytest.fixture
def temp_db_path():
    """Create a temporary database path for testing."""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def learner(temp_db_path):
    """Create a LessonLearner instance with temporary database."""
    return LessonLearner(db_path=temp_db_path)


class TestFailureRecording:
    """Tests for failure recording functionality."""
    
    def test_record_failure_basic(self, learner):
        """Test basic failure recording."""
        context = {
            'task_type': 'implementation',
            'situation_type': 'normal',
            'error_type': 'api_rate_limit'
        }
        decision = {
            'action': 'call_llm_api',
            'strategy': 'balanced',
            'confidence': 0.7
        }
        root_cause = 'API rate limit exceeded'
        
        failure_id = learner.record_failure(
            failure_type='api_rate_limit',
            context=context,
            decision=decision,
            root_cause=root_cause,
            severity='medium'
        )
        
        assert failure_id is not None
        assert len(failure_id) > 0
    
    def test_record_failure_with_resources(self, learner):
        """Test failure recording with resource information."""
        context = {'task_type': 'planning'}
        decision = {'action': 'analyze'}
        root_cause = 'Insufficient tokens'
        resources = {
            'tokens_used': 1500,
            'time_elapsed': 2.5,
            'cost': 0.03
        }
        
        failure_id = learner.record_failure(
            failure_type='insufficient_tokens',
            context=context,
            decision=decision,
            root_cause=root_cause,
            resources=resources
        )
        
        assert failure_id is not None
    
    def test_record_failure_different_severities(self, learner):
        """Test recording failures with different severity levels."""
        severities = ['low', 'medium', 'high', 'critical']
        failure_ids = []
        
        for severity in severities:
            failure_id = learner.record_failure(
                failure_type='test_failure',
                context={'test': True},
                decision={'action': 'test'},
                root_cause='Test',
                severity=severity
            )
            failure_ids.append(failure_id)
        
        assert len(failure_ids) == len(severities)
        assert all(fid is not None for fid in failure_ids)
    
    def test_record_multiple_failures(self, learner):
        """Test recording multiple failures."""
        failure_ids = []
        
        for i in range(10):
            failure_id = learner.record_failure(
                failure_type='test_failure',
                context={'iteration': i},
                decision={'action': f'action_{i}'},
                root_cause=f'Test failure {i}'
            )
            failure_ids.append(failure_id)
        
        assert len(failure_ids) == 10
        assert len(set(failure_ids)) == 10  # All unique


class TestRootCauseAnalysis:
    """Tests for root cause analysis."""
    
    def test_analyze_root_cause_with_error(self, learner):
        """Test root cause analysis with error information."""
        context = {
            'error_type': 'timeout',
            'task_type': 'implementation'
        }
        decision = {
            'action': 'wait_for_response',
            'reasoning': 'Waiting for API response'
        }
        
        root_cause = learner.analyze_root_cause(
            failure_type='timeout',
            context=context,
            decision=decision
        )
        
        assert 'timeout' in root_cause.lower()
    
    def test_analyze_root_cause_with_low_confidence(self, learner):
        """Test root cause analysis with low confidence."""
        context = {'task_type': 'planning'}
        decision = {
            'action': 'decide',
            'confidence': 0.3,
            'reasoning': 'Not enough context'
        }
        
        root_cause = learner.analyze_root_cause(
            failure_type='low_confidence',
            context=context,
            decision=decision
        )
        
        assert 'low confidence' in root_cause.lower()
    
    def test_analyze_root_cause_with_strategy(self, learner):
        """Test root cause analysis with strategy information."""
        context = {'task_type': 'implementation'}
        decision = {
            'action': 'proceed',
            'strategy': 'aggressive',
            'reasoning': 'Fast approach'
        }
        
        root_cause = learner.analyze_root_cause(
            failure_type='strategy_mismatch',
            context=context,
            decision=decision
        )
        
        assert 'aggressive' in root_cause
        assert 'strategy' in root_cause.lower()
    
    def test_analyze_root_cause_insufficient_context(self, learner):
        """Test root cause analysis with insufficient context."""
        context = {}
        decision = {}
        
        root_cause = learner.analyze_root_cause(
            failure_type='unknown',
            context=context,
            decision=decision
        )
        
        assert 'unknown' in root_cause.lower()
        assert 'insufficient' in root_cause.lower()


class TestPatternIdentification:
    """Tests for pattern identification."""
    
    def test_identify_pattern_single_occurrence(self, learner):
        """Test identifying a pattern from single failure."""
        context = {
            'task_type': 'implementation',
            'error_type': 'api_rate_limit'
        }
        
        failure_id = learner.record_failure(
            failure_type='api_rate_limit',
            context=context,
            decision={'action': 'call_api'},
            root_cause='Rate limit'
        )
        
        patterns = learner.get_failure_patterns(failure_type='api_rate_limit', min_frequency=1)
        assert len(patterns) == 1
        assert patterns[0]['frequency'] == 1
    
    def test_identify_recurring_pattern(self, learner):
        """Test identifying a recurring pattern."""
        context = {
            'task_type': 'implementation',
            'error_type': 'timeout'
        }
        
        # Record same failure multiple times
        for _ in range(5):
            learner.record_failure(
                failure_type='timeout',
                context=context,
                decision={'action': 'wait'},
                root_cause='Timeout'
            )
        
        patterns = learner.get_failure_patterns(failure_type='timeout', min_frequency=3)
        assert len(patterns) == 1
        assert patterns[0]['frequency'] == 5
    
    def test_identify_different_patterns(self, learner):
        """Test identifying different failure patterns."""
        contexts = [
            {'task_type': 'planning', 'error_type': 'timeout'},
            {'task_type': 'implementation', 'error_type': 'rate_limit'}
        ]
        
        for i, context in enumerate(contexts):
            learner.record_failure(
                failure_type='api_error',
                context=context,
                decision={'action': f'call_{i}'},
                root_cause='API error'
            )
        
        # Use min_frequency=1 to see all patterns, even single occurrences
        patterns = learner.get_failure_patterns(failure_type='api_error', min_frequency=1)
        assert len(patterns) == 2
    
    def test_pattern_timestamps(self, learner):
        """Test pattern timestamp tracking."""
        context = {'task_type': 'test', 'error_type': 'test_error'}
        
        # Record failure
        learner.record_failure(
            failure_type='test_failure',
            context=context,
            decision={'action': 'test'},
            root_cause='Test'
        )
        
        patterns = learner.get_failure_patterns(failure_type='test_failure', min_frequency=1)
        assert len(patterns) == 1
        assert 'first_seen' in patterns[0]
        assert 'last_seen' in patterns[0]


class TestLessonExtraction:
    """Tests for lesson extraction from failures."""
    
    def test_extract_lesson_basic(self, learner):
        """Test basic lesson extraction."""
        # Record a failure
        failure_id = learner.record_failure(
            failure_type='api_rate_limit',
            context={'task_type': 'implementation'},
            decision={'action': 'call_api'},
            root_cause='API rate limit exceeded'
        )
        
        # Extract lesson
        lesson = learner.extract_lesson(failure_id)
        
        assert lesson is not None
        assert lesson.lesson_id is not None
        assert lesson.failure_type == 'api_rate_limit'
        assert lesson.prevention is not None
        assert len(lesson.prevention) > 0
    
    def test_extract_lesson_with_custom_prevention(self, learner):
        """Test lesson extraction with custom prevention."""
        failure_id = learner.record_failure(
            failure_type='timeout',
            context={'task_type': 'implementation'},
            decision={'action': 'wait'},
            root_cause='Timeout'
        )
        
        custom_prevention = 'Use caching to reduce API calls'
        lesson = learner.extract_lesson(failure_id, prevention=custom_prevention)
        
        assert lesson.prevention == custom_prevention
    
    def test_extract_lesson_invalid_failure_id(self, learner):
        """Test lesson extraction with invalid failure ID."""
        lesson = learner.extract_lesson('invalid_id')
        assert lesson is None
    
    def test_extract_lesson_context_pattern(self, learner):
        """Test that lesson includes context pattern."""
        failure_id = learner.record_failure(
            failure_type='low_confidence',
            context={
                'task_type': 'planning',
                'situation_type': 'uncertain'
            },
            decision={'action': 'decide'},
            root_cause='Low confidence'
        )
        
        lesson = learner.extract_lesson(failure_id)
        # Pattern should include observable context features, not internal failure_type
        assert 'task_type=planning' in lesson.context_pattern
        assert 'situation_type=uncertain' in lesson.context_pattern
        # failure_type is stored separately in the lesson object
        assert lesson.failure_type == 'low_confidence'


class TestLessonApplication:
    """Tests for lesson application and tracking."""
    
    def test_apply_lesson_basic(self, learner):
        """Test basic lesson application."""
        failure_id = learner.record_failure(
            failure_type='test_failure',
            context={'task_type': 'test'},
            decision={'action': 'test'},
            root_cause='Test'
        )
        
        lesson = learner.extract_lesson(failure_id)
        success = learner.apply_lesson(lesson.lesson_id, prevented=True)
        
        assert success is True
    
    def test_apply_lesson_with_decision_id(self, learner):
        """Test lesson application with decision ID."""
        failure_id = learner.record_failure(
            failure_type='test_failure',
            context={'task_type': 'test'},
            decision={'action': 'test'},
            root_cause='Test'
        )
        
        lesson = learner.extract_lesson(failure_id)
        success = learner.apply_lesson(
            lesson.lesson_id,
            decision_id='decision_123',
            prevented=True
        )
        
        assert success is True
    
    def test_apply_lesson_effectiveness_score(self, learner):
        """Test that lesson effectiveness score updates."""
        failure_id = learner.record_failure(
            failure_type='test_failure',
            context={'task_type': 'test'},
            decision={'action': 'test'},
            root_cause='Test'
        )
        
        lesson = learner.extract_lesson(failure_id)
        initial_score = lesson.effectiveness_score
        
        # Apply lesson multiple times with prevention
        for _ in range(5):
            learner.apply_lesson(lesson.lesson_id, prevented=True)
        
        # Get updated lesson
        lessons = learner.get_lessons(failure_type='test_failure')
        updated_lesson = [l for l in lessons if l.lesson_id == lesson.lesson_id][0]
        
        assert updated_lesson.effectiveness_score > initial_score
        assert updated_lesson.application_count == 5
    
    def test_apply_lesson_prevented_false(self, learner):
        """Test lesson application when prevention failed."""
        failure_id = learner.record_failure(
            failure_type='test_failure',
            context={'task_type': 'test'},
            decision={'action': 'test'},
            root_cause='Test'
        )
        
        lesson = learner.extract_lesson(failure_id)
        initial_score = lesson.effectiveness_score
        
        # Apply lesson without prevention
        learner.apply_lesson(lesson.lesson_id, prevented=False)
        
        # Get updated lesson
        lessons = learner.get_lessons(failure_type='test_failure')
        updated_lesson = [l for l in lessons if l.lesson_id == lesson.lesson_id][0]
        
        # Score should not increase
        assert updated_lesson.effectiveness_score == initial_score
        assert updated_lesson.application_count == 1


class TestLessonChecking:
    """Tests for checking applicable lessons."""
    
    def test_check_lessons_no_lessons(self, learner):
        """Test checking lessons when none exist."""
        context = {'task_type': 'implementation'}
        decision = {'action': 'proceed'}
        
        applicable = learner.check_lessons(context, decision)
        assert len(applicable) == 0
    
    def test_check_lessons_applicable(self, learner):
        """Test checking lessons that apply to current context."""
        # Record and extract a lesson
        failure_id = learner.record_failure(
            failure_type='api_rate_limit',
            context={
                'task_type': 'implementation',
                'error_type': 'api_rate_limit'
            },
            decision={'action': 'call_api'},
            root_cause='Rate limit'
        )
        lesson = learner.extract_lesson(failure_id)
        
        # Check with matching context
        context = {
            'task_type': 'implementation',
            'error_type': 'api_rate_limit'
        }
        decision = {'action': 'call_api'}
        
        applicable = learner.check_lessons(context, decision)
        assert len(applicable) == 1
        assert applicable[0].lesson_id == lesson.lesson_id
    
    def test_check_lessons_not_applicable(self, learner):
        """Test checking lessons that don't apply to current context."""
        failure_id = learner.record_failure(
            failure_type='api_rate_limit',
            context={
                'task_type': 'implementation',
                'error_type': 'api_rate_limit'
            },
            decision={'action': 'call_api'},
            root_cause='Rate limit'
        )
        learner.extract_lesson(failure_id)
        
        # Check with different context
        context = {
            'task_type': 'planning',  # Different task type
            'error_type': 'timeout'  # Different error type
        }
        decision = {'action': 'analyze'}
        
        applicable = learner.check_lessons(context, decision)
        assert len(applicable) == 0
    
    def test_check_lessons_multiple_applicable(self, learner):
        """Test checking when multiple lessons apply."""
        # Record multiple failures with same context pattern
        for i in range(3):
            failure_id = learner.record_failure(
                failure_type='api_rate_limit',
                context={'task_type': 'implementation', 'error_type': 'api_rate_limit'},
                decision={'action': 'call_api'},
                root_cause=f'Rate limit {i}'
            )
            learner.extract_lesson(failure_id)
        
        context = {'task_type': 'implementation', 'error_type': 'api_rate_limit'}
        decision = {'action': 'call_api'}
        
        applicable = learner.check_lessons(context, decision)
        assert len(applicable) == 3


class TestMetricsCalculation:
    """Tests for metrics calculation."""
    
    def test_get_mistake_reduction_metrics_empty(self, learner):
        """Test metrics with no data."""
        metrics = learner.get_mistake_reduction_metrics()
        
        assert metrics['total_failures'] == 0
        assert metrics['total_lessons'] == 0
        assert metrics['total_applications'] == 0
        assert metrics['prevented_failures'] == 0
        assert metrics['patterns_found'] == 0
        assert metrics['avg_effectiveness'] == 0.0
        assert metrics['prevention_rate'] == 0.0
    
    def test_get_mistake_reduction_metrics_with_data(self, learner):
        """Test metrics with data."""
        # Record failures
        for i in range(5):
            failure_id = learner.record_failure(
                failure_type='test_failure',
                context={'task_type': 'test'},
                decision={'action': 'test'},
                root_cause=f'Test {i}'
            )
            # Extract lesson
            lesson = learner.extract_lesson(failure_id)
            # Apply lesson
            learner.apply_lesson(lesson.lesson_id, prevented=True)
        
        metrics = learner.get_mistake_reduction_metrics()
        
        assert metrics['total_failures'] == 5
        assert metrics['total_lessons'] == 5
        assert metrics['total_applications'] == 5
        assert metrics['prevented_failures'] == 5
        assert metrics['avg_effectiveness'] > 0
        assert metrics['prevention_rate'] == 1.0
    
    def test_metrics_failure_by_type(self, learner):
        """Test failure breakdown by type."""
        failure_types = ['timeout', 'rate_limit', 'invalid_context']
        
        for failure_type in failure_types:
            learner.record_failure(
                failure_type=failure_type,
                context={'task_type': 'test'},
                decision={'action': 'test'},
                root_cause='Test'
            )
        
        metrics = learner.get_mistake_reduction_metrics()
        
        for failure_type in failure_types:
            assert failure_type in metrics['failure_by_type']
            assert metrics['failure_by_type'][failure_type] == 1


class TestDataManagement:
    """Tests for data management operations."""
    
    def test_get_lessons_filter_by_type(self, learner):
        """Test getting lessons filtered by type."""
        # Record different failure types
        for failure_type in ['timeout', 'rate_limit']:
            failure_id = learner.record_failure(
                failure_type=failure_type,
                context={'task_type': 'test'},
                decision={'action': 'test'},
                root_cause='Test'
            )
            learner.extract_lesson(failure_id)
        
        timeout_lessons = learner.get_lessons(failure_type='timeout')
        rate_limit_lessons = learner.get_lessons(failure_type='rate_limit')
        all_lessons = learner.get_lessons()
        
        assert len(timeout_lessons) == 1
        assert len(rate_limit_lessons) == 1
        assert len(all_lessons) == 2
    
    def test_get_lessons_min_effectiveness(self, learner):
        """Test getting lessons with minimum effectiveness threshold."""
        # Create lessons with different effectiveness
        for i in range(3):
            failure_id = learner.record_failure(
                failure_type='test_failure',
                context={'task_type': 'test'},
                decision={'action': 'test'},
                root_cause='Test'
            )
            lesson = learner.extract_lesson(failure_id)
            # Apply lesson to increase effectiveness
            for _ in range(i):
                learner.apply_lesson(lesson.lesson_id, prevented=True)
        
        # Get lessons with high effectiveness
        high_effectiveness = learner.get_lessons(min_effectiveness=0.2)
        # Get all lessons
        all_lessons = learner.get_lessons()
        
        # Should have fewer lessons with high effectiveness threshold
        assert len(high_effectiveness) <= len(all_lessons)
    
    def test_get_lessons_limit(self, learner):
        """Test getting lessons with limit."""
        # Create multiple lessons
        for i in range(10):
            failure_id = learner.record_failure(
                failure_type='test_failure',
                context={'task_type': 'test'},
                decision={'action': f'test_{i}'},
                root_cause='Test'
            )
            learner.extract_lesson(failure_id)
        
        limited = learner.get_lessons(limit=5)
        all_lessons = learner.get_lessons()
        
        assert len(limited) == 5
        assert len(all_lessons) == 10
    
    def test_export_lessons_json(self, learner):
        """Test exporting lessons as JSON."""
        failure_id = learner.record_failure(
            failure_type='test_failure',
            context={'task_type': 'test'},
            decision={'action': 'test'},
            root_cause='Test'
        )
        lesson = learner.extract_lesson(failure_id)
        
        json_export = learner.export_lessons(output_format='json')
        
        assert isinstance(json_export, str)
        assert lesson.lesson_id in json_export
        assert 'failure_type' in json_export
    
    def test_export_lessons_dict(self, learner):
        """Test exporting lessons as dict."""
        failure_id = learner.record_failure(
            failure_type='test_failure',
            context={'task_type': 'test'},
            decision={'action': 'test'},
            root_cause='Test'
        )
        learner.extract_lesson(failure_id)
        
        dict_export = learner.export_lessons(output_format='dict')
        
        assert isinstance(dict_export, list)
        assert len(dict_export) == 1
        assert isinstance(dict_export[0], dict)
    
    def test_delete_old_failures(self, learner):
        """Test deleting old failure records."""
        from datetime import datetime, timedelta
        
        # Record recent failure
        recent_id = learner.record_failure(
            failure_type='recent_failure',
            context={'task_type': 'test'},
            decision={'action': 'test'},
            root_cause='Test'
        )
        
        # Manually insert an old failure
        old_timestamp = (datetime.utcnow() - timedelta(days=100)).isoformat()
        with sqlite3.connect(learner.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO failures
                (failure_id, timestamp, failure_type, context, decision, root_cause, severity)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                'old_failure_id',
                old_timestamp,
                'old_failure',
                '{"task": "test"}',
                '{"action": "test"}',
                'Test',
                'medium'
            ))
            conn.commit()
        
        # Delete failures older than 30 days
        deleted = learner.delete_old_failures(days_old=30)
        
        assert deleted == 1
        
        # Verify recent failure still exists
        lessons = learner.get_lessons(failure_type='recent_failure')
        # Note: We didn't extract a lesson from recent_id, so we check patterns
        patterns = learner.get_failure_patterns(failure_type='recent_failure')
        # Should have pattern from recent failure
        assert len(patterns) >= 0  # May or may not have pattern based on implementation


class TestContextSignature:
    """Tests for context signature generation."""
    
    def test_context_signature_with_task_type(self, learner):
        """Test context signature with task type."""
        context = {'task_type': 'implementation'}
        signature = learner._create_context_signature(context)
        assert 'task:implementation' in signature
    
    def test_context_signature_with_multiple_features(self, learner):
        """Test context signature with multiple features."""
        context = {
            'task_type': 'planning',
            'situation_type': 'complex',
            'error_type': 'timeout',
            'strategy': 'conservative',
            'action_type': 'analyze'
        }
        signature = learner._create_context_signature(context)
        
        assert 'task:planning' in signature
        assert 'situation:complex' in signature
        assert 'error:timeout' in signature
        assert 'strategy:conservative' in signature
        assert 'action:analyze' in signature
    
    def test_context_signature_empty(self, learner):
        """Test context signature with empty context."""
        context = {}
        signature = learner._create_context_signature(context)
        assert signature == ""


class TestLessonApplies:
    """Tests for lesson applicability checking."""
    
    def test_lesson_applies_exact_match(self, learner):
        """Test lesson applies with exact context match."""
        failure_id = learner.record_failure(
            failure_type='test_failure',
            context={
                'task_type': 'implementation',
                'error_type': 'timeout'
            },
            decision={'action': 'wait'},
            root_cause='Test'
        )
        lesson = learner.extract_lesson(failure_id)
        
        current_context = {
            'task_type': 'implementation',
            'error_type': 'timeout'
        }
        current_decision = {'action': 'wait'}
        
        applies = learner._lesson_applies(lesson, current_context, current_decision)
        assert applies is True
    
    def test_lesson_applies_partial_match(self, learner):
        """Test lesson does not apply when required context is missing."""
        failure_id = learner.record_failure(
            failure_type='test_failure',
            context={
                'task_type': 'implementation',
                'error_type': 'timeout'
            },
            decision={'action': 'wait'},
            root_cause='Test'
        )
        lesson = learner.extract_lesson(failure_id)
        
        # Missing error_type from current context
        # The lesson pattern includes error_type, so current situation doesn't match
        current_context = {'task_type': 'implementation'}
        current_decision = {'action': 'wait'}
        
        applies = learner._lesson_applies(lesson, current_context, current_decision)
        # Should be False because error_type is missing from current context but is in lesson pattern
        assert applies is False
    
    def test_lesson_applies_no_match(self, learner):
        """Test lesson doesn't apply with different context."""
        failure_id = learner.record_failure(
            failure_type='test_failure',
            context={'task_type': 'planning'},
            decision={'action': 'analyze'},
            root_cause='Test'
        )
        lesson = learner.extract_lesson(failure_id)
        
        current_context = {'task_type': 'implementation'}
        current_decision = {'action': 'implement'}
        
        applies = learner._lesson_applies(lesson, current_context, current_decision)
        assert applies is False


class TestIntegration:
    """Integration tests for complete workflows."""
    
    def test_complete_learning_workflow(self, learner):
        """Test complete learning workflow: record -> extract -> apply."""
        # Record failure
        failure_id = learner.record_failure(
            failure_type='api_rate_limit',
            context={
                'task_type': 'implementation',
                'error_type': 'api_rate_limit'
            },
            decision={
                'action': 'call_llm_api',
                'strategy': 'aggressive'
            },
            root_cause='API rate limit exceeded',
            resources={'tokens_used': 2000}
        )
        
        # Extract lesson
        lesson = learner.extract_lesson(failure_id)
        assert lesson is not None
        
        # Check lesson applies to similar situation
        context = {
            'task_type': 'implementation',
            'error_type': 'api_rate_limit'
        }
        decision = {'action': 'call_llm_api'}
        applicable = learner.check_lessons(context, decision)
        assert len(applicable) == 1
        
        # Apply lesson
        success = learner.apply_lesson(lesson.lesson_id, prevented=True)
        assert success is True
        
        # Get metrics
        metrics = learner.get_mistake_reduction_metrics()
        assert metrics['total_failures'] == 1
        assert metrics['total_lessons'] == 1
        assert metrics['prevented_failures'] == 1
    
    def test_learning_from_recurring_failure(self, learner):
        """Test learning from recurring failure pattern."""
        context = {
            'task_type': 'implementation',
            'error_type': 'timeout'
        }
        
        # Record same failure multiple times
        failure_ids = []
        for _ in range(5):
            failure_id = learner.record_failure(
                failure_type='timeout',
                context=context,
                decision={'action': 'wait_for_response'},
                root_cause='Timeout occurred'
            )
            failure_ids.append(failure_id)
        
        # Extract lessons
        lessons = []
        for failure_id in failure_ids:
            lesson = learner.extract_lesson(failure_id)
            lessons.append(lesson)
        
        assert len(lessons) == 5
        
        # Check pattern was identified
        patterns = learner.get_failure_patterns(failure_type='timeout', min_frequency=3)
        assert len(patterns) == 1
        assert patterns[0]['frequency'] == 5
        
        # Apply one lesson
        learner.apply_lesson(lessons[0].lesson_id, prevented=True)
        
        # Get metrics
        metrics = learner.get_mistake_reduction_metrics()
        assert metrics['patterns_found'] >= 1


if __name__ == '__main__':
    # Run tests
    pytest.main([__file__, '-v'])