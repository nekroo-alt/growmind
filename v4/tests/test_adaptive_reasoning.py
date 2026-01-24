"""
Comprehensive test suite for V4 Adaptive Reasoning System

This test suite validates all V4 components:
- Context hierarchy management
- Reasoning engine components
- Strategy selection and switching
- Progress tracking and validation
- Trap detection and recovery
- Meta-cognition and learning
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
import sqlite3
import json
from datetime import datetime, timedelta

# Import V4 components
from v3.data.context_hierarchy import ContextHierarchyManager
from v3.logic.context_expander import ContextExpander
from v3.logic.context_scorer import ContextScorer
from v3.logic.context_summarizer import ContextSummarizer
from v3.logic.reasoning_engine import ReasoningEngine
from v3.logic.context_analyzer import ContextAnalyzer
from v3.logic.decision_maker import DecisionMaker
from v3.logic.action_validator import ActionValidator
from v3.logic.strategy_selector import StrategySelector
from v3.logic.strategy_evaluator import StrategyEvaluator
from v3.logic.strategy_switcher import StrategySwitcher
from v3.logic.strategy_hybridizer import StrategyHybridizer
from v3.logic.progress_tracker import ProgressTracker
from v3.logic.progress_predictor import ProgressPredictor
from v3.logic.trap_detector import TrapDetector
from v3.logic.trap_recovery import TrapRecovery
from v3.logic.trap_prevention import TrapPrevention
from v3.logic.pattern_recognizer import PatternRecognizer
from v3.logic.self_reflection import SelfReflection
from v3.logic.lesson_learner import LessonLearner
from v3.logic.adaptive_heuristics import AdaptiveHeuristics
from v3.logic.explanation_generator import ExplanationGenerator
from v3.data.decision_history import DecisionHistory
from v3.data.decision_tracer import DecisionTracer


class TestContextHierarchy:
    """Test context hierarchy management"""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def context_hierarchy(self, temp_dir):
        """Create context hierarchy manager"""
        db_path = Path(temp_dir) / "context_hierarchy.db"
        return ContextHierarchyManager(db_path=str(db_path))
    
    def test_context_hierarchy_initialization(self, context_hierarchy):
        """Test context hierarchy manager initialization"""
        assert context_hierarchy is not None
        assert hasattr(context_hierarchy, 'get_context')
        assert hasattr(context_hierarchy, 'get_current_action')
    
    def test_store_and_retrieve_l0_context(self, context_hierarchy):
        """Test storing and retrieving L0 (immediate) context"""
        context = {
            'action': 'test_action',
            'state': {'status': 'in_progress'},
            'error': None
        }
        context_hierarchy.store_context('L0', context)
        
        retrieved = context_hierarchy.get_context('L0')
        assert retrieved is not None
        assert retrieved['action'] == 'test_action'
    
    def test_store_and_retrieve_l1_context(self, context_hierarchy):
        """Test storing and retrieving L1 (recent) context"""
        context = {
            'recent_actions': ['action1', 'action2'],
            'recent_errors': ['error1'],
            'recent_telemetry': {'tokens': 100}
        }
        context_hierarchy.store_context('L1', context)
        
        retrieved = context_hierarchy.get_context('L1')
        assert retrieved is not None
        assert len(retrieved['recent_actions']) == 2
    
    def test_context_caching(self, context_hierarchy):
        """Test context caching mechanism"""
        context = {'test': 'data'}
        context_hierarchy.store_context('L0', context)
        
        # First retrieval should cache
        first = context_hierarchy.get_context('L0')
        # Second retrieval should come from cache
        second = context_hierarchy.get_context('L0')
        
        assert first == second
    
    def test_context_expiration(self, context_hierarchy):
        """Test TTL-based context expiration"""
        # Store L0 context with short TTL
        context = {'action': 'test'}
        context_hierarchy.store_context('L0', context, ttl=1)
        
        # Should be retrievable immediately
        retrieved = context_hierarchy.get_context('L0')
        assert retrieved is not None
        
        # Should expire after TTL
        # Note: This test would need to mock time for proper testing


class TestReasoningEngine:
    """Test adaptive reasoning engine"""
    
    @pytest.fixture
    def reasoning_engine(self):
        """Create reasoning engine with mocked components"""
        analyzer = Mock()
        decision_maker = Mock()
        validator = Mock()
        
        engine = ReasoningEngine(
            analyzer=analyzer,
            decision_maker=decision_maker,
            validator=validator
        )
        return engine
    
    def test_reasoning_pipeline(self, reasoning_engine):
        """Test complete reasoning pipeline"""
        context = {'situation': 'normal'}
        
        # Mock the pipeline components
        reasoning_engine.analyzer.analyze.return_value = {
            'situation_type': 'normal',
            'confidence': 0.8
        }
        reasoning_engine.decision_maker.decide.return_value = {
            'action': 'test_action',
            'confidence': 0.85
        }
        reasoning_engine.validator.validate.return_value = {
            'success': True,
            'progress': 0.5
        }
        
        result = reasoning_engine.reason(context)
        
        assert result is not None
        assert result['action'] == 'test_action'
        assert reasoning_engine.analyzer.analyze.called
        assert reasoning_engine.decision_maker.decide.called
        assert reasoning_engine.validator.validate.called
    
    def test_reasoning_strategies(self, reasoning_engine):
        """Test different reasoning strategies"""
        for strategy in ['conservative', 'balanced', 'aggressive']:
            reasoning_engine.set_strategy(strategy)
            assert reasoning_engine.current_strategy == strategy
    
    def test_reasoning_error_handling(self, reasoning_engine):
        """Test error handling in reasoning"""
        reasoning_engine.analyzer.analyze.side_effect = Exception("Analysis failed")
        
        with pytest.raises(Exception):
            reasoning_engine.reason({})


class TestContextAnalyzer:
    """Test context analyzer for situation assessment"""
    
    @pytest.fixture
    def context_analyzer(self):
        """Create context analyzer"""
        return ContextAnalyzer()
    
    def test_situation_classification(self, context_analyzer):
        """Test situation classification"""
        # Test normal situation
        context = {'errors': [], 'complexity': 'low'}
        result = context_analyzer.analyze(context)
        assert result['situation_type'] == 'normal'
        
        # Test error situation
        context = {'errors': ['error1', 'error2'], 'complexity': 'high'}
        result = context_analyzer.analyze(context)
        assert result['situation_type'] == 'error'
    
    def test_feature_extraction(self, context_analyzer):
        """Test feature extraction from context"""
        context = {
            'errors': ['TypeError', 'ValueError'],
            'task_complexity': 0.8,
            'resources': {'tokens': 1000}
        }
        
        features = context_analyzer.extract_features(context)
        
        assert 'error_frequency' in features
        assert 'task_complexity' in features
        assert 'resource_availability' in features
    
    def test_confidence_estimation(self, context_analyzer):
        """Test confidence estimation"""
        context = {
            'past_success_rate': 0.9,
            'context_completeness': 0.95
        }
        
        confidence = context_analyzer.estimate_confidence(context)
        
        assert 0 <= confidence <= 1
        assert confidence > 0.8  # High confidence with good context


class TestDecisionMaker:
    """Test decision maker for action selection"""
    
    @pytest.fixture
    def decision_maker(self):
        """Create decision maker"""
        return DecisionMaker()
    
    def test_action_selection(self, decision_maker):
        """Test action selection based on context"""
        alternatives = [
            {'action': 'action1', 'success_prob': 0.7, 'cost': 10},
            {'action': 'action2', 'success_prob': 0.9, 'cost': 15},
            {'action': 'action3', 'success_prob': 0.6, 'cost': 5}
        ]
        
        selected = decision_maker.select_action(alternatives)
        
        assert selected is not None
        assert selected['action'] in ['action1', 'action2', 'action3']
    
    def test_decision_strategies(self, decision_maker):
        """Test different decision strategies"""
        alternatives = [
            {'action': 'safe', 'success_prob': 0.95, 'cost': 20},
            {'action': 'risky', 'success_prob': 0.6, 'cost': 5}
        ]
        
        # Greedy strategy should choose risky
        greedy = decision_maker.select_action(alternatives, strategy='greedy')
        assert greedy['cost'] < 15
        
        # Safe strategy should choose safe
        safe = decision_maker.select_action(alternatives, strategy='safe')
        assert safe['success_prob'] > 0.8
    
    def test_decision_confidence(self, decision_maker):
        """Test confidence estimation for decisions"""
        alternatives = [
            {'action': 'test', 'success_prob': 0.8, 'cost': 10}
        ]
        
        result = decision_maker.select_action(alternatives)
        
        assert 'confidence' in result
        assert 0 <= result['confidence'] <= 1


class TestActionValidator:
    """Test action validator for result verification"""
    
    @pytest.fixture
    def action_validator(self):
        """Create action validator"""
        return ActionValidator()
    
    def test_goal_achievement_validation(self, action_validator):
        """Test goal achievement validation"""
        action = {'action': 'create_file'}
        result = {'file_created': True}
        goal = {'goal': 'create_file'}
        
        validation = action_validator.validate(action, result, goal)
        
        assert validation['goal_achieved'] == True
    
    def test_side_effect_detection(self, action_validator):
        """Test side effect detection"""
        action = {'action': 'modify_file'}
        result = {
            'file_modified': True,
            'unexpected_deletion': True
        }
        
        validation = action_validator.validate(action, result, {})
        
        assert validation['has_side_effects'] == True
    
    def test_progress_measurement(self, action_validator):
        """Test progress measurement"""
        before_state = {'progress': 0.3}
        after_state = {'progress': 0.6}
        
        progress = action_validator.measure_progress(before_state, after_state)
        
        assert progress == 0.3
    
    def test_validation_accuracy_tracking(self, action_validator):
        """Test validation accuracy tracking"""
        action_validator.record_validation(success=True)
        action_validator.record_validation(success=True)
        action_validator.record_validation(success=False)
        
        accuracy = action_validator.get_accuracy()
        
        assert accuracy == 2/3


class TestStrategySelector:
    """Test adaptive strategy selection"""
    
    @pytest.fixture
    def strategy_selector(self):
        """Create strategy selector"""
        return StrategySelector()
    
    def test_strategy_selection_by_situation(self, strategy_selector):
        """Test strategy selection based on situation type"""
        # Normal situation
        strategy = strategy_selector.select_strategy('normal')
        assert strategy in ['conservative', 'balanced', 'aggressive']
        
        # Error recovery
        strategy = strategy_selector.select_strategy('error')
        assert strategy == 'conservative'  # More conservative on errors
    
    def test_strategy_adaptation(self, strategy_selector):
        """Test strategy adaptation based on performance"""
        # Simulate poor performance with current strategy
        strategy_selector.record_performance('balanced', success_rate=0.5)
        
        # Should switch to different strategy
        new_strategy = strategy_selector.adapt_strategy('balanced')
        assert new_strategy != 'balanced'
    
    def test_strategy_switching(self, strategy_selector):
        """Test strategy switching triggers"""
        # Simulate repeated failures
        for _ in range(5):
            strategy_selector.record_failure('balanced')
        
        should_switch = strategy_selector.should_switch('balanced')
        
        assert should_switch == True


class TestProgressTracker:
    """Test progress tracking and validation"""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def progress_tracker(self, temp_dir):
        """Create progress tracker"""
        db_path = Path(temp_dir) / "progress.db"
        return ProgressTracker(db_path=str(db_path))
    
    def test_progress_tracking(self, progress_tracker):
        """Test progress tracking"""
        task_id = 1
        progress_tracker.start_tracking(task_id)
        
        metrics = {'lines_added': 10, 'tests_passing': 5}
        progress_tracker.update_progress(task_id, metrics)
        
        report = progress_tracker.get_report(task_id)
        
        assert report is not None
        assert report['lines_added'] == 10
        assert report['tests_passing'] == 5
    
    def test_stagnation_detection(self, progress_tracker):
        """Test stagnation detection"""
        task_id = 1
        progress_tracker.start_tracking(task_id)
        
        # Simulate no progress
        for _ in range(6):
            progress_tracker.update_progress(task_id, {'lines_added': 0})
        
        is_stagnant = progress_tracker.check_stagnation(task_id)
        
        assert is_stagnant == True
    
    def test_regression_detection(self, progress_tracker):
        """Test regression detection"""
        task_id = 1
        progress_tracker.start_tracking(task_id)
        
        progress_tracker.update_progress(task_id, {'lines_added': 10})
        progress_tracker.update_progress(task_id, {'lines_added': 5})  # Regression
        
        has_regression = progress_tracker.check_regression(task_id)
        
        assert has_regression == True
    
    def test_progress_validation(self, progress_tracker):
        """Test progress validation against thresholds"""
        task_id = 1
        progress_tracker.start_tracking(task_id, expected_rate=0.3)
        
        # Adequate progress
        progress_tracker.update_progress(task_id, {'completion': 0.4})
        is_adequate = progress_tracker.check_progress(task_id)
        
        assert is_adequate == True


class TestProgressPredictor:
    """Test progress prediction"""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def progress_predictor(self, temp_dir):
        """Create progress predictor"""
        db_path = Path(temp_dir) / "predictor.db"
        return ProgressPredictor(db_path=str(db_path))
    
    def test_time_prediction(self, progress_predictor):
        """Test time to completion prediction"""
        task_id = 1
        current_progress = 0.5
        progress_rate = 0.1
        
        prediction = progress_predictor.predict_completion_time(
            task_id, current_progress, progress_rate
        )
        
        assert prediction['estimated_time'] > 0
        assert 'confidence' in prediction
    
    def test_resource_prediction(self, progress_predictor):
        """Test resource prediction"""
        task_id = 1
        current_tokens = 1000
        progress_rate = 0.1
        
        prediction = progress_predictor.predict_resources(
            task_id, current_tokens, progress_rate
        )
        
        assert prediction['estimated_tokens'] > 1000
    
    def test_success_probability_prediction(self, progress_predictor):
        """Test success probability prediction"""
        task_id = 1
        context = {'past_success_rate': 0.8, 'complexity': 'medium'}
        
        prediction = progress_predictor.predict_success(task_id, context)
        
        assert 0 <= prediction['probability'] <= 1


class TestTrapDetector:
    """Test trap detection"""
    
    @pytest.fixture
    def trap_detector(self):
        """Create trap detector"""
        return TrapDetector()
    
    def test_exact_loop_detection(self, trap_detector):
        """Test exact action loop detection"""
        actions = ['action1', 'action1', 'action1']
        
        loops = trap_detector.detect_exact_action_loop(actions)
        
        assert loops is not None
        assert loops['detected'] == True
        assert loops['count'] >= 3
    
    def test_similar_pattern_detection(self, trap_detector):
        """Test similar action pattern detection"""
        actions = [
            {'type': 'modify', 'file': 'test.py'},
            {'type': 'modify', 'file': 'test.py'},
            {'type': 'modify', 'file': 'test.py'}
        ]
        
        loops = trap_detector.detect_similar_action_pattern(actions)
        
        assert loops is not None
        assert loops['detected'] == True
    
    def test_dead_end_detection(self, trap_detector):
        """Test dead end detection"""
        progress_history = [0.1, 0.1, 0.1, 0.1, 0.1]  # No progress
        
        dead_end = trap_detector.detect_dead_end_no_progress(progress_history)
        
        assert dead_end is not None
        assert dead_end['detected'] == True
    
    def test_circular_reasoning_detection(self, trap_detector):
        """Test circular reasoning detection"""
        decisions = [
            {'id': 1, 'reason': 'A because B', 'dependencies': [2]},
            {'id': 2, 'reason': 'B because C', 'dependencies': [3]},
            {'id': 3, 'reason': 'C because A', 'dependencies': [1]}
        ]
        
        circular = trap_detector.detect_circular_reasoning(decisions)
        
        assert circular is not None
        assert circular['detected'] == True


class TestTrapRecovery:
    """Test trap recovery"""
    
    @pytest.fixture
    def trap_recovery(self):
        """Create trap recovery"""
        return TrapRecovery()
    
    def test_loop_recovery(self, trap_recovery):
        """Test loop recovery"""
        trap = {'type': 'infinite_loop', 'action': 'test_action'}
        
        recovery = trap_recovery.recover(trap)
        
        assert recovery['success'] == True
        assert recovery['strategy'] in ['break_loop_change_approach', 
                                       'backtrack_to_checkpoint',
                                       'try_different_strategy']
    
    def test_dead_end_recovery(self, trap_recovery):
        """Test dead end recovery"""
        trap = {'type': 'dead_end', 'reason': 'no_progress'}
        
        recovery = trap_recovery.recover(trap)
        
        assert recovery['success'] == True
        assert 'alternative_approach' in recovery
    
    def test_recovery_validation(self, trap_recovery):
        """Test recovery validation"""
        trap = {'type': 'test_trap'}
        
        # Simulate recovery
        recovery = trap_recovery.recover(trap)
        recovery['success'] = True
        
        # Validate recovery
        validation = trap_recovery.validate_recovery(recovery)
        
        assert validation['valid'] == recovery['success']


class TestTrapPrevention:
    """Test trap prevention"""
    
    @pytest.fixture
    def trap_prevention(self):
        """Create trap prevention"""
        return TrapPrevention()
    
    def test_loop_prevention(self, trap_prevention):
        """Test loop prevention"""
        action = 'test_action'
        
        # First attempt
        can_proceed = trap_prevention.check_action(action)
        assert can_proceed == True
        
        # Second attempt - warn
        can_proceed = trap_prevention.check_action(action)
        assert can_proceed == True
        
        # Third attempt - block
        can_proceed = trap_prevention.check_action(action)
        assert can_proceed == False
    
    def test_progress_validation_prevention(self, trap_prevention):
        """Test progress validation for dead end prevention"""
        progress = 0.05  # Below threshold
        
        can_proceed = trap_prevention.validate_progress(progress, threshold=0.1)
        
        assert can_proceed == False
        assert 'warning' in trap_prevention.get_status()


class TestPatternRecognizer:
    """Test pattern recognition"""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def pattern_recognizer(self, temp_dir):
        """Create pattern recognizer"""
        db_path = Path(temp_dir) / "patterns.db"
        return PatternRecognizer(db_path=str(db_path))
    
    def test_decision_pattern_recognition(self, pattern_recognizer):
        """Test decision pattern recognition"""
        decisions = [
            {'context': {'error': 'test'}, 'action': 'retry', 'outcome': 'success'},
            {'context': {'error': 'test'}, 'action': 'retry', 'outcome': 'success'},
            {'context': {'error': 'test'}, 'action': 'retry', 'outcome': 'success'}
        ]
        
        pattern = pattern_recognizer.recognize_pattern(decisions)
        
        assert pattern is not None
        assert pattern['pattern_type'] == 'decision_pattern'
        assert pattern['frequency'] >= 3
    
    def test_success_pattern_identification(self, pattern_recognizer):
        """Test success pattern identification"""
        pattern = {
            'pattern': 'test_pattern',
            'success_rate': 0.9
        }
        
        pattern_recognizer.record_pattern(pattern)
        
        success_patterns = pattern_recognizer.get_success_patterns()
        
        assert len(success_patterns) > 0
        assert success_patterns[0]['success_rate'] > 0.8
    
    def test_pattern_prediction(self, pattern_recognizer):
        """Test pattern-based prediction"""
        context = {'error': 'test', 'complexity': 'low'}
        
        # Train on successful patterns
        for _ in range(5):
            pattern_recognizer.record_pattern({
                'context': context,
                'action': 'retry',
                'outcome': 'success'
            })
        
        prediction = pattern_recognizer.predict(context)
        
        assert prediction is not None
        assert 'recommended_action' in prediction


class TestSelfReflection:
    """Test self-reflection mechanism"""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def self_reflection(self, temp_dir):
        """Create self-reflection"""
        db_path = Path(temp_dir) / "reflection.db"
        return SelfReflection(db_path=str(db_path))
    
    def test_reflection_perform(self, self_reflection):
        """Test performing self-reflection"""
        decisions = [
            {'action': 'test1', 'outcome': 'success'},
            {'action': 'test2', 'outcome': 'failure'},
            {'action': 'test3', 'outcome': 'success'}
        ]
        
        reflection = self_reflection.perform_reflection(decisions)
        
        assert reflection is not None
        assert 'summary' in reflection
        assert 'insights' in reflection
        assert 'recommendations' in reflection
    
    def test_pattern_identification(self, self_reflection):
        """Test pattern identification in reflection"""
        decisions = [
            {'action': 'retry', 'outcome': 'success'},
            {'action': 'retry', 'outcome': 'success'},
            {'action': 'retry', 'outcome': 'success'}
        ]
        
        reflection = self_reflection.perform_reflection(decisions)
        
        assert 'patterns' in reflection
        assert len(reflection['patterns']) > 0
    
    def test_reflection_generation(self, self_reflection):
        """Test reflection report generation"""
        reflection = self_reflection.generate_report()
        
        assert reflection is not None
        assert 'performance_summary' in reflection
        assert 'key_insights' in reflection
        assert 'action_items' in reflection


class TestLessonLearner:
    """Test learning from mistakes"""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def lesson_learner(self, temp_dir):
        """Create lesson learner"""
        db_path = Path(temp_dir) / "lessons.db"
        return LessonLearner(db_path=str(db_path))
    
    def test_failure_recording(self, lesson_learner):
        """Test failure recording"""
        failure = {
            'action': 'test_action',
            'error': 'test_error',
            'context': {'situation': 'test'}
        }
        
        lesson_learner.record_failure(failure)
        
        failures = lesson_learner.get_failures()
        
        assert len(failures) == 1
        assert failures[0]['action'] == 'test_action'
    
    def test_root_cause_analysis(self, lesson_learner):
        """Test root cause analysis"""
        failure = {
            'action': 'test_action',
            'error': 'TypeError',
            'context': {'variable_type': 'string', 'expected_type': 'int'}
        }
        
        root_cause = lesson_learner.analyze_root_cause(failure)
        
        assert root_cause is not None
        assert 'cause' in root_cause
        assert 'prevention' in root_cause
    
    def test_lesson_extraction(self, lesson_learner):
        """Test lesson extraction from failures"""
        failure = {
            'action': 'test_action',
            'error': 'test_error',
            'context': {}
        }
        
        lesson_learner.record_failure(failure)
        lesson = lesson_learner.extract_lesson(failure)
        
        assert lesson is not None
        assert 'lesson' in lesson
        assert 'prevention' in lesson
    
    def test_lesson_application(self, lesson_learner):
        """Test lesson application"""
        lesson = {
            'lesson': 'test_lesson',
            'context_pattern': {'error': 'test_error'},
            'prevention': 'do_something_else'
        }
        
        lesson_learner.apply_lesson(lesson)
        
        context = {'error': 'test_error'}
        applicable = lesson_learner.check_lessons(context)
        
        assert applicable is not None
        assert len(applicable) > 0
    
    def test_mistake_reduction_tracking(self, lesson_learner):
        """Test mistake reduction tracking"""
        # Record failures
        for _ in range(5):
            lesson_learner.record_failure({
                'error': 'test_error',
                'timestamp': datetime.now() - timedelta(days=1)
            })
        
        # Record success after learning
        lesson_learner.record_success('test_error')
        
        metrics = lesson_learner.get_mistake_reduction_metrics()
        
        assert 'reduction_rate' in metrics
        assert metrics['reduction_rate'] >= 0


class TestAdaptiveHeuristics:
    """Test adaptive heuristics"""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def adaptive_heuristics(self, temp_dir):
        """Create adaptive heuristics"""
        db_path = Path(temp_dir) / "heuristics.db"
        return AdaptiveHeuristics(db_path=str(db_path))
    
    def test_heuristic_initialization(self, adaptive_heuristics):
        """Test heuristic initialization with baseline values"""
        heuristics = adaptive_heuristics.get_heuristics()
        
        assert 'decision_weights' in heuristics
        assert 'validation_thresholds' in heuristics
        assert 'context_levels' in heuristics
    
    def test_weight_learning(self, adaptive_heuristics):
        """Test learning optimal weights"""
        # Simulate performance data
        for i in range(10):
            adaptive_heuristics.record_performance({
                'weights': {'success': 0.5, 'cost': 0.3, 'risk': 0.2},
                'success': i < 7  # 70% success rate
            })
        
        # Learn optimal weights
        optimal_weights = adaptive_heuristics.learn_weights()
        
        assert optimal_weights is not None
        assert 'success' in optimal_weights
        assert optimal_weights['success'] > 0.4  # Higher weight for success
    
    def test_threshold_learning(self, adaptive_heuristics):
        """Test learning optimal thresholds"""
        # Simulate performance data
        for threshold in [0.1, 0.2, 0.3, 0.4, 0.5]:
            adaptive_heuristics.record_performance({
                'threshold': threshold,
                'success_rate': threshold * 2  # Higher threshold = higher success
            })
        
        # Learn optimal threshold
        optimal_threshold = adaptive_heuristics.learn_threshold('progress_threshold')
        
        assert optimal_threshold is not None
        assert 0.1 <= optimal_threshold <= 0.5
    
    def test_heuristic_update(self, adaptive_heuristics):
        """Test heuristic updates based on performance"""
        initial = adaptive_heuristics.get_heuristics()
        
        # Update heuristics
        adaptive_heuristics.update_heuristics({
            'decision_weights': {'success': 0.8, 'cost': 0.1, 'risk': 0.1}
        })
        
        updated = adaptive_heuristics.get_heuristics()
        
        assert updated['decision_weights']['success'] == 0.8
        assert updated['decision_weights']['success'] != initial['decision_weights']['success']
    
    def test_heuristic_quality_tracking(self, adaptive_heuristics):
        """Test heuristic quality tracking"""
        adaptive_heuristics.record_quality(success_rate=0.85, efficiency=0.9)
        
        quality = adaptive_heuristics.get_quality_metrics()
        
        assert 'success_rate' in quality
        assert 'efficiency' in quality
        assert quality['success_rate'] == 0.85


class TestExplanationGenerator:
    """Test decision explanation generation"""
    
    @pytest.fixture
    def explanation_generator(self):
        """Create explanation generator"""
        return ExplanationGenerator()
    
    def test_brief_explanation(self, explanation_generator):
        """Test brief explanation generation"""
        decision = {
            'action': 'create_test',
            'reasoning': 'Test coverage is low',
            'confidence': 0.9
        }
        
        explanation = explanation_generator.generate_brief(decision)
        
        assert explanation is not None
        assert len(explanation) < 200  # Brief
        assert 'create_test' in explanation
    
    def test_detailed_explanation(self, explanation_generator):
        """Test detailed explanation generation"""
        decision = {
            'action': 'create_test',
            'reasoning': 'Test coverage is low, needs improvement',
            'alternatives': [
                {'action': 'create_test', 'reason': 'improve coverage'},
                {'action': 'skip_test', 'reason': 'not critical', 'rejected': True}
            ],
            'confidence': 0.9
        }
        
        explanation = explanation_generator.generate_detailed(decision)
        
        assert explanation is not None
        assert len(explanation) > 200  # Detailed
        assert 'reasoning' in explanation
        assert 'alternatives' in explanation
    
    def test_technical_explanation(self, explanation_generator):
        """Test technical explanation generation"""
        decision = {
            'action': 'optimize_algorithm',
            'reasoning': 'Time complexity is O(n^2)',
            'metrics': {'time': 100, 'space': 50},
            'confidence': 0.95
        }
        
        explanation = explanation_generator.generate_technical(decision)
        
        assert explanation is not None
        assert 'O(n^2)' in explanation
        assert 'time' in explanation
    
    def test_audience_tailoring(self, explanation_generator):
        """Test explanation tailoring to audience"""
        decision = {'action': 'refactor', 'confidence': 0.9}
        
        # Developer explanation
        dev_exp = explanation_generator.generate_for_audience(
            decision, 'developer'
        )
        assert 'code' in dev_exp.lower() or 'refactor' in dev_exp.lower()
        
        # Manager explanation
        mgr_exp = explanation_generator.generate_for_audience(
            decision, 'manager'
        )
        assert 'benefit' in mgr_exp.lower() or 'improve' in mgr_exp.lower()


class TestDecisionHistory:
    """Test decision history tracking"""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def decision_history(self, temp_dir):
        """Create decision history"""
        db_path = Path(temp_dir) / "decisions.db"
        return DecisionHistory(db_path=str(db_path))
    
    def test_decision_recording(self, decision_history):
        """Test decision recording"""
        decision = {
            'context': {'situation': 'normal'},
            'reasoning': 'test reasoning',
            'action': 'test_action',
            'confidence': 0.8
        }
        
        decision_id = decision_history.record_decision(decision)
        
        assert decision_id is not None
        
        retrieved = decision_history.get_decision(decision_id)
        assert retrieved['action'] == 'test_action'
    
    def test_outcome_recording(self, decision_history):
        """Test outcome recording"""
        decision_id = decision_history.record_decision({
            'action': 'test',
            'confidence': 0.8
        })
        
        decision_history.record_outcome(
            decision_id,
            outcome='success',
            time_elapsed=1.5,
            resources={'tokens': 100}
        )
        
        decision = decision_history.get_decision(decision_id)
        
        assert decision['outcome'] == 'success'
        assert decision['time_elapsed'] == 1.5
        assert decision['resources']['tokens'] == 100
    
    def test_dependency_tracking(self, decision_history):
        """Test decision dependency tracking"""
        decision1_id = decision_history.record_decision({'action': 'test1'})
        decision2_id = decision_history.record_decision({'action': 'test2'})
        
        decision_history.record_dependency(decision2_id, decision1_id)
        
        decision2 = decision_history.get_decision(decision2_id)
        
        assert decision1_id in decision2['dependencies']
    
    def test_decision_graph(self, decision_history):
        """Test decision graph construction"""
        decision1_id = decision_history.record_decision({'action': 'test1'})
        decision2_id = decision_history.record_decision({'action': 'test2'})
        decision_history.record_dependency(decision2_id, decision1_id)
        
        graph = decision_history.get_decision_graph()
        
        assert graph is not None
        assert decision1_id in graph['nodes']
        assert decision2_id in graph['nodes']
        assert (decision1_id, decision2_id) in graph['edges']


class TestDecisionTracer:
    """Test decision trace logging"""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def decision_tracer(self, temp_dir):
        """Create decision tracer"""
        db_path = Path(temp_dir) / "traces.db"
        return DecisionTracer(db_path=str(db_path))
    
    def test_trace_logging(self, decision_tracer):
        """Test decision trace logging"""
        trace = {
            'decision_id': 'test_id',
            'reasoning_chain': [
                {'step': 1, 'thought': 'thought1', 'conclusion': 'conclusion1'},
                {'step': 2, 'thought': 'thought2', 'conclusion': 'conclusion2'}
            ],
            'alternatives': [
                {'action': 'alt1', 'reason_for_rejection': 'reason1'},
                {'action': 'alt2', 'reason_for_rejection': 'reason2'}
            ],
            'confidence': 0.85
        }
        
        decision_tracer.log_trace(trace)
        
        retrieved = decision_tracer.get_trace('test_id')
        
        assert retrieved is not None
        assert len(retrieved['reasoning_chain']) == 2
        assert len(retrieved['alternatives']) == 2
    
    def test_trace_search(self, decision_tracer):
        """Test trace search"""
        # Log multiple traces
        for i in range(3):
            decision_tracer.log_trace({
                'decision_id': f'decision_{i}',
                'action': f'action_{i}',
                'outcome': 'success' if i < 2 else 'failure',
                'confidence': 0.8
            })
        
        # Search by outcome
        successful = decision_tracer.search(outcome='success')
        
        assert len(successful) == 2
    
    def test_trace_export(self, decision_tracer):
        """Test trace export"""
        decision_tracer.log_trace({
            'decision_id': 'test_id',
            'action': 'test_action',
            'confidence': 0.8
        })
        
        exported = decision_tracer.export_traces(format='json')
        
        assert isinstance(exported, list)
        assert len(exported) > 0


class TestStrategyEvaluator:
    """Test strategy evaluation"""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def strategy_evaluator(self, temp_dir):
        """Create strategy evaluator"""
        db_path = Path(temp_dir) / "evaluation.db"
        return StrategyEvaluator(db_path=str(db_path))
    
    def test_performance_tracking(self, strategy_evaluator):
        """Test strategy performance tracking"""
        strategy = 'balanced'
        
        strategy_evaluator.track_performance(
            strategy,
            success=True,
            time_elapsed=1.5,
            resources={'tokens': 100}
        )
        
        metrics = strategy_evaluator.get_performance_metrics(strategy)
        
        assert metrics['success_rate'] == 1.0
        assert metrics['avg_time'] == 1.5
    
    def test_strategy_comparison(self, strategy_evaluator):
        """Test strategy comparison"""
        # Track performance for multiple strategies
        for strategy in ['conservative', 'balanced', 'aggressive']:
            for _ in range(5):
                strategy_evaluator.track_performance(
                    strategy,
                    success=True if strategy != 'aggressive' else False,
                    time_elapsed=2.0 if strategy == 'conservative' else 1.0,
                    resources={'tokens': 100}
                )
        
        comparison = strategy_evaluator.compare_strategies()
        
        assert len(comparison) == 3
        assert 'ranking' in comparison
    
    def test_strategy_ranking(self, strategy_evaluator):
        """Test strategy ranking"""
        # Track performance
        strategy_evaluator.track_performance('balanced', success=True, time_elapsed=1.0)
        strategy_evaluator.track_performance('conservative', success=True, time_elapsed=2.0)
        strategy_evaluator.track_performance('aggressive', success=False, time_elapsed=0.5)
        
        ranking = strategy_evaluator.rank_strategies()
        
        assert len(ranking) == 3
        # Balanced should rank higher than aggressive
        assert ranking.index('balanced') < ranking.index('aggressive')


class TestStrategySwitcher:
    """Test strategy switching"""
    
    @pytest.fixture
    def strategy_switcher(self):
        """Create strategy switcher"""
        return StrategySwitcher()
    
    def test_switch_detection(self, strategy_switcher):
        """Test switch condition detection"""
        # Simulate poor performance
        for _ in range(5):
            strategy_switcher.record_failure('balanced')
        
        should_switch = strategy_switcher.should_switch('balanced')
        
        assert should_switch == True
    
    def test_strategy_switch(self, strategy_switcher):
        """Test strategy execution"""
        current_strategy = 'balanced'
        reason = 'low_success_rate'
        
        new_strategy = strategy_switcher.switch_strategy(current_strategy, reason)
        
        assert new_strategy != current_strategy
        assert new_strategy in ['conservative', 'balanced', 'aggressive']
    
    def test_switch_validation(self, strategy_switcher):
        """Test switch validation"""
        switch = {
            'from_strategy': 'balanced',
            'to_strategy': 'conservative',
            'reason': 'error_recovery',
            'success': True
        }
        
        strategy_switcher.record_switch(switch)
        
        validation = strategy_switcher.validate_switch(switch)
        
        assert validation['valid'] == True


class TestStrategyHybridizer:
    """Test strategy hybridization"""
    
    @pytest.fixture
    def strategy_hybridizer(self):
        """Create strategy hybridizer"""
        return StrategyHybridizer()
    
    def test_hybrid_strategy_creation(self, strategy_hybridizer):
        """Test hybrid strategy creation"""
        strategies = {
            'planning': 'conservative',
            'implementation': 'balanced',
            'testing': 'conservative'
        }
        
        hybrid = strategy_hybridizer.create_hybrid(strategies)
        
        assert hybrid is not None
        assert 'planning' in hybrid
        assert 'implementation' in hybrid
        assert 'testing' in hybrid
    
    def test_phase_based_hybridization(self, strategy_hybridizer):
        """Test phase-based hybridization"""
        phases = ['planning', 'implementation', 'testing']
        
        hybrid = strategy_hybridizer.create_phase_based_hybrid(phases)
        
        assert len(hybrid) == 3
        assert all(phase in hybrid for phase in phases)
    
    def test_risk_based_hybridization(self, strategy_hybridizer):
        """Test risk-based hybridization"""
        tasks = [
            {'task': 'critical', 'risk': 'high'},
            {'task': 'routine', 'risk': 'low'}
        ]
        
        hybrid = strategy_hybridizer.create_risk_based_hybrid(tasks)
        
        assert hybrid is not None
        assert hybrid['critical']['strategy'] == 'conservative'
        assert hybrid['routine']['strategy'] in ['balanced', 'aggressive']


class TestIntegration:
    """Integration tests for complete workflows"""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    def test_complete_adaptive_reasoning_workflow(self, temp_dir):
        """Test complete adaptive reasoning workflow"""
        # Initialize components
        db_path = Path(temp_dir) / "test.db"
        
        context_hierarchy = ContextHierarchyManager(db_path=str(db_path))
        decision_maker = DecisionMaker()
        progress_tracker = ProgressTracker(db_path=str(db_path))
        trap_detector = TrapDetector()
        
        # Simulate workflow
        context = {'situation': 'normal', 'task': 'implement_feature'}
        
        # Store context
        context_hierarchy.store_context('L0', context)
        
        # Make decision
        alternatives = [
            {'action': 'write_test', 'success_prob': 0.9, 'cost': 10},
            {'action': 'skip_test', 'success_prob': 0.5, 'cost': 5}
        ]
        decision = decision_maker.select_action(alternatives)
        
        # Track progress
        task_id = 1
        progress_tracker.start_tracking(task_id)
        progress_tracker.update_progress(task_id, {'completion': 0.5})
        
        # Check for traps
        actions = ['write_test', 'write_test', 'write_test']
        loops = trap_detector.detect_exact_action_loop(actions)
        
        # Verify workflow
        assert decision['action'] in ['write_test', 'skip_test']
        assert progress_tracker.check_progress(task_id) == True
        assert loops['detected'] == True
    
    def test_trap_detection_and_recovery_workflow(self, temp_dir):
        """Test trap detection and recovery workflow"""
        trap_detector = TrapDetector()
        trap_recovery = TrapRecovery()
        progress_tracker = ProgressTracker(db_path=str(db_path))
        
        # Simulate loop trap
        actions = ['retry', 'retry', 'retry']
        trap = trap_detector.detect_exact_action_loop(actions)
        
        if trap['detected']:
            # Recover from trap
            recovery = trap_recovery.recover(trap)
            
            # Validate recovery
            assert recovery['success'] == True
            assert recovery['strategy'] is not None
    
    def test_meta_cognition_workflow(self, temp_dir):
        """Test meta-cognition workflow"""
        db_path = Path(temp_dir) / "test.db"
        
        decision_history = DecisionHistory(db_path=str(db_path))
        pattern_recognizer = PatternRecognizer(db_path=str(db_path))
        self_reflection = SelfReflection(db_path=str(db_path))
        
        # Record decisions
        for i in range(5):
            decision_id = decision_history.record_decision({
                'action': 'test_action',
                'confidence': 0.8
            })
            decision_history.record_outcome(
                decision_id,
                outcome='success' if i < 4 else 'failure',
                time_elapsed=1.0
            )
        
        # Recognize patterns
        decisions = decision_history.list_decisions()
        patterns = pattern_recognizer.recognize_patterns(decisions)
        
        # Perform reflection
        reflection = self_reflection.perform_reflection(decisions)
        
        # Verify meta-cognition
        assert len(decisions) == 5
        assert 'summary' in reflection
        assert 'insights' in reflection


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])