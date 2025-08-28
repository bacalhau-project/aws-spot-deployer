"""Tests for ClusterManager."""

import tempfile
from unittest.mock import Mock, patch

import pytest
import yaml

from amauo.manager import ClusterManager


@pytest.fixture
def temp_config():
    """Create a temporary cluster config file."""
    config = {
        "name": "test-cluster",
        "num_nodes": 3,
        "resources": {"infra": "aws", "instance_type": "t3.medium", "use_spot": True},
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(config, f)
        return f.name


@pytest.fixture
def manager():
    """Create a ClusterManager instance."""
    return ClusterManager(log_to_console=True)


def test_load_cluster_config(manager, temp_config):
    """Test loading cluster configuration."""
    config = manager.load_cluster_config(temp_config)

    assert config["name"] == "test-cluster"
    assert config["num_nodes"] == 3
    assert config["resources"]["infra"] == "aws"


def test_load_cluster_config_missing_file(manager):
    """Test loading non-existent config file."""
    with pytest.raises(FileNotFoundError):
        manager.load_cluster_config("nonexistent.yaml")


def test_get_cluster_name_from_config(manager, temp_config):
    """Test extracting cluster name from config."""
    name = manager.get_cluster_name_from_config(temp_config)
    assert name == "test-cluster"


def test_get_cluster_name_from_config_fallback(manager):
    """Test fallback cluster name for missing config."""
    name = manager.get_cluster_name_from_config("nonexistent.yaml")
    assert name == "cluster"


@patch("subprocess.run")
def test_run_sky_cmd_success(mock_run, manager):
    """Test successful sky command execution."""
    # Mock docker ps to show container running
    mock_run.side_effect = [
        Mock(stdout="container_id", returncode=0),  # docker ps
        Mock(stdout="sky version", stderr="", returncode=0),  # sky command
    ]

    success, stdout, stderr = manager.run_sky_cmd("--version")

    assert success is True
    assert stdout == "sky version"
    assert stderr == ""


@patch("subprocess.run")
def test_run_sky_cmd_failure(mock_run, manager):
    """Test failed sky command execution."""
    # Mock docker ps to show container running
    mock_run.side_effect = [
        Mock(stdout="container_id", returncode=0),  # docker ps
        Mock(stdout="", stderr="error message", returncode=1),  # sky command
    ]

    success, stdout, stderr = manager.run_sky_cmd("bad-command")

    assert success is False
    assert stderr == "error message"


def test_logging_methods(manager):
    """Test logging methods don't crash."""
    # These should not raise exceptions
    manager.log_info("Test info")
    manager.log_success("Test success")
    manager.log_warning("Test warning")
    manager.log_error("Test error")
    manager.log_header("Test header")


@patch("subprocess.run")
def test_get_sky_cluster_name_json(mock_run, manager):
    """Test getting cluster name from JSON output."""
    # Mock docker ps and sky status commands
    json_output = '{"clusters": [{"name": "sky-abc123-root"}]}'
    mock_run.side_effect = [
        Mock(stdout="container_id", returncode=0),  # docker ps
        Mock(stdout=json_output, stderr="", returncode=0),  # sky status --format json
    ]

    cluster_name = manager.get_sky_cluster_name()
    assert cluster_name == "sky-abc123-root"


@patch("subprocess.run")
@patch("amauo.manager.ClusterManager.ensure_docker_container")
def test_get_sky_cluster_name_text_fallback(mock_ensure_docker, mock_run, manager):
    """Test getting cluster name from text output fallback."""
    mock_ensure_docker.return_value = True

    # Mock sky status commands
    text_output = """Enabled Infra: aws

Clusters
NAME           INFRA    STATUS
sky-def456-root AWS     UP
"""
    mock_run.side_effect = [
        Mock(stdout="", stderr="", returncode=1),  # sky status --format json (fails)
        Mock(stdout=text_output, stderr="", returncode=0),  # sky status (text)
    ]

    cluster_name = manager.get_sky_cluster_name()
    assert cluster_name == "sky-def456-root"


@patch("subprocess.run")
def test_get_sky_cluster_name_none(mock_run, manager):
    """Test getting cluster name when no cluster exists."""
    mock_run.side_effect = [
        Mock(stdout="container_id", returncode=0),  # docker ps
        Mock(stdout="", stderr="", returncode=1),  # sky status --format json
        Mock(stdout="No clusters found", stderr="", returncode=0),  # sky status
    ]

    cluster_name = manager.get_sky_cluster_name()
    assert cluster_name is None
