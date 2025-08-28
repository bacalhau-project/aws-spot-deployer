"""Tests for CLI interface."""

import tempfile
from unittest.mock import Mock, patch

import pytest
import yaml
from click.testing import CliRunner

from spot_deployer.cli import cli


@pytest.fixture
def temp_config():
    """Create a temporary cluster config file."""
    config = {
        "name": "test-cluster",
        "num_nodes": 3,
        "resources": {
            "infra": "aws",
            "instance_type": "t3.medium"
        }
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config, f)
        return f.name


def test_cli_version():
    """Test --version flag."""
    runner = CliRunner()
    result = runner.invoke(cli, ['--version'])

    assert result.exit_code == 0
    assert "spot-deployer version" in result.output


def test_cli_help():
    """Test help output."""
    runner = CliRunner()
    result = runner.invoke(cli, ['--help'])

    assert result.exit_code == 0
    assert "SkyPilot Spot Deployer" in result.output
    assert "Deploy global clusters" in result.output


def test_cli_no_command():
    """Test CLI with no command shows help."""
    runner = CliRunner()
    result = runner.invoke(cli, [])

    assert result.exit_code == 0
    assert "SkyPilot Spot Deployer" in result.output


@patch('spot_deployer.cli.ClusterManager')
def test_create_command_missing_config(mock_manager_class):
    """Test create command with missing config file."""
    mock_manager = Mock()
    mock_manager_class.return_value = mock_manager

    runner = CliRunner()
    result = runner.invoke(cli, ['-c', 'nonexistent.yaml', 'create'])

    assert result.exit_code == 1
    assert "Config file not found" in result.output


@patch('spot_deployer.cli.ClusterManager')
@patch('pathlib.Path.exists')
def test_create_command_success(mock_exists, mock_manager_class, temp_config):
    """Test successful create command."""
    mock_exists.return_value = True
    mock_manager = Mock()
    mock_manager.check_prerequisites.return_value = True
    mock_manager.deploy_cluster.return_value = True
    mock_manager_class.return_value = mock_manager

    runner = CliRunner()
    result = runner.invoke(cli, ['-c', temp_config, 'create'])

    assert result.exit_code == 0
    mock_manager.check_prerequisites.assert_called_once()
    mock_manager.deploy_cluster.assert_called_once_with(temp_config)


@patch('spot_deployer.cli.ClusterManager')
def test_destroy_command(mock_manager_class):
    """Test destroy command."""
    mock_manager = Mock()
    mock_manager.destroy_cluster.return_value = True
    mock_manager_class.return_value = mock_manager

    runner = CliRunner()
    result = runner.invoke(cli, ['destroy'])

    assert result.exit_code == 0
    mock_manager.destroy_cluster.assert_called_once()


@patch('spot_deployer.cli.ClusterManager')
def test_status_command(mock_manager_class):
    """Test status command."""
    mock_manager = Mock()
    mock_manager.check_prerequisites.return_value = True
    mock_manager.show_status.return_value = True
    mock_manager_class.return_value = mock_manager

    runner = CliRunner()
    result = runner.invoke(cli, ['status'])

    assert result.exit_code == 0
    mock_manager.check_prerequisites.assert_called_once()
    mock_manager.show_status.assert_called_once()


@patch('spot_deployer.cli.ClusterManager')
def test_list_command(mock_manager_class):
    """Test list command."""
    mock_manager = Mock()
    mock_manager.check_prerequisites.return_value = True
    mock_manager.list_nodes.return_value = True
    mock_manager_class.return_value = mock_manager

    runner = CliRunner()
    result = runner.invoke(cli, ['list'])

    assert result.exit_code == 0
    mock_manager.check_prerequisites.assert_called_once()
    mock_manager.list_nodes.assert_called_once()


@patch('spot_deployer.cli.ClusterManager')
def test_console_flag(mock_manager_class):
    """Test -f/--console flag."""
    mock_manager_class.return_value = Mock()

    runner = CliRunner()
    result = runner.invoke(cli, ['-f', 'cleanup'])

    # Verify manager was created with log_to_console=True
    mock_manager_class.assert_called_once_with(log_to_console=True, log_file="cluster-deploy.log")


def test_command_help():
    """Test help for individual commands."""
    runner = CliRunner()

    commands = ['create', 'destroy', 'status', 'list', 'ssh', 'logs', 'cleanup', 'check']

    for command in commands:
        result = runner.invoke(cli, [command, '--help'])
        assert result.exit_code == 0
        assert command in result.output.lower()
