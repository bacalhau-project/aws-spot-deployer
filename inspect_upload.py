#!/usr/bin/env uv run
# /// script
# requires-python = ">=3.9"
# dependencies = [
#     "boto3>=1.26.0",
#     "pyyaml>=6.0",
#     "rich>=13.0.0",
# ]
# ///
"""
Inspect what files would be uploaded by transfer_files_scp without actually uploading.
This shows exactly what files are prepared and how they're organized.
"""

import os
import shutil
import sys
import tempfile
from pathlib import Path

# Import the actual function we use
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from spot_deployer.utils.bacalhau_config import (
    generate_bacalhau_config_with_credentials,
)


def inspect_upload(
    files_directory: str = "files",
    scripts_directory: str = "instance/scripts",
    config_directory: str = "instance/config",
):
    """Simulate the file preparation process and show what would be uploaded."""

    print("=== UPLOAD INSPECTION ===\n")

    # Create a temporary directory to simulate the upload staging
    staging_dir = tempfile.mkdtemp(prefix="upload_staging_")
    print(f"Staging directory: {staging_dir}\n")

    try:
        # Create the directory structure
        os.makedirs(os.path.join(staging_dir, "scripts"), exist_ok=True)
        os.makedirs(os.path.join(staging_dir, "config"), exist_ok=True)

        # 1. Scripts Directory
        print("1. SCRIPTS DIRECTORY")
        print(f"   Source: {scripts_directory}")
        if os.path.exists(scripts_directory):
            script_files = []
            for file in os.listdir(scripts_directory):
                if os.path.isfile(os.path.join(scripts_directory, file)):
                    script_files.append(file)
                    # Copy to staging to show what would be uploaded
                    shutil.copy2(
                        os.path.join(scripts_directory, file),
                        os.path.join(staging_dir, "scripts", file),
                    )

            print(f"   Files to upload ({len(script_files)}):")
            for file in sorted(script_files):
                size = os.path.getsize(os.path.join(scripts_directory, file))
                print(f"     - {file} ({size:,} bytes)")
        else:
            print("   ERROR: Scripts directory not found!")
        print()

        # 2. User Files Directory (excluding credentials)
        print("2. USER FILES DIRECTORY")
        print(f"   Source: {files_directory}")
        if os.path.exists(files_directory):
            excluded_files = ["orchestrator_endpoint", "orchestrator_token"]
            user_files = []
            excluded = []

            for item in os.listdir(files_directory):
                if item in excluded_files:
                    excluded.append(item)
                else:
                    src_path = os.path.join(files_directory, item)
                    if os.path.isfile(src_path):
                        user_files.append(item)
                        # Copy to staging
                        shutil.copy2(src_path, os.path.join(staging_dir, item))
                    elif os.path.isdir(src_path):
                        user_files.append(f"{item}/")
                        shutil.copytree(src_path, os.path.join(staging_dir, item))

            print(f"   Files to upload ({len(user_files)}):")
            for file in sorted(user_files):
                if file.endswith("/"):
                    print(f"     - {file} (directory)")
                else:
                    size = os.path.getsize(os.path.join(files_directory, file))
                    print(f"     - {file} ({size:,} bytes)")

            if excluded:
                print(f"   EXCLUDED sensitive files ({len(excluded)}):")
                for file in excluded:
                    print(f"     - {file} (credentials)")
        else:
            print("   WARNING: User files directory not found!")
        print()

        # 3. Config Directory with Bacalhau config generation
        print("3. CONFIG DIRECTORY")
        print(f"   Source: {config_directory}")
        if os.path.exists(config_directory):
            # Check for Bacalhau template
            bacalhau_template = os.path.join(
                config_directory, "bacalhau-config-template.yaml"
            )

            if os.path.exists(bacalhau_template):
                print("   Bacalhau config generation:")
                print(f"     - Template: {bacalhau_template}")

                # Check for credentials
                endpoint_file = os.path.join(files_directory, "orchestrator_endpoint")
                token_file = os.path.join(files_directory, "orchestrator_token")

                if os.path.exists(endpoint_file) and os.path.exists(token_file):
                    print("     - Credentials found: YES")
                    try:
                        # Generate the config
                        generated_config = generate_bacalhau_config_with_credentials(
                            bacalhau_template, files_directory=files_directory
                        )

                        # Copy to staging as bacalhau-config.yaml
                        shutil.copy2(
                            generated_config,
                            os.path.join(staging_dir, "config", "bacalhau-config.yaml"),
                        )

                        # Show config content (without token)
                        with open(generated_config, "r") as f:
                            content = f.read()
                            if "Token:" in content:
                                # Redact the token for display
                                lines = content.split("\n")
                                for i, line in enumerate(lines):
                                    if "Token:" in line:
                                        lines[i] = '    Token: "***REDACTED***"'
                                content = "\n".join(lines)

                        print("     - Generated config preview:")
                        print("       " + "\n       ".join(content.split("\n")[:15]))
                        print("       ...")

                        # Clean up temp file
                        os.unlink(generated_config)
                    except Exception as e:
                        print(f"     - ERROR generating config: {e}")
                else:
                    print("     - Credentials found: NO")
                    print("       Missing files:")
                    if not os.path.exists(endpoint_file):
                        print(f"       - {endpoint_file}")
                    if not os.path.exists(token_file):
                        print(f"       - {token_file}")
            else:
                print(f"   ERROR: Bacalhau template not found: {bacalhau_template}")

            # Other config files
            config_files = []
            for file in os.listdir(config_directory):
                if os.path.isfile(os.path.join(config_directory, file)):
                    config_files.append(file)
                    shutil.copy2(
                        os.path.join(config_directory, file),
                        os.path.join(staging_dir, "config", file),
                    )

            print(f"\n   Other config files ({len(config_files)}):")
            for file in sorted(config_files):
                size = os.path.getsize(os.path.join(config_directory, file))
                print(f"     - {file} ({size:,} bytes)")
        else:
            print("   ERROR: Config directory not found!")
        print()

        # 4. Summary
        print("4. UPLOAD SUMMARY")
        print(f"   Staging directory: {staging_dir}")

        # Count total files
        total_files = 0
        total_size = 0
        for root, dirs, files in os.walk(staging_dir):
            for file in files:
                total_files += 1
                total_size += os.path.getsize(os.path.join(root, file))

        print(f"   Total files to upload: {total_files}")
        print(
            f"   Total size: {total_size:,} bytes ({total_size / 1024 / 1024:.2f} MB)"
        )
        print()

        # Show directory tree
        print("5. DIRECTORY STRUCTURE")
        print("   /tmp/uploaded_files/")
        for root, dirs, files in os.walk(staging_dir):
            level = root.replace(staging_dir, "").count(os.sep)
            indent = "   " * (level + 1)
            subdir = os.path.basename(root)
            if subdir and subdir != os.path.basename(staging_dir):
                print(f"{indent}{subdir}/")
            subindent = "   " * (level + 2)
            for file in sorted(files):
                print(f"{subindent}{file}")

        print("\n6. DEPLOYMENT TRIGGER")
        print("   After upload, the following would happen:")
        print("   1. Create marker file: /tmp/uploaded_files_ready")
        print("   2. Cloud-init watcher detects marker")
        print("   3. Watcher runs: uv run deploy_services.py")
        print("   4. Deployment begins")

        input("\nPress Enter to clean up staging directory...")

    finally:
        # Clean up
        shutil.rmtree(staging_dir, ignore_errors=True)
        print(f"\nStaging directory cleaned up: {staging_dir}")


if __name__ == "__main__":
    # Allow overriding directories via command line
    files_dir = sys.argv[1] if len(sys.argv) > 1 else "files"
    scripts_dir = sys.argv[2] if len(sys.argv) > 2 else "instance/scripts"
    config_dir = sys.argv[3] if len(sys.argv) > 3 else "instance/config"

    print("Usage: uv run inspect_upload.py [files_dir] [scripts_dir] [config_dir]")
    print(f"Using: files={files_dir}, scripts={scripts_dir}, config={config_dir}\n")

    inspect_upload(files_dir, scripts_dir, config_dir)
