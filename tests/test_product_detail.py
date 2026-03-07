"""
Unit tests for product detail endpoint (GET /products/{productId}).
Tests Requirements 5.1, 5.2, 5.3, 5.4, 5.5
"""
import json
import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import patch, MagicMock, Mock
import sys
import os

# Setup path
backend_path = os.path.join(os.path.dirname(__file__), '..', 'backend')
sys.path.insert(0, backend_path)


@pytest.fixture
def mock_shared_modules():
    """Mock shared modules."""
    with patch.dict('sys.modules', {
        'shared': MagicMock(),
        'shared.database': MagicMock(),
        'shared.constants': MagicMock(),
        'shared.exceptions': MagicMock()
    }):
        yield


@pytest.fixture
def sample_product():
    """Sample product data."""
    return {
        'PK': 'PRODUCT#test-product-123',
        'SK': 'METADATA',
        'EntityType': 'Product',
        'productId': 'test-product-123',
        'farmerId': 'farmer-456',
        'name': 'Organic Alphonso Mangoes',
        'category': 'fruits',
        'description': 'Premium quality Alphonso mangoes from Ratnagiri',
        'price': Decimal('450.00'),
        'unit': 'kg',
        'giTag': {
            'hasTag': True,
            'tagName': 'Ratnagiri Alphonso',
            'region': 'Ratnagiri, Maharashtra'
        },
        'seasonal': {
            'isSeasonal': True,
            'seasonStart': (datetime.utcnow() - timedelta(days=30)).isoformat(),
            'seasonEnd': (datetime.utcnow() + timedelta(days=15)).isoformat()
        },
        'images': [
            {'url': 'https://s3.amazonaws.com/image1.jpg', 'isPrimary': True},
            {'url': 'https://s3.amazonaws.com/image2.jpg', 'isPrimary': False}
        ],
        'verificationStatus': 'approved',
        'fraudRiskScore': Decimal('15.5'),
        'authenticityConfidence': Decimal('92.3'),
        'aiExplanation': 'Product verified with high confidence',
        'predictedMarketPrice': Decimal('420.00'),
        'quantity': 50,
        'averageRating': Decimal('4.5'),
        'totalReviews': 12,
        'totalSales': 45,
        'viewCount': 234,
        'currentViewers': 3,
        'recentPurchaseCount': 8,
        'createdAt': '2024-01-15T10:30:00Z',
        'updatedAt': '2024-01-20T14:45:00Z'
    }


@pytest.fixture
def sample_farmer_profile():
    """Sample farmer profile data."""
    return {
        'PK': 'USER#farmer-456',
        'SK': 'PROFILE',
        'userId': 'farmer-456',
        'email': 'farmer@example.com',
        'role': 'farmer',
        'firstName': 'Ramesh',
        'lastName': 'Patil',
        'farmerProfile': {
            'farmName': 'Patil Organic Farms',
            'farmLocation': 'Ratnagiri, Maharashtra',
            'certifications': ['Organic India', 'FSSAI'],
            'averageRating': 4.7,
            'totalReviews': 45,
            'totalSales': 120,
            'featuredStatus': True
        }
    }


@pytest.fixture
def sample_reviews():
    """Sample product reviews."""
    return [
        {
            'PK': 'PRODUCT#test-product-123',
            'SK': 'REVIEW#review-1',
            'reviewId': 'review-1',
            'consumerId': 'consumer-1',
            'rating': 5,
            'reviewText': 'Excellent quality mangoes!',
            'photos': [{'url': 'https://s3.amazonaws.com/review1.jpg', 'caption': 'Fresh mangoes'}],
            'helpful': 10,
            'createdAt': '2024-01-18T12:00:00Z'
        },
        {
            'PK': 'PRODUCT#test-product-123',
            'SK': 'REVIEW#review-2',
            'reviewId': 'review-2',
            'consumerId': 'consumer-2',
            'rating': 4,
            'reviewText': 'Good taste, slightly expensive',
            'photos': [],
            'helpful': 5,
            'createdAt': '2024-01-17T09:30:00Z'
        }
    ]


