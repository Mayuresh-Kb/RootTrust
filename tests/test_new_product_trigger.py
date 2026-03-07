"""
Unit tests for new product notification trigger Lambda function.
"""
import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal


# Mock the shared modules before importing the handler
@pytest.fixture(autouse=True)
def mock_shared_modules():
    """Mock shared modules for all tests."""
    with patch.dict('sys.modules', {
        'shared': MagicMock(),
        'shared.database': MagicMock(),
        'shared.email_service': MagicMock(),
        'shared.email_templates': MagicMock(),
        'shared.constants': MagicMock(),
    }):
        yield


def test_handler_processes_product_approval_event(mock_shared_modules):
    """Test that handler processes product status change from pending to approved."""
    from backend.notifications.new_product_trigger import handler
    from shared.constants import VerificationStatus, UserRole
    
    # Mock constants
    VerificationStatus.APPROVED = Mock(value='approved')
    VerificationStatus.PENDING = Mock(value='pending')
    UserRole.CONSUMER = Mock(value='consumer')
    
    # Mock database functions
    from shared import database
    database.get_item = Mock(return_value={
        'email': 'farmer@example.com',
        'firstName': 'John',
        'lastName': 'Farmer',
        'farmerProfile': {
            'farmName': 'Green Valley Farm'
        }
    })
    
    database.scan = Mock(return_value={
        'Items': [
            {
                'email': 'consumer1@example.com',
                'firstName': 'Alice',
                'role': 'consumer',
                'notificationPreferences': {
                    'newProducts': True
                }
            },
            {
                'email': 'consumer2@example.com',
                'firstName': 'Bob',
                'role': 'consumer',
                'notificationPreferences': {
                    'newProducts': True
                }
            }
        ]
    })
    
    # Mock email service
    from shared import email_service, email_templates
    mock_email_service = Mock()
    mock_email_service.send_email = Mock(return_value={'success': True, 'message_id': 'test-123'})
    email_service.get_email_service = Mock(return_value=mock_email_service)
    
    email_templates.get_new_product_notification_email = Mock(return_value={
        'subject': 'New Product Available',
        'html_body': '<html>Test</html>',
        'text_body': 'Test'
    })
    
    # Create DynamoDB Stream event
    event = {
        'Records': [
            {
                'eventName': 'MODIFY',
                'dynamodb': {
                    'NewImage': {
                        'EntityType': {'S': 'Product'},
                        'productId': {'S': 'prod-123'},
                        'name': {'S': 'Organic Tomatoes'},
                        'category': {'S': 'vegetables'},
                        'price': {'N': '50.00'},
                        'farmerId': {'S': 'farmer-123'},
                        'description': {'S': 'Fresh organic tomatoes'},
                        'verificationStatus': {'S': 'approved'}
                    },
                    'OldImage': {
                        'EntityType': {'S': 'Product'},
                        'productId': {'S': 'prod-123'},
                        'verificationStatus': {'S': 'pending'}
                    }
                }
            }
        ]
    }
    
    # Call handler
    result = handler(event, None)
    
    # Verify result
    assert result['statusCode'] == 200
    body = json.loads(result['body'])
    assert body['processed'] == 1
    assert body['emails_sent'] == 2
    assert body['errors'] == 0
    
    # Verify email service was called twice (once for each consumer)
    assert mock_email_service.send_email.call_count == 2


def test_handler_ignores_non_product_entities(mock_shared_modules):
    """Test that handler ignores non-product entities."""
    from backend.notifications.new_product_trigger import handler
    
    # Create DynamoDB Stream event with non-product entity
    event = {
        'Records': [
            {
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
                        'status': {'S': 'shipped'}
                    }
                }
            }
        ]
    }
    
    # Call handler
    result = handler(event, None)
    
    # Verify result
    assert result['statusCode'] == 200
    body = json.loads(result['body'])
    assert body['processed'] == 0
    assert body['emails_sent'] == 0


def test_handler_ignores_insert_events(mock_shared_modules):
    """Test that handler ignores INSERT events (only processes MODIFY)."""
    from backend.notifications.new_product_trigger import handler
    
    # Create DynamoDB Stream event with INSERT
    event = {
        'Records': [
            {
                'eventName': 'INSERT',
                'dynamodb': {
                    'NewImage': {
                        'EntityType': {'S': 'Product'},
                        'productId': {'S': 'prod-123'},
                        'verificationStatus': {'S': 'approved'}
                    }
                }
            }
        ]
    }
    
    # Call handler
    result = handler(event, None)
    
    # Verify result
    assert result['statusCode'] == 200
    body = json.loads(result['body'])
    assert body['processed'] == 0


