"""
Limited release detail Lambda handler for RootTrust marketplace.
Handles GET /limited-releases/{releaseId} endpoint to get release details with countdown.
"""
import json
import os
from typing import Dict, Any
from datetime import datetime

# Import shared modules
import sys
sys.path.append('/opt/python')

from database import get_item
from constants import LimitedReleaseStatus
from exceptions import ResourceNotFoundError, ServiceUnavailableError


def calculate_time_remaining(end_date_str: str) -> Dict[str, Any]:
    """
    Calculate time remaining until end date.
    
    Args:
        end_date_str: ISO 8601 formatted end date string
        
    Returns:
        Dictionary with countdown information including:
        - expired: boolean indicating if release has expired
        - daysRemaining: number of days remaining
        - hoursRemaining: number of hours remaining (0-23)
        - minutesRemaining: number of minutes remaining (0-59)
        - secondsRemaining: number of seconds remaining (0-59)
        - totalSeconds: total seconds remaining
    """
    try:
        # Parse end date and ensure it's timezone-aware
        end_date_str_clean = end_date_str.replace('Z', '+00:00')
        end_date = datetime.fromisoformat(end_date_str_clean)
        
        # Make end_date timezone-naive if it has timezone info
        if end_date.tzinfo is not None:
            end_date = end_date.replace(tzinfo=None)
        
        now = datetime.utcnow()
        
        if end_date <= now:
            return {
                'expired': True,
                'daysRemaining': 0,
                'hoursRemaining': 0,
                'minutesRemaining': 0,
                'secondsRemaining': 0,
                'totalSeconds': 0
            }
        
        time_remaining = end_date - now
        days = time_remaining.days
        seconds = time_remaining.seconds
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        
        return {
            'expired': False,
            'daysRemaining': days,
            'hoursRemaining': hours,
            'minutesRemaining': minutes,
            'secondsRemaining': secs,
            'totalSeconds': int(time_remaining.total_seconds())
        }
    
    except Exception as e:
        print(f"Error calculating time remaining: {str(e)}")
        return {
            'expired': False,
            'daysRemaining': 0,
            'hoursRemaining': 0,
            'minutesRemaining': 0,
            'secondsRemaining': 0,
            'totalSeconds': 0
        }


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for limited release detail endpoint.
    
    Queries release by PK=LIMITED_RELEASE#{releaseId}.
    Calculates time remaining until endDate.
    Returns release details with countdown timer data.
    
    Args:
        event: API Gateway event with releaseId in path parameters
        context: Lambda context
        
    Returns:
        API Gateway response with release details and countdown
    """
    try:
        # Extract releaseId from path parameters
        path_params = event.get('pathParameters', {})
        release_id = path_params.get('releaseId')
        
        if not release_id:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'BAD_REQUEST',
                        'message': 'releaseId is required in path parameters'
                    }
                })
            }
        
        # Query release by PK
        try:
            release = get_item(f"LIMITED_RELEASE#{release_id}", "METADATA")
            
            if not release:
                return {
                    'statusCode': 404,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({
                        'error': {
                            'code': 'NOT_FOUND',
                            'message': f'Limited release with ID {release_id} not found'
                        }
                    })
                }
        
        except ServiceUnavailableError as e:
            return {
                'statusCode': 503,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'SERVICE_UNAVAILABLE',
                        'message': 'Failed to query limited release',
                        'details': str(e)
                    }
                })
            }
        except Exception as e:
            print(f"Error querying limited release: {str(e)}")
            return {
                'statusCode': 503,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'SERVICE_UNAVAILABLE',
                        'message': 'Failed to query limited release',
                        'details': str(e)
                    }
                })
            }
        
        # Query product details
        product = None
        product_id = release.get('productId')
        if product_id:
            try:
                product = get_item(f"PRODUCT#{product_id}", "METADATA")
            except Exception as e:
                print(f"Error querying product: {str(e)}")
                # Continue without product details
        
        # Calculate time remaining
        end_date = release.get('endDate')
        countdown = calculate_time_remaining(end_date) if end_date else {
            'expired': False,
            'daysRemaining': 0,
            'hoursRemaining': 0,
            'minutesRemaining': 0,
            'secondsRemaining': 0,
            'totalSeconds': 0
        }
        
        # Build response with release details and countdown
        response_data = {
            'releaseId': release.get('releaseId'),
            'farmerId': release.get('farmerId'),
            'productId': product_id,
            'releaseName': release.get('releaseName'),
            'quantityLimit': release.get('quantityLimit'),
            'quantityRemaining': release.get('quantityRemaining'),
            'duration': release.get('duration'),
            'status': release.get('status'),
            'startDate': release.get('startDate'),
            'endDate': end_date,
            'countdown': countdown,
            'subscriberNotificationsSent': release.get('subscriberNotificationsSent', False),
            'createdAt': release.get('createdAt')
        }
        
        # Add product details if available
        if product:
            response_data['product'] = {
                'name': product.get('name'),
                'category': product.get('category'),
                'price': product.get('price'),
                'unit': product.get('unit'),
                'description': product.get('description', ''),
                'images': product.get('images', []),
                'averageRating': product.get('averageRating', 0),
                'giTag': product.get('giTag', {}),
                'verificationStatus': product.get('verificationStatus'),
                'authenticityConfidence': product.get('authenticityConfidence')
            }
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(response_data)
        }
    
    except Exception as e:
        # Catch-all for unexpected errors
        print(f"Unexpected error in limited release detail: {str(e)}")
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
