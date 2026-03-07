# Design Document: RootTrust Marketplace Platform

## Overview

RootTrust is an AI-powered serverless marketplace platform built entirely on AWS infrastructure that connects farmers directly with consumers while ensuring product authenticity through AI-based fraud detection. The platform addresses two critical market problems:

1. **Consumer Problem**: Receiving counterfeit or low-quality agricultural products, especially GI-tagged (Geographical Indication) items
2. **Farmer Problem**: Struggling with marketing expertise and logistics to reach consumers directly

The platform leverages Amazon Bedrock for AI capabilities including fraud detection, market price prediction, and marketing content generation. The entire system is designed to operate within a $300 AWS credit budget for over one month as a hackathon prototype.

### Key Design Principles

- **Serverless-First**: Minimize operational costs using Lambda, API Gateway, and managed services
- **AI-Driven Trust**: Use Amazon Bedrock to verify product authenticity and generate fraud risk scores
- **Cost-Optimized**: Implement caching, lifecycle policies, and on-demand pricing to stay within budget
- **Role-Based Access**: Separate farmer and consumer portals with distinct capabilities
- **Real-Time Engagement**: Live viewer counts, purchase notifications, and countdown timers
- **Value Equation Optimization**: Design UI to maximize (Dream Outcome × Likelihood) / (Time × Effort)

## Architecture

### High-Level Architecture

The RootTrust platform follows a serverless microservices architecture with the following layers:

**1. Presentation Layer**

- React-based Single Page Application (SPA)
- Hosted on AWS Amplify
- Separate views for Farmer Portal and Consumer Portal
- Responsive design for mobile and desktop

**2. API Layer**

- AWS API Gateway (REST API)
- Request validation and throttling
- CORS configuration for web access
- API key management for internal services

**3. Business Logic Layer**

- AWS Lambda functions (Node.js/Python)
- Stateless, event-driven processing
- Function-per-endpoint pattern for cost optimization
- Cold start mitigation through provisioned concurrency for critical paths

**4. AI/ML Layer**

- Amazon Bedrock for AI capabilities
- Claude or Titan models for text generation
- Custom prompt engineering for fraud detection
- Response caching to minimize API calls

**5. Data Layer**

- Amazon DynamoDB (on-demand pricing)
- Single-table design pattern for cost efficiency
- Global Secondary Indexes (GSI) for query patterns
- DynamoDB Streams for event-driven workflows

**6. Storage Layer**

- Amazon S3 for product images and documents
- S3 lifecycle policies (Standard → Standard-IA after 30 days)
- CloudFront CDN for image delivery (optional, budget permitting)

**7. Integration Layer**

- Amazon SES for email notifications
- Razorpay/Stripe webhooks for payment processing
- EventBridge for scheduled tasks (limited releases, promotions)

### Architecture Diagram Description

```
┌─────────────────────────────────────────────────────────────────┐
│                         Users (Web Browser)                      │
│                  Farmers              Consumers                  │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      AWS Amplify Hosting                         │
│                    React SPA (Frontend)                          │
│              Farmer Portal  |  Consumer Portal                   │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      AWS API Gateway                             │
│                    REST API Endpoints                            │
│         /auth  /products  /orders  /reviews  /ai                │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      AWS Lambda Functions                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │   Auth   │  │ Products │  │  Orders  │  │   AI     │       │
│  │ Handler  │  │ Handler  │  │ Handler  │  │ Handler  │       │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘       │
└────────┬───────────────┬───────────────┬───────────────┬────────┘
         │               │               │               │
         ▼               ▼               ▼               ▼
┌────────────────┐ ┌────────────────┐ ┌────────────────┐ ┌────────────────┐
│   DynamoDB     │ │   Amazon S3    │ │  Amazon SES    │ │ Amazon Bedrock │
│                │ │                │ │                │ │                │
│ • Users        │ │ • Product      │ │ • Email        │ │ • Claude/Titan │
│ • Products     │ │   Images       │ │   Notifications│ │ • Fraud        │
│ • Orders       │ │ • Invoices     │ │                │ │   Detection    │
│ • Reviews      │ │                │ │                │ │ • Content Gen  │
│ • Referrals    │ │                │ │                │ │                │
└────────────────┘ └────────────────┘ └────────────────┘ └────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────────────────┐
│                    DynamoDB Streams                             │
│              (Triggers for async processing)                    │
└────────────────────────┬───────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                  EventBridge Scheduler                           │
│        • Limited Release Expiry                                  │
│        • Promotion End Notifications                             │
│        • Review Request Emails                                   │
└─────────────────────────────────────────────────────────────────┘

External Integrations:
┌────────────────┐
│ Razorpay/Stripe│ ◄──── Payment webhooks
└────────────────┘
```

## Components and Interfaces

### Frontend Components

#### 1. Authentication Module

- **LoginForm**: Email/password authentication with role selection
- **RegistrationForm**: New user signup with farmer/consumer role choice
- **AuthContext**: React context for managing authentication state
- **ProtectedRoute**: Route wrapper for role-based access control

#### 2. Farmer Portal Components

- **ProductUploadForm**: Multi-step form for product details, images, and documentation
- **ProductListView**: Dashboard showing farmer's products with status indicators
- **AnalyticsDashboard**: Sales metrics, view counts, conversion rates
- **MarketingContentGenerator**: AI-powered content creation interface
- **PromotionManager**: Create and manage product promotions
- **LimitedReleaseCreator**: Configure time-bound exclusive offerings
- **BonusTracker**: Display current bonuses and progress

#### 3. Consumer Portal Components

- **MarketplaceBrowser**: Grid/list view of products with filters
- **ProductDetailView**: Full product information with farmer profile
- **SearchBar**: Keyword search with autocomplete
- **FilterPanel**: Category, seasonal, GI-tag, price range filters
- **ShoppingCart**: Order summary and checkout initiation
- **OrderHistory**: Past orders with tracking information
- **ReviewForm**: Rating and review submission with photo upload
- **ReferralDashboard**: Share links and reward tracking

#### 4. Shared Components

- **ProductCard**: Reusable product display with image, price, rating
- **ScarcityIndicators**: Live viewer count, stock warnings, countdown timers
- **ValueEquationDisplay**: Dream outcome, GI badge, delivery guarantees
- **NotificationCenter**: Email preference management
- **ImageUploader**: S3 direct upload with preview

### Backend Components

#### 1. Authentication Service (Lambda)

- **Function**: `auth-handler`
- **Endpoints**:
  - `POST /auth/register` - Create new user account
  - `POST /auth/login` - Authenticate user and return JWT token
  - `POST /auth/refresh` - Refresh expired JWT token
  - `GET /auth/verify` - Verify JWT token validity
- **Dependencies**: DynamoDB (Users table), SES (confirmation emails)
- **Security**: Bcrypt password hashing, JWT token generation

#### 2. Product Service (Lambda)

- **Function**: `product-handler`
- **Endpoints**:
  - `POST /products` - Create new product (farmer only)
  - `GET /products` - List products with filters and pagination
  - `GET /products/{id}` - Get product details
  - `PUT /products/{id}` - Update product (farmer only)
  - `DELETE /products/{id}` - Delete product (farmer only)
  - `POST /products/{id}/images` - Upload product images to S3
- **Dependencies**: DynamoDB (Products table), S3 (image storage), Bedrock (verification)
- **Business Logic**: Product validation, image processing, fraud detection trigger

#### 3. AI Verification Service (Lambda)

- **Function**: `ai-verification-handler`
- **Endpoints**:
  - `POST /ai/verify-product` - Analyze product for fraud detection
  - `POST /ai/predict-price` - Generate market price prediction
  - `GET /ai/verification-status/{productId}` - Check verification status
- **Dependencies**: Amazon Bedrock, DynamoDB (Products table)
- **AI Logic**:
  - Fraud risk scoring (0-100)
  - Authenticity confidence calculation
  - Market price prediction using category, GI tag, seasonal factors
  - Explanation generation

#### 4. AI Marketing Service (Lambda)

- **Function**: `ai-marketing-handler`
- **Endpoints**:
  - `POST /ai/generate-description` - Create product descriptions
  - `POST /ai/generate-names` - Suggest product names (3 variations)
  - `POST /ai/generate-social` - Create social media content
  - `POST /ai/generate-launch` - Create launch announcements
  - `POST /ai/enhance-description` - Improve farmer-provided text
- **Dependencies**: Amazon Bedrock, DynamoDB (Products table)
- **Caching**: Redis/ElastiCache or DynamoDB for response caching

#### 5. Order Service (Lambda)

- **Function**: `order-handler`
- **Endpoints**:
  - `POST /orders` - Create new order
  - `GET /orders` - List user orders
  - `GET /orders/{id}` - Get order details
  - `PUT /orders/{id}/status` - Update order status
  - `POST /orders/{id}/payment-callback` - Handle payment webhook
- **Dependencies**: DynamoDB (Orders, Transactions tables), SES (notifications)
- **Business Logic**: Order creation, payment integration, status tracking

#### 6. Payment Service (Lambda)

- **Function**: `payment-handler`
- **Endpoints**:
  - `POST /payments/initiate` - Create payment session
  - `POST /payments/webhook` - Handle Razorpay/Stripe webhooks
  - `GET /payments/{transactionId}` - Get payment status
- **Dependencies**: Razorpay/Stripe API, DynamoDB (Transactions table)
- **Security**: Webhook signature verification, idempotency keys

#### 7. Review Service (Lambda)

- **Function**: `review-handler`
- **Endpoints**:
  - `POST /reviews` - Submit product review
  - `GET /reviews/product/{productId}` - Get product reviews
  - `GET /reviews/farmer/{farmerId}` - Get farmer reviews
  - `POST /reviews/{id}/photos` - Upload review photos to S3
- **Dependencies**: DynamoDB (Reviews table), S3 (review photos)
- **Business Logic**: Rating aggregation, farmer/product score updates

#### 8. Referral Service (Lambda)

- **Function**: `referral-handler`
- **Endpoints**:
  - `POST /referrals/generate` - Create referral link
  - `GET /referrals/{code}` - Validate referral code
  - `POST /referrals/track` - Track referral conversion
  - `GET /referrals/rewards` - Get user reward balance
- **Dependencies**: DynamoDB (Referrals table)
- **Business Logic**: Unique code generation, conversion tracking, reward calculation

#### 9. Promotion Service (Lambda)

- **Function**: `promotion-handler`
- **Endpoints**:
  - `POST /promotions` - Create product promotion (farmer only)
  - `GET /promotions` - List active promotions
  - `PUT /promotions/{id}` - Update promotion
  - `DELETE /promotions/{id}` - Cancel promotion
  - `GET /promotions/{id}/metrics` - Get promotion performance
- **Dependencies**: DynamoDB (Promotions table), EventBridge (scheduling)
- **Business Logic**: Budget validation, featured placement, metrics tracking

#### 10. Limited Release Service (Lambda)

- **Function**: `limited-release-handler`
- **Endpoints**:
  - `POST /limited-releases` - Create limited release (farmer only)
  - `GET /limited-releases` - List active limited releases
  - `GET /limited-releases/{id}` - Get release details with countdown
  - `POST /limited-releases/{id}/purchase` - Purchase from limited release
- **Dependencies**: DynamoDB (LimitedReleases table), SES (notifications), EventBridge (expiry)
- **Business Logic**: Quantity tracking, expiry management, subscriber notifications