def test_handler_ignores_status_change_not_pending_to_approved(mock_shared_modules):
    """Test that handler ignores status changes that are not pending to approved."""
    from backend.notifications.new_product_trigger import handler
    from shared.constants import VerificationStatus
    
    # Mock constants
    VerificationStatus.APPROVED = Mock(value='approved')
    VerificationStatus.PENDING = Mock(value='pending')
    VerificationStatus.FLAGGED = Mock(value='flagged')
    
    # Create DynamoDB Stream event with flagged to approved change
    event = {
        'Records': [
            {
                'eventName': 'MODIFY',
                'dynamodb': {
                    'NewImage': {
                        'EntityType': {'S': 'Product'},
                        'productId': {'S': 'prod-123'},
                        'verificationStatus': {'S': 'approved'}
                    },
                    'OldImage': {
                        'EntityType': {'S': 'Product'},
                        'productId': {'S': 'prod-123'},
                        'verificationStatus': {'S': 'flagged'}
                    }
                }
            }
        ]
    }
    
    # Call handler
    result = handler(event, None)
    
    # Verify result
    assert result['statusCode'] == 200
    body = json.loads(result['body'])
    assert body['processed'] == 0


def test_handler_skips_consumers_without_new_products_preference(mock_shared_modules):
    """Test that handler skips consumers who haven't opted in to new product notifications."""
    from backend.notifications.new_product_trigger import handler
    from shared.constants import VerificationStatus, UserRole
    
    # Mock constants
    VerificationStatus.APPROVED = Mock(value='approved')
    VerificationStatus.PENDING = Mock(value='pending')
    UserRole.CONSUMER = Mock(value='consumer')
    
    # Mock database functions
    from shared import database
    database.get_item = Mock(return_value={
        'email': 'farmer@example.com',
        'firstName': 'John',
        'farmerProfile': {'farmName': 'Green Valley Farm'}
    })
    
    # Return consumers with newProducts=false
    database.scan = Mock(return_value={
        'Items': []  # No consumers with newProducts=true
    })
    
    # Mock email service
    from shared import email_service
    mock_email_service = Mock()
    mock_email_service.send_email = Mock(return_value={'success': True})
    email_service.get_email_service = Mock(return_value=mock_email_service)
    
    # Create DynamoDB Stream event
    event = {
        'Records': [
            {
                'eventName': 'MODIFY',
                'dynamodb': {
                    'NewImage': {
                        'EntityType': {'S': 'Product'},
                        'productId': {'S': 'prod-123'},
                        'name': {'S': 'Organic Tomatoes'},
                        'category': {'S': 'vegetables'},
                        'price': {'N': '50.00'},
                        'farmerId': {'S': 'farmer-123'},
                        'verificationStatus': {'S': 'approved'}
                    },
                    'OldImage': {
                        'EntityType': {'S': 'Product'},
                        'verificationStatus': {'S': 'pending'}
                    }
                }
            }
        ]
    }
    
    # Call handler
    result = handler(event, None)
    
    # Verify result
    assert result['statusCode'] == 200
    body = json.loads(result['body'])
    assert body['processed'] == 1
    assert body['emails_sent'] == 0
    
    # Verify email service was not called
    assert mock_email_service.send_email.call_count == 0


