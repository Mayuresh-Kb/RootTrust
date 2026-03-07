"""
Farmer reviews listing Lambda handler for RootTrust marketplace.
Handles GET /reviews/farmer/{farmerId} endpoint to retrieve all reviews for a farmer's products.
"""
import json
import os
from typing import Dict, Any, List
from datetime import datetime

# Import shared modules
import sys
sys.path.append('/opt/python')

from database import query
from exceptions import ServiceUnavailableError
from boto3.dynamodb.conditions import Key


def format_review_response(review_item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format a review item for API response.
    
    Args:
        review_item: Raw DynamoDB review item
        
    Returns:
        Formatted review dictionary
    """
    return {
        'reviewId': review_item.get('reviewId'),
        'productId': review_item.get('productId'),
        'consumerId': review_item.get('consumerId'),
        'orderId': review_item.get('orderId'),
        'rating': review_item.get('rating'),
        'reviewText': review_item.get('reviewText'),
        'photos': review_item.get('photos', []),
        'helpful': review_item.get('helpful', 0),
        'createdAt': review_item.get('createdAt')
    }


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for farmer reviews listing endpoint.
    
    Retrieves all reviews for a farmer's products using GSI2,
    sorted by creation date in descending order (most recent first).
    
    Args:
        event: API Gateway event with farmerId in path parameters
        context: Lambda context
        
    Returns:
        API Gateway response with reviews array
    """
    try:
        # Extract farmerId from path parameters
        path_params = event.get('pathParameters', {})
        farmer_id = path_params.get('farmerId')
        
        if not farmer_id:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'VALIDATION_ERROR',
                        'message': 'farmerId is required in path parameters'
                    }
                })
            }
        
        # Query DynamoDB using GSI2 for all reviews of this farmer's products
        # GSI2PK=FARMER#{farmerId}
        farmer_gsi2pk = f"FARMER#{farmer_id}"
        
        try:
            result = query(
                key_condition_expression=Key('GSI2PK').eq(farmer_gsi2pk),
                index_name='GSI2',
                scan_index_forward=False  # Sort descending (most recent first)
            )
        except ServiceUnavailableError as e:
            print(f"Error querying farmer reviews: {str(e)}")
            return {
                'statusCode': 503,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'SERVICE_UNAVAILABLE',
                        'message': 'Failed to retrieve reviews',
                        'details': str(e)
                    }
                })
            }
        except Exception as e:
            print(f"Unexpected error querying farmer reviews: {str(e)}")
            return {
                'statusCode': 503,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'SERVICE_UNAVAILABLE',
                        'message': 'Failed to retrieve reviews',
                        'details': str(e)
                    }
                })
            }
        
        # Format reviews for response
        reviews = result.get('Items', [])
        formatted_reviews = [format_review_response(review) for review in reviews]
        
        # Return success response
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'reviews': formatted_reviews,
                'count': len(formatted_reviews)
            })
        }
    
    except Exception as e:
        # Catch-all for unexpected errors
        print(f"Unexpected error in farmer reviews listing: {str(e)}")
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
