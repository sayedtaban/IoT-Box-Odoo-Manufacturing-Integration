"""
Event Manager for IoT Box

Handles event processing, validation, and routing to Odoo integration.
"""

import asyncio
import logging
import time
import uuid
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import json

from ..utils.logger import get_logger
from ..utils.validators import validate_scan_data, validate_work_order

logger = get_logger(__name__)


class EventType(Enum):
    """Event type enumeration"""
    SCAN = "scan"
    WORK_ORDER_SET = "work_order_set"
    COMPONENT_CONSUMED = "component_consumed"
    ERROR = "error"
    ALERT = "alert"


class EventStatus(Enum):
    """Event status enumeration"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Event:
    """Event data structure"""
    id: str
    type: EventType
    status: EventStatus
    device_id: str
    scan_data: str
    scan_type: str
    work_order_id: Optional[str] = None
    component_id: Optional[str] = None
    operator_id: Optional[str] = None
    timestamp: float = 0.0
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()
        if self.metadata is None:
            self.metadata = {}


class EventManager:
    """Manages event processing and routing"""
    
    def __init__(self):
        self.events: Dict[str, Event] = {}
        self.event_handlers: Dict[EventType, List[Callable]] = {}
        self.running = False
        self.processing_queue = asyncio.Queue()
        self.max_queue_size = 1000
        self.processing_workers = 4
        
    async def start(self):
        """Start the event manager"""
        self.running = True
        logger.info("Starting event manager")
        
        # Start processing workers
        for i in range(self.processing_workers):
            asyncio.create_task(self._event_processor(f"worker-{i}"))
    
    async def stop(self):
        """Stop the event manager"""
        self.running = False
        logger.info("Stopping event manager")
        
        # Wait for queue to empty
        await self.processing_queue.join()
    
    def register_handler(self, event_type: EventType, handler: Callable):
        """Register an event handler"""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        
        self.event_handlers[event_type].append(handler)
        logger.info(f"Registered handler for event type: {event_type}")
    
    async def create_event(self, 
                          event_type: EventType,
                          device_id: str,
                          scan_data: str,
                          scan_type: str,
                          work_order_id: Optional[str] = None,
                          component_id: Optional[str] = None,
                          operator_id: Optional[str] = None,
                          metadata: Optional[Dict[str, Any]] = None) -> str:
        """Create a new event"""
        
        event_id = str(uuid.uuid4())
        
        event = Event(
            id=event_id,
            type=event_type,
            status=EventStatus.PENDING,
            device_id=device_id,
            scan_data=scan_data,
            scan_type=scan_type,
            work_order_id=work_order_id,
            component_id=component_id,
            operator_id=operator_id,
            metadata=metadata or {}
        )
        
        self.events[event_id] = event
        
        # Add to processing queue
        try:
            await self.processing_queue.put(event)
            logger.debug(f"Created event {event_id} of type {event_type}")
        except asyncio.QueueFull:
            logger.error("Event processing queue is full")
            event.status = EventStatus.FAILED
            event.error_message = "Processing queue full"
        
        return event_id
    
    async def _event_processor(self, worker_name: str):
        """Event processing worker"""
        logger.info(f"Started event processor: {worker_name}")
        
        while self.running:
            try:
                # Get event from queue
                event = await asyncio.wait_for(
                    self.processing_queue.get(), 
                    timeout=1.0
                )
                
                await self._process_event(event)
                self.processing_queue.task_done()
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error in event processor {worker_name}: {e}")
    
    async def _process_event(self, event: Event):
        """Process a single event"""
        try:
            event.status = EventStatus.PROCESSING
            logger.debug(f"Processing event {event.id} of type {event.type}")
            
            # Validate event data
            if not await self._validate_event(event):
                event.status = EventStatus.FAILED
                event.error_message = "Event validation failed"
                return
            
            # Route to appropriate handlers
            handlers = self.event_handlers.get(event.type, [])
            
            if not handlers:
                logger.warning(f"No handlers registered for event type: {event.type}")
                event.status = EventStatus.COMPLETED
                return
            
            # Execute handlers
            for handler in handlers:
                try:
                    await handler(event)
                except Exception as e:
                    logger.error(f"Error in event handler: {e}")
                    event.error_message = str(e)
                    event.status = EventStatus.FAILED
                    return
            
            event.status = EventStatus.COMPLETED
            logger.debug(f"Successfully processed event {event.id}")
            
        except Exception as e:
            logger.error(f"Error processing event {event.id}: {e}")
            event.status = EventStatus.FAILED
            event.error_message = str(e)
    
    async def _validate_event(self, event: Event) -> bool:
        """Validate event data"""
        try:
            # Validate scan data
            if not validate_scan_data(event.scan_data, event.scan_type):
                logger.warning(f"Invalid scan data for event {event.id}")
                return False
            
            # Validate work order if present
            if event.work_order_id and not validate_work_order(event.work_order_id):
                logger.warning(f"Invalid work order for event {event.id}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating event {event.id}: {e}")
            return False
    
    def get_event(self, event_id: str) -> Optional[Event]:
        """Get event by ID"""
        return self.events.get(event_id)
    
    def get_events_by_status(self, status: EventStatus) -> List[Event]:
        """Get events by status"""
        return [event for event in self.events.values() 
                if event.status == status]
    
    def get_events_by_type(self, event_type: EventType) -> List[Event]:
        """Get events by type"""
        return [event for event in self.events.values() 
                if event.type == event_type]
    
    def get_events_by_device(self, device_id: str) -> List[Event]:
        """Get events by device"""
        return [event for event in self.events.values() 
                if event.device_id == device_id]
    
    def get_events_by_work_order(self, work_order_id: str) -> List[Event]:
        """Get events by work order"""
        return [event for event in self.events.values() 
                if event.work_order_id == work_order_id]
    
    def get_event_statistics(self) -> Dict[str, Any]:
        """Get event processing statistics"""
        total_events = len(self.events)
        
        status_counts = {}
        for status in EventStatus:
            status_counts[status.value] = len(self.get_events_by_status(status))
        
        type_counts = {}
        for event_type in EventType:
            type_counts[event_type.value] = len(self.get_events_by_type(event_type))
        
        return {
            "total_events": total_events,
            "queue_size": self.processing_queue.qsize(),
            "status_counts": status_counts,
            "type_counts": type_counts,
            "processing_workers": self.processing_workers
        }
    
    async def retry_failed_events(self, max_retries: int = 3):
        """Retry failed events"""
        failed_events = self.get_events_by_status(EventStatus.FAILED)
        
        for event in failed_events:
            retry_count = event.metadata.get('retry_count', 0)
            
            if retry_count < max_retries:
                event.metadata['retry_count'] = retry_count + 1
                event.status = EventStatus.PENDING
                event.error_message = None
                
                try:
                    await self.processing_queue.put(event)
                    logger.info(f"Retrying failed event {event.id}")
                except asyncio.QueueFull:
                    logger.error("Cannot retry event - queue is full")
    
    def clear_old_events(self, max_age_hours: int = 24):
        """Clear old completed events"""
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        
        events_to_remove = []
        
        for event_id, event in self.events.items():
            if (event.status == EventStatus.COMPLETED and 
                current_time - event.timestamp > max_age_seconds):
                events_to_remove.append(event_id)
        
        for event_id in events_to_remove:
            del self.events[event_id]
        
        if events_to_remove:
            logger.info(f"Cleared {len(events_to_remove)} old events")
    
    def export_events(self, 
                     start_time: Optional[float] = None,
                     end_time: Optional[float] = None,
                     event_types: Optional[List[EventType]] = None) -> List[Dict[str, Any]]:
        """Export events to JSON format"""
        filtered_events = []
        
        for event in self.events.values():
            # Filter by time range
            if start_time and event.timestamp < start_time:
                continue
            if end_time and event.timestamp > end_time:
                continue
            
            # Filter by event type
            if event_types and event.type not in event_types:
                continue
            
            # Convert to dictionary
            event_dict = asdict(event)
            event_dict['type'] = event.type.value
            event_dict['status'] = event.status.value
            filtered_events.append(event_dict)
        
        return filtered_events
