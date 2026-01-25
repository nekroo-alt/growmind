"""
Common Utilities for CLI Commands

This module provides shared utilities and helper functions used across CLI commands.
"""

import sys
import os
from typing import Dict, Any, Optional, List
from datetime import datetime

# Ensure L4_ROOT is in sys.path so that imports work
L4_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if L4_ROOT not in sys.path:
    sys.path.insert(0, L4_ROOT)


def print_header(title: str, char: str = "="):
    """Print a formatted header."""
    print("\n" + char * 60)
    print(title)
    print(char * 60)


def print_success(message: str):
    """Print a success message with checkmark."""
    print(f"✓ {message}")


def print_error(message: str):
    """Print an error message with X mark."""
    print(f"✗ {message}")


def print_warning(message: str):
    """Print a warning message."""
    print(f"⚠️  {message}")


def print_info(message: str):
    """Print an info message."""
    print(f"ℹ️  {message}")


def format_timestamp(timestamp_str: str) -> str:
    """Format ISO timestamp to readable string."""
    if not timestamp_str:
        return "N/A"
    return timestamp_str.replace("T", " ").split(".")[0]


def format_number(value: int) -> str:
    """Format number with thousands separator."""
    return f"{value:,}"


def format_percentage(value: float) -> str:
    """Format percentage."""
    return f"{value:.1f}%"


def format_cost(value: float) -> str:
    """Format cost in USD."""
    return f"${value:.4f}"


def create_progress_bar(
    percentage: float, length: int = 50, filled_char: str = "█", empty_char: str = "░"
) -> str:
    """Create a text-based progress bar."""
    filled = int(length * percentage / 100)
    return filled_char * filled + empty_char * (length - filled)


def confirm_action(prompt: str, default: bool = False) -> bool:
    """Ask user for confirmation."""
    default_str = "Y/n" if default else "y/N"
    choice = input(f"\n{prompt} [{default_str}]: ").strip().lower()
    
    if not choice:
        return default
    
    return choice == "y"


def print_table(
    headers: List[str],
    rows: List[List[Any]],
    padding: int = 2,
    max_width: Optional[int] = None
):
    """Print a formatted table."""
    if not headers or not rows:
        return
    
    # Calculate column widths
    num_cols = len(headers)
    col_widths = [len(str(h)) for h in headers]
    
    for row in rows:
        for i, cell in enumerate(row):
            cell_str = str(cell)
            if i < num_cols:
                width = len(cell_str)
                if width > col_widths[i]:
                    col_widths[i] = width
    
    # Apply max width constraint
    if max_width:
        for i in range(num_cols):
            if col_widths[i] > max_width:
                col_widths[i] = max_width
    
    # Print headers
    header_line = ""
    for i, header in enumerate(headers):
        header_str = str(header)[:max_width] if max_width else str(header)
        header_line += header_str.ljust(col_widths[i]) + " " * padding
    
    print(header_line)
    print("-" * len(header_line))
    
    # Print rows
    for row in rows:
        row_line = ""
        for i, cell in enumerate(row):
            cell_str = str(cell)
            if max_width and len(cell_str) > max_width:
                cell_str = cell_str[:max_width-3] + "..."
            if i < num_cols:
                row_line += cell_str.ljust(col_widths[i]) + " " * padding
        print(row_line)


def validate_file_exists(path: str, description: str = "File") -> bool:
    """Validate that a file exists."""
    if not path:
        print_error(f"{description} path is required")
        return False
    
    if not os.path.exists(path):
        print_error(f"{description} not found: {path}")
        return False
    
    return True


def validate_directory_exists(path: str, description: str = "Directory") -> bool:
    """Validate that a directory exists."""
    if not path:
        print_error(f"{description} path is required")
        return False
    
    if not os.path.isdir(path):
        print_error(f"{description} not found: {path}")
        return False
    
    return True


def ensure_directory(path: str) -> bool:
    """Ensure a directory exists, creating it if necessary."""
    if os.path.exists(path):
        return os.path.isdir(path)
    
    try:
        os.makedirs(path, exist_ok=True)
        return True
    except Exception as e:
        print_error(f"Failed to create directory {path}: {e}")
        return False


