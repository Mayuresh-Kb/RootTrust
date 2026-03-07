"""
Unit tests for order creation endpoint.
Tests order creation, authorization, validation, inventory management, and race conditions.
"""
import json
import pytest
import uuid
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from decimal import Decimal

# Add backend paths to sys.path
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend', 'shared'))

# Import after path setup
from shared.constants import (
    UserRole, OrderStatus, PaymentStatus, VerificationStatus,
    DEFAULT_DELIVERY_DAYS
)

# Import the handler module
from orders import create_order


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
def valid_order_request():
    """Valid order creation request body."""
    return {
        'productId': 'product-789',
        'quantity': 2,
        'deliveryAddress': {
            'street': '123 Main St',
            'city': 'Mumbai',
            'state': 'Maharashtra',
            'pincode': '400001'
        },
        'referralCode': 'REF123'
    }


@pytest.fixture
def mock_approved_product():
    """Mock approved product with sufficient quantity."""
    return {
        'PK': 'PRODUCT#product-789',
        'SK': 'METADATA',
        'productId': 'product-789',
        'farmerId': 'farmer-456',
        'name': 'Organic Tomatoes',
        'price': Decimal('50.00'),
        'quantity': 10,
        'verificationStatus': VerificationStatus.APPROVED.value,
        'category': 'vegetables'
    }


class TestOrderCreation:
    """Test order creation with valid inputs."""
    
    def test_create_order_success(self, mock_env, valid_consumer_token, valid_order_request, mock_approved_product):
        """Test successful order creation with all valid inputs."""
        event = {
            'headers': {
                'Authorization': f'Bearer {valid_consumer_token}'
            },
            'body': json.dumps(valid_order_request)
        }
        
        with patch('orders.create_order.get_item') as mock_get_item, \
             patch('orders.create_order.put_item') as mock_put_item, \
             patch('orders.create_order.update_item') as mock_update_item:
            
            mock_get_item.return_value = mock_approved_product
            mock_put_item.return_value = {}
            mock_update_item.return_value = {}
            
            response = create_order.handler(event, None)
            
            assert response['statusCode'] == 201
            body = json.loads(response['body'])
            assert 'orderId' in body
            assert body['totalAmount'] == 100.0  # 50 * 2
            assert 'estimatedDeliveryDate' in body
            
            # Verify order was stored
            mock_put_item.assert_called_once()
            order_dict = mock_put_item.call_args[0][0]
            assert order_dict['consumerId'] == 'consumer-123'
            assert order_dict['farmerId'] == 'farmer-456'
            assert order_dict['productId'] == 'product-789'
            assert order_dict['quantity'] == 2
            assert order_dict['totalAmount'] == 100.0
            assert order_dict['status'] == OrderStatus.PENDING.value
            
            # Verify inventory was decremented
            mock_update_item.assert_called_once()
            update_call = mock_update_item.call_args
            assert update_call[1]['pk'] == 'PRODUCT#product-789'
            assert update_call[1]['expression_attribute_values'][':qty'] == 2
    
    def test_create_order_without_referral_code(self, mock_env, valid_consumer_token, mock_approved_product):
        """Test order creation without optional referral code."""
        order_request = {
            'productId': 'product-789',
            'quantity': 1,
            'deliveryAddress': {
                'street': '123 Main St',
                'city': 'Mumbai',
                'state': 'Maharashtra',
                'pincode': '400001'
            }
        }
        
        event = {
            'headers': {
                'Authorization': f'Bearer {valid_consumer_token}'
            },
            'body': json.dumps(order_request)
        }
        
        with patch('orders.create_order.get_item') as mock_get_item, \
             patch('orders.create_order.put_item') as mock_put_item, \
             patch('orders.create_order.update_item') as mock_update_item:
            
            mock_get_item.return_value = mock_approved_product
            mock_put_item.return_value = {}
            mock_update_item.return_value = {}
            
            response = create_order.handler(event, None)
            
            assert response['statusCode'] == 201
            body = json.loads(response['body'])
            assert 'orderId' in body
            
            # Verify referralCode is None in stored order
            order_dict = mock_put_item.call_args[0][0]
            assert order_dict['referralCode'] is None
    
    def test_estimated_delivery_date_calculation(self, mock_env, valid_consumer_token, valid_order_request, mock_approved_product):
        """Test that estimated delivery date is correctly calculated as current date + 7 days."""
        event = {
            'headers': {
                'Authorization': f'Bearer {valid_consumer_token}'
            },
            'body': json.dumps(valid_order_request)
        }
        
        with patch('orders.create_order.get_item') as mock_get_item, \
             patch('orders.create_order.put_item') as mock_put_item, \
             patch('orders.create_order.update_item') as mock_update_item:
            
            mock_get_item.return_value = mock_approved_product
            mock_put_item.return_value = {}
            mock_update_item.return_value = {}
            
            before_time = datetime.utcnow()
            response = create_order.handler(event, None)
            after_time = datetime.utcnow()
            
            assert response['statusCode'] == 201
            body = json.loads(response['body'])
            
            # Parse estimated delivery date
            estimated_date = datetime.fromisoformat(body['estimatedDeliveryDate'].replace('Z', '+00:00'))
            
            # Verify it's approximately 7 days from now
            expected_min = before_time + timedelta(days=DEFAULT_DELIVERY_DAYS)
            expected_max = after_time + timedelta(days=DEFAULT_DELIVERY_DAYS)
            
            assert expected_min <= estimated_date <= expected_max


