# RootTrust Marketplace - Deployment Guide

## Overview

This guide provides step-by-step instructions for deploying the RootTrust Marketplace platform to AWS. The platform consists of a serverless backend (AWS SAM) and a React frontend (AWS Amplify).

## Prerequisites

### Required Tools

- AWS Account with appropriate permissions
- AWS CLI (v2.x or later)
- AWS SAM CLI (v1.x or later)
- Python 3.11
- Node.js 18+ and npm
- Git

### AWS Services Required

- Lambda
- API Gateway
- DynamoDB
- S3
- Amazon Bedrock (Claude 3 Haiku access)
- Amazon SES (verified email/domain)
- EventBridge
- Secrets Manager
- CloudWatch

### Cost Estimate

- **Monthly Budget**: ~$300 for 30+ days
- See IMPLEMENTATION_SUMMARY.md for detailed cost breakdown

## Part 1: Backend Deployment (AWS SAM)

### Step 1: Install Prerequisites

```bash
# Install AWS CLI
# macOS
brew install awscli

# Verify installation
aws --version

# Install AWS SAM CLI
# macOS
brew install aws-sam-cli

# Verify installation
sam --version

# Install Python 3.11
brew install python@3.11
```

### Step 2: Configure AWS Credentials

```bash
# Configure AWS CLI with your credentials
aws configure

# Enter when prompted:
# - AWS Access Key ID
# - AWS Secret Access Key
# - Default region (e.g., us-east-1)
# - Default output format (json)
```

### Step 3: Set Up Amazon Bedrock

```bash
# Request access to Claude 3 Haiku in AWS Console
# 1. Go to Amazon Bedrock console
# 2. Navigate to Model access
# 3. Request access to "Claude 3 Haiku" by Anthropic
# 4. Wait for approval (usually instant)
```

### Step 4: Set Up Amazon SES

```bash
# Verify your email address for sending
aws ses verify-email-identity --email-address your-email@example.com

# Check verification status
aws ses get-identity-verification-attributes --identities your-email@example.com

# Note: For production, verify your domain instead
# See backend/auth/SES_SETUP.md for detailed instructions
```

### Step 5: Create Secrets in AWS Secrets Manager

```bash
# Create JWT secret
aws secretsmanager create-secret \
  --name roottrust/jwt-secret \
  --secret-string "$(openssl rand -base64 32)"

# Create Razorpay secrets (if using Razorpay)
aws secretsmanager create-secret \
  --name roottrust/razorpay-key-id \
  --secret-string "your_razorpay_key_id"

aws secretsmanager create-secret \
  --name roottrust/razorpay-key-secret \
  --secret-string "your_razorpay_key_secret"
```

### Step 6: Build and Deploy Backend

```bash
# Navigate to project root
cd /path/to/roottrust-marketplace

# Build the SAM application
sam build

# Deploy with guided prompts (first time)
sam deploy --guided

# You will be prompted for:
# - Stack name: roottrust-marketplace
# - AWS Region: us-east-1 (or your preferred region)
# - Parameter JWTSecretName: roottrust/jwt-secret
# - Parameter SESFromEmail: your-verified-email@example.com
# - Parameter BedrockModelId: anthropic.claude-3-haiku-20240307-v1:0
# - Confirm changes before deploy: Y
# - Allow SAM CLI IAM role creation: Y
# - Save arguments to configuration file: Y

# Subsequent deployments (after first time)
sam deploy
```

### Step 7: Note API Gateway URL

```bash
# After deployment, SAM will output the API Gateway URL
# Example output:
# Outputs:
# ApiUrl: https://abc123.execute-api.us-east-1.amazonaws.com/Prod/

# Save this URL - you'll need it for frontend configuration
export API_URL="https://your-api-id.execute-api.us-east-1.amazonaws.com/Prod"
```

### Step 8: Test Backend Deployment

```bash
# Test health endpoint (if you have one)
curl $API_URL/health

# Test registration
curl -X POST $API_URL/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "testpass123",
    "role": "consumer",
    "firstName": "Test",
    "lastName": "User",
    "phone": "+911234567890"
  }'

# Test login
curl -X POST $API_URL/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "testpass123"
  }'
```

## Part 2: Frontend Deployment (AWS Amplify)

### Step 1: Prepare Frontend Configuration

