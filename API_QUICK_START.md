# RootTrust Marketplace API - Quick Start Guide

**Base URL**: `https://b88kwrtrik.execute-api.us-east-1.amazonaws.com/dev`

---

## Authentication

### Register a New User

**Endpoint**: `POST /auth/register`

**Consumer Registration**:

```bash
curl -X POST https://b88kwrtrik.execute-api.us-east-1.amazonaws.com/dev/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "consumer@example.com",
    "password": "SecurePass123",
    "role": "consumer",
    "firstName": "John",
    "lastName": "Doe",
    "phone": "1234567890"
  }'
```

**Farmer Registration**:

```bash
curl -X POST https://b88kwrtrik.execute-api.us-east-1.amazonaws.com/dev/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "farmer@example.com",
    "password": "SecurePass123",
    "role": "farmer",
    "firstName": "Jane",
    "lastName": "Smith",
    "phone": "0987654321"
  }'
```

### Login

**Endpoint**: `POST /auth/login`

```bash
curl -X POST https://b88kwrtrik.execute-api.us-east-1.amazonaws.com/dev/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "consumer@example.com",
    "password": "SecurePass123"
  }'
```

**Response**:

```json
{
  "success": true,
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "userId": "uuid-here",
  "role": "consumer",
  "expiresIn": 86400
}
```

**Save the token** for authenticated requests!

---

## Products

### List Products

**Endpoint**: `GET /products`

```bash
# List all products
curl -X GET "https://b88kwrtrik.execute-api.us-east-1.amazonaws.com/dev/products"

# Filter by category
curl -X GET "https://b88kwrtrik.execute-api.us-east-1.amazonaws.com/dev/products?category=vegetables"

# Search products
curl -X GET "https://b88kwrtrik.execute-api.us-east-1.amazonaws.com/dev/products?search=organic&limit=10"
```

### Create Product (Farmer Only)

**Endpoint**: `POST /products`

```bash
curl -X POST https://b88kwrtrik.execute-api.us-east-1.amazonaws.com/dev/products \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "name": "Organic Tomatoes",
    "category": "vegetables",
    "description": "Fresh organic tomatoes from my farm",
    "price": 50.00,
    "unit": "kg",
    "quantity": 100,
    "hasGITag": false,
    "isSeasonal": true,
    "seasonStart": "2026-03-01",
    "seasonEnd": "2026-06-30"
  }'
```

### Get Product Details

**Endpoint**: `GET /products/{productId}`

```bash
curl -X GET "https://b88kwrtrik.execute-api.us-east-1.amazonaws.com/dev/products/PRODUCT_ID"
```

### Update Product (Farmer Only)

**Endpoint**: `PUT /products/{productId}`

```bash
curl -X PUT https://b88kwrtrik.execute-api.us-east-1.amazonaws.com/dev/products/PRODUCT_ID \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "price": 45.00,
    "quantity": 150
  }'
```

---

## AI Services

### Verify Product (Farmer Only)

**Endpoint**: `POST /ai/verify-product`

```bash
curl -X POST https://b88kwrtrik.execute-api.us-east-1.amazonaws.com/dev/ai/verify-product \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "productId": "PRODUCT_ID"
  }'
```

### Generate Product Description

**Endpoint**: `POST /ai/generate-description`

```bash
curl -X POST https://b88kwrtrik.execute-api.us-east-1.amazonaws.com/dev/ai/generate-description \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "productName": "Organic Tomatoes",
    "category": "vegetables",
    "features": ["organic", "locally grown", "pesticide-free"]
  }'
```

### Generate Product Names

**Endpoint**: `POST /ai/generate-names`

```bash
curl -X POST https://b88kwrtrik.execute-api.us-east-1.amazonaws.com/dev/ai/generate-names \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "category": "vegetables",
    "features": ["organic", "heirloom"],
    "count": 5
  }'
```

---

## Orders

### Create Order (Consumer Only)

**Endpoint**: `POST /orders`

