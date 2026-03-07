"""
Active promotions listing Lambda handler for RootTrust marketplace.
Handles GET /promotions endpoint to list all active promotions.
"""
import json
import os
from typing import Dict, Any
from boto3.dynamodb.conditions import Key

# Import shared modules
import sys
sys.path.append('/opt/python')

from database import query, get_item
from constants import PromotionStatus
from exceptions import ServiceUnavailableError


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for active promotions listing endpoint.
    
    Queries GSI3 with GSI3PK=STATUS#active to retrieve all active promotions.
    Returns active promotions with product details.
    
    Args:
        event: API Gateway event
        context: Lambda context
        
    Returns:
        API Gateway response with active promotions array
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
        
        # Query GSI3 for active promotions
        try:
            gsi3_pk = f"STATUS#{PromotionStatus.ACTIVE.value}"
            
            result = query(
                key_condition_expression=Key('GSI3PK').eq(gsi3_pk),
                index_name='GSI3',
                limit=limit,
                exclusive_start_key=exclusive_start_key,
                scan_index_forward=False  # Most recent first (by endDate)
            )
            
            promotions = result.get('Items', [])
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
                        'message': 'Failed to query promotions',
                        'details': str(e)
                    }
                })
            }
        except Exception as e:
            print(f"Error querying promotions: {str(e)}")
            return {
                'statusCode': 503,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'SERVICE_UNAVAILABLE',
                        'message': 'Failed to query promotions',
                        'details': str(e)
                    }
                })
            }
        
        # Enrich promotions with product details
        enriched_promotions = []
        for promotion in promotions:
            try:
                # Query product details
                product_id = promotion.get('productId')
                if product_id:
                    product = get_item(f"PRODUCT#{product_id}", "METADATA")
                    
                    if product:
                        # Add product details to promotion
                        enriched_promotion = {
                            'promotionId': promotion.get('promotionId'),
                            'farmerId': promotion.get('farmerId'),
                            'productId': product_id,
                            'budget': promotion.get('budget'),
                            'duration': promotion.get('duration'),
                            'status': promotion.get('status'),
                            'startDate': promotion.get('startDate'),
                            'endDate': promotion.get('endDate'),
                            'aiGeneratedAdCopy': promotion.get('aiGeneratedAdCopy'),
                            'metrics': promotion.get('metrics', {
                                'views': 0,
                                'clicks': 0,
                                'conversions': 0,
                                'spent': 0.0
                            }),
                            'product': {
                                'name': product.get('name'),
                                'category': product.get('category'),
                                'price': product.get('price'),
                                'images': product.get('images', []),
                                'averageRating': product.get('averageRating', 0),
                                'giTag': product.get('giTag', {})
                            }
                        }
                        enriched_promotions.append(enriched_promotion)
                    else:
                        # Product not found, skip this promotion
                        print(f"Product {product_id} not found for promotion {promotion.get('promotionId')}")
                else:
                    # No product ID, skip
                    print(f"Promotion {promotion.get('promotionId')} has no productId")
            
            except Exception as e:
                # Log error but continue with other promotions
                print(f"Error enriching promotion {promotion.get('promotionId')}: {str(e)}")
                continue
        
        # Prepare response
        response_body = {
            'promotions': enriched_promotions,
            'count': len(enriched_promotions)
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
        print(f"Unexpected error in active promotions listing: {str(e)}")
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