class TestAuthorization:
    """Test authorization and authentication."""
    
    def test_missing_authorization_header(self, mock_env, valid_order_request):
        """Test that missing authorization header returns 401."""
        event = {
            'headers': {},
            'body': json.dumps(valid_order_request)
        }
        
        response = create_order.handler(event, None)
        
        assert response['statusCode'] == 401
        body = json.loads(response['body'])
        assert body['error']['code'] == 'UNAUTHORIZED'
    
    def test_invalid_token(self, mock_env, valid_order_request):
        """Test that invalid JWT token returns 401."""
        event = {
            'headers': {
                'Authorization': 'Bearer invalid-token-12345'
            },
            'body': json.dumps(valid_order_request)
        }
        
        response = create_order.handler(event, None)
        
        assert response['statusCode'] == 401
        body = json.loads(response['body'])
        assert body['error']['code'] == 'INVALID_TOKEN'
    
    def test_farmer_cannot_create_order(self, mock_env, valid_farmer_token, valid_order_request):
        """Test that farmers cannot create orders (consumer-only endpoint)."""
        event = {
            'headers': {
                'Authorization': f'Bearer {valid_farmer_token}'
            },
            'body': json.dumps(valid_order_request)
        }
        
        response = create_order.handler(event, None)
        
        assert response['statusCode'] == 403
        body = json.loads(response['body'])
        assert body['error']['code'] == 'FORBIDDEN'
        assert 'consumer' in body['error']['message'].lower()


