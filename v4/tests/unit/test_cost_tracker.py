"""
Unit Tests for Cost Tracker - Task 4.4: Cost Tracking and Reporting

Tests comprehensive cost tracking functionality including:
- LLM API cost recording
- Cost aggregation by task, session, operation, and project
- Cost trend analysis
- Cost prediction
- Budget management and alerts
- Cost report generation
"""

import unittest
import sqlite3
import os
import json
from datetime import datetime, timedelta
from v4.data.cost_tracker import (
    CostTracker,
    get_cost_tracker,
    LLM_PRICING,
    COST_TRACKER_DB_PATH,
    CostRecord,
    CostAlert,
)


class TestCostTrackerInitialization(unittest.TestCase):
    """Test cost tracker initialization."""

    def setUp(self):
        """Set up test database."""
        self.test_db_path = "test_cost_tracker.db"
        self.cost_tracker = CostTracker(db_path=self.test_db_path)

    def tearDown(self):
        """Clean up test database."""
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)

    def test_initialization(self):
        """Test that cost tracker initializes correctly."""
        self.assertIsNotNone(self.cost_tracker)
        self.assertTrue(os.path.exists(self.test_db_path))

    def test_schema_initialization(self):
        """Test that database schema is created correctly."""
        conn = sqlite3.connect(self.test_db_path)
        cursor = conn.cursor()

        # Check tables exist
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = [row[0] for row in cursor.fetchall()]

        expected_tables = [
            "cost_records",
            "cost_aggregations",
            "cost_alerts",
            "cost_budgets",
            "cost_trends",
        ]
        for table in expected_tables:
            self.assertIn(table, tables)

        conn.close()


