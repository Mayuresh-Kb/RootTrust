"""
AI Marketing Lambda Function - Social Media Content Generation
POST /ai/generate-social

This function uses Amazon Bedrock to generate social media content for products,
with special urgency messaging for seasonal products nearing the end of their season.
"""
import json
import os
import boto3
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

# Import shared modules (available via Lambda Layer)
from database import get_item, put_item
from auth import validate_jwt_token
from constants import UserRole, MARKETING_CONTENT_CACHE_TTL
from exceptions import (
    ValidationError,
    ResourceNotFoundError,
    AuthorizationError,
    ServiceUnavailableError
)


# Initialize AWS clients
bedrock_runtime = boto3.client('bedrock-runtime', region_name=os.environ.get('BEDROCK_REGION', 'us-east-1'))


def get_cached_social(cache_key: str) -> Optional[str]:
    """
    Check if generated social content exists in cache (DynamoDB with TTL).
    
    Args:
        cache_key: Cache key string
        
    Returns:
        Cached social content if found and not expired, None otherwise
    """
    try:
        cache_item = get_item(
            pk=f"MARKETING_CACHE#{cache_key}",
            sk="SOCIAL"
        )
        
        if cache_item:
            # Check if cache is still valid (TTL not expired)
            ttl = cache_item.get('ttl', 0)
            current_time = int(datetime.utcnow().timestamp())
            
            if ttl > current_time:
                return cache_item.get('socialMediaContent', '')
        
        return None
    except Exception as e:
        print(f"Error checking cache: {str(e)}")
        return None


def store_social_cache(cache_key: str, social_content: str) -> None:
    """
    Store generated social content in cache with 7-day TTL.
    
    Args:
        cache_key: Cache key string
        social_content: Social media content to cache
    """
    try:
        ttl = int((datetime.utcnow() + timedelta(seconds=MARKETING_CONTENT_CACHE_TTL)).timestamp())
        
        cache_item = {
            'PK': f"MARKETING_CACHE#{cache_key}",
            'SK': 'SOCIAL',
            'EntityType': 'MarketingCache',
            'cacheKey': cache_key,
            'socialMediaContent': social_content,
            'cachedAt': datetime.utcnow().isoformat(),
            'ttl': ttl
        }
        
        put_item(cache_item)
    except Exception as e:
        print(f"Error storing cache: {str(e)}")


def check_seasonal_urgency(product: Dict[str, Any]) -> tuple[bool, int]:
    """
    Check if product is seasonal and near season end (within 7 days).
    
    Args:
        product: Product data dictionary
        
    Returns:
        Tuple of (is_urgent, days_remaining)
        - is_urgent: True if seasonal and within 7 days of season end
        - days_remaining: Number of days until season end (0 if not seasonal)
    """
    seasonal_info = product.get('seasonal', {})
    is_seasonal = seasonal_info.get('isSeasonal', False)
    
    if not is_seasonal:
        return False, 0
    
    season_end_str = seasonal_info.get('seasonEnd')
    if not season_end_str:
        return False, 0
    
    try:
        # Parse season end date (ISO 8601 format)
        season_end = datetime.fromisoformat(season_end_str.replace('Z', '+00:00'))
        current_date = datetime.utcnow()
        
        # Calculate days remaining using date comparison (ignore time component)
        days_remaining = (season_end.date() - current_date.date()).days
        
        # Check if within 7 days of season end
        is_urgent = 0 <= days_remaining <= 7
        
        return is_urgent, max(0, days_remaining)
    except (ValueError, AttributeError) as e:
        print(f"Error parsing season end date: {str(e)}")
        return False, 0


def construct_bedrock_prompt(product: Dict[str, Any], is_urgent: bool, days_remaining: int) -> str:
    """
    Construct prompt for Bedrock social media content generation.
    Includes urgency focus if product is seasonal and near season end.
    
    Args:
        product: Product data dictionary
        is_urgent: Whether product is near season end
        days_remaining: Days until season end
        
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
    
    # Build urgency context
    urgency_context = ""
    if is_urgent:
        urgency_context = f"""

