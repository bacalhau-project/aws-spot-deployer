# Installation Guide

## Quick Start (Recommended)

Deploy spot instances with a single command:

```bash
curl -sSL https://bac.al/spot | bash -s -- create
```

## First Time Setup

1. **Run initial setup**:
   ```bash
   curl -sSL https://bac.al/spot | bash -s -- setup
   ```

2. **Edit configuration**:
   ```bash
   nano ~/.spot-deployer/config/config.yaml
   ```

3. **Add your SSH key path and AWS settings**

4. **Deploy instances**:
   ```bash
   curl -sSL https://bac.al/spot | bash -s -- create
   ```

## Configuration

The installer creates a working directory at `~/.spot-deployer` with:
- `config/config.yaml` - Main configuration file
- `files/` - Files to upload to instances
- `output/` - State files and logs

## Prerequisites

- Docker installed and running
- AWS credentials configured (via AWS CLI, environment variables, or SSO)
- SSH key pair for instance access

## Advanced Usage

### Version Selection
By default, the installer uses the latest stable release. You can specify different versions:

```bash
# Use latest stable release (default)
curl -sSL https://bac.al/spot | bash -s -- create

# Use latest development version from main branch
curl -sSL https://bac.al/spot | bash -s -- create --version latest

# Use specific version
curl -sSL https://bac.al/spot | bash -s -- create --version v1.0.0
```

### Dry Run
```bash
curl -sSL https://bac.al/spot | bash -s -- create --dry-run
```

### Custom Working Directory
```bash
export SPOT_WORK_DIR=/path/to/workdir
curl -sSL https://bac.al/spot | bash -s -- create
```