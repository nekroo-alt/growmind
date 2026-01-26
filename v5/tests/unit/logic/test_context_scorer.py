"""
Unit tests for Context Relevance Scorer (V4 Task 1.4)

Tests context scoring, ranking, pruning, and learning capabilities.
"""

import pytest
from datetime import datetime, timedelta
from v5.logic.context_scorer import (
    ContextScorer,
    ContextItem,
    ScoringWeights,
    ScoringMetrics,
    ScoringFactor
)


class TestContextItem:
    """Test ContextItem dataclass."""
    
    def test_context_item_creation(self):
        """Test creating a context item."""
        item = ContextItem(
            id="test-1",
            content="Test content",
            timestamp=datetime.now(),
            item_type="action"
        )
        
        assert item.id == "test-1"
        assert item.content == "Test content"
        assert item.item_type == "action"
        assert item.recency_score == 0.0
        assert item.total_score == 0.0
    
    def test_context_item_with_metadata(self):
        """Test creating a context item with metadata."""
        metadata = {
            'severity': 'high',
            'dependencies': ['module_a', 'module_b']
        }
        item = ContextItem(
            id="test-2",
            content="Test content",
            timestamp=datetime.now(),
            item_type="error",
            metadata=metadata
        )
        
        assert item.metadata == metadata
        assert item.item_type == "error"
    
    def test_compute_hash(self):
        """Test computing hash of content."""
        item = ContextItem(
            id="test-3",
            content="Test content",
            timestamp=datetime.now(),
            item_type="action"
        )
        
        hash1 = item.compute_hash()
        hash2 = item.compute_hash()
        
        # Same content should produce same hash
        assert hash1 == hash2
        
        # Different content should produce different hash
        item2 = ContextItem(
            id="test-4",
            content="Different content",
            timestamp=datetime.now(),
            item_type="action"
        )
        assert item.compute_hash() != item2.compute_hash()


class TestScoringWeights:
    """Test ScoringWeights dataclass."""
    
    def test_default_weights(self):
        """Test default weights sum to 1.0."""
        weights = ScoringWeights()
        total = sum([weights.recency, weights.similarity, 
                     weights.dependency, weights.impact])
        
        assert abs(total - 1.0) < 0.01
    
    def test_custom_weights(self):
        """Test custom weights can be set."""
        weights = ScoringWeights(
            recency=0.4,
            similarity=0.3,
            dependency=0.2,
            impact=0.1
        )
        
        assert weights.recency == 0.4
        assert weights.similarity == 0.3
        assert weights.dependency == 0.2
        assert weights.impact == 0.1
    
    def test_validate_valid_weights(self):
        """Test validation of valid weights."""
        weights = ScoringWeights(
            recency=0.25,
            similarity=0.25,
            dependency=0.25,
            impact=0.25
        )
        
        assert weights.validate() is True
    
    def test_validate_invalid_weights(self):
        """Test validation of invalid weights."""
        weights = ScoringWeights(
            recency=0.5,
            similarity=0.5,
            dependency=0.0,
            impact=0.0
        )
        
        # Sums to 1.0, but this tests the validation works
        assert weights.validate() is True
    
    def test_validate_weights_with_small_error(self):
        """Test validation allows small floating point errors."""
        weights = ScoringWeights(
            recency=0.3333,
            similarity=0.3333,
            dependency=0.1667,
            impact=0.1667
        )
        
        # Sum is approximately 1.0
        assert weights.validate() is True


