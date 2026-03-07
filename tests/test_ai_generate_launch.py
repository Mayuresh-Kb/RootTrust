"""
Unit tests for AI launch announcement generation endpoint.
Tests the launch announcement content generation functionality.
"""
import json
import pytest
import sys
from decimal import Decimal
from unittest.mock import Mock, patch, MagicMock

# Add backend to path for imports
sys.path.insert(0, 'backend/shared')
sys.path.insert(0, 'backend/ai')


class TestPromptConstruction:
    """Test cases for Bedrock prompt construction."""
    
    def test_construct_prompt_basic_product(self):
        """Test prompt construction for basic product."""
        from generate_launch import construct_bedrock_prompt
        
        product = {
            'name': 'Fresh Tomatoes',
            'category': 'vegetables',
            'price': 50,
            'unit': 'kg',
            'description': 'Locally grown tomatoes',
            'giTag': {'hasTag': False},
            'seasonal': {'isSeasonal': False}
        }
        
        prompt = construct_bedrock_prompt(product)
        
        assert 'Fresh Tomatoes' in prompt
        assert 'vegetables' in prompt
        assert '₹50' in prompt
        assert 'Locally grown tomatoes' in prompt
        assert 'launch announcement' in prompt.lower()
        assert 'email newsletters' in prompt.lower()
        assert 'website announcements' in prompt.lower()
        assert '200-300 words' in prompt
    
    def test_construct_prompt_with_gi_tag(self):
        """Test prompt construction for product with GI tag."""
        from generate_launch import construct_bedrock_prompt
        
        product = {
            'name': 'Darjeeling Tea',
            'category': 'spices',
            'price': 500,
            'unit': 'kg',
            'description': 'Premium tea leaves from Darjeeling hills',
            'giTag': {
                'hasTag': True,
                'tagName': 'Darjeeling Tea',
                'region': 'West Bengal'
            },
            'seasonal': {'isSeasonal': False}
        }
        
        prompt = construct_bedrock_prompt(product)
        
        assert 'Darjeeling Tea' in prompt
        assert 'West Bengal' in prompt
        assert 'GI Tag' in prompt
        assert 'authenticity and regional heritage' in prompt.lower()
    
    def test_construct_prompt_with_authenticity_confidence(self):
        """Test prompt includes authenticity confidence when available."""
        from generate_launch import construct_bedrock_prompt
        
        product = {
            'name': 'Organic Rice',
            'category': 'grains',
            'price': 80,
            'unit': 'kg',
            'description': 'Organic basmati rice',
            'giTag': {'hasTag': False},
            'seasonal': {'isSeasonal': False},
            'authenticityConfidence': Decimal('95.5')
        }
        
        prompt = construct_bedrock_prompt(product)
        
        assert 'Authenticity Confidence: 95.5%' in prompt
    
    def test_construct_prompt_with_seasonal_info(self):
        """Test prompt construction for seasonal product."""
        from generate_launch import construct_bedrock_prompt
        
        product = {
            'name': 'Alphonso Mangoes',
            'category': 'fruits',
            'price': 200,
            'unit': 'kg',
            'description': 'Premium Alphonso mangoes',
            'giTag': {'hasTag': False},
            'seasonal': {
                'isSeasonal': True,
                'seasonStart': '2024-04-01',
                'seasonEnd': '2024-06-30'
            }
        }
        
        prompt = construct_bedrock_prompt(product)
        
        assert 'Alphonso Mangoes' in prompt
        assert 'Seasonal Product' in prompt
        assert '2024-04-01' in prompt
        assert '2024-06-30' in prompt
        assert 'limited availability' in prompt.lower()
    
    def test_construct_prompt_with_all_features(self):
        """Test prompt construction with all features (GI tag, authenticity, seasonal)."""
        from generate_launch import construct_bedrock_prompt
        
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
            'authenticityConfidence': Decimal('98.0'),
            'seasonal': {
                'isSeasonal': True,
                'seasonStart': '2024-05-01',
                'seasonEnd': '2024-07-31'
            }
        }
        
        prompt = construct_bedrock_prompt(product)
        
        assert 'Kesar Mangoes' in prompt
        assert 'Gujarat' in prompt
        assert 'GI Tag' in prompt
        assert 'Authenticity Confidence: 98.0%' in prompt
        assert 'Seasonal Product' in prompt
        assert '2024-05-01' in prompt
    
    def test_construct_prompt_tone_and_format(self):
        """Test prompt specifies correct tone and format."""
        from generate_launch import construct_bedrock_prompt
        
        product = {
            'name': 'Test Product',
            'category': 'vegetables',
            'price': 100,
            'unit': 'kg',
            'description': 'Test description',
            'giTag': {'hasTag': False},
            'seasonal': {'isSeasonal': False}
        }
        
        prompt = construct_bedrock_prompt(product)
        
        assert 'Exciting and professional' in prompt
        assert '3-4 paragraphs' in prompt
        assert 'call-to-action' in prompt.lower()
        assert 'Opening paragraph' in prompt
        assert 'Middle paragraphs' in prompt
        assert 'Closing paragraph' in prompt