```bash
# Navigate to frontend directory
cd frontend

# Create production environment file
cat > .env.production << EOF
VITE_API_BASE_URL=$API_URL
VITE_AWS_REGION=us-east-1
VITE_S3_BUCKET=roottrust-assets-prod
VITE_RAZORPAY_KEY_ID=your_razorpay_key_id
EOF

# Install dependencies
npm install

# Test build locally
npm run build

# Test production build locally
npm run preview
```

### Step 2: Deploy to AWS Amplify (Option A: Console)

1. **Connect Repository**
   - Go to AWS Amplify Console
   - Click "New app" → "Host web app"
   - Connect your Git repository (GitHub, GitLab, Bitbucket)
   - Select the repository and branch

2. **Configure Build Settings**
   - Amplify will auto-detect the build settings
   - Verify the build configuration:

   ```yaml
   version: 1
   frontend:
     phases:
       preBuild:
         commands:
           - cd frontend
           - npm ci
       build:
         commands:
           - npm run build
     artifacts:
       baseDirectory: frontend/dist
       files:
         - "**/*"
     cache:
       paths:
         - frontend/node_modules/**/*
   ```

3. **Set Environment Variables**
   - In Amplify Console, go to "Environment variables"
   - Add the following:
     - `VITE_API_BASE_URL`: Your API Gateway URL
     - `VITE_AWS_REGION`: us-east-1
     - `VITE_S3_BUCKET`: roottrust-assets-prod
     - `VITE_RAZORPAY_KEY_ID`: Your Razorpay key

