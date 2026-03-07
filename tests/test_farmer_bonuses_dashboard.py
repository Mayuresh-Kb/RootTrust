"""
Unit tests for farmer bonus dashboard endpoint.

Tests the GET /analytics/farmer/{farmerId}/bonuses endpoint that displays
farmer bonus status, progress toward next reward, and total bonuses earned.

Requirements tested:
- 12.3: The Farmer Portal shall display current bonus status and progress toward next reward
- 12.5: The Farmer Portal shall track and display total bonuses earned
"""
import json
import pytest
from unittest.mock import patch, MagicMock
from decimal import Decimal
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from referrals.get_farmer_bonuses import handler
from shared.constants import UserRole


class TestFarmerBonusDashboard:
    """Test suite for farmer bonus dashboard endpoint."""
    
    @pytest.fixture
    def mock_farmer_item(self):
        """Mock farmer profile item from DynamoDB."""
        return {
            'PK': 'USER#farmer123',
            'SK': 'PROFILE',
            'EntityType': 'User',
            'userId': 'farmer123',
            'email': 'farmer@example.com',
            'role': 'farmer',
            'firstName': 'John',
            'lastName': 'Farmer',
            'farmerProfile': {
                'farmName': 'Green Valley Farm',
                'bonusesEarned': Decimal('1000.0'),
                'consecutiveSalesStreak': 7,
                'featuredStatus': False
            }
        }
    
    @pytest.fixture
    def mock_farmer_item_with_bonus(self):
        """Mock farmer profile with bonus achieved."""
        return {
            'PK': 'USER#farmer456',
            'SK': 'PROFILE',
            'EntityType': 'User',
            'userId': 'farmer456',
            'email': 'farmer2@example.com',
            'role': 'farmer',
            'firstName': 'Jane',
            'lastName': 'Farmer',
            'farmerProfile': {
                'farmName': 'Sunny Acres',
                'bonusesEarned': Decimal('2000.0'),
                'consecutiveSalesStreak': 10,
                'featuredStatus': True
            }
        }
    
    @pytest.fixture
    def mock_farmer_item_no_streak(self):
        """Mock farmer profile with no sales streak."""
        return {
            'PK': 'USER#farmer789',
            'SK': 'PROFILE',
            'EntityType': 'User',
            'userId': 'farmer789',
            'email': 'farmer3@example.com',
            'role': 'farmer',
            'firstName': 'Bob',
            'lastName': 'Farmer',
            'farmerProfile': {
                'farmName': 'Fresh Fields',
                'bonusesEarned': 0.0,
                'consecutiveSalesStreak': 0,
                'featuredStatus': False
            }
        }
    
    @pytest.fixture
    def valid_event(self):
        """Valid API Gateway event."""
        return {
            'headers': {
                'Authorization': 'Bearer valid_token'
            },
            'pathParameters': {
                'farmerId': 'farmer123'
            }
        }
    
    @pytest.fixture
    def mock_context(self):
        """Mock Lambda context."""
        return MagicMock()
    
    def test_successful_bonus_dashboard_retrieval(
        self, valid_event, mock_context, mock_farmer_item
    ):
        """Test successful retrieval of farmer bonus dashboard."""
        with patch('referrals.get_farmer_bonuses.get_user_from_token') as mock_auth, \
             patch('referrals.get_farmer_bonuses.get_item') as mock_get_item:
            
            # Mock authentication
            mock_auth.return_value = {
                'userId': 'farmer123',
                'role': 'farmer'
            }
            
            # Mock DynamoDB query
            mock_get_item.return_value = mock_farmer_item
            
            # Call handler
            response = handler(valid_event, mock_context)
            
            # Verify response
            assert response['statusCode'] == 200
            
            body = json.loads(response['body'])
            assert body['bonusesEarned'] == 1000.0
            assert body['consecutiveSalesStreak'] == 7
            assert body['progressToNextBonus'] == '7/10 sales'
            assert body['progressPercentage'] == 70
            assert body['featuredStatus'] is False
            assert body['nextBonusThreshold'] == 10
            
            # Verify bonus details
            assert 'bonusDetails' in body
            assert 'salesStreakBonus' in body['bonusDetails']
            assert 'featuredPlacement' in body['bonusDetails']
            
            # Verify sales streak bonus details
            sales_streak = body['bonusDetails']['salesStreakBonus']
            assert sales_streak['currentProgress'] == 7
            assert sales_streak['threshold'] == 10
            assert sales_streak['achieved'] is False
            
            # Verify featured placement details
            featured = body['bonusDetails']['featuredPlacement']
            assert featured['currentStatus'] is False
            assert featured['achieved'] is False
    
    def test_bonus_dashboard_with_achieved_bonus(
        self, valid_event, mock_context, mock_farmer_item_with_bonus
    ):
        """Test bonus dashboard when farmer has achieved the bonus."""
        with patch('referrals.get_farmer_bonuses.get_user_from_token') as mock_auth, \
             patch('referrals.get_farmer_bonuses.get_item') as mock_get_item:
            
            # Update event for different farmer
            event = valid_event.copy()
            event['pathParameters'] = {'farmerId': 'farmer456'}
            
            # Mock authentication
            mock_auth.return_value = {
                'userId': 'farmer456',
                'role': 'farmer'
            }
            
            # Mock DynamoDB query
            mock_get_item.return_value = mock_farmer_item_with_bonus
            
            # Call handler
            response = handler(event, mock_context)
            
            # Verify response
            assert response['statusCode'] == 200
            
            body = json.loads(response['body'])
            assert body['bonusesEarned'] == 2000.0
            assert body['consecutiveSalesStreak'] == 10
            assert body['progressToNextBonus'] == '10/10 sales (Bonus earned!)'
            assert body['progressPercentage'] == 100
            assert body['featuredStatus'] is True
            
            # Verify bonus achievement
            sales_streak = body['bonusDetails']['salesStreakBonus']
            assert sales_streak['achieved'] is True
            
            featured = body['bonusDetails']['featuredPlacement']
            assert featured['achieved'] is True
    
    def test_bonus_dashboard_with_no_streak(
        self, valid_event, mock_context, mock_farmer_item_no_streak
    ):
        """Test bonus dashboard when farmer has no sales streak."""
        with patch('referrals.get_farmer_bonuses.get_user_from_token') as mock_auth, \
             patch('referrals.get_farmer_bonuses.get_item') as mock_get_item:
            
            # Update event for different farmer
            event = valid_event.copy()
            event['pathParameters'] = {'farmerId': 'farmer789'}
            
            # Mock authentication
            mock_auth.return_value = {
                'userId': 'farmer789',
                'role': 'farmer'
            }
            
            # Mock DynamoDB query
            mock_get_item.return_value = mock_farmer_item_no_streak
            
            # Call handler
            response = handler(event, mock_context)
            
            # Verify response
            assert response['statusCode'] == 200
            
            body = json.loads(response['body'])
            assert body['bonusesEarned'] == 0.0
            assert body['consecutiveSalesStreak'] == 0
            assert body['progressToNextBonus'] == '0/10 sales'
            assert body['progressPercentage'] == 0
            assert body['featuredStatus'] is False
    
    def test_missing_authorization_header(self, mock_context):
        """Test request without authorization header."""
        event = {
            'headers': {},
            'pathParameters': {'farmerId': 'farmer123'}
        }
        
        response = handler(event, mock_context)
        
        assert response['statusCode'] == 401
        body = json.loads(response['body'])
        assert body['error']['code'] == 'UNAUTHORIZED'
        assert 'Authorization header is required' in body['error']['message']
    
    def test_invalid_token(self, valid_event, mock_context):
        """Test request with invalid JWT token."""
        with patch('referrals.get_farmer_bonuses.get_user_from_token') as mock_auth:
            mock_auth.side_effect = Exception('Invalid token')
            
            response = handler(valid_event, mock_context)
            
            assert response['statusCode'] == 401
            body = json.loads(response['body'])
            assert body['error']['code'] == 'INVALID_TOKEN'
    
    def test_non_farmer_role_forbidden(self, valid_event, mock_context):
        """Test that non-farmer users cannot access the endpoint."""
        with patch('referrals.get_farmer_bonuses.get_user_from_token') as mock_auth:
            # Mock consumer role
            mock_auth.return_value = {
                'userId': 'consumer123',
                'role': 'consumer'
            }
            
            response = handler(valid_event, mock_context)
            
            assert response['statusCode'] == 403
            body = json.loads(response['body'])
            assert body['error']['code'] == 'FORBIDDEN'
            assert 'Only farmers can view bonus dashboard' in body['error']['message']
    
    def test_missing_farmer_id_parameter(self, mock_context):
        """Test request without farmerId in path parameters."""
        event = {
            'headers': {
                'Authorization': 'Bearer valid_token'
            },
            'pathParameters': {}
        }
        
        with patch('referrals.get_farmer_bonuses.get_user_from_token') as mock_auth:
            mock_auth.return_value = {
                'userId': 'farmer123',
                'role': 'farmer'
            }
            
            response = handler(event, mock_context)
            
            assert response['statusCode'] == 400
            body = json.loads(response['body'])
            assert body['error']['code'] == 'INVALID_REQUEST'
            assert 'farmerId is required' in body['error']['message']
    
    def test_farmer_accessing_other_farmer_data(self, valid_event, mock_context):
        """Test that farmers cannot access other farmers' bonus data."""
        with patch('referrals.get_farmer_bonuses.get_user_from_token') as mock_auth:
            # Mock authentication for different farmer
            mock_auth.return_value = {
                'userId': 'farmer999',
                'role': 'farmer'
            }
            
            response = handler(valid_event, mock_context)
            
            assert response['statusCode'] == 403
            body = json.loads(response['body'])
            assert body['error']['code'] == 'FORBIDDEN'
            assert 'You can only view your own bonus dashboard' in body['error']['message']
    
    def test_farmer_not_found(self, valid_event, mock_context):
        """Test when farmer profile is not found in database."""
        with patch('referrals.get_farmer_bonuses.get_user_from_token') as mock_auth, \
             patch('referrals.get_farmer_bonuses.get_item') as mock_get_item:
            
            mock_auth.return_value = {
                'userId': 'farmer123',
                'role': 'farmer'
            }
            
            # Mock DynamoDB returning None
            mock_get_item.return_value = None
            
            response = handler(valid_event, mock_context)
            
            assert response['statusCode'] == 404
            body = json.loads(response['body'])
            assert body['error']['code'] == 'RESOURCE_NOT_FOUND'
            assert 'Farmer profile not found' in body['error']['message']
    
    def test_database_error(self, valid_event, mock_context):
        """Test handling of database errors."""
        with patch('referrals.get_farmer_bonuses.get_user_from_token') as mock_auth, \
             patch('referrals.get_farmer_bonuses.get_item') as mock_get_item:
            
            mock_auth.return_value = {
                'userId': 'farmer123',
                'role': 'farmer'
            }
            
            # Mock DynamoDB error
            mock_get_item.side_effect = Exception('Database connection error')
            
            response = handler(valid_event, mock_context)
            
            assert response['statusCode'] == 503
            body = json.loads(response['body'])
            assert body['error']['code'] == 'SERVICE_UNAVAILABLE'
            assert 'Failed to query farmer profile' in body['error']['message']
    
    def test_farmer_profile_without_bonus_fields(self, valid_event, mock_context):
        """Test handling of farmer profile without bonus fields (defaults)."""
        with patch('referrals.get_farmer_bonuses.get_user_from_token') as mock_auth, \
             patch('referrals.get_farmer_bonuses.get_item') as mock_get_item:
            
            mock_auth.return_value = {
                'userId': 'farmer123',
                'role': 'farmer'
            }
            
            # Mock farmer item without farmerProfile fields
            mock_get_item.return_value = {
                'PK': 'USER#farmer123',
                'SK': 'PROFILE',
                'EntityType': 'User',
                'userId': 'farmer123',
                'email': 'farmer@example.com',
                'role': 'farmer',
                'farmerProfile': {}  # Empty profile
            }
            
            response = handler(valid_event, mock_context)
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            
            # Verify defaults are used
            assert body['bonusesEarned'] == 0.0
            assert body['consecutiveSalesStreak'] == 0
            assert body['featuredStatus'] is False
            assert body['progressToNextBonus'] == '0/10 sales'
    
    def test_cors_headers_present(self, valid_event, mock_context, mock_farmer_item):
        """Test that CORS headers are present in response."""
        with patch('referrals.get_farmer_bonuses.get_user_from_token') as mock_auth, \
             patch('referrals.get_farmer_bonuses.get_item') as mock_get_item:
            
            mock_auth.return_value = {
                'userId': 'farmer123',
                'role': 'farmer'
            }
            mock_get_item.return_value = mock_farmer_item
            
            response = handler(valid_event, mock_context)
            
            assert 'Access-Control-Allow-Origin' in response['headers']
            assert response['headers']['Access-Control-Allow-Origin'] == '*'
    
    def test_progress_calculation_edge_cases(self, valid_event, mock_context):
        """Test progress calculation for various streak values."""
        test_cases = [
            (0, '0/10 sales', 0),
            (1, '1/10 sales', 10),
            (5, '5/10 sales', 50),
            (9, '9/10 sales', 90),
            (10, '10/10 sales (Bonus earned!)', 100),
            (15, '10/10 sales (Bonus earned!)', 100),
        ]
        
        for streak, expected_progress, expected_percentage in test_cases:
            with patch('referrals.get_farmer_bonuses.get_user_from_token') as mock_auth, \
                 patch('referrals.get_farmer_bonuses.get_item') as mock_get_item:
                
                mock_auth.return_value = {
                    'userId': 'farmer123',
                    'role': 'farmer'
                }
                
                mock_get_item.return_value = {
                    'PK': 'USER#farmer123',
                    'SK': 'PROFILE',
                    'EntityType': 'User',
                    'userId': 'farmer123',
                    'email': 'farmer@example.com',
                    'role': 'farmer',
                    'farmerProfile': {
                        'bonusesEarned': 0.0,
                        'consecutiveSalesStreak': streak,
                        'featuredStatus': False
                    }
                }
                
                response = handler(valid_event, mock_context)
                
                assert response['statusCode'] == 200
                body = json.loads(response['body'])
                assert body['progressToNextBonus'] == expected_progress
                assert body['progressPercentage'] == expected_percentage
    
    def test_unexpected_error_handling(self, valid_event, mock_context):
        """Test handling of unexpected errors during database operations."""
        with patch('referrals.get_farmer_bonuses.get_user_from_token') as mock_auth, \
             patch('referrals.get_farmer_bonuses.get_item') as mock_get_item:
            
            # Mock successful authentication
            mock_auth.return_value = {
                'userId': 'farmer123',
                'role': 'farmer'
            }
            
            # Cause an unexpected error during database operation
            mock_get_item.side_effect = RuntimeError('Unexpected database error')
            
            response = handler(valid_event, mock_context)
            
            # Should return 503 for database errors
            assert response['statusCode'] == 503
            body = json.loads(response['body'])
            assert body['error']['code'] == 'SERVICE_UNAVAILABLE'


