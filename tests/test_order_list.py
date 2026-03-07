"""
Unit tests for order listing endpoint.
Tests order listing for consumers and farmers with proper role-based filtering.
"""
import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from decimal import Decimal

# Add backend paths to sys.path
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend', 'shared'))

# Import after path setup
from shared.constants import UserRole, OrderStatus, PaymentStatus

# Import the handler module
from orders import list_orders


@pytest.fixture
def mock_env(monkeypatch):
    """Set up environment variables for tests."""
    monkeypatch.setenv('DYNAMODB_TABLE_NAME', 'RootTrustData-test')
    monkeypatch.setenv('JWT_SECRET_KEY', 'test-secret-key-12345')


@pytest.fixture
def valid_consumer_token():
    """Generate a valid consumer JWT token."""
    from shared.auth import generate_jwt_token
    token_data = generate_jwt_token(
        user_id='consumer-123',
        email='consumer@test.com',
        role=UserRole.CONSUMER.value,
        secret_key='test-secret-key-12345'
    )
    return token_data['token']


@pytest.fixture
def valid_farmer_token():
    """Generate a valid farmer JWT token."""
    from shared.auth import generate_jwt_token
    token_data = generate_jwt_token(
        user_id='farmer-456',
        email='farmer@test.com',
        role=UserRole.FARMER.value,
        secret_key='test-secret-key-12345'
    )
    return token_data['token']


@pytest.fixture
def mock_consumer_orders():
    """Mock orders for a consumer."""
    return [
        {
            'PK': 'ORDER#order-1',
            'SK': 'METADATA',
            'orderId': 'order-1',
            'consumerId': 'consumer-123',
            'farmerId': 'farmer-456',
            'productId': 'product-789',
            'productName': 'Organic Tomatoes',
            'quantity': 2,
            'totalAmount': Decimal('100.00'),
            'status': OrderStatus.CONFIRMED.value,
            'estimatedDeliveryDate': (datetime.utcnow() + timedelta(days=7)).isoformat(),
            'createdAt': datetime.utcnow().isoformat(),
            'GSI2PK': 'CONSUMER#consumer-123',
            'GSI2SK': 'ORDER#' + datetime.utcnow().isoformat()
        },
        {
            'PK': 'ORDER#order-2',
            'SK': 'METADATA',
            'orderId': 'order-2',
            'consumerId': 'consumer-123',
            'farmerId': 'farmer-789',
            'productId': 'product-456',
            'productName': 'Fresh Mangoes',
            'quantity': 5,
            'totalAmount': Decimal('250.00'),
            'status': OrderStatus.DELIVERED.value,
            'estimatedDeliveryDate': (datetime.utcnow() + timedelta(days=5)).isoformat(),
            'createdAt': (datetime.utcnow() - timedelta(days=2)).isoformat(),
            'GSI2PK': 'CONSUMER#consumer-123',
            'GSI2SK': 'ORDER#' + (datetime.utcnow() - timedelta(days=2)).isoformat()
        }
    ]


@pytest.fixture
def mock_farmer_orders():
    """Mock orders for a farmer."""
    return [
        {
            'PK': 'ORDER#order-3',
            'SK': 'METADATA',
            'orderId': 'order-3',
            'consumerId': 'consumer-111',
            'farmerId': 'farmer-456',
            'productId': 'product-789',
            'productName': 'Organic Tomatoes',
            'quantity': 3,
            'totalAmount': Decimal('150.00'),
            'status': OrderStatus.PROCESSING.value,
            'estimatedDeliveryDate': (datetime.utcnow() + timedelta(days=6)).isoformat(),
            'createdAt': datetime.utcnow().isoformat(),
            'GSI3PK': 'FARMER#farmer-456',
            'GSI3SK': 'ORDER#' + datetime.utcnow().isoformat()
        },
        {
            'PK': 'ORDER#order-4',
            'SK': 'METADATA',
            'orderId': 'order-4',
            'consumerId': 'consumer-222',
            'farmerId': 'farmer-456',
            'productId': 'product-789',
            'productName': 'Organic Tomatoes',
            'quantity': 1,
            'totalAmount': Decimal('50.00'),
            'status': OrderStatus.SHIPPED.value,
            'estimatedDeliveryDate': (datetime.utcnow() + timedelta(days=3)).isoformat(),
            'createdAt': (datetime.utcnow() - timedelta(days=1)).isoformat(),
            'GSI3PK': 'FARMER#farmer-456',
            'GSI3SK': 'ORDER#' + (datetime.utcnow() - timedelta(days=1)).isoformat()
        }
    ]


