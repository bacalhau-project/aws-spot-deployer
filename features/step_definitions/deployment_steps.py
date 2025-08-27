#!/usr/bin/env -S uv run -s
# /// script
# dependencies = ["behave", "boto3", "pyyaml", "rich"]
# ///
"""Step definitions for Bacalhau cluster deployment features."""

import subprocess
import time
from pathlib import Path

import yaml
from behave import given, then, when
from rich.console import Console

console = Console()


# ============================================================================
# GIVEN Steps - Preconditions
# ============================================================================


@given("I have AWS credentials configured")
def step_aws_credentials_configured(context):
    """Verify AWS credentials are properly configured."""
    import boto3

    try:
        sts = boto3.client("sts")
        identity = sts.get_caller_identity()
        context.aws_account = identity["Account"]
        assert context.aws_account, "No AWS account found"
    except Exception as e:
        raise AssertionError(f"AWS credentials not configured: {e}")


@given("I have SkyPilot installed with uv")
def step_skypilot_installed(context):
    """Verify SkyPilot is installed and accessible."""
    result = subprocess.run(["sky", "--version"], capture_output=True, text=True)
    assert result.returncode == 0, "SkyPilot not installed"
    context.skypilot_version = result.stdout.strip()


@given("I have orchestrator credentials in deployment-new/etc/bacalhau/")
def step_orchestrator_credentials_exist(context):
    """Check that orchestrator credential files exist."""
    endpoint_file = Path("deployment-new/etc/bacalhau/orchestrator_endpoint")
    token_file = Path("deployment-new/etc/bacalhau/orchestrator_token")

    context.has_credentials = endpoint_file.exists() and token_file.exists()
    if context.has_credentials:
        context.orchestrator_endpoint = endpoint_file.read_text().strip()


@given("I have Docker Compose files prepared")
def step_docker_compose_files_prepared(context):
    """Verify Docker Compose files are in place."""
    compose_files = [
        Path("deployment-new/opt/bacalhau/docker-compose.yml"),
        Path("deployment-new/opt/sensor/docker-compose.yml"),
    ]

    for compose_file in compose_files:
        assert compose_file.exists(), f"Missing {compose_file}"

        # Validate YAML syntax
        with open(compose_file) as f:
            compose_config = yaml.safe_load(f)
        assert "services" in compose_config, f"Invalid compose file {compose_file}"


@given("I have a valid SkyPilot task configuration")
def step_valid_task_configuration(context):
    """Ensure SkyPilot task YAML is valid."""
    task_file = Path("skypilot-tasks/bacalhau-node.yaml")
    assert task_file.exists(), "Task file not found"

    with open(task_file) as f:
        context.task_config = yaml.safe_load(f)

    required_fields = ["name", "resources", "setup", "run"]
    for field in required_fields:
        assert field in context.task_config, f"Missing required field: {field}"


@given("I have a running Bacalhau cluster")
def step_running_cluster(context):
    """Verify cluster is already running."""
    result = subprocess.run(["sky", "status", "bacalhau-cluster"], capture_output=True, text=True)
    assert "RUNNING" in result.stdout, "Cluster not running"
    context.cluster_running = True


@given("I have no orchestrator credential files")
def step_no_credentials(context):
    """Ensure credential files don't exist."""
    endpoint_file = Path("deployment-new/etc/bacalhau/orchestrator_endpoint")
    token_file = Path("deployment-new/etc/bacalhau/orchestrator_token")

    # Temporarily rename if they exist
    if endpoint_file.exists():
        endpoint_file.rename(endpoint_file.with_suffix(".backup"))
    if token_file.exists():
        token_file.rename(token_file.with_suffix(".backup"))

    context.credentials_backed_up = True


@given("I have a running cluster with {count:d} nodes")
def step_cluster_with_nodes(context, count):
    """Verify cluster has specific number of nodes."""
    step_running_cluster(context)

    result = subprocess.run(
        ["sky", "status", "bacalhau-cluster", "--show-all"], capture_output=True, text=True
    )

    # Count nodes in output
    node_count = result.stdout.count("RUNNING")
    assert node_count == count, f"Expected {count} nodes, found {node_count}"
    context.node_count = count


# ============================================================================
# WHEN Steps - Actions
# ============================================================================


@when('I run "{command}"')
def step_run_command(context, command):
    """Execute a command and capture output."""
    console.print(f"[cyan]Executing: {command}[/cyan]")

    result = subprocess.run(command, shell=True, capture_output=True, text=True)

    context.last_command = command
    context.last_result = result
    context.last_stdout = result.stdout
    context.last_stderr = result.stderr
    context.last_returncode = result.returncode


@when("a spot instance is preempted by AWS")
def step_spot_preemption(context):
    """Simulate or wait for spot instance preemption."""
    # In real testing, this would either:
    # 1. Use AWS API to send interruption notice
    # 2. Wait for natural preemption
    # 3. Manually terminate an instance

    # For testing, we'll simulate by terminating one instance
    subprocess.run(
        ["sky", "exec", "bacalhau-cluster", "--node", "0", "sudo shutdown -h now"],
        capture_output=True,
        text=True,
    )

    time.sleep(30)  # Wait for termination
    context.preemption_simulated = True


