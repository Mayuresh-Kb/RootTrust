# Authentication Service

This directory contains Lambda functions for user authentication in the RootTrust marketplace platform.

## Endpoints

### POST /auth/register

User registration endpoint that creates new farmer or consumer accounts.

#### Request Body

```json
{
  "email": "user@example.com",
  "password": "SecurePassword123",
  "role": "farmer", // or "consumer"
  "firstName": "John",
  "lastName": "Doe",
  "phone": "1234567890"
}
```

#### Validation Rules

- **email**: Valid email format (validated by email-validator)
- **password**: Minimum 8 characters, maximum 128 characters
- **role**: Must be either "farmer" or "consumer"
- **firstName**: 1-100 characters
- **lastName**: 1-100 characters
- **phone**: 10-15 digits (formatting characters removed)

#### Success Response (201 Created)

```json
{
  "success": true,
  "message": "User registered successfully",
  "userId": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "role": "farmer"
}
```

#### Error Responses

**400 Bad Request - Validation Error**

```json
{
  "success": false,
  "error": "VALIDATION_ERROR",
  "message": "Request validation failed",
  "details": [
    {
      "field": "password",
      "message": "Password must be at least 8 characters long"
    }
  ]
}
```

**409 Conflict - Duplicate Email**

```json
{
  "success": false,
  "error": "CONFLICT_ERROR",
  "message": "User with identifier user@example.com already exists"
}
```

**500 Internal Server Error**

```json
{
  "success": false,
  "error": "INTERNAL_ERROR",
  "message": "An unexpected error occurred"
}
```

## Implementation Details

### Password Security

- Passwords are hashed using bcrypt with automatically generated salt
- Plain text passwords are never stored in the database
- Password hashes are stored in the `passwordHash` field

### User ID Generation

- User IDs are generated using UUID v4 for uniqueness
- Format: `550e8400-e29b-41d4-a716-446655440000`

### DynamoDB Storage

**User Record**

- PK: `USER#{userId}`
- SK: `PROFILE`
- GSI2PK: `ROLE#{role}` (for role-based queries)
- GSI2SK: `USER#{createdAt}` (for chronological sorting)

**Email Lookup Record** (for duplicate checking)

- PK: `EMAIL#{email}`
- SK: `METADATA`
- Contains: `userId`, `email`

### Role-Specific Profiles

**Farmer Profile**

- farmName, farmLocation (initially empty, filled during profile completion)
- certifications (empty array)
- averageRating: 0.0
- totalReviews: 0
- totalSales: 0
- consecutiveSalesStreak: 0
- bonusesEarned: 0.0
- featuredStatus: false

**Consumer Profile**

- referralCode (8-character alphanumeric, auto-generated)
- referralRewardBalance: 0.0
- totalOrders: 0
- followedFarmers (empty array)

### Notification Preferences

All users start with default notification preferences:

- newProducts: true
- promotions: true
- orderUpdates: true
- reviewRequests: true
- limitedReleases: true
- farmerBonuses: true

## Testing

Run unit tests:

```bash
python -m pytest tests/test_auth_register.py -v
```

Run integration tests:

```bash
python tests/test_integration_register.py
```

## Dependencies

See `requirements.txt` for full list:

- boto3: AWS SDK for DynamoDB operations
- PyJWT: JWT token handling (used by other auth endpoints)
- bcrypt: Password hashing
- pydantic: Request validation
- email-validator: Email format validation

## Environment Variables

- `TABLE_NAME`: DynamoDB table name (set by SAM template)
- `DYNAMODB_TABLE_NAME`: Alternative table name variable (for compatibility)

## Related Files

- `backend/shared/models.py`: User, FarmerProfile, ConsumerProfile models
- `backend/shared/auth.py`: Password hashing utilities
- `backend/shared/database.py`: DynamoDB helper functions
- `backend/shared/validators.py`: UserRegistrationRequest validation schema
- `backend/shared/constants.py`: UserRole enum and other constants
- `backend/shared/exceptions.py`: Custom exception classes

## Requirements Validated

This endpoint implements and validates:

- **Requirement 1.1**: User registration with role selection
- **Requirement 1.4**: Secure credential storage with encryption (bcrypt hashing)

## Next Steps

After registration, users should:

1. Verify their email (optional, not yet implemented)
2. Complete their profile (farmers: farm details, consumers: preferences)
3. Login using POST /auth/login to receive JWT token
