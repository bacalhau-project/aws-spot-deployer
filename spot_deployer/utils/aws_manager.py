"""AWS Resource Manager - Centralized AWS operations management."""

import time
from typing import Dict, List, Optional, Tuple

import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError

from ..core.constants import CANONICAL_OWNER_ID, DEFAULT_UBUNTU_AMI_PATTERN


class AWSResourceManager:
    """Manages all AWS resource operations for spot instances."""

    def __init__(self, region: str):
        """Initialize AWS manager for a specific region."""
        self.region = region
        self._ec2 = None

    @property
    def ec2(self):
        """Lazy-load EC2 client with optimized config."""
        if self._ec2 is None:
            boto_config = BotoConfig(
                retries={
                    "max_attempts": 3,  # Retry up to 3 times for transient errors
                    "mode": "adaptive",  # Use adaptive retry mode for better handling
                },
                connect_timeout=10,  # 10 second connection timeout
                read_timeout=60,  # 60 second read timeout
            )
            self._ec2 = boto3.client("ec2", region_name=self.region, config=boto_config)
        return self._ec2

    def find_or_create_vpc(
        self, use_dedicated: bool, deployment_id: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        Find existing VPC or create a dedicated one.

        Returns:
            Tuple of (vpc_id, subnet_id)
        """
        if use_dedicated and deployment_id:
            # First check if we already have a SpotDeployer VPC
            existing_vpc = self._find_existing_spot_vpc()
            if existing_vpc:
                return existing_vpc
            # Otherwise create a new one
            return self._create_dedicated_vpc(deployment_id)
        else:
            return self._find_default_vpc()

    def _find_existing_spot_vpc(self) -> Optional[Tuple[str, str]]:
        """Find an existing VPC created by SpotDeployer."""
        try:
            # Look for VPCs with our ManagedBy tag
            vpcs = self.ec2.describe_vpcs(
                Filters=[
                    {"Name": "tag:ManagedBy", "Values": ["SpotDeployer"]},
                    {"Name": "state", "Values": ["available"]},
                ]
            )

            if vpcs["Vpcs"]:
                # Use the first available SpotDeployer VPC
                vpc_id = vpcs["Vpcs"][0]["VpcId"]

                # Find a subnet in this VPC
                subnets = self.ec2.describe_subnets(
                    Filters=[
                        {"Name": "vpc-id", "Values": [vpc_id]},
                        {"Name": "state", "Values": ["available"]},
                    ]
                )

                if subnets["Subnets"]:
                    subnet_id = subnets["Subnets"][0]["SubnetId"]
                    return vpc_id, subnet_id

        except Exception:
            pass

        return None

    def _find_default_vpc(self) -> Tuple[str, str]:
        """Find the default VPC and subnet."""
        # Find default VPC
        vpcs = self.ec2.describe_vpcs(Filters=[{"Name": "isDefault", "Values": ["true"]}])

        if not vpcs["Vpcs"]:
            raise Exception(f"No default VPC found in {self.region}")

        vpc_id = vpcs["Vpcs"][0]["VpcId"]

        # Find default subnet
        subnets = self.ec2.describe_subnets(
            Filters=[
                {"Name": "vpc-id", "Values": [vpc_id]},
                {"Name": "default-for-az", "Values": ["true"]},
            ]
        )

        if not subnets["Subnets"]:
            raise Exception(f"No default subnets found in {self.region}")

        subnet_id = subnets["Subnets"][0]["SubnetId"]

        return vpc_id, subnet_id

    def _create_dedicated_vpc(self, deployment_id: str) -> Tuple[str, str]:
        """Create a dedicated VPC for this deployment."""
        # Create VPC
        vpc_response = self.ec2.create_vpc(CidrBlock="10.0.0.0/16")
        vpc_id = vpc_response["Vpc"]["VpcId"]

        # Enable DNS
        self.ec2.modify_vpc_attribute(VpcId=vpc_id, EnableDnsSupport={"Value": True})
        self.ec2.modify_vpc_attribute(VpcId=vpc_id, EnableDnsHostnames={"Value": True})

        # Create subnet
        subnet_response = self.ec2.create_subnet(
            VpcId=vpc_id, CidrBlock="10.0.1.0/24", AvailabilityZone=self._get_first_az()
        )
        subnet_id = subnet_response["Subnet"]["SubnetId"]

        # Enable auto-assign public IP
        self.ec2.modify_subnet_attribute(SubnetId=subnet_id, MapPublicIpOnLaunch={"Value": True})

        # Create and attach internet gateway
        igw_response = self.ec2.create_internet_gateway()
        igw_id = igw_response["InternetGateway"]["InternetGatewayId"]
        self.ec2.attach_internet_gateway(InternetGatewayId=igw_id, VpcId=vpc_id)

        # Create route table and add route
        rt_response = self.ec2.create_route_table(VpcId=vpc_id)
        rt_id = rt_response["RouteTable"]["RouteTableId"]

        self.ec2.create_route(
            RouteTableId=rt_id, DestinationCidrBlock="0.0.0.0/0", GatewayId=igw_id
        )

        # Associate route table with subnet
        self.ec2.associate_route_table(RouteTableId=rt_id, SubnetId=subnet_id)

        # Tag resources
        tags = [
            {"Key": "Name", "Value": f"spot-vpc-{deployment_id}"},
            {"Key": "ManagedBy", "Value": "SpotDeployer"},
            {"Key": "DeploymentId", "Value": deployment_id},
        ]

        for resource_id in [vpc_id, subnet_id, igw_id, rt_id]:
            self.ec2.create_tags(Resources=[resource_id], Tags=tags)

        return vpc_id, subnet_id

    def _get_first_az(self) -> str:
        """Get the first available AZ in the region."""
        azs = self.ec2.describe_availability_zones(
            Filters=[{"Name": "state", "Values": ["available"]}]
        )
        return azs["AvailabilityZones"][0]["ZoneName"]

    def create_security_group(self, vpc_id: str) -> str:
        """Create a security group for spot instances."""
        sg_name = f"spot-sg-{int(time.time())}"

        try:
            response = self.ec2.create_security_group(
                GroupName=sg_name, Description="Security group for spot instances", VpcId=vpc_id
            )
            sg_id = response["GroupId"]

            # Add ingress rules
            self.ec2.authorize_security_group_ingress(
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
                        "FromPort": 1234,
                        "ToPort": 1235,
                        "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
                    },
                ],
            )

            return sg_id

        except ClientError as e:
            if "InvalidGroup.Duplicate" in str(e):
                # Find existing group
                sgs = self.ec2.describe_security_groups(
                    Filters=[
                        {"Name": "group-name", "Values": [sg_name]},
                        {"Name": "vpc-id", "Values": [vpc_id]},
                    ]
                )
                if sgs["SecurityGroups"]:
                    return sgs["SecurityGroups"][0]["GroupId"]
            raise

    def find_ubuntu_ami(self, ami_pattern: str = DEFAULT_UBUNTU_AMI_PATTERN) -> Optional[str]:
        """Find the latest Ubuntu AMI."""
        try:
            response = self.ec2.describe_images(
                Owners=[CANONICAL_OWNER_ID],
                Filters=[
                    {"Name": "name", "Values": [ami_pattern]},
                    {"Name": "state", "Values": ["available"]},
                    {"Name": "architecture", "Values": ["x86_64"]},
                    {"Name": "virtualization-type", "Values": ["hvm"]},
                ],
            )

            if not response["Images"]:
                return None

            # Sort by creation date and get the latest
            images = sorted(response["Images"], key=lambda x: x["CreationDate"], reverse=True)

            return images[0]["ImageId"]

        except Exception as e:
            # Log error but don't fail - will try default AMI
            import logging

            logging.getLogger(__name__).debug(f"Error finding AMI in {self.region}: {e}")
            return None

    def delete_vpc_resources(self, vpc_id: str) -> bool:
        """Delete all resources associated with a VPC."""
        try:
            # Get all resources
            vpc_resources = self._get_vpc_resources(vpc_id)

            # Delete in correct order
            # 1. Terminate instances
            if vpc_resources["instances"]:
                instance_ids = [i["InstanceId"] for i in vpc_resources["instances"]]
                self.ec2.terminate_instances(InstanceIds=instance_ids)

                # Wait for termination
                waiter = self.ec2.get_waiter("instance_terminated")
                waiter.wait(InstanceIds=instance_ids)

            # 2. Delete security groups (except default)
            for sg in vpc_resources["security_groups"]:
                if sg["GroupName"] != "default":
                    try:
                        self.ec2.delete_security_group(GroupId=sg["GroupId"])
                    except ClientError:
                        pass

            # 3. Delete subnets
            for subnet in vpc_resources["subnets"]:
                self.ec2.delete_subnet(SubnetId=subnet["SubnetId"])

            # 4. Detach and delete internet gateways
            for igw in vpc_resources["internet_gateways"]:
                self.ec2.detach_internet_gateway(
                    InternetGatewayId=igw["InternetGatewayId"], VpcId=vpc_id
                )
                self.ec2.delete_internet_gateway(InternetGatewayId=igw["InternetGatewayId"])

            # 5. Delete route tables (except main)
            for rt in vpc_resources["route_tables"]:
                if not any(assoc.get("Main") for assoc in rt.get("Associations", [])):
                    self.ec2.delete_route_table(RouteTableId=rt["RouteTableId"])

            # 6. Delete the VPC
            self.ec2.delete_vpc(VpcId=vpc_id)

            return True

        except Exception as e:
            import logging

            logging.getLogger(__name__).error(f"Error deleting VPC {vpc_id}: {e}")
            return False

    def _get_vpc_resources(self, vpc_id: str) -> Dict[str, List]:
        """Get all resources associated with a VPC."""
        resources = {
            "instances": [],
            "security_groups": [],
            "subnets": [],
            "internet_gateways": [],
            "route_tables": [],
        }

        # Get instances
        instances = self.ec2.describe_instances(
            Filters=[
                {"Name": "vpc-id", "Values": [vpc_id]},
                {
                    "Name": "instance-state-name",
                    "Values": ["pending", "running", "stopping", "stopped"],
                },
            ]
        )
        for reservation in instances.get("Reservations", []):
            resources["instances"].extend(reservation.get("Instances", []))

        # Get security groups
        sgs = self.ec2.describe_security_groups(Filters=[{"Name": "vpc-id", "Values": [vpc_id]}])
        resources["security_groups"] = sgs.get("SecurityGroups", [])

        # Get subnets
        subnets = self.ec2.describe_subnets(Filters=[{"Name": "vpc-id", "Values": [vpc_id]}])
        resources["subnets"] = subnets.get("Subnets", [])

        # Get internet gateways
        igws = self.ec2.describe_internet_gateways(
            Filters=[{"Name": "attachment.vpc-id", "Values": [vpc_id]}]
        )
        resources["internet_gateways"] = igws.get("InternetGateways", [])

        # Get route tables
        rts = self.ec2.describe_route_tables(Filters=[{"Name": "vpc-id", "Values": [vpc_id]}])
        resources["route_tables"] = rts.get("RouteTables", [])

        return resources

    def get_instance_state(self, instance_id: str) -> str:
        """Get the current state of an instance."""
        try:
            response = self.ec2.describe_instances(InstanceIds=[instance_id])

            for reservation in response.get("Reservations", []):
                for instance in reservation.get("Instances", []):
                    return instance.get("State", {}).get("Name", "unknown")

            return "not-found"
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "InvalidInstanceID.NotFound":
                return "not-found"
            elif error_code == "UnauthorizedOperation":
                return "unauthorized"
            # For other errors, return error state
            return "error"
        except Exception:
            return "error"

    def terminate_instance(self, instance_id: str) -> bool:
        """Terminate a specific instance."""
        try:
            self.ec2.terminate_instances(InstanceIds=[instance_id])
            return True
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code in ["InvalidInstanceID.NotFound", "InvalidInstanceID.Malformed"]:
                # Instance already gone or invalid ID
                return True
            # Log the actual error for debugging
            import logging

            logging.getLogger(__name__).error(
                f"Error terminating instance {instance_id}: {error_code} - {str(e)}"
            )
            return False
        except Exception as e:
            import logging

            logging.getLogger(__name__).error(
                f"Unexpected error terminating instance {instance_id}: {str(e)}"
            )
            return False