class TestBedrockInvocation:
    """Test cases for Bedrock API invocation."""
    
    @patch('generate_launch.bedrock_runtime')
    def test_invoke_bedrock_success(self, mock_bedrock):
        """Test successful Bedrock invocation."""
        from generate_launch import invoke_bedrock
        
        # Mock Bedrock response
        mock_response = {
            'body': MagicMock()
        }
        mock_response['body'].read.return_value = json.dumps({
            'content': [
                {
                    'text': 'Exciting news! We are thrilled to announce the launch of our premium Fresh Tomatoes...\n\nOrder now and experience the difference!'
                }
            ]
        }).encode('utf-8')
        
        mock_bedrock.invoke_model.return_value = mock_response
        
        result = invoke_bedrock('Test prompt')
        
        assert 'Exciting news!' in result
        assert 'Order now' in result
        mock_bedrock.invoke_model.assert_called_once()
        
        # Verify correct model and parameters
        call_kwargs = mock_bedrock.invoke_model.call_args[1]
        assert call_kwargs['modelId'] == 'anthropic.claude-3-haiku-20240307-v1:0'
        
        body = json.loads(call_kwargs['body'])
        assert body['temperature'] == 0.7
        assert body['max_tokens'] == 700
    
    @patch('generate_launch.bedrock_runtime')
    def test_invoke_bedrock_empty_response(self, mock_bedrock):
        """Test Bedrock invocation with empty response."""
        from generate_launch import invoke_bedrock
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
    
    @patch('generate_launch.bedrock_runtime')
    def test_invoke_bedrock_api_error(self, mock_bedrock):
        """Test Bedrock invocation with API error."""
        from generate_launch import invoke_bedrock
        from backend.shared.exceptions import ServiceUnavailableError
        
        mock_bedrock.invoke_model.side_effect = Exception('Bedrock API error')
        
        with pytest.raises(ServiceUnavailableError):
            invoke_bedrock('Test prompt')
    
    @patch('generate_launch.bedrock_runtime')
    def test_invoke_bedrock_empty_text_content(self, mock_bedrock):
        """Test Bedrock invocation with empty text content."""
        from generate_launch import invoke_bedrock
        from backend.shared.exceptions import ServiceUnavailableError
        
        # Mock response with empty text
        mock_response = {
            'body': MagicMock()
        }
        mock_response['body'].read.return_value = json.dumps({
            'content': [
                {
                    'text': ''
                }
            ]
        }).encode('utf-8')
        
        mock_bedrock.invoke_model.return_value = mock_response
        
        with pytest.raises(ServiceUnavailableError):
            invoke_bedrock('Test prompt')


