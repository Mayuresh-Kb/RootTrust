"""
Unit tests for active limited releases listing endpoint.
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

from shared.constants import LimitedReleaseStatus


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Set up environment variables for tests."""
    monkeypatch.setenv('DYNAMODB_TABLE_NAME', 'RootTrustData-test')


@pytest.fixture
def mock_active_releases():
    """Mock active limited releases data."""
    now = datetime.utcnow()
    return [
        {
            'PK': 'LIMITED_RELEASE#release-1',
            'SK': 'METADATA',
            'releaseId': 'release-1',
            'farmerId': 'farmer-1',
            'productId': 'product-1',
            'releaseName': 'Spring Harvest Special',
            'quantityLimit': 50,
            'quantityRemaining': 30,
            'duration': 7,
            'status': 'active',
            'startDate': now.isoformat(),
            'endDate': (now + timedelta(days=7)).isoformat(),
            'subscriberNotificationsSent': True,
            'GSI3PK': 'STATUS#active',
            'GSI3SK': f"RELEASE#{(now + timedelta(days=7)).isoformat()}"
        },
        {
            'PK': 'LIMITED_RELEASE#release-2',
            'SK': 'METADATA',
            'releaseId': 'release-2',
            'farmerId': 'farmer-2',
            'productId': 'product-2',
            'releaseName': 'Exclusive Mango Drop',
            'quantityLimit': 100,
            'quantityRemaining': 75,
            'duration': 5,
            'status': 'active',
            'startDate': now.isoformat(),
            'endDate': (now + timedelta(days=5)).isoformat(),
            'subscriberNotificationsSent': True,
            'GSI3PK': 'STATUS#active',
            'GSI3SK': f"RELEASE#{(now + timedelta(days=5)).isoformat()}"
        }
    ]


@pytest.fixture
def mock_products():
    """Mock product data."""
    return {
        'product-1': {
            'PK': 'PRODUCT#product-1',
            'SK': 'METADATA',
            'productId': 'product-1',
            'name': 'Organic Tomatoes',
            'category': 'vegetables',
            'price': 50.0,
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
            }
        },
        'product-2': {
            'PK': 'PRODUCT#product-2',
            'SK': 'METADATA',
            'productId': 'product-2',
            'name': 'Alphonso Mangoes',
            'category': 'fruits',
            'price': 200.0,
            'unit': 'dozen',
            'description': 'Premium Alphonso mangoes',
            'images': [
                {'url': 'https://s3.amazonaws.com/image2.jpg', 'isPrimary': True}
            ],
            'averageRating': 4.9,
            'giTag': {
                'hasTag': True,
                'tagName': 'Ratnagiri Alphonso',
                'region': 'Ratnagiri'
            }
        }
    }


