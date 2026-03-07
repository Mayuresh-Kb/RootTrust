"""
Unit tests for referral link generation endpoint.
Tests POST /referrals/generate functionality.
"""
import json
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from referrals.generate_referral import handler, generate_referral_code, check_referral_code_exists
from shared.constants import UserRole, VerificationStatus


@pytest.fixture
def mock_env():
    """Set up environment variables for tests."""
    os.environ['DYNAMODB_TABLE_NAME'] = 'RootTrustData'
    os.environ['JWT_SECRET_KEY'] = 'test-secret-key-for-testing-only'
    os.environ['FRONTEND_DOMAIN'] = 'https://roottrust.example.com'


@pytest.fixture
def valid_consumer_token():
    """Generate a valid JWT token for a consumer."""
    from shared.auth import generate_jwt_token
    return generate_jwt_token(
        user_id='consumer-123',
        email='consumer@example.com',
        role=UserRole.CONSUMER.value
    )['token']


@pytest.fixture
def valid_farmer_token():
    """Generate a valid JWT token for a farmer."""
    from shared.auth import generate_jwt_token
    return generate_jwt_token(
        user_id='farmer-456',
        email='farmer@example.com',
        role=UserRole.FARMER.value
    )['token']


@pytest.fixture
def valid_product():
    """Mock product data."""
    return {
        'PK': 'PRODUCT#product-789',
        'SK': 'METADATA',
        'productId': 'product-789',
        'farmerId': 'farmer-456',
        'name': 'Organic Tomatoes',
        'category': 'vegetables',
        'price': 50.0,
        'verificationStatus': VerificationStatus.APPROVED.value,
        'quantity': 100
    }


class TestReferralCodeGeneration:
    """Test referral code generation utility functions."""
    
    def test_generate_referral_code_length(self):
        """Test that generated referral codes are 8 characters long."""
        code = generate_referral_code()
        assert len(code) == 8
    
    def test_generate_referral_code_alphanumeric(self):
        """Test that generated referral codes contain only uppercase letters and numbers."""
        code = generate_referral_code()
        assert code.isalnum()
        assert code.isupper() or code.isdigit()
    
    def test_generate_referral_code_uniqueness(self):
        """Test that multiple generated codes are different (probabilistic)."""
        codes = [generate_referral_code() for _ in range(100)]
        # With 8 characters from 36 possible (26 letters + 10 digits),
        # collisions should be extremely rare
        assert len(set(codes)) > 95  # Allow for small chance of collision


