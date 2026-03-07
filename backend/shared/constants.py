"""
Constants and enums for RootTrust marketplace platform.
"""
from enum import Enum


class UserRole(str, Enum):
    """User role types."""
    FARMER = "farmer"
    CONSUMER = "consumer"


class ProductCategory(str, Enum):
    """Product category types."""
    VEGETABLES = "vegetables"
    FRUITS = "fruits"
    GRAINS = "grains"
    SPICES = "spices"
    DAIRY = "dairy"


class OrderStatus(str, Enum):
    """Order status types."""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    FAILED = "failed"


class PaymentStatus(str, Enum):
    """Payment status types."""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class VerificationStatus(str, Enum):
    """Product verification status types."""
    PENDING = "pending"
    APPROVED = "approved"
    FLAGGED = "flagged"
    REJECTED = "rejected"


class PromotionStatus(str, Enum):
    """Promotion status types."""
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class LimitedReleaseStatus(str, Enum):
    """Limited release status types."""
    SCHEDULED = "scheduled"
    ACTIVE = "active"
    SOLD_OUT = "sold_out"
    EXPIRED = "expired"


class PaymentMethod(str, Enum):
    """Payment method types."""
    UPI = "upi"
    CARD = "card"
    NETBANKING = "netbanking"


class PaymentGateway(str, Enum):
    """Payment gateway types."""
    RAZORPAY = "razorpay"
    STRIPE = "stripe"


# JWT Configuration
JWT_EXPIRATION_HOURS = 24

# Fraud Detection Thresholds
FRAUD_RISK_THRESHOLD = 70  # Products with score > 70 are flagged

# Pagination
DEFAULT_PAGE_LIMIT = 20
MAX_PAGE_LIMIT = 100

# File Upload Limits
MAX_IMAGE_SIZE_MB = 5
MAX_IMAGES_PER_PRODUCT = 5
ALLOWED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/jpg"]

# Limited Release Constraints
MIN_RELEASE_DURATION_DAYS = 1
MAX_RELEASE_DURATION_DAYS = 30

# Low Stock Threshold
LOW_STOCK_THRESHOLD = 10

# Scarcity Display Threshold
SCARCITY_DISPLAY_THRESHOLD = 50

# Review Constraints
MIN_RATING = 1
MAX_RATING = 5

# Sales Streak Bonus Threshold
SALES_STREAK_THRESHOLD = 10
MIN_ACCEPTABLE_RATING = 3

# Featured Farmer Threshold
FEATURED_AUTHENTICITY_THRESHOLD = 90

# Referral Reward Percentage
REFERRAL_REWARD_PERCENTAGE = 5

# Cache TTL (seconds)
VERIFICATION_CACHE_TTL = 86400  # 24 hours
MARKETING_CONTENT_CACHE_TTL = 604800  # 7 days

# S3 Lifecycle
S3_STANDARD_IA_TRANSITION_DAYS = 30

# Delivery Estimate
DEFAULT_DELIVERY_DAYS = 7

# Recent Purchase Window (seconds)
RECENT_PURCHASE_WINDOW = 86400  # 24 hours