@pytest.fixture
def api_gateway_event():
    """Sample API Gateway event."""
    return {
        'httpMethod': 'GET',
        'path': '/products/test-product-123',
        'pathParameters': {
            'productId': 'test-product-123'
        },
        'headers': {
            'Content-Type': 'application/json'
        },
        'queryStringParameters': None,
        'body': None
    }


class TestProductDetailEndpoint:
    """Integration tests for product detail endpoint."""
    
    def test_handler_success(self, mock_shared_modules, api_gateway_event, sample_product, sample_farmer_profile):
        """Test successful product detail retrieval - Requirements 5.1, 5.2, 5.3, 5.4, 5.5."""
        # Import after mocking
        from products import get_product_detail
        
        # Setup mocks
        with patch.object(get_product_detail, 'get_item') as mock_get_item, \
             patch.object(get_product_detail, 'get_farmer_profile') as mock_get_farmer, \
             patch.object(get_product_detail, 'get_product_reviews') as mock_get_reviews, \
             patch.object(get_product_detail, 'increment_viewer_count') as mock_increment:
            
            mock_get_item.return_value = sample_product
            mock_get_farmer.return_value = {
                'farmerId': 'farmer-456',
                'firstName': 'Ramesh',
                'lastName': 'Patil',
                'farmName': 'Patil Organic Farms',
                'farmLocation': 'Ratnagiri, Maharashtra',
                'certifications': ['Organic India', 'FSSAI'],
                'averageRating': 4.7,
                'totalReviews': 45,
                'totalSales': 120,
                'featuredStatus': True
            }
            mock_get_reviews.return_value = [
                {
                    'reviewId': 'review-1',
                    'consumerId': 'consumer-1',
                    'rating': 5,
                    'reviewText': 'Great product!',
                    'photos': [{'url': 'https://s3.amazonaws.com/photo.jpg', 'caption': 'Photo'}],
                    'helpful': 10,
                    'createdAt': '2024-01-18T12:00:00Z'
                }
            ]
            mock_increment.return_value = 5
            
            # Call handler
            response = get_product_detail.handler(api_gateway_event, None)
            
            # Verify response
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            
            # Requirement 5.1: Full product details
            assert body['productId'] == 'test-product-123'
            assert body['name'] == 'Organic Alphonso Mangoes'
            assert 'description' in body
            assert 'images' in body
            assert 'price' in body
            assert 'giTag' in body
            
            # Requirement 5.2: Authenticity confidence score
            assert 'authenticityConfidence' in body
            assert body['authenticityConfidence'] == 92.3
            
            # Requirement 5.3: Farmer profile with ratings
            assert 'farmer' in body
            assert body['farmer']['averageRating'] == 4.7
            assert body['farmer']['totalReviews'] == 45
            
            # Requirement 5.4: Customer reviews and ratings
            assert 'reviews' in body
            assert len(body['reviews']) > 0
            
            # Requirement 5.5: Customer photos in reviews
            assert len(body['reviews'][0]['photos']) > 0
    
    def test_handler_product_not_found(self, mock_shared_modules, api_gateway_event):
        """Test product not found error."""
        from products import get_product_detail
        
        with patch.object(get_product_detail, 'get_item') as mock_get_item:
            mock_get_item.return_value = None
            
            response = get_product_detail.handler(api_gateway_event, None)
            
            assert response['statusCode'] == 404
            body = json.loads(response['body'])
            assert body['error']['code'] == 'PRODUCT_NOT_FOUND'
    
    def test_handler_missing_product_id(self, mock_shared_modules):
        """Test missing product ID parameter."""
        from products import get_product_detail
        
        event = {
            'httpMethod': 'GET',
            'path': '/products/',
            'pathParameters': None,
            'headers': {},
            'queryStringParameters': None,
            'body': None
        }
        
        response = get_product_detail.handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error']['code'] == 'MISSING_PARAMETER'
    
    def test_low_stock_indicator(self, mock_shared_modules, api_gateway_event, sample_product):
        """Test low stock indicator when quantity < 10."""
        from products import get_product_detail
        
        sample_product['quantity'] = 5
        
        with patch.object(get_product_detail, 'get_item') as mock_get_item, \
             patch.object(get_product_detail, 'get_farmer_profile') as mock_get_farmer, \
             patch.object(get_product_detail, 'get_product_reviews') as mock_get_reviews, \
             patch.object(get_product_detail, 'increment_viewer_count') as mock_increment:
            
            mock_get_item.return_value = sample_product
            mock_get_farmer.return_value = None
            mock_get_reviews.return_value = []
            mock_increment.return_value = 1
            
            response = get_product_detail.handler(api_gateway_event, None)
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert body['lowStock'] is True
            assert body['quantity'] == 5


