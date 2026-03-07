"""
Input validation schemas and functions for RootTrust marketplace platform.
"""
import re
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr, Field, validator
from constants import (
    UserRole, ProductCategory, PromotionStatus, MIN_RATING, MAX_RATING,
    MIN_RELEASE_DURATION_DAYS, MAX_RELEASE_DURATION_DAYS
)
from exceptions import ValidationError


# Email validation regex
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

# Password requirements
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128


def validate_email(email: str) -> str:
    """
    Validate email format.
    
    Args:
        email: Email address to validate
        
    Returns:
        Validated email
        
    Raises:
        ValidationError: If email format is invalid
    """
    if not email or not EMAIL_REGEX.match(email):
        raise ValidationError("Invalid email format")
    return email.lower()


def validate_password(password: str) -> str:
    """
    Validate password strength.
    
    Args:
        password: Password to validate
        
    Returns:
        Validated password
        
    Raises:
        ValidationError: If password doesn't meet requirements
    """
    if not password:
        raise ValidationError("Password is required")
    
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValidationError(
            f"Password must be at least {MIN_PASSWORD_LENGTH} characters long"
        )
    
    if len(password) > MAX_PASSWORD_LENGTH:
        raise ValidationError(
            f"Password must not exceed {MAX_PASSWORD_LENGTH} characters"
        )
    
    return password


class UserRegistrationRequest(BaseModel):
    """User registration request validation schema."""
    email: EmailStr
    password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=MAX_PASSWORD_LENGTH)
    role: UserRole
    firstName: str = Field(min_length=1, max_length=100)
    lastName: str = Field(min_length=1, max_length=100)
    phone: str = Field(min_length=10, max_length=15)
    
    @validator('email')
    def validate_email_field(cls, v):
        return validate_email(v)
    
    @validator('password')
    def validate_password_field(cls, v):
        return validate_password(v)
    
    @validator('phone')
    def validate_phone_field(cls, v):
        # Remove common formatting characters
        cleaned = re.sub(r'[\s\-\(\)]', '', v)
        if not cleaned.isdigit():
            raise ValueError("Phone number must contain only digits")
        return cleaned


class UserLoginRequest(BaseModel):
    """User login request validation schema."""
    email: EmailStr
    password: str
    
    @validator('email')
    def validate_email_field(cls, v):
        return validate_email(v)


class ProductCreateRequest(BaseModel):
    """Product creation request validation schema."""
    name: str = Field(min_length=1, max_length=200)
    category: ProductCategory
    description: str = Field(min_length=10, max_length=5000)
    price: float = Field(gt=0)
    unit: str = Field(min_length=1, max_length=50)
    quantity: int = Field(ge=0)
    hasGITag: bool = False
    giTagName: Optional[str] = Field(None, max_length=200)
    giTagRegion: Optional[str] = Field(None, max_length=200)
    isSeasonal: bool = False
    seasonStart: Optional[str] = None  # ISO date string
    seasonEnd: Optional[str] = None  # ISO date string
    
    @validator('price')
    def validate_price_positive(cls, v):
        if v <= 0:
            raise ValueError("Price must be a positive number")
        return v
    
    @validator('giTagName')
    def validate_gi_tag_name(cls, v, values):
        if values.get('hasGITag') and not v:
            raise ValueError("GI tag name is required when hasGITag is true")
        return v
    
    @validator('seasonEnd')
    def validate_season_dates(cls, v, values):
        if values.get('isSeasonal'):
            if not values.get('seasonStart') or not v:
                raise ValueError("Season start and end dates are required for seasonal products")
        return v


