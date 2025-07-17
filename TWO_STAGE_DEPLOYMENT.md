# Two-Stage Deployment Solution

## Overview

This solution solves the AWS cloud-init 16KB size limit by using a two-stage deployment:

1. **Stage 1**: Minimal cloud-init (3.6KB) that sets up basic environment and waits for files
2. **Stage 2**: deploy_spot.py uploads compressed bundle (22.7KB) after instance is ready

## Benefits

- ✅ Cloud-init stays well under 16KB limit (only 3.6KB)
- ✅ No external dependencies (S3, HTTP servers)
- ✅ All files deployed automatically
- ✅ Clean separation of concerns
- ✅ Instances bootstrap autonomously after receiving files

## How It Works

### Stage 1: Cloud-Init (3.6KB)
- Sets up user, SSH keys, and basic packages
- Creates directory structure
- Embeds orchestrator credentials
- Runs a systemd service that waits for `/opt/deployment-bundle.tar.gz`
- When bundle arrives, extracts it and starts services

### Stage 2: File Upload (22.7KB)
- deploy_spot.py creates instances with minimal cloud-init
- Waits for instances to be accessible via SSH
- Creates compressed bundle of all deployment files
- Uploads bundle via SCP to each instance
- Instances automatically detect and process the bundle

## Implementation Steps

### 1. Update deploy_spot.py

Add these functions to deploy_spot.py:

```python
def generate_full_cloud_init(config: SimpleConfig) -> str:
    """Generate minimal cloud-init that waits for deployment bundle."""
    # See generate_wait_cloud_init.py for full implementation
    # This creates a 3.6KB cloud-init that waits for files

def create_deployment_bundle(config: SimpleConfig) -> str:
    """Create a tar.gz bundle of all deployment files."""
    # See create_deployment_bundle.py for implementation
    # Creates a 22.7KB compressed bundle

def upload_deployment_bundle(hostname: str, username: str, private_key_path: str, bundle_file: str, logger=None) -> bool:
    """Upload deployment bundle to instance via SCP."""
    # Simple SCP upload function
```

### 2. Modify wait_for_instance_ready

Add bundle upload after SSH is accessible:

```python
# In wait_for_instance_ready function, after "Instance accessible":
if elapsed > 30:  # Give cloud-init time to set up
    # Create bundle once
    if not hasattr(wait_for_instance_ready, '_bundle_file'):
        bundle_file = create_deployment_bundle(config)
        wait_for_instance_ready._bundle_file = bundle_file
    
    # Upload bundle
    if upload_deployment_bundle(hostname, username, private_key_path, 
                               wait_for_instance_ready._bundle_file, logger):
        update_progress("Upload", 85, "Deployment files uploaded")
    else:
        update_progress("Upload", 70, "Upload failed, retrying...")
```

## File Sizes

- **Original cloud-init**: 120KB (❌ 750% over limit)
- **New cloud-init**: 3.6KB (✅ 22% of limit)
- **Deployment bundle**: 22.7KB (compressed)
- **Total transfer**: 26.3KB (split into two stages)

## Testing

1. Test cloud-init size:
   ```bash
   uv run generate_wait_cloud_init.py
   # Output: 3.6KB (29.7% of AWS limit)
   ```

2. Test bundle creation:
   ```bash
   uv run create_deployment_bundle.py
   # Output: deployment-bundle.tar.gz (22.7KB)
   ```

3. Deploy and verify:
   ```bash
   uv run -s deploy_spot.py create
   # Watch for "Deployment files uploaded" status
   ```

## Debugging

If deployment fails:

1. Check cloud-init completed:
   ```bash
   ssh ubuntu@<ip> "cloud-init status"
   ```

2. Check if waiting for bundle:
   ```bash
   ssh ubuntu@<ip> "tail -f /opt/startup.log"
   ```

3. Manually upload bundle:
   ```bash
   scp -i ~/.ssh/key.pem deployment-bundle.tar.gz ubuntu@<ip>:/opt/
   ```

4. Check systemd service:
   ```bash
   ssh ubuntu@<ip> "sudo systemctl status wait-deployment.service"
   ```

## Alternative Approaches

If you need to deploy even larger file sets:

1. **GitHub Release**: Host bundle on GitHub releases, download in cloud-init
2. **S3 with IAM Role**: Give instances IAM role to download from S3
3. **Multiple Bundles**: Split into multiple smaller uploads
4. **Compression**: Use better compression (xz instead of gzip)

## Summary

This two-stage approach elegantly solves the cloud-init size limit while maintaining full automation and avoiding external dependencies. The deployment remains fast, reliable, and self-contained.