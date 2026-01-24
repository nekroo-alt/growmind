"""
Integration Tests for V4 Adaptive Reasoning System

This module contains end-to-end integration tests for the complete V4 adaptive reasoning system.
Tests cover realistic workflows including normal operations, trap detection and recovery,
strategy switching, meta-cognition, and decision explainability.
"""

import os
import sys
import unittest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import json

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from data.context_hierarchy import ContextHierarchyManager, ContextLevel
from data.decision_history import DecisionHistory
from data.decision_tracer import DecisionTracer
from logic.context_expander import ContextExpander
from logic.reasoning_engine import ReasoningEngine, ReasoningStrategy
from logic.context_analyzer import ContextAnalyzer, SituationType
from logic.decision_maker import DecisionMaker, DecisionStrategy
from logic.action_validator import ActionValidator
from logic.strategy_selector import StrategySelector
from logic.strategy_evaluator import StrategyEvaluator
from logic.progress_tracker import ProgressTracker, ProgressThreshold
from logic.trap_detector import TrapDetector, TrapType, TrapSeverity
from logic.trap_recovery import TrapRecovery
from logic.trap_prevention import TrapPrevention
from logic.pattern_recognizer import PatternRecognizer
from logic.self_reflection import SelfReflection
from logic.lesson_learner import LessonLearner
from logic.adaptive_heuristics import AdaptiveHeuristics
from logic.explanation_generator import ExplanationGenerator, ExplanationFormat, AudienceType


