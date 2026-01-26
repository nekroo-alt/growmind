"""
Context Hierarchy Manager - V5 Layered Context Architecture

This module implements hierarchical context management with progressive loading,
layer prioritization, and optimization for L4D V5.

Context Levels:
- L0 (Immediate): Current file, current function, immediate dependencies (HOT cache)
- L1 (Recent): Last 10 actions, last 5 errors, recent telemetry (WARM cache)
- L2 (Session): Session history, task progress, patterns learned (COLD disk cache)
- L3 (Project): Project state, architecture, long-term patterns (on-demand loading)

V5 Enhancements:
- Progressive loading: Start with L0, expand to L1/L2/L3 only when needed
- Layer prioritization: Learn optimal layers for each task type
- Hot/Warm/Cold classification: Cache frequently used layers intelligently
- Access pattern optimization: Learn and optimize layer loading based on patterns
"""

import sqlite3
import json
import gzip
import time
from typing import Optional, Dict, List, Any, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import threading
from collections import OrderedDict

from v5.core import get_logger

logger = get_logger(__name__)

# Global singleton instance
_context_hierarchy_manager: Optional['ContextHierarchyManager'] = None


def get_context_hierarchy(db_path: str = "context_hierarchy.db", 
                      cache_capacities: Optional[Dict[str, int]] = None) -> 'ContextHierarchyManager':
    """
    Get or create the global ContextHierarchyManager instance.
    
    Args:
        db_path: Path to SQLite database file
        cache_capacities: Optional cache capacities per level
    
    Returns:
        Global ContextHierarchyManager instance
    """
    global _context_hierarchy_manager
    
    if _context_hierarchy_manager is None:
        _context_hierarchy_manager = ContextHierarchyManager(
            db_path=db_path,
            cache_capacities=cache_capacities
        )
        logger.info("Created global ContextHierarchyManager instance")
    
    return _context_hierarchy_manager


class ContextLevel:
    """Context level enumeration with priority."""
    L0 = "L0"  # Immediate context (highest priority, HOT)
    L1 = "L1"  # Recent context (high priority, WARM)
    L2 = "L2"  # Session context (medium priority, COLD)
    L3 = "L3"  # Project context (low priority, on-demand)
    
    @classmethod
    def get_priority(cls, level: str) -> int:
        """Get priority level (lower = higher priority)."""
        priorities = {
            cls.L0: 0,
            cls.L1: 1,
            cls.L2: 2,
            cls.L3: 3
        }
        return priorities.get(level, 999)
    
    @classmethod
    def get_cache_type(cls, level: str) -> str:
        """Get cache type for a level (HOT, WARM, COLD, NONE)."""
        cache_types = {
            cls.L0: "HOT",      # Always in memory
            cls.L1: "WARM",     # Cached in memory
            cls.L2: "COLD",     # Cached on disk
            cls.L3: "NONE"       # Load on demand
        }
        return cache_types.get(level, "NONE")


class LayerUsagePattern:
    """Track usage patterns for context layers."""
    
    def __init__(self):
        self.task_types: Dict[str, Dict[str, int]] = {}  # task_type -> {level: count}
        self.layer_success_rates: Dict[str, float] = {}  # level -> success_rate
        self.layer_load_times: Dict[str, List[float]] = {}  # level -> [load_times]
        self.last_updated = time.time()
    
    def record_usage(self, task_type: str, level: str, success: bool, load_time: float):
        """Record layer usage for analysis."""
        if task_type not in self.task_types:
            self.task_types[task_type] = {}
        
        self.task_types[task_type][level] = self.task_types[task_type].get(level, 0) + 1
        
        # Update success rate
        if level not in self.layer_success_rates:
            self.layer_success_rates[level] = 0.0
        
        # Exponential moving average
        if success:
            self.layer_success_rates[level] = 0.9 * self.layer_success_rates[level] + 0.1 * 1.0
        else:
            self.layer_success_rates[level] = 0.9 * self.layer_success_rates[level] + 0.1 * 0.0
        
        # Track load time
        if level not in self.layer_load_times:
            self.layer_load_times[level] = []
        self.layer_load_times[level].append(load_time)
        
        # Keep only last 100 load times
        if len(self.layer_load_times[level]) > 100:
            self.layer_load_times[level] = self.layer_load_times[level][-100:]
        
        self.last_updated = time.time()
    
    def get_optimal_level(self, task_type: str) -> str:
        """Get optimal context level for a given task type."""
        if task_type not in self.task_types:
            return ContextLevel.L0  # Default to minimal
        
        # Find level with highest usage and success rate
        level_scores = {}
        for level, count in self.task_types[task_type].items():
            success_rate = self.layer_success_rates.get(level, 0.5)
            # Score combines usage frequency and success rate
            level_scores[level] = count * success_rate
        
        if not level_scores:
            return ContextLevel.L0
        
        # Return level with highest score
        optimal_level = max(level_scores, key=level_scores.get)
        
        # Always start at least at L0
        if ContextLevel.get_priority(optimal_level) < ContextLevel.get_priority(ContextLevel.L0):
            return ContextLevel.L0
        
        return optimal_level
    
    def get_average_load_time(self, level: str) -> Optional[float]:
        """Get average load time for a level."""
        if level not in self.layer_load_times or not self.layer_load_times[level]:
            return None
        return sum(self.layer_load_times[level]) / len(self.layer_load_times[level])


