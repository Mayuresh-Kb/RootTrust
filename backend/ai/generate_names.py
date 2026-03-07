"""
AI Marketing Lambda Function - Product Name Suggestion
POST /ai/generate-names

This function uses Amazon Bedrock to generate 3 creative product name variations
that emphasize different value propositions (quality, origin, benefit).
"""
import json
import os
import boto3
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

# Import shared modules (available via Lambda Layer)
from database import get_item, put_item
from auth import validate_jwt_token
from constants import UserRole, ProductCategory, MARKETING_CONTENT_CACHE_TTL
from exceptions import (
    ValidationError,
    ResourceNotFoundError,
    AuthorizationError,
    ServiceUnavailableError
)


# Initialize AWS clients
bedrock_runtime = boto3.client('bedrock-runtime', region_name=os.environ.get('BEDROCK_REGION', 'us-east-1'))


def generate_cache_key(product_details: Dict[str, Any]) -> str:
    """
    Generate a cache key based on product details.
    
    Args:
        product_details: Product data dictionary
        
    Returns:
        Hash string to use as cache key
    """
    # Create a stable string representation of the product details
    cache_input = f"{product_details.get('name', '')}|{product_details.get('category', '')}|{product_details.get('description', '')}|{product_details.get('giTag', {}).get('hasTag', False)}"
    
    # Generate SHA256 hash
    return hashlib.sha256(cache_input.encode()).hexdigest()


def get_cached_names(cache_key: str) -> Optional[List[str]]:
    """
    Check if generated names exist in cache (DynamoDB with TTL).
    
    Args:
        cache_key: Cache key hash
        
    Returns:
        Cached names list if found and not expired, None otherwise
    """
    try:
        cache_item = get_item(
            pk=f"MARKETING_CACHE#{cache_key}",
            sk="NAMES"
        )
        
        if cache_item:
            # Check if cache is still valid (TTL not expired)
            ttl = cache_item.get('ttl', 0)
            current_time = int(datetime.utcnow().timestamp())
            
            if ttl > current_time:
                return cache_item.get('generatedNames', [])
        
        return None
    except Exception as e:
        print(f"Error checking cache: {str(e)}")
        return None


def store_names_cache(cache_key: str, names: List[str]) -> None:
    """
    Store generated names in cache with 7-day TTL.
    
    Args:
        cache_key: Cache key hash
        names: Generated names list to cache
    """
    try:
        ttl = int((datetime.utcnow() + timedelta(seconds=MARKETING_CONTENT_CACHE_TTL)).timestamp())
        
        cache_item = {
            'PK': f"MARKETING_CACHE#{cache_key}",
            'SK': 'NAMES',
            'EntityType': 'MarketingCache',
            'cacheKey': cache_key,
            'generatedNames': names,
            'cachedAt': datetime.utcnow().isoformat(),
            'ttl': ttl
        }
        
        put_item(cache_item)
    except Exception as e:
        print(f"Error storing cache: {str(e)}")


def construct_bedrock_prompt(product_details: Dict[str, Any]) -> str:
    """
    Construct prompt for Bedrock product name generation.
    Requests 3 name variations emphasizing different value propositions.
    
    Args:
        product_details: Product data dictionary
        
    Returns:
        Formatted prompt string
    """
    gi_tag_info = product_details.get('giTag', {})
    has_gi_tag = gi_tag_info.get('hasTag', False)
    gi_details = ""
    
    if has_gi_tag:
        gi_details = f"\n- GI Tag: {gi_tag_info.get('tagName', 'N/A')} from {gi_tag_info.get('region', 'N/A')}"
    
    prompt = f"""You are an expert marketing copywriter for an agricultural marketplace. Generate 3 creative product name variations for a farmer's product.

Product Information:
- Current Name: {product_details.get('name', 'Unknown')}
- Category: {product_details.get('category', 'Unknown')}
- Description: {product_details.get('description', 'No description provided')}{gi_details}

IMPORTANT: Generate exactly 3 name variations, each emphasizing a DIFFERENT value proposition:
1. QUALITY-FOCUSED: Emphasize premium quality, freshness, or superior characteristics
2. ORIGIN-FOCUSED: Emphasize geographical origin, authenticity, or traditional methods
3. BENEFIT-FOCUSED: Emphasize health benefits, taste experience, or customer outcomes

Guidelines:
- Each name should be 2-5 words
- Make names memorable, appealing, and marketable
- Use descriptive adjectives that evoke positive emotions
- Keep names natural and not overly salesy
- Ensure names are appropriate for the product category
- If the product has a GI tag, incorporate the region in the origin-focused name

Format your response as a JSON array with exactly 3 names:
["Name 1", "Name 2", "Name 3"]

Respond ONLY with the JSON array, no additional text or explanation."""
    
    return prompt


