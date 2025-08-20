# Node.js Application Deployment Example

This example shows how to deploy a Node.js web application using spot-deployer.

## Structure

```
.spot/
├── deployment.yaml      # Deployment manifest
├── scripts/
│   ├── install.sh      # Install application
│   └── nginx.sh        # Configure Nginx reverse proxy
├── services/
│   └── nodeapp.service # SystemD service for Node.js app
└── configs/
    ├── app.env         # Application environment variables
    └── nginx.conf      # Nginx configuration
```

## Usage

1. **Customize the deployment**:
   - Edit `scripts/install.sh` to add your app's Git URL or download location
   - Update `configs/app.env` with your environment variables
   - Modify `configs/nginx.conf` with your domain name

2. **Validate the deployment**:
   ```bash
   spot validate
   ```

3. **Deploy to AWS**:
   ```bash
   spot create
   ```

4. **Check deployment status**:
   ```bash
   spot list
   ```

## What Gets Deployed

- Ubuntu 22.04 instances with:
  - Node.js and npm
  - Nginx as reverse proxy
  - Your Node.js application as a SystemD service
  - SSL support ready (via Certbot)

## Post-Deployment

After deployment, SSH into your instances to:

1. **Check service status**:
   ```bash
   sudo systemctl status nodeapp
   ```

2. **View logs**:
   ```bash
   sudo journalctl -u nodeapp -f
   ```

3. **Setup SSL** (optional):
   ```bash
   sudo certbot --nginx -d yourdomain.com
   ```

## Customization

- **Multiple services**: Add more `.service` files in `services/`
- **Database setup**: Add database installation to scripts
- **Monitoring**: Add monitoring agents to the deployment
- **Load balancing**: Deploy multiple instances with AWS ELB