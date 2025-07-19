# Checking Your Docker Build

## 1. Check GitHub Actions

Go to: https://github.com/bacalhau-project/aws-spot-deployer/actions

You should see:
- A workflow run for the `v1.0.0` tag
- The workflow name: "Build and Publish Docker Image"

## 2. Monitor Build Progress

The workflow will:
1. Check out the code
2. Set up Docker Buildx
3. Log in to GitHub Container Registry
4. Build multi-arch images (amd64 + arm64)
5. Push to ghcr.io
6. Generate SBOM
7. Run security scans

This typically takes 5-10 minutes.

## 3. Verify Published Image

Once the build completes successfully:

```bash
# Pull the versioned image
docker pull ghcr.io/bacalhau-project/spot-deployer:v1.0.0

# Pull the latest tag
docker pull ghcr.io/bacalhau-project/spot-deployer:latest

# Test it works
docker run --rm ghcr.io/bacalhau-project/spot-deployer:v1.0.0 help
```

## 4. Check Package Visibility

Go to: https://github.com/bacalhau-project/aws-spot-deployer/packages

You should see the `spot-deployer` package. You may need to:
1. Click on the package
2. Go to "Package settings"
3. Change visibility to "Public" if you want public access

## 5. Test Full Workflow

```bash
# Create a test directory
mkdir spot-test
cd spot-test

# Create config
docker run --rm -v $(pwd):/app/output ghcr.io/bacalhau-project/spot-deployer:v1.0.0 setup

# View the generated config
cat config.yaml

# Test with your AWS credentials
docker run --rm \
  -v ~/.aws:/root/.aws:ro \
  -v $(pwd)/config.yaml:/app/config/config.yaml:ro \
  ghcr.io/bacalhau-project/spot-deployer:v1.0.0 list
```

## Common Issues

### "Package not found"
- The build might still be running
- The package might be private (check package settings)
- The organization name might be different

### "Unauthorized"
- For private packages, you need to authenticate:
  ```bash
  echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin
  ```

### Build Failed
- Check the Actions tab for error logs
- Common issues:
  - Missing requirements.txt
  - Syntax errors in scripts
  - Docker build context issues

## Next Steps

Once verified:
1. Update any documentation with the correct image name
2. Test the wrapper script:
   ```bash
   curl -O https://raw.githubusercontent.com/bacalhau-project/aws-spot-deployer/main/spot-docker
   chmod +x spot-docker
   ./spot-docker help
   ```
3. Create a release on GitHub with release notes