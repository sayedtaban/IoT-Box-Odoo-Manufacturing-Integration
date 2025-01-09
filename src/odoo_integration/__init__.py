"""
Odoo Integration Module

This module provides integration with Odoo Manufacturing for work order management,
component tracking, and traceability.
"""

__version__ = "1.0.0"
__author__ = "IoT Box Team"

from .models.work_order import WorkOrderManager
from .models.component import ComponentManager
from .models.traceability import TraceabilityManager
from .services.bom_service import BOMService
from .services.validation_service import ValidationService
from .services.sync_service import SyncService

__all__ = [
    "WorkOrderManager",
    "ComponentManager", 
    "TraceabilityManager",
    "BOMService",
    "ValidationService",
    "SyncService"
]
