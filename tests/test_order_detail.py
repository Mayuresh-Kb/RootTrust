"""
Unit tests for order detail endpoint.
Tests order detail retrieval with proper authorization and ownership verification.
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
from orders import get_order_detail


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
def other_consumer_token():
    """Generate a token for a different consumer."""
    from shared.auth import generate_jwt_token
    token_data = generate_jwt_token(
        user_id='consumer-999',
        email='other@test.com',
        role=UserRole.CONSUMER.value,
        secret_key='test-secret-key-12345'
    )
    return token_data['token']


@pytest.fixture
def mock_order():
    """Mock order data."""
    return {
        'PK': 'ORDER#order-123',
        'SK': 'METADATA',
        'orderId': 'order-123',
        'consumerId': 'consumer-123',
        'farmerId': 'farmer-456',
        'productId': 'product-789',
        'productName': 'Organic Tomatoes',
        'quantity': 2,
        'unitPrice': Decimal('50.00'),
        'totalAmount': Decimal('100.00'),
        'status': OrderStatus.CONFIRMED.value,
        'paymentStatus': PaymentStatus.COMPLETED.value,
        'transactionId': 'txn-abc123',
        'deliveryAddress': {
            'street': '123 Main St',
            'city': 'Mumbai',
            'state': 'Maharashtra',
            'pincode': '400001'
        },
        'estimatedDeliveryDate': (datetime.utcnow() + timedelta(days=7)).isoformat(),
        'actualDeliveryDate': None,
        'referralCode': 'REF123',
        'createdAt': datetime.utcnow().isoformat(),
        'updatedAt': datetime.utcnow().isoformat(),
        'GSI2PK': 'CONSUMER#consumer-123',
        'GSI2SK': 'ORDER#' + datetime.utcnow().isoformat(),
        'GSI3PK': 'FARMER#farmer-456',
        'GSI3SK': 'ORDER#' + datetime.utcnow().isoformat()
    }


class TestOrderDetailRetrieval:
    """Test order detail retrieval with valid authorization."""
    
    def test_consumer_get_own_order_success(self, mock_env, valid_consumer_token, mock_order):
        """Test that consumers can successfully retrieve their own order details."""
        event = {
            'headers': {
                'Authorization': f'Bearer {valid_consumer_token}'
            },
            'pathParameters': {
                'orderId': 'order-123'
            }
        }
        
        with patch('orders.get_order_detail.get_item') as mock_get_item:
            mock_get_item.return_value = mock_order
            
            response = get_order_detail.handler(event, None)
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert 'order' in body
            
            order = body['order']
            assert order['orderId'] == 'order-123'
            assert order['consumerId'] == 'consumer-123'
            assert order['farmerId'] == 'farmer-456'
            assert order['productName'] == 'Organic Tomatoes'
            assert order['quantity'] == 2
            assert order['totalAmount'] == 100.0
            assert order['status'] == OrderStatus.CONFIRMED.value
            
            # Verify get_item was called with correct keys
            mock_get_item.assert_called_once_with('ORDER#order-123', 'METADATA')
    
    def test_farmer_get_own_order_success(self, mock_env, valid_farmer_token, mock_order):
        """Test that farmers can successfully retrieve orders for their products."""
        event = {
            'headers': {
                'Authorization': f'Bearer {valid_farmer_token}'
            },
            'pathParameters': {
                'orderId': 'order-123'
            }
        }
        
        with patch('orders.get_order_detail.get_item') as mock_get_item:
            mock_get_item.return_value = mock_order
            
            response = get_order_detail.handler(event, None)
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert 'order' in body
            
            order = body['order']
            assert order['orderId'] == 'order-123'
            assert order['farmerId'] == 'farmer-456'
    
    def test_order_detail_includes_all_fields(self, mock_env, valid_consumer_token, mock_order):
        """Test that order detail response includes all required fields."""
        event = {
            'headers': {
                'Authorization': f'Bearer {valid_consumer_token}'
            },
            'pathParameters': {
                'orderId': 'order-123'
            }
        }
        
        with patch('orders.get_order_detail.get_item') as mock_get_item:
            mock_get_item.return_value = mock_order
            
            response = get_order_detail.handler(event, None)
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            order = body['order']
            
            # Verify all required fields are present
            required_fields = [
                'orderId', 'consumerId', 'farmerId', 'productId', 'productName',
                'quantity', 'unitPrice', 'totalAmount', 'status', 'paymentStatus',
                'transactionId', 'deliveryAddress', 'estimatedDeliveryDate',
                'actualDeliveryDate', 'referralCode', 'createdAt', 'updatedAt'
            ]
            
            for field in required_fields:
                assert field in order, f"Missing required field: {field}"
    
    def test_delivery_address_structure(self, mock_env, valid_consumer_token, mock_order):
        """Test that delivery address is properly included in response."""
        event = {
            'headers': {
                'Authorization': f'Bearer {valid_consumer_token}'
            },
            'pathParameters': {
                'orderId': 'order-123'
            }
        }
        
        with patch('orders.get_order_detail.get_item') as mock_get_item:
            mock_get_item.return_value = mock_order
            
            response = get_order_detail.handler(event, None)
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            order = body['order']
            
            # Verify delivery address structure
            address = order['deliveryAddress']
            assert address['street'] == '123 Main St'
            assert address['city'] == 'Mumbai'
            assert address['state'] == 'Maharashtra'
            assert address['pincode'] == '400001'
    
    def test_decimal_to_float_conversion(self, mock_env, valid_consumer_token, mock_order):
        """Test that Decimal values are converted to float in response."""
        event = {
            'headers': {
                'Authorization': f'Bearer {valid_consumer_token}'
            },
            'pathParameters': {
                'orderId': 'order-123'
            }
        }
        
        with patch('orders.get_order_detail.get_item') as mock_get_item:
            mock_get_item.return_value = mock_order
            
            response = get_order_detail.handler(event, None)
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            order = body['order']
            
            # Verify numeric values are floats, not Decimals
            assert isinstance(order['unitPrice'], float)
            assert isinstance(order['totalAmount'], float)


class TestAuthorization:
    """Test authorization and ownership verification."""
    
    def test_missing_authorization_header(self, mock_env):
        """Test that missing authorization header returns 401."""
        event = {
            'headers': {},
            'pathParameters': {
                'orderId': 'order-123'
            }
        }
        
        response = get_order_detail.handler(event, None)
        
        assert response['statusCode'] == 401
        body = json.loads(response['body'])
        assert body['error']['code'] == 'UNAUTHORIZED'
    
    def test_invalid_token(self, mock_env):
        """Test that invalid JWT token returns 401."""
        event = {
            'headers': {
                'Authorization': 'Bearer invalid-token-12345'
            },
            'pathParameters': {
                'orderId': 'order-123'
            }
        }
        
        response = get_order_detail.handler(event, None)
        
        assert response['statusCode'] == 401
        body = json.loads(response['body'])
        assert body['error']['code'] == 'INVALID_TOKEN'
    
    def test_consumer_cannot_view_other_consumer_order(self, mock_env, other_consumer_token, mock_order):
        """Test that consumers cannot view orders they don't own."""
        event = {
            'headers': {
                'Authorization': f'Bearer {other_consumer_token}'
            },
            'pathParameters': {
                'orderId': 'order-123'
            }
        }
        
        with patch('orders.get_order_detail.get_item') as mock_get_item:
            mock_get_item.return_value = mock_order
            
            response = get_order_detail.handler(event, None)
            
            assert response['statusCode'] == 403
            body = json.loads(response['body'])
            assert body['error']['code'] == 'FORBIDDEN'
            assert 'permission' in body['error']['message'].lower()
    
    def test_farmer_cannot_view_other_farmer_order(self, mock_env, mock_order):
        """Test that farmers cannot view orders for other farmers' products."""
        from shared.auth import generate_jwt_token
        
        # Create token for a different farmer
        other_farmer_token_data = generate_jwt_token(
            user_id='farmer-999',
            email='otherfarmer@test.com',
            role=UserRole.FARMER.value,
            secret_key='test-secret-key-12345'
        )
        other_farmer_token = other_farmer_token_data['token']
        
        event = {
            'headers': {
                'Authorization': f'Bearer {other_farmer_token}'
            },
            'pathParameters': {
                'orderId': 'order-123'
            }
        }
        
        with patch('orders.get_order_detail.get_item') as mock_get_item:
            mock_get_item.return_value = mock_order
            
            response = get_order_detail.handler(event, None)
            
            assert response['statusCode'] == 403
            body = json.loads(response['body'])
            assert body['error']['code'] == 'FORBIDDEN'


