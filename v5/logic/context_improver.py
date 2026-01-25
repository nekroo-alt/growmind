"""
Context Improver - V5 Quality Enhancement

This module implements automated context improvement based on quality metrics.
It identifies low-quality contexts, suggests improvements, applies high-confidence
improvements automatically, and tracks effectiveness for learning.

Key Features:
- Automatic identification of low-quality contexts
- Context improvement suggestion generation
- Automated improvement application (with confidence threshold)
- Improvement effectiveness tracking
- Learning from successful improvements
"""

import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

from logic.context_quality_tracker import (
    ContextQualityTracker,
    ContextQualityMetrics,
    QualityMetric,
    QualityThreshold
)
from logic.context_scorer import ContextItem, RelevanceCategory
from logic.context_compressor import ContextCompressor, CompressionLevel


class ImprovementType(Enum):
    """Types of context improvements"""
    ADD_MISSING_DEPENDENCIES = "add_missing_dependencies"
    REPLACE_LOW_RELEVANCE = "replace_low_relevance"
    UPDATE_STALE_CONTEXT = "update_stale_context"
    COMPRESS_VERBOSE_CONTEXT = "compress_verbose_context"
    ADD_DIVERSE_SOURCES = "add_diverse_sources"
    INCREASE_CONTEXT_DEPTH = "increase_context_depth"
    REBALANCE_WEIGHTS = "rebalance_weights"
    REFRESH_CACHE = "refresh_cache"


@dataclass
class ImprovementSuggestion:
    """A single improvement suggestion"""
    suggestion_id: str
    improvement_type: ImprovementType
    metric: QualityMetric
    current_value: float
    target_value: float
    confidence: float  # 0.0 - 1.0
    description: str
    implementation_details: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class ImprovementPlan:
    """A complete improvement plan for a task"""
    task_id: str
    task_type: str
    timestamp: datetime
    current_quality: float
    target_quality: float
    suggestions: List[ImprovementSuggestion]
    expected_improvement: float  # Expected quality increase
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = asdict(self)
        result['timestamp'] = self.timestamp.isoformat()
        result['suggestions'] = [s.to_dict() for s in self.suggestions]
        return result


@dataclass
class ImprovementResult:
    """Result of applying improvements"""
    task_id: str
    timestamp: datetime
    applied_improvements: List[str]  # List of suggestion IDs
    skipped_improvements: List[str]  # List of suggestion IDs
    quality_before: float
    quality_after: float
    quality_improvement: float
    success: bool
    execution_time_seconds: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = asdict(self)
        # Convert datetime to ISO format string for JSON serialization
        result['timestamp'] = self.timestamp.isoformat()
        return result


