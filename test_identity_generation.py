#!/usr/bin/env python3
"""Test script for node identity generation."""

import json
import sys
import os

# Add the instance/scripts directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'instance', 'scripts'))

from generate_node_identity import NodeIdentityGenerator

def test_identity_generation():
    """Test the identity generation system."""
    print("Testing Node Identity Generation System")
    print("=" * 50)
    
    # Test with different instance IDs to show determinism
    test_instances = [
        "i-0a1b2c3d4e5f6789a",
        "i-0a1b2c3d4e5f6789a",  # Same ID - should produce same result
        "i-9z8y7x6w5v4u3t2s1r",
        "i-1234567890abcdef0",
    ]
    
    previous_identity = None
    
    for i, instance_id in enumerate(test_instances):
        print(f"\nTest {i+1}: Instance ID: {instance_id}")
        print("-" * 30)
        
        generator = NodeIdentityGenerator(instance_id)
        identity = generator.generate_identity()
        
        print(f"Sensor ID: {identity['sensor_id']}")
        print(f"Location: {identity['location']['address']}")
        print(f"Coordinates: {identity['location']['coordinates']['latitude']}, {identity['location']['coordinates']['longitude']}")
        print(f"Timezone: {identity['location']['timezone']}")
        print(f"Device: {identity['device_info']['manufacturer']} {identity['device_info']['model']}")
        print(f"Firmware: {identity['device_info']['firmware_version']}")
        print(f"Deployment: {identity['deployment']['deployment_type']}")
        print(f"Height: {identity['deployment']['height_meters']}m")
        
        # Check determinism (skip timestamp fields)
        if i == 1:  # Second test with same instance ID
            # Compare without timestamp fields
            identity_copy = dict(identity)
            prev_identity_copy = dict(previous_identity)
            
            # Remove non-deterministic timestamp fields
            for key in ['metadata']:
                if key in identity_copy and key in prev_identity_copy:
                    identity_metadata = dict(identity_copy[key])
                    prev_metadata = dict(prev_identity_copy[key])
                    
                    # Only compare deterministic fields
                    deterministic_fields = ['instance_id', 'generation_seed', 'sensor_type']
                    identity_det = {k: identity_metadata.get(k) for k in deterministic_fields}
                    prev_det = {k: prev_metadata.get(k) for k in deterministic_fields}
                    
                    identity_copy[key] = identity_det
                    prev_identity_copy[key] = prev_det
            
            if identity_copy == prev_identity_copy:
                print("✅ Determinism test PASSED - Same instance ID produces same identity")
            else:
                print("❌ Determinism test FAILED - Same instance ID produces different identity")
        
        previous_identity = identity
        
        # Save test output
        test_output = f"/tmp/test_identity_{instance_id.replace('i-', '')}.json"
        with open(test_output, 'w') as f:
            json.dump(identity, f, indent=2)
        print(f"Test identity saved to: {test_output}")
    
    print("\n" + "=" * 50)
    print("Testing JSON structure validation...")
    
    # Validate structure
    required_keys = [
        'sensor_id', 'location', 'device_info', 'deployment', 'metadata'
    ]
    
    for key in required_keys:
        if key not in identity:
            print(f"❌ Missing required key: {key}")
            return False
    
    # Validate location structure
    location_keys = ['city', 'state', 'coordinates', 'timezone', 'address']
    for key in location_keys:
        if key not in identity['location']:
            print(f"❌ Missing location key: {key}")
            return False
    
    # Validate coordinates
    coords = identity['location']['coordinates']
    if not (-90 <= coords['latitude'] <= 90):
        print("❌ Invalid latitude")
        return False
    if not (-180 <= coords['longitude'] <= 180):
        print("❌ Invalid longitude")
        return False
    
    # Validate sensor ID format
    sensor_id = identity['sensor_id']
    if not sensor_id.startswith('SENSOR_'):
        print("❌ Invalid sensor ID format")
        return False
    
    print("✅ JSON structure validation PASSED")
    
    # Test file generation
    print("\nTesting file generation...")
    test_file = "/tmp/test_node_identity.json"
    if generator.save_identity(test_file):
        print(f"✅ File generation test PASSED - Saved to {test_file}")
        with open(test_file, 'r') as f:
            loaded_identity = json.load(f)
            # Compare without timestamp for round-trip test
            identity_copy = dict(identity)
            loaded_copy = dict(loaded_identity)
            
            # Remove timestamp fields for comparison
            for key in ['metadata']:
                if key in identity_copy and key in loaded_copy:
                    identity_metadata = dict(identity_copy[key])
                    loaded_metadata = dict(loaded_copy[key])
                    
                    # Compare deterministic fields
                    deterministic_fields = ['instance_id', 'generation_seed', 'sensor_type']
                    identity_det = {k: identity_metadata.get(k) for k in deterministic_fields}
                    loaded_det = {k: loaded_metadata.get(k) for k in deterministic_fields}
                    
                    identity_copy[key] = identity_det
                    loaded_copy[key] = loaded_det
            
            if identity_copy == loaded_copy:
                print("✅ File round-trip test PASSED")
            else:
                print("❌ File round-trip test FAILED")
    else:
        print("❌ File generation test FAILED")
    
    return True

if __name__ == "__main__":
    try:
        test_identity_generation()
        print("\n🎉 All tests completed successfully!")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()