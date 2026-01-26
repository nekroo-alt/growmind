"""
Validation Utilities

This module provides validation functions for files, directories, and configurations.
"""

import os
from typing import Any, List


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


def validate_path_writable(path: str) -> bool:
    """
    Validate that a path is writable.
    
    Args:
        path: Path to validate
        
    Returns:
        bool: True if path is writable
    """
    if not os.path.exists(path):
        return False
    
    return os.access(path, os.W_OK)


def validate_positive_integer(value: Any, name: str = "value") -> bool:
    """
    Validate that a value is a positive integer.
    
    Args:
        value: Value to validate
        name: Name of the value for error messages
        
    Returns:
        bool: True if value is a positive integer
    """
    if not isinstance(value, int):
        print(f"{name} must be an integer, got {type(value).__name__}")
        return False
    
    if value < 0:
        print(f"{name} must be positive, got {value}")
        return False
    
    return True


def validate_in_range(value: Any, min_val: float, max_val: float, name: str = "value") -> bool:
    """
    Validate that a value is within a specific range.
    
    Args:
        value: Value to validate
        min_val: Minimum allowed value
        max_val: Maximum allowed value
        name: Name of the value for error messages
        
    Returns:
        bool: True if value is within range
    """
    try:
        num_value = float(value)
    except (ValueError, TypeError):
        print(f"{name} must be a number, got {value}")
        return False
    
    if num_value < min_val or num_value > max_val:
        print(f"{name} must be between {min_val} and {max_val}, got {num_value}")
        return False
    
    return True


def validate_required_fields(data: dict, required: List[str]) -> bool:
    """
    Validate that required fields exist in a dictionary.
    
    Args:
        data: Dictionary to validate
        required: List of required field names
        
    Returns:
        bool: True if all required fields are present
    """
    missing = [field for field in required if field not in data]
    
    if missing:
        print(f"Missing required fields: {', '.join(missing)}")
        return False
    
    return True


def validate_email(email: str) -> bool:
    """
    Validate email address format.
    
    Args:
        email: Email address to validate
        
    Returns:
        bool: True if email format is valid
    """
    import re
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_url(url: str) -> bool:
    """
    Validate URL format.
    
    Args:
        url: URL to validate
        
    Returns:
        bool: True if URL format is valid
    """
    import re
    
    pattern = r'^https?://[^\s/$.?#].[^\s]*$'
    return bool(re.match(pattern, url))