"""Tarball handler for creating and managing deployment packages."""

import hashlib
import logging
import os
import tarfile
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple

from ..utils.ui_manager import UIManager

logger = logging.getLogger(__name__)


class TarballHandler:
    """Handles tarball creation and extraction for deployments."""

    def __init__(self):
        """Initialize tarball handler."""
        self.temp_dir = Path(tempfile.gettempdir()) / "amauo"
        self.temp_dir.mkdir(exist_ok=True)
        self.ui = UIManager()

    def create_tarball(
        self,
        source_dir: Path,
        output_path: Optional[Path] = None,
        exclude_patterns: Optional[List[str]] = None,
    ) -> Path:
        """Create a tarball from a directory.

        Args:
            source_dir: Directory to compress
            output_path: Output tarball path (auto-generated if None)
            exclude_patterns: List of patterns to exclude (e.g., ['*.pyc', '__pycache__'])

        Returns:
            Path to created tarball
        """
        if not source_dir.exists():
            raise FileNotFoundError(f"Source directory not found: {source_dir}")

        if not source_dir.is_dir():
            raise ValueError(f"Source must be a directory: {source_dir}")

        # Generate output path if not provided
        if output_path is None:
            # Create hash of source dir for unique name
            dir_hash = hashlib.md5(str(source_dir).encode()).hexdigest()[:8]
            output_path = self.temp_dir / f"deployment-{dir_hash}.tar.gz"

        # Default exclude patterns
        if exclude_patterns is None:
            exclude_patterns = [
                "__pycache__",
                "*.pyc",
                ".git",
                ".gitignore",
                ".DS_Store",
                "*.swp",
                ".env",
                "node_modules",
            ]

        logger.info(f"Creating tarball from {source_dir} to {output_path}")

        def should_exclude(path: Path) -> bool:
            """Check if path should be excluded."""
            name = path.name
            for pattern in exclude_patterns:
                if pattern.startswith("*"):
                    if name.endswith(pattern[1:]):
                        return True
                elif pattern in str(path):
                    return True
            return False

        # Create tarball
        with tarfile.open(output_path, "w:gz") as tar:
            for root, dirs, files in os.walk(source_dir):
                root_path = Path(root)

                # Filter directories
                dirs[:] = [d for d in dirs if not should_exclude(root_path / d)]

                # Add files
                for file in files:
                    file_path = root_path / file
                    if not should_exclude(file_path):
                        # Add with relative path from source_dir
                        arcname = file_path.relative_to(source_dir)
                        tar.add(file_path, arcname=arcname)

        # Calculate size
        size_mb = output_path.stat().st_size / (1024 * 1024)
        logger.info(f"Created tarball: {output_path} ({size_mb:.2f} MB)")

        return output_path

    def extract_tarball(self, tarball_path: Path, dest_dir: Path) -> None:
        """Extract a tarball to a directory.

        Args:
            tarball_path: Path to tarball
            dest_dir: Destination directory
        """
        if not tarball_path.exists():
            raise FileNotFoundError(f"Tarball not found: {tarball_path}")

        dest_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Extracting {tarball_path} to {dest_dir}")

        with tarfile.open(tarball_path, "r:*") as tar:
            # Validate members for security
            for member in tar.getmembers():
                # Prevent path traversal
                if member.name.startswith("..") or member.name.startswith("/"):
                    raise ValueError(f"Unsafe path in tarball: {member.name}")

            tar.extractall(dest_dir)

        logger.info(f"Extracted to {dest_dir}")

    def create_deployment_tarball(self, deployment_dir: Path) -> Path:
        """Create a tarball specifically for deployment.

        This method understands deployment structure and excludes
        unnecessary files automatically.

        Args:
            deployment_dir: Directory containing deployment files (.spot or deployment)

        Returns:
            Path to created tarball
        """
        # Check if it's a valid deployment directory
        if deployment_dir.name == ".spot":
            base_dir = deployment_dir
        elif (deployment_dir / ".spot").exists():
            base_dir = deployment_dir / ".spot"
        elif (deployment_dir / "deployment").exists():
            base_dir = deployment_dir / "deployment"
        else:
            raise ValueError(f"No deployment structure found in {deployment_dir}")

        # Create tarball with deployment-specific exclusions
        exclude_patterns = [
            "__pycache__",
            "*.pyc",
            ".git",
            ".gitignore",
            ".DS_Store",
            "*.swp",
            ".env.local",
            "*.log",
            "README.md",  # Exclude docs from tarball
            "*.md",
        ]

        return self.create_tarball(base_dir, exclude_patterns=exclude_patterns)

    def generate_upload_script(
        self,
        tarball_path: Path,
        remote_path: str = "/tmp/deployment.tar.gz",
    ) -> str:
        """Generate script to upload and extract tarball on remote instance.

        Args:
            tarball_path: Local path to tarball
            remote_path: Remote path for tarball

        Returns:
            Shell script commands
        """
        extract_dir = "/opt/deployment"

        script = f"""
# Extract deployment tarball
echo "Extracting deployment package..."
mkdir -p {extract_dir}
tar -xzf {remote_path} -C {extract_dir}
rm -f {remote_path}

# Set permissions
chown -R ubuntu:ubuntu {extract_dir}
chmod -R 755 {extract_dir}/scripts/ 2>/dev/null || true
chmod -R 644 {extract_dir}/configs/ 2>/dev/null || true

echo "Deployment package extracted to {extract_dir}"
"""
        return script

    def validate_tarball(self, tarball_path: Path) -> Tuple[bool, str]:
        """Validate a tarball file.

        Args:
            tarball_path: Path to tarball

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not tarball_path.exists():
            return False, f"Tarball not found: {tarball_path}"

        if not tarball_path.is_file():
            return False, f"Not a file: {tarball_path}"

        # Check extension
        valid_extensions = {".tar", ".tar.gz", ".tgz", ".tar.bz2"}
        if not any(str(tarball_path).endswith(ext) for ext in valid_extensions):
            return False, f"Invalid tarball extension: {tarball_path.suffix}"

        # Try to open it
        try:
            with tarfile.open(tarball_path, "r:*") as tar:
                # Check for dangerous paths
                for member in tar.getmembers():
                    if member.name.startswith("..") or member.name.startswith("/"):
                        return False, f"Unsafe path in tarball: {member.name}"
            return True, ""
        except Exception as e:
            return False, f"Invalid tarball: {e}"

    def cleanup(self):
        """Clean up temporary files."""
        import shutil

        if self.temp_dir.exists():
            try:
                shutil.rmtree(self.temp_dir)
                logger.info("Cleaned up temporary tarball files")
            except Exception as e:
                logger.warning(f"Failed to cleanup temp dir: {e}")
