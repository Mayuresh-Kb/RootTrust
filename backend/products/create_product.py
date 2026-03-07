"""
Product creation Lambda handler for RootTrust marketplace.
Handles POST /products endpoint for farmers to create new products.
"""
import json
import os
import uuid
import boto3
from datetime import datetime, timedelta
from typing import Dict, Any

# Import shared modules
import sys
sys.path.append('/opt/python')

from models import Product, GITag, SeasonalInfo
from validators import ProductCreateRequest, validate_request_body
from database import put_item, get_item
from auth import get_user_from_token
from constants import UserRole, VerificationStatus, ProductCategory
from exceptions import (
    ValidationError, AuthenticationError, AuthorizationError,
    ResourceNotFoundError, ServiceUnavailableError
)


# Initialize S3 client
s3_client = boto3.client('s3')


def generate_presigned_urls(bucket_name: str, product_id: str, num_urls: int = 5) -> list:
    """
    Generate S3 pre-signed URLs for image uploads.
    
    Args:
        bucket_name: S3 bucket name
        product_id: Product ID for organizing uploads
        num_urls: Number of pre-signed URLs to generate
        
    Returns:
        List of pre-signed URL dictionaries with url and key
    """
    urls = []
    expiration = 900  # 15 minutes
    
    for i in range(num_urls):
        # Generate unique key for each image
        image_key = f"products/{product_id}/images/image-{i+1}-{uuid.uuid4().hex[:8]}.jpg"
        
        try:
            # Generate pre-signed URL for PUT operation
            presigned_url = s3_client.generate_presigned_url(
                'put_object',
                Params={
                    'Bucket': bucket_name,
                    'Key': image_key,
                    'ContentType': 'image/jpeg',
                    'ContentLength': 5 * 1024 * 1024  # 5MB max
                },
                ExpiresIn=expiration
            )
            
            urls.append({
                'url': presigned_url,
                'key': image_key,
                'expiresIn': expiration
            })
        except Exception as e:
            print(f"Error generating presigned URL: {str(e)}")
            raise ServiceUnavailableError('S3', f'Failed to generate upload URL: {str(e)}')
    
    return urls


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for product creation endpoint.
    
    Validates JWT token, farmer role, product data, and creates product record.
    Generates S3 pre-signed URLs for image uploads.
    
    Args:
        event: API Gateway event
        context: Lambda context
        
    Returns:
        API Gateway response with productId, status, and uploadUrls
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
                        'message': 'Only farmers can create products'
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
        
        # Validate product data
        try:
            product_request = validate_request_body(body, ProductCreateRequest)
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
        
        # Generate unique product ID
        product_id = str(uuid.uuid4())
        
        # Get current timestamp
        now = datetime.utcnow()
        
        # Build GI tag object
        gi_tag = GITag(
            hasTag=product_request.hasGITag,
            tagName=product_request.giTagName if product_request.hasGITag else None,
            region=product_request.giTagRegion if product_request.hasGITag else None
        )
        
        # Build seasonal info object
        seasonal_info = SeasonalInfo(
            isSeasonal=product_request.isSeasonal,
            seasonStart=datetime.fromisoformat(product_request.seasonStart) if product_request.seasonStart else None,
            seasonEnd=datetime.fromisoformat(product_request.seasonEnd) if product_request.seasonEnd else None
        )
        
        # Create Product model instance
        product = Product(
            productId=product_id,
            farmerId=user_id,
            name=product_request.name,
            category=product_request.category,
            description=product_request.description,
            price=product_request.price,
            unit=product_request.unit,
            giTag=gi_tag,
            seasonal=seasonal_info,
            images=[],  # Images will be added after upload
            verificationStatus=VerificationStatus.PENDING,
            quantity=product_request.quantity,
            createdAt=now,
            updatedAt=now
        )
        
        # Convert to DynamoDB item format
        product_dict = product.dict()
        
        # Convert datetime objects to ISO strings for DynamoDB
        product_dict['createdAt'] = product_dict['createdAt'].isoformat()
        product_dict['updatedAt'] = product_dict['updatedAt'].isoformat()
        if product_dict['seasonal']['seasonStart']:
            product_dict['seasonal']['seasonStart'] = product_dict['seasonal']['seasonStart'].isoformat()
        if product_dict['seasonal']['seasonEnd']:
            product_dict['seasonal']['seasonEnd'] = product_dict['seasonal']['seasonEnd'].isoformat()
        
        # Convert enums to strings
        product_dict['category'] = product_dict['category'].value if hasattr(product_dict['category'], 'value') else product_dict['category']
        product_dict['verificationStatus'] = product_dict['verificationStatus'].value if hasattr(product_dict['verificationStatus'], 'value') else product_dict['verificationStatus']
        
        # Store product in DynamoDB
        try:
            put_item(product_dict)
        except Exception as e:
            print(f"Error storing product in DynamoDB: {str(e)}")
            return {
                'statusCode': 503,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'SERVICE_UNAVAILABLE',
                        'message': 'Failed to create product',
                        'details': str(e)
                    }
                })
            }
        
        # Generate S3 pre-signed URLs for image uploads
        bucket_name = os.environ.get('BUCKET_NAME')
        if not bucket_name:
            print("Warning: BUCKET_NAME environment variable not set")
            upload_urls = []
        else:
            try:
                upload_urls = generate_presigned_urls(bucket_name, product_id, num_urls=5)
            except ServiceUnavailableError as e:
                # Log error but don't fail the request - farmer can upload images later
                print(f"Warning: Failed to generate presigned URLs: {str(e)}")
                upload_urls = []
        
        # Return success response
        return {
            'statusCode': 201,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'productId': product_id,
                'status': VerificationStatus.PENDING.value,
                'uploadUrls': upload_urls,
                'message': 'Product created successfully'
            })
        }
    
    except Exception as e:
        # Catch-all for unexpected errors
        print(f"Unexpected error in product creation: {str(e)}")
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
