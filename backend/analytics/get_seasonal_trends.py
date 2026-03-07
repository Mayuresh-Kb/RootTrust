"""
Seasonal trends analytics Lambda handler for RootTrust marketplace.
Handles GET /analytics/trends endpoint for seasonal sales trend data.
"""
import json
from typing import Dict, Any, List
from decimal import Decimal
from datetime import datetime
from boto3.dynamodb.conditions import Attr

# Import shared modules
import sys
sys.path.append('/opt/python')

from database import scan
from constants import ProductCategory, OrderStatus


def decimal_to_float(obj):
    """Convert Decimal objects to float for JSON serialization."""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for seasonal trends analytics endpoint.
    
    Queries all products from DynamoDB, groups by category and seasonal status,
    calculates sales trends by season, and returns comprehensive trend data.
    
    Args:
        event: API Gateway event
        context: Lambda context
        
    Returns:
        API Gateway response with seasonal trends data
    """
    try:
        # Query all products from DynamoDB using scan
        # Note: In production, this should be optimized with better indexing
        # or pre-aggregated data, but for MVP this is acceptable
        try:
            products_result = scan(
                filter_expression=Attr('EntityType').eq('Product')
            )
            products = products_result.get('Items', [])
        except Exception as e:
            print(f"Error scanning products: {str(e)}")
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
        
        # Initialize data structures for trend analysis
        category_trends = {}
        seasonal_vs_nonseasonal = {
            'seasonal': {
                'totalProducts': 0,
                'totalSales': 0,
                'totalRevenue': 0.0,
                'averagePrice': 0.0,
                'categories': {}
            },
            'nonSeasonal': {
                'totalProducts': 0,
                'totalSales': 0,
                'totalRevenue': 0.0,
                'averagePrice': 0.0,
                'categories': {}
            }
        }
        
        # Track seasonal availability by month
        seasonal_by_month = {}
        for month in range(1, 13):
            seasonal_by_month[month] = {
                'productsAvailable': 0,
                'categories': {}
            }
        
        # Process each product
        for product in products:
            category = product.get('category', 'unknown')
            is_seasonal = product.get('seasonal', {}).get('isSeasonal', False)
            total_sales = int(product.get('totalSales', 0))
            price = float(product.get('price', 0.0))
            
            # Initialize category in trends if not exists
            if category not in category_trends:
                category_trends[category] = {
                    'category': category,
                    'totalProducts': 0,
                    'seasonalProducts': 0,
                    'nonSeasonalProducts': 0,
                    'totalSales': 0,
                    'totalRevenue': 0.0,
                    'averagePrice': 0.0
                }
            
            # Update category trends
            category_trends[category]['totalProducts'] += 1
            category_trends[category]['totalSales'] += total_sales
            category_trends[category]['totalRevenue'] += total_sales * price
            
            # Determine seasonal vs non-seasonal
            if is_seasonal:
                category_trends[category]['seasonalProducts'] += 1
                seasonal_vs_nonseasonal['seasonal']['totalProducts'] += 1
                seasonal_vs_nonseasonal['seasonal']['totalSales'] += total_sales
                seasonal_vs_nonseasonal['seasonal']['totalRevenue'] += total_sales * price
                
                # Track by category within seasonal
                if category not in seasonal_vs_nonseasonal['seasonal']['categories']:
                    seasonal_vs_nonseasonal['seasonal']['categories'][category] = {
                        'products': 0,
                        'sales': 0,
                        'revenue': 0.0
                    }
                seasonal_vs_nonseasonal['seasonal']['categories'][category]['products'] += 1
                seasonal_vs_nonseasonal['seasonal']['categories'][category]['sales'] += total_sales
                seasonal_vs_nonseasonal['seasonal']['categories'][category]['revenue'] += total_sales * price
                
                # Track seasonal availability by month
                season_start = product.get('seasonal', {}).get('seasonStart')
                season_end = product.get('seasonal', {}).get('seasonEnd')
                
                if season_start and season_end:
                    try:
                        # Parse dates
                        start_date = datetime.fromisoformat(season_start.replace('Z', '+00:00'))
                        end_date = datetime.fromisoformat(season_end.replace('Z', '+00:00'))
                        
                        # Determine which months this product is available
                        # Simple approach: check if month falls within season
                        for month in range(1, 13):
                            # Create a date in the middle of the month for checking
                            check_date = datetime(datetime.utcnow().year, month, 15)
                            
                            # Check if this month falls within the season
                            # Handle year wrapping for seasonal products
                            if start_date.month <= end_date.month:
                                # Season doesn't wrap around year
                                if start_date.month <= month <= end_date.month:
                                    seasonal_by_month[month]['productsAvailable'] += 1
                                    if category not in seasonal_by_month[month]['categories']:
                                        seasonal_by_month[month]['categories'][category] = 0
                                    seasonal_by_month[month]['categories'][category] += 1
                            else:
                                # Season wraps around year (e.g., Nov-Feb)
                                if month >= start_date.month or month <= end_date.month:
                                    seasonal_by_month[month]['productsAvailable'] += 1
                                    if category not in seasonal_by_month[month]['categories']:
                                        seasonal_by_month[month]['categories'][category] = 0
                                    seasonal_by_month[month]['categories'][category] += 1
                    except Exception as e:
                        print(f"Error parsing seasonal dates for product: {str(e)}")
                        continue
            else:
                category_trends[category]['nonSeasonalProducts'] += 1
                seasonal_vs_nonseasonal['nonSeasonal']['totalProducts'] += 1
                seasonal_vs_nonseasonal['nonSeasonal']['totalSales'] += total_sales
                seasonal_vs_nonseasonal['nonSeasonal']['totalRevenue'] += total_sales * price
                
                # Track by category within non-seasonal
                if category not in seasonal_vs_nonseasonal['nonSeasonal']['categories']:
                    seasonal_vs_nonseasonal['nonSeasonal']['categories'][category] = {
                        'products': 0,
                        'sales': 0,
                        'revenue': 0.0
                    }
                seasonal_vs_nonseasonal['nonSeasonal']['categories'][category]['products'] += 1
                seasonal_vs_nonseasonal['nonSeasonal']['categories'][category]['sales'] += total_sales
                seasonal_vs_nonseasonal['nonSeasonal']['categories'][category]['revenue'] += total_sales * price
        
        # Calculate averages for categories
        for category_data in category_trends.values():
            if category_data['totalProducts'] > 0:
                total_product_price = sum(
                    float(p.get('price', 0.0)) 
                    for p in products 
                    if p.get('category') == category_data['category']
                )
                category_data['averagePrice'] = round(
                    total_product_price / category_data['totalProducts'], 2
                )
        
        # Calculate averages for seasonal vs non-seasonal
        if seasonal_vs_nonseasonal['seasonal']['totalProducts'] > 0:
            total_seasonal_price = sum(
                float(p.get('price', 0.0))
                for p in products
                if p.get('seasonal', {}).get('isSeasonal', False)
            )
            seasonal_vs_nonseasonal['seasonal']['averagePrice'] = round(
                total_seasonal_price / seasonal_vs_nonseasonal['seasonal']['totalProducts'], 2
            )
        
        if seasonal_vs_nonseasonal['nonSeasonal']['totalProducts'] > 0:
            total_nonseasonal_price = sum(
                float(p.get('price', 0.0))
                for p in products
                if not p.get('seasonal', {}).get('isSeasonal', False)
            )
            seasonal_vs_nonseasonal['nonSeasonal']['averagePrice'] = round(
                total_nonseasonal_price / seasonal_vs_nonseasonal['nonSeasonal']['totalProducts'], 2
            )
        
        # Identify top performing categories by revenue
        top_categories = sorted(
            category_trends.values(),
            key=lambda x: x['totalRevenue'],
            reverse=True
        )[:5]  # Top 5 categories
        
        # Format seasonal availability by month for response
        seasonal_availability = []
        month_names = [
            'January', 'February', 'March', 'April', 'May', 'June',
            'July', 'August', 'September', 'October', 'November', 'December'
        ]
        
        for month in range(1, 13):
            seasonal_availability.append({
                'month': month,
                'monthName': month_names[month - 1],
                'productsAvailable': seasonal_by_month[month]['productsAvailable'],
                'categoriesAvailable': seasonal_by_month[month]['categories']
            })
        
        # Build trends response
        trends = {
            'categoryTrends': list(category_trends.values()),
            'seasonalVsNonSeasonal': {
                'seasonal': {
                    'totalProducts': seasonal_vs_nonseasonal['seasonal']['totalProducts'],
                    'totalSales': seasonal_vs_nonseasonal['seasonal']['totalSales'],
                    'totalRevenue': round(seasonal_vs_nonseasonal['seasonal']['totalRevenue'], 2),
                    'averagePrice': seasonal_vs_nonseasonal['seasonal']['averagePrice'],
                    'byCategory': seasonal_vs_nonseasonal['seasonal']['categories']
                },
                'nonSeasonal': {
                    'totalProducts': seasonal_vs_nonseasonal['nonSeasonal']['totalProducts'],
                    'totalSales': seasonal_vs_nonseasonal['nonSeasonal']['totalSales'],
                    'totalRevenue': round(seasonal_vs_nonseasonal['nonSeasonal']['totalRevenue'], 2),
                    'averagePrice': seasonal_vs_nonseasonal['nonSeasonal']['averagePrice'],
                    'byCategory': seasonal_vs_nonseasonal['nonSeasonal']['categories']
                }
            },
            'topCategories': top_categories,
            'seasonalAvailability': seasonal_availability,
            'summary': {
                'totalProducts': len(products),
                'totalCategories': len(category_trends),
                'seasonalProductsPercentage': round(
                    (seasonal_vs_nonseasonal['seasonal']['totalProducts'] / len(products) * 100)
                    if len(products) > 0 else 0, 2
                )
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
                'trends': trends
            }, default=decimal_to_float)
        }
    
    except Exception as e:
        # Catch-all for unexpected errors
        print(f"Unexpected error in seasonal trends: {str(e)}")
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