class ContextImprover:
    """
    Context Improver
    
    Automatically identifies and applies context improvements based on quality metrics.
    Tracks effectiveness and learns optimal improvement strategies.
    """
    
    def __init__(
        self,
        db_path: str = "context_improvements.db",
        quality_tracker_db: str = "context_quality.db"
    ):
        """
        Initialize context improver.
        
        Args:
            db_path: Path to improvement tracking database
            quality_tracker_db: Path to quality tracker database
        """
        self.db_path = db_path
        self.conn = None
        
        # Initialize quality tracker for metrics access
        self.quality_tracker = ContextQualityTracker(quality_tracker_db)
        self.quality_tracker.connect()
        
        # Initialize context compressor for compression improvements
        self.compressor = ContextCompressor()
        
        # Configuration
        self.threshold = QualityThreshold()
        self.auto_apply_threshold = 0.8  # Auto-apply improvements with confidence >= 0.8
        
        # Learning: Track improvement effectiveness
        self.improvement_effectiveness: Dict[str, Dict[str, float]] = {}
    
    def connect(self):
        """Connect to database"""
        self.conn = sqlite3.connect(self.db_path)
        self._create_tables()
    
    def close(self):
        """Close database connections"""
        if self.conn:
            self.conn.close()
            self.conn = None
        
        self.quality_tracker.close()
    
    def _create_tables(self):
        """Create database tables"""
        cursor = self.conn.cursor()
        
        # Improvement suggestions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS improvement_suggestions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                task_type TEXT NOT NULL,
                suggestion_id TEXT NOT NULL UNIQUE,
                improvement_type TEXT NOT NULL,
                metric TEXT NOT NULL,
                current_value REAL NOT NULL,
                target_value REAL NOT NULL,
                confidence REAL NOT NULL,
                description TEXT NOT NULL,
                implementation_details TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                applied INTEGER DEFAULT 0
            )
        """)
        
        # Improvement results table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS improvement_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                timestamp DATETIME NOT NULL,
                applied_improvements TEXT NOT NULL,
                skipped_improvements TEXT NOT NULL,
                quality_before REAL NOT NULL,
                quality_after REAL NOT NULL,
                quality_improvement REAL NOT NULL,
                success INTEGER NOT NULL,
                execution_time_seconds REAL NOT NULL
            )
        """)
        
        # Improvement effectiveness tracking table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS improvement_effectiveness (
                improvement_type TEXT PRIMARY KEY,
                total_applications INTEGER DEFAULT 0,
                successful_applications INTEGER DEFAULT 0,
                avg_quality_improvement REAL DEFAULT 0.0,
                avg_confidence REAL DEFAULT 0.0,
                success_rate REAL DEFAULT 0.0,
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_suggestions_task 
            ON improvement_suggestions(task_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_suggestions_type 
            ON improvement_suggestions(improvement_type)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_suggestions_confidence 
            ON improvement_suggestions(confidence)
        """)
        
        self.conn.commit()
    
    def identify_improvements(
        self,
        task_id: str,
        task_type: str,
        quality_metrics: ContextQualityMetrics
    ) -> List[ImprovementSuggestion]:
        """
        Identify improvements needed based on quality metrics.
        
        Analyzes quality metrics and generates improvement suggestions
        for metrics that fall below thresholds.
        
        Args:
            task_id: Unique task identifier
            task_type: Type of task
            quality_metrics: Current quality metrics
            
        Returns:
            List of ImprovementSuggestion objects
        """
        suggestions = []
        
        # Check completeness
        if quality_metrics.completeness < self.threshold.medium_threshold:
            suggestion = self._suggest_completeness_improvement(
                task_id, quality_metrics
            )
            if suggestion:
                suggestions.append(suggestion)
        
        # Check relevance
        if quality_metrics.relevance < self.threshold.medium_threshold:
            suggestion = self._suggest_relevance_improvement(
                task_id, quality_metrics
            )
            if suggestion:
                suggestions.append(suggestion)
        
        # Check freshness
        if quality_metrics.freshness < self.threshold.medium_threshold:
            suggestion = self._suggest_freshness_improvement(
                task_id, quality_metrics
            )
            if suggestion:
                suggestions.append(suggestion)
        
        # Check conciseness
        if quality_metrics.conciseness < self.threshold.medium_threshold:
            suggestion = self._suggest_conciseness_improvement(
                task_id, quality_metrics
            )
            if suggestion:
                suggestions.append(suggestion)
        
        # Check diversity
        if quality_metrics.diversity < self.threshold.medium_threshold:
            suggestion = self._suggest_diversity_improvement(
                task_id, quality_metrics
            )
            if suggestion:
                suggestions.append(suggestion)
        
        return suggestions
    
    def _suggest_completeness_improvement(
        self,
        task_id: str,
        quality_metrics: ContextQualityMetrics
    ) -> Optional[ImprovementSuggestion]:
        """
        Suggest improvement for low completeness.
        
        Suggests adding missing dependencies and increasing context depth.
        """
        # Calculate expected improvement
        current_value = quality_metrics.completeness
        target_value = self.threshold.high_threshold
        
        # Confidence based on how far from threshold and historical effectiveness
        gap = target_value - current_value
        base_confidence = min(gap / 0.3, 1.0)  # Larger gap = higher confidence
        
        # Adjust by historical effectiveness
        effectiveness = self._get_improvement_effectiveness(
            ImprovementType.ADD_MISSING_DEPENDENCIES.value
        )
        adjusted_confidence = base_confidence * effectiveness.get('success_rate', 0.8)
        
        return ImprovementSuggestion(
            suggestion_id=f"{task_id}_completeness_{datetime.now().timestamp()}",
            improvement_type=ImprovementType.ADD_MISSING_DEPENDENCIES,
            metric=QualityMetric.COMPLETENESS,
            current_value=current_value,
            target_value=target_value,
            confidence=min(adjusted_confidence, 1.0),
            description=(
                f"Low completeness ({current_value:.2f}): Add missing dependencies "
                f"and increase context depth. Current context is missing "
                f"{(1.0 - current_value):.1%} of required items."
            ),
            implementation_details={
                'action': 'expand_context',
                'strategy': 'add_transitive_dependencies',
                'max_depth': 3,
                'include_tests': True,
                'include_docs': True
            }
        )
    
    def _suggest_relevance_improvement(
        self,
        task_id: str,
        quality_metrics: ContextQualityMetrics
    ) -> Optional[ImprovementSuggestion]:
        """
        Suggest improvement for low relevance.
        
        Suggests replacing low-relevance items with high-relevance ones.
        """
        current_value = quality_metrics.relevance
        target_value = self.threshold.high_threshold
        
        gap = target_value - current_value
        base_confidence = min(gap / 0.3, 1.0)
        
        effectiveness = self._get_improvement_effectiveness(
            ImprovementType.REPLACE_LOW_RELEVANCE.value
        )
        adjusted_confidence = base_confidence * effectiveness.get('success_rate', 0.75)
        
        return ImprovementSuggestion(
            suggestion_id=f"{task_id}_relevance_{datetime.now().timestamp()}",
            improvement_type=ImprovementType.REPLACE_LOW_RELEVANCE,
            metric=QualityMetric.RELEVANCE,
            current_value=current_value,
            target_value=target_value,
            confidence=min(adjusted_confidence, 1.0),
            description=(
                f"Low relevance ({current_value:.2f}): Replace low-relevance "
                f"context items with high-relevance alternatives. "
                f"Focus on task-specific context."
            ),
            implementation_details={
                'action': 'filter_and_replace',
                'relevance_threshold': 0.7,
                'replace_low_items': True,
                'use_task_impact_analysis': True
            }
        )
    
    def _suggest_freshness_improvement(
        self,
        task_id: str,
        quality_metrics: ContextQualityMetrics
    ) -> Optional[ImprovementSuggestion]:
        """
        Suggest improvement for low freshness.
        
        Suggests updating stale context items and refreshing cache.
        """
        current_value = quality_metrics.freshness
        target_value = self.threshold.high_threshold
        
        gap = target_value - current_value
        base_confidence = min(gap / 0.3, 1.0)
        
        effectiveness = self._get_improvement_effectiveness(
            ImprovementType.UPDATE_STALE_CONTEXT.value
        )
        adjusted_confidence = base_confidence * effectiveness.get('success_rate', 0.9)
        
        return ImprovementSuggestion(
            suggestion_id=f"{task_id}_freshness_{datetime.now().timestamp()}",
            improvement_type=ImprovementType.UPDATE_STALE_CONTEXT,
            metric=QualityMetric.FRESHNESS,
            current_value=current_value,
            target_value=target_value,
            confidence=min(adjusted_confidence, 1.0),
            description=(
                f"Low freshness ({current_value:.2f}): Update stale context "
                f"items and refresh cache. Some context is older than 30 days."
            ),
            implementation_details={
                'action': 'refresh_context',
                'max_age_days': 30,
                'invalidate_cache': True,
                'reload_from_source': True
            }
        )
    
    def _suggest_conciseness_improvement(
        self,
        task_id: str,
        quality_metrics: ContextQualityMetrics
    ) -> Optional[ImprovementSuggestion]:
        """
        Suggest improvement for low conciseness.
        
        Suggests compressing verbose contexts.
        """
        current_value = quality_metrics.conciseness
        target_value = self.threshold.high_threshold
        
        gap = target_value - current_value
        base_confidence = min(gap / 0.3, 1.0)
        
        effectiveness = self._get_improvement_effectiveness(
            ImprovementType.COMPRESS_VERBOSE_CONTEXT.value
        )
        adjusted_confidence = base_confidence * effectiveness.get('success_rate', 0.85)
        
        # Determine appropriate compression level based on gap
        if gap > 0.3:
            compression_level = CompressionLevel.LEVEL_3
        elif gap > 0.2:
            compression_level = CompressionLevel.LEVEL_2
        else:
            compression_level = CompressionLevel.LEVEL_1
        
        return ImprovementSuggestion(
            suggestion_id=f"{task_id}_conciseness_{datetime.now().timestamp()}",
            improvement_type=ImprovementType.COMPRESS_VERBOSE_CONTEXT,
            metric=QualityMetric.CONCISENESS,
            current_value=current_value,
            target_value=target_value,
            confidence=min(adjusted_confidence, 1.0),
            description=(
                f"Low conciseness ({current_value:.2f}): Compress verbose "
                f"context to remove unnecessary details. Expected 40-50% reduction."
            ),
            implementation_details={
                'action': 'compress_context',
                'compression_level': compression_level.value,
                'preserve_signatures': True,
                'preserve_imports': True,
                'preserve_critical_logic': True
            }
        )
    
    def _suggest_diversity_improvement(
        self,
        task_id: str,
        quality_metrics: ContextQualityMetrics
    ) -> Optional[ImprovementSuggestion]:
        """
        Suggest improvement for low diversity.
        
        Suggests adding diverse sources (docs, tests, config).
        """
        current_value = quality_metrics.diversity
        target_value = self.threshold.high_threshold
        
        gap = target_value - current_value
        base_confidence = min(gap / 0.3, 1.0)
        
        effectiveness = self._get_improvement_effectiveness(
            ImprovementType.ADD_DIVERSE_SOURCES.value
        )
        adjusted_confidence = base_confidence * effectiveness.get('success_rate', 0.8)
        
        return ImprovementSuggestion(
            suggestion_id=f"{task_id}_diversity_{datetime.now().timestamp()}",
            improvement_type=ImprovementType.ADD_DIVERSE_SOURCES,
            metric=QualityMetric.DIVERSITY,
            current_value=current_value,
            target_value=target_value,
            confidence=min(adjusted_confidence, 1.0),
            description=(
                f"Low diversity ({current_value:.2f}): Add context from "
                f"diverse sources including documentation, tests, and config files."
            ),
            implementation_details={
                'action': 'add_sources',
                'include_docs': True,
                'include_tests': True,
                'include_config': True,
                'source_types': ['.md', '.txt', '.json', '.yaml', '.toml']
            }
        )
    
    def generate_improvement_plan(
        self,
        task_id: str,
        task_type: str,
        quality_metrics: ContextQualityMetrics
    ) -> ImprovementPlan:
        """
        Generate a complete improvement plan for a task.
        
        Identifies all improvements needed and calculates expected improvement.
        
        Args:
            task_id: Unique task identifier
            task_type: Type of task
            quality_metrics: Current quality metrics
            
        Returns:
            ImprovementPlan with all suggestions
        """
        # Identify improvements
        suggestions = self.identify_improvements(
            task_id, task_type, quality_metrics
        )
        
        # Calculate expected improvement
        current_quality = quality_metrics.overall_quality
        expected_improvement = 0.0
        
        for suggestion in suggestions:
            # Expected improvement based on gap and confidence
            gap = suggestion.target_value - suggestion.current_value
            expected_improvement += gap * suggestion.confidence * 0.2  # Weight by metric
        
        target_quality = min(current_quality + expected_improvement, 1.0)
        
        return ImprovementPlan(
            task_id=task_id,
            task_type=task_type,
            timestamp=datetime.now(),
            current_quality=current_quality,
            target_quality=target_quality,
            suggestions=suggestions,
            expected_improvement=expected_improvement
        )
    
    def apply_improvements(
        self,
        improvement_plan: ImprovementPlan,
        context_items: List[Dict[str, Any]],
        auto_apply: bool = True
    ) -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        Apply improvements to context items.
        
        Args:
            improvement_plan: Improvement plan to apply
            context_items: Current context items
            auto_apply: If True, auto-apply high-confidence improvements
            
        Returns:
            Tuple of (updated_context_items, applied_suggestion_ids)
        """
        updated_items = context_items.copy()
        applied_suggestions = []
        
        for suggestion in improvement_plan.suggestions:
            # Check if auto-apply or manual approval
            should_apply = auto_apply and suggestion.confidence >= self.auto_apply_threshold
            
            if should_apply:
                # Apply the improvement
                updated_items = self._apply_suggestion(
                    suggestion, updated_items
                )
                applied_suggestions.append(suggestion.suggestion_id)
        
        return updated_items, applied_suggestions
    
    def _apply_suggestion(
        self,
        suggestion: ImprovementSuggestion,
        context_items: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Apply a single improvement suggestion.
        
        Args:
            suggestion: Improvement suggestion to apply
            context_items: Current context items
            
        Returns:
            Updated context items
        """
        action = suggestion.implementation_details.get('action')
        
        if action == 'expand_context':
            # Add transitive dependencies
            # In a full implementation, this would call ContextEngine
            # For now, we just mark items for expansion
            for item in context_items:
                if item.get('relevance_score', 0) < 0.5:
                    item['needs_expansion'] = True
        
        elif action == 'filter_and_replace':
            # Replace low-relevance items
            relevance_threshold = suggestion.implementation_details.get(
                'relevance_threshold', 0.7
            )
            context_items = [
                item for item in context_items
                if item.get('relevance_score', 0) >= relevance_threshold
                or item.get('preserve', False)
            ]
        
        elif action == 'refresh_context':
            # Mark items for refresh
            max_age_days = suggestion.implementation_details.get('max_age_days', 30)
            for item in context_items:
                item['needs_refresh'] = True
        
        elif action == 'compress_context':
            # Compress verbose context
            compression_level = suggestion.implementation_details.get(
                'compression_level', 1
            )
            for item in context_items:
                content = item.get('content', '')
                if len(content) > 1000:  # Only compress large items
                    compressed = self._compress_content(
                        content, compression_level
                    )
                    item['content'] = compressed
                    item['compressed'] = True
        
        elif action == 'add_sources':
            # In a full implementation, this would add new sources
            # For now, we just mark that additional sources are needed
            pass
        
        return context_items
    
    def _compress_content(
        self,
        content: str,
        compression_level: int
    ) -> str:
        """
        Compress content based on level.
        
        Args:
            content: Content to compress
            compression_level: Compression level (1-3)
            
        Returns:
            Compressed content
        """
        if compression_level == 1:
            # Level 1: Remove comments and excessive whitespace
            lines = []
            for line in content.split('\n'):
                stripped = line.strip()
                if stripped and not stripped.startswith('#'):
                    lines.append(stripped)
            return '\n'.join(lines)
        
        elif compression_level == 2:
            # Level 2: Keep only signatures and docstrings
            lines = []
            in_docstring = False
            docstring_delimiter = None
            
            for line in content.split('\n'):
                stripped = line.strip()
                
                # Handle docstring delimiters
                if '"""' in stripped or "'''" in stripped:
                    if in_docstring:
                        # Closing docstring
                        lines.append(stripped)
                        in_docstring = False
                        docstring_delimiter = None
                    else:
                        # Opening docstring - check which delimiter
                        if '"""' in stripped:
                            docstring_delimiter = '"""'
                        else:
                            docstring_delimiter = "'''"
                        lines.append(stripped)
                        in_docstring = True
                    continue
                
                if in_docstring:
                    lines.append(stripped)
                    continue
                    
                # Outside docstring - keep signatures and imports
                if any(kw in stripped for kw in ['def ', 'class ', 'import ', 'from ']):
                    lines.append(stripped)
            
            return '\n'.join(lines)
        
        else:  # Level 3: Maximum compression
            # Level 3: Only signatures
            lines = []
            for line in content.split('\n'):
                stripped = line.strip()
                if any(kw in stripped for kw in ['def ', 'class ', 'import ', 'from ']):
                    lines.append(stripped)
                elif stripped.endswith(':'):
                    lines.append(stripped)
            return '\n'.join(lines)
    
    def track_improvement_effectiveness(
        self,
        task_id: str,
        applied_suggestions: List[str],
        quality_before: float,
        quality_after: float,
        success: bool,
        execution_time_seconds: float
    ) -> ImprovementResult:
        """
        Track effectiveness of applied improvements.
        
        Records the results of applied improvements and updates
        effectiveness tracking for learning.
        
        Args:
            task_id: Unique task identifier
            applied_suggestions: List of applied suggestion IDs
            quality_before: Quality score before improvements
            quality_after: Quality score after improvements
            success: Whether task succeeded after improvements
            execution_time_seconds: Time to apply improvements
            
        Returns:
            ImprovementResult object
        """
        # Calculate quality improvement
        quality_improvement = quality_after - quality_before
        
        # Get suggestion types from IDs
        suggestion_types = []
        for suggestion_id in applied_suggestions:
            suggestion_types.append(
                suggestion_id.split('_')[1]  # Extract type from ID
            )
        
        # Create result
        result = ImprovementResult(
            task_id=task_id,
            timestamp=datetime.now(),
            applied_improvements=applied_suggestions,
            skipped_improvements=[],
            quality_before=quality_before,
            quality_after=quality_after,
            quality_improvement=quality_improvement,
            success=success,
            execution_time_seconds=execution_time_seconds
        )
        
        # Save to database
        self._save_improvement_result(result)
        
        # Update effectiveness tracking
        for suggestion_type in suggestion_types:
            self._update_effectiveness(
                suggestion_type,
                quality_improvement,
                success
            )
        
        return result
    
    def _save_improvement_result(self, result: ImprovementResult):
        """Save improvement result to database"""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            INSERT INTO improvement_results (
                task_id, timestamp, applied_improvements, skipped_improvements,
                quality_before, quality_after, quality_improvement,
                success, execution_time_seconds
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            result.task_id,
            result.timestamp.isoformat(),
            json.dumps(result.applied_improvements),
            json.dumps(result.skipped_improvements),
            result.quality_before,
            result.quality_after,
            result.quality_improvement,
            1 if result.success else 0,
            result.execution_time_seconds
        ))
        
        self.conn.commit()
    
    def _update_effectiveness(
        self,
        improvement_type: str,
        quality_improvement: float,
        success: bool
    ):
        """Update effectiveness tracking for an improvement type"""
        cursor = self.conn.cursor()
        
        # Get current effectiveness
        cursor.execute("""
            SELECT total_applications, successful_applications,
                   avg_quality_improvement, avg_confidence
            FROM improvement_effectiveness
            WHERE improvement_type = ?
        """, (improvement_type,))
        
        row = cursor.fetchone()
        
        if row:
            # Update existing
            total, successful, avg_improvement, avg_conf = row
            
            new_total = total + 1
            new_successful = successful + (1 if success else 0)
            new_avg_improvement = (
                (avg_improvement * total + quality_improvement) / new_total
            )
            
            cursor.execute("""
                UPDATE improvement_effectiveness
                SET total_applications = ?,
                    successful_applications = ?,
                    avg_quality_improvement = ?,
                    success_rate = ?,
                    last_updated = ?
                WHERE improvement_type = ?
            """, (
                new_total,
                new_successful,
                new_avg_improvement,
                new_successful / new_total,
                datetime.now().isoformat(),
                improvement_type
            ))
        else:
            # Insert new
            cursor.execute("""
                INSERT INTO improvement_effectiveness
                (improvement_type, total_applications, successful_applications,
                 avg_quality_improvement, success_rate, avg_confidence)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                improvement_type,
                1,
                1 if success else 0,
                quality_improvement,
                1.0 if success else 0.0,
                0.8
            ))
        
        self.conn.commit()
    
    def _get_improvement_effectiveness(
        self,
        improvement_type: str
    ) -> Dict[str, float]:
        """
        Get effectiveness data for an improvement type.
        
        Args:
            improvement_type: Type of improvement
            
        Returns:
            Dictionary with effectiveness metrics
        """
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT total_applications, successful_applications,
                   avg_quality_improvement, success_rate
            FROM improvement_effectiveness
            WHERE improvement_type = ?
        """, (improvement_type,))
        
        row = cursor.fetchone()
        
        if row:
            return {
                'total_applications': row[0],
                'successful_applications': row[1],
                'avg_quality_improvement': row[2],
                'success_rate': row[3]
            }
        else:
            # Default effectiveness for new improvement types
            return {
                'total_applications': 0,
                'successful_applications': 0,
                'avg_quality_improvement': 0.1,
                'success_rate': 0.8
            }
    
    def get_improvement_history(
        self,
        task_id: Optional[str] = None,
        limit: int = 100
    ) -> List[ImprovementResult]:
        """
        Get improvement history.
        
        Args:
            task_id: Filter by task ID (optional)
            limit: Maximum number of results to return (None for no limit)
            
        Returns:
            List of ImprovementResult objects
        """
        cursor = self.conn.cursor()
        
        if task_id:
            if limit is not None:
                cursor.execute("""
                    SELECT * FROM improvement_results
                    WHERE task_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (task_id, limit))
            else:
                cursor.execute("""
                    SELECT * FROM improvement_results
                    WHERE task_id = ?
                    ORDER BY timestamp DESC
                """, (task_id,))
        else:
            if limit is not None:
                cursor.execute("""
                    SELECT * FROM improvement_results
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (limit,))
            else:
                cursor.execute("""
                    SELECT * FROM improvement_results
                    ORDER BY timestamp DESC
                """)
        
        rows = cursor.fetchall()
        
        results = []
        for row in rows:
            results.append(ImprovementResult(
                task_id=row[1],
                timestamp=datetime.fromisoformat(row[2]),
                applied_improvements=json.loads(row[3]),
                skipped_improvements=json.loads(row[4]),
                quality_before=row[5],
                quality_after=row[6],
                quality_improvement=row[7],
                success=bool(row[8]),
                execution_time_seconds=row[9]
            ))
        
        return results
    
    def get_effectiveness_summary(self) -> Dict[str, Dict[str, float]]:
        """
        Get effectiveness summary for all improvement types.
        
        Returns:
            Dictionary mapping improvement types to effectiveness data
        """
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT improvement_type, total_applications, successful_applications,
                   avg_quality_improvement, success_rate
            FROM improvement_effectiveness
            ORDER BY success_rate DESC
        """)
        
        rows = cursor.fetchall()
        
        summary = {}
        for row in rows:
            summary[row[0]] = {
                'total_applications': row[1],
                'successful_applications': row[2],
                'avg_quality_improvement': row[3],
                'success_rate': row[4]
            }
        
        return summary
    
    def export_improvement_data(self, filepath: str, format: str = 'json'):
        """
        Export improvement data to file.
        
        Args:
            filepath: Output file path
            format: Export format ('json' or 'csv')
        """
        results = self.get_improvement_history(limit=None)
        
        if format == 'json':
            data = [r.to_dict() for r in results]
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
        elif format == 'csv':
            import csv
            with open(filepath, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=[
                    'task_id', 'timestamp', 'applied_improvements',
                    'skipped_improvements', 'quality_before',
                    'quality_after', 'quality_improvement',
                    'success', 'execution_time_seconds'
                ])
                writer.writeheader()
                for r in results:
                    result_dict = r.to_dict()
                    result_dict['applied_improvements'] = json.dumps(
                        result_dict['applied_improvements']
                    )
                    result_dict['skipped_improvements'] = json.dumps(
                        result_dict['skipped_improvements']
                    )
                    writer.writerow(result_dict)
        else:
            raise ValueError(f"Unsupported format: {format}")