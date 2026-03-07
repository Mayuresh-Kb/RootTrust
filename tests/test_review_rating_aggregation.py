"""
Unit tests for rating aggregation functions.
Tests Requirements 14.5, 14.6.

These tests verify that:
- Product average ratings are calculated correctly from all reviews
- Farmer average ratings are calculated correctly from all their products' reviews
- Rating aggregation handles edge cases (no reviews, single review, multiple reviews)
"""
import pytest
from unittest.mock import patch, MagicMock
from decimal import Decimal


# Mock the sys.path.append in the handler
import sys
sys.path.insert(0, 'backend')


class TestProductRatingAggregation:
    """Test suite for product rating aggregation (Requirement 14.5)."""
    
    def test_calculate_average_rating_no_reviews(self):
        """Test product rating calculation when no reviews exist."""
        from reviews.create_review import calculate_average_rating
        
        product_pk = 'PRODUCT#product-123'
        
        with patch('reviews.create_review.query') as mock_query:
            # No reviews found
            mock_query.return_value = {'Items': []}
            
            result = calculate_average_rating(product_pk)
            
            assert result['averageRating'] == 0.0
            assert result['totalReviews'] == 0
    
    def test_calculate_average_rating_single_review(self):
        """Test product rating calculation with a single review."""
        from reviews.create_review import calculate_average_rating
        
        product_pk = 'PRODUCT#product-123'
        
        with patch('reviews.create_review.query') as mock_query:
            mock_query.return_value = {
                'Items': [
                    {
                        'PK': 'PRODUCT#product-123',
                        'SK': 'REVIEW#review-1',
                        'rating': 5,
                        'reviewText': 'Excellent!'
                    }
                ]
            }
            
            result = calculate_average_rating(product_pk)
            
            assert result['averageRating'] == 5.0
            assert result['totalReviews'] == 1
    
    def test_calculate_average_rating_multiple_reviews_same_rating(self):
        """Test product rating calculation with multiple reviews of the same rating."""
        from reviews.create_review import calculate_average_rating
        
        product_pk = 'PRODUCT#product-123'
        
        with patch('reviews.create_review.query') as mock_query:
            mock_query.return_value = {
                'Items': [
                    {'PK': 'PRODUCT#product-123', 'SK': 'REVIEW#review-1', 'rating': 4},
                    {'PK': 'PRODUCT#product-123', 'SK': 'REVIEW#review-2', 'rating': 4},
                    {'PK': 'PRODUCT#product-123', 'SK': 'REVIEW#review-3', 'rating': 4}
                ]
            }
            
            result = calculate_average_rating(product_pk)
            
            assert result['averageRating'] == 4.0
            assert result['totalReviews'] == 3
    
    def test_calculate_average_rating_multiple_reviews_different_ratings(self):
        """Test product rating calculation with multiple reviews of different ratings."""
        from reviews.create_review import calculate_average_rating
        
        product_pk = 'PRODUCT#product-123'
        
        with patch('reviews.create_review.query') as mock_query:
            # Reviews with ratings: 5, 4, 3, 4, 5 = 21 / 5 = 4.2
            mock_query.return_value = {
                'Items': [
                    {'PK': 'PRODUCT#product-123', 'SK': 'REVIEW#review-1', 'rating': 5},
                    {'PK': 'PRODUCT#product-123', 'SK': 'REVIEW#review-2', 'rating': 4},
                    {'PK': 'PRODUCT#product-123', 'SK': 'REVIEW#review-3', 'rating': 3},
                    {'PK': 'PRODUCT#product-123', 'SK': 'REVIEW#review-4', 'rating': 4},
                    {'PK': 'PRODUCT#product-123', 'SK': 'REVIEW#review-5', 'rating': 5}
                ]
            }
            
            result = calculate_average_rating(product_pk)
            
            assert result['averageRating'] == 4.2
            assert result['totalReviews'] == 5
    
    def test_calculate_average_rating_rounds_to_two_decimals(self):
        """Test that average rating is rounded to 2 decimal places."""
        from reviews.create_review import calculate_average_rating
        
        product_pk = 'PRODUCT#product-123'
        
        with patch('reviews.create_review.query') as mock_query:
            # Reviews with ratings: 5, 4, 3 = 12 / 3 = 4.0
            # But let's test with: 5, 5, 4 = 14 / 3 = 4.666... should round to 4.67
            mock_query.return_value = {
                'Items': [
                    {'PK': 'PRODUCT#product-123', 'SK': 'REVIEW#review-1', 'rating': 5},
                    {'PK': 'PRODUCT#product-123', 'SK': 'REVIEW#review-2', 'rating': 5},
                    {'PK': 'PRODUCT#product-123', 'SK': 'REVIEW#review-3', 'rating': 4}
                ]
            }
            
            result = calculate_average_rating(product_pk)
            
            assert result['averageRating'] == 4.67
            assert result['totalReviews'] == 3
    
    def test_calculate_average_rating_all_minimum_ratings(self):
        """Test product rating calculation with all minimum ratings (1 star)."""
        from reviews.create_review import calculate_average_rating
        
        product_pk = 'PRODUCT#product-123'
        
        with patch('reviews.create_review.query') as mock_query:
            mock_query.return_value = {
                'Items': [
                    {'PK': 'PRODUCT#product-123', 'SK': 'REVIEW#review-1', 'rating': 1},
                    {'PK': 'PRODUCT#product-123', 'SK': 'REVIEW#review-2', 'rating': 1},
                    {'PK': 'PRODUCT#product-123', 'SK': 'REVIEW#review-3', 'rating': 1}
                ]
            }
            
            result = calculate_average_rating(product_pk)
            
            assert result['averageRating'] == 1.0
            assert result['totalReviews'] == 3
    
    def test_calculate_average_rating_all_maximum_ratings(self):
        """Test product rating calculation with all maximum ratings (5 stars)."""
        from reviews.create_review import calculate_average_rating
        
        product_pk = 'PRODUCT#product-123'
        
        with patch('reviews.create_review.query') as mock_query:
            mock_query.return_value = {
                'Items': [
                    {'PK': 'PRODUCT#product-123', 'SK': 'REVIEW#review-1', 'rating': 5},
                    {'PK': 'PRODUCT#product-123', 'SK': 'REVIEW#review-2', 'rating': 5},
                    {'PK': 'PRODUCT#product-123', 'SK': 'REVIEW#review-3', 'rating': 5}
                ]
            }
            
            result = calculate_average_rating(product_pk)
            
            assert result['averageRating'] == 5.0
            assert result['totalReviews'] == 3
    
    def test_calculate_average_rating_large_number_of_reviews(self):
        """Test product rating calculation with a large number of reviews."""
        from reviews.create_review import calculate_average_rating
        
        product_pk = 'PRODUCT#product-123'
        
        with patch('reviews.create_review.query') as mock_query:
            # Create 100 reviews with varying ratings
            reviews = []
            for i in range(100):
                rating = (i % 5) + 1  # Cycles through 1, 2, 3, 4, 5
                reviews.append({
                    'PK': 'PRODUCT#product-123',
                    'SK': f'REVIEW#review-{i}',
                    'rating': rating
                })
            
            mock_query.return_value = {'Items': reviews}
            
            result = calculate_average_rating(product_pk)
            
            # Average of 1,2,3,4,5 repeated 20 times = (1+2+3+4+5)*20 / 100 = 300/100 = 3.0
            assert result['averageRating'] == 3.0
            assert result['totalReviews'] == 100
    
    def test_calculate_average_rating_query_error_returns_defaults(self):
        """Test that query errors return default values without crashing."""
        from reviews.create_review import calculate_average_rating
        
        product_pk = 'PRODUCT#product-123'
        
        with patch('reviews.create_review.query') as mock_query:
            mock_query.side_effect = Exception('DynamoDB connection error')
            
            result = calculate_average_rating(product_pk)
            
            # Should return defaults on error
            assert result['averageRating'] == 0.0
            assert result['totalReviews'] == 0
    
    def test_calculate_average_rating_missing_rating_field(self):
        """Test handling of reviews with missing rating field."""
        from reviews.create_review import calculate_average_rating
        
        product_pk = 'PRODUCT#product-123'
        
        with patch('reviews.create_review.query') as mock_query:
            mock_query.return_value = {
                'Items': [
                    {'PK': 'PRODUCT#product-123', 'SK': 'REVIEW#review-1', 'rating': 5},
                    {'PK': 'PRODUCT#product-123', 'SK': 'REVIEW#review-2'},  # Missing rating
                    {'PK': 'PRODUCT#product-123', 'SK': 'REVIEW#review-3', 'rating': 4}
                ]
            }
            
            result = calculate_average_rating(product_pk)
            
            # Missing rating should be treated as 0, so (5 + 0 + 4) / 3 = 3.0
            assert result['averageRating'] == 3.0
            assert result['totalReviews'] == 3