class TestPathParameters:
    """Test path parameter validation."""
    
    def test_missing_order_id(self, mock_env, valid_consumer_token):
        """Test that missing orderId in path parameters returns 400."""
        event = {
            'headers': {
                'Authorization': f'Bearer {valid_consumer_token}'
            },
            'pathParameters': {}
        }
        
        response = get_order_detail.handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error']['code'] == 'BAD_REQUEST'
        assert 'orderId' in body['error']['message']
    
    def test_none_path_parameters(self, mock_env, valid_consumer_token):
        """Test handling when pathParameters is None."""
        event = {
            'headers': {
                'Authorization': f'Bearer {valid_consumer_token}'
            },
            'pathParameters': None
        }
        
        response = get_order_detail.handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error']['code'] == 'BAD_REQUEST'


class TestOrderNotFound:
    """Test handling of non-existent orders."""
    
    def test_order_not_found(self, mock_env, valid_consumer_token):
        """Test that querying non-existent order returns 404."""
        event = {
            'headers': {
                'Authorization': f'Bearer {valid_consumer_token}'
            },
            'pathParameters': {
                'orderId': 'non-existent-order'
            }
        }
        
        with patch('orders.get_order_detail.get_item') as mock_get_item:
            mock_get_item.return_value = None
            
            response = get_order_detail.handler(event, None)
            
            assert response['statusCode'] == 404
            body = json.loads(response['body'])
            assert body['error']['code'] == 'RESOURCE_NOT_FOUND'
            assert 'non-existent-order' in body['error']['message']