class TestActiveLimitedReleasesListing:
    """Test cases for active limited releases listing endpoint."""
    
    def test_list_active_releases_success(
        self, mock_env_vars, mock_active_releases, mock_products
    ):
        """Test successful listing of active limited releases."""
        # Import after env vars are set
        from limited_releases.list_active_limited_releases import handler
        
        # Mock dependencies
        with patch('limited_releases.list_active_limited_releases.query') as mock_query, \
             patch('limited_releases.list_active_limited_releases.get_item') as mock_get:
            
            # Setup mocks
            mock_query.return_value = {
                'Items': mock_active_releases
            }
            
            # Mock get_item to return products
            def get_item_side_effect(pk, sk):
                product_id = pk.replace('PRODUCT#', '')
                return mock_products.get(product_id)
            
            mock_get.side_effect = get_item_side_effect
            
            # Create event
            event = {
                'queryStringParameters': None
            }
            
            # Call handler
            response = handler(event, None)
            
            # Assertions
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert 'releases' in body
            assert 'count' in body
            assert body['count'] == 2
            assert len(body['releases']) == 2
            
            # Verify first release
            release1 = body['releases'][0]
            assert release1['releaseId'] == 'release-1'
            assert release1['productId'] == 'product-1'
            assert release1['releaseName'] == 'Spring Harvest Special'
            assert release1['quantityLimit'] == 50
            assert release1['quantityRemaining'] == 30
            assert release1['status'] == 'active'
            
            # Verify product details
            assert 'product' in release1
            assert release1['product']['name'] == 'Organic Tomatoes'
            assert release1['product']['category'] == 'vegetables'
            assert release1['product']['price'] == 50.0
            assert release1['product']['unit'] == 'kg'
            assert release1['product']['averageRating'] == 4.5
            assert release1['product']['giTag']['hasTag'] is True
            
            # Verify countdown is present
            assert 'countdown' in release1
            assert 'daysRemaining' in release1['countdown']
            assert 'hoursRemaining' in release1['countdown']
            assert 'expired' in release1['countdown']
            
            # Verify query was called with correct parameters
            mock_query.assert_called_once()
            call_kwargs = mock_query.call_args[1]
            assert call_kwargs['index_name'] == 'GSI3'
            assert call_kwargs['limit'] == 50
            assert call_kwargs['scan_index_forward'] is False
    
    def test_list_active_releases_empty(self, mock_env_vars):
        """Test listing when no active releases exist."""
        from limited_releases.list_active_limited_releases import handler
        
        with patch('limited_releases.list_active_limited_releases.query') as mock_query:
            mock_query.return_value = {
                'Items': []
            }
            
            event = {
                'queryStringParameters': None
            }
            
            response = handler(event, None)
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert body['releases'] == []
            assert body['count'] == 0
            assert 'nextCursor' not in body
    
    def test_list_active_releases_with_pagination(
        self, mock_env_vars, mock_active_releases, mock_products
    ):
        """Test listing with pagination parameters."""
        from limited_releases.list_active_limited_releases import handler
        
        with patch('limited_releases.list_active_limited_releases.query') as mock_query, \
             patch('limited_releases.list_active_limited_releases.get_item') as mock_get:
            
            # Mock query with LastEvaluatedKey
            mock_query.return_value = {
                'Items': [mock_active_releases[0]],
                'LastEvaluatedKey': {
                    'PK': 'LIMITED_RELEASE#release-1',
                    'SK': 'METADATA',
                    'GSI3PK': 'STATUS#active',
                    'GSI3SK': 'RELEASE#2024-01-01T00:00:00'
                }
            }
            
            def get_item_side_effect(pk, sk):
                product_id = pk.replace('PRODUCT#', '')
                return mock_products.get(product_id)
            
            mock_get.side_effect = get_item_side_effect
            
            event = {
                'queryStringParameters': {
                    'limit': '1'
                }
            }
            
            response = handler(event, None)
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert body['count'] == 1
            assert 'nextCursor' in body
            
            # Verify cursor is base64 encoded
            import base64
            cursor_data = json.loads(base64.b64decode(body['nextCursor']).decode('utf-8'))
            assert 'PK' in cursor_data
            assert cursor_data['PK'] == 'LIMITED_RELEASE#release-1'
    
    def test_list_active_releases_with_cursor(
        self, mock_env_vars, mock_active_releases, mock_products
    ):
        """Test listing with pagination cursor."""
        from limited_releases.list_active_limited_releases import handler
        
        with patch('limited_releases.list_active_limited_releases.query') as mock_query, \
             patch('limited_releases.list_active_limited_releases.get_item') as mock_get:
            
            mock_query.return_value = {
                'Items': [mock_active_releases[1]]
            }
            
            def get_item_side_effect(pk, sk):
                product_id = pk.replace('PRODUCT#', '')
                return mock_products.get(product_id)
            
            mock_get.side_effect = get_item_side_effect
            
            # Create valid cursor
            import base64
            cursor_data = {
                'PK': 'LIMITED_RELEASE#release-1',
                'SK': 'METADATA',
                'GSI3PK': 'STATUS#active',
                'GSI3SK': 'RELEASE#2024-01-01T00:00:00'
            }
            cursor = base64.b64encode(json.dumps(cursor_data).encode('utf-8')).decode('utf-8')
            
            event = {
                'queryStringParameters': {
                    'cursor': cursor
                }
            }
            
            response = handler(event, None)
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert body['count'] == 1
            
            # Verify query was called with exclusive_start_key
            call_kwargs = mock_query.call_args[1]
            assert call_kwargs['exclusive_start_key'] == cursor_data
    
    def test_list_active_releases_invalid_cursor(
        self, mock_env_vars, mock_active_releases, mock_products
    ):
        """Test listing with invalid cursor (should continue without cursor)."""
        from limited_releases.list_active_limited_releases import handler
        
        with patch('limited_releases.list_active_limited_releases.query') as mock_query, \
             patch('limited_releases.list_active_limited_releases.get_item') as mock_get:
            
            mock_query.return_value = {
                'Items': mock_active_releases
            }
            
            def get_item_side_effect(pk, sk):
                product_id = pk.replace('PRODUCT#', '')
                return mock_products.get(product_id)
            
            mock_get.side_effect = get_item_side_effect
            
            event = {
                'queryStringParameters': {
                    'cursor': 'invalid-cursor-data'
                }
            }
            
            response = handler(event, None)
            
            # Should succeed and return results without cursor
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert body['count'] == 2
    
    def test_list_active_releases_custom_limit(
        self, mock_env_vars, mock_active_releases, mock_products
    ):
        """Test listing with custom limit parameter."""
        from limited_releases.list_active_limited_releases import handler
        
        with patch('limited_releases.list_active_limited_releases.query') as mock_query, \
             patch('limited_releases.list_active_limited_releases.get_item') as mock_get:
            
            mock_query.return_value = {
                'Items': [mock_active_releases[0]]
            }
            
            def get_item_side_effect(pk, sk):
                product_id = pk.replace('PRODUCT#', '')
                return mock_products.get(product_id)
            
            mock_get.side_effect = get_item_side_effect
            
            event = {
                'queryStringParameters': {
                    'limit': '10'
                }
            }
            
            response = handler(event, None)
            
            assert response['statusCode'] == 200
            
            # Verify query was called with correct limit
            call_kwargs = mock_query.call_args[1]
            assert call_kwargs['limit'] == 10
    
    def test_list_active_releases_limit_validation(
        self, mock_env_vars, mock_active_releases, mock_products
    ):
        """Test that invalid limits are normalized."""
        from limited_releases.list_active_limited_releases import handler
        
        with patch('limited_releases.list_active_limited_releases.query') as mock_query, \
             patch('limited_releases.list_active_limited_releases.get_item') as mock_get:
            
            mock_query.return_value = {
                'Items': mock_active_releases
            }
            
            def get_item_side_effect(pk, sk):
                product_id = pk.replace('PRODUCT#', '')
                return mock_products.get(product_id)
            
            mock_get.side_effect = get_item_side_effect
            
            # Test limit too high
            event = {
                'queryStringParameters': {
                    'limit': '200'
                }
            }
            
            response = handler(event, None)
            assert response['statusCode'] == 200
            
            # Verify limit was normalized to 50
            call_kwargs = mock_query.call_args[1]
            assert call_kwargs['limit'] == 50
    
    def test_list_active_releases_product_not_found(
        self, mock_env_vars, mock_active_releases
    ):
        """Test listing when product is not found (should skip that release)."""
        from limited_releases.list_active_limited_releases import handler
        
        with patch('limited_releases.list_active_limited_releases.query') as mock_query, \
             patch('limited_releases.list_active_limited_releases.get_item') as mock_get:
            
            mock_query.return_value = {
                'Items': mock_active_releases
            }
            
            # Mock get_item to return None (product not found)
            mock_get.return_value = None
            
            event = {
                'queryStringParameters': None
            }
            
            response = handler(event, None)
            
            # Should succeed but with no releases (all skipped)
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert body['count'] == 0
            assert body['releases'] == []
    
    def test_list_active_releases_partial_product_failure(
        self, mock_env_vars, mock_active_releases, mock_products
    ):
        """Test listing when some products fail to load."""
        from limited_releases.list_active_limited_releases import handler
        
        with patch('limited_releases.list_active_limited_releases.query') as mock_query, \
             patch('limited_releases.list_active_limited_releases.get_item') as mock_get:
            
            mock_query.return_value = {
                'Items': mock_active_releases
            }
            
            # First call succeeds, second fails
            mock_get.side_effect = [
                mock_products['product-1'],
                None  # Second product not found
            ]
            
            event = {
                'queryStringParameters': None
            }
            
            response = handler(event, None)
            
            # Should succeed with only the first release
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert body['count'] == 1
            assert body['releases'][0]['productId'] == 'product-1'
    
    def test_list_active_releases_query_error(self, mock_env_vars):
        """Test listing when DynamoDB query fails."""
        from limited_releases.list_active_limited_releases import handler
        from backend.shared.exceptions import ServiceUnavailableError
        
        with patch('limited_releases.list_active_limited_releases.query') as mock_query:
            mock_query.side_effect = ServiceUnavailableError('DynamoDB', 'Service unavailable')
            
            event = {
                'queryStringParameters': None
            }
            
            response = handler(event, None)
            
            assert response['statusCode'] == 503
            body = json.loads(response['body'])
            assert body['error']['code'] == 'SERVICE_UNAVAILABLE'
    
    def test_list_active_releases_enrichment_error(
        self, mock_env_vars, mock_active_releases, mock_products
    ):
        """Test listing when product enrichment fails for one release."""
        from limited_releases.list_active_limited_releases import handler
        
        with patch('limited_releases.list_active_limited_releases.query') as mock_query, \
             patch('limited_releases.list_active_limited_releases.get_item') as mock_get:
            
            mock_query.return_value = {
                'Items': mock_active_releases
            }
            
            # First call succeeds, second raises exception
            mock_get.side_effect = [
                mock_products['product-1'],
                Exception('Database error')
            ]
            
            event = {
                'queryStringParameters': None
            }
            
            response = handler(event, None)
            
            # Should succeed with only the first release
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert body['count'] == 1
            assert body['releases'][0]['productId'] == 'product-1'
    
    def test_list_active_releases_no_query_params(
        self, mock_env_vars, mock_active_releases, mock_products
    ):
        """Test listing without any query parameters."""
        from limited_releases.list_active_limited_releases import handler
        
        with patch('limited_releases.list_active_limited_releases.query') as mock_query, \
             patch('limited_releases.list_active_limited_releases.get_item') as mock_get:
            
            mock_query.return_value = {
                'Items': mock_active_releases
            }
            
            def get_item_side_effect(pk, sk):
                product_id = pk.replace('PRODUCT#', '')
                return mock_products.get(product_id)
            
            mock_get.side_effect = get_item_side_effect
            
            # No queryStringParameters at all
            event = {}
            
            response = handler(event, None)
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert body['count'] == 2
    
    def test_list_active_releases_includes_all_fields(
        self, mock_env_vars, mock_active_releases, mock_products
    ):
        """Test that all required fields are included in response."""
        from limited_releases.list_active_limited_releases import handler
        
        with patch('limited_releases.list_active_limited_releases.query') as mock_query, \
             patch('limited_releases.list_active_limited_releases.get_item') as mock_get:
            
            mock_query.return_value = {
                'Items': [mock_active_releases[0]]
            }
            
            mock_get.return_value = mock_products['product-1']
            
            event = {
                'queryStringParameters': None
            }
            
            response = handler(event, None)
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            
            release = body['releases'][0]
            
            # Verify release fields
            assert 'releaseId' in release
            assert 'farmerId' in release
            assert 'productId' in release
            assert 'releaseName' in release
            assert 'quantityLimit' in release
            assert 'quantityRemaining' in release
            assert 'duration' in release
            assert 'status' in release
            assert 'startDate' in release
            assert 'endDate' in release
            assert 'countdown' in release
            
            # Verify product fields
            assert 'product' in release
            product = release['product']
            assert 'name' in product
            assert 'category' in product
            assert 'price' in product
            assert 'unit' in product
            assert 'images' in product
            assert 'averageRating' in product
            assert 'giTag' in product
            assert 'description' in product
    
    def test_countdown_calculation_future_date(self, mock_env_vars):
        """Test countdown calculation for future end date."""
        from limited_releases.list_active_limited_releases import calculate_countdown
        
        # Create end date 5 days in the future
        future_date = datetime.utcnow() + timedelta(days=5, hours=3, minutes=30)
        end_date_str = future_date.isoformat()
        
        countdown = calculate_countdown(end_date_str)
        
        assert countdown['expired'] is False
        assert countdown['daysRemaining'] == 5
        assert countdown['hoursRemaining'] == 3
        # Allow for small timing differences (within 1 minute)
        assert countdown['minutesRemaining'] >= 29
        assert countdown['minutesRemaining'] <= 30
        assert 'totalSeconds' in countdown
        assert countdown['totalSeconds'] > 0
    
    def test_countdown_calculation_past_date(self, mock_env_vars):
        """Test countdown calculation for past end date."""
        from limited_releases.list_active_limited_releases import calculate_countdown
        
        # Create end date in the past
        past_date = datetime.utcnow() - timedelta(days=2)
        end_date_str = past_date.isoformat()
        
        countdown = calculate_countdown(end_date_str)
        
        assert countdown['expired'] is True
        assert countdown['daysRemaining'] == 0
        assert countdown['hoursRemaining'] == 0
        assert countdown['minutesRemaining'] == 0
        assert countdown['secondsRemaining'] == 0
    
    def test_countdown_calculation_invalid_date(self, mock_env_vars):
        """Test countdown calculation with invalid date string."""
        from limited_releases.list_active_limited_releases import calculate_countdown
        
        countdown = calculate_countdown('invalid-date')
        
        # Should return default countdown values
        assert 'expired' in countdown
        assert 'daysRemaining' in countdown
        assert countdown['daysRemaining'] == 0
    
    def test_list_active_releases_countdown_accuracy(
        self, mock_env_vars, mock_products
    ):
        """Test that countdown is calculated accurately for each release."""
        from limited_releases.list_active_limited_releases import handler
        
        now = datetime.utcnow()
        
        # Create release ending in exactly 3 days
        release_with_countdown = {
            'PK': 'LIMITED_RELEASE#release-3',
            'SK': 'METADATA',
            'releaseId': 'release-3',
            'farmerId': 'farmer-1',
            'productId': 'product-1',
            'releaseName': 'Test Release',
            'quantityLimit': 50,
            'quantityRemaining': 30,
            'duration': 3,
            'status': 'active',
            'startDate': now.isoformat(),
            'endDate': (now + timedelta(days=3)).isoformat(),
            'GSI3PK': 'STATUS#active',
            'GSI3SK': f"RELEASE#{(now + timedelta(days=3)).isoformat()}"
        }
        
        with patch('limited_releases.list_active_limited_releases.query') as mock_query, \
             patch('limited_releases.list_active_limited_releases.get_item') as mock_get:
            
            mock_query.return_value = {
                'Items': [release_with_countdown]
            }
            
            mock_get.return_value = mock_products['product-1']
            
            event = {
                'queryStringParameters': None
            }
            
            response = handler(event, None)
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            
            release = body['releases'][0]
            countdown = release['countdown']
            
            # Should be approximately 3 days remaining
            assert countdown['expired'] is False
            assert countdown['daysRemaining'] >= 2  # Allow for small timing differences
            assert countdown['daysRemaining'] <= 3
    
    def test_list_active_releases_quantity_remaining_displayed(
        self, mock_env_vars, mock_active_releases, mock_products
    ):
        """Test that quantityRemaining is correctly displayed."""
        from limited_releases.list_active_limited_releases import handler
        
        with patch('limited_releases.list_active_limited_releases.query') as mock_query, \
             patch('limited_releases.list_active_limited_releases.get_item') as mock_get:
            
            mock_query.return_value = {
                'Items': mock_active_releases
            }
            
            def get_item_side_effect(pk, sk):
                product_id = pk.replace('PRODUCT#', '')
                return mock_products.get(product_id)
            
            mock_get.side_effect = get_item_side_effect
            
            event = {
                'queryStringParameters': None
            }
            
            response = handler(event, None)
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            
            # Verify quantityRemaining for both releases
            release1 = body['releases'][0]
            assert release1['quantityLimit'] == 50
            assert release1['quantityRemaining'] == 30
            
            release2 = body['releases'][1]
            assert release2['quantityLimit'] == 100
            assert release2['quantityRemaining'] == 75


