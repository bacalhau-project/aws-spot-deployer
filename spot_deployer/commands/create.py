"""Create command implementation."""
import os
import time
import threading
from datetime import datetime
from typing import List
from concurrent.futures import ThreadPoolExecutor

import boto3

from ..core.config import SimpleConfig
from ..core.state import SimpleStateManager
from ..core.constants import ColumnWidths
from ..utils.aws import check_aws_auth
from ..utils.display import (
    rich_status, rich_success, rich_error, rich_warning,
    console, Table, Layout, Live, Panel
)
from ..utils.logging import ConsoleLogger, setup_logger
from ..utils.ssh import transfer_files_scp, wait_for_ssh_only
from ..utils.cloud_init import generate_minimal_cloud_init


def post_creation_setup(instances, config, update_status_func, logger):
    """Handle post-creation setup for all instances."""
    if not instances:
        return
    
    private_key_path = config.private_ssh_key_path()
    if not private_key_path:
        logger.error("No private SSH key path configured")
        return
    
    expanded_key_path = os.path.expanduser(private_key_path)
    if not os.path.exists(expanded_key_path):
        logger.error(f"Private SSH key not found at {expanded_key_path}")
        return
    
    username = config.username()
    files_directory = config.files_directory()
    scripts_directory = config.scripts_directory()
    
    def setup_instance(instance, instance_key):
        instance_id = instance["id"]
        instance_ip = instance.get("public_ip")
        
        if not instance_ip:
            logger.error(f"[{instance_id}] No public IP available")
            update_status_func(instance_key, "ERROR: No public IP", is_final=True)
            return
        
        thread_name = f"Setup-{instance_id}"
        threading.current_thread().name = thread_name
        
        try:
            # Wait for SSH to be available
            logger.info(f"[{instance_id} @ {instance_ip}] Waiting for SSH...")
            update_status_func(instance_key, "Waiting for SSH...")
            
            if not wait_for_ssh_only(instance_ip, username, expanded_key_path, timeout=300):
                logger.error(f"[{instance_id} @ {instance_ip}] SSH timeout")
                update_status_func(instance_key, "ERROR: SSH timeout", is_final=True)
                return
            
            logger.info(f"[{instance_id} @ {instance_ip}] SSH available")
            update_status_func(instance_key, "SSH ready")
            
            # Transfer files
            logger.info(f"[{instance_id} @ {instance_ip}] Starting file transfer...")
            update_status_func(instance_key, "Uploading files...")
            
            def progress_callback(phase, progress, status):
                # Show detailed progress
                update_status_func(instance_key, f"{phase} ({progress}%): {status}")
            
            success = transfer_files_scp(
                instance_ip,
                username,
                expanded_key_path,
                files_directory,
                scripts_directory,
                progress_callback=progress_callback,
                log_function=lambda msg: logger.info(f"[{instance_id} @ {instance_ip}] {msg}"),
            )
            
            if not success:
                logger.error(f"[{instance_id} @ {instance_ip}] File transfer failed")
                update_status_func(instance_key, "ERROR: File upload failed", is_final=True)
                return
            
            logger.info(f"[{instance_id} @ {instance_ip}] SUCCESS: Files uploaded and deployment started")
            update_status_func(instance_key, "SUCCESS: Deployment started", is_final=True)
            
            # Deployment script is now running in background
            logger.info(f"[{instance_id} @ {instance_ip}] Deployment running in background - check ~/deployment.log")
        
        except Exception as e:
            logger.error(f"[{instance_id} @ {instance_ip}] Setup failed: {e}")
            error_msg = str(e)
            if len(error_msg) > 40:
                error_msg = f"{error_msg[:37]}..."
            update_status_func(instance_key, f"ERROR: {error_msg}", is_final=True)
    
    # Process instances in parallel
    with ThreadPoolExecutor(max_workers=len(instances), thread_name_prefix="Setup") as executor:
        futures = []
        for i, instance in enumerate(instances):
            region = instance.get("region", "unknown")
            instance_key = f"{region}-{i + 1}"
            futures.append(executor.submit(setup_instance, instance, instance_key))
        
        # Wait for all setups to complete
        for future in futures:
            future.result()


