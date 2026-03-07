#!/bin/bash

# RootTrust Marketplace - Budget Setup Script
# This script sets up AWS Budgets and CloudWatch cost monitoring

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}RootTrust Budget Setup${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo -e "${RED}Error: AWS CLI is not installed${NC}"
    echo "Please install AWS CLI: https://aws.amazon.com/cli/"
    exit 1
fi

# Get AWS Account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo -e "${GREEN}AWS Account ID:${NC} $ACCOUNT_ID"

# Get admin email from parameter or use default
ADMIN_EMAIL=${1:-"admin@roottrust.example.com"}
echo -e "${GREEN}Admin Email:${NC} $ADMIN_EMAIL"
echo ""

# Get stage from parameter or use default
STAGE=${2:-"dev"}
echo -e "${GREEN}Stage:${NC} $STAGE"
echo ""

echo -e "${YELLOW}Creating SNS Topic for cost alerts...${NC}"

# Create SNS Topic
TOPIC_ARN=$(aws sns create-topic \
    --name "RootTrust-Cost-Alerts-${STAGE}" \
    --output text \
    --query 'TopicArn' 2>/dev/null || echo "")

if [ -z "$TOPIC_ARN" ]; then
    # Topic might already exist, try to get it
    TOPIC_ARN=$(aws sns list-topics --query "Topics[?contains(TopicArn, 'RootTrust-Cost-Alerts-${STAGE}')].TopicArn" --output text)
fi

echo -e "${GREEN}SNS Topic ARN:${NC} $TOPIC_ARN"

# Subscribe email to SNS topic
echo -e "${YELLOW}Subscribing email to SNS topic...${NC}"
aws sns subscribe \
    --topic-arn "$TOPIC_ARN" \
    --protocol email \
    --notification-endpoint "$ADMIN_EMAIL" \
    --output text > /dev/null 2>&1 || echo "Subscription may already exist"

echo -e "${GREEN}✓ Email subscription created (check inbox for confirmation)${NC}"
echo ""

echo -e "${YELLOW}Creating budget alerts...${NC}"
echo ""

# Budget 1: Warning at $100
echo -e "${YELLOW}1. Creating Warning Budget ($100)...${NC}"
cat > /tmp/budget-warning.json <<EOF
{
  "BudgetName": "RootTrust-Warning-${STAGE}",
  "BudgetLimit": {
    "Amount": "100",
    "Unit": "USD"
  },
  "TimeUnit": "MONTHLY",
  "BudgetType": "COST"
}
EOF

cat > /tmp/notifications-warning.json <<EOF
[
  {
    "Notification": {
      "NotificationType": "ACTUAL",
      "ComparisonOperator": "GREATER_THAN",
      "Threshold": 100,
      "ThresholdType": "ABSOLUTE_VALUE"
    },
    "Subscribers": [
      {
        "SubscriptionType": "EMAIL",
        "Address": "$ADMIN_EMAIL"
      }
    ]
  }
]
EOF

aws budgets create-budget \
    --account-id "$ACCOUNT_ID" \
    --budget file:///tmp/budget-warning.json \
    --notifications-with-subscribers file:///tmp/notifications-warning.json \
    2>/dev/null || echo "Budget may already exist"

echo -e "${GREEN}✓ Warning budget created${NC}"

# Budget 2: Critical at $200
echo -e "${YELLOW}2. Creating Critical Budget ($200)...${NC}"
cat > /tmp/budget-critical.json <<EOF
{
  "BudgetName": "RootTrust-Critical-${STAGE}",
  "BudgetLimit": {
    "Amount": "200",
    "Unit": "USD"
  },
  "TimeUnit": "MONTHLY",
  "BudgetType": "COST"
}
EOF

cat > /tmp/notifications-critical.json <<EOF
[
  {
    "Notification": {
      "NotificationType": "ACTUAL",
      "ComparisonOperator": "GREATER_THAN",
      "Threshold": 100,
      "ThresholdType": "ABSOLUTE_VALUE"
    },
    "Subscribers": [
      {
        "SubscriptionType": "EMAIL",
        "Address": "$ADMIN_EMAIL"
      }
    ]
  }
]
EOF

aws budgets create-budget \
    --account-id "$ACCOUNT_ID" \
    --budget file:///tmp/budget-critical.json \
    --notifications-with-subscribers file:///tmp/notifications-critical.json \
    2>/dev/null || echo "Budget may already exist"

echo -e "${GREEN}✓ Critical budget created${NC}"

# Budget 3: Maximum at $280
echo -e "${YELLOW}3. Creating Maximum Budget ($280)...${NC}"
cat > /tmp/budget-maximum.json <<EOF
{
  "BudgetName": "RootTrust-Maximum-${STAGE}",
  "BudgetLimit": {
    "Amount": "280",
    "Unit": "USD"
  },
  "TimeUnit": "MONTHLY",
  "BudgetType": "COST"
}
EOF

cat > /tmp/notifications-maximum.json <<EOF
[
  {
    "Notification": {
      "NotificationType": "ACTUAL",
      "ComparisonOperator": "GREATER_THAN",
      "Threshold": 100,
      "ThresholdType": "ABSOLUTE_VALUE"
    },
    "Subscribers": [
      {
        "SubscriptionType": "EMAIL",
        "Address": "$ADMIN_EMAIL"
      }
    ]
  }
]
EOF

aws budgets create-budget \
    --account-id "$ACCOUNT_ID" \
    --budget file:///tmp/budget-maximum.json \
    --notifications-with-subscribers file:///tmp/notifications-maximum.json \
    2>/dev/null || echo "Budget may already exist"

echo -e "${GREEN}✓ Maximum budget created${NC}"

# Budget 4: Main budget with 80% and 90% thresholds
echo -e "${YELLOW}4. Creating Main Budget ($300 with 80% and 90% alerts)...${NC}"
cat > /tmp/budget-main.json <<EOF
{
  "BudgetName": "RootTrust-Main-${STAGE}",
  "BudgetLimit": {
    "Amount": "300",
    "Unit": "USD"
  },
  "TimeUnit": "MONTHLY",
  "BudgetType": "COST"
}
EOF

cat > /tmp/notifications-main.json <<EOF
[
  {
    "Notification": {
      "NotificationType": "ACTUAL",
      "ComparisonOperator": "GREATER_THAN",
      "Threshold": 80,
      "ThresholdType": "PERCENTAGE"
    },
    "Subscribers": [
      {
        "SubscriptionType": "EMAIL",
        "Address": "$ADMIN_EMAIL"
      }
    ]
  },
  {
    "Notification": {
      "NotificationType": "ACTUAL",
      "ComparisonOperator": "GREATER_THAN",
      "Threshold": 90,
      "ThresholdType": "PERCENTAGE"
    },
    "Subscribers": [
      {
        "SubscriptionType": "EMAIL",
        "Address": "$ADMIN_EMAIL"
      }
    ]
  }
]
EOF

aws budgets create-budget \
    --account-id "$ACCOUNT_ID" \
    --budget file:///tmp/budget-main.json \
    --notifications-with-subscribers file:///tmp/notifications-main.json \
    2>/dev/null || echo "Budget may already exist"

echo -e "${GREEN}✓ Main budget created${NC}"
echo ""

# Clean up temp files
rm -f /tmp/budget-*.json /tmp/notifications-*.json

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Budget Setup Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}Budget Alerts Configured:${NC}"
echo "  1. Warning Alert: $100 (absolute)"
echo "  2. Critical Alert: $200 (absolute)"
echo "  3. Maximum Alert: $280 (absolute)"
echo "  4. Main Budget: $300"
echo "     - 80% threshold: $240"
echo "     - 90% threshold: $270"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "  1. Check your email ($ADMIN_EMAIL) to confirm SNS subscription"
echo "  2. Monitor costs in AWS Cost Explorer"
echo "  3. View budgets in AWS Budgets console"
echo "  4. Review COST_OPTIMIZATION.md for cost reduction strategies"
echo ""
echo -e "${GREEN}To view current costs:${NC}"
echo "  aws ce get-cost-and-usage \\"
echo "    --time-period Start=\$(date -d '7 days ago' +%Y-%m-%d),End=\$(date +%Y-%m-%d) \\"
echo "    --granularity DAILY \\"
echo "    --metrics BlendedCost"
echo ""
