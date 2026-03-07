# AI Verification Status Endpoint

## Overview

This endpoint retrieves the current verification status and scores for a product that has been processed by the AI fraud detection system.

## Endpoint

```
GET /ai/verification-status/{productId}
```

## Authentication

- **Optional**: This endpoint can be accessed with or without authentication
- If a valid JWT token is provided, it will be validated but not required
- Verification status is considered public information for approved products

## Path Parameters

- `productId` (required): The UUID of the product to check

## Response Format

### Success Response (200 OK)

```json
{
  "productId": "uuid",
  "verificationStatus": "approved|pending|flagged|rejected",
  "fraudRiskScore": 45.5,
  "authenticityConfidence": 85.0,
  "predictedMarketPrice": 120.5,
  "aiExplanation": "Product appears authentic based on provided details..."
}
```

### Pending Product (200 OK)

```json
{
  "productId": "uuid",
  "verificationStatus": "pending"
}
```

Note: Verification details (scores, explanation) are only included if verification has been completed.

### Error Responses

#### Product Not Found (404)

```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Product {productId} not found"
  }
}
```

#### Missing Product ID (400)

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "productId is required in path"
  }
}
```

## Implementation Details

### Lambda Function

- **Handler**: `verification_status.handler`
- **Timeout**: 10 seconds
- **Memory**: 256 MB
- **Permissions**: DynamoDB Read access

### Data Source

The endpoint queries the DynamoDB `Products` table with:

- **PK**: `PRODUCT#{productId}`
- **SK**: `METADATA`

### Fields Retrieved

- `verificationStatus`: Current status (pending, approved, flagged, rejected)
- `fraudRiskScore`: AI-calculated fraud risk (0-100)
- `authenticityConfidence`: AI confidence in authenticity (0-100)
- `predictedMarketPrice`: AI-predicted market price
- `aiExplanation`: Human-readable explanation of verification decision

## Usage Examples

### With cURL

```bash
# Without authentication
curl -X GET https://api.roottrust.com/ai/verification-status/abc-123-def

# With authentication
curl -X GET https://api.roottrust.com/ai/verification-status/abc-123-def \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### With JavaScript/Fetch

```javascript
// Without authentication
const response = await fetch(
  `https://api.roottrust.com/ai/verification-status/${productId}`,
);
const data = await response.json();

// With authentication
const response = await fetch(
  `https://api.roottrust.com/ai/verification-status/${productId}`,
  {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  },
);
const data = await response.json();
```

## Integration with Frontend

### Consumer Portal

Consumers can view verification status on product detail pages to make informed purchasing decisions.

### Farmer Portal

Farmers can check the verification status of their products to understand if they need to provide additional documentation.

## Related Endpoints

- `POST /ai/verify-product`: Trigger AI verification for a product
- `GET /products/{productId}`: Get complete product details including verification status

## Requirements Validated

- **Requirement 3.1**: Product verification system provides status and scores
