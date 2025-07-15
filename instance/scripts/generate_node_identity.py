#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "requests",
#     "hashlib",
# ]
# ///

import hashlib
import json
import os
import random
from datetime import datetime
from typing import Dict, Any, Tuple

class NodeIdentityGenerator:
    """Generate realistic but fake node identities for Bacalhau sensor demo."""
    
    # Real US cities with GPS coordinates and timezone mapping
    US_CITIES = [
        {"name": "San Francisco", "state": "CA", "lat": 37.7749, "lon": -122.4194, "timezone": "America/Los_Angeles"},
        {"name": "Austin", "state": "TX", "lat": 30.2672, "lon": -97.7431, "timezone": "America/Chicago"},
        {"name": "Seattle", "state": "WA", "lat": 47.6062, "lon": -122.3321, "timezone": "America/Los_Angeles"},
        {"name": "Denver", "state": "CO", "lat": 39.7392, "lon": -104.9903, "timezone": "America/Denver"},
        {"name": "Miami", "state": "FL", "lat": 25.7617, "lon": -80.1918, "timezone": "America/New_York"},
        {"name": "Boston", "state": "MA", "lat": 42.3601, "lon": -71.0589, "timezone": "America/New_York"},
        {"name": "Chicago", "state": "IL", "lat": 41.8781, "lon": -87.6298, "timezone": "America/Chicago"},
        {"name": "Atlanta", "state": "GA", "lat": 33.7490, "lon": -84.3880, "timezone": "America/New_York"},
        {"name": "Portland", "state": "OR", "lat": 45.5152, "lon": -122.6784, "timezone": "America/Los_Angeles"},
        {"name": "Phoenix", "state": "AZ", "lat": 33.4484, "lon": -112.0740, "timezone": "America/Phoenix"},
        {"name": "Nashville", "state": "TN", "lat": 36.1627, "lon": -86.7816, "timezone": "America/Chicago"},
        {"name": "San Diego", "state": "CA", "lat": 32.7157, "lon": -117.1611, "timezone": "America/Los_Angeles"},
        {"name": "Dallas", "state": "TX", "lat": 32.7767, "lon": -96.7970, "timezone": "America/Chicago"},
        {"name": "Minneapolis", "state": "MN", "lat": 44.9778, "lon": -93.2650, "timezone": "America/Chicago"},
        {"name": "Charlotte", "state": "NC", "lat": 35.2271, "lon": -80.8431, "timezone": "America/New_York"},
    ]
    
    # Realistic sensor manufacturers and models
    SENSOR_MANUFACTURERS = [
        {"manufacturer": "AcmeSensors", "models": ["EnviroPro-3000", "WeatherSense-XL", "AirQuality-Plus"], "firmware_prefix": "ACME"},
        {"manufacturer": "EcoTech", "models": ["EcoSensor-Pro", "ClimateTracker-500", "GreenMonitor-2"], "firmware_prefix": "ECO"},
        {"manufacturer": "WeatherFlow", "models": ["Tempest-Pro", "SkyTracker-7", "StormWatch-3D"], "firmware_prefix": "WF"},
        {"manufacturer": "SensorMax", "models": ["MaxObserver-4K", "UltraSense-Pro", "PrecisionEnv-8"], "firmware_prefix": "SMX"},
        {"manufacturer": "DataLogger", "models": ["EnviroLogger-360", "ClimateScope-Pro", "AirData-Plus"], "firmware_prefix": "DLG"},
    ]
    
    def __init__(self, instance_id: str):
        """Initialize with EC2 instance ID for deterministic generation."""
        self.instance_id = instance_id
        self.seed = int(hashlib.md5(instance_id.encode()).hexdigest(), 16)
        self.rng = random.Random(self.seed)
    
    def _add_coordinate_noise(self, lat: float, lon: float) -> Tuple[float, float]:
        """Add deterministic noise to coordinates based on instance ID."""
        # Use the seeded RNG for deterministic noise
        lat_noise = self.rng.uniform(-0.01, 0.01)
        lon_noise = self.rng.uniform(-0.01, 0.01)
        return round(lat + lat_noise, 6), round(lon + lon_noise, 6)
    
    def _select_city(self) -> Dict[str, Any]:
        """Select a city based on instance ID hash."""
        city_index = self.seed % len(self.US_CITIES)
        return self.US_CITIES[city_index]
    
    def _generate_sensor_id(self, city: Dict[str, Any]) -> str:
        """Generate unique sensor ID based on region and number."""
        region_code = f"{city['state']}_{city['name'][:3].upper()}"
        # Generate a consistent number based on instance ID
        number = (self.seed // len(self.US_CITIES)) % 9999 + 1
        return f"SENSOR_{region_code}_{number:04d}"
    
    def _select_manufacturer_config(self) -> Dict[str, str]:
        """Select manufacturer and model configuration deterministically."""
        manufacturer_index = (self.seed // 100) % len(self.SENSOR_MANUFACTURERS)
        manufacturer = self.SENSOR_MANUFACTURERS[manufacturer_index]
        
        model_index = (self.seed // 1000) % len(manufacturer["models"])
        model = manufacturer["models"][model_index]
        
        # Generate firmware version deterministically
        major = (self.seed // 10000) % 5 + 1  # 1-5
        minor = (self.seed // 100000) % 20    # 0-19
        patch = (self.seed // 1000000) % 50   # 0-49
        firmware = f"{manufacturer['firmware_prefix']}_v{major}.{minor}.{patch}"
        
        return {
            "manufacturer": manufacturer["manufacturer"],
            "model": model,
            "firmware_version": firmware
        }
    
    def _generate_deployment_info(self) -> Dict[str, Any]:
        """Generate deterministic deployment metadata."""
        deployment_types = ["rooftop", "street_pole", "ground_station", "mobile_unit"]
        deployment_type = deployment_types[self.seed % len(deployment_types)]
        
        # Generate installation date (within last 2 years) - deterministic
        days_ago = self.seed % 730  # ~2 years
        install_date = datetime.fromtimestamp(
            datetime.now().timestamp() - (days_ago * 24 * 3600)
        ).strftime("%Y-%m-%d")
        
        # Use seeded RNG for deterministic values
        height_meters = round(2.0 + (self.seed % 480) / 10.0, 1)  # 2.0-50.0 in 0.1 steps
        orientation_degrees = self.seed % 360
        
        return {
            "deployment_type": deployment_type,
            "installation_date": install_date,
            "height_meters": height_meters,
            "orientation_degrees": orientation_degrees
        }
    
    def generate_identity(self) -> Dict[str, Any]:
        """Generate complete node identity."""
        city = self._select_city()
        lat, lon = self._add_coordinate_noise(city["lat"], city["lon"])
        manufacturer_config = self._select_manufacturer_config()
        deployment_info = self._generate_deployment_info()
        sensor_id = self._generate_sensor_id(city)
        
        identity = {
            "sensor_id": sensor_id,
            "location": {
                "city": city["name"],
                "state": city["state"],
                "coordinates": {
                    "latitude": lat,
                    "longitude": lon
                },
                "timezone": city["timezone"],
                "address": f"{city['name']}, {city['state']}, USA"
            },
            "device_info": {
                **manufacturer_config,
                "serial_number": f"{manufacturer_config['manufacturer']}-{self.seed % 1000000:06d}",
                "manufacture_date": datetime.fromtimestamp(
                    datetime.now().timestamp() - ((self.seed % 365) * 24 * 3600)
                ).strftime("%Y-%m-%d")
            },
            "deployment": deployment_info,
            "metadata": {
                "instance_id": self.instance_id,
                "identity_generation_timestamp": datetime.now().isoformat(),
                "generation_seed": self.seed,
                "sensor_type": "environmental_monitoring"
            }
        }
        
        return identity
    
    def save_identity(self, output_path: str) -> bool:
        """Save identity to JSON file."""
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            identity = self.generate_identity()
            
            with open(output_path, 'w') as f:
                json.dump(identity, f, indent=2)
            
            return True
        except Exception as e:
            print(f"Error saving identity: {e}")
            return False


def get_instance_id() -> str:
    """Get EC2 instance ID from metadata service."""
    import subprocess
    try:
        response = subprocess.check_output(['curl', '-s', 'http://169.254.169.254/latest/meta-data/instance-id'])
        return response.decode('utf-8').strip()
    except Exception:
        # Fallback for testing
        return "i-1234567890abcdef0"


def main():
    """Main function to generate and save node identity."""
    instance_id = get_instance_id()
    generator = NodeIdentityGenerator(instance_id)
    
    output_path = "/opt/sensor/config/node_identity.json"
    
    print(f"Generating node identity for instance: {instance_id}")
    identity = generator.generate_identity()
    
    print(f"Selected location: {identity['location']['address']}")
    print(f"Sensor ID: {identity['sensor_id']}")
    print(f"Device: {identity['device_info']['manufacturer']} {identity['device_info']['model']}")
    
    if generator.save_identity(output_path):
        print(f"Node identity saved to: {output_path}")
        return True
    else:
        print("Failed to save node identity")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)