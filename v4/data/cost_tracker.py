"""
Cost Tracker - Task 4.4: Cost Tracking and Reporting

This module implements comprehensive cost tracking and reporting for LLM API usage.
It tracks costs by task, session, and project, analyzes trends, predicts future costs,
and provides alerts when approaching budget limits.

Features:
- LLM API cost tracking (tokens × price)
- Cost aggregation by task, session, project
- Cost trend analysis over time
- Future cost prediction based on usage patterns
- Cost report generation (text, markdown, JSON)
- Cost alerts when approaching budget limits
- Integration with TelemetryManager for automatic cost recording
"""

import sqlite3
import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import json
import os
import threading
from dataclasses import dataclass, asdict
from collections import defaultdict

# LLM pricing data (as of 2024)
LLM_PRICING = {
    "openai": {
        "gpt-4": {"prompt": 0.03 / 1000, "completion": 0.06 / 1000},
        "gpt-4-turbo": {"prompt": 0.01 / 1000, "completion": 0.03 / 1000},
        "gpt-3.5-turbo": {"prompt": 0.0005 / 1000, "completion": 0.0015 / 1000},
    },
    "anthropic": {
        "claude-3-opus": {"prompt": 0.015 / 1000, "completion": 0.075 / 1000},
        "claude-3-sonnet": {"prompt": 0.003 / 1000, "completion": 0.015 / 1000},
        "claude-3-haiku": {"prompt": 0.00025 / 1000, "completion": 0.00125 / 1000},
    },
    "gemini": {
        "gemini-pro": {"prompt": 0.0005 / 1000, "completion": 0.0015 / 1000},
        "gemini-ultra": {"prompt": 0.002 / 1000, "completion": 0.008 / 1000},
    },
}


@dataclass
class CostRecord:
    """Cost record for LLM API call."""
    id: str
    timestamp: str
    provider: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    prompt_cost: float
    completion_cost: float
    total_cost: float
    operation_id: Optional[str] = None
    task_id: Optional[int] = None
    session_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class CostAlert:
    """Cost alert for budget overruns."""
    id: str
    alert_type: str  # "threshold", "trend", "prediction"
    severity: str  # "info", "warning", "critical"
    message: str
    current_cost: float
    threshold: Optional[float]
    predicted_cost: Optional[float]
    timestamp: str
    acknowledged: bool = False


# Database path
COST_TRACKER_DB_PATH = "cost_tracker.db"