class TestFarmerRatingAggregation:
    """Test suite for farmer rating aggregation (Requirement 14.6)."""
    
    def test_calculate_farmer_average_rating_no_reviews(self):
        """Test farmer rating calculation when no reviews exist."""
        from reviews.create_review import calculate_farmer_average_rating
        
        farmer_id = 'farmer-123'
        
        with patch('reviews.create_review.query') as mock_query:
            # No reviews found
            mock_query.return_value = {'Items': []}
            
            result = calculate_farmer_average_rating(farmer_id)
            
            assert result['averageRating'] == 0.0
            assert result['totalReviews'] == 0
    
    def test_calculate_farmer_average_rating_single_review(self):
        """Test farmer rating calculation with a single review."""
        from reviews.create_review import calculate_farmer_average_rating
        
        farmer_id = 'farmer-123'
        
        with patch('reviews.create_review.query') as mock_query:
            mock_query.return_value = {
                'Items': [
                    {
                        'PK': 'PRODUCT#product-1',
                        'SK': 'REVIEW#review-1',
                        'GSI2PK': 'FARMER#farmer-123',
                        'rating': 5,
                        'reviewText': 'Excellent farmer!'
                    }
                ]
            }
            
            result = calculate_farmer_average_rating(farmer_id)
            
            assert result['averageRating'] == 5.0
            assert result['totalReviews'] == 1
    
    def test_calculate_farmer_average_rating_multiple_products(self):
        """Test farmer rating calculation across multiple products."""
        from reviews.create_review import calculate_farmer_average_rating
        
        farmer_id = 'farmer-123'
        
        with patch('reviews.create_review.query') as mock_query:
            # Reviews from different products by the same farmer
            mock_query.return_value = {
                'Items': [
                    {'PK': 'PRODUCT#product-1', 'SK': 'REVIEW#review-1', 'GSI2PK': 'FARMER#farmer-123', 'rating': 5},
                    {'PK': 'PRODUCT#product-1', 'SK': 'REVIEW#review-2', 'GSI2PK': 'FARMER#farmer-123', 'rating': 4},
                    {'PK': 'PRODUCT#product-2', 'SK': 'REVIEW#review-3', 'GSI2PK': 'FARMER#farmer-123', 'rating': 5},
                    {'PK': 'PRODUCT#product-2', 'SK': 'REVIEW#review-4', 'GSI2PK': 'FARMER#farmer-123', 'rating': 3},
                    {'PK': 'PRODUCT#product-3', 'SK': 'REVIEW#review-5', 'GSI2PK': 'FARMER#farmer-123', 'rating': 4}
                ]
            }
            
            result = calculate_farmer_average_rating(farmer_id)
            
            # Average: (5 + 4 + 5 + 3 + 4) / 5 = 21 / 5 = 4.2
            assert result['averageRating'] == 4.2
            assert result['totalReviews'] == 5
    
    def test_calculate_farmer_average_rating_rounds_to_two_decimals(self):
        """Test that farmer average rating is rounded to 2 decimal places."""
        from reviews.create_review import calculate_farmer_average_rating
        
        farmer_id = 'farmer-123'
        
        with patch('reviews.create_review.query') as mock_query:
            # Ratings: 5, 5, 4 = 14 / 3 = 4.666... should round to 4.67
            mock_query.return_value = {
                'Items': [
                    {'PK': 'PRODUCT#product-1', 'SK': 'REVIEW#review-1', 'GSI2PK': 'FARMER#farmer-123', 'rating': 5},
                    {'PK': 'PRODUCT#product-1', 'SK': 'REVIEW#review-2', 'GSI2PK': 'FARMER#farmer-123', 'rating': 5},
                    {'PK': 'PRODUCT#product-2', 'SK': 'REVIEW#review-3', 'GSI2PK': 'FARMER#farmer-123', 'rating': 4}
                ]
            }
            
            result = calculate_farmer_average_rating(farmer_id)
            
            assert result['averageRating'] == 4.67
            assert result['totalReviews'] == 3
    
    def test_calculate_farmer_average_rating_all_minimum_ratings(self):
        """Test farmer rating calculation with all minimum ratings (1 star)."""
        from reviews.create_review import calculate_farmer_average_rating
        
        farmer_id = 'farmer-123'
        
        with patch('reviews.create_review.query') as mock_query:
            mock_query.return_value = {
                'Items': [
                    {'PK': 'PRODUCT#product-1', 'SK': 'REVIEW#review-1', 'GSI2PK': 'FARMER#farmer-123', 'rating': 1},
                    {'PK': 'PRODUCT#product-2', 'SK': 'REVIEW#review-2', 'GSI2PK': 'FARMER#farmer-123', 'rating': 1},
                    {'PK': 'PRODUCT#product-3', 'SK': 'REVIEW#review-3', 'GSI2PK': 'FARMER#farmer-123', 'rating': 1}
                ]
            }
            
            result = calculate_farmer_average_rating(farmer_id)
            
            assert result['averageRating'] == 1.0
            assert result['totalReviews'] == 3
    
    def test_calculate_farmer_average_rating_all_maximum_ratings(self):
        """Test farmer rating calculation with all maximum ratings (5 stars)."""
        from reviews.create_review import calculate_farmer_average_rating
        
        farmer_id = 'farmer-123'
        
        with patch('reviews.create_review.query') as mock_query:
            mock_query.return_value = {
                'Items': [
                    {'PK': 'PRODUCT#product-1', 'SK': 'REVIEW#review-1', 'GSI2PK': 'FARMER#farmer-123', 'rating': 5},
                    {'PK': 'PRODUCT#product-2', 'SK': 'REVIEW#review-2', 'GSI2PK': 'FARMER#farmer-123', 'rating': 5},
                    {'PK': 'PRODUCT#product-3', 'SK': 'REVIEW#review-3', 'GSI2PK': 'FARMER#farmer-123', 'rating': 5}
                ]
            }
            
            result = calculate_farmer_average_rating(farmer_id)
            
            assert result['averageRating'] == 5.0
            assert result['totalReviews'] == 3
    
    def test_calculate_farmer_average_rating_large_number_of_reviews(self):
        """Test farmer rating calculation with a large number of reviews across many products."""
        from reviews.create_review import calculate_farmer_average_rating
        
        farmer_id = 'farmer-123'
        
        with patch('reviews.create_review.query') as mock_query:
            # Create 100 reviews across 10 products
            reviews = []
            for i in range(100):
                rating = (i % 5) + 1  # Cycles through 1, 2, 3, 4, 5
                product_num = i % 10
                reviews.append({
                    'PK': f'PRODUCT#product-{product_num}',
                    'SK': f'REVIEW#review-{i}',
                    'GSI2PK': 'FARMER#farmer-123',
                    'rating': rating
                })
            
            mock_query.return_value = {'Items': reviews}
            
            result = calculate_farmer_average_rating(farmer_id)
            
            # Average of 1,2,3,4,5 repeated 20 times = (1+2+3+4+5)*20 / 100 = 300/100 = 3.0
            assert result['averageRating'] == 3.0
            assert result['totalReviews'] == 100
    
    def test_calculate_farmer_average_rating_query_error_returns_defaults(self):
        """Test that query errors return default values without crashing."""
        from reviews.create_review import calculate_farmer_average_rating
        
        farmer_id = 'farmer-123'
        
        with patch('reviews.create_review.query') as mock_query:
            mock_query.side_effect = Exception('DynamoDB connection error')
            
            result = calculate_farmer_average_rating(farmer_id)
            
            # Should return defaults on error
            assert result['averageRating'] == 0.0
            assert result['totalReviews'] == 0
    
    def test_calculate_farmer_average_rating_missing_rating_field(self):
        """Test handling of reviews with missing rating field."""
        from reviews.create_review import calculate_farmer_average_rating
        
        farmer_id = 'farmer-123'
        
        with patch('reviews.create_review.query') as mock_query:
            mock_query.return_value = {
                'Items': [
                    {'PK': 'PRODUCT#product-1', 'SK': 'REVIEW#review-1', 'GSI2PK': 'FARMER#farmer-123', 'rating': 5},
                    {'PK': 'PRODUCT#product-2', 'SK': 'REVIEW#review-2', 'GSI2PK': 'FARMER#farmer-123'},  # Missing rating
                    {'PK': 'PRODUCT#product-3', 'SK': 'REVIEW#review-3', 'GSI2PK': 'FARMER#farmer-123', 'rating': 4}
                ]
            }
            
            result = calculate_farmer_average_rating(farmer_id)
            
            # Missing rating should be treated as 0, so (5 + 0 + 4) / 3 = 3.0
            assert result['averageRating'] == 3.0
            assert result['totalReviews'] == 3
    
    def test_calculate_farmer_average_rating_uses_gsi2(self):
        """Test that farmer rating calculation uses GSI2 index."""
        from reviews.create_review import calculate_farmer_average_rating
        
        farmer_id = 'farmer-123'
        
        with patch('reviews.create_review.query') as mock_query:
            mock_query.return_value = {'Items': []}
            
            calculate_farmer_average_rating(farmer_id)
            
            # Verify query was called with GSI2 index
            mock_query.assert_called_once()
            call_kwargs = mock_query.call_args[1]
            assert call_kwargs['index_name'] == 'GSI2'


