# Spot Deployer Architecture

## Overview

Spot Deployer is a modern AWS spot instance deployment tool designed with a clean, modular architecture. The codebase follows best practices for maintainability, testability, and extensibility.

## Core Architecture Principles

1. **Manager Pattern**: Centralized managers handle specific domains (AWS, SSH, UI)
2. **Separation of Concerns**: Each module has a single, well-defined responsibility
3. **Retry Logic**: Built-in resilience with exponential backoff for network operations
4. **Type Safety**: Full type annotations throughout the codebase
5. **Error Handling**: Specific error handling with proper error codes

## Directory Structure

```
spot_deployer/
├── commands/           # CLI command implementations
│   ├── create.py      # Instance creation command
│   ├── destroy.py     # Instance termination command
│   ├── list.py        # List instances command
│   ├── nuke.py        # Nuclear cleanup command
│   └── setup.py       # Configuration setup command
├── core/              # Core functionality
│   ├── config.py      # Configuration management
│   ├── constants.py   # Global constants
│   └── state.py       # State management
├── utils/             # Utility modules
│   ├── aws_manager.py # AWS resource management
│   ├── ssh_manager.py # SSH connection management
│   ├── ui_manager.py  # Terminal UI management
│   ├── display.py     # Rich display utilities
│   ├── tables.py      # Table formatting
│   ├── logging.py     # Logging utilities
│   └── bacalhau.py    # Bacalhau-specific utilities
└── main.py            # Entry point
```

## Key Components

### 1. AWS Manager (`utils/aws_manager.py`)

Centralized AWS operations management with built-in retry logic.

```python
class AWSResourceManager:
    """Manages all AWS resource operations for spot instances."""

    def __init__(self, region: str)
    def find_or_create_vpc(use_dedicated: bool, deployment_id: Optional[str]) -> Tuple[str, str]
    def create_security_group(vpc_id: str) -> str
    def find_ubuntu_ami(ami_pattern: str) -> Optional[str]
    def terminate_instance(instance_id: str) -> bool
    def delete_vpc_resources(vpc_id: str) -> bool
```

**Features:**
- Lazy-loaded EC2 clients for performance
- Adaptive retry mode with 3 attempts
- Connection timeout: 10 seconds
- Read timeout: 60 seconds
- Specific error code handling

### 2. SSH Manager (`utils/ssh_manager.py`)

Centralized SSH and file transfer operations.

```python
class SSHManager:
    """Manages SSH connections and file transfers to instances."""

    def wait_for_ssh(timeout: int) -> bool
    def execute_command(command: str, timeout: int, retries: int) -> Tuple[bool, str, str]
    def transfer_file(local_path: str, remote_path: str) -> bool
    def transfer_directory(local_path: str, remote_path: str) -> bool

class BatchSSHManager:
    """Manages SSH operations across multiple hosts concurrently."""

    def wait_for_all_ssh(timeout: int) -> Dict[str, bool]
    def execute_on_all(command: str) -> Dict[str, Tuple[bool, str, str]]
    def transfer_to_all(local_path: str, remote_path: str) -> Dict[str, bool]
```

**Features:**
- Built-in retry logic with exponential backoff
- Connection pooling for batch operations
- Configurable timeouts and retries
- Server keepalive for long operations

### 3. UI Manager (`utils/ui_manager.py`)

Unified terminal UI management using Rich.

```python
class UIManager:
    """Centralized UI management for consistent terminal output."""

    def print_success(message: str)
    def print_error(message: str)
    def print_warning(message: str)
    def print_info(message: str)
    def create_live_display(layout: Layout) -> Live
    def create_progress_bar(description: str, total: int)
```

**Features:**
- Consistent styling across all commands
- Full-screen layouts with split panels
- Live updating tables and progress bars
- Proper Unicode emoji support

## Command Flow

### Create Command Flow

1. **Configuration**: Load and validate configuration
2. **AWS Setup**:
   - Find/create VPC using `AWSResourceManager`
   - Create security groups
   - Find Ubuntu AMI (with caching)
3. **Instance Creation**:
   - Request spot instances with retry logic
   - Handle rate limiting with exponential backoff
   - Save state immediately after creation
4. **Post-Creation**:
   - Wait for SSH using `SSHManager`
   - Transfer files with automatic retry
   - Update state file

### Destroy Command Flow

1. **State Loading**: Load instances from state file
2. **Bacalhau Cleanup**:
   - Check for disconnected nodes
   - Remove nodes with retry logic
3. **Instance Termination**:
   - Terminate instances using `AWSResourceManager`
   - Handle already-terminated instances gracefully
4. **VPC Cleanup**:
   - Delete dedicated VPCs if configured
   - Clean up all associated resources

## Error Handling Strategy

### Retryable Errors
- `RequestLimitExceeded`: AWS rate limiting
- `Throttling`: API throttling
- Connection timeouts
- SSH connection failures

### Terminal Errors
- `InsufficientInstanceCapacity`: No spot capacity
- `SpotMaxPriceTooLow`: Price too low
- `InvalidInstanceID.NotFound`: Instance doesn't exist
- Authentication failures

### Retry Logic
```python
# Exponential backoff pattern used throughout
for attempt in range(max_retries):
    try:
        # Operation
        if success:
            break
    except RetryableError:
        if attempt < max_retries - 1:
            time.sleep(2 ** attempt)  # 2, 4, 8 seconds
        else:
            raise
```

## State Management

### State File Structure (`instances.json`)
```json
{
  "instances": [
    {
      "id": "i-1234567890abcdef0",
      "region": "us-west-2",
      "type": "t3.medium",
      "public_ip": "54.123.45.67",
      "private_ip": "10.0.1.23",
      "state": "running",
      "created": "2024-01-15T10:30:00Z",
      "deployment_id": "spot-deploy-1234567890",
      "vpc_id": "vpc-abc123",
      "creator": "user@example.com"
    }
  ]
}
```

## Performance Optimizations

1. **Lazy Loading**: EC2 clients created only when needed
2. **Parallel Operations**: ThreadPoolExecutor for concurrent operations
3. **AMI Caching**: Local cache for AMI lookups
4. **Batch Operations**: Process multiple instances/regions concurrently
5. **Connection Reuse**: SSH connections maintained for multiple operations

## Security Considerations

1. **Credential Handling**:
   - No hardcoded credentials
   - Support for AWS SSO, profiles, and IAM roles
   - Secure credential file handling
2. **SSH Security**:
   - StrictHostKeyChecking disabled only for automation
   - Private key permissions validated
   - No password authentication
3. **Network Security**:
   - Security groups with minimal required ports
   - VPC isolation option
   - No public S3 buckets

## Future Enhancements

1. **Plugin System**: Support for custom deployment plugins
2. **Multi-Cloud**: Abstract managers for other cloud providers
3. **Monitoring**: Built-in CloudWatch integration
4. **Auto-Scaling**: Dynamic instance scaling based on load
5. **Cost Optimization**: Spot price analysis and recommendations
