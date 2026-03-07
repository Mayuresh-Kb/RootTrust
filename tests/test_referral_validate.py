"""
Unit tests for referral validation endpoint.
Tests GET /referrals/{code} functionality.
"""
import json
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from referrals.validate_referral import handler


@pytest.fixture
def mock_env():
    """Set up environment variables for tests."""
    os.environ['DYNAMODB_TABLE_NAME'] = 'RootTrustData'


@pytest.fixture
def valid_referral():
    """Mock referral data."""
    return {
        'PK': 'REFERRAL#ABC12345',
        'SK': 'METADATA',
        'EntityType': 'Referral',
        'referralCode': 'ABC12345',
        'referrerId': 'consumer-123',
        'productId': 'product-789',
        'conversions': [],
        'totalConversions': 0,
        'totalRewards': 0.0,
        'createdAt': '2024-01-15T10:30:00Z',
        'GSI2PK': 'REFERRER#consumer-123',
        'GSI2SK': 'REFERRAL#2024-01-15T10:30:00Z'
    }


class TestReferralValidationEndpoint:
    """Test referral validation endpoint."""
    
    def test_missing_referral_code(self, mock_env):
        """Test that missing referral code returns 400."""
        event = {
            'pathParameters': {}
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error']['code'] == 'INVALID_REQUEST'
        assert 'required' in body['error']['message'].lower()
    
    def test_empty_path_parameters(self, mock_env):
        """Test that empty path parameters returns 400."""
        event = {
            'pathParameters': None
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error']['code'] == 'INVALID_REQUEST'
    
    @patch('referrals.validate_referral.get_item')
    def test_referral_not_found(self, mock_get_item, mock_env):
        """Test that non-existent referral code returns 404."""
        mock_get_item.return_value = None
        
        event = {
            'pathParameters': {'code': 'INVALID99'}
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 404
        body = json.loads(response['body'])
        assert body['error']['code'] == 'RESOURCE_NOT_FOUND'
        assert 'INVALID99' in body['error']['message']
        
        # Verify get_item was called with correct parameters
        mock_get_item.assert_called_once_with('REFERRAL#INVALID99', 'METADATA')
    
    @patch('referrals.validate_referral.get_item')
    def test_successful_referral_validation(self, mock_get_item, mock_env, valid_referral):
        """Test successful referral validation returns correct details."""
        mock_get_item.return_value = valid_referral
        
        event = {
            'pathParameters': {'code': 'ABC12345'}
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        
        # Verify response structure
        assert 'referralCode' in body
        assert 'referrerId' in body
        assert 'productId' in body
        assert 'message' in body
        
        # Verify response values
        assert body['referralCode'] == 'ABC12345'
        assert body['referrerId'] == 'consumer-123'
        assert body['productId'] == 'product-789'
        assert 'valid' in body['message'].lower()
        
        # Verify get_item was called with correct parameters
        mock_get_item.assert_called_once_with('REFERRAL#ABC12345', 'METADATA')
    
    @patch('referrals.validate_referral.get_item')
    def test_dynamodb_service_error(self, mock_get_item, mock_env):
        """Test that DynamoDB service error returns 503."""
        from backend.shared.exceptions import ServiceUnavailableError
        mock_get_item.side_effect = ServiceUnavailableError('DynamoDB', 'Service unavailable')
        
        event = {
            'pathParameters': {'code': 'ABC12345'}
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 503
        body = json.loads(response['body'])
        assert body['error']['code'] == 'SERVICE_UNAVAILABLE'
        assert 'failed to query' in body['error']['message'].lower()
    
    @patch('referrals.validate_referral.get_item')
    def test_unexpected_database_error(self, mock_get_item, mock_env):
        """Test that unexpected database error returns 503."""
        mock_get_item.side_effect = Exception('Unexpected database error')
        
        event = {
            'pathParameters': {'code': 'ABC12345'}
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 503
        body = json.loads(response['body'])
        assert body['error']['code'] == 'SERVICE_UNAVAILABLE'
    
    @patch('referrals.validate_referral.get_item')
    def test_cors_headers(self, mock_get_item, mock_env, valid_referral):
        """Test that CORS headers are present in response."""
        mock_get_item.return_value = valid_referral
        
        event = {
            'pathParameters': {'code': 'ABC12345'}
        }
        
        response = handler(event, None)
        
        assert 'Access-Control-Allow-Origin' in response['headers']
        assert response['headers']['Access-Control-Allow-Origin'] == '*'
        assert response['headers']['Content-Type'] == 'application/json'
    
    @patch('referrals.validate_referral.get_item')
    def test_cors_headers_on_error(self, mock_get_item, mock_env):
        """Test that CORS headers are present even on error responses."""
        mock_get_item.return_value = None
        
        event = {
            'pathParameters': {'code': 'INVALID99'}
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 404
        assert 'Access-Control-Allow-Origin' in response['headers']
        assert response['headers']['Access-Control-Allow-Origin'] == '*'
    
    @patch('referrals.validate_referral.get_item')
    def test_referral_with_conversions(self, mock_get_item, mock_env):
        """Test validation of referral that has conversions."""
        referral_with_conversions = {
            'PK': 'REFERRAL#XYZ98765',
            'SK': 'METADATA',
            'EntityType': 'Referral',
            'referralCode': 'XYZ98765',
            'referrerId': 'consumer-456',
            'productId': 'product-999',
            'conversions': [
                {
                    'referredUserId': 'consumer-789',
                    'orderId': 'order-111',
                    'rewardAmount': 25.0,
                    'convertedAt': '2024-01-16T12:00:00Z'
                }
            ],
            'totalConversions': 1,
            'totalRewards': 25.0,
            'createdAt': '2024-01-15T10:30:00Z',
            'GSI2PK': 'REFERRER#consumer-456',
            'GSI2SK': 'REFERRAL#2024-01-15T10:30:00Z'
        }
        mock_get_item.return_value = referral_with_conversions
        
        event = {
            'pathParameters': {'code': 'XYZ98765'}
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        
        # Verify basic referral details are returned
        assert body['referralCode'] == 'XYZ98765'
        assert body['referrerId'] == 'consumer-456'
        assert body['productId'] == 'product-999'
        
        # Note: conversions and rewards are not exposed in the public validation endpoint
        # This is intentional for privacy/security
    
    @patch('referrals.validate_referral.get_item')
    def test_case_sensitive_referral_code(self, mock_get_item, mock_env, valid_referral):
        """Test that referral codes are case-sensitive."""
        mock_get_item.return_value = valid_referral
        
        # Test with exact case
        event = {
            'pathParameters': {'code': 'ABC12345'}
        }
        
        response = handler(event, None)
        assert response['statusCode'] == 200
        
        # Verify the exact code was used in the query
        mock_get_item.assert_called_with('REFERRAL#ABC12345', 'METADATA')
    
    @patch('referrals.validate_referral.get_item')
    def test_special_characters_in_code(self, mock_get_item, mock_env):
        """Test handling of special characters in referral code."""
        # Even though our generation only uses alphanumeric,
        # the validation endpoint should handle any string safely
        mock_get_item.return_value = None
        
        event = {
            'pathParameters': {'code': 'ABC-123!@'}
        }
        
        response = handler(event, None)
        
        # Should return 404 for non-existent code
        assert response['statusCode'] == 404
        
        # Verify it attempted to query with the exact code
        mock_get_item.assert_called_once_with('REFERRAL#ABC-123!@', 'METADATA')
    
    @patch('referrals.validate_referral.get_item')
    def test_whitespace_in_code(self, mock_get_item, mock_env):
        """Test handling of whitespace in referral code."""
        mock_get_item.return_value = None
        
        event = {
            'pathParameters': {'code': 'ABC 123'}
        }
        
        response = handler(event, None)
        
        # Should return 404 for non-existent code
        assert response['statusCode'] == 404
        
        # Verify it attempted to query with the exact code (including whitespace)
        mock_get_item.assert_called_once_with('REFERRAL#ABC 123', 'METADATA')
    
    @patch('referrals.validate_referral.get_item')
    def test_very_long_referral_code(self, mock_get_item, mock_env):
        """Test handling of unusually long referral code."""
        long_code = 'A' * 100
        mock_get_item.return_value = None
        
        event = {
            'pathParameters': {'code': long_code}
        }
        
        response = handler(event, None)
        
        # Should handle gracefully and return 404
        assert response['statusCode'] == 404
    
    @patch('referrals.validate_referral.get_item')
    def test_empty_string_referral_code(self, mock_get_item, mock_env):
        """Test handling of empty string as referral code."""
        event = {
            'pathParameters': {'code': ''}
        }
        
        response = handler(event, None)
        
        # Empty string should be treated as missing
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error']['code'] == 'INVALID_REQUEST'
    
    @patch('referrals.validate_referral.get_item')
    def test_response_json_format(self, mock_get_item, mock_env, valid_referral):
        """Test that response body is valid JSON."""
        mock_get_item.return_value = valid_referral
        
        event = {
            'pathParameters': {'code': 'ABC12345'}
        }
        
        response = handler(event, None)
        
        # Should not raise exception
        body = json.loads(response['body'])
        
        # Verify it's a dictionary
        assert isinstance(body, dict)
    
    @patch('referrals.validate_referral.get_item')
    def test_no_authentication_required(self, mock_get_item, mock_env, valid_referral):
        """Test that endpoint works without authentication (public endpoint)."""
        mock_get_item.return_value = valid_referral
        
        # Event without any authorization headers
        event = {
            'pathParameters': {'code': 'ABC12345'},
            'headers': {}
        }
        
        response = handler(event, None)
        
        # Should succeed without authentication
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['referralCode'] == 'ABC12345'


class TestReferralValidationEdgeCases:
    """Test edge cases for referral validation."""
    
    @patch('referrals.validate_referral.get_item')
    def test_referral_missing_referrer_id(self, mock_get_item, mock_env):
        """Test handling of malformed referral missing referrerId."""
        malformed_referral = {
            'PK': 'REFERRAL#BAD12345',
            'SK': 'METADATA',
            'EntityType': 'Referral',
            'referralCode': 'BAD12345',
            # Missing referrerId
            'productId': 'product-789',
            'conversions': [],
            'totalConversions': 0,
            'totalRewards': 0.0,
            'createdAt': '2024-01-15T10:30:00Z'
        }
        mock_get_item.return_value = malformed_referral
        
        event = {
            'pathParameters': {'code': 'BAD12345'}
        }
        
        response = handler(event, None)
        
        # Should still return 200 but with None for referrerId
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['referrerId'] is None
        assert body['productId'] == 'product-789'
    
    @patch('referrals.validate_referral.get_item')
    def test_referral_missing_product_id(self, mock_get_item, mock_env):
        """Test handling of malformed referral missing productId."""
        malformed_referral = {
            'PK': 'REFERRAL#BAD67890',
            'SK': 'METADATA',
            'EntityType': 'Referral',
            'referralCode': 'BAD67890',
            'referrerId': 'consumer-123',
            # Missing productId
            'conversions': [],
            'totalConversions': 0,
            'totalRewards': 0.0,
            'createdAt': '2024-01-15T10:30:00Z'
        }
        mock_get_item.return_value = malformed_referral
        
        event = {
            'pathParameters': {'code': 'BAD67890'}
        }
        
        response = handler(event, None)
        
        # Should still return 200 but with None for productId
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['referrerId'] == 'consumer-123'
        assert body['productId'] is None
    
    def test_completely_malformed_event(self, mock_env):
        """Test handling of completely malformed event."""
        event = {}
        
        response = handler(event, None)
        
        # Should handle gracefully
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'error' in body


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
