"""
Context Quality Tracker - V5 Quality Enhancement

This module implements comprehensive context quality metrics to measure and improve
context quality over time, correlating with task success rates.

Quality Metrics:
- Completeness: % of required context items included
- Relevance: Average relevance score of included items
- Freshness: Average age of context items (newer = better)
- Conciseness: Information density (more = better)
- Diversity: Variety of context sources (files, modules)
"""

import sqlite3
import json
import math
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import statistics


class QualityMetric(Enum):
    """Quality metric types"""
    COMPLETENESS = "completeness"
    RELEVANCE = "relevance"
    FRESHNESS = "freshness"
    CONCISENESS = "conciseness"
    DIVERSITY = "diversity"


@dataclass
class ContextQualityMetrics:
    """Context quality metrics for a single task"""
    task_id: str
    task_type: str
    timestamp: datetime
    
    # Individual metrics (0.0 - 1.0)
    completeness: float
    relevance: float
    freshness: float
    conciseness: float
    diversity: float
    
    # Overall quality score (weighted average)
    overall_quality: float
    
    # Context metadata
    context_items_count: int
    total_tokens: int
    unique_sources: int
    
    # Task outcome
    success: bool
    attempts: int
    execution_time_seconds: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = asdict(self)
        result['timestamp'] = self.timestamp.isoformat()
        return result


@dataclass
class QualityThreshold:
    """Quality threshold configuration"""
    low_threshold: float = 0.5
    medium_threshold: float = 0.75
    high_threshold: float = 0.9
    
    def get_quality_level(self, score: float) -> str:
        """Get quality level from score"""
        if score < self.low_threshold:
            return "LOW"
        elif score < self.medium_threshold:
            return "MEDIUM"
        elif score < self.high_threshold:
            return "HIGH"
        else:
            return "EXCELLENT"


@dataclass
class QualityReport:
    """Comprehensive quality report"""
    period_start: datetime
    period_end: datetime
    total_tasks: int
    successful_tasks: int
    
    # Quality averages
    avg_completeness: float
    avg_relevance: float
    avg_freshness: float
    avg_conciseness: float
    avg_diversity: float
    avg_overall_quality: float
    
    # Success rates by quality level
    success_rate_low_quality: float
    success_rate_medium_quality: float
    success_rate_high_quality: float
    success_rate_excellent_quality: float
    
    # Quality trends
    quality_trend: str  # "IMPROVING", "STABLE", "DECLINING"
    quality_change_rate: float  # percentage change
    
    # Recommendations
    recommendations: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = asdict(self)
        result['period_start'] = self.period_start.isoformat()
        result['period_end'] = self.period_end.isoformat()
        return result


