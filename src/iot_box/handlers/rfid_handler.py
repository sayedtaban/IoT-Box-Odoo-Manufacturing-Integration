"""
RFID Scanner Handler for IoT Box

Handles various types of RFID scanners including UHF and HF readers.
"""

import asyncio
import logging
import time
import json
import socket
import threading
from typing import Dict, Any, Optional, List

from .base_handler import BaseHandler
from ..utils.logger import get_logger

logger = get_logger(__name__)


class RFIDHandler(BaseHandler):
    """Handler for RFID scanners"""
    
    def __init__(self):
        super().__init__()
        self.scanner_type = None
        self.connection = None
        self.scan_thread = None
        self.running = False
        self.last_tag_id = None
        self.tag_cache = {}
        
    async def connect(self, config: Dict[str, Any]) -> bool:
        """Connect to RFID scanner"""
        try:
            if not self.validate_config(config):
                return False
            
            self.device_config = config
            scanner_type = config.get('type', 'network')
            
            if scanner_type == 'usb':
                return await self._connect_usb()
            elif scanner_type == 'network':
                return await self._connect_network()
            else:
                logger.error(f"Unsupported RFID scanner type: {scanner_type}")
                return False
                
        except Exception as e:
            logger.error(f"Error connecting to RFID scanner: {e}")
            return False
    
    async def disconnect(self) -> bool:
        """Disconnect from RFID scanner"""
        try:
            self.running = False
            
            if self.scan_thread and self.scan_thread.is_alive():
                self.scan_thread.join(timeout=5)
            
            if self.connection:
                if hasattr(self.connection, 'close'):
                    self.connection.close()
                self.connection = None
            
            self.connected = False
            logger.info("Disconnected from RFID scanner")
            return True
            
        except Exception as e:
            logger.error(f"Error disconnecting from RFID scanner: {e}")
            return False
    
    async def scan(self) -> Optional[str]:
        """Perform a scan"""
        if not self.connected:
            logger.warning("RFID scanner not connected")
            return None
        
        try:
            if self.scanner_type == 'usb':
                return await self._scan_usb()
            elif self.scanner_type == 'network':
                return await self._scan_network()
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error during RFID scan: {e}")
            return None
    
    async def is_connected(self) -> bool:
        """Check if RFID scanner is connected"""
        return self.connected
    
    def get_required_config_fields(self) -> List[str]:
        """Get required configuration fields"""
        return ['type', 'name']
    
    def get_supported_protocols(self) -> List[str]:
        """Get supported protocols"""
        return ['epc_gen2', 'iso14443', 'iso15693', 'network_tcp']
    
    async def _connect_usb(self) -> bool:
        """Connect to USB RFID scanner"""
        try:
            import usb.core
            import usb.util
            
            vendor_id = int(self.device_config.get('vendor_id', '0x1234'), 16)
            product_id = int(self.device_config.get('product_id', '0x5678'), 16)
            
            # Find the device
            device = usb.core.find(idVendor=vendor_id, idProduct=product_id)
            if device is None:
                logger.error(f"USB RFID device not found: {vendor_id:04x}:{product_id:04x}")
                return False
            
            # Set configuration
            try:
                device.set_configuration()
            except usb.core.USBError as e:
                if e.errno == 16:  # Device busy
                    logger.warning("Device busy, trying to detach kernel driver")
                    device.reset()
                    device.set_configuration()
                else:
                    raise
            
            # Get endpoint
            cfg = device.get_active_configuration()
            intf = cfg[(0, 0)]
            
            ep = usb.util.find_descriptor(
                intf,
                custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_IN
            )
            
            if ep is None:
                logger.error("Could not find input endpoint")
                return False
            
            self.connection = {
                'device': device,
                'endpoint': ep,
                'interface': intf
            }
            
            self.scanner_type = 'usb'
            self.connected = True
            
            # Start scan monitoring thread
            self.running = True
            self.scan_thread = threading.Thread(target=self._usb_scan_loop)
            self.scan_thread.daemon = True
            self.scan_thread.start()
            
            logger.info(f"Connected to USB RFID scanner: {vendor_id:04x}:{product_id:04x}")
            return True
            
        except ImportError:
            logger.error("pyusb not available, USB RFID support disabled")
            return False
        except Exception as e:
            logger.error(f"Error connecting to USB RFID scanner: {e}")
            return False
    
    async def _connect_network(self) -> bool:
        """Connect to network RFID scanner"""
        try:
            ip = self.device_config.get('ip')
            port = self.device_config.get('port', 8080)
            timeout = self.device_config.get('timeout', 10)
            protocol = self.device_config.get('protocol', 'tcp')
            
            if not ip:
                logger.error("IP address not provided for network RFID scanner")
                return False
            
            # Create socket
            if protocol.lower() == 'tcp':
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            else:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            
            sock.settimeout(timeout)
            
            # Connect to scanner
            sock.connect((ip, port))
            
            self.connection = sock
            self.scanner_type = 'network'
            self.connected = True
            
            # Start scan monitoring thread
            self.running = True
            self.scan_thread = threading.Thread(target=self._network_scan_loop)
            self.scan_thread.daemon = True
            self.scan_thread.start()
            
            logger.info(f"Connected to network RFID scanner: {ip}:{port}")
            return True
            
        except Exception as e:
            logger.error(f"Error connecting to network RFID scanner: {e}")
            return False
    
    async def _scan_usb(self) -> Optional[str]:
        """Scan from USB RFID device"""
        # USB scanning is handled by the monitoring thread
        return None
    
    async def _scan_network(self) -> Optional[str]:
        """Scan from network RFID device"""
        # Network scanning is handled by the monitoring thread
        return None
    
    def _usb_scan_loop(self):
        """USB RFID scan monitoring loop"""
        try:
            while self.running and self.connected:
                try:
                    # Read data from USB endpoint
                    data = self.connection['endpoint'].read(64, timeout=1000)
                    
                    if data:
                        # Parse RFID tag data
                        tag_data = self._parse_rfid_data(data)
                        
                        if tag_data:
                            logger.debug(f"USB RFID tag: {tag_data}")
                            asyncio.create_task(self._trigger_scan_callback(tag_data))
                
                except usb.core.USBTimeoutError:
                    # Timeout is normal, continue
                    continue
                except usb.core.USBError as e:
                    if e.errno == 110:  # Operation timed out
                        continue
                    else:
                        logger.error(f"USB error: {e}")
                        break
                except Exception as e:
                    logger.error(f"Error in USB RFID scan loop: {e}")
                    break
                    
        except Exception as e:
            logger.error(f"Error in USB RFID scan loop: {e}")
        finally:
            self.connected = False
    
    def _network_scan_loop(self):
        """Network RFID scan monitoring loop"""
        try:
            while self.running and self.connected:
                try:
                    # Read data from network socket
                    data = self.connection.recv(1024)
                    
                    if data:
                        # Parse RFID tag data
                        tag_data = self._parse_network_rfid_data(data)
                        
                        if tag_data:
                            logger.debug(f"Network RFID tag: {tag_data}")
                            asyncio.create_task(self._trigger_scan_callback(tag_data))
                
                except socket.timeout:
                    # Timeout is normal, continue
                    continue
                except Exception as e:
                    logger.error(f"Error in network RFID scan loop: {e}")
                    break
                    
        except Exception as e:
            logger.error(f"Error in network RFID scan loop: {e}")
        finally:
            self.connected = False
    
    def _parse_rfid_data(self, raw_data: bytes) -> Optional[str]:
        """Parse raw RFID data from USB"""
        try:
            # Convert bytes to hex string
            hex_data = raw_data.hex().upper()
            
            # Look for EPC Gen2 format
            if len(hex_data) >= 8:
                # Extract EPC from the data
                epc = hex_data[:16]  # First 8 bytes (16 hex chars)
                return epc
            
            return None
            
        except Exception as e:
            logger.error(f"Error parsing USB RFID data: {e}")
            return None
    
    def _parse_network_rfid_data(self, raw_data: bytes) -> Optional[str]:
        """Parse RFID data from network scanner"""
        try:
            # Try to parse as JSON first
            try:
                data = json.loads(raw_data.decode('utf-8'))
                
                # Common RFID reader JSON formats
                if 'tag_id' in data:
                    return data['tag_id']
                elif 'epc' in data:
                    return data['epc']
                elif 'id' in data:
                    return data['id']
                elif 'data' in data:
                    return data['data']
                    
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass
            
            # Try to parse as plain text
            text_data = raw_data.decode('utf-8', errors='ignore').strip()
            
            if text_data:
                # Remove any control characters
                clean_data = ''.join(char for char in text_data if char.isprintable())
                
                # Validate RFID format (hex string)
                if all(c in '0123456789ABCDEFabcdef' for c in clean_data):
                    return clean_data.upper()
            
            return None
            
        except Exception as e:
            logger.error(f"Error parsing network RFID data: {e}")
            return None
    
    def _validate_rfid_tag(self, tag_id: str) -> bool:
        """Validate RFID tag format"""
        try:
            # Check if it's a valid hex string
            if not all(c in '0123456789ABCDEFabcdef' for c in tag_id):
                return False
            
            # Check length (typical RFID tags are 8-32 hex characters)
            if len(tag_id) < 8 or len(tag_id) > 32:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating RFID tag: {e}")
            return False
    
    def _deduplicate_tag(self, tag_id: str) -> bool:
        """Check if tag is duplicate (same tag within short time)"""
        current_time = time.time()
        
        # Check if this tag was seen recently
        if tag_id in self.tag_cache:
            last_seen = self.tag_cache[tag_id]
            if current_time - last_seen < 2.0:  # 2 second deduplication window
                return True  # Duplicate
        
        # Update cache
        self.tag_cache[tag_id] = current_time
        
        # Clean old entries from cache
        cutoff_time = current_time - 10.0  # Keep 10 seconds of history
        self.tag_cache = {
            tid: timestamp for tid, timestamp in self.tag_cache.items()
            if timestamp > cutoff_time
        }
        
        return False  # Not duplicate
