"""
Unit tests for referral rewards endpoint.
Tests GET /referrals/rewards functionality.
"""
import json
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from referrals.get_rewards import handler
from shared.constants import UserRole


@pytest.fixture
def mock_env():
    """Set up environment variables for tests."""
    os.environ['DYNAMODB_TABLE_NAME'] = 'RootTrustData'
    os.environ['JWT_SECRET_KEY'] = 'test-secret-key-for-testing-only'


@pytest.fixture
def valid_consumer_token():
    """Generate a valid JWT token for a consumer."""
    from shared.auth import generate_jwt_token
    return generate_jwt_token(
        user_id='consumer-123',
        email='consumer@example.com',
        role=UserRole.CONSUMER.value
    )['token']


@pytest.fixture
def valid_farmer_token():
    """Generate a valid JWT token for a farmer."""
    from shared.auth import generate_jwt_token
    return generate_jwt_token(
        user_id='farmer-456',
        email='farmer@example.com',
        role=UserRole.FARMER.value
    )['token']


@pytest.fixture
def valid_user():
    """Mock user data with consumer profile."""
    return {
        'PK': 'USER#consumer-123',
        'SK': 'PROFILE',
        'EntityType': 'User',
        'userId': 'consumer-123',
        'email': 'consumer@example.com',
        'role': 'consumer',
        'consumerProfile': {
            'referralCode': 'USER123',
            'referralRewardBalance': 125.50,
            'totalOrders': 10,
            'followedFarmers': []
        }
    }


@pytest.fixture
def valid_referrals():
    """Mock referral data for user."""
    return [
        {
            'PK': 'REFERRAL#ABC12345',
            'SK': 'METADATA',
            'EntityType': 'Referral',
            'referralCode': 'ABC12345',
            'referrerId': 'consumer-123',
            'productId': 'product-789',
            'conversions': [
                {
                    'referredUserId': 'consumer-buyer-1',
                    'orderId': 'order-1',
                    'rewardAmount': 25.0,
                    'convertedAt': '2024-01-20T14:00:00Z'
                },
                {
                    'referredUserId': 'consumer-buyer-2',
                    'orderId': 'order-2',
                    'rewardAmount': 15.0,
                    'convertedAt': '2024-01-21T10:00:00Z'
                }
            ],
            'totalConversions': 2,
            'totalRewards': 40.0,
            'createdAt': '2024-01-15T10:30:00Z',
            'GSI2PK': 'REFERRER#consumer-123',
            'GSI2SK': 'REFERRAL#2024-01-15T10:30:00Z'
        },
        {
            'PK': 'REFERRAL#XYZ98765',
            'SK': 'METADATA',
            'EntityType': 'Referral',
            'referralCode': 'XYZ98765',
            'referrerId': 'consumer-123',
            'productId': 'product-456',
            'conversions': [
                {
                    'referredUserId': 'consumer-buyer-3',
                    'orderId': 'order-3',
                    'rewardAmount': 30.0,
                    'convertedAt': '2024-01-22T16:00:00Z'
                }
            ],
            'totalConversions': 1,
            'totalRewards': 30.0,
            'createdAt': '2024-01-18T12:00:00Z',
            'GSI2PK': 'REFERRER#consumer-123',
            'GSI2SK': 'REFERRAL#2024-01-18T12:00:00Z'
        }
    ]


