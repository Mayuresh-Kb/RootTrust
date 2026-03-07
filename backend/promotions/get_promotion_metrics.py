"""
Promotion metrics retrieval Lambda handler for RootTrust marketplace.
Handles GET /promotions/{promotionId}/metrics endpoint for farmers to view promotion performance.
"""
import json
import os
from typing import Dict, Any

# Import shared modules
import sys
sys.path.append('/opt/python')

from database import get_item
from auth import get_user_from_token
from constants import UserRole
from exceptions import (
    AuthenticationError, AuthorizationError,
    ResourceNotFoundError, ServiceUnavailableError
)


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for promotion metrics endpoint.
    
    Validates JWT token, farmer role authorization, and returns promotion metrics.
    
    Args:
        event: API Gateway event
        context: Lambda context
        
    Returns:
        API Gateway response with promotion metrics (views, clicks, conversions, spent)
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
                        'message': 'Only farmers can view promotion metrics'
                    }
                })
            }
        
        # Extract promotionId from path parameters
        path_params = event.get('pathParameters', {})
        promotion_id = path_params.get('promotionId')
        
        if not promotion_id:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'INVALID_REQUEST',
                        'message': 'promotionId is required'
                    }
                })
            }
        
        # Query promotion record
        try:
            promotion = get_item(f"PROMOTION#{promotion_id}", "METADATA")
            
            if not promotion:
                return {
                    'statusCode': 404,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({
                        'error': {
                            'code': 'NOT_FOUND',
                            'message': 'Promotion not found'
                        }
                    })
                }
            
            # Verify farmer owns the promotion
            if promotion.get('farmerId') != user_id:
                return {
                    'statusCode': 403,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({
                        'error': {
                            'code': 'FORBIDDEN',
                            'message': 'You can only view metrics for your own promotions'
                        }
                    })
                }
        
        except Exception as e:
            print(f"Error querying promotion: {str(e)}")
            return {
                'statusCode': 503,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'SERVICE_UNAVAILABLE',
                        'message': 'Failed to retrieve promotion',
                        'details': str(e)
                    }
                })
            }
        
        # Extract metrics from promotion record
        metrics = promotion.get('metrics', {
            'views': 0,
            'clicks': 0,
            'conversions': 0,
            'spent': 0.0
        })
        
        # Return metrics response
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'promotionId': promotion_id,
                'metrics': {
                    'views': metrics.get('views', 0),
                    'clicks': metrics.get('clicks', 0),
                    'conversions': metrics.get('conversions', 0),
                    'spent': metrics.get('spent', 0.0)
                }
            })
        }
    
    except Exception as e:
        # Catch-all for unexpected errors
        print(f"Unexpected error in promotion metrics retrieval: {str(e)}")
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
