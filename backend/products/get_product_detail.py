"""
Product detail Lambda handler for RootTrust marketplace.
Handles GET /products/{productId} endpoint for viewing detailed product information.
"""
import json
import os
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Any, Optional, List

# Import shared modules
import sys
sys.path.append('/opt/python')

from database import get_item, query, update_item
from constants import VerificationStatus
from exceptions import ResourceNotFoundError, ServiceUnavailableError


class DecimalEncoder(json.JSONEncoder):
    """Custom JSON encoder for Decimal types from DynamoDB."""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)


def get_farmer_profile(farmer_id: str) -> Optional[Dict[str, Any]]:
    """
    Get farmer profile information.
    
    Args:
        farmer_id: Farmer user ID
        
    Returns:
        Farmer profile dictionary or None
    """
    try:
        user = get_item(f"USER#{farmer_id}", "PROFILE")
        if not user:
            return None
        
        farmer_profile = user.get('farmerProfile', {})
        
        return {
            'farmerId': farmer_id,
            'firstName': user.get('firstName', ''),
            'lastName': user.get('lastName', ''),
            'farmName': farmer_profile.get('farmName', ''),
            'farmLocation': farmer_profile.get('farmLocation', ''),
            'certifications': farmer_profile.get('certifications', []),
            'averageRating': farmer_profile.get('averageRating', 0.0),
            'totalReviews': farmer_profile.get('totalReviews', 0),
            'totalSales': farmer_profile.get('totalSales', 0),
            'featuredStatus': farmer_profile.get('featuredStatus', False)
        }
    except Exception as e:
        print(f"Error fetching farmer profile: {str(e)}")
        return None


