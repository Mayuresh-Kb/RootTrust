"""
Unit tests for product analytics endpoint.
Tests GET /analytics/product/{productId} endpoint.
"""
import json
import pytest
from unittest.mock import patch
from decimal import Decimal

# Add backend paths to sys.path
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend', 'shared'))

# Import the handler module
from analytics import get_product_analytics


@pytest.fixture
def mock_env(monkeypatch):
    """Set up environment variables for tests."""
    monkeypatch.setenv('DYNAMODB_TABLE_NAME', 'RootTrustData-test')


@pytest.fixture
def mock_dependencies():
    """Mock all external dependencies."""
    with patch('analytics.get_product_analytics.get_item') as mock_get_item:
        yield {
            'get_item': mock_get_item
        }


@pytest.fixture
def sample_product_record():
    """Sample product record with analytics data."""
    return {
        'productId': 'product-123',
        'name': 'Organic Tomatoes',
        'category': 'vegetables',
        'price': Decimal('150.00'),
        'viewCount': 500,
        'totalSales': 50,
        'averageRating': Decimal('4.5'),
        'totalReviews': 25,
        'verificationStatus': 'approved'
    }


def test_product_analytics_success(mock_env, mock_dependencies, sample_product_record):
    """Test successful product analytics retrieval."""
    
    # Setup mocks
    mock_dependencies['get_item'].return_value = sample_product_record
    
    # Create event
    event = {
        'pathParameters': {'productId': 'product-123'}
    }
    
    # Call handler
    response = get_product_analytics.handler(event, None)
    
    # Verify response
    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert 'analytics' in body
    
    analytics = body['analytics']
    assert analytics['productId'] == 'product-123'
    assert analytics['productName'] == 'Organic Tomatoes'
    assert analytics['viewCount'] == 500
    assert analytics['totalSales'] == 50
    assert analytics['averageRating'] == 4.5
    assert analytics['totalReviews'] == 25
    assert analytics['conversionRate'] == 10.0  # 50/500 * 100
    assert analytics['category'] == 'vegetables'
    assert analytics['price'] == 150.0
    assert analytics['verificationStatus'] == 'approved'


def test_product_analytics_missing_product_id(mock_dependencies):
    """Test analytics request without productId parameter."""
    
    event = {
        'pathParameters': {}
    }
    
    response = get_product_analytics.handler(event, None)
    
    assert response['statusCode'] == 400
    body = json.loads(response['body'])
    assert body['error']['code'] == 'BAD_REQUEST'
    assert 'productid' in body['error']['message'].lower()


def test_product_analytics_product_not_found(mock_dependencies):
    """Test analytics request for non-existent product."""
    
    mock_dependencies['get_item'].return_value = None
    
    event = {
        'pathParameters': {'productId': 'nonexistent-product'}
    }
    
    response = get_product_analytics.handler(event, None)
    
    assert response['statusCode'] == 404
    body = json.loads(response['body'])
    assert body['error']['code'] == 'NOT_FOUND'
    assert 'not found' in body['error']['message'].lower()


def test_product_analytics_database_error(mock_dependencies):
    """Test analytics when database query fails."""
    
    mock_dependencies['get_item'].side_effect = Exception('Database error')
    
    event = {
        'pathParameters': {'productId': 'product-123'}
    }
    
    response = get_product_analytics.handler(event, None)
    
    assert response['statusCode'] == 503
    body = json.loads(response['body'])
    assert body['error']['code'] == 'SERVICE_UNAVAILABLE'


def test_product_analytics_zero_views_no_division_error(mock_dependencies):
    """Test that zero views doesn't cause division by zero error."""
    
    product_record = {
        'productId': 'product-123',
        'name': 'New Product',
        'category': 'fruits',
        'price': Decimal('200.00'),
        'viewCount': 0,  # Zero views
        'totalSales': 0,
        'averageRating': Decimal('0.0'),
        'totalReviews': 0,
        'verificationStatus': 'approved'
    }
    
    mock_dependencies['get_item'].return_value = product_record
    
    event = {
        'pathParameters': {'productId': 'product-123'}
    }
    
    response = get_product_analytics.handler(event, None)
    
    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    analytics = body['analytics']
    assert analytics['conversionRate'] == 0.0