class TestCostRecording(unittest.TestCase):
    """Test cost recording functionality."""

    def setUp(self):
        """Set up test database."""
        self.test_db_path = "test_cost_tracker.db"
        self.cost_tracker = CostTracker(db_path=self.test_db_path)

    def tearDown(self):
        """Clean up test database."""
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)

    def test_record_cost_openai_gpt4(self):
        """Test recording cost for OpenAI GPT-4."""
        cost_id = self.cost_tracker.record_cost(
            provider="openai",
            model="gpt-4",
            prompt_tokens=1000,
            completion_tokens=500,
            operation_id="op1",
            task_id=1,
            session_id="session1",
        )

        self.assertIsNotNone(cost_id)

        # Verify cost calculation
        pricing = LLM_PRICING["openai"]["gpt-4"]
        expected_prompt_cost = 1000 * pricing["prompt"]
        expected_completion_cost = 500 * pricing["completion"]
        expected_total_cost = expected_prompt_cost + expected_completion_cost

        # Get cost record
        conn = sqlite3.connect(self.test_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM cost_records WHERE id = ?", (cost_id,))
        row = cursor.fetchone()

        self.assertEqual(row[2], "openai")  # provider
        self.assertEqual(row[3], "gpt-4")  # model
        self.assertEqual(row[4], 1000)  # prompt_tokens
        self.assertEqual(row[5], 500)  # completion_tokens
        self.assertEqual(row[6], 1500)  # total_tokens
        self.assertAlmostEqual(row[7], expected_prompt_cost, places=6)  # prompt_cost
        self.assertAlmostEqual(
            row[8], expected_completion_cost, places=6
        )  # completion_cost
        self.assertAlmostEqual(
            row[9], expected_total_cost, places=6
        )  # total_cost

        conn.close()

    def test_record_cost_anthropic_claude(self):
        """Test recording cost for Anthropic Claude."""
        cost_id = self.cost_tracker.record_cost(
            provider="anthropic",
            model="claude-3-sonnet",
            prompt_tokens=2000,
            completion_tokens=1000,
        )

        self.assertIsNotNone(cost_id)

        # Verify cost calculation
        pricing = LLM_PRICING["anthropic"]["claude-3-sonnet"]
        expected_prompt_cost = 2000 * pricing["prompt"]
        expected_completion_cost = 1000 * pricing["completion"]
        expected_total_cost = expected_prompt_cost + expected_completion_cost

        # Get cost record
        conn = sqlite3.connect(self.test_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM cost_records WHERE id = ?", (cost_id,))
        row = cursor.fetchone()

        self.assertEqual(row[2], "anthropic")
        self.assertEqual(row[3], "claude-3-sonnet")
        self.assertAlmostEqual(row[9], expected_total_cost, places=6)

        conn.close()

    def test_record_cost_with_metadata(self):
        """Test recording cost with metadata."""
        metadata = {"request_id": "req123", "user_id": "user456"}

        cost_id = self.cost_tracker.record_cost(
            provider="openai",
            model="gpt-3.5-turbo",
            prompt_tokens=500,
            completion_tokens=250,
            metadata=metadata,
        )

        self.assertIsNotNone(cost_id)

        # Get cost record
        conn = sqlite3.connect(self.test_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM cost_records WHERE id = ?", (cost_id,))
        row = cursor.fetchone()

        # Verify metadata (index 13 is the metadata column)
        stored_metadata = json.loads(row[13]) if row[13] else None
        self.assertEqual(stored_metadata, metadata)

        conn.close()

    def test_invalid_provider(self):
        """Test that invalid provider raises ValueError."""
        with self.assertRaises(ValueError):
            self.cost_tracker.record_cost(
                provider="invalid",
                model="gpt-4",
                prompt_tokens=1000,
                completion_tokens=500,
            )

    def test_invalid_model(self):
        """Test that invalid model raises ValueError."""
        with self.assertRaises(ValueError):
            self.cost_tracker.record_cost(
                provider="openai",
                model="invalid-model",
                prompt_tokens=1000,
                completion_tokens=500,
            )


class TestCostAggregation(unittest.TestCase):
    """Test cost aggregation functionality."""

    def setUp(self):
        """Set up test database with sample data."""
        self.test_db_path = "test_cost_tracker.db"
        self.cost_tracker = CostTracker(db_path=self.test_db_path)

        # Insert sample cost records
        self.cost_tracker.record_cost(
            provider="openai",
            model="gpt-4",
            prompt_tokens=1000,
            completion_tokens=500,
            task_id=1,
            operation_id="op1",
            session_id="session1",
        )
        self.cost_tracker.record_cost(
            provider="openai",
            model="gpt-3.5-turbo",
            prompt_tokens=2000,
            completion_tokens=1000,
            task_id=1,
            operation_id="op2",
            session_id="session1",
        )
        self.cost_tracker.record_cost(
            provider="anthropic",
            model="claude-3-sonnet",
            prompt_tokens=500,
            completion_tokens=250,
            task_id=2,
            operation_id="op3",
            session_id="session2",
        )

    def tearDown(self):
        """Clean up test database."""
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)

    def test_get_cost_by_task(self):
        """Test getting cost by task ID."""
        task_cost = self.cost_tracker.get_cost_by_task(task_id=1)

        self.assertEqual(task_cost["call_count"], 2)
        self.assertEqual(task_cost["total_tokens"], 4500)
        self.assertGreater(task_cost["total_cost"], 0)
        self.assertIsNotNone(task_cost.get("first_call"))
        self.assertIsNotNone(task_cost.get("last_call"))

    def test_get_cost_by_session(self):
        """Test getting cost by session ID."""
        session_cost = self.cost_tracker.get_cost_by_session(session_id="session1")

        self.assertEqual(session_cost["call_count"], 2)
        self.assertEqual(session_cost["total_tokens"], 4500)
        self.assertGreater(session_cost["total_cost"], 0)

    def test_get_cost_by_operation(self):
        """Test getting cost by operation ID."""
        op_cost = self.cost_tracker.get_cost_by_operation(operation_id="op1")

        self.assertEqual(op_cost["call_count"], 1)
        self.assertEqual(op_cost["total_tokens"], 1500)
        self.assertGreater(op_cost["total_cost"], 0)

    def test_get_project_cost(self):
        """Test getting total project cost."""
        project_cost = self.cost_tracker.get_project_cost()

        self.assertEqual(project_cost["call_count"], 3)
        self.assertEqual(project_cost["total_tokens"], 5250)
        self.assertGreater(project_cost["total_cost"], 0)

    def test_get_cost_by_provider_model(self):
        """Test getting cost breakdown by provider and model."""
        by_provider_model = self.cost_tracker.get_cost_by_provider_model()

        self.assertEqual(len(by_provider_model), 3)

        # Check OpenAI GPT-4
        gpt4 = next(
            (item for item in by_provider_model if item["model"] == "gpt-4"),
            None,
        )
        self.assertIsNotNone(gpt4)
        self.assertEqual(gpt4["provider"], "openai")
        self.assertEqual(gpt4["call_count"], 1)
        self.assertEqual(gpt4["total_tokens"], 1500)


class TestCostTrends(unittest.TestCase):
    """Test cost trend analysis."""

    def setUp(self):
        """Set up test database with time-series data."""
        self.test_db_path = "test_cost_tracker.db"
        self.cost_tracker = CostTracker(db_path=self.test_db_path)

        # Insert data for multiple days
        base_time = datetime.utcnow()
        for day in range(10):
            day_time = base_time - timedelta(days=day)
            # Simulate increasing costs
            cost = 0.01 * (10 - day)  # Decreasing from 0.10 to 0.01

            # Insert directly into database to control timestamps
            conn = sqlite3.connect(self.test_db_path)
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO cost_records
                (id, timestamp, provider, model, prompt_tokens, completion_tokens,
                 total_tokens, prompt_cost, completion_cost, total_cost)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(day),
                    day_time.isoformat(),
                    "openai",
                    "gpt-3.5-turbo",
                    1000,
                    500,
                    1500,
                    cost * 0.4,
                    cost * 0.6,
                    cost,
                ),
            )
            conn.commit()
            conn.close()

    def tearDown(self):
        """Clean up test database."""
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)

    def test_get_cost_trend_daily(self):
        """Test getting daily cost trends."""
        trends = self.cost_tracker.get_cost_trend(period="daily", periods=7)

        self.assertLessEqual(len(trends), 7)
        self.assertGreater(len(trends), 0)

        # Check trend structure
        for trend in trends:
            self.assertIn("time_bucket", trend)
            self.assertIn("total_cost", trend)
            self.assertIn("total_tokens", trend)
            self.assertIn("call_count", trend)
            self.assertIn("growth_rate", trend)
            self.assertIn("trend_direction", trend)

    def test_get_cost_trend_hourly(self):
        """Test getting hourly cost trends."""
        trends = self.cost_tracker.get_cost_trend(period="hourly", periods=24)

        self.assertLessEqual(len(trends), 24)

    def test_invalid_period(self):
        """Test that invalid period raises ValueError."""
        with self.assertRaises(ValueError):
            self.cost_tracker.get_cost_trend(period="invalid")


