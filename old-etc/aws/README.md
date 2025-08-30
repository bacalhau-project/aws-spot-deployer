# AWS Credentials Configuration

To provide S3 access to Bacalhau nodes, create a `credentials` file in this directory with your AWS credentials.

## Setup

1. Copy the example file:
   ```bash
   cp credentials.example credentials
   ```

2. Edit `credentials` and add your AWS access keys:
   ```ini
   [default]
   aws_access_key_id = YOUR_ACCESS_KEY_ID
   aws_secret_access_key = YOUR_SECRET_ACCESS_KEY
   region = us-west-2
   ```

3. The credentials will be automatically deployed to `/root/.aws/credentials` on each node

## Security Notes

- Never commit the `credentials` file to git (it's in .gitignore)
- Use IAM roles with minimal required permissions
- Consider using temporary credentials or STS tokens for better security

## Required Permissions

The AWS credentials should have at least:
- `s3:PutObject` - To upload data
- `s3:GetObject` - To read data
- `s3:ListBucket` - To list bucket contents

Example IAM policy:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::your-bucket-name",
        "arn:aws:s3:::your-bucket-name/*"
      ]
    }
  ]
}
```
