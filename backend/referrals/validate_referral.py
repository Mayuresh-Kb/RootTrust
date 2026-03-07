"""
Referral validation Lambda handler for RootTrust marketplace.
Handles GET /referrals/{code} endpoint to validate and retrieve referral details.
"""
import json
import os
from typing import Dict, Any

# Import shared modules
import sys
sys.path.append('/opt/python')

from database import get_item
from exceptions import ResourceNotFoundError, ServiceUnavailableError


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for referral validation endpoint.
    
    This is a public endpoint (no authentication required) that validates
    a referral code and returns referral details.
    
    Args:
        event: API Gateway event with path parameter 'code'
        context: Lambda context
        
    Returns:
        API Gateway response with referral details (referrerId, productId)
    """
    try:
        # Extract referral code from path parameters
        path_parameters = event.get('pathParameters') or {}
        referral_code = path_parameters.get('code')
        
        if not referral_code:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'INVALID_REQUEST',
                        'message': 'Referral code is required'
                    }
                })
            }
        
        # Query referral by PK=REFERRAL#{code}, SK=METADATA
        pk = f"REFERRAL#{referral_code}"
        sk = "METADATA"
        
        try:
            referral_item = get_item(pk, sk)
        except ServiceUnavailableError as e:
            print(f"Error querying referral: {str(e)}")
            return {
                'statusCode': 503,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'SERVICE_UNAVAILABLE',
                        'message': 'Failed to query referral',
                        'details': str(e)
                    }
                })
            }
        except Exception as e:
            print(f"Unexpected error querying referral: {str(e)}")
            return {
                'statusCode': 503,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'SERVICE_UNAVAILABLE',
                        'message': 'Failed to query referral',
                        'details': str(e)
                    }
                })
            }
        
        # Check if referral exists
        if not referral_item:
            return {
                'statusCode': 404,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'RESOURCE_NOT_FOUND',
                        'message': f'Referral code {referral_code} not found'
                    }
                })
            }
        
        # Extract referral details
        referrer_id = referral_item.get('referrerId')
        product_id = referral_item.get('productId')
        
        # Return referral details
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'referralCode': referral_code,
                'referrerId': referrer_id,
                'productId': product_id,
                'message': 'Referral code is valid'
            })
        }
    
    except Exception as e:
        # Catch-all for unexpected errors
        print(f"Unexpected error in referral validation: {str(e)}")
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
