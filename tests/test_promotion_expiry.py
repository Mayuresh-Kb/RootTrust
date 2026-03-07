"""
Unit tests for promotion expiry check Lambda handler.
Tests the scheduled function that checks for expired promotions,
updates their status, and sends summary emails.
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

from promotions.expiry_check import (
    handler,
    check_expired_promotions,
    update_promotion_status,
    send_summary_email
)


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Set up environment variables for tests."""
    monkeypatch.setenv('TABLE_NAME', 'test-table')
    monkeypatch.setenv('SENDER_EMAIL', 'test@example.com')
    monkeypatch.setenv('AWS_REGION', 'us-east-1')


@pytest.fixture
def sample_expired_promotion():
    """Create a sample expired promotion."""
    now = datetime.utcnow()
    past_date = now - timedelta(hours=2)
    
    return {
        'PK': 'PROMOTION#test-promo-1',
        'SK': 'METADATA',
        'EntityType': 'Promotion',
        'promotionId': 'test-promo-1',
        'farmerId': 'farmer-123',
        'productId': 'product-456',
        'budget': 100.0,
        'duration': 7,
        'status': 'active',
        'startDate': (now - timedelta(days=7)).isoformat(),
        'endDate': past_date.isoformat(),
        'aiGeneratedAdCopy': 'Test ad copy',
        'metrics': {
            'views': 150,
            'clicks': 25,
            'conversions': 5,
            'spent': 75.0
        },
        'createdAt': (now - timedelta(days=7)).isoformat(),
        'GSI2PK': 'FARMER#farmer-123',
        'GSI2SK': f"PROMOTION#{(now - timedelta(days=7)).isoformat()}",
        'GSI3PK': 'STATUS#active',
        'GSI3SK': f"PROMOTION#{past_date.isoformat()}"
    }


@pytest.fixture
def sample_active_promotion():
    """Create a sample active (not expired) promotion."""
    now = datetime.utcnow()
    future_date = now + timedelta(days=3)
    
    return {
        'PK': 'PROMOTION#test-promo-2',
        'SK': 'METADATA',
        'EntityType': 'Promotion',
        'promotionId': 'test-promo-2',
        'farmerId': 'farmer-789',
        'productId': 'product-101',
        'budget': 200.0,
        'duration': 14,
        'status': 'active',
        'startDate': (now - timedelta(days=11)).isoformat(),
        'endDate': future_date.isoformat(),
        'aiGeneratedAdCopy': 'Test ad copy 2',
        'metrics': {
            'views': 200,
            'clicks': 40,
            'conversions': 8,
            'spent': 120.0
        },
        'createdAt': (now - timedelta(days=11)).isoformat(),
        'GSI2PK': 'FARMER#farmer-789',
        'GSI2SK': f"PROMOTION#{(now - timedelta(days=11)).isoformat()}",
        'GSI3PK': 'STATUS#active',
        'GSI3SK': f"PROMOTION#{future_date.isoformat()}"
    }


@pytest.fixture
def sample_farmer():
    """Create a sample farmer profile."""
    return {
        'PK': 'USER#farmer-123',
        'SK': 'PROFILE',
        'EntityType': 'User',
        'userId': 'farmer-123',
        'email': 'farmer@example.com',
        'firstName': 'John',
        'lastName': 'Farmer',
        'role': 'farmer'
    }


@pytest.fixture
def sample_product():
    """Create a sample product."""
    return {
        'PK': 'PRODUCT#product-456',
        'SK': 'METADATA',
        'EntityType': 'Product',
        'productId': 'product-456',
        'name': 'Organic Tomatoes',
        'category': 'vegetables',
        'price': 50.0
    }


class TestCheckExpiredPromotions:
    """Tests for check_expired_promotions function."""
    
    @patch('promotions.expiry_check.query')
    def test_finds_expired_promotions(self, mock_query, sample_expired_promotion, sample_active_promotion):
        """Test that expired promotions are correctly identified."""
        mock_query.return_value = {
            'Items': [sample_expired_promotion, sample_active_promotion]
        }
        
        expired = check_expired_promotions()
        
        assert len(expired) == 1
        assert expired[0]['promotionId'] == 'test-promo-1'
        mock_query.assert_called_once()
    
    @patch('promotions.expiry_check.query')
    def test_no_expired_promotions(self, mock_query, sample_active_promotion):
        """Test when no promotions are expired."""
        mock_query.return_value = {
            'Items': [sample_active_promotion]
        }
        
        expired = check_expired_promotions()
        
        assert len(expired) == 0
    
    @patch('promotions.expiry_check.query')
    def test_empty_promotions_list(self, mock_query):
        """Test when there are no active promotions."""
        mock_query.return_value = {
            'Items': []
        }
        
        expired = check_expired_promotions()
        
        assert len(expired) == 0
    
    @patch('promotions.expiry_check.query')
    def test_handles_invalid_date_format(self, mock_query):
        """Test handling of promotions with invalid date formats."""
        invalid_promotion = {
            'promotionId': 'test-promo-invalid',
            'endDate': 'invalid-date-format'
        }
        
        mock_query.return_value = {
            'Items': [invalid_promotion]
        }
        
        expired = check_expired_promotions()
        
        # Should skip invalid promotion and return empty list
        assert len(expired) == 0


