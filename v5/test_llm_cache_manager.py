"""
Unit tests for LLM Cache Manager - V5 Cost Optimization
"""

import os
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from v4.data.llm_cache_manager import (
    LLMPromptHash,
    LLMMatchResult,
    LLMLLMCacheManager,
    get_cache_manager
)


class TestLLMPromptHash(unittest.TestCase):
    """Test cases for prompt hash generation."""
    
    def test_generate_hash(self):
        """Test hash generation with different inputs."""
        hash1 = LLMPromptHash.generate_hash("test prompt", "gpt-4", 0.7)
        hash2 = LLMPromptHash.generate_hash("test prompt", "gpt-4", 0.7)
        hash3 = LLMPromptHash.generate_hash("test prompt", "gpt-3.5", 0.7)
        
        # Same inputs should produce same hash
        self.assertEqual(hash1, hash2)
        
        # Different inputs should produce different hashes
        self.assertNotEqual(hash1, hash3)
        
        # Hash should be consistent
        self.assertEqual(len(hash1), 64)  # SHA256 produces 64 hex chars
    
    def test_generate_hash_normalizes_whitespace(self):
        """Test that hash generation normalizes whitespace."""
        hash1 = LLMPromptHash.generate_hash("test  prompt", "gpt-4", 0.7)
        hash2 = LLMPromptHash.generate_hash("test prompt", "gpt-4", 0.7)
        hash3 = LLMPromptHash.generate_hash("test   prompt", "gpt-4", 0.7)
        
        # All should produce same hash (whitespace normalized)
        self.assertEqual(hash1, hash2)
        self.assertEqual(hash2, hash3)


