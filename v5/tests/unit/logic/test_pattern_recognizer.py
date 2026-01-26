"""
Unit tests for Pattern Recognition Engine
"""

import unittest
import os
import tempfile
import shutil
from datetime import datetime, timedelta

from v5.logic.pattern_recognizer import (
    PatternRecognizer,
    DecisionPattern,
    PatternPrediction
)


class TestDecisionPattern(unittest.TestCase):
    """Test cases for DecisionPattern dataclass"""
    
    def test_decision_pattern_creation(self):
        """Test creating a decision pattern"""
        pattern = DecisionPattern(
            pattern_id='test-id',
            pattern_type='sequence',
            pattern={'sequence': ['action1', 'action2']},
            success_rate=0.85,
            frequency=10,
            confidence=0.9,
            created_at='2024-01-01T00:00:00Z',
            updated_at='2024-01-01T00:00:00Z'
        )
        
        self.assertEqual(pattern.pattern_id, 'test-id')
        self.assertEqual(pattern.pattern_type, 'sequence')
        self.assertEqual(pattern.success_rate, 0.85)
        self.assertEqual(pattern.frequency, 10)
        self.assertEqual(pattern.confidence, 0.9)
    
    def test_decision_pattern_with_optional_fields(self):
        """Test creating a decision pattern with optional fields"""
        pattern = DecisionPattern(
            pattern_id='test-id',
            pattern_type='context',
            pattern={'context_key': 'situation:normal'},
            success_rate=0.75,
            frequency=5,
            confidence=0.8,
            created_at='2024-01-01T00:00:00Z',
            updated_at='2024-01-01T00:00:00Z',
            context_filter={'context_key': 'situation:normal'},
            sample_decisions=['dec1', 'dec2']
        )
        
        self.assertIsNotNone(pattern.context_filter)
        self.assertEqual(len(pattern.sample_decisions), 2)


class TestPatternPrediction(unittest.TestCase):
    """Test cases for PatternPrediction dataclass"""
    
    def test_pattern_prediction_creation(self):
        """Test creating a pattern prediction"""
        prediction = PatternPrediction(
            pattern_id='pattern-id',
            predicted_action='write_test',
            confidence=0.85,
            expected_success_rate=0.9,
            reasoning='Based on similar contexts',
            matching_patterns=['pat1', 'pat2', 'pat3']
        )
        
        self.assertEqual(prediction.predicted_action, 'write_test')
        self.assertEqual(prediction.confidence, 0.85)
        self.assertEqual(len(prediction.matching_patterns), 3)