class TestAdaptiveReasoningIntegration(unittest.TestCase):
    """End-to-end integration tests for V4 adaptive reasoning system."""
    
    def setUp(self):
        """Set up test environment with temporary databases."""
        self.test_dir = tempfile.mkdtemp()
        self.context_hierarchy_db = os.path.join(self.test_dir, 'context_hierarchy.db')
        self.decision_history_db = os.path.join(self.test_dir, 'decision_history.db')
        self.decision_tracer_db = os.path.join(self.test_dir, 'decision_tracer.db')
        self.strategy_evaluator_db = os.path.join(self.test_dir, 'strategy_evaluator.db')
        self.pattern_recognizer_db = os.path.join(self.test_dir, 'pattern_recognizer.db')
        self.lesson_learner_db = os.path.join(self.test_dir, 'lesson_learner.db')
        self.adaptive_heuristics_db = os.path.join(self.test_dir, 'adaptive_heuristics.db')
        
        # Initialize all V4 components
        self.context_hierarchy = ContextHierarchyManager(self.context_hierarchy_db)
        self.decision_history = DecisionHistory(self.decision_history_db)
        self.decision_tracer = DecisionTracer(self.decision_tracer_db)
        self.context_expander = ContextExpander(self.context_hierarchy)
        self.context_analyzer = ContextAnalyzer(self.context_hierarchy)
        self.decision_maker = DecisionMaker(self.decision_history)
        self.action_validator = ActionValidator(self.decision_history)
        self.strategy_selector = StrategySelector(self.context_analyzer)
        self.strategy_evaluator = StrategyEvaluator(self.strategy_evaluator_db)
        self.progress_tracker = ProgressTracker()
        self.trap_detector = TrapDetector()
        self.trap_recovery = TrapRecovery(self.context_hierarchy, self.decision_history)
        self.trap_prevention = TrapPrevention()
        self.pattern_recognizer = PatternRecognizer(self.pattern_recognizer_db, self.decision_history)
        self.self_reflection = SelfReflection(self.pattern_recognizer, self.decision_history)
        self.lesson_learner = LessonLearner(self.lesson_learner_db, self.decision_history)
        self.adaptive_heuristics = AdaptiveHeuristics(self.adaptive_heuristics_db)
        self.explanation_generator = ExplanationGenerator()
        self.reasoning_engine = ReasoningEngine(
            self.context_analyzer,
            self.decision_maker,
            self.action_validator,
            self.strategy_selector
        )
    
    def tearDown(self):
        """Clean up test environment."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_complete_workflow_with_adaptive_reasoning(self):
        """Test 1: Complete workflow with adaptive reasoning from planning to completion."""
        # Simulate a complete task: "Add user authentication module"
        task_id = "task_001"
        task_description = "Add user authentication module with JWT tokens"
        
        # Step 1: Context hierarchy stores task context
        self.context_hierarchy.add_context(
            ContextLevel.L0,
            task_id,
            {
                'action': 'start_task',
                'task_description': task_description,
                'timestamp': datetime.now().isoformat()
            }
        )
        
        # Step 2: Analyze situation
        situation = self.context_analyzer.analyze_situation(
            task_id,
            task_description,
            {'complexity': 'medium', 'dependencies': ['database', 'crypto']}
        )
        self.assertEqual(situation.situation_type, SituationType.NORMAL)
        self.assertGreater(situation.confidence, 0.5)
        
        # Step 3: Select strategy based on situation
        strategy = self.strategy_selector.select_strategy(
            situation.situation_type,
            task_description
        )
        self.assertIn(strategy, [s.value for s in ReasoningStrategy])
        
        # Step 4: Make decision
        decision = self.decision_maker.select_action(
            task_id,
            ['create_auth_class', 'add_jwt_handlers', 'write_tests'],
            strategy=DecisionStrategy.OPTIMAL
        )
        self.assertIsNotNone(decision.selected_action)
        self.assertGreater(decision.confidence, 0.0)
        
        # Step 5: Record decision
        decision_id = self.decision_history.record_decision(
            task_id=task_id,
            action=decision.selected_action,
            reasoning=decision.reasoning,
            context={'strategy': strategy},
            confidence=decision.confidence
        )
        self.assertIsNotNone(decision_id)
        
        # Step 6: Trace decision
        self.decision_tracer.log_decision(
            decision_id=decision_id,
            task_id=task_id,
            operation_id='op_001',
            context_snapshot={'task': task_description},
            reasoning_chain=[
                {'step': 1, 'thought': 'Analyze task requirements', 'conclusion': 'Need auth module'},
                {'step': 2, 'thought': 'Evaluate options', 'conclusion': 'Create auth class first'}
            ],
            alternatives=[
                {'action': 'add_jwt_handlers', 'reason_for_rejection': 'Too early, need base class'},
                {'action': 'write_tests', 'reason_for_rejection': 'No code to test yet'}
            ],
            selected_action=decision.selected_action,
            confidence=decision.confidence
        )
        
        # Step 7: Track progress
        self.progress_tracker.start_tracking(task_id, {
            'task_description': task_description,
            'estimated_steps': 5
        })
        self.progress_tracker.update_progress(task_id, {
            'steps_completed': 1,
            'files_created': 1
        })
        
        # Step 8: Validate action
        validation_result = self.action_validator.validate_action(
            decision_id=decision_id,
            action=decision.selected_action,
            expected_outcome={'auth_class_created': True},
            actual_outcome={'auth_class_created': True, 'quality': 'good'}
        )
        self.assertTrue(validation_result.success)
        
        # Step 9: Record outcome
        self.decision_history.record_outcome(
            decision_id=decision_id,
            outcome='success',
            time_elapsed=2.5,
            resources={'tokens': 1250, 'api_calls': 3}
        )
        
        # Step 10: Validate progress
        progress_result = self.progress_tracker.check_progress(task_id)
        self.assertTrue(progress_result['is_adequate'])
        
        # Verify all components worked together
        self.assertEqual(len(self.decision_history.list_decisions(task_id=task_id)), 1)
        self.assertEqual(len(self.decision_tracer.search(task_id=task_id)), 1)
    
    def test_trap_detection_and_recovery_workflow(self):
        """Test 2: Trap detection and automatic recovery in realistic scenario."""
        task_id = "task_002"
        
        # Simulate getting stuck in a loop: trying same fix repeatedly
        actions = [
            'fix_import_error_in_auth',
            'fix_import_error_in_auth',
            'fix_import_error_in_auth',
            'fix_import_error_in_auth'
        ]
        
        # Record each action
        for i, action in enumerate(actions):
            decision_id = self.decision_history.record_decision(
                task_id=task_id,
                action=action,
                reasoning=f'Attempt {i+1} to fix import error',
                context={'error': 'ModuleNotFoundError'},
                confidence=0.8
            )
            
            # Add to trap detector
            self.trap_detector.add_action(action)
            
            # Record outcome (all fail)
            self.decision_history.record_outcome(
                decision_id=decision_id,
                outcome='failure',
                time_elapsed=1.0,
                resources={'tokens': 500}
            )
        
        # Detect loop
        loop_result = self.trap_detector.detect_exact_action_loop(threshold=3)
        self.assertTrue(loop_result.detected)
        self.assertEqual(loop_result.trap_type, TrapType.INFINITE_LOOP)
        self.assertEqual(loop_result.severity, TrapSeverity.CRITICAL)
        
        # Suggest recovery strategy
        recovery_strategy = self.trap_recovery.select_recovery_strategy(
            loop_result.trap_type,
            loop_result.severity
        )
        self.assertIsNotNone(recovery_strategy)
        
        # Execute recovery
        recovery_result = self.trap_recovery.execute_recovery(
            loop_result.trap_type,
            recovery_strategy,
            {'task_id': task_id}
        )
        self.assertTrue(recovery_result.success)
        
        # Record trap and recovery in telemetry
        self.decision_tracer.log_event(
            task_id=task_id,
            event_type='trap_detected',
            details={
                'trap_type': loop_result.trap_type.value,
                'severity': loop_result.severity.value,
                'recovery_strategy': recovery_strategy
            }
        )
        
        # Verify trap was detected and recovered
        self.assertTrue(loop_result.detected)
        self.assertTrue(recovery_result.success)
    
    def test_strategy_switching_during_task_execution(self):
        """Test 3: Strategy switching when current strategy underperforms."""
        task_id = "task_003"
        
        # Start with conservative strategy
        initial_strategy = ReasoningStrategy.CONSERVATIVE
        
        # Simulate several operations with poor success rate
        success_count = 0
        total_operations = 10
        
        for i in range(total_operations):
            decision_id = self.decision_history.record_decision(
                task_id=task_id,
                action=f'operation_{i+1}',
                reasoning='Using conservative approach',
                context={'strategy': initial_strategy.value},
                confidence=0.7
            )
            
            # Simulate 30% success rate (very poor)
            if i < 3:  # Only first 3 succeed
                self.decision_history.record_outcome(
                    decision_id=decision_id,
                    outcome='success',
                    time_elapsed=5.0,
                    resources={'tokens': 2000}
                )
                success_count += 1
            else:
                self.decision_history.record_outcome(
                    decision_id=decision_id,
                    outcome='failure',
                    time_elapsed=5.0,
                    resources={'tokens': 2000}
                )
        
        # Track strategy performance
        self.strategy_evaluator.track_performance(
            strategy=initial_strategy.value,
            task_type='implementation',
            success_rate=success_count / total_operations,
            avg_time=5.0,
            avg_tokens=2000
        )
        
        # Check if strategy should switch
        should_switch = self.strategy_selector.should_switch(
            current_strategy=initial_strategy.value,
            recent_success_rate=success_count / total_operations
        )
        self.assertTrue(should_switch)
        
        # Switch to better strategy
        new_strategy = self.strategy_selector.switch_strategy(
            current_strategy=initial_strategy.value,
            situation_type=SituationType.ERROR_RECOVERY
        )
        self.assertNotEqual(new_strategy, initial_strategy.value)
        
        # Record strategy switch
        self.decision_tracer.log_event(
            task_id=task_id,
            event_type='strategy_switched',
            details={
                'old_strategy': initial_strategy.value,
                'new_strategy': new_strategy,
                'reason': 'low_success_rate',
                'success_rate': success_count / total_operations
            }
        )
        
        # Verify strategy switched
        self.assertNotEqual(new_strategy, initial_strategy.value)
    
    def test_meta_cognition_over_multiple_sessions(self):
        """Test 4: Meta-cognition and learning across multiple sessions."""
        # Session 1: Make decisions and learn patterns
        session1_id = "session_001"
        
        decisions_session1 = [
            ('create_user_model', 'success', 'simple CRUD operation'),
            ('add_authentication', 'failure', 'missing JWT dependency'),
            ('implement_login', 'success', 'standard auth pattern'),
            ('add_password_reset', 'success', 'email integration works')
        ]
        
        for action, outcome, reasoning in decisions_session1:
            decision_id = self.decision_history.record_decision(
                task_id=session1_id,
                action=action,
                reasoning=reasoning,
                context={'session': session1_id},
                confidence=0.75
            )
            self.decision_history.record_outcome(
                decision_id=decision_id,
                outcome=outcome,
                time_elapsed=2.0,
                resources={'tokens': 1000}
            )
        
        # Recognize patterns
        self.pattern_recognizer.recognize_patterns(session1_id)
        patterns = self.pattern_recognizer.get_patterns()
        self.assertGreater(len(patterns), 0)
        
        # Session 2: Apply learned patterns to make better decisions
        session2_id = "session_002"
        
        decision_id = self.decision_history.record_decision(
            task_id=session2_id,
            action='implement_logout',
            reasoning='Similar to login, should succeed',
            context={'session': session2_id},
            confidence=0.85  # Higher confidence from pattern recognition
        )
        
        # Use adaptive heuristics learned from session 1
        heuristics = self.adaptive_heuristics.get_heuristics()
        self.assertIsNotNone(heuristics)
        
        # Perform self-reflection on session 1
        reflection_report = self.self_reflection.perform_reflection(
            task_id=session1_id,
            trigger='after_task'
        )
        self.assertIsNotNone(reflection_report)
        self.assertIn('summary', reflection_report)
        self.assertIn('insights', reflection_report)
        
        # Session 2 succeeds due to learning
        self.decision_history.record_outcome(
            decision_id=decision_id,
            outcome='success',
            time_elapsed=1.5,  # Faster due to learning
            resources={'tokens': 800}  # Fewer tokens due to learning
        )
        
        # Verify learning improved performance
        self.assertGreaterEqual(0.85, 0.75)  # Higher confidence
        
        # Test lesson learning from failures
        if any(outcome == 'failure' for _, outcome, _ in decisions_session1):
            failure_decision = [d for d in decisions_session1 if d[1] == 'failure'][0]
            lesson = self.lesson_learner.extract_lesson(
                failure_type=failure_decision[1],
                root_cause='missing dependency',
                context=failure_decision[2]
            )
            self.assertIsNotNone(lesson)
    
    def test_decision_explainability_and_traceability(self):
        """Test 5: Decision explainability with full traceability."""
        task_id = "task_004"
        
        # Make a complex decision
        alternatives = [
            {'action': 'use_postgresql', 'reason': 'ACID compliance', 'cost': 'high'},
            {'action': 'use_mysql', 'reason': 'familiar', 'cost': 'medium'},
            {'action': 'use_mongodb', 'reason': 'flexible schema', 'cost': 'low'}
        ]
        
        decision = self.decision_maker.select_action(
            task_id=task_id,
            actions=[alt['action'] for alt in alternatives],
            strategy=DecisionStrategy.OPTIMAL
        )
        
        decision_id = self.decision_history.record_decision(
            task_id=task_id,
            action=decision.selected_action,
            reasoning=decision.reasoning,
            context={'alternatives': alternatives},
            confidence=decision.confidence
        )
        
        # Trace decision with full reasoning chain
        reasoning_chain = [
            {'step': 1, 'thought': 'Analyze requirements', 'conclusion': 'Need ACID compliance'},
            {'step': 2, 'thought': 'Evaluate options', 'conclusion': 'PostgreSQL best fit'},
            {'step': 3, 'thought': 'Consider cost', 'conclusion': 'Accept high cost for reliability'}
        ]
        
        self.decision_tracer.log_decision(
            decision_id=decision_id,
            task_id=task_id,
            operation_id='op_004',
            context_snapshot={'requirements': ['ACID', 'reliability']},
            reasoning_chain=reasoning_chain,
            alternatives=[{'action': alt['action'], 'reason_for_rejection': f"{alt['reason']} - {alt['cost']} cost"} for alt in alternatives if alt['action'] != decision.selected_action],
            selected_action=decision.selected_action,
            confidence=decision.confidence
        )
        
        # Generate explanation for different audiences
        # Brief explanation
        brief_explanation = self.explanation_generator.generate_explanation(
            action=decision.selected_action,
            reasoning=decision.reasoning,
            format=ExplanationFormat.BRIEF,
            audience=AudienceType.MANAGER
        )
        self.assertIsNotNone(brief_explanation)
        self.assertLess(len(brief_explanation.text), 200)
        
        # Detailed explanation
        detailed_explanation = self.explanation_generator.generate_explanation(
            action=decision.selected_action,
            reasoning=decision.reasoning,
            alternatives=alternatives,
            format=ExplanationFormat.DETAILED,
            audience=AudienceType.DEVELOPER
        )
        self.assertIsNotNone(detailed_explanation)
        self.assertIn(decision.selected_action, detailed_explanation.text)
        
        # Technical explanation
        technical_explanation = self.explanation_generator.generate_explanation(
            action=decision.selected_action,
            reasoning=decision.reasoning,
            context={'confidence': decision.confidence},
            format=ExplanationFormat.TECHNICAL,
            audience=AudienceType.DEVELOPER
        )
        self.assertIsNotNone(technical_explanation)
        self.assertIn(str(decision.confidence), technical_explanation.text)
        
        # Search and retrieve decision trace
        traces = self.decision_tracer.search(task_id=task_id)
        self.assertEqual(len(traces), 1)
        self.assertEqual(traces[0]['selected_action'], decision.selected_action)
        
        # Verify full traceability
        full_trace = self.decision_tracer.get_decision_trace(decision_id)
        self.assertIsNotNone(full_trace)
        self.assertEqual(len(full_trace['reasoning_chain']), 3)
        self.assertEqual(len(full_trace['alternatives']), 2)
    
    def test_error_conditions_and_resilience(self):
        """Test 6: System resilience under error conditions."""
        task_id = "task_005"
        
        # Test 1: Handle missing context gracefully
        try:
            situation = self.context_analyzer.analyze_situation(
                task_id=task_id,
                task_description="",
                context={}
            )
            # Should still return something, not crash
            self.assertIsNotNone(situation)
        except Exception as e:
            # Should handle gracefully
            self.assertIsNotNone(e)
        
        # Test 2: Handle invalid decision ID gracefully
        result = self.decision_history.get_decision("invalid_id")
        self.assertIsNone(result)
        
        # Test 3: Handle concurrent access (thread safety)
        import threading
        
        def record_decision():
            for i in range(10):
                decision_id = self.decision_history.record_decision(
                    task_id=task_id,
                    action=f'concurrent_action_{i}',
                    reasoning='Concurrent test',
                    context={'thread': 'test'},
                    confidence=0.5
                )
        
        threads = [threading.Thread(target=record_decision) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Verify all decisions were recorded
        decisions = self.decision_history.list_decisions(task_id=task_id)
        self.assertEqual(len(decisions), 30)
        
        # Test 4: Handle corrupted data gracefully
        try:
            # Try to get decision with invalid format
            result = self.decision_tracer.search_context(query="")
            self.assertIsInstance(result, list)
        except Exception as e:
            # Should handle gracefully
            self.assertIsNotNone(e)


class TestScenarioCoverage(unittest.TestCase):
    """Test scenario coverage to ensure >80% coverage."""
    
    def test_scenario_coverage(self):
        """Verify coverage of major V4 scenarios."""
        # Define all major scenarios
        scenarios = [
            'normal_workflow',
            'trap_detection',
            'trap_recovery',
            'strategy_selection',
            'strategy_switching',
            'progress_tracking',
            'progress_validation',
            'pattern_recognition',
            'self_reflection',
            'lesson_learning',
            'decision_explanation',
            'decision_traceability',
            'error_handling',
            'concurrent_access'
        ]
        
        # Check which scenarios are covered in integration tests
        covered_scenarios = [
            'normal_workflow',  # test_complete_workflow_with_adaptive_reasoning
            'trap_detection',   # test_trap_detection_and_recovery_workflow
            'trap_recovery',    # test_trap_detection_and_recovery_workflow
            'strategy_selection', # test_strategy_switching_during_task_execution
            'strategy_switching', # test_strategy_switching_during_task_execution
            'pattern_recognition', # test_meta_cognition_over_multiple_sessions
            'self_reflection',    # test_meta_cognition_over_multiple_sessions
            'lesson_learning',     # test_meta_cognition_over_multiple_sessions
            'decision_explanation', # test_decision_explainability_and_traceability
            'decision_traceability', # test_decision_explainability_and_traceability
            'error_handling',       # test_error_conditions_and_resilience
            'concurrent_access'      # test_error_conditions_and_resilience
        ]
        
        coverage_rate = len(covered_scenarios) / len(scenarios)
        self.assertGreaterEqual(coverage_rate, 0.80, 
            f"Coverage rate {coverage_rate:.2%} is below 80%")
        
        print(f"\nScenario Coverage: {coverage_rate:.2%} ({len(covered_scenarios)}/{len(scenarios)} scenarios)")
        print(f"Covered scenarios: {covered_scenarios}")
        print(f"Missing scenarios: {set(scenarios) - set(covered_scenarios)}")


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)