"""
Strategy Performance Tracking and Evaluation Module (V4)

This module tracks strategy performance metrics, compares strategies,
and provides recommendations for optimal strategy selection.
"""

import sqlite3
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from enum import Enum
import json


class StrategyType(Enum):
    """Enumeration of available reasoning strategies."""
    CONSERVATIVE = "conservative"
    BALANCED = "balanced"
    AGGRESSIVE = "aggressive"


class SituationType(Enum):
    """Enumeration of situation types."""
    NORMAL = "normal"
    ERROR_RECOVERY = "error_recovery"
    COMPLEX_TASK = "complex_task"
    TIME_CRITICAL = "time_critical"


@dataclass
class StrategyPerformanceMetrics:
    """Performance metrics for a strategy."""
    strategy: StrategyType
    task_type: str
    situation_type: SituationType
    success_rate: float = 0.0
    efficiency: float = 0.0  # Operations per second
    effectiveness: float = 0.0  # Quality score (0-1)
    robustness: float = 0.0  # Error handling capability
    total_operations: int = 0
    successful_operations: int = 0
    avg_time_per_operation: float = 0.0
    avg_tokens_per_operation: float = 0.0


@dataclass
class StrategyComparison:
    """Comparison result between strategies."""
    strategy: StrategyType
    rank: int
    score: float
    metrics: StrategyPerformanceMetrics
    advantages: List[str]
    disadvantages: List[str]


