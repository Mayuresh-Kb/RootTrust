"""
Featured placement eligibility Lambda handler for RootTrust marketplace.
Calculates average authenticityConfidence across all farmer's products and grants
featured status if average > 90%.

This function can be triggered by:
1. DynamoDB Stream when product verification status changes
2. Scheduled EventBridge rule (e.g., daily)
3. Manual invocation via API endpoint

Requirement 12.2: When a farmer achieves high authenticity scores, 
the RootTrust Platform shall grant featured placement for their products.
"""
import json
import os
from typing import Dict, Any, List
from decimal import Decimal

# Import shared modules
import sys
sys.path.append('/opt/python')

from database import get_item, update_item, query
from email_service import get_email_service
from email_templates import get_farmer_bonus_email
from boto3.dynamodb.conditions import Key


# Featured status threshold
FEATURED_STATUS_THRESHOLD = 90.0  # Average authenticityConfidence must be > 90%


def calculate_farmer_featured_status(farmer_id: str) -> Dict[str, Any]:
    """
    Calculate whether a farmer should have featured status based on their
    products' average authenticityConfidence.
    
    Args:
        farmer_id: The farmer's user ID
        
    Returns:
        Dictionary with:
            - should_be_featured: bool
            - average_confidence: float
            - approved_product_count: int
            - error: str (if error occurred)
    """
    try:
        # Query all farmer's products using GSI2 with GSI2PK=FARMER#{farmerId}
        products_result = query(
            key_condition_expression=Key('GSI2PK').eq(f"FARMER#{farmer_id}"),
            index_name='GSI2'
        )
        
        products = products_result.get('Items', [])
        
        if not products:
            print(f"No products found for farmer {farmer_id}")
            return {
                'should_be_featured': False,
                'average_confidence': 0.0,
                'approved_product_count': 0
            }
        
        # Filter for products with verificationStatus=approved
        approved_products = [
            p for p in products 
            if p.get('verificationStatus') == 'approved'
        ]
        
        if not approved_products:
            print(f"No approved products found for farmer {farmer_id}")
            return {
                'should_be_featured': False,
                'average_confidence': 0.0,
                'approved_product_count': 0
            }
        
        # Calculate average authenticityConfidence across all approved products
        total_confidence = 0.0
        products_with_confidence = 0
        
        for product in approved_products:
            confidence = product.get('authenticityConfidence')
            
            if confidence is not None:
                # Convert Decimal to float if needed
                if isinstance(confidence, Decimal):
                    confidence = float(confidence)
                
                total_confidence += confidence
                products_with_confidence += 1
        
        if products_with_confidence == 0:
            print(f"No products with authenticityConfidence for farmer {farmer_id}")
            return {
                'should_be_featured': False,
                'average_confidence': 0.0,
                'approved_product_count': len(approved_products)
            }
        
        # Calculate average
        average_confidence = total_confidence / products_with_confidence
        
        # Determine if farmer should be featured
        should_be_featured = average_confidence > FEATURED_STATUS_THRESHOLD
        
        print(f"Farmer {farmer_id}: {products_with_confidence} products, "
              f"avg confidence: {average_confidence:.2f}%, "
              f"featured: {should_be_featured}")
        
        return {
            'should_be_featured': should_be_featured,
            'average_confidence': average_confidence,
            'approved_product_count': len(approved_products)
        }
    
    except Exception as e:
        print(f"Error calculating featured status for farmer {farmer_id}: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'should_be_featured': False,
            'average_confidence': 0.0,
            'approved_product_count': 0,
            'error': str(e)
        }


