"""
Referral rewards Lambda handler for RootTrust marketplace.
Handles GET /referrals/rewards endpoint for consumers to view their referral rewards.
"""
import json
import os
from typing import Dict, Any

# Import shared modules
import sys
sys.path.append('/opt/python')

from database import get_item, query
from auth import get_user_from_token
from constants import UserRole
from exceptions import (
    AuthenticationError, AuthorizationError, ServiceUnavailableError
)
from boto3.dynamodb.conditions import Key


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for referral rewards endpoint.
    
    Validates JWT token, consumer role authorization, queries user's referral reward balance,
    queries user's referrals, and returns reward information with redemption options.
    
    Args:
        event: API Gateway event
        context: Lambda context
        
    Returns:
        API Gateway response with reward balance, total conversions, and redemption options
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
            user_id = user_info['userId']
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
                        'message': 'Only consumers can view referral rewards'
                    }
                })
            }
        
        # Query user's consumer profile for referral reward balance
        user_pk = f"USER#{user_id}"
        user_sk = "PROFILE"
        
        try:
            user_item = get_item(user_pk, user_sk)
        except Exception as e:
            print(f"Error querying user profile: {str(e)}")
            return {
                'statusCode': 503,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'SERVICE_UNAVAILABLE',
                        'message': 'Failed to query user profile',
                        'details': str(e)
                    }
                })
            }
        
        if not user_item:
            return {
                'statusCode': 404,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'RESOURCE_NOT_FOUND',
                        'message': f'User profile not found'
                    }
                })
            }
        
        # Extract referral reward balance from consumer profile
        consumer_profile = user_item.get('consumerProfile', {})
        reward_balance = float(consumer_profile.get('referralRewardBalance', 0.0))
        
        # Query user's referrals using GSI2 with GSI2PK=REFERRER#{userId}
        gsi2_pk = f"REFERRER#{user_id}"
        
        try:
            query_result = query(
                key_condition_expression=Key('GSI2PK').eq(gsi2_pk),
                index_name='GSI2'
            )
            referrals = query_result.get('Items', [])
        except Exception as e:
            print(f"Error querying referrals: {str(e)}")
            return {
                'statusCode': 503,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'SERVICE_UNAVAILABLE',
                        'message': 'Failed to query referrals',
                        'details': str(e)
                    }
                })
            }
        
        # Calculate total conversions across all referrals
        total_conversions = sum(referral.get('totalConversions', 0) for referral in referrals)
        
        # Calculate total rewards earned across all referrals
        total_rewards_earned = sum(float(referral.get('totalRewards', 0.0)) for referral in referrals)
        
        # Prepare referral summary data
        referral_summaries = []
        for referral in referrals:
            referral_summaries.append({
                'referralCode': referral.get('referralCode'),
                'productId': referral.get('productId'),
                'conversions': referral.get('totalConversions', 0),
                'rewardsEarned': float(referral.get('totalRewards', 0.0)),
                'createdAt': referral.get('createdAt')
            })
        
        # Define redemption options
        redemption_options = [
            {
                'type': 'wallet_credit',
                'name': 'Wallet Credit',
                'description': 'Apply rewards as credit to your RootTrust wallet for future purchases',
                'minimumAmount': 10.0,
                'available': reward_balance >= 10.0
            },
            {
                'type': 'order_discount',
                'name': 'Order Discount',
                'description': 'Use rewards as a discount on your next order',
                'minimumAmount': 5.0,
                'available': reward_balance >= 5.0
            },
            {
                'type': 'bank_transfer',
                'name': 'Bank Transfer',
                'description': 'Transfer rewards to your bank account (processing fee may apply)',
                'minimumAmount': 50.0,
                'available': reward_balance >= 50.0
            }
        ]
        
        # Return success response
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'rewardBalance': reward_balance,
                'totalConversions': total_conversions,
                'totalRewardsEarned': total_rewards_earned,
                'referralCount': len(referrals),
                'referrals': referral_summaries,
                'redemptionOptions': redemption_options
            })
        }
    
    except Exception as e:
        # Catch-all for unexpected errors
        print(f"Unexpected error in referral rewards: {str(e)}")
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
