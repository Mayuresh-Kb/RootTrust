"""
Sales streak tracking Lambda handler for RootTrust marketplace.
Listens to DynamoDB Stream for new reviews and tracks farmer sales streaks.
Awards bonus when farmer reaches 10 consecutive sales with ratings >= 3 stars.
"""
import json
import os
from datetime import datetime
from typing import Dict, Any, List
from decimal import Decimal

# Import shared modules
import sys
sys.path.append('/opt/python')

from database import get_item, update_item, query
from email_service import get_email_service
from email_templates import get_farmer_bonus_email
from constants import MIN_ACCEPTABLE_RATING, SALES_STREAK_THRESHOLD
from boto3.dynamodb.conditions import Key


# Bonus amount for sales streak achievement
SALES_STREAK_BONUS_AMOUNT = 1000.0  # ₹1000 bonus


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for DynamoDB Stream events.
    
    Processes new review submissions and tracks farmer sales streaks.
    According to Requirement 12.1, when a farmer completes 10 consecutive sales
    without negative reviews (all ratings >= 3 stars), award a bonus.
    
    Args:
        event: DynamoDB Stream event containing records
        context: Lambda context
        
    Returns:
        Dictionary with processing results
    """
    print(f"Processing {len(event.get('Records', []))} stream records")
    
    processed_count = 0
    error_count = 0
    bonuses_awarded = 0
    
    for record in event.get('Records', []):
        try:
            # Only process INSERT events (new reviews)
            event_name = record.get('eventName')
            if event_name != 'INSERT':
                continue
            
            # Get new image
            new_image = record.get('dynamodb', {}).get('NewImage', {})
            
            # Check if this is a review entity
            entity_type = new_image.get('EntityType', {}).get('S', '')
            if entity_type != 'Review':
                continue
            
            print(f"New review detected: {new_image.get('reviewId', {}).get('S', 'unknown')}")
            
            # Extract review details from new image
            review_id = new_image.get('reviewId', {}).get('S', '')
            farmer_id = new_image.get('farmerId', {}).get('S', '')
            product_id = new_image.get('productId', {}).get('S', '')
            order_id = new_image.get('orderId', {}).get('S', '')
            rating = int(new_image.get('rating', {}).get('N', '0'))
            
            if not all([review_id, farmer_id, product_id, order_id]):
                print(f"Warning: Missing required fields in review record")
                error_count += 1
                continue
            
            # Get farmer information
            farmer_pk = f"USER#{farmer_id}"
            farmer_sk = "PROFILE"
            
            try:
                farmer_item = get_item(farmer_pk, farmer_sk)
            except Exception as e:
                print(f"Error fetching farmer {farmer_id}: {str(e)}")
                error_count += 1
                continue
            
            if not farmer_item:
                print(f"Warning: Farmer {farmer_id} not found")
                error_count += 1
                continue
            
            # Check notification preferences
            notification_prefs = farmer_item.get('notificationPreferences', {})
            farmer_email = farmer_item.get('email')
            farmer_first_name = farmer_item.get('firstName', 'Farmer')
            
            # Get farmer profile
            farmer_profile = farmer_item.get('farmerProfile', {})
            current_streak = farmer_profile.get('consecutiveSalesStreak', 0)
            bonuses_earned = farmer_profile.get('bonusesEarned', 0.0)
            
            # Query farmer's last 10 orders with reviews
            # We need to get orders for this farmer and check their review status
            try:
                # Query orders using GSI3 (FARMER#farmerId)
                orders_result = query(
                    key_condition_expression=Key('GSI3PK').eq(f"FARMER#{farmer_id}"),
                    index_name='GSI3',
                    limit=10,
                    scan_index_forward=False  # Most recent first
                )
                
                orders = orders_result.get('Items', [])
                
                if len(orders) < 10:
                    print(f"Farmer {farmer_id} has only {len(orders)} orders, need 10 for streak evaluation")
                    # Update streak to current order count if less than 10
                    # This is not a full streak yet
                    processed_count += 1
                    continue
                
                # Get the last 10 orders
                last_10_orders = orders[:10]
                
                # Check if all last 10 orders have reviews with rating >= 3
                all_orders_have_good_reviews = True
                orders_with_reviews = 0
                
                for order in last_10_orders:
                    order_id_check = order.get('orderId')
                    product_id_check = order.get('productId')
                    
                    if not order_id_check or not product_id_check:
                        continue
                    
                    # Query for review of this order
                    # Reviews are stored with PK=PRODUCT#{productId}, SK=REVIEW#{reviewId}
                    # We need to find the review for this specific order
                    try:
                        reviews_result = query(
                            key_condition_expression=Key('PK').eq(f"PRODUCT#{product_id_check}") & Key('SK').begins_with('REVIEW#')
                        )
                        
                        order_reviews = reviews_result.get('Items', [])
                        
                        # Find review for this specific order
                        order_review = None
                        for review in order_reviews:
                            if review.get('orderId') == order_id_check:
                                order_review = review
                                break
                        
                        if order_review:
                            orders_with_reviews += 1
                            review_rating = order_review.get('rating', 0)
                            
                            if review_rating < MIN_ACCEPTABLE_RATING:
                                all_orders_have_good_reviews = False
                                print(f"Order {order_id_check} has rating {review_rating} < {MIN_ACCEPTABLE_RATING}")
                                break
                        else:
                            # Order doesn't have a review yet
                            all_orders_have_good_reviews = False
                            print(f"Order {order_id_check} doesn't have a review yet")
                            break
                    
                    except Exception as e:
                        print(f"Error querying reviews for order {order_id_check}: {str(e)}")
                        all_orders_have_good_reviews = False
                        break
                
                # Calculate new streak
                new_streak = orders_with_reviews if all_orders_have_good_reviews else 0
                
                print(f"Farmer {farmer_id}: {orders_with_reviews} orders with reviews, all good: {all_orders_have_good_reviews}, new streak: {new_streak}")
                
                # Check if streak threshold reached and bonus should be awarded
                bonus_awarded = False
                if new_streak >= SALES_STREAK_THRESHOLD and current_streak < SALES_STREAK_THRESHOLD:
                    # Farmer just reached the threshold, award bonus
                    print(f"Farmer {farmer_id} reached sales streak threshold of {SALES_STREAK_THRESHOLD}!")
                    
                    # Convert bonuses_earned to float if it's a Decimal
                    if isinstance(bonuses_earned, Decimal):
                        bonuses_earned = float(bonuses_earned)
                    
                    # Update farmer profile with new streak and bonus
                    try:
                        update_item(
                            pk=farmer_pk,
                            sk=farmer_sk,
                            update_expression='SET farmerProfile.consecutiveSalesStreak = :streak, farmerProfile.bonusesEarned = :bonuses',
                            expression_attribute_values={
                                ':streak': new_streak,
                                ':bonuses': bonuses_earned + SALES_STREAK_BONUS_AMOUNT
                            }
                        )
                        
                        bonus_awarded = True
                        bonuses_awarded += 1
                        
                        print(f"Updated farmer {farmer_id} with streak {new_streak} and bonus ₹{SALES_STREAK_BONUS_AMOUNT}")
                    
                    except Exception as e:
                        print(f"Error updating farmer profile: {str(e)}")
                        error_count += 1
                        continue
                    
                    # Send bonus notification email
                    if notification_prefs.get('farmerBonuses', True) and farmer_email:
                        try:
                            email_service = get_email_service()
                            email_content = get_farmer_bonus_email(
                                farmer_email=farmer_email,
                                farmer_first_name=farmer_first_name,
                                bonus_type="Sales Streak Bonus",
                                bonus_amount=SALES_STREAK_BONUS_AMOUNT,
                                streak_count=new_streak
                            )
                            
                            email_result = email_service.send_email(
                                recipient=farmer_email,
                                subject=email_content['subject'],
                                html_body=email_content['html_body'],
                                text_body=email_content['text_body']
                            )
                            
                            if email_result.get('success'):
                                print(f"Bonus notification email sent to {farmer_email}")
                            else:
                                print(f"Failed to send bonus notification email: {email_result.get('error_message')}")
                        
                        except Exception as e:
                            print(f"Error sending bonus notification email: {str(e)}")
                            # Don't fail the whole process if email fails
                
                else:
                    # Just update the streak count
                    try:
                        update_item(
                            pk=farmer_pk,
                            sk=farmer_sk,
                            update_expression='SET farmerProfile.consecutiveSalesStreak = :streak',
                            expression_attribute_values={
                                ':streak': new_streak
                            }
                        )
                        
                        print(f"Updated farmer {farmer_id} streak to {new_streak}")
                    
                    except Exception as e:
                        print(f"Error updating farmer streak: {str(e)}")
                        error_count += 1
                        continue
                
                processed_count += 1
            
            except Exception as e:
                print(f"Error processing sales streak for farmer {farmer_id}: {str(e)}")
                import traceback
                traceback.print_exc()
                error_count += 1
                continue
        
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
            'bonuses_awarded': bonuses_awarded,
            'errors': error_count
        })
    }
    
    print(f"Processing complete: {processed_count} processed, {bonuses_awarded} bonuses awarded, {error_count} errors")
    
    return result
