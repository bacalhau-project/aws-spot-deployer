# SkyPilot Multi-Region Deployment Examples

SkyPilot supports several approaches for multi-region deployment. Here are the main strategies:

## Approach 1: Single Cluster with Zone Flexibility

Let SkyPilot automatically select the best availability zone within a region:

```yaml
name: bacalhau-sensors
num_nodes: 6

resources:
  cloud: aws
  region: us-west-2  # SkyPilot will distribute across zones automatically
  instance_type: t3.medium
  use_spot: true
  disk_size: 30
```

## Approach 2: Multiple Separate Deployments

Deploy separate clusters in different regions using a wrapper script:

### bacalhau-us-west.yaml
```yaml
name: bacalhau-sensors-west
num_nodes: 2

resources:
  cloud: aws
  region: us-west-2
  instance_type: t3.medium
  use_spot: true
  disk_size: 30

# ... rest of config identical
```

### bacalhau-us-east.yaml
```yaml
name: bacalhau-sensors-east
num_nodes: 2

resources:
  cloud: aws
  region: us-east-1
  instance_type: t3.medium
  use_spot: true
  disk_size: 30

# ... rest of config identical
```

### bacalhau-eu-west.yaml
```yaml
name: bacalhau-sensors-eu
num_nodes: 2

resources:
  cloud: aws
  region: eu-west-1
  instance_type: t3.medium
  use_spot: true
  disk_size: 30

# ... rest of config identical
```

## Approach 3: Infrastructure Specification (Recommended)

Use the newer `infra` field for more flexible region targeting:

```yaml
name: bacalhau-sensors
num_nodes: 6

resources:
  # Let SkyPilot choose the best AWS region
  infra: aws
  # Or specify: infra: aws/us-west-2  for specific region
  # Or specify: infra: aws/us-west-2/us-west-2a  for specific zone

  instance_type: t3.medium
  use_spot: true
  disk_size: 30
```

## Approach 4: Multi-Region Deployment Script

Create a deployment script that manages multiple regions:

```bash
#!/bin/bash
# multi-region-deploy.sh

REGIONS=("us-west-2" "us-east-1" "eu-west-1")
NODES_PER_REGION=2

for region in "${REGIONS[@]}"; do
    echo "Deploying to $region..."

    # Create region-specific config
    sed "s/REGION_PLACEHOLDER/$region/g; s/NODES_PLACEHOLDER/$NODES_PER_REGION/g" \
        bacalhau-template.yaml > bacalhau-$region.yaml

    # Launch cluster
    sky launch -c bacalhau-sensors-$region bacalhau-$region.yaml

    echo "Deployed to $region successfully"
done
```

### bacalhau-template.yaml
```yaml
name: bacalhau-sensors-REGION_PLACEHOLDER
num_nodes: NODES_PLACEHOLDER

resources:
  cloud: aws
  region: REGION_PLACEHOLDER
  instance_type: t3.medium
  use_spot: true
  disk_size: 30

# ... rest of config
```

## Recommendation

For your use case, I recommend **Approach 1** initially (single region with zone flexibility) for simplicity, then **Approach 4** (multi-region script) for production scale.

The single region approach will distribute your 6 nodes across availability zones automatically, providing good fault tolerance within the region.