def update_farmer_featured_status(farmer_id: str, featured_status: bool) -> bool:
    """
    Update farmer's featuredStatus in DynamoDB.
    
    Args:
        farmer_id: The farmer's user ID
        featured_status: New featured status value
        
    Returns:
        True if update successful, False otherwise
    """
    try:
        farmer_pk = f"USER#{farmer_id}"
        farmer_sk = "PROFILE"
        
        # Update farmer profile
        update_item(
            pk=farmer_pk,
            sk=farmer_sk,
            update_expression='SET farmerProfile.featuredStatus = :status',
            expression_attribute_values={
                ':status': featured_status
            }
        )
        
        print(f"Updated farmer {farmer_id} featuredStatus to {featured_status}")
        return True
    
    except Exception as e:
        print(f"Error updating farmer featured status: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def send_featured_status_notification(
    farmer_email: str,
    farmer_first_name: str,
    featured_status: bool,
    average_confidence: float
) -> bool:
    """
    Send email notification to farmer about featured status change.
    
    Args:
        farmer_email: Farmer's email address
        farmer_first_name: Farmer's first name
        featured_status: New featured status
        average_confidence: Average authenticity confidence score
        
    Returns:
        True if email sent successfully, False otherwise
    """
    try:
        email_service = get_email_service()
        
        if featured_status:
            # Farmer gained featured status
            subject = "🌟 Congratulations! You've Earned Featured Status"
            html_body = f"""
            <html>
            <body>
                <h2>Congratulations, {farmer_first_name}!</h2>
                <p>Your products have achieved an outstanding average authenticity confidence score of <strong>{average_confidence:.1f}%</strong>!</p>
                <p>As a result, you've been granted <strong>Featured Status</strong> on the RootTrust marketplace.</p>
                <h3>What does this mean?</h3>
                <ul>
                    <li>Your products will appear in featured sections of the marketplace</li>
                    <li>Increased visibility to consumers</li>
                    <li>Recognition for your commitment to quality and authenticity</li>
                </ul>
                <p>Keep up the excellent work!</p>
                <p>Best regards,<br>The RootTrust Team</p>
            </body>
            </html>
            """
            text_body = f"""
            Congratulations, {farmer_first_name}!
            
            Your products have achieved an outstanding average authenticity confidence score of {average_confidence:.1f}%!
            
            As a result, you've been granted Featured Status on the RootTrust marketplace.
            
            What does this mean?
            - Your products will appear in featured sections of the marketplace
            - Increased visibility to consumers
            - Recognition for your commitment to quality and authenticity
            
            Keep up the excellent work!
            
            Best regards,
            The RootTrust Team
            """
        else:
            # Farmer lost featured status
            subject = "Update: Featured Status Change"
            html_body = f"""
            <html>
            <body>
                <h2>Hello, {farmer_first_name}</h2>
                <p>We wanted to let you know that your featured status has been updated.</p>
                <p>Your current average authenticity confidence score is <strong>{average_confidence:.1f}%</strong>.</p>
                <p>To regain featured status, maintain an average authenticity confidence score above {FEATURED_STATUS_THRESHOLD}% across all your approved products.</p>
                <h3>Tips to improve your score:</h3>
                <ul>
                    <li>Ensure all product information is accurate and complete</li>
                    <li>Provide clear, high-quality product images</li>
                    <li>Include proper documentation and certifications</li>
                    <li>Maintain consistent quality across all products</li>
                </ul>
                <p>We're here to help you succeed!</p>
                <p>Best regards,<br>The RootTrust Team</p>
            </body>
            </html>
            """
            text_body = f"""
            Hello, {farmer_first_name}
            
            We wanted to let you know that your featured status has been updated.
            
            Your current average authenticity confidence score is {average_confidence:.1f}%.
            
            To regain featured status, maintain an average authenticity confidence score above {FEATURED_STATUS_THRESHOLD}% across all your approved products.
            
            Tips to improve your score:
            - Ensure all product information is accurate and complete
            - Provide clear, high-quality product images
            - Include proper documentation and certifications
            - Maintain consistent quality across all products
            
            We're here to help you succeed!
            
            Best regards,
            The RootTrust Team
            """
        
        email_result = email_service.send_email(
            recipient=farmer_email,
            subject=subject,
            html_body=html_body,
            text_body=text_body
        )
        
        if email_result.get('success'):
            print(f"Featured status notification email sent to {farmer_email}")
            return True
        else:
            print(f"Failed to send featured status notification: {email_result.get('error_message')}")
            return False
    
    except Exception as e:
        print(f"Error sending featured status notification: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for featured status updates.
    
    Can be triggered by:
    1. DynamoDB Stream events (product verification status changes)
    2. EventBridge scheduled events (daily recalculation)
    3. Direct invocation with farmerId in event
    
    Args:
        event: Lambda event (DynamoDB Stream, EventBridge, or direct invocation)
        context: Lambda context
        
    Returns:
        Dictionary with processing results
    """
    print(f"Featured status update handler invoked")
    print(f"Event: {json.dumps(event, default=str)}")
    
    processed_count = 0
    error_count = 0
    status_changes = 0
    farmer_ids_to_process = set()
    
    # Determine which farmers to process based on event type
    
    # Case 1: DynamoDB Stream event (product verification status changed)
    if 'Records' in event and event['Records']:
        print("Processing DynamoDB Stream event")
        
        for record in event['Records']:
            try:
                event_name = record.get('eventName')
                
                # Process INSERT and MODIFY events
                if event_name not in ['INSERT', 'MODIFY']:
                    continue
                
                # Get new image
                new_image = record.get('dynamodb', {}).get('NewImage', {})
                
                # Check if this is a product entity
                entity_type = new_image.get('EntityType', {}).get('S', '')
                if entity_type != 'Product':
                    continue
                
                # Check if verification status is approved
                verification_status = new_image.get('verificationStatus', {}).get('S', '')
                if verification_status != 'approved':
                    continue
                
                # Extract farmer ID
                farmer_id = new_image.get('farmerId', {}).get('S', '')
                if farmer_id:
                    farmer_ids_to_process.add(farmer_id)
                    print(f"Added farmer {farmer_id} to processing queue from stream event")
            
            except Exception as e:
                print(f"Error processing stream record: {str(e)}")
                error_count += 1
                continue
    
    # Case 2: EventBridge scheduled event or direct invocation
    elif 'farmerId' in event:
        # Direct invocation with specific farmer ID
        farmer_id = event['farmerId']
        farmer_ids_to_process.add(farmer_id)
        print(f"Processing specific farmer: {farmer_id}")
    
    elif event.get('source') == 'aws.events':
        # Scheduled event - process all farmers (expensive, use sparingly)
        print("Processing scheduled event - recalculating all farmers")
        # For scheduled events, we would need to query all farmers
        # This is expensive, so we'll skip for now and rely on stream triggers
        # In production, you might want to implement this with pagination
        pass
    
    # Process each farmer
    for farmer_id in farmer_ids_to_process:
        try:
            # Get farmer information
            farmer_pk = f"USER#{farmer_id}"
            farmer_sk = "PROFILE"
            
            farmer_item = get_item(farmer_pk, farmer_sk)
            
            if not farmer_item:
                print(f"Warning: Farmer {farmer_id} not found")
                error_count += 1
                continue
            
            # Check notification preferences
            notification_prefs = farmer_item.get('notificationPreferences', {})
            farmer_email = farmer_item.get('email')
            farmer_first_name = farmer_item.get('firstName', 'Farmer')
            
            # Get current featured status
            farmer_profile = farmer_item.get('farmerProfile', {})
            current_featured_status = farmer_profile.get('featuredStatus', False)
            
            # Calculate new featured status
            calculation_result = calculate_farmer_featured_status(farmer_id)
            
            if 'error' in calculation_result:
                error_count += 1
                continue
            
            new_featured_status = calculation_result['should_be_featured']
            average_confidence = calculation_result['average_confidence']
            
            # Update farmer record if status changed
            if new_featured_status != current_featured_status:
                print(f"Featured status changed for farmer {farmer_id}: "
                      f"{current_featured_status} -> {new_featured_status}")
                
                success = update_farmer_featured_status(farmer_id, new_featured_status)
                
                if success:
                    status_changes += 1
                    
                    # Send notification email if preferences allow
                    if notification_prefs.get('farmerBonuses', True) and farmer_email:
                        send_featured_status_notification(
                            farmer_email=farmer_email,
                            farmer_first_name=farmer_first_name,
                            featured_status=new_featured_status,
                            average_confidence=average_confidence
                        )
                else:
                    error_count += 1
                    continue
            else:
                print(f"No status change for farmer {farmer_id} "
                      f"(current: {current_featured_status}, avg: {average_confidence:.2f}%)")
            
            processed_count += 1
        
        except Exception as e:
            print(f"Error processing farmer {farmer_id}: {str(e)}")
            import traceback
            traceback.print_exc()
            error_count += 1
            continue
    
    result = {
        'statusCode': 200,
        'body': json.dumps({
            'message': 'Featured status update completed',
            'processed': processed_count,
            'status_changes': status_changes,
            'errors': error_count
        })
    }
    
    print(f"Processing complete: {processed_count} processed, "
          f"{status_changes} status changes, {error_count} errors")
    
    return result
