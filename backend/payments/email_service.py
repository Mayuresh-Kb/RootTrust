"""
Email service for sending emails via Amazon SES.
"""
import os
import boto3
from typing import Dict, Any, Optional
from botocore.exceptions import ClientError


class EmailService:
    """Service for sending emails via Amazon SES."""
    
    def __init__(self):
        """Initialize SES client."""
        self.ses_client = boto3.client('ses', region_name=os.environ.get('AWS_REGION', 'us-east-1'))
        self.sender_email = os.environ.get('SENDER_EMAIL', 'noreply@roottrust.com')
    
    def send_email(
        self,
        recipient: str,
        subject: str,
        html_body: str,
        text_body: str,
        sender: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send an email via Amazon SES.
        
        Args:
            recipient: Email address of the recipient
            subject: Email subject line
            html_body: HTML version of the email body
            text_body: Plain text version of the email body
            sender: Optional sender email (defaults to configured sender)
        
        Returns:
            Dictionary with success status and message_id or error
        
        Raises:
            ClientError: If SES API call fails
        """
        if sender is None:
            sender = self.sender_email
        
        try:
            response = self.ses_client.send_email(
                Source=sender,
                Destination={
                    'ToAddresses': [recipient]
                },
                Message={
                    'Subject': {
                        'Data': subject,
                        'Charset': 'UTF-8'
                    },
                    'Body': {
                        'Html': {
                            'Data': html_body,
                            'Charset': 'UTF-8'
                        },
                        'Text': {
                            'Data': text_body,
                            'Charset': 'UTF-8'
                        }
                    }
                }
            )
            
            return {
                'success': True,
                'message_id': response['MessageId']
            }
        
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            
            print(f"SES Error: {error_code} - {error_message}")
            
            return {
                'success': False,
                'error_code': error_code,
                'error_message': error_message
            }
        
        except Exception as e:
            print(f"Unexpected error sending email: {str(e)}")
            
            return {
                'success': False,
                'error_code': 'UNKNOWN_ERROR',
                'error_message': str(e)
            }
    
    def send_registration_confirmation(
        self,
        user_email: str,
        first_name: str,
        user_id: str,
        verification_link: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send registration confirmation email.
        
        Args:
            user_email: User's email address
            first_name: User's first name
            user_id: User's unique ID
            verification_link: Optional verification link
        
        Returns:
            Dictionary with success status and message_id or error
        """
        from email_templates import get_registration_confirmation_email
        
        email_content = get_registration_confirmation_email(
            user_email=user_email,
            first_name=first_name,
            user_id=user_id,
            verification_link=verification_link
        )
        
        return self.send_email(
            recipient=user_email,
            subject=email_content['subject'],
            html_body=email_content['html_body'],
            text_body=email_content['text_body']
        )
    def send_email_with_preference_check(
        self,
        recipient: str,
        email_type: str,
        subject: str,
        html_body: str,
        text_body: str,
        user_id: Optional[str] = None,
        sender: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send an email with user notification preference check.

        This method checks if the user has unsubscribed from marketing emails
        before sending. Marketing emails are skipped for unsubscribed users,
        but transactional emails are always sent.

        Args:
            recipient: Email address of the recipient
            email_type: Type of email - 'marketing' or 'transactional'
                       Marketing: newProducts, promotions, limitedReleases, farmerBonuses
                       Transactional: orderUpdates, reviewRequests, payment confirmations
            subject: Email subject line
            html_body: HTML version of the email body
            text_body: Plain text version of the email body
            user_id: Optional user ID for preference lookup
            sender: Optional sender email (defaults to configured sender)

        Returns:
            Dictionary with success status and message_id or reason for skipping

        Examples:
            >>> service.send_email_with_preference_check(
            ...     recipient='user@example.com',
            ...     email_type='marketing',
            ...     subject='New Products Available',
            ...     html_body='<p>Check out our new products</p>',
            ...     text_body='Check out our new products',
            ...     user_id='user-123'
            ... )
            {'success': False, 'reason': 'unsubscribed'}

            >>> service.send_email_with_preference_check(
            ...     recipient='user@example.com',
            ...     email_type='transactional',
            ...     subject='Order Confirmation',
            ...     html_body='<p>Your order is confirmed</p>',
            ...     text_body='Your order is confirmed',
            ...     user_id='user-123'
            ... )
            {'success': True, 'message_id': 'abc123'}
        """
        from database import get_item

        # Validate email_type
        if email_type not in ['marketing', 'transactional']:
            print(f"Invalid email_type: {email_type}. Must be 'marketing' or 'transactional'")
            return {
                'success': False,
                'error_code': 'INVALID_EMAIL_TYPE',
                'error_message': f"Invalid email_type: {email_type}"
            }

        # Check user notification preferences if user_id provided
        if user_id:
            try:
                user_pk = f"USER#{user_id}"
                user_sk = "PROFILE"
                user_item = get_item(user_pk, user_sk)

                if user_item:
                    # Get notification preferences
                    prefs = user_item.get('notificationPreferences', {})
                    unsubscribed_at = prefs.get('unsubscribedAt')

                    # If user has unsubscribed and this is a marketing email, skip
                    if unsubscribed_at and email_type == 'marketing':
                        print(f"Skipping marketing email to {recipient} - user unsubscribed at {unsubscribed_at}")
                        return {
                            'success': False,
                            'reason': 'unsubscribed',
                            'message': f'User unsubscribed from marketing emails at {unsubscribed_at}'
                        }
                else:
                    # User not found - send email anyway for safety (fail open)
                    print(f"User {user_id} not found in database - sending email anyway for safety")

            except Exception as e:
                # Database error - send email anyway for safety (fail open)
                print(f"Error checking notification preferences for user {user_id}: {str(e)}")
                print("Sending email anyway for safety (fail open)")

        # Send the email
        result = self.send_email(
            recipient=recipient,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
            sender=sender
        )

        # Log email sent event
        if result.get('success'):
            print(f"Email sent successfully to {recipient} - Type: {email_type}, MessageId: {result.get('message_id')}")
        else:
            print(f"Failed to send email to {recipient} - Type: {email_type}, Error: {result.get('error_code')}")

        return result



# Singleton instance
_email_service = None


def get_email_service() -> EmailService:
    """Get or create EmailService singleton instance."""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service
