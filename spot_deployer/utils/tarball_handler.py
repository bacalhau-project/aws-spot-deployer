#!/usr/bin/env python3
"""Tarball handler for deployment packages."""

import hashlib
import os
import tempfile
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import urlparse


class TarballHandler:
    """Handles tarball operations for deployments."""

    def __init__(self):
        """Initialize tarball handler."""
        self.temp_dir = Path(tempfile.gettempdir()) / "spot-deployer"
        self.temp_dir.mkdir(exist_ok=True)

    def validate_tarball(self, tarball_ref: str) -> Tuple[bool, str]:
        """Validate tarball URL or path.

        Args:
            tarball_ref: URL or local path to tarball

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check if it's a URL
        parsed = urlparse(tarball_ref)
        if parsed.scheme in ("http", "https", "s3", "gs"):
            # Valid URL schemes
            return True, ""
        elif parsed.scheme == "file" or not parsed.scheme:
            # Local file
            path = Path(tarball_ref.replace("file://", ""))
            if path.exists():
                if path.suffix not in (".tar", ".tar.gz", ".tgz", ".tar.bz2"):
                    return False, f"Invalid tarball extension: {path.suffix}"
                return True, ""
            else:
                return False, f"Local tarball not found: {path}"
        else:
            return False, f"Unsupported scheme: {parsed.scheme}"

    def generate_download_commands(
        self, tarball_url: str, dest_path: str = "/tmp/deployment.tar.gz"
    ) -> str:
        """Generate shell commands to download tarball.

        Args:
            tarball_url: URL of the tarball
            dest_path: Destination path on instance

        Returns:
            Shell commands to download tarball
        """
        parsed = urlparse(tarball_url)

        if parsed.scheme in ("http", "https"):
            # Use wget with retry and timeout
            return f"""
# Download deployment tarball
echo "Downloading deployment package..."
wget --tries=3 --timeout=30 -O {dest_path} '{tarball_url}' || \\
    curl --retry 3 --connect-timeout 30 -L -o {dest_path} '{tarball_url}'
"""
        elif parsed.scheme == "s3":
            # Use AWS CLI
            return f"""
# Download from S3
echo "Downloading from S3..."
aws s3 cp '{tarball_url}' {dest_path}
"""
        elif parsed.scheme == "gs":
            # Use gsutil
            return f"""
# Download from Google Cloud Storage
echo "Downloading from GCS..."
gsutil cp '{tarball_url}' {dest_path}
"""
        else:
            # Shouldn't reach here if validation passed
            return f"echo 'ERROR: Unsupported URL scheme: {parsed.scheme}'"

    def generate_extraction_commands(
        self,
        tarball_path: str = "/tmp/deployment.tar.gz",
        extract_dir: str = "/opt/deployment",
        cleanup: bool = True,
    ) -> str:
        """Generate shell commands to extract tarball.

        Args:
            tarball_path: Path to tarball on instance
            extract_dir: Directory to extract to
            cleanup: Whether to remove tarball after extraction

        Returns:
            Shell commands to extract tarball
        """
        commands = f"""
# Extract deployment package
echo "Extracting deployment package..."
mkdir -p {extract_dir}
tar -xzf {tarball_path} -C {extract_dir}
echo "Extraction complete"
"""

        if cleanup:
            commands += f"""
# Clean up tarball
rm -f {tarball_path}
"""

        return commands

    def generate_checksum_verification(
        self, tarball_path: str, checksum: str, algorithm: str = "sha256"
    ) -> str:
        """Generate commands to verify tarball checksum.

        Args:
            tarball_path: Path to tarball on instance
            checksum: Expected checksum value
            algorithm: Hash algorithm (sha256, sha1, md5)

        Returns:
            Shell commands to verify checksum
        """
        if algorithm == "sha256":
            cmd = "sha256sum"
        elif algorithm == "sha1":
            cmd = "sha1sum"
        elif algorithm == "md5":
            cmd = "md5sum"
        else:
            return f"echo 'ERROR: Unsupported checksum algorithm: {algorithm}'"

        return f"""
