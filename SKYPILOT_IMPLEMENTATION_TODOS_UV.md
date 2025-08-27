# SkyPilot Implementation - Step-by-Step TODO List (UV Edition)

## Overview
This document provides granular, sequential tasks for migrating from the current custom AWS spot deployment tool to SkyPilot. Each task is designed to be completed independently and in order. All Python operations use `uv` exclusively.

## Phase 1: Environment Setup (Day 1)

### 1.1 Install SkyPilot with UV
```bash
# Task: Create a uv script for SkyPilot installation
cat << 'EOF' > install_skypilot.py
#!/usr/bin/env -S uv run -s
# /// script
# dependencies = ["skypilot[aws]"]
# ///

import sky

def main():
    print(f"SkyPilot version: {sky.__version__}")
    print("Running sky check...")
    import subprocess
    subprocess.run(["sky", "check"], check=True)

if __name__ == "__main__":
    main()
EOF

chmod +x install_skypilot.py
./install_skypilot.py
```
**Verification**: Script runs and shows SkyPilot version

### 1.2 Configure AWS Credentials for SkyPilot
```bash
# Task: Create AWS credential checker with uv
cat << 'EOF' > check_aws.py
#!/usr/bin/env -S uv run -s
# /// script
# dependencies = ["boto3", "rich"]
# ///

import boto3
from rich.console import Console
from rich.table import Table

console = Console()

def check_credentials():
    try:
        session = boto3.Session()
        credentials = session.get_credentials()

        if credentials:
            sts = boto3.client('sts')
            identity = sts.get_caller_identity()

            table = Table(title="AWS Configuration")
            table.add_column("Property", style="cyan")
            table.add_column("Value", style="green")

            table.add_row("Account ID", identity['Account'])
            table.add_row("User ARN", identity['Arn'])
            table.add_row("Access Key", credentials.access_key[:10] + "...")

            console.print(table)
            return True
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        return False

    return False

if __name__ == "__main__":
    import sys
    sys.exit(0 if check_credentials() else 1)
EOF

chmod +x check_aws.py
./check_aws.py
```
**Verification**: AWS credentials are displayed

### 1.3 Create Project Backup
```bash
# Task: Create a backup branch and tag
git checkout -b pre-skypilot-migration
git add .
git commit -m "Backup before SkyPilot migration"
git tag pre-skypilot-backup
```
**Verification**: `git tag -l` shows the backup tag

### 1.4 Create New Directory Structure
```bash
# Task: Create SkyPilot directories
mkdir -p skypilot-tasks
mkdir -p sky-cli
mkdir -p deployment-new/etc/bacalhau
mkdir -p deployment-new/opt/bacalhau
mkdir -p deployment-new/opt/sensor/config
mkdir -p deployment-new/scripts
mkdir -p features/step_definitions
mkdir -p features/support
```
**Verification**: `tree skypilot-tasks deployment-new features` shows structure

## Phase 2: Basic SkyPilot Task Creation (Day 2)

### 2.1 Create SkyPilot Task Validator
```python
# Task: Create validate_task.py
cat << 'EOF' > validate_task.py
#!/usr/bin/env -S uv run -s
# /// script
# dependencies = ["pyyaml", "skypilot[aws]", "rich"]
# ///

import yaml
import sys
from pathlib import Path
from rich.console import Console

console = Console()

def validate_skypilot_task(task_file: str):
    """Validate a SkyPilot task YAML file."""
    try:
        with open(task_file, 'r') as f:
            task = yaml.safe_load(f)

        # Check required fields
        required = ['name', 'resources', 'run']
        missing = [f for f in required if f not in task]

        if missing:
            console.print(f"[red]Missing required fields: {missing}[/red]")
            return False

        console.print(f"[green]✓ Task '{task['name']}' is valid[/green]")
        return True

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        return False

if __name__ == "__main__":
    if len(sys.argv) != 2:
        console.print("Usage: ./validate_task.py <task.yaml>")
        sys.exit(1)

    sys.exit(0 if validate_skypilot_task(sys.argv[1]) else 1)
EOF

chmod +x validate_task.py
```
**Verification**: Script validates YAML files

