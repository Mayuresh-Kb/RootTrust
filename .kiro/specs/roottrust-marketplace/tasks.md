# Implementation Plan: RootTrust Marketplace Platform

## Overview

This implementation plan breaks down the RootTrust marketplace platform into actionable coding tasks. The platform is a serverless AI-powered marketplace built on AWS that connects farmers with consumers while ensuring product authenticity through Amazon Bedrock-powered fraud detection.

**Technology Stack:**

- Backend: Python 3.11 with AWS Lambda
- Frontend: React with TypeScript
- Infrastructure: AWS SAM (Serverless Application Model)
- Database: DynamoDB (single-table design)
- Storage: Amazon S3
- AI: Amazon Bedrock (Claude/Titan models)
- Deployment: AWS SAM CLI + AWS Amplify

**Architecture:** Serverless microservices with API Gateway, 13 Lambda functions, DynamoDB single-table design, S3 for assets, Bedrock for AI, SES for emails, EventBridge for scheduling.

**Budget Constraint:** $300 AWS credits for 30+ days

## Tasks

### Phase 1: Infrastructure and Core Setup

- [x] 1. Set up project structure and AWS SAM configuration
  - Create directory structure: `backend/`, `frontend/`, `infrastructure/`, `tests/`
  - Create AWS SAM template (`template.yaml`) with globals and parameters
  - Define DynamoDB table with single-table design (PK, SK, 3 GSIs)
  - Define S3 bucket with lifecycle policies (Standard → Standard-IA after 30 days)
  - Configure API Gateway with CORS and throttling (100 req/sec per user)
  - Set up Secrets Manager for JWT secret and API keys
  - Configure AWS Budgets alert at 80% of $300 limit
  - _Requirements: 19.1, 19.2, 19.3, 21.1, 21.2, 21.4_

- [x] 2. Create shared Python utilities and data models
  - Create `backend/shared/models.py` with Pydantic models for User, Product, Order, Review, etc.
  - Create `backend/shared/database.py` with DynamoDB helper functions (get_item, put_item, query, scan)
  - Create `backend/shared/auth.py` with JWT token generation and validation functions
  - Create `backend/shared/validators.py` with input validation schemas
  - Create `backend/shared/constants.py` with enums (UserRole, ProductCategory, OrderStatus, etc.)
  - Create `backend/shared/exceptions.py` with custom exception classes
  - _Requirements: 20.1, 20.2, 20.3, 1.4_

- [ ]\* 2.1 Write property tests for data models
  - **Property 9: Product Data Round-Trip Preservation**
  - **Validates: Requirements 20.5**
  - Test that Product objects serialize to JSON and deserialize back without data loss
  - Use `hypothesis` library with 100+ iterations

### Phase 2: Authentication Service

- [x] 3. Implement authentication Lambda function
  - [x] 3.1 Create user registration endpoint (POST /auth/register)
    - Accept email, password, role (farmer/consumer), firstName, lastName, phone
    - Validate email format and password strength (min 8 chars)
    - Hash password using bcrypt
    - Generate unique userId (UUID v4)
    - Store user record in DynamoDB with PK=USER#{userId}, SK=PROFILE
    - Set GSI2PK=ROLE#{role}, GSI2SK=USER#{createdAt} for role-based queries
    - Return userId, email, role, success message
    - _Requirements: 1.1, 1.4_

  - [ ]\* 3.2 Write property test for user registration
    - **Property 1: User Registration Creates Valid Accounts**
    - **Validates: Requirements 1.1, 1.4**
    - Test with random valid emails, passwords, and roles

  - [ ]\* 3.3 Write property test for password hashing
    - **Property 5: Passwords Are Never Stored in Plaintext**
    - **Validates: Requirements 1.4**
    - Verify all stored passwords are bcrypt hashes

  - [x] 3.4 Create user login endpoint (POST /auth/login)
    - Accept email and password
    - Query DynamoDB for user by email (requires GSI on email field)
    - Verify password using bcrypt.compare()
    - Generate JWT token with userId, role, email claims (24h expiration)
    - Sign JWT using secret from Secrets Manager
    - Return token, userId, role, expiresIn
    - _Requirements: 1.2_

  - [ ]\* 3.5 Write property test for valid authentication
    - **Property 2: Valid Credentials Authenticate Successfully**
    - **Validates: Requirements 1.2**

  - [ ]\* 3.6 Write property test for invalid authentication
    - **Property 3: Invalid Credentials Are Rejected**
    - **Validates: Requirements 1.3**

  - [x] 3.7 Create JWT authorizer Lambda function
    - Extract JWT token from Authorization header
    - Validate token signature using secret from Secrets Manager
    - Verify token expiration
    - Return IAM policy allowing/denying API Gateway access
    - Include userId and role in context for downstream Lambdas
    - _Requirements: 1.2_

  - [x] 3.8 Integrate SES for confirmation emails
    - Create email template for registration confirmation
    - Send email via boto3 SES client after successful registration
    - Include verification link (optional for MVP)
    - _Requirements: 1.5_

  - [ ]\* 3.9 Write property test for confirmation email trigger
    - **Property 4: Registration Triggers Confirmation Email**
    - **Validates: Requirements 1.5**

### Phase 3: Product Management Service

