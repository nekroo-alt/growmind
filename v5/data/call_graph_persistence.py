"""
Call Graph Persistence Module (V5)

This module provides persistent storage of call graphs across sessions,
enabling faster analysis and tracking of code usage patterns over time.

Key Features:
- Persist call graphs to SQLite database
- Track function/class usage statistics over time
- Identify hot vs cold functions
- Track import dependencies and usage frequency
- Support incremental updates to call graphs
- Export call graphs for external analysis
"""

import sqlite3
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from collections import defaultdict


class CallGraphPersistence:
    """
    Manages persistent storage of call graphs and usage statistics.
    """

    def __init__(self, db_path: str = ".l4_cache/call_graph.db"):
        """
        Initialize call graph persistence with SQLite database.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._ensure_db_directory()
        self._initialize_db()

    def _ensure_db_directory(self):
        """Ensure the database directory exists."""
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

    def _initialize_db(self):
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Call graph table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS call_graph (
                    source_file TEXT NOT NULL,
                    source_function TEXT NOT NULL,
                    target_file TEXT NOT NULL,
                    target_function TEXT NOT NULL,
                    call_count INTEGER DEFAULT 1,
                    last_call_timestamp DATETIME,
                    PRIMARY KEY (source_file, source_function, target_file, target_function)
                )
            """)

            # Function usage table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS function_usage (
                    file_path TEXT NOT NULL,
                    function_name TEXT NOT NULL,
                    function_type TEXT NOT NULL,  # 'function' or 'method'
                    call_count INTEGER DEFAULT 0,
                    last_used DATETIME,
                    first_seen DATETIME,
                    is_hot BOOLEAN DEFAULT 0,
                    PRIMARY KEY (file_path, function_name)
                )
            """)

            # Import dependencies table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS import_dependencies (
                    file_path TEXT NOT NULL,
                    module_name TEXT NOT NULL,
                    import_type TEXT NOT NULL,  # 'import' or 'from'
                    imported_names TEXT,  # JSON array for from imports
                    line_number INTEGER,
                    usage_count INTEGER DEFAULT 0,
                    last_used DATETIME,
                    PRIMARY KEY (file_path, module_name, import_type, imported_names)
                )
            """)

            # File analysis metadata
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS file_metadata (
                    file_path TEXT PRIMARY KEY,
                    last_analyzed DATETIME,
                    file_hash TEXT,
                    analysis_version TEXT DEFAULT '1.0'
                )
            """)

            # Create indexes for performance
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_call_graph_source 
                ON call_graph(source_file, source_function)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_call_graph_target 
                ON call_graph(target_file, target_function)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_function_usage_calls 
                ON function_usage(call_count)
            """)

            conn.commit()

    def store_call_graph(
        self,
        file_path: str,
        call_graph: Dict[str, List[Dict]]
    ):
        """
        Store or update call graph for a file.

        Args:
            file_path: Path to the source file
            call_graph: Call graph from SemanticMapper.get_call_graph()
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            timestamp = datetime.now()

            for caller, callees in call_graph.items():
                for callee_info in callees:
                    callee = callee_info["callee"]
                    line_number = callee_info["line_number"]

                    # Try to update existing record
                    cursor.execute("""
                        UPDATE call_graph
                        SET call_count = call_count + 1,
                            last_call_timestamp = ?
                        WHERE source_file = ? 
                            AND source_function = ? 
                            AND target_function = ?
                    """, (timestamp, file_path, caller, callee))

                    # If no rows updated, insert new record
                    if cursor.rowcount == 0:
                        cursor.execute("""
                            INSERT INTO call_graph 
                            (source_file, source_function, target_file, target_function, 
                             call_count, last_call_timestamp)
                            VALUES (?, ?, ?, ?, 1, ?)
                        """, (file_path, caller, file_path, callee, timestamp))

                    # Update function usage statistics
                    self._update_function_usage(cursor, file_path, caller, "function", timestamp)
                    self._update_function_usage(cursor, file_path, callee, "function", timestamp)

            # Update file metadata
            self._update_file_metadata(cursor, file_path)

            conn.commit()

    def _update_function_usage(
        self,
        cursor: sqlite3.Cursor,
        file_path: str,
        function_name: str,
        function_type: str,
        timestamp: datetime
    ):
        """
        Update or insert function usage record.

        Args:
            cursor: Database cursor
            file_path: Path to source file
            function_name: Name of function
            function_type: Type ('function' or 'method')
            timestamp: Current timestamp
        """
        # Try to update existing record
        cursor.execute("""
            UPDATE function_usage
            SET call_count = call_count + 1,
                last_used = ?
            WHERE file_path = ? AND function_name = ?
        """, (timestamp, file_path, function_name))

        # If no rows updated, insert new record
        if cursor.rowcount == 0:
            cursor.execute("""
                INSERT INTO function_usage
                (file_path, function_name, function_type, call_count, 
                 last_used, first_seen, is_hot)
                VALUES (?, ?, ?, 1, ?, ?, 0)
            """, (file_path, function_name, function_type, timestamp, timestamp))

    def _update_file_metadata(
        self,
        cursor: sqlite3.Cursor,
        file_path: str
    ):
        """
        Update file analysis metadata.

        Args:
            cursor: Database cursor
            file_path: Path to source file
        """
        timestamp = datetime.now()

        cursor.execute("""
            INSERT OR REPLACE INTO file_metadata
            (file_path, last_analyzed, analysis_version)
            VALUES (?, ?, '1.0')
        """, (file_path, timestamp))

    def get_call_graph(
        self,
        file_path: Optional[str] = None,
        function_name: Optional[str] = None
    ) -> Dict[str, List[Dict]]:
        """
        Retrieve call graph from database.

        Args:
            file_path: Filter by source file (optional)
            function_name: Filter by function name (optional)

        Returns:
            Dict: Call graph structure
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            if file_path and function_name:
                cursor.execute("""
                    SELECT source_function, target_function, call_count, last_call_timestamp
                    FROM call_graph
                    WHERE source_file = ? AND source_function = ?
                    ORDER BY call_count DESC
                """, (file_path, function_name))
            elif file_path:
                cursor.execute("""
                    SELECT source_function, target_function, call_count, last_call_timestamp
                    FROM call_graph
                    WHERE source_file = ?
                    ORDER BY source_function, call_count DESC
                """, (file_path,))
            else:
                cursor.execute("""
                    SELECT source_file, source_function, target_function, 
                           call_count, last_call_timestamp
                    FROM call_graph
                    ORDER BY source_file, source_function, call_count DESC
                """)

            call_graph = defaultdict(list)

            for row in cursor.fetchall():
                if file_path:
                    source_func, target_func, count, timestamp = row
                    call_graph[source_func].append({
                        "callee": target_func,
                        "call_count": count,
                        "last_call_timestamp": timestamp,
                        "is_external": False
                    })
                else:
                    source_file, source_func, target_func, count, timestamp = row
                    key = f"{source_file}:{source_func}"
                    call_graph[key].append({
                        "callee": target_func,
                        "call_count": count,
                        "last_call_timestamp": timestamp,
                        "is_external": False
                    })

            return dict(call_graph)

    def get_usage_statistics(
        self,
        file_path: Optional[str] = None,
        min_calls: int = 0
    ) -> List[Dict]:
        """
        Get function usage statistics.

        Args:
            file_path: Filter by file path (optional)
            min_calls: Minimum call count threshold

        Returns:
            List: Function usage statistics sorted by call count
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            if file_path:
                cursor.execute("""
                    SELECT file_path, function_name, function_type, call_count,
                           last_used, first_seen, is_hot
                    FROM function_usage
                    WHERE file_path = ? AND call_count >= ?
                    ORDER BY call_count DESC
                """, (file_path, min_calls))
            else:
                cursor.execute("""
                    SELECT file_path, function_name, function_type, call_count,
                           last_used, first_seen, is_hot
                    FROM function_usage
                    WHERE call_count >= ?
                    ORDER BY call_count DESC
                """, (min_calls,))

            stats = []
            for row in cursor.fetchall():
                stats.append({
                    "file_path": row[0],
                    "function_name": row[1],
                    "function_type": row[2],
                    "call_count": row[3],
                    "last_used": row[4],
                    "first_seen": row[5],
                    "is_hot": bool(row[6])
                })

            return stats

    def identify_hot_cold_functions(
        self,
        hot_threshold: int = 10,
        cold_threshold: int = 2
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        Identify hot and cold functions based on usage patterns.

        Args:
            hot_threshold: Minimum call count to be considered hot
            cold_threshold: Maximum call count to be considered cold

        Returns:
            Tuple: (hot_functions, cold_functions)
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Update hot/cold flags
            cursor.execute("""
                UPDATE function_usage
                SET is_hot = CASE
                    WHEN call_count >= ? THEN 1
                    WHEN call_count <= ? THEN 0
                    ELSE is_hot
                END
            """, (hot_threshold, cold_threshold))

            conn.commit()

            # Get hot functions
            cursor.execute("""
                SELECT file_path, function_name, function_type, call_count, last_used
                FROM function_usage
                WHERE is_hot = 1
                ORDER BY call_count DESC
            """)

            hot_functions = []
            for row in cursor.fetchall():
                hot_functions.append({
                    "file_path": row[0],
                    "function_name": row[1],
                    "function_type": row[2],
                    "call_count": row[3],
                    "last_used": row[4]
                })

            # Get cold functions
            cursor.execute("""
                SELECT file_path, function_name, function_type, call_count, last_used, first_seen
                FROM function_usage
                WHERE call_count <= ? AND call_count > 0
                ORDER BY call_count ASC
            """, (cold_threshold,))

            cold_functions = []
            for row in cursor.fetchall():
                cold_functions.append({
                    "file_path": row[0],
                    "function_name": row[1],
                    "function_type": row[2],
                    "call_count": row[3],
                    "last_used": row[4],
                    "first_seen": row[5]
                })

            return hot_functions, cold_functions

    def store_import_dependencies(
        self,
        file_path: str,
        import_deps: Dict
    ):
        """
        Store import dependencies for a file.

        Args:
            file_path: Path to source file
            import_deps: Import dependencies from SemanticMapper.get_import_dependencies()
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            timestamp = datetime.now()

            # Store simple imports
            for module in import_deps.get("modules", []):
                cursor.execute("""
                    INSERT OR REPLACE INTO import_dependencies
                    (file_path, module_name, import_type, imported_names, 
                     line_number, usage_count, last_used)
                    VALUES (?, ?, 'import', NULL, ?, 1, ?)
                """, (file_path, module, import_deps["line_numbers"].get(module), timestamp))

            # Store from imports
            for module, names in import_deps.get("from_imports", {}).items():
                names_json = json.dumps(names)
                line_key = f"from {module}"
                line_number = import_deps["line_numbers"].get(line_key)
                cursor.execute("""
                    INSERT OR REPLACE INTO import_dependencies
                    (file_path, module_name, import_type, imported_names, 
                     line_number, usage_count, last_used)
                    VALUES (?, ?, 'from', ?, ?, 1, ?)
                """, (file_path, module, names_json, line_number, timestamp))

            conn.commit()

    def track_import_usage(
        self,
        file_path: str,
        module_name: str
    ):
        """
        Track usage of an imported module.

        Args:
            file_path: Path to source file
            module_name: Name of imported module
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            timestamp = datetime.now()

            cursor.execute("""
                UPDATE import_dependencies
                SET usage_count = usage_count + 1,
                    last_used = ?
                WHERE file_path = ? AND module_name = ?
            """, (timestamp, file_path, module_name))

            conn.commit()

    def get_import_dependencies(
        self,
        file_path: Optional[str] = None
    ) -> List[Dict]:
        """
        Retrieve import dependencies.

        Args:
            file_path: Filter by file path (optional)

        Returns:
            List: Import dependencies
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            if file_path:
                cursor.execute("""
                    SELECT file_path, module_name, import_type, imported_names,
                           line_number, usage_count, last_used
                    FROM import_dependencies
                    WHERE file_path = ?
                    ORDER BY line_number
                """, (file_path,))
            else:
                cursor.execute("""
                    SELECT file_path, module_name, import_type, imported_names,
                           line_number, usage_count, last_used
                    FROM import_dependencies
                    ORDER BY file_path, line_number
                """)

            deps = []
            for row in cursor.fetchall():
                names = json.loads(row[3]) if row[3] else None
                deps.append({
                    "file_path": row[0],
                    "module_name": row[1],
                    "import_type": row[2],
                    "imported_names": names,
                    "line_number": row[4],
                    "usage_count": row[5],
                    "last_used": row[6]
                })

            return deps

    def export_call_graph(
        self,
        format: str = "json",
        file_path: Optional[str] = None
    ) -> str:
        """
        Export call graph in specified format.

        Args:
            format: Export format ('json', 'graphml', 'dot')
            file_path: Filter by file path (optional)

        Returns:
            str: Exported data
        """
        call_graph = self.get_call_graph(file_path)

        if format == "json":
            return json.dumps(call_graph, indent=2, default=str)

        elif format == "dot":
            return self._export_to_dot(call_graph)

        elif format == "graphml":
            return self._export_to_graphml(call_graph)

        else:
            raise ValueError(f"Unsupported format: {format}")

    def _export_to_dot(self, call_graph: Dict) -> str:
        """
        Export call graph to DOT format (for Graphviz).

        Args:
            call_graph: Call graph data

        Returns:
            str: DOT format string
        """
        lines = ["digraph CallGraph {"]
        lines.append('  rankdir=LR;')
        lines.append('  node [shape=box];')

        for caller, callees in call_graph.items():
            for callee_info in callees:
                callee = callee_info["callee"]
                count = callee_info["call_count"]
                lines.append(f'  "{caller}" -> "{callee}" [label="{count}"];')

        lines.append("}")
        return "\n".join(lines)

    def _export_to_graphml(self, call_graph: Dict) -> str:
        """
        Export call graph to GraphML format.

        Args:
            call_graph: Call graph data

        Returns:
            str: GraphML format string
        """
        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<graphml xmlns="http://graphml.graphdrawing.org/xmlns"',
            '    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"',
            '    xsi:schemaLocation="http://graphml.graphdrawing.org/xmlns',
            '     http://graphml.graphdrawing.org/xmlns/1.0/graphml.xsd">',
            '  <graph id="CallGraph" edgedefault="directed">'
        ]

        # Add nodes
        nodes = set()
        for caller, callees in call_graph.items():
            nodes.add(caller)
            for callee_info in callees:
                nodes.add(callee_info["callee"])

        for node in nodes:
            lines.append(f'    <node id="{node}"/>')

        # Add edges
        edge_id = 0
        for caller, callees in call_graph.items():
            for callee_info in callees:
                lines.append(f'    <edge id="e{edge_id}" source="{caller}" target="{callee_info["callee"]}"/>')
                edge_id += 1

        lines.extend([
            '  </graph>',
            '</graphml>'
        ])

        return "\n".join(lines)

    def merge_call_graphs(self, other_db_path: str):
        """
        Merge call graphs from another database.

        Args:
            other_db_path: Path to other database
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Attach other database
            cursor.execute(f"ATTACH DATABASE ? AS other_db", (other_db_path,))

            # Merge call graphs
            cursor.execute("""
                INSERT OR REPLACE INTO call_graph
                (source_file, source_function, target_file, target_function,
                 call_count, last_call_timestamp)
                SELECT 
                    other_db.call_graph.source_file,
                    other_db.call_graph.source_function,
                    other_db.call_graph.target_file,
                    other_db.call_graph.target_function,
                    other_db.call_graph.call_count + COALESCE(
                        (SELECT call_count FROM call_graph 
                         WHERE source_file = other_db.call_graph.source_file
                         AND source_function = other_db.call_graph.source_function
                         AND target_function = other_db.call_graph.target_function), 
                        0
                    ),
                    other_db.call_graph.last_call_timestamp
                FROM other_db.call_graph
            """)

            # Merge function usage
            cursor.execute("""
                INSERT OR REPLACE INTO function_usage
                (file_path, function_name, function_type, call_count, 
                 last_used, first_seen, is_hot)
                SELECT 
                    other_db.function_usage.file_path,
                    other_db.function_usage.function_name,
                    other_db.function_usage.function_type,
                    other_db.function_usage.call_count + COALESCE(
                        (SELECT call_count FROM function_usage 
                         WHERE file_path = other_db.function_usage.file_path
                         AND function_name = other_db.function_usage.function_name), 
                        0
                    ),
                    other_db.function_usage.last_used,
                    other_db.function_usage.first_seen,
                    other_db.function_usage.is_hot
                FROM other_db.function_usage
            """)

            # Detach other database
            cursor.execute("DETACH DATABASE other_db")

            conn.commit()

    def get_statistics(self) -> Dict:
        """
        Get overall statistics about call graph data.

        Returns:
            Dict: Statistics
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Total functions analyzed
            cursor.execute("SELECT COUNT(*) FROM function_usage")
            total_functions = cursor.fetchone()[0]

            # Total call edges
            cursor.execute("SELECT COUNT(*) FROM call_graph")
            total_calls = cursor.fetchone()[0]

            # Total imports tracked
            cursor.execute("SELECT COUNT(*) FROM import_dependencies")
            total_imports = cursor.fetchone()[0]

            # Total files analyzed
            cursor.execute("SELECT COUNT(*) FROM file_metadata")
            total_files = cursor.fetchone()[0]

            # Hot functions count
            cursor.execute("SELECT COUNT(*) FROM function_usage WHERE is_hot = 1")
            hot_functions = cursor.fetchone()[0]

            # Cold functions count
            cursor.execute("SELECT COUNT(*) FROM function_usage WHERE call_count <= 2")
            cold_functions = cursor.fetchone()[0]

            return {
                "total_functions": total_functions,
                "total_calls": total_calls,
                "total_imports": total_imports,
                "total_files": total_files,
                "hot_functions": hot_functions,
                "cold_functions": cold_functions
            }