"""
Unit tests for sales streak tracking Lambda function.
Tests Requirements 12.1 and 12.4: Sales streak bonus and notifications.
"""
import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal

# Mock the shared modules before importing the handler
import sys
sys.path.insert(0, 'backend/referrals')
sys.path.insert(0, 'backend/shared')

# Mock the shared module imports
sys.modules['shared'] = MagicMock()
sys.modules['shared.database'] = MagicMock()
sys.modules['shared.email_service'] = MagicMock()
sys.modules['shared.email_templates'] = MagicMock()
sys.modules['shared.constants'] = MagicMock()

# Set constants
sys.modules['shared.constants'].MIN_ACCEPTABLE_RATING = 3
sys.modules['shared.constants'].SALES_STREAK_THRESHOLD = 10

# Import the handler after mocking
from track_sales_streak import handler, SALES_STREAK_BONUS_AMOUNT


@pytest.fixture
def dynamodb_stream_event_new_review():
    """Create a DynamoDB Stream event for a new review (INSERT)."""
    return {
        'Records': [
            {
                'eventName': 'INSERT',
                'dynamodb': {
                    'NewImage': {
                        'EntityType': {'S': 'Review'},
                        'reviewId': {'S': 'review-123'},
                        'farmerId': {'S': 'farmer-456'},
                        'productId': {'S': 'product-789'},
                        'orderId': {'S': 'order-001'},
                        'rating': {'N': '4'},
                        'reviewText': {'S': 'Great product!'},
                        'createdAt': {'S': '2024-01-15T10:00:00Z'}
                    }
                }
            }
        ]
    }


@pytest.fixture
def dynamodb_stream_event_modify_review():
    """Create a DynamoDB Stream event for a modified review (should be ignored)."""
    return {
        'Records': [
            {
                'eventName': 'MODIFY',
                'dynamodb': {
                    'NewImage': {
                        'EntityType': {'S': 'Review'},
                        'reviewId': {'S': 'review-123'},
                        'farmerId': {'S': 'farmer-456'},
                        'rating': {'N': '5'}
                    }
                }
            }
        ]
    }


@pytest.fixture
def dynamodb_stream_event_non_review():
    """Create a DynamoDB Stream event for a non-review entity (should be ignored)."""
    return {
        'Records': [
            {
                'eventName': 'INSERT',
                'dynamodb': {
                    'NewImage': {
                        'EntityType': {'S': 'Order'},
                        'orderId': {'S': 'order-123'}
                    }
                }
            }
        ]
    }


@pytest.fixture
def mock_farmer_item():
    """Create a mock farmer item."""
    return {
        'PK': 'USER#farmer-456',
        'SK': 'PROFILE',
        'EntityType': 'User',
        'userId': 'farmer-456',
        'email': 'farmer@example.com',
        'firstName': 'John',
        'lastName': 'Farmer',
        'role': 'farmer',
        'notificationPreferences': {
            'farmerBonuses': True
        },
        'farmerProfile': {
            'farmName': 'Green Valley Farm',
            'consecutiveSalesStreak': 9,
            'bonusesEarned': Decimal('0.0'),
            'averageRating': Decimal('4.5'),
            'totalReviews': 50
        }
    }


@pytest.fixture
def mock_orders_10_with_good_reviews():
    """Create 10 mock orders for a farmer."""
    orders = []
    for i in range(10):
        orders.append({
            'PK': f'ORDER#order-{i:03d}',
            'SK': 'METADATA',
            'EntityType': 'Order',
            'orderId': f'order-{i:03d}',
            'farmerId': 'farmer-456',
            'productId': f'product-{i:03d}',
            'consumerId': f'consumer-{i:03d}',
            'status': 'delivered',
            'createdAt': (datetime.now() - timedelta(days=i)).isoformat()
        })
    return orders


@pytest.fixture
def mock_reviews_all_good():
    """Create mock reviews with all ratings >= 3."""
    reviews = []
    for i in range(10):
        reviews.append({
            'PK': f'PRODUCT#product-{i:03d}',
            'SK': f'REVIEW#review-{i:03d}',
            'EntityType': 'Review',
            'reviewId': f'review-{i:03d}',
            'orderId': f'order-{i:03d}',
            'rating': 4,  # All good ratings
            'reviewText': 'Great product!',
            'createdAt': (datetime.now() - timedelta(days=i)).isoformat()
        })
    return reviews