def invoke_bedrock(prompt: str) -> List[str]:
    """
    Invoke Amazon Bedrock with the name generation prompt.
    Uses Claude 3 Haiku for cost efficiency.
    
    Args:
        prompt: Formatted prompt string
        
    Returns:
        List of 3 generated product names
        
    Raises:
        ServiceUnavailableError: If Bedrock invocation fails
    """
    try:
        # Use Claude 3 Haiku for cost efficiency
        model_id = "anthropic.claude-3-haiku-20240307-v1:0"
        
        # Construct request body for Claude 3
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 300,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.8  # Higher temperature for more creative name variations
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
            
            # Parse JSON array from response
            # Handle potential markdown code blocks
            if '```json' in text_content:
                # Extract JSON from markdown code block
                start = text_content.find('[')
                end = text_content.rfind(']') + 1
                if start != -1 and end > start:
                    text_content = text_content[start:end]
            elif '```' in text_content:
                # Remove any code block markers
                text_content = text_content.replace('```', '').strip()
            
            # Parse the JSON array
            names = json.loads(text_content)
            
            # Validate we got exactly 3 names
            if not isinstance(names, list):
                raise ValueError("Response is not a JSON array")
            
            if len(names) != 3:
                raise ValueError(f"Expected 3 names, got {len(names)}")
            
            # Validate all names are strings
            if not all(isinstance(name, str) for name in names):
                raise ValueError("All names must be strings")
            
            # Validate names are not empty
            if not all(name.strip() for name in names):
                raise ValueError("Names cannot be empty")
            
            return [name.strip() for name in names]
        else:
            raise ValueError("Empty response from Bedrock")
            
    except json.JSONDecodeError as e:
        print(f"JSON parsing error: {str(e)}")
        raise ServiceUnavailableError('Bedrock', f'Failed to parse AI response: {str(e)}')
    except Exception as e:
        print(f"Bedrock invocation error: {str(e)}")
        raise ServiceUnavailableError('Bedrock', f'Failed to invoke AI model: {str(e)}')


def handler(event, context):
    """
    Lambda handler for AI product name suggestion endpoint.
    
    POST /ai/generate-names
    
    Request body:
    {
        "name": "Current product name",
        "category": "vegetables",
        "description": "Product description",
        "giTag": {
            "hasTag": true,
            "tagName": "Darjeeling Tea",
            "region": "West Bengal"
        }
    }
    
    Response:
    {
        "names": ["Name 1", "Name 2", "Name 3"]
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
                        'message': 'Only farmers can generate product names'
                    }
                })
            }
        
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        
        # Validate required fields
        name = body.get('name')
        category = body.get('category')
        description = body.get('description')
        
        if not name:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'error': {
                        'code': 'VALIDATION_ERROR',
                        'message': 'name is required'
                    }
                })
            }
        
        if not category:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'error': {
                        'code': 'VALIDATION_ERROR',
                        'message': 'category is required'
                    }
                })
            }
        
        # Construct product details for prompt
        product_details = {
            'name': name,
            'category': category,
            'description': description or 'No description provided',
            'giTag': body.get('giTag', {'hasTag': False})
        }
        
        # Generate cache key based on product details
        cache_key = generate_cache_key(product_details)
        
        # Check cache first
        cached_names = get_cached_names(cache_key)
        if cached_names:
            print(f"Cache hit for names with key {cache_key}")
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'names': cached_names,
                    'cached': True
                })
            }
        
        # Construct Bedrock prompt requesting 3 name variations
        prompt = construct_bedrock_prompt(product_details)
        
        # Invoke Bedrock for name generation
        generated_names = invoke_bedrock(prompt)
        
        # Store in cache with 7-day TTL
        store_names_cache(cache_key, generated_names)
        
        # Return response
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'names': generated_names,
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