#### 11. Analytics Service (Lambda)

- **Function**: `analytics-handler`
- **Endpoints**:
  - `GET /analytics/farmer/{farmerId}` - Get farmer dashboard metrics
  - `GET /analytics/product/{productId}` - Get product performance
  - `GET /analytics/trends` - Get seasonal trend data
- **Dependencies**: DynamoDB (aggregated from Orders, Products, Reviews)
- **Business Logic**: Revenue calculation, conversion rate analysis, trend identification

#### 12. Notification Service (Lambda)

- **Function**: `notification-handler`
- **Triggered by**: DynamoDB Streams, EventBridge schedules
- **Responsibilities**:
  - Order confirmation emails
  - Payment success/failure notifications
  - Review request emails (post-delivery)
  - New product launch notifications
  - Limited release alerts
  - Promotion expiry summaries
  - Farmer bonus notifications
- **Dependencies**: Amazon SES, DynamoDB (Users, NotificationPreferences)

## Data Models

### DynamoDB Single-Table Design

To optimize costs and query performance, we use a single-table design with the following access patterns:

**Table Name**: `RootTrustData`

**Primary Key**:

- Partition Key (PK): String
- Sort Key (SK): String

**Global Secondary Indexes**:

- GSI1: GSI1PK (partition), GSI1SK (sort) - For category/seasonal queries
- GSI2: GSI2PK (partition), GSI2SK (sort) - For farmer/consumer lookups
- GSI3: GSI3PK (partition), GSI3SK (sort) - For time-based queries

### Entity Schemas

#### 1. User Entity

```json
{
  "PK": "USER#<userId>",
  "SK": "PROFILE",
  "EntityType": "User",
  "userId": "uuid-v4",
  "email": "string",
  "passwordHash": "string (bcrypt)",
  "role": "farmer | consumer",
  "firstName": "string",
  "lastName": "string",
  "phone": "string",
  "address": {
    "street": "string",
    "city": "string",
    "state": "string",
    "pincode": "string"
  },
  "createdAt": "ISO 8601 timestamp",
  "emailVerified": "boolean",
  "notificationPreferences": {
    "newProducts": "boolean",
    "promotions": "boolean",
    "orderUpdates": "boolean"
  },
  "GSI2PK": "ROLE#<role>",
  "GSI2SK": "USER#<createdAt>"
}
```

**Farmer-Specific Attributes**:

```json
{
  "farmerProfile": {
    "farmName": "string",
    "farmLocation": "string",
    "certifications": ["string"],
    "averageRating": "number (0-5)",
    "totalReviews": "number",
    "totalSales": "number",
    "consecutiveSalesStreak": "number",
    "bonusesEarned": "number",
    "featuredStatus": "boolean"
  }
}
```

**Consumer-Specific Attributes**:

```json
{
  "consumerProfile": {
    "referralCode": "string",
    "referralRewardBalance": "number",
    "totalOrders": "number",
    "followedFarmers": ["farmerId"]
  }
}
```

#### 2. Product Entity

```json
{
  "PK": "PRODUCT#<productId>",
  "SK": "METADATA",
  "EntityType": "Product",
  "productId": "uuid-v4",
  "farmerId": "uuid-v4",
  "name": "string",
  "category": "string (vegetables|fruits|grains|spices|dairy)",
  "description": "string",
  "price": "number (positive)",
  "unit": "string (kg|liter|dozen|piece)",
  "giTag": {
    "hasTag": "boolean",
    "tagName": "string",
    "region": "string"
  },
  "seasonal": {
    "isSeasonal": "boolean",
    "seasonStart": "ISO 8601 date",
    "seasonEnd": "ISO 8601 date"
  },
  "images": [
    {
      "url": "S3 URL",
      "isPrimary": "boolean"
    }
  ],
  "invoiceDocumentUrl": "S3 URL",
  "verificationStatus": "pending | approved | flagged | rejected",
  "fraudRiskScore": "number (0-100)",
  "authenticityConfidence": "number (0-100)",
  "aiExplanation": "string",
  "predictedMarketPrice": "number",
  "quantity": "number",
  "averageRating": "number (0-5)",
  "totalReviews": "number",
  "totalSales": "number",
  "viewCount": "number",
  "currentViewers": "number",
  "recentPurchaseCount": "number (last 24h)",
  "createdAt": "ISO 8601 timestamp",
  "updatedAt": "ISO 8601 timestamp",
  "GSI1PK": "CATEGORY#<category>",
  "GSI1SK": "PRODUCT#<createdAt>",
  "GSI2PK": "FARMER#<farmerId>",
  "GSI2SK": "PRODUCT#<createdAt>",
  "GSI3PK": "STATUS#<verificationStatus>",
  "GSI3SK": "PRODUCT#<createdAt>"
}
```

#### 3. Order Entity

```json
{
  "PK": "ORDER#<orderId>",
  "SK": "METADATA",
  "EntityType": "Order",
  "orderId": "uuid-v4",
  "consumerId": "uuid-v4",
  "farmerId": "uuid-v4",
  "productId": "uuid-v4",
  "productName": "string",
  "quantity": "number",
  "unitPrice": "number",
  "totalAmount": "number",
  "status": "pending | confirmed | processing | shipped | delivered | cancelled | failed",
  "paymentStatus": "pending | completed | failed | refunded",
  "transactionId": "string",
  "deliveryAddress": {
    "street": "string",
    "city": "string",
    "state": "string",
    "pincode": "string"
  },
  "estimatedDeliveryDate": "ISO 8601 date",
  "actualDeliveryDate": "ISO 8601 date",
  "referralCode": "string (optional)",
  "createdAt": "ISO 8601 timestamp",
  "updatedAt": "ISO 8601 timestamp",
  "GSI2PK": "CONSUMER#<consumerId>",
  "GSI2SK": "ORDER#<createdAt>",
  "GSI3PK": "FARMER#<farmerId>",
  "GSI3SK": "ORDER#<createdAt>"
}
```

#### 4. Transaction Entity

```json
{
  "PK": "TRANSACTION#<transactionId>",
  "SK": "METADATA",
  "EntityType": "Transaction",
  "transactionId": "string (from payment gateway)",
  "orderId": "uuid-v4",
  "amount": "number",
  "currency": "INR",
  "paymentMethod": "upi | card | netbanking",
  "paymentGateway": "razorpay | stripe",
  "status": "initiated | success | failed | refunded",
  "gatewayResponse": "object",
  "createdAt": "ISO 8601 timestamp",
  "completedAt": "ISO 8601 timestamp",
  "GSI2PK": "ORDER#<orderId>",
  "GSI2SK": "TRANSACTION#<createdAt>"
}
```

#### 5. Review Entity

```json
{
  "PK": "PRODUCT#<productId>",
  "SK": "REVIEW#<reviewId>",
  "EntityType": "Review",
  "reviewId": "uuid-v4",
  "productId": "uuid-v4",
  "farmerId": "uuid-v4",
  "consumerId": "uuid-v4",
  "orderId": "uuid-v4",
  "rating": "number (1-5)",
  "reviewText": "string",
  "photos": [
    {
      "url": "S3 URL",
      "caption": "string"
    }
  ],
  "helpful": "number (count)",
  "createdAt": "ISO 8601 timestamp",
  "GSI2PK": "FARMER#<farmerId>",
  "GSI2SK": "REVIEW#<createdAt>",
  "GSI3PK": "CONSUMER#<consumerId>",
  "GSI3SK": "REVIEW#<createdAt>"
}
```

#### 6. Referral Entity

```json
{
  "PK": "REFERRAL#<referralCode>",
  "SK": "METADATA",
  "EntityType": "Referral",
  "referralCode": "string (unique)",
  "referrerId": "uuid-v4",
  "productId": "uuid-v4",
  "conversions": [
    {
      "referredUserId": "uuid-v4",
      "orderId": "uuid-v4",
      "rewardAmount": "number",
      "convertedAt": "ISO 8601 timestamp"
    }
  ],
  "totalConversions": "number",
  "totalRewards": "number",
  "createdAt": "ISO 8601 timestamp",
  "GSI2PK": "REFERRER#<referrerId>",
  "GSI2SK": "REFERRAL#<createdAt>"
}
```

#### 7. Promotion Entity

```json
{
  "PK": "PROMOTION#<promotionId>",
  "SK": "METADATA",
  "EntityType": "Promotion",
  "promotionId": "uuid-v4",
  "farmerId": "uuid-v4",
  "productId": "uuid-v4",
  "budget": "number",
  "duration": "number (days)",
  "status": "active | paused | completed | cancelled",
  "startDate": "ISO 8601 timestamp",
  "endDate": "ISO 8601 timestamp",
  "metrics": {
    "views": "number",
    "clicks": "number",
    "conversions": "number",
    "spent": "number"
  },
  "aiGeneratedAdCopy": "string",
  "createdAt": "ISO 8601 timestamp",
  "GSI2PK": "FARMER#<farmerId>",
  "GSI2SK": "PROMOTION#<startDate>",
  "GSI3PK": "STATUS#active",
  "GSI3SK": "PROMOTION#<endDate>"
}
```

#### 8. Limited Release Entity

```json
{
  "PK": "LIMITED_RELEASE#<releaseId>",
  "SK": "METADATA",
  "EntityType": "LimitedRelease",
  "releaseId": "uuid-v4",
  "farmerId": "uuid-v4",
  "productId": "uuid-v4",
  "releaseName": "string",
  "quantityLimit": "number (positive integer)",
  "quantityRemaining": "number",
  "duration": "number (1-30 days)",
  "startDate": "ISO 8601 timestamp",
  "endDate": "ISO 8601 timestamp",
  "status": "scheduled | active | sold_out | expired",
  "subscriberNotificationsSent": "boolean",
  "createdAt": "ISO 8601 timestamp",
  "GSI2PK": "FARMER#<farmerId>",
  "GSI2SK": "RELEASE#<startDate>",
  "GSI3PK": "STATUS#<status>",
  "GSI3SK": "RELEASE#<endDate>"
}
```

#### 9. Notification Preference Entity

```json
{
  "PK": "USER#<userId>",
  "SK": "NOTIFICATIONS",
  "EntityType": "NotificationPreference",
  "userId": "uuid-v4",
  "emailNotifications": {
    "newProducts": "boolean",
    "promotions": "boolean",
    "orderUpdates": "boolean",
    "reviewRequests": "boolean",
    "limitedReleases": "boolean",
    "farmerBonuses": "boolean"
  },
  "unsubscribedAt": "ISO 8601 timestamp (null if subscribed)",
  "updatedAt": "ISO 8601 timestamp"
}
```

### S3 Bucket Structure

**Bucket Name**: `roottrust-assets-<environment>`

**Folder Structure**:

```
/products/
  /<productId>/
    /images/
      primary.jpg
      gallery-1.jpg
      gallery-2.jpg
    /documents/
      invoice.pdf

/reviews/
  /<reviewId>/
    /photos/
      photo-1.jpg
      photo-2.jpg

/temp-uploads/
  /<uploadId>/
    file.jpg  (expires after 24h)
```

**Lifecycle Policies**:

- Standard storage for first 30 days
- Transition to Standard-IA after 30 days
- Delete temp-uploads after 1 day

## Correctness Properties

_A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees._

### Authentication and User Management Properties

#### Property 1: User Registration Creates Valid Accounts

