"""
Unit tests for unsubscribe endpoint.
Tests POST /notifications/unsubscribe functionality.
"""
import json
import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock
from backend.notifications.unsubscribe import handler


@pytest.fixture
def mock_user_item():
    """Mock user item from DynamoDB."""
    return {
        'PK': 'USER#user-123',
        'SK': 'PROFILE',
        'userId': 'user-123',
        'email': 'test@example.com',
        'role': 'consumer',
        'firstName': 'Test',
        'lastName': 'User',
        'notificationPreferences': {
            'newProducts': True,
            'promotions': True,
            'orderUpdates': True,
            'reviewRequests': True,
            'limitedReleases': True,
            'farmerBonuses': True
        },
        'createdAt': '2024-01-01T00:00:00',
        'updatedAt': '2024-01-01T00:00:00'
    }


@pytest.fixture
def api_gateway_event_with_email():
    """Mock API Gateway event with email."""
    return {
        'headers': {
            'Content-Type': 'application/json'
        },
        'body': json.dumps({'email': 'test@example.com'})
    }


@pytest.fixture
def api_gateway_event_with_user_id():
    """Mock API Gateway event with userId."""
    return {
        'headers': {
            'Content-Type': 'application/json'
        },
        'body': json.dumps({'userId': 'user-123'})
    }


