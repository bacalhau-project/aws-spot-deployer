# Docker Installation Update

## Changes Made

### Using Docker's Official APT Repository

Updated the installation to use Docker's official APT repository as recommended by Docker. This is the standard, reliable way to install Docker and Docker Compose v2.

### Cloud-init Changes

1. **Removed** `docker.io` from packages list (Ubuntu's outdated version)
2. **Added** prerequisite packages for Docker's repository:
   - `ca-certificates`
   - `gnupg` 
   - `lsb-release`
   - `apt-transport-https`
   - `software-properties-common`

3. **Updated runcmd** to install Docker properly:
   ```bash
   # Add Docker's official GPG key
   curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
   
   # Add Docker repository
   echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
   
   # Install Docker packages
   apt-get update -qq
   apt-get install -qq -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
   ```

### What Gets Installed

- **docker-ce**: Docker Community Edition (latest stable)
- **docker-ce-cli**: Docker CLI
- **containerd.io**: Container runtime
- **docker-buildx-plugin**: BuildKit plugin for advanced builds
- **docker-compose-plugin**: Docker Compose v2 (as `docker compose`)

### Advantages

1. **Always up-to-date**: Gets latest stable Docker version
2. **Official support**: This is Docker's recommended installation method
3. **Includes all plugins**: Docker Compose v2 is included as a plugin
4. **Reliable**: No fragile GitHub downloads or manual binary installs
5. **Proper dependencies**: All required components installed together

### Simplified startup.py

Since Docker Compose is now properly installed, the startup script no longer needs to:
- Try to install docker-compose-plugin from apt (doesn't exist)
- Download binaries from GitHub
- Create plugin directories manually

It now simply checks if `docker compose` works and fails with a clear error if not.

## Testing

After deployment, Docker and Docker Compose v2 should work immediately:

```bash
ssh -i ~/.ssh/your-key ubuntu@<ip> "docker --version"
ssh -i ~/.ssh/your-key ubuntu@<ip> "docker compose version"
```

Expected output:
- Docker version 27.x.x or later
- Docker Compose version v2.x.x