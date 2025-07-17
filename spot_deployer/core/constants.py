"""Constants and configuration values."""

# Column widths for Rich tables
class ColumnWidths:
    """Defines the widths for the Rich status table columns."""
    REGION = 15
    INSTANCE_ID = 21
    STATUS = 50
    TYPE = 15
    PUBLIC_IP = 16
    CREATED = 20
    
    @classmethod
    def get_total_width(cls):
        """Calculate total table width."""
        return (
            cls.REGION + cls.INSTANCE_ID + cls.STATUS + 
            cls.TYPE + cls.PUBLIC_IP + cls.CREATED + 
            11  # Account for borders and padding
        )

# Default values
DEFAULT_TIMEOUT = 300  # 5 minutes
DEFAULT_SSH_TIMEOUT = 120  # 2 minutes
DEFAULT_CACHE_AGE_HOURS = 24
DEFAULT_INSTANCE_TYPE = "t3.medium"
DEFAULT_STORAGE_GB = 50

# AWS constants
CANONICAL_OWNER_ID = "099720109477"  # Ubuntu AMI owner
DEFAULT_UBUNTU_AMI_PATTERN = "ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"

# File paths
DEFAULT_CONFIG_FILE = "config.yaml"
DEFAULT_STATE_FILE = "instances.json"
CACHE_DIR = ".aws_cache"

# Security group
DEFAULT_SECURITY_GROUP_NAME = "spot-deployer-sg"
DEFAULT_SECURITY_GROUP_DESC = "Simple security group for spot instances"