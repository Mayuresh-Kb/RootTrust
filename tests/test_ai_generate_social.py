"""
Unit tests for AI social media content generation endpoint.
Tests the social media content generation with seasonal urgency functionality.
"""
import json
import pytest
import sys
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch, MagicMock

# Add backend to path for imports
sys.path.insert(0, 'backend/shared')
sys.path.insert(0, 'backend/ai')


class TestSeasonalUrgencyCheck:
    """Test cases for seasonal urgency detection."""
    
    def test_check_seasonal_urgency_not_seasonal(self):
        """Test non-seasonal product returns no urgency."""
        from generate_social import check_seasonal_urgency
        
        product = {
            'seasonal': {
                'isSeasonal': False
            }
        }
        
        is_urgent, days_remaining = check_seasonal_urgency(product)
        
        assert is_urgent is False
        assert days_remaining == 0
    
    def test_check_seasonal_urgency_within_7_days(self):
        """Test seasonal product within 7 days of season end."""
        from generate_social import check_seasonal_urgency
        
        # Season ends in 5 days (use date at start of day to avoid timing issues)
        season_end = (datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=5)).isoformat()
        
        product = {
            'seasonal': {
                'isSeasonal': True,
                'seasonEnd': season_end
            }
        }
        
        is_urgent, days_remaining = check_seasonal_urgency(product)
        
        assert is_urgent is True
        assert days_remaining == 5
    
    def test_check_seasonal_urgency_exactly_7_days(self):
        """Test seasonal product exactly 7 days from season end."""
        from generate_social import check_seasonal_urgency
        
        # Season ends in exactly 7 days (use date at start of day to avoid timing issues)
        season_end = (datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=7)).isoformat()
        
        product = {
            'seasonal': {
                'isSeasonal': True,
                'seasonEnd': season_end
            }
        }
        
        is_urgent, days_remaining = check_seasonal_urgency(product)
        
        assert is_urgent is True
        assert days_remaining == 7
    
    def test_check_seasonal_urgency_beyond_7_days(self):
        """Test seasonal product more than 7 days from season end."""
        from generate_social import check_seasonal_urgency
        
        # Season ends in 15 days (use date at start of day to avoid timing issues)
        season_end = (datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=15)).isoformat()
        
        product = {
            'seasonal': {
                'isSeasonal': True,
                'seasonEnd': season_end
            }
        }
        
        is_urgent, days_remaining = check_seasonal_urgency(product)
        
        assert is_urgent is False
        assert days_remaining == 15
    
    def test_check_seasonal_urgency_last_day(self):
        """Test seasonal product on last day of season."""
        from generate_social import check_seasonal_urgency
        
        # Season ends today (within 24 hours)
        season_end = (datetime.utcnow() + timedelta(hours=12)).isoformat()
        
        product = {
            'seasonal': {
                'isSeasonal': True,
                'seasonEnd': season_end
            }
        }
        
        is_urgent, days_remaining = check_seasonal_urgency(product)
        
        assert is_urgent is True
        assert days_remaining == 0
    
    def test_check_seasonal_urgency_already_ended(self):
        """Test seasonal product past season end."""
        from generate_social import check_seasonal_urgency
        
        # Season ended 2 days ago
        season_end = (datetime.utcnow() - timedelta(days=2)).isoformat()
        
        product = {
            'seasonal': {
                'isSeasonal': True,
                'seasonEnd': season_end
            }
        }
        
        is_urgent, days_remaining = check_seasonal_urgency(product)
        
        assert is_urgent is False
        assert days_remaining == 0
    
    def test_check_seasonal_urgency_missing_season_end(self):
        """Test seasonal product without season end date."""
        from generate_social import check_seasonal_urgency
        
        product = {
            'seasonal': {
                'isSeasonal': True
            }
        }
        
        is_urgent, days_remaining = check_seasonal_urgency(product)
        
        assert is_urgent is False
        assert days_remaining == 0
    
    def test_check_seasonal_urgency_invalid_date_format(self):
        """Test seasonal product with invalid date format."""
        from generate_social import check_seasonal_urgency
        
        product = {
            'seasonal': {
                'isSeasonal': True,
                'seasonEnd': 'invalid-date'
            }
        }
        
        is_urgent, days_remaining = check_seasonal_urgency(product)
        
        assert is_urgent is False
        assert days_remaining == 0


