"""
Device Manager for IoT Box

Handles device detection, registration, and management for various scanner types.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import yaml
import json

from ..handlers.base_handler import BaseHandler
from ..handlers.barcode_handler import BarcodeHandler
from ..handlers.rfid_handler import RFIDHandler
from ..utils.logger import get_logger

logger = get_logger(__name__)


class DeviceType(Enum):
    """Device type enumeration"""
    BARCODE = "barcode"
    RFID = "rfid"
    UNKNOWN = "unknown"


class DeviceStatus(Enum):
    """Device status enumeration"""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    UNKNOWN = "unknown"


@dataclass
class Device:
    """Device information dataclass"""
    id: str
    name: str
    type: DeviceType
    status: DeviceStatus
    handler: Optional[BaseHandler] = None
    config: Dict[str, Any] = None
    last_seen: float = 0.0
    error_count: int = 0
    max_errors: int = 5


class DeviceManager:
    """Manages all connected devices and their handlers"""
    
    def __init__(self, config_path: str = "config/devices.yaml"):
        self.config_path = config_path
        self.devices: Dict[str, Device] = {}
        self.handlers: Dict[DeviceType, BaseHandler] = {}
        self.running = False
        self.scan_interval = 5.0
        self._load_config()
        self._initialize_handlers()
        
    def _load_config(self):
        """Load device configuration from YAML file"""
        try:
            with open(self.config_path, 'r') as file:
                self.config = yaml.safe_load(file)
                
            # Set scan intervals
            detection_config = self.config.get('detection', {})
            self.scan_interval = detection_config.get('scan_interval', 5.0)
            
            logger.info(f"Loaded device configuration from {self.config_path}")
            
        except FileNotFoundError:
            logger.error(f"Configuration file not found: {self.config_path}")
            self.config = {}
        except yaml.YAMLError as e:
            logger.error(f"Error parsing configuration file: {e}")
            self.config = {}
    
    def _initialize_handlers(self):
        """Initialize device handlers"""
        self.handlers[DeviceType.BARCODE] = BarcodeHandler()
        self.handlers[DeviceType.RFID] = RFIDHandler()
        
        logger.info("Initialized device handlers")
    
    async def start(self):
        """Start the device manager"""
        self.running = True
        logger.info("Starting device manager")
        
        # Start device detection task
        asyncio.create_task(self._device_detection_loop())
        
        # Load configured devices
        await self._load_configured_devices()
        
    async def stop(self):
        """Stop the device manager"""
        self.running = False
        logger.info("Stopping device manager")
        
        # Disconnect all devices
        for device in self.devices.values():
            if device.handler:
                await device.handler.disconnect()
    
    async def _device_detection_loop(self):
        """Main device detection loop"""
        while self.running:
            try:
                await self._scan_for_devices()
                await asyncio.sleep(self.scan_interval)
            except Exception as e:
                logger.error(f"Error in device detection loop: {e}")
                await asyncio.sleep(5)
    
    async def _scan_for_devices(self):
        """Scan for new devices"""
        # Scan for USB devices
        if self.config.get('detection', {}).get('usb', {}).get('enabled', True):
            await self._scan_usb_devices()
            
        # Scan for Bluetooth devices
        if self.config.get('detection', {}).get('bluetooth', {}).get('enabled', True):
            await self._scan_bluetooth_devices()
            
        # Scan for network devices
        if self.config.get('detection', {}).get('network', {}).get('enabled', True):
            await self._scan_network_devices()
    
    async def _scan_usb_devices(self):
        """Scan for USB devices"""
        try:
            import usb.core
            import usb.util
            
            # Find all USB devices
            devices = usb.core.find(find_all=True)
            
            for device in devices:
                vendor_id = f"0x{device.idVendor:04x}"
                product_id = f"0x{device.idProduct:04x}"
                
                # Check if device is configured
                device_config = self._find_device_config(vendor_id, product_id, "usb")
                if device_config and device_config.get('enabled', False):
                    device_id = f"usb_{vendor_id}_{product_id}"
                    
                    if device_id not in self.devices:
                        await self._register_device(device_id, device_config)
                        
        except ImportError:
            logger.warning("pyusb not available, USB device detection disabled")
        except Exception as e:
            logger.error(f"Error scanning USB devices: {e}")
    
    async def _scan_bluetooth_devices(self):
        """Scan for Bluetooth devices"""
        try:
            import bluetooth
            
            # Scan for nearby Bluetooth devices
            nearby_devices = bluetooth.discover_devices(duration=8, lookup_names=True)
            
            for addr, name in nearby_devices:
                # Check if device is configured
                device_config = self._find_device_config(addr, name, "bluetooth")
                if device_config and device_config.get('enabled', False):
                    device_id = f"bt_{addr.replace(':', '_')}"
                    
                    if device_id not in self.devices:
                        await self._register_device(device_id, device_config)
                        
        except ImportError:
            logger.warning("pybluez not available, Bluetooth device detection disabled")
        except Exception as e:
            logger.error(f"Error scanning Bluetooth devices: {e}")
    
    async def _scan_network_devices(self):
        """Scan for network devices"""
        try:
            import socket
            import ipaddress
            
            # Get network configuration
            network_config = self.config.get('detection', {}).get('network', {})
            subnet = network_config.get('subnet', '192.168.1.0/24')
            port_range = network_config.get('port_range', '8000-9000')
            
            # Parse subnet
            network = ipaddress.ip_network(subnet)
            
            # Scan network for devices
            for ip in network.hosts():
                ip_str = str(ip)
                
                # Check if device is configured
                device_config = self._find_device_config(ip_str, None, "network")
                if device_config and device_config.get('enabled', False):
                    device_id = f"net_{ip_str.replace('.', '_')}"
                    
                    if device_id not in self.devices:
                        await self._register_device(device_id, device_config)
                        
        except Exception as e:
            logger.error(f"Error scanning network devices: {e}")
    
    def _find_device_config(self, identifier1: str, identifier2: str, device_type: str) -> Optional[Dict]:
        """Find device configuration by identifiers"""
        config_section = f"{device_type}_scanners" if device_type != "network" else "rfid_scanners"
        devices = self.config.get(config_section, [])
        
        for device in devices:
            if device_type == "usb":
                if (device.get('vendor_id') == identifier1 and 
                    device.get('product_id') == identifier2):
                    return device
            elif device_type == "bluetooth":
                if device.get('mac_address') == identifier1:
                    return device
            elif device_type == "network":
                if device.get('ip') == identifier1:
                    return device
                    
        return None
    
    async def _load_configured_devices(self):
        """Load pre-configured devices"""
        # Load barcode scanners
        for device_config in self.config.get('barcode_scanners', []):
            if device_config.get('enabled', False):
                device_id = f"barcode_{device_config['name'].lower().replace(' ', '_')}"
                await self._register_device(device_id, device_config)
        
        # Load RFID scanners
        for device_config in self.config.get('rfid_scanners', []):
            if device_config.get('enabled', False):
                device_id = f"rfid_{device_config['name'].lower().replace(' ', '_')}"
                await self._register_device(device_id, device_config)
    
    async def _register_device(self, device_id: str, config: Dict[str, Any]):
        """Register a new device"""
        try:
            device_type = DeviceType.BARCODE if 'barcode' in device_id else DeviceType.RFID
            handler = self.handlers.get(device_type)
            
            if not handler:
                logger.error(f"No handler available for device type: {device_type}")
                return
            
            # Create device instance
            device = Device(
                id=device_id,
                name=config.get('name', f'Device {device_id}'),
                type=device_type,
                status=DeviceStatus.UNKNOWN,
                handler=handler,
                config=config
            )
            
            # Connect to device
            if await handler.connect(config):
                device.status = DeviceStatus.CONNECTED
                device.last_seen = time.time()
                logger.info(f"Successfully registered device: {device.name}")
            else:
                device.status = DeviceStatus.ERROR
                logger.error(f"Failed to connect to device: {device.name}")
            
            self.devices[device_id] = device
            
        except Exception as e:
            logger.error(f"Error registering device {device_id}: {e}")
    
    async def unregister_device(self, device_id: str):
        """Unregister a device"""
        if device_id in self.devices:
            device = self.devices[device_id]
            
            if device.handler:
                await device.handler.disconnect()
            
            del self.devices[device_id]
            logger.info(f"Unregistered device: {device.name}")
    
    def get_device(self, device_id: str) -> Optional[Device]:
        """Get device by ID"""
        return self.devices.get(device_id)
    
    def get_devices_by_type(self, device_type: DeviceType) -> List[Device]:
        """Get all devices of a specific type"""
        return [device for device in self.devices.values() 
                if device.type == device_type]
    
    def get_connected_devices(self) -> List[Device]:
        """Get all connected devices"""
        return [device for device in self.devices.values() 
                if device.status == DeviceStatus.CONNECTED]
    
    async def scan_device(self, device_id: str) -> Optional[str]:
        """Scan from a specific device"""
        device = self.get_device(device_id)
        
        if not device or device.status != DeviceStatus.CONNECTED:
            logger.warning(f"Device {device_id} not available for scanning")
            return None
        
        try:
            scan_data = await device.handler.scan()
            if scan_data:
                device.last_seen = time.time()
                device.error_count = 0
                return scan_data
            else:
                device.error_count += 1
                if device.error_count >= device.max_errors:
                    device.status = DeviceStatus.ERROR
                    logger.error(f"Device {device_id} exceeded max errors")
                
        except Exception as e:
            device.error_count += 1
            device.status = DeviceStatus.ERROR
            logger.error(f"Error scanning device {device_id}: {e}")
            
        return None
    
    def get_device_status(self) -> Dict[str, Any]:
        """Get status of all devices"""
        status = {
            "total_devices": len(self.devices),
            "connected_devices": len(self.get_connected_devices()),
            "devices": []
        }
        
        for device in self.devices.values():
            device_status = {
                "id": device.id,
                "name": device.name,
                "type": device.type.value,
                "status": device.status.value,
                "last_seen": device.last_seen,
                "error_count": device.error_count
            }
            status["devices"].append(device_status)
        
        return status
