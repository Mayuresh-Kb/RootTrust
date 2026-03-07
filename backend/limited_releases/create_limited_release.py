"""
Limited release creation Lambda handler for RootTrust marketplace.
Handles POST /limited-releases endpoint for farmers to create limited releases.
"""
import json
import os
import uuid
import boto3
from datetime import datetime, timedelta
from typing import Dict, Any, List

# Import shared modules
import sys
sys.path.append('/opt/python')

from models import LimitedRelease
from validators import LimitedReleaseCreateRequest, validate_request_body
from database import get_item, put_item, query
from auth import get_user_from_token
from constants import UserRole, LimitedReleaseStatus
from exceptions import (
    ValidationError, AuthenticationError, AuthorizationError,
    ResourceNotFoundError, ConflictError, ServiceUnavailableError
)
from email_service import get_email_service


def get_subscribers_for_limited_releases() -> List[Dict[str, Any]]:
    """
    Query all consumers who have opted in to limited release notifications.
    
    Returns:
        List of user records with email and notification preferences
    """
    try:
        # Query all users with consumer role
        from boto3.dynamodb.conditions import Key
        
        result = query(
            key_condition_expression=Key('GSI2PK').eq(f'ROLE#{UserRole.CONSUMER.value}'),
            index_name='GSI2'
        )
        
        # Filter for users with limitedReleases notification enabled
        subscribers = []
        for user in result.get('Items', []):
            notification_prefs = user.get('notificationPreferences', {})
            if notification_prefs.get('limitedReleases', True):
                subscribers.append(user)
        
        return subscribers
    
    except Exception as e:
        print(f"Error querying subscribers: {str(e)}")
        return []


