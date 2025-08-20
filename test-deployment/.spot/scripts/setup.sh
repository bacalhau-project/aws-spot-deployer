#!/bin/bash
# Example setup script for portable deployment

set -e

echo "========================================="
echo "Starting portable deployment setup"
echo "========================================="

# Update system
echo "Updating system packages..."
apt-get update

# Start nginx
echo "Starting nginx..."
systemctl start nginx
systemctl enable nginx

# Create a test page
cat > /var/www/html/index.html << 'EOF'
<!DOCTYPE html>
<html>
<head>
    <title>Portable Spot Deployment</title>
</head>
<body>
    <h1>Success!</h1>
    <p>This instance was deployed using the portable spot deployer.</p>
    <p>Instance ID: $(ec2-metadata --instance-id | cut -d' ' -f2)</p>
    <p>Region: $(ec2-metadata --availability-zone | cut -d' ' -f2 | sed 's/.$//')</p>
</body>
</html>
EOF

echo "Setup complete!"
echo "Web server running on port 80"