class ProductUpdateRequest(BaseModel):
    """Product update request validation schema."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, min_length=10, max_length=5000)
    price: Optional[float] = Field(None, gt=0)
    quantity: Optional[int] = Field(None, ge=0)
    
    @validator('price')
    def validate_price_positive(cls, v):
        if v is not None and v <= 0:
            raise ValueError("Price must be a positive number")
        return v


class OrderCreateRequest(BaseModel):
    """Order creation request validation schema."""
    productId: str
    quantity: int = Field(gt=0)
    deliveryAddress: Dict[str, str]
    referralCode: Optional[str] = None
    
    @validator('deliveryAddress')
    def validate_delivery_address(cls, v):
        required_fields = ['street', 'city', 'state', 'pincode']
        for field in required_fields:
            if field not in v or not v[field]:
                raise ValueError(f"Delivery address must include {field}")
        return v


class ReviewCreateRequest(BaseModel):
    """Review creation request validation schema."""
    productId: str
    orderId: str
    rating: int = Field(ge=MIN_RATING, le=MAX_RATING)
    reviewText: str = Field(min_length=10, max_length=2000)
    photoUploadCount: int = Field(default=0, ge=0, le=5)
    
    @validator('rating')
    def validate_rating_range(cls, v):
        if v < MIN_RATING or v > MAX_RATING:
            raise ValueError(f"Rating must be between {MIN_RATING} and {MAX_RATING}")
        return v


class LimitedReleaseCreateRequest(BaseModel):
    """Limited release creation request validation schema."""
    productId: str
    releaseName: str = Field(min_length=1, max_length=200)
    quantityLimit: int = Field(gt=0)
    duration: int = Field(ge=MIN_RELEASE_DURATION_DAYS, le=MAX_RELEASE_DURATION_DAYS)
    
    @validator('quantityLimit')
    def validate_quantity_positive(cls, v):
        if v <= 0:
            raise ValueError("Quantity limit must be a positive integer")
        return v
    
    @validator('duration')
    def validate_duration_range(cls, v):
        if v < MIN_RELEASE_DURATION_DAYS or v > MAX_RELEASE_DURATION_DAYS:
            raise ValueError(
                f"Duration must be between {MIN_RELEASE_DURATION_DAYS} and {MAX_RELEASE_DURATION_DAYS} days"
            )
        return v


class PromotionCreateRequest(BaseModel):
    """Promotion creation request validation schema."""
    productId: str
    budget: float = Field(gt=0)
    duration: int = Field(gt=0)
    
    @validator('budget')
    def validate_budget_positive(cls, v):
        if v <= 0:
            raise ValueError("Budget must be a positive number")
        return v
    
    @validator('duration')
    def validate_duration_positive(cls, v):
        if v <= 0:
            raise ValueError("Duration must be a positive number of days")
        return v


class PromotionUpdateRequest(BaseModel):
    """Promotion update request validation schema."""
    status: PromotionStatus
    
    @validator('status')
    def validate_status(cls, v):
        allowed_statuses = [
            PromotionStatus.ACTIVE,
            PromotionStatus.PAUSED,
            PromotionStatus.CANCELLED,
            PromotionStatus.COMPLETED
        ]
        if v not in allowed_statuses:
            raise ValueError(f"Status must be one of: {', '.join([s.value for s in allowed_statuses])}")
        return v


class ReferralGenerateRequest(BaseModel):
    """Referral link generation request validation schema."""
    productId: str



class ReferralTrackConversionRequest(BaseModel):
    """Referral conversion tracking request validation schema."""
    referralCode: str
    orderId: str


class NotificationPreferencesUpdateRequest(BaseModel):
    """Notification preferences update request validation schema."""
    newProducts: Optional[bool] = None
    promotions: Optional[bool] = None
    orderUpdates: Optional[bool] = None
    reviewRequests: Optional[bool] = None
    limitedReleases: Optional[bool] = None
    farmerBonuses: Optional[bool] = None


class MarketplaceQueryParams(BaseModel):
    """Marketplace product listing query parameters validation schema."""
    category: Optional[ProductCategory] = None
    seasonal: Optional[bool] = None
    giTag: Optional[bool] = None
    search: Optional[str] = Field(None, max_length=200)
    limit: Optional[int] = Field(default=20, ge=1, le=100)
    cursor: Optional[str] = None


def validate_request_body(data: Dict[str, Any], schema_class: type) -> BaseModel:
    """
    Validate request body against a Pydantic schema.
    
    Args:
        data: Request body data
        schema_class: Pydantic model class to validate against
        
    Returns:
        Validated Pydantic model instance
        
    Raises:
        ValidationError: If validation fails
    """
    try:
        return schema_class(**data)
    except Exception as e:
        # Convert Pydantic validation errors to our ValidationError
        if hasattr(e, 'errors'):
            details = []
            for error in e.errors():
                field = '.'.join(str(loc) for loc in error['loc'])
                details.append({
                    'field': field,
                    'message': error['msg']
                })
            raise ValidationError("Request validation failed", details=details)
        else:
            raise ValidationError(str(e))
