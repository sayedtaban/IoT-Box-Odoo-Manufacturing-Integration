"""
Logging utilities for IoT Box

Provides centralized logging configuration and utilities.
"""

import logging
import sys
from pathlib import Path
from typing import Optional
from loguru import logger as loguru_logger
import yaml


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for the given name"""
    return logging.getLogger(name)


def setup_logging(config_path: str = "config/config.yaml", 
                  log_level: str = "INFO",
                  log_file: Optional[str] = None):
    """Setup logging configuration"""
    
    try:
        # Load configuration
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
        
        logging_config = config.get('logging', {})
        log_level = logging_config.get('level', log_level)
        log_file = logging_config.get('file', log_file)
        
    except FileNotFoundError:
        # Use default configuration if file not found
        pass
    except Exception as e:
        print(f"Error loading logging config: {e}")
    
    # Configure loguru
    loguru_logger.remove()  # Remove default handler
    
    # Console handler
    loguru_logger.add(
        sys.stdout,
        level=log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        colorize=True
    )
    
    # File handler
    if log_file:
        log_file_path = Path(log_file)
        log_file_path.parent.mkdir(parents=True, exist_ok=True)
        
        loguru_logger.add(
            log_file,
            level=log_level,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            rotation="10 MB",
            retention="7 days",
            compression="zip"
        )
    
    # Configure standard logging to use loguru
    class InterceptHandler(logging.Handler):
        def emit(self, record):
            try:
                level = loguru_logger.level(record.levelname).name
            except ValueError:
                level = record.levelno
            
            frame, depth = sys._getframe(6), 6
            while frame and frame.f_code.co_filename == logging.__file__:
                frame = frame.f_back
                depth += 1
            
            loguru_logger.opt(depth=depth, exception=record.exc_info).log(
                level, record.getMessage()
            )
    
    # Replace all existing handlers
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    
    # Set specific logger levels
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    
    return loguru_logger


def get_audit_logger():
    """Get audit logger for security events"""
    audit_logger = logging.getLogger("audit")
    audit_logger.setLevel(logging.INFO)
    
    # Add file handler for audit logs
    audit_file = Path("logs/audit.log")
    audit_file.parent.mkdir(parents=True, exist_ok=True)
    
    handler = logging.FileHandler(audit_file)
    handler.setLevel(logging.INFO)
    
    formatter = logging.Formatter(
        "%(asctime)s - AUDIT - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)
    
    audit_logger.addHandler(handler)
    
    return audit_logger


def log_security_event(event_type: str, 
                      username: Optional[str] = None,
                      device_id: Optional[str] = None,
                      ip_address: Optional[str] = None,
                      details: Optional[dict] = None):
    """Log a security event"""
    audit_logger = get_audit_logger()
    
    message = f"SECURITY_EVENT: {event_type}"
    if username:
        message += f" | User: {username}"
    if device_id:
        message += f" | Device: {device_id}"
    if ip_address:
        message += f" | IP: {ip_address}"
    if details:
        message += f" | Details: {details}"
    
    audit_logger.info(message)


def log_scan_event(device_id: str, 
                  scan_data: str, 
                  scan_type: str,
                  work_order_id: Optional[str] = None,
                  status: str = "success"):
    """Log a scan event"""
    logger = get_logger("scan_events")
    
    message = f"SCAN_EVENT: {scan_type} | Device: {device_id} | Data: {scan_data}"
    if work_order_id:
        message += f" | WorkOrder: {work_order_id}"
    message += f" | Status: {status}"
    
    logger.info(message)


def log_odoo_event(event_type: str,
                  work_order_id: Optional[str] = None,
                  component_id: Optional[str] = None,
                  status: str = "success",
                  error_message: Optional[str] = None):
    """Log an Odoo integration event"""
    logger = get_logger("odoo_events")
    
    message = f"ODOO_EVENT: {event_type}"
    if work_order_id:
        message += f" | WorkOrder: {work_order_id}"
    if component_id:
        message += f" | Component: {component_id}"
    message += f" | Status: {status}"
    if error_message:
        message += f" | Error: {error_message}"
    
    logger.info(message)
