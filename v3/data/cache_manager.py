import os
import pickle
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from collections import OrderedDict


class CacheManager:
    """
    Manages caching of AST analysis results to avoid redundant parsing.

    Features:
    - File-based cache stored in .l4_cache/ directory
    - Cache invalidation based on file modification time
    - LRU eviction when cache size limit is reached
    - Serialization of semantic maps and analysis results
    """

    def __init__(self, cache_dir: str = ".l4_cache", max_cache_size: int = 100):
        """
        Initialize the cache manager.

        Args:
            cache_dir: Directory to store cache files (default: .l4_cache/)
            max_cache_size: Maximum number of cache entries before LRU eviction
        """
        self.cache_dir = Path(cache_dir)
        self.max_cache_size = max_cache_size
        self.cache_index = OrderedDict()  # Ordered by access time for LRU
        self.cache_index_file = self.cache_dir / "cache_index.pkl"

        # Ensure cache directory exists
        self.cache_dir.mkdir(exist_ok=True)

        # Load existing cache index
        self._load_cache_index()

    def _load_cache_index(self):
        """Load the cache index from disk if it exists."""
        if self.cache_index_file.exists():
            try:
                with open(self.cache_index_file, "rb") as f:
                    self.cache_index = pickle.load(f)
            except (pickle.PickleError, EOFError):
                # Corrupted cache index, start fresh
                self.cache_index = OrderedDict()

    def _save_cache_index(self):
        """Save the cache index to disk."""
        with open(self.cache_index_file, "wb") as f:
            pickle.dump(self.cache_index, f)

    def _get_file_hash(self, file_path: str) -> str:
        """
        Calculate MD5 hash of a file for cache key.

        Args:
            file_path: Path to the file

        Returns:
            str: MD5 hash of the file content
        """
        if not os.path.exists(file_path):
            return None

        hasher = hashlib.md5()
        with open(file_path, "rb") as f:
            # Read in chunks to handle large files
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)

        return hasher.hexdigest()

    def _get_file_mtime(self, file_path: str) -> float:
        """
        Get file modification time.

        Args:
            file_path: Path to the file

        Returns:
            float: Modification timestamp or None if file doesn't exist
        """
        try:
            return os.path.getmtime(file_path)
        except OSError:
            return None

    def _generate_cache_key(self, file_path: str, analysis_type: str) -> str:
        """
        Generate a unique cache key for a file and analysis type.

        Args:
            file_path: Path to the source file
            analysis_type: Type of analysis (e.g., 'semantic_map', 'call_graph')

        Returns:
            str: Unique cache key
        """
        file_hash = self._get_file_hash(file_path)
        if not file_hash:
            return None

        # Use file hash + analysis type as key
        # This automatically handles file changes (different hash = different key)
        return f"{file_hash}_{analysis_type}"

    def _get_cache_file_path(self, cache_key: str) -> Path:
        """
        Get the full path to a cache file.

        Args:
            cache_key: Cache key

        Returns:
            Path: Path to cache file
        """
        return self.cache_dir / f"{cache_key}.pkl"

    def _evict_if_needed(self):
        """
        Evict least recently used cache entries if cache is full.
        """
        while len(self.cache_index) >= self.max_cache_size:
            # Pop the oldest item (LRU)
            lru_key, lru_info = self.cache_index.popitem(last=False)

            # Delete the cache file
            cache_file = self._get_cache_file_path(lru_key)
            if cache_file.exists():
                cache_file.unlink()

    def _is_cache_valid(self, cache_info: Dict[str, Any]) -> bool:
        """
        Check if cached data is still valid.

        Args:
            cache_info: Cache metadata dictionary

        Returns:
            bool: True if cache is valid
        """
        if not os.path.exists(cache_info["file_path"]):
            return False

        # Check if file has been modified since cache was created
        current_mtime = self._get_file_mtime(cache_info["file_path"])
        cached_mtime = cache_info.get("file_mtime")

        if current_mtime is None or cached_mtime is None:
            return False

        return current_mtime == cached_mtime

    def get(self, file_path: str, analysis_type: str) -> Optional[Any]:
        """
        Retrieve cached analysis result if available and valid.

        Args:
            file_path: Path to the source file
            analysis_type: Type of analysis (e.g., 'semantic_map', 'call_graph')

        Returns:
            Cached data or None if not found/invalid
        """
        if not os.path.exists(file_path):
            return None

        file_hash = self._get_file_hash(file_path)
        cache_key = self._generate_cache_key(file_path, analysis_type)

        if cache_key is None:
            return None

        if cache_key not in self.cache_index:
            return None

        cache_info = self.cache_index[cache_key]

        # Check if cache is still valid
        if not self._is_cache_valid(cache_info):
            # Remove invalid cache entry
            del self.cache_index[cache_key]
            self._save_cache_index()
            return None

        # Move to end of OrderedDict (most recently used)
        self.cache_index.move_to_end(cache_key)
        self._save_cache_index()

        # Load cached data
        cache_file = self._get_cache_file_path(cache_key)
        if not cache_file.exists():
            return None

        try:
            with open(cache_file, "rb") as f:
                cached_data = pickle.load(f)
                cached_data["_cache_hit"] = True
                return cached_data
        except (pickle.PickleError, EOFError):
            # Corrupted cache file
            return None

    def set(self, file_path: str, analysis_type: str, data: Any) -> bool:
        """
        Store analysis result in cache.

        Args:
            file_path: Path to the source file
            analysis_type: Type of analysis (e.g., 'semantic_map', 'call_graph')
            data: Data to cache

        Returns:
            bool: True if successfully cached
        """
        if not os.path.exists(file_path):
            return False

        file_hash = self._get_file_hash(file_path)
        cache_key = self._generate_cache_key(file_path, analysis_type)

        if cache_key is None:
            return False

        # Evict old entries if needed
        self._evict_if_needed()

        # Prepare cache metadata
        cache_info = {
            "file_path": os.path.abspath(file_path),
            "file_mtime": self._get_file_mtime(file_path),
            "file_hash": file_hash,
            "cached_at": datetime.now().isoformat(),
            "analysis_type": analysis_type,
        }

        # Store cache index
        self.cache_index[cache_key] = cache_info
        self.cache_index.move_to_end(cache_key)  # Mark as most recently used

        # Save cached data
        cache_file = self._get_cache_file_path(cache_key)
        try:
            with open(cache_file, "wb") as f:
                pickle.dump(data, f)

            self._save_cache_index()
            return True
        except (pickle.PickleError, IOError) as e:
            # Failed to cache, remove from index
            if cache_key in self.cache_index:
                del self.cache_index[cache_key]
            return False

    def invalidate(self, file_path: str):
        """
        Invalidate all cached data for a specific file.

        Args:
            file_path: Path to the source file
        """
        if not os.path.exists(file_path):
            return

        file_hash = self._get_file_hash(file_path)
        keys_to_remove = []

        # Find all cache entries for this file
        for cache_key, cache_info in self.cache_index.items():
            if cache_info["file_path"] == os.path.abspath(file_path):
                keys_to_remove.append(cache_key)

        # Remove cache entries and files
        for cache_key in keys_to_remove:
            cache_file = self._get_cache_file_path(cache_key)
            if cache_file.exists():
                cache_file.unlink()
            del self.cache_index[cache_key]

        if keys_to_remove:
            self._save_cache_index()

    def clear_all(self):
        """Clear all cached data."""
        # Delete all cache files
        for cache_file in self.cache_dir.glob("*.pkl"):
            if cache_file != self.cache_index_file:  # Don't delete index file
                cache_file.unlink()

        # Clear index
        self.cache_index = OrderedDict()
        self._save_cache_index()

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            dict: Cache statistics including size, hit rate, etc.
        """
        total_size = 0
        valid_entries = 0

        for cache_key, cache_info in self.cache_index.items():
            cache_file = self._get_cache_file_path(cache_key)
            if cache_file.exists():
                total_size += cache_file.stat().st_size
                if self._is_cache_valid(cache_info):
                    valid_entries += 1

        return {
            "total_entries": len(self.cache_index),
            "valid_entries": valid_entries,
            "max_size": self.max_cache_size,
            "usage_percent": (len(self.cache_index) / self.max_cache_size) * 100,
            "total_size_bytes": total_size,
            "total_size_mb": total_size / (1024 * 1024),
            "cache_dir": str(self.cache_dir),
        }

    def cleanup_stale(self):
        """
        Remove all stale (invalid) cache entries.
        """
        keys_to_remove = []

        for cache_key, cache_info in self.cache_index.items():
            if not self._is_cache_valid(cache_info):
                keys_to_remove.append(cache_key)

        for cache_key in keys_to_remove:
            cache_file = self._get_cache_file_path(cache_key)
            if cache_file.exists():
                cache_file.unlink()
            del self.cache_index[cache_key]

        if keys_to_remove:
            self._save_cache_index()

        return len(keys_to_remove)


# Global cache manager instance (singleton pattern)
_global_cache_manager = None


def get_cache_manager() -> CacheManager:
    """
    Get the global cache manager instance.

    Returns:
        CacheManager: Global cache manager instance
    """
    global _global_cache_manager

    if _global_cache_manager is None:
        _global_cache_manager = CacheManager()

    return _global_cache_manager
