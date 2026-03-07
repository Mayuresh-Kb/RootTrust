"""
Unit tests for promotion update endpoint.
"""
import json
import pytest
import os
import sys
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend', 'shared'))

from shared.constants import UserRole, PromotionStatus


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Set up environment variables for tests."""
    monkeypatch.setenv('DYNAMODB_TABLE_NAME', 'RootTrustData-test')
    monkeypatch.setenv('AWS_REGION', 'us-east-1')
    monkeypatch.setenv('JWT_SECRET_KEY', 'test-secret-key-12345678')
    monkeypatch.setenv('SENDER_EMAIL', 'noreply@roottrust.com')


@pytest.fixture
def farmer_token_payload():
    """Mock farmer JWT token payload."""
    return {
        'userId': 'farmer-123',
        'email': 'farmer@example.com',
        'role': 'farmer'
    }


@pytest.fixture
def consumer_token_payload():
    """Mock consumer JWT token payload."""
    return {
        'userId': 'consumer-123',
        'email': 'consumer@example.com',
        'role': 'consumer'
    }


@pytest.fixture
def mock_promotion():
    """Mock promotion data."""
    return {
        'PK': 'PROMOTION#promo-123',
        'SK': 'METADATA',
        'promotionId': 'promo-123',
        'farmerId': 'farmer-123',
        'productId': 'product-123',
        'budget': 500.0,
        'duration': 7,
        'status': 'active',
        'startDate': '2024-01-01T00:00:00Z',
        'endDate': '2024-01-08T00:00:00Z',
        'metrics': {
            'views': 1000,
            'clicks': 150,
            'conversions': 25,
            'spent': 450.0
        },
        'aiGeneratedAdCopy': 'Test ad copy',
        'GSI3PK': 'STATUS#active'
    }


@pytest.fixture
def mock_farmer():
    """Mock farmer data."""
    return {
        'PK': 'USER#farmer-123',
        'SK': 'PROFILE',
        'userId': 'farmer-123',
        'email': 'farmer@example.com',
        'firstName': 'John',
        'role': 'farmer'
    }


@pytest.fixture
def mock_product():
    """Mock product data."""
    return {
        'PK': 'PRODUCT#product-123',
        'SK': 'METADATA',
        'productId': 'product-123',
        'name': 'Organic Tomatoes',
        'farmerId': 'farmer-123'
    }


class TestPromotionUpdate:
    """Test cases for promotion update endpoint."""
    
    def test_update_promotion_to_paused_success(
        self, mock_env_vars, farmer_token_payload, mock_promotion
    ):
        """Test successfully pausing an active promotion."""
        from promotions.update_promotion import handler
        
        with patch('promotions.update_promotion.get_user_from_token') as mock_auth, \
             patch('promotions.update_promotion.get_item') as mock_get, \
             patch('promotions.update_promotion.update_item') as mock_update:
            
            mock_auth.return_value = farmer_token_payload
            mock_get.return_value = mock_promotion
            mock_update.return_value = {}
            
            event = {
                'headers': {
                    'Authorization': 'Bearer valid-token'
                },
                'pathParameters': {
                    'promotionId': 'promo-123'
                },
                'body': json.dumps({
                    'status': 'paused'
                })
            }
            
            response = handler(event, None)
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert body['promotionId'] == 'promo-123'
            assert body['status'] == 'paused'
            assert body['summarySent'] == False
            
            # Verify update_item was called with correct parameters
            mock_update.assert_called_once()
            call_args = mock_update.call_args[1]
            assert call_args['pk'] == 'PROMOTION#promo-123'
            assert call_args['expression_attribute_values'][':status'] == 'paused'
    
    def test_update_promotion_to_cancelled_sends_summary(
        self, mock_env_vars, farmer_token_payload, mock_promotion, 
        mock_farmer, mock_product
    ):
        """Test cancelling a promotion sends summary email."""
        from promotions.update_promotion import handler
        
        with patch('promotions.update_promotion.get_user_from_token') as mock_auth, \
             patch('promotions.update_promotion.get_item') as mock_get, \
             patch('promotions.update_promotion.update_item') as mock_update, \
             patch('promotions.update_promotion.get_email_service') as mock_email_service:
            
            mock_auth.return_value = farmer_token_payload
            mock_get.side_effect = [mock_promotion, mock_farmer, mock_product]
            mock_update.return_value = {}
            
            # Mock email service
            mock_service = MagicMock()
            mock_service.send_email.return_value = {'success': True, 'message_id': 'msg-123'}
            mock_email_service.return_value = mock_service
            
            event = {
                'headers': {
                    'Authorization': 'Bearer valid-token'
                },
                'pathParameters': {
                    'promotionId': 'promo-123'
                },
                'body': json.dumps({
                    'status': 'cancelled'
                })
            }
            
            response = handler(event, None)
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert body['status'] == 'cancelled'
            assert body['summarySent'] == True
            
            # Verify email was sent
            mock_service.send_email.assert_called_once()
            email_call = mock_service.send_email.call_args[1]
            assert email_call['recipient'] == 'farmer@example.com'
            assert 'Promotion Summary' in email_call['subject']
    
    def test_update_promotion_to_completed_sends_summary(
        self, mock_env_vars, farmer_token_payload, mock_promotion,
        mock_farmer, mock_product
    ):
        """Test completing a promotion sends summary email."""
        from promotions.update_promotion import handler
        
        with patch('promotions.update_promotion.get_user_from_token') as mock_auth, \
             patch('promotions.update_promotion.get_item') as mock_get, \
             patch('promotions.update_promotion.update_item') as mock_update, \
             patch('promotions.update_promotion.get_email_service') as mock_email_service:
            
            mock_auth.return_value = farmer_token_payload
            mock_get.side_effect = [mock_promotion, mock_farmer, mock_product]
            mock_update.return_value = {}
            
            # Mock email service
            mock_service = MagicMock()
            mock_service.send_email.return_value = {'success': True, 'message_id': 'msg-123'}
            mock_email_service.return_value = mock_service
            
            event = {
                'headers': {
                    'Authorization': 'Bearer valid-token'
                },
                'pathParameters': {
                    'promotionId': 'promo-123'
                },
                'body': json.dumps({
                    'status': 'completed'
                })
            }
            
            response = handler(event, None)
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert body['status'] == 'completed'
            assert body['summarySent'] == True
            
            # Verify email was sent
            mock_service.send_email.assert_called_once()
    
    def test_update_promotion_missing_auth_header(self, mock_env_vars):
        """Test promotion update without authorization header."""
        from promotions.update_promotion import handler
        
        event = {
            'headers': {},
            'pathParameters': {
                'promotionId': 'promo-123'
            },
            'body': json.dumps({
                'status': 'paused'
            })
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 401
        body = json.loads(response['body'])
        assert body['error']['code'] == 'UNAUTHORIZED'
    
    def test_update_promotion_consumer_forbidden(
        self, mock_env_vars, consumer_token_payload
    ):
        """Test that consumers cannot update promotions."""
        from promotions.update_promotion import handler
        
        with patch('promotions.update_promotion.get_user_from_token') as mock_auth:
            mock_auth.return_value = consumer_token_payload
            
            event = {
                'headers': {
                    'Authorization': 'Bearer consumer-token'
                },
                'pathParameters': {
                    'promotionId': 'promo-123'
                },
                'body': json.dumps({
                    'status': 'paused'
                })
            }
            
            response = handler(event, None)
            
            assert response['statusCode'] == 403
            body = json.loads(response['body'])
            assert body['error']['code'] == 'FORBIDDEN'
    
    def test_update_promotion_missing_promotion_id(
        self, mock_env_vars, farmer_token_payload
    ):
        """Test promotion update without promotion ID in path."""
        from promotions.update_promotion import handler
        
        with patch('promotions.update_promotion.get_user_from_token') as mock_auth:
            mock_auth.return_value = farmer_token_payload
            
            event = {
                'headers': {
                    'Authorization': 'Bearer valid-token'
                },
                'pathParameters': {},
                'body': json.dumps({
                    'status': 'paused'
                })
            }
            
            response = handler(event, None)
            
            assert response['statusCode'] == 400
            body = json.loads(response['body'])
            assert body['error']['code'] == 'INVALID_REQUEST'
    
    def test_update_promotion_invalid_json(
        self, mock_env_vars, farmer_token_payload
    ):
        """Test promotion update with invalid JSON."""
        from promotions.update_promotion import handler
        
        with patch('promotions.update_promotion.get_user_from_token') as mock_auth:
            mock_auth.return_value = farmer_token_payload
            
            event = {
                'headers': {
                    'Authorization': 'Bearer valid-token'
                },
                'pathParameters': {
                    'promotionId': 'promo-123'
                },
                'body': 'invalid json {'
            }
            
            response = handler(event, None)
            
            assert response['statusCode'] == 400
            body = json.loads(response['body'])
            assert body['error']['code'] == 'INVALID_JSON'
    
    def test_update_promotion_invalid_status(
        self, mock_env_vars, farmer_token_payload
    ):
        """Test promotion update with invalid status value."""
        from promotions.update_promotion import handler
        
        with patch('promotions.update_promotion.get_user_from_token') as mock_auth:
            mock_auth.return_value = farmer_token_payload
            
            event = {
                'headers': {
                    'Authorization': 'Bearer valid-token'
                },
                'pathParameters': {
                    'promotionId': 'promo-123'
                },
                'body': json.dumps({
                    'status': 'invalid_status'
                })
            }
            
            response = handler(event, None)
            
            assert response['statusCode'] == 400
            body = json.loads(response['body'])
            assert body['error']['code'] == 'VALIDATION_ERROR'
    
    def test_update_promotion_not_found(
        self, mock_env_vars, farmer_token_payload
    ):
        """Test updating non-existent promotion."""
        from promotions.update_promotion import handler
        
        with patch('promotions.update_promotion.get_user_from_token') as mock_auth, \
             patch('promotions.update_promotion.get_item') as mock_get:
            
            mock_auth.return_value = farmer_token_payload
            mock_get.return_value = None  # Promotion not found
            
            event = {
                'headers': {
                    'Authorization': 'Bearer valid-token'
                },
                'pathParameters': {
                    'promotionId': 'promo-999'
                },
                'body': json.dumps({
                    'status': 'paused'
                })
            }
            
            response = handler(event, None)
            
            assert response['statusCode'] == 404
            body = json.loads(response['body'])
            assert body['error']['code'] == 'NOT_FOUND'
    
    def test_update_promotion_not_owner(
        self, mock_env_vars, farmer_token_payload, mock_promotion
    ):
        """Test updating promotion owned by another farmer."""
        from promotions.update_promotion import handler
        
        with patch('promotions.update_promotion.get_user_from_token') as mock_auth, \
             patch('promotions.update_promotion.get_item') as mock_get:
            
            mock_auth.return_value = farmer_token_payload
            
            # Promotion owned by different farmer
            other_farmer_promotion = mock_promotion.copy()
            other_farmer_promotion['farmerId'] = 'other-farmer-456'
            mock_get.return_value = other_farmer_promotion
            
            event = {
                'headers': {
                    'Authorization': 'Bearer valid-token'
                },
                'pathParameters': {
                    'promotionId': 'promo-123'
                },
                'body': json.dumps({
                    'status': 'paused'
                })
            }
            
            response = handler(event, None)
            
            assert response['statusCode'] == 403
            body = json.loads(response['body'])
            assert body['error']['code'] == 'FORBIDDEN'
            assert 'own promotions' in body['error']['message'].lower()
    
    def test_update_promotion_dynamodb_error(
        self, mock_env_vars, farmer_token_payload, mock_promotion
    ):
        """Test promotion update when DynamoDB fails."""
        from promotions.update_promotion import handler
        
        with patch('promotions.update_promotion.get_user_from_token') as mock_auth, \
             patch('promotions.update_promotion.get_item') as mock_get, \
             patch('promotions.update_promotion.update_item') as mock_update:
            
            mock_auth.return_value = farmer_token_payload
            mock_get.return_value = mock_promotion
            mock_update.side_effect = Exception('DynamoDB error')
            
            event = {
                'headers': {
                    'Authorization': 'Bearer valid-token'
                },
                'pathParameters': {
                    'promotionId': 'promo-123'
                },
                'body': json.dumps({
                    'status': 'paused'
                })
            }
            
            response = handler(event, None)
            
            assert response['statusCode'] == 503
            body = json.loads(response['body'])
            assert body['error']['code'] == 'SERVICE_UNAVAILABLE'
    
    def test_update_promotion_email_failure_does_not_fail_request(
        self, mock_env_vars, farmer_token_payload, mock_promotion,
        mock_farmer, mock_product
    ):
        """Test that email failure doesn't cause the update to fail."""
        from promotions.update_promotion import handler
        
        with patch('promotions.update_promotion.get_user_from_token') as mock_auth, \
             patch('promotions.update_promotion.get_item') as mock_get, \
             patch('promotions.update_promotion.update_item') as mock_update, \
             patch('promotions.update_promotion.get_email_service') as mock_email_service:
            
            mock_auth.return_value = farmer_token_payload
            mock_get.side_effect = [mock_promotion, mock_farmer, mock_product]
            mock_update.return_value = {}
            
            # Mock email service to fail
            mock_service = MagicMock()
            mock_service.send_email.return_value = {
                'success': False,
                'error_message': 'Email service unavailable'
            }
            mock_email_service.return_value = mock_service
            
            event = {
                'headers': {
                    'Authorization': 'Bearer valid-token'
                },
                'pathParameters': {
                    'promotionId': 'promo-123'
                },
                'body': json.dumps({
                    'status': 'cancelled'
                })
            }
            
            response = handler(event, None)
            
            # Should still succeed even though email failed
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert body['status'] == 'cancelled'
    
    def test_update_promotion_reactivate_from_paused(
        self, mock_env_vars, farmer_token_payload, mock_promotion
    ):
        """Test reactivating a paused promotion."""
        from promotions.update_promotion import handler
        
        with patch('promotions.update_promotion.get_user_from_token') as mock_auth, \
             patch('promotions.update_promotion.get_item') as mock_get, \
             patch('promotions.update_promotion.update_item') as mock_update:
            
            mock_auth.return_value = farmer_token_payload
            
            # Paused promotion
            paused_promotion = mock_promotion.copy()
            paused_promotion['status'] = 'paused'
            mock_get.return_value = paused_promotion
            mock_update.return_value = {}
            
            event = {
                'headers': {
                    'Authorization': 'Bearer valid-token'
                },
                'pathParameters': {
                    'promotionId': 'promo-123'
                },
                'body': json.dumps({
                    'status': 'active'
                })
            }
            
            response = handler(event, None)
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert body['status'] == 'active'
            assert body['summarySent'] == False  # No summary when reactivating
    
    def test_update_already_cancelled_promotion_no_summary(
        self, mock_env_vars, farmer_token_payload, mock_promotion
    ):
        """Test updating already cancelled promotion doesn't send another summary."""
        from promotions.update_promotion import handler
        
        with patch('promotions.update_promotion.get_user_from_token') as mock_auth, \
             patch('promotions.update_promotion.get_item') as mock_get, \
             patch('promotions.update_promotion.update_item') as mock_update, \
             patch('promotions.update_promotion.get_email_service') as mock_email_service:
            
            mock_auth.return_value = farmer_token_payload
            
            # Already cancelled promotion
            cancelled_promotion = mock_promotion.copy()
            cancelled_promotion['status'] = 'cancelled'
            mock_get.return_value = cancelled_promotion
            mock_update.return_value = {}
            
            mock_service = MagicMock()
            mock_email_service.return_value = mock_service
            
            event = {
                'headers': {
                    'Authorization': 'Bearer valid-token'
                },
                'pathParameters': {
                    'promotionId': 'promo-123'
                },
                'body': json.dumps({
                    'status': 'completed'
                })
            }
            
            response = handler(event, None)
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert body['summarySent'] == False
            
            # Verify email was NOT sent
            mock_service.send_email.assert_not_called()
    
    def test_update_promotion_gsi3pk_updated(
        self, mock_env_vars, farmer_token_payload, mock_promotion
    ):
        """Test that GSI3PK is updated when status changes."""
        from promotions.update_promotion import handler
        
        with patch('promotions.update_promotion.get_user_from_token') as mock_auth, \
             patch('promotions.update_promotion.get_item') as mock_get, \
             patch('promotions.update_promotion.update_item') as mock_update:
            
            mock_auth.return_value = farmer_token_payload
            mock_get.return_value = mock_promotion
            mock_update.return_value = {}
            
            event = {
                'headers': {
                    'Authorization': 'Bearer valid-token'
                },
                'pathParameters': {
                    'promotionId': 'promo-123'
                },
                'body': json.dumps({
                    'status': 'paused'
                })
            }
            
            response = handler(event, None)
            
            assert response['statusCode'] == 200
            
            # Verify GSI3PK was updated
            call_args = mock_update.call_args[1]
            assert call_args['expression_attribute_values'][':gsi3pk'] == 'STATUS#paused'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
