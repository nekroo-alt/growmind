"""
Context Relevance Scorer for L4D V4

Implements relevance scoring for context items to help prioritize
which context information is most relevant to the current task.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from enum import Enum
import hashlib
import json

logger = logging.getLogger(__name__)


class ScoringFactor(Enum):
    """Scoring factors used in relevance calculation."""
    RECENCY = "recency"
    SIMILARITY = "similarity"
    DEPENDENCY = "dependency"
    IMPACT = "impact"


@dataclass
class ScoringWeights:
    """Weights for scoring factors."""
    recency: float = 0.3
    similarity: float = 0.3
    dependency: float = 0.25
    impact: float = 0.15
    
    def validate(self) -> bool:
        """Validate that weights sum to approximately 1.0."""
        total = sum([self.recency, self.similarity, self.dependency, self.impact])
        return abs(total - 1.0) < 0.01


@dataclass
class ContextItem:
    """Represents a context item with metadata."""
    id: str
    content: str
    timestamp: datetime
    item_type: str  # 'action', 'decision', 'error', 'state', etc.
    metadata: Dict = field(default_factory=dict)
    
    # Scoring factors
    recency_score: float = 0.0
    similarity_score: float = 0.0
    dependency_score: float = 0.0
    impact_score: float = 0.0
    total_score: float = 0.0
    
    def compute_hash(self) -> str:
        """Compute hash of content for comparison."""
        return hashlib.md5(self.content.encode()).hexdigest()


@dataclass
class ScoringMetrics:
    """Metrics for tracking scoring accuracy."""
    total_items_scored: int = 0
    average_score: float = 0.0
    score_distribution: Dict[str, int] = field(default_factory=dict)
    scoring_accuracy: float = 0.0  # Based on downstream success
    
    def update(self, score: float):
        """Update metrics with new score."""
        self.total_items_scored += 1
        
        # Update average
        self.average_score = (
            (self.average_score * (self.total_items_scored - 1) + score) 
            / self.total_items_scored
        )
        
        # Update distribution
        if score < 0.2:
            bucket = "very_low"
        elif score < 0.4:
            bucket = "low"
        elif score < 0.6:
            bucket = "medium"
        elif score < 0.8:
            bucket = "high"
        else:
            bucket = "very_high"
        
        self.score_distribution[bucket] = self.score_distribution.get(bucket, 0) + 1


class ContextScorer:
    """
    Context Relevance Scorer
    
    Scores context items by relevance to current task using multiple factors:
    - Recency: More recent = higher score
    - Similarity: Semantic similarity to current task
    - Dependency: Direct/indirect dependencies
    - Impact: High-impact actions = higher score
    """
    
    def __init__(
        self,
        weights: Optional[ScoringWeights] = None,
        learning_rate: float = 0.1
    ):
        """
        Initialize context scorer.
        
        Args:
            weights: Scoring weights (default: balanced)
            learning_rate: Rate at which weights adapt (0.0 to 1.0)
        """
        self.weights = weights or ScoringWeights()
        self.learning_rate = max(0.0, min(1.0, learning_rate))
        self.metrics = ScoringMetrics()
        
        # Learn optimal weights from historical data
        self.historical_weights: List[Tuple[ScoringWeights, float]] = []
        
        logger.info(
            "ContextScorer initialized",
            weights=self.weights,
            learning_rate=self.learning_rate
        )
    
    def score_context_items(
        self,
        items: List[ContextItem],
        current_task: str,
        current_time: Optional[datetime] = None
    ) -> List[ContextItem]:
        """
        Score a list of context items.
        
        Args:
            items: List of context items to score
            current_task: Description of current task
            current_time: Current time for recency scoring
        
        Returns:
            List of items with scores set, sorted by total_score (descending)
        """
        if current_time is None:
            current_time = datetime.now()
        
        for item in items:
            # Calculate individual scores
            item.recency_score = self._score_recency(item, current_time)
            item.similarity_score = self._score_similarity(item, current_task)
            item.dependency_score = self._score_dependency(item, current_task)
            item.impact_score = self._score_impact(item)
            
            # Calculate total score using weights
            item.total_score = (
                self.weights.recency * item.recency_score +
                self.weights.similarity * item.similarity_score +
                self.weights.dependency * item.dependency_score +
                self.weights.impact * item.impact_score
            )
            
            # Update metrics
            self.metrics.update(item.total_score)
        
        # Sort by total score (descending)
        scored_items = sorted(items, key=lambda x: x.total_score, reverse=True)
        
        logger.debug(
            "Scored context items",
            count=len(items),
            avg_score=sum(item.total_score for item in items) / len(items) if items else 0.0
        )
        
        return scored_items
    
    def rank_context_items(
        self,
        items: List[ContextItem],
        current_task: str,
        top_k: Optional[int] = None,
        min_score: float = 0.0
    ) -> List[ContextItem]:
        """
        Rank context items and filter by score.
        
        Args:
            items: List of context items to rank
            current_task: Description of current task
            top_k: Return only top k items (None for all)
            min_score: Minimum score threshold
        
        Returns:
            Ranked and filtered list of context items
        """
        scored_items = self.score_context_items(items, current_task)
        
        # Filter by minimum score
        filtered_items = [item for item in scored_items if item.total_score >= min_score]
        
        # Return top k if specified
        if top_k is not None and top_k > 0:
            filtered_items = filtered_items[:top_k]
        
        logger.debug(
            "Ranked context items",
            total=len(scored_items),
            filtered=len(filtered_items),
            top_k=top_k,
            min_score=min_score
        )
        
        return filtered_items
    
    def prune_context_items(
        self,
        items: List[ContextItem],
        current_task: str,
        keep_percentage: float = 0.7,
        min_score: float = 0.3
    ) -> List[ContextItem]:
        """
        Prune low-relevance context items to reduce noise.
        
        Args:
            items: List of context items to prune
            current_task: Description of current task
            keep_percentage: Percentage of items to keep (0.0 to 1.0)
            min_score: Minimum score threshold
        
        Returns:
            Pruned list of context items
        """
        scored_items = self.score_context_items(items, current_task)
        
        # Keep items above minimum score
        filtered_items = [item for item in scored_items if item.total_score >= min_score]
        
        # Keep top percentage if more items remain
        if keep_percentage < 1.0:
            keep_count = max(1, int(len(filtered_items) * keep_percentage))
            filtered_items = filtered_items[:keep_count]
        
        logger.debug(
            "Pruned context items",
            original=len(items),
            kept=len(filtered_items),
            removed=len(items) - len(filtered_items),
            keep_percentage=keep_percentage
        )
        
        return filtered_items
    
    def _score_recency(
        self,
        item: ContextItem,
        current_time: datetime
    ) -> float:
        """
        Score recency of context item.
        
        More recent items get higher scores. Uses exponential decay.
        
        Args:
            item: Context item to score
            current_time: Current time
        
        Returns:
            Recency score (0.0 to 1.0)
        """
        time_diff = (current_time - item.timestamp).total_seconds()
        
        # Exponential decay: score = e^(-time_diff / half_life)
        # Half-life of 1 hour (3600 seconds)
        half_life = 3600.0
        score = 2.0 ** (-time_diff / half_life)
        
        # Clamp to [0, 1]
        return max(0.0, min(1.0, score))
    
    def _score_similarity(
        self,
        item: ContextItem,
        current_task: str
    ) -> float:
        """
        Score similarity between context item and current task.
        
        Uses simple keyword matching. In production, this would use
        semantic similarity with embeddings or LLM.
        
        Args:
            item: Context item to score
            current_task: Description of current task
        
        Returns:
            Similarity score (0.0 to 1.0)
        """
        # Extract keywords from item and task
        item_keywords = set(self._extract_keywords(item.content))
        task_keywords = set(self._extract_keywords(current_task))
        
        if not task_keywords:
            return 0.5  # Default to medium if no keywords
        
        # Calculate Jaccard similarity
        if not item_keywords and not task_keywords:
            return 0.5
        
        intersection = item_keywords & task_keywords
        union = item_keywords | task_keywords
        
        if not union:
            return 0.0
        
        similarity = len(intersection) / len(union)
        
        # Boost score if item type matches task-relevant types
        if item.item_type in ['action', 'decision', 'error']:
            similarity = min(1.0, similarity * 1.2)
        
        return max(0.0, min(1.0, similarity))
    
    def _score_dependency(
        self,
        item: ContextItem,
        current_task: str
    ) -> float:
        """
        Score dependency relationship between context item and current task.
        
        Higher score if item is directly or indirectly related to task.
        
        Args:
            item: Context item to score
            current_task: Description of current task
        
        Returns:
            Dependency score (0.0 to 1.0)
        """
        # Check metadata for dependency information
        metadata = item.metadata
        
        # Direct dependency
        if 'depends_on' in metadata:
            if current_task in metadata['depends_on']:
                return 1.0
        
        # Reverse dependency
        if 'used_by' in metadata:
            if current_task in metadata['used_by']:
                return 1.0
        
        # Check for shared dependencies
        if 'dependencies' in metadata:
            task_keywords = set(self._extract_keywords(current_task))
            item_deps = set(metadata['dependencies'])
            
            intersection = task_keywords & item_deps
            if intersection:
                # Partial dependency based on overlap
                return min(1.0, len(intersection) / len(item_deps) if item_deps else 0.0)
        
        # Check if item is a high-level component relevant to task
        if item.item_type in ['module', 'class', 'function']:
            # Higher score for structural elements
            return 0.7
        
        return 0.3  # Default to low for no explicit dependency
    
    def _score_impact(self, item: ContextItem) -> float:
        """
        Score impact of context item.
        
        High-impact items (errors, critical decisions) get higher scores.
        
        Args:
            item: Context item to score
        
        Returns:
            Impact score (0.0 to 1.0)
        """
        # Check item type
        impact_by_type = {
            'error': 1.0,           # Highest impact
            'critical': 1.0,
            'decision': 0.9,
            'action': 0.7,
            'test': 0.6,
            'state': 0.4,
            'info': 0.3,
            'debug': 0.2,
        }
        
        base_score = impact_by_type.get(item.item_type, 0.5)
        
        # Boost if metadata indicates high impact
        if item.metadata.get('severity') == 'critical':
            base_score = 1.0
        elif item.metadata.get('severity') == 'high':
            base_score = max(base_score, 0.8)
        
        # Boost if item has many downstream dependencies
        if item.metadata.get('downstream_count', 0) > 5:
            base_score = min(1.0, base_score * 1.2)
        
        return base_score
    
    def _extract_keywords(self, text: str) -> List[str]:
        """
        Extract keywords from text for similarity scoring.
        
        Simple implementation - removes common words and returns remaining words.
        In production, this would use NLP techniques.
        
        Args:
            text: Text to extract keywords from
        
        Returns:
            List of keywords
        """
        # Common words to filter out
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at',
            'to', 'for', 'of', 'with', 'by', 'from', 'is', 'are', 'was',
            'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do',
            'does', 'did', 'will', 'would', 'could', 'should', 'may',
            'might', 'must', 'shall', 'can', 'need', 'this', 'that',
            'these', 'those', 'it', 'its', 'as', 'if', 'then', 'else'
        }
        
        # Split on non-alphanumeric characters and lowercase
        words = text.lower().split()
        keywords = [
            word.strip('.,!?;:"\'()[]{}')
            for word in words
            if len(word) > 2 and word not in stop_words
        ]
        
        return keywords
    
    def update_weights(self, new_weights: ScoringWeights):
        """
        Update scoring weights.
        
        Args:
            new_weights: New weights to use
        """
        if not new_weights.validate():
            raise ValueError("Weights must sum to approximately 1.0")
        
        # Store historical weights
        self.historical_weights.append((self.weights, self.metrics.scoring_accuracy))
        
        # Update weights
        self.weights = new_weights
        
        logger.info(
            "Updated scoring weights",
            new_weights=new_weights
        )
    
    def learn_weights(self, success_rate: float):
        """
        Learn optimal weights from success rate.
        
        Adjusts weights based on downstream success to improve scoring accuracy.
        
        Args:
            success_rate: Downstream success rate (0.0 to 1.0)
        """
        # Update metrics
        self.metrics.scoring_accuracy = success_rate
        
        # Simple learning: if success rate is low, try to adjust weights
        # In production, this would use more sophisticated ML
        if success_rate < 0.7 and len(self.historical_weights) > 0:
            # Find historically best weights
            best_weights, _ = max(
                self.historical_weights,
                key=lambda x: x[1]
            )
            
            # Gradually move toward best weights
            self.weights = ScoringWeights(
                recency=self._interpolate_weight(
                    self.weights.recency,
                    best_weights.recency,
                    self.learning_rate
                ),
                similarity=self._interpolate_weight(
                    self.weights.similarity,
                    best_weights.similarity,
                    self.learning_rate
                ),
                dependency=self._interpolate_weight(
                    self.weights.dependency,
                    best_weights.dependency,
                    self.learning_rate
                ),
                impact=self._interpolate_weight(
                    self.weights.impact,
                    best_weights.impact,
                    self.learning_rate
                )
            )
            
            logger.info(
                "Learned new weights from success rate",
                success_rate=success_rate,
                new_weights=self.weights
            )
    
    def _interpolate_weight(
        self,
        current: float,
        target: float,
        learning_rate: float
    ) -> float:
        """
        Interpolate between current and target weight.
        
        Args:
            current: Current weight value
            target: Target weight value
            learning_rate: Learning rate (0.0 to 1.0)
        
        Returns:
            Interpolated weight value
        """
        return current + learning_rate * (target - current)
    
    def get_metrics(self) -> ScoringMetrics:
        """
        Get current scoring metrics.
        
        Returns:
            Scoring metrics
        """
        return self.metrics
    
    def reset_metrics(self):
        """Reset scoring metrics."""
        self.metrics = ScoringMetrics()
        logger.info("Reset scoring metrics")
    
    def export_state(self) -> Dict:
        """
        Export scorer state for persistence.
        
        Returns:
            Dictionary containing scorer state
        """
        return {
            'weights': {
                'recency': self.weights.recency,
                'similarity': self.weights.similarity,
                'dependency': self.weights.dependency,
                'impact': self.weights.impact
            },
            'learning_rate': self.learning_rate,
            'metrics': {
                'total_items_scored': self.metrics.total_items_scored,
                'average_score': self.metrics.average_score,
                'score_distribution': self.metrics.score_distribution,
                'scoring_accuracy': self.metrics.scoring_accuracy
            },
            'historical_weights': [
                {
                    'weights': {
                        'recency': w.recency,
                        'similarity': w.similarity,
                        'dependency': w.dependency,
                        'impact': w.impact
                    },
                    'accuracy': acc
                }
                for w, acc in self.historical_weights[-10:]  # Keep last 10
            ]
        }
    
    def import_state(self, state: Dict):
        """
        Import scorer state from persistence.
        
        Args:
            state: Dictionary containing scorer state
        """
        self.weights = ScoringWeights(
            recency=state['weights']['recency'],
            similarity=state['weights']['similarity'],
            dependency=state['weights']['dependency'],
            impact=state['weights']['impact']
        )
        
        self.learning_rate = state.get('learning_rate', 0.1)
        
        self.metrics = ScoringMetrics(
            total_items_scored=state['metrics']['total_items_scored'],
            average_score=state['metrics']['average_score'],
            score_distribution=state['metrics'].get('score_distribution', {}),
            scoring_accuracy=state['metrics'].get('scoring_accuracy', 0.0)
        )
        
        self.historical_weights = [
            (
                ScoringWeights(
                    recency=hw['weights']['recency'],
                    similarity=hw['weights']['similarity'],
                    dependency=hw['weights']['dependency'],
                    impact=hw['weights']['impact']
                ),
                hw['accuracy']
            )
            for hw in state.get('historical_weights', [])
        ]
        
        logger.info(
            "Imported scorer state",
            weights=self.weights,
            learning_rate=self.learning_rate,
            total_items_scored=self.metrics.total_items_scored
        )