class LRUCache:
    """
    Thread-safe LRU cache with custom eviction policy.
    
    Features:
    - LRU eviction when capacity is reached
    - Thread-safe operations
    - Cache statistics tracking
    """
    
    def __init__(self, capacity: int):
        """
        Initialize LRU cache.
        
        Args:
            capacity: Maximum number of items in cache
        """
        self.capacity = capacity
        self.cache: OrderedDict = OrderedDict()
        self.hits = 0
        self.misses = 0
        self._lock = threading.RLock()
    
    def get(self, key: Any) -> Optional[Any]:
        """
        Get item from cache.
        
        Args:
            key: Cache key
        
        Returns:
            Cached value or None if not found
        """
        with self._lock:
            if key in self.cache:
                # Move to end (most recently used)
                value = self.cache.pop(key)
                self.cache[key] = value
                self.hits += 1
                return value
            self.misses += 1
            return None
    
    def put(self, key: Any, value: Any):
        """
        Put item in cache.
        
        Args:
            key: Cache key
            value: Value to cache
        """
        with self._lock:
            if key in self.cache:
                # Update existing
                self.cache.pop(key)
            elif len(self.cache) >= self.capacity:
                # Evict least recently used
                self.cache.popitem(last=False)
            
            self.cache[key] = value
    
    def invalidate(self, key: Any):
        """
        Invalidate specific cache entry.
        
        Args:
            key: Cache key to invalidate
        """
        with self._lock:
            if key in self.cache:
                del self.cache[key]
    
    def clear(self):
        """Clear all cache entries."""
        with self._lock:
            self.cache.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with hit rate, size, etc.
        """
        with self._lock:
            total = self.hits + self.misses
            hit_rate = self.hits / total if total > 0 else 0.0
            return {
                'capacity': self.capacity,
                'size': len(self.cache),
                'hits': self.hits,
                'misses': self.misses,
                'hit_rate': hit_rate
            }


class ContextHierarchyManager:
    """
    Manages hierarchical context storage and retrieval for adaptive reasoning.
    
    Features:
    - Multi-level context storage (L0-L3)
    - TTL-based expiration for L0/L1
    - Context summarization support
    - Context propagation between levels
    - Thread-safe operations
    - LRU caching for L0/L1 contexts
    """
    
    # Default retention policies (in seconds)
    DEFAULT_TTL = {
        ContextLevel.L0: 300,      # 5 minutes
        ContextLevel.L1: 3600,     # 1 hour
        ContextLevel.L2: 86400,    # 24 hours
        ContextLevel.L3: 604800,   # 7 days
    }
    
    # Default context limits
    DEFAULT_LIMITS = {
        ContextLevel.L0: 1,        # Only current action
        ContextLevel.L1: 10,       # Last 10 actions
        ContextLevel.L2: 100,      # Session history
        ContextLevel.L3: 1000,     # Project history
    }
    
    # Default cache capacities (V5 enhanced)
    DEFAULT_CACHE_CAPACITIES = {
        ContextLevel.L0: 50,       # HOT cache: 50 L0 items in memory
        ContextLevel.L1: 200,      # WARM cache: 200 L1 items in memory
        ContextLevel.L2: 1000,     # COLD cache: 1000 L2 items on disk
        ContextLevel.L3: 0,        # No caching: L3 loaded on demand
    }
    
    # Default optimal levels per task type (learned over time)
    DEFAULT_OPTIMAL_LEVELS = {
        'implementation': ContextLevel.L0,
        'planning': ContextLevel.L2,
        'verification': ContextLevel.L0,
        'refactoring': ContextLevel.L2,
        'debugging': ContextLevel.L1,
        'analysis': ContextLevel.L2,
        'default': ContextLevel.L0
    }
    
    def __init__(self, db_path: str = "context_hierarchy.db", cache_capacities: Optional[Dict[str, int]] = None):
        """
        Initialize ContextHierarchyManager with V5 progressive loading features.
        
        Args:
            db_path: Path to SQLite database file
            cache_capacities: Optional cache capacities per level
        """
        self.db_path = db_path
        self._lock = threading.RLock()
        
        # Initialize LRU caches
        capacities = cache_capacities or self.DEFAULT_CACHE_CAPACITIES
        self._caches: Dict[str, Optional[LRUCache]] = {}
        for level in [ContextLevel.L0, ContextLevel.L1, ContextLevel.L2, ContextLevel.L3]:
            capacity = capacities.get(level, 0)
            if capacity > 0:
                self._caches[level] = LRUCache(capacity)
            else:
                self._caches[level] = None
        
        # V5: Layer usage pattern tracking
        self.usage_pattern = LayerUsagePattern()
        
        # V5: Pre-loaded layers cache
        self._preloaded_layers: Dict[str, Optional[Any]] = {
            ContextLevel.L0: None,
            ContextLevel.L1: None,
            ContextLevel.L2: None,
            ContextLevel.L3: None
        }
        
        self._init_database()
        self._load_usage_patterns()
        logger.info(f"ContextHierarchyManager initialized with db_path={db_path}")
    
    def _init_database(self):
        """Initialize database schema for context hierarchy."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Context items table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS context_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    level TEXT NOT NULL,
                    item_type TEXT NOT NULL,
                    content BLOB NOT NULL,
                    compressed INTEGER DEFAULT 1,
                    timestamp REAL NOT NULL,
                    expires_at REAL,
                    metadata TEXT,
                    parent_id INTEGER,
                    FOREIGN KEY (parent_id) REFERENCES context_items(id) ON DELETE CASCADE
                )
            """)
            
            # Context summaries table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS context_summaries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    level TEXT NOT NULL,
                    summary_type TEXT NOT NULL,
                    content BLOB NOT NULL,
                    compressed INTEGER DEFAULT 1,
                    timestamp REAL NOT NULL,
                    expires_at REAL,
                    item_ids TEXT NOT NULL
                )
            """)
            
            # Context propagation rules table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS propagation_rules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    from_level TEXT NOT NULL,
                    to_level TEXT NOT NULL,
                    rule_type TEXT NOT NULL,
                    criteria TEXT NOT NULL,
                    action TEXT NOT NULL,
                    priority INTEGER DEFAULT 0,
                    UNIQUE(from_level, to_level, rule_type)
                )
            """)
            
            # Context access patterns table (for optimization)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS access_patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    level TEXT NOT NULL,
                    access_type TEXT NOT NULL,
                    access_count INTEGER DEFAULT 0,
                    last_access REAL NOT NULL,
                    avg_access_interval REAL
                )
            """)
            
            # V5: Layer usage patterns table (for progressive loading optimization)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS layer_usage_patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_type TEXT NOT NULL,
                    level TEXT NOT NULL,
                    usage_count INTEGER DEFAULT 0,
                    success_count INTEGER DEFAULT 0,
                    avg_load_time REAL,
                    last_used REAL NOT NULL,
                    UNIQUE(task_type, level)
                )
            """)
            
            # V5: Preload recommendations table (for layer prioritization)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS preload_recommendations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_type TEXT NOT NULL UNIQUE,
                    recommended_level TEXT NOT NULL,
                    confidence REAL DEFAULT 0.5,
                    last_updated REAL NOT NULL
                )
            """)
            
            # Create indexes for performance
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_context_level_timestamp 
                ON context_items(level, timestamp DESC)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_context_expires 
                ON context_items(expires_at)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_context_parent 
                ON context_items(parent_id)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_summary_level_timestamp 
                ON context_summaries(level, timestamp DESC)
            """)
            
            # V5: Indexes for layer usage patterns
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_layer_usage_task 
                ON layer_usage_patterns(task_type)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_layer_usage_level 
                ON layer_usage_patterns(level)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_preload_task 
                ON preload_recommendations(task_type)
            """)
            
            conn.commit()
            
            logger.debug("Database schema initialized for context hierarchy (V5)")
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory and WAL mode for better concurrency."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")  # V5: Better concurrency
        conn.execute("PRAGMA synchronous = NORMAL")  # V5: Better performance
        return conn
    
    def _compress_data(self, data: Any) -> bytes:
        """Compress data using gzip."""
        json_str = json.dumps(data, default=str)
        return gzip.compress(json_str.encode('utf-8'))
    
    def _decompress_data(self, compressed: bytes) -> Any:
        """Decompress gzip data."""
        json_str = gzip.decompress(compressed).decode('utf-8')
        return json.loads(json_str)
    
    def add_context_item(
        self,
        level: str,
        item_type: str,
        content: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
        parent_id: Optional[int] = None,
        ttl: Optional[float] = None
    ) -> int:
        """
        Add a context item to specified level.
        
        Args:
            level: Context level (L0, L1, L2, L3)
            item_type: Type of context item (action, error, state, etc.)
            content: Content dictionary
            metadata: Optional metadata dictionary
            parent_id: Optional parent context item ID
            ttl: Optional time-to-live in seconds (overrides default)
        
        Returns:
            ID of inserted context item
        """
        with self._lock:
            timestamp = time.time()
            expires_at = None
            
            if ttl:
                expires_at = timestamp + ttl
            elif level in self.DEFAULT_TTL:
                expires_at = timestamp + self.DEFAULT_TTL[level]
            
            compressed_content = self._compress_data(content)
            metadata_json = json.dumps(metadata, default=str) if metadata else None
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO context_items 
                    (level, item_type, content, compressed, timestamp, expires_at, metadata, parent_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    level, item_type, compressed_content, 1,
                    timestamp, expires_at, metadata_json, parent_id
                ))
                item_id = cursor.lastrowid
                conn.commit()
                
                # Invalidate related cache entries
                self._invalidate_cache(level)
                
                # Clean up old items if limit exceeded
                self._enforce_limit(conn, level)
                
                logger.debug(f"Added context item {item_id} at level {level}")
                return item_id
    
    def _invalidate_cache(self, level: str):
        """
        Invalidate cache entries for a given level.
        
        Args:
            level: Context level to invalidate
        """
        cache = self._caches.get(level)
        if cache:
            cache.clear()
            logger.debug(f"Invalidated cache for level {level}")
    
    def get_current_action(self) -> Optional[Dict[str, Any]]:
        """
        Get current action from L0 context.
        
        Returns:
            Current action context or None if not found
        """
        # Check cache first
        cache_key = ('current_action', ContextLevel.L0)
        cache = self._caches.get(ContextLevel.L0)
        
        if cache:
            cached = cache.get(cache_key)
            if cached is not None:
                logger.debug("Cache hit for current action")
                return cached
        
        # Query from database
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT content, compressed FROM context_items 
                WHERE level = ? AND item_type = 'action'
                ORDER BY timestamp DESC LIMIT 1
            """, (ContextLevel.L0,))
            
            row = cursor.fetchone()
            if row:
                if row['compressed']:
                    content = self._decompress_data(row['content'])
                else:
                    content = json.loads(row['content'])
                
                # Cache result
                if cache:
                    cache.put(cache_key, content)
                
                return content
            return None
    
    def get_recent_actions(self, count: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent actions from L1 context.
        
        Args:
            count: Number of actions to retrieve
        
        Returns:
            List of recent action contexts
        """
        # Check cache first
        cache_key = ('recent_actions', ContextLevel.L1, count)
        cache = self._caches.get(ContextLevel.L1)
        
        if cache:
            cached = cache.get(cache_key)
            if cached is not None:
                logger.debug(f"Cache hit for recent actions (count={count})")
                return cached
        
        # Query from database
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT content, compressed, timestamp FROM context_items 
                WHERE level = ? AND item_type = 'action'
                ORDER BY timestamp DESC LIMIT ?
            """, (ContextLevel.L1, count))
            
            actions = []
            for row in cursor.fetchall():
                if row['compressed']:
                    content = self._decompress_data(row['content'])
                else:
                    content = json.loads(row['content'])
                content['timestamp'] = row['timestamp']
                actions.append(content)
            
            # Cache result
            if cache:
                cache.put(cache_key, actions)
            
            return actions
    
    def get_session_context(self) -> Dict[str, Any]:
        """
        Get session context from L2.
        
        Returns:
            Session context dictionary with actions, errors, and patterns
        """
        # Check cache first
        cache_key = ('session_context', ContextLevel.L2)
        cache = self._caches.get(ContextLevel.L2)
        
        if cache:
            cached = cache.get(cache_key)
            if cached is not None:
                logger.debug("Cache hit for session context")
                return cached
        
        # Query from database
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Get actions
            cursor.execute("""
                SELECT content, compressed FROM context_items 
                WHERE level = ? AND item_type = 'action'
                ORDER BY timestamp DESC
            """, (ContextLevel.L2,))
            
            actions = []
            for row in cursor.fetchall():
                if row['compressed']:
                    actions.append(self._decompress_data(row['content']))
                else:
                    actions.append(json.loads(row['content']))
            
            # Get errors
            cursor.execute("""
                SELECT content, compressed FROM context_items 
                WHERE level = ? AND item_type = 'error'
                ORDER BY timestamp DESC
            """, (ContextLevel.L2,))
            
            errors = []
            for row in cursor.fetchall():
                if row['compressed']:
                    errors.append(self._decompress_data(row['content']))
                else:
                    errors.append(json.loads(row['content']))
            
            context = {
                'actions': actions,
                'errors': errors,
                'timestamp': time.time()
            }
            
            # Cache result
            if cache:
                cache.put(cache_key, context)
            
            return context
    
    def get_project_context(self) -> Dict[str, Any]:
        """
        Get project context from L3.
        
        Returns:
            Project context dictionary with state, architecture, and patterns
        """
        # Check cache first
        cache_key = ('project_context', ContextLevel.L3)
        cache = self._caches.get(ContextLevel.L3)
        
        if cache:
            cached = cache.get(cache_key)
            if cached is not None:
                logger.debug("Cache hit for project context")
                return cached
        
        # Query from database
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Get all project-level items
            cursor.execute("""
                SELECT item_type, content, compressed FROM context_items 
                WHERE level = ?
                ORDER BY item_type, timestamp DESC
            """, (ContextLevel.L3,))
            
            context = {
                'state': None,
                'architecture': None,
                'patterns': [],
                'timestamp': time.time()
            }
            
            for row in cursor.fetchall():
                if row['compressed']:
                    content = self._decompress_data(row['content'])
                else:
                    content = json.loads(row['content'])
                
                if row['item_type'] == 'state':
                    context['state'] = content
                elif row['item_type'] == 'architecture':
                    context['architecture'] = content
                elif row['item_type'] == 'pattern':
                    context['patterns'].append(content)
            
            # Cache result
            if cache:
                cache.put(cache_key, context)
            
            return context
    
    def get_context(
        self,
        level: str,
        count: Optional[int] = None,
        item_type: Optional[str] = None,
        time_range: Optional[Tuple[float, float]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get context items from specified level with optional filters.
        
        Args:
            level: Context level (L0, L1, L2, L3)
            count: Optional limit on number of items
            item_type: Optional filter by item type
            time_range: Optional (start_time, end_time) tuple
        
        Returns:
            List of context items
        """
        # Check cache first for L0 and L1
        cache_key = ('context', level, count, item_type, time_range)
        cache = self._caches.get(level)
        
        if cache and not time_range:  # Don't cache time-range queries
            cached = cache.get(cache_key)
            if cached is not None:
                logger.debug(f"Cache hit for context query at level {level}")
                return cached
        
        # Query from database
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT id, item_type, content, compressed, timestamp, expires_at, metadata 
                FROM context_items 
                WHERE level = ?
            """
            params = [level]
            
            if item_type:
                query += " AND item_type = ?"
                params.append(item_type)
            
            if time_range:
                query += " AND timestamp >= ? AND timestamp <= ?"
                params.extend(time_range)
            
            query += " ORDER BY timestamp DESC"
            
            if count:
                query += " LIMIT ?"
                params.append(count)
            
            cursor.execute(query, params)
            
            items = []
            for row in cursor.fetchall():
                if row['compressed']:
                    content = self._decompress_data(row['content'])
                else:
                    content = json.loads(row['content'])
                
                metadata = json.loads(row['metadata']) if row['metadata'] else None
                
                items.append({
                    'id': row['id'],
                    'item_type': row['item_type'],
                    'content': content,
                    'timestamp': row['timestamp'],
                    'expires_at': row['expires_at'],
                    'metadata': metadata
                })
            
            # Update access patterns
            self._update_access_pattern(level, 'query')
            
            # Cache result for L0 and L1 (no time-range queries)
            if cache and not time_range:
                cache.put(cache_key, items)
            
            return items
    
    # V5: Progressive Loading Methods
    
    def load_context_progressively(
        self,
        task_type: str,
        min_level: str = ContextLevel.L0,
        max_level: Optional[str] = None,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Load context progressively starting from minimal level.
        
        This method implements V5's progressive loading strategy:
        1. Start with minimal level (L0 by default)
        2. Check if current context is sufficient
        3. Expand to next level if needed
        4. Stop when sufficient or max_level reached
        
        Args:
            task_type: Type of task (implementation, planning, etc.)
            min_level: Minimum level to start with (default L0)
            max_level: Maximum level to load (default L3)
            max_tokens: Optional token budget to limit context size
        
        Returns:
            Dictionary with loaded context and metadata
        """
        max_level = max_level or ContextLevel.L3
        current_level = min_level
        
        loaded_context = {
            'level': current_level,
            'items': [],
            'tokens_estimate': 0,
            'sufficient': False,
            'expansion_history': []
        }
        
        logger.info(f"Loading context progressively for task_type={task_type}, starting at {current_level}")
        
        # Try to use optimal level from learned patterns
        optimal_level = self.get_optimal_level(task_type)
        if ContextLevel.get_priority(optimal_level) > ContextLevel.get_priority(current_level):
            logger.debug(f"Using optimal level {optimal_level} based on learned patterns")
            current_level = optimal_level
        
        # Load progressively
        while current_level and ContextLevel.get_priority(current_level) <= ContextLevel.get_priority(max_level):
            start_time = time.time()
            
            # Load context at current level
            items = self._load_level(current_level, max_tokens)
            load_time = time.time() - start_time
            
            # Track usage pattern
            loaded_context['items'].extend(items)
            
            # Estimate tokens (rough estimate: 1 token per 4 characters)
            items_text = json.dumps(items, default=str)
            tokens_estimate = len(items_text) // 4
            loaded_context['tokens_estimate'] += tokens_estimate
            
            # Check if context is sufficient
            sufficient = self._is_context_sufficient(task_type, current_level, loaded_context['items'])
            
            # Record usage
            self._record_layer_usage(task_type, current_level, True, load_time)
            
            loaded_context['expansion_history'].append({
                'level': current_level,
                'items_count': len(items),
                'tokens_estimate': tokens_estimate,
                'load_time': load_time,
                'sufficient': sufficient
            })
            
            if sufficient:
                loaded_context['sufficient'] = True
                loaded_context['level'] = current_level
                logger.info(f"Context sufficient at level {current_level} ({tokens_estimate} tokens)")
                break
            
            # Expand to next level if not sufficient
            next_level = self._get_next_level(current_level)
            if next_level and ContextLevel.get_priority(next_level) <= ContextLevel.get_priority(max_level):
                logger.debug(f"Expanding context from {current_level} to {next_level}")
                current_level = next_level
            else:
                break
        
        # Cache preloaded layer
        self._preloaded_layers[loaded_context['level']] = loaded_context
        
        return loaded_context
    
    def _load_level(self, level: str, max_tokens: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Load context items from a specific level.
        
        Args:
            level: Context level to load
            max_tokens: Optional token limit
        
        Returns:
            List of context items
        """
        # Check if already preloaded
        if self._preloaded_layers.get(level):
            return self._preloaded_layers[level].get('items', [])
        
        # Load from cache or database
        items = self.get_context(level=level)
        
        # Apply token limit if specified
        if max_tokens:
            items = self._limit_by_tokens(items, max_tokens)
        
        return items
    
    def _limit_by_tokens(self, items: List[Dict[str, Any]], max_tokens: int) -> List[Dict[str, Any]]:
        """
        Limit context items by token budget.
        
        Args:
            items: List of context items
            max_tokens: Maximum tokens
        
        Returns:
            Filtered list of items
        """
        limited_items = []
        current_tokens = 0
        
        for item in items:
            # Estimate token count for this item
            item_text = json.dumps(item, default=str)
            item_tokens = len(item_text) // 4
            
            if current_tokens + item_tokens <= max_tokens:
                limited_items.append(item)
                current_tokens += item_tokens
            else:
                break
        
        if len(limited_items) < len(items):
            logger.debug(f"Limited context to {len(limited_items)} items ({current_tokens} tokens)")
        
        return limited_items
    
    def _is_context_sufficient(
        self,
        task_type: str,
        level: str,
        items: List[Dict[str, Any]]
    ) -> bool:
        """
        Check if current context is sufficient for the task.
        
        Args:
            task_type: Type of task
            level: Current context level
            items: Context items loaded
        
        Returns:
            True if context is sufficient, False otherwise
        """
        # L0 is always loaded but may not be sufficient for complex tasks
        if level == ContextLevel.L0:
            # Check if we have essential items
            has_action = any(item.get('item_type') == 'action' for item in items)
            has_state = any(item.get('item_type') == 'state' for item in items)
            
            # For simple tasks, L0 may be sufficient
            simple_tasks = ['implementation', 'verification']
            if task_type in simple_tasks and has_action and has_state:
                return True
            
            return False
        
        # L1, L2, L3 are progressively more comprehensive
        # Check if we have enough context items
        min_items = {
            ContextLevel.L1: 5,   # At least 5 recent items
            ContextLevel.L2: 20,  # At least 20 session items
            ContextLevel.L3: 50   # At least 50 project items
        }
        
        if level in min_items:
            return len(items) >= min_items[level]
        
        return True
    
    def _get_next_level(self, current_level: str) -> Optional[str]:
        """
        Get next higher context level.
        
        Args:
            current_level: Current context level
        
        Returns:
            Next level or None if at max level
        """
        levels = [ContextLevel.L0, ContextLevel.L1, ContextLevel.L2, ContextLevel.L3]
        current_idx = levels.index(current_level) if current_level in levels else -1
        
        if current_idx >= 0 and current_idx < len(levels) - 1:
            return levels[current_idx + 1]
        
        return None
    
    def get_optimal_level(self, task_type: str) -> str:
        """
        Get optimal context level for a given task type based on learned patterns.
        
        Args:
            task_type: Type of task
        
        Returns:
            Optimal context level
        """
        # Check learned optimal level
        optimal = self.usage_pattern.get_optimal_level(task_type)
        
        # Fall back to defaults if no learned pattern
        if optimal == ContextLevel.L0 and task_type in self.DEFAULT_OPTIMAL_LEVELS:
            return self.DEFAULT_OPTIMAL_LEVELS[task_type]
        
        return optimal
    
    def _record_layer_usage(
        self,
        task_type: str,
        level: str,
        success: bool,
        load_time: float
    ):
        """
        Record layer usage for pattern learning.
        
        Args:
            task_type: Type of task
            level: Context level used
            success: Whether the level was sufficient
            load_time: Time taken to load the level
        """
        # Update in-memory pattern
        self.usage_pattern.record_usage(task_type, level, success, load_time)
        
        # Persist to database
        current_time = time.time()
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO layer_usage_patterns
                (task_type, level, usage_count, success_count, avg_load_time, last_used)
                VALUES (
                    ?,
                    ?,
                    COALESCE((SELECT usage_count FROM layer_usage_patterns 
                              WHERE task_type = ? AND level = ?), 0) + 1,
                    COALESCE((SELECT success_count FROM layer_usage_patterns 
                              WHERE task_type = ? AND level = ?), 0) + ?,
                    COALESCE((SELECT avg_load_time FROM layer_usage_patterns 
                              WHERE task_type = ? AND level = ?), ?),
                    ?
                )
            """, (task_type, level, task_type, level, task_type, level, 1 if success else 0,
                  task_type, level, load_time, current_time))
            
            conn.commit()
    
    def _load_usage_patterns(self):
        """Load usage patterns from database."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT task_type, level, usage_count, success_count, avg_load_time, last_used
                FROM layer_usage_patterns
            """)
            
            for row in cursor.fetchall():
                task_type = row['task_type']
                level = row['level']
                
                if task_type not in self.usage_pattern.task_types:
                    self.usage_pattern.task_types[task_type] = {}
                
                self.usage_pattern.task_types[task_type][level] = row['usage_count']
                
                # Calculate success rate
                if row['usage_count'] > 0:
                    success_rate = row['success_count'] / row['usage_count']
                    self.usage_pattern.layer_success_rates[level] = success_rate
                
                # Track load time
                if row['avg_load_time']:
                    if level not in self.usage_pattern.layer_load_times:
                        self.usage_pattern.layer_load_times[level] = []
                    self.usage_pattern.layer_load_times[level].append(row['avg_load_time'])
            
            logger.debug(f"Loaded usage patterns for {len(self.usage_pattern.task_types)} task types")
    
    def preload_layer(self, level: str, task_types: Optional[List[str]] = None):
        """
        Preload a context layer for frequently used tasks.
        
        Args:
            level: Context level to preload
            task_types: Optional list of task types to preload for
        """
        cache_type = ContextLevel.get_cache_type(level)
        
        if cache_type == "NONE":
            logger.debug(f"Skipping preload for {level} (no caching)")
            return
        
        logger.info(f"Preloading {level} layer (cache type: {cache_type})")
        
        start_time = time.time()
        items = self._load_level(level)
        load_time = time.time() - start_time
        
        self._preloaded_layers[level] = {
            'level': level,
            'items': items,
            'tokens_estimate': sum(len(json.dumps(item, default=str)) // 4 for item in items),
            'load_time': load_time,
            'loaded_at': time.time()
        }
        
        # Record as successful preload
        for task_type in task_types or ['default']:
            self._record_layer_usage(task_type, level, True, load_time)
        
        logger.info(f"Preloaded {level} layer with {len(items)} items in {load_time:.3f}s")
    
    def get_preloaded_layer(self, level: str) -> Optional[Dict[str, Any]]:
        """
        Get preloaded context layer if available.
        
        Args:
            level: Context level to get
        
        Returns:
            Preloaded layer data or None if not preloaded
        """
        preloaded = self._preloaded_layers.get(level)
        
        if preloaded:
            # Check if preload is still valid (within TTL)
            age = time.time() - preloaded.get('loaded_at', 0)
            ttl = self.DEFAULT_TTL.get(level, 3600)
            
            if age < ttl:
                return preloaded
            else:
                # Expired preload
                self._preloaded_layers[level] = None
                logger.debug(f"Preload for {level} expired (age={age:.1f}s, ttl={ttl}s)")
        
        return None
    
    def get_layer_recommendations(self, task_type: str) -> Dict[str, Any]:
        """
        Get layer loading recommendations based on usage patterns.
        
        Args:
            task_type: Type of task
        
        Returns:
            Dictionary with recommendations
        """
        optimal_level = self.get_optimal_level(task_type)
        
        # Get usage statistics for this task type
        task_usage = self.usage_pattern.task_types.get(task_type, {})
        
        # Calculate recommendation confidence
        total_usage = sum(task_usage.values()) if task_usage else 0
        optimal_usage = task_usage.get(optimal_level, 0)
        confidence = optimal_usage / total_usage if total_usage > 0 else 0.5
        
        # Get average load times
        avg_load_times = {}
        for level in [ContextLevel.L0, ContextLevel.L1, ContextLevel.L2, ContextLevel.L3]:
            avg_time = self.usage_pattern.get_average_load_time(level)
            if avg_time:
                avg_load_times[level] = avg_time
        
        return {
            'task_type': task_type,
            'recommended_level': optimal_level,
            'confidence': confidence,
            'usage_stats': task_usage,
            'avg_load_times': avg_load_times,
            'cache_types': {
                level: ContextLevel.get_cache_type(level)
                for level in [ContextLevel.L0, ContextLevel.L1, ContextLevel.L2, ContextLevel.L3]
            }
        }
    
    def save_preload_recommendations(self):
        """Save preload recommendations to database."""
        for task_type, optimal_level in self.usage_pattern.task_types.items():
            # Get optimal level for this task type
            optimal = self.usage_pattern.get_optimal_level(task_type)
            
            # Calculate confidence
            task_usage = self.usage_pattern.task_types.get(task_type, {})
            total_usage = sum(task_usage.values()) if task_usage else 0
            optimal_usage = task_usage.get(optimal, 0)
            confidence = optimal_usage / total_usage if total_usage > 0 else 0.5
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO preload_recommendations
                    (task_type, recommended_level, confidence, last_updated)
                    VALUES (?, ?, ?, ?)
                """, (task_type, optimal, confidence, time.time()))
                conn.commit()
        
        logger.info("Saved preload recommendations for all task types")
    
    def store_summary(
        self,
        level: str,
        summary_type: str,
        content: Dict[str, Any],
        item_ids: List[int],
        ttl: Optional[float] = None
    ) -> int:
        """
        Store a context summary for a given level.
        
        Args:
            level: Context level
            summary_type: Type of summary (brief, detailed, full)
            content: Summary content dictionary
            item_ids: List of context item IDs included in summary
            ttl: Optional time-to-live in seconds
        
        Returns:
            ID of inserted summary
        """
        with self._lock:
            timestamp = time.time()
            expires_at = None
            
            if ttl:
                expires_at = timestamp + ttl
            elif level in self.DEFAULT_TTL:
                expires_at = timestamp + self.DEFAULT_TTL[level]
            
            compressed_content = self._compress_data(content)
            item_ids_json = json.dumps(item_ids)
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO context_summaries 
                    (level, summary_type, content, compressed, timestamp, expires_at, item_ids)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    level, summary_type, compressed_content, 1,
                    timestamp, expires_at, item_ids_json
                ))
                summary_id = cursor.lastrowid
                conn.commit()
                
                # Invalidate cache for this level
                self._invalidate_cache(level)
                
                logger.debug(f"Stored summary {summary_id} for level {level}")
                return summary_id
    
    def get_summary(
        self,
        level: str,
        summary_type: str = 'detailed'
    ) -> Optional[Dict[str, Any]]:
        """
        Get latest summary for a given level.
        
        Args:
            level: Context level
            summary_type: Type of summary (brief, detailed, full)
        
        Returns:
            Summary content or None if not found
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT content, compressed, item_ids FROM context_summaries 
                WHERE level = ? AND summary_type = ?
                ORDER BY timestamp DESC LIMIT 1
            """, (level, summary_type))
            
            row = cursor.fetchone()
            if row:
                if row['compressed']:
                    content = self._decompress_data(row['content'])
                else:
                    content = json.loads(row['content'])
                
                content['item_ids'] = json.loads(row['item_ids'])
                return content
            
            return None
    
    def propagate_context(
        self,
        from_level: str,
        to_level: str,
        item_ids: Optional[List[int]] = None,
        criteria: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Propagate context from one level to another.
        
        Args:
            from_level: Source context level
            to_level: Target context level
            item_ids: Optional list of specific item IDs to propagate
            criteria: Optional criteria for selecting items to propagate
        
        Returns:
            Number of items propagated
        """
        with self._get_connection() as conn:
            # Query items from source level
            query = "SELECT item_type, content FROM context_items WHERE level = ?"
            params = [from_level]
            
            if item_ids:
                placeholders = ','.join(['?'] * len(item_ids))
                query += f" AND id IN ({placeholders})"
                params.extend(item_ids)
            
            if criteria:
                # Apply criteria filters
                if 'item_type' in criteria:
                    query += " AND item_type = ?"
                    params.append(criteria['item_type'])
            
            cursor = conn.cursor()
            cursor.execute(query, params)
            
            count = 0
            for row in cursor.fetchall():
                content = self._decompress_data(row['content'])
                try:
                    self.add_context_item(
                        level=to_level,
                        item_type=row['item_type'],
                        content=content,
                        ttl=None  # Use target level's default TTL
                    )
                    count += 1
                except Exception as e:
                    logger.warning(f"Failed to propagate item to {to_level}: {e}")
            
            logger.info(f"Propagated {count} items from {from_level} to {to_level}")
            return count
    
    def cleanup_expired(self) -> int:
        """
        Remove expired context items and summaries.
        
        Returns:
            Number of items removed
        """
        current_time = time.time()
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Delete expired context items
            cursor.execute("""
                DELETE FROM context_items 
                WHERE expires_at IS NOT NULL AND expires_at < ?
            """, (current_time,))
            items_deleted = cursor.rowcount
            
            # Delete expired summaries
            cursor.execute("""
                DELETE FROM context_summaries 
                WHERE expires_at IS NOT NULL AND expires_at < ?
            """, (current_time,))
            summaries_deleted = cursor.rowcount
            
            conn.commit()
            
            # Invalidate all caches
            for level in [ContextLevel.L0, ContextLevel.L1, ContextLevel.L2, ContextLevel.L3]:
                self._invalidate_cache(level)
            
            total_deleted = items_deleted + summaries_deleted
            if total_deleted > 0:
                logger.info(f"Cleaned up {total_deleted} expired items")
            
            return total_deleted
    
    def _enforce_limit(self, conn: sqlite3.Connection, level: str):
        """Enforce context item limit for a given level."""
        limit = self.DEFAULT_LIMITS.get(level)
        if not limit:
            return
        
        # Count current items
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) as count FROM context_items WHERE level = ?
        """, (level,))
        count = cursor.fetchone()['count']
        
        if count <= limit:
            return
        
        # Delete oldest items beyond limit
        to_delete = count - limit
        cursor.execute("""
            DELETE FROM context_items 
            WHERE id IN (
                SELECT id FROM context_items 
                WHERE level = ? 
                ORDER BY timestamp ASC 
                LIMIT ?
            )
        """, (level, to_delete))
        
        conn.commit()
        logger.debug(f"Enforced limit for level {level}: deleted {to_delete} old items")
    
    def _update_access_pattern(self, level: str, access_type: str):
        """Update access pattern tracking for optimization."""
        current_time = time.time()
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Get last access
            cursor.execute("""
                SELECT access_count, last_access, avg_access_interval 
                FROM access_patterns 
                WHERE level = ? AND access_type = ?
            """, (level, access_type))
            
            row = cursor.fetchone()
            
            if row:
                # Update existing record
                new_count = row['access_count'] + 1
                interval = current_time - row['last_access']
                
                # Update average interval using exponential moving average
                if row['avg_access_interval']:
                    new_avg = 0.9 * row['avg_access_interval'] + 0.1 * interval
                else:
                    new_avg = interval
                
                cursor.execute("""
                    UPDATE access_patterns 
                    SET access_count = ?, last_access = ?, avg_access_interval = ?
                    WHERE level = ? AND access_type = ?
                """, (new_count, current_time, new_avg, level, access_type))
            else:
                # Insert new record
                cursor.execute("""
                    INSERT INTO access_patterns 
                    (level, access_type, access_count, last_access, avg_access_interval)
                    VALUES (?, ?, 1, ?, NULL)
                """, (level, access_type, current_time))
            
            conn.commit()
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about context hierarchy.
        
        Returns:
            Statistics dictionary with item counts, sizes, and access patterns
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Count items per level
            level_counts = {}
            for level in [ContextLevel.L0, ContextLevel.L1, ContextLevel.L2, ContextLevel.L3]:
                cursor.execute("""
                    SELECT COUNT(*) as count FROM context_items WHERE level = ?
                """, (level,))
                level_counts[level] = cursor.fetchone()['count']
            
            # Get summary counts
            cursor.execute("SELECT level, COUNT(*) as count FROM context_summaries GROUP BY level")
            summary_counts = {row['level']: row['count'] for row in cursor.fetchall()}
            
            # Get access patterns
            cursor.execute("""
                SELECT level, access_type, access_count, avg_access_interval 
                FROM access_patterns
            """)
            access_patterns = [
                {
                    'level': row['level'],
                    'access_type': row['access_type'],
                    'access_count': row['access_count'],
                    'avg_access_interval': row['avg_access_interval']
                }
                for row in cursor.fetchall()
            ]
            
            # Get cache statistics
            cache_stats = {}
            for level in [ContextLevel.L0, ContextLevel.L1, ContextLevel.L2, ContextLevel.L3]:
                cache = self._caches.get(level)
                if cache:
                    cache_stats[level] = cache.get_stats()
            
            return {
                'item_counts': level_counts,
                'summary_counts': summary_counts,
                'access_patterns': access_patterns,
                'cache_stats': cache_stats,
                'timestamp': time.time()
            }
    
    def get_cache_stats(self, level: Optional[str] = None) -> Dict[str, Any]:
        """
        Get cache statistics for a specific level or all levels.
        
        Args:
            level: Optional context level to get stats for
        
        Returns:
            Cache statistics dictionary
        """
        if level:
            cache = self._caches.get(level)
            if cache:
                stats = cache.get_stats()
                # Add V5 layer info
                stats['cache_type'] = ContextLevel.get_cache_type(level)
                stats['priority'] = ContextLevel.get_priority(level)
                return stats
            return {}
        
        # Return stats for all levels
        all_stats = {}
        for level, cache in self._caches.items():
            if cache:
                stats = cache.get_stats()
                stats['cache_type'] = ContextLevel.get_cache_type(level)
                stats['priority'] = ContextLevel.get_priority(level)
                all_stats[level] = stats
        
        return all_stats
    
    def get_layer_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive layer statistics including usage patterns.
        
        Returns:
            Dictionary with layer statistics
        """
        # Get item counts
        item_counts = {}
        for level in [ContextLevel.L0, ContextLevel.L1, ContextLevel.L2, ContextLevel.L3]:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COUNT(*) as count FROM context_items WHERE level = ?
                """, (level,))
                item_counts[level] = cursor.fetchone()['count']
        
        # Get cache stats
        cache_stats = self.get_cache_stats()
        
        # Get usage pattern stats
        usage_stats = {}
        for task_type, level_counts in self.usage_pattern.task_types.items():
            total = sum(level_counts.values()) if level_counts else 0
            optimal = self.usage_pattern.get_optimal_level(task_type)
            
            usage_stats[task_type] = {
                'total_usage': total,
                'optimal_level': optimal,
                'level_usage': level_counts,
                'success_rates': {
                    level: self.usage_pattern.layer_success_rates.get(level, 0.0)
                    for level in level_counts.keys()
                },
                'avg_load_times': {
                    level: self.usage_pattern.get_average_load_time(level)
                    for level in level_counts.keys()
                }
            }
        
        # Get preload status
        preload_status = {}
        for level in [ContextLevel.L0, ContextLevel.L1, ContextLevel.L2, ContextLevel.L3]:
            preloaded = self.get_preloaded_layer(level)
            preload_status[level] = {
                'is_preloaded': preloaded is not None,
                'loaded_at': preloaded.get('loaded_at') if preloaded else None,
                'items_count': len(preloaded.get('items', [])) if preloaded else 0
            }
        
        return {
            'item_counts': item_counts,
            'cache_stats': cache_stats,
            'usage_stats': usage_stats,
            'preload_status': preload_status,
            'cache_types': {
                level: ContextLevel.get_cache_type(level)
                for level in [ContextLevel.L0, ContextLevel.L1, ContextLevel.L2, ContextLevel.L3]
            },
            'priorities': {
                level: ContextLevel.get_priority(level)
                for level in [ContextLevel.L0, ContextLevel.L1, ContextLevel.L2, ContextLevel.L3]
            },
            'timestamp': time.time()
        }