- [x] 4. Implement product Lambda function
  - [x] 4.1 Create product creation endpoint (POST /products)
    - Validate JWT token and farmer role authorization
    - Accept name, category, price, unit, description, giTag, seasonal, quantity
    - Validate price is positive number
    - Validate category is valid enum value
    - Generate unique productId (UUID v4)
    - Store product in DynamoDB with PK=PRODUCT#{productId}, SK=METADATA
    - Set verificationStatus=pending, GSI1PK=CATEGORY#{category}, GSI2PK=FARMER#{farmerId}
    - Generate S3 pre-signed URLs for image uploads (15 min expiration, max 5MB)
    - Return productId, status, uploadUrls
    - _Requirements: 2.1, 2.3, 2.5_

  - [ ]\* 4.2 Write property test for valid product creation
    - **Property 6: Valid Product Data Is Accepted and Stored**
    - **Validates: Requirements 2.1, 2.5**

  - [ ]\* 4.3 Write property test for non-positive price rejection
    - **Property 8: Non-Positive Prices Are Rejected**
    - **Validates: Requirements 2.3**

  - [ ]\* 4.4 Write property test for invalid product data errors
    - **Property 10: Invalid Product Data Returns Descriptive Errors**
    - **Validates: Requirements 20.2**

  - [x] 4.5 Create product listing endpoint (GET /products)
    - Accept query parameters: category, seasonal, giTag, search, limit, cursor
    - Query DynamoDB using GSI1 for category filter
    - Filter by seasonal date range if seasonal=true
    - Filter by giTag.hasTag if giTag=true
    - Implement keyword search in name/description (scan with filter)
    - Return only products with verificationStatus=approved
    - Implement pagination using lastEvaluatedKey as cursor
    - Return products array with images, price, farmerName, averageRating, nextCursor
    - _Requirements: 4.1, 4.2, 4.3, 4.5, 4.6_

  - [ ]\* 4.6 Write property test for approved products only
    - **Property 17: Only Approved Products Appear in Marketplace**
    - **Validates: Requirements 4.1**

  - [ ]\* 4.7 Write property test for category filter
    - **Property 18: Category Filter Returns Matching Products**
    - **Validates: Requirements 4.2**

  - [ ]\* 4.8 Write property test for seasonal filter
    - **Property 19: Seasonal Filter Returns In-Season Products**
    - **Validates: Requirements 4.3**

  - [ ]\* 4.9 Write property test for keyword search
    - **Property 21: Keyword Search Matches Name or Description**
    - **Validates: Requirements 4.5**

  - [x] 4.10 Create product detail endpoint (GET /products/{productId})
    - Query DynamoDB for product by PK=PRODUCT#{productId}
    - Query farmer profile using farmerId from product
    - Query reviews using PK=PRODUCT#{productId}, SK begins_with REVIEW#
    - Calculate currentViewers (increment counter in DynamoDB with TTL)
    - Return complete product details with farmer profile and reviews
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

  - [ ]\* 4.11 Write property test for product detail completeness
    - **Property 23: Product Detail View Includes Complete Information**
    - **Validates: Requirements 5.1, 5.2, 5.3, 5.4**

  - [x] 4.12 Create product update endpoint (PUT /products/{productId})
    - Validate JWT token and farmer role authorization
    - Verify farmer owns the product
    - Accept updated fields (name, description, price, quantity, etc.)
    - Update product record in DynamoDB
    - Set updatedAt timestamp
    - Return updated product
    - _Requirements: 2.1_

  - [x] 4.13 Create product image upload handler
    - Handle S3 upload completion events (optional)
    - Update product record with image URLs
    - Set isPrimary flag for first image
    - _Requirements: 2.2_

  - [ ]\* 4.14 Write property test for image storage and linking
    - **Property 7: Product Images Are Stored in S3 and Linked**
    - **Validates: Requirements 2.2**

### Phase 4: AI Verification Service

- [x] 5. Implement AI verification Lambda function
  - [x] 5.1 Create Bedrock fraud detection endpoint (POST /ai/verify-product)
    - Validate JWT token and farmer/admin role authorization
    - Accept productId
    - Retrieve product details from DynamoDB
    - Check cache (DynamoDB) for existing verification (24h TTL)
    - If cache miss, construct Bedrock prompt with product details
    - Invoke Bedrock (Claude 2) with prompt requesting fraud analysis
    - Parse response to extract fraudRiskScore (0-100), authenticityConfidence (0-100), aiExplanation
    - Calculate predictedMarketPrice based on category, GI tag, seasonal factors
    - Set verificationStatus=flagged if fraudRiskScore > 70, else approved
    - Update product record in DynamoDB with verification results
    - Store verification in cache with 24h TTL
    - Return fraudRiskScore, authenticityConfidence, predictedMarketPrice, aiExplanation, verificationStatus
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 19.4_

  - [ ]\* 5.2 Write property test for Bedrock invocation
    - **Property 11: Product Verification Invokes Bedrock**
    - **Validates: Requirements 3.1**

  - [ ]\* 5.3 Write property test for market price prediction
    - **Property 12: Market Price Prediction Is Generated**
    - **Validates: Requirements 3.2**

  - [ ]\* 5.4 Write property test for fraud risk score range
    - **Property 13: Fraud Risk Score Is Within Valid Range**
    - **Validates: Requirements 3.3**

  - [ ]\* 5.5 Write property test for authenticity confidence range
    - **Property 14: Authenticity Confidence Is a Valid Percentage**
    - **Validates: Requirements 3.4**

  - [ ]\* 5.6 Write property test for AI explanation generation
    - **Property 15: Verification Generates Non-Empty Explanation**
    - **Validates: Requirements 3.5**

  - [ ]\* 5.7 Write property test for verification status logic
    - **Property 16: Verification Status Matches Fraud Risk Score**
    - **Validates: Requirements 3.6, 3.7**

  - [x] 5.8 Create verification status check endpoint (GET /ai/verification-status/{productId})
    - Query product record for verification status and scores
    - Return current verification state
    - _Requirements: 3.1_

### Phase 5: AI Marketing Service

- [x] 6. Implement AI marketing Lambda function
  - [x] 6.1 Create product description generation endpoint (POST /ai/generate-description)
    - Validate JWT token and farmer role authorization
    - Accept productId
    - Retrieve product details from DynamoDB
    - Check cache (DynamoDB) for existing content (7d TTL)
    - If cache miss, construct Bedrock prompt emphasizing dream outcome and likelihood
    - Invoke Bedrock (Claude Instant) for cost efficiency
    - Parse response to extract generated description
    - Store in cache with 7d TTL
    - Return generated description
    - _Requirements: 8.1, 8.2, 19.4_

  - [ ]\* 6.2 Write property test for marketing content generation
    - **Property 33: Marketing Content Generation Invokes Bedrock**
    - **Validates: Requirements 8.1, 8.3, 8.4**

  - [ ]\* 6.3 Write property test for value-driven descriptions
    - **Property 34: Generated Descriptions Emphasize Value Elements**
    - **Validates: Requirements 8.2**

  - [x] 6.4 Create product name suggestion endpoint (POST /ai/generate-names)
    - Accept product details
    - Construct Bedrock prompt requesting 3 name variations
    - Invoke Bedrock (Claude Instant)
    - Parse response to extract 3 name suggestions
    - Return array of 3 names
    - _Requirements: 18.1, 18.2_

  - [ ]\* 6.5 Write property test for name variations
    - **Property 37: AI Suggests Three Product Name Variations**
    - **Validates: Requirements 18.2**

  - [x] 6.6 Create description enhancement endpoint (POST /ai/enhance-description)
    - Accept farmer-provided description
    - Construct Bedrock prompt to enhance with sensory language
    - Invoke Bedrock (Claude Instant)
    - Return enhanced description
    - _Requirements: 18.3, 18.5_

  - [ ]\* 6.7 Write property test for description enhancement
    - **Property 38: AI-Enhanced Descriptions Include Sensory Language**
    - **Validates: Requirements 18.3, 18.5**

  - [x] 6.8 Create social media content endpoint (POST /ai/generate-social)
    - Accept productId
    - Check if product is seasonal and near season end (within 7 days)
    - Construct Bedrock prompt with urgency focus if seasonal
    - Invoke Bedrock (Claude Instant)
    - Return social media text
    - _Requirements: 8.3, 8.5_

  - [ ]\* 6.9 Write property test for seasonal urgency messaging
    - **Property 35: Seasonal High-Demand Generates Urgency Messaging**
    - **Validates: Requirements 8.5**

  - [x] 6.10 Create launch announcement endpoint (POST /ai/generate-launch)
    - Accept productId
    - Construct Bedrock prompt for launch announcement
    - Invoke Bedrock (Claude Instant)
    - Return launch announcement text
    - _Requirements: 8.4_

