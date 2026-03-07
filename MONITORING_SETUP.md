# RootTrust Marketplace - Cost Monitoring Setup

## Overview

This document describes the CloudWatch cost monitoring and AWS Budgets configuration for the RootTrust Marketplace platform. The monitoring system provides multi-tier alerts to ensure the platform stays within the $300 AWS credits budget.

## Budget Alert Structure

### Alert Tiers

The platform implements a 5-tier alert system:

| Alert Level    | Threshold | Amount | Type       | Action Required                       |
| -------------- | --------- | ------ | ---------- | ------------------------------------- |
| **Warning**    | $100      | $100   | Absolute   | Informational - Review cost breakdown |
| **Critical**   | $200      | $200   | Absolute   | Manual review required                |
| **Maximum**    | $280      | $280   | Absolute   | Immediate intervention required       |
| **80% Budget** | 80%       | $240   | Percentage | Monitor daily costs closely           |
| **90% Budget** | 90%       | $270   | Percentage | Urgent review - Enable cost controls  |

### Alert Actions by Tier

#### 1. Warning Alert ($100)

**Trigger**: Monthly costs exceed $100

**Actions**:

- ✉️ Email notification sent to admin
- 📊 Review cost breakdown by service
- 📝 No immediate action required
- ℹ️ Informational only

**What to Check**:

- Review AWS Cost Explorer for service breakdown
- Check Bedrock usage (should be <$10/month with caching)
- Verify DynamoDB is on-demand pricing
- Confirm S3 lifecycle policies are active

#### 2. Critical Alert ($200)

**Trigger**: Monthly costs exceed $200

**Actions**:

- ✉️ Email notification sent to admin
- 🔍 Review all active services
- ⚠️ Consider disabling non-essential features
- 📋 Manual review required

**What to Check**:

- Identify cost spike source in Cost Explorer
- Review Lambda invocation counts
- Check for unexpected Bedrock usage
- Verify no runaway processes
- Consider emergency cost controls (see COST_OPTIMIZATION.md)

**Potential Actions**:

- Disable promotions feature
- Disable limited releases
- Increase Bedrock cache TTL to 7 days
- Reduce EventBridge schedule frequency

#### 3. Maximum Alert ($280)

**Trigger**: Monthly costs exceed $280

**Actions**:

- ✉️ Email notification sent to admin
- 🚨 Immediate manual intervention required
- 🛑 Consider emergency cost controls
- 📖 Review COST_OPTIMIZATION.md emergency procedures

**Emergency Actions**:

1. **Disable Bedrock** (saves $50-80/month)

   ```bash
   aws lambda update-function-configuration \
     --function-name roottrust-ai-verify \
     --environment Variables={BEDROCK_ENABLED=false}
   ```

2. **Disable EventBridge Rules** (saves $5-10/month)

   ```bash
   aws events disable-rule --name roottrust-promotion-expiry
   aws events disable-rule --name roottrust-limited-release-expiry
   ```

3. **Enable API Gateway Caching** (reduces Lambda costs by 80%)
   - Update template.yaml to enable caching
   - Redeploy stack

4. **Contact AWS Support**
   - Request credit extension
   - Explain hackathon usage
   - Request cost optimization review

#### 4. 80% Budget Alert ($240)

**Trigger**: Monthly costs reach 80% of $300 budget

**Actions**:

- ✉️ Email notification sent to admin
- 📈 Monitor daily costs closely
- 🔍 Review Bedrock usage patterns
- ⚙️ Consider increasing cache TTL

**Preventive Measures**:

- Increase verification cache from 24h to 48h
- Increase marketing content cache from 7d to 14d
- Review and optimize Lambda memory settings
- Check for inefficient queries

#### 5. 90% Budget Alert ($270)

**Trigger**: Monthly costs reach 90% of $300 budget

**Actions**:

- ✉️ Email notification sent to admin
- 🚨 Urgent review required
- 🛠️ Consider enabling emergency cost controls
- ⏱️ Reduce EventBridge frequency

**Immediate Actions**:

1. Reduce EventBridge schedules:
   - Promotion expiry: Every 6 hours → Every 12 hours
   - Limited release expiry: Every 30 min → Every 2 hours

2. Increase cache TTL:
   - Verification: 24h → 7 days
   - Marketing: 7d → 30 days

3. Disable non-essential features:
   - Analytics aggregation
   - Bonus tracking
   - Featured placement updates

## Setup Instructions

### Option 1: Deploy via SAM Template (Recommended)

The budget alerts are included in the main SAM template and will be created automatically during deployment:

```bash
# Deploy the complete stack including budgets
sam build
sam deploy --guided

# When prompted, provide:
# - MonthlyBudgetLimit: 300
# - BudgetAlertThreshold: 80
# - SenderEmail: your-email@example.com
```

### Option 2: Manual Setup via Script

Use the provided setup script to create budgets independently:

