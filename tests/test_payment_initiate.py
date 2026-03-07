"""
Unit tests for payment initiation endpoint.
Tests POST /payments/initiate for creating payment sessions.
"""
import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
import sys
import os

# Add backend paths to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend', 'shared'))

# Import after path setup
from shared.constants import UserRole, OrderStatus, PaymentStatus, PaymentGateway
from backend.shared.exceptions import ServiceUnavailableError
from shared.auth import generate_jwt_token

# Import the handler module
from payments import initiate_payment


@pytest.fixture
def mock_env(monkeypatch):
    """Set up mock environment variables."""
    monkeypatch.setenv('DYNAMODB_TABLE_NAME', 'RootTrustData-test')
    monkeypatch.setenv('JWT_SECRET_KEY', 'test-secret-key-12345')
    monkeypatch.setenv('USE_MOCK_PAYMENT', 'true')
    monkeypatch.setenv('PAYMENT_SUCCESS_URL', 'https://test.roottrust.com/payment/success')
    monkeypatch.setenv('PAYMENT_CANCEL_URL', 'https://test.roottrust.com/payment/cancel')


@pytest.fixture
def valid_consumer_token():
    """Generate a valid consumer JWT token."""
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
    token_data = generate_jwt_token(
        user_id='farmer-456',
        email='farmer@test.com',
        role=UserRole.FARMER.value,
        secret_key='test-secret-key-12345'
    )
    return token_data['token']


@pytest.fixture
def mock_pending_order():
    """Mock order data in pending status."""
    return {
        'PK': 'ORDER#order-123',
        'SK': 'METADATA',
        'orderId': 'order-123',
        'consumerId': 'consumer-123',
        'farmerId': 'farmer-456',
        'productId': 'product-789',
        'productName': 'Organic Tomatoes',
        'quantity': 5,
        'unitPrice': 50.0,
        'totalAmount': 250.0,
        'status': OrderStatus.PENDING.value,
        'paymentStatus': PaymentStatus.PENDING.value,
        'createdAt': datetime.utcnow().isoformat(),
        'updatedAt': datetime.utcnow().isoformat()
    }


