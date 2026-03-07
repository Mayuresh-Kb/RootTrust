"""
Unit tests for review request email trigger Lambda handler.
"""
import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend', 'reviews'))

from reviews.review_request_trigger import handler
from shared.constants import OrderStatus


@pytest.fixture
def mock_dynamodb_stream_event():
    """Create a mock DynamoDB Stream event for order status change to delivered."""
    return {
        'Records': [
            {
                'eventID': '1',
                'eventName': 'MODIFY',
                'eventVersion': '1.1',
                'eventSource': 'aws:dynamodb',
                'dynamodb': {
                    'Keys': {
                        'PK': {'S': 'ORDER#order-123'},
                        'SK': {'S': 'METADATA'}
                    },
                    'NewImage': {
                        'PK': {'S': 'ORDER#order-123'},
                        'SK': {'S': 'METADATA'},
                        'EntityType': {'S': 'Order'},
                        'orderId': {'S': 'order-123'},
                        'consumerId': {'S': 'consumer-456'},
                        'farmerId': {'S': 'farmer-789'},
                        'productId': {'S': 'product-101'},
                        'productName': {'S': 'Organic Tomatoes'},
                        'status': {'S': 'delivered'},
                        'updatedAt': {'S': datetime.utcnow().isoformat()}
                    },
                    'OldImage': {
                        'PK': {'S': 'ORDER#order-123'},
                        'SK': {'S': 'METADATA'},
                        'EntityType': {'S': 'Order'},
                        'orderId': {'S': 'order-123'},
                        'consumerId': {'S': 'consumer-456'},
                        'farmerId': {'S': 'farmer-789'},
                        'productId': {'S': 'product-101'},
                        'productName': {'S': 'Organic Tomatoes'},
                        'status': {'S': 'shipped'},
                        'updatedAt': {'S': (datetime.utcnow() - timedelta(hours=1)).isoformat()}
                    },
                    'SequenceNumber': '111',
                    'SizeBytes': 26,
                    'StreamViewType': 'NEW_AND_OLD_IMAGES'
                }
            }
        ]
    }


@pytest.fixture
def mock_consumer_data():
    """Mock consumer data."""
    return {
        'PK': 'USER#consumer-456',
        'SK': 'PROFILE',
        'EntityType': 'User',
        'userId': 'consumer-456',
        'email': 'consumer@example.com',
        'firstName': 'John',
        'lastName': 'Doe',
        'role': 'consumer',
        'notificationPreferences': {
            'reviewRequests': True,
            'orderUpdates': True
        }
    }


@pytest.fixture
def mock_farmer_data():
    """Mock farmer data."""
    return {
        'PK': 'USER#farmer-789',
        'SK': 'PROFILE',
        'EntityType': 'User',
        'userId': 'farmer-789',
        'email': 'farmer@example.com',
        'firstName': 'Jane',
        'lastName': 'Smith',
        'role': 'farmer',
        'farmerProfile': {
            'farmName': 'Green Valley Farm',
            'farmLocation': 'California'
        }
    }


@pytest.fixture
def lambda_context():
    """Mock Lambda context."""
    context = Mock()
    context.function_name = 'review-request-trigger'
    context.memory_limit_in_mb = 128
    context.invoked_function_arn = 'arn:aws:lambda:us-east-1:123456789012:function:review-request-trigger'
    context.aws_request_id = 'test-request-id'
    return context


