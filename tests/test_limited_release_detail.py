"""
Unit tests for limited release detail endpoint.
Tests GET /limited-releases/{releaseId} functionality.
"""
import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend', 'limited_releases'))

from get_limited_release_detail import handler, calculate_time_remaining


@pytest.fixture
def mock_env(monkeypatch):
    """Set up environment variables."""
    monkeypatch.setenv('DYNAMODB_TABLE_NAME', 'RootTrustData')
    monkeypatch.setenv('AWS_REGION', 'us-east-1')


@pytest.fixture
def mock_release():
    """Mock limited release from database."""
    now = datetime.utcnow()
    return {
        'PK': 'LIMITED_RELEASE#release-123',
        'SK': 'METADATA',
        'releaseId': 'release-123',
        'farmerId': 'farmer-456',
        'productId': 'product-789',
        'releaseName': 'Spring Harvest Special',
        'quantityLimit': 50,
        'quantityRemaining': 30,
        'duration': 7,
        'status': 'active',
        'startDate': now.isoformat(),
        'endDate': (now + timedelta(days=7)).isoformat(),
        'subscriberNotificationsSent': True,
        'createdAt': now.isoformat(),
        'GSI2PK': 'FARMER#farmer-456',
        'GSI2SK': f"RELEASE#{now.isoformat()}",
        'GSI3PK': 'STATUS#active',
        'GSI3SK': f"RELEASE#{(now + timedelta(days=7)).isoformat()}"
    }


@pytest.fixture
def mock_product():
    """Mock product from database."""
    return {
        'PK': 'PRODUCT#product-789',
        'SK': 'METADATA',
        'productId': 'product-789',
        'farmerId': 'farmer-456',
        'name': 'Organic Tomatoes',
        'category': 'vegetables',
        'price': 150.0,
        'unit': 'kg',
        'description': 'Fresh organic tomatoes from our farm',
        'images': [
            {'url': 'https://s3.amazonaws.com/image1.jpg', 'isPrimary': True}
        ],
        'averageRating': 4.5,
        'giTag': {
            'hasTag': True,
            'tagName': 'Nashik Tomato',
            'region': 'Nashik'
        },
        'verificationStatus': 'approved',
        'authenticityConfidence': 95
    }


