import os
import sqlite3
from v3.data.db_manager import log_activity, init_db, ACTIVITY_DB_PATH


def test_log_activity_with_telemetry():
    # Ensure DB is initialized
    init_db()

    # Test data
    summary = "Test Activity with Telemetry"
    action = "TEST"
    status = "Success"
    cot_blob = "Thinking about tests..."
    commit_hash = "abc1234"
    tokens_used = 150
    estimated_cost = 0.00045

    # Log the activity
    log_activity(
        summary=summary,
        action=action,
        status=status,
        cot_blob=cot_blob,
        commit_hash=commit_hash,
        tokens_used=tokens_used,
        estimated_cost=estimated_cost,
    )

    # Verify the data in the database
    conn = sqlite3.connect(ACTIVITY_DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM activities WHERE summary = ? ORDER BY timestamp DESC LIMIT 1",
        (summary,),
    )
    row = cursor.fetchone()
    conn.close()

    assert row is not None
    assert row["summary"] == summary
    assert row["action"] == action
    assert row["status"] == status
    assert row["CoT_blob"] == cot_blob
    assert row["commit_hash"] == commit_hash
    assert row["tokens_used"] == tokens_used
    assert row["estimated_cost"] == estimated_cost

    print("Test passed: log_activity correctly stores tokens_used and estimated_cost.")


if __name__ == "__main__":
    try:
        test_log_activity_with_telemetry()
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback

        traceback.print_exc()