class TestPromptConstruction:
    """Test cases for Bedrock prompt construction."""
    
    def test_construct_prompt_basic_product_no_urgency(self):
        """Test prompt construction for non-urgent product."""
        from generate_social import construct_bedrock_prompt
        
        product = {
            'name': 'Fresh Tomatoes',
            'category': 'vegetables',
            'price': 50,
            'unit': 'kg',
            'description': 'Locally grown tomatoes',
            'giTag': {'hasTag': False}
        }
        
        prompt = construct_bedrock_prompt(product, is_urgent=False, days_remaining=0)
        
        assert 'Fresh Tomatoes' in prompt
        assert 'vegetables' in prompt
        assert '₹50' in prompt
        assert 'Locally grown tomatoes' in prompt
        assert 'Facebook and Instagram' in prompt
        assert 'CRITICAL' not in prompt
        assert 'Limited time' not in prompt
    
    def test_construct_prompt_with_urgency(self):
        """Test prompt construction for urgent seasonal product."""
        from generate_social import construct_bedrock_prompt
        
        product = {
            'name': 'Alphonso Mangoes',
            'category': 'fruits',
            'price': 200,
            'unit': 'kg',
            'description': 'Premium mangoes',
            'giTag': {'hasTag': False}
        }
        
        prompt = construct_bedrock_prompt(product, is_urgent=True, days_remaining=3)
        
        assert 'Alphonso Mangoes' in prompt
        assert 'CRITICAL' in prompt
        assert 'SEASONAL' in prompt
        assert '3 days' in prompt
        assert 'Limited time' in prompt
        assert 'Ending soon' in prompt
        assert 'Last chance' in prompt
        assert 'FOMO' in prompt
    
    def test_construct_prompt_with_urgency_singular_day(self):
        """Test prompt construction for product with 1 day remaining."""
        from generate_social import construct_bedrock_prompt
        
        product = {
            'name': 'Seasonal Berries',
            'category': 'fruits',
            'price': 150,
            'unit': 'kg',
            'description': 'Fresh berries',
            'giTag': {'hasTag': False}
        }
        
        prompt = construct_bedrock_prompt(product, is_urgent=True, days_remaining=1)
        
        assert '1 day' in prompt
        assert '1 days' not in prompt  # Check singular form
    
    def test_construct_prompt_with_gi_tag(self):
        """Test prompt construction for product with GI tag."""
        from generate_social import construct_bedrock_prompt
        
        product = {
            'name': 'Darjeeling Tea',
            'category': 'spices',
            'price': 500,
            'unit': 'kg',
            'description': 'Premium tea leaves',
            'giTag': {
                'hasTag': True,
                'tagName': 'Darjeeling Tea',
                'region': 'West Bengal'
            }
        }
        
        prompt = construct_bedrock_prompt(product, is_urgent=False, days_remaining=0)
        
        assert 'Darjeeling Tea' in prompt
        assert 'West Bengal' in prompt
        assert 'GI Tag' in prompt
    
    def test_construct_prompt_with_authenticity_confidence(self):
        """Test prompt includes authenticity confidence when available."""
        from generate_social import construct_bedrock_prompt
        
        product = {
            'name': 'Organic Rice',
            'category': 'grains',
            'price': 80,
            'unit': 'kg',
            'description': 'Organic basmati rice',
            'giTag': {'hasTag': False},
            'authenticityConfidence': Decimal('95.5')
        }
        
        prompt = construct_bedrock_prompt(product, is_urgent=False, days_remaining=0)
        
        assert 'Authenticity Confidence: 95.5%' in prompt
    
    def test_construct_prompt_with_all_features(self):
        """Test prompt construction with urgency, GI tag, and authenticity."""
        from generate_social import construct_bedrock_prompt
        
        product = {
            'name': 'Kesar Mangoes',
            'category': 'fruits',
            'price': 300,
            'unit': 'kg',
            'description': 'Premium Kesar mangoes from Gujarat',
            'giTag': {
                'hasTag': True,
                'tagName': 'Kesar Mango',
                'region': 'Gujarat'
            },
            'authenticityConfidence': Decimal('98.0')
        }
        
        prompt = construct_bedrock_prompt(product, is_urgent=True, days_remaining=5)
        
        assert 'Kesar Mangoes' in prompt
        assert 'Gujarat' in prompt
        assert 'GI Tag' in prompt
        assert 'Authenticity Confidence: 98.0%' in prompt
        assert 'CRITICAL' in prompt
        assert '5 days' in prompt


