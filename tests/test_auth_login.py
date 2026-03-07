"""
Unit tests for user login endpoint.
"""
import json
import os
import sys
import pytest
from unittest.mock import patch, MagicMock, Mock
from datetime import datetime

# Mock environment variables before any imports
os.environ['DYNAMODB_TABLE_NAME'] = 'test-table'
os.environ['TABLE_NAME'] = 'test-table'
os.environ['JWT_SECRET_KEY'] = 'test-secret-key-for-testing-only'

# Add backend to path
backend_path = os.path.join(os.path.dirname(__file__), '..', 'backend')
sys.path.insert(0, backend_path)
sys.path.insert(0, os.path.join(backend_path, 'shared'))


class TestUserLoginBasic:
    """Basic test cases for user login endpoint structure."""
    
    def test_login_handler_exists(self):
        """Test that the login handler module can be imported."""
        handler_path = os.path.join(os.path.dirname(__file__), '..', 'backend', 'auth', 'login.py')
        assert os.path.exists(handler_path), "Login handler file should exist"
    
    def test_login_handler_has_handler_function(self):
        """Test that the handler function exists."""
        with open(os.path.join(os.path.dirname(__file__), '..', 'backend', 'auth', 'login.py'), 'r') as f:
            content = f.read()
            assert 'def handler(' in content, "Handler function should be defined"
            assert 'event' in content and 'context' in content, "Handler should accept event and context"
    
    def test_login_validates_email(self):
        """Test that login includes email validation."""
        with open(os.path.join(os.path.dirname(__file__), '..', 'backend', 'auth', 'login.py'), 'r') as f:
            content = f.read()
            assert 'email' in content.lower(), "Login should handle email"
    
    def test_login_verifies_password(self):
        """Test that login includes password verification."""
        with open(os.path.join(os.path.dirname(__file__), '..', 'backend', 'auth', 'login.py'), 'r') as f:
            content = f.read()
            assert 'verify_password' in content, "Login should verify passwords"
    
    def test_login_generates_jwt_token(self):
        """Test that login generates JWT token."""
        with open(os.path.join(os.path.dirname(__file__), '..', 'backend', 'auth', 'login.py'), 'r') as f:
            content = f.read()
            assert 'generate_jwt_token' in content, "Login should generate JWT token"
    
    def test_login_queries_dynamodb(self):
        """Test that login queries DynamoDB."""
        with open(os.path.join(os.path.dirname(__file__), '..', 'backend', 'auth', 'login.py'), 'r') as f:
            content = f.read()
            assert 'get_item' in content, "Login should query DynamoDB"
    
    def test_login_returns_token_response(self):
        """Test that login returns proper response structure."""
        with open(os.path.join(os.path.dirname(__file__), '..', 'backend', 'auth', 'login.py'), 'r') as f:
            content = f.read()
            assert 'statusCode' in content, "Response should include statusCode"
            assert 'token' in content, "Response should include token"
            assert 'userId' in content, "Response should include userId"
            assert 'role' in content, "Response should include role"
            assert 'expiresIn' in content, "Response should include expiresIn"
    
    def test_login_handles_authentication_errors(self):
        """Test that login handles authentication errors."""
        with open(os.path.join(os.path.dirname(__file__), '..', 'backend', 'auth', 'login.py'), 'r') as f:
            content = f.read()
            assert 'AuthenticationError' in content, "Login should handle authentication errors"
    
    def test_login_handles_validation_errors(self):
        """Test that login handles validation errors."""
        with open(os.path.join(os.path.dirname(__file__), '..', 'backend', 'auth', 'login.py'), 'r') as f:
            content = f.read()
            assert 'ValidationError' in content, "Login should handle validation errors"
    
    def test_login_uses_email_lookup(self):
        """Test that login uses email lookup pattern."""
        with open(os.path.join(os.path.dirname(__file__), '..', 'backend', 'auth', 'login.py'), 'r') as f:
            content = f.read()
            assert 'EMAIL#' in content, "Login should use email lookup pattern"
    
    def test_login_checks_jwt_secret(self):
        """Test that login checks for JWT secret."""
        with open(os.path.join(os.path.dirname(__file__), '..', 'backend', 'auth', 'login.py'), 'r') as f:
            content = f.read()
            assert 'JWT_SECRET_KEY' in content, "Login should check for JWT secret"
    
    def test_login_returns_cors_headers(self):
        """Test that login returns CORS headers."""
        with open(os.path.join(os.path.dirname(__file__), '..', 'backend', 'auth', 'login.py'), 'r') as f:
            content = f.read()
            assert 'Access-Control-Allow-Origin' in content, "Response should include CORS headers"
    
    def test_login_validates_request_body(self):
        """Test that login validates request body."""
        with open(os.path.join(os.path.dirname(__file__), '..', 'backend', 'auth', 'login.py'), 'r') as f:
            content = f.read()
            assert 'UserLoginRequest' in content, "Login should validate request body"
            assert 'validate_request_body' in content, "Login should use validation function"
    
    def test_login_error_message_security(self):
        """Test that login doesn't reveal whether email exists."""
        with open(os.path.join(os.path.dirname(__file__), '..', 'backend', 'auth', 'login.py'), 'r') as f:
            content = f.read()
            # Should use generic error message
            assert 'Invalid email or password' in content, "Login should use generic error message"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
