# Credentials Directory

This directory contains credential files that are NOT committed to git.
You must create these files before deploying.

## Required Files

### orchestrator_endpoint
Contains the Bacalhau orchestrator NATS endpoint URL.
Example:
```
nats://your-orchestrator.example.com:4222
```

### orchestrator_token
Contains the authentication token for the orchestrator.
Example:
```
your-secret-token-here
```

### aws-credentials
Contains AWS credentials in standard format for S3 access.
Example:
```
[default]
aws_access_key_id = YOUR_ACCESS_KEY
aws_secret_access_key = YOUR_SECRET_KEY
region = us-west-2
```

## Creating Credential Files

```bash
# Create orchestrator endpoint
echo "nats://your-orchestrator.example.com:4222" > credentials/orchestrator_endpoint

# Create orchestrator token
echo "your-secret-token-here" > credentials/orchestrator_token

# Create AWS credentials
cat > credentials/aws-credentials << EOF
[default]
aws_access_key_id = YOUR_ACCESS_KEY
aws_secret_access_key = YOUR_SECRET_KEY
region = us-west-2
EOF
```

## Security Note

These files contain sensitive information and should never be committed to version control.
The `.gitignore` file excludes them from git automatically.
