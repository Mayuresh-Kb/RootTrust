# RootTrust Infrastructure Documentation

## AWS SAM Template Overview

The `template.yaml` file defines all AWS resources for the RootTrust platform.

## Resources Created

### 1. DynamoDB Table (RootTrustDataTable)

- **Purpose**: Single-table design for all entities
- **Billing**: On-demand (cost-optimized)
- **Primary Key**: PK (partition), SK (sort)
- **GSI1**: Category/seasonal queries (CATEGORY#vegetables)
- **GSI2**: Farmer/consumer lookups (FARMER#userId, CONSUMER#userId)
- **GSI3**: Time-based queries (STATUS#active, RELEASE#endDate)
- **Streams**: Enabled for event-driven processing
- **Backup**: Point-in-time recovery enabled

### 2. S3 Bucket (RootTrustAssetsBucket)

- **Purpose**: Product images, invoices, review photos
- **Lifecycle Rules**:
  - Products: Standard → Standard-IA after 30 days (cost savings)
  - Temp uploads: Auto-delete after 1 day
- **CORS**: Enabled for web uploads
- **Access**: Private with Lambda access via bucket policy

### 3. API Gateway (RootTrustApi)

- **Type**: REST API with JWT authorization
- **CORS**: Configured for web access
- **Throttling**: 100 req/sec per user, 500 burst
- **Logging**: CloudWatch integration
- **Tracing**: X-Ray enabled

### 4. Secrets Manager

- **JWTSecret**: Auto-generated 64-char secret for token signing
- **APIKeysSecret**: Razorpay/Stripe credentials (manual update required)

### 5. AWS Budgets

- **Limit**: $300/month
- **Alert**: Email at 80% ($240)
- **Scope**: Tagged resources (Project=RootTrust)

### 6. IAM Role (LambdaExecutionRole)

- **Permissions**:
  - DynamoDB: Full CRUD + Query/Scan
  - S3: Get/Put/Delete objects
  - Secrets Manager: Read secrets
  - Bedrock: Invoke models
  - SES: Send emails
  - DynamoDB Streams: Read stream records
  - CloudWatch Logs: Write logs
  - X-Ray: Write traces

## Cost Optimization Strategy

1. **Lambda**: Serverless, pay per invocation
2. **DynamoDB**: On-demand pricing, no idle costs
3. **S3**: Lifecycle policies reduce storage costs
4. **API Gateway**: Throttling prevents runaway costs
5. **Bedrock**: Response caching (24h TTL)

## Security Features

- Private S3 bucket with IAM-based access
- JWT authentication with Secrets Manager
- Least-privilege IAM policies
- API throttling and CORS restrictions
- Encrypted secrets at rest

## Monitoring

- CloudWatch Logs for all Lambda functions
- X-Ray tracing for performance analysis
- API Gateway metrics (requests, latency, errors)
- Budget alerts via email

## Deployment Parameters

- **Stage**: dev or prod
- **MonthlyBudgetLimit**: Default $300
- **BudgetAlertThreshold**: Default 80%

## Outputs

- ApiEndpoint: API Gateway URL
- DynamoDBTableName: Table name for Lambda env vars
- S3BucketName: Bucket name for asset storage
- JWTSecretArn: Secret ARN for authentication
- APIKeysSecretArn: Secret ARN for payment gateways
- LambdaExecutionRoleArn: IAM role for Lambda functions