class ContextQualityTracker:
    """
    Context Quality Tracker
    
    Tracks context quality metrics over time, correlates with task success,
    and generates quality reports with improvement recommendations.
    """
    
    def __init__(self, db_path: str = "context_quality.db"):
        """
        Initialize context quality tracker.
        
        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
        self.conn = None
        self.threshold = QualityThreshold()
        
        # Quality weights for overall score
        self.quality_weights = {
            QualityMetric.COMPLETENESS: 0.3,
            QualityMetric.RELEVANCE: 0.3,
            QualityMetric.FRESHNESS: 0.2,
            QualityMetric.CONCISENESS: 0.1,
            QualityMetric.DIVERSITY: 0.1
        }
    
    def connect(self):
        """Connect to database"""
        self.conn = sqlite3.connect(self.db_path)
        self._create_tables()
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def _create_tables(self):
        """Create database tables"""
        cursor = self.conn.cursor()
        
        # Context quality metrics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS context_quality (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                task_type TEXT NOT NULL,
                timestamp DATETIME NOT NULL,
                completeness REAL NOT NULL,
                relevance REAL NOT NULL,
                freshness REAL NOT NULL,
                conciseness REAL NOT NULL,
                diversity REAL NOT NULL,
                overall_quality REAL NOT NULL,
                context_items_count INTEGER NOT NULL,
                total_tokens INTEGER NOT NULL,
                unique_sources INTEGER NOT NULL,
                success INTEGER NOT NULL,
                attempts INTEGER NOT NULL,
                execution_time_seconds REAL NOT NULL
            )
        """)
        
        # Quality correlation table (for analyzing success vs quality)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quality_correlation (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                quality_level TEXT NOT NULL,
                total_tasks INTEGER NOT NULL,
                successful_tasks INTEGER NOT NULL,
                success_rate REAL NOT NULL,
                avg_attempts REAL NOT NULL,
                avg_execution_time REAL NOT NULL,
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Quality recommendations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quality_recommendations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric TEXT NOT NULL,
                issue TEXT NOT NULL,
                suggestion TEXT NOT NULL,
                priority TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                applied INTEGER DEFAULT 0,
                effectiveness REAL
            )
        """)
        
        # Create indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_quality_task 
            ON context_quality(task_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_quality_task_type 
            ON context_quality(task_type)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_quality_timestamp 
            ON context_quality(timestamp)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_quality_overall 
            ON context_quality(overall_quality)
        """)
        
        self.conn.commit()
    
    def calculate_completeness(
        self,
        required_context: List[str],
        provided_context: List[str]
    ) -> float:
        """
        Calculate completeness metric.
        
        Args:
            required_context: List of required context items
            provided_context: List of provided context items
            
        Returns:
            Completeness score (0.0 - 1.0)
        """
        if not required_context:
            return 1.0  # Perfect if no requirements
        
        required_set = set(item.lower() for item in required_context)
        provided_set = set(item.lower() for item in provided_context)
        
        matched = required_set & provided_set
        return len(matched) / len(required_set)
    
    def calculate_relevance(
        self,
        context_items: List[Dict[str, Any]]
    ) -> float:
        """
        Calculate relevance metric.
        
        Args:
            context_items: List of context items with 'relevance_score' field
            
        Returns:
            Average relevance score (0.0 - 1.0)
        """
        if not context_items:
            return 0.0
        
        relevance_scores = [
            item.get('relevance_score', 0.0)
            for item in context_items
        ]
        
        return statistics.mean(relevance_scores)
    
    def calculate_freshness(
        self,
        context_items: List[Dict[str, Any]],
        reference_time: Optional[datetime] = None
    ) -> float:
        """
        Calculate freshness metric.
        
        Args:
            context_items: List of context items with 'timestamp' or 'modified' field
            reference_time: Reference time for freshness calculation (default: now)
            
        Returns:
            Freshness score (0.0 - 1.0, newer = better)
        """
        if not context_items:
            return 0.0
        
        reference_time = reference_time or datetime.now()
        
        # Calculate age for each context item
        ages = []
        max_age_days = 30.0  # Max age for normalization
        
        for item in context_items:
            timestamp_str = item.get('timestamp') or item.get('modified')
            if not timestamp_str:
                ages.append(max_age_days)  # Assume oldest if no timestamp
                continue
            
            try:
                if isinstance(timestamp_str, str):
                    timestamp = datetime.fromisoformat(timestamp_str)
                else:
                    timestamp = timestamp_str
                
                age = (reference_time - timestamp).total_seconds() / 86400.0
                ages.append(min(age, max_age_days))
            except (ValueError, TypeError):
                ages.append(max_age_days)
        
        # Normalize to 0-1 (younger = higher score)
        avg_age = statistics.mean(ages)
        freshness = max(0.0, 1.0 - (avg_age / max_age_days))
        
        return freshness
    
    def calculate_conciseness(
        self,
        context_items: List[Dict[str, Any]]
    ) -> float:
        """
        Calculate conciseness metric (information density).
        
        Args:
            context_items: List of context items with 'content' and 'token_count' fields
            
        Returns:
            Conciseness score (0.0 - 1.0)
        """
        if not context_items:
            return 0.0
        
        # Calculate information density (tokens / characters ratio)
        # Higher density = more information per character = more concise
        densities = []
        
        for item in context_items:
            content = item.get('content', '')
            token_count = item.get('token_count', len(content) // 3)
            char_count = len(content.strip())
            
            if char_count == 0:
                densities.append(0.0)
                continue
            
            # Density: tokens per character (typically 0.1 - 0.33)
            # Normalize to 0-1 (0.33 is optimal ~3 chars per token)
            density = token_count / char_count
            normalized_density = min(density / 0.33, 1.0)
            densities.append(normalized_density)
        
        return statistics.mean(densities)
    
    def calculate_diversity(
        self,
        context_items: List[Dict[str, Any]]
    ) -> float:
        """
        Calculate diversity metric (variety of context sources).
        
        Args:
            context_items: List of context items with 'source' field
            
        Returns:
            Diversity score (0.0 - 1.0)
        """
        if not context_items:
            return 0.0
        
        # Count unique sources
        sources = [item.get('source', 'unknown') for item in context_items]
        unique_sources = len(set(sources))
        total_sources = len(sources)
        
        # Normalize to 0-1
        # Ideal: each item from different source (unique_sources == total_sources)
        diversity = unique_sources / total_sources
        
        return diversity
    
    def calculate_overall_quality(
        self,
        metrics: Dict[QualityMetric, float]
    ) -> float:
        """
        Calculate overall quality score using weighted average.
        
        Args:
            metrics: Dictionary of metric scores
            
        Returns:
            Overall quality score (0.0 - 1.0)
        """
        total_score = 0.0
        total_weight = 0.0
        
        for metric, score in metrics.items():
            weight = self.quality_weights.get(metric, 0.2)
            total_score += score * weight
            total_weight += weight
        
        return total_score / total_weight if total_weight > 0 else 0.0
    
    def record_context_quality(
        self,
        task_id: str,
        task_type: str,
        required_context: List[str],
        provided_context: List[str],
        context_items: List[Dict[str, Any]],
        success: bool,
        attempts: int = 1,
        execution_time_seconds: float = 0.0
    ) -> ContextQualityMetrics:
        """
        Record context quality for a task.
        
        Args:
            task_id: Unique task identifier
            task_type: Type of task (planning, implementation, verification, etc.)
            required_context: List of required context items
            provided_context: List of provided context items
            context_items: List of context items with metadata
            success: Whether task was successful
            attempts: Number of attempts made
            execution_time_seconds: Execution time in seconds
            
        Returns:
            ContextQualityMetrics object with calculated metrics
        """
        # Calculate individual metrics
        completeness = self.calculate_completeness(
            required_context,
            provided_context
        )
        relevance = self.calculate_relevance(context_items)
        freshness = self.calculate_freshness(context_items)
        conciseness = self.calculate_conciseness(context_items)
        diversity = self.calculate_diversity(context_items)
        
        # Calculate overall quality
        metrics = {
            QualityMetric.COMPLETENESS: completeness,
            QualityMetric.RELEVANCE: relevance,
            QualityMetric.FRESHNESS: freshness,
            QualityMetric.CONCISENESS: conciseness,
            QualityMetric.DIVERSITY: diversity
        }
        overall_quality = self.calculate_overall_quality(metrics)
        
        # Count context items and tokens
        context_items_count = len(context_items)
        total_tokens = sum(
            item.get('token_count', 0)
            for item in context_items
        )
        unique_sources = len(set(
            item.get('source', 'unknown')
            for item in context_items
        ))
        
        # Create metrics object
        quality_metrics = ContextQualityMetrics(
            task_id=task_id,
            task_type=task_type,
            timestamp=datetime.now(),
            completeness=completeness,
            relevance=relevance,
            freshness=freshness,
            conciseness=conciseness,
            diversity=diversity,
            overall_quality=overall_quality,
            context_items_count=context_items_count,
            total_tokens=total_tokens,
            unique_sources=unique_sources,
            success=success,
            attempts=attempts,
            execution_time_seconds=execution_time_seconds
        )
        
        # Save to database
        self._save_quality_metrics(quality_metrics)
        
        # Update correlation data
        self._update_correlation_data()
        
        return quality_metrics
    
    def _save_quality_metrics(self, metrics: ContextQualityMetrics):
        """Save quality metrics to database"""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            INSERT INTO context_quality (
                task_id, task_type, timestamp,
                completeness, relevance, freshness, conciseness, diversity,
                overall_quality, context_items_count, total_tokens, unique_sources,
                success, attempts, execution_time_seconds
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            metrics.task_id,
            metrics.task_type,
            metrics.timestamp.isoformat(),
            metrics.completeness,
            metrics.relevance,
            metrics.freshness,
            metrics.conciseness,
            metrics.diversity,
            metrics.overall_quality,
            metrics.context_items_count,
            metrics.total_tokens,
            metrics.unique_sources,
            1 if metrics.success else 0,
            metrics.attempts,
            metrics.execution_time_seconds
        ))
        
        self.conn.commit()
    
    def _update_correlation_data(self):
        """Update quality correlation analysis"""
        cursor = self.conn.cursor()
        
        # Calculate success rates for each quality level
        for level in ["LOW", "MEDIUM", "HIGH", "EXCELLENT"]:
            # Get quality range for this level
            if level == "LOW":
                quality_min = 0.0
                quality_max = self.threshold.low_threshold
            elif level == "MEDIUM":
                quality_min = self.threshold.low_threshold
                quality_max = self.threshold.medium_threshold
            elif level == "HIGH":
                quality_min = self.threshold.medium_threshold
                quality_max = self.threshold.high_threshold
            else:  # EXCELLENT
                quality_min = self.threshold.high_threshold
                quality_max = 1.0
            
            # Get tasks in this quality range
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(success) as successful,
                    AVG(attempts) as avg_attempts,
                    AVG(execution_time_seconds) as avg_execution_time
                FROM context_quality
                WHERE overall_quality >= ? AND overall_quality < ?
            """, (quality_min, quality_max))
            
            result = cursor.fetchone()
            if result and result[0] > 0:
                total, successful, avg_attempts, avg_execution_time = result
                success_rate = (successful / total) if total > 0 else 0.0
                
                # Update or insert correlation data
                cursor.execute("""
                    INSERT OR REPLACE INTO quality_correlation 
                    (quality_level, total_tasks, successful_tasks, success_rate, 
                     avg_attempts, avg_execution_time, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    level,
                    total,
                    int(successful),
                    success_rate,
                    avg_attempts or 0.0,
                    avg_execution_time or 0.0,
                    datetime.now().isoformat()
                ))
        
        self.conn.commit()
    
    def get_quality_metrics(
        self,
        task_id: Optional[str] = None,
        task_type: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[ContextQualityMetrics]:
        """
        Retrieve quality metrics.
        
        Args:
            task_id: Filter by task ID
            task_type: Filter by task type
            start_time: Filter by start time
            end_time: Filter by end time
            
        Returns:
            List of ContextQualityMetrics objects
        """
        cursor = self.conn.cursor()
        
        query = "SELECT * FROM context_quality WHERE 1=1"
        params = []
        
        if task_id:
            query += " AND task_id = ?"
            params.append(task_id)
        
        if task_type:
            query += " AND task_type = ?"
            params.append(task_type)
        
        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time.isoformat())
        
        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time.isoformat())
        
        query += " ORDER BY timestamp DESC"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        # Convert to ContextQualityMetrics objects
        metrics_list = []
        for row in rows:
            metrics_list.append(ContextQualityMetrics(
                task_id=row[1],
                task_type=row[2],
                timestamp=datetime.fromisoformat(row[3]),
                completeness=row[4],
                relevance=row[5],
                freshness=row[6],
                conciseness=row[7],
                diversity=row[8],
                overall_quality=row[9],
                context_items_count=row[10],
                total_tokens=row[11],
                unique_sources=row[12],
                success=bool(row[13]),
                attempts=row[14],
                execution_time_seconds=row[15]
            ))
        
        return metrics_list
    
    def generate_quality_report(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> QualityReport:
        """
        Generate comprehensive quality report.
        
        Args:
            start_time: Report start time (default: 30 days ago)
            end_time: Report end time (default: now)
            
        Returns:
            QualityReport object with comprehensive analysis
        """
        cursor = self.conn.cursor()
        
        # Default time range: last 30 days
        if not end_time:
            end_time = datetime.now()
        if not start_time:
            start_time = end_time - timedelta(days=30)
        
        # Get all metrics in time range
        cursor.execute("""
            SELECT * FROM context_quality
            WHERE timestamp >= ? AND timestamp <= ?
            ORDER BY timestamp
        """, (start_time.isoformat(), end_time.isoformat()))
        
        rows = cursor.fetchall()
        
        if not rows:
            # Return empty report
            return QualityReport(
                period_start=start_time,
                period_end=end_time,
                total_tasks=0,
                successful_tasks=0,
                avg_completeness=0.0,
                avg_relevance=0.0,
                avg_freshness=0.0,
                avg_conciseness=0.0,
                avg_diversity=0.0,
                avg_overall_quality=0.0,
                success_rate_low_quality=0.0,
                success_rate_medium_quality=0.0,
                success_rate_high_quality=0.0,
                success_rate_excellent_quality=0.0,
                quality_trend="STABLE",
                quality_change_rate=0.0,
                recommendations=[]
            )
        
        # Calculate averages
        total_tasks = len(rows)
        successful_tasks = sum(1 for row in rows if row[13] == 1)
        
        avg_completeness = statistics.mean(row[4] for row in rows)
        avg_relevance = statistics.mean(row[5] for row in rows)
        avg_freshness = statistics.mean(row[6] for row in rows)
        avg_conciseness = statistics.mean(row[7] for row in rows)
        avg_diversity = statistics.mean(row[8] for row in rows)
        avg_overall_quality = statistics.mean(row[9] for row in rows)
        
        # Get success rates by quality level
        cursor.execute("""
            SELECT quality_level, success_rate
            FROM quality_correlation
            WHERE quality_level IN ('LOW', 'MEDIUM', 'HIGH', 'EXCELLENT')
            ORDER BY 
                CASE quality_level
                    WHEN 'LOW' THEN 1
                    WHEN 'MEDIUM' THEN 2
                    WHEN 'HIGH' THEN 3
                    WHEN 'EXCELLENT' THEN 4
                END
        """)
        
        success_rates = cursor.fetchall()
        success_rate_dict = dict(success_rates)
        
        success_rate_low = success_rate_dict.get('LOW', 0.0)
        success_rate_medium = success_rate_dict.get('MEDIUM', 0.0)
        success_rate_high = success_rate_dict.get('HIGH', 0.0)
        success_rate_excellent = success_rate_dict.get('EXCELLENT', 0.0)
        
        # Calculate quality trend
        if total_tasks >= 2:
            first_half = rows[:total_tasks // 2]
            second_half = rows[total_tasks // 2:]
            
            avg_first_half = statistics.mean(row[9] for row in first_half)
            avg_second_half = statistics.mean(row[9] for row in second_half)
            
            change_rate = ((avg_second_half - avg_first_half) / avg_first_half) * 100
            
            if abs(change_rate) < 5.0:
                quality_trend = "STABLE"
            elif change_rate > 0:
                quality_trend = "IMPROVING"
            else:
                quality_trend = "DECLINING"
        else:
            quality_trend = "STABLE"
            change_rate = 0.0
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            avg_completeness,
            avg_relevance,
            avg_freshness,
            avg_conciseness,
            avg_diversity
        )
        
        return QualityReport(
            period_start=start_time,
            period_end=end_time,
            total_tasks=total_tasks,
            successful_tasks=successful_tasks,
            avg_completeness=avg_completeness,
            avg_relevance=avg_relevance,
            avg_freshness=avg_freshness,
            avg_conciseness=avg_conciseness,
            avg_diversity=avg_diversity,
            avg_overall_quality=avg_overall_quality,
            success_rate_low_quality=success_rate_low,
            success_rate_medium_quality=success_rate_medium,
            success_rate_high_quality=success_rate_high,
            success_rate_excellent_quality=success_rate_excellent,
            quality_trend=quality_trend,
            quality_change_rate=change_rate,
            recommendations=recommendations
        )
    
    def _generate_recommendations(
        self,
        completeness: float,
        relevance: float,
        freshness: float,
        conciseness: float,
        diversity: float
    ) -> List[str]:
        """
        Generate improvement recommendations based on quality metrics.
        
        Args:
            completeness: Average completeness score
            relevance: Average relevance score
            freshness: Average freshness score
            conciseness: Average conciseness score
            diversity: Average diversity score
            
        Returns:
            List of recommendation strings
        """
        recommendations = []
        
        if completeness < self.threshold.medium_threshold:
            recommendations.append(
                "LOW COMPLETENESS: Add missing required context items. "
                "Ensure all necessary files and modules are included."
            )
        
        if relevance < self.threshold.medium_threshold:
            recommendations.append(
                "LOW RELEVANCE: Improve context filtering. "
                "Use more precise task impact analysis and relevance scoring."
            )
        
        if freshness < self.threshold.medium_threshold:
            recommendations.append(
                "LOW FRESHNESS: Update stale context items. "
                "Refresh cached context more frequently or use shorter TTL."
            )
        
        if conciseness < self.threshold.medium_threshold:
            recommendations.append(
                "LOW CONCISENESS: Compress verbose contexts. "
                "Use context compression to remove unnecessary comments and whitespace."
            )
        
        if diversity < self.threshold.medium_threshold:
            recommendations.append(
                "LOW DIVERSITY: Include context from more sources. "
                "Add documentation, tests, and configuration files to context."
            )
        
        return recommendations
    
    def get_correlation_data(self) -> Dict[str, Dict[str, Any]]:
        """
        Get quality correlation with task success.
        
        Returns:
            Dictionary mapping quality levels to correlation data
        """
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT quality_level, total_tasks, successful_tasks, 
                   success_rate, avg_attempts, avg_execution_time
            FROM quality_correlation
            ORDER BY 
                CASE quality_level
                    WHEN 'LOW' THEN 1
                    WHEN 'MEDIUM' THEN 2
                    WHEN 'HIGH' THEN 3
                    WHEN 'EXCELLENT' THEN 4
                END
        """)
        
        rows = cursor.fetchall()
        
        correlation_data = {}
        for row in rows:
            correlation_data[row[0]] = {
                'total_tasks': row[1],
                'successful_tasks': row[2],
                'success_rate': row[3],
                'avg_attempts': row[4],
                'avg_execution_time': row[5]
            }
        
        return correlation_data
    
    def get_quality_trend(
        self,
        task_type: Optional[str] = None,
        days: int = 30
    ) -> Dict[str, List[float]]:
        """
        Get quality trend over time.
        
        Args:
            task_type: Filter by task type (optional)
            days: Number of days to analyze
            
        Returns:
            Dictionary with dates and corresponding quality scores
        """
        cursor = self.conn.cursor()
        
        start_time = datetime.now() - timedelta(days=days)
        
        query = """
            SELECT DATE(timestamp) as date, 
                   AVG(completeness) as completeness,
                   AVG(relevance) as relevance,
                   AVG(freshness) as freshness,
                   AVG(conciseness) as conciseness,
                   AVG(diversity) as diversity,
                   AVG(overall_quality) as overall_quality
            FROM context_quality
            WHERE timestamp >= ?
        """
        params = [start_time.isoformat()]
        
        if task_type:
            query += " AND task_type = ?"
            params.append(task_type)
        
        query += " GROUP BY DATE(timestamp) ORDER BY date"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        trend_data = {
            'dates': [],
            'completeness': [],
            'relevance': [],
            'freshness': [],
            'conciseness': [],
            'diversity': [],
            'overall_quality': []
        }
        
        for row in rows:
            trend_data['dates'].append(row[0])
            trend_data['completeness'].append(row[1])
            trend_data['relevance'].append(row[2])
            trend_data['freshness'].append(row[3])
            trend_data['conciseness'].append(row[4])
            trend_data['diversity'].append(row[5])
            trend_data['overall_quality'].append(row[6])
        
        return trend_data
    
    def export_quality_data(
        self,
        filepath: str,
        format: str = 'json'
    ):
        """
        Export quality data to file.
        
        Args:
            filepath: Output file path
            format: Export format ('json' or 'csv')
        """
        metrics = self.get_quality_metrics()
        
        if format == 'json':
            data = [m.to_dict() for m in metrics]
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
        elif format == 'csv':
            import csv
            with open(filepath, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=[
                    'task_id', 'task_type', 'timestamp',
                    'completeness', 'relevance', 'freshness', 
                    'conciseness', 'diversity', 'overall_quality',
                    'context_items_count', 'total_tokens', 'unique_sources',
                    'success', 'attempts', 'execution_time_seconds'
                ])
                writer.writeheader()
                for m in metrics:
                    writer.writerow(m.to_dict())
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def clear_old_data(self, days: int = 90):
        """
        Clear old quality data.
        
        Args:
            days: Delete data older than this many days
        """
        cutoff_time = datetime.now() - timedelta(days=days)
        
        cursor = self.conn.cursor()
        cursor.execute("""
            DELETE FROM context_quality
            WHERE timestamp < ?
        """, (cutoff_time.isoformat(),))
        
        deleted = cursor.rowcount
        self.conn.commit()
        
        return deleted