class TestLimitedReleaseDetail:
    """Test cases for limited release detail endpoint."""
    
    @patch('get_limited_release_detail.get_item')
    def test_get_release_detail_success(
        self,
        mock_get_item,
        mock_env,
        mock_release,
        mock_product
    ):
        """Test successful retrieval of limited release details."""
        # Setup mocks
        def get_item_side_effect(pk, sk):
            if pk.startswith('LIMITED_RELEASE#'):
                return mock_release
            elif pk.startswith('PRODUCT#'):
                return mock_product
            return None
        
        mock_get_item.side_effect = get_item_side_effect
        
        # Create event
        event = {
            'pathParameters': {
                'releaseId': 'release-123'
            }
        }
        
        # Execute handler
        response = handler(event, {})
        
        # Assertions
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        
        # Verify release fields
        assert body['releaseId'] == 'release-123'
        assert body['farmerId'] == 'farmer-456'
        assert body['productId'] == 'product-789'
        assert body['releaseName'] == 'Spring Harvest Special'
        assert body['quantityLimit'] == 50
        assert body['quantityRemaining'] == 30
        assert body['duration'] == 7
        assert body['status'] == 'active'
        assert 'startDate' in body
        assert 'endDate' in body
        assert 'createdAt' in body
        assert body['subscriberNotificationsSent'] is True
        
        # Verify countdown is present
        assert 'countdown' in body
        countdown = body['countdown']
        assert 'expired' in countdown
        assert 'daysRemaining' in countdown
        assert 'hoursRemaining' in countdown
        assert 'minutesRemaining' in countdown
        assert 'secondsRemaining' in countdown
        assert 'totalSeconds' in countdown
        
        # Verify product details are included
        assert 'product' in body
        product = body['product']
        assert product['name'] == 'Organic Tomatoes'
        assert product['category'] == 'vegetables'
        assert product['price'] == 150.0
        assert product['unit'] == 'kg'
        assert product['description'] == 'Fresh organic tomatoes from our farm'
        assert len(product['images']) == 1
        assert product['averageRating'] == 4.5
        assert product['giTag']['hasTag'] is True
        assert product['verificationStatus'] == 'approved'
        assert product['authenticityConfidence'] == 95
        
        # Verify get_item was called correctly
        assert mock_get_item.call_count == 2
        calls = mock_get_item.call_args_list
        assert calls[0][0] == ('LIMITED_RELEASE#release-123', 'METADATA')
        assert calls[1][0] == ('PRODUCT#product-789', 'METADATA')
    
    @patch('get_limited_release_detail.get_item')
    def test_get_release_detail_without_product(
        self,
        mock_get_item,
        mock_env,
        mock_release
    ):
        """Test retrieval when product details are not available."""
        # Setup mocks - product query returns None
        def get_item_side_effect(pk, sk):
            if pk.startswith('LIMITED_RELEASE#'):
                return mock_release
            elif pk.startswith('PRODUCT#'):
                return None
            return None
        
        mock_get_item.side_effect = get_item_side_effect
        
        # Create event
        event = {
            'pathParameters': {
                'releaseId': 'release-123'
            }
        }
        
        # Execute handler
        response = handler(event, {})
        
        # Assertions
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        
        # Verify release fields are present
        assert body['releaseId'] == 'release-123'
        assert body['releaseName'] == 'Spring Harvest Special'
        
        # Product details should not be included
        assert 'product' not in body
    
    @patch('get_limited_release_detail.get_item')
    def test_get_release_detail_product_query_error(
        self,
        mock_get_item,
        mock_env,
        mock_release
    ):
        """Test that product query errors don't fail the request."""
        # Setup mocks - product query raises exception
        def get_item_side_effect(pk, sk):
            if pk.startswith('LIMITED_RELEASE#'):
                return mock_release
            elif pk.startswith('PRODUCT#'):
                raise Exception("Database error")
            return None
        
        mock_get_item.side_effect = get_item_side_effect
        
        # Create event
        event = {
            'pathParameters': {
                'releaseId': 'release-123'
            }
        }
        
        # Execute handler
        response = handler(event, {})
        
        # Should succeed without product details
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['releaseId'] == 'release-123'
        assert 'product' not in body
    
    def test_missing_release_id(self, mock_env):
        """Test request without releaseId in path parameters."""
        event = {
            'pathParameters': {}
        }
        
        response = handler(event, {})
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error']['code'] == 'BAD_REQUEST'
        assert 'releaseId' in body['error']['message']
    
    def test_missing_path_parameters(self, mock_env):
        """Test request without path parameters."""
        event = {}
        
        response = handler(event, {})
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error']['code'] == 'BAD_REQUEST'
    
    @patch('get_limited_release_detail.get_item')
    def test_release_not_found(self, mock_get_item, mock_env):
        """Test request for non-existent release."""
        mock_get_item.return_value = None
        
        event = {
            'pathParameters': {
                'releaseId': 'nonexistent-release'
            }
        }
        
        response = handler(event, {})
        
        assert response['statusCode'] == 404
        body = json.loads(response['body'])
        assert body['error']['code'] == 'NOT_FOUND'
        assert 'nonexistent-release' in body['error']['message']
    
    @patch('get_limited_release_detail.get_item')
    def test_database_error(self, mock_get_item, mock_env):
        """Test handling of database errors."""
        from backend.shared.exceptions import ServiceUnavailableError
        
        mock_get_item.side_effect = ServiceUnavailableError('DynamoDB', 'Service unavailable')
        
        event = {
            'pathParameters': {
                'releaseId': 'release-123'
            }
        }
        
        response = handler(event, {})
        
        assert response['statusCode'] == 503
        body = json.loads(response['body'])
        assert body['error']['code'] == 'SERVICE_UNAVAILABLE'
    
    @patch('get_limited_release_detail.get_item')
    def test_countdown_calculation_included(
        self,
        mock_get_item,
        mock_env,
        mock_release
    ):
        """Test that countdown is calculated and included in response."""
        mock_get_item.return_value = mock_release
        
        event = {
            'pathParameters': {
                'releaseId': 'release-123'
            }
        }
        
        response = handler(event, {})
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        
        # Verify countdown structure
        countdown = body['countdown']
        assert isinstance(countdown['expired'], bool)
        assert isinstance(countdown['daysRemaining'], int)
        assert isinstance(countdown['hoursRemaining'], int)
        assert isinstance(countdown['minutesRemaining'], int)
        assert isinstance(countdown['secondsRemaining'], int)
        assert isinstance(countdown['totalSeconds'], int)
        
        # Should not be expired (7 days in future)
        assert countdown['expired'] is False
        assert countdown['daysRemaining'] >= 6  # Allow for timing differences
    
    @patch('get_limited_release_detail.get_item')
    def test_expired_release_countdown(self, mock_get_item, mock_env):
        """Test countdown for expired release."""
        # Create expired release
        now = datetime.utcnow()
        expired_release = {
            'PK': 'LIMITED_RELEASE#release-expired',
            'SK': 'METADATA',
            'releaseId': 'release-expired',
            'farmerId': 'farmer-456',
            'productId': 'product-789',
            'releaseName': 'Expired Release',
            'quantityLimit': 50,
            'quantityRemaining': 0,
            'duration': 7,
            'status': 'expired',
            'startDate': (now - timedelta(days=10)).isoformat(),
            'endDate': (now - timedelta(days=3)).isoformat(),  # Expired 3 days ago
            'subscriberNotificationsSent': True,
            'createdAt': (now - timedelta(days=10)).isoformat()
        }
        
        mock_get_item.return_value = expired_release
        
        event = {
            'pathParameters': {
                'releaseId': 'release-expired'
            }
        }
        
        response = handler(event, {})
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        
        # Verify countdown shows expired
        countdown = body['countdown']
        assert countdown['expired'] is True
        assert countdown['daysRemaining'] == 0
        assert countdown['hoursRemaining'] == 0
        assert countdown['minutesRemaining'] == 0
        assert countdown['secondsRemaining'] == 0
        assert countdown['totalSeconds'] == 0
    
    @patch('get_limited_release_detail.get_item')
    def test_release_without_end_date(self, mock_get_item, mock_env):
        """Test handling of release without endDate."""
        release_no_end = {
            'PK': 'LIMITED_RELEASE#release-no-end',
            'SK': 'METADATA',
            'releaseId': 'release-no-end',
            'farmerId': 'farmer-456',
            'productId': 'product-789',
            'releaseName': 'No End Date Release',
            'quantityLimit': 50,
            'quantityRemaining': 30,
            'duration': 7,
            'status': 'active',
            'startDate': datetime.utcnow().isoformat(),
            # No endDate field
            'subscriberNotificationsSent': True,
            'createdAt': datetime.utcnow().isoformat()
        }
        
        mock_get_item.return_value = release_no_end
        
        event = {
            'pathParameters': {
                'releaseId': 'release-no-end'
            }
        }
        
        response = handler(event, {})
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        
        # Should have countdown with default values
        assert 'countdown' in body
        countdown = body['countdown']
        assert countdown['daysRemaining'] == 0
        assert countdown['totalSeconds'] == 0
    
    @patch('get_limited_release_detail.get_item')
    def test_all_release_fields_included(
        self,
        mock_get_item,
        mock_env,
        mock_release,
        mock_product
    ):
        """Test that all required release fields are included in response."""
        def get_item_side_effect(pk, sk):
            if pk.startswith('LIMITED_RELEASE#'):
                return mock_release
            elif pk.startswith('PRODUCT#'):
                return mock_product
            return None
        
        mock_get_item.side_effect = get_item_side_effect
        
        event = {
            'pathParameters': {
                'releaseId': 'release-123'
            }
        }
        
        response = handler(event, {})
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        
        # Verify all required fields
        required_fields = [
            'releaseId', 'farmerId', 'productId', 'releaseName',
            'quantityLimit', 'quantityRemaining', 'duration',
            'status', 'startDate', 'endDate', 'countdown',
            'subscriberNotificationsSent', 'createdAt'
        ]
        
        for field in required_fields:
            assert field in body, f"Missing required field: {field}"
    
    @patch('get_limited_release_detail.get_item')
    def test_quantity_remaining_displayed(
        self,
        mock_get_item,
        mock_env,
        mock_release
    ):
        """Test that quantityRemaining is correctly displayed."""
        mock_get_item.return_value = mock_release
        
        event = {
            'pathParameters': {
                'releaseId': 'release-123'
            }
        }
        
        response = handler(event, {})
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        
        assert body['quantityLimit'] == 50
        assert body['quantityRemaining'] == 30
    
    @patch('get_limited_release_detail.get_item')
    def test_cors_headers_present(self, mock_get_item, mock_env, mock_release):
        """Test that CORS headers are present in response."""
        mock_get_item.return_value = mock_release
        
        event = {
            'pathParameters': {
                'releaseId': 'release-123'
            }
        }
        
        response = handler(event, {})
        
        assert 'Access-Control-Allow-Origin' in response['headers']
        assert response['headers']['Access-Control-Allow-Origin'] == '*'
        assert response['headers']['Content-Type'] == 'application/json'