### Phase 6: Order and Payment Services

- [x] 7. Implement order Lambda function
  - [x] 7.1 Create order creation endpoint (POST /orders)
    - Validate JWT token and consumer role authorization
    - Accept productId, quantity, deliveryAddress, referralCode (optional)
    - Query product to verify availability and approved status
    - Verify quantity <= product.quantity
    - Calculate totalAmount = product.price × quantity
    - Generate unique orderId (UUID v4)
    - Calculate estimatedDeliveryDate (current date + 7 days)
    - Store order in DynamoDB with PK=ORDER#{orderId}, SK=METADATA, status=pending
    - Set GSI2PK=CONSUMER#{consumerId}, GSI3PK=FARMER#{farmerId} for queries
    - Decrement product quantity using conditional update
    - Return orderId, totalAmount, estimatedDeliveryDate
    - _Requirements: 6.1, 6.5_

  - [ ]\* 7.2 Write property test for order creation
    - **Property 25: Purchase Initiation Creates Order Record**
    - **Validates: Requirements 6.1**

  - [ ]\* 7.3 Write property test for estimated delivery date
    - **Property 28: Orders Have Estimated Delivery Date**
    - **Validates: Requirements 6.5, 9.4**

  - [x] 7.4 Create order listing endpoint (GET /orders)
    - Validate JWT token
    - If consumer role, query GSI2 with GSI2PK=CONSUMER#{consumerId}
    - If farmer role, query GSI3 with GSI3PK=FARMER#{farmerId}
    - Return orders array with productName, quantity, totalAmount, status, estimatedDeliveryDate
    - _Requirements: 6.1_

  - [x] 7.5 Create order detail endpoint (GET /orders/{orderId})
    - Validate JWT token
    - Query order by PK=ORDER#{orderId}
    - Verify user owns the order (consumer or farmer)
    - Return complete order details
    - _Requirements: 6.1_

  - [x] 7.6 Create order status update endpoint (PUT /orders/{orderId}/status)
    - Validate JWT token and farmer role authorization
    - Accept new status (confirmed, processing, shipped, delivered, cancelled)
    - Update order status in DynamoDB
    - Trigger notification email via SES
    - If status=delivered, set actualDeliveryDate
    - Return updated order
    - _Requirements: 6.6_

  - [ ]\* 7.7 Write property test for status change notifications
    - **Property 29: Order Status Changes Trigger Notifications**
    - **Validates: Requirements 6.6**

- [x] 8. Implement payment Lambda function
  - [x] 8.1 Create payment initiation endpoint (POST /payments/initiate)
    - Validate JWT token and consumer role authorization
    - Accept orderId
    - Query order to get totalAmount
    - Create Razorpay/Stripe payment session with order details
    - Generate payment redirect URL
    - Return paymentUrl, sessionId
    - _Requirements: 6.2, 7.1, 7.2_

  - [ ]\* 8.2 Write property test for payment redirect
    - **Property 26: Purchase Redirects to Payment Gateway**
    - **Validates: Requirements 6.2**

  - [x] 8.3 Create payment webhook handler (POST /payments/webhook)
    - Verify webhook signature from Razorpay/Stripe
    - Parse webhook payload for payment status
    - Extract transactionId, orderId, amount, status
    - Store transaction in DynamoDB with PK=TRANSACTION#{transactionId}, SK=METADATA
    - Set GSI2PK=ORDER#{orderId} for order association
    - If payment success: update order status to confirmed, send confirmation email to consumer and farmer
    - If payment failed: update order status to failed, send failure notification to consumer
    - Return 200 OK to webhook
    - _Requirements: 6.3, 6.4, 7.3, 7.4, 7.5_

  - [ ]\* 8.4 Write property test for payment outcome handling
    - **Property 27: Payment Outcome Updates Order Status Correctly**
    - **Validates: Requirements 6.3, 6.4**

  - [ ]\* 8.5 Write property test for transaction ID storage
    - **Property 30: Payment Processing Returns Transaction ID**
    - **Validates: Requirements 7.3**

  - [ ]\* 8.6 Write property test for transaction persistence
    - **Property 31: Transactions Are Persisted with Order Association**
    - **Validates: Requirements 7.4**

  - [ ]\* 8.7 Write property test for farmer payment notification
    - **Property 32: Successful Payments Notify Farmers**
    - **Validates: Requirements 7.5**

  - [x] 8.4 Create payment status endpoint (GET /payments/{transactionId})
    - Query transaction by PK=TRANSACTION#{transactionId}
    - Return transaction status and details
    - _Requirements: 7.3_

### Phase 7: Review and Rating Service

- [x] 9. Implement review Lambda function
  - [x] 9.1 Create review submission endpoint (POST /reviews)
    - Validate JWT token and consumer role authorization
    - Accept productId, orderId, rating (1-5), reviewText, photoUploadCount
    - Verify consumer has purchased the product (query order)
    - Validate rating is integer between 1 and 5
    - Generate unique reviewId (UUID v4)
    - Store review in DynamoDB with PK=PRODUCT#{productId}, SK=REVIEW#{reviewId}
    - Set GSI2PK=FARMER#{farmerId}, GSI3PK=CONSUMER#{consumerId} for queries
    - Generate S3 pre-signed URLs for photo uploads if photoUploadCount > 0
    - Trigger rating aggregation (update product and farmer average ratings)
    - Return reviewId, photoUploadUrls
    - _Requirements: 14.2, 14.3, 14.4_

  - [ ]\* 9.2 Write property test for rating range validation
    - **Property 65: Rating Submissions Are Within Valid Range**
    - **Validates: Requirements 14.2**

  - [ ]\* 9.3 Write property test for review storage
    - **Property 66: Review Text and Photos Are Stored**
    - **Validates: Requirements 14.3, 14.4**

  - [x] 9.4 Create product reviews endpoint (GET /reviews/product/{productId})
    - Query DynamoDB with PK=PRODUCT#{productId}, SK begins_with REVIEW#
    - Sort by createdAt descending (most recent first)
    - Return reviews array with rating, reviewText, photos, createdAt
    - _Requirements: 14.7_

  - [ ]\* 9.5 Write property test for review chronological order
    - **Property 69: Reviews Are Displayed in Reverse Chronological Order**
    - **Validates: Requirements 14.7**

  - [x] 9.6 Create farmer reviews endpoint (GET /reviews/farmer/{farmerId})
    - Query GSI2 with GSI2PK=FARMER#{farmerId}
    - Return all reviews for farmer's products
    - _Requirements: 14.6_

  - [x] 9.7 Implement rating aggregation function
    - Query all reviews for a product
    - Calculate average rating as mean of all ratings
    - Update product.averageRating and product.totalReviews
    - Query all reviews for all farmer's products
    - Calculate farmer average rating
    - Update farmer.averageRating and farmer.totalReviews
    - _Requirements: 14.5, 14.6_

  - [ ]\* 9.8 Write property test for product rating update
    - **Property 67: Reviews Update Product Average Rating**
    - **Validates: Requirements 14.5**

  - [ ]\* 9.9 Write property test for farmer rating update
    - **Property 68: Reviews Update Farmer Average Rating**
    - **Validates: Requirements 14.6**

  - [x] 9.10 Create review request email trigger
    - Listen to DynamoDB Stream for order status changes
    - When order status changes to delivered, schedule review request email
    - Send email via SES within 24 hours of delivery
    - _Requirements: 14.1_

  - [ ]\* 9.11 Write property test for review request trigger
    - **Property 64: Delivered Orders Trigger Review Requests**
    - **Validates: Requirements 14.1**