```bash
curl -X POST https://b88kwrtrik.execute-api.us-east-1.amazonaws.com/dev/orders \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "productId": "PRODUCT_ID",
    "quantity": 5,
    "deliveryAddress": {
      "street": "123 Main St",
      "city": "Mumbai",
      "state": "Maharashtra",
      "pincode": "400001"
    },
    "referralCode": "OPTIONAL_CODE"
  }'
```

### List Orders

**Endpoint**: `GET /orders`

```bash
# List your orders
curl -X GET "https://b88kwrtrik.execute-api.us-east-1.amazonaws.com/dev/orders" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Get Order Details

**Endpoint**: `GET /orders/{orderId}`

```bash
curl -X GET "https://b88kwrtrik.execute-api.us-east-1.amazonaws.com/dev/orders/ORDER_ID" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Update Order Status (Farmer Only)

**Endpoint**: `PUT /orders/{orderId}/status`

```bash
curl -X PUT https://b88kwrtrik.execute-api.us-east-1.amazonaws.com/dev/orders/ORDER_ID/status \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "status": "shipped"
  }'
```

**Valid statuses**: `pending`, `confirmed`, `processing`, `shipped`, `delivered`, `cancelled`

---

## Payments

### Initiate Payment (Consumer Only)

**Endpoint**: `POST /payments/initiate`

```bash
curl -X POST https://b88kwrtrik.execute-api.us-east-1.amazonaws.com/dev/payments/initiate \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "orderId": "ORDER_ID",
    "paymentMethod": "upi"
  }'
```

**Payment Methods**: `upi`, `card`, `netbanking`

### Get Payment Status

**Endpoint**: `GET /payments/{transactionId}/status`

```bash
curl -X GET "https://b88kwrtrik.execute-api.us-east-1.amazonaws.com/dev/payments/TRANSACTION_ID/status" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

## Reviews

### Create Review (Consumer Only)

**Endpoint**: `POST /reviews`

```bash
curl -X POST https://b88kwrtrik.execute-api.us-east-1.amazonaws.com/dev/reviews \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "productId": "PRODUCT_ID",
    "orderId": "ORDER_ID",
    "rating": 5,
    "reviewText": "Excellent quality tomatoes! Very fresh and organic.",
    "photoUploadCount": 2
  }'
```

**Rating**: 1-5 stars

### List Product Reviews

**Endpoint**: `GET /reviews/product/{productId}`

```bash
curl -X GET "https://b88kwrtrik.execute-api.us-east-1.amazonaws.com/dev/reviews/product/PRODUCT_ID"
```

### List Farmer Reviews

**Endpoint**: `GET /reviews/farmer/{farmerId}`

```bash
curl -X GET "https://b88kwrtrik.execute-api.us-east-1.amazonaws.com/dev/reviews/farmer/FARMER_ID"
```

---

## Referrals

### Generate Referral Link (Consumer Only)

**Endpoint**: `POST /referrals/generate`

```bash
curl -X POST https://b88kwrtrik.execute-api.us-east-1.amazonaws.com/dev/referrals/generate \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "productId": "PRODUCT_ID"
  }'
```

### Get Referral Rewards

**Endpoint**: `GET /referrals/rewards`

```bash
curl -X GET "https://b88kwrtrik.execute-api.us-east-1.amazonaws.com/dev/referrals/rewards" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

## Promotions

### Create Promotion (Farmer Only)

**Endpoint**: `POST /promotions`

```bash
curl -X POST https://b88kwrtrik.execute-api.us-east-1.amazonaws.com/dev/promotions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "productId": "PRODUCT_ID",
    "budget": 500.00,
    "duration": 7
  }'
```

### List Active Promotions

**Endpoint**: `GET /promotions/active`

```bash
curl -X GET "https://b88kwrtrik.execute-api.us-east-1.amazonaws.com/dev/promotions/active" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Update Promotion Status

**Endpoint**: `PUT /promotions/{promotionId}`

```bash
curl -X PUT https://b88kwrtrik.execute-api.us-east-1.amazonaws.com/dev/promotions/PROMOTION_ID \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "status": "paused"
  }'
