#!/usr/bin/env python3
"""
Setup script for IoT Box Odoo Integration

This script helps set up the IoT Box system with proper configuration
and dependency installation.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
import yaml
import json


def run_command(command, check=True):
    """Run a shell command"""
    print(f"Running: {command}")
    result = subprocess.run(command, shell=True, check=check, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr)
    return result


def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 8):
        print("Error: Python 3.8 or higher is required")
        sys.exit(1)
    print(f"Python version: {sys.version}")


def install_dependencies():
    """Install Python dependencies"""
    print("Installing Python dependencies...")
    
    # Check if requirements.txt exists
    if not Path("requirements.txt").exists():
        print("Error: requirements.txt not found")
        sys.exit(1)
    
    # Install dependencies
    run_command("pip install -r requirements.txt")
    print("Dependencies installed successfully")


def create_directories():
    """Create necessary directories"""
    print("Creating directories...")
    
    directories = [
        "logs",
        "data",
        "config",
        "src/iot_box",
        "src/odoo_integration",
        "src/web_interface",
        "src/web_interface/static/css",
        "src/web_interface/static/js",
        "src/web_interface/static/images",
        "src/web_interface/templates",
        "tests/unit",
        "tests/integration",
        "tests/fixtures",
        "docs/api",
        "docs/user_guide",
        "docs/developer_guide"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"Created directory: {directory}")


def create_config_files():
    """Create configuration files from templates"""
    print("Creating configuration files...")
    
    # Check if config files already exist
    config_files = [
        "config/config.yaml",
        "config/devices.yaml",
        "config/odoo_config.yaml"
    ]
    
    for config_file in config_files:
        if Path(config_file).exists():
            print(f"Configuration file already exists: {config_file}")
            continue
        
        # Create from example if available
        example_file = f"{config_file}.example"
        if Path(example_file).exists():
            shutil.copy(example_file, config_file)
            print(f"Created {config_file} from example")
        else:
            print(f"Warning: No example file found for {config_file}")


def setup_database():
    """Setup database if needed"""
    print("Setting up database...")
    
    # Check if SQLite database exists
    db_path = Path("data/iot_traceability.db")
    if db_path.exists():
        print("Database already exists")
        return
    
    # Create SQLite database
    import sqlite3
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create basic tables
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS traceability (
            id TEXT PRIMARY KEY,
            event_type TEXT NOT NULL,
            device_id TEXT NOT NULL,
            scan_data TEXT NOT NULL,
            scan_type TEXT NOT NULL,
            work_order_id TEXT,
            component_id INTEGER,
            operator_id TEXT,
            timestamp REAL NOT NULL,
            status TEXT NOT NULL,
            error_message TEXT,
            metadata TEXT
        )
    """)
    
    conn.commit()
    conn.close()
    print("Database created successfully")


def setup_logging():
    """Setup logging configuration"""
    print("Setting up logging...")
    
    # Create logs directory if it doesn't exist
    Path("logs").mkdir(exist_ok=True)
    
    # Create log files
    log_files = [
        "logs/iot_box.log",
        "logs/audit.log",
        "logs/error.log"
    ]
    
    for log_file in log_files:
        Path(log_file).touch()
        print(f"Created log file: {log_file}")


def setup_permissions():
    """Setup file permissions"""
    print("Setting up permissions...")
    
    # Make scripts executable
    script_files = [
        "scripts/setup.py",
        "scripts/install_dependencies.py",
        "scripts/deploy.py"
    ]
    
    for script_file in script_files:
        if Path(script_file).exists():
            os.chmod(script_file, 0o755)
            print(f"Made executable: {script_file}")


def validate_configuration():
    """Validate configuration files"""
    print("Validating configuration...")
    
    try:
        # Load main config
        with open("config/config.yaml", 'r') as file:
            config = yaml.safe_load(file)
        
        # Check required sections
        required_sections = ['iot_box', 'odoo', 'logging']
        for section in required_sections:
            if section not in config:
                print(f"Warning: Missing configuration section: {section}")
        
        print("Configuration validation completed")
        
    except Exception as e:
        print(f"Error validating configuration: {e}")


def create_systemd_service():
    """Create systemd service file"""
    print("Creating systemd service...")
    
    service_content = f"""[Unit]
Description=IoT Box Odoo Integration
After=network.target

[Service]
Type=simple
User=iotbox
Group=iotbox
WorkingDirectory={os.getcwd()}
ExecStart=/usr/bin/python3 {os.getcwd()}/src/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
"""
    
    service_file = Path("/etc/systemd/system/iot-box.service")
    
    if service_file.exists():
        print("Systemd service already exists")
        return
    
    try:
        with open(service_file, 'w') as f:
            f.write(service_content)
        print(f"Created systemd service: {service_file}")
        print("Run 'sudo systemctl daemon-reload' to reload systemd")
    except PermissionError:
        print("Warning: Cannot create systemd service (permission denied)")
        print("Create the service file manually or run with sudo")


def main():
    """Main setup function"""
    print("IoT Box Odoo Integration Setup")
    print("=" * 40)
    
    try:
        # Check Python version
        check_python_version()
        
        # Create directories
        create_directories()
        
        # Install dependencies
        install_dependencies()
        
        # Create configuration files
        create_config_files()
        
        # Setup database
        setup_database()
        
        # Setup logging
        setup_logging()
        
        # Setup permissions
        setup_permissions()
        
        # Validate configuration
        validate_configuration()
        
        # Create systemd service
        create_systemd_service()
        
        print("\nSetup completed successfully!")
        print("\nNext steps:")
        print("1. Edit configuration files in config/ directory")
        print("2. Configure Odoo connection in config/odoo_config.yaml")
        print("3. Configure devices in config/devices.yaml")
        print("4. Run: python src/main.py")
        print("5. Access web interface at http://localhost:8080")
        
    except Exception as e:
        print(f"Setup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
