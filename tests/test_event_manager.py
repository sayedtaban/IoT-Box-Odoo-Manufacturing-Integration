"""
Tests for Event Manager

Unit tests for the event management functionality.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from iot_box.core.event_manager import EventManager, Event, EventType, EventStatus


class TestEventManager:
    """Test cases for EventManager"""
    
    @pytest.fixture
    def event_manager(self):
        """Create an EventManager instance for testing"""
        return EventManager()
    
    @pytest.fixture
    def sample_event_data(self):
        """Sample event data for testing"""
        return {
            'device_id': 'test_device',
            'scan_data': '1234567890',
            'scan_type': 'barcode',
            'work_order_id': 'WO001',
            'operator_id': 'operator_001'
        }
    
    def test_event_creation(self):
        """Test event object creation"""
        event = Event(
            id="test_event",
            type=EventType.SCAN,
            status=EventStatus.PENDING,
            device_id="test_device",
            scan_data="1234567890",
            scan_type="barcode"
        )
        
        assert event.id == "test_event"
        assert event.type == EventType.SCAN
        assert event.status == EventStatus.PENDING
        assert event.device_id == "test_device"
        assert event.scan_data == "1234567890"
        assert event.scan_type == "barcode"
    
    def test_event_type_enum(self):
        """Test event type enumeration"""
        assert EventType.SCAN.value == "scan"
        assert EventType.WORK_ORDER_SET.value == "work_order_set"
        assert EventType.COMPONENT_CONSUMED.value == "component_consumed"
        assert EventType.ERROR.value == "error"
        assert EventType.ALERT.value == "alert"
    
    def test_event_status_enum(self):
        """Test event status enumeration"""
        assert EventStatus.PENDING.value == "pending"
        assert EventStatus.PROCESSING.value == "processing"
        assert EventStatus.COMPLETED.value == "completed"
        assert EventStatus.FAILED.value == "failed"
        assert EventStatus.CANCELLED.value == "cancelled"
    
    @pytest.mark.asyncio
    async def test_event_manager_initialization(self, event_manager):
        """Test event manager initialization"""
        assert event_manager.events == {}
        assert event_manager.event_handlers == {}
        assert event_manager.running == False
    
    @pytest.mark.asyncio
    async def test_event_manager_start_stop(self, event_manager):
        """Test event manager start and stop"""
        # Mock the event processor
        with patch.object(event_manager, '_event_processor', new_callable=AsyncMock):
            await event_manager.start()
            assert event_manager.running == True
            
            await event_manager.stop()
            assert event_manager.running == False
    
    @pytest.mark.asyncio
    async def test_create_event(self, event_manager, sample_event_data):
        """Test creating an event"""
        event_id = await event_manager.create_event(
            event_type=EventType.SCAN,
            device_id=sample_event_data['device_id'],
            scan_data=sample_event_data['scan_data'],
            scan_type=sample_event_data['scan_type'],
            work_order_id=sample_event_data['work_order_id'],
            operator_id=sample_event_data['operator_id']
        )
        
        assert event_id is not None
        assert event_id in event_manager.events
        
        event = event_manager.events[event_id]
        assert event.type == EventType.SCAN
        assert event.device_id == sample_event_data['device_id']
        assert event.scan_data == sample_event_data['scan_data']
        assert event.work_order_id == sample_event_data['work_order_id']
        assert event.operator_id == sample_event_data['operator_id']
    
    def test_register_handler(self, event_manager):
        """Test registering event handlers"""
        mock_handler = Mock()
        
        event_manager.register_handler(EventType.SCAN, mock_handler)
        
        assert EventType.SCAN in event_manager.event_handlers
        assert mock_handler in event_manager.event_handlers[EventType.SCAN]
    
    def test_get_event(self, event_manager):
        """Test getting event by ID"""
        event = Event(
            id="test_event",
            type=EventType.SCAN,
            status=EventStatus.PENDING,
            device_id="test_device",
            scan_data="1234567890",
            scan_type="barcode"
        )
        
        event_manager.events["test_event"] = event
        
        retrieved_event = event_manager.get_event("test_event")
        assert retrieved_event == event
        
        # Test non-existent event
        non_existent = event_manager.get_event("non_existent")
        assert non_existent is None
    
    def test_get_events_by_status(self, event_manager):
        """Test getting events by status"""
        # Create test events
        event1 = Event("event1", EventType.SCAN, EventStatus.PENDING, "device1", "data1", "barcode")
        event2 = Event("event2", EventType.SCAN, EventStatus.COMPLETED, "device2", "data2", "barcode")
        event3 = Event("event3", EventType.ERROR, EventStatus.FAILED, "device3", "data3", "barcode")
        
        event_manager.events = {
            "event1": event1,
            "event2": event2,
            "event3": event3
        }
        
        # Test getting pending events
        pending_events = event_manager.get_events_by_status(EventStatus.PENDING)
        assert len(pending_events) == 1
        assert event1 in pending_events
        
        # Test getting completed events
        completed_events = event_manager.get_events_by_status(EventStatus.COMPLETED)
        assert len(completed_events) == 1
        assert event2 in completed_events
        
        # Test getting failed events
        failed_events = event_manager.get_events_by_status(EventStatus.FAILED)
        assert len(failed_events) == 1
        assert event3 in failed_events
    
    def test_get_events_by_type(self, event_manager):
        """Test getting events by type"""
        # Create test events
        event1 = Event("event1", EventType.SCAN, EventStatus.PENDING, "device1", "data1", "barcode")
        event2 = Event("event2", EventType.SCAN, EventStatus.COMPLETED, "device2", "data2", "barcode")
        event3 = Event("event3", EventType.ERROR, EventStatus.FAILED, "device3", "data3", "barcode")
        
        event_manager.events = {
            "event1": event1,
            "event2": event2,
            "event3": event3
        }
        
        # Test getting scan events
        scan_events = event_manager.get_events_by_type(EventType.SCAN)
        assert len(scan_events) == 2
        assert event1 in scan_events
        assert event2 in scan_events
        
        # Test getting error events
        error_events = event_manager.get_events_by_type(EventType.ERROR)
        assert len(error_events) == 1
        assert event3 in error_events
    
    def test_get_events_by_device(self, event_manager):
        """Test getting events by device"""
        # Create test events
        event1 = Event("event1", EventType.SCAN, EventStatus.PENDING, "device1", "data1", "barcode")
        event2 = Event("event2", EventType.SCAN, EventStatus.COMPLETED, "device1", "data2", "barcode")
        event3 = Event("event3", EventType.ERROR, EventStatus.FAILED, "device2", "data3", "barcode")
        
        event_manager.events = {
            "event1": event1,
            "event2": event2,
            "event3": event3
        }
        
        # Test getting events for device1
        device1_events = event_manager.get_events_by_device("device1")
        assert len(device1_events) == 2
        assert event1 in device1_events
        assert event2 in device1_events
        
        # Test getting events for device2
        device2_events = event_manager.get_events_by_device("device2")
        assert len(device2_events) == 1
        assert event3 in device2_events
    
    def test_get_events_by_work_order(self, event_manager):
        """Test getting events by work order"""
        # Create test events
        event1 = Event("event1", EventType.SCAN, EventStatus.PENDING, "device1", "data1", "barcode", work_order_id="WO001")
        event2 = Event("event2", EventType.SCAN, EventStatus.COMPLETED, "device2", "data2", "barcode", work_order_id="WO001")
        event3 = Event("event3", EventType.ERROR, EventStatus.FAILED, "device3", "data3", "barcode", work_order_id="WO002")
        
        event_manager.events = {
            "event1": event1,
            "event2": event2,
            "event3": event3
        }
        
        # Test getting events for WO001
        wo001_events = event_manager.get_events_by_work_order("WO001")
        assert len(wo001_events) == 2
        assert event1 in wo001_events
        assert event2 in wo001_events
        
        # Test getting events for WO002
        wo002_events = event_manager.get_events_by_work_order("WO002")
        assert len(wo002_events) == 1
        assert event3 in wo002_events
    
    def test_get_event_statistics(self, event_manager):
        """Test getting event statistics"""
        # Create test events
        event1 = Event("event1", EventType.SCAN, EventStatus.PENDING, "device1", "data1", "barcode")
        event2 = Event("event2", EventType.SCAN, EventStatus.COMPLETED, "device2", "data2", "barcode")
        event3 = Event("event3", EventType.ERROR, EventStatus.FAILED, "device3", "data3", "barcode")
        
        event_manager.events = {
            "event1": event1,
            "event2": event2,
            "event3": event3
        }
        
        stats = event_manager.get_event_statistics()
        
        assert stats['total_events'] == 3
        assert stats['status_counts']['pending'] == 1
        assert stats['status_counts']['completed'] == 1
        assert stats['status_counts']['failed'] == 1
        assert stats['type_counts']['scan'] == 2
        assert stats['type_counts']['error'] == 1
    
    @pytest.mark.asyncio
    async def test_retry_failed_events(self, event_manager):
        """Test retrying failed events"""
        # Create a failed event
        event = Event("event1", EventType.SCAN, EventStatus.FAILED, "device1", "data1", "barcode")
        event.metadata = {'retry_count': 0}
        event_manager.events["event1"] = event
        
        # Mock the processing queue
        with patch.object(event_manager.processing_queue, 'put', new_callable=AsyncMock) as mock_put:
            await event_manager.retry_failed_events(max_retries=3)
            
            # Check that event status was reset
            assert event.status == EventStatus.PENDING
            assert event.error_message is None
            assert event.metadata['retry_count'] == 1
            
            # Check that event was added to queue
            mock_put.assert_called_once()
    
    def test_clear_old_events(self, event_manager):
        """Test clearing old events"""
        import time
        
        # Create events with different timestamps
        current_time = time.time()
        
        event1 = Event("event1", EventType.SCAN, EventStatus.COMPLETED, "device1", "data1", "barcode")
        event1.timestamp = current_time - 3600  # 1 hour ago
        
        event2 = Event("event2", EventType.SCAN, EventStatus.COMPLETED, "device2", "data2", "barcode")
        event2.timestamp = current_time - 7200  # 2 hours ago
        
        event3 = Event("event3", EventType.SCAN, EventStatus.PENDING, "device3", "data3", "barcode")
        event3.timestamp = current_time - 1800  # 30 minutes ago
        
        event_manager.events = {
            "event1": event1,
            "event2": event2,
            "event3": event3
        }
        
        # Clear events older than 1.5 hours
        event_manager.clear_old_events(max_age_hours=1.5)
        
        # Only event3 should remain (not completed and recent)
        assert len(event_manager.events) == 1
        assert "event3" in event_manager.events


if __name__ == "__main__":
    pytest.main([__file__])
