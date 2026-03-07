"""
AI Marketing Lambda Function - Product Description Generation
POST /ai/generate-description

This function uses Amazon Bedrock to generate compelling product descriptions
that emphasize dream outcome and likelihood of achievement.
"""
import json
import os
import boto3
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from decimal import Decimal

# Import shared modules (available via Lambda Layer)
from models import Product
from database import get_item, put_item
from auth import validate_jwt_token
from constants import (
    MARKETING_CONTENT_CACHE_TTL,
    UserRole,
    ProductCategory
)
from exceptions import (
    ValidationError,
    ResourceNotFoundError,
    AuthorizationError,
    ServiceUnavailableError
)


# Initialize AWS clients
bedrock_runtime = boto3.client('bedrock-runtime', region_name=os.environ.get('BEDROCK_REGION', 'us-east-1'))


def get_cached_description(product_id: str) -> Optional[str]:
    """
    Check if a generated description exists in cache (DynamoDB with TTL).
    
    Args:
        product_id: Product ID to check
        
    Returns:
        Cached description if found and not expired, None otherwise
    """
    try:
        cache_item = get_item(
            pk=f"MARKETING_CACHE#{product_id}",
            sk="DESCRIPTION"
        )
        
        if cache_item:
            # Check if cache is still valid (TTL not expired)
            ttl = cache_item.get('ttl', 0)
            current_time = int(datetime.utcnow().timestamp())
            
            if ttl > current_time:
                return cache_item.get('generatedDescription', '')
        
        return None
    except Exception as e:
        print(f"Error checking cache: {str(e)}")
        return None


def store_description_cache(product_id: str, description: str) -> None:
    """
    Store generated description in cache with 7-day TTL.
    
    Args:
        product_id: Product ID
        description: Generated description to cache
    """
    try:
        ttl = int((datetime.utcnow() + timedelta(seconds=MARKETING_CONTENT_CACHE_TTL)).timestamp())
        
        cache_item = {
            'PK': f"MARKETING_CACHE#{product_id}",
            'SK': 'DESCRIPTION',
            'EntityType': 'MarketingCache',
            'productId': product_id,
            'generatedDescription': description,
            'cachedAt': datetime.utcnow().isoformat(),
            'ttl': ttl
        }
        
        put_item(cache_item)
    except Exception as e:
        print(f"Error storing cache: {str(e)}")


def construct_bedrock_prompt(product: Dict[str, Any]) -> str:
    """
    Construct prompt for Bedrock marketing content generation.
    Emphasizes dream outcome and likelihood of achievement.
    
    Args:
        product: Product data dictionary
        
    Returns:
        Formatted prompt string
    """
    gi_tag_info = product.get('giTag', {})
    has_gi_tag = gi_tag_info.get('hasTag', False)
    gi_details = ""
    
    if has_gi_tag:
        gi_details = f"\n- GI Tag: {gi_tag_info.get('tagName', 'N/A')} from {gi_tag_info.get('region', 'N/A')}"
    
    # Get authenticity confidence if available
    authenticity_confidence = product.get('authenticityConfidence')
    authenticity_info = ""
    if authenticity_confidence:
        authenticity_info = f"\n- Authenticity Confidence: {float(authenticity_confidence)}%"
    
    prompt = f"""You are an expert marketing copywriter for an agricultural marketplace. Write a compelling product description that helps farmers sell their produce to consumers.

Product Information:
- Name: {product.get('name', 'Unknown')}
- Category: {product.get('category', 'Unknown')}
- Price: ₹{product.get('price', 0)} per {product.get('unit', 'unit')}
- Current Description: {product.get('description', 'No description provided')}{gi_details}{authenticity_info}

IMPORTANT: Focus on the VALUE EQUATION - emphasize:
1. DREAM OUTCOME: What amazing result will the customer achieve? (health benefits, taste experience, culinary success, family satisfaction)
2. PERCEIVED LIKELIHOOD: Why should they trust this will deliver? (GI tag authenticity, farmer reputation, quality guarantees, freshness)

Guidelines:
- Write 2-3 paragraphs (150-200 words total)
- Start with the dream outcome - paint a vivid picture of the benefit
- Include sensory language (taste, smell, texture, appearance)
- Emphasize trust signals (GI tag, authenticity, direct from farmer)
- Highlight what makes this product special and worth buying
- Use emotional, benefit-driven language, not just features
- Keep it natural and conversational, not overly salesy

Write ONLY the product description, no additional commentary or labels."""
    
    return prompt


def invoke_bedrock(prompt: str) -> str:
    """
    Invoke Amazon Bedrock with the marketing content generation prompt.
    Uses Claude Instant for cost efficiency.
    
    Args:
        prompt: Formatted prompt string
        
    Returns:
        Generated description from Bedrock
        
    Raises:
        ServiceUnavailableError: If Bedrock invocation fails
    """
    try:
        # Use Claude 3 Haiku for cost efficiency (Claude Instant is being deprecated)
        model_id = "anthropic.claude-3-haiku-20240307-v1:0"
        
        # Construct request body for Claude 3
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 500,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.7  # Higher temperature for more creative marketing content
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
    Lambda handler for AI product description generation endpoint.
    
    POST /ai/generate-description
    
    Request body:
    {
        "productId": "uuid"
    }
    
    Response:
    {
        "productId": "uuid",
        "generatedDescription": "Compelling marketing description...",
        "cached": false
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
                        'message': 'Only farmers can generate marketing content'
                    }
                })
            }
        
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        product_id = body.get('productId')
        
        if not product_id:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'error': {
                        'code': 'VALIDATION_ERROR',
                        'message': 'productId is required'
                    }
                })
            }
        
        # Check cache first
        cached_description = get_cached_description(product_id)
        if cached_description:
            print(f"Cache hit for product {product_id}")
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'productId': product_id,
                    'generatedDescription': cached_description,
                    'cached': True
                })
            }
        
        # Retrieve product from DynamoDB
        product_item = get_item(
            pk=f"PRODUCT#{product_id}",
            sk="METADATA"
        )
        
        if not product_item:
            return {
                'statusCode': 404,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'error': {
                        'code': 'NOT_FOUND',
                        'message': f'Product {product_id} not found'
                    }
                })
            }
        
        # Verify farmer owns the product
        if product_item.get('farmerId') != user_data.get('userId'):
            return {
                'statusCode': 403,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'error': {
                        'code': 'FORBIDDEN',
                        'message': 'You can only generate descriptions for your own products'
                    }
                })
            }
        
        # Construct Bedrock prompt emphasizing dream outcome and likelihood
        prompt = construct_bedrock_prompt(product_item)
        
        # Invoke Bedrock for description generation
        generated_description = invoke_bedrock(prompt)
        
        # Store in cache with 7-day TTL
        store_description_cache(product_id, generated_description)
        
        # Return response
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'productId': product_id,
                'generatedDescription': generated_description,
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
    except ResourceNotFoundError as e:
        return {
            'statusCode': 404,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'error': {
                    'code': 'NOT_FOUND',
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
