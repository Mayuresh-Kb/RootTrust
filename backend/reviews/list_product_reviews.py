"""
Product reviews listing Lambda handler for RootTrust marketplace.
Handles GET /reviews/product/{productId} endpoint to retrieve all reviews for a product.
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
    Lambda handler for product reviews listing endpoint.
    
    Retrieves all reviews for a specific product, sorted by creation date
    in descending order (most recent first).
    
    Args:
        event: API Gateway event with productId in path parameters
        context: Lambda context
        
    Returns:
        API Gateway response with reviews array
    """
    try:
        # Extract productId from path parameters
        path_params = event.get('pathParameters', {})
        product_id = path_params.get('productId')
        
        if not product_id:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'VALIDATION_ERROR',
                        'message': 'productId is required in path parameters'
                    }
                })
            }
        
        # Query DynamoDB for all reviews of this product
        # PK=PRODUCT#{productId}, SK begins_with REVIEW#
        product_pk = f"PRODUCT#{product_id}"
        
        try:
            result = query(
                key_condition_expression=Key('PK').eq(product_pk) & Key('SK').begins_with('REVIEW#'),
                scan_index_forward=False  # Sort descending (most recent first)
            )
        except ServiceUnavailableError as e:
            print(f"Error querying reviews: {str(e)}")
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
            print(f"Unexpected error querying reviews: {str(e)}")
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
        print(f"Unexpected error in product reviews listing: {str(e)}")
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
