"""
Unit tests for limited release creation endpoint.
Tests POST /limited-releases functionality.
"""
import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend', 'limited_releases'))

from create_limited_release import handler, get_subscribers_for_limited_releases, send_limited_release_notifications


@pytest.fixture
def mock_env(monkeypatch):
    """Set up environment variables."""
    monkeypatch.setenv('DYNAMODB_TABLE_NAME', 'RootTrustData')
    monkeypatch.setenv('AWS_REGION', 'us-east-1')
    monkeypatch.setenv('SENDER_EMAIL', 'noreply@roottrust.com')


@pytest.fixture
def valid_token():
    """Mock valid JWT token."""
    return "Bearer valid.jwt.token"


@pytest.fixture
def farmer_user_info():
    """Mock farmer user info from token."""
    return {
        'userId': 'farmer-123',
        'role': 'farmer',
        'email': 'farmer@example.com'
    }


@pytest.fixture
def valid_release_request():
    """Valid limited release creation request."""
    return {
        'productId': 'product-456',
        'releaseName': 'Spring Harvest Special',
        'quantityLimit': 50,
        'duration': 7
    }


@pytest.fixture
def mock_product():
    """Mock product from database."""
    return {
        'PK': 'PRODUCT#product-456',
        'SK': 'METADATA',
        'productId': 'product-456',
        'farmerId': 'farmer-123',
        'name': 'Organic Tomatoes',
        'category': 'vegetables',
        'price': 150.0,
        'verificationStatus': 'approved'
    }


@pytest.fixture
def mock_farmer():
    """Mock farmer profile from database."""
    return {
        'PK': 'USER#farmer-123',
        'SK': 'PROFILE',
        'userId': 'farmer-123',
        'email': 'farmer@example.com',
        'firstName': 'John',
        'lastName': 'Farmer',
        'role': 'farmer',
        'farmerProfile': {
            'farmName': 'Green Valley Farm',
            'farmLocation': 'Karnataka'
        }
    }


@pytest.fixture
def mock_subscribers():
    """Mock list of subscribers."""
    return [
        {
            'PK': 'USER#consumer-1',
            'userId': 'consumer-1',
            'email': 'consumer1@example.com',
            'firstName': 'Alice',
            'notificationPreferences': {
                'limitedReleases': True
            }
        },
        {
            'PK': 'USER#consumer-2',
            'userId': 'consumer-2',
            'email': 'consumer2@example.com',
            'firstName': 'Bob',
            'notificationPreferences': {
                'limitedReleases': True
            }
        }
    ]


