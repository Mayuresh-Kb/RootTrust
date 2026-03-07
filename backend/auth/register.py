"""
User registration Lambda handler for RootTrust marketplace.
Handles POST /auth/register endpoint.
"""
import json
import os
import uuid
from datetime import datetime
from typing import Dict, Any

from models import User, FarmerProfile, ConsumerProfile, NotificationPreferences
from auth import hash_password
from database import put_item, get_item
from validators import UserRegistrationRequest, validate_request_body
from constants import UserRole
from exceptions import (
    RootTrustException, ValidationError, DuplicateResourceError
)
from email_service import get_email_service

# Set environment variable for database module
if 'TABLE_NAME' in os.environ:
    os.environ['DYNAMODB_TABLE_NAME'] = os.environ['TABLE_NAME']


def create_response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    """Create API Gateway response."""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,Authorization',
            'Access-Control-Allow-Methods': 'POST,OPTIONS'
        },
        'body': json.dumps(body)
    }


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for user registration.
    
    Accepts: email, password, role, firstName, lastName, phone
    Returns: userId, email, role, success message
    """
    try:
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        
        # Validate request
        registration_data = validate_request_body(body, UserRegistrationRequest)
        
        # Check if user already exists by email
        # Note: In production, we'd use a GSI on email for efficient lookup
        # For now, we'll use a simple check with email as part of a secondary key
        email_check_pk = f"EMAIL#{registration_data.email}"
        existing_user = get_item(email_check_pk, "METADATA")
        
        if existing_user:
            raise DuplicateResourceError("User", registration_data.email)
        
        # Generate unique userId
        user_id = str(uuid.uuid4())
        
        # Hash password
        password_hash = hash_password(registration_data.password)
        
        # Create timestamp
        created_at = datetime.utcnow()
        
        # Create role-specific profile
        farmer_profile = None
        consumer_profile = None
        
        if registration_data.role == UserRole.FARMER:
            farmer_profile = FarmerProfile(
                farmName="",  # To be filled in profile completion
                farmLocation="",
                certifications=[],
                averageRating=0.0,
                totalReviews=0,
                totalSales=0,
                consecutiveSalesStreak=0,
                bonusesEarned=0.0,
                featuredStatus=False
            )
        else:  # CONSUMER
            # Generate unique referral code for consumer
            referral_code = str(uuid.uuid4())[:8].upper()
            consumer_profile = ConsumerProfile(
                referralCode=referral_code,
                referralRewardBalance=0.0,
                totalOrders=0,
                followedFarmers=[]
            )
        
        # Create User model
        user = User(
            userId=user_id,
            email=registration_data.email,
            passwordHash=password_hash,
            role=registration_data.role,
            firstName=registration_data.firstName,
            lastName=registration_data.lastName,
            phone=registration_data.phone,
            createdAt=created_at,
            emailVerified=False,
            notificationPreferences=NotificationPreferences(),
            farmerProfile=farmer_profile,
            consumerProfile=consumer_profile
        )
        
        # Convert to DynamoDB item
        user_dict = user.dict()
        
        # Store user record in DynamoDB
        put_item(user_dict)
        
        # Also create email lookup record for duplicate checking
        email_lookup = {
            'PK': email_check_pk,
            'SK': 'METADATA',
            'EntityType': 'EmailLookup',
            'userId': user_id,
            'email': registration_data.email
        }
        put_item(email_lookup)
        
        # Send registration confirmation email
        try:
            email_service = get_email_service()
            
            # Generate verification link (optional for MVP)
            # In production, this would include a verification token
            verification_link = None
            if os.environ.get('ENABLE_EMAIL_VERIFICATION', 'false').lower() == 'true':
                api_endpoint = os.environ.get('API_ENDPOINT', '')
                verification_token = str(uuid.uuid4())
                verification_link = f"{api_endpoint}/auth/verify?token={verification_token}"
                # TODO: Store verification token in DynamoDB for validation
            
            email_result = email_service.send_registration_confirmation(
                user_email=registration_data.email,
                first_name=registration_data.firstName,
                user_id=user_id,
                verification_link=verification_link
            )
            
            if not email_result['success']:
                # Log the error but don't fail registration
                print(f"Failed to send confirmation email: {email_result.get('error_message')}")
        
        except Exception as e:
            # Log the error but don't fail registration
            print(f"Error sending confirmation email: {str(e)}")
        
        # Return success response
        return create_response(201, {
            'success': True,
            'message': 'User registered successfully',
            'userId': user_id,
            'email': registration_data.email,
            'role': registration_data.role.value
        })
    
    except ValidationError as e:
        return create_response(e.status_code, {
            'success': False,
            'error': e.code,
            'message': e.message,
            'details': e.details if hasattr(e, 'details') else []
        })
    
    except DuplicateResourceError as e:
        return create_response(e.status_code, {
            'success': False,
            'error': e.code,
            'message': e.message
        })
    
    except RootTrustException as e:
        return create_response(e.status_code, {
            'success': False,
            'error': e.code,
            'message': e.message
        })
    
    except Exception as e:
        import traceback
        print(f"Unexpected error: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        return create_response(500, {
            'success': False,
            'error': 'INTERNAL_ERROR',
            'message': 'An unexpected error occurred'
        })
