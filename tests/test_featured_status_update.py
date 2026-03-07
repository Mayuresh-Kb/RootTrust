"""
Unit tests for featured status update Lambda function.
Tests Requirement 12.2: High authenticity scores grant featured placement.
"""
import json
import pytest
from datetime import datetime
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

# Import the handler after mocking
from update_featured_status import (
    handler,
    calculate_farmer_featured_status,
    update_farmer_featured_status,
    FEATURED_STATUS_THRESHOLD
)


@pytest.fixture
def mock_farmer_item():
    """Create a mock farmer item."""
    return {
        'PK': 'USER#farmer-123',
        'SK': 'PROFILE',
        'EntityType': 'User',
        'userId': 'farmer-123',
        'email': 'farmer@example.com',
        'firstName': 'John',
        'lastName': 'Farmer',
        'role': 'farmer',
        'notificationPreferences': {
            'farmerBonuses': True
        },
        'farmerProfile': {
            'farmName': 'Green Valley Farm',
            'featuredStatus': False,
            'averageRating': Decimal('4.5'),
            'totalReviews': 50
        }
    }


@pytest.fixture
def mock_products_high_confidence():
    """Create mock products with high authenticityConfidence (> 90%)."""
    products = []
    for i in range(5):
        products.append({
            'PK': f'PRODUCT#product-{i}',
            'SK': 'METADATA',
            'EntityType': 'Product',
            'productId': f'product-{i}',
            'farmerId': 'farmer-123',
            'name': f'Product {i}',
            'verificationStatus': 'approved',
            'authenticityConfidence': Decimal('95.0'),  # High confidence
            'fraudRiskScore': Decimal('5.0'),
            'createdAt': datetime.now().isoformat()
        })
    return products


@pytest.fixture
def mock_products_low_confidence():
    """Create mock products with low authenticityConfidence (<= 90%)."""
    products = []
    for i in range(5):
        products.append({
            'PK': f'PRODUCT#product-{i}',
            'SK': 'METADATA',
            'EntityType': 'Product',
            'productId': f'product-{i}',
            'farmerId': 'farmer-123',
            'name': f'Product {i}',
            'verificationStatus': 'approved',
            'authenticityConfidence': Decimal('85.0'),  # Low confidence
            'fraudRiskScore': Decimal('15.0'),
            'createdAt': datetime.now().isoformat()
        })
    return products


@pytest.fixture
def mock_products_mixed_confidence():
    """Create mock products with mixed authenticityConfidence (average = 90%)."""
    return [
        {
            'PK': 'PRODUCT#product-1',
            'SK': 'METADATA',
            'EntityType': 'Product',
            'productId': 'product-1',
            'farmerId': 'farmer-123',
            'verificationStatus': 'approved',
            'authenticityConfidence': Decimal('95.0')
        },
        {
            'PK': 'PRODUCT#product-2',
            'SK': 'METADATA',
            'EntityType': 'Product',
            'productId': 'product-2',
            'farmerId': 'farmer-123',
            'verificationStatus': 'approved',
            'authenticityConfidence': Decimal('85.0')
        }
    ]


@pytest.fixture
def mock_products_pending_verification():
    """Create mock products with pending verification status."""
    return [
        {
            'PK': 'PRODUCT#product-1',
            'SK': 'METADATA',
            'EntityType': 'Product',
            'productId': 'product-1',
            'farmerId': 'farmer-123',
            'verificationStatus': 'pending',
            'authenticityConfidence': None
        }
    ]


@pytest.fixture
def dynamodb_stream_event_product_approved():
    """Create a DynamoDB Stream event for an approved product."""
    return {
        'Records': [
            {
                'eventName': 'MODIFY',
                'dynamodb': {
                    'NewImage': {
                        'EntityType': {'S': 'Product'},
                        'productId': {'S': 'product-123'},
                        'farmerId': {'S': 'farmer-456'},
                        'verificationStatus': {'S': 'approved'},
                        'authenticityConfidence': {'N': '95.5'},
                        'fraudRiskScore': {'N': '4.5'}
                    }
                }
            }
        ]
    }


@pytest.fixture
def direct_invocation_event():
    """Create a direct invocation event with farmerId."""
    return {
        'farmerId': 'farmer-123'
    }


