"""
Performance Benchmarking for V4 Adaptive Reasoning System

This module provides comprehensive benchmarking tools to measure and analyze
the performance overhead of V4 adaptive reasoning features compared to V3 baseline.

Key Performance Metrics:
- Overhead: Time added by adaptive reasoning
- Context Operations: Context access time per level
- Reasoning: Reasoning time per decision
- Trap Detection: Detection time per operation
- Meta-Cognition: Learning time per session

Performance Budgets:
- Overhead < 20%
- Context access < 100ms
- Reasoning < 500ms
- Trap detection < 50ms
"""

import time
import statistics
import sqlite3
from pathlib import Path
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import json

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from v5.data import ContextHierarchyManager
from v5.data import DecisionHistory
from v5.logic import ContextExpander
from v5.logic import ContextScorer
from v5.logic import ContextSummarizer
from v5.logic import ReasoningEngine
from v5.logic import ContextAnalyzer
from v5.logic import DecisionMaker
from v5.logic import ActionValidator
from v5.logic import StrategySelector
from v5.logic import ProgressTracker
from v5.logic import ProgressPredictor
from v5.logic import TrapDetector
from v5.logic import TrapRecovery
from v5.logic import TrapPrevention
from v5.logic import PatternRecognizer
from v5.logic import SelfReflection
from v5.logic import LessonLearner
from v5.logic import AdaptiveHeuristics
from v5.logic import ExplanationGenerator
from v5.data import DecisionTracer
from v5.logic import StrategyEvaluator
from v5.logic import StrategySwitcher
from v5.logic import StrategyHybridizer
from v5.data import TelemetryManager


@dataclass
class BenchmarkResult:
    """Result of a single benchmark run."""
    name: str
    operation: str
    duration_ms: float
    memory_bytes: int = 0
    success: bool = True
    error: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BenchmarkSummary:
    """Summary statistics for a benchmark."""
    name: str
    operation: str
    mean_ms: float
    median_ms: float
    std_dev_ms: float
    min_ms: float
    max_ms: float
    samples: int
    success_rate: float
    overhead_vs_baseline_ms: float = 0.0
    overhead_percentage: float = 0.0


