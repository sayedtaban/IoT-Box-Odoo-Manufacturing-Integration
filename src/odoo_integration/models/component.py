"""
Component Management for Odoo Integration

Handles component tracking, validation, and inventory management.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import time

from ...iot_box.utils.logger import get_logger
from ...iot_box.utils.validators import validate_barcode, validate_rfid

logger = get_logger(__name__)


class ComponentType(Enum):
    """Component type enumeration"""
    RAW_MATERIAL = "raw_material"
    SEMI_FINISHED = "semi_finished"
    FINISHED_GOOD = "finished_good"
    TOOL = "tool"
    CONSUMABLE = "consumable"


@dataclass
class Component:
    """Component data structure"""
    id: int
    name: str
    default_code: str
    barcode: str
    type: ComponentType
    category_id: int
    category_name: str
    tracking: str
    uom_id: int
    uom_name: str
    cost: float
    weight: float
    volume: float
    active: bool = True
    last_scan: Optional[float] = None
    scan_count: int = 0


class ComponentManager:
    """Manages component operations"""
    
    def __init__(self, odoo_client):
        self.odoo_client = odoo_client
        self.component_cache: Dict[str, Component] = {}
        self.cache_ttl = 600  # 10 minutes
        self.cache_timestamps: Dict[str, float] = {}
    
    async def get_component_by_barcode(self, barcode: str) -> Optional[Component]:
        """Get component by barcode"""
        try:
            # Validate barcode format
            if not validate_barcode(barcode):
                logger.warning(f"Invalid barcode format: {barcode}")
                return None
            
            # Check cache first
            if barcode in self.component_cache:
                cache_time = self.cache_timestamps.get(barcode, 0)
                if time.time() - cache_time < self.cache_ttl:
                    return self.component_cache[barcode]
            
            # Search in Odoo
            products = self.odoo_client.execute_kw(
                'product.product',
                'search_read',
                [[('barcode', '=', barcode)]],
                {'fields': [
                    'name', 'default_code', 'barcode', 'type', 'categ_id',
                    'tracking', 'uom_id', 'standard_price', 'weight', 'volume', 'active'
                ]}
            )
            
            if not products:
                logger.warning(f"Component not found for barcode: {barcode}")
                return None
            
            product_data = products[0]
            
            # Get category information
            category = self.odoo_client.execute_kw(
                'product.category',
                'read',
                [product_data['categ_id'][0]],
                {'fields': ['name']}
            )[0]
            
            # Get UOM information
            uom = self.odoo_client.execute_kw(
                'uom.uom',
                'read',
                [product_data['uom_id'][0]],
                {'fields': ['name']}
            )[0]
            
            # Create component object
            component = Component(
                id=product_data['id'],
                name=product_data['name'],
                default_code=product_data['default_code'],
                barcode=product_data['barcode'],
                type=ComponentType(product_data['type']),
                category_id=product_data['categ_id'][0],
                category_name=category['name'],
                tracking=product_data['tracking'],
                uom_id=product_data['uom_id'][0],
                uom_name=uom['name'],
                cost=product_data['standard_price'],
                weight=product_data['weight'],
                volume=product_data['volume'],
                active=product_data['active']
            )
            
            # Cache the component
            self.component_cache[barcode] = component
            self.cache_timestamps[barcode] = time.time()
            
            logger.debug(f"Retrieved component: {component.name} ({barcode})")
            return component
            
        except Exception as e:
            logger.error(f"Error getting component by barcode {barcode}: {e}")
            return None
    
    async def get_component_by_rfid(self, rfid: str) -> Optional[Component]:
        """Get component by RFID tag"""
        try:
            # Validate RFID format
            if not validate_rfid(rfid):
                logger.warning(f"Invalid RFID format: {rfid}")
                return None
            
            # Search for RFID in product attributes or custom fields
            # This assumes RFID is stored in a custom field or attribute
            products = self.odoo_client.execute_kw(
                'product.product',
                'search_read',
                [[('x_rfid_tag', '=', rfid)]],  # Custom field for RFID
                {'fields': [
                    'name', 'default_code', 'barcode', 'type', 'categ_id',
                    'tracking', 'uom_id', 'standard_price', 'weight', 'volume', 'active'
                ]}
            )
            
            if not products:
                logger.warning(f"Component not found for RFID: {rfid}")
                return None
            
            product_data = products[0]
            
            # Get category information
            category = self.odoo_client.execute_kw(
                'product.category',
                'read',
                [product_data['categ_id'][0]],
                {'fields': ['name']}
            )[0]
            
            # Get UOM information
            uom = self.odoo_client.execute_kw(
                'uom.uom',
                'read',
                [product_data['uom_id'][0]],
                {'fields': ['name']}
            )[0]
            
            # Create component object
            component = Component(
                id=product_data['id'],
                name=product_data['name'],
                default_code=product_data['default_code'],
                barcode=product_data['barcode'],
                type=ComponentType(product_data['type']),
                category_id=product_data['categ_id'][0],
                category_name=category['name'],
                tracking=product_data['tracking'],
                uom_id=product_data['uom_id'][0],
                uom_name=uom['name'],
                cost=product_data['standard_price'],
                weight=product_data['weight'],
                volume=product_data['volume'],
                active=product_data['active']
            )
            
            # Cache the component
            self.component_cache[rfid] = component
            self.cache_timestamps[rfid] = time.time()
            
            logger.debug(f"Retrieved component by RFID: {component.name} ({rfid})")
            return component
            
        except Exception as e:
            logger.error(f"Error getting component by RFID {rfid}: {e}")
            return None
    
    async def validate_component(self, scan_data: str, scan_type: str) -> Tuple[bool, str, Optional[Component]]:
        """Validate component based on scan data and type"""
        try:
            if scan_type.lower() == 'barcode':
                component = await self.get_component_by_barcode(scan_data)
            elif scan_type.lower() == 'rfid':
                component = await self.get_component_by_rfid(scan_data)
            else:
                return False, f"Unsupported scan type: {scan_type}", None
            
            if not component:
                return False, f"Component not found for {scan_type}: {scan_data}", None
            
            if not component.active:
                return False, f"Component {component.name} is inactive", None
            
            # Update scan statistics
            component.last_scan = time.time()
            component.scan_count += 1
            
            return True, f"Component {component.name} validated successfully", component
            
        except Exception as e:
            logger.error(f"Error validating component: {e}")
            return False, f"Error validating component: {str(e)}", None
    
    async def get_component_inventory(self, component_id: int) -> Dict[str, Any]:
        """Get component inventory information"""
        try:
            # Get stock quant information
            quants = self.odoo_client.execute_kw(
                'stock.quant',
                'search_read',
                [[('product_id', '=', component_id)]],
                {'fields': ['quantity', 'location_id', 'lot_id', 'package_id']}
            )
            
            total_quantity = sum(quant['quantity'] for quant in quants)
            
            # Get location information
            locations = {}
            for quant in quants:
                location_id = quant['location_id'][0]
                if location_id not in locations:
                    location = self.odoo_client.execute_kw(
                        'stock.location',
                        'read',
                        [location_id],
                        {'fields': ['name', 'usage']}
                    )[0]
                    locations[location_id] = {
                        'name': location['name'],
                        'usage': location['usage'],
                        'quantity': 0
                    }
                locations[location_id]['quantity'] += quant['quantity']
            
            return {
                'component_id': component_id,
                'total_quantity': total_quantity,
                'locations': list(locations.values()),
                'quants_count': len(quants)
            }
            
        except Exception as e:
            logger.error(f"Error getting component inventory: {e}")
            return {
                'component_id': component_id,
                'total_quantity': 0,
                'locations': [],
                'quants_count': 0
            }
    
    async def update_component_tracking(self, component_id: int, tracking_type: str) -> Tuple[bool, str]:
        """Update component tracking type"""
        try:
            # Update product tracking
            self.odoo_client.execute_kw(
                'product.product',
                'write',
                [component_id],
                {'tracking': tracking_type}
            )
            
            logger.info(f"Updated component {component_id} tracking to {tracking_type}")
            return True, f"Component tracking updated to {tracking_type}"
            
        except Exception as e:
            logger.error(f"Error updating component tracking: {e}")
            return False, f"Error updating component tracking: {str(e)}"
    
    async def create_component(self, component_data: Dict[str, Any]) -> Tuple[bool, str, Optional[int]]:
        """Create a new component"""
        try:
            # Validate required fields
            required_fields = ['name', 'default_code', 'barcode', 'type']
            missing_fields = [field for field in required_fields if field not in component_data]
            
            if missing_fields:
                return False, f"Missing required fields: {missing_fields}", None
            
            # Create product
            product_id = self.odoo_client.execute_kw(
                'product.product',
                'create',
                [component_data]
            )
            
            logger.info(f"Created component: {component_data['name']} (ID: {product_id})")
            return True, f"Component created successfully", product_id
            
        except Exception as e:
            logger.error(f"Error creating component: {e}")
            return False, f"Error creating component: {str(e)}", None
    
    async def search_components(self, search_term: str, limit: int = 50) -> List[Component]:
        """Search components by name or code"""
        try:
            # Search products
            products = self.odoo_client.execute_kw(
                'product.product',
                'search_read',
                [[('name', 'ilike', search_term)]],
                {'fields': [
                    'name', 'default_code', 'barcode', 'type', 'categ_id',
                    'tracking', 'uom_id', 'standard_price', 'weight', 'volume', 'active'
                ], 'limit': limit}
            )
            
            components = []
            for product_data in products:
                # Get category information
                category = self.odoo_client.execute_kw(
                    'product.category',
                    'read',
                    [product_data['categ_id'][0]],
                    {'fields': ['name']}
                )[0]
                
                # Get UOM information
                uom = self.odoo_client.execute_kw(
                    'uom.uom',
                    'read',
                    [product_data['uom_id'][0]],
                    {'fields': ['name']}
                )[0]
                
                component = Component(
                    id=product_data['id'],
                    name=product_data['name'],
                    default_code=product_data['default_code'],
                    barcode=product_data['barcode'],
                    type=ComponentType(product_data['type']),
                    category_id=product_data['categ_id'][0],
                    category_name=category['name'],
                    tracking=product_data['tracking'],
                    uom_id=product_data['uom_id'][0],
                    uom_name=uom['name'],
                    cost=product_data['standard_price'],
                    weight=product_data['weight'],
                    volume=product_data['volume'],
                    active=product_data['active']
                )
                
                components.append(component)
            
            return components
            
        except Exception as e:
            logger.error(f"Error searching components: {e}")
            return []
    
    def get_component_statistics(self) -> Dict[str, Any]:
        """Get component statistics"""
        return {
            'cached_components': len(self.component_cache),
            'cache_ttl': self.cache_ttl,
            'component_types': [t.value for t in ComponentType]
        }
    
    def clear_component_cache(self):
        """Clear component cache"""
        self.component_cache.clear()
        self.cache_timestamps.clear()
        logger.info("Component cache cleared")
    
    def get_cached_component(self, identifier: str) -> Optional[Component]:
        """Get component from cache"""
        if identifier in self.component_cache:
            cache_time = self.cache_timestamps.get(identifier, 0)
            if time.time() - cache_time < self.cache_ttl:
                return self.component_cache[identifier]
        return None
