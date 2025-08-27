# Installation Guide

## Quick Start (Recommended)

Deploy spot instances with a single command:

```bash
curl -sSL https://bac.al/spot | bash -s -- create
```

## First Time Setup

1. **Run initial setup** (in your project directory):
   ```bash
   curl -sSL https://bac.al/spot | bash -s -- setup
   ```

2. **Edit configuration**:
   ```bash
   nano config.yaml
   ```

3. **Add your SSH key path and AWS settings**

4. **Deploy instances**:
   ```bash
   curl -sSL https://bac.al/spot | bash -s -- create
   ```

## Configuration

The installer uses your current directory for all files:
- `config.yaml` - Main configuration file (created by setup)
- `files/` - Files to upload to instances (optional)
- `output/` - State files and logs (created automatically)

## Prerequisites

- Python 3.12+ (uv/uvx will be installed automatically if needed)
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

### Custom File Locations
```bash
# Use config from different location
export SPOT_CONFIG_FILE=/path/to/config.yaml
curl -sSL https://bac.al/spot | bash -s -- create

# Use custom output directory
export SPOT_OUTPUT_DIR=/path/to/output
curl -sSL https://bac.al/spot | bash -s -- list
```