class TestPaymentInitiateEndpoint:
    """Test suite for payment initiation endpoint."""
    
    def test_initiate_payment_success(self, mock_env, valid_consumer_token, mock_pending_order):
        """Test successful payment initiation with valid order."""
        with patch('payments.initiate_payment.get_item') as mock_get_item, \
             patch('payments.initiate_payment.put_item') as mock_put_item, \
             patch('payments.initiate_payment.update_item') as mock_update_item:
            
            # Mock order retrieval
            mock_get_item.return_value = mock_pending_order
            
            # Create event
            event = {
                'headers': {
                    'Authorization': f'Bearer {valid_consumer_token}'
                },
                'body': json.dumps({
                    'orderId': 'order-123'
                })
            }
            
            # Call handler
            response = initiate_payment.handler(event, None)
            
            # Verify response
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert 'paymentUrl' in body
            assert 'sessionId' in body
            assert body['orderId'] == 'order-123'
            assert body['amount'] == 250.0
            assert body['currency'] == 'INR'
            assert 'message' in body
            
            # Verify payment URL format
            assert body['paymentUrl'].startswith('https://checkout.stripe.com/pay/')
            assert body['sessionId'].startswith('cs_test_')
            
            # Verify database calls
            mock_get_item.assert_called_once()
            mock_put_item.assert_called_once()  # Transaction stored
            mock_update_item.assert_called_once()  # Order updated with transaction ID
    
    def test_initiate_payment_missing_authorization(self, mock_env):
        """Test payment initiation without authorization header."""
        event = {
            'headers': {},
            'body': json.dumps({'orderId': 'order-123'})
        }
        
        response = initiate_payment.handler(event, None)
        
        assert response['statusCode'] == 401
        body = json.loads(response['body'])
        assert body['error']['code'] == 'UNAUTHORIZED'
        assert 'Authorization header is required' in body['error']['message']
    
    def test_initiate_payment_invalid_token(self, mock_env):
        """Test payment initiation with invalid JWT token."""
        event = {
            'headers': {
                'Authorization': 'Bearer invalid-token-xyz'
            },
            'body': json.dumps({'orderId': 'order-123'})
        }
        
        response = initiate_payment.handler(event, None)
        
        assert response['statusCode'] == 401
        body = json.loads(response['body'])
        assert body['error']['code'] == 'INVALID_TOKEN'
    
    def test_initiate_payment_farmer_role_forbidden(self, mock_env, valid_farmer_token):
        """Test payment initiation by farmer (should be forbidden)."""
        event = {
            'headers': {
                'Authorization': f'Bearer {valid_farmer_token}'
            },
            'body': json.dumps({'orderId': 'order-123'})
        }
        
        response = initiate_payment.handler(event, None)
        
        assert response['statusCode'] == 403
        body = json.loads(response['body'])
        assert body['error']['code'] == 'FORBIDDEN'
        assert 'Only consumers can initiate payments' in body['error']['message']
    
    def test_initiate_payment_invalid_json(self, mock_env, valid_consumer_token):
        """Test payment initiation with invalid JSON body."""
        event = {
            'headers': {
                'Authorization': f'Bearer {valid_consumer_token}'
            },
            'body': 'invalid-json{'
        }
        
        response = initiate_payment.handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error']['code'] == 'INVALID_JSON'
    
    def test_initiate_payment_missing_order_id(self, mock_env, valid_consumer_token):
        """Test payment initiation without orderId."""
        event = {
            'headers': {
                'Authorization': f'Bearer {valid_consumer_token}'
            },
            'body': json.dumps({})
        }
        
        response = initiate_payment.handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error']['code'] == 'VALIDATION_ERROR'
        assert 'orderId is required' in body['error']['message']
    
    def test_initiate_payment_order_not_found(self, mock_env, valid_consumer_token):
        """Test payment initiation for non-existent order."""
        with patch('payments.initiate_payment.get_item') as mock_get_item:
            mock_get_item.return_value = None
            
            event = {
                'headers': {
                    'Authorization': f'Bearer {valid_consumer_token}'
                },
                'body': json.dumps({'orderId': 'nonexistent-order'})
            }
            
            response = initiate_payment.handler(event, None)
            
            assert response['statusCode'] == 404
            body = json.loads(response['body'])
            assert body['error']['code'] == 'RESOURCE_NOT_FOUND'
            assert 'not found' in body['error']['message']
    
    def test_initiate_payment_wrong_consumer(self, mock_env, valid_consumer_token, mock_pending_order):
        """Test payment initiation by consumer who doesn't own the order."""
        with patch('payments.initiate_payment.get_item') as mock_get_item:
            # Order belongs to different consumer
            order = mock_pending_order.copy()
            order['consumerId'] = 'different-consumer-999'
            mock_get_item.return_value = order
            
            event = {
                'headers': {
                    'Authorization': f'Bearer {valid_consumer_token}'
                },
                'body': json.dumps({'orderId': 'order-123'})
            }
            
            response = initiate_payment.handler(event, None)
            
            assert response['statusCode'] == 403
            body = json.loads(response['body'])
            assert body['error']['code'] == 'FORBIDDEN'
            assert 'do not have permission' in body['error']['message']
    
    def test_initiate_payment_order_not_pending(self, mock_env, valid_consumer_token, mock_pending_order):
        """Test payment initiation for order not in pending status."""
        with patch('payments.initiate_payment.get_item') as mock_get_item:
            # Order is already confirmed
            order = mock_pending_order.copy()
            order['status'] = OrderStatus.CONFIRMED.value
            mock_get_item.return_value = order
            
            event = {
                'headers': {
                    'Authorization': f'Bearer {valid_consumer_token}'
                },
                'body': json.dumps({'orderId': 'order-123'})
            }
            
            response = initiate_payment.handler(event, None)
            
            assert response['statusCode'] == 409
            body = json.loads(response['body'])
            assert body['error']['code'] == 'CONFLICT_ERROR'
            assert 'Cannot initiate payment' in body['error']['message']
    
    def test_initiate_payment_already_completed(self, mock_env, valid_consumer_token, mock_pending_order):
        """Test payment initiation for order with completed payment."""
        with patch('payments.initiate_payment.get_item') as mock_get_item:
            # Payment already completed
            order = mock_pending_order.copy()
            order['paymentStatus'] = PaymentStatus.COMPLETED.value
            mock_get_item.return_value = order
            
            event = {
                'headers': {
                    'Authorization': f'Bearer {valid_consumer_token}'
                },
                'body': json.dumps({'orderId': 'order-123'})
            }
            
            response = initiate_payment.handler(event, None)
            
            assert response['statusCode'] == 409
            body = json.loads(response['body'])
            assert body['error']['code'] == 'CONFLICT_ERROR'
            assert 'already been completed' in body['error']['message']
    
    def test_initiate_payment_invalid_amount(self, mock_env, valid_consumer_token, mock_pending_order):
        """Test payment initiation with invalid order amount."""
        with patch('payments.initiate_payment.get_item') as mock_get_item:
            # Order has zero or negative amount
            order = mock_pending_order.copy()
            order['totalAmount'] = 0
            mock_get_item.return_value = order
            
            event = {
                'headers': {
                    'Authorization': f'Bearer {valid_consumer_token}'
                },
                'body': json.dumps({'orderId': 'order-123'})
            }
            
            response = initiate_payment.handler(event, None)
            
            assert response['statusCode'] == 400
            body = json.loads(response['body'])
            assert body['error']['code'] == 'VALIDATION_ERROR'
            assert 'invalid' in body['error']['message'].lower()
    
    def test_initiate_payment_database_error(self, mock_env, valid_consumer_token):
        """Test payment initiation with database error."""
        with patch('payments.initiate_payment.get_item') as mock_get_item:
            mock_get_item.side_effect = Exception('DynamoDB connection error')
            
            event = {
                'headers': {
                    'Authorization': f'Bearer {valid_consumer_token}'
                },
                'body': json.dumps({'orderId': 'order-123'})
            }
            
            response = initiate_payment.handler(event, None)
            
            assert response['statusCode'] == 503
            body = json.loads(response['body'])
            assert body['error']['code'] == 'SERVICE_UNAVAILABLE'
    
    def test_initiate_payment_transaction_stored(self, mock_env, valid_consumer_token, mock_pending_order):
        """Test that transaction details are stored in DynamoDB."""
        with patch('payments.initiate_payment.get_item') as mock_get_item, \
             patch('payments.initiate_payment.put_item') as mock_put_item, \
             patch('payments.initiate_payment.update_item') as mock_update_item:
            
            mock_get_item.return_value = mock_pending_order
            
            event = {
                'headers': {
                    'Authorization': f'Bearer {valid_consumer_token}'
                },
                'body': json.dumps({'orderId': 'order-123'})
            }
            
            response = initiate_payment.handler(event, None)
            
            assert response['statusCode'] == 200
            
            # Verify transaction was stored
            mock_put_item.assert_called_once()
            transaction_data = mock_put_item.call_args[0][0]
            
            assert transaction_data['EntityType'] == 'Transaction'
            assert transaction_data['orderId'] == 'order-123'
            assert transaction_data['amount'] == 250.0
            assert transaction_data['currency'] == 'INR'
            assert transaction_data['paymentGateway'] == PaymentGateway.STRIPE.value
            assert transaction_data['status'] == PaymentStatus.PENDING.value
            assert 'sessionId' in transaction_data['gatewayResponse']
            assert 'paymentUrl' in transaction_data['gatewayResponse']
    
    def test_initiate_payment_order_updated_with_transaction_id(self, mock_env, valid_consumer_token, mock_pending_order):
        """Test that order is updated with transaction ID."""
        with patch('payments.initiate_payment.get_item') as mock_get_item, \
             patch('payments.initiate_payment.put_item') as mock_put_item, \
             patch('payments.initiate_payment.update_item') as mock_update_item:
            
            mock_get_item.return_value = mock_pending_order
            
            event = {
                'headers': {
                    'Authorization': f'Bearer {valid_consumer_token}'
                },
                'body': json.dumps({'orderId': 'order-123'})
            }
            
            response = initiate_payment.handler(event, None)
            
            assert response['statusCode'] == 200
            
            # Verify order was updated
            mock_update_item.assert_called_once()
            update_call = mock_update_item.call_args
            
            assert update_call[1]['pk'] == 'ORDER#order-123'
            assert update_call[1]['sk'] == 'METADATA'
            assert 'transactionId' in update_call[1]['update_expression']


