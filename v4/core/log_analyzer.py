"""
Log Analysis and Search Tools for L4D V3

Provides comprehensive log analysis capabilities:
- Full-text search with complex queries (AND, OR, NOT)
- Filtering by level, module, operation, task, time range
- Log summaries and statistics
- Error pattern identification
- Operation timeline generation
- Log export to CSV/JSON
"""

import sqlite3
import json
import re
import csv
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple, Iterator
from collections import Counter, defaultdict
import fnmatch


class LogEntry:
    """Represents a single log entry."""

    def __init__(self, data: Dict[str, Any]):
        """
        Initialize from parsed log data.

        Args:
            data: Parsed JSON log data
        """
        self.timestamp = self._parse_timestamp(data.get("timestamp"))
        self.level = data.get("level", "INFO")
        self.logger = data.get("logger", "")
        self.message = data.get("message", "")
        self.module = data.get("module", "")
        self.function = data.get("function", "")
        self.line = data.get("line", 0)
        self.operation_id = data.get("operation_id")
        self.task_id = data.get("task_id")
        self.session_id = data.get("session_id")
        self.exception = data.get("exception")
        self.extra = {
            k: v
            for k, v in data.items()
            if k
            not in [
                "timestamp",
                "level",
                "logger",
                "message",
                "module",
                "function",
                "line",
                "operation_id",
                "task_id",
                "session_id",
                "exception",
            ]
        }
        self.raw_data = data

    def _parse_timestamp(self, timestamp_str: str) -> Optional[datetime]:
        """Parse timestamp string to datetime object."""
        if not timestamp_str:
            return None
        try:
            # Try ISO format first
            return datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            try:
                # Try common formats
                return datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
            except (ValueError, AttributeError):
                return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "level": self.level,
            "logger": self.logger,
            "message": self.message,
            "module": self.module,
            "function": self.function,
            "line": self.line,
            "operation_id": self.operation_id,
            "task_id": self.task_id,
            "session_id": self.session_id,
            "exception": self.exception,
            **self.extra,
        }

    def __repr__(self) -> str:
        return f"LogEntry(timestamp={self.timestamp}, level={self.level}, message={self.message[:50]}...)"


class LogQuery:
    """Represents a log query with filters."""

    def __init__(
        self,
        level: Optional[str] = None,
        module: Optional[str] = None,
        operation_id: Optional[str] = None,
        task_id: Optional[int] = None,
        session_id: Optional[str] = None,
        search: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        has_error: bool = False,
    ):
        """
        Initialize log query.

        Args:
            level: Filter by log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            module: Filter by module name (supports wildcards)
            operation_id: Filter by operation ID
            task_id: Filter by task ID
            session_id: Filter by session ID
            search: Full-text search query
            start_time: Start of time range
            end_time: End of time range
            has_error: Only include entries with exceptions
        """
        self.level = level
        self.module = module
        self.operation_id = operation_id
        self.task_id = task_id
        self.session_id = session_id
        self.search = search
        self.start_time = start_time
        self.end_time = end_time
        self.has_error = has_error

    def matches(self, entry: LogEntry) -> bool:
        """
        Check if a log entry matches this query.

        Args:
            entry: Log entry to check

        Returns:
            True if entry matches all filters
        """
        # Level filter
        if self.level and entry.level != self.level:
            return False

        # Module filter (with wildcard support)
        if self.module and not fnmatch.fnmatch(entry.module, self.module):
            return False

        # Operation ID filter
        if self.operation_id and entry.operation_id != self.operation_id:
            return False

        # Task ID filter
        if self.task_id and entry.task_id != self.task_id:
            return False

        # Session ID filter
        if self.session_id and entry.session_id != self.session_id:
            return False

        # Time range filter
        if self.start_time and entry.timestamp and entry.timestamp < self.start_time:
            return False
        if self.end_time and entry.timestamp and entry.timestamp > self.end_time:
            return False

        # Error filter
        if self.has_error and not entry.exception:
            return False

        # Search filter (with AND, OR, NOT support)
        if self.search:
            if not self._matches_search(entry):
                return False

        return True

    def _matches_search(self, entry: LogEntry) -> bool:
        """Check if entry matches search query with boolean operators."""
        # Convert search to lowercase for case-insensitive matching
        search_lower = self.search.lower()

        # Parse boolean operators
        tokens = re.findall(r'(?:AND|OR|NOT|"[^"]+"|\S+)', search_lower)

        # Evaluate expression
        return self._evaluate_tokens(tokens, entry)

    def _evaluate_tokens(self, tokens: List[str], entry: LogEntry) -> bool:
        """Evaluate search tokens with boolean operators."""
        # Convert entry to searchable text
        searchable_text = (
            f"{entry.message} {entry.module} {entry.function} "
            f"{entry.logger} {entry.exception or ''}"
        ).lower()

        # Simple evaluation (left to right, no operator precedence)
        result = True
        operator = None

        for token in tokens:
            if token in ("AND", "OR", "NOT"):
                operator = token
            elif token.startswith('"') and token.endswith('"'):
                # Quoted phrase
                term = token[1:-1]
                term_result = term in searchable_text
                result = self._apply_operator(result, term_result, operator)
                operator = None
            else:
                # Single term
                term = token
                term_result = term in searchable_text
                result = self._apply_operator(result, term_result, operator)
                operator = None

        return result

    def _apply_operator(self, left: bool, right: bool, operator: Optional[str]) -> bool:
        """Apply boolean operator."""
        if operator == "AND":
            return left and right
        elif operator == "OR":
            return left or right
        elif operator == "NOT":
            return left and not right
        else:
            return right