_For any_ valid email, password, and role selection (farmer or consumer), when a new user registers, the system should create an account record in DynamoDB with the correct role, hashed password, and all required profile fields.

**Validates: Requirements 1.1, 1.4**

#### Property 2: Valid Credentials Authenticate Successfully

_For any_ registered user with valid credentials, authentication should succeed and return a JWT token containing the correct user ID and role claims.

**Validates: Requirements 1.2**

#### Property 3: Invalid Credentials Are Rejected

_For any_ authentication attempt with invalid credentials (wrong password, non-existent email, or malformed input), the system should reject authentication and return a descriptive error message without revealing whether the email exists.

**Validates: Requirements 1.3**

#### Property 4: Registration Triggers Confirmation Email

_For any_ successful user registration, the system should invoke the email service with a confirmation email containing the user's email address and a verification link.

**Validates: Requirements 1.5**

#### Property 5: Passwords Are Never Stored in Plaintext

_For any_ user record in DynamoDB, the password field should be a bcrypt hash, not the original plaintext password.

**Validates: Requirements 1.4**

### Product Management Properties

#### Property 6: Valid Product Data Is Accepted and Stored

_For any_ valid product submission with name, category, positive price, GI tag status, description, and invoice data, the system should create a product record in DynamoDB with all provided fields and pending verification status.

**Validates: Requirements 2.1, 2.5**

#### Property 7: Product Images Are Stored in S3 and Linked

_For any_ product image upload, the system should store the image in S3 under the correct product folder structure and associate the S3 URL with the product record in DynamoDB.

**Validates: Requirements 2.2**

#### Property 8: Non-Positive Prices Are Rejected

_For any_ product submission with a price that is zero, negative, or not a number, the system should reject the submission and return a validation error.

**Validates: Requirements 2.3**

#### Property 9: Product Data Round-Trip Preservation

_For any_ valid Product object, serializing to JSON then parsing back to a Product object should produce an equivalent object with all fields preserved.

**Validates: Requirements 20.5**

#### Property 10: Invalid Product Data Returns Descriptive Errors

_For any_ product submission with invalid fields (missing required fields, wrong types, or constraint violations), the system should return validation errors that specifically identify which fields are invalid and why.

**Validates: Requirements 20.2**

### AI Verification Properties

#### Property 11: Product Verification Invokes Bedrock

_For any_ product submitted for verification, the system should invoke Amazon Bedrock with the product details (name, category, price, GI tag, description, invoice data) to perform fraud analysis.

**Validates: Requirements 3.1**

#### Property 12: Market Price Prediction Is Generated

_For any_ product, the Market Price Predictor should generate a predicted market price based on the product's category, GI tag status, and seasonal factors, returning a positive number.

**Validates: Requirements 3.2**

#### Property 13: Fraud Risk Score Is Within Valid Range

_For any_ product verification, the calculated Fraud Risk Score should be a number between 0 and 100 (inclusive).

**Validates: Requirements 3.3**

#### Property 14: Authenticity Confidence Is a Valid Percentage

_For any_ product verification, the Authenticity Confidence should be a number between 0 and 100 (inclusive), representing a percentage.

**Validates: Requirements 3.4**

#### Property 15: Verification Generates Non-Empty Explanation

_For any_ product verification, the system should generate an AI explanation string that is non-empty and describes the reasoning behind the fraud risk assessment.

**Validates: Requirements 3.5**

#### Property 16: Verification Status Matches Fraud Risk Score

_For any_ product verification, if the Fraud Risk Score exceeds 70, the product status should be set to "flagged", and if the score is 70 or below, the status should be set to "approved".

**Validates: Requirements 3.6, 3.7**

### Marketplace Browsing and Search Properties

#### Property 17: Only Approved Products Appear in Marketplace

_For any_ marketplace query, the returned products should only include those with verification status "approved", excluding pending, flagged, and rejected products.

**Validates: Requirements 4.1**

#### Property 18: Category Filter Returns Matching Products

_For any_ category filter applied to the marketplace, all returned products should have a category field that matches the filter value.

**Validates: Requirements 4.2**

#### Property 19: Seasonal Filter Returns In-Season Products

_For any_ seasonal filter applied with a reference date, all returned products should have seasonal date ranges that include the reference date (seasonStart ≤ date ≤ seasonEnd).

**Validates: Requirements 4.3**

#### Property 20: GI Badge Display Matches GI Tag Presence

_For any_ product displayed in the marketplace or detail view, a verified GI badge should be shown if and only if the product has giTag.hasTag set to true.

**Validates: Requirements 4.4, 9.2**

#### Property 21: Keyword Search Matches Name or Description

_For any_ keyword search query, all returned products should contain the search term (case-insensitive) in either the product name or description fields.

**Validates: Requirements 4.5**

#### Property 22: Product Listings Include Required Display Fields

_For any_ product in marketplace listing view, the displayed data should include product images, price, farmer name, and rating.

**Validates: Requirements 4.6**

#### Property 23: Product Detail View Includes Complete Information

_For any_ product detail view, the displayed data should include full description, all images, price, GI tag status, authenticity confidence score, farmer profile with ratings, and customer reviews.

**Validates: Requirements 5.1, 5.2, 5.3, 5.4**

#### Property 24: Review Photos Display When Present

_For any_ product with customer reviews, if a review has associated photos, those photos should be displayed in the review; if no photos exist, no photo section should appear.

**Validates: Requirements 5.5**

### Order and Payment Properties

#### Property 25: Purchase Initiation Creates Order Record

_For any_ valid purchase request (consumer ID, product ID, quantity), the system should create an order record in DynamoDB with status "pending" and all order details.

**Validates: Requirements 6.1**

#### Property 26: Purchase Redirects to Payment Gateway

_For any_ order creation, the system should generate a payment session with the payment gateway and return a redirect URL to the consumer.

**Validates: Requirements 6.2**

#### Property 27: Payment Outcome Updates Order Status Correctly

_For any_ payment callback, if payment succeeds, the order status should update to "confirmed" and a confirmation email should be sent; if payment fails, the order status should update to "failed" and a failure notification should be sent.

**Validates: Requirements 6.3, 6.4**

#### Property 28: Orders Include Estimated Delivery Date

_For any_ order record, an estimated delivery date should be calculated and stored based on the current date plus delivery time for the product's region.

**Validates: Requirements 6.5, 9.4**

#### Property 29: Order Status Changes Trigger Notifications

_For any_ order status change (pending → confirmed, confirmed → shipped, shipped → delivered), the system should send an email notification to the consumer with the updated status.

**Validates: Requirements 6.6**

#### Property 30: Payment Processing Returns Transaction ID

_For any_ payment processed through the payment gateway, the system should receive and store a unique transaction ID linking the payment to the order.

**Validates: Requirements 7.3**

#### Property 31: Transactions Are Persisted with Order Association

_For any_ payment transaction, the system should store a transaction record in DynamoDB with the transaction ID, order ID, amount, payment method, status, and timestamp.

**Validates: Requirements 7.4**

#### Property 32: Successful Payments Notify Farmers

_For any_ successful payment, the system should send an email notification to the farmer associated with the product, informing them of the new order.

**Validates: Requirements 7.5**

### AI Marketing Content Properties

#### Property 33: Marketing Content Generation Invokes Bedrock

_For any_ marketing content request (product description, social media text, launch announcement), the system should invoke Amazon Bedrock with the product details and content type to generate the requested content.

**Validates: Requirements 8.1, 8.3, 8.4**

#### Property 34: Generated Descriptions Emphasize Value Elements

_For any_ AI-generated product description, the content should include language emphasizing dream outcome (benefits, results) and perceived likelihood (trust signals, guarantees).

**Validates: Requirements 8.2**

#### Property 35: Seasonal High-Demand Generates Urgency Messaging

_For any_ product marked as seasonal with current date within 7 days of season end, AI-generated marketing content should include urgency-focused language (limited time, ending soon, last chance).

**Validates: Requirements 8.5**

#### Property 36: Farmers Can Edit AI-Generated Content

_For any_ AI-generated marketing content, the farmer should be able to modify the text before publishing, and the modified version should be stored instead of the original AI output.

**Validates: Requirements 8.6**

#### Property 37: AI Suggests Three Product Name Variations

_For any_ product name generation request, the AI Marketing Engine should return exactly three name variations, each emphasizing a different value proposition (quality, origin, benefit).

**Validates: Requirements 18.2**

#### Property 38: AI-Enhanced Descriptions Include Sensory Language

_For any_ farmer-provided description enhanced by AI, the output should contain sensory language (taste, texture, appearance descriptors) and benefit statements while preserving factual accuracy.

**Validates: Requirements 18.3, 18.5**

#### Property 39: Farmers Can Select from AI Suggestions or Original

_For any_ AI-generated name or description suggestions, the farmer should be able to choose one of the AI options or keep their original text, and the selected version should be used for the product.

**Validates: Requirements 18.4**

### Value Equation and Engagement Properties

#### Property 40: Products Display Dream Outcome Statements

_For any_ product displayed to consumers, the UI should include a dream outcome statement describing the benefit or result the consumer will achieve.

**Validates: Requirements 9.1**

#### Property 41: Products Display Guaranteed Delivery Messaging

_For any_ product displayed to consumers, the UI should include guaranteed delivery messaging to increase perceived likelihood of success.

**Validates: Requirements 9.3**

#### Property 42: Value Equation Is Calculated for Products

_For any_ product, the system should calculate a value equation score based on (Dream Outcome × Likelihood) / (Time × Effort), where likelihood factors include GI tag presence and authenticity confidence, time is estimated delivery days, and effort is checkout complexity.

**Validates: Requirements 9.6**

#### Property 43: Limited Quantity Products Display Remaining Stock

_For any_ product with quantity less than or equal to 50, the marketplace should display the remaining quantity count to create scarcity.

**Validates: Requirements 10.1**

#### Property 44: Seasonal Products Display Countdown Timer

_For any_ seasonal product with a defined season end date, the marketplace should display a countdown showing days remaining until the season ends.

**Validates: Requirements 10.2**

#### Property 45: Concurrent Viewers Are Tracked and Displayed

_For any_ product being viewed by multiple users simultaneously, the system should track the current viewer count and display it on the product page.

**Validates: Requirements 10.3**

#### Property 46: Recent Purchase Count Is Displayed

_For any_ product with purchases in the last 24 hours, the marketplace should display the count of recent purchases to create social proof.

**Validates: Requirements 10.4**

#### Property 47: Low Stock Warning Appears Below Threshold

_For any_ product with quantity less than 10, the marketplace should display a low stock warning message.

**Validates: Requirements 10.5**

### Limited Release Properties

#### Property 48: Valid Limited Releases Are Created

_For any_ valid limited release submission with release name, positive integer quantity limit, and duration between 1-30 days, the system should create a limited release record with status "scheduled" or "active".

**Validates: Requirements 11.1**

#### Property 49: Non-Positive Quantity Limits Are Rejected

_For any_ limited release submission with quantity limit that is zero, negative, or not an integer, the system should reject the submission with a validation error.

**Validates: Requirements 11.2**

#### Property 50: Duration Outside Valid Range Is Rejected

_For any_ limited release submission with duration less than 1 day or greater than 30 days, the system should reject the submission with a validation error.

**Validates: Requirements 11.3**

#### Property 51: Limited Release Creation Notifies Subscribers

