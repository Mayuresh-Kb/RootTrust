"""
Tests for email service functionality.
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from backend.shared.email_service import EmailService, get_email_service
from backend.shared.email_templates import get_registration_confirmation_email


class TestEmailTemplates(unittest.TestCase):
    """Test email template generation."""
    
    def test_registration_confirmation_template_has_required_fields(self):
        """Test that registration confirmation template has all required fields."""
        email = get_registration_confirmation_email(
            user_email="test@example.com",
            first_name="John",
            user_id="test-user-id"
        )
        
        self.assertIn('subject', email)
        self.assertIn('html_body', email)
        self.assertIn('text_body', email)
    
    def test_registration_confirmation_includes_user_name(self):
        """Test that registration confirmation includes user's first name."""
        first_name = "Alice"
        email = get_registration_confirmation_email(
            user_email="alice@example.com",
            first_name=first_name,
            user_id="test-user-id"
        )
        
        self.assertIn(first_name, email['html_body'])
        self.assertIn(first_name, email['text_body'])
    
    def test_registration_confirmation_with_verification_link(self):
        """Test that verification link is included when provided."""
        verification_link = "https://example.com/verify?token=abc123"
        email = get_registration_confirmation_email(
            user_email="test@example.com",
            first_name="John",
            user_id="test-user-id",
            verification_link=verification_link
        )
        
        self.assertIn(verification_link, email['html_body'])
        self.assertIn(verification_link, email['text_body'])
    
    def test_registration_confirmation_without_verification_link(self):
        """Test that template works without verification link."""
        email = get_registration_confirmation_email(
            user_email="test@example.com",
            first_name="John",
            user_id="test-user-id",
            verification_link=None
        )
        
        # Should not contain verification button/link text
        self.assertNotIn('Verify Email Address', email['html_body'])