class TestBedrockInvocation:
    """Test cases for Bedrock API invocation."""
    
    @patch('generate_social.bedrock_runtime')
    def test_invoke_bedrock_success(self, mock_bedrock):
        """Test successful Bedrock invocation."""
        from generate_social import invoke_bedrock
        
        # Mock Bedrock response
        mock_response = {
            'body': MagicMock()
        }
        mock_response['body'].read.return_value = json.dumps({
            'content': [
                {
                    'text': '🍅 Fresh from the farm! Get your hands on juicy, vine-ripened tomatoes...\n\n#FreshProduce #LocalFarm #HealthyEating'
                }
            ]
        }).encode('utf-8')
        
        mock_bedrock.invoke_model.return_value = mock_response
        
        result = invoke_bedrock('Test prompt')
        
        assert '🍅 Fresh from the farm' in result
        assert '#FreshProduce' in result
        mock_bedrock.invoke_model.assert_called_once()
        
        # Verify correct model and parameters
        call_kwargs = mock_bedrock.invoke_model.call_args[1]
        assert call_kwargs['modelId'] == 'anthropic.claude-3-haiku-20240307-v1:0'
        
        body = json.loads(call_kwargs['body'])
        assert body['temperature'] == 0.8
        assert body['max_tokens'] == 400
    
    @patch('generate_social.bedrock_runtime')
    def test_invoke_bedrock_empty_response(self, mock_bedrock):
        """Test Bedrock invocation with empty response."""
        from generate_social import invoke_bedrock
        from backend.shared.exceptions import ServiceUnavailableError
        
        # Mock empty response
        mock_response = {
            'body': MagicMock()
        }
        mock_response['body'].read.return_value = json.dumps({
            'content': []
        }).encode('utf-8')
        
        mock_bedrock.invoke_model.return_value = mock_response
        
        with pytest.raises(ServiceUnavailableError):
            invoke_bedrock('Test prompt')
    
    @patch('generate_social.bedrock_runtime')
    def test_invoke_bedrock_api_error(self, mock_bedrock):
        """Test Bedrock invocation with API error."""
        from generate_social import invoke_bedrock
        from backend.shared.exceptions import ServiceUnavailableError
        
        mock_bedrock.invoke_model.side_effect = Exception('Bedrock API error')
        
        with pytest.raises(ServiceUnavailableError):
            invoke_bedrock('Test prompt')


