"""Configuration validator - ensures configuration is valid before operations."""

import os

import yaml

from ..utils.ui_manager import UIManager


class ConfigValidator:
    """Validates spot deployer configuration files."""

    def __init__(self) -> None:
        """Initialize the configuration validator."""
        self.ui = UIManager()
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def validate_config_file(self, config_path: str) -> tuple[bool, dict]:
        """
        Validate a configuration file.

        Returns:
            Tuple of (is_valid, config_dict)
        """
        self.errors = []
        self.warnings = []

        # Check file exists
        if not os.path.exists(config_path):
            self.errors.append(f"Configuration file not found: {config_path}")
            return False, {}

        # Load and parse YAML
        try:
            with open(config_path) as f:
                config = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            self.errors.append(f"Invalid YAML syntax: {e}")
            return False, {}
        except Exception as e:
            self.errors.append(f"Error reading config file: {e}")
            return False, {}

        # Validate structure
        self._validate_structure(config)

        # Validate AWS section
        if "aws" in config:
            self._validate_aws_section(config["aws"])

        # Validate regions
        if "regions" in config:
            self._validate_regions(config["regions"])
        else:
            self.errors.append("Missing required 'regions' section")

        # Print validation results
        self._print_validation_results()

        return len(self.errors) == 0, config

    def _validate_structure(self, config: dict) -> None:
        """Validate overall configuration structure."""
        # Check required top-level keys
        required_keys = ["aws", "regions"]
        for key in required_keys:
            if key not in config:
                self.errors.append(f"Missing required section: '{key}'")

        # Check for unknown top-level keys
        valid_keys = {"aws", "regions"}
        unknown_keys = set(config.keys()) - valid_keys
        if unknown_keys:
            self.warnings.append(
                f"Unknown configuration keys: {', '.join(unknown_keys)}"
            )

    def _validate_aws_section(self, aws_config: dict) -> None:
        """Validate AWS configuration section."""
        # Required fields
        required_fields = {
            "total_instances": "Number of instances to create",
            "username": "SSH username for instances",
        }

        for field, description in required_fields.items():
            if field not in aws_config:
                self.errors.append(
                    f"Missing required AWS field '{field}' ({description})"
                )

        # Validate SSH keys
        if "public_ssh_key_path" in aws_config:
            self._validate_ssh_key(aws_config["public_ssh_key_path"], "public")
        else:
            self.warnings.append(
                "No 'public_ssh_key_path' specified - instances will not be accessible via SSH"
            )

        if "private_ssh_key_path" in aws_config:
            self._validate_ssh_key(aws_config["private_ssh_key_path"], "private")

        # Validate numeric fields
        if "total_instances" in aws_config:
            instances = aws_config["total_instances"]
            if not isinstance(instances, int) or instances < 0:
                self.errors.append(
                    f"'total_instances' must be a positive integer, got: {instances}"
                )
            elif instances == 0:
                self.warnings.append(
                    "'total_instances' is 0 - no instances will be created"
                )
            elif instances > 100:
                self.warnings.append(
                    f"'total_instances' is {instances} - this may be expensive!"
                )

        if "instance_storage_gb" in aws_config:
            storage = aws_config["instance_storage_gb"]
            if not isinstance(storage, (int, float)) or storage < 8:
                self.errors.append(
                    f"'instance_storage_gb' must be at least 8 GB, got: {storage}"
                )

        if "spot_price_limit" in aws_config:
            price = aws_config["spot_price_limit"]
            if not isinstance(price, (int, float)) or price <= 0:
                self.errors.append(f"'spot_price_limit' must be positive, got: {price}")

        # Validate file/script directories
        if "files_directory" in aws_config:
            self._validate_directory(aws_config["files_directory"], "files_directory")

        if "scripts_directory" in aws_config:
            self._validate_directory(
                aws_config["scripts_directory"], "scripts_directory"
            )

        # Validate boolean fields
        bool_fields = ["use_dedicated_vpc", "ensure_default_vpc", "associate_public_ip"]
        for field in bool_fields:
            if field in aws_config and not isinstance(aws_config[field], bool):
                self.errors.append(
                    f"'{field}' must be true or false, got: {aws_config[field]}"
                )

    def _validate_ssh_key(self, key_path: str, key_type: str) -> None:
        """Validate SSH key file exists and has correct permissions."""
        expanded_path = os.path.expanduser(key_path)

        if not os.path.exists(expanded_path):
            self.errors.append(f"{key_type.capitalize()} SSH key not found: {key_path}")
            return

        # Check permissions for private key
        if key_type == "private":
            stat_info = os.stat(expanded_path)
            mode = stat_info.st_mode & 0o777
            if mode != 0o600:
                self.warnings.append(
                    f"Private SSH key has insecure permissions ({oct(mode)}). "
                    f"Run: chmod 600 {key_path}"
                )

    def _validate_directory(self, dir_path: str, field_name: str) -> None:
        """Validate directory exists."""
        if not os.path.exists(dir_path):
            self.warnings.append(f"Directory for '{field_name}' not found: {dir_path}")

    def _validate_regions(self, regions: list) -> None:
        """Validate regions configuration."""
        if not isinstance(regions, list):
            self.errors.append("'regions' must be a list")  # type: ignore[unreachable]
            return

        if not regions:
            self.errors.append("At least one region must be specified")
            return

        valid_regions = {
            "us-east-1",
            "us-east-2",
            "us-west-1",
            "us-west-2",
            "eu-west-1",
            "eu-west-2",
            "eu-west-3",
            "eu-central-1",
            "ap-southeast-1",
            "ap-southeast-2",
            "ap-northeast-1",
            "ap-northeast-2",
            "ap-south-1",
            "sa-east-1",
            "ca-central-1",
        }

        seen_regions = set()

        for i, region_config in enumerate(regions):
            if not isinstance(region_config, dict):
                self.errors.append(f"Region entry {i + 1} must be a dictionary")
                continue

            if len(region_config) != 1:
                self.errors.append(
                    f"Region entry {i + 1} must have exactly one region key"
                )
                continue

            region_name = list(region_config.keys())[0]

            # Check for duplicate regions
            if region_name in seen_regions:
                self.errors.append(f"Duplicate region: {region_name}")
            seen_regions.add(region_name)

            # Warn about unknown regions
            if region_name not in valid_regions:
                self.warnings.append(
                    f"Unknown AWS region: {region_name} (might be valid but uncommon)"
                )

            # Validate region config
            region_data = region_config[region_name]
            if not isinstance(region_data, dict):
                self.errors.append(
                    f"Configuration for region {region_name} must be a dictionary"
                )
                continue

            # Check machine type
            if "machine_type" not in region_data:
                self.errors.append(f"Missing 'machine_type' for region {region_name}")
            else:
                machine_type = region_data["machine_type"]
                # Basic validation of instance type format
                if not isinstance(machine_type, str) or not machine_type:
                    self.errors.append(
                        f"Invalid machine_type for {region_name}: {machine_type}"
                    )
                elif "." not in machine_type:
                    self.warnings.append(
                        f"Unusual machine_type format for {region_name}: {machine_type}"
                    )

            # Check image
            if "image" not in region_data:
                self.warnings.append(
                    f"No 'image' specified for {region_name}, will use 'auto'"
                )
            elif region_data["image"] not in ["auto", "latest"] and not region_data[
                "image"
            ].startswith("ami-"):
                self.warnings.append(
                    f"Image for {region_name} should be 'auto' or an AMI ID (ami-...)"
                )

    def _print_validation_results(self) -> None:
        """Print validation errors and warnings."""
        if self.errors:
            self.ui.print_error("Configuration validation failed:")
            for error in self.errors:
                self.ui.console.print(f"  ❌ {error}")

        if self.warnings:
            if not self.errors:
                self.ui.print_warning("Configuration warnings:")
            for warning in self.warnings:
                self.ui.console.print(f"  ⚠️  {warning}")

    def validate_runtime_environment(self) -> bool:
        """Validate the runtime environment is properly configured."""
        env_errors = []

        # Check AWS credentials
        try:
            import boto3

            sts = boto3.client("sts")
            sts.get_caller_identity()
        except Exception:
            env_errors.append(
                "AWS credentials not configured. Run 'aws configure' or set AWS_PROFILE"
            )

        # Check for required commands
        required_commands = [
            ("ssh", "SSH client"),
            ("scp", "SCP for file transfer"),
        ]

        for cmd, description in required_commands:
            if not self._command_exists(cmd):
                env_errors.append(
                    f"{description} not found: '{cmd}' command is required"
                )

        if env_errors:
            self.ui.print_error("Environment validation failed:")
            for error in env_errors:
                self.ui.console.print(f"  ❌ {error}")
            return False

        return True

    def _command_exists(self, command: str) -> bool:
        """Check if a command exists in PATH."""
        import shutil

        return shutil.which(command) is not None

    def suggest_fixes(self) -> None:
        """Suggest fixes for common configuration issues."""
        if not self.errors:
            return

        self.ui.console.print("\n[bold cyan]Suggested fixes:[/bold cyan]")

        # SSH key suggestions
        ssh_key_errors = [e for e in self.errors if "SSH key" in e]
        if ssh_key_errors:
            self.ui.console.print("\nTo generate SSH keys:")
            self.ui.console.print("  ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N ''")

        # Missing sections
        missing_sections = [e for e in self.errors if "Missing required section" in e]
        if missing_sections:
            self.ui.console.print("\nMinimal configuration example:")
            self.ui.console.print("""
aws:
  total_instances: 2
  username: ubuntu
  public_ssh_key_path: ~/.ssh/id_ed25519.pub
  private_ssh_key_path: ~/.ssh/id_ed25519
regions:
  - us-east-2:
      machine_type: t3.micro
      image: auto
""")
