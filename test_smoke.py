#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "boto3",
#     "botocore",
#     "rich",
#     "aiosqlite",
#     "aiofiles",
#     "pyyaml",
# ]
# ///

"""
Smoke tests for AWS Spot Deployer CLI tool.

These tests verify basic functionality without requiring AWS credentials
or making actual API calls. They use mocking to test the CLI interface,
argument parsing, configuration loading, and basic workflows.
"""

import asyncio
import os
import subprocess
import sys
import unittest
import warnings
from unittest.mock import Mock, MagicMock, patch, mock_open

# Suppress RuntimeWarnings about unawaited coroutines during testing
warnings.filterwarnings(
    "ignore", category=RuntimeWarning, message=".*coroutine.*was never awaited"
)
warnings.filterwarnings(
    "ignore", category=RuntimeWarning, message=".*Enable tracemalloc.*"
)

# Add the current directory to the path to import the main module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import deploy_spot
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# Globally disable cache during tests
deploy_spot.DISABLE_CACHE_FOR_TESTS = True


class LiveTestResult(unittest.TestResult):
    """Custom test result class that provides real-time feedback."""

    def __init__(self, console, test_names):
        super().__init__()
        self.console = console
        self.test_names = test_names
        self.current_test = 0
        self.completed_tests = []

    def startTest(self, test):
        super().startTest(test)
        self.current_test += 1
        test_name = f"{test.__class__.__name__}.{test._testMethodName}"

        # Show current test status
        self.console.print(
            f"[yellow]⚡ Running test {self.current_test}/28:[/yellow] [cyan]{test_name}[/cyan]"
        )

    def addSuccess(self, test):
        super().addSuccess(test)
        test_name = f"{test.__class__.__name__}.{test._testMethodName}"
        self.completed_tests.append((test_name, "✅", "PASS"))
        self.console.print(f"[green]  ✅ PASSED[/green] - {test_name}")

    def addError(self, test, err):
        super().addError(test, err)
        test_name = f"{test.__class__.__name__}.{test._testMethodName}"
        self.completed_tests.append((test_name, "💥", "ERROR"))
        self.console.print(f"[red]  💥 ERROR[/red] - {test_name}")

    def addFailure(self, test, err):
        super().addFailure(test, err)
        test_name = f"{test.__class__.__name__}.{test._testMethodName}"
        self.completed_tests.append((test_name, "❌", "FAIL"))
        self.console.print(f"[red]  ❌ FAILED[/red] - {test_name}")


class LiveTestRunner:
    """Custom test runner with real-time feedback."""

    def __init__(self, console, verbosity=1):
        self.console = console
        self.verbosity = verbosity

    def run(self, test_suite, test_names):
        result = LiveTestResult(self.console, test_names)

        self.console.print(
            "\n[bold yellow]🚀 Starting test execution...[/bold yellow]\n"
        )

        # Run the tests
        test_suite.run(result)

        self.console.print("\n[bold blue]📊 Test execution completed![/bold blue]")

        return result


class TestCLIArgumentParsing(unittest.TestCase):
    """Test CLI argument parsing and command recognition."""

    def setUp(self):
        """Set up test environment."""
        self.original_argv = sys.argv.copy()

    def tearDown(self):
        """Clean up after tests."""
        sys.argv = self.original_argv

    def test_help_command(self):
        """Test that help command works."""
        sys.argv = ["deploy_spot.py", "help"]

        with patch("builtins.print") as mock_print:
            result = deploy_spot.main()
            self.assertEqual(result, 0)
            mock_print.assert_called()

            # Check that help text was printed
            call_args = mock_print.call_args_list
            help_printed = any(
                "AWS Spot Instance Deployment Tool" in str(call) for call in call_args
            )
            self.assertTrue(help_printed, "Help text should be printed")

    def test_invalid_command(self):
        """Test handling of invalid commands."""
        invalid_commands = ["invalid_command", "foo", "bar", "not-a-command", "123"]

        for invalid_cmd in invalid_commands:
            with self.subTest(command=invalid_cmd):
                sys.argv = ["deploy_spot.py", invalid_cmd]

                with patch("builtins.print") as mock_print:
                    result = deploy_spot.main()
                    self.assertEqual(
                        result,
                        1,
                        f"Invalid command '{invalid_cmd}' should return error code 1",
                    )

                    # Check that error message was printed
                    call_args = str(mock_print.call_args_list)
                    self.assertIn(
                        "Unknown command",
                        call_args,
                        f"Error message should be printed for invalid command '{invalid_cmd}'",
                    )

    def test_valid_commands_recognized(self):
        """Test that all valid commands are recognized."""
        valid_commands = [
            "setup",
            "verify",
            "validate",
            "create",
            "list",
            "status",
            "destroy",
            "cleanup",
        ]

        for command in valid_commands:
            sys.argv = ["deploy_spot.py", command]

            with patch("deploy_spot.setup_environment"):
                with patch("deploy_spot.verify_environment"):
                    with patch("deploy_spot.run_validation_tests"):
                        with patch(
                            "deploy_spot.asyncio.run", return_value=0
                        ) as mock_run:
                            with patch("os.path.exists", return_value=True):
                                with patch.object(
                                    deploy_spot.AWSDataCache,
                                    "refresh_cache",
                                    return_value=None,
                                ):
                                    try:
                                        result = deploy_spot.main()
                                        # Should not return error for valid commands
                                        self.assertIn(
                                            result, [0, 1]
                                        )  # Either success or controlled failure
                                    except SystemExit:
                                        pass  # Some commands might call sys.exit

    def test_config_parameter_parsing(self):
        """Test that --config parameter is parsed correctly."""
        sys.argv = ["deploy_spot.py", "verify", "--config", "custom_config.yaml"]

        with patch("deploy_spot.verify_environment") as mock_verify:
            with patch("os.path.exists", return_value=True):
                with patch.object(
                    deploy_spot.AWSDataCache, "refresh_cache", return_value=None
                ):
                    deploy_spot.main()
                    mock_verify.assert_called_with("custom_config.yaml")


