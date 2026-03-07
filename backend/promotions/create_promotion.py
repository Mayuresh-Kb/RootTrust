"""
Promotion creation Lambda handler for RootTrust marketplace.
Handles POST /promotions endpoint for farmers to create product promotions.
"""
import json
import os
import uuid
import boto3
from datetime import datetime, timedelta
from typing import Dict, Any

# Import shared modules
import sys
sys.path.append('/opt/python')

from models import Promotion, PromotionMetrics
from validators import PromotionCreateRequest, validate_request_body
from database import get_item, put_item, update_item
from auth import get_user_from_token
from constants import UserRole, PromotionStatus
from exceptions import (
    ValidationError, AuthenticationError, AuthorizationError,
    ResourceNotFoundError, ConflictError, ServiceUnavailableError
)


# Initialize Bedrock client
bedrock_runtime = boto3.client('bedrock-runtime', region_name=os.environ.get('BEDROCK_REGION', 'us-east-1'))


def generate_promotional_ad_copy(product_name: str, product_description: str, product_category: str) -> str:
    """
    Generate AI promotional ad copy using Amazon Bedrock.
    
    Args:
        product_name: Name of the product
        product_description: Product description
        product_category: Product category
        
    Returns:
        AI-generated promotional ad copy
    """
    try:
        # Construct prompt for promotional ad copy
        prompt = f"""Generate compelling promotional ad copy for the following agricultural product:

Product Name: {product_name}
Category: {product_category}
Description: {product_description}

Create a short, engaging promotional message (2-3 sentences) that:
1. Highlights the product's unique value and benefits
2. Creates urgency and excitement
3. Encourages immediate purchase
4. Uses persuasive, action-oriented language

Promotional Ad Copy:"""

        # Prepare request body for Claude
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 200,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.7
        }
        
        # Invoke Bedrock
        response = bedrock_runtime.invoke_model(
            modelId='anthropic.claude-3-haiku-20240307-v1:0',
            contentType='application/json',
            accept='application/json',
            body=json.dumps(request_body)
        )
        
        # Parse response
        response_body = json.loads(response['body'].read())
        ad_copy = response_body['content'][0]['text'].strip()
        
        return ad_copy
    
    except Exception as e:
        print(f"Error generating promotional ad copy: {str(e)}")
        # Return a default message if Bedrock fails
        return f"Special promotion on {product_name}! Limited time offer. Order now and enjoy premium quality {product_category} delivered fresh to your door!"


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for promotion creation endpoint.
    
    Validates JWT token, farmer role, budget availability, and creates promotion record.
    Generates AI promotional ad copy via Bedrock.
    
    Args:
        event: API Gateway event
        context: Lambda context
        
    Returns:
        API Gateway response with promotionId, startDate, endDate, and aiGeneratedAdCopy
    """
    try:
        # Extract authorization header
        headers = event.get('headers', {})
        auth_header = headers.get('Authorization') or headers.get('authorization')
        
        if not auth_header:
            return {
                'statusCode': 401,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'UNAUTHORIZED',
                        'message': 'Authorization header is required'
                    }
                })
            }
        
        # Validate JWT token and extract user info
        try:
            user_info = get_user_from_token(auth_header)
            user_id = user_info['userId']
            user_role = user_info['role']
        except Exception as e:
            return {
                'statusCode': 401,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'INVALID_TOKEN',
                        'message': str(e)
                    }
                })
            }
        
        # Verify farmer role
        if user_role != UserRole.FARMER.value:
            return {
                'statusCode': 403,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'FORBIDDEN',
                        'message': 'Only farmers can create promotions'
                    }
                })
            }
        
        # Parse and validate request body
        try:
            body = json.loads(event.get('body', '{}'))
        except json.JSONDecodeError:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'INVALID_JSON',
                        'message': 'Request body must be valid JSON'
                    }
                })
            }
        
        # Validate promotion data
        try:
            promotion_request = validate_request_body(body, PromotionCreateRequest)
        except ValidationError as e:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'VALIDATION_ERROR',
                        'message': e.message,
                        'details': e.details if hasattr(e, 'details') else []
                    }
                })
            }
        
        # Query product to verify it exists and belongs to the farmer
        try:
            product = get_item(f"PRODUCT#{promotion_request.productId}", "METADATA")
            if not product:
                return {
                    'statusCode': 404,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({
                        'error': {
                            'code': 'NOT_FOUND',
                            'message': 'Product not found'
                        }
                    })
                }
            
            # Verify farmer owns the product
            if product.get('farmerId') != user_id:
                return {
                    'statusCode': 403,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({
                        'error': {
                            'code': 'FORBIDDEN',
                            'message': 'You can only promote your own products'
                        }
                    })
                }
        
        except Exception as e:
            print(f"Error querying product: {str(e)}")
            return {
                'statusCode': 503,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'SERVICE_UNAVAILABLE',
                        'message': 'Failed to verify product',
                        'details': str(e)
                    }
                })
            }
        
        # Query farmer account to check balance
        try:
            farmer = get_item(f"USER#{user_id}", "PROFILE")
            if not farmer:
                return {
                    'statusCode': 404,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({
                        'error': {
                            'code': 'NOT_FOUND',
                            'message': 'Farmer profile not found'
                        }
                    })
                }
            
            # Get farmer balance (default to 0 if not set)
            farmer_profile = farmer.get('farmerProfile', {})
            farmer_balance = farmer_profile.get('accountBalance', 0.0)
            
            # Validate budget <= farmer balance
            if promotion_request.budget > farmer_balance:
                return {
                    'statusCode': 409,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({
                        'error': {
                            'code': 'INSUFFICIENT_BALANCE',
                            'message': f'Insufficient balance. Available: {farmer_balance}, Required: {promotion_request.budget}'
                        }
                    })
                }
        
        except Exception as e:
            print(f"Error querying farmer account: {str(e)}")
            return {
                'statusCode': 503,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'SERVICE_UNAVAILABLE',
                        'message': 'Failed to verify account balance',
                        'details': str(e)
                    }
                })
            }
        
        # Generate unique promotion ID
        promotion_id = str(uuid.uuid4())
        
        # Calculate start and end dates
        now = datetime.utcnow()
        start_date = now
        end_date = now + timedelta(days=promotion_request.duration)
        
        # Generate AI promotional ad copy
        product_name = product.get('name', '')
        product_description = product.get('description', '')
        product_category = product.get('category', '')
        
        ai_ad_copy = generate_promotional_ad_copy(
            product_name,
            product_description,
            product_category
        )
        
        # Create Promotion model instance
        promotion = Promotion(
            promotionId=promotion_id,
            farmerId=user_id,
            productId=promotion_request.productId,
            budget=promotion_request.budget,
            duration=promotion_request.duration,
            status=PromotionStatus.ACTIVE,
            startDate=start_date,
            endDate=end_date,
            metrics=PromotionMetrics(),
            aiGeneratedAdCopy=ai_ad_copy,
            createdAt=now
        )
        
        # Convert to DynamoDB item format
        promotion_dict = promotion.dict()
        
        # Convert datetime objects to ISO strings for DynamoDB
        promotion_dict['startDate'] = promotion_dict['startDate'].isoformat()
        promotion_dict['endDate'] = promotion_dict['endDate'].isoformat()
        promotion_dict['createdAt'] = promotion_dict['createdAt'].isoformat()
        
        # Convert enums to strings
        promotion_dict['status'] = promotion_dict['status'].value if hasattr(promotion_dict['status'], 'value') else promotion_dict['status']
        
        # Store promotion in DynamoDB
        try:
            put_item(promotion_dict)
        except Exception as e:
            print(f"Error storing promotion in DynamoDB: {str(e)}")
            return {
                'statusCode': 503,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'SERVICE_UNAVAILABLE',
                        'message': 'Failed to create promotion',
                        'details': str(e)
                    }
                })
            }
        
        # Deduct budget from farmer balance
        try:
            new_balance = farmer_balance - promotion_request.budget
            update_item(
                pk=f"USER#{user_id}",
                sk="PROFILE",
                update_expression="SET farmerProfile.accountBalance = :balance",
                expression_attribute_values={
                    ':balance': new_balance
                }
            )
        except Exception as e:
            print(f"Error updating farmer balance: {str(e)}")
            # Note: In production, this should be a transaction to ensure atomicity
            # For now, we log the error but don't fail the request
        
        # Return success response
        return {
            'statusCode': 201,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'promotionId': promotion_id,
                'startDate': start_date.isoformat(),
                'endDate': end_date.isoformat(),
                'aiGeneratedAdCopy': ai_ad_copy,
                'message': 'Promotion created successfully'
            })
        }
    
    except Exception as e:
        # Catch-all for unexpected errors
        print(f"Unexpected error in promotion creation: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': {
                    'code': 'INTERNAL_ERROR',
                    'message': 'An unexpected error occurred',
                    'details': str(e)
                }
            })
        }
