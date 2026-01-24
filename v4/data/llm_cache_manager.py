"""
LLM Cache Manager - V5 Cost Optimization

This module implements intelligent caching of LLM responses to reduce API costs.
Features:
- Response caching based on prompt hash
- TTL support for cache expiration
- Semantic similarity matching (optional, using embeddings)
- Cache hit/miss rate tracking
- Context-based cache invalidation
- Cache statistics export
"""

import hashlib
import json
import sqlite3
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class LLMPromptHash:
    """Generate consistent hashes for LLM prompts."""
    
    @staticmethod
    def generate_hash(prompt: str, model: str, temperature: float) -> str:
        """
        Generate a unique hash for a prompt combination.
        
        Args:
            prompt: The prompt text
            model: The model name
            temperature: The temperature parameter
            
        Returns:
            A SHA256 hash string
        """
        # Normalize prompt (remove extra whitespace)
        normalized_prompt = ' '.join(prompt.strip().split())
        
        # Create hash string
        hash_input = f"{model}:{temperature}:{normalized_prompt}"
        return hashlib.sha256(hash_input.encode()).hexdigest()


class LLMMatchResult:
    """Result of a cache match operation."""
    
    def __init__(self, is_match: bool, response: Optional[str] = None, 
                 similarity: float = 0.0, reason: str = ""):
        self.is_match = is_match
        self.response = response
        self.similarity = similarity
        self.reason = reason
    
    def __repr__(self):
        return f"LLMMatchResult(is_match={self.is_match}, similarity={self.similarity}, reason='{self.reason}')"