# Verify checksum
echo "Verifying checksum..."
echo "{checksum}  {tarball_path}" | {cmd} -c
if [ $? -ne 0 ]; then
    echo "ERROR: Checksum verification failed!"
    exit 1
fi
echo "Checksum verified successfully"
"""

    def calculate_local_checksum(self, file_path: Path, algorithm: str = "sha256") -> Optional[str]:
        """Calculate checksum of a local file.

        Args:
            file_path: Path to local file
            algorithm: Hash algorithm

        Returns:
            Checksum string or None if error
        """
        if not file_path.exists():
            return None

        hash_func = getattr(hashlib, algorithm, None)
        if not hash_func:
            return None

        hasher = hash_func()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)

        return hasher.hexdigest()

    def prepare_local_tarball(self, local_path: Path) -> Tuple[bool, str, Optional[Path]]:
        """Prepare local tarball for upload.

        Args:
            local_path: Path to local tarball

        Returns:
            Tuple of (success, message, prepared_path)
        """
        if not local_path.exists():
            return False, f"File not found: {local_path}", None

        # Check file size
        size_mb = local_path.stat().st_size / (1024 * 1024)
        if size_mb > 1000:  # 1GB limit
            return False, f"Tarball too large: {size_mb:.1f}MB (max 1000MB)", None

        # Validate it's a real tarball
        import tarfile

        try:
            with tarfile.open(local_path, "r:*") as tar:
                # Just try to read the tarball
                tar.getnames()
        except Exception as e:
            return False, f"Invalid tarball: {e}", None

        return True, f"Tarball ready ({size_mb:.1f}MB)", local_path

    def create_deployment_tarball(
        self,
        source_dir: Path,
        output_path: Optional[Path] = None,
        exclude_patterns: Optional[list] = None,
    ) -> Tuple[bool, str, Optional[Path]]:
        """Create a tarball from a directory.

        Args:
            source_dir: Directory to create tarball from
            output_path: Output path for tarball
            exclude_patterns: Patterns to exclude

        Returns:
            Tuple of (success, message, tarball_path)
        """
        import tarfile

        if not source_dir.exists():
            return False, f"Source directory not found: {source_dir}", None

        if output_path is None:
            output_path = self.temp_dir / f"deployment-{os.getpid()}.tar.gz"

        exclude_patterns = exclude_patterns or [
            "*.pyc",
            "__pycache__",
            ".git",
            ".gitignore",
            ".DS_Store",
            "*.swp",
            "*.swo",
        ]

        try:
            with tarfile.open(output_path, "w:gz") as tar:
                for item in source_dir.iterdir():
                    # Check if item should be excluded
                    skip = False
                    for pattern in exclude_patterns:
                        if item.match(pattern):
                            skip = True
                            break

                    if not skip:
                        tar.add(item, arcname=item.name)

            size_mb = output_path.stat().st_size / (1024 * 1024)
            return True, f"Created tarball ({size_mb:.1f}MB)", output_path

        except Exception as e:
            return False, f"Failed to create tarball: {e}", None

    def get_progress_callback(self, total_size: int):
        """Create a progress callback for downloads.

        Args:
            total_size: Total size in bytes

        Returns:
            Callback function for progress updates
        """

        def callback(block_num: int, block_size: int, total: int):
            downloaded = block_num * block_size
            percent = min(100, downloaded * 100 / total_size)
            mb_downloaded = downloaded / (1024 * 1024)
            mb_total = total_size / (1024 * 1024)
            print(f"\rDownloading: {percent:.1f}% ({mb_downloaded:.1f}/{mb_total:.1f} MB)", end="")
            if downloaded >= total_size:
                print()  # New line when complete

        return callback
