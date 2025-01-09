  # IoT Box Odoo Manufacturing Integration

## 📋 Project Overview

This project provides a comprehensive IoT Box solution for integrating barcode and RFID scanners with Odoo Manufacturing, enabling real-time component tracking, automated data entry, and full traceability for compliance requirements.

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Scanners      │    │   IoT Box       │    │   Odoo Server   │
│                 │    │                 │    │                 │
│ • Barcode       │───▶│ • Device Mgmt   │───▶│ • Manufacturing │
│ • RFID          │    │ • Event Buffer  │    │ • Traceability  │
│ • USB/Network   │    │ • Offline Sync  │    │ • Work Orders   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🚀 Key Features

### Core Functionality
- **Real-time Component Tracking**: Track movement of components in production lines
- **Automated Validation**: Ensure correct parts are consumed in work orders
- **Full Traceability**: Complete audit trail for compliance (ISO 9001, FDA)
- **Error Reduction**: Eliminate manual data entry errors

### Device Support
- **Barcode Scanners**: USB, Bluetooth, Wi-Fi connectivity
- **RFID Scanners**: UHF/HF tag support
- **Plug-and-Play**: Automatic device detection and registration
- **Multi-device**: Support for multiple scanners simultaneously

### Integration Features
- **Odoo Manufacturing**: Seamless integration with work orders and BoM
- **Offline Mode**: Buffer scans when disconnected, sync when online
- **Security**: HTTPS communication and access control
- **Performance**: < 2 second scan registration

## 📁 Project Structure

```
iot_box_odoo_project/
├── README.md                           # This file
├── requirements.txt                    # Python dependencies
├── docker-compose.yml                  # Docker setup
├── config/
│   ├── config.yaml                     # Main configuration
│   ├── devices.yaml                    # Device configurations
│   └── odoo_config.yaml               # Odoo connection settings
├── src/
│   ├── iot_box/                        # IoT Box core
│   │   ├── __init__.py
│   │   ├── core/
│   │   │   ├── device_manager.py       # Device detection & management
│   │   │   ├── event_manager.py        # Event processing
│   │   │   ├── buffer_manager.py       # Offline buffering
│   │   │   └── security_manager.py     # Security & authentication
│   │   ├── handlers/
│   │   │   ├── barcode_handler.py      # Barcode scanner interface
│   │   │   ├── rfid_handler.py         # RFID scanner interface
│   │   │   └── base_handler.py         # Base handler class
│   │   └── utils/
│   │       ├── logger.py               # Logging utilities
│   │       ├── validators.py           # Data validation
│   │       └── helpers.py              # Helper functions
│   ├── odoo_integration/               # Odoo integration module
│   │   ├── __init__.py
│   │   ├── models/
│   │   │   ├── work_order.py           # Work order management
│   │   │   ├── component.py            # Component tracking
│   │   │   └── traceability.py         # Audit trail
│   │   ├── services/
│   │   │   ├── bom_service.py          # Bill of Materials service
│   │   │   ├── validation_service.py   # Component validation
│   │   │   └── sync_service.py         # Data synchronization
│   │   └── api/
│   │       ├── endpoints.py            # REST API endpoints
│   │       └── webhooks.py             # Webhook handlers
│   └── web_interface/                  # Web dashboard
│       ├── static/
│       │   ├── css/
│       │   ├── js/
│       │   └── images/
│       ├── templates/
│       │   ├── dashboard.html
│       │   ├── devices.html
│       │   └── traceability.html
│       └── app.py                      # Flask web application
├── tests/
│   ├── unit/                           # Unit tests
│   ├── integration/                    # Integration tests
│   └── fixtures/                       # Test data
├── scripts/
│   ├── setup.py                        # Setup script
│   ├── install_dependencies.py         # Dependency installer
│   └── deploy.py                       # Deployment script
├── docs/
│   ├── api/                            # API documentation
│   ├── user_guide/                     # User documentation
│   └── developer_guide/                # Developer documentation
└── docker/
    ├── Dockerfile.iotbox               # IoT Box container
    ├── Dockerfile.odoo                 # Odoo integration container
    └── docker-compose.yml              # Multi-container setup
```

