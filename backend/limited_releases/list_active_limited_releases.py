"""
Active limited releases listing Lambda handler for RootTrust marketplace.
Handles GET /limited-releases endpoint to list all active limited releases.
"""
import json
import os
from typing import Dict, Any
from datetime import datetime
from boto3.dynamodb.conditions import Key

# Import shared modules
import sys
sys.path.append('/opt/python')

from database import query, get_item
from constants import LimitedReleaseStatus
from exceptions import ServiceUnavailableError


def calculate_countdown(end_date_str: str) -> Dict[str, Any]:
    """
    Calculate countdown timer data from end date.
    
    Args:
        end_date_str: ISO 8601 formatted end date string
        
    Returns:
        Dictionary with countdown information
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
                'secondsRemaining': 0
            }
        
        time_remaining = end_date - now
        days = time_remaining.days
        seconds = time_remaining.seconds
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60
        
        return {
            'expired': False,
            'daysRemaining': days,
            'hoursRemaining': hours,
            'minutesRemaining': minutes,
            'secondsRemaining': seconds,
            'totalSeconds': int(time_remaining.total_seconds())
        }
    
    except Exception as e:
        print(f"Error calculating countdown: {str(e)}")
        return {
            'expired': False,
            'daysRemaining': 0,
            'hoursRemaining': 0,
            'minutesRemaining': 0,
            'secondsRemaining': 0
        }


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for active limited releases listing endpoint.
    
    Queries GSI3 with GSI3PK=STATUS#active to retrieve all active limited releases.
    Returns active releases with product details, quantityRemaining, and countdown.
    
    Args:
        event: API Gateway event
        context: Lambda context
        
    Returns:
        API Gateway response with active limited releases array
    """
    try:
        # Extract query parameters for pagination
        query_params = event.get('queryStringParameters') or {}
        limit = int(query_params.get('limit', 50))
        cursor = query_params.get('cursor')
        
        # Validate limit
        if limit < 1 or limit > 100:
            limit = 50
        
        # Prepare exclusive start key for pagination
        exclusive_start_key = None
        if cursor:
            try:
                import base64
                cursor_data = json.loads(base64.b64decode(cursor).decode('utf-8'))
                exclusive_start_key = cursor_data
            except Exception as e:
                print(f"Invalid cursor: {str(e)}")
                # Continue without cursor if invalid
        
        # Query GSI3 for active limited releases
        try:
            gsi3_pk = f"STATUS#{LimitedReleaseStatus.ACTIVE.value}"
            
            result = query(
                key_condition_expression=Key('GSI3PK').eq(gsi3_pk),
                index_name='GSI3',
                limit=limit,
                exclusive_start_key=exclusive_start_key,
                scan_index_forward=False  # Most recent first (by endDate)
            )
            
            releases = result.get('Items', [])
            last_evaluated_key = result.get('LastEvaluatedKey')
        
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
                        'message': 'Failed to query limited releases',
                        'details': str(e)
                    }
                })
            }
        except Exception as e:
            print(f"Error querying limited releases: {str(e)}")
            return {
                'statusCode': 503,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'SERVICE_UNAVAILABLE',
                        'message': 'Failed to query limited releases',
                        'details': str(e)
                    }
                })
            }
        
        # Enrich releases with product details and countdown
        enriched_releases = []
        for release in releases:
            try:
                # Query product details
                product_id = release.get('productId')
                if product_id:
                    product = get_item(f"PRODUCT#{product_id}", "METADATA")
                    
                    if product:
                        # Calculate countdown timer
                        end_date = release.get('endDate')
                        countdown = calculate_countdown(end_date) if end_date else None
                        
                        # Add product details and countdown to release
                        enriched_release = {
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
                            'product': {
                                'name': product.get('name'),
                                'category': product.get('category'),
                                'price': product.get('price'),
                                'unit': product.get('unit'),
                                'images': product.get('images', []),
                                'averageRating': product.get('averageRating', 0),
                                'giTag': product.get('giTag', {}),
                                'description': product.get('description', '')
                            }
                        }
                        enriched_releases.append(enriched_release)
                    else:
                        # Product not found, skip this release
                        print(f"Product {product_id} not found for release {release.get('releaseId')}")
                else:
                    # No product ID, skip
                    print(f"Release {release.get('releaseId')} has no productId")
            
            except Exception as e:
                # Log error but continue with other releases
                print(f"Error enriching release {release.get('releaseId')}: {str(e)}")
                continue
        
        # Prepare response
        response_body = {
            'releases': enriched_releases,
            'count': len(enriched_releases)
        }
        
        # Add pagination cursor if there are more results
        if last_evaluated_key:
            import base64
            cursor_str = base64.b64encode(
                json.dumps(last_evaluated_key).encode('utf-8')
            ).decode('utf-8')
            response_body['nextCursor'] = cursor_str
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(response_body)
        }
    
    except Exception as e:
        # Catch-all for unexpected errors
        print(f"Unexpected error in active limited releases listing: {str(e)}")
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