CRITICAL: This product is SEASONAL and the season ends in {days_remaining} day{'s' if days_remaining != 1 else ''}!
You MUST include urgency-focused language:
- "Limited time" / "Ending soon" / "Last chance"
- "Only {days_remaining} day{'s' if days_remaining != 1 else ''} left"
- "Don't miss out" / "Act now"
- Create FOMO (fear of missing out)
- Emphasize scarcity and time sensitivity"""
    
    prompt = f"""You are an expert social media marketing copywriter for an agricultural marketplace. Create engaging social media content for the following product.

Product Information:
- Name: {product.get('name', 'Unknown')}
- Category: {product.get('category', 'Unknown')}
- Price: ₹{product.get('price', 0)} per {product.get('unit', 'unit')}
- Description: {product.get('description', 'No description provided')}{gi_details}{authenticity_info}{urgency_context}

Guidelines:
- Write 2-3 short paragraphs optimized for Facebook and Instagram
- Total length: 100-150 words
- Use engaging, conversational tone
- Include relevant emojis (2-4 total) to increase engagement
- Emphasize benefits and value to customers
- Include a clear call-to-action (e.g., "Order now", "Shop today", "Get yours before it's gone")
- Make it shareable and appealing
- If GI tag is present, highlight authenticity and origin
- If urgency applies, make it the PRIMARY focus of the message

Format:
- Start with an attention-grabbing opening
- Middle paragraph with key benefits/features
- End with strong call-to-action
- Add 3-5 relevant hashtags at the end

Write ONLY the social media post content, no additional commentary or labels."""
    
    return prompt


def invoke_bedrock(prompt: str) -> str:
    """
    Invoke Amazon Bedrock with the social media content generation prompt.
    Uses Claude 3 Haiku for cost efficiency.
    
    Args:
        prompt: Formatted prompt string
        
    Returns:
        Generated social media content from Bedrock
        
    Raises:
        ServiceUnavailableError: If Bedrock invocation fails
    """
    try:
        # Use Claude 3 Haiku for cost efficiency
        model_id = "anthropic.claude-3-haiku-20240307-v1:0"
        
        # Construct request body for Claude 3
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 400,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.8  # Higher temperature for creative social media content
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
    Lambda handler for AI social media content generation endpoint.
    
    POST /ai/generate-social
    
    Request body:
    {
        "productId": "uuid"
    }
    
    Response:
    {
        "productId": "uuid",
        "socialMediaContent": "Engaging social media post...",
        "isUrgent": false,
        "daysRemaining": 0
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
                        'message': 'Only farmers can generate social media content'
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
                        'message': 'You can only generate content for your own products'
                    }
                })
            }
        
        # Check if product is seasonal and near season end
        is_urgent, days_remaining = check_seasonal_urgency(product_item)
        
        print(f"Seasonal urgency check: is_urgent={is_urgent}, days_remaining={days_remaining}")
        
        # Generate cache key based on product ID and urgency status
        cache_key = f"{product_id}|social|{is_urgent}|{days_remaining}"
        
        # Check cache first
        cached_social = get_cached_social(cache_key)
        if cached_social:
            print(f"Cache hit for social content with key {cache_key}")
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'productId': product_id,
                    'socialMediaContent': cached_social,
                    'isUrgent': is_urgent,
                    'daysRemaining': days_remaining,
                    'cached': True
                })
            }
        
        # Construct Bedrock prompt with urgency focus if applicable
        prompt = construct_bedrock_prompt(product_item, is_urgent, days_remaining)
        
        # Invoke Bedrock for social media content generation
        social_media_content = invoke_bedrock(prompt)
        
        # Store in cache with 7-day TTL
        store_social_cache(cache_key, social_media_content)
        
        # Return response
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'productId': product_id,
                'socialMediaContent': social_media_content,
                'isUrgent': is_urgent,
                'daysRemaining': days_remaining,
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
