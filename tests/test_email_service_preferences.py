"""
Tests for email service with notification preference checking.
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from backend.shared.email_service import EmailService


class TestEmailServiceWithPreferences(unittest.TestCase):
    """Test email service with notification preference checking."""
    
    def setUp(self):
        """Set up test fixtures."""
        os.environ['AWS_REGION'] = 'us-east-1'
        os.environ['SENDER_EMAIL'] = 'test@roottrust.com'
    
    @patch('shared.database.get_item')
    @patch('shared.email_service.boto3.client')
    def test_send_marketing_email_to_unsubscribed_user_skips_email(self, mock_boto_client, mock_get_item):
        """Test that marketing emails are skipped for unsubscribed users."""
        # Mock user with unsubscribedAt set
        mock_get_item.return_value = {
            'PK': 'USER#user-123',
            'SK': 'PROFILE',
            'userId': 'user-123',
            'email': 'user@example.com',
            'notificationPreferences': {
                'newProducts': False,
                'promotions': False,
                'unsubscribedAt': '2024-01-15T10:00:00Z'
            }
        }
        
        # Mock SES client (should not be called)
        mock_ses = MagicMock()
        mock_boto_client.return_value = mock_ses
        
        service = EmailService()
        result = service.send_email_with_preference_check(
            recipient='user@example.com',
            email_type='marketing',
            subject='New Products Available',
            html_body='<p>Check out our new products</p>',
            text_body='Check out our new products',
            user_id='user-123'
        )
        
        # Verify email was skipped
        self.assertFalse(result['success'])
        self.assertEqual(result['reason'], 'unsubscribed')
        self.assertIn('unsubscribed', result['message'])
        
        # Verify SES was NOT called
        mock_ses.send_email.assert_not_called()
        
        # Verify database was queried
        mock_get_item.assert_called_once_with('USER#user-123', 'PROFILE')
    
    @patch('shared.database.get_item')
    @patch('shared.email_service.boto3.client')
    def test_send_transactional_email_to_unsubscribed_user_sends_email(self, mock_boto_client, mock_get_item):
        """Test that transactional emails are sent even to unsubscribed users."""
        # Mock user with unsubscribedAt set
        mock_get_item.return_value = {
            'PK': 'USER#user-123',
            'SK': 'PROFILE',
            'userId': 'user-123',
            'email': 'user@example.com',
            'notificationPreferences': {
                'newProducts': False,
                'promotions': False,
                'orderUpdates': True,
                'unsubscribedAt': '2024-01-15T10:00:00Z'
            }
        }
        
        # Mock SES client
        mock_ses = MagicMock()
        mock_ses.send_email.return_value = {'MessageId': 'test-message-id'}
        mock_boto_client.return_value = mock_ses
        
        service = EmailService()
        result = service.send_email_with_preference_check(
            recipient='user@example.com',
            email_type='transactional',
            subject='Order Confirmation',
            html_body='<p>Your order is confirmed</p>',
            text_body='Your order is confirmed',
            user_id='user-123'
        )
        
        # Verify email was sent
        self.assertTrue(result['success'])
        self.assertEqual(result['message_id'], 'test-message-id')
        
        # Verify SES was called
        mock_ses.send_email.assert_called_once()
    
    @patch('shared.database.get_item')
    @patch('shared.email_service.boto3.client')
    def test_send_marketing_email_to_subscribed_user_sends_email(self, mock_boto_client, mock_get_item):
        """Test that marketing emails are sent to subscribed users."""
        # Mock user without unsubscribedAt
        mock_get_item.return_value = {
            'PK': 'USER#user-123',
            'SK': 'PROFILE',
            'userId': 'user-123',
            'email': 'user@example.com',
            'notificationPreferences': {
                'newProducts': True,
                'promotions': True,
                'orderUpdates': True
            }
        }
        
        # Mock SES client
        mock_ses = MagicMock()
        mock_ses.send_email.return_value = {'MessageId': 'test-message-id'}
        mock_boto_client.return_value = mock_ses
        
        service = EmailService()
        result = service.send_email_with_preference_check(
            recipient='user@example.com',
            email_type='marketing',
            subject='New Products Available',
            html_body='<p>Check out our new products</p>',
            text_body='Check out our new products',
            user_id='user-123'
        )
        
        # Verify email was sent
        self.assertTrue(result['success'])
        self.assertEqual(result['message_id'], 'test-message-id')
        
        # Verify SES was called
        mock_ses.send_email.assert_called_once()
    
    @patch('shared.database.get_item')
    @patch('shared.email_service.boto3.client')
    def test_send_email_when_user_not_found_sends_anyway(self, mock_boto_client, mock_get_item):
        """Test that email is sent when user is not found (fail open for safety)."""
        # Mock user not found
        mock_get_item.return_value = None
        
        # Mock SES client
        mock_ses = MagicMock()
        mock_ses.send_email.return_value = {'MessageId': 'test-message-id'}
        mock_boto_client.return_value = mock_ses
        
        service = EmailService()
        result = service.send_email_with_preference_check(
            recipient='user@example.com',
            email_type='marketing',
            subject='New Products Available',
            html_body='<p>Check out our new products</p>',
            text_body='Check out our new products',
            user_id='user-123'
        )
        
        # Verify email was sent (fail open)
        self.assertTrue(result['success'])
        self.assertEqual(result['message_id'], 'test-message-id')
        
        # Verify SES was called
        mock_ses.send_email.assert_called_once()
    
    @patch('shared.database.get_item')
    @patch('shared.email_service.boto3.client')
    def test_send_email_when_database_error_sends_anyway(self, mock_boto_client, mock_get_item):
        """Test that email is sent when database query fails (fail open for safety)."""
        # Mock database error
        mock_get_item.side_effect = Exception('Database connection error')
        
        # Mock SES client
        mock_ses = MagicMock()
        mock_ses.send_email.return_value = {'MessageId': 'test-message-id'}
        mock_boto_client.return_value = mock_ses
        
        service = EmailService()
        result = service.send_email_with_preference_check(
            recipient='user@example.com',
            email_type='marketing',
            subject='New Products Available',
            html_body='<p>Check out our new products</p>',
            text_body='Check out our new products',
            user_id='user-123'
        )
        
        # Verify email was sent (fail open)
        self.assertTrue(result['success'])
        self.assertEqual(result['message_id'], 'test-message-id')
        
        # Verify SES was called
        mock_ses.send_email.assert_called_once()
    
    @patch('shared.email_service.boto3.client')
    def test_send_email_without_user_id_sends_email(self, mock_boto_client):
        """Test that email is sent when no user_id is provided."""
        # Mock SES client
        mock_ses = MagicMock()
        mock_ses.send_email.return_value = {'MessageId': 'test-message-id'}
        mock_boto_client.return_value = mock_ses
        
        service = EmailService()
        result = service.send_email_with_preference_check(
            recipient='user@example.com',
            email_type='marketing',
            subject='New Products Available',
            html_body='<p>Check out our new products</p>',
            text_body='Check out our new products',
            user_id=None
        )
        
        # Verify email was sent
        self.assertTrue(result['success'])
        self.assertEqual(result['message_id'], 'test-message-id')
        
        # Verify SES was called
        mock_ses.send_email.assert_called_once()
    
    @patch('shared.email_service.boto3.client')
    def test_send_email_with_invalid_email_type_returns_error(self, mock_boto_client):
        """Test that invalid email_type returns an error."""
        # Mock SES client (should not be called)
        mock_ses = MagicMock()
        mock_boto_client.return_value = mock_ses
        
        service = EmailService()
        result = service.send_email_with_preference_check(
            recipient='user@example.com',
            email_type='invalid_type',
            subject='Test',
            html_body='<p>Test</p>',
            text_body='Test',
            user_id='user-123'
        )
        
        # Verify error was returned
        self.assertFalse(result['success'])
        self.assertEqual(result['error_code'], 'INVALID_EMAIL_TYPE')
        self.assertIn('invalid_type', result['error_message'])
        
        # Verify SES was NOT called
        mock_ses.send_email.assert_not_called()
    
    @patch('shared.database.get_item')
    @patch('shared.email_service.boto3.client')
    def test_send_email_handles_ses_error(self, mock_boto_client, mock_get_item):
        """Test that SES errors are handled properly."""
        from botocore.exceptions import ClientError
        
        # Mock user without unsubscribedAt
        mock_get_item.return_value = {
            'PK': 'USER#user-123',
            'SK': 'PROFILE',
            'userId': 'user-123',
            'email': 'user@example.com',
            'notificationPreferences': {
                'newProducts': True
            }
        }
        
        # Mock SES client to raise error
        mock_ses = MagicMock()
        mock_ses.send_email.side_effect = ClientError(
            {'Error': {'Code': 'MessageRejected', 'Message': 'Email address not verified'}},
            'SendEmail'
        )
        mock_boto_client.return_value = mock_ses
        
        service = EmailService()
        result = service.send_email_with_preference_check(
            recipient='invalid@example.com',
            email_type='marketing',
            subject='Test',
            html_body='<p>Test</p>',
            text_body='Test',
            user_id='user-123'
        )
        
        # Verify error was returned
        self.assertFalse(result['success'])
        self.assertEqual(result['error_code'], 'MessageRejected')
    
    @patch('shared.database.get_item')
    @patch('shared.email_service.boto3.client')
    def test_send_email_with_custom_sender(self, mock_boto_client, mock_get_item):
        """Test that custom sender email is used when provided."""
        # Mock user without unsubscribedAt
        mock_get_item.return_value = {
            'PK': 'USER#user-123',
            'SK': 'PROFILE',
            'userId': 'user-123',
            'email': 'user@example.com',
            'notificationPreferences': {
                'newProducts': True
            }
        }
        
        # Mock SES client
        mock_ses = MagicMock()
        mock_ses.send_email.return_value = {'MessageId': 'test-message-id'}
        mock_boto_client.return_value = mock_ses
        
        service = EmailService()
        custom_sender = 'custom@roottrust.com'
        result = service.send_email_with_preference_check(
            recipient='user@example.com',
            email_type='transactional',
            subject='Test',
            html_body='<p>Test</p>',
            text_body='Test',
            user_id='user-123',
            sender=custom_sender
        )
        
        # Verify email was sent
        self.assertTrue(result['success'])
        
        # Verify SES was called with custom sender
        call_args = mock_ses.send_email.call_args[1]
        self.assertEqual(call_args['Source'], custom_sender)
    
    @patch('shared.database.get_item')
    @patch('shared.email_service.boto3.client')
    def test_send_email_logs_decisions(self, mock_boto_client, mock_get_item):
        """Test that email sending decisions are logged."""
        # Mock user with unsubscribedAt
        mock_get_item.return_value = {
            'PK': 'USER#user-123',
            'SK': 'PROFILE',
            'userId': 'user-123',
            'email': 'user@example.com',
            'notificationPreferences': {
                'unsubscribedAt': '2024-01-15T10:00:00Z'
            }
        }
        
        # Mock SES client
        mock_ses = MagicMock()
        mock_boto_client.return_value = mock_ses
        
        service = EmailService()
        
        # Test with print capture
        with patch('builtins.print') as mock_print:
            result = service.send_email_with_preference_check(
                recipient='user@example.com',
                email_type='marketing',
                subject='Test',
                html_body='<p>Test</p>',
                text_body='Test',
                user_id='user-123'
            )
            
            # Verify logging occurred
            mock_print.assert_called()
            # Check that unsubscribe message was logged
            log_calls = [str(call) for call in mock_print.call_args_list]
            self.assertTrue(any('unsubscribed' in str(call) for call in log_calls))


class TestEmailServicePreferencesEdgeCases(unittest.TestCase):
    """Test edge cases for email service with preferences."""
    
    def setUp(self):
        """Set up test fixtures."""
        os.environ['AWS_REGION'] = 'us-east-1'
        os.environ['SENDER_EMAIL'] = 'test@roottrust.com'
    
    @patch('shared.database.get_item')
    @patch('shared.email_service.boto3.client')
    def test_user_with_empty_notification_preferences_sends_email(self, mock_boto_client, mock_get_item):
        """Test that email is sent when user has empty notification preferences."""
        # Mock user with empty preferences
        mock_get_item.return_value = {
            'PK': 'USER#user-123',
            'SK': 'PROFILE',
            'userId': 'user-123',
            'email': 'user@example.com',
            'notificationPreferences': {}
        }
        
        # Mock SES client
        mock_ses = MagicMock()
        mock_ses.send_email.return_value = {'MessageId': 'test-message-id'}
        mock_boto_client.return_value = mock_ses
        
        service = EmailService()
        result = service.send_email_with_preference_check(
            recipient='user@example.com',
            email_type='marketing',
            subject='Test',
            html_body='<p>Test</p>',
            text_body='Test',
            user_id='user-123'
        )
        
        # Verify email was sent (no unsubscribedAt means subscribed)
        self.assertTrue(result['success'])
    
    @patch('shared.database.get_item')
    @patch('shared.email_service.boto3.client')
    def test_user_without_notification_preferences_field_sends_email(self, mock_boto_client, mock_get_item):
        """Test that email is sent when user has no notificationPreferences field."""
        # Mock user without notificationPreferences field
        mock_get_item.return_value = {
            'PK': 'USER#user-123',
            'SK': 'PROFILE',
            'userId': 'user-123',
            'email': 'user@example.com'
        }
        
        # Mock SES client
        mock_ses = MagicMock()
        mock_ses.send_email.return_value = {'MessageId': 'test-message-id'}
        mock_boto_client.return_value = mock_ses
        
        service = EmailService()
        result = service.send_email_with_preference_check(
            recipient='user@example.com',
            email_type='marketing',
            subject='Test',
            html_body='<p>Test</p>',
            text_body='Test',
            user_id='user-123'
        )
        
        # Verify email was sent (no preferences means subscribed)
        self.assertTrue(result['success'])


if __name__ == '__main__':
    unittest.main()
