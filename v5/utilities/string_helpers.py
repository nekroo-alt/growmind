"""
String Helper Utilities

This module provides utility functions for string manipulation and formatting.
"""

from typing import Any, Dict


def truncate_string(s: str, max_length: int, suffix: str = "...") -> str:
    """
    Truncate a string to maximum length with suffix.
    
    Args:
        s: String to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated
        
    Returns:
        str: Truncated string with suffix if needed
    """
    if len(s) <= max_length:
        return s
    return s[: max_length - len(suffix)] + suffix


def safe_dict_get(d: Dict[str, Any], key: str, default: Any = None) -> Any:
    """
    Safely get a value from a dictionary.
    
    Args:
        d: Dictionary to get value from
        key: Key to look up
        default: Default value if key not found
        
    Returns:
        Value from dictionary or default
    """
    if not d:
        return default
    return d.get(key, default)


def format_number(value: int) -> str:
    """
    Format number with thousands separator.
    
    Args:
        value: Number to format
        
    Returns:
        str: Formatted number
    """
    return f"{value:,}"


def format_percentage(value: float) -> str:
    """
    Format percentage.
    
    Args:
        value: Percentage value (0-100)
        
    Returns:
        str: Formatted percentage
    """
    return f"{value:.1f}%"


def format_cost(value: float) -> str:
    """
    Format cost in USD.
    
    Args:
        value: Cost value in USD
        
    Returns:
        str: Formatted cost
    """
    return f"${value:.4f}"


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        str: Formatted size string
    """
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def create_progress_bar(
    percentage: float, length: int = 50, filled_char: str = "█", empty_char: str = "░"
) -> str:
    """
    Create a text-based progress bar.
    
    Args:
        percentage: Percentage complete (0-100)
        length: Total length of progress bar
        filled_char: Character for filled portion
        empty_char: Character for empty portion
        
    Returns:
        str: Progress bar string
    """
    filled = int(length * percentage / 100)
    return filled_char * filled + empty_char * (length - filled)


def confirm_action(prompt: str, default: bool = False) -> bool:
    """
    Ask user for confirmation.
    
    Args:
        prompt: Confirmation prompt message
        default: Default choice
        
    Returns:
        bool: User's confirmation choice
    """
    default_str = "Y/n" if default else "y/N"
    choice = input(f"\n{prompt} [{default_str}]: ").strip().lower()
    
    if not choice:
        return default
    
    return choice == "y"