# CI Troubleshooting Checklist

## Before Pushing to CI

Run these commands locally:

```bash
# 1. Test the Docker build
./test-docker-build.sh

# 2. If that fails, check file permissions
ls -la docker-entrypoint.sh
ls -la spot_deployer/__init__.py

# 3. Try the simple Dockerfile
docker build -f Dockerfile.simple -t spot-test:simple .
docker run --rm spot-test:simple help
```

## Common CI Failures

### 1. "exec /usr/local/bin/docker-entrypoint.sh: no such file or directory"

**Cause**: Line ending issues (CRLF vs LF)

**Fix**:
```bash
# Convert to Unix line endings
dos2unix docker-entrypoint.sh
# OR
sed -i 's/\r$//' docker-entrypoint.sh
```

### 2. "ModuleNotFoundError: No module named 'spot_deployer'"

**Cause**: Python path issues

**Fix**: Already added `ENV PYTHONPATH=/app` to Dockerfile

### 3. "permission denied"

**Cause**: Script not executable

**Fix**: Already added multiple `chmod +x` commands

### 4. Multi-arch build fails

**Cause**: Missing QEMU setup

**Fix**: Already added `docker/setup-qemu-action@v3`

### 5. Push fails with "unauthorized"

**Cause**: Wrong image name or permissions

**Fix**: Using `${{ github.repository }}` which automatically uses the correct name

## What Changed

1. **Simplified Dockerfile**: Removed multi-stage build complexity
2. **Fixed Python imports**: Added `PYTHONPATH=/app`
3. **Simplified entrypoint**: Using `python -m` instead of `uv run`
4. **Better error handling**: Clear messages for missing credentials/config
5. **Simplified CI workflow**: Removed vulnerability scanning for now
6. **Fixed image naming**: Using repository name directly

## Next Steps

1. Commit these changes:
   ```bash
   git add .
   git commit -m "Fix Docker build issues for CI"
   git push origin main
   ```

2. Watch the GitHub Actions run

3. If it still fails, check the specific error in the logs

4. The image name will be:
   ```
   ghcr.io/bacalhau-project/aws-spot-deployer:latest
   ```

## Testing After Successful Build

```bash
# Pull the image
docker pull ghcr.io/bacalhau-project/aws-spot-deployer:latest

# Test help
docker run --rm ghcr.io/bacalhau-project/aws-spot-deployer:latest help

# Test setup
docker run --rm -v $(pwd):/app/output ghcr.io/bacalhau-project/aws-spot-deployer:latest setup
```