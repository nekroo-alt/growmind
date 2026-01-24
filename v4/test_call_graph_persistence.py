"""
Unit tests for Call Graph Persistence Module (V5)

Tests cover:
- Database initialization and schema
- Call graph storage and retrieval
- Function usage tracking
- Hot/cold function identification
- Import dependency tracking
- Export functionality (JSON, DOT, GraphML)
- Call graph merging
- Statistics generation
"""

import os
import sqlite3
import tempfile
import json
from datetime import datetime
from data.call_graph_persistence import CallGraphPersistence


def test_database_initialization():
    """Test that database is properly initialized with correct schema."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        persistence = CallGraphPersistence(db_path)

        # Verify tables exist
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table'
        """)
        tables = {row[0] for row in cursor.fetchall()}

        assert "call_graph" in tables
        assert "function_usage" in tables
        assert "import_dependencies" in tables
        assert "file_metadata" in tables

        conn.close()
        print("✓ Database initialization test passed")


def test_call_graph_storage():
    """Test storing and retrieving call graph."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        persistence = CallGraphPersistence(db_path)

        # Sample call graph
        call_graph = {
            "function_a": [
                {"callee": "function_b", "line_number": 10, "is_external": False},
                {"callee": "function_c", "line_number": 15, "is_external": False}
            ],
            "function_b": [
                {"callee": "function_d", "line_number": 20, "is_external": False}
            ]
        }

        # Store call graph
        persistence.store_call_graph("test_file.py", call_graph)

        # Retrieve call graph
        retrieved = persistence.get_call_graph("test_file.py")

        assert len(retrieved) == 2
        assert "function_a" in retrieved
        assert "function_b" in retrieved

        # Check callees
        callees_a = retrieved["function_a"]
        assert len(callees_a) == 2
        assert callees_a[0]["callee"] == "function_b"
        assert callees_a[0]["call_count"] == 1

        print("✓ Call graph storage test passed")


def test_function_usage_tracking():
    """Test tracking function usage statistics."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        persistence = CallGraphPersistence(db_path)

        # Store call graph (which updates function usage)
        call_graph = {
            "function_a": [
                {"callee": "function_b", "line_number": 10, "is_external": False}
            ]
        }
        persistence.store_call_graph("test_file.py", call_graph)

        # Store again to increment counts
        persistence.store_call_graph("test_file.py", call_graph)

        # Get usage statistics
        stats = persistence.get_usage_statistics("test_file.py")

        assert len(stats) == 2  # function_a and function_b

        # Find function_a and function_b
        func_a = next((f for f in stats if f["function_name"] == "function_a"), None)
        func_b = next((f for f in stats if f["function_name"] == "function_b"), None)

        assert func_a is not None
        assert func_b is not None
        assert func_a["call_count"] >= 1
        assert func_b["call_count"] >= 1

        print("✓ Function usage tracking test passed")