def test_handler_skips_unsubscribed_consumers(mock_shared_modules):
    """Test that handler skips consumers who have unsubscribed."""
    from backend.notifications.new_product_trigger import handler
    from shared.constants import VerificationStatus, UserRole
    
    # Mock constants
    VerificationStatus.APPROVED = Mock(value='approved')
    VerificationStatus.PENDING = Mock(value='pending')
    UserRole.CONSUMER = Mock(value='consumer')
    
    # Mock database functions
    from shared import database
    database.get_item = Mock(return_value={
        'email': 'farmer@example.com',
        'firstName': 'John',
        'farmerProfile': {'farmName': 'Green Valley Farm'}
    })
    
    # Return consumer with unsubscribedAt set
    database.scan = Mock(return_value={
        'Items': [
            {
                'email': 'consumer@example.com',
                'firstName': 'Alice',
                'role': 'consumer',
                'notificationPreferences': {
                    'newProducts': True,
                    'unsubscribedAt': '2024-01-01T00:00:00Z'
                }
            }
        ]
    })
    
    # Mock email service
    from shared import email_service
    mock_email_service = Mock()
    mock_email_service.send_email = Mock(return_value={'success': True})
    email_service.get_email_service = Mock(return_value=mock_email_service)
    
    # Create DynamoDB Stream event
    event = {
        'Records': [
            {
                'eventName': 'MODIFY',
                'dynamodb': {
                    'NewImage': {
                        'EntityType': {'S': 'Product'},
                        'productId': {'S': 'prod-123'},
                        'name': {'S': 'Organic Tomatoes'},
                        'category': {'S': 'vegetables'},
                        'price': {'N': '50.00'},
                        'farmerId': {'S': 'farmer-123'},
                        'verificationStatus': {'S': 'approved'}
                    },
                    'OldImage': {
                        'EntityType': {'S': 'Product'},
                        'verificationStatus': {'S': 'pending'}
                    }
                }
            }
        ]
    }
    
    # Call handler
    result = handler(event, None)
    
    # Verify result
    assert result['statusCode'] == 200
    body = json.loads(result['body'])
    assert body['emails_sent'] == 0
    
    # Verify email service was not called
    assert mock_email_service.send_email.call_count == 0


def test_handler_continues_on_individual_email_failure(mock_shared_modules):
    """Test that handler continues processing other consumers if one email fails."""
    from backend.notifications.new_product_trigger import handler
    from shared.constants import VerificationStatus, UserRole
    
    # Mock constants
    VerificationStatus.APPROVED = Mock(value='approved')
    VerificationStatus.PENDING = Mock(value='pending')
    UserRole.CONSUMER = Mock(value='consumer')
    
    # Mock database functions
    from shared import database
    database.get_item = Mock(return_value={
        'email': 'farmer@example.com',
        'firstName': 'John',
        'farmerProfile': {'farmName': 'Green Valley Farm'}
    })
    
    database.scan = Mock(return_value={
        'Items': [
            {
                'email': 'consumer1@example.com',
                'firstName': 'Alice',
                'role': 'consumer',
                'notificationPreferences': {'newProducts': True}
            },
            {
                'email': 'consumer2@example.com',
                'firstName': 'Bob',
                'role': 'consumer',
                'notificationPreferences': {'newProducts': True}
            }
        ]
    })
    
    # Mock email service - first call fails, second succeeds
    from shared import email_service, email_templates
    mock_email_service = Mock()
    mock_email_service.send_email = Mock(side_effect=[
        {'success': False, 'error_message': 'Email failed'},
        {'success': True, 'message_id': 'test-123'}
    ])
    email_service.get_email_service = Mock(return_value=mock_email_service)
    
    email_templates.get_new_product_notification_email = Mock(return_value={
        'subject': 'New Product Available',
        'html_body': '<html>Test</html>',
        'text_body': 'Test'
    })
    
    # Create DynamoDB Stream event
    event = {
        'Records': [
            {
                'eventName': 'MODIFY',
                'dynamodb': {
                    'NewImage': {
                        'EntityType': {'S': 'Product'},
                        'productId': {'S': 'prod-123'},
                        'name': {'S': 'Organic Tomatoes'},
                        'category': {'S': 'vegetables'},
                        'price': {'N': '50.00'},
                        'farmerId': {'S': 'farmer-123'},
                        'verificationStatus': {'S': 'approved'}
                    },
                    'OldImage': {
                        'EntityType': {'S': 'Product'},
                        'verificationStatus': {'S': 'pending'}
                    }
                }
            }
        ]
    }
    
    # Call handler
    result = handler(event, None)
    
    # Verify result
    assert result['statusCode'] == 200
    body = json.loads(result['body'])
    assert body['processed'] == 1
    assert body['emails_sent'] == 1  # Only one succeeded
    
    # Verify email service was called twice
    assert mock_email_service.send_email.call_count == 2