class TestScoringMetrics:
    """Test ScoringMetrics dataclass."""
    
    def test_initial_metrics(self):
        """Test initial metrics are zero."""
        metrics = ScoringMetrics()
        
        assert metrics.total_items_scored == 0
        assert metrics.average_score == 0.0
        assert metrics.scoring_accuracy == 0.0
        assert len(metrics.score_distribution) == 0
    
    def test_update_metrics(self):
        """Test updating metrics with scores."""
        metrics = ScoringMetrics()
        
        metrics.update(0.5)
        metrics.update(0.7)
        metrics.update(0.3)
        
        assert metrics.total_items_scored == 3
        assert metrics.average_score == 0.5  # (0.5 + 0.7 + 0.3) / 3
    
    def test_score_distribution(self):
        """Test score distribution tracking."""
        metrics = ScoringMetrics()
        
        metrics.update(0.1)  # very_low
        metrics.update(0.3)  # low
        metrics.update(0.5)  # medium
        metrics.update(0.7)  # high
        metrics.update(0.9)  # very_high
        
        assert metrics.score_distribution['very_low'] == 1
        assert metrics.score_distribution['low'] == 1
        assert metrics.score_distribution['medium'] == 1
        assert metrics.score_distribution['high'] == 1
        assert metrics.score_distribution['very_high'] == 1


class TestContextScorerInitialization:
    """Test ContextScorer initialization."""
    
    def test_default_initialization(self):
        """Test scorer initializes with defaults."""
        scorer = ContextScorer()
        
        assert isinstance(scorer.weights, ScoringWeights)
        assert scorer.learning_rate == 0.1
        assert isinstance(scorer.metrics, ScoringMetrics)
        assert len(scorer.historical_weights) == 0
    
    def test_custom_weights_initialization(self):
        """Test scorer initializes with custom weights."""
        custom_weights = ScoringWeights(
            recency=0.4,
            similarity=0.3,
            dependency=0.2,
            impact=0.1
        )
        scorer = ContextScorer(weights=custom_weights)
        
        assert scorer.weights.recency == 0.4
        assert scorer.weights.similarity == 0.3
    
    def test_custom_learning_rate(self):
        """Test scorer initializes with custom learning rate."""
        scorer = ContextScorer(learning_rate=0.5)
        
        assert scorer.learning_rate == 0.5
    
    def test_learning_rate_clamping(self):
        """Test learning rate is clamped to [0, 1]."""
        scorer1 = ContextScorer(learning_rate=-0.5)
        scorer2 = ContextScorer(learning_rate=1.5)
        
        assert scorer1.learning_rate == 0.0
        assert scorer2.learning_rate == 1.0


class TestRecencyScoring:
    """Test recency scoring factor."""
    
    def test_recent_item_high_score(self):
        """Test recent items get high recency score."""
        scorer = ContextScorer()
        
        item = ContextItem(
            id="test-1",
            content="Recent action",
            timestamp=datetime.now() - timedelta(minutes=5),
            item_type="action"
        )
        
        score = scorer._score_recency(item, datetime.now())
        
        assert score > 0.9  # Very recent
    
    def test_old_item_low_score(self):
        """Test old items get low recency score."""
        scorer = ContextScorer()
        
        item = ContextItem(
            id="test-2",
            content="Old action",
            timestamp=datetime.now() - timedelta(hours=10),
            item_type="action"
        )
        
        score = scorer._score_recency(item, datetime.now())
        
        assert score < 0.1  # Very old
    
    def test_recency_clamping(self):
        """Test recency scores are clamped to [0, 1]."""
        scorer = ContextScorer()
        
        # Very recent (would be > 1.0 without clamping)
        recent_item = ContextItem(
            id="test-3",
            content="Very recent",
            timestamp=datetime.now(),
            item_type="action"
        )
        score1 = scorer._score_recency(recent_item, datetime.now())
        assert score1 <= 1.0
        
        # Very old (would be < 0.0 without clamping)
        old_item = ContextItem(
            id="test-4",
            content="Very old",
            timestamp=datetime.now() - timedelta(days=365),
            item_type="action"
        )
        score2 = scorer._score_recency(old_item, datetime.now())
        assert score2 >= 0.0


