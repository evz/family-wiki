"""
Tests for service utility functions
"""

from unittest.mock import patch

from web_app.services.exceptions import ConflictError, NotFoundError, ServiceError, ValidationError
from web_app.services.service_utils import handle_service_errors


class TestHandleServiceErrors:
    """Test service error handling decorator"""

    def test_successful_function_execution(self, app):
        """Test decorator with successful function execution"""
        @handle_service_errors()
        def test_function():
            return "success"

        with app.test_request_context():
            result = test_function()
            assert result == "success"

    def test_successful_function_with_success_message(self, app):
        """Test decorator with success message"""
        @handle_service_errors(success_message="Operation completed")
        def test_function():
            return "success"

        with app.test_request_context():
            with patch('web_app.services.service_utils.flash') as mock_flash:
                result = test_function()
                assert result == "success"
                mock_flash.assert_called_once_with("Operation completed", "success")

    def test_validation_error_handling(self, app):
        """Test ValidationError handling"""
        @handle_service_errors()
        def test_function():
            raise ValidationError("Invalid input")

        with app.test_request_context():
            with patch('web_app.services.service_utils.flash') as mock_flash, \
                 patch('web_app.services.service_utils.redirect') as mock_redirect, \
                 patch('web_app.services.service_utils.url_for') as mock_url_for:

                mock_url_for.return_value = "/main"
                mock_redirect.return_value = "redirect_response"

                result = test_function()

                assert result == "redirect_response"
                mock_flash.assert_called_once_with("Validation error: Invalid input", "error")
                mock_url_for.assert_called_once_with("main.index")
                mock_redirect.assert_called_once_with("/main")

    def test_not_found_error_handling(self, app):
        """Test NotFoundError handling"""
        @handle_service_errors()
        def test_function():
            raise NotFoundError("Resource not found")

        with app.test_request_context():
            with patch('web_app.services.service_utils.flash') as mock_flash, \
                 patch('web_app.services.service_utils.redirect') as mock_redirect, \
                 patch('web_app.services.service_utils.url_for') as mock_url_for:

                mock_url_for.return_value = "/main"
                mock_redirect.return_value = "redirect_response"

                result = test_function()

                assert result == "redirect_response"
                mock_flash.assert_called_once_with("Not found: Resource not found", "error")
                mock_url_for.assert_called_once_with("main.index")

    def test_conflict_error_handling(self, app):
        """Test ConflictError handling"""
        @handle_service_errors()
        def test_function():
            raise ConflictError("Resource conflict")

        with app.test_request_context():
            with patch('web_app.services.service_utils.flash') as mock_flash, \
                 patch('web_app.services.service_utils.redirect') as mock_redirect, \
                 patch('web_app.services.service_utils.url_for') as mock_url_for:

                mock_url_for.return_value = "/main"
                mock_redirect.return_value = "redirect_response"

                result = test_function()

                assert result == "redirect_response"
                mock_flash.assert_called_once_with("Conflict: Resource conflict", "error")

    def test_generic_service_error_handling(self, app):
        """Test generic ServiceError handling"""
        @handle_service_errors()
        def test_function():
            raise ServiceError("Generic service error")

        with app.test_request_context():
            with patch('web_app.services.service_utils.flash') as mock_flash, \
                 patch('web_app.services.service_utils.redirect') as mock_redirect, \
                 patch('web_app.services.service_utils.url_for') as mock_url_for:

                mock_url_for.return_value = "/main"
                mock_redirect.return_value = "redirect_response"

                result = test_function()

                assert result == "redirect_response"
                mock_flash.assert_called_once_with("Error: Generic service error", "error")

    def test_unexpected_error_handling(self, app):
        """Test unexpected exception handling"""
        @handle_service_errors()
        def test_function():
            raise ValueError("Unexpected error")

        with app.test_request_context():
            with patch('web_app.services.service_utils.flash') as mock_flash, \
                 patch('web_app.services.service_utils.redirect') as mock_redirect, \
                 patch('web_app.services.service_utils.url_for') as mock_url_for:

                mock_url_for.return_value = "/main"
                mock_redirect.return_value = "redirect_response"

                result = test_function()

                assert result == "redirect_response"
                mock_flash.assert_called_once_with("Unexpected error: Unexpected error", "error")

    def test_custom_redirect_endpoint(self, app):
        """Test decorator with custom redirect endpoint"""
        @handle_service_errors(redirect_endpoint='custom.endpoint')
        def test_function():
            raise ValidationError("Test error")

        with app.test_request_context():
            with patch('web_app.services.service_utils.flash'), \
                 patch('web_app.services.service_utils.redirect') as mock_redirect, \
                 patch('web_app.services.service_utils.url_for') as mock_url_for:

                mock_url_for.return_value = "/custom"
                mock_redirect.return_value = "redirect_response"

                result = test_function()

                assert result == "redirect_response"
                mock_url_for.assert_called_once_with("custom.endpoint")

    def test_decorator_preserves_function_metadata(self):
        """Test that decorator preserves original function metadata"""
        @handle_service_errors()
        def test_function():
            """Test function docstring"""
            return "test"

        assert test_function.__name__ == "test_function"
        assert test_function.__doc__ == "Test function docstring"

    def test_decorator_with_function_arguments(self, app):
        """Test decorator works with function arguments"""
        @handle_service_errors()
        def test_function(arg1, arg2, kwarg1=None):
            return f"{arg1}-{arg2}-{kwarg1}"

        with app.test_request_context():
            result = test_function("a", "b", kwarg1="c")
            assert result == "a-b-c"

    def test_decorator_with_function_that_raises_and_has_args(self, app):
        """Test decorator error handling with function arguments"""
        @handle_service_errors()
        def test_function(arg1, arg2):
            raise ValidationError(f"Error with {arg1} and {arg2}")

        with app.test_request_context():
            with patch('web_app.services.service_utils.flash') as mock_flash, \
                 patch('web_app.services.service_utils.redirect') as mock_redirect, \
                 patch('web_app.services.service_utils.url_for') as mock_url_for:

                mock_url_for.return_value = "/main"
                mock_redirect.return_value = "redirect_response"

                result = test_function("test1", "test2")

                assert result == "redirect_response"
                mock_flash.assert_called_once_with("Validation error: Error with test1 and test2", "error")