class TestDynamoDBKeys:
    """Test that correct DynamoDB keys are used for queries."""
    
    def test_correct_pk_sk_used(self, mock_env, valid_consumer_token, mock_order):
        """Test that correct PK and SK are used to query order."""
        event = {
            'headers': {
                'Authorization': f'Bearer {valid_consumer_token}'
            },
            'pathParameters': {
                'orderId': 'order-123'
            }
        }
        
        with patch('orders.get_order_detail.get_item') as mock_get_item:
            mock_get_item.return_value = mock_order
            
            response = get_order_detail.handler(event, None)
            
            assert response['statusCode'] == 200
            
            # Verify get_item was called with correct PK and SK
            mock_get_item.assert_called_once_with('ORDER#order-123', 'METADATA')


class TestErrorHandling:
    """Test error handling for external service failures."""
    
    def test_dynamodb_query_failure(self, mock_env, valid_consumer_token):
        """Test handling of DynamoDB query failure."""
        event = {
            'headers': {
                'Authorization': f'Bearer {valid_consumer_token}'
            },
            'pathParameters': {
                'orderId': 'order-123'
            }
        }
        
        with patch('orders.get_order_detail.get_item') as mock_get_item:
            mock_get_item.side_effect = Exception('DynamoDB unavailable')
            
            response = get_order_detail.handler(event, None)
            
            assert response['statusCode'] == 503
            body = json.loads(response['body'])
            assert body['error']['code'] == 'SERVICE_UNAVAILABLE'
    
    def test_unexpected_error_handling(self, mock_env, valid_consumer_token):
        """Test handling of unexpected errors."""
        event = {
            'headers': {
                'Authorization': f'Bearer {valid_consumer_token}'
            },
            'pathParameters': {
                'orderId': 'order-123'
            }
        }
        
        with patch('orders.get_order_detail.get_user_from_token') as mock_get_user:
            mock_get_user.side_effect = Exception('Unexpected error')
            
            response = get_order_detail.handler(event, None)
            
            # Should return 401 for token-related errors
            assert response['statusCode'] == 401


class TestCORSHeaders:
    """Test CORS headers are included in all responses."""
    
    def test_cors_headers_in_success_response(self, mock_env, valid_consumer_token, mock_order):
        """Test that CORS headers are included in successful response."""
        event = {
            'headers': {
                'Authorization': f'Bearer {valid_consumer_token}'
            },
            'pathParameters': {
                'orderId': 'order-123'
            }
        }
        
        with patch('orders.get_order_detail.get_item') as mock_get_item:
            mock_get_item.return_value = mock_order
            
            response = get_order_detail.handler(event, None)
            
            assert response['statusCode'] == 200
            assert 'Access-Control-Allow-Origin' in response['headers']
            assert response['headers']['Access-Control-Allow-Origin'] == '*'
    
    def test_cors_headers_in_error_response(self, mock_env):
        """Test that CORS headers are included in error response."""
        event = {
            'headers': {},
            'pathParameters': {
                'orderId': 'order-123'
            }
        }
        
        response = get_order_detail.handler(event, None)
        
        assert response['statusCode'] == 401
        assert 'Access-Control-Allow-Origin' in response['headers']
        assert response['headers']['Access-Control-Allow-Origin'] == '*'