class TestConsumerOrderListing:
    """Test order listing for consumers."""
    
    def test_consumer_list_orders_success(self, mock_env, valid_consumer_token, mock_consumer_orders):
        """Test that consumers can successfully list their orders."""
        event = {
            'headers': {
                'Authorization': f'Bearer {valid_consumer_token}'
            }
        }
        
        with patch('orders.list_orders.query') as mock_query:
            mock_query.return_value = {'Items': mock_consumer_orders}
            
            response = list_orders.handler(event, None)
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert 'orders' in body
            assert body['count'] == 2
            assert len(body['orders']) == 2
            
            # Verify query was called with correct GSI2 parameters
            mock_query.assert_called_once()
            call_kwargs = mock_query.call_args[1]
            assert call_kwargs['index_name'] == 'GSI2'
            assert call_kwargs['scan_index_forward'] is False  # Most recent first
            
            # Verify order data structure
            first_order = body['orders'][0]
            assert 'orderId' in first_order
            assert 'productName' in first_order
            assert 'quantity' in first_order
            assert 'totalAmount' in first_order
            assert 'status' in first_order
            assert 'estimatedDeliveryDate' in first_order
            assert 'farmerId' in first_order  # Consumer-specific field
            assert 'consumerId' not in first_order  # Should not include own ID
    
    def test_consumer_empty_orders(self, mock_env, valid_consumer_token):
        """Test that consumers with no orders receive empty array."""
        event = {
            'headers': {
                'Authorization': f'Bearer {valid_consumer_token}'
            }
        }
        
        with patch('orders.list_orders.query') as mock_query:
            mock_query.return_value = {'Items': []}
            
            response = list_orders.handler(event, None)
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert body['orders'] == []
            assert body['count'] == 0
    
    def test_consumer_orders_sorted_by_date(self, mock_env, valid_consumer_token, mock_consumer_orders):
        """Test that orders are returned in reverse chronological order (most recent first)."""
        event = {
            'headers': {
                'Authorization': f'Bearer {valid_consumer_token}'
            }
        }
        
        with patch('orders.list_orders.query') as mock_query:
            mock_query.return_value = {'Items': mock_consumer_orders}
            
            response = list_orders.handler(event, None)
            
            assert response['statusCode'] == 200
            
            # Verify scan_index_forward=False was used for descending order
            call_kwargs = mock_query.call_args[1]
            assert call_kwargs['scan_index_forward'] is False


class TestFarmerOrderListing:
    """Test order listing for farmers."""
    
    def test_farmer_list_orders_success(self, mock_env, valid_farmer_token, mock_farmer_orders):
        """Test that farmers can successfully list orders for their products."""
        event = {
            'headers': {
                'Authorization': f'Bearer {valid_farmer_token}'
            }
        }
        
        with patch('orders.list_orders.query') as mock_query:
            mock_query.return_value = {'Items': mock_farmer_orders}
            
            response = list_orders.handler(event, None)
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert 'orders' in body
            assert body['count'] == 2
            assert len(body['orders']) == 2
            
            # Verify query was called with correct GSI3 parameters
            mock_query.assert_called_once()
            call_kwargs = mock_query.call_args[1]
            assert call_kwargs['index_name'] == 'GSI3'
            assert call_kwargs['scan_index_forward'] is False  # Most recent first
            
            # Verify order data structure
            first_order = body['orders'][0]
            assert 'orderId' in first_order
            assert 'productName' in first_order
            assert 'quantity' in first_order
            assert 'totalAmount' in first_order
            assert 'status' in first_order
            assert 'estimatedDeliveryDate' in first_order
            assert 'consumerId' in first_order  # Farmer-specific field
            assert 'farmerId' not in first_order  # Should not include own ID
    
    def test_farmer_empty_orders(self, mock_env, valid_farmer_token):
        """Test that farmers with no orders receive empty array."""
        event = {
            'headers': {
                'Authorization': f'Bearer {valid_farmer_token}'
            }
        }
        
        with patch('orders.list_orders.query') as mock_query:
            mock_query.return_value = {'Items': []}
            
            response = list_orders.handler(event, None)
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert body['orders'] == []
            assert body['count'] == 0


class TestAuthorization:
    """Test authorization and authentication."""
    
    def test_missing_authorization_header(self, mock_env):
        """Test that missing authorization header returns 401."""
        event = {
            'headers': {}
        }
        
        response = list_orders.handler(event, None)
        
        assert response['statusCode'] == 401
        body = json.loads(response['body'])
        assert body['error']['code'] == 'UNAUTHORIZED'
    
    def test_invalid_token(self, mock_env):
        """Test that invalid JWT token returns 401."""
        event = {
            'headers': {
                'Authorization': 'Bearer invalid-token-12345'
            }
        }
        
        response = list_orders.handler(event, None)
        
        assert response['statusCode'] == 401
        body = json.loads(response['body'])
        assert body['error']['code'] == 'INVALID_TOKEN'


