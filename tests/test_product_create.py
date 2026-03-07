"""
Unit tests for product creation endpoint.
"""
import json
import pytest
import os
import sys
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend', 'shared'))

from shared.constants import UserRole, VerificationStatus, ProductCategory


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Set up environment variables for tests."""
    monkeypatch.setenv('DYNAMODB_TABLE_NAME', 'RootTrustData-test')
    monkeypatch.setenv('BUCKET_NAME', 'roottrust-assets-test')
    monkeypatch.setenv('JWT_SECRET_KEY', 'test-secret-key-12345678')


@pytest.fixture
def valid_product_data():
    """Valid product creation request data."""
    return {
        'name': 'Organic Tomatoes',
        'category': 'vegetables',
        'description': 'Fresh organic tomatoes from our farm',
        'price': 50.0,
        'unit': 'kg',
        'quantity': 100,
        'hasGITag': True,
        'giTagName': 'Nashik Tomato',
        'giTagRegion': 'Nashik, Maharashtra',
        'isSeasonal': True,
        'seasonStart': '2024-01-01T00:00:00',
        'seasonEnd': '2024-06-30T23:59:59'
    }


@pytest.fixture
def farmer_token_payload():
    """Mock farmer JWT token payload."""
    return {
        'userId': 'farmer-123',
        'email': 'farmer@example.com',
        'role': 'farmer'
    }


@pytest.fixture
def consumer_token_payload():
    """Mock consumer JWT token payload."""
    return {
        'userId': 'consumer-123',
        'email': 'consumer@example.com',
        'role': 'consumer'
    }


class TestProductCreation:
    """Test cases for product creation endpoint."""
    
    def test_create_product_success(self, mock_env_vars, valid_product_data, farmer_token_payload):
        """Test successful product creation by farmer."""
        # Import after env vars are set
        from products.create_product import handler
        
        # Mock dependencies
        with patch('products.create_product.get_user_from_token') as mock_auth, \
             patch('products.create_product.put_item') as mock_put, \
             patch('products.create_product.generate_presigned_urls') as mock_urls:
            
            # Setup mocks
            mock_auth.return_value = farmer_token_payload
            mock_put.return_value = {}
            mock_urls.return_value = [
                {
                    'url': 'https://s3.amazonaws.com/presigned-url-1',
                    'key': 'products/test-id/images/image-1.jpg',
                    'expiresIn': 900
                }
            ]
            
            # Create event
            event = {
                'headers': {
                    'Authorization': 'Bearer valid-token'
                },
                'body': json.dumps(valid_product_data)
            }
            
            # Call handler
            response = handler(event, None)
            
            # Assertions
            assert response['statusCode'] == 201
            body = json.loads(response['body'])
            assert 'productId' in body
            assert body['status'] == 'pending'
            assert 'uploadUrls' in body
            assert len(body['uploadUrls']) > 0
            
            # Verify put_item was called
            mock_put.assert_called_once()
            product_dict = mock_put.call_args[0][0]
            assert product_dict['name'] == 'Organic Tomatoes'
            assert product_dict['category'] == 'vegetables'
            assert product_dict['price'] == 50.0
            assert product_dict['farmerId'] == 'farmer-123'
            assert product_dict['verificationStatus'] == 'pending'
    
    def test_create_product_missing_auth_header(self, mock_env_vars, valid_product_data):
        """Test product creation without authorization header."""
        from products.create_product import handler
        
        event = {
            'headers': {},
            'body': json.dumps(valid_product_data)
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 401
        body = json.loads(response['body'])
        assert body['error']['code'] == 'UNAUTHORIZED'
    
    def test_create_product_consumer_forbidden(self, mock_env_vars, valid_product_data, consumer_token_payload):
        """Test that consumers cannot create products."""
        from products.create_product import handler
        
        with patch('products.create_product.get_user_from_token') as mock_auth:
            mock_auth.return_value = consumer_token_payload
            
            event = {
                'headers': {
                    'Authorization': 'Bearer consumer-token'
                },
                'body': json.dumps(valid_product_data)
            }
            
            response = handler(event, None)
            
            assert response['statusCode'] == 403
            body = json.loads(response['body'])
            assert body['error']['code'] == 'FORBIDDEN'
            assert 'farmers' in body['error']['message'].lower()
    
    def test_create_product_invalid_json(self, mock_env_vars, farmer_token_payload):
        """Test product creation with invalid JSON."""
        from products.create_product import handler
        
        with patch('products.create_product.get_user_from_token') as mock_auth:
            mock_auth.return_value = farmer_token_payload
            
            event = {
                'headers': {
                    'Authorization': 'Bearer valid-token'
                },
                'body': 'invalid json {'
            }
            
            response = handler(event, None)
            
            assert response['statusCode'] == 400
            body = json.loads(response['body'])
            assert body['error']['code'] == 'INVALID_JSON'
    
    def test_create_product_negative_price(self, mock_env_vars, valid_product_data, farmer_token_payload):
        """Test product creation with negative price."""
        from products.create_product import handler
        
        with patch('products.create_product.get_user_from_token') as mock_auth:
            mock_auth.return_value = farmer_token_payload
            
            # Set negative price
            invalid_data = valid_product_data.copy()
            invalid_data['price'] = -10.0
            
            event = {
                'headers': {
                    'Authorization': 'Bearer valid-token'
                },
                'body': json.dumps(invalid_data)
            }
            
            response = handler(event, None)
            
            assert response['statusCode'] == 400
            body = json.loads(response['body'])
            assert body['error']['code'] == 'VALIDATION_ERROR'
    
    def test_create_product_zero_price(self, mock_env_vars, valid_product_data, farmer_token_payload):
        """Test product creation with zero price."""
        from products.create_product import handler
        
        with patch('products.create_product.get_user_from_token') as mock_auth:
            mock_auth.return_value = farmer_token_payload
            
            # Set zero price
            invalid_data = valid_product_data.copy()
            invalid_data['price'] = 0
            
            event = {
                'headers': {
                    'Authorization': 'Bearer valid-token'
                },
                'body': json.dumps(invalid_data)
            }
            
            response = handler(event, None)
            
            assert response['statusCode'] == 400
            body = json.loads(response['body'])
            assert body['error']['code'] == 'VALIDATION_ERROR'
    
    def test_create_product_invalid_category(self, mock_env_vars, valid_product_data, farmer_token_payload):
        """Test product creation with invalid category."""
        from products.create_product import handler
        
        with patch('products.create_product.get_user_from_token') as mock_auth:
            mock_auth.return_value = farmer_token_payload
            
            # Set invalid category
            invalid_data = valid_product_data.copy()
            invalid_data['category'] = 'invalid_category'
            
            event = {
                'headers': {
                    'Authorization': 'Bearer valid-token'
                },
                'body': json.dumps(invalid_data)
            }
            
            response = handler(event, None)
            
            assert response['statusCode'] == 400
            body = json.loads(response['body'])
            assert body['error']['code'] == 'VALIDATION_ERROR'
    
    def test_create_product_missing_required_fields(self, mock_env_vars, farmer_token_payload):
        """Test product creation with missing required fields."""
        from products.create_product import handler
        
        with patch('products.create_product.get_user_from_token') as mock_auth:
            mock_auth.return_value = farmer_token_payload
            
            # Minimal data missing required fields
            incomplete_data = {
                'name': 'Test Product'
            }
            
            event = {
                'headers': {
                    'Authorization': 'Bearer valid-token'
                },
                'body': json.dumps(incomplete_data)
            }
            
            response = handler(event, None)
            
            assert response['statusCode'] == 400
            body = json.loads(response['body'])
            assert body['error']['code'] == 'VALIDATION_ERROR'
    
    def test_create_product_dynamodb_error(self, mock_env_vars, valid_product_data, farmer_token_payload):
        """Test product creation when DynamoDB fails."""
        from products.create_product import handler
        
        with patch('products.create_product.get_user_from_token') as mock_auth, \
             patch('products.create_product.put_item') as mock_put:
            
            mock_auth.return_value = farmer_token_payload
            mock_put.side_effect = Exception('DynamoDB error')
            
            event = {
                'headers': {
                    'Authorization': 'Bearer valid-token'
                },
                'body': json.dumps(valid_product_data)
            }
            
            response = handler(event, None)
            
            assert response['statusCode'] == 503
            body = json.loads(response['body'])
            assert body['error']['code'] == 'SERVICE_UNAVAILABLE'
    
    def test_create_product_without_gi_tag(self, mock_env_vars, valid_product_data, farmer_token_payload):
        """Test product creation without GI tag."""
        from products.create_product import handler
        
        with patch('products.create_product.get_user_from_token') as mock_auth, \
             patch('products.create_product.put_item') as mock_put, \
             patch('products.create_product.generate_presigned_urls') as mock_urls:
            
            mock_auth.return_value = farmer_token_payload
            mock_put.return_value = {}
            mock_urls.return_value = []
            
            # Remove GI tag
            data_without_gi = valid_product_data.copy()
            data_without_gi['hasGITag'] = False
            data_without_gi['giTagName'] = None
            data_without_gi['giTagRegion'] = None
            
            event = {
                'headers': {
                    'Authorization': 'Bearer valid-token'
                },
                'body': json.dumps(data_without_gi)
            }
            
            response = handler(event, None)
            
            assert response['statusCode'] == 201
            body = json.loads(response['body'])
            assert 'productId' in body
    
    def test_create_product_without_seasonal_info(self, mock_env_vars, valid_product_data, farmer_token_payload):
        """Test product creation without seasonal information."""
        from products.create_product import handler
        
        with patch('products.create_product.get_user_from_token') as mock_auth, \
             patch('products.create_product.put_item') as mock_put, \
             patch('products.create_product.generate_presigned_urls') as mock_urls:
            
            mock_auth.return_value = farmer_token_payload
            mock_put.return_value = {}
            mock_urls.return_value = []
            
            # Remove seasonal info
            data_without_seasonal = valid_product_data.copy()
            data_without_seasonal['isSeasonal'] = False
            data_without_seasonal['seasonStart'] = None
            data_without_seasonal['seasonEnd'] = None
            
            event = {
                'headers': {
                    'Authorization': 'Bearer valid-token'
                },
                'body': json.dumps(data_without_seasonal)
            }
            
            response = handler(event, None)
            
            assert response['statusCode'] == 201
            body = json.loads(response['body'])
            assert 'productId' in body


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
