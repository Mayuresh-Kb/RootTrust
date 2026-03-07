"""
Order status update Lambda handler for RootTrust marketplace.
Handles PUT /orders/{orderId}/status endpoint for farmers to update order status.
"""
import json
import os
from datetime import datetime
from typing import Dict, Any

# Import shared modules
import sys
sys.path.append('/opt/python')

from models import Order
from database import get_item, update_item
from auth import get_user_from_token
from constants import UserRole, OrderStatus
from exceptions import (
    ValidationError, AuthenticationError, AuthorizationError,
    ResourceNotFoundError
)
from email_service import get_email_service
from email_templates import get_order_status_update_email


# Valid order status transitions
VALID_ORDER_STATUSES = [
    OrderStatus.CONFIRMED.value,
    OrderStatus.PROCESSING.value,
    OrderStatus.SHIPPED.value,
    OrderStatus.DELIVERED.value,
    OrderStatus.CANCELLED.value
]


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for order status update endpoint.
    
    Validates JWT token, farmer role authorization, farmer ownership of product,
    updates order status in DynamoDB, triggers notification email via SES,
    and sets actualDeliveryDate if status is delivered.
    
    Args:
        event: API Gateway event
        context: Lambda context
        
    Returns:
        API Gateway response with updated order details
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
            farmer_id = user_info['userId']
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
                        'message': 'Only farmers can update order status'
                    }
                })
            }
        
        # Extract orderId from path parameters
        path_params = event.get('pathParameters', {})
        order_id = path_params.get('orderId')
        
        if not order_id:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'VALIDATION_ERROR',
                        'message': 'orderId is required in path'
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
        
        # Validate new status
        new_status = body.get('status')
        if not new_status:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'VALIDATION_ERROR',
                        'message': 'status is required in request body'
                    }
                })
            }
        
        if new_status not in VALID_ORDER_STATUSES:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'VALIDATION_ERROR',
                        'message': f'Invalid status. Must be one of: {", ".join(VALID_ORDER_STATUSES)}'
                    }
                })
            }
        
        # Query order from DynamoDB
        order_pk = f"ORDER#{order_id}"
        order_sk = "METADATA"
        
        try:
            order_item = get_item(order_pk, order_sk)
        except Exception as e:
            print(f"Error querying order: {str(e)}")
            return {
                'statusCode': 503,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'SERVICE_UNAVAILABLE',
                        'message': 'Failed to query order',
                        'details': str(e)
                    }
                })
            }
        
        if not order_item:
            return {
                'statusCode': 404,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'RESOURCE_NOT_FOUND',
                        'message': f'Order with ID {order_id} not found'
                    }
                })
            }
        
        # Verify farmer owns the product associated with this order
        order_farmer_id = order_item.get('farmerId')
        if order_farmer_id != farmer_id:
            return {
                'statusCode': 403,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'FORBIDDEN',
                        'message': 'You can only update orders for your own products'
                    }
                })
            }
        
        # Prepare update expression
        now = datetime.utcnow()
        update_expression = 'SET #status = :status, updatedAt = :updated'
        expression_attribute_names = {
            '#status': 'status'
        }
        expression_attribute_values = {
            ':status': new_status,
            ':updated': now.isoformat()
        }
        
        # If status is delivered, set actualDeliveryDate
        if new_status == OrderStatus.DELIVERED.value:
            update_expression += ', actualDeliveryDate = :delivery_date'
            expression_attribute_values[':delivery_date'] = now.isoformat()
        
        # Update order status in DynamoDB
        try:
            update_item(
                pk=order_pk,
                sk=order_sk,
                update_expression=update_expression,
                expression_attribute_values=expression_attribute_values,
                expression_attribute_names=expression_attribute_names
            )
        except Exception as e:
            print(f"Error updating order status: {str(e)}")
            return {
                'statusCode': 503,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'SERVICE_UNAVAILABLE',
                        'message': 'Failed to update order status',
                        'details': str(e)
                    }
                })
            }
        
        # Get consumer information for email notification
        consumer_id = order_item.get('consumerId')
        consumer_pk = f"USER#{consumer_id}"
        consumer_sk = "PROFILE"
        
        try:
            consumer_item = get_item(consumer_pk, consumer_sk)
        except Exception as e:
            print(f"Warning: Failed to query consumer for email notification: {str(e)}")
            consumer_item = None
        
        # Send email notification to consumer
        if consumer_item:
            consumer_email = consumer_item.get('email')
            consumer_first_name = consumer_item.get('firstName', 'Customer')
            product_name = order_item.get('productName', 'Product')
            
            try:
                email_service = get_email_service()
                email_content = get_order_status_update_email(
                    consumer_email=consumer_email,
                    consumer_first_name=consumer_first_name,
                    order_id=order_id,
                    product_name=product_name,
                    new_status=new_status,
                    estimated_delivery_date=order_item.get('estimatedDeliveryDate'),
                    actual_delivery_date=now.isoformat() if new_status == OrderStatus.DELIVERED.value else None
                )
                
                email_result = email_service.send_email(
                    recipient=consumer_email,
                    subject=email_content['subject'],
                    html_body=email_content['html_body'],
                    text_body=email_content['text_body']
                )
                
                if not email_result.get('success'):
                    print(f"Warning: Failed to send email notification: {email_result.get('error_message')}")
            except Exception as e:
                print(f"Warning: Error sending email notification: {str(e)}")
        
        # Fetch updated order to return
        try:
            updated_order_item = get_item(order_pk, order_sk)
        except Exception as e:
            print(f"Warning: Failed to fetch updated order: {str(e)}")
            updated_order_item = order_item
            updated_order_item['status'] = new_status
            updated_order_item['updatedAt'] = now.isoformat()
            if new_status == OrderStatus.DELIVERED.value:
                updated_order_item['actualDeliveryDate'] = now.isoformat()
        
        # Return success response with updated order
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'message': 'Order status updated successfully',
                'order': updated_order_item
            }, default=str)
        }
    
    except Exception as e:
        # Catch-all for unexpected errors
        print(f"Unexpected error in order status update: {str(e)}")
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
