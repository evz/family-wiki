"""
Tests for service layer exceptions
"""
from unittest.mock import Mock

import pytest
import requests
import sqlalchemy.exc

from web_app.services.exceptions import (
    ConflictError,
    ConnectionError,
    DatabaseError,
    ExternalServiceError,
    NotFoundError,
    ServiceError,
    TimeoutError,
    ValidationError,
    handle_service_exceptions,
)


class TestServiceExceptions:
    """Test service exception classes"""

    def test_service_error_base_exception(self):
        """Test ServiceError base exception"""
        error = ServiceError("Test error message")
        assert str(error) == "Test error message"
        assert isinstance(error, Exception)

    def test_service_error_inheritance(self):
        """Test that all exceptions inherit from ServiceError"""
        validation_error = ValidationError("Validation failed")
        not_found_error = NotFoundError("Resource not found")
        conflict_error = ConflictError("Resource conflict")

        assert isinstance(validation_error, ServiceError)
        assert isinstance(not_found_error, ServiceError)
        assert isinstance(conflict_error, ServiceError)

    def test_validation_error(self):
        """Test ValidationError exception"""
        message = "Invalid input data"
        error = ValidationError(message)
        assert str(error) == message
        assert isinstance(error, ServiceError)

    def test_not_found_error(self):
        """Test NotFoundError exception"""
        message = "Resource not found"
        error = NotFoundError(message)
        assert str(error) == message
        assert isinstance(error, ServiceError)

    def test_conflict_error(self):
        """Test ConflictError exception"""
        message = "Resource already exists"
        error = ConflictError(message)
        assert str(error) == message
        assert isinstance(error, ServiceError)

    def test_exception_chaining(self):
        """Test exception chaining works correctly"""
        original_error = ValueError("Original error")

        try:
            raise ValidationError("Validation failed") from original_error
        except ValidationError as e:
            assert str(e) == "Validation failed"
            assert e.__cause__ == original_error

    def test_exception_without_message(self):
        """Test exceptions can be created without message"""
        error = ServiceError()
        assert str(error) == ""

    def test_exception_with_multiple_args(self):
        """Test exceptions with multiple arguments"""
        error = ServiceError("Error", "Additional info", 123)
        # Python's default behavior for multiple args
        assert "Error" in str(error)
        assert "Additional info" in str(error)
        assert "123" in str(error)

    def test_connection_error(self):
        """Test ConnectionError exception"""
        message = "Unable to connect to service"
        error = ConnectionError(message)
        assert str(error) == message
        assert isinstance(error, ServiceError)

    def test_timeout_error(self):
        """Test TimeoutError exception"""
        message = "Operation timed out"
        error = TimeoutError(message)
        assert str(error) == message
        assert isinstance(error, ServiceError)

    def test_external_service_error(self):
        """Test ExternalServiceError exception"""
        message = "External service failed"
        error = ExternalServiceError(message)
        assert str(error) == message
        assert isinstance(error, ServiceError)

    def test_database_error(self):
        """Test DatabaseError exception"""
        message = "Database connection failed"
        error = DatabaseError(message)
        assert str(error) == message
        assert isinstance(error, ServiceError)