class TestLambdaHandler:
    """Test cases for Lambda handler function."""
    
    @patch('generate_launch.validate_jwt_token')
    @patch('generate_launch.get_item')
    @patch('generate_launch.invoke_bedrock')
    def test_handler_success(
        self,
        mock_invoke_bedrock,
        mock_get_item,
        mock_verify_token
    ):
        """Test successful launch announcement generation."""
        from generate_launch import handler
        
        # Mock JWT verification
        mock_verify_token.return_value = {
            'userId': 'farmer-123',
            'role': 'farmer'
        }
        
        # Mock product retrieval
        mock_get_item.return_value = {
            'productId': 'product-123',
            'farmerId': 'farmer-123',
            'name': 'Fresh Tomatoes',
            'category': 'vegetables',
            'price': Decimal('50'),
            'unit': 'kg',
            'description': 'Locally grown tomatoes',
            'giTag': {'hasTag': False},
            'seasonal': {'isSeasonal': False}
        }
        
        # Mock Bedrock response
        mock_invoke_bedrock.return_value = 'Exciting news! We are thrilled to announce the launch of our premium Fresh Tomatoes. Grown locally with care, these tomatoes bring farm-fresh quality to your table.\n\nOur tomatoes are hand-picked at peak ripeness, ensuring maximum flavor and nutrition. Perfect for salads, cooking, or enjoying fresh, they represent the best of local agriculture.\n\nDon\'t miss this opportunity to experience truly fresh produce. Order now and taste the difference that quality makes!'
        
        event = {
            'headers': {'Authorization': 'Bearer valid-token'},
            'body': json.dumps({'productId': 'product-123'})
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['productId'] == 'product-123'
        assert 'launchAnnouncement' in body
        assert 'Exciting news!' in body['launchAnnouncement']
        assert 'Order now' in body['launchAnnouncement']
    
    @patch('generate_launch.validate_jwt_token')
    @patch('generate_launch.get_item')
    @patch('generate_launch.invoke_bedrock')
    def test_handler_success_with_gi_tag(
        self,
        mock_invoke_bedrock,
        mock_get_item,
        mock_verify_token
    ):
        """Test successful launch announcement for product with GI tag."""
        from generate_launch import handler
        
        # Mock JWT verification
        mock_verify_token.return_value = {
            'userId': 'farmer-123',
            'role': 'farmer'
        }
        
        # Mock product retrieval with GI tag
        mock_get_item.return_value = {
            'productId': 'product-123',
            'farmerId': 'farmer-123',
            'name': 'Darjeeling Tea',
            'category': 'spices',
            'price': Decimal('500'),
            'unit': 'kg',
            'description': 'Premium tea leaves',
            'giTag': {
                'hasTag': True,
                'tagName': 'Darjeeling Tea',
                'region': 'West Bengal'
            },
            'seasonal': {'isSeasonal': False},
            'authenticityConfidence': Decimal('98.5')
        }
        
        # Mock Bedrock response
        mock_invoke_bedrock.return_value = 'Introducing authentic Darjeeling Tea with GI certification from West Bengal!'
        
        event = {
            'headers': {'Authorization': 'Bearer valid-token'},
            'body': json.dumps({'productId': 'product-123'})
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['productId'] == 'product-123'
        assert 'launchAnnouncement' in body
    
    def test_handler_missing_authorization(self):
        """Test handler with missing authorization header."""
        from generate_launch import handler
        
        event = {
            'headers': {},
            'body': json.dumps({'productId': 'product-123'})
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 401
        body = json.loads(response['body'])
        assert body['error']['code'] == 'UNAUTHORIZED'
    
    @patch('generate_launch.validate_jwt_token')
    def test_handler_consumer_role_forbidden(self, mock_verify_token):
        """Test handler rejects consumer role."""
        from generate_launch import handler
        
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
    
    @patch('generate_launch.validate_jwt_token')
    def test_handler_missing_product_id(self, mock_verify_token):
        """Test handler with missing productId."""
        from generate_launch import handler
        
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
    
    @patch('generate_launch.validate_jwt_token')
    @patch('generate_launch.get_item')
    def test_handler_product_not_found(
        self,
        mock_get_item,
        mock_verify_token
    ):
        """Test handler with non-existent product."""
        from generate_launch import handler
        
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
    
    @patch('generate_launch.validate_jwt_token')
    @patch('generate_launch.get_item')
    def test_handler_wrong_farmer(
        self,
        mock_get_item,
        mock_verify_token
    ):
        """Test handler rejects farmer accessing another farmer's product."""
        from generate_launch import handler
        
        mock_verify_token.return_value = {
            'userId': 'farmer-123',
            'role': 'farmer'
        }
        
        # Product belongs to different farmer
        mock_get_item.return_value = {
            'productId': 'product-123',
            'farmerId': 'farmer-456',
            'name': 'Product',
            'giTag': {'hasTag': False},
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
    
    @patch('generate_launch.validate_jwt_token')
    @patch('generate_launch.get_item')
    @patch('generate_launch.invoke_bedrock')
    def test_handler_bedrock_failure(
        self,
        mock_invoke_bedrock,
        mock_get_item,
        mock_verify_token
    ):
        """Test handler with Bedrock service failure."""
        from generate_launch import handler
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
    
    @patch('generate_launch.validate_jwt_token')
    @patch('generate_launch.get_item')
    @patch('generate_launch.invoke_bedrock')
    def test_handler_unexpected_error(
        self,
        mock_invoke_bedrock,
        mock_get_item,
        mock_verify_token
    ):
        """Test handler with unexpected error."""
        from generate_launch import handler
        
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
        
        # Simulate unexpected error
        mock_invoke_bedrock.side_effect = RuntimeError('Unexpected error')
        
        event = {
            'headers': {'Authorization': 'Bearer valid-token'},
            'body': json.dumps({'productId': 'product-123'})
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 500
        body = json.loads(response['body'])
        assert body['error']['code'] == 'INTERNAL_ERROR'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