class TestUnsubscribe:
    """Test unsubscribe endpoint."""
    
    @patch('backend.notifications.unsubscribe.get_item')
    @patch('backend.notifications.unsubscribe.update_item')
    def test_successful_unsubscribe_with_user_id(
        self,
        mock_update_item,
        mock_get_item,
        api_gateway_event_with_user_id,
        mock_user_item
    ):
        """Test successful unsubscribe with userId."""
        # Setup mocks
        mock_get_item.return_value = mock_user_item
        
        updated_user = mock_user_item.copy()
        updated_user['notificationPreferences'] = {
            'newProducts': False,
            'promotions': False,
            'limitedReleases': False,
            
            'farmerBonuses': False,
            'orderUpdates': True,
            'reviewRequests': True,
            'unsubscribedAt': datetime.utcnow().isoformat()
        }
        mock_update_item.return_value = updated_user
        
        # Execute handler
        response = handler(api_gateway_event_with_user_id, None)
        
        # Verify response
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert 'successfully unsubscribed' in body['message'].lower()
        assert body['status'] == 'unsubscribed'
        assert body['details']['marketingEmailsDisabled'] is True
        assert body['details']['transactionalEmailsEnabled'] is True
        assert 'unsubscribedAt' in body['details']
        
        # Verify mocks called correctly
        mock_get_item.assert_called_once_with('USER#user-123', 'PROFILE')
        mock_update_item.assert_called_once()
        
        # Verify update expression disables marketing notifications
        call_args = mock_update_item.call_args
        assert call_args[1]['pk'] == 'USER#user-123'
        assert call_args[1]['sk'] == 'PROFILE'
        prefs = call_args[1]['expression_attribute_values'][':prefs']
        assert prefs['newProducts'] is False
        assert prefs['promotions'] is False
        assert prefs['limitedReleases'] is False
        assert prefs['orderUpdates'] is True
        assert prefs['reviewRequests'] is True
        assert 'unsubscribedAt' in prefs
    
    @patch('backend.notifications.unsubscribe.scan')
    @patch('backend.notifications.unsubscribe.update_item')
    def test_successful_unsubscribe_with_email(
        self,
        mock_update_item,
        mock_scan,
        api_gateway_event_with_email,
        mock_user_item
    ):
        """Test successful unsubscribe with email."""
        # Setup mocks
        mock_scan.return_value = {'Items': [mock_user_item]}
        
        updated_user = mock_user_item.copy()
        updated_user['notificationPreferences'] = {
            'newProducts': False,
            'promotions': False,
            'limitedReleases': False,
            
            'farmerBonuses': False,
            'orderUpdates': True,
            'reviewRequests': True,
            'unsubscribedAt': datetime.utcnow().isoformat()
        }
        mock_update_item.return_value = updated_user
        
        # Execute handler
        response = handler(api_gateway_event_with_email, None)
        
        # Verify response
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert 'successfully unsubscribed' in body['message'].lower()
        assert body['status'] == 'unsubscribed'
        
        # Verify scan was called to find user by email
        mock_scan.assert_called_once()
        mock_update_item.assert_called_once()
    
    def test_missing_email_and_user_id(self):
        """Test request without email or userId."""
        event = {
            'headers': {},
            'body': json.dumps({})
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error']['code'] == 'VALIDATION_ERROR'
        assert 'email or userId is required' in body['error']['message']
    
    def test_invalid_json_body(self):
        """Test request with invalid JSON body."""
        event = {
            'headers': {},
            'body': 'invalid json'
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error']['code'] == 'INVALID_JSON'
    
    @patch('backend.notifications.unsubscribe.get_item')
    @patch('backend.notifications.unsubscribe.update_item')
    def test_user_not_found_returns_success(
        self,
        mock_update_item,
        mock_get_item
    ):
        """Test unsubscribe for non-existent user returns success (privacy)."""
        mock_get_item.return_value = None
        
        event = {
            'headers': {},
            'body': json.dumps({'userId': 'nonexistent-user'})
        }
        
        response = handler(event, None)
        
        # Should return success for privacy (don't reveal if user exists)
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['status'] == 'unsubscribed'
        
        # Update should not be called
        mock_update_item.assert_not_called()
    
    @patch('backend.notifications.unsubscribe.scan')
    @patch('backend.notifications.unsubscribe.update_item')
    def test_email_not_found_returns_success(
        self,
        mock_update_item,
        mock_scan
    ):
        """Test unsubscribe for non-existent email returns success (privacy)."""
        mock_scan.return_value = {'Items': []}
        
        event = {
            'headers': {},
            'body': json.dumps({'email': 'nonexistent@example.com'})
        }
        
        response = handler(event, None)
        
        # Should return success for privacy
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['status'] == 'unsubscribed'
        
        # Update should not be called
        mock_update_item.assert_not_called()
    
    @patch('backend.notifications.unsubscribe.get_item')
    def test_database_query_error_returns_error(
        self,
        mock_get_item
    ):
        """Test handling of database query errors."""
        mock_get_item.side_effect = Exception('DynamoDB error')
        
        event = {
            'headers': {},
            'body': json.dumps({'userId': 'user-123'})
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 503
        body = json.loads(response['body'])
        assert body['error']['code'] == 'SERVICE_UNAVAILABLE'
        assert 'Failed to query user' in body['error']['message']
    
    @patch('backend.notifications.unsubscribe.scan')
    def test_database_scan_error_returns_error(
        self,
        mock_scan
    ):
        """Test handling of database scan errors."""
        mock_scan.side_effect = Exception('DynamoDB scan error')
        
        event = {
            'headers': {},
            'body': json.dumps({'email': 'test@example.com'})
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 503
        body = json.loads(response['body'])
        assert body['error']['code'] == 'SERVICE_UNAVAILABLE'
    
    @patch('backend.notifications.unsubscribe.get_item')
    @patch('backend.notifications.unsubscribe.update_item')
    def test_database_update_error_returns_success(
        self,
        mock_update_item,
        mock_get_item,
        mock_user_item
    ):
        """Test handling of database update errors (returns success for idempotency)."""
        mock_get_item.return_value = mock_user_item
        mock_update_item.side_effect = Exception('Update failed')
        
        event = {
            'headers': {},
            'body': json.dumps({'userId': 'user-123'})
        }
        
        response = handler(event, None)
        
        # Should return success for idempotency
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['status'] == 'unsubscribed'
    
    @patch('backend.notifications.unsubscribe.get_item')
    @patch('backend.notifications.unsubscribe.update_item')
    def test_idempotent_unsubscribe(
        self,
        mock_update_item,
        mock_get_item,
        mock_user_item
    ):
        """Test that multiple unsubscribe calls are idempotent."""
        # User already unsubscribed
        already_unsubscribed = mock_user_item.copy()
        already_unsubscribed['notificationPreferences'] = {
            'newProducts': False,
            'promotions': False,
            'limitedReleases': False,
            
            'farmerBonuses': False,
            'orderUpdates': True,
            'reviewRequests': True,
            'unsubscribedAt': '2024-01-01T00:00:00'
        }
        mock_get_item.return_value = already_unsubscribed
        mock_update_item.return_value = already_unsubscribed
        
        event = {
            'headers': {},
            'body': json.dumps({'userId': 'user-123'})
        }
        
        response = handler(event, None)
        
        # Should still return success
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['status'] == 'unsubscribed'
        
        # Update should still be called (to update timestamp)
        mock_update_item.assert_called_once()
    
    @patch('backend.notifications.unsubscribe.get_item')
    @patch('backend.notifications.unsubscribe.update_item')
    def test_transactional_notifications_remain_enabled(
        self,
        mock_update_item,
        mock_get_item,
        mock_user_item
    ):
        """Test that transactional notifications remain enabled after unsubscribe."""
        mock_get_item.return_value = mock_user_item
        
        updated_user = mock_user_item.copy()
        mock_update_item.return_value = updated_user
        
        event = {
            'headers': {},
            'body': json.dumps({'userId': 'user-123'})
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 200
        
        # Verify transactional notifications remain enabled
        call_args = mock_update_item.call_args
        prefs = call_args[1]['expression_attribute_values'][':prefs']
        assert prefs['orderUpdates'] is True
        assert prefs['reviewRequests'] is True
    
    @patch('backend.notifications.unsubscribe.get_item')
    @patch('backend.notifications.unsubscribe.update_item')
    def test_marketing_notifications_disabled(
        self,
        mock_update_item,
        mock_get_item,
        mock_user_item
    ):
        """Test that all marketing notifications are disabled after unsubscribe."""
        mock_get_item.return_value = mock_user_item
        
        updated_user = mock_user_item.copy()
        mock_update_item.return_value = updated_user
        
        event = {
            'headers': {},
            'body': json.dumps({'userId': 'user-123'})
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 200
        
        # Verify all marketing notifications are disabled
        call_args = mock_update_item.call_args
        prefs = call_args[1]['expression_attribute_values'][':prefs']
        assert prefs['newProducts'] is False
        assert prefs['promotions'] is False
        assert prefs['limitedReleases'] is False
        
        assert prefs['farmerBonuses'] is False
    
    @patch('backend.notifications.unsubscribe.get_item')
    @patch('backend.notifications.unsubscribe.update_item')
    def test_unsubscribed_at_timestamp_set(
        self,
        mock_update_item,
        mock_get_item,
        mock_user_item
    ):
        """Test that unsubscribedAt timestamp is set."""
        mock_get_item.return_value = mock_user_item
        
        updated_user = mock_user_item.copy()
        mock_update_item.return_value = updated_user
        
        event = {
            'headers': {},
            'body': json.dumps({'userId': 'user-123'})
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 200
        
        # Verify unsubscribedAt is set
        call_args = mock_update_item.call_args
        prefs = call_args[1]['expression_attribute_values'][':prefs']
        assert 'unsubscribedAt' in prefs
        assert prefs['unsubscribedAt'] is not None
    
    @patch('backend.notifications.unsubscribe.get_item')
    @patch('backend.notifications.unsubscribe.update_item')
    def test_response_includes_cors_headers(
        self,
        mock_update_item,
        mock_get_item,
        mock_user_item
    ):
        """Test that response includes CORS headers."""
        mock_get_item.return_value = mock_user_item
        mock_update_item.return_value = mock_user_item
        
        event = {
            'headers': {},
            'body': json.dumps({'userId': 'user-123'})
        }
        
        response = handler(event, None)
        
        assert 'Access-Control-Allow-Origin' in response['headers']
        assert response['headers']['Access-Control-Allow-Origin'] == '*'
        assert response['headers']['Content-Type'] == 'application/json'
    
    @patch('backend.notifications.unsubscribe.get_item')
    @patch('backend.notifications.unsubscribe.update_item')
    def test_farmer_can_unsubscribe(
        self,
        mock_update_item,
        mock_get_item,
        mock_user_item
    ):
        """Test that farmers can also unsubscribe."""
        farmer_item = mock_user_item.copy()
        farmer_item['userId'] = 'farmer-456'
        farmer_item['PK'] = 'USER#farmer-456'
        farmer_item['role'] = 'farmer'
        mock_get_item.return_value = farmer_item
        
        updated_farmer = farmer_item.copy()
        mock_update_item.return_value = updated_farmer
        
        event = {
            'headers': {},
            'body': json.dumps({'userId': 'farmer-456'})
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['status'] == 'unsubscribed'
        mock_get_item.assert_called_once_with('USER#farmer-456', 'PROFILE')
    
    @patch('backend.notifications.unsubscribe.get_item')
    @patch('backend.notifications.unsubscribe.update_item')
    def test_both_email_and_user_id_provided(
        self,
        mock_update_item,
        mock_get_item,
        mock_user_item
    ):
        """Test that userId takes precedence when both email and userId provided."""
        mock_get_item.return_value = mock_user_item
        mock_update_item.return_value = mock_user_item
        
        event = {
            'headers': {},
            'body': json.dumps({
                'email': 'test@example.com',
                'userId': 'user-123'
            })
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 200
        # Should use userId (direct query, not scan)
        mock_get_item.assert_called_once_with('USER#user-123', 'PROFILE')
    
    @patch('backend.notifications.unsubscribe.get_item')
    @patch('backend.notifications.unsubscribe.update_item')
    def test_unexpected_error_in_update_returns_success(
        self,
        mock_update_item,
        mock_get_item,
        mock_user_item
    ):
        """Test that unexpected errors during update return success for idempotency."""
        mock_get_item.return_value = mock_user_item
        mock_update_item.side_effect = RuntimeError('Unexpected error')
        
        event = {
            'headers': {},
            'body': json.dumps({'userId': 'user-123'})
        }
        
        response = handler(event, None)
        
        # Should return success for idempotency even if update fails
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['status'] == 'unsubscribed'