class TestValidation:
    """Test input validation."""
    
    def test_invalid_json_body(self, mock_env, valid_consumer_token):
        """Test that invalid JSON returns 400."""
        event = {
            'headers': {
                'Authorization': f'Bearer {valid_consumer_token}'
            },
            'body': 'invalid json {'
        }
        
        response = create_order.handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error']['code'] == 'INVALID_JSON'
    
    def test_missing_required_fields(self, mock_env, valid_consumer_token):
        """Test that missing required fields returns validation error."""
        incomplete_request = {
            'productId': 'product-789'
            # Missing quantity and deliveryAddress
        }
        
        event = {
            'headers': {
                'Authorization': f'Bearer {valid_consumer_token}'
            },
            'body': json.dumps(incomplete_request)
        }
        
        response = create_order.handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error']['code'] == 'VALIDATION_ERROR'
    
    def test_negative_quantity(self, mock_env, valid_consumer_token):
        """Test that negative quantity returns validation error."""
        invalid_request = {
            'productId': 'product-789',
            'quantity': -1,
            'deliveryAddress': {
                'street': '123 Main St',
                'city': 'Mumbai',
                'state': 'Maharashtra',
                'pincode': '400001'
            }
        }
        
        event = {
            'headers': {
                'Authorization': f'Bearer {valid_consumer_token}'
            },
            'body': json.dumps(invalid_request)
        }
        
        response = create_order.handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error']['code'] == 'VALIDATION_ERROR'
    
    def test_zero_quantity(self, mock_env, valid_consumer_token):
        """Test that zero quantity returns validation error."""
        invalid_request = {
            'productId': 'product-789',
            'quantity': 0,
            'deliveryAddress': {
                'street': '123 Main St',
                'city': 'Mumbai',
                'state': 'Maharashtra',
                'pincode': '400001'
            }
        }
        
        event = {
            'headers': {
                'Authorization': f'Bearer {valid_consumer_token}'
            },
            'body': json.dumps(invalid_request)
        }
        
        response = create_order.handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error']['code'] == 'VALIDATION_ERROR'
    
    def test_incomplete_delivery_address(self, mock_env, valid_consumer_token):
        """Test that incomplete delivery address returns validation error."""
        invalid_request = {
            'productId': 'product-789',
            'quantity': 1,
            'deliveryAddress': {
                'street': '123 Main St'
                # Missing city, state, pincode
            }
        }
        
        event = {
            'headers': {
                'Authorization': f'Bearer {valid_consumer_token}'
            },
            'body': json.dumps(invalid_request)
        }
        
        response = create_order.handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error']['code'] == 'VALIDATION_ERROR'


class TestProductAvailability:
    """Test product availability and verification status checks."""
    
    def test_product_not_found(self, mock_env, valid_consumer_token, valid_order_request):
        """Test that ordering non-existent product returns 404."""
        event = {
            'headers': {
                'Authorization': f'Bearer {valid_consumer_token}'
            },
            'body': json.dumps(valid_order_request)
        }
        
        with patch('orders.create_order.get_item') as mock_get_item:
            mock_get_item.return_value = None
            
            response = create_order.handler(event, None)
            
            assert response['statusCode'] == 404
            body = json.loads(response['body'])
            assert body['error']['code'] == 'RESOURCE_NOT_FOUND'
    
    def test_product_not_approved(self, mock_env, valid_consumer_token, valid_order_request, mock_approved_product):
        """Test that ordering pending/flagged product returns 409."""
        event = {
            'headers': {
                'Authorization': f'Bearer {valid_consumer_token}'
            },
            'body': json.dumps(valid_order_request)
        }
        
        # Modify product to be pending
        pending_product = mock_approved_product.copy()
        pending_product['verificationStatus'] = VerificationStatus.PENDING.value
        
        with patch('orders.create_order.get_item') as mock_get_item:
            mock_get_item.return_value = pending_product
            
            response = create_order.handler(event, None)
            
            assert response['statusCode'] == 409
            body = json.loads(response['body'])
            assert body['error']['code'] == 'CONFLICT_ERROR'
            assert 'not approved' in body['error']['message'].lower()
    
    def test_insufficient_quantity(self, mock_env, valid_consumer_token, valid_order_request, mock_approved_product):
        """Test that ordering more than available quantity returns 409."""
        event = {
            'headers': {
                'Authorization': f'Bearer {valid_consumer_token}'
            },
            'body': json.dumps(valid_order_request)
        }
        
        # Modify product to have less quantity than requested
        low_stock_product = mock_approved_product.copy()
        low_stock_product['quantity'] = 1  # Request is for 2
        
        with patch('orders.create_order.get_item') as mock_get_item:
            mock_get_item.return_value = low_stock_product
            
            response = create_order.handler(event, None)
            
            assert response['statusCode'] == 409
            body = json.loads(response['body'])
            assert body['error']['code'] == 'OUT_OF_STOCK'
            assert 'insufficient quantity' in body['error']['message'].lower()
    
    def test_exact_quantity_available(self, mock_env, valid_consumer_token, valid_order_request, mock_approved_product):
        """Test that ordering exact available quantity succeeds."""
        event = {
            'headers': {
                'Authorization': f'Bearer {valid_consumer_token}'
            },
            'body': json.dumps(valid_order_request)
        }
        
        # Set product quantity to exactly match request
        exact_stock_product = mock_approved_product.copy()
        exact_stock_product['quantity'] = 2  # Request is for 2
        
        with patch('orders.create_order.get_item') as mock_get_item, \
             patch('orders.create_order.put_item') as mock_put_item, \
             patch('orders.create_order.update_item') as mock_update_item:
            
            mock_get_item.return_value = exact_stock_product
            mock_put_item.return_value = {}
            mock_update_item.return_value = {}
            
            response = create_order.handler(event, None)
            
            assert response['statusCode'] == 201