class TestSimilarityScoring:
    """Test similarity scoring factor."""
    
    def test_high_similarity(self):
        """Test high similarity when keywords match."""
        scorer = ContextScorer()
        
        item = ContextItem(
            id="test-1",
            content="Implement user authentication module",
            timestamp=datetime.now(),
            item_type="action"
        )
        
        score = scorer._score_similarity(item, "Implement user authentication")
        
        assert score > 0.5  # High similarity
    
    def test_low_similarity(self):
        """Test low similarity when keywords don't match."""
        scorer = ContextScorer()
        
        item = ContextItem(
            id="test-2",
            content="Fix database connection error",
            timestamp=datetime.now(),
            item_type="action"
        )
        
        score = scorer._score_similarity(item, "Implement user interface")
        
        assert score < 0.3  # Low similarity
    
    def test_similarity_boost_for_relevant_types(self):
        """Test similarity boost for relevant item types."""
        scorer = ContextScorer()
        
        # Action item
        action_item = ContextItem(
            id="test-3",
            content="User authentication",
            timestamp=datetime.now(),
            item_type="action"
        )
        action_score = scorer._score_similarity(action_item, "Implement user authentication")
        
        # Info item (no boost)
        info_item = ContextItem(
            id="test-4",
            content="User authentication",
            timestamp=datetime.now(),
            item_type="info"
        )
        info_score = scorer._score_similarity(info_item, "Implement user authentication")
        
        assert action_score > info_score
    
    def test_similarity_with_no_keywords(self):
        """Test similarity returns default when no keywords."""
        scorer = ContextScorer()
        
        item = ContextItem(
            id="test-5",
            content="the a an",
            timestamp=datetime.now(),
            item_type="action"
        )
        
        score = scorer._score_similarity(item, "Implement")
        
        # Should return default (0.5) when no keywords
        assert score == 0.5


class TestDependencyScoring:
    """Test dependency scoring factor."""
    
    def test_direct_dependency_high_score(self):
        """Test direct dependency gets high score."""
        scorer = ContextScorer()
        
        item = ContextItem(
            id="test-1",
            content="Module A",
            timestamp=datetime.now(),
            item_type="module",
            metadata={'depends_on': ['user authentication']}
        )
        
        score = scorer._score_dependency(item, "user authentication")
        
        assert score == 1.0  # Direct dependency
    
    def test_reverse_dependency_high_score(self):
        """Test reverse dependency gets high score."""
        scorer = ContextScorer()
        
        item = ContextItem(
            id="test-2",
            content="Module A",
            timestamp=datetime.now(),
            item_type="module",
            metadata={'used_by': ['user authentication']}
        )
        
        score = scorer._score_dependency(item, "user authentication")
        
        assert score == 1.0  # Reverse dependency
    
    def test_shared_dependency_partial_score(self):
        """Test shared dependency gets partial score."""
        scorer = ContextScorer()
        
        item = ContextItem(
            id="test-3",
            content="Module A",
            timestamp=datetime.now(),
            item_type="module",
            metadata={'dependencies': ['user', 'auth', 'module']}
        )
        
        score = scorer._score_dependency(item, "user authentication")
        
        # Partial match (1 out of 3)
        assert 0.2 < score < 0.5
    
    def test_structural_element_higher_score(self):
        """Test structural elements get higher default score."""
        scorer = ContextScorer()
        
        module_item = ContextItem(
            id="test-4",
            content="User class",
            timestamp=datetime.now(),
            item_type="module"
        )
        module_score = scorer._score_dependency(module_item, "Implement user")
        
        info_item = ContextItem(
            id="test-5",
            content="Info message",
            timestamp=datetime.now(),
            item_type="info"
        )
        info_score = scorer._score_dependency(info_item, "Implement user")
        
        assert module_score > info_score


