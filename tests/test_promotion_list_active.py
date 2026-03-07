"""
Unit tests for active promotions listing endpoint.
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

from shared.constants import PromotionStatus


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Set up environment variables for tests."""
    monkeypatch.setenv('DYNAMODB_TABLE_NAME', 'RootTrustData-test')


@pytest.fixture
def mock_active_promotions():
    """Mock active promotions data."""
    now = datetime.utcnow()
    return [
        {
            'PK': 'PROMOTION#promo-1',
            'SK': 'METADATA',
            'promotionId': 'promo-1',
            'farmerId': 'farmer-1',
            'productId': 'product-1',
            'budget': 500.0,
            'duration': 7,
            'status': 'active',
            'startDate': now.isoformat(),
            'endDate': (now + timedelta(days=7)).isoformat(),
            'aiGeneratedAdCopy': 'Special promotion on Organic Tomatoes!',
            'metrics': {
                'views': 100,
                'clicks': 20,
                'conversions': 5,
                'spent': 50.0
            },
            'GSI3PK': 'STATUS#active',
            'GSI3SK': f"PROMOTION#{(now + timedelta(days=7)).isoformat()}"
        },
        {
            'PK': 'PROMOTION#promo-2',
            'SK': 'METADATA',
            'promotionId': 'promo-2',
            'farmerId': 'farmer-2',
            'productId': 'product-2',
            'budget': 300.0,
            'duration': 5,
            'status': 'active',
            'startDate': now.isoformat(),
            'endDate': (now + timedelta(days=5)).isoformat(),
            'aiGeneratedAdCopy': 'Fresh mangoes available now!',
            'metrics': {
                'views': 50,
                'clicks': 10,
                'conversions': 2,
                'spent': 30.0
            },
            'GSI3PK': 'STATUS#active',
            'GSI3SK': f"PROMOTION#{(now + timedelta(days=5)).isoformat()}"
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
            'name': 'Fresh Mangoes',
            'category': 'fruits',
            'price': 100.0,
            'images': [
                {'url': 'https://s3.amazonaws.com/image2.jpg', 'isPrimary': True}
            ],
            'averageRating': 4.8,
            'giTag': {
                'hasTag': False
            }
        }
    }