## 🛠️ Installation & Setup

### Prerequisites
- Python 3.8+
- Docker & Docker Compose
- Odoo 15+ with Manufacturing module
- Compatible barcode/RFID scanners

### Quick Start

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd iot_box_odoo_project
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure the system**
   ```bash
   cp config/config.yaml.example config/config.yaml
   # Edit config/config.yaml with your settings
   ```

4. **Start with Docker**
   ```bash
   docker-compose up -d
   ```

5. **Access the web interface**
   - Open http://localhost:8080
   - Configure Odoo connection
   - Register your scanners

## 🔧 Odoo IoT Box Configuration Guide

### Step 1: Install IoT Module in Odoo

1. **Enable Developer Mode**
   - Go to Settings → General Settings
   - Check "Developer Tools" → "Developer Mode"
   - Save settings

2. **Install IoT Module**
   - Go to Apps → Update Apps List
   - Search for "IoT" or "Hardware"
   - Install "IoT Box" module if available
   - If not available, install "Hardware Proxy" module

3. **Configure IoT Box Connection**
   - Go to IoT → IoT Boxes
   - Click "Create" to add a new IoT Box
   - Fill in the following details:
     ```
     Name: IoT Box Manufacturing
     URL: http://your-iot-box-ip:8069
     Status: Online
     ```

### Step 2: Configure Manufacturing Integration

1. **Enable Manufacturing Module**
   - Go to Apps → Manufacturing
   - Install "Manufacturing" module if not already installed
   - Install "Quality Control" module for enhanced traceability

2. **Configure Work Orders**
   - Go to Manufacturing → Configuration → Settings
   - Enable "Work Orders" if not already enabled
   - Enable "Track Manufacturing Orders" for traceability

3. **Set Up Product Tracking**
   - Go to Inventory → Configuration → Settings
   - Enable "Track Lots/Serial Numbers" for components
   - Enable "Track Manufacturing Lots" for finished products

### Step 3: Configure IoT Box in Odoo

1. **Access IoT Box Settings**
   - Go to IoT → IoT Boxes
   - Select your IoT Box
   - Click "Configure"

2. **Add Scanner Devices**
   - Click "Add Device"
   - Select device type:
     - **Barcode Scanner**: For barcode readers
     - **RFID Reader**: For RFID scanners
     - **Generic Device**: For custom devices
   - Configure device parameters:
     ```
     Device Name: Production Scanner 1
     Device Type: Barcode Scanner
     Connection: USB/Network/Bluetooth
     Port/Address: /dev/ttyUSB0 or IP:Port
     ```

3. **Configure Manufacturing Integration**
   - Go to Manufacturing → Configuration → IoT Box Integration
   - Enable "IoT Box Integration"
   - Select your IoT Box
   - Configure scan behavior:
     ```
     Auto-consume components: Yes
     Validate work orders: Yes
     Require operator login: Yes
     Log all scans: Yes
     ```

### Step 4: Set Up Work Order Templates

1. **Create Work Order Template**
   - Go to Manufacturing → Master Data → Work Centers
   - Create work centers for each production line
   - Assign IoT Box to work centers:
     ```
     Work Center: Assembly Line 1
     IoT Box: IoT Box Manufacturing
     Scanner: Production Scanner 1
     ```

2. **Configure Bill of Materials (BoM)**
   - Go to Manufacturing → Master Data → Bills of Materials
   - Create BoM for your products
   - Ensure components have barcodes:
     ```
     Product: Finished Product A
     Components:
     - Raw Material 1 (Barcode: 1234567890)
     - Raw Material 2 (Barcode: 0987654321)
     - Semi-finished Part 1 (Barcode: 1122334455)
     ```