class TestCalculateFarmerFeaturedStatus:
    """Test suite for calculate_farmer_featured_status function."""
    
    def test_high_confidence_grants_featured_status(self, mock_products_high_confidence):
        """Test that average confidence > 90% grants featured status."""
        with patch('update_featured_status.query') as mock_query:
            mock_query.return_value = {'Items': mock_products_high_confidence}
            
            result = calculate_farmer_featured_status('farmer-123')
            
            assert result['should_be_featured'] is True
            assert result['average_confidence'] == 95.0
            assert result['approved_product_count'] == 5
    
    def test_low_confidence_denies_featured_status(self, mock_products_low_confidence):
        """Test that average confidence <= 90% denies featured status."""
        with patch('update_featured_status.query') as mock_query:
            mock_query.return_value = {'Items': mock_products_low_confidence}
            
            result = calculate_farmer_featured_status('farmer-123')
            
            assert result['should_be_featured'] is False
            assert result['average_confidence'] == 85.0
            assert result['approved_product_count'] == 5
    
    def test_exactly_90_percent_denies_featured_status(self, mock_products_mixed_confidence):
        """Test that average confidence exactly 90% denies featured status (must be > 90%)."""
        with patch('update_featured_status.query') as mock_query:
            mock_query.return_value = {'Items': mock_products_mixed_confidence}
            
            result = calculate_farmer_featured_status('farmer-123')
            
            # Average of 95 and 85 is 90, which is NOT > 90
            assert result['should_be_featured'] is False
            assert result['average_confidence'] == 90.0
            assert result['approved_product_count'] == 2
    
    def test_no_products_denies_featured_status(self):
        """Test that farmer with no products doesn't get featured status."""
        with patch('update_featured_status.query') as mock_query:
            mock_query.return_value = {'Items': []}
            
            result = calculate_farmer_featured_status('farmer-123')
            
            assert result['should_be_featured'] is False
            assert result['average_confidence'] == 0.0
            assert result['approved_product_count'] == 0
    
    def test_only_approved_products_counted(self, mock_products_pending_verification):
        """Test that only approved products are counted in calculation."""
        with patch('update_featured_status.query') as mock_query:
            mock_query.return_value = {'Items': mock_products_pending_verification}
            
            result = calculate_farmer_featured_status('farmer-123')
            
            assert result['should_be_featured'] is False
            assert result['average_confidence'] == 0.0
            assert result['approved_product_count'] == 0
    
    def test_products_without_confidence_ignored(self):
        """Test that products without authenticityConfidence are ignored."""
        products = [
            {
                'productId': 'product-1',
                'farmerId': 'farmer-123',
                'verificationStatus': 'approved',
                'authenticityConfidence': None  # No confidence score
            },
            {
                'productId': 'product-2',
                'farmerId': 'farmer-123',
                'verificationStatus': 'approved',
                'authenticityConfidence': Decimal('95.0')
            }
        ]
        
        with patch('update_featured_status.query') as mock_query:
            mock_query.return_value = {'Items': products}
            
            result = calculate_farmer_featured_status('farmer-123')
            
            # Should only count product-2
            assert result['average_confidence'] == 95.0
            assert result['should_be_featured'] is True
    
    def test_handles_decimal_type_confidence(self):
        """Test that Decimal type authenticityConfidence is handled correctly."""
        products = [
            {
                'productId': 'product-1',
                'farmerId': 'farmer-123',
                'verificationStatus': 'approved',
                'authenticityConfidence': Decimal('92.5')
            }
        ]
        
        with patch('update_featured_status.query') as mock_query:
            mock_query.return_value = {'Items': products}
            
            result = calculate_farmer_featured_status('farmer-123')
            
            assert result['average_confidence'] == 92.5
            assert result['should_be_featured'] is True
    
    def test_handles_query_error(self):
        """Test that query errors are handled gracefully."""
        with patch('update_featured_status.query', side_effect=Exception('Database error')):
            result = calculate_farmer_featured_status('farmer-123')
            
            assert result['should_be_featured'] is False
            assert 'error' in result


class TestUpdateFarmerFeaturedStatus:
    """Test suite for update_farmer_featured_status function."""
    
    def test_updates_featured_status_to_true(self):
        """Test updating featured status to True."""
        with patch('update_featured_status.update_item') as mock_update:
            result = update_farmer_featured_status('farmer-123', True)
            
            assert result is True
            mock_update.assert_called_once()
            call_args = mock_update.call_args
            assert call_args[1]['pk'] == 'USER#farmer-123'
            assert call_args[1]['sk'] == 'PROFILE'
            assert call_args[1]['expression_attribute_values'][':status'] is True
    
    def test_updates_featured_status_to_false(self):
        """Test updating featured status to False."""
        with patch('update_featured_status.update_item') as mock_update:
            result = update_farmer_featured_status('farmer-123', False)
            
            assert result is True
            mock_update.assert_called_once()
            call_args = mock_update.call_args
            assert call_args[1]['expression_attribute_values'][':status'] is False
    
    def test_handles_update_error(self):
        """Test that update errors are handled gracefully."""
        with patch('update_featured_status.update_item', side_effect=Exception('Update error')):
            result = update_farmer_featured_status('farmer-123', True)
            
            assert result is False