### Phase 8: Referral System

- [x] 10. Implement referral Lambda function
  - [x] 10.1 Create referral link generation endpoint (POST /referrals/generate)
    - Validate JWT token and consumer role authorization
    - Accept productId
    - Generate unique referralCode (8-char alphanumeric)
    - Check for code collision, regenerate if exists
    - Store referral in DynamoDB with PK=REFERRAL#{referralCode}, SK=METADATA
    - Set GSI2PK=REFERRER#{referrerId} for user's referrals query
    - Construct referralUrl with code and productId
    - Return referralCode, referralUrl
    - _Requirements: 13.1, 13.2_

  - [ ]\* 10.2 Write property test for referral code uniqueness
    - **Property 60: Referral Codes Are Unique per User-Product Combination**
    - **Validates: Requirements 13.2**

  - [x] 10.3 Create referral validation endpoint (GET /referrals/{code})
    - Query referral by PK=REFERRAL#{code}
    - Return referral details (referrerId, productId)
    - _Requirements: 13.2_

  - [x] 10.4 Create referral conversion tracking endpoint (POST /referrals/track)
    - Accept referralCode, orderId
    - Query referral record
    - Calculate reward amount (e.g., 5% of order total)
    - Add conversion to referral.conversions array
    - Update referral.totalConversions and referral.totalRewards
    - Update referrer's consumerProfile.referralRewardBalance
    - Store conversion metrics
    - _Requirements: 13.3, 13.5_

  - [ ]\* 10.5 Write property test for referral conversion crediting
    - **Property 61: Referral Conversions Credit Referrers**
    - **Validates: Requirements 13.3**

  - [ ]\* 10.6 Write property test for referral metrics persistence
    - **Property 63: Referral Metrics Are Persisted**
    - **Validates: Requirements 13.5**

  - [x] 10.7 Create referral rewards endpoint (GET /referrals/rewards)
    - Validate JWT token and consumer role authorization
    - Query user's consumerProfile for referralRewardBalance
    - Query user's referrals using GSI2 with GSI2PK=REFERRER#{userId}
    - Return reward balance, total conversions, redemption options
    - _Requirements: 13.4_

  - [ ]\* 10.8 Write property test for reward display
    - **Property 62: Referral Rewards Are Displayed**
    - **Validates: Requirements 13.4**

### Phase 9: Promotion Service

- [x] 11. Implement promotion Lambda function
  - [x] 11.1 Create promotion creation endpoint (POST /promotions)
    - Validate JWT token and farmer role authorization
    - Accept productId, budget, duration (days)
    - Query farmer account balance
    - Validate budget <= farmer balance
    - Generate unique promotionId (UUID v4)
    - Calculate startDate (now) and endDate (now + duration days)
    - Generate AI promotional ad copy via Bedrock
    - Store promotion in DynamoDB with PK=PROMOTION#{promotionId}, SK=METADATA, status=active
    - Set GSI2PK=FARMER#{farmerId}, GSI3PK=STATUS#active, GSI3SK=PROMOTION#{endDate}
    - Deduct budget from farmer balance
    - Return promotionId, startDate, endDate, aiGeneratedAdCopy
    - _Requirements: 15.1, 15.2, 15.4_

  - [ ]\* 11.2 Write property test for promotion balance validation
    - **Property 70: Promotions Require Sufficient Balance**
    - **Validates: Requirements 15.2**

  - [ ]\* 11.3 Write property test for AI ad copy generation
    - **Property 72: Promotions Generate AI Ad Copy**
    - **Validates: Requirements 15.4**

  - [x] 11.4 Create active promotions listing endpoint (GET /promotions)
    - Query GSI3 with GSI3PK=STATUS#active
    - Return active promotions with product details
    - _Requirements: 15.3_

  - [ ]\* 11.5 Write property test for featured placement
    - **Property 71: Active Promotions Appear in Featured Sections**
    - **Validates: Requirements 15.3**

  - [x] 11.6 Create promotion metrics endpoint (GET /promotions/{promotionId}/metrics)
    - Validate JWT token and farmer role authorization
    - Query promotion record
    - Return metrics (views, clicks, conversions, spent)
    - _Requirements: 15.5_

  - [ ]\* 11.7 Write property test for promotion metrics tracking
    - **Property 73: Promotion Metrics Are Tracked**
    - **Validates: Requirements 15.5**

  - [x] 11.8 Create promotion update endpoint (PUT /promotions/{promotionId})
    - Accept status change (active, paused, cancelled)
    - Update promotion record
    - If ending promotion, send summary email via SES
    - _Requirements: 15.6_

  - [ ]\* 11.9 Write property test for promotion summary reports
    - **Property 74: Expired Promotions Send Summary Reports**
    - **Validates: Requirements 15.6**

  - [x] 11.10 Create EventBridge rule for promotion expiry
    - Schedule hourly check for promotions past endDate
    - Update status to completed
    - Send summary email to farmer
    - _Requirements: 15.6_

### Phase 10: Limited Release Service

