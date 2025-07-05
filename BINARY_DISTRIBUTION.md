# Binary Distribution Guide

## Overview

This guide shows how to create standalone binaries of the AWS Spot Instance Deployment Tool that can be distributed to internal teams without requiring Python installation or dependency management.

## 🚀 Quick Start

### 1. Install Build Dependencies

```bash
# Install PyInstaller
pip install pyinstaller

# Or using UV
uv add pyinstaller --dev
```

### 2. Build Binary

```bash
# Build portable version (recommended for distribution)
python build.py --target portable

# Build modular version
python build.py --target modular

# Build both versions
python build.py --target both --package
```

### 3. Distribute

```bash
# Find your binary in the dist/ directory
ls -la dist/

# Example output:
# aws-spot-deployer-macos-arm64    (85.2 MB)
# aws-spot-deployer-linux-x64      (92.1 MB)
# aws-spot-deployer-windows-x64.exe (78.5 MB)
```

## 📋 Build Options

### Basic Build Commands

```bash
# Portable version (single-file, easier to distribute)
python build.py --target portable

# Modular version (includes all modules)
python build.py --target modular

# Debug build (for troubleshooting)
python build.py --target portable --debug

# Custom output directory
python build.py --target portable --output-dir builds/v1.0
```

### Advanced Build Options

```bash
# Create complete release package
python build.py --target both --package

# Generate Docker script for cross-platform builds
python build.py --create-docker-script

# Cross-platform build (requires Docker)
./build_multiplatform.sh portable
```

## 🏗️ Build Process Details

### What PyInstaller Does

1. **Analyzes Dependencies**: Scans your script and finds all imports
2. **Bundles Python Runtime**: Includes Python interpreter
3. **Packages Libraries**: Includes all required packages (boto3, rich, etc.)
4. **Creates Executable**: Single binary file that runs anywhere
5. **Handles Platform Differences**: Creates platform-specific binaries

### Build Artifacts

```
dist/
├── aws-spot-deployer-macos-arm64           # macOS ARM64 binary
├── aws-spot-deployer-linux-x64            # Linux x64 binary
├── aws-spot-deployer-windows-x64.exe      # Windows x64 binary
└── release/                               # Complete package
    ├── aws-spot-deployer-*                # All binaries
    ├── config.yaml_example               # Configuration template
    ├── PORTABLE_DISTRIBUTION.md          # User documentation
    └── install.sh                        # Setup script
```

## 📦 Distribution Strategies

### 1. Internal File Server

```bash
# Upload to internal server
scp dist/aws-spot-deployer-* internal-server:/shared/tools/

# Team downloads
wget http://internal-server/shared/tools/aws-spot-deployer-linux-x64
chmod +x aws-spot-deployer-linux-x64
```

### 2. Git Repository Releases

```bash
# Create GitHub release
gh release create v1.0.0 dist/aws-spot-deployer-* \
  --title "AWS Spot Deployer v1.0.0" \
  --notes "Initial binary release"

# Team downloads
gh release download v1.0.0
```

### 3. Container Registry

```bash
# Create container with binary
cat > Dockerfile << 'EOF'
FROM alpine:latest
RUN apk add --no-cache ca-certificates
COPY dist/aws-spot-deployer-linux-x64 /usr/local/bin/aws-spot-deployer
RUN chmod +x /usr/local/bin/aws-spot-deployer
ENTRYPOINT ["/usr/local/bin/aws-spot-deployer"]
EOF

docker build -t internal-registry/aws-spot-deployer:v1.0.0 .
docker push internal-registry/aws-spot-deployer:v1.0.0
```

### 4. Package Managers

```bash
# Homebrew (for macOS teams)
# Create formula in internal tap

# APT repository (for Ubuntu teams)
# Create .deb package

# Chocolatey (for Windows teams)
# Create .nupkg package
```

## 🎯 Platform-Specific Builds

### Current Platform

```bash
# Builds for your current OS/architecture
python build.py --target portable
```

