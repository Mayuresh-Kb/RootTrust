"""
Unit tests for farmer analytics dashboard endpoint.
Tests GET /analytics/farmer/{farmerId} endpoint.
"""
import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from decimal import Decimal

# Add backend paths to sys.path
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend', 'shared'))

# Import after path setup
from shared.constants import UserRole, OrderStatus

# Import the handler module
from analytics import get_farmer_analytics


@pytest.fixture
def mock_env(monkeypatch):
    """Set up environment variables for tests."""
    monkeypatch.setenv('DYNAMODB_TABLE_NAME', 'RootTrustData-test')
    monkeypatch.setenv('JWT_SECRET_KEY', 'test-secret-key-12345')


@pytest.fixture
def mock_dependencies():
    """Mock all external dependencies."""
    with patch('analytics.get_farmer_analytics.query') as mock_query, \
         patch('analytics.get_farmer_analytics.get_item') as mock_get_item, \
         patch('analytics.get_farmer_analytics.get_user_from_token') as mock_auth:
        yield {
            'query': mock_query,
            'get_item': mock_get_item,
            'auth': mock_auth
        }


@pytest.fixture
def valid_auth_header():
    """Valid authorization header."""
    return 'Bearer valid_token_here'


@pytest.fixture
def farmer_user_info():
    """Farmer user information from token."""
    return {
        'userId': 'farmer-123',
        'email': 'farmer@example.com',
        'role': 'farmer'
    }


@pytest.fixture
def consumer_user_info():
    """Consumer user information from token."""
    return {
        'userId': 'consumer-456',
        'email': 'consumer@example.com',
        'role': 'consumer'
    }


@pytest.fixture
def sample_orders():
    """Sample orders for testing."""
    now = datetime.utcnow()
    month_start = datetime(now.year, now.month, 1)
    last_month = month_start - timedelta(days=1)
    
    return [
        {
            'orderId': 'order-1',
            'productId': 'product-1',
            'productName': 'Organic Tomatoes',
            'totalAmount': Decimal('150.00'),
            'status': 'delivered',
            'createdAt': now.isoformat()
        },
        {
            'orderId': 'order-2',
            'productId': 'product-2',
            'productName': 'Fresh Mangoes',
            'totalAmount': Decimal('300.00'),
            'status': 'delivered',
            'createdAt': now.isoformat()
        },
        {
            'orderId': 'order-3',
            'productId': 'product-1',
            'productName': 'Organic Tomatoes',
            'totalAmount': Decimal('200.00'),
            'status': 'delivered',
            'createdAt': now.isoformat()
        },
        {
            'orderId': 'order-4',
            'productId': 'product-3',
            'productName': 'Basmati Rice',
            'totalAmount': Decimal('500.00'),
            'status': 'delivered',
            'createdAt': last_month.isoformat()  # Last month
        },
        {
            'orderId': 'order-5',
            'productId': 'product-1',
            'productName': 'Organic Tomatoes',
            'totalAmount': Decimal('100.00'),
            'status': 'pending',  # Not delivered
            'createdAt': now.isoformat()
        }
    ]


@pytest.fixture
def sample_farmer_record():
    """Sample farmer record."""
    return {
        'userId': 'farmer-123',
        'email': 'farmer@example.com',
        'role': 'farmer',
        'farmerProfile': {
            'farmName': 'Green Valley Farm',
            'averageRating': Decimal('4.5'),
            'totalReviews': 25,
            'totalSales': 100
        }
    }


@pytest.fixture
def sample_products():
    """Sample products for testing."""
    return [
        {
            'productId': 'product-1',
            'name': 'Organic Tomatoes',
            'viewCount': 500,
            'totalSales': 50
        },
        {
            'productId': 'product-2',
            'name': 'Fresh Mangoes',
            'viewCount': 300,
            'totalSales': 20
        },
        {
            'productId': 'product-3',
            'name': 'Basmati Rice',
            'viewCount': 200,
            'totalSales': 10
        }
    ]


