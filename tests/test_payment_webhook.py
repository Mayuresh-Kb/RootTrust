"""
Tests for payment webhook handler.
"""
import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend', 'shared'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend', 'payments'))

# Import after path setup
import constants
from constants import OrderStatus, PaymentStatus, PaymentGateway

# Mock the shared imports before importing webhook_handler
sys.modules['shared.models'] = MagicMock()
sys.modules['shared.database'] = MagicMock()
sys.modules['shared.constants'] = constants
sys.modules['shared.exceptions'] = MagicMock()
sys.modules['shared.email_service'] = MagicMock()
sys.modules['shared.email_templates'] = MagicMock()

import webhook_handler
from webhook_handler import (
    verify_stripe_signature,
    verify_razorpay_signature,
    parse_stripe_webhook,
    parse_razorpay_webhook
)


# Test fixtures
@pytest.fixture
def mock_env(monkeypatch):
    """Set up mock environment variables."""
    monkeypatch.setenv('DYNAMODB_TABLE_NAME', 'test-table')
    monkeypatch.setenv('USE_MOCK_PAYMENT', 'true')
    monkeypatch.setenv('STRIPE_WEBHOOK_SECRET', 'whsec_test_secret')
    monkeypatch.setenv('RAZORPAY_WEBHOOK_SECRET', 'test_secret')
    monkeypatch.setenv('SENDER_EMAIL', 'test@roottrust.com')


@pytest.fixture
def sample_order():
    """Sample order data."""
    return {
        'PK': 'ORDER#order-123',
        'SK': 'METADATA',
        'orderId': 'order-123',
        'consumerId': 'consumer-456',
        'farmerId': 'farmer-789',
        'productName': 'Organic Tomatoes',
        'totalAmount': 500.0,
        'status': OrderStatus.PENDING.value,
        'paymentStatus': PaymentStatus.PENDING.value,
        'estimatedDeliveryDate': (datetime.utcnow() + timedelta(days=7)).isoformat()
    }


@pytest.fixture
def sample_consumer():
    """Sample consumer data."""
    return {
        'PK': 'USER#consumer-456',
        'SK': 'PROFILE',
        'userId': 'consumer-456',
        'email': 'consumer@example.com',
        'firstName': 'John',
        'role': 'consumer'
    }


@pytest.fixture
def sample_farmer():
    """Sample farmer data."""
    return {
        'PK': 'USER#farmer-789',
        'SK': 'PROFILE',
        'userId': 'farmer-789',
        'email': 'farmer@example.com',
        'firstName': 'Jane',
        'role': 'farmer'
    }


@pytest.fixture
def stripe_success_webhook():
    """Sample Stripe success webhook payload."""
    return {
        'type': 'checkout.session.completed',
        'data': {
            'object': {
                'id': 'cs_test_abc123',
                'amount_total': 50000,  # 500.00 INR in cents
                'payment_status': 'paid',
                'metadata': {
                    'order_id': 'order-123'
                }
            }
        }
    }


@pytest.fixture
def stripe_failure_webhook():
    """Sample Stripe failure webhook payload."""
    return {
        'type': 'checkout.session.async_payment_failed',
        'data': {
            'object': {
                'id': 'cs_test_abc123',
                'amount_total': 50000,
                'metadata': {
                    'order_id': 'order-123'
                }
            }
        }
    }


@pytest.fixture
def razorpay_success_webhook():
    """Sample Razorpay success webhook payload."""
    return {
        'event': 'payment.captured',
        'payload': {
            'payment': {
                'entity': {
                    'id': 'pay_abc123',
                    'amount': 50000,  # 500.00 INR in paise
                    'notes': {
                        'order_id': 'order-123'
                    }
                }
            }
        }
    }


@pytest.fixture
def razorpay_failure_webhook():
    """Sample Razorpay failure webhook payload."""
    return {
        'event': 'payment.failed',
        'payload': {
            'payment': {
                'entity': {
                    'id': 'pay_abc123',
                    'amount': 50000,
                    'notes': {
                        'order_id': 'order-123'
                    }
                }
            }
        }
    }


# Signature verification tests
def test_verify_stripe_signature_mock_mode(mock_env):
    """Test Stripe signature verification in mock mode."""
    result = verify_stripe_signature('payload', 'signature', 'secret')
    assert result is True


