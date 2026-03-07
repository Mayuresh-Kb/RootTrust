"""
Unit tests for product update endpoint.
Tests PUT /products/{productId} functionality.
"""
import json
import pytest
import os
import sys
from datetime import datetime
from unittest.mock import patch, MagicMock

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend', 'products'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import update_product
from shared.constants import UserRole, VerificationStatus


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Set up environment variables for tests."""
    monkeypatch.setenv('DYNAMODB_TABLE_NAME', 'test-table')
    monkeypatch.setenv('JWT_SECRET_KEY', 'test-secret-key-12345')


@pytest.fixture
def valid_token():
    """Generate a valid JWT token for testing."""
    from shared.auth import generate_jwt_token
    token_data = generate_jwt_token(
        user_id='farmer-123',
        email='farmer@example.com',
        role=UserRole.FARMER.value,
        secret_key='test-secret-key-12345'
    )
    return token_data['token']


@pytest.fixture
def existing_product():
    """Sample existing product data."""
    return {
        'PK': 'PRODUCT#product-123',
        'SK': 'METADATA',
        'productId': 'product-123',
        'farmerId': 'farmer-123',
        'name': 'Original Product Name',
        'category': 'vegetables',
        'description': 'Original description of the product',
        'price': 100.0,
        'unit': 'kg',
        'quantity': 50,
        'verificationStatus': VerificationStatus.APPROVED.value,
        'createdAt': '2024-01-01T00:00:00',
        'updatedAt': '2024-01-01T00:00:00'
    }


def test_update_product_success(mock_env_vars, valid_token, existing_product):
    """Test successful product update."""
    event = {
        'headers': {
            'Authorization': f'Bearer {valid_token}'
        },
        'pathParameters': {
            'productId': 'product-123'
        },
        'body': json.dumps({
            'name': 'Updated Product Name',
            'price': 150.0,
            'quantity': 75
        })
    }
    
    with patch('update_product.get_item') as mock_get, \
         patch('update_product.update_item') as mock_update:
        
        mock_get.return_value = existing_product
        mock_update.return_value = {
            **existing_product,
            'name': 'Updated Product Name',
            'price': 150.0,
            'quantity': 75,
            'updatedAt': datetime.utcnow().isoformat()
        }
        
        response = update_product.handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['productId'] == 'product-123'
        assert body['message'] == 'Product updated successfully'
        assert body['updatedFields']['name'] == 'Updated Product Name'
        assert body['updatedFields']['price'] == 150.0
        assert body['updatedFields']['quantity'] == 75


def test_update_product_missing_auth_header(mock_env_vars):
    """Test update without authorization header."""
    event = {
        'headers': {},
        'pathParameters': {
            'productId': 'product-123'
        },
        'body': json.dumps({
            'name': 'Updated Name'
        })
    }
    
    response = update_product.handler(event, None)
    
    assert response['statusCode'] == 401
    body = json.loads(response['body'])
    assert body['error']['code'] == 'UNAUTHORIZED'


def test_update_product_invalid_token(mock_env_vars):
    """Test update with invalid JWT token."""
    event = {
        'headers': {
            'Authorization': 'Bearer invalid-token'
        },
        'pathParameters': {
            'productId': 'product-123'
        },
        'body': json.dumps({
            'name': 'Updated Name'
        })
    }
    
    response = update_product.handler(event, None)
    
    assert response['statusCode'] == 401
    body = json.loads(response['body'])
    assert body['error']['code'] == 'INVALID_TOKEN'


def test_update_product_non_farmer_role(mock_env_vars):
    """Test update by non-farmer user."""
    from shared.auth import generate_jwt_token
    consumer_token = generate_jwt_token(
        user_id='consumer-123',
        email='consumer@example.com',
        role=UserRole.CONSUMER.value,
        secret_key='test-secret-key-12345'
    )['token']
    
    event = {
        'headers': {
            'Authorization': f'Bearer {consumer_token}'
        },
        'pathParameters': {
            'productId': 'product-123'
        },
        'body': json.dumps({
            'name': 'Updated Name'
        })
    }
    
    response = update_product.handler(event, None)
    
    assert response['statusCode'] == 403
    body = json.loads(response['body'])
    assert body['error']['code'] == 'FORBIDDEN'
    assert 'Only farmers can update products' in body['error']['message']


def test_update_product_not_found(mock_env_vars, valid_token):
    """Test update of non-existent product."""
    event = {
        'headers': {
            'Authorization': f'Bearer {valid_token}'
        },
        'pathParameters': {
            'productId': 'nonexistent-product'
        },
        'body': json.dumps({
            'name': 'Updated Name'
        })
    }
    
    with patch('update_product.get_item') as mock_get:
        mock_get.return_value = None
        
        response = update_product.handler(event, None)
        
        assert response['statusCode'] == 404
        body = json.loads(response['body'])
        assert body['error']['code'] == 'PRODUCT_NOT_FOUND'


def test_update_product_not_owner(mock_env_vars, existing_product):
    """Test update by farmer who doesn't own the product."""
    from shared.auth import generate_jwt_token
    other_farmer_token = generate_jwt_token(
        user_id='other-farmer-456',
        email='other@example.com',
        role=UserRole.FARMER.value,
        secret_key='test-secret-key-12345'
    )['token']
    
    event = {
        'headers': {
            'Authorization': f'Bearer {other_farmer_token}'
        },
        'pathParameters': {
            'productId': 'product-123'
        },
        'body': json.dumps({
            'name': 'Updated Name'
        })
    }
    
    with patch('update_product.get_item') as mock_get:
        mock_get.return_value = existing_product
        
        response = update_product.handler(event, None)
        
        assert response['statusCode'] == 403
        body = json.loads(response['body'])
        assert body['error']['code'] == 'FORBIDDEN'
        assert 'You can only update your own products' in body['error']['message']


