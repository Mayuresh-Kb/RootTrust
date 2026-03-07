"""
AI Verification Status Lambda Function
GET /ai/verification-status/{productId}

This function retrieves the current verification status and scores for a product.
"""
import json
import os
from typing import Dict, Any

# Import shared modules (available via Lambda Layer)
from database import get_item
from auth import validate_jwt_token
from constants import UserRole
from exceptions import ResourceNotFoundError


def handler(event, context):
    """
    Lambda handler for verification status check endpoint.
    
    GET /ai/verification-status/{productId}
    
    Response:
    {
        "productId": "uuid",
        "verificationStatus": "approved|pending|flagged|rejected",
        "fraudRiskScore": 45.5,
        "authenticityConfidence": 85.0,
        "predictedMarketPrice": 120.50,
        "aiExplanation": "Product appears authentic..."
    }
    """
    try:
        print(f"Event: {json.dumps(event)}")
        
        # Extract JWT token from headers (optional for this endpoint - public data)
        headers = event.get('headers', {})
        auth_header = headers.get('Authorization') or headers.get('authorization')
        
        # If token provided, verify it (but don't require it)
        user_data = None
        if auth_header:
            try:
                token = auth_header.replace('Bearer ', '')
                user_data = validate_jwt_token(token)
            except Exception as e:
                print(f"Token verification failed: {str(e)}")
                # Continue without authentication - verification status is public
        
        # Extract productId from path parameters
        path_parameters = event.get('pathParameters', {})
        product_id = path_parameters.get('productId')
        
        if not product_id:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'error': {
                        'code': 'VALIDATION_ERROR',
                        'message': 'productId is required in path'
                    }
                })
            }
        
        # Retrieve product from DynamoDB
        product_item = get_item(
            pk=f"PRODUCT#{product_id}",
            sk="METADATA"
        )
        
        if not product_item:
            return {
                'statusCode': 404,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'error': {
                        'code': 'NOT_FOUND',
                        'message': f'Product {product_id} not found'
                    }
                })
            }
        
        # Extract verification data from product record
        verification_status = product_item.get('verificationStatus', 'pending')
        fraud_risk_score = product_item.get('fraudRiskScore')
        authenticity_confidence = product_item.get('authenticityConfidence')
        predicted_market_price = product_item.get('predictedMarketPrice')
        ai_explanation = product_item.get('aiExplanation')
        
        # Build response
        response_data = {
            'productId': product_id,
            'verificationStatus': verification_status
        }
        
        # Include verification details if available
        if fraud_risk_score is not None:
            response_data['fraudRiskScore'] = float(fraud_risk_score)
        
        if authenticity_confidence is not None:
            response_data['authenticityConfidence'] = float(authenticity_confidence)
        
        if predicted_market_price is not None:
            response_data['predictedMarketPrice'] = float(predicted_market_price)
        
        if ai_explanation:
            response_data['aiExplanation'] = ai_explanation
        
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps(response_data)
        }
        
    except ResourceNotFoundError as e:
        return {
            'statusCode': 404,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'error': {
                    'code': 'NOT_FOUND',
                    'message': str(e)
                }
            })
        }
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'error': {
                    'code': 'INTERNAL_ERROR',
                    'message': 'An unexpected error occurred'
                }
            })
        }