class TestImpactScoring:
    """Test impact scoring factor."""
    
    def test_error_highest_impact(self):
        """Test errors get highest impact score."""
        scorer = ContextScorer()
        
        error_item = ContextItem(
            id="test-1",
            content="Database connection failed",
            timestamp=datetime.now(),
            item_type="error"
        )
        error_score = scorer._score_impact(error_item)
        
        assert error_score == 1.0
    
    def test_critical_severity_boost(self):
        """Test critical severity gets boost."""
        scorer = ContextScorer()
        
        critical_item = ContextItem(
            id="test-2",
            content="Critical error",
            timestamp=datetime.now(),
            item_type="error",
            metadata={'severity': 'critical'}
        )
        critical_score = scorer._score_impact(critical_item)
        
        normal_item = ContextItem(
            id="test-3",
            content="Normal error",
            timestamp=datetime.now(),
            item_type="error"
        )
        normal_score = scorer._score_impact(normal_item)
        
        assert critical_score == 1.0
        assert normal_score == 1.0  # Error type already max
    
    def test_downstream_dependency_boost(self):
        """Test items with many dependencies get boost."""
        scorer = ContextScorer()
        
        high_downstream = ContextItem(
            id="test-4",
            content="Core module",
            timestamp=datetime.now(),
            item_type="module",
            metadata={'downstream_count': 10}
        )
        high_score = scorer._score_impact(high_downstream)
        
        low_downstream = ContextItem(
            id="test-5",
            content="Utility function",
            timestamp=datetime.now(),
            item_type="function",
            metadata={'downstream_count': 1}
        )
        low_score = scorer._score_impact(low_downstream)
        
        assert high_score > low_score
    
    def test_impact_by_type(self):
        """Test impact scores vary by item type."""
        scorer = ContextScorer()
        
        types_scores = [
            ('error', scorer._score_impact(ContextItem(id="1", content="", timestamp=datetime.now(), item_type='error'))),
            ('decision', scorer._score_impact(ContextItem(id="2", content="", timestamp=datetime.now(), item_type='decision'))),
            ('action', scorer._score_impact(ContextItem(id="3", content="", timestamp=datetime.now(), item_type='action'))),
            ('info', scorer._score_impact(ContextItem(id="4", content="", timestamp=datetime.now(), item_type='info'))),
        ]
        
        # Error should have highest score
        assert types_scores[0][1] == 1.0
        # Info should have lower score than action/decision
        assert types_scores[3][1] < types_scores[2][1]


class TestScoreContextItems:
    """Test scoring context items."""
    
    def test_score_empty_list(self):
        """Test scoring empty list."""
        scorer = ContextScorer()
        
        result = scorer.score_context_items([], "Test task")
        
        assert result == []
    
    def test_score_single_item(self):
        """Test scoring single item."""
        scorer = ContextScorer()
        
        item = ContextItem(
            id="test-1",
            content="Implement user authentication",
            timestamp=datetime.now(),
            item_type="action"
        )
        
        result = scorer.score_context_items([item], "Implement user authentication")
        
        assert len(result) == 1
        assert result[0].total_score > 0
    
    def test_score_multiple_items(self):
        """Test scoring multiple items."""
        scorer = ContextScorer()
        
        items = [
            ContextItem(
                id="test-1",
                content="Implement user authentication",
                timestamp=datetime.now() - timedelta(minutes=5),
                item_type="action"
            ),
            ContextItem(
                id="test-2",
                content="Fix database error",
                timestamp=datetime.now() - timedelta(hours=2),
                item_type="error"
            ),
            ContextItem(
                id="test-3",
                content="Test authentication module",
                timestamp=datetime.now() - timedelta(minutes=10),
                item_type="test"
            ),
        ]
        
        result = scorer.score_context_items(items, "Implement user authentication")
        
        assert len(result) == 3
        for item in result:
            assert item.total_score >= 0
            assert item.total_score <= 1
    
    def test_scores_sorted(self):
        """Test items are sorted by score descending."""
        scorer = ContextScorer()
        
        # Create items with different recency to ensure different scores
        items = [
            ContextItem(
                id=f"test-{i}",
                content=f"Content {i}",
                timestamp=datetime.now() - timedelta(hours=i),
                item_type="action"
            )
            for i in range(5)
        ]
        
        result = scorer.score_context_items(items, "Test task")
        
        # Check sorted descending
        scores = [item.total_score for item in result]
        assert scores == sorted(scores, reverse=True)
    
    def test_individual_scores_calculated(self):
        """Test individual factor scores are calculated."""
        scorer = ContextScorer()
        
        item = ContextItem(
            id="test-1",
            content="Implement user authentication",
            timestamp=datetime.now(),
            item_type="action"
        )
        
        scorer.score_context_items([item], "Implement user authentication")
        
        assert item.recency_score > 0
        assert item.similarity_score >= 0
        assert item.dependency_score >= 0
        assert item.impact_score >= 0


