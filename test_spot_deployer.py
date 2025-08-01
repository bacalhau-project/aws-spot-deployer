#!/usr/bin/env python3
# /// script
# dependencies = [
#   "boto3>=1.26.0",
#   "pyyaml>=6.0",
#   "rich>=13.0.0",
# ]
# ///
"""
Test script for Spot Deployer - safely test with minimal AWS resources.
"""

import os
import sys
import time
from datetime import datetime
from pathlib import Path

import yaml

# Add the spot directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from spot_deployer.core.state import SimpleStateManager
from spot_deployer.main import main
from spot_deployer.utils.display import console, rich_error, rich_success


def create_test_config(instance_count=2, instance_type="t3.micro"):
    """Create a minimal test configuration."""
    config = {
        "aws": {
            "total_instances": instance_count,
            "username": "ubuntu",
            "public_ssh_key_path": "~/.ssh/id_ed25519.pub",
            "private_ssh_key_path": "~/.ssh/id_ed25519",
            "files_directory": "files",
            "scripts_directory": "instance/scripts",
            "use_dedicated_vpc": False,  # Use default VPC for testing
            "instance_storage_gb": 8,  # Minimal storage
            "tags": {
                "Environment": "Testing",
                "Purpose": "SpotDeployerTest",
                "TestRun": datetime.now().strftime("%Y%m%d-%H%M%S"),
            },
        },
        "regions": [
            {
                "us-east-2": {  # Usually has good spot availability
                    "machine_type": instance_type,
                    "image": "auto",
                }
            }
        ],
    }

    # Write config
    config_path = Path("test-config.yaml")
    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False)

    return config_path


def run_command(command, config_file=None):
    """Run a spot deployer command."""
    args = [command]
    if config_file:
        args.extend(["--config", str(config_file)])

    # Save original argv
    original_argv = sys.argv

    try:
        # Set up arguments for main()
        sys.argv = ["spot_deployer"] + args
        main()
    finally:
        # Restore original argv
        sys.argv = original_argv


def test_lifecycle():
    """Test the full lifecycle of instance creation and destruction."""
    console.print("\n[bold cyan]Starting Spot Deployer Test Suite[/bold cyan]\n")

    # Create test config
    console.print("1️⃣  Creating test configuration...")
    config_path = create_test_config(instance_count=2)
    rich_success(f"Created test config: {config_path}")

    # Check initial state
    console.print("\n2️⃣  Checking initial state...")
    # Use the same path as main.py
    state_path = os.path.join("output", "instances.json")
    state = SimpleStateManager(state_path)
    initial_instances = state.load_instances()
    if initial_instances:
        rich_error(f"Found {len(initial_instances)} existing instances! Run 'destroy' first.")
        return False
    rich_success("No existing instances found")

    # Create instances
    console.print("\n3️⃣  Creating test instances...")
    console.print("[dim]This will create 2 t3.micro spot instances in us-east-2[/dim]")

    start_time = time.time()
    run_command("create", config_path)
    create_time = time.time() - start_time

    # Check created instances
    console.print("\n4️⃣  Verifying instance creation...")
    # Reload state after create command
    state = SimpleStateManager(state_path)
    created_instances = state.load_instances()
    if len(created_instances) != 2:
        rich_error(f"Expected 2 instances, found {len(created_instances)}")
        return False

    rich_success(
        f"Successfully created {len(created_instances)} instances in {create_time:.1f} seconds"
    )

    # List instances
    console.print("\n5️⃣  Listing instances...")
    run_command("list")

    # Wait a bit
    console.print("\n[dim]Waiting 30 seconds before cleanup...[/dim]")
    time.sleep(30)

    # Destroy instances
    console.print("\n6️⃣  Destroying test instances...")
    start_time = time.time()
    run_command("destroy")
    destroy_time = time.time() - start_time

    # Verify cleanup
    console.print("\n7️⃣  Verifying cleanup...")
    # Reload state after destroy command
    state = SimpleStateManager(state_path)
    final_instances = state.load_instances()
    if final_instances:
        rich_error(f"Found {len(final_instances)} instances after destroy!")
        return False

    rich_success(f"All instances destroyed in {destroy_time:.1f} seconds")

    # Clean up test config
    config_path.unlink()

    console.print("\n[bold green]✅ All tests passed![/bold green]")
    return True


def test_error_handling():
    """Test error handling scenarios."""
    console.print("\n[bold cyan]Testing Error Handling[/bold cyan]\n")

    # Test with invalid instance type
    console.print("1️⃣  Testing with likely unavailable instance type...")
    config_path = create_test_config(instance_count=1, instance_type="p4d.24xlarge")

    run_command("create", config_path)

    # Check if any instances were created
    state_path = os.path.join("output", "instances.json")
    state = SimpleStateManager(state_path)
    instances = state.load_instances()

    if instances:
        console.print(
            f"[yellow]Warning: {len(instances)} instances created, cleaning up...[/yellow]"
        )
        run_command("destroy")
    else:
        rich_success("Correctly handled capacity error")

    config_path.unlink()
    return True


def main_test():
    """Main test runner."""
    try:
        # Check AWS credentials first
        import boto3

        sts = boto3.client("sts")
        try:
            identity = sts.get_caller_identity()
            console.print(f"[green]✓ AWS authenticated as: {identity['Arn']}[/green]")
        except Exception as e:
            rich_error(f"AWS authentication failed: {e}")
            rich_error("Please configure AWS credentials before running tests")
            return 1

        # Ensure output directory exists
        os.makedirs("output", exist_ok=True)

        # Run tests
        if not test_lifecycle():
            return 1

        if not test_error_handling():
            return 1

        console.print("\n[bold green]🎉 All tests completed successfully![/bold green]")
        return 0

    except KeyboardInterrupt:
        console.print("\n[yellow]Test interrupted by user[/yellow]")
        # Try to clean up
        state_path = os.path.join("output", "instances.json")
        state = SimpleStateManager(state_path)
        if state.load_instances():
            console.print("Running emergency cleanup...")
            run_command("destroy")
        return 1
    except Exception as e:
        rich_error(f"Test failed with error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main_test())
