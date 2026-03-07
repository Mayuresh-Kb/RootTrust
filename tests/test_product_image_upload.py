"""
Tests for product image upload handler.
"""
import json
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
import sys
import os

# Add backend directories to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend', 'shared'))

# Import the handler
from products import update_product_images


@pytest.fixture
def mock_env(monkeypatch):
    """Set up environment variables."""
    monkeypatch.setenv('DYNAMODB_TABLE_NAME', 'RootTrustData-test')
    monkeypatch.setenv('JWT_SECRET_KEY', 'test-secret-key')


@pytest.fixture
def valid_token():
    """Mock valid JWT token."""
    return 'Bearer valid-token'


@pytest.fixture
def farmer_user_info():
    """Mock farmer user info."""
    return {
        'userId': 'farmer-123',
        'role': 'farmer',
        'email': 'farmer@example.com'
    }


@pytest.fixture
def existing_product():
    """Mock existing product."""
    return {
        'PK': 'PRODUCT#product-123',
        'SK': 'METADATA',
        'productId': 'product-123',
        'farmerId': 'farmer-123',
        'name': 'Test Product',
        'images': [],
        'createdAt': '2024-01-01T00:00:00',
        'updatedAt': '2024-01-01T00:00:00'
    }


@pytest.fixture
def existing_product_with_images():
    """Mock existing product with images."""
    return {
        'PK': 'PRODUCT#product-123',
        'SK': 'METADATA',
        'productId': 'product-123',
        'farmerId': 'farmer-123',
        'name': 'Test Product',
        'images': [
            {'url': 'https://s3.amazonaws.com/bucket/existing-image.jpg', 'isPrimary': True}
        ],
        'createdAt': '2024-01-01T00:00:00',
        'updatedAt': '2024-01-01T00:00:00'
    }