class TestFeaturedStatusHandler:
    """Test suite for main Lambda handler."""
    
    def test_processes_dynamodb_stream_event(
        self, dynamodb_stream_event_product_approved, mock_farmer_item,
        mock_products_high_confidence
    ):
        """Test processing DynamoDB Stream event when product is approved."""
        with patch('update_featured_status.get_item', return_value=mock_farmer_item), \
             patch('update_featured_status.query') as mock_query, \
             patch('update_featured_status.update_item') as mock_update, \
             patch('update_featured_status.get_email_service') as mock_email_service:
            
            mock_query.return_value = {'Items': mock_products_high_confidence}
            
            # Mock email service
            mock_email = Mock()
            mock_email.send_email.return_value = {'success': True, 'message_id': 'msg-123'}
            mock_email_service.return_value = mock_email
            
            result = handler(dynamodb_stream_event_product_approved, None)
            
            assert result['statusCode'] == 200
            body = json.loads(result['body'])
            assert body['processed'] == 1
            assert body['status_changes'] == 1
            
            # Verify update was called
            mock_update.assert_called()
            call_args = mock_update.call_args
            assert call_args[1]['expression_attribute_values'][':status'] is True
            
            # Verify email was sent
            mock_email.send_email.assert_called_once()
    
    def test_processes_direct_invocation(
        self, direct_invocation_event, mock_farmer_item, mock_products_high_confidence
    ):
        """Test processing direct invocation with farmerId."""
        with patch('update_featured_status.get_item', return_value=mock_farmer_item), \
             patch('update_featured_status.query') as mock_query, \
             patch('update_featured_status.update_item') as mock_update, \
             patch('update_featured_status.get_email_service') as mock_email_service:
            
            mock_query.return_value = {'Items': mock_products_high_confidence}
            
            # Mock email service
            mock_email = Mock()
            mock_email.send_email.return_value = {'success': True}
            mock_email_service.return_value = mock_email
            
            result = handler(direct_invocation_event, None)
            
            assert result['statusCode'] == 200
            body = json.loads(result['body'])
            assert body['processed'] == 1
            assert body['status_changes'] == 1
    
    def test_no_status_change_when_already_featured(
        self, direct_invocation_event, mock_farmer_item, mock_products_high_confidence
    ):
        """Test that no update occurs when farmer already has correct featured status."""
        # Set farmer as already featured
        mock_farmer_item['farmerProfile']['featuredStatus'] = True
        
        with patch('update_featured_status.get_item', return_value=mock_farmer_item), \
             patch('update_featured_status.query') as mock_query, \
             patch('update_featured_status.update_item') as mock_update, \
             patch('update_featured_status.get_email_service') as mock_email_service:
            
            mock_query.return_value = {'Items': mock_products_high_confidence}
            
            # Mock email service
            mock_email = Mock()
            mock_email_service.return_value = mock_email
            
            result = handler(direct_invocation_event, None)
            
            assert result['statusCode'] == 200
            body = json.loads(result['body'])
            assert body['processed'] == 1
            assert body['status_changes'] == 0  # No change
            
            # Verify update was NOT called
            mock_update.assert_not_called()
            
            # Verify email was NOT sent
            mock_email.send_email.assert_not_called()
    
    def test_removes_featured_status_when_confidence_drops(
        self, direct_invocation_event, mock_farmer_item, mock_products_low_confidence
    ):
        """Test that featured status is removed when average confidence drops below threshold."""
        # Set farmer as currently featured
        mock_farmer_item['farmerProfile']['featuredStatus'] = True
        
        with patch('update_featured_status.get_item', return_value=mock_farmer_item), \
             patch('update_featured_status.query') as mock_query, \
             patch('update_featured_status.update_item') as mock_update, \
             patch('update_featured_status.get_email_service') as mock_email_service:
            
            mock_query.return_value = {'Items': mock_products_low_confidence}
            
            # Mock email service
            mock_email = Mock()
            mock_email.send_email.return_value = {'success': True}
            mock_email_service.return_value = mock_email
            
            result = handler(direct_invocation_event, None)
            
            assert result['statusCode'] == 200
            body = json.loads(result['body'])
            assert body['processed'] == 1
            assert body['status_changes'] == 1
            
            # Verify update was called with False
            mock_update.assert_called()
            call_args = mock_update.call_args
            assert call_args[1]['expression_attribute_values'][':status'] is False
            
            # Verify email was sent
            mock_email.send_email.assert_called_once()
    
    def test_respects_notification_preferences(
        self, direct_invocation_event, mock_farmer_item, mock_products_high_confidence
    ):
        """Test that email is not sent if farmer has disabled notifications."""
        # Disable bonus notifications
        mock_farmer_item['notificationPreferences']['farmerBonuses'] = False
        
        with patch('update_featured_status.get_item', return_value=mock_farmer_item), \
             patch('update_featured_status.query') as mock_query, \
             patch('update_featured_status.update_item') as mock_update, \
             patch('update_featured_status.get_email_service') as mock_email_service:
            
            mock_query.return_value = {'Items': mock_products_high_confidence}
            
            # Mock email service
            mock_email = Mock()
            mock_email_service.return_value = mock_email
            
            result = handler(direct_invocation_event, None)
            
            assert result['statusCode'] == 200
            body = json.loads(result['body'])
            assert body['status_changes'] == 1
            
            # Verify email was NOT sent due to preferences
            mock_email.send_email.assert_not_called()
    
    def test_handles_missing_farmer(self, direct_invocation_event):
        """Test handling when farmer is not found."""
        with patch('update_featured_status.get_item', return_value=None):
            result = handler(direct_invocation_event, None)
            
            assert result['statusCode'] == 200
            body = json.loads(result['body'])
            assert body['errors'] == 1
    
    def test_ignores_non_product_stream_events(self):
        """Test that non-Product entities in stream are ignored."""
        event = {
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
        
        with patch('update_featured_status.get_item') as mock_get_item:
            result = handler(event, None)
            
            assert result['statusCode'] == 200
            body = json.loads(result['body'])
            assert body['processed'] == 0
            mock_get_item.assert_not_called()
    
    def test_ignores_non_approved_products_in_stream(self):
        """Test that non-approved products in stream are ignored."""
        event = {
            'Records': [
                {
                    'eventName': 'INSERT',
                    'dynamodb': {
                        'NewImage': {
                            'EntityType': {'S': 'Product'},
                            'productId': {'S': 'product-123'},
                            'farmerId': {'S': 'farmer-456'},
                            'verificationStatus': {'S': 'pending'}
                        }
                    }
                }
            ]
        }
        
        with patch('update_featured_status.get_item') as mock_get_item:
            result = handler(event, None)
            
            assert result['statusCode'] == 200
            body = json.loads(result['body'])
            assert body['processed'] == 0
            mock_get_item.assert_not_called()
    
    def test_processes_multiple_farmers_in_batch(
        self, mock_farmer_item, mock_products_high_confidence
    ):
        """Test processing multiple farmers in a single batch."""
        event = {
            'Records': [
                {
                    'eventName': 'MODIFY',
                    'dynamodb': {
                        'NewImage': {
                            'EntityType': {'S': 'Product'},
                            'productId': {'S': f'product-{i}'},
                            'farmerId': {'S': f'farmer-{i}'},
                            'verificationStatus': {'S': 'approved'},
                            'authenticityConfidence': {'N': '95.0'}
                        }
                    }
                }
                for i in range(3)
            ]
        }
        
        with patch('update_featured_status.get_item', return_value=mock_farmer_item), \
             patch('update_featured_status.query') as mock_query, \
             patch('update_featured_status.update_item') as mock_update, \
             patch('update_featured_status.get_email_service') as mock_email_service:
            
            mock_query.return_value = {'Items': mock_products_high_confidence}
            
            # Mock email service
            mock_email = Mock()
            mock_email.send_email.return_value = {'success': True}
            mock_email_service.return_value = mock_email
            
            result = handler(event, None)
            
            assert result['statusCode'] == 200
            body = json.loads(result['body'])
            assert body['processed'] == 3
            assert body['status_changes'] == 3
    
    def test_handles_database_errors_gracefully(self, direct_invocation_event):
        """Test that database errors are handled gracefully."""
        with patch('update_featured_status.get_item', side_effect=Exception('Database error')):
            result = handler(direct_invocation_event, None)
            
            assert result['statusCode'] == 200
            body = json.loads(result['body'])
            assert body['errors'] == 1
    
    def test_threshold_boundary_91_percent(self):
        """Test that 91% confidence grants featured status (just above threshold)."""
        products = [
            {
                'productId': 'product-1',
                'farmerId': 'farmer-123',
                'verificationStatus': 'approved',
                'authenticityConfidence': Decimal('91.0')
            }
        ]
        
        with patch('update_featured_status.query') as mock_query:
            mock_query.return_value = {'Items': products}
            
            result = calculate_farmer_featured_status('farmer-123')
            
            assert result['should_be_featured'] is True
            assert result['average_confidence'] == 91.0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
