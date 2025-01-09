"""
Validation utilities for IoT Box

Provides data validation functions for scan data, work orders, and other inputs.
"""

import re
from typing import Optional, Dict, Any, List
from datetime import datetime


def validate_scan_data(scan_data: str, scan_type: str) -> bool:
    """Validate scan data based on type"""
    if not scan_data or not isinstance(scan_data, str):
        return False
    
    # Remove whitespace
    scan_data = scan_data.strip()
    
    if not scan_data:
        return False
    
    if scan_type.lower() == 'barcode':
        return validate_barcode(scan_data)
    elif scan_type.lower() == 'rfid':
        return validate_rfid(scan_data)
    else:
        # Generic validation
        return len(scan_data) >= 3 and len(scan_data) <= 50
    
    return True


def validate_barcode(barcode: str) -> bool:
    """Validate barcode format"""
    if not barcode:
        return False
    
    # Remove any non-alphanumeric characters except common barcode separators
    clean_barcode = re.sub(r'[^A-Za-z0-9\-\.]', '', barcode)
    
    # Check length (typical barcodes are 8-14 digits)
    if len(clean_barcode) < 3 or len(clean_barcode) > 50:
        return False
    
    # Check if it contains at least some digits
    if not re.search(r'\d', clean_barcode):
        return False
    
    return True


def validate_rfid(rfid: str) -> bool:
    """Validate RFID tag format"""
    if not rfid:
        return False
    
    # RFID tags are typically hexadecimal
    if not re.match(r'^[0-9A-Fa-f]+$', rfid):
        return False
    
    # Check length (typical RFID tags are 8-32 hex characters)
    if len(rfid) < 8 or len(rfid) > 32:
        return False
    
    return True


def validate_work_order(work_order_id: str) -> bool:
    """Validate work order ID format"""
    if not work_order_id:
        return False
    
    # Work order IDs typically start with WO or similar prefix
    if not re.match(r'^[A-Z]{2,4}\d{4,8}$', work_order_id.upper()):
        return False
    
    return True


def validate_component_id(component_id: str) -> bool:
    """Validate component ID format"""
    if not component_id:
        return False
    
    # Component IDs can be alphanumeric with common separators
    if not re.match(r'^[A-Za-z0-9\-\._]+$', component_id):
        return False
    
    # Check length
    if len(component_id) < 3 or len(component_id) > 50:
        return False
    
    return True


def validate_operator_id(operator_id: str) -> bool:
    """Validate operator ID format"""
    if not operator_id:
        return False
    
    # Operator IDs are typically alphanumeric
    if not re.match(r'^[A-Za-z0-9\-_]+$', operator_id):
        return False
    
    # Check length
    if len(operator_id) < 2 or len(operator_id) > 20:
        return False
    
    return True


def validate_device_id(device_id: str) -> bool:
    """Validate device ID format"""
    if not device_id:
        return False
    
    # Device IDs can contain alphanumeric characters and underscores
    if not re.match(r'^[A-Za-z0-9_]+$', device_id):
        return False
    
    # Check length
    if len(device_id) < 3 or len(device_id) > 30:
        return False
    
    return True


def validate_ip_address(ip_address: str) -> bool:
    """Validate IP address format"""
    if not ip_address:
        return False
    
    # IPv4 pattern
    ipv4_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    if re.match(ipv4_pattern, ip_address):
        # Check each octet is 0-255
        octets = ip_address.split('.')
        for octet in octets:
            if not 0 <= int(octet) <= 255:
                return False
        return True
    
    # IPv6 pattern (basic)
    ipv6_pattern = r'^([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$'
    if re.match(ipv6_pattern, ip_address):
        return True
    
    return False


def validate_mac_address(mac_address: str) -> bool:
    """Validate MAC address format"""
    if not mac_address:
        return False
    
    # MAC address pattern (XX:XX:XX:XX:XX:XX)
    mac_pattern = r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$'
    return bool(re.match(mac_pattern, mac_address))