- [~] 12. Implement limited release Lambda function
  - [x] 12.1 Create limited release creation endpoint (POST /limited-releases)
    - Validate JWT token and farmer role authorization
    - Accept productId, releaseName, quantityLimit, duration (1-30 days)
    - Validate quantityLimit is positive integer
    - Validate duration is between 1 and 30 days
    - Generate unique releaseId (UUID v4)
    - Calculate startDate (now) and endDate (now + duration days)
    - Store limited release in DynamoDB with PK=LIMITED_RELEASE#{releaseId}, SK=METADATA
    - Set status=active, quantityRemaining=quantityLimit
    - Set GSI2PK=FARMER#{farmerId}, GSI3PK=STATUS#active, GSI3SK=RELEASE#{endDate}
    - Query all consumers with limitedReleases notification preference enabled
    - Send email notifications via SES to subscribers
    - Return releaseId, startDate, endDate, status
    - _Requirements: 11.1, 11.2, 11.3, 11.4_

  - [ ]\* 12.2 Write property test for valid limited release creation
    - **Property 48: Valid Limited Releases Are Created**
    - **Validates: Requirements 11.1**

  - [ ]\* 12.3 Write property test for non-positive quantity rejection
    - **Property 49: Non-Positive Quantity Limits Are Rejected**
    - **Validates: Requirements 11.2**

  - [ ]\* 12.4 Write property test for duration validation
    - **Property 50: Duration Outside Valid Range Is Rejected**
    - **Validates: Requirements 11.3**

  - [ ]\* 12.5 Write property test for subscriber notifications
    - **Property 51: Limited Release Creation Notifies Subscribers**
    - **Validates: Requirements 11.4**

  - [x] 12.6 Create active limited releases listing endpoint (GET /limited-releases)
    - Query GSI3 with GSI3PK=STATUS#active
    - Return active releases with product details, quantityRemaining, countdown
    - _Requirements: 11.5_

  - [x] 12.7 Create limited release detail endpoint (GET /limited-releases/{releaseId})
    - Query release by PK=LIMITED_RELEASE#{releaseId}
    - Calculate time remaining until endDate
    - Return release details with countdown timer data
    - _Requirements: 11.5_

  - [x] 12.8 Create limited release purchase endpoint (POST /limited-releases/{releaseId}/purchase)
    - Validate JWT token and consumer role authorization
    - Query release to verify status=active and quantityRemaining > 0
    - Decrement quantityRemaining using conditional update
    - If quantityRemaining reaches 0, update status to sold_out
    - Create order record (reuse order creation logic)
    - Return orderId
    - _Requirements: 11.5_

  - [ ]\* 12.9 Write property test for sold out status
    - **Property 52: Sold Out Limited Releases Display Correct Status**
    - **Validates: Requirements 11.5**

  - [x] 12.10 Create EventBridge rule for limited release expiry
    - Schedule every 5 minutes to check for releases past endDate
    - Update status to expired
    - Remove from marketplace listings
    - _Requirements: 11.6_

  - [ ]\* 12.11 Write property test for automatic delisting
    - **Property 53: Expired Limited Releases Are Delisted**
    - **Validates: Requirements 11.6**

### Phase 11: Farmer Incentive System

- [~] 13. Implement farmer bonus tracking
  - [x] 13.1 Create sales streak tracking function
    - Listen to DynamoDB Stream for new reviews
    - Query farmer's last 10 orders with reviews
    - Check if all reviews have rating >= 3 stars
    - If yes and consecutiveSalesStreak reaches 10, award bonus
    - Update farmer.consecutiveSalesStreak and farmer.bonusesEarned
    - Send bonus notification email via SES
    - _Requirements: 12.1, 12.4_

  - [ ]\* 13.2 Write property test for sales streak bonus
    - **Property 54: Sales Streak Bonus Awards at Threshold**
    - **Validates: Requirements 12.1**

  - [ ]\* 13.3 Write property test for bonus notifications
    - **Property 57: Bonus Awards Trigger Notifications**
    - **Validates: Requirements 12.4**

  - [x] 13.4 Create featured placement eligibility function
    - Calculate average authenticityConfidence across all farmer's products
    - If average > 90%, set farmer.featuredStatus = true
    - Update farmer record in DynamoDB
    - _Requirements: 12.2_

  - [ ]\* 13.5 Write property test for featured placement
    - **Property 55: High Authenticity Scores Grant Featured Placement**
    - **Validates: Requirements 12.2**

  - [x] 13.6 Create farmer bonus dashboard endpoint (GET /analytics/farmer/{farmerId}/bonuses)
    - Validate JWT token and farmer role authorization
    - Query farmer record for bonusesEarned, consecutiveSalesStreak, featuredStatus
    - Calculate progress toward next bonus (e.g., 7/10 sales)
    - Return bonus status, total bonuses, progress
    - _Requirements: 12.3, 12.5_

  - [ ]\* 13.7 Write property test for bonus display
    - **Property 56: Bonus Status and Progress Are Displayed**
    - **Validates: Requirements 12.3**

  - [ ]\* 13.8 Write property test for total bonuses tracking
    - **Property 58: Total Bonuses Are Tracked Accurately**
    - **Validates: Requirements 12.5**

### Phase 12: Analytics Service

- [~] 14. Implement analytics Lambda function
  - [x] 14.1 Create farmer analytics dashboard endpoint (GET /analytics/farmer/{farmerId})
    - Validate JWT token and farmer role authorization
    - Query all orders for farmer using GSI3 with GSI3PK=FARMER#{farmerId}
    - Filter orders by current month and status=delivered
    - Calculate monthlyRevenue as sum of order amounts
    - Calculate totalSales count
    - Query farmer record for averageRating, totalReviews
    - Query all farmer's products for view counts
    - Calculate conversion rates (orders / views)
    - Identify top products by revenue
    - Return analytics object with all metrics
    - _Requirements: 17.1, 17.2, 17.3, 17.5_

  - [ ]\* 14.2 Write property test for monthly revenue calculation
    - **Property 79: Monthly Revenue Is Calculated Correctly**
    - **Validates: Requirements 17.1**

  - [ ]\* 14.3 Write property test for conversion rate calculation
    - **Property 80: Conversion Rates Are Calculated Accurately**
    - **Validates: Requirements 17.2**

  - [ ]\* 14.4 Write property test for rating aggregation
    - **Property 81: Product Ratings and Review Counts Are Aggregated**
    - **Validates: Requirements 17.3**

  - [ ]\* 14.5 Write property test for top products ranking
    - **Property 82: Top Products Are Ranked by Revenue**
    - **Validates: Requirements 17.5**

  - [x] 14.6 Create product analytics endpoint (GET /analytics/product/{productId})
    - Query product for viewCount, totalSales, averageRating
    - Calculate conversion rate
    - Return product performance metrics
    - _Requirements: 17.2, 17.3_

  - [x] 14.7 Create seasonal trends endpoint (GET /analytics/trends)
    - Query all products grouped by category and seasonal status
    - Calculate sales trends by season
    - Return trend data
    - _Requirements: 17.4_

### Phase 13: Notification Service

- [~] 15. Implement notification Lambda function
  - [x] 15.1 Create notification preference management endpoint (PUT /notifications/preferences)
    - Validate JWT token
    - Accept notification preferences object (newProducts, promotions, orderUpdates, etc.)
    - Update user's notificationPreferences in DynamoDB
    - Return updated preferences
    - _Requirements: 16.1, 16.4_

  - [ ]\* 15.2 Write property test for preference updates
    - **Property 77: Notification Preferences Can Be Updated**
    - **Validates: Requirements 16.4**

  - [x] 15.3 Create new product notification trigger
    - Listen to DynamoDB Stream for product status changes
    - When product changes from pending to approved, query consumers with newProducts=true
    - Send email notifications via SES
    - _Requirements: 16.2_

  - [ ]\* 15.4 Write property test for new product notifications
    - **Property 75: New Product Launches Notify Subscribers**
    - **Validates: Requirements 16.2**

  - [x] 15.5 Create followed farmer notification trigger
    - When farmer creates new product, query consumers in followedFarmers array
    - Send email notifications via SES
    - _Requirements: 16.3_

  - [ ]\* 15.6 Write property test for followed farmer notifications
    - **Property 76: Followed Farmers' Products Notify Followers**
    - **Validates: Requirements 16.3**

  - [x] 15.7 Create unsubscribe endpoint (POST /notifications/unsubscribe)
    - Accept email or userId
    - Set user.notificationPreferences.unsubscribedAt = now
    - Disable all marketing notifications
    - Keep transactional notifications enabled
    - _Requirements: 16.5_

  - [ ]\* 15.8 Write property test for unsubscribe handling
    - **Property 78: Unsubscribed Users Receive No Marketing Emails**
    - **Validates: Requirements 16.5**

  - [x] 15.9 Create email sending helper function
    - Accept recipient, template, data
    - Check user notification preferences
    - If unsubscribed and email is marketing, skip
    - Send email via boto3 SES client
    - Log email sent event
    - _Requirements: 16.5_