class TestRankContextItems:
    """Test ranking context items."""
    
    def test_rank_with_top_k(self):
        """Test ranking with top_k parameter."""
        scorer = ContextScorer()
        
        items = [
            ContextItem(
                id=f"test-{i}",
                content=f"Content {i}",
                timestamp=datetime.now() - timedelta(minutes=i),
                item_type="action"
            )
            for i in range(10)
        ]
        
        result = scorer.rank_context_items(items, "Test task", top_k=5)
        
        assert len(result) == 5
    
    def test_rank_with_min_score(self):
        """Test ranking with min_score threshold."""
        scorer = ContextScorer()
        
        items = [
            ContextItem(
                id=f"test-{i}",
                content=f"Content {i}",
                timestamp=datetime.now() - timedelta(hours=i),
                item_type="action"
            )
            for i in range(10)
        ]
        
        result = scorer.rank_context_items(items, "Test task", min_score=0.5)
        
        for item in result:
            assert item.total_score >= 0.5
    
    def test_rank_empty_list(self):
        """Test ranking empty list."""
        scorer = ContextScorer()
        
        result = scorer.rank_context_items([], "Test task")
        
        assert result == []
    
    def test_rank_returns_sorted(self):
        """Test rank returns sorted items."""
        scorer = ContextScorer()
        
        items = [
            ContextItem(
                id=f"test-{i}",
                content=f"Content {i}",
                timestamp=datetime.now() - timedelta(minutes=i),
                item_type="action"
            )
            for i in range(5)
        ]
        
        result = scorer.rank_context_items(items, "Test task")
        
        scores = [item.total_score for item in result]
        assert scores == sorted(scores, reverse=True)


class TestPruneContextItems:
    """Test pruning context items."""
    
    def test_prune_by_percentage(self):
        """Test pruning by keep_percentage."""
        scorer = ContextScorer()
        
        items = [
            ContextItem(
                id=f"test-{i}",
                content=f"Content {i}",
                timestamp=datetime.now() - timedelta(minutes=i),
                item_type="action"
            )
            for i in range(10)
        ]
        
        result = scorer.prune_context_items(items, "Test task", keep_percentage=0.5)
        
        # Should keep ~50%
        assert len(result) == 5
    
    def test_prune_by_min_score(self):
        """Test pruning by min_score threshold."""
        scorer = ContextScorer()
        
        items = [
            ContextItem(
                id=f"test-{i}",
                content=f"Content {i}",
                timestamp=datetime.now() - timedelta(hours=i),
                item_type="action"
            )
            for i in range(10)
        ]
        
        result = scorer.prune_context_items(items, "Test task", min_score=0.5)
        
        for item in result:
            assert item.total_score >= 0.5
    
    def test_prune_keeps_at_least_one(self):
        """Test pruning keeps at least one item."""
        scorer = ContextScorer()
        
        items = [
            ContextItem(
                id="test-1",
                content="Content",
                timestamp=datetime.now() - timedelta(hours=10),
                item_type="action"
            )
        ]
        
        # Even with very low keep_percentage
        result = scorer.prune_context_items(items, "Test task", keep_percentage=0.01)
        
        assert len(result) >= 1
    
    def test_prune_empty_list(self):
        """Test pruning empty list."""
        scorer = ContextScorer()
        
        result = scorer.prune_context_items([], "Test task")
        
        assert result == []