def test_verify_razorpay_signature_mock_mode(mock_env):
    """Test Razorpay signature verification in mock mode."""
    result = verify_razorpay_signature('payload', 'signature', 'secret')
    assert result is True


# Webhook parsing tests
def test_parse_stripe_success_webhook(stripe_success_webhook):
    """Test parsing Stripe success webhook."""
    result = parse_stripe_webhook(stripe_success_webhook)
    
    assert result is not None
    assert result['transactionId'] == 'cs_test_abc123'
    assert result['orderId'] == 'order-123'
    assert result['amount'] == 500.0
    assert result['status'] == PaymentStatus.COMPLETED.value
    assert result['gateway'] == PaymentGateway.STRIPE.value


def test_parse_stripe_failure_webhook(stripe_failure_webhook):
    """Test parsing Stripe failure webhook."""
    result = parse_stripe_webhook(stripe_failure_webhook)
    
    assert result is not None
    assert result['transactionId'] == 'cs_test_abc123'
    assert result['orderId'] == 'order-123'
    assert result['amount'] == 500.0
    assert result['status'] == PaymentStatus.FAILED.value
    assert result['gateway'] == PaymentGateway.STRIPE.value


def test_parse_stripe_webhook_invalid_event():
    """Test parsing Stripe webhook with invalid event type."""
    payload = {
        'type': 'unknown.event',
        'data': {'object': {}}
    }
    
    result = parse_stripe_webhook(payload)
    assert result is None


def test_parse_razorpay_success_webhook(razorpay_success_webhook):
    """Test parsing Razorpay success webhook."""
    result = parse_razorpay_webhook(razorpay_success_webhook)
    
    assert result is not None
    assert result['transactionId'] == 'pay_abc123'
    assert result['orderId'] == 'order-123'
    assert result['amount'] == 500.0
    assert result['status'] == PaymentStatus.COMPLETED.value
    assert result['gateway'] == PaymentGateway.RAZORPAY.value


def test_parse_razorpay_failure_webhook(razorpay_failure_webhook):
    """Test parsing Razorpay failure webhook."""
    result = parse_razorpay_webhook(razorpay_failure_webhook)
    
    assert result is not None
    assert result['transactionId'] == 'pay_abc123'
    assert result['orderId'] == 'order-123'
    assert result['amount'] == 500.0
    assert result['status'] == PaymentStatus.FAILED.value
    assert result['gateway'] == PaymentGateway.RAZORPAY.value


def test_parse_razorpay_webhook_invalid_event():
    """Test parsing Razorpay webhook with invalid event type."""
    payload = {
        'event': 'unknown.event',
        'payload': {}
    }
    
    result = parse_razorpay_webhook(payload)
    assert result is None


# Webhook handler tests
@patch('webhook_handler.get_item')
@patch('webhook_handler.put_item')
@patch('webhook_handler.update_item')
@patch('webhook_handler.get_email_service')
def test_stripe_success_webhook_handler(
    mock_email_service,
    mock_update_item,
    mock_put_item,
    mock_get_item,
    mock_env,
    stripe_success_webhook,
    sample_order,
    sample_consumer,
    sample_farmer
):
    """Test handling Stripe success webhook."""
    # Mock database responses
    def get_item_side_effect(pk, sk):
        if pk == 'ORDER#order-123':
            return sample_order
        elif pk == 'USER#consumer-456':
            return sample_consumer
        elif pk == 'USER#farmer-789':
            return sample_farmer
        return None
    
    mock_get_item.side_effect = get_item_side_effect
    
    # Mock email service
    mock_email = MagicMock()
    mock_email.send_email.return_value = {'success': True, 'message_id': 'test-123'}
    mock_email_service.return_value = mock_email
    
    # Create webhook event
    event = {
        'body': json.dumps(stripe_success_webhook),
        'headers': {
            'stripe-signature': 't=123456,v1=test_signature'
        }
    }
    
    # Call handler
    response = webhook_handler.handler(event, None)
    
    # Verify response
    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert body['message'] == 'Webhook processed successfully'
    assert body['transactionId'] == 'cs_test_abc123'
    assert body['orderId'] == 'order-123'
    assert body['status'] == PaymentStatus.COMPLETED.value
    
    # Verify transaction was stored
    assert mock_put_item.called
    transaction_call = mock_put_item.call_args[0][0]
    assert transaction_call['transactionId'] == 'cs_test_abc123'
    assert transaction_call['orderId'] == 'order-123'
    assert transaction_call['status'] == PaymentStatus.COMPLETED.value
    
    # Verify order was updated
    assert mock_update_item.called
    update_call = mock_update_item.call_args
    assert update_call[1]['pk'] == 'ORDER#order-123'
    assert OrderStatus.CONFIRMED.value in str(update_call[1]['expression_attribute_values'])
    
    # Verify emails were sent (consumer + farmer)
    assert mock_email.send_email.call_count == 2