class TestLimitedReleaseCreation:
    """Test cases for limited release creation endpoint."""
    
    @patch('create_limited_release.get_user_from_token')
    @patch('create_limited_release.get_item')
    @patch('create_limited_release.put_item')
    @patch('create_limited_release.query')
    @patch('shared.database.update_item')
    @patch('create_limited_release.get_email_service')
    def test_create_limited_release_success(
        self,
        mock_email_service,
        mock_update_item,
        mock_query,
        mock_put_item,
        mock_get_item,
        mock_get_user,
        mock_env,
        valid_token,
        farmer_user_info,
        valid_release_request,
        mock_product,
        mock_farmer,
        mock_subscribers
    ):
        """Test successful limited release creation."""
        # Setup mocks
        mock_get_user.return_value = farmer_user_info
        
        def get_item_side_effect(pk, sk):
            if pk.startswith('PRODUCT#'):
                return mock_product
            elif pk.startswith('USER#'):
                return mock_farmer
            return None
        
        mock_get_item.side_effect = get_item_side_effect
        mock_put_item.return_value = {}
        mock_query.return_value = {'Items': mock_subscribers}
        mock_update_item.return_value = {}
        
        # Mock email service
        mock_email = MagicMock()
        mock_email.send_email.return_value = {'success': True, 'message_id': 'msg-123'}
        mock_email_service.return_value = mock_email
        
        # Create event
        event = {
            'headers': {'Authorization': valid_token},
            'body': json.dumps(valid_release_request)
        }
        
        # Execute handler
        response = handler(event, {})
        
        # Assertions
        assert response['statusCode'] == 201
        body = json.loads(response['body'])
        assert 'releaseId' in body
        assert 'startDate' in body
        assert 'endDate' in body
        assert body['status'] == 'active'
        assert body['message'] == 'Limited release created successfully'
        
        # Verify put_item was called
        mock_put_item.assert_called_once()
        stored_item = mock_put_item.call_args[0][0]
        assert stored_item['PK'].startswith('LIMITED_RELEASE#')
        assert stored_item['SK'] == 'METADATA'
        assert stored_item['farmerId'] == 'farmer-123'
        assert stored_item['productId'] == 'product-456'
        assert stored_item['releaseName'] == 'Spring Harvest Special'
        assert stored_item['quantityLimit'] == 50
        assert stored_item['quantityRemaining'] == 50
        assert stored_item['duration'] == 7
        assert stored_item['status'] == 'active'
        
        # Verify GSI keys
        assert stored_item['GSI2PK'] == 'FARMER#farmer-123'
        assert stored_item['GSI3PK'] == 'STATUS#active'
        assert stored_item['GSI3SK'].startswith('RELEASE#')
    
    @patch('create_limited_release.get_user_from_token')
    def test_missing_authorization_header(self, mock_get_user, mock_env):
        """Test request without authorization header."""
        event = {
            'headers': {},
            'body': json.dumps({'productId': 'product-456'})
        }
        
        response = handler(event, {})
        
        assert response['statusCode'] == 401
        body = json.loads(response['body'])
        assert body['error']['code'] == 'UNAUTHORIZED'
    
    @patch('create_limited_release.get_user_from_token')
    def test_invalid_token(self, mock_get_user, mock_env):
        """Test request with invalid JWT token."""
        mock_get_user.side_effect = Exception("Invalid token")
        
        event = {
            'headers': {'Authorization': 'Bearer invalid.token'},
            'body': json.dumps({'productId': 'product-456'})
        }
        
        response = handler(event, {})
        
        assert response['statusCode'] == 401
        body = json.loads(response['body'])
        assert body['error']['code'] == 'INVALID_TOKEN'
    
    @patch('create_limited_release.get_user_from_token')
    def test_consumer_role_forbidden(self, mock_get_user, mock_env):
        """Test that consumers cannot create limited releases."""
        mock_get_user.return_value = {
            'userId': 'consumer-123',
            'role': 'consumer',
            'email': 'consumer@example.com'
        }
        
        event = {
            'headers': {'Authorization': 'Bearer valid.token'},
            'body': json.dumps({'productId': 'product-456'})
        }
        
        response = handler(event, {})
        
        assert response['statusCode'] == 403
        body = json.loads(response['body'])
        assert body['error']['code'] == 'FORBIDDEN'
        assert 'farmers' in body['error']['message'].lower()
    
    @patch('create_limited_release.get_user_from_token')
    def test_invalid_json_body(self, mock_get_user, mock_env, farmer_user_info):
        """Test request with invalid JSON body."""
        mock_get_user.return_value = farmer_user_info
        
        event = {
            'headers': {'Authorization': 'Bearer valid.token'},
            'body': 'invalid json'
        }
        
        response = handler(event, {})
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error']['code'] == 'INVALID_JSON'
    
    @patch('create_limited_release.get_user_from_token')
    def test_validation_error_missing_fields(self, mock_get_user, mock_env, farmer_user_info):
        """Test validation error for missing required fields."""
        mock_get_user.return_value = farmer_user_info
        
        event = {
            'headers': {'Authorization': 'Bearer valid.token'},
            'body': json.dumps({
                'productId': 'product-456'
                # Missing releaseName, quantityLimit, duration
            })
        }
        
        response = handler(event, {})
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error']['code'] == 'VALIDATION_ERROR'
    
    @patch('create_limited_release.get_user_from_token')
    def test_validation_error_negative_quantity(self, mock_get_user, mock_env, farmer_user_info):
        """Test validation error for non-positive quantity limit."""
        mock_get_user.return_value = farmer_user_info
        
        event = {
            'headers': {'Authorization': 'Bearer valid.token'},
            'body': json.dumps({
                'productId': 'product-456',
                'releaseName': 'Test Release',
                'quantityLimit': -10,  # Invalid: negative
                'duration': 7
            })
        }
        
        response = handler(event, {})
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error']['code'] == 'VALIDATION_ERROR'
    
    @patch('create_limited_release.get_user_from_token')
    def test_validation_error_zero_quantity(self, mock_get_user, mock_env, farmer_user_info):
        """Test validation error for zero quantity limit."""
        mock_get_user.return_value = farmer_user_info
        
        event = {
            'headers': {'Authorization': 'Bearer valid.token'},
            'body': json.dumps({
                'productId': 'product-456',
                'releaseName': 'Test Release',
                'quantityLimit': 0,  # Invalid: zero
                'duration': 7
            })
        }
        
        response = handler(event, {})
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error']['code'] == 'VALIDATION_ERROR'
    
    @patch('create_limited_release.get_user_from_token')
    def test_validation_error_duration_too_short(self, mock_get_user, mock_env, farmer_user_info):
        """Test validation error for duration less than 1 day."""
        mock_get_user.return_value = farmer_user_info
        
        event = {
            'headers': {'Authorization': 'Bearer valid.token'},
            'body': json.dumps({
                'productId': 'product-456',
                'releaseName': 'Test Release',
                'quantityLimit': 50,
                'duration': 0  # Invalid: less than 1
            })
        }
        
        response = handler(event, {})
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error']['code'] == 'VALIDATION_ERROR'
    
    @patch('create_limited_release.get_user_from_token')
    def test_validation_error_duration_too_long(self, mock_get_user, mock_env, farmer_user_info):
        """Test validation error for duration greater than 30 days."""
        mock_get_user.return_value = farmer_user_info
        
        event = {
            'headers': {'Authorization': 'Bearer valid.token'},
            'body': json.dumps({
                'productId': 'product-456',
                'releaseName': 'Test Release',
                'quantityLimit': 50,
                'duration': 31  # Invalid: greater than 30
            })
        }
        
        response = handler(event, {})
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error']['code'] == 'VALIDATION_ERROR'
    
    @patch('create_limited_release.get_user_from_token')
    @patch('create_limited_release.get_item')
    def test_product_not_found(self, mock_get_item, mock_get_user, mock_env, farmer_user_info, valid_release_request):
        """Test error when product doesn't exist."""
        mock_get_user.return_value = farmer_user_info
        mock_get_item.return_value = None  # Product not found
        
        event = {
            'headers': {'Authorization': 'Bearer valid.token'},
            'body': json.dumps(valid_release_request)
        }
        
        response = handler(event, {})
        
        assert response['statusCode'] == 404
        body = json.loads(response['body'])
        assert body['error']['code'] == 'NOT_FOUND'
        assert 'product' in body['error']['message'].lower()
    
    @patch('create_limited_release.get_user_from_token')
    @patch('create_limited_release.get_item')
    def test_farmer_does_not_own_product(
        self,
        mock_get_item,
        mock_get_user,
        mock_env,
        farmer_user_info,
        valid_release_request,
        mock_product
    ):
        """Test error when farmer tries to create release for another farmer's product."""
        mock_get_user.return_value = farmer_user_info
        
        # Product belongs to different farmer
        different_farmer_product = mock_product.copy()
        different_farmer_product['farmerId'] = 'different-farmer-789'
        mock_get_item.return_value = different_farmer_product
        
        event = {
            'headers': {'Authorization': 'Bearer valid.token'},
            'body': json.dumps(valid_release_request)
        }
        
        response = handler(event, {})
        
        assert response['statusCode'] == 403
        body = json.loads(response['body'])
        assert body['error']['code'] == 'FORBIDDEN'
        assert 'own products' in body['error']['message'].lower()
    
    @patch('create_limited_release.get_user_from_token')
    @patch('create_limited_release.get_item')
    @patch('create_limited_release.put_item')
    @patch('create_limited_release.query')
    @patch('shared.database.update_item')
    @patch('create_limited_release.get_email_service')
    def test_notifications_sent_to_subscribers(
        self,
        mock_email_service,
        mock_update_item,
        mock_query,
        mock_put_item,
        mock_get_item,
        mock_get_user,
        mock_env,
        farmer_user_info,
        valid_release_request,
        mock_product,
        mock_farmer,
        mock_subscribers
    ):
        """Test that email notifications are sent to subscribers."""
        # Setup mocks
        mock_get_user.return_value = farmer_user_info
        
        def get_item_side_effect(pk, sk):
            if pk.startswith('PRODUCT#'):
                return mock_product
            elif pk.startswith('USER#'):
                return mock_farmer
            return None
        
        mock_get_item.side_effect = get_item_side_effect
        mock_put_item.return_value = {}
        mock_query.return_value = {'Items': mock_subscribers}
        mock_update_item.return_value = {}
        
        # Mock email service
        mock_email = MagicMock()
        mock_email.send_email.return_value = {'success': True, 'message_id': 'msg-123'}
        mock_email_service.return_value = mock_email
        
        # Create event
        event = {
            'headers': {'Authorization': 'Bearer valid.token'},
            'body': json.dumps(valid_release_request)
        }
        
        # Execute handler
        response = handler(event, {})
        
        # Assertions
        assert response['statusCode'] == 201
        
        # Verify email service was called for each subscriber
        assert mock_email.send_email.call_count == len(mock_subscribers)
        
        # Verify update_item was called to mark notifications as sent
        mock_update_item.assert_called_once()
        update_call = mock_update_item.call_args
        assert 'subscriberNotificationsSent' in update_call[1]['update_expression']
    
    @patch('create_limited_release.get_user_from_token')
    @patch('create_limited_release.get_item')
    @patch('create_limited_release.put_item')
    def test_database_error_handling(
        self,
        mock_put_item,
        mock_get_item,
        mock_get_user,
        mock_env,
        farmer_user_info,
        valid_release_request,
        mock_product,
        mock_farmer
    ):
        """Test error handling when database operation fails."""
        mock_get_user.return_value = farmer_user_info
        
        def get_item_side_effect(pk, sk):
            if pk.startswith('PRODUCT#'):
                return mock_product
            elif pk.startswith('USER#'):
                return mock_farmer
            return None
        
        mock_get_item.side_effect = get_item_side_effect
        mock_put_item.side_effect = Exception("DynamoDB error")
        
        event = {
            'headers': {'Authorization': 'Bearer valid.token'},
            'body': json.dumps(valid_release_request)
        }
        
        response = handler(event, {})
        
        assert response['statusCode'] == 503
        body = json.loads(response['body'])
        assert body['error']['code'] == 'SERVICE_UNAVAILABLE'


