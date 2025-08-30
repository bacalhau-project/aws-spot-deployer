#!/usr/bin/env python3
"""
Deploy instance files from tarball to their proper locations.
This script extracts the tarball in /tmp and moves files according to their directory structure.
"""

import os
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path


def main():
    """Main deployment function."""
    tarball_path = "/tmp/deployment.tar.gz"
    extract_dir = "/tmp/instance-deployment"
    
    if not os.path.exists(tarball_path):
        print(f"ERROR: Tarball not found at {tarball_path}")
        sys.exit(1)
    
    try:
        # Extract tarball to temp directory
        print(f"Extracting {tarball_path} to {extract_dir}")
        os.makedirs(extract_dir, exist_ok=True)
        
        with tarfile.open(tarball_path, "r:gz") as tar:
            tar.extractall(extract_dir)
        
        # Find the instance-files directory in the extracted content
        instance_files_dir = Path(extract_dir) / "instance-files"
        
        if not instance_files_dir.exists():
            print(f"ERROR: instance-files directory not found in tarball")
            sys.exit(1)
        
        # Deploy files according to their structure
        print("Deploying files to their target locations...")
        deploy_directory_structure(instance_files_dir, Path("/"))
        
        # Clean up
        print("Cleaning up temporary files...")
        shutil.rmtree(extract_dir, ignore_errors=True)
        os.remove(tarball_path)
        
        print("✅ Deployment complete!")
        
    except Exception as e:
        print(f"ERROR during deployment: {e}")
        sys.exit(1)


def deploy_directory_structure(source_dir: Path, target_root: Path):
    """Deploy directory structure from source to target, preserving paths."""
    for item in source_dir.rglob("*"):
        if item.is_file():
            # Calculate relative path from source_dir
            relative_path = item.relative_to(source_dir)
            target_path = target_root / relative_path
            
            # Create parent directories
            target_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy file with proper permissions
            print(f"  Deploying: {relative_path} -> {target_path}")
            shutil.copy2(item, target_path)
            
            # Make scripts executable
            if target_path.suffix == ".py" or target_path.suffix == ".sh":
                os.chmod(target_path, 0o755)
            
            # Set proper ownership for ubuntu user
            try:
                subprocess.run(["chown", "ubuntu:ubuntu", str(target_path)], 
                             check=False, capture_output=True)
            except Exception:
                pass  # Ignore ownership errors


if __name__ == "__main__":
    main()