class TestInventoryManagement:
    """Test atomic inventory decrement and race condition handling."""
    
    def test_inventory_decremented_atomically(self, mock_env, valid_consumer_token, valid_order_request, mock_approved_product):
        """Test that product quantity is decremented using conditional update."""
        event = {
            'headers': {
                'Authorization': f'Bearer {valid_consumer_token}'
            },
            'body': json.dumps(valid_order_request)
        }
        
        with patch('orders.create_order.get_item') as mock_get_item, \
             patch('orders.create_order.put_item') as mock_put_item, \
             patch('orders.create_order.update_item') as mock_update_item:
            
            mock_get_item.return_value = mock_approved_product
            mock_put_item.return_value = {}
            mock_update_item.return_value = {}
            
            response = create_order.handler(event, None)
            
            assert response['statusCode'] == 201
            
            # Verify conditional update was used
            update_call = mock_update_item.call_args
            assert 'condition_expression' in update_call[1]
            assert 'quantity >= :min_qty' in update_call[1]['condition_expression']
    
    def test_race_condition_handling(self, mock_env, valid_consumer_token, valid_order_request, mock_approved_product):
        """Test that race condition (concurrent orders) is handled gracefully."""
        from backend.shared.exceptions import ConflictError
        
        event = {
            'headers': {
                'Authorization': f'Bearer {valid_consumer_token}'
            },
            'body': json.dumps(valid_order_request)
        }
        
        with patch('orders.create_order.get_item') as mock_get_item, \
             patch('orders.create_order.put_item') as mock_put_item, \
             patch('orders.create_order.update_item') as mock_update_item:
            
            mock_get_item.return_value = mock_approved_product
            mock_put_item.return_value = {}
            # Simulate conditional update failure (race condition)
            mock_update_item.side_effect = ConflictError('Update condition not met')
            
            response = create_order.handler(event, None)
            
            assert response['statusCode'] == 409
            body = json.loads(response['body'])
            assert body['error']['code'] == 'OUT_OF_STOCK'
            assert 'quantity changed' in body['error']['message'].lower()


class TestDynamoDBKeys:
    """Test that correct DynamoDB keys are set for queries."""
    
    def test_order_keys_set_correctly(self, mock_env, valid_consumer_token, valid_order_request, mock_approved_product):
        """Test that order PK, SK, and GSI keys are set correctly."""
        event = {
            'headers': {
                'Authorization': f'Bearer {valid_consumer_token}'
            },
            'body': json.dumps(valid_order_request)
        }
        
        with patch('orders.create_order.get_item') as mock_get_item, \
             patch('orders.create_order.put_item') as mock_put_item, \
             patch('orders.create_order.update_item') as mock_update_item:
            
            mock_get_item.return_value = mock_approved_product
            mock_put_item.return_value = {}
            mock_update_item.return_value = {}
            
            response = create_order.handler(event, None)
            
            assert response['statusCode'] == 201
            
            # Verify order keys
            order_dict = mock_put_item.call_args[0][0]
            assert order_dict['PK'].startswith('ORDER#')
            assert order_dict['SK'] == 'METADATA'
            assert order_dict['GSI2PK'] == 'CONSUMER#consumer-123'
            assert order_dict['GSI2SK'].startswith('ORDER#')
            assert order_dict['GSI3PK'] == 'FARMER#farmer-456'
            assert order_dict['GSI3SK'].startswith('ORDER#')