def test_product_analytics_conversion_rate_calculation(mock_dependencies):
    """Test conversion rate calculation with specific values."""
    
    # 25 sales, 100 views = 25% conversion rate
    product_record = {
        'productId': 'product-456',
        'name': 'Fresh Mangoes',
        'category': 'fruits',
        'price': Decimal('300.00'),
        'viewCount': 100,
        'totalSales': 25,
        'averageRating': Decimal('4.8'),
        'totalReviews': 15,
        'verificationStatus': 'approved'
    }
    
    mock_dependencies['get_item'].return_value = product_record
    
    event = {
        'pathParameters': {'productId': 'product-456'}
    }
    
    response = get_product_analytics.handler(event, None)
    
    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    analytics = body['analytics']
    assert analytics['conversionRate'] == 25.0


def test_product_analytics_high_conversion_rate(mock_dependencies):
    """Test product with high conversion rate."""
    
    # 90 sales, 100 views = 90% conversion rate
    product_record = {
        'productId': 'product-789',
        'name': 'Premium Basmati Rice',
        'category': 'grains',
        'price': Decimal('500.00'),
        'viewCount': 100,
        'totalSales': 90,
        'averageRating': Decimal('5.0'),
        'totalReviews': 50,
        'verificationStatus': 'approved'
    }
    
    mock_dependencies['get_item'].return_value = product_record
    
    event = {
        'pathParameters': {'productId': 'product-789'}
    }
    
    response = get_product_analytics.handler(event, None)
    
    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    analytics = body['analytics']
    assert analytics['conversionRate'] == 90.0


def test_product_analytics_low_conversion_rate(mock_dependencies):
    """Test product with low conversion rate."""
    
    # 5 sales, 1000 views = 0.5% conversion rate
    product_record = {
        'productId': 'product-101',
        'name': 'Exotic Spices',
        'category': 'spices',
        'price': Decimal('800.00'),
        'viewCount': 1000,
        'totalSales': 5,
        'averageRating': Decimal('3.5'),
        'totalReviews': 3,
        'verificationStatus': 'approved'
    }
    
    mock_dependencies['get_item'].return_value = product_record
    
    event = {
        'pathParameters': {'productId': 'product-101'}
    }
    
    response = get_product_analytics.handler(event, None)
    
    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    analytics = body['analytics']
    assert analytics['conversionRate'] == 0.5


def test_product_analytics_missing_optional_fields(mock_dependencies):
    """Test analytics when product has missing optional fields."""
    
    # Minimal product record
    product_record = {
        'productId': 'product-minimal',
        # Missing name, category, etc.
    }
    
    mock_dependencies['get_item'].return_value = product_record
    
    event = {
        'pathParameters': {'productId': 'product-minimal'}
    }
    
    response = get_product_analytics.handler(event, None)
    
    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    analytics = body['analytics']
    assert analytics['productId'] == 'product-minimal'
    assert analytics['productName'] == 'Unknown'
    assert analytics['viewCount'] == 0
    assert analytics['totalSales'] == 0
    assert analytics['averageRating'] == 0.0
    assert analytics['totalReviews'] == 0
    assert analytics['conversionRate'] == 0.0
    assert analytics['category'] == 'Unknown'


