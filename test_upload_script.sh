#!/bin/bash
# Test script for demonstrating upload-script functionality

echo "=== Test Script Execution ==="
echo "Hostname: $(hostname)"
echo "Current user: $(whoami)"
echo "Current directory: $(pwd)"
echo "Date/Time: $(date)"
echo "System uptime: $(uptime)"

# Test some system information
echo -e "\n=== System Information ==="
echo "OS: $(cat /etc/os-release | grep PRETTY_NAME | cut -d'"' -f2)"
echo "Kernel: $(uname -r)"
echo "Architecture: $(uname -m)"

# Test network connectivity
echo -e "\n=== Network Test ==="
echo "External IP: $(curl -s https://ipinfo.io/ip || echo 'Unable to determine')"
echo "DNS test: $(nslookup google.com > /dev/null && echo 'DNS working' || echo 'DNS issues')"

# Test Docker if available
echo -e "\n=== Docker Status ==="
if command -v docker > /dev/null; then
    echo "Docker version: $(docker --version)"
    echo "Docker status: $(systemctl is-active docker 2>/dev/null || echo 'not available')"
else
    echo "Docker not installed"
fi

# Test Bacalhau if available
echo -e "\n=== Bacalhau Status ==="
if command -v bacalhau > /dev/null; then
    echo "Bacalhau version: $(bacalhau version --output json 2>/dev/null | grep -o '"GitVersion":"[^"]*' | cut -d'"' -f4 || echo 'version unavailable')"
else
    echo "Bacalhau not installed"
fi

echo -e "\n=== Script completed successfully ==="
exit 0