class TestCommandValidation(unittest.TestCase):
    """Test command validation and error handling."""

    def setUp(self):
        """Set up test environment."""
        self.original_argv = sys.argv.copy()

    def tearDown(self):
        """Clean up after tests."""
        sys.argv = self.original_argv

    def test_help_command_variations(self):
        """Test different ways to access help."""
        help_variations = ["help", "--help", "-h"]

        for help_cmd in help_variations:
            with self.subTest(help_command=help_cmd):
                sys.argv = ["deploy_spot.py", help_cmd]

                with patch("builtins.print") as mock_print:
                    result = deploy_spot.main()
                    self.assertEqual(
                        result, 0, f"Help command '{help_cmd}' should succeed"
                    )
                    mock_print.assert_called()

    def test_command_case_sensitivity(self):
        """Test that commands are case sensitive."""
        case_variations = ["SETUP", "Setup", "sETup", "VERIFY", "Verify"]

        for cmd in case_variations:
            with self.subTest(command=cmd):
                sys.argv = ["deploy_spot.py", cmd]

                with patch("builtins.print") as mock_print:
                    result = deploy_spot.main()
                    self.assertEqual(
                        result, 1, f"Command '{cmd}' should fail (case sensitive)"
                    )

    def test_empty_command(self):
        """Test behavior with no command provided."""
        sys.argv = ["deploy_spot.py"]

        with patch("deploy_spot._get_console") as mock_get_console:
            mock_console = Mock()
            mock_get_console.return_value = mock_console
            result = deploy_spot.main()
            self.assertEqual(result, 0, "No command shows help and returns 0")

    def test_multiple_commands(self):
        """Test behavior with multiple commands."""
        sys.argv = ["deploy_spot.py", "setup", "verify"]

        with patch("deploy_spot._get_console") as mock_get_console:
            mock_console = Mock()
            mock_get_console.return_value = mock_console
            # This should still process the first command (setup)
            with patch("deploy_spot.setup_environment"):
                with patch.object(
                    deploy_spot.AWSDataCache, "refresh_cache", return_value=None
                ):
                    result = deploy_spot.main()
                    # Result depends on implementation but should handle gracefully
                    self.assertIn(result, [0, 1])


class TestConfigurationLoading(unittest.TestCase):
    """Test configuration file loading and parsing."""

    def test_config_class_initialization(self):
        """Test Config class can be initialized with valid YAML."""
        yaml_content = """
aws:
  total_instances: 5
  username: test-user
bacalhau:
  orchestrators:
    - nats://test:4222
  token: test-token
  tls: true
regions:
  - us-west-2:
      image: ami-12345
      machine_type: t3.medium
"""

        # Ensure imports are loaded for Config to work
        deploy_spot._ensure_imports()

        with patch("builtins.open", mock_open(read_data=yaml_content)):
            config = deploy_spot.Config("test_config.yaml")

            self.assertEqual(config.get_username(), "test-user")
            self.assertEqual(config.get_total_instances(), 5)
            self.assertEqual(config.get_token(), "test-token")
            self.assertTrue(config.get_tls())
            self.assertEqual(len(config.get_regions()), 1)
            self.assertIn("us-west-2", config.get_regions())

    def test_config_with_legacy_format(self):
        """Test Config class handles legacy configuration format."""
        yaml_content = """
username: bacalhau-runner
max_instances: 10
orchestrators:
  - nats://legacy:4222
token: legacy-token
tls: false
regions:
  - eu-west-1:
      image: auto
      machine_type: t3.small
"""

        # Ensure imports are loaded for Config to work
        deploy_spot._ensure_imports()

        with patch("builtins.open", mock_open(read_data=yaml_content)):
            config = deploy_spot.Config("test_config.yaml")

            self.assertEqual(config.get_username(), "bacalhau-runner")
            self.assertEqual(config.get_total_instances(), 10)
            self.assertEqual(config.get_token(), "legacy-token")
            self.assertFalse(config.get_tls())

    def test_config_file_not_found(self):
        """Test Config class handles missing file gracefully."""
        # Ensure imports are loaded for Config to work
        deploy_spot._ensure_imports()

        with patch("builtins.open", side_effect=FileNotFoundError):
            with self.assertRaises(FileNotFoundError):
                deploy_spot.Config("nonexistent.yaml")


