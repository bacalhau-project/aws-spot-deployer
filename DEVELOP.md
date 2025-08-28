# Development & Release Process

This document outlines our development workflow using **Jujutsu (jj)** for version control and our automated release pipeline.

## 🏗️ Development Workflow

We use a feature branch workflow with Jujutsu to maintain clean release notes and proper change tracking.

### Prerequisites

1. **Install Jujutsu**: `cargo install --locked jj-cli` or `brew install jj`
2. **Setup repo**: If migrating from git: `jj git import`
3. **Configure jj**:
   ```bash
   jj config set --user user.name "Your Name"
   jj config set --user user.email "your.email@example.com"
   ```

### Branch Strategy

- **`main`** - Protected branch, releases only
- **`develop`** - Integration branch for features
- **`feature/*`** - Individual feature development
- **`fix/*`** - Bug fixes
- **`release/*`** - Release preparation

## 🚀 Development Process

### 1. Start New Feature

```bash
# Create and checkout feature branch
jj new main -m "Start feature: add multi-cloud support"
jj branch create feature/multi-cloud-support

# Or start from develop for integration features
jj new develop -m "Start feature: improve logging"
jj branch create feature/improve-logging
```

### 2. Development Cycle

```bash
# Make changes
jj diff                          # See current changes
jj status                        # Check repository status

# Commit changes (use conventional commits)
jj commit -m "feat: add AWS multi-region support"
jj commit -m "fix: resolve shellcheck warnings"
jj commit -m "docs: update API documentation"

# Push to remote
jj git push --branch feature/multi-cloud-support
```

### 3. Pre-commit Validation

Our pre-commit hooks will automatically run:
```bash
# Manual testing before push
make ci-local                    # Run full CI pipeline locally
./scripts/test-ci-locally.sh     # Alternative CI test

# Pre-push hook runs automatically on jj git push
```

### 4. Code Review Process

```bash
# Open PR: feature/multi-cloud-support → develop
gh pr create --base develop --title "feat: add multi-cloud support" \
  --body "## Summary
- Added AWS multi-region deployment
- Implemented region failover logic
- Updated configuration schema

## Testing
- All 20 tests pass
- Shellcheck validation passes
- Deployed to 3 regions successfully"

# Address review feedback
jj commit -m "fix: address code review feedback"
jj git push
```

### 5. Merge to Integration

```bash
# After PR approval, squash and merge
jj rebase -d develop            # Rebase onto develop
jj git push --branch develop    # Push to develop branch
```

## 📦 Release Process

### 1. Prepare Release Branch

```bash
# Create release branch from develop
jj new develop -m "Prepare release v1.3.0"
jj branch create release/v1.3.0

# Update version information
jj commit -m "chore: bump version to v1.3.0"
jj git push --branch release/v1.3.0
```

### 2. Final Testing & Documentation

```bash
# Run comprehensive tests
make ci-local
make check-all

# Update documentation
jj commit -m "docs: update CHANGELOG for v1.3.0"
jj commit -m "docs: update README with new features"

jj git push
```

### 3. Release to Main

```bash
# Open PR: release/v1.3.0 → main
gh pr create --base main --title "Release v1.3.0" \
  --body "## Release v1.3.0

### New Features
- Multi-cloud support for AWS, GCP, Azure
- Enhanced logging with structured output
- Improved error handling and retries

### Bug Fixes
- Fixed shellcheck warnings
- Resolved CI dependency issues
- Fixed cluster cleanup race conditions

### Documentation
- Updated API documentation
- Added deployment examples
- Improved troubleshooting guide"

# After approval, merge to main
jj new main                     # Switch to main
jj git pull                     # Get latest main

# Create release tag
jj commit --allow-empty -m "Release v1.3.0"
jj tag v1.3.0
jj git push --all-remotes
```

### 4. Automated Release

Our GitHub Actions will automatically:
1. Run full CI pipeline
2. Build and test PyPI package
3. Deploy to PyPI (on version tags)
4. Generate release notes from conventional commits
5. Create GitHub release

## 🔧 Local Development Commands

### Essential Commands