class TestLLMCacheManager(unittest.TestCase):
    """Test cases for LLM cache manager."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create temporary database for testing
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_cache.db")
        self.cache_manager = LLMLLMCacheManager(
            db_path=self.db_path,
            default_ttl_hours=1  # 1 hour TTL for tests
        )
    
    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        os.rmdir(self.temp_dir)
    
    def test_cache_and_retrieve_response(self):
        """Test caching and retrieving responses."""
        prompt = "Write a Python function to add two numbers"
        response = "def add(a, b): return a + b"
        model = "gpt-4"
        temperature = 0.7
        
        # Cache the response
        self.cache_manager.cache_response(
            prompt=prompt,
            response=response,
            model=model,
            temperature=temperature
        )
        
        # Retrieve the cached response
        cached = self.cache_manager.get_cached_response(
            prompt=prompt,
            model=model,
            temperature=temperature
        )
        
        self.assertIsNotNone(cached)
        self.assertEqual(cached['response'], response)
        self.assertEqual(cached['hit_count'], 1)
    
    def test_cache_miss_returns_none(self):
        """Test that cache miss returns None."""
        cached = self.cache_manager.get_cached_response(
            prompt="non-existent prompt",
            model="gpt-4",
            temperature=0.7
        )
        
        self.assertIsNone(cached)
    
    def test_cache_different_model(self):
        """Test that different models produce different cache entries."""
        prompt = "test prompt"
        response1 = "response for gpt-4"
        response2 = "response for gpt-3.5"
        
        # Cache for gpt-4
        self.cache_manager.cache_response(
            prompt=prompt,
            response=response1,
            model="gpt-4",
            temperature=0.7
        )
        
        # Cache for gpt-3.5
        self.cache_manager.cache_response(
            prompt=prompt,
            response=response2,
            model="gpt-3.5",
            temperature=0.7
        )
        
        # Retrieve for gpt-4
        cached1 = self.cache_manager.get_cached_response(
            prompt=prompt,
            model="gpt-4",
            temperature=0.7
        )
        
        # Retrieve for gpt-3.5
        cached2 = self.cache_manager.get_cached_response(
            prompt=prompt,
            model="gpt-3.5",
            temperature=0.7
        )
        
        self.assertEqual(cached1['response'], response1)
        self.assertEqual(cached2['response'], response2)
    
    def test_cache_different_temperature(self):
        """Test that different temperatures produce different cache entries."""
        prompt = "test prompt"
        response1 = "response at 0.7"
        response2 = "response at 0.5"
        
        # Cache at temperature 0.7
        self.cache_manager.cache_response(
            prompt=prompt,
            response=response1,
            model="gpt-4",
            temperature=0.7
        )
        
        # Cache at temperature 0.5
        self.cache_manager.cache_response(
            prompt=prompt,
            response=response2,
            model="gpt-4",
            temperature=0.5
        )
        
        # Retrieve at temperature 0.7
        cached1 = self.cache_manager.get_cached_response(
            prompt=prompt,
            model="gpt-4",
            temperature=0.7
        )
        
        # Retrieve at temperature 0.5
        cached2 = self.cache_manager.get_cached_response(
            prompt=prompt,
            model="gpt-4",
            temperature=0.5
        )
        
        self.assertEqual(cached1['response'], response1)
        self.assertEqual(cached2['response'], response2)
    
    def test_cache_hit_increments_count(self):
        """Test that cache hits increment hit count."""
        prompt = "test prompt"
        response = "test response"
        
        # Cache the response
        self.cache_manager.cache_response(
            prompt=prompt,
            response=response,
            model="gpt-4",
            temperature=0.7
        )
        
        # Hit the cache multiple times
        for i in range(3):
            cached = self.cache_manager.get_cached_response(
                prompt=prompt,
                model="gpt-4",
                temperature=0.7
            )
            self.assertEqual(cached['hit_count'], i + 1)
    
    def test_cache_replace_existing(self):
        """Test that caching replaces existing entry."""
        prompt = "test prompt"
        response1 = "response 1"
        response2 = "response 2"
        
        # Cache first response
        self.cache_manager.cache_response(
            prompt=prompt,
            response=response1,
            model="gpt-4",
            temperature=0.7
        )
        
        # Cache second response (should replace)
        self.cache_manager.cache_response(
            prompt=prompt,
            response=response2,
            model="gpt-4",
            temperature=0.7
        )
        
        # Retrieve should get second response
        cached = self.cache_manager.get_cached_response(
            prompt=prompt,
            model="gpt-4",
            temperature=0.7
        )
        
        self.assertEqual(cached['response'], response2)
    
    def test_invalidate_for_files(self):
        """Test cache invalidation for specific files."""
        prompt = "Consider the file v4/core/config.py"
        response = "test response"
        
        # Cache the response
        self.cache_manager.cache_response(
            prompt=prompt,
            response=response,
            model="gpt-4",
            temperature=0.7
        )
        
        # Verify cache has entry
        cached = self.cache_manager.get_cached_response(
            prompt=prompt,
            model="gpt-4",
            temperature=0.7
        )
        self.assertIsNotNone(cached)
        
        # Invalidate for file
        self.cache_manager.invalidate_for_files(["v4/core/config.py"])
        
        # Verify cache is cleared
        cached = self.cache_manager.get_cached_response(
            prompt=prompt,
            model="gpt-4",
            temperature=0.7
        )
        self.assertIsNone(cached)
    
    def test_invalidate_expired(self):
        """Test invalidation of expired entries."""
        prompt = "test prompt"
        response = "test response"
        
        # Cache with very short TTL (negative to ensure immediate expiration)
        self.cache_manager.cache_response(
            prompt=prompt,
            response=response,
            model="gpt-4",
            temperature=0.7,
            ttl_hours=-1  # Expired in the past
        )
        
        # Wait a moment to ensure time passes
        import time
        time.sleep(0.1)
        
        # Run invalidation
        deleted = self.cache_manager.invalidate_expired()
        
        # Should have deleted at least one entry
        self.assertGreater(deleted, 0)
        
        # Verify cache is cleared
        cached = self.cache_manager.get_cached_response(
            prompt=prompt,
            model="gpt-4",
            temperature=0.7
        )
        self.assertIsNone(cached)
    
    def test_get_stats(self):
        """Test statistics tracking."""
        # Generate some cache hits and misses
        prompt1 = "prompt 1"
        response1 = "response 1"
        
        # Cache first prompt
        self.cache_manager.cache_response(
            prompt=prompt1,
            response=response1,
            model="gpt-4",
            temperature=0.7
        )
        
        # Hit the cache twice
        self.cache_manager.get_cached_response(prompt1, "gpt-4", 0.7)
        self.cache_manager.get_cached_response(prompt1, "gpt-4", 0.7)
        
        # Generate a miss
        self.cache_manager.get_cached_response("non-existent", "gpt-4", 0.7)
        
        # Get statistics
        stats = self.cache_manager.get_stats(days=1)
        
        # Verify statistics
        self.assertEqual(stats['total_hits'], 2)
        self.assertEqual(stats['total_misses'], 1)
        self.assertEqual(stats['total_requests'], 3)
        # Calculate expected hit rate from hits/requests
        expected_hit_rate = stats['total_hits'] / stats['total_requests'] if stats['total_requests'] > 0 else 0.0
        self.assertAlmostEqual(stats['hit_rate'], expected_hit_rate, places=2)
        self.assertEqual(stats['cache_size'], 1)
    
    def test_clear_all(self):
        """Test clearing all cache entries."""
        # Cache multiple entries
        for i in range(5):
            self.cache_manager.cache_response(
                prompt=f"prompt {i}",
                response=f"response {i}",
                model="gpt-4",
                temperature=0.7
            )
        
        # Verify cache has entries
        stats = self.cache_manager.get_stats()
        self.assertEqual(stats['cache_size'], 5)
        
        # Clear all
        self.cache_manager.clear_all()
        
        # Verify cache is empty
        stats = self.cache_manager.get_stats()
        self.assertEqual(stats['cache_size'], 0)
    
    def test_get_cache_size_mb(self):
        """Test getting cache database size."""
        # Cache some entries
        for i in range(10):
            self.cache_manager.cache_response(
                prompt=f"prompt {i}",
                response=f"response {i}" * 100,  # Make responses larger
                model="gpt-4",
                temperature=0.7
            )
        
        # Get size
        size_mb = self.cache_manager.get_cache_size_mb()
        
        # Should be non-zero
        self.assertGreater(size_mb, 0)
        self.assertLess(size_mb, 1)  # Should be less than 1MB for this test
    
    def test_get_daily_stats(self):
        """Test daily statistics breakdown."""
        # Cache and hit some entries
        prompt = "test prompt"
        response = "test response"
        
        self.cache_manager.cache_response(prompt, response, "gpt-4", 0.7)
        self.cache_manager.get_cached_response(prompt, "gpt-4", 0.7)
        self.cache_manager.get_cached_response("miss", "gpt-4", 0.7)
        
        # Get daily stats
        daily_stats = self.cache_manager.get_daily_stats(days=1)
        
        # Should have at least one day of stats
        self.assertGreater(len(daily_stats), 0)
        
        # Verify stats structure
        first_day = daily_stats[0]
        self.assertIn('stat_date', first_day)
        self.assertIn('hits', first_day)
        self.assertIn('misses', first_day)
        self.assertIn('requests', first_day)
        self.assertIn('hit_rate', first_day)
    
    def test_find_similar_response_placeholder(self):
        """Test that semantic matching returns placeholder result."""
        result = self.cache_manager.find_similar_response(
            prompt="test prompt",
            model="gpt-4",
            temperature=0.7
        )
        
        # Should return match result indicating not implemented
        self.assertIsInstance(result, LLMMatchResult)
        self.assertFalse(result.is_match)
        self.assertIn("not yet implemented", result.reason)


class TestGetCacheManager(unittest.TestCase):
    """Test cases for singleton cache manager."""
    
    def test_singleton_returns_same_instance(self):
        """Test that get_cache_manager returns same instance."""
        # Create temporary database for testing
        temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(temp_dir, "test_singleton.db")
        
        try:
            # Get instance twice
            manager1 = get_cache_manager(db_path)
            manager2 = get_cache_manager(db_path)
            
            # Should be the same instance
            self.assertIs(manager1, manager2)
        finally:
            if os.path.exists(db_path):
                os.remove(db_path)
            os.rmdir(temp_dir)


if __name__ == '__main__':
    unittest.main()