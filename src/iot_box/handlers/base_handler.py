"""
Base Handler for IoT Box

Abstract base class for all device handlers.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import asyncio
import logging

from ..utils.logger import get_logger

logger = get_logger(__name__)


class BaseHandler(ABC):
    """Abstract base class for device handlers"""
    
    def __init__(self):
        self.connected = False
        self.device_config: Optional[Dict[str, Any]] = None
        self.scan_callback: Optional[callable] = None
        
    @abstractmethod
    async def connect(self, config: Dict[str, Any]) -> bool:
        """Connect to the device"""
        pass
    
    @abstractmethod
    async def disconnect(self) -> bool:
        """Disconnect from the device"""
        pass
    
    @abstractmethod
    async def scan(self) -> Optional[str]:
        """Perform a scan and return data"""
        pass
    
    @abstractmethod
    async def is_connected(self) -> bool:
        """Check if device is connected"""
        pass
    
    def set_scan_callback(self, callback: callable):
        """Set callback function for scan events"""
        self.scan_callback = callback
    
    async def _trigger_scan_callback(self, scan_data: str):
        """Trigger scan callback if set"""
        if self.scan_callback:
            try:
                await self.scan_callback(scan_data)
            except Exception as e:
                logger.error(f"Error in scan callback: {e}")
    
    def get_device_info(self) -> Dict[str, Any]:
        """Get device information"""
        return {
            "connected": self.connected,
            "config": self.device_config,
            "handler_type": self.__class__.__name__
        }
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate device configuration"""
        required_fields = self.get_required_config_fields()
        
        for field in required_fields:
            if field not in config:
                logger.error(f"Missing required config field: {field}")
                return False
        
        return True
    
    @abstractmethod
    def get_required_config_fields(self) -> list:
        """Get list of required configuration fields"""
        pass
    
    @abstractmethod
    def get_supported_protocols(self) -> list:
        """Get list of supported protocols"""
        pass