class LogAnalyzer:
    """
    Main log analysis engine.

    Provides search, filtering, analysis, and export capabilities.
    """

    def __init__(self, log_dir: str = "v2/logs"):
        """
        Initialize log analyzer.

        Args:
            log_dir: Directory containing log files
        """
        self.log_dir = Path(log_dir)
        self.entries: List[LogEntry] = []
        self._loaded = False

    def load_logs(self, force_reload: bool = False) -> None:
        """
        Load log entries from log files.

        Args:
            force_reload: If True, reload even if already loaded
        """
        if self._loaded and not force_reload:
            return

        self.entries = []

        # Load main log file
        log_file = self.log_dir / "l4d.log"
        if log_file.exists():
            self._load_log_file(log_file)

        # Load error log file
        error_log_file = self.log_dir / "errors.log"
        if error_log_file.exists():
            self._load_log_file(error_log_file)

        # Sort entries by timestamp
        self.entries.sort(key=lambda e: e.timestamp or datetime.min)

        self._loaded = True

    def _load_log_file(self, log_file: Path) -> None:
        """Load entries from a single log file."""
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        # Parse JSON line
                        data = json.loads(line)
                        entry = LogEntry(data)
                        self.entries.append(entry)
                    except json.JSONDecodeError:
                        # Skip non-JSON lines
                        continue
        except Exception as e:
            print(f"Warning: Failed to load log file {log_file}: {e}")

    def search(self, query: LogQuery) -> List[LogEntry]:
        """
        Search logs matching the query.

        Args:
            query: Log query with filters

        Returns:
            List of matching log entries
        """
        if not self._loaded:
            self.load_logs()

        return [entry for entry in self.entries if query.matches(entry)]

    def get_entries_by_operation(self, operation_id: str) -> List[LogEntry]:
        """
        Get all log entries for a specific operation.

        Args:
            operation_id: Operation ID to filter by

        Returns:
            List of log entries for the operation
        """
        query = LogQuery(operation_id=operation_id)
        return self.search(query)

    def get_entries_by_task(self, task_id: int) -> List[LogEntry]:
        """
        Get all log entries for a specific task.

        Args:
            task_id: Task ID to filter by

        Returns:
            List of log entries for the task
        """
        query = LogQuery(task_id=task_id)
        return self.search(query)

    def get_errors(self, since: Optional[datetime] = None) -> List[LogEntry]:
        """
        Get all error log entries.

        Args:
            since: Only include errors after this time

        Returns:
            List of error log entries
        """
        query = LogQuery(level="ERROR", has_error=True, start_time=since)
        return self.search(query)

    def generate_summary(self, query: Optional[LogQuery] = None) -> Dict[str, Any]:
        """
        Generate summary statistics for logs.

        Args:
            query: Optional query to filter logs before summary

        Returns:
            Dictionary with summary statistics
        """
        if not self._loaded:
            self.load_logs()

        entries = self.search(query) if query else self.entries

        if not entries:
            return {
                "total_entries": 0,
                "by_level": {},
                "by_module": {},
                "by_operation": {},
                "error_count": 0,
                "time_range": None,
            }

        # Count by level
        by_level = Counter(e.level for e in entries)

        # Count by module
        by_module = Counter(e.module for e in entries if e.module)

        # Count by operation
        by_operation = Counter(e.operation_id for e in entries if e.operation_id)

        # Count errors
        error_count = sum(1 for e in entries if e.level in ("ERROR", "CRITICAL"))

        # Time range
        timestamps = [e.timestamp for e in entries if e.timestamp]
        time_range = {
            "start": min(timestamps).isoformat() if timestamps else None,
            "end": max(timestamps).isoformat() if timestamps else None,
        }

        return {
            "total_entries": len(entries),
            "by_level": dict(by_level),
            "by_module": dict(by_module.most_common(10)),
            "by_operation": dict(by_operation.most_common(10)),
            "error_count": error_count,
            "time_range": time_range,
        }

    def identify_error_patterns(self) -> List[Dict[str, Any]]:
        """
        Identify common error patterns in logs.

        Returns:
            List of error patterns with counts
        """
        errors = self.get_errors()

        if not errors:
            return []

        # Group errors by error type
        error_types = defaultdict(list)
        for error in errors:
            if error.exception:
                # Extract error type from exception message
                match = re.search(r"^(\w+):", error.exception)
                if match:
                    error_type = match.group(1)
                else:
                    error_type = "Unknown"
                error_types[error_type].append(error)

        # Analyze patterns
        patterns = []
        for error_type, error_list in error_types.items():
            # Group by message pattern (simplified)
            message_patterns = defaultdict(int)
            for error in error_list:
                # Simplify message to identify patterns
                message_pattern = re.sub(r"\d+", "N", error.message)
                message_pattern = re.sub(r'["\'].*?["\']', "STR", message_pattern)
                message_pattern = re.sub(r"\b[0-9a-f]{8,}\b", "HEX", message_pattern)
                message_patterns[message_pattern] += 1

            patterns.append(
                {
                    "error_type": error_type,
                    "count": len(error_list),
                    "message_patterns": dict(
                        sorted(
                            message_patterns.items(), key=lambda x: x[1], reverse=True
                        )[:5]
                    ),
                    "first_occurrence": (
                        min(e.timestamp for e in error_list if e.timestamp).isoformat()
                        if any(e.timestamp for e in error_list)
                        else None
                    ),
                    "last_occurrence": (
                        max(e.timestamp for e in error_list if e.timestamp).isoformat()
                        if any(e.timestamp for e in error_list)
                        else None
                    ),
                }
            )

        # Sort by frequency
        patterns.sort(key=lambda p: p["count"], reverse=True)

        return patterns

    def generate_operation_timeline(self, operation_id: str) -> List[Dict[str, Any]]:
        """
        Generate timeline for an operation.

        Args:
            operation_id: Operation ID to generate timeline for

        Returns:
            List of timeline events sorted by timestamp
        """
        entries = self.get_entries_by_operation(operation_id)

        if not entries:
            return []

        # Filter entries with timestamps
        timed_entries = [e for e in entries if e.timestamp]
        timed_entries.sort(key=lambda e: e.timestamp)

        # Create timeline events
        timeline = []
        for entry in timed_entries:
            event = {
                "timestamp": entry.timestamp.isoformat(),
                "level": entry.level,
                "message": entry.message,
                "module": entry.module,
                "function": entry.function,
                "line": entry.line,
            }

            # Add context
            if entry.task_id:
                event["task_id"] = entry.task_id
            if entry.exception:
                event["exception"] = entry.exception

            timeline.append(event)

        return timeline

    def export_to_csv(
        self, query: Optional[LogQuery] = None, output_file: str = "logs_export.csv"
    ) -> None:
        """
        Export logs to CSV file.

        Args:
            query: Optional query to filter logs before export
            output_file: Output CSV file path
        """
        entries = self.search(query) if query else self.entries

        if not entries:
            print("No entries to export")
            return

        # Define CSV columns
        fieldnames = [
            "timestamp",
            "level",
            "logger",
            "message",
            "module",
            "function",
            "line",
            "operation_id",
            "task_id",
            "session_id",
        ]

        with open(output_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for entry in entries:
                row = {
                    "timestamp": entry.timestamp.isoformat() if entry.timestamp else "",
                    "level": entry.level,
                    "logger": entry.logger,
                    "message": entry.message,
                    "module": entry.module,
                    "function": entry.function,
                    "line": entry.line,
                    "operation_id": entry.operation_id or "",
                    "task_id": entry.task_id or "",
                    "session_id": entry.session_id or "",
                }
                writer.writerow(row)

        print(f"Exported {len(entries)} entries to {output_file}")

    def export_to_json(
        self, query: Optional[LogQuery] = None, output_file: str = "logs_export.json"
    ) -> None:
        """
        Export logs to JSON file.

        Args:
            query: Optional query to filter logs before export
            output_file: Output JSON file path
        """
        entries = self.search(query) if query else self.entries

        if not entries:
            print("No entries to export")
            return

        # Convert to list of dictionaries
        export_data = [entry.to_dict() for entry in entries]

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2, default=str)

        print(f"Exported {len(entries)} entries to {output_file}")

    def count_logs_by_hour(self, query: Optional[LogQuery] = None) -> Dict[str, int]:
        """
        Count logs by hour of day.

        Args:
            query: Optional query to filter logs before counting

        Returns:
            Dictionary mapping hour to count
        """
        entries = self.search(query) if query else self.entries

        hour_counts = defaultdict(int)
        for entry in entries:
            if entry.timestamp:
                hour = entry.timestamp.hour
                hour_counts[f"{hour:02d}:00"] += 1

        # Fill in all hours with 0 if missing
        result = {}
        for hour in range(24):
            key = f"{hour:02d}:00"
            result[key] = hour_counts.get(key, 0)

        return result

    def get_recent_errors(self, hours: int = 24) -> List[LogEntry]:
        """
        Get errors from the last N hours.

        Args:
            hours: Number of hours to look back

        Returns:
            List of recent error entries
        """
        since = datetime.now() - timedelta(hours=hours)
        return [e for e in self.get_errors(since=since)]

    def get_operation_stats(self, operation_id: str) -> Dict[str, Any]:
        """
        Get statistics for a specific operation.

        Args:
            operation_id: Operation ID to analyze

        Returns:
            Dictionary with operation statistics
        """
        entries = self.get_entries_by_operation(operation_id)

        if not entries:
            return {
                "operation_id": operation_id,
                "total_entries": 0,
                "duration_seconds": None,
                "start_time": None,
                "end_time": None,
                "error_count": 0,
                "by_level": {},
            }

        # Time range
        timed_entries = [e for e in entries if e.timestamp]
        if timed_entries:
            start_time = min(e.timestamp for e in timed_entries)
            end_time = max(e.timestamp for e in timed_entries)
            duration_seconds = (end_time - start_time).total_seconds()
        else:
            start_time = None
            end_time = None
            duration_seconds = None

        # Count by level
        by_level = Counter(e.level for e in entries)

        # Count errors
        error_count = sum(1 for e in entries if e.level in ("ERROR", "CRITICAL"))

        return {
            "operation_id": operation_id,
            "total_entries": len(entries),
            "duration_seconds": duration_seconds,
            "start_time": start_time.isoformat() if start_time else None,
            "end_time": end_time.isoformat() if end_time else None,
            "error_count": error_count,
            "by_level": dict(by_level),
        }


def create_analyzer(log_dir: str = "v2/logs") -> LogAnalyzer:
    """
    Create a log analyzer instance.

    Args:
        log_dir: Directory containing log files

    Returns:
        LogAnalyzer instance
    """
    return LogAnalyzer(log_dir)
