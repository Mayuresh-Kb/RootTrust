"""
Unit tests for limited release expiry check Lambda handler.
Tests the scheduled function that checks for expired limited releases
and updates their status.
"""
import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend', 'limited_releases'))

from limited_releases.expiry_check import (
    handler,
    check_expired_releases,
    update_release_status
)


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Set up environment variables for tests."""
    monkeypatch.setenv('DYNAMODB_TABLE_NAME', 'test-table')
    monkeypatch.setenv('AWS_REGION', 'us-east-1')


@pytest.fixture
def sample_expired_release():
    """Create a sample expired limited release."""
    now = datetime.utcnow()
    past_date = now - timedelta(hours=1)
    
    return {
        'PK': 'LIMITED_RELEASE#test-release-1',
        'SK': 'METADATA',
        'EntityType': 'LimitedRelease',
        'releaseId': 'test-release-1',
        'farmerId': 'farmer-123',
        'productId': 'product-456',
        'releaseName': 'Summer Harvest Special',
        'quantityLimit': 100,
        'quantityRemaining': 25,
        'duration': 7,
        'status': 'active',
        'startDate': (now - timedelta(days=7)).isoformat(),
        'endDate': past_date.isoformat(),
        'subscriberNotificationsSent': True,
        'createdAt': (now - timedelta(days=7)).isoformat(),
        'GSI2PK': 'FARMER#farmer-123',
        'GSI2SK': f"RELEASE#{(now - timedelta(days=7)).isoformat()}",
        'GSI3PK': 'STATUS#active',
        'GSI3SK': f"RELEASE#{past_date.isoformat()}"
    }


@pytest.fixture
def sample_active_release():
    """Create a sample active (not expired) limited release."""
    now = datetime.utcnow()
    future_date = now + timedelta(days=2)
    
    return {
        'PK': 'LIMITED_RELEASE#test-release-2',
        'SK': 'METADATA',
        'EntityType': 'LimitedRelease',
        'releaseId': 'test-release-2',
        'farmerId': 'farmer-789',
        'productId': 'product-101',
        'releaseName': 'Winter Collection',
        'quantityLimit': 50,
        'quantityRemaining': 30,
        'duration': 5,
        'status': 'active',
        'startDate': (now - timedelta(days=3)).isoformat(),
        'endDate': future_date.isoformat(),
        'subscriberNotificationsSent': True,
        'createdAt': (now - timedelta(days=3)).isoformat(),
        'GSI2PK': 'FARMER#farmer-789',
        'GSI2SK': f"RELEASE#{(now - timedelta(days=3)).isoformat()}",
        'GSI3PK': 'STATUS#active',
        'GSI3SK': f"RELEASE#{future_date.isoformat()}"
    }


@pytest.fixture
def sample_sold_out_release():
    """Create a sample sold out limited release."""
    now = datetime.utcnow()
    future_date = now + timedelta(days=1)
    
    return {
        'PK': 'LIMITED_RELEASE#test-release-3',
        'SK': 'METADATA',
        'EntityType': 'LimitedRelease',
        'releaseId': 'test-release-3',
        'farmerId': 'farmer-456',
        'productId': 'product-789',
        'releaseName': 'Flash Sale',
        'quantityLimit': 20,
        'quantityRemaining': 0,
        'duration': 3,
        'status': 'sold_out',
        'startDate': (now - timedelta(days=2)).isoformat(),
        'endDate': future_date.isoformat(),
        'subscriberNotificationsSent': True,
        'createdAt': (now - timedelta(days=2)).isoformat(),
        'GSI2PK': 'FARMER#farmer-456',
        'GSI2SK': f"RELEASE#{(now - timedelta(days=2)).isoformat()}",
        'GSI3PK': 'STATUS#sold_out',
        'GSI3SK': f"RELEASE#{future_date.isoformat()}"
    }


class TestCheckExpiredReleases:
    """Tests for check_expired_releases function."""
    
    @patch('limited_releases.expiry_check.query')
    def test_finds_expired_releases(self, mock_query, sample_expired_release, sample_active_release):
        """Test that expired limited releases are correctly identified."""
        mock_query.return_value = {
            'Items': [sample_expired_release, sample_active_release]
        }
        
        expired = check_expired_releases()
        
        assert len(expired) == 1
        assert expired[0]['releaseId'] == 'test-release-1'
        mock_query.assert_called_once()
    
    @patch('limited_releases.expiry_check.query')
    def test_no_expired_releases(self, mock_query, sample_active_release):
        """Test when no limited releases are expired."""
        mock_query.return_value = {
            'Items': [sample_active_release]
        }
        
        expired = check_expired_releases()
        
        assert len(expired) == 0
    
    @patch('limited_releases.expiry_check.query')
    def test_empty_releases_list(self, mock_query):
        """Test when there are no active limited releases."""
        mock_query.return_value = {
            'Items': []
        }
        
        expired = check_expired_releases()
        
        assert len(expired) == 0
    
    @patch('limited_releases.expiry_check.query')
    def test_handles_invalid_date_format(self, mock_query):
        """Test handling of releases with invalid date formats."""
        invalid_release = {
            'releaseId': 'test-release-invalid',
            'endDate': 'invalid-date-format'
        }
        
        mock_query.return_value = {
            'Items': [invalid_release]
        }
        
        expired = check_expired_releases()
        
        # Should skip invalid release and return empty list
        assert len(expired) == 0
    
    @patch('limited_releases.expiry_check.query')
    def test_multiple_expired_releases(self, mock_query):
        """Test when multiple releases are expired."""
        now = datetime.utcnow()
        past_date_1 = now - timedelta(hours=2)
        past_date_2 = now - timedelta(hours=5)
        
        expired_1 = {
            'releaseId': 'test-release-1',
            'endDate': past_date_1.isoformat()
        }
        expired_2 = {
            'releaseId': 'test-release-2',
            'endDate': past_date_2.isoformat()
        }
        
        mock_query.return_value = {
            'Items': [expired_1, expired_2]
        }
        
        expired = check_expired_releases()
        
        assert len(expired) == 2
    
    @patch('limited_releases.expiry_check.query')
    def test_query_uses_correct_gsi(self, mock_query):
        """Test that query uses GSI3 with correct status."""
        mock_query.return_value = {'Items': []}
        
        check_expired_releases()
        
        # Verify query was called with correct parameters
        call_args = mock_query.call_args
        assert call_args[1]['index_name'] == 'GSI3'
        assert call_args[1]['scan_index_forward'] is True


class TestUpdateReleaseStatus:
    """Tests for update_release_status function."""
    
    @patch('limited_releases.expiry_check.update_item')
    def test_successful_status_update(self, mock_update_item):
        """Test successful release status update."""
        mock_update_item.return_value = True
        
        result = update_release_status('test-release-1')
        
        assert result is True
        mock_update_item.assert_called_once()
        
        # Verify the update parameters
        call_args = mock_update_item.call_args
        assert call_args[1]['pk'] == 'LIMITED_RELEASE#test-release-1'
        assert call_args[1]['sk'] == 'METADATA'
        assert 'expired' in str(call_args[1]['expression_attribute_values'])
    
    @patch('limited_releases.expiry_check.update_item')
    def test_failed_status_update(self, mock_update_item):
        """Test handling of failed status update."""
        mock_update_item.side_effect = Exception('DynamoDB error')
        
        result = update_release_status('test-release-1')
        
        assert result is False
    
    @patch('limited_releases.expiry_check.update_item')
    def test_updates_gsi3pk_for_delisting(self, mock_update_item):
        """Test that GSI3PK is updated to remove from active listings."""
        mock_update_item.return_value = True
        
        update_release_status('test-release-1')
        
        call_args = mock_update_item.call_args
        expression_values = call_args[1]['expression_attribute_values']
        
        # Verify GSI3PK is updated to STATUS#expired
        assert ':gsi3pk' in expression_values
        assert expression_values[':gsi3pk'] == 'STATUS#expired'


class TestHandler:
    """Tests for the main Lambda handler."""
    
    @patch('limited_releases.expiry_check.update_release_status')
    @patch('limited_releases.expiry_check.check_expired_releases')
    def test_no_expired_releases(
        self,
        mock_check_expired,
        mock_update_status,
        mock_env_vars
    ):
        """Test handler when no releases are expired."""
        mock_check_expired.return_value = []
        
        event = {}
        context = {}
        
        response = handler(event, context)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['processed'] == 0
        assert body['message'] == 'No expired limited releases found'
        
        mock_update_status.assert_not_called()
    
    @patch('limited_releases.expiry_check.update_release_status')
    @patch('limited_releases.expiry_check.check_expired_releases')
    def test_successful_processing(
        self,
        mock_check_expired,
        mock_update_status,
        mock_env_vars,
        sample_expired_release
    ):
        """Test successful processing of expired releases."""
        mock_check_expired.return_value = [sample_expired_release]
        mock_update_status.return_value = True
        
        event = {}
        context = {}
        
        response = handler(event, context)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['totalExpired'] == 1
        assert body['statusUpdated'] == 1
        assert len(body['failedUpdates']) == 0
        
        mock_update_status.assert_called_once_with('test-release-1')
    
    @patch('limited_releases.expiry_check.update_release_status')
    @patch('limited_releases.expiry_check.check_expired_releases')
    def test_partial_failures(
        self,
        mock_check_expired,
        mock_update_status,
        mock_env_vars,
        sample_expired_release
    ):
        """Test handling of partial failures in processing."""
        # Create two expired releases
        release1 = sample_expired_release.copy()
        release2 = sample_expired_release.copy()
        release2['releaseId'] = 'test-release-2'
        release2['PK'] = 'LIMITED_RELEASE#test-release-2'
        
        mock_check_expired.return_value = [release1, release2]
        
        # First release succeeds, second fails status update
        mock_update_status.side_effect = [True, False]
        
        event = {}
        context = {}
        
        response = handler(event, context)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['totalExpired'] == 2
        assert body['statusUpdated'] == 1
        assert len(body['failedUpdates']) == 1
        assert 'test-release-2' in body['failedUpdates']
    
    @patch('limited_releases.expiry_check.update_release_status')
    @patch('limited_releases.expiry_check.check_expired_releases')
    def test_multiple_successful_updates(
        self,
        mock_check_expired,
        mock_update_status,
        mock_env_vars
    ):
        """Test processing multiple expired releases successfully."""
        now = datetime.utcnow()
        past_date = now - timedelta(hours=1)
        
        releases = []
        for i in range(3):
            release = {
                'releaseId': f'test-release-{i}',
                'endDate': past_date.isoformat(),
                'status': 'active'
            }
            releases.append(release)
        
        mock_check_expired.return_value = releases
        mock_update_status.return_value = True
        
        event = {}
        context = {}
        
        response = handler(event, context)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['totalExpired'] == 3
        assert body['statusUpdated'] == 3
        assert len(body['failedUpdates']) == 0
        assert mock_update_status.call_count == 3
    
    @patch('limited_releases.expiry_check.check_expired_releases')
    def test_exception_handling(self, mock_check_expired, mock_env_vars):
        """Test handling of unexpected exceptions."""
        mock_check_expired.side_effect = Exception('Unexpected error')
        
        event = {}
        context = {}
        
        response = handler(event, context)
        
        assert response['statusCode'] == 500
        body = json.loads(response['body'])
        assert 'error' in body
        assert body['error']['code'] == 'INTERNAL_ERROR'
    
    @patch('limited_releases.expiry_check.update_release_status')
    @patch('limited_releases.expiry_check.check_expired_releases')
    def test_all_updates_fail(
        self,
        mock_check_expired,
        mock_update_status,
        mock_env_vars,
        sample_expired_release
    ):
        """Test when all status updates fail."""
        mock_check_expired.return_value = [sample_expired_release]
        mock_update_status.return_value = False
        
        event = {}
        context = {}
        
        response = handler(event, context)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['totalExpired'] == 1
        assert body['statusUpdated'] == 0
        assert len(body['failedUpdates']) == 1
        assert 'test-release-1' in body['failedUpdates']


class TestIntegration:
    """Integration tests for the complete workflow."""
    
    @patch('limited_releases.expiry_check.update_item')
    @patch('limited_releases.expiry_check.query')
    def test_complete_workflow(
        self,
        mock_query,
        mock_update_item,
        mock_env_vars,
        sample_expired_release
    ):
        """Test the complete workflow from check to update."""
        # Mock query for expired releases
        mock_query.return_value = {
            'Items': [sample_expired_release]
        }
        
        # Mock update
        mock_update_item.return_value = True
        
        event = {}
        context = {}
        
        response = handler(event, context)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['totalExpired'] == 1
        assert body['statusUpdated'] == 1
        
        # Verify all steps were called
        mock_query.assert_called_once()
        mock_update_item.assert_called_once()
    
    @patch('limited_releases.expiry_check.update_item')
    @patch('limited_releases.expiry_check.query')
    def test_mixed_expired_and_active_releases(
        self,
        mock_query,
        mock_update_item,
        mock_env_vars,
        sample_expired_release,
        sample_active_release
    ):
        """Test processing when both expired and active releases exist."""
        # Mock query returns both expired and active
        mock_query.return_value = {
            'Items': [sample_expired_release, sample_active_release]
        }
        
        mock_update_item.return_value = True
        
        event = {}
        context = {}
        
        response = handler(event, context)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        
        # Only expired release should be processed
        assert body['totalExpired'] == 1
        assert body['statusUpdated'] == 1
        
        # Update should only be called once (for expired release)
        mock_update_item.assert_called_once()
    
    @patch('limited_releases.expiry_check.update_item')
    @patch('limited_releases.expiry_check.query')
    def test_releases_expiring_at_exact_time(
        self,
        mock_query,
        mock_update_item,
        mock_env_vars
    ):
        """Test handling of releases expiring at the exact current time."""
        now = datetime.utcnow()
        
        # Release ending exactly now
        release = {
            'releaseId': 'test-release-exact',
            'endDate': now.isoformat(),
            'status': 'active'
        }
        
        mock_query.return_value = {'Items': [release]}
        mock_update_item.return_value = True
        
        event = {}
        context = {}
        
        response = handler(event, context)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        
        # Release ending exactly now should be considered expired
        assert body['totalExpired'] == 1
        assert body['statusUpdated'] == 1


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""
    
    @patch('limited_releases.expiry_check.query')
    def test_release_without_end_date(self, mock_query):
        """Test handling of release without endDate field."""
        release_no_date = {
            'releaseId': 'test-release-no-date',
            'status': 'active'
            # Missing endDate
        }
        
        mock_query.return_value = {'Items': [release_no_date]}
        
        expired = check_expired_releases()
        
        # Should skip release without endDate
        assert len(expired) == 0
    
    @patch('limited_releases.expiry_check.query')
    def test_release_with_timezone_aware_date(self, mock_query):
        """Test handling of timezone-aware datetime strings."""
        now = datetime.utcnow()
        past_date = now - timedelta(hours=1)
        
        release = {
            'releaseId': 'test-release-tz',
            'endDate': past_date.isoformat() + 'Z',  # UTC timezone indicator
            'status': 'active'
        }
        
        mock_query.return_value = {'Items': [release]}
        
        expired = check_expired_releases()
        
        # Should correctly parse timezone-aware date
        assert len(expired) == 1
    
    @patch('limited_releases.expiry_check.update_item')
    def test_update_with_special_characters_in_id(self, mock_update_item):
        """Test update with release ID containing special characters."""
        mock_update_item.return_value = True
        
        special_id = 'test-release-123-abc_xyz'
        result = update_release_status(special_id)
        
        assert result is True
        call_args = mock_update_item.call_args
        assert call_args[1]['pk'] == f'LIMITED_RELEASE#{special_id}'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