class TestActivePromotionsListing:
    """Test cases for active promotions listing endpoint."""
    
    def test_list_active_promotions_success(
        self, mock_env_vars, mock_active_promotions, mock_products
    ):
        """Test successful listing of active promotions."""
        # Import after env vars are set
        from promotions.list_active_promotions import handler
        
        # Mock dependencies
        with patch('promotions.list_active_promotions.query') as mock_query, \
             patch('promotions.list_active_promotions.get_item') as mock_get:
            
            # Setup mocks
            mock_query.return_value = {
                'Items': mock_active_promotions
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
            assert 'promotions' in body
            assert 'count' in body
            assert body['count'] == 2
            assert len(body['promotions']) == 2
            
            # Verify first promotion
            promo1 = body['promotions'][0]
            assert promo1['promotionId'] == 'promo-1'
            assert promo1['productId'] == 'product-1'
            assert promo1['status'] == 'active'
            assert 'product' in promo1
            assert promo1['product']['name'] == 'Organic Tomatoes'
            assert promo1['product']['category'] == 'vegetables'
            assert promo1['product']['price'] == 50.0
            assert promo1['product']['averageRating'] == 4.5
            assert promo1['product']['giTag']['hasTag'] is True
            
            # Verify metrics are included
            assert 'metrics' in promo1
            assert promo1['metrics']['views'] == 100
            assert promo1['metrics']['clicks'] == 20
            
            # Verify query was called with correct parameters
            mock_query.assert_called_once()
            call_kwargs = mock_query.call_args[1]
            assert call_kwargs['index_name'] == 'GSI3'
            assert call_kwargs['limit'] == 50
            assert call_kwargs['scan_index_forward'] is False
    
    def test_list_active_promotions_empty(self, mock_env_vars):
        """Test listing when no active promotions exist."""
        from promotions.list_active_promotions import handler
        
        with patch('promotions.list_active_promotions.query') as mock_query:
            mock_query.return_value = {
                'Items': []
            }
            
            event = {
                'queryStringParameters': None
            }
            
            response = handler(event, None)
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert body['promotions'] == []
            assert body['count'] == 0
            assert 'nextCursor' not in body
    
    def test_list_active_promotions_with_pagination(
        self, mock_env_vars, mock_active_promotions, mock_products
    ):
        """Test listing with pagination parameters."""
        from promotions.list_active_promotions import handler
        
        with patch('promotions.list_active_promotions.query') as mock_query, \
             patch('promotions.list_active_promotions.get_item') as mock_get:
            
            # Mock query with LastEvaluatedKey
            mock_query.return_value = {
                'Items': [mock_active_promotions[0]],
                'LastEvaluatedKey': {
                    'PK': 'PROMOTION#promo-1',
                    'SK': 'METADATA',
                    'GSI3PK': 'STATUS#active',
                    'GSI3SK': 'PROMOTION#2024-01-01T00:00:00'
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
            assert cursor_data['PK'] == 'PROMOTION#promo-1'
    
    def test_list_active_promotions_with_cursor(
        self, mock_env_vars, mock_active_promotions, mock_products
    ):
        """Test listing with pagination cursor."""
        from promotions.list_active_promotions import handler
        
        with patch('promotions.list_active_promotions.query') as mock_query, \
             patch('promotions.list_active_promotions.get_item') as mock_get:
            
            mock_query.return_value = {
                'Items': [mock_active_promotions[1]]
            }
            
            def get_item_side_effect(pk, sk):
                product_id = pk.replace('PRODUCT#', '')
                return mock_products.get(product_id)
            
            mock_get.side_effect = get_item_side_effect
            
            # Create valid cursor
            import base64
            cursor_data = {
                'PK': 'PROMOTION#promo-1',
                'SK': 'METADATA',
                'GSI3PK': 'STATUS#active',
                'GSI3SK': 'PROMOTION#2024-01-01T00:00:00'
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
    
    def test_list_active_promotions_invalid_cursor(
        self, mock_env_vars, mock_active_promotions, mock_products
    ):
        """Test listing with invalid cursor (should continue without cursor)."""
        from promotions.list_active_promotions import handler
        
        with patch('promotions.list_active_promotions.query') as mock_query, \
             patch('promotions.list_active_promotions.get_item') as mock_get:
            
            mock_query.return_value = {
                'Items': mock_active_promotions
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
    
    def test_list_active_promotions_custom_limit(
        self, mock_env_vars, mock_active_promotions, mock_products
    ):
        """Test listing with custom limit parameter."""
        from promotions.list_active_promotions import handler
        
        with patch('promotions.list_active_promotions.query') as mock_query, \
             patch('promotions.list_active_promotions.get_item') as mock_get:
            
            mock_query.return_value = {
                'Items': [mock_active_promotions[0]]
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
    
    def test_list_active_promotions_limit_validation(
        self, mock_env_vars, mock_active_promotions, mock_products
    ):
        """Test that invalid limits are normalized."""
        from promotions.list_active_promotions import handler
        
        with patch('promotions.list_active_promotions.query') as mock_query, \
             patch('promotions.list_active_promotions.get_item') as mock_get:
            
            mock_query.return_value = {
                'Items': mock_active_promotions
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
    
    def test_list_active_promotions_product_not_found(
        self, mock_env_vars, mock_active_promotions
    ):
        """Test listing when product is not found (should skip that promotion)."""
        from promotions.list_active_promotions import handler
        
        with patch('promotions.list_active_promotions.query') as mock_query, \
             patch('promotions.list_active_promotions.get_item') as mock_get:
            
            mock_query.return_value = {
                'Items': mock_active_promotions
            }
            
            # Mock get_item to return None (product not found)
            mock_get.return_value = None
            
            event = {
                'queryStringParameters': None
            }
            
            response = handler(event, None)
            
            # Should succeed but with no promotions (all skipped)
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert body['count'] == 0
            assert body['promotions'] == []
    
    def test_list_active_promotions_partial_product_failure(
        self, mock_env_vars, mock_active_promotions, mock_products
    ):
        """Test listing when some products fail to load."""
        from promotions.list_active_promotions import handler
        
        with patch('promotions.list_active_promotions.query') as mock_query, \
             patch('promotions.list_active_promotions.get_item') as mock_get:
            
            mock_query.return_value = {
                'Items': mock_active_promotions
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
            
            # Should succeed with only the first promotion
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert body['count'] == 1
            assert body['promotions'][0]['productId'] == 'product-1'
    
    def test_list_active_promotions_query_error(self, mock_env_vars):
        """Test listing when DynamoDB query fails."""
        from promotions.list_active_promotions import handler
        from backend.shared.exceptions import ServiceUnavailableError
        
        with patch('promotions.list_active_promotions.query') as mock_query:
            mock_query.side_effect = ServiceUnavailableError('DynamoDB', 'Service unavailable')
            
            event = {
                'queryStringParameters': None
            }
            
            response = handler(event, None)
            
            assert response['statusCode'] == 503
            body = json.loads(response['body'])
            assert body['error']['code'] == 'SERVICE_UNAVAILABLE'
    
    def test_list_active_promotions_enrichment_error(
        self, mock_env_vars, mock_active_promotions, mock_products
    ):
        """Test listing when product enrichment fails for one promotion."""
        from promotions.list_active_promotions import handler
        
        with patch('promotions.list_active_promotions.query') as mock_query, \
             patch('promotions.list_active_promotions.get_item') as mock_get:
            
            mock_query.return_value = {
                'Items': mock_active_promotions
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
            
            # Should succeed with only the first promotion
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert body['count'] == 1
            assert body['promotions'][0]['productId'] == 'product-1'
    
    def test_list_active_promotions_no_query_params(
        self, mock_env_vars, mock_active_promotions, mock_products
    ):
        """Test listing without any query parameters."""
        from promotions.list_active_promotions import handler
        
        with patch('promotions.list_active_promotions.query') as mock_query, \
             patch('promotions.list_active_promotions.get_item') as mock_get:
            
            mock_query.return_value = {
                'Items': mock_active_promotions
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
    
    def test_list_active_promotions_includes_all_fields(
        self, mock_env_vars, mock_active_promotions, mock_products
    ):
        """Test that all required fields are included in response."""
        from promotions.list_active_promotions import handler
        
        with patch('promotions.list_active_promotions.query') as mock_query, \
             patch('promotions.list_active_promotions.get_item') as mock_get:
            
            mock_query.return_value = {
                'Items': [mock_active_promotions[0]]
            }
            
            mock_get.return_value = mock_products['product-1']
            
            event = {
                'queryStringParameters': None
            }
            
            response = handler(event, None)
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            
            promo = body['promotions'][0]
            
            # Verify promotion fields
            assert 'promotionId' in promo
            assert 'farmerId' in promo
            assert 'productId' in promo
            assert 'budget' in promo
            assert 'duration' in promo
            assert 'status' in promo
            assert 'startDate' in promo
            assert 'endDate' in promo
            assert 'aiGeneratedAdCopy' in promo
            assert 'metrics' in promo
            
            # Verify product fields
            assert 'product' in promo
            product = promo['product']
            assert 'name' in product
            assert 'category' in product
            assert 'price' in product
            assert 'images' in product
            assert 'averageRating' in product
            assert 'giTag' in product
    
    def test_list_active_promotions_default_metrics(
        self, mock_env_vars, mock_products
    ):
        """Test that default metrics are provided when missing."""
        from promotions.list_active_promotions import handler
        
        # Promotion without metrics
        promotion_no_metrics = {
            'PK': 'PROMOTION#promo-3',
            'SK': 'METADATA',
            'promotionId': 'promo-3',
            'farmerId': 'farmer-1',
            'productId': 'product-1',
            'budget': 500.0,
            'duration': 7,
            'status': 'active',
            'startDate': datetime.utcnow().isoformat(),
            'endDate': (datetime.utcnow() + timedelta(days=7)).isoformat(),
            'aiGeneratedAdCopy': 'Test ad',
            'GSI3PK': 'STATUS#active',
            'GSI3SK': 'PROMOTION#2024-01-01T00:00:00'
        }
        
        with patch('promotions.list_active_promotions.query') as mock_query, \
             patch('promotions.list_active_promotions.get_item') as mock_get:
            
            mock_query.return_value = {
                'Items': [promotion_no_metrics]
            }
            
            mock_get.return_value = mock_products['product-1']
            
            event = {
                'queryStringParameters': None
            }
            
            response = handler(event, None)
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            
            promo = body['promotions'][0]
            assert 'metrics' in promo
            assert promo['metrics']['views'] == 0
            assert promo['metrics']['clicks'] == 0
            assert promo['metrics']['conversions'] == 0
            assert promo['metrics']['spent'] == 0.0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