class TestTotalAmountCalculation:
    """Test total amount calculation."""
    
    def test_total_amount_calculation(self, mock_env, valid_consumer_token, mock_approved_product):
        """Test that total amount is correctly calculated as price × quantity."""
        test_cases = [
            (1, 50.0),
            (2, 100.0),
            (5, 250.0),
            (10, 500.0)
        ]
        
        for quantity, expected_total in test_cases:
            order_request = {
                'productId': 'product-789',
                'quantity': quantity,
                'deliveryAddress': {
                    'street': '123 Main St',
                    'city': 'Mumbai',
                    'state': 'Maharashtra',
                    'pincode': '400001'
                }
            }
            
            event = {
                'headers': {
                    'Authorization': f'Bearer {valid_consumer_token}'
                },
                'body': json.dumps(order_request)
            }
            
            with patch('orders.create_order.get_item') as mock_get_item, \
                 patch('orders.create_order.put_item') as mock_put_item, \
                 patch('orders.create_order.update_item') as mock_update_item:
                
                mock_get_item.return_value = mock_approved_product
                mock_put_item.return_value = {}
                mock_update_item.return_value = {}
                
                response = create_order.handler(event, None)
                
                assert response['statusCode'] == 201
                body = json.loads(response['body'])
                assert body['totalAmount'] == expected_total


class TestErrorHandling:
    """Test error handling for external service failures."""
    
    def test_dynamodb_get_failure(self, mock_env, valid_consumer_token, valid_order_request):
        """Test handling of DynamoDB get_item failure."""
        event = {
            'headers': {
                'Authorization': f'Bearer {valid_consumer_token}'
            },
            'body': json.dumps(valid_order_request)
        }
        
        with patch('orders.create_order.get_item') as mock_get_item:
            mock_get_item.side_effect = Exception('DynamoDB unavailable')
            
            response = create_order.handler(event, None)
            
            assert response['statusCode'] == 503
            body = json.loads(response['body'])
            assert body['error']['code'] == 'SERVICE_UNAVAILABLE'
    
    def test_dynamodb_put_failure(self, mock_env, valid_consumer_token, valid_order_request, mock_approved_product):
        """Test handling of DynamoDB put_item failure."""
        event = {
            'headers': {
                'Authorization': f'Bearer {valid_consumer_token}'
            },
            'body': json.dumps(valid_order_request)
        }
        
        with patch('orders.create_order.get_item') as mock_get_item, \
             patch('orders.create_order.put_item') as mock_put_item:
            
            mock_get_item.return_value = mock_approved_product
            mock_put_item.side_effect = Exception('DynamoDB write failed')
            
            response = create_order.handler(event, None)
            
            assert response['statusCode'] == 503
            body = json.loads(response['body'])
            assert body['error']['code'] == 'SERVICE_UNAVAILABLE'
    
    def test_dynamodb_update_failure(self, mock_env, valid_consumer_token, valid_order_request, mock_approved_product):
        """Test handling of DynamoDB update_item failure."""
        event = {
            'headers': {
                'Authorization': f'Bearer {valid_consumer_token}'
            },
            'body': json.dumps(valid_order_request)
        }
        
        with patch('orders.create_order.get_item') as mock_get_item, \
             patch('orders.create_order.put_item') as mock_put_item, \
             patch('orders.create_order.update_item') as mock_update_item:
            
            mock_get_item.return_value = mock_approved_product
            mock_put_item.return_value = {}
            mock_update_item.side_effect = Exception('DynamoDB update failed')
            
            response = create_order.handler(event, None)
            
            assert response['statusCode'] == 503
            body = json.loads(response['body'])
            assert body['error']['code'] == 'SERVICE_UNAVAILABLE'