- [x] 16. Checkpoint - Ensure all backend tests pass
  - Run all property-based tests with hypothesis (100+ iterations each)
  - Run all unit tests for Lambda functions
  - Verify DynamoDB operations work correctly
  - Verify S3 operations work correctly
  - Verify Bedrock integration works correctly
  - Ensure all tests pass, ask the user if questions arise.

### Phase 14: Frontend - Shared Components and Context

- [x] 17. Set up React frontend project structure
  - Create React app with TypeScript using Vite or Create React App
  - Install dependencies: react-router-dom, axios, @aws-sdk/client-s3, tailwindcss, etc.
  - Create directory structure: `src/components/`, `src/pages/`, `src/contexts/`, `src/services/`, `src/types/`
  - Configure Tailwind CSS for styling
  - Create environment variables file for API endpoint
  - _Requirements: 19.5_

- [x] 18. Create authentication context and shared components
  - [x] 18.1 Create AuthContext (src/contexts/AuthContext.tsx)
    - Implement useAuth hook with login, logout, register functions
    - Store JWT token in localStorage
    - Decode token to get userId and role
    - Provide authentication state to app
    - _Requirements: 1.1, 1.2_

  - [x] 18.2 Create LoginForm component (src/components/auth/LoginForm.tsx)
    - Email and password input fields
    - Role selection (farmer/consumer)
    - Call /auth/login API endpoint
    - Store token in AuthContext
    - Redirect to appropriate portal based on role
    - _Requirements: 1.2_

  - [x] 18.3 Create RegistrationForm component (src/components/auth/RegistrationForm.tsx)
    - Email, password, firstName, lastName, phone, role inputs
    - Client-side validation (email format, password min 8 chars)
    - Call /auth/register API endpoint
    - Show success message and redirect to login
    - _Requirements: 1.1_

  - [x] 18.4 Create ProtectedRoute component (src/components/auth/ProtectedRoute.tsx)
    - Check authentication status from AuthContext
    - Check user role matches required role
    - Redirect to login if not authenticated
    - Redirect to home if wrong role
    - _Requirements: 1.2_

  - [x] 18.5 Create ProductCard component (src/components/shared/ProductCard.tsx)
    - Display product image, name, price, farmer name, rating
    - Show GI badge if product has GI tag
    - Show authenticity confidence score
    - Show scarcity indicators (low stock, viewers, recent purchases)
    - Click handler to navigate to product detail
    - _Requirements: 4.6, 9.1, 9.2, 10.1, 10.3, 10.4_

  - [ ]\* 18.6 Write unit tests for ProductCard component
    - Test rendering with various product data
    - Test GI badge display logic
    - Test scarcity indicator display

  - [x] 18.7 Create ImageUploader component (src/components/shared/ImageUploader.tsx)
    - File input with drag-and-drop support
    - Image preview before upload
    - Upload to S3 using pre-signed URLs
    - Progress indicator
    - _Requirements: 2.2_

  - [x] 18.8 Create NotificationCenter component (src/components/shared/NotificationCenter.tsx)
    - Display notification preferences checkboxes
    - Call /notifications/preferences API to update
    - _Requirements: 16.1, 16.4_

### Phase 15: Frontend - Consumer Portal

- [~] 19. Create consumer portal pages and components
  - [~] 19.1 Create MarketplaceBrowser page (src/pages/consumer/MarketplaceBrowser.tsx)
    - Grid/list view toggle for products
    - Call /products API endpoint with filters
    - Display ProductCard components for each product
    - Implement pagination using cursor
    - _Requirements: 4.1, 4.6_

  - [~] 19.2 Create FilterPanel component (src/components/consumer/FilterPanel.tsx)
    - Category dropdown (vegetables, fruits, grains, spices, dairy)
    - Seasonal checkbox filter
    - GI tag checkbox filter
    - Price range slider
    - Apply filters to marketplace query
    - _Requirements: 4.2, 4.3, 4.4_

  - [ ]\* 19.3 Write property test for filter combinations
    - Test that all filter combinations return valid results

  - [~] 19.4 Create SearchBar component (src/components/consumer/SearchBar.tsx)
    - Text input with search icon
    - Autocomplete suggestions (optional)
    - Call /products API with search query parameter
    - _Requirements: 4.5_

  - [~] 19.5 Create ProductDetailView page (src/pages/consumer/ProductDetailView.tsx)
    - Call /products/{productId} API endpoint
    - Display full product details (description, images, price, GI tag)
    - Display authenticity confidence score with explanation
    - Display farmer profile with ratings
    - Display customer reviews with photos
    - Display scarcity indicators (viewers, stock, countdown)
    - Display value equation elements (dream outcome, guaranteed delivery)
    - Add to cart / purchase button
    - Share button for referral link generation
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 9.1, 9.2, 9.3, 10.1, 10.2, 10.3, 10.4, 13.1_

  - [~] 19.6 Create ShoppingCart component (src/components/consumer/ShoppingCart.tsx)
    - Display selected products with quantities
    - Calculate total amount
    - Delivery address form
    - Referral code input (optional)
    - Checkout button to create order
    - _Requirements: 6.1_

  - [~] 19.7 Create OrderHistory page (src/pages/consumer/OrderHistory.tsx)
    - Call /orders API endpoint
    - Display orders list with status, date, amount
    - Click to view order details
    - _Requirements: 6.1_

  - [~] 19.8 Create ReviewForm component (src/components/consumer/ReviewForm.tsx)
    - Star rating selector (1-5)
    - Review text textarea
    - Photo upload using ImageUploader
    - Submit button to call /reviews API
    - _Requirements: 14.2, 14.3, 14.4_

  - [~] 19.9 Create ReferralDashboard page (src/pages/consumer/ReferralDashboard.tsx)
    - Display referral reward balance
    - Display referral link for sharing
    - Display conversion count
    - Display redemption options
    - _Requirements: 13.4_

### Phase 16: Frontend - Farmer Portal