_For any_ newly created limited release, the system should send email notifications to all consumers who have opted in to limited release notifications.

**Validates: Requirements 11.4**

#### Property 52: Sold Out Limited Releases Display Correct Status

_For any_ limited release where quantity remaining reaches zero, the status should update to "sold_out" and the marketplace should display sold out messaging.

**Validates: Requirements 11.5**

#### Property 53: Expired Limited Releases Are Delisted

_For any_ limited release where the current time exceeds the end date, the system should automatically update the status to "expired" and remove the product from marketplace listings.

**Validates: Requirements 11.6**

### Farmer Incentive Properties

#### Property 54: Sales Streak Bonus Awards at Threshold

_For any_ farmer who completes 10 consecutive sales where all associated reviews have ratings ≥ 3 stars (no negative reviews), the system should award a sales streak bonus and update the farmer's bonus count.

**Validates: Requirements 12.1**

#### Property 55: High Authenticity Scores Grant Featured Placement

_For any_ farmer whose products have an average authenticity confidence score above 90%, the system should grant featured status, causing their products to appear in featured sections of the marketplace.

**Validates: Requirements 12.2**

#### Property 56: Bonus Status and Progress Are Displayed

_For any_ farmer viewing their dashboard, the system should display current bonus status, total bonuses earned, and progress toward the next reward (e.g., "7/10 sales toward streak bonus").

**Validates: Requirements 12.3**

#### Property 57: Bonus Awards Trigger Notifications

_For any_ farmer who earns a bonus (sales streak, featured placement, or other reward), the system should send an email notification describing the bonus earned.

**Validates: Requirements 12.4**

#### Property 58: Total Bonuses Are Tracked Accurately

_For any_ farmer, the total bonuses earned should equal the sum of all individual bonus awards recorded in the system.

**Validates: Requirements 12.5**

### Referral System Properties

#### Property 59: Products Display Share Button with Referral Link

_For any_ product viewed by a consumer, the UI should display a share button that generates a unique referral link containing the consumer's referral code and product ID.

**Validates: Requirements 13.1**

#### Property 60: Referral Codes Are Unique per User-Product Combination

_For any_ two referral link generation requests, if they have different user-product combinations, the generated referral codes should be unique (no collisions).

**Validates: Requirements 13.2**

#### Property 61: Referral Conversions Credit Referrers

_For any_ order completed using a valid referral code, the system should credit the referrer's reward balance with the configured referral reward amount and record the conversion.

**Validates: Requirements 13.3**

#### Property 62: Referral Rewards Are Displayed

_For any_ consumer viewing their referral dashboard, the system should display their current reward balance and available redemption options.

**Validates: Requirements 13.4**

#### Property 63: Referral Metrics Are Persisted

_For any_ referral conversion (referred user completes purchase), the system should store conversion metrics in DynamoDB including referrer ID, referred user ID, order ID, reward amount, and timestamp.

**Validates: Requirements 13.5**

### Review and Rating Properties

#### Property 64: Delivered Orders Trigger Review Requests

_For any_ order that transitions to "delivered" status, the system should send a review request email to the consumer within 24 hours of delivery.

**Validates: Requirements 14.1**

#### Property 65: Rating Submissions Are Within Valid Range

_For any_ review submission, the rating should be validated to be an integer between 1 and 5 (inclusive); values outside this range should be rejected.

**Validates: Requirements 14.2**

#### Property 66: Review Text and Photos Are Stored

_For any_ review submission with text and/or photos, the system should store the review text in DynamoDB and upload photos to S3, associating the S3 URLs with the review record.

**Validates: Requirements 14.3, 14.4**

#### Property 67: Reviews Update Product Average Rating

_For any_ review submitted for a product, the system should recalculate the product's average rating as the mean of all review ratings for that product, and update the product record.

**Validates: Requirements 14.5**

#### Property 68: Reviews Update Farmer Average Rating

_For any_ review submitted for a product, the system should recalculate the farmer's average rating as the mean of all review ratings for all products by that farmer, and update the farmer profile.

**Validates: Requirements 14.6**

#### Property 69: Reviews Are Displayed in Reverse Chronological Order

_For any_ list of reviews displayed for a product or farmer, the reviews should be sorted by creation timestamp in descending order (most recent first).

**Validates: Requirements 14.7**

### Promotion Properties

#### Property 70: Promotions Require Sufficient Balance

_For any_ promotion creation request, if the promotion budget exceeds the farmer's account balance, the system should reject the request with an insufficient balance error.

**Validates: Requirements 15.2**

#### Property 71: Active Promotions Appear in Featured Sections

_For any_ promotion with status "active", the associated product should appear in featured sections of the marketplace with promoted/boosted visual indicators.

**Validates: Requirements 15.3**

#### Property 72: Promotions Generate AI Ad Copy

_For any_ newly created promotion, the AI Marketing Engine should generate promotional ad copy optimized for the product and store it with the promotion record.

**Validates: Requirements 15.4**

#### Property 73: Promotion Metrics Are Tracked

_For any_ active promotion, the system should track and display metrics including view count, click count, and conversion count.

**Validates: Requirements 15.5**

#### Property 74: Expired Promotions Send Summary Reports

_For any_ promotion that reaches its end date or is manually ended, the system should send an email to the farmer with a summary report including total views, clicks, conversions, and amount spent.

**Validates: Requirements 15.6**

### Notification Properties

#### Property 75: New Product Launches Notify Subscribers

_For any_ new product that transitions from pending to approved status, the system should send email notifications to all consumers who have opted in to new product notifications.

**Validates: Requirements 16.2**

#### Property 76: Followed Farmers' Products Notify Followers

_For any_ new product created by a farmer, the system should send email notifications to all consumers who follow that farmer.

**Validates: Requirements 16.3**

#### Property 77: Notification Preferences Can Be Updated

_For any_ consumer, the system should allow updating notification preferences (enabling/disabling specific notification types), and the updated preferences should be persisted and respected for future notifications.

**Validates: Requirements 16.4**

#### Property 78: Unsubscribed Users Receive No Marketing Emails

_For any_ consumer who has unsubscribed from marketing emails, the system should not send promotional, new product, or limited release notifications, but should still send transactional emails (order confirmations, shipping updates).

**Validates: Requirements 16.5**

### Analytics Properties

#### Property 79: Monthly Revenue Is Calculated Correctly

_For any_ farmer viewing analytics for a given month, the displayed total sales revenue should equal the sum of all order amounts for orders with status "delivered" where the order date falls within that month.

**Validates: Requirements 17.1**

#### Property 80: Conversion Rates Are Calculated Accurately

_For any_ product, the conversion rate should be calculated as (total orders / total views) × 100, and should be a percentage between 0 and 100.

**Validates: Requirements 17.2**

#### Property 81: Product Ratings and Review Counts Are Aggregated

_For any_ product in the analytics dashboard, the displayed average rating should match the product's calculated average from all reviews, and the review count should match the total number of reviews for that product.

**Validates: Requirements 17.3**

#### Property 82: Top Products Are Ranked by Revenue

_For any_ farmer's analytics dashboard showing top-performing products, the products should be sorted in descending order by total revenue (sum of all order amounts for that product).

**Validates: Requirements 17.5**

### Infrastructure and Cost Optimization Properties

#### Property 83: S3 Images Transition to Standard-IA After 30 Days

_For any_ product image stored in S3, the storage class should automatically transition from Standard to Standard-IA after 30 days based on the configured lifecycle policy.

**Validates: Requirements 19.3**

#### Property 84: Bedrock Requests Are Cached

_For any_ identical Bedrock request (same product details, same operation type) made within the cache TTL period, the system should return the cached response without invoking Bedrock again.

**Validates: Requirements 19.4**

#### Property 85: Cost Alerts Trigger at Budget Thresholds

_For any_ day where cumulative AWS costs exceed 80% of the monthly budget ($240 of $300), the system should send an alert notification to the platform administrators.

**Validates: Requirements 19.6**

## Error Handling

### Error Categories and Strategies

#### 1. Validation Errors (4xx Client Errors)

**Scenarios**:

- Invalid input data (negative prices, empty required fields)
- Authentication failures (invalid credentials, expired tokens)
- Authorization failures (consumer trying to access farmer endpoints)
- Resource not found (non-existent product ID, order ID)
- Business rule violations (insufficient balance, out of stock)

**Handling Strategy**:

- Return HTTP 400 (Bad Request) for validation errors
- Return HTTP 401 (Unauthorized) for authentication failures
- Return HTTP 403 (Forbidden) for authorization failures
- Return HTTP 404 (Not Found) for missing resources
- Return HTTP 409 (Conflict) for business rule violations
- Include descriptive error messages with field-level details
- Use consistent error response format:

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

#### 2. External Service Errors (5xx Server Errors)

**Scenarios**:

- Amazon Bedrock API failures or timeouts
- Payment gateway (Razorpay/Stripe) unavailability
- S3 upload failures
- DynamoDB throttling or service errors
- SES email delivery failures

**Handling Strategy**:

- Implement exponential backoff retry logic (3 attempts with 1s, 2s, 4s delays)
- Return HTTP 503 (Service Unavailable) for temporary failures
- Return HTTP 500 (Internal Server Error) for unexpected failures
- Log detailed error information for debugging
- For critical operations (payments), implement idempotency keys
- For non-critical operations (emails), queue for retry via DynamoDB Streams
- Graceful degradation: if Bedrock fails, allow manual verification

#### 3. Data Consistency Errors

**Scenarios**:

- Concurrent updates to product quantity (race conditions)
- Order creation with out-of-stock products
- Referral code collisions
- Rating calculation inconsistencies

**Handling Strategy**:

- Use DynamoDB conditional writes with version numbers or timestamps
- Implement optimistic locking for inventory updates
- Use DynamoDB transactions for multi-item operations (order + inventory update)
- Validate product availability immediately before order creation
- Implement unique constraints via conditional PutItem operations

#### 4. Rate Limiting and Throttling

**Scenarios**:

- API Gateway throttling (default 10,000 requests/second)
- DynamoDB throttling on hot partitions
- Bedrock rate limits (varies by model)
- Payment gateway rate limits

**Handling Strategy**:

- Implement API Gateway usage plans with per-user rate limits
- Use DynamoDB on-demand pricing to handle burst traffic
- Implement request queuing for Bedrock calls using SQS
- Cache Bedrock responses aggressively (24-hour TTL for fraud scores)
- Return HTTP 429 (Too Many Requests) with Retry-After header

#### 5. Security Errors

**Scenarios**:

- SQL injection attempts (not applicable with DynamoDB)
- XSS attacks in user-generated content
- CSRF attacks on state-changing operations
- Unauthorized file uploads (malicious files)
- JWT token tampering

**Handling Strategy**:

- Sanitize all user input before storage and display
- Validate JWT signatures and expiration on every request
- Implement CORS policies restricting origins
- Validate file types and sizes for uploads (images only, max 5MB)
- Use S3 pre-signed URLs with expiration for uploads
- Implement Content Security Policy (CSP) headers
- Log security events for monitoring

#### 6. Business Logic Errors

**Scenarios**:

- Attempting to review a product not purchased
- Farmer trying to promote another farmer's product
- Consumer trying to purchase their own product
- Duplicate review submissions
- Referral self-referral attempts

**Handling Strategy**:

- Validate business rules before processing operations
- Return HTTP 422 (Unprocessable Entity) for business logic violations
- Provide clear error messages explaining the violation
- Log business logic errors for analytics