def test_product_analytics_decimal_conversion(mock_dependencies):
    """Test that Decimal values are properly converted to float."""
    
    product_record = {
        'productId': 'product-decimal',
        'name': 'Test Product',
        'category': 'vegetables',
        'price': Decimal('123.45'),
        'viewCount': 200,
        'totalSales': 20,
        'averageRating': Decimal('4.75'),
        'totalReviews': 10,
        'verificationStatus': 'approved'
    }
    
    mock_dependencies['get_item'].return_value = product_record
    
    event = {
        'pathParameters': {'productId': 'product-decimal'}
    }
    
    response = get_product_analytics.handler(event, None)
    
    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    analytics = body['analytics']
    
    # Verify all numeric values are JSON-serializable (not Decimal)
    assert isinstance(analytics['price'], float)
    assert isinstance(analytics['averageRating'], float)
    assert isinstance(analytics['conversionRate'], float)
    assert analytics['price'] == 123.45
    assert analytics['averageRating'] == 4.75


def test_product_analytics_rounding(mock_dependencies):
    """Test that values are properly rounded to 2 decimal places."""
    
    # 33 sales, 100 views = 33.0% conversion rate
    product_record = {
        'productId': 'product-round',
        'name': 'Test Product',
        'category': 'fruits',
        'price': Decimal('99.999'),
        'viewCount': 100,
        'totalSales': 33,
        'averageRating': Decimal('4.567'),
        'totalReviews': 20,
        'verificationStatus': 'approved'
    }
    
    mock_dependencies['get_item'].return_value = product_record
    
    event = {
        'pathParameters': {'productId': 'product-round'}
    }
    
    response = get_product_analytics.handler(event, None)
    
    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    analytics = body['analytics']
    
    # Check rounding
    assert analytics['averageRating'] == 4.57
    assert analytics['conversionRate'] == 33.0


def test_product_analytics_no_sales_with_views(mock_dependencies):
    """Test product with views but no sales."""
    
    product_record = {
        'productId': 'product-no-sales',
        'name': 'Unpopular Product',
        'category': 'dairy',
        'price': Decimal('1000.00'),
        'viewCount': 500,
        'totalSales': 0,  # No sales
        'averageRating': Decimal('0.0'),
        'totalReviews': 0,
        'verificationStatus': 'approved'
    }
    
    mock_dependencies['get_item'].return_value = product_record
    
    event = {
        'pathParameters': {'productId': 'product-no-sales'}
    }
    
    response = get_product_analytics.handler(event, None)
    
    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    analytics = body['analytics']
    assert analytics['viewCount'] == 500
    assert analytics['totalSales'] == 0
    assert analytics['conversionRate'] == 0.0


def test_product_analytics_cors_headers(mock_dependencies, sample_product_record):
    """Test that CORS headers are included in response."""
    
    mock_dependencies['get_item'].return_value = sample_product_record
    
    event = {
        'pathParameters': {'productId': 'product-123'}
    }
    
    response = get_product_analytics.handler(event, None)
    
    assert 'Access-Control-Allow-Origin' in response['headers']
    assert response['headers']['Access-Control-Allow-Origin'] == '*'
    assert response['headers']['Content-Type'] == 'application/json'


def test_product_analytics_error_cors_headers(mock_dependencies):
    """Test that CORS headers are included in error responses."""
    
    mock_dependencies['get_item'].return_value = None
    
    event = {
        'pathParameters': {'productId': 'nonexistent'}
    }
    
    response = get_product_analytics.handler(event, None)
    
    assert response['statusCode'] == 404
    assert 'Access-Control-Allow-Origin' in response['headers']
    assert response['headers']['Access-Control-Allow-Origin'] == '*'


def test_product_analytics_includes_all_required_fields(mock_dependencies, sample_product_record):
    """Test that response includes all required analytics fields."""
    
    mock_dependencies['get_item'].return_value = sample_product_record
    
    event = {
        'pathParameters': {'productId': 'product-123'}
    }
    
    response = get_product_analytics.handler(event, None)
    
    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    analytics = body['analytics']
    
    # Verify all required fields are present
    required_fields = [
        'productId', 'productName', 'viewCount', 'totalSales',
        'averageRating', 'totalReviews', 'conversionRate',
        'category', 'price', 'verificationStatus'
    ]
    
    for field in required_fields:
        assert field in analytics, f"Missing required field: {field}"