- [~] 20. Create farmer portal pages and components
  - [~] 20.1 Create ProductUploadForm page (src/pages/farmer/ProductUploadForm.tsx)
    - Multi-step form wizard (details → images → documentation)
    - Step 1: Product details (name, category, price, unit, description, quantity)
    - Step 2: GI tag information (hasTag, tagName, region)
    - Step 3: Seasonal information (isSeasonal, seasonStart, seasonEnd)
    - Step 4: Image uploads using ImageUploader (multiple images)
    - Step 5: Invoice document upload
    - Call /products API to create product
    - Upload images to S3 using pre-signed URLs
    - Show success message with pending verification status
    - _Requirements: 2.1, 2.2, 2.4, 2.5_

  - [~] 20.2 Create ProductListView page (src/pages/farmer/ProductListView.tsx)
    - Call /products API filtered by farmerId
    - Display farmer's products in table/grid
    - Show status indicators (pending, approved, flagged)
    - Show verification scores (fraud risk, authenticity confidence)
    - Edit and delete buttons for each product
    - _Requirements: 2.1, 3.3, 3.4_

  - [~] 20.3 Create AnalyticsDashboard page (src/pages/farmer/AnalyticsDashboard.tsx)
    - Call /analytics/farmer/{farmerId} API endpoint
    - Display monthly revenue chart
    - Display total sales count
    - Display average rating and review count
    - Display top products by revenue
    - Display conversion rates by product
    - Display bonus status and progress
    - _Requirements: 17.1, 17.2, 17.3, 17.5, 12.3_

  - [~] 20.4 Create MarketingContentGenerator component (src/components/farmer/MarketingContentGenerator.tsx)
    - Product selection dropdown
    - Content type selection (description, social, launch, names)
    - Generate button to call /ai/generate-\* APIs
    - Display AI-generated content
    - Edit textarea for farmer to modify content
    - Save button to update product with selected content
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.6, 18.1, 18.2, 18.3, 18.4_

  - [ ]\* 20.5 Write unit tests for MarketingContentGenerator
    - Test content generation for each type
    - Test farmer editing functionality

  - [~] 20.6 Create PromotionManager page (src/pages/farmer/PromotionManager.tsx)
    - Product selection for promotion
    - Budget and duration inputs
    - Call /promotions API to create promotion
    - Display active promotions list
    - Display promotion metrics (views, clicks, conversions)
    - Pause/cancel promotion buttons
    - _Requirements: 15.1, 15.2, 15.3, 15.5_

  - [~] 20.7 Create LimitedReleaseCreator page (src/pages/farmer/LimitedReleaseCreator.tsx)
    - Product selection
    - Release name input
    - Quantity limit input (positive integer validation)
    - Duration input (1-30 days validation)
    - Call /limited-releases API to create release
    - Display active limited releases list
    - Show quantity remaining and countdown
    - _Requirements: 11.1, 11.2, 11.3_

  - [~] 20.8 Create BonusTracker component (src/components/farmer/BonusTracker.tsx)
    - Display current sales streak progress (e.g., 7/10)
    - Display total bonuses earned
    - Display featured status badge
    - Display bonus history
    - _Requirements: 12.3, 12.5_

### Phase 17: Frontend - Value Equation and Engagement Features

- [~] 21. Implement value equation optimization features
  - [~] 21.1 Create ValueEquationDisplay component (src/components/shared/ValueEquationDisplay.tsx)
    - Display dream outcome statement prominently
    - Display GI badge for perceived likelihood
    - Display guaranteed delivery messaging
    - Display estimated delivery time
    - Display one-click ordering button
    - Calculate and display value score (optional visual indicator)
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6_

  - [ ]\* 21.2 Write property test for value equation calculation
    - **Property 42: Value Equation Is Calculated for Products**
    - **Validates: Requirements 9.6**

  - [~] 21.3 Create ScarcityIndicators component (src/components/shared/ScarcityIndicators.tsx)
    - Display remaining quantity if <= 50
    - Display countdown timer for seasonal products
    - Display current viewers count (real-time via polling or WebSocket)
    - Display recent purchase count (last 24h)
    - Display low stock warning if quantity < 10
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5_

  - [ ]\* 21.4 Write property tests for scarcity indicators
    - **Property 43: Limited Quantity Products Display Remaining Stock**
    - **Property 44: Seasonal Products Display Countdown Timer**
    - **Property 45: Concurrent Viewers Are Tracked and Displayed**
    - **Property 46: Recent Purchase Count Is Displayed**
    - **Property 47: Low Stock Warning Appears Below Threshold**
    - **Validates: Requirements 10.1, 10.2, 10.3, 10.4, 10.5**

  - [~] 21.5 Implement viewer count tracking
    - On ProductDetailView mount, increment currentViewers in backend
    - On unmount, decrement currentViewers
    - Poll /products/{productId} every 10 seconds to update viewer count
    - _Requirements: 10.3_

  - [~] 21.6 Create GI badge component (src/components/shared/GIBadge.tsx)
    - Display verified GI badge icon
    - Show GI tag name and region on hover
    - Only display if product.giTag.hasTag is true
    - _Requirements: 4.4, 9.2_

  - [ ]\* 21.7 Write property test for GI badge display
    - **Property 20: GI Badge Display Matches GI Tag Presence**
    - **Validates: Requirements 4.4, 9.2**

### Phase 18: Integration and Wiring

- [x] 22. Wire all components together and implement routing
  - [x] 22.1 Create main App component with routing
    - Set up React Router with routes for all pages
    - Implement role-based routing (farmer vs consumer portals)
    - Create navigation bar with role-specific links
    - Implement logout functionality
    - _Requirements: 1.2_

  - [x] 22.2 Create API service layer (src/services/api.ts)
    - Axios instance with base URL from environment
    - Request interceptor to add JWT token to headers
    - Response interceptor for error handling
    - Helper functions for all API endpoints
    - _Requirements: 1.2_

  - [x] 22.3 Implement payment flow integration
    - On checkout, call /payments/initiate API
    - Redirect to payment gateway URL
    - Handle payment callback/redirect back to app
    - Display payment success/failure message
    - _Requirements: 6.2, 6.3, 6.4, 7.1, 7.2_

  - [x] 22.4 Implement referral link sharing
    - On share button click, call /referrals/generate API
    - Display referral URL in modal
    - Copy to clipboard functionality
    - Social media share buttons (optional)
    - _Requirements: 13.1, 13.2_

  - [ ]\* 22.5 Write property test for referral link generation
    - **Property 59: Products Display Share Button with Referral Link**
    - **Validates: Requirements 13.1**

  - [x] 22.6 Implement AI content selection flow
    - Display AI-generated name/description variations
    - Allow farmer to select one or keep original
    - Update product with selected content
    - _Requirements: 18.4, 8.6_

  - [ ]\* 22.7 Write property test for AI content selection
    - **Property 36: Farmers Can Edit AI-Generated Content**
    - **Property 39: Farmers Can Select from AI Suggestions or Original**
    - **Validates: Requirements 8.6, 18.4**

  - [x] 22.8 Implement product listing display requirements
    - Ensure marketplace listings show all required fields
    - Ensure product detail view shows complete information
    - Ensure review photos display when present
    - _Requirements: 4.6, 5.1, 5.2, 5.3, 5.4, 5.5_

  - [ ]\* 22.9 Write property tests for display requirements
    - **Property 22: Product Listings Include Required Display Fields**
    - **Property 23: Product Detail View Includes Complete Information**
    - **Property 24: Review Photos Display When Present**
    - **Validates: Requirements 4.6, 5.1, 5.2, 5.3, 5.4, 5.5**