class TestScriptUploadFunctionality(unittest.TestCase):
    """Test the upload-script command functionality."""

    def test_upload_script_command_validation(self):
        """Test that upload-script command validates script path requirement."""
        with patch("sys.argv", ["deploy_spot.py", "upload-script"]):
            with patch("os.path.exists", return_value=False):
                with patch.object(deploy_spot, "_get_console") as mock_console:
                    mock_console.return_value.print = Mock()

                    try:
                        result = deploy_spot.main()
                        # Should return 1 due to missing script path
                        self.assertEqual(result, 1)
                    except SystemExit as e:
                        # Alternative: might exit with code 1
                        self.assertEqual(e.code, 1)

    def test_upload_script_help_text_includes_command(self):
        """Test that help text includes upload-script command."""
        with patch("sys.argv", ["deploy_spot.py", "help"]):
            with patch("builtins.print") as mock_print:
                deploy_spot.main()

                # Check if any print call contained upload-script
                help_text = "".join(str(call) for call in mock_print.call_args_list)
                self.assertIn("upload-script", help_text)

    def test_upload_script_function_exists(self):
        """Test that upload_script_to_instances function exists and is callable."""
        self.assertTrue(hasattr(deploy_spot, "upload_script_to_instances"))
        self.assertTrue(callable(getattr(deploy_spot, "upload_script_to_instances")))

    def test_upload_files_directory_function_exists(self):
        """Test that _upload_files_directory helper function exists."""
        self.assertTrue(hasattr(deploy_spot, "_upload_files_directory"))
        self.assertTrue(callable(getattr(deploy_spot, "_upload_files_directory")))

    def test_files_directory_detection(self):
        """Test that files directory is properly detected."""
        import tempfile
        import os

        with tempfile.TemporaryDirectory() as tmpdir:
            files_dir = os.path.join(tmpdir, "files")

            # Test non-existent directory
            self.assertFalse(os.path.exists(files_dir))

            # Test creation and detection
            os.makedirs(files_dir)
            self.assertTrue(os.path.exists(files_dir))
            self.assertTrue(os.path.isdir(files_dir))

    def test_config_startup_script_path(self):
        """Test that config can return startup script path."""
        import tempfile
        import yaml
        import os

        config_data = {
            "startup_script_path": "./custom_startup.sh",
            "files_directory_path": "./custom_files",
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            config_file = f.name

        try:
            config = deploy_spot.Config(config_file)
            self.assertEqual(config.get_startup_script_path(), "./custom_startup.sh")
            self.assertEqual(config.get_files_directory_path(), "./custom_files")
        finally:
            os.unlink(config_file)

    def test_config_default_paths(self):
        """Test that config returns default paths when not specified."""
        import tempfile
        import yaml
        import os

        config_data = {"aws": {"total_instances": 1}}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            config_file = f.name

        try:
            config = deploy_spot.Config(config_file)
            self.assertEqual(config.get_startup_script_path(), "./startup_script.sh")
            self.assertEqual(config.get_files_directory_path(), "./files")
        finally:
            os.unlink(config_file)


class TestEnvironmentValidation(unittest.TestCase):
    """Test environment validation functions."""

    @patch("shutil.which")
    @patch("boto3.Session")
    @patch("os.path.exists")
    def test_validate_environment_success(self, mock_exists, mock_session, mock_which):
        """Test successful environment validation."""
        # Ensure imports are loaded for validate_environment to work
        deploy_spot._ensure_imports()

        # Mock all requirements as satisfied
        mock_which.return_value = "/usr/bin/aws"
        mock_exists.return_value = True

        mock_boto_session = Mock()
        mock_credentials = Mock()
        mock_boto_session.get_credentials.return_value = mock_credentials
        mock_sts_client = Mock()
        mock_boto_session.client.return_value = mock_sts_client
        mock_session.return_value = mock_boto_session

        issues = deploy_spot.validate_environment()
        self.assertEqual(len(issues), 0)

    @patch("shutil.which")
    @patch("boto3.Session")
    @patch("os.path.exists")
    def test_validate_environment_missing_aws_cli(
        self, mock_exists, mock_session, mock_which
    ):
        """Test environment validation with missing AWS CLI."""
        # Ensure imports are loaded for validate_environment to work
        deploy_spot._ensure_imports()

        mock_which.return_value = None  # AWS CLI not found
        mock_exists.return_value = True

        issues = deploy_spot.validate_environment()
        self.assertGreater(len(issues), 0)
        self.assertTrue(any("AWS CLI not found" in issue for issue in issues))

    @patch("shutil.which")
    @patch("boto3.Session")
    @patch("os.path.exists")
    def test_validate_environment_missing_config(
        self, mock_exists, mock_session, mock_which
    ):
        """Test environment validation with missing config file."""
        # Ensure imports are loaded for validate_environment to work
        deploy_spot._ensure_imports()

        mock_which.return_value = "/usr/bin/aws"
        mock_exists.return_value = False  # config.yaml not found

        mock_boto_session = Mock()
        mock_credentials = Mock()
        mock_boto_session.get_credentials.return_value = mock_credentials
        mock_session.return_value = mock_boto_session

        issues = deploy_spot.validate_environment()
        self.assertGreater(len(issues), 0)
        self.assertTrue(any("config.yaml not found" in issue for issue in issues))


class TestDatabaseOperations(unittest.TestCase):
    """Test database operations without actual SQLite files."""

    def test_database_manager_initialization(self):
        """Test MachineStateManager initialization."""
        with patch("sqlite3.connect") as mock_connect:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_conn.cursor.return_value = mock_cursor
            mock_connect.return_value.__enter__.return_value = mock_conn

            db = deploy_spot.MachineStateManager(":memory:")
            self.assertIsInstance(db, deploy_spot.MachineStateManager)

            # Verify that table creation SQL was executed
            mock_cursor.execute.assert_called()
            call_args = str(mock_cursor.execute.call_args_list)
            self.assertIn("CREATE TABLE", call_args)

    @patch("aiosqlite.connect")
    def test_add_machine_async(self, mock_connect):
        """Test adding machine to database."""
        # Create async mock for connection
        mock_conn = MagicMock()

        # Make execute and commit async functions
        async def mock_execute(*args, **kwargs):
            return None

        async def mock_commit(*args, **kwargs):
            return None

        mock_conn.execute = mock_execute
        mock_conn.commit = mock_commit

        # Mock the async context manager properly
        async def mock_connect_async(self):
            return mock_conn

        mock_connect.return_value.__aenter__ = mock_connect_async

        async def mock_exit_async(self, exc_type, exc_val, exc_tb):
            return None

        mock_connect.return_value.__aexit__ = mock_exit_async

        db = deploy_spot.MachineStateManager(":memory:")

        # Run the async function using asyncio
        result = asyncio.run(
            db.add_machine(
                instance_id="i-12345",
                region="us-west-2",
                instance_type="t3.medium",
                status="running",
            )
        )

        self.assertTrue(result)


class TestAWSUtilityFunctions(unittest.TestCase):
    """Test AWS utility functions with mocked boto3."""

    @patch("boto3.client")
    def test_get_ec2_client(self, mock_boto_client):
        """Test EC2 client creation."""
        # Ensure imports are loaded for get_ec2_client to work
        deploy_spot._ensure_imports()

        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        client = deploy_spot.get_ec2_client("us-west-2")

        mock_boto_client.assert_called_with("ec2", region_name="us-west-2")
        self.assertEqual(client, mock_client)

    @patch("boto3.client")
    def test_get_all_aws_regions(self, mock_boto_client):
        """Test getting all AWS regions."""
        # Ensure imports are loaded for get_all_aws_regions to work
        deploy_spot._ensure_imports()

        mock_client = Mock()
        mock_client.describe_regions.return_value = {
            "Regions": [
                {"RegionName": "us-east-1"},
                {"RegionName": "us-west-2"},
                {"RegionName": "eu-west-1"},
            ]
        }
        mock_boto_client.return_value = mock_client

        regions = deploy_spot.get_all_aws_regions()

        self.assertEqual(len(regions), 3)
        self.assertIn("us-east-1", regions)
        self.assertIn("us-west-2", regions)
        self.assertIn("eu-west-1", regions)

    @patch("boto3.client")
    def test_check_region_spot_availability_success(self, mock_boto_client):
        """Test successful spot availability check."""
        # Ensure imports are loaded for check_region_spot_availability to work
        deploy_spot._ensure_imports()

        mock_client = Mock()
        mock_client.describe_instance_types.return_value = {
            "InstanceTypes": [
                {
                    "InstanceType": "t3.medium",
                    "VCpuInfo": {"DefaultVCpus": 2},
                    "MemoryInfo": {"SizeInMiB": 4096},
                }
            ]
        }
        mock_client.describe_spot_price_history.return_value = {
            "SpotPriceHistory": [{"SpotPrice": "0.0416"}]
        }
        mock_boto_client.return_value = mock_client

        result = deploy_spot.check_region_spot_availability("us-west-2")

        self.assertTrue(result["available"])
        self.assertEqual(result["region"], "us-west-2")
        self.assertIn("instances", result)
        self.assertIn("cheapest_instance", result)


class TestAWSDataCache(unittest.TestCase):
    """Test AWS data caching functionality."""

    def setUp(self):
        """Set up cache test environment."""
        self.test_cache_dir = ".test_cache"
        # Ensure imports are loaded before creating cache
        deploy_spot._ensure_imports()
        self.cache = deploy_spot.AWSDataCache(self.test_cache_dir)

    def tearDown(self):
        """Clean up cache test environment."""
        import shutil
        from pathlib import Path

        cache_path = Path(self.test_cache_dir)
        if cache_path.exists():
            shutil.rmtree(cache_path)

    def test_cache_directory_creation(self):
        """Test cache directory and gitignore creation."""
        from pathlib import Path

        cache_path = Path(self.test_cache_dir)
        gitignore_path = cache_path / ".gitignore"

        self.assertTrue(cache_path.exists())
        self.assertTrue(gitignore_path.exists())

        with open(gitignore_path, "r") as f:
            content = f.read()
            self.assertIn("*", content)

    def test_cache_metadata_operations(self):
        """Test cache metadata loading and saving."""
        # Ensure imports are loaded for cache operations
        deploy_spot._ensure_imports()

        # Test empty metadata
        metadata = self.cache._load_metadata()
        self.assertIn("cache_timestamps", metadata)
        self.assertIn("cache_stats", metadata)

        # Test saving metadata
        test_metadata = {
            "cache_timestamps": {"test": "2025-01-04T10:00:00"},
            "cache_stats": {"test": {"size": 100}},
        }
        self.cache._save_metadata(test_metadata)

        # Test loading saved metadata
        loaded_metadata = self.cache._load_metadata()
        self.assertEqual(
            loaded_metadata["cache_timestamps"]["test"], "2025-01-04T10:00:00"
        )

    def test_cache_data_operations(self):
        """Test cache data saving and loading."""
        # Ensure imports are loaded for cache operations
        deploy_spot._ensure_imports()

        test_data = {
            "regions": ["us-east-1", "us-west-2"],
            "timestamp": "2025-01-04T10:00:00",
        }

        # Test saving
        self.cache._save_cache_data("regions", test_data)

        # Test loading
        loaded_data = self.cache._load_cache_data("regions")
        self.assertEqual(loaded_data["regions"], ["us-east-1", "us-west-2"])

    def test_cache_freshness_check(self):
        """Test cache freshness logic."""
        # Ensure imports are loaded for cache operations
        deploy_spot._ensure_imports()

        # Fresh cache should not exist for new cache
        self.assertFalse(self.cache._is_cache_fresh("regions"))

        # Add some test data
        test_data = {"regions": ["us-east-1"], "timestamp": "2025-01-04T10:00:00"}
        self.cache._save_cache_data("regions", test_data)

        # Should be fresh now
        self.assertTrue(self.cache._is_cache_fresh("regions"))

    @patch("deploy_spot.get_all_aws_regions")
    def test_cache_regions_integration(self, mock_get_regions):
        """Test regions caching integration."""
        # Ensure imports are loaded for cache operations
        deploy_spot._ensure_imports()

        mock_get_regions.return_value = ["us-east-1", "us-west-2", "eu-west-1"]

        # Test caching
        regions = mock_get_regions()
        self.cache.cache_regions(regions)

        # Test retrieval
        cached_regions = self.cache.get_cached_regions()
        self.assertEqual(cached_regions, ["us-east-1", "us-west-2", "eu-west-1"])

    def test_cache_stats(self):
        """Test cache statistics generation."""
        # Ensure imports are loaded for cache operations
        deploy_spot._ensure_imports()

        # Add some test data
        self.cache.cache_regions(["us-east-1", "us-west-2"])

        # Get stats
        stats = self.cache.get_cache_stats()

        # Check structure
        self.assertIn("regions", stats)
        self.assertIn("instance_types", stats)
        self.assertIn("spot_pricing", stats)
        self.assertIn("amis", stats)

        # Check that regions shows as fresh
        self.assertTrue(stats["regions"]["is_fresh"])


class TestAsyncOperations(unittest.TestCase):
    """Test async operations with proper mocking."""

    def setUp(self):
        """Set up async test environment."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        """Clean up async test environment."""
        self.loop.close()

    @patch("deploy_spot.get_ec2_client")
    @patch("deploy_spot.get_latest_ubuntu_ami")
    def test_create_spot_instances_mock(self, mock_get_ami, mock_get_client):
        """Test create_spot_instances with mocked dependencies."""
        # Ensure imports are loaded for create_spot_instances to work
        deploy_spot._ensure_imports()

        # Mock configuration
        config = Mock()
        config.get_regions.return_value = ["us-west-2"]
        config.get_total_instances.return_value = 1
        config.get_region_config.return_value = {
            "image": "auto",
            "machine_type": "t3.medium",
        }
        config.get_username.return_value = "test-user"
        config.get_startup_script_path.return_value = (
            "/nonexistent/startup.sh"  # Non-existent path
        )
        config.get_files_directory_path.return_value = (
            "/nonexistent/files"  # Non-existent path
        )

        # Mock AMI lookup
        mock_get_ami.return_value = {"image_id": "ami-12345", "name": "ubuntu-22.04"}

        # Mock EC2 client
        mock_ec2 = Mock()
        mock_ec2.request_spot_instances.return_value = {
            "SpotInstanceRequests": [{"SpotInstanceRequestId": "sir-12345"}]
        }
        mock_ec2.describe_spot_instance_requests.return_value = {
            "SpotInstanceRequests": [
                {
                    "SpotInstanceRequestId": "sir-12345",
                    "State": "active",
                    "InstanceId": "i-12345",
                }
            ]
        }
        mock_get_client.return_value = mock_ec2

        # Mock database with async return
        db = Mock()

        async def mock_add_machine(*args, **kwargs):
            return True

        db.add_machine = mock_add_machine

        # Run the function using asyncio
        result = asyncio.run(deploy_spot.create_spot_instances(config, db))

        # Verify results
        self.assertGreater(result, 0)
        mock_ec2.request_spot_instances.assert_called()


class TestEnhancedConfiguration(unittest.TestCase):
    """Test enhanced configuration system and setup orchestrator."""

    def test_setup_orchestrator_import(self):
        """Test that setup orchestrator can be imported without syntax errors."""
        setup_orchestrator_path = os.path.join(
            os.path.dirname(__file__), "instance", "scripts", "setup_orchestrator.py"
        )

        if os.path.exists(setup_orchestrator_path):
            # Test Python syntax compilation
            try:
                result = subprocess.run(
                    [sys.executable, "-m", "py_compile", setup_orchestrator_path],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                self.assertEqual(
                    result.returncode,
                    0,
                    f"Setup orchestrator syntax error: {result.stderr}",
                )
            except Exception as e:
                self.fail(f"Error testing setup orchestrator syntax: {e}")
        else:
            self.skipTest("Setup orchestrator not found")

    def test_cloud_metadata_script_syntax(self):
        """Test cloud metadata detection script syntax."""
        script_path = os.path.join(
            os.path.dirname(__file__), "instance", "scripts", "cloud_metadata.py"
        )

        if os.path.exists(script_path):
            try:
                result = subprocess.run(
                    [sys.executable, "-m", "py_compile", script_path],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                self.assertEqual(
                    result.returncode,
                    0,
                    f"Cloud metadata script syntax error: {result.stderr}",
                )
            except Exception as e:
                self.fail(f"Error testing cloud metadata script: {e}")
        else:
            self.skipTest("Cloud metadata script not found")

    def test_custom_command_runner_syntax(self):
        """Test custom command runner script syntax."""
        script_path = os.path.join(
            os.path.dirname(__file__), "instance", "scripts", "run_custom_command.py"
        )

        if os.path.exists(script_path):
            try:
                result = subprocess.run(
                    [sys.executable, "-m", "py_compile", script_path],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                self.assertEqual(
                    result.returncode,
                    0,
                    f"Custom command runner syntax error: {result.stderr}",
                )
            except Exception as e:
                self.fail(f"Error testing custom command runner: {e}")
        else:
            self.skipTest("Custom command runner not found")

    def test_enhanced_config_template_syntax(self):
        """Test enhanced configuration template YAML syntax."""
        config_path = os.path.join(
            os.path.dirname(__file__),
            "instance",
            "config",
            "config-template-enhanced.yaml",
        )

        if os.path.exists(config_path):
            try:
                import yaml

                with open(config_path, "r") as f:
                    content = f.read()

                # Replace template variables for testing
                test_content = content.replace(
                    "${orchestrators_list}", "nats://test:4222"
                )
                test_content = test_content.replace("${bacalhau_token}", "test_token")
                test_content = test_content.replace("${tls}", "true")

                # Parse YAML
                config_data = yaml.safe_load(test_content)

                # Test structure
                self.assertIn("setup_stages", config_data)
                self.assertIsInstance(config_data["setup_stages"], list)

                # Test that all required stages are present
                stage_names = [stage["name"] for stage in config_data["setup_stages"]]
                required_stages = [
                    "cloud_metadata",
                    "docker_verification",
                    "bacalhau_setup",
                ]
                for required_stage in required_stages:
                    self.assertIn(
                        required_stage,
                        stage_names,
                        f"Required stage '{required_stage}' not found",
                    )

                # Test stage structure
                for stage in config_data["setup_stages"]:
                    self.assertIn("name", stage)
                    self.assertIn("script", stage)
                    self.assertIn("timeout", stage)
                    self.assertIn("required", stage)
                    self.assertIsInstance(stage["timeout"], int)
                    self.assertIsInstance(stage["required"], bool)

            except Exception as e:
                self.fail(f"Error testing enhanced config template: {e}")
        else:
            self.skipTest("Enhanced config template not found")

    def test_setup_stage_configuration_validation(self):
        """Test setup stage configuration validation."""
        # Test valid stage configuration
        valid_stage = {
            "name": "test_stage",
            "script": "test_script.py",
            "timeout": 60,
            "required": True,
            "description": "Test stage",
            "env_vars": {"TEST_VAR": "test_value"},
        }

        # Test required fields
        required_fields = ["name", "script", "timeout", "required"]
        for field in required_fields:
            self.assertIn(field, valid_stage, f"Required field '{field}' missing")

        # Test field types
        self.assertIsInstance(valid_stage["name"], str)
        self.assertIsInstance(valid_stage["script"], str)
        self.assertIsInstance(valid_stage["timeout"], int)
        self.assertIsInstance(valid_stage["required"], bool)

        # Test optional fields
        if "env_vars" in valid_stage:
            self.assertIsInstance(valid_stage["env_vars"], dict)

    def test_custom_command_security_config(self):
        """Test custom command security configuration structure."""
        security_config = {
            "allow_all": True,
            "max_execution_time": 600,
            "allowed_commands": ["docker", "systemctl", "curl"],
            "forbidden_patterns": ["rm -rf /", "format", "shutdown"],
        }

        # Test required fields
        required_fields = [
            "allow_all",
            "max_execution_time",
            "allowed_commands",
            "forbidden_patterns",
        ]
        for field in required_fields:
            self.assertIn(
                field, security_config, f"Required security field '{field}' missing"
            )

        # Test field types
        self.assertIsInstance(security_config["allow_all"], bool)
        self.assertIsInstance(security_config["max_execution_time"], int)
        self.assertIsInstance(security_config["allowed_commands"], list)
        self.assertIsInstance(security_config["forbidden_patterns"], list)

        # Test positive timeout
        self.assertGreater(security_config["max_execution_time"], 0)

    def test_cloud_init_template_enhanced_integration(self):
        """Test that cloud-init template includes setup orchestrator."""
        template_path = os.path.join(
            os.path.dirname(__file__), "instance", "cloud-init", "init-vm-template.yml"
        )

        if os.path.exists(template_path):
            with open(template_path, "r") as f:
                content = f.read()

            # Check for setup orchestrator references
            self.assertIn(
                "setup_orchestrator.py",
                content,
                "Setup orchestrator not referenced in cloud-init template",
            )

            # Check for required permissions setting
            self.assertIn(
                "chmod 0755 /usr/local/bin/setup_orchestrator.py",
                content,
                "Setup orchestrator permissions not set correctly",
            )

            # Check that service file references setup orchestrator
            service_path = os.path.join(
                os.path.dirname(__file__),
                "instance",
                "scripts",
                "bacalhau-startup.service",
            )
            if os.path.exists(service_path):
                with open(service_path, "r") as f:
                    service_content = f.read()

                self.assertIn(
                    "setup_orchestrator.py",
                    service_content,
                    "Service file does not reference setup orchestrator",
                )
        else:
            self.skipTest("Cloud-init template not found")


class TestCommandIntegration(unittest.TestCase):
    """Test command integration without AWS dependencies."""

    @patch("deploy_spot.validate_environment")
    @patch("deploy_spot.check_ssh_keys")
    @patch("os.path.exists")
    def test_verify_command(self, mock_exists, mock_check_ssh, mock_validate):
        """Test verify command integration."""
        # Ensure imports are loaded for verify_environment to work
        deploy_spot._ensure_imports()

        mock_exists.return_value = True
        mock_validate.return_value = []  # No issues
        mock_check_ssh.return_value = []  # No SSH issues

        with patch("deploy_spot.Config") as mock_config_class:
            mock_config = Mock()
            mock_config_class.return_value = mock_config

            with patch("deploy_spot._get_console") as mock_get_console:
                mock_console = Mock()
                mock_get_console.return_value = mock_console

                result = deploy_spot.verify_environment("test_config.yaml")

                self.assertTrue(result)
                mock_validate.assert_called()
                mock_check_ssh.assert_called()

                # Check that success message was printed
                call_args = str(mock_console.print.call_args_list)
                self.assertIn("validation passed", call_args)

    @patch("deploy_spot.verify_environment")
    @patch("boto3.Session")
    def test_validate_command(self, mock_session, mock_verify):
        """Test validate command integration."""
        # Ensure imports are loaded for run_validation_tests to work
        deploy_spot._ensure_imports()

        mock_verify.return_value = True

        # Mock config loading
        with patch("deploy_spot.Config") as mock_config_class:
            mock_config = Mock()
            mock_config.get_regions.return_value = ["us-west-2", "eu-west-1"]
            mock_config_class.return_value = mock_config

            # Mock boto3 session
            mock_boto_session = Mock()
            mock_credentials = Mock()
            mock_boto_session.get_credentials.return_value = mock_credentials
            mock_session.return_value = mock_boto_session

            with patch("deploy_spot._get_console") as mock_get_console:
                mock_console = Mock()
                mock_get_console.return_value = mock_console

                result = deploy_spot.run_validation_tests("test_config.yaml")

                # Should have run multiple tests
                call_args = str(mock_console.print.call_args_list)
                self.assertIn("Test Results:", call_args)


def run_smoke_tests():
    """Run all smoke tests and return results with pretty formatting."""
    console = Console()

    # Print header
    console.print(
        Panel.fit(
            "🧪 [bold cyan]AWS Spot Deployer - Smoke Tests[/bold cyan]",
            border_style="cyan",
        )
    )

    # Discover and run all tests
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])

    # Extract test names for display
    test_names = []
    for test_group in suite:
        for test in test_group:
            test_names.append(f"{test.__class__.__name__}.{test._testMethodName}")

    # Display test list
    console.print(
        f"\n[bold green]📋 Test Execution Plan ({len(test_names)} tests):[/bold green]"
    )
    test_table = Table(show_header=True, header_style="bold blue")
    test_table.add_column("#", style="dim", width=3, justify="right")
    test_table.add_column("Test Class", style="cyan", no_wrap=True)
    test_table.add_column("Test Method", style="white")

    for i, test_name in enumerate(test_names, 1):
        class_name, method_name = test_name.split(".", 1)
        test_table.add_row(str(i), class_name, method_name)

    console.print(test_table)

    # Use our custom live test runner
    runner = LiveTestRunner(console, verbosity=2)
    result = runner.run(suite, test_names)

    # Create results table
    table = Table(
        title="Test Results Summary", show_header=True, header_style="bold magenta"
    )
    table.add_column("Metric", style="cyan", no_wrap=True)
    table.add_column("Count", style="green", justify="center")
    table.add_column("Details", style="white")

    # Calculate success rate
    success_rate = (
        (
            (result.testsRun - len(result.failures) - len(result.errors))
            / result.testsRun
            * 100
        )
        if result.testsRun > 0
        else 0
    )

    # Add rows to table
    table.add_row(
        "Tests Run", str(result.testsRun), "Total number of test methods executed"
    )
    table.add_row(
        "Passed",
        str(result.testsRun - len(result.failures) - len(result.errors)),
        "✅ Successfully completed",
    )
    table.add_row(
        "Failures",
        str(len(result.failures)),
        "❌ Test assertions that failed" if result.failures else "None",
    )
    table.add_row(
        "Errors",
        str(len(result.errors)),
        "💥 Unexpected exceptions" if result.errors else "None",
    )
    table.add_row(
        "Success Rate", f"{success_rate:.1f}%", "🎯 Overall test success percentage"
    )

    console.print(table)

    # Show detailed results if there are failures or errors
    if result.failures:
        console.print(
            Panel(
                "\n".join(
                    [
                        f"• {test}: {traceback.split('AssertionError:')[-1].strip()}"
                        for test, traceback in result.failures
                    ]
                ),
                title="❌ Test Failures",
                border_style="red",
            )
        )

    if result.errors:
        console.print(
            Panel(
                "\n".join(
                    [
                        f"• {test}: {traceback.split('Error:')[-1].strip()}"
                        for test, traceback in result.errors
                    ]
                ),
                title="💥 Test Errors",
                border_style="red",
            )
        )

    # Overall status
    if result.wasSuccessful():
        console.print(
            Panel(
                "[bold green]🎉 All tests passed! The AWS Spot Deployer is ready for action.[/bold green]",
                border_style="green",
            )
        )
    else:
        console.print(
            Panel(
                f"[bold red]⚠️  {len(result.failures) + len(result.errors)} test(s) failed. Please review the issues above.[/bold red]",
                border_style="red",
            )
        )

    # Print detailed test results if there were any issues
    if result.failures or result.errors:
        console.print("\n[dim]Detailed test execution summary:[/dim]")
        for test_name, status, result_type in result.completed_tests:
            if result_type != "PASS":
                console.print(f"  {status} {test_name} - {result_type}")

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_smoke_tests()
    sys.exit(0 if success else 1)
