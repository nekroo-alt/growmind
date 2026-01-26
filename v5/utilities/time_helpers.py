"""
Time Helper Utilities

This module provides utility functions for time and date manipulation.
"""

from typing import Optional
from datetime import datetime, timedelta


def format_timestamp(timestamp_str: str) -> str:
    """
    Format ISO timestamp to readable string.
    
    Args:
        timestamp_str: ISO format timestamp string
        
    Returns:
        str: Formatted timestamp string
    """
    if not timestamp_str:
        return "N/A"
    return timestamp_str.replace("T", " ").split(".")[0]


def parse_time_range(time_str: str) -> Optional[datetime]:
    """
    Parse time range string (e.g., '24h', '7d').
    
    Args:
        time_str: Time range string (e.g., '24h', '7d', '1w')
        
    Returns:
        Optional[datetime]: Datetime object or None if parse fails
    """
    if not time_str:
        return None
    
    try:
        time_str = time_str.strip().lower()
        value = int("".join(filter(str.isdigit, time_str)))
        unit = "".join(filter(str.isalpha, time_str))
        
        if unit.startswith("h"):
            return datetime.utcnow() - timedelta(hours=value)
        elif unit.startswith("d"):
            return datetime.utcnow() - timedelta(days=value)
        elif unit.startswith("w"):
            return datetime.utcnow() - timedelta(weeks=value)
        elif unit.startswith("m"):
            return datetime.utcnow() - timedelta(minutes=value)
        else:
            print(f"Unknown time unit: {unit}")
            return None
    except Exception as e:
        print(f"Failed to parse time range: {e}")
        return None


def format_duration(seconds: float) -> str:
    """
    Format duration in human-readable format.
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        str: Formatted duration string
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    
    minutes = seconds / 60
    if minutes < 60:
        return f"{minutes:.1f}m"
    
    hours = minutes / 60
    if hours < 24:
        return f"{hours:.1f}h"
    
    days = hours / 24
    return f"{days:.1f}d"


def get_timestamp_now() -> str:
    """
    Get current timestamp in ISO format.
    
    Returns:
        str: ISO format timestamp
    """
    return datetime.utcnow().isoformat()