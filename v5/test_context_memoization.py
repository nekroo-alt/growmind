"""
Test suite for Context Memoization (Task 4.2)
Tests context caching, reuse, fuzzy matching, and incremental updates.
"""

import os
import tempfile
import shutil
from v5.logic import ContextEngine


def test_context_caching():
    """Test that context is cached and reused on subsequent calls."""
    # Create temporary test directory
    temp_dir = tempfile.mkdtemp()

    try:
        # Create a test Python file
        test_file = os.path.join(temp_dir, "test_module.py")
        with open(test_file, "w") as f:
            f.write(
                """
class Calculator:
    def add(self, a, b):
        return a + b
    
    def subtract(self, a, b):
        return a - b

def helper_function(x):
    return x * 2
"""
            )

        # Initialize ContextEngine
        engine = ContextEngine(workspace_root=temp_dir)

        # First call - should be cache miss
        context1 = engine.get_pruned_context(
            task_query="Calculator add method",
            files=["test_module.py"],
            use_smart_scoping=False,
            task_title="Add functionality",
        )

        stats1 = engine.get_cache_stats()
        assert stats1["cache_misses"] == 1, "First call should be a cache miss"
        assert stats1["cache_hits"] == 0, "First call should not be a cache hit"

        # Second call with same parameters - should be cache hit
        context2 = engine.get_pruned_context(
            task_query="Calculator add method",
            files=["test_module.py"],
            use_smart_scoping=False,
            task_title="Add functionality",
        )

        stats2 = engine.get_cache_stats()
        assert stats2["cache_hits"] == 1, "Second call should be a cache hit"
        assert stats2["cache_misses"] == 1, "Cache misses should not increase"
        assert context1 == context2, "Cached context should be identical"

        print("✓ Test context caching passed")

    finally:
        shutil.rmtree(temp_dir)


def test_fuzzy_matching():
    """Test fuzzy matching for similar tasks."""
    temp_dir = tempfile.mkdtemp()

    try:
        # Create test file
        test_file = os.path.join(temp_dir, "data_processor.py")
        with open(test_file, "w") as f:
            f.write(
                """
class DataProcessor:
    def process_data(self, data):
        return data.strip()
    
    def transform_data(self, data):
        return data.upper()
"""
            )

        engine = ContextEngine(workspace_root=temp_dir)

        # Cache context for one task
        engine.get_pruned_context(
            task_query="DataProcessor process",
            files=["data_processor.py"],
            use_smart_scoping=False,
            task_title="Process data functionality",
        )

        # Find similar task
        similar = engine.get_similar_cached_context(
            task_query="DataProcessor transform",
            task_title="Transform data feature",
            similarity_threshold=0.3,  # Lower threshold for testing
        )

        assert similar is not None, "Should find similar cached context"
        assert similar["similarity"] > 0, "Similarity should be positive"
        assert "data" in similar["shared_keywords"], "Should share 'data' keyword"

        print(f"✓ Test fuzzy matching passed (similarity: {similar['similarity']:.2f})")

    finally:
        shutil.rmtree(temp_dir)


def test_cache_invalidation():
    """Test that cache entries are invalidated when files change."""
    temp_dir = tempfile.mkdtemp()

    try:
        # Create test file
        test_file = os.path.join(temp_dir, "cache_test.py")
        with open(test_file, "w") as f:
            f.write("def original_function(): pass\n")

        engine = ContextEngine(workspace_root=temp_dir)

        # Generate and cache context
        engine.get_pruned_context(
            task_query="original function",
            files=["cache_test.py"],
            use_smart_scoping=False,
            task_title="Original task",
        )

        stats_before = engine.get_cache_stats()
        assert stats_before["cache_entries"] == 1, "Should have one cache entry"

        # Invalidate cache for the file
        invalidated = engine.invalidate_cache_for_files(["cache_test.py"])
        assert invalidated == 1, "Should invalidate one cache entry"

        stats_after = engine.get_cache_stats()
        assert (
            stats_after["cache_entries"] == 0
        ), "Cache should be empty after invalidation"

        print("✓ Test cache invalidation passed")

    finally:
        shutil.rmtree(temp_dir)


def test_incremental_update():
    """Test incremental context updates after file modifications."""
    temp_dir = tempfile.mkdtemp()

    try:
        # Create test file
        test_file = os.path.join(temp_dir, "updater_test.py")
        with open(test_file, "w") as f:
            f.write(
                """
class Updater:
    def update(self, value):
        return value + 1
"""
            )

        engine = ContextEngine(workspace_root=temp_dir)

        # Generate and cache context
        engine.get_pruned_context(
            task_query="Updater update method",
            files=["updater_test.py"],
            use_smart_scoping=False,
            task_title="Update method task",
        )

        stats_before = engine.get_cache_stats()
        cache_updates_before = stats_before["cache_updates"]

        # Modify the file
        with open(test_file, "w") as f:
            f.write(
                """
class Updater:
    def update(self, value):
        return value + 1
    
    def decrement(self, value):
        return value - 1
"""
            )

        # Trigger incremental update
        engine.update_context_incrementally(
            modified_files=["updater_test.py"], task_title="Update method task"
        )

        stats_after = engine.get_cache_stats()
        assert (
            stats_after["cache_updates"] == cache_updates_before + 1
        ), "Should have one more cache update"

        print("✓ Test incremental update passed")

    finally:
        shutil.rmtree(temp_dir)


