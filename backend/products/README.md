# Product Service

This module handles product management operations for the RootTrust marketplace platform.

## Endpoints

### POST /products

Creates a new product listing for farmers.

**Authentication:** Required (JWT token)  
**Authorization:** Farmer role only

**Request Body:**

```json
{
  "name": "Organic Tomatoes",
  "category": "vegetables",
  "description": "Fresh organic tomatoes from our farm",
  "price": 50.0,
  "unit": "kg",
  "quantity": 100,
  "hasGITag": true,
  "giTagName": "Nashik Tomato",
  "giTagRegion": "Nashik, Maharashtra",
  "isSeasonal": true,
  "seasonStart": "2024-01-01T00:00:00",
  "seasonEnd": "2024-06-30T23:59:59"
}
```

**Response (201 Created):**

```json
{
  "productId": "uuid-v4",
  "status": "pending",
  "uploadUrls": [
    {
      "url": "https://s3.amazonaws.com/presigned-url",
      "key": "products/uuid/images/image-1.jpg",
      "expiresIn": 900
    }
  ],
  "message": "Product created successfully"
}
```

**Validation Rules:**

- `name`: Required, 1-200 characters
- `category`: Required, must be one of: vegetables, fruits, grains, spices, dairy
- `description`: Required, 10-5000 characters
- `price`: Required, must be positive number (> 0)
- `unit`: Required, 1-50 characters
- `quantity`: Required, must be >= 0
- `hasGITag`: Boolean, if true then giTagName is required
- `isSeasonal`: Boolean, if true then seasonStart and seasonEnd are required

**Error Responses:**

401 Unauthorized:

```json
{
  "error": {
    "code": "UNAUTHORIZED",
    "message": "Authorization header is required"
  }
}
```

403 Forbidden:

```json
{
  "error": {
    "code": "FORBIDDEN",
    "message": "Only farmers can create products"
  }
}
```

400 Bad Request:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Product validation failed",
    "details": [
      {
        "field": "price",
        "message": "Price must be a positive number"
      }
    ]
  }
}
```

## Features

- **JWT Authentication**: Validates farmer role before allowing product creation
- **Input Validation**: Comprehensive validation of all product fields
- **Price Validation**: Ensures price is positive (Property 8)
- **Category Validation**: Validates category against enum values
- **S3 Pre-signed URLs**: Generates secure upload URLs for product images (15 min expiration, 5MB max)
- **DynamoDB Storage**: Stores product with single-table design pattern
- **Verification Status**: Sets initial status to "pending" for AI verification
- **GSI Indexing**: Automatically sets up GSI keys for efficient querying

## Implementation Details

### DynamoDB Keys

- **PK**: `PRODUCT#{productId}`
- **SK**: `METADATA`
- **GSI1PK**: `CATEGORY#{category}` (for category filtering)
- **GSI1SK**: `PRODUCT#{createdAt}`
- **GSI2PK**: `FARMER#{farmerId}` (for farmer's products)
- **GSI2SK**: `PRODUCT#{createdAt}`
- **GSI3PK**: `STATUS#{verificationStatus}` (for status filtering)
- **GSI3SK**: `PRODUCT#{createdAt}`

### S3 Image Upload Flow

1. Product is created with empty images array
2. Pre-signed URLs are generated for up to 5 images
3. Frontend uploads images directly to S3 using pre-signed URLs
4. Separate endpoint (future) updates product record with image URLs

## Testing

Run unit tests:

```bash
pytest tests/test_product_create.py -v
```

Test coverage includes:

- Successful product creation
- Authorization checks (missing token, consumer role)
- Input validation (negative price, zero price, invalid category)
- Missing required fields
- DynamoDB error handling
- Products with/without GI tags
- Products with/without seasonal information

## Requirements Validated

- **Requirement 2.1**: Accept product details (name, category, price, GI tag, description)
- **Requirement 2.3**: Validate price is positive number (Property 8)
- **Requirement 2.5**: Store product with pending verification status

## Related Tasks

- Task 4.1: ✅ Create product creation endpoint (POST /products)
- Task 4.2: Property test for valid product creation
- Task 4.3: Property test for non-positive price rejection
- Task 4.4: Property test for invalid product data errors