class TestSubscriberQuery:
    """Test cases for subscriber query functionality."""
    
    @patch('create_limited_release.query')
    def test_get_subscribers_filters_by_preference(self, mock_query):
        """Test that only users with limitedReleases preference enabled are returned."""
        mock_query.return_value = {
            'Items': [
                {
                    'userId': 'user-1',
                    'email': 'user1@example.com',
                    'notificationPreferences': {'limitedReleases': True}
                },
                {
                    'userId': 'user-2',
                    'email': 'user2@example.com',
                    'notificationPreferences': {'limitedReleases': False}
                },
                {
                    'userId': 'user-3',
                    'email': 'user3@example.com',
                    'notificationPreferences': {'limitedReleases': True}
                }
            ]
        }
        
        subscribers = get_subscribers_for_limited_releases()
        
        # Should only return users with limitedReleases=True
        assert len(subscribers) == 2
        assert subscribers[0]['userId'] == 'user-1'
        assert subscribers[1]['userId'] == 'user-3'


class TestNotificationSending:
    """Test cases for notification sending functionality."""
    
    @patch('create_limited_release.get_email_service')
    def test_send_notifications_to_all_subscribers(self, mock_email_service):
        """Test that notifications are sent to all subscribers."""
        mock_email = MagicMock()
        mock_email.send_email.return_value = {'success': True, 'message_id': 'msg-123'}
        mock_email_service.return_value = mock_email
        
        subscribers = [
            {'email': 'user1@example.com', 'firstName': 'Alice'},
            {'email': 'user2@example.com', 'firstName': 'Bob'},
            {'email': 'user3@example.com', 'firstName': 'Charlie'}
        ]
        
        sent_count = send_limited_release_notifications(
            subscribers=subscribers,
            release_name='Spring Harvest',
            product_name='Organic Tomatoes',
            quantity_limit=50,
            duration=7,
            farmer_name='John Farmer'
        )
        
        assert sent_count == 3
        assert mock_email.send_email.call_count == 3
    
    @patch('create_limited_release.get_email_service')
    def test_notification_email_content(self, mock_email_service):
        """Test that notification email contains correct content."""
        mock_email = MagicMock()
        mock_email.send_email.return_value = {'success': True, 'message_id': 'msg-123'}
        mock_email_service.return_value = mock_email
        
        subscribers = [
            {'email': 'user1@example.com', 'firstName': 'Alice'}
        ]
        
        send_limited_release_notifications(
            subscribers=subscribers,
            release_name='Spring Harvest Special',
            product_name='Organic Tomatoes',
            quantity_limit=50,
            duration=7,
            farmer_name='John Farmer'
        )
        
        # Verify email was called with correct parameters
        call_args = mock_email.send_email.call_args
        assert call_args[1]['recipient'] == 'user1@example.com'
        assert 'Spring Harvest Special' in call_args[1]['subject']
        assert 'Alice' in call_args[1]['html_body']
        assert 'Organic Tomatoes' in call_args[1]['html_body']
        assert '50' in call_args[1]['html_body']
        assert '7' in call_args[1]['html_body']
        assert 'John Farmer' in call_args[1]['html_body']
    
    @patch('create_limited_release.get_email_service')
    def test_notification_handles_email_failures(self, mock_email_service):
        """Test that notification sending continues even if some emails fail."""
        mock_email = MagicMock()
        
        # First email succeeds, second fails, third succeeds
        mock_email.send_email.side_effect = [
            {'success': True, 'message_id': 'msg-1'},
            {'success': False, 'error': 'Email failed'},
            {'success': True, 'message_id': 'msg-3'}
        ]
        mock_email_service.return_value = mock_email
        
        subscribers = [
            {'email': 'user1@example.com', 'firstName': 'Alice'},
            {'email': 'user2@example.com', 'firstName': 'Bob'},
            {'email': 'user3@example.com', 'firstName': 'Charlie'}
        ]
        
        sent_count = send_limited_release_notifications(
            subscribers=subscribers,
            release_name='Spring Harvest',
            product_name='Organic Tomatoes',
            quantity_limit=50,
            duration=7,
            farmer_name='John Farmer'
        )
        
        # Should count only successful sends
        assert sent_count == 2
        assert mock_email.send_email.call_count == 3


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