class TestProductImageUpload:
    """Test cases for product image upload handler."""
    
    def test_missing_authorization_header(self, mock_env):
        """Test that missing authorization header returns 401."""
        event = {
            'headers': {},
            'pathParameters': {'productId': 'product-123'},
            'body': json.dumps({'imageUrls': ['https://s3.amazonaws.com/bucket/image.jpg']})
        }
        
        response = update_product_images.handler(event, None)
        
        assert response['statusCode'] == 401
        body = json.loads(response['body'])
        assert body['error']['code'] == 'UNAUTHORIZED'
    
    @patch('products.update_product_images.get_user_from_token')
    def test_invalid_token(self, mock_get_user, mock_env, valid_token):
        """Test that invalid token returns 401."""
        mock_get_user.side_effect = Exception('Invalid token')
        
        event = {
            'headers': {'Authorization': valid_token},
            'pathParameters': {'productId': 'product-123'},
            'body': json.dumps({'imageUrls': ['https://s3.amazonaws.com/bucket/image.jpg']})
        }
        
        response = update_product_images.handler(event, None)
        
        assert response['statusCode'] == 401
        body = json.loads(response['body'])
        assert body['error']['code'] == 'INVALID_TOKEN'
    
    @patch('products.update_product_images.get_user_from_token')
    def test_non_farmer_role_forbidden(self, mock_get_user, mock_env, valid_token):
        """Test that non-farmer users cannot update product images."""
        mock_get_user.return_value = {
            'userId': 'consumer-123',
            'role': 'consumer',
            'email': 'consumer@example.com'
        }
        
        event = {
            'headers': {'Authorization': valid_token},
            'pathParameters': {'productId': 'product-123'},
            'body': json.dumps({'imageUrls': ['https://s3.amazonaws.com/bucket/image.jpg']})
        }
        
        response = update_product_images.handler(event, None)
        
        assert response['statusCode'] == 403
        body = json.loads(response['body'])
        assert body['error']['code'] == 'FORBIDDEN'
    
    @patch('products.update_product_images.get_user_from_token')
    def test_missing_product_id(self, mock_get_user, mock_env, valid_token, farmer_user_info):
        """Test that missing product ID returns 400."""
        mock_get_user.return_value = farmer_user_info
        
        event = {
            'headers': {'Authorization': valid_token},
            'pathParameters': {},
            'body': json.dumps({'imageUrls': ['https://s3.amazonaws.com/bucket/image.jpg']})
        }
        
        response = update_product_images.handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error']['code'] == 'MISSING_PARAMETER'
    
    @patch('products.update_product_images.get_item')
    @patch('products.update_product_images.get_user_from_token')
    def test_product_not_found(self, mock_get_user, mock_get_item, mock_env, valid_token, farmer_user_info):
        """Test that non-existent product returns 404."""
        mock_get_user.return_value = farmer_user_info
        mock_get_item.return_value = None
        
        event = {
            'headers': {'Authorization': valid_token},
            'pathParameters': {'productId': 'product-123'},
            'body': json.dumps({'imageUrls': ['https://s3.amazonaws.com/bucket/image.jpg']})
        }
        
        response = update_product_images.handler(event, None)
        
        assert response['statusCode'] == 404
        body = json.loads(response['body'])
        assert body['error']['code'] == 'PRODUCT_NOT_FOUND'
    
    @patch('products.update_product_images.get_item')
    @patch('products.update_product_images.get_user_from_token')
    def test_farmer_cannot_update_other_farmer_product(
        self, mock_get_user, mock_get_item, mock_env, valid_token, farmer_user_info, existing_product
    ):
        """Test that farmers cannot update other farmers' products."""
        mock_get_user.return_value = farmer_user_info
        other_farmer_product = existing_product.copy()
        other_farmer_product['farmerId'] = 'other-farmer-456'
        mock_get_item.return_value = other_farmer_product
        
        event = {
            'headers': {'Authorization': valid_token},
            'pathParameters': {'productId': 'product-123'},
            'body': json.dumps({'imageUrls': ['https://s3.amazonaws.com/bucket/image.jpg']})
        }
        
        response = update_product_images.handler(event, None)
        
        assert response['statusCode'] == 403
        body = json.loads(response['body'])
        assert body['error']['code'] == 'FORBIDDEN'
    
    @patch('products.update_product_images.get_item')
    @patch('products.update_product_images.get_user_from_token')
    def test_invalid_json_body(self, mock_get_user, mock_get_item, mock_env, valid_token, farmer_user_info, existing_product):
        """Test that invalid JSON body returns 400."""
        mock_get_user.return_value = farmer_user_info
        mock_get_item.return_value = existing_product
        
        event = {
            'headers': {'Authorization': valid_token},
            'pathParameters': {'productId': 'product-123'},
            'body': 'invalid json'
        }
        
        response = update_product_images.handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error']['code'] == 'INVALID_JSON'
    
    @patch('products.update_product_images.get_item')
    @patch('products.update_product_images.get_user_from_token')
    def test_image_urls_not_array(self, mock_get_user, mock_get_item, mock_env, valid_token, farmer_user_info, existing_product):
        """Test that imageUrls must be an array."""
        mock_get_user.return_value = farmer_user_info
        mock_get_item.return_value = existing_product
        
        event = {
            'headers': {'Authorization': valid_token},
            'pathParameters': {'productId': 'product-123'},
            'body': json.dumps({'imageUrls': 'not-an-array'})
        }
        
        response = update_product_images.handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error']['code'] == 'VALIDATION_ERROR'
        assert 'array' in body['error']['message']
    
    @patch('products.update_product_images.get_item')
    @patch('products.update_product_images.get_user_from_token')
    def test_empty_image_urls(self, mock_get_user, mock_get_item, mock_env, valid_token, farmer_user_info, existing_product):
        """Test that at least one image URL is required."""
        mock_get_user.return_value = farmer_user_info
        mock_get_item.return_value = existing_product
        
        event = {
            'headers': {'Authorization': valid_token},
            'pathParameters': {'productId': 'product-123'},
            'body': json.dumps({'imageUrls': []})
        }
        
        response = update_product_images.handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error']['code'] == 'VALIDATION_ERROR'
        assert 'At least one' in body['error']['message']
    
    @patch('products.update_product_images.get_item')
    @patch('products.update_product_images.get_user_from_token')
    def test_invalid_image_url(self, mock_get_user, mock_get_item, mock_env, valid_token, farmer_user_info, existing_product):
        """Test that invalid image URLs are rejected."""
        mock_get_user.return_value = farmer_user_info
        mock_get_item.return_value = existing_product
        
        event = {
            'headers': {'Authorization': valid_token},
            'pathParameters': {'productId': 'product-123'},
            'body': json.dumps({'imageUrls': ['https://valid.com/image.jpg', '', 'another-url']})
        }
        
        response = update_product_images.handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error']['code'] == 'VALIDATION_ERROR'
        assert 'Invalid image URL' in body['error']['message']
    
    @patch('products.update_product_images.update_item')
    @patch('products.update_product_images.get_item')
    @patch('products.update_product_images.get_user_from_token')
    def test_successful_image_upload_first_image_is_primary(
        self, mock_get_user, mock_get_item, mock_update_item, 
        mock_env, valid_token, farmer_user_info, existing_product
    ):
        """Test successful image upload with first image marked as primary."""
        mock_get_user.return_value = farmer_user_info
        mock_get_item.return_value = existing_product
        
        updated_product = existing_product.copy()
        updated_product['images'] = [
            {'url': 'https://s3.amazonaws.com/bucket/image1.jpg', 'isPrimary': True},
            {'url': 'https://s3.amazonaws.com/bucket/image2.jpg', 'isPrimary': False}
        ]
        updated_product['updatedAt'] = '2024-01-02T00:00:00'
        mock_update_item.return_value = updated_product
        
        event = {
            'headers': {'Authorization': valid_token},
            'pathParameters': {'productId': 'product-123'},
            'body': json.dumps({
                'imageUrls': [
                    'https://s3.amazonaws.com/bucket/image1.jpg',
                    'https://s3.amazonaws.com/bucket/image2.jpg'
                ]
            })
        }
        
        response = update_product_images.handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['productId'] == 'product-123'
        assert body['message'] == 'Product images updated successfully'
        assert len(body['images']) == 2
        assert body['images'][0]['isPrimary'] is True
        assert body['images'][1]['isPrimary'] is False
        
        # Verify update_item was called with correct parameters
        mock_update_item.assert_called_once()
        call_args = mock_update_item.call_args
        assert call_args[1]['pk'] == 'PRODUCT#product-123'
        assert call_args[1]['sk'] == 'METADATA'
    
    @patch('products.update_product_images.update_item')
    @patch('products.update_product_images.get_item')
    @patch('products.update_product_images.get_user_from_token')
    def test_successful_image_upload_preserves_existing_images(
        self, mock_get_user, mock_get_item, mock_update_item,
        mock_env, valid_token, farmer_user_info, existing_product_with_images
    ):
        """Test that new images are added to existing images."""
        mock_get_user.return_value = farmer_user_info
        mock_get_item.return_value = existing_product_with_images
        
        updated_product = existing_product_with_images.copy()
        updated_product['images'] = [
            {'url': 'https://s3.amazonaws.com/bucket/existing-image.jpg', 'isPrimary': True},
            {'url': 'https://s3.amazonaws.com/bucket/new-image.jpg', 'isPrimary': False}
        ]
        updated_product['updatedAt'] = '2024-01-02T00:00:00'
        mock_update_item.return_value = updated_product
        
        event = {
            'headers': {'Authorization': valid_token},
            'pathParameters': {'productId': 'product-123'},
            'body': json.dumps({
                'imageUrls': ['https://s3.amazonaws.com/bucket/new-image.jpg']
            })
        }
        
        response = update_product_images.handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert len(body['images']) == 2
        # Existing image should still be primary
        assert body['images'][0]['isPrimary'] is True
        # New image should not be primary
        assert body['images'][1]['isPrimary'] is False
    
    @patch('products.update_product_images.update_item')
    @patch('products.update_product_images.get_item')
    @patch('products.update_product_images.get_user_from_token')
    def test_database_error_returns_503(
        self, mock_get_user, mock_get_item, mock_update_item,
        mock_env, valid_token, farmer_user_info, existing_product
    ):
        """Test that database errors return 503."""
        mock_get_user.return_value = farmer_user_info
        mock_get_item.return_value = existing_product
        mock_update_item.side_effect = Exception('Database error')
        
        event = {
            'headers': {'Authorization': valid_token},
            'pathParameters': {'productId': 'product-123'},
            'body': json.dumps({
                'imageUrls': ['https://s3.amazonaws.com/bucket/image.jpg']
            })
        }
        
        response = update_product_images.handler(event, None)
        
        assert response['statusCode'] == 503
        body = json.loads(response['body'])
        assert body['error']['code'] == 'SERVICE_UNAVAILABLE'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
