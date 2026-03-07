"""
Limited release purchase Lambda handler for RootTrust marketplace.
Handles POST /limited-releases/{releaseId}/purchase endpoint for consumers to purchase from limited releases.
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
from database import get_item, put_item, update_item
from auth import get_user_from_token
from constants import (
    UserRole, OrderStatus, PaymentStatus, LimitedReleaseStatus,
    DEFAULT_DELIVERY_DAYS
)
from exceptions import (
    ValidationError, AuthenticationError, AuthorizationError,
    ResourceNotFoundError, ConflictError, OutOfStockError
)


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for limited release purchase endpoint.
    
    Validates JWT token, consumer role authorization, verifies release availability,
    decrements quantityRemaining atomically, updates status to sold_out if needed,
    and creates order record.
    
    Args:
        event: API Gateway event
        context: Lambda context
        
    Returns:
        API Gateway response with orderId
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
                        'message': 'Only consumers can purchase from limited releases'
                    }
                })
            }
        
        # Extract releaseId from path parameters
        path_parameters = event.get('pathParameters', {})
        release_id = path_parameters.get('releaseId')
        
        if not release_id:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'VALIDATION_ERROR',
                        'message': 'releaseId is required in path'
                    }
                })
            }
        
        # Parse request body for delivery address
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
        
        # Validate delivery address
        delivery_address_data = body.get('deliveryAddress')
        if not delivery_address_data:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'VALIDATION_ERROR',
                        'message': 'deliveryAddress is required'
                    }
                })
            }
        
        required_address_fields = ['street', 'city', 'state', 'pincode']
        for field in required_address_fields:
            if field not in delivery_address_data or not delivery_address_data[field]:
                return {
                    'statusCode': 400,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({
                        'error': {
                            'code': 'VALIDATION_ERROR',
                            'message': f'deliveryAddress.{field} is required'
                        }
                    })
                }
        
        # Query limited release to verify it exists and is available
        release_pk = f"LIMITED_RELEASE#{release_id}"
        release_sk = "METADATA"
        
        try:
            release_item = get_item(release_pk, release_sk)
        except Exception as e:
            print(f"Error querying limited release: {str(e)}")
            return {
                'statusCode': 503,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'SERVICE_UNAVAILABLE',
                        'message': 'Failed to query limited release',
                        'details': str(e)
                    }
                })
            }
        
        if not release_item:
            return {
                'statusCode': 404,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'RESOURCE_NOT_FOUND',
                        'message': f'Limited release with ID {release_id} not found'
                    }
                })
            }
        
        # Verify release is active
        release_status = release_item.get('status')
        if release_status != LimitedReleaseStatus.ACTIVE.value:
            return {
                'statusCode': 409,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'CONFLICT_ERROR',
                        'message': f'Limited release is not active (status: {release_status})'
                    }
                })
            }
        
        # Verify quantity remaining > 0
        quantity_remaining = release_item.get('quantityRemaining', 0)
        if quantity_remaining <= 0:
            return {
                'statusCode': 409,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'OUT_OF_STOCK',
                        'message': 'Limited release is sold out'
                    }
                })
            }
        
        # Get product details for order creation
        product_id = release_item.get('productId')
        product_pk = f"PRODUCT#{product_id}"
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
                        'message': f'Product with ID {product_id} not found'
                    }
                })
            }
        
        # Extract product details
        unit_price = float(product_item.get('price', 0))
        product_name = product_item.get('name')
        farmer_id = product_item.get('farmerId')
        
        # For limited releases, quantity is always 1
        quantity = 1
        total_amount = unit_price * quantity
        
        # Generate unique order ID
        order_id = str(uuid.uuid4())
        
        # Calculate estimated delivery date
        now = datetime.utcnow()
        estimated_delivery_date = now + timedelta(days=DEFAULT_DELIVERY_DAYS)
        
        # Build delivery address
        delivery_address = Address(**delivery_address_data)
        
        # Create Order model instance
        order = Order(
            orderId=order_id,
            consumerId=consumer_id,
            farmerId=farmer_id,
            productId=product_id,
            productName=product_name,
            quantity=quantity,
            unitPrice=unit_price,
            totalAmount=total_amount,
            status=OrderStatus.PENDING,
            paymentStatus=PaymentStatus.PENDING,
            deliveryAddress=delivery_address,
            estimatedDeliveryDate=estimated_delivery_date,
            referralCode=body.get('referralCode'),
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
        
        # Decrement quantityRemaining using conditional update to prevent overselling
        try:
            updated_release = update_item(
                pk=release_pk,
                sk=release_sk,
                update_expression='SET quantityRemaining = quantityRemaining - :qty',
                expression_attribute_values={
                    ':qty': 1,
                    ':min_qty': 1,
                    ':active_status': LimitedReleaseStatus.ACTIVE.value
                },
                condition_expression='quantityRemaining >= :min_qty AND #status = :active_status',
                expression_attribute_names={
                    '#status': 'status'
                }
            )
            
            # Check if quantityRemaining reached 0 and update status to sold_out
            new_quantity_remaining = updated_release.get('quantityRemaining', 0)
            if new_quantity_remaining == 0:
                try:
                    update_item(
                        pk=release_pk,
                        sk=release_sk,
                        update_expression='SET #status = :sold_out_status, GSI3PK = :gsi3pk',
                        expression_attribute_values={
                            ':sold_out_status': LimitedReleaseStatus.SOLD_OUT.value,
                            ':gsi3pk': f"STATUS#{LimitedReleaseStatus.SOLD_OUT.value}"
                        },
                        expression_attribute_names={
                            '#status': 'status'
                        }
                    )
                    print(f"Limited release {release_id} marked as sold out")
                except Exception as e:
                    print(f"Error updating release status to sold_out: {str(e)}")
                    # Don't fail the request if status update fails
        
        except ConflictError:
            # Conditional update failed - release sold out or status changed
            return {
                'statusCode': 409,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'OUT_OF_STOCK',
                        'message': 'Limited release sold out during purchase. Please try another product.'
                    }
                })
            }
        except Exception as e:
            print(f"Error updating limited release quantity: {str(e)}")
            # Order was created but inventory update failed
            return {
                'statusCode': 503,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'SERVICE_UNAVAILABLE',
                        'message': 'Failed to update limited release inventory',
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
                'message': 'Limited release purchase successful'
            })
        }
    
    except Exception as e:
        # Catch-all for unexpected errors
        print(f"Unexpected error in limited release purchase: {str(e)}")
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