### Error Monitoring and Alerting

**CloudWatch Integration**:

- Log all errors to CloudWatch Logs with structured JSON format
- Create CloudWatch Alarms for:
  - Lambda function error rates > 5%
  - API Gateway 5xx error rates > 1%
  - DynamoDB throttling events
  - Bedrock API failures
  - Payment processing failures
- Set up SNS notifications for critical errors

**Error Metrics**:

- Track error rates by endpoint and error type
- Monitor P95 and P99 latencies for all operations
- Track Bedrock cache hit rates
- Monitor payment success/failure rates

## Testing Strategy

### Dual Testing Approach

The RootTrust platform requires both unit testing and property-based testing to ensure comprehensive correctness:

- **Unit Tests**: Verify specific examples, edge cases, error conditions, and integration points
- **Property Tests**: Verify universal properties across all inputs through randomized testing

Both approaches are complementary and necessary. Unit tests catch concrete bugs in specific scenarios, while property tests verify general correctness across the input space.

### Property-Based Testing Configuration

**Framework Selection**:

- **JavaScript/Node.js**: Use `fast-check` library for Lambda functions
- **Python**: Use `hypothesis` library if any Lambda functions are written in Python
- **Frontend (React)**: Use `fast-check` with Jest for component testing

**Test Configuration**:

- Minimum 100 iterations per property test (due to randomization)
- Each property test must reference its design document property
- Tag format: `Feature: roottrust-marketplace, Property {number}: {property_text}`

**Example Property Test Structure**:

```javascript
// Feature: roottrust-marketplace, Property 1: User Registration Creates Valid Accounts
describe("Property 1: User Registration", () => {
  it("should create valid accounts for any valid email, password, and role", async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.emailAddress(),
        fc.string({ minLength: 8, maxLength: 128 }),
        fc.constantFrom("farmer", "consumer"),
        async (email, password, role) => {
          const result = await registerUser({ email, password, role });

          expect(result.userId).toBeDefined();
          expect(result.role).toBe(role);

          const user = await getUserFromDB(result.userId);
          expect(user.email).toBe(email);
          expect(user.passwordHash).not.toBe(password); // bcrypt hash
          expect(user.role).toBe(role);
        },
      ),
      { numRuns: 100 },
    );
  });
});
```

### Unit Testing Strategy

**Test Coverage Goals**:

- Minimum 80% code coverage for Lambda functions
- 100% coverage for critical paths (authentication, payments, fraud detection)
- Focus on edge cases and error conditions

**Unit Test Categories**:

1. **Authentication Tests**:
   - Valid registration with farmer and consumer roles
   - Login with correct credentials
   - Login with incorrect password
   - Login with non-existent email
   - JWT token generation and validation
   - Token expiration handling

2. **Product Management Tests**:
   - Product creation with all required fields
   - Product creation with missing required fields
   - Product creation with negative price
   - Product creation without images
   - Image upload to S3
   - Product JSON serialization/deserialization

3. **AI Verification Tests**:
   - Bedrock invocation with product details
   - Fraud score calculation within 0-100 range
   - Product flagging when score > 70
   - Product approval when score ≤ 70
   - Market price prediction generation
   - Bedrock response caching

4. **Order and Payment Tests**:
   - Order creation with valid data
   - Payment gateway redirect generation
   - Payment success webhook handling
   - Payment failure webhook handling
   - Order status transitions
   - Email notifications on status changes

5. **Review and Rating Tests**:
   - Review submission with rating 1-5
   - Review submission with rating outside range (should fail)
   - Product average rating calculation
   - Farmer average rating calculation
   - Review photo upload to S3

6. **Limited Release Tests**:
   - Limited release creation with valid duration (1-30 days)
   - Limited release creation with duration < 1 (should fail)
   - Limited release creation with duration > 30 (should fail)
   - Quantity depletion and sold out status
   - Expiry handling and delisting

7. **Referral Tests**:
   - Referral code generation uniqueness
   - Referral conversion tracking
   - Reward credit on successful referral
   - Self-referral prevention

8. **Error Handling Tests**:
   - DynamoDB throttling retry logic
   - Bedrock API failure handling
   - Payment gateway timeout handling
   - S3 upload failure handling
   - Invalid JWT token rejection

### Integration Testing

**API Integration Tests**:

- Test complete request/response flows through API Gateway → Lambda → DynamoDB
- Use LocalStack or DynamoDB Local for local testing
- Mock external services (Bedrock, Razorpay, SES) using libraries like `nock` or `aws-sdk-mock`

**End-to-End Tests**:

- User registration → product upload → verification → marketplace listing → purchase flow
- Farmer creates limited release → consumer receives notification → purchase → review
- Referral link generation → referred user purchase → reward credit

### Frontend Testing

**Component Tests**:

- React component rendering with various props
- User interaction handling (clicks, form submissions)
- State management (React hooks, context)
- API call mocking and response handling

**Property-Based Component Tests**:

- ProductCard renders correctly for any valid product data
- FilterPanel filters products correctly for any filter combination
- SearchBar returns matching products for any search query

### Performance Testing

**Load Testing**:

- Simulate 100 concurrent users browsing marketplace
- Simulate 50 concurrent product uploads
- Simulate 20 concurrent orders with payment processing
- Measure Lambda cold start times and optimize

**Cost Testing**:

- Monitor AWS costs during load testing
- Verify Bedrock caching reduces API calls by >80%
- Verify S3 lifecycle policies transition images correctly
- Ensure daily costs stay under $10 ($300/30 days)

### Security Testing

**Vulnerability Testing**:

- Test for XSS vulnerabilities in user-generated content
- Test for authentication bypass attempts
- Test for authorization violations (consumer accessing farmer endpoints)
- Test for file upload vulnerabilities (malicious files)
- Test for JWT token tampering

**Penetration Testing**:

- Attempt SQL injection (should be impossible with DynamoDB)
- Attempt CSRF attacks on state-changing operations
- Attempt rate limit bypass
- Attempt unauthorized data access

### Continuous Integration

**CI/CD Pipeline**:

- Run all unit tests on every commit
- Run property tests on every pull request
- Run integration tests before deployment
- Deploy to staging environment for manual testing
- Deploy to production after approval

**Test Automation**:

- Use GitHub Actions or AWS CodePipeline
- Fail builds on test failures or coverage drops
- Generate test coverage reports
- Send notifications on test failures

### Test Data Management

**Test Data Generation**:

- Use `fast-check` generators for property tests
- Use factory functions for unit test data
- Seed test database with realistic data for integration tests

**Test Data Cleanup**:

- Clean up DynamoDB test data after each test
- Clean up S3 test uploads after each test
- Use separate AWS accounts or resource prefixes for testing

## API Specifications

### Authentication Endpoints

#### POST /auth/register

**Description**: Create new user account  
**Request Body**:

```json
{
  "email": "string",
  "password": "string (min 8 chars)",
  "role": "farmer | consumer",
  "firstName": "string",
  "lastName": "string",
  "phone": "string"
}
```

**Response**: `201 Created`

```json
{
  "userId": "uuid",
  "email": "string",
  "role": "string",
  "message": "Registration successful. Please check your email for verification."
}
```

#### POST /auth/login

**Description**: Authenticate user and return JWT token  
**Request Body**:

```json
{
  "email": "string",
  "password": "string"
}
```

**Response**: `200 OK`

```json
{
  "token": "jwt-token",
  "userId": "uuid",
  "role": "farmer | consumer",
  "expiresIn": 86400
}
```

### Product Endpoints

#### POST /products

**Description**: Create new product (farmer only)  
**Authentication**: Required (JWT)  
**Authorization**: Farmer role  
**Request Body**:

```json
{
  "name": "string",
  "category": "vegetables | fruits | grains | spices | dairy",
  "price": "number",
  "unit": "kg | liter | dozen | piece",
  "description": "string",
  "giTag": {
    "hasTag": "boolean",
    "tagName": "string",
    "region": "string"
  },
  "seasonal": {
    "isSeasonal": "boolean",
    "seasonStart": "ISO 8601 date",
    "seasonEnd": "ISO 8601 date"
  },
  "quantity": "number"
}
```

**Response**: `201 Created`

```json
{
  "productId": "uuid",
  "status": "pending",
  "uploadUrls": ["presigned-s3-url-1", "presigned-s3-url-2"]
}
```

#### GET /products

**Description**: List products with filters and pagination  
**Query Parameters**:

- `category`: Filter by category
- `seasonal`: Filter by seasonal availability (true/false)
- `giTag`: Filter by GI tag presence (true/false)
- `search`: Keyword search in name/description
- `limit`: Results per page (default 20, max 100)
- `cursor`: Pagination cursor
  **Response**: `200 OK`

```json
{
  "products": [
    {
      "productId": "uuid",
      "name": "string",
      "category": "string",
      "price": "number",
      "images": ["url"],
      "farmerName": "string",
      "averageRating": "number",
      "giTag": "boolean",
      "authenticityConfidence": "number"
    }
  ],
  "nextCursor": "string | null"
}
```

#### GET /products/{productId}

**Description**: Get detailed product information  
**Response**: `200 OK`

```json
{
  "productId": "uuid",
  "name": "string",
  "category": "string",
  "description": "string",
  "price": "number",
  "unit": "string",
  "images": ["url"],
  "giTag": { "hasTag": "boolean", "tagName": "string", "region": "string" },
  "seasonal": {
    "isSeasonal": "boolean",
    "seasonStart": "date",
    "seasonEnd": "date"
  },
  "verificationStatus": "approved | pending | flagged",
  "fraudRiskScore": "number",
  "authenticityConfidence": "number",
  "aiExplanation": "string",
  "quantity": "number",
  "currentViewers": "number",
  "recentPurchaseCount": "number",
  "farmer": {
    "farmerId": "uuid",
    "farmName": "string",
    "averageRating": "number",
    "totalReviews": "number"
  },
  "reviews": [
    {
      "reviewId": "uuid",
      "rating": "number",
      "reviewText": "string",
      "photos": ["url"],
      "createdAt": "timestamp"
    }
  ]
}
```

### AI Endpoints

#### POST /ai/verify-product

**Description**: Trigger AI fraud detection for product  
**Authentication**: Required (JWT)  
**Authorization**: Farmer role or admin  
**Request Body**:

```json
{
  "productId": "uuid"
}
```

**Response**: `200 OK`

```json
{
  "fraudRiskScore": "number (0-100)",
  "authenticityConfidence": "number (0-100)",
  "predictedMarketPrice": "number",
  "aiExplanation": "string",
  "verificationStatus": "approved | flagged"
}
```

#### POST /ai/generate-marketing

**Description**: Generate AI marketing content  
**Authentication**: Required (JWT)  
**Authorization**: Farmer role  
**Request Body**:

```json
{
  "productId": "uuid",
  "contentType": "description | social | launch | names"
}
```

**Response**: `200 OK`

```json
{
  "content": "string | string[]",
  "variations": ["string"] // for name generation
}
```

### Order Endpoints

#### POST /orders

**Description**: Create new order  
**Authentication**: Required (JWT)  
**Authorization**: Consumer role  
**Request Body**:

```json
{
  "productId": "uuid",
  "quantity": "number",
  "deliveryAddress": {
    "street": "string",
    "city": "string",
    "state": "string",
    "pincode": "string"
  },
  "referralCode": "string (optional)"
}
```

