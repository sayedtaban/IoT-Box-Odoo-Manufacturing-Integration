"""
Helper utilities for IoT Box

Provides common helper functions and utilities.
"""

import time
import hashlib
import uuid
import json
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timezone
import asyncio
import functools


def generate_id(prefix: str = "") -> str:
    """Generate a unique ID with optional prefix"""
    unique_id = str(uuid.uuid4()).replace('-', '')
    return f"{prefix}_{unique_id}" if prefix else unique_id


def generate_scan_id() -> str:
    """Generate a unique scan ID"""
    timestamp = int(time.time() * 1000)
    random_part = str(uuid.uuid4())[:8]
    return f"scan_{timestamp}_{random_part}"


def generate_work_order_id() -> str:
    """Generate a work order ID"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M")
    random_part = str(uuid.uuid4())[:4].upper()
    return f"WO{timestamp}{random_part}"


def hash_data(data: str, algorithm: str = "sha256") -> str:
    """Hash data using specified algorithm"""
    if algorithm == "md5":
        return hashlib.md5(data.encode()).hexdigest()
    elif algorithm == "sha1":
        return hashlib.sha1(data.encode()).hexdigest()
    elif algorithm == "sha256":
        return hashlib.sha256(data.encode()).hexdigest()
    elif algorithm == "sha512":
        return hashlib.sha512(data.encode()).hexdigest()
    else:
        raise ValueError(f"Unsupported hash algorithm: {algorithm}")


def get_current_timestamp() -> float:
    """Get current Unix timestamp"""
    return time.time()


def format_timestamp(timestamp: float, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Format timestamp to readable string"""
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime(format_str)


def parse_timestamp(timestamp_str: str, format_str: str = "%Y-%m-%d %H:%M:%S") -> float:
    """Parse timestamp string to Unix timestamp"""
    dt = datetime.strptime(timestamp_str, format_str)
    return dt.replace(tzinfo=timezone.utc).timestamp()


def deep_merge_dicts(dict1: Dict, dict2: Dict) -> Dict:
    """Deep merge two dictionaries"""
    result = dict1.copy()
    
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge_dicts(result[key], value)
        else:
            result[key] = value
    
    return result


def safe_json_loads(json_str: str, default: Any = None) -> Any:
    """Safely load JSON string with default value"""
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return default


def safe_json_dumps(obj: Any, default: str = "{}") -> str:
    """Safely dump object to JSON string with default value"""
    try:
        return json.dumps(obj, default=str)
    except (TypeError, ValueError):
        return default


def chunk_list(lst: List[Any], chunk_size: int) -> List[List[Any]]:
    """Split list into chunks of specified size"""
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


def flatten_dict(d: Dict, parent_key: str = '', sep: str = '.') -> Dict:
    """Flatten nested dictionary"""
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def retry_on_exception(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """Decorator to retry function on exception"""
    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        raise last_exception
            
            return None
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        raise last_exception
            
            return None
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def timeout_after(seconds: float):
    """Decorator to add timeout to function"""
    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=seconds)
            except asyncio.TimeoutError:
                raise TimeoutError(f"Function {func.__name__} timed out after {seconds} seconds")
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            import signal
            
            def timeout_handler(signum, frame):
                raise TimeoutError(f"Function {func.__name__} timed out after {seconds} seconds")
            
            old_handler = signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(int(seconds))
            
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                signal.alarm(0)
                signal.signal(signal.SIGALRM, old_handler)
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def format_bytes(bytes_value: int) -> str:
    """Format bytes to human readable string"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.1f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.1f} PB"


def format_duration(seconds: float) -> str:
    """Format duration in seconds to human readable string"""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    elif seconds < 86400:
        hours = seconds / 3600
        return f"{hours:.1f}h"
    else:
        days = seconds / 86400
        return f"{days:.1f}d"


def calculate_percentage(part: float, total: float) -> float:
    """Calculate percentage"""
    if total == 0:
        return 0.0
    return (part / total) * 100


def clamp(value: float, min_value: float, max_value: float) -> float:
    """Clamp value between min and max"""
    return max(min_value, min(value, max_value))


def is_valid_uuid(uuid_string: str) -> bool:
    """Check if string is valid UUID"""
    try:
        uuid.UUID(uuid_string)
        return True
    except ValueError:
        return False


def extract_numbers(text: str) -> List[float]:
    """Extract all numbers from text"""
    import re
    pattern = r'-?\d+\.?\d*'
    matches = re.findall(pattern, text)
    return [float(match) for match in matches]


def clean_string(text: str, remove_whitespace: bool = True) -> str:
    """Clean string by removing unwanted characters"""
    if not text:
        return ""
    
    # Remove control characters
    cleaned = ''.join(char for char in text if ord(char) >= 32 or char in '\t\n\r')
    
    if remove_whitespace:
        cleaned = ' '.join(cleaned.split())
    
    return cleaned


def truncate_string(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate string to maximum length with suffix"""
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def normalize_string(text: str) -> str:
    """Normalize string for comparison"""
    if not text:
        return ""
    
    # Convert to lowercase and remove extra whitespace
    normalized = text.lower().strip()
    
    # Remove special characters
    import re
    normalized = re.sub(r'[^\w\s]', '', normalized)
    
    # Replace multiple spaces with single space
    normalized = re.sub(r'\s+', ' ', normalized)
    
    return normalized


def create_batch_id() -> str:
    """Create a batch ID for grouping operations"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    random_part = str(uuid.uuid4())[:6].upper()
    return f"BATCH_{timestamp}_{random_part}"


def parse_boolean(value: Any) -> bool:
    """Parse various boolean representations"""
    if isinstance(value, bool):
        return value
    
    if isinstance(value, str):
        return value.lower() in ('true', '1', 'yes', 'on', 'enabled')
    
    if isinstance(value, (int, float)):
        return bool(value)
    
    return False


def safe_int(value: Any, default: int = 0) -> int:
    """Safely convert value to integer with default"""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    """Safely convert value to float with default"""
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_str(value: Any, default: str = "") -> str:
    """Safely convert value to string with default"""
    try:
        return str(value)
    except (ValueError, TypeError):
        return default


def merge_lists(*lists) -> List:
    """Merge multiple lists into one"""
    result = []
    for lst in lists:
        if isinstance(lst, list):
            result.extend(lst)
        else:
            result.append(lst)
    return result


def remove_duplicates(lst: List) -> List:
    """Remove duplicates from list while preserving order"""
    seen = set()
    result = []
    for item in lst:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def group_by_key(items: List[Dict], key: str) -> Dict[Any, List[Dict]]:
    """Group list of dictionaries by key"""
    groups = {}
    for item in items:
        group_key = item.get(key)
        if group_key not in groups:
            groups[group_key] = []
        groups[group_key].append(item)
    return groups


def sort_by_key(items: List[Dict], key: str, reverse: bool = False) -> List[Dict]:
    """Sort list of dictionaries by key"""
    return sorted(items, key=lambda x: x.get(key, 0), reverse=reverse)
