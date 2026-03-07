"""
Pydantic data models for RootTrust marketplace platform.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, validator
from backend.shared.constants import (
    UserRole, ProductCategory, OrderStatus, PaymentStatus,
    VerificationStatus, PromotionStatus, LimitedReleaseStatus,
    PaymentMethod, PaymentGateway, MIN_RATING, MAX_RATING
)


class Address(BaseModel):
    """Address model."""
    street: str
    city: str
    state: str
    pincode: str


class GITag(BaseModel):
    """Geographical Indication tag model."""
    hasTag: bool
    tagName: Optional[str] = None
    region: Optional[str] = None


class SeasonalInfo(BaseModel):
    """Seasonal product information."""
    isSeasonal: bool
    seasonStart: Optional[datetime] = None
    seasonEnd: Optional[datetime] = None


class ProductImage(BaseModel):
    """Product image model."""
    url: str
    isPrimary: bool = False


class NotificationPreferences(BaseModel):
    """User notification preferences."""
    newProducts: bool = True
    promotions: bool = True
    orderUpdates: bool = True
    reviewRequests: bool = True
    limitedReleases: bool = True
    farmerBonuses: bool = True


class FarmerProfile(BaseModel):
    """Farmer-specific profile data."""
    farmName: str
    farmLocation: str
    certifications: List[str] = []
    averageRating: float = 0.0
    totalReviews: int = 0
    totalSales: int = 0
    consecutiveSalesStreak: int = 0
    bonusesEarned: float = 0.0
    featuredStatus: bool = False
    accountBalance: float = 0.0


class ConsumerProfile(BaseModel):
    """Consumer-specific profile data."""
    referralCode: str
    referralRewardBalance: float = 0.0
    totalOrders: int = 0
    followedFarmers: List[str] = []


class User(BaseModel):
    """User model."""
    userId: str
    email: EmailStr
    passwordHash: str
    role: UserRole
    firstName: str
    lastName: str
    phone: str
    address: Optional[Address] = None
    createdAt: datetime
    emailVerified: bool = False
    notificationPreferences: NotificationPreferences = NotificationPreferences()
    farmerProfile: Optional[FarmerProfile] = None
    consumerProfile: Optional[ConsumerProfile] = None
    
    # DynamoDB keys
    PK: str = ""
    SK: str = "PROFILE"
    EntityType: str = "User"
    GSI2PK: str = ""
    GSI2SK: str = ""
    
    def __init__(self, **data):
        super().__init__(**data)
        if not self.PK:
            self.PK = f"USER#{self.userId}"
        if not self.GSI2PK:
            self.GSI2PK = f"ROLE#{self.role.value}"
        if not self.GSI2SK:
            self.GSI2SK = f"USER#{self.createdAt.isoformat()}"


class Product(BaseModel):
    """Product model."""
    productId: str
    farmerId: str
    name: str
    category: ProductCategory
    description: str
    price: float = Field(gt=0, description="Price must be positive")
    unit: str
    giTag: GITag
    seasonal: SeasonalInfo
    images: List[ProductImage] = []
    invoiceDocumentUrl: Optional[str] = None
    verificationStatus: VerificationStatus = VerificationStatus.PENDING
    fraudRiskScore: Optional[float] = Field(None, ge=0, le=100)
    authenticityConfidence: Optional[float] = Field(None, ge=0, le=100)
    aiExplanation: Optional[str] = None
    predictedMarketPrice: Optional[float] = None
    quantity: int = Field(ge=0)
    averageRating: float = Field(default=0.0, ge=0, le=5)
    totalReviews: int = 0
    totalSales: int = 0
    viewCount: int = 0
    currentViewers: int = 0
    recentPurchaseCount: int = 0
    createdAt: datetime
    updatedAt: datetime
    
    # DynamoDB keys
    PK: str = ""
    SK: str = "METADATA"
    EntityType: str = "Product"
    GSI1PK: str = ""
    GSI1SK: str = ""
    GSI2PK: str = ""
    GSI2SK: str = ""
    GSI3PK: str = ""
    GSI3SK: str = ""
    
    def __init__(self, **data):
        super().__init__(**data)
        if not self.PK:
            self.PK = f"PRODUCT#{self.productId}"
        if not self.GSI1PK:
            self.GSI1PK = f"CATEGORY#{self.category.value}"
        if not self.GSI1SK:
            self.GSI1SK = f"PRODUCT#{self.createdAt.isoformat()}"
        if not self.GSI2PK:
            self.GSI2PK = f"FARMER#{self.farmerId}"
        if not self.GSI2SK:
            self.GSI2SK = f"PRODUCT#{self.createdAt.isoformat()}"
        if not self.GSI3PK:
            self.GSI3PK = f"STATUS#{self.verificationStatus.value}"
        if not self.GSI3SK:
            self.GSI3SK = f"PRODUCT#{self.createdAt.isoformat()}"
    
    @validator('price')
    def validate_price(cls, v):
        if v <= 0:
            raise ValueError('Price must be a positive number')
        return v


class Order(BaseModel):
    """Order model."""
    orderId: str
    consumerId: str
    farmerId: str
    productId: str
    productName: str
    quantity: int = Field(gt=0)
    unitPrice: float = Field(gt=0)
    totalAmount: float = Field(gt=0)
    status: OrderStatus = OrderStatus.PENDING
    paymentStatus: PaymentStatus = PaymentStatus.PENDING
    transactionId: Optional[str] = None
    deliveryAddress: Address
    estimatedDeliveryDate: datetime
    actualDeliveryDate: Optional[datetime] = None
    referralCode: Optional[str] = None
    createdAt: datetime
    updatedAt: datetime
    
    # DynamoDB keys
    PK: str = ""
    SK: str = "METADATA"
    EntityType: str = "Order"
    GSI2PK: str = ""
    GSI2SK: str = ""
    GSI3PK: str = ""
    GSI3SK: str = ""
    
    def __init__(self, **data):
        super().__init__(**data)
        if not self.PK:
            self.PK = f"ORDER#{self.orderId}"
        if not self.GSI2PK:
            self.GSI2PK = f"CONSUMER#{self.consumerId}"
        if not self.GSI2SK:
            self.GSI2SK = f"ORDER#{self.createdAt.isoformat()}"
        if not self.GSI3PK:
            self.GSI3PK = f"FARMER#{self.farmerId}"
        if not self.GSI3SK:
            self.GSI3SK = f"ORDER#{self.createdAt.isoformat()}"


class Transaction(BaseModel):
    """Payment transaction model."""
    transactionId: str
    orderId: str
    amount: float = Field(gt=0)
    currency: str = "INR"
    paymentMethod: PaymentMethod
    paymentGateway: PaymentGateway
    status: PaymentStatus
    gatewayResponse: dict = {}
    createdAt: datetime
    completedAt: Optional[datetime] = None
    
    # DynamoDB keys
    PK: str = ""
    SK: str = "METADATA"
    EntityType: str = "Transaction"
    GSI2PK: str = ""
    GSI2SK: str = ""
    
    def __init__(self, **data):
        super().__init__(**data)
        if not self.PK:
            self.PK = f"TRANSACTION#{self.transactionId}"
        if not self.GSI2PK:
            self.GSI2PK = f"ORDER#{self.orderId}"
        if not self.GSI2SK:
            self.GSI2SK = f"TRANSACTION#{self.createdAt.isoformat()}"


class ReviewPhoto(BaseModel):
    """Review photo model."""
    url: str
    caption: Optional[str] = None


class Review(BaseModel):
    """Review model."""
    reviewId: str
    productId: str
    farmerId: str
    consumerId: str
    orderId: str
    rating: int = Field(ge=MIN_RATING, le=MAX_RATING)
    reviewText: str
    photos: List[ReviewPhoto] = []
    helpful: int = 0
    createdAt: datetime
    
    # DynamoDB keys
    PK: str = ""
    SK: str = ""
    EntityType: str = "Review"
    GSI2PK: str = ""
    GSI2SK: str = ""
    GSI3PK: str = ""
    GSI3SK: str = ""
    
    def __init__(self, **data):
        super().__init__(**data)
        if not self.PK:
            self.PK = f"PRODUCT#{self.productId}"
        if not self.SK:
            self.SK = f"REVIEW#{self.reviewId}"
        if not self.GSI2PK:
            self.GSI2PK = f"FARMER#{self.farmerId}"
        if not self.GSI2SK:
            self.GSI2SK = f"REVIEW#{self.createdAt.isoformat()}"
        if not self.GSI3PK:
            self.GSI3PK = f"CONSUMER#{self.consumerId}"
        if not self.GSI3SK:
            self.GSI3SK = f"REVIEW#{self.createdAt.isoformat()}"
    
    @validator('rating')
    def validate_rating(cls, v):
        if v < MIN_RATING or v > MAX_RATING:
            raise ValueError(f'Rating must be between {MIN_RATING} and {MAX_RATING}')
        return v


class ReferralConversion(BaseModel):
    """Referral conversion record."""
    referredUserId: str
    orderId: str
    rewardAmount: float
    convertedAt: datetime


class Referral(BaseModel):
    """Referral model."""
    referralCode: str
    referrerId: str
    productId: str
    conversions: List[ReferralConversion] = []
    totalConversions: int = 0
    totalRewards: float = 0.0
    createdAt: datetime
    
    # DynamoDB keys
    PK: str = ""
    SK: str = "METADATA"
    EntityType: str = "Referral"
    GSI2PK: str = ""
    GSI2SK: str = ""
    
    def __init__(self, **data):
        super().__init__(**data)
        if not self.PK:
            self.PK = f"REFERRAL#{self.referralCode}"
        if not self.GSI2PK:
            self.GSI2PK = f"REFERRER#{self.referrerId}"
        if not self.GSI2SK:
            self.GSI2SK = f"REFERRAL#{self.createdAt.isoformat()}"


class PromotionMetrics(BaseModel):
    """Promotion performance metrics."""
    views: int = 0
    clicks: int = 0
    conversions: int = 0
    spent: float = 0.0


class Promotion(BaseModel):
    """Promotion model."""
    promotionId: str
    farmerId: str
    productId: str
    budget: float = Field(gt=0)
    duration: int = Field(gt=0)
    status: PromotionStatus = PromotionStatus.ACTIVE
    startDate: datetime
    endDate: datetime
    metrics: PromotionMetrics = PromotionMetrics()
    aiGeneratedAdCopy: Optional[str] = None
    createdAt: datetime
    
    # DynamoDB keys
    PK: str = ""
    SK: str = "METADATA"
    EntityType: str = "Promotion"
    GSI2PK: str = ""
    GSI2SK: str = ""
    GSI3PK: str = ""
    GSI3SK: str = ""
    
    def __init__(self, **data):
        super().__init__(**data)
        if not self.PK:
            self.PK = f"PROMOTION#{self.promotionId}"
        if not self.GSI2PK:
            self.GSI2PK = f"FARMER#{self.farmerId}"
        if not self.GSI2SK:
            self.GSI2SK = f"PROMOTION#{self.startDate.isoformat()}"
        if not self.GSI3PK:
            self.GSI3PK = f"STATUS#{self.status.value}"
        if not self.GSI3SK:
            self.GSI3SK = f"PROMOTION#{self.endDate.isoformat()}"


class LimitedRelease(BaseModel):
    """Limited release model."""
    releaseId: str
    farmerId: str
    productId: str
    releaseName: str
    quantityLimit: int = Field(gt=0)
    quantityRemaining: int = Field(ge=0)
    duration: int = Field(ge=1, le=30)
    startDate: datetime
    endDate: datetime
    status: LimitedReleaseStatus = LimitedReleaseStatus.ACTIVE
    subscriberNotificationsSent: bool = False
    createdAt: datetime
    
    # DynamoDB keys
    PK: str = ""
    SK: str = "METADATA"
    EntityType: str = "LimitedRelease"
    GSI2PK: str = ""
    GSI2SK: str = ""
    GSI3PK: str = ""
    GSI3SK: str = ""
    
    def __init__(self, **data):
        super().__init__(**data)
        if not self.PK:
            self.PK = f"LIMITED_RELEASE#{self.releaseId}"
        if not self.GSI2PK:
            self.GSI2PK = f"FARMER#{self.farmerId}"
        if not self.GSI2SK:
            self.GSI2SK = f"RELEASE#{self.startDate.isoformat()}"
        if not self.GSI3PK:
            self.GSI3PK = f"STATUS#{self.status.value}"
        if not self.GSI3SK:
            self.GSI3SK = f"RELEASE#{self.endDate.isoformat()}"
    
    @validator('duration')
    def validate_duration(cls, v):
        if v < 1 or v > 30:
            raise ValueError('Duration must be between 1 and 30 days')
        return v


class NotificationPreferenceEntity(BaseModel):
    """Notification preference entity for DynamoDB."""
    userId: str
    emailNotifications: NotificationPreferences
    unsubscribedAt: Optional[datetime] = None
    updatedAt: datetime
    
    # DynamoDB keys
    PK: str = ""
    SK: str = "NOTIFICATIONS"
    EntityType: str = "NotificationPreference"
    
    def __init__(self, **data):
        super().__init__(**data)
        if not self.PK:
            self.PK = f"USER#{self.userId}"
