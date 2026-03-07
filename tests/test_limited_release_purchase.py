"""
Unit tests for limited release purchase endpoint.
Tests POST /limited-releases/{releaseId}/purchase
"""
import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend', 'limited_releases'))

from purchase_limited_release import handler


@pytest.fixture
def mock_consumer_token():
    """Mock JWT token for consumer user."""
    return "Bearer mock-consumer-token"


@pytest.fixture
def mock_farmer_token():
    """Mock JWT token for farmer user."""
    return "Bearer mock-farmer-token"


@pytest.fixture
def mock_consumer_user():
    """Mock consumer user info."""
    return {
        'userId': 'consumer-123',
        'role': 'consumer',
        'email': 'consumer@example.com'
    }


@pytest.fixture
def mock_farmer_user():
    """Mock farmer user info."""
    return {
        'userId': 'farmer-456',
        'role': 'farmer',
        'email': 'farmer@example.com'
    }


@pytest.fixture
def mock_active_release():
    """Mock active limited release."""
    return {
        'PK': 'LIMITED_RELEASE#release-789',
        'SK': 'METADATA',
        'releaseId': 'release-789',
        'farmerId': 'farmer-456',
        'productId': 'product-101',
        'releaseName': 'Exclusive Harvest',
        'quantityLimit': 10,
        'quantityRemaining': 5,
        'duration': 7,
        'status': 'active',
        'startDate': datetime.utcnow().isoformat(),
        'endDate': (datetime.utcnow() + timedelta(days=7)).isoformat()
    }


@pytest.fixture
def mock_sold_out_release():
    """Mock sold out limited release."""
    return {
        'PK': 'LIMITED_RELEASE#release-789',
        'SK': 'METADATA',
        'releaseId': 'release-789',
        'farmerId': 'farmer-456',
        'productId': 'product-101',
        'releaseName': 'Exclusive Harvest',
        'quantityLimit': 10,
        'quantityRemaining': 0,
        'duration': 7,
        'status': 'sold_out',
        'startDate': datetime.utcnow().isoformat(),
        'endDate': (datetime.utcnow() + timedelta(days=7)).isoformat()
    }


@pytest.fixture
def mock_product():
    """Mock product."""
    return {
        'PK': 'PRODUCT#product-101',
        'SK': 'METADATA',
        'productId': 'product-101',
        'farmerId': 'farmer-456',
        'name': 'Premium Organic Apples',
        'price': 150.0,
        'category': 'fruits',
        'verificationStatus': 'approved'
    }


@pytest.fixture
def valid_delivery_address():
    """Valid delivery address."""
    return {
        'street': '123 Main St',
        'city': 'Mumbai',
        'state': 'Maharashtra',
        'pincode': '400001'
    }


@pytest.fixture
def api_event(mock_consumer_token, valid_delivery_address):
    """Mock API Gateway event."""
    return {
        'headers': {
            'Authorization': mock_consumer_token
        },
        'pathParameters': {
            'releaseId': 'release-789'
        },
        'body': json.dumps({
            'deliveryAddress': valid_delivery_address
        })
    }


