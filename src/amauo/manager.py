"""
SPAT-based Cluster Manager - Core cluster operations.

Handles AWS spot instance deployment and management using the proven SPAT architecture
instead of SkyPilot Docker containers. Provides compatibility layer for existing CLI.
"""

import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from rich.console import Console

from .config_adapter import ConfigAdapter
from .core.config import SimpleConfig
from .core.state import SimpleStateManager
from .commands import cmd_create, cmd_destroy, cmd_list


class ClusterManager:
    """
    Compatibility layer that bridges the old SkyPilot-based interface 
    to the new SPAT-based architecture.
    """

    def __init__(
        self,
        log_to_console: bool = False,
        log_file: str = "cluster-deploy.log", 
        debug: bool = False,
    ):
        self.console = Console()
        self.log_to_console = log_to_console
        self.log_file = Path(log_file)
        self.debug = debug

        # Initialize SPAT components
        self.config: Optional[SimpleConfig] = None
        self.state: Optional[SimpleStateManager] = None

    def log(self, level: str, message: str, style: str = "") -> None:
        """Log message to console and/or file."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if self.log_to_console:
            self.console.print(f"[{level}] {message}", style=style)
        else:
            # Write to file
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] [{level}] {message}\n")
            # Also show brief status to console
            self.console.print(f"[{level}] {message}", style=style)

    def log_info(self, message: str) -> None:
        """Log info message."""
        self.log("INFO", message, "blue")

    def log_success(self, message: str) -> None:
        """Log success message."""
        self.log("SUCCESS", message, "green")

    def log_warning(self, message: str) -> None:
        """Log warning message."""
        self.log("WARNING", message, "yellow")

    def log_error(self, message: str) -> None:
        """Log error message."""
        self.log("ERROR", message, "red")

    def log_header(self, message: str) -> None:
        """Log header message."""
        if self.log_to_console:
            self.console.print(f"\n🌍 {message}", style="bold blue")
            self.console.print()
        else:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(f"\n[{timestamp}] [HEADER] 🌍 {message}\n\n")
            self.console.print(f"\n🌍 {message}", style="bold blue")
            self.console.print()

    def _ensure_config_migrated(self, config_file: str) -> bool:
        """Ensure configuration is migrated from cluster.yaml to config.yaml."""
        cluster_file = Path("cluster.yaml")
        spat_config_file = Path("config.yaml")

        # If we have a cluster.yaml but no config.yaml, migrate automatically
        if cluster_file.exists() and not spat_config_file.exists():
            self.log_info("Found cluster.yaml but no config.yaml - migrating automatically")
            try:
                adapter = ConfigAdapter()
                adapter.convert_full_migration("cluster.yaml", "config.yaml")
                self.log_success("Migration completed - using config.yaml")
                return True
            except Exception as e:
                self.log_error(f"Failed to migrate cluster.yaml: {e}")
                self.log_error("Please run 'amauo migrate' or create config.yaml manually")
                return False

        # If we have the specific config file requested
        requested_config = Path(config_file)
        if requested_config.exists():
            return True

        # Config file doesn't exist
        self.log_error(f"Configuration file not found: {config_file}")
        
        if cluster_file.exists():
            self.log_info("Found cluster.yaml - run 'amauo migrate' to convert to SPAT format")
        else:
            self.log_info("Run 'amauo setup' to create initial configuration")
        
        return False

    def _initialize_spat_components(self, config_file: str = "config.yaml") -> bool:
        """Initialize SPAT configuration and state managers."""
        try:
            if not self._ensure_config_migrated(config_file):
                return False

            self.config = SimpleConfig(config_file)
            self.state = SimpleStateManager()
            return True
        except Exception as e:
            self.log_error(f"Failed to initialize SPAT components: {e}")
            return False

    def check_prerequisites(self) -> bool:
        """Check prerequisites (replaces Docker/SkyPilot checks with AWS checks)."""
        self.log_header("Checking Prerequisites")

        # Initialize SPAT components
        if not self._initialize_spat_components():
            return False

        # Check AWS credentials
        try:
            import boto3
            from botocore.exceptions import ClientError, NoCredentialsError

            try:
                sts = boto3.client("sts")
                response = sts.get_caller_identity()
                account_id = response.get("Account")
                arn = response.get("Arn", "unknown")
                user = arn.split("/")[-1] if "/" in arn else "unknown"
                
                self.log_success(f"AWS credentials valid (Account: {account_id}, User: {user})")
                
            except NoCredentialsError:
                self.log_error("No AWS credentials found")
                self.log_error("Configure credentials with: aws configure")
                self.log_error("Or use: aws sso login")
                return False
            except ClientError as e:
                error_code = e.response.get("Error", {}).get("Code", "")
                if error_code == "ExpiredToken":
                    self.log_error("AWS credentials expired")
                    self.log_error("Refresh with: aws sso login")
                elif error_code in ["InvalidUserID.NotFound", "AccessDenied"]:
                    self.log_error("AWS credentials invalid or insufficient permissions")
                else:
                    self.log_error(f"AWS credential error: {e}")
                return False

            # Check SSH keys if configured
            if self.config:
                public_key_path = self.config.public_ssh_key_path()
                private_key_path = self.config.private_ssh_key_path()

                if public_key_path:
                    pub_key_file = Path(os.path.expanduser(public_key_path))
                    if pub_key_file.exists():
                        self.log_success(f"SSH public key found: {public_key_path}")
                    else:
                        self.log_error(f"SSH public key not found: {public_key_path}")
                        return False

                if private_key_path:
                    priv_key_file = Path(os.path.expanduser(private_key_path))
                    if priv_key_file.exists():
                        self.log_success(f"SSH private key found: {private_key_path}")
                    else:
                        self.log_error(f"SSH private key not found: {private_key_path}")
                        return False

            return True

        except ImportError:
            self.log_error("boto3 not available - install with: pip install boto3")
            return False
        except Exception as e:
            self.log_error(f"Prerequisites check failed: {e}")
            return False

    def deploy_cluster(self, config_file: str = "config.yaml", follow: bool = False) -> bool:
        """Deploy cluster using SPAT architecture."""
        if not self._initialize_spat_components(config_file):
            return False

        self.log_header("Deploying Bacalhau Compute Nodes")

        try:
            # Use SPAT create command
            cmd_create(self.config, self.state)
            self.log_success("Deployment completed successfully!")
            return True

        except KeyboardInterrupt:
            self.log_warning("Deployment interrupted by user")
            return False
        except Exception as e:
            self.log_error(f"Deployment failed: {e}")
            return False

    def destroy_cluster(self) -> bool:
        """Destroy cluster using SPAT architecture."""
        if not self._initialize_spat_components():
            return False

        self.log_header("Destroying All Instances")

        try:
            cmd_destroy(self.state)
            self.log_success("All instances destroyed successfully!")
            return True

        except KeyboardInterrupt:
            self.log_warning("Destruction interrupted by user") 
            return False
        except Exception as e:
            self.log_error(f"Destruction failed: {e}")
            return False

    def show_status(self) -> bool:
        """Show cluster status using SPAT architecture."""
        if not self._initialize_spat_components():
            return False

        try:
            cmd_list(self.state)
            return True
        except Exception as e:
            self.log_error(f"Status failed: {e}")
            return False

    def list_nodes(self) -> bool:
        """List nodes using SPAT architecture."""
        return self.show_status()

    def ssh_cluster(self) -> bool:
        """SSH functionality - provide guidance for SPAT approach."""
        if not self._initialize_spat_components():
            return False

        instances = self.state.load_instances()
        if not instances:
            self.log_error("No running instances found")
            return False

        # Show available instances for SSH
        self.log_info("Available instances for SSH:")
        for i, instance in enumerate(instances[:3]):  # Show first 3
            public_ip = instance.get("public_ip")
            instance_id = instance.get("id")
            region = instance.get("region")
            
            if public_ip and public_ip != "pending":
                username = self.config.username() if self.config else "ubuntu"
                private_key_path = self.config.private_ssh_key_path() if self.config else "~/.ssh/id_rsa"
                
                self.console.print(f"  {i+1}. [{region}] {instance_id}")
                self.console.print(f"     ssh -i {private_key_path} {username}@{public_ip}")

        if len(instances) > 3:
            self.console.print(f"     ... and {len(instances) - 3} more (use 'amauo list' to see all)")

        return True

    def show_logs(self) -> bool:
        """Show deployment logs."""
        if self.log_file.exists():
            self.log_info(f"Showing logs from {self.log_file}")
            with open(self.log_file) as f:
                print(f.read())
            return True
        else:
            self.log_error(f"Log file not found: {self.log_file}")
            return False

    def monitor_deployments(self, follow: bool = False) -> bool:
        """Monitor deployments using SPAT approach."""
        if not self._initialize_spat_components():
            return False

        self.log_header("Deployment Monitor")
        
        # Show current instances
        self.show_status()

        if follow:
            self.log_info("Use 'amauo list' to refresh instance status")
            self.log_info("Logs are available in: {}".format(self.log_file))

        return True

    def cleanup_docker(self) -> bool:
        """Cleanup - no Docker containers to clean in SPAT approach."""
        self.log_info("No Docker containers to clean up (SPAT uses native AWS deployment)")
        return True

    def debug_container_credentials(self) -> None:
        """Debug function - show AWS credentials instead of container credentials."""
        self.log_info("AWS credential debug information:")
        
        try:
            import boto3
            
            # Show current AWS identity
            sts = boto3.client("sts")
            response = sts.get_caller_identity()
            
            self.log_info(f"Account: {response.get('Account')}")
            self.log_info(f"ARN: {response.get('Arn')}")
            self.log_info(f"User ID: {response.get('UserId')}")

            # Show available regions
            ec2 = boto3.client("ec2")
            regions = ec2.describe_regions()
            available_regions = [r["RegionName"] for r in regions["Regions"]]
            self.log_info(f"Available regions: {', '.join(available_regions[:10])}...")

        except Exception as e:
            self.log_error(f"AWS debug failed: {e}")

    def get_cluster_name_from_config(self, config_file: str = "config.yaml") -> str:
        """Get cluster name - return a default name for SPAT."""
        return "amauo-cluster"

    def load_cluster_config(self, config_file: str = "config.yaml") -> dict:
        """Load configuration - compatibility method."""
        if not self._initialize_spat_components(config_file):
            return {}
        
        return self.config.data if self.config else {}

    def get_sky_cluster_name(self) -> Optional[str]:
        """Get cluster name - compatibility method for SPAT."""
        instances = self.state.load_instances() if self.state else []
        return "amauo-cluster" if instances else None