### 2.2 Create Minimal SkyPilot Task
```yaml
# Task: Create skypilot-tasks/test-minimal.yaml
name: bacalhau-test-minimal

resources:
  cloud: aws
  region: us-west-2
  instance_type: t3.small
  use_spot: true

run: |
  echo "SkyPilot node is running!"
  uname -a
  docker --version || echo "Docker not installed"
```
**Verification**: `./validate_task.py skypilot-tasks/test-minimal.yaml`

## Phase 3: Port Configuration Scripts (Day 3)

### 3.1 Create Bacalhau Config Generator with UV
```python
# Task: Create deployment-new/scripts/generate_bacalhau_config.py
cat << 'EOF' > deployment-new/scripts/generate_bacalhau_config.py
#!/usr/bin/env -S uv run -s
# /// script
# dependencies = ["pyyaml", "rich"]
# ///

import os
import yaml
import sys
from pathlibением Path
from rich.console import Console

console = Console()

def generate_config():
    """Generate Bacalhau configuration from orchestrator credentials."""
    endpoint_file = Path('/etc/bacalhau/orchestrator_endpoint')
    token_file = Path('/etc/bacalhau/orchestrator_token')
    config_file = Path('/etc/bacalhau/config.yaml')

    if not endpoint_file.exists():
        console.print("[yellow]Warning: orchestrator_endpoint file not found[/yellow]")
        return False

    endpoint = endpoint_file.read_text().strip()
    console.print(f"[cyan]Endpoint: {endpoint}[/cyan]")

    token = ""
    if token_file.exists():
        token = token_file.read_text().strip()
        console.print("[cyan]Token: [hidden][/cyan]")

    config = {
        'node': {
            'type': 'compute',
            'orchestrator': {
                'endpoint': endpoint,
                'token': token
            },
            'compute': {
                'enabled': True,
                'engines': {
                    'docker': {'enabled': True}
                }
            },
            'disableanalytics': True,
            'loglevel': 'info'
        }
    }

    config_file.parent.mkdir(parents=True, exist_ok=True)
    with open(config_file, 'w') as f:
        yaml.dump(config, f, default_flow_style=False)

    console.print(f"[green]✓ Generated {config_file}[/green]")
    return True

if __name__ == '__main__':
    sys.exit(0 if generate_config() else 1)
EOF

chmod +x deployment-new/scripts/generate_bacalhau_config.py
```
**Verification**: Script has proper uv shebang and dependencies

### 3.2 Port Node Identity Generator with UV
```python
# Task: Create deployment-new/opt/sensor/generate_node_identity.py
cat << 'EOF' > deployment-new/opt/sensor/generate_node_identity.py
#!/usr/bin/env -S uv run -s
# /// script
# dependencies = ["faker", "rich"]
# ///

import os
import json
import hashlib
import random
from pathlib import Path
from rich.console import Console

console = Console()

def generate_deterministic_identity():
    """Generate deterministic sensor identity based on instance ID."""
    instance_id = os.environ.get('INSTANCE_ID', 'local-dev')

    # Use instance ID as seed for deterministic generation
    seed = int(hashlib.md5(instance_id.encode()).hexdigest(), 16)
    random.seed(seed)

    # US cities with coordinates
    cities = [
        {"city": "New York", "state": "NY", "lat": 40.7128, "lon": -74.0060},
        {"city": "Los Angeles", "state": "CA", "lat": 34.0522, "lon": -118.2437},
        {"city": "Chicago", "state": "IL", "lat": 41.8781, "lon": -87.6298},
        {"city": "Houston", "state": "TX", "lat": 29.7604, "lon": -95.3698},
        {"city": "Phoenix", "state": "AZ", "lat": 33.4484, "lon": -112.0740},
    ]

    location = random.choice(cities)

    identity = {
        "node_id": f"sensor-{instance_id[:8]}",
        "location": location,
        "sensor": {
            "type": "environmental",
            "manufacturer": random.choice(["Bosch", "Honeywell", "Siemens"]),
            "model": f"ENV-{random.randint(1000, 9999)}"
        }
    }

    output_file = Path('/opt/sensor/config/node_identity.json')
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w') as f:
        json.dump(identity, f, indent=2)

    console.print(f"[green]✓ Generated identity for {instance_id}[/green]")
    console.print(f"[cyan]Node ID: {identity['node_id']}[/cyan]")
    console.print(f"[cyan]Location: {location['city']}, {location['state']}[/cyan]")

    return True

if __name__ == '__main__':
    import sys
    sys.exit(0 if generate_deterministic_identity() else 1)
EOF

chmod +x deployment-new/opt/sensor/generate_node_identity.py
```
**Verification**: `INSTANCE_ID=test ./deployment-new/opt/sensor/generate_node_identity.py`

