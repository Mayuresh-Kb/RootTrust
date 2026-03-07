"""
Unit tests for product listing endpoint (GET /products).
Tests filtering, pagination, and search functionality.
"""
import json
import pytest
import os
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import patch, MagicMock, Mock
from moto import mock_aws
import boto3

# Set environment variables before importing handler
os.environ['DYNAMODB_TABLE_NAME'] = 'RootTrustData-test'
os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'

# Add backend to path
import sys
backend_dir = os.path.join(os.path.dirname(__file__), '..', 'backend')
sys.path.insert(0, backend_dir)

# Now we can import
from products.list_products import handler, is_product_seasonal_match, matches_keyword_search, encode_cursor, parse_cursor


@pytest.fixture
def mock_dynamodb_table():
    """Create a mock DynamoDB table for testing."""
    with mock_aws():
        # Create DynamoDB resource
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        
        # Create table
        table = dynamodb.create_table(
            TableName='RootTrustData-test',
            KeySchema=[
                {'AttributeName': 'PK', 'KeyType': 'HASH'},
                {'AttributeName': 'SK', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'PK', 'AttributeType': 'S'},
                {'AttributeName': 'SK', 'AttributeType': 'S'},
                {'AttributeName': 'GSI1PK', 'AttributeType': 'S'},
                {'AttributeName': 'GSI1SK', 'AttributeType': 'S'},
                {'AttributeName': 'GSI3PK', 'AttributeType': 'S'},
                {'AttributeName': 'GSI3SK', 'AttributeType': 'S'}
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'GSI1',
                    'KeySchema': [
                        {'AttributeName': 'GSI1PK', 'KeyType': 'HASH'},
                        {'AttributeName': 'GSI1SK', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'}
                },
                {
                    'IndexName': 'GSI3',
                    'KeySchema': [
                        {'AttributeName': 'GSI3PK', 'KeyType': 'HASH'},
                        {'AttributeName': 'GSI3SK', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'}
                }
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        
        yield table


def create_test_product(
    product_id: str,
    farmer_id: str,
    name: str,
    category: str = 'vegetables',
    verification_status: str = 'approved',
    has_gi_tag: bool = False,
    is_seasonal: bool = False,
    season_start: str = None,
    season_end: str = None,
    price: float = 100.0,
    rating: float = 4.5
) -> dict:
    """Create a test product item."""
    now = datetime.utcnow().isoformat()
    
    return {
        'PK': f'PRODUCT#{product_id}',
        'SK': 'METADATA',
        'EntityType': 'Product',
        'productId': product_id,
        'farmerId': farmer_id,
        'name': name,
        'category': category,
        'description': f'Description for {name}',
        'price': Decimal(str(price)),  # Convert to Decimal for DynamoDB
        'unit': 'kg',
        'giTag': {
            'hasTag': has_gi_tag,
            'tagName': 'Darjeeling Tea' if has_gi_tag else None,
            'region': 'Darjeeling' if has_gi_tag else None
        },
        'seasonal': {
            'isSeasonal': is_seasonal,
            'seasonStart': season_start,
            'seasonEnd': season_end
        },
        'images': [
            {'url': f'https://s3.amazonaws.com/products/{product_id}/image1.jpg', 'isPrimary': True}
        ],
        'verificationStatus': verification_status,
        'quantity': 100,
        'averageRating': Decimal(str(rating)),  # Convert to Decimal for DynamoDB
        'totalReviews': 10,
        'createdAt': now,
        'updatedAt': now,
        'GSI1PK': f'CATEGORY#{category}',
        'GSI1SK': f'PRODUCT#{now}',
        'GSI3PK': f'STATUS#{verification_status}',
        'GSI3SK': f'PRODUCT#{now}'
    }


def create_test_user(user_id: str, first_name: str, last_name: str) -> dict:
    """Create a test user item."""
    return {
        'PK': f'USER#{user_id}',
        'SK': 'PROFILE',
        'EntityType': 'User',
        'userId': user_id,
        'firstName': first_name,
        'lastName': last_name,
        'email': f'{first_name.lower()}@example.com',
        'role': 'farmer'
    }


class TestProductListing:
    """Test cases for product listing endpoint."""
    
    def test_list_all_approved_products(self, mock_dynamodb_table):
        """Test listing all approved products without filters."""
        # Create test data
        farmer_id = 'farmer-123'
        mock_dynamodb_table.put_item(Item=create_test_user(farmer_id, 'John', 'Farmer'))
        mock_dynamodb_table.put_item(Item=create_test_product('prod-1', farmer_id, 'Tomatoes'))
        mock_dynamodb_table.put_item(Item=create_test_product('prod-2', farmer_id, 'Potatoes'))
        mock_dynamodb_table.put_item(Item=create_test_product('prod-3', farmer_id, 'Pending Product', verification_status='pending'))
        
        # Create API Gateway event
        event = {
            'queryStringParameters': None,
            'headers': {}
        }
        
        # Call handler
        response = handler(event, None)
        
        # Verify response
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert 'products' in body
        assert len(body['products']) == 2  # Only approved products
        assert body['count'] == 2
        
        # Verify product data
        product_names = [p['name'] for p in body['products']]
        assert 'Tomatoes' in product_names
        assert 'Potatoes' in product_names
        assert 'Pending Product' not in product_names
    
    def test_filter_by_category(self, mock_dynamodb_table):
        """Test filtering products by category."""
        farmer_id = 'farmer-123'
        mock_dynamodb_table.put_item(Item=create_test_user(farmer_id, 'John', 'Farmer'))
        mock_dynamodb_table.put_item(Item=create_test_product('prod-1', farmer_id, 'Tomatoes', category='vegetables'))
        mock_dynamodb_table.put_item(Item=create_test_product('prod-2', farmer_id, 'Apples', category='fruits'))
        mock_dynamodb_table.put_item(Item=create_test_product('prod-3', farmer_id, 'Carrots', category='vegetables'))
        
        # Create API Gateway event with category filter
        event = {
            'queryStringParameters': {
                'category': 'vegetables'
            },
            'headers': {}
        }
        
        # Call handler
        response = handler(event, None)
        
        # Verify response
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert len(body['products']) == 2
        
        # Verify all products are vegetables
        for product in body['products']:
            assert product['category'] == 'vegetables'
    
    def test_filter_by_gi_tag(self, mock_dynamodb_table):
        """Test filtering products by GI tag presence."""
        farmer_id = 'farmer-123'
        mock_dynamodb_table.put_item(Item=create_test_user(farmer_id, 'John', 'Farmer'))
        mock_dynamodb_table.put_item(Item=create_test_product('prod-1', farmer_id, 'Darjeeling Tea', has_gi_tag=True))
        mock_dynamodb_table.put_item(Item=create_test_product('prod-2', farmer_id, 'Regular Tea', has_gi_tag=False))
        mock_dynamodb_table.put_item(Item=create_test_product('prod-3', farmer_id, 'Basmati Rice', has_gi_tag=True))
        
        # Create API Gateway event with giTag filter
        event = {
            'queryStringParameters': {
                'giTag': 'true'
            },
            'headers': {}
        }
        
        # Call handler
        response = handler(event, None)
        
        # Verify response
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert len(body['products']) == 2
        
        # Verify all products have GI tag
        for product in body['products']:
            assert product['giTag']['hasTag'] is True
    
    def test_filter_by_seasonal(self, mock_dynamodb_table):
        """Test filtering products by seasonal availability."""
        farmer_id = 'farmer-123'
        now = datetime.utcnow()
        past_date = (now - timedelta(days=60)).isoformat()
        future_date = (now + timedelta(days=60)).isoformat()
        old_date = (now - timedelta(days=120)).isoformat()
        
        mock_dynamodb_table.put_item(Item=create_test_user(farmer_id, 'John', 'Farmer'))
        mock_dynamodb_table.put_item(Item=create_test_product(
            'prod-1', farmer_id, 'Mangoes',
            is_seasonal=True,
            season_start=past_date,
            season_end=future_date
        ))
        mock_dynamodb_table.put_item(Item=create_test_product(
            'prod-2', farmer_id, 'Strawberries',
            is_seasonal=True,
            season_start=old_date,
            season_end=past_date
        ))
        mock_dynamodb_table.put_item(Item=create_test_product(
            'prod-3', farmer_id, 'Potatoes',
            is_seasonal=False
        ))
        
        # Create API Gateway event with seasonal filter
        event = {
            'queryStringParameters': {
                'seasonal': 'true'
            },
            'headers': {}
        }
        
        # Call handler
        response = handler(event, None)
        
        # Verify response
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert len(body['products']) == 1
        assert body['products'][0]['name'] == 'Mangoes'
    
    def test_keyword_search(self, mock_dynamodb_table):
        """Test keyword search in product name and description."""
        farmer_id = 'farmer-123'
        mock_dynamodb_table.put_item(Item=create_test_user(farmer_id, 'John', 'Farmer'))
        
        # Create products with different names and descriptions
        product1 = create_test_product('prod-1', farmer_id, 'Organic Tomatoes')
        product1['description'] = 'Fresh organic tomatoes from local farm'
        mock_dynamodb_table.put_item(Item=product1)
        
        product2 = create_test_product('prod-2', farmer_id, 'Potatoes')
        product2['description'] = 'Regular potatoes'
        mock_dynamodb_table.put_item(Item=product2)
        
        product3 = create_test_product('prod-3', farmer_id, 'Carrots')
        product3['description'] = 'Organic carrots grown naturally'
        mock_dynamodb_table.put_item(Item=product3)
        
        # Search for "organic"
        event = {
            'queryStringParameters': {
                'search': 'organic'
            },
            'headers': {}
        }
        
        # Call handler
        response = handler(event, None)
        
        # Verify response
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert len(body['products']) == 2
        
        # Verify search results
        product_names = [p['name'] for p in body['products']]
        assert 'Organic Tomatoes' in product_names
        assert 'Carrots' in product_names
    
    def test_pagination_with_limit(self, mock_dynamodb_table):
        """Test pagination with limit parameter."""
        farmer_id = 'farmer-123'
        mock_dynamodb_table.put_item(Item=create_test_user(farmer_id, 'John', 'Farmer'))
        
        # Create multiple products
        for i in range(5):
            mock_dynamodb_table.put_item(Item=create_test_product(f'prod-{i}', farmer_id, f'Product {i}'))
        
        # Request with limit
        event = {
            'queryStringParameters': {
                'limit': '2'
            },
            'headers': {}
        }
        
        # Call handler
        response = handler(event, None)
        
        # Verify response
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert len(body['products']) <= 2
        assert 'nextCursor' in body
    
    def test_invalid_category(self, mock_dynamodb_table):
        """Test error handling for invalid category."""
        event = {
            'queryStringParameters': {
                'category': 'invalid_category'
            },
            'headers': {}
        }
        
        # Call handler
        response = handler(event, None)
        
        # Verify error response
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'error' in body
        assert body['error']['code'] == 'INVALID_CATEGORY'
    
    def test_product_includes_farmer_name(self, mock_dynamodb_table):
        """Test that product listing includes farmer name."""
        farmer_id = 'farmer-123'
        mock_dynamodb_table.put_item(Item=create_test_user(farmer_id, 'John', 'Doe'))
        mock_dynamodb_table.put_item(Item=create_test_product('prod-1', farmer_id, 'Tomatoes'))
        
        event = {
            'queryStringParameters': None,
            'headers': {}
        }
        
        # Call handler
        response = handler(event, None)
        
        # Verify response
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert len(body['products']) == 1
        assert body['products'][0]['farmerName'] == 'John Doe'
    
    def test_product_includes_rating_and_images(self, mock_dynamodb_table):
        """Test that product listing includes rating and images."""
        farmer_id = 'farmer-123'
        mock_dynamodb_table.put_item(Item=create_test_user(farmer_id, 'John', 'Farmer'))
        mock_dynamodb_table.put_item(Item=create_test_product('prod-1', farmer_id, 'Tomatoes', rating=4.5))
        
        event = {
            'queryStringParameters': None,
            'headers': {}
        }
        
        # Call handler
        response = handler(event, None)
        
        # Verify response
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert len(body['products']) == 1
        product = body['products'][0]
        assert float(product['averageRating']) == 4.5  # Convert Decimal to float for comparison
        assert 'images' in product
        assert len(product['images']) > 0
        assert 'primaryImage' in product


class TestHelperFunctions:
    """Test helper functions."""
    
    def test_is_product_seasonal_match_in_season(self):
        """Test seasonal matching for product in season."""
        now = datetime.utcnow()
        past_date = (now - timedelta(days=30)).isoformat()
        future_date = (now + timedelta(days=30)).isoformat()
        
        product = {
            'seasonal': {
                'isSeasonal': True,
                'seasonStart': past_date,
                'seasonEnd': future_date
            }
        }
        
        assert is_product_seasonal_match(product, now) is True
    
    def test_is_product_seasonal_match_out_of_season(self):
        """Test seasonal matching for product out of season."""
        now = datetime.utcnow()
        old_start = (now - timedelta(days=90)).isoformat()
        old_end = (now - timedelta(days=30)).isoformat()
        
        product = {
            'seasonal': {
                'isSeasonal': True,
                'seasonStart': old_start,
                'seasonEnd': old_end
            }
        }
        
        assert is_product_seasonal_match(product, now) is False
    
    def test_is_product_seasonal_match_not_seasonal(self):
        """Test seasonal matching for non-seasonal product."""
        product = {
            'seasonal': {
                'isSeasonal': False
            }
        }
        
        assert is_product_seasonal_match(product, datetime.utcnow()) is False
    
    def test_matches_keyword_search_in_name(self):
        """Test keyword search matching in product name."""
        product = {
            'name': 'Organic Tomatoes',
            'description': 'Fresh vegetables'
        }
        
        assert matches_keyword_search(product, 'organic') is True
        assert matches_keyword_search(product, 'tomatoes') is True
        assert matches_keyword_search(product, 'ORGANIC') is True  # Case insensitive
    
    def test_matches_keyword_search_in_description(self):
        """Test keyword search matching in product description."""
        product = {
            'name': 'Tomatoes',
            'description': 'Fresh organic vegetables from local farm'
        }
        
        assert matches_keyword_search(product, 'organic') is True
        assert matches_keyword_search(product, 'local') is True
    
    def test_matches_keyword_search_no_match(self):
        """Test keyword search with no match."""
        product = {
            'name': 'Tomatoes',
            'description': 'Fresh vegetables'
        }
        
        assert matches_keyword_search(product, 'organic') is False
    
    def test_cursor_encoding_decoding(self):
        """Test cursor encoding and decoding."""
        original_key = {
            'PK': 'PRODUCT#123',
            'SK': 'METADATA',
            'GSI3PK': 'STATUS#approved'
        }
        
        # Encode
        cursor = encode_cursor(original_key)
        assert isinstance(cursor, str)
        assert len(cursor) > 0
        
        # Decode
        decoded_key = parse_cursor(cursor)
        assert decoded_key == original_key
    
    def test_parse_cursor_invalid(self):
        """Test parsing invalid cursor."""
        assert parse_cursor('invalid_cursor') is None
        assert parse_cursor(None) is None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