class TestLimitedReleasePurchaseAuthentication:
    """Test authentication and authorization."""
    
    def test_missing_authorization_header(self):
        """Test that missing authorization header returns 401."""
        event = {
            'headers': {},
            'pathParameters': {'releaseId': 'release-789'},
            'body': json.dumps({'deliveryAddress': {}})
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 401
        body = json.loads(response['body'])
        assert body['error']['code'] == 'UNAUTHORIZED'
        assert 'Authorization header is required' in body['error']['message']
    
    @patch('purchase_limited_release.get_user_from_token')
    def test_invalid_token(self, mock_get_user):
        """Test that invalid token returns 401."""
        mock_get_user.side_effect = Exception('Invalid token')
        
        event = {
            'headers': {'Authorization': 'Bearer invalid-token'},
            'pathParameters': {'releaseId': 'release-789'},
            'body': json.dumps({'deliveryAddress': {}})
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 401
        body = json.loads(response['body'])
        assert body['error']['code'] == 'INVALID_TOKEN'
    
    @patch('purchase_limited_release.get_user_from_token')
    def test_farmer_role_forbidden(self, mock_get_user, mock_farmer_user):
        """Test that farmer role is forbidden from purchasing."""
        mock_get_user.return_value = mock_farmer_user
        
        event = {
            'headers': {'Authorization': 'Bearer farmer-token'},
            'pathParameters': {'releaseId': 'release-789'},
            'body': json.dumps({'deliveryAddress': {}})
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 403
        body = json.loads(response['body'])
        assert body['error']['code'] == 'FORBIDDEN'
        assert 'Only consumers can purchase' in body['error']['message']


class TestLimitedReleasePurchaseValidation:
    """Test input validation."""
    
    @patch('purchase_limited_release.get_user_from_token')
    def test_missing_release_id(self, mock_get_user, mock_consumer_user):
        """Test that missing releaseId returns 400."""
        mock_get_user.return_value = mock_consumer_user
        
        event = {
            'headers': {'Authorization': 'Bearer token'},
            'pathParameters': {},
            'body': json.dumps({'deliveryAddress': {}})
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error']['code'] == 'VALIDATION_ERROR'
        assert 'releaseId is required' in body['error']['message']
    
    @patch('purchase_limited_release.get_user_from_token')
    def test_invalid_json_body(self, mock_get_user, mock_consumer_user):
        """Test that invalid JSON returns 400."""
        mock_get_user.return_value = mock_consumer_user
        
        event = {
            'headers': {'Authorization': 'Bearer token'},
            'pathParameters': {'releaseId': 'release-789'},
            'body': 'invalid json'
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error']['code'] == 'INVALID_JSON'
    
    @patch('purchase_limited_release.get_user_from_token')
    def test_missing_delivery_address(self, mock_get_user, mock_consumer_user):
        """Test that missing delivery address returns 400."""
        mock_get_user.return_value = mock_consumer_user
        
        event = {
            'headers': {'Authorization': 'Bearer token'},
            'pathParameters': {'releaseId': 'release-789'},
            'body': json.dumps({})
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error']['code'] == 'VALIDATION_ERROR'
        assert 'deliveryAddress is required' in body['error']['message']
    
    @patch('purchase_limited_release.get_user_from_token')
    def test_incomplete_delivery_address(self, mock_get_user, mock_consumer_user):
        """Test that incomplete delivery address returns 400."""
        mock_get_user.return_value = mock_consumer_user
        
        event = {
            'headers': {'Authorization': 'Bearer token'},
            'pathParameters': {'releaseId': 'release-789'},
            'body': json.dumps({
                'deliveryAddress': {
                    'street': '123 Main St'
                    # Missing city, state, pincode
                }
            })
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error']['code'] == 'VALIDATION_ERROR'
        assert 'city' in body['error']['message']


class TestLimitedReleasePurchaseBusinessLogic:
    """Test business logic for limited release purchase."""
    
    @patch('purchase_limited_release.get_user_from_token')
    @patch('purchase_limited_release.get_item')
    def test_release_not_found(self, mock_get_item, mock_get_user, 
                               mock_consumer_user, api_event):
        """Test that non-existent release returns 404."""
        mock_get_user.return_value = mock_consumer_user
        mock_get_item.return_value = None
        
        response = handler(api_event, None)
        
        assert response['statusCode'] == 404
        body = json.loads(response['body'])
        assert body['error']['code'] == 'RESOURCE_NOT_FOUND'
        assert 'not found' in body['error']['message']
    
    @patch('purchase_limited_release.get_user_from_token')
    @patch('purchase_limited_release.get_item')
    def test_release_not_active(self, mock_get_item, mock_get_user,
                                mock_consumer_user, api_event):
        """Test that non-active release returns 409."""
        mock_get_user.return_value = mock_consumer_user
        
        expired_release = {
            'releaseId': 'release-789',
            'status': 'expired',
            'quantityRemaining': 5
        }
        
        mock_get_item.return_value = expired_release
        
        response = handler(api_event, None)
        
        assert response['statusCode'] == 409
        body = json.loads(response['body'])
        assert body['error']['code'] == 'CONFLICT_ERROR'
        assert 'not active' in body['error']['message']
    
    @patch('purchase_limited_release.get_user_from_token')
    @patch('purchase_limited_release.get_item')
    def test_release_sold_out(self, mock_get_item, mock_get_user,
                              mock_consumer_user, api_event, mock_sold_out_release):
        """Test that sold out release returns 409."""
        mock_get_user.return_value = mock_consumer_user
        
        # Release with sold_out status should be treated as not active
        sold_out_release = mock_sold_out_release.copy()
        sold_out_release['status'] = 'sold_out'
        mock_get_item.return_value = sold_out_release
        
        response = handler(api_event, None)
        
        assert response['statusCode'] == 409
        body = json.loads(response['body'])
        assert body['error']['code'] == 'CONFLICT_ERROR'
        assert 'not active' in body['error']['message']
    
    @patch('purchase_limited_release.get_user_from_token')
    @patch('purchase_limited_release.get_item')
    def test_product_not_found(self, mock_get_item, mock_get_user,
                               mock_consumer_user, api_event, mock_active_release):
        """Test that missing product returns 404."""
        mock_get_user.return_value = mock_consumer_user
        
        # First call returns release, second call returns None for product
        mock_get_item.side_effect = [mock_active_release, None]
        
        response = handler(api_event, None)
        
        assert response['statusCode'] == 404
        body = json.loads(response['body'])
        assert body['error']['code'] == 'RESOURCE_NOT_FOUND'
        assert 'Product' in body['error']['message']
    
    @patch('purchase_limited_release.get_user_from_token')
    @patch('purchase_limited_release.get_item')
    @patch('purchase_limited_release.put_item')
    @patch('purchase_limited_release.update_item')
    def test_successful_purchase(self, mock_update_item, mock_put_item, 
                                 mock_get_item, mock_get_user,
                                 mock_consumer_user, api_event, 
                                 mock_active_release, mock_product):
        """Test successful limited release purchase."""
        mock_get_user.return_value = mock_consumer_user
        mock_get_item.side_effect = [mock_active_release, mock_product]
        mock_put_item.return_value = {}
        
        # Mock update_item to return updated release with decremented quantity
        updated_release = mock_active_release.copy()
        updated_release['quantityRemaining'] = 4
        mock_update_item.return_value = updated_release
        
        response = handler(api_event, None)
        
        assert response['statusCode'] == 201
        body = json.loads(response['body'])
        assert 'orderId' in body
        assert body['message'] == 'Limited release purchase successful'
        
        # Verify order was created
        mock_put_item.assert_called_once()
        order_dict = mock_put_item.call_args[0][0]
        assert order_dict['consumerId'] == 'consumer-123'
        assert order_dict['productId'] == 'product-101'
        assert order_dict['quantity'] == 1
        assert order_dict['totalAmount'] == 150.0
        
        # Verify quantity was decremented
        mock_update_item.assert_called()
        update_call = mock_update_item.call_args
        assert 'quantityRemaining - :qty' in update_call[1]['update_expression']
    
    @patch('purchase_limited_release.get_user_from_token')
    @patch('purchase_limited_release.get_item')
    @patch('purchase_limited_release.put_item')
    @patch('purchase_limited_release.update_item')
    def test_purchase_last_item_marks_sold_out(self, mock_update_item, mock_put_item,
                                                mock_get_item, mock_get_user,
                                                mock_consumer_user, api_event,
                                                mock_active_release, mock_product):
        """Test that purchasing last item marks release as sold out."""
        mock_get_user.return_value = mock_consumer_user
        
        # Release with only 1 item remaining
        last_item_release = mock_active_release.copy()
        last_item_release['quantityRemaining'] = 1
        
        mock_get_item.side_effect = [last_item_release, mock_product]
        mock_put_item.return_value = {}
        
        # First update decrements to 0, second update marks as sold out
        updated_release = last_item_release.copy()
        updated_release['quantityRemaining'] = 0
        mock_update_item.side_effect = [updated_release, {}]
        
        response = handler(api_event, None)
        
        assert response['statusCode'] == 201
        
        # Verify two update calls: one for decrement, one for sold_out status
        assert mock_update_item.call_count == 2
        
        # Check second update call sets status to sold_out
        second_update = mock_update_item.call_args_list[1]
        assert 'sold_out' in str(second_update)
    
    @patch('purchase_limited_release.get_user_from_token')
    @patch('purchase_limited_release.get_item')
    @patch('purchase_limited_release.put_item')
    @patch('purchase_limited_release.update_item')
    def test_concurrent_purchase_race_condition(self, mock_update_item, mock_put_item,
                                                mock_get_item, mock_get_user,
                                                mock_consumer_user, api_event,
                                                mock_active_release, mock_product):
        """Test that concurrent purchases are handled with conditional update."""
        # Import ConflictError from shared.exceptions
        import sys
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend', 'shared'))
        from backend.shared.exceptions import ConflictError
        
        mock_get_user.return_value = mock_consumer_user
        mock_get_item.side_effect = [mock_active_release, mock_product]
        mock_put_item.return_value = {}
        
        # Simulate race condition - conditional update fails
        mock_update_item.side_effect = ConflictError('Condition not met')
        
        response = handler(api_event, None)
        
        # ConflictError should be caught and return 409 or 503
        assert response['statusCode'] in [409, 503]
        body = json.loads(response['body'])
        assert body['error']['code'] in ['OUT_OF_STOCK', 'SERVICE_UNAVAILABLE']
    
    @patch('purchase_limited_release.get_user_from_token')
    @patch('purchase_limited_release.get_item')
    @patch('purchase_limited_release.put_item')
    @patch('purchase_limited_release.update_item')
    def test_purchase_with_referral_code(self, mock_update_item, mock_put_item,
                                         mock_get_item, mock_get_user,
                                         mock_consumer_user, mock_active_release,
                                         mock_product, valid_delivery_address):
        """Test purchase with referral code is stored in order."""
        mock_get_user.return_value = mock_consumer_user
        mock_get_item.side_effect = [mock_active_release, mock_product]
        mock_put_item.return_value = {}
        
        updated_release = mock_active_release.copy()
        updated_release['quantityRemaining'] = 4
        mock_update_item.return_value = updated_release
        
        event = {
            'headers': {'Authorization': 'Bearer token'},
            'pathParameters': {'releaseId': 'release-789'},
            'body': json.dumps({
                'deliveryAddress': valid_delivery_address,
                'referralCode': 'REF123'
            })
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 201
        
        # Verify referral code was included in order
        order_dict = mock_put_item.call_args[0][0]
        assert order_dict['referralCode'] == 'REF123'


class TestLimitedReleasePurchaseErrorHandling:
    """Test error handling."""
    
    @patch('purchase_limited_release.get_user_from_token')
    @patch('purchase_limited_release.get_item')
    def test_database_error_on_release_query(self, mock_get_item, mock_get_user,
                                             mock_consumer_user, api_event):
        """Test that database errors are handled gracefully."""
        mock_get_user.return_value = mock_consumer_user
        mock_get_item.side_effect = Exception('Database connection failed')
        
        response = handler(api_event, None)
        
        assert response['statusCode'] == 503
        body = json.loads(response['body'])
        assert body['error']['code'] == 'SERVICE_UNAVAILABLE'
    
    @patch('purchase_limited_release.get_user_from_token')
    @patch('purchase_limited_release.get_item')
    @patch('purchase_limited_release.put_item')
    def test_database_error_on_order_creation(self, mock_put_item, mock_get_item,
                                              mock_get_user, mock_consumer_user,
                                              api_event, mock_active_release,
                                              mock_product):
        """Test that order creation errors are handled."""
        mock_get_user.return_value = mock_consumer_user
        mock_get_item.side_effect = [mock_active_release, mock_product]
        mock_put_item.side_effect = Exception('Failed to write to database')
        
        response = handler(api_event, None)
        
        assert response['statusCode'] == 503
        body = json.loads(response['body'])
        assert body['error']['code'] == 'SERVICE_UNAVAILABLE'
        assert 'Failed to create order' in body['error']['message']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
