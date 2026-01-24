"""
Decision Trace Logging Module for L4D V4

This module provides comprehensive decision trace logging and querying capabilities
for decision explainability and analysis.
"""

import json
import sqlite3
import threading
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.telemetry_manager import TelemetryManager


class DecisionTracer:
    """
    Manages decision trace logging and querying for explainability.
    
    This class provides comprehensive logging of all decisions with full reasoning
    chains, context snapshots, alternatives considered, and resources consumed.
    It also provides powerful query and export capabilities.
    """
    
    def __init__(self, db_path: str = "decision_traces.db", telemetry_manager: Optional[TelemetryManager] = None):
        """
        Initialize DecisionTracer.
        
        Args:
            db_path: Path to SQLite database
            telemetry_manager: Optional TelemetryManager for correlation
        """
        self.db_path = db_path
        self.telemetry_manager = telemetry_manager
        self._lock = threading.RLock()
        self._init_database()
    
    def _init_database(self) -> None:
        """Initialize SQLite database with required tables."""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Main decision traces table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS decision_traces (
                    decision_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    operation_id TEXT,
                    task_id INTEGER,
                    context_snapshot TEXT,
                    reasoning_chain TEXT,
                    alternatives TEXT,
                    selected_action TEXT,
                    confidence REAL,
                    resources TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Full-text search table for context
            cursor.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS decision_fts 
                USING fts5(decision_id, reasoning_chain, selected_action)
            """)
            
            # Create triggers to keep FTS in sync
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS decision_traces_ai AFTER INSERT ON decision_traces BEGIN
                    INSERT INTO decision_fts(decision_id, reasoning_chain, selected_action)
                    VALUES (NEW.decision_id, NEW.reasoning_chain, NEW.selected_action);
                END
            """)
            
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS decision_traces_ad AFTER DELETE ON decision_traces BEGIN
                    DELETE FROM decision_fts WHERE decision_id = OLD.decision_id;
                END
            """)
            
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS decision_traces_au AFTER UPDATE ON decision_traces BEGIN
                    UPDATE decision_fts SET reasoning_chain = NEW.reasoning_chain, selected_action = NEW.selected_action
                    WHERE decision_id = NEW.decision_id;
                END
            """)
            
            # Create indexes for common queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_decision_timestamp 
                ON decision_traces(timestamp)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_decision_operation_id 
                ON decision_traces(operation_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_decision_task_id 
                ON decision_traces(task_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_decision_confidence 
                ON decision_traces(confidence)
            """)
            
            conn.commit()
            conn.close()
    
    def log_decision(
        self,
        operation_id: str,
        task_id: Optional[int] = None,
        context_snapshot: Optional[Dict[str, Any]] = None,
        reasoning_chain: Optional[List[Dict[str, Any]]] = None,
        alternatives: Optional[List[Dict[str, str]]] = None,
        selected_action: Optional[str] = None,
        confidence: Optional[float] = None,
        resources: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Log a complete decision trace.
        
        Args:
            operation_id: Associated operation ID from telemetry
            task_id: Optional task ID
            context_snapshot: Context at decision point
            reasoning_chain: List of reasoning steps with thoughts and conclusions
            alternatives: List of alternative actions with rejection reasons
            selected_action: The action that was selected
            confidence: Confidence level (0.0 to 1.0)
            resources: Optional resource consumption metrics
        
        Returns:
            decision_id: Unique ID for the logged decision
        """
        decision_id = str(uuid4())
        timestamp = datetime.utcnow().isoformat()
        
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO decision_traces (
                    decision_id, timestamp, operation_id, task_id,
                    context_snapshot, reasoning_chain, alternatives,
                    selected_action, confidence, resources
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                decision_id,
                timestamp,
                operation_id,
                task_id,
                json.dumps(context_snapshot or {}),
                json.dumps(reasoning_chain or []),
                json.dumps(alternatives or []),
                selected_action,
                confidence,
                json.dumps(resources or {})
            ))
            
            conn.commit()
            conn.close()
        
        # Log to telemetry if available
        if self.telemetry_manager and selected_action is not None:
            self.telemetry_manager.record_event(
                "decision_logged",
                {
                    "decision_id": decision_id,
                    "operation_id": operation_id,
                    "action": selected_action,
                    "confidence": confidence
                }
            )
        
        return decision_id
    
    def trace_decision(self, decision_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve full decision trace by ID.
        
        Args:
            decision_id: Decision ID to retrieve
        
        Returns:
            Full decision trace or None if not found
        """
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT decision_id, timestamp, operation_id, task_id,
                       context_snapshot, reasoning_chain, alternatives,
                       selected_action, confidence, resources
                FROM decision_traces
                WHERE decision_id = ?
            """, (decision_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                return None
            
            return self._row_to_dict(cursor, row)
    
    def search(
        self,
        task_id: Optional[int] = None,
        operation_id: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        min_confidence: Optional[float] = None,
        max_confidence: Optional[float] = None,
        action_pattern: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Search decisions with multiple filters.
        
        Args:
            task_id: Filter by task ID
            operation_id: Filter by operation ID
            start_time: Start of time range (ISO format)
            end_time: End of time range (ISO format)
            min_confidence: Minimum confidence threshold
            max_confidence: Maximum confidence threshold
            action_pattern: Pattern to match in selected_action
            limit: Maximum number of results
        
        Returns:
            List of matching decisions
        """
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Build query dynamically
            conditions = []
            params = []
            
            if task_id is not None:
                conditions.append("task_id = ?")
                params.append(task_id)
            
            if operation_id is not None:
                conditions.append("operation_id = ?")
                params.append(operation_id)
            
            if start_time is not None:
                conditions.append("timestamp >= ?")
                params.append(start_time)
            
            if end_time is not None:
                conditions.append("timestamp <= ?")
                params.append(end_time)
            
            if min_confidence is not None:
                conditions.append("confidence >= ?")
                params.append(min_confidence)
            
            if max_confidence is not None:
                conditions.append("confidence <= ?")
                params.append(max_confidence)
            
            if action_pattern:
                conditions.append("selected_action LIKE ?")
                params.append(f"%{action_pattern}%")
            
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            cursor.execute(f"""
                SELECT decision_id, timestamp, operation_id, task_id,
                       context_snapshot, reasoning_chain, alternatives,
                       selected_action, confidence, resources
                FROM decision_traces
                WHERE {where_clause}
                ORDER BY timestamp DESC
                LIMIT ?
            """, params + [limit])
            
            rows = cursor.fetchall()
            conn.close()
            
            return [self._row_to_dict(cursor, row) for row in rows]
    
    def search_context(
        self,
        context_key: str,
        context_value: Any,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Search decisions by context pattern.
        
        Args:
            context_key: Key in context to search
            context_value: Value to match (can use LIKE pattern)
            limit: Maximum number of results
        
        Returns:
            List of matching decisions
        """
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Search in JSON context_snapshot
            cursor.execute("""
                SELECT decision_id, timestamp, operation_id, task_id,
                       context_snapshot, reasoning_chain, alternatives,
                       selected_action, confidence, resources
                FROM decision_traces
                WHERE context_snapshot LIKE ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (f'%"{context_key}": "{context_value}"%', limit))
            
            rows = cursor.fetchall()
            conn.close()
            
            return [self._row_to_dict(cursor, row) for row in rows]
    
    def search_reasoning(
        self,
        reasoning_keyword: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Search decisions by reasoning keywords using full-text search.
        
        Args:
            reasoning_keyword: Keyword to search in reasoning chain
            limit: Maximum number of results
        
        Returns:
            List of matching decisions
        """
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Use FTS for efficient text search
            cursor.execute("""
                SELECT dt.decision_id, dt.timestamp, dt.operation_id, dt.task_id,
                       dt.context_snapshot, dt.reasoning_chain, dt.alternatives,
                       dt.selected_action, dt.confidence, dt.resources
                FROM decision_traces dt
                JOIN decision_fts fts ON dt.decision_id = fts.decision_id
                WHERE decision_fts MATCH ?
                ORDER BY dt.timestamp DESC
                LIMIT ?
            """, (reasoning_keyword, limit))
            
            rows = cursor.fetchall()
            conn.close()
            
            return [self._row_to_dict(cursor, row) for row in rows]
    
    def get_last_decision(
        self,
        operation_id: Optional[str] = None,
        task_id: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get the most recent decision.
        
        Args:
            operation_id: Optional operation ID filter
            task_id: Optional task ID filter
        
        Returns:
            Most recent decision or None
        """
        results = self.search(
            operation_id=operation_id,
            task_id=task_id,
            limit=1
        )
        
        return results[0] if results else None
    
    def export_traces(
        self,
        decisions: List[Dict[str, Any]],
        format: str = "json",
        file_path: Optional[str] = None
    ) -> str:
        """
        Export decision traces to file or string.
        
        Args:
            decisions: List of decisions to export
            format: Export format ('json' or 'csv')
            file_path: Optional file path to save to
        
        Returns:
            Exported data as string
        """
        if format.lower() == "json":
            data = json.dumps(decisions, indent=2, default=str)
        elif format.lower() == "csv":
            # Simple CSV export (flattened)
            import csv
            from io import StringIO
            
            output = StringIO()
            fieldnames = [
                'decision_id', 'timestamp', 'operation_id', 'task_id',
                'selected_action', 'confidence'
            ]
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            
            for decision in decisions:
                row = {k: decision.get(k) for k in fieldnames}
                writer.writerow(row)
            
            data = output.getvalue()
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        if file_path:
            with open(file_path, 'w') as f:
                f.write(data)
        
        return data
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get decision trace statistics.
        
        Returns:
            Dictionary with statistics
        """
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Total decisions
            cursor.execute("SELECT COUNT(*) FROM decision_traces")
            total = cursor.fetchone()[0]
            
            # Average confidence
            cursor.execute("SELECT AVG(confidence) FROM decision_traces")
            avg_confidence = cursor.fetchone()[0] or 0.0
            
            # Confidence distribution
            cursor.execute("""
                SELECT 
                    COUNT(CASE WHEN confidence >= 0.9 THEN 1 END) as high,
                    COUNT(CASE WHEN confidence >= 0.7 AND confidence < 0.9 THEN 1 END) as medium,
                    COUNT(CASE WHEN confidence < 0.7 THEN 1 END) as low
                FROM decision_traces
            """)
            row = cursor.fetchone()
            confidence_dist = {
                'high': row[0],
                'medium': row[1],
                'low': row[2]
            }
            
            # Decisions per task
            cursor.execute("""
                SELECT task_id, COUNT(*) as count
                FROM decision_traces
                WHERE task_id IS NOT NULL
                GROUP BY task_id
                ORDER BY count DESC
                LIMIT 10
            """)
            top_tasks = [{'task_id': row[0], 'decisions': row[1]} for row in cursor.fetchall()]
            
            conn.close()
        
        return {
            'total_decisions': total,
            'average_confidence': avg_confidence,
            'confidence_distribution': confidence_dist,
            'top_tasks': top_tasks
        }
    
    def delete_old_traces(self, days: int = 30) -> int:
        """
        Delete decision traces older than specified days.
        
        Args:
            days: Number of days to keep
        
        Returns:
            Number of traces deleted
        """
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cutoff_date = (datetime.utcnow() - timedelta(days=days)).isoformat()
            
            cursor.execute("""
                DELETE FROM decision_traces
                WHERE timestamp < ?
            """, (cutoff_date,))
            
            deleted = cursor.rowcount
            conn.commit()
            conn.close()
        
        return deleted
    
    def _row_to_dict(self, cursor: sqlite3.Cursor, row: sqlite3.Row) -> Dict[str, Any]:
        """Convert database row to dictionary."""
        columns = [description[0] for description in cursor.description]
        return {
            columns[0]: row[0],  # decision_id
            columns[1]: row[1],  # timestamp
            columns[2]: row[2],  # operation_id
            columns[3]: row[3],  # task_id
            columns[4]: json.loads(row[4]) if row[4] else {},  # context_snapshot
            columns[5]: json.loads(row[5]) if row[5] else [],  # reasoning_chain
            columns[6]: json.loads(row[6]) if row[6] else [],  # alternatives
            columns[7]: row[7],  # selected_action
            columns[8]: row[8],  # confidence
            columns[9]: json.loads(row[9]) if row[9] else {}   # resources
        }


# Global instance for easy access
_global_tracer: Optional[DecisionTracer] = None


def get_tracer(db_path: str = "decision_traces.db", telemetry_manager: Optional[TelemetryManager] = None) -> DecisionTracer:
    """
    Get or create global DecisionTracer instance.
    
    Args:
        db_path: Path to SQLite database
        telemetry_manager: Optional TelemetryManager
    
    Returns:
        DecisionTracer instance
    """
    global _global_tracer
    
    if _global_tracer is None:
        _global_tracer = DecisionTracer(db_path, telemetry_manager)
    
    return _global_tracer