def send_limited_release_notifications(
    subscribers: List[Dict[str, Any]],
    release_name: str,
    product_name: str,
    quantity_limit: int,
    duration: int,
    farmer_name: str
) -> int:
    """
    Send email notifications to subscribers about new limited release.
    
    Args:
        subscribers: List of subscriber user records
        release_name: Name of the limited release
        product_name: Name of the product
        quantity_limit: Quantity limit for the release
        duration: Duration in days
        farmer_name: Name of the farmer
        
    Returns:
        Number of emails sent successfully
    """
    email_service = get_email_service()
    sent_count = 0
    
    for subscriber in subscribers:
        try:
            email = subscriber.get('email')
            first_name = subscriber.get('firstName', 'Valued Customer')
            
            if not email:
                continue
            
            # Construct email content
            subject = f"🌟 New Limited Release: {release_name}"
            
            html_body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #2c5f2d;">Exclusive Limited Release Alert!</h2>
                    
                    <p>Hi {first_name},</p>
                    
                    <p>We're excited to announce a new limited release offering from {farmer_name}:</p>
                    
                    <div style="background-color: #f5f5f5; padding: 20px; border-radius: 8px; margin: 20px 0;">
                        <h3 style="margin-top: 0; color: #2c5f2d;">{release_name}</h3>
                        <p><strong>Product:</strong> {product_name}</p>
                        <p><strong>Limited Quantity:</strong> Only {quantity_limit} units available</p>
                        <p><strong>Duration:</strong> Available for {duration} days only</p>
                    </div>
                    
                    <p style="color: #d9534f; font-weight: bold;">⏰ Don't miss out! This exclusive offering won't last long.</p>
                    
                    <p>Visit RootTrust Marketplace now to secure your order before it's gone!</p>
                    
                    <div style="margin: 30px 0;">
                        <a href="#" style="background-color: #2c5f2d; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block;">
                            View Limited Release
                        </a>
                    </div>
                    
                    <p style="color: #666; font-size: 12px; margin-top: 30px;">
                        You're receiving this email because you've opted in to limited release notifications. 
                        You can update your preferences in your account settings.
                    </p>
                </div>
            </body>
            </html>
            """
            
            text_body = f"""
            Exclusive Limited Release Alert!
            
            Hi {first_name},
            
            We're excited to announce a new limited release offering from {farmer_name}:
            
            {release_name}
            
            Product: {product_name}
            Limited Quantity: Only {quantity_limit} units available
            Duration: Available for {duration} days only
            
            Don't miss out! This exclusive offering won't last long.
            
            Visit RootTrust Marketplace now to secure your order before it's gone!
            
            ---
            You're receiving this email because you've opted in to limited release notifications.
            You can update your preferences in your account settings.
            """
            
            result = email_service.send_email(
                recipient=email,
                subject=subject,
                html_body=html_body,
                text_body=text_body
            )
            
            if result.get('success'):
                sent_count += 1
        
        except Exception as e:
            print(f"Error sending email to {subscriber.get('email')}: {str(e)}")
            continue
    
    return sent_count


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for limited release creation endpoint.
    
    Validates JWT token, farmer role, and creates limited release record.
    Sends email notifications to subscribers.
    
    Args:
        event: API Gateway event
        context: Lambda context
        
    Returns:
        API Gateway response with releaseId, startDate, endDate, and status
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
                        'message': 'Only farmers can create limited releases'
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
        
        # Validate limited release data
        try:
            release_request = validate_request_body(body, LimitedReleaseCreateRequest)
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
        
        # Query product to verify it exists and belongs to the farmer
        try:
            product = get_item(f"PRODUCT#{release_request.productId}", "METADATA")
            if not product:
                return {
                    'statusCode': 404,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({
                        'error': {
                            'code': 'NOT_FOUND',
                            'message': 'Product not found'
                        }
                    })
                }
            
            # Verify farmer owns the product
            if product.get('farmerId') != user_id:
                return {
                    'statusCode': 403,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({
                        'error': {
                            'code': 'FORBIDDEN',
                            'message': 'You can only create limited releases for your own products'
                        }
                    })
                }
        
        except Exception as e:
            print(f"Error querying product: {str(e)}")
            return {
                'statusCode': 503,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'SERVICE_UNAVAILABLE',
                        'message': 'Failed to verify product',
                        'details': str(e)
                    }
                })
            }
        
        # Get farmer profile for notifications
        try:
            farmer = get_item(f"USER#{user_id}", "PROFILE")
            farmer_name = f"{farmer.get('firstName', '')} {farmer.get('lastName', '')}".strip()
            if not farmer_name:
                farmer_profile = farmer.get('farmerProfile', {})
                farmer_name = farmer_profile.get('farmName', 'A Farmer')
        except Exception as e:
            print(f"Error querying farmer profile: {str(e)}")
            farmer_name = "A Farmer"
        
        # Generate unique release ID
        release_id = str(uuid.uuid4())
        
        # Calculate start and end dates
        now = datetime.utcnow()
        start_date = now
        end_date = now + timedelta(days=release_request.duration)
        
        # Create LimitedRelease model instance
        limited_release = LimitedRelease(
            releaseId=release_id,
            farmerId=user_id,
            productId=release_request.productId,
            releaseName=release_request.releaseName,
            quantityLimit=release_request.quantityLimit,
            quantityRemaining=release_request.quantityLimit,
            duration=release_request.duration,
            startDate=start_date,
            endDate=end_date,
            status=LimitedReleaseStatus.ACTIVE,
            subscriberNotificationsSent=False,
            createdAt=now
        )
        
        # Convert to DynamoDB item format
        release_dict = limited_release.dict()
        
        # Convert datetime objects to ISO strings for DynamoDB
        release_dict['startDate'] = release_dict['startDate'].isoformat()
        release_dict['endDate'] = release_dict['endDate'].isoformat()
        release_dict['createdAt'] = release_dict['createdAt'].isoformat()
        
        # Convert enums to strings
        release_dict['status'] = release_dict['status'].value if hasattr(release_dict['status'], 'value') else release_dict['status']
        
        # Store limited release in DynamoDB
        try:
            put_item(release_dict)
        except Exception as e:
            print(f"Error storing limited release in DynamoDB: {str(e)}")
            return {
                'statusCode': 503,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'SERVICE_UNAVAILABLE',
                        'message': 'Failed to create limited release',
                        'details': str(e)
                    }
                })
            }
        
        # Query subscribers and send notifications
        try:
            subscribers = get_subscribers_for_limited_releases()
            product_name = product.get('name', 'Product')
            
            sent_count = send_limited_release_notifications(
                subscribers=subscribers,
                release_name=release_request.releaseName,
                product_name=product_name,
                quantity_limit=release_request.quantityLimit,
                duration=release_request.duration,
                farmer_name=farmer_name
            )
            
            print(f"Sent {sent_count} limited release notifications to subscribers")
            
            # Update the release to mark notifications as sent
            from database import update_item
            update_item(
                pk=f"LIMITED_RELEASE#{release_id}",
                sk="METADATA",
                update_expression="SET subscriberNotificationsSent = :sent",
                expression_attribute_values={
                    ':sent': True
                }
            )
        
        except Exception as e:
            print(f"Error sending notifications: {str(e)}")
            # Don't fail the request if notifications fail
        
        # Return success response
        return {
            'statusCode': 201,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'releaseId': release_id,
                'startDate': start_date.isoformat(),
                'endDate': end_date.isoformat(),
                'status': LimitedReleaseStatus.ACTIVE.value,
                'message': 'Limited release created successfully'
            })
        }
    
    except Exception as e:
        # Catch-all for unexpected errors
        print(f"Unexpected error in limited release creation: {str(e)}")
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
