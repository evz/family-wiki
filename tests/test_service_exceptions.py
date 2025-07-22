"""
Tests for service layer exceptions
"""


from web_app.services.exceptions import ConflictError, NotFoundError, ServiceError, ValidationError


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