- [~] 23. Checkpoint - Ensure all frontend tests pass
  - Run all frontend unit tests
  - Run all property-based tests for components
  - Test authentication flow end-to-end
  - Test product upload and verification flow
  - Test order and payment flow
  - Test referral flow
  - Ensure all tests pass, ask the user if questions arise.

### Phase 19: Infrastructure Cost Optimization

- [x] 24. Implement cost optimization features
  - [x] 24.1 Configure S3 lifecycle policies
    - Set up transition to Standard-IA after 30 days
    - Set up deletion of temp-uploads after 1 day
    - Verify lifecycle rules in SAM template
    - _Requirements: 19.3_

  - [ ]\* 24.2 Write property test for S3 lifecycle transitions
    - **Property 83: S3 Images Transition to Standard-IA After 30 Days**
    - **Validates: Requirements 19.3**

  - [x] 24.3 Implement Bedrock response caching
    - Create cache table in DynamoDB or use existing table
    - Cache key: hash of (productId + operation type)
    - Cache fraud detection results for 24 hours
    - Cache marketing content for 7 days
    - Check cache before invoking Bedrock
    - Store Bedrock response in cache after invocation
    - _Requirements: 19.4_

  - [ ]\* 24.4 Write property test for Bedrock caching
    - **Property 84: Bedrock Requests Are Cached**
    - **Validates: Requirements 19.4**

  - [x] 24.5 Set up CloudWatch cost monitoring
    - Create CloudWatch dashboard for daily costs
    - Create alarm for 80% budget threshold ($240)
    - Create alarm for 90% budget threshold ($270)
    - Send SNS notifications to admin email
    - _Requirements: 19.6_

  - [ ]\* 24.6 Write property test for cost alerts
    - **Property 85: Cost Alerts Trigger at Budget Thresholds**
    - **Validates: Requirements 19.6**

  - [x] 24.7 Optimize Lambda function configurations
    - Set appropriate memory sizes (512MB default, tune per function)
    - Set appropriate timeouts (30s default, 60s for AI functions)
    - Use ARM64 architecture for 20% cost savings
    - Minimize cold starts with code optimization
    - _Requirements: 19.1_

  - [x] 24.8 Configure API Gateway caching
    - Enable caching for GET /products endpoint (5 min TTL)
    - Enable caching for GET /products/{productId} endpoint (1 hour TTL)
    - Cache key includes query parameters and user role
    - _Requirements: 19.1_

### Phase 20: Deployment and Documentation

- [~] 25. Complete AWS SAM template and deployment configuration
  - [~] 25.1 Finalize SAM template with all resources
    - All 13 Lambda functions with correct IAM policies
    - DynamoDB table with streams enabled
    - S3 bucket with lifecycle policies and CORS
    - API Gateway with all endpoints and authorizer
    - Secrets Manager for JWT secret and API keys
    - EventBridge rules for scheduled tasks
    - CloudWatch alarms for monitoring
    - AWS Budgets for cost alerts
    - _Requirements: 21.1, 21.2, 21.3, 21.4_

  - [~] 25.2 Create deployment scripts
    - `deploy.sh` script to build and deploy SAM stack
    - `deploy-frontend.sh` script to deploy React app to Amplify
    - Environment-specific configuration (dev, prod)
    - _Requirements: 21.4, 21.5_

  - [~] 25.3 Create environment configuration files
    - `.env.dev` for development environment
    - `.env.prod` for production environment
    - Document required environment variables
    - _Requirements: 21.5_

  - [x] 25.4 Test deployment to AWS
    - Deploy SAM stack to AWS account
    - Verify all resources created successfully
    - Test API endpoints with Postman/curl
    - Deploy frontend to Amplify
    - Verify frontend can communicate with backend
    - _Requirements: 21.4_

- [~] 26. Create comprehensive documentation
  - [~] 26.1 Create architecture diagram
    - Visual diagram showing all AWS services
    - Data flow between components
    - User interaction flows
    - Include in README or separate doc
    - _Requirements: 22.1_

  - [~] 26.2 Document AI value proposition
    - Explain why AI is required for fraud detection
    - Explain why AI is required for marketing content
    - Describe how Bedrock is used
    - Describe benefits to farmers and consumers
    - _Requirements: 22.2, 22.6_

  - [~] 26.3 Document AWS service utilization
    - Describe how each AWS service is used
    - Explain architectural decisions
    - Document cost optimization strategies
    - _Requirements: 22.3_

  - [~] 26.4 Create cost estimation breakdown
    - Detailed cost breakdown by service
    - Daily and monthly cost estimates
    - Explain how platform stays within $300 budget
    - _Requirements: 22.4_

  - [~] 26.5 Create setup and deployment instructions
    - Prerequisites (AWS account, AWS CLI, SAM CLI, Node.js, Python)
    - Step-by-step deployment instructions
    - Configuration instructions
    - Testing instructions
    - Troubleshooting guide
    - _Requirements: 22.5_

  - [~] 26.6 Create user guide
    - How farmers can upload products
    - How consumers can browse and purchase
    - How to use AI marketing features
    - How referral system works
    - _Requirements: 22.6_

  - [~] 26.7 Create API documentation
    - Document all API endpoints
    - Request/response schemas
    - Authentication requirements
    - Error codes and messages
    - _Requirements: 22.3_

- [~] 27. Final checkpoint - End-to-end testing and validation
  - Deploy complete platform to AWS
  - Test complete user flows:
    - Farmer registration → product upload → AI verification → marketplace listing
    - Consumer registration → browse marketplace → purchase → payment → review
    - Farmer creates promotion → consumer sees featured product
    - Farmer creates limited release → consumer receives notification → purchase
    - Consumer shares referral link → referred user purchases → referrer gets reward
  - Verify all 85 correctness properties are satisfied
  - Monitor AWS costs and verify staying within budget
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional property-based tests and can be skipped for faster MVP delivery
- Each task references specific requirements for traceability
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- Checkpoints ensure incremental validation at key milestones
- Implementation uses Python 3.11 for backend Lambda functions
- Frontend uses React with TypeScript
- Infrastructure uses AWS SAM for deployment
- Budget constraint: $300 AWS credits for 30+ days

## Implementation Strategy

1. Start with infrastructure setup to establish foundation
2. Build backend services incrementally, testing each service before moving to next
3. Implement frontend after backend APIs are stable
4. Wire everything together and test end-to-end flows
5. Optimize for cost and performance
6. Document thoroughly for hackathon judges

## Success Criteria

- All 22 requirements implemented and validated
- All 85 correctness properties satisfied
- Platform operates within $300 AWS budget for 30+ days
- Complete documentation for judges and users
- Deployable with single command
- Comprehensive test coverage (property tests + unit tests)
