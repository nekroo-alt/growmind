import os
import tempfile
import time
from pathlib import Path
import pytest

from v1.data.cache_manager import CacheManager, get_cache_manager


class TestCacheManager:
    """Test suite for CacheManager functionality."""
    
    def test_cache_initialization(self):
        """Test that CacheManager initializes correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir)
            manager = CacheManager(str(cache_dir))
            
            assert manager.cache_dir == cache_dir
            assert manager.max_cache_size == 100
            assert len(manager.cache_index) == 0
            # cache_index_file is created on first save, not initialization
            assert manager.cache_dir.exists()
    
    def test_cache_and_retrieve(self):
        """Test basic cache storage and retrieval."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = CacheManager(tmpdir)
            
            # Create a test file
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("def hello():\n    print('world')\n")
            
            # Cache some data
            test_data = {"summary": {"functions": [{"name": "hello"}]}}
            result = manager.set(str(test_file), "semantic_map", test_data)
            assert result is True
            
            # Retrieve cached data
            cached = manager.get(str(test_file), "semantic_map")
            assert cached is not None
            assert cached["summary"] == test_data["summary"]
            assert cached.get("_cache_hit") is True
    
    def test_cache_miss(self):
        """Test cache miss when data doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = CacheManager(tmpdir)
            
            # Create a test file
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("def hello():\n    pass\n")
            
            # Try to get non-existent cache
            cached = manager.get(str(test_file), "nonexistent")
            assert cached is None
    
    def test_cache_invalidation_on_file_change(self):
        """Test that cache is invalidated when file is modified."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = CacheManager(tmpdir)
            
            # Create a test file
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("def hello():\n    pass\n")
            
            # Cache data
            test_data = {"version": 1}
            manager.set(str(test_file), "semantic_map", test_data)
            
            # Verify cache hit
            cached = manager.get(str(test_file), "semantic_map")
            assert cached is not None
            assert cached["version"] == 1
            
            # Modify the file
            time.sleep(0.01)  # Ensure different modification time
            test_file.write_text("def hello():\n    print('modified')\n")
            
            # Cache should be invalidated
            cached = manager.get(str(test_file), "semantic_map")
            assert cached is None
    
    def test_invalidate_method(self):
        """Test explicit cache invalidation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = CacheManager(tmpdir)
            
            # Create a test file
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("def hello():\n    pass\n")
            
            # Cache multiple analysis types
            manager.set(str(test_file), "semantic_map", {"type": "map"})
            manager.set(str(test_file), "call_graph", {"type": "graph"})
            
            # Verify both are cached
            assert manager.get(str(test_file), "semantic_map") is not None
            assert manager.get(str(test_file), "call_graph") is not None
            
            # Invalidate all cache for this file
            manager.invalidate(str(test_file))
            
            # Both should be gone
            assert manager.get(str(test_file), "semantic_map") is None
            assert manager.get(str(test_file), "call_graph") is None
    
    def test_lru_eviction(self):
        """Test LRU eviction when cache is full."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create manager with small cache size
            manager = CacheManager(tmpdir, max_cache_size=3)
            
            # Create test files
            for i in range(5):
                test_file = Path(tmpdir) / f"test{i}.py"
                test_file.write_text(f"def func{i}():\n    pass\n")
                manager.set(str(test_file), "semantic_map", {"id": i})
            
            # Cache should only hold the 3 most recent entries
            assert len(manager.cache_index) == 3
            
            # Oldest entries should be evicted
            assert manager.get(str(Path(tmpdir) / "test0.py"), "semantic_map") is None
            assert manager.get(str(Path(tmpdir) / "test1.py"), "semantic_map") is None
            
            # Newest entries should still be there
            assert manager.get(str(Path(tmpdir) / "test2.py"), "semantic_map") is not None
            assert manager.get(str(Path(tmpdir) / "test3.py"), "semantic_map") is not None
            assert manager.get(str(Path(tmpdir) / "test4.py"), "semantic_map") is not None
    
    def test_cache_statistics(self):
        """Test cache statistics reporting."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = CacheManager(tmpdir)
            
            # Create test files
            for i in range(3):
                test_file = Path(tmpdir) / f"test{i}.py"
                test_file.write_text(f"def func{i}():\n    pass\n")
                manager.set(str(test_file), "semantic_map", {"id": i})
            
            stats = manager.get_stats()
            
            assert stats['total_entries'] == 3
            assert stats['valid_entries'] == 3
            assert stats['max_size'] == 100
            assert stats['total_size_bytes'] > 0
            assert stats['total_size_mb'] > 0
    
    def test_clear_all(self):
        """Test clearing all cached data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = CacheManager(tmpdir)
            
            # Create and cache multiple files
            for i in range(3):
                test_file = Path(tmpdir) / f"test{i}.py"
                test_file.write_text(f"def func{i}():\n    pass\n")
                manager.set(str(test_file), "semantic_map", {"id": i})
            
            # Clear all
            manager.clear_all()
            
            # Verify all cache is gone
            assert len(manager.cache_index) == 0
            for i in range(3):
                test_file = Path(tmpdir) / f"test{i}.py"
                assert manager.get(str(test_file), "semantic_map") is None
    
    def test_cleanup_stale(self):
        """Test cleanup of stale cache entries."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = CacheManager(tmpdir)
            
            # Create test files
            test_file1 = Path(tmpdir) / "test1.py"
            test_file2 = Path(tmpdir) / "test2.py"
            test_file1.write_text("def func1():\n    pass\n")
            test_file2.write_text("def func2():\n    pass\n")
            
            # Cache both
            manager.set(str(test_file1), "semantic_map", {"id": 1})
            manager.set(str(test_file2), "semantic_map", {"id": 2})
            
            # Modify one file to make its cache stale
            time.sleep(0.01)
            test_file2.write_text("def func2():\n    print('modified')\n")
            
            # Cleanup stale
            removed = manager.cleanup_stale()
            
            # One entry should be removed
            assert removed == 1
            
            # First file should still be cached
            assert manager.get(str(test_file1), "semantic_map") is not None
            # Second file's cache should be gone
            assert manager.get(str(test_file2), "semantic_map") is None
    
    def test_singleton_pattern(self):
        """Test that get_cache_manager returns the same instance."""
        manager1 = get_cache_manager()
        manager2 = get_cache_manager()
        
        assert manager1 is manager2
    
    def test_nonexistent_file(self):
        """Test handling of non-existent files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = CacheManager(tmpdir)
            
            # Try to cache non-existent file
            result = manager.set("nonexistent.py", "semantic_map", {"data": "test"})
            assert result is False
            
            # Try to get cache for non-existent file
            cached = manager.get("nonexistent.py", "semantic_map")
            assert cached is None
    
    def test_different_analysis_types(self):
        """Test caching different analysis types for the same file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = CacheManager(tmpdir)
            
            # Create a test file
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("def hello():\n    pass\n")
            
            # Cache different analysis types
            manager.set(str(test_file), "semantic_map", {"type": "map"})
            manager.set(str(test_file), "call_graph", {"type": "graph"})
            manager.set(str(test_file), "data_flow", {"type": "flow"})
            
            # Each should be retrievable independently
            assert manager.get(str(test_file), "semantic_map")["type"] == "map"
            assert manager.get(str(test_file), "call_graph")["type"] == "graph"
            assert manager.get(str(test_file), "data_flow")["type"] == "flow"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