@when("I confirm the destruction")
def step_confirm_destruction(context):
    """Confirmation is handled by -y flag in command."""
    # The destroy command should already have -y flag
    pass


@when("I modify the sensor configuration locally")
def step_modify_sensor_config(context):
    """Make a change to local sensor configuration."""
    config_file = Path("deployment-new/opt/sensor/config/sensor-config.yaml")

    with open(config_file) as f:
        config = yaml.safe_load(f)

    # Make a test modification
    config["test_timestamp"] = time.time()

    with open(config_file, "w") as f:
        yaml.dump(config, f)

    context.config_modified = True


@when("I SSH into the node")
def step_ssh_into_node(context):
    """SSH into first node and run commands."""
    # This would normally open interactive SSH
    # For testing, we'll run a command instead
    result = subprocess.run(
        ["sky", "ssh", "bacalhau-cluster", "--command", "hostname"], capture_output=True, text=True
    )

    context.ssh_successful = result.returncode == 0
    context.node_hostname = result.stdout.strip()


# ============================================================================
# THEN Steps - Assertions
# ============================================================================


@then("a single AWS spot instance should be created")
def step_single_instance_created(context):
    """Verify single spot instance was created."""
    time.sleep(60)  # Wait for instance to be created

    result = subprocess.run(["sky", "status", "bacalhau-cluster"], capture_output=True, text=True)

    assert "RUNNING" in result.stdout, "Instance not running"
    assert "1x" in result.stdout, "Not exactly 1 instance"


@then("{count:d} AWS spot instances should be created")
def step_multiple_instances_created(context, count):
    """Verify multiple spot instances were created."""
    time.sleep(90)  # Wait for instances

    result = subprocess.run(
        ["sky", "status", "bacalhau-cluster", "--show-all"], capture_output=True, text=True
    )

    running_count = result.stdout.count("RUNNING")
    assert running_count == count, f"Expected {count}, got {running_count}"


@then("Docker should be installed on the instance")
def step_docker_installed(context):
    """Verify Docker is installed."""
    result = subprocess.run(
        ["sky", "exec", "bacalhau-cluster", "docker --version"], capture_output=True, text=True
    )

    assert result.returncode == 0, "Docker not installed"
    assert "Docker version" in result.stdout, "Docker not responding"


@then("Bacalhau container should be running")
def step_bacalhau_running(context):
    """Verify Bacalhau container is running."""
    result = subprocess.run(
        [
            "sky",
            "exec",
            "bacalhau-cluster",
            'sudo docker ps --filter name=compute --format "{{.Names}}"',
        ],
        capture_output=True,
        text=True,
    )

    assert "compute" in result.stdout, "Bacalhau container not running"


@then("the node should connect to the orchestrator")
def step_node_connects_orchestrator(context):
    """Verify node connected to orchestrator."""
    if not context.has_credentials:
        return  # Skip if no credentials

    result = subprocess.run(
        [
            "sky",
            "exec",
            "bacalhau-cluster",
            'sudo docker logs bacalhau_compute_1 | grep "connected to orchestrator"',
        ],
        capture_output=True,
        text=True,
    )

    # Check for connection logs
    assert (
        "connected" in result.stdout.lower() or "orchestrator" in result.stdout.lower()
    ), "Node not connected to orchestrator"


@then("the sensor service should be generating data")
def step_sensor_generating_data(context):
    """Verify sensor is generating data."""
    result = subprocess.run(
        ["sky", "exec", "bacalhau-cluster", "sudo docker logs --tail 10 sensor_simulators_1"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, "Could not get sensor logs"
    # Check for data generation indicators
    assert len(result.stdout) > 0, "No sensor logs found"


@then("all nodes should have Docker installed")
def step_all_nodes_docker(context):
    """Verify Docker on all nodes."""
    for i in range(context.node_count):
        result = subprocess.run(
            ["sky", "exec", "bacalhau-cluster", "--node", str(i), "docker --version"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"Docker not installed on node {i}"


@then("all AWS spot instances should be terminated")
def step_instances_terminated(context):
    """Verify all instances are terminated."""
    time.sleep(30)  # Wait for termination

    result = subprocess.run(["sky", "status", "bacalhau-cluster"], capture_output=True, text=True)

    assert (
        "No clusters found" in result.stdout or "bacalhau-cluster" not in result.stdout
    ), "Cluster still exists"


@then("health checks should be scheduled every {minutes:d} minutes")
def step_health_checks_scheduled(context, minutes):
    """Verify cron job for health checks."""
    result = subprocess.run(
        ["sky", "exec", "bacalhau-cluster", "sudo crontab -l"], capture_output=True, text=True
    )

    assert (
        f"*/{minutes} * * * *" in result.stdout
    ), f"Health check not scheduled every {minutes} minutes"
    assert "health_monitor.py" in result.stdout, "Health monitor script not in cron"
