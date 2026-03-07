"""
Custom exception classes for RootTrust marketplace platform.
"""


class RootTrustException(Exception):
    """Base exception for all RootTrust errors."""
    
    def __init__(self, message: str, code: str = "INTERNAL_ERROR", status_code: int = 500):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(self.message)


class ValidationError(RootTrustException):
    """Raised when input validation fails."""
    
    def __init__(self, message: str, details: list = None):
        super().__init__(message, code="VALIDATION_ERROR", status_code=400)
        self.details = details or []


class AuthenticationError(RootTrustException):
    """Raised when authentication fails."""
    
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, code="AUTHENTICATION_ERROR", status_code=401)


class AuthorizationError(RootTrustException):
    """Raised when user lacks permission for an operation."""
    
    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(message, code="AUTHORIZATION_ERROR", status_code=403)


class ResourceNotFoundError(RootTrustException):
    """Raised when a requested resource doesn't exist."""
    
    def __init__(self, resource_type: str, resource_id: str):
        message = f"{resource_type} with ID {resource_id} not found"
        super().__init__(message, code="RESOURCE_NOT_FOUND", status_code=404)


class ConflictError(RootTrustException):
    """Raised when a business rule is violated."""
    
    def __init__(self, message: str):
        super().__init__(message, code="CONFLICT_ERROR", status_code=409)


class UnprocessableEntityError(RootTrustException):
    """Raised when business logic prevents processing."""
    
    def __init__(self, message: str):
        super().__init__(message, code="UNPROCESSABLE_ENTITY", status_code=422)


class ServiceUnavailableError(RootTrustException):
    """Raised when an external service is unavailable."""
    
    def __init__(self, service_name: str, message: str = None):
        msg = message or f"{service_name} is temporarily unavailable"
        super().__init__(msg, code="SERVICE_UNAVAILABLE", status_code=503)


class RateLimitError(RootTrustException):
    """Raised when rate limit is exceeded."""
    
    def __init__(self, message: str = "Rate limit exceeded", retry_after: int = None):
        super().__init__(message, code="RATE_LIMIT_EXCEEDED", status_code=429)
        self.retry_after = retry_after


class InsufficientBalanceError(ConflictError):
    """Raised when user has insufficient balance for an operation."""
    
    def __init__(self, required: float, available: float):
        message = f"Insufficient balance. Required: {required}, Available: {available}"
        super().__init__(message)


class OutOfStockError(ConflictError):
    """Raised when product is out of stock."""
    
    def __init__(self, product_id: str):
        message = f"Product {product_id} is out of stock"
        super().__init__(message)


class InvalidTokenError(AuthenticationError):
    """Raised when JWT token is invalid or expired."""
    
    def __init__(self, message: str = "Invalid or expired token"):
        super().__init__(message)


class DuplicateResourceError(ConflictError):
    """Raised when attempting to create a duplicate resource."""
    
    def __init__(self, resource_type: str, identifier: str):
        message = f"{resource_type} with identifier {identifier} already exists"
        super().__init__(message)
