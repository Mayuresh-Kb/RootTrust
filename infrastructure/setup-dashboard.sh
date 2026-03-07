#!/bin/bash

# RootTrust Marketplace - CloudWatch Dashboard Setup Script
# This script creates a CloudWatch dashboard for cost and performance monitoring

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}RootTrust CloudWatch Dashboard Setup${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo -e "${RED}Error: AWS CLI is not installed${NC}"
    echo "Please install AWS CLI: https://aws.amazon.com/cli/"
    exit 1
fi

# Get stage from parameter or use default
STAGE=${1:-"dev"}
echo -e "${GREEN}Stage:${NC} $STAGE"
echo ""

# Dashboard name
DASHBOARD_NAME="RootTrust-Cost-Monitoring-${STAGE}"

echo -e "${YELLOW}Creating CloudWatch Dashboard: ${DASHBOARD_NAME}${NC}"

# Create the dashboard
aws cloudwatch put-dashboard \
    --dashboard-name "$DASHBOARD_NAME" \
    --dashboard-body file://dashboard-config.json

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ CloudWatch Dashboard created successfully${NC}"
    echo ""
    echo -e "${GREEN}Dashboard URL:${NC}"
    REGION=$(aws configure get region)
    echo "https://console.aws.amazon.com/cloudwatch/home?region=${REGION}#dashboards:name=${DASHBOARD_NAME}"
    echo ""
else
    echo -e "${RED}✗ Failed to create CloudWatch Dashboard${NC}"
    exit 1
fi

echo -e "${YELLOW}Dashboard Widgets:${NC}"
echo "  1. Daily Estimated AWS Charges (with budget thresholds)"
echo "  2. Lambda Performance (invocations, errors, duration)"
echo "  3. DynamoDB Capacity Usage (read/write units)"
echo "  4. API Gateway Requests (total, 4XX, 5XX errors)"
echo "  5. S3 Storage Usage (size and object count)"
echo "  6. Recent Lambda Errors (log insights)"
echo "  7. Bedrock AI Usage (invocations and latency)"
echo "  8. Current Month Estimated Charges (single value)"
echo ""

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Dashboard Setup Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "  1. Open the dashboard URL above"
echo "  2. Customize widgets as needed"
echo "  3. Set up CloudWatch alarms for critical metrics"
echo "  4. Review dashboard daily during development"
echo ""