class TestTimeRemainingCalculation:
    """Test cases for time remaining calculation logic."""
    
    def test_calculate_time_remaining_future_date(self):
        """Test calculation for future end date."""
        # Create end date 5 days, 3 hours, 30 minutes in the future
        future_date = datetime.utcnow() + timedelta(days=5, hours=3, minutes=30)
        end_date_str = future_date.isoformat()
        
        result = calculate_time_remaining(end_date_str)
        
        assert result['expired'] is False
        assert result['daysRemaining'] == 5
        assert result['hoursRemaining'] == 3
        # Allow for small timing differences (within 1 minute)
        assert result['minutesRemaining'] >= 29
        assert result['minutesRemaining'] <= 30
        assert result['totalSeconds'] > 0
    
    def test_calculate_time_remaining_past_date(self):
        """Test calculation for past end date."""
        # Create end date 2 days in the past
        past_date = datetime.utcnow() - timedelta(days=2)
        end_date_str = past_date.isoformat()
        
        result = calculate_time_remaining(end_date_str)
        
        assert result['expired'] is True
        assert result['daysRemaining'] == 0
        assert result['hoursRemaining'] == 0
        assert result['minutesRemaining'] == 0
        assert result['secondsRemaining'] == 0
        assert result['totalSeconds'] == 0
    
    def test_calculate_time_remaining_with_z_suffix(self):
        """Test calculation with Z suffix in ISO date."""
        future_date = datetime.utcnow() + timedelta(days=3)
        end_date_str = future_date.isoformat() + 'Z'
        
        result = calculate_time_remaining(end_date_str)
        
        assert result['expired'] is False
        assert result['daysRemaining'] >= 2
        assert result['daysRemaining'] <= 3
    
    def test_calculate_time_remaining_exact_expiry(self):
        """Test calculation when release is expiring right now."""
        now = datetime.utcnow()
        end_date_str = now.isoformat()
        
        result = calculate_time_remaining(end_date_str)
        
        # Should be expired or very close to expiry
        assert result['daysRemaining'] == 0
    
    def test_calculate_time_remaining_invalid_date(self):
        """Test calculation with invalid date string."""
        result = calculate_time_remaining('invalid-date-string')
        
        # Should return default values without crashing
        assert 'expired' in result
        assert 'daysRemaining' in result
        assert result['daysRemaining'] == 0
        assert result['totalSeconds'] == 0
    
    def test_calculate_time_remaining_one_hour(self):
        """Test calculation for release ending in one hour."""
        future_date = datetime.utcnow() + timedelta(hours=1)
        end_date_str = future_date.isoformat()
        
        result = calculate_time_remaining(end_date_str)
        
        assert result['expired'] is False
        assert result['daysRemaining'] == 0
        assert result['hoursRemaining'] >= 0
        assert result['hoursRemaining'] <= 1
        assert result['totalSeconds'] > 0
        assert result['totalSeconds'] <= 3600
    
    def test_calculate_time_remaining_exact_days(self):
        """Test calculation for exact number of days."""
        # Exactly 7 days in the future
        future_date = datetime.utcnow() + timedelta(days=7)
        end_date_str = future_date.isoformat()
        
        result = calculate_time_remaining(end_date_str)
        
        assert result['expired'] is False
        assert result['daysRemaining'] >= 6  # Allow for small timing differences
        assert result['daysRemaining'] <= 7
    
    def test_calculate_time_remaining_includes_all_fields(self):
        """Test that all required fields are present in result."""
        future_date = datetime.utcnow() + timedelta(days=1)
        end_date_str = future_date.isoformat()
        
        result = calculate_time_remaining(end_date_str)
        
        required_fields = [
            'expired', 'daysRemaining', 'hoursRemaining',
            'minutesRemaining', 'secondsRemaining', 'totalSeconds'
        ]
        
        for field in required_fields:
            assert field in result, f"Missing required field: {field}"
    
    def test_calculate_time_remaining_total_seconds_accuracy(self):
        """Test that totalSeconds is calculated accurately."""
        # 2 days, 5 hours, 30 minutes = 183000 seconds
        future_date = datetime.utcnow() + timedelta(days=2, hours=5, minutes=30)
        end_date_str = future_date.isoformat()
        
        result = calculate_time_remaining(end_date_str)
        
        expected_seconds = (2 * 24 * 3600) + (5 * 3600) + (30 * 60)
        # Allow for small timing differences (within 60 seconds)
        assert abs(result['totalSeconds'] - expected_seconds) < 60
    
    def test_calculate_time_remaining_boundary_midnight(self):
        """Test calculation across midnight boundary."""
        # End date is tomorrow at 1 AM
        now = datetime.utcnow()
        tomorrow = now.replace(hour=1, minute=0, second=0, microsecond=0) + timedelta(days=1)
        end_date_str = tomorrow.isoformat()
        
        result = calculate_time_remaining(end_date_str)
        
        assert result['expired'] is False
        # Should be at least 0 days (could be 0 or 1 depending on current time)
        assert result['daysRemaining'] >= 0
        assert result['totalSeconds'] > 0


