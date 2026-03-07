"""
Product image upload handler for RootTrust marketplace.
Handles POST /products/{productId}/images endpoint to update product with uploaded image URLs.
"""
import json
import os
from datetime import datetime
from typing import Dict, Any, List

# Import shared modules
import sys
sys.path.append('/opt/python')

from database import get_item, update_item
from auth import get_user_from_token
from constants import UserRole
from exceptions import (
    ValidationError, AuthenticationError, AuthorizationError,
    ResourceNotFoundError, ServiceUnavailableError
)


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for product image upload completion.
    
    Updates product record with image URLs after S3 upload.
    Sets isPrimary flag for the first image.
    
    Args:
        event: API Gateway event
        context: Lambda context
        
    Returns:
        API Gateway response with updated product images
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
                        'message': 'Only farmers can update product images'
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
                        'message': 'You can only update your own product images'
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
        
        # Validate image URLs
        image_urls = body.get('imageUrls', [])
        
        if not isinstance(image_urls, list):
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'VALIDATION_ERROR',
                        'message': 'imageUrls must be an array'
                    }
                })
            }
        
        if not image_urls:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'VALIDATION_ERROR',
                        'message': 'At least one image URL is required'
                    }
                })
            }
        
        # Build image objects with isPrimary flag
        # Get existing images to preserve them
        existing_images = existing_product.get('images', [])
        
        # Create new image objects
        new_images = []
        for idx, url in enumerate(image_urls):
            if not isinstance(url, str) or not url.strip():
                return {
                    'statusCode': 400,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({
                        'error': {
                            'code': 'VALIDATION_ERROR',
                            'message': f'Invalid image URL at index {idx}'
                        }
                    })
                }
            
            # First image is primary if no existing images, otherwise not primary
            is_primary = (idx == 0 and len(existing_images) == 0)
            
            new_images.append({
                'url': url.strip(),
                'isPrimary': is_primary
            })
        
        # Merge with existing images (new images are added to the end)
        all_images = existing_images + new_images
        
        # Update product in DynamoDB
        try:
            updated_product = update_item(
                pk=f"PRODUCT#{product_id}",
                sk="METADATA",
                update_expression="SET images = :images, updatedAt = :updatedAt",
                expression_attribute_values={
                    ':images': all_images,
                    ':updatedAt': datetime.utcnow().isoformat()
                }
            )
        except Exception as e:
            print(f"Error updating product images in DynamoDB: {str(e)}")
            return {
                'statusCode': 503,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'SERVICE_UNAVAILABLE',
                        'message': 'Failed to update product images',
                        'details': str(e)
                    }
                })
            }
        
        # Return success response
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'productId': product_id,
                'message': 'Product images updated successfully',
                'images': all_images,
                'updatedAt': updated_product.get('updatedAt')
            })
        }
    
    except Exception as e:
        # Catch-all for unexpected errors
        print(f"Unexpected error in product image update: {str(e)}")
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
