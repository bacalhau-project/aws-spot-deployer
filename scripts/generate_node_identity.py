#!/usr/bin/env python3
"""
Generate deterministic node identities for sensor simulator.
Multi-cloud compatible version that works across different providers.
"""

import hashlib
import json
import os
import random
import sys
from datetime import datetime
from typing import Any, Dict


class MultiCloudNodeIdentityGenerator:
    """Generate realistic node identities across cloud providers."""

    # US cities with coordinates for realistic sensor locations
    LOCATIONS = [
        {
            "city": "San Francisco",
            "state": "CA",
            "lat": 37.7749,
            "lon": -122.4194,
            "timezone": "America/Los_Angeles",
        },
        {
            "city": "Austin",
            "state": "TX",
            "lat": 30.2672,
            "lon": -97.7431,
            "timezone": "America/Chicago",
        },
        {
            "city": "Seattle",
            "state": "WA",
            "lat": 47.6062,
            "lon": -122.3321,
            "timezone": "America/Los_Angeles",
        },
        {
            "city": "Denver",
            "state": "CO",
            "lat": 39.7392,
            "lon": -104.9903,
            "timezone": "America/Denver",
        },
        {
            "city": "Miami",
            "state": "FL",
            "lat": 25.7617,
            "lon": -80.1918,
            "timezone": "America/New_York",
        },
        {
            "city": "Boston",
            "state": "MA",
            "lat": 42.3601,
            "lon": -71.0589,
            "timezone": "America/New_York",
        },
        {
            "city": "Chicago",
            "state": "IL",
            "lat": 41.8781,
            "lon": -87.6298,
            "timezone": "America/Chicago",
        },
        {
            "city": "Atlanta",
            "state": "GA",
            "lat": 33.7490,
            "lon": -84.3880,
            "timezone": "America/New_York",
        },
        {
            "city": "Portland",
            "state": "OR",
            "lat": 45.5152,
            "lon": -122.6784,
            "timezone": "America/Los_Angeles",
        },
        {
            "city": "Phoenix",
            "state": "AZ",
            "lat": 33.4484,
            "lon": -112.0740,
            "timezone": "America/Phoenix",
        },
    ]

    # Sensor manufacturers and models for realism
    SENSORS = [
        {"manufacturer": "Honeywell", "model": "HMC5883L", "type": "magnetometer"},
        {"manufacturer": "Bosch", "model": "BME280", "type": "environmental"},
        {"manufacturer": "STMicroelectronics", "model": "LIS3DH", "type": "accelerometer"},
        {"manufacturer": "InvenSense", "model": "MPU-9250", "type": "IMU"},
        {"manufacturer": "Sensirion", "model": "SHT30", "type": "humidity"},
        {"manufacturer": "ams", "model": "TSL2561", "type": "light"},
        {"manufacturer": "Analog Devices", "model": "ADXL345", "type": "accelerometer"},
        {"manufacturer": "Maxim", "model": "DS18B20", "type": "temperature"},
    ]

    def __init__(self, instance_id: str = None):
        """Initialize with instance ID for deterministic generation."""
        self.instance_id = instance_id or self._get_instance_id()

        # Create deterministic random generator
        seed = int(hashlib.md5(self.instance_id.encode()).hexdigest()[:8], 16)
        self.rng = random.Random(seed)

    def _get_instance_id(self) -> str:
        """Get instance ID from various sources."""
        # Try environment variable first
        instance_id = os.environ.get("INSTANCE_ID")
        if instance_id:
            return instance_id

        # Try EC2 metadata
        try:
            import subprocess

            result = subprocess.run(
                ["ec2-metadata", "--instance-id"], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                return result.stdout.split()[-1]
        except Exception:
            pass

        # Try GCP metadata
        try:
            import subprocess

            result = subprocess.run(
                [
                    "curl",
                    "-s",
                    "-H",
                    "Metadata-Flavor: Google",
                    "http://metadata.google.internal/computeMetadata/v1/instance/id",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                return f"gcp-{result.stdout.strip()}"
        except Exception:
            pass

        # Try Azure metadata
        try:
            import subprocess

            result = subprocess.run(
                [
                    "curl",
                    "-s",
                    "-H",
                    "Metadata: true",
                    "http://169.254.169.254/metadata/instance/compute/vmId?api-version=2021-02-01&format=text",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                return f"azure-{result.stdout.strip()}"
        except Exception:
            pass

        # Fall back to hostname or UUID
        import socket
        import uuid

        hostname = socket.gethostname()
        if hostname and hostname != "localhost":
            return hostname

        return f"node-{str(uuid.uuid4())[:8]}"

    def generate_identity(self) -> Dict[str, Any]:
        """Generate complete node identity."""
        # Select location deterministically
        location = self.rng.choice(self.LOCATIONS)

        # Select sensor deterministically
        sensor = self.rng.choice(self.SENSORS)

        # Generate deterministic variations
        location_offset = self.rng.uniform(-0.01, 0.01)  # ~1km variation
        sensor_serial = f"{sensor['manufacturer'][:2].upper()}{self.rng.randint(1000000, 9999999)}"

        # Create identity
        identity = {
            "node_id": self.instance_id,
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "location": {
                "city": location["city"],
                "state": location["state"],
                "country": "US",  # TODO: Support other countries
                "coordinates": {
                    "latitude": round(location["lat"] + location_offset, 6),
                    "longitude": round(location["lon"] + location_offset, 6),
                },
                "timezone": location["timezone"],
            },
            "sensor": {
                "manufacturer": sensor["manufacturer"],
                "model": sensor["model"],
                "type": sensor["type"],
                "serial_number": sensor_serial,
                "firmware_version": f"{self.rng.randint(1, 5)}.{self.rng.randint(0, 9)}.{self.rng.randint(0, 9)}",
            },
            "deployment": {
                "deployment_date": datetime.utcnow().isoformat() + "Z",
                "environment": "field",
                "power_source": self.rng.choice(["battery", "solar", "mains"]),
                "connectivity": self.rng.choice(["cellular", "wifi", "ethernet"]),
            },
            "metadata": {
                "cloud_provider": self._detect_cloud_provider(),
                "instance_type": self._get_instance_type(),
                "region": self._get_region(),
                "generation_method": "deterministic",
                "generator_version": "2.0.0",
            },
        }

        return identity

    def _detect_cloud_provider(self) -> str:
        """Detect which cloud provider we're running on."""
        if self.instance_id.startswith("i-"):
            return "aws"
        elif self.instance_id.startswith("gcp-"):
            return "gcp"
        elif self.instance_id.startswith("azure-"):
            return "azure"
        else:
            return "unknown"

    def _get_instance_type(self) -> str:
        """Get instance type from metadata or environment."""
        # Try AWS first
        try:
            import subprocess

            result = subprocess.run(
                ["ec2-metadata", "--instance-type"], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                return result.stdout.split()[-1]
        except Exception:
            pass

        # Fall back to environment or default
        return os.environ.get("INSTANCE_TYPE", "t3.medium")

    def _get_region(self) -> str:
        """Get region from metadata or environment."""
        # Try AWS first
        try:
            import subprocess

            result = subprocess.run(
                ["ec2-metadata", "--availability-zone"], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                az = result.stdout.split()[-1]
                return az[:-1] if az and len(az) > 1 else "us-west-2"
        except Exception:
            pass

        # Fall back to environment or default
        return os.environ.get("AWS_DEFAULT_REGION", "us-west-2")


def main():
    """Generate and save node identity."""
    print("Generating node identity...")

    try:
        # Get instance ID from environment or detect
        instance_id = os.environ.get("INSTANCE_ID")
        if not instance_id:
            print("No INSTANCE_ID environment variable set, detecting...")

        # Generate identity
        generator = MultiCloudNodeIdentityGenerator(instance_id)
        identity = generator.generate_identity()

        print(f"✓ Generated identity for node: {identity['node_id']}")
        print(f"✓ Location: {identity['location']['city']}, {identity['location']['state']}")
        print(f"✓ Sensor: {identity['sensor']['manufacturer']} {identity['sensor']['model']}")

        # Create output directory
        output_dir = "/opt/sensor/config"
        os.makedirs(output_dir, exist_ok=True)

        # Write identity file
        output_path = os.path.join(output_dir, "node_identity.json")
        with open(output_path, "w") as f:
            json.dump(identity, f, indent=2)

        print(f"✓ Identity written to: {output_path}")

        # Also write to backup location
        backup_path = "/opt/node_identity_backup.json"
        with open(backup_path, "w") as f:
            json.dump(identity, f, indent=2)

        return 0

    except Exception as e:
        print(f"✗ Failed to generate node identity: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
