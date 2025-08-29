# VPC Configuration Guide for Multi-Region Deployments

## Problem
Some AWS regions may not have default VPCs, causing deployment failures with the error:
```
ERROR: No default VPC found
```

This commonly occurs in:
- **eu-west-1** (Ireland)
- **us-east-1** (N. Virginia)
- Other regions where default VPCs were deleted

## Solutions

### Option 1: Use Dedicated VPCs (Recommended)

Add this to your `config.yaml`:

```yaml
aws:
  use_dedicated_vpc: true  # Creates dedicated VPC for each deployment
```

**Advantages:**
- ✅ Works in all regions automatically
- ✅ Better security isolation
- ✅ Consistent network configuration
- ✅ Easy cleanup (VPC deleted with instances)

**How it works:**
- Creates a new VPC with CIDR `10.0.0.0/16` in each region
- Sets up Internet Gateway for public access
- Creates public subnet with auto-assign public IP
- Configures route tables for internet connectivity

### Option 2: Create Default VPCs Manually

If you prefer using default VPCs, create them using AWS CLI:

```bash
# For eu-west-1
aws ec2 create-default-vpc --region eu-west-1

# For us-east-1
aws ec2 create-default-vpc --region us-east-1
```

### Option 3: Specify Existing VPCs

If you have existing VPCs, specify them in `config.yaml`:

```yaml
regions:
  - us-west-2:
      machine_type: t3.medium
      image: auto
      vpc_id: vpc-12345678        # Optional: specific VPC
      subnet_id: subnet-87654321   # Optional: specific subnet

  - us-east-1:
      machine_type: t3.medium
      image: auto
      vpc_id: vpc-abcdef12
      subnet_id: subnet-fedcba21

  - eu-west-1:
      machine_type: t3.medium
      image: auto
      vpc_id: vpc-11223344
      subnet_id: subnet-44332211
```

## Region-Specific Considerations

### Optimal Regions for Spot Instances

Based on availability and pricing, these regions typically work well:

1. **us-west-2** (Oregon) - Usually has default VPC
   - Good spot availability
   - Lower prices
   - Multiple availability zones

2. **us-east-2** (Ohio) - Usually has default VPC
   - Excellent spot capacity
   - Competitive pricing
   - Less congested than us-east-1

3. **eu-central-1** (Frankfurt) - Usually has default VPC
   - Good for European deployments
   - Stable spot pricing

4. **ap-southeast-1** (Singapore) - Usually has default VPC
   - Good for Asia-Pacific region
   - Decent spot availability

### Regions That May Need Configuration

These regions often lack default VPCs:

- **us-east-1** (N. Virginia) - Oldest region, default VPCs often deleted
- **eu-west-1** (Ireland) - Another old region with similar issues
- **ap-northeast-1** (Tokyo) - May lack defaults in older accounts

## Best Practices

### 1. For Development/Testing
Use dedicated VPCs for isolation:
```yaml
aws:
  use_dedicated_vpc: true
```

### 2. For Production
Specify existing VPCs with proper configuration:
```yaml
regions:
  - us-west-2:
      vpc_id: vpc-prod-west
      subnet_id: subnet-prod-public-2a
```

### 3. For Cost Optimization
Stick to regions with good spot availability:
```yaml
regions:
  - us-west-2:    # Oregon - reliable
      machine_type: t3.medium
      image: auto

  - us-east-2:    # Ohio - good capacity
      machine_type: t3.medium
      image: auto

  - eu-central-1: # Frankfurt - stable
      machine_type: t3.medium
      image: auto
```

## Troubleshooting

### Check VPC Status in a Region

```bash
# List all VPCs in a region
aws ec2 describe-vpcs --region eu-west-1

# Check for default VPC
aws ec2 describe-vpcs --region eu-west-1 --filters "Name=is-default,Values=true"
```

### Create Missing Default VPC

```bash
# Create default VPC (if allowed by AWS)
aws ec2 create-default-vpc --region eu-west-1

# If that fails, use dedicated VPCs in config
echo "use_dedicated_vpc: true" >> config.yaml
```

### Clean Up Dedicated VPCs

When using `use_dedicated_vpc: true`, VPCs are automatically deleted when you run:
```bash
./spot-dev.sh destroy
```

To manually clean up orphaned VPCs:
```bash
uv run delete_vpcs.py --dry-run  # Preview
uv run delete_vpcs.py            # Execute cleanup
```

## Recommended Configuration

For most users, this configuration works best:

```yaml
aws:
  total_instances: 6
  use_dedicated_vpc: true  # Avoids VPC issues
  instance_storage_gb: 20
  associate_public_ip: true

regions:
  # Primary regions with good spot capacity
  - us-west-2:     # Oregon
      machine_type: t3.medium
      image: auto

  - us-east-2:     # Ohio (instead of us-east-1)
      machine_type: t3.medium
      image: auto

  - eu-central-1:  # Frankfurt (instead of eu-west-1)
      machine_type: t3.medium
      image: auto
```

This configuration:
- ✅ Avoids regions with VPC issues
- ✅ Uses regions with good spot availability
- ✅ Creates isolated VPCs for security
- ✅ Works out-of-the-box without manual setup