class TestRatingAggregationIntegration:
    """Integration tests for rating aggregation in the review submission flow."""
    
    def test_review_submission_updates_product_rating(self):
        """Test that submitting a review updates the product's average rating."""
        from reviews.create_review import handler
        import json
        
        consumer_token_payload = {
            'userId': 'consumer-123',
            'email': 'consumer@example.com',
            'role': 'consumer'
        }
        
        review_request = {
            'productId': 'product-789',
            'orderId': 'order-abc',
            'rating': 5,
            'reviewText': 'Excellent product!',
            'photoUploadCount': 0
        }
        
        order_item = {
            'PK': 'ORDER#order-abc',
            'SK': 'METADATA',
            'orderId': 'order-abc',
            'consumerId': 'consumer-123',
            'productId': 'product-789',
            'farmerId': 'farmer-456',
            'status': 'delivered'
        }
        
        product_item = {
            'PK': 'PRODUCT#product-789',
            'SK': 'METADATA',
            'productId': 'product-789',
            'farmerId': 'farmer-456',
            'name': 'Organic Tomatoes',
            'averageRating': 4.0,
            'totalReviews': 2
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
            
            mock_auth.return_value = consumer_token_payload
            mock_get.side_effect = [order_item, product_item]
            # New average after adding rating 5 to existing ratings: (4.0*2 + 5) / 3 = 13/3 = 4.33
            mock_calc_product.return_value = {'averageRating': 4.33, 'totalReviews': 3}
            mock_calc_farmer.return_value = {'averageRating': 4.5, 'totalReviews': 10}
            
            response = handler(event, None)
            
            assert response['statusCode'] == 201
            
            # Verify product rating was updated
            product_update_calls = [call for call in mock_update.call_args_list 
                                   if call[1]['pk'] == 'PRODUCT#product-789']
            assert len(product_update_calls) == 1
            
            product_update = product_update_calls[0]
            assert product_update[1]['expression_attribute_values'][':avg'] == 4.33
            assert product_update[1]['expression_attribute_values'][':total'] == 3
    
    def test_review_submission_updates_farmer_rating(self):
        """Test that submitting a review updates the farmer's average rating."""
        from reviews.create_review import handler
        import json
        
        consumer_token_payload = {
            'userId': 'consumer-123',
            'email': 'consumer@example.com',
            'role': 'consumer'
        }
        
        review_request = {
            'productId': 'product-789',
            'orderId': 'order-abc',
            'rating': 5,
            'reviewText': 'Excellent product!',
            'photoUploadCount': 0
        }
        
        order_item = {
            'PK': 'ORDER#order-abc',
            'SK': 'METADATA',
            'orderId': 'order-abc',
            'consumerId': 'consumer-123',
            'productId': 'product-789',
            'farmerId': 'farmer-456'
        }
        
        product_item = {
            'PK': 'PRODUCT#product-789',
            'SK': 'METADATA',
            'productId': 'product-789',
            'farmerId': 'farmer-456',
            'name': 'Organic Tomatoes'
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
            
            mock_auth.return_value = consumer_token_payload
            mock_get.side_effect = [order_item, product_item]
            mock_calc_product.return_value = {'averageRating': 4.5, 'totalReviews': 3}
            # Farmer has reviews across multiple products
            mock_calc_farmer.return_value = {'averageRating': 4.6, 'totalReviews': 15}
            
            response = handler(event, None)
            
            assert response['statusCode'] == 201
            
            # Verify farmer rating was updated
            farmer_update_calls = [call for call in mock_update.call_args_list 
                                  if call[1]['pk'] == 'USER#farmer-456']
            assert len(farmer_update_calls) == 1
            
            farmer_update = farmer_update_calls[0]
            assert farmer_update[1]['expression_attribute_values'][':avg'] == 4.6
            assert farmer_update[1]['expression_attribute_values'][':total'] == 15


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
