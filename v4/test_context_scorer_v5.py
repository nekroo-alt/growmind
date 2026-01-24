"""
Comprehensive unit tests for V5 ContextScorer enhancements.

Tests for:
- Token-aware relevance filtering
- LLM feedback mechanism
- Relevance accuracy tracking
- Smart filtering strategy
"""

import unittest
import sys
import os
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from logic.context_scorer import (
    ContextScorer,
    ContextItem,
    ScoringWeights,
    ScoringMetrics,
    RelevanceCategory,
    ScoringFactor
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
    
    def test_get_relevance_category_boundary_high(self):
        """Test boundary condition for high relevance (> 0.7)."""
        item = ContextItem(
            id="test_4",
            content="Test content",
            timestamp=datetime.now(),
            item_type="action"
        )
        item.total_score = 0.71
        self.assertEqual(item.get_relevance_category(), RelevanceCategory.HIGH)
    
    def test_get_relevance_category_boundary_medium_upper(self):
        """Test boundary condition for medium relevance (<= 0.7)."""
        item = ContextItem(
            id="test_5",
            content="Test content",
            timestamp=datetime.now(),
            item_type="action"
        )
        item.total_score = 0.7
        self.assertEqual(item.get_relevance_category(), RelevanceCategory.MEDIUM)
    
    def test_get_relevance_category_boundary_medium_lower(self):
        """Test boundary condition for medium relevance (> 0.3)."""
        item = ContextItem(
            id="test_6",
            content="Test content",
            timestamp=datetime.now(),
            item_type="action"
        )
        item.total_score = 0.31
        self.assertEqual(item.get_relevance_category(), RelevanceCategory.MEDIUM)
    
    def test_get_relevance_category_boundary_low(self):
        """Test boundary condition for low relevance (<= 0.3)."""
        item = ContextItem(
            id="test_7",
            content="Test content",
            timestamp=datetime.now(),
            item_type="action"
        )
        item.total_score = 0.3
        self.assertEqual(item.get_relevance_category(), RelevanceCategory.LOW)


class TestContextItemV5(unittest.TestCase):
    """Test V5 enhancements to ContextItem."""
    
    def test_token_estimate_initialization(self):
        """Test that token_estimate initializes to 0."""
        item = ContextItem(
            id="test_1",
            content="Test content",
            timestamp=datetime.now(),
            item_type="action"
        )
        self.assertEqual(item.token_estimate, 0)
    
    def test_token_estimate_custom(self):
        """Test setting custom token_estimate."""
        item = ContextItem(
            id="test_2",
            content="Test content",
            timestamp=datetime.now(),
            item_type="action",
            token_estimate=500
        )
        self.assertEqual(item.token_estimate, 500)
    
    def test_was_needed_initialization(self):
        """Test that was_needed initializes to False."""
        item = ContextItem(
            id="test_3",
            content="Test content",
            timestamp=datetime.now(),
            item_type="action"
        )
        self.assertFalse(item.was_needed)
    
    def test_feedback_score_initialization(self):
        """Test that feedback_score initializes to 0.5."""
        item = ContextItem(
            id="test_4",
            content="Test content",
            timestamp=datetime.now(),
            item_type="action"
        )
        self.assertEqual(item.feedback_score, 0.5)


class TestScoringMetricsV5(unittest.TestCase):
    """Test V5 enhancements to ScoringMetrics."""
    
    def test_relevance_accuracy_initialization(self):
        """Test that relevance_accuracy initializes to 0.0."""
        metrics = ScoringMetrics()
        self.assertEqual(metrics.relevance_accuracy, 0.0)
        self.assertEqual(metrics.false_positive_rate, 0.0)
        self.assertEqual(metrics.false_negative_rate, 0.0)
    
    def test_update_relevance_accuracy_perfect(self):
        """Test relevance accuracy update with perfect predictions."""
        metrics = ScoringMetrics()
        
        included = {"item1", "item2", "item3"}
        needed = {"item1", "item2", "item3"}
        
        metrics.update_relevance_accuracy(included, needed)
        
        # Perfect match: precision = 1.0, recall = 1.0, F1 = 1.0
        self.assertEqual(metrics.relevance_accuracy, 1.0)
        self.assertEqual(metrics.false_positive_rate, 0.0)
        self.assertEqual(metrics.false_negative_rate, 0.0)
    
    def test_update_relevance_accuracy_partial(self):
        """Test relevance accuracy update with partial predictions."""
        metrics = ScoringMetrics()
        
        included = {"item1", "item2", "item3"}
        needed = {"item1", "item4", "item5"}
        
        metrics.update_relevance_accuracy(included, needed)
        
        # True positives: item1 (1)
        # False positives: item2, item3 (2)
        # False negatives: item4, item5 (2)
        # Precision: 1/3 = 0.333
        # Recall: 1/3 = 0.333
        # F1: 2 * (0.333 * 0.333) / (0.333 + 0.333) = 0.333
        
        self.assertAlmostEqual(metrics.relevance_accuracy, 0.333, places=2)
        self.assertAlmostEqual(metrics.false_positive_rate, 0.667, places=2)
        self.assertAlmostEqual(metrics.false_negative_rate, 0.4, places=2)
    
    def test_update_relevance_accuracy_empty(self):
        """Test relevance accuracy update with empty sets."""
        metrics = ScoringMetrics()
        
        included = set()
        needed = {"item1", "item2"}
        
        metrics.update_relevance_accuracy(included, needed)
        
        # No items included, should not update
        self.assertEqual(metrics.relevance_accuracy, 0.0)
        self.assertEqual(metrics.false_positive_rate, 0.0)
        self.assertEqual(metrics.false_negative_rate, 0.0)
    
    def test_update_relevance_accuracy_no_needed(self):
        """Test relevance accuracy update when no items needed."""
        metrics = ScoringMetrics()
        
        included = {"item1", "item2"}
        needed = set()
        
        metrics.update_relevance_accuracy(included, needed)
        
        # All false positives, precision = 0, recall undefined
        self.assertEqual(metrics.relevance_accuracy, 0.0)
        self.assertEqual(metrics.false_positive_rate, 1.0)


class TestFilterByRelevance(unittest.TestCase):
    """Test token-aware relevance filtering."""
    
    def setUp(self):
        """Set up test scorer and items."""
        self.scorer = ContextScorer()
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
        
        # Should include 3 items (2 high + 1 highest medium)
        self.assertEqual(len(filtered), 3)
        self.assertEqual(stats['tokens_used'], 370)
        self.assertEqual(filtered[2].id, "medium_2")  # 120 tokens
    
    def test_filter_by_relevance_custom_thresholds(self):
        """Test filtering with custom relevance thresholds."""
        filtered, stats = self.scorer.filter_by_relevance(
            self.items,
            "Add user authentication",
            token_budget=None,
            high_threshold=0.6,  # Stricter high threshold
            low_threshold=0.2    # Stricter low threshold
        )
        
        # With stricter thresholds:
        # High: score > 0.6 (1 item: 0.9)
        # Medium: 0.2 < score <= 0.6 (3 items: 0.8, 0.6, 0.5, 0.2 is excluded)
        # Low: score <= 0.2 (1 item: 0.1)
        # Should include 4 items
        self.assertEqual(len(filtered), 4)
        self.assertEqual(stats['high_relevance'], 1)
        self.assertEqual(stats['medium_relevance'], 3)
    
    def test_filter_by_relevance_all_excluded(self):
        """Test filtering when all items are low relevance."""
        # Set all scores to low
        for item in self.items:
            item.total_score = 0.1
        
        filtered, stats = self.scorer.filter_by_relevance(
            self.items,
            "Add user authentication",
            token_budget=None
        )
        
        # Should exclude all items
        self.assertEqual(len(filtered), 0)
        self.assertEqual(stats['included'], 0)
        self.assertEqual(stats['excluded'], 6)
    
    def test_filter_by_relevance_sorting(self):
        """Test that filtered items are sorted by score."""
        filtered, stats = self.scorer.filter_by_relevance(
            self.items,
            "Add user authentication",
            token_budget=None
        )
        
        # Check that items are sorted by score descending
        for i in range(len(filtered) - 1):
            self.assertGreaterEqual(
                filtered[i].total_score,
                filtered[i + 1].total_score
            )


class TestUpdateFromFeedback(unittest.TestCase):
    """Test LLM feedback mechanism."""
    
    def setUp(self):
        """Set up test scorer and items."""
        self.scorer = ContextScorer()
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
        
        # Set initial scores
        self.items[0].total_score = 0.5
        self.items[1].total_score = 0.6
        self.items[2].total_score = 0.7
    
    def test_update_from_feedback_single_item(self):
        """Test updating a single item from feedback."""
        feedback = {"item1": 0.9}  # Increase score for item1
        
        self.scorer.update_from_feedback(self.items, feedback)
        
        # Original: 0.5
        # Feedback: 0.9
        # Blended: 0.7 * 0.5 + 0.3 * 0.9 = 0.35 + 0.27 = 0.62
        self.assertAlmostEqual(self.items[0].total_score, 0.62, places=2)
        self.assertEqual(self.items[0].feedback_score, 0.9)
    
    def test_update_from_feedback_multiple_items(self):
        """Test updating multiple items from feedback."""
        feedback = {
            "item1": 0.9,  # Increase
            "item2": 0.3,  # Decrease
            "item3": 0.8   # Slight increase
        }
        
        self.scorer.update_from_feedback(self.items, feedback)
        
        # Item1: 0.7 * 0.5 + 0.3 * 0.9 = 0.62
        # Item2: 0.7 * 0.6 + 0.3 * 0.3 = 0.51
        # Item3: 0.7 * 0.7 + 0.3 * 0.8 = 0.73
        
        self.assertAlmostEqual(self.items[0].total_score, 0.62, places=2)
        self.assertAlmostEqual(self.items[1].total_score, 0.51, places=2)
        self.assertAlmostEqual(self.items[2].total_score, 0.73, places=2)
    
    def test_update_from_feedback_unmatched_items(self):
        """Test that unmatched items are not updated."""
        feedback = {"item999": 0.9}  # Item doesn't exist
        
        self.scorer.update_from_feedback(self.items, feedback)
        
        # No items should be updated
        self.assertEqual(self.items[0].total_score, 0.5)
        self.assertEqual(self.items[1].total_score, 0.6)
        self.assertEqual(self.items[2].total_score, 0.7)
    
    def test_update_from_feedback_empty_feedback(self):
        """Test that empty feedback doesn't change anything."""
        feedback = {}
        
        self.scorer.update_from_feedback(self.items, feedback)
        
        self.assertEqual(self.items[0].total_score, 0.5)
        self.assertEqual(self.items[1].total_score, 0.6)
        self.assertEqual(self.items[2].total_score, 0.7)


class TestTrackNeededItems(unittest.TestCase):
    """Test tracking of needed items for relevance accuracy."""
    
    def setUp(self):
        """Set up test scorer and items."""
        self.scorer = ContextScorer()
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
    
    def test_track_needed_items_partial(self):
        """Test tracking when some items are needed."""
        needed_ids = {"item1", "item3"}
        
        self.scorer.track_needed_items(self.items, needed_ids)
        
        # Only item1 and item3 should be marked as needed
        self.assertTrue(self.items[0].was_needed)
        self.assertFalse(self.items[1].was_needed)
        self.assertTrue(self.items[2].was_needed)
        
        # Relevance accuracy should reflect partial match
        # True positives: 2 (item1, item3)
        # False positives: 1 (item2)
        # False negatives: 0
        # Precision: 2/3 = 0.667
        # Recall: 2/2 = 1.0
        # F1: 2 * (0.667 * 1.0) / (0.667 + 1.0) = 0.8
        
        self.assertAlmostEqual(self.scorer.metrics.relevance_accuracy, 0.8, places=1)
    
    def test_track_needed_items_none_needed(self):
        """Test tracking when no items are needed."""
        needed_ids = set()
        
        self.scorer.track_needed_items(self.items, needed_ids)
        
        # No items should be marked as needed
        self.assertFalse(self.items[0].was_needed)
        self.assertFalse(self.items[1].was_needed)
        self.assertFalse(self.items[2].was_needed)
        
        # All false positives
        self.assertEqual(self.scorer.metrics.relevance_accuracy, 0.0)
        self.assertEqual(self.scorer.metrics.false_positive_rate, 1.0)
    
    def test_track_needed_items_empty_list(self):
        """Test tracking with empty item list."""
        needed_ids = {"item1", "item2"}
        
        self.scorer.track_needed_items([], needed_ids)
        
        # Should not crash, metrics should remain at defaults
        self.assertEqual(self.scorer.metrics.relevance_accuracy, 0.0)


class TestLearnWeightsV5(unittest.TestCase):
    """Test V5 weight learning with relevance feedback."""
    
    def setUp(self):
        """Set up test scorer."""
        self.scorer = ContextScorer(learning_rate=0.5)
    
    def test_learn_weights_with_relevance_feedback(self):
        """Test weight learning from relevance feedback."""
        feedback = {
            'recency': 0.8,    # High effectiveness
            'similarity': 0.6,
            'dependency': 0.4,
            'impact': 0.2      # Low effectiveness
        }
        
        original_weights = self.scorer.weights
        
        self.scorer.learn_weights(success_rate=0.8, relevance_feedback=feedback)
        
        # Weights should move toward feedback
        # Learning rate is 0.5, so move 50% toward target
        
        # Recency: 0.3 -> 0.8 (target), move 50% -> 0.3 + 0.5*(0.8-0.3) = 0.55
        self.assertGreater(self.scorer.weights.recency, original_weights.recency)
        
        # Impact: 0.15 -> 0.2 (target), move 50% -> 0.15 + 0.5*(0.2-0.15) = 0.175
        self.assertGreater(self.scorer.weights.impact, original_weights.impact)
    
    def test_learn_weights_without_relevance_feedback(self):
        """Test weight learning without relevance feedback (backward compatibility)."""
        # Add some history
        self.scorer.historical_weights.append(
            (ScoringWeights(recency=0.5, similarity=0.3, dependency=0.1, impact=0.1), 0.9)
        )
        
        original_weights = self.scorer.weights
        
        # Low success rate should trigger weight adjustment
        self.scorer.learn_weights(success_rate=0.6)
        
        # Weights should move toward historically best weights
        self.assertNotEqual(
            self.scorer.weights.recency,
            original_weights.recency
        )
    
    def test_learn_weights_invalid_feedback(self):
        """Test that invalid feedback doesn't change weights."""
        feedback = {'invalid_factor': 1.0}  # Invalid factor name
        
        original_weights = self.scorer.weights
        
        self.scorer.learn_weights(success_rate=0.8, relevance_feedback=feedback)
        
        # Weights should remain unchanged
        self.assertEqual(self.scorer.weights.recency, original_weights.recency)
        self.assertEqual(self.scorer.weights.similarity, original_weights.similarity)
        self.assertEqual(self.scorer.weights.dependency, original_weights.dependency)
        self.assertEqual(self.scorer.weights.impact, original_weights.impact)


class TestStatePersistenceV5(unittest.TestCase):
    """Test V5 state persistence."""
    
    def setUp(self):
        """Set up test scorer with V5 features."""
        self.scorer = ContextScorer(learning_rate=0.2)
        
        # Add some metrics
        self.scorer.metrics.total_items_scored = 100
        self.scorer.metrics.average_score = 0.6
        self.scorer.metrics.relevance_accuracy = 0.85
        self.scorer.metrics.false_positive_rate = 0.1
        self.scorer.metrics.false_negative_rate = 0.05
    
    def test_export_state_includes_v5_metrics(self):
        """Test that exported state includes V5 metrics."""
        state = self.scorer.export_state()
        
        # Check V5 metrics are present
        self.assertIn('relevance_accuracy', state['metrics'])
        self.assertIn('false_positive_rate', state['metrics'])
        self.assertIn('false_negative_rate', state['metrics'])
        
        # Check values
        self.assertEqual(state['metrics']['relevance_accuracy'], 0.85)
        self.assertEqual(state['metrics']['false_positive_rate'], 0.1)
        self.assertEqual(state['metrics']['false_negative_rate'], 0.05)
    
    def test_import_state_restores_v5_metrics(self):
        """Test that imported state restores V5 metrics."""
        state = {
            'weights': {
                'recency': 0.3,
                'similarity': 0.3,
                'dependency': 0.25,
                'impact': 0.15
            },
            'learning_rate': 0.2,
            'metrics': {
                'total_items_scored': 150,
                'average_score': 0.7,
                'score_distribution': {'high': 50, 'medium': 50, 'low': 50},
                'scoring_accuracy': 0.8,
                'relevance_accuracy': 0.9,
                'false_positive_rate': 0.08,
                'false_negative_rate': 0.02
            },
            'historical_weights': []
        }
        
        new_scorer = ContextScorer()
        new_scorer.import_state(state)
        
        # Check V5 metrics are restored
        self.assertEqual(new_scorer.metrics.relevance_accuracy, 0.9)
        self.assertEqual(new_scorer.metrics.false_positive_rate, 0.08)
        self.assertEqual(new_scorer.metrics.false_negative_rate, 0.02)
    
    def test_import_state_missing_v5_metrics(self):
        """Test that import handles missing V5 metrics gracefully."""
        state = {
            'weights': {
                'recency': 0.3,
                'similarity': 0.3,
                'dependency': 0.25,
                'impact': 0.15
            },
            'learning_rate': 0.2,
            'metrics': {
                'total_items_scored': 100,
                'average_score': 0.6,
                'score_distribution': {'high': 30, 'medium': 30, 'low': 40},
                'scoring_accuracy': 0.75
                # Missing V5 metrics
            },
            'historical_weights': []
        }
        
        new_scorer = ContextScorer()
        new_scorer.import_state(state)
        
        # V5 metrics should default to 0.0
        self.assertEqual(new_scorer.metrics.relevance_accuracy, 0.0)
        self.assertEqual(new_scorer.metrics.false_positive_rate, 0.0)
        self.assertEqual(new_scorer.metrics.false_negative_rate, 0.0)


if __name__ == '__main__':
    unittest.main()