def test_update_product_invalid_json(mock_env_vars, valid_token, existing_product):
    """Test update with invalid JSON body."""
    event = {
        'headers': {
            'Authorization': f'Bearer {valid_token}'
        },
        'pathParameters': {
            'productId': 'product-123'
        },
        'body': 'invalid json'
    }
    
    with patch('update_product.get_item') as mock_get:
        mock_get.return_value = existing_product
        
        response = update_product.handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error']['code'] == 'INVALID_JSON'


def test_update_product_negative_price(mock_env_vars, valid_token, existing_product):
    """Test update with negative price (should fail validation)."""
    event = {
        'headers': {
            'Authorization': f'Bearer {valid_token}'
        },
        'pathParameters': {
            'productId': 'product-123'
        },
        'body': json.dumps({
            'price': -50.0
        })
    }
    
    with patch('update_product.get_item') as mock_get:
        mock_get.return_value = existing_product
        
        response = update_product.handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error']['code'] == 'VALIDATION_ERROR'


def test_update_product_partial_update(mock_env_vars, valid_token, existing_product):
    """Test partial product update (only some fields)."""
    event = {
        'headers': {
            'Authorization': f'Bearer {valid_token}'
        },
        'pathParameters': {
            'productId': 'product-123'
        },
        'body': json.dumps({
            'description': 'Updated description only'
        })
    }
    
    with patch('update_product.get_item') as mock_get, \
         patch('update_product.update_item') as mock_update:
        
        mock_get.return_value = existing_product
        mock_update.return_value = {
            **existing_product,
            'description': 'Updated description only',
            'updatedAt': datetime.utcnow().isoformat()
        }
        
        response = update_product.handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['updatedFields']['description'] == 'Updated description only'
        assert body['updatedFields']['name'] is None  # Not updated
        assert body['updatedFields']['price'] is None  # Not updated


def test_update_product_missing_product_id(mock_env_vars, valid_token):
    """Test update without product ID in path."""
    event = {
        'headers': {
            'Authorization': f'Bearer {valid_token}'
        },
        'pathParameters': {},
        'body': json.dumps({
            'name': 'Updated Name'
        })
    }
    
    response = update_product.handler(event, None)
    
    assert response['statusCode'] == 400
    body = json.loads(response['body'])
    assert body['error']['code'] == 'MISSING_PARAMETER'


def test_update_product_database_error(mock_env_vars, valid_token, existing_product):
    """Test update when database update fails."""
    event = {
        'headers': {
            'Authorization': f'Bearer {valid_token}'
        },
        'pathParameters': {
            'productId': 'product-123'
        },
        'body': json.dumps({
            'name': 'Updated Name'
        })
    }
    
    with patch('update_product.get_item') as mock_get, \
         patch('update_product.update_item') as mock_update:
        
        mock_get.return_value = existing_product
        mock_update.side_effect = Exception('Database error')
        
        response = update_product.handler(event, None)
        
        assert response['statusCode'] == 503
        body = json.loads(response['body'])
        assert body['error']['code'] == 'SERVICE_UNAVAILABLE'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