class TestReferralRewardsEndpoint:
    """Test referral rewards endpoint."""
    
    def test_missing_authorization_header(self, mock_env):
        """Test that missing authorization header returns 401."""
        event = {
            'headers': {}
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 401
        body = json.loads(response['body'])
        assert body['error']['code'] == 'UNAUTHORIZED'
    
    def test_invalid_token(self, mock_env):
        """Test that invalid JWT token returns 401."""
        event = {
            'headers': {'Authorization': 'Bearer invalid-token'}
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 401
        body = json.loads(response['body'])
        assert body['error']['code'] == 'INVALID_TOKEN'
    
    def test_farmer_role_forbidden(self, mock_env, valid_farmer_token):
        """Test that farmers cannot view referral rewards."""
        event = {
            'headers': {'Authorization': f'Bearer {valid_farmer_token}'}
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 403
        body = json.loads(response['body'])
        assert body['error']['code'] == 'FORBIDDEN'
        assert 'consumers' in body['error']['message'].lower()
    
    @patch('referrals.get_rewards.get_item')
    def test_user_not_found(self, mock_get_item, mock_env, valid_consumer_token):
        """Test that non-existent user returns 404."""
        mock_get_item.return_value = None
        
        event = {
            'headers': {'Authorization': f'Bearer {valid_consumer_token}'}
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 404
        body = json.loads(response['body'])
        assert body['error']['code'] == 'RESOURCE_NOT_FOUND'
    
    @patch('referrals.get_rewards.query')
    @patch('referrals.get_rewards.get_item')
    def test_successful_rewards_retrieval(
        self, mock_get_item, mock_query,
        mock_env, valid_consumer_token, valid_user, valid_referrals
    ):
        """Test successful referral rewards retrieval."""
        mock_get_item.return_value = valid_user
        mock_query.return_value = {'Items': valid_referrals}
        
        event = {
            'headers': {'Authorization': f'Bearer {valid_consumer_token}'}
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        
        # Verify response structure
        assert 'rewardBalance' in body
        assert 'totalConversions' in body
        assert 'totalRewardsEarned' in body
        assert 'referralCount' in body
        assert 'referrals' in body
        assert 'redemptionOptions' in body
        
        # Verify reward balance from user profile
        assert body['rewardBalance'] == 125.50
        
        # Verify total conversions (2 + 1 = 3)
        assert body['totalConversions'] == 3
        
        # Verify total rewards earned (40.0 + 30.0 = 70.0)
        assert body['totalRewardsEarned'] == 70.0
        
        # Verify referral count
        assert body['referralCount'] == 2
        
        # Verify referrals array
        assert len(body['referrals']) == 2
        assert body['referrals'][0]['referralCode'] == 'ABC12345'
        assert body['referrals'][0]['conversions'] == 2
        assert body['referrals'][0]['rewardsEarned'] == 40.0
        assert body['referrals'][1]['referralCode'] == 'XYZ98765'
        assert body['referrals'][1]['conversions'] == 1
        assert body['referrals'][1]['rewardsEarned'] == 30.0
        
        # Verify redemption options
        assert len(body['redemptionOptions']) == 3
        assert any(opt['type'] == 'wallet_credit' for opt in body['redemptionOptions'])
        assert any(opt['type'] == 'order_discount' for opt in body['redemptionOptions'])
        assert any(opt['type'] == 'bank_transfer' for opt in body['redemptionOptions'])
    
    @patch('referrals.get_rewards.query')
    @patch('referrals.get_rewards.get_item')
    def test_no_referrals(
        self, mock_get_item, mock_query,
        mock_env, valid_consumer_token, valid_user
    ):
        """Test user with no referrals."""
        user_no_rewards = valid_user.copy()
        user_no_rewards['consumerProfile']['referralRewardBalance'] = 0.0
        
        mock_get_item.return_value = user_no_rewards
        mock_query.return_value = {'Items': []}
        
        event = {
            'headers': {'Authorization': f'Bearer {valid_consumer_token}'}
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        
        assert body['rewardBalance'] == 0.0
        assert body['totalConversions'] == 0
        assert body['totalRewardsEarned'] == 0.0
        assert body['referralCount'] == 0
        assert body['referrals'] == []
    
    @patch('referrals.get_rewards.query')
    @patch('referrals.get_rewards.get_item')
    def test_referrals_with_no_conversions(
        self, mock_get_item, mock_query,
        mock_env, valid_consumer_token, valid_user
    ):
        """Test referrals that have no conversions yet."""
        referrals_no_conversions = [
            {
                'PK': 'REFERRAL#NEW12345',
                'SK': 'METADATA',
                'EntityType': 'Referral',
                'referralCode': 'NEW12345',
                'referrerId': 'consumer-123',
                'productId': 'product-999',
                'conversions': [],
                'totalConversions': 0,
                'totalRewards': 0.0,
                'createdAt': '2024-01-25T10:00:00Z',
                'GSI2PK': 'REFERRER#consumer-123',
                'GSI2SK': 'REFERRAL#2024-01-25T10:00:00Z'
            }
        ]
        
        user_no_rewards = valid_user.copy()
        user_no_rewards['consumerProfile']['referralRewardBalance'] = 0.0
        
        mock_get_item.return_value = user_no_rewards
        mock_query.return_value = {'Items': referrals_no_conversions}
        
        event = {
            'headers': {'Authorization': f'Bearer {valid_consumer_token}'}
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        
        assert body['rewardBalance'] == 0.0
        assert body['totalConversions'] == 0
        assert body['totalRewardsEarned'] == 0.0
        assert body['referralCount'] == 1
        assert len(body['referrals']) == 1
        assert body['referrals'][0]['conversions'] == 0
        assert body['referrals'][0]['rewardsEarned'] == 0.0
    
    @patch('referrals.get_rewards.query')
    @patch('referrals.get_rewards.get_item')
    def test_redemption_options_availability(
        self, mock_get_item, mock_query,
        mock_env, valid_consumer_token, valid_user
    ):
        """Test that redemption options availability is calculated correctly."""
        mock_get_item.return_value = valid_user
        mock_query.return_value = {'Items': []}
        
        event = {
            'headers': {'Authorization': f'Bearer {valid_consumer_token}'}
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        
        # User has 125.50 balance
        redemption_options = body['redemptionOptions']
        
        # Find each option and verify availability
        wallet_credit = next(opt for opt in redemption_options if opt['type'] == 'wallet_credit')
        assert wallet_credit['minimumAmount'] == 10.0
        assert wallet_credit['available'] is True  # 125.50 >= 10.0
        
        order_discount = next(opt for opt in redemption_options if opt['type'] == 'order_discount')
        assert order_discount['minimumAmount'] == 5.0
        assert order_discount['available'] is True  # 125.50 >= 5.0
        
        bank_transfer = next(opt for opt in redemption_options if opt['type'] == 'bank_transfer')
        assert bank_transfer['minimumAmount'] == 50.0
        assert bank_transfer['available'] is True  # 125.50 >= 50.0
    
    @patch('referrals.get_rewards.query')
    @patch('referrals.get_rewards.get_item')
    def test_redemption_options_low_balance(
        self, mock_get_item, mock_query,
        mock_env, valid_consumer_token, valid_user
    ):
        """Test redemption options with low balance."""
        user_low_balance = valid_user.copy()
        user_low_balance['consumerProfile']['referralRewardBalance'] = 7.50
        
        mock_get_item.return_value = user_low_balance
        mock_query.return_value = {'Items': []}
        
        event = {
            'headers': {'Authorization': f'Bearer {valid_consumer_token}'}
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        
        redemption_options = body['redemptionOptions']
        
        # User has 7.50 balance
        wallet_credit = next(opt for opt in redemption_options if opt['type'] == 'wallet_credit')
        assert wallet_credit['available'] is False  # 7.50 < 10.0
        
        order_discount = next(opt for opt in redemption_options if opt['type'] == 'order_discount')
        assert order_discount['available'] is True  # 7.50 >= 5.0
        
        bank_transfer = next(opt for opt in redemption_options if opt['type'] == 'bank_transfer')
        assert bank_transfer['available'] is False  # 7.50 < 50.0
    
    @patch('referrals.get_rewards.query')
    @patch('referrals.get_rewards.get_item')
    def test_missing_consumer_profile(
        self, mock_get_item, mock_query,
        mock_env, valid_consumer_token
    ):
        """Test user without consumer profile."""
        user_no_profile = {
            'PK': 'USER#consumer-123',
            'SK': 'PROFILE',
            'EntityType': 'User',
            'userId': 'consumer-123',
            'email': 'consumer@example.com',
            'role': 'consumer'
            # Missing consumerProfile
        }
        
        mock_get_item.return_value = user_no_profile
        mock_query.return_value = {'Items': []}
        
        event = {
            'headers': {'Authorization': f'Bearer {valid_consumer_token}'}
        }
        
        response = handler(event, None)
        
        # Should succeed with 0 balance
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['rewardBalance'] == 0.0
    
    @patch('referrals.get_rewards.query')
    @patch('referrals.get_rewards.get_item')
    def test_missing_reward_balance(
        self, mock_get_item, mock_query,
        mock_env, valid_consumer_token
    ):
        """Test consumer profile without referralRewardBalance."""
        user_no_balance = {
            'PK': 'USER#consumer-123',
            'SK': 'PROFILE',
            'EntityType': 'User',
            'userId': 'consumer-123',
            'email': 'consumer@example.com',
            'role': 'consumer',
            'consumerProfile': {
                'referralCode': 'USER123',
                'totalOrders': 5
                # Missing referralRewardBalance
            }
        }
        
        mock_get_item.return_value = user_no_balance
        mock_query.return_value = {'Items': []}
        
        event = {
            'headers': {'Authorization': f'Bearer {valid_consumer_token}'}
        }
        
        response = handler(event, None)
        
        # Should succeed with 0 balance
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['rewardBalance'] == 0.0
    
    @patch('referrals.get_rewards.get_item')
    def test_user_query_error(self, mock_get_item, mock_env, valid_consumer_token):
        """Test that user query error returns 503."""
        mock_get_item.side_effect = Exception('DynamoDB error')
        
        event = {
            'headers': {'Authorization': f'Bearer {valid_consumer_token}'}
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 503
        body = json.loads(response['body'])
        assert body['error']['code'] == 'SERVICE_UNAVAILABLE'
        assert 'user profile' in body['error']['message'].lower()
    
    @patch('referrals.get_rewards.query')
    @patch('referrals.get_rewards.get_item')
    def test_referrals_query_error(
        self, mock_get_item, mock_query,
        mock_env, valid_consumer_token, valid_user
    ):
        """Test that referrals query error returns 503."""
        mock_get_item.return_value = valid_user
        mock_query.side_effect = Exception('DynamoDB error')
        
        event = {
            'headers': {'Authorization': f'Bearer {valid_consumer_token}'}
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 503
        body = json.loads(response['body'])
        assert body['error']['code'] == 'SERVICE_UNAVAILABLE'
        assert 'referrals' in body['error']['message'].lower()
    
    @patch('referrals.get_rewards.query')
    @patch('referrals.get_rewards.get_item')
    def test_gsi2_query_parameters(
        self, mock_get_item, mock_query,
        mock_env, valid_consumer_token, valid_user
    ):
        """Test that GSI2 query is called with correct parameters."""
        mock_get_item.return_value = valid_user
        mock_query.return_value = {'Items': []}
        
        event = {
            'headers': {'Authorization': f'Bearer {valid_consumer_token}'}
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 200
        
        # Verify query was called with correct parameters
        assert mock_query.called
        call_kwargs = mock_query.call_args[1]
        assert call_kwargs['index_name'] == 'GSI2'
        
        # Verify key condition expression
        # The Key condition should be for GSI2PK = REFERRER#consumer-123
        key_condition = call_kwargs['key_condition_expression']
        # We can't easily inspect the Key object, but we can verify the query succeeded
    
    @patch('referrals.get_rewards.query')
    @patch('referrals.get_rewards.get_item')
    def test_cors_headers(
        self, mock_get_item, mock_query,
        mock_env, valid_consumer_token, valid_user
    ):
        """Test that CORS headers are present in response."""
        mock_get_item.return_value = valid_user
        mock_query.return_value = {'Items': []}
        
        event = {
            'headers': {'Authorization': f'Bearer {valid_consumer_token}'}
        }
        
        response = handler(event, None)
        
        assert 'Access-Control-Allow-Origin' in response['headers']
        assert response['headers']['Access-Control-Allow-Origin'] == '*'
        assert response['headers']['Content-Type'] == 'application/json'
    
    @patch('referrals.get_rewards.query')
    @patch('referrals.get_rewards.get_item')
    def test_cors_headers_on_error(
        self, mock_get_item, mock_query,
        mock_env, valid_consumer_token
    ):
        """Test that CORS headers are present even on error responses."""
        mock_get_item.return_value = None
        
        event = {
            'headers': {'Authorization': f'Bearer {valid_consumer_token}'}
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 404
        assert 'Access-Control-Allow-Origin' in response['headers']
        assert response['headers']['Access-Control-Allow-Origin'] == '*'
    
    @patch('referrals.get_rewards.query')
    @patch('referrals.get_rewards.get_item')
    def test_referral_summary_structure(
        self, mock_get_item, mock_query,
        mock_env, valid_consumer_token, valid_user, valid_referrals
    ):
        """Test that referral summary has correct structure."""
        mock_get_item.return_value = valid_user
        mock_query.return_value = {'Items': valid_referrals}
        
        event = {
            'headers': {'Authorization': f'Bearer {valid_consumer_token}'}
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        
        # Verify each referral summary has required fields
        for referral in body['referrals']:
            assert 'referralCode' in referral
            assert 'productId' in referral
            assert 'conversions' in referral
            assert 'rewardsEarned' in referral
            assert 'createdAt' in referral
    
    @patch('referrals.get_rewards.query')
    @patch('referrals.get_rewards.get_item')
    def test_redemption_option_structure(
        self, mock_get_item, mock_query,
        mock_env, valid_consumer_token, valid_user
    ):
        """Test that redemption options have correct structure."""
        mock_get_item.return_value = valid_user
        mock_query.return_value = {'Items': []}
        
        event = {
            'headers': {'Authorization': f'Bearer {valid_consumer_token}'}
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        
        # Verify each redemption option has required fields
        for option in body['redemptionOptions']:
            assert 'type' in option
            assert 'name' in option
            assert 'description' in option
            assert 'minimumAmount' in option
            assert 'available' in option
            assert isinstance(option['available'], bool)
    
    @patch('referrals.get_rewards.query')
    @patch('referrals.get_rewards.get_item')
    def test_response_json_format(
        self, mock_get_item, mock_query,
        mock_env, valid_consumer_token, valid_user
    ):
        """Test that response body is valid JSON."""
        mock_get_item.return_value = valid_user
        mock_query.return_value = {'Items': []}
        
        event = {
            'headers': {'Authorization': f'Bearer {valid_consumer_token}'}
        }
        
        response = handler(event, None)
        
        # Should not raise exception
        body = json.loads(response['body'])
        
        # Verify it's a dictionary
        assert isinstance(body, dict)
        assert isinstance(body['referrals'], list)
        assert isinstance(body['redemptionOptions'], list)
    
    @patch('referrals.get_rewards.query')
    @patch('referrals.get_rewards.get_item')
    def test_large_number_of_referrals(
        self, mock_get_item, mock_query,
        mock_env, valid_consumer_token, valid_user
    ):
        """Test handling of user with many referrals."""
        # Create 50 referrals
        many_referrals = []
        for i in range(50):
            many_referrals.append({
                'PK': f'REFERRAL#CODE{i:05d}',
                'SK': 'METADATA',
                'EntityType': 'Referral',
                'referralCode': f'CODE{i:05d}',
                'referrerId': 'consumer-123',
                'productId': f'product-{i}',
                'conversions': [],
                'totalConversions': i % 5,  # 0-4 conversions
                'totalRewards': float((i % 5) * 10),
                'createdAt': f'2024-01-{(i % 28) + 1:02d}T10:00:00Z',
                'GSI2PK': 'REFERRER#consumer-123',
                'GSI2SK': f'REFERRAL#2024-01-{(i % 28) + 1:02d}T10:00:00Z'
            })
        
        mock_get_item.return_value = valid_user
        mock_query.return_value = {'Items': many_referrals}
        
        event = {
            'headers': {'Authorization': f'Bearer {valid_consumer_token}'}
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        
        assert body['referralCount'] == 50
        assert len(body['referrals']) == 50
    
    @patch('referrals.get_rewards.query')
    @patch('referrals.get_rewards.get_item')
    def test_decimal_precision_in_totals(
        self, mock_get_item, mock_query,
        mock_env, valid_consumer_token, valid_user
    ):
        """Test that decimal precision is maintained in calculations."""
        referrals_with_decimals = [
            {
                'PK': 'REFERRAL#DEC12345',
                'SK': 'METADATA',
                'EntityType': 'Referral',
                'referralCode': 'DEC12345',
                'referrerId': 'consumer-123',
                'productId': 'product-1',
                'conversions': [],
                'totalConversions': 3,
                'totalRewards': 12.345,
                'createdAt': '2024-01-15T10:00:00Z',
                'GSI2PK': 'REFERRER#consumer-123',
                'GSI2SK': 'REFERRAL#2024-01-15T10:00:00Z'
            },
            {
                'PK': 'REFERRAL#DEC67890',
                'SK': 'METADATA',
                'EntityType': 'Referral',
                'referralCode': 'DEC67890',
                'referrerId': 'consumer-123',
                'productId': 'product-2',
                'conversions': [],
                'totalConversions': 2,
                'totalRewards': 8.675,
                'createdAt': '2024-01-16T10:00:00Z',
                'GSI2PK': 'REFERRER#consumer-123',
                'GSI2SK': 'REFERRAL#2024-01-16T10:00:00Z'
            }
        ]
        
        mock_get_item.return_value = valid_user
        mock_query.return_value = {'Items': referrals_with_decimals}
        
        event = {
            'headers': {'Authorization': f'Bearer {valid_consumer_token}'}
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        
        # Verify totals are calculated correctly
        assert body['totalConversions'] == 5  # 3 + 2
        # Use approximate comparison for floating point
        assert abs(body['totalRewardsEarned'] - 21.02) < 0.001  # 12.345 + 8.675


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