if __name__ == '__main__':
    pytest.main([__file__, '-v'])


@pytest.fixture
def sample_product():
    """Sample product data."""
    return {
        'PK': 'PRODUCT#test-product-123',
        'SK': 'METADATA',
        'EntityType': 'Product',
        'productId': 'test-product-123',
        'farmerId': 'farmer-456',
        'name': 'Organic Alphonso Mangoes',
        'category': 'fruits',
        'description': 'Premium quality Alphonso mangoes from Ratnagiri',
        'price': Decimal('450.00'),
        'unit': 'kg',
        'giTag': {
            'hasTag': True,
            'tagName': 'Ratnagiri Alphonso',
            'region': 'Ratnagiri, Maharashtra'
        },
        'seasonal': {
            'isSeasonal': True,
            'seasonStart': (datetime.utcnow() - timedelta(days=30)).isoformat(),
            'seasonEnd': (datetime.utcnow() + timedelta(days=15)).isoformat()
        },
        'images': [
            {'url': 'https://s3.amazonaws.com/image1.jpg', 'isPrimary': True},
            {'url': 'https://s3.amazonaws.com/image2.jpg', 'isPrimary': False}
        ],
        'verificationStatus': 'approved',
        'fraudRiskScore': Decimal('15.5'),
        'authenticityConfidence': Decimal('92.3'),
        'aiExplanation': 'Product verified with high confidence',
        'predictedMarketPrice': Decimal('420.00'),
        'quantity': 50,
        'averageRating': Decimal('4.5'),
        'totalReviews': 12,
        'totalSales': 45,
        'viewCount': 234,
        'currentViewers': 3,
        'recentPurchaseCount': 8,
        'createdAt': '2024-01-15T10:30:00Z',
        'updatedAt': '2024-01-20T14:45:00Z'
    }


@pytest.fixture
def sample_farmer_profile():
    """Sample farmer profile data."""
    return {
        'PK': 'USER#farmer-456',
        'SK': 'PROFILE',
        'userId': 'farmer-456',
        'email': 'farmer@example.com',
        'role': 'farmer',
        'firstName': 'Ramesh',
        'lastName': 'Patil',
        'farmerProfile': {
            'farmName': 'Patil Organic Farms',
            'farmLocation': 'Ratnagiri, Maharashtra',
            'certifications': ['Organic India', 'FSSAI'],
            'averageRating': 4.7,
            'totalReviews': 45,
            'totalSales': 120,
            'featuredStatus': True
        }
    }


@pytest.fixture
def sample_reviews():
    """Sample product reviews."""
    return [
        {
            'PK': 'PRODUCT#test-product-123',
            'SK': 'REVIEW#review-1',
            'reviewId': 'review-1',
            'consumerId': 'consumer-1',
            'rating': 5,
            'reviewText': 'Excellent quality mangoes!',
            'photos': [{'url': 'https://s3.amazonaws.com/review1.jpg', 'caption': 'Fresh mangoes'}],
            'helpful': 10,
            'createdAt': '2024-01-18T12:00:00Z'
        },
        {
            'PK': 'PRODUCT#test-product-123',
            'SK': 'REVIEW#review-2',
            'reviewId': 'review-2',
            'consumerId': 'consumer-2',
            'rating': 4,
            'reviewText': 'Good taste, slightly expensive',
            'photos': [],
            'helpful': 5,
            'createdAt': '2024-01-17T09:30:00Z'
        }
    ]


@pytest.fixture
def api_gateway_event():
    """Sample API Gateway event."""
    return {
        'httpMethod': 'GET',
        'path': '/products/test-product-123',
        'pathParameters': {
            'productId': 'test-product-123'
        },
        'headers': {
            'Content-Type': 'application/json'
        },
        'queryStringParameters': None,
        'body': None
    }


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
