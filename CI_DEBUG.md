# CI/CD Debugging Guide

## Common CI Failures and Fixes

### 1. Python Module Import Errors

**Issue**: `ModuleNotFoundError: No module named 'spot_deployer'`

**Fix**: The Dockerfile needs to ensure the Python package structure is correct:

```dockerfile
# Add this to ensure Python recognizes the package
COPY spot_deployer/ ./spot_deployer/
RUN touch spot_deployer/__init__.py
```

### 2. Missing Dependencies

**Issue**: Build fails due to missing system packages

**Fix**: Ensure all dependencies are in the Dockerfile:
```dockerfile
RUN apt-get update && apt-get install -y \
    curl \
    git \
    openssh-client \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*
```

### 3. UV Installation Issues

**Issue**: UV not found or installation fails

**Fix**: Use the official UV installation method:
```dockerfile
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    mv /root/.local/bin/uv /usr/local/bin/uv
```

### 4. File Permissions

**Issue**: Permission denied on scripts

**Fix**: Ensure scripts are executable:
```dockerfile
RUN chmod +x /usr/local/bin/docker-entrypoint.sh
```

### 5. Multi-arch Build Failures

**Issue**: Build fails on ARM64

**Fix**: Use buildx with proper setup:
```yaml
- name: Set up QEMU
  uses: docker/setup-qemu-action@v3
```

### 6. Registry Authentication

**Issue**: Permission denied pushing to ghcr.io

**Fix**: Ensure proper permissions in workflow:
```yaml
permissions:
  contents: read
  packages: write
```

### 7. Image Naming

**Issue**: Invalid image name

**Fix**: Use the repository name directly:
```yaml
env:
  IMAGE_NAME: ${{ github.repository }}
```

## Quick Test Build Locally

Test the build locally before pushing:

```bash
# Build for current platform only
docker build -t test-spot .

# Test multi-platform build
docker buildx create --use
docker buildx build --platform linux/amd64,linux/arm64 -t test-spot .

# Run basic test
docker run --rm test-spot help
```

## Debugging CI Logs

1. Go to Actions tab in GitHub
2. Click on the failed workflow run
3. Look for these common errors:
   - "exec format error" = architecture mismatch
   - "permission denied" = file permissions or registry auth
   - "not found" = missing files or wrong paths
   - "no such file" = COPY command has wrong source path

## Minimal Working Dockerfile

If all else fails, start with this minimal version:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN apt-get update && apt-get install -y curl openssh-client && \
    rm -rf /var/lib/apt/lists/*

# Install Python packages
COPY requirements.txt .
RUN pip install -r requirements.txt

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    mv /root/.local/bin/uv /usr/local/bin/uv

# Copy application
COPY spot_deployer/ ./spot_deployer/
COPY instance/ ./instance/
COPY docker-entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["help"]
```