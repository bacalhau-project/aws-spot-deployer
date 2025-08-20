#!/usr/bin/env python3
"""Generic file uploader for deployment files based on manifest."""

import logging
import os
import subprocess
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from ..core.deployment import DeploymentConfig
from ..utils.display import console, rich_error, rich_success

logger = logging.getLogger(__name__)


class FileUploader:
    """Handles file uploads based on deployment configuration."""

    def __init__(self, deployment_config: DeploymentConfig, base_dir: Path):
        """Initialize file uploader.

        Args:
            deployment_config: DeploymentConfig with upload mappings
            base_dir: Base directory for relative paths
        """
        self.config = deployment_config
        self.base_dir = base_dir
        self.stats = {
            "total_files": 0,
            "uploaded_files": 0,
            "failed_files": 0,
            "total_bytes": 0,
        }

    def upload_all(
        self,
        host: str,
        username: str,
        key_path: str,
        progress_callback: Optional[Callable] = None,
    ) -> Tuple[bool, str]:
        """Upload all files according to deployment configuration.

        Args:
            host: Target host IP
            username: SSH username
            key_path: Path to SSH private key
            progress_callback: Optional callback for progress updates

        Returns:
            Tuple of (success, message)
        """
        if not self.config.uploads:
            logger.info("No uploads defined in deployment configuration")
            return True, "No files to upload"

        # Prepare upload list
        upload_list = self._prepare_upload_list()
        if not upload_list:
            return True, "No files matched upload patterns"

        self.stats["total_files"] = len(upload_list)

        # Upload files
        success_count = 0
        for i, (local_path, remote_path, permissions) in enumerate(upload_list):
            if progress_callback:
                progress = (i + 1) / len(upload_list) * 100
                progress_callback(f"Uploading {local_path.name}", progress)

            success, msg = self._upload_file(
                host, username, key_path, local_path, remote_path, permissions
            )

            if success:
                success_count += 1
                self.stats["uploaded_files"] += 1
                logger.info(f"Uploaded: {local_path} -> {remote_path}")
            else:
                self.stats["failed_files"] += 1
                logger.error(f"Failed to upload {local_path}: {msg}")

        # Return summary
        if success_count == len(upload_list):
            return True, f"Uploaded {success_count} files successfully"
        elif success_count > 0:
            return (
                False,
                f"Uploaded {success_count}/{len(upload_list)} files (partial success)",
            )
        else:
            return False, "Failed to upload any files"

    def _prepare_upload_list(self) -> List[Tuple[Path, str, Optional[str]]]:
        """Prepare list of files to upload.

        Returns:
            List of (local_path, remote_path, permissions) tuples
        """
        upload_list = []

        for upload_spec in self.config.uploads:
            source = upload_spec.get("source")
            dest = upload_spec.get("dest", "/opt/deployment")
            permissions = upload_spec.get("permissions")
            exclude = upload_spec.get("exclude", [])

            if not source:
                logger.warning("Upload spec missing 'source' field")
                continue

            source_path = self.base_dir / source

            if source_path.is_file():
                # Single file
                remote_path = dest if dest.endswith("/") else dest
                if dest.endswith("/"):
                    remote_path = f"{dest}{source_path.name}"
                upload_list.append((source_path, remote_path, permissions))

            elif source_path.is_dir():
                # Directory - recursively add files
                for file_path in source_path.rglob("*"):
                    if file_path.is_file():
                        # Check exclusions
                        if self._should_exclude(file_path, exclude):
                            continue

                        # Calculate relative path
                        rel_path = file_path.relative_to(source_path)
                        remote_path = f"{dest}/{rel_path}"
                        upload_list.append((file_path, remote_path, permissions))

            else:
                logger.warning(f"Source path not found: {source_path}")

        return upload_list

    def _should_exclude(self, file_path: Path, exclude_patterns: List[str]) -> bool:
        """Check if file should be excluded.

        Args:
            file_path: Path to check
            exclude_patterns: List of exclusion patterns

        Returns:
            True if file should be excluded
        """
        for pattern in exclude_patterns:
            if file_path.match(pattern):
                return True
            # Also check against the full path
            if pattern in str(file_path):
                return True
        return False

    def _upload_file(
        self,
        host: str,
        username: str,
        key_path: str,
        local_path: Path,
        remote_path: str,
        permissions: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """Upload a single file.

        Args:
            host: Target host
            username: SSH username
            key_path: SSH key path
            local_path: Local file path
            remote_path: Remote destination path
            permissions: Optional permissions to set

        Returns:
            Tuple of (success, message)
        """
        # First, create remote directory
        remote_dir = os.path.dirname(remote_path)
        mkdir_cmd = [
            "ssh",
            "-o",
            "StrictHostKeyChecking=no",
            "-o",
            "UserKnownHostsFile=/dev/null",
            "-o",
            "LogLevel=ERROR",
            "-i",
            key_path,
            f"{username}@{host}",
            f"sudo mkdir -p {remote_dir}",
        ]

        result = subprocess.run(mkdir_cmd, capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            return False, f"Failed to create directory: {result.stderr}"

        # Upload file
        scp_cmd = [
            "scp",
            "-o",
            "StrictHostKeyChecking=no",
            "-o",
            "UserKnownHostsFile=/dev/null",
            "-o",
            "LogLevel=ERROR",
            "-i",
            key_path,
            str(local_path),
            f"{username}@{host}:/tmp/upload_temp",
        ]

        # Try upload with retries
        max_retries = 3
        for attempt in range(max_retries):
            result = subprocess.run(scp_cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                break
            if attempt < max_retries - 1:
                logger.debug(f"Upload retry {attempt + 1} for {local_path}")
        else:
            return False, f"Upload failed after {max_retries} attempts: {result.stderr}"

        # Move to final location with sudo
        move_cmd = [
            "ssh",
            "-o",
            "StrictHostKeyChecking=no",
            "-o",
            "UserKnownHostsFile=/dev/null",
            "-o",
            "LogLevel=ERROR",
            "-i",
            key_path,
            f"{username}@{host}",
            f"sudo mv /tmp/upload_temp {remote_path}",
        ]

        result = subprocess.run(move_cmd, capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            return False, f"Failed to move file: {result.stderr}"

        # Set permissions if specified
        if permissions:
            chmod_cmd = [
                "ssh",
                "-o",
                "StrictHostKeyChecking=no",
                "-o",
                "UserKnownHostsFile=/dev/null",
                "-o",
                "LogLevel=ERROR",
                "-i",
                key_path,
                f"{username}@{host}",
                f"sudo chmod {permissions} {remote_path}",
            ]

            result = subprocess.run(chmod_cmd, capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                logger.warning(f"Failed to set permissions on {remote_path}: {result.stderr}")

        # Update stats
        self.stats["total_bytes"] += local_path.stat().st_size

        return True, "Success"

    def get_stats(self) -> Dict:
        """Get upload statistics.

        Returns:
            Dictionary of statistics
        """
        return self.stats.copy()

    def estimate_upload_size(self) -> int:
        """Estimate total upload size in bytes.

        Returns:
            Total size in bytes
        """
        total_size = 0
        upload_list = self._prepare_upload_list()

        for local_path, _, _ in upload_list:
            if local_path.exists():
                total_size += local_path.stat().st_size

        return total_size

    def validate_uploads(self) -> Tuple[bool, List[str]]:
        """Validate that all source files exist.

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        for upload_spec in self.config.uploads:
            source = upload_spec.get("source")
            if not source:
                errors.append("Upload spec missing 'source' field")
                continue

            source_path = self.base_dir / source
            if not source_path.exists():
                errors.append(f"Source not found: {source_path}")

        return len(errors) == 0, errors
