"""
Custom exceptions for service layer
"""

class ServiceError(Exception):
    """Base exception for service layer errors"""
    pass

class ValidationError(ServiceError):
    """Raised when input validation fails"""
    pass

class NotFoundError(ServiceError):
    """Raised when a requested resource is not found"""
    pass

class ConflictError(ServiceError):
    """Raised when an operation conflicts with current state"""
    pass