def test_farmer_analytics_success(mock_env, mock_dependencies, valid_auth_header, farmer_user_info, 
                                   sample_orders, sample_farmer_record, sample_products):
    """Test successful farmer analytics retrieval."""
    
    # Setup mocks
    mock_dependencies['auth'].return_value = farmer_user_info
    mock_dependencies['query'].side_effect = [
        {'Items': sample_orders},  # Orders query
        {'Items': sample_products}  # Products query
    ]
    mock_dependencies['get_item'].return_value = sample_farmer_record
    
    # Create event
    event = {
        'headers': {'Authorization': valid_auth_header},
        'pathParameters': {'farmerId': 'farmer-123'}
    }
    
    # Call handler
    response = get_farmer_analytics.handler(event, None)
    
    # Verify response
    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert 'analytics' in body
    
    analytics = body['analytics']
    assert analytics['farmerId'] == 'farmer-123'
    assert analytics['monthlyRevenue'] == 650.0  # 150 + 300 + 200 (current month delivered)
    assert analytics['totalSales'] == 4  # All delivered orders
    assert analytics['averageRating'] == 4.5
    assert analytics['totalReviews'] == 25
    assert analytics['totalViews'] == 1000  # 500 + 300 + 200
    assert 'conversionRate' in analytics
    assert 'topProducts' in analytics
    assert len(analytics['topProducts']) > 0
    assert 'productAnalytics' in analytics


def test_farmer_analytics_missing_auth_header(mock_dependencies):
    """Test analytics request without authorization header."""
    # Import already done at top
    
    event = {
        'headers': {},
        'pathParameters': {'farmerId': 'farmer-123'}
    }
    
    response = get_farmer_analytics.handler(event, None)
    
    assert response['statusCode'] == 401
    body = json.loads(response['body'])
    assert body['error']['code'] == 'UNAUTHORIZED'


def test_farmer_analytics_invalid_token(mock_dependencies, valid_auth_header):
    """Test analytics request with invalid token."""
    # Import already done at top
    
    mock_dependencies['auth'].side_effect = Exception('Invalid token')
    
    event = {
        'headers': {'Authorization': valid_auth_header},
        'pathParameters': {'farmerId': 'farmer-123'}
    }
    
    response = get_farmer_analytics.handler(event, None)
    
    assert response['statusCode'] == 401
    body = json.loads(response['body'])
    assert body['error']['code'] == 'INVALID_TOKEN'


def test_farmer_analytics_consumer_role_forbidden(mock_dependencies, valid_auth_header, consumer_user_info):
    """Test analytics request by consumer (should be forbidden)."""
    # Import already done at top
    
    mock_dependencies['auth'].return_value = consumer_user_info
    
    event = {
        'headers': {'Authorization': valid_auth_header},
        'pathParameters': {'farmerId': 'farmer-123'}
    }
    
    response = get_farmer_analytics.handler(event, None)
    
    assert response['statusCode'] == 403
    body = json.loads(response['body'])
    assert body['error']['code'] == 'FORBIDDEN'
    assert 'farmers' in body['error']['message'].lower()


def test_farmer_analytics_missing_farmer_id(mock_dependencies, valid_auth_header, farmer_user_info):
    """Test analytics request without farmerId parameter."""
    # Import already done at top
    
    mock_dependencies['auth'].return_value = farmer_user_info
    
    event = {
        'headers': {'Authorization': valid_auth_header},
        'pathParameters': {}
    }
    
    response = get_farmer_analytics.handler(event, None)
    
    assert response['statusCode'] == 400
    body = json.loads(response['body'])
    assert body['error']['code'] == 'BAD_REQUEST'


def test_farmer_analytics_accessing_other_farmer_data(mock_dependencies, valid_auth_header, farmer_user_info):
    """Test farmer trying to access another farmer's analytics."""
    # Import already done at top
    
    mock_dependencies['auth'].return_value = farmer_user_info
    
    event = {
        'headers': {'Authorization': valid_auth_header},
        'pathParameters': {'farmerId': 'other-farmer-456'}
    }
    
    response = get_farmer_analytics.handler(event, None)
    
    assert response['statusCode'] == 403
    body = json.loads(response['body'])
    assert body['error']['code'] == 'FORBIDDEN'
    assert 'your own' in body['error']['message'].lower()


def test_farmer_analytics_no_orders(mock_dependencies, valid_auth_header, farmer_user_info, 
                                    sample_farmer_record, sample_products):
    """Test analytics when farmer has no orders."""
    # Import already done at top
    
    mock_dependencies['auth'].return_value = farmer_user_info
    mock_dependencies['query'].side_effect = [
        {'Items': []},  # No orders
        {'Items': sample_products}  # Products
    ]
    mock_dependencies['get_item'].return_value = sample_farmer_record
    
    event = {
        'headers': {'Authorization': valid_auth_header},
        'pathParameters': {'farmerId': 'farmer-123'}
    }
    
    response = get_farmer_analytics.handler(event, None)
    
    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    analytics = body['analytics']
    assert analytics['monthlyRevenue'] == 0.0
    assert analytics['totalSales'] == 0
    assert len(analytics['topProducts']) == 0