3. **Set Up Work Orders**
   - Go to Manufacturing → Operations → Manufacturing Orders
   - Create manufacturing orders
   - Assign to work centers with IoT Box integration

### Step 5: Configure Scanner Workflows

1. **Work Order Context Setting**
   - Configure how work orders are identified:
     - **QR Code on Work Order**: Print QR codes on work order sheets
     - **Manual Selection**: Operators select work order from interface
     - **Auto-detection**: Based on production line and schedule

2. **Component Scanning Rules**
   - Set up validation rules:
     ```
     Validate component against BoM: Yes
     Check quantity limits: Yes
     Require operator confirmation: No
     Auto-consume on valid scan: Yes
     ```

3. **Error Handling**
   - Configure error responses:
     ```
     Invalid component: Alert + Log + Block production
     Wrong work order: Alert + Log + Allow override
     Quantity exceeded: Alert + Log + Require approval
     ```

### Step 6: Test Integration

1. **Test Scanner Connection**
   - Go to IoT → IoT Boxes → Your Box → Devices
   - Test each scanner device
   - Verify scan data is received

2. **Test Work Order Flow**
   - Create a test manufacturing order
   - Go to the production line
   - Scan work order barcode
   - Scan component barcodes
   - Verify consumption in Odoo

3. **Test Traceability**
   - Go to Manufacturing → Reporting → Traceability
   - Check that all scans are logged
   - Verify component consumption tracking

### Step 7: Production Setup

1. **Train Operators**
   - Provide training on scanner usage
   - Document work order scanning procedures
   - Create troubleshooting guides

2. **Monitor Performance**
   - Set up dashboards for real-time monitoring
   - Configure alerts for errors
   - Schedule regular maintenance

3. **Backup and Recovery**
   - Configure automated backups
   - Test disaster recovery procedures
   - Document recovery steps

### Troubleshooting Common Issues

#### Scanner Not Detected
- Check USB/Network connection
- Verify device drivers are installed
- Check IoT Box logs for errors
- Restart IoT Box service

#### Work Order Not Found
- Verify work order is in "Confirmed" or "In Progress" state
- Check work order number format
- Ensure work order is assigned to correct work center

#### Component Validation Failed
- Verify component barcode is correct
- Check if component is in the BoM
- Ensure component is not already fully consumed
- Check component tracking settings

#### Sync Issues
- Check network connectivity between IoT Box and Odoo
- Verify Odoo API credentials
- Check IoT Box buffer status
- Review error logs

### Advanced Configuration

#### Custom Fields
- Add custom fields to work orders for additional context
- Configure custom validation rules
- Set up custom reporting fields

#### Multi-Location Setup
- Configure multiple IoT Boxes for different locations
- Set up location-specific work orders
- Configure cross-location traceability

#### Integration with Other Systems
- Connect to MES systems
- Integrate with quality control systems
- Set up ERP integration

### Security Considerations

1. **Network Security**
   - Use HTTPS for all communications
   - Configure firewall rules
   - Use VPN for remote access

2. **Access Control**
   - Set up user roles and permissions
   - Configure operator authentication
   - Enable audit logging

3. **Data Protection**
   - Encrypt sensitive data
   - Regular security updates
   - Backup encryption

### Manual Installation

1. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Odoo connection**
   ```yaml
   # config/odoo_config.yaml
   odoo:
     url: "https://your-odoo-instance.com"
     database: "your_database"
     username: "your_username"
     password: "your_password"
   ```

3. **Start the IoT Box service**
   ```bash
   python src/iot_box/main.py
   ```

4. **Start the web interface**
   ```bash
   python src/web_interface/app.py
   ```

## 🔧 Configuration

### Device Configuration
```yaml
# config/devices.yaml
scanners:
  barcode:
    - name: "USB Barcode Scanner"
      type: "usb"
      vendor_id: "0x05e0"
      product_id: "0x1200"
      enabled: true
  rfid:
    - name: "UHF RFID Reader"
      type: "network"
      ip: "192.168.1.100"
      port: 8080
      enabled: true
```

