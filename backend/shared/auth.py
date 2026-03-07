"""
Authentication utilities for JWT token generation and validation.
"""
import os
import jwt
import bcrypt
from datetime import datetime, timedelta
from typing import Dict, Optional
from backend.shared.constants import JWT_EXPIRATION_HOURS
from backend.shared.exceptions import InvalidTokenError, AuthenticationError


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Args:
        password: Plain text password
        
    Returns:
        Bcrypt hashed password
    """
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(password: str, password_hash: str) -> bool:
    """
    Verify a password against a bcrypt hash.
    
    Args:
        password: Plain text password to verify
        password_hash: Bcrypt hash to compare against
        
    Returns:
        True if password matches, False otherwise
    """
    try:
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    except Exception:
        return False


def generate_jwt_token(
    user_id: str,
    email: str,
    role: str,
    secret_key: Optional[str] = None
) -> Dict[str, any]:
    """
    Generate a JWT token for authenticated user.
    
    Args:
        user_id: User's unique identifier
        email: User's email address
        role: User's role (farmer or consumer)
        secret_key: JWT secret key (defaults to env variable)
        
    Returns:
        Dictionary with token, userId, role, and expiresIn
        
    Raises:
        AuthenticationError: If secret key is not available
    """
    if secret_key is None:
        secret_key = os.environ.get('JWT_SECRET_KEY')
    
    if not secret_key:
        raise AuthenticationError("JWT secret key not configured")
    
    # Calculate expiration
    expiration = datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    
    # Create payload
    payload = {
        'userId': user_id,
        'email': email,
        'role': role,
        'iat': datetime.utcnow(),
        'exp': expiration
    }
    
    # Generate token
    token = jwt.encode(payload, secret_key, algorithm='HS256')
    
    return {
        'token': token,
        'userId': user_id,
        'role': role,
        'expiresIn': int(JWT_EXPIRATION_HOURS * 3600)  # seconds
    }


def validate_jwt_token(token: str, secret_key: Optional[str] = None) -> Dict[str, any]:
    """
    Validate and decode a JWT token.
    
    Args:
        token: JWT token string
        secret_key: JWT secret key (defaults to env variable)
        
    Returns:
        Decoded token payload with userId, email, and role
        
    Raises:
        InvalidTokenError: If token is invalid, expired, or malformed
    """
    if secret_key is None:
        secret_key = os.environ.get('JWT_SECRET_KEY')
    
    if not secret_key:
        raise AuthenticationError("JWT secret key not configured")
    
    try:
        # Decode and verify token
        payload = jwt.decode(token, secret_key, algorithms=['HS256'])
        
        # Verify required claims exist
        required_claims = ['userId', 'email', 'role']
        for claim in required_claims:
            if claim not in payload:
                raise InvalidTokenError(f"Missing required claim: {claim}")
        
        return {
            'userId': payload['userId'],
            'email': payload['email'],
            'role': payload['role']
        }
    
    except jwt.ExpiredSignatureError:
        raise InvalidTokenError("Token has expired")
    except jwt.InvalidTokenError as e:
        raise InvalidTokenError(f"Invalid token: {str(e)}")
    except Exception as e:
        raise InvalidTokenError(f"Token validation failed: {str(e)}")


def extract_token_from_header(authorization_header: Optional[str]) -> str:
    """
    Extract JWT token from Authorization header.
    
    Args:
        authorization_header: Authorization header value (e.g., "Bearer <token>")
        
    Returns:
        Extracted token string
        
    Raises:
        InvalidTokenError: If header is missing or malformed
    """
    if not authorization_header:
        raise InvalidTokenError("Authorization header missing")
    
    parts = authorization_header.split()
    
    if len(parts) != 2 or parts[0].lower() != 'bearer':
        raise InvalidTokenError("Invalid authorization header format. Expected: Bearer <token>")
    
    return parts[1]


def get_user_from_token(authorization_header: Optional[str], secret_key: Optional[str] = None) -> Dict[str, any]:
    """
    Extract and validate user information from Authorization header.
    
    Args:
        authorization_header: Authorization header value
        secret_key: JWT secret key (defaults to env variable)
        
    Returns:
        User information from token (userId, email, role)
        
    Raises:
        InvalidTokenError: If token is invalid or missing
    """
    token = extract_token_from_header(authorization_header)
    return validate_jwt_token(token, secret_key)
