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
        auto_track: bool = True
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
                    (operation_id, parent_id, operation_type, title, start_time, metadata_json, activity_id)
                )
                conn.commit()

            # Track operation for auto-timing
            if auto_track:
                self._operation_stack.append({
                    'id': operation_id,
                    'start_time': time.time(),
                    'type': operation_type
                })

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
        with self._lock:
            end_time = datetime.utcnow().isoformat()
            
            # Calculate duration if auto-tracked
            elapsed_time = None
            for i, op in enumerate(self._operation_stack):
                if op['id'] == operation_id:
                    elapsed_time = time.time() - op['start_time']
                    self._operation_stack.pop(i)
                    break

            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Auto-record time_elapsed metric
                if elapsed_time is not None:
                    self.record_metric(operation_id, 'time_elapsed', elapsed_time, 'seconds')
                
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
        limit: int = 100,
        offset: int = 0
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
        with self._lock:
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
        with self._lock:
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
        with self._lock:
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

    # Resource Usage Monitoring (Task 1.5)

    @dataclass
    class ResourceThresholds:
        """Thresholds for resource alerts"""
        cpu_warning: float = 80.0  # CPU usage percentage
        cpu_critical: float = 95.0
        memory_warning: float = 80.0  # Memory usage percentage
        memory_critical: float = 95.0
        disk_warning: float = 90.0  # Disk usage percentage
        disk_critical: float = 98.0

    def _check_psutil_available(self) -> bool:
        """Check if psutil is available for resource monitoring"""
        return PSUTIL_AVAILABLE

    def _get_cpu_usage(self) -> Dict[str, Any]:
        """
        Get current CPU usage information.
        
        Returns:
            Dictionary with CPU metrics
        """
        if not self._check_psutil_available():
            return {"error": "psutil not available"}
        
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            cpu_count = psutil.cpu_count()
            cpu_freq = psutil.cpu_freq()
            
            metrics = {
                "cpu_percent": cpu_percent,
                "cpu_count": cpu_count,
                "cpu_freq_mhz": cpu_freq.current if cpu_freq else None
            }
            
            # Per-CPU usage
            cpu_percents = psutil.cpu_percent(interval=0.1, percpu=True)
            metrics["cpu_percents_per_core"] = cpu_percents
            
            return metrics
        except Exception as e:
            return {"error": str(e)}

    def _get_memory_usage(self) -> Dict[str, Any]:
        """
        Get current memory usage information.
        
        Returns:
            Dictionary with memory metrics
        """
        if not self._check_psutil_available():
            return {"error": "psutil not available"}
        
        try:
            mem = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            return {
                "total_mb": mem.total / (1024 * 1024),
                "available_mb": mem.available / (1024 * 1024),
                "used_mb": mem.used / (1024 * 1024),
                "free_mb": mem.free / (1024 * 1024),
                "percent": mem.percent,
                "swap_total_mb": swap.total / (1024 * 1024),
                "swap_used_mb": swap.used / (1024 * 1024),
                "swap_percent": swap.percent
            }
        except Exception as e:
            return {"error": str(e)}

    def _get_disk_usage(self, path: str = ".") -> Dict[str, Any]:
        """
        Get disk usage information for a path.
        
        Args:
            path: Path to check disk usage for
            
        Returns:
            Dictionary with disk metrics
        """
        if not self._check_psutil_available():
            return {"error": "psutil not available"}
        
        try:
            disk = psutil.disk_usage(path)
            
            return {
                "total_gb": disk.total / (1024 ** 3),
                "used_gb": disk.used / (1024 ** 3),
                "free_gb": disk.free / (1024 ** 3),
                "percent": disk.percent,
                "path": path
            }
        except Exception as e:
            return {"error": str(e)}

    def _get_disk_io(self) -> Dict[str, Any]:
        """
        Get disk I/O statistics.
        
        Returns:
            Dictionary with I/O metrics
        """
        if not self._check_psutil_available():
            return {"error": "psutil not available"}
        
        try:
            io = psutil.disk_io_counters()
            if io is None:
                return {"error": "disk I/O not available"}
            
            return {
                "read_count": io.read_count,
                "write_count": io.write_count,
                "read_bytes_mb": io.read_bytes / (1024 * 1024),
                "write_bytes_mb": io.write_bytes / (1024 * 1024),
                "read_time_ms": io.read_time,
                "write_time_ms": io.write_time
            }
        except Exception as e:
            return {"error": str(e)}

    def _get_network_io(self) -> Dict[str, Any]:
        """
        Get network I/O statistics.
        
        Returns:
            Dictionary with network metrics
        """
        if not self._check_psutil_available():
            return {"error": "psutil not available"}
        
        try:
            net = psutil.net_io_counters()
            if net is None:
                return {"error": "network I/O not available"}
            
            return {
                "bytes_sent_mb": net.bytes_sent / (1024 * 1024),
                "bytes_recv_mb": net.bytes_recv / (1024 * 1024),
                "packets_sent": net.packets_sent,
                "packets_recv": net.packets_recv,
                "errin": net.errin,
                "errout": net.errout,
                "dropin": net.dropin,
                "dropout": net.dropout
            }
        except Exception as e:
            return {"error": str(e)}

    def _check_resource_thresholds(
        self,
        metrics: Dict[str, Any],
        thresholds: ResourceThresholds,
        operation_id: str
    ) -> List[Dict[str, Any]]:
        """
        Check if resource metrics exceed thresholds and generate alerts.
        
        Args:
            metrics: Resource metrics dictionary
            thresholds: Threshold configuration
            operation_id: ID of the operation for context
            
        Returns:
            List of alert dictionaries
        """
        alerts = []
        
        if "cpu_percent" in metrics:
            cpu = metrics["cpu_percent"]
            if cpu >= thresholds.cpu_critical:
                alerts.append({
                    "resource_type": "cpu",
                    "severity": "critical",
                    "value": cpu,
                    "threshold": thresholds.cpu_critical,
                    "message": f"CPU usage critically high: {cpu:.1f}%"
                })
                self.record_event(
                    operation_id,
                    "resource_alert",
                    "critical",
                    f"CPU usage critically high: {cpu:.1f}%",
                    {"cpu_percent": cpu, "threshold": thresholds.cpu_critical}
                )
            elif cpu >= thresholds.cpu_warning:
                alerts.append({
                    "resource_type": "cpu",
                    "severity": "warning",
                    "value": cpu,
                    "threshold": thresholds.cpu_warning,
                    "message": f"CPU usage high: {cpu:.1f}%"
                })
                self.record_event(
                    operation_id,
                    "resource_alert",
                    "warning",
                    f"CPU usage high: {cpu:.1f}%",
                    {"cpu_percent": cpu, "threshold": thresholds.cpu_warning}
                )
        
        if "percent" in metrics:  # Memory usage
            mem = metrics["percent"]
            if mem >= thresholds.memory_critical:
                alerts.append({
                    "resource_type": "memory",
                    "severity": "critical",
                    "value": mem,
                    "threshold": thresholds.memory_critical,
                    "message": f"Memory usage critically high: {mem:.1f}%"
                })
                self.record_event(
                    operation_id,
                    "resource_alert",
                    "critical",
                    f"Memory usage critically high: {mem:.1f}%",
                    {"memory_percent": mem, "threshold": thresholds.memory_critical}
                )
            elif mem >= thresholds.memory_warning:
                alerts.append({
                    "resource_type": "memory",
                    "severity": "warning",
                    "value": mem,
                    "threshold": thresholds.memory_warning,
                    "message": f"Memory usage high: {mem:.1f}%"
                })
                self.record_event(
                    operation_id,
                    "resource_alert",
                    "warning",
                    f"Memory usage high: {mem:.1f}%",
                    {"memory_percent": mem, "threshold": thresholds.memory_warning}
                )
        
        if "percent" in metrics and "path" in metrics:  # Disk usage
            disk = metrics["percent"]
            if disk >= thresholds.disk_critical:
                alerts.append({
                    "resource_type": "disk",
                    "severity": "critical",
                    "value": disk,
                    "threshold": thresholds.disk_critical,
                    "message": f"Disk usage critically high: {disk:.1f}%",
                    "path": metrics["path"]
                })
                self.record_event(
                    operation_id,
                    "resource_alert",
                    "critical",
                    f"Disk usage critically high: {disk:.1f}%",
                    {"disk_percent": disk, "threshold": thresholds.disk_critical, "path": metrics["path"]}
                )
            elif disk >= thresholds.disk_warning:
                alerts.append({
                    "resource_type": "disk",
                    "severity": "warning",
                    "value": disk,
                    "threshold": thresholds.disk_warning,
                    "message": f"Disk usage high: {disk:.1f}%",
                    "path": metrics["path"]
                })
                self.record_event(
                    operation_id,
                    "resource_alert",
                    "warning",
                    f"Disk usage high: {disk:.1f}%",
                    {"disk_percent": disk, "threshold": thresholds.disk_warning, "path": metrics["path"]}
                )
        
        return alerts

    @contextmanager
    def monitor_resources(
        self,
        operation_id: str,
        sample_interval: float = 1.0,
        thresholds: Optional[ResourceThresholds] = None,
        disk_path: str = "."
    ):
        """
        Context manager to monitor resources during an operation.
        
        Usage:
            with telemetry.monitor_resources(op_id, sample_interval=1.0) as monitor:
                # ... perform operation ...
                pass
            
            # After context exits, get resource summary
            summary = monitor.get_summary()
        
        Args:
            operation_id: ID of the operation to monitor
            sample_interval: Sampling interval in seconds
            thresholds: Optional thresholds for alerts
            disk_path: Path to monitor disk usage for
            
        Yields:
            ResourceMonitor context
        """
        if not self._check_psutil_available():
            # Return a dummy monitor if psutil not available
            class DummyMonitor:
                def get_summary(self):
                    return {"error": "psutil not available, monitoring disabled"}
            yield DummyMonitor()
            return
        
        if thresholds is None:
            thresholds = self.ResourceThresholds()
        
        class ResourceMonitor:
            def __init__(self, telemetry_manager, operation_id, sample_interval, thresholds, disk_path):
                self.telemetry = telemetry_manager
                self.operation_id = operation_id
                self.sample_interval = sample_interval
                self.thresholds = thresholds
                self.disk_path = disk_path
                self._monitoring = False
                self._monitor_thread = None
                self._samples = {
                    "cpu": [],
                    "memory": [],
                    "disk": [],
                    "disk_io": [],
                    "network": []
                }
                self._baseline = None
                self._start_time = None
                self._end_time = None
                self._alerts = []
            
            def _monitor_loop(self):
                """Monitor loop that runs in background thread"""
                import threading as th
                while self._monitoring:
                    try:
                        # Collect all metrics
                        cpu_metrics = self.telemetry._get_cpu_usage()
                        mem_metrics = self.telemetry._get_memory_usage()
                        disk_metrics = self.telemetry._get_disk_usage(self.disk_path)
                        disk_io_metrics = self.telemetry._get_disk_io()
                        net_metrics = self.telemetry._get_network_io()
                        
                        # Store samples
                        timestamp = time.time()
                        self._samples["cpu"].append((timestamp, cpu_metrics))
                        self._samples["memory"].append((timestamp, mem_metrics))
                        self._samples["disk"].append((timestamp, disk_metrics))
                        self._samples["disk_io"].append((timestamp, disk_io_metrics))
                        self._samples["network"].append((timestamp, net_metrics))
                        
                        # Record to telemetry
                        if "cpu_percent" in cpu_metrics:
                            self.telemetry.record_resource_usage(
                                self.operation_id,
                                "cpu",
                                cpu_metrics["cpu_percent"],
                                "%",
                                "cpu_usage"
                            )
                        
                        if "percent" in mem_metrics:
                            self.telemetry.record_resource_usage(
                                self.operation_id,
                                "memory",
                                mem_metrics["percent"],
                                "%",
                                "memory_usage"
                            )
                        
                        if "percent" in disk_metrics:
                            self.telemetry.record_resource_usage(
                                self.operation_id,
                                "disk",
                                disk_metrics["percent"],
                                "%",
                                f"disk_usage_{self.disk_path}"
                            )
                        
                        # Check thresholds and generate alerts
                        alerts = self.telemetry._check_resource_thresholds(
                            {**cpu_metrics, **mem_metrics, **disk_metrics},
                            self.thresholds,
                            self.operation_id
                        )
                        self._alerts.extend(alerts)
                        
                    except Exception as e:
                        # Log error but continue monitoring
                        self.telemetry.record_event(
                            self.operation_id,
                            "monitoring_error",
                            "warning",
                            f"Resource monitoring error: {str(e)}"
                        )
                    
                    time.sleep(self.sample_interval)
            
            def start(self):
                """Start monitoring"""
                self._monitoring = True
                self._start_time = time.time()
                
                # Capture baseline
                self._baseline = {
                    "cpu": self.telemetry._get_cpu_usage(),
                    "memory": self.telemetry._get_memory_usage(),
                    "disk": self.telemetry._get_disk_usage(self.disk_path),
                    "disk_io": self.telemetry._get_disk_io(),
                    "network": self.telemetry._get_network_io()
                }
                
                # Start monitoring thread
                self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
                self._monitor_thread.start()
            
            def stop(self):
                """Stop monitoring"""
                self._monitoring = False
                self._end_time = time.time()
                if self._monitor_thread:
                    self._monitor_thread.join(timeout=2.0)
            
            def get_summary(self) -> Dict[str, Any]:
                """Get resource usage summary"""
                if not self._samples or not any(self._samples.values()):
                    return {"error": "No samples collected"}
                
                duration = (self._end_time - self._start_time) if self._end_time else 0
                
                def calculate_stats(samples):
                    """Calculate statistics from samples list"""
                    values = []
                    for timestamp, metrics in samples:
                        if "cpu_percent" in metrics:
                            values.append(metrics["cpu_percent"])
                        elif "percent" in metrics and "path" not in metrics:
                            values.append(metrics["percent"])
                        elif "percent" in metrics and "path" in metrics:
                            values.append(metrics["percent"])
                        elif "read_bytes_mb" in metrics:
                            values.append(metrics["read_bytes_mb"] + metrics["write_bytes_mb"])
                        elif "bytes_sent_mb" in metrics:
                            values.append(metrics["bytes_sent_mb"] + metrics["bytes_recv_mb"])
                    
                    if not values:
                        return None
                    
                    return {
                        "min": min(values),
                        "max": max(values),
                        "avg": sum(values) / len(values),
                        "count": len(values)
                    }
                
                cpu_stats = calculate_stats(self._samples["cpu"])
                mem_stats = calculate_stats(self._samples["memory"])
                disk_stats = calculate_stats(self._samples["disk"])
                disk_io_stats = calculate_stats(self._samples["disk_io"])
                net_stats = calculate_stats(self._samples["network"])
                
                # Calculate disk I/O throughput
                io_throughput = None
                if disk_io_stats and disk_io_stats["count"] > 1:
                    first_io = self._samples["disk_io"][0][1]
                    last_io = self._samples["disk_io"][-1][1]
                    time_diff = self._samples["disk_io"][-1][0] - self._samples["disk_io"][0][0]
                    if time_diff > 0 and "read_bytes_mb" in first_io and "read_bytes_mb" in last_io:
                        read_delta = last_io["read_bytes_mb"] - first_io["read_bytes_mb"]
                        write_delta = last_io["write_bytes_mb"] - first_io["write_bytes_mb"]
                        io_throughput = {
                            "read_mb_per_sec": read_delta / time_diff if time_diff > 0 else 0,
                            "write_mb_per_sec": write_delta / time_diff if time_diff > 0 else 0
                        }
                
                # Calculate network throughput
                net_throughput = None
                if net_stats and net_stats["count"] > 1:
                    first_net = self._samples["network"][0][1]
                    last_net = self._samples["network"][-1][1]
                    time_diff = self._samples["network"][-1][0] - self._samples["network"][0][0]
                    if time_diff > 0 and "bytes_sent_mb" in first_net and "bytes_sent_mb" in last_net:
                        sent_delta = last_net["bytes_sent_mb"] - first_net["bytes_sent_mb"]
                        recv_delta = last_net["bytes_recv_mb"] - first_net["bytes_recv_mb"]
                        net_throughput = {
                            "sent_mb_per_sec": sent_delta / time_diff if time_diff > 0 else 0,
                            "recv_mb_per_sec": recv_delta / time_diff if time_diff > 0 else 0
                        }
                
                return {
                    "duration_seconds": round(duration, 2),
                    "cpu": cpu_stats,
                    "memory": mem_stats,
                    "disk": disk_stats,
                    "disk_io_throughput": io_throughput,
                    "network_throughput": net_throughput,
                    "baseline": self._baseline,
                    "sample_count": sum(len(samples) for samples in self._samples.values()),
                    "alerts": self._alerts
                }
        
        monitor = ResourceMonitor(self, operation_id, sample_interval, thresholds, disk_path)
        monitor.start()
        
        try:
            yield monitor
        finally:
            monitor.stop()
            
            # Store summary as metadata
            summary = monitor.get_summary()
            if "error" not in summary:
                self.record_metric(
                    operation_id,
                    "resource_monitoring_samples",
                    summary["sample_count"],
                    "samples"
                )

    def generate_resource_report(
        self,
        operation_id: str,
        include_details: bool = True
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive resource usage report for an operation.
        
        Args:
            operation_id: ID of the operation
            include_details: Include detailed samples
            
        Returns:
            Resource usage report dictionary
        """
        with self._lock:
            # Get operation details
            operation = self.get_operation(operation_id)
            if not operation:
                return {"error": "Operation not found"}
            
            # Get resource records
            resources = self.get_operation_resources(operation_id)
            
            if not resources:
                return {
                    "operation_id": operation_id,
                    "operation_type": operation.get("operation_type"),
                    "status": "No resource data available"
                }
            
            # Group by resource type
            by_type = defaultdict(list)
            for resource in resources:
                by_type[resource["resource_type"]].append(resource)
            
            # Calculate statistics for each type
            report = {
                "operation_id": operation_id,
                "operation_type": operation.get("operation_type"),
                "operation_title": operation.get("title"),
                "operation_start": operation.get("start_time"),
                "operation_end": operation.get("end_time"),
                "resources": {}
            }
            
            for resource_type, records in by_type.items():
                values = [r["value"] for r in records]
                timestamps = [r["timestamp"] for r in records]
                
                stats = {
                    "unit": records[0]["unit"] if records else "unknown",
                    "count": len(values),
                    "min": min(values),
                    "max": max(values),
                    "avg": sum(values) / len(values),
                    "first_sample": timestamps[0],
                    "last_sample": timestamps[-1]
                }
                
                # Include unit-specific labels
                if resource_type == "cpu":
                    stats["label"] = f"CPU Usage ({stats['unit']})"
                elif resource_type == "memory":
                    stats["label"] = f"Memory Usage ({stats['unit']})"
                elif resource_type == "disk":
                    stats["label"] = f"Disk Usage ({stats['unit']})"
                
                if include_details:
                    stats["samples"] = records
                
                report["resources"][resource_type] = stats
            
            return report

    def get_resource_trends(
        self,
        operation_type: Optional[str] = None,
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        Analyze resource usage trends across operations.
        
        Args:
            operation_type: Filter by operation type
            limit: Maximum operations to analyze
            
        Returns:
            Resource trends analysis
        """
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Get operations
                query = "SELECT id, operation_type, start_time FROM operations WHERE 1=1"
                params = []
                
                if operation_type:
                    query += " AND operation_type = ?"
                    params.append(operation_type)
                
                query += " ORDER BY start_time DESC LIMIT ?"
                params.append(limit)
                
                cursor.execute(query, params)
                operations = cursor.fetchall()
                
                if not operations:
                    return {"message": "No operations found"}
                
                # Collect resource data
                trends = {
                    "cpu": [],
                    "memory": [],
                    "disk": []
                }
                
                for op in operations:
                    op_id = op["id"]
                    
                    # Get resource records
                    cursor.execute(
                        """
                        SELECT resource_type, AVG(value) as avg_value
                        FROM resources
                        WHERE operation_id = ?
                        GROUP BY resource_type
                        """,
                        (op_id,)
                    )
                    resource_avgs = cursor.fetchall()
                    
                    for res in resource_avgs:
                        resource_type = res["resource_type"]
                        avg_value = res["avg_value"]
                        
                        if resource_type in trends:
                            trends[resource_type].append({
                                "operation_id": op_id,
                                "operation_type": op["operation_type"],
                                "timestamp": op["start_time"],
                                "avg_value": avg_value
                            })
                
                # Calculate trend statistics
                for resource_type, values in trends.items():
                    if values:
                        numeric_values = [v["avg_value"] for v in values]
                        trends[resource_type] = {
                            "samples": values,
                            "count": len(values),
                            "min": min(numeric_values),
                            "max": max(numeric_values),
                            "avg": sum(numeric_values) / len(numeric_values)
                        }
                
                return {
                    "operation_type": operation_type,
                    "operations_analyzed": len(operations),
                    "trends": trends
                }

    # File Operation Tracking (Task 1.4)

    def record_file_read(
        self,
        operation_id: str,
        file_path: str,
        file_size: int = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Record a file read operation.
        
        Args:
            operation_id: ID of the operation
            file_path: Path to the file that was read
            file_size: Size of the file in bytes
            metadata: Additional metadata
            
        Returns:
            File operation ID (UUID string)
        """
        with self._lock:
            import hashlib
            file_op_id = str(uuid.uuid4())
            timestamp = datetime.utcnow().isoformat()
            
            # Get file size if not provided
            if file_size is None and os.path.exists(file_path):
                try:
                    file_size = os.path.getsize(file_path)
                except (OSError, IOError):
                    file_size = 0
            
            # Calculate content hash for verification
            content_hash = None
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'rb') as f:
                        content_hash = hashlib.sha256(f.read()).hexdigest()[:16]
                except (OSError, IOError):
                    pass
            
            metadata_json = json.dumps(metadata) if metadata else None

            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO file_operations 
                    (id, operation_id, operation_type, file_path, file_size, content_hash, timestamp, metadata)
                    VALUES (?, ?, 'read', ?, ?, ?, ?, ?)
                    """,
                    (file_op_id, operation_id, file_path, file_size, content_hash, timestamp, metadata_json)
                )
                conn.commit()

            return file_op_id

    def record_file_write(
        self,
        operation_id: str,
        file_path: str,
        file_size: int = None,
        content_hash: str = None,
        diff_summary: str = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Record a file write operation.
        
        Args:
            operation_id: ID of the operation
            file_path: Path to the file that was written
            file_size: Size of the file in bytes
            content_hash: Hash of the file content for verification
            diff_summary: Summary of changes made to the file
            metadata: Additional metadata
            
        Returns:
            File operation ID (UUID string)
        """
        with self._lock:
            file_op_id = str(uuid.uuid4())
            timestamp = datetime.utcnow().isoformat()
            metadata_json = json.dumps(metadata) if metadata else None

            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO file_operations 
                    (id, operation_id, operation_type, file_path, file_size, content_hash, diff_summary, timestamp, metadata)
                    VALUES (?, ?, 'write', ?, ?, ?, ?, ?, ?)
                    """,
                    (file_op_id, operation_id, file_path, file_size, content_hash, diff_summary, timestamp, metadata_json)
                )
                conn.commit()

            return file_op_id

    def record_file_delete(
        self,
        operation_id: str,
        file_path: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Record a file delete operation.
        
        Args:
            operation_id: ID of the operation
            file_path: Path to the file that was deleted
            metadata: Additional metadata
            
        Returns:
            File operation ID (UUID string)
        """
        with self._lock:
            file_op_id = str(uuid.uuid4())
            timestamp = datetime.utcnow().isoformat()
            metadata_json = json.dumps(metadata) if metadata else None

            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO file_operations 
                    (id, operation_id, operation_type, file_path, timestamp, metadata)
                    VALUES (?, ?, 'delete', ?, ?, ?)
                    """,
                    (file_op_id, operation_id, file_path, timestamp, metadata_json)
                )
                conn.commit()

            return file_op_id

    def record_git_operation(
        self,
        operation_id: str,
        git_op_type: str,
        details: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Record a git operation (add, commit, checkout, etc.).
        
        Args:
            operation_id: ID of the operation
            git_op_type: Type of git operation ('add', 'commit', 'checkout', 'branch', 'merge')
            details: Operation details (files added, commit hash, etc.)
            metadata: Additional metadata
            
        Returns:
            File operation ID (UUID string)
        """
        with self._lock:
            file_op_id = str(uuid.uuid4())
            timestamp = datetime.utcnow().isoformat()
            
            # Combine details and metadata
            combined_metadata = {}
            if details:
                combined_metadata.update(details)
            if metadata:
                combined_metadata.update(metadata)
            metadata_json = json.dumps(combined_metadata) if combined_metadata else None

            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO file_operations 
                    (id, operation_id, operation_type, file_path, timestamp, metadata)
                    VALUES (?, ?, 'git_' || ?, NULL, ?, ?)
                    """,
                    (file_op_id, operation_id, git_op_type, timestamp, metadata_json)
                )
                conn.commit()

            return file_op_id

    def get_file_operations(
        self,
        operation_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get all file operations for an operation.
        
        Args:
            operation_id: ID of the operation
            
        Returns:
            List of file operation dictionaries ordered by timestamp
        """
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT * FROM file_operations WHERE operation_id = ? ORDER BY timestamp ASC
                    """,
                    (operation_id,)
                )
                rows = cursor.fetchall()
                
                file_ops = []
                for row in rows:
                    op = dict(row)
                    if op["metadata"]:
                        op["metadata"] = json.loads(op["metadata"])
                    file_ops.append(op)
                
                return file_ops

    def get_file_operations_by_path(
        self,
        file_path: str,
        operation_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get file operations for a specific file path.
        
        Args:
            file_path: Path to the file
            operation_type: Filter by operation type (read, write, delete, git_*)
            limit: Maximum results
            
        Returns:
            List of file operation dictionaries ordered by timestamp
        """
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                query = "SELECT * FROM file_operations WHERE file_path = ?"
                params = [file_path]
                
                if operation_type:
                    if operation_type.startswith('git_'):
                        query += " AND operation_type = ?"
                    else:
                        query += " AND operation_type = ?"
                    params.append(operation_type)
                
                query += " ORDER BY timestamp DESC LIMIT ?"
                params.append(limit)
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                file_ops = []
                for row in rows:
                    op = dict(row)
                    if op["metadata"]:
                        op["metadata"] = json.loads(op["metadata"])
                    file_ops.append(op)
                
                return file_ops

    def get_modified_files(
        self,
        operation_id: str
    ) -> List[str]:
        """
        Get list of files modified during an operation.
        
        Args:
            operation_id: ID of the operation
            
        Returns:
            List of unique file paths
        """
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT DISTINCT file_path 
                    FROM file_operations 
                    WHERE operation_id = ? 
                    AND file_path IS NOT NULL 
                    AND operation_type IN ('read', 'write', 'delete')
                    """,
                    (operation_id,)
                )
                rows = cursor.fetchall()
                
                return [row["file_path"] for row in rows if row["file_path"]]

    # File I/O Wrappers for Automatic Telemetry

    @contextmanager
    def track_file_read(self, operation_id: str, file_path: str, metadata: Optional[Dict[str, Any]] = None):
        """
        Context manager to automatically track file reads.
        
        Usage:
            with telemetry.track_file_read(op_id, "file.txt") as f:
                content = f.read()
        
        Args:
            operation_id: ID of the operation
            file_path: Path to the file
            metadata: Additional metadata
            
        Yields:
            File handle
        """
        file_size = 0
        try:
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
            
            with open(file_path, 'r') as f:
                yield f
                self.record_file_read(
                    operation_id=operation_id,
                    file_path=file_path,
                    file_size=file_size,
                    metadata=metadata
                )
        except Exception as e:
            # Record failed read attempt
            self.record_file_read(
                operation_id=operation_id,
                file_path=file_path,
                file_size=file_size,
                metadata={**(metadata or {}), "error": str(e)}
            )
            raise

    def tracked_write_file(
        self,
        operation_id: str,
        file_path: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Write to a file and automatically track the operation.
        
        Args:
            operation_id: ID of the operation
            file_path: Path to the file
            content: Content to write
            metadata: Additional metadata
        """
        import hashlib
        
        # Calculate content hash
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        
        # Write file
        with open(file_path, 'w') as f:
            f.write(content)
        
        # Record operation
        self.record_file_write(
            operation_id=operation_id,
            file_path=file_path,
            file_size=len(content.encode()),
            content_hash=content_hash,
            metadata=metadata
        )

    # Migration Management

    def apply_migration(self, version: int, description: str, migration_sql: str):
        """
        Apply a database migration.
        
        Args:
            version: Migration version number
            description: Human-readable description of migration
            migration_sql: SQL to execute for the migration
        """
        with self._lock:
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
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT MAX(version) FROM migrations")
                row = cursor.fetchone()
                return row[0] if row[0] else 0

    # Context Manager API

    @contextmanager
    def track_operation(
        self,
        operation_type: str,
        title: str,
        parent_id: Optional[str] = None,
        activity_id: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
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
            metadata=metadata
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
                {"exception_type": type(e).__name__}
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
                    metadata={
                        "function": func.__name__,
                        "module": func.__module__
                    }
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
                        {"exception_type": type(e).__name__}
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
        limit: int = 100
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
        self,
        operation_type: Optional[str] = None
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
                status_query = "SELECT status, COUNT(*) as count FROM operations WHERE 1=1"
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
                avg_duration = duration_row["avg_duration"] if duration_row["avg_duration"] else 0
                
                return {
                    "count": count,
                    "avg_duration_seconds": round(avg_duration, 2),
                    "success_rate_percent": round(success_rate, 2),
                    "status_breakdown": status_breakdown
                }

    def search_events(
        self,
        event_type: Optional[str] = None,
        severity: Optional[str] = None,
        message_contains: Optional[str] = None,
        limit: int = 100
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