class TestLambdaHandler:
    """Test cases for Lambda handler function."""
    
    @patch('generate_social.validate_jwt_token')
    @patch('generate_social.get_item')
    @patch('generate_social.invoke_bedrock')
    def test_handler_success_no_urgency(
        self,
        mock_invoke_bedrock,
        mock_get_item,
        mock_verify_token
    ):
        """Test successful social media content generation without urgency."""
        from generate_social import handler
        
        # Mock JWT verification
        mock_verify_token.return_value = {
            'userId': 'farmer-123',
            'role': 'farmer'
        }
        
        # Mock product retrieval (non-seasonal)
        mock_get_item.return_value = {
            'productId': 'product-123',
            'farmerId': 'farmer-123',
            'name': 'Fresh Tomatoes',
            'category': 'vegetables',
            'price': Decimal('50'),
            'unit': 'kg',
            'description': 'Locally grown',
            'giTag': {'hasTag': False},
            'seasonal': {'isSeasonal': False}
        }
        
        # Mock Bedrock response
        mock_invoke_bedrock.return_value = '🍅 Fresh tomatoes from local farms! #FreshProduce'
        
        event = {
            'headers': {'Authorization': 'Bearer valid-token'},
            'body': json.dumps({'productId': 'product-123'})
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['productId'] == 'product-123'
        assert 'socialMediaContent' in body
        assert body['isUrgent'] is False
        assert body['daysRemaining'] == 0
    
    @patch('generate_social.validate_jwt_token')
    @patch('generate_social.get_item')
    @patch('generate_social.invoke_bedrock')
    def test_handler_success_with_urgency(
        self,
        mock_invoke_bedrock,
        mock_get_item,
        mock_verify_token
    ):
        """Test successful social media content generation with seasonal urgency."""
        from generate_social import handler
        
        # Mock JWT verification
        mock_verify_token.return_value = {
            'userId': 'farmer-123',
            'role': 'farmer'
        }
        
        # Season ends in 3 days
        season_end = (datetime.utcnow() + timedelta(days=3)).isoformat()
        
        # Mock product retrieval (seasonal, urgent)
        mock_get_item.return_value = {
            'productId': 'product-123',
            'farmerId': 'farmer-123',
            'name': 'Alphonso Mangoes',
            'category': 'fruits',
            'price': Decimal('200'),
            'unit': 'kg',
            'description': 'Premium mangoes',
            'giTag': {'hasTag': False},
            'seasonal': {
                'isSeasonal': True,
                'seasonEnd': season_end
            }
        }
        
        # Mock Bedrock response with urgency
        mock_invoke_bedrock.return_value = '⏰ LAST CHANCE! Only 3 days left to get premium Alphonso mangoes! #LimitedTime'
        
        event = {
            'headers': {'Authorization': 'Bearer valid-token'},
            'body': json.dumps({'productId': 'product-123'})
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['productId'] == 'product-123'
        assert 'socialMediaContent' in body
        assert body['isUrgent'] is True
        assert body['daysRemaining'] == 3
    
    def test_handler_missing_authorization(self):
        """Test handler with missing authorization header."""
        from generate_social import handler
        
        event = {
            'headers': {},
            'body': json.dumps({'productId': 'product-123'})
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 401
        body = json.loads(response['body'])
        assert body['error']['code'] == 'UNAUTHORIZED'
    
    @patch('generate_social.validate_jwt_token')
    def test_handler_consumer_role_forbidden(self, mock_verify_token):
        """Test handler rejects consumer role."""
        from generate_social import handler
        
        # Mock JWT verification with consumer role
        mock_verify_token.return_value = {
            'userId': 'consumer-123',
            'role': 'consumer'
        }
        
        event = {
            'headers': {'Authorization': 'Bearer valid-token'},
            'body': json.dumps({'productId': 'product-123'})
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 403
        body = json.loads(response['body'])
        assert body['error']['code'] == 'FORBIDDEN'
        assert 'farmers' in body['error']['message'].lower()
    
    @patch('generate_social.validate_jwt_token')
    def test_handler_missing_product_id(self, mock_verify_token):
        """Test handler with missing productId."""
        from generate_social import handler
        
        mock_verify_token.return_value = {
            'userId': 'farmer-123',
            'role': 'farmer'
        }
        
        event = {
            'headers': {'Authorization': 'Bearer valid-token'},
            'body': json.dumps({})
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error']['code'] == 'VALIDATION_ERROR'
        assert 'productId' in body['error']['message']
    
    @patch('generate_social.validate_jwt_token')
    @patch('generate_social.get_item')
    def test_handler_product_not_found(
        self,
        mock_get_item,
        mock_verify_token
    ):
        """Test handler with non-existent product."""
        from generate_social import handler
        
        mock_verify_token.return_value = {
            'userId': 'farmer-123',
            'role': 'farmer'
        }
        
        mock_get_item.return_value = None
        
        event = {
            'headers': {'Authorization': 'Bearer valid-token'},
            'body': json.dumps({'productId': 'non-existent'})
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 404
        body = json.loads(response['body'])
        assert body['error']['code'] == 'NOT_FOUND'
    
    @patch('generate_social.validate_jwt_token')
    @patch('generate_social.get_item')
    def test_handler_wrong_farmer(
        self,
        mock_get_item,
        mock_verify_token
    ):
        """Test handler rejects farmer accessing another farmer's product."""
        from generate_social import handler
        
        mock_verify_token.return_value = {
            'userId': 'farmer-123',
            'role': 'farmer'
        }
        
        # Product belongs to different farmer
        mock_get_item.return_value = {
            'productId': 'product-123',
            'farmerId': 'farmer-456',
            'name': 'Product',
            'seasonal': {'isSeasonal': False}
        }
        
        event = {
            'headers': {'Authorization': 'Bearer valid-token'},
            'body': json.dumps({'productId': 'product-123'})
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 403
        body = json.loads(response['body'])
        assert body['error']['code'] == 'FORBIDDEN'
        assert 'your own products' in body['error']['message']
    
    @patch('generate_social.validate_jwt_token')
    @patch('generate_social.get_item')
    @patch('generate_social.invoke_bedrock')
    def test_handler_bedrock_failure(
        self,
        mock_invoke_bedrock,
        mock_get_item,
        mock_verify_token
    ):
        """Test handler with Bedrock service failure."""
        from generate_social import handler
        from backend.shared.exceptions import ServiceUnavailableError
        
        mock_verify_token.return_value = {
            'userId': 'farmer-123',
            'role': 'farmer'
        }
        
        mock_get_item.return_value = {
            'productId': 'product-123',
            'farmerId': 'farmer-123',
            'name': 'Product',
            'category': 'vegetables',
            'price': Decimal('50'),
            'unit': 'kg',
            'description': 'Test',
            'giTag': {'hasTag': False},
            'seasonal': {'isSeasonal': False}
        }
        
        mock_invoke_bedrock.side_effect = ServiceUnavailableError('Bedrock', 'Service error')
        
        event = {
            'headers': {'Authorization': 'Bearer valid-token'},
            'body': json.dumps({'productId': 'product-123'})
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 503
        body = json.loads(response['body'])
        assert body['error']['code'] == 'SERVICE_UNAVAILABLE'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
