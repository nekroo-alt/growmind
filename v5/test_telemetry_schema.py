"""
Test telemetry schema creation - Task 1.1 verification

Tests that the telemetry database schema is properly created and functional.
"""

import os
import sqlite3
import tempfile
from v5.data import TelemetryManager


def test_telemetry_schema_creation():
    """Test that telemetry database schema is created correctly."""
    # Use a temporary database file
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        # Initialize telemetry manager
        manager = TelemetryManager(db_path=db_path)

        # Verify tables exist
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = [row[0] for row in cursor.fetchall()]

        # Check all required tables exist
        expected_tables = ["events", "metrics", "migrations", "operations", "resources"]
        for table in expected_tables:
            assert table in tables, f"Table {table} not found"

        # Verify indexes exist
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='index' ORDER BY name"
        )
        indexes = [row[0] for row in cursor.fetchall()]

        # Check key indexes exist
        expected_indexes = [
            "idx_events_operation",
            "idx_events_timestamp",
            "idx_metrics_operation",
            "idx_operations_timestamp",
            "idx_operations_type_status",
            "idx_resources_operation",
        ]
        for index in expected_indexes:
            assert index in indexes, f"Index {index} not found"

        # Verify operations table schema
        cursor.execute("PRAGMA table_info(operations)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        assert columns["id"] in ["TEXT", "VARCHAR"], "operations.id should be TEXT"
        assert columns["parent_id"] in [
            "TEXT",
            "VARCHAR",
            None,
        ], "operations.parent_id should be TEXT or nullable"
        assert columns["operation_type"] in [
            "TEXT",
            "VARCHAR",
        ], "operations.operation_type should be TEXT"
        assert columns["title"] in [
            "TEXT",
            "VARCHAR",
        ], "operations.title should be TEXT"
        assert columns["status"] in [
            "TEXT",
            "VARCHAR",
        ], "operations.status should be TEXT"
        assert columns["start_time"] in [
            "TEXT",
            "VARCHAR",
            "DATETIME",
        ], "operations.start_time should be TEXT or DATETIME"
        assert columns["end_time"] in [
            "TEXT",
            "VARCHAR",
            "DATETIME",
            None,
        ], "operations.end_time should be TEXT or DATETIME or nullable"
        assert columns["metadata"] in [
            "TEXT",
            "VARCHAR",
            None,
        ], "operations.metadata should be TEXT or nullable"
        assert columns["activity_id"] in [
            "INTEGER",
            "INT",
            None,
        ], "operations.activity_id should be INTEGER or nullable"

        # Verify events table schema
        cursor.execute("PRAGMA table_info(events)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        assert columns["id"] in ["TEXT", "VARCHAR"], "events.id should be TEXT"
        assert columns["operation_id"] in [
            "TEXT",
            "VARCHAR",
        ], "events.operation_id should be TEXT"
        assert columns["event_type"] in [
            "TEXT",
            "VARCHAR",
        ], "events.event_type should be TEXT"
        assert columns["severity"] in [
            "TEXT",
            "VARCHAR",
        ], "events.severity should be TEXT"
        assert columns["timestamp"] in [
            "TEXT",
            "VARCHAR",
            "DATETIME",
        ], "events.timestamp should be TEXT or DATETIME"
        assert columns["message"] in [
            "TEXT",
            "VARCHAR",
        ], "events.message should be TEXT"
        assert columns["context"] in [
            "TEXT",
            "VARCHAR",
            None,
        ], "events.context should be TEXT or nullable"

        # Verify metrics table schema
        cursor.execute("PRAGMA table_info(metrics)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        assert columns["id"] in ["TEXT", "VARCHAR"], "metrics.id should be TEXT"
        assert columns["operation_id"] in [
            "TEXT",
            "VARCHAR",
        ], "metrics.operation_id should be TEXT"
        assert columns["metric_name"] in [
            "TEXT",
            "VARCHAR",
        ], "metrics.metric_name should be TEXT"
        assert columns["metric_value"] in [
            "REAL",
            "FLOAT",
            "DOUBLE",
        ], "metrics.metric_value should be REAL"
        assert columns["unit"] in [
            "TEXT",
            "VARCHAR",
            None,
        ], "metrics.unit should be TEXT or nullable"
        assert columns["timestamp"] in [
            "TEXT",
            "VARCHAR",
            "DATETIME",
        ], "metrics.timestamp should be TEXT or DATETIME"

        # Verify resources table schema
        cursor.execute("PRAGMA table_info(resources)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        assert columns["id"] in ["TEXT", "VARCHAR"], "resources.id should be TEXT"
        assert columns["operation_id"] in [
            "TEXT",
            "VARCHAR",
        ], "resources.operation_id should be TEXT"
        assert columns["resource_type"] in [
            "TEXT",
            "VARCHAR",
        ], "resources.resource_type should be TEXT"
        assert columns["resource_name"] in [
            "TEXT",
            "VARCHAR",
            None,
        ], "resources.resource_name should be TEXT or nullable"
        assert columns["value"] in [
            "REAL",
            "FLOAT",
            "DOUBLE",
        ], "resources.value should be REAL"
        assert columns["unit"] in [
            "TEXT",
            "VARCHAR",
            None,
        ], "resources.unit should be TEXT or nullable"
        assert columns["timestamp"] in [
            "TEXT",
            "VARCHAR",
            "DATETIME",
        ], "resources.timestamp should be TEXT or DATETIME"

        # Verify migrations table schema
        cursor.execute("PRAGMA table_info(migrations)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        assert columns["version"] in [
            "INTEGER",
            "INT",
        ], "migrations.version should be INTEGER"
        assert columns["applied_at"] in [
            "TEXT",
            "VARCHAR",
            "DATETIME",
        ], "migrations.applied_at should be TEXT or DATETIME"
        assert columns["description"] in [
            "TEXT",
            "VARCHAR",
        ], "migrations.description should be TEXT"

        conn.close()

        print("✅ All schema verification tests passed!")
        return True

    finally:
        # Clean up temporary file
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_operation_crud():
    """Test create, read, update, delete operations."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        manager = TelemetryManager(db_path=db_path)

        # Test creating an operation
        op_id = manager.start_operation(
            operation_type="implementation",
            title="Test Task Implementation",
            activity_id=123,
        )
        assert op_id is not None, "Operation ID should not be None"

        # Test reading an operation
        op = manager.get_operation(op_id)
        assert op is not None, "Operation should exist"
        assert op["operation_type"] == "implementation", "Operation type mismatch"
        assert op["title"] == "Test Task Implementation", "Title mismatch"
        assert op["status"] == "started", "Status should be started"
        assert op["activity_id"] == 123, "Activity ID mismatch"

        # Test ending an operation
        manager.end_operation(op_id, "completed")
        op = manager.get_operation(op_id)
        assert op["status"] == "completed", "Status should be completed"
        assert op["end_time"] is not None, "End time should be set"

        # Test hierarchical operations
        child_op_id = manager.start_operation(
            operation_type="test_generation", title="Generate Tests", parent_id=op_id
        )
        children = manager.get_child_operations(op_id)
        assert len(children) == 1, "Should have one child operation"
        assert children[0]["id"] == child_op_id, "Child ID mismatch"

        # Test listing operations
        ops = manager.list_operations(operation_type="implementation")
        assert len(ops) >= 1, "Should have at least one implementation operation"

        ops = manager.list_operations(status="completed")
        assert len(ops) >= 1, "Should have at least one completed operation"

        print("✅ All operation CRUD tests passed!")
        return True

    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_events_and_metrics():
    """Test recording events and metrics."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        manager = TelemetryManager(db_path=db_path)

        # Create an operation
        op_id = manager.start_operation(
            operation_type="implementation", title="Test Operation"
        )

        # Test recording an event
        event_id = manager.record_event(
            operation_id=op_id,
            event_type="started",
            severity="info",
            message="Implementation started",
            context={"task_id": 42},
        )
        assert event_id is not None, "Event ID should not be None"

        # Test retrieving events
        events = manager.get_operation_events(op_id)
        assert len(events) == 1, "Should have one event"
        assert events[0]["event_type"] == "started", "Event type mismatch"
        assert events[0]["severity"] == "info", "Severity mismatch"
        assert events[0]["message"] == "Implementation started", "Message mismatch"

        # Test recording a metric
        metric_id = manager.record_metric(
            operation_id=op_id,
            metric_name="tokens_used",
            metric_value=1250.0,
            unit="tokens",
        )
        assert metric_id is not None, "Metric ID should not be None"

        # Test retrieving metrics
        metrics = manager.get_operation_metrics(op_id)
        assert len(metrics) == 1, "Should have one metric"
        assert metrics[0]["metric_name"] == "tokens_used", "Metric name mismatch"
        assert metrics[0]["metric_value"] == 1250.0, "Metric value mismatch"
        assert metrics[0]["unit"] == "tokens", "Unit mismatch"

        # Test metric summary
        summary = manager.get_metric_summary(op_id, "tokens_used")
        assert summary is not None, "Summary should exist"
        assert summary["count"] == 1, "Count should be 1"
        assert summary["total"] == 1250.0, "Total should be 1250.0"
        assert summary["avg"] == 1250.0, "Average should be 1250.0"
        assert summary["min"] == 1250.0, "Min should be 1250.0"
        assert summary["max"] == 1250.0, "Max should be 1250.0"

        print("✅ All events and metrics tests passed!")
        return True

    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_resources():
    """Test recording resource usage."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        manager = TelemetryManager(db_path=db_path)

        # Create an operation
        op_id = manager.start_operation(
            operation_type="implementation", title="Test Operation"
        )

        # Test recording CPU usage
        cpu_id = manager.record_resource_usage(
            operation_id=op_id, resource_type="cpu", value=45.5, unit="%"
        )
        assert cpu_id is not None, "Resource ID should not be None"

        # Test recording memory usage
        mem_id = manager.record_resource_usage(
            operation_id=op_id, resource_type="memory", value=512.0, unit="MB"
        )
        assert mem_id is not None, "Resource ID should not be None"

        # Test retrieving resources
        resources = manager.get_operation_resources(op_id)
        assert len(resources) == 2, "Should have two resource records"

        cpu_resource = next((r for r in resources if r["resource_type"] == "cpu"), None)
        assert cpu_resource is not None, "CPU resource should exist"
        assert cpu_resource["value"] == 45.5, "CPU value mismatch"
        assert cpu_resource["unit"] == "%", "CPU unit mismatch"

        mem_resource = next(
            (r for r in resources if r["resource_type"] == "memory"), None
        )
        assert mem_resource is not None, "Memory resource should exist"
        assert mem_resource["value"] == 512.0, "Memory value mismatch"
        assert mem_resource["unit"] == "MB", "Memory unit mismatch"

        print("✅ All resource tests passed!")
        return True

    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_migration_system():
    """Test migration tracking system."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        manager = TelemetryManager(db_path=db_path)

        # Test initial migration version
        version = manager.get_migration_version()
        assert version == 0, "Initial version should be 0"

        # Test applying a migration
        migration_sql = """
        -- Sample migration
        CREATE TABLE IF NOT EXISTS test_table (
            id INTEGER PRIMARY KEY,
            name TEXT
        );
        """
        manager.apply_migration(1, "Test migration", migration_sql)

        # Check version increased
        version = manager.get_migration_version()
        assert version == 1, "Version should be 1 after migration"

        # Test that migration is not reapplied
        manager.apply_migration(1, "Test migration", migration_sql)
        version = manager.get_migration_version()
        assert version == 1, "Version should still be 1 (not reapplied)"

        print("✅ All migration system tests passed!")
        return True

    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


if __name__ == "__main__":
    print("Running Telemetry Schema Tests (Task 1.1)...\n")

    test_telemetry_schema_creation()
    test_operation_crud()
    test_events_and_metrics()
    test_resources()
    test_migration_system()

    print("\n" + "=" * 60)
    print("All Task 1.1 tests passed! ✅")
    print("=" * 60)
