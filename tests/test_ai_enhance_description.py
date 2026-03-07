"""
Unit tests for AI description enhancement endpoint
POST /ai/enhance-description
"""
import json
import pytest
import sys
from unittest.mock import patch, MagicMock
from decimal import Decimal

# Add backend to path for imports
sys.path.insert(0, 'backend/shared')
sys.path.insert(0, 'backend/ai')


# Mock JWT token verification
@pytest.fixture
def mock_jwt_verify():
    with patch('enhance_description.validate_jwt_token') as mock:
        mock.return_value = {
            'userId': 'farmer-123',
            'role': 'farmer',
            'email': 'farmer@example.com'
        }
        yield mock


# Mock Bedrock client
@pytest.fixture
def mock_bedrock():
    with patch('enhance_description.bedrock_runtime') as mock:
        yield mock


class TestConstructBedrockPrompt:
    """Test Bedrock prompt construction"""
    
    def test_prompt_includes_original_description(self):
        """Prompt should include the original description"""
        from enhance_description import construct_bedrock_prompt
        
        description = "Fresh organic tomatoes from my farm"
        prompt = construct_bedrock_prompt(description)
        
        assert description in prompt
        assert "Original Description:" in prompt
    
    def test_prompt_requests_sensory_language(self):
        """Prompt should request sensory enhancements"""
        from enhance_description import construct_bedrock_prompt
        
        description = "Fresh tomatoes"
        prompt = construct_bedrock_prompt(description)
        
        assert "SENSORY LANGUAGE" in prompt
        assert "Taste:" in prompt
        assert "Smell:" in prompt
        assert "Texture:" in prompt
        assert "Appearance:" in prompt
    
    def test_prompt_requests_benefit_statements(self):
        """Prompt should request benefit statements"""
        from enhance_description import construct_bedrock_prompt
        
        description = "Fresh tomatoes"
        prompt = construct_bedrock_prompt(description)
        
        assert "BENEFIT STATEMENTS" in prompt
        assert "Health benefits" in prompt
        assert "Culinary uses" in prompt
    
    def test_prompt_emphasizes_factual_accuracy(self):
        """Prompt should emphasize preserving factual accuracy"""
        from enhance_description import construct_bedrock_prompt
        
        description = "Fresh tomatoes"
        prompt = construct_bedrock_prompt(description)
        
        assert "factual accuracy" in prompt.lower()
        assert "unchanged" in prompt.lower() or "preserve" in prompt.lower()


class TestInvokeBedrock:
    """Test Bedrock invocation"""
    
    def test_invoke_bedrock_success(self, mock_bedrock):
        """Should successfully invoke Bedrock and return enhanced description"""
        from enhance_description import invoke_bedrock
        
        # Mock Bedrock response
        mock_response = {
            'body': MagicMock()
        }
        mock_response['body'].read.return_value = json.dumps({
            'content': [
                {
                    'text': 'Enhanced description with vivid sensory details and benefits'
                }
            ]
        }).encode('utf-8')
        
        mock_bedrock.invoke_model.return_value = mock_response
        
        prompt = "Test prompt"
        result = invoke_bedrock(prompt)
        
        assert result == 'Enhanced description with vivid sensory details and benefits'
        assert mock_bedrock.invoke_model.called
        
        # Verify correct model is used
        call_args = mock_bedrock.invoke_model.call_args
        assert call_args[1]['modelId'] == 'anthropic.claude-3-haiku-20240307-v1:0'
    
    def test_invoke_bedrock_uses_correct_parameters(self, mock_bedrock):
        """Should use correct Bedrock parameters"""
        from enhance_description import invoke_bedrock
        
        mock_response = {
            'body': MagicMock()
        }
        mock_response['body'].read.return_value = json.dumps({
            'content': [{'text': 'Enhanced text'}]
        }).encode('utf-8')
        
        mock_bedrock.invoke_model.return_value = mock_response
        
        prompt = "Test prompt"
        invoke_bedrock(prompt)
        
        call_args = mock_bedrock.invoke_model.call_args
        request_body = json.loads(call_args[1]['body'])
        
        assert request_body['anthropic_version'] == 'bedrock-2023-05-31'
        assert request_body['max_tokens'] == 600
        assert request_body['temperature'] == 0.7
        assert request_body['messages'][0]['role'] == 'user'
        assert request_body['messages'][0]['content'] == prompt
    
    def test_invoke_bedrock_empty_response(self, mock_bedrock):
        """Should raise error on empty Bedrock response"""
        from enhance_description import invoke_bedrock
        from backend.shared.exceptions import ServiceUnavailableError
        
        mock_response = {
            'body': MagicMock()
        }
        mock_response['body'].read.return_value = json.dumps({
            'content': []
        }).encode('utf-8')
        
        mock_bedrock.invoke_model.return_value = mock_response
        
        with pytest.raises(ServiceUnavailableError):
            invoke_bedrock("Test prompt")
    
    def test_invoke_bedrock_handles_exception(self, mock_bedrock):
        """Should handle Bedrock invocation exceptions"""
        from enhance_description import invoke_bedrock
        from backend.shared.exceptions import ServiceUnavailableError
        
        mock_bedrock.invoke_model.side_effect = Exception("Bedrock error")
        
        with pytest.raises(ServiceUnavailableError) as exc_info:
            invoke_bedrock("Test prompt")
        
        assert "Failed to invoke AI model" in str(exc_info.value)