class LLMLLMCacheManager:
    """
    Manages LLM response caching for cost optimization.
    
    This manager provides:
    - Exact match caching (by prompt hash)
    - TTL-based expiration
    - Semantic similarity matching (optional)
    - Context-based invalidation
    - Statistics tracking
    """
    
    def __init__(self, db_path: str = "llm_cache.db", 
                 default_ttl_hours: int = 24,
                 semantic_threshold: float = 0.95):
        """
        Initialize the LLM cache manager.
        
        Args:
            db_path: Path to the cache database
            default_ttl_hours: Default TTL for cached responses (in hours)
            semantic_threshold: Minimum similarity threshold for semantic matching
        """
        self.db_path = Path(db_path)
        self.default_ttl_hours = default_ttl_hours
        self.semantic_threshold = semantic_threshold
        
        # Initialize database
        self._init_db()
        
        logger.info(f"LLM Cache Manager initialized at {self.db_path}")
    
    def _init_db(self):
        """Initialize the cache database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS llm_cache (
                    prompt_hash TEXT PRIMARY KEY,
                    prompt TEXT,
                    response TEXT,
                    model TEXT,
                    temperature REAL,
                    created_at DATETIME,
                    expires_at DATETIME,
                    hit_count INTEGER DEFAULT 0,
                    last_hit DATETIME,
                    similarity_enabled INTEGER DEFAULT 0
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_expires_at 
                ON llm_cache(expires_at)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_model 
                ON llm_cache(model, temperature)
            """)
            
            # Statistics table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache_stats (
                    stat_date TEXT PRIMARY KEY,
                    hits INTEGER DEFAULT 0,
                    misses INTEGER DEFAULT 0,
                    requests INTEGER DEFAULT 0,
                    hit_rate REAL DEFAULT 0.0,
                    tokens_saved INTEGER DEFAULT 0
                )
            """)
            
            conn.commit()
    
    def get_cached_response(self, prompt: str, model: str, 
                          temperature: float) -> Optional[Dict[str, Any]]:
        """
        Retrieve a cached response if available and not expired.
        
        Args:
            prompt: The prompt to look up
            model: The model name
            temperature: The temperature parameter
            
        Returns:
            Dict with 'response', 'created_at', 'hit_count' if found, None otherwise
        """
        prompt_hash = LLMPromptHash.generate_hash(prompt, model, temperature)
        current_time = datetime.now()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Try exact match first
            cursor.execute("""
                SELECT response, created_at, hit_count
                FROM llm_cache
                WHERE prompt_hash = ? AND expires_at > ?
            """, (prompt_hash, current_time))
            
            result = cursor.fetchone()
            
            if result:
                # Update hit count and last_hit
                cursor.execute("""
                    UPDATE llm_cache
                    SET hit_count = hit_count + 1,
                        last_hit = ?
                    WHERE prompt_hash = ?
                """, (current_time, prompt_hash))
                
                conn.commit()
                
                # Update statistics
                self._record_hit()
                
                logger.debug(f"Cache HIT for prompt_hash={prompt_hash[:16]}...")
                
                return {
                    'response': result[0],
                    'created_at': result[1],
                    'hit_count': result[2] + 1
                }
            else:
                # Record miss
                self._record_miss()
                
                logger.debug(f"Cache MISS for prompt_hash={prompt_hash[:16]}...")
                return None
    
    def cache_response(self, prompt: str, response: str, 
                     model: str, temperature: float,
                     ttl_hours: Optional[int] = None,
                     enable_semantic: bool = False):
        """
        Cache a new LLM response.
        
        Args:
            prompt: The prompt
            response: The LLM response
            model: The model name
            temperature: The temperature parameter
            ttl_hours: Custom TTL (uses default if None)
            enable_semantic: Whether to enable semantic similarity for this entry
        """
        prompt_hash = LLMPromptHash.generate_hash(prompt, model, temperature)
        ttl_hours = ttl_hours or self.default_ttl_hours
        
        current_time = datetime.now()
        expires_at = current_time + timedelta(hours=ttl_hours)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO llm_cache
                (prompt_hash, prompt, response, model, temperature,
                 created_at, expires_at, hit_count, last_hit, similarity_enabled)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0, NULL, ?)
            """, (prompt_hash, prompt, response, model, temperature,
                  current_time, expires_at, 1 if enable_semantic else 0))
            
            conn.commit()
        
        logger.info(f"Cached response for prompt_hash={prompt_hash[:16]}..., "
                  f"expires in {ttl_hours} hours")
    
    def find_similar_response(self, prompt: str, model: str,
                            temperature: float) -> Optional[LLMMatchResult]:
        """
        Find semantically similar cached responses.
        
        Note: This is a placeholder for semantic matching.
        In a production implementation, you would use embeddings
        from OpenAI, Cohere, or similar services.
        
        Args:
            prompt: The prompt to find matches for
            model: The model name
            temperature: The temperature parameter
            
        Returns:
            LLMMatchResult with match information
        """
        # Placeholder for semantic matching
        # In production, this would:
        # 1. Generate embeddings for the prompt
        # 2. Query cache entries with similarity_enabled=1
        # 3. Calculate cosine similarity
        # 4. Return matches above threshold
        
        logger.debug("Semantic matching not yet implemented")
        return LLMMatchResult(
            is_match=False,
            reason="Semantic matching not yet implemented"
        )
    
    def invalidate_for_files(self, file_paths: List[str]):
        """
        Invalidate cache entries that depend on specific files.
        
        This is a conservative approach - it clears any cache that
        might be affected by changes to the specified files.
        
        Args:
            file_paths: List of file paths that have changed
        """
        # In a more sophisticated implementation, we would:
        # 1. Track which files each cache entry depends on
        # 2. Only invalidate entries that directly depend on changed files
        
        # For now, we'll invalidate all entries that contain
        # references to the changed files in their prompts
        file_count = 0
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            for file_path in file_paths:
                # Check for file references in prompts
                cursor.execute("""
                    DELETE FROM llm_cache
                    WHERE prompt LIKE ?
                """, (f"%{file_path}%",))
                
                deleted = cursor.rowcount
                file_count += deleted
                
                logger.info(f"Invalidated {deleted} cache entries for file={file_path}")
            
            conn.commit()
        
        if file_count > 0:
            logger.info(f"Total invalidated: {file_count} cache entries")
    
    def invalidate_expired(self) -> int:
        """
        Remove expired cache entries.
        
        Returns:
            Number of entries removed
        """
        current_time = datetime.now()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                DELETE FROM llm_cache
                WHERE expires_at < ?
            """, (current_time,))
            
            deleted = cursor.rowcount
            conn.commit()
        
        if deleted > 0:
            logger.info(f"Removed {deleted} expired cache entries")
        
        return deleted
    
    def _record_hit(self):
        """Record a cache hit in today's statistics."""
        today = datetime.now().strftime("%Y-%m-%d")
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO cache_stats (stat_date, hits, requests)
                VALUES (?, 1, 1)
                ON CONFLICT(stat_date) DO UPDATE SET
                    hits = hits + 1,
                    requests = requests + 1,
                    hit_rate = CAST(hits AS REAL) / CAST(requests AS REAL)
            """, (today,))
            conn.commit()
    
    def _record_miss(self):
        """Record a cache miss in today's statistics."""
        today = datetime.now().strftime("%Y-%m-%d")
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO cache_stats (stat_date, misses, requests)
                VALUES (?, 1, 1)
                ON CONFLICT(stat_date) DO UPDATE SET
                    misses = misses + 1,
                    requests = requests + 1,
                    hit_rate = CAST(hits AS REAL) / CAST(requests AS REAL)
            """, (today,))
            conn.commit()
    
    def get_stats(self, days: int = 7) -> Dict[str, Any]:
        """
        Get cache statistics for the specified period.
        
        Args:
            days: Number of days to include in statistics
            
        Returns:
            Dict with cache statistics
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get recent statistics
            cursor.execute("""
                SELECT 
                    SUM(hits) as total_hits,
                    SUM(misses) as total_misses,
                    SUM(requests) as total_requests,
                    SUM(tokens_saved) as total_tokens_saved
                FROM cache_stats
                WHERE stat_date >= date('now', '-' || ? || ' days')
            """, (days,))
            
            result = cursor.fetchone()
            
            # Calculate overall hit rate from total hits and requests
            total_hits = result[0] or 0
            total_requests = result[2] or 0
            hit_rate = total_hits / total_requests if total_requests > 0 else 0.0
            
            # Get current cache size
            cursor.execute("SELECT COUNT(*) FROM llm_cache")
            cache_size = cursor.fetchone()[0]
            
            # Get expired entries count
            cursor.execute("SELECT COUNT(*) FROM llm_cache WHERE expires_at < ?", 
                         (datetime.now(),))
            expired_count = cursor.fetchone()[0]
            
            stats = {
                'period_days': days,
                'total_hits': total_hits,
                'total_misses': result[1] or 0,
                'total_requests': total_requests,
                'hit_rate': hit_rate,
                'total_tokens_saved': result[3] or 0,
                'cache_size': cache_size,
                'expired_entries': expired_count,
                'hit_rate_percent': hit_rate * 100
            }
            
            return stats
    
    def get_daily_stats(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        Get daily statistics breakdown.
        
        Args:
            days: Number of days to include
            
        Returns:
            List of daily statistics dictionaries
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    stat_date,
                    hits,
                    misses,
                    requests,
                    hit_rate,
                    tokens_saved
                FROM cache_stats
                WHERE stat_date >= date('now', '-' || ? || ' days')
                ORDER BY stat_date DESC
                LIMIT ?
            """, (days, days))
            
            rows = cursor.fetchall()
            
            return [dict(row) for row in rows]
    
    def clear_all(self):
        """Clear all cache entries."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM llm_cache")
            count = cursor.fetchone()[0]
            
            cursor.execute("DELETE FROM llm_cache")
            conn.commit()
        
        logger.warning(f"Cleared {count} cache entries")
    
    def get_cache_size_mb(self) -> float:
        """
        Get the approximate size of the cache database in MB.
        
        Returns:
            Size in megabytes
        """
        if not self.db_path.exists():
            return 0.0
        
        size_bytes = self.db_path.stat().st_size
        return size_bytes / (1024 * 1024)


# Convenience function for quick access
def get_cache_manager(db_path: str = "llm_cache.db") -> LLMLLMCacheManager:
    """
    Get a singleton instance of the LLM cache manager.
    
    Args:
        db_path: Path to the cache database
        
    Returns:
        LLMLLMCacheManager instance
    """
    if not hasattr(get_cache_manager, '_instance'):
        get_cache_manager._instance = LLMLLMCacheManager(db_path)
    return get_cache_manager._instance