"""
Tests for Device Manager

Unit tests for the device management functionality.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from iot_box.core.device_manager import DeviceManager, Device, DeviceType, DeviceStatus


class TestDeviceManager:
    """Test cases for DeviceManager"""
    
    @pytest.fixture
    def device_manager(self):
        """Create a DeviceManager instance for testing"""
        return DeviceManager()
    
    @pytest.fixture
    def mock_device_config(self):
        """Mock device configuration"""
        return {
            'barcode_scanners': [
                {
                    'name': 'Test USB Scanner',
                    'type': 'usb',
                    'vendor_id': '0x05e0',
                    'product_id': '0x1200',
                    'enabled': True
                }
            ],
            'rfid_scanners': [
                {
                    'name': 'Test RFID Reader',
                    'type': 'network',
                    'ip': '192.168.1.100',
                    'port': 8080,
                    'enabled': True
                }
            ]
        }
    
    def test_device_creation(self):
        """Test device object creation"""
        device = Device(
            id="test_device",
            name="Test Device",
            type=DeviceType.BARCODE,
            status=DeviceStatus.CONNECTED
        )
        
        assert device.id == "test_device"
        assert device.name == "Test Device"
        assert device.type == DeviceType.BARCODE
        assert device.status == DeviceStatus.CONNECTED
    
    def test_device_type_enum(self):
        """Test device type enumeration"""
        assert DeviceType.BARCODE.value == "barcode"
        assert DeviceType.RFID.value == "rfid"
        assert DeviceType.UNKNOWN.value == "unknown"
    
    def test_device_status_enum(self):
        """Test device status enumeration"""
        assert DeviceStatus.CONNECTED.value == "connected"
        assert DeviceStatus.DISCONNECTED.value == "disconnected"
        assert DeviceStatus.ERROR.value == "error"
        assert DeviceStatus.UNKNOWN.value == "unknown"
    
    @pytest.mark.asyncio
    async def test_device_manager_initialization(self, device_manager):
        """Test device manager initialization"""
        assert device_manager.devices == {}
        assert device_manager.handlers == {}
        assert device_manager.running == False
    
    @pytest.mark.asyncio
    async def test_device_manager_start_stop(self, device_manager):
        """Test device manager start and stop"""
        # Mock the device detection loop
        with patch.object(device_manager, '_device_detection_loop', new_callable=AsyncMock):
            await device_manager.start()
            assert device_manager.running == True
            
            await device_manager.stop()
            assert device_manager.running == False
    
    def test_get_device_by_type(self, device_manager):
        """Test getting devices by type"""
        # Add test devices
        device1 = Device("device1", "Test Device 1", DeviceType.BARCODE, DeviceStatus.CONNECTED)
        device2 = Device("device2", "Test Device 2", DeviceType.RFID, DeviceStatus.CONNECTED)
        device3 = Device("device3", "Test Device 3", DeviceType.BARCODE, DeviceStatus.DISCONNECTED)
        
        device_manager.devices = {
            "device1": device1,
            "device2": device2,
            "device3": device3
        }
        
        # Test getting barcode devices
        barcode_devices = device_manager.get_devices_by_type(DeviceType.BARCODE)
        assert len(barcode_devices) == 2
        assert device1 in barcode_devices
        assert device3 in barcode_devices
        
        # Test getting RFID devices
        rfid_devices = device_manager.get_devices_by_type(DeviceType.RFID)
        assert len(rfid_devices) == 1
        assert device2 in rfid_devices
    
    def test_get_connected_devices(self, device_manager):
        """Test getting connected devices"""
        # Add test devices
        device1 = Device("device1", "Test Device 1", DeviceType.BARCODE, DeviceStatus.CONNECTED)
        device2 = Device("device2", "Test Device 2", DeviceType.RFID, DeviceStatus.CONNECTED)
        device3 = Device("device3", "Test Device 3", DeviceType.BARCODE, DeviceStatus.DISCONNECTED)
        
        device_manager.devices = {
            "device1": device1,
            "device2": device2,
            "device3": device3
        }
        
        connected_devices = device_manager.get_connected_devices()
        assert len(connected_devices) == 2
        assert device1 in connected_devices
        assert device2 in connected_devices
        assert device3 not in connected_devices
    
    def test_get_device_status(self, device_manager):
        """Test getting device status"""
        # Add test devices
        device1 = Device("device1", "Test Device 1", DeviceType.BARCODE, DeviceStatus.CONNECTED)
        device2 = Device("device2", "Test Device 2", DeviceType.RFID, DeviceStatus.DISCONNECTED)
        
        device_manager.devices = {
            "device1": device1,
            "device2": device2
        }
        
        status = device_manager.get_device_status()
        
        assert status['total_devices'] == 2
        assert status['connected_devices'] == 1
        assert len(status['devices']) == 2
        
        # Check device details
        device_statuses = {d['id']: d for d in status['devices']}
        assert device_statuses['device1']['status'] == 'connected'
        assert device_statuses['device2']['status'] == 'disconnected'
    
    @pytest.mark.asyncio
    async def test_scan_device_not_connected(self, device_manager):
        """Test scanning from disconnected device"""
        device = Device("test_device", "Test Device", DeviceType.BARCODE, DeviceStatus.DISCONNECTED)
        device_manager.devices["test_device"] = device
        
        result = await device_manager.scan_device("test_device")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_scan_device_connected(self, device_manager):
        """Test scanning from connected device"""
        # Mock handler
        mock_handler = Mock()
        mock_handler.scan = AsyncMock(return_value="test_scan_data")
        
        device = Device("test_device", "Test Device", DeviceType.BARCODE, DeviceStatus.CONNECTED)
        device.handler = mock_handler
        device_manager.devices["test_device"] = device
        
        result = await device_manager.scan_device("test_device")
        assert result == "test_scan_data"
        mock_handler.scan.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_scan_device_error(self, device_manager):
        """Test scanning from device with error"""
        # Mock handler that raises exception
        mock_handler = Mock()
        mock_handler.scan = AsyncMock(side_effect=Exception("Scan error"))
        
        device = Device("test_device", "Test Device", DeviceType.BARCODE, DeviceStatus.CONNECTED)
        device.handler = mock_handler
        device_manager.devices["test_device"] = device
        
        result = await device_manager.scan_device("test_device")
        assert result is None
        assert device.error_count == 1
        assert device.status == DeviceStatus.ERROR


if __name__ == "__main__":
    pytest.main([__file__])
