#!/bin/bash
# Quick test to verify deployment fixes

echo "=== Deployment Fix Verification ==="
echo ""

echo "1. Checking for simple-startup.py..."
if [ -f "instance/scripts/simple-startup.py" ]; then
    echo "✅ simple-startup.py exists"
else
    echo "❌ simple-startup.py missing!"
fi

echo ""
echo "2. Checking bacalhau-startup.service references simple-startup.py..."
if grep -q "simple-startup.py" instance/scripts/bacalhau-startup.service; then
    echo "✅ Service correctly references simple-startup.py"
else
    echo "❌ Service does not reference simple-startup.py!"
fi

echo ""
echo "3. Checking for bacalhau-config.yaml..."
if [ -f "instance/config/bacalhau-config.yaml" ]; then
    echo "✅ bacalhau-config.yaml exists"
else
    echo "❌ bacalhau-config.yaml missing!"
fi

echo ""
echo "4. Checking all required service files exist..."
services=("bacalhau-startup.service" "setup-config.service" "bacalhau.service" "sensor-generator.service")
all_good=true
for service in "${services[@]}"; do
    if [ -f "instance/scripts/$service" ]; then
        echo "✅ $service exists"
    else
        echo "❌ $service missing!"
        all_good=false
    fi
done

echo ""
echo "5. Checking for docker-compose files..."
compose_files=("docker-compose-bacalhau.yaml" "docker-compose-sensor.yaml")
for compose in "${compose_files[@]}"; do
    if [ -f "instance/scripts/$compose" ]; then
        echo "✅ $compose exists"
    else
        echo "❌ $compose missing!"
    fi
done

echo ""
echo "6. Checking deployment script syntax..."
if uv run ruff check deploy_spot.py > /dev/null 2>&1; then
    echo "✅ deploy_spot.py passes syntax check"
else
    echo "❌ deploy_spot.py has syntax errors!"
    echo "Run: uv run ruff check deploy_spot.py"
fi

echo ""
echo "=== Summary ==="
echo "If all checks pass, the deployment should work correctly."
echo "Run './debug_deployment.sh <instance-ip>' after deployment to verify."