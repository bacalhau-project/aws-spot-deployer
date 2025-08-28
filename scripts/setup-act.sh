#!/bin/bash
# /// script
# description = "Setup GitHub Actions local runner with act"
# ///

set -euo pipefail

echo "🔧 Setting up GitHub Actions local testing with 'act'"
echo "=================================================="

# Check if act is installed
if command -v act &> /dev/null; then
    echo "✅ act is already installed: $(act --version)"
else
    echo "📦 Installing act..."

    # Detect OS and install act
    if [[ "$OSTYPE" == "darwin"* ]]; then
        if command -v brew &> /dev/null; then
            brew install act
        else
            echo "❌ Please install Homebrew first, then run: brew install act"
            exit 1
        fi
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Install via curl
        curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash
    else
        echo "❌ Unsupported OS. Please install act manually: https://github.com/nektos/act"
        exit 1
    fi
fi

# Create act configuration
cat > .actrc << 'EOF'
# Use medium runner for better compatibility
-P ubuntu-latest=catthehacker/ubuntu:act-latest
-P ubuntu-22.04=catthehacker/ubuntu:act-22.04

# Set environment variables
--env UV_CACHE_DIR=/tmp/uv-cache

# Enable verbose output for debugging
--verbose
EOF

echo "✅ Created .actrc configuration"

# Create a script to run specific workflows
cat > scripts/run-ci-with-act.sh << 'EOF'
#!/bin/bash
# Run GitHub Actions locally with act

set -euo pipefail

echo "🚀 Running GitHub Actions CI locally with act"
echo "============================================="

# Run the CI workflow
echo "▶ Running CI workflow..."
act -W .github/workflows/ci.yml

echo ""
echo "✅ Local GitHub Actions test completed!"
echo "If this passes, your CI should pass on GitHub"
EOF

chmod +x scripts/run-ci-with-act.sh

echo ""
echo "✅ Setup complete!"
echo ""
echo "Usage:"
echo "  ./scripts/run-ci-with-act.sh     # Run CI workflow locally"
echo "  act -l                           # List available workflows"
echo "  act -W .github/workflows/ci.yml  # Run specific workflow"
echo ""
echo "Note: First run will download Docker images (~2GB)"
