# RootTrust Cost Monitoring - Quick Reference

## Budget Alert Thresholds

| Alert         | Amount | Action                    |
| ------------- | ------ | ------------------------- |
| ⚠️ Warning    | $100   | Review costs              |
| 🔶 Critical   | $200   | Manual review required    |
| 🔴 Maximum    | $280   | Immediate action required |
| 📊 80% Budget | $240   | Monitor closely           |
| 🚨 90% Budget | $270   | Enable cost controls      |

## Quick Commands

### Check Current Costs

```bash
# Last 7 days
aws ce get-cost-and-usage \
  --time-period Start=$(date -d '7 days ago' +%Y-%m-%d),End=$(date +%Y-%m-%d) \
  --granularity DAILY \
  --metrics BlendedCost
```

### Check Service Breakdown

```bash
# Current month by service
aws ce get-cost-and-usage \
  --time-period Start=$(date -d '1 month ago' +%Y-%m-%d),End=$(date +%Y-%m-%d) \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --group-by Type=SERVICE
```

### List Active Budgets

```bash
aws budgets describe-budgets \
  --account-id $(aws sts get-caller-identity --query Account --output text)
```

## Emergency Cost Controls

### 1. Disable Bedrock (saves $50-80/month)

```bash
aws lambda update-function-configuration \
  --function-name roottrust-ai-verify \
  --environment Variables={BEDROCK_ENABLED=false}
```

### 2. Disable EventBridge Rules

```bash
aws events disable-rule --name roottrust-promotion-expiry
aws events disable-rule --name roottrust-limited-release-expiry
```

### 3. Increase Cache TTL

Update Lambda environment variables:

- `VERIFICATION_CACHE_TTL=604800` (7 days)
- `MARKETING_CACHE_TTL=2592000` (30 days)

## Setup Commands

### Deploy Budgets

```bash
cd infrastructure
./setup-budgets.sh your-email@example.com dev
```

### Deploy Dashboard

```bash
cd infrastructure
./setup-dashboard.sh dev
```

## Monitoring URLs

- **Cost Explorer**: https://console.aws.amazon.com/cost-management/home#/cost-explorer
- **Budgets**: https://console.aws.amazon.com/billing/home#/budgets
- **CloudWatch Dashboard**: https://console.aws.amazon.com/cloudwatch/home#/dashboards

## Cost Targets

| Traffic Level       | Monthly Cost |
| ------------------- | ------------ |
| Low (10 users)      | $17-25       |
| Moderate (50 users) | $50-75       |
| High (200 users)    | $150-200     |

## Support

For detailed information, see:

- [MONITORING_SETUP.md](../MONITORING_SETUP.md)
- [COST_OPTIMIZATION.md](../COST_OPTIMIZATION.md)