## Phase 4: CLI Wrapper with UV (Day 4)

### 4.1 Create SkyPilot CLI Wrapper
```python
# Task: Create sky-cli/sky-deploy.py
cat << 'EOF' > sky-cli/sky-deploy.py
#!/usr/bin/env -S uv run -s
# /// script
# dependencies = ["click", "pyyaml", "rich", "skypilot[aws]"]
# ///

import click
import yaml
import subprocess
from pathlib import Path
from rich.console import Console
from rich.table import Table

console = Console()

TASK_FILE = "skypilot-tasks/bacalhau-node.yaml"
CLUSTER_NAME = "bacalhau-cluster"

@click.group()
def cli():
    """SkyPilot deployment CLI for Bacalhau nodes."""
    pass

@cli.command()
@click.option('--nodes', default=1, help='Number of nodes to deploy')
@click.option('--dry-run', is_flag=True, help='Show what would be deployed')
def create(nodes, dry_run):
    """Create a new Bacalhau cluster."""
    console.print(f"[cyan]Creating cluster with {nodes} nodes...[/cyan]")

    # Update task file with node count
    task_path = Path(TASK_FILE)
    if task_path.exists():
        with open(task_path, 'r') as f:
            task = yaml.safe_load(f)

        task['resources']['num_nodes'] = nodes

        if dry_run:
            console.print("[yellow]Dry run - would deploy:[/yellow]")
            console.print(yaml.dump(task, default_flow_style=False))
            return

        # Write updated task
        with open(task_path, 'w') as f:
            yaml.dump(task, f, default_flow_style=False)

    cmd = ['sky', 'launch', '-c', CLUSTER_NAME, TASK_FILE, '-y']
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        console.print("[green]✓ Cluster created successfully[/green]")
    else:
        console.print(f"[red]✗ Failed: {result.stderr}[/red]")

@cli.command()
def list():
    """List cluster status."""
    cmd = ['sky', 'status', CLUSTER_NAME]
    subprocess.run(cmd)

@cli.command()
@click.confirmation_option(prompt='Are you sure you want to destroy the cluster?')
def destroy():
    """Destroy the Bacalhau cluster."""
    console.print("[yellow]Destroying cluster...[/yellow]")
    cmd = ['sky', 'down', CLUSTER_NAME, '-y']
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        console.print("[green]✓ Cluster destroyed[/green]")
    else:
        console.print(f"[red]✗ Failed: {result.stderr}[/red]")

@cli.command()
@click.argument('node_index', type=int, default=0)
def ssh(node_index):
    """SSH into a cluster node."""
    cmd = ['sky', 'ssh', CLUSTER_NAME, '--node', str(node_index)]
    subprocess.run(cmd)

@cli.command()
@click.argument('service', type=click.Choice(['bacalhau', 'sensor', 'all']))
def logs(service):
    """View service logs."""
    if service == 'bacalhau' or service == 'all':
        cmd = ['sky', 'exec', CLUSTER_NAME,
               'sudo docker logs --tail 50 bacalhau_compute_1']
        subprocess.run(cmd)

    if service == 'sensor' or service == 'all':
        cmd = ['sky', 'exec', CLUSTER_NAME,
               'sudo docker logs --tail 50 sensor_simulators_1']
        subprocess.run(cmd)

@cli.command()
def health():
    """Check cluster health."""
    console.print("[cyan]Checking cluster health...[/cyan]")

    checks = [
        ('Docker Status', 'sudo docker ps'),
        ('Bacalhau Version', 'sudo docker exec $(sudo docker ps -q -f name=compute) bacalhau version'),
        ('Node List', 'sudo docker exec $(sudo docker ps -q -f name=compute) bacalhau node list'),
        ('Disk Usage', 'df -h /'),
        ('Memory', 'free -h')
    ]

    table = Table(title="Health Check Results")
    table.add_column("Check", style="cyan")
    table.add_column("Status", style="green")

    for check_name, check_cmd in checks:
        cmd = ['sky', 'exec', CLUSTER_NAME, check_cmd]
        result = subprocess.run(cmd, capture_output=True, text=True)
        status = "✓ OK" if result.returncode == 0 else "✗ Failed"
        table.add_row(check_name, status)

    console.print(table)

if __name__ == '__main__':
    cli()
EOF

chmod +x sky-cli/sky-deploy.py
```
**Verification**: `./sky-cli/sky-deploy.py --help` shows commands

