"""
Product listing Lambda handler for RootTrust marketplace.
Handles GET /products endpoint for browsing products with filters.
"""
import json
import os
import base64
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, Optional, List
from boto3.dynamodb.conditions import Key, Attr

# Import shared modules
import sys
sys.path.append('/opt/python')

from database import query, scan, get_item
from constants import VerificationStatus, ProductCategory, DEFAULT_PAGE_LIMIT, MAX_PAGE_LIMIT
from exceptions import ValidationError, ServiceUnavailableError


class DecimalEncoder(json.JSONEncoder):
    """Custom JSON encoder for Decimal types from DynamoDB."""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)


def parse_cursor(cursor: Optional[str]) -> Optional[Dict[str, Any]]:
    """
    Parse base64-encoded pagination cursor.
    
    Args:
        cursor: Base64-encoded cursor string
        
    Returns:
        Decoded cursor dictionary or None
    """
    if not cursor:
        return None
    
    try:
        decoded = base64.b64decode(cursor).decode('utf-8')
        return json.loads(decoded)
    except Exception as e:
        print(f"Error parsing cursor: {str(e)}")
        return None


def encode_cursor(last_evaluated_key: Dict[str, Any]) -> str:
    """
    Encode pagination cursor to base64.
    
    Args:
        last_evaluated_key: DynamoDB LastEvaluatedKey
        
    Returns:
        Base64-encoded cursor string
    """
    cursor_json = json.dumps(last_evaluated_key)
    return base64.b64encode(cursor_json.encode('utf-8')).decode('utf-8')


def is_product_seasonal_match(product: Dict[str, Any], current_date: datetime) -> bool:
    """
    Check if product matches seasonal filter criteria.
    
    Args:
        product: Product item from DynamoDB
        current_date: Current date for comparison
        
    Returns:
        True if product is in season, False otherwise
    """
    seasonal = product.get('seasonal', {})
    
    if not seasonal.get('isSeasonal'):
        return False
    
    season_start = seasonal.get('seasonStart')
    season_end = seasonal.get('seasonEnd')
    
    if not season_start or not season_end:
        return False
    
    try:
        start_date = datetime.fromisoformat(season_start.replace('Z', '+00:00'))
        end_date = datetime.fromisoformat(season_end.replace('Z', '+00:00'))
        
        return start_date <= current_date <= end_date
    except Exception as e:
        print(f"Error parsing seasonal dates: {str(e)}")
        return False


def matches_keyword_search(product: Dict[str, Any], search_term: str) -> bool:
    """
    Check if product matches keyword search in name or description.
    
    Args:
        product: Product item from DynamoDB
        search_term: Search keyword (case-insensitive)
        
    Returns:
        True if product matches search, False otherwise
    """
    search_lower = search_term.lower()
    
    name = product.get('name', '').lower()
    description = product.get('description', '').lower()
    
    return search_lower in name or search_lower in description


def get_farmer_name(farmer_id: str) -> str:
    """
    Get farmer name from user record.
    
    Args:
        farmer_id: Farmer user ID
        
    Returns:
        Farmer's full name or 'Unknown Farmer'
    """
    try:
        user = get_item(f"USER#{farmer_id}", "PROFILE")
        if user:
            first_name = user.get('firstName', '')
            last_name = user.get('lastName', '')
            return f"{first_name} {last_name}".strip() or "Unknown Farmer"
        return "Unknown Farmer"
    except Exception as e:
        print(f"Error fetching farmer name: {str(e)}")
        return "Unknown Farmer"