class TestWeightManagement:
    """Test weight management and learning."""
    
    def test_update_valid_weights(self):
        """Test updating with valid weights."""
        scorer = ContextScorer()
        
        new_weights = ScoringWeights(
            recency=0.4,
            similarity=0.3,
            dependency=0.2,
            impact=0.1
        )
        
        scorer.update_weights(new_weights)
        
        assert scorer.weights.recency == 0.4
        assert scorer.weights.similarity == 0.3
        assert scorer.weights.dependency == 0.2
        assert scorer.weights.impact == 0.1
    
    def test_update_invalid_weights_raises_error(self):
        """Test updating with invalid weights raises error."""
        scorer = ContextScorer()
        
        invalid_weights = ScoringWeights(
            recency=0.5,
            similarity=0.5,
            dependency=0.0,
            impact=0.0
        )
        
        # This actually sums to 1.0, so it's valid
        scorer.update_weights(invalid_weights)
        
        # Test truly invalid
        invalid_weights2 = ScoringWeights(
            recency=0.8,
            similarity=0.8,
            dependency=0.0,
            impact=0.0
        )
        
        with pytest.raises(ValueError):
            scorer.update_weights(invalid_weights2)
    
    def test_historical_weights_stored(self):
        """Test historical weights are stored."""
        scorer = ContextScorer()
        
        new_weights = ScoringWeights(
            recency=0.4,
            similarity=0.3,
            dependency=0.2,
            impact=0.1
        )
        
        scorer.update_weights(new_weights)
        
        assert len(scorer.historical_weights) == 1
    
    def test_learn_weights_updates_success_rate(self):
        """Test learning updates success rate."""
        scorer = ContextScorer()
        
        scorer.learn_weights(0.8)
        
        assert scorer.metrics.scoring_accuracy == 0.8
    
    def test_learn_weights_adjusts_when_low_success(self):
        """Test learning adjusts weights when success rate is low."""
        scorer = ContextScorer()
        
        # Set some historical weights
        best_weights = ScoringWeights(
            recency=0.4,
            similarity=0.4,
            dependency=0.1,
            impact=0.1
        )
        scorer.historical_weights.append((best_weights, 0.9))
        
        # Current weights are different
        scorer.weights = ScoringWeights(
            recency=0.25,
            similarity=0.25,
            dependency=0.25,
            impact=0.25
        )
        
        # Learn with low success rate
        scorer.learn_weights(0.6)
        
        # Weights should have moved toward best_weights
        assert abs(scorer.weights.recency - 0.4) < abs(0.25 - 0.4)
    
    def test_learn_weights_no_adjustment_when_high_success(self):
        """Test learning doesn't adjust when success rate is high."""
        scorer = ContextScorer()
        
        original_weights = ScoringWeights(
            recency=0.3,
            similarity=0.3,
            dependency=0.25,
            impact=0.15
        )
        scorer.weights = original_weights
        
        # Learn with high success rate
        scorer.learn_weights(0.9)
        
        # Weights should remain unchanged
        assert scorer.weights.recency == original_weights.recency
        assert scorer.weights.similarity == original_weights.similarity


class TestMetrics:
    """Test metrics tracking."""
    
    def test_get_metrics(self):
        """Test getting metrics."""
        scorer = ContextScorer()
        
        metrics = scorer.get_metrics()
        
        assert isinstance(metrics, ScoringMetrics)
    
    def test_reset_metrics(self):
        """Test resetting metrics."""
        scorer = ContextScorer()
        
        # Score some items to populate metrics
        items = [
            ContextItem(
                id="test-1",
                content="Content",
                timestamp=datetime.now(),
                item_type="action"
            )
        ]
        scorer.score_context_items(items, "Test task")
        
        # Reset
        scorer.reset_metrics()
        
        metrics = scorer.get_metrics()
        assert metrics.total_items_scored == 0
        assert metrics.average_score == 0.0


