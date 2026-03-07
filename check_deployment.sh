#!/bin/bash

echo "🚀 Checking RootTrust Marketplace Deployment Status..."
echo ""

# Check CloudFormation stack status
STACK_STATUS=$(aws cloudformation describe-stacks \
  --stack-name roottrust-marketplace \
  --region us-east-1 \
  --query 'Stacks[0].StackStatus' \
  --output text 2>/dev/null)

if [ -z "$STACK_STATUS" ]; then
  echo "❌ Stack not found or deployment not started yet"
  exit 1
fi

echo "📊 Stack Status: $STACK_STATUS"
echo ""

# Show stack events (last 10)
echo "📝 Recent Events:"
aws cloudformation describe-stack-events \
  --stack-name roottrust-marketplace \
  --region us-east-1 \
  --max-items 10 \
  --query 'StackEvents[*].[Timestamp,ResourceStatus,ResourceType,LogicalResourceId]' \
  --output table

# If deployment is complete, show outputs
if [ "$STACK_STATUS" == "CREATE_COMPLETE" ] || [ "$STACK_STATUS" == "UPDATE_COMPLETE" ]; then
  echo ""
  echo "✅ Deployment Complete!"
  echo ""
  echo "📋 Stack Outputs:"
  aws cloudformation describe-stacks \
    --stack-name roottrust-marketplace \
    --region us-east-1 \
    --query 'Stacks[0].Outputs' \
    --output table
fi