class TestOptionalFields:
    """Test handling of optional fields in order data."""
    
    def test_order_without_referral_code(self, mock_env, valid_consumer_token, mock_order):
        """Test order detail with no referral code."""
        order_without_referral = mock_order.copy()
        order_without_referral['referralCode'] = None
        
        event = {
            'headers': {
                'Authorization': f'Bearer {valid_consumer_token}'
            },
            'pathParameters': {
                'orderId': 'order-123'
            }
        }
        
        with patch('orders.get_order_detail.get_item') as mock_get_item:
            mock_get_item.return_value = order_without_referral
            
            response = get_order_detail.handler(event, None)
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert body['order']['referralCode'] is None
    
    def test_order_without_transaction_id(self, mock_env, valid_consumer_token, mock_order):
        """Test order detail with no transaction ID (pending payment)."""
        order_pending = mock_order.copy()
        order_pending['transactionId'] = None
        order_pending['paymentStatus'] = PaymentStatus.PENDING.value
        
        event = {
            'headers': {
                'Authorization': f'Bearer {valid_consumer_token}'
            },
            'pathParameters': {
                'orderId': 'order-123'
            }
        }
        
        with patch('orders.get_order_detail.get_item') as mock_get_item:
            mock_get_item.return_value = order_pending
            
            response = get_order_detail.handler(event, None)
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert body['order']['transactionId'] is None
            assert body['order']['paymentStatus'] == PaymentStatus.PENDING.value
    
    def test_order_without_actual_delivery_date(self, mock_env, valid_consumer_token, mock_order):
        """Test order detail with no actual delivery date (not yet delivered)."""
        event = {
            'headers': {
                'Authorization': f'Bearer {valid_consumer_token}'
            },
            'pathParameters': {
                'orderId': 'order-123'
            }
        }
        
        with patch('orders.get_order_detail.get_item') as mock_get_item:
            mock_get_item.return_value = mock_order
            
            response = get_order_detail.handler(event, None)
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert body['order']['actualDeliveryDate'] is None


class TestOrderStatuses:
    """Test order detail retrieval for various order statuses."""
    
    def test_pending_order(self, mock_env, valid_consumer_token, mock_order):
        """Test retrieving pending order details."""
        pending_order = mock_order.copy()
        pending_order['status'] = OrderStatus.PENDING.value
        pending_order['paymentStatus'] = PaymentStatus.PENDING.value
        
        event = {
            'headers': {
                'Authorization': f'Bearer {valid_consumer_token}'
            },
            'pathParameters': {
                'orderId': 'order-123'
            }
        }
        
        with patch('orders.get_order_detail.get_item') as mock_get_item:
            mock_get_item.return_value = pending_order
            
            response = get_order_detail.handler(event, None)
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert body['order']['status'] == OrderStatus.PENDING.value
    
    def test_delivered_order(self, mock_env, valid_consumer_token, mock_order):
        """Test retrieving delivered order details."""
        delivered_order = mock_order.copy()
        delivered_order['status'] = OrderStatus.DELIVERED.value
        delivered_order['actualDeliveryDate'] = datetime.utcnow().isoformat()
        
        event = {
            'headers': {
                'Authorization': f'Bearer {valid_consumer_token}'
            },
            'pathParameters': {
                'orderId': 'order-123'
            }
        }
        
        with patch('orders.get_order_detail.get_item') as mock_get_item:
            mock_get_item.return_value = delivered_order
            
            response = get_order_detail.handler(event, None)
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert body['order']['status'] == OrderStatus.DELIVERED.value
            assert body['order']['actualDeliveryDate'] is not None
    
    def test_cancelled_order(self, mock_env, valid_consumer_token, mock_order):
        """Test retrieving cancelled order details."""
        cancelled_order = mock_order.copy()
        cancelled_order['status'] = OrderStatus.CANCELLED.value
        
        event = {
            'headers': {
                'Authorization': f'Bearer {valid_consumer_token}'
            },
            'pathParameters': {
                'orderId': 'order-123'
            }
        }
        
        with patch('orders.get_order_detail.get_item') as mock_get_item:
            mock_get_item.return_value = cancelled_order
            
            response = get_order_detail.handler(event, None)
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert body['order']['status'] == OrderStatus.CANCELLED.value
