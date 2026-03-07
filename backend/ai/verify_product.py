"""
AI Verification Lambda Function - Bedrock Fraud Detection
POST /ai/verify-product

This function uses Amazon Bedrock to analyze products for fraud detection,
calculate market prices, and determine verification status.
"""
import json
import os
import boto3
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from decimal import Decimal

# Import shared modules (available via Lambda Layer)
from models import Product
from database import get_item, update_item, put_item
from auth import validate_jwt_token
from constants import (
    FRAUD_RISK_THRESHOLD,
    VERIFICATION_CACHE_TTL,
    VerificationStatus,
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


def get_cached_verification(product_id: str) -> Optional[Dict[str, Any]]:
    """
    Check if a verification result exists in cache (DynamoDB with TTL).
    
    Args:
        product_id: Product ID to check
        
    Returns:
        Cached verification data if found and not expired, None otherwise
    """
    try:
        cache_item = get_item(
            pk=f"VERIFICATION_CACHE#{product_id}",
            sk="LATEST"
        )
        
        if cache_item:
            # Check if cache is still valid (TTL not expired)
            ttl = cache_item.get('ttl', 0)
            current_time = int(datetime.utcnow().timestamp())
            
            if ttl > current_time:
                return {
                    'fraudRiskScore': float(cache_item.get('fraudRiskScore', 0)),
                    'authenticityConfidence': float(cache_item.get('authenticityConfidence', 0)),
                    'aiExplanation': cache_item.get('aiExplanation', ''),
                    'predictedMarketPrice': float(cache_item.get('predictedMarketPrice', 0)),
                    'verificationStatus': cache_item.get('verificationStatus', 'pending')
                }
        
        return None
    except Exception as e:
        print(f"Error checking cache: {str(e)}")
        return None


def store_verification_cache(product_id: str, verification_data: Dict[str, Any]) -> None:
    """
    Store verification result in cache with TTL.
    
    Args:
        product_id: Product ID
        verification_data: Verification results to cache
    """
    try:
        ttl = int((datetime.utcnow() + timedelta(seconds=VERIFICATION_CACHE_TTL)).timestamp())
        
        cache_item = {
            'PK': f"VERIFICATION_CACHE#{product_id}",
            'SK': 'LATEST',
            'EntityType': 'VerificationCache',
            'productId': product_id,
            'fraudRiskScore': Decimal(str(verification_data['fraudRiskScore'])),
            'authenticityConfidence': Decimal(str(verification_data['authenticityConfidence'])),
            'aiExplanation': verification_data['aiExplanation'],
            'predictedMarketPrice': Decimal(str(verification_data['predictedMarketPrice'])),
            'verificationStatus': verification_data['verificationStatus'],
            'cachedAt': datetime.utcnow().isoformat(),
            'ttl': ttl
        }
        
        put_item(cache_item)
    except Exception as e:
        print(f"Error storing cache: {str(e)}")


def calculate_market_price(product: Dict[str, Any]) -> float:
    """
    Calculate predicted market price based on product attributes.
    
    Args:
        product: Product data dictionary
        
    Returns:
        Predicted market price
    """
    # Base prices by category (per kg/unit)
    base_prices = {
        ProductCategory.VEGETABLES.value: 50.0,
        ProductCategory.FRUITS.value: 80.0,
        ProductCategory.GRAINS.value: 40.0,
        ProductCategory.SPICES.value: 200.0,
        ProductCategory.DAIRY.value: 60.0
    }
    
    category = product.get('category', 'vegetables')
    base_price = base_prices.get(category, 50.0)
    
    # Apply GI tag premium (20% increase)
    gi_tag = product.get('giTag', {})
    if gi_tag.get('hasTag', False):
        base_price *= 1.2
    
    # Apply seasonal factor
    seasonal = product.get('seasonal', {})
    if seasonal.get('isSeasonal', False):
        # Check if currently in season
        try:
            season_start = seasonal.get('seasonStart')
            season_end = seasonal.get('seasonEnd')
            
            if season_start and season_end:
                current_date = datetime.utcnow()
                start_date = datetime.fromisoformat(season_start.replace('Z', '+00:00'))
                end_date = datetime.fromisoformat(season_end.replace('Z', '+00:00'))
                
                if start_date <= current_date <= end_date:
                    # In season: 10% discount
                    base_price *= 0.9
                else:
                    # Out of season: 30% premium
                    base_price *= 1.3
        except Exception as e:
            print(f"Error calculating seasonal factor: {str(e)}")
    
    return round(base_price, 2)


def construct_bedrock_prompt(product: Dict[str, Any]) -> str:
    """
    Construct prompt for Bedrock fraud detection analysis.
    
    Args:
        product: Product data dictionary
        
    Returns:
        Formatted prompt string
    """
    gi_tag_info = product.get('giTag', {})
    gi_status = "Yes" if gi_tag_info.get('hasTag', False) else "No"
    gi_details = f" (Tag: {gi_tag_info.get('tagName', 'N/A')}, Region: {gi_tag_info.get('region', 'N/A')})" if gi_status == "Yes" else ""
    
    prompt = f"""You are an AI fraud detection system for an agricultural marketplace. Analyze the following product listing for authenticity and fraud risk.

Product Details:
- Name: {product.get('name', 'Unknown')}
- Category: {product.get('category', 'Unknown')}
- Price: ₹{product.get('price', 0)} per {product.get('unit', 'unit')}
- Description: {product.get('description', 'No description provided')}
- GI Tag (Geographical Indication): {gi_status}{gi_details}
- Invoice Document: {"Provided" if product.get('invoiceDocumentUrl') else "Not provided"}

Please analyze this product and provide:
1. Fraud Risk Score (0-100): A numerical score where 0 means no fraud risk and 100 means extremely high fraud risk
2. Authenticity Confidence (0-100): Your confidence percentage that this product is authentic
3. Explanation: A brief explanation of your assessment (2-3 sentences)

Consider factors such as:
- Price reasonableness for the category and GI tag status
- Description quality and consistency
- Presence of supporting documentation
- GI tag claims (if any)

Respond in the following JSON format:
{{
  "fraudRiskScore": <number 0-100>,
  "authenticityConfidence": <number 0-100>,
  "explanation": "<your explanation>"
}}"""
    
    return prompt


def invoke_bedrock(prompt: str) -> Dict[str, Any]:
    """
    Invoke Amazon Bedrock with the fraud detection prompt.
    
    Args:
        prompt: Formatted prompt string
        
    Returns:
        Parsed response from Bedrock
        
    Raises:
        ServiceUnavailableError: If Bedrock invocation fails
    """
    try:
        # Use Claude 3 Haiku for cost efficiency (Claude 2 is being deprecated)
        model_id = "anthropic.claude-3-haiku-20240307-v1:0"
        
        # Construct request body for Claude 3
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.3  # Lower temperature for more consistent results
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
            text_content = content[0].get('text', '')
            
            # Try to extract JSON from the response
            # Claude might wrap JSON in markdown code blocks
            if '```json' in text_content:
                json_start = text_content.find('```json') + 7
                json_end = text_content.find('```', json_start)
                text_content = text_content[json_start:json_end].strip()
            elif '```' in text_content:
                json_start = text_content.find('```') + 3
                json_end = text_content.find('```', json_start)
                text_content = text_content[json_start:json_end].strip()
            
            # Parse JSON response
            result = json.loads(text_content)
            
            # Validate response structure
            if 'fraudRiskScore' not in result or 'authenticityConfidence' not in result or 'explanation' not in result:
                raise ValueError("Invalid response structure from Bedrock")
            
            # Ensure scores are within valid range
            result['fraudRiskScore'] = max(0, min(100, float(result['fraudRiskScore'])))
            result['authenticityConfidence'] = max(0, min(100, float(result['authenticityConfidence'])))
            
            return result
        else:
            raise ValueError("Empty response from Bedrock")
            
    except Exception as e:
        print(f"Bedrock invocation error: {str(e)}")
        raise ServiceUnavailableError('Bedrock', f'Failed to invoke AI model: {str(e)}')


def update_product_verification(product_id: str, verification_data: Dict[str, Any]) -> None:
    """
    Update product record with verification results.
    
    Args:
        product_id: Product ID
        verification_data: Verification results
    """
    update_expression = """
        SET verificationStatus = :status,
            fraudRiskScore = :fraud_score,
            authenticityConfidence = :auth_confidence,
            aiExplanation = :explanation,
            predictedMarketPrice = :market_price,
            updatedAt = :updated_at,
            GSI3PK = :gsi3pk
    """
    
    expression_values = {
        ':status': verification_data['verificationStatus'],
        ':fraud_score': Decimal(str(verification_data['fraudRiskScore'])),
        ':auth_confidence': Decimal(str(verification_data['authenticityConfidence'])),
        ':explanation': verification_data['aiExplanation'],
        ':market_price': Decimal(str(verification_data['predictedMarketPrice'])),
        ':updated_at': datetime.utcnow().isoformat(),
        ':gsi3pk': f"STATUS#{verification_data['verificationStatus']}"
    }
    
    update_item(
        pk=f"PRODUCT#{product_id}",
        sk="METADATA",
        update_expression=update_expression,
        expression_attribute_values=expression_values
    )


def handler(event, context):
    """
    Lambda handler for AI product verification endpoint.
    
    POST /ai/verify-product
    
    Request body:
    {
        "productId": "uuid"
    }
    
    Response:
    {
        "fraudRiskScore": 45.5,
        "authenticityConfidence": 85.0,
        "predictedMarketPrice": 120.50,
        "aiExplanation": "Product appears authentic...",
        "verificationStatus": "approved",
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
        
        # Check if user is farmer or admin
        user_role = user_data.get('role')
        if user_role not in [UserRole.FARMER.value, 'admin']:
            return {
                'statusCode': 403,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'error': {
                        'code': 'FORBIDDEN',
                        'message': 'Only farmers and admins can verify products'
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
        cached_result = get_cached_verification(product_id)
        if cached_result:
            print(f"Cache hit for product {product_id}")
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    **cached_result,
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
        
        # If farmer, verify they own the product
        if user_role == UserRole.FARMER.value:
            if product_item.get('farmerId') != user_data.get('userId'):
                return {
                    'statusCode': 403,
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps({
                        'error': {
                            'code': 'FORBIDDEN',
                            'message': 'You can only verify your own products'
                        }
                    })
                }
        
        # Calculate predicted market price
        predicted_price = calculate_market_price(product_item)
        
        # Construct Bedrock prompt
        prompt = construct_bedrock_prompt(product_item)
        
        # Invoke Bedrock for fraud analysis
        bedrock_result = invoke_bedrock(prompt)
        
        # Determine verification status based on fraud risk score
        fraud_score = bedrock_result['fraudRiskScore']
        verification_status = VerificationStatus.FLAGGED.value if fraud_score > FRAUD_RISK_THRESHOLD else VerificationStatus.APPROVED.value
        
        # Prepare verification data
        verification_data = {
            'fraudRiskScore': fraud_score,
            'authenticityConfidence': bedrock_result['authenticityConfidence'],
            'aiExplanation': bedrock_result['explanation'],
            'predictedMarketPrice': predicted_price,
            'verificationStatus': verification_status
        }
        
        # Update product record
        update_product_verification(product_id, verification_data)
        
        # Store in cache
        store_verification_cache(product_id, verification_data)
        
        # Return response
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                **verification_data,
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
