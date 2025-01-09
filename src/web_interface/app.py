"""
Web Interface for IoT Box

Flask-based web interface for monitoring and controlling the IoT Box system.
"""

import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from flask import Flask, render_template, jsonify, request, redirect, url_for, flash
from flask_cors import CORS
import asyncio
import threading

from ..iot_box.utils.logger import get_logger

logger = get_logger(__name__)


def create_app(device_manager=None, event_manager=None, buffer_manager=None, 
               security_manager=None, sync_service=None):
    """Create Flask application"""
    app = Flask(__name__)
    app.secret_key = 'iot-box-secret-key'  # Should be from config
    
    # Enable CORS
    CORS(app)
    
    # Store managers
    app.device_manager = device_manager
    app.event_manager = event_manager
    app.buffer_manager = buffer_manager
    app.security_manager = security_manager
    app.sync_service = sync_service
    
    # Register routes
    register_routes(app)
    
    return app


def register_routes(app):
    """Register Flask routes"""
    
    @app.route('/')
    def index():
        """Main dashboard"""
        return render_template('dashboard.html')
    
    @app.route('/api/status')
    def api_status():
        """Get system status"""
        try:
            status = {
                'system': 'running',
                'timestamp': datetime.now().isoformat(),
                'devices': {},
                'events': {},
                'buffer': {},
                'odoo': {}
            }
            
            # Device status
            if app.device_manager:
                status['devices'] = app.device_manager.get_device_status()
            
            # Event status
            if app.event_manager:
                status['events'] = app.event_manager.get_event_statistics()
            
            # Buffer status
            if app.buffer_manager:
                status['buffer'] = asyncio.run(app.buffer_manager.get_buffer_statistics())
            
            # Odoo status
            if app.sync_service:
                status['odoo'] = {
                    'connected': True,  # Should check actual connection
                    'work_order': asyncio.run(app.sync_service.get_work_order_status()) if hasattr(app.sync_service, 'get_work_order_status') else None
                }
            
            return jsonify(status)
            
        except Exception as e:
            logger.error(f"Error getting status: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/devices')
    def api_devices():
        """Get device information"""
        try:
            if not app.device_manager:
                return jsonify({'error': 'Device manager not available'}), 500
            
            devices = app.device_manager.get_device_status()
            return jsonify(devices)
            
        except Exception as e:
            logger.error(f"Error getting devices: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/scan', methods=['POST'])
    def api_scan():
        """Handle scan request"""
        try:
            data = request.get_json()
            
            if not data or 'device_id' not in data or 'scan_data' not in data:
                return jsonify({'error': 'Missing required fields'}), 400
            
            device_id = data['device_id']
            scan_data = data['scan_data']
            scan_type = data.get('scan_type', 'barcode')
            work_order_id = data.get('work_order_id')
            operator_id = data.get('operator_id')
            
            # Create scan event
            if app.event_manager:
                event_id = asyncio.run(app.event_manager.create_event(
                    event_type=app.event_manager.EventType.SCAN,
                    device_id=device_id,
                    scan_data=scan_data,
                    scan_type=scan_type,
                    work_order_id=work_order_id,
                    operator_id=operator_id
                ))
                
                return jsonify({
                    'success': True,
                    'event_id': event_id,
                    'message': 'Scan event created successfully'
                })
            else:
                return jsonify({'error': 'Event manager not available'}), 500
                
        except Exception as e:
            logger.error(f"Error handling scan: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/work-order/set-context', methods=['POST'])
    def api_set_work_order_context():
        """Set work order context"""
        try:
            data = request.get_json()
            
            if not data or 'work_order_id' not in data:
                return jsonify({'error': 'Missing work_order_id'}), 400
            
            work_order_id = data['work_order_id']
            operator_id = data.get('operator_id', 'unknown')
            
            # Create work order event
            if app.event_manager:
                event_id = asyncio.run(app.event_manager.create_event(
                    event_type=app.event_manager.EventType.WORK_ORDER_SET,
                    device_id='web_interface',
                    scan_data=work_order_id,
                    scan_type='work_order',
                    work_order_id=work_order_id,
                    operator_id=operator_id
                ))
                
                return jsonify({
                    'success': True,
                    'event_id': event_id,
                    'message': f'Work order context set to {work_order_id}'
                })
            else:
                return jsonify({'error': 'Event manager not available'}), 500
                
        except Exception as e:
            logger.error(f"Error setting work order context: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/traceability')
    def api_traceability():
        """Get traceability data"""
        try:
            work_order_id = request.args.get('work_order_id')
            limit = int(request.args.get('limit', 100))
            
            if app.sync_service and hasattr(app.sync_service, 'traceability_manager'):
                if work_order_id:
                    data = asyncio.run(app.sync_service.traceability_manager.get_work_order_traceability(work_order_id))
                else:
                    data = app.sync_service.traceability_manager.get_traceability_statistics()
                
                return jsonify(data)
            else:
                return jsonify({'error': 'Traceability manager not available'}), 500
                
        except Exception as e:
            logger.error(f"Error getting traceability data: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/buffer/sync', methods=['POST'])
    def api_sync_buffer():
        """Sync buffer to Odoo"""
        try:
            if not app.buffer_manager:
                return jsonify({'error': 'Buffer manager not available'}), 500
            
            success, message = asyncio.run(app.buffer_manager.sync_all())
            
            return jsonify({
                'success': success,
                'message': message
            })
            
        except Exception as e:
            logger.error(f"Error syncing buffer: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/devices')
    def devices():
        """Device management page"""
        return render_template('devices.html')
    
    @app.route('/traceability')
    def traceability():
        """Traceability page"""
        return render_template('traceability.html')
    
    @app.route('/logs')
    def logs():
        """Logs page"""
        return render_template('logs.html')
    
    @app.errorhandler(404)
    def not_found(error):
        """404 error handler"""
        return render_template('404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        """500 error handler"""
        return render_template('500.html'), 500


def run_async_in_thread(coro):
    """Run async coroutine in thread"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()
