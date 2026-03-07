"""
Unit tests for referral conversion tracking endpoint.
Tests POST /referrals/track functionality.
"""
import json
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
from decimal import Decimal
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from referrals.track_conversion import handler, REWARD_PERCENTAGE
from shared.constants import OrderStatus, PaymentStatus


@pytest.fixture
def mock_env():
    """Set up environment variables for tests."""
    os.environ['DYNAMODB_TABLE_NAME'] = 'RootTrustData'


@pytest.fixture
def valid_referral():
    """Mock referral data."""
    return {
        'PK': 'REFERRAL#ABC12345',
        'SK': 'METADATA',
        'EntityType': 'Referral',
        'referralCode': 'ABC12345',
        'referrerId': 'consumer-referrer-123',
        'productId': 'product-789',
        'conversions': [],
        'totalConversions': 0,
        'totalRewards': 0.0,
        'createdAt': '2024-01-15T10:30:00Z',
        'GSI2PK': 'REFERRER#consumer-referrer-123',
        'GSI2SK': 'REFERRAL#2024-01-15T10:30:00Z'
    }


@pytest.fixture
def valid_order():
    """Mock order data."""
    return {
        'PK': 'ORDER#order-456',
        'SK': 'METADATA',
        'EntityType': 'Order',
        'orderId': 'order-456',
        'consumerId': 'consumer-buyer-789',
        'farmerId': 'farmer-999',
        'productId': 'product-789',
        'productName': 'Organic Tomatoes',
        'quantity': 10,
        'unitPrice': 50.0,
        'totalAmount': 500.0,
        'status': OrderStatus.CONFIRMED.value,
        'paymentStatus': PaymentStatus.COMPLETED.value,
        'referralCode': 'ABC12345',
        'createdAt': '2024-01-20T14:00:00Z'
    }


@pytest.fixture
def valid_user():
    """Mock user data for referrer."""
    return {
        'PK': 'USER#consumer-referrer-123',
        'SK': 'PROFILE',
        'EntityType': 'User',
        'userId': 'consumer-referrer-123',
        'email': 'referrer@example.com',
        'role': 'consumer',
        'consumerProfile': {
            'referralRewardBalance': 100.0,
            'totalOrders': 5
        }
    }


