"""
AI Marketing Lambda Function - Description Enhancement
POST /ai/enhance-description

This function uses Amazon Bedrock to enhance farmer-provided descriptions
with sensory language (taste, smell, texture, appearance) and benefit statements.
"""
import json
import os
import boto3
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

# Import shared modules (available via Lambda Layer)
from database import get_item, put_item
from auth import validate_jwt_token
from constants import UserRole, MARKETING_CONTENT_CACHE_TTL
from exceptions import (
    ValidationError,
    AuthorizationError,
    ServiceUnavailableError
)


# Initialize AWS clients
bedrock_runtime = boto3.client('bedrock-runtime', region_name=os.environ.get('BEDROCK_REGION', 'us-east-1'))


def generate_cache_key(description: str) -> str:
    """
    Generate a cache key based on description text.
    
    Args:
        description: Original description text
        
    Returns:
        Hash string to use as cache key
    """
    # Generate SHA256 hash of the description
    return hashlib.sha256(description.encode()).hexdigest()


def get_cached_enhancement(cache_key: str) -> Optional[str]:
    """
    Check if an enhanced description exists in cache (DynamoDB with TTL).
    
    Args:
        cache_key: Cache key hash
        
    Returns:
        Cached enhanced description if found and not expired, None otherwise
    """
    try:
        cache_item = get_item(
            pk=f"MARKETING_CACHE#{cache_key}",
            sk="ENHANCEMENT"
        )
        
        if cache_item:
            # Check if cache is still valid (TTL not expired)
            ttl = cache_item.get('ttl', 0)
            current_time = int(datetime.utcnow().timestamp())
            
            if ttl > current_time:
                return cache_item.get('enhancedDescription', '')
        
        return None
    except Exception as e:
        print(f"Error checking cache: {str(e)}")
        return None


def store_enhancement_cache(cache_key: str, enhanced_description: str) -> None:
    """
    Store enhanced description in cache with 7-day TTL.
    
    Args:
        cache_key: Cache key hash
        enhanced_description: Enhanced description to cache
    """
    try:
        ttl = int((datetime.utcnow() + timedelta(seconds=MARKETING_CONTENT_CACHE_TTL)).timestamp())
        
        cache_item = {
            'PK': f"MARKETING_CACHE#{cache_key}",
            'SK': 'ENHANCEMENT',
            'EntityType': 'MarketingCache',
            'cacheKey': cache_key,
            'enhancedDescription': enhanced_description,
            'cachedAt': datetime.utcnow().isoformat(),
            'ttl': ttl
        }
        
        put_item(cache_item)
    except Exception as e:
        print(f"Error storing cache: {str(e)}")


def construct_bedrock_prompt(original_description: str) -> str:
    """
    Construct prompt for Bedrock description enhancement.
    Focuses on adding sensory language and benefit statements.
    
    Args:
        original_description: Farmer-provided description to enhance
        
    Returns:
        Formatted prompt string
    """
    prompt = f"""You are an expert marketing copywriter for an agricultural marketplace. Enhance the following product description by adding sensory language and benefit statements while preserving factual accuracy.

Original Description:
{original_description}

IMPORTANT: Enhance the description by:
1. SENSORY LANGUAGE: Add vivid descriptions of:
   - Taste: flavor profiles, sweetness, richness, etc.
   - Smell: aroma, fragrance, scent characteristics
   - Texture: crispness, smoothness, juiciness, etc.
   - Appearance: color, shape, visual appeal

2. BENEFIT STATEMENTS: Emphasize:
   - Health benefits (nutrition, wellness)
   - Culinary uses (cooking applications, recipe ideas)
   - Quality indicators (freshness, authenticity)
   - Customer satisfaction (family meals, special occasions)

Guidelines:
- Keep the core facts from the original description unchanged
- Add 2-3 sentences of sensory and benefit enhancements
- Make it natural and conversational, not overly promotional
- Total length should be 150-250 words
- Maintain the farmer's authentic voice while making it more compelling
- Do not make false claims or add information not implied by the original

Write ONLY the enhanced description, no additional commentary or labels."""
    
    return prompt


