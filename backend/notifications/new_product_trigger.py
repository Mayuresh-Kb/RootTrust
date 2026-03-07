"""
New product notification trigger Lambda handler for RootTrust marketplace.
Listens to DynamoDB Stream for product status changes from pending to approved.
Sends email notifications to consumers who have opted in to receive new product notifications.
"""
import json
import os
from typing import Dict, Any, List

# Import shared modules
import sys
sys.path.append('/opt/python')

from database import get_item, scan
from email_service import get_email_service
from email_templates import get_new_product_notification_email
from constants import VerificationStatus, UserRole
from boto3.dynamodb.conditions import Attr


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for DynamoDB Stream events.
    
    Processes product status changes and sends new product notification emails
    when a product changes from pending to approved.
    According to Requirement 16.2, consumers who have opted in to newProducts
    notifications should be notified when new seasonal products launch.
    
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
            
            # Check if this is a product entity
            entity_type = new_image.get('EntityType', {}).get('S', '')
            if entity_type != 'Product':
                continue
            
            # Extract verification status from new and old images
            new_status = new_image.get('verificationStatus', {}).get('S', '')
            old_status = old_image.get('verificationStatus', {}).get('S', '')
            
            # Check if status changed from pending to approved
            if new_status == VerificationStatus.APPROVED.value and old_status == VerificationStatus.PENDING.value:
                print(f"Product status changed to approved: {new_image.get('productId', {}).get('S', 'unknown')}")
                
                # Extract product details from new image
                product_id = new_image.get('productId', {}).get('S', '')
                product_name = new_image.get('name', {}).get('S', '')
                category = new_image.get('category', {}).get('S', '')
                price = float(new_image.get('price', {}).get('N', '0'))
                farmer_id = new_image.get('farmerId', {}).get('S', '')
                
                # Get description if available
                description = new_image.get('description', {}).get('S', '')
                
                if not all([product_id, product_name, category, farmer_id]):
                    print(f"Warning: Missing required fields in product record")
                    error_count += 1
                    continue
                
                # Get farmer information
                farmer_pk = f"USER#{farmer_id}"
                farmer_sk = "PROFILE"
                
                try:
                    farmer_item = get_item(farmer_pk, farmer_sk)
                except Exception as e:
                    print(f"Error fetching farmer {farmer_id}: {str(e)}")
                    # Continue with default farmer name
                    farmer_item = None
                
                farmer_name = 'RootTrust Farmer'
                if farmer_item:
                    farmer_profile = farmer_item.get('farmerProfile', {})
                    farmer_name = farmer_profile.get('farmName') or f"{farmer_item.get('firstName', '')} {farmer_item.get('lastName', '')}".strip() or 'RootTrust Farmer'
                
                # Query all consumers with newProducts notification preference enabled
                try:
                    # Scan for users with role=consumer
                    # Note: In production, consider using GSI for better performance
                    consumers_result = scan(
                        filter_expression=Attr('EntityType').eq('User') & Attr('role').eq(UserRole.CONSUMER.value)
                    )
                    
                    all_consumers = consumers_result.get('Items', [])
                    
                    # Filter for consumers with newProducts=true in Python
                    consumers = [
                        c for c in all_consumers 
                        if c.get('notificationPreferences', {}).get('newProducts', False) is True
                    ]
                    
                    print(f"Found {len(consumers)} consumers with newProducts notifications enabled")
                    
                    # Send email to each subscribed consumer
                    for consumer in consumers:
                        consumer_email = consumer.get('email')
                        consumer_first_name = consumer.get('firstName', 'Customer')
                        
                        if not consumer_email:
                            print(f"Warning: Consumer missing email address")
                            continue
                        
                        # Check if consumer has unsubscribed
                        notification_prefs = consumer.get('notificationPreferences', {})
                        if notification_prefs.get('unsubscribedAt'):
                            print(f"Consumer {consumer_email} has unsubscribed from all notifications")
                            continue
                        
                        try:
                            email_service = get_email_service()
                            email_content = get_new_product_notification_email(
                                consumer_email=consumer_email,
                                consumer_first_name=consumer_first_name,
                                product_name=product_name,
                                product_id=product_id,
                                category=category,
                                price=price,
                                farmer_name=farmer_name,
                                product_description=description
                            )
                            
                            email_result = email_service.send_email(
                                recipient=consumer_email,
                                subject=email_content['subject'],
                                html_body=email_content['html_body'],
                                text_body=email_content['text_body']
                            )
                            
                            if email_result.get('success'):
                                print(f"New product notification sent to {consumer_email}")
                                emails_sent += 1
                            else:
                                print(f"Failed to send notification to {consumer_email}: {email_result.get('error_message')}")
                                # Don't increment error_count for individual email failures
                                # to avoid failing the entire batch
                        
                        except Exception as e:
                            print(f"Error sending notification to {consumer_email}: {str(e)}")
                            # Continue processing other consumers
                            continue
                
                except Exception as e:
                    print(f"Error querying consumers: {str(e)}")
                    import traceback
                    traceback.print_exc()
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
