"""
Adaptive Heuristics - Task 6.5: Adaptive Heuristics that Improve Over Time

This module implements adaptive heuristics for continuous improvement:
- Start with baseline heuristics
- Update heuristics based on performance data
- Learn optimal weights for decision factors
- Learn optimal thresholds for validation
- Learn optimal context levels per task type
- Learn optimal strategies per situation type

This is a simplified implementation for Task 6.3 self-reflection to use.
Full implementation will be completed in Task 6.5.
"""

import logging
from typing import Dict, Any, Optional, List
import json


class AdaptiveHeuristics:
    """
    Adaptive heuristics that improve over time.
    
    This is a simplified version for Task 6.3.
    Full implementation will include:
    - Bayesian optimization for weight learning
    - Reinforcement learning for strategy policies
    - Gradient descent for scoring function weights
    """
    
    def __init__(self, db_path: str = "v4_adaptive_heuristics.db"):
        """
        Initialize adaptive heuristics system.
        
        Args:
            db_path: Path to SQLite database for heuristic storage
        """
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        
        # Baseline heuristics
        self.baseline_heuristics = {
            'confidence_threshold': 0.7,
            'progress_minimal_threshold': 0.1,
            'progress_expected_threshold': 0.3,
            'loop_threshold': 3,
            'dead_end_threshold': 5,
            'default_strategy': 'balanced'
        }
        
        # Current heuristics (start with baseline)
        self.current_heuristics = self.baseline_heuristics.copy()
        
        # Weighted decision factors
        self.decision_weights = {
            'success_probability': 1.0,
            'cost': 0.5,
            'risk': 0.8,
            'time': 0.3
        }
        
        # Initialize database
        self._init_db()
        
        # Load heuristics from database
        self._load_heuristics()
    
    def _init_db(self):
        """Initialize SQLite database for heuristic storage."""
        import sqlite3
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        
        # Create heuristics table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS heuristics (
                heuristic_name TEXT PRIMARY KEY,
                current_value REAL NOT NULL,
                baseline_value REAL NOT NULL,
                last_updated TEXT,
                update_count INTEGER DEFAULT 0,
                metadata TEXT
            )
        """)
        
        # Create heuristic history table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS heuristic_history (
                id TEXT PRIMARY KEY,
                heuristic_name TEXT NOT NULL,
                old_value REAL NOT NULL,
                new_value REAL NOT NULL,
                reason TEXT,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (heuristic_name) REFERENCES heuristics (heuristic_name)
            )
        """)
        
        # Create decision weights table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS decision_weights (
                weight_name TEXT PRIMARY KEY,
                current_value REAL NOT NULL,
                last_updated TEXT
            )
        """)
        
        # Initialize baseline heuristics in database
        self.conn.execute("""
            INSERT OR IGNORE INTO heuristics 
            (heuristic_name, current_value, baseline_value, last_updated, update_count)
            VALUES 
            ('confidence_threshold', 0.7, 0.7, datetime('now'), 0),
            ('progress_minimal_threshold', 0.1, 0.1, datetime('now'), 0),
            ('progress_expected_threshold', 0.3, 0.3, datetime('now'), 0),
            ('loop_threshold', 3, 3, datetime('now'), 0),
            ('dead_end_threshold', 5, 5, datetime('now'), 0),
            ('default_strategy', 1.0, 1.0, datetime('now'), 0)
        """)
        
        # Initialize decision weights in database
        for name, value in self.decision_weights.items():
            self.conn.execute("""
                INSERT OR IGNORE INTO decision_weights (weight_name, current_value, last_updated)
                VALUES (?, ?, datetime('now'))
            """, (name, value))
        
        self.conn.commit()
    
    def _load_heuristics(self):
        """Load heuristics from database."""
        import sqlite3
        cursor = self.conn.execute("""
            SELECT heuristic_name, current_value FROM heuristics
        """)
        
        for row in cursor.fetchall():
            self.current_heuristics[row['heuristic_name']] = row['current_value']
        
        # Load decision weights
        cursor = self.conn.execute("""
            SELECT weight_name, current_value FROM decision_weights
        """)
        
        for row in cursor.fetchall():
            self.decision_weights[row['weight_name']] = row['current_value']
    
    def update_heuristic(
        self,
        heuristic_name: str,
        new_value: float,
        reason: Optional[str] = None
    ) -> bool:
        """
        Update a heuristic value.
        
        Args:
            heuristic_name: Name of heuristic to update
            new_value: New value for heuristic
            reason: Reason for the update
        
        Returns:
            True if update was successful, False otherwise
        """
        import sqlite3
        
        # Get old value
        cursor = self.conn.execute("""
            SELECT current_value, update_count FROM heuristics
            WHERE heuristic_name = ?
        """, (heuristic_name,))
        
        row = cursor.fetchone()
        if not row:
            self.logger.warning(f"Heuristic not found: {heuristic_name}")
            return False
        
        old_value = row['current_value']
        update_count = row['update_count']
        
        # Check if value has significantly changed (avoid micro-updates)
        if abs(new_value - old_value) < 0.01:
            return True  # No significant change
        
        # Update heuristic
        self.conn.execute("""
            UPDATE heuristics
            SET current_value = ?, last_updated = datetime('now'), update_count = ?
            WHERE heuristic_name = ?
        """, (new_value, update_count + 1, heuristic_name))
        
        # Record history
        import uuid
        self.conn.execute("""
            INSERT INTO heuristic_history 
            (id, heuristic_name, old_value, new_value, reason, timestamp)
            VALUES (?, ?, ?, ?, ?, datetime('now'))
        """, (str(uuid.uuid4()), heuristic_name, old_value, new_value, reason))
        
        self.conn.commit()
        
        # Update in-memory value
        self.current_heuristics[heuristic_name] = new_value
        
        self.logger.info(f"Updated heuristic {heuristic_name}: {old_value:.3f} -> {new_value:.3f}")
        
        return True
    
    def get_heuristic(self, heuristic_name: str, default: float = 0.0) -> float:
        """
        Get current value of a heuristic.
        
        Args:
            heuristic_name: Name of heuristic
            default: Default value if not found
        
        Returns:
            Current heuristic value
        """
        return self.current_heuristics.get(heuristic_name, default)
    
    def get_all_heuristics(self) -> Dict[str, float]:
        """
        Get all current heuristics.
        
        Returns:
            Dictionary of all heuristics
        """
        return self.current_heuristics.copy()
    
    def reset_to_baseline(self, heuristic_name: Optional[str] = None) -> bool:
        """
        Reset heuristics to baseline values.
        
        Args:
            heuristic_name: Specific heuristic to reset (None for all)
        
        Returns:
            True if reset was successful
        """
        import sqlite3
        
        if heuristic_name:
            # Reset specific heuristic
            baseline = self.baseline_heuristics.get(heuristic_name)
            if baseline is not None:
                self.update_heuristic(heuristic_name, baseline, "Reset to baseline")
                return True
            return False
        else:
            # Reset all heuristics
            for name, value in self.baseline_heuristics.items():
                self.update_heuristic(name, value, "Reset to baseline")
            return True
    
    def update_decision_weight(
        self,
        weight_name: str,
        new_value: float,
        reason: Optional[str] = None
    ) -> bool:
        """
        Update a decision weight.
        
        Args:
            weight_name: Name of weight to update
            new_value: New weight value
            reason: Reason for the update
        
        Returns:
            True if update was successful
        """
        import sqlite3
        
        # Get old value
        cursor = self.conn.execute("""
            SELECT current_value FROM decision_weights
            WHERE weight_name = ?
        """, (weight_name,))
        
        row = cursor.fetchone()
        if not row:
            self.logger.warning(f"Decision weight not found: {weight_name}")
            return False
        
        old_value = row['current_value']
        
        # Check if value has significantly changed
        if abs(new_value - old_value) < 0.01:
            return True
        
        # Update weight
        self.conn.execute("""
            UPDATE decision_weights
            SET current_value = ?, last_updated = datetime('now')
            WHERE weight_name = ?
        """, (new_value, weight_name))
        
        self.conn.commit()
        
        # Update in-memory value
        self.decision_weights[weight_name] = new_value
        
        self.logger.info(f"Updated weight {weight_name}: {old_value:.3f} -> {new_value:.3f}")
        
        return True
    
    def get_decision_weight(self, weight_name: str, default: float = 1.0) -> float:
        """
        Get current value of a decision weight.
        
        Args:
            weight_name: Name of weight
            default: Default value if not found
        
        Returns:
            Current weight value
        """
        return self.decision_weights.get(weight_name, default)
    
    def get_all_decision_weights(self) -> Dict[str, float]:
        """
        Get all decision weights.
        
        Returns:
            Dictionary of all decision weights
        """
        return self.decision_weights.copy()
    
    def get_heuristic_history(
        self,
        heuristic_name: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get history of heuristic updates.
        
        Args:
            heuristic_name: Specific heuristic to get history for (None for all)
            limit: Maximum number of history entries
        
        Returns:
            List of history entries
        """
        import sqlite3
        
        if heuristic_name:
            cursor = self.conn.execute("""
                SELECT * FROM heuristic_history
                WHERE heuristic_name = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (heuristic_name, limit))
        else:
            cursor = self.conn.execute("""
                SELECT * FROM heuristic_history
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))
        
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    def get_heuristic_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about heuristics.
        
        Returns:
            Dictionary with heuristic statistics
        """
        import sqlite3
        
        cursor = self.conn.execute("""
            SELECT 
                COUNT(*) as total_heuristics,
                AVG(update_count) as avg_update_count,
                MAX(update_count) as max_update_count
            FROM heuristics
        """)
        
        stats = dict(cursor.fetchone())
        
        # Count heuristics updated recently
        cursor = self.conn.execute("""
            SELECT COUNT(*) as recent_updates
            FROM heuristics
            WHERE last_updated > datetime('now', '-7 days')
        """)
        
        stats['recent_updates'] = cursor.fetchone()['recent_updates']
        
        return stats
    
    def export_heuristics(self) -> str:
        """
        Export current heuristics as JSON.
        
        Returns:
            JSON string of current heuristics
        """
        export_data = {
            "heuristics": self.current_heuristics.copy(),
            "decision_weights": self.decision_weights.copy(),
            "baselines": self.baseline_heuristics.copy(),
            "exported_at": datetime.now().isoformat()
        }
        
        return json.dumps(export_data, indent=2, default=str)
    
    def close(self) -> None:
        """Close database connection."""
        if self.conn:
            self.conn.close()


# Global adaptive heuristics manager instance
_adaptive_heuristics = None
_lock = None


def get_adaptive_heuristics() -> AdaptiveHeuristics:
    """
    Get global adaptive heuristics instance (thread-safe singleton).
    
    Returns:
        AdaptiveHeuristics instance
    """
    global _adaptive_heuristics, _lock
    if _adaptive_heuristics is None:
        import threading
        if _lock is None:
            _lock = threading.Lock()
        
        with _lock:
            if _adaptive_heuristics is None:
                _adaptive_heuristics = AdaptiveHeuristics()
    return _adaptive_heuristics