class TestResponseStructure:
    """Test cases for response structure and format."""
    
    @patch('get_limited_release_detail.get_item')
    def test_response_json_format(
        self,
        mock_get_item,
        mock_env,
        mock_release
    ):
        """Test that response is valid JSON."""
        mock_get_item.return_value = mock_release
        
        event = {
            'pathParameters': {
                'releaseId': 'release-123'
            }
        }
        
        response = handler(event, {})
        
        # Should be able to parse JSON
        body = json.loads(response['body'])
        assert isinstance(body, dict)
    
    @patch('get_limited_release_detail.get_item')
    def test_error_response_format(self, mock_get_item, mock_env):
        """Test that error responses have consistent format."""
        mock_get_item.return_value = None
        
        event = {
            'pathParameters': {
                'releaseId': 'nonexistent'
            }
        }
        
        response = handler(event, {})
        
        body = json.loads(response['body'])
        assert 'error' in body
        assert 'code' in body['error']
        assert 'message' in body['error']
    
    @patch('get_limited_release_detail.get_item')
    def test_product_details_structure(
        self,
        mock_get_item,
        mock_env,
        mock_release,
        mock_product
    ):
        """Test that product details have correct structure."""
        def get_item_side_effect(pk, sk):
            if pk.startswith('LIMITED_RELEASE#'):
                return mock_release
            elif pk.startswith('PRODUCT#'):
                return mock_product
            return None
        
        mock_get_item.side_effect = get_item_side_effect
        
        event = {
            'pathParameters': {
                'releaseId': 'release-123'
            }
        }
        
        response = handler(event, {})
        
        body = json.loads(response['body'])
        product = body['product']
        
        # Verify product structure
        required_product_fields = [
            'name', 'category', 'price', 'unit', 'description',
            'images', 'averageRating', 'giTag', 'verificationStatus',
            'authenticityConfidence'
        ]
        
        for field in required_product_fields:
            assert field in product, f"Missing product field: {field}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