class TestReviewRequestTrigger:
    """Test cases for review request email trigger."""
    
    @patch('reviews.review_request_trigger.get_item')
    @patch('reviews.review_request_trigger.get_email_service')
    def test_delivered_order_sends_review_request_email(
        self,
        mock_get_email_service,
        mock_get_item,
        mock_dynamodb_stream_event,
        mock_consumer_data,
        mock_farmer_data,
        lambda_context
    ):
        """Test that changing order status to delivered sends a review request email."""
        # Setup mocks
        def get_item_side_effect(pk, sk):
            if pk == 'USER#consumer-456':
                return mock_consumer_data
            elif pk == 'USER#farmer-789':
                return mock_farmer_data
            return None
        
        mock_get_item.side_effect = get_item_side_effect
        
        mock_email_service = Mock()
        mock_email_service.send_email.return_value = {
            'success': True,
            'message_id': 'test-message-id'
        }
        mock_get_email_service.return_value = mock_email_service
        
        # Execute handler
        response = handler(mock_dynamodb_stream_event, lambda_context)
        
        # Verify response
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['processed'] == 1
        assert body['emails_sent'] == 1
        assert body['errors'] == 0
        
        # Verify email was sent
        mock_email_service.send_email.assert_called_once()
        call_args = mock_email_service.send_email.call_args
        assert call_args[1]['recipient'] == 'consumer@example.com'
        assert 'roottrust' in call_args[1]['subject'].lower()
        assert 'Organic Tomatoes' in call_args[1]['html_body']
        assert 'Green Valley Farm' in call_args[1]['html_body']
        assert 'order-123' in call_args[1]['html_body']
    
    @patch('reviews.review_request_trigger.get_item')
    @patch('reviews.review_request_trigger.get_email_service')
    def test_non_delivered_status_change_does_not_send_email(
        self,
        mock_get_email_service,
        mock_get_item,
        lambda_context
    ):
        """Test that status changes other than to delivered do not trigger emails."""
        event = {
            'Records': [
                {
                    'eventID': '1',
                    'eventName': 'MODIFY',
                    'dynamodb': {
                        'NewImage': {
                            'EntityType': {'S': 'Order'},
                            'orderId': {'S': 'order-123'},
                            'status': {'S': 'shipped'}
                        },
                        'OldImage': {
                            'EntityType': {'S': 'Order'},
                            'orderId': {'S': 'order-123'},
                            'status': {'S': 'processing'}
                        }
                    }
                }
            ]
        }
        
        # Execute handler
        response = handler(event, lambda_context)
        
        # Verify no emails sent
        body = json.loads(response['body'])
        assert body['emails_sent'] == 0
        mock_get_email_service.return_value.send_email.assert_not_called()
    
    @patch('reviews.review_request_trigger.get_item')
    @patch('reviews.review_request_trigger.get_email_service')
    def test_insert_event_does_not_trigger_email(
        self,
        mock_get_email_service,
        mock_get_item,
        lambda_context
    ):
        """Test that INSERT events do not trigger review request emails."""
        event = {
            'Records': [
                {
                    'eventID': '1',
                    'eventName': 'INSERT',
                    'dynamodb': {
                        'NewImage': {
                            'EntityType': {'S': 'Order'},
                            'orderId': {'S': 'order-123'},
                            'status': {'S': 'delivered'}
                        }
                    }
                }
            ]
        }
        
        # Execute handler
        response = handler(event, lambda_context)
        
        # Verify no emails sent
        body = json.loads(response['body'])
        assert body['emails_sent'] == 0
        mock_get_email_service.return_value.send_email.assert_not_called()
    
    @patch('reviews.review_request_trigger.get_item')
    @patch('reviews.review_request_trigger.get_email_service')
    def test_non_order_entity_does_not_trigger_email(
        self,
        mock_get_email_service,
        mock_get_item,
        lambda_context
    ):
        """Test that non-Order entities do not trigger review request emails."""
        event = {
            'Records': [
                {
                    'eventID': '1',
                    'eventName': 'MODIFY',
                    'dynamodb': {
                        'NewImage': {
                            'EntityType': {'S': 'Product'},
                            'productId': {'S': 'product-123'},
                            'status': {'S': 'approved'}
                        },
                        'OldImage': {
                            'EntityType': {'S': 'Product'},
                            'productId': {'S': 'product-123'},
                            'status': {'S': 'pending'}
                        }
                    }
                }
            ]
        }
        
        # Execute handler
        response = handler(event, lambda_context)
        
        # Verify no emails sent
        body = json.loads(response['body'])
        assert body['emails_sent'] == 0
        mock_get_email_service.return_value.send_email.assert_not_called()
    
    @patch('reviews.review_request_trigger.get_item')
    @patch('reviews.review_request_trigger.get_email_service')
    def test_consumer_not_found_does_not_send_email(
        self,
        mock_get_email_service,
        mock_get_item,
        mock_dynamodb_stream_event,
        lambda_context
    ):
        """Test that missing consumer data prevents email from being sent."""
        # Setup mock to return None for consumer
        mock_get_item.return_value = None
        
        # Execute handler
        response = handler(mock_dynamodb_stream_event, lambda_context)
        
        # Verify no emails sent but error recorded
        body = json.loads(response['body'])
        assert body['emails_sent'] == 0
        assert body['errors'] == 1
        mock_get_email_service.return_value.send_email.assert_not_called()
    
    @patch('reviews.review_request_trigger.get_item')
    @patch('reviews.review_request_trigger.get_email_service')
    def test_notification_preferences_disabled_does_not_send_email(
        self,
        mock_get_email_service,
        mock_get_item,
        mock_dynamodb_stream_event,
        mock_consumer_data,
        lambda_context
    ):
        """Test that disabled review request notifications prevent email from being sent."""
        # Modify consumer data to disable review requests
        consumer_data = mock_consumer_data.copy()
        consumer_data['notificationPreferences'] = {
            'reviewRequests': False,
            'orderUpdates': True
        }
        
        mock_get_item.return_value = consumer_data
        
        # Execute handler
        response = handler(mock_dynamodb_stream_event, lambda_context)
        
        # Verify no emails sent
        body = json.loads(response['body'])
        assert body['emails_sent'] == 0
        assert body['processed'] == 1
        mock_get_email_service.return_value.send_email.assert_not_called()
    
    @patch('reviews.review_request_trigger.get_item')
    @patch('reviews.review_request_trigger.get_email_service')
    def test_email_service_failure_records_error(
        self,
        mock_get_email_service,
        mock_get_item,
        mock_dynamodb_stream_event,
        mock_consumer_data,
        mock_farmer_data,
        lambda_context
    ):
        """Test that email service failures are recorded as errors."""
        # Setup mocks
        def get_item_side_effect(pk, sk):
            if pk == 'USER#consumer-456':
                return mock_consumer_data
            elif pk == 'USER#farmer-789':
                return mock_farmer_data
            return None
        
        mock_get_item.side_effect = get_item_side_effect
        
        mock_email_service = Mock()
        mock_email_service.send_email.return_value = {
            'success': False,
            'error_code': 'SES_ERROR',
            'error_message': 'Failed to send email'
        }
        mock_get_email_service.return_value = mock_email_service
        
        # Execute handler
        response = handler(mock_dynamodb_stream_event, lambda_context)
        
        # Verify error recorded
        body = json.loads(response['body'])
        assert body['emails_sent'] == 0
        assert body['errors'] == 1
    
    @patch('reviews.review_request_trigger.get_item')
    @patch('reviews.review_request_trigger.get_email_service')
    def test_multiple_records_processed_correctly(
        self,
        mock_get_email_service,
        mock_get_item,
        mock_consumer_data,
        mock_farmer_data,
        lambda_context
    ):
        """Test that multiple stream records are processed correctly."""
        event = {
            'Records': [
                {
                    'eventID': '1',
                    'eventName': 'MODIFY',
                    'dynamodb': {
                        'NewImage': {
                            'EntityType': {'S': 'Order'},
                            'orderId': {'S': 'order-1'},
                            'consumerId': {'S': 'consumer-456'},
                            'farmerId': {'S': 'farmer-789'},
                            'productId': {'S': 'product-101'},
                            'productName': {'S': 'Product 1'},
                            'status': {'S': 'delivered'}
                        },
                        'OldImage': {
                            'EntityType': {'S': 'Order'},
                            'status': {'S': 'shipped'}
                        }
                    }
                },
                {
                    'eventID': '2',
                    'eventName': 'MODIFY',
                    'dynamodb': {
                        'NewImage': {
                            'EntityType': {'S': 'Order'},
                            'orderId': {'S': 'order-2'},
                            'consumerId': {'S': 'consumer-456'},
                            'farmerId': {'S': 'farmer-789'},
                            'productId': {'S': 'product-102'},
                            'productName': {'S': 'Product 2'},
                            'status': {'S': 'delivered'}
                        },
                        'OldImage': {
                            'EntityType': {'S': 'Order'},
                            'status': {'S': 'shipped'}
                        }
                    }
                }
            ]
        }
        
        # Setup mocks
        def get_item_side_effect(pk, sk):
            if pk == 'USER#consumer-456':
                return mock_consumer_data
            elif pk == 'USER#farmer-789':
                return mock_farmer_data
            return None
        
        mock_get_item.side_effect = get_item_side_effect
        
        mock_email_service = Mock()
        mock_email_service.send_email.return_value = {
            'success': True,
            'message_id': 'test-message-id'
        }
        mock_get_email_service.return_value = mock_email_service
        
        # Execute handler
        response = handler(event, lambda_context)
        
        # Verify both records processed
        body = json.loads(response['body'])
        assert body['processed'] == 2
        assert body['emails_sent'] == 2
        assert body['errors'] == 0
        assert mock_email_service.send_email.call_count == 2
    
    @patch('reviews.review_request_trigger.get_item')
    @patch('reviews.review_request_trigger.get_email_service')
    def test_missing_required_fields_records_error(
        self,
        mock_get_email_service,
        mock_get_item,
        lambda_context
    ):
        """Test that missing required fields in order record are handled gracefully."""
        event = {
            'Records': [
                {
                    'eventID': '1',
                    'eventName': 'MODIFY',
                    'dynamodb': {
                        'NewImage': {
                            'EntityType': {'S': 'Order'},
                            'orderId': {'S': 'order-123'},
                            # Missing consumerId, farmerId, productId, productName
                            'status': {'S': 'delivered'}
                        },
                        'OldImage': {
                            'EntityType': {'S': 'Order'},
                            'status': {'S': 'shipped'}
                        }
                    }
                }
            ]
        }
        
        # Execute handler
        response = handler(event, lambda_context)
        
        # Verify error recorded
        body = json.loads(response['body'])
        assert body['emails_sent'] == 0
        assert body['errors'] == 1
        mock_get_email_service.return_value.send_email.assert_not_called()
    
    @patch('reviews.review_request_trigger.get_item')
    @patch('reviews.review_request_trigger.get_email_service')
    def test_farmer_not_found_uses_default_name(
        self,
        mock_get_email_service,
        mock_get_item,
        mock_dynamodb_stream_event,
        mock_consumer_data,
        lambda_context
    ):
        """Test that missing farmer data uses default farmer name."""
        # Setup mock to return consumer but not farmer
        def get_item_side_effect(pk, sk):
            if pk == 'USER#consumer-456':
                return mock_consumer_data
            return None
        
        mock_get_item.side_effect = get_item_side_effect
        
        mock_email_service = Mock()
        mock_email_service.send_email.return_value = {
            'success': True,
            'message_id': 'test-message-id'
        }
        mock_get_email_service.return_value = mock_email_service
        
        # Execute handler
        response = handler(mock_dynamodb_stream_event, lambda_context)
        
        # Verify email sent with default farmer name
        body = json.loads(response['body'])
        assert body['emails_sent'] == 1
        
        call_args = mock_email_service.send_email.call_args
        assert 'Your Farmer' in call_args[1]['html_body']
    
    @patch('reviews.review_request_trigger.get_item')
    @patch('reviews.review_request_trigger.get_email_service')
    def test_already_delivered_order_does_not_send_duplicate_email(
        self,
        mock_get_email_service,
        mock_get_item,
        lambda_context
    ):
        """Test that orders already in delivered status do not trigger duplicate emails."""
        event = {
            'Records': [
                {
                    'eventID': '1',
                    'eventName': 'MODIFY',
                    'dynamodb': {
                        'NewImage': {
                            'EntityType': {'S': 'Order'},
                            'orderId': {'S': 'order-123'},
                            'status': {'S': 'delivered'}
                        },
                        'OldImage': {
                            'EntityType': {'S': 'Order'},
                            'orderId': {'S': 'order-123'},
                            'status': {'S': 'delivered'}  # Already delivered
                        }
                    }
                }
            ]
        }
        
        # Execute handler
        response = handler(event, lambda_context)
        
        # Verify no emails sent
        body = json.loads(response['body'])
        assert body['emails_sent'] == 0
        mock_get_email_service.return_value.send_email.assert_not_called()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
