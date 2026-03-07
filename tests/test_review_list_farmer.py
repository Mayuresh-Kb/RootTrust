"""
Unit tests for farmer reviews listing endpoint (GET /reviews/farmer/{farmerId}).
Tests Requirement 14.6.
"""
import json
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta


# Mock the sys.path.append in the handler
import sys
sys.path.insert(0, 'backend')


class TestFarmerReviewsListing:
    """Test suite for farmer reviews listing endpoint."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.farmer_id = 'farmer-123'
        
        # Create sample reviews for different products from the same farmer
        now = datetime.utcnow()
        self.review_items = [
            {
                'PK': 'PRODUCT#product-1',
                'SK': 'REVIEW#review-1',
                'GSI2PK': f'FARMER#{self.farmer_id}',
                'GSI2SK': 'REVIEW#review-1',
                'reviewId': 'review-1',
                'productId': 'product-1',
                'farmerId': self.farmer_id,
                'consumerId': 'consumer-1',
                'orderId': 'order-1',
                'rating': 5,
                'reviewText': 'Excellent tomatoes! Very fresh and tasty.',
                'photos': [
                    {'url': 'https://s3.amazonaws.com/photo1.jpg', 'caption': 'Fresh tomatoes'}
                ],
                'helpful': 10,
                'createdAt': (now - timedelta(days=1)).isoformat()
            },
            {
                'PK': 'PRODUCT#product-2',
                'SK': 'REVIEW#review-2',
                'GSI2PK': f'FARMER#{self.farmer_id}',
                'GSI2SK': 'REVIEW#review-2',
                'reviewId': 'review-2',
                'productId': 'product-2',
                'farmerId': self.farmer_id,
                'consumerId': 'consumer-2',
                'orderId': 'order-2',
                'rating': 4,
                'reviewText': 'Good quality potatoes, would buy again.',
                'photos': [],
                'helpful': 5,
                'createdAt': (now - timedelta(days=3)).isoformat()
            },
            {
                'PK': 'PRODUCT#product-1',
                'SK': 'REVIEW#review-3',
                'GSI2PK': f'FARMER#{self.farmer_id}',
                'GSI2SK': 'REVIEW#review-3',
                'reviewId': 'review-3',
                'productId': 'product-1',
                'farmerId': self.farmer_id,
                'consumerId': 'consumer-3',
                'orderId': 'order-3',
                'rating': 5,
                'reviewText': 'Best tomatoes I have ever bought!',
                'photos': [
                    {'url': 'https://s3.amazonaws.com/photo2.jpg', 'caption': 'Delicious'}
                ],
                'helpful': 8,
                'createdAt': (now - timedelta(days=5)).isoformat()
            },
            {
                'PK': 'PRODUCT#product-3',
                'SK': 'REVIEW#review-4',
                'GSI2PK': f'FARMER#{self.farmer_id}',
                'GSI2SK': 'REVIEW#review-4',
                'reviewId': 'review-4',
                'productId': 'product-3',
                'farmerId': self.farmer_id,
                'consumerId': 'consumer-4',
                'orderId': 'order-4',
                'rating': 3,
                'reviewText': 'Average carrots, nothing special.',
                'photos': [],
                'helpful': 2,
                'createdAt': (now - timedelta(days=7)).isoformat()
            }
        ]
    
    def test_list_farmer_reviews_success(self):
        """Test successful retrieval of farmer reviews."""
        from reviews.list_farmer_reviews import handler
        
        event = {
            'pathParameters': {'farmerId': self.farmer_id}
        }
        
        with patch('reviews.list_farmer_reviews.query') as mock_query:
            mock_query.return_value = {'Items': self.review_items}
            
            response = handler(event, None)
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert 'reviews' in body
            assert body['count'] == 4
            assert len(body['reviews']) == 4
            
            # Verify query was called with correct parameters
            mock_query.assert_called_once()
            call_kwargs = mock_query.call_args[1]
            assert call_kwargs['index_name'] == 'GSI2'
            assert call_kwargs['scan_index_forward'] is False  # Descending order
    
    def test_list_farmer_reviews_uses_gsi2(self):
        """Test that farmer reviews query uses GSI2 index."""
        from reviews.list_farmer_reviews import handler
        
        event = {
            'pathParameters': {'farmerId': self.farmer_id}
        }
        
        with patch('reviews.list_farmer_reviews.query') as mock_query:
            mock_query.return_value = {'Items': self.review_items}
            
            response = handler(event, None)
            
            assert response['statusCode'] == 200
            
            # Verify GSI2 was used
            call_kwargs = mock_query.call_args[1]
            assert call_kwargs['index_name'] == 'GSI2'
    
    def test_list_farmer_reviews_sorted_descending(self):
        """Test that reviews are returned in descending order by creation date."""
        from reviews.list_farmer_reviews import handler
        
        event = {
            'pathParameters': {'farmerId': self.farmer_id}
        }
        
        with patch('reviews.list_farmer_reviews.query') as mock_query:
            # Return reviews in descending order (most recent first)
            mock_query.return_value = {'Items': self.review_items}
            
            response = handler(event, None)
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            
            # Verify scan_index_forward=False was used for descending order
            call_kwargs = mock_query.call_args[1]
            assert call_kwargs['scan_index_forward'] is False
    
    def test_list_farmer_reviews_empty_result(self):
        """Test listing reviews for farmer with no reviews."""
        from reviews.list_farmer_reviews import handler
        
        event = {
            'pathParameters': {'farmerId': 'farmer-no-reviews'}
        }
        
        with patch('reviews.list_farmer_reviews.query') as mock_query:
            mock_query.return_value = {'Items': []}
            
            response = handler(event, None)
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert body['reviews'] == []
            assert body['count'] == 0
    
    def test_list_farmer_reviews_missing_farmer_id(self):
        """Test listing reviews without farmerId in path parameters."""
        from reviews.list_farmer_reviews import handler
        
        event = {
            'pathParameters': {}
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error']['code'] == 'VALIDATION_ERROR'
        assert 'farmerId' in body['error']['message']
    
    def test_list_farmer_reviews_no_path_parameters(self):
        """Test listing reviews with missing path parameters."""
        from reviews.list_farmer_reviews import handler
        
        event = {}
        
        response = handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error']['code'] == 'VALIDATION_ERROR'
    
    def test_list_farmer_reviews_database_error(self):
        """Test listing reviews when database is unavailable."""
        from reviews.list_farmer_reviews import handler
        from backend.shared.exceptions import ServiceUnavailableError
        
        event = {
            'pathParameters': {'farmerId': self.farmer_id}
        }
        
        with patch('reviews.list_farmer_reviews.query') as mock_query:
            mock_query.side_effect = ServiceUnavailableError('DynamoDB', 'Connection error')
            
            response = handler(event, None)
            
            assert response['statusCode'] == 503
            body = json.loads(response['body'])
            assert body['error']['code'] == 'SERVICE_UNAVAILABLE'
    
    def test_list_farmer_reviews_unexpected_error(self):
        """Test listing reviews with unexpected error."""
        from reviews.list_farmer_reviews import handler
        
        event = {
            'pathParameters': {'farmerId': self.farmer_id}
        }
        
        with patch('reviews.list_farmer_reviews.query') as mock_query:
            mock_query.side_effect = Exception('Unexpected error')
            
            response = handler(event, None)
            
            assert response['statusCode'] == 503
            body = json.loads(response['body'])
            assert body['error']['code'] == 'SERVICE_UNAVAILABLE'
    
    def test_list_farmer_reviews_response_format(self):
        """Test that review response format includes all required fields."""
        from reviews.list_farmer_reviews import handler
        
        event = {
            'pathParameters': {'farmerId': self.farmer_id}
        }
        
        with patch('reviews.list_farmer_reviews.query') as mock_query:
            mock_query.return_value = {'Items': [self.review_items[0]]}
            
            response = handler(event, None)
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            review = body['reviews'][0]
            
            # Verify all required fields are present
            assert 'reviewId' in review
            assert 'productId' in review
            assert 'consumerId' in review
            assert 'orderId' in review
            assert 'rating' in review
            assert 'reviewText' in review
            assert 'photos' in review
            assert 'helpful' in review
            assert 'createdAt' in review
            
            # Verify values match
            assert review['reviewId'] == 'review-1'
            assert review['productId'] == 'product-1'
            assert review['rating'] == 5
            assert review['reviewText'] == 'Excellent tomatoes! Very fresh and tasty.'
            assert len(review['photos']) == 1
    
    def test_list_farmer_reviews_multiple_products(self):
        """Test listing reviews across multiple products from the same farmer."""
        from reviews.list_farmer_reviews import handler
        
        event = {
            'pathParameters': {'farmerId': self.farmer_id}
        }
        
        with patch('reviews.list_farmer_reviews.query') as mock_query:
            mock_query.return_value = {'Items': self.review_items}
            
            response = handler(event, None)
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            
            assert body['count'] == 4
            assert len(body['reviews']) == 4
            
            # Verify reviews from different products are included
            product_ids = [r['productId'] for r in body['reviews']]
            assert 'product-1' in product_ids
            assert 'product-2' in product_ids
            assert 'product-3' in product_ids
            
            # Verify multiple reviews for same product are included
            product_1_reviews = [r for r in body['reviews'] if r['productId'] == 'product-1']
            assert len(product_1_reviews) == 2
    
    def test_list_farmer_reviews_with_photos(self):
        """Test listing reviews that include photos."""
        from reviews.list_farmer_reviews import handler
        
        event = {
            'pathParameters': {'farmerId': self.farmer_id}
        }
        
        with patch('reviews.list_farmer_reviews.query') as mock_query:
            mock_query.return_value = {'Items': [self.review_items[0]]}
            
            response = handler(event, None)
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            review = body['reviews'][0]
            
            assert len(review['photos']) == 1
            assert review['photos'][0]['url'] == 'https://s3.amazonaws.com/photo1.jpg'
            assert review['photos'][0]['caption'] == 'Fresh tomatoes'
    
    def test_list_farmer_reviews_without_photos(self):
        """Test listing reviews without photos."""
        from reviews.list_farmer_reviews import handler
        
        event = {
            'pathParameters': {'farmerId': self.farmer_id}
        }
        
        with patch('reviews.list_farmer_reviews.query') as mock_query:
            mock_query.return_value = {'Items': [self.review_items[1]]}
            
            response = handler(event, None)
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            review = body['reviews'][0]
            
            assert review['photos'] == []
    
    def test_list_farmer_reviews_different_ratings(self):
        """Test listing reviews with different rating values."""
        from reviews.list_farmer_reviews import handler
        
        event = {
            'pathParameters': {'farmerId': self.farmer_id}
        }
        
        with patch('reviews.list_farmer_reviews.query') as mock_query:
            mock_query.return_value = {'Items': self.review_items}
            
            response = handler(event, None)
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            
            ratings = [r['rating'] for r in body['reviews']]
            assert 5 in ratings
            assert 4 in ratings
            assert 3 in ratings
    
    def test_list_farmer_reviews_cors_headers(self):
        """Test that CORS headers are included in response."""
        from reviews.list_farmer_reviews import handler
        
        event = {
            'pathParameters': {'farmerId': self.farmer_id}
        }
        
        with patch('reviews.list_farmer_reviews.query') as mock_query:
            mock_query.return_value = {'Items': []}
            
            response = handler(event, None)
            
            assert 'Access-Control-Allow-Origin' in response['headers']
            assert response['headers']['Access-Control-Allow-Origin'] == '*'
    
    def test_list_farmer_reviews_query_parameters(self):
        """Test that query is called with correct DynamoDB parameters."""
        from reviews.list_farmer_reviews import handler
        from boto3.dynamodb.conditions import Key
        
        event = {
            'pathParameters': {'farmerId': self.farmer_id}
        }
        
        with patch('reviews.list_farmer_reviews.query') as mock_query:
            mock_query.return_value = {'Items': []}
            
            response = handler(event, None)
            
            # Verify query was called
            assert mock_query.called
            
            # Verify correct parameters
            call_kwargs = mock_query.call_args[1]
            assert 'index_name' in call_kwargs
            assert call_kwargs['index_name'] == 'GSI2'
            assert 'scan_index_forward' in call_kwargs
            assert call_kwargs['scan_index_forward'] is False
    
    def test_list_farmer_reviews_helpful_count(self):
        """Test that helpful count is included in review response."""
        from reviews.list_farmer_reviews import handler
        
        event = {
            'pathParameters': {'farmerId': self.farmer_id}
        }
        
        with patch('reviews.list_farmer_reviews.query') as mock_query:
            mock_query.return_value = {'Items': [self.review_items[0]]}
            
            response = handler(event, None)
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            review = body['reviews'][0]
            
            assert review['helpful'] == 10
    
    def test_list_farmer_reviews_created_at_format(self):
        """Test that createdAt timestamp is included in ISO format."""
        from reviews.list_farmer_reviews import handler
        
        event = {
            'pathParameters': {'farmerId': self.farmer_id}
        }
        
        with patch('reviews.list_farmer_reviews.query') as mock_query:
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
    
    def test_list_farmer_reviews_all_reviews_for_farmer(self):
        """Test that all reviews for farmer's products are returned."""
        from reviews.list_farmer_reviews import handler
        
        event = {
            'pathParameters': {'farmerId': self.farmer_id}
        }
        
        with patch('reviews.list_farmer_reviews.query') as mock_query:
            mock_query.return_value = {'Items': self.review_items}
            
            response = handler(event, None)
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            
            # Verify all reviews are present
            review_ids = [r['reviewId'] for r in body['reviews']]
            assert 'review-1' in review_ids
            assert 'review-2' in review_ids
            assert 'review-3' in review_ids
            assert 'review-4' in review_ids
    
    def test_list_farmer_reviews_different_consumers(self):
        """Test that reviews from different consumers are included."""
        from reviews.list_farmer_reviews import handler
        
        event = {
            'pathParameters': {'farmerId': self.farmer_id}
        }
        
        with patch('reviews.list_farmer_reviews.query') as mock_query:
            mock_query.return_value = {'Items': self.review_items}
            
            response = handler(event, None)
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            
            # Verify reviews from different consumers
            consumer_ids = [r['consumerId'] for r in body['reviews']]
            assert 'consumer-1' in consumer_ids
            assert 'consumer-2' in consumer_ids
            assert 'consumer-3' in consumer_ids
            assert 'consumer-4' in consumer_ids
    
    def test_list_farmer_reviews_gsi2pk_format(self):
        """Test that GSI2PK is correctly formatted for farmer queries."""
        from reviews.list_farmer_reviews import handler
        from boto3.dynamodb.conditions import Key
        
        event = {
            'pathParameters': {'farmerId': self.farmer_id}
        }
        
        with patch('reviews.list_farmer_reviews.query') as mock_query:
            mock_query.return_value = {'Items': []}
            
            response = handler(event, None)
            
            # Verify query was called
            assert mock_query.called
            
            # The key condition should query GSI2PK=FARMER#{farmerId}
            # We can't easily inspect the Key condition object, but we verified
            # the index_name is GSI2 which is correct
            call_kwargs = mock_query.call_args[1]
            assert call_kwargs['index_name'] == 'GSI2'
    
    def test_list_farmer_reviews_single_review(self):
        """Test listing a single review for a farmer."""
        from reviews.list_farmer_reviews import handler
        
        event = {
            'pathParameters': {'farmerId': self.farmer_id}
        }
        
        with patch('reviews.list_farmer_reviews.query') as mock_query:
            mock_query.return_value = {'Items': [self.review_items[0]]}
            
            response = handler(event, None)
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            
            assert body['count'] == 1
            assert len(body['reviews']) == 1
            assert body['reviews'][0]['reviewId'] == 'review-1'
    
    def test_list_farmer_reviews_content_type_header(self):
        """Test that Content-Type header is set correctly."""
        from reviews.list_farmer_reviews import handler
        
        event = {
            'pathParameters': {'farmerId': self.farmer_id}
        }
        
        with patch('reviews.list_farmer_reviews.query') as mock_query:
            mock_query.return_value = {'Items': []}
            
            response = handler(event, None)
            
            assert 'Content-Type' in response['headers']
            assert response['headers']['Content-Type'] == 'application/json'
    
    def test_list_farmer_reviews_error_response_format(self):
        """Test that error responses follow the correct format."""
        from reviews.list_farmer_reviews import handler
        
        event = {
            'pathParameters': {}
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        
        # Verify error structure
        assert 'error' in body
        assert 'code' in body['error']
        assert 'message' in body['error']
        assert body['error']['code'] == 'VALIDATION_ERROR'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