def test_farmer_analytics_no_products(mock_dependencies, valid_auth_header, farmer_user_info, 
                                      sample_orders, sample_farmer_record):
    """Test analytics when farmer has no products."""
    # Import already done at top
    
    mock_dependencies['auth'].return_value = farmer_user_info
    mock_dependencies['query'].side_effect = [
        {'Items': sample_orders},  # Orders
        {'Items': []}  # No products
    ]
    mock_dependencies['get_item'].return_value = sample_farmer_record
    
    event = {
        'headers': {'Authorization': valid_auth_header},
        'pathParameters': {'farmerId': 'farmer-123'}
    }
    
    response = get_farmer_analytics.handler(event, None)
    
    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    analytics = body['analytics']
    assert analytics['totalViews'] == 0
    assert len(analytics['productAnalytics']) == 0


def test_farmer_analytics_farmer_not_found(mock_dependencies, valid_auth_header, farmer_user_info, sample_orders):
    """Test analytics when farmer record doesn't exist."""
    # Import already done at top
    
    mock_dependencies['auth'].return_value = farmer_user_info
    mock_dependencies['query'].return_value = {'Items': sample_orders}
    mock_dependencies['get_item'].return_value = None  # Farmer not found
    
    event = {
        'headers': {'Authorization': valid_auth_header},
        'pathParameters': {'farmerId': 'farmer-123'}
    }
    
    response = get_farmer_analytics.handler(event, None)
    
    assert response['statusCode'] == 404
    body = json.loads(response['body'])
    assert body['error']['code'] == 'NOT_FOUND'


def test_farmer_analytics_database_error_orders(mock_dependencies, valid_auth_header, farmer_user_info):
    """Test analytics when orders query fails."""
    # Import already done at top
    
    mock_dependencies['auth'].return_value = farmer_user_info
    mock_dependencies['query'].side_effect = Exception('Database error')
    
    event = {
        'headers': {'Authorization': valid_auth_header},
        'pathParameters': {'farmerId': 'farmer-123'}
    }
    
    response = get_farmer_analytics.handler(event, None)
    
    assert response['statusCode'] == 503
    body = json.loads(response['body'])
    assert body['error']['code'] == 'SERVICE_UNAVAILABLE'


def test_farmer_analytics_database_error_farmer_record(mock_dependencies, valid_auth_header, 
                                                        farmer_user_info, sample_orders):
    """Test analytics when farmer record query fails."""
    # Import already done at top
    
    mock_dependencies['auth'].return_value = farmer_user_info
    mock_dependencies['query'].return_value = {'Items': sample_orders}
    mock_dependencies['get_item'].side_effect = Exception('Database error')
    
    event = {
        'headers': {'Authorization': valid_auth_header},
        'pathParameters': {'farmerId': 'farmer-123'}
    }
    
    response = get_farmer_analytics.handler(event, None)
    
    assert response['statusCode'] == 503
    body = json.loads(response['body'])
    assert body['error']['code'] == 'SERVICE_UNAVAILABLE'


def test_farmer_analytics_database_error_products(mock_dependencies, valid_auth_header, 
                                                   farmer_user_info, sample_orders, sample_farmer_record):
    """Test analytics when products query fails."""
    # Import already done at top
    
    mock_dependencies['auth'].return_value = farmer_user_info
    mock_dependencies['query'].side_effect = [
        {'Items': sample_orders},  # Orders succeed
        Exception('Database error')  # Products fail
    ]
    mock_dependencies['get_item'].return_value = sample_farmer_record
    
    event = {
        'headers': {'Authorization': valid_auth_header},
        'pathParameters': {'farmerId': 'farmer-123'}
    }
    
    response = get_farmer_analytics.handler(event, None)
    
    assert response['statusCode'] == 503
    body = json.loads(response['body'])
    assert body['error']['code'] == 'SERVICE_UNAVAILABLE'


def test_farmer_analytics_conversion_rate_calculation(mock_dependencies, valid_auth_header, 
                                                       farmer_user_info, sample_farmer_record):
    """Test conversion rate calculation with specific values."""
    # Import already done at top
    
    now = datetime.utcnow()
    
    # 10 orders, 100 views = 10% conversion rate
    orders = [
        {
            'orderId': f'order-{i}',
            'productId': 'product-1',
            'productName': 'Test Product',
            'totalAmount': Decimal('100.00'),
            'status': 'delivered',
            'createdAt': now.isoformat()
        }
        for i in range(10)
    ]
    
    products = [
        {
            'productId': 'product-1',
            'name': 'Test Product',
            'viewCount': 100,
            'totalSales': 10
        }
    ]
    
    mock_dependencies['auth'].return_value = farmer_user_info
    mock_dependencies['query'].side_effect = [
        {'Items': orders},
        {'Items': products}
    ]
    mock_dependencies['get_item'].return_value = sample_farmer_record
    
    event = {
        'headers': {'Authorization': valid_auth_header},
        'pathParameters': {'farmerId': 'farmer-123'}
    }
    
    response = get_farmer_analytics.handler(event, None)
    
    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    analytics = body['analytics']
    assert analytics['conversionRate'] == 10.0  # 10 sales / 100 views * 100


