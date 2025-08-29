#!/bin/bash
# Converted from SkyPilot setup commands

set -e

set -e

# Update system
sudo apt-get update -qq

# Install essential packages
sudo apt-get install -y \
  python3 \
  python3-pip \
  curl \
  wget \
  unzip \
  jq \
  net-tools

# Install Docker
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER

# Install Docker Compose plugin
sudo apt-get install -y docker-compose-plugin

# Create directory structure
sudo mkdir -p \
  /etc/bacalhau \
  /bacalhau_data \
  /bacalhau_node \
  /opt/bacalhau \
  /opt/sensor/config \
  /opt/sensor/data \
  /opt/sensor/exports \
  /opt/credentials \
  /opt/config \
  /opt/compose \
  /opt/scripts \
  /var/log/bacalhau \
  /root/.aws \
  /home/ubuntu/.aws

# Set proper ownership
sudo chown -R ubuntu:ubuntu \
  /opt/bacalhau \
  /opt/sensor \
  /bacalhau_data \
  /bacalhau_node \
  /home/ubuntu/.aws

# Move uploaded files to proper locations
sudo mv /tmp/credentials/* /opt/credentials/ 2>/dev/null || echo "No credentials files to move"
sudo mv /tmp/compose/* /opt/compose/ 2>/dev/null || echo "No compose files to move"
sudo mv /tmp/scripts/* /opt/scripts/ 2>/dev/null || echo "No script files to move"

# Move config files to correct locations
sudo mv /tmp/config/bacalhau-config-template.yaml /opt/config/ 2>/dev/null || echo "No bacalhau config to move"
sudo mv /tmp/config/sensor-config.yaml /opt/sensor/config/ 2>/dev/null || echo "No sensor config to move"

# Make scripts executable
sudo chmod +x /opt/scripts/*.sh /opt/scripts/*.py

# Set up AWS credentials for containers
sudo cp /opt/credentials/aws-credentials /root/.aws/credentials 2>/dev/null || true
sudo cp /opt/credentials/aws-credentials /home/ubuntu/.aws/credentials 2>/dev/null || true
sudo chmod 600 /root/.aws/credentials /home/ubuntu/.aws/credentials 2>/dev/null || true

# Tag AWS resources for proper identification and cleanup
INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id 2>/dev/null || echo "unknown")
REGION=$(curl -s http://169.254.169.254/latest/meta-data/placement/availability-zone 2>/dev/null | sed 's/.$//' || echo "us-west-2")

if [ "$INSTANCE_ID" != "unknown" ] && [ "$REGION" != "unknown" ]; then
  # Install AWS CLI if not present
  if ! command -v aws &> /dev/null; then
    curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
    unzip awscliv2.zip
    sudo ./aws/install
    rm -rf aws awscliv2.zip
  fi

  # Tag the instance
  aws ec2 create-tags --region "$REGION" --resources "$INSTANCE_ID" --tags \
    Key=Project,Value=databricks-wind-farm-cluster \
    Key=DeploymentID,Value="${DEPLOYMENT_ID}" \
    Key=Purpose,Value=bacalhau-compute-node \
    Key=ManagedBy,Value=skypilot \
    Key=Environment,Value=production 2>/dev/null || true

  # Tag associated volumes
  VOLUMES=$(aws ec2 describe-instances --region "$REGION" --instance-ids "$INSTANCE_ID" \
    --query 'Reservations[].Instances[].BlockDeviceMappings[].Ebs.VolumeId' --output text 2>/dev/null || echo "")

  for volume in $VOLUMES; do
    aws ec2 create-tags --region "$REGION" --resources "$volume" --tags \
      Key=Project,Value=databricks-wind-farm-cluster \
      Key=DeploymentID,Value="${DEPLOYMENT_ID}" \
      Key=Purpose,Value=bacalhau-storage \
      Key=ManagedBy,Value=skypilot \
      Key=Environment,Value=production 2>/dev/null || true
  done
fi
