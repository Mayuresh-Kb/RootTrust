"""
Promotion expiry check Lambda handler for RootTrust marketplace.
Scheduled by EventBridge to run hourly and check for expired promotions.
Updates promotion status to completed and sends summary emails to farmers.
"""
import json
import os
from typing import Dict, Any, List
from datetime import datetime
from boto3.dynamodb.conditions import Key

# Import shared modules
import sys
sys.path.append('/opt/python')

from database import query, update_item, get_item
from constants import PromotionStatus
from email_service import get_email_service
from email_templates import get_promotion_summary_email


def check_expired_promotions() -> List[Dict[str, Any]]:
    """
    Query active promotions and check if any have passed their endDate.
    
    Returns:
        List of expired promotion records
    """
    expired_promotions = []
    
    try:
        # Query GSI3 for active promotions
        gsi3_pk = f"STATUS#{PromotionStatus.ACTIVE.value}"
        
        result = query(
            key_condition_expression=Key('GSI3PK').eq(gsi3_pk),
            index_name='GSI3',
            scan_index_forward=True  # Oldest endDate first
        )
        
        promotions = result.get('Items', [])
        current_time = datetime.utcnow()
        
        # Check each promotion's endDate
        for promotion in promotions:
            end_date_str = promotion.get('endDate')
            if end_date_str:
                try:
                    # Parse ISO format datetime
                    end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
                    
                    # Check if promotion has expired
                    if end_date <= current_time:
                        expired_promotions.append(promotion)
                except Exception as e:
                    print(f"Error parsing endDate for promotion {promotion.get('promotionId')}: {str(e)}")
                    continue
        
        return expired_promotions
    
    except Exception as e:
        print(f"Error querying active promotions: {str(e)}")
        raise


def update_promotion_status(promotion_id: str) -> bool:
    """
    Update promotion status from active to completed.
    
    Args:
        promotion_id: The promotion ID to update
        
    Returns:
        True if update succeeded, False otherwise
    """
    try:
        new_status = PromotionStatus.COMPLETED.value
        
        update_item(
            pk=f"PROMOTION#{promotion_id}",
            sk="METADATA",
            update_expression="SET #status = :status, #gsi3pk = :gsi3pk",
            expression_attribute_names={
                '#status': 'status',
                '#gsi3pk': 'GSI3PK'
            },
            expression_attribute_values={
                ':status': new_status,
                ':gsi3pk': f"STATUS#{new_status}"
            }
        )
        
        return True
    
    except Exception as e:
        print(f"Error updating promotion {promotion_id} status: {str(e)}")
        return False


def send_summary_email(promotion: Dict[str, Any]) -> bool:
    """
    Send promotion summary email to farmer.
    
    Args:
        promotion: The promotion record
        
    Returns:
        True if email sent successfully, False otherwise
    """
    try:
        # Get farmer details
        farmer_id = promotion.get('farmerId')
        farmer = get_item(f"USER#{farmer_id}", "PROFILE")
        
        if not farmer:
            print(f"Farmer {farmer_id} not found for promotion {promotion.get('promotionId')}")
            return False
        
        farmer_email = farmer.get('email', '')
        farmer_first_name = farmer.get('firstName', 'Farmer')
        
        # Get product details
        product_id = promotion.get('productId')
        product = get_item(f"PRODUCT#{product_id}", "METADATA")
        product_name = product.get('name', 'Product') if product else 'Product'
        
        # Get promotion metrics
        metrics = promotion.get('metrics', {})
        total_views = metrics.get('views', 0)
        total_clicks = metrics.get('clicks', 0)
        total_conversions = metrics.get('conversions', 0)
        total_spent = metrics.get('spent', 0.0)
        
        # Get promotion details
        promotion_id = promotion.get('promotionId')
        budget = promotion.get('budget', 0.0)
        start_date = promotion.get('startDate', '')
        end_date = promotion.get('endDate', '')
        
        # Generate and send summary email
        email_content = get_promotion_summary_email(
            farmer_email=farmer_email,
            farmer_first_name=farmer_first_name,
            promotion_id=promotion_id,
            product_name=product_name,
            start_date=start_date,
            end_date=end_date,
            total_views=total_views,
            total_clicks=total_clicks,
            total_conversions=total_conversions,
            total_spent=total_spent,
            budget=budget
        )
        
        email_service = get_email_service()
        email_result = email_service.send_email(
            recipient=farmer_email,
            subject=email_content['subject'],
            html_body=email_content['html_body'],
            text_body=email_content['text_body']
        )
        
        if email_result.get('success'):
            print(f"Summary email sent to {farmer_email} for promotion {promotion_id}")
            return True
        else:
            print(f"Failed to send summary email: {email_result.get('error_message')}")
            return False
    
    except Exception as e:
        print(f"Error sending summary email for promotion {promotion.get('promotionId')}: {str(e)}")
        return False


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for promotion expiry check.
    
    Triggered by EventBridge on an hourly schedule.
    Checks for expired promotions, updates their status to completed,
    and sends summary emails to farmers.
    
    Args:
        event: EventBridge event
        context: Lambda context
        
    Returns:
        Response with processing summary
    """
    try:
        print("Starting promotion expiry check...")
        
        # Find expired promotions
        expired_promotions = check_expired_promotions()
        
        if not expired_promotions:
            print("No expired promotions found")
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'No expired promotions found',
                    'processed': 0
                })
            }
        
        print(f"Found {len(expired_promotions)} expired promotion(s)")
        
        # Process each expired promotion
        processed_count = 0
        email_sent_count = 0
        failed_updates = []
        failed_emails = []
        
        for promotion in expired_promotions:
            promotion_id = promotion.get('promotionId')
            print(f"Processing expired promotion: {promotion_id}")
            
            # Update status to completed
            if update_promotion_status(promotion_id):
                processed_count += 1
                print(f"Updated promotion {promotion_id} status to completed")
                
                # Send summary email
                if send_summary_email(promotion):
                    email_sent_count += 1
                else:
                    failed_emails.append(promotion_id)
            else:
                failed_updates.append(promotion_id)
        
        # Log summary
        print(f"Promotion expiry check completed:")
        print(f"  - Total expired: {len(expired_promotions)}")
        print(f"  - Status updated: {processed_count}")
        print(f"  - Emails sent: {email_sent_count}")
        
        if failed_updates:
            print(f"  - Failed status updates: {failed_updates}")
        if failed_emails:
            print(f"  - Failed email sends: {failed_emails}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Promotion expiry check completed',
                'totalExpired': len(expired_promotions),
                'statusUpdated': processed_count,
                'emailsSent': email_sent_count,
                'failedUpdates': failed_updates,
                'failedEmails': failed_emails
            })
        }
    
    except Exception as e:
        # Catch-all for unexpected errors
        print(f"Unexpected error in promotion expiry check: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': {
                    'code': 'INTERNAL_ERROR',
                    'message': 'An unexpected error occurred during promotion expiry check',
                    'details': str(e)
                }
            })
        }
