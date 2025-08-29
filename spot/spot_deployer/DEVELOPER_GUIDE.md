# Developer Guide

This guide explains how to work with the Spot Deployer codebase and extend its functionality.

## Architecture Overview

The codebase follows a manager pattern where specialized managers handle different domains:

```
Commands (CLI) → Managers → AWS/SSH/UI Operations
```

## Adding a New Command

1. Create a new file in `spot_deployer/commands/`
2. Implement the command function:

```python
from ..core.config import SimpleConfig
from ..core.state import SimpleStateManager
from ..utils.aws import check_aws_auth
from ..utils.display import console

def cmd_mycommand(config: SimpleConfig, state: SimpleStateManager) -> None:
    """My new command implementation."""
    if not check_aws_auth():
        return

    # Your command logic here
    console.print("[green]Command executed successfully![/green]")
```

3. Add to `main.py`:

```python
from .commands.mycommand import cmd_mycommand

# In the main() function
elif command == "mycommand":
    cmd_mycommand(config, state)
```

## Using the Managers

### AWS Operations

Always use `AWSResourceManager` for AWS operations:

```python
from ..utils.aws_manager import AWSResourceManager

# Create manager for a region
aws_manager = AWSResourceManager("us-west-2")

# Find or create VPC
vpc_id, subnet_id = aws_manager.find_or_create_vpc(
    use_dedicated=True,
    deployment_id="my-deployment"
)

# Create security group
sg_id = aws_manager.create_security_group(vpc_id)

# Terminate instance (with built-in retry)
success = aws_manager.terminate_instance(instance_id)

# Get instance state
state = aws_manager.get_instance_state(instance_id)
```

### SSH Operations

Use `SSHManager` for single hosts or `BatchSSHManager` for multiple:

```python
from ..utils.ssh_manager import SSHManager, BatchSSHManager

# Single host
ssh = SSHManager(hostname, username, private_key_path)

# Wait for SSH (with timeout)
if ssh.wait_for_ssh(timeout=300):
    # Execute command with retry
    success, stdout, stderr = ssh.execute_command("ls -la")

    # Transfer file with retry
    ssh.transfer_file("/local/file", "/remote/path")

# Multiple hosts
hosts = [
    {"hostname": "host1", "username": "ubuntu"},
    {"hostname": "host2", "username": "ubuntu"}
]
batch_ssh = BatchSSHManager(hosts, private_key_path)

# Execute on all hosts
results = batch_ssh.execute_on_all("uptime")
for hostname, (success, stdout, stderr) in results.items():
    print(f"{hostname}: {stdout}")
```

### UI Operations

Use `UIManager` for consistent terminal output:

```python
from ..utils.ui_manager import UIManager
from rich.layout import Layout
from rich.table import Table

ui = UIManager()

# Status messages
ui.print_success("Operation completed!")
ui.print_error("Operation failed!")
ui.print_warning("Check your configuration")
ui.print_info("Processing...")

# Progress bar
with ui.create_progress_bar("Uploading files", total=100) as progress:
    task = progress.add_task("Upload", total=100)
    for i in range(100):
        progress.update(task, advance=1)

# Live display with layout
table = Table(title="Instances")
layout = Layout()
layout.split_column(
    Layout(table, ratio=4),
    Layout(log_panel, size=10)
)

with ui.create_live_display(layout) as live:
    # Update display
    live.update(layout)
```

## Error Handling Best Practices

### 1. Use Specific Exceptions

```python
from botocore.exceptions import ClientError

try:
    ec2.terminate_instances(InstanceIds=[instance_id])
except ClientError as e:
    error_code = e.response.get("Error", {}).get("Code", "")
    if error_code == "InvalidInstanceID.NotFound":
        # Instance already gone - not an error
        return True
    elif error_code == "UnauthorizedOperation":
        # Permission issue
        raise
    else:
        # Log and handle appropriately
        logger.error(f"AWS error: {error_code}")
        raise
```

### 2. Implement Retry Logic

```python
def operation_with_retry(max_retries=3):
    for attempt in range(max_retries):
        try:
            # Your operation
            result = risky_operation()
            return result
        except RetryableError as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff
                logger.info(f"Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                raise
```

### 3. Handle Rate Limiting

```python
except ClientError as e:
    error_code = e.response.get("Error", {}).get("Code", "")
    if error_code in ["RequestLimitExceeded", "Throttling"]:
        # These are retryable
        time.sleep(2 ** retry_count)
        continue
    else:
        raise
```

## Testing

### Unit Tests

Create tests in `tests/` directory:

```python
import pytest
from spot_deployer.utils.aws_manager import AWSResourceManager

def test_aws_manager_initialization():
    manager = AWSResourceManager("us-west-2")
    assert manager.region == "us-west-2"
    assert manager._ec2 is None  # Lazy loaded

@pytest.mark.parametrize("error_code,expected", [
    ("InvalidInstanceID.NotFound", True),
    ("UnauthorizedOperation", False),
])
def test_terminate_instance_error_handling(error_code, expected):
    # Test error handling
    pass
```

### Integration Tests

For testing with real AWS:

```python
@pytest.mark.integration
@pytest.mark.skipif(not os.environ.get("AWS_PROFILE"),
                    reason="AWS credentials required")
def test_real_aws_operations():
    manager = AWSResourceManager("us-west-2")
    # Real AWS operations
```

## Common Patterns

### 1. Progress Tracking

```python
def long_operation(instances, progress_callback):
    total = len(instances)
    for i, instance in enumerate(instances):
        # Do work
        process_instance(instance)

        # Update progress
        if progress_callback:
            progress_callback(i + 1, total, f"Processing {instance['id']}")
```

### 2. Concurrent Operations

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def process_regions_concurrently(regions):
    results = {}

    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_region = {
            executor.submit(process_region, region): region
            for region in regions
        }

        for future in as_completed(future_to_region):
            region = future_to_region[future]
            try:
                result = future.result()
                results[region] = result
            except Exception as e:
                logger.error(f"Failed to process {region}: {e}")
                results[region] = None

    return results
```

### 3. State Management

```python
# Always use locks when updating shared state
from threading import Lock

state_lock = Lock()

def update_instance_state(instance_id, new_state):
    with state_lock:
        instances = state.load_instances()
        for inst in instances:
            if inst["id"] == instance_id:
                inst["state"] = new_state
                break
        state.save_instances(instances)
```

## Performance Tips

1. **Lazy Loading**: Initialize expensive resources only when needed
2. **Caching**: Use file-based caching for AMI lookups
3. **Batch Operations**: Process multiple items in parallel
4. **Connection Reuse**: Maintain SSH connections for multiple operations
5. **Async Progress**: Update UI asynchronously from worker threads

## Security Guidelines

1. **Never hardcode credentials**
2. **Validate all user input**
3. **Use least-privilege IAM policies**
4. **Sanitize log output** (no secrets in logs)
5. **Validate file paths** to prevent directory traversal

## Debugging

### Enable Debug Logging

```python
# Set environment variable
export SPOT_DEBUG=1

# Or in code
import logging
logging.getLogger("spot_deployer").setLevel(logging.DEBUG)
```

### Common Issues

1. **SSH Connection Failures**
   - Check security group rules
   - Verify key permissions (600)
   - Check instance state

2. **AWS Rate Limiting**
   - Implement exponential backoff
   - Reduce concurrent operations
   - Use different regions

3. **Spot Capacity Issues**
   - Try different instance types
   - Try different availability zones
   - Check spot pricing history
