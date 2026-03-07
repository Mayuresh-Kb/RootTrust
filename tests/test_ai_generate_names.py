"""
Unit tests for AI product name suggestion endpoint.
Tests the name generation functionality.
"""
import json
import pytest
import sys
from unittest.mock import Mock, patch, MagicMock

# Add backend to path for imports
sys.path.insert(0, 'backend/shared')
sys.path.insert(0, 'backend/ai')


class TestPromptConstruction:
    """Test cases for Bedrock prompt construction."""
    
    def test_construct_prompt_basic_product(self):
        """Test prompt construction for basic product without GI tag."""
        from generate_names import construct_bedrock_prompt
        
        product_details = {
            'name': 'Fresh Tomatoes',
            'category': 'vegetables',
            'description': 'Locally grown tomatoes',
            'giTag': {'hasTag': False}
        }
        
        prompt = construct_bedrock_prompt(product_details)
        
        assert 'Fresh Tomatoes' in prompt
        assert 'vegetables' in prompt
        assert 'Locally grown tomatoes' in prompt
        assert 'QUALITY-FOCUSED' in prompt
        assert 'ORIGIN-FOCUSED' in prompt
        assert 'BENEFIT-FOCUSED' in prompt
        assert 'exactly 3 name variations' in prompt
    
    def test_construct_prompt_with_gi_tag(self):
        """Test prompt construction for product with GI tag."""
        from generate_names import construct_bedrock_prompt
        
        product_details = {
            'name': 'Darjeeling Tea',
            'category': 'spices',
            'description': 'Premium tea leaves',
            'giTag': {
                'hasTag': True,
                'tagName': 'Darjeeling Tea',
                'region': 'West Bengal'
            }
        }
        
        prompt = construct_bedrock_prompt(product_details)
        
        assert 'Darjeeling Tea' in prompt
        assert 'West Bengal' in prompt
        assert 'GI Tag' in prompt
        assert 'incorporate the region' in prompt
    
    def test_construct_prompt_no_description(self):
        """Test prompt handles missing description."""
        from generate_names import construct_bedrock_prompt
        
        product_details = {
            'name': 'Organic Rice',
            'category': 'grains',
            'description': 'No description provided',
            'giTag': {'hasTag': False}
        }
        
        prompt = construct_bedrock_prompt(product_details)
        
        assert 'Organic Rice' in prompt
        assert 'No description provided' in prompt