```

**Valid statuses**: `active`, `paused`, `cancelled`, `completed`

---

## Limited Releases

### Create Limited Release (Farmer Only)

**Endpoint**: `POST /limited-releases`

```bash
curl -X POST https://b88kwrtrik.execute-api.us-east-1.amazonaws.com/dev/limited-releases \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "productId": "PRODUCT_ID",
    "releaseName": "Spring Harvest Special",
    "quantityLimit": 50,
    "duration": 3
  }'
```

### List Active Limited Releases

**Endpoint**: `GET /limited-releases/active`

```bash
curl -X GET "https://b88kwrtrik.execute-api.us-east-1.amazonaws.com/dev/limited-releases/active"
```

### Purchase from Limited Release

**Endpoint**: `POST /limited-releases/{releaseId}/purchase`

```bash
curl -X POST https://b88kwrtrik.execute-api.us-east-1.amazonaws.com/dev/limited-releases/RELEASE_ID/purchase \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "quantity": 2,
    "deliveryAddress": {
      "street": "123 Main St",
      "city": "Mumbai",
      "state": "Maharashtra",
      "pincode": "400001"
    }
  }'
```

---

## Analytics

### Get Farmer Analytics (Farmer Only)

**Endpoint**: `GET /analytics/farmer`

```bash
curl -X GET "https://b88kwrtrik.execute-api.us-east-1.amazonaws.com/dev/analytics/farmer" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Get Product Analytics (Farmer Only)

**Endpoint**: `GET /analytics/product/{productId}`

```bash
curl -X GET "https://b88kwrtrik.execute-api.us-east-1.amazonaws.com/dev/analytics/product/PRODUCT_ID" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Get Seasonal Trends

**Endpoint**: `GET /analytics/seasonal-trends`

```bash
curl -X GET "https://b88kwrtrik.execute-api.us-east-1.amazonaws.com/dev/analytics/seasonal-trends?category=vegetables"
```

---

## Notifications

### Update Notification Preferences

**Endpoint**: `PUT /notifications/preferences`

```bash
curl -X PUT https://b88kwrtrik.execute-api.us-east-1.amazonaws.com/dev/notifications/preferences \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "newProducts": true,
    "promotions": false,
    "orderUpdates": true,
    "reviewRequests": true,
    "limitedReleases": true
  }'
```

### Unsubscribe from Notifications

**Endpoint**: `POST /notifications/unsubscribe`

```bash
curl -X POST https://b88kwrtrik.execute-api.us-east-1.amazonaws.com/dev/notifications/unsubscribe \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "token": "UNSUBSCRIBE_TOKEN"
  }'
```

---

## Error Handling

All endpoints return errors in this format:

```json
{
  "success": false,
  "error": "ERROR_CODE",
  "message": "Human-readable error message",
  "details": []
}
```

### Common Error Codes

- `VALIDATION_ERROR` (400): Invalid request data
- `AUTHENTICATION_ERROR` (401): Missing or invalid JWT token
- `AUTHORIZATION_ERROR` (403): Insufficient permissions
- `RESOURCE_NOT_FOUND` (404): Resource doesn't exist
- `CONFLICT_ERROR` (409): Business rule violation
- `INTERNAL_ERROR` (500): Server error

---

## Rate Limiting

- **Rate**: 100 requests/second
- **Burst**: 500 requests

If you exceed the limit, you'll receive a `429 Too Many Requests` response.

---

## Testing Tips

1. **Save your JWT token** after login for subsequent requests
2. **Use environment variables** for tokens and IDs
3. **Test with Postman** or similar tools for easier debugging
4. **Check CloudWatch logs** if you encounter errors
5. **Use the frontend** for a better user experience

---

## Frontend Integration

Update your frontend `.env` file:

```env
VITE_API_BASE_URL=https://b88kwrtrik.execute-api.us-east-1.amazonaws.com/dev
VITE_AWS_REGION=us-east-1
VITE_S3_BUCKET=roottrust-assets-dev-504181993609
```

---

## Support

**Issues?** Check:

1. CloudWatch logs for Lambda functions
2. API Gateway execution logs
3. DynamoDB table for data
4. JWT token expiration (24 hours)

**Email**: mayureshkasabe51@gmail.com