def test_farmer_analytics_top_products_ranking(mock_dependencies, valid_auth_header, 
                                                farmer_user_info, sample_farmer_record):
    """Test top products are correctly ranked by revenue."""
    # Import already done at top
    
    now = datetime.utcnow()
    
    orders = [
        {
            'orderId': 'order-1',
            'productId': 'product-1',
            'productName': 'Product A',
            'totalAmount': Decimal('500.00'),
            'status': 'delivered',
            'createdAt': now.isoformat()
        },
        {
            'orderId': 'order-2',
            'productId': 'product-2',
            'productName': 'Product B',
            'totalAmount': Decimal('300.00'),
            'status': 'delivered',
            'createdAt': now.isoformat()
        },
        {
            'orderId': 'order-3',
            'productId': 'product-1',
            'productName': 'Product A',
            'totalAmount': Decimal('200.00'),
            'status': 'delivered',
            'createdAt': now.isoformat()
        }
    ]
    
    products = [
        {'productId': 'product-1', 'name': 'Product A', 'viewCount': 100},
        {'productId': 'product-2', 'name': 'Product B', 'viewCount': 50}
    ]
    
    mock_dependencies['auth'].return_value = farmer_user_info
    mock_dependencies['query'].side_effect = [
        {'Items': orders},
        {'Items': products}
    ]
    mock_dependencies['get_item'].return_value = sample_farmer_record
    
    event = {
        'headers': {'Authorization': valid_auth_header},
        'pathParameters': {'farmerId': 'farmer-123'}
    }
    
    response = get_farmer_analytics.handler(event, None)
    
    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    analytics = body['analytics']
    
    # Product A should be first (700 revenue), Product B second (300 revenue)
    assert len(analytics['topProducts']) == 2
    assert analytics['topProducts'][0]['productId'] == 'product-1'
    assert analytics['topProducts'][0]['revenue'] == 700.0
    assert analytics['topProducts'][1]['productId'] == 'product-2'
    assert analytics['topProducts'][1]['revenue'] == 300.0


def test_farmer_analytics_zero_views_no_division_error(mock_dependencies, valid_auth_header, 
                                                        farmer_user_info, sample_farmer_record):
    """Test that zero views doesn't cause division by zero error."""
    # Import already done at top
    
    now = datetime.utcnow()
    
    orders = [
        {
            'orderId': 'order-1',
            'productId': 'product-1',
            'productName': 'Test Product',
            'totalAmount': Decimal('100.00'),
            'status': 'delivered',
            'createdAt': now.isoformat()
        }
    ]
    
    products = [
        {
            'productId': 'product-1',
            'name': 'Test Product',
            'viewCount': 0  # Zero views
        }
    ]
    
    mock_dependencies['auth'].return_value = farmer_user_info
    mock_dependencies['query'].side_effect = [
        {'Items': orders},
        {'Items': products}
    ]
    mock_dependencies['get_item'].return_value = sample_farmer_record
    
    event = {
        'headers': {'Authorization': valid_auth_header},
        'pathParameters': {'farmerId': 'farmer-123'}
    }
    
    response = get_farmer_analytics.handler(event, None)
    
    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    analytics = body['analytics']
    assert analytics['conversionRate'] == 0.0
    assert analytics['productAnalytics'][0]['conversionRate'] == 0.0


def test_farmer_analytics_period_information(mock_dependencies, valid_auth_header, 
                                              farmer_user_info, sample_orders, 
                                              sample_farmer_record, sample_products):
    """Test that period information is included in response."""
    # Import already done at top
    
    mock_dependencies['auth'].return_value = farmer_user_info
    mock_dependencies['query'].side_effect = [
        {'Items': sample_orders},
        {'Items': sample_products}
    ]
    mock_dependencies['get_item'].return_value = sample_farmer_record
    
    event = {
        'headers': {'Authorization': valid_auth_header},
        'pathParameters': {'farmerId': 'farmer-123'}
    }
    
    response = get_farmer_analytics.handler(event, None)
    
    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    analytics = body['analytics']
    
    assert 'period' in analytics
    assert 'month' in analytics['period']
    assert 'year' in analytics['period']
    assert 'monthStart' in analytics['period']
    
    now = datetime.utcnow()
    assert analytics['period']['month'] == now.month
    assert analytics['period']['year'] == now.year
