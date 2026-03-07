"""
Unit tests for promotion creation endpoint.
"""
import json
import pytest
import os
import sys
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend', 'shared'))

from shared.constants import UserRole, PromotionStatus


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Set up environment variables for tests."""
    monkeypatch.setenv('DYNAMODB_TABLE_NAME', 'RootTrustData-test')
    monkeypatch.setenv('BEDROCK_REGION', 'us-east-1')
    monkeypatch.setenv('JWT_SECRET_KEY', 'test-secret-key-12345678')


@pytest.fixture
def valid_promotion_data():
    """Valid promotion creation request data."""
    return {
        'productId': 'product-123',
        'budget': 500.0,
        'duration': 7
    }


@pytest.fixture
def farmer_token_payload():
    """Mock farmer JWT token payload."""
    return {
        'userId': 'farmer-123',
        'email': 'farmer@example.com',
        'role': 'farmer'
    }


@pytest.fixture
def consumer_token_payload():
    """Mock consumer JWT token payload."""
    return {
        'userId': 'consumer-123',
        'email': 'consumer@example.com',
        'role': 'consumer'
    }


@pytest.fixture
def mock_product():
    """Mock product data."""
    return {
        'PK': 'PRODUCT#product-123',
        'SK': 'METADATA',
        'productId': 'product-123',
        'farmerId': 'farmer-123',
        'name': 'Organic Tomatoes',
        'description': 'Fresh organic tomatoes from our farm',
        'category': 'vegetables',
        'price': 50.0
    }


@pytest.fixture
def mock_farmer():
    """Mock farmer data with account balance."""
    return {
        'PK': 'USER#farmer-123',
        'SK': 'PROFILE',
        'userId': 'farmer-123',
        'email': 'farmer@example.com',
        'role': 'farmer',
        'farmerProfile': {
            'farmName': 'Test Farm',
            'accountBalance': 1000.0
        }
    }


class TestPromotionCreation:
    """Test cases for promotion creation endpoint."""
    
    def test_create_promotion_success(
        self, mock_env_vars, valid_promotion_data, farmer_token_payload, 
        mock_product, mock_farmer
    ):
        """Test successful promotion creation by farmer."""
        # Import after env vars are set
        from promotions.create_promotion import handler
        
        # Mock dependencies
        with patch('promotions.create_promotion.get_user_from_token') as mock_auth, \
             patch('promotions.create_promotion.get_item') as mock_get, \
             patch('promotions.create_promotion.put_item') as mock_put, \
             patch('promotions.create_promotion.update_item') as mock_update, \
             patch('promotions.create_promotion.generate_promotional_ad_copy') as mock_ad_copy:
            
            # Setup mocks
            mock_auth.return_value = farmer_token_payload
            mock_get.side_effect = [mock_product, mock_farmer]  # First call for product, second for farmer
            mock_put.return_value = {}
            mock_update.return_value = {}
            mock_ad_copy.return_value = "Special promotion on Organic Tomatoes! Limited time offer!"
            
            # Create event
            event = {
                'headers': {
                    'Authorization': 'Bearer valid-token'
                },
                'body': json.dumps(valid_promotion_data)
            }
            
            # Call handler
            response = handler(event, None)
            
            # Assertions
            assert response['statusCode'] == 201
            body = json.loads(response['body'])
            assert 'promotionId' in body
            assert 'startDate' in body
            assert 'endDate' in body
            assert 'aiGeneratedAdCopy' in body
            assert body['aiGeneratedAdCopy'] == "Special promotion on Organic Tomatoes! Limited time offer!"
            
            # Verify put_item was called
            mock_put.assert_called_once()
            promotion_dict = mock_put.call_args[0][0]
            assert promotion_dict['farmerId'] == 'farmer-123'
            assert promotion_dict['productId'] == 'product-123'
            assert promotion_dict['budget'] == 500.0
            assert promotion_dict['duration'] == 7
            assert promotion_dict['status'] == 'active'
            
            # Verify balance was deducted
            mock_update.assert_called_once()
    
    def test_create_promotion_missing_auth_header(self, mock_env_vars, valid_promotion_data):
        """Test promotion creation without authorization header."""
        from promotions.create_promotion import handler
        
        event = {
            'headers': {},
            'body': json.dumps(valid_promotion_data)
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 401
        body = json.loads(response['body'])
        assert body['error']['code'] == 'UNAUTHORIZED'
    
    def test_create_promotion_consumer_forbidden(
        self, mock_env_vars, valid_promotion_data, consumer_token_payload
    ):
        """Test that consumers cannot create promotions."""
        from promotions.create_promotion import handler
        
        with patch('promotions.create_promotion.get_user_from_token') as mock_auth:
            mock_auth.return_value = consumer_token_payload
            
            event = {
                'headers': {
                    'Authorization': 'Bearer consumer-token'
                },
                'body': json.dumps(valid_promotion_data)
            }
            
            response = handler(event, None)
            
            assert response['statusCode'] == 403
            body = json.loads(response['body'])
            assert body['error']['code'] == 'FORBIDDEN'
            assert 'farmers' in body['error']['message'].lower()
    
    def test_create_promotion_invalid_json(self, mock_env_vars, farmer_token_payload):
        """Test promotion creation with invalid JSON."""
        from promotions.create_promotion import handler
        
        with patch('promotions.create_promotion.get_user_from_token') as mock_auth:
            mock_auth.return_value = farmer_token_payload
            
            event = {
                'headers': {
                    'Authorization': 'Bearer valid-token'
                },
                'body': 'invalid json {'
            }
            
            response = handler(event, None)
            
            assert response['statusCode'] == 400
            body = json.loads(response['body'])
            assert body['error']['code'] == 'INVALID_JSON'
    
    def test_create_promotion_negative_budget(
        self, mock_env_vars, valid_promotion_data, farmer_token_payload
    ):
        """Test promotion creation with negative budget."""
        from promotions.create_promotion import handler
        
        with patch('promotions.create_promotion.get_user_from_token') as mock_auth:
            mock_auth.return_value = farmer_token_payload
            
            # Set negative budget
            invalid_data = valid_promotion_data.copy()
            invalid_data['budget'] = -100.0
            
            event = {
                'headers': {
                    'Authorization': 'Bearer valid-token'
                },
                'body': json.dumps(invalid_data)
            }
            
            response = handler(event, None)
            
            assert response['statusCode'] == 400
            body = json.loads(response['body'])
            assert body['error']['code'] == 'VALIDATION_ERROR'
    
    def test_create_promotion_zero_budget(
        self, mock_env_vars, valid_promotion_data, farmer_token_payload
    ):
        """Test promotion creation with zero budget."""
        from promotions.create_promotion import handler
        
        with patch('promotions.create_promotion.get_user_from_token') as mock_auth:
            mock_auth.return_value = farmer_token_payload
            
            # Set zero budget
            invalid_data = valid_promotion_data.copy()
            invalid_data['budget'] = 0
            
            event = {
                'headers': {
                    'Authorization': 'Bearer valid-token'
                },
                'body': json.dumps(invalid_data)
            }
            
            response = handler(event, None)
            
            assert response['statusCode'] == 400
            body = json.loads(response['body'])
            assert body['error']['code'] == 'VALIDATION_ERROR'
    
    def test_create_promotion_product_not_found(
        self, mock_env_vars, valid_promotion_data, farmer_token_payload
    ):
        """Test promotion creation for non-existent product."""
        from promotions.create_promotion import handler
        
        with patch('promotions.create_promotion.get_user_from_token') as mock_auth, \
             patch('promotions.create_promotion.get_item') as mock_get:
            
            mock_auth.return_value = farmer_token_payload
            mock_get.return_value = None  # Product not found
            
            event = {
                'headers': {
                    'Authorization': 'Bearer valid-token'
                },
                'body': json.dumps(valid_promotion_data)
            }
            
            response = handler(event, None)
            
            assert response['statusCode'] == 404
            body = json.loads(response['body'])
            assert body['error']['code'] == 'NOT_FOUND'
            assert 'product' in body['error']['message'].lower()
    
    def test_create_promotion_not_product_owner(
        self, mock_env_vars, valid_promotion_data, farmer_token_payload, mock_product
    ):
        """Test promotion creation for product owned by another farmer."""
        from promotions.create_promotion import handler
        
        with patch('promotions.create_promotion.get_user_from_token') as mock_auth, \
             patch('promotions.create_promotion.get_item') as mock_get:
            
            mock_auth.return_value = farmer_token_payload
            
            # Product owned by different farmer
            other_farmer_product = mock_product.copy()
            other_farmer_product['farmerId'] = 'other-farmer-456'
            mock_get.return_value = other_farmer_product
            
            event = {
                'headers': {
                    'Authorization': 'Bearer valid-token'
                },
                'body': json.dumps(valid_promotion_data)
            }
            
            response = handler(event, None)
            
            assert response['statusCode'] == 403
            body = json.loads(response['body'])
            assert body['error']['code'] == 'FORBIDDEN'
            assert 'own products' in body['error']['message'].lower()
    
    def test_create_promotion_insufficient_balance(
        self, mock_env_vars, valid_promotion_data, farmer_token_payload, 
        mock_product, mock_farmer
    ):
        """Test promotion creation with insufficient farmer balance."""
        from promotions.create_promotion import handler
        
        with patch('promotions.create_promotion.get_user_from_token') as mock_auth, \
             patch('promotions.create_promotion.get_item') as mock_get:
            
            mock_auth.return_value = farmer_token_payload
            
            # Farmer with low balance
            low_balance_farmer = mock_farmer.copy()
            low_balance_farmer['farmerProfile']['accountBalance'] = 100.0
            
            mock_get.side_effect = [mock_product, low_balance_farmer]
            
            # Request budget higher than balance
            high_budget_data = valid_promotion_data.copy()
            high_budget_data['budget'] = 500.0
            
            event = {
                'headers': {
                    'Authorization': 'Bearer valid-token'
                },
                'body': json.dumps(high_budget_data)
            }
            
            response = handler(event, None)
            
            assert response['statusCode'] == 409
            body = json.loads(response['body'])
            assert body['error']['code'] == 'INSUFFICIENT_BALANCE'
    
    def test_create_promotion_missing_required_fields(
        self, mock_env_vars, farmer_token_payload
    ):
        """Test promotion creation with missing required fields."""
        from promotions.create_promotion import handler
        
        with patch('promotions.create_promotion.get_user_from_token') as mock_auth:
            mock_auth.return_value = farmer_token_payload
            
            # Minimal data missing required fields
            incomplete_data = {
                'productId': 'product-123'
            }
            
            event = {
                'headers': {
                    'Authorization': 'Bearer valid-token'
                },
                'body': json.dumps(incomplete_data)
            }
            
            response = handler(event, None)
            
            assert response['statusCode'] == 400
            body = json.loads(response['body'])
            assert body['error']['code'] == 'VALIDATION_ERROR'
    
    def test_create_promotion_dynamodb_error(
        self, mock_env_vars, valid_promotion_data, farmer_token_payload, 
        mock_product, mock_farmer
    ):
        """Test promotion creation when DynamoDB fails."""
        from promotions.create_promotion import handler
        
        with patch('promotions.create_promotion.get_user_from_token') as mock_auth, \
             patch('promotions.create_promotion.get_item') as mock_get, \
             patch('promotions.create_promotion.put_item') as mock_put, \
             patch('promotions.create_promotion.generate_promotional_ad_copy') as mock_ad_copy:
            
            mock_auth.return_value = farmer_token_payload
            mock_get.side_effect = [mock_product, mock_farmer]
            mock_put.side_effect = Exception('DynamoDB error')
            mock_ad_copy.return_value = "Test ad copy"
            
            event = {
                'headers': {
                    'Authorization': 'Bearer valid-token'
                },
                'body': json.dumps(valid_promotion_data)
            }
            
            response = handler(event, None)
            
            assert response['statusCode'] == 503
            body = json.loads(response['body'])
            assert body['error']['code'] == 'SERVICE_UNAVAILABLE'
    
    def test_create_promotion_with_exact_balance(
        self, mock_env_vars, valid_promotion_data, farmer_token_payload, 
        mock_product, mock_farmer
    ):
        """Test promotion creation when budget equals farmer balance."""
        from promotions.create_promotion import handler
        
        with patch('promotions.create_promotion.get_user_from_token') as mock_auth, \
             patch('promotions.create_promotion.get_item') as mock_get, \
             patch('promotions.create_promotion.put_item') as mock_put, \
             patch('promotions.create_promotion.update_item') as mock_update, \
             patch('promotions.create_promotion.generate_promotional_ad_copy') as mock_ad_copy:
            
            mock_auth.return_value = farmer_token_payload
            
            # Farmer with exact balance
            exact_balance_farmer = mock_farmer.copy()
            exact_balance_farmer['farmerProfile']['accountBalance'] = 500.0
            
            mock_get.side_effect = [mock_product, exact_balance_farmer]
            mock_put.return_value = {}
            mock_update.return_value = {}
            mock_ad_copy.return_value = "Test ad copy"
            
            event = {
                'headers': {
                    'Authorization': 'Bearer valid-token'
                },
                'body': json.dumps(valid_promotion_data)
            }
            
            response = handler(event, None)
            
            assert response['statusCode'] == 201
            body = json.loads(response['body'])
            assert 'promotionId' in body
    
    def test_create_promotion_duration_calculation(
        self, mock_env_vars, valid_promotion_data, farmer_token_payload, 
        mock_product, mock_farmer
    ):
        """Test that promotion duration is calculated correctly."""
        from promotions.create_promotion import handler
        
        with patch('promotions.create_promotion.get_user_from_token') as mock_auth, \
             patch('promotions.create_promotion.get_item') as mock_get, \
             patch('promotions.create_promotion.put_item') as mock_put, \
             patch('promotions.create_promotion.update_item') as mock_update, \
             patch('promotions.create_promotion.generate_promotional_ad_copy') as mock_ad_copy:
            
            mock_auth.return_value = farmer_token_payload
            mock_get.side_effect = [mock_product, mock_farmer]
            mock_put.return_value = {}
            mock_update.return_value = {}
            mock_ad_copy.return_value = "Test ad copy"
            
            # Set duration to 14 days
            duration_data = valid_promotion_data.copy()
            duration_data['duration'] = 14
            
            event = {
                'headers': {
                    'Authorization': 'Bearer valid-token'
                },
                'body': json.dumps(duration_data)
            }
            
            response = handler(event, None)
            
            assert response['statusCode'] == 201
            body = json.loads(response['body'])
            
            # Parse dates
            start_date = datetime.fromisoformat(body['startDate'])
            end_date = datetime.fromisoformat(body['endDate'])
            
            # Verify duration
            duration = (end_date - start_date).days
            assert duration == 14


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
