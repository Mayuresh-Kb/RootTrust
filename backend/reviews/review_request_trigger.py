"""
Review request email trigger Lambda handler for RootTrust marketplace.
Listens to DynamoDB Stream for order status changes to 'delivered' and schedules review request emails.
"""
import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List

# Import shared modules
import sys
sys.path.append('/opt/python')

from database import get_item
from email_service import get_email_service
from email_templates import get_review_request_email
from constants import OrderStatus


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for DynamoDB Stream events.
    
    Processes order status changes and sends review request emails when orders are delivered.
    According to Requirement 14.1, review request emails should be sent within 24 hours of delivery.
    
    Args:
        event: DynamoDB Stream event containing records
        context: Lambda context
        
    Returns:
        Dictionary with processing results
    """
    print(f"Processing {len(event.get('Records', []))} stream records")
    
    processed_count = 0
    error_count = 0
    emails_sent = 0
    
    for record in event.get('Records', []):
        try:
            # Only process MODIFY events (status updates)
            event_name = record.get('eventName')
            if event_name != 'MODIFY':
                continue
            
            # Get new and old images
            new_image = record.get('dynamodb', {}).get('NewImage', {})
            old_image = record.get('dynamodb', {}).get('OldImage', {})
            
            # Check if this is an order entity
            entity_type = new_image.get('EntityType', {}).get('S', '')
            if entity_type != 'Order':
                continue
            
            # Extract status from new and old images
            new_status = new_image.get('status', {}).get('S', '')
            old_status = old_image.get('status', {}).get('S', '')
            
            # Check if status changed to 'delivered'
            if new_status == OrderStatus.DELIVERED.value and old_status != OrderStatus.DELIVERED.value:
                print(f"Order status changed to delivered: {new_image.get('orderId', {}).get('S', 'unknown')}")
                
                # Extract order details from new image
                order_id = new_image.get('orderId', {}).get('S', '')
                consumer_id = new_image.get('consumerId', {}).get('S', '')
                farmer_id = new_image.get('farmerId', {}).get('S', '')
                product_id = new_image.get('productId', {}).get('S', '')
                product_name = new_image.get('productName', {}).get('S', '')
                
                if not all([order_id, consumer_id, farmer_id, product_id, product_name]):
                    print(f"Warning: Missing required fields in order record")
                    error_count += 1
                    continue
                
                # Get consumer information
                consumer_pk = f"USER#{consumer_id}"
                consumer_sk = "PROFILE"
                
                try:
                    consumer_item = get_item(consumer_pk, consumer_sk)
                except Exception as e:
                    print(f"Error fetching consumer {consumer_id}: {str(e)}")
                    error_count += 1
                    continue
                
                if not consumer_item:
                    print(f"Warning: Consumer {consumer_id} not found")
                    error_count += 1
                    continue
                
                # Check notification preferences
                notification_prefs = consumer_item.get('notificationPreferences', {})
                if not notification_prefs.get('reviewRequests', True):
                    print(f"Consumer {consumer_id} has disabled review request notifications")
                    processed_count += 1
                    continue
                
                consumer_email = consumer_item.get('email')
                consumer_first_name = consumer_item.get('firstName', 'Customer')
                
                # Get farmer information for the email
                farmer_pk = f"USER#{farmer_id}"
                farmer_sk = "PROFILE"
                
                try:
                    farmer_item = get_item(farmer_pk, farmer_sk)
                except Exception as e:
                    print(f"Error fetching farmer {farmer_id}: {str(e)}")
                    # Continue with default farmer name
                    farmer_item = None
                
                farmer_name = 'Your Farmer'
                if farmer_item:
                    farmer_profile = farmer_item.get('farmerProfile', {})
                    farmer_name = farmer_profile.get('farmName') or f"{farmer_item.get('firstName', '')} {farmer_item.get('lastName', '')}".strip() or 'Your Farmer'
                
                # Send review request email
                try:
                    email_service = get_email_service()
                    email_content = get_review_request_email(
                        consumer_email=consumer_email,
                        consumer_first_name=consumer_first_name,
                        order_id=order_id,
                        product_name=product_name,
                        product_id=product_id,
                        farmer_name=farmer_name
                    )
                    
                    email_result = email_service.send_email(
                        recipient=consumer_email,
                        subject=email_content['subject'],
                        html_body=email_content['html_body'],
                        text_body=email_content['text_body']
                    )
                    
                    if email_result.get('success'):
                        print(f"Review request email sent to {consumer_email} for order {order_id}")
                        emails_sent += 1
                    else:
                        print(f"Failed to send review request email: {email_result.get('error_message')}")
                        error_count += 1
                except Exception as e:
                    print(f"Error sending review request email: {str(e)}")
                    error_count += 1
                    continue
                
                processed_count += 1
        
        except Exception as e:
            print(f"Error processing stream record: {str(e)}")
            import traceback
            traceback.print_exc()
            error_count += 1
            continue
    
    result = {
        'statusCode': 200,
        'body': json.dumps({
            'message': 'Stream processing completed',
            'processed': processed_count,
            'emails_sent': emails_sent,
            'errors': error_count
        })
    }
    
    print(f"Processing complete: {processed_count} processed, {emails_sent} emails sent, {error_count} errors")
    
    return result
