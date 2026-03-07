"""
Tests for order status update endpoint (PUT /orders/{orderId}/status).
Tests farmer authorization, ownership verification, status updates, and email notifications.
"""
import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend', 'orders'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend', 'shared'))

from orders.update_order_status import handler, VALID_ORDER_STATUSES
from shared.constants import UserRole, OrderStatus


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Set up environment variables for tests."""
    monkeypatch.setenv('TABLE_NAME', 'test-table')
    monkeypatch.setenv('JWT_SECRET_ARN', 'test-secret-arn')
    monkeypatch.setenv('SENDER_EMAIL', 'test@roottrust.com')


@pytest.fixture
def farmer_token_payload():
    """Mock farmer JWT token payload."""
    return {
        'userId': 'farmer-123',
        'role': UserRole.FARMER.value,
        'email': 'farmer@example.com'
    }


@pytest.fixture
def consumer_token_payload():
    """Mock consumer JWT token payload."""
    return {
        'userId': 'consumer-456',
        'role': UserRole.CONSUMER.value,
        'email': 'consumer@example.com'
    }


@pytest.fixture
def sample_order():
    """Sample order data."""
    return {
        'PK': 'ORDER#order-789',
        'SK': 'METADATA',
        'EntityType': 'Order',
        'orderId': 'order-789',
        'consumerId': 'consumer-456',
        'farmerId': 'farmer-123',
        'productId': 'product-101',
        'productName': 'Organic Tomatoes',
        'quantity': 5,
        'unitPrice': 50.0,
        'totalAmount': 250.0,
        'status': OrderStatus.CONFIRMED.value,
        'paymentStatus': 'completed',
        'deliveryAddress': {
            'street': '123 Main St',
            'city': 'Mumbai',
            'state': 'Maharashtra',
            'pincode': '400001'
        },
        'estimatedDeliveryDate': (datetime.utcnow() + timedelta(days=7)).isoformat(),
        'createdAt': datetime.utcnow().isoformat(),
        'updatedAt': datetime.utcnow().isoformat()
    }


@pytest.fixture
def sample_consumer():
    """Sample consumer data."""
    return {
        'PK': 'USER#consumer-456',
        'SK': 'PROFILE',
        'EntityType': 'User',
        'userId': 'consumer-456',
        'email': 'consumer@example.com',
        'firstName': 'John',
        'lastName': 'Doe',
        'role': UserRole.CONSUMER.value
    }


class TestOrderStatusUpdateAuthentication:
    """Test authentication and authorization for order status update."""
    
    @patch('orders.update_order_status.get_user_from_token')
    def test_missing_authorization_header(self, mock_env_vars):
        """Test that missing authorization header returns 401."""
        event = {
            'headers': {},
            'pathParameters': {'orderId': 'order-789'},
            'body': json.dumps({'status': 'processing'})
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 401
        body = json.loads(response['body'])
        assert body['error']['code'] == 'UNAUTHORIZED'
    
    @patch('orders.update_order_status.get_user_from_token')
    def test_invalid_token(self, mock_get_user, mock_env_vars):
        """Test that invalid token returns 401."""
        mock_get_user.side_effect = Exception('Invalid token')
        
        event = {
            'headers': {'Authorization': 'Bearer invalid-token'},
            'pathParameters': {'orderId': 'order-789'},
            'body': json.dumps({'status': 'processing'})
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 401
        body = json.loads(response['body'])
        assert body['error']['code'] == 'INVALID_TOKEN'
    
    @patch('orders.update_order_status.get_user_from_token')
    def test_consumer_cannot_update_status(self, mock_get_user, mock_env_vars, consumer_token_payload):
        """Test that consumers cannot update order status."""
        mock_get_user.return_value = consumer_token_payload
        
        event = {
            'headers': {'Authorization': 'Bearer consumer-token'},
            'pathParameters': {'orderId': 'order-789'},
            'body': json.dumps({'status': 'processing'})
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 403
        body = json.loads(response['body'])
        assert body['error']['code'] == 'FORBIDDEN'
        assert 'Only farmers' in body['error']['message']


class TestOrderStatusUpdateValidation:
    """Test input validation for order status update."""
    
    @patch('orders.update_order_status.get_user_from_token')
    def test_missing_order_id(self, mock_get_user, mock_env_vars, farmer_token_payload):
        """Test that missing orderId returns 400."""
        mock_get_user.return_value = farmer_token_payload
        
        event = {
            'headers': {'Authorization': 'Bearer farmer-token'},
            'pathParameters': {},
            'body': json.dumps({'status': 'processing'})
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error']['code'] == 'VALIDATION_ERROR'
        assert 'orderId' in body['error']['message']
    
    @patch('orders.update_order_status.get_user_from_token')
    def test_invalid_json_body(self, mock_get_user, mock_env_vars, farmer_token_payload):
        """Test that invalid JSON returns 400."""
        mock_get_user.return_value = farmer_token_payload
        
        event = {
            'headers': {'Authorization': 'Bearer farmer-token'},
            'pathParameters': {'orderId': 'order-789'},
            'body': 'invalid-json'
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error']['code'] == 'INVALID_JSON'
    
    @patch('orders.update_order_status.get_user_from_token')
    def test_missing_status_field(self, mock_get_user, mock_env_vars, farmer_token_payload):
        """Test that missing status field returns 400."""
        mock_get_user.return_value = farmer_token_payload
        
        event = {
            'headers': {'Authorization': 'Bearer farmer-token'},
            'pathParameters': {'orderId': 'order-789'},
            'body': json.dumps({})
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error']['code'] == 'VALIDATION_ERROR'
        assert 'status is required' in body['error']['message']
    
    @patch('orders.update_order_status.get_user_from_token')
    def test_invalid_status_value(self, mock_get_user, mock_env_vars, farmer_token_payload):
        """Test that invalid status value returns 400."""
        mock_get_user.return_value = farmer_token_payload
        
        event = {
            'headers': {'Authorization': 'Bearer farmer-token'},
            'pathParameters': {'orderId': 'order-789'},
            'body': json.dumps({'status': 'invalid-status'})
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error']['code'] == 'VALIDATION_ERROR'
        assert 'Invalid status' in body['error']['message']
    
    @patch('orders.update_order_status.get_user_from_token')
    @pytest.mark.parametrize('valid_status', VALID_ORDER_STATUSES)
    def test_all_valid_statuses_accepted(self, mock_get_user, mock_env_vars, farmer_token_payload, valid_status):
        """Test that all valid status values are accepted in validation."""
        mock_get_user.return_value = farmer_token_payload
        
        with patch('orders.update_order_status.get_item') as mock_get_item:
            # Mock order not found to stop execution after validation
            mock_get_item.return_value = None
            
            event = {
                'headers': {'Authorization': 'Bearer farmer-token'},
                'pathParameters': {'orderId': 'order-789'},
                'body': json.dumps({'status': valid_status})
            }
            
            response = handler(event, None)
            
            # Should pass validation and fail at order lookup (404)
            assert response['statusCode'] == 404


class TestOrderStatusUpdateBusinessLogic:
    """Test business logic for order status update."""
    
    @patch('orders.update_order_status.get_user_from_token')
    @patch('orders.update_order_status.get_item')
    def test_order_not_found(self, mock_get_item, mock_get_user, mock_env_vars, farmer_token_payload):
        """Test that non-existent order returns 404."""
        mock_get_user.return_value = farmer_token_payload
        mock_get_item.return_value = None
        
        event = {
            'headers': {'Authorization': 'Bearer farmer-token'},
            'pathParameters': {'orderId': 'nonexistent-order'},
            'body': json.dumps({'status': 'processing'})
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 404
        body = json.loads(response['body'])
        assert body['error']['code'] == 'RESOURCE_NOT_FOUND'
    
    @patch('orders.update_order_status.get_user_from_token')
    @patch('orders.update_order_status.get_item')
    def test_farmer_cannot_update_other_farmers_order(
        self, mock_get_item, mock_get_user, mock_env_vars, farmer_token_payload, sample_order
    ):
        """Test that farmers can only update orders for their own products."""
        # Different farmer ID
        different_farmer_payload = farmer_token_payload.copy()
        different_farmer_payload['userId'] = 'different-farmer-999'
        
        mock_get_user.return_value = different_farmer_payload
        mock_get_item.return_value = sample_order
        
        event = {
            'headers': {'Authorization': 'Bearer farmer-token'},
            'pathParameters': {'orderId': 'order-789'},
            'body': json.dumps({'status': 'processing'})
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 403
        body = json.loads(response['body'])
        assert body['error']['code'] == 'FORBIDDEN'
        assert 'your own products' in body['error']['message']
    
    @patch('orders.update_order_status.get_user_from_token')
    @patch('orders.update_order_status.get_item')
    @patch('orders.update_order_status.update_item')
    @patch('orders.update_order_status.get_email_service')
    def test_successful_status_update_to_processing(
        self, mock_email_service, mock_update_item, mock_get_item, mock_get_user,
        mock_env_vars, farmer_token_payload, sample_order, sample_consumer
    ):
        """Test successful order status update to processing."""
        mock_get_user.return_value = farmer_token_payload
        
        # Mock get_item to return order first, then consumer, then updated order
        mock_get_item.side_effect = [sample_order, sample_consumer, {**sample_order, 'status': 'processing'}]
        
        mock_email = MagicMock()
        mock_email.send_email.return_value = {'success': True, 'message_id': 'test-123'}
        mock_email_service.return_value = mock_email
        
        event = {
            'headers': {'Authorization': 'Bearer farmer-token'},
            'pathParameters': {'orderId': 'order-789'},
            'body': json.dumps({'status': 'processing'})
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['message'] == 'Order status updated successfully'
        assert body['order']['status'] == 'processing'
        
        # Verify update_item was called correctly
        mock_update_item.assert_called_once()
        call_kwargs = mock_update_item.call_args[1]
        assert call_kwargs['pk'] == 'ORDER#order-789'
        assert call_kwargs['sk'] == 'METADATA'
        assert ':status' in call_kwargs['expression_attribute_values']
        assert call_kwargs['expression_attribute_values'][':status'] == 'processing'
        
        # Verify email was sent
        mock_email.send_email.assert_called_once()
    
    @patch('orders.update_order_status.get_user_from_token')
    @patch('orders.update_order_status.get_item')
    @patch('orders.update_order_status.update_item')
    @patch('orders.update_order_status.get_email_service')
    def test_delivered_status_sets_actual_delivery_date(
        self, mock_email_service, mock_update_item, mock_get_item, mock_get_user,
        mock_env_vars, farmer_token_payload, sample_order, sample_consumer
    ):
        """Test that delivered status sets actualDeliveryDate."""
        mock_get_user.return_value = farmer_token_payload
        
        # Mock get_item to return order first, then consumer, then updated order
        updated_order = {**sample_order, 'status': 'delivered', 'actualDeliveryDate': datetime.utcnow().isoformat()}
        mock_get_item.side_effect = [sample_order, sample_consumer, updated_order]
        
        mock_email = MagicMock()
        mock_email.send_email.return_value = {'success': True, 'message_id': 'test-123'}
        mock_email_service.return_value = mock_email
        
        event = {
            'headers': {'Authorization': 'Bearer farmer-token'},
            'pathParameters': {'orderId': 'order-789'},
            'body': json.dumps({'status': 'delivered'})
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['order']['status'] == 'delivered'
        assert 'actualDeliveryDate' in body['order']
        
        # Verify update_item included actualDeliveryDate
        call_kwargs = mock_update_item.call_args[1]
        assert 'actualDeliveryDate' in call_kwargs['update_expression']
        assert ':delivery_date' in call_kwargs['expression_attribute_values']
    
    @patch('orders.update_order_status.get_user_from_token')
    @patch('orders.update_order_status.get_item')
    @patch('orders.update_order_status.update_item')
    @patch('orders.update_order_status.get_email_service')
    def test_non_delivered_status_does_not_set_delivery_date(
        self, mock_email_service, mock_update_item, mock_get_item, mock_get_user,
        mock_env_vars, farmer_token_payload, sample_order, sample_consumer
    ):
        """Test that non-delivered statuses don't set actualDeliveryDate."""
        mock_get_user.return_value = farmer_token_payload
        
        mock_get_item.side_effect = [sample_order, sample_consumer, {**sample_order, 'status': 'shipped'}]
        
        mock_email = MagicMock()
        mock_email.send_email.return_value = {'success': True, 'message_id': 'test-123'}
        mock_email_service.return_value = mock_email
        
        event = {
            'headers': {'Authorization': 'Bearer farmer-token'},
            'pathParameters': {'orderId': 'order-789'},
            'body': json.dumps({'status': 'shipped'})
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 200
        
        # Verify update_item did NOT include actualDeliveryDate
        call_kwargs = mock_update_item.call_args[1]
        assert 'actualDeliveryDate' not in call_kwargs['update_expression']
        assert ':delivery_date' not in call_kwargs['expression_attribute_values']


class TestOrderStatusUpdateEmailNotifications:
    """Test email notification functionality."""
    
    @patch('orders.update_order_status.get_user_from_token')
    @patch('orders.update_order_status.get_item')
    @patch('orders.update_order_status.update_item')
    @patch('orders.update_order_status.get_email_service')
    @patch('orders.update_order_status.get_order_status_update_email')
    def test_email_notification_sent_to_consumer(
        self, mock_email_template, mock_email_service, mock_update_item, mock_get_item,
        mock_get_user, mock_env_vars, farmer_token_payload, sample_order, sample_consumer
    ):
        """Test that email notification is sent to consumer on status update."""
        mock_get_user.return_value = farmer_token_payload
        mock_get_item.side_effect = [sample_order, sample_consumer, {**sample_order, 'status': 'shipped'}]
        
        mock_email_template.return_value = {
            'subject': 'Order Update',
            'html_body': '<html>Test</html>',
            'text_body': 'Test'
        }
        
        mock_email = MagicMock()
        mock_email.send_email.return_value = {'success': True, 'message_id': 'test-123'}
        mock_email_service.return_value = mock_email
        
        event = {
            'headers': {'Authorization': 'Bearer farmer-token'},
            'pathParameters': {'orderId': 'order-789'},
            'body': json.dumps({'status': 'shipped'})
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 200
        
        # Verify email template was called with correct parameters
        mock_email_template.assert_called_once()
        call_kwargs = mock_email_template.call_args[1]
        assert call_kwargs['consumer_email'] == 'consumer@example.com'
        assert call_kwargs['consumer_first_name'] == 'John'
        assert call_kwargs['order_id'] == 'order-789'
        assert call_kwargs['product_name'] == 'Organic Tomatoes'
        assert call_kwargs['new_status'] == 'shipped'
        
        # Verify email was sent
        mock_email.send_email.assert_called_once()
        email_call_kwargs = mock_email.send_email.call_args[1]
        assert email_call_kwargs['recipient'] == 'consumer@example.com'
    
    @patch('orders.update_order_status.get_user_from_token')
    @patch('orders.update_order_status.get_item')
    @patch('orders.update_order_status.update_item')
    @patch('orders.update_order_status.get_email_service')
    def test_status_update_succeeds_even_if_email_fails(
        self, mock_email_service, mock_update_item, mock_get_item, mock_get_user,
        mock_env_vars, farmer_token_payload, sample_order, sample_consumer
    ):
        """Test that status update succeeds even if email notification fails."""
        mock_get_user.return_value = farmer_token_payload
        mock_get_item.side_effect = [sample_order, sample_consumer, {**sample_order, 'status': 'processing'}]
        
        # Mock email service to fail
        mock_email = MagicMock()
        mock_email.send_email.return_value = {'success': False, 'error_message': 'SES error'}
        mock_email_service.return_value = mock_email
        
        event = {
            'headers': {'Authorization': 'Bearer farmer-token'},
            'pathParameters': {'orderId': 'order-789'},
            'body': json.dumps({'status': 'processing'})
        }
        
        response = handler(event, None)
        
        # Status update should still succeed
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['message'] == 'Order status updated successfully'
    
    @patch('orders.update_order_status.get_user_from_token')
    @patch('orders.update_order_status.get_item')
    @patch('orders.update_order_status.update_item')
    def test_status_update_succeeds_if_consumer_not_found(
        self, mock_update_item, mock_get_item, mock_get_user,
        mock_env_vars, farmer_token_payload, sample_order
    ):
        """Test that status update succeeds even if consumer lookup fails."""
        mock_get_user.return_value = farmer_token_payload
        # Return order, then None for consumer, then updated order
        mock_get_item.side_effect = [sample_order, None, {**sample_order, 'status': 'processing'}]
        
        event = {
            'headers': {'Authorization': 'Bearer farmer-token'},
            'pathParameters': {'orderId': 'order-789'},
            'body': json.dumps({'status': 'processing'})
        }
        
        response = handler(event, None)
        
        # Status update should still succeed
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['message'] == 'Order status updated successfully'


class TestOrderStatusUpdateErrorHandling:
    """Test error handling for order status update."""
    
    @patch('orders.update_order_status.get_user_from_token')
    @patch('orders.update_order_status.get_item')
    def test_database_error_on_order_query(self, mock_get_item, mock_get_user, mock_env_vars, farmer_token_payload):
        """Test handling of database errors when querying order."""
        mock_get_user.return_value = farmer_token_payload
        mock_get_item.side_effect = Exception('DynamoDB error')
        
        event = {
            'headers': {'Authorization': 'Bearer farmer-token'},
            'pathParameters': {'orderId': 'order-789'},
            'body': json.dumps({'status': 'processing'})
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 503
        body = json.loads(response['body'])
        assert body['error']['code'] == 'SERVICE_UNAVAILABLE'
    
    @patch('orders.update_order_status.get_user_from_token')
    @patch('orders.update_order_status.get_item')
    @patch('orders.update_order_status.update_item')
    def test_database_error_on_status_update(
        self, mock_update_item, mock_get_item, mock_get_user,
        mock_env_vars, farmer_token_payload, sample_order
    ):
        """Test handling of database errors when updating status."""
        mock_get_user.return_value = farmer_token_payload
        mock_get_item.return_value = sample_order
        mock_update_item.side_effect = Exception('DynamoDB update error')
        
        event = {
            'headers': {'Authorization': 'Bearer farmer-token'},
            'pathParameters': {'orderId': 'order-789'},
            'body': json.dumps({'status': 'processing'})
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 503
        body = json.loads(response['body'])
        assert body['error']['code'] == 'SERVICE_UNAVAILABLE'
        assert 'update order status' in body['error']['message']


class TestOrderStatusUpdateIntegration:
    """Integration tests for complete order status update flow."""
    
    @patch('orders.update_order_status.get_user_from_token')
    @patch('orders.update_order_status.get_item')
    @patch('orders.update_order_status.update_item')
    @patch('orders.update_order_status.get_email_service')
    @pytest.mark.parametrize('status', ['confirmed', 'processing', 'shipped', 'delivered', 'cancelled'])
    def test_complete_flow_for_all_statuses(
        self, mock_email_service, mock_update_item, mock_get_item, mock_get_user,
        mock_env_vars, farmer_token_payload, sample_order, sample_consumer, status
    ):
        """Test complete flow for all valid status transitions."""
        mock_get_user.return_value = farmer_token_payload
        
        updated_order = {**sample_order, 'status': status}
        if status == 'delivered':
            updated_order['actualDeliveryDate'] = datetime.utcnow().isoformat()
        
        mock_get_item.side_effect = [sample_order, sample_consumer, updated_order]
        
        mock_email = MagicMock()
        mock_email.send_email.return_value = {'success': True, 'message_id': 'test-123'}
        mock_email_service.return_value = mock_email
        
        event = {
            'headers': {'Authorization': 'Bearer farmer-token'},
            'pathParameters': {'orderId': 'order-789'},
            'body': json.dumps({'status': status})
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['message'] == 'Order status updated successfully'
        assert body['order']['status'] == status
        
        # Verify email was sent
        mock_email.send_email.assert_called_once()
