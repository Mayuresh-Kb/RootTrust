# Amazon SES Setup for RootTrust Email Notifications

This document explains how to configure Amazon SES (Simple Email Service) for sending registration confirmation emails and other notifications in the RootTrust marketplace.

## Prerequisites

- AWS Account with appropriate permissions
- AWS CLI configured
- Access to AWS SES console

## Setup Steps

### 1. Verify Sender Email Address

Before you can send emails, you need to verify the sender email address in Amazon SES.

#### Using AWS Console:

1. Navigate to Amazon SES console: https://console.aws.amazon.com/ses/
2. Click on "Verified identities" in the left sidebar
3. Click "Create identity"
4. Select "Email address"
5. Enter your sender email (e.g., `noreply@roottrust.com`)
6. Click "Create identity"
7. Check your email inbox for a verification email from AWS
8. Click the verification link in the email

#### Using AWS CLI:

```bash
aws ses verify-email-identity --email-address noreply@roottrust.com
```

Then check your email and click the verification link.

### 2. Request Production Access (Optional)

By default, SES accounts are in "sandbox mode" which has the following limitations:

- You can only send emails to verified email addresses
- Maximum of 200 emails per 24-hour period
- Maximum send rate of 1 email per second

For production use, you should request production access:

1. Go to the SES console
2. Click "Account dashboard" in the left sidebar
3. Click "Request production access"
4. Fill out the form explaining your use case
5. Submit the request

AWS typically reviews and approves requests within 24 hours.

### 3. Configure SAM Template

The SAM template (`template.yaml`) already includes:

- SES permissions in the Lambda execution role
- Environment variable for sender email (`SENDER_EMAIL`)

When deploying, you can specify the sender email:

```bash
sam deploy --parameter-overrides SenderEmail=noreply@roottrust.com
```

### 4. Environment Variables

The following environment variables are used for email functionality:

- `SENDER_EMAIL`: The verified email address to send from (default: `noreply@roottrust.com`)
- `AWS_REGION`: AWS region for SES (default: `us-east-1`)
- `ENABLE_EMAIL_VERIFICATION`: Enable email verification links (default: `false`)

### 5. Testing Email Functionality

#### In Sandbox Mode:

To test emails in sandbox mode, you need to verify recipient email addresses:

```bash
aws ses verify-email-identity --email-address test@example.com
```

Then register a user with that email address.

#### Using AWS SES Mailbox Simulator:

AWS provides test email addresses that don't require verification:

- `success@simulator.amazonses.com` - Simulates successful delivery
- `bounce@simulator.amazonses.com` - Simulates a bounce
- `complaint@simulator.amazonses.com` - Simulates a complaint
- `suppressionlist@simulator.amazonses.com` - Simulates suppression list

Example registration:

```bash
curl -X POST https://your-api-endpoint/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "success@simulator.amazonses.com",
    "password": "TestPass123!",
    "role": "consumer",
    "firstName": "Test",
    "lastName": "User",
    "phone": "1234567890"
  }'
```

## Email Templates

Email templates are defined in `backend/shared/email_templates.py`. Currently available templates:

### Registration Confirmation Email

- **Function**: `get_registration_confirmation_email()`
- **Trigger**: Sent automatically after successful user registration
- **Content**: Welcome message with optional email verification link
- **Format**: HTML and plain text versions

## Monitoring and Troubleshooting

### Check Email Sending Statistics

```bash
aws ses get-send-statistics
```

### View Sending Quota

```bash
aws ses get-send-quota
```

### Common Issues

1. **Email not received**:
   - Check if sender email is verified
   - Check if recipient email is verified (in sandbox mode)
   - Check CloudWatch logs for Lambda function errors
   - Check SES sending statistics for bounces/complaints

2. **"Email address not verified" error**:
   - Verify the sender email address in SES console
   - Wait a few minutes after verification before testing

3. **Rate limit exceeded**:
   - In sandbox mode, you're limited to 1 email/second
   - Request production access for higher limits
   - Implement retry logic with exponential backoff

### CloudWatch Logs

Email sending logs are available in CloudWatch:

```bash
aws logs tail /aws/lambda/RootTrust-Auth-Register-dev --follow
```

## Cost Considerations

Amazon SES pricing (as of 2024):

- First 62,000 emails per month: FREE (when sent from EC2 or Lambda)
- Additional emails: $0.10 per 1,000 emails
- Attachments: $0.12 per GB

For the RootTrust hackathon prototype with $300 budget, email costs should be negligible.

## Security Best Practices

1. **Use verified domains**: For production, verify your domain instead of individual email addresses
2. **Implement DKIM**: Add DKIM signatures to improve deliverability
3. **Set up SPF records**: Configure SPF records for your domain
4. **Monitor bounce rates**: High bounce rates can affect your sender reputation
5. **Handle unsubscribes**: Implement unsubscribe functionality (required by law in many jurisdictions)

## Future Enhancements

- Email verification with token-based confirmation
- Email templates for order confirmations, shipping updates, etc.
- HTML email template customization
- Email preference management
- Transactional email tracking
- Email analytics and reporting

## References

- [Amazon SES Documentation](https://docs.aws.amazon.com/ses/)
- [SES Sending Limits](https://docs.aws.amazon.com/ses/latest/dg/manage-sending-quotas.html)
- [SES Best Practices](https://docs.aws.amazon.com/ses/latest/dg/best-practices.html)
