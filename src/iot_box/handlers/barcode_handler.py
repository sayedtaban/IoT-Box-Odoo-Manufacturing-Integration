"""
Barcode Scanner Handler for IoT Box

Handles various types of barcode scanners including USB, Bluetooth, and Network.
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional, List
import json
import socket
import threading

from .base_handler import BaseHandler
from ..utils.logger import get_logger

logger = get_logger(__name__)


class BarcodeHandler(BaseHandler):
    """Handler for barcode scanners"""
    
    def __init__(self):
        super().__init__()
        self.scanner_type = None
        self.connection = None
        self.scan_thread = None
        self.running = False
        
    async def connect(self, config: Dict[str, Any]) -> bool:
        """Connect to barcode scanner"""
        try:
            if not self.validate_config(config):
                return False
            
            self.device_config = config
            scanner_type = config.get('type', 'usb')
            
            if scanner_type == 'usb':
                return await self._connect_usb()
            elif scanner_type == 'bluetooth':
                return await self._connect_bluetooth()
            elif scanner_type == 'network':
                return await self._connect_network()
            else:
                logger.error(f"Unsupported scanner type: {scanner_type}")
                return False
                
        except Exception as e:
            logger.error(f"Error connecting to barcode scanner: {e}")
            return False
    
    async def disconnect(self) -> bool:
        """Disconnect from barcode scanner"""
        try:
            self.running = False
            
            if self.scan_thread and self.scan_thread.is_alive():
                self.scan_thread.join(timeout=5)
            
            if self.connection:
                if hasattr(self.connection, 'close'):
                    self.connection.close()
                self.connection = None
            
            self.connected = False
            logger.info("Disconnected from barcode scanner")
            return True
            
        except Exception as e:
            logger.error(f"Error disconnecting from barcode scanner: {e}")
            return False
    
    async def scan(self) -> Optional[str]:
        """Perform a scan"""
        if not self.connected:
            logger.warning("Scanner not connected")
            return None
        
        try:
            if self.scanner_type == 'usb':
                return await self._scan_usb()
            elif self.scanner_type == 'bluetooth':
                return await self._scan_bluetooth()
            elif self.scanner_type == 'network':
                return await self._scan_network()
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error during scan: {e}")
            return None
    
    async def is_connected(self) -> bool:
        """Check if scanner is connected"""
        return self.connected
    
    def get_required_config_fields(self) -> List[str]:
        """Get required configuration fields"""
        return ['type', 'name']
    
    def get_supported_protocols(self) -> List[str]:
        """Get supported protocols"""
        return ['usb_hid', 'serial', 'bluetooth', 'network_tcp']
    
    async def _connect_usb(self) -> bool:
        """Connect to USB barcode scanner"""
        try:
            import usb.core
            import usb.util
            
            vendor_id = int(self.device_config.get('vendor_id', '0x05e0'), 16)
            product_id = int(self.device_config.get('product_id', '0x1200'), 16)
            
            # Find the device
            device = usb.core.find(idVendor=vendor_id, idProduct=product_id)
            if device is None:
                logger.error(f"USB device not found: {vendor_id:04x}:{product_id:04x}")
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
            
            logger.info(f"Connected to USB barcode scanner: {vendor_id:04x}:{product_id:04x}")
            return True
            
        except ImportError:
            logger.error("pyusb not available, USB support disabled")
            return False
        except Exception as e:
            logger.error(f"Error connecting to USB scanner: {e}")
            return False
    
    async def _connect_bluetooth(self) -> bool:
        """Connect to Bluetooth barcode scanner"""
        try:
            import bluetooth
            
            mac_address = self.device_config.get('mac_address')
            if not mac_address:
                logger.error("MAC address not provided for Bluetooth scanner")
                return False
            
            # Create Bluetooth socket
            sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
            
            # Connect to device
            sock.connect((mac_address, 1))  # RFCOMM port 1
            
            self.connection = sock
            self.scanner_type = 'bluetooth'
            self.connected = True
            
            # Start scan monitoring thread
            self.running = True
            self.scan_thread = threading.Thread(target=self._bluetooth_scan_loop)
            self.scan_thread.daemon = True
            self.scan_thread.start()
            
            logger.info(f"Connected to Bluetooth barcode scanner: {mac_address}")
            return True
            
        except ImportError:
            logger.error("pybluez not available, Bluetooth support disabled")
            return False
        except Exception as e:
            logger.error(f"Error connecting to Bluetooth scanner: {e}")
            return False
    
    async def _connect_network(self) -> bool:
        """Connect to network barcode scanner"""
        try:
            ip = self.device_config.get('ip')
            port = self.device_config.get('port', 8080)
            timeout = self.device_config.get('timeout', 10)
            
            if not ip:
                logger.error("IP address not provided for network scanner")
                return False
            
            # Create socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
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
            
            logger.info(f"Connected to network barcode scanner: {ip}:{port}")
            return True
            
        except Exception as e:
            logger.error(f"Error connecting to network scanner: {e}")
            return False
    
    async def _scan_usb(self) -> Optional[str]:
        """Scan from USB device"""
        # USB scanning is handled by the monitoring thread
        # This method can be used for manual scanning if needed
        return None
    
    async def _scan_bluetooth(self) -> Optional[str]:
        """Scan from Bluetooth device"""
        # Bluetooth scanning is handled by the monitoring thread
        return None
    
    async def _scan_network(self) -> Optional[str]:
        """Scan from network device"""
        # Network scanning is handled by the monitoring thread
        return None
    
    def _usb_scan_loop(self):
        """USB scan monitoring loop"""
        try:
            while self.running and self.connected:
                try:
                    # Read data from USB endpoint
                    data = self.connection['endpoint'].read(64, timeout=1000)
                    
                    if data:
                        # Convert bytes to string
                        scan_data = ''.join([chr(b) for b in data if b != 0])
                        scan_data = scan_data.strip()
                        
                        if scan_data:
                            logger.debug(f"USB scan data: {scan_data}")
                            asyncio.create_task(self._trigger_scan_callback(scan_data))
                
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
                    logger.error(f"Error in USB scan loop: {e}")
                    break
                    
        except Exception as e:
            logger.error(f"Error in USB scan loop: {e}")
        finally:
            self.connected = False
    
    def _bluetooth_scan_loop(self):
        """Bluetooth scan monitoring loop"""
        try:
            while self.running and self.connected:
                try:
                    # Read data from Bluetooth socket
                    data = self.connection.recv(1024)
                    
                    if data:
                        scan_data = data.decode('utf-8').strip()
                        
                        if scan_data:
                            logger.debug(f"Bluetooth scan data: {scan_data}")
                            asyncio.create_task(self._trigger_scan_callback(scan_data))
                
                except Exception as e:
                    logger.error(f"Error in Bluetooth scan loop: {e}")
                    break
                    
        except Exception as e:
            logger.error(f"Error in Bluetooth scan loop: {e}")
        finally:
            self.connected = False
    
    def _network_scan_loop(self):
        """Network scan monitoring loop"""
        try:
            while self.running and self.connected:
                try:
                    # Read data from network socket
                    data = self.connection.recv(1024)
                    
                    if data:
                        scan_data = data.decode('utf-8').strip()
                        
                        if scan_data:
                            logger.debug(f"Network scan data: {scan_data}")
                            asyncio.create_task(self._trigger_scan_callback(scan_data))
                
                except socket.timeout:
                    # Timeout is normal, continue
                    continue
                except Exception as e:
                    logger.error(f"Error in network scan loop: {e}")
                    break
                    
        except Exception as e:
            logger.error(f"Error in network scan loop: {e}")
        finally:
            self.connected = False
    
    def _parse_scan_data(self, raw_data: str) -> Optional[str]:
        """Parse raw scan data"""
        try:
            # Remove any control characters
            clean_data = ''.join(char for char in raw_data if char.isprintable())
            
            # Validate barcode format (basic validation)
            if len(clean_data) < 3 or len(clean_data) > 50:
                logger.warning(f"Invalid barcode length: {len(clean_data)}")
                return None
            
            # Check for common barcode prefixes/suffixes
            if clean_data.startswith('\x02') and clean_data.endswith('\x03'):
                clean_data = clean_data[1:-1]  # Remove STX/ETX
            
            return clean_data
            
        except Exception as e:
            logger.error(f"Error parsing scan data: {e}")
            return None
