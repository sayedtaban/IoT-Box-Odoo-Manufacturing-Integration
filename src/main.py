"""
Main IoT Box Application

Entry point for the IoT Box Odoo integration system.
"""

import asyncio
import logging
import signal
import sys
from pathlib import Path
from typing import Optional
import yaml
import argparse

from iot_box.core.device_manager import DeviceManager
from iot_box.core.event_manager import EventManager
from iot_box.core.buffer_manager import BufferManager
from iot_box.core.security_manager import SecurityManager
from iot_box.utils.logger import setup_logging, get_logger
from odoo_integration.services.sync_service import SyncService
from web_interface.app import create_app

logger = get_logger(__name__)


class IoTBoxApplication:
    """Main IoT Box application class"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        self.config_path = config_path
        self.config = {}
        self.running = False
        
        # Core managers
        self.device_manager: Optional[DeviceManager] = None
        self.event_manager: Optional[EventManager] = None
        self.buffer_manager: Optional[BufferManager] = None
        self.security_manager: Optional[SecurityManager] = None
        self.sync_service: Optional[SyncService] = None
        
        # Web application
        self.web_app = None
        
    async def initialize(self):
        """Initialize the application"""
        try:
            # Load configuration
            await self._load_config()
            
            # Setup logging
            setup_logging(self.config_path, self.config.get('logging', {}).get('level', 'INFO'))
            
            logger.info("Initializing IoT Box Application")
            
            # Initialize core managers
            await self._initialize_managers()
            
            # Initialize web interface
            await self._initialize_web_interface()
            
            # Setup event handlers
            await self._setup_event_handlers()
            
            logger.info("IoT Box Application initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing application: {e}")
            raise
    
    async def _load_config(self):
        """Load configuration from YAML file"""
        try:
            with open(self.config_path, 'r') as file:
                self.config = yaml.safe_load(file)
            
            logger.info(f"Loaded configuration from {self.config_path}")
            
        except FileNotFoundError:
            logger.error(f"Configuration file not found: {self.config_path}")
            raise
        except yaml.YAMLError as e:
            logger.error(f"Error parsing configuration file: {e}")
            raise
    
    async def _initialize_managers(self):
        """Initialize core managers"""
        try:
            # Initialize security manager
            security_config = self.config.get('iot_box', {}).get('security', {})
            self.security_manager = SecurityManager(
                secret_key=security_config.get('secret_key', 'default-secret-key'),
                encryption_key=security_config.get('encryption_key'),
                policy=None  # Use default policy for now
            )
            
            # Initialize device manager
            self.device_manager = DeviceManager()
            
            # Initialize event manager
            self.event_manager = EventManager()
            
            # Initialize buffer manager
            buffer_config = self.config.get('iot_box', {}).get('offline', {})
            self.buffer_manager = BufferManager(
                buffer_size=buffer_config.get('buffer_size', 1000),
                sync_interval=buffer_config.get('sync_interval', 60),
                max_retries=buffer_config.get('max_retries', 3)
            )
            
            # Initialize sync service
            odoo_config = self.config.get('odoo', {})
            self.sync_service = SyncService(odoo_config)
            
            logger.info("Core managers initialized")
            
        except Exception as e:
            logger.error(f"Error initializing managers: {e}")
            raise
    
    async def _initialize_web_interface(self):
        """Initialize web interface"""
        try:
            # Create Flask application
            self.web_app = create_app(
                device_manager=self.device_manager,
                event_manager=self.event_manager,
                buffer_manager=self.buffer_manager,
                security_manager=self.security_manager,
                sync_service=self.sync_service
            )
            
            logger.info("Web interface initialized")
            
        except Exception as e:
            logger.error(f"Error initializing web interface: {e}")
            raise
    
    async def _setup_event_handlers(self):
        """Setup event handlers"""
        try:
            # Register scan event handler
            self.event_manager.register_handler(
                self.event_manager.EventType.SCAN,
                self._handle_scan_event
            )
            
            # Register work order event handler
            self.event_manager.register_handler(
                self.event_manager.EventType.WORK_ORDER_SET,
                self._handle_work_order_event
            )
            
            # Register component consumption handler
            self.event_manager.register_handler(
                self.event_manager.EventType.COMPONENT_CONSUMED,
                self._handle_component_consumption_event
            )
            
            # Register error handler
            self.event_manager.register_handler(
                self.event_manager.EventType.ERROR,
                self._handle_error_event
            )
            
            logger.info("Event handlers registered")
            
        except Exception as e:
            logger.error(f"Error setting up event handlers: {e}")
            raise
    
    async def _handle_scan_event(self, event):
        """Handle scan events"""
        try:
            logger.info(f"Processing scan event: {event.scan_data}")
            
            # Validate component
            if self.sync_service:
                is_valid, message, component = await self.sync_service.validate_component(
                    event.scan_data, event.scan_type
                )
                
                if is_valid:
                    # Check if component is valid for current work order
                    if event.work_order_id:
                        work_order_valid, work_order_message = await self.sync_service.validate_component_for_work_order(
                            event.work_order_id, event.scan_data
                        )
                        
                        if work_order_valid:
                            # Consume component
                            success, consume_message = await self.sync_service.consume_component(
                                event.work_order_id, event.scan_data, 1.0
                            )
                            
                            if success:
                                logger.info(f"Component consumed successfully: {consume_message}")
                            else:
                                logger.warning(f"Failed to consume component: {consume_message}")
                        else:
                            logger.warning(f"Component not valid for work order: {work_order_message}")
                    else:
                        logger.warning("No work order context set")
                else:
                    logger.warning(f"Invalid component: {message}")
            
        except Exception as e:
            logger.error(f"Error handling scan event: {e}")
    
    async def _handle_work_order_event(self, event):
        """Handle work order events"""
        try:
            logger.info(f"Processing work order event: {event.work_order_id}")
            
            if self.sync_service:
                success, message = await self.sync_service.set_work_order_context(
                    event.work_order_id, event.operator_id or "unknown"
                )
                
                if success:
                    logger.info(f"Work order context set: {message}")
                else:
                    logger.warning(f"Failed to set work order context: {message}")
            
        except Exception as e:
            logger.error(f"Error handling work order event: {e}")
    
    async def _handle_component_consumption_event(self, event):
        """Handle component consumption events"""
        try:
            logger.info(f"Processing component consumption event: {event.component_id}")
            
            # Log traceability
            if self.sync_service and self.sync_service.traceability_manager:
                await self.sync_service.traceability_manager.log_component_consumption(
                    work_order_id=event.work_order_id or "unknown",
                    component_id=event.component_id or 0,
                    component_name=event.component_name or "unknown",
                    quantity=1.0,
                    operator_id=event.operator_id,
                    operator_name=event.operator_name
                )
            
        except Exception as e:
            logger.error(f"Error handling component consumption event: {e}")
    
    async def _handle_error_event(self, event):
        """Handle error events"""
        try:
            logger.error(f"Processing error event: {event.error_message}")
            
            # Log traceability
            if self.sync_service and self.sync_service.traceability_manager:
                await self.sync_service.traceability_manager.log_error_event(
                    device_id=event.device_id,
                    error_message=event.error_message or "Unknown error",
                    work_order_id=event.work_order_id,
                    operator_id=event.operator_id
                )
            
        except Exception as e:
            logger.error(f"Error handling error event: {e}")
    
    async def start(self):
        """Start the application"""
        try:
            logger.info("Starting IoT Box Application")
            self.running = True
            
            # Start core managers
            await self.device_manager.start()
            await self.event_manager.start()
            await self.buffer_manager.start()
            
            # Start sync service
            if self.sync_service:
                await self.sync_service.start()
            
            # Start web interface
            if self.web_app:
                import threading
                web_thread = threading.Thread(
                    target=lambda: self.web_app.run(
                        host=self.config.get('iot_box', {}).get('server', {}).get('host', '0.0.0.0'),
                        port=self.config.get('iot_box', {}).get('server', {}).get('port', 8080),
                        debug=False
                    )
                )
                web_thread.daemon = True
                web_thread.start()
            
            logger.info("IoT Box Application started successfully")
            
        except Exception as e:
            logger.error(f"Error starting application: {e}")
            raise
    
    async def stop(self):
        """Stop the application"""
        try:
            logger.info("Stopping IoT Box Application")
            self.running = False
            
            # Stop core managers
            if self.device_manager:
                await self.device_manager.stop()
            
            if self.event_manager:
                await self.event_manager.stop()
            
            if self.buffer_manager:
                await self.buffer_manager.stop()
            
            if self.sync_service:
                await self.sync_service.stop()
            
            logger.info("IoT Box Application stopped")
            
        except Exception as e:
            logger.error(f"Error stopping application: {e}")
    
    async def run(self):
        """Run the application"""
        try:
            await self.initialize()
            await self.start()
            
            # Keep running until interrupted
            while self.running:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        except Exception as e:
            logger.error(f"Application error: {e}")
        finally:
            await self.stop()


def setup_signal_handlers(app: IoTBoxApplication):
    """Setup signal handlers for graceful shutdown"""
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}")
        asyncio.create_task(app.stop())
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="IoT Box Odoo Integration")
    parser.add_argument("--config", "-c", default="config/config.yaml", help="Configuration file path")
    parser.add_argument("--debug", "-d", action="store_true", help="Enable debug mode")
    
    args = parser.parse_args()
    
    # Create application
    app = IoTBoxApplication(args.config)
    
    # Setup signal handlers
    setup_signal_handlers(app)
    
    # Run application
    await app.run()


if __name__ == "__main__":
    asyncio.run(main())