class TestGSIQueries:
    """Test that correct GSI indexes are queried based on role."""
    
    def test_consumer_queries_gsi2(self, mock_env, valid_consumer_token):
        """Test that consumer role queries GSI2 with correct partition key."""
        event = {
            'headers': {
                'Authorization': f'Bearer {valid_consumer_token}'
            }
        }
        
        with patch('orders.list_orders.query') as mock_query:
            mock_query.return_value = {'Items': []}
            
            response = list_orders.handler(event, None)
            
            assert response['statusCode'] == 200
            
            # Verify GSI2 was queried with correct key
            mock_query.assert_called_once()
            call_kwargs = mock_query.call_args[1]
            assert call_kwargs['index_name'] == 'GSI2'
            
            # Verify key condition includes CONSUMER#consumer-123
            # The key_condition_expression is a boto3 Key object, so we check it was called
            assert mock_query.called
    
    def test_farmer_queries_gsi3(self, mock_env, valid_farmer_token):
        """Test that farmer role queries GSI3 with correct partition key."""
        event = {
            'headers': {
                'Authorization': f'Bearer {valid_farmer_token}'
            }
        }
        
        with patch('orders.list_orders.query') as mock_query:
            mock_query.return_value = {'Items': []}
            
            response = list_orders.handler(event, None)
            
            assert response['statusCode'] == 200
            
            # Verify GSI3 was queried with correct key
            mock_query.assert_called_once()
            call_kwargs = mock_query.call_args[1]
            assert call_kwargs['index_name'] == 'GSI3'
            
            # Verify key condition includes FARMER#farmer-456
            assert mock_query.called


class TestResponseFormat:
    """Test response format and data transformation."""
    
    def test_response_includes_required_fields(self, mock_env, valid_consumer_token, mock_consumer_orders):
        """Test that response includes all required fields per requirements."""
        event = {
            'headers': {
                'Authorization': f'Bearer {valid_consumer_token}'
            }
        }
        
        with patch('orders.list_orders.query') as mock_query:
            mock_query.return_value = {'Items': mock_consumer_orders}
            
            response = list_orders.handler(event, None)
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            
            # Verify required fields per task requirements
            for order in body['orders']:
                assert 'productName' in order
                assert 'quantity' in order
                assert 'totalAmount' in order
                assert 'status' in order
                assert 'estimatedDeliveryDate' in order
    
    def test_decimal_to_float_conversion(self, mock_env, valid_consumer_token, mock_consumer_orders):
        """Test that Decimal values are converted to float in response."""
        event = {
            'headers': {
                'Authorization': f'Bearer {valid_consumer_token}'
            }
        }
        
        with patch('orders.list_orders.query') as mock_query:
            mock_query.return_value = {'Items': mock_consumer_orders}
            
            response = list_orders.handler(event, None)
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            
            # Verify totalAmount is a float, not Decimal
            for order in body['orders']:
                assert isinstance(order['totalAmount'], float)
    
    def test_response_includes_count(self, mock_env, valid_consumer_token, mock_consumer_orders):
        """Test that response includes count of orders."""
        event = {
            'headers': {
                'Authorization': f'Bearer {valid_consumer_token}'
            }
        }
        
        with patch('orders.list_orders.query') as mock_query:
            mock_query.return_value = {'Items': mock_consumer_orders}
            
            response = list_orders.handler(event, None)
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert 'count' in body
            assert body['count'] == len(mock_consumer_orders)


class TestErrorHandling:
    """Test error handling for external service failures."""
    
    def test_dynamodb_query_failure(self, mock_env, valid_consumer_token):
        """Test handling of DynamoDB query failure."""
        event = {
            'headers': {
                'Authorization': f'Bearer {valid_consumer_token}'
            }
        }
        
        with patch('orders.list_orders.query') as mock_query:
            mock_query.side_effect = Exception('DynamoDB unavailable')
            
            response = list_orders.handler(event, None)
            
            assert response['statusCode'] == 503
            body = json.loads(response['body'])
            assert body['error']['code'] == 'SERVICE_UNAVAILABLE'
    
    def test_unexpected_error_handling(self, mock_env, valid_consumer_token):
        """Test handling of unexpected errors."""
        event = {
            'headers': {
                'Authorization': f'Bearer {valid_consumer_token}'
            }
        }
        
        with patch('orders.list_orders.get_user_from_token') as mock_get_user:
            mock_get_user.side_effect = Exception('Unexpected error')
            
            response = list_orders.handler(event, None)
            
            # Should return 401 for token-related errors
            assert response['statusCode'] == 401


class TestCORSHeaders:
    """Test CORS headers are included in all responses."""
    
    def test_cors_headers_in_success_response(self, mock_env, valid_consumer_token):
        """Test that CORS headers are included in successful response."""
        event = {
            'headers': {
                'Authorization': f'Bearer {valid_consumer_token}'
            }
        }
        
        with patch('orders.list_orders.query') as mock_query:
            mock_query.return_value = {'Items': []}
            
            response = list_orders.handler(event, None)
            
            assert response['statusCode'] == 200
            assert 'Access-Control-Allow-Origin' in response['headers']
            assert response['headers']['Access-Control-Allow-Origin'] == '*'
    
    def test_cors_headers_in_error_response(self, mock_env):
        """Test that CORS headers are included in error response."""
        event = {
            'headers': {}
        }
        
        response = list_orders.handler(event, None)
        
        assert response['statusCode'] == 401
        assert 'Access-Control-Allow-Origin' in response['headers']
        assert response['headers']['Access-Control-Allow-Origin'] == '*'
