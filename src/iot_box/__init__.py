"""
IoT Box Core Module

This module provides the core functionality for the IoT Box,
including device management, event processing, and Odoo integration.
"""

__version__ = "1.0.0"
__author__ = "IoT Box Team"

from .core.device_manager import DeviceManager
from .core.event_manager import EventManager
from .core.buffer_manager import BufferManager
from .core.security_manager import SecurityManager

__all__ = [
    "DeviceManager",
    "EventManager", 
    "BufferManager",
    "SecurityManager"
]
