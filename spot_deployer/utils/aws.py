"""AWS-specific utility functions."""
import os
import json
import time
import threading
from typing import Optional, Dict
from datetime import datetime

import boto3

from ..core.constants import (
    CANONICAL_OWNER_ID,
    DEFAULT_UBUNTU_AMI_PATTERN,
    CACHE_DIR,
    DEFAULT_CACHE_AGE_HOURS,
)
from .display import rich_error

# Global AMI cache
AMI_CACHE = {}
CACHE_LOCK = threading.Lock()


def cache_file_fresh(filepath: str, max_age_hours: int = DEFAULT_CACHE_AGE_HOURS) -> bool:
    """Check if cache file is fresh."""
    if not os.path.exists(filepath):
        return False
    age_hours = (time.time() - os.path.getmtime(filepath)) / 3600
    return age_hours < max_age_hours


def load_cache(filepath: str) -> Optional[Dict]:
    """Load data from cache file."""
    if cache_file_fresh(filepath):
        try:
            with open(filepath, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return None


def save_cache(filepath: str, data: Dict) -> None:
    """Save data to cache file."""
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2, default=str)
    except Exception:
        pass


def get_latest_ubuntu_ami(region: str, log_function=None) -> Optional[str]:
    """Get latest Ubuntu 22.04 LTS AMI for region."""
    cache_file = f"{CACHE_DIR}/ami_{region}.json"
    
    def log_message(msg: str):
        if log_function:
            log_function(msg)
        else:
            print(msg)
    
    # Check memory cache first (fastest)
    with CACHE_LOCK:
        if region in AMI_CACHE:
            log_message(f"Using memory-cached AMI for {region}: {AMI_CACHE[region]}")
            return AMI_CACHE[region]
    
    # Try file cache second
    cached = load_cache(cache_file)
    if cached and "ami_id" in cached:
        log_message(f"Using file-cached AMI for {region}: {cached['ami_id']}")
        # Also store in memory cache
        with CACHE_LOCK:
            AMI_CACHE[region] = cached["ami_id"]
        return cached["ami_id"]
    
    # Fetch from AWS
    try:
        log_message(f"Fetching AMI for {region}...")
        ec2 = boto3.client("ec2", region_name=region)
        response = ec2.describe_images(
            Owners=[CANONICAL_OWNER_ID],  # Canonical
            Filters=[
                {
                    "Name": "name",
                    "Values": [DEFAULT_UBUNTU_AMI_PATTERN],
                },
                {"Name": "state", "Values": ["available"]},
            ],
        )
        
        log_message(
            f"AMI response for {region}: {len(response.get('Images', []))} images found"
        )
        
        if response["Images"]:
            # Sort by creation date to get latest
            images = sorted(
                response["Images"], key=lambda x: x["CreationDate"], reverse=True
            )
            ami_id = images[0]["ImageId"]
            log_message(f"Found AMI for {region}: {ami_id}")
            # Cache result
            save_cache(
                cache_file, {"ami_id": ami_id, "timestamp": datetime.now().isoformat()}
            )
            # Store in memory cache
            with CACHE_LOCK:
                AMI_CACHE[region] = ami_id
            return ami_id
        else:
            log_message(f"No Ubuntu AMIs found for {region}")
    except Exception as e:
        log_message(f"Error getting AMI for {region}: {e}")
    
    return None


def check_aws_auth() -> bool:
    """Quick AWS authentication check."""
    try:
        sts = boto3.client("sts")
        sts.get_caller_identity()
        return True
    except Exception as e:
        if "token has expired" in str(e).lower():
            rich_error("AWS credentials expired. Run: aws sso login")
        else:
            rich_error(f"AWS authentication failed: {e}")
        return False


def create_simple_security_group(ec2, vpc_id: str, group_name: str = "spot-deployer-sg") -> str:
    """Create basic security group."""
    try:
        # Check for existing security group
        response = ec2.describe_security_groups(
            Filters=[
                {"Name": "vpc-id", "Values": [vpc_id]},
                {"Name": "group-name", "Values": [group_name]},
            ]
        )
        
        if response["SecurityGroups"]:
            return response["SecurityGroups"][0]["GroupId"]
        
        # Create new security group
        response = ec2.create_security_group(
            GroupName=group_name,
            Description="Simple security group for spot instances",
            VpcId=vpc_id,
        )
        sg_id = response["GroupId"]
        
        # Add basic rules
        ec2.authorize_security_group_ingress(
            GroupId=sg_id,
            IpPermissions=[
                {
                    "IpProtocol": "tcp",
                    "FromPort": 22,
                    "ToPort": 22,
                    "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
                },
                {
                    "IpProtocol": "tcp",
                    "FromPort": 80,
                    "ToPort": 80,
                    "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
                },
                {
                    "IpProtocol": "tcp",
                    "FromPort": 443,
                    "ToPort": 443,
                    "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
                },
                {
                    "IpProtocol": "tcp",
                    "FromPort": 1234,
                    "ToPort": 1234,
                    "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
                },
                {
                    "IpProtocol": "tcp",
                    "FromPort": 4222,
                    "ToPort": 4222,
                    "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
                },
            ],
        )
        
        return sg_id
    except Exception as e:
        print(f"Error creating security group: {e}")
        raise