class TestUpdatePromotionStatus:
    """Tests for update_promotion_status function."""
    
    @patch('promotions.expiry_check.update_item')
    def test_successful_status_update(self, mock_update_item):
        """Test successful promotion status update."""
        mock_update_item.return_value = True
        
        result = update_promotion_status('test-promo-1')
        
        assert result is True
        mock_update_item.assert_called_once()
        
        # Verify the update parameters
        call_args = mock_update_item.call_args
        assert call_args[1]['pk'] == 'PROMOTION#test-promo-1'
        assert call_args[1]['sk'] == 'METADATA'
        assert 'completed' in str(call_args[1]['expression_attribute_values'])
    
    @patch('promotions.expiry_check.update_item')
    def test_failed_status_update(self, mock_update_item):
        """Test handling of failed status update."""
        mock_update_item.side_effect = Exception('DynamoDB error')
        
        result = update_promotion_status('test-promo-1')
        
        assert result is False


class TestSendSummaryEmail:
    """Tests for send_summary_email function."""
    
    @patch('promotions.expiry_check.get_email_service')
    @patch('promotions.expiry_check.get_item')
    @patch('promotions.expiry_check.get_promotion_summary_email')
    def test_successful_email_send(
        self,
        mock_get_email_template,
        mock_get_item,
        mock_get_email_service,
        sample_expired_promotion,
        sample_farmer,
        sample_product
    ):
        """Test successful summary email sending."""
        # Mock database queries
        def get_item_side_effect(pk, sk):
            if pk == 'USER#farmer-123':
                return sample_farmer
            elif pk == 'PRODUCT#product-456':
                return sample_product
            return None
        
        mock_get_item.side_effect = get_item_side_effect
        
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
        
        result = send_summary_email(sample_expired_promotion)
        
        assert result is True
        mock_email_service.send_email.assert_called_once()
        
        # Verify email parameters
        call_args = mock_email_service.send_email.call_args
        assert call_args[1]['recipient'] == 'farmer@example.com'
        assert call_args[1]['subject'] == 'Promotion Summary'
    
    @patch('promotions.expiry_check.get_item')
    def test_farmer_not_found(self, mock_get_item, sample_expired_promotion):
        """Test handling when farmer profile is not found."""
        mock_get_item.return_value = None
        
        result = send_summary_email(sample_expired_promotion)
        
        assert result is False
    
    @patch('promotions.expiry_check.get_email_service')
    @patch('promotions.expiry_check.get_item')
    @patch('promotions.expiry_check.get_promotion_summary_email')
    def test_email_send_failure(
        self,
        mock_get_email_template,
        mock_get_item,
        mock_get_email_service,
        sample_expired_promotion,
        sample_farmer,
        sample_product
    ):
        """Test handling of email send failure."""
        # Mock database queries
        def get_item_side_effect(pk, sk):
            if pk == 'USER#farmer-123':
                return sample_farmer
            elif pk == 'PRODUCT#product-456':
                return sample_product
            return None
        
        mock_get_item.side_effect = get_item_side_effect
        
        # Mock email template
        mock_get_email_template.return_value = {
            'subject': 'Promotion Summary',
            'html_body': '<html>Summary</html>',
            'text_body': 'Summary'
        }
        
        # Mock email service failure
        mock_email_service = MagicMock()
        mock_email_service.send_email.return_value = {
            'success': False,
            'error_message': 'Email service error'
        }
        mock_get_email_service.return_value = mock_email_service
        
        result = send_summary_email(sample_expired_promotion)
        
        assert result is False