### Odoo Integration
```yaml
# config/odoo_config.yaml
odoo:
  url: "https://your-odoo-instance.com"
  database: "production_db"
  username: "iot_user"
  password: "secure_password"
  api_version: "15.0"
  timeout: 30
  retry_attempts: 3
```

## 📱 Usage

### Basic Workflow

1. **Start Production**
   - Scan work order barcode to set context
   - System validates work order exists in Odoo

2. **Component Consumption**
   - Scan component barcode/RFID
   - System checks if component is required for current work order
   - Valid components are marked as consumed
   - Invalid components trigger alerts

3. **Production Completion**
   - Scan finished product barcode
   - Work order is marked as complete
   - Traceability data is logged

### Web Interface

- **Dashboard**: Real-time production status
- **Device Management**: Configure and monitor scanners
- **Traceability**: View complete audit trail
- **Alerts**: Monitor errors and warnings

## 🔒 Security Features

- **HTTPS Communication**: Encrypted data transmission
- **Access Control**: Role-based permissions
- **Device Authentication**: Secure scanner registration
- **Audit Logging**: Complete activity tracking
- **Data Validation**: Input sanitization and validation

## 📊 Monitoring & Logging

### Log Levels
- **DEBUG**: Detailed debugging information
- **INFO**: General operational messages
- **WARNING**: Warning conditions
- **ERROR**: Error conditions
- **CRITICAL**: Critical errors

### Metrics
- Scan success rate
- Device connectivity status
- Odoo sync performance
- Error rates and types

## 🧪 Testing

### Run Tests
```bash
# Unit tests
python -m pytest tests/unit/

# Integration tests
python -m pytest tests/integration/

# All tests
python -m pytest tests/
```

### Test Coverage
```bash
python -m pytest --cov=src tests/
```

## 🚀 Deployment

### Production Deployment

1. **Environment Setup**
   ```bash
   export ODOO_URL="https://your-odoo-instance.com"
   export ODOO_DB="production_db"
   export ODOO_USER="iot_user"
   export ODOO_PASSWORD="secure_password"
   ```

2. **Docker Deployment**
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

3. **Health Check**
   ```bash
   curl http://localhost:8080/health
   ```

## 🔄 API Documentation

### REST Endpoints

#### Scan Events
```http
POST /api/v1/scan
Content-Type: application/json

{
  "device_id": "scanner_001",
  "scan_data": "1234567890",
  "scan_type": "barcode",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

#### Work Order Context
```http
POST /api/v1/work-order/set-context
Content-Type: application/json

{
  "work_order_id": "WO001",
  "operator_id": "operator_123"
}
```

#### Traceability Query
```http
GET /api/v1/traceability?work_order_id=WO001&start_date=2024-01-01&end_date=2024-01-31
```

## 🐛 Troubleshooting

### Common Issues

1. **Scanner Not Detected**
   - Check USB connection
   - Verify device drivers
   - Check device configuration

2. **Odoo Connection Failed**
   - Verify Odoo URL and credentials
   - Check network connectivity
   - Validate API permissions

3. **Scan Not Processing**
   - Check device registration
   - Verify work order context
   - Review error logs

### Debug Mode
```bash
python src/iot_box/main.py --debug
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 📞 Support

- **Documentation**: [docs/](docs/)
- **Issues**: [GitHub Issues](https://github.com/your-repo/issues)
- **Email**: support@yourcompany.com

## 🔮 Roadmap

### Version 2.0
- [ ] Label printer integration
- [ ] Weighing scale integration
- [ ] Advanced analytics dashboard
- [ ] Mobile app for operators

### Version 2.1
- [ ] Machine learning for predictive maintenance
- [ ] Advanced reporting and analytics
- [ ] Multi-language support
- [ ] Cloud deployment options

---

**Made with ❤️ for Manufacturing Excellence**