class TestBonusDashboardIntegration:
    """Integration tests for bonus dashboard with real-world scenarios."""
    
    def test_new_farmer_with_no_activity(self):
        """Test bonus dashboard for a newly registered farmer."""
        event = {
            'headers': {'Authorization': 'Bearer valid_token'},
            'pathParameters': {'farmerId': 'new_farmer'}
        }
        
        with patch('referrals.get_farmer_bonuses.get_user_from_token') as mock_auth, \
             patch('referrals.get_farmer_bonuses.get_item') as mock_get_item:
            
            mock_auth.return_value = {
                'userId': 'new_farmer',
                'role': 'farmer'
            }
            
            mock_get_item.return_value = {
                'PK': 'USER#new_farmer',
                'SK': 'PROFILE',
                'EntityType': 'User',
                'userId': 'new_farmer',
                'email': 'new@example.com',
                'role': 'farmer',
                'farmerProfile': {
                    'farmName': 'New Farm',
                    'bonusesEarned': 0.0,
                    'consecutiveSalesStreak': 0,
                    'featuredStatus': False
                }
            }
            
            response = handler(event, MagicMock())
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            
            # Verify new farmer has zero bonuses and no progress
            assert body['bonusesEarned'] == 0.0
            assert body['consecutiveSalesStreak'] == 0
            assert body['progressPercentage'] == 0
            assert body['featuredStatus'] is False
    
    def test_experienced_farmer_with_multiple_bonuses(self):
        """Test bonus dashboard for an experienced farmer with multiple bonuses."""
        event = {
            'headers': {'Authorization': 'Bearer valid_token'},
            'pathParameters': {'farmerId': 'experienced_farmer'}
        }
        
        with patch('referrals.get_farmer_bonuses.get_user_from_token') as mock_auth, \
             patch('referrals.get_farmer_bonuses.get_item') as mock_get_item:
            
            mock_auth.return_value = {
                'userId': 'experienced_farmer',
                'role': 'farmer'
            }
            
            mock_get_item.return_value = {
                'PK': 'USER#experienced_farmer',
                'SK': 'PROFILE',
                'EntityType': 'User',
                'userId': 'experienced_farmer',
                'email': 'experienced@example.com',
                'role': 'farmer',
                'farmerProfile': {
                    'farmName': 'Veteran Farm',
                    'bonusesEarned': Decimal('5000.0'),  # Multiple bonuses earned
                    'consecutiveSalesStreak': 25,  # Well beyond threshold
                    'featuredStatus': True
                }
            }
            
            response = handler(event, MagicMock())
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            
            # Verify experienced farmer data
            assert body['bonusesEarned'] == 5000.0
            assert body['consecutiveSalesStreak'] == 25
            assert body['progressPercentage'] == 100
            assert body['featuredStatus'] is True
            assert body['bonusDetails']['salesStreakBonus']['achieved'] is True
            assert body['bonusDetails']['featuredPlacement']['achieved'] is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