**Response**: `201 Created`

```json
{
  "orderId": "uuid",
  "totalAmount": "number",
  "paymentUrl": "string",
  "estimatedDeliveryDate": "date"
}
```

#### GET /orders

**Description**: List user's orders  
**Authentication**: Required (JWT)  
**Response**: `200 OK`

```json
{
  "orders": [
    {
      "orderId": "uuid",
      "productName": "string",
      "quantity": "number",
      "totalAmount": "number",
      "status": "pending | confirmed | shipped | delivered",
      "estimatedDeliveryDate": "date",
      "createdAt": "timestamp"
    }
  ]
}
```

### Review Endpoints

#### POST /reviews

**Description**: Submit product review  
**Authentication**: Required (JWT)  
**Authorization**: Consumer role, must have purchased product  
**Request Body**:

```json
{
  "productId": "uuid",
  "orderId": "uuid",
  "rating": "number (1-5)",
  "reviewText": "string",
  "photoUploadCount": "number"
}
```

**Response**: `201 Created`

```json
{
  "reviewId": "uuid",
  "photoUploadUrls": ["presigned-s3-url"]
}
```

### Limited Release Endpoints

#### POST /limited-releases

**Description**: Create limited release  
**Authentication**: Required (JWT)  
**Authorization**: Farmer role  
**Request Body**:

```json
{
  "productId": "uuid",
  "releaseName": "string",
  "quantityLimit": "number (positive integer)",
  "duration": "number (1-30 days)"
}
```

**Response**: `201 Created`

```json
{
  "releaseId": "uuid",
  "startDate": "timestamp",
  "endDate": "timestamp",
  "status": "scheduled"
}
```

### Referral Endpoints

#### POST /referrals/generate

**Description**: Generate referral link for product  
**Authentication**: Required (JWT)  
**Authorization**: Consumer role  
**Request Body**:

```json
{
  "productId": "uuid"
}
```

**Response**: `200 OK`

```json
{
  "referralCode": "string",
  "referralUrl": "string"
}
```

### Analytics Endpoints

#### GET /analytics/farmer/{farmerId}

**Description**: Get farmer analytics dashboard  
**Authentication**: Required (JWT)  
**Authorization**: Farmer role (own data only)  
**Response**: `200 OK`

```json
{
  "monthlyRevenue": "number",
  "totalSales": "number",
  "averageRating": "number",
  "totalReviews": "number",
  "topProducts": [
    {
      "productId": "uuid",
      "name": "string",
      "revenue": "number",
      "views": "number",
      "conversionRate": "number"
    }
  ],
  "bonusStatus": {
    "currentStreak": "number",
    "totalBonuses": "number",
    "featuredStatus": "boolean"
  }
}
```

## Security and Authentication Design

### Authentication Flow

**JWT-Based Authentication**:

1. User registers or logs in via `/auth/register` or `/auth/login`
2. Server validates credentials and generates JWT token with:
   - User ID
   - Role (farmer/consumer)
   - Expiration (24 hours)
   - Signature using secret key stored in AWS Secrets Manager
3. Client stores JWT token in localStorage or httpOnly cookie
4. Client includes token in Authorization header for all authenticated requests
5. Lambda authorizer validates JWT on each request before invoking handler

**JWT Token Structure**:

```json
{
  "sub": "userId",
  "role": "farmer | consumer",
  "email": "user@example.com",
  "iat": 1234567890,
  "exp": 1234654290
}
```

### Authorization Model

**Role-Based Access Control (RBAC)**:

**Farmer Permissions**:

- Create, update, delete own products
- View own analytics and orders
- Create promotions and limited releases
- Generate AI marketing content
- View all marketplace products

**Consumer Permissions**:

- Browse marketplace products
- Create orders and reviews
- Generate referral links
- View own orders and referral rewards
- Follow farmers

**Admin Permissions** (future):

- View all products and users
- Manual product verification
- Platform analytics
- Cost monitoring

### Security Measures

#### 1. Data Encryption

**At Rest**:

- DynamoDB encryption enabled using AWS KMS
- S3 bucket encryption enabled (SSE-S3)
- Secrets Manager for sensitive configuration (JWT secret, API keys)

**In Transit**:

- HTTPS only (TLS 1.2+) enforced via API Gateway
- Certificate management via AWS Certificate Manager

#### 2. Input Validation and Sanitization

**Server-Side Validation**:

- Validate all input against schemas using libraries like `joi` or `zod`
- Sanitize user-generated content (product descriptions, reviews) to prevent XSS
- Validate file uploads (type, size, content)
- Reject requests with invalid or missing required fields

**Client-Side Validation**:

- Pre-validate forms before submission for better UX
- Never trust client-side validation alone

#### 3. API Security

**Rate Limiting**:

- API Gateway usage plans with per-user rate limits
- Throttling: 100 requests/second per user
- Burst: 200 requests
- Return HTTP 429 with Retry-After header when exceeded

**CORS Configuration**:

- Restrict origins to frontend domain only
- Allow credentials for authenticated requests
- Specify allowed methods and headers

**API Key Management**:

- Use API keys for internal service-to-service communication
- Rotate keys regularly (every 90 days)
- Store keys in AWS Secrets Manager

#### 4. File Upload Security

**S3 Pre-Signed URLs**:

- Generate pre-signed URLs with 15-minute expiration
- Restrict to specific file types (image/jpeg, image/png)
- Limit file size to 5MB
- Validate file content-type on upload

**Malware Scanning**:

- Consider AWS Lambda-based antivirus scanning for uploaded files
- Quarantine suspicious files for manual review

#### 5. Payment Security

**PCI Compliance**:

- Never store credit card information
- Use Razorpay/Stripe hosted payment pages
- Validate webhook signatures to prevent tampering
- Use idempotency keys to prevent duplicate charges

**Webhook Security**:

- Verify webhook signatures using gateway-provided secret
- Validate webhook source IP addresses
- Log all webhook events for audit trail

#### 6. Secrets Management

**AWS Secrets Manager**:

- Store JWT signing secret
- Store payment gateway API keys
- Store Bedrock API credentials
- Store database connection strings
- Rotate secrets automatically every 90 days

**Environment Variables**:

- Use Lambda environment variables for non-sensitive config
- Encrypt environment variables using KMS

#### 7. Logging and Monitoring

**CloudWatch Logs**:

- Log all authentication attempts (success and failure)
- Log all authorization failures
- Log all payment transactions
- Log all API errors with stack traces
- Redact sensitive data (passwords, tokens) from logs

**Security Monitoring**:

- CloudWatch Alarms for:
  - High rate of authentication failures (potential brute force)
  - Unusual API access patterns
  - Unauthorized access attempts
  - Payment failures
- AWS GuardDuty for threat detection
- AWS WAF for web application firewall (if budget permits)

#### 8. Data Privacy

**GDPR/Privacy Compliance**:

- Implement user data export functionality
- Implement user data deletion (right to be forgotten)
- Obtain consent for email notifications
- Provide clear privacy policy
- Anonymize analytics data

**Data Minimization**:

- Only collect necessary user data
- Delete old data based on retention policies
- Anonymize user data in analytics

## Deployment Architecture

### Infrastructure as Code

**AWS SAM Template Structure**:

```yaml
AWSTemplateFormatVersion: "2010-09-09"
Transform: AWS::Serverless-2016-10-31

Parameters:
  Environment:
    Type: String
    AllowedValues: [dev, staging, prod]
    Default: dev

  BudgetLimit:
    Type: Number
    Default: 300
    Description: Monthly AWS budget in USD

Globals:
  Function:
    Runtime: nodejs18.x
    Timeout: 30
    MemorySize: 512
    Environment:
      Variables:
        TABLE_NAME: !Ref RootTrustTable
        BUCKET_NAME: !Ref AssetsBucket
        JWT_SECRET: !Sub "{{resolve:secretsmanager:${JWTSecret}:SecretString}}"

Resources:
  # API Gateway
  RootTrustAPI:
    Type: AWS::Serverless::Api
    Properties:
      StageName: !Ref Environment
      Cors:
        AllowOrigin: "'*'"
        AllowHeaders: "'Content-Type,Authorization'"
      Auth:
        DefaultAuthorizer: JWTAuthorizer
        Authorizers:
          JWTAuthorizer:
            FunctionArn: !GetAtt AuthorizerFunction.Arn

  # Lambda Functions
  AuthFunction:
    Type: AWS::Serverless::Function
    Properties:
      CodeUri: src/handlers/auth/
      Handler: index.handler
      Events:
        Register:
          Type: Api
          Properties:
            RestApiId: !Ref RootTrustAPI
            Path: /auth/register
            Method: POST
            Auth:
              Authorizer: NONE
        Login:
          Type: Api
          Properties:
            RestApiId: !Ref RootTrustAPI
            Path: /auth/login
            Method: POST
            Auth:
              Authorizer: NONE

  ProductFunction:
    Type: AWS::Serverless::Function
    Properties:
      CodeUri: src/handlers/product/
      Handler: index.handler
      Policies:
        - DynamoDBCrudPolicy:
            TableName: !Ref RootTrustTable
        - S3CrudPolicy:
            BucketName: !Ref AssetsBucket
      Events:
        CreateProduct:
          Type: Api
          Properties:
            RestApiId: !Ref RootTrustAPI
            Path: /products
            Method: POST
        ListProducts:
          Type: Api
          Properties:
            RestApiId: !Ref RootTrustAPI
            Path: /products
            Method: GET
            Auth:
              Authorizer: NONE

  AIVerificationFunction:
    Type: AWS::Serverless::Function
    Properties:
      CodeUri: src/handlers/ai-verification/
      Handler: index.handler
      Timeout: 60
      Policies:
        - DynamoDBCrudPolicy:
            TableName: !Ref RootTrustTable
        - Statement:
            - Effect: Allow
              Action:
                - bedrock:InvokeModel
              Resource: "*"

  # DynamoDB Table
  RootTrustTable:
    Type: AWS::DynamoDB::Table
    Properties:
      TableName: !Sub RootTrustData-${Environment}
      BillingMode: PAY_PER_REQUEST
      AttributeDefinitions:
        - AttributeName: PK
          AttributeType: S
        - AttributeName: SK
          AttributeType: S
        - AttributeName: GSI1PK
          AttributeType: S
        - AttributeName: GSI1SK
          AttributeType: S
        - AttributeName: GSI2PK
          AttributeType: S
        - AttributeName: GSI2SK
          AttributeType: S
        - AttributeName: GSI3PK
          AttributeType: S
        - AttributeName: GSI3SK
          AttributeType: S
      KeySchema:
        - AttributeName: PK
          KeyType: HASH
        - AttributeName: SK
          KeyType: RANGE
      GlobalSecondaryIndexes:
        - IndexName: GSI1
          KeySchema:
            - AttributeName: GSI1PK
              KeyType: HASH
            - AttributeName: GSI1SK
              KeyType: RANGE
          Projection:
            ProjectionType: ALL
        - IndexName: GSI2
          KeySchema:
            - AttributeName: GSI2PK
              KeyType: HASH
            - AttributeName: GSI2SK
              KeyType: RANGE
          Projection:
            ProjectionType: ALL
        - IndexName: GSI3
          KeySchema:
            - AttributeName: GSI3PK
              KeyType: HASH
            - AttributeName: GSI3SK
              KeyType: RANGE
          Projection:
            ProjectionType: ALL
      StreamSpecification:
        StreamViewType: NEW_AND_OLD_IMAGES
      PointInTimeRecoverySpecification:
        PointInTimeRecoveryEnabled: true

  # S3 Bucket
  AssetsBucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: !Sub roottrust-assets-${Environment}-${AWS::AccountId}
      PublicAccessBlockConfiguration:
        BlockPublicAcls: true
        BlockPublicPolicy: true
        IgnorePublicAcls: true
        RestrictPublicBuckets: true
      LifecycleConfiguration:
        Rules:
          - Id: TransitionToIA
            Status: Enabled
            Transitions:
              - TransitionInDays: 30
                StorageClass: STANDARD_IA
          - Id: DeleteTempUploads
            Status: Enabled
            Prefix: temp-uploads/
            ExpirationInDays: 1
      CorsConfiguration:
        CorsRules:
          - AllowedOrigins: ["*"]
            AllowedMethods: [GET, PUT, POST]
            AllowedHeaders: ["*"]

  # Secrets Manager
  JWTSecret:
    Type: AWS::SecretsManager::Secret
    Properties:
      Name: !Sub roottrust-jwt-secret-${Environment}
      GenerateSecretString:
        SecretStringTemplate: "{}"
        GenerateStringKey: secret
        PasswordLength: 64

  # Budget Alert
  BudgetAlert:
    Type: AWS::Budgets::Budget
    Properties:
      Budget:
        BudgetName: !Sub RootTrust-${Environment}-Budget
        BudgetLimit:
          Amount: !Ref BudgetLimit
          Unit: USD
        TimeUnit: MONTHLY
        BudgetType: COST
      NotificationsWithSubscribers:
        - Notification:
            NotificationType: ACTUAL
            ComparisonOperator: GREATER_THAN
            Threshold: 80
          Subscribers:
            - SubscriptionType: EMAIL
              Address: admin@roottrust.com

Outputs:
  ApiEndpoint:
    Description: API Gateway endpoint URL
    Value: !Sub https://${RootTrustAPI}.execute-api.${AWS::Region}.amazonaws.com/${Environment}

  TableName:
    Description: DynamoDB table name
    Value: !Ref RootTrustTable

  BucketName:
    Description: S3 bucket name
    Value: !Ref AssetsBucket
```

