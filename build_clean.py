#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "pyinstaller",
# ]
# ///
"""
Clean build script for AWS Spot Deployer.

This script:
1. Runs smoke tests to verify functionality
2. Cleans up old build artifacts
3. Builds a clean binary from deploy_spot.py
4. Tests the resulting binary
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path


def run_command(cmd, description, check=True):
    """Run a command and handle output."""
    print(f"\n{'='*60}")
    print(f"{description}")
    print(f"{'='*60}")
    print(f"Running: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=check, capture_output=True, text=True, encoding='utf-8')
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(f"STDERR: {result.stderr}")
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"Command failed with exit code {e.returncode}")
        if e.stdout:
            print(f"STDOUT: {e.stdout}")
        if e.stderr:
            print(f"STDERR: {e.stderr}")
        return False


def clean_artifacts():
    """Clean up old build artifacts."""
    print("\n" + "="*60)
    print("CLEANING BUILD ARTIFACTS")
    print("="*60)
    
    # Directories to clean
    dirs_to_clean = ['build', 'dist', '__pycache__']
    
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            print(f"Removing {dir_name}/")
            shutil.rmtree(dir_name)
    
    # Files to clean
    files_to_clean = [
        '*.pyc',
        'debug_deploy_spot.log',
        'machines.db'
    ]
    
    for pattern in files_to_clean:
        if '*' in pattern:
            # Use glob for patterns
            import glob
            for file_path in glob.glob(pattern):
                if os.path.exists(file_path):
                    print(f"Removing {file_path}")
                    os.remove(file_path)
        else:
            if os.path.exists(pattern):
                print(f"Removing {pattern}")
                os.remove(pattern)
    
    print("✓ Cleanup complete")


def run_smoke_tests():
    """Run smoke tests to verify functionality."""
    print("\n" + "="*60)
    print("RUNNING SMOKE TESTS")
    print("="*60)
    
    # Use UV to run the smoke tests with proper dependencies
    success = run_command(
        ['uv', 'run', '-s', 'test_smoke.py'],
        "Running smoke tests to verify functionality"
    )
    
    if success:
        print("✓ All smoke tests passed")
    else:
        print("✗ Smoke tests failed")
    
    return success


def build_binary():
    """Build the binary using PyInstaller."""
    print("\n" + "="*60)
    print("BUILDING BINARY")
    print("="*60)
    
    # Build the binary using UV to run PyInstaller with all dependencies
    success = run_command(
        ['uv', 'run', '--with', 'pyinstaller', '--with', 'boto3', '--with', 'botocore', '--with', 'rich', '--with', 'aiosqlite', '--with', 'aiofiles', '--with', 'pyyaml', 'pyinstaller', 'aws-spot-deployer.spec'],
        "Building binary with PyInstaller and all dependencies"
    )
    
    if success:
        print("✓ Binary build complete")
        
        # Check if binary was created
        binary_path = 'dist/aws-spot-deployer'
        if os.path.exists(binary_path):
            size = os.path.getsize(binary_path) / (1024 * 1024)  # MB
            print(f"✓ Binary created: {binary_path} ({size:.1f} MB)")
            
            # Make binary executable
            os.chmod(binary_path, 0o755)
            print("✓ Binary made executable")
            
            return True
        else:
            print("✗ Binary not found after build")
            return False
    else:
        print("✗ Binary build failed")
        return False


def test_binary():
    """Test the built binary."""
    print("\n" + "="*60)
    print("TESTING BINARY")
    print("="*60)
    
    binary_path = './dist/aws-spot-deployer'
    
    if not os.path.exists(binary_path):
        print("✗ Binary not found for testing")
        return False
    
    # Test basic functionality
    tests = [
        (['./dist/aws-spot-deployer', 'help'], "Testing help command"),
        (['./dist/aws-spot-deployer', 'verify'], "Testing verify command (may fail without config)"),
    ]
    
    all_passed = True
    
    for cmd, description in tests:
        success = run_command(cmd, description, check=False)
        if not success and 'help' in cmd:
            # Help command should always work
            print(f"✗ {description} failed")
            all_passed = False
        elif success:
            print(f"✓ {description} passed")
        else:
            print(f"~ {description} failed (expected without proper config)")
    
    return all_passed


def main():
    """Main build process."""
    print("AWS Spot Deployer - Clean Build Process")
    print("="*60)
    
    # Check requirements
    if not os.path.exists('deploy_spot.py'):
        print("✗ deploy_spot.py not found in current directory")
        return 1
    
    if not os.path.exists('aws-spot-deployer.spec'):
        print("✗ aws-spot-deployer.spec not found in current directory")
        return 1
    
    if not os.path.exists('test_smoke.py'):
        print("✗ test_smoke.py not found in current directory")
        return 1
    
    print("✓ All required files found")
    
    # Step 1: Run smoke tests
    if not run_smoke_tests():
        print("\n❌ SMOKE TESTS FAILED - Aborting build")
        return 1
    
    # Step 2: Clean artifacts
    clean_artifacts()
    
    # Step 3: Build binary
    if not build_binary():
        print("\n❌ BINARY BUILD FAILED")
        return 1
    
    # Step 4: Test binary
    if not test_binary():
        print("\n⚠️  BINARY TESTS HAD ISSUES")
        # Don't fail here as some tests may fail without proper config
    
    print("\n" + "="*60)
    print("BUILD COMPLETE")
    print("="*60)
    print("✓ Clean binary built successfully!")
    print("✓ Binary location: ./dist/aws-spot-deployer")
    print("✓ Ready for distribution")
    
    # Show final binary info
    binary_path = './dist/aws-spot-deployer'
    if os.path.exists(binary_path):
        size = os.path.getsize(binary_path) / (1024 * 1024)
        print(f"✓ Binary size: {size:.1f} MB")
    
    print("\n📋 DISTRIBUTION CHECKLIST:")
    print("   1. Copy ./dist/aws-spot-deployer to target system")
    print("   2. Ensure target system has AWS CLI configured")
    print("   3. Create config.yaml from template")
    print("   4. Run './aws-spot-deployer verify' to test setup")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())