class TestEnhanceDescriptionHandler:
    """Test Lambda handler for description enhancement"""
    
    def test_enhance_description_success(self, mock_jwt_verify, mock_bedrock):
        """Should successfully enhance description"""
        from enhance_description import handler
        
        # Mock Bedrock response
        mock_response = {
            'body': MagicMock()
        }
        enhanced_text = "These vibrant, sun-ripened organic tomatoes burst with sweet, tangy flavor and a juicy texture. Rich in antioxidants and vitamins, they're perfect for fresh salads, pasta sauces, or simply enjoying with a sprinkle of salt."
        mock_response['body'].read.return_value = json.dumps({
            'content': [{'text': enhanced_text}]
        }).encode('utf-8')
        
        mock_bedrock.invoke_model.return_value = mock_response
        
        event = {
            'headers': {
                'Authorization': 'Bearer valid-token'
            },
            'body': json.dumps({
                'description': 'Fresh organic tomatoes from my farm'
            })
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['originalDescription'] == 'Fresh organic tomatoes from my farm'
        assert body['enhancedDescription'] == enhanced_text
        assert mock_bedrock.invoke_model.called
    
    def test_missing_authorization_header(self):
        """Should return 401 when authorization header is missing"""
        from enhance_description import handler
        
        event = {
            'headers': {},
            'body': json.dumps({
                'description': 'Test description'
            })
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 401
        body = json.loads(response['body'])
        assert body['error']['code'] == 'UNAUTHORIZED'
    
    def test_non_farmer_role_forbidden(self, mock_jwt_verify):
        """Should return 403 when user is not a farmer"""
        from enhance_description import handler
        
        mock_jwt_verify.return_value = {
            'userId': 'consumer-123',
            'role': 'consumer',
            'email': 'consumer@example.com'
        }
        
        event = {
            'headers': {
                'Authorization': 'Bearer valid-token'
            },
            'body': json.dumps({
                'description': 'Test description'
            })
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 403
        body = json.loads(response['body'])
        assert body['error']['code'] == 'FORBIDDEN'
        assert 'farmers' in body['error']['message'].lower()
    
    def test_missing_description(self, mock_jwt_verify):
        """Should return 400 when description is missing"""
        from enhance_description import handler
        
        event = {
            'headers': {
                'Authorization': 'Bearer valid-token'
            },
            'body': json.dumps({})
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error']['code'] == 'VALIDATION_ERROR'
        assert 'description is required' in body['error']['message']
    
    def test_empty_description(self, mock_jwt_verify):
        """Should return 400 when description is empty or too short"""
        from enhance_description import handler
        
        event = {
            'headers': {
                'Authorization': 'Bearer valid-token'
            },
            'body': json.dumps({
                'description': '   '
            })
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error']['code'] == 'VALIDATION_ERROR'
    
    def test_description_too_short(self, mock_jwt_verify):
        """Should return 400 when description is less than 10 characters"""
        from enhance_description import handler
        
        event = {
            'headers': {
                'Authorization': 'Bearer valid-token'
            },
            'body': json.dumps({
                'description': 'Short'
            })
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error']['code'] == 'VALIDATION_ERROR'
        assert 'at least 10 characters' in body['error']['message']
    
    def test_description_whitespace_trimmed(self, mock_jwt_verify, mock_bedrock):
        """Should trim whitespace from description"""
        from enhance_description import handler
        
        mock_response = {
            'body': MagicMock()
        }
        mock_response['body'].read.return_value = json.dumps({
            'content': [{'text': 'Enhanced description'}]
        }).encode('utf-8')
        
        mock_bedrock.invoke_model.return_value = mock_response
        
        event = {
            'headers': {
                'Authorization': 'Bearer valid-token'
            },
            'body': json.dumps({
                'description': '  Fresh organic tomatoes  '
            })
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['originalDescription'] == 'Fresh organic tomatoes'
    
    def test_bedrock_service_unavailable(self, mock_jwt_verify, mock_bedrock):
        """Should return 503 when Bedrock is unavailable"""
        from enhance_description import handler
        
        mock_bedrock.invoke_model.side_effect = Exception("Service unavailable")
        
        event = {
            'headers': {
                'Authorization': 'Bearer valid-token'
            },
            'body': json.dumps({
                'description': 'Fresh organic tomatoes from my farm'
            })
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 503
        body = json.loads(response['body'])
        assert body['error']['code'] == 'SERVICE_UNAVAILABLE'
    
    def test_handles_invalid_json_body(self, mock_jwt_verify):
        """Should handle invalid JSON in request body"""
        from enhance_description import handler
        
        event = {
            'headers': {
                'Authorization': 'Bearer valid-token'
            },
            'body': 'invalid json'
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 500
        body = json.loads(response['body'])
        assert body['error']['code'] == 'INTERNAL_ERROR'
    
    def test_authorization_header_case_insensitive(self, mock_jwt_verify, mock_bedrock):
        """Should handle authorization header case-insensitively"""
        from enhance_description import handler
        
        mock_response = {
            'body': MagicMock()
        }
        mock_response['body'].read.return_value = json.dumps({
            'content': [{'text': 'Enhanced description'}]
        }).encode('utf-8')
        
        mock_bedrock.invoke_model.return_value = mock_response
        
        event = {
            'headers': {
                'authorization': 'Bearer valid-token'  # lowercase
            },
            'body': json.dumps({
                'description': 'Fresh organic tomatoes'
            })
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 200


class TestIntegrationScenarios:
    """Integration test scenarios"""
    
    def test_complete_enhancement_flow(self, mock_jwt_verify, mock_bedrock):
        """Test complete flow from request to enhanced description"""
        from enhance_description import handler
        
        # Setup
        original_desc = "Fresh organic tomatoes grown in my farm using traditional methods"
        enhanced_desc = "These vibrant, sun-ripened organic tomatoes burst with sweet, tangy flavor and a juicy, firm texture. Grown using time-honored traditional methods, each tomato is packed with antioxidants and vitamins. Perfect for fresh salads, homemade pasta sauces, or simply enjoying with a drizzle of olive oil and fresh basil."
        
        mock_response = {
            'body': MagicMock()
        }
        mock_response['body'].read.return_value = json.dumps({
            'content': [{'text': enhanced_desc}]
        }).encode('utf-8')
        
        mock_bedrock.invoke_model.return_value = mock_response
        
        # Execute
        event = {
            'headers': {
                'Authorization': 'Bearer farmer-token'
            },
            'body': json.dumps({
                'description': original_desc
            })
        }
        
        response = handler(event, None)
        
        # Verify
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['originalDescription'] == original_desc
        assert body['enhancedDescription'] == enhanced_desc
        assert len(body['enhancedDescription']) > len(body['originalDescription'])
        
        # Verify Bedrock was called with correct prompt
        call_args = mock_bedrock.invoke_model.call_args
        request_body = json.loads(call_args[1]['body'])
        prompt = request_body['messages'][0]['content']
        assert original_desc in prompt
        assert 'SENSORY LANGUAGE' in prompt
        assert 'BENEFIT STATEMENTS' in prompt


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
