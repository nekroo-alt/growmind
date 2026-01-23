"""
Context Hierarchy Manager - V4 Adaptive Reasoning System

This module implements hierarchical context management for the L4D V4 adaptive reasoning system.
It provides multi-level context access (L0-L3) for granular information retrieval and management.

Context Levels:
- L0 (Immediate): Current action, current state, last error
- L1 (Recent): Last 10 actions, last 5 errors, recent telemetry
- L2 (Session): Session history, task progress, patterns
- L3 (Project): Project state, architecture, long-term patterns
"""

import sqlite3
import json
import gzip
import time
from typing import Optional, Dict, List, Any, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import threading

from v3.core.logging_config import get_logger

logger = get_logger(__name__)


class ContextLevel:
    """Context level enumeration."""
    L0 = "L0"  # Immediate context
    L1 = "L1"  # Recent context
    L2 = "L2"  # Session context
    L3 = "L3"  # Project context


class ContextHierarchyManager:
    """
    Manages hierarchical context storage and retrieval for adaptive reasoning.
    
    Features:
    - Multi-level context storage (L0-L3)
    - TTL-based expiration for L0/L1
    - Context summarization support
    - Context propagation between levels
    - Thread-safe operations
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
    
    def __init__(self, db_path: str = "context_hierarchy.db"):
        """
        Initialize ContextHierarchyManager.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._lock = threading.RLock()
        self._init_database()
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
            
            conn.commit()
            
            logger.debug("Database schema initialized for context hierarchy")
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
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
        Add a context item to the specified level.
        
        Args:
            level: Context level (L0, L1, L2, L3)
            item_type: Type of context item (action, error, state, etc.)
            content: Content dictionary
            metadata: Optional metadata dictionary
            parent_id: Optional parent context item ID
            ttl: Optional time-to-live in seconds (overrides default)
        
        Returns:
            ID of the inserted context item
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
                
                # Clean up old items if limit exceeded
                self._enforce_limit(conn, level)
                
                logger.debug(f"Added context item {item_id} at level {level}")
                return item_id
    
    def get_current_action(self) -> Optional[Dict[str, Any]]:
        """
        Get the current action from L0 context.
        
        Returns:
            Current action context or None if not found
        """
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
                    return self._decompress_data(row['content'])
                else:
                    return json.loads(row['content'])
            return None
    
    def get_recent_actions(self, count: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent actions from L1 context.
        
        Args:
            count: Number of actions to retrieve
        
        Returns:
            List of recent action contexts
        """
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
            
            return actions
    
    def get_session_context(self) -> Dict[str, Any]:
        """
        Get session context from L2.
        
        Returns:
            Session context dictionary with actions, errors, and patterns
        """
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
            
            return {
                'actions': actions,
                'errors': errors,
                'timestamp': time.time()
            }
    
    def get_project_context(self) -> Dict[str, Any]:
        """
        Get project context from L3.
        
        Returns:
            Project context dictionary with state, architecture, and patterns
        """
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
            
            return items
    
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
            ID of the inserted summary
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
                
                logger.debug(f"Stored summary {summary_id} for level {level}")
                return summary_id
    
    def get_summary(
        self,
        level: str,
        summary_type: str = 'detailed'
    ) -> Optional[Dict[str, Any]]:
        """
        Get the latest summary for a given level.
        
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
            
            return {
                'item_counts': level_counts,
                'summary_counts': summary_counts,
                'access_patterns': access_patterns,
                'timestamp': time.time()
            }