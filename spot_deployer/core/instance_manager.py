"""Instance creation and management logic."""
import time
import subprocess
from typing import List, Dict
from datetime import datetime

import boto3

from ..utils.aws import get_latest_ubuntu_ami, create_simple_security_group
from ..utils.display import rich_status, rich_error
from ..core.constants import DEFAULT_INSTANCE_TYPE, DEFAULT_TIMEOUT


def create_instances_in_region(
    config, region: str, count: int, progress=None, task=None
) -> List[Dict]:
    """Create spot instances in a specific region."""
    if count <= 0:
        return []
    
    def update_progress(message: str):
        """Update progress bar if available, otherwise use rich_status."""
        if progress and task is not None:
            progress.update(task, description=message)
            time.sleep(0.2)  # Brief pause to show progress
        else:
            rich_status(message)
    
    update_progress(f"🔍 Looking for VPC in {region}...")
    
    try:
        ec2 = boto3.client("ec2", region_name=region)
        
        # Get default VPC
        vpcs = ec2.describe_vpcs(Filters=[{"Name": "isDefault", "Values": ["true"]}])
        if not vpcs["Vpcs"]:
            rich_error(f"No default VPC found in {region}")
            return []
        
        vpc_id = vpcs["Vpcs"][0]["VpcId"]
        update_progress(f"📍 Found VPC: {vpc_id}")
        
        # Get subnet
        subnets = ec2.describe_subnets(
            Filters=[
                {"Name": "vpc-id", "Values": [vpc_id]},
                {"Name": "default-for-az", "Values": ["true"]},
            ]
        )
        if not subnets["Subnets"]:
            rich_error(f"No default subnets found in {region}")
            return []
        
        subnet_id = subnets["Subnets"][0]["SubnetId"]
        update_progress(f"🌐 Using subnet: {subnet_id}")
        
        # Create security group
        sg_id = create_simple_security_group(ec2, vpc_id)
        update_progress(f"🔒 Security group: {sg_id}")
        
        # Get region config
        region_cfg = config.region_config(region)
        machine_type = region_cfg.get("machine_type", DEFAULT_INSTANCE_TYPE)
        
        # Get AMI
        ami_id = None
        if region_cfg.get("image") == "auto":
            update_progress(f"🔍 Finding Ubuntu AMI for {region}...")
            ami_id = get_latest_ubuntu_ami(region)
        else:
            ami_id = region_cfg.get("image")
        
        if not ami_id:
            rich_error(f"No AMI found for {region}")
            return []
        
        update_progress(f"💿 Using AMI: {ami_id}")
        
        # Create instances
        instances_per_region = region_cfg.get("instances_per_region", count)
        update_progress(f"🚀 Creating {instances_per_region} instances...")
        
        market_options = {
            "MarketType": "spot",
            "SpotOptions": {"SpotInstanceType": "one-time"},
        }
        
        result = ec2.run_instances(
            ImageId=ami_id,
            MinCount=instances_per_region,
            MaxCount=instances_per_region,
            InstanceType=machine_type,
            KeyName=config.ssh_key_name(),
            SecurityGroupIds=[sg_id],
            SubnetId=subnet_id,
            InstanceMarketOptions=market_options,
            BlockDeviceMappings=[
                {
                    "DeviceName": "/dev/sda1",
                    "Ebs": {
                        "VolumeSize": config.instance_storage_gb(),
                        "VolumeType": "gp3",
                        "DeleteOnTermination": True,
                    },
                }
            ],
            TagSpecifications=[
                {
                    "ResourceType": "instance",
                    "Tags": [
                        {"Key": "Name", "Value": f"spot-{region}"},
                        {"Key": "ManagedBy", "Value": "SpotDeployer"},
                    ]
                    + [{"Key": k, "Value": v} for k, v in config.tags().items()],
                }
            ],
            UserData=config.cloud_init_script if hasattr(config, 'cloud_init_script') else "",
        )
        
        # Process created instances
        created_instances = []
        for inst in result["Instances"]:
            instance_data = {
                "id": inst["InstanceId"],
                "region": region,
                "type": machine_type,
                "state": inst["State"]["Name"],
                "created": datetime.now().isoformat(),
                "ami": ami_id,
                "vpc_id": vpc_id,
                "subnet_id": subnet_id,
                "security_group_id": sg_id,
            }
            created_instances.append(instance_data)
        
        update_progress(f"✅ Created {len(created_instances)} instances in {region}")
        return created_instances
        
    except Exception as e:
        rich_error(f"Error creating instances in {region}: {e}")
        return []


