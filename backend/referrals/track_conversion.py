"""
Referral conversion tracking Lambda handler for RootTrust marketplace.
Handles POST /referrals/track endpoint for tracking referral conversions.
"""
import json
import os
from datetime import datetime
from typing import Dict, Any
from decimal import Decimal

# Import shared modules
import sys
sys.path.append('/opt/python')

from models import ReferralConversion
from validators import ReferralTrackConversionRequest, validate_request_body
from database import get_item, update_item
from constants import OrderStatus
from exceptions import (
    ValidationError, ResourceNotFoundError, ServiceUnavailableError
)


# Reward percentage (5% of order total)
REWARD_PERCENTAGE = 0.05


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for referral conversion tracking endpoint.
    
    Accepts referralCode and orderId, calculates reward amount,
    updates referral record with conversion, and credits referrer's reward balance.
    
    Args:
        event: API Gateway event
        context: Lambda context
        
    Returns:
        API Gateway response with conversion details
    """
    try:
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
        
        # Validate conversion tracking request data
        try:
            track_request = validate_request_body(body, ReferralTrackConversionRequest)
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
        
        # Query referral record
        referral_pk = f"REFERRAL#{track_request.referralCode}"
        referral_sk = "METADATA"
        
        try:
            referral_item = get_item(referral_pk, referral_sk)
        except Exception as e:
            print(f"Error querying referral: {str(e)}")
            return {
                'statusCode': 503,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'SERVICE_UNAVAILABLE',
                        'message': 'Failed to query referral',
                        'details': str(e)
                    }
                })
            }
        
        if not referral_item:
            return {
                'statusCode': 404,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'RESOURCE_NOT_FOUND',
                        'message': f'Referral with code {track_request.referralCode} not found'
                    }
                })
            }
        
        # Query order record to get order details
        order_pk = f"ORDER#{track_request.orderId}"
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
                        'message': f'Order with ID {track_request.orderId} not found'
                    }
                })
            }
        
        # Extract order details
        order_total = float(order_item.get('totalAmount', 0))
        consumer_id = order_item.get('consumerId')
        referrer_id = referral_item.get('referrerId')
        
        # Calculate reward amount (5% of order total)
        reward_amount = order_total * REWARD_PERCENTAGE
        
        # Create conversion record
        now = datetime.utcnow()
        conversion = {
            'referredUserId': consumer_id,
            'orderId': track_request.orderId,
            'rewardAmount': reward_amount,
            'convertedAt': now.isoformat()
        }
        
        # Get existing conversions
        existing_conversions = referral_item.get('conversions', [])
        
        # Check if this order has already been tracked
        for existing_conversion in existing_conversions:
            if existing_conversion.get('orderId') == track_request.orderId:
                return {
                    'statusCode': 409,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({
                        'error': {
                            'code': 'CONFLICT',
                            'message': f'Order {track_request.orderId} has already been tracked for this referral'
                        }
                    })
                }
        
        # Append new conversion to list
        existing_conversions.append(conversion)
        
        # Calculate new totals
        new_total_conversions = referral_item.get('totalConversions', 0) + 1
        new_total_rewards = float(referral_item.get('totalRewards', 0)) + reward_amount
        
        # Update referral record with conversion
        try:
            update_item(
                pk=referral_pk,
                sk=referral_sk,
                update_expression='SET conversions = :conversions, totalConversions = :total_conversions, totalRewards = :total_rewards',
                expression_attribute_values={
                    ':conversions': existing_conversions,
                    ':total_conversions': new_total_conversions,
                    ':total_rewards': Decimal(str(new_total_rewards))
                }
            )
        except Exception as e:
            print(f"Error updating referral record: {str(e)}")
            return {
                'statusCode': 503,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'SERVICE_UNAVAILABLE',
                        'message': 'Failed to update referral record',
                        'details': str(e)
                    }
                })
            }
        
        # Update referrer's consumer profile reward balance
        user_pk = f"USER#{referrer_id}"
        user_sk = "PROFILE"
        
        try:
            user_item = get_item(user_pk, user_sk)
        except Exception as e:
            print(f"Error querying user: {str(e)}")
            # Continue even if user query fails - conversion is already tracked
            user_item = None
        
        if user_item:
            # Get current reward balance
            consumer_profile = user_item.get('consumerProfile', {})
            current_balance = float(consumer_profile.get('referralRewardBalance', 0))
            new_balance = current_balance + reward_amount
            
            # Update user's reward balance
            try:
                update_item(
                    pk=user_pk,
                    sk=user_sk,
                    update_expression='SET consumerProfile.referralRewardBalance = :balance',
                    expression_attribute_values={
                        ':balance': Decimal(str(new_balance))
                    }
                )
            except Exception as e:
                print(f"Error updating user reward balance: {str(e)}")
                # Log error but don't fail the request - conversion is already tracked
        
        # Return success response
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'message': 'Referral conversion tracked successfully',
                'conversion': {
                    'referralCode': track_request.referralCode,
                    'orderId': track_request.orderId,
                    'referredUserId': consumer_id,
                    'rewardAmount': reward_amount,
                    'convertedAt': conversion['convertedAt']
                },
                'referralStats': {
                    'totalConversions': new_total_conversions,
                    'totalRewards': new_total_rewards
                }
            })
        }
    
    except Exception as e:
        # Catch-all for unexpected errors
        print(f"Unexpected error in referral conversion tracking: {str(e)}")
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
