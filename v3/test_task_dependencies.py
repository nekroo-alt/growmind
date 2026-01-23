"""
Test script for Task 3.1: Task Dependency Graph
Tests the dependency tracking and validation functionality.
"""

import os
import sqlite3
import json
from v3.data.db_manager import (
    init_db,
    log_task,
    get_pending_task,
    get_task_dependencies,
    check_dependencies_satisfied,
    validate_no_circular_dependencies,
    update_task_dependencies,
    get_task_dependency_graph,
    TASK_DB_PATH,
)


def setup_test_db():
    """Setup a fresh test database."""
    # Remove existing test database if it exists
    if os.path.exists(TASK_DB_PATH):
        os.remove(TASK_DB_PATH)

    init_db()
    print("✓ Test database initialized")


def test_basic_dependency_tracking():
    """Test that tasks can have dependencies and they are stored correctly."""
    print("\n--- Test 1: Basic Dependency Tracking ---")

    # Create tasks with dependencies
    log_task("Task A", "pending", module="module1", depends_on=[])
    log_task("Task B", "pending", module="module1", depends_on=[1])
    log_task("Task C", "pending", module="module1", depends_on=[1, 2])

    # Verify dependencies are stored
    deps_b = get_task_dependencies(2)
    deps_c = get_task_dependencies(3)

    assert deps_b == [1], f"Expected [1], got {deps_b}"
    assert deps_c == [1, 2], f"Expected [1, 2], got {deps_c}"

    print("✓ Tasks can have dependencies")
    print(f"  Task 2 depends on: {deps_b}")
    print(f"  Task 3 depends on: {deps_c}")


def test_dependency_satisfaction():
    """Test that tasks with unsatisfied dependencies are not returned."""
    print("\n--- Test 2: Dependency Satisfaction ---")

    # Task A has no dependencies
    task = get_pending_task()
    assert task is not None and task["title"] == "Task A", "Task A should be available"
    print("✓ Task with no dependencies is available")

    # Complete Task A
    conn = sqlite3.connect(TASK_DB_PATH)
    conn.execute("UPDATE tasks SET status = 'completed' WHERE id = 1")
    conn.commit()
    conn.close()

    # Now Task B should be available
    task = get_pending_task()
    assert (
        task is not None and task["title"] == "Task B"
    ), "Task B should be available after Task A completes"
    print("✓ Task becomes available after dependency completes")

    # Complete Task B
    conn = sqlite3.connect(TASK_DB_PATH)
    conn.execute("UPDATE tasks SET status = 'completed' WHERE id = 2")
    conn.commit()
    conn.close()

    # Now Task C should be available
    task = get_pending_task()
    assert (
        task is not None and task["title"] == "Task C"
    ), "Task C should be available after Task A and B complete"
    print("✓ Task with multiple dependencies becomes available")


def test_circular_dependency_detection():
    """Test that circular dependencies are detected and prevented."""
    print("\n--- Test 3: Circular Dependency Detection ---")

    # Create new tasks for circular dependency test
    log_task("Task X", "pending", module="module1", depends_on=[])
    log_task("Task Y", "pending", module="module1", depends_on=[])

    # Try to make Task X depend on Task Y
    success, msg = update_task_dependencies(4, [5])
    assert success, f"Expected success, got: {msg}"
    print("✓ Valid dependency can be added")

    # Try to make Task Y depend on Task X (creating circular dependency)
    success, msg = update_task_dependencies(5, [4])
    assert not success, "Circular dependency should be detected"
    assert (
        "Circular dependency" in msg
    ), f"Expected circular dependency message, got: {msg}"
    print(f"✓ Circular dependency detected: {msg}")


def test_dependency_graph():
    """Test that the complete dependency graph can be retrieved."""
    print("\n--- Test 4: Dependency Graph ---")

    graph = get_task_dependency_graph()

    # Verify structure
    assert isinstance(graph, dict), "Graph should be a dictionary"
    assert 1 in graph, "Task 1 should be in graph"

    # Verify task 3 has correct dependencies
    assert graph[3]["depends_on"] == [
        1,
        2,
    ], f"Task 3 dependencies should be [1, 2], got {graph[3]['depends_on']}"

    print("✓ Dependency graph can be retrieved")
    print(f"  Graph contains {len(graph)} tasks")


def test_dependency_chain():
    """Test that dependency chains work correctly."""
    print("\n--- Test 5: Dependency Chain ---")

    # Mark all previous tasks as completed to clean up
    conn = sqlite3.connect(TASK_DB_PATH)
    conn.execute("UPDATE tasks SET status = 'completed' WHERE status = 'pending'")
    conn.commit()
    conn.close()

    # Create a chain: Task D -> Task E -> Task F
    log_task("Task D", "pending", module="module1", depends_on=[])
    log_task("Task E", "pending", module="module1", depends_on=[])
    log_task("Task F", "pending", module="module1", depends_on=[])

    # Get the actual task IDs
    conn = sqlite3.connect(TASK_DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, title FROM tasks WHERE title IN ('Task D', 'Task E', 'Task F') ORDER BY id"
    )
    task_ids = {row[1]: row[0] for row in cursor.fetchall()}
    conn.close()

    task_d_id = task_ids["Task D"]
    task_e_id = task_ids["Task E"]
    task_f_id = task_ids["Task F"]

    # Update dependencies
    update_task_dependencies(task_e_id, [task_d_id])
    update_task_dependencies(task_f_id, [task_e_id])

    # Only Task D should be available
    task = get_pending_task()
    print(f"  Available task: {task['title'] if task else None}")
    assert (
        task is not None and task["title"] == "Task D"
    ), f"Only Task D should be available, got {task['title'] if task else None}"
    print("✓ Dependency chain prevents downstream tasks from being available")

    # Complete the chain
    conn = sqlite3.connect(TASK_DB_PATH)
    conn.execute(
        "UPDATE tasks SET status = 'completed' WHERE id = ?", (task_d_id,)
    )  # Task D
    conn.execute(
        "UPDATE tasks SET status = 'completed' WHERE id = ?", (task_e_id,)
    )  # Task E
    conn.commit()
    conn.close()

    # Now Task F should be available
    task = get_pending_task()
    assert (
        task is not None and task["title"] == "Task F"
    ), "Task F should be available after chain completes"
    print("✓ Dependency chain works correctly")


def test_nonexistent_dependency():
    """Test that dependencies on non-existent tasks are rejected."""
    print("\n--- Test 6: Non-existent Dependency ---")

    log_task("Task G", "pending", module="module1", depends_on=[])

    # Try to add dependency on non-existent task
    success, msg = update_task_dependencies(9, [999])
    assert not success, "Non-existent dependency should be rejected"
    assert "does not exist" in msg, f"Expected 'does not exist' message, got: {msg}"
    print(f"✓ Non-existent dependency rejected: {msg}")


def run_all_tests():
    """Run all tests."""
    print("=" * 60)
    print("Testing Task 3.1: Task Dependency Graph")
    print("=" * 60)

    setup_test_db()
    test_basic_dependency_tracking()
    test_dependency_satisfaction()
    test_circular_dependency_detection()
    test_dependency_graph()
    test_dependency_chain()
    test_nonexistent_dependency()

    print("\n" + "=" * 60)
    print("✓ ALL TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