def create_instances_in_region_with_table(
    config: SimpleConfig,
    region: str,
    count: int,
    creation_status: dict,
    lock: threading.Lock,
    logger,
    update_status_func,
) -> List[dict]:
    """Create spot instances in a specific region with live table updates."""
    if count <= 0:
        return []
    
    instance_keys = [f"{region}-{i + 1}" for i in range(count)]
    
    def log_message(msg: str):
        """Thread-safe logging to file."""
        logger.info(msg)
    
    for key in instance_keys:
        update_status_func(key, "Finding VPC")
    
    try:
        from botocore.config import Config as BotoConfig
        
        # Configure boto3 to not retry capacity errors
        boto_config = BotoConfig(
            retries={
                'max_attempts': 1,  # No retries, fail fast
                'mode': 'standard'
            }
        )
        
        ec2 = boto3.client("ec2", region_name=region, config=boto_config)
        
        # Check if we should use dedicated VPC
        if config.use_dedicated_vpc():
            for key in instance_keys:
                update_status_func(key, "Creating dedicated VPC")
            
            # Create dedicated VPC for this deployment
            from ..utils.aws import create_deployment_vpc
            
            # Generate a deployment ID that's shared across all regions
            if not hasattr(config, '_deployment_id'):
                config._deployment_id = f"spot-{int(time.time())}"
            
            try:
                vpc_id, subnet_id, igw_id = create_deployment_vpc(ec2, region, config._deployment_id)
                log_message(f"Created dedicated VPC in {region}: {vpc_id}")
                log_message(f"Created subnet: {subnet_id}, IGW: {igw_id}")
            except Exception as e:
                log_message(f"Failed to create VPC in {region}: {e}")
                for key in instance_keys:
                    update_status_func(key, "ERROR: VPC creation failed", is_final=True)
                return []
        else:
            # Use default VPC (old behavior)
            vpcs = ec2.describe_vpcs(Filters=[{"Name": "isDefault", "Values": ["true"]}])
            if not vpcs["Vpcs"]:
                log_message(f"No default VPC found in {region}")
                for key in instance_keys:
                    update_status_func(key, "ERROR: No default VPC", is_final=True)
                return []
            
            vpc_id = vpcs["Vpcs"][0]["VpcId"]
            log_message(f"Found VPC in {region}: {vpc_id}")
            
            for key in instance_keys:
                update_status_func(key, "Finding subnet")
            
            # Get subnet
            subnets = ec2.describe_subnets(
                Filters=[
                    {"Name": "vpc-id", "Values": [vpc_id]},
                    {"Name": "default-for-az", "Values": ["true"]},
                ]
            )
            if not subnets["Subnets"]:
                log_message(f"No default subnets found in {region}")
                for key in instance_keys:
                    update_status_func(key, "ERROR: No subnets", is_final=True)
                return []
            
            subnet_id = subnets["Subnets"][0]["SubnetId"]
            log_message(f"Using subnet in {region}: {subnet_id}")
        
        for key in instance_keys:
            update_status_func(key, "Creating security group")
        
        # Create security group
        from ..utils.aws import create_simple_security_group
        sg_id = create_simple_security_group(ec2, vpc_id)
        log_message(f"Security group in {region}: {sg_id}")
        
        # Get region config
        region_cfg = config.region_config(region)
        machine_type = region_cfg.get("machine_type", "t3.medium")
        
        for key in instance_keys:
            update_status_func(key, "Finding AMI")
        
        # Get AMI
        ami_id = None
        if region_cfg.get("image") == "auto":
            from ..utils.aws import get_latest_ubuntu_ami
            ami_id = get_latest_ubuntu_ami(region, log_function=log_message)
        else:
            ami_id = region_cfg.get("image")
        
        if not ami_id:
            log_message(f"No AMI found for {region}")
            for key in instance_keys:
                update_status_func(key, "ERROR: No AMI found", is_final=True)
            return []
        
        log_message(f"Using AMI in {region}: {ami_id}")
        
        for key in instance_keys:
            update_status_func(key, "Launching instance")
        
        # Generate cloud-init script
        cloud_init_script = generate_minimal_cloud_init(config)
        
        # Create instances
        market_options = {
            "MarketType": "spot",
            "SpotOptions": {"SpotInstanceType": "one-time"},
        }
        
        # Build run_instances parameters
        run_params = {
            "ImageId": ami_id,
            "MinCount": count,
            "MaxCount": count,
            "InstanceType": machine_type,
            "SecurityGroupIds": [sg_id],
            "SubnetId": subnet_id,
            "InstanceMarketOptions": market_options,
            "BlockDeviceMappings": [
                {
                    "DeviceName": "/dev/sda1",
                    "Ebs": {
                        "VolumeSize": config.instance_storage_gb(),
                        "VolumeType": "gp3",
                        "DeleteOnTermination": True,
                    },
                }
            ],
            "TagSpecifications": [
                {
                    "ResourceType": "instance",
                    "Tags": [
                        {"Key": "Name", "Value": f"spot-{region}"},
                        {"Key": "ManagedBy", "Value": "SpotDeployer"},
                    ]
                    + [{"Key": k, "Value": v} for k, v in config.tags().items() if k != "ManagedBy"],
                }
            ],
            "UserData": cloud_init_script,
        }
        
        # We don't use AWS KeyName - SSH key is injected via cloud-init
        result = ec2.run_instances(**run_params)
        
        # Wait for instances to get public IPs
        created_instances = []
        instance_ids = [inst["InstanceId"] for inst in result["Instances"]]
        
        log_message(f"Created {len(instance_ids)} instances in {region}, waiting for public IPs...")
        
        for i, inst_id in enumerate(instance_ids):
            key = instance_keys[i]
            update_status_func(key, "Waiting for public IP", instance_id=inst_id)
        
        # Poll for public IPs
        time.sleep(1)  # Give AWS a moment to register the instances
        max_attempts = 30
        for attempt in range(max_attempts):
            try:
                instances_data = ec2.describe_instances(InstanceIds=instance_ids)
                
                for reservation in instances_data["Reservations"]:
                    for inst in reservation["Instances"]:
                        inst_id = inst["InstanceId"]
                        idx = instance_ids.index(inst_id)
                        key = instance_keys[idx]
                        
                        public_ip = inst.get("PublicIpAddress")
                        state = inst["State"]["Name"]
                        
                        if public_ip:
                            instance_data = {
                                "id": inst_id,
                                "region": region,
                                "type": machine_type,
                                "state": state,
                                "public_ip": public_ip,
                                "created": datetime.now().isoformat(),
                                "ami": ami_id,
                                "vpc_id": vpc_id,
                                "subnet_id": subnet_id,
                                "security_group_id": sg_id,
                            }
                            
                            # Check if we already added this instance
                            if not any(ci["id"] == inst_id for ci in created_instances):
                                created_instances.append(instance_data)
                                update_status_func(
                                    key,
                                    "SUCCESS: Created",
                                    instance_id=inst_id,
                                    ip=public_ip,
                                    created=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                )
                                
                                # Update the console logger's IP map
                                with lock:
                                    if hasattr(logger, 'console_handler') and hasattr(logger.console_handler, 'instance_ip_map'):
                                        logger.console_handler.instance_ip_map[inst_id] = public_ip
                
                if len(created_instances) == len(instance_ids):
                    break
                
                time.sleep(2)
            
            except Exception as e:
                # Instances might not be ready yet, just continue
                if attempt < 5:  # Only log after a few attempts
                    time.sleep(2)
                    continue
                log_message(f"Error checking instance status: {e}")
        
        # Mark any instances without IPs as errors
        for i, inst_id in enumerate(instance_ids):
            if not any(ci["id"] == inst_id for ci in created_instances):
                key = instance_keys[i]
                update_status_func(key, "ERROR: No public IP", instance_id=inst_id, is_final=True)
        
        return created_instances
    
    except Exception as e:
        error_msg = str(e)
        log_message(f"Error creating instances in {region}: {error_msg}")
        
        # Handle capacity errors specially - just skip this region
        if "InsufficientInstanceCapacity" in error_msg:
            log_message(f"No capacity in {region}, skipping")
            for key in instance_keys:
                update_status_func(key, "SKIPPED: No capacity", is_final=True)
            return []  # Return empty list, no instances created
        elif "Parameter validation failed" in error_msg:
            # AWS parameter validation errors often have the details after a colon
            if "Invalid" in error_msg:
                # Try to extract the specific validation error
                parts = error_msg.split("Invalid")
                if len(parts) > 1:
                    short_error = f"Invalid{parts[1][:40]}..."
                else:
                    short_error = error_msg[:50]
            else:
                short_error = "Parameter validation failed"
        elif len(error_msg) > 50:
            short_error = f"{error_msg[:47]}..."
        else:
            short_error = error_msg
            
        for key in instance_keys:
            update_status_func(key, f"ERROR: {short_error}", is_final=True)
        return []