```bash
# Run the budget setup script
cd infrastructure
./setup-budgets.sh your-email@example.com dev

# The script will:
# 1. Create SNS topic for alerts
# 2. Subscribe your email to the topic
# 3. Create all 4 budget alerts
# 4. Configure notification thresholds
```

### Option 3: Manual Setup via AWS Console

1. **Create SNS Topic**:
   - Go to AWS SNS Console
   - Create topic: `RootTrust-Cost-Alerts-dev`
   - Create email subscription with your admin email
   - Confirm subscription via email

2. **Create Budget Alerts**:
   - Go to AWS Budgets Console
   - Create 4 budgets using the configurations below

#### Budget 1: Warning Alert

```
Name: RootTrust-Warning-dev
Amount: $100
Period: Monthly
Type: Cost budget
Alert: Email when actual costs > $100
```

#### Budget 2: Critical Alert

```
Name: RootTrust-Critical-dev
Amount: $200
Period: Monthly
Type: Cost budget
Alert: Email when actual costs > $200
```

#### Budget 3: Maximum Alert

```
Name: RootTrust-Maximum-dev
Amount: $280
Period: Monthly
Type: Cost budget
Alert: Email when actual costs > $280
```

#### Budget 4: Main Budget

```
Name: RootTrust-Main-dev
Amount: $300
Period: Monthly
Type: Cost budget
Alerts:
  - Email when actual costs > 80% ($240)
  - Email when actual costs > 90% ($270)
```

## Monitoring Daily Costs

### Using AWS CLI

Check daily costs for the last 7 days:

```bash
aws ce get-cost-and-usage \
  --time-period Start=$(date -d '7 days ago' +%Y-%m-%d),End=$(date +%Y-%m-%d) \
  --granularity DAILY \
  --metrics BlendedCost \
  --group-by Type=SERVICE
```

### Using AWS Cost Explorer

1. Go to AWS Cost Explorer Console
2. Select date range (last 7 days)
3. Group by: Service
4. View daily cost breakdown

### Service-Specific Monitoring

#### Monitor Bedrock Usage

```bash
# Get Bedrock invocation count
aws cloudwatch get-metric-statistics \
  --namespace AWS/Bedrock \
  --metric-name Invocations \
  --dimensions Name=ModelId,Value=anthropic.claude-3-haiku-20240307-v1:0 \
  --start-time $(date -u -d '1 day ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 3600 \
  --statistics Sum
```

#### Monitor DynamoDB Usage

```bash
# Get DynamoDB read/write capacity
aws cloudwatch get-metric-statistics \
  --namespace AWS/DynamoDB \
  --metric-name ConsumedReadCapacityUnits \
  --dimensions Name=TableName,Value=RootTrustData-dev \
  --start-time $(date -u -d '1 day ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 3600 \
  --statistics Sum
```

#### Monitor Lambda Invocations

```bash
# Get Lambda invocation count
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --start-time $(date -u -d '1 day ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 3600 \
  --statistics Sum
```

## CloudWatch Dashboard (Optional)

Create a CloudWatch dashboard to visualize costs in real-time:

### Dashboard Configuration

```json
{
  "widgets": [
    {
      "type": "metric",
      "properties": {
        "metrics": [["AWS/Billing", "EstimatedCharges", { "stat": "Maximum" }]],
        "period": 86400,
        "stat": "Maximum",
        "region": "us-east-1",
        "title": "Daily Estimated Charges"
      }
    },
    {
      "type": "metric",
      "properties": {
        "metrics": [
          ["AWS/Lambda", "Invocations", { "stat": "Sum" }],
          ["AWS/DynamoDB", "ConsumedReadCapacityUnits", { "stat": "Sum" }],
          ["AWS/Bedrock", "Invocations", { "stat": "Sum" }]
        ],
        "period": 3600,
        "stat": "Sum",
        "region": "us-east-1",
        "title": "Service Usage"
      }
    }
  ]
}
```

### Create Dashboard via CLI

```bash
# Create CloudWatch dashboard
aws cloudwatch put-dashboard \
  --dashboard-name RootTrust-Cost-Monitoring \
  --dashboard-body file://infrastructure/dashboard-config.json
```

## Cost Anomaly Detection

AWS Cost Anomaly Detection can automatically detect unusual spending patterns:

### Enable Cost Anomaly Detection

1. Go to AWS Cost Anomaly Detection Console
2. Create monitor:
   - Name: `RootTrust-Anomaly-Monitor`
   - Monitor type: AWS Services
   - Alert threshold: 50% increase
3. Create subscription:
   - Frequency: Daily
   - Recipients: Your admin email

### Benefits

- Automatic detection of cost spikes
- Daily summary emails
- Root cause analysis
- Historical anomaly tracking

## Notification Configuration

### Email Notifications

All budget alerts send email notifications to the configured admin email address.

**Email Format**:

