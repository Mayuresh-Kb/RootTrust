"""
Product update Lambda handler for RootTrust marketplace.
Handles PUT /products/{productId} endpoint for farmers to update their products.
"""
import json
import os
from datetime import datetime
from typing import Dict, Any

# Import shared modules
import sys
sys.path.append('/opt/python')

from models import Product
from validators import ProductUpdateRequest, validate_request_body
from database import get_item, update_item
from auth import get_user_from_token
from constants import UserRole
from exceptions import (
    ValidationError, AuthenticationError, AuthorizationError,
    ResourceNotFoundError, ServiceUnavailableError
)


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for product update endpoint.
    
    Validates JWT token, farmer role, product ownership, and updates product record.
    
    Args:
        event: API Gateway event
        context: Lambda context
        
    Returns:
        API Gateway response with updated product
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
                        'message': 'Only farmers can update products'
                    }
                })
            }
        
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
        
        # Get existing product from DynamoDB
        existing_product = get_item(f"PRODUCT#{product_id}", "METADATA")
        
        if not existing_product:
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
        
        # Verify farmer owns the product
        if existing_product.get('farmerId') != user_id:
            return {
                'statusCode': 403,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'FORBIDDEN',
                        'message': 'You can only update your own products'
                    }
                })
            }
        
        # Parse and validate request body
        try:
            body = json.loads(event.get('body', '{}'))
        except json.JSONDecodeError:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'INVALID_JSON',
                        'message': 'Request body must be valid JSON'
                    }
                })
            }
        
        # Validate update data
        try:
            update_request = validate_request_body(body, ProductUpdateRequest)
        except ValidationError as e:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'VALIDATION_ERROR',
                        'message': e.message,
                        'details': e.details if hasattr(e, 'details') else []
                    }
                })
            }
        
        # Build update expression dynamically based on provided fields
        update_expression_parts = []
        expression_attribute_values = {}
        expression_attribute_names = {}
        
        # Always update the updatedAt timestamp
        update_expression_parts.append("#updatedAt = :updatedAt")
        expression_attribute_names['#updatedAt'] = 'updatedAt'
        expression_attribute_values[':updatedAt'] = datetime.utcnow().isoformat()
        
        # Add fields that were provided in the request
        if update_request.name is not None:
            update_expression_parts.append("#name = :name")
            expression_attribute_names['#name'] = 'name'
            expression_attribute_values[':name'] = update_request.name
        
        if update_request.description is not None:
            update_expression_parts.append("description = :description")
            expression_attribute_values[':description'] = update_request.description
        
        if update_request.price is not None:
            update_expression_parts.append("price = :price")
            expression_attribute_values[':price'] = update_request.price
        
        if update_request.quantity is not None:
            update_expression_parts.append("quantity = :quantity")
            expression_attribute_values[':quantity'] = update_request.quantity
        
        # Construct the full update expression
        update_expression = "SET " + ", ".join(update_expression_parts)
        
        # Update product in DynamoDB
        try:
            updated_product = update_item(
                pk=f"PRODUCT#{product_id}",
                sk="METADATA",
                update_expression=update_expression,
                expression_attribute_values=expression_attribute_values,
                expression_attribute_names=expression_attribute_names if expression_attribute_names else None
            )
        except Exception as e:
            print(f"Error updating product in DynamoDB: {str(e)}")
            return {
                'statusCode': 503,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'SERVICE_UNAVAILABLE',
                        'message': 'Failed to update product',
                        'details': str(e)
                    }
                })
            }
        
        # Return success response with updated product
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'productId': product_id,
                'message': 'Product updated successfully',
                'updatedFields': {
                    'name': update_request.name,
                    'description': update_request.description,
                    'price': update_request.price,
                    'quantity': update_request.quantity
                },
                'updatedAt': expression_attribute_values[':updatedAt']
            })
        }
    
    except Exception as e:
        # Catch-all for unexpected errors
        print(f"Unexpected error in product update: {str(e)}")
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