class TestReferralGenerationEndpoint:
    """Test referral link generation endpoint."""
    
    def test_missing_authorization_header(self, mock_env):
        """Test that missing authorization header returns 401."""
        event = {
            'headers': {},
            'body': json.dumps({'productId': 'product-789'})
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 401
        body = json.loads(response['body'])
        assert body['error']['code'] == 'UNAUTHORIZED'
    
    def test_invalid_token(self, mock_env):
        """Test that invalid JWT token returns 401."""
        event = {
            'headers': {'Authorization': 'Bearer invalid-token'},
            'body': json.dumps({'productId': 'product-789'})
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 401
        body = json.loads(response['body'])
        assert body['error']['code'] == 'INVALID_TOKEN'
    
    def test_farmer_role_forbidden(self, mock_env, valid_farmer_token):
        """Test that farmers cannot generate referral links."""
        event = {
            'headers': {'Authorization': f'Bearer {valid_farmer_token}'},
            'body': json.dumps({'productId': 'product-789'})
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 403
        body = json.loads(response['body'])
        assert body['error']['code'] == 'FORBIDDEN'
        assert 'consumers' in body['error']['message'].lower()
    
    def test_invalid_json_body(self, mock_env, valid_consumer_token):
        """Test that invalid JSON returns 400."""
        event = {
            'headers': {'Authorization': f'Bearer {valid_consumer_token}'},
            'body': 'invalid json'
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error']['code'] == 'INVALID_JSON'
    
    def test_missing_product_id(self, mock_env, valid_consumer_token):
        """Test that missing productId returns validation error."""
        event = {
            'headers': {'Authorization': f'Bearer {valid_consumer_token}'},
            'body': json.dumps({})
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error']['code'] == 'VALIDATION_ERROR'
    
    @patch('referrals.generate_referral.get_item')
    def test_product_not_found(self, mock_get_item, mock_env, valid_consumer_token):
        """Test that non-existent product returns 404."""
        mock_get_item.return_value = None
        
        event = {
            'headers': {'Authorization': f'Bearer {valid_consumer_token}'},
            'body': json.dumps({'productId': 'nonexistent-product'})
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 404
        body = json.loads(response['body'])
        assert body['error']['code'] == 'RESOURCE_NOT_FOUND'
        assert 'nonexistent-product' in body['error']['message']
    
    @patch('referrals.generate_referral.put_item')
    @patch('referrals.generate_referral.check_referral_code_exists')
    @patch('referrals.generate_referral.get_item')
    def test_successful_referral_generation(
        self, mock_get_item, mock_check_exists, mock_put_item,
        mock_env, valid_consumer_token, valid_product
    ):
        """Test successful referral link generation."""
        mock_get_item.return_value = valid_product
        mock_check_exists.return_value = False
        mock_put_item.return_value = {}
        
        event = {
            'headers': {'Authorization': f'Bearer {valid_consumer_token}'},
            'body': json.dumps({'productId': 'product-789'})
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 201
        body = json.loads(response['body'])
        
        # Verify response structure
        assert 'referralCode' in body
        assert 'referralUrl' in body
        assert 'message' in body
        
        # Verify referral code format
        assert len(body['referralCode']) == 8
        assert body['referralCode'].isalnum()
        
        # Verify referral URL format
        assert 'product-789' in body['referralUrl']
        assert body['referralCode'] in body['referralUrl']
        assert body['referralUrl'].startswith('https://roottrust.example.com')
        
        # Verify put_item was called
        assert mock_put_item.called
        put_args = mock_put_item.call_args[0][0]
        assert put_args['referralCode'] == body['referralCode']
        assert put_args['referrerId'] == 'consumer-123'
        assert put_args['productId'] == 'product-789'
        assert put_args['PK'] == f"REFERRAL#{body['referralCode']}"
        assert put_args['SK'] == 'METADATA'
        assert put_args['GSI2PK'] == 'REFERRER#consumer-123'
    
    @patch('referrals.generate_referral.put_item')
    @patch('referrals.generate_referral.check_referral_code_exists')
    @patch('referrals.generate_referral.get_item')
    def test_referral_code_collision_retry(
        self, mock_get_item, mock_check_exists, mock_put_item,
        mock_env, valid_consumer_token, valid_product
    ):
        """Test that code collision triggers retry and eventually succeeds."""
        mock_get_item.return_value = valid_product
        # First two checks return True (collision), third returns False
        mock_check_exists.side_effect = [True, True, False]
        mock_put_item.return_value = {}
        
        event = {
            'headers': {'Authorization': f'Bearer {valid_consumer_token}'},
            'body': json.dumps({'productId': 'product-789'})
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 201
        # Verify that check_exists was called 3 times
        assert mock_check_exists.call_count == 3
    
    @patch('referrals.generate_referral.check_referral_code_exists')
    @patch('referrals.generate_referral.get_item')
    def test_referral_code_max_collision_retries(
        self, mock_get_item, mock_check_exists,
        mock_env, valid_consumer_token, valid_product
    ):
        """Test that max collision retries returns 503."""
        mock_get_item.return_value = valid_product
        # All checks return True (collision)
        mock_check_exists.return_value = True
        
        event = {
            'headers': {'Authorization': f'Bearer {valid_consumer_token}'},
            'body': json.dumps({'productId': 'product-789'})
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 503
        body = json.loads(response['body'])
        assert body['error']['code'] == 'SERVICE_UNAVAILABLE'
        assert 'unique referral code' in body['error']['message'].lower()
        # Verify that check_exists was called MAX_COLLISION_RETRIES times
        assert mock_check_exists.call_count == 3
    
    @patch('referrals.generate_referral.put_item')
    @patch('referrals.generate_referral.check_referral_code_exists')
    @patch('referrals.generate_referral.get_item')
    def test_dynamodb_put_conflict(
        self, mock_get_item, mock_check_exists, mock_put_item,
        mock_env, valid_consumer_token, valid_product
    ):
        """Test that DynamoDB conflict error returns 503."""
        from backend.shared.exceptions import ConflictError
        
        mock_get_item.return_value = valid_product
        mock_check_exists.return_value = False
        mock_put_item.side_effect = ConflictError('Item already exists')
        
        event = {
            'headers': {'Authorization': f'Bearer {valid_consumer_token}'},
            'body': json.dumps({'productId': 'product-789'})
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 503
        body = json.loads(response['body'])
        assert body['error']['code'] == 'SERVICE_UNAVAILABLE'
        assert 'collision' in body['error']['message'].lower()
    
    @patch('referrals.generate_referral.put_item')
    @patch('referrals.generate_referral.check_referral_code_exists')
    @patch('referrals.generate_referral.get_item')
    def test_dynamodb_put_error(
        self, mock_get_item, mock_check_exists, mock_put_item,
        mock_env, valid_consumer_token, valid_product
    ):
        """Test that DynamoDB error returns 503."""
        mock_get_item.return_value = valid_product
        mock_check_exists.return_value = False
        mock_put_item.side_effect = Exception('DynamoDB error')
        
        event = {
            'headers': {'Authorization': f'Bearer {valid_consumer_token}'},
            'body': json.dumps({'productId': 'product-789'})
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 503
        body = json.loads(response['body'])
        assert body['error']['code'] == 'SERVICE_UNAVAILABLE'
    
    @patch('referrals.generate_referral.get_item')
    def test_product_query_error(self, mock_get_item, mock_env, valid_consumer_token):
        """Test that product query error returns 503."""
        mock_get_item.side_effect = Exception('DynamoDB error')
        
        event = {
            'headers': {'Authorization': f'Bearer {valid_consumer_token}'},
            'body': json.dumps({'productId': 'product-789'})
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 503
        body = json.loads(response['body'])
        assert body['error']['code'] == 'SERVICE_UNAVAILABLE'
    
    @patch('referrals.generate_referral.put_item')
    @patch('referrals.generate_referral.check_referral_code_exists')
    @patch('referrals.generate_referral.get_item')
    def test_referral_data_structure(
        self, mock_get_item, mock_check_exists, mock_put_item,
        mock_env, valid_consumer_token, valid_product
    ):
        """Test that referral data structure is correct."""
        mock_get_item.return_value = valid_product
        mock_check_exists.return_value = False
        mock_put_item.return_value = {}
        
        event = {
            'headers': {'Authorization': f'Bearer {valid_consumer_token}'},
            'body': json.dumps({'productId': 'product-789'})
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 201
        
        # Verify the data structure passed to put_item
        put_args = mock_put_item.call_args[0][0]
        
        # Verify required fields
        assert 'referralCode' in put_args
        assert 'referrerId' in put_args
        assert 'productId' in put_args
        assert 'conversions' in put_args
        assert 'totalConversions' in put_args
        assert 'totalRewards' in put_args
        assert 'createdAt' in put_args
        
        # Verify DynamoDB keys
        assert 'PK' in put_args
        assert 'SK' in put_args
        assert 'EntityType' in put_args
        assert 'GSI2PK' in put_args
        assert 'GSI2SK' in put_args
        
        # Verify initial values
        assert put_args['conversions'] == []
        assert put_args['totalConversions'] == 0
        assert put_args['totalRewards'] == 0.0
        assert put_args['EntityType'] == 'Referral'
        
        # Verify GSI2 keys for querying user's referrals
        assert put_args['GSI2PK'] == 'REFERRER#consumer-123'
        assert 'REFERRAL#' in put_args['GSI2SK']
    
    @patch('referrals.generate_referral.put_item')
    @patch('referrals.generate_referral.check_referral_code_exists')
    @patch('referrals.generate_referral.get_item')
    def test_cors_headers(
        self, mock_get_item, mock_check_exists, mock_put_item,
        mock_env, valid_consumer_token, valid_product
    ):
        """Test that CORS headers are present in response."""
        mock_get_item.return_value = valid_product
        mock_check_exists.return_value = False
        mock_put_item.return_value = {}
        
        event = {
            'headers': {'Authorization': f'Bearer {valid_consumer_token}'},
            'body': json.dumps({'productId': 'product-789'})
        }
        
        response = handler(event, None)
        
        assert 'Access-Control-Allow-Origin' in response['headers']
        assert response['headers']['Access-Control-Allow-Origin'] == '*'
        assert response['headers']['Content-Type'] == 'application/json'


class TestCheckReferralCodeExists:
    """Test referral code existence checking."""
    
    @patch('referrals.generate_referral.get_item')
    def test_code_exists(self, mock_get_item):
        """Test that existing code returns True."""
        mock_get_item.return_value = {'PK': 'REFERRAL#ABC12345', 'SK': 'METADATA'}
        
        result = check_referral_code_exists('ABC12345')
        
        assert result is True
        mock_get_item.assert_called_once_with('REFERRAL#ABC12345', 'METADATA')
    
    @patch('referrals.generate_referral.get_item')
    def test_code_not_exists(self, mock_get_item):
        """Test that non-existent code returns False."""
        mock_get_item.return_value = None
        
        result = check_referral_code_exists('XYZ98765')
        
        assert result is False
        mock_get_item.assert_called_once_with('REFERRAL#XYZ98765', 'METADATA')
    
    @patch('referrals.generate_referral.get_item')
    def test_dynamodb_error_returns_false(self, mock_get_item):
        """Test that DynamoDB error returns False (fail-safe)."""
        mock_get_item.side_effect = Exception('DynamoDB error')
        
        result = check_referral_code_exists('ERR00000')
        
        assert result is False


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