```
Subject: AWS Budget Alert - [Budget Name] - [Alert Level]

Your AWS account has exceeded the budget threshold:

Budget: RootTrust-Warning-dev
Threshold: $100
Current Spend: $105.23
Percentage: 105%

Please review your AWS costs in the Cost Explorer console.
```

### SNS Topic

All alerts are published to the SNS topic: `RootTrust-Cost-Alerts-{Stage}`

You can add additional subscribers:

- Email
- SMS (requires phone number verification)
- Lambda function (for automated responses)
- HTTP/HTTPS endpoint (for webhook integration)

### Adding SMS Notifications

To add SMS notifications for critical alerts:

```bash
# Subscribe phone number to SNS topic
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:ACCOUNT_ID:RootTrust-Cost-Alerts-dev \
  --protocol sms \
  --notification-endpoint +1234567890
```

**Note**: SMS notifications incur additional costs (~$0.50 per 100 messages).

## Cost Optimization Strategies

When alerts trigger, refer to these optimization strategies:

### Immediate Actions (< 1 hour)

1. Check Cost Explorer for service breakdown
2. Identify cost spike source
3. Review recent deployments or changes
4. Check for runaway processes

### Short-term Actions (< 1 day)

1. Increase cache TTL for Bedrock responses
2. Reduce EventBridge schedule frequency
3. Optimize Lambda memory settings
4. Review and optimize DynamoDB queries

### Long-term Actions (< 1 week)

1. Implement API Gateway caching
2. Optimize Lambda cold starts
3. Review and optimize data models
4. Implement request rate limiting

### Emergency Actions (Immediate)

1. Disable Bedrock AI features
2. Disable EventBridge schedules
3. Pause non-essential Lambda functions
4. Contact AWS Support for assistance

## Testing Budget Alerts

To test that budget alerts are working:

### Option 1: Lower Budget Threshold (Recommended)

```bash
# Temporarily lower budget to $1 to trigger alert
aws budgets update-budget \
  --account-id $(aws sts get-caller-identity --query Account --output text) \
  --budget BudgetName=RootTrust-Warning-dev,BudgetLimit={Amount=1,Unit=USD}

# Wait for alert email (may take up to 24 hours)

# Restore original budget
aws budgets update-budget \
  --account-id $(aws sts get-caller-identity --query Account --output text) \
  --budget BudgetName=RootTrust-Warning-dev,BudgetLimit={Amount=100,Unit=USD}
```

### Option 2: Test SNS Topic

```bash
# Send test message to SNS topic
aws sns publish \
  --topic-arn arn:aws:sns:us-east-1:ACCOUNT_ID:RootTrust-Cost-Alerts-dev \
  --subject "Test Alert" \
  --message "This is a test cost alert notification"
```

## Troubleshooting

### Budget Alerts Not Received

**Check 1**: Verify SNS subscription is confirmed

```bash
aws sns list-subscriptions-by-topic \
  --topic-arn arn:aws:sns:us-east-1:ACCOUNT_ID:RootTrust-Cost-Alerts-dev
```

**Check 2**: Verify budget exists

```bash
aws budgets describe-budgets \
  --account-id $(aws sts get-caller-identity --query Account --output text)
```

**Check 3**: Check email spam folder

**Check 4**: Verify budget notification configuration

```bash
aws budgets describe-notifications-for-budget \
  --account-id $(aws sts get-caller-identity --query Account --output text) \
  --budget-name RootTrust-Warning-dev
```

### Cost Explorer Shows No Data

- Cost data can take up to 24 hours to appear
- Ensure you have incurred some costs (even $0.01)
- Check that Cost Explorer is enabled in your account

### Budget Alerts Delayed

- Budget alerts can take up to 24 hours to trigger
- AWS evaluates budgets 3 times per day
- For real-time monitoring, use CloudWatch alarms instead

## Additional Resources

- [AWS Budgets Documentation](https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-managing-costs.html)
- [AWS Cost Explorer](https://aws.amazon.com/aws-cost-management/aws-cost-explorer/)
- [AWS Cost Anomaly Detection](https://aws.amazon.com/aws-cost-management/aws-cost-anomaly-detection/)
- [RootTrust Cost Optimization Guide](./COST_OPTIMIZATION.md)

## Summary

The RootTrust Marketplace cost monitoring system provides:

✅ **5-tier alert system** covering $100, $200, $280, 80%, and 90% thresholds
✅ **Email notifications** for all budget alerts
✅ **SNS topic** for flexible notification routing
✅ **Automated setup** via SAM template or shell script
✅ **Daily cost monitoring** via AWS CLI commands
✅ **Emergency procedures** for cost overruns
✅ **Cost optimization strategies** for each alert level

With this monitoring system in place, you can confidently run the RootTrust Marketplace platform within the $300 AWS credits budget while receiving timely alerts if costs approach critical thresholds.
