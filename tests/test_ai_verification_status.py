"""
Unit tests for AI verification status endpoint.
"""
import json
import pytest
import os
import sys
from unittest.mock import patch, MagicMock
from decimal import Decimal

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend', 'shared'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend', 'ai'))


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Set up environment variables for tests."""
    monkeypatch.setenv('DYNAMODB_TABLE_NAME', 'RootTrustData-test')
    monkeypatch.setenv('JWT_SECRET_KEY', 'test-secret-key-12345678')


class TestVerificationStatusEndpoint:
    """Test cases for verification status retrieval endpoint."""
    
    @patch('verification_status.get_item')
    def test_get_verification_status_success(self, mock_get_item, mock_env_vars):
        """Test successful retrieval of verification status."""
        import verification_status
        
        # Mock product with verification data
        mock_get_item.return_value = {
            'PK': 'PRODUCT#test-product-id',
            'SK': 'METADATA',
            'productId': 'test-product-id',
            'verificationStatus': 'approved',
            'fraudRiskScore': Decimal('45.5'),
            'authenticityConfidence': Decimal('85.0'),
            'predictedMarketPrice': Decimal('120.50'),
            'aiExplanation': 'Product appears authentic based on provided details.'
        }
        
        event = {
            'pathParameters': {
                'productId': 'test-product-id'
            },
            'headers': {}
        }
        
        response = verification_status.handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['productId'] == 'test-product-id'
        assert body['verificationStatus'] == 'approved'
        assert body['fraudRiskScore'] == 45.5
        assert body['authenticityConfidence'] == 85.0
        assert body['predictedMarketPrice'] == 120.50
        assert body['aiExplanation'] == 'Product appears authentic based on provided details.'
    
    @patch('verification_status.get_item')
    def test_get_verification_status_pending(self, mock_get_item, mock_env_vars):
        """Test retrieval of pending verification status."""
        import verification_status
        
        # Mock product without verification data (pending)
        mock_get_item.return_value = {
            'PK': 'PRODUCT#test-product-id',
            'SK': 'METADATA',
            'productId': 'test-product-id',
            'verificationStatus': 'pending'
        }
        
        event = {
            'pathParameters': {
                'productId': 'test-product-id'
            },
            'headers': {}
        }
        
        response = verification_status.handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['productId'] == 'test-product-id'
        assert body['verificationStatus'] == 'pending'
        # Verification details should not be present
        assert 'fraudRiskScore' not in body
        assert 'authenticityConfidence' not in body
        assert 'predictedMarketPrice' not in body
        assert 'aiExplanation' not in body
    
    @patch('verification_status.get_item')
    def test_get_verification_status_flagged(self, mock_get_item, mock_env_vars):
        """Test retrieval of flagged verification status."""
        import verification_status
        
        # Mock product with high fraud risk
        mock_get_item.return_value = {
            'PK': 'PRODUCT#test-product-id',
            'SK': 'METADATA',
            'productId': 'test-product-id',
            'verificationStatus': 'flagged',
            'fraudRiskScore': Decimal('85.0'),
            'authenticityConfidence': Decimal('30.0'),
            'predictedMarketPrice': Decimal('50.00'),
            'aiExplanation': 'High fraud risk detected due to price inconsistencies.'
        }
        
        event = {
            'pathParameters': {
                'productId': 'test-product-id'
            },
            'headers': {}
        }
        
        response = verification_status.handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['verificationStatus'] == 'flagged'
        assert body['fraudRiskScore'] == 85.0
        assert body['authenticityConfidence'] == 30.0
    
    @patch('verification_status.get_item')
    def test_get_verification_status_product_not_found(self, mock_get_item, mock_env_vars):
        """Test error when product does not exist."""
        import verification_status
        
        # Mock product not found
        mock_get_item.return_value = None
        
        event = {
            'pathParameters': {
                'productId': 'non-existent-id'
            },
            'headers': {}
        }
        
        response = verification_status.handler(event, None)
        
        assert response['statusCode'] == 404
        body = json.loads(response['body'])
        assert body['error']['code'] == 'NOT_FOUND'
        assert 'not found' in body['error']['message'].lower()
    
    def test_get_verification_status_missing_product_id(self, mock_env_vars):
        """Test error when productId is missing from path."""
        import verification_status
        
        event = {
            'pathParameters': {},
            'headers': {}
        }
        
        response = verification_status.handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error']['code'] == 'VALIDATION_ERROR'
        assert 'productId' in body['error']['message']
    
    def test_get_verification_status_no_path_parameters(self, mock_env_vars):
        """Test error when path parameters are missing."""
        import verification_status
        
        event = {
            'headers': {}
        }
        
        response = verification_status.handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error']['code'] == 'VALIDATION_ERROR'
    
    @patch('verification_status.get_item')
    @patch('verification_status.validate_jwt_token')
    def test_get_verification_status_with_valid_token(self, mock_validate_jwt, mock_get_item, mock_env_vars):
        """Test that valid JWT token is accepted but not required."""
        import verification_status
        
        # Mock JWT verification
        mock_validate_jwt.return_value = {
            'userId': 'test-user-id',
            'role': 'consumer'
        }
        
        # Mock product
        mock_get_item.return_value = {
            'PK': 'PRODUCT#test-product-id',
            'SK': 'METADATA',
            'productId': 'test-product-id',
            'verificationStatus': 'approved',
            'fraudRiskScore': Decimal('40.0'),
            'authenticityConfidence': Decimal('90.0')
        }
        
        event = {
            'pathParameters': {
                'productId': 'test-product-id'
            },
            'headers': {
                'Authorization': 'Bearer valid-token'
            }
        }
        
        response = verification_status.handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['verificationStatus'] == 'approved'
    
    @patch('verification_status.get_item')
    @patch('verification_status.validate_jwt_token')
    def test_get_verification_status_with_invalid_token(self, mock_validate_jwt, mock_get_item, mock_env_vars):
        """Test that invalid JWT token is ignored (endpoint is public)."""
        import verification_status
        
        # Mock JWT verification failure
        mock_validate_jwt.side_effect = Exception('Invalid token')
        
        # Mock product
        mock_get_item.return_value = {
            'PK': 'PRODUCT#test-product-id',
            'SK': 'METADATA',
            'productId': 'test-product-id',
            'verificationStatus': 'approved',
            'fraudRiskScore': Decimal('40.0')
        }
        
        event = {
            'pathParameters': {
                'productId': 'test-product-id'
            },
            'headers': {
                'Authorization': 'Bearer invalid-token'
            }
        }
        
        response = verification_status.handler(event, None)
        
        # Should still succeed - token is optional
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['verificationStatus'] == 'approved'
    
    @patch('verification_status.get_item')
    def test_get_verification_status_partial_data(self, mock_get_item, mock_env_vars):
        """Test handling of product with partial verification data."""
        import verification_status
        
        # Mock product with only some verification fields
        mock_get_item.return_value = {
            'PK': 'PRODUCT#test-product-id',
            'SK': 'METADATA',
            'productId': 'test-product-id',
            'verificationStatus': 'approved',
            'fraudRiskScore': Decimal('50.0'),
            # Missing authenticityConfidence, predictedMarketPrice, aiExplanation
        }
        
        event = {
            'pathParameters': {
                'productId': 'test-product-id'
            },
            'headers': {}
        }
        
        response = verification_status.handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['verificationStatus'] == 'approved'
        assert body['fraudRiskScore'] == 50.0
        # Missing fields should not be in response
        assert 'authenticityConfidence' not in body
        assert 'predictedMarketPrice' not in body
        assert 'aiExplanation' not in body
    
    @patch('verification_status.get_item')
    def test_get_verification_status_decimal_conversion(self, mock_get_item, mock_env_vars):
        """Test that Decimal values are properly converted to float."""
        import verification_status
        
        # Mock product with Decimal values
        mock_get_item.return_value = {
            'PK': 'PRODUCT#test-product-id',
            'SK': 'METADATA',
            'productId': 'test-product-id',
            'verificationStatus': 'approved',
            'fraudRiskScore': Decimal('45.567'),
            'authenticityConfidence': Decimal('85.123'),
            'predictedMarketPrice': Decimal('120.999')
        }
        
        event = {
            'pathParameters': {
                'productId': 'test-product-id'
            },
            'headers': {}
        }
        
        response = verification_status.handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        # Verify values are floats, not Decimal objects
        assert isinstance(body['fraudRiskScore'], float)
        assert isinstance(body['authenticityConfidence'], float)
        assert isinstance(body['predictedMarketPrice'], float)
        assert body['fraudRiskScore'] == 45.567
        assert body['authenticityConfidence'] == 85.123
        assert body['predictedMarketPrice'] == 120.999


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
