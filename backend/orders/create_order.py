"""
Order creation Lambda handler for RootTrust marketplace.
Handles POST /orders endpoint for consumers to create new orders.
"""
import json
import os
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any

# Import shared modules
import sys
sys.path.append('/opt/python')

from models import Order, Address
from validators import OrderCreateRequest, validate_request_body
from database import get_item, put_item, update_item
from auth import get_user_from_token
from constants import (
    UserRole, OrderStatus, PaymentStatus, VerificationStatus,
    DEFAULT_DELIVERY_DAYS
)
from exceptions import (
    ValidationError, AuthenticationError, AuthorizationError,
    ResourceNotFoundError, ConflictError, OutOfStockError
)


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for order creation endpoint.
    
    Validates JWT token, consumer role authorization, product availability,
    creates order record, and decrements product inventory atomically.
    
    Args:
        event: API Gateway event
        context: Lambda context
        
    Returns:
        API Gateway response with orderId, totalAmount, estimatedDeliveryDate
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
            consumer_id = user_info['userId']
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
        
        # Verify consumer role
        if user_role != UserRole.CONSUMER.value:
            return {
                'statusCode': 403,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'FORBIDDEN',
                        'message': 'Only consumers can create orders'
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
        
        # Validate order data
        try:
            order_request = validate_request_body(body, OrderCreateRequest)
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
        
        # Query product to verify availability and approved status
        product_pk = f"PRODUCT#{order_request.productId}"
        product_sk = "METADATA"
        
        try:
            product_item = get_item(product_pk, product_sk)
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
                        'message': 'Failed to query product',
                        'details': str(e)
                    }
                })
            }
        
        if not product_item:
            return {
                'statusCode': 404,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'RESOURCE_NOT_FOUND',
                        'message': f'Product with ID {order_request.productId} not found'
                    }
                })
            }
        
        # Verify product is approved
        if product_item.get('verificationStatus') != VerificationStatus.APPROVED.value:
            return {
                'statusCode': 409,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'CONFLICT_ERROR',
                        'message': 'Product is not approved for purchase'
                    }
                })
            }
        
        # Verify quantity availability
        available_quantity = product_item.get('quantity', 0)
        if order_request.quantity > available_quantity:
            return {
                'statusCode': 409,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'OUT_OF_STOCK',
                        'message': f'Insufficient quantity. Available: {available_quantity}, Requested: {order_request.quantity}'
                    }
                })
            }
        
        # Calculate total amount
        unit_price = float(product_item.get('price', 0))
        total_amount = unit_price * order_request.quantity
        
        # Generate unique order ID
        order_id = str(uuid.uuid4())
        
        # Calculate estimated delivery date (current date + 7 days)
        now = datetime.utcnow()
        estimated_delivery_date = now + timedelta(days=DEFAULT_DELIVERY_DAYS)
        
        # Build delivery address
        delivery_address = Address(**order_request.deliveryAddress)
        
        # Create Order model instance
        order = Order(
            orderId=order_id,
            consumerId=consumer_id,
            farmerId=product_item.get('farmerId'),
            productId=order_request.productId,
            productName=product_item.get('name'),
            quantity=order_request.quantity,
            unitPrice=unit_price,
            totalAmount=total_amount,
            status=OrderStatus.PENDING,
            paymentStatus=PaymentStatus.PENDING,
            deliveryAddress=delivery_address,
            estimatedDeliveryDate=estimated_delivery_date,
            referralCode=order_request.referralCode,
            createdAt=now,
            updatedAt=now
        )
        
        # Convert to DynamoDB item format
        order_dict = order.dict()
        
        # Convert datetime objects to ISO strings for DynamoDB
        order_dict['createdAt'] = order_dict['createdAt'].isoformat()
        order_dict['updatedAt'] = order_dict['updatedAt'].isoformat()
        order_dict['estimatedDeliveryDate'] = order_dict['estimatedDeliveryDate'].isoformat()
        
        # Convert enums to strings
        order_dict['status'] = order_dict['status'].value if hasattr(order_dict['status'], 'value') else order_dict['status']
        order_dict['paymentStatus'] = order_dict['paymentStatus'].value if hasattr(order_dict['paymentStatus'], 'value') else order_dict['paymentStatus']
        
        # Store order in DynamoDB
        try:
            put_item(order_dict)
        except Exception as e:
            print(f"Error storing order in DynamoDB: {str(e)}")
            return {
                'statusCode': 503,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'SERVICE_UNAVAILABLE',
                        'message': 'Failed to create order',
                        'details': str(e)
                    }
                })
            }
        
        # Decrement product quantity using conditional update to prevent overselling
        try:
            update_item(
                pk=product_pk,
                sk=product_sk,
                update_expression='SET quantity = quantity - :qty, updatedAt = :updated',
                expression_attribute_values={
                    ':qty': order_request.quantity,
                    ':updated': now.isoformat(),
                    ':min_qty': order_request.quantity
                },
                condition_expression='quantity >= :min_qty'
            )
        except ConflictError:
            # Conditional update failed - product quantity changed between check and update
            # This is a race condition - another order was placed simultaneously
            return {
                'statusCode': 409,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'OUT_OF_STOCK',
                        'message': 'Product quantity changed during order creation. Please try again.'
                    }
                })
            }
        except Exception as e:
            print(f"Error updating product quantity: {str(e)}")
            # Order was created but inventory update failed
            # In production, this should trigger a compensating transaction
            return {
                'statusCode': 503,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'SERVICE_UNAVAILABLE',
                        'message': 'Failed to update product inventory',
                        'details': str(e)
                    }
                })
            }
        
        # Return success response
        return {
            'statusCode': 201,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'orderId': order_id,
                'totalAmount': total_amount,
                'estimatedDeliveryDate': estimated_delivery_date.isoformat(),
                'message': 'Order created successfully'
            })
        }
    
    except Exception as e:
        # Catch-all for unexpected errors
        print(f"Unexpected error in order creation: {str(e)}")
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
