"""
Product analytics Lambda handler for RootTrust marketplace.
Handles GET /analytics/product/{productId} endpoint for product performance metrics.
"""
import json
from typing import Dict, Any
from decimal import Decimal

# Import shared modules
import sys
sys.path.append('/opt/python')

from database import get_item
from constants import OrderStatus


def decimal_to_float(obj):
    """Convert Decimal objects to float for JSON serialization."""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for product analytics endpoint.
    
    Queries product record for viewCount, totalSales, averageRating,
    calculates conversion rate, and returns product performance metrics.
    
    Args:
        event: API Gateway event
        context: Lambda context
        
    Returns:
        API Gateway response with product analytics object
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
                        'code': 'BAD_REQUEST',
                        'message': 'productId path parameter is required'
                    }
                })
            }
        
        # Query product record from DynamoDB
        try:
            product_record = get_item(f"PRODUCT#{product_id}", "METADATA")
            
            if not product_record:
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
        except Exception as e:
            print(f"Error querying product record: {str(e)}")
            return {
                'statusCode': 503,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'SERVICE_UNAVAILABLE',
                        'message': 'Failed to query product record',
                        'details': str(e)
                    }
                })
            }
        
        # Extract metrics from product record
        view_count = int(product_record.get('viewCount', 0))
        total_sales = int(product_record.get('totalSales', 0))
        average_rating = float(product_record.get('averageRating', 0.0))
        total_reviews = int(product_record.get('totalReviews', 0))
        
        # Calculate conversion rate
        conversion_rate = 0.0
        if view_count > 0:
            conversion_rate = (total_sales / view_count) * 100
        
        # Build analytics response
        analytics = {
            'productId': product_id,
            'productName': product_record.get('name', 'Unknown'),
            'viewCount': view_count,
            'totalSales': total_sales,
            'averageRating': round(average_rating, 2),
            'totalReviews': total_reviews,
            'conversionRate': round(conversion_rate, 2),
            'category': product_record.get('category', 'Unknown'),
            'price': float(product_record.get('price', 0.0)),
            'verificationStatus': product_record.get('verificationStatus', 'unknown')
        }
        
        # Return success response
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'analytics': analytics
            }, default=decimal_to_float)
        }
    
    except Exception as e:
        # Catch-all for unexpected errors
        print(f"Unexpected error in product analytics: {str(e)}")
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
