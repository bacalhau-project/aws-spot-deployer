# New Log Commands

I've added two new commands to the deploy_spot.py tool:

## 1. `print-log` - Print Basic Startup Log

```bash
uv run -s deploy_spot.py print-log
```

This command:
- Selects a random running instance
- Fetches and displays the `/opt/startup.log` file
- Shows all service startup messages in chronological order
- Quick way to see what happened during instance setup

## 2. `debug-log` - Print Comprehensive Debug Information

```bash
uv run -s deploy_spot.py debug-log
```

This command collects and displays:
- System information (hostname, uptime)
- Status of all 4 systemd services:
  - bacalhau-startup.service (initial setup)
  - setup-config.service (configuration setup)
  - bacalhau.service (Bacalhau node)
  - sensor-generator.service (sensor log generator)
- Docker status and running containers
- Last 50 lines of `/opt/startup.log`
- Configuration file checks
- Cloud-init status

## Usage Examples

### After creating instances, wait 5 minutes then:

Check basic startup log:
```bash
uv run -s deploy_spot.py print-log
```

Get full debug information:
```bash
uv run -s deploy_spot.py debug-log
```

### Save logs to file:

```bash
uv run -s deploy_spot.py print-log > startup.log
uv run -s deploy_spot.py debug-log > debug_info.txt
```

## Notes

- Both commands randomly select from running instances
- Requires instances to have public IPs
- Uses your configured SSH key automatically
- All services now log to `/opt/startup.log` for centralized logging
- Wait at least 5 minutes after instance creation for cloud-init to complete

## What You'll See

The `/opt/startup.log` file contains output from:
1. Initial cloud-init setup
2. Initial system setup script
3. Configuration setup service
4. Bacalhau service startup
5. Sensor generator service startup

All timestamped and in chronological order!