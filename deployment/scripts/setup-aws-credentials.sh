#!/bin/bash
# Setup AWS credentials for Databricks S3 access

set -e

echo "[$(date)] Setting up AWS credentials for Databricks S3 access..."

# Create AWS directories for both root and ubuntu users
mkdir -p /root/.aws
mkdir -p /home/ubuntu/.aws

# Function to setup credentials for a user
setup_credentials() {
    local USER=$1
    local HOME_DIR=$2

    echo "[$(date)] Configuring AWS credentials for $USER..."

    # Check if we have the expanso S3 credentials
    if [ -f /opt/deployment/etc/aws/credentials/expanso-s3-credentials ]; then
        echo "[$(date)] Found expanso S3 credentials file"
        cp /opt/deployment/etc/aws/credentials/expanso-s3-credentials $HOME_DIR/.aws/credentials
        chmod 600 $HOME_DIR/.aws/credentials
        chown $USER:$USER $HOME_DIR/.aws/credentials
    elif [ -f /opt/deployment/etc/aws/credentials ]; then
        echo "[$(date)] Found general AWS credentials file"
        cp /opt/deployment/etc/aws/credentials $HOME_DIR/.aws/credentials
        chmod 600 $HOME_DIR/.aws/credentials
        chown $USER:$USER $HOME_DIR/.aws/credentials
    else
        echo "[$(date)] WARNING: No AWS credentials found in deployment files"
    fi

    # Setup AWS config
    cat > $HOME_DIR/.aws/config << 'EOF'
[default]
region = us-west-2
output = json
EOF
    chmod 600 $HOME_DIR/.aws/config
    chown $USER:$USER $HOME_DIR/.aws/config
}

# Setup for root (needed for Docker containers)
setup_credentials "root" "/root"

# Setup for ubuntu user
setup_credentials "ubuntu" "/home/ubuntu"

# Copy S3 configuration files if they exist
if [ -f /opt/deployment/etc/aws/credentials/expanso-s3-config.json ]; then
    echo "[$(date)] Copying S3 configuration file..."
    cp /opt/deployment/etc/aws/credentials/expanso-s3-config.json /opt/sensor/config/s3-config.json
    chown ubuntu:ubuntu /opt/sensor/config/s3-config.json
    chmod 644 /opt/sensor/config/s3-config.json
fi

# Copy Databricks configuration if it exists
if [ -f /opt/deployment/etc/aws/credentials/databricks-storage-config.yaml ]; then
    echo "[$(date)] Copying Databricks storage configuration..."
    cp /opt/deployment/etc/aws/credentials/databricks-storage-config.yaml /opt/sensor/config/
    chown ubuntu:ubuntu /opt/sensor/config/databricks-storage-config.yaml
    chmod 644 /opt/sensor/config/databricks-storage-config.yaml
fi

# Setup environment variables for S3 access
if [ -f /opt/deployment/etc/aws/credentials/expanso-production.env ]; then
    echo "[$(date)] Setting up S3 environment variables..."
    cp /opt/deployment/etc/aws/credentials/expanso-production.env /opt/sensor/.env
    chown ubuntu:ubuntu /opt/sensor/.env
    chmod 600 /opt/sensor/.env

    # Also create a Docker env file
    cp /opt/deployment/etc/aws/credentials/expanso-production.docker.env /opt/sensor/docker.env 2>/dev/null || true
    if [ -f /opt/sensor/docker.env ]; then
        chown ubuntu:ubuntu /opt/sensor/docker.env
        chmod 600 /opt/sensor/docker.env
    fi
fi

# Verify credentials are working
echo "[$(date)] Verifying AWS credentials..."
if aws sts get-caller-identity &>/dev/null; then
    echo "[$(date)] AWS credentials are working!"
    aws sts get-caller-identity --output json | jq -r '.Arn' || true
else
    echo "[$(date)] WARNING: AWS credentials verification failed"
fi

# Test S3 access to Databricks buckets
echo "[$(date)] Testing S3 bucket access..."
for BUCKET in expanso-databricks-raw-us-west-2 expanso-databricks-schematized-us-west-2 expanso-databricks-filtered-us-west-2 expanso-databricks-emergency-us-west-2; do
    if aws s3 ls s3://$BUCKET --max-items 1 &>/dev/null; then
        echo "[$(date)] ✓ Access confirmed to s3://$BUCKET"
    else
        echo "[$(date)] ✗ Cannot access s3://$BUCKET"
    fi
done

echo "[$(date)] AWS credential setup completed"
