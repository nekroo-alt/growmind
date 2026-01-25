"""
Decision History Manager - Task 6.1: Decision History Tracking

This module implements decision history tracking for meta-cognition and pattern recognition.
It tracks all decisions with full context, reasoning, confidence, outcomes, and dependencies.

Features:
- Track every decision with context, reasoning, and outcome
- Track decision dependencies and relationships
- Track decision confidence and actual success
- Track decision time and resources consumed
- Build decision graph for analysis
- Export decision history for external analysis
"""

import sqlite3
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
import json
import threading
from dataclasses import dataclass
from collections import defaultdict

# Database path
DECISION_HISTORY_DB_PATH = "decision_history.db"


class DecisionHistoryManager:
    """
    Manages decision history data storage and retrieval for meta-cognition.

    Features:
    - Thread-safe operations using locks
    - Decision recording with full context
    - Decision dependency tracking
    - Decision graph building
    - Query interface for pattern recognition
    - Export capabilities for external analysis
    """

    def __init__(self, db_path: str = DECISION_HISTORY_DB_PATH):
        """
        Initialize decision history manager.

        Args:
            db_path: Path to decision history database file
        """
        self.db_path = db_path
        self._lock = threading.RLock()  # Reentrant lock for thread safety
        self._init_schema()

    def _init_schema(self):
        """
        Initialize decision history database schema.
        Creates tables for decisions, dependencies, and outcomes.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Decisions table - tracks all decisions with full context
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS decisions (
                    id TEXT PRIMARY KEY,
                    timestamp DATETIME NOT NULL,
                    operation_id TEXT,
                    task_id INTEGER,
                    context TEXT,
                    reasoning TEXT,
                    action TEXT,
                    confidence REAL,
                    outcome TEXT,
                    time_elapsed REAL,
                    resources TEXT,
                    metadata TEXT
                )
                """
            )

            # Decision dependencies table - tracks relationships between decisions
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS decision_dependencies (
                    id TEXT PRIMARY KEY,
                    decision_id TEXT NOT NULL,
                    depends_on_decision_id TEXT NOT NULL,
                    dependency_type TEXT,
                    FOREIGN KEY (decision_id) REFERENCES decisions (id) ON DELETE CASCADE,
                    FOREIGN KEY (depends_on_decision_id) REFERENCES decisions (id) ON DELETE CASCADE
                )
                """
            )

            # Decision alternatives table - tracks considered alternatives and rejection reasons
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS decision_alternatives (
                    id TEXT PRIMARY KEY,
                    decision_id TEXT NOT NULL,
                    alternative_action TEXT NOT NULL,
                    reason_for_rejection TEXT,
                    estimated_success REAL,
                    FOREIGN KEY (decision_id) REFERENCES decisions (id) ON DELETE CASCADE
                )
                """
            )

            # Create indexes for fast queries
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_decisions_timestamp 
                ON decisions(timestamp)
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_decisions_operation 
                ON decisions(operation_id)
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_decisions_task 
                ON decisions(task_id)
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_decisions_outcome 
                ON decisions(outcome)
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_decision_dependencies_decision 
                ON decision_dependencies(decision_id)
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_decision_dependencies_depends_on 
                ON decision_dependencies(depends_on_decision_id)
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_decision_alternatives_decision 
                ON decision_alternatives(decision_id)
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

    # Decision Recording

    def record_decision(
        self,
        reasoning: str,
        action: str,
        confidence: float,
        context: Optional[Dict[str, Any]] = None,
        operation_id: Optional[str] = None,
        task_id: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
        alternatives: Optional[List[Dict[str, Any]]] = None,
        dependencies: Optional[List[str]] = None,
    ) -> str:
        """
        Record a decision with full context and reasoning.

        Args:
            reasoning: Natural language reasoning for the decision
            action: The action that was taken
            confidence: Confidence level (0.0 to 1.0)
            context: Context at the time of decision
            operation_id: ID of the operation (from telemetry)
            task_id: ID of the task (from task.db)
            metadata: Additional metadata
            alternatives: List of alternative actions considered
            dependencies: List of decision IDs this decision depends on

        Returns:
            Decision ID (UUID string)
        """
        with self._lock:
            decision_id = str(uuid.uuid4())
            timestamp = datetime.utcnow().isoformat()

            context_json = json.dumps(context) if context else None
            metadata_json = json.dumps(metadata) if metadata else None

            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO decisions 
                    (id, timestamp, operation_id, task_id, context, reasoning, action, confidence, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        decision_id,
                        timestamp,
                        operation_id,
                        task_id,
                        context_json,
                        reasoning,
                        action,
                        confidence,
                        metadata_json,
                    ),
                )
                conn.commit()

            # Record alternatives if provided
            if alternatives:
                for alt in alternatives:
                    self.record_alternative(
                        decision_id,
                        alt.get("action"),
                        alt.get("reason_for_rejection"),
                        alt.get("estimated_success"),
                    )

            # Record dependencies if provided
            if dependencies:
                for dep_id in dependencies:
                    self.record_dependency(decision_id, dep_id)

            return decision_id

    def record_outcome(
        self,
        decision_id: str,
        outcome: str,
        time_elapsed: Optional[float] = None,
        resources: Optional[Dict[str, Any]] = None,
    ):
        """
        Record the outcome of a decision.

        Args:
            decision_id: ID of the decision
            outcome: Outcome ('success', 'failure', 'partial', 'cancelled')
            time_elapsed: Time elapsed in seconds
            resources: Resources consumed (e.g., {'tokens': 1250})
        """
        with self._lock:
            resources_json = json.dumps(resources) if resources else None

            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE decisions 
                    SET outcome = ?, time_elapsed = ?, resources = ?
                    WHERE id = ?
                    """,
                    (outcome, time_elapsed, resources_json, decision_id),
                )
                conn.commit()

    def record_alternative(
        self,
        decision_id: str,
        alternative_action: str,
        reason_for_rejection: Optional[str] = None,
        estimated_success: Optional[float] = None,
    ) -> str:
        """
        Record an alternative action that was considered but not chosen.

        Args:
            decision_id: ID of the decision
            alternative_action: The alternative action
            reason_for_rejection: Why this alternative was rejected
            estimated_success: Estimated success probability for this alternative

        Returns:
            Alternative ID (UUID string)
        """
        with self._lock:
            alternative_id = str(uuid.uuid4())

            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO decision_alternatives 
                    (id, decision_id, alternative_action, reason_for_rejection, estimated_success)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        alternative_id,
                        decision_id,
                        alternative_action,
                        reason_for_rejection,
                        estimated_success,
                    ),
                )
                conn.commit()

            return alternative_id

    def record_dependency(
        self,
        decision_id: str,
        depends_on_decision_id: str,
        dependency_type: Optional[str] = None,
    ) -> str:
        """
        Record a dependency between decisions.

        Args:
            decision_id: ID of the decision that depends on another
            depends_on_decision_id: ID of the decision being depended on
            dependency_type: Type of dependency ('prerequisite', 'related', 'followup')

        Returns:
            Dependency ID (UUID string)
        """
        with self._lock:
            dependency_id = str(uuid.uuid4())

            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO decision_dependencies 
                    (id, decision_id, depends_on_decision_id, dependency_type)
                    VALUES (?, ?, ?, ?)
                    """,
                    (dependency_id, decision_id, depends_on_decision_id, dependency_type),
                )
                conn.commit()

            return dependency_id

    # Decision Retrieval

    def get_decision(self, decision_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a decision by ID with full details.

        Args:
            decision_id: ID of the decision

        Returns:
            Dictionary with decision details or None if not found
        """
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT * FROM decisions WHERE id = ?
                    """,
                    (decision_id,),
                )
                row = cursor.fetchone()

                if row:
                    decision = dict(row)

                    # Parse JSON fields
                    if decision["context"]:
                        decision["context"] = json.loads(decision["context"])
                    if decision["resources"]:
                        decision["resources"] = json.loads(decision["resources"])
                    if decision["metadata"]:
                        decision["metadata"] = json.loads(decision["metadata"])

                    # Get dependencies
                    decision["dependencies"] = self.get_decision_dependencies(decision_id)

                    # Get alternatives
                    decision["alternatives"] = self.get_decision_alternatives(decision_id)

                    return decision
                return None

    def list_decisions(
        self,
        operation_id: Optional[str] = None,
        task_id: Optional[int] = None,
        outcome: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        List decisions with optional filters.

        Args:
            operation_id: Filter by operation ID
            task_id: Filter by task ID
            outcome: Filter by outcome
            start_time: Start time filter (ISO format)
            end_time: End time filter (ISO format)
            limit: Maximum number of decisions to return
            offset: Number of decisions to skip (for pagination)

        Returns:
            List of decision dictionaries
        """
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                query = "SELECT * FROM decisions WHERE 1=1"
                params = []

                if operation_id:
                    query += " AND operation_id = ?"
                    params.append(operation_id)

                if task_id:
                    query += " AND task_id = ?"
                    params.append(task_id)

                if outcome:
                    query += " AND outcome = ?"
                    params.append(outcome)

                if start_time:
                    query += " AND timestamp >= ?"
                    params.append(start_time)

                if end_time:
                    query += " AND timestamp <= ?"
                    params.append(end_time)

                query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
                params.extend([limit, offset])

                cursor.execute(query, params)
                rows = cursor.fetchall()

                decisions = []
                for row in rows:
                    decision = dict(row)

                    # Parse JSON fields
                    if decision["context"]:
                        decision["context"] = json.loads(decision["context"])
                    if decision["resources"]:
                        decision["resources"] = json.loads(decision["resources"])
                    if decision["metadata"]:
                        decision["metadata"] = json.loads(decision["metadata"])

                    decisions.append(decision)

                return decisions

    def get_decision_dependencies(self, decision_id: str) -> List[Dict[str, Any]]:
        """
        Get all dependencies of a decision.

        Args:
            decision_id: ID of the decision

        Returns:
            List of dependency dictionaries
        """
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT dd.*, d.action, d.outcome
                    FROM decision_dependencies dd
                    INNER JOIN decisions d ON dd.depends_on_decision_id = d.id
                    WHERE dd.decision_id = ?
                    """,
                    (decision_id,),
                )
                rows = cursor.fetchall()

                return [dict(row) for row in rows]

    def get_decision_alternatives(self, decision_id: str) -> List[Dict[str, Any]]:
        """
        Get all alternatives considered for a decision.

        Args:
            decision_id: ID of the decision

        Returns:
            List of alternative dictionaries
        """
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT * FROM decision_alternatives WHERE decision_id = ?
                    """,
                    (decision_id,),
                )
                rows = cursor.fetchall()

                return [dict(row) for row in rows]

    # Decision Graph

    def get_decision_graph(
        self, decision_id: str, max_depth: int = 3
    ) -> Dict[str, Any]:
        """
        Build a decision graph starting from a given decision.

        The graph includes both dependencies (prerequisites) and dependent decisions (decisions that depend on this one).

        Args:
            decision_id: ID of the root decision
            max_depth: Maximum depth to traverse

        Returns:
            Dictionary with decision graph structure
        """
        with self._lock:
            # Get the root decision
            root = self.get_decision(decision_id)
            if not root:
                return {"error": "Decision not found"}

            # Build graph recursively
            graph = {"nodes": {}, "edges": []}

            # Add root node
            graph["nodes"][decision_id] = {
                "action": root["action"],
                "confidence": root["confidence"],
                "outcome": root["outcome"],
                "timestamp": root["timestamp"],
            }

            # Traverse dependencies (upstream)
            self._traverse_dependencies(decision_id, graph, max_depth, direction="up")

            # Traverse dependent decisions (downstream)
            self._traverse_dependencies(decision_id, graph, max_depth, direction="down")

            return graph

    def _traverse_dependencies(
        self,
        decision_id: str,
        graph: Dict[str, Any],
        max_depth: int,
        depth: int = 0,
        direction: str = "up",
        visited: Optional[set] = None,
    ):
        """
        Recursively traverse decision dependencies to build graph.

        Args:
            decision_id: Current decision ID
            graph: Graph structure to populate
            max_depth: Maximum traversal depth
            depth: Current traversal depth
            direction: 'up' for dependencies, 'down' for dependents
            visited: Set of visited decision IDs to prevent cycles
        """
        if depth >= max_depth:
            return

        if visited is None:
            visited = set()

        if decision_id in visited:
            return

        visited.add(decision_id)

        with self._get_connection() as conn:
            cursor = conn.cursor()

            if direction == "up":
                # Get dependencies (prerequisites)
                cursor.execute(
                    """
                    SELECT dd.depends_on_decision_id as related_id, d.*
                    FROM decision_dependencies dd
                    INNER JOIN decisions d ON dd.depends_on_decision_id = d.id
                    WHERE dd.decision_id = ?
                    """,
                    (decision_id,),
                )
            else:
                # Get dependent decisions (downstream)
                cursor.execute(
                    """
                    SELECT dd.decision_id as related_id, d.*
                    FROM decision_dependencies dd
                    INNER JOIN decisions d ON dd.decision_id = d.id
                    WHERE dd.depends_on_decision_id = ?
                    """,
                    (decision_id,),
                )

            rows = cursor.fetchall()

            for row in rows:
                related_id = row["related_id"]

                # Add node if not exists
                if related_id not in graph["nodes"]:
                    graph["nodes"][related_id] = {
                        "action": row["action"],
                        "confidence": row["confidence"],
                        "outcome": row["outcome"],
                        "timestamp": row["timestamp"],
                    }

                # Add edge
                if direction == "up":
                    graph["edges"].append(
                        {
                            "from": related_id,
                            "to": decision_id,
                            "type": "dependency",
                        }
                    )
                else:
                    graph["edges"].append(
                        {
                            "from": decision_id,
                            "to": related_id,
                            "type": "dependency",
                        }
                    )

                # Recurse
                self._traverse_dependencies(
                    related_id, graph, max_depth, depth + 1, direction, visited
                )

    # Search Interface

    def search_decisions(
        self,
        action_contains: Optional[str] = None,
        reasoning_contains: Optional[str] = None,
        outcome: Optional[str] = None,
        min_confidence: Optional[float] = None,
        max_confidence: Optional[float] = None,
        operation_id: Optional[str] = None,
        task_id: Optional[int] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Search decisions by various criteria.

        Args:
            action_contains: Filter by action content
            reasoning_contains: Filter by reasoning content
            outcome: Filter by outcome
            min_confidence: Minimum confidence level
            max_confidence: Maximum confidence level
            operation_id: Filter by operation ID
            task_id: Filter by task ID
            start_time: Start time filter (ISO format)
            end_time: End time filter (ISO format)
            limit: Maximum results

        Returns:
            List of decision dictionaries
        """
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                query = "SELECT * FROM decisions WHERE 1=1"
                params = []

                if action_contains:
                    query += " AND action LIKE ?"
                    params.append(f"%{action_contains}%")

                if reasoning_contains:
                    query += " AND reasoning LIKE ?"
                    params.append(f"%{reasoning_contains}%")

                if outcome:
                    query += " AND outcome = ?"
                    params.append(outcome)

                if min_confidence is not None:
                    query += " AND confidence >= ?"
                    params.append(min_confidence)

                if max_confidence is not None:
                    query += " AND confidence <= ?"
                    params.append(max_confidence)

                if operation_id:
                    query += " AND operation_id = ?"
                    params.append(operation_id)

                if task_id:
                    query += " AND task_id = ?"
                    params.append(task_id)

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

                decisions = []
                for row in rows:
                    decision = dict(row)

                    # Parse JSON fields
                    if decision["context"]:
                        decision["context"] = json.loads(decision["context"])
                    if decision["resources"]:
                        decision["resources"] = json.loads(decision["resources"])
                    if decision["metadata"]:
                        decision["metadata"] = json.loads(decision["metadata"])

                    decisions.append(decision)

                return decisions

    # Statistics and Analytics

    def get_decision_statistics(
        self,
        operation_id: Optional[str] = None,
        task_id: Optional[int] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get statistics about decisions.

        Args:
            operation_id: Optional filter by operation ID
            task_id: Optional filter by task ID
            start_time: Optional start time filter
            end_time: Optional end time filter

        Returns:
            Dictionary with decision statistics
        """
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Build query with filters
                query = "SELECT * FROM decisions WHERE 1=1"
                params = []

                if operation_id:
                    query += " AND operation_id = ?"
                    params.append(operation_id)

                if task_id:
                    query += " AND task_id = ?"
                    params.append(task_id)

                if start_time:
                    query += " AND timestamp >= ?"
                    params.append(start_time)

                if end_time:
                    query += " AND timestamp <= ?"
                    params.append(end_time)

                cursor.execute(query, params)
                rows = cursor.fetchall()

                decisions = [dict(row) for row in rows]

                if not decisions:
                    return {
                        "total_decisions": 0,
                        "success_rate": 0.0,
                        "avg_confidence": 0.0,
                    }

        # Calculate statistics
        total = len(decisions)
        successful = sum(1 for d in decisions if d["outcome"] == "success")
        failed = sum(1 for d in decisions if d["outcome"] == "failure")
        avg_confidence = sum(d["confidence"] for d in decisions) / total
        
        # Calculate average time elapsed (handle case where no time elapsed values)
        decisions_with_time = [d for d in decisions if d["time_elapsed"]]
        if decisions_with_time:
            avg_time_elapsed = sum(d["time_elapsed"] for d in decisions_with_time) / len(decisions_with_time)
        else:
            avg_time_elapsed = 0.0

        return {
            "total_decisions": total,
            "successful": successful,
            "failed": failed,
            "success_rate": (successful / total) * 100 if total > 0 else 0.0,
            "avg_confidence": round(avg_confidence, 3),
            "avg_time_elapsed_seconds": round(avg_time_elapsed, 2),
        }

    # Export

    def export_decisions(
        self,
        format: str = "json",
        operation_id: Optional[str] = None,
        task_id: Optional[int] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        include_graph: bool = False,
    ) -> Any:
        """
        Export decisions for external analysis.

        Args:
            format: Export format ('json' or 'dict')
            operation_id: Optional filter by operation ID
            task_id: Optional filter by task ID
            start_time: Optional start time filter
            end_time: Optional end time filter
            include_graph: Include decision graph for each decision

        Returns:
            JSON string or dictionary with exported decisions
        """
        with self._lock:
            decisions = self.search_decisions(
                operation_id=operation_id,
                task_id=task_id,
                start_time=start_time,
                end_time=end_time,
                limit=10000,
            )

            export_data = {
                "decisions": [],
                "exported_at": datetime.utcnow().isoformat(),
                "total_count": len(decisions),
            }

            for decision in decisions:
                decision_data = dict(decision)

                # Include alternatives
                decision_data["alternatives"] = self.get_decision_alternatives(
                    decision["id"]
                )

                # Include dependencies
                decision_data["dependencies"] = self.get_decision_dependencies(
                    decision["id"]
                )

                # Include graph if requested
                if include_graph:
                    decision_data["graph"] = self.get_decision_graph(decision["id"])

                export_data["decisions"].append(decision_data)

            if format == "json":
                return json.dumps(export_data, indent=2, default=str)
            else:
                return export_data

    # Cleanup

    def delete_old_decisions(
        self, days: int = 30
    ) -> int:
        """
        Delete decisions older than specified number of days.

        Args:
            days: Number of days to keep

        Returns:
            Number of decisions deleted
        """
        with self._lock:
            from datetime import timedelta

            cutoff_date = datetime.utcnow() - timedelta(days=days)

            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Get count before deletion
                cursor.execute(
                    """
                    SELECT COUNT(*) as count FROM decisions WHERE timestamp < ?
                    """,
                    (cutoff_date.isoformat(),),
                )
                count = cursor.fetchone()["count"]

                # Delete old decisions (cascades to dependencies and alternatives)
                cursor.execute(
                    """
                    DELETE FROM decisions WHERE timestamp < ?
                    """,
                    (cutoff_date.isoformat(),),
                )

                conn.commit()

                return count


# Global decision history manager instance
_decision_history_manager = None
_decision_history_lock = threading.Lock()


def get_decision_history_manager() -> DecisionHistoryManager:
    """
    Get global decision history manager instance (thread-safe singleton).

    Returns:
        DecisionHistoryManager instance
    """
    global _decision_history_manager
    if _decision_history_manager is None:
        with _decision_history_lock:
            if _decision_history_manager is None:
                _decision_history_manager = DecisionHistoryManager()
    return _decision_history_manager


def get_decision_history() -> DecisionHistoryManager:
    """
    Alias for get_decision_history_manager() for compatibility.
    
    Returns:
        DecisionHistoryManager instance
    """
    return get_decision_history_manager()


def reset_decision_history():
    """
    Reset global decision history manager instance.
    Useful for testing or reinitialization.
    """
    global _decision_history_manager
    with _decision_history_lock:
        _decision_history_manager = None