class TestPatternRecognizer(unittest.TestCase):
    """Test cases for PatternRecognizer class"""
    
    def setUp(self):
        """Set up test environment"""
        # Create temporary directory for test database
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, 'test_patterns.db')
        
        # Create pattern recognizer
        self.recognizer = PatternRecognizer(db_path=self.db_path)
    
    def tearDown(self):
        """Clean up test environment"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_initialization(self):
        """Test pattern recognizer initialization"""
        self.assertIsNotNone(self.recognizer)
        self.assertEqual(self.recognizer.db_path, self.db_path)
        self.assertEqual(self.recognizer.min_pattern_frequency, 3)
        self.assertEqual(self.recognizer.success_threshold, 0.7)
        self.assertEqual(self.recognizer.failure_threshold, 0.3)
    
    def test_database_initialization(self):
        """Test database tables are created"""
        import sqlite3
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Check patterns table exists
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='patterns'"
            )
            result = cursor.fetchone()
            self.assertIsNotNone(result)
            
            # Check pattern_metrics table exists
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='pattern_metrics'"
            )
            result = cursor.fetchone()
            self.assertIsNotNone(result)
            
            # Check pattern_relationships table exists
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='pattern_relationships'"
            )
            result = cursor.fetchone()
            self.assertIsNotNone(result)
    
    def test_recognize_sequence_patterns(self):
        """Test sequence pattern recognition"""
        decisions = [
            {
                'decision_id': f'dec-{i}',
                'action': f'action_{i % 3}',  # Repeating pattern: action_0, action_1, action_2
                'outcome': 'success' if i % 2 == 0 else 'success',
                'context': {'situation_type': 'normal'}
            }
            for i in range(10)
        ]
        
        patterns = self.recognizer.recognize_patterns(decisions)
        
        # Should recognize sequence patterns
        sequence_patterns = [p for p in patterns if p.pattern_type == 'sequence']
        self.assertGreater(len(sequence_patterns), 0)
        
        # Check pattern properties
        pattern = sequence_patterns[0]
        self.assertIsNotNone(pattern.pattern_id)
        self.assertGreaterEqual(pattern.frequency, 3)
        self.assertGreaterEqual(pattern.success_rate, 0.0)
        self.assertGreaterEqual(pattern.confidence, 0.0)
    
    def test_recognize_context_patterns(self):
        """Test context pattern recognition"""
        decisions = [
            {
                'decision_id': f'dec-{i}',
                'action': 'write_test',
                'outcome': 'success',
                'context': {
                    'situation_type': 'normal',
                    'task_type': 'implementation'
                }
            }
            for i in range(10)
        ]
        
        patterns = self.recognizer.recognize_patterns(decisions)
        
        # Should recognize context patterns
        context_patterns = [p for p in patterns if p.pattern_type == 'context']
        self.assertGreater(len(context_patterns), 0)
        
        # Check pattern has context filter
        pattern = context_patterns[0]
        self.assertIsNotNone(pattern.context_filter)
        self.assertIn('context_key', pattern.context_filter)
    
    def test_recognize_success_patterns(self):
        """Test success pattern recognition"""
        decisions = [
            {
                'decision_id': f'dec-{i}',
                'action': 'write_test',
                'outcome': 'success',
                'context': {'situation_type': 'normal', 'task_type': 'test'}
            }
            for i in range(10)
        ]
        
        patterns = self.recognizer.recognize_patterns(decisions)
        
        # Should recognize success patterns
        success_patterns = [p for p in patterns if p.pattern_type == 'success']
        self.assertGreater(len(success_patterns), 0)
        
        # Check success patterns have high success rate
        pattern = success_patterns[0]
        self.assertGreaterEqual(pattern.success_rate, self.recognizer.success_threshold)
    
    def test_recognize_failure_patterns(self):
        """Test failure pattern recognition"""
        decisions = [
            {
                'decision_id': f'dec-{i}',
                'action': 'write_test',
                'outcome': 'failure',  # All failures
                'context': {'situation_type': 'error', 'task_type': 'test'}
            }
            for i in range(10)
        ]
        
        patterns = self.recognizer.recognize_patterns(decisions)
        
        # Should recognize failure patterns
        failure_patterns = [p for p in patterns if p.pattern_type == 'failure']
        self.assertGreater(len(failure_patterns), 0)
        
        # Check failure patterns have low success rate
        pattern = failure_patterns[0]
        self.assertLessEqual(pattern.success_rate, self.recognizer.failure_threshold)
    
    def test_recognize_patterns_with_insufficient_data(self):
        """Test pattern recognition with insufficient data"""
        # Only 2 decisions (below min_frequency of 3)
        decisions = [
            {
                'decision_id': f'dec-{i}',
                'action': 'write_test',
                'outcome': 'success',
                'context': {'situation_type': 'normal'}
            }
            for i in range(2)
        ]
        
        patterns = self.recognizer.recognize_patterns(decisions)
        
        # Should return empty list or very few patterns
        self.assertLessEqual(len(patterns), 1)
    
    def test_predict_decision(self):
        """Test decision prediction"""
        # First, add some patterns
        decisions = [
            {
                'decision_id': f'dec-{i}',
                'action': 'write_test',
                'outcome': 'success',
                'context': {
                    'situation_type': 'normal',
                    'task_type': 'implementation'
                }
            }
            for i in range(10)
        ]
        
        self.recognizer.update_patterns(decisions)
        
        # Now predict for similar context
        context = {
            'situation_type': 'normal',
            'task_type': 'implementation'
        }
        
        prediction = self.recognizer.predict_decision(context)
        
        # Should get a prediction
        self.assertIsNotNone(prediction)
        self.assertIsNotNone(prediction.predicted_action)
        self.assertGreater(prediction.confidence, 0.0)
        self.assertGreater(prediction.expected_success_rate, 0.0)
        self.assertIsNotNone(prediction.reasoning)
    
    def test_predict_decision_no_patterns(self):
        """Test prediction when no patterns exist"""
        context = {
            'situation_type': 'unknown',
            'task_type': 'unknown'
        }
        
        prediction = self.recognizer.predict_decision(context)
        
        # Should return None when no patterns
        self.assertIsNone(prediction)
    
    def test_predict_decision_with_sufficient_data(self):
        """Test prediction with sufficient pattern data"""
        # Add patterns with sufficient frequency
        decisions = [
            {
                'decision_id': f'dec-{i}',
                'action': 'write_test',
                'outcome': 'success',
                'context': {'situation_type': 'normal', 'task_type': 'implementation'}
            }
            for i in range(10)
        ]
        
        self.recognizer.update_patterns(decisions)
        
        # Predict for similar context
        context = {
            'situation_type': 'normal',
            'task_type': 'implementation'
        }
        
        prediction = self.recognizer.predict_decision(context)
        
        # Should return prediction with high confidence
        self.assertIsNotNone(prediction)
        self.assertGreater(prediction.confidence, 0.5)
        self.assertEqual(prediction.predicted_action, 'write_test')
    
    def test_update_patterns(self):
        """Test updating patterns with new decisions"""
        # Add initial patterns
        decisions1 = [
            {
                'decision_id': f'dec-{i}',
                'action': 'write_test',
                'outcome': 'success',
                'context': {'situation_type': 'normal'}
            }
            for i in range(10)
        ]
        
        self.recognizer.update_patterns(decisions1)
        
        # Add new decisions
        decisions2 = [
            {
                'decision_id': f'dec-{i+10}',
                'action': 'run_tests',
                'outcome': 'success',
                'context': {'situation_type': 'normal'}
            }
            for i in range(5)
        ]
        
        self.recognizer.update_patterns(decisions2)
        
        # Check patterns are updated
        stats = self.recognizer.get_pattern_statistics()
        self.assertGreater(stats['total_patterns'], 0)
    
    def test_save_and_update_pattern(self):
        """Test saving and updating a pattern"""
        pattern = DecisionPattern(
            pattern_id='test-pattern-1',
            pattern_type='sequence',
            pattern={'sequence': ['action1', 'action2']},
            success_rate=0.8,
            frequency=5,
            confidence=0.7,
            created_at='2024-01-01T00:00:00Z',
            updated_at='2024-01-01T00:00:00Z'
        )
        
        # Save pattern
        self.recognizer._save_or_update_pattern(pattern)
        
        # Update pattern with new frequency
        pattern.frequency = 10
        pattern.success_rate = 0.85
        pattern.updated_at = datetime.utcnow().isoformat()
        
        self.recognizer._save_or_update_pattern(pattern)
        
        # Verify update
        import sqlite3
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT frequency, success_rate FROM patterns WHERE pattern_id = ?',
                ('test-pattern-1',)
            )
            result = cursor.fetchone()
            
            self.assertEqual(result[0], 10)  # Updated frequency
            self.assertEqual(result[1], 0.85)  # Updated success rate
    
    def test_get_relevant_patterns(self):
        """Test getting relevant patterns"""
        # Add patterns
        decisions = [
            {
                'decision_id': f'dec-{i}',
                'action': 'write_test',
                'outcome': 'success',
                'context': {'situation_type': 'normal', 'task_type': 'test'}
            }
            for i in range(10)
        ]
        
        self.recognizer.update_patterns(decisions)
        
        # Get relevant patterns
        context = {'situation_type': 'normal', 'task_type': 'test'}
        patterns = self.recognizer._get_relevant_patterns(context)
        
        # Should return some patterns
        self.assertGreater(len(patterns), 0)
        self.assertLessEqual(len(patterns), 100)  # Should limit to 100
    
    def test_get_pattern_statistics(self):
        """Test getting pattern statistics"""
        # Add patterns
        decisions = [
            {
                'decision_id': f'dec-{i}',
                'action': 'write_test',
                'outcome': 'success',
                'context': {'situation_type': 'normal'}
            }
            for i in range(10)
        ]
        
        self.recognizer.update_patterns(decisions)
        
        # Get statistics
        stats = self.recognizer.get_pattern_statistics()
        
        # Check statistics structure
        self.assertIn('total_patterns', stats)
        self.assertIn('patterns_by_type', stats)
        self.assertIn('average_success_rate_by_type', stats)
        self.assertIn('min_pattern_frequency', stats)
        self.assertIn('success_threshold', stats)
        self.assertIn('failure_threshold', stats)
        
        # Check values
        self.assertGreater(stats['total_patterns'], 0)
        self.assertEqual(stats['min_pattern_frequency'], 3)
        self.assertEqual(stats['success_threshold'], 0.7)
        self.assertEqual(stats['failure_threshold'], 0.3)
    
    def test_get_patterns_by_type(self):
        """Test getting patterns by type"""
        # Add patterns
        decisions = [
            {
                'decision_id': f'dec-{i}',
                'action': 'write_test',
                'outcome': 'success',
                'context': {'situation_type': 'normal'}
            }
            for i in range(10)
        ]
        
        self.recognizer.update_patterns(decisions)
        
        # Get context patterns
        context_patterns = self.recognizer.get_patterns_by_type('context', limit=10)
        
        # Should return context patterns
        self.assertGreater(len(context_patterns), 0)
        self.assertLessEqual(len(context_patterns), 10)
        
        # All should be context type
        for pattern in context_patterns:
            self.assertEqual(pattern.pattern_type, 'context')
    
    def test_cleanup_old_patterns(self):
        """Test cleanup of old patterns"""
        # Add pattern with low confidence
        pattern = DecisionPattern(
            pattern_id='low-confidence-pattern',
            pattern_type='sequence',
            pattern={'sequence': ['action1']},
            success_rate=0.5,
            frequency=2,
            confidence=0.2,  # Low confidence
            created_at='2024-01-01T00:00:00Z',
            updated_at='2024-01-01T00:00:00Z'
        )
        
        self.recognizer._save_or_update_pattern(pattern)
        
        # Run cleanup
        self.recognizer._cleanup_old_patterns()
        
        # Verify low confidence pattern is deleted
        import sqlite3
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT COUNT(*) FROM patterns WHERE pattern_id = ?',
                ('low-confidence-pattern',)
            )
            count = cursor.fetchone()[0]
            self.assertEqual(count, 0)
    
    def test_extract_frequent_sequences(self):
        """Test extraction of frequent sequences"""
        actions = ['A', 'B', 'C', 'A', 'B', 'C', 'A', 'B', 'C']
        
        sequences = self.recognizer._extract_frequent_sequences(actions, 2)
        
        # Should find 'A->B' and 'B->C' sequences
        self.assertIn(('A', 'B'), sequences)
        self.assertIn(('B', 'C'), sequences)
        self.assertEqual(sequences[('A', 'B')], 3)
        self.assertEqual(sequences[('B', 'C')], 3)
    
    def test_calculate_success_rate(self):
        """Test success rate calculation"""
        decisions = [
            {'outcome': 'success'},
            {'outcome': 'success'},
            {'outcome': 'failure'},
            {'outcome': 'success'},
            {'outcome': 'failure'}
        ]
        
        success_rate = self.recognizer._calculate_success_rate(decisions)
        
        # Should be 3/5 = 0.6
        self.assertEqual(success_rate, 0.6)
    
    def test_extract_context_key(self):
        """Test context key extraction"""
        context1 = {
            'situation_type': 'normal',
            'task_type': 'implementation',
            'error_type': None
        }
        
        key1 = self.recognizer._extract_context_key(context1)
        self.assertEqual(key1, 'situation:normal|task:implementation')
        
        # Empty context
        context2 = {}
        key2 = self.recognizer._extract_context_key(context2)
        self.assertIsNone(key2)
    
    def test_has_feature(self):
        """Test feature checking"""
        decision = {
            'context': {
                'situation_type': 'normal',
                'task_type': 'test',
                'error_type': None
            },
            'action': 'write_test'
        }
        
        # Should match
        self.assertTrue(self.recognizer._has_feature(decision, 'situation:normal'))
        self.assertTrue(self.recognizer._has_feature(decision, 'task:test'))
        self.assertTrue(self.recognizer._has_feature(decision, 'action:write_test'))
        
        # Should not match
        self.assertFalse(self.recognizer._has_feature(decision, 'situation:error'))
        self.assertFalse(self.recognizer._has_feature(decision, 'action:run_tests'))
    
    def test_calculate_pattern_relevance(self):
        """Test pattern relevance calculation"""
        pattern = DecisionPattern(
            pattern_id='test-pattern',
            pattern_type='context',
            pattern={'context_key': 'situation:normal'},
            success_rate=0.8,
            frequency=5,
            confidence=0.75,
            created_at='2024-01-01T00:00:00Z',
            updated_at='2024-01-01T00:00:00Z',
            context_filter={'context_key': 'situation:normal'}
        )
        
        context = {'situation_type': 'normal', 'task_type': 'test'}
        
        relevance = self.recognizer._calculate_pattern_relevance(pattern, context)
        
        # Should have positive relevance
        self.assertGreater(relevance, 0.0)
        self.assertLessEqual(relevance, 1.0)
    
    def test_extract_action_from_pattern(self):
        """Test action extraction from pattern"""
        # Sequence pattern
        pattern1 = DecisionPattern(
            pattern_id='seq-pattern',
            pattern_type='sequence',
            pattern={'sequence': ['action1', 'action2', 'action3']},
            success_rate=0.8,
            frequency=5,
            confidence=0.7,
            created_at='2024-01-01T00:00:00Z',
            updated_at='2024-01-01T00:00:00Z'
        )
        
        action1 = self.recognizer._extract_action_from_pattern(pattern1)
        self.assertEqual(action1, 'action3')
        
        # Context pattern
        pattern2 = DecisionPattern(
            pattern_id='ctx-pattern',
            pattern_type='context',
            pattern={'context_key': 'situation:normal', 'most_common_action': 'write_test'},
            success_rate=0.8,
            frequency=5,
            confidence=0.7,
            created_at='2024-01-01T00:00:00Z',
            updated_at='2024-01-01T00:00:00Z'
        )
        
        action2 = self.recognizer._extract_action_from_pattern(pattern2)
        self.assertEqual(action2, 'write_test')
    
    def test_generate_reasoning(self):
        """Test reasoning generation"""
        pattern = DecisionPattern(
            pattern_id='test-pattern',
            pattern_type='context',
            pattern={
                'context_key': 'situation:normal|task:test',
                'most_common_action': 'write_test'
            },
            success_rate=0.85,
            frequency=10,
            confidence=0.8,
            created_at='2024-01-01T00:00:00Z',
            updated_at='2024-01-01T00:00:00Z'
        )
        
        context = {'situation_type': 'normal', 'task_type': 'test'}
        
        reasoning = self.recognizer._generate_reasoning(pattern, context)
        
        # Should contain relevant information
        self.assertIn('85.0%', reasoning)  # Success rate
        self.assertIn('80.0%', reasoning)  # Confidence
        self.assertIn('situation:normal|task:test', reasoning)  # Context
    
    def test_thread_safety(self):
        """Test thread safety of pattern operations"""
        import threading
        
        decisions = [
            {
                'decision_id': f'dec-{i}',
                'action': 'write_test',
                'outcome': 'success',
                'context': {'situation_type': 'normal'}
            }
            for i in range(20)
        ]
        
        # Update patterns from multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=self.recognizer.update_patterns, args=(decisions,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Should not have errors
        stats = self.recognizer.get_pattern_statistics()
        self.assertGreater(stats['total_patterns'], 0)


class TestPatternRecognitionIntegration(unittest.TestCase):
    """Integration tests for pattern recognition workflow"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, 'test_patterns.db')
        self.recognizer = PatternRecognizer(db_path=self.db_path)
    
    def tearDown(self):
        """Clean up test environment"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_full_pattern_recognition_workflow(self):
        """Test complete pattern recognition and prediction workflow"""
        # Phase 1: Add decisions and recognize patterns
        decisions = [
            {
                'decision_id': f'dec-{i}',
                'action': f'action_{i % 4}',
                'outcome': 'success' if i % 3 != 0 else 'failure',
                'context': {
                    'situation_type': 'normal' if i % 2 == 0 else 'error',
                    'task_type': 'implementation'
                }
            }
            for i in range(30)
        ]
        
        self.recognizer.update_patterns(decisions)
        
        # Phase 2: Check patterns are recognized
        stats = self.recognizer.get_pattern_statistics()
        self.assertGreater(stats['total_patterns'], 0)
        
        # Phase 3: Predict decisions
        context = {'situation_type': 'normal', 'task_type': 'implementation'}
        prediction = self.recognizer.predict_decision(context)
        
        # Phase 4: Verify prediction
        if prediction:
            self.assertIsNotNone(prediction.predicted_action)
            self.assertGreater(prediction.confidence, 0.0)
            self.assertIsNotNone(prediction.reasoning)
    
    def test_pattern_evolution_over_time(self):
        """Test how patterns evolve as new decisions are added"""
        # Initial decisions
        decisions_v1 = [
            {
                'decision_id': f'dec-{i}',
                'action': 'action_A',
                'outcome': 'success',
                'context': {'situation_type': 'normal'}
            }
            for i in range(10)
        ]
        
        self.recognizer.update_patterns(decisions_v1)
        stats_v1 = self.recognizer.get_pattern_statistics()
        
        # Add new decisions with different behavior
        decisions_v2 = [
            {
                'decision_id': f'dec-{i+10}',
                'action': 'action_B',
                'outcome': 'success',
                'context': {'situation_type': 'normal'}
            }
            for i in range(10)
        ]
        
        self.recognizer.update_patterns(decisions_v2)
        stats_v2 = self.recognizer.get_pattern_statistics()
        
        # Should have more patterns after adding more data
        self.assertGreaterEqual(stats_v2['total_patterns'], stats_v1['total_patterns'])
    
    def test_different_pattern_types_recognition(self):
        """Test recognition of all pattern types"""
        decisions = []
        
        # Add successful decisions
        for i in range(30):
            decisions.append({
                'decision_id': f'dec-success-{i}',
                'action': f'action_{i % 3}',
                'outcome': 'success',
                'context': {
                    'situation_type': 'normal' if i % 3 == 0 else 'error',
                    'task_type': 'test' if i % 2 == 0 else 'implementation'
                }
            })
        
        # Add failed decisions with consistent pattern
        for i in range(15):
            decisions.append({
                'decision_id': f'dec-fail-{i}',
                'action': 'action_fail',  # Consistent failing action
                'outcome': 'failure',
                'context': {
                    'situation_type': 'error',  # Consistent error context
                    'task_type': 'implementation'
                }
            })
        
        self.recognizer.update_patterns(decisions)
        
        # Check all pattern types are recognized
        sequence_patterns = self.recognizer.get_patterns_by_type('sequence', limit=10)
        context_patterns = self.recognizer.get_patterns_by_type('context', limit=10)
        success_patterns = self.recognizer.get_patterns_by_type('success', limit=10)
        failure_patterns = self.recognizer.get_patterns_by_type('failure', limit=10)
        
        # Should have patterns of each type
        self.assertGreater(len(sequence_patterns), 0)
        self.assertGreater(len(context_patterns), 0)
        self.assertGreater(len(success_patterns), 0)
        self.assertGreater(len(failure_patterns), 0)


if __name__ == '__main__':
    unittest.main()