"""
User login Lambda handler for RootTrust marketplace.
Handles POST /auth/login endpoint.
"""
import json
import os
from typing import Dict, Any

from models import User
from auth import verify_password, generate_jwt_token
from database import get_item
from validators import UserLoginRequest, validate_request_body
from exceptions import (
    RootTrustException, ValidationError, AuthenticationError
)

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
    Lambda handler for user login.
    
    Accepts: email, password
    Returns: token, userId, role, expiresIn
    """
    try:
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        
        # Validate request
        login_data = validate_request_body(body, UserLoginRequest)
        
        # Look up user by email using email lookup record
        email_check_pk = f"EMAIL#{login_data.email}"
        email_lookup = get_item(email_check_pk, "METADATA")
        
        if not email_lookup:
            # Don't reveal whether email exists or not
            raise AuthenticationError("Invalid email or password")
        
        # Get user record
        user_id = email_lookup['userId']
        user_pk = f"USER#{user_id}"
        user_record = get_item(user_pk, "PROFILE")
        
        if not user_record:
            raise AuthenticationError("Invalid email or password")
        
        # Verify password
        if not verify_password(login_data.password, user_record['passwordHash']):
            raise AuthenticationError("Invalid email or password")
        
        # Get JWT secret from environment or Secrets Manager
        jwt_secret = os.environ.get('JWT_SECRET_KEY')
        if not jwt_secret:
            # In production, retrieve from Secrets Manager
            # For now, use environment variable
            raise AuthenticationError("Authentication service unavailable")
        
        # Generate JWT token
        token_data = generate_jwt_token(
            user_id=user_id,
            email=user_record['email'],
            role=user_record['role'],
            secret_key=jwt_secret
        )
        
        # Return success response with token
        return create_response(200, {
            'success': True,
            'token': token_data['token'],
            'userId': token_data['userId'],
            'role': token_data['role'],
            'expiresIn': token_data['expiresIn']
        })
    
    except ValidationError as e:
        return create_response(e.status_code, {
            'success': False,
            'error': e.code,
            'message': e.message,
            'details': e.details if hasattr(e, 'details') else []
        })
    
    except AuthenticationError as e:
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
        print(f"Unexpected error: {str(e)}")
        return create_response(500, {
            'success': False,
            'error': 'INTERNAL_ERROR',
            'message': 'An unexpected error occurred'
        })
