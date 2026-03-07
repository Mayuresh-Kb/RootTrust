"""
Order detail Lambda handler for RootTrust marketplace.
Handles GET /orders/{orderId} endpoint for consumers and farmers to view order details.
"""
import json
import os
from typing import Dict, Any

# Import shared modules
import sys
sys.path.append('/opt/python')

from database import get_item
from auth import get_user_from_token
from constants import UserRole


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for order detail endpoint.
    
    Validates JWT token, queries order by orderId, verifies user owns the order
    (consumer or farmer), and returns complete order details.
    
    Args:
        event: API Gateway event with orderId in pathParameters
        context: Lambda context
        
    Returns:
        API Gateway response with complete order details
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
        
        # Extract orderId from path parameters
        path_parameters = event.get('pathParameters') or {}
        order_id = path_parameters.get('orderId')
        
        if not order_id:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'BAD_REQUEST',
                        'message': 'orderId is required in path parameters'
                    }
                })
            }
        
        # Query order by PK and SK
        order_pk = f"ORDER#{order_id}"
        order_sk = "METADATA"
        
        try:
            order = get_item(order_pk, order_sk)
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
        
        if not order:
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
        
        # Verify user owns the order (consumer or farmer)
        consumer_id = order.get('consumerId')
        farmer_id = order.get('farmerId')
        
        is_consumer_owner = (user_role == UserRole.CONSUMER.value and user_id == consumer_id)
        is_farmer_owner = (user_role == UserRole.FARMER.value and user_id == farmer_id)
        
        if not (is_consumer_owner or is_farmer_owner):
            return {
                'statusCode': 403,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'FORBIDDEN',
                        'message': 'You do not have permission to view this order'
                    }
                })
            }
        
        # Format order details for response
        order_details = {
            'orderId': order.get('orderId'),
            'consumerId': consumer_id,
            'farmerId': farmer_id,
            'productId': order.get('productId'),
            'productName': order.get('productName'),
            'quantity': order.get('quantity'),
            'unitPrice': float(order.get('unitPrice', 0)),
            'totalAmount': float(order.get('totalAmount', 0)),
            'status': order.get('status'),
            'paymentStatus': order.get('paymentStatus'),
            'transactionId': order.get('transactionId'),
            'deliveryAddress': order.get('deliveryAddress'),
            'estimatedDeliveryDate': order.get('estimatedDeliveryDate'),
            'actualDeliveryDate': order.get('actualDeliveryDate'),
            'referralCode': order.get('referralCode'),
            'createdAt': order.get('createdAt'),
            'updatedAt': order.get('updatedAt')
        }
        
        # Return success response
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'order': order_details
            })
        }
    
    except Exception as e:
        # Catch-all for unexpected errors
        print(f"Unexpected error in order detail: {str(e)}")
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