def wait_for_instance_ready(
    hostname: str,
    username: str,
    private_key_path: str,
    timeout: int = DEFAULT_TIMEOUT,
    instance_key: str = None,
    update_status_func=None,
    progress_callback=None,
    config=None,
) -> bool:
    """Wait for SSH to be ready and for cloud-init to finish with detailed progress tracking."""
    start_time = time.time()
    ssh_ready = False
    
    def update_progress(phase, progress, status=""):
        if progress_callback and instance_key:
            progress_callback(instance_key, phase, progress, status)
        if update_status_func and instance_key:
            update_status_func(instance_key, f"{phase}: {status}")
    
    update_progress("SSH: Connection", 0, "Starting SSH connection check...")
    
    while time.time() - start_time < timeout:
        elapsed = int(time.time() - start_time)
        
        # Phase 1: Wait for SSH
        if not ssh_ready:
            update_progress(
                "SSH: Connection", 10, f"Attempting SSH connection... ({elapsed}s)"
            )
            try:
                result = subprocess.run(
                    [
                        "ssh",
                        "-i",
                        private_key_path,
                        "-o",
                        "StrictHostKeyChecking=no",
                        "-o",
                        "UserKnownHostsFile=/dev/null",
                        "-o",
                        "ConnectTimeout=5",
                        f"{username}@{hostname}",
                        'echo "SSH ready"',
                    ],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if result.returncode == 0:
                    ssh_ready = True
                    update_progress("SSH: Connected", 20, "SSH connection established")
            except Exception:
                pass
        
        # Phase 2: Check cloud-init status
        if ssh_ready:
            update_progress("Cloud-Init: Status", 30, "Checking cloud-init status...")
            try:
                result = subprocess.run(
                    [
                        "ssh",
                        "-i",
                        private_key_path,
                        "-o",
                        "StrictHostKeyChecking=no",
                        "-o",
                        "UserKnownHostsFile=/dev/null",
                        "-o",
                        "ConnectTimeout=5",
                        f"{username}@{hostname}",
                        "cloud-init status --wait || cloud-init status",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                
                status_output = result.stdout.strip()
                
                if "done" in status_output.lower():
                    update_progress("Cloud-Init: Complete", 100, "Instance fully ready")
                    return True
                elif "running" in status_output.lower():
                    update_progress(
                        "Cloud-Init: Running",
                        50,
                        f"Cloud-init in progress... ({elapsed}s)",
                    )
                elif "error" in status_output.lower():
                    update_progress("Cloud-Init: Error", 0, "Cloud-init failed")
                    if update_status_func and instance_key:
                        update_status_func(
                            instance_key,
                            "ERROR: Cloud-init failed",
                            is_final=True,
                        )
                    return False
                else:
                    update_progress(
                        "Cloud-Init: Unknown",
                        40,
                        f"Status: {status_output[:30]}...",
                    )
            except subprocess.TimeoutExpired:
                update_progress(
                    "Cloud-Init: Timeout", 30, "Status check timed out, retrying..."
                )
            except Exception as e:
                update_progress(
                    "Cloud-Init: Error", 30, f"Check failed: {str(e)[:30]}"
                )
        
        time.sleep(5)
    
    # Timeout reached
    update_progress("Timeout", 0, f"Timeout after {timeout}s")
    if update_status_func and instance_key:
        update_status_func(
            instance_key,
            "ERROR: Timeout waiting for instance to be ready.",
            is_final=True,
        )
    return False