@pytest.fixture
def mock_reviews_with_bad_rating():
    """Create mock reviews with one bad rating."""
    reviews = []
    for i in range(10):
        rating = 2 if i == 5 else 4  # One bad rating
        reviews.append({
            'PK': f'PRODUCT#product-{i:03d}',
            'SK': f'REVIEW#review-{i:03d}',
            'EntityType': 'Review',
            'reviewId': f'review-{i:03d}',
            'orderId': f'order-{i:03d}',
            'rating': rating,
            'reviewText': 'Product review',
            'createdAt': (datetime.now() - timedelta(days=i)).isoformat()
        })
    return reviews


class TestSalesStreakTracking:
    """Test suite for sales streak tracking function."""
    
    def test_ignores_non_insert_events(self, dynamodb_stream_event_modify_review):
        """Test that MODIFY events are ignored."""
        with patch('track_sales_streak.get_item') as mock_get_item:
            result = handler(dynamodb_stream_event_modify_review, None)
            
            assert result['statusCode'] == 200
            body = json.loads(result['body'])
            assert body['processed'] == 0
            mock_get_item.assert_not_called()
    
    def test_ignores_non_review_entities(self, dynamodb_stream_event_non_review):
        """Test that non-Review entities are ignored."""
        with patch('track_sales_streak.get_item') as mock_get_item:
            result = handler(dynamodb_stream_event_non_review, None)
            
            assert result['statusCode'] == 200
            body = json.loads(result['body'])
            assert body['processed'] == 0
            mock_get_item.assert_not_called()
    
    def test_handles_missing_farmer(self, dynamodb_stream_event_new_review):
        """Test handling when farmer is not found."""
        with patch('track_sales_streak.get_item', return_value=None):
            result = handler(dynamodb_stream_event_new_review, None)
            
            assert result['statusCode'] == 200
            body = json.loads(result['body'])
            assert body['errors'] == 1
    
    def test_handles_farmer_with_less_than_10_orders(
        self, dynamodb_stream_event_new_review, mock_farmer_item
    ):
        """Test that farmers with less than 10 orders don't get evaluated."""
        with patch('track_sales_streak.get_item', return_value=mock_farmer_item), \
             patch('track_sales_streak.query') as mock_query:
            
            # Return only 5 orders
            mock_query.return_value = {
                'Items': [{'orderId': f'order-{i}'} for i in range(5)]
            }
            
            result = handler(dynamodb_stream_event_new_review, None)
            
            assert result['statusCode'] == 200
            body = json.loads(result['body'])
            assert body['processed'] == 1
            assert body['bonuses_awarded'] == 0
    
    def test_awards_bonus_when_streak_threshold_reached(
        self, dynamodb_stream_event_new_review, mock_farmer_item,
        mock_orders_10_with_good_reviews, mock_reviews_all_good
    ):
        """Test that bonus is awarded when farmer reaches 10 consecutive good sales."""
        # Set current streak to 9 (just below threshold)
        mock_farmer_item['farmerProfile']['consecutiveSalesStreak'] = 9
        
        with patch('track_sales_streak.get_item', return_value=mock_farmer_item), \
             patch('track_sales_streak.query') as mock_query, \
             patch('track_sales_streak.update_item') as mock_update, \
             patch('track_sales_streak.get_email_service') as mock_email_service, \
             patch('track_sales_streak.get_farmer_bonus_email') as mock_email_template:
            
            # Mock query to return orders and reviews
            def query_side_effect(*args, **kwargs):
                index_name = kwargs.get('index_name')
                if index_name == 'GSI3':
                    # This is the orders query
                    return {'Items': mock_orders_10_with_good_reviews}
                else:
                    # This is a reviews query - return all reviews
                    return {'Items': mock_reviews_all_good}
            
            mock_query.side_effect = query_side_effect
            
            # Mock email template
            mock_email_template.return_value = {
                'subject': 'Congratulations! You\'ve Earned a Sales Streak Bonus',
                'html_body': '<html>Bonus email</html>',
                'text_body': 'Bonus email'
            }
            
            # Mock email service
            mock_email = Mock()
            mock_email.send_email.return_value = {'success': True, 'message_id': 'msg-123'}
            mock_email_service.return_value = mock_email
            
            result = handler(dynamodb_stream_event_new_review, None)
            
            assert result['statusCode'] == 200
            body = json.loads(result['body'])
            assert body['processed'] == 1
            assert body['bonuses_awarded'] == 1
            
            # Verify update_item was called with correct bonus amount
            mock_update.assert_called()
            call_args = mock_update.call_args
            assert call_args[1]['expression_attribute_values'][':bonuses'] == SALES_STREAK_BONUS_AMOUNT
            assert call_args[1]['expression_attribute_values'][':streak'] == 10
            
            # Verify email was sent
            mock_email.send_email.assert_called_once()
            email_call = mock_email.send_email.call_args
            assert email_call[1]['recipient'] == 'farmer@example.com'
            assert 'Sales Streak Bonus' in email_call[1]['subject']
    
    def test_no_bonus_when_already_above_threshold(
        self, dynamodb_stream_event_new_review, mock_farmer_item,
        mock_orders_10_with_good_reviews, mock_reviews_all_good
    ):
        """Test that bonus is not awarded again if farmer already has streak >= 10."""
        # Set current streak to 10 (already at threshold)
        mock_farmer_item['farmerProfile']['consecutiveSalesStreak'] = 10
        
        with patch('track_sales_streak.get_item', return_value=mock_farmer_item), \
             patch('track_sales_streak.query') as mock_query, \
             patch('track_sales_streak.update_item') as mock_update, \
             patch('track_sales_streak.get_email_service') as mock_email_service:
            
            # Mock query to return orders and reviews
            def query_side_effect(*args, **kwargs):
                index_name = kwargs.get('index_name')
                if index_name == 'GSI3':
                    return {'Items': mock_orders_10_with_good_reviews}
                else:
                    return {'Items': mock_reviews_all_good}
            
            mock_query.side_effect = query_side_effect
            
            # Mock email service
            mock_email = Mock()
            mock_email_service.return_value = mock_email
            
            result = handler(dynamodb_stream_event_new_review, None)
            
            assert result['statusCode'] == 200
            body = json.loads(result['body'])
            assert body['processed'] == 1
            assert body['bonuses_awarded'] == 0
            
            # Verify update_item was called but only to update streak, not bonus
            mock_update.assert_called()
            call_args = mock_update.call_args
            # Should only update streak, not bonuses
            assert ':streak' in call_args[1]['expression_attribute_values']
            assert ':bonuses' not in call_args[1]['expression_attribute_values']
            
            # Verify email was NOT sent
            mock_email.send_email.assert_not_called()
    
    def test_resets_streak_when_bad_review_found(
        self, dynamodb_stream_event_new_review, mock_farmer_item,
        mock_orders_10_with_good_reviews, mock_reviews_with_bad_rating
    ):
        """Test that streak is reset to 0 when a review with rating < 3 is found."""
        # Set current streak to 9
        mock_farmer_item['farmerProfile']['consecutiveSalesStreak'] = 9
        
        with patch('track_sales_streak.get_item', return_value=mock_farmer_item), \
             patch('track_sales_streak.query') as mock_query, \
             patch('track_sales_streak.update_item') as mock_update:
            
            # Mock query to return orders and reviews (with one bad rating)
            def query_side_effect(*args, **kwargs):
                index_name = kwargs.get('index_name')
                if index_name == 'GSI3':
                    return {'Items': mock_orders_10_with_good_reviews}
                else:
                    return {'Items': mock_reviews_with_bad_rating}
            
            mock_query.side_effect = query_side_effect
            
            result = handler(dynamodb_stream_event_new_review, None)
            
            assert result['statusCode'] == 200
            body = json.loads(result['body'])
            assert body['processed'] == 1
            assert body['bonuses_awarded'] == 0
            
            # Verify streak was reset to 0
            mock_update.assert_called()
            call_args = mock_update.call_args
            assert call_args[1]['expression_attribute_values'][':streak'] == 0
    
    def test_respects_notification_preferences(
        self, dynamodb_stream_event_new_review, mock_farmer_item,
        mock_orders_10_with_good_reviews, mock_reviews_all_good
    ):
        """Test that bonus email is not sent if farmer has disabled notifications."""
        # Disable bonus notifications
        mock_farmer_item['notificationPreferences']['farmerBonuses'] = False
        mock_farmer_item['farmerProfile']['consecutiveSalesStreak'] = 9
        
        with patch('track_sales_streak.get_item', return_value=mock_farmer_item), \
             patch('track_sales_streak.query') as mock_query, \
             patch('track_sales_streak.update_item') as mock_update, \
             patch('track_sales_streak.get_email_service') as mock_email_service:
            
            # Mock query to return orders and reviews
            def query_side_effect(*args, **kwargs):
                index_name = kwargs.get('index_name')
                if index_name == 'GSI3':
                    return {'Items': mock_orders_10_with_good_reviews}
                else:
                    return {'Items': mock_reviews_all_good}
            
            mock_query.side_effect = query_side_effect
            
            # Mock email service
            mock_email = Mock()
            mock_email_service.return_value = mock_email
            
            result = handler(dynamodb_stream_event_new_review, None)
            
            assert result['statusCode'] == 200
            body = json.loads(result['body'])
            assert body['bonuses_awarded'] == 1
            
            # Verify email was NOT sent due to preferences
            mock_email.send_email.assert_not_called()
    
    def test_handles_missing_order_reviews(
        self, dynamodb_stream_event_new_review, mock_farmer_item,
        mock_orders_10_with_good_reviews
    ):
        """Test that streak is reset when some orders don't have reviews yet."""
        mock_farmer_item['farmerProfile']['consecutiveSalesStreak'] = 5
        
        with patch('track_sales_streak.get_item', return_value=mock_farmer_item), \
             patch('track_sales_streak.query') as mock_query, \
             patch('track_sales_streak.update_item') as mock_update:
            
            # Mock query to return orders but no reviews for some
            def query_side_effect(*args, **kwargs):
                index_name = kwargs.get('index_name')
                if index_name == 'GSI3':
                    return {'Items': mock_orders_10_with_good_reviews}
                else:
                    # Return empty reviews (orders without reviews)
                    return {'Items': []}
            
            mock_query.side_effect = query_side_effect
            
            result = handler(dynamodb_stream_event_new_review, None)
            
            assert result['statusCode'] == 200
            body = json.loads(result['body'])
            assert body['processed'] == 1
            
            # Verify streak was reset to 0
            mock_update.assert_called()
            call_args = mock_update.call_args
            assert call_args[1]['expression_attribute_values'][':streak'] == 0
    
    def test_handles_database_errors_gracefully(self, dynamodb_stream_event_new_review):
        """Test that database errors are handled gracefully."""
        with patch('track_sales_streak.get_item', side_effect=Exception('Database error')):
            result = handler(dynamodb_stream_event_new_review, None)
            
            assert result['statusCode'] == 200
            body = json.loads(result['body'])
            assert body['errors'] == 1
    
    def test_processes_multiple_reviews_in_batch(
        self, mock_farmer_item, mock_orders_10_with_good_reviews, mock_reviews_all_good
    ):
        """Test processing multiple review records in a single batch."""
        event = {
            'Records': [
                {
                    'eventName': 'INSERT',
                    'dynamodb': {
                        'NewImage': {
                            'EntityType': {'S': 'Review'},
                            'reviewId': {'S': f'review-{i}'},
                            'farmerId': {'S': 'farmer-456'},
                            'productId': {'S': f'product-{i}'},
                            'orderId': {'S': f'order-{i}'},
                            'rating': {'N': '4'}
                        }
                    }
                }
                for i in range(3)
            ]
        }
        
        with patch('track_sales_streak.get_item', return_value=mock_farmer_item), \
             patch('track_sales_streak.query') as mock_query, \
             patch('track_sales_streak.update_item') as mock_update:
            
            # Mock query to return orders and reviews
            def query_side_effect(*args, **kwargs):
                index_name = kwargs.get('index_name')
                if index_name == 'GSI3':
                    return {'Items': mock_orders_10_with_good_reviews}
                else:
                    return {'Items': mock_reviews_all_good}
            
            mock_query.side_effect = query_side_effect
            
            result = handler(event, None)
            
            assert result['statusCode'] == 200
            body = json.loads(result['body'])
            assert body['processed'] == 3


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