def test_hot_cold_function_identification():
    """Test identification of hot and cold functions."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        persistence = CallGraphPersistence(db_path)

        # Store call graph with varying call counts
        call_graph_hot = {
            "hot_function": [
                {"callee": "another_hot", "line_number": 10, "is_external": False}
            ]
        }
        call_graph_cold = {
            "cold_function": [
                {"callee": "rarely_used", "line_number": 20, "is_external": False}
            ]
        }

        # Store multiple times to create hot functions
        for _ in range(15):
            persistence.store_call_graph("hot_file.py", call_graph_hot)

        # Store once for cold function
        persistence.store_call_graph("cold_file.py", call_graph_cold)

        # Identify hot/cold functions
        hot, cold = persistence.identify_hot_cold_functions(
            hot_threshold=10,
            cold_threshold=2
        )

        # Check hot functions
        assert len(hot) >= 1
        hot_funcs = [f["function_name"] for f in hot]
        assert "hot_function" in hot_funcs or "another_hot" in hot_funcs

        # Check cold functions
        assert len(cold) >= 1
        cold_funcs = [f["function_name"] for f in cold]
        assert "cold_function" in cold_funcs or "rarely_used" in cold_funcs

        print("✓ Hot/cold function identification test passed")


def test_import_dependency_storage():
    """Test storing and retrieving import dependencies."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        persistence = CallGraphPersistence(db_path)

        # Sample import dependencies
        import_deps = {
            "modules": ["os", "sys", "json"],
            "from_imports": {
                "typing": ["List", "Dict", "Optional"],
                "ast": ["parse", "Import"]
            },
            "line_numbers": {
                "os": 1,
                "sys": 2,
                "json": 3,
                "from typing": 5,
                "from ast": 6
            }
        }

        # Store import dependencies
        persistence.store_import_dependencies("test_file.py", import_deps)

        # Retrieve import dependencies
        retrieved = persistence.get_import_dependencies("test_file.py")

        assert len(retrieved) == 5  # 3 modules + 2 from imports

        # Check simple imports
        simple_imports = [d for d in retrieved if d["import_type"] == "import"]
        assert len(simple_imports) == 3
        modules = {d["module_name"] for d in simple_imports}
        assert "os" in modules
        assert "sys" in modules
        assert "json" in modules

        # Check from imports
        from_imports = [d for d in retrieved if d["import_type"] == "from"]
        assert len(from_imports) == 2
        from_modules = {d["module_name"] for d in from_imports}
        assert "typing" in from_modules
        assert "ast" in from_modules

        print("✓ Import dependency storage test passed")


def test_export_json():
    """Test exporting call graph to JSON format."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        persistence = CallGraphPersistence(db_path)

        # Store call graph
        call_graph = {
            "function_a": [
                {"callee": "function_b", "line_number": 10, "is_external": False}
            ]
        }
        persistence.store_call_graph("test_file.py", call_graph)

        # Export to JSON
        exported = persistence.export_call_graph(format="json", file_path="test_file.py")

        # Verify it's valid JSON
        parsed = json.loads(exported)
        assert isinstance(parsed, dict)
        assert "function_a" in parsed

        print("✓ JSON export test passed")


def test_export_dot():
    """Test exporting call graph to DOT format."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        persistence = CallGraphPersistence(db_path)

        # Store call graph
        call_graph = {
            "function_a": [
                {"callee": "function_b", "line_number": 10, "is_external": False}
            ]
        }
        persistence.store_call_graph("test_file.py", call_graph)

        # Export to DOT
        exported = persistence.export_call_graph(format="dot", file_path="test_file.py")

        # Verify DOT format
        assert exported.startswith("digraph CallGraph {")
        assert exported.endswith("}")
        assert "function_a" in exported
        assert "function_b" in exported
        assert "->" in exported  # Edge notation

        print("✓ DOT export test passed")


def test_export_graphml():
    """Test exporting call graph to GraphML format."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        persistence = CallGraphPersistence(db_path)

        # Store call graph
        call_graph = {
            "function_a": [
                {"callee": "function_b", "line_number": 10, "is_external": False}
            ]
        }
        persistence.store_call_graph("test_file.py", call_graph)

        # Export to GraphML
        exported = persistence.export_call_graph(format="graphml", file_path="test_file.py")

        # Verify GraphML format
        assert exported.startswith('<?xml version="1.0"')
        assert '<graphml xmlns=' in exported
        assert '<graph id="CallGraph"' in exported
        assert '</graphml>' in exported

        print("✓ GraphML export test passed")


def test_merge_call_graphs():
    """Test merging call graphs from multiple databases."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path1 = os.path.join(tmpdir, "test1.db")
        db_path2 = os.path.join(tmpdir, "test2.db")

        # Create first database
        persistence1 = CallGraphPersistence(db_path1)
        call_graph1 = {
            "function_a": [
                {"callee": "function_b", "line_number": 10, "is_external": False}
            ]
        }
        persistence1.store_call_graph("file1.py", call_graph1)

        # Create second database
        persistence2 = CallGraphPersistence(db_path2)
        call_graph2 = {
            "function_c": [
                {"callee": "function_d", "line_number": 20, "is_external": False}
            ]
        }
        persistence2.store_call_graph("file2.py", call_graph2)

        # Merge second database into first
        persistence1.merge_call_graphs(db_path2)

        # Verify merged data
        stats = persistence1.get_usage_statistics()
        assert len(stats) >= 4  # function_a, function_b, function_c, function_d

        print("✓ Call graph merge test passed")