### Cross-Platform (Docker Required)

```bash
# Generate multi-platform build script
python build.py --create-docker-script

# Build for Linux ARM64 and AMD64
./build_multiplatform.sh portable

# Results in:
# dist/linux-amd64/aws-spot-deployer-linux-amd64
# dist/linux-arm64/aws-spot-deployer-linux-arm64
```

### Manual Cross-Platform

```bash
# macOS → Linux (using Docker)
docker run --rm -v "$(pwd):/app" -w /app python:3.11-slim bash -c \
  "pip install pyinstaller boto3 rich aiosqlite pyyaml && python build.py --target portable"

# Windows (using WSL or GitHub Actions)
# See GitHub Actions example below
```

## 🔧 Configuration for Teams

### 1. Create Team Configuration Template

```yaml
# config-team-template.yaml
aws:
  total_instances: 5
  username: devops-user
  public_ssh_key_path: ~/.ssh/company_ed25519.pub
  private_ssh_key_path: ~/.ssh/company_ed25519

bacalhau:
  orchestrators:
    - nats://company-bacalhau.internal:4222
  token: ${BACALHAU_TOKEN}  # Set via environment
  tls: true

regions:
  - us-west-2:
      image: auto
      machine_type: t3.medium
      node_count: auto
  - us-east-1:
      image: auto
      machine_type: t3.medium
      node_count: auto
```

### 2. Create Setup Script for Teams

```bash
#!/bin/bash
# setup-team.sh

set -e

echo "🔧 Setting up AWS Spot Deployer for team use..."

# Download binary (example)
if [[ "$OSTYPE" == "darwin"* ]]; then
    BINARY_NAME="aws-spot-deployer-macos-arm64"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    BINARY_NAME="aws-spot-deployer-linux-x64"
else
    echo "Unsupported platform: $OSTYPE"
    exit 1
fi

# Download from internal server
wget "http://internal-tools.company.com/$BINARY_NAME"
chmod +x "$BINARY_NAME"
mv "$BINARY_NAME" /usr/local/bin/aws-spot-deployer

# Setup configuration
mkdir -p ~/.aws-spot-deployer
wget "http://internal-tools.company.com/config-team-template.yaml" \
     -O ~/.aws-spot-deployer/config.yaml

echo "✅ Setup complete!"
echo "Next steps:"
echo "1. Edit ~/.aws-spot-deployer/config.yaml"
echo "2. Set BACALHAU_TOKEN environment variable"
echo "3. Run: aws-spot-deployer --action verify"
```

### 3. Team Documentation

```markdown
# Quick Start for Internal Teams

## Installation

```bash
curl -sSL https://internal-tools.company.com/setup-team.sh | bash
```

## Usage

```bash
# Verify setup
aws-spot-deployer --action verify

# Deploy instances
aws-spot-deployer --action create

# List instances  
aws-spot-deployer --action list

# Cleanup
aws-spot-deployer --action destroy
```

## Configuration

Edit `~/.aws-spot-deployer/config.yaml`:
- Set your SSH key paths
- Configure regions as needed
- Adjust instance counts

## Support

- Documentation: https://internal-wiki.company.com/aws-spot-deployer
- Issues: https://internal-git.company.com/devops/aws-spot-deployer/issues
- Slack: #devops-tools
```

## 🔄 CI/CD Integration

### GitHub Actions

```yaml
# .github/workflows/build-binaries.yml
name: Build Binaries

on:
  push:
    tags: ['v*']
  workflow_dispatch:

jobs:
  build:
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
    
    runs-on: ${{ matrix.os }}
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Setup Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: pip install pyinstaller boto3 rich aiosqlite pyyaml
    
    - name: Build binary
      run: python build.py --target portable --package
    
    - name: Upload artifacts
      uses: actions/upload-artifact@v3
      with:
        name: binaries-${{ matrix.os }}
        path: dist/
    
    - name: Create release
      if: startsWith(github.ref, 'refs/tags/')
      uses: softprops/action-gh-release@v1
      with:
        files: dist/aws-spot-deployer-*
```

