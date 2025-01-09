"""
Traceability Management for Odoo Integration

Handles audit trails, scan logging, and compliance tracking.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import time
import json

from ...iot_box.utils.logger import get_logger
from ...iot_box.utils.helpers import generate_id, get_current_timestamp

logger = get_logger(__name__)


class TraceabilityEventType(Enum):
    """Traceability event type enumeration"""
    SCAN = "scan"
    COMPONENT_CONSUMED = "component_consumed"
    WORK_ORDER_START = "work_order_start"
    WORK_ORDER_COMPLETE = "work_order_complete"
    QUALITY_CHECK = "quality_check"
    ERROR = "error"
    ALERT = "alert"


class TraceabilityStatus(Enum):
    """Traceability status enumeration"""
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    INFO = "info"


@dataclass
class TraceabilityRecord:
    """Traceability record data structure"""
    id: str
    event_type: TraceabilityEventType
    status: TraceabilityStatus
    device_id: str
    scan_data: str
    scan_type: str
    work_order_id: Optional[str] = None
    component_id: Optional[int] = None
    component_name: Optional[str] = None
    operator_id: Optional[str] = None
    operator_name: Optional[str] = None
    timestamp: float = 0.0
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = get_current_timestamp()
        if self.metadata is None:
            self.metadata = {}


class TraceabilityManager:
    """Manages traceability and audit logging"""
    
    def __init__(self, odoo_client):
        self.odoo_client = odoo_client
        self.records: List[TraceabilityRecord] = []
        self.max_memory_records = 1000
        self.batch_size = 100
        self.sync_interval = 60  # seconds
        self.last_sync = 0.0
    
    async def log_scan_event(self, 
                           device_id: str,
                           scan_data: str,
                           scan_type: str,
                           work_order_id: Optional[str] = None,
                           component_id: Optional[int] = None,
                           component_name: Optional[str] = None,
                           operator_id: Optional[str] = None,
                           operator_name: Optional[str] = None,
                           status: TraceabilityStatus = TraceabilityStatus.SUCCESS,
                           error_message: Optional[str] = None,
                           metadata: Optional[Dict[str, Any]] = None) -> str:
        """Log a scan event"""
        try:
            record_id = generate_id("trace")
            
            record = TraceabilityRecord(
                id=record_id,
                event_type=TraceabilityEventType.SCAN,
                status=status,
                device_id=device_id,
                scan_data=scan_data,
                scan_type=scan_type,
                work_order_id=work_order_id,
                component_id=component_id,
                component_name=component_name,
                operator_id=operator_id,
                operator_name=operator_name,
                error_message=error_message,
                metadata=metadata or {}
            )
            
            # Add to memory records
            self.records.append(record)
            
            # Trim memory records if needed
            if len(self.records) > self.max_memory_records:
                self.records = self.records[-self.max_memory_records:]
            
            # Log to file
            logger.info(f"TRACEABILITY: {record.event_type.value} | Device: {device_id} | Data: {scan_data} | Status: {status.value}")
            
            # Sync to Odoo if needed
            await self._sync_if_needed()
            
            return record_id
            
        except Exception as e:
            logger.error(f"Error logging scan event: {e}")
            return ""
    
    async def log_component_consumption(self,
                                      work_order_id: str,
                                      component_id: int,
                                      component_name: str,
                                      quantity: float,
                                      operator_id: Optional[str] = None,
                                      operator_name: Optional[str] = None,
                                      metadata: Optional[Dict[str, Any]] = None) -> str:
        """Log component consumption event"""
        try:
            record_id = generate_id("trace")
            
            record = TraceabilityRecord(
                id=record_id,
                event_type=TraceabilityEventType.COMPONENT_CONSUMED,
                status=TraceabilityStatus.SUCCESS,
                device_id="system",
                scan_data=f"Consumed {quantity} units of {component_name}",
                scan_type="consumption",
                work_order_id=work_order_id,
                component_id=component_id,
                component_name=component_name,
                operator_id=operator_id,
                operator_name=operator_name,
                metadata={
                    'quantity': quantity,
                    **(metadata or {})
                }
            )
            
            self.records.append(record)
            
            # Log to file
            logger.info(f"TRACEABILITY: {record.event_type.value} | WorkOrder: {work_order_id} | Component: {component_name} | Quantity: {quantity}")
            
            # Sync to Odoo
            await self._sync_if_needed()
            
            return record_id
            
        except Exception as e:
            logger.error(f"Error logging component consumption: {e}")
            return ""
    
    async def log_work_order_event(self,
                                 event_type: TraceabilityEventType,
                                 work_order_id: str,
                                 operator_id: Optional[str] = None,
                                 operator_name: Optional[str] = None,
                                 metadata: Optional[Dict[str, Any]] = None) -> str:
        """Log work order event"""
        try:
            record_id = generate_id("trace")
            
            record = TraceabilityRecord(
                id=record_id,
                event_type=event_type,
                status=TraceabilityStatus.SUCCESS,
                device_id="system",
                scan_data=f"Work order {event_type.value}: {work_order_id}",
                scan_type="work_order",
                work_order_id=work_order_id,
                operator_id=operator_id,
                operator_name=operator_name,
                metadata=metadata or {}
            )
            
            self.records.append(record)
            
            # Log to file
            logger.info(f"TRACEABILITY: {record.event_type.value} | WorkOrder: {work_order_id}")
            
            # Sync to Odoo
            await self._sync_if_needed()
            
            return record_id
            
        except Exception as e:
            logger.error(f"Error logging work order event: {e}")
            return ""
    
    async def log_error_event(self,
                            device_id: str,
                            error_message: str,
                            work_order_id: Optional[str] = None,
                            operator_id: Optional[str] = None,
                            metadata: Optional[Dict[str, Any]] = None) -> str:
        """Log error event"""
        try:
            record_id = generate_id("trace")
            
            record = TraceabilityRecord(
                id=record_id,
                event_type=TraceabilityEventType.ERROR,
                status=TraceabilityStatus.ERROR,
                device_id=device_id,
                scan_data=error_message,
                scan_type="error",
                work_order_id=work_order_id,
                operator_id=operator_id,
                error_message=error_message,
                metadata=metadata or {}
            )
            
            self.records.append(record)
            
            # Log to file
            logger.error(f"TRACEABILITY: {record.event_type.value} | Device: {device_id} | Error: {error_message}")
            
            # Sync to Odoo
            await self._sync_if_needed()
            
            return record_id
            
        except Exception as e:
            logger.error(f"Error logging error event: {e}")
            return ""
    
    async def _sync_if_needed(self):
        """Sync records to Odoo if needed"""
        current_time = get_current_timestamp()
        
        if (current_time - self.last_sync > self.sync_interval or 
            len(self.records) >= self.batch_size):
            await self.sync_to_odoo()
    
    async def sync_to_odoo(self) -> Tuple[bool, str]:
        """Sync traceability records to Odoo"""
        try:
            if not self.records:
                return True, "No records to sync"
            
            # Get records to sync
            records_to_sync = self.records.copy()
            self.records.clear()
            
            # Create traceability records in Odoo
            for record in records_to_sync:
                await self._create_odoo_traceability_record(record)
            
            self.last_sync = get_current_timestamp()
            
            logger.info(f"Synced {len(records_to_sync)} traceability records to Odoo")
            return True, f"Synced {len(records_to_sync)} records successfully"
            
        except Exception as e:
            logger.error(f"Error syncing traceability records: {e}")
            return False, f"Error syncing records: {str(e)}"
    
    async def _create_odoo_traceability_record(self, record: TraceabilityRecord):
        """Create traceability record in Odoo"""
        try:
            # Check if traceability model exists
            try:
                self.odoo_client.execute_kw(
                    'iot.traceability',
                    'create',
                    [{
                        'scan_id': record.id,
                        'device_id': record.device_id,
                        'scan_data': record.scan_data,
                        'scan_type': record.scan_type,
                        'work_order_id': record.work_order_id,
                        'component_id': record.component_id,
                        'component_name': record.component_name,
                        'operator_id': record.operator_id,
                        'operator_name': record.operator_name,
                        'timestamp': record.timestamp,
                        'event_type': record.event_type.value,
                        'status': record.status.value,
                        'error_message': record.error_message,
                        'metadata': json.dumps(record.metadata) if record.metadata else None
                    }]
                )
            except Exception as e:
                # If custom model doesn't exist, log to standard log
                logger.warning(f"Custom traceability model not available, logging to standard log: {e}")
                
                # Create a log entry in the system
                self.odoo_client.execute_kw(
                    'mail.message',
                    'create',
                    [{
                        'model': 'mrp.production',
                        'res_id': 0,
                        'message_type': 'notification',
                        'subject': f"IoT Traceability: {record.event_type.value}",
                        'body': f"""
                        <p><strong>Device:</strong> {record.device_id}</p>
                        <p><strong>Scan Data:</strong> {record.scan_data}</p>
                        <p><strong>Scan Type:</strong> {record.scan_type}</p>
                        <p><strong>Work Order:</strong> {record.work_order_id or 'N/A'}</p>
                        <p><strong>Component:</strong> {record.component_name or 'N/A'}</p>
                        <p><strong>Operator:</strong> {record.operator_name or 'N/A'}</p>
                        <p><strong>Status:</strong> {record.status.value}</p>
                        <p><strong>Timestamp:</strong> {record.timestamp}</p>
                        {f'<p><strong>Error:</strong> {record.error_message}</p>' if record.error_message else ''}
                        """,
                        'date': record.timestamp
                    }]
                )
            
        except Exception as e:
            logger.error(f"Error creating Odoo traceability record: {e}")
            raise
    
    async def get_traceability_records(self,
                                     work_order_id: Optional[str] = None,
                                     component_id: Optional[int] = None,
                                     device_id: Optional[str] = None,
                                     start_time: Optional[float] = None,
                                     end_time: Optional[float] = None,
                                     event_type: Optional[TraceabilityEventType] = None,
                                     limit: int = 100) -> List[TraceabilityRecord]:
        """Get traceability records with filters"""
        try:
            # Filter records
            filtered_records = self.records.copy()
            
            if work_order_id:
                filtered_records = [r for r in filtered_records if r.work_order_id == work_order_id]
            
            if component_id:
                filtered_records = [r for r in filtered_records if r.component_id == component_id]
            
            if device_id:
                filtered_records = [r for r in filtered_records if r.device_id == device_id]
            
            if start_time:
                filtered_records = [r for r in filtered_records if r.timestamp >= start_time]
            
            if end_time:
                filtered_records = [r for r in filtered_records if r.timestamp <= end_time]
            
            if event_type:
                filtered_records = [r for r in filtered_records if r.event_type == event_type]
            
            # Sort by timestamp (newest first)
            filtered_records.sort(key=lambda x: x.timestamp, reverse=True)
            
            # Apply limit
            return filtered_records[:limit]
            
        except Exception as e:
            logger.error(f"Error getting traceability records: {e}")
            return []
    
    async def get_work_order_traceability(self, work_order_id: str) -> Dict[str, Any]:
        """Get complete traceability for a work order"""
        try:
            records = await self.get_traceability_records(work_order_id=work_order_id)
            
            # Group by event type
            events_by_type = {}
            for record in records:
                event_type = record.event_type.value
                if event_type not in events_by_type:
                    events_by_type[event_type] = []
                events_by_type[event_type].append(record)
            
            # Calculate statistics
            total_events = len(records)
            error_events = len([r for r in records if r.status == TraceabilityStatus.ERROR])
            success_events = len([r for r in records if r.status == TraceabilityStatus.SUCCESS])
            
            # Get component consumption summary
            component_consumption = {}
            for record in records:
                if record.event_type == TraceabilityEventType.COMPONENT_CONSUMED:
                    component_name = record.component_name or "Unknown"
                    if component_name not in component_consumption:
                        component_consumption[component_name] = {
                            'quantity': 0,
                            'events': 0
                        }
                    component_consumption[component_name]['quantity'] += record.metadata.get('quantity', 0)
                    component_consumption[component_name]['events'] += 1
            
            return {
                'work_order_id': work_order_id,
                'total_events': total_events,
                'error_events': error_events,
                'success_events': success_events,
                'events_by_type': events_by_type,
                'component_consumption': component_consumption,
                'first_event': records[-1].timestamp if records else None,
                'last_event': records[0].timestamp if records else None
            }
            
        except Exception as e:
            logger.error(f"Error getting work order traceability: {e}")
            return {
                'work_order_id': work_order_id,
                'total_events': 0,
                'error_events': 0,
                'success_events': 0,
                'events_by_type': {},
                'component_consumption': {},
                'first_event': None,
                'last_event': None
            }
    
    def get_traceability_statistics(self) -> Dict[str, Any]:
        """Get traceability statistics"""
        total_records = len(self.records)
        
        if not total_records:
            return {
                'total_records': 0,
                'records_by_type': {},
                'records_by_status': {},
                'memory_usage': 0
            }
        
        # Count by event type
        records_by_type = {}
        for record in self.records:
            event_type = record.event_type.value
            records_by_type[event_type] = records_by_type.get(event_type, 0) + 1
        
        # Count by status
        records_by_status = {}
        for record in self.records:
            status = record.status.value
            records_by_status[status] = records_by_status.get(status, 0) + 1
        
        return {
            'total_records': total_records,
            'records_by_type': records_by_type,
            'records_by_status': records_by_status,
            'memory_usage': total_records * 1024,  # Approximate memory usage
            'last_sync': self.last_sync,
            'sync_interval': self.sync_interval
        }
    
    def export_traceability_data(self, 
                               start_time: Optional[float] = None,
                               end_time: Optional[float] = None) -> List[Dict[str, Any]]:
        """Export traceability data for reporting"""
        try:
            records = await self.get_traceability_records(
                start_time=start_time,
                end_time=end_time,
                limit=10000  # Large limit for export
            )
            
            # Convert to dictionary format
            export_data = []
            for record in records:
                record_dict = asdict(record)
                record_dict['event_type'] = record.event_type.value
                record_dict['status'] = record.status.value
                export_data.append(record_dict)
            
            return export_data
            
        except Exception as e:
            logger.error(f"Error exporting traceability data: {e}")
            return []
