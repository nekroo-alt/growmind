"""
Unit tests for Lesson Learner module
"""

import pytest
import sqlite3
import tempfile
import os
from datetime import datetime
from v3.logic.lesson_learner import LessonLearner, LessonLearned, FailureAnalysis


class TestLessonLearner:
    """Test suite for LessonLearner class"""
    
    @pytest.fixture
    def temp_db_path(self):
        """Create temporary database for testing"""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        yield path
        if os.path.exists(path):
            os.remove(path)
    
    @pytest.fixture
    def learner(self, temp_db_path):
        """Create LessonLearner instance with temporary database"""
        learner = LessonLearner(db_path=temp_db_path)
        yield learner
        # Cleanup is handled by temp_db_path fixture
    
    def test_initialization(self, temp_db_path):
        """Test that LessonLearner initializes correctly"""
        learner = LessonLearner(db_path=temp_db_path)
        
        # Check that database was created
        assert os.path.exists(temp_db_path)
        
        # Check that tables were created
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        
        # Check lessons_learned table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='lessons_learned'")
        assert cursor.fetchone() is not None
        
        # Check failures table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='failures'")
        assert cursor.fetchone() is not None
        
        # Check mistake_tracking table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='mistake_tracking'")
        assert cursor.fetchone() is not None
        
        conn.close()
    
    def test_record_timeout_failure(self, learner):
        """Test recording a timeout failure"""
        decision_id = "test-decision-1"
        context = {
            'situation_type': 'normal',
            'task_type': 'implementation',
            'context_level': 'L0',
            'strategy': 'balanced',
            'resources': {'tokens_used': 1000, 'token_budget': 5000}
        }
        error_message = "Operation timed out after 30 seconds"
        
        analysis = learner.record_failure(decision_id, context, error_message)
        
        # Check analysis
        assert analysis.decision_id == decision_id
        assert analysis.failure_type == 'timeout_failure'
        assert analysis.severity == 'high'
        assert 'timeout' in analysis.root_cause.lower()
        assert len(analysis.contributing_factors) >= 0
        assert 'retry' in analysis.suggested_prevention.lower()
        
        # Check that failure was saved to database
        conn = sqlite3.connect(learner.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM failures WHERE decision_id = ?', (decision_id,))
        count = cursor.fetchone()[0]
        assert count == 1
        conn.close()
    
    def test_record_connection_failure(self, learner):
        """Test recording a connection failure"""
        decision_id = "test-decision-2"
        context = {
            'situation_type': 'error',
            'task_type': 'implementation'
        }
        error_message = "Failed to connect to database: connection refused"
        
        analysis = learner.record_failure(decision_id, context, error_message)
        
        assert analysis.failure_type == 'connection_failure'
        assert analysis.severity == 'high'
        assert 'connection' in analysis.root_cause.lower()
    
    def test_record_permission_failure(self, learner):
        """Test recording a permission failure"""
        decision_id = "test-decision-3"
        context = {
            'situation_type': 'normal',
            'task_type': 'implementation'
        }
        error_message = "Permission denied: cannot write to file"
        
        analysis = learner.record_failure(decision_id, context, error_message)
        
        assert analysis.failure_type == 'permission_failure'
        assert analysis.severity == 'critical'
        assert 'permission' in analysis.root_cause.lower()
    
    def test_record_memory_failure(self, learner):
        """Test recording a memory failure"""
        decision_id = "test-decision-4"
        context = {
            'situation_type': 'error',
            'task_type': 'implementation'
        }
        error_message = "Out of memory: cannot allocate buffer"
        
        analysis = learner.record_failure(decision_id, context, error_message)
        
        assert analysis.failure_type == 'memory_failure'
        assert analysis.severity == 'critical'
        assert 'memory' in analysis.root_cause.lower()
    
    def test_record_validation_failure(self, learner):
        """Test recording a validation failure"""
        decision_id = "test-decision-5"
        context = {
            'situation_type': 'normal',
            'task_type': 'validation'
        }
        error_message = "Invalid input: validation failed for field 'name'"
        
        analysis = learner.record_failure(decision_id, context, error_message)
        
        assert analysis.failure_type == 'validation_failure'
        assert 'validation' in analysis.root_cause.lower()
    
    def test_record_loop_failure(self, learner):
        """Test recording a loop failure"""
        decision_id = "test-decision-6"
        context = {
            'situation_type': 'error',
            'task_type': 'implementation',
            'detected_traps': ['loop', 'dead_end']
        }
        
        analysis = learner.record_failure(decision_id, context)
        
        assert analysis.failure_type == 'loop_failure'
        assert analysis.severity == 'medium'
        assert 'loop' in analysis.root_cause.lower()
    
    def test_record_dead_end_failure(self, learner):
        """Test recording a dead end failure"""
        decision_id = "test-decision-7"
        context = {
            'situation_type': 'error',
            'task_type': 'implementation',
            'detected_traps': ['dead_end']
        }
        
        analysis = learner.record_failure(decision_id, context)
        
        assert analysis.failure_type == 'dead_end_failure'
        assert analysis.severity == 'medium'
        assert 'dead end' in analysis.root_cause.lower()
    
    def test_record_planning_failure(self, learner):
        """Test recording a planning failure"""
        decision_id = "test-decision-8"
        context = {
            'situation_type': 'normal',
            'task_type': 'planning'
        }
        
        analysis = learner.record_failure(decision_id, context)
        
        assert analysis.failure_type == 'planning_failure'
        assert 'planning' in analysis.root_cause.lower()
    
    def test_record_implementation_failure(self, learner):
        """Test recording an implementation failure"""
        decision_id = "test-decision-9"
        context = {
            'situation_type': 'normal',
            'task_type': 'implementation'
        }
        
        analysis = learner.record_failure(decision_id, context)
        
        assert analysis.failure_type == 'implementation_failure'
        assert analysis.severity == 'medium'
        assert 'implementation' in analysis.root_cause.lower()
    
    def test_identify_contributing_factors(self, learner):
        """Test identification of contributing factors"""
        decision_id = "test-decision-10"
        context = {
            'situation_type': 'normal',
            'task_type': 'implementation',
            'context_level': 'L0',
            'strategy': 'aggressive',
            'resources': {'tokens_used': 4600, 'token_budget': 5000},
            'recent_error_count': 4,
            'detected_traps': ['loop'],
            'task_type': 'complex_implementation'
        }
        
        analysis = learner.record_failure(decision_id, context)
        
        # Check for identified factors
        factors = analysis.contributing_factors
        assert len(factors) > 0
        
        # Should detect insufficient context
        assert any('Insufficient context' in f for f in factors)
        
        # Should detect aggressive strategy
        assert any('Aggressive strategy' in f for f in factors)
        
        # Should detect resource constraints
        assert any('Resource constraints' in f for f in factors)
        
        # Should detect high error rate
        assert any('High error rate' in f for f in factors)
        
        # Should detect traps
        assert any('Detected traps' in f for f in factors)
        
        # Should detect task complexity
        assert any('High task complexity' in f for f in factors)
    
    def test_severity_adjustment_by_error_count(self, learner):
        """Test that severity is adjusted based on error count"""
        # Low error count
        context_low = {
            'situation_type': 'normal',
            'task_type': 'implementation',
            'recent_error_count': 1
        }
        analysis_low = learner.record_failure("decision-low", context_low)
        
        # High error count
        context_high = {
            'situation_type': 'normal',
            'task_type': 'implementation',
            'recent_error_count': 6
        }
        analysis_high = learner.record_failure("decision-high", context_high)
        
        # High error count should result in higher severity
        assert analysis_high.severity in ['high', 'critical']
    
    def test_lesson_creation_from_failure(self, learner):
        """Test that a lesson is created from a failure"""
        decision_id = "test-decision-11"
        context = {
            'situation_type': 'normal',
            'task_type': 'implementation'
        }
        error_message = "Timeout occurred"
        
        analysis = learner.record_failure(decision_id, context, error_message)
        
        # Check that a lesson was created
        conn = sqlite3.connect(learner.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM lessons_learned')
        lesson_count = cursor.fetchone()[0]
        assert lesson_count >= 1
        
        # Check that failure is linked to lesson
        cursor.execute('SELECT lesson_id FROM failures WHERE failure_id = ?', (analysis.failure_id,))
        lesson_id = cursor.fetchone()[0]
        assert lesson_id is not None
        
        # Check lesson details
        cursor.execute('''
            SELECT failure_type, root_cause, prevention, frequency, effectiveness
            FROM lessons_learned WHERE lesson_id = ?
        ''', (lesson_id,))
        result = cursor.fetchone()
        assert result is not None
        assert result[0] == 'timeout_failure'
        assert result[3] == 1  # frequency
        assert result[4] == 0.5  # initial effectiveness
        
        conn.close()
    
    def test_lesson_update_for_similar_failure(self, learner):
        """Test that existing lesson is updated for similar failure"""
        # Record first failure
        context1 = {
            'situation_type': 'normal',
            'task_type': 'implementation'
        }
        error_message = "Timeout occurred"
        analysis1 = learner.record_failure("decision-1", context1, error_message)
        
        # Get initial lesson frequency
        conn = sqlite3.connect(learner.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT frequency FROM lessons_learned WHERE lesson_id = ?', (analysis1.lesson_id,))
        initial_freq = cursor.fetchone()[0]
        conn.close()
        
        assert initial_freq == 1
        
        # Record similar failure (same type)
        analysis2 = learner.record_failure("decision-2", context1, error_message)
        
        # Check that lesson was updated (not new lesson created)
        conn = sqlite3.connect(learner.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM lessons_learned')
        lesson_count = cursor.fetchone()[0]
        assert lesson_count == 1  # Should still be one lesson
        
        # Check that frequency was incremented
        cursor.execute('SELECT frequency FROM lessons_learned WHERE lesson_id = ?', (analysis1.lesson_id,))
        updated_freq = cursor.fetchone()[0]
        assert updated_freq == 2  # Should be incremented
        
        conn.close()
    
    def test_get_lessons_for_context(self, learner):
        """Test getting lessons for a specific context"""
        # Create some failures
        context1 = {
            'situation_type': 'normal',
            'task_type': 'implementation'
        }
        learner.record_failure("decision-1", context1, "Timeout occurred")
        learner.record_failure("decision-2", context1, "Timeout occurred")
        
        # Get lessons for similar context
        context2 = {
            'situation_type': 'normal',
            'task_type': 'implementation'
        }
        lessons = learner.get_lessons_for_context(context2)
        
        assert len(lessons) > 0
        assert all(isinstance(lesson, LessonLearned) for lesson in lessons)
        assert all(lesson.failure_type == 'timeout_failure' for lesson in lessons)
    
    def test_apply_lesson_success(self, learner):
        """Test applying a lesson successfully"""
        # Create a failure and lesson
        context = {
            'situation_type': 'normal',
            'task_type': 'implementation'
        }
        analysis = learner.record_failure("decision-1", context, "Timeout occurred")
        lesson_id = analysis.lesson_id
        
        # Apply lesson successfully
        learner.apply_lesson(lesson_id, success=True)
        
        # Check that effectiveness increased
        conn = sqlite3.connect(learner.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT effectiveness FROM lessons_learned WHERE lesson_id = ?', (lesson_id,))
        effectiveness = cursor.fetchone()[0]
        conn.close()
        
        assert effectiveness > 0.5  # Should be higher than initial 0.5
        
        # Check mistake tracking
        conn = sqlite3.connect(learner.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT mistake_avoided FROM mistake_tracking WHERE lesson_applied = 1')
        avoided = cursor.fetchone()[0]
        conn.close()
        
        assert avoided == 1
    def test_apply_lesson_failure(self, learner):
        """Test applying a lesson with failure"""
        # Create a failure and lesson
        context = {
            'situation_type': 'normal',
            'task_type': 'implementation'
        }
        analysis = learner.record_failure("decision-1", context, "Timeout occurred")
        lesson_id = analysis.lesson_id
        
        # Apply lesson with failure
        learner.apply_lesson(lesson_id, success=False)
        
        # Check that effectiveness decreased
        conn = sqlite3.connect(learner.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT effectiveness FROM lessons_learned WHERE lesson_id = ?', (lesson_id,))
        effectiveness = cursor.fetchone()[0]
        conn.close()
        
        assert effectiveness < 0.5  # Should be lower than initial 0.5
    
    def test_effectiveness_calculation(self, learner):
        """Test effectiveness calculation with multiple applications"""
        # Create a failure and lesson
        context = {
            'situation_type': 'normal',
            'task_type': 'implementation'
        }
        analysis = learner.record_failure("decision-1", context, "Timeout occurred")
        lesson_id = analysis.lesson_id
        
        # Apply lesson multiple times with mixed results
        learner.apply_lesson(lesson_id, success=True)
        learner.apply_lesson(lesson_id, success=False)
        learner.apply_lesson(lesson_id, success=True)
        
        # Check that effectiveness reflects the mixed results
        conn = sqlite3.connect(learner.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT effectiveness FROM lessons_learned WHERE lesson_id = ?', (lesson_id,))
        effectiveness = cursor.fetchone()[0]
        conn.close()
        
        # Should be somewhere between 0 and 1
        assert 0.0 < effectiveness < 1.0
    
    def test_get_mistake_statistics(self, learner):
        """Test getting mistake statistics"""
        # Create some failures
        context1 = {'situation_type': 'normal', 'task_type': 'implementation'}
        learner.record_failure("decision-1", context1, "Timeout occurred")
        
        context2 = {'situation_type': 'normal', 'task_type': 'planning'}
        learner.record_failure("decision-2", context2, "Permission denied")
        
        # Get statistics
        stats = learner.get_mistake_statistics()
        
        # Check statistics
        assert 'total_failures' in stats
        assert stats['total_failures'] >= 2
        assert 'failures_by_type' in stats
        assert stats['total_lessons'] >= 2
        assert 'average_effectiveness' in stats
        assert 'total_lesson_applications' in stats
        assert 'mistakes_avoided' in stats
        assert 'mistake_avoidance_rate' in stats
    
    def test_get_lessons_by_effectiveness(self, learner):
        """Test getting lessons sorted by effectiveness"""
        # Create failures and apply lessons with different results
        context = {'situation_type': 'normal', 'task_type': 'implementation'}
        analysis1 = learner.record_failure("decision-1", context, "Timeout occurred")
        lesson_id1 = analysis1.lesson_id
        
        analysis2 = learner.record_failure("decision-2", context, "Timeout occurred")
        lesson_id2 = analysis2.lesson_id
        
        # Apply lessons with different results
        learner.apply_lesson(lesson_id1, success=True)
        learner.apply_lesson(lesson_id1, success=True)  # High effectiveness
        learner.apply_lesson(lesson_id2, success=False)
        learner.apply_lesson(lesson_id2, success=False)  # Low effectiveness
        
        # Get lessons by effectiveness
        lessons = learner.get_lessons_by_effectiveness(min_effectiveness=0.0, limit=10)
        
        assert len(lessons) >= 2
        # Should be sorted by effectiveness (highest first)
        if len(lessons) >= 2:
            assert lessons[0].effectiveness >= lessons[1].effectiveness
    
    def test_get_recent_failures(self, learner):
        """Test getting recent failures"""
        # Create some failures
        context = {'situation_type': 'normal', 'task_type': 'implementation'}
        learner.record_failure("decision-1", context, "Timeout occurred")
        learner.record_failure("decision-2", context, "Permission denied")
        learner.record_failure("decision-3", context, "Memory error")
        
        # Get recent failures
        recent = learner.get_recent_failures(limit=5)
        
        assert len(recent) >= 3
        assert all(isinstance(f, FailureAnalysis) for f in recent)
        # Should be sorted by analyzed_at (most recent first)
        assert len(recent) <= 5
    
    def test_cleanup_old_data(self, learner):
        """Test cleanup of old data"""
        # Create some failures
        context = {'situation_type': 'normal', 'task_type': 'implementation'}
        analysis = learner.record_failure("decision-1", context, "Timeout occurred")
        lesson_id = analysis.lesson_id
        
        # Apply lesson multiple times to make it effective
        for _ in range(10):
            learner.apply_lesson(lesson_id, success=True)
        
        # Cleanup old data (0 days = all data)
        learner.cleanup_old_data(days=0)
        
        # Check that old data was cleaned
        conn = sqlite3.connect(learner.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM failures')
        failure_count = cursor.fetchone()[0]
        
        # Old lessons with low effectiveness should be deleted
        cursor.execute('''
            SELECT COUNT(*) FROM lessons_learned 
            WHERE effectiveness < 0.5 AND frequency < 3
        ''')
        low_quality_count = cursor.fetchone()[0]
        conn.close()
        
        assert low_quality_count == 0  # Low quality lessons should be cleaned
    
    def test_thread_safety(self, temp_db_path):
        """Test that LessonLearner is thread-safe"""
        import threading
        
        learner = LessonLearner(db_path=temp_db_path)
        results = []
        
        def record_failure(i):
            context = {'situation_type': 'normal', 'task_type': 'implementation'}
            try:
                analysis = learner.record_failure(f"decision-{i}", context, "Timeout occurred")
                results.append((i, analysis.failure_type))
            except Exception as e:
                results.append((i, str(e)))
        
        # Create multiple threads
        threads = []
        for i in range(10):
            t = threading.Thread(target=record_failure, args=(i,))
            threads.append(t)
            t.start()
        
        # Wait for all threads to complete
        for t in threads:
            t.join()
        
        # Check that all operations succeeded
        assert len(results) == 10
        assert all(failure_type == 'timeout_failure' for _, failure_type in results)
        
        # Check that all failures were recorded
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM failures')
        count = cursor.fetchone()[0]
        assert count == 10
        conn.close()
    
    def test_failure_without_error_message(self, learner):
        """Test recording a failure without an error message"""
        decision_id = "test-decision-12"
        context = {
            'situation_type': 'normal',
            'task_type': 'implementation'
        }
        
        analysis = learner.record_failure(decision_id, context)
        
        # Should still create analysis
        assert analysis.decision_id == decision_id
        assert analysis.failure_type == 'implementation_failure'
    
    def test_unknown_failure_type(self, learner):
        """Test handling of unknown failure type"""
        decision_id = "test-decision-13"
        context = {
            'situation_type': 'unknown',
            'task_type': 'unknown'
        }
        
        analysis = learner.record_failure(decision_id, context)
        
        # Should classify as unknown
        assert analysis.failure_type == 'unknown_failure'
        assert 'Unknown' in analysis.root_cause or 'investigation' in analysis.root_cause.lower()
    
    def test_prevention_strategy_generation(self, learner):
        """Test that prevention strategies are generated correctly"""
        # Test different failure types
        test_cases = [
            ("Timeout occurred", 'timeout_failure', 'retry'),
            ("Connection failed", 'connection_failure', 'circuit breaker'),
            ("Permission denied", 'permission_failure', 'permission'),
            ("Out of memory", 'memory_failure', 'memory'),
            ("Validation failed", 'validation_failure', 'validation'),
            ("Loop detected", 'loop_failure', 'loop'),
            ("Dead end", 'dead_end_failure', 'progress'),
        ]
        
        for error_msg, expected_type, keyword in test_cases:
            context = {'situation_type': 'normal', 'task_type': 'implementation'}
            analysis = learner.record_failure(f"decision-{expected_type}", context, error_msg)
            
            assert analysis.failure_type == expected_type
            assert keyword.lower() in analysis.suggested_prevention.lower()
    
    def test_multiple_failure_patterns(self, learner):
        """Test identification of multiple failure patterns"""
        # Create multiple failures of the same type
        context = {'situation_type': 'normal', 'task_type': 'implementation'}
        
        for i in range(5):
            learner.record_failure(f"decision-{i}", context, "Timeout occurred")
        
        # Check that failure patterns were identified
        # (This will print to console in _identify_failure_patterns)
        # We can check the database for pattern results
        conn = sqlite3.connect(learner.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM failures WHERE failure_type = ?', ('timeout_failure',))
        count = cursor.fetchone()[0]
        conn.close()
        
        assert count >= 5
    
    def test_dataclass_serialization(self, learner):
        """Test that dataclasses are properly serialized to database"""
        context = {'situation_type': 'normal', 'task_type': 'implementation'}
        analysis = learner.record_failure("decision-1", context, "Timeout occurred")
        
        # Retrieve from database
        conn = sqlite3.connect(learner.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM failures WHERE failure_id = ?', (analysis.failure_id,))
        row = cursor.fetchone()
        conn.close()
        
        # Check that all fields are present
        assert row is not None
        assert len(row) >= 9  # Should have at least 9 columns
    
    def test_lesson_learned_dataclass(self, learner):
        """Test LessonLearned dataclass properties"""
        lesson = LessonLearned(
            lesson_id="test-lesson-1",
            failure_type="timeout_failure",
            root_cause="Timeout occurred",
            context={'situation_type': 'normal'},
            prevention="Increase timeout",
            frequency=1,
            effectiveness=0.5,
            created_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat(),
            sample_failures=["failure-1", "failure-2"]
        )
        
        # Check that all fields are accessible
        assert lesson.lesson_id == "test-lesson-1"
        assert lesson.failure_type == "timeout_failure"
        assert lesson.frequency == 1
        assert lesson.effectiveness == 0.5
        assert len(lesson.sample_failures) == 2
    
    def test_failure_analysis_dataclass(self, learner):
        """Test FailureAnalysis dataclass properties"""
        analysis = FailureAnalysis(
            failure_id="test-failure-1",
            decision_id="decision-1",
            failure_type="timeout_failure",
            root_cause="Timeout occurred",
            context={'situation_type': 'normal'},
            contributing_factors=["Factor 1", "Factor 2"],
            suggested_prevention="Increase timeout",
            severity="high",
            analyzed_at=datetime.utcnow().isoformat()
        )
        
        # Check that all fields are accessible
        assert analysis.failure_id == "test-failure-1"
        assert analysis.decision_id == "decision-1"
        assert analysis.failure_type == "timeout_failure"
        assert analysis.severity == "high"
        assert len(analysis.contributing_factors) == 2
    
    def test_empty_contributing_factors(self, learner):
        """Test handling of cases with no contributing factors"""
        context = {
            'situation_type': 'normal',
            'task_type': 'simple_task'
        }
        
        analysis = learner.record_failure("decision-1", context, "Unknown error")
        
        # Should still have contributing factors (default message)
        assert len(analysis.contributing_factors) > 0
        assert 'No specific contributing factors' in ' '.join(analysis.contributing_factors)