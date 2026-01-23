"""
Telemetry Manager - Task 1.1 & 1.2: Telemetry Data Schema & Manager Implementation

This module implements the telemetry database schema for comprehensive operation tracking.
It includes tables for operations, events, metrics, and resources with hierarchical support.

Task 1.2 Features:
- Context manager API for automatic operation tracking
- Decorator support for function tracking
- Thread-safe operations for concurrent access
- Auto-capture timing and resource usage
- Query interface for analytics and debugging

Task 1.5 Features:
- CPU usage monitoring with psutil
- Memory usage and allocation tracking
- Disk I/O and space monitoring
- Network usage tracking
- Alerting for resource exhaustion
- Resource usage reports

Task 2.3 Features:
- Log-telemetry correlation
- Log reference tracking
- Operation timeline generation
- Log query by operation and task
"""

import sqlite3
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any, Callable
import json
import os
import threading
import functools
import time
from contextlib import contextmanager
from dataclasses import dataclass
from collections import defaultdict

# Try to import psutil for resource monitoring
try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    psutil = None

# Database path
TELEMETRY_DB_PATH = "telemetry.db"


class TelemetryManager:
    """
    Manages telemetry data storage and retrieval for operation tracking.

    Features:
    - Thread-safe operations using locks
    - Context manager API for automatic tracking
    - Decorator support for function tracking
    - Auto-capture timing and metrics
    - Query interface for analytics
    - Log-telemetry correlation (Task 2.3)
    """

    def __init__(self, db_path: str = TELEMETRY_DB_PATH):
        """
        Initialize the telemetry manager.

        Args:
            db_path: Path to the telemetry database file
        """
        self.db_path = db_path
        self._lock = threading.RLock()  # Reentrant lock for thread safety
        self._operation_stack = []  # Track active operations for auto-timing
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

            # File operations table - tracks file I/O operations (Task 1.4)
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS file_operations (
                    id TEXT PRIMARY KEY,
                    operation_id TEXT NOT NULL,
                    operation_type TEXT NOT NULL,
                    file_path TEXT,
                    file_size INTEGER,
                    content_hash TEXT,
                    diff_summary TEXT,
                    timestamp DATETIME NOT NULL,
                    metadata TEXT,
                    FOREIGN KEY (operation_id) REFERENCES operations (id) ON DELETE CASCADE
                )
                """
            )

            # Log references table (Task 2.3) - Correlates logs with telemetry
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS log_references (
                    id TEXT PRIMARY KEY,
                    operation_id TEXT NOT NULL,
                    log_level TEXT NOT NULL,
                    logger_name TEXT,
                    message TEXT,
                    timestamp DATETIME NOT NULL,
                    log_data TEXT,
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
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_file_operations_operation 
                ON file_operations(operation_id)
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_file_operations_path 
                ON file_operations(file_path)
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_file_operations_timestamp 
                ON file_operations(timestamp)
                """
            )

            # Create indexes for log references (Task 2.3)
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_log_references_operation 
                ON log_references(operation_id)
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_log_references_timestamp 
                ON log_references(timestamp)
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_log_references_level 
                ON log_references(log_level)
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
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    # Operation Management

    def start_operation(
        self,
        operation_type: str,
        title: str,
        parent_id: Optional[str] = None,
        activity_id: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
        auto_track: bool = True,
    ) -> str:
        """
        Start a new operation and return its ID.

        Args:
            operation_type: Type of operation (e.g., 'implementation', 'task_breakdown')
            title: Human-readable title of the operation
            parent_id: ID of parent operation for hierarchy
            activity_id: ID of corresponding activity record
            metadata: Additional metadata as dictionary
            auto_track: If True, automatically track timing for this operation

        Returns:
            Operation ID (UUID string)
        """
        with self._lock:
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
                    (
                        operation_id,
                        parent_id,
                        operation_type,
                        title,
                        start_time,
                        metadata_json,
                        activity_id,
                    ),
                )
                conn.commit()

            # Track operation for auto-timing
            if auto_track:
                self._operation_stack.append(
                    {
                        "id": operation_id,
                        "start_time": time.time(),
                        "type": operation_type,
                    }
                )

            return operation_id

    def end_operation(
        self, operation_id: str, status: str, metadata: Optional[Dict[str, Any]] = None
    ):
        """
        End an operation with a status.

        Args:
            operation_id: ID of the operation to end
            status: Final status ('completed', 'failed', 'interrupted')
            metadata: Optional metadata to add at end
        """
        with self._lock:
            end_time = datetime.utcnow().isoformat()

            # Calculate duration if auto-tracked
            elapsed_time = None
            for i, op in enumerate(self._operation_stack):
                if op["id"] == operation_id:
                    elapsed_time = time.time() - op["start_time"]
                    self._operation_stack.pop(i)
                    break

            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Auto-record time_elapsed metric
                if elapsed_time is not None:
                    self.record_metric(
                        operation_id, "time_elapsed", elapsed_time, "seconds"
                    )

                if metadata:
                    cursor.execute(
                        """
                        SELECT metadata FROM operations WHERE id = ?
                        """,
                        (operation_id,),
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
                        (status, end_time, metadata_json, operation_id),
                    )
                else:
                    cursor.execute(
                        """
                        UPDATE operations 
                        SET status = ?, end_time = ?
                        WHERE id = ?
                        """,
                        (status, end_time, operation_id),
                    )

                conn.commit()

    def cancel_operation(self, operation_id: str):
        """
        Cancel an ongoing operation.

        Args:
            operation_id: ID of the operation to cancel
        """
        with self._lock:
            self.end_operation(operation_id, "cancelled")

    def get_operation(self, operation_id: str) -> Optional[Dict[str, Any]]:
        """
        Get operation details by ID.

        Args:
            operation_id: ID of the operation

        Returns:
            Dictionary with operation details or None if not found
        """
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT * FROM operations WHERE id = ?
                    """,
                    (operation_id,),
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
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        List operations with optional filters.

        Args:
            operation_type: Filter by operation type
            status: Filter by status
            parent_id: Filter by parent operation ID
            limit: Maximum number of operations to return
            offset: Number of operations to skip (for pagination)

        Returns:
            List of operation dictionaries
        """
        with self._lock:
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

                query += " ORDER BY start_time DESC LIMIT ? OFFSET ?"
                params.extend([limit, offset])

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
        with self._lock:
            return self.list_operations(parent_id=parent_id, limit=1000)

    # Event Management

    def record_event(
        self,
        operation_id: str,
        event_type: str,
        severity: str,
        message: str,
        context: Optional[Dict[str, Any]] = None,
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
        with self._lock:
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
                    (
                        event_id,
                        operation_id,
                        event_type,
                        severity,
                        timestamp,
                        message,
                        context_json,
                    ),
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
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT * FROM events WHERE operation_id = ? ORDER BY timestamp ASC
                    """,
                    (operation_id,),
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
        unit: Optional[str] = None,
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
        with self._lock:
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
                    (
                        metric_id,
                        operation_id,
                        metric_name,
                        metric_value,
                        unit,
                        timestamp,
                    ),
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
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT * FROM metrics WHERE operation_id = ? ORDER BY timestamp ASC
                    """,
                    (operation_id,),
                )
                rows = cursor.fetchall()

                return [dict(row) for row in rows]

    def get_metric_summary(
        self, operation_id: str, metric_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get summary statistics for a specific metric.

        Args:
            operation_id: ID of the operation
            metric_name: Name of the metric

        Returns:
            Dictionary with count, sum, avg, min, max or None if no metrics found
        """
        with self._lock:
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
                    (operation_id, metric_name),
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
        resource_name: Optional[str] = None,
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
        with self._lock:
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
                    (
                        resource_id,
                        operation_id,
                        resource_type,
                        resource_name,
                        value,
                        unit,
                        timestamp,
                    ),
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
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT * FROM resources WHERE operation_id = ? ORDER BY timestamp ASC
                    """,
                    (operation_id,),
                )
                rows = cursor.fetchall()

                return [dict(row) for row in rows]

    # Log-Telemetry Integration (Task 2.3)

    def record_log_reference(
        self,
        operation_id: str,
        log_level: str,
        logger_name: str,
        message: str,
        log_data: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Record a log reference for an operation.

        This enables querying logs by operation and generating operation timelines.

        Args:
            operation_id: ID of the operation
            log_level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            logger_name: Name of the logger
            message: Log message
            log_data: Additional log data (context, exception info, etc.)

        Returns:
            Log reference ID (UUID string)
        """
        with self._lock:
            log_ref_id = str(uuid.uuid4())
            timestamp = datetime.utcnow().isoformat()
            log_data_json = json.dumps(log_data) if log_data else None

            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO log_references 
                    (id, operation_id, log_level, logger_name, message, timestamp, log_data)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        log_ref_id,
                        operation_id,
                        log_level,
                        logger_name,
                        message,
                        timestamp,
                        log_data_json,
                    ),
                )
                conn.commit()

            return log_ref_id

    def get_operation_logs(
        self, operation_id: str, log_level: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all log references for an operation.

        Args:
            operation_id: ID of the operation
            log_level: Optional filter by log level

        Returns:
            List of log reference dictionaries ordered by timestamp
        """
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                query = "SELECT * FROM log_references WHERE operation_id = ?"
                params = [operation_id]

                if log_level:
                    query += " AND log_level = ?"
                    params.append(log_level)

                query += " ORDER BY timestamp ASC"

                cursor.execute(query, params)
                rows = cursor.fetchall()

                logs = []
                for row in rows:
                    log_ref = dict(row)
                    if log_ref["log_data"]:
                        log_ref["log_data"] = json.loads(log_ref["log_data"])
                    logs.append(log_ref)

                return logs

    def get_logs_by_task(
        self, task_id: int, log_level: Optional[str] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get all log references for operations associated with a task.

        Args:
            task_id: Task ID to query logs for
            log_level: Optional filter by log level
            limit: Maximum number of logs to return

        Returns:
            List of log reference dictionaries ordered by timestamp
        """
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                query = """
                    SELECT lr.* 
                    FROM log_references lr
                    INNER JOIN operations op ON lr.operation_id = op.id
                    WHERE op.metadata LIKE ?
                """
                params = [f'%"{task_id}"%']

                if log_level:
                    query += " AND lr.log_level = ?"
                    params.append(log_level)

                query += " ORDER BY lr.timestamp DESC LIMIT ?"
                params.append(limit)

                cursor.execute(query, params)
                rows = cursor.fetchall()

                logs = []
                for row in rows:
                    log_ref = dict(row)
                    if log_ref["log_data"]:
                        log_ref["log_data"] = json.loads(log_ref["log_data"])
                    logs.append(log_ref)

                return logs

    def search_logs(
        self,
        message_contains: Optional[str] = None,
        log_level: Optional[str] = None,
        logger_name: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Search log references by various criteria.

        Args:
            message_contains: Filter by message content
            log_level: Filter by log level
            logger_name: Filter by logger name
            start_time: Start time filter (ISO format)
            end_time: End time filter (ISO format)
            limit: Maximum results

        Returns:
            List of log reference dictionaries ordered by timestamp
        """
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                query = "SELECT * FROM log_references WHERE 1=1"
                params = []

                if message_contains:
                    query += " AND message LIKE ?"
                    params.append(f"%{message_contains}%")

                if log_level:
                    query += " AND log_level = ?"
                    params.append(log_level)

                if logger_name:
                    query += " AND logger_name = ?"
                    params.append(logger_name)

                if start_time:
                    query += " AND timestamp >= ?"
                    params.append(start_time)

                if end_time:
                    query += " AND timestamp <= ?"
                    params.append(end_time)

                query += " ORDER BY timestamp DESC LIMIT ?"
                params.append(limit)

                cursor.execute(query, params)
                rows = cursor.fetchall()

                logs = []
                for row in rows:
                    log_ref = dict(row)
                    if log_ref["log_data"]:
                        log_ref["log_data"] = json.loads(log_ref["log_data"])
                    logs.append(log_ref)

                return logs

    def generate_operation_timeline(
        self,
        operation_id: str,
        include_telemetry: bool = True,
        include_logs: bool = True,
    ) -> Dict[str, Any]:
        """
        Generate a timeline of events for an operation.

        Combines telemetry events, metrics, and log references into a unified timeline.

        Args:
            operation_id: ID of the operation
            include_telemetry: Include telemetry events and metrics
            include_logs: Include log references

        Returns:
            Dictionary with operation details and timeline of events
        """
        with self._lock:
            # Get operation details
            operation = self.get_operation(operation_id)
            if not operation:
                return {"error": "Operation not found"}

            timeline_events = []

            # Add telemetry events
            if include_telemetry:
                events = self.get_operation_events(operation_id)
                for event in events:
                    timeline_events.append(
                        {
                            "type": "telemetry_event",
                            "timestamp": event["timestamp"],
                            "event_type": event["event_type"],
                            "severity": event["severity"],
                            "message": event["message"],
                            "context": event.get("context"),
                        }
                    )

                metrics = self.get_operation_metrics(operation_id)
                for metric in metrics:
                    timeline_events.append(
                        {
                            "type": "telemetry_metric",
                            "timestamp": metric["timestamp"],
                            "metric_name": metric["metric_name"],
                            "metric_value": metric["metric_value"],
                            "unit": metric.get("unit"),
                        }
                    )

            # Add log references
            if include_logs:
                logs = self.get_operation_logs(operation_id)
                for log in logs:
                    timeline_events.append(
                        {
                            "type": "log",
                            "timestamp": log["timestamp"],
                            "log_level": log["log_level"],
                            "logger_name": log["logger_name"],
                            "message": log["message"],
                            "data": log.get("log_data"),
                        }
                    )

            # Sort timeline by timestamp
            timeline_events.sort(key=lambda x: x["timestamp"])

            return {
                "operation_id": operation_id,
                "operation_type": operation.get("operation_type"),
                "operation_title": operation.get("title"),
                "operation_status": operation.get("status"),
                "operation_start": operation.get("start_time"),
                "operation_end": operation.get("end_time"),
                "timeline": timeline_events,
                "event_count": len(timeline_events),
            }

    def export_operation_with_logs(
        self, operation_id: str, format: str = "json"
    ) -> Dict[str, Any]:
        """
        Export operation data with associated logs for analysis.

        Args:
            operation_id: ID of the operation
            format: Export format ('json' or 'dict')

        Returns:
            Dictionary with complete operation data including logs
        """
        with self._lock:
            # Get operation details
            operation = self.get_operation(operation_id)
            if not operation:
                return {"error": "Operation not found"}

            # Get all related data
            events = self.get_operation_events(operation_id)
            metrics = self.get_operation_metrics(operation_id)
            resources = self.get_operation_resources(operation_id)
            logs = self.get_operation_logs(operation_id)
            child_ops = self.get_child_operations(operation_id)

            export_data = {
                "operation": operation,
                "events": events,
                "metrics": metrics,
                "resources": resources,
                "logs": logs,
                "child_operations": child_ops,
                "exported_at": datetime.utcnow().isoformat(),
            }

            if format == "json":
                return json.dumps(export_data, indent=2, default=str)
            else:
                return export_data

    def get_log_statistics(
        self,
        operation_id: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get statistics about logs for an operation or time range.

        Args:
            operation_id: Optional operation ID to filter by
            start_time: Optional start time filter
            end_time: Optional end time filter

        Returns:
            Dictionary with log statistics
        """
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                query = (
                    "SELECT log_level, COUNT(*) as count FROM log_references WHERE 1=1"
                )
                params = []

                if operation_id:
                    query += " AND operation_id = ?"
                    params.append(operation_id)

                if start_time:
                    query += " AND timestamp >= ?"
                    params.append(start_time)

                if end_time:
                    query += " AND timestamp <= ?"
                    params.append(end_time)

                query += " GROUP BY log_level"

                cursor.execute(query, params)
                rows = cursor.fetchall()

                level_counts = {row["log_level"]: row["count"] for row in rows}
                total_logs = sum(level_counts.values())

                return {
                    "total_logs": total_logs,
                    "by_level": level_counts,
                    "error_count": level_counts.get("ERROR", 0),
                    "warning_count": level_counts.get("WARNING", 0),
                    "critical_count": level_counts.get("CRITICAL", 0),
                }

    def get_operation_with_telemetry_metrics(self, operation_id: str) -> Dict[str, Any]:
        """
        Get operation details with aggregated telemetry metrics in log context.

        This is useful for including telemetry metrics in log messages.

        Args:
            operation_id: ID of the operation

        Returns:
            Dictionary with operation details and key metrics
        """
        with self._lock:
            operation = self.get_operation(operation_id)
            if not operation:
                return {"error": "Operation not found"}

            # Get key metrics
            metrics = self.get_operation_metrics(operation_id)
            metric_summary = {}

            for metric in metrics:
                metric_name = metric["metric_name"]
                if metric_name not in metric_summary:
                    metric_summary[metric_name] = {
                        "value": metric["metric_value"],
                        "unit": metric.get("unit"),
                        "timestamp": metric["timestamp"],
                    }
                else:
                    # Keep the latest value
                    if metric["timestamp"] > metric_summary[metric_name]["timestamp"]:
                        metric_summary[metric_name] = {
                            "value": metric["metric_value"],
                            "unit": metric.get("unit"),
                            "timestamp": metric["timestamp"],
                        }

            return {
                "operation_id": operation_id,
                "operation_type": operation.get("operation_type"),
                "operation_title": operation.get("title"),
                "operation_status": operation.get("status"),
                "start_time": operation.get("start_time"),
                "end_time": operation.get("end_time"),
                "telemetry_metrics": metric_summary,
            }

    # Context Manager API

    @contextmanager
    def track_operation(
        self,
        operation_type: str,
        title: str,
        parent_id: Optional[str] = None,
        activity_id: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Context manager for automatic operation tracking.

        Usage:
            with telemetry.track_operation("implementation", "Task 42") as op:
                op.record_event("test_generation", "info", "Starting test generation")
                # ... perform work ...
                op.record_metric("tokens_used", 1250)

        Args:
            operation_type: Type of operation
            title: Human-readable title
            parent_id: Optional parent operation ID
            activity_id: Optional activity ID
            metadata: Optional metadata

        Yields:
            Operation context manager
        """
        operation_id = self.start_operation(
            operation_type=operation_type,
            title=title,
            parent_id=parent_id,
            activity_id=activity_id,
            metadata=metadata,
        )

        class OperationContext:
            def __init__(self, telemetry_manager, operation_id):
                self.telemetry = telemetry_manager
                self.operation_id = operation_id

            def record_event(self, event_type, severity, message, context=None):
                """Record an event for this operation"""
                self.telemetry.record_event(
                    self.operation_id, event_type, severity, message, context
                )

            def record_metric(self, metric_name, metric_value, unit=None):
                """Record a metric for this operation"""
                self.telemetry.record_metric(
                    self.operation_id, metric_name, metric_value, unit
                )

            def record_resource(self, resource_type, value, unit, name=None):
                """Record resource usage for this operation"""
                self.telemetry.record_resource_usage(
                    self.operation_id, resource_type, value, unit, name
                )

            def get_telemetry_context(self) -> Dict[str, Any]:
                """
                Get telemetry context for logging.

                Returns a dictionary with operation details that can be
                passed to log messages as context.

                Returns:
                    Dictionary with operation context
                """
                return {
                    "operation_id": self.operation_id,
                    "operation_type": (
                        self.telemetry.get_operation(self.operation_id).get(
                            "operation_type"
                        )
                        if self.telemetry.get_operation(self.operation_id)
                        else None
                    ),
                }

        op_context = OperationContext(self, operation_id)

        try:
            yield op_context
            self.end_operation(operation_id, "completed")
        except Exception as e:
            self.record_event(
                operation_id,
                "failed",
                "error",
                f"Operation failed: {str(e)}",
                {"exception_type": type(e).__name__},
            )
            self.end_operation(operation_id, "failed", {"error": str(e)})
            raise

    # Decorator Support

    def track_decorator(self, operation_type: Optional[str] = None):
        """
        Decorator for automatic function tracking.

        Usage:
            @telemetry.track_decorator()
            def my_function():
                pass

            @telemetry.track_decorator(operation_type="custom_type")
            def my_function():
                pass

        Args:
            operation_type: Optional operation type (defaults to function name)

        Returns:
            Decorator function
        """

        def decorator(func: Callable):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                # Determine operation type
                op_type = operation_type or func.__name__
                title = f"{func.__name__}"

                # Start operation
                operation_id = self.start_operation(
                    operation_type=op_type,
                    title=title,
                    metadata={"function": func.__name__, "module": func.__module__},
                )

                try:
                    result = func(*args, **kwargs)
                    self.end_operation(operation_id, "completed")
                    return result
                except Exception as e:
                    self.record_event(
                        operation_id,
                        "failed",
                        "error",
                        f"Function failed: {str(e)}",
                        {"exception_type": type(e).__name__},
                    )
                    self.end_operation(operation_id, "failed", {"error": str(e)})
                    raise

            return wrapper

        return decorator

    # Query Interface for Analytics

    def query_operations(
        self,
        operation_type: Optional[str] = None,
        status: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Query operations with advanced filters for analytics.

        Args:
            operation_type: Filter by operation type
            status: Filter by status
            start_time: Start time filter (ISO format)
            end_time: End time filter (ISO format)
            limit: Maximum results

        Returns:
            List of operation dictionaries
        """
        with self._lock:
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

                if start_time:
                    query += " AND start_time >= ?"
                    params.append(start_time)

                if end_time:
                    query += " AND start_time <= ?"
                    params.append(end_time)

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

    def get_operation_stats(
        self, operation_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get statistics for operations by type.

        Args:
            operation_type: Filter by operation type (optional)

        Returns:
            Dictionary with statistics: count, avg_duration, success_rate, etc.
        """
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                query = "SELECT COUNT(*) as count FROM operations WHERE 1=1"
                params = []

                if operation_type:
                    query += " AND operation_type = ?"
                    params.append(operation_type)

                cursor.execute(query, params)
                count = cursor.fetchone()["count"]

                if count == 0:
                    return {"count": 0}

                # Get completion status breakdown
                status_query = (
                    "SELECT status, COUNT(*) as count FROM operations WHERE 1=1"
                )
                status_params = list(params)
                status_query += " GROUP BY status"
                cursor.execute(status_query, status_params)
                status_rows = cursor.fetchall()

                status_breakdown = {row["status"]: row["count"] for row in status_rows}

                # Calculate success rate
                success_count = status_breakdown.get("completed", 0)
                success_rate = (success_count / count) * 100 if count > 0 else 0

                # Get average duration
                duration_query = """
                    SELECT AVG(
                        CAST((julianday(end_time) - julianday(start_time)) * 86400 AS REAL)
                    ) as avg_duration
                    FROM operations
                    WHERE end_time IS NOT NULL
                """
                duration_params = []
                if operation_type:
                    duration_query += " AND operation_type = ?"
                    duration_params.append(operation_type)

                cursor.execute(duration_query, duration_params)
                duration_row = cursor.fetchone()
                avg_duration = (
                    duration_row["avg_duration"] if duration_row["avg_duration"] else 0
                )

                return {
                    "count": count,
                    "avg_duration_seconds": round(avg_duration, 2),
                    "success_rate_percent": round(success_rate, 2),
                    "status_breakdown": status_breakdown,
                }

    def search_events(
        self,
        event_type: Optional[str] = None,
        severity: Optional[str] = None,
        message_contains: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Search events by various criteria.

        Args:
            event_type: Filter by event type
            severity: Filter by severity
            message_contains: Filter by message content
            limit: Maximum results

        Returns:
            List of event dictionaries
        """
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                query = "SELECT * FROM events WHERE 1=1"
                params = []

                if event_type:
                    query += " AND event_type = ?"
                    params.append(event_type)

                if severity:
                    query += " AND severity = ?"
                    params.append(severity)

                if message_contains:
                    query += " AND message LIKE ?"
                    params.append(f"%{message_contains}%")

                query += " ORDER BY timestamp DESC LIMIT ?"
                params.append(limit)

                cursor.execute(query, params)
                rows = cursor.fetchall()

                events = []
                for row in rows:
                    event = dict(row)
                    if event["context"]:
                        event["context"] = json.loads(event["context"])
                    events.append(event)

                return events


# Global telemetry manager instance
_telemetry_manager = None
_telemetry_lock = threading.Lock()


def get_telemetry_manager() -> TelemetryManager:
    """
    Get the global telemetry manager instance (thread-safe singleton).

    Returns:
        TelemetryManager instance
    """
    global _telemetry_manager
    if _telemetry_manager is None:
        with _telemetry_lock:
            if _telemetry_manager is None:
                _telemetry_manager = TelemetryManager()
    return _telemetry_manager