class TestCreateStripePaymentSession:
    """Test suite for Stripe payment session creation."""
    
    def test_create_mock_payment_session(self, mock_env):
        """Test mock payment session creation."""
        result = initiate_payment.create_stripe_payment_session(
            order_id='order-123',
            amount=250.0,
            currency='INR'
        )
        
        assert 'sessionId' in result
        assert 'paymentUrl' in result
        assert 'gateway' in result
        assert result['gateway'] == PaymentGateway.STRIPE.value
        assert result['sessionId'].startswith('cs_test_')
        assert 'checkout.stripe.com' in result['paymentUrl']
    
    def test_create_payment_session_different_amounts(self, mock_env):
        """Test payment session creation with different amounts."""
        amounts = [10.0, 100.0, 1000.0, 9999.99]
        
        for amount in amounts:
            result = initiate_payment.create_stripe_payment_session(
                order_id=f'order-{amount}',
                amount=amount,
                currency='INR'
            )
            
            assert result['sessionId'].startswith('cs_test_')
            assert result['paymentUrl'].startswith('https://checkout.stripe.com/pay/')
    
    def test_create_payment_session_unique_session_ids(self, mock_env):
        """Test that each payment session gets a unique session ID."""
        session_ids = set()
        
        for i in range(10):
            result = initiate_payment.create_stripe_payment_session(
                order_id=f'order-{i}',
                amount=100.0,
                currency='INR'
            )
            session_ids.add(result['sessionId'])
        
        # All session IDs should be unique
        assert len(session_ids) == 10