### Deployment Process

**Development Environment**:

1. Developer commits code to feature branch
2. GitHub Actions runs unit tests and linting
3. On merge to `develop` branch, deploy to dev environment
4. Run integration tests against dev environment

**Staging Environment**:

1. On merge to `staging` branch, deploy to staging environment
2. Run full test suite including E2E tests
3. Manual QA testing
4. Performance and load testing

**Production Environment**:

1. Create release tag from `main` branch
2. Deploy to production using blue-green deployment
3. Monitor CloudWatch metrics and error rates
4. Rollback if error rate exceeds threshold

**Deployment Commands**:

```bash
# Build and package
sam build

# Deploy to dev
sam deploy --config-env dev --parameter-overrides Environment=dev

# Deploy to production
sam deploy --config-env prod --parameter-overrides Environment=prod
```

### Frontend Deployment (AWS Amplify)

**Amplify Configuration**:

```yaml
version: 1
frontend:
  phases:
    preBuild:
      commands:
        - npm ci
    build:
      commands:
        - npm run build
  artifacts:
    baseDirectory: build
    files:
      - "**/*"
  cache:
    paths:
      - node_modules/**/*
```

**Environment Variables**:

- `REACT_APP_API_ENDPOINT`: API Gateway URL
- `REACT_APP_ENVIRONMENT`: dev/staging/prod
- `REACT_APP_RAZORPAY_KEY`: Payment gateway public key

### Monitoring and Observability

**CloudWatch Dashboards**:

- API Gateway request count, latency, error rate
- Lambda invocation count, duration, errors, throttles
- DynamoDB read/write capacity, throttles
- Bedrock API call count, latency, errors
- S3 request count, data transfer

**CloudWatch Alarms**:

- Lambda error rate > 5%
- API Gateway 5xx error rate > 1%
- DynamoDB throttling events
- Budget exceeds 80% of limit
- Bedrock API failures

**X-Ray Tracing**:

- Enable X-Ray for all Lambda functions
- Trace request flow through API Gateway → Lambda → DynamoDB
- Identify performance bottlenecks
- Analyze cold start impact

### Disaster Recovery

**Backup Strategy**:

- DynamoDB Point-in-Time Recovery enabled
- Daily automated backups of DynamoDB table
- S3 versioning enabled for critical assets
- Backup retention: 30 days

**Recovery Procedures**:

- DynamoDB restore from backup (RPO: 5 minutes, RTO: 1 hour)
- S3 object restoration from versioning
- Lambda function redeployment from SAM template
- Secrets rotation and regeneration

## Cost Optimization Strategies

### Budget Breakdown ($300 for 30+ days)

**Target Daily Budget**: $10/day

**Estimated Cost Distribution**:

| Service         | Daily Cost | Monthly Cost | Optimization Strategy                  |
| --------------- | ---------- | ------------ | -------------------------------------- |
| Lambda          | $2.00      | $60          | Minimize cold starts, optimize memory  |
| DynamoDB        | $1.50      | $45          | On-demand pricing, single-table design |
| API Gateway     | $1.00      | $30          | Caching, request batching              |
| Amazon Bedrock  | $3.00      | $90          | Aggressive caching (24h TTL)           |
| S3              | $0.50      | $15          | Lifecycle policies, CloudFront caching |
| SES             | $0.30      | $9           | Batch emails, respect preferences      |
| Amplify         | $0.50      | $15          | Static hosting, CDN caching            |
| CloudWatch      | $0.50      | $15          | Log retention policies, metric filters |
| Secrets Manager | $0.20      | $6           | Minimize secret count                  |
| Data Transfer   | $0.50      | $15          | CloudFront, compression                |
| **Total**       | **$10.00** | **$300**     |                                        |

### Lambda Cost Optimization

**Function Configuration**:

- Use ARM64 (Graviton2) for 20% cost savings
- Right-size memory allocation (512MB default, tune per function)
- Minimize cold starts with provisioned concurrency for critical paths only
- Use Lambda layers for shared dependencies to reduce deployment size

**Code Optimization**:

- Minimize initialization code outside handler
- Reuse SDK clients and database connections
- Use async/await efficiently to reduce execution time
- Implement early returns to avoid unnecessary processing

**Invocation Reduction**:

- Batch DynamoDB operations where possible
- Use DynamoDB Streams instead of polling
- Implement request caching at API Gateway level
- Use EventBridge for scheduled tasks instead of polling

**Cost Monitoring**:

```javascript
// Track Lambda costs per function
const costPerInvocation = (memoryMB, durationMs) => {
  const gbSeconds = (memoryMB / 1024) * (durationMs / 1000);
  const cost = gbSeconds * 0.0000166667; // $0.0000166667 per GB-second
  return cost;
};
```

### DynamoDB Cost Optimization

**On-Demand Pricing**:

- Pay per request instead of provisioned capacity
- No capacity planning required
- Automatically scales with traffic
- Cost: $1.25 per million write requests, $0.25 per million read requests

**Single-Table Design**:

- Reduces number of tables (fewer costs)
- Enables efficient queries with GSIs
- Minimizes cross-table joins

**Query Optimization**:

- Use GSIs for common query patterns
- Avoid scans (use queries with partition keys)
- Use projection expressions to fetch only needed attributes
- Implement pagination to limit result sizes

**Data Modeling**:

- Denormalize data to reduce queries
- Store computed values (averages, totals) to avoid aggregations
- Use sparse indexes to reduce GSI costs

### Amazon Bedrock Cost Optimization

**Aggressive Caching**:

- Cache fraud detection results for 24 hours
- Cache marketing content for 7 days
- Use DynamoDB or ElastiCache for cache storage
- Cache key: hash of product details + operation type

**Request Batching**:

- Batch multiple product verifications in single request
- Generate marketing content for multiple products together
- Use async processing for non-urgent requests

**Model Selection**:

- Use Claude Instant for faster, cheaper responses
- Use Claude 2 only for complex fraud detection
- Experiment with Titan models for cost comparison

**Prompt Optimization**:

- Minimize prompt length to reduce token costs
- Use structured prompts for consistent responses
- Avoid unnecessary context in prompts

**Cost Calculation**:

```javascript
// Claude Instant pricing: $0.00163 per 1K input tokens, $0.00551 per 1K output tokens
const estimateBedrock Cost = (inputTokens, outputTokens) => {
  const inputCost = (inputTokens / 1000) * 0.00163;
  const outputCost = (outputTokens / 1000) * 0.00551;
  return inputCost + outputCost;
};

// Example: Fraud detection (500 input, 200 output tokens)
// Cost: $0.00082 + $0.00110 = $0.00192 per product
// With 24h caching, 1000 products = $1.92/day
```

### S3 Cost Optimization

**Lifecycle Policies**:

```json
{
  "Rules": [
    {
      "Id": "TransitionToIA",
      "Status": "Enabled",
      "Transitions": [
        {
          "Days": 30,
          "StorageClass": "STANDARD_IA"
        }
      ]
    },
    {
      "Id": "DeleteTempUploads",
      "Status": "Enabled",
      "Prefix": "temp-uploads/",
      "Expiration": {
        "Days": 1
      }
    }
  ]
}
```

**Storage Class Comparison**:

- Standard: $0.023 per GB/month
- Standard-IA: $0.0125 per GB/month (45% savings)
- Transition after 30 days when access frequency drops

**Image Optimization**:

- Compress images before upload (JPEG quality 85%)
- Generate thumbnails for listings (reduce bandwidth)
- Use WebP format for modern browsers (30% smaller)
- Lazy load images in frontend

**CloudFront CDN** (optional, if budget permits):

- Cache images at edge locations
- Reduce S3 data transfer costs
- Improve load times for users

### API Gateway Cost Optimization

**Request Caching**:

- Enable caching for GET endpoints (product listings, details)
- Cache TTL: 5 minutes for marketplace, 1 hour for product details
- Cache key includes query parameters and user role
- Cost: $0.02 per GB cached

**Request Batching**:

- Batch multiple product fetches in single request
- Use GraphQL-style queries to fetch related data together
- Reduce number of API calls from frontend

**Compression**:

- Enable gzip compression for responses
- Reduces data transfer costs by 70-80%

### SES Cost Optimization

**Email Batching**:

- Batch notification emails instead of sending individually
- Use SES bulk email API for newsletters
- Cost: $0.10 per 1,000 emails

**Preference Management**:

- Respect user notification preferences
- Avoid sending unnecessary emails
- Implement unsubscribe functionality

**Template Reuse**:

- Use SES email templates to reduce payload size
- Store templates in SES, not in Lambda code

### Monitoring and Alerting

**Cost Anomaly Detection**:

- Enable AWS Cost Anomaly Detection
- Set up alerts for unusual spending patterns
- Review Cost Explorer daily

**Budget Alerts**:

- Alert at 50%, 80%, 90%, 100% of budget
- Automatic notifications via SNS/email
- Consider automatic resource shutdown at 95%

**Cost Allocation Tags**:

- Tag all resources with Environment, Service, Feature
- Track costs per feature/service
- Identify cost optimization opportunities

### Emergency Cost Controls

**If Budget Exceeds 90%**:

