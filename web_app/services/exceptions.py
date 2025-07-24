"""
Custom exceptions for service layer
"""

import functools

import requests
import sqlalchemy.exc


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

class ConnectionError(ServiceError):
    """Raised when unable to connect to external services (LLM, database, etc.)"""
    pass

class TimeoutError(ServiceError):
    """Raised when an operation times out"""
    pass

class ExternalServiceError(ServiceError):
    """Raised when an external service returns an error"""
    pass

class DatabaseError(ServiceError):
    """Raised when database operations fail"""
    pass


def handle_service_exceptions(logger=None):
    """Decorator to handle common service exceptions and convert them to service-specific exceptions"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except ValidationError:
                # Re-raise our own validation errors
                raise
            except NotFoundError:
                # Re-raise our own not found errors
                raise
            except ConflictError:
                # Re-raise our own conflict errors
                raise
            except (ConnectionError, TimeoutError, ExternalServiceError, DatabaseError):
                # Re-raise our own service errors
                raise
            except requests.exceptions.ConnectionError as e:
                if logger:
                    logger.error(f"HTTP connection error in {func.__name__}: {e}")
                raise ConnectionError(f"Unable to connect to external service: {e}") from e
            except requests.exceptions.Timeout as e:
                if logger:
                    logger.error(f"HTTP timeout error in {func.__name__}: {e}")
                raise TimeoutError(f"Request timed out: {e}") from e
            except requests.exceptions.RequestException as e:
                if logger:
                    logger.error(f"HTTP request error in {func.__name__}: {e}")
                raise ExternalServiceError(f"External service error: {e}") from e
            except sqlalchemy.exc.OperationalError as e:
                if logger:
                    logger.error(f"Database operational error in {func.__name__}: {e}")
                raise DatabaseError(f"Database connection error: {e}") from e
            except sqlalchemy.exc.IntegrityError as e:
                if logger:
                    logger.error(f"Database integrity error in {func.__name__}: {e}")
                raise ConflictError(f"Data integrity violation: {e}") from e
            except sqlalchemy.exc.SQLAlchemyError as e:
                if logger:
                    logger.error(f"Database error in {func.__name__}: {e}")
                raise DatabaseError(f"Database error: {e}") from e
            except ValueError as e:
                if logger:
                    logger.error(f"Validation error in {func.__name__}: {e}")
                raise ValidationError(f"Invalid input: {e}") from e
            except KeyError as e:
                if logger:
                    logger.error(f"Missing required data in {func.__name__}: {e}")
                raise ValidationError(f"Missing required field: {e}") from e
            except Exception as e:
                if logger:
                    logger.error(f"Unexpected error in {func.__name__}: {e}", exc_info=True)
                raise ServiceError(f"Unexpected service error: {e}") from e
        return wrapper
    return decorator
