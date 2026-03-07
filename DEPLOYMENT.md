# RootTrust Deployment Guide

## Quick Start

### 1. Prerequisites Check

```bash
aws --version          # AWS CLI 2.x
sam --version          # SAM CLI 1.x
python --version       # Python 3.11+
```

### 2. Build

```bash
sam build
```

### 3. Deploy

```bash
sam deploy --guided
```

### 4. Configure Secrets

Update API keys in AWS Secrets Manager after deployment.

## Detailed Instructions

See README.md for complete setup and configuration details.

## Budget Monitoring

Monitor costs in AWS Budgets console. Alert triggers at $240 (80% of $300).

## Troubleshooting

- **Build fails**: Check Python version and dependencies
- **Deploy fails**: Verify AWS credentials and permissions
- **Budget alert**: Review CloudWatch metrics and optimize resources
