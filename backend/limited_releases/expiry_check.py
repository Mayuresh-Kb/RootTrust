"""
Limited release expiry check Lambda handler for RootTrust marketplace.
Scheduled by EventBridge to run every 5 minutes and check for expired limited releases.
Updates release status to expired and removes from marketplace listings.
"""
import json
import os
from typing import Dict, Any, List
from datetime import datetime
from boto3.dynamodb.conditions import Key

# Import shared modules
import sys
sys.path.append('/opt/python')

from database import query, update_item
from constants import LimitedReleaseStatus


def check_expired_releases() -> List[Dict[str, Any]]:
    """
    Query active limited releases and check if any have passed their endDate.
    
    Returns:
        List of expired limited release records
    """
    expired_releases = []
    
    try:
        # Query GSI3 for active limited releases
        gsi3_pk = f"STATUS#{LimitedReleaseStatus.ACTIVE.value}"
        
        result = query(
            key_condition_expression=Key('GSI3PK').eq(gsi3_pk),
            index_name='GSI3',
            scan_index_forward=True  # Oldest endDate first
        )
        
        releases = result.get('Items', [])
        current_time = datetime.utcnow()
        
        # Check each release's endDate
        for release in releases:
            end_date_str = release.get('endDate')
            if end_date_str:
                try:
                    # Parse ISO format datetime
                    end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
                    
                    # Remove timezone info for comparison if present
                    if end_date.tzinfo is not None:
                        end_date = end_date.replace(tzinfo=None)
                    
                    # Check if release has expired
                    if end_date <= current_time:
                        expired_releases.append(release)
                except Exception as e:
                    print(f"Error parsing endDate for release {release.get('releaseId')}: {str(e)}")
                    continue
        
        return expired_releases
    
    except Exception as e:
        print(f"Error querying active limited releases: {str(e)}")
        raise


def update_release_status(release_id: str) -> bool:
    """
    Update limited release status from active to expired.
    
    Args:
        release_id: The release ID to update
        
    Returns:
        True if update succeeded, False otherwise
    """
    try:
        new_status = LimitedReleaseStatus.EXPIRED.value
        
        update_item(
            pk=f"LIMITED_RELEASE#{release_id}",
            sk="METADATA",
            update_expression="SET #status = :status, #gsi3pk = :gsi3pk",
            expression_attribute_names={
                '#status': 'status',
                '#gsi3pk': 'GSI3PK'
            },
            expression_attribute_values={
                ':status': new_status,
                ':gsi3pk': f"STATUS#{new_status}"
            }
        )
        
        return True
    
    except Exception as e:
        print(f"Error updating release {release_id} status: {str(e)}")
        return False


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for limited release expiry check.
    
    Triggered by EventBridge every 5 minutes.
    Checks for expired limited releases, updates their status to expired,
    and removes them from marketplace listings.
    
    Args:
        event: EventBridge event
        context: Lambda context
        
    Returns:
        Response with processing summary
    """
    try:
        print("Starting limited release expiry check...")
        
        # Find expired releases
        expired_releases = check_expired_releases()
        
        if not expired_releases:
            print("No expired limited releases found")
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'No expired limited releases found',
                    'processed': 0
                })
            }
        
        print(f"Found {len(expired_releases)} expired limited release(s)")
        
        # Process each expired release
        processed_count = 0
        failed_updates = []
        
        for release in expired_releases:
            release_id = release.get('releaseId')
            print(f"Processing expired limited release: {release_id}")
            
            # Update status to expired
            if update_release_status(release_id):
                processed_count += 1
                print(f"Updated release {release_id} status to expired")
            else:
                failed_updates.append(release_id)
        
        # Log summary
        print(f"Limited release expiry check completed:")
        print(f"  - Total expired: {len(expired_releases)}")
        print(f"  - Status updated: {processed_count}")
        
        if failed_updates:
            print(f"  - Failed status updates: {failed_updates}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Limited release expiry check completed',
                'totalExpired': len(expired_releases),
                'statusUpdated': processed_count,
                'failedUpdates': failed_updates
            })
        }
    
    except Exception as e:
        # Catch-all for unexpected errors
        print(f"Unexpected error in limited release expiry check: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': {
                    'code': 'INTERNAL_ERROR',
                    'message': 'An unexpected error occurred during limited release expiry check',
                    'details': str(e)
                }
            })
        }
