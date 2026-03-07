"""
Unit tests for product reviews listing endpoint (GET /reviews/product/{productId}).
Tests Requirement 14.7.
"""
import json
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta


# Mock the sys.path.append in the handler
import sys
sys.path.insert(0, 'backend')


class TestProductReviewsListing:
    """Test suite for product reviews listing endpoint."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.product_id = 'product-123'
        
        # Create sample reviews with different timestamps
        now = datetime.utcnow()
        self.review_items = [
            {
                'PK': f'PRODUCT#{self.product_id}',
                'SK': 'REVIEW#review-1',
                'reviewId': 'review-1',
                'productId': self.product_id,
                'consumerId': 'consumer-1',
                'farmerId': 'farmer-1',
                'orderId': 'order-1',
                'rating': 5,
                'reviewText': 'Excellent product! Very fresh.',
                'photos': [
                    {'url': 'https://s3.amazonaws.com/photo1.jpg', 'caption': 'Fresh tomatoes'}
                ],
                'helpful': 10,
                'createdAt': (now - timedelta(days=1)).isoformat()
            },
            {
                'PK': f'PRODUCT#{self.product_id}',
                'SK': 'REVIEW#review-2',
                'reviewId': 'review-2',
                'productId': self.product_id,
                'consumerId': 'consumer-2',
                'farmerId': 'farmer-1',
                'orderId': 'order-2',
                'rating': 4,
                'reviewText': 'Good quality, would buy again.',
                'photos': [],
                'helpful': 5,
                'createdAt': (now - timedelta(days=3)).isoformat()
            },
            {
                'PK': f'PRODUCT#{self.product_id}',
                'SK': 'REVIEW#review-3',
                'reviewId': 'review-3',
                'productId': self.product_id,
                'consumerId': 'consumer-3',
                'farmerId': 'farmer-1',
                'orderId': 'order-3',
                'rating': 3,
                'reviewText': 'Average product, nothing special.',
                'photos': [
                    {'url': 'https://s3.amazonaws.com/photo2.jpg', 'caption': 'Product photo'}
                ],
                'helpful': 2,
                'createdAt': (now - timedelta(days=7)).isoformat()
            }
        ]
    
    def test_list_product_reviews_success(self):
        """Test successful retrieval of product reviews."""
        from reviews.list_product_reviews import handler
        
        event = {
            'pathParameters': {'productId': self.product_id}
        }
        
        with patch('reviews.list_product_reviews.query') as mock_query:
            mock_query.return_value = {'Items': self.review_items}
            
            response = handler(event, None)
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert 'reviews' in body
            assert body['count'] == 3
            assert len(body['reviews']) == 3
            
            # Verify query was called with correct parameters
            mock_query.assert_called_once()
            call_kwargs = mock_query.call_args[1]
            assert call_kwargs['scan_index_forward'] is False  # Descending order
    
    def test_list_product_reviews_sorted_descending(self):
        """Test that reviews are returned in descending order by creation date."""
        from reviews.list_product_reviews import handler
        
        event = {
            'pathParameters': {'productId': self.product_id}
        }
        
        with patch('reviews.list_product_reviews.query') as mock_query:
            # Return reviews in descending order (most recent first)
            mock_query.return_value = {'Items': self.review_items}
            
            response = handler(event, None)
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            
            # Verify scan_index_forward=False was used for descending order
            call_kwargs = mock_query.call_args[1]
            assert call_kwargs['scan_index_forward'] is False
    
    def test_list_product_reviews_empty_result(self):
        """Test listing reviews for product with no reviews."""
        from reviews.list_product_reviews import handler
        
        event = {
            'pathParameters': {'productId': 'product-no-reviews'}
        }
        
        with patch('reviews.list_product_reviews.query') as mock_query:
            mock_query.return_value = {'Items': []}
            
            response = handler(event, None)
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert body['reviews'] == []
            assert body['count'] == 0
    
    def test_list_product_reviews_missing_product_id(self):
        """Test listing reviews without productId in path parameters."""
        from reviews.list_product_reviews import handler
        
        event = {
            'pathParameters': {}
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error']['code'] == 'VALIDATION_ERROR'
        assert 'productId' in body['error']['message']
    
    def test_list_product_reviews_no_path_parameters(self):
        """Test listing reviews with missing path parameters."""
        from reviews.list_product_reviews import handler
        
        event = {}
        
        response = handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error']['code'] == 'VALIDATION_ERROR'
    
    def test_list_product_reviews_database_error(self):
        """Test listing reviews when database is unavailable."""
        from reviews.list_product_reviews import handler
        from backend.shared.exceptions import ServiceUnavailableError
        
        event = {
            'pathParameters': {'productId': self.product_id}
        }
        
        with patch('reviews.list_product_reviews.query') as mock_query:
            mock_query.side_effect = ServiceUnavailableError('DynamoDB', 'Connection error')
            
            response = handler(event, None)
            
            assert response['statusCode'] == 503
            body = json.loads(response['body'])
            assert body['error']['code'] == 'SERVICE_UNAVAILABLE'
    
    def test_list_product_reviews_unexpected_error(self):
        """Test listing reviews with unexpected error."""
        from reviews.list_product_reviews import handler
        
        event = {
            'pathParameters': {'productId': self.product_id}
        }
        
        with patch('reviews.list_product_reviews.query') as mock_query:
            mock_query.side_effect = Exception('Unexpected error')
            
            response = handler(event, None)
            
            assert response['statusCode'] == 503
            body = json.loads(response['body'])
            assert body['error']['code'] == 'SERVICE_UNAVAILABLE'
    
    def test_list_product_reviews_response_format(self):
        """Test that review response format includes all required fields."""
        from reviews.list_product_reviews import handler
        
        event = {
            'pathParameters': {'productId': self.product_id}
        }
        
        with patch('reviews.list_product_reviews.query') as mock_query:
            mock_query.return_value = {'Items': [self.review_items[0]]}
            
            response = handler(event, None)
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            review = body['reviews'][0]
            
            # Verify all required fields are present
            assert 'reviewId' in review
            assert 'consumerId' in review
            assert 'orderId' in review
            assert 'rating' in review
            assert 'reviewText' in review
            assert 'photos' in review
            assert 'helpful' in review
            assert 'createdAt' in review
            
            # Verify values match
            assert review['reviewId'] == 'review-1'
            assert review['rating'] == 5
            assert review['reviewText'] == 'Excellent product! Very fresh.'
            assert len(review['photos']) == 1
    
    def test_list_product_reviews_with_photos(self):
        """Test listing reviews that include photos."""
        from reviews.list_product_reviews import handler
        
        event = {
            'pathParameters': {'productId': self.product_id}
        }
        
        with patch('reviews.list_product_reviews.query') as mock_query:
            mock_query.return_value = {'Items': [self.review_items[0]]}
            
            response = handler(event, None)
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            review = body['reviews'][0]
            
            assert len(review['photos']) == 1
            assert review['photos'][0]['url'] == 'https://s3.amazonaws.com/photo1.jpg'
            assert review['photos'][0]['caption'] == 'Fresh tomatoes'
    
    def test_list_product_reviews_without_photos(self):
        """Test listing reviews without photos."""
        from reviews.list_product_reviews import handler
        
        event = {
            'pathParameters': {'productId': self.product_id}
        }
        
        with patch('reviews.list_product_reviews.query') as mock_query:
            mock_query.return_value = {'Items': [self.review_items[1]]}
            
            response = handler(event, None)
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            review = body['reviews'][0]
            
            assert review['photos'] == []
    
    def test_list_product_reviews_multiple_reviews(self):
        """Test listing multiple reviews for a product."""
        from reviews.list_product_reviews import handler
        
        event = {
            'pathParameters': {'productId': self.product_id}
        }
        
        with patch('reviews.list_product_reviews.query') as mock_query:
            mock_query.return_value = {'Items': self.review_items}
            
            response = handler(event, None)
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            
            assert body['count'] == 3
            assert len(body['reviews']) == 3
            
            # Verify all reviews are present
            review_ids = [r['reviewId'] for r in body['reviews']]
            assert 'review-1' in review_ids
            assert 'review-2' in review_ids
            assert 'review-3' in review_ids
    
    def test_list_product_reviews_different_ratings(self):
        """Test listing reviews with different rating values."""
        from reviews.list_product_reviews import handler
        
        event = {
            'pathParameters': {'productId': self.product_id}
        }
        
        with patch('reviews.list_product_reviews.query') as mock_query:
            mock_query.return_value = {'Items': self.review_items}
            
            response = handler(event, None)
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            
            ratings = [r['rating'] for r in body['reviews']]
            assert 5 in ratings
            assert 4 in ratings
            assert 3 in ratings
    
    def test_list_product_reviews_cors_headers(self):
        """Test that CORS headers are included in response."""
        from reviews.list_product_reviews import handler
        
        event = {
            'pathParameters': {'productId': self.product_id}
        }
        
        with patch('reviews.list_product_reviews.query') as mock_query:
            mock_query.return_value = {'Items': []}
            
            response = handler(event, None)
            
            assert 'Access-Control-Allow-Origin' in response['headers']
            assert response['headers']['Access-Control-Allow-Origin'] == '*'
    
    def test_list_product_reviews_query_parameters(self):
        """Test that query is called with correct DynamoDB parameters."""
        from reviews.list_product_reviews import handler
        from boto3.dynamodb.conditions import Key
        
        event = {
            'pathParameters': {'productId': self.product_id}
        }
        
        with patch('reviews.list_product_reviews.query') as mock_query:
            mock_query.return_value = {'Items': []}
            
            response = handler(event, None)
            
            # Verify query was called
            assert mock_query.called
            
            # Verify scan_index_forward is False for descending order
            call_kwargs = mock_query.call_args[1]
            assert 'scan_index_forward' in call_kwargs
            assert call_kwargs['scan_index_forward'] is False
    
    def test_list_product_reviews_helpful_count(self):
        """Test that helpful count is included in review response."""
        from reviews.list_product_reviews import handler
        
        event = {
            'pathParameters': {'productId': self.product_id}
        }
        
        with patch('reviews.list_product_reviews.query') as mock_query:
            mock_query.return_value = {'Items': [self.review_items[0]]}
            
            response = handler(event, None)
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            review = body['reviews'][0]
            
            assert review['helpful'] == 10
    
    def test_list_product_reviews_created_at_format(self):
        """Test that createdAt timestamp is included in ISO format."""
        from reviews.list_product_reviews import handler
        
        event = {
            'pathParameters': {'productId': self.product_id}
        }
        
        with patch('reviews.list_product_reviews.query') as mock_query:
            mock_query.return_value = {'Items': [self.review_items[0]]}
            
            response = handler(event, None)
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            review = body['reviews'][0]
            
            assert 'createdAt' in review
            # Verify it's a valid ISO timestamp string
            assert isinstance(review['createdAt'], str)
            # Should be parseable as ISO format
            datetime.fromisoformat(review['createdAt'].replace('Z', '+00:00'))


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