class TestBedrockInvocation:
    """Test cases for Bedrock API invocation."""
    
    @patch('generate_names.bedrock_runtime')
    def test_invoke_bedrock_success(self, mock_bedrock):
        """Test successful Bedrock invocation with 3 names."""
        from generate_names import invoke_bedrock
        
        # Mock Bedrock response with JSON array
        mock_response = {
            'body': MagicMock()
        }
        mock_response['body'].read.return_value = json.dumps({
            'content': [
                {
                    'text': '["Premium Farm-Fresh Tomatoes", "Authentic Local Tomatoes", "Healthy Garden Tomatoes"]'
                }
            ]
        }).encode('utf-8')
        
        mock_bedrock.invoke_model.return_value = mock_response
        
        result = invoke_bedrock('Test prompt')
        
        assert len(result) == 3
        assert result[0] == 'Premium Farm-Fresh Tomatoes'
        assert result[1] == 'Authentic Local Tomatoes'
        assert result[2] == 'Healthy Garden Tomatoes'
        
        # Verify correct model and parameters
        call_kwargs = mock_bedrock.invoke_model.call_args[1]
        assert call_kwargs['modelId'] == 'anthropic.claude-3-haiku-20240307-v1:0'
        
        body = json.loads(call_kwargs['body'])
        assert body['temperature'] == 0.8
        assert body['max_tokens'] == 300
    
    @patch('generate_names.bedrock_runtime')
    def test_invoke_bedrock_with_markdown_json(self, mock_bedrock):
        """Test Bedrock response with JSON wrapped in markdown code block."""
        from generate_names import invoke_bedrock
        
        # Mock Bedrock response with markdown
        mock_response = {
            'body': MagicMock()
        }
        mock_response['body'].read.return_value = json.dumps({
            'content': [
                {
                    'text': '```json\n["Name One", "Name Two", "Name Three"]\n```'
                }
            ]
        }).encode('utf-8')
        
        mock_bedrock.invoke_model.return_value = mock_response
        
        result = invoke_bedrock('Test prompt')
        
        assert len(result) == 3
        assert result[0] == 'Name One'
        assert result[1] == 'Name Two'
        assert result[2] == 'Name Three'
    
    @patch('generate_names.bedrock_runtime')
    def test_invoke_bedrock_with_whitespace(self, mock_bedrock):
        """Test Bedrock response with extra whitespace in names."""
        from generate_names import invoke_bedrock
        
        mock_response = {
            'body': MagicMock()
        }
        mock_response['body'].read.return_value = json.dumps({
            'content': [
                {
                    'text': '[" Name One ", "  Name Two", "Name Three  "]'
                }
            ]
        }).encode('utf-8')
        
        mock_bedrock.invoke_model.return_value = mock_response
        
        result = invoke_bedrock('Test prompt')
        
        # Verify whitespace is stripped
        assert result[0] == 'Name One'
        assert result[1] == 'Name Two'
        assert result[2] == 'Name Three'
    
    @patch('generate_names.bedrock_runtime')
    def test_invoke_bedrock_wrong_count(self, mock_bedrock):
        """Test Bedrock invocation with wrong number of names."""
        from generate_names import invoke_bedrock
        from backend.shared.exceptions import ServiceUnavailableError
        
        # Mock response with only 2 names
        mock_response = {
            'body': MagicMock()
        }
        mock_response['body'].read.return_value = json.dumps({
            'content': [
                {
                    'text': '["Name One", "Name Two"]'
                }
            ]
        }).encode('utf-8')
        
        mock_bedrock.invoke_model.return_value = mock_response
        
        with pytest.raises(ServiceUnavailableError) as exc_info:
            invoke_bedrock('Test prompt')
        
        assert 'Expected 3 names' in str(exc_info.value)
    
    @patch('generate_names.bedrock_runtime')
    def test_invoke_bedrock_not_array(self, mock_bedrock):
        """Test Bedrock invocation with non-array response."""
        from generate_names import invoke_bedrock
        from backend.shared.exceptions import ServiceUnavailableError
        
        # Mock response with object instead of array
        mock_response = {
            'body': MagicMock()
        }
        mock_response['body'].read.return_value = json.dumps({
            'content': [
                {
                    'text': '{"name1": "Test", "name2": "Test2", "name3": "Test3"}'
                }
            ]
        }).encode('utf-8')
        
        mock_bedrock.invoke_model.return_value = mock_response
        
        with pytest.raises(ServiceUnavailableError) as exc_info:
            invoke_bedrock('Test prompt')
        
        assert 'not a JSON array' in str(exc_info.value)
    
    @patch('generate_names.bedrock_runtime')
    def test_invoke_bedrock_empty_names(self, mock_bedrock):
        """Test Bedrock invocation with empty name strings."""
        from generate_names import invoke_bedrock
        from backend.shared.exceptions import ServiceUnavailableError
        
        # Mock response with empty strings
        mock_response = {
            'body': MagicMock()
        }
        mock_response['body'].read.return_value = json.dumps({
            'content': [
                {
                    'text': '["Name One", "", "Name Three"]'
                }
            ]
        }).encode('utf-8')
        
        mock_bedrock.invoke_model.return_value = mock_response
        
        with pytest.raises(ServiceUnavailableError) as exc_info:
            invoke_bedrock('Test prompt')
        
        assert 'cannot be empty' in str(exc_info.value)
    
    @patch('generate_names.bedrock_runtime')
    def test_invoke_bedrock_non_string_names(self, mock_bedrock):
        """Test Bedrock invocation with non-string names."""
        from generate_names import invoke_bedrock
        from backend.shared.exceptions import ServiceUnavailableError
        
        # Mock response with numbers instead of strings
        mock_response = {
            'body': MagicMock()
        }
        mock_response['body'].read.return_value = json.dumps({
            'content': [
                {
                    'text': '[123, "Name Two", "Name Three"]'
                }
            ]
        }).encode('utf-8')
        
        mock_bedrock.invoke_model.return_value = mock_response
        
        with pytest.raises(ServiceUnavailableError) as exc_info:
            invoke_bedrock('Test prompt')
        
        assert 'must be strings' in str(exc_info.value)
    
    @patch('generate_names.bedrock_runtime')
    def test_invoke_bedrock_empty_response(self, mock_bedrock):
        """Test Bedrock invocation with empty response."""
        from generate_names import invoke_bedrock
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
    
    @patch('generate_names.bedrock_runtime')
    def test_invoke_bedrock_invalid_json(self, mock_bedrock):
        """Test Bedrock invocation with invalid JSON."""
        from generate_names import invoke_bedrock
        from backend.shared.exceptions import ServiceUnavailableError
        
        # Mock response with invalid JSON
        mock_response = {
            'body': MagicMock()
        }
        mock_response['body'].read.return_value = json.dumps({
            'content': [
                {
                    'text': 'This is not valid JSON'
                }
            ]
        }).encode('utf-8')
        
        mock_bedrock.invoke_model.return_value = mock_response
        
        with pytest.raises(ServiceUnavailableError) as exc_info:
            invoke_bedrock('Test prompt')
        
        assert 'Failed to parse AI response' in str(exc_info.value)
    
    @patch('generate_names.bedrock_runtime')
    def test_invoke_bedrock_api_error(self, mock_bedrock):
        """Test Bedrock invocation with API error."""
        from generate_names import invoke_bedrock
        from backend.shared.exceptions import ServiceUnavailableError
        
        mock_bedrock.invoke_model.side_effect = Exception('Bedrock API error')
        
        with pytest.raises(ServiceUnavailableError):
            invoke_bedrock('Test prompt')


