"""
AI Marketing Lambda Function - Launch Announcement Generation
POST /ai/generate-launch

This function uses Amazon Bedrock to generate launch announcement content
for new products, suitable for email newsletters and website announcements.
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


def get_cached_launch(product_id: str) -> Optional[str]:
    """
    Check if a generated launch announcement exists in cache (DynamoDB with TTL).
    
    Args:
        product_id: Product ID to check
        
    Returns:
        Cached launch announcement if found and not expired, None otherwise
    """
    try:
        cache_item = get_item(
            pk=f"MARKETING_CACHE#{product_id}",
            sk="LAUNCH"
        )
        
        if cache_item:
            # Check if cache is still valid (TTL not expired)
            ttl = cache_item.get('ttl', 0)
            current_time = int(datetime.utcnow().timestamp())
            
            if ttl > current_time:
                return cache_item.get('launchAnnouncement', '')
        
        return None
    except Exception as e:
        print(f"Error checking cache: {str(e)}")
        return None


def store_launch_cache(product_id: str, launch_announcement: str) -> None:
    """
    Store generated launch announcement in cache with 7-day TTL.
    
    Args:
        product_id: Product ID
        launch_announcement: Launch announcement to cache
    """
    try:
        ttl = int((datetime.utcnow() + timedelta(seconds=MARKETING_CONTENT_CACHE_TTL)).timestamp())
        
        cache_item = {
            'PK': f"MARKETING_CACHE#{product_id}",
            'SK': 'LAUNCH',
            'EntityType': 'MarketingCache',
            'productId': product_id,
            'launchAnnouncement': launch_announcement,
            'cachedAt': datetime.utcnow().isoformat(),
            'ttl': ttl
        }
        
        put_item(cache_item)
    except Exception as e:
        print(f"Error storing cache: {str(e)}")


def construct_bedrock_prompt(product: Dict[str, Any]) -> str:
    """
    Construct prompt for Bedrock launch announcement generation.
    Creates exciting, professional content suitable for newsletters and announcements.
    
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
    
    # Get seasonal information
    seasonal_info = product.get('seasonal', {})
    is_seasonal = seasonal_info.get('isSeasonal', False)
    seasonal_details = ""
    if is_seasonal:
        seasonal_details = f"\n- Seasonal Product: Available from {seasonal_info.get('seasonStart', 'N/A')} to {seasonal_info.get('seasonEnd', 'N/A')}"
    
    prompt = f"""You are an expert marketing copywriter for an agricultural marketplace. Write an exciting launch announcement for a new product that will be used in email newsletters and website announcements.

Product Information:
- Name: {product.get('name', 'Unknown')}
- Category: {product.get('category', 'Unknown')}
- Price: ₹{product.get('price', 0)} per {product.get('unit', 'unit')}
- Description: {product.get('description', 'No description provided')}{gi_details}{authenticity_info}{seasonal_details}

Guidelines:
- Write 3-4 paragraphs (200-300 words total)
- Tone: Exciting and professional, suitable for email newsletters
- Start with an attention-grabbing announcement headline or opening
- Emphasize what makes this product special and worth trying
- Include key benefits and unique selling points
- If GI tag is present, highlight authenticity and regional heritage
- If seasonal, mention limited availability
- Create excitement and anticipation
- End with a clear call-to-action encouraging customers to try the product
- Make it suitable for both email newsletters and website announcements
- Use professional language that builds trust while generating enthusiasm

Format:
- Opening paragraph: Announce the product launch with excitement
- Middle paragraphs: Highlight key features, benefits, and what makes it special
- Closing paragraph: Strong call-to-action and availability information

Write ONLY the launch announcement content, no additional commentary or labels."""
    
    return prompt


def invoke_bedrock(prompt: str) -> str:
    """
    Invoke Amazon Bedrock with the launch announcement generation prompt.
    Uses Claude 3 Haiku for cost efficiency.
    
    Args:
        prompt: Formatted prompt string
        
    Returns:
        Generated launch announcement from Bedrock
        
    Raises:
        ServiceUnavailableError: If Bedrock invocation fails
    """
    try:
        # Use Claude 3 Haiku for cost efficiency
        model_id = "anthropic.claude-3-haiku-20240307-v1:0"
        
        # Construct request body for Claude 3
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 700,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.7  # Balanced creativity for professional content
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
    Lambda handler for AI launch announcement generation endpoint.
    
    POST /ai/generate-launch
    
    Request body:
    {
        "productId": "uuid"
    }
    
    Response:
    {
        "productId": "uuid",
        "launchAnnouncement": "Exciting launch announcement content..."
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
                        'message': 'Only farmers can generate launch announcements'
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
                        'message': 'You can only generate announcements for your own products'
                    }
                })
            }
        
        # Check cache first
        cached_launch = get_cached_launch(product_id)
        if cached_launch:
            print(f"Cache hit for launch announcement for product {product_id}")
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'productId': product_id,
                    'launchAnnouncement': cached_launch,
                    'cached': True
                })
            }
        
        # Construct Bedrock prompt for launch announcement
        prompt = construct_bedrock_prompt(product_item)
        
        # Invoke Bedrock for launch announcement generation
        launch_announcement = invoke_bedrock(prompt)
        
        # Store in cache with 7-day TTL
        store_launch_cache(product_id, launch_announcement)
        
        # Return response
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'productId': product_id,
                'launchAnnouncement': launch_announcement,
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
