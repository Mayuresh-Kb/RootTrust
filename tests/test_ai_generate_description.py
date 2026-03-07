"""
Unit tests for AI product description generation endpoint.
Tests the marketing content generation functionality.
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


class TestPromptConstruction:
    """Test cases for Bedrock prompt construction."""
    
    def test_construct_prompt_basic_product(self):
        """Test prompt construction for basic product without GI tag."""
        from generate_description import construct_bedrock_prompt
        
        product = {
            'name': 'Fresh Tomatoes',
            'category': 'vegetables',
            'price': 50,
            'unit': 'kg',
            'description': 'Locally grown tomatoes',
            'giTag': {'hasTag': False}
        }
        
        prompt = construct_bedrock_prompt(product)
        
        assert 'Fresh Tomatoes' in prompt
        assert 'vegetables' in prompt
        assert '₹50' in prompt
        assert 'Locally grown tomatoes' in prompt
        assert 'DREAM OUTCOME' in prompt
        assert 'PERCEIVED LIKELIHOOD' in prompt
    
    def test_construct_prompt_with_gi_tag(self):
        """Test prompt construction for product with GI tag."""
        from generate_description import construct_bedrock_prompt
        
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
        
        prompt = construct_bedrock_prompt(product)
        
        assert 'Darjeeling Tea' in prompt
        assert 'West Bengal' in prompt
        assert 'GI Tag' in prompt
    
    def test_construct_prompt_with_authenticity_confidence(self):
        """Test prompt includes authenticity confidence when available."""
        from generate_description import construct_bedrock_prompt
        
        product = {
            'name': 'Organic Rice',
            'category': 'grains',
            'price': 80,
            'unit': 'kg',
            'description': 'Organic basmati rice',
            'giTag': {'hasTag': False},
            'authenticityConfidence': Decimal('95.5')
        }
        
        prompt = construct_bedrock_prompt(product)
        
        assert 'Authenticity Confidence: 95.5%' in prompt


class TestCaching:
    """Test cases for description caching functionality."""
    
    @patch('generate_description.get_item')
    def test_get_cached_description_hit(self, mock_get_item):
        """Test cache hit returns cached description."""
        from generate_description import get_cached_description
        
        # Mock cache hit with valid TTL
        future_ttl = int((datetime.utcnow() + timedelta(days=1)).timestamp())
        mock_get_item.return_value = {
            'generatedDescription': 'Cached marketing description',
            'ttl': future_ttl
        }
        
        result = get_cached_description('test-product-id')
        
        assert result == 'Cached marketing description'
        mock_get_item.assert_called_once_with(
            pk='MARKETING_CACHE#test-product-id',
            sk='DESCRIPTION'
        )
    
    @patch('generate_description.get_item')
    def test_get_cached_description_expired(self, mock_get_item):
        """Test expired cache returns None."""
        from generate_description import get_cached_description
        
        # Mock cache hit with expired TTL
        past_ttl = int((datetime.utcnow() - timedelta(days=1)).timestamp())
        mock_get_item.return_value = {
            'generatedDescription': 'Expired description',
            'ttl': past_ttl
        }
        
        result = get_cached_description('test-product-id')
        
        assert result is None
    
    @patch('generate_description.get_item')
    def test_get_cached_description_miss(self, mock_get_item):
        """Test cache miss returns None."""
        from generate_description import get_cached_description
        
        mock_get_item.return_value = None
        
        result = get_cached_description('test-product-id')
        
        assert result is None
    
    @patch('generate_description.put_item')
    def test_store_description_cache(self, mock_put_item):
        """Test storing description in cache."""
        from generate_description import store_description_cache
        
        store_description_cache('test-product-id', 'Generated description')
        
        mock_put_item.assert_called_once()
        call_args = mock_put_item.call_args[0][0]
        
        assert call_args['PK'] == 'MARKETING_CACHE#test-product-id'
        assert call_args['SK'] == 'DESCRIPTION'
        assert call_args['EntityType'] == 'MarketingCache'
        assert call_args['productId'] == 'test-product-id'
        assert call_args['generatedDescription'] == 'Generated description'
        assert 'ttl' in call_args
        assert 'cachedAt' in call_args


class TestBedrockInvocation:
    """Test cases for Bedrock API invocation."""
    
    @patch('generate_description.bedrock_runtime')
    def test_invoke_bedrock_success(self, mock_bedrock):
        """Test successful Bedrock invocation."""
        from generate_description import invoke_bedrock
        
        # Mock Bedrock response
        mock_response = {
            'body': MagicMock()
        }
        mock_response['body'].read.return_value = json.dumps({
            'content': [
                {
                    'text': 'Experience the vibrant taste of farm-fresh tomatoes...'
                }
            ]
        }).encode('utf-8')
        
        mock_bedrock.invoke_model.return_value = mock_response
        
        result = invoke_bedrock('Test prompt')
        
        assert 'Experience the vibrant taste' in result
        mock_bedrock.invoke_model.assert_called_once()
        
        # Verify correct model and parameters
        call_kwargs = mock_bedrock.invoke_model.call_args[1]
        assert call_kwargs['modelId'] == 'anthropic.claude-3-haiku-20240307-v1:0'
        
        body = json.loads(call_kwargs['body'])
        assert body['temperature'] == 0.7
        assert body['max_tokens'] == 500
    
    @patch('generate_description.bedrock_runtime')
    def test_invoke_bedrock_with_markdown_json(self, mock_bedrock):
        """Test Bedrock response with JSON wrapped in markdown."""
        from generate_description import invoke_bedrock
        
        # Mock Bedrock response with markdown code block
        mock_response = {
            'body': MagicMock()
        }
        mock_response['body'].read.return_value = json.dumps({
            'content': [
                {
                    'text': 'Here is the description:\n\nFresh, organic tomatoes from local farms.'
                }
            ]
        }).encode('utf-8')
        
        mock_bedrock.invoke_model.return_value = mock_response
        
        result = invoke_bedrock('Test prompt')
        
        assert 'Fresh, organic tomatoes' in result
    
    @patch('generate_description.bedrock_runtime')
    def test_invoke_bedrock_empty_response(self, mock_bedrock):
        """Test Bedrock invocation with empty response."""
        from generate_description import invoke_bedrock
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
    
    @patch('generate_description.bedrock_runtime')
    def test_invoke_bedrock_api_error(self, mock_bedrock):
        """Test Bedrock invocation with API error."""
        from generate_description import invoke_bedrock
        from backend.shared.exceptions import ServiceUnavailableError
        
        mock_bedrock.invoke_model.side_effect = Exception('Bedrock API error')
        
        with pytest.raises(ServiceUnavailableError):
            invoke_bedrock('Test prompt')


class TestLambdaHandler:
    """Test cases for Lambda handler function."""
    
    @patch('generate_description.validate_jwt_token')
    @patch('generate_description.get_cached_description')
    @patch('generate_description.get_item')
    @patch('generate_description.invoke_bedrock')
    @patch('generate_description.store_description_cache')
    def test_handler_success_cache_miss(
        self,
        mock_store_cache,
        mock_invoke_bedrock,
        mock_get_item,
        mock_get_cached,
        mock_verify_token
    ):
        """Test successful description generation with cache miss."""
        from generate_description import handler
        
        # Mock JWT verification
        mock_verify_token.return_value = {
            'userId': 'farmer-123',
            'role': 'farmer'
        }
        
        # Mock cache miss
        mock_get_cached.return_value = None
        
        # Mock product retrieval
        mock_get_item.return_value = {
            'productId': 'product-123',
            'farmerId': 'farmer-123',
            'name': 'Fresh Tomatoes',
            'category': 'vegetables',
            'price': Decimal('50'),
            'unit': 'kg',
            'description': 'Locally grown',
            'giTag': {'hasTag': False}
        }
        
        # Mock Bedrock response
        mock_invoke_bedrock.return_value = 'Experience the vibrant taste of farm-fresh tomatoes...'
        
        event = {
            'headers': {'Authorization': 'Bearer valid-token'},
            'body': json.dumps({'productId': 'product-123'})
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['productId'] == 'product-123'
        assert 'generatedDescription' in body
        assert body['cached'] is False
        
        mock_store_cache.assert_called_once()
    
    @patch('generate_description.validate_jwt_token')
    @patch('generate_description.get_cached_description')
    def test_handler_success_cache_hit(
        self,
        mock_get_cached,
        mock_verify_token
    ):
        """Test successful description retrieval from cache."""
        from generate_description import handler
        
        # Mock JWT verification
        mock_verify_token.return_value = {
            'userId': 'farmer-123',
            'role': 'farmer'
        }
        
        # Mock cache hit
        mock_get_cached.return_value = 'Cached description from previous generation'
        
        event = {
            'headers': {'Authorization': 'Bearer valid-token'},
            'body': json.dumps({'productId': 'product-123'})
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['productId'] == 'product-123'
        assert body['generatedDescription'] == 'Cached description from previous generation'
        assert body['cached'] is True
    
    def test_handler_missing_authorization(self):
        """Test handler with missing authorization header."""
        from generate_description import handler
        
        event = {
            'headers': {},
            'body': json.dumps({'productId': 'product-123'})
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 401
        body = json.loads(response['body'])
        assert body['error']['code'] == 'UNAUTHORIZED'
    
    @patch('generate_description.validate_jwt_token')
    def test_handler_consumer_role_forbidden(self, mock_verify_token):
        """Test handler rejects consumer role."""
        from generate_description import handler
        
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
    
    @patch('generate_description.validate_jwt_token')
    def test_handler_missing_product_id(self, mock_verify_token):
        """Test handler with missing productId."""
        from generate_description import handler
        
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
    
    @patch('generate_description.validate_jwt_token')
    @patch('generate_description.get_cached_description')
    @patch('generate_description.get_item')
    def test_handler_product_not_found(
        self,
        mock_get_item,
        mock_get_cached,
        mock_verify_token
    ):
        """Test handler with non-existent product."""
        from generate_description import handler
        
        mock_verify_token.return_value = {
            'userId': 'farmer-123',
            'role': 'farmer'
        }
        
        mock_get_cached.return_value = None
        mock_get_item.return_value = None
        
        event = {
            'headers': {'Authorization': 'Bearer valid-token'},
            'body': json.dumps({'productId': 'non-existent'})
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 404
        body = json.loads(response['body'])
        assert body['error']['code'] == 'NOT_FOUND'
    
    @patch('generate_description.validate_jwt_token')
    @patch('generate_description.get_cached_description')
    @patch('generate_description.get_item')
    def test_handler_wrong_farmer(
        self,
        mock_get_item,
        mock_get_cached,
        mock_verify_token
    ):
        """Test handler rejects farmer accessing another farmer's product."""
        from generate_description import handler
        
        mock_verify_token.return_value = {
            'userId': 'farmer-123',
            'role': 'farmer'
        }
        
        mock_get_cached.return_value = None
        
        # Product belongs to different farmer
        mock_get_item.return_value = {
            'productId': 'product-123',
            'farmerId': 'farmer-456',
            'name': 'Product'
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
    
    @patch('generate_description.validate_jwt_token')
    @patch('generate_description.get_cached_description')
    @patch('generate_description.get_item')
    @patch('generate_description.invoke_bedrock')
    def test_handler_bedrock_failure(
        self,
        mock_invoke_bedrock,
        mock_get_item,
        mock_get_cached,
        mock_verify_token
    ):
        """Test handler with Bedrock service failure."""
        from generate_description import handler
        from backend.shared.exceptions import ServiceUnavailableError
        
        mock_verify_token.return_value = {
            'userId': 'farmer-123',
            'role': 'farmer'
        }
        
        mock_get_cached.return_value = None
        
        mock_get_item.return_value = {
            'productId': 'product-123',
            'farmerId': 'farmer-123',
            'name': 'Product',
            'category': 'vegetables',
            'price': Decimal('50'),
            'unit': 'kg',
            'description': 'Test',
            'giTag': {'hasTag': False}
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
