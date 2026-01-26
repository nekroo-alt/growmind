"""
File Operations Utilities

This module provides utility functions for file system operations.
"""

import os
from typing import Any, List


def ensure_directory(path: str) -> bool:
    """
    Ensure a directory exists, creating it if necessary.
    
    Args:
        path: Directory path
        
    Returns:
        bool: True if directory exists or was created successfully
    """
    if os.path.exists(path):
        return os.path.isdir(path)
    
    try:
        os.makedirs(path, exist_ok=True)
        return True
    except Exception as e:
        print(f"Failed to create directory {path}: {e}")
        return False


def validate_file_exists(path: str, description: str = "File") -> bool:
    """
    Validate that a file exists.
    
    Args:
        path: File path to validate
        description: Description of the file for error messages
        
    Returns:
        bool: True if file exists
    """
    if not path:
        print(f"{description} path is required")
        return False
    
    if not os.path.exists(path):
        print(f"{description} not found: {path}")
        return False
    
    return True


def validate_directory_exists(path: str, description: str = "Directory") -> bool:
    """
    Validate that a directory exists.
    
    Args:
        path: Directory path to validate
        description: Description of the directory for error messages
        
    Returns:
        bool: True if directory exists
    """
    if not path:
        print(f"{description} path is required")
        return False
    
    if not os.path.isdir(path):
        print(f"{description} not found: {path}")
        return False
    
    return True


def get_file_size_mb(path: str) -> float:
    """
    Get file size in MB.
    
    Args:
        path: File path
        
    Returns:
        float: File size in MB
    """
    if not os.path.exists(path):
        return 0.0
    
    return os.path.getsize(path) / (1024 * 1024)


def export_to_json(data: Any, path: str) -> bool:
    """
    Export data to JSON file.
    
    Args:
        data: Data to export
        path: Output file path
        
    Returns:
        bool: True if export succeeded
    """
    import json
    
    try:
        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)
        print(f"Exported to {path}")
        return True
    except Exception as e:
        print(f"Failed to export to {path}: {e}")
        return False


def export_to_csv(data: Any, path: str, headers: List[str]) -> bool:
    """
    Export data to CSV file.
    
    Args:
        data: Data to export (list of dicts or list of lists)
        path: Output file path
        headers: Column headers
        
    Returns:
        bool: True if export succeeded
    """
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
        
        print(f"Exported to {path}")
        return True
    except Exception as e:
        print(f"Failed to export to {path}: {e}")
        return False