def test_cache_key_generation():
    """Test that different parameters generate different cache keys."""
    engine = ContextEngine()

    key1 = engine._generate_cache_key(
        "query1", ["file1.py"], True, "title1", "criteria1"
    )

    key2 = engine._generate_cache_key(
        "query2", ["file1.py"], True, "title1", "criteria1"
    )

    key3 = engine._generate_cache_key(
        "query1", ["file2.py"], True, "title1", "criteria1"
    )

    key4 = engine._generate_cache_key(
        "query1", ["file1.py"], False, "title1", "criteria1"
    )

    # Same parameters should generate same key
    key1_duplicate = engine._generate_cache_key(
        "query1", ["file1.py"], True, "title1", "criteria1"
    )

    assert key1 == key1_duplicate, "Same parameters should generate same key"
    assert key1 != key2, "Different query should generate different key"
    assert key1 != key3, "Different files should generate different key"
    assert key1 != key4, "Different scoping should generate different key"

    print("✓ Test cache key generation passed")


def test_cache_stats():
    """Test cache statistics tracking."""
    engine = ContextEngine()

    # Initial stats
    stats = engine.get_cache_stats()
    assert stats["cache_hits"] == 0
    assert stats["cache_misses"] == 0
    assert stats["cache_updates"] == 0
    assert stats["cache_entries"] == 0
    assert stats["hit_rate"] == 0.0

    # Manually increment to test calculations
    engine._cache_hits = 3
    engine._cache_misses = 2
    stats = engine.get_cache_stats()

    assert stats["cache_hits"] == 3
    assert stats["cache_misses"] == 2
    assert stats["total_requests"] == 5
    assert stats["hit_rate"] == 0.6  # 3/5 = 0.6

    print("✓ Test cache stats passed")


def test_clear_cache():
    """Test cache clearing functionality."""
    temp_dir = tempfile.mkdtemp()

    try:
        # Create test file
        test_file = os.path.join(temp_dir, "clear_test.py")
        with open(test_file, "w") as f:
            f.write("def test(): pass\n")

        engine = ContextEngine(workspace_root=temp_dir)

        # Generate some cache entries
        engine.get_pruned_context(
            task_query="test",
            files=["clear_test.py"],
            use_smart_scoping=False,
            task_title="Test task",
        )

        engine._cache_hits = 5
        engine._cache_misses = 3
        engine._cache_updates = 2

        # Clear cache
        engine.clear_cache()

        stats = engine.get_cache_stats()
        assert stats["cache_entries"] == 0, "Cache should be empty"
        assert stats["cache_hits"] == 0, "Hits should be reset"
        assert stats["cache_misses"] == 0, "Misses should be reset"
        assert stats["cache_updates"] == 0, "Updates should be reset"

        print("✓ Test clear cache passed")

    finally:
        shutil.rmtree(temp_dir)


def test_force_refresh():
    """Test that force_refresh bypasses cache."""
    temp_dir = tempfile.mkdtemp()

    try:
        # Create test file
        test_file = os.path.join(temp_dir, "refresh_test.py")
        with open(test_file, "w") as f:
            f.write("def refreshable(): pass\n")

        engine = ContextEngine(workspace_root=temp_dir)

        # First call
        context1 = engine.get_pruned_context(
            task_query="refreshable",
            files=["refresh_test.py"],
            use_smart_scoping=False,
            task_title="Refresh test",
        )

        stats = engine.get_cache_stats()
        assert stats["cache_misses"] == 1

        # Second call with force_refresh=True
        context2 = engine.get_pruned_context(
            task_query="refreshable",
            files=["refresh_test.py"],
            use_smart_scoping=False,
            task_title="Refresh test",
            force_refresh=True,
        )

        stats = engine.get_cache_stats()
        assert stats["cache_misses"] == 2, "Force refresh should cause another miss"
        assert stats["cache_hits"] == 0, "Force refresh should bypass cache"

        print("✓ Test force refresh passed")

    finally:
        shutil.rmtree(temp_dir)


def run_all_tests():
    """Run all context memoization tests."""
    print("\n" + "=" * 60)
    print("Testing Context Memoization (Task 4.2)")
    print("=" * 60 + "\n")

    test_context_caching()
    test_fuzzy_matching()
    test_cache_invalidation()
    test_incremental_update()
    test_cache_key_generation()
    test_cache_stats()
    test_clear_cache()
    test_force_refresh()

    print("\n" + "=" * 60)
    print("All context memoization tests passed! ✓")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    run_all_tests()