## Phase 5: Testing Framework with UV (Day 5)

### 5.1 Create Test Runner
```python
# Task: Create test_deployment.py
cat << 'EOF' > test_deployment.py
#!/usr/bin/env -S uv run -s
# /// script
# dependencies = ["pytest", "pytest-asyncio", "rich", "boto3"]
# ///

import pytest
import subprocess
import time
from pathlib import Path
from rich.console import Console

console = Console()

class TestSkyPilotDeployment:
    @pytest.fixture(scope="class")
    def cluster(self):
        """Deploy a test cluster."""
        console.print("[cyan]Setting up test cluster...[/cyan]")
        subprocess.run(['./sky-cli/sky-deploy.py', 'create', '--nodes', '1'],
                      check=True)
        time.sleep(120)  # Wait for services to start
        yield
        console.print("[yellow]Tearing down test cluster...[/yellow]")
        subprocess.run(['./sky-cli/sky-deploy.py', 'destroy'], check=True)

    def test_docker_running(self, cluster):
        """Test that Docker is running."""
        result = subprocess.run(
            ['sky', 'exec', 'bacalhau-cluster', 'sudo docker ps'],
            capture_output=True, text=True
        )
        assert result.returncode == 0
        assert 'CONTAINER ID' in result.stdout

    def test_bacalhau_service(self, cluster):
        """Test that Bacalhau service is running."""
        result = subprocess.run(
            ['sky', 'exec', 'bacalhau-cluster',
             'sudo docker ps --filter name=compute --format "{{.Names}}"'],
            capture_output=True, text=True
        )
        assert 'compute' in result.stdout

    def test_sensor_service(self, cluster):
        """Test that sensor service is running."""
        result = subprocess.run(
            ['sky', 'exec', 'bacalhau-cluster',
             'sudo docker ps --filter name=sensor --format "{{.Names}}"'],
            capture_output=True, text=True
        )
        assert 'sensor' in result.stdout

    def test_node_identity(self, cluster):
        """Test that node identity was generated."""
        result = subprocess.run(
            ['sky', 'exec', 'bacalhau-cluster',
             'test -f /opt/sensor/config/node_identity.json && echo "exists"'],
            capture_output=True, text=True
        )
        assert 'exists' in result.stdout

if __name__ == "__main__":
    pytest.main([__file__, '-v'])
EOF

chmod +x test_deployment.py
```
**Verification**: Script runs with pytest

## Phase 6: Health Check System (Day 6)