class TestHandler:
    """Tests for the main Lambda handler."""
    
    @patch('promotions.expiry_check.send_summary_email')
    @patch('promotions.expiry_check.update_promotion_status')
    @patch('promotions.expiry_check.check_expired_promotions')
    def test_no_expired_promotions(
        self,
        mock_check_expired,
        mock_update_status,
        mock_send_email,
        mock_env_vars
    ):
        """Test handler when no promotions are expired."""
        mock_check_expired.return_value = []
        
        event = {}
        context = {}
        
        response = handler(event, context)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['processed'] == 0
        assert body['message'] == 'No expired promotions found'
        
        mock_update_status.assert_not_called()
        mock_send_email.assert_not_called()
    
    @patch('promotions.expiry_check.send_summary_email')
    @patch('promotions.expiry_check.update_promotion_status')
    @patch('promotions.expiry_check.check_expired_promotions')
    def test_successful_processing(
        self,
        mock_check_expired,
        mock_update_status,
        mock_send_email,
        mock_env_vars,
        sample_expired_promotion
    ):
        """Test successful processing of expired promotions."""
        mock_check_expired.return_value = [sample_expired_promotion]
        mock_update_status.return_value = True
        mock_send_email.return_value = True
        
        event = {}
        context = {}
        
        response = handler(event, context)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['totalExpired'] == 1
        assert body['statusUpdated'] == 1
        assert body['emailsSent'] == 1
        assert len(body['failedUpdates']) == 0
        assert len(body['failedEmails']) == 0
        
        mock_update_status.assert_called_once_with('test-promo-1')
        mock_send_email.assert_called_once()
    
    @patch('promotions.expiry_check.send_summary_email')
    @patch('promotions.expiry_check.update_promotion_status')
    @patch('promotions.expiry_check.check_expired_promotions')
    def test_partial_failures(
        self,
        mock_check_expired,
        mock_update_status,
        mock_send_email,
        mock_env_vars,
        sample_expired_promotion
    ):
        """Test handling of partial failures in processing."""
        # Create two expired promotions
        promo1 = sample_expired_promotion.copy()
        promo2 = sample_expired_promotion.copy()
        promo2['promotionId'] = 'test-promo-2'
        promo2['PK'] = 'PROMOTION#test-promo-2'
        
        mock_check_expired.return_value = [promo1, promo2]
        
        # First promotion succeeds, second fails status update
        mock_update_status.side_effect = [True, False]
        mock_send_email.return_value = True
        
        event = {}
        context = {}
        
        response = handler(event, context)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['totalExpired'] == 2
        assert body['statusUpdated'] == 1
        assert body['emailsSent'] == 1
        assert len(body['failedUpdates']) == 1
        assert 'test-promo-2' in body['failedUpdates']
    
    @patch('promotions.expiry_check.send_summary_email')
    @patch('promotions.expiry_check.update_promotion_status')
    @patch('promotions.expiry_check.check_expired_promotions')
    def test_email_failure_after_status_update(
        self,
        mock_check_expired,
        mock_update_status,
        mock_send_email,
        mock_env_vars,
        sample_expired_promotion
    ):
        """Test handling when email fails after successful status update."""
        mock_check_expired.return_value = [sample_expired_promotion]
        mock_update_status.return_value = True
        mock_send_email.return_value = False
        
        event = {}
        context = {}
        
        response = handler(event, context)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['totalExpired'] == 1
        assert body['statusUpdated'] == 1
        assert body['emailsSent'] == 0
        assert len(body['failedEmails']) == 1
        assert 'test-promo-1' in body['failedEmails']
    
    @patch('promotions.expiry_check.check_expired_promotions')
    def test_exception_handling(self, mock_check_expired, mock_env_vars):
        """Test handling of unexpected exceptions."""
        mock_check_expired.side_effect = Exception('Unexpected error')
        
        event = {}
        context = {}
        
        response = handler(event, context)
        
        assert response['statusCode'] == 500
        body = json.loads(response['body'])
        assert 'error' in body
        assert body['error']['code'] == 'INTERNAL_ERROR'


class TestIntegration:
    """Integration tests for the complete workflow."""
    
    @patch('promotions.expiry_check.get_email_service')
    @patch('promotions.expiry_check.get_promotion_summary_email')
    @patch('promotions.expiry_check.get_item')
    @patch('promotions.expiry_check.update_item')
    @patch('promotions.expiry_check.query')
    def test_complete_workflow(
        self,
        mock_query,
        mock_update_item,
        mock_get_item,
        mock_get_email_template,
        mock_get_email_service,
        mock_env_vars,
        sample_expired_promotion,
        sample_farmer,
        sample_product
    ):
        """Test the complete workflow from check to email."""
        # Mock query for expired promotions
        mock_query.return_value = {
            'Items': [sample_expired_promotion]
        }
        
        # Mock database queries
        def get_item_side_effect(pk, sk):
            if pk == 'USER#farmer-123':
                return sample_farmer
            elif pk == 'PRODUCT#product-456':
                return sample_product
            return None
        
        mock_get_item.side_effect = get_item_side_effect
        
        # Mock update
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
        
        event = {}
        context = {}
        
        response = handler(event, context)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['totalExpired'] == 1
        assert body['statusUpdated'] == 1
        assert body['emailsSent'] == 1
        
        # Verify all steps were called
        mock_query.assert_called_once()
        mock_update_item.assert_called_once()
        mock_email_service.send_email.assert_called_once()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
