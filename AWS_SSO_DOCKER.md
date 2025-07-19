# Using AWS SSO with Docker

## The Challenge

AWS SSO stores credentials in a different location and format than traditional AWS credentials. When you run `aws sso login`, it creates session credentials in `~/.aws/sso/cache/` that need to be accessible to the Docker container.

## Solution 1: Mount the Entire AWS Directory (Recommended)

```bash
# After logging in with SSO
aws sso login

# Mount your entire .aws directory
docker run --rm \
  -v ~/.aws:/root/.aws:ro \
  -v $(pwd)/config.yaml:/app/config/config.yaml:ro \
  ghcr.io/bacalhau-project/spot-deployer:latest list
```

## Solution 2: Export Temporary Credentials

```bash
# Get temporary credentials from SSO
eval $(aws configure export-credentials --format env)

# Use environment variables
docker run --rm \
  -e AWS_ACCESS_KEY_ID \
  -e AWS_SECRET_ACCESS_KEY \
  -e AWS_SESSION_TOKEN \
  -e AWS_DEFAULT_REGION \
  -v $(pwd)/config.yaml:/app/config/config.yaml:ro \
  ghcr.io/bacalhau-project/spot-deployer:latest list
```

## Solution 3: Use AWS SSO Helper Script

Create a helper script `spot-sso`:

```bash
#!/bin/bash
# spot-sso - Helper for using spot-deployer with AWS SSO

# Ensure SSO is logged in
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo "Please run 'aws sso login' first"
    exit 1
fi

# Export credentials
eval $(aws configure export-credentials --format env)

# Run docker with credentials
docker run --rm \
  -e AWS_ACCESS_KEY_ID \
  -e AWS_SECRET_ACCESS_KEY \
  -e AWS_SESSION_TOKEN \
  -e AWS_DEFAULT_REGION \
  -v $(pwd)/config.yaml:/app/config/config.yaml:ro \
  -v $(pwd)/files:/app/files:ro \
  ghcr.io/bacalhau-project/spot-deployer:latest "$@"
```

Then use:
```bash
chmod +x spot-sso
./spot-sso create
./spot-sso list
./spot-sso destroy
```

## Solution 4: Update the Wrapper Script

Update `spot-docker` to handle SSO:

```bash
# Check if using SSO
if [ -d "$HOME/.aws/sso" ] && aws sts get-caller-identity > /dev/null 2>&1; then
    # Export SSO credentials
    eval $(aws configure export-credentials --format env)
    ENV_VARS="$ENV_VARS -e AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY -e AWS_SESSION_TOKEN"
fi
```

## Testing SSO Works

1. **Login with SSO**:
   ```bash
   aws sso login
   aws sts get-caller-identity  # Verify it works
   ```

2. **Test with Docker**:
   ```bash
   # Should work if mounting ~/.aws
   docker run --rm \
     -v ~/.aws:/root/.aws:ro \
     -v $(pwd)/config.yaml:/app/config/config.yaml:ro \
     ghcr.io/bacalhau-project/spot-deployer:latest list
   ```

## Troubleshooting

### "No credentials found"
- Make sure you've run `aws sso login` recently
- SSO sessions expire, re-login if needed
- Check that ~/.aws/config has your SSO configuration

### "Invalid security token"
- Your SSO session has expired
- Run `aws sso login` again

### Docker can't find credentials
- Make sure you're mounting the entire `~/.aws` directory
- Use `:ro` for read-only access
- Check file permissions on ~/.aws/sso/cache/

## AWS Config Example

Your `~/.aws/config` should look like:

```ini
[default]
sso_start_url = https://your-org.awsapps.com/start
sso_region = us-east-1
sso_account_id = 123456789012
sso_role_name = YourRoleName
region = us-west-2
output = json
```

## Best Practices

1. **Always use read-only mounts**: `-v ~/.aws:/root/.aws:ro`
2. **Re-login before long operations**: SSO tokens expire
3. **Use the wrapper script**: It handles credential export automatically
4. **Test locally first**: Ensure AWS CLI works before trying Docker