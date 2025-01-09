#!/usr/bin/env python3
"""
Dependency installation script for IoT Box

This script installs all required dependencies for the IoT Box system.
"""

import subprocess
import sys
import platform
import os
from pathlib import Path


def run_command(command, check=True):
    """Run a shell command"""
    print(f"Running: {command}")
    result = subprocess.run(command, shell=True, check=check, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr)
    return result


def install_system_dependencies():
    """Install system dependencies based on OS"""
    system = platform.system().lower()
    
    print(f"Installing system dependencies for {system}")
    
    if system == "linux":
        install_linux_dependencies()
    elif system == "darwin":  # macOS
        install_macos_dependencies()
    elif system == "windows":
        install_windows_dependencies()
    else:
        print(f"Unsupported operating system: {system}")
        sys.exit(1)


def install_linux_dependencies():
    """Install Linux dependencies"""
    print("Installing Linux dependencies...")
    
    # Update package list
    run_command("sudo apt-get update")
    
    # Install required packages
    packages = [
        "python3-dev",
        "python3-pip",
        "python3-venv",
        "libusb-1.0-0",
        "libusb-1.0-0-dev",
        "libbluetooth-dev",
        "libglib2.0-dev",
        "libdbus-1-dev",
        "libudev-dev",
        "libical-dev",
        "libreadline-dev",
        "libsndfile1-dev",
        "libasound2-dev",
        "build-essential",
        "pkg-config",
        "curl",
        "wget",
        "git"
    ]
    
    for package in packages:
        try:
            run_command(f"sudo apt-get install -y {package}")
        except subprocess.CalledProcessError:
            print(f"Warning: Failed to install {package}")


def install_macos_dependencies():
    """Install macOS dependencies"""
    print("Installing macOS dependencies...")
    
    # Check if Homebrew is installed
    try:
        run_command("brew --version")
    except subprocess.CalledProcessError:
        print("Installing Homebrew...")
        run_command('/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"')
    
    # Install required packages
    packages = [
        "python@3.9",
        "libusb",
        "pkg-config",
        "curl",
        "wget",
        "git"
    ]
    
    for package in packages:
        try:
            run_command(f"brew install {package}")
        except subprocess.CalledProcessError:
            print(f"Warning: Failed to install {package}")


def install_windows_dependencies():
    """Install Windows dependencies"""
    print("Installing Windows dependencies...")
    
    # Check if Chocolatey is installed
    try:
        run_command("choco --version")
    except subprocess.CalledProcessError:
        print("Installing Chocolatey...")
        run_command('powershell -Command "Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString(\'https://community.chocolatey.org/install.ps1\'))"')
    
    # Install required packages
    packages = [
        "python3",
        "git",
        "curl",
        "wget"
    ]
    
    for package in packages:
        try:
            run_command(f"choco install {package} -y")
        except subprocess.CalledProcessError:
            print(f"Warning: Failed to install {package}")


def install_python_dependencies():
    """Install Python dependencies"""
    print("Installing Python dependencies...")
    
    # Check if requirements.txt exists
    if not Path("requirements.txt").exists():
        print("Error: requirements.txt not found")
        sys.exit(1)
    
    # Upgrade pip
    run_command("python -m pip install --upgrade pip")
    
    # Install dependencies
    run_command("pip install -r requirements.txt")
    
    # Install additional development dependencies
    dev_packages = [
        "pytest",
        "pytest-cov",
        "black",
        "flake8",
        "mypy"
    ]
    
    for package in dev_packages:
        try:
            run_command(f"pip install {package}")
        except subprocess.CalledProcessError:
            print(f"Warning: Failed to install {package}")


def setup_virtual_environment():
    """Setup Python virtual environment"""
    print("Setting up virtual environment...")
    
    venv_path = Path("venv")
    
    if venv_path.exists():
        print("Virtual environment already exists")
        return
    
    # Create virtual environment
    run_command("python -m venv venv")
    
    # Activate virtual environment
    if platform.system().lower() == "windows":
        activate_script = "venv\\Scripts\\activate"
    else:
        activate_script = "venv/bin/activate"
    
    print(f"Virtual environment created. Activate it with: {activate_script}")


def install_usb_dependencies():
    """Install USB-related dependencies"""
    print("Installing USB dependencies...")
    
    try:
        # Install pyusb
        run_command("pip install pyusb")
        
        # Install libusb for pyusb
        if platform.system().lower() == "linux":
            run_command("sudo apt-get install -y libusb-1.0-0-dev")
        elif platform.system().lower() == "darwin":
            run_command("brew install libusb")
        
    except subprocess.CalledProcessError as e:
        print(f"Warning: Failed to install USB dependencies: {e}")


def install_bluetooth_dependencies():
    """Install Bluetooth dependencies"""
    print("Installing Bluetooth dependencies...")
    
    try:
        # Install pybluez
        run_command("pip install pybluez")
        
        # Install Bluetooth libraries
        if platform.system().lower() == "linux":
            run_command("sudo apt-get install -y libbluetooth-dev")
        elif platform.system().lower() == "darwin":
            run_command("brew install bluez")
        
    except subprocess.CalledProcessError as e:
        print(f"Warning: Failed to install Bluetooth dependencies: {e}")


def verify_installation():
    """Verify installation"""
    print("Verifying installation...")
    
    # Check Python version
    result = run_command("python --version")
    print(f"Python version: {result.stdout.strip()}")
    
    # Check pip version
    result = run_command("pip --version")
    print(f"Pip version: {result.stdout.strip()}")
    
    # Test imports
    test_imports = [
        "flask",
        "fastapi",
        "pydantic",
        "yaml",
        "sqlalchemy",
        "redis"
    ]
    
    for module in test_imports:
        try:
            run_command(f"python -c 'import {module}; print(f\"{module} imported successfully\")'")
        except subprocess.CalledProcessError:
            print(f"Warning: Failed to import {module}")


def main():
    """Main installation function"""
    print("IoT Box Dependency Installation")
    print("=" * 40)
    
    try:
        # Install system dependencies
        install_system_dependencies()
        
        # Setup virtual environment
        setup_virtual_environment()
        
        # Install Python dependencies
        install_python_dependencies()
        
        # Install USB dependencies
        install_usb_dependencies()
        
        # Install Bluetooth dependencies
        install_bluetooth_dependencies()
        
        # Verify installation
        verify_installation()
        
        print("\nDependency installation completed successfully!")
        print("\nNext steps:")
        print("1. Activate virtual environment:")
        if platform.system().lower() == "windows":
            print("   venv\\Scripts\\activate")
        else:
            print("   source venv/bin/activate")
        print("2. Run: python scripts/setup.py")
        print("3. Configure your system and run: python src/main.py")
        
    except Exception as e:
        print(f"Installation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
