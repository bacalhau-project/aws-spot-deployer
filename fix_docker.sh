#!/bin/bash
# Manual Docker fix script - run this on the instance
set -e

echo "=== Fixing Docker Installation ==="
echo ""

echo "1. Configuring any incomplete packages..."
sudo dpkg --configure -a

echo ""
echo "2. Updating package lists..."
sudo apt-get update

echo ""
echo "3. Fixing broken dependencies..."
sudo apt-get install -f -y

echo ""
echo "4. Installing Docker..."
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

echo ""
echo "5. Starting Docker service..."
sudo systemctl start docker
sudo systemctl enable docker

echo ""
echo "6. Adding user to docker group..."
sudo usermod -aG docker $USER

echo ""
echo "7. Verifying Docker installation..."
docker --version
docker compose version

echo ""
echo "8. Testing Docker..."
sudo docker run hello-world

echo ""
echo "=== Docker Installation Fixed! ==="
echo "Note: You may need to log out and back in for group membership to take effect."
echo "Or run: newgrp docker"