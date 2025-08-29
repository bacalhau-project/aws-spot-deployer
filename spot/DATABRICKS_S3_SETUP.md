# Databricks S3 Integration Setup Guide

This guide explains how AWS credentials are deployed and configured for Databricks S3 bucket access in the Spot Deployer.

## Overview

The deployment automatically configures AWS credentials on each EC2 instance to enable:
- **Sensor data upload** to Databricks S3 buckets
- **Bacalhau job access** to S3 storage
- **Data export** functionality for analytics

## AWS Credential Files

### Required Credential Files

Place these files in `deployment/etc/aws/credentials/` before deployment:

1. **`expanso-s3-credentials`** - AWS access keys for S3 access
   ```ini
   [default]
   aws_access_key_id = YOUR_ACCESS_KEY_ID
   aws_secret_access_key = YOUR_SECRET_ACCESS_KEY
   region = us-west-2
   ```

2. **`expanso-s3-config.json`** - S3 bucket configuration
   ```json
   {
     "aws_access_key_id": "YOUR_ACCESS_KEY_ID",
     "aws_secret_access_key": "YOUR_SECRET_ACCESS_KEY",
     "region": "us-west-2",
     "s3_configuration": {
       "buckets": {
         "raw": "expanso-databricks-raw-us-west-2",
         "schematized": "expanso-databricks-schematized-us-west-2",
         "filtered": "expanso-databricks-filtered-us-west-2",
         "emergency": "expanso-databricks-emergency-us-west-2"
       }
     }
   }
   ```

3. **`expanso-production.env`** - Environment variables for containers
   ```bash
   AWS_ACCESS_KEY_ID=YOUR_ACCESS_KEY_ID
   AWS_SECRET_ACCESS_KEY=YOUR_SECRET_ACCESS_KEY
   AWS_DEFAULT_REGION=us-west-2
   S3_BUCKET_RAW=expanso-databricks-raw-us-west-2
   S3_BUCKET_SCHEMATIZED=expanso-databricks-schematized-us-west-2
   S3_BUCKET_FILTERED=expanso-databricks-filtered-us-west-2
   S3_BUCKET_EMERGENCY=expanso-databricks-emergency-us-west-2
   ```

## Deployment Process

### 1. Credential Deployment Flow

When instances are created, the deployment process:

1. **Uploads credential files** from `deployment/etc/aws/credentials/` to `/opt/deployment/etc/aws/credentials/`
2. **Runs setup script** (`setup-aws-credentials.sh`) which:
   - Copies credentials to `/root/.aws/credentials` and `/home/ubuntu/.aws/credentials`
   - Sets proper file permissions (600)
   - Copies S3 configuration to `/opt/sensor/config/`
   - Sets up environment variables in `/opt/sensor/.env`
   - Verifies AWS access with `aws sts get-caller-identity`
   - Tests S3 bucket access

3. **Docker containers** receive credentials via:
   - Volume mounts: `/root/.aws:/root/.aws:ro`
   - Environment file: `env_file: ./docker.env`
   - Environment variables: `AWS_SHARED_CREDENTIALS_FILE`, `AWS_CONFIG_FILE`

### 2. File Locations on Instances

After deployment, credentials are available at:

```
/root/.aws/credentials                          # Root user AWS credentials
/home/ubuntu/.aws/credentials                   # Ubuntu user AWS credentials
/opt/sensor/config/s3-config.json              # S3 bucket configuration
/opt/sensor/config/databricks-storage-config.yaml  # Databricks storage config
/opt/sensor/.env                               # Environment variables
/opt/sensor/docker.env                          # Docker environment file
```

### 3. Docker Container Access

Both sensor and Bacalhau containers have AWS access through:

#### Sensor Container (`sensor-simulators`)
```yaml
environment:
  - AWS_SHARED_CREDENTIALS_FILE=/root/.aws/credentials
  - AWS_CONFIG_FILE=/root/.aws/config
env_file:
  - ./docker.env
volumes:
  - /root/.aws:/root/.aws:ro
  - /home/ubuntu/.aws:/home/app/.aws:ro
```

#### Bacalhau Container (`compute`)
```yaml
volumes:
  - /root/.aws:/root/.aws:ro
  - /home/ubuntu/.aws:/home/bacalhau/.aws:ro
  - /opt/sensor/exports:/opt/sensor/exports:ro
```

## S3 Bucket Structure

The Databricks integration uses four S3 buckets:

1. **Raw Data**: `expanso-databricks-raw-us-west-2`
   - Unprocessed sensor data
   - Direct uploads from sensor nodes

2. **Schematized Data**: `expanso-databricks-schematized-us-west-2`
   - Structured data with defined schema
   - Ready for analytics processing

3. **Filtered Data**: `expanso-databricks-filtered-us-west-2`
   - Processed and filtered datasets
   - Optimized for specific queries

4. **Emergency Data**: `expanso-databricks-emergency-us-west-2`
   - Critical alerts and anomalies
   - High-priority data for immediate action

## Security Considerations

### IAM Permissions Required

The AWS credentials need the following permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:ListBucket",
        "s3:DeleteObject",
        "s3:GetBucketLocation"
      ],
      "Resource": [
        "arn:aws:s3:::expanso-databricks-*",
        "arn:aws:s3:::expanso-databricks-*/*"
      ]
    }
  ]
}
```

### Best Practices

1. **Never commit credentials** - All credential files are in `.gitignore`
2. **Use IAM roles when possible** - Consider EC2 instance profiles for production
3. **Rotate credentials regularly** - Update credentials periodically
4. **Limit permissions** - Use minimal required S3 permissions
5. **Monitor access** - Enable CloudTrail logging for S3 access

## Verification

### Check Credential Deployment

SSH into an instance and verify:

```bash
# Check AWS credentials
aws sts get-caller-identity

# Test S3 access
aws s3 ls s3://expanso-databricks-raw-us-west-2/

# Check container environment
docker exec sensor-simulators-1 env | grep AWS

# Verify mounted credentials in container
docker exec sensor-simulators-1 ls -la /root/.aws/
```

### Troubleshooting

If credentials are not working:

1. **Check file permissions**:
   ```bash
   ls -la /root/.aws/credentials
   # Should be: -rw------- (600)
   ```

2. **Verify credential content**:
   ```bash
   cat /root/.aws/credentials
   # Should contain [default] section with keys
   ```

3. **Test from container**:
   ```bash
   docker exec sensor-simulators-1 aws s3 ls
   ```

4. **Check logs**:
   ```bash
   grep "AWS" /opt/deployment.log
   docker logs sensor-simulators-1 | grep -i s3
   ```

## Updates and Maintenance

To update AWS credentials:

1. Update files in `deployment/etc/aws/credentials/`
2. Destroy existing instances: `./spot-dev.sh destroy`
3. Deploy new instances: `./spot-dev.sh create`

The new instances will automatically receive the updated credentials.

## Alternative: Using IAM Instance Profiles

For production deployments, consider using IAM instance profiles instead of static credentials:

1. Create an IAM role with S3 permissions
2. Attach the role to EC2 instances during creation
3. Remove credential files from deployment
4. Containers will automatically use instance profile credentials

This approach eliminates the need to manage and rotate access keys.