class StrategyEvaluator:
    """
    Evaluates and tracks strategy performance across multiple dimensions.
    
    Tracks:
    - Success rate per strategy
    - Efficiency (time, resources) per strategy
    - Effectiveness (quality of result) per strategy
    - Robustness (error handling) per strategy
    - Performance per task type
    - Performance per situation type
    """
    
    def __init__(self, db_path: str = "strategy_performance.db"):
        """
        Initialize the strategy evaluator.
        
        Args:
            db_path: Path to SQLite database for performance tracking
        """
        self.db_path = db_path
        self._init_database()
        
    def _init_database(self) -> None:
        """Initialize the SQLite database for performance tracking."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Strategy performance table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS strategy_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy TEXT NOT NULL,
                task_type TEXT NOT NULL,
                situation_type TEXT NOT NULL,
                success_rate REAL NOT NULL,
                efficiency REAL NOT NULL,
                effectiveness REAL NOT NULL,
                robustness REAL NOT NULL,
                total_operations INTEGER NOT NULL,
                successful_operations INTEGER NOT NULL,
                avg_time_per_operation REAL NOT NULL,
                avg_tokens_per_operation REAL NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(strategy, task_type, situation_type)
            )
        """)
        
        # Strategy operations log table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS strategy_operations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy TEXT NOT NULL,
                task_type TEXT NOT NULL,
                situation_type TEXT NOT NULL,
                success INTEGER NOT NULL,
                time_elapsed REAL NOT NULL,
                tokens_used INTEGER NOT NULL,
                quality_score REAL,
                error_handled INTEGER NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes for efficient queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_strategy_performance_lookup 
            ON strategy_performance(strategy, task_type, situation_type)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_strategy_operations_lookup 
            ON strategy_operations(strategy, task_type, situation_type)
        """)
        
        conn.commit()
        conn.close()
        
    def track_performance(
        self,
        strategy: StrategyType,
        task_type: str,
        situation_type: SituationType,
        success: bool,
        time_elapsed: float,
        tokens_used: int,
        quality_score: Optional[float] = None,
        error_handled: bool = False
    ) -> None:
        """
        Track a single strategy operation.
        
        Args:
            strategy: Strategy used
            task_type: Type of task (e.g., "planning", "implementation", "testing")
            situation_type: Type of situation (normal, error_recovery, etc.)
            success: Whether the operation was successful
            time_elapsed: Time taken for the operation (seconds)
            tokens_used: Tokens consumed by the operation
            quality_score: Quality of result (0-1, optional)
            error_handled: Whether an error was handled successfully
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Log the operation
        cursor.execute("""
            INSERT INTO strategy_operations 
            (strategy, task_type, situation_type, success, time_elapsed, 
             tokens_used, quality_score, error_handled)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            strategy.value,
            task_type,
            situation_type.value,
            1 if success else 0,
            time_elapsed,
            tokens_used,
            quality_score,
            1 if error_handled else 0
        ))
        
        # Update performance metrics
        self._update_performance_metrics(cursor, strategy, task_type, situation_type)
        
        conn.commit()
        conn.close()
        
    def _update_performance_metrics(
        self,
        cursor: sqlite3.Cursor,
        strategy: StrategyType,
        task_type: str,
        situation_type: SituationType
    ) -> None:
        """Update aggregated performance metrics for a strategy."""
        
        # Calculate metrics from operations log
        cursor.execute("""
            SELECT 
                COUNT(*) as total_ops,
                SUM(success) as successful_ops,
                AVG(time_elapsed) as avg_time,
                AVG(tokens_used) as avg_tokens,
                AVG(quality_score) as avg_quality,
                SUM(error_handled) as errors_handled
            FROM strategy_operations
            WHERE strategy = ? AND task_type = ? AND situation_type = ?
        """, (strategy.value, task_type, situation_type.value))
        
        row = cursor.fetchone()
        if not row:
            return
            
        total_ops, successful_ops, avg_time, avg_tokens, avg_quality, errors_handled = row
        
        if total_ops == 0:
            return
            
        # Calculate metrics
        success_rate = successful_ops / total_ops
        efficiency = 1.0 / (avg_time + 0.001)  # Operations per second (avoid division by zero)
        effectiveness = avg_quality if avg_quality else 0.0
        robustness = errors_handled / total_ops
        
        # Upsert performance metrics
        cursor.execute("""
            INSERT INTO strategy_performance 
            (strategy, task_type, situation_type, success_rate, efficiency,
             effectiveness, robustness, total_operations, successful_operations,
             avg_time_per_operation, avg_tokens_per_operation, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(strategy, task_type, situation_type) DO UPDATE SET
                success_rate = excluded.success_rate,
                efficiency = excluded.efficiency,
                effectiveness = excluded.effectiveness,
                robustness = excluded.robustness,
                total_operations = excluded.total_operations,
                successful_operations = excluded.successful_operations,
                avg_time_per_operation = excluded.avg_time_per_operation,
                avg_tokens_per_operation = excluded.avg_tokens_per_operation,
                updated_at = CURRENT_TIMESTAMP
        """, (
            strategy.value,
            task_type,
            situation_type.value,
            success_rate,
            efficiency,
            effectiveness,
            robustness,
            total_ops,
            successful_ops,
            avg_time,
            avg_tokens
        ))
        
    def get_performance(
        self,
        strategy: StrategyType,
        task_type: Optional[str] = None,
        situation_type: Optional[SituationType] = None
    ) -> Optional[StrategyPerformanceMetrics]:
        """
        Get performance metrics for a strategy.
        
        Args:
            strategy: Strategy to query
            task_type: Filter by task type (optional)
            situation_type: Filter by situation type (optional)
            
        Returns:
            StrategyPerformanceMetrics if found, None otherwise
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Build query dynamically based on filters
        query = """
            SELECT 
                strategy, task_type, situation_type, success_rate,
                efficiency, effectiveness, robustness, total_operations,
                successful_operations, avg_time_per_operation,
                avg_tokens_per_operation
            FROM strategy_performance
            WHERE strategy = ?
        """
        params = [strategy.value]
        
        if task_type is not None:
            query += " AND task_type = ?"
            params.append(task_type)
        
        if situation_type is not None:
            query += " AND situation_type = ?"
            params.append(situation_type.value)
        
        # If no specific filters, get the most used one
        if task_type is None and situation_type is None:
            query += " ORDER BY total_operations DESC LIMIT 1"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            return None
        
        # If multiple rows (different situation types for same task type), aggregate them
        if len(rows) == 1:
            row = rows[0]
            return StrategyPerformanceMetrics(
                strategy=StrategyType(row[0]),
                task_type=row[1],
                situation_type=SituationType(row[2]),
                success_rate=row[3],
                efficiency=row[4],
                effectiveness=row[5],
                robustness=row[6],
                total_operations=row[7],
                successful_operations=row[8],
                avg_time_per_operation=row[9],
                avg_tokens_per_operation=row[10]
            )
        else:
            # Aggregate across multiple situation types
            total_ops = sum(r[7] for r in rows)
            successful_ops = sum(r[8] for r in rows)
            
            if total_ops == 0:
                return None
            
            # Weighted averages based on operation count
            weighted_success_rate = successful_ops / total_ops
            weighted_efficiency = sum(r[4] * r[7] for r in rows) / total_ops
            weighted_effectiveness = sum(r[5] * r[7] for r in rows) / total_ops
            weighted_robustness = sum(r[6] * r[7] for r in rows) / total_ops
            weighted_time = sum(r[9] * r[7] for r in rows) / total_ops
            weighted_tokens = sum(r[10] * r[7] for r in rows) / total_ops
            
            # Use the most common task type
            task_type_agg = rows[0][1]
            # Use 'normal' as aggregate situation type
            situation_type_agg = SituationType.NORMAL
            
            return StrategyPerformanceMetrics(
                strategy=strategy,
                task_type=task_type_agg,
                situation_type=situation_type_agg,
                success_rate=weighted_success_rate,
                efficiency=weighted_efficiency,
                effectiveness=weighted_effectiveness,
                robustness=weighted_robustness,
                total_operations=total_ops,
                successful_operations=successful_ops,
                avg_time_per_operation=weighted_time,
                avg_tokens_per_operation=weighted_tokens
            )
        
    def compare_strategies(
        self,
        task_type: Optional[str] = None,
        situation_type: Optional[SituationType] = None,
        weights: Optional[Dict[str, float]] = None
    ) -> List[StrategyComparison]:
        """
        Compare and rank strategies across multiple dimensions.
        
        Args:
            task_type: Filter by task type (optional)
            situation_type: Filter by situation type (optional)
            weights: Custom weights for scoring (optional)
            
        Returns:
            List of StrategyComparison objects, sorted by rank
        """
        # Default weights: success rate is primary, others are secondary
        if weights is None:
            weights = {
                'success_rate': 0.5,
                'efficiency': 0.2,
                'effectiveness': 0.2,
                'robustness': 0.1
            }
        
        # Get performance for all strategies
        strategies = []
        for strategy in StrategyType:
            metrics = self.get_performance(strategy, task_type, situation_type)
            if metrics and metrics.total_operations > 0:
                strategies.append(metrics)
        
        # If no data, return empty list
        if not strategies:
            return []
        
        # Calculate scores and rank
        comparisons = []
        for metrics in strategies:
            score = (
                weights['success_rate'] * metrics.success_rate +
                weights['efficiency'] * min(metrics.efficiency / 100, 1.0) +  # Normalize efficiency
                weights['effectiveness'] * metrics.effectiveness +
                weights['robustness'] * metrics.robustness
            )
            
            advantages = []
            disadvantages = []
            
            # Compare with other strategies
            for other in strategies:
                if other.strategy == metrics.strategy:
                    continue
                    
                if metrics.success_rate > other.success_rate:
                    advantages.append(f"Higher success rate ({metrics.success_rate:.1%} vs {other.success_rate:.1%})")
                elif metrics.success_rate < other.success_rate:
                    disadvantages.append(f"Lower success rate ({metrics.success_rate:.1%} vs {other.success_rate:.1%})")
                    
                if metrics.efficiency > other.efficiency:
                    advantages.append(f"More efficient ({metrics.efficiency:.2f} vs {other.efficiency:.2f})")
                elif metrics.efficiency < other.efficiency:
                    disadvantages.append(f"Less efficient ({metrics.efficiency:.2f} vs {other.efficiency:.2f})")
            
            comparisons.append(StrategyComparison(
                strategy=metrics.strategy,
                rank=0,  # Will be set after sorting
                score=score,
                metrics=metrics,
                advantages=advantages,
                disadvantages=disadvantages
            ))
    
        # Sort by score and assign ranks
        comparisons.sort(key=lambda x: x.score, reverse=True)
        for i, comparison in enumerate(comparisons):
            comparison.rank = i + 1
    
        return comparisons
    
    def get_optimal_strategy(
        self,
        task_type: Optional[str] = None,
        situation_type: Optional[SituationType] = None,
        weights: Optional[Dict[str, float]] = None
    ) -> Optional[StrategyType]:
        """
        Get the optimal strategy for a given task and situation.
        
        Args:
            task_type: Type of task (optional)
            situation_type: Type of situation (optional)
            weights: Custom weights for scoring (optional)
            
        Returns:
            Optimal StrategyType if data available, None otherwise
        """
        comparisons = self.compare_strategies(task_type, situation_type, weights)
        if not comparisons:
            return None
        
        return comparisons[0].strategy
    
    def generate_performance_report(
        self,
        task_type: Optional[str] = None,
        situation_type: Optional[SituationType] = None
    ) -> str:
        """
        Generate a performance report for all strategies.
        
        Args:
            task_type: Filter by task type (optional)
            situation_type: Filter by situation type (optional)
            
        Returns:
            Formatted performance report as string
        """
        comparisons = self.compare_strategies(task_type, situation_type)
        
        if not comparisons:
            return "No performance data available."
        
        report = []
        report.append("=" * 80)
        report.append("STRATEGY PERFORMANCE REPORT")
        report.append("=" * 80)
        
        if task_type:
            report.append(f"Task Type: {task_type}")
        if situation_type:
            report.append(f"Situation Type: {situation_type.value}")
        report.append("")
        
        for comp in comparisons:
            report.append(f"Rank {comp.rank}: {comp.strategy.value.upper()}")
            report.append(f"  Score: {comp.score:.3f}")
            report.append(f"  Success Rate: {comp.metrics.success_rate:.1%} ({comp.metrics.successful_operations}/{comp.metrics.total_operations})")
            report.append(f"  Efficiency: {comp.metrics.efficiency:.2f} ops/sec")
            report.append(f"  Effectiveness: {comp.metrics.effectiveness:.2f}/1.0")
            report.append(f"  Robustness: {comp.metrics.robustness:.1%}")
            report.append(f"  Avg Time: {comp.metrics.avg_time_per_operation:.3f}s")
            report.append(f"  Avg Tokens: {comp.metrics.avg_tokens_per_operation:.0f}")
            
            if comp.advantages:
                report.append(f"  Advantages:")
                for adv in comp.advantages:
                    report.append(f"    - {adv}")
                    
            if comp.disadvantages:
                report.append(f"  Disadvantages:")
                for dis in comp.disadvantages:
                    report.append(f"    - {dis}")
                    
            report.append("")
        
        report.append("=" * 80)
        
        return "\n".join(report)
    
    def export_performance_data(
        self,
        filepath: str,
        task_type: Optional[str] = None,
        situation_type: Optional[SituationType] = None
    ) -> None:
        """
        Export performance data to JSON file.
        
        Args:
            filepath: Path to output JSON file
            task_type: Filter by task type (optional)
            situation_type: Filter by situation type (optional)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = "SELECT * FROM strategy_performance WHERE 1=1"
        params = []
        
        if task_type:
            query += " AND task_type = ?"
            params.append(task_type)
        if situation_type:
            query += " AND situation_type = ?"
            params.append(situation_type.value)
            
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        # Convert to list of dicts
        columns = [
            'id', 'strategy', 'task_type', 'situation_type', 'success_rate',
            'efficiency', 'effectiveness', 'robustness', 'total_operations',
            'successful_operations', 'avg_time_per_operation', 
            'avg_tokens_per_operation', 'updated_at'
        ]
        
        data = [dict(zip(columns, row)) for row in rows]
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)
    
    def get_strategy_rankings(
        self,
        task_type: Optional[str] = None
    ) -> Dict[StrategyType, int]:
        """
        Get strategy rankings across all or specific task types.
        
        Args:
            task_type: Filter by task type (optional)
            
        Returns:
            Dictionary mapping StrategyType to rank (1-based)
        """
        comparisons = self.compare_strategies(task_type=task_type)
        
        rankings = {}
        for comp in comparisons:
            rankings[comp.strategy] = comp.rank
            
        return rankings
    
    def get_recommendations(
        self,
        task_type: str,
        situation_type: SituationType
    ) -> Tuple[Optional[StrategyType], str]:
        """
        Get strategy recommendation with explanation.
        
        Args:
            task_type: Type of task
            situation_type: Type of situation
            
        Returns:
            Tuple of (StrategyType, explanation)
        """
        optimal = self.get_optimal_strategy(task_type, situation_type)
        
        if optimal is None:
            return StrategyType.BALANCED, "No performance data available, using default balanced strategy."
        
        comparisons = self.compare_strategies(task_type, situation_type)
        best = comparisons[0]
        
        explanation = f"Recommended {best.strategy.value} strategy. "
        explanation += f"Based on {best.metrics.total_operations} operations, "
        explanation += f"with {best.metrics.success_rate:.1%} success rate. "
        
        if best.advantages:
            explanation += f"Key advantages: {', '.join(best.advantages[:2])}."
        
        return optimal, explanation
    
    def identify_optimal_combinations(
        self,
        task_type: str,
        min_combinations: int = 3,
        min_success_rate: float = 0.6
    ) -> List[Dict]:
        """
        Identify optimal strategy combinations for different phases of a task.
        
        Analyzes strategy performance across different situation types to find
        combinations that work well together for complete task execution.
        
        Args:
            task_type: Type of task to analyze
            min_combinations: Minimum number of combinations to return
            min_success_rate: Minimum success rate threshold for combinations
            
        Returns:
            List of strategy combination dictionaries with scores and rationale
        """
        # Get performance data for all strategies across all situation types
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT strategy, situation_type, success_rate, total_operations
            FROM strategy_performance
            WHERE task_type = ? AND total_operations >= 5
        """, (task_type,))
        
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            return []
        
        # Group performance by strategy and situation type
        perf_data = {}
        for strategy, situation, success_rate, ops in rows:
            if strategy not in perf_data:
                perf_data[strategy] = {}
            perf_data[strategy][SituationType(situation)] = {
                'success_rate': success_rate,
                'operations': ops
            }
        
        # Generate strategy combinations for different task phases
        combinations = []
        
        # Common task phase patterns:
        # 1. Planning -> Implementation -> Testing
        # 2. Simple tasks: single strategy throughout
        # 3. Complex tasks: conservative planning -> balanced implementation -> conservative testing
        # 4. Time-critical tasks: aggressive where possible
        
        # Combination 1: Conservative throughout (safest)
        if 'conservative' in perf_data:
            combo_score = self._calculate_combination_score(
                perf_data['conservative'],
                [SituationType.NORMAL, SituationType.COMPLEX_TASK, SituationType.ERROR_RECOVERY]
            )
            if combo_score >= min_success_rate:
                combinations.append({
                    'strategy': 'conservative',
                    'phases': {
                        'planning': 'conservative',
                        'implementation': 'conservative',
                        'testing': 'conservative'
                    },
                    'overall_score': combo_score,
                    'rationale': 'Highest safety and quality, lowest risk',
                    'best_for': 'Critical tasks, production deployments, complex refactoring'
                })
        
        # Combination 2: Balanced throughout (recommended default)
        if 'balanced' in perf_data:
            combo_score = self._calculate_combination_score(
                perf_data['balanced'],
                [SituationType.NORMAL, SituationType.COMPLEX_TASK, SituationType.ERROR_RECOVERY]
            )
            if combo_score >= min_success_rate:
                combinations.append({
                    'strategy': 'balanced',
                    'phases': {
                        'planning': 'balanced',
                        'implementation': 'balanced',
                        'testing': 'balanced'
                    },
                    'overall_score': combo_score,
                    'rationale': 'Optimal balance of speed, quality, and safety',
                    'best_for': 'Most development tasks, feature implementation'
                })
        
        # Combination 3: Aggressive throughout (fastest)
        if 'aggressive' in perf_data:
            combo_score = self._calculate_combination_score(
                perf_data['aggressive'],
                [SituationType.NORMAL, SituationType.TIME_CRITICAL, SituationType.COMPLEX_TASK]
            )
            if combo_score >= min_success_rate:
                combinations.append({
                    'strategy': 'aggressive',
                    'phases': {
                        'planning': 'aggressive',
                        'implementation': 'aggressive',
                        'testing': 'aggressive'
                    },
                    'overall_score': combo_score,
                    'rationale': 'Maximum speed, higher risk',
                    'best_for': 'Prototyping, time-critical tasks, low-risk features'
                })
        
        # Combination 4: Hybrid - Conservative planning, Balanced implementation, Conservative testing
        if 'conservative' in perf_data and 'balanced' in perf_data:
            scores = []
            scores.append(perf_data['conservative'].get(SituationType.NORMAL, {}).get('success_rate', 0.5))
            scores.append(perf_data['balanced'].get(SituationType.NORMAL, {}).get('success_rate', 0.5))
            scores.append(perf_data['conservative'].get(SituationType.ERROR_RECOVERY, {}).get('success_rate', 0.5))
            combo_score = sum(scores) / len(scores) if scores else 0.0
            
            if combo_score >= min_success_rate:
                combinations.append({
                    'strategy': 'conservative_balanced_conservative',
                    'phases': {
                        'planning': 'conservative',
                        'implementation': 'balanced',
                        'testing': 'conservative'
                    },
                    'overall_score': combo_score,
                    'rationale': 'Safe planning, efficient implementation, thorough testing',
                    'best_for': 'Quality-critical features, production code'
                })
        
        # Combination 5: Balanced planning, Aggressive implementation, Balanced testing
        if 'balanced' in perf_data and 'aggressive' in perf_data:
            scores = []
            scores.append(perf_data['balanced'].get(SituationType.NORMAL, {}).get('success_rate', 0.5))
            scores.append(perf_data['aggressive'].get(SituationType.TIME_CRITICAL, {}).get('success_rate', 0.5))
            scores.append(perf_data['balanced'].get(SituationType.ERROR_RECOVERY, {}).get('success_rate', 0.5))
            combo_score = sum(scores) / len(scores) if scores else 0.0
            
            if combo_score >= min_success_rate:
                combinations.append({
                    'strategy': 'balanced_aggressive_balanced',
                    'phases': {
                        'planning': 'balanced',
                        'implementation': 'aggressive',
                        'testing': 'balanced'
                    },
                    'overall_score': combo_score,
                    'rationale': 'Good planning, fast implementation, reliable testing',
                    'best_for': 'Standard features with time constraints'
                })
        
        # Sort by overall score
        combinations.sort(key=lambda x: x['overall_score'], reverse=True)
        
        # Return top N combinations
        return combinations[:min_combinations]
    
    def _calculate_combination_score(
        self,
        strategy_perf: Dict,
        situation_types: List[SituationType]
    ) -> float:
        """
        Calculate overall score for a strategy across multiple situation types.
        
        Args:
            strategy_perf: Performance data for a single strategy
            situation_types: List of situation types to include in score
            
        Returns:
            Weighted average score (0-1)
        """
        scores = []
        for sit_type in situation_types:
            if sit_type in strategy_perf:
                scores.append(strategy_perf[sit_type]['success_rate'])
        
        return sum(scores) / len(scores) if scores else 0.0
    
    def get_adaptive_weights(
        self,
        situation_type: SituationType
    ) -> Dict[str, float]:
        """
        Get adaptive scoring weights based on situation type.
        
        Args:
            situation_type: Current situation type
            
        Returns:
            Dictionary of weights for scoring dimensions
        """
        # Weights adapt based on situation:
        # - Time Critical: Higher weight on efficiency
        # - Error Recovery: Higher weight on success rate
        # - Complex Task: Higher weight on effectiveness
        # - Normal: Balanced weights
        
        if situation_type == SituationType.TIME_CRITICAL:
            return {
                'success_rate': 0.3,
                'efficiency': 0.4,
                'effectiveness': 0.2,
                'robustness': 0.1
            }
        elif situation_type == SituationType.ERROR_RECOVERY:
            return {
                'success_rate': 0.6,
                'efficiency': 0.1,
                'effectiveness': 0.2,
                'robustness': 0.1
            }
        elif situation_type == SituationType.COMPLEX_TASK:
            return {
                'success_rate': 0.4,
                'efficiency': 0.1,
                'effectiveness': 0.4,
                'robustness': 0.1
            }
        else:  # NORMAL
            return {
                'success_rate': 0.5,
                'efficiency': 0.2,
                'effectiveness': 0.2,
                'robustness': 0.1
            }
    
    def compare_strategies_dynamic(
        self,
        task_type: Optional[str] = None,
        situation_type: Optional[SituationType] = None
    ) -> List[StrategyComparison]:
        """
        Compare strategies with situation-adaptive weights.
        
        Uses adaptive weights that change based on the current situation type
        to provide more relevant rankings.
        
        Args:
            task_type: Filter by task type (optional)
            situation_type: Filter by situation type (optional)
            
        Returns:
            List of StrategyComparison objects, sorted by rank
        """
        # Get adaptive weights based on situation
        if situation_type:
            weights = self.get_adaptive_weights(situation_type)
        else:
            weights = None  # Use default weights
        
        # Use compare_strategies with adaptive weights
        return self.compare_strategies(task_type, situation_type, weights)


if __name__ == "__main__":
    # Test
    evaluator = StrategyEvaluator("test_strategy_performance.db")
    
    # Simulate some operations
    evaluator.track_performance(
        StrategyType.BALANCED,
        "implementation",
        SituationType.NORMAL,
        success=True,
        time_elapsed=1.5,
        tokens_used=1200,
        quality_score=0.85
    )
    
    evaluator.track_performance(
        StrategyType.AGGRESSIVE,
        "implementation",
        SituationType.TIME_CRITICAL,
        success=True,
        time_elapsed=0.8,
        tokens_used=800,
        quality_score=0.75
    )
    
    evaluator.track_performance(
        StrategyType.CONSERVATIVE,
        "implementation",
        SituationType.ERROR_RECOVERY,
        success=True,
        time_elapsed=2.3,
        tokens_used=1500,
        quality_score=0.95,
        error_handled=True
    )
    
    # Generate report
    print(evaluator.generate_performance_report(task_type="implementation"))
    
    # Get recommendation
    strategy, explanation = evaluator.get_recommendations("implementation", SituationType.NORMAL)
    print(f"\nRecommendation: {explanation}")