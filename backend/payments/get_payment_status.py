"""
Payment status retrieval Lambda handler for RootTrust marketplace.
Handles GET /payments/{transactionId} endpoint to retrieve payment transaction status.
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
from exceptions import (
    AuthenticationError, AuthorizationError,
    ResourceNotFoundError, ServiceUnavailableError
)


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for payment status retrieval endpoint.
    
    Validates JWT token, retrieves transaction details from DynamoDB,
    and returns transaction status and details.
    
    Args:
        event: API Gateway event
        context: Lambda context
        
    Returns:
        API Gateway response with transaction details
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
        
        # Extract transaction ID from path parameters
        path_parameters = event.get('pathParameters', {})
        transaction_id = path_parameters.get('transactionId')
        
        if not transaction_id:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'VALIDATION_ERROR',
                        'message': 'transactionId is required in path',
                        'details': [{'field': 'transactionId', 'message': 'This field is required'}]
                    }
                })
            }
        
        # Query transaction by PK=TRANSACTION#{transactionId}
        transaction_pk = f"TRANSACTION#{transaction_id}"
        transaction_sk = "METADATA"
        
        try:
            transaction_item = get_item(transaction_pk, transaction_sk)
        except Exception as e:
            print(f"Error querying transaction: {str(e)}")
            return {
                'statusCode': 503,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'SERVICE_UNAVAILABLE',
                        'message': 'Failed to query transaction',
                        'details': str(e)
                    }
                })
            }
        
        if not transaction_item:
            return {
                'statusCode': 404,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'RESOURCE_NOT_FOUND',
                        'message': f'Transaction with ID {transaction_id} not found'
                    }
                })
            }
        
        # Get associated order to verify user has access
        order_id = transaction_item.get('orderId')
        
        if order_id:
            order_pk = f"ORDER#{order_id}"
            order_sk = "METADATA"
            
            try:
                order_item = get_item(order_pk, order_sk)
                
                if order_item:
                    # Verify user has access to this transaction
                    # Consumer can view their own orders, farmer can view orders for their products
                    consumer_id = order_item.get('consumerId')
                    farmer_id = order_item.get('farmerId')
                    
                    if user_role == UserRole.CONSUMER.value and consumer_id != user_id:
                        return {
                            'statusCode': 403,
                            'headers': {
                                'Content-Type': 'application/json',
                                'Access-Control-Allow-Origin': '*'
                            },
                            'body': json.dumps({
                                'error': {
                                    'code': 'FORBIDDEN',
                                    'message': 'You do not have permission to view this transaction'
                                }
                            })
                        }
                    
                    if user_role == UserRole.FARMER.value and farmer_id != user_id:
                        return {
                            'statusCode': 403,
                            'headers': {
                                'Content-Type': 'application/json',
                                'Access-Control-Allow-Origin': '*'
                            },
                            'body': json.dumps({
                                'error': {
                                    'code': 'FORBIDDEN',
                                    'message': 'You do not have permission to view this transaction'
                                }
                            })
                        }
            except Exception as e:
                print(f"Error querying order for authorization: {str(e)}")
                # Continue even if order query fails - transaction data is still valid
        
        # Build response with transaction details
        response_data = {
            'transactionId': transaction_item.get('transactionId'),
            'orderId': transaction_item.get('orderId'),
            'amount': transaction_item.get('amount'),
            'currency': transaction_item.get('currency', 'INR'),
            'status': transaction_item.get('status'),
            'paymentMethod': transaction_item.get('paymentMethod'),
            'paymentGateway': transaction_item.get('paymentGateway'),
            'createdAt': transaction_item.get('createdAt'),
            'completedAt': transaction_item.get('completedAt')
        }
        
        # Return success response with transaction details
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(response_data)
        }
    
    except Exception as e:
        # Catch-all for unexpected errors
        print(f"Unexpected error in payment status retrieval: {str(e)}")
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
