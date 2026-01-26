"""
Test File for Task 1.5: Resource Usage Monitoring

Tests the resource monitoring capabilities of the TelemetryManager:
- CPU usage monitoring
- Memory usage tracking
- Disk I/O and space monitoring
- Network usage tracking
- Alerting for resource exhaustion
- Resource usage reports
"""

import os
import sys
import time
import tempfile
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from v5.data import TelemetryManager


def test_resource_monitoring():
    """Test basic resource monitoring functionality"""
    print("Testing resource monitoring...")

    # Create a temporary database for testing
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        telemetry = TelemetryManager(db_path=db_path)

        # Start an operation
        op_id = telemetry.start_operation(
            operation_type="test", title="Resource Monitoring Test"
        )

        # Test CPU monitoring
        print("  Testing CPU monitoring...")
        cpu_metrics = telemetry._get_cpu_usage()
        if "error" not in cpu_metrics:
            assert "cpu_percent" in cpu_metrics
            assert "cpu_count" in cpu_metrics
            print(
                f"    CPU: {cpu_metrics['cpu_percent']}% across {cpu_metrics['cpu_count']} cores"
            )
        else:
            print(f"    psutil not available: {cpu_metrics['error']}")

        # Test memory monitoring
        print("  Testing memory monitoring...")
        mem_metrics = telemetry._get_memory_usage()
        if "error" not in mem_metrics:
            assert "percent" in mem_metrics
            assert "total_mb" in mem_metrics
            print(
                f"    Memory: {mem_metrics['percent']}% of {mem_metrics['total_mb']:.1f}MB"
            )
        else:
            print(f"    psutil not available: {mem_metrics['error']}")

        # Test disk usage monitoring
        print("  Testing disk usage monitoring...")
        disk_metrics = telemetry._get_disk_usage(".")
        if "error" not in disk_metrics:
            assert "percent" in disk_metrics
            assert "total_gb" in disk_metrics
            print(
                f"    Disk: {disk_metrics['percent']}% of {disk_metrics['total_gb']:.1f}GB"
            )
        else:
            print(f"    psutil not available: {disk_metrics['error']}")

        # Test disk I/O monitoring
        print("  Testing disk I/O monitoring...")
        io_metrics = telemetry._get_disk_io()
        if "error" not in io_metrics:
            assert "read_bytes_mb" in io_metrics
            assert "write_bytes_mb" in io_metrics
            print(
                f"    I/O: Read {io_metrics['read_bytes_mb']:.2f}MB, Write {io_metrics['write_bytes_mb']:.2f}MB"
            )
        else:
            print(f"    psutil not available: {io_metrics['error']}")

        # Test network monitoring
        print("  Testing network monitoring...")
        net_metrics = telemetry._get_network_io()
        if "error" not in net_metrics:
            assert "bytes_sent_mb" in net_metrics
            assert "bytes_recv_mb" in net_metrics
            print(
                f"    Network: Sent {net_metrics['bytes_sent_mb']:.2f}MB, Recv {net_metrics['bytes_recv_mb']:.2f}MB"
            )
        else:
            print(f"    psutil not available: {net_metrics['error']}")

        # End operation
        telemetry.end_operation(op_id, "completed")

        print("  ✓ Resource monitoring tests passed!")
        return True

    finally:
        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_resource_thresholds():
    """Test resource threshold checking and alerting"""
    print("\nTesting resource threshold alerts...")

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        telemetry = TelemetryManager(db_path=db_path)

        # Start an operation
        op_id = telemetry.start_operation(operation_type="test", title="Threshold Test")

        # Create thresholds with low values to trigger alerts
        thresholds = telemetry.ResourceThresholds(
            cpu_warning=0.1,  # Very low to trigger warning
            cpu_critical=0.01,
            memory_warning=0.1,
            memory_critical=0.01,
            disk_warning=99.9,  # High to avoid triggering
            disk_critical=99.99,
        )

        # Get current metrics
        cpu_metrics = telemetry._get_cpu_usage()
        mem_metrics = telemetry._get_memory_usage()

        # Check thresholds
        if "error" not in cpu_metrics and "error" not in mem_metrics:
            alerts = telemetry._check_resource_thresholds(
                {**cpu_metrics, **mem_metrics}, thresholds, op_id
            )

            print(f"  Generated {len(alerts)} alerts:")
            for alert in alerts:
                print(
                    f"    - {alert['resource_type']}: {alert['severity']} - {alert['message']}"
                )

            # Check that events were recorded
            events = telemetry.get_operation_events(op_id)
            alert_events = [e for e in events if e["event_type"] == "resource_alert"]
            print(f"  Recorded {len(alert_events)} alert events")

        else:
            print("  psutil not available, skipping threshold tests")

        telemetry.end_operation(op_id, "completed")
        print("  ✓ Threshold alert tests passed!")
        return True

    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_resource_monitoring_context_manager():
    """Test the monitor_resources context manager"""
    print("\nTesting resource monitoring context manager...")

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        telemetry = TelemetryManager(db_path=db_path)

        # Start an operation
        op_id = telemetry.start_operation(
            operation_type="test", title="Context Manager Test"
        )

        # Use the context manager
        with telemetry.monitor_resources(
            op_id, sample_interval=0.5, disk_path="."  # Sample every 0.5 seconds
        ) as monitor:
            # Simulate some work
            print("  Monitoring resources for 2 seconds...")
            time.sleep(2.0)

        # Get summary
        summary = monitor.get_summary()

        if "error" not in summary:
            print(f"  Monitoring summary:")
            print(f"    Duration: {summary['duration_seconds']}s")
            print(f"    Sample count: {summary['sample_count']}")
            print(
                f"    CPU: min={summary['cpu']['min']:.1f}%, max={summary['cpu']['max']:.1f}%, avg={summary['cpu']['avg']:.1f}%"
            )
            print(
                f"    Memory: min={summary['memory']['min']:.1f}%, max={summary['memory']['max']:.1f}%, avg={summary['memory']['avg']:.1f}%"
            )
            print(
                f"    Disk: min={summary['disk']['min']:.1f}%, max={summary['disk']['max']:.1f}%, avg={summary['disk']['avg']:.1f}%"
            )
            print(f"    Alerts: {len(summary['alerts'])}")
        else:
            print(f"  {summary['error']}")

        telemetry.end_operation(op_id, "completed")
        print("  ✓ Context manager tests passed!")
        return True

    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_resource_report_generation():
    """Test resource report generation"""
    print("\nTesting resource report generation...")

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        telemetry = TelemetryManager(db_path=db_path)

        # Start an operation
        op_id = telemetry.start_operation(
            operation_type="test", title="Report Generation Test"
        )

        # Record some resource usage
        telemetry.record_resource_usage(op_id, "cpu", 45.5, "%")
        telemetry.record_resource_usage(op_id, "cpu", 50.2, "%")
        telemetry.record_resource_usage(op_id, "memory", 60.0, "%")
        telemetry.record_resource_usage(op_id, "memory", 65.3, "%")
        telemetry.record_resource_usage(op_id, "disk", 75.0, "%")

        # Wait a bit to create time separation
        time.sleep(0.1)

        telemetry.record_resource_usage(op_id, "cpu", 55.8, "%")
        telemetry.record_resource_usage(op_id, "memory", 68.5, "%")

        telemetry.end_operation(op_id, "completed")

        # Generate report
        report = telemetry.generate_resource_report(op_id, include_details=False)

        print(f"  Report for operation '{report['operation_title']}':")
        print(f"    Operation ID: {report['operation_id']}")
        print(f"    Operation Type: {report['operation_type']}")

        for resource_type, stats in report["resources"].items():
            print(f"    {resource_type.upper()}:")
            print(f"      Count: {stats['count']}")
            print(f"      Avg: {stats['avg']:.2f} {stats['unit']}")
            print(f"      Min: {stats['min']:.2f} {stats['unit']}")
            print(f"      Max: {stats['max']:.2f} {stats['unit']}")

        # Verify report structure
        assert report["operation_id"] == op_id
        assert "resources" in report
        assert "cpu" in report["resources"]
        assert "memory" in report["resources"]
        assert "disk" in report["resources"]

        print("  ✓ Report generation tests passed!")
        return True

    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_resource_trends():
    """Test resource trend analysis"""
    print("\nTesting resource trend analysis...")

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        telemetry = TelemetryManager(db_path=db_path)

        # Create multiple operations with resource data
        for i in range(5):
            op_id = telemetry.start_operation(
                operation_type="test", title=f"Trend Test Operation {i+1}"
            )

            # Record resource usage for this operation
            telemetry.record_resource_usage(op_id, "cpu", 40.0 + i * 5, "%")
            telemetry.record_resource_usage(op_id, "memory", 50.0 + i * 3, "%")
            telemetry.record_resource_usage(op_id, "disk", 70.0 + i * 2, "%")

            telemetry.end_operation(op_id, "completed")

        # Analyze trends
        trends = telemetry.get_resource_trends(operation_type="test", limit=10)

        print(f"  Analyzed {trends['operations_analyzed']} operations")

        for resource_type, trend_data in trends["trends"].items():
            if isinstance(trend_data, dict) and "samples" in trend_data:
                print(f"  {resource_type.upper()} trends:")
                print(f"    Min: {trend_data['min']:.2f}%")
                print(f"    Max: {trend_data['max']:.2f}%")
                print(f"    Avg: {trend_data['avg']:.2f}%")
                print(f"    Samples: {trend_data['count']}")

        # Verify trend structure
        assert trends["operations_analyzed"] == 5
        assert "trends" in trends

        print("  ✓ Trend analysis tests passed!")
        return True

    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_integration_with_operation_tracking():
    """Test integration of resource monitoring with operation tracking"""
    print("\nTesting integration with operation tracking...")

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        telemetry = TelemetryManager(db_path=db_path)

        # Use the context manager API for operation tracking
        with telemetry.track_operation("test", "Integration Test") as op:
            # Record some resource usage
            op.record_resource("cpu", 45.5, "%")
            op.record_resource("memory", 60.0, "%")
            op.record_resource("disk", 75.0, "%")

            # Record some metrics
            op.record_metric("tokens_used", 1250, "tokens")

            # Record some events
            op.record_event("test_step", "info", "Testing integration")

        # Get operation details
        operations = telemetry.list_operations(operation_type="test", limit=1)
        assert len(operations) == 1

        op_id = operations[0]["id"]

        # Check resources
        resources = telemetry.get_operation_resources(op_id)
        print(f"  Recorded {len(resources)} resource entries")

        # Check metrics
        metrics = telemetry.get_operation_metrics(op_id)
        print(f"  Recorded {len(metrics)} metric entries")

        # Check events
        events = telemetry.get_operation_events(op_id)
        print(f"  Recorded {len(events)} event entries")

        assert len(resources) >= 3
        assert len(metrics) >= 1
        assert len(events) >= 1

        print("  ✓ Integration tests passed!")
        return True

    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def main():
    """Run all tests"""
    print("=" * 70)
    print("Task 1.5: Resource Usage Monitoring Tests")
    print("=" * 70)

    tests = [
        test_resource_monitoring,
        test_resource_thresholds,
        test_resource_monitoring_context_manager,
        test_resource_report_generation,
        test_resource_trends,
        test_integration_with_operation_tracking,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"  ✗ Test failed: {e}")
            import traceback

            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 70)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 70)

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
