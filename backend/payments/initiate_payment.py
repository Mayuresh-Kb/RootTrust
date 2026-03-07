"""
Payment initiation Lambda handler for RootTrust marketplace.
Handles POST /payments/initiate endpoint for consumers to initiate payment for orders.
"""
import json
import os
import uuid
from datetime import datetime
from typing import Dict, Any

# Import shared modules
import sys
sys.path.append('/opt/python')

from models import Transaction
from database import get_item, put_item, update_item
from auth import get_user_from_token
from constants import (
    UserRole, OrderStatus, PaymentStatus, PaymentGateway, PaymentMethod
)
from exceptions import (
    ValidationError, AuthenticationError, AuthorizationError,
    ResourceNotFoundError, ConflictError, ServiceUnavailableError
)


def create_stripe_payment_session(order_id: str, amount: float, currency: str = "INR") -> Dict[str, Any]:
    """
    Create a Stripe payment session for the order.
    
    For MVP, this uses Stripe test mode. In production, this would use
    the Stripe API to create a checkout session.
    
    Args:
        order_id: Order ID
        amount: Payment amount
        currency: Currency code (default INR)
        
    Returns:
        Dictionary with sessionId and paymentUrl
    """
    # For MVP/testing, generate mock Stripe session
    # In production, use: stripe.checkout.Session.create()
    
    use_mock = os.environ.get('USE_MOCK_PAYMENT', 'true').lower() == 'true'
    
    if use_mock:
        # Mock payment session for testing
        session_id = f"cs_test_{uuid.uuid4().hex[:24]}"
        payment_url = f"https://checkout.stripe.com/pay/{session_id}"
        
        return {
            'sessionId': session_id,
            'paymentUrl': payment_url,
            'gateway': PaymentGateway.STRIPE.value
        }
    else:
        # Real Stripe integration (requires stripe library)
        try:
            import stripe
            stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')
            
            # Get callback URLs from environment
            success_url = os.environ.get('PAYMENT_SUCCESS_URL', 'https://roottrust.com/payment/success')
            cancel_url = os.environ.get('PAYMENT_CANCEL_URL', 'https://roottrust.com/payment/cancel')
            
            # Create Stripe checkout session
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': currency.lower(),
                        'product_data': {
                            'name': f'Order {order_id}',
                        },
                        'unit_amount': int(amount * 100),  # Stripe uses cents
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=f"{success_url}?session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=cancel_url,
                metadata={
                    'order_id': order_id
                }
            )
            
            return {
                'sessionId': session.id,
                'paymentUrl': session.url,
                'gateway': PaymentGateway.STRIPE.value
            }
        except Exception as e:
            print(f"Stripe API error: {str(e)}")
            raise ServiceUnavailableError('Stripe', f'Failed to create payment session: {str(e)}')


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for payment initiation endpoint.
    
    Validates JWT token, consumer role authorization, order ownership,
    creates payment session with Stripe, and returns payment URL.
    
    Args:
        event: API Gateway event
        context: Lambda context
        
    Returns:
        API Gateway response with paymentUrl and sessionId
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
                        'message': 'Only consumers can initiate payments'
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
        
        # Validate required fields
        order_id = body.get('orderId')
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
                        'message': 'orderId is required',
                        'details': [{'field': 'orderId', 'message': 'This field is required'}]
                    }
                })
            }
        
        # Query order to verify existence and ownership
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
        
        # Verify consumer owns the order
        if order_item.get('consumerId') != consumer_id:
            return {
                'statusCode': 403,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'FORBIDDEN',
                        'message': 'You do not have permission to initiate payment for this order'
                    }
                })
            }
        
        # Verify order is in pending status
        order_status = order_item.get('status')
        if order_status != OrderStatus.PENDING.value:
            return {
                'statusCode': 409,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'CONFLICT_ERROR',
                        'message': f'Cannot initiate payment for order with status: {order_status}'
                    }
                })
            }
        
        # Verify payment is not already completed
        payment_status = order_item.get('paymentStatus')
        if payment_status == PaymentStatus.COMPLETED.value:
            return {
                'statusCode': 409,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'CONFLICT_ERROR',
                        'message': 'Payment has already been completed for this order'
                    }
                })
            }
        
        # Get total amount from order
        total_amount = float(order_item.get('totalAmount', 0))
        
        if total_amount <= 0:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'VALIDATION_ERROR',
                        'message': 'Order total amount is invalid'
                    }
                })
            }
        
        # Create payment session with Stripe
        try:
            payment_session = create_stripe_payment_session(
                order_id=order_id,
                amount=total_amount,
                currency='INR'
            )
        except ServiceUnavailableError as e:
            return {
                'statusCode': 503,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'SERVICE_UNAVAILABLE',
                        'message': e.message
                    }
                })
            }
        except Exception as e:
            print(f"Error creating payment session: {str(e)}")
            return {
                'statusCode': 500,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'INTERNAL_ERROR',
                        'message': 'Failed to create payment session',
                        'details': str(e)
                    }
                })
            }
        
        # Store payment session details in DynamoDB for webhook verification
        now = datetime.utcnow()
        transaction_id = payment_session['sessionId']
        
        transaction = Transaction(
            transactionId=transaction_id,
            orderId=order_id,
            amount=total_amount,
            currency='INR',
            paymentMethod=PaymentMethod.CARD,  # Default for Stripe
            paymentGateway=PaymentGateway.STRIPE,
            status=PaymentStatus.PENDING,
            gatewayResponse={
                'sessionId': payment_session['sessionId'],
                'paymentUrl': payment_session['paymentUrl']
            },
            createdAt=now
        )
        
        # Convert to DynamoDB item format
        transaction_dict = transaction.dict()
        transaction_dict['createdAt'] = transaction_dict['createdAt'].isoformat()
        
        # Convert enums to strings
        transaction_dict['paymentMethod'] = transaction_dict['paymentMethod'].value if hasattr(transaction_dict['paymentMethod'], 'value') else transaction_dict['paymentMethod']
        transaction_dict['paymentGateway'] = transaction_dict['paymentGateway'].value if hasattr(transaction_dict['paymentGateway'], 'value') else transaction_dict['paymentGateway']
        transaction_dict['status'] = transaction_dict['status'].value if hasattr(transaction_dict['status'], 'value') else transaction_dict['status']
        
        # Store transaction in DynamoDB
        try:
            put_item(transaction_dict)
        except Exception as e:
            print(f"Error storing transaction in DynamoDB: {str(e)}")
            # Payment session was created but we couldn't store it
            # Log the error but still return the payment URL
            print(f"WARNING: Transaction {transaction_id} created but not stored in DB")
        
        # Update order with transaction ID
        try:
            update_item(
                pk=order_pk,
                sk=order_sk,
                update_expression='SET transactionId = :txn_id, updatedAt = :updated',
                expression_attribute_values={
                    ':txn_id': transaction_id,
                    ':updated': now.isoformat()
                }
            )
        except Exception as e:
            print(f"Error updating order with transaction ID: {str(e)}")
            # Non-critical error, payment can still proceed
        
        # Return success response with payment URL
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'paymentUrl': payment_session['paymentUrl'],
                'sessionId': payment_session['sessionId'],
                'orderId': order_id,
                'amount': total_amount,
                'currency': 'INR',
                'message': 'Payment session created successfully'
            })
        }
    
    except Exception as e:
        # Catch-all for unexpected errors
        print(f"Unexpected error in payment initiation: {str(e)}")
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
