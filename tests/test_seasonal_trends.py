"""
Unit tests for seasonal trends analytics Lambda handler.
"""
import json
import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import patch, MagicMock
from moto import mock_aws
import boto3
import os

# Add backend paths to sys.path
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend', 'shared'))

# Set environment variables before importing handler
os.environ['DYNAMODB_TABLE_NAME'] = 'RootTrustData-Test'
os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'

# Import after path setup
from shared.constants import ProductCategory, OrderStatus
from analytics import get_seasonal_trends


@pytest.fixture
def dynamodb_table():
    """Create a mock DynamoDB table for testing."""
    with mock_aws():
        # Create DynamoDB resource
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        
        # Create table
        table = dynamodb.create_table(
            TableName='RootTrustData-Test',
            KeySchema=[
                {'AttributeName': 'PK', 'KeyType': 'HASH'},
                {'AttributeName': 'SK', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'PK', 'AttributeType': 'S'},
                {'AttributeName': 'SK', 'AttributeType': 'S'},
                {'AttributeName': 'GSI1PK', 'AttributeType': 'S'},
                {'AttributeName': 'GSI1SK', 'AttributeType': 'S'},
                {'AttributeName': 'GSI2PK', 'AttributeType': 'S'},
                {'AttributeName': 'GSI2SK', 'AttributeType': 'S'},
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
                    'Projection': {'ProjectionType': 'ALL'},
                    'ProvisionedThroughput': {'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
                },
                {
                    'IndexName': 'GSI2',
                    'KeySchema': [
                        {'AttributeName': 'GSI2PK', 'KeyType': 'HASH'},
                        {'AttributeName': 'GSI2SK', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                    'ProvisionedThroughput': {'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
                },
                {
                    'IndexName': 'GSI3',
                    'KeySchema': [
                        {'AttributeName': 'GSI3PK', 'KeyType': 'HASH'},
                        {'AttributeName': 'GSI3SK', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                    'ProvisionedThroughput': {'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
                }
            ],
            BillingMode='PROVISIONED',
            ProvisionedThroughput={'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
        )
        
        yield table


def create_product(product_id, farmer_id, category, is_seasonal, total_sales, price, 
                   season_start=None, season_end=None):
    """Helper function to create a product record."""
    now = datetime.utcnow()
    
    product = {
        'PK': f'PRODUCT#{product_id}',
        'SK': 'METADATA',
        'EntityType': 'Product',
        'productId': product_id,
        'farmerId': farmer_id,
        'name': f'Test Product {product_id}',
        'category': category,
        'description': 'Test description',
        'price': Decimal(str(price)),
        'unit': 'kg',
        'giTag': {
            'hasTag': False
        },
        'seasonal': {
            'isSeasonal': is_seasonal
        },
        'quantity': 100,
        'totalSales': total_sales,
        'totalReviews': 0,
        'averageRating': Decimal('0.0'),
        'viewCount': 100,
        'verificationStatus': 'approved',
        'createdAt': now.isoformat(),
        'updatedAt': now.isoformat(),
        'GSI1PK': f'CATEGORY#{category}',
        'GSI1SK': f'PRODUCT#{now.isoformat()}',
        'GSI2PK': f'FARMER#{farmer_id}',
        'GSI2SK': f'PRODUCT#{now.isoformat()}',
        'GSI3PK': 'STATUS#approved',
        'GSI3SK': f'PRODUCT#{now.isoformat()}'
    }
    
    if is_seasonal and season_start and season_end:
        product['seasonal']['seasonStart'] = season_start
        product['seasonal']['seasonEnd'] = season_end
    
    return product


def test_seasonal_trends_with_no_products(dynamodb_table):
    """Test seasonal trends endpoint with no products."""
    event = {
        'httpMethod': 'GET',
        'path': '/analytics/trends',
        'headers': {},
        'pathParameters': {},
        'queryStringParameters': None
    }
    
    response = get_seasonal_trends.handler(event, None)
    
    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    
    assert 'trends' in body
    trends = body['trends']
    
    assert trends['summary']['totalProducts'] == 0
    assert trends['summary']['totalCategories'] == 0
    assert len(trends['categoryTrends']) == 0
    assert len(trends['topCategories']) == 0


def test_seasonal_trends_with_mixed_products(dynamodb_table):
    """Test seasonal trends with both seasonal and non-seasonal products."""
    # Create test products
    products = [
        # Seasonal vegetables
        create_product('p1', 'f1', 'vegetables', True, 50, 25.0,
                      datetime(2024, 6, 1).isoformat(),
                      datetime(2024, 9, 30).isoformat()),
        create_product('p2', 'f1', 'vegetables', True, 30, 20.0,
                      datetime(2024, 6, 1).isoformat(),
                      datetime(2024, 9, 30).isoformat()),
        # Non-seasonal vegetables
        create_product('p3', 'f1', 'vegetables', False, 100, 15.0),
        # Seasonal fruits
        create_product('p4', 'f2', 'fruits', True, 75, 50.0,
                      datetime(2024, 3, 1).isoformat(),
                      datetime(2024, 5, 31).isoformat()),
        # Non-seasonal fruits
        create_product('p5', 'f2', 'fruits', False, 60, 40.0),
    ]
    
    # Insert products into DynamoDB
    for product in products:
        dynamodb_table.put_item(Item=product)
    
    event = {
        'httpMethod': 'GET',
        'path': '/analytics/trends',
        'headers': {},
        'pathParameters': {},
        'queryStringParameters': None
    }
    
    response = get_seasonal_trends.handler(event, None)
    
    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    
    assert 'trends' in body
    trends = body['trends']
    
    # Check summary
    assert trends['summary']['totalProducts'] == 5
    assert trends['summary']['totalCategories'] == 2
    assert trends['summary']['seasonalProductsPercentage'] == 60.0  # 3 out of 5
    
    # Check category trends
    assert len(trends['categoryTrends']) == 2
    
    # Find vegetables category
    veg_trend = next((c for c in trends['categoryTrends'] if c['category'] == 'vegetables'), None)
    assert veg_trend is not None
    assert veg_trend['totalProducts'] == 3
    assert veg_trend['seasonalProducts'] == 2
    assert veg_trend['nonSeasonalProducts'] == 1
    assert veg_trend['totalSales'] == 180  # 50 + 30 + 100
    
    # Find fruits category
    fruit_trend = next((c for c in trends['categoryTrends'] if c['category'] == 'fruits'), None)
    assert fruit_trend is not None
    assert fruit_trend['totalProducts'] == 2
    assert fruit_trend['seasonalProducts'] == 1
    assert fruit_trend['nonSeasonalProducts'] == 1
    assert fruit_trend['totalSales'] == 135  # 75 + 60
    
    # Check seasonal vs non-seasonal
    seasonal_data = trends['seasonalVsNonSeasonal']['seasonal']
    assert seasonal_data['totalProducts'] == 3
    assert seasonal_data['totalSales'] == 155  # 50 + 30 + 75
    
    nonseasonal_data = trends['seasonalVsNonSeasonal']['nonSeasonal']
    assert nonseasonal_data['totalProducts'] == 2
    assert nonseasonal_data['totalSales'] == 160  # 100 + 60
    
    # Check top categories
    assert len(trends['topCategories']) == 2
    # Fruits should be top (higher revenue: 75*50 + 60*40 = 6150 vs vegetables: 50*25 + 30*20 + 100*15 = 3350)
    assert trends['topCategories'][0]['category'] == 'fruits'


def test_seasonal_trends_category_breakdown(dynamodb_table):
    """Test seasonal trends with detailed category breakdown."""
    # Create products across multiple categories
    products = [
        create_product('p1', 'f1', 'vegetables', True, 100, 20.0,
                      datetime(2024, 6, 1).isoformat(),
                      datetime(2024, 9, 30).isoformat()),
        create_product('p2', 'f1', 'fruits', True, 80, 30.0,
                      datetime(2024, 3, 1).isoformat(),
                      datetime(2024, 5, 31).isoformat()),
        create_product('p3', 'f2', 'grains', False, 150, 10.0),
        create_product('p4', 'f2', 'spices', True, 50, 100.0,
                      datetime(2024, 1, 1).isoformat(),
                      datetime(2024, 12, 31).isoformat()),
        create_product('p5', 'f3', 'dairy', False, 200, 5.0),
    ]
    
    for product in products:
        dynamodb_table.put_item(Item=product)
    
    event = {
        'httpMethod': 'GET',
        'path': '/analytics/trends',
        'headers': {},
        'pathParameters': {},
        'queryStringParameters': None
    }
    
    response = get_seasonal_trends.handler(event, None)
    
    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    trends = body['trends']
    
    # Check all categories are present
    assert len(trends['categoryTrends']) == 5
    categories = [c['category'] for c in trends['categoryTrends']]
    assert 'vegetables' in categories
    assert 'fruits' in categories
    assert 'grains' in categories
    assert 'spices' in categories
    assert 'dairy' in categories
    
    # Check seasonal breakdown by category
    seasonal_categories = trends['seasonalVsNonSeasonal']['seasonal']['byCategory']
    assert 'vegetables' in seasonal_categories
    assert 'fruits' in seasonal_categories
    assert 'spices' in seasonal_categories
    
    nonseasonal_categories = trends['seasonalVsNonSeasonal']['nonSeasonal']['byCategory']
    assert 'grains' in nonseasonal_categories
    assert 'dairy' in nonseasonal_categories


def test_seasonal_availability_by_month(dynamodb_table):
    """Test seasonal availability tracking by month."""
    # Create seasonal products with different seasons
    products = [
        # Summer product (June-September)
        create_product('p1', 'f1', 'vegetables', True, 50, 20.0,
                      datetime(2024, 6, 1).isoformat(),
                      datetime(2024, 9, 30).isoformat()),
        # Spring product (March-May)
        create_product('p2', 'f1', 'fruits', True, 30, 30.0,
                      datetime(2024, 3, 1).isoformat(),
                      datetime(2024, 5, 31).isoformat()),
        # Year-round product
        create_product('p3', 'f2', 'grains', True, 100, 10.0,
                      datetime(2024, 1, 1).isoformat(),
                      datetime(2024, 12, 31).isoformat()),
    ]
    
    for product in products:
        dynamodb_table.put_item(Item=product)
    
    event = {
        'httpMethod': 'GET',
        'path': '/analytics/trends',
        'headers': {},
        'pathParameters': {},
        'queryStringParameters': None
    }
    
    response = get_seasonal_trends.handler(event, None)
    
    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    trends = body['trends']
    
    # Check seasonal availability
    seasonal_availability = trends['seasonalAvailability']
    assert len(seasonal_availability) == 12
    
    # Check specific months
    # January should have only year-round product
    jan_data = next((m for m in seasonal_availability if m['month'] == 1), None)
    assert jan_data is not None
    assert jan_data['productsAvailable'] == 1
    
    # April should have spring and year-round products
    apr_data = next((m for m in seasonal_availability if m['month'] == 4), None)
    assert apr_data is not None
    assert apr_data['productsAvailable'] == 2
    
    # July should have summer and year-round products
    jul_data = next((m for m in seasonal_availability if m['month'] == 7), None)
    assert jul_data is not None
    assert jul_data['productsAvailable'] == 2


def test_seasonal_trends_revenue_calculations(dynamodb_table):
    """Test revenue calculations in seasonal trends."""
    products = [
        create_product('p1', 'f1', 'vegetables', True, 100, 25.0,
                      datetime(2024, 6, 1).isoformat(),
                      datetime(2024, 9, 30).isoformat()),
        create_product('p2', 'f1', 'vegetables', False, 50, 20.0),
    ]
    
    for product in products:
        dynamodb_table.put_item(Item=product)
    
    event = {
        'httpMethod': 'GET',
        'path': '/analytics/trends',
        'headers': {},
        'pathParameters': {},
        'queryStringParameters': None
    }
    
    response = get_seasonal_trends.handler(event, None)
    
    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    trends = body['trends']
    
    # Check seasonal revenue: 100 sales * $25 = $2500
    seasonal_data = trends['seasonalVsNonSeasonal']['seasonal']
    assert seasonal_data['totalRevenue'] == 2500.0
    assert seasonal_data['averagePrice'] == 25.0
    
    # Check non-seasonal revenue: 50 sales * $20 = $1000
    nonseasonal_data = trends['seasonalVsNonSeasonal']['nonSeasonal']
    assert nonseasonal_data['totalRevenue'] == 1000.0
    assert nonseasonal_data['averagePrice'] == 20.0
    
    # Check category revenue: $2500 + $1000 = $3500
    veg_trend = next((c for c in trends['categoryTrends'] if c['category'] == 'vegetables'), None)
    assert veg_trend['totalRevenue'] == 3500.0


def test_seasonal_trends_top_categories(dynamodb_table):
    """Test top categories ranking by revenue."""
    products = [
        create_product('p1', 'f1', 'vegetables', False, 100, 10.0),  # $1000
        create_product('p2', 'f1', 'fruits', False, 50, 50.0),       # $2500
        create_product('p3', 'f2', 'grains', False, 200, 5.0),       # $1000
        create_product('p4', 'f2', 'spices', False, 20, 200.0),      # $4000
        create_product('p5', 'f3', 'dairy', False, 150, 8.0),        # $1200
    ]
    
    for product in products:
        dynamodb_table.put_item(Item=product)
    
    event = {
        'httpMethod': 'GET',
        'path': '/analytics/trends',
        'headers': {},
        'pathParameters': {},
        'queryStringParameters': None
    }
    
    response = get_seasonal_trends.handler(event, None)
    
    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    trends = body['trends']
    
    # Check top categories are sorted by revenue
    top_categories = trends['topCategories']
    assert len(top_categories) == 5
    
    # Spices should be #1 ($4000)
    assert top_categories[0]['category'] == 'spices'
    assert top_categories[0]['totalRevenue'] == 4000.0
    
    # Fruits should be #2 ($2500)
    assert top_categories[1]['category'] == 'fruits'
    assert top_categories[1]['totalRevenue'] == 2500.0


def test_seasonal_trends_with_zero_sales(dynamodb_table):
    """Test seasonal trends with products that have zero sales."""
    products = [
        create_product('p1', 'f1', 'vegetables', True, 0, 25.0,
                      datetime(2024, 6, 1).isoformat(),
                      datetime(2024, 9, 30).isoformat()),
        create_product('p2', 'f1', 'fruits', False, 0, 30.0),
    ]
    
    for product in products:
        dynamodb_table.put_item(Item=product)
    
    event = {
        'httpMethod': 'GET',
        'path': '/analytics/trends',
        'headers': {},
        'pathParameters': {},
        'queryStringParameters': None
    }
    
    response = get_seasonal_trends.handler(event, None)
    
    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    trends = body['trends']
    
    # Should still return data with zero sales
    assert trends['summary']['totalProducts'] == 2
    assert trends['seasonalVsNonSeasonal']['seasonal']['totalSales'] == 0
    assert trends['seasonalVsNonSeasonal']['nonSeasonal']['totalSales'] == 0
    assert trends['seasonalVsNonSeasonal']['seasonal']['totalRevenue'] == 0.0
    assert trends['seasonalVsNonSeasonal']['nonSeasonal']['totalRevenue'] == 0.0


def test_seasonal_trends_cors_headers(dynamodb_table):
    """Test that CORS headers are included in response."""
    event = {
        'httpMethod': 'GET',
        'path': '/analytics/trends',
        'headers': {},
        'pathParameters': {},
        'queryStringParameters': None
    }
    
    response = get_seasonal_trends.handler(event, None)
    
    assert response['statusCode'] == 200
    assert 'Access-Control-Allow-Origin' in response['headers']
    assert response['headers']['Access-Control-Allow-Origin'] == '*'
    assert response['headers']['Content-Type'] == 'application/json'


def test_seasonal_trends_database_error(dynamodb_table):
    """Test error handling when database query fails."""
    # Mock scan to raise an exception
    with patch('analytics.get_seasonal_trends.scan') as mock_scan:
        mock_scan.side_effect = Exception('Database connection failed')
        
        event = {
            'httpMethod': 'GET',
            'path': '/analytics/trends',
            'headers': {},
            'pathParameters': {},
            'queryStringParameters': None
        }
        
        response = get_seasonal_trends.handler(event, None)
        
        assert response['statusCode'] == 503
        body = json.loads(response['body'])
        assert 'error' in body
        assert body['error']['code'] == 'SERVICE_UNAVAILABLE'


def test_seasonal_trends_wrapping_season(dynamodb_table):
    """Test seasonal availability for seasons that wrap around the year (e.g., Nov-Feb)."""
    # Create a winter product (November to February)
    products = [
        create_product('p1', 'f1', 'vegetables', True, 50, 20.0,
                      datetime(2024, 11, 1).isoformat(),
                      datetime(2025, 2, 28).isoformat()),
    ]
    
    for product in products:
        dynamodb_table.put_item(Item=product)
    
    event = {
        'httpMethod': 'GET',
        'path': '/analytics/trends',
        'headers': {},
        'pathParameters': {},
        'queryStringParameters': None
    }
    
    response = get_seasonal_trends.handler(event, None)
    
    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    trends = body['trends']
    
    seasonal_availability = trends['seasonalAvailability']
    
    # Check that product is available in November, December, January, February
    nov_data = next((m for m in seasonal_availability if m['month'] == 11), None)
    assert nov_data['productsAvailable'] == 1
    
    dec_data = next((m for m in seasonal_availability if m['month'] == 12), None)
    assert dec_data['productsAvailable'] == 1
    
    jan_data = next((m for m in seasonal_availability if m['month'] == 1), None)
    assert jan_data['productsAvailable'] == 1
    
    feb_data = next((m for m in seasonal_availability if m['month'] == 2), None)
    assert feb_data['productsAvailable'] == 1
    
    # Check that product is NOT available in summer months
    jul_data = next((m for m in seasonal_availability if m['month'] == 7), None)
    assert jul_data['productsAvailable'] == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
