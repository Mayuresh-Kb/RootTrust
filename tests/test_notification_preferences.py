"""
Unit tests for notification preference management endpoint.
Tests PUT /notifications/preferences functionality.
"""
import json
import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock
from backend.notifications.update_preferences import handler


@pytest.fixture
def valid_jwt_token():
    """Mock valid JWT token."""
    return "Bearer valid.jwt.token"


@pytest.fixture
def mock_user_info():
    """Mock user info from JWT token."""
    return {
        'userId': 'user-123',
        'email': 'test@example.com',
        'role': 'consumer'
    }


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
def valid_preferences():
    """Valid notification preferences."""
    return {
        'newProducts': False,
        'promotions': True,
        'orderUpdates': True,
        'reviewRequests': False,
        'limitedReleases': True,
        'farmerBonuses': False
    }


@pytest.fixture
def api_gateway_event(valid_jwt_token, valid_preferences):
    """Mock API Gateway event."""
    return {
        'headers': {
            'Authorization': valid_jwt_token,
            'Content-Type': 'application/json'
        },
        'body': json.dumps(valid_preferences)
    }


class TestNotificationPreferenceUpdate:
    """Test notification preference update endpoint."""
    
    @patch('backend.notifications.update_preferences.get_user_from_token')
    @patch('backend.notifications.update_preferences.get_item')
    @patch('backend.notifications.update_preferences.update_item')
    def test_successful_preference_update(
        self,
        mock_update_item,
        mock_get_item,
        mock_get_user_from_token,
        api_gateway_event,
        mock_user_info,
        mock_user_item,
        valid_preferences
    ):
        """Test successful notification preference update."""
        # Setup mocks
        mock_get_user_from_token.return_value = mock_user_info
        mock_get_item.return_value = mock_user_item
        
        updated_user = mock_user_item.copy()
        updated_user['notificationPreferences'] = valid_preferences
        updated_user['updatedAt'] = datetime.utcnow().isoformat()
        mock_update_item.return_value = updated_user
        
        # Execute handler
        response = handler(api_gateway_event, None)
        
        # Verify response
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['message'] == 'Notification preferences updated successfully'
        assert body['preferences'] == valid_preferences
        
        # Verify mocks called correctly
        mock_get_user_from_token.assert_called_once()
        mock_get_item.assert_called_once_with('USER#user-123', 'PROFILE')
        mock_update_item.assert_called_once()
        
        # Verify update expression
        call_args = mock_update_item.call_args
        assert call_args[1]['pk'] == 'USER#user-123'
        assert call_args[1]['sk'] == 'PROFILE'
        assert 'notificationPreferences' in call_args[1]['update_expression']
    
    @patch('backend.notifications.update_preferences.get_user_from_token')
    def test_missing_authorization_header(self, mock_get_user_from_token):
        """Test request without authorization header."""
        event = {
            'headers': {},
            'body': json.dumps({'newProducts': True})
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 401
        body = json.loads(response['body'])
        assert body['error']['code'] == 'UNAUTHORIZED'
        assert 'Authorization header is required' in body['error']['message']
        mock_get_user_from_token.assert_not_called()
    
    @patch('backend.notifications.update_preferences.get_user_from_token')
    def test_invalid_jwt_token(self, mock_get_user_from_token):
        """Test request with invalid JWT token."""
        mock_get_user_from_token.side_effect = Exception('Invalid token')
        
        event = {
            'headers': {'Authorization': 'Bearer invalid.token'},
            'body': json.dumps({'newProducts': True})
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 401
        body = json.loads(response['body'])
        assert body['error']['code'] == 'INVALID_TOKEN'
        assert 'Invalid token' in body['error']['message']
    
    @patch('backend.notifications.update_preferences.get_user_from_token')
    def test_invalid_json_body(self, mock_get_user_from_token, mock_user_info):
        """Test request with invalid JSON body."""
        mock_get_user_from_token.return_value = mock_user_info
        
        event = {
            'headers': {'Authorization': 'Bearer valid.token'},
            'body': 'invalid json'
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error']['code'] == 'INVALID_JSON'
    
    @patch('backend.notifications.update_preferences.get_user_from_token')
    def test_invalid_preference_fields(self, mock_get_user_from_token, mock_user_info):
        """Test request with invalid preference fields."""
        mock_get_user_from_token.return_value = mock_user_info
        
        event = {
            'headers': {'Authorization': 'Bearer valid.token'},
            'body': json.dumps({
                'newProducts': 'not_a_boolean',  # Invalid type
                'promotions': True
            })
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error']['code'] == 'VALIDATION_ERROR'
    
    @patch('backend.notifications.update_preferences.get_user_from_token')
    @patch('backend.notifications.update_preferences.get_item')
    def test_user_not_found(self, mock_get_item, mock_get_user_from_token, mock_user_info):
        """Test update for non-existent user."""
        mock_get_user_from_token.return_value = mock_user_info
        mock_get_item.return_value = None
        
        event = {
            'headers': {'Authorization': 'Bearer valid.token'},
            'body': json.dumps({'newProducts': True, 'promotions': False})
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 404
        body = json.loads(response['body'])
        assert body['error']['code'] == 'RESOURCE_NOT_FOUND'
        assert 'User with ID user-123 not found' in body['error']['message']
    
    @patch('backend.notifications.update_preferences.get_user_from_token')
    @patch('backend.notifications.update_preferences.get_item')
    def test_database_query_error(self, mock_get_item, mock_get_user_from_token, mock_user_info):
        """Test handling of database query errors."""
        mock_get_user_from_token.return_value = mock_user_info
        mock_get_item.side_effect = Exception('DynamoDB error')
        
        event = {
            'headers': {'Authorization': 'Bearer valid.token'},
            'body': json.dumps({'newProducts': True})
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 503
        body = json.loads(response['body'])
        assert body['error']['code'] == 'SERVICE_UNAVAILABLE'
        assert 'Failed to query user' in body['error']['message']
    
    @patch('backend.notifications.update_preferences.get_user_from_token')
    @patch('backend.notifications.update_preferences.get_item')
    @patch('backend.notifications.update_preferences.update_item')
    def test_database_update_error(
        self,
        mock_update_item,
        mock_get_item,
        mock_get_user_from_token,
        mock_user_info,
        mock_user_item
    ):
        """Test handling of database update errors."""
        mock_get_user_from_token.return_value = mock_user_info
        mock_get_item.return_value = mock_user_item
        mock_update_item.side_effect = Exception('Update failed')
        
        event = {
            'headers': {'Authorization': 'Bearer valid.token'},
            'body': json.dumps({'newProducts': False})
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 503
        body = json.loads(response['body'])
        assert body['error']['code'] == 'SERVICE_UNAVAILABLE'
        assert 'Failed to update notification preferences' in body['error']['message']
    
    @patch('backend.notifications.update_preferences.get_user_from_token')
    @patch('backend.notifications.update_preferences.get_item')
    @patch('backend.notifications.update_preferences.update_item')
    def test_partial_preference_update(
        self,
        mock_update_item,
        mock_get_item,
        mock_get_user_from_token,
        mock_user_info,
        mock_user_item
    ):
        """Test updating only some preference fields."""
        mock_get_user_from_token.return_value = mock_user_info
        mock_get_item.return_value = mock_user_item
        
        partial_prefs = {
            'newProducts': False,
            'promotions': True,
            'orderUpdates': True,
            'reviewRequests': True,
            'limitedReleases': True,
            'farmerBonuses': True
        }
        
        updated_user = mock_user_item.copy()
        updated_user['notificationPreferences'] = partial_prefs
        mock_update_item.return_value = updated_user
        
        event = {
            'headers': {'Authorization': 'Bearer valid.token'},
            'body': json.dumps(partial_prefs)
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['preferences'] == partial_prefs
    
    @patch('backend.notifications.update_preferences.get_user_from_token')
    @patch('backend.notifications.update_preferences.get_item')
    @patch('backend.notifications.update_preferences.update_item')
    def test_all_preferences_disabled(
        self,
        mock_update_item,
        mock_get_item,
        mock_get_user_from_token,
        mock_user_info,
        mock_user_item
    ):
        """Test disabling all notification preferences."""
        mock_get_user_from_token.return_value = mock_user_info
        mock_get_item.return_value = mock_user_item
        
        all_disabled = {
            'newProducts': False,
            'promotions': False,
            'orderUpdates': False,
            'reviewRequests': False,
            'limitedReleases': False,
            'farmerBonuses': False
        }
        
        updated_user = mock_user_item.copy()
        updated_user['notificationPreferences'] = all_disabled
        mock_update_item.return_value = updated_user
        
        event = {
            'headers': {'Authorization': 'Bearer valid.token'},
            'body': json.dumps(all_disabled)
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['preferences'] == all_disabled
        assert all(not v for v in body['preferences'].values())
    
    @patch('backend.notifications.update_preferences.get_user_from_token')
    @patch('backend.notifications.update_preferences.get_item')
    @patch('backend.notifications.update_preferences.update_item')
    def test_all_preferences_enabled(
        self,
        mock_update_item,
        mock_get_item,
        mock_get_user_from_token,
        mock_user_info,
        mock_user_item
    ):
        """Test enabling all notification preferences."""
        mock_get_user_from_token.return_value = mock_user_info
        mock_get_item.return_value = mock_user_item
        
        all_enabled = {
            'newProducts': True,
            'promotions': True,
            'orderUpdates': True,
            'reviewRequests': True,
            'limitedReleases': True,
            'farmerBonuses': True
        }
        
        updated_user = mock_user_item.copy()
        updated_user['notificationPreferences'] = all_enabled
        mock_update_item.return_value = updated_user
        
        event = {
            'headers': {'Authorization': 'Bearer valid.token'},
            'body': json.dumps(all_enabled)
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['preferences'] == all_enabled
        assert all(v for v in body['preferences'].values())
    
    @patch('backend.notifications.update_preferences.get_user_from_token')
    @patch('backend.notifications.update_preferences.get_item')
    @patch('backend.notifications.update_preferences.update_item')
    def test_farmer_can_update_preferences(
        self,
        mock_update_item,
        mock_get_item,
        mock_get_user_from_token,
        mock_user_item
    ):
        """Test that farmers can also update notification preferences."""
        farmer_info = {
            'userId': 'farmer-456',
            'email': 'farmer@example.com',
            'role': 'farmer'
        }
        mock_get_user_from_token.return_value = farmer_info
        
        farmer_item = mock_user_item.copy()
        farmer_item['userId'] = 'farmer-456'
        farmer_item['PK'] = 'USER#farmer-456'
        farmer_item['role'] = 'farmer'
        mock_get_item.return_value = farmer_item
        
        prefs = {
            'newProducts': True,
            'promotions': False,
            'orderUpdates': True,
            'reviewRequests': False,
            'limitedReleases': True,
            'farmerBonuses': True
        }
        
        updated_farmer = farmer_item.copy()
        updated_farmer['notificationPreferences'] = prefs
        mock_update_item.return_value = updated_farmer
        
        event = {
            'headers': {'Authorization': 'Bearer farmer.token'},
            'body': json.dumps(prefs)
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['preferences'] == prefs
        mock_get_item.assert_called_once_with('USER#farmer-456', 'PROFILE')
    
    @patch('backend.notifications.update_preferences.get_user_from_token')
    @patch('backend.notifications.update_preferences.get_item')
    @patch('backend.notifications.update_preferences.update_item')
    def test_response_includes_cors_headers(
        self,
        mock_update_item,
        mock_get_item,
        mock_get_user_from_token,
        api_gateway_event,
        mock_user_info,
        mock_user_item
    ):
        """Test that response includes CORS headers."""
        mock_get_user_from_token.return_value = mock_user_info
        mock_get_item.return_value = mock_user_item
        mock_update_item.return_value = mock_user_item
        
        response = handler(api_gateway_event, None)
        
        assert 'Access-Control-Allow-Origin' in response['headers']
        assert response['headers']['Access-Control-Allow-Origin'] == '*'
        assert response['headers']['Content-Type'] == 'application/json'
    
    @patch('backend.notifications.update_preferences.get_user_from_token')
    @patch('backend.notifications.update_preferences.get_item')
    @patch('backend.notifications.update_preferences.update_item')
    def test_lowercase_authorization_header(
        self,
        mock_update_item,
        mock_get_item,
        mock_get_user_from_token,
        mock_user_info,
        mock_user_item,
        valid_preferences
    ):
        """Test handling of lowercase 'authorization' header."""
        mock_get_user_from_token.return_value = mock_user_info
        mock_get_item.return_value = mock_user_item
        mock_update_item.return_value = mock_user_item
        
        event = {
            'headers': {
                'authorization': 'Bearer valid.token',  # lowercase
                'Content-Type': 'application/json'
            },
            'body': json.dumps(valid_preferences)
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 200
        mock_get_user_from_token.assert_called_once()