def invoke_bedrock(prompt: str) -> str:
    """
    Invoke Amazon Bedrock with the description enhancement prompt.
    Uses Claude 3 Haiku for cost efficiency.
    
    Args:
        prompt: Formatted prompt string
        
    Returns:
        Enhanced description from Bedrock
        
    Raises:
        ServiceUnavailableError: If Bedrock invocation fails
    """
    try:
        # Use Claude 3 Haiku for cost efficiency
        model_id = "anthropic.claude-3-haiku-20240307-v1:0"
        
        # Construct request body for Claude 3
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 600,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.7  # Balanced creativity for enhancement
        }
        
        # Invoke Bedrock
        response = bedrock_runtime.invoke_model(
            modelId=model_id,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(request_body)
        )
        
        # Parse response
        response_body = json.loads(response['body'].read())
        
        # Extract content from Claude 3 response format
        content = response_body.get('content', [])
        if content and len(content) > 0:
            text_content = content[0].get('text', '').strip()
            
            if not text_content:
                raise ValueError("Empty response from Bedrock")
            
            return text_content
        else:
            raise ValueError("Empty response from Bedrock")
            
    except Exception as e:
        print(f"Bedrock invocation error: {str(e)}")
        raise ServiceUnavailableError('Bedrock', f'Failed to invoke AI model: {str(e)}')


def handler(event, context):
    """
    Lambda handler for AI description enhancement endpoint.
    
    POST /ai/enhance-description
    
    Request body:
    {
        "description": "Farmer-provided product description"
    }
    
    Response:
    {
        "originalDescription": "Original text...",
        "enhancedDescription": "Enhanced text with sensory language..."
    }
    """
    try:
        print(f"Event: {json.dumps(event)}")
        
        # Extract JWT token from headers
        headers = event.get('headers', {})
        auth_header = headers.get('Authorization') or headers.get('authorization')
        
        if not auth_header:
            return {
                'statusCode': 401,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'error': {
                        'code': 'UNAUTHORIZED',
                        'message': 'Missing authorization token'
                    }
                })
            }
        
        # Verify JWT token
        token = auth_header.replace('Bearer ', '')
        user_data = validate_jwt_token(token)
        
        # Check if user is farmer
        user_role = user_data.get('role')
        if user_role != UserRole.FARMER.value:
            return {
                'statusCode': 403,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'error': {
                        'code': 'FORBIDDEN',
                        'message': 'Only farmers can enhance descriptions'
                    }
                })
            }
        
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        description = body.get('description')
        
        if not description:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'error': {
                        'code': 'VALIDATION_ERROR',
                        'message': 'description is required'
                    }
                })
            }
        
        # Validate description is not empty or too short
        description = description.strip()
        if len(description) < 10:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'error': {
                        'code': 'VALIDATION_ERROR',
                        'message': 'description must be at least 10 characters'
                    }
                })
            }
        
        # Generate cache key based on description
        cache_key = generate_cache_key(description)
        
        # Check cache first
        cached_enhancement = get_cached_enhancement(cache_key)
        if cached_enhancement:
            print(f"Cache hit for enhancement with key {cache_key}")
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'originalDescription': description,
                    'enhancedDescription': cached_enhancement,
                    'cached': True
                })
            }
        
        # Construct Bedrock prompt for enhancement
        prompt = construct_bedrock_prompt(description)
        
        # Invoke Bedrock for description enhancement
        enhanced_description = invoke_bedrock(prompt)
        
        # Store in cache with 7-day TTL
        store_enhancement_cache(cache_key, enhanced_description)
        
        # Return response
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'originalDescription': description,
                'enhancedDescription': enhanced_description,
                'cached': False
            })
        }
        
    except ValidationError as e:
        return {
            'statusCode': 400,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'error': {
                    'code': 'VALIDATION_ERROR',
                    'message': str(e)
                }
            })
        }
    except AuthorizationError as e:
        return {
            'statusCode': 403,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'error': {
                    'code': 'FORBIDDEN',
                    'message': str(e)
                }
            })
        }
    except ServiceUnavailableError as e:
        return {
            'statusCode': 503,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'error': {
                    'code': 'SERVICE_UNAVAILABLE',
                    'message': str(e)
                }
            })
        }
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'error': {
                    'code': 'INTERNAL_ERROR',
                    'message': 'An unexpected error occurred'
                }
            })
        }
