"""
Referral link generation Lambda handler for RootTrust marketplace.
Handles POST /referrals/generate endpoint for consumers to create referral links.
"""
import json
import os
import uuid
import random
import string
from datetime import datetime
from typing import Dict, Any

# Import shared modules
import sys
sys.path.append('/opt/python')

from models import Referral
from validators import ReferralGenerateRequest, validate_request_body
from database import get_item, put_item
from auth import get_user_from_token
from constants import UserRole, VerificationStatus
from exceptions import (
    ValidationError, AuthenticationError, AuthorizationError,
    ResourceNotFoundError, ConflictError
)


# Maximum collision retry attempts
MAX_COLLISION_RETRIES = 3

# Referral code length
REFERRAL_CODE_LENGTH = 8


def generate_referral_code() -> str:
    """
    Generate a random 8-character alphanumeric referral code.
    Uses uppercase letters and numbers only.
    
    Returns:
        8-character alphanumeric string
    """
    characters = string.ascii_uppercase + string.digits
    return ''.join(random.choice(characters) for _ in range(REFERRAL_CODE_LENGTH))


def check_referral_code_exists(referral_code: str) -> bool:
    """
    Check if a referral code already exists in DynamoDB.
    
    Args:
        referral_code: Referral code to check
        
    Returns:
        True if code exists, False otherwise
    """
    pk = f"REFERRAL#{referral_code}"
    sk = "METADATA"
    
    try:
        item = get_item(pk, sk)
        return item is not None
    except Exception:
        # If there's an error checking, assume it doesn't exist
        # The put_item will fail if it actually does exist
        return False


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for referral link generation endpoint.
    
    Validates JWT token, consumer role authorization, generates unique referral code,
    stores referral in DynamoDB, and returns referral URL.
    
    Args:
        event: API Gateway event
        context: Lambda context
        
    Returns:
        API Gateway response with referralCode and referralUrl
    """
    try:
        # Extract authorization header
        headers = event.get('headers', {})
        auth_header = headers.get('Authorization') or headers.get('authorization')
        
        if not auth_header:
            return {
                'statusCode': 401,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'UNAUTHORIZED',
                        'message': 'Authorization header is required'
                    }
                })
            }
        
        # Validate JWT token and extract user info
        try:
            user_info = get_user_from_token(auth_header)
            referrer_id = user_info['userId']
            user_role = user_info['role']
        except Exception as e:
            return {
                'statusCode': 401,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'INVALID_TOKEN',
                        'message': str(e)
                    }
                })
            }
        
        # Verify consumer role
        if user_role != UserRole.CONSUMER.value:
            return {
                'statusCode': 403,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'FORBIDDEN',
                        'message': 'Only consumers can generate referral links'
                    }
                })
            }
        
        # Parse and validate request body
        try:
            body = json.loads(event.get('body', '{}'))
        except json.JSONDecodeError:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'INVALID_JSON',
                        'message': 'Request body must be valid JSON'
                    }
                })
            }
        
        # Validate referral request data
        try:
            referral_request = validate_request_body(body, ReferralGenerateRequest)
        except ValidationError as e:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'VALIDATION_ERROR',
                        'message': e.message,
                        'details': e.details if hasattr(e, 'details') else []
                    }
                })
            }
        
        # Verify product exists
        product_pk = f"PRODUCT#{referral_request.productId}"
        product_sk = "METADATA"
        
        try:
            product_item = get_item(product_pk, product_sk)
        except Exception as e:
            print(f"Error querying product: {str(e)}")
            return {
                'statusCode': 503,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'SERVICE_UNAVAILABLE',
                        'message': 'Failed to query product',
                        'details': str(e)
                    }
                })
            }
        
        if not product_item:
            return {
                'statusCode': 404,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'RESOURCE_NOT_FOUND',
                        'message': f'Product with ID {referral_request.productId} not found'
                    }
                })
            }
        
        # Generate unique referral code with collision detection
        referral_code = None
        collision_attempts = 0
        
        while collision_attempts < MAX_COLLISION_RETRIES:
            candidate_code = generate_referral_code()
            
            # Check if code already exists
            if not check_referral_code_exists(candidate_code):
                referral_code = candidate_code
                break
            
            collision_attempts += 1
            print(f"Referral code collision detected, attempt {collision_attempts}/{MAX_COLLISION_RETRIES}")
        
        if not referral_code:
            # Failed to generate unique code after max retries
            return {
                'statusCode': 503,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'SERVICE_UNAVAILABLE',
                        'message': 'Failed to generate unique referral code. Please try again.'
                    }
                })
            }
        
        # Create Referral model instance
        now = datetime.utcnow()
        referral = Referral(
            referralCode=referral_code,
            referrerId=referrer_id,
            productId=referral_request.productId,
            conversions=[],
            totalConversions=0,
            totalRewards=0.0,
            createdAt=now
        )
        
        # Convert to DynamoDB item format
        referral_dict = referral.dict()
        
        # Convert datetime objects to ISO strings for DynamoDB
        referral_dict['createdAt'] = referral_dict['createdAt'].isoformat()
        
        # Store referral in DynamoDB with condition to prevent duplicates
        try:
            put_item(
                referral_dict,
                condition_expression='attribute_not_exists(PK)'
            )
        except ConflictError:
            # Code collision occurred despite our check
            # This is extremely rare but possible in high-concurrency scenarios
            return {
                'statusCode': 503,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'SERVICE_UNAVAILABLE',
                        'message': 'Referral code collision occurred. Please try again.'
                    }
                })
            }
        except Exception as e:
            print(f"Error storing referral in DynamoDB: {str(e)}")
            return {
                'statusCode': 503,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'SERVICE_UNAVAILABLE',
                        'message': 'Failed to create referral',
                        'details': str(e)
                    }
                })
            }
        
        # Construct referral URL
        # In production, this would use the actual frontend domain
        frontend_domain = os.environ.get('FRONTEND_DOMAIN', 'https://roottrust.example.com')
        referral_url = f"{frontend_domain}/products/{referral_request.productId}?ref={referral_code}"
        
        # Return success response
        return {
            'statusCode': 201,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'referralCode': referral_code,
                'referralUrl': referral_url,
                'message': 'Referral link generated successfully'
            })
        }
    
    except Exception as e:
        # Catch-all for unexpected errors
        print(f"Unexpected error in referral generation: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': {
                    'code': 'INTERNAL_ERROR',
                    'message': 'An unexpected error occurred',
                    'details': str(e)
                }
            })
        }
