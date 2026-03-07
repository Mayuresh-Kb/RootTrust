"""
Followed farmer notification trigger Lambda handler for RootTrust marketplace.
Listens to DynamoDB Stream for new product creation (INSERT events).
Sends email notifications to consumers who follow the farmer and have opted in.
"""
import json
import os
from typing import Dict, Any, List

# Import shared modules
import sys
sys.path.append('/opt/python')

from database import get_item, scan
from email_service import get_email_service
from email_templates import get_followed_farmer_notification_email
from constants import UserRole
from boto3.dynamodb.conditions import Attr


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for DynamoDB Stream events.
    
    Processes new product creation and sends notifications to consumers
    who follow the farmer and have opted in to followed farmer notifications.
    According to Requirement 16.3, consumers who follow a farmer should be
    notified when that farmer lists a new product.
    
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
            # Only process INSERT events (new product creation)
            event_name = record.get('eventName')
            if event_name != 'INSERT':
                continue
            
            # Get new image
            new_image = record.get('dynamodb', {}).get('NewImage', {})
            
            # Check if this is a product entity
            entity_type = new_image.get('EntityType', {}).get('S', '')
            if entity_type != 'Product':
                continue
            
            # Extract product details from new image
            product_id = new_image.get('productId', {}).get('S', '')
            product_name = new_image.get('name', {}).get('S', '')
            category = new_image.get('category', {}).get('S', '')
            price_str = new_image.get('price', {}).get('N', '0')
            price = float(price_str) if price_str else 0.0
            farmer_id = new_image.get('farmerId', {}).get('S', '')
            
            # Get description if available
            description = new_image.get('description', {}).get('S', '')
            
            if not all([product_id, product_name, category, farmer_id]):
                print(f"Warning: Missing required fields in product record")
                error_count += 1
                continue
            
            print(f"New product created: {product_name} (ID: {product_id}) by farmer {farmer_id}")
            
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
            
            # Query all consumers who follow this farmer
            try:
                # Scan for users with role=consumer
                # Note: In production, consider using GSI for better performance
                consumers_result = scan(
                    filter_expression=Attr('EntityType').eq('User') & Attr('role').eq(UserRole.CONSUMER.value)
                )
                
                all_consumers = consumers_result.get('Items', [])
                
                # Filter for consumers who:
                # 1. Have farmerId in their followedFarmers array
                # 2. Have notificationPreferences.followedFarmers=true
                followers = []
                for consumer in all_consumers:
                    consumer_profile = consumer.get('consumerProfile', {})
                    followed_farmers = consumer_profile.get('followedFarmers', [])
                    
                    # Check if this farmer is in the followed list
                    if farmer_id in followed_farmers:
                        # Check notification preference
                        notification_prefs = consumer.get('notificationPreferences', {})
                        if notification_prefs.get('followedFarmers', False):
                            followers.append(consumer)
                
                print(f"Found {len(followers)} followers with notifications enabled for farmer {farmer_id}")
                
                # Send email to each subscribed follower
                for consumer in followers:
                    consumer_email = consumer.get('email')
                    consumer_first_name = consumer.get('firstName', 'Customer')
                    
                    if not consumer_email:
                        print(f"Warning: Consumer missing email address")
                        continue
                    
                    # Check if consumer has unsubscribed from all notifications
                    notification_prefs = consumer.get('notificationPreferences', {})
                    if notification_prefs.get('unsubscribedAt'):
                        print(f"Consumer {consumer_email} has unsubscribed from all notifications")
                        continue
                    
                    try:
                        email_service = get_email_service()
                        email_content = get_followed_farmer_notification_email(
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
                            print(f"Followed farmer notification sent to {consumer_email}")
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
