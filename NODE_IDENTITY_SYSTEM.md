# Node Identity Generation System for Bacalhau Sensor Demo

## Overview

This system generates realistic but fake node identities for environmental sensor nodes in the Bacalhau distributed computing demo. The identities are deterministic based on EC2 instance IDs, ensuring consistent identities across reboots.

## Components

### 1. Identity Generator Script
- **File**: `instance/scripts/generate_node_identity.py`
- **Purpose**: Generates complete node identity JSON files
- **Output**: `/opt/sensor/config/node_identity.json`

### 2. Integration with Startup
- **File**: `instance/scripts/startup.py`
- **Integration**: Automatically generates identity during startup
- **Location**: Identity generation runs after Docker Compose setup

## Identity Structure

Each generated identity includes:

```json
{
  "sensor_id": "SENSOR_[REGION]_[NUMBER]",
  "location": {
    "city": "Real US city name",
    "state": "US state code",
    "coordinates": {
      "latitude": 36.17043,
      "longitude": -86.78651
    },
    "timezone": "America/Chicago",
    "address": "City, State, USA"
  },
  "device_info": {
    "manufacturer": "AcmeSensors",
    "model": "EnviroPro-3000",
    "firmware_version": "ACME_v3.3.2",
    "serial_number": "AcmeSensors-324085",
    "manufacture_date": "2025-04-19"
  },
  "deployment": {
    "deployment_type": "street_pole|rooftop|ground_station|mobile_unit",
    "installation_date": "2025-04-19",
    "height_meters": 10.5,
    "orientation_degrees": 325
  },
  "metadata": {
    "instance_id": "i-1234567890abcdef0",
    "identity_generation_timestamp": "2025-07-13T12:04:50.704513",
    "generation_seed": 263662312046034352660800051568002324085,
    "sensor_type": "environmental_monitoring"
  }
}
```

## Features

### Deterministic Generation
- Based on EC2 instance ID
- Same instance ID always produces same identity
- Useful for consistent testing and debugging

### Realistic Data
- **Cities**: 15 major US cities with real GPS coordinates
- **Manufacturers**: 5 realistic sensor manufacturers with authentic model names
- **Firmware**: Realistic versioning with prefixes (ACME, ECO, WF, SMX, DLG)
- **Deployment**: Realistic deployment types and parameters

### Location Coverage
- San Francisco, CA (Pacific timezone)
- Austin, TX (Central timezone)
- Seattle, WA (Pacific timezone)
- Denver, CO (Mountain timezone)
- Miami, FL (Eastern timezone)
- Boston, MA (Eastern timezone)
- Chicago, IL (Central timezone)
- Atlanta, GA (Eastern timezone)
- Portland, OR (Pacific timezone)
- Phoenix, AZ (Arizona timezone)
- Nashville, TN (Central timezone)
- San Diego, CA (Pacific timezone)
- Dallas, TX (Central timezone)
- Minneapolis, MN (Central timezone)
- Charlotte, NC (Eastern timezone)

## Usage

### Manual Generation
```bash
# Run identity generator directly
python3 instance/scripts/generate_node_identity.py

# Output will be saved to /opt/sensor/config/node_identity.json
```

### Test Mode
```bash
# Run comprehensive tests
python3 test_identity_generation.py
```

### Automatic Integration
The identity generation is automatically triggered during instance startup via the `startup.py` script.

## Testing

The system includes comprehensive testing:

- **Determinism**: Same instance ID produces identical results
- **Structure validation**: JSON schema compliance
- **Location validation**: Realistic coordinates
- **File generation**: Proper file creation and saving
- **Round-trip testing**: Save/load consistency

## Customization

### Adding New Cities
Edit the `US_CITIES` list in `generate_node_identity.py`:

```python
US_CITIES = [
    {"name": "New City", "state": "ST", "lat": 40.7128, "lon": -74.0060, "timezone": "America/New_York"},
    # ... existing cities
]
```

### Adding New Manufacturers
Edit the `SENSOR_MANUFACTURERS` list:

```python
SENSOR_MANUFACTURERS = [
    {"manufacturer": "NewCorp", "models": ["Model1", "Model2"], "firmware_prefix": "NC"},
    # ... existing manufacturers
]
```

## Troubleshooting

### Common Issues

1. **Permission denied writing to `/opt/sensor/config/`**
   - Ensure directory exists: `sudo mkdir -p /opt/sensor/config/`
   - Set permissions: `sudo chmod 755 /opt/sensor/config/`

2. **Instance ID not available**
   - Script falls back to `i-1234567890abcdef0` for testing
   - Ensure EC2 metadata service is accessible

3. **Python dependencies missing**
   - Standard library only (hashlib, json, random, datetime)
   - No external dependencies required

### Verification

Check generated identity:
```bash
cat /opt/sensor/config/node_identity.json | jq .
```

Test with specific instance ID:
```bash
INSTANCE_ID=i-0a1b2c3d4e5f6789a python3 instance/scripts/generate_node_identity.py
```