class TestPaymentInitiateEdgeCases:
    """Test edge cases and error scenarios."""
    
    def test_initiate_payment_with_lowercase_authorization_header(self, mock_env, valid_consumer_token, mock_pending_order):
        """Test payment initiation with lowercase 'authorization' header."""
        with patch('payments.initiate_payment.get_item') as mock_get_item, \
             patch('payments.initiate_payment.put_item') as mock_put_item, \
             patch('payments.initiate_payment.update_item') as mock_update_item:
            
            mock_get_item.return_value = mock_pending_order
            
            event = {
                'headers': {
                    'authorization': f'Bearer {valid_consumer_token}'  # lowercase
                },
                'body': json.dumps({'orderId': 'order-123'})
            }
            
            response = initiate_payment.handler(event, None)
            
            assert response['statusCode'] == 200
    
    def test_initiate_payment_cors_headers(self, mock_env, valid_consumer_token, mock_pending_order):
        """Test that CORS headers are present in response."""
        with patch('payments.initiate_payment.get_item') as mock_get_item, \
             patch('payments.initiate_payment.put_item') as mock_put_item, \
             patch('payments.initiate_payment.update_item') as mock_update_item:
            
            mock_get_item.return_value = mock_pending_order
            
            event = {
                'headers': {
                    'Authorization': f'Bearer {valid_consumer_token}'
                },
                'body': json.dumps({'orderId': 'order-123'})
            }
            
            response = initiate_payment.handler(event, None)
            
            assert 'Access-Control-Allow-Origin' in response['headers']
            assert response['headers']['Access-Control-Allow-Origin'] == '*'
            assert response['headers']['Content-Type'] == 'application/json'
    
    def test_initiate_payment_unexpected_exception(self, mock_env, valid_consumer_token):
        """Test handling of unexpected exceptions."""
        with patch('payments.initiate_payment.get_item') as mock_get_item:
            # Simulate an unexpected exception after auth
            mock_get_item.side_effect = RuntimeError('Unexpected database error')
            
            event = {
                'headers': {
                    'Authorization': f'Bearer {valid_consumer_token}'
                },
                'body': json.dumps({'orderId': 'order-123'})
            }
            
            response = initiate_payment.handler(event, None)
            
            # Should return 503 for database errors
            assert response['statusCode'] == 503
            body = json.loads(response['body'])
            assert body['error']['code'] == 'SERVICE_UNAVAILABLE'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