class PerformanceBenchmark:
    """
    Comprehensive performance benchmarking suite for V4 adaptive reasoning.
    
    Benchmarks all major V4 components and compares against V3 baseline.
    Tracks overhead, efficiency, and adherence to performance budgets.
    """
    
    def __init__(self, test_db_path: str = "test_benchmark.db"):
        """Initialize benchmark suite with test database."""
        self.test_db_path = test_db_path
        self.results: List[BenchmarkResult] = []
        self.summaries: Dict[str, BenchmarkSummary] = {}
        
        # Initialize V4 components
        self._init_components()
        
        # Baseline V3 timings (simulated)
        self.v3_baseline = {
            'context_access': 10.0,  # 10ms for simple context access
            'decision_making': 50.0,  # 50ms for simple decision
            'action_validation': 30.0,  # 30ms for validation
            'tracking': 5.0,  # 5ms for tracking
        }
        
        # Performance budgets
        self.budgets = {
            'context_access_l0': 10.0,  # 10ms
            'context_access_l1': 25.0,  # 25ms
            'context_access_l2': 50.0,  # 50ms
            'context_access_l3': 100.0,  # 100ms
            'reasoning': 500.0,  # 500ms
            'trap_detection': 50.0,  # 50ms
            'meta_cognition': 1000.0,  # 1s for learning
            'overall_overhead': 0.2,  # 20% overhead
        }
    
    def _init_components(self):
        """Initialize V4 components for benchmarking."""
        # Context hierarchy
        self.context_hierarchy = ContextHierarchyManager(self.test_db_path)
        
        # Decision tracking
        self.decision_history = DecisionHistory(self.test_db_path)
        self.decision_tracer = DecisionTracer(self.test_db_path)
        
        # Context operations
        self.context_expander = ContextExpander(self.context_hierarchy)
        self.context_scorer = ContextScorer()
        self.context_summarizer = ContextSummarizer()
        
        # Reasoning engine
        self.context_analyzer = ContextAnalyzer()
        self.decision_maker = DecisionMaker()
        self.action_validator = ActionValidator()
        self.reasoning_engine = ReasoningEngine(
            self.context_analyzer,
            self.decision_maker,
            self.action_validator
        )
        
        # Strategy management
        self.strategy_selector = StrategySelector()
        self.strategy_evaluator = StrategyEvaluator(self.test_db_path)
        self.strategy_switcher = StrategySwitcher()
        self.strategy_hybridizer = StrategyHybridizer()
        
        # Progress tracking
        self.progress_tracker = ProgressTracker(self.test_db_path)
        self.progress_predictor = ProgressPredictor(self.test_db_path)
        
        # Trap detection and recovery
        self.trap_detector = TrapDetector()
        self.trap_recovery = TrapRecovery()
        self.trap_prevention = TrapPrevention()
        
        # Meta-cognition
        self.pattern_recognizer = PatternRecognizer(self.test_db_path)
        self.self_reflection = SelfReflection(self.test_db_path)
        self.lesson_learner = LessonLearner(self.test_db_path)
        self.adaptive_heuristics = AdaptiveHeuristics(self.test_db_path)
        
        # Explainability
        self.explanation_generator = ExplanationGenerator()
        
        # Telemetry
        self.telemetry = TelemetryManager(self.test_db_path)
    
    def benchmark_context_hierarchy(self, samples: int = 100) -> List[BenchmarkResult]:
        """
        Benchmark context hierarchy operations.
        
        Tests:
        - L0 context access (immediate)
        - L1 context access (recent)
        - L2 context access (session)
        - L3 context access (project)
        """
        print("\n" + "="*70)
        print("Benchmarking Context Hierarchy Operations")
        print("="*70)
        
        results = []
        
        # Populate test data
        self._populate_context_data()
        
        # Benchmark L0 access
        print("\nBenchmarking L0 (Immediate) context access...")
        results.extend(self._benchmark_operation(
            name="Context_Hierarchy",
            operation="get_current_action",
            func=lambda: self.context_hierarchy.get_current_action(),
            samples=samples,
            budget_ms=self.budgets['context_access_l0']
        ))
        
        # Benchmark L1 access
        print("Benchmarking L1 (Recent) context access...")
        results.extend(self._benchmark_operation(
            name="Context_Hierarchy",
            operation="get_recent_actions",
            func=lambda: self.context_hierarchy.get_recent_actions(count=10),
            samples=samples,
            budget_ms=self.budgets['context_access_l1']
        ))
        
        # Benchmark L2 access
        print("Benchmarking L2 (Session) context access...")
        results.extend(self._benchmark_operation(
            name="Context_Hierarchy",
            operation="get_session_context",
            func=lambda: self.context_hierarchy.get_session_context(),
            samples=samples,
            budget_ms=self.budgets['context_access_l2']
        ))
        
        # Benchmark L3 access
        print("Benchmarking L3 (Project) context access...")
        results.extend(self._benchmark_operation(
            name="Context_Hierarchy",
            operation="get_project_context",
            func=lambda: self.context_hierarchy.get_project_context(),
            samples=samples,
            budget_ms=self.budgets['context_access_l3']
        ))
        
        # Benchmark adaptive context query
        print("Benchmarking adaptive context query...")
        results.extend(self._benchmark_operation(
            name="Context_Hierarchy",
            operation="get_context_adaptive",
            func=lambda: self.context_hierarchy.get_context(scope='adaptive', max_levels=3),
            samples=samples // 2,  # More expensive, fewer samples
            budget_ms=self.budgets['context_access_l2']
        ))
        
        return results
    
    def benchmark_context_operations(self, samples: int = 100) -> List[BenchmarkResult]:
        """
        Benchmark context operations.
        
        Tests:
        - Context expansion
        - Context relevance scoring
        - Context summarization
        """
        print("\n" + "="*70)
        print("Benchmarking Context Operations")
        print("="*70)
        
        results = []
        
        # Prepare test data
        test_context = {
            'task_type': 'implementation',
            'description': 'Implement new feature',
            'files': ['module.py'],
            'dependencies': ['module2.py']
        }
        
        # Benchmark context expansion
        print("\nBenchmarking context expansion...")
        results.extend(self._benchmark_operation(
            name="Context_Expansion",
            operation="get_context",
            func=lambda: self.context_expander.get_context(test_context['task_type']),
            samples=samples,
            budget_ms=self.budgets['context_access_l1']
        ))
        
        # Benchmark context scoring
        print("Benchmarking context relevance scoring...")
        test_items = [
            {'content': 'Test item 1', 'timestamp': datetime.now(), 'importance': 0.8},
            {'content': 'Test item 2', 'timestamp': datetime.now(), 'importance': 0.5},
        ]
        results.extend(self._benchmark_operation(
            name="Context_Scoring",
            operation="score_context",
            func=lambda: self.context_scorer.score_context(test_items, test_context),
            samples=samples,
            budget_ms=20.0
        ))
        
        # Benchmark context summarization (brief)
        print("Benchmarking context summarization (brief)...")
        test_summary_data = "This is a test context with multiple items that need summarization."
        results.extend(self._benchmark_operation(
            name="Context_Summarization",
            operation="summarize_brief",
            func=lambda: self.context_summarizer.summarize(test_summary_data, 'brief'),
            samples=samples // 2,  # More expensive
            budget_ms=100.0
        ))
        
        return results
    
    def benchmark_reasoning_engine(self, samples: int = 50) -> List[BenchmarkResult]:
        """
        Benchmark reasoning engine operations.
        
        Tests:
        - Context analysis
        - Decision making
        - Action validation
        - Full reasoning pipeline
        """
        print("\n" + "="*70)
        print("Benchmarking Reasoning Engine")
        print("="*70)
        
        results = []
        
        # Prepare test data
        test_context = {
            'situation': 'normal',
            'task_type': 'implementation',
            'recent_errors': [],
            'recent_actions': [],
            'resource_availability': {'tokens': 10000, 'time': 3600}
        }
        
        # Benchmark context analysis
        print("\nBenchmarking context analysis...")
        results.extend(self._benchmark_operation(
            name="Reasoning_Engine",
            operation="analyze",
            func=lambda: self.context_analyzer.analyze_situation(test_context),
            samples=samples,
            budget_ms=self.budgets['reasoning'] // 3
        ))
        
        # Benchmark decision making
        print("Benchmarking decision making...")
        alternatives = [
            {'action': 'implement_feature', 'success_prob': 0.8, 'cost': 100, 'risk': 0.2},
            {'action': 'refactor_code', 'success_prob': 0.9, 'cost': 150, 'risk': 0.1},
        ]
        results.extend(self._benchmark_operation(
            name="Reasoning_Engine",
            operation="decide",
            func=lambda: self.decision_maker.select_action(
                alternatives,
                strategy='balanced'
            ),
            samples=samples,
            budget_ms=self.budgets['reasoning'] // 3
        ))
        
        # Benchmark action validation
        print("Benchmarking action validation...")
        test_action = {
            'action': 'implement_feature',
            'expected_outcome': 'feature_implemented',
            'actual_outcome': 'feature_implemented',
            'side_effects': []
        }
        results.extend(self._benchmark_operation(
            name="Reasoning_Engine",
            operation="validate",
            func=lambda: self.action_validator.validate_action(test_action),
            samples=samples,
            budget_ms=self.budgets['reasoning'] // 3
        ))
        
        # Benchmark full reasoning pipeline
        print("Benchmarking full reasoning pipeline...")
        results.extend(self._benchmark_operation(
            name="Reasoning_Engine",
            operation="full_pipeline",
            func=lambda: self.reasoning_engine.reason(
                context=test_context,
                alternatives=alternatives,
                action=test_action
            ),
            samples=samples // 2,  # More expensive
            budget_ms=self.budgets['reasoning']
        ))
        
        return results
    
    def benchmark_strategy_management(self, samples: int = 50) -> List[BenchmarkResult]:
        """
        Benchmark strategy management operations.
        
        Tests:
        - Strategy selection
        - Strategy evaluation
        - Strategy switching
        - Strategy hybridization
        """
        print("\n" + "="*70)
        print("Benchmarking Strategy Management")
        print("="*70)
        
        results = []
        
        # Prepare test data
        test_situation = 'normal'
        test_task_type = 'implementation'
        test_strategies = ['conservative', 'balanced', 'aggressive']
        
        # Benchmark strategy selection
        print("\nBenchmarking strategy selection...")
        results.extend(self._benchmark_operation(
            name="Strategy_Management",
            operation="select_strategy",
            func=lambda: self.strategy_selector.select_strategy(
                test_situation,
                test_task_type
            ),
            samples=samples,
            budget_ms=50.0
        ))
        
        # Benchmark strategy evaluation
        print("Benchmarking strategy evaluation...")
        results.extend(self._benchmark_operation(
            name="Strategy_Management",
            operation="evaluate_performance",
            func=lambda: self.strategy_evaluator.get_strategy_performance(
                strategy='balanced',
                task_type=test_task_type
            ),
            samples=samples,
            budget_ms=100.0
        ))
        
        # Benchmark strategy comparison
        print("Benchmarking strategy comparison...")
        results.extend(self._benchmark_operation(
            name="Strategy_Management",
            operation="compare_strategies",
            func=lambda: self.strategy_evaluator.compare_strategies(
                task_type=test_task_type,
                situation_type=test_situation
            ),
            samples=samples // 2,
            budget_ms=150.0
        ))
        
        # Benchmark strategy hybridization
        print("Benchmarking strategy hybridization...")
        results.extend(self._benchmark_operation(
            name="Strategy_Management",
            operation="create_hybrid",
            func=lambda: self.strategy_hybridizer.create_hybrid_strategy(
                strategies=test_strategies,
                weights=[0.3, 0.5, 0.2]
            ),
            samples=samples,
            budget_ms=100.0
        ))
        
        return results
    
    def benchmark_progress_tracking(self, samples: int = 100) -> List[BenchmarkResult]:
        """
        Benchmark progress tracking operations.
        
        Tests:
        - Progress tracking
        - Progress validation
        - Progress prediction
        """
        print("\n" + "="*70)
        print("Benchmarking Progress Tracking")
        print("="*70)
        
        results = []
        
        # Prepare test data
        test_task_id = 1
        test_metrics = {
            'lines_added': 10,
            'tests_passing': 5,
            'coverage': 0.8
        }
        
        # Benchmark progress tracking
        print("\nBenchmarking progress tracking...")
        results.extend(self._benchmark_operation(
            name="Progress_Tracking",
            operation="update_progress",
            func=lambda: self.progress_tracker.update_progress(
                test_task_id,
                test_metrics
            ),
            samples=samples,
            budget_ms=20.0
        ))
        
        # Benchmark progress validation
        print("Benchmarking progress validation...")
        results.extend(self._benchmark_operation(
            name="Progress_Tracking",
            operation="check_progress",
            func=lambda: self.progress_tracker.check_progress(test_task_id),
            samples=samples,
            budget_ms=30.0
        ))
        
        # Benchmark progress prediction
        print("Benchmarking progress prediction...")
        results.extend(self._benchmark_operation(
            name="Progress_Prediction",
            operation="predict_completion",
            func=lambda: self.progress_predictor.predict_completion_time(test_task_id),
            samples=samples,
            budget_ms=100.0
        ))
        
        return results
    
    def benchmark_trap_detection(self, samples: int = 100) -> List[BenchmarkResult]:
        """
        Benchmark trap detection operations.
        
        Tests:
        - Loop detection
        - Dead end detection
        - Circular reasoning detection
        - Full trap detection
        """
        print("\n" + "="*70)
        print("Benchmarking Trap Detection")
        print("="*70)
        
        results = []
        
        # Prepare test data
        test_actions = [
            {'action': 'test_action', 'timestamp': datetime.now()},
            {'action': 'test_action', 'timestamp': datetime.now()},
            {'action': 'test_action', 'timestamp': datetime.now()},
        ]
        
        # Benchmark loop detection
        print("\nBenchmarking loop detection...")
        results.extend(self._benchmark_operation(
            name="Trap_Detection",
            operation="detect_loop",
            func=lambda: self.trap_detector.detect_exact_action_loop(test_actions),
            samples=samples,
            budget_ms=self.budgets['trap_detection']
        ))
        
        # Benchmark dead end detection
        print("Benchmarking dead end detection...")
        test_progress = [{'value': 0.1}, {'value': 0.1}, {'value': 0.1}]
        results.extend(self._benchmark_operation(
            name="Trap_Detection",
            operation="detect_dead_end",
            func=lambda: self.trap_detector.detect_dead_end_no_progress(test_progress),
            samples=samples,
            budget_ms=self.budgets['trap_detection']
        ))
        
        # Benchmark circular reasoning detection
        print("Benchmarking circular reasoning detection...")
        test_decisions = [
            {'decision_id': '1', 'depends_on': []},
            {'decision_id': '2', 'depends_on': ['1']},
            {'decision_id': '3', 'depends_on': ['2', '1']},
        ]
        results.extend(self._benchmark_operation(
            name="Trap_Detection",
            operation="detect_circular",
            func=lambda: self.trap_detector.detect_circular_reasoning(test_decisions),
            samples=samples,
            budget_ms=self.budgets['trap_detection']
        ))
        
        # Benchmark full trap detection
        print("Benchmarking full trap detection...")
        results.extend(self._benchmark_operation(
            name="Trap_Detection",
            operation="detect_all",
            func=lambda: self.trap_detector.detect_all_loops(test_actions),
            samples=samples,
            budget_ms=self.budgets['trap_detection'] * 2
        ))
        
        return results
    
    def benchmark_meta_cognition(self, samples: int = 20) -> List[BenchmarkResult]:
        """
        Benchmark meta-cognition operations.
        
        Tests:
        - Pattern recognition
        - Self-reflection
        - Lesson learning
        - Adaptive heuristics
        """
        print("\n" + "="*70)
        print("Benchmarking Meta-Cognition")
        print("="*70)
        
        results = []
        
        # Prepare test data
        test_decisions = [
            {'decision_id': '1', 'context': {}, 'outcome': 'success'},
            {'decision_id': '2', 'context': {}, 'outcome': 'failure'},
        ]
        
        # Benchmark pattern recognition
        print("\nBenchmarking pattern recognition...")
        results.extend(self._benchmark_operation(
            name="Meta_Cognition",
            operation="recognize_patterns",
            func=lambda: self.pattern_recognizer.recognize_patterns(test_decisions),
            samples=samples,
            budget_ms=200.0
        ))
        
        # Benchmark self-reflection
        print("Benchmarking self-reflection...")
        results.extend(self._benchmark_operation(
            name="Meta_Cognition",
            operation="perform_reflection",
            func=lambda: self.self_reflection.perform_reflection(
                trigger='periodic',
                operation_count=10
            ),
            samples=samples // 2,  # More expensive
            budget_ms=self.budgets['meta_cognition']
        ))
        
        # Benchmark lesson learning
        print("Benchmarking lesson learning...")
        test_failure = {
            'failure_id': '1',
            'context': {},
            'error': 'Test error'
        }
        results.extend(self._benchmark_operation(
            name="Meta_Cognition",
            operation="learn_from_failure",
            func=lambda: self.lesson_learner.record_failure(test_failure),
            samples=samples,
            budget_ms=150.0
        ))
        
        # Benchmark adaptive heuristics
        print("Benchmarking adaptive heuristics...")
        results.extend(self._benchmark_operation(
            name="Meta_Cognition",
            operation="update_heuristics",
            func=lambda: self.adaptive_heuristics.update_heuristics(
                metric_name='success_rate',
                value=0.85
            ),
            samples=samples,
            budget_ms=100.0
        ))
        
        return results
    
    def benchmark_decision_explainability(self, samples: int = 50) -> List[BenchmarkResult]:
        """
        Benchmark decision explainability operations.
        
        Tests:
        - Decision tracing
        - Explanation generation
        - Decision queries
        """
        print("\n" + "="*70)
        print("Benchmarking Decision Explainability")
        print("="*70)
        
        results = []
        
        # Prepare test data
        test_decision = {
            'decision_id': 'test_1',
            'context': {'task': 'test'},
            'reasoning': 'Test reasoning',
            'action': 'test_action',
            'confidence': 0.85
        }
        
        # Benchmark decision tracing
        print("\nBenchmarking decision tracing...")
        results.extend(self._benchmark_operation(
            name="Decision_Explainability",
            operation="log_decision",
            func=lambda: self.decision_tracer.log_decision(
                operation_id='op_1',
                task_id=1,
                context_snapshot={},
                reasoning_chain=[],
                alternatives=[],
                selected_action='test_action',
                confidence=0.85
            ),
            samples=samples,
            budget_ms=30.0
        ))
        
        # Benchmark explanation generation
        print("Benchmarking explanation generation...")
        results.extend(self._benchmark_operation(
            name="Decision_Explainability",
            operation="generate_explanation",
            func=lambda: self.explanation_generator.generate_explanation(
                test_decision,
                format='detailed',
                audience='developer'
            ),
            samples=samples,
            budget_ms=100.0
        ))
        
        # Benchmark decision queries
        print("Benchmarking decision queries...")
        results.extend(self._benchmark_operation(
            name="Decision_Explainability",
            operation="search_decisions",
            func=lambda: self.decision_tracer.search(task_id=1),
            samples=samples,
            budget_ms=50.0
        ))
        
        return results
    
    def benchmark_overhead(self, samples: int = 50) -> List[BenchmarkResult]:
        """
        Benchmark overall V4 overhead compared to V3 baseline.
        
        Measures:
        - Context access overhead
        - Decision making overhead
        - Action validation overhead
        - Tracking overhead
        - Total system overhead
        """
        print("\n" + "="*70)
        print("Benchmarking V4 Overhead vs V3 Baseline")
        print("="*70)
        
        results = []
        
        # Measure context access overhead
        print("\nMeasuring context access overhead...")
        v4_context_time = self._measure_average(
            lambda: self.context_hierarchy.get_current_action(),
            samples
        )
        v3_context_time = self.v3_baseline['context_access']
        overhead_ms = v4_context_time - v3_context_time
        overhead_pct = (overhead_ms / v3_context_time) * 100
        
        print(f"  V3 baseline: {v3_context_time:.2f}ms")
        print(f"  V4 measured: {v4_context_time:.2f}ms")
        print(f"  Overhead: {overhead_ms:.2f}ms ({overhead_pct:.1f}%)")
        
        results.append(BenchmarkResult(
            name="Overhead",
            operation="context_access",
            duration_ms=v4_context_time,
            metadata={
                'baseline_ms': v3_context_time,
                'overhead_ms': overhead_ms,
                'overhead_percentage': overhead_pct
            }
        ))
        
        # Measure decision making overhead
        print("\nMeasuring decision making overhead...")
        test_alternatives = [
            {'action': 'test', 'success_prob': 0.8, 'cost': 100, 'risk': 0.2}
        ]
        v4_decision_time = self._measure_average(
            lambda: self.decision_maker.select_action(test_alternatives, 'balanced'),
            samples
        )
        v3_decision_time = self.v3_baseline['decision_making']
        overhead_ms = v4_decision_time - v3_decision_time
        overhead_pct = (overhead_ms / v3_decision_time) * 100
        
        print(f"  V3 baseline: {v3_decision_time:.2f}ms")
        print(f"  V4 measured: {v4_decision_time:.2f}ms")
        print(f"  Overhead: {overhead_ms:.2f}ms ({overhead_pct:.1f}%)")
        
        results.append(BenchmarkResult(
            name="Overhead",
            operation="decision_making",
            duration_ms=v4_decision_time,
            metadata={
                'baseline_ms': v3_decision_time,
                'overhead_ms': overhead_ms,
                'overhead_percentage': overhead_pct
            }
        ))
        
        # Measure action validation overhead
        print("\nMeasuring action validation overhead...")
        test_action = {
            'action': 'test',
            'expected': 'result',
            'actual': 'result'
        }
        v4_validation_time = self._measure_average(
            lambda: self.action_validator.validate_action(test_action),
            samples
        )
        v3_validation_time = self.v3_baseline['action_validation']
        overhead_ms = v4_validation_time - v3_validation_time
        overhead_pct = (overhead_ms / v3_validation_time) * 100
        
        print(f"  V3 baseline: {v3_validation_time:.2f}ms")
        print(f"  V4 measured: {v4_validation_time:.2f}ms")
        print(f"  Overhead: {overhead_ms:.2f}ms ({overhead_pct:.1f}%)")
        
        results.append(BenchmarkResult(
            name="Overhead",
            operation="action_validation",
            duration_ms=v4_validation_time,
            metadata={
                'baseline_ms': v3_validation_time,
                'overhead_ms': overhead_ms,
                'overhead_percentage': overhead_pct
            }
        ))
        
        return results
    
    def run_all_benchmarks(self) -> Dict[str, List[BenchmarkResult]]:
        """
        Run all benchmarks and return results.
        
        Returns:
            Dictionary mapping benchmark names to their results
        """
        print("\n" + "="*70)
        print("V4 ADAPTIVE REASONING PERFORMANCE BENCHMARK")
        print("="*70)
        print(f"Started at: {datetime.now().isoformat()}")
        
        all_results = {}
        
        try:
            # Benchmark context hierarchy
            all_results['context_hierarchy'] = self.benchmark_context_hierarchy()
            
            # Benchmark context operations
            all_results['context_operations'] = self.benchmark_context_operations()
            
            # Benchmark reasoning engine
            all_results['reasoning_engine'] = self.benchmark_reasoning_engine()
            
            # Benchmark strategy management
            all_results['strategy_management'] = self.benchmark_strategy_management()
            
            # Benchmark progress tracking
            all_results['progress_tracking'] = self.benchmark_progress_tracking()
            
            # Benchmark trap detection
            all_results['trap_detection'] = self.benchmark_trap_detection()
            
            # Benchmark meta-cognition
            all_results['meta_cognition'] = self.benchmark_meta_cognition()
            
            # Benchmark decision explainability
            all_results['decision_explainability'] = self.benchmark_decision_explainability()
            
            # Benchmark overhead
            all_results['overhead'] = self.benchmark_overhead()
            
        finally:
            print("\n" + "="*70)
            print(f"Benchmark completed at: {datetime.now().isoformat()}")
            print("="*70)
        
        # Flatten results
        self.results = [r for results in all_results.values() for r in results]
        
        # Calculate summaries
        self._calculate_summaries()
        
        return all_results
    
    def generate_report(self, output_path: str = "benchmark_report.json") -> str:
        """
        Generate comprehensive benchmark report.
        
        Args:
            output_path: Path to save report JSON file
            
        Returns:
            Report as JSON string
        """
        report = {
            'metadata': {
                'timestamp': datetime.now().isoformat(),
                'version': 'V4',
                'total_samples': len(self.results),
                'total_benchmarks': len(set(r.name for r in self.results))
            },
            'summaries': {
                name: {
                    'operation': summary.operation,
                    'mean_ms': summary.mean_ms,
                    'median_ms': summary.median_ms,
                    'std_dev_ms': summary.std_dev_ms,
                    'min_ms': summary.min_ms,
                    'max_ms': summary.max_ms,
                    'samples': summary.samples,
                    'success_rate': summary.success_rate,
                    'overhead_vs_baseline_ms': summary.overhead_vs_baseline_ms,
                    'overhead_percentage': summary.overhead_percentage,
                    'within_budget': summary.mean_ms <= self.budgets.get(
                        summary.operation.replace('get_', '').replace('_access', '').lower(),
                        float('inf')
                    )
                }
                for name, summary in self.summaries.items()
            },
            'budget_compliance': self._check_budget_compliance(),
            'overhead_summary': self._summarize_overhead(),
            'recommendations': self._generate_recommendations()
        }
        
        # Save to file
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\nBenchmark report saved to: {output_path}")
        
        return json.dumps(report, indent=2)
    
    def print_summary(self):
        """Print benchmark summary to console."""
        print("\n" + "="*70)
        print("BENCHMARK SUMMARY")
        print("="*70)
        
        # Print overhead summary
        print("\nV4 OVERHEAD vs V3 BASELINE:")
        print("-" * 70)
        overhead_summary = self._summarize_overhead()
        for operation, overhead in overhead_summary.items():
            print(f"  {operation:25s}: {overhead['percentage']:6.1f}% overhead")
            print(f"    V3 baseline: {overhead['baseline_ms']:6.2f}ms")
            print(f"    V4 measured: {overhead['measured_ms']:6.2f}ms")
        
        # Print budget compliance
        print("\nBUDGET COMPLIANCE:")
        print("-" * 70)
        compliance = self._check_budget_compliance()
        for operation, within_budget in compliance.items():
            status = "✓ PASS" if within_budget else "✗ FAIL"
            summary = self.summaries.get(operation)
            if summary:
                budget = self.budgets.get(operation.lower(), float('inf'))
                print(f"  {operation:25s}: {status} (budget: {budget:6.1f}ms, actual: {summary.mean_ms:6.2f}ms)")
        
        # Print top performers
        print("\nTOP 10 FASTEST OPERATIONS:")
        print("-" * 70)
        sorted_results = sorted(self.summaries.values(), key=lambda s: s.mean_ms)[:10]
        for i, summary in enumerate(sorted_results, 1):
            print(f"  {i:2d}. {summary.name:20s} {summary.operation:20s}: {summary.mean_ms:6.2f}ms")
        
        # Print recommendations
        print("\nRECOMMENDATIONS:")
        print("-" * 70)
        recommendations = self._generate_recommendations()
        for rec in recommendations:
            print(f"  • {rec}")
        
        print("\n" + "="*70)
    
    def _benchmark_operation(
        self,
        name: str,
        operation: str,
        func: callable,
        samples: int,
        budget_ms: float
    ) -> List[BenchmarkResult]:
        """Benchmark a single operation multiple times."""
        results = []
        
        for i in range(samples):
            try:
                start_time = time.perf_counter()
                func()
                end_time = time.perf_counter()
                
                duration_ms = (end_time - start_time) * 1000
                
                results.append(BenchmarkResult(
                    name=name,
                    operation=operation,
                    duration_ms=duration_ms,
                    success=True
                ))
                
            except Exception as e:
                results.append(BenchmarkResult(
                    name=name,
                    operation=operation,
                    duration_ms=0,
                    success=False,
                    error=str(e)
                ))
            
            # Progress indicator
            if (i + 1) % max(1, samples // 10) == 0:
                progress = (i + 1) / samples * 100
                print(f"  Progress: {progress:.0f}% ({i+1}/{samples} samples)")
        
        # Calculate statistics
        durations = [r.duration_ms for r in results if r.success]
        if durations:
            mean_ms = statistics.mean(durations)
            median_ms = statistics.median(durations)
            std_dev_ms = statistics.stdev(durations) if len(durations) > 1 else 0
            min_ms = min(durations)
            max_ms = max(durations)
            success_rate = len(durations) / len(results) * 100
            
            # Check against budget
            within_budget = mean_ms <= budget_ms
            status = "✓ PASS" if within_budget else "✗ FAIL"
            
            print(f"  Result: {mean_ms:.2f}ms (median: {median_ms:.2f}ms, std: {std_dev_ms:.2f}ms)")
            print(f"  Budget: {budget_ms:.2f}ms - {status}")
            
            # Store summary
            summary_key = f"{name}_{operation}"
            self.summaries[summary_key] = BenchmarkSummary(
                name=name,
                operation=operation,
                mean_ms=mean_ms,
                median_ms=median_ms,
                std_dev_ms=std_dev_ms,
                min_ms=min_ms,
                max_ms=max_ms,
                samples=len(durations),
                success_rate=success_rate
            )
        
        return results
    
    def _measure_average(self, func: callable, samples: int) -> float:
        """Measure average execution time of a function."""
        durations = []
        for _ in range(samples):
            start_time = time.perf_counter()
            func()
            end_time = time.perf_counter()
            durations.append((end_time - start_time) * 1000)
        return statistics.mean(durations)
    
    def _calculate_summaries(self):
        """Calculate summary statistics for all benchmarks."""
        # Summaries are already calculated in _benchmark_operation
        pass
    
    def _check_budget_compliance(self) -> Dict[str, bool]:
        """Check which operations are within performance budgets."""
        compliance = {}
        for key, summary in self.summaries.items():
            operation = summary.operation.lower()
            budget = self.budgets.get(operation, float('inf'))
            compliance[key] = summary.mean_ms <= budget
        return compliance
    
    def _summarize_overhead(self) -> Dict[str, Dict[str, float]]:
        """Summarize V4 overhead compared to V3 baseline."""
        overhead = {}
        for result in self.results:
            if result.name == "Overhead":
                overhead[result.operation] = {
                    'baseline_ms': result.metadata.get('baseline_ms', 0),
                    'measured_ms': result.duration_ms,
                    'overhead_ms': result.metadata.get('overhead_ms', 0),
                    'percentage': result.metadata.get('overhead_percentage', 0)
                }
        return overhead
    
    def _generate_recommendations(self) -> List[str]:
        """Generate performance optimization recommendations."""
        recommendations = []
        
        # Check budget compliance
        compliance = self._check_budget_compliance()
        for key, within_budget in compliance.items():
            if not within_budget:
                summary = self.summaries[key]
                budget = self.budgets.get(summary.operation.lower(), float('inf'))
                recommendations.append(
                    f"Optimize {summary.name}.{summary.operation}: "
                    f"currently {summary.mean_ms:.2f}ms, budget is {budget:.2f}ms "
                    f"({(summary.mean_ms/budget-1)*100:.0f}% over budget)"
                )
        
        # Check overhead
        overhead_summary = self._summarize_overhead()
        overall_overhead = statistics.mean(
            [h['percentage'] for h in overhead_summary.values()]
        )
        if overall_overhead > self.budgets['overall_overhead'] * 100:
            recommendations.append(
                f"Overall V4 overhead is {overall_overhead:.1f}%, "
                f"exceeds 20% target. Consider optimizing:"
            )
            for operation, overhead in overhead_summary.items():
                if overhead['percentage'] > 20:
                    recommendations.append(
                        f"  - {operation}: {overhead['percentage']:.1f}% overhead"
                    )
        else:
            recommendations.append(
                f"Overall V4 overhead is {overall_overhead:.1f}%, "
                f"within 20% target ✓"
            )
        
        # Check success rates
        for summary in self.summaries.values():
            if summary.success_rate < 95:
                recommendations.append(
                    f"Low success rate for {summary.name}.{summary.operation}: "
                    f"{summary.success_rate:.1f}% (target: >95%)"
                )
        
        if not recommendations:
            recommendations.append("All benchmarks meet performance targets!")
        
        return recommendations
    
    def _populate_context_data(self):
        """Populate test context data for benchmarking."""
        # This would populate the context hierarchy with test data
        # For now, we'll assume it's already populated
        pass
    
    def cleanup(self):
        """Clean up test database and resources."""
        try:
            if os.path.exists(self.test_db_path):
                os.remove(self.test_db_path)
                print(f"\nCleaned up test database: {self.test_db_path}")
        except Exception as e:
            print(f"Error cleaning up: {e}")


def main():
    """Main entry point for benchmarking."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="V4 Adaptive Reasoning Performance Benchmark"
    )
    parser.add_argument(
        '--samples',
        type=int,
        default=50,
        help='Number of samples per benchmark (default: 50)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='benchmark_report.json',
        help='Output path for benchmark report (default: benchmark_report.json)'
    )
    parser.add_argument(
        '--cleanup',
        action='store_true',
        help='Clean up test database after benchmarking'
    )
    
    args = parser.parse_args()
    
    # Create benchmark suite
    benchmark = PerformanceBenchmark(test_db_path="test_benchmark.db")
    
    try:
        # Run all benchmarks
        all_results = benchmark.run_all_benchmarks()
        
        # Generate report
        report = benchmark.generate_report(output_path=args.output)
        
        # Print summary
        benchmark.print_summary()
        
        # Print total samples
        print(f"\nTotal samples collected: {len(benchmark.results)}")
        print(f"Total benchmarks run: {len(all_results)}")
        
    finally:
        # Cleanup if requested
        if args.cleanup:
            benchmark.cleanup()


if __name__ == "__main__":
    main()