### GitLab CI

```yaml
# .gitlab-ci.yml
stages:
  - build
  - release

variables:
  PYTHON_VERSION: "3.11"

build-linux:
  stage: build
  image: python:${PYTHON_VERSION}-slim
  before_script:
    - pip install pyinstaller boto3 rich aiosqlite pyyaml
  script:
    - python build.py --target portable
  artifacts:
    paths:
      - dist/
    expire_in: 1 week

build-windows:
  stage: build
  tags:
    - windows
  script:
    - pip install pyinstaller boto3 rich aiosqlite pyyaml
    - python build.py --target portable
  artifacts:
    paths:
      - dist/
    expire_in: 1 week

release:
  stage: release
  image: registry.gitlab.com/gitlab-org/release-cli:latest
  rules:
    - if: $CI_COMMIT_TAG
  script:
    - echo "Creating release $CI_COMMIT_TAG"
  release:
    name: 'Release $CI_COMMIT_TAG'
    description: 'AWS Spot Deployer $CI_COMMIT_TAG'
    assets:
      links:
        - name: 'Linux Binary'
          url: '$CI_PROJECT_URL/-/jobs/artifacts/$CI_COMMIT_TAG/download?job=build-linux'
        - name: 'Windows Binary'
          url: '$CI_PROJECT_URL/-/jobs/artifacts/$CI_COMMIT_TAG/download?job=build-windows'
```

## 📊 Binary Size Optimization

### Reducing Binary Size

```bash
# Use UPX compression (reduces size by ~60%)
pip install upx-ucl

# Build with optimization
python build.py --target portable
upx --best dist/aws-spot-deployer-*

# Exclude unnecessary modules
pyinstaller \
  --onefile \
  --exclude-module tkinter \
  --exclude-module matplotlib \
  --exclude-module scipy \
  deploy_spot_portable.py
```

### Size Comparison

| Version | Uncompressed | UPX Compressed | Reduction |
|---------|-------------|----------------|-----------|
| Portable | ~85 MB | ~30 MB | 65% |
| Modular | ~92 MB | ~35 MB | 62% |

## 🔒 Security Considerations

### Binary Verification

```bash
# Generate checksums
sha256sum dist/aws-spot-deployer-* > checksums.txt

# Sign binaries (if you have code signing certificates)
codesign -s "Developer ID" dist/aws-spot-deployer-macos-arm64

# Verify downloads
sha256sum -c checksums.txt
```

### Distribution Security

1. **Internal Distribution Only**: Keep binaries on internal servers
2. **Access Control**: Restrict download access to team members
3. **Version Control**: Track who downloads which versions
4. **Regular Updates**: Rebuild and redistribute regularly
5. **Antivirus Whitelist**: Add to corporate antivirus exceptions

## 🆘 Troubleshooting

### Common Build Issues

```bash
# Missing dependencies
pip install pyinstaller boto3 rich aiosqlite pyyaml

# Permission issues
chmod +x build.py

# Large binary size
# Use --exclude-module for unused packages

# Import errors in binary
# Add --hidden-import for missing modules
```

### Runtime Issues

```bash
# Binary won't start
# Check dependencies with ldd (Linux) or otool (macOS)

# AWS authentication
# Ensure AWS credentials are configured on target system

# Config file not found
# Include config template with binary distribution
```

## 🎉 Success Metrics

After implementing binary distribution:

- ✅ **Zero Python Installation Required**: Team members run tool immediately
- ✅ **Consistent Environment**: Same dependencies across all systems  
- ✅ **Easy Distribution**: Single file to share
- ✅ **Platform Support**: Works on Windows, macOS, Linux
- ✅ **Internal Control**: Managed distribution through internal channels
- ✅ **Version Management**: Clear versioning and update process

This binary distribution approach will make it extremely easy for your internal team to use the AWS Spot Instance Deployment Tool without any technical setup requirements.