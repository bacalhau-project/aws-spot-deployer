"""Unit tests for AWSResourceManager."""

from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError

from spot_deployer.utils.aws_manager import AWSResourceManager


class TestAWSResourceManager:
    """Test cases for AWSResourceManager."""

    def test_initialization(self):
        """Test manager initialization."""
        manager = AWSResourceManager("us-west-2")
        assert manager.region == "us-west-2"
        assert manager._ec2 is None  # Should be lazy loaded

    def test_lazy_ec2_loading(self):
        """Test that EC2 client is created on first access."""
        manager = AWSResourceManager("us-east-1")
        assert manager._ec2 is None

        with patch("boto3.client") as mock_client:
            mock_ec2 = MagicMock()
            mock_client.return_value = mock_ec2

            # First access should create client
            client = manager.ec2
            assert client == mock_ec2
            assert manager._ec2 == mock_ec2

            # Second access should reuse existing client
            client2 = manager.ec2
            assert client2 == mock_ec2
            assert mock_client.call_count == 1

    def test_find_default_vpc_success(self):
        """Test finding default VPC and subnet."""
        manager = AWSResourceManager("us-west-2")

        # Mock the EC2 client directly
        mock_ec2 = MagicMock()
        manager._ec2 = mock_ec2

        # Mock VPC response
        mock_ec2.describe_vpcs.return_value = {"Vpcs": [{"VpcId": "vpc-12345"}]}

        # Mock subnet response
        mock_ec2.describe_subnets.return_value = {"Subnets": [{"SubnetId": "subnet-67890"}]}

        vpc_id, subnet_id = manager._find_default_vpc()

        assert vpc_id == "vpc-12345"
        assert subnet_id == "subnet-67890"

        # Verify correct filters were used
        mock_ec2.describe_vpcs.assert_called_once_with(
            Filters=[{"Name": "isDefault", "Values": ["true"]}]
        )

        mock_ec2.describe_subnets.assert_called_once_with(
            Filters=[
                {"Name": "vpc-id", "Values": ["vpc-12345"]},
                {"Name": "default-for-az", "Values": ["true"]},
            ]
        )

    def test_find_default_vpc_not_found(self):
        """Test error when no default VPC exists."""
        manager = AWSResourceManager("us-west-2")

        mock_ec2 = MagicMock()
        manager._ec2 = mock_ec2
        mock_ec2.describe_vpcs.return_value = {"Vpcs": []}

        with pytest.raises(Exception) as exc_info:
            manager._find_default_vpc()

        assert "No default VPC found" in str(exc_info.value)

    def test_terminate_instance_success(self):
        """Test successful instance termination."""
        manager = AWSResourceManager("us-west-2")

        mock_ec2 = MagicMock()
        manager._ec2 = mock_ec2
        result = manager.terminate_instance("i-12345")

        assert result is True
        mock_ec2.terminate_instances.assert_called_once_with(InstanceIds=["i-12345"])

    def test_terminate_instance_not_found(self):
        """Test terminating non-existent instance returns success."""
        manager = AWSResourceManager("us-west-2")

        mock_ec2 = MagicMock()
        manager._ec2 = mock_ec2
        # Simulate instance not found error
        error_response = {"Error": {"Code": "InvalidInstanceID.NotFound"}}
        mock_ec2.terminate_instances.side_effect = ClientError(error_response, "TerminateInstances")

        result = manager.terminate_instance("i-nonexistent")

        # Should return True even if instance doesn't exist
        assert result is True

    def test_terminate_instance_permission_error(self):
        """Test terminating instance with permission error."""
        manager = AWSResourceManager("us-west-2")

        mock_ec2 = MagicMock()
        manager._ec2 = mock_ec2
        # Simulate permission error
        error_response = {"Error": {"Code": "UnauthorizedOperation"}}
        mock_ec2.terminate_instances.side_effect = ClientError(error_response, "TerminateInstances")

        result = manager.terminate_instance("i-12345")

        # Should return False for permission errors
        assert result is False

    def test_get_instance_state_running(self):
        """Test getting state of running instance."""
        manager = AWSResourceManager("us-west-2")

        mock_ec2 = MagicMock()
        manager._ec2 = mock_ec2
        mock_ec2.describe_instances.return_value = {
            "Reservations": [{"Instances": [{"State": {"Name": "running"}}]}]
        }

        state = manager.get_instance_state("i-12345")

        assert state == "running"
        mock_ec2.describe_instances.assert_called_once_with(InstanceIds=["i-12345"])

    def test_get_instance_state_not_found(self):
        """Test getting state of non-existent instance."""
        manager = AWSResourceManager("us-west-2")

        mock_ec2 = MagicMock()
        manager._ec2 = mock_ec2
        error_response = {"Error": {"Code": "InvalidInstanceID.NotFound"}}
        mock_ec2.describe_instances.side_effect = ClientError(error_response, "DescribeInstances")

        state = manager.get_instance_state("i-nonexistent")

        assert state == "not-found"

    def test_create_security_group_success(self):
        """Test creating security group."""
        manager = AWSResourceManager("us-west-2")

        mock_ec2 = MagicMock()
        manager._ec2 = mock_ec2
        with patch("time.time", return_value=1234567890):
            mock_ec2.create_security_group.return_value = {"GroupId": "sg-12345"}

            sg_id = manager.create_security_group("vpc-12345")

            assert sg_id == "sg-12345"

            # Verify security group creation
            mock_ec2.create_security_group.assert_called_once()
            call_args = mock_ec2.create_security_group.call_args[1]
            assert call_args["VpcId"] == "vpc-12345"
            assert "spot-sg-" in call_args["GroupName"]

            # Verify ingress rules were added
            mock_ec2.authorize_security_group_ingress.assert_called_once()

    def test_find_ubuntu_ami_success(self):
        """Test finding Ubuntu AMI."""
        manager = AWSResourceManager("us-west-2")

        mock_ec2 = MagicMock()
        manager._ec2 = mock_ec2
        mock_ec2.describe_images.return_value = {
            "Images": [
                {"ImageId": "ami-old", "CreationDate": "2023-01-01"},
                {"ImageId": "ami-new", "CreationDate": "2023-12-01"},
                {"ImageId": "ami-middle", "CreationDate": "2023-06-01"},
            ]
        }

        ami_id = manager.find_ubuntu_ami()

        # Should return the newest AMI
        assert ami_id == "ami-new"

    def test_find_ubuntu_ami_not_found(self):
        """Test when no Ubuntu AMI is found."""
        manager = AWSResourceManager("us-west-2")

        mock_ec2 = MagicMock()
        manager._ec2 = mock_ec2
        mock_ec2.describe_images.return_value = {"Images": []}

        ami_id = manager.find_ubuntu_ami()

        assert ami_id is None

    def test_delete_vpc_resources_success(self):
        """Test deleting VPC and all its resources."""
        manager = AWSResourceManager("us-west-2")

        with patch.object(manager, "_get_vpc_resources") as mock_get_resources:
            mock_get_resources.return_value = {
                "instances": [{"InstanceId": "i-12345"}],
                "security_groups": [
                    {"GroupId": "sg-12345", "GroupName": "my-sg"},
                    {"GroupId": "sg-default", "GroupName": "default"},
                ],
                "subnets": [{"SubnetId": "subnet-12345"}],
                "internet_gateways": [{"InternetGatewayId": "igw-12345"}],
                "route_tables": [
                    {"RouteTableId": "rtb-12345", "Associations": []},
                    {"RouteTableId": "rtb-main", "Associations": [{"Main": True}]},
                ],
            }

            mock_ec2 = MagicMock()
            manager._ec2 = mock_ec2
            # Mock waiter
            mock_waiter = MagicMock()
            mock_ec2.get_waiter.return_value = mock_waiter

            result = manager.delete_vpc_resources("vpc-12345")

            assert result is True

            # Verify correct deletion order
            mock_ec2.terminate_instances.assert_called_once_with(InstanceIds=["i-12345"])
            mock_waiter.wait.assert_called_once()

            # Only non-default security group should be deleted
            mock_ec2.delete_security_group.assert_called_once_with(GroupId="sg-12345")

            mock_ec2.delete_subnet.assert_called_once_with(SubnetId="subnet-12345")

            mock_ec2.detach_internet_gateway.assert_called_once()
            mock_ec2.delete_internet_gateway.assert_called_once()

            # Only non-main route table should be deleted
            mock_ec2.delete_route_table.assert_called_once_with(RouteTableId="rtb-12345")

            mock_ec2.delete_vpc.assert_called_once_with(VpcId="vpc-12345")

    def test_create_dedicated_vpc(self):
        """Test creating a dedicated VPC with all resources."""
        manager = AWSResourceManager("us-west-2")

        mock_ec2 = MagicMock()
        manager._ec2 = mock_ec2
        with patch.object(manager, "_get_first_az") as mock_get_az:
            mock_get_az.return_value = "us-west-2a"

            # Mock responses
            mock_ec2.create_vpc.return_value = {"Vpc": {"VpcId": "vpc-new"}}
            mock_ec2.create_subnet.return_value = {"Subnet": {"SubnetId": "subnet-new"}}
            mock_ec2.create_internet_gateway.return_value = {
                "InternetGateway": {"InternetGatewayId": "igw-new"}
            }
            mock_ec2.create_route_table.return_value = {"RouteTable": {"RouteTableId": "rtb-new"}}

            vpc_id, subnet_id = manager._create_dedicated_vpc("test-deployment")

            assert vpc_id == "vpc-new"
            assert subnet_id == "subnet-new"

            # Verify VPC creation and configuration
            mock_ec2.create_vpc.assert_called_once_with(CidrBlock="10.0.0.0/16")
            assert mock_ec2.modify_vpc_attribute.call_count == 2  # DNS settings

            # Verify subnet creation
            mock_ec2.create_subnet.assert_called_once_with(
                VpcId="vpc-new", CidrBlock="10.0.1.0/24", AvailabilityZone="us-west-2a"
            )

            # Verify IGW and routing
            mock_ec2.create_internet_gateway.assert_called_once()
            mock_ec2.attach_internet_gateway.assert_called_once()
            mock_ec2.create_route_table.assert_called_once()
            mock_ec2.create_route.assert_called_once()
            mock_ec2.associate_route_table.assert_called_once()

            # Verify tagging
            assert mock_ec2.create_tags.call_count == 4  # VPC, subnet, IGW, RT
