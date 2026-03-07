"""
Review submission Lambda handler for RootTrust marketplace.
Handles POST /reviews endpoint for consumers to submit product reviews.
"""
import json
import os
import uuid
import boto3
from datetime import datetime
from typing import Dict, Any, List

# Import shared modules
import sys
sys.path.append('/opt/python')

from models import Review, ReviewPhoto
from validators import ReviewCreateRequest, validate_request_body
from database import get_item, put_item, query, update_item
from auth import get_user_from_token
from constants import UserRole, OrderStatus, MIN_RATING, MAX_RATING
from exceptions import (
    ValidationError, AuthenticationError, AuthorizationError,
    ResourceNotFoundError, ConflictError, UnprocessableEntityError,
    ServiceUnavailableError
)


# Initialize S3 client
s3_client = boto3.client('s3')


def generate_review_photo_presigned_urls(bucket_name: str, review_id: str, num_urls: int) -> List[Dict[str, Any]]:
    """
    Generate S3 pre-signed URLs for review photo uploads.
    
    Args:
        bucket_name: S3 bucket name
        review_id: Review ID for organizing uploads
        num_urls: Number of pre-signed URLs to generate
        
    Returns:
        List of pre-signed URL dictionaries with url and key
    """
    urls = []
    expiration = 900  # 15 minutes
    
    for i in range(num_urls):
        # Generate unique key for each photo
        photo_key = f"reviews/{review_id}/photos/photo-{i+1}-{uuid.uuid4().hex[:8]}.jpg"
        
        try:
            # Generate pre-signed URL for PUT operation
            presigned_url = s3_client.generate_presigned_url(
                'put_object',
                Params={
                    'Bucket': bucket_name,
                    'Key': photo_key,
                    'ContentType': 'image/jpeg',
                    'ContentLength': 5 * 1024 * 1024  # 5MB max
                },
                ExpiresIn=expiration
            )
            
            urls.append({
                'url': presigned_url,
                'key': photo_key,
                'expiresIn': expiration
            })
        except Exception as e:
            print(f"Error generating presigned URL: {str(e)}")
            raise ServiceUnavailableError('S3', f'Failed to generate upload URL: {str(e)}')
    
    return urls


def calculate_average_rating(product_pk: str) -> Dict[str, float]:
    """
    Calculate average rating for a product by querying all reviews.
    
    Args:
        product_pk: Product partition key (PRODUCT#{productId})
        
    Returns:
        Dictionary with averageRating and totalReviews
    """
    try:
        from boto3.dynamodb.conditions import Key
        
        # Query all reviews for the product
        result = query(
            key_condition_expression=Key('PK').eq(product_pk) & Key('SK').begins_with('REVIEW#')
        )
        
        reviews = result.get('Items', [])
        
        if not reviews:
            return {'averageRating': 0.0, 'totalReviews': 0}
        
        # Calculate average
        total_rating = sum(review.get('rating', 0) for review in reviews)
        average_rating = total_rating / len(reviews)
        
        return {
            'averageRating': round(average_rating, 2),
            'totalReviews': len(reviews)
        }
    except Exception as e:
        print(f"Error calculating average rating: {str(e)}")
        # Return current values on error
        return {'averageRating': 0.0, 'totalReviews': 0}


