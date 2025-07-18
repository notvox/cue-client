# client/src/notvox/utils/formatting.py
"""Formatting utilities for NotVox client"""

from datetime import datetime, timedelta
from typing import Union

def format_time(iso_time: str) -> str:
    """Format ISO time string to human readable"""
    dt = datetime.fromisoformat(iso_time.replace("Z", "+00:00"))
    return dt.strftime("%I:%M %p")

def format_duration(seconds: int) -> str:
    """Format seconds to human readable duration"""
    intervals = [
        (86400, 'd', 'days'),
        (3600, 'h', 'hours'),
        (60, 'm', 'minutes'),
        (1, 's', 'seconds')
    ]
    
    for divisor, suffix, _ in intervals:
        if seconds >= divisor:
            value = seconds // divisor
            remainder = seconds % divisor
            
            # For days and hours, show the next unit if there's a remainder
            if suffix in ['d', 'h'] and remainder >= intervals[intervals.index((divisor, suffix, _)) + 1][0]:
                next_value = remainder // intervals[intervals.index((divisor, suffix, _)) + 1][0]
                next_suffix = intervals[intervals.index((divisor, suffix, _)) + 1][1]
                return f"{value}{suffix}{next_value}{next_suffix}"
            else:
                return f"{value}{suffix}"
    
    return "0s"

def format_relative_time(iso_time: str) -> str:
    """Format ISO time to relative time (e.g., '2 hours ago')"""
    dt = datetime.fromisoformat(iso_time.replace("Z", "+00:00"))
    now = datetime.now(dt.tzinfo) if dt.tzinfo else datetime.now()
    delta = now - dt

    seconds = delta.total_seconds()
    
    if seconds < 60:
        return "just now"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    elif delta.days == 1:
        return "yesterday"
    elif delta.days < 7:
        return f"{delta.days} days ago"
    else:
        return dt.strftime("%b %d, %Y")

def truncate_text(text: str, max_length: int = 50) -> str:
    """Truncate text with ellipsis if too long"""
    if len(text) > max_length:
        return text[:max_length-3] + "..."
    return text

def format_track_duration_ms(duration_ms: int) -> str:
    """Format milliseconds to MM:SS format"""
    duration_min = duration_ms // 60000
    duration_sec = (duration_ms % 60000) // 1000
    return f"{duration_min}:{duration_sec:02d}"

def get_popularity_indicator(popularity: int) -> str:
    """Get visual indicator for track popularity"""
    if popularity >= 80:
        return "[***]"
    elif popularity >= 60:
        return "[** ]"
    elif popularity >= 40:
        return "[*  ]"
    else:
        return "[   ]"