class TestEmailService(unittest.TestCase):
    """Test email service functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        os.environ['AWS_REGION'] = 'us-east-1'
        os.environ['SENDER_EMAIL'] = 'test@roottrust.com'
    
    @patch('shared.email_service.boto3.client')
    def test_email_service_initialization(self, mock_boto_client):
        """Test that EmailService initializes correctly."""
        service = EmailService()
        
        self.assertIsNotNone(service.ses_client)
        self.assertEqual(service.sender_email, 'test@roottrust.com')
        mock_boto_client.assert_called_once_with('ses', region_name='us-east-1')
    
    @patch('shared.email_service.boto3.client')
    def test_send_email_success(self, mock_boto_client):
        """Test successful email sending."""
        # Mock SES client
        mock_ses = MagicMock()
        mock_ses.send_email.return_value = {'MessageId': 'test-message-id'}
        mock_boto_client.return_value = mock_ses
        
        service = EmailService()
        result = service.send_email(
            recipient='recipient@example.com',
            subject='Test Subject',
            html_body='<p>Test HTML</p>',
            text_body='Test Text'
        )
        
        self.assertTrue(result['success'])
        self.assertEqual(result['message_id'], 'test-message-id')
        
        # Verify SES was called with correct parameters
        mock_ses.send_email.assert_called_once()
        call_args = mock_ses.send_email.call_args[1]
        self.assertEqual(call_args['Source'], 'test@roottrust.com')
        self.assertEqual(call_args['Destination']['ToAddresses'], ['recipient@example.com'])
        self.assertEqual(call_args['Message']['Subject']['Data'], 'Test Subject')
    
    @patch('shared.email_service.boto3.client')
    def test_send_email_handles_ses_error(self, mock_boto_client):
        """Test that email service handles SES errors gracefully."""
        from botocore.exceptions import ClientError
        
        # Mock SES client to raise error
        mock_ses = MagicMock()
        mock_ses.send_email.side_effect = ClientError(
            {'Error': {'Code': 'MessageRejected', 'Message': 'Email address not verified'}},
            'SendEmail'
        )
        mock_boto_client.return_value = mock_ses
        
        service = EmailService()
        result = service.send_email(
            recipient='invalid@example.com',
            subject='Test',
            html_body='<p>Test</p>',
            text_body='Test'
        )
        
        self.assertFalse(result['success'])
        self.assertEqual(result['error_code'], 'MessageRejected')
        self.assertIn('not verified', result['error_message'])
    
    @patch('shared.email_service.boto3.client')
    def test_send_registration_confirmation(self, mock_boto_client):
        """Test sending registration confirmation email."""
        # Mock SES client
        mock_ses = MagicMock()
        mock_ses.send_email.return_value = {'MessageId': 'test-message-id'}
        mock_boto_client.return_value = mock_ses
        
        service = EmailService()
        result = service.send_registration_confirmation(
            user_email='newuser@example.com',
            first_name='Jane',
            user_id='user-123'
        )
        
        self.assertTrue(result['success'])
        self.assertEqual(result['message_id'], 'test-message-id')
        
        # Verify email was sent
        mock_ses.send_email.assert_called_once()
        call_args = mock_ses.send_email.call_args[1]
        self.assertEqual(call_args['Destination']['ToAddresses'], ['newuser@example.com'])
        self.assertIn('Welcome', call_args['Message']['Subject']['Data'])
    
    @patch('shared.email_service.boto3.client')
    def test_get_email_service_singleton(self, mock_boto_client):
        """Test that get_email_service returns singleton instance."""
        # Reset singleton
        import shared.email_service
        shared.email_service._email_service = None
        
        service1 = get_email_service()
        service2 = get_email_service()
        
        self.assertIs(service1, service2)


class TestRegistrationEmailIntegration(unittest.TestCase):
    """Test email integration in registration handler."""
    
    @patch('backend.auth.register.get_email_service')
    @patch('backend.auth.register.put_item')
    @patch('backend.auth.register.get_item')
    def test_registration_sends_confirmation_email(self, mock_get_item, mock_put_item, mock_get_email_service):
        """Test that registration handler sends confirmation email."""
        # Mock database calls
        mock_get_item.return_value = None  # No existing user
        
        # Mock email service
        mock_email_service = MagicMock()
        mock_email_service.send_registration_confirmation.return_value = {
            'success': True,
            'message_id': 'test-message-id'
        }
        mock_get_email_service.return_value = mock_email_service
        
        # Import handler
        from backend.auth.register import handler
        
        # Create test event
        event = {
            'body': '{"email": "test@example.com", "password": "TestPass123!", "role": "consumer", "firstName": "John", "lastName": "Doe", "phone": "1234567890"}'
        }
        
        # Call handler
        response = handler(event, None)
        
        # Verify email service was called
        mock_get_email_service.assert_called_once()
        mock_email_service.send_registration_confirmation.assert_called_once()
        
        # Verify email parameters
        call_args = mock_email_service.send_registration_confirmation.call_args[1]
        self.assertEqual(call_args['user_email'], 'test@example.com')
        self.assertEqual(call_args['first_name'], 'John')
        self.assertIsNotNone(call_args['user_id'])
    
    @patch('backend.auth.register.get_email_service')
    @patch('backend.auth.register.put_item')
    @patch('backend.auth.register.get_item')
    def test_registration_succeeds_even_if_email_fails(self, mock_get_item, mock_put_item, mock_get_email_service):
        """Test that registration succeeds even if email sending fails."""
        # Mock database calls
        mock_get_item.return_value = None  # No existing user
        
        # Mock email service to fail
        mock_email_service = MagicMock()
        mock_email_service.send_registration_confirmation.return_value = {
            'success': False,
            'error_code': 'MessageRejected',
            'error_message': 'Email not verified'
        }
        mock_get_email_service.return_value = mock_email_service
        
        # Import handler
        from backend.auth.register import handler
        
        # Create test event
        event = {
            'body': '{"email": "test@example.com", "password": "TestPass123!", "role": "consumer", "firstName": "John", "lastName": "Doe", "phone": "1234567890"}'
        }
        
        # Call handler
        response = handler(event, None)
        
        # Verify registration still succeeded
        self.assertEqual(response['statusCode'], 201)
        import json
        body = json.loads(response['body'])
        self.assertTrue(body['success'])


if __name__ == '__main__':
    unittest.main()