def test_handler_handles_missing_farmer_gracefully(mock_shared_modules):
    """Test that handler uses default farmer name if farmer not found."""
    from backend.notifications.new_product_trigger import handler
    from shared.constants import VerificationStatus, UserRole
    
    # Mock constants
    VerificationStatus.APPROVED = Mock(value='approved')
    VerificationStatus.PENDING = Mock(value='pending')
    UserRole.CONSUMER = Mock(value='consumer')
    
    # Mock database functions - farmer not found
    from shared import database
    database.get_item = Mock(return_value=None)
    
    database.scan = Mock(return_value={
        'Items': [
            {
                'email': 'consumer@example.com',
                'firstName': 'Alice',
                'role': 'consumer',
                'notificationPreferences': {'newProducts': True}
            }
        ]
    })
    
    # Mock email service
    from shared import email_service, email_templates
    mock_email_service = Mock()
    mock_email_service.send_email = Mock(return_value={'success': True})
    email_service.get_email_service = Mock(return_value=mock_email_service)
    
    email_templates.get_new_product_notification_email = Mock(return_value={
        'subject': 'New Product Available',
        'html_body': '<html>Test</html>',
        'text_body': 'Test'
    })
    
    # Create DynamoDB Stream event
    event = {
        'Records': [
            {
                'eventName': 'MODIFY',
                'dynamodb': {
                    'NewImage': {
                        'EntityType': {'S': 'Product'},
                        'productId': {'S': 'prod-123'},
                        'name': {'S': 'Organic Tomatoes'},
                        'category': {'S': 'vegetables'},
                        'price': {'N': '50.00'},
                        'farmerId': {'S': 'farmer-123'},
                        'verificationStatus': {'S': 'approved'}
                    },
                    'OldImage': {
                        'EntityType': {'S': 'Product'},
                        'verificationStatus': {'S': 'pending'}
                    }
                }
            }
        ]
    }
    
    # Call handler
    result = handler(event, None)
    
    # Verify result
    assert result['statusCode'] == 200
    body = json.loads(result['body'])
    assert body['processed'] == 1
    assert body['emails_sent'] == 1
    
    # Verify email template was called with default farmer name
    call_args = email_templates.get_new_product_notification_email.call_args[1]
    assert call_args['farmer_name'] == 'RootTrust Farmer'


def test_handler_processes_multiple_records(mock_shared_modules):
    """Test that handler processes multiple stream records in batch."""
    from backend.notifications.new_product_trigger import handler
    from shared.constants import VerificationStatus, UserRole
    
    # Mock constants
    VerificationStatus.APPROVED = Mock(value='approved')
    VerificationStatus.PENDING = Mock(value='pending')
    UserRole.CONSUMER = Mock(value='consumer')
    
    # Mock database functions
    from shared import database
    database.get_item = Mock(return_value={
        'email': 'farmer@example.com',
        'firstName': 'John',
        'farmerProfile': {'farmName': 'Green Valley Farm'}
    })
    
    database.scan = Mock(return_value={
        'Items': [
            {
                'email': 'consumer@example.com',
                'firstName': 'Alice',
                'role': 'consumer',
                'notificationPreferences': {'newProducts': True}
            }
        ]
    })
    
    # Mock email service
    from shared import email_service, email_templates
    mock_email_service = Mock()
    mock_email_service.send_email = Mock(return_value={'success': True})
    email_service.get_email_service = Mock(return_value=mock_email_service)
    
    email_templates.get_new_product_notification_email = Mock(return_value={
        'subject': 'New Product Available',
        'html_body': '<html>Test</html>',
        'text_body': 'Test'
    })
    
    # Create DynamoDB Stream event with multiple records
    event = {
        'Records': [
            {
                'eventName': 'MODIFY',
                'dynamodb': {
                    'NewImage': {
                        'EntityType': {'S': 'Product'},
                        'productId': {'S': 'prod-123'},
                        'name': {'S': 'Organic Tomatoes'},
                        'category': {'S': 'vegetables'},
                        'price': {'N': '50.00'},
                        'farmerId': {'S': 'farmer-123'},
                        'verificationStatus': {'S': 'approved'}
                    },
                    'OldImage': {
                        'EntityType': {'S': 'Product'},
                        'verificationStatus': {'S': 'pending'}
                    }
                }
            },
            {
                'eventName': 'MODIFY',
                'dynamodb': {
                    'NewImage': {
                        'EntityType': {'S': 'Product'},
                        'productId': {'S': 'prod-456'},
                        'name': {'S': 'Fresh Apples'},
                        'category': {'S': 'fruits'},
                        'price': {'N': '80.00'},
                        'farmerId': {'S': 'farmer-456'},
                        'verificationStatus': {'S': 'approved'}
                    },
                    'OldImage': {
                        'EntityType': {'S': 'Product'},
                        'verificationStatus': {'S': 'pending'}
                    }
                }
            }
        ]
    }
    
    # Call handler
    result = handler(event, None)
    
    # Verify result
    assert result['statusCode'] == 200
    body = json.loads(result['body'])
    assert body['processed'] == 2
    assert body['emails_sent'] == 2  # One email per product
