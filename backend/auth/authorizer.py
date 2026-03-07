"""
JWT Authorizer Lambda Function
Validates JWT tokens and returns IAM policy for API Gateway
"""
import json
import os
import boto3
from typing import Dict, Any

# Import shared auth utilities
# In Lambda, shared modules are in /opt/python layer
# For local testing, import from backend.shared
try:
    from auth import validate_jwt_token, extract_token_from_header
    from exceptions import InvalidTokenError, AuthenticationError
except ImportError:
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from auth import validate_jwt_token, extract_token_from_header
    from exceptions import InvalidTokenError, AuthenticationError


def get_jwt_secret() -> str:
    """
    Retrieve JWT secret from Secrets Manager.
    
    Returns:
        JWT secret key string
        
    Raises:
        AuthenticationError: If secret cannot be retrieved
    """
    secret_arn = os.environ.get('JWT_SECRET_ARN')
    if not secret_arn:
        raise AuthenticationError("JWT_SECRET_ARN environment variable not set")
    
    try:
        secrets_client = boto3.client('secretsmanager')
        response = secrets_client.get_secret_value(SecretId=secret_arn)
        
        # Parse the secret JSON
        secret_dict = json.loads(response['SecretString'])
        jwt_secret = secret_dict.get('jwt_secret')
        
        if not jwt_secret:
            raise AuthenticationError("jwt_secret not found in Secrets Manager")
        
        return jwt_secret
    except Exception as e:
        raise AuthenticationError(f"Failed to retrieve JWT secret: {str(e)}")


def generate_policy(principal_id: str, effect: str, resource: str, context: Dict[str, str] = None) -> Dict[str, Any]:
    """
    Generate IAM policy document for API Gateway.
    
    Args:
        principal_id: User identifier
        effect: 'Allow' or 'Deny'
        resource: API Gateway method ARN
        context: Additional context to pass to downstream Lambdas
        
    Returns:
        IAM policy document
    """
    policy = {
        'principalId': principal_id,
        'policyDocument': {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Action': 'execute-api:Invoke',
                    'Effect': effect,
                    'Resource': resource
                }
            ]
        }
    }
    
    # Add context if provided
    if context:
        policy['context'] = context
    
    return policy


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda authorizer handler for JWT token validation.
    
    This function:
    1. Extracts JWT token from Authorization header
    2. Validates token signature using secret from Secrets Manager
    3. Verifies token expiration
    4. Returns IAM policy allowing/denying API Gateway access
    5. Includes userId and role in context for downstream Lambdas
    
    Args:
        event: API Gateway authorizer event containing headers and methodArn
        context: Lambda context
        
    Returns:
        IAM policy document with user context
    """
    try:
        # Extract Authorization header
        # API Gateway REQUEST authorizer provides headers in different formats
        headers = event.get('headers', {})
        
        # Handle case-insensitive header names
        authorization_header = None
        for key, value in headers.items():
            if key.lower() == 'authorization':
                authorization_header = value
                break
        
        if not authorization_header:
            print("Authorization header missing")
            raise InvalidTokenError("Authorization header missing")
        
        # Extract token from header
        token = extract_token_from_header(authorization_header)
        
        # Get JWT secret from Secrets Manager
        jwt_secret = get_jwt_secret()
        
        # Validate token and extract user information
        user_info = validate_jwt_token(token, jwt_secret)
        
        # Extract user details
        user_id = user_info['userId']
        role = user_info['role']
        email = user_info['email']
        
        # Generate Allow policy with user context
        # The context will be available to downstream Lambda functions
        # in event['requestContext']['authorizer']
        policy = generate_policy(
            principal_id=user_id,
            effect='Allow',
            resource=event['methodArn'],
            context={
                'userId': user_id,
                'role': role,
                'email': email
            }
        )
        
        print(f"Authorization successful for user {user_id} with role {role}")
        return policy
        
    except InvalidTokenError as e:
        print(f"Token validation failed: {str(e)}")
        # Return Deny policy for invalid tokens
        # Note: We use a generic principal ID for denied requests
        return generate_policy(
            principal_id='unauthorized',
            effect='Deny',
            resource=event['methodArn']
        )
        
    except AuthenticationError as e:
        print(f"Authentication error: {str(e)}")
        # Return Deny policy for authentication errors
        return generate_policy(
            principal_id='unauthorized',
            effect='Deny',
            resource=event['methodArn']
        )
        
    except Exception as e:
        print(f"Unexpected error in authorizer: {str(e)}")
        # Return Deny policy for any unexpected errors
        return generate_policy(
            principal_id='unauthorized',
            effect='Deny',
            resource=event['methodArn']
        )
