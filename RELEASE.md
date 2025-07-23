# Release Process

This document describes the release process for spot-deployer.

## Version Management

The version is automatically derived from git tags. When on a tagged release, it uses the tag version. Otherwise, it generates a development version as `previousTag-YYYYMMDD`.

## Release Steps

1. **Update Changelog**
   - Document all changes in CHANGELOG.md
   - Include breaking changes, new features, bug fixes

2. **Test Locally**
   ```bash
   # Test Docker build
   docker build -t spot-test:local .
   docker run --rm spot-test:local help

   # Lint check
   uv run ruff check .
   ```

3. **Commit Changes**
   ```bash
   git add CHANGELOG.md
   git commit -m "Update changelog for v1.0.0"
   git push origin main
   ```

4. **Create Tag and Push**

   **Option 1: Use GitHub Actions**
   - Go to Actions → Create Version Tag → Run workflow
   - Enter version number (e.g., 1.0.0)

   **Option 2: Create tag locally**
   ```bash
   # Create annotated tag
   git tag -a v1.0.0 -m "Release version 1.0.0"

   # Push tag
   git push origin v1.0.0
   ```

5. **Monitor Release**
   - Go to GitHub Actions to monitor the release workflow
   - The workflow will:
     - Build multi-architecture Docker images (amd64, arm64)
     - Push images to GitHub Container Registry
     - Create a GitHub release

## Docker Images

The release process creates Docker images with the following tags:

- `ghcr.io/daaronch/spot:latest` - Latest stable version
- `ghcr.io/daaronch/spot:1.0.0` - Specific version
- `ghcr.io/daaronch/spot:1.0` - Major.minor version
- `ghcr.io/daaronch/spot:1` - Major version only

## Using Released Images

```bash
# Pull the latest version
docker pull ghcr.io/daaronch/spot:latest

# Run with local config
docker run -it --rm \
  -v $(pwd)/config.yaml:/app/config/config.yaml \
  -v $(pwd)/files:/app/files \
  -v ~/.aws:/root/.aws:ro \
  -e BACALHAU_API_HOST=$BACALHAU_API_HOST \
  -e BACALHAU_API_KEY=$BACALHAU_API_KEY \
  ghcr.io/daaronch/spot:latest create

# Or use the spot-dev wrapper script
./spot-dev create
```

## Post-Release

1. **Verify Release**
   - Check GitHub releases page
   - Pull and test Docker images:
     ```bash
     docker pull ghcr.io/daaronch/spot:latest
     docker run --rm ghcr.io/daaronch/spot:latest --version
     ```

2. **Update Documentation**
   - Update README with new version info if needed
   - Update any version-specific documentation

## Troubleshooting

- If the release workflow fails, check the GitHub Actions logs
- For Docker build issues, test locally with `docker build -t test .`
- Ensure Docker Hub / GHCR authentication is properly configured in repository settings
