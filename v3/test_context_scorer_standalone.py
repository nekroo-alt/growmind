"""
Standalone test for ContextScorer to bypass import issues.
"""
import importlib.util
import sys
from datetime import datetime, timedelta

# Import context_scorer directly
spec = importlib.util.spec_from_file_location('context_scorer', 'v3/logic/context_scorer.py')
context_scorer_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(context_scorer_module)

ContextScorer = context_scorer_module.ContextScorer
ContextItem = context_scorer_module.ContextItem
ScoringWeights = context_scorer_module.ScoringWeights


def test_basic_functionality():
    """Test basic functionality of ContextScorer."""
    print("Testing basic functionality...")
    
    # Create scorer
    scorer = ContextScorer()
    
    # Create test items
    items = [
        ContextItem(
            id="test-1",
            content="Implement user authentication module",
            timestamp=datetime.now() - timedelta(minutes=5),
            item_type="action"
        ),
        ContextItem(
            id="test-2",
            content="Fix database connection error",
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
    
    # Score items
    result = scorer.score_context_items(items, "Implement user authentication")
    
    # Verify results
    assert len(result) == 3
    for item in result:
        assert item.total_score >= 0
        assert item.total_score <= 1
        assert item.recency_score >= 0
        assert item.similarity_score >= 0
        assert item.dependency_score >= 0
        assert item.impact_score >= 0
    
    # Verify sorted descending
    scores = [item.total_score for item in result]
    assert scores == sorted(scores, reverse=True)
    
    print("✓ Basic functionality test passed")


def test_ranking():
    """Test ranking functionality."""
    print("Testing ranking...")
    
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
    
    # Test top_k
    result = scorer.rank_context_items(items, "Test task", top_k=5)
    assert len(result) == 5
    
    # Test min_score
    result2 = scorer.rank_context_items(items, "Test task", min_score=0.0)
    assert len(result2) >= 5
    
    print("✓ Ranking test passed")


def test_pruning():
    """Test pruning functionality."""
    print("Testing pruning...")
    
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
    
    # Test keep_percentage
    result = scorer.prune_context_items(items, "Test task", keep_percentage=0.5)
    assert len(result) == 5
    
    # Test min_score
    result2 = scorer.prune_context_items(items, "Test task", min_score=0.5)
    for item in result2:
        assert item.total_score >= 0.5
    
    print("✓ Pruning test passed")


def test_weight_management():
    """Test weight management."""
    print("Testing weight management...")
    
    scorer = ContextScorer()
    
    # Test custom weights
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
    
    # Test learning
    scorer.learn_weights(0.8)
    assert scorer.metrics.scoring_accuracy == 0.8
    
    print("✓ Weight management test passed")


def test_scoring_factors():
    """Test individual scoring factors."""
    print("Testing scoring factors...")
    
    scorer = ContextScorer()
    
    # Test recency
    recent_item = ContextItem(
        id="recent",
        content="Recent action",
        timestamp=datetime.now() - timedelta(minutes=5),
        item_type="action"
    )
    old_item = ContextItem(
        id="old",
        content="Old action",
        timestamp=datetime.now() - timedelta(hours=10),
        item_type="action"
    )
    
    recent_score = scorer._score_recency(recent_item, datetime.now())
    old_score = scorer._score_recency(old_item, datetime.now())
    
    assert recent_score > old_score
    
    # Test similarity
    similar_item = ContextItem(
        id="similar",
        content="Implement user authentication module",
        timestamp=datetime.now(),
        item_type="action"
    )
    similar_score = scorer._score_similarity(similar_item, "Implement user authentication")
    
    dissimilar_item = ContextItem(
        id="dissimilar",
        content="Fix database error",
        timestamp=datetime.now(),
        item_type="action"
    )
    dissimilar_score = scorer._score_similarity(dissimilar_item, "Implement user interface")
    
    assert similar_score > dissimilar_score
    
    # Test impact
    error_item = ContextItem(
        id="error",
        content="Database connection failed",
        timestamp=datetime.now(),
        item_type="error"
    )
    error_score = scorer._score_impact(error_item)
    
    info_item = ContextItem(
        id="info",
        content="Info message",
        timestamp=datetime.now(),
        item_type="info"
    )
    info_score = scorer._score_impact(info_item)
    
    assert error_score > info_score
    
    print("✓ Scoring factors test passed")


def test_state_persistence():
    """Test state export and import."""
    print("Testing state persistence...")
    
    scorer1 = ContextScorer(learning_rate=0.5)
    
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
    
    # Export state
    state = scorer1.export_state()
    
    # Import into new scorer
    scorer2 = ContextScorer()
    scorer2.import_state(state)
    
    # Verify imported state
    assert scorer2.learning_rate == 0.5
    assert scorer2.metrics.total_items_scored == 5
    assert scorer2.weights.recency == scorer1.weights.recency
    
    print("✓ State persistence test passed")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Running ContextScorer standalone tests")
    print("=" * 60)
    print()
    
    try:
        test_basic_functionality()
        test_ranking()
        test_pruning()
        test_weight_management()
        test_scoring_factors()
        test_state_persistence()
        
        print()
        print("=" * 60)
        print("✓ All tests passed!")
        print("=" * 60)
        return 0
    except AssertionError as e:
        print()
        print("=" * 60)
        print(f"✗ Test failed: {e}")
        print("=" * 60)
        return 1
    except Exception as e:
        print()
        print("=" * 60)
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        print("=" * 60)
        return 1


if __name__ == '__main__':
    sys.exit(main())