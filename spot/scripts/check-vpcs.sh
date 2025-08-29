#!/bin/bash
# Quick script to check default VPCs across all AWS regions

set -e

echo "🔍 Checking Default VPCs in All AWS Regions"
echo "==========================================="
echo

# Get all regions
REGIONS=$(aws ec2 describe-regions --query "Regions[].RegionName" --output text 2>/dev/null)

if [ -z "$REGIONS" ]; then
    echo "❌ Error: Could not fetch AWS regions. Check your AWS credentials."
    exit 1
fi

# Count total regions
TOTAL_REGIONS=$(echo "$REGIONS" | wc -w | tr -d ' ')
echo "Found $TOTAL_REGIONS AWS regions to check"
echo

# Initialize counters
WITH_DEFAULT=0
WITHOUT_DEFAULT=0
REGIONS_WITHOUT=""

# Table header
printf "%-20s %-25s %-18s %-10s %s\n" "REGION" "VPC ID" "CIDR" "SUBNETS" "STATUS"
printf "%-20s %-25s %-18s %-10s %s\n" "------" "------" "----" "-------" "------"

# Check each region
for REGION in $REGIONS; do
    # Check for default VPC
    VPC_INFO=$(aws ec2 describe-vpcs \
        --region "$REGION" \
        --filters "Name=is-default,Values=true" \
        --query "Vpcs[0].[VpcId,CidrBlock]" \
        --output text 2>/dev/null || echo "ERROR")

    if [ "$VPC_INFO" = "ERROR" ]; then
        printf "%-20s %-25s %-18s %-10s %s\n" "$REGION" "-" "-" "-" "⚠️  Error"
        continue
    fi

    if [ -n "$VPC_INFO" ] && [ "$VPC_INFO" != "None" ]; then
        VPC_ID=$(echo "$VPC_INFO" | awk '{print $1}')
        CIDR=$(echo "$VPC_INFO" | awk '{print $2}')

        # Get subnet count
        SUBNET_COUNT=$(aws ec2 describe-subnets \
            --region "$REGION" \
            --filters "Name=vpc-id,Values=$VPC_ID" \
            --query "Subnets | length(@)" \
            --output text 2>/dev/null || echo "?")

        printf "%-20s %-25s %-18s %-10s %s\n" "$REGION" "$VPC_ID" "$CIDR" "$SUBNET_COUNT" "✅ Default"
        ((WITH_DEFAULT++))
    else
        # Check if region has any VPCs
        VPC_COUNT=$(aws ec2 describe-vpcs \
            --region "$REGION" \
            --query "Vpcs | length(@)" \
            --output text 2>/dev/null || echo "0")

        printf "%-20s %-25s %-18s %-10s %s\n" "$REGION" "-" "-" "-" "❌ No default ($VPC_COUNT custom)"
        ((WITHOUT_DEFAULT++))
        REGIONS_WITHOUT="$REGIONS_WITHOUT $REGION"
    fi
done

# Summary
echo
echo "==========================================="
echo "SUMMARY"
echo "==========================================="
echo "✅ Regions with default VPC: $WITH_DEFAULT"
echo "❌ Regions without default VPC: $WITHOUT_DEFAULT"
echo "Total regions checked: $TOTAL_REGIONS"

# Show regions without default VPCs
if [ $WITHOUT_DEFAULT -gt 0 ]; then
    echo
    echo "⚠️  Regions without default VPCs:"
    for REGION in $REGIONS_WITHOUT; do
        echo "  - $REGION"
    done

    echo
    echo "To create default VPCs, run:"
    for REGION in $REGIONS_WITHOUT; do
        echo "  aws ec2 create-default-vpc --region $REGION"
    done | head -3

    echo
    echo "Or add to config.yaml:"
    echo "  aws:"
    echo "    use_dedicated_vpc: true"
fi

# Recommend good regions
echo
echo "✅ Recommended regions with default VPCs:"
RECOMMENDED="us-west-2 us-east-2 eu-central-1 ap-southeast-1 eu-west-2"
for REC_REGION in $RECOMMENDED; do
    if echo "$REGIONS" | grep -q "$REC_REGION"; then
        VPC_ID=$(aws ec2 describe-vpcs \
            --region "$REC_REGION" \
            --filters "Name=is-default,Values=true" \
            --query "Vpcs[0].VpcId" \
            --output text 2>/dev/null || echo "")

        if [ -n "$VPC_ID" ] && [ "$VPC_ID" != "None" ]; then
            echo "  • $REC_REGION - $VPC_ID"
        fi
    fi
done
