"""
Promotion update Lambda handler for RootTrust marketplace.
Handles PUT /promotions/{promotionId} endpoint for farmers to update promotion status.
"""
import json
import os
from typing import Dict, Any
from datetime import datetime

# Import shared modules
import sys
sys.path.append('/opt/python')

from models import Promotion
from validators import PromotionUpdateRequest, validate_request_body
from database import get_item, update_item
from auth import get_user_from_token
from constants import UserRole, PromotionStatus
from exceptions import (
    ValidationError, AuthenticationError, AuthorizationError,
    ResourceNotFoundError, ServiceUnavailableError
)
from email_service import get_email_service
from email_templates import get_promotion_summary_email


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for promotion update endpoint.
    
    Validates JWT token, farmer role, and updates promotion status.
    Sends summary email via SES if promotion is being ended.
    
    Args:
        event: API Gateway event
        context: Lambda context
        
    Returns:
        API Gateway response with updated promotion details
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
                        'message': 'Only farmers can update promotions'
                    }
                })
            }
        
        # Extract promotion ID from path parameters
        path_params = event.get('pathParameters', {})
        promotion_id = path_params.get('promotionId')
        
        if not promotion_id:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'INVALID_REQUEST',
                        'message': 'Promotion ID is required'
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
        
        # Validate promotion update data
        try:
            update_request = validate_request_body(body, PromotionUpdateRequest)
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
        
        # Query promotion to verify it exists and belongs to the farmer
        try:
            promotion = get_item(f"PROMOTION#{promotion_id}", "METADATA")
            if not promotion:
                return {
                    'statusCode': 404,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({
                        'error': {
                            'code': 'NOT_FOUND',
                            'message': 'Promotion not found'
                        }
                    })
                }
            
            # Verify farmer owns the promotion
            if promotion.get('farmerId') != user_id:
                return {
                    'statusCode': 403,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({
                        'error': {
                            'code': 'FORBIDDEN',
                            'message': 'You can only update your own promotions'
                        }
                    })
                }
        
        except Exception as e:
            print(f"Error querying promotion: {str(e)}")
            return {
                'statusCode': 503,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'SERVICE_UNAVAILABLE',
                        'message': 'Failed to verify promotion',
                        'details': str(e)
                    }
                })
            }
        
        # Get old status for comparison
        old_status = promotion.get('status')
        new_status = update_request.status.value
        
        # Check if promotion is being ended (cancelled or completed)
        is_ending = new_status in [PromotionStatus.CANCELLED.value, PromotionStatus.COMPLETED.value]
        send_summary = is_ending and old_status not in [PromotionStatus.CANCELLED.value, PromotionStatus.COMPLETED.value]
        
        # Update promotion status in DynamoDB
        try:
            # Update GSI3PK if status changed (for querying by status)
            update_expression = "SET #status = :status, #gsi3pk = :gsi3pk"
            expression_attribute_names = {
                '#status': 'status',
                '#gsi3pk': 'GSI3PK'
            }
            expression_attribute_values = {
                ':status': new_status,
                ':gsi3pk': f"STATUS#{new_status}"
            }
            
            update_item(
                pk=f"PROMOTION#{promotion_id}",
                sk="METADATA",
                update_expression=update_expression,
                expression_attribute_names=expression_attribute_names,
                expression_attribute_values=expression_attribute_values
            )
            
            # Update local promotion object for response
            promotion['status'] = new_status
            promotion['GSI3PK'] = f"STATUS#{new_status}"
        
        except Exception as e:
            print(f"Error updating promotion in DynamoDB: {str(e)}")
            return {
                'statusCode': 503,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'SERVICE_UNAVAILABLE',
                        'message': 'Failed to update promotion',
                        'details': str(e)
                    }
                })
            }
        
        # Send summary email if promotion is ending
        if send_summary:
            try:
                # Get farmer details
                farmer = get_item(f"USER#{user_id}", "PROFILE")
                farmer_email = farmer.get('email', '')
                farmer_first_name = farmer.get('firstName', 'Farmer')
                
                # Get product details
                product_id = promotion.get('productId')
                product = get_item(f"PRODUCT#{product_id}", "METADATA")
                product_name = product.get('name', 'Product') if product else 'Product'
                
                # Get promotion metrics
                metrics = promotion.get('metrics', {})
                total_views = metrics.get('views', 0)
                total_clicks = metrics.get('clicks', 0)
                total_conversions = metrics.get('conversions', 0)
                total_spent = metrics.get('spent', 0.0)
                
                # Get promotion details
                budget = promotion.get('budget', 0.0)
                start_date = promotion.get('startDate', '')
                end_date = promotion.get('endDate', '')
                
                # Generate and send summary email
                email_content = get_promotion_summary_email(
                    farmer_email=farmer_email,
                    farmer_first_name=farmer_first_name,
                    promotion_id=promotion_id,
                    product_name=product_name,
                    start_date=start_date,
                    end_date=end_date,
                    total_views=total_views,
                    total_clicks=total_clicks,
                    total_conversions=total_conversions,
                    total_spent=total_spent,
                    budget=budget
                )
                
                email_service = get_email_service()
                email_result = email_service.send_email(
                    recipient=farmer_email,
                    subject=email_content['subject'],
                    html_body=email_content['html_body'],
                    text_body=email_content['text_body']
                )
                
                if not email_result.get('success'):
                    print(f"Failed to send summary email: {email_result.get('error_message')}")
                    # Don't fail the request if email fails
            
            except Exception as e:
                print(f"Error sending summary email: {str(e)}")
                # Don't fail the request if email fails
        
        # Return success response
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'promotionId': promotion_id,
                'status': new_status,
                'message': 'Promotion updated successfully',
                'summarySent': send_summary
            })
        }
    
    except Exception as e:
        # Catch-all for unexpected errors
        print(f"Unexpected error in promotion update: {str(e)}")
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