class TestLambdaHandler:
    """Test cases for Lambda handler function."""
    
    @patch('generate_names.validate_jwt_token')
    @patch('generate_names.invoke_bedrock')
    def test_handler_success(self, mock_invoke_bedrock, mock_verify_token):
        """Test successful name generation."""
        from generate_names import handler
        
        # Mock JWT verification
        mock_verify_token.return_value = {
            'userId': 'farmer-123',
            'role': 'farmer'
        }
        
        # Mock Bedrock response
        mock_invoke_bedrock.return_value = [
            'Premium Fresh Tomatoes',
            'Authentic Farm Tomatoes',
            'Healthy Garden Tomatoes'
        ]
        
        event = {
            'headers': {'Authorization': 'Bearer valid-token'},
            'body': json.dumps({
                'name': 'Tomatoes',
                'category': 'vegetables',
                'description': 'Fresh tomatoes from local farm'
            })
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert 'names' in body
        assert len(body['names']) == 3
        assert body['names'][0] == 'Premium Fresh Tomatoes'
        assert body['names'][1] == 'Authentic Farm Tomatoes'
        assert body['names'][2] == 'Healthy Garden Tomatoes'
    
    @patch('generate_names.validate_jwt_token')
    @patch('generate_names.invoke_bedrock')
    def test_handler_with_gi_tag(self, mock_invoke_bedrock, mock_verify_token):
        """Test name generation with GI tag."""
        from generate_names import handler
        
        mock_verify_token.return_value = {
            'userId': 'farmer-123',
            'role': 'farmer'
        }
        
        mock_invoke_bedrock.return_value = [
            'Premium Darjeeling Tea',
            'Authentic West Bengal Tea',
            'Healthy Mountain Tea'
        ]
        
        event = {
            'headers': {'Authorization': 'Bearer valid-token'},
            'body': json.dumps({
                'name': 'Tea',
                'category': 'spices',
                'description': 'Premium tea leaves',
                'giTag': {
                    'hasTag': True,
                    'tagName': 'Darjeeling Tea',
                    'region': 'West Bengal'
                }
            })
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert len(body['names']) == 3
    
    @patch('generate_names.validate_jwt_token')
    @patch('generate_names.invoke_bedrock')
    def test_handler_without_description(self, mock_invoke_bedrock, mock_verify_token):
        """Test name generation without description."""
        from generate_names import handler
        
        mock_verify_token.return_value = {
            'userId': 'farmer-123',
            'role': 'farmer'
        }
        
        mock_invoke_bedrock.return_value = ['Name 1', 'Name 2', 'Name 3']
        
        event = {
            'headers': {'Authorization': 'Bearer valid-token'},
            'body': json.dumps({
                'name': 'Rice',
                'category': 'grains'
            })
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert len(body['names']) == 3
    
    def test_handler_missing_authorization(self):
        """Test handler with missing authorization header."""
        from generate_names import handler
        
        event = {
            'headers': {},
            'body': json.dumps({
                'name': 'Tomatoes',
                'category': 'vegetables'
            })
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 401
        body = json.loads(response['body'])
        assert body['error']['code'] == 'UNAUTHORIZED'
    
    @patch('generate_names.validate_jwt_token')
    def test_handler_consumer_role_forbidden(self, mock_verify_token):
        """Test handler rejects consumer role."""
        from generate_names import handler
        
        # Mock JWT verification with consumer role
        mock_verify_token.return_value = {
            'userId': 'consumer-123',
            'role': 'consumer'
        }
        
        event = {
            'headers': {'Authorization': 'Bearer valid-token'},
            'body': json.dumps({
                'name': 'Tomatoes',
                'category': 'vegetables'
            })
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 403
        body = json.loads(response['body'])
        assert body['error']['code'] == 'FORBIDDEN'
        assert 'farmers' in body['error']['message'].lower()
    
    @patch('generate_names.validate_jwt_token')
    def test_handler_missing_name(self, mock_verify_token):
        """Test handler with missing name field."""
        from generate_names import handler
        
        mock_verify_token.return_value = {
            'userId': 'farmer-123',
            'role': 'farmer'
        }
        
        event = {
            'headers': {'Authorization': 'Bearer valid-token'},
            'body': json.dumps({
                'category': 'vegetables'
            })
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error']['code'] == 'VALIDATION_ERROR'
        assert 'name' in body['error']['message']
    
    @patch('generate_names.validate_jwt_token')
    def test_handler_missing_category(self, mock_verify_token):
        """Test handler with missing category field."""
        from generate_names import handler
        
        mock_verify_token.return_value = {
            'userId': 'farmer-123',
            'role': 'farmer'
        }
        
        event = {
            'headers': {'Authorization': 'Bearer valid-token'},
            'body': json.dumps({
                'name': 'Tomatoes'
            })
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error']['code'] == 'VALIDATION_ERROR'
        assert 'category' in body['error']['message']
    
    @patch('generate_names.validate_jwt_token')
    @patch('generate_names.invoke_bedrock')
    def test_handler_bedrock_failure(self, mock_invoke_bedrock, mock_verify_token):
        """Test handler with Bedrock service failure."""
        from generate_names import handler
        from backend.shared.exceptions import ServiceUnavailableError
        
        mock_verify_token.return_value = {
            'userId': 'farmer-123',
            'role': 'farmer'
        }
        
        mock_invoke_bedrock.side_effect = ServiceUnavailableError('Bedrock', 'Service error')
        
        event = {
            'headers': {'Authorization': 'Bearer valid-token'},
            'body': json.dumps({
                'name': 'Tomatoes',
                'category': 'vegetables'
            })
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 503
        body = json.loads(response['body'])
        assert body['error']['code'] == 'SERVICE_UNAVAILABLE'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