### 6.1 Create Health Monitor
```python
# Task: Create deployment-new/scripts/health_monitor.py
cat << 'EOF' > deployment-new/scripts/health_monitor.py
#!/usr/bin/env -S uv run -s
# /// script
# dependencies = ["psutil", "rich", "pyyaml"]
# ///

import json
import subprocess
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel

console = Console()

def get_docker_status():
    """Get Docker container status."""
    try:
        result = subprocess.run(
            ['sudo', 'docker', 'ps', '--format', 'json'],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            containers = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    containers.append(json.loads(line))
            return containers
    except:
        pass
    return []

def get_system_stats():
    """Get system resource statistics."""
    import psutil

    return {
        'cpu_percent': psutil.cpu_percent(interval=1),
        'memory': psutil.virtual_memory()._asdict(),
        'disk': psutil.disk_usage('/')._asdict(),
        'network': len(psutil.net_connections())
    }

def create_dashboard():
    """Create health dashboard."""
    layout = Layout()

    # Get data
    containers = get_docker_status()
    stats = get_system_stats()

    # Container table
    container_table = Table(title="Docker Containers")
    container_table.add_column("Name", style="cyan")
    container_table.add_column("Status", style="green")
    container_table.add_column("Uptime")

    for container in containers:
        container_table.add_row(
            container.get('Names', 'unknown'),
            container.get('Status', 'unknown'),
            container.get('RunningFor', 'unknown')
        )

    # System stats table
    stats_table = Table(title="System Resources")
    stats_table.add_column("Resource", style="cyan")
    stats_table.add_column("Usage", style="yellow")

    stats_table.add_row("CPU", f"{stats['cpu_percent']:.1f}%")
    stats_table.add_row("Memory",
                       f"{stats['memory']['percent']:.1f}%")
    stats_table.add_row("Disk", f"{stats['disk']['percent']:.1f}%")
    stats_table.add_row("Network Connections", str(stats['network']))

    layout.split_column(
        Panel(container_table, title="Services"),
        Panel(stats_table, title="Resources")
    )

    return layout

def main():
    """Run health monitoring dashboard."""
    console.print("[cyan]Health Monitoring Dashboard[/cyan]")
    console.print(f"[dim]Updated: {datetime.now()}[/dim]\n")

    dashboard = create_dashboard()
    console.print(dashboard)

    # Write to log file
    with open('/var/log/health-check.json', 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'containers': get_docker_status(),
            'system': get_system_stats()
        }, f, default=str)

if __name__ == '__main__':
    main()
EOF

chmod +x deployment-new/scripts/health_monitor.py
```
**Verification**: Script shows health dashboard

## Phase 7: Main SkyPilot Task Update (Day 7)

### 7.1 Update Main Task with UV Scripts
```yaml
# Task: Update skypilot-tasks/bacalhau-node.yaml
name: bacalhau-sensor-node

resources:
  cloud: aws
  region: us-west-2
  instance_type: t3.medium
  use_spot: true
  disk_size: 30
  num_nodes: 3

file_mounts:
  # All deployment files
  /tmp/deploy: ./deployment-new

setup: |
  # Install uv
  curl -LsSf https://astral.sh/uv/install.sh | sh
  source $HOME/.local/bin/env

  # Install system dependencies
  sudo apt-get update
  sudo apt-get install -y ec2-metadata

  # Install Docker
  curl -fsSL https://get.docker.com | sudo sh
  sudo usermod -aG docker $USER

  # Install Docker Compose
  sudo apt-get install -y docker-compose-plugin

  # Copy files to proper locations
  sudo cp -r /tmp/deploy/* /

  # Make scripts executable
  sudo chmod +x /opt/sensor/generate_node_identity.py
  sudo chmod +x /scripts/generate_bacalhau_config.py
  sudo chmod +x /scripts/health_monitor.py

  # Generate configurations
  sudo uv run /scripts/generate_bacalhau_config.py

  # Generate node identity
  INSTANCE_ID=$(ec2-metadata --instance-id | cut -d ' ' -f 2)
  sudo INSTANCE_ID=$INSTANCE_ID uv run /opt/sensor/generate_node_identity.py

run: |
  # Start services
  cd /opt/bacalhau && sudo docker compose up -d
  cd /opt/sensor && sudo docker compose up -d

  # Run health check
  sleep 10
  sudo uv run /scripts/health_monitor.py

  # Setup monitoring cron
  (crontab -l 2>/dev/null; echo "*/5 * * * * /usr/bin/uv run \
    /scripts/health_monitor.py > /dev/null 2>&1") | sudo crontab -

  echo "Deployment complete!"
```
**Verification**: Task uses uv for all Python scripts

## Phase 8: Validation Suite (Day 8)

