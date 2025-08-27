# 🌍 Global Zone Coverage

When you deploy with `./sky-deploy deploy`, SkyPilot automatically distributes your 9 nodes across zones worldwide for maximum geographic coverage.

## Typical Global Distribution

Your nodes will be spread across zones like these:

### 🇺🇸 **North America (3-4 nodes)**
- **us-west-2a** - Oregon (US West Coast)
- **us-east-1a** - Virginia (US East Coast)
- **ca-central-1a** - Canada Central

### 🇪🇺 **Europe (2-3 nodes)**
- **eu-west-1a** - Ireland (Western Europe)
- **eu-central-1a** - Frankfurt (Central Europe)

### 🌏 **Asia Pacific (2-3 nodes)**
- **ap-south-1a** - Mumbai (India)
- **ap-southeast-2a** - Sydney (Australia)
- **ap-northeast-1a** - Tokyo (Japan)

### 🇧🇷 **South America (1 node)**
- **sa-east-1a** - São Paulo (Brazil)

## Benefits of Global Distribution

✅ **Maximum fault tolerance** - No single region failure affects the entire network
✅ **Low latency worldwide** - Nodes close to users everywhere
✅ **Spot price optimization** - SkyPilot finds cheapest zones automatically
✅ **Regulatory compliance** - Data stays in appropriate regions
✅ **Automatic failover** - If one zone fails, others continue running

## Customizing Zone Selection

If you need specific zones, you can modify `bacalhau-cluster.yaml`:

```yaml
# Use any AWS region (default - recommended)
infra: aws

# Use specific region
infra: aws/us-west-2

# Use specific zone
infra: aws/us-west-2/us-west-2a

# Use any zone in a specific region
infra: aws/us-west-2/*
```

But for most use cases, `infra: aws` gives you the best global coverage automatically!
