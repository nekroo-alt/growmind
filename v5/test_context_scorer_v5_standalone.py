"""
Standalone test for V5 ContextScorer enhancements - minimal dependencies.
"""

import unittest
import sys
from datetime import datetime

# Minimal imports to avoid circular dependencies
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from enum import Enum

# Minimal implementations for testing
class RelevanceCategory(Enum):
    """Relevance category for context items."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

@dataclass
class ScoringWeights:
    """Weights for scoring factors."""
    recency: float = 0.3
    similarity: float = 0.3
    dependency: float = 0.25
    impact: float = 0.15

@dataclass
class ScoringMetrics:
    """Scoring metrics and statistics."""
    total_items_scored: int = 0
    average_score: float = 0.0
    score_distribution: Dict[str, int] = None
    scoring_accuracy: float = 0.0
    relevance_accuracy: float = 0.0
    false_positive_rate: float = 0.0
    false_negative_rate: float = 0.0
    
    def __post_init__(self):
        if self.score_distribution is None:
            self.score_distribution = {'high': 0, 'medium': 0, 'low': 0}

@dataclass
class ContextItem:
    """Context item with V5 enhancements."""
    id: str
    content: str
    timestamp: datetime
    item_type: str
    token_estimate: int = 0
    was_needed: bool = False
    feedback_score: float = 0.5
    total_score: float = 0.0
    recency_score: float = 0.0
    similarity_score: float = 0.0
    dependency_score: float = 0.0
    impact_score: float = 0.0
    
    def get_relevance_category(self) -> RelevanceCategory:
        """Get relevance category based on total score."""
        if self.total_score > 0.7:
            return RelevanceCategory.HIGH
        elif self.total_score > 0.3:
            return RelevanceCategory.MEDIUM
        else:
            return RelevanceCategory.LOW


class MinimalContextScorer:
    """Minimal ContextScorer for testing V5 features."""
    
    def __init__(self, learning_rate: float = 0.2):
        self.weights = ScoringWeights()
        self.learning_rate = learning_rate
        self.metrics = ScoringMetrics()
        self.historical_weights: List[tuple] = []
    
    def filter_by_relevance(
        self,
        items: List[ContextItem],
        task: str,
        token_budget: Optional[int] = None,
        high_threshold: float = 0.7,
        low_threshold: float = 0.3
    ) -> tuple[List[ContextItem], Dict[str, Any]]:
        """Filter context items by relevance with token awareness."""
        
        # Categorize items
        for item in items:
            if item.total_score > high_threshold:
                item_category = RelevanceCategory.HIGH
            elif item.total_score > low_threshold:
                item_category = RelevanceCategory.MEDIUM
            else:
                item_category = RelevanceCategory.LOW
        
        # Filter based on relevance
        always_include = [
            item for item in items
            if item.total_score > high_threshold
        ]
        maybe_include = [
            item for item in items
            if low_threshold < item.total_score <= high_threshold
        ]
        
        # Include maybe items based on token budget
        if token_budget is not None:
            included = self._select_by_token_budget(
                always_include, maybe_include, token_budget
            )
        else:
            included = always_include + maybe_include
        
        # Calculate stats
        stats = {
            'total_items': len(items),
            'high_relevance': len(always_include),
            'medium_relevance': len(maybe_include),
            'low_relevance': len(items) - len(always_include) - len(maybe_include),
            'included': len(included),
            'excluded': len(items) - len(included),
            'token_budget': token_budget,
            'tokens_used': sum(item.token_estimate for item in included)
        }
        
        # Sort by score
        included.sort(key=lambda x: x.total_score, reverse=True)
        
        return included, stats
    
    def _select_by_token_budget(
        self,
        always_include: List[ContextItem],
        maybe_include: List[ContextItem],
        token_budget: int
    ) -> List[ContextItem]:
        """Select items within token budget."""
        included = list(always_include)
        used_tokens = sum(item.token_estimate for item in included)
        
        # Sort maybe items by score
        maybe_include.sort(key=lambda x: x.total_score, reverse=True)
        
        for item in maybe_include:
            if used_tokens + item.token_estimate <= token_budget:
                included.append(item)
                used_tokens += item.token_estimate
            # Continue to check other items - don't break!
        
        return included
    
    def update_from_feedback(
        self,
        items: List[ContextItem],
        feedback: Dict[str, float]
    ):
        """Update item scores from LLM feedback."""
        feedback_weight = 0.3  # Weight for feedback
        original_weight = 0.7    # Weight for original score
        
        for item in items:
            if item.id in feedback:
                item.feedback_score = feedback[item.id]
                # Blend original score with feedback
                item.total_score = (
                    original_weight * item.total_score +
                    feedback_weight * feedback[item.id]
                )
    
    def track_needed_items(
        self,
        items: List[ContextItem],
        needed_ids: set
    ):
        """Track which items were actually needed."""
        included_ids = {item.id for item in items}
        
        # Mark items as needed
        for item in items:
            item.was_needed = item.id in needed_ids
        
        # Calculate relevance accuracy
        true_positives = included_ids & needed_ids
        false_positives = included_ids - needed_ids
        false_negatives = needed_ids - included_ids
        
        precision = len(true_positives) / len(included_ids) if included_ids else 0
        recall = len(true_positives) / len(needed_ids) if needed_ids else 0
        
        if precision + recall > 0:
            f1 = 2 * (precision * recall) / (precision + recall)
        else:
            f1 = 0.0
        
        self.metrics.relevance_accuracy = f1
        self.metrics.false_positive_rate = (
            len(false_positives) / len(included_ids) if included_ids else 0
        )
        self.metrics.false_negative_rate = (
            len(false_negatives) / len(needed_ids) if needed_ids else 0
        )
    
    def learn_weights(
        self,
        success_rate: float,
        relevance_feedback: Optional[Dict[str, float]] = None
    ):
        """Learn weights from performance and feedback."""
        if relevance_feedback:
            # Adjust weights toward feedback effectiveness
            for factor, effectiveness in relevance_feedback.items():
                if hasattr(self.weights, factor):
                    current = getattr(self.weights, factor)
                    # Move toward feedback
                    setattr(
                        self.weights,
                        factor,
                        current + self.learning_rate * (effectiveness - current)
                    )


class TestRelevanceCategory(unittest.TestCase):
    """Test relevance category enumeration and classification."""
    
    def test_relevance_category_values(self):
        """Test that relevance categories have correct values."""
        self.assertEqual(RelevanceCategory.HIGH.value, "high")
        self.assertEqual(RelevanceCategory.MEDIUM.value, "medium")
        self.assertEqual(RelevanceCategory.LOW.value, "low")
    
    def test_get_relevance_category_high(self):
        """Test classification of high-relevance items."""
        item = ContextItem(
            id="test_1",
            content="Test content",
            timestamp=datetime.now(),
            item_type="action"
        )
        item.total_score = 0.8
        self.assertEqual(item.get_relevance_category(), RelevanceCategory.HIGH)
    
    def test_get_relevance_category_medium(self):
        """Test classification of medium-relevance items."""
        item = ContextItem(
            id="test_2",
            content="Test content",
            timestamp=datetime.now(),
            item_type="action"
        )
        item.total_score = 0.5
        self.assertEqual(item.get_relevance_category(), RelevanceCategory.MEDIUM)
    
    def test_get_relevance_category_low(self):
        """Test classification of low-relevance items."""
        item = ContextItem(
            id="test_3",
            content="Test content",
            timestamp=datetime.now(),
            item_type="action"
        )
        item.total_score = 0.2
        self.assertEqual(item.get_relevance_category(), RelevanceCategory.LOW)


class TestFilterByRelevance(unittest.TestCase):
    """Test token-aware relevance filtering."""
    
    def setUp(self):
        """Set up test scorer and items."""
        self.scorer = MinimalContextScorer()
        self.current_time = datetime.now()
        
        # Create test items with different scores
        self.items = [
            ContextItem(
                id="high_1",
                content="High relevance item 1",
                timestamp=self.current_time,
                item_type="action",
                token_estimate=100
            ),
            ContextItem(
                id="high_2",
                content="High relevance item 2",
                timestamp=self.current_time,
                item_type="action",
                token_estimate=150
            ),
            ContextItem(
                id="medium_1",
                content="Medium relevance item 1",
                timestamp=self.current_time,
                item_type="state",
                token_estimate=200
            ),
            ContextItem(
                id="medium_2",
                content="Medium relevance item 2",
                timestamp=self.current_time,
                item_type="state",
                token_estimate=120
            ),
            ContextItem(
                id="low_1",
                content="Low relevance item 1",
                timestamp=self.current_time,
                item_type="debug",
                token_estimate=80
            ),
            ContextItem(
                id="low_2",
                content="Low relevance item 2",
                timestamp=self.current_time,
                item_type="debug",
                token_estimate=90
            ),
        ]
        
        # Manually set scores for testing
        self.items[0].total_score = 0.9   # high
        self.items[1].total_score = 0.8   # high
        self.items[2].total_score = 0.6   # medium
        self.items[3].total_score = 0.5   # medium
        self.items[4].total_score = 0.2   # low
        self.items[5].total_score = 0.1   # low
    
    def test_filter_by_relevance_no_budget(self):
        """Test filtering without token budget (include all high and medium)."""
        filtered, stats = self.scorer.filter_by_relevance(
            self.items,
            "Add user authentication",
            token_budget=None
        )
        
        # Should include 4 items (2 high + 2 medium)
        self.assertEqual(len(filtered), 4)
        self.assertEqual(stats['total_items'], 6)
        self.assertEqual(stats['high_relevance'], 2)
        self.assertEqual(stats['medium_relevance'], 2)
        self.assertEqual(stats['low_relevance'], 2)
        self.assertEqual(stats['included'], 4)
        self.assertEqual(stats['excluded'], 2)
        self.assertIsNone(stats['token_budget'])
    
    def test_filter_by_relevance_with_budget(self):
        """Test filtering with limited token budget."""
        filtered, stats = self.scorer.filter_by_relevance(
            self.items,
            "Add user authentication",
            token_budget=250  # Only enough for 2 high items (100 + 150)
        )
        
        # Should include only 2 high items
        self.assertEqual(len(filtered), 2)
        self.assertEqual(filtered[0].id, "high_1")  # Sorted by score
        self.assertEqual(filtered[1].id, "high_2")
        self.assertEqual(stats['tokens_used'], 250)
        self.assertEqual(stats['token_budget'], 250)
    
    def test_filter_by_relevance_partial_medium(self):
        """Test filtering with budget for some medium items."""
        filtered, stats = self.scorer.filter_by_relevance(
            self.items,
            "Add user authentication",
            token_budget=400  # Enough for 2 high (250) + 1 medium (120)
        )
        
        # Should include 3 items (2 high + 1 medium that fits)
        # medium_1 (200 tokens) doesn't fit, medium_2 (120 tokens) fits
        self.assertEqual(len(filtered), 3)
        self.assertEqual(stats['tokens_used'], 370)
        # medium_2 is included because it fits in the remaining budget (400 - 250 = 150)
        # medium_1 is excluded because 200 > 150 remaining budget
        self.assertIn("medium_2", [item.id for item in filtered])


class TestUpdateFromFeedback(unittest.TestCase):
    """Test LLM feedback mechanism."""
    
    def setUp(self):
        """Set up test scorer and items."""
        self.scorer = MinimalContextScorer()
        self.items = [
            ContextItem(
                id="item1",
                content="Item 1",
                timestamp=datetime.now(),
                item_type="action"
            ),
            ContextItem(
                id="item2",
                content="Item 2",
                timestamp=datetime.now(),
                item_type="action"
            ),
        ]
        
        # Set initial scores
        self.items[0].total_score = 0.5
        self.items[1].total_score = 0.6
    
    def test_update_from_feedback_single_item(self):
        """Test updating a single item from feedback."""
        feedback = {"item1": 0.9}  # Increase score for item1
        
        self.scorer.update_from_feedback(self.items, feedback)
        
        # Original: 0.5
        # Feedback: 0.9
        # Blended: 0.7 * 0.5 + 0.3 * 0.9 = 0.35 + 0.27 = 0.62
        self.assertAlmostEqual(self.items[0].total_score, 0.62, places=2)
        self.assertEqual(self.items[0].feedback_score, 0.9)


class TestTrackNeededItems(unittest.TestCase):
    """Test tracking of needed items for relevance accuracy."""
    
    def setUp(self):
        """Set up test scorer and items."""
        self.scorer = MinimalContextScorer()
        self.items = [
            ContextItem(
                id="item1",
                content="Item 1",
                timestamp=datetime.now(),
                item_type="action"
            ),
            ContextItem(
                id="item2",
                content="Item 2",
                timestamp=datetime.now(),
                item_type="action"
            ),
            ContextItem(
                id="item3",
                content="Item 3",
                timestamp=datetime.now(),
                item_type="action"
            ),
        ]
    
    def test_track_needed_items_all_needed(self):
        """Test tracking when all items are needed."""
        needed_ids = {"item1", "item2", "item3"}
        
        self.scorer.track_needed_items(self.items, needed_ids)
        
        # All items should be marked as needed
        self.assertTrue(self.items[0].was_needed)
        self.assertTrue(self.items[1].was_needed)
        self.assertTrue(self.items[2].was_needed)
        
        # Relevance accuracy should be perfect
        self.assertEqual(self.scorer.metrics.relevance_accuracy, 1.0)


if __name__ == '__main__':
    unittest.main()