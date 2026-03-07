"""
Farmer bonus dashboard Lambda handler for RootTrust marketplace.
Handles GET /analytics/farmer/{farmerId}/bonuses endpoint for farmers to view their bonus status.

Requirement 12.3: The Farmer Portal shall display current bonus status and progress toward next reward.
Requirement 12.5: The Farmer Portal shall track and display total bonuses earned.
"""
import json
import os
from typing import Dict, Any
from decimal import Decimal

# Import shared modules
import sys
sys.path.append('/opt/python')

from database import get_item
from auth import get_user_from_token
from constants import UserRole, SALES_STREAK_THRESHOLD
from exceptions import (
    AuthenticationError, AuthorizationError, ServiceUnavailableError
)


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for farmer bonus dashboard endpoint.
    
    Validates JWT token, farmer role authorization, queries farmer record for bonus information,
    calculates progress toward next bonus, and returns bonus dashboard data.
    
    Args:
        event: API Gateway event with farmerId in path parameters
        context: Lambda context
        
    Returns:
        API Gateway response with bonus status, total bonuses, and progress information
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
        
        # Verify farmer role
        if user_role != UserRole.FARMER.value:
            return {
                'statusCode': 403,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'FORBIDDEN',
                        'message': 'Only farmers can view bonus dashboard'
                    }
                })
            }
        
        # Extract farmerId from path parameters
        path_parameters = event.get('pathParameters', {})
        farmer_id = path_parameters.get('farmerId')
        
        if not farmer_id:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'INVALID_REQUEST',
                        'message': 'farmerId is required in path parameters'
                    }
                })
            }
        
        # Verify farmer is accessing their own data
        if user_id != farmer_id:
            return {
                'statusCode': 403,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'FORBIDDEN',
                        'message': 'You can only view your own bonus dashboard'
                    }
                })
            }
        
        # Query farmer record by PK=USER#{farmerId}, SK=PROFILE
        farmer_pk = f"USER#{farmer_id}"
        farmer_sk = "PROFILE"
        
        try:
            farmer_item = get_item(farmer_pk, farmer_sk)
        except Exception as e:
            print(f"Error querying farmer profile: {str(e)}")
            return {
                'statusCode': 503,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'SERVICE_UNAVAILABLE',
                        'message': 'Failed to query farmer profile',
                        'details': str(e)
                    }
                })
            }
        
        if not farmer_item:
            return {
                'statusCode': 404,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'RESOURCE_NOT_FOUND',
                        'message': f'Farmer profile not found'
                    }
                })
            }
        
        # Extract farmer profile data
        farmer_profile = farmer_item.get('farmerProfile', {})
        
        # Get bonus-related fields
        bonuses_earned = farmer_profile.get('bonusesEarned', 0.0)
        consecutive_sales_streak = farmer_profile.get('consecutiveSalesStreak', 0)
        featured_status = farmer_profile.get('featuredStatus', False)
        
        # Convert Decimal to float if needed
        if isinstance(bonuses_earned, Decimal):
            bonuses_earned = float(bonuses_earned)
        
        if isinstance(consecutive_sales_streak, Decimal):
            consecutive_sales_streak = int(consecutive_sales_streak)
        
        # Calculate progress toward next bonus
        # Next milestone is at SALES_STREAK_THRESHOLD (10 sales)
        next_bonus_threshold = SALES_STREAK_THRESHOLD
        
        # Calculate progress string (e.g., "7/10 sales")
        if consecutive_sales_streak >= next_bonus_threshold:
            # Farmer has already reached the threshold
            progress_to_next_bonus = f"{next_bonus_threshold}/{next_bonus_threshold} sales (Bonus earned!)"
            progress_percentage = 100
        else:
            progress_to_next_bonus = f"{consecutive_sales_streak}/{next_bonus_threshold} sales"
            progress_percentage = int((consecutive_sales_streak / next_bonus_threshold) * 100)
        
        # Prepare bonus dashboard response
        bonus_dashboard = {
            'bonusesEarned': bonuses_earned,
            'consecutiveSalesStreak': consecutive_sales_streak,
            'progressToNextBonus': progress_to_next_bonus,
            'progressPercentage': progress_percentage,
            'featuredStatus': featured_status,
            'nextBonusThreshold': next_bonus_threshold,
            'bonusDetails': {
                'salesStreakBonus': {
                    'name': 'Sales Streak Bonus',
                    'description': f'Complete {next_bonus_threshold} consecutive sales without negative reviews',
                    'reward': '₹1000',
                    'currentProgress': consecutive_sales_streak,
                    'threshold': next_bonus_threshold,
                    'achieved': consecutive_sales_streak >= next_bonus_threshold
                },
                'featuredPlacement': {
                    'name': 'Featured Placement',
                    'description': 'Maintain average authenticity confidence score above 90%',
                    'reward': 'Featured status in marketplace',
                    'currentStatus': featured_status,
                    'achieved': featured_status
                }
            }
        }
        
        # Return success response
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(bonus_dashboard)
        }
    
    except Exception as e:
        # Catch-all for unexpected errors
        print(f"Unexpected error in farmer bonus dashboard: {str(e)}")
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