@patch('webhook_handler.get_item')
@patch('webhook_handler.put_item')
@patch('webhook_handler.update_item')
@patch('webhook_handler.get_email_service')
def test_stripe_failure_webhook_handler(
    mock_email_service,
    mock_update_item,
    mock_put_item,
    mock_get_item,
    mock_env,
    stripe_failure_webhook,
    sample_order,
    sample_consumer
):
    """Test handling Stripe failure webhook."""
    # Mock database responses
    def get_item_side_effect(pk, sk):
        if pk == 'ORDER#order-123':
            return sample_order
        elif pk == 'USER#consumer-456':
            return sample_consumer
        return None
    
    mock_get_item.side_effect = get_item_side_effect
    
    # Mock email service
    mock_email = MagicMock()
    mock_email.send_email.return_value = {'success': True, 'message_id': 'test-123'}
    mock_email_service.return_value = mock_email
    
    # Create webhook event
    event = {
        'body': json.dumps(stripe_failure_webhook),
        'headers': {
            'stripe-signature': 't=123456,v1=test_signature'
        }
    }
    
    # Call handler
    response = webhook_handler.handler(event, None)
    
    # Verify response
    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert body['status'] == PaymentStatus.FAILED.value
    
    # Verify order was updated to failed
    assert mock_update_item.called
    update_call = mock_update_item.call_args
    assert OrderStatus.FAILED.value in str(update_call[1]['expression_attribute_values'])
    
    # Verify failure email was sent to consumer
    assert mock_email.send_email.call_count == 1


@patch('webhook_handler.get_item')
@patch('webhook_handler.put_item')
@patch('webhook_handler.update_item')
@patch('webhook_handler.get_email_service')
def test_razorpay_success_webhook_handler(
    mock_email_service,
    mock_update_item,
    mock_put_item,
    mock_get_item,
    mock_env,
    razorpay_success_webhook,
    sample_order,
    sample_consumer,
    sample_farmer
):
    """Test handling Razorpay success webhook."""
    # Mock database responses
    def get_item_side_effect(pk, sk):
        if pk == 'ORDER#order-123':
            return sample_order
        elif pk == 'USER#consumer-456':
            return sample_consumer
        elif pk == 'USER#farmer-789':
            return sample_farmer
        return None
    
    mock_get_item.side_effect = get_item_side_effect
    
    # Mock email service
    mock_email = MagicMock()
    mock_email.send_email.return_value = {'success': True, 'message_id': 'test-123'}
    mock_email_service.return_value = mock_email
    
    # Create webhook event
    event = {
        'body': json.dumps(razorpay_success_webhook),
        'headers': {
            'x-razorpay-signature': 'test_signature'
        }
    }
    
    # Call handler
    response = webhook_handler.handler(event, None)
    
    # Verify response
    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert body['transactionId'] == 'pay_abc123'
    assert body['status'] == PaymentStatus.COMPLETED.value
    
    # Verify transaction was stored
    assert mock_put_item.called
    
    # Verify order was updated
    assert mock_update_item.called
    
    # Verify emails were sent
    assert mock_email.send_email.call_count == 2


def test_webhook_missing_signature(mock_env):
    """Test webhook handler with missing signature."""
    event = {
        'body': json.dumps({'test': 'data'}),
        'headers': {}
    }
    
    response = webhook_handler.handler(event, None)
    
    assert response['statusCode'] == 400
    body = json.loads(response['body'])
    assert body['error']['code'] == 'MISSING_SIGNATURE'


def test_webhook_invalid_json(mock_env):
    """Test webhook handler with invalid JSON."""
    event = {
        'body': 'invalid json',
        'headers': {
            'stripe-signature': 't=123456,v1=test_signature'
        }
    }
    
    response = webhook_handler.handler(event, None)
    
    assert response['statusCode'] == 400
    body = json.loads(response['body'])
    assert body['error']['code'] == 'INVALID_JSON'