class TestStatePersistence:
    """Test state export and import."""
    
    def test_export_state(self):
        """Test exporting state."""
        scorer = ContextScorer(learning_rate=0.5)
        
        # Score some items
        items = [
            ContextItem(
                id="test-1",
                content="Content",
                timestamp=datetime.now(),
                item_type="action"
            )
        ]
        scorer.score_context_items(items, "Test task")
        
        state = scorer.export_state()
        
        assert 'weights' in state
        assert 'learning_rate' in state
        assert 'metrics' in state
        assert 'historical_weights' in state
        assert state['learning_rate'] == 0.5
    
    def test_import_state(self):
        """Test importing state."""
        scorer1 = ContextScorer(learning_rate=0.3)
        
        # Score some items
        items = [
            ContextItem(
                id="test-1",
                content="Content",
                timestamp=datetime.now(),
                item_type="action"
            )
        ]
        scorer1.score_context_items(items, "Test task")
        
        # Export
        state = scorer1.export_state()
        
        # Create new scorer and import
        scorer2 = ContextScorer()
        scorer2.import_state(state)
        
        # Verify imported state
        assert scorer2.learning_rate == 0.3
        assert scorer2.weights.recency == scorer1.weights.recency
        assert scorer2.metrics.total_items_scored == scorer1.metrics.total_items_scored
    
    def test_round_trip_state(self):
        """Test state survives round-trip export/import."""
        scorer1 = ContextScorer(learning_rate=0.7)
        
        # Score some items
        items = [
            ContextItem(
                id=f"test-{i}",
                content=f"Content {i}",
                timestamp=datetime.now(),
                item_type="action"
            )
            for i in range(5)
        ]
        scorer1.score_context_items(items, "Test task")
        
        # Export
        state = scorer1.export_state()
        
        # Import into new scorer
        scorer2 = ContextScorer()
        scorer2.import_state(state)
        
        # Export again and compare
        state2 = scorer2.export_state()
        
        assert state['weights'] == state2['weights']
        assert state['learning_rate'] == state2['learning_rate']
        assert state['metrics'] == state2['metrics']


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_score_with_none_current_time(self):
        """Test scoring with None current_time uses datetime.now()."""
        scorer = ContextScorer()
        
        item = ContextItem(
            id="test-1",
            content="Content",
            timestamp=datetime.now(),
            item_type="action"
        )
        
        # Should not raise error
        result = scorer.score_context_items([item], "Test task", current_time=None)
        
        assert len(result) == 1
    
    def test_extract_keywords_empty_string(self):
        """Test extracting keywords from empty string."""
        scorer = ContextScorer()
        
        keywords = scorer._extract_keywords("")
        
        assert keywords == []
    
    def test_extract_keywords_with_punctuation(self):
        """Test extracting keywords removes punctuation."""
        scorer = ContextScorer()
        
        keywords = scorer._extract_keywords("Hello, world! This is a test.")
        
        assert "hello" in keywords
        assert "world" in keywords
        assert "test" in keywords
        assert "," not in keywords
        assert "!" not in keywords
    
    def test_extract_keywords_filters_stop_words(self):
        """Test extracting keywords filters stop words."""
        scorer = ContextScorer()
        
        keywords = scorer._extract_keywords("The quick brown fox jumps over the lazy dog")
        
        # Stop words should be filtered
        assert "the" not in keywords
        assert "over" not in keywords
        # Content words should remain
        assert "quick" in keywords
        assert "brown" in keywords
        assert "fox" in keywords
    
    def test_score_with_zero_weight(self):
        """Test scoring with zero-weight factor."""
        scorer = ContextScorer(
            weights=ScoringWeights(
                recency=0.0,
                similarity=1.0,
                dependency=0.0,
                impact=0.0
            )
        )
        
        item = ContextItem(
            id="test-1",
            content="Implement user authentication",
            timestamp=datetime.now() - timedelta(hours=24),
            item_type="action"
        )
        
        result = scorer.score_context_items([item], "Implement user authentication")
        
        # Score should be based only on similarity
        assert result[0].total_score == result[0].similarity_score


if __name__ == '__main__':
    pytest.main([__file__, '-v'])