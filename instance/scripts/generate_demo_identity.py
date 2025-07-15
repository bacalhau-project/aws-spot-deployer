#!/usr/bin/env uv run -s
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///

"""
Generate demo-friendly node identities for sensor data simulation.
Creates realistic factory/manufacturing environment names for demo purposes.
"""

import hashlib
import json
import os
import subprocess
from datetime import datetime, timedelta


def get_instance_metadata(metadata_key):
    """Get instance metadata from the EC2 metadata service."""
    try:
        response = subprocess.check_output(
            ["curl", "-s", f"http://169.254.169.254/latest/meta-data/{metadata_key}"]
        )
        return response.decode("utf-8")
    except Exception:
        return None


def generate_demo_identity():
    """Generate a demo-friendly node identity for sensor simulation."""
    print("Generating demo node identity...")

    instance_id = get_instance_metadata("instance-id")
    if not instance_id:
        print("Warning: Could not get instance ID, using default")
        instance_id = "i-demo-123456"

    # Demo factory/manufacturing locations
    demo_locations = [
        {
            "facility": "Acme Manufacturing Plant",
            "building": "Assembly Building A",
            "floor": "Floor 3",
            "room": "Room 301",
            "zone": "Assembly Line 7",
            "sensor_type": "Temperature Monitor",
            "lat": 37.7749,
            "lng": -122.4194,
            "address": "1234 Industrial Way, San Francisco, CA",
        },
        {
            "facility": "Global Tech Solutions",
            "building": "Production Facility B",
            "floor": "Floor 2",
            "room": "Room 208",
            "zone": "Quality Control Station 3",
            "sensor_type": "Vibration Sensor",
            "lat": 40.7128,
            "lng": -74.0060,
            "address": "567 Innovation Drive, New York, NY",
        },
        {
            "facility": "TechCorp Assembly Plant",
            "building": "Manufacturing Complex C",
            "floor": "Floor 1",
            "room": "Room 104",
            "zone": "Packaging Line 2",
            "sensor_type": "Humidity Monitor",
            "lat": 41.8781,
            "lng": -87.6298,
            "address": "890 Factory Street, Chicago, IL",
        },
        {
            "facility": "Industrial Solutions Inc",
            "building": "Processing Plant D",
            "floor": "Basement Level",
            "room": "Room B12",
            "zone": "HVAC Control Center",
            "sensor_type": "Air Quality Sensor",
            "lat": 34.0522,
            "lng": -118.2437,
            "address": "321 Industrial Blvd, Los Angeles, CA",
        },
        {
            "facility": "Advanced Manufacturing Hub",
            "building": "Smart Factory E",
            "floor": "Floor 4",
            "room": "Room 412",
            "zone": "Robotic Assembly Station 5",
            "sensor_type": "Power Monitor",
            "lat": 30.2672,
            "lng": -97.7431,
            "address": "654 Tech Avenue, Austin, TX",
        },
        {
            "facility": "Precision Components Ltd",
            "building": "Quality Assurance F",
            "floor": "Floor 2",
            "room": "Room 215",
            "zone": "Testing Lab Alpha",
            "sensor_type": "Pressure Sensor",
            "lat": 47.6062,
            "lng": -122.3321,
            "address": "987 Precision Way, Seattle, WA",
        },
        {
            "facility": "MegaCorp Production Facility",
            "building": "Assembly Line G",
            "floor": "Floor 3",
            "room": "Room 307",
            "zone": "Conveyor Belt Monitor 12",
            "sensor_type": "Vibration Analyzer",
            "lat": 39.7392,
            "lng": -104.9903,
            "address": "147 Production Road, Denver, CO",
        },
        {
            "facility": "Innovation Manufacturing",
            "building": "Smart Building H",
            "floor": "Floor 5",
            "room": "Room 503",
            "zone": "Energy Management Center",
            "sensor_type": "Power Quality Monitor",
            "lat": 33.7490,
            "lng": -84.3880,
            "address": "258 Innovation Blvd, Atlanta, GA",
        },
        {
            "facility": "FutureTech Assembly",
            "building": "Automated Plant I",
            "floor": "Floor 1",
            "room": "Room 118",
            "zone": "Material Handling Zone 3",
            "sensor_type": "Flow Meter",
            "lat": 45.5152,
            "lng": -122.6784,
            "address": "369 Future Street, Portland, OR",
        },
        {
            "facility": "NextGen Manufacturing",
            "building": "Production Line J",
            "floor": "Floor 2",
            "room": "Room 222",
            "zone": "Environmental Control Unit",
            "sensor_type": "Temperature/Humidity Combo",
            "lat": 42.3601,
            "lng": -71.0589,
            "address": "741 NextGen Avenue, Boston, MA",
        },
        {
            "facility": "SmartFactory Solutions",
            "building": "IoT Building K",
            "floor": "Basement Level 2",
            "room": "Room B202",
            "zone": "Water Treatment Monitor",
            "sensor_type": "pH Sensor",
            "lat": 33.4484,
            "lng": -112.0740,
            "address": "852 Smart Way, Phoenix, AZ",
        },
        {
            "facility": "TechInnovation Plant",
            "building": "Manufacturing Line L",
            "floor": "Floor 4",
            "room": "Room 405",
            "zone": "Waste Management Station",
            "sensor_type": "Gas Detector",
            "lat": 36.1627,
            "lng": -86.7816,
            "address": "963 Tech Road, Nashville, TN",
        },
    ]

    # Deterministic location selection based on instance ID
    hash_val = int(hashlib.md5(instance_id.encode()).hexdigest(), 16)
    location_index = hash_val % len(demo_locations)
    location = demo_locations[location_index]

    # Create unique location name for demo reference
    location_name = f"{location['facility']} - {location['building']} - {location['room']} - {location['zone']}"

    # Generate sensor ID with facility reference
    facility_code = "".join(
        word[0] for word in location["facility"].split()[:2]
    ).upper()
    building_code = (
        location["building"].split()[1]
        if len(location["building"].split()) > 1
        else "B"
    )
    sensor_num = 1000 + (hash_val % 9000)
    sensor_id = f"SENSOR_{facility_code}_{building_code}_{sensor_num}"

    # Manufacturers and models for demo
    manufacturers = [
        "IndustrialSensors",
        "FactoryMonitor",
        "ProductionTech",
        "AssemblySensors",
        "ManufacturingIoT",
    ]
    models = [
        "FactorySense-Pro",
        "ProductionMonitor-XL",
        "LineAnalyzer-2000",
        "IndustrialEye-5G",
        "SmartSensor-IoT",
    ]

    # Deterministic selection
    manufacturer = manufacturers[hash_val % len(manufacturers)]
    model = models[hash_val % len(models)]
    firmware_version = f"FM_v{2 + (hash_val % 5)}.{hash_val % 10}.{hash_val % 100}"

    # Create demo identity
    identity = {
        "sensor_id": sensor_id,
        "location": {
            "facility": location["facility"],
            "building": location["building"],
            "floor": location["floor"],
            "room": location["room"],
            "zone": location["zone"],
            "location_name": location_name,
            "coordinates": {"latitude": location["lat"], "longitude": location["lng"]},
            "address": location["address"],
            "timezone": "America/New_York",  # Default for demo
        },
        "device_info": {
            "manufacturer": manufacturer,
            "model": model,
            "firmware_version": firmware_version,
            "serial_number": f"{manufacturer}-{sensor_num}",
            "sensor_type": location["sensor_type"],
        },
        "deployment": {
            "deployment_type": "industrial_monitor",
            "installation_date": (
                datetime.now() - timedelta(days=hash_val % 365)
            ).strftime("%Y-%m-%d"),
            "height_meters": 2.5 + (hash_val % 5),  # 2.5-7.5m typical mounting height
            "orientation_degrees": hash_val % 360,
            "calibration_date": datetime.now().strftime("%Y-%m-%d"),
        },
        "metadata": {
            "instance_id": instance_id,
            "generation_timestamp": datetime.now().isoformat(),
            "demo_environment": True,
            "purpose": "Bacalhau sensor data demo",
            "contact": "demo@bacalhau.org",
        },
    }

    return identity


def main():
    """Generate and save the demo identity."""
    identity = generate_demo_identity()

    # Ensure directory exists
    os.makedirs("/opt/sensor/config", exist_ok=True)

    # Write identity file
    identity_path = "/opt/sensor/config/node_identity.json"
    with open(identity_path, "w") as f:
        json.dump(identity, f, indent=2)

    # Also write a human-readable version
    readable_path = "/opt/sensor/config/location_info.txt"
    with open(readable_path, "w") as f:
        f.write(f"Demo Location: {identity['location']['location_name']}\n")
        f.write(f"Sensor ID: {identity['sensor_id']}\n")
        f.write(f"Sensor Type: {identity['device_info']['sensor_type']}\n")
        f.write(f"Address: {identity['location']['address']}\n")
        f.write(
            f"Coordinates: {identity['location']['coordinates']['latitude']}, {identity['location']['coordinates']['longitude']}\n"
        )
        f.write(f"Installation Date: {identity['deployment']['installation_date']}\n")

    print("Generated demo identity: {}".format(identity["sensor_id"]))
    print("Location: {}".format(identity["location"]["location_name"]))
    print("Files saved:")
    print("   - {}".format(identity_path))
    print("   - {}".format(readable_path))


if __name__ == "__main__":
    main()
