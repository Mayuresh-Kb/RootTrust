"""
Order listing Lambda handler for RootTrust marketplace.
Handles GET /orders endpoint for consumers and farmers to view their orders.
"""
import json
import os
from typing import Dict, Any, List
from boto3.dynamodb.conditions import Key

# Import shared modules
import sys
sys.path.append('/opt/python')

from database import query
from auth import get_user_from_token
from constants import UserRole


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for order listing endpoint.
    
    Validates JWT token, determines user role, and queries appropriate GSI:
    - Consumers: Query GSI2 with GSI2PK=CONSUMER#{consumerId}
    - Farmers: Query GSI3 with GSI3PK=FARMER#{farmerId}
    
    Args:
        event: API Gateway event
        context: Lambda context
        
    Returns:
        API Gateway response with orders array
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
        
        # Query orders based on user role
        try:
            if user_role == UserRole.CONSUMER.value:
                # Query GSI2 for consumer orders
                gsi2_pk = f"CONSUMER#{user_id}"
                result = query(
                    key_condition_expression=Key('GSI2PK').eq(gsi2_pk) & Key('GSI2SK').begins_with('ORDER#'),
                    index_name='GSI2',
                    scan_index_forward=False  # Most recent first
                )
            elif user_role == UserRole.FARMER.value:
                # Query GSI3 for farmer orders
                gsi3_pk = f"FARMER#{user_id}"
                result = query(
                    key_condition_expression=Key('GSI3PK').eq(gsi3_pk) & Key('GSI3SK').begins_with('ORDER#'),
                    index_name='GSI3',
                    scan_index_forward=False  # Most recent first
                )
            else:
                return {
                    'statusCode': 403,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({
                        'error': {
                            'code': 'FORBIDDEN',
                            'message': f'Invalid role: {user_role}'
                        }
                    })
                }
            
            orders = result.get('Items', [])
            
        except Exception as e:
            print(f"Error querying orders: {str(e)}")
            return {
                'statusCode': 503,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'SERVICE_UNAVAILABLE',
                        'message': 'Failed to query orders',
                        'details': str(e)
                    }
                })
            }
        
        # Format orders for response
        formatted_orders = []
        for order in orders:
            formatted_order = {
                'orderId': order.get('orderId'),
                'productName': order.get('productName'),
                'quantity': order.get('quantity'),
                'totalAmount': float(order.get('totalAmount', 0)),
                'status': order.get('status'),
                'estimatedDeliveryDate': order.get('estimatedDeliveryDate'),
                'createdAt': order.get('createdAt')
            }
            
            # Add role-specific fields
            if user_role == UserRole.CONSUMER.value:
                formatted_order['farmerId'] = order.get('farmerId')
            elif user_role == UserRole.FARMER.value:
                formatted_order['consumerId'] = order.get('consumerId')
            
            formatted_orders.append(formatted_order)
        
        # Return success response
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'orders': formatted_orders,
                'count': len(formatted_orders)
            })
        }
    
    except Exception as e:
        # Catch-all for unexpected errors
        print(f"Unexpected error in order listing: {str(e)}")
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
