"""
Unit tests for followed farmer notification trigger Lambda function.
"""
import json
import pytest
from unittest.mock import Mock, patch, MagicMock


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


def create_mock_scan(items):
    """Helper function to create a mock scan that ignores filter_expression."""
    def mock_scan(**kwargs):
        return {'Items': items}
    return Mock(side_effect=mock_scan)


def test_handler_processes_new_product_insert_event(mock_shared_modules):
    """Test that handler processes INSERT events for new products."""
    from shared.constants import UserRole
    
    # Mock constants
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
    
    # Mock scan to ignore filter_expression parameter
    def mock_scan(**kwargs):
        return {
            'Items': [
                {
                    'EntityType': 'User',  # Add EntityType
                    'email': 'consumer1@example.com',
                    'firstName': 'Alice',
                    'role': 'consumer',
                    'consumerProfile': {
                        'followedFarmers': ['farmer-123']
                    },
                    'notificationPreferences': {
                        'followedFarmers': True
                    }
                },
                {
                    'EntityType': 'User',  # Add EntityType
                    'email': 'consumer2@example.com',
                    'firstName': 'Bob',
                    'role': 'consumer',
                    'consumerProfile': {
                        'followedFarmers': ['farmer-123', 'farmer-456']
                    },
                    'notificationPreferences': {
                        'followedFarmers': True
                    }
                }
            ]
        }
    
    database.scan = Mock(side_effect=mock_scan)
    
    # Mock email service
    from shared import email_service, email_templates
    mock_email_service = Mock()
    mock_email_service.send_email = Mock(return_value={'success': True, 'message_id': 'test-123'})
    email_service.get_email_service = Mock(return_value=mock_email_service)
    
    email_templates.get_followed_farmer_notification_email = Mock(return_value={
        'subject': 'New Product from Farmer',
        'html_body': '<html>Test</html>',
        'text_body': 'Test'
    })
    
    # Import handler AFTER mocks are set up
    from backend.notifications.followed_farmer_trigger import handler
    
    # Create DynamoDB Stream event for INSERT
    event = {
        'Records': [
            {
                'eventName': 'INSERT',
                'dynamodb': {
                    'NewImage': {
                        'EntityType': {'S': 'Product'},
                        'productId': {'S': 'prod-123'},
                        'name': {'S': 'Organic Tomatoes'},
                        'category': {'S': 'vegetables'},
                        'price': {'N': '50.00'},
                        'farmerId': {'S': 'farmer-123'},
                        'description': {'S': 'Fresh organic tomatoes'}
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
    
    # Verify email service was called twice (once for each follower)
    assert mock_email_service.send_email.call_count == 2


def test_handler_ignores_modify_events(mock_shared_modules):
    """Test that handler ignores MODIFY events (only processes INSERT)."""
    from backend.notifications.followed_farmer_trigger import handler
    
    # Create DynamoDB Stream event with MODIFY
    event = {
        'Records': [
            {
                'eventName': 'MODIFY',
                'dynamodb': {
                    'NewImage': {
                        'EntityType': {'S': 'Product'},
                        'productId': {'S': 'prod-123'},
                        'name': {'S': 'Organic Tomatoes'}
                    },
                    'OldImage': {
                        'EntityType': {'S': 'Product'},
                        'productId': {'S': 'prod-123'},
                        'name': {'S': 'Organic Tomatoes'}
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


def test_handler_ignores_non_product_entities(mock_shared_modules):
    """Test that handler ignores non-product entities."""
    from backend.notifications.followed_farmer_trigger import handler
    
    # Create DynamoDB Stream event with non-product entity
    event = {
        'Records': [
            {
                'eventName': 'INSERT',
                'dynamodb': {
                    'NewImage': {
                        'EntityType': {'S': 'Order'},
                        'orderId': {'S': 'order-123'},
                        'status': {'S': 'confirmed'}
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


def test_handler_only_notifies_followers_with_preference_enabled(mock_shared_modules):
    """Test that handler only notifies followers who have followedFarmers preference enabled."""
    from backend.notifications.followed_farmer_trigger import handler
    from shared.constants import UserRole
    
    # Mock constants
    UserRole.CONSUMER = Mock(value='consumer')
    
    # Mock database functions
    from shared import database
    database.get_item = Mock(return_value={
        'email': 'farmer@example.com',
        'firstName': 'John',
        'farmerProfile': {'farmName': 'Green Valley Farm'}
    })
    
    # Return consumers with different preferences
    database.scan = create_mock_scan([
        {
            'EntityType': 'User',  # Add EntityType
            'email': 'consumer1@example.com',
            'firstName': 'Alice',
            'role': 'consumer',
            'consumerProfile': {
                'followedFarmers': ['farmer-123']
            },
            'notificationPreferences': {
                'followedFarmers': True  # Enabled
            }
        },
        {
            'EntityType': 'User',  # Add EntityType
            'email': 'consumer2@example.com',
            'firstName': 'Bob',
            'role': 'consumer',
            'consumerProfile': {
                'followedFarmers': ['farmer-123']
            },
            'notificationPreferences': {
                'followedFarmers': False  # Disabled
            }
        },
        {
            'EntityType': 'User',  # Add EntityType
            'email': 'consumer3@example.com',
            'firstName': 'Charlie',
            'role': 'consumer',
            'consumerProfile': {
                'followedFarmers': ['farmer-456']  # Follows different farmer
            },
            'notificationPreferences': {
                'followedFarmers': True
            }
        }
    ])
    
    # Mock email service
    from shared import email_service, email_templates
    mock_email_service = Mock()
    mock_email_service.send_email = Mock(return_value={'success': True})
    email_service.get_email_service = Mock(return_value=mock_email_service)
    
    email_templates.get_followed_farmer_notification_email = Mock(return_value={
        'subject': 'New Product',
        'html_body': '<html>Test</html>',
        'text_body': 'Test'
    })
    
    # Create DynamoDB Stream event
    event = {
        'Records': [
            {
                'eventName': 'INSERT',
                'dynamodb': {
                    'NewImage': {
                        'EntityType': {'S': 'Product'},
                        'productId': {'S': 'prod-123'},
                        'name': {'S': 'Organic Tomatoes'},
                        'category': {'S': 'vegetables'},
                        'price': {'N': '50.00'},
                        'farmerId': {'S': 'farmer-123'}
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
    assert body['emails_sent'] == 1  # Only consumer1 should receive email
    
    # Verify email service was called once
    assert mock_email_service.send_email.call_count == 1


def test_handler_skips_consumers_not_following_farmer(mock_shared_modules):
    """Test that handler skips consumers who don't follow the farmer."""
    from backend.notifications.followed_farmer_trigger import handler
    from shared.constants import UserRole
    
    # Mock constants
    UserRole.CONSUMER = Mock(value='consumer')
    
    # Mock database functions
    from shared import database
    database.get_item = Mock(return_value={
        'email': 'farmer@example.com',
        'firstName': 'John',
        'farmerProfile': {'farmName': 'Green Valley Farm'}
    })
    
    # Return consumers who don't follow this farmer
    database.scan = Mock(return_value={
        'Items': [
            {
                'email': 'consumer1@example.com',
                'firstName': 'Alice',
                'role': 'consumer',
                'consumerProfile': {
                    'followedFarmers': ['farmer-456', 'farmer-789']  # Different farmers
                },
                'notificationPreferences': {
                    'followedFarmers': True
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
                'eventName': 'INSERT',
                'dynamodb': {
                    'NewImage': {
                        'EntityType': {'S': 'Product'},
                        'productId': {'S': 'prod-123'},
                        'name': {'S': 'Organic Tomatoes'},
                        'category': {'S': 'vegetables'},
                        'price': {'N': '50.00'},
                        'farmerId': {'S': 'farmer-123'}
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
    from backend.notifications.followed_farmer_trigger import handler
    from shared.constants import UserRole
    
    # Mock constants
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
                'consumerProfile': {
                    'followedFarmers': ['farmer-123']
                },
                'notificationPreferences': {
                    'followedFarmers': True,
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
                'eventName': 'INSERT',
                'dynamodb': {
                    'NewImage': {
                        'EntityType': {'S': 'Product'},
                        'productId': {'S': 'prod-123'},
                        'name': {'S': 'Organic Tomatoes'},
                        'category': {'S': 'vegetables'},
                        'price': {'N': '50.00'},
                        'farmerId': {'S': 'farmer-123'}
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
    from backend.notifications.followed_farmer_trigger import handler
    from shared.constants import UserRole
    
    # Mock constants
    UserRole.CONSUMER = Mock(value='consumer')
    
    # Mock database functions
    from shared import database
    database.get_item = Mock(return_value={
        'email': 'farmer@example.com',
        'firstName': 'John',
        'farmerProfile': {'farmName': 'Green Valley Farm'}
    })
    
    database.scan = create_mock_scan([
        {
            'EntityType': 'User',  # Add EntityType
            'email': 'consumer1@example.com',
            'firstName': 'Alice',
            'role': 'consumer',
            'consumerProfile': {'followedFarmers': ['farmer-123']},
            'notificationPreferences': {'followedFarmers': True}
        },
        {
            'EntityType': 'User',  # Add EntityType
            'email': 'consumer2@example.com',
            'firstName': 'Bob',
            'role': 'consumer',
            'consumerProfile': {'followedFarmers': ['farmer-123']},
            'notificationPreferences': {'followedFarmers': True}
        }
    ])
    
    # Mock email service - first call fails, second succeeds
    from shared import email_service, email_templates
    mock_email_service = Mock()
    mock_email_service.send_email = Mock(side_effect=[
        {'success': False, 'error_message': 'Email failed'},
        {'success': True, 'message_id': 'test-123'}
    ])
    email_service.get_email_service = Mock(return_value=mock_email_service)
    
    email_templates.get_followed_farmer_notification_email = Mock(return_value={
        'subject': 'New Product',
        'html_body': '<html>Test</html>',
        'text_body': 'Test'
    })
    
    # Create DynamoDB Stream event
    event = {
        'Records': [
            {
                'eventName': 'INSERT',
                'dynamodb': {
                    'NewImage': {
                        'EntityType': {'S': 'Product'},
                        'productId': {'S': 'prod-123'},
                        'name': {'S': 'Organic Tomatoes'},
                        'category': {'S': 'vegetables'},
                        'price': {'N': '50.00'},
                        'farmerId': {'S': 'farmer-123'}
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
    from backend.notifications.followed_farmer_trigger import handler
    from shared.constants import UserRole
    
    # Mock constants
    UserRole.CONSUMER = Mock(value='consumer')
    
    # Mock database functions - farmer not found
    from shared import database
    database.get_item = Mock(return_value=None)
    
    database.scan = create_mock_scan([
        {
            'EntityType': 'User',  # Add EntityType
            'email': 'consumer@example.com',
            'firstName': 'Alice',
            'role': 'consumer',
            'consumerProfile': {'followedFarmers': ['farmer-123']},
            'notificationPreferences': {'followedFarmers': True}
        }
    ])
    
    # Mock email service
    from shared import email_service, email_templates
    mock_email_service = Mock()
    mock_email_service.send_email = Mock(return_value={'success': True})
    email_service.get_email_service = Mock(return_value=mock_email_service)
    
    email_templates.get_followed_farmer_notification_email = Mock(return_value={
        'subject': 'New Product',
        'html_body': '<html>Test</html>',
        'text_body': 'Test'
    })
    
    # Create DynamoDB Stream event
    event = {
        'Records': [
            {
                'eventName': 'INSERT',
                'dynamodb': {
                    'NewImage': {
                        'EntityType': {'S': 'Product'},
                        'productId': {'S': 'prod-123'},
                        'name': {'S': 'Organic Tomatoes'},
                        'category': {'S': 'vegetables'},
                        'price': {'N': '50.00'},
                        'farmerId': {'S': 'farmer-123'}
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
    call_args = email_templates.get_followed_farmer_notification_email.call_args[1]
    assert call_args['farmer_name'] == 'RootTrust Farmer'


def test_handler_processes_multiple_records(mock_shared_modules):
    """Test that handler processes multiple stream records in batch."""
    from backend.notifications.followed_farmer_trigger import handler
    from shared.constants import UserRole
    
    # Mock constants
    UserRole.CONSUMER = Mock(value='consumer')
    
    # Mock database functions
    from shared import database
    database.get_item = Mock(return_value={
        'email': 'farmer@example.com',
        'firstName': 'John',
        'farmerProfile': {'farmName': 'Green Valley Farm'}
    })
    
    database.scan = create_mock_scan([
        {
            'EntityType': 'User',  # Add EntityType
            'email': 'consumer@example.com',
            'firstName': 'Alice',
            'role': 'consumer',
            'consumerProfile': {'followedFarmers': ['farmer-123']},
            'notificationPreferences': {'followedFarmers': True}
        }
    ])
    
    # Mock email service
    from shared import email_service, email_templates
    mock_email_service = Mock()
    mock_email_service.send_email = Mock(return_value={'success': True})
    email_service.get_email_service = Mock(return_value=mock_email_service)
    
    email_templates.get_followed_farmer_notification_email = Mock(return_value={
        'subject': 'New Product',
        'html_body': '<html>Test</html>',
        'text_body': 'Test'
    })
    
    # Create DynamoDB Stream event with multiple records
    event = {
        'Records': [
            {
                'eventName': 'INSERT',
                'dynamodb': {
                    'NewImage': {
                        'EntityType': {'S': 'Product'},
                        'productId': {'S': 'prod-123'},
                        'name': {'S': 'Organic Tomatoes'},
                        'category': {'S': 'vegetables'},
                        'price': {'N': '50.00'},
                        'farmerId': {'S': 'farmer-123'}
                    }
                }
            },
            {
                'eventName': 'INSERT',
                'dynamodb': {
                    'NewImage': {
                        'EntityType': {'S': 'Product'},
                        'productId': {'S': 'prod-456'},
                        'name': {'S': 'Fresh Apples'},
                        'category': {'S': 'fruits'},
                        'price': {'N': '80.00'},
                        'farmerId': {'S': 'farmer-123'}
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


def test_handler_handles_missing_required_fields(mock_shared_modules):
    """Test that handler handles missing required fields gracefully."""
    from backend.notifications.followed_farmer_trigger import handler
    
    # Create DynamoDB Stream event with missing fields
    event = {
        'Records': [
            {
                'eventName': 'INSERT',
                'dynamodb': {
                    'NewImage': {
                        'EntityType': {'S': 'Product'},
                        'productId': {'S': 'prod-123'},
                        # Missing name, category, price, farmerId
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
    assert body['errors'] == 1


def test_handler_handles_consumer_without_email(mock_shared_modules):
    """Test that handler skips consumers without email addresses."""
    from backend.notifications.followed_farmer_trigger import handler
    from shared.constants import UserRole
    
    # Mock constants
    UserRole.CONSUMER = Mock(value='consumer')
    
    # Mock database functions
    from shared import database
    database.get_item = Mock(return_value={
        'email': 'farmer@example.com',
        'firstName': 'John',
        'farmerProfile': {'farmName': 'Green Valley Farm'}
    })
    
    # Return consumer without email
    database.scan = Mock(return_value={
        'Items': [
            {
                # Missing email field
                'firstName': 'Alice',
                'role': 'consumer',
                'consumerProfile': {'followedFarmers': ['farmer-123']},
                'notificationPreferences': {'followedFarmers': True}
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
                'eventName': 'INSERT',
                'dynamodb': {
                    'NewImage': {
                        'EntityType': {'S': 'Product'},
                        'productId': {'S': 'prod-123'},
                        'name': {'S': 'Organic Tomatoes'},
                        'category': {'S': 'vegetables'},
                        'price': {'N': '50.00'},
                        'farmerId': {'S': 'farmer-123'}
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


def test_handler_handles_empty_followed_farmers_list(mock_shared_modules):
    """Test that handler handles consumers with empty followedFarmers list."""
    from backend.notifications.followed_farmer_trigger import handler
    from shared.constants import UserRole
    
    # Mock constants
    UserRole.CONSUMER = Mock(value='consumer')
    
    # Mock database functions
    from shared import database
    database.get_item = Mock(return_value={
        'email': 'farmer@example.com',
        'firstName': 'John',
        'farmerProfile': {'farmName': 'Green Valley Farm'}
    })
    
    # Return consumer with empty followedFarmers
    database.scan = Mock(return_value={
        'Items': [
            {
                'email': 'consumer@example.com',
                'firstName': 'Alice',
                'role': 'consumer',
                'consumerProfile': {
                    'followedFarmers': []  # Empty list
                },
                'notificationPreferences': {'followedFarmers': True}
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
                'eventName': 'INSERT',
                'dynamodb': {
                    'NewImage': {
                        'EntityType': {'S': 'Product'},
                        'productId': {'S': 'prod-123'},
                        'name': {'S': 'Organic Tomatoes'},
                        'category': {'S': 'vegetables'},
                        'price': {'N': '50.00'},
                        'farmerId': {'S': 'farmer-123'}
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


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