### 8.1 Create Comprehensive Validator
```python
# Task: Create validate_all.py
cat << 'EOF' > validate_all.py
#!/usr/bin/env -S uv run -s
# /// script
# dependencies = ["click", "rich", "pyyaml", "jsonschema"]
# ///

import click
import yaml
import json
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

@click.command()
@click.option('--verbose', is_flag=True, help='Verbose output')
def validate_all(verbose):
    """Validate all deployment configurations."""

    validations = [
        ('SkyPilot tasks', validate_tasks),
        ('Docker Compose files', validate_compose),
        ('Python scripts', validate_scripts),
        ('Credentials', validate_credentials),
        ('Directory structure', validate_structure)
    ]

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:

        results = []
        for name, validator in validations:
            task = progress.add_task(f"Validating {name}...", total=1)

            try:
                result = validator(verbose)
                results.append((name, result, None))
                progress.update(task, advance=1)
            except Exception as e:
                results.append((name, False, str(e)))
                progress.update(task, advance=1)

    # Print results
    console.print("\n[bold]Validation Results:[/bold]")
    for name, result, error in results:
        if result:
            console.print(f"  [green]✓[/green] {name}")
        else:
            console.print(f"  [red]✗[/red] {name}")
            if error and verbose:
                console.print(f"    [dim]{error}[/dim]")

    all_passed = all(r[1] for r in results)
    if all_passed:
        console.print("\n[green]All validations passed![/green]")
    else:
        console.print("\n[red]Some validations failed.[/red]")

    return 0 if all_passed else 1

def validate_tasks(verbose):
    """Validate SkyPilot task files."""
    task_dir = Path('skypilot-tasks')
    if not task_dir.exists():
        raise Exception("skypilot-tasks directory not found")

    for task_file in task_dir.glob('*.yaml'):
        with open(task_file) as f:
            task = yaml.safe_load(f)

        if not all(k in task for k in ['name', 'resources']):
            raise Exception(f"{task_file.name} missing required fields")

    return True

def validate_compose(verbose):
    """Validate Docker Compose files."""
    compose_files = [
        'deployment-new/opt/bacalhau/docker-compose.yml',
        'deployment-new/opt/sensor/docker-compose.yml'
    ]

    for compose_file in compose_files:
        if not Path(compose_file).exists():
            raise Exception(f"{compose_file} not found")

        with open(compose_file) as f:
            compose = yaml.safe_load(f)

        if 'services' not in compose:
            raise Exception(f"{compose_file} missing services section")

    return True

def validate_scripts(verbose):
    """Validate Python scripts have uv shebangs."""
    scripts = Path('deployment-new').rglob('*.py')

    for script in scripts:
        with open(script) as f:
            first_line = f.readline()

        if not ('uv run' in first_line or '#!/usr/bin/env' in first_line):
            raise Exception(f"{script} missing uv shebang")

    return True

def validate_credentials(verbose):
    """Check if credential files exist."""
    cred_files = [
        'deployment-new/etc/bacalhau/orchestrator_endpoint',
        'deployment-new/etc/bacalhau/orchestrator_token'
    ]

    for cred_file in cred_files:
        if not Path(cred_file).exists():
            if verbose:
                console.print(f"[yellow]Warning: {cred_file} not found[/yellow]")

    return True  # Don't fail on missing credentials

def validate_structure(verbose):
    """Validate directory structure."""
    required_dirs = [
        'skypilot-tasks',
        'deployment-new/etc/bacalhau',
        'deployment-new/opt/bacalhau',
        'deployment-new/opt/sensor',
        'deployment-new/scripts',
        'sky-cli'
    ]

    for dir_path in required_dirs:
        if not Path(dir_path).exists():
            raise Exception(f"Required directory {dir_path} not found")

    return True

if __name__ == '__main__':
    import sys
    sys.exit(validate_all())
EOF

chmod +x validate_all.py
```
**Verification**: `./validate_all.py --verbose`

## Success Criteria

After completing all tasks:
- [ ] All Python scripts use `uv run` with inline dependencies
- [ ] No direct `pip` or `python` commands in deployment
- [ ] SkyPilot deploys nodes successfully
- [ ] Bacalhau nodes connect to orchestrator
- [ ] Sensor service generates data
- [ ] Health monitoring works
- [ ] All validations pass
- [ ] Documentation updated with uv examples

## Notes

1. **Always use uv** - Every Python script has `#!/usr/bin/env -S uv run -s`
2. **Inline dependencies** - Dependencies declared in script metadata
3. **No virtual environments** - uv handles isolation automatically
4. **Executable scripts** - All scripts are directly executable
5. **Rich output** - Using Rich library for beautiful terminal output