1. Disable non-critical features (promotions, limited releases)
2. Reduce Bedrock caching TTL to 1 hour
3. Disable email notifications except transactional
4. Reduce API Gateway cache TTL
5. Throttle API requests more aggressively

**If Budget Exceeds 100%**:

1. Put platform in read-only mode
2. Disable all AI features (Bedrock)
3. Disable image uploads
4. Display maintenance message to users
5. Investigate cost spike and optimize

## AWS Service Utilization Details

### AWS Lambda

**Purpose**: Serverless compute for all business logic

**Functions**:

- `auth-handler`: User registration, login, JWT generation
- `product-handler`: Product CRUD operations
- `ai-verification-handler`: Fraud detection via Bedrock
- `ai-marketing-handler`: Marketing content generation
- `order-handler`: Order creation and management
- `payment-handler`: Payment processing and webhooks
- `review-handler`: Review submission and aggregation
- `referral-handler`: Referral link generation and tracking
- `promotion-handler`: Promotion management
- `limited-release-handler`: Limited release management
- `analytics-handler`: Metrics calculation and reporting
- `notification-handler`: Email notification sending
- `authorizer-function`: JWT validation for API Gateway

**Configuration**:

- Runtime: Node.js 18.x (or Python 3.11)
- Memory: 512MB (tune per function)
- Timeout: 30s (60s for AI functions)
- Architecture: ARM64 (Graviton2)
- Concurrency: 100 (reserved for critical functions)

**Why Lambda**:

- Zero infrastructure management
- Pay only for execution time
- Automatic scaling
- Integrates seamlessly with API Gateway, DynamoDB, S3
- Cost-effective for variable workload

### Amazon API Gateway

**Purpose**: RESTful API endpoint management

**Configuration**:

- Type: REST API (not HTTP API for authorizer support)
- Stage: dev/staging/prod
- Throttling: 100 requests/second per user
- Caching: Enabled for GET endpoints (5-60 min TTL)
- CORS: Enabled for web access
- Authorization: Lambda authorizer for JWT validation

**Endpoints**: 50+ endpoints across authentication, products, orders, reviews, AI, analytics

**Why API Gateway**:

- Managed API infrastructure
- Built-in throttling and caching
- Request/response transformation
- API key management
- CloudWatch integration

### Amazon DynamoDB

**Purpose**: NoSQL database for all application data

**Table Design**: Single table with GSIs for query patterns

**Capacity Mode**: On-demand (pay per request)

**Features Used**:

- Point-in-Time Recovery for backups
- DynamoDB Streams for event-driven processing
- Global Secondary Indexes (3) for query optimization
- Conditional writes for data consistency
- Transactions for multi-item operations

**Why DynamoDB**:

- Serverless, fully managed
- Predictable performance at scale
- On-demand pricing fits variable workload
- Streams enable event-driven architecture
- Single-table design reduces costs

### Amazon S3

**Purpose**: Object storage for images and documents

**Buckets**:

- `roottrust-assets-{env}`: Product images, review photos, invoices

**Features Used**:

- Lifecycle policies (Standard → Standard-IA after 30 days)
- Pre-signed URLs for secure uploads
- Versioning for critical assets
- CORS configuration for browser uploads
- Server-side encryption (SSE-S3)

**Why S3**:

- Highly durable (99.999999999%)
- Cost-effective storage
- Lifecycle policies reduce costs
- Integrates with CloudFront for CDN
- Pre-signed URLs enable direct uploads

### Amazon Bedrock

**Purpose**: AI/ML capabilities for fraud detection and content generation

**Models Used**:

- Claude Instant: Fast, cost-effective for marketing content
- Claude 2: Advanced reasoning for fraud detection
- Titan: Alternative for cost comparison

**Use Cases**:

1. **Fraud Detection**: Analyze product details, calculate fraud risk score
2. **Market Price Prediction**: Estimate expected prices based on category, GI tag, seasonality
3. **Marketing Content**: Generate product descriptions, social media posts, launch announcements
4. **Product Naming**: Suggest optimized product names
5. **Description Enhancement**: Improve farmer-provided descriptions

**Why Bedrock**:

- Managed AI service (no model training/hosting)
- Multiple model options
- Pay-per-use pricing
- Built-in security and compliance
- Easy integration with Lambda

**Cost Control**:

- Aggressive caching (24h for fraud scores, 7d for marketing)
- Prompt optimization to reduce token usage
- Model selection based on task complexity

### Amazon SES

**Purpose**: Transactional and marketing email delivery

**Email Types**:

- Registration confirmation
- Order confirmations
- Payment notifications
- Review requests
- Limited release alerts
- Promotion summaries
- Farmer bonus notifications

**Configuration**:

- Verified sender domain
- Email templates for consistency
- Bounce and complaint handling
- Unsubscribe management

**Why SES**:

- Cost-effective ($0.10 per 1,000 emails)
- High deliverability
- Bounce and complaint tracking
- Template support
- Integrates with Lambda

### AWS Amplify

**Purpose**: Frontend hosting and deployment

**Features Used**:

- Static site hosting for React SPA
- Continuous deployment from Git
- Custom domain support
- HTTPS/SSL certificates
- Environment variable management
- Build and deploy automation

**Why Amplify**:

- Managed hosting for SPAs
- Built-in CI/CD
- Global CDN distribution
- Automatic HTTPS
- Cost-effective for static sites

### Amazon EventBridge

**Purpose**: Scheduled tasks and event routing

**Scheduled Rules**:

- Limited release expiry check (every 5 minutes)
- Promotion end notifications (every hour)
- Review request emails (daily)
- Cost monitoring (daily)
- Analytics aggregation (daily)

**Event Patterns**:

- DynamoDB Stream events → Notification Lambda
- Order status changes → Email notifications
- Product approval → Marketplace updates

**Why EventBridge**:

- Serverless event bus
- Cron-based scheduling
- Event filtering and routing
- Integrates with Lambda, DynamoDB Streams
- Pay per event

### AWS Secrets Manager

**Purpose**: Secure storage for sensitive configuration

**Secrets Stored**:

- JWT signing secret
- Razorpay/Stripe API keys
- Bedrock API credentials
- Database connection strings
- Email service credentials

**Features Used**:

- Automatic rotation (90 days)
- Encryption at rest (KMS)
- Fine-grained access control (IAM)
- Versioning

**Why Secrets Manager**:

- Secure secret storage
- Automatic rotation
- Audit logging
- Integrates with Lambda
- Better than environment variables

### AWS CloudWatch

**Purpose**: Monitoring, logging, and alerting

**Features Used**:

- Logs: All Lambda function logs
- Metrics: Custom metrics for business KPIs
- Alarms: Error rates, budget alerts, performance
- Dashboards: Real-time platform health
- Insights: Log analysis and querying

**Metrics Tracked**:

- API request count, latency, errors
- Lambda invocations, duration, errors
- DynamoDB read/write capacity, throttles
- Bedrock API calls, latency, errors
- S3 request count, data transfer
- Daily AWS costs

**Why CloudWatch**:

- Integrated with all AWS services
- Centralized logging and monitoring
- Powerful alerting capabilities
- Log retention policies
- Cost-effective

### AWS X-Ray

**Purpose**: Distributed tracing and performance analysis

**Features Used**:

- Trace API requests through Lambda, DynamoDB
- Identify performance bottlenecks
- Analyze cold start impact
- Service map visualization
- Error analysis

**Why X-Ray**:

- End-to-end request tracing
- Performance optimization insights
- Integrates with Lambda, API Gateway
- Helps identify cost optimization opportunities

### AWS Budgets

**Purpose**: Cost monitoring and alerting

**Configuration**:

- Monthly budget: $300
- Alerts at 50%, 80%, 90%, 100%
- Email notifications to admins
- Forecasted cost alerts

**Why Budgets**:

- Proactive cost management
- Prevents budget overruns
- Forecasting capabilities
- Free service (no additional cost)

### AWS IAM

**Purpose**: Identity and access management

**Policies**:

- Lambda execution roles with least privilege
- API Gateway invoke permissions
- DynamoDB table access policies
- S3 bucket access policies
- Bedrock model access policies

**Why IAM**:

- Fine-grained access control
- Principle of least privilege
- Audit logging via CloudTrail
- No additional cost

## AI Value Proposition

### Why AI is Required

**1. Fraud Detection and Authenticity Verification**

**Problem**: Consumers receive counterfeit or low-quality agricultural products, especially GI-tagged items. Manual verification is:

- Time-consuming and expensive
- Inconsistent across verifiers
- Not scalable for marketplace growth
- Prone to human error and bias

**AI Solution**: Amazon Bedrock analyzes product details to:

- Calculate fraud risk scores (0-100) based on price anomalies, description inconsistencies, invoice validation
- Generate authenticity confidence percentages
- Provide explainable reasoning for decisions
- Flag high-risk products for manual review
- Predict market prices to detect pricing fraud

**Value**: Automated, consistent, scalable fraud detection that builds consumer trust and protects farmers from counterfeit competition.

**2. Marketing Content Generation**

**Problem**: Farmers lack marketing expertise and struggle to:

- Write compelling product descriptions
- Create engaging social media content
- Craft effective product names
- Generate urgency-focused messaging

**AI Solution**: Amazon Bedrock generates:

- Value-driven product descriptions emphasizing benefits
- Social media promotional text optimized for engagement
- Product launch announcements
- Three product name variations with different value propositions
- Seasonal urgency messaging

**Value**: Levels the playing field for farmers without marketing skills, increases product appeal, drives sales conversions.

**3. Market Price Prediction**

**Problem**: Farmers struggle to price products competitively while consumers don't know if prices are fair.

**AI Solution**: Bedrock predicts market prices based on:

- Product category and quality indicators
- GI tag presence (premium pricing)
- Seasonal supply/demand factors
- Historical pricing data

**Value**: Helps farmers price competitively, helps consumers identify fair prices, detects pricing fraud.

### AI Integration Patterns

**Pattern 1: Synchronous AI Calls**

- User uploads product → Lambda invokes Bedrock → Returns fraud score immediately
- Used for: Fraud detection, product naming suggestions
- Latency: 2-5 seconds

**Pattern 2: Asynchronous AI Processing**

- Product uploaded → Queued in DynamoDB → Background Lambda processes → Updates product record
- Used for: Marketing content generation, batch verifications
- Latency: 30-60 seconds

**Pattern 3: Cached AI Responses**

- Check cache (DynamoDB) → If miss, invoke Bedrock → Store in cache → Return result
- Used for: All AI operations to reduce costs
- Cache TTL: 24h for fraud scores, 7d for marketing content

## Conclusion

The RootTrust marketplace platform is designed as a cost-optimized, serverless solution that leverages AWS services to connect farmers with consumers while ensuring product authenticity through AI-powered fraud detection. The architecture prioritizes:

- **Cost Efficiency**: Staying within $300/month budget through aggressive caching, lifecycle policies, and on-demand pricing
- **Scalability**: Serverless architecture that scales automatically with demand
- **Trust**: AI-powered fraud detection builds consumer confidence
- **Farmer Empowerment**: AI marketing tools help farmers compete effectively
- **Maintainability**: Infrastructure as code, comprehensive testing, monitoring

The design addresses all 22 requirements with 85 testable correctness properties, ensuring the platform delivers on its promise to solve the dual problems of product authenticity and farmer marketing challenges.