def format_product_for_listing(product: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format product data for listing response.
    
    Args:
        product: Product item from DynamoDB
        
    Returns:
        Formatted product dictionary
    """
    # Get farmer name
    farmer_id = product.get('farmerId', '')
    farmer_name = get_farmer_name(farmer_id)
    
    # Extract images
    images = product.get('images', [])
    primary_image = None
    for img in images:
        if img.get('isPrimary'):
            primary_image = img.get('url')
            break
    if not primary_image and images:
        primary_image = images[0].get('url')
    
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
        'seasonal': product.get('seasonal', {}),
        'farmerName': farmer_name,
        'farmerId': farmer_id,
        'averageRating': product.get('averageRating', 0.0),
        'totalReviews': product.get('totalReviews', 0),
        'quantity': product.get('quantity', 0),
        'authenticityConfidence': product.get('authenticityConfidence'),
        'createdAt': product.get('createdAt')
    }


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for product listing endpoint.
    
    Accepts query parameters:
    - category: Filter by product category
    - seasonal: Filter by seasonal products (true/false)
    - giTag: Filter by GI tag presence (true/false)
    - search: Keyword search in name/description
    - limit: Number of results per page (default 20, max 100)
    - cursor: Pagination cursor
    
    Returns only products with verificationStatus=approved.
    
    Args:
        event: API Gateway event
        context: Lambda context
        
    Returns:
        API Gateway response with products array and nextCursor
    """
    try:
        # Extract query parameters
        query_params = event.get('queryStringParameters') or {}
        
        category = query_params.get('category')
        seasonal_filter = query_params.get('seasonal', '').lower() == 'true'
        gi_tag_filter = query_params.get('giTag', '').lower() == 'true'
        search_term = query_params.get('search', '').strip()
        limit_str = query_params.get('limit', str(DEFAULT_PAGE_LIMIT))
        cursor = query_params.get('cursor')
        
        # Validate and parse limit
        try:
            limit = int(limit_str)
            if limit < 1:
                limit = DEFAULT_PAGE_LIMIT
            elif limit > MAX_PAGE_LIMIT:
                limit = MAX_PAGE_LIMIT
        except ValueError:
            limit = DEFAULT_PAGE_LIMIT
        
        # Parse pagination cursor
        exclusive_start_key = parse_cursor(cursor)
        
        # Determine query strategy
        products = []
        last_evaluated_key = None
        
        if category:
            # Validate category
            try:
                category_enum = ProductCategory(category)
                category_value = category_enum.value
            except ValueError:
                return {
                    'statusCode': 400,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({
                        'error': {
                            'code': 'INVALID_CATEGORY',
                            'message': f'Invalid category: {category}. Valid categories: {[c.value for c in ProductCategory]}'
                        }
                    })
                }
            
            # Query using GSI1 for category filter
            key_condition = Key('GSI1PK').eq(f"CATEGORY#{category_value}")
            filter_expr = Attr('verificationStatus').eq(VerificationStatus.APPROVED.value)
            
            result = query(
                key_condition_expression=key_condition,
                filter_expression=filter_expr,
                index_name='GSI1',
                limit=limit * 2,  # Fetch more to account for filtering
                exclusive_start_key=exclusive_start_key,
                scan_index_forward=False  # Most recent first
            )
            
            products = result.get('Items', [])
            last_evaluated_key = result.get('LastEvaluatedKey')
        
        else:
            # No category filter - use GSI3 to query by verification status
            key_condition = Key('GSI3PK').eq(f"STATUS#{VerificationStatus.APPROVED.value}")
            
            result = query(
                key_condition_expression=key_condition,
                index_name='GSI3',
                limit=limit * 2,  # Fetch more to account for filtering
                exclusive_start_key=exclusive_start_key,
                scan_index_forward=False  # Most recent first
            )
            
            products = result.get('Items', [])
            last_evaluated_key = result.get('LastEvaluatedKey')
        
        # Apply additional filters
        filtered_products = []
        current_date = datetime.utcnow()
        
        for product in products:
            # Skip if not approved (double-check)
            if product.get('verificationStatus') != VerificationStatus.APPROVED.value:
                continue
            
            # Apply seasonal filter
            if seasonal_filter:
                if not is_product_seasonal_match(product, current_date):
                    continue
            
            # Apply GI tag filter
            if gi_tag_filter:
                gi_tag = product.get('giTag', {})
                if not gi_tag.get('hasTag'):
                    continue
            
            # Apply keyword search
            if search_term:
                if not matches_keyword_search(product, search_term):
                    continue
            
            filtered_products.append(product)
            
            # Stop if we have enough results
            if len(filtered_products) >= limit:
                break
        
        # Format products for response
        formatted_products = [format_product_for_listing(p) for p in filtered_products]
        
        # Encode next cursor if there are more results
        next_cursor = None
        if last_evaluated_key and len(filtered_products) >= limit:
            next_cursor = encode_cursor(last_evaluated_key)
        
        # Return success response
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'products': formatted_products,
                'count': len(formatted_products),
                'nextCursor': next_cursor,
                'hasMore': next_cursor is not None
            }, cls=DecimalEncoder)
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
        print(f"Unexpected error in product listing: {str(e)}")
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