def get_product_reviews(product_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get reviews for a product.
    
    Args:
        product_id: Product ID
        limit: Maximum number of reviews to return
        
    Returns:
        List of review dictionaries
    """
    try:
        from boto3.dynamodb.conditions import Key
        
        # Query reviews using PK=PRODUCT#{productId}, SK begins_with REVIEW#
        key_condition = Key('PK').eq(f"PRODUCT#{product_id}") & Key('SK').begins_with('REVIEW#')
        
        result = query(
            key_condition_expression=key_condition,
            limit=limit,
            scan_index_forward=False  # Most recent first
        )
        
        reviews = []
        for item in result.get('Items', []):
            reviews.append({
                'reviewId': item.get('reviewId'),
                'consumerId': item.get('consumerId'),
                'rating': item.get('rating'),
                'reviewText': item.get('reviewText'),
                'photos': item.get('photos', []),
                'helpful': item.get('helpful', 0),
                'createdAt': item.get('createdAt')
            })
        
        return reviews
    except Exception as e:
        print(f"Error fetching product reviews: {str(e)}")
        return []


def increment_viewer_count(product_id: str) -> int:
    """
    Increment and return current viewer count for a product.
    Uses a TTL-based approach to track concurrent viewers.
    
    Args:
        product_id: Product ID
        
    Returns:
        Current viewer count
    """
    try:
        # Increment currentViewers counter
        # In a real implementation, this would use a separate viewer tracking table with TTL
        # For now, we'll just increment the counter
        updated = update_item(
            pk=f"PRODUCT#{product_id}",
            sk="METADATA",
            update_expression="ADD currentViewers :inc",
            expression_attribute_values={
                ':inc': 1
            }
        )
        
        return updated.get('currentViewers', 1)
    except Exception as e:
        print(f"Error incrementing viewer count: {str(e)}")
        return 0


def format_product_detail(
    product: Dict[str, Any],
    farmer_profile: Optional[Dict[str, Any]],
    reviews: List[Dict[str, Any]],
    current_viewers: int
) -> Dict[str, Any]:
    """
    Format complete product detail response.
    
    Args:
        product: Product item from DynamoDB
        farmer_profile: Farmer profile information
        reviews: List of product reviews
        current_viewers: Current viewer count
        
    Returns:
        Formatted product detail dictionary
    """
    # Extract images
    images = product.get('images', [])
    primary_image = None
    for img in images:
        if img.get('isPrimary'):
            primary_image = img.get('url')
            break
    if not primary_image and images:
        primary_image = images[0].get('url')
    
    # Calculate if product is low stock
    quantity = product.get('quantity', 0)
    low_stock = quantity < 10
    
    # Check if seasonal and calculate days remaining
    seasonal = product.get('seasonal', {})
    days_remaining = None
    if seasonal.get('isSeasonal') and seasonal.get('seasonEnd'):
        try:
            season_end = datetime.fromisoformat(seasonal['seasonEnd'].replace('Z', '+00:00'))
            now = datetime.utcnow()
            if season_end > now:
                days_remaining = (season_end - now).days
        except Exception as e:
            print(f"Error calculating days remaining: {str(e)}")
    
    return {
        'productId': product.get('productId'),
        'name': product.get('name'),
        'category': product.get('category'),
        'description': product.get('description'),
        'price': product.get('price'),
        'unit': product.get('unit'),
        'images': images,
        'primaryImage': primary_image,
        'giTag': product.get('giTag', {}),
        'seasonal': {
            **seasonal,
            'daysRemaining': days_remaining
        },
        'quantity': quantity,
        'lowStock': low_stock,
        'verificationStatus': product.get('verificationStatus'),
        'fraudRiskScore': product.get('fraudRiskScore'),
        'authenticityConfidence': product.get('authenticityConfidence'),
        'aiExplanation': product.get('aiExplanation'),
        'predictedMarketPrice': product.get('predictedMarketPrice'),
        'averageRating': product.get('averageRating', 0.0),
        'totalReviews': product.get('totalReviews', 0),
        'totalSales': product.get('totalSales', 0),
        'viewCount': product.get('viewCount', 0),
        'currentViewers': current_viewers,
        'recentPurchaseCount': product.get('recentPurchaseCount', 0),
        'createdAt': product.get('createdAt'),
        'updatedAt': product.get('updatedAt'),
        'farmer': farmer_profile,
        'reviews': reviews
    }


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for product detail endpoint.
    
    Retrieves complete product information including:
    - Product details
    - Farmer profile
    - Product reviews
    - Current viewer count
    
    Args:
        event: API Gateway event
        context: Lambda context
        
    Returns:
        API Gateway response with complete product details
    """
    try:
        # Extract product ID from path parameters
        path_params = event.get('pathParameters') or {}
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
                        'code': 'MISSING_PARAMETER',
                        'message': 'Product ID is required'
                    }
                })
            }
        
        # Query product from DynamoDB
        product = get_item(f"PRODUCT#{product_id}", "METADATA")
        
        if not product:
            return {
                'statusCode': 404,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'PRODUCT_NOT_FOUND',
                        'message': f'Product with ID {product_id} not found'
                    }
                })
            }
        
        # Get farmer profile
        farmer_id = product.get('farmerId')
        farmer_profile = None
        if farmer_id:
            farmer_profile = get_farmer_profile(farmer_id)
        
        # Get product reviews
        reviews = get_product_reviews(product_id, limit=10)
        
        # Increment viewer count
        current_viewers = increment_viewer_count(product_id)
        
        # Format complete product detail
        product_detail = format_product_detail(
            product=product,
            farmer_profile=farmer_profile,
            reviews=reviews,
            current_viewers=current_viewers
        )
        
        # Return success response
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(product_detail, cls=DecimalEncoder)
        }
    
    except ServiceUnavailableError as e:
        print(f"Service unavailable: {str(e)}")
        return {
            'statusCode': 503,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': {
                    'code': 'SERVICE_UNAVAILABLE',
                    'message': str(e)
                }
            })
        }
    
    except Exception as e:
        # Catch-all for unexpected errors
        print(f"Unexpected error in product detail: {str(e)}")
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
