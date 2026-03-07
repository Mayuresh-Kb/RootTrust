"""
Payment webhook handler Lambda for RootTrust marketplace.
Handles POST /payments/webhook endpoint for payment gateway webhooks (Razorpay/Stripe).
"""
import json
import os
import hmac
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional

# Import shared modules
import sys
sys.path.append('/opt/python')

from models import Transaction
from database import get_item, put_item, update_item
from constants import (
    OrderStatus, PaymentStatus, PaymentGateway
)
from exceptions import (
    ValidationError, ResourceNotFoundError, ServiceUnavailableError
)
from email_service import get_email_service
from email_templates import get_order_status_update_email


def verify_stripe_signature(payload: str, signature: str, secret: str) -> bool:
    """
    Verify Stripe webhook signature.
    
    Args:
        payload: Raw request body as string
        signature: Stripe signature from header
        secret: Stripe webhook secret
        
    Returns:
        True if signature is valid, False otherwise
    """
    # For MVP, use mock verification if enabled
    use_mock = os.environ.get('USE_MOCK_PAYMENT', 'true').lower() == 'true'
    
    if use_mock:
        # Mock verification always returns True for testing
        return True
    
    # Real Stripe signature verification
    try:
        # Extract timestamp and signatures from header
        # Format: t=timestamp,v1=signature1,v1=signature2
        elements = signature.split(',')
        timestamp = None
        signatures = []
        
        for element in elements:
            if element.startswith('t='):
                timestamp = element.split('=')[1]
            elif element.startswith('v1='):
                signatures.append(element.split('=')[1])
        
        if not timestamp or not signatures:
            return False
        
        # Construct signed payload
        signed_payload = f"{timestamp}.{payload}"
        
        # Compute expected signature
        expected_signature = hmac.new(
            secret.encode('utf-8'),
            signed_payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        # Compare signatures (constant-time comparison)
        return any(hmac.compare_digest(expected_signature, sig) for sig in signatures)
    
    except Exception as e:
        print(f"Error verifying Stripe signature: {str(e)}")
        return False


def verify_razorpay_signature(payload: str, signature: str, secret: str) -> bool:
    """
    Verify Razorpay webhook signature.
    
    Args:
        payload: Raw request body as string
        signature: Razorpay signature from header
        secret: Razorpay webhook secret
        
    Returns:
        True if signature is valid, False otherwise
    """
    # For MVP, use mock verification if enabled
    use_mock = os.environ.get('USE_MOCK_PAYMENT', 'true').lower() == 'true'
    
    if use_mock:
        # Mock verification always returns True for testing
        return True
    
    # Real Razorpay signature verification
    try:
        # Compute expected signature
        expected_signature = hmac.new(
            secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        # Compare signatures (constant-time comparison)
        return hmac.compare_digest(expected_signature, signature)
    
    except Exception as e:
        print(f"Error verifying Razorpay signature: {str(e)}")
        return False


def parse_stripe_webhook(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Parse Stripe webhook payload to extract payment details.
    
    Args:
        payload: Stripe webhook event payload
        
    Returns:
        Dictionary with transactionId, orderId, amount, status or None if invalid
    """
    try:
        event_type = payload.get('type')
        
        # Handle checkout.session.completed event
        if event_type == 'checkout.session.completed':
            session = payload.get('data', {}).get('object', {})
            
            transaction_id = session.get('id')
            order_id = session.get('metadata', {}).get('order_id')
            amount = session.get('amount_total', 0) / 100  # Stripe uses cents
            payment_status = session.get('payment_status')
            
            # Map Stripe payment status to our status
            if payment_status == 'paid':
                status = PaymentStatus.COMPLETED.value
            else:
                status = PaymentStatus.FAILED.value
            
            return {
                'transactionId': transaction_id,
                'orderId': order_id,
                'amount': amount,
                'status': status,
                'gateway': PaymentGateway.STRIPE.value
            }
        
        # Handle checkout.session.async_payment_failed event
        elif event_type == 'checkout.session.async_payment_failed':
            session = payload.get('data', {}).get('object', {})
            
            transaction_id = session.get('id')
            order_id = session.get('metadata', {}).get('order_id')
            amount = session.get('amount_total', 0) / 100
            
            return {
                'transactionId': transaction_id,
                'orderId': order_id,
                'amount': amount,
                'status': PaymentStatus.FAILED.value,
                'gateway': PaymentGateway.STRIPE.value
            }
        
        return None
    
    except Exception as e:
        print(f"Error parsing Stripe webhook: {str(e)}")
        return None


def parse_razorpay_webhook(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Parse Razorpay webhook payload to extract payment details.
    
    Args:
        payload: Razorpay webhook event payload
        
    Returns:
        Dictionary with transactionId, orderId, amount, status or None if invalid
    """
    try:
        event = payload.get('event')
        
        # Handle payment.captured event
        if event == 'payment.captured':
            payment = payload.get('payload', {}).get('payment', {}).get('entity', {})
            
            transaction_id = payment.get('id')
            order_id = payment.get('notes', {}).get('order_id')
            amount = payment.get('amount', 0) / 100  # Razorpay uses paise
            
            return {
                'transactionId': transaction_id,
                'orderId': order_id,
                'amount': amount,
                'status': PaymentStatus.COMPLETED.value,
                'gateway': PaymentGateway.RAZORPAY.value
            }
        
        # Handle payment.failed event
        elif event == 'payment.failed':
            payment = payload.get('payload', {}).get('payment', {}).get('entity', {})
            
            transaction_id = payment.get('id')
            order_id = payment.get('notes', {}).get('order_id')
            amount = payment.get('amount', 0) / 100
            
            return {
                'transactionId': transaction_id,
                'orderId': order_id,
                'amount': amount,
                'status': PaymentStatus.FAILED.value,
                'gateway': PaymentGateway.RAZORPAY.value
            }
        
        return None
    
    except Exception as e:
        print(f"Error parsing Razorpay webhook: {str(e)}")
        return None


def send_payment_confirmation_emails(
    order_id: str,
    consumer_email: str,
    consumer_first_name: str,
    farmer_email: str,
    farmer_first_name: str,
    product_name: str,
    estimated_delivery_date: Optional[str] = None
) -> None:
    """
    Send payment confirmation emails to consumer and farmer.
    
    Args:
        order_id: Order ID
        consumer_email: Consumer's email address
        consumer_first_name: Consumer's first name
        farmer_email: Farmer's email address
        farmer_first_name: Farmer's first name
        product_name: Product name
        estimated_delivery_date: Estimated delivery date (ISO format)
    """
    email_service = get_email_service()
    
    # Send confirmation email to consumer
    try:
        consumer_email_content = get_order_status_update_email(
            consumer_email=consumer_email,
            consumer_first_name=consumer_first_name,
            order_id=order_id,
            product_name=product_name,
            new_status='confirmed',
            estimated_delivery_date=estimated_delivery_date
        )
        
        consumer_result = email_service.send_email(
            recipient=consumer_email,
            subject=consumer_email_content['subject'],
            html_body=consumer_email_content['html_body'],
            text_body=consumer_email_content['text_body']
        )
        
        if not consumer_result.get('success'):
            print(f"Warning: Failed to send consumer confirmation email: {consumer_result.get('error_message')}")
    
    except Exception as e:
        print(f"Warning: Error sending consumer confirmation email: {str(e)}")
    
    # Send notification email to farmer
    try:
        farmer_email_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background-color: #2e7d32;
                    color: white;
                    padding: 20px;
                    text-align: center;
                    border-radius: 5px 5px 0 0;
                }}
                .content {{
                    background-color: #f9f9f9;
                    padding: 30px;
                    border: 1px solid #ddd;
                    border-top: none;
                }}
                .order-details {{
                    background-color: white;
                    padding: 20px;
                    border-radius: 5px;
                    margin: 20px 0;
                }}
                .footer {{
                    text-align: center;
                    padding: 20px;
                    color: #666;
                    font-size: 12px;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>New Order Received!</h1>
            </div>
            <div class="content">
                <p>Hi {farmer_first_name},</p>
                
                <p>Great news! You have received a new order for your product.</p>
                
                <div class="order-details">
                    <h3>Order Details</h3>
                    <p><strong>Order ID:</strong> {order_id}</p>
                    <p><strong>Product:</strong> {product_name}</p>
                    <p><strong>Status:</strong> Confirmed</p>
                </div>
                
                <p>Please log in to your farmer portal to view the full order details and begin processing.</p>
                
                <p>Best regards,<br>The RootTrust Team</p>
            </div>
            <div class="footer">
                <p>This is an automated message. Please do not reply to this email.</p>
                <p>&copy; 2024 RootTrust. All rights reserved.</p>
            </div>
        </body>
        </html>
        """
        
        farmer_email_text = f"""
        New Order Received!
        
        Hi {farmer_first_name},
        
        Great news! You have received a new order for your product.
        
        Order Details:
        - Order ID: {order_id}
        - Product: {product_name}
        - Status: Confirmed
        
        Please log in to your farmer portal to view the full order details and begin processing.
        
        Best regards,
        The RootTrust Team
        
        ---
        This is an automated message. Please do not reply to this email.
        © 2024 RootTrust. All rights reserved.
        """
        
        farmer_result = email_service.send_email(
            recipient=farmer_email,
            subject=f"RootTrust: New Order for {product_name}",
            html_body=farmer_email_html,
            text_body=farmer_email_text
        )
        
        if not farmer_result.get('success'):
            print(f"Warning: Failed to send farmer notification email: {farmer_result.get('error_message')}")
    
    except Exception as e:
        print(f"Warning: Error sending farmer notification email: {str(e)}")


def send_payment_failure_email(
    consumer_email: str,
    consumer_first_name: str,
    order_id: str,
    product_name: str
) -> None:
    """
    Send payment failure notification to consumer.
    
    Args:
        consumer_email: Consumer's email address
        consumer_first_name: Consumer's first name
        order_id: Order ID
        product_name: Product name
    """
    email_service = get_email_service()
    
    try:
        failure_email_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background-color: #d32f2f;
                    color: white;
                    padding: 20px;
                    text-align: center;
                    border-radius: 5px 5px 0 0;
                }}
                .content {{
                    background-color: #f9f9f9;
                    padding: 30px;
                    border: 1px solid #ddd;
                    border-top: none;
                }}
                .order-details {{
                    background-color: white;
                    padding: 20px;
                    border-radius: 5px;
                    margin: 20px 0;
                }}
                .footer {{
                    text-align: center;
                    padding: 20px;
                    color: #666;
                    font-size: 12px;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Payment Failed</h1>
            </div>
            <div class="content">
                <p>Hi {consumer_first_name},</p>
                
                <p>Unfortunately, your payment for the following order could not be processed.</p>
                
                <div class="order-details">
                    <h3>Order Details</h3>
                    <p><strong>Order ID:</strong> {order_id}</p>
                    <p><strong>Product:</strong> {product_name}</p>
                    <p><strong>Status:</strong> Payment Failed</p>
                </div>
                
                <p>You can try placing the order again or contact our support team if you need assistance.</p>
                
                <p>Best regards,<br>The RootTrust Team</p>
            </div>
            <div class="footer">
                <p>This is an automated message. Please do not reply to this email.</p>
                <p>&copy; 2024 RootTrust. All rights reserved.</p>
            </div>
        </body>
        </html>
        """
        
        failure_email_text = f"""
        Payment Failed
        
        Hi {consumer_first_name},
        
        Unfortunately, your payment for the following order could not be processed.
        
        Order Details:
        - Order ID: {order_id}
        - Product: {product_name}
        - Status: Payment Failed
        
        You can try placing the order again or contact our support team if you need assistance.
        
        Best regards,
        The RootTrust Team
        
        ---
        This is an automated message. Please do not reply to this email.
        © 2024 RootTrust. All rights reserved.
        """
        
        result = email_service.send_email(
            recipient=consumer_email,
            subject="RootTrust: Payment Failed",
            html_body=failure_email_html,
            text_body=failure_email_text
        )
        
        if not result.get('success'):
            print(f"Warning: Failed to send payment failure email: {result.get('error_message')}")
    
    except Exception as e:
        print(f"Warning: Error sending payment failure email: {str(e)}")


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for payment webhook endpoint.
    
    Verifies webhook signature, parses payment status, updates transaction and order records,
    and sends appropriate email notifications.
    
    Args:
        event: API Gateway event
        context: Lambda context
        
    Returns:
        API Gateway response with 200 OK or error status
    """
    try:
        # Get raw request body for signature verification
        raw_body = event.get('body', '')
        
        # Parse request body
        try:
            body = json.loads(raw_body) if raw_body else {}
        except json.JSONDecodeError:
            print("Invalid JSON in webhook payload")
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'INVALID_JSON',
                        'message': 'Request body must be valid JSON'
                    }
                })
            }
        
        # Extract headers
        headers = event.get('headers', {})
        
        # Determine payment gateway and verify signature
        stripe_signature = headers.get('stripe-signature') or headers.get('Stripe-Signature')
        razorpay_signature = headers.get('x-razorpay-signature') or headers.get('X-Razorpay-Signature')
        
        payment_data = None
        
        if stripe_signature:
            # Verify Stripe webhook signature
            stripe_secret = os.environ.get('STRIPE_WEBHOOK_SECRET', 'whsec_test_secret')
            
            if not verify_stripe_signature(raw_body, stripe_signature, stripe_secret):
                print("Invalid Stripe webhook signature")
                return {
                    'statusCode': 401,
                    'headers': {
                        'Content-Type': 'application/json'
                    },
                    'body': json.dumps({
                        'error': {
                            'code': 'INVALID_SIGNATURE',
                            'message': 'Webhook signature verification failed'
                        }
                    })
                }
            
            # Parse Stripe webhook payload
            payment_data = parse_stripe_webhook(body)
        
        elif razorpay_signature:
            # Verify Razorpay webhook signature
            razorpay_secret = os.environ.get('RAZORPAY_WEBHOOK_SECRET', 'test_secret')
            
            if not verify_razorpay_signature(raw_body, razorpay_signature, razorpay_secret):
                print("Invalid Razorpay webhook signature")
                return {
                    'statusCode': 401,
                    'headers': {
                        'Content-Type': 'application/json'
                    },
                    'body': json.dumps({
                        'error': {
                            'code': 'INVALID_SIGNATURE',
                            'message': 'Webhook signature verification failed'
                        }
                    })
                }
            
            # Parse Razorpay webhook payload
            payment_data = parse_razorpay_webhook(body)
        
        else:
            print("No recognized payment gateway signature found")
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'MISSING_SIGNATURE',
                        'message': 'Payment gateway signature header is required'
                    }
                })
            }
        
        # Validate parsed payment data
        if not payment_data:
            print("Failed to parse webhook payload")
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'INVALID_PAYLOAD',
                        'message': 'Could not parse payment data from webhook'
                    }
                })
            }
        
        transaction_id = payment_data.get('transactionId')
        order_id = payment_data.get('orderId')
        amount = payment_data.get('amount')
        status = payment_data.get('status')
        gateway = payment_data.get('gateway')
        
        if not all([transaction_id, order_id, status]):
            print(f"Missing required fields in payment data: {payment_data}")
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'INVALID_PAYLOAD',
                        'message': 'Missing required payment fields'
                    }
                })
            }
        
        # Store transaction in DynamoDB
        now = datetime.utcnow()
        
        transaction_pk = f"TRANSACTION#{transaction_id}"
        transaction_sk = "METADATA"
        
        transaction_item = {
            'PK': transaction_pk,
            'SK': transaction_sk,
            'EntityType': 'Transaction',
            'transactionId': transaction_id,
            'orderId': order_id,
            'amount': amount,
            'currency': 'INR',
            'status': status,
            'paymentGateway': gateway,
            'gatewayResponse': body,
            'createdAt': now.isoformat(),
            'completedAt': now.isoformat() if status == PaymentStatus.COMPLETED.value else None,
            'GSI2PK': f"ORDER#{order_id}",
            'GSI2SK': f"TRANSACTION#{now.isoformat()}"
        }
        
        try:
            put_item(transaction_item)
        except Exception as e:
            print(f"Error storing transaction: {str(e)}")
            # Continue processing even if transaction storage fails
        
        # Update order status based on payment outcome
        order_pk = f"ORDER#{order_id}"
        order_sk = "METADATA"
        
        # Get order details for email notifications
        try:
            order_item = get_item(order_pk, order_sk)
        except Exception as e:
            print(f"Error querying order: {str(e)}")
            # Return 200 OK to acknowledge webhook even if order update fails
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json'
                },
                'body': json.dumps({
                    'message': 'Webhook received but order update failed'
                })
            }
        
        if not order_item:
            print(f"Order {order_id} not found")
            # Return 200 OK to acknowledge webhook
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json'
                },
                'body': json.dumps({
                    'message': 'Webhook received but order not found'
                })
            }
        
        # Update order based on payment status
        if status == PaymentStatus.COMPLETED.value:
            # Payment success: update order to confirmed
            try:
                update_item(
                    pk=order_pk,
                    sk=order_sk,
                    update_expression='SET #status = :status, paymentStatus = :payment_status, updatedAt = :updated',
                    expression_attribute_names={
                        '#status': 'status'
                    },
                    expression_attribute_values={
                        ':status': OrderStatus.CONFIRMED.value,
                        ':payment_status': PaymentStatus.COMPLETED.value,
                        ':updated': now.isoformat()
                    }
                )
            except Exception as e:
                print(f"Error updating order status: {str(e)}")
            
            # Get consumer and farmer details for email notifications
            consumer_id = order_item.get('consumerId')
            farmer_id = order_item.get('farmerId')
            product_name = order_item.get('productName', 'Product')
            estimated_delivery_date = order_item.get('estimatedDeliveryDate')
            
            # Get consumer details
            try:
                consumer_pk = f"USER#{consumer_id}"
                consumer_sk = "PROFILE"
                consumer_item = get_item(consumer_pk, consumer_sk)
                consumer_email = consumer_item.get('email') if consumer_item else None
                consumer_first_name = consumer_item.get('firstName', 'Customer') if consumer_item else 'Customer'
            except Exception as e:
                print(f"Error querying consumer: {str(e)}")
                consumer_email = None
                consumer_first_name = 'Customer'
            
            # Get farmer details
            try:
                farmer_pk = f"USER#{farmer_id}"
                farmer_sk = "PROFILE"
                farmer_item = get_item(farmer_pk, farmer_sk)
                farmer_email = farmer_item.get('email') if farmer_item else None
                farmer_first_name = farmer_item.get('firstName', 'Farmer') if farmer_item else 'Farmer'
            except Exception as e:
                print(f"Error querying farmer: {str(e)}")
                farmer_email = None
                farmer_first_name = 'Farmer'
            
            # Send confirmation emails to both consumer and farmer
            if consumer_email and farmer_email:
                send_payment_confirmation_emails(
                    order_id=order_id,
                    consumer_email=consumer_email,
                    consumer_first_name=consumer_first_name,
                    farmer_email=farmer_email,
                    farmer_first_name=farmer_first_name,
                    product_name=product_name,
                    estimated_delivery_date=estimated_delivery_date
                )
        
        elif status == PaymentStatus.FAILED.value:
            # Payment failed: update order to failed
            try:
                update_item(
                    pk=order_pk,
                    sk=order_sk,
                    update_expression='SET #status = :status, paymentStatus = :payment_status, updatedAt = :updated',
                    expression_attribute_names={
                        '#status': 'status'
                    },
                    expression_attribute_values={
                        ':status': OrderStatus.FAILED.value,
                        ':payment_status': PaymentStatus.FAILED.value,
                        ':updated': now.isoformat()
                    }
                )
            except Exception as e:
                print(f"Error updating order status: {str(e)}")
            
            # Get consumer details for failure notification
            consumer_id = order_item.get('consumerId')
            product_name = order_item.get('productName', 'Product')
            
            try:
                consumer_pk = f"USER#{consumer_id}"
                consumer_sk = "PROFILE"
                consumer_item = get_item(consumer_pk, consumer_sk)
                consumer_email = consumer_item.get('email') if consumer_item else None
                consumer_first_name = consumer_item.get('firstName', 'Customer') if consumer_item else 'Customer'
            except Exception as e:
                print(f"Error querying consumer: {str(e)}")
                consumer_email = None
                consumer_first_name = 'Customer'
            
            # Send failure notification to consumer
            if consumer_email:
                send_payment_failure_email(
                    consumer_email=consumer_email,
                    consumer_first_name=consumer_first_name,
                    order_id=order_id,
                    product_name=product_name
                )
        
        # Return 200 OK to acknowledge webhook
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'message': 'Webhook processed successfully',
                'transactionId': transaction_id,
                'orderId': order_id,
                'status': status
            })
        }
    
    except Exception as e:
        # Catch-all for unexpected errors
        print(f"Unexpected error in webhook handler: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Return 200 OK even on error to prevent webhook retries
        # Log the error for investigation
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'message': 'Webhook received but processing failed',
                'error': str(e)
            })
        }