4. **Deploy**
   - Click "Save and deploy"
   - Wait for deployment to complete
   - Note the Amplify app URL (e.g., https://main.d1234567890.amplifyapp.com)

### Step 3: Deploy to AWS Amplify (Option B: CLI)

```bash
# Install Amplify CLI
npm install -g @aws-amplify/cli

# Configure Amplify
amplify configure

# Initialize Amplify in your project
cd frontend
amplify init

# Add hosting
amplify add hosting

# Select:
# - Hosting with Amplify Console
# - Manual deployment

# Publish
amplify publish
```

### Step 4: Configure Custom Domain (Optional)

1. In Amplify Console, go to "Domain management"
2. Click "Add domain"
3. Enter your domain name
4. Follow DNS configuration instructions
5. Wait for SSL certificate provisioning

## Part 3: Post-Deployment Configuration

### Step 1: Enable DynamoDB Streams

```bash
# Verify DynamoDB streams are enabled for triggers
aws dynamodb describe-table \
  --table-name RootTrustMarketplace \
  --query 'Table.StreamSpecification'

# Should show: StreamEnabled: true, StreamViewType: NEW_AND_OLD_IMAGES
```

### Step 2: Configure EventBridge Rules

```bash
# Verify EventBridge rules are created
aws events list-rules --name-prefix roottrust

# Should show:
# - roottrust-promotion-expiry-check (hourly)
# - roottrust-limited-release-expiry-check (every 5 min)
```

### Step 3: Set Up CloudWatch Alarms (Optional)

```bash
# Create budget alert
aws budgets create-budget \
  --account-id $(aws sts get-caller-identity --query Account --output text) \
  --budget file://budget-config.json

# budget-config.json:
{
  "BudgetName": "RootTrust-Monthly-Budget",
  "BudgetLimit": {
    "Amount": "300",
    "Unit": "USD"
  },
  "TimeUnit": "MONTHLY",
  "BudgetType": "COST"
}
```

### Step 4: Test End-to-End Flows

1. **User Registration Flow**
   - Visit frontend URL
   - Register as consumer
   - Check email for confirmation
   - Register as farmer

2. **Consumer Flow**
   - Login as consumer
   - Browse marketplace
   - View product details
   - Test checkout (up to payment redirect)
   - Generate referral link

3. **Farmer Flow**
   - Login as farmer
   - View dashboard
   - Test AI content generator
   - View analytics (if products exist)

## Part 4: Monitoring and Maintenance

### CloudWatch Logs

```bash
# View Lambda logs
aws logs tail /aws/lambda/roottrust-auth-register --follow

# View API Gateway logs
aws logs tail /aws/apigateway/roottrust-api --follow

# View all Lambda function logs
sam logs --stack-name roottrust-marketplace --tail
```

### DynamoDB Monitoring

```bash
# Check table metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/DynamoDB \
  --metric-name ConsumedReadCapacityUnits \
  --dimensions Name=TableName,Value=RootTrustMarketplace \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 3600 \
  --statistics Sum
```

### Cost Monitoring

```bash
# Check current month costs
aws ce get-cost-and-usage \
  --time-period Start=$(date +%Y-%m-01),End=$(date +%Y-%m-%d) \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --group-by Type=SERVICE

# Set up cost alerts in AWS Budgets console
```

### API Gateway Caching (Optional)

**Note**: API Gateway caching is **DISABLED by default** to minimize costs ($14.40/month).

**When to enable**: When daily traffic exceeds 10,000 requests/day

**How to enable**: See [API_GATEWAY_CACHING.md](./API_GATEWAY_CACHING.md) for detailed instructions.

**Quick check if caching should be enabled**:

```bash
# Check daily API Gateway requests
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApiGateway \
  --metric-name Count \
  --dimensions Name=ApiName,Value=RootTrustAPI-prod \
  --start-time $(date -u -d '1 day ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 86400 \
  --statistics Sum

# If Sum > 10,000, consider enabling caching
```

**Current configuration**:

- GET /products: 5 minute TTL (when enabled)
- GET /products/{productId}: 1 hour TTL (when enabled)
- Cache size: 0.5GB
- Status: DISABLED

## Part 5: Troubleshooting

### Common Issues

#### 1. Lambda Function Timeout

```bash
# Increase timeout in template.yaml
Timeout: 60  # seconds

# Redeploy
sam build && sam deploy
```

#### 2. DynamoDB Throttling

```bash
# Check for throttling
aws cloudwatch get-metric-statistics \
  --namespace AWS/DynamoDB \
  --metric-name UserErrors \
  --dimensions Name=TableName,Value=RootTrustMarketplace \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum

# Solution: Enable auto-scaling or increase provisioned capacity
```

#### 3. Bedrock Access Denied

```bash
# Verify model access
aws bedrock list-foundation-models \
  --query 'modelSummaries[?modelId==`anthropic.claude-3-haiku-20240307-v1:0`]'

# Request access in Bedrock console if not available
```

#### 4. SES Email Not Sending

```bash
# Check SES sending limits
aws ses get-send-quota

# Verify email identity
aws ses get-identity-verification-attributes \
  --identities your-email@example.com

# Check for bounces/complaints
aws ses get-send-statistics
```

#### 5. CORS Issues

```bash
# Verify CORS configuration in template.yaml
Cors:
  AllowOrigins:
    - "*"  # Or specific domain
  AllowHeaders:
    - "*"
  AllowMethods:
    - GET
    - POST
    - PUT
    - DELETE
    - OPTIONS
```

### Debug Mode

```bash
# Enable debug logging for SAM
sam local invoke FunctionName --event event.json --debug

# Enable verbose logging for Lambda
# Add to Lambda environment variables:
LOG_LEVEL: DEBUG
```

## Part 6: Rollback Procedures

### Rollback Backend

```bash
# List CloudFormation stacks
aws cloudformation list-stacks

# Rollback to previous version
aws cloudformation rollback-stack \
  --stack-name roottrust-marketplace

# Or delete and redeploy
aws cloudformation delete-stack \
  --stack-name roottrust-marketplace

# Wait for deletion
aws cloudformation wait stack-delete-complete \
  --stack-name roottrust-marketplace

# Redeploy previous version
sam deploy
```

### Rollback Frontend

```bash
# In Amplify Console:
# 1. Go to your app
# 2. Click on "Deployments"
# 3. Find previous successful deployment
# 4. Click "Redeploy this version"
```

## Part 7: Scaling Considerations

### Auto-Scaling DynamoDB

```bash
# Enable auto-scaling for reads
aws application-autoscaling register-scalable-target \
  --service-namespace dynamodb \
  --resource-id table/RootTrustMarketplace \
  --scalable-dimension dynamodb:table:ReadCapacityUnits \
  --min-capacity 5 \
  --max-capacity 100

# Enable auto-scaling for writes
aws application-autoscaling register-scalable-target \
  --service-namespace dynamodb \
  --resource-id table/RootTrustMarketplace \
  --scalable-dimension dynamodb:table:WriteCapacityUnits \
  --min-capacity 5 \
  --max-capacity 100
```

### Lambda Concurrency Limits

```bash
# Set reserved concurrency for critical functions
aws lambda put-function-concurrency \
  --function-name roottrust-auth-login \
  --reserved-concurrent-executions 100
```

### API Gateway Throttling

```bash
# Update throttling settings in template.yaml
ThrottleSettings:
  RateLimit: 1000
  BurstLimit: 2000
```

## Part 8: Security Hardening

### Enable WAF (Optional)

```bash
# Create WAF web ACL
aws wafv2 create-web-acl \
  --name roottrust-waf \
  --scope REGIONAL \
  --default-action Allow={} \
  --rules file://waf-rules.json

# Associate with API Gateway
aws wafv2 associate-web-acl \
  --web-acl-arn arn:aws:wafv2:region:account:regional/webacl/roottrust-waf/id \
  --resource-arn arn:aws:apigateway:region::/restapis/api-id/stages/Prod
```

### Enable CloudTrail

```bash
# Create trail for audit logging
aws cloudtrail create-trail \
  --name roottrust-audit \
  --s3-bucket-name roottrust-audit-logs

# Start logging
aws cloudtrail start-logging \
  --name roottrust-audit
```

### Rotate Secrets

```bash
# Enable automatic rotation for JWT secret
aws secretsmanager rotate-secret \
  --secret-id roottrust/jwt-secret \
  --rotation-lambda-arn arn:aws:lambda:region:account:function:rotation-function
```

## Part 9: Backup and Disaster Recovery

### Enable DynamoDB Point-in-Time Recovery

```bash
# Enable PITR
aws dynamodb update-continuous-backups \
  --table-name RootTrustMarketplace \
  --point-in-time-recovery-specification PointInTimeRecoveryEnabled=true
```

### S3 Versioning

```bash
# Enable versioning on S3 bucket
aws s3api put-bucket-versioning \
  --bucket roottrust-assets-prod \
  --versioning-configuration Status=Enabled
```

### Automated Backups

```bash
# Create backup plan with AWS Backup
aws backup create-backup-plan \
  --backup-plan file://backup-plan.json
```

## Part 10: Production Checklist

### Pre-Launch Checklist

- [ ] Backend deployed successfully
- [ ] Frontend deployed successfully
- [ ] All environment variables configured
- [ ] SES email verified/domain verified
- [ ] Bedrock access enabled
- [ ] DynamoDB streams enabled
- [ ] EventBridge rules active
- [ ] CloudWatch alarms configured
- [ ] Budget alerts set up
- [ ] SSL certificate active (custom domain)
- [ ] CORS configured correctly
- [ ] API throttling configured
- [ ] Lambda timeouts appropriate
- [ ] DynamoDB capacity appropriate
- [ ] S3 lifecycle policies active
- [ ] Backup enabled
- [ ] Monitoring dashboards created
- [ ] Documentation updated
- [ ] End-to-end testing completed
- [ ] Load testing completed (optional)
- [ ] Security review completed

### Post-Launch Monitoring

- Monitor CloudWatch metrics daily
- Check error logs regularly
- Review cost reports weekly
- Test critical flows weekly
- Update dependencies monthly
- Review security patches monthly
- Backup verification monthly

## Support and Resources

### AWS Documentation

- [AWS SAM Documentation](https://docs.aws.amazon.com/serverless-application-model/)
- [AWS Amplify Documentation](https://docs.amplify.aws/)
- [Amazon Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [DynamoDB Documentation](https://docs.aws.amazon.com/dynamodb/)

### Project Documentation

- `README.md` - Project overview
- `IMPLEMENTATION_SUMMARY.md` - Implementation details
- `template.yaml` - SAM template with all resources
- `frontend/README.md` - Frontend documentation
- `backend/*/README.md` - Service-specific documentation

### Getting Help

- Check CloudWatch logs for errors
- Review AWS service health dashboard
- Consult AWS Support (if you have a support plan)
- Review project documentation

## Conclusion

Your RootTrust Marketplace platform is now deployed and ready for use! Monitor the application closely in the first few days to ensure everything is working as expected. Adjust scaling parameters based on actual usage patterns.

**Estimated Deployment Time**: 2-3 hours (first time)
**Estimated Monthly Cost**: ~$300 (within budget)
**Deployment Status**: Production-ready MVP

For questions or issues, refer to the troubleshooting section or consult the AWS documentation.
