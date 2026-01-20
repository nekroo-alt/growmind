"""
Telemetry Manager - Task 1.1: Telemetry Data Schema Design

This module implements the telemetry database schema for comprehensive operation tracking.
It includes tables for operations, events, metrics, and resources with hierarchical support.
"""

import sqlite3
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
import json
import os

# Database path
TELEMETRY_DB_PATH = "telemetry.db"


class TelemetryManager:
    """
    Manages telemetry data storage and retrieval for operation tracking.
    """

    def __init__(self, db_path: str = TELEMETRY_DB_PATH):
        """
        Initialize the telemetry manager.
        
        Args:
            db_path: Path to the telemetry database file
        """
        self.db_path = db_path
        self._init_schema()

    def _init_schema(self):
        """
        Initialize the telemetry database schema.
        Creates tables for operations, events, metrics, and resources.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Operations table - tracks hierarchical operations
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS operations (
                    id TEXT PRIMARY KEY,
                    parent_id TEXT,
                    operation_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    status TEXT NOT NULL,
                    start_time DATETIME NOT NULL,
                    end_time DATETIME,
                    metadata TEXT,
                    activity_id INTEGER,
                    FOREIGN KEY (parent_id) REFERENCES operations (id),
                    FOREIGN KEY (activity_id) REFERENCES activity(id)
                )
                """
            )

            # Events table - tracks events within operations
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY,
                    operation_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    timestamp DATETIME NOT NULL,
                    message TEXT,
                    context TEXT,
                    FOREIGN KEY (operation_id) REFERENCES operations (id) ON DELETE CASCADE
                )
                """
            )

            # Metrics table - tracks operation metrics
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS metrics (
                    id TEXT PRIMARY KEY,
                    operation_id TEXT NOT NULL,
                    metric_name TEXT NOT NULL,
                    metric_value REAL NOT NULL,
                    unit TEXT,
                    timestamp DATETIME NOT NULL,
                    FOREIGN KEY (operation_id) REFERENCES operations (id) ON DELETE CASCADE
                )
                """
            )

            # Resources table - tracks resource usage
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS resources (
                    id TEXT PRIMARY KEY,
                    operation_id TEXT NOT NULL,
                    resource_type TEXT NOT NULL,
                    resource_name TEXT,
                    value REAL NOT NULL,
                    unit TEXT,
                    timestamp DATETIME NOT NULL,
                    FOREIGN KEY (operation_id) REFERENCES operations (id) ON DELETE CASCADE
                )
                """
            )

            # Create indexes for fast queries
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_operations_timestamp 
                ON operations(start_time)
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_operations_type_status 
                ON operations(operation_type, status)
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_events_operation 
                ON events(operation_id)
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_events_timestamp 
                ON events(timestamp)
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_metrics_operation 
                ON metrics(operation_id)
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_resources_operation 
                ON resources(operation_id)
                """
            )

            # Create migration tracking table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS migrations (
                    version INTEGER PRIMARY KEY,
                    applied_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    description TEXT
                )
                """
            )

            conn.commit()

    def _get_connection(self):
        """
        Get a database connection with row factory enabled.
        
        Returns:
            SQLite connection object
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # Operation Management

    def start_operation(
        self,
        operation_type: str,
        title: str,
        parent_id: Optional[str] = None,
        activity_id: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Start a new operation and return its ID.
        
        Args:
            operation_type: Type of operation (e.g., 'implementation', 'task_breakdown')
            title: Human-readable title of the operation
            parent_id: ID of parent operation for hierarchy
            activity_id: ID of corresponding activity record
            metadata: Additional metadata as dictionary
            
        Returns:
            Operation ID (UUID string)
        """
        operation_id = str(uuid.uuid4())
        start_time = datetime.utcnow().isoformat()
        metadata_json = json.dumps(metadata) if metadata else None

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO operations 
                (id, parent_id, operation_type, title, status, start_time, metadata, activity_id)
                VALUES (?, ?, ?, ?, 'started', ?, ?, ?)
                """,
                (operation_id, parent_id, operation_type, title, start_time, metadata_json, activity_id)
            )
            conn.commit()

        return operation_id

    def end_operation(
        self,
        operation_id: str,
        status: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        End an operation with a status.
        
        Args:
            operation_id: ID of the operation to end
            status: Final status ('completed', 'failed', 'interrupted')
            metadata: Optional metadata to add at end
        """
        end_time = datetime.utcnow().isoformat()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            if metadata:
                cursor.execute(
                    """
                    SELECT metadata FROM operations WHERE id = ?
                    """,
                    (operation_id,)
                )
                row = cursor.fetchone()
                if row and row["metadata"]:
                    existing_metadata = json.loads(row["metadata"])
                    existing_metadata.update(metadata)
                    metadata_json = json.dumps(existing_metadata)
                else:
                    metadata_json = json.dumps(metadata)
                
                cursor.execute(
                    """
                    UPDATE operations 
                    SET status = ?, end_time = ?, metadata = ?
                    WHERE id = ?
                    """,
                    (status, end_time, metadata_json, operation_id)
                )
            else:
                cursor.execute(
                    """
                    UPDATE operations 
                    SET status = ?, end_time = ?
                    WHERE id = ?
                    """,
                    (status, end_time, operation_id)
                )
            
            conn.commit()

    def cancel_operation(self, operation_id: str):
        """
        Cancel an ongoing operation.
        
        Args:
            operation_id: ID of the operation to cancel
        """
        self.end_operation(operation_id, "cancelled")

    def get_operation(self, operation_id: str) -> Optional[Dict[str, Any]]:
        """
        Get operation details by ID.
        
        Args:
            operation_id: ID of the operation
            
        Returns:
            Dictionary with operation details or None if not found
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM operations WHERE id = ?
                """,
                (operation_id,)
            )
            row = cursor.fetchone()
            
            if row:
                operation = dict(row)
                if operation["metadata"]:
                    operation["metadata"] = json.loads(operation["metadata"])
                return operation
            return None

    def list_operations(
        self,
        operation_type: Optional[str] = None,
        status: Optional[str] = None,
        parent_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        List operations with optional filters.
        
        Args:
            operation_type: Filter by operation type
            status: Filter by status
            parent_id: Filter by parent operation ID
            limit: Maximum number of operations to return
            
        Returns:
            List of operation dictionaries
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM operations WHERE 1=1"
            params = []
            
            if operation_type:
                query += " AND operation_type = ?"
                params.append(operation_type)
            
            if status:
                query += " AND status = ?"
                params.append(status)
            
            if parent_id:
                query += " AND parent_id = ?"
                params.append(parent_id)
            
            query += " ORDER BY start_time DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            operations = []
            for row in rows:
                operation = dict(row)
                if operation["metadata"]:
                    operation["metadata"] = json.loads(operation["metadata"])
                operations.append(operation)
            
            return operations

    def get_child_operations(self, parent_id: str) -> List[Dict[str, Any]]:
        """
        Get all child operations of a parent operation.
        
        Args:
            parent_id: ID of parent operation
            
        Returns:
            List of child operation dictionaries
        """
        return self.list_operations(parent_id=parent_id, limit=1000)

    # Event Management

    def record_event(
        self,
        operation_id: str,
        event_type: str,
        severity: str,
        message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Record an event for an operation.
        
        Args:
            operation_id: ID of the operation
            event_type: Type of event ('started', 'completed', 'failed', etc.)
            severity: Event severity ('info', 'warning', 'error', 'critical')
            message: Event message
            context: Additional context as dictionary
            
        Returns:
            Event ID (UUID string)
        """
        event_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()
        context_json = json.dumps(context) if context else None

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO events 
                (id, operation_id, event_type, severity, timestamp, message, context)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (event_id, operation_id, event_type, severity, timestamp, message, context_json)
            )
            conn.commit()

        return event_id

    def get_operation_events(self, operation_id: str) -> List[Dict[str, Any]]:
        """
        Get all events for an operation.
        
        Args:
            operation_id: ID of the operation
            
        Returns:
            List of event dictionaries ordered by timestamp
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM events WHERE operation_id = ? ORDER BY timestamp ASC
                """,
                (operation_id,)
            )
            rows = cursor.fetchall()
            
            events = []
            for row in rows:
                event = dict(row)
                if event["context"]:
                    event["context"] = json.loads(event["context"])
                events.append(event)
            
            return events

    # Metrics Management

    def record_metric(
        self,
        operation_id: str,
        metric_name: str,
        metric_value: float,
        unit: Optional[str] = None
    ) -> str:
        """
        Record a metric for an operation.
        
        Args:
            operation_id: ID of the operation
            metric_name: Name of the metric ('tokens_used', 'time_elapsed', etc.)
            metric_value: Value of the metric
            unit: Unit of measurement (e.g., 'seconds', 'tokens', 'MB')
            
        Returns:
            Metric ID (UUID string)
        """
        metric_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO metrics 
                (id, operation_id, metric_name, metric_value, unit, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (metric_id, operation_id, metric_name, metric_value, unit, timestamp)
            )
            conn.commit()

        return metric_id

    def get_operation_metrics(self, operation_id: str) -> List[Dict[str, Any]]:
        """
        Get all metrics for an operation.
        
        Args:
            operation_id: ID of the operation
            
        Returns:
            List of metric dictionaries
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM metrics WHERE operation_id = ? ORDER BY timestamp ASC
                """,
                (operation_id,)
            )
            rows = cursor.fetchall()
            
            return [dict(row) for row in rows]

    def get_metric_summary(
        self,
        operation_id: str,
        metric_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get summary statistics for a specific metric.
        
        Args:
            operation_id: ID of the operation
            metric_name: Name of the metric
            
        Returns:
            Dictionary with count, sum, avg, min, max or None if no metrics found
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT 
                    COUNT(*) as count,
                    SUM(metric_value) as total,
                    AVG(metric_value) as avg,
                    MIN(metric_value) as min,
                    MAX(metric_value) as max
                FROM metrics 
                WHERE operation_id = ? AND metric_name = ?
                """,
                (operation_id, metric_name)
            )
            row = cursor.fetchone()
            
            if row and row["count"] > 0:
                return dict(row)
            return None

    # Resource Management

    def record_resource_usage(
        self,
        operation_id: str,
        resource_type: str,
        value: float,
        unit: str,
        resource_name: Optional[str] = None
    ) -> str:
        """
        Record resource usage for an operation.
        
        Args:
            operation_id: ID of the operation
            resource_type: Type of resource ('cpu', 'memory', 'disk', 'network')
            value: Resource value
            unit: Unit of measurement (e.g., '%', 'MB', 'MB/s')
            resource_name: Optional name for the resource
            
        Returns:
            Resource ID (UUID string)
        """
        resource_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO resources 
                (id, operation_id, resource_type, resource_name, value, unit, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (resource_id, operation_id, resource_type, resource_name, value, unit, timestamp)
            )
            conn.commit()

        return resource_id

    def get_operation_resources(self, operation_id: str) -> List[Dict[str, Any]]:
        """
        Get all resource usage records for an operation.
        
        Args:
            operation_id: ID of the operation
            
        Returns:
            List of resource dictionaries ordered by timestamp
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM resources WHERE operation_id = ? ORDER BY timestamp ASC
                """,
                (operation_id,)
            )
            rows = cursor.fetchall()
            
            return [dict(row) for row in rows]

    # Migration Management

    def apply_migration(self, version: int, description: str, migration_sql: str):
        """
        Apply a database migration.
        
        Args:
            version: Migration version number
            description: Human-readable description of migration
            migration_sql: SQL to execute for the migration
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if migration already applied
            cursor.execute(
                "SELECT 1 FROM migrations WHERE version = ?",
                (version,)
            )
            if cursor.fetchone():
                return  # Already applied
            
            # Execute migration
            cursor.executescript(migration_sql)
            
            # Record migration
            cursor.execute(
                """
                INSERT INTO migrations (version, description)
                VALUES (?, ?)
                """,
                (version, description)
            )
            
            conn.commit()

    def get_migration_version(self) -> int:
        """
        Get the current migration version.
        
        Returns:
            Highest migration version applied
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(version) FROM migrations")
            row = cursor.fetchone()
            return row[0] if row[0] else 0


# Global telemetry manager instance
_telemetry_manager = None


def get_telemetry_manager() -> TelemetryManager:
    """
    Get the global telemetry manager instance.
    
    Returns:
        TelemetryManager instance
    """
    global _telemetry_manager
    if _telemetry_manager is None:
        _telemetry_manager = TelemetryManager()
    return _telemetry_manager