def validate_timestamp(timestamp: float) -> bool:
    """Validate timestamp (Unix timestamp)"""
    if not isinstance(timestamp, (int, float)):
        return False
    
    # Check if timestamp is reasonable (between 2020 and 2030)
    min_timestamp = 1577836800  # 2020-01-01
    max_timestamp = 1893456000  # 2030-01-01
    
    return min_timestamp <= timestamp <= max_timestamp


def validate_config(config: Dict[str, Any], required_fields: List[str]) -> bool:
    """Validate configuration dictionary"""
    if not isinstance(config, dict):
        return False
    
    for field in required_fields:
        if field not in config:
            return False
        
        if config[field] is None:
            return False
    
    return True


def sanitize_input(input_string: str, max_length: int = 100) -> str:
    """Sanitize user input"""
    if not input_string:
        return ""
    
    # Remove control characters
    sanitized = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', input_string)
    
    # Limit length
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    
    return sanitized.strip()


def validate_json_data(data: str) -> bool:
    """Validate JSON data format"""
    if not data:
        return False
    
    try:
        import json
        json.loads(data)
        return True
    except (json.JSONDecodeError, TypeError):
        return False


def validate_email(email: str) -> bool:
    """Validate email address format"""
    if not email:
        return False
    
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(email_pattern, email))


def validate_url(url: str) -> bool:
    """Validate URL format"""
    if not url:
        return False
    
    url_pattern = r'^https?://[^\s/$.?#].[^\s]*$'
    return bool(re.match(url_pattern, url))


def validate_numeric_range(value: Any, min_val: float, max_val: float) -> bool:
    """Validate numeric value is within range"""
    try:
        num_value = float(value)
        return min_val <= num_value <= max_val
    except (ValueError, TypeError):
        return False


def validate_string_length(value: str, min_length: int, max_length: int) -> bool:
    """Validate string length is within range"""
    if not isinstance(value, str):
        return False
    
    return min_length <= len(value) <= max_length


def validate_choice(value: Any, choices: List[Any]) -> bool:
    """Validate value is one of the allowed choices"""
    return value in choices


def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> List[str]:
    """Validate required fields and return list of missing fields"""
    missing_fields = []
    
    for field in required_fields:
        if field not in data or data[field] is None or data[field] == "":
            missing_fields.append(field)
    
    return missing_fields


def validate_scan_event_data(event_data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate scan event data and return validation results"""
    errors = []
    warnings = []
    
    # Required fields
    required_fields = ['device_id', 'scan_data', 'scan_type']
    missing_fields = validate_required_fields(event_data, required_fields)
    
    if missing_fields:
        errors.extend([f"Missing required field: {field}" for field in missing_fields])
    
    # Validate device_id
    if 'device_id' in event_data and not validate_device_id(event_data['device_id']):
        errors.append("Invalid device_id format")
    
    # Validate scan_data
    if 'scan_data' in event_data and not validate_scan_data(event_data['scan_data'], event_data.get('scan_type', '')):
        errors.append("Invalid scan_data format")
    
    # Validate scan_type
    if 'scan_type' in event_data and event_data['scan_type'] not in ['barcode', 'rfid']:
        errors.append("Invalid scan_type (must be 'barcode' or 'rfid')")
    
    # Validate work_order_id if present
    if 'work_order_id' in event_data and event_data['work_order_id'] and not validate_work_order(event_data['work_order_id']):
        warnings.append("Invalid work_order_id format")
    
    # Validate operator_id if present
    if 'operator_id' in event_data and event_data['operator_id'] and not validate_operator_id(event_data['operator_id']):
        warnings.append("Invalid operator_id format")
    
    # Validate timestamp if present
    if 'timestamp' in event_data and not validate_timestamp(event_data['timestamp']):
        warnings.append("Invalid timestamp format")
    
    return {
        'valid': len(errors) == 0,
        'errors': errors,
        'warnings': warnings
    }
