"""
Unit tests for promotion metrics endpoint.
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
    monkeypatch.setenv('JWT_SECRET_KEY', 'test-secret-key-12345678')


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
    """Mock promotion data with metrics."""
    now = datetime.utcnow()
    return {
        'PK': 'PROMOTION#promo-123',
        'SK': 'METADATA',
        'promotionId': 'promo-123',
        'farmerId': 'farmer-123',
        'productId': 'product-123',
        'budget': 500.0,
        'duration': 7,
        'status': 'active',
        'startDate': now.isoformat(),
        'endDate': (now + timedelta(days=7)).isoformat(),
        'metrics': {
            'views': 150,
            'clicks': 30,
            'conversions': 8,
            'spent': 75.50
        },
        'aiGeneratedAdCopy': 'Special promotion!',
        'createdAt': now.isoformat()
    }


@pytest.fixture
def mock_promotion_no_metrics():
    """Mock promotion data without metrics."""
    now = datetime.utcnow()
    return {
        'PK': 'PROMOTION#promo-456',
        'SK': 'METADATA',
        'promotionId': 'promo-456',
        'farmerId': 'farmer-123',
        'productId': 'product-456',
        'budget': 300.0,
        'duration': 5,
        'status': 'active',
        'startDate': now.isoformat(),
        'endDate': (now + timedelta(days=5)).isoformat(),
        'aiGeneratedAdCopy': 'New promotion!',
        'createdAt': now.isoformat()
    }


class TestPromotionMetrics:
    """Test cases for promotion metrics endpoint."""
    
    def test_get_promotion_metrics_success(
        self, mock_env_vars, farmer_token_payload, mock_promotion
    ):
        """Test successful retrieval of promotion metrics."""
        # Import after env vars are set
        from promotions.get_promotion_metrics import handler
        
        # Mock dependencies
        with patch('promotions.get_promotion_metrics.get_user_from_token') as mock_auth, \
             patch('promotions.get_promotion_metrics.get_item') as mock_get:
            
            # Setup mocks
            mock_auth.return_value = farmer_token_payload
            mock_get.return_value = mock_promotion
            
            # Create event
            event = {
                'headers': {
                    'Authorization': 'Bearer valid-token'
                },
                'pathParameters': {
                    'promotionId': 'promo-123'
                }
            }
            
            # Call handler
            response = handler(event, None)
            
            # Assertions
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert 'promotionId' in body
            assert body['promotionId'] == 'promo-123'
            assert 'metrics' in body
            
            metrics = body['metrics']
            assert metrics['views'] == 150
            assert metrics['clicks'] == 30
            assert metrics['conversions'] == 8
            assert metrics['spent'] == 75.50
            
            # Verify get_item was called with correct parameters
            mock_get.assert_called_once_with('PROMOTION#promo-123', 'METADATA')
    
    def test_get_promotion_metrics_no_metrics_field(
        self, mock_env_vars, farmer_token_payload, mock_promotion_no_metrics
    ):
        """Test retrieval when promotion has no metrics field (returns defaults)."""
        from promotions.get_promotion_metrics import handler
        
        with patch('promotions.get_promotion_metrics.get_user_from_token') as mock_auth, \
             patch('promotions.get_promotion_metrics.get_item') as mock_get:
            
            mock_auth.return_value = farmer_token_payload
            mock_get.return_value = mock_promotion_no_metrics
            
            event = {
                'headers': {
                    'Authorization': 'Bearer valid-token'
                },
                'pathParameters': {
                    'promotionId': 'promo-456'
                }
            }
            
            response = handler(event, None)
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            
            # Should return default metrics
            metrics = body['metrics']
            assert metrics['views'] == 0
            assert metrics['clicks'] == 0
            assert metrics['conversions'] == 0
            assert metrics['spent'] == 0.0
    
    def test_get_promotion_metrics_missing_auth_header(self, mock_env_vars):
        """Test metrics retrieval without authorization header."""
        from promotions.get_promotion_metrics import handler
        
        event = {
            'headers': {},
            'pathParameters': {
                'promotionId': 'promo-123'
            }
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 401
        body = json.loads(response['body'])
        assert body['error']['code'] == 'UNAUTHORIZED'
    
    def test_get_promotion_metrics_invalid_token(self, mock_env_vars):
        """Test metrics retrieval with invalid JWT token."""
        from promotions.get_promotion_metrics import handler
        
        with patch('promotions.get_promotion_metrics.get_user_from_token') as mock_auth:
            mock_auth.side_effect = Exception('Invalid token')
            
            event = {
                'headers': {
                    'Authorization': 'Bearer invalid-token'
                },
                'pathParameters': {
                    'promotionId': 'promo-123'
                }
            }
            
            response = handler(event, None)
            
            assert response['statusCode'] == 401
            body = json.loads(response['body'])
            assert body['error']['code'] == 'INVALID_TOKEN'
    
    def test_get_promotion_metrics_consumer_forbidden(
        self, mock_env_vars, consumer_token_payload
    ):
        """Test that consumers cannot view promotion metrics."""
        from promotions.get_promotion_metrics import handler
        
        with patch('promotions.get_promotion_metrics.get_user_from_token') as mock_auth:
            mock_auth.return_value = consumer_token_payload
            
            event = {
                'headers': {
                    'Authorization': 'Bearer consumer-token'
                },
                'pathParameters': {
                    'promotionId': 'promo-123'
                }
            }
            
            response = handler(event, None)
            
            assert response['statusCode'] == 403
            body = json.loads(response['body'])
            assert body['error']['code'] == 'FORBIDDEN'
            assert 'farmers' in body['error']['message'].lower()
    
    def test_get_promotion_metrics_missing_promotion_id(
        self, mock_env_vars, farmer_token_payload
    ):
        """Test metrics retrieval without promotionId parameter."""
        from promotions.get_promotion_metrics import handler
        
        with patch('promotions.get_promotion_metrics.get_user_from_token') as mock_auth:
            mock_auth.return_value = farmer_token_payload
            
            event = {
                'headers': {
                    'Authorization': 'Bearer valid-token'
                },
                'pathParameters': {}
            }
            
            response = handler(event, None)
            
            assert response['statusCode'] == 400
            body = json.loads(response['body'])
            assert body['error']['code'] == 'INVALID_REQUEST'
            assert 'promotionId' in body['error']['message']
    
    def test_get_promotion_metrics_promotion_not_found(
        self, mock_env_vars, farmer_token_payload
    ):
        """Test metrics retrieval for non-existent promotion."""
        from promotions.get_promotion_metrics import handler
        
        with patch('promotions.get_promotion_metrics.get_user_from_token') as mock_auth, \
             patch('promotions.get_promotion_metrics.get_item') as mock_get:
            
            mock_auth.return_value = farmer_token_payload
            mock_get.return_value = None  # Promotion not found
            
            event = {
                'headers': {
                    'Authorization': 'Bearer valid-token'
                },
                'pathParameters': {
                    'promotionId': 'nonexistent-promo'
                }
            }
            
            response = handler(event, None)
            
            assert response['statusCode'] == 404
            body = json.loads(response['body'])
            assert body['error']['code'] == 'NOT_FOUND'
            assert 'promotion' in body['error']['message'].lower()
    
    def test_get_promotion_metrics_not_owner(
        self, mock_env_vars, farmer_token_payload, mock_promotion
    ):
        """Test metrics retrieval for promotion owned by another farmer."""
        from promotions.get_promotion_metrics import handler
        
        with patch('promotions.get_promotion_metrics.get_user_from_token') as mock_auth, \
             patch('promotions.get_promotion_metrics.get_item') as mock_get:
            
            # Different farmer trying to access
            other_farmer_payload = farmer_token_payload.copy()
            other_farmer_payload['userId'] = 'other-farmer-456'
            
            mock_auth.return_value = other_farmer_payload
            mock_get.return_value = mock_promotion  # Owned by farmer-123
            
            event = {
                'headers': {
                    'Authorization': 'Bearer valid-token'
                },
                'pathParameters': {
                    'promotionId': 'promo-123'
                }
            }
            
            response = handler(event, None)
            
            assert response['statusCode'] == 403
            body = json.loads(response['body'])
            assert body['error']['code'] == 'FORBIDDEN'
            assert 'own promotions' in body['error']['message'].lower()
    
    def test_get_promotion_metrics_dynamodb_error(
        self, mock_env_vars, farmer_token_payload
    ):
        """Test metrics retrieval when DynamoDB fails."""
        from promotions.get_promotion_metrics import handler
        
        with patch('promotions.get_promotion_metrics.get_user_from_token') as mock_auth, \
             patch('promotions.get_promotion_metrics.get_item') as mock_get:
            
            mock_auth.return_value = farmer_token_payload
            mock_get.side_effect = Exception('DynamoDB error')
            
            event = {
                'headers': {
                    'Authorization': 'Bearer valid-token'
                },
                'pathParameters': {
                    'promotionId': 'promo-123'
                }
            }
            
            response = handler(event, None)
            
            assert response['statusCode'] == 503
            body = json.loads(response['body'])
            assert body['error']['code'] == 'SERVICE_UNAVAILABLE'
    
    def test_get_promotion_metrics_zero_metrics(
        self, mock_env_vars, farmer_token_payload, mock_promotion
    ):
        """Test metrics retrieval for promotion with zero metrics."""
        from promotions.get_promotion_metrics import handler
        
        with patch('promotions.get_promotion_metrics.get_user_from_token') as mock_auth, \
             patch('promotions.get_promotion_metrics.get_item') as mock_get:
            
            # Promotion with zero metrics
            zero_metrics_promotion = mock_promotion.copy()
            zero_metrics_promotion['metrics'] = {
                'views': 0,
                'clicks': 0,
                'conversions': 0,
                'spent': 0.0
            }
            
            mock_auth.return_value = farmer_token_payload
            mock_get.return_value = zero_metrics_promotion
            
            event = {
                'headers': {
                    'Authorization': 'Bearer valid-token'
                },
                'pathParameters': {
                    'promotionId': 'promo-123'
                }
            }
            
            response = handler(event, None)
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            
            metrics = body['metrics']
            assert metrics['views'] == 0
            assert metrics['clicks'] == 0
            assert metrics['conversions'] == 0
            assert metrics['spent'] == 0.0
    
    def test_get_promotion_metrics_high_values(
        self, mock_env_vars, farmer_token_payload, mock_promotion
    ):
        """Test metrics retrieval with high metric values."""
        from promotions.get_promotion_metrics import handler
        
        with patch('promotions.get_promotion_metrics.get_user_from_token') as mock_auth, \
             patch('promotions.get_promotion_metrics.get_item') as mock_get:
            
            # Promotion with high metrics
            high_metrics_promotion = mock_promotion.copy()
            high_metrics_promotion['metrics'] = {
                'views': 10000,
                'clicks': 2500,
                'conversions': 500,
                'spent': 9999.99
            }
            
            mock_auth.return_value = farmer_token_payload
            mock_get.return_value = high_metrics_promotion
            
            event = {
                'headers': {
                    'Authorization': 'Bearer valid-token'
                },
                'pathParameters': {
                    'promotionId': 'promo-123'
                }
            }
            
            response = handler(event, None)
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            
            metrics = body['metrics']
            assert metrics['views'] == 10000
            assert metrics['clicks'] == 2500
            assert metrics['conversions'] == 500
            assert metrics['spent'] == 9999.99
    
    def test_get_promotion_metrics_partial_metrics(
        self, mock_env_vars, farmer_token_payload, mock_promotion
    ):
        """Test metrics retrieval when some metric fields are missing."""
        from promotions.get_promotion_metrics import handler
        
        with patch('promotions.get_promotion_metrics.get_user_from_token') as mock_auth, \
             patch('promotions.get_promotion_metrics.get_item') as mock_get:
            
            # Promotion with partial metrics
            partial_metrics_promotion = mock_promotion.copy()
            partial_metrics_promotion['metrics'] = {
                'views': 100,
                'clicks': 20
                # Missing conversions and spent
            }
            
            mock_auth.return_value = farmer_token_payload
            mock_get.return_value = partial_metrics_promotion
            
            event = {
                'headers': {
                    'Authorization': 'Bearer valid-token'
                },
                'pathParameters': {
                    'promotionId': 'promo-123'
                }
            }
            
            response = handler(event, None)
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            
            metrics = body['metrics']
            assert metrics['views'] == 100
            assert metrics['clicks'] == 20
            assert metrics['conversions'] == 0  # Default value
            assert metrics['spent'] == 0.0  # Default value
    
    def test_get_promotion_metrics_response_structure(
        self, mock_env_vars, farmer_token_payload, mock_promotion
    ):
        """Test that response has correct structure."""
        from promotions.get_promotion_metrics import handler
        
        with patch('promotions.get_promotion_metrics.get_user_from_token') as mock_auth, \
             patch('promotions.get_promotion_metrics.get_item') as mock_get:
            
            mock_auth.return_value = farmer_token_payload
            mock_get.return_value = mock_promotion
            
            event = {
                'headers': {
                    'Authorization': 'Bearer valid-token'
                },
                'pathParameters': {
                    'promotionId': 'promo-123'
                }
            }
            
            response = handler(event, None)
            
            assert response['statusCode'] == 200
            assert 'headers' in response
            assert response['headers']['Content-Type'] == 'application/json'
            assert response['headers']['Access-Control-Allow-Origin'] == '*'
            
            body = json.loads(response['body'])
            assert 'promotionId' in body
            assert 'metrics' in body
            assert isinstance(body['metrics'], dict)
            assert 'views' in body['metrics']
            assert 'clicks' in body['metrics']
            assert 'conversions' in body['metrics']
            assert 'spent' in body['metrics']
    
    def test_get_promotion_metrics_no_path_parameters(
        self, mock_env_vars, farmer_token_payload
    ):
        """Test metrics retrieval without pathParameters in event."""
        from promotions.get_promotion_metrics import handler
        
        with patch('promotions.get_promotion_metrics.get_user_from_token') as mock_auth:
            mock_auth.return_value = farmer_token_payload
            
            event = {
                'headers': {
                    'Authorization': 'Bearer valid-token'
                }
            }
            
            response = handler(event, None)
            
            assert response['statusCode'] == 400
            body = json.loads(response['body'])
            assert body['error']['code'] == 'INVALID_REQUEST'
    
    def test_get_promotion_metrics_case_insensitive_auth_header(
        self, mock_env_vars, farmer_token_payload, mock_promotion
    ):
        """Test that authorization header is case-insensitive."""
        from promotions.get_promotion_metrics import handler
        
        with patch('promotions.get_promotion_metrics.get_user_from_token') as mock_auth, \
             patch('promotions.get_promotion_metrics.get_item') as mock_get:
            
            mock_auth.return_value = farmer_token_payload
            mock_get.return_value = mock_promotion
            
            # Use lowercase 'authorization'
            event = {
                'headers': {
                    'authorization': 'Bearer valid-token'
                },
                'pathParameters': {
                    'promotionId': 'promo-123'
                }
            }
            
            response = handler(event, None)
            
            assert response['statusCode'] == 200


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
