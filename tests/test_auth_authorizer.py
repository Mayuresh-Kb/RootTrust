"""
Unit tests for JWT Authorizer Lambda function
"""
import json
import os
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import jwt

# Mock the shared imports before importing the handler
import sys
sys.path.insert(0, 'backend/shared')

from backend.auth.authorizer import handler, generate_policy, get_jwt_secret


class TestJWTAuthorizer:
    """Test suite for JWT authorizer Lambda function"""
    
    @pytest.fixture
    def jwt_secret(self):
        """Fixture providing a test JWT secret"""
        return "test-secret-key-for-jwt-validation-12345"
    
    @pytest.fixture
    def valid_token(self, jwt_secret):
        """Fixture providing a valid JWT token"""
        payload = {
            'userId': 'test-user-123',
            'email': 'test@example.com',
            'role': 'farmer',
            'iat': datetime.utcnow(),
            'exp': datetime.utcnow() + timedelta(hours=24)
        }
        return jwt.encode(payload, jwt_secret, algorithm='HS256')
    
    @pytest.fixture
    def expired_token(self, jwt_secret):
        """Fixture providing an expired JWT token"""
        payload = {
            'userId': 'test-user-123',
            'email': 'test@example.com',
            'role': 'farmer',
            'iat': datetime.utcnow() - timedelta(hours=25),
            'exp': datetime.utcnow() - timedelta(hours=1)
        }
        return jwt.encode(payload, jwt_secret, algorithm='HS256')
    
    @pytest.fixture
    def authorizer_event(self, valid_token):
        """Fixture providing a sample API Gateway authorizer event"""
        return {
            'type': 'REQUEST',
            'methodArn': 'arn:aws:execute-api:us-east-1:123456789012:abcdef123/dev/GET/products',
            'headers': {
                'Authorization': f'Bearer {valid_token}'
            }
        }
    
    @pytest.fixture
    def mock_secrets_manager(self, jwt_secret):
        """Fixture to mock Secrets Manager client"""
        with patch('boto3.client') as mock_client:
            mock_sm = MagicMock()
            mock_sm.get_secret_value.return_value = {
                'SecretString': json.dumps({'jwt_secret': jwt_secret})
            }
            mock_client.return_value = mock_sm
            yield mock_sm
    
    def test_generate_policy_allow(self):
        """Test generating an Allow IAM policy"""
        policy = generate_policy(
            principal_id='user-123',
            effect='Allow',
            resource='arn:aws:execute-api:us-east-1:123456789012:abcdef123/dev/GET/products',
            context={'userId': 'user-123', 'role': 'farmer'}
        )
        
        assert policy['principalId'] == 'user-123'
        assert policy['policyDocument']['Version'] == '2012-10-17'
        assert len(policy['policyDocument']['Statement']) == 1
        assert policy['policyDocument']['Statement'][0]['Effect'] == 'Allow'
        assert policy['policyDocument']['Statement'][0]['Action'] == 'execute-api:Invoke'
        assert policy['context']['userId'] == 'user-123'
        assert policy['context']['role'] == 'farmer'
    
    def test_generate_policy_deny(self):
        """Test generating a Deny IAM policy"""
        policy = generate_policy(
            principal_id='unauthorized',
            effect='Deny',
            resource='arn:aws:execute-api:us-east-1:123456789012:abcdef123/dev/GET/products'
        )
        
        assert policy['principalId'] == 'unauthorized'
        assert policy['policyDocument']['Statement'][0]['Effect'] == 'Deny'
        assert 'context' not in policy
    
    @patch.dict(os.environ, {'JWT_SECRET_ARN': 'arn:aws:secretsmanager:us-east-1:123456789012:secret:test-secret'})
    def test_get_jwt_secret_success(self, mock_secrets_manager, jwt_secret):
        """Test successful retrieval of JWT secret from Secrets Manager"""
        secret = get_jwt_secret()
        assert secret == jwt_secret
        mock_secrets_manager.get_secret_value.assert_called_once()
    
    @patch.dict(os.environ, {}, clear=True)
    def test_get_jwt_secret_missing_env_var(self):
        """Test error when JWT_SECRET_ARN environment variable is missing"""
        from backend.shared.exceptions import AuthenticationError
        with pytest.raises(AuthenticationError, match="JWT_SECRET_ARN environment variable not set"):
            get_jwt_secret()
    
    @patch.dict(os.environ, {'JWT_SECRET_ARN': 'arn:aws:secretsmanager:us-east-1:123456789012:secret:test-secret'})
    def test_handler_valid_token(self, mock_secrets_manager, authorizer_event):
        """Test authorizer handler with valid JWT token"""
        response = handler(authorizer_event, None)
        
        assert response['principalId'] == 'test-user-123'
        assert response['policyDocument']['Statement'][0]['Effect'] == 'Allow'
        assert response['context']['userId'] == 'test-user-123'
        assert response['context']['role'] == 'farmer'
        assert response['context']['email'] == 'test@example.com'
    
    @patch.dict(os.environ, {'JWT_SECRET_ARN': 'arn:aws:secretsmanager:us-east-1:123456789012:secret:test-secret'})
    def test_handler_expired_token(self, mock_secrets_manager, authorizer_event, expired_token):
        """Test authorizer handler with expired JWT token"""
        authorizer_event['headers']['Authorization'] = f'Bearer {expired_token}'
        
        response = handler(authorizer_event, None)
        
        assert response['principalId'] == 'unauthorized'
        assert response['policyDocument']['Statement'][0]['Effect'] == 'Deny'
        assert 'context' not in response
    
    @patch.dict(os.environ, {'JWT_SECRET_ARN': 'arn:aws:secretsmanager:us-east-1:123456789012:secret:test-secret'})
    def test_handler_invalid_token(self, mock_secrets_manager, authorizer_event):
        """Test authorizer handler with invalid JWT token"""
        authorizer_event['headers']['Authorization'] = 'Bearer invalid-token-string'
        
        response = handler(authorizer_event, None)
        
        assert response['principalId'] == 'unauthorized'
        assert response['policyDocument']['Statement'][0]['Effect'] == 'Deny'
    
    @patch.dict(os.environ, {'JWT_SECRET_ARN': 'arn:aws:secretsmanager:us-east-1:123456789012:secret:test-secret'})
    def test_handler_missing_authorization_header(self, mock_secrets_manager, authorizer_event):
        """Test authorizer handler with missing Authorization header"""
        del authorizer_event['headers']['Authorization']
        
        response = handler(authorizer_event, None)
        
        assert response['principalId'] == 'unauthorized'
        assert response['policyDocument']['Statement'][0]['Effect'] == 'Deny'
    
    @patch.dict(os.environ, {'JWT_SECRET_ARN': 'arn:aws:secretsmanager:us-east-1:123456789012:secret:test-secret'})
    def test_handler_malformed_authorization_header(self, mock_secrets_manager, authorizer_event):
        """Test authorizer handler with malformed Authorization header"""
        authorizer_event['headers']['Authorization'] = 'InvalidFormat token'
        
        response = handler(authorizer_event, None)
        
        assert response['principalId'] == 'unauthorized'
        assert response['policyDocument']['Statement'][0]['Effect'] == 'Deny'
    
    @patch.dict(os.environ, {'JWT_SECRET_ARN': 'arn:aws:secretsmanager:us-east-1:123456789012:secret:test-secret'})
    def test_handler_case_insensitive_header(self, mock_secrets_manager, authorizer_event):
        """Test authorizer handler handles case-insensitive Authorization header"""
        # API Gateway may normalize headers differently
        token = authorizer_event['headers']['Authorization']
        del authorizer_event['headers']['Authorization']
        authorizer_event['headers']['authorization'] = token
        
        response = handler(authorizer_event, None)
        
        assert response['principalId'] == 'test-user-123'
        assert response['policyDocument']['Statement'][0]['Effect'] == 'Allow'
    
    @patch.dict(os.environ, {'JWT_SECRET_ARN': 'arn:aws:secretsmanager:us-east-1:123456789012:secret:test-secret'})
    def test_handler_includes_user_context(self, mock_secrets_manager, authorizer_event):
        """Test that authorizer includes userId and role in context for downstream Lambdas"""
        response = handler(authorizer_event, None)
        
        # Verify context is included
        assert 'context' in response
        assert 'userId' in response['context']
        assert 'role' in response['context']
        assert 'email' in response['context']
        
        # Verify values match token payload
        assert response['context']['userId'] == 'test-user-123'
        assert response['context']['role'] == 'farmer'
        assert response['context']['email'] == 'test@example.com'
