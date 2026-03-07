"""
Farmer analytics dashboard Lambda handler for RootTrust marketplace.
Handles GET /analytics/farmer/{farmerId} endpoint for farmer performance metrics.
"""
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List
from decimal import Decimal
from boto3.dynamodb.conditions import Key, Attr

# Import shared modules
import sys
sys.path.append('/opt/python')

from database import query, get_item
from auth import get_user_from_token
from constants import UserRole, OrderStatus


def decimal_to_float(obj):
    """Convert Decimal objects to float for JSON serialization."""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for farmer analytics dashboard endpoint.
    
    Validates JWT token and farmer role authorization, then calculates:
    - Monthly revenue (sum of delivered orders this month)
    - Total sales count
    - Average rating and total reviews
    - Product view counts and conversion rates
    - Top products by revenue
    
    Args:
        event: API Gateway event
        context: Lambda context
        
    Returns:
        API Gateway response with analytics object
    """
    try:
        # Extract authorization header
        headers = event.get('headers', {})
        auth_header = headers.get('Authorization') or headers.get('authorization')
        
        if not auth_header:
            return {
                'statusCode': 401,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'UNAUTHORIZED',
                        'message': 'Authorization header is required'
                    }
                })
            }
        
        # Validate JWT token and extract user info
        try:
            user_info = get_user_from_token(auth_header)
            user_id = user_info['userId']
            user_role = user_info['role']
        except Exception as e:
            return {
                'statusCode': 401,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'INVALID_TOKEN',
                        'message': str(e)
                    }
                })
            }
        
        # Verify farmer role
        if user_role != UserRole.FARMER.value:
            return {
                'statusCode': 403,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'FORBIDDEN',
                        'message': 'Only farmers can access analytics dashboard'
                    }
                })
            }
        
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
                        'code': 'BAD_REQUEST',
                        'message': 'farmerId path parameter is required'
                    }
                })
            }
        
        # Verify farmer is accessing their own analytics
        if user_id != farmer_id:
            return {
                'statusCode': 403,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'FORBIDDEN',
                        'message': 'You can only access your own analytics'
                    }
                })
            }
        
        # Query all orders for farmer using GSI3
        try:
            gsi3_pk = f"FARMER#{farmer_id}"
            orders_result = query(
                key_condition_expression=Key('GSI3PK').eq(gsi3_pk) & Key('GSI3SK').begins_with('ORDER#'),
                index_name='GSI3'
            )
            all_orders = orders_result.get('Items', [])
        except Exception as e:
            print(f"Error querying farmer orders: {str(e)}")
            return {
                'statusCode': 503,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'SERVICE_UNAVAILABLE',
                        'message': 'Failed to query orders',
                        'details': str(e)
                    }
                })
            }
        
        # Calculate current month start date
        now = datetime.utcnow()
        month_start = datetime(now.year, now.month, 1)
        
        # Filter orders by current month and status=delivered
        monthly_revenue = 0.0
        total_sales = 0
        product_revenue = {}  # Track revenue per product
        
        for order in all_orders:
            order_date_str = order.get('createdAt', '')
            order_status = order.get('status', '')
            
            # Parse order date
            try:
                order_date = datetime.fromisoformat(order_date_str.replace('Z', '+00:00'))
            except:
                continue
            
            # Check if order is delivered
            if order_status == OrderStatus.DELIVERED.value:
                total_sales += 1
                
                # Check if order is in current month
                if order_date >= month_start:
                    total_amount = float(order.get('totalAmount', 0))
                    monthly_revenue += total_amount
                
                # Track product revenue for top products
                product_id = order.get('productId')
                if product_id:
                    total_amount = float(order.get('totalAmount', 0))
                    if product_id not in product_revenue:
                        product_revenue[product_id] = {
                            'productId': product_id,
                            'productName': order.get('productName', 'Unknown'),
                            'revenue': 0.0,
                            'salesCount': 0
                        }
                    product_revenue[product_id]['revenue'] += total_amount
                    product_revenue[product_id]['salesCount'] += 1
        
        # Query farmer record for averageRating and totalReviews
        try:
            farmer_record = get_item(f"USER#{farmer_id}", "PROFILE")
            
            if not farmer_record:
                return {
                    'statusCode': 404,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({
                        'error': {
                            'code': 'NOT_FOUND',
                            'message': 'Farmer not found'
                        }
                    })
                }
            
            farmer_profile = farmer_record.get('farmerProfile', {})
            average_rating = float(farmer_profile.get('averageRating', 0.0))
            total_reviews = int(farmer_profile.get('totalReviews', 0))
            
        except Exception as e:
            print(f"Error querying farmer record: {str(e)}")
            return {
                'statusCode': 503,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'SERVICE_UNAVAILABLE',
                        'message': 'Failed to query farmer record',
                        'details': str(e)
                    }
                })
            }
        
        # Query all farmer's products for view counts
        try:
            gsi2_pk = f"FARMER#{farmer_id}"
            products_result = query(
                key_condition_expression=Key('GSI2PK').eq(gsi2_pk) & Key('GSI2SK').begins_with('PRODUCT#'),
                index_name='GSI2'
            )
            products = products_result.get('Items', [])
        except Exception as e:
            print(f"Error querying farmer products: {str(e)}")
            return {
                'statusCode': 503,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'SERVICE_UNAVAILABLE',
                        'message': 'Failed to query products',
                        'details': str(e)
                    }
                })
            }
        
        # Calculate total views and conversion rates
        total_views = 0
        product_analytics = []
        
        for product in products:
            product_id = product.get('productId')
            view_count = int(product.get('viewCount', 0))
            total_views += view_count
            
            # Get sales count for this product
            sales_count = 0
            if product_id in product_revenue:
                sales_count = product_revenue[product_id]['salesCount']
            
            # Calculate conversion rate
            conversion_rate = 0.0
            if view_count > 0:
                conversion_rate = (sales_count / view_count) * 100
            
            product_analytics.append({
                'productId': product_id,
                'productName': product.get('name', 'Unknown'),
                'viewCount': view_count,
                'salesCount': sales_count,
                'conversionRate': round(conversion_rate, 2)
            })
        
        # Calculate overall conversion rate
        overall_conversion_rate = 0.0
        if total_views > 0:
            overall_conversion_rate = (total_sales / total_views) * 100
        
        # Identify top products by revenue
        top_products = sorted(
            product_revenue.values(),
            key=lambda x: x['revenue'],
            reverse=True
        )[:5]  # Top 5 products
        
        # Format top products for response
        formatted_top_products = []
        for product in top_products:
            formatted_top_products.append({
                'productId': product['productId'],
                'productName': product['productName'],
                'revenue': round(product['revenue'], 2),
                'salesCount': product['salesCount']
            })
        
        # Build analytics response
        analytics = {
            'farmerId': farmer_id,
            'monthlyRevenue': round(monthly_revenue, 2),
            'totalSales': total_sales,
            'averageRating': round(average_rating, 2),
            'totalReviews': total_reviews,
            'totalViews': total_views,
            'conversionRate': round(overall_conversion_rate, 2),
            'topProducts': formatted_top_products,
            'productAnalytics': product_analytics,
            'period': {
                'month': now.month,
                'year': now.year,
                'monthStart': month_start.isoformat()
            }
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
        print(f"Unexpected error in farmer analytics: {str(e)}")
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
