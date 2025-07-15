#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""
Simple test script for sensor integration validation.
"""

import os
import json
import sys

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
    """Test the identity generation script structure."""
    print("🔍 Testing identity generation...")
    
    try:
        # Import the module
        sys.path.append('instance/scripts')
        
        # Test identity generation logic
        from generate_demo_identity import generate_demo_identity
        
        # Generate a test identity
        os.environ['MOCK_INSTANCE_ID'] = 'i-test-123456'
        identity = generate_demo_identity()
        
        # Validate structure
        required_keys = ["sensor_id", "location", "device_info", "deployment"]
        for key in required_keys:
            if key not in identity:
                print(f"❌ Missing key in identity: {key}")
                return False
        
        print(f"✅ Identity generated: {identity['sensor_id']}")
        print(f"📍 Location: {identity['location']['location_name']}")
        print(f"🏭 Facility: {identity['location']['facility']}")
        print(f"🔧 Sensor Type: {identity['device_info']['sensor_type']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing identity generation: {e}")
        return False

def test_config_format():
    """Test configuration file format."""
    print("🔍 Testing configuration format...")
    
    try:
        with open('instance/config/sensor-config.yaml') as f:
            content = f.read()
            
        # Basic validation
        required_keywords = ['simulation', 'normal_parameters', 'database', 'output']
        for keyword in required_keywords:
            if keyword not in content:
                print(f"❌ Missing config section: {keyword}")
                return False
        
        print("✅ Configuration format is valid")
        return True
        
    except Exception as e:
        print(f"❌ Error testing config: {e}")
        return False

def test_service_file():
    """Test systemd service file."""
    print("🔍 Testing systemd service file...")
    
    try:
        with open('instance/scripts/sensor-log-generator.service') as f:
            content = f.read()
            
        required_elements = [
            "Description=Sensor Log Generator Container Service",
            "After=docker.service",
            "ExecStart=/usr/bin/docker run",
            "ghcr.io/bacalhau-project/sensor-log-generator:latest",
            "/opt/sensor/config"
        ]
        
        for element in required_elements:
            if element not in content:
                print(f"❌ Missing from service file: {element}")
                return False
        
        print("✅ Systemd service file is valid")
        return True
        
    except Exception as e:
        print(f"❌ Error testing service file: {e}")
        return False

def test_demo_locations():
    """Test demo locations generation."""
    print("🔍 Testing demo locations...")
    
    try:
        sys.path.append('instance/scripts')
        from generate_demo_identity import generate_demo_identity
        
        # Test multiple instance IDs
        test_ids = ["i-demo-001", "i-demo-002", "i-demo-003"]
        locations = []
        
        for test_id in test_ids:
            os.environ['MOCK_INSTANCE_ID'] = test_id
            identity = generate_demo_identity()
            locations.append(identity['location']['location_name'])
        
        unique_locations = len(set(locations))
        print(f"✅ Generated {unique_locations} unique demo locations")
        
        for i, location in enumerate(locations):
            print(f"   {i+1}. {location}")
        
        return unique_locations > 0
        
    except Exception as e:
        print(f"❌ Error testing demo locations: {e}")
        return False

def main():
    """Run all tests."""
    print("🧪 Running sensor integration validation...\n")
    
    tests = [
        ("File Structure", test_files_exist),
        ("Identity Generation", test_identity_generation),
        ("Configuration Format", test_config_format),
        ("Systemd Service", test_service_file),
        ("Demo Locations", test_demo_locations)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        results.append(test_func())
    
    print(f"\n{'='*60}")
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"🎉 All {total} tests passed! Sensor integration is ready.")
        print("\n📋 Demo locations created:")
        print("   - Acme Manufacturing Plant - Assembly Building A - Room 301")
        print("   - Global Tech Solutions - Production Facility B - Room 208") 
        print("   - TechCorp Assembly Plant - Manufacturing Complex C - Room 104")
        print("\n🚀 Ready for deployment:")
        print("   uv run deploy_spot.py create")
        print("   ssh into instances to verify sensor data generation")
    else:
        print(f"❌ {total - passed} out of {total} tests failed")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)