def cmd_create(config: SimpleConfig, state: SimpleStateManager) -> None:
    """Create spot instances across configured regions with enhanced real-time progress tracking."""
    if not check_aws_auth():
        return
    
    # Initial header will be shown in the Live display
    
    # Setup local logging
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"spot_creation_{timestamp}.log"
    
    # Create console handler with instance IP map
    console_handler = ConsoleLogger(console, {})
    logger = setup_logger("spot_creator", log_filename, console_handler)
    
    # Store reference to console handler for updating IP map
    logger.console_handler = console_handler
    
    # Check for SSH key configuration
    public_key_path = config.public_ssh_key_path()
    private_key_path = config.private_ssh_key_path()
    
    if not public_key_path:
        rich_error("❌ No 'public_ssh_key_path' configured in config.yaml")
        rich_error("   This is required to inject your SSH key into instances.")
        return
    
    # Check if public key exists
    expanded_public_path = os.path.expanduser(public_key_path)
    if not os.path.exists(expanded_public_path):
        rich_error(f"Public SSH key not found at '{public_key_path}'")
        return
    
    # Check private key for SSH operations
    if private_key_path:
        expanded_private_path = os.path.expanduser(private_key_path)
        if not os.path.exists(expanded_private_path):
            rich_error(f"Private SSH key not found at '{private_key_path}'")
            return
    else:
        rich_warning("Private SSH key path is not set in config.yaml. SSH-based operations will fail.")
    
    regions = config.regions()
    if not regions:
        rich_error("No regions configured. Run 'setup' first.")
        return
    
    # Calculate instance distribution
    total_instances = config.instance_count()
    instances_per_region = total_instances // len(regions)
    remainder = total_instances % len(regions)
    
    region_instance_map = {}
    for i, region in enumerate(regions):
        # Distribute remainder instances across first regions
        count = instances_per_region + (1 if i < remainder else 0)
        if count > 0:
            region_instance_map[region] = count
    
    total_instances_to_create = sum(region_instance_map.values())
    
    if total_instances_to_create == 0:
        rich_warning("No instances configured to be created.")
        return
    
    # Track regions that were skipped due to capacity
    skipped_regions = set()
    
    creation_status = {}
    all_instances = []
    lock = threading.Lock()
    
    # Initialize status for all instances
    for region, count in region_instance_map.items():
        region_cfg = config.region_config(region)
        instance_type = region_cfg.get("machine_type", "t3.medium")
        for i in range(count):
            key = f"{region}-{i + 1}"
            creation_status[key] = {
                "region": region,
                "instance_id": "pending...",
                "status": "WAIT: Starting...",
                "type": instance_type,
                "public_ip": "pending...",
                "created": "pending...",
            }
    
    def generate_layout():
        # Count active (non-skipped) instances
        active_count = sum(1 for item in creation_status.values() if "SKIPPED" not in item["status"])
        table = Table(
            title=f"Creating instances ({active_count} active)",
            show_header=True,
            expand=True,
            show_lines=False,
            padding=(0, 1),
        )
        table.add_column("Region", style="magenta", no_wrap=True)
        table.add_column("Instance ID", style="cyan", no_wrap=True)
        table.add_column("Status", style="yellow")
        table.add_column("Type", style="green", no_wrap=True)
        table.add_column("Public IP", style="blue", no_wrap=True)
        table.add_column("Created", style="dim", no_wrap=True)
        
        sorted_items = sorted(creation_status.items(), key=lambda x: x[0])
        
        # Limit table rows to prevent pushing log panel off screen
        # Show priority: errors, then in-progress, then success
        error_items = []
        progress_items = []
        success_items = []
        
        for key, item in sorted_items:
            status = item["status"]
            # Don't show skipped instances in the table
            if "SKIPPED" in status:
                continue
            
            if "ERROR" in status:
                error_items.append((key, item))
            elif "SUCCESS" in status:
                success_items.append((key, item))
            else:
                progress_items.append((key, item))
        
        # Combine in priority order: in-progress first, then errors, then success
        all_items = progress_items + error_items + success_items
        max_rows = 25  # Reasonable limit to keep log visible
        
        items_to_show = all_items[:max_rows]
        if len(all_items) > max_rows:
            # Add indicator that there are more items
            table.caption = f"[dim]Showing {max_rows} of {len(all_items)} instances[/dim]"
        
        for key, item in items_to_show:
            status = item["status"]
            
            if "SUCCESS" in status:
                status_style = f"[bold green]{status}[/bold green]"
            elif "ERROR" in status:
                status_style = f"[bold red]{status}[/bold red]"
            else:
                status_style = status
            
            table.add_row(
                item["region"],
                item["instance_id"],
                status_style,
                item["type"],
                item["public_ip"],
                item["created"],
            )
        
        try:
            with open(log_filename, 'r') as f:
                # Read only last 5 lines for compact display
                lines = [line.rstrip() for line in f.readlines()[-5:]]
                log_content = "\n".join(lines)
        except (FileNotFoundError, IOError):
            log_content = "Waiting for log entries..."
        
        log_panel = Panel(log_content, title=f"Log: {log_filename}", border_style="blue", height=7)
        
        layout = Layout()
        layout.split_column(
            Layout(table),  # Table takes available space
            Layout(log_panel, size=7)  # Fixed log panel at bottom
        )
        
        return layout
    
    def update_status(key, status, instance_id=None, ip=None, created=None, is_final=False):
        with lock:
            if key in creation_status:
                creation_status[key]["status"] = status
                if instance_id:
                    creation_status[key]["instance_id"] = instance_id
                if ip:
                    creation_status[key]["public_ip"] = ip
                if created:
                    creation_status[key]["created"] = created
                
                log_ip = ip if ip else "N/A"
                log_id = instance_id if instance_id else key
                logger.info(f"[{log_id} @ {log_ip}] {status}")
    
    with Live(generate_layout(), refresh_per_second=4, console=console, screen=True) as live:
        
        def create_region_instances(region, count):
            try:
                instances = create_instances_in_region_with_table(
                    config, region, count, creation_status, lock, logger, update_status
                )
                with lock:
                    all_instances.extend(instances)
            except Exception as e:
                logger.error(f"Error in create_region_instances for {region}: {e}")
        
        with ThreadPoolExecutor(max_workers=len(regions), thread_name_prefix="Create") as executor:
            futures = [executor.submit(create_region_instances, r, c) for r, c in region_instance_map.items()]
            while any(f.running() for f in futures):
                live.update(generate_layout())
                time.sleep(0.25)
        
        live.update(generate_layout())  # Final update after creation phase
        
        if all_instances:
            # Status will be shown in the layout, not printed separately
            live.update(generate_layout())
            
            # Always run post-creation setup to upload files
            post_creation_setup(all_instances, config, update_status, logger)
            
            # Keep the live display running during setup
            live.update(generate_layout())
        else:
            rich_error("No instances were successfully created.")
    
    # Show summary
    rich_success(f"Deployment process complete for {len(all_instances)} instances.")
    
    # Count skipped regions
    skipped_count = sum(1 for item in creation_status.values() if "SKIPPED" in item["status"])
    if skipped_count > 0:
        skipped_regions = set()
        for key, item in creation_status.items():
            if "SKIPPED" in item["status"]:
                skipped_regions.add(item["region"])
        if skipped_regions:
            rich_warning(f"Skipped {len(skipped_regions)} region(s) due to no capacity: {', '.join(sorted(skipped_regions))}")
    
    state.save_instances(all_instances)
    
    # Import and call cmd_list to show final state
    from .list import cmd_list
    cmd_list(state)