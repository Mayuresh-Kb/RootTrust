"""
Notification preference management Lambda handler for RootTrust marketplace.
Handles PUT /notifications/preferences endpoint for users to manage notification settings.
"""
import json
import os
from datetime import datetime
from typing import Dict, Any

# Import shared modules
import sys
sys.path.append('/opt/python')

try:
    # Lambda environment
    from models import NotificationPreferences
    from database import get_item, update_item
    from auth import get_user_from_token
    from exceptions import ValidationError, ResourceNotFoundError
except ImportError:
    # Local testing environment
    from models import NotificationPreferences
    from database import get_item, update_item
    from auth import get_user_from_token
    from exceptions import ValidationError, ResourceNotFoundError


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for notification preference update endpoint.
    
    Validates JWT token, accepts notification preferences object,
    updates user's notificationPreferences in DynamoDB, and returns updated preferences.
    
    Args:
        event: API Gateway event
        context: Lambda context
        
    Returns:
        API Gateway response with updated notification preferences
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
        
        # Validate notification preferences using Pydantic model
        try:
            preferences = NotificationPreferences(**body)
        except Exception as e:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'VALIDATION_ERROR',
                        'message': 'Invalid notification preferences',
                        'details': str(e)
                    }
                })
            }
        
        # Query user from DynamoDB to verify existence
        user_pk = f"USER#{user_id}"
        user_sk = "PROFILE"
        
        try:
            user_item = get_item(user_pk, user_sk)
        except Exception as e:
            print(f"Error querying user: {str(e)}")
            return {
                'statusCode': 503,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'SERVICE_UNAVAILABLE',
                        'message': 'Failed to query user',
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
                        'message': f'User with ID {user_id} not found'
                    }
                })
            }
        
        # Prepare update expression for notification preferences
        now = datetime.utcnow()
        preferences_dict = preferences.dict()
        
        update_expression = 'SET notificationPreferences = :prefs, updatedAt = :updated'
        expression_attribute_values = {
            ':prefs': preferences_dict,
            ':updated': now.isoformat()
        }
        
        # Update user's notification preferences in DynamoDB
        try:
            updated_item = update_item(
                pk=user_pk,
                sk=user_sk,
                update_expression=update_expression,
                expression_attribute_values=expression_attribute_values
            )
        except Exception as e:
            print(f"Error updating notification preferences: {str(e)}")
            return {
                'statusCode': 503,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'SERVICE_UNAVAILABLE',
                        'message': 'Failed to update notification preferences',
                        'details': str(e)
                    }
                })
            }
        
        # Extract updated preferences from response
        updated_preferences = updated_item.get('notificationPreferences', preferences_dict)
        
        # Return success response with updated preferences
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'message': 'Notification preferences updated successfully',
                'preferences': updated_preferences
            })
        }
    
    except Exception as e:
        # Catch-all for unexpected errors
        print(f"Unexpected error in notification preference update: {str(e)}")
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