```bash
# Setup development environment
make dev                        # Install deps + pre-commit hooks
uv sync --group dev            # Install dependencies only

# Code Quality (matches CI exactly)
make lint                       # Run ruff linting with fixes
make format                     # Run code formatting
make type-check                 # Run mypy type checking
make security                   # Run bandit security checks
make test                       # Run pytest test suite

# Comprehensive Testing
make ci-local                   # Run FULL CI pipeline locally
make push-ready                 # Alias for ci-local
./scripts/test-ci-locally.sh    # Direct script execution

# GitHub Actions Local Testing (optional)
./scripts/setup-act.sh          # Setup act for local GH Actions
make act-ci                     # Run CI workflow locally with act
```

### Pre-commit & Pre-push Hooks

- **Pre-commit**: Runs linting, formatting, security checks
- **Pre-push**: Runs **complete CI pipeline** before allowing push
- Use `jj git push --no-verify` only in emergencies

## 📋 Conventional Commit Format

We use conventional commits for automatic changelog generation:

```bash
feat: add new feature
fix: bug fix
docs: documentation changes
style: formatting changes
refactor: code refactoring
test: adding tests
chore: maintenance tasks
ci: CI/CD changes
perf: performance improvements
build: build system changes
```

### Examples

```bash
jj commit -m "feat: add multi-region cluster deployment"
jj commit -m "fix: resolve shellcheck warnings in deployment scripts"
jj commit -m "docs: update installation guide with uvx instructions"
jj commit -m "ci: add pre-push hook for comprehensive testing"
jj commit -m "perf: optimize cluster status checking with parallel queries"
```

## 🚨 Emergency Hotfixes

For critical production issues:

```bash
# Create hotfix from main
jj new main -m "Hotfix: critical security patch"
jj branch create hotfix/security-patch

# Make minimal fix
jj commit -m "fix: patch critical security vulnerability"

# Test thoroughly
make ci-local

# Direct PR to main (bypass develop)
jj git push --branch hotfix/security-patch
gh pr create --base main --title "HOTFIX: Critical Security Patch"

# After merge, also merge back to develop
jj new develop
jj git pull
jj merge main                   # Merge hotfix to develop
```

## 🔍 Debugging & Troubleshooting

### Common Jujutsu Operations

```bash
# View commit history
jj log                          # Beautiful commit graph
jj log --oneline               # Compact view

# Undo last commit
jj undo                        # Undo last operation

# Interactive rebase
jj rebase -i                   # Interactive rebase current branch

# View branches
jj branch list                 # List all branches
jj branch delete old-feature   # Delete branch

# Sync with remote
jj git fetch                   # Fetch from remote
jj git import                  # Import git changes to jj
```

### CI/CD Troubleshooting

```bash
# If CI fails, debug locally first
make ci-local                  # Run identical checks locally

# Check specific components
make lint                      # Just linting
make test                      # Just tests
make type-check                # Just type checking

# Check shell scripts
shellcheck cluster-deploy scripts/*.sh

# Validate pyproject.toml
uv check                       # Validate project configuration
```

## 📈 Release Automation

### Version Bumping

Our releases are automated based on conventional commits:
- `feat:` → Minor version bump (1.2.0 → 1.3.0)
- `fix:` → Patch version bump (1.2.0 → 1.2.1)
- `feat!:` or `BREAKING CHANGE:` → Major version bump (1.2.0 → 2.0.0)

### PyPI Deployment

Automatic deployment happens on version tags:
1. **TestPyPI**: On push to `develop` branch
2. **PyPI**: On version tags (v1.2.3) to `main`

Users can install with:
```bash
uvx run spot-deployer create    # Latest from PyPI
pip install spot-deployer       # Traditional pip install
```

## 🎯 Quality Standards

Before any merge:
- ✅ All 20+ tests pass
- ✅ Shellcheck passes on all scripts
- ✅ Ruff linting with zero warnings
- ✅ MyPy type checking passes
- ✅ Bandit security scanning passes
- ✅ Local CI pipeline passes completely
- ✅ Pre-commit hooks installed and passing

**Remember**: Our pre-push hook prevents broken code from reaching GitHub by running the complete CI pipeline locally first.