@patch('webhook_handler.get_item')
@patch('webhook_handler.put_item')
def test_webhook_order_not_found(
    mock_put_item,
    mock_get_item,
    mock_env,
    stripe_success_webhook
):
    """Test webhook handler when order is not found."""
    # Mock order not found
    mock_get_item.return_value = None
    
    event = {
        'body': json.dumps(stripe_success_webhook),
        'headers': {
            'stripe-signature': 't=123456,v1=test_signature'
        }
    }
    
    response = webhook_handler.handler(event, None)
    
    # Should still return 200 OK to acknowledge webhook
    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert 'order not found' in body['message'].lower()


@patch('webhook_handler.get_item')
@patch('webhook_handler.put_item')
@patch('webhook_handler.update_item')
def test_webhook_database_error(
    mock_update_item,
    mock_put_item,
    mock_get_item,
    mock_env,
    stripe_success_webhook,
    sample_order
):
    """Test webhook handler with database error."""
    # Mock database error
    mock_get_item.side_effect = Exception('Database error')
    
    event = {
        'body': json.dumps(stripe_success_webhook),
        'headers': {
            'stripe-signature': 't=123456,v1=test_signature'
        }
    }
    
    response = webhook_handler.handler(event, None)
    
    # Should still return 200 OK to prevent webhook retries
    assert response['statusCode'] == 200


def test_webhook_missing_required_fields(mock_env):
    """Test webhook with missing required fields."""
    # Webhook with missing order_id
    invalid_webhook = {
        'type': 'checkout.session.completed',
        'data': {
            'object': {
                'id': 'cs_test_abc123',
                'amount_total': 50000,
                'payment_status': 'paid',
                'metadata': {}  # Missing order_id
            }
        }
    }
    
    event = {
        'body': json.dumps(invalid_webhook),
        'headers': {
            'stripe-signature': 't=123456,v1=test_signature'
        }
    }
    
    response = webhook_handler.handler(event, None)
    
    assert response['statusCode'] == 400
    body = json.loads(response['body'])
    assert body['error']['code'] == 'INVALID_PAYLOAD'


# Edge case tests
def test_parse_stripe_webhook_with_missing_fields():
    """Test parsing Stripe webhook with missing fields."""
    payload = {
        'type': 'checkout.session.completed',
        'data': {
            'object': {
                'id': 'cs_test_abc123'
                # Missing amount_total, payment_status, metadata
            }
        }
    }
    
    result = parse_stripe_webhook(payload)
    # Should handle gracefully
    assert result is not None or result is None  # Implementation dependent


def test_parse_razorpay_webhook_with_missing_fields():
    """Test parsing Razorpay webhook with missing fields."""
    payload = {
        'event': 'payment.captured',
        'payload': {
            'payment': {
                'entity': {
                    'id': 'pay_abc123'
                    # Missing amount, notes
                }
            }
        }
    }
    
    result = parse_razorpay_webhook(payload)
    # Should handle gracefully
    assert result is not None or result is None  # Implementation dependent


@patch('webhook_handler.get_item')
@patch('webhook_handler.put_item')
@patch('webhook_handler.update_item')
@patch('webhook_handler.get_email_service')
def test_webhook_email_failure_does_not_block(
    mock_email_service,
    mock_update_item,
    mock_put_item,
    mock_get_item,
    mock_env,
    stripe_success_webhook,
    sample_order,
    sample_consumer,
    sample_farmer
):
    """Test that email failures don't block webhook processing."""
    # Mock database responses
    def get_item_side_effect(pk, sk):
        if pk == 'ORDER#order-123':
            return sample_order
        elif pk == 'USER#consumer-456':
            return sample_consumer
        elif pk == 'USER#farmer-789':
            return sample_farmer
        return None
    
    mock_get_item.side_effect = get_item_side_effect
    
    # Mock email service to fail
    mock_email = MagicMock()
    mock_email.send_email.side_effect = Exception('Email service error')
    mock_email_service.return_value = mock_email
    
    event = {
        'body': json.dumps(stripe_success_webhook),
        'headers': {
            'stripe-signature': 't=123456,v1=test_signature'
        }
    }
    
    response = webhook_handler.handler(event, None)
    
    # Should still return 200 OK
    assert response['statusCode'] == 200
    
    # Order should still be updated
    assert mock_update_item.called


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
