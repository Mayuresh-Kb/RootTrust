"""
Integration test for promotion expiry check functionality.
This test demonstrates the complete workflow of the EventBridge-triggered Lambda.
"""
import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend', 'promotions'))

from promotions.expiry_check import handler


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Set up environment variables for tests."""
    monkeypatch.setenv('TABLE_NAME', 'test-table')
    monkeypatch.setenv('SENDER_EMAIL', 'test@example.com')
    monkeypatch.setenv('AWS_REGION', 'us-east-1')


@pytest.fixture
def eventbridge_event():
    """Create a sample EventBridge scheduled event."""
    return {
        "version": "0",
        "id": "test-event-id",
        "detail-type": "Scheduled Event",
        "source": "aws.events",
        "account": "123456789012",
        "time": datetime.utcnow().isoformat(),
        "region": "us-east-1",
        "resources": [
            "arn:aws:events:us-east-1:123456789012:rule/RootTrust-Promotion-ExpiryCheck"
        ],
        "detail": {}
    }


def create_promotion(promotion_id, hours_until_expiry):
    """Helper to create a promotion with specified expiry time."""
    now = datetime.utcnow()
    end_date = now + timedelta(hours=hours_until_expiry)
    start_date = now - timedelta(days=7)
    
    return {
        'PK': f'PROMOTION#{promotion_id}',
        'SK': 'METADATA',
        'EntityType': 'Promotion',
        'promotionId': promotion_id,
        'farmerId': f'farmer-{promotion_id}',
        'productId': f'product-{promotion_id}',
        'budget': 100.0,
        'duration': 7,
        'status': 'active',
        'startDate': start_date.isoformat(),
        'endDate': end_date.isoformat(),
        'aiGeneratedAdCopy': f'Ad copy for {promotion_id}',
        'metrics': {
            'views': 100,
            'clicks': 20,
            'conversions': 5,
            'spent': 50.0
        },
        'createdAt': start_date.isoformat(),
        'GSI2PK': f'FARMER#farmer-{promotion_id}',
        'GSI2SK': f"PROMOTION#{start_date.isoformat()}",
        'GSI3PK': 'STATUS#active',
        'GSI3SK': f"PROMOTION#{end_date.isoformat()}"
    }


class TestPromotionExpiryIntegration:
    """Integration tests for the promotion expiry check workflow."""
    
    @patch('promotions.expiry_check.get_email_service')
    @patch('promotions.expiry_check.get_promotion_summary_email')
    @patch('promotions.expiry_check.get_item')
    @patch('promotions.expiry_check.update_item')
    @patch('promotions.expiry_check.query')
    def test_eventbridge_triggered_expiry_check(
        self,
        mock_query,
        mock_update_item,
        mock_get_item,
        mock_get_email_template,
        mock_get_email_service,
        mock_env_vars,
        eventbridge_event
    ):
        """Test the complete workflow triggered by EventBridge."""
        # Create test data: 2 expired, 1 active
        expired_promo_1 = create_promotion('promo-1', -2)  # Expired 2 hours ago
        expired_promo_2 = create_promotion('promo-2', -1)  # Expired 1 hour ago
        active_promo = create_promotion('promo-3', 24)     # Expires in 24 hours
        
        # Mock query to return all promotions
        mock_query.return_value = {
            'Items': [expired_promo_1, expired_promo_2, active_promo]
        }
        
        # Mock database queries for farmer and product
        def get_item_side_effect(pk, sk):
            if pk.startswith('USER#'):
                farmer_id = pk.split('#')[1]
                return {
                    'PK': pk,
                    'SK': 'PROFILE',
                    'userId': farmer_id,
                    'email': f'{farmer_id}@example.com',
                    'firstName': 'Test',
                    'lastName': 'Farmer',
                    'role': 'farmer'
                }
            elif pk.startswith('PRODUCT#'):
                product_id = pk.split('#')[1]
                return {
                    'PK': pk,
                    'SK': 'METADATA',
                    'productId': product_id,
                    'name': f'Product {product_id}',
                    'category': 'vegetables',
                    'price': 50.0
                }
            return None
        
        mock_get_item.side_effect = get_item_side_effect
        mock_update_item.return_value = True
        
        # Mock email template
        mock_get_email_template.return_value = {
            'subject': 'Promotion Summary',
            'html_body': '<html>Summary</html>',
            'text_body': 'Summary'
        }
        
        # Mock email service
        mock_email_service = MagicMock()
        mock_email_service.send_email.return_value = {'success': True}
        mock_get_email_service.return_value = mock_email_service
        
        # Execute handler with EventBridge event
        response = handler(eventbridge_event, {})
        
        # Verify response
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        
        # Should process 2 expired promotions
        assert body['totalExpired'] == 2
        assert body['statusUpdated'] == 2
        assert body['emailsSent'] == 2
        assert len(body['failedUpdates']) == 0
        assert len(body['failedEmails']) == 0
        
        # Verify query was called to get active promotions
        mock_query.assert_called_once()
        
        # Verify status updates were called for both expired promotions
        assert mock_update_item.call_count == 2
        
        # Verify emails were sent for both expired promotions
        assert mock_email_service.send_email.call_count == 2
    
    @patch('promotions.expiry_check.query')
    def test_no_action_when_no_expired_promotions(
        self,
        mock_query,
        mock_env_vars,
        eventbridge_event
    ):
        """Test that no action is taken when no promotions are expired."""
        # Create only active promotions
        active_promo_1 = create_promotion('promo-1', 24)
        active_promo_2 = create_promotion('promo-2', 48)
        
        mock_query.return_value = {
            'Items': [active_promo_1, active_promo_2]
        }
        
        response = handler(eventbridge_event, {})
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        
        assert body['processed'] == 0
        assert body['message'] == 'No expired promotions found'
    
    @patch('promotions.expiry_check.get_email_service')
    @patch('promotions.expiry_check.get_promotion_summary_email')
    @patch('promotions.expiry_check.get_item')
    @patch('promotions.expiry_check.update_item')
    @patch('promotions.expiry_check.query')
    def test_handles_mixed_success_and_failure(
        self,
        mock_query,
        mock_update_item,
        mock_get_item,
        mock_get_email_template,
        mock_get_email_service,
        mock_env_vars,
        eventbridge_event
    ):
        """Test handling when some operations succeed and others fail."""
        # Create 3 expired promotions
        expired_promo_1 = create_promotion('promo-1', -2)
        expired_promo_2 = create_promotion('promo-2', -1)
        expired_promo_3 = create_promotion('promo-3', -3)
        
        mock_query.return_value = {
            'Items': [expired_promo_1, expired_promo_2, expired_promo_3]
        }
        
        # Mock database queries
        def get_item_side_effect(pk, sk):
            if pk.startswith('USER#'):
                # Farmer for promo-2 not found
                if 'farmer-promo-2' in pk:
                    return None
                farmer_id = pk.split('#')[1]
                return {
                    'PK': pk,
                    'SK': 'PROFILE',
                    'userId': farmer_id,
                    'email': f'{farmer_id}@example.com',
                    'firstName': 'Test',
                    'lastName': 'Farmer',
                    'role': 'farmer'
                }
            elif pk.startswith('PRODUCT#'):
                product_id = pk.split('#')[1]
                return {
                    'PK': pk,
                    'SK': 'METADATA',
                    'productId': product_id,
                    'name': f'Product {product_id}',
                    'category': 'vegetables',
                    'price': 50.0
                }
            return None
        
        mock_get_item.side_effect = get_item_side_effect
        
        # Status update fails for promo-3
        def update_item_side_effect(*args, **kwargs):
            if 'promo-3' in kwargs.get('pk', ''):
                raise Exception('DynamoDB error')
            return True
        
        mock_update_item.side_effect = update_item_side_effect
        
        # Mock email template
        mock_get_email_template.return_value = {
            'subject': 'Promotion Summary',
            'html_body': '<html>Summary</html>',
            'text_body': 'Summary'
        }
        
        # Mock email service
        mock_email_service = MagicMock()
        mock_email_service.send_email.return_value = {'success': True}
        mock_get_email_service.return_value = mock_email_service
        
        response = handler(eventbridge_event, {})
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        
        # Should find 3 expired promotions
        assert body['totalExpired'] == 3
        
        # promo-1 succeeds completely
        # promo-2 status update succeeds but email fails (farmer not found)
        # promo-3 fails at status update
        assert body['statusUpdated'] == 2
        assert body['emailsSent'] == 1
        
        # Should have failures recorded
        assert len(body['failedUpdates']) == 1
        assert 'promo-3' in body['failedUpdates']
        assert len(body['failedEmails']) == 1
        assert 'promo-2' in body['failedEmails']


class TestEventBridgeScheduleConfiguration:
    """Tests to verify EventBridge schedule configuration."""
    
    def test_handler_accepts_eventbridge_event_format(self, mock_env_vars, eventbridge_event):
        """Test that handler accepts EventBridge scheduled event format."""
        with patch('promotions.expiry_check.check_expired_promotions') as mock_check:
            mock_check.return_value = []
            
            # Should not raise any errors
            response = handler(eventbridge_event, {})
            
            assert response['statusCode'] == 200
    
    def test_handler_works_with_empty_event(self, mock_env_vars):
        """Test that handler works even with empty event (for manual invocation)."""
        with patch('promotions.expiry_check.check_expired_promotions') as mock_check:
            mock_check.return_value = []
            
            # Should work with empty event
            response = handler({}, {})
            
            assert response['statusCode'] == 200


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