class TestReferralTrackConversionEndpoint:
    """Test referral conversion tracking endpoint."""
    
    def test_invalid_json_body(self, mock_env):
        """Test that invalid JSON returns 400."""
        event = {
            'body': 'invalid json'
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error']['code'] == 'INVALID_JSON'
    
    def test_missing_referral_code(self, mock_env):
        """Test that missing referralCode returns validation error."""
        event = {
            'body': json.dumps({'orderId': 'order-456'})
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error']['code'] == 'VALIDATION_ERROR'
    
    def test_missing_order_id(self, mock_env):
        """Test that missing orderId returns validation error."""
        event = {
            'body': json.dumps({'referralCode': 'ABC12345'})
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error']['code'] == 'VALIDATION_ERROR'
    
    @patch('referrals.track_conversion.get_item')
    def test_referral_not_found(self, mock_get_item, mock_env):
        """Test that non-existent referral code returns 404."""
        mock_get_item.return_value = None
        
        event = {
            'body': json.dumps({
                'referralCode': 'INVALID99',
                'orderId': 'order-456'
            })
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 404
        body = json.loads(response['body'])
        assert body['error']['code'] == 'RESOURCE_NOT_FOUND'
        assert 'INVALID99' in body['error']['message']
    
    @patch('referrals.track_conversion.get_item')
    def test_order_not_found(self, mock_get_item, mock_env, valid_referral):
        """Test that non-existent order returns 404."""
        # First call returns referral, second call returns None for order
        mock_get_item.side_effect = [valid_referral, None]
        
        event = {
            'body': json.dumps({
                'referralCode': 'ABC12345',
                'orderId': 'nonexistent-order'
            })
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 404
        body = json.loads(response['body'])
        assert body['error']['code'] == 'RESOURCE_NOT_FOUND'
        assert 'nonexistent-order' in body['error']['message']
    
    @patch('referrals.track_conversion.update_item')
    @patch('referrals.track_conversion.get_item')
    def test_successful_conversion_tracking(
        self, mock_get_item, mock_update_item,
        mock_env, valid_referral, valid_order, valid_user
    ):
        """Test successful referral conversion tracking."""
        # get_item calls: referral, order, user
        mock_get_item.side_effect = [valid_referral, valid_order, valid_user]
        mock_update_item.return_value = {}
        
        event = {
            'body': json.dumps({
                'referralCode': 'ABC12345',
                'orderId': 'order-456'
            })
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        
        # Verify response structure
        assert 'message' in body
        assert 'conversion' in body
        assert 'referralStats' in body
        
        # Verify conversion details
        conversion = body['conversion']
        assert conversion['referralCode'] == 'ABC12345'
        assert conversion['orderId'] == 'order-456'
        assert conversion['referredUserId'] == 'consumer-buyer-789'
        assert conversion['rewardAmount'] == 500.0 * REWARD_PERCENTAGE  # 5% of 500
        assert 'convertedAt' in conversion
        
        # Verify referral stats
        stats = body['referralStats']
        assert stats['totalConversions'] == 1
        assert stats['totalRewards'] == 25.0  # 5% of 500
        
        # Verify update_item was called twice (referral and user)
        assert mock_update_item.call_count == 2
        
        # Verify referral update
        referral_update_call = mock_update_item.call_args_list[0]
        assert referral_update_call[1]['pk'] == 'REFERRAL#ABC12345'
        assert referral_update_call[1]['sk'] == 'METADATA'
        assert ':conversions' in referral_update_call[1]['expression_attribute_values']
        assert ':total_conversions' in referral_update_call[1]['expression_attribute_values']
        assert ':total_rewards' in referral_update_call[1]['expression_attribute_values']
        
        # Verify user update
        user_update_call = mock_update_item.call_args_list[1]
        assert user_update_call[1]['pk'] == 'USER#consumer-referrer-123'
        assert user_update_call[1]['sk'] == 'PROFILE'
    
    @patch('referrals.track_conversion.update_item')
    @patch('referrals.track_conversion.get_item')
    def test_reward_calculation(
        self, mock_get_item, mock_update_item,
        mock_env, valid_referral, valid_order, valid_user
    ):
        """Test that reward amount is calculated correctly as 5% of order total."""
        # Test with different order amounts
        test_cases = [
            (100.0, 5.0, 'order-100'),    # 5% of 100
            (500.0, 25.0, 'order-500'),   # 5% of 500
            (1000.0, 50.0, 'order-1000'), # 5% of 1000
            (250.50, 12.525, 'order-250') # 5% of 250.50
        ]
        
        for order_total, expected_reward, order_id in test_cases:
            mock_get_item.reset_mock()
            mock_update_item.reset_mock()
            
            # Create fresh referral with empty conversions
            referral = {
                'PK': 'REFERRAL#ABC12345',
                'SK': 'METADATA',
                'EntityType': 'Referral',
                'referralCode': 'ABC12345',
                'referrerId': 'consumer-referrer-123',
                'productId': 'product-789',
                'conversions': [],
                'totalConversions': 0,
                'totalRewards': 0.0,
                'createdAt': '2024-01-15T10:30:00Z'
            }
            
            order = valid_order.copy()
            order['orderId'] = order_id
            order['totalAmount'] = order_total
            
            user = valid_user.copy()
            
            mock_get_item.side_effect = [referral, order, user]
            mock_update_item.return_value = {}
            
            event = {
                'body': json.dumps({
                    'referralCode': 'ABC12345',
                    'orderId': order_id
                })
            }
            
            response = handler(event, None)
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert body['conversion']['rewardAmount'] == expected_reward
    
    @patch('referrals.track_conversion.get_item')
    def test_duplicate_conversion_tracking(
        self, mock_get_item, mock_env, valid_referral, valid_order
    ):
        """Test that tracking the same order twice returns 409 conflict."""
        # Referral already has this order tracked
        referral_with_conversion = valid_referral.copy()
        referral_with_conversion['conversions'] = [
            {
                'referredUserId': 'consumer-buyer-789',
                'orderId': 'order-456',
                'rewardAmount': 25.0,
                'convertedAt': '2024-01-20T15:00:00Z'
            }
        ]
        referral_with_conversion['totalConversions'] = 1
        referral_with_conversion['totalRewards'] = 25.0
        
        mock_get_item.side_effect = [referral_with_conversion, valid_order]
        
        event = {
            'body': json.dumps({
                'referralCode': 'ABC12345',
                'orderId': 'order-456'
            })
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 409
        body = json.loads(response['body'])
        assert body['error']['code'] == 'CONFLICT'
        assert 'already been tracked' in body['error']['message']
    
    @patch('referrals.track_conversion.update_item')
    @patch('referrals.track_conversion.get_item')
    def test_multiple_conversions_accumulate(
        self, mock_get_item, mock_update_item,
        mock_env, valid_referral, valid_order, valid_user
    ):
        """Test that multiple conversions accumulate correctly."""
        # Referral already has one conversion
        referral_with_conversion = valid_referral.copy()
        referral_with_conversion['conversions'] = [
            {
                'referredUserId': 'consumer-other-111',
                'orderId': 'order-111',
                'rewardAmount': 15.0,
                'convertedAt': '2024-01-19T12:00:00Z'
            }
        ]
        referral_with_conversion['totalConversions'] = 1
        referral_with_conversion['totalRewards'] = 15.0
        
        # New order with different ID
        new_order = valid_order.copy()
        new_order['orderId'] = 'order-456'
        new_order['totalAmount'] = 500.0
        
        mock_get_item.side_effect = [referral_with_conversion, new_order, valid_user]
        mock_update_item.return_value = {}
        
        event = {
            'body': json.dumps({
                'referralCode': 'ABC12345',
                'orderId': 'order-456'
            })
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        
        # Verify stats show accumulated values
        stats = body['referralStats']
        assert stats['totalConversions'] == 2  # 1 existing + 1 new
        assert stats['totalRewards'] == 40.0  # 15.0 existing + 25.0 new
    
    @patch('referrals.track_conversion.update_item')
    @patch('referrals.track_conversion.get_item')
    def test_user_reward_balance_updated(
        self, mock_get_item, mock_update_item,
        mock_env, valid_referral, valid_order, valid_user
    ):
        """Test that user's reward balance is updated correctly."""
        mock_get_item.side_effect = [valid_referral, valid_order, valid_user]
        mock_update_item.return_value = {}
        
        event = {
            'body': json.dumps({
                'referralCode': 'ABC12345',
                'orderId': 'order-456'
            })
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 200
        
        # Verify user update was called
        user_update_call = mock_update_item.call_args_list[1]
        assert user_update_call[1]['pk'] == 'USER#consumer-referrer-123'
        
        # Verify new balance is old balance + reward
        new_balance = user_update_call[1]['expression_attribute_values'][':balance']
        assert float(new_balance) == 125.0  # 100.0 existing + 25.0 reward
    
    @patch('referrals.track_conversion.update_item')
    @patch('referrals.track_conversion.get_item')
    def test_user_not_found_still_succeeds(
        self, mock_get_item, mock_update_item,
        mock_env, valid_referral, valid_order
    ):
        """Test that conversion tracking succeeds even if user is not found."""
        # get_item calls: referral, order, user (returns None)
        mock_get_item.side_effect = [valid_referral, valid_order, None]
        mock_update_item.return_value = {}
        
        event = {
            'body': json.dumps({
                'referralCode': 'ABC12345',
                'orderId': 'order-456'
            })
        }
        
        response = handler(event, None)
        
        # Should still succeed
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['conversion']['rewardAmount'] == 25.0
        
        # Verify only referral was updated (not user)
        assert mock_update_item.call_count == 1
    
    @patch('referrals.track_conversion.update_item')
    @patch('referrals.track_conversion.get_item')
    def test_user_update_failure_still_succeeds(
        self, mock_get_item, mock_update_item,
        mock_env, valid_referral, valid_order, valid_user
    ):
        """Test that conversion tracking succeeds even if user update fails."""
        mock_get_item.side_effect = [valid_referral, valid_order, valid_user]
        # First update (referral) succeeds, second update (user) fails
        mock_update_item.side_effect = [{}, Exception('User update failed')]
        
        event = {
            'body': json.dumps({
                'referralCode': 'ABC12345',
                'orderId': 'order-456'
            })
        }
        
        response = handler(event, None)
        
        # Should still succeed because conversion is already tracked
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['conversion']['rewardAmount'] == 25.0
    
    @patch('referrals.track_conversion.update_item')
    @patch('referrals.track_conversion.get_item')
    def test_referral_update_failure(
        self, mock_get_item, mock_update_item,
        mock_env, valid_referral, valid_order
    ):
        """Test that referral update failure returns 503."""
        mock_get_item.side_effect = [valid_referral, valid_order]
        mock_update_item.side_effect = Exception('DynamoDB error')
        
        event = {
            'body': json.dumps({
                'referralCode': 'ABC12345',
                'orderId': 'order-456'
            })
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 503
        body = json.loads(response['body'])
        assert body['error']['code'] == 'SERVICE_UNAVAILABLE'
        assert 'update referral' in body['error']['message'].lower()
    
    @patch('referrals.track_conversion.get_item')
    def test_referral_query_error(self, mock_get_item, mock_env):
        """Test that referral query error returns 503."""
        mock_get_item.side_effect = Exception('DynamoDB error')
        
        event = {
            'body': json.dumps({
                'referralCode': 'ABC12345',
                'orderId': 'order-456'
            })
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 503
        body = json.loads(response['body'])
        assert body['error']['code'] == 'SERVICE_UNAVAILABLE'
        assert 'query referral' in body['error']['message'].lower()
    
    @patch('referrals.track_conversion.get_item')
    def test_order_query_error(self, mock_get_item, mock_env, valid_referral):
        """Test that order query error returns 503."""
        # First call returns referral, second call raises exception
        mock_get_item.side_effect = [valid_referral, Exception('DynamoDB error')]
        
        event = {
            'body': json.dumps({
                'referralCode': 'ABC12345',
                'orderId': 'order-456'
            })
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 503
        body = json.loads(response['body'])
        assert body['error']['code'] == 'SERVICE_UNAVAILABLE'
        assert 'query order' in body['error']['message'].lower()
    
    @patch('referrals.track_conversion.update_item')
    @patch('referrals.track_conversion.get_item')
    def test_cors_headers(
        self, mock_get_item, mock_update_item,
        mock_env, valid_referral, valid_order, valid_user
    ):
        """Test that CORS headers are present in response."""
        mock_get_item.side_effect = [valid_referral, valid_order, valid_user]
        mock_update_item.return_value = {}
        
        event = {
            'body': json.dumps({
                'referralCode': 'ABC12345',
                'orderId': 'order-456'
            })
        }
        
        response = handler(event, None)
        
        assert 'Access-Control-Allow-Origin' in response['headers']
        assert response['headers']['Access-Control-Allow-Origin'] == '*'
        assert response['headers']['Content-Type'] == 'application/json'
    
    @patch('referrals.track_conversion.get_item')
    def test_cors_headers_on_error(self, mock_get_item, mock_env):
        """Test that CORS headers are present even on error responses."""
        mock_get_item.return_value = None
        
        event = {
            'body': json.dumps({
                'referralCode': 'INVALID99',
                'orderId': 'order-456'
            })
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 404
        assert 'Access-Control-Allow-Origin' in response['headers']
        assert response['headers']['Access-Control-Allow-Origin'] == '*'
    
    @patch('referrals.track_conversion.update_item')
    @patch('referrals.track_conversion.get_item')
    def test_conversion_timestamp_format(
        self, mock_get_item, mock_update_item,
        mock_env, valid_referral, valid_order, valid_user
    ):
        """Test that conversion timestamp is in ISO 8601 format."""
        mock_get_item.side_effect = [valid_referral, valid_order, valid_user]
        mock_update_item.return_value = {}
        
        event = {
            'body': json.dumps({
                'referralCode': 'ABC12345',
                'orderId': 'order-456'
            })
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        
        # Verify timestamp is ISO 8601 format
        converted_at = body['conversion']['convertedAt']
        # Should be parseable as datetime
        datetime.fromisoformat(converted_at.replace('Z', '+00:00'))
    
    @patch('referrals.track_conversion.update_item')
    @patch('referrals.track_conversion.get_item')
    def test_zero_order_amount(
        self, mock_get_item, mock_update_item,
        mock_env, valid_referral, valid_order, valid_user
    ):
        """Test handling of order with zero amount."""
        order = valid_order.copy()
        order['totalAmount'] = 0.0
        
        mock_get_item.side_effect = [valid_referral, order, valid_user]
        mock_update_item.return_value = {}
        
        event = {
            'body': json.dumps({
                'referralCode': 'ABC12345',
                'orderId': 'order-456'
            })
        }
        
        response = handler(event, None)
        
        # Should succeed with zero reward
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['conversion']['rewardAmount'] == 0.0
    
    @patch('referrals.track_conversion.update_item')
    @patch('referrals.track_conversion.get_item')
    def test_large_order_amount(
        self, mock_get_item, mock_update_item,
        mock_env, valid_referral, valid_order, valid_user
    ):
        """Test handling of order with large amount."""
        order = valid_order.copy()
        order['totalAmount'] = 10000.0
        
        mock_get_item.side_effect = [valid_referral, order, valid_user]
        mock_update_item.return_value = {}
        
        event = {
            'body': json.dumps({
                'referralCode': 'ABC12345',
                'orderId': 'order-456'
            })
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['conversion']['rewardAmount'] == 500.0  # 5% of 10000
    
    @patch('referrals.track_conversion.update_item')
    @patch('referrals.track_conversion.get_item')
    def test_decimal_precision(
        self, mock_get_item, mock_update_item,
        mock_env, valid_referral, valid_order, valid_user
    ):
        """Test that decimal precision is maintained for rewards."""
        order = valid_order.copy()
        order['totalAmount'] = 123.45
        
        mock_get_item.side_effect = [valid_referral, order, valid_user]
        mock_update_item.return_value = {}
        
        event = {
            'body': json.dumps({
                'referralCode': 'ABC12345',
                'orderId': 'order-456'
            })
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        # 5% of 123.45 = 6.1725
        assert body['conversion']['rewardAmount'] == 6.1725
    
    @patch('referrals.track_conversion.update_item')
    @patch('referrals.track_conversion.get_item')
    def test_response_json_format(
        self, mock_get_item, mock_update_item,
        mock_env, valid_referral, valid_order, valid_user
    ):
        """Test that response body is valid JSON."""
        mock_get_item.side_effect = [valid_referral, valid_order, valid_user]
        mock_update_item.return_value = {}
        
        event = {
            'body': json.dumps({
                'referralCode': 'ABC12345',
                'orderId': 'order-456'
            })
        }
        
        response = handler(event, None)
        
        # Should not raise exception
        body = json.loads(response['body'])
        
        # Verify it's a dictionary
        assert isinstance(body, dict)
        assert isinstance(body['conversion'], dict)
        assert isinstance(body['referralStats'], dict)


class TestReferralTrackConversionEdgeCases:
    """Test edge cases for referral conversion tracking."""
    
    @patch('referrals.track_conversion.update_item')
    @patch('referrals.track_conversion.get_item')
    def test_missing_consumer_profile(
        self, mock_get_item, mock_update_item,
        mock_env, valid_referral, valid_order
    ):
        """Test handling of user without consumerProfile."""
        user_without_profile = {
            'PK': 'USER#consumer-referrer-123',
            'SK': 'PROFILE',
            'EntityType': 'User',
            'userId': 'consumer-referrer-123',
            'email': 'referrer@example.com',
            'role': 'consumer'
            # Missing consumerProfile
        }
        
        mock_get_item.side_effect = [valid_referral, valid_order, user_without_profile]
        mock_update_item.return_value = {}
        
        event = {
            'body': json.dumps({
                'referralCode': 'ABC12345',
                'orderId': 'order-456'
            })
        }
        
        response = handler(event, None)
        
        # Should succeed and create balance from 0
        assert response['statusCode'] == 200
    
    @patch('referrals.track_conversion.update_item')
    @patch('referrals.track_conversion.get_item')
    def test_missing_reward_balance(
        self, mock_get_item, mock_update_item,
        mock_env, valid_referral, valid_order
    ):
        """Test handling of consumerProfile without referralRewardBalance."""
        user_without_balance = {
            'PK': 'USER#consumer-referrer-123',
            'SK': 'PROFILE',
            'EntityType': 'User',
            'userId': 'consumer-referrer-123',
            'email': 'referrer@example.com',
            'role': 'consumer',
            'consumerProfile': {
                'totalOrders': 5
                # Missing referralRewardBalance
            }
        }
        
        mock_get_item.side_effect = [valid_referral, valid_order, user_without_balance]
        mock_update_item.return_value = {}
        
        event = {
            'body': json.dumps({
                'referralCode': 'ABC12345',
                'orderId': 'order-456'
            })
        }
        
        response = handler(event, None)
        
        # Should succeed and create balance from 0
        assert response['statusCode'] == 200
    
    def test_empty_request_body(self, mock_env):
        """Test handling of empty request body."""
        event = {
            'body': json.dumps({})
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error']['code'] == 'VALIDATION_ERROR'
    
    def test_missing_body(self, mock_env):
        """Test handling of missing body."""
        event = {}
        
        response = handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error']['code'] == 'VALIDATION_ERROR'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