class CostTracker:
    """
    Tracks and reports LLM API costs across tasks, sessions, and projects.

    Features:
    - Cost tracking per LLM API call
    - Cost aggregation by task, session, project
    - Trend analysis and prediction
    - Budget alerts and warnings
    - Multi-format reporting (text, markdown, JSON)
    """

    def __init__(self, db_path: str = COST_TRACKER_DB_PATH):
        """
        Initialize cost tracker.

        Args:
            db_path: Path to cost tracker database file
        """
        self.db_path = db_path
        self._lock = threading.RLock()  # Reentrant lock for thread safety
        self._init_schema()

    def _init_schema(self):
        """
        Initialize cost tracker database schema.
        Creates tables for cost records, aggregations, and alerts.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Cost records table - individual LLM API calls
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS cost_records (
                    id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    model TEXT NOT NULL,
                    prompt_tokens INTEGER NOT NULL,
                    completion_tokens INTEGER NOT NULL,
                    total_tokens INTEGER NOT NULL,
                    prompt_cost REAL NOT NULL,
                    completion_cost REAL NOT NULL,
                    total_cost REAL NOT NULL,
                    operation_id TEXT,
                    task_id INTEGER,
                    session_id TEXT,
                    metadata TEXT
                )
                """
            )

            # Cost aggregations table - aggregated costs by type
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS cost_aggregations (
                    id TEXT PRIMARY KEY,
                    aggregation_type TEXT NOT NULL,
                    aggregation_key TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT NOT NULL,
                    total_cost REAL NOT NULL,
                    total_tokens INTEGER NOT NULL,
                    call_count INTEGER NOT NULL,
                    prompt_tokens INTEGER NOT NULL,
                    completion_tokens INTEGER NOT NULL,
                    avg_cost_per_call REAL NOT NULL,
                    models_used TEXT,
                    providers_used TEXT,
                    UNIQUE(aggregation_type, aggregation_key, start_time, end_time)
                )
                """
            )

            # Cost alerts table - budget and trend alerts
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS cost_alerts (
                    id TEXT PRIMARY KEY,
                    alert_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    message TEXT NOT NULL,
                    current_cost REAL NOT NULL,
                    threshold REAL,
                    predicted_cost REAL,
                    timestamp TEXT NOT NULL,
                    acknowledged INTEGER DEFAULT 0,
                    budget_id TEXT,
                    UNIQUE(alert_type, budget_id, acknowledged)
                )
                """
            )

            # Cost budget table - budget limits and thresholds
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS cost_budgets (
                    id TEXT PRIMARY KEY,
                    budget_type TEXT NOT NULL,
                    budget_key TEXT,
                    budget_limit REAL NOT NULL,
                    alert_threshold REAL NOT NULL,
                    alert_threshold_percent REAL NOT NULL,
                    time_period TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

            # Cost trends table - historical cost trends for prediction
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS cost_trends (
                    id TEXT PRIMARY KEY,
                    period_type TEXT NOT NULL,
                    period_key TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT NOT NULL,
                    total_cost REAL NOT NULL,
                    total_tokens INTEGER NOT NULL,
                    call_count INTEGER NOT NULL,
                    avg_cost_per_day REAL,
                    growth_rate REAL,
                    trend_direction TEXT,
                    UNIQUE(period_type, period_key, start_time, end_time)
                )
                """
            )

            # Create indexes for fast queries
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_cost_records_timestamp 
                ON cost_records(timestamp)
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_cost_records_operation 
                ON cost_records(operation_id)
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_cost_records_task 
                ON cost_records(task_id)
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_cost_records_session 
                ON cost_records(session_id)
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_cost_aggregations_type 
                ON cost_aggregations(aggregation_type, aggregation_key)
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_cost_alerts_timestamp 
                ON cost_alerts(timestamp)
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_cost_alerts_acknowledged 
                ON cost_alerts(acknowledged)
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

    def record_cost(
        self,
        provider: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        operation_id: Optional[str] = None,
        task_id: Optional[int] = None,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Record cost for an LLM API call.

        Automatically calculates cost using provider/model pricing.

        Args:
            provider: LLM provider (openai, anthropic, gemini)
            model: Model name (e.g., gpt-4, claude-3-opus)
            prompt_tokens: Number of prompt tokens used
            completion_tokens: Number of completion tokens used
            operation_id: Optional telemetry operation ID
            task_id: Optional task ID
            session_id: Optional session ID
            metadata: Optional metadata dictionary

        Returns:
            Cost record ID (UUID string)
        """
        with self._lock:
            # Calculate costs
            total_tokens = prompt_tokens + completion_tokens

            # Get pricing
            pricing = self._get_pricing(provider, model)
            prompt_cost = prompt_tokens * pricing["prompt"]
            completion_cost = completion_tokens * pricing["completion"]
            total_cost = prompt_cost + completion_cost

            # Create cost record
            cost_id = str(uuid.uuid4())
            timestamp = datetime.utcnow().isoformat()
            metadata_json = json.dumps(metadata) if metadata else None

            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO cost_records 
                    (id, timestamp, provider, model, prompt_tokens, completion_tokens,
                     total_tokens, prompt_cost, completion_cost, total_cost,
                     operation_id, task_id, session_id, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        cost_id,
                        timestamp,
                        provider,
                        model,
                        prompt_tokens,
                        completion_tokens,
                        total_tokens,
                        prompt_cost,
                        completion_cost,
                        total_cost,
                        operation_id,
                        task_id,
                        session_id,
                        metadata_json,
                    ),
                )
                conn.commit()

            # Check for budget alerts
            self._check_budget_alerts()

            return cost_id

    def _get_pricing(self, provider: str, model: str) -> Dict[str, float]:
        """
        Get pricing for a provider/model combination.

        Args:
            provider: LLM provider
            model: Model name

        Returns:
            Dictionary with prompt and completion pricing

        Raises:
            ValueError: If provider/model not found
        """
        if provider not in LLM_PRICING:
            raise ValueError(f"Unknown provider: {provider}")

        if model not in LLM_PRICING[provider]:
            raise ValueError(f"Unknown model: {model} for provider: {provider}")

        return LLM_PRICING[provider][model]

    def get_cost_by_task(self, task_id: int) -> Dict[str, Any]:
        """
        Get total cost for a task.

        Args:
            task_id: Task ID

        Returns:
            Dictionary with cost details
        """
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT 
                        COUNT(*) as call_count,
                        SUM(prompt_tokens) as total_prompt_tokens,
                        SUM(completion_tokens) as total_completion_tokens,
                        SUM(total_tokens) as total_tokens,
                        SUM(prompt_cost) as total_prompt_cost,
                        SUM(completion_cost) as total_completion_cost,
                        SUM(total_cost) as total_cost,
                        AVG(total_cost) as avg_cost_per_call,
                        MIN(timestamp) as first_call,
                        MAX(timestamp) as last_call
                    FROM cost_records 
                    WHERE task_id = ?
                    """,
                    (task_id,),
                )
                row = cursor.fetchone()

                if row and row["call_count"] > 0:
                    return dict(row)
                return {
                    "call_count": 0,
                    "total_cost": 0.0,
                    "total_tokens": 0,
                }

    def get_cost_by_session(self, session_id: str) -> Dict[str, Any]:
        """
        Get total cost for a session.

        Args:
            session_id: Session ID

        Returns:
            Dictionary with cost details
        """
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT 
                        COUNT(*) as call_count,
                        SUM(prompt_tokens) as total_prompt_tokens,
                        SUM(completion_tokens) as total_completion_tokens,
                        SUM(total_tokens) as total_tokens,
                        SUM(prompt_cost) as total_prompt_cost,
                        SUM(completion_cost) as total_completion_cost,
                        SUM(total_cost) as total_cost,
                        AVG(total_cost) as avg_cost_per_call,
                        MIN(timestamp) as first_call,
                        MAX(timestamp) as last_call
                    FROM cost_records 
                    WHERE session_id = ?
                    """,
                    (session_id,),
                )
                row = cursor.fetchone()

                if row and row["call_count"] > 0:
                    return dict(row)
                return {
                    "call_count": 0,
                    "total_cost": 0.0,
                    "total_tokens": 0,
                }

    def get_cost_by_operation(self, operation_id: str) -> Dict[str, Any]:
        """
        Get total cost for an operation.

        Args:
            operation_id: Operation ID

        Returns:
            Dictionary with cost details
        """
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT 
                        COUNT(*) as call_count,
                        SUM(prompt_tokens) as total_prompt_tokens,
                        SUM(completion_tokens) as total_completion_tokens,
                        SUM(total_tokens) as total_tokens,
                        SUM(prompt_cost) as total_prompt_cost,
                        SUM(completion_cost) as total_completion_cost,
                        SUM(total_cost) as total_cost,
                        AVG(total_cost) as avg_cost_per_call,
                        MIN(timestamp) as first_call,
                        MAX(timestamp) as last_call
                    FROM cost_records 
                    WHERE operation_id = ?
                    """,
                    (operation_id,),
                )
                row = cursor.fetchone()

                if row and row["call_count"] > 0:
                    return dict(row)
                return {
                    "call_count": 0,
                    "total_cost": 0.0,
                    "total_tokens": 0,
                }

    def get_project_cost(
        self, start_time: Optional[str] = None, end_time: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get total project cost.

        Args:
            start_time: Optional start time (ISO format)
            end_time: Optional end time (ISO format)

        Returns:
            Dictionary with cost details
        """
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                query = """
                    SELECT 
                        COUNT(*) as call_count,
                        SUM(prompt_tokens) as total_prompt_tokens,
                        SUM(completion_tokens) as total_completion_tokens,
                        SUM(total_tokens) as total_tokens,
                        SUM(prompt_cost) as total_prompt_cost,
                        SUM(completion_cost) as total_completion_cost,
                        SUM(total_cost) as total_cost,
                        AVG(total_cost) as avg_cost_per_call,
                        MIN(timestamp) as first_call,
                        MAX(timestamp) as last_call
                    FROM cost_records 
                    WHERE 1=1
                """
                params = []

                if start_time:
                    query += " AND timestamp >= ?"
                    params.append(start_time)

                if end_time:
                    query += " AND timestamp <= ?"
                    params.append(end_time)

                cursor.execute(query, params)
                row = cursor.fetchone()

                if row and row["call_count"] > 0:
                    return dict(row)
                return {
                    "call_count": 0,
                    "total_cost": 0.0,
                    "total_tokens": 0,
                }

    def get_cost_by_provider_model(
        self, start_time: Optional[str] = None, end_time: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get cost breakdown by provider and model.

        Args:
            start_time: Optional start time (ISO format)
            end_time: Optional end time (ISO format)

        Returns:
            List of cost breakdown dictionaries
        """
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                query = """
                    SELECT 
                        provider,
                        model,
                        COUNT(*) as call_count,
                        SUM(prompt_tokens) as total_prompt_tokens,
                        SUM(completion_tokens) as total_completion_tokens,
                        SUM(total_tokens) as total_tokens,
                        SUM(prompt_cost) as total_prompt_cost,
                        SUM(completion_cost) as total_completion_cost,
                        SUM(total_cost) as total_cost,
                        AVG(total_cost) as avg_cost_per_call
                    FROM cost_records 
                    WHERE 1=1
                """
                params = []

                if start_time:
                    query += " AND timestamp >= ?"
                    params.append(start_time)

                if end_time:
                    query += " AND timestamp <= ?"
                    params.append(end_time)

                query += " GROUP BY provider, model ORDER BY total_cost DESC"

                cursor.execute(query, params)
                rows = cursor.fetchall()

                return [dict(row) for row in rows]

    def get_cost_trend(
        self, period: str = "daily", periods: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Get cost trend over time.

        Args:
            period: Time period ('hourly', 'daily', 'weekly', 'monthly')
            periods: Number of periods to return

        Returns:
            List of cost trend dictionaries
        """
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Determine time bucket based on period
                if period == "hourly":
                    time_format = "%Y-%m-%d %H:00:00"
                    time_sql = "strftime('%Y-%m-%d %H:00:00', timestamp)"
                elif period == "daily":
                    time_format = "%Y-%m-%d"
                    time_sql = "date(timestamp)"
                elif period == "weekly":
                    time_format = "%Y-%W"
                    time_sql = "strftime('%Y-%W', timestamp)"
                elif period == "monthly":
                    time_format = "%Y-%m"
                    time_sql = "strftime('%Y-%m', timestamp)"
                else:
                    raise ValueError(f"Invalid period: {period}")

                query = f"""
                    SELECT 
                        {time_sql} as time_bucket,
                        COUNT(*) as call_count,
                        SUM(total_tokens) as total_tokens,
                        SUM(total_cost) as total_cost,
                        AVG(total_cost) as avg_cost_per_call
                    FROM cost_records 
                    GROUP BY time_bucket 
                    ORDER BY time_bucket DESC 
                    LIMIT ?
                """

                cursor.execute(query, (periods,))
                rows = cursor.fetchall()

                # Calculate growth rate
                trends = []
                for i, row in enumerate(rows):
                    trend = dict(row)
                    if i > 0:
                        current_cost = row["total_cost"]
                        prev_cost = rows[i - 1]["total_cost"]
                        if prev_cost > 0:
                            growth_rate = ((current_cost - prev_cost) / prev_cost) * 100
                            trend["growth_rate"] = round(growth_rate, 2)
                        else:
                            trend["growth_rate"] = 0.0

                        # Determine trend direction
                        if growth_rate > 5:
                            trend["trend_direction"] = "increasing"
                        elif growth_rate < -5:
                            trend["trend_direction"] = "decreasing"
                        else:
                            trend["trend_direction"] = "stable"
                    else:
                        trend["growth_rate"] = 0.0
                        trend["trend_direction"] = "unknown"

                    trends.append(trend)

                return trends

    def predict_future_cost(
        self, days: int = 30, method: str = "average"
    ) -> Dict[str, Any]:
        """
        Predict future costs based on historical data.

        Args:
            days: Number of days to predict
            method: Prediction method ('average', 'linear', 'exponential')

        Returns:
            Dictionary with prediction details
        """
        with self._lock:
            # Get historical data
            trends = self.get_cost_trend(period="daily", periods=days)

            if not trends:
                return {"error": "Insufficient historical data"}

            # Calculate prediction based on method
            if method == "average":
                # Simple average of recent days
                recent_costs = [t["total_cost"] for t in trends[:7]]  # Last 7 days
                avg_daily_cost = sum(recent_costs) / len(recent_costs)
                predicted_cost = avg_daily_cost * days

            elif method == "linear":
                # Linear regression
                import statistics

                x = list(range(len(trends)))
                y = [t["total_cost"] for t in trends]

                # Calculate linear regression
                n = len(x)
                x_mean = sum(x) / n
                y_mean = sum(y) / n

                numerator = sum((xi - x_mean) * (yi - y_mean) for xi, yi in zip(x, y))
                denominator = sum((xi - x_mean) ** 2 for xi in x)

                if denominator == 0:
                    slope = 0
                else:
                    slope = numerator / denominator

                intercept = y_mean - slope * x_mean

                # Predict for future days
                predicted_cost = 0
                for future_day in range(days):
                    x_future = len(trends) + future_day
                    predicted_cost += slope * x_future + intercept

            elif method == "exponential":
                # Exponential smoothing
                import statistics

                alpha = 0.3  # Smoothing factor
                s = trends[0]["total_cost"]

                for i in range(1, len(trends)):
                    s = alpha * trends[i]["total_cost"] + (1 - alpha) * s

                # Predict future days with trend growth
                growth_rates = [
                    t["growth_rate"]
                    for t in trends
                    if t["growth_rate"] != 0.0
                ]
                avg_growth_rate = statistics.mean(growth_rates) if growth_rates else 0.0

                predicted_cost = s * (1 + avg_growth_rate / 100) ** days

            else:
                raise ValueError(f"Invalid prediction method: {method}")

            # Calculate confidence based on historical variance
            if len(trends) > 1:
                import statistics

                costs = [t["total_cost"] for t in trends]
                variance = statistics.variance(costs)
                std_dev = statistics.stdev(costs)
                mean = statistics.mean(costs)

                # Coefficient of variation
                cv = std_dev / mean if mean > 0 else 0

                # Confidence level based on CV
                if cv < 0.1:
                    confidence = "high"
                elif cv < 0.3:
                    confidence = "medium"
                else:
                    confidence = "low"
            else:
                confidence = "low"

            return {
                "prediction_method": method,
                "prediction_period_days": days,
                "predicted_cost": round(predicted_cost, 4),
                "confidence_level": confidence,
                "historical_data_points": len(trends),
                "avg_daily_cost": round(trends[0]["total_cost"], 4),
            }

    def set_budget(
        self,
        budget_type: str,
        budget_limit: float,
        alert_threshold: Optional[float] = None,
        alert_threshold_percent: float = 0.8,
        time_period: Optional[str] = None,
        budget_key: Optional[str] = None,
    ):
        """
        Set a cost budget with alert threshold.

        Args:
            budget_type: Type of budget ('project', 'monthly', 'task', 'session')
            budget_limit: Budget limit amount in USD
            alert_threshold: Absolute threshold for alerts
            alert_threshold_percent: Percentage threshold for alerts (default: 0.8 = 80%)
            time_period: Time period for budget (e.g., 'month', 'week')
            budget_key: Optional key for budget (e.g., task_id, session_id)
        """
        with self._lock:
            if alert_threshold is None:
                alert_threshold = budget_limit * alert_threshold_percent

            budget_id = str(uuid.uuid4())
            now = datetime.utcnow().isoformat()

            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO cost_budgets 
                    (id, budget_type, budget_key, budget_limit, alert_threshold,
                     alert_threshold_percent, time_period, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        budget_id,
                        budget_type,
                        budget_key,
                        budget_limit,
                        alert_threshold,
                        alert_threshold_percent,
                        time_period,
                        now,
                        now,
                    ),
                )
                conn.commit()

    def _check_budget_alerts(self):
        """
        Check for budget alerts and create alerts if thresholds exceeded.
        """
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Get all budgets
                cursor.execute("SELECT * FROM cost_budgets")
                budgets = [dict(row) for row in cursor.fetchall()]

                for budget in budgets:
                    # Get current cost for this budget
                    if budget["budget_type"] == "project":
                        current_cost = self.get_project_cost().get("total_cost", 0.0)
                    elif budget["budget_type"] == "monthly":
                        # Get cost for this month
                        start_time = datetime.utcnow().replace(
                            day=1, hour=0, minute=0, second=0, microsecond=0
                        ).isoformat()
                        current_cost = self.get_project_cost(
                            start_time=start_time
                        ).get("total_cost", 0.0)
                    elif budget["budget_type"] == "task" and budget["budget_key"]:
                        current_cost = self.get_cost_by_task(
                            int(budget["budget_key"])
                        ).get("total_cost", 0.0)
                    elif budget["budget_type"] == "session" and budget[
                        "budget_key"
                    ]:
                        current_cost = self.get_cost_by_session(
                            budget["budget_key"]
                        ).get("total_cost", 0.0)
                    else:
                        continue

                    # Check if threshold exceeded
                    if current_cost >= budget["alert_threshold"]:
                        # Check if unacknowledged alert already exists for this budget
                        cursor.execute(
                            """
                            SELECT COUNT(*) as count FROM cost_alerts
                            WHERE alert_type = 'threshold'
                            AND budget_id = ?
                            AND acknowledged = 0
                            LIMIT 1
                            """,
                            (budget["id"],),
                        )
                        existing_alert = cursor.fetchone()

                        if not existing_alert or existing_alert["count"] == 0:
                            # Create new alert
                            alert_id = str(uuid.uuid4())
                            severity = "critical" if current_cost >= budget[
                                "budget_limit"
                            ] else "warning"
                            message = f"Budget threshold exceeded: ${current_cost:.2f} / ${budget['budget_limit']:.2f}"

                            cursor.execute(
                                """
                                INSERT INTO cost_alerts
                                (id, alert_type, severity, message, current_cost,
                                 threshold, timestamp, acknowledged)
                                VALUES (?, ?, ?, ?, ?, ?, ?, 0)
                                """,
                                (
                                    alert_id,
                                    "threshold",
                                    severity,
                                    message,
                                    current_cost,
                                    budget["budget_limit"],
                                    datetime.utcnow().isoformat(),
                                ),
                            )
                            conn.commit()

    def get_cost_alerts(
        self, acknowledged: Optional[bool] = None, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get cost alerts.

        Args:
            acknowledged: Filter by acknowledged status
            limit: Maximum number of alerts to return

        Returns:
            List of cost alert dictionaries
        """
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                query = "SELECT * FROM cost_alerts WHERE 1=1"
                params = []

                if acknowledged is not None:
                    query += " AND acknowledged = ?"
                    params.append(1 if acknowledged else 0)

                query += " ORDER BY timestamp DESC LIMIT ?"
                params.append(limit)

                cursor.execute(query, params)
                rows = cursor.fetchall()

                alerts = []
                for row in rows:
                    alert = dict(row)
                    alert["acknowledged"] = bool(alert["acknowledged"])
                    alerts.append(alert)

                return alerts

    def acknowledge_alert(self, alert_id: str):
        """
        Acknowledge a cost alert.

        Args:
            alert_id: Alert ID to acknowledge
        """
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE cost_alerts 
                    SET acknowledged = 1 
                    WHERE id = ?
                    """,
                    (alert_id,),
                )
                conn.commit()

    def generate_cost_report(
        self,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        format: str = "text",
    ) -> str:
        """
        Generate comprehensive cost report.

        Args:
            start_time: Optional start time (ISO format)
            end_time: Optional end time (ISO format)
            format: Report format ('text', 'markdown', 'json')

        Returns:
            Report as string
        """
        # Get cost data
        project_cost = self.get_project_cost(start_time, end_time)
        by_provider_model = self.get_cost_by_provider_model(start_time, end_time)
        trends = self.get_cost_trend(period="daily", periods=7)
        prediction = self.predict_future_cost(days=30, method="average")

        if format == "json":
            report = {
                "period": {"start": start_time, "end": end_time},
                "project_cost": project_cost,
                "by_provider_model": by_provider_model,
                "trends": trends,
                "prediction": prediction,
                "generated_at": datetime.utcnow().isoformat(),
            }
            return json.dumps(report, indent=2, default=str)

        elif format == "markdown":
            report = "# Cost Report\n\n"
            if start_time or end_time:
                report += f"**Period**: {start_time or 'Beginning'} to {end_time or 'Now'}\n\n"
            report += f"**Generated**: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

            # Project Cost Summary
            report += "## Project Cost Summary\n\n"
            report += f"- **Total Cost**: ${project_cost.get('total_cost', 0):.4f}\n"
            report += f"- **Total Tokens**: {project_cost.get('total_tokens', 0):,}\n"
            report += f"- **Call Count**: {project_cost.get('call_count', 0)}\n"
            report += f"- **Avg Cost/Call**: ${project_cost.get('avg_cost_per_call', 0):.4f}\n"
            report += f"- **Avg Cost/Token**: ${project_cost.get('total_cost', 0) / project_cost.get('total_tokens', 1) if project_cost.get('total_tokens', 0) > 0 else 0:.6f}\n\n"

            # Cost by Provider/Model
            report += "## Cost by Provider/Model\n\n"
            report += "| Provider | Model | Calls | Tokens | Cost |\n"
            report += "|----------|-------|-------|--------|------|\n"
            for item in by_provider_model:
                report += f"| {item['provider']} | {item['model']} | {item['call_count']} | {item['total_tokens']:,} | ${item['total_cost']:.4f} |\n"

            # Trends
            report += "\n## Recent Trends (Last 7 Days)\n\n"
            report += "| Date | Cost | Tokens | Calls | Growth |\n"
            report += "|------|------|--------|-------|--------|\n"
            for trend in trends:
                growth_pct = f"{trend.get('growth_rate', 0):.1f}%"
                report += f"| {trend['time_bucket']} | ${trend['total_cost']:.4f} | {trend['total_tokens']:,} | {trend['call_count']} | {growth_pct} |\n"

            # Prediction
            report += "\n## Cost Prediction (Next 30 Days)\n\n"
            report += f"- **Predicted Cost**: ${prediction.get('predicted_cost', 0):.4f}\n"
            report += f"- **Confidence**: {prediction.get('confidence_level', 'unknown')}\n"
            report += f"- **Method**: {prediction.get('prediction_method', 'unknown')}\n"
            report += f"- **Avg Daily Cost**: ${prediction.get('avg_daily_cost', 0):.4f}\n\n"

            return report

        else:  # text format
            report = "=" * 60 + "\n"
            report += "COST REPORT\n"
            report += "=" * 60 + "\n\n"

            if start_time or end_time:
                report += f"Period: {start_time or 'Beginning'} to {end_time or 'Now'}\n"
            report += f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

            # Project Cost Summary
            report += "Project Cost Summary:\n"
            report += "-" * 40 + "\n"
            report += f"  Total Cost:     ${project_cost.get('total_cost', 0):.4f}\n"
            report += f"  Total Tokens:    {project_cost.get('total_tokens', 0):,}\n"
            report += f"  Call Count:      {project_cost.get('call_count', 0)}\n"
            report += f"  Avg Cost/Call:   ${project_cost.get('avg_cost_per_call', 0):.4f}\n"
            if project_cost.get('total_tokens', 0) > 0:
                report += f"  Avg Cost/Token:  ${project_cost.get('total_cost', 0) / project_cost.get('total_tokens', 0):.6f}\n"
            report += "\n"

            # Cost by Provider/Model
            report += "Cost by Provider/Model:\n"
            report += "-" * 40 + "\n"
            for item in by_provider_model:
                report += f"  {item['provider']}/{item['model']}:\n"
                report += f"    Calls:  {item['call_count']}\n"
                report += f"    Tokens: {item['total_tokens']:,}\n"
                report += f"    Cost:   ${item['total_cost']:.4f}\n"
            report += "\n"

            # Trends
            report += "Recent Trends (Last 7 Days):\n"
            report += "-" * 40 + "\n"
            for trend in trends:
                growth_pct = f"{trend.get('growth_rate', 0):.1f}%"
                report += f"  {trend['time_bucket']}: ${trend['total_cost']:.4f} ({trend['call_count']} calls, growth: {growth_pct})\n"
            report += "\n"

            # Prediction
            report += "Cost Prediction (Next 30 Days):\n"
            report += "-" * 40 + "\n"
            report += f"  Predicted Cost: ${prediction.get('predicted_cost', 0):.4f}\n"
            report += f"  Confidence:     {prediction.get('confidence_level', 'unknown')}\n"
            report += f"  Method:         {prediction.get('prediction_method', 'unknown')}\n"
            report += f"  Avg Daily Cost: ${prediction.get('avg_daily_cost', 0):.4f}\n"
            report += "\n"

            report += "=" * 60 + "\n"

            return report

    def export_cost_data(
        self,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        format: str = "csv",
    ) -> str:
        """
        Export cost data for external analysis.

        Args:
            start_time: Optional start time (ISO format)
            end_time: Optional end time (ISO format)
            format: Export format ('csv', 'json')

        Returns:
            Exported data as string
        """
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                query = "SELECT * FROM cost_records WHERE 1=1"
                params = []

                if start_time:
                    query += " AND timestamp >= ?"
                    params.append(start_time)

                if end_time:
                    query += " AND timestamp <= ?"
                    params.append(end_time)

                query += " ORDER BY timestamp ASC"

                cursor.execute(query, params)
                rows = cursor.fetchall()

                if format == "csv":
                    # CSV header
                    header = "id,timestamp,provider,model,prompt_tokens,completion_tokens,total_tokens,prompt_cost,completion_cost,total_cost,operation_id,task_id,session_id\n"
                    lines = [header]

                    # CSV rows
                    for row in rows:
                        line = f"{row['id']},{row['timestamp']},{row['provider']},{row['model']},{row['prompt_tokens']},{row['completion_tokens']},{row['total_tokens']},{row['prompt_cost']},{row['completion_cost']},{row['total_cost']},{row['operation_id'] or ''},{row['task_id'] or ''},{row['session_id'] or ''}\n"
                        lines.append(line)

                    return "".join(lines)

                elif format == "json":
                    data = [dict(row) for row in rows]
                    return json.dumps(data, indent=2, default=str)

                else:
                    raise ValueError(f"Invalid export format: {format}")


# Global cost tracker instance
_cost_tracker = None
_cost_tracker_lock = threading.Lock()


def get_cost_tracker() -> CostTracker:
    """
    Get global cost tracker instance (thread-safe singleton).

    Returns:
        CostTracker instance
    """
    global _cost_tracker
    if _cost_tracker is None:
        with _cost_tracker_lock:
            if _cost_tracker is None:
                _cost_tracker = CostTracker()
    return _cost_tracker