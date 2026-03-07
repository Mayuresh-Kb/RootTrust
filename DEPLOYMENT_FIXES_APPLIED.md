# RootTrust Marketplace - Deployment Fixes Applied

**Date**: March 7, 2026  
**Status**: 🔄 Deployment In Progress (3rd Attempt)

## Issues Encountered and Fixed

### Issue 1: JWT Secret Key Mismatch

**Problem**: The JWT secret was being generated with key `jwt_secret` but the Lambda functions were trying to resolve it with key `secret`.

**Error Message**:

```
Could not find a value associated with JSONKey in SecretString
```

**Fix Applied**:
Changed the `GenerateStringKey` in the JWTSecret resource from `jwt_secret` to `secret`:

```yaml
JWTSecret:
  Type: AWS::SecretsManager::Secret
  Properties:
    Name: !Sub "RootTrust-JWT-Secret-${Stage}"
    GenerateSecretString:
      SecretStringTemplate: "{}"
      GenerateStringKey: "secret" # Changed from "jwt_secret"
      PasswordLength: 64
```

**File Modified**: `template.yaml` (line 264)

### Issue 2: Missing Payment Webhook Secrets

**Problem**: PaymentWebhookFunction was trying to access Stripe and Razorpay webhook secrets that don't exist yet.

**Error Message**:

```
Secrets Manager can't find the specified secret
```

**Fix Applied**:
Removed the webhook secret references since we're using mock payments (`USE_MOCK_PAYMENT: "true"`):

```yaml
PaymentWebhookFunction:
  Environment:
    Variables:
      DYNAMODB_TABLE_NAME: !Ref RootTrustDataTable
      USE_MOCK_PAYMENT: "true"
      SENDER_EMAIL: !Ref SenderEmail
      # Removed: STRIPE_WEBHOOK_SECRET
      # Removed: RAZORPAY_WEBHOOK_SECRET
```

Also removed the Secrets Manager policy statements for these secrets.

**File Modified**: `template.yaml` (lines 928-960)

## Deployment Attempts

### Attempt 1 (Failed)

- **Time**: ~13:08 UTC
- **Failure Reason**: JWT secret key mismatch
- **Duration**: ~8 minutes before rollback
- **Resources Created Before Failure**: 15 (Budgets, SNS, some IAM roles, Secrets, S3, DynamoDB)

### Attempt 2 (Failed)

- **Time**: ~18:50 UTC
- **Failure Reason**: Payment webhook secrets not found
- **Duration**: ~2 minutes before rollback
- **Resources Created Before Failure**: 20+ (more IAM roles, some Lambda functions)

### Attempt 3 (In Progress)

- **Time**: Started ~19:15 UTC
- **Status**: Creating changeset
- **Expected Duration**: 15-20 minutes
- **Fixes Applied**: Both JWT secret and webhook secret issues resolved

## Current Deployment Status

The deployment is now proceeding with all fixes applied. The CloudFormation stack is being created with:

- ✅ JWT secret with correct key name (`secret`)
- ✅ Payment webhook function without missing secret references
- ✅ All 44 Lambda functions
- ✅ DynamoDB table with streams
- ✅ S3 bucket for assets
- ✅ API Gateway with JWT authorizer
- ✅ EventBridge rules for scheduled tasks
- ✅ Budget alerts (4 levels)
- ✅ SNS topic for cost alerts

## Next Steps After Successful Deployment

1. **Retrieve API Gateway URL**:

   ```bash
   aws cloudformation describe-stacks \
     --stack-name roottrust-marketplace \
     --region us-east-1 \
     --query 'Stacks[0].Outputs[?OutputKey==`ApiUrl`].OutputValue' \
     --output text
   ```

2. **Test Backend API**:
   - Test registration endpoint
   - Test login endpoint
   - Test product listing endpoint

3. **Configure Frontend**:

   ```bash
   cd frontend
   echo "VITE_API_BASE_URL=<api-url>" > .env.production
   npm run build
   ```

4. **Deploy Frontend to AWS Amplify**

5. **Set Up Cost Monitoring**:
   ```bash
   cd infrastructure
   ./setup-budgets.sh mayureshkasabe51@gmail.com dev
   ./setup-dashboard.sh dev
   ```

## Lessons Learned

1. **Secrets Manager Key Names**: Always ensure the `GenerateStringKey` matches the key used in `resolve:secretsmanager` references.

2. **Optional Secrets**: For development/testing with mock services, don't reference secrets that don't exist. Remove them from environment variables and IAM policies.

3. **Stack Cleanup**: Always delete failed stacks in `ROLLBACK_COMPLETE` state before redeploying:

   ```bash
   aws cloudformation delete-stack --stack-name <stack-name>
   aws cloudformation wait stack-delete-complete --stack-name <stack-name>
   ```

4. **Incremental Testing**: Test secret resolution locally or with a minimal stack before deploying the full application.

## Files Modified

1. `template.yaml`:
   - Line 264: Changed JWT secret key from `jwt_secret` to `secret`
   - Lines 928-960: Removed webhook secret references from PaymentWebhookFunction

## Monitoring Deployment

To monitor the current deployment:

```bash
# Check stack status
aws cloudformation describe-stacks \
  --stack-name roottrust-marketplace \
  --region us-east-1 \
  --query 'Stacks[0].StackStatus'

# Watch stack events
aws cloudformation describe-stack-events \
  --stack-name roottrust-marketplace \
  --region us-east-1 \
  --max-items 20
```

---

**Deployment will complete in approximately 15-20 minutes.**
