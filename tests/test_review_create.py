"""
Unit tests for review submission endpoint (POST /reviews).
Tests Requirements 14.2, 14.3, 14.4.
"""
import json
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime


# Mock the sys.path.append in the handler
import sys
sys.path.insert(0, 'backend')


class TestReviewSubmission:
    """Test suite for review submission endpoint."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.consumer_token_payload = {
            'userId': 'consumer-123',
            'email': 'consumer@example.com',
            'role': 'consumer'
        }
        
        self.farmer_token_payload = {
            'userId': 'farmer-456',
            'email': 'farmer@example.com',
            'role': 'farmer'
        }
        
        self.valid_review_request = {
            'productId': 'product-789',
            'orderId': 'order-abc',
            'rating': 5,
            'reviewText': 'Excellent product! Fresh and high quality.',
            'photoUploadCount': 2
        }
        
        self.order_item = {
            'PK': 'ORDER#order-abc',
            'SK': 'METADATA',
            'orderId': 'order-abc',
            'consumerId': 'consumer-123',
            'productId': 'product-789',
            'farmerId': 'farmer-456',
            'status': 'delivered',
            'totalAmount': 100.0
        }
        
        self.product_item = {
            'PK': 'PRODUCT#product-789',
            'SK': 'METADATA',
            'productId': 'product-789',
            'farmerId': 'farmer-456',
            'name': 'Organic Tomatoes',
            'averageRating': 4.5,
            'totalReviews': 10
        }
    
    def test_review_submission_success(self):
        """Test successful review submission with all valid data."""
        from reviews.create_review import handler
        
        event = {
            'headers': {'Authorization': 'Bearer valid-token'},
            'body': json.dumps(self.valid_review_request)
        }
        
        with patch('reviews.create_review.get_user_from_token') as mock_auth, \
             patch('reviews.create_review.get_item') as mock_get, \
             patch('reviews.create_review.put_item') as mock_put, \
             patch('reviews.create_review.update_item') as mock_update, \
             patch('reviews.create_review.calculate_average_rating') as mock_calc_product, \
             patch('reviews.create_review.calculate_farmer_average_rating') as mock_calc_farmer, \
             patch('reviews.create_review.generate_review_photo_presigned_urls') as mock_urls, \
             patch.dict('os.environ', {'BUCKET_NAME': 'test-bucket'}):
            
            # Setup mocks
            mock_auth.return_value = self.consumer_token_payload
            mock_get.side_effect = [self.order_item, self.product_item]
            mock_calc_product.return_value = {'averageRating': 4.6, 'totalReviews': 11}
            mock_calc_farmer.return_value = {'averageRating': 4.7, 'totalReviews': 25}
            mock_urls.return_value = [
                {'url': 'https://s3.amazonaws.com/presigned1', 'key': 'reviews/xxx/photos/photo-1.jpg', 'expiresIn': 900},
                {'url': 'https://s3.amazonaws.com/presigned2', 'key': 'reviews/xxx/photos/photo-2.jpg', 'expiresIn': 900}
            ]
            
            # Execute
            response = handler(event, None)
            
            # Verify
            assert response['statusCode'] == 201
            body = json.loads(response['body'])
            assert 'reviewId' in body
            assert len(body['photoUploadUrls']) == 2
            assert body['message'] == 'Review submitted successfully'
            
            # Verify review was stored
            mock_put.assert_called_once()
            stored_review = mock_put.call_args[0][0]
            assert stored_review['rating'] == 5
            assert stored_review['reviewText'] == 'Excellent product! Fresh and high quality.'
            assert stored_review['consumerId'] == 'consumer-123'
            assert stored_review['productId'] == 'product-789'
            assert stored_review['farmerId'] == 'farmer-456'
            assert stored_review['orderId'] == 'order-abc'
            assert stored_review['PK'] == 'PRODUCT#product-789'
            assert stored_review['SK'].startswith('REVIEW#')
            assert stored_review['GSI2PK'] == 'FARMER#farmer-456'
            assert stored_review['GSI3PK'] == 'CONSUMER#consumer-123'
            
            # Verify rating aggregation was triggered
            assert mock_update.call_count == 2  # Product and farmer updates
    
    def test_review_submission_without_photos(self):
        """Test review submission without photo uploads."""
        from reviews.create_review import handler
        
        review_request = {
            'productId': 'product-789',
            'orderId': 'order-abc',
            'rating': 4,
            'reviewText': 'Good product, would buy again.',
            'photoUploadCount': 0
        }
        
        event = {
            'headers': {'Authorization': 'Bearer valid-token'},
            'body': json.dumps(review_request)
        }
        
        with patch('reviews.create_review.get_user_from_token') as mock_auth, \
             patch('reviews.create_review.get_item') as mock_get, \
             patch('reviews.create_review.put_item') as mock_put, \
             patch('reviews.create_review.update_item') as mock_update, \
             patch('reviews.create_review.calculate_average_rating') as mock_calc_product, \
             patch('reviews.create_review.calculate_farmer_average_rating') as mock_calc_farmer:
            
            mock_auth.return_value = self.consumer_token_payload
            mock_get.side_effect = [self.order_item, self.product_item]
            mock_calc_product.return_value = {'averageRating': 4.6, 'totalReviews': 11}
            mock_calc_farmer.return_value = {'averageRating': 4.7, 'totalReviews': 25}
            
            response = handler(event, None)
            
            assert response['statusCode'] == 201
            body = json.loads(response['body'])
            assert body['photoUploadUrls'] == []
    
    def test_review_submission_missing_authorization(self):
        """Test review submission without authorization header."""
        from reviews.create_review import handler
        
        event = {
            'headers': {},
            'body': json.dumps(self.valid_review_request)
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 401
        body = json.loads(response['body'])
        assert body['error']['code'] == 'UNAUTHORIZED'
    
    def test_review_submission_invalid_token(self):
        """Test review submission with invalid JWT token."""
        from reviews.create_review import handler
        
        event = {
            'headers': {'Authorization': 'Bearer invalid-token'},
            'body': json.dumps(self.valid_review_request)
        }
        
        with patch('reviews.create_review.get_user_from_token') as mock_auth:
            mock_auth.side_effect = Exception('Invalid token')
            
            response = handler(event, None)
            
            assert response['statusCode'] == 401
            body = json.loads(response['body'])
            assert body['error']['code'] == 'INVALID_TOKEN'
    
    def test_review_submission_farmer_role_forbidden(self):
        """Test that farmers cannot submit reviews."""
        from reviews.create_review import handler
        
        event = {
            'headers': {'Authorization': 'Bearer farmer-token'},
            'body': json.dumps(self.valid_review_request)
        }
        
        with patch('reviews.create_review.get_user_from_token') as mock_auth:
            mock_auth.return_value = self.farmer_token_payload
            
            response = handler(event, None)
            
            assert response['statusCode'] == 403
            body = json.loads(response['body'])
            assert body['error']['code'] == 'FORBIDDEN'
            assert 'Only consumers can submit reviews' in body['error']['message']
    
    def test_review_submission_invalid_json(self):
        """Test review submission with malformed JSON."""
        from reviews.create_review import handler
        
        event = {
            'headers': {'Authorization': 'Bearer valid-token'},
            'body': 'invalid json {'
        }
        
        with patch('reviews.create_review.get_user_from_token') as mock_auth:
            mock_auth.return_value = self.consumer_token_payload
            
            response = handler(event, None)
            
            assert response['statusCode'] == 400
            body = json.loads(response['body'])
            assert body['error']['code'] == 'INVALID_JSON'
    
    def test_review_submission_missing_required_fields(self):
        """Test review submission with missing required fields."""
        from reviews.create_review import handler
        
        invalid_request = {
            'productId': 'product-789',
            # Missing orderId, rating, reviewText
        }
        
        event = {
            'headers': {'Authorization': 'Bearer valid-token'},
            'body': json.dumps(invalid_request)
        }
        
        with patch('reviews.create_review.get_user_from_token') as mock_auth:
            mock_auth.return_value = self.consumer_token_payload
            
            response = handler(event, None)
            
            assert response['statusCode'] == 400
            body = json.loads(response['body'])
            assert body['error']['code'] == 'VALIDATION_ERROR'
    
    def test_review_submission_rating_below_minimum(self):
        """Test review submission with rating below 1."""
        from reviews.create_review import handler
        
        invalid_request = {
            'productId': 'product-789',
            'orderId': 'order-abc',
            'rating': 0,
            'reviewText': 'Terrible product',
            'photoUploadCount': 0
        }
        
        event = {
            'headers': {'Authorization': 'Bearer valid-token'},
            'body': json.dumps(invalid_request)
        }
        
        with patch('reviews.create_review.get_user_from_token') as mock_auth:
            mock_auth.return_value = self.consumer_token_payload
            
            response = handler(event, None)
            
            assert response['statusCode'] == 400
            body = json.loads(response['body'])
            assert body['error']['code'] == 'VALIDATION_ERROR'
            # Validation error should be present (message format may vary)
            assert 'details' in body['error'] or 'message' in body['error']
    
    def test_review_submission_rating_above_maximum(self):
        """Test review submission with rating above 5."""
        from reviews.create_review import handler
        
        invalid_request = {
            'productId': 'product-789',
            'orderId': 'order-abc',
            'rating': 6,
            'reviewText': 'Amazing product',
            'photoUploadCount': 0
        }
        
        event = {
            'headers': {'Authorization': 'Bearer valid-token'},
            'body': json.dumps(invalid_request)
        }
        
        with patch('reviews.create_review.get_user_from_token') as mock_auth:
            mock_auth.return_value = self.consumer_token_payload
            
            response = handler(event, None)
            
            assert response['statusCode'] == 400
            body = json.loads(response['body'])
            assert body['error']['code'] == 'VALIDATION_ERROR'
            # Validation error should be present (message format may vary)
            assert 'details' in body['error'] or 'message' in body['error']
    
    def test_review_submission_rating_not_integer(self):
        """Test review submission with non-integer rating."""
        from reviews.create_review import handler
        
        invalid_request = {
            'productId': 'product-789',
            'orderId': 'order-abc',
            'rating': 4.5,  # Float instead of integer
            'reviewText': 'Good product',
            'photoUploadCount': 0
        }
        
        event = {
            'headers': {'Authorization': 'Bearer valid-token'},
            'body': json.dumps(invalid_request)
        }
        
        with patch('reviews.create_review.get_user_from_token') as mock_auth:
            mock_auth.return_value = self.consumer_token_payload
            
            response = handler(event, None)
            
            assert response['statusCode'] == 400
            body = json.loads(response['body'])
            assert body['error']['code'] == 'VALIDATION_ERROR'
    
    def test_review_submission_order_not_found(self):
        """Test review submission for non-existent order."""
        from reviews.create_review import handler
        
        event = {
            'headers': {'Authorization': 'Bearer valid-token'},
            'body': json.dumps(self.valid_review_request)
        }
        
        with patch('reviews.create_review.get_user_from_token') as mock_auth, \
             patch('reviews.create_review.get_item') as mock_get:
            
            mock_auth.return_value = self.consumer_token_payload
            mock_get.return_value = None  # Order not found
            
            response = handler(event, None)
            
            assert response['statusCode'] == 404
            body = json.loads(response['body'])
            assert body['error']['code'] == 'RESOURCE_NOT_FOUND'
            assert 'Order' in body['error']['message']
    
    def test_review_submission_order_not_owned_by_consumer(self):
        """Test review submission for order owned by different consumer."""
        from reviews.create_review import handler
        
        event = {
            'headers': {'Authorization': 'Bearer valid-token'},
            'body': json.dumps(self.valid_review_request)
        }
        
        other_consumer_order = self.order_item.copy()
        other_consumer_order['consumerId'] = 'different-consumer-999'
        
        with patch('reviews.create_review.get_user_from_token') as mock_auth, \
             patch('reviews.create_review.get_item') as mock_get:
            
            mock_auth.return_value = self.consumer_token_payload
            mock_get.return_value = other_consumer_order
            
            response = handler(event, None)
            
            assert response['statusCode'] == 403
            body = json.loads(response['body'])
            assert body['error']['code'] == 'FORBIDDEN'
            assert 'purchased' in body['error']['message'].lower()
    
    def test_review_submission_product_not_in_order(self):
        """Test review submission for product not in the order."""
        from reviews.create_review import handler
        
        review_request = self.valid_review_request.copy()
        review_request['productId'] = 'different-product-999'
        
        event = {
            'headers': {'Authorization': 'Bearer valid-token'},
            'body': json.dumps(review_request)
        }
        
        with patch('reviews.create_review.get_user_from_token') as mock_auth, \
             patch('reviews.create_review.get_item') as mock_get:
            
            mock_auth.return_value = self.consumer_token_payload
            mock_get.return_value = self.order_item
            
            response = handler(event, None)
            
            assert response['statusCode'] == 422
            body = json.loads(response['body'])
            assert body['error']['code'] == 'UNPROCESSABLE_ENTITY'
            assert 'does not contain' in body['error']['message']
    
    def test_review_submission_product_not_found(self):
        """Test review submission for non-existent product."""
        from reviews.create_review import handler
        
        event = {
            'headers': {'Authorization': 'Bearer valid-token'},
            'body': json.dumps(self.valid_review_request)
        }
        
        with patch('reviews.create_review.get_user_from_token') as mock_auth, \
             patch('reviews.create_review.get_item') as mock_get:
            
            mock_auth.return_value = self.consumer_token_payload
            mock_get.side_effect = [self.order_item, None]  # Order found, product not found
            
            response = handler(event, None)
            
            assert response['statusCode'] == 404
            body = json.loads(response['body'])
            assert body['error']['code'] == 'RESOURCE_NOT_FOUND'
            assert 'Product' in body['error']['message']
    
    def test_review_submission_database_error(self):
        """Test review submission when database is unavailable."""
        from reviews.create_review import handler
        
        event = {
            'headers': {'Authorization': 'Bearer valid-token'},
            'body': json.dumps(self.valid_review_request)
        }
        
        with patch('reviews.create_review.get_user_from_token') as mock_auth, \
             patch('reviews.create_review.get_item') as mock_get:
            
            mock_auth.return_value = self.consumer_token_payload
            mock_get.side_effect = Exception('DynamoDB connection error')
            
            response = handler(event, None)
            
            assert response['statusCode'] == 503
            body = json.loads(response['body'])
            assert body['error']['code'] == 'SERVICE_UNAVAILABLE'
    
    def test_review_submission_s3_presigned_url_failure(self):
        """Test review submission when S3 presigned URL generation fails."""
        from reviews.create_review import handler
        
        event = {
            'headers': {'Authorization': 'Bearer valid-token'},
            'body': json.dumps(self.valid_review_request)
        }
        
        with patch('reviews.create_review.get_user_from_token') as mock_auth, \
             patch('reviews.create_review.get_item') as mock_get, \
             patch('reviews.create_review.put_item') as mock_put, \
             patch('reviews.create_review.update_item') as mock_update, \
             patch('reviews.create_review.calculate_average_rating') as mock_calc_product, \
             patch('reviews.create_review.calculate_farmer_average_rating') as mock_calc_farmer, \
             patch('reviews.create_review.generate_review_photo_presigned_urls') as mock_urls, \
             patch.dict('os.environ', {'BUCKET_NAME': 'test-bucket'}):
            
            mock_auth.return_value = self.consumer_token_payload
            mock_get.side_effect = [self.order_item, self.product_item]
            mock_calc_product.return_value = {'averageRating': 4.6, 'totalReviews': 11}
            mock_calc_farmer.return_value = {'averageRating': 4.7, 'totalReviews': 25}
            
            from backend.shared.exceptions import ServiceUnavailableError
            mock_urls.side_effect = ServiceUnavailableError('S3', 'Failed to generate URLs')
            
            response = handler(event, None)
            
            # Review should still be created successfully
            assert response['statusCode'] == 201
            body = json.loads(response['body'])
            assert 'reviewId' in body
            # Photo URLs should be empty due to error
            assert body['photoUploadUrls'] == []
    
    def test_review_submission_rating_aggregation_failure(self):
        """Test review submission when rating aggregation fails."""
        from reviews.create_review import handler
        
        event = {
            'headers': {'Authorization': 'Bearer valid-token'},
            'body': json.dumps(self.valid_review_request)
        }
        
        with patch('reviews.create_review.get_user_from_token') as mock_auth, \
             patch('reviews.create_review.get_item') as mock_get, \
             patch('reviews.create_review.put_item') as mock_put, \
             patch('reviews.create_review.update_item') as mock_update, \
             patch('reviews.create_review.calculate_average_rating') as mock_calc_product, \
             patch('reviews.create_review.calculate_farmer_average_rating') as mock_calc_farmer, \
             patch.dict('os.environ', {'BUCKET_NAME': 'test-bucket'}):
            
            mock_auth.return_value = self.consumer_token_payload
            mock_get.side_effect = [self.order_item, self.product_item]
            mock_calc_product.side_effect = Exception('Calculation error')
            mock_calc_farmer.side_effect = Exception('Calculation error')
            
            response = handler(event, None)
            
            # Review should still be created successfully
            assert response['statusCode'] == 201
            body = json.loads(response['body'])
            assert 'reviewId' in body
    
    def test_review_submission_all_rating_values(self):
        """Test review submission with all valid rating values (1-5)."""
        from reviews.create_review import handler
        
        for rating in [1, 2, 3, 4, 5]:
            review_request = self.valid_review_request.copy()
            review_request['rating'] = rating
            
            event = {
                'headers': {'Authorization': 'Bearer valid-token'},
                'body': json.dumps(review_request)
            }
            
            with patch('reviews.create_review.get_user_from_token') as mock_auth, \
                 patch('reviews.create_review.get_item') as mock_get, \
                 patch('reviews.create_review.put_item') as mock_put, \
                 patch('reviews.create_review.update_item') as mock_update, \
                 patch('reviews.create_review.calculate_average_rating') as mock_calc_product, \
                 patch('reviews.create_review.calculate_farmer_average_rating') as mock_calc_farmer:
                
                mock_auth.return_value = self.consumer_token_payload
                mock_get.side_effect = [self.order_item, self.product_item]
                mock_calc_product.return_value = {'averageRating': 4.0, 'totalReviews': 10}
                mock_calc_farmer.return_value = {'averageRating': 4.0, 'totalReviews': 20}
                
                response = handler(event, None)
                
                assert response['statusCode'] == 201
                body = json.loads(response['body'])
                assert 'reviewId' in body
                
                # Verify correct rating was stored
                stored_review = mock_put.call_args[0][0]
                assert stored_review['rating'] == rating
    
    def test_review_submission_review_text_minimum_length(self):
        """Test review submission with minimum valid review text length."""
        from reviews.create_review import handler
        
        review_request = self.valid_review_request.copy()
        review_request['reviewText'] = 'Good item!'  # 10 characters minimum
        
        event = {
            'headers': {'Authorization': 'Bearer valid-token'},
            'body': json.dumps(review_request)
        }
        
        with patch('reviews.create_review.get_user_from_token') as mock_auth, \
             patch('reviews.create_review.get_item') as mock_get, \
             patch('reviews.create_review.put_item') as mock_put, \
             patch('reviews.create_review.update_item') as mock_update, \
             patch('reviews.create_review.calculate_average_rating') as mock_calc_product, \
             patch('reviews.create_review.calculate_farmer_average_rating') as mock_calc_farmer:
            
            mock_auth.return_value = self.consumer_token_payload
            mock_get.side_effect = [self.order_item, self.product_item]
            mock_calc_product.return_value = {'averageRating': 4.0, 'totalReviews': 10}
            mock_calc_farmer.return_value = {'averageRating': 4.0, 'totalReviews': 20}
            
            response = handler(event, None)
            
            assert response['statusCode'] == 201
    
    def test_review_submission_gsi_keys_set_correctly(self):
        """Test that GSI keys are set correctly for querying."""
        from reviews.create_review import handler
        
        event = {
            'headers': {'Authorization': 'Bearer valid-token'},
            'body': json.dumps(self.valid_review_request)
        }
        
        with patch('reviews.create_review.get_user_from_token') as mock_auth, \
             patch('reviews.create_review.get_item') as mock_get, \
             patch('reviews.create_review.put_item') as mock_put, \
             patch('reviews.create_review.update_item') as mock_update, \
             patch('reviews.create_review.calculate_average_rating') as mock_calc_product, \
             patch('reviews.create_review.calculate_farmer_average_rating') as mock_calc_farmer:
            
            mock_auth.return_value = self.consumer_token_payload
            mock_get.side_effect = [self.order_item, self.product_item]
            mock_calc_product.return_value = {'averageRating': 4.6, 'totalReviews': 11}
            mock_calc_farmer.return_value = {'averageRating': 4.7, 'totalReviews': 25}
            
            response = handler(event, None)
            
            assert response['statusCode'] == 201
            
            # Verify GSI keys
            stored_review = mock_put.call_args[0][0]
            assert stored_review['GSI2PK'] == 'FARMER#farmer-456'
            assert stored_review['GSI2SK'].startswith('REVIEW#')
            assert stored_review['GSI3PK'] == 'CONSUMER#consumer-123'
            assert stored_review['GSI3SK'].startswith('REVIEW#')


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
