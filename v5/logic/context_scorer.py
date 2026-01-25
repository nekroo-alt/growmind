"""
Context Relevance Scorer for L4D V4/V5

Implements relevance scoring for context items to help prioritize
which context information is most relevant to the current task.

V5 Enhancement: Added token-aware filtering, LLM feedback mechanism,
and relevance accuracy tracking for improved context quality.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Set
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


class RelevanceCategory(Enum):
    """Relevance categories for filtering."""
    HIGH = "high"           # score > 0.7, always include
    MEDIUM = "medium"       # 0.3 < score <= 0.7, include if space
    LOW = "low"             # score <= 0.3, exclude


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
    
    # V5: Additional metadata for filtering
    token_estimate: int = 0  # Estimated token count for this item
    was_needed: bool = False  # Was this item actually needed during execution?
    feedback_score: float = 0.5  # Feedback score from LLM (0.0 to 1.0)
    
    def compute_hash(self) -> str:
        """Compute hash of content for comparison."""
        return hashlib.md5(self.content.encode()).hexdigest()
    
    def get_relevance_category(self) -> RelevanceCategory:
        """
        Get relevance category based on total score.
        
        Returns:
            Relevance category (HIGH, MEDIUM, LOW)
        """
        if self.total_score > 0.7:
            return RelevanceCategory.HIGH
        elif self.total_score > 0.3:
            return RelevanceCategory.MEDIUM
        else:
            return RelevanceCategory.LOW


@dataclass
class ScoringMetrics:
    """Metrics for tracking scoring accuracy."""
    total_items_scored: int = 0
    average_score: float = 0.0
    score_distribution: Dict[str, int] = field(default_factory=dict)
    scoring_accuracy: float = 0.0  # Based on downstream success
    
    # V5: Relevance accuracy tracking
    relevance_accuracy: float = 0.0  # How often high-relevance items were actually needed
    false_positive_rate: float = 0.0  # Items included but not needed
    false_negative_rate: float = 0.0  # Items excluded but actually needed
    
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
    
    def update_relevance_accuracy(
        self,
        included_items: Set[str],
        needed_items: Set[str]
    ):
        """
        Update relevance accuracy metrics.
        
        Args:
            included_items: IDs of items that were included in context
            needed_items: IDs of items that were actually needed during execution
        """
        if not included_items:
            return
        
        # True positives: items included and needed
        true_positives = len(included_items & needed_items)
        
        # False positives: items included but not needed
        false_positives = len(included_items - needed_items)
        
        # False negatives: items needed but not included
        false_negatives = len(needed_items - included_items)
        
        # True negatives: items excluded and not needed (can't calculate without all items)
        
        # Calculate precision and recall
        precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0.0
        recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0.0
        
        # F1 score as accuracy metric
        if precision + recall > 0:
            self.relevance_accuracy = 2 * (precision * recall) / (precision + recall)
        else:
            self.relevance_accuracy = 0.0
        
        # Update error rates
        self.false_positive_rate = false_positives / len(included_items) if included_items else 0.0
        self.false_negative_rate = false_negatives / (len(included_items) + false_negatives) if (len(included_items) + false_negatives) > 0 else 0.0
        
        logger.debug(
            "Updated relevance accuracy",
            f1_score=self.relevance_accuracy,
            precision=precision,
            recall=recall,
            false_positive_rate=self.false_positive_rate,
            false_negative_rate=self.false_negative_rate
        )


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
    
    def filter_by_relevance(
        self,
        items: List[ContextItem],
        current_task: str,
        token_budget: Optional[int] = None,
        high_threshold: float = 0.7,
        low_threshold: float = 0.3
    ) -> Tuple[List[ContextItem], Dict[str, int]]:
        """
        Filter context items by relevance with V5 strategy:
        - Always include: score > high_threshold (> 0.7)
        - Include if space: low_threshold < score <= high_threshold (0.3-0.7)
        - Exclude: score <= low_threshold (<= 0.3)
        
        Args:
            items: List of context items to filter
            current_task: Description of current task
            token_budget: Maximum tokens to include (None for unlimited)
            high_threshold: Threshold for high relevance (default 0.7)
            low_threshold: Threshold for low relevance (default 0.3)
        
        Returns:
            Tuple of (filtered_items, stats_dict)
        """
        scored_items = self.score_context_items(items, current_task)
        
        # Categorize items
        high_items = [item for item in scored_items if item.total_score > high_threshold]
        medium_items = [item for item in scored_items 
                       if low_threshold < item.total_score <= high_threshold]
        low_items = [item for item in scored_items if item.total_score <= low_threshold]
        
        # Start with high-relevance items (always included)
        filtered_items = high_items.copy()
        current_tokens = sum(item.token_estimate for item in filtered_items)
        
        # Add medium-relevance items if we have token budget space
        # Sort by score descending
        medium_items_sorted = sorted(medium_items, key=lambda x: x.total_score, reverse=True)
        
        for item in medium_items_sorted:
            item_tokens = item.token_estimate
            
            # Check if we can include this item
            if token_budget is None or (current_tokens + item_tokens) <= token_budget:
                filtered_items.append(item)
                current_tokens += item_tokens
            else:
                # Not enough space, stop adding medium items
                break
        
        # Sort final list by score
        filtered_items = sorted(filtered_items, key=lambda x: x.total_score, reverse=True)
        
        # Stats
        stats = {
            'total_items': len(items),
            'high_relevance': len(high_items),
            'medium_relevance': len(medium_items),
            'low_relevance': len(low_items),
            'included': len(filtered_items),
            'excluded': len(items) - len(filtered_items),
            'token_budget': token_budget,
            'tokens_used': current_tokens,
            'high_threshold': high_threshold,
            'low_threshold': low_threshold
        }
        
        logger.info(
            "Filtered context by relevance",
            **stats
        )
        
        return filtered_items, stats
    
    def update_from_feedback(
        self,
        items: List[ContextItem],
        feedback: Dict[str, float]
    ):
        """
        Update item scores based on LLM feedback.
        
        Args:
            items: List of context items
            feedback: Dictionary mapping item IDs to feedback scores (0.0 to 1.0)
        """
        for item in items:
            if item.id in feedback:
                item.feedback_score = feedback[item.id]
                
                # Adjust total score based on feedback
                # Blend original score with feedback (70% original, 30% feedback)
                item.total_score = (
                    0.7 * item.total_score +
                    0.3 * item.feedback_score
                )
                
                logger.debug(
                    "Updated item from feedback",
                    item_id=item.id,
                    original_score=item.total_score / 0.7 if item.feedback_score > 0 else item.total_score,
                    feedback_score=item.feedback_score,
                    new_score=item.total_score
                )
        
        logger.info(
            "Updated items from feedback",
            updated_count=len(feedback),
            total_items=len(items)
        )
    
    def track_needed_items(
        self,
        items: List[ContextItem],
        needed_item_ids: Set[str]
    ):
        """
        Track which items were actually needed during execution.
        
        Args:
            items: List of context items
            needed_item_ids: IDs of items that were actually needed
        """
        for item in items:
            item.was_needed = item.id in needed_item_ids
        
        # Update relevance accuracy metrics
        included_ids = {item.id for item in items}
        self.metrics.update_relevance_accuracy(included_ids, needed_item_ids)
        
        logger.debug(
            "Tracked needed items",
            total_items=len(items),
            needed_count=len(needed_item_ids),
            included_count=len(included_ids),
            relevance_accuracy=self.metrics.relevance_accuracy
        )
    
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
    
    def learn_weights(self, success_rate: float, relevance_feedback: Optional[Dict[str, float]] = None):
        """
        Learn optimal weights from success rate and relevance feedback.
        
        Adjusts weights based on downstream success and feedback to improve scoring accuracy.
        
        Args:
            success_rate: Downstream success rate (0.0 to 1.0)
            relevance_feedback: Optional feedback on which scoring factors worked best
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
        
        # V5: Adjust weights based on relevance feedback
        if relevance_feedback:
            self._adjust_weights_from_feedback(relevance_feedback)
    
    def _adjust_weights_from_feedback(self, feedback: Dict[str, float]):
        """
        Adjust scoring weights based on feedback.
        
        Args:
            feedback: Dictionary mapping scoring factors to effectiveness scores (0.0 to 1.0)
        """
        # Normalize feedback to sum to 1.0
        total = sum(feedback.values())
        if total == 0:
            return
        
        normalized_feedback = {k: v / total for k, v in feedback.items()}
        
        # Move weights toward feedback
        new_weights = ScoringWeights(
            recency=self._interpolate_weight(
                self.weights.recency,
                normalized_feedback.get('recency', self.weights.recency),
                self.learning_rate
            ),
            similarity=self._interpolate_weight(
                self.weights.similarity,
                normalized_feedback.get('similarity', self.weights.similarity),
                self.learning_rate
            ),
            dependency=self._interpolate_weight(
                self.weights.dependency,
                normalized_feedback.get('dependency', self.weights.dependency),
                self.learning_rate
            ),
            impact=self._interpolate_weight(
                self.weights.impact,
                normalized_feedback.get('impact', self.weights.impact),
                self.learning_rate
            )
        )
        
        # Update weights if valid
        if new_weights.validate():
            self.weights = new_weights
            logger.info(
                "Adjusted weights from feedback",
                feedback=feedback,
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
                'scoring_accuracy': self.metrics.scoring_accuracy,
                'relevance_accuracy': self.metrics.relevance_accuracy,
                'false_positive_rate': self.metrics.false_positive_rate,
                'false_negative_rate': self.metrics.false_negative_rate
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
        
        metrics_data = state.get('metrics', {})
        self.metrics = ScoringMetrics(
            total_items_scored=metrics_data.get('total_items_scored', 0),
            average_score=metrics_data.get('average_score', 0.0),
            score_distribution=metrics_data.get('score_distribution', {}),
            scoring_accuracy=metrics_data.get('scoring_accuracy', 0.0),
            relevance_accuracy=metrics_data.get('relevance_accuracy', 0.0),
            false_positive_rate=metrics_data.get('false_positive_rate', 0.0),
            false_negative_rate=metrics_data.get('false_negative_rate', 0.0)
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
            total_items_scored=self.metrics.total_items_scored,
            relevance_accuracy=self.metrics.relevance_accuracy
        )