class TestCostPrediction(unittest.TestCase):
    """Test cost prediction functionality."""

    def setUp(self):
        """Set up test database with historical data."""
        self.test_db_path = "test_cost_tracker.db"
        self.cost_tracker = CostTracker(db_path=self.test_db_path)

        # Insert 30 days of data
        base_time = datetime.utcnow()
        for day in range(30):
            day_time = base_time - timedelta(days=day)
            cost = 0.02  # Consistent $0.02 per day

            conn = sqlite3.connect(self.test_db_path)
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO cost_records
                (id, timestamp, provider, model, prompt_tokens, completion_tokens,
                 total_tokens, prompt_cost, completion_cost, total_cost)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(day),
                    day_time.isoformat(),
                    "openai",
                    "gpt-3.5-turbo",
                    2000,
                    1000,
                    3000,
                    cost * 0.4,
                    cost * 0.6,
                    cost,
                ),
            )
            conn.commit()
            conn.close()

    def tearDown(self):
        """Clean up test database."""
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)

    def test_predict_future_cost_average(self):
        """Test cost prediction using average method."""
        prediction = self.cost_tracker.predict_future_cost(days=30, method="average")

        self.assertIn("prediction_method", prediction)
        self.assertEqual(prediction["prediction_method"], "average")
        self.assertIn("predicted_cost", prediction)
        self.assertIn("confidence_level", prediction)
        self.assertIn("historical_data_points", prediction)
        self.assertEqual(prediction["prediction_period_days"], 30)

        # For consistent $0.02/day, 30 days should be $0.60
        self.assertAlmostEqual(prediction["predicted_cost"], 0.60, places=1)

    def test_predict_future_cost_linear(self):
        """Test cost prediction using linear regression."""
        prediction = self.cost_tracker.predict_future_cost(days=30, method="linear")

        self.assertEqual(prediction["prediction_method"], "linear")
        self.assertIn("predicted_cost", prediction)

    def test_predict_future_cost_exponential(self):
        """Test cost prediction using exponential smoothing."""
        prediction = self.cost_tracker.predict_future_cost(
            days=30, method="exponential"
        )

        self.assertEqual(prediction["prediction_method"], "exponential")
        self.assertIn("predicted_cost", prediction)

    def test_predict_insufficient_data(self):
        """Test prediction with insufficient data."""
        # Create new tracker with no data
        empty_tracker = CostTracker(db_path="empty_cost_tracker.db")
        prediction = empty_tracker.predict_future_cost(days=30)

        self.assertIn("error", prediction)

        if os.path.exists("empty_cost_tracker.db"):
            os.remove("empty_cost_tracker.db")

    def test_invalid_prediction_method(self):
        """Test that invalid prediction method raises ValueError."""
        with self.assertRaises(ValueError):
            self.cost_tracker.predict_future_cost(days=30, method="invalid")


