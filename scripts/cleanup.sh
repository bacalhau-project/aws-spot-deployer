#!/bin/bash
# Aggressive cleanup script for amauo project
# Run this to remove temporary files, logs, and prevent conflicts

set -e

echo "🧹 Starting aggressive cleanup of amauo project..."

# Remove all log files (both old spot naming and new amauo naming)
echo "Cleaning up log files..."
rm -f ./*.log
rm -f ./spot_*.log
rm -f ./amauo_*.log
rm -f ./*_creation_*.log
rm -f ./*_destroy_*.log

# Remove Python cache and compiled files
echo "Cleaning up Python cache..."
find . -name "*.pyc" -delete 2>/dev/null || true
find . -name "*.pyo" -delete 2>/dev/null || true
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# Remove editor and system temp files
echo "Cleaning up editor and system files..."
find . -name ".DS_Store" -delete 2>/dev/null || true
find . -name "*.swp" -delete 2>/dev/null || true
find . -name "*.tmp" -delete 2>/dev/null || true
find . -name "*~" -delete 2>/dev/null || true
find . -name "*.bak" -delete 2>/dev/null || true
find . -name "*.orig" -delete 2>/dev/null || true
find . -name "*.old" -delete 2>/dev/null || true

# Clean up any leftover temporary tarballs
echo "Cleaning up temporary tarballs..."
rm -f /tmp/*spot*deployment*.tar.gz 2>/dev/null || true
rm -f /tmp/*amauo*deployment*.tar.gz 2>/dev/null || true
rm -rf /tmp/spot-deployer/ 2>/dev/null || true
rm -rf /tmp/amauo/ 2>/dev/null || true

# Clean up any duplicate or conflicting deployment files
echo "Removing conflicting deployment files..."
# Keep only the root setup.sh, remove any nested ones
find ./instance-files -path "./instance-files/setup.sh" -prune -o -name "setup.sh" -delete 2>/dev/null || true

# Remove any old instance files directory contents
rm -rf ./instance/files/* 2>/dev/null || true

# Clean up any potential state file conflicts
echo "Cleaning up state files..."
# Don't remove instances.json as it contains active deployment state
# but clean up any backup/temp versions
rm -f ./instances.json.bak 2>/dev/null || true
rm -f ./instances.json.tmp 2>/dev/null || true
rm -f ./instances.json.old 2>/dev/null || true

# Clean up any AWS cache
echo "Cleaning up AWS cache..."
rm -rf ./.aws_cache/orphaned_* 2>/dev/null || true

# Remove any conflicting config files
echo "Checking for config conflicts..."
# Don't remove main config.yaml but remove any backups
rm -f ./config.yaml.bak 2>/dev/null || true
rm -f ./config.yaml.old 2>/dev/null || true
rm -f ./config.yaml.tmp 2>/dev/null || true

echo "✅ Cleanup complete!"
echo ""
echo "📋 Summary of cleaned items:"
echo "  • All log files (spot_*.log, amauo_*.log)"
echo "  • Python cache (__pycache__, *.pyc)"
echo "  • Editor temp files (*.swp, *~, .DS_Store)"
echo "  • Temporary tarballs in /tmp"
echo "  • Duplicate setup.sh files"
echo "  • State and config backups"
echo ""
echo "💡 To prevent future conflicts:"
echo "  • This script runs automatically during deployment"
echo "  • Updated .gitignore prevents temp file commits"
echo "  • Use only instance-files/ for deployment structure"