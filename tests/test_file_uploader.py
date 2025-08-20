#!/usr/bin/env python3
"""Tests for FileUploader class."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from spot_deployer.core.deployment import DeploymentConfig
from spot_deployer.utils.file_uploader import FileUploader


class TestFileUploader(unittest.TestCase):
    """Test FileUploader functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_dir = Path(self.temp_dir.name)

        # Create test deployment structure
        self.spot_dir = self.test_dir / ".spot"
        self.spot_dir.mkdir()

        # Create test files
        (self.spot_dir / "files").mkdir()
        (self.spot_dir / "configs").mkdir()
        (self.spot_dir / "scripts").mkdir()

        # Create test content
        test_file = self.spot_dir / "files" / "test.txt"
        test_file.write_text("test content")

        test_config = self.spot_dir / "configs" / "app.config"
        test_config.write_text("config content")

        test_script = self.spot_dir / "scripts" / "setup.sh"
        test_script.write_text("#!/bin/bash\necho 'setup'")
        test_script.chmod(0o755)

        # Mock SSH manager
        self.mock_ssh = MagicMock()
        self.mock_ui = MagicMock()

    def tearDown(self):
        """Clean up test fixtures."""
        self.temp_dir.cleanup()

    def test_collect_files_basic(self):
        """Test basic file collection."""
        config = DeploymentConfig(
            version=1,
            packages=[],
            scripts=[],
            uploads=[{"source": "files/test.txt", "destination": "/opt/test.txt"}],
            services=[],
            spot_dir=self.spot_dir,
        )

        uploader = FileUploader(self.mock_ssh, self.mock_ui)
        manifest = uploader.collect_files(config)

        self.assertEqual(len(manifest), 1)
        self.assertEqual(manifest[0]["source"], str(self.spot_dir / "files" / "test.txt"))
        self.assertEqual(manifest[0]["destination"], "/opt/test.txt")
        self.assertEqual(manifest[0]["permissions"], "644")

    def test_collect_files_with_permissions(self):
        """Test file collection with custom permissions."""
        config = DeploymentConfig(
            version=1,
            packages=[],
            scripts=[],
            uploads=[
                {"source": "scripts/setup.sh", "destination": "/opt/setup.sh", "permissions": "755"}
            ],
            services=[],
            spot_dir=self.spot_dir,
        )

        uploader = FileUploader(self.mock_ssh, self.mock_ui)
        manifest = uploader.collect_files(config)

        self.assertEqual(len(manifest), 1)
        self.assertEqual(manifest[0]["permissions"], "755")

    def test_collect_files_missing_source(self):
        """Test handling of missing source files."""
        config = DeploymentConfig(
            version=1,
            packages=[],
            scripts=[],
            uploads=[{"source": "files/missing.txt", "destination": "/opt/missing.txt"}],
            services=[],
            spot_dir=self.spot_dir,
        )

        uploader = FileUploader(self.mock_ssh, self.mock_ui)

        with patch("spot_deployer.utils.file_uploader.logger") as mock_logger:
            manifest = uploader.collect_files(config)
            self.assertEqual(len(manifest), 0)
            mock_logger.warning.assert_called()

    def test_upload_files(self):
        """Test file upload process."""
        manifest = [
            {
                "source": str(self.spot_dir / "files" / "test.txt"),
                "destination": "/opt/test.txt",
                "permissions": "644",
            }
        ]

        uploader = FileUploader(self.mock_ssh, self.mock_ui)
        uploader.upload_files("1.2.3.4", manifest)

        # Verify SSH operations
        self.mock_ssh.execute_command.assert_called()
        self.mock_ssh.upload_file.assert_called_once_with(
            "1.2.3.4", str(self.spot_dir / "files" / "test.txt"), "/opt/test.txt"
        )

    def test_upload_files_with_directory_creation(self):
        """Test that directories are created before upload."""
        manifest = [
            {
                "source": str(self.spot_dir / "files" / "test.txt"),
                "destination": "/opt/deep/nested/test.txt",
                "permissions": "644",
            }
        ]

        uploader = FileUploader(self.mock_ssh, self.mock_ui)
        uploader.upload_files("1.2.3.4", manifest)

        # Verify directory creation
        calls = self.mock_ssh.execute_command.call_args_list
        mkdir_call = calls[0]
        self.assertIn("mkdir -p", mkdir_call[0][1])
        self.assertIn("/opt/deep/nested", mkdir_call[0][1])

    def test_upload_files_empty_manifest(self):
        """Test upload with empty manifest."""
        uploader = FileUploader(self.mock_ssh, self.mock_ui)
        uploader.upload_files("1.2.3.4", [])

        # Should not attempt any uploads
        self.mock_ssh.upload_file.assert_not_called()

    def test_validate_manifest(self):
        """Test manifest validation."""
        config = DeploymentConfig(
            version=1,
            packages=[],
            scripts=[],
            uploads=[
                {"source": "files/test.txt", "destination": "/opt/test.txt"},
                {"source": "files/missing.txt", "destination": "/opt/missing.txt"},
            ],
            services=[],
            spot_dir=self.spot_dir,
        )

        uploader = FileUploader(self.mock_ssh, self.mock_ui)
        errors = uploader.validate_manifest(config)

        self.assertEqual(len(errors), 1)
        self.assertIn("missing.txt", errors[0])


if __name__ == "__main__":
    unittest.main()