class TestHandleServiceExceptionsDecorator:
    """Test handle_service_exceptions decorator"""

    def test_decorator_success_case(self):
        """Test decorator allows successful function execution"""
        @handle_service_exceptions()
        def test_func():
            return "success"

        result = test_func()
        assert result == "success"

    def test_decorator_reraises_service_exceptions(self):
        """Test decorator re-raises existing service exceptions"""
        @handle_service_exceptions()
        def test_func():
            raise ValidationError("Test validation error")

        with pytest.raises(ValidationError, match="Test validation error"):
            test_func()

    def test_decorator_handles_requests_connection_error(self):
        """Test decorator converts requests ConnectionError"""
        mock_logger = Mock()

        @handle_service_exceptions(logger=mock_logger)
        def test_func():
            raise requests.exceptions.ConnectionError("Connection failed")

        with pytest.raises(ConnectionError, match="Unable to connect to external service"):
            test_func()

        mock_logger.error.assert_called_once()

    def test_decorator_handles_requests_timeout(self):
        """Test decorator converts requests Timeout"""
        mock_logger = Mock()

        @handle_service_exceptions(logger=mock_logger)
        def test_func():
            raise requests.exceptions.Timeout("Request timed out")

        with pytest.raises(TimeoutError, match="Request timed out"):
            test_func()

        mock_logger.error.assert_called_once()

    def test_decorator_handles_requests_exception(self):
        """Test decorator converts general requests exception"""
        mock_logger = Mock()

        @handle_service_exceptions(logger=mock_logger)
        def test_func():
            raise requests.exceptions.RequestException("Request failed")

        with pytest.raises(ExternalServiceError, match="External service error"):
            test_func()

        mock_logger.error.assert_called_once()

    def test_decorator_handles_sqlalchemy_operational_error(self):
        """Test decorator converts SQLAlchemy OperationalError"""
        mock_logger = Mock()

        @handle_service_exceptions(logger=mock_logger)
        def test_func():
            raise sqlalchemy.exc.OperationalError("DB connection failed", None, None)

        with pytest.raises(DatabaseError, match="Database connection error"):
            test_func()

        mock_logger.error.assert_called_once()

    def test_decorator_handles_sqlalchemy_integrity_error(self):
        """Test decorator converts SQLAlchemy IntegrityError"""
        mock_logger = Mock()

        @handle_service_exceptions(logger=mock_logger)
        def test_func():
            raise sqlalchemy.exc.IntegrityError("Constraint violation", None, None)

        with pytest.raises(ConflictError, match="Data integrity violation"):
            test_func()

        mock_logger.error.assert_called_once()

    def test_decorator_handles_sqlalchemy_error(self):
        """Test decorator converts general SQLAlchemy error"""
        mock_logger = Mock()

        @handle_service_exceptions(logger=mock_logger)
        def test_func():
            raise sqlalchemy.exc.SQLAlchemyError("Database error")

        with pytest.raises(DatabaseError, match="Database error"):
            test_func()

        mock_logger.error.assert_called_once()

    def test_decorator_handles_value_error(self):
        """Test decorator converts ValueError to ValidationError"""
        mock_logger = Mock()

        @handle_service_exceptions(logger=mock_logger)
        def test_func():
            raise ValueError("Invalid value")

        with pytest.raises(ValidationError, match="Invalid input"):
            test_func()

        mock_logger.error.assert_called_once()

    def test_decorator_handles_key_error(self):
        """Test decorator converts KeyError to ValidationError"""
        mock_logger = Mock()

        @handle_service_exceptions(logger=mock_logger)
        def test_func():
            raise KeyError("missing_field")

        with pytest.raises(ValidationError, match="Missing required field"):
            test_func()

        mock_logger.error.assert_called_once()

    def test_decorator_handles_unexpected_exception(self):
        """Test decorator converts unexpected exceptions to ServiceError"""
        mock_logger = Mock()

        @handle_service_exceptions(logger=mock_logger)
        def test_func():
            raise RuntimeError("Unexpected error")

        with pytest.raises(ServiceError, match="Unexpected service error"):
            test_func()

        mock_logger.error.assert_called_once()

    def test_decorator_without_logger(self):
        """Test decorator works without logger"""
        @handle_service_exceptions()
        def test_func():
            raise ValueError("Test error")

        with pytest.raises(ValidationError):
            test_func()

    def test_decorator_preserves_function_metadata(self):
        """Test decorator preserves original function metadata"""
        @handle_service_exceptions()
        def test_func():
            """Test function docstring"""
            return "test"

        assert test_func.__name__ == "test_func"
        assert test_func.__doc__ == "Test function docstring"

    def test_decorator_with_function_args(self):
        """Test decorator works with function arguments"""
        @handle_service_exceptions()
        def test_func(arg1, arg2, kwarg1=None):
            return f"{arg1}-{arg2}-{kwarg1}"

        result = test_func("a", "b", kwarg1="c")
        assert result == "a-b-c"
