"""
Work Order Management for Odoo Integration

Handles work order operations including context setting, validation, and status updates.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import time

from ...iot_box.utils.logger import get_logger
from ...iot_box.utils.validators import validate_work_order

logger = get_logger(__name__)


class WorkOrderStatus(Enum):
    """Work order status enumeration"""
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    PROGRESS = "progress"
    TO_CLOSE = "to_close"
    DONE = "done"
    CANCEL = "cancel"


@dataclass
class WorkOrder:
    """Work order data structure"""
    id: str
    name: str
    product_id: int
    product_name: str
    status: WorkOrderStatus
    quantity: float
    bom_id: int
    date_planned_start: str
    date_planned_finished: str
    user_id: int
    user_name: str
    components: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.components is None:
            self.components = []


class WorkOrderManager:
    """Manages work order operations"""
    
    def __init__(self, odoo_client):
        self.odoo_client = odoo_client
        self.current_work_order: Optional[WorkOrder] = None
        self.work_order_cache: Dict[str, WorkOrder] = {}
        self.cache_ttl = 300  # 5 minutes
        self.cache_timestamps: Dict[str, float] = {}
    
    async def set_work_order_context(self, work_order_id: str, operator_id: str) -> Tuple[bool, str]:
        """Set current work order context"""
        try:
            # Validate work order ID format
            if not validate_work_order(work_order_id):
                return False, "Invalid work order ID format"
            
            # Get work order from Odoo
            work_order = await self.get_work_order(work_order_id)
            
            if not work_order:
                return False, f"Work order {work_order_id} not found"
            
            # Check if work order is in valid state
            if work_order.status not in [WorkOrderStatus.CONFIRMED, WorkOrderStatus.PROGRESS]:
                return False, f"Work order {work_order_id} is not in a valid state for production"
            
            # Set current work order
            self.current_work_order = work_order
            
            # Log the context change
            logger.info(f"Work order context set: {work_order_id} by operator {operator_id}")
            
            return True, f"Work order context set to {work_order_id}"
            
        except Exception as e:
            logger.error(f"Error setting work order context: {e}")
            return False, f"Error setting work order context: {str(e)}"
    
    async def get_work_order(self, work_order_id: str) -> Optional[WorkOrder]:
        """Get work order by ID"""
        try:
            # Check cache first
            if work_order_id in self.work_order_cache:
                cache_time = self.cache_timestamps.get(work_order_id, 0)
                if time.time() - cache_time < self.cache_ttl:
                    return self.work_order_cache[work_order_id]
            
            # Get from Odoo
            work_orders = self.odoo_client.execute_kw(
                'mrp.production',
                'search_read',
                [[('name', '=', work_order_id)]],
                {'fields': [
                    'name', 'product_id', 'product_qty', 'state', 'bom_id',
                    'date_planned_start', 'date_planned_finished', 'user_id'
                ]}
            )
            
            if not work_orders:
                return None
            
            wo_data = work_orders[0]
            
            # Get product information
            product = self.odoo_client.execute_kw(
                'product.product',
                'read',
                [wo_data['product_id'][0]],
                {'fields': ['name']}
            )[0]
            
            # Get user information
            user = self.odoo_client.execute_kw(
                'res.users',
                'read',
                [wo_data['user_id'][0]],
                {'fields': ['name']}
            )[0]
            
            # Get BOM components
            components = await self._get_bom_components(wo_data['bom_id'][0])
            
            # Create work order object
            work_order = WorkOrder(
                id=wo_data['name'],
                name=wo_data['name'],
                product_id=wo_data['product_id'][0],
                product_name=product['name'],
                status=WorkOrderStatus(wo_data['state']),
                quantity=wo_data['product_qty'],
                bom_id=wo_data['bom_id'][0],
                date_planned_start=wo_data['date_planned_start'],
                date_planned_finished=wo_data['date_planned_finished'],
                user_id=wo_data['user_id'][0],
                user_name=user['name'],
                components=components
            )
            
            # Cache the work order
            self.work_order_cache[work_order_id] = work_order
            self.cache_timestamps[work_order_id] = time.time()
            
            return work_order
            
        except Exception as e:
            logger.error(f"Error getting work order {work_order_id}: {e}")
            return None
    
    async def _get_bom_components(self, bom_id: int) -> List[Dict[str, Any]]:
        """Get BOM components for work order"""
        try:
            # Get BOM lines
            bom_lines = self.odoo_client.execute_kw(
                'mrp.bom.line',
                'search_read',
                [[('bom_id', '=', bom_id)]],
                {'fields': [
                    'product_id', 'product_qty', 'product_uom_id', 'operation_id'
                ]}
            )
            
            components = []
            for line in bom_lines:
                # Get product information
                product = self.odoo_client.execute_kw(
                    'product.product',
                    'read',
                    [line['product_id'][0]],
                    {'fields': ['name', 'default_code', 'barcode', 'type']}
                )[0]
                
                # Get UOM information
                uom = self.odoo_client.execute_kw(
                    'uom.uom',
                    'read',
                    [line['product_uom_id'][0]],
                    {'fields': ['name']}
                )[0]
                
                component = {
                    'product_id': line['product_id'][0],
                    'product_name': product['name'],
                    'default_code': product['default_code'],
                    'barcode': product['barcode'],
                    'quantity': line['product_qty'],
                    'uom_id': line['product_uom_id'][0],
                    'uom_name': uom['name'],
                    'operation_id': line['operation_id'][0] if line['operation_id'] else None,
                    'consumed_quantity': 0.0,
                    'remaining_quantity': line['product_qty']
                }
                
                components.append(component)
            
            return components
            
        except Exception as e:
            logger.error(f"Error getting BOM components: {e}")
            return []
    
    async def validate_component_for_work_order(self, component_barcode: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Validate if component is required for current work order"""
        try:
            if not self.current_work_order:
                return False, "No work order context set", None
            
            # Find component in work order BOM
            for component in self.current_work_order.components:
                if component['barcode'] == component_barcode:
                    # Check if component is already fully consumed
                    if component['remaining_quantity'] <= 0:
                        return False, f"Component {component_barcode} already fully consumed", None
                    
                    return True, f"Component {component_barcode} is valid for work order {self.current_work_order.id}", component
            
            return False, f"Component {component_barcode} not found in work order {self.current_work_order.id}", None
            
        except Exception as e:
            logger.error(f"Error validating component: {e}")
            return False, f"Error validating component: {str(e)}", None
    
    async def consume_component(self, component_barcode: str, quantity: float = 1.0) -> Tuple[bool, str]:
        """Consume component for current work order"""
        try:
            if not self.current_work_order:
                return False, "No work order context set"
            
            # Validate component
            is_valid, message, component = await self.validate_component_for_work_order(component_barcode)
            
            if not is_valid:
                return False, message
            
            # Check if quantity is available
            if quantity > component['remaining_quantity']:
                return False, f"Requested quantity {quantity} exceeds remaining quantity {component['remaining_quantity']}"
            
            # Update component consumption
            component['consumed_quantity'] += quantity
            component['remaining_quantity'] -= quantity
            
            # Create stock move in Odoo
            await self._create_stock_move(component, quantity)
            
            logger.info(f"Consumed {quantity} units of {component_barcode} for work order {self.current_work_order.id}")
            
            return True, f"Successfully consumed {quantity} units of {component_barcode}"
            
        except Exception as e:
            logger.error(f"Error consuming component: {e}")
            return False, f"Error consuming component: {str(e)}"
    
    async def _create_stock_move(self, component: Dict[str, Any], quantity: float):
        """Create stock move in Odoo for component consumption"""
        try:
            # Get work order ID
            work_order = self.odoo_client.execute_kw(
                'mrp.production',
                'search',
                [[('name', '=', self.current_work_order.id)]]
            )[0]
            
            # Create stock move
            move_data = {
                'name': f"Component consumption: {component['product_name']}",
                'product_id': component['product_id'],
                'product_uom_qty': quantity,
                'product_uom': component['uom_id'],
                'location_id': 8,  # Stock location
                'location_dest_id': 9,  # Production location
                'origin': self.current_work_order.id,
                'reference': f"WO: {self.current_work_order.id}",
                'state': 'done',
                'raw_material_production_id': work_order
            }
            
            move_id = self.odoo_client.execute_kw(
                'stock.move',
                'create',
                [move_data]
            )
            
            logger.debug(f"Created stock move {move_id} for component consumption")
            
        except Exception as e:
            logger.error(f"Error creating stock move: {e}")
            raise
    
    async def update_work_order_progress(self, progress_percentage: float) -> Tuple[bool, str]:
        """Update work order progress"""
        try:
            if not self.current_work_order:
                return False, "No work order context set"
            
            # Update work order in Odoo
            work_order_id = self.odoo_client.execute_kw(
                'mrp.production',
                'search',
                [[('name', '=', self.current_work_order.id)]]
            )[0]
            
            # Update progress
            self.odoo_client.execute_kw(
                'mrp.production',
                'write',
                [work_order_id],
                {'progress': progress_percentage}
            )
            
            logger.info(f"Updated work order {self.current_work_order.id} progress to {progress_percentage}%")
            
            return True, f"Work order progress updated to {progress_percentage}%"
            
        except Exception as e:
            logger.error(f"Error updating work order progress: {e}")
            return False, f"Error updating work order progress: {str(e)}"
    
    async def complete_work_order(self) -> Tuple[bool, str]:
        """Complete current work order"""
        try:
            if not self.current_work_order:
                return False, "No work order context set"
            
            # Get work order ID
            work_order_id = self.odoo_client.execute_kw(
                'mrp.production',
                'search',
                [[('name', '=', self.current_work_order.id)]]
            )[0]
            
            # Mark work order as done
            self.odoo_client.execute_kw(
                'mrp.production',
                'write',
                [work_order_id],
                {'state': 'done'}
            )
            
            # Clear current work order context
            self.current_work_order = None
            
            logger.info(f"Completed work order {self.current_work_order.id}")
            
            return True, f"Work order {self.current_work_order.id} completed successfully"
            
        except Exception as e:
            logger.error(f"Error completing work order: {e}")
            return False, f"Error completing work order: {str(e)}"
    
    async def get_work_order_status(self) -> Dict[str, Any]:
        """Get current work order status"""
        if not self.current_work_order:
            return {
                'has_context': False,
                'work_order_id': None,
                'status': None
            }
        
        return {
            'has_context': True,
            'work_order_id': self.current_work_order.id,
            'product_name': self.current_work_order.product_name,
            'status': self.current_work_order.status.value,
            'quantity': self.current_work_order.quantity,
            'components_count': len(self.current_work_order.components),
            'components_consumed': sum(1 for c in self.current_work_order.components if c['consumed_quantity'] > 0),
            'progress_percentage': self._calculate_progress()
        }
    
    def _calculate_progress(self) -> float:
        """Calculate work order progress based on component consumption"""
        if not self.current_work_order or not self.current_work_order.components:
            return 0.0
        
        total_components = len(self.current_work_order.components)
        consumed_components = sum(1 for c in self.current_work_order.components if c['remaining_quantity'] <= 0)
        
        return (consumed_components / total_components) * 100
    
    def clear_work_order_context(self):
        """Clear current work order context"""
        self.current_work_order = None
        logger.info("Work order context cleared")
    
    def get_work_order_summary(self) -> Dict[str, Any]:
        """Get work order summary for display"""
        if not self.current_work_order:
            return {
                'work_order_id': 'None',
                'product_name': 'No work order selected',
                'status': 'No context',
                'progress': 0,
                'components': []
            }
        
        return {
            'work_order_id': self.current_work_order.id,
            'product_name': self.current_work_order.product_name,
            'status': self.current_work_order.status.value,
            'progress': self._calculate_progress(),
            'components': [
                {
                    'name': c['product_name'],
                    'barcode': c['barcode'],
                    'required': c['quantity'],
                    'consumed': c['consumed_quantity'],
                    'remaining': c['remaining_quantity'],
                    'status': 'Complete' if c['remaining_quantity'] <= 0 else 'In Progress'
                }
                for c in self.current_work_order.components
            ]
        }
