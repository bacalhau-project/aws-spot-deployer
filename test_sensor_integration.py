#!/usr/bin/env python3
"""
Test script to validate sensor integration for Bacalhau demo.
"""

import os
import json
import subprocess
import time
import sqlite3
from pathlib import Path

def test_files_exist():
    """Test that all required files exist."""
    print("🔍 Testing file structure...")
    
    required_files = [
        "instance/scripts/generate_demo_identity.py",
        "instance/config/sensor-config.yaml", 
        "instance/scripts/sensor-log-generator.service"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
    
    if missing_files:
        print(f"❌ Missing files: {missing_files}")
        return False
    
    print("✅ All required files exist")
    return True

def test_identity_generation():
    """Test the identity generation script."""
    print("🔍 Testing identity generation...")
    
    try:
        # Run the identity generator
        result = subprocess.run([
            'python3', 
            'instance/scripts/generate_demo_identity.py'
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"❌ Identity generation failed: {result.stderr}")
            return False
        
        # Check if identity file was created
        identity_file = "/opt/sensor/config/node_identity.json"
        if os.path.exists(identity_file):
            with open(identity_file) as f:
                identity = json.load(f)
                
            # Validate structure
            required_keys = ["sensor_id", "location", "device_info", "deployment"]
            for key in required_keys:
                if key not in identity:
                    print(f"❌ Missing key in identity: {key}")
                    return False
            
            print(f"✅ Identity generated: {identity['sensor_id']}")
            print(f"📍 Location: {identity['location']['location_name']}")
            return True
        else:
            print("❌ Identity file not created")
            return False
            
    except Exception as e:
        print(f"❌ Error testing identity generation: {e}")
        return False

def test_config_files():
    """Test configuration files are valid."""
    print("🔍 Testing configuration files...")
    
    try:
        # Test sensor config
        with open('instance/config/sensor-config.yaml') as f:
            import yaml
            config = yaml.safe_load(f)
            
        required_sections = ['simulation', 'normal_parameters', 'database']
        for section in required_sections:
            if section not in config:
                print(f"❌ Missing config section: {section}")
                return False
        
        print("✅ Configuration files are valid")
        return True
        
    except Exception as e:
        print(f"❌ Error testing config: {e}")
        return False

def test_systemd_service():
    """Test systemd service file."""
    print("🔍 Testing systemd service...")
    
    try:
        with open('instance/scripts/sensor-log-generator.service') as f:
            content = f.read()
            
        required_lines = [
            "Description=Sensor Log Generator Container Service",
            "After=docker.service",
            "ExecStart=/usr/bin/docker run",
            "ghcr.io/bacalhau-project/sensor-log-generator:latest"
        ]
        
        for line in required_lines:
            if line not in content:
                print(f"❌ Missing from service file: {line}")
                return False
        
        print("✅ Systemd service file is valid")
        return True
        
    except Exception as e:
        print(f"❌ Error testing service file: {e}")
        return False

def test_demo_locations():
    """Test that demo locations are properly formatted."""
    print("🔍 Testing demo locations...")
    
    try:
        # Import and test the identity generator
        import sys
        sys.path.append('instance/scripts')
        
        # Run with different instance IDs to test determinism
        test_ids = ["i-12345abcdef", "i-67890ghijkl", "i-11111mnopqr"]
        
        locations = []
        for test_id in test_ids:
            # Set mock instance ID
            os.environ['MOCK_INSTANCE_ID'] = test_id
            
            # Run generator
            result = subprocess.run([
                'python3', 
                'instance/scripts/generate_demo_identity.py'
            ], capture_output=True, text=True, env=os.environ)
            
            if result.returncode == 0:
                identity_file = "/opt/sensor/config/node_identity.json"
                if os.path.exists(identity_file):
                    with open(identity_file) as f:
                        identity = json.load(f)
                        locations.append(identity['location']['location_name'])
        
        print(f"✅ Generated {len(set(locations))} unique demo locations")
        for location in locations:
            print(f"   📍 {location}")
        
        return len(locations) > 0
        
    except Exception as e:
        print(f"❌ Error testing demo locations: {e}")
        return False

def test_integration():
    """Run all integration tests."""
    print("🧪 Running sensor integration tests...\n")
    
    tests = [
        ("File Structure", test_files_exist),
        ("Identity Generation", test_identity_generation),
        ("Configuration", test_config_files),
        ("Systemd Service", test_systemd_service),
        ("Demo Locations", test_demo_locations)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        results.append(test_func())
    
    print(f"\n{'='*50}")
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"🎉 All {total} tests passed! Sensor integration is ready.")
        print("\nNext steps:")
        print("1. Deploy spot instances with uv run deploy_spot.py create")
        print("2. SSH into instances and verify sensor service is running")
        print("3. Check /opt/sensor/data/sensor_data.db for generated data")
        print("4. Use bacalhau to process sensor data across all instances")
    else:
        print(f"❌ {total - passed} out of {total} tests failed")
        return False
    
    return True

if __name__ == "__main__":
    success = test_integration()
    exit(0 if success else 1)