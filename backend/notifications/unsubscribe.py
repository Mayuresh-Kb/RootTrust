"""
Unsubscribe Lambda handler for RootTrust marketplace.
Handles POST /notifications/unsubscribe endpoint for users to unsubscribe from marketing emails.
This is a public endpoint (no authentication required) for email unsubscribe links.
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
    from database import get_item, update_item, scan
    from exceptions import ValidationError, ResourceNotFoundError
except ImportError:
    # Local testing environment
    from database import get_item, update_item, scan
    from exceptions import ValidationError, ResourceNotFoundError


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for unsubscribe endpoint.
    
    Accepts email or userId, sets user.notificationPreferences.unsubscribedAt = now,
    disables all marketing notifications, and keeps transactional notifications enabled.
    
    This is a public endpoint (no authentication required) for email unsubscribe links.
    
    Args:
        event: API Gateway event
        context: Lambda context
        
    Returns:
        API Gateway response with unsubscribe confirmation
    """
    try:
        # Parse request body
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
        
        # Extract email or userId
        email = body.get('email')
        user_id = body.get('userId')
        
        if not email and not user_id:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'VALIDATION_ERROR',
                        'message': 'Either email or userId is required'
                    }
                })
            }
        
        # Find user by email or userId
        user_item = None
        
        if user_id:
            # Query by userId directly
            user_pk = f"USER#{user_id}"
            user_sk = "PROFILE"
            
            try:
                user_item = get_item(user_pk, user_sk)
            except Exception as e:
                print(f"Error querying user by userId: {str(e)}")
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
        elif email:
            # Scan for user by email (not ideal but necessary for public endpoint)
            try:
                from boto3.dynamodb.conditions import Attr
                result = scan(
                    filter_expression=Attr('email').eq(email) & Attr('SK').eq('PROFILE')
                )
                items = result.get('Items', [])
                if items:
                    user_item = items[0]
                    user_id = user_item.get('userId')
            except Exception as e:
                print(f"Error scanning for user by email: {str(e)}")
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
        
        # Return success even if user not found (for privacy - don't reveal if email exists)
        if not user_item:
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'message': 'Unsubscribe request processed successfully',
                    'status': 'unsubscribed'
                })
            }
        
        # Prepare update expression to disable marketing notifications
        now = datetime.utcnow()
        
        # Disable all marketing notifications, keep transactional ones enabled
        marketing_disabled_prefs = {
            'newProducts': False,
            'promotions': False,
            'limitedReleases': False,
            'farmerBonuses': False,
            # Keep transactional notifications enabled
            'orderUpdates': True,
            'reviewRequests': True
        }
        
        # Check if already unsubscribed
        existing_prefs = user_item.get('notificationPreferences', {})
        unsubscribed_at = existing_prefs.get('unsubscribedAt')
        
        # Update notification preferences with unsubscribedAt timestamp
        marketing_disabled_prefs['unsubscribedAt'] = now.isoformat()
        
        update_expression = 'SET notificationPreferences = :prefs, updatedAt = :updated'
        expression_attribute_values = {
            ':prefs': marketing_disabled_prefs,
            ':updated': now.isoformat()
        }
        
        # Update user's notification preferences in DynamoDB
        user_pk = f"USER#{user_id}"
        user_sk = "PROFILE"
        
        try:
            updated_item = update_item(
                pk=user_pk,
                sk=user_sk,
                update_expression=update_expression,
                expression_attribute_values=expression_attribute_values
            )
        except Exception as e:
            print(f"Error updating notification preferences: {str(e)}")
            # Return success anyway for idempotency
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'message': 'Unsubscribe request processed successfully',
                    'status': 'unsubscribed'
                })
            }
        
        # Return success response
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'message': 'You have been successfully unsubscribed from marketing emails',
                'status': 'unsubscribed',
                'details': {
                    'marketingEmailsDisabled': True,
                    'transactionalEmailsEnabled': True,
                    'unsubscribedAt': now.isoformat()
                }
            })
        }
    
    except Exception as e:
        # Catch-all for unexpected errors
        print(f"Unexpected error in unsubscribe handler: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Return success for privacy (don't reveal errors)
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'message': 'Unsubscribe request processed successfully',
                'status': 'unsubscribed'
            })
        }