class TestCountdownCalculation:
    """Test cases specifically for countdown calculation logic."""
    
    def test_countdown_with_z_suffix(self, mock_env_vars):
        """Test countdown calculation with Z suffix in ISO date."""
        from limited_releases.list_active_limited_releases import calculate_countdown
        
        future_date = datetime.utcnow() + timedelta(days=2)
        end_date_str = future_date.isoformat() + 'Z'
        
        countdown = calculate_countdown(end_date_str)
        
        assert countdown['expired'] is False
        assert countdown['daysRemaining'] >= 1
    
    def test_countdown_exact_expiry(self, mock_env_vars):
        """Test countdown when release is expiring right now."""
        from limited_releases.list_active_limited_releases import calculate_countdown
        
        # End date is now (or very close)
        now = datetime.utcnow()
        end_date_str = now.isoformat()
        
        countdown = calculate_countdown(end_date_str)
        
        # Should be expired or very close to expiry
        assert countdown['daysRemaining'] == 0
    
    def test_countdown_includes_total_seconds(self, mock_env_vars):
        """Test that countdown includes totalSeconds field."""
        from limited_releases.list_active_limited_releases import calculate_countdown
        
        future_date = datetime.utcnow() + timedelta(days=1, hours=12)
        end_date_str = future_date.isoformat()
        
        countdown = calculate_countdown(end_date_str)
        
        assert 'totalSeconds' in countdown
        # Should be approximately 1.5 days = 129600 seconds
        assert countdown['totalSeconds'] > 100000
        assert countdown['totalSeconds'] < 150000


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