def test_statistics():
    """Test overall statistics generation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        persistence = CallGraphPersistence(db_path)

        # Store some data
        call_graph = {
            "function_a": [
                {"callee": "function_b", "line_number": 10, "is_external": False}
            ]
        }
        persistence.store_call_graph("test_file.py", call_graph)

        import_deps = {
            "modules": ["os", "sys"],
            "from_imports": {"typing": ["List"]},
            "line_numbers": {"os": 1, "sys": 2, "from typing": 3}
        }
        persistence.store_import_dependencies("test_file.py", import_deps)

        # Get statistics
        stats = persistence.get_statistics()

        assert stats["total_functions"] >= 2
        assert stats["total_calls"] >= 1
        assert stats["total_imports"] >= 2
        assert stats["total_files"] >= 1

        print("✓ Statistics generation test passed")


def test_incremental_updates():
    """Test that call graphs can be incrementally updated."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        persistence = CallGraphPersistence(db_path)

        # Initial call graph
        call_graph_v1 = {
            "function_a": [
                {"callee": "function_b", "line_number": 10, "is_external": False}
            ]
        }
        persistence.store_call_graph("test_file.py", call_graph_v1)

        # Updated call graph with new calls
        call_graph_v2 = {
            "function_a": [
                {"callee": "function_b", "line_number": 10, "is_external": False},
                {"callee": "function_c", "line_number": 15, "is_external": False}  # New
            ],
            "function_c": [  # New function
                {"callee": "function_d", "line_number": 20, "is_external": False}
            ]
        }
        persistence.store_call_graph("test_file.py", call_graph_v2)

        # Retrieve and verify
        retrieved = persistence.get_call_graph("test_file.py")
        assert "function_a" in retrieved
        assert "function_b" in retrieved
        assert "function_c" in retrieved

        # Check that function_a now has 2 callees
        callees_a = retrieved["function_a"]
        assert len(callees_a) == 2
        callees = {c["callee"] for c in callees_a}
        assert "function_b" in callees
        assert "function_c" in callees

        print("✓ Incremental updates test passed")


def test_file_metadata():
    """Test that file analysis metadata is tracked."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        persistence = CallGraphPersistence(db_path)

        # Store call graph
        call_graph = {
            "function_a": [
                {"callee": "function_b", "line_number": 10, "is_external": False}
            ]
        }
        persistence.store_call_graph("test_file.py", call_graph)

        # Check metadata
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT last_analyzed, analysis_version
            FROM file_metadata
            WHERE file_path = ?
        """, ("test_file.py",))

        row = cursor.fetchone()
        assert row is not None
        assert row[1] == "1.0"  # analysis version
        conn.close()

        print("✓ File metadata test passed")


def run_all_tests():
    """Run all unit tests."""
    print("=" * 60)
    print("Running Call Graph Persistence Unit Tests")
    print("=" * 60)
    print()

    test_database_initialization()
    test_call_graph_storage()
    test_function_usage_tracking()
    test_hot_cold_function_identification()
    test_import_dependency_storage()
    test_export_json()
    test_export_dot()
    test_export_graphml()
    test_merge_call_graphs()
    test_statistics()
    test_incremental_updates()
    test_file_metadata()

    print()
    print("=" * 60)
    print("✓ All Call Graph Persistence tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()