class TestBudgetManagement(unittest.TestCase):
    """Test budget management and alerts."""

    def setUp(self):
        """Set up test database."""
        self.test_db_path = "test_cost_tracker.db"
        self.cost_tracker = CostTracker(db_path=self.test_db_path)

    def tearDown(self):
        """Clean up test database."""
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)

    def test_set_budget(self):
        """Test setting a budget."""
        self.cost_tracker.set_budget(
            budget_type="project",
            budget_limit=100.0,
            alert_threshold_percent=0.8,
        )

        # Verify budget was set
        conn = sqlite3.connect(self.test_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM cost_budgets WHERE budget_type = ?", ("project",))
        row = cursor.fetchone()

        self.assertIsNotNone(row)
        self.assertEqual(row[3], 100.0)  # budget_limit (index 3)
        self.assertEqual(row[4], 80.0)  # alert_threshold (80% of 100)
        self.assertEqual(row[5], 0.8)  # alert_threshold_percent (index 5)

        conn.close()

    def test_budget_alert_on_exceedance(self):
        """Test that alert is created when budget threshold exceeded."""
        # Set budget with very low threshold for testing
        self.cost_tracker.set_budget(
            budget_type="project", budget_limit=10.0, alert_threshold_percent=0.005
        )

        # Record costs that exceed threshold (each call ~$0.00125)
        # 50 calls = $0.0625, which exceeds 0.5% of $10 ($0.05)
        for _ in range(50):
            self.cost_tracker.record_cost(
                provider="openai",
                model="gpt-3.5-turbo",
                prompt_tokens=1000,
                completion_tokens=500,
            )

        # Check for alerts
        alerts = self.cost_tracker.get_cost_alerts(acknowledged=False)

        self.assertGreater(len(alerts), 0)

        # Verify alert structure
        alert = alerts[0]
        self.assertIn("id", alert)
        self.assertIn("alert_type", alert)
        self.assertIn("severity", alert)
        self.assertIn("message", alert)
        self.assertIn("current_cost", alert)

    def test_get_cost_alerts(self):
        """Test getting cost alerts."""
        # Create a budget and exceed it
        self.cost_tracker.set_budget(
            budget_type="project", budget_limit=1.0, alert_threshold_percent=0.005
        )

        # Record costs (50 calls = $0.0625, exceeds 0.5% of $1.0)
        for _ in range(50):
            self.cost_tracker.record_cost(
                provider="openai",
                model="gpt-3.5-turbo",
                prompt_tokens=1000,
                completion_tokens=500,
            )

        # Get alerts
        all_alerts = self.cost_tracker.get_cost_alerts()
        unacknowledged_alerts = self.cost_tracker.get_cost_alerts(
            acknowledged=False
        )

        self.assertGreater(len(all_alerts), 0)
        self.assertGreater(len(unacknowledged_alerts), 0)

    def test_acknowledge_alert(self):
        """Test acknowledging an alert."""
        # Create an alert with low threshold
        self.cost_tracker.set_budget(
            budget_type="project", budget_limit=1.0, alert_threshold_percent=0.005
        )

        # Record costs to exceed threshold
        for _ in range(50):
            self.cost_tracker.record_cost(
                provider="openai",
                model="gpt-3.5-turbo",
                prompt_tokens=1000,
                completion_tokens=500,
            )

        # Get unacknowledged alerts
        alerts = self.cost_tracker.get_cost_alerts(acknowledged=False)
        self.assertGreater(len(alerts), 0)

        # Acknowledge first alert
        alert_id = alerts[0]["id"]
        self.cost_tracker.acknowledge_alert(alert_id)

        # Verify alert is acknowledged
        updated_alerts = self.cost_tracker.get_cost_alerts(acknowledged=False)
        self.assertEqual(len(updated_alerts), len(alerts) - 1)


class TestCostReports(unittest.TestCase):
    """Test cost report generation."""

    def setUp(self):
        """Set up test database with sample data."""
        self.test_db_path = "test_cost_tracker.db"
        self.cost_tracker = CostTracker(db_path=self.test_db_path)

        # Insert sample cost records
        self.cost_tracker.record_cost(
            provider="openai",
            model="gpt-4",
            prompt_tokens=1000,
            completion_tokens=500,
            task_id=1,
        )
        self.cost_tracker.record_cost(
            provider="anthropic",
            model="claude-3-sonnet",
            prompt_tokens=2000,
            completion_tokens=1000,
            task_id=2,
        )

    def tearDown(self):
        """Clean up test database."""
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)

    def test_generate_text_report(self):
        """Test generating text format cost report."""
        report = self.cost_tracker.generate_cost_report(format="text")

        self.assertIn("COST REPORT", report)
        self.assertIn("Project Cost Summary", report)
        self.assertIn("Cost by Provider/Model", report)
        self.assertIn("Recent Trends", report)
        self.assertIn("Cost Prediction", report)
        self.assertIn("$", report)  # Should have dollar amounts

    def test_generate_markdown_report(self):
        """Test generating markdown format cost report."""
        report = self.cost_tracker.generate_cost_report(format="markdown")

        self.assertIn("# Cost Report", report)
        self.assertIn("## Project Cost Summary", report)
        self.assertIn("| Provider | Model | Calls", report)  # Markdown table
        # Note: Report uses single # and ##, not ###

    def test_generate_json_report(self):
        """Test generating JSON format cost report."""
        report = self.cost_tracker.generate_cost_report(format="json")

        # Parse JSON
        report_data = json.loads(report)

        self.assertIn("project_cost", report_data)
        self.assertIn("by_provider_model", report_data)
        self.assertIn("trends", report_data)
        self.assertIn("prediction", report_data)
        self.assertIn("generated_at", report_data)

    def test_export_csv(self):
        """Test exporting cost data as CSV."""
        csv_data = self.cost_tracker.export_cost_data(format="csv")

        self.assertIn("id,timestamp,provider,model", csv_data)
        self.assertIn("openai,gpt-4", csv_data)
        self.assertIn("anthropic,claude-3-sonnet", csv_data)

    def test_export_json(self):
        """Test exporting cost data as JSON."""
        json_data = self.cost_tracker.export_cost_data(format="json")

        data = json.loads(json_data)

        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)

        # Check first record structure
        first_record = data[0]
        self.assertIn("id", first_record)
        self.assertIn("provider", first_record)
        self.assertIn("model", first_record)
        self.assertIn("total_cost", first_record)

    def test_invalid_export_format(self):
        """Test that invalid export format raises ValueError."""
        with self.assertRaises(ValueError):
            self.cost_tracker.export_cost_data(format="invalid")


class TestGlobalCostTracker(unittest.TestCase):
    """Test global cost tracker instance."""

    def test_singleton_pattern(self):
        """Test that get_cost_tracker returns singleton instance."""
        tracker1 = get_cost_tracker()
        tracker2 = get_cost_tracker()

        # Should be the same instance
        self.assertIs(tracker1, tracker2)

    def test_thread_safety(self):
        """Test that cost tracker is thread-safe."""
        import threading

        results = []
        errors = []

        def record_cost():
            try:
                tracker = get_cost_tracker()
                cost_id = tracker.record_cost(
                    provider="openai",
                    model="gpt-3.5-turbo",
                    prompt_tokens=100,
                    completion_tokens=50,
                )
                results.append(cost_id)
            except Exception as e:
                errors.append(e)

        # Create multiple threads
        threads = [threading.Thread(target=record_cost) for _ in range(10)]

        # Start threads
        for thread in threads:
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Check results
        self.assertEqual(len(errors), 0)  # No errors
        self.assertEqual(len(results), 10)  # All threads completed

        # Clean up
        if os.path.exists(COST_TRACKER_DB_PATH):
            os.remove(COST_TRACKER_DB_PATH)


if __name__ == "__main__":
    unittest.main()