def get_file_size_mb(path: str) -> float:
    """Get file size in MB."""
    if not os.path.exists(path):
        return 0.0
    
    return os.path.getsize(path) / (1024 * 1024)


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def truncate_string(s: str, max_length: int, suffix: str = "...") -> str:
    """Truncate a string to maximum length with suffix."""
    if len(s) <= max_length:
        return s
    return s[: max_length - len(suffix)] + suffix


def safe_dict_get(d: Dict[str, Any], key: str, default: Any = None) -> Any:
    """Safely get a value from a dictionary."""
    if not d:
        return default
    return d.get(key, default)


def parse_time_range(time_str: str) -> Optional[datetime]:
    """Parse time range string (e.g., '24h', '7d')."""
    if not time_str:
        return None
    
    try:
        from datetime import timedelta, datetime as dt
        
        time_str = time_str.strip().lower()
        value = int("".join(filter(str.isdigit, time_str)))
        unit = "".join(filter(str.isalpha, time_str))
        
        if unit.startswith("h"):
            return dt.utcnow() - timedelta(hours=value)
        elif unit.startswith("d"):
            return dt.utcnow() - timedelta(days=value)
        elif unit.startswith("w"):
            return dt.utcnow() - timedelta(weeks=value)
        elif unit.startswith("m"):
            return dt.utcnow() - timedelta(minutes=value)
        else:
            print_error(f"Unknown time unit: {unit}")
            return None
    except Exception as e:
        print_error(f"Failed to parse time range: {e}")
        return None


def export_to_json(data: Any, path: str) -> bool:
    """Export data to JSON file."""
    import json
    
    try:
        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)
        print_success(f"Exported to {path}")
        return True
    except Exception as e:
        print_error(f"Failed to export to {path}: {e}")
        return False


def export_to_csv(data: Any, path: str, headers: List[str]) -> bool:
    """Export data to CSV file."""
    import csv
    
    try:
        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            
            # Handle different data types
            if isinstance(data, list):
                for row in data:
                    if isinstance(row, dict):
                        writer.writerow([row.get(h) for h in headers])
                    elif isinstance(row, list):
                        writer.writerow(row)
            
        print_success(f"Exported to {path}")
        return True
    except Exception as e:
        print_error(f"Failed to export to {path}: {e}")
        return False


def print_metrics(metrics: Dict[str, float], title: str = "Metrics"):
    """Print a formatted metrics display."""
    print_header(title)
    
    for name, value in metrics.items():
        print(f"{name}: {value:.2f}")


def print_summary(stats: Dict[str, Any], title: str = "Summary"):
    """Print a formatted summary display."""
    print_header(title)
    
    for key, value in stats.items():
        if isinstance(value, (int, float)):
            print(f"{key}: {value}")
        elif isinstance(value, dict):
            print(f"{key}:")
            for subkey, subvalue in value.items():
                print(f"  {subkey}: {subvalue}")
        elif isinstance(value, list):
            print(f"{key}:")
            for item in value:
                print(f"  - {item}")
        else:
            print(f"{key}: {value}")


def load_config_from_env(prefix: str = "L4_") -> Dict[str, str]:
    """Load configuration from environment variables."""
    config = {}
    
    for key, value in os.environ.items():
        if key.startswith(prefix):
            config_key = key[len(prefix):].lower()
            config[config_key] = value
    
    return config


def get_l4_root() -> str:
    """Get the L4 root directory."""
    return L4_ROOT


def ensure_l4_root_in_path() -> None:
    """Ensure L4_ROOT is in sys.path."""
    global L4_ROOT
    if L4_ROOT not in sys.path:
        sys.path.insert(0, L4_ROOT)


class ProgressBar:
    """Simple text-based progress bar."""
    
    def __init__(self, total: int, description: str = "Progress"):
        self.total = total
        self.current = 0
        self.description = description
    
    def update(self, increment: int = 1) -> None:
        """Update progress."""
        self.current += increment
        self._display()
    
    def set_progress(self, value: int) -> None:
        """Set progress to specific value."""
        self.current = value
        self._display()
    
    def _display(self) -> None:
        """Display current progress."""
        percentage = (self.current / self.total) * 100
        bar = create_progress_bar(percentage)
        print(f"\r{self.description}: [{bar}] {percentage:.1f}% ({self.current}/{self.total})", end="", flush=True)
    
    def finish(self) -> None:
        """Mark progress as complete."""
        self.current = self.total
        self._display()
        print()
        print_success("Complete!")