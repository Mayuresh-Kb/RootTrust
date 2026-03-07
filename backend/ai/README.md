# AI Verification Service

This module provides AI-powered fraud detection and product verification using Amazon Bedrock.

## Endpoints

### POST /ai/verify-product

Analyzes a product for fraud detection using Amazon Bedrock (Claude 3 Haiku).

**Authentication:** Required (JWT token)
**Authorization:** Farmer (own products only) or Admin

**Request Body:**

```json
{
  "productId": "uuid-v4"
}
```

**Response (200 OK):**

```json
{
  "fraudRiskScore": 45.5,
  "authenticityConfidence": 85.0,
  "predictedMarketPrice": 120.5,
  "aiExplanation": "Product appears authentic based on reasonable pricing, GI tag verification, and supporting documentation.",
  "verificationStatus": "approved",
  "cached": false
}
```

**Verification Status Logic:**

- `fraudRiskScore > 70`: Product is flagged for manual review
- `fraudRiskScore ≤ 70`: Product is approved

**Caching:**

- Verification results are cached for 24 hours in DynamoDB
- Cache key: `VERIFICATION_CACHE#{productId}`
- Reduces Bedrock API costs by avoiding duplicate analyses

## Market Price Calculation

The predicted market price is calculated based on:

1. **Base Price by Category:**
   - Vegetables: ₹50/kg
   - Fruits: ₹80/kg
   - Grains: ₹40/kg
   - Spices: ₹200/kg
   - Dairy: ₹60/unit

2. **GI Tag Premium:** +20% if product has GI tag

3. **Seasonal Factor:**
   - In season: -10% (more supply)
   - Out of season: +30% (scarcity premium)

## Bedrock Model

- **Model:** Claude 3 Haiku (`anthropic.claude-3-haiku-20240307-v1:0`)
- **Temperature:** 0.3 (for consistent results)
- **Max Tokens:** 1000

## Error Handling

- **400 Bad Request:** Missing or invalid productId
- **401 Unauthorized:** Missing JWT token
- **403 Forbidden:** User not authorized (not farmer/admin, or not product owner)
- **404 Not Found:** Product doesn't exist
- **503 Service Unavailable:** Bedrock API failure

## Cost Optimization

1. **Caching:** 24-hour TTL reduces duplicate Bedrock calls
2. **Model Selection:** Claude 3 Haiku is cost-efficient
3. **Low Temperature:** Reduces token usage with focused responses