def calculate_farmer_average_rating(farmer_id: str) -> Dict[str, float]:
    """
    Calculate average rating for a farmer across all their products.
    
    Args:
        farmer_id: Farmer user ID
        
    Returns:
        Dictionary with averageRating and totalReviews
    """
    try:
        from boto3.dynamodb.conditions import Key
        
        # Query all reviews for the farmer using GSI2
        result = query(
            key_condition_expression=Key('GSI2PK').eq(f'FARMER#{farmer_id}'),
            index_name='GSI2'
        )
        
        reviews = result.get('Items', [])
        
        if not reviews:
            return {'averageRating': 0.0, 'totalReviews': 0}
        
        # Calculate average
        total_rating = sum(review.get('rating', 0) for review in reviews)
        average_rating = total_rating / len(reviews)
        
        return {
            'averageRating': round(average_rating, 2),
            'totalReviews': len(reviews)
        }
    except Exception as e:
        print(f"Error calculating farmer average rating: {str(e)}")
        # Return current values on error
        return {'averageRating': 0.0, 'totalReviews': 0}


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for review submission endpoint.
    
    Validates JWT token, consumer role authorization, purchase verification,
    creates review record, generates S3 pre-signed URLs for photos,
    and triggers rating aggregation.
    
    Args:
        event: API Gateway event
        context: Lambda context
        
    Returns:
        API Gateway response with reviewId and photoUploadUrls
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
            consumer_id = user_info['userId']
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
        
        # Verify consumer role
        if user_role != UserRole.CONSUMER.value:
            return {
                'statusCode': 403,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'FORBIDDEN',
                        'message': 'Only consumers can submit reviews'
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
        
        # Validate review data
        try:
            review_request = validate_request_body(body, ReviewCreateRequest)
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
        
        # Validate rating is integer between 1 and 5
        if not isinstance(review_request.rating, int) or review_request.rating < MIN_RATING or review_request.rating > MAX_RATING:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'VALIDATION_ERROR',
                        'message': f'Rating must be an integer between {MIN_RATING} and {MAX_RATING}',
                        'details': [{'field': 'rating', 'message': f'Must be an integer between {MIN_RATING} and {MAX_RATING}'}]
                    }
                })
            }
        
        # Query order to verify consumer has purchased the product
        order_pk = f"ORDER#{review_request.orderId}"
        order_sk = "METADATA"
        
        try:
            order_item = get_item(order_pk, order_sk)
        except Exception as e:
            print(f"Error querying order: {str(e)}")
            return {
                'statusCode': 503,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'SERVICE_UNAVAILABLE',
                        'message': 'Failed to query order',
                        'details': str(e)
                    }
                })
            }
        
        if not order_item:
            return {
                'statusCode': 404,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'RESOURCE_NOT_FOUND',
                        'message': f'Order with ID {review_request.orderId} not found'
                    }
                })
            }
        
        # Verify consumer owns the order
        if order_item.get('consumerId') != consumer_id:
            return {
                'statusCode': 403,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'FORBIDDEN',
                        'message': 'You can only review products you have purchased'
                    }
                })
            }
        
        # Verify order contains the product being reviewed
        if order_item.get('productId') != review_request.productId:
            return {
                'statusCode': 422,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'UNPROCESSABLE_ENTITY',
                        'message': 'The order does not contain the product being reviewed'
                    }
                })
            }
        
        # Query product to get farmer ID
        product_pk = f"PRODUCT#{review_request.productId}"
        product_sk = "METADATA"
        
        try:
            product_item = get_item(product_pk, product_sk)
        except Exception as e:
            print(f"Error querying product: {str(e)}")
            return {
                'statusCode': 503,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'SERVICE_UNAVAILABLE',
                        'message': 'Failed to query product',
                        'details': str(e)
                    }
                })
            }
        
        if not product_item:
            return {
                'statusCode': 404,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'RESOURCE_NOT_FOUND',
                        'message': f'Product with ID {review_request.productId} not found'
                    }
                })
            }
        
        farmer_id = product_item.get('farmerId')
        if not farmer_id:
            return {
                'statusCode': 500,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'INTERNAL_ERROR',
                        'message': 'Product does not have an associated farmer'
                    }
                })
            }
        
        # Generate unique review ID
        review_id = str(uuid.uuid4())
        now = datetime.utcnow()
        
        # Create Review model instance
        review = Review(
            reviewId=review_id,
            productId=review_request.productId,
            farmerId=farmer_id,
            consumerId=consumer_id,
            orderId=review_request.orderId,
            rating=review_request.rating,
            reviewText=review_request.reviewText,
            photos=[],  # Photos will be added after upload
            helpful=0,
            createdAt=now
        )
        
        # Convert to DynamoDB item format
        review_dict = review.dict()
        review_dict['createdAt'] = review_dict['createdAt'].isoformat()
        
        # Store review in DynamoDB
        try:
            put_item(review_dict)
        except Exception as e:
            print(f"Error storing review in DynamoDB: {str(e)}")
            return {
                'statusCode': 503,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': {
                        'code': 'SERVICE_UNAVAILABLE',
                        'message': 'Failed to create review',
                        'details': str(e)
                    }
                })
            }
        
        # Generate S3 pre-signed URLs for photo uploads if requested
        photo_upload_urls = []
        if review_request.photoUploadCount > 0:
            bucket_name = os.environ.get('BUCKET_NAME')
            if bucket_name:
                try:
                    photo_upload_urls = generate_review_photo_presigned_urls(
                        bucket_name,
                        review_id,
                        review_request.photoUploadCount
                    )
                except ServiceUnavailableError as e:
                    # Log error but don't fail the request - review is already created
                    print(f"Warning: Failed to generate presigned URLs: {str(e)}")
                    photo_upload_urls = []
        
        # Trigger rating aggregation - update product average rating
        try:
            product_rating_stats = calculate_average_rating(product_pk)
            update_item(
                pk=product_pk,
                sk=product_sk,
                update_expression='SET averageRating = :avg, totalReviews = :total, updatedAt = :updated',
                expression_attribute_values={
                    ':avg': product_rating_stats['averageRating'],
                    ':total': product_rating_stats['totalReviews'],
                    ':updated': now.isoformat()
                }
            )
        except Exception as e:
            # Log error but don't fail the request - review is already created
            print(f"Warning: Failed to update product rating: {str(e)}")
        
        # Trigger rating aggregation - update farmer average rating
        try:
            farmer_rating_stats = calculate_farmer_average_rating(farmer_id)
            farmer_pk = f"USER#{farmer_id}"
            farmer_sk = "PROFILE"
            
            update_item(
                pk=farmer_pk,
                sk=farmer_sk,
                update_expression='SET farmerProfile.averageRating = :avg, farmerProfile.totalReviews = :total',
                expression_attribute_values={
                    ':avg': farmer_rating_stats['averageRating'],
                    ':total': farmer_rating_stats['totalReviews']
                }
            )
        except Exception as e:
            # Log error but don't fail the request - review is already created
            print(f"Warning: Failed to update farmer rating: {str(e)}")
        
        # Return success response
        return {
            'statusCode': 201,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'reviewId': review_id,
                'photoUploadUrls': photo_upload_urls,
                'message': 'Review submitted successfully'
            })
        }
    
    except Exception as e:
        # Catch-all for unexpected errors
        print(f"Unexpected error in review submission: {str(e)}")
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
