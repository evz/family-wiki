"""
Tests for shared_utils module
"""
from unittest.mock import Mock, patch

from celery.exceptions import OperationalError
from kombu.exceptions import ConnectionError
from kombu.exceptions import OperationalError as KombuOperationalError

from web_app.blueprints.shared_utils import safe_task_submit


class TestSafeTaskSubmit:
    """Test safe_task_submit function"""

    def test_safe_task_submit_success(self, app):
        """Test successful task submission"""
        mock_task_func = Mock()
        mock_task_func.return_value = "task_result"

        result = safe_task_submit(mock_task_func, "test_task", "arg1", "arg2", kwarg1="value1")

        assert result == "task_result"
        mock_task_func.assert_called_once_with("arg1", "arg2", kwarg1="value1")

    def test_safe_task_submit_celery_operational_error(self, app):
        """Test handling of Celery OperationalError"""
        mock_task_func = Mock()
        mock_task_func.side_effect = OperationalError("Broker connection failed")

        with patch('web_app.blueprints.shared_utils.flash') as mock_flash:
            result = safe_task_submit(mock_task_func, "test_task")

            assert result is None
            mock_flash.assert_called_once_with(
                'Unable to connect to task queue - check that Redis and Celery worker are running',
                'error'
            )

    def test_safe_task_submit_kombu_operational_error(self, app):
        """Test handling of Kombu OperationalError"""
        mock_task_func = Mock()
        mock_task_func.side_effect = KombuOperationalError("Kombu broker error")

        with patch('web_app.blueprints.shared_utils.flash') as mock_flash:
            result = safe_task_submit(mock_task_func, "test_task")

            assert result is None
            mock_flash.assert_called_once_with(
                'Unable to connect to task queue - check that Redis and Celery worker are running',
                'error'
            )

    def test_safe_task_submit_connection_error(self, app):
        """Test handling of ConnectionError"""
        mock_task_func = Mock()
        mock_task_func.side_effect = ConnectionError("Connection failed")

        with patch('web_app.blueprints.shared_utils.flash') as mock_flash:
            result = safe_task_submit(mock_task_func, "test_task")

            assert result is None
            mock_flash.assert_called_once_with(
                'Unable to connect to task queue - check that Redis and Celery worker are running',
                'error'
            )

    def test_safe_task_submit_os_error(self, app):
        """Test handling of OSError"""
        mock_task_func = Mock()
        mock_task_func.side_effect = OSError("Network error")

        with patch('web_app.blueprints.shared_utils.flash') as mock_flash:
            result = safe_task_submit(mock_task_func, "test_task")

            assert result is None
            mock_flash.assert_called_once_with('Network error - unable to reach task queue', 'error')

    def test_safe_task_submit_unexpected_error(self, app):
        """Test handling of unexpected errors"""
        mock_task_func = Mock()
        mock_task_func.side_effect = ValueError("Unexpected error")

        with patch('web_app.blueprints.shared_utils.flash') as mock_flash:
            result = safe_task_submit(mock_task_func, "test_task")

            assert result is None
            mock_flash.assert_called_once_with(
                'An unexpected error occurred while starting the job',
                'error'
            )

    def test_safe_task_submit_with_args_and_kwargs(self, app):
        """Test that args and kwargs are properly passed through"""
        mock_task_func = Mock()
        mock_task_func.return_value = "success"

        result = safe_task_submit(
            mock_task_func,
            "test_task",
            "pos_arg1",
            "pos_arg2",
            keyword_arg="keyword_value",
            another_kwarg=123
        )

        assert result == "success"
        mock_task_func.assert_called_once_with(
            "pos_arg1",
            "pos_arg2",
            keyword_arg="keyword_value",
            another_kwarg=123
        )

    def test_safe_task_submit_no_args(self, app):
        """Test task submission with no arguments"""
        mock_task_func = Mock()
        mock_task_func.return_value = "no_args_result"

        result = safe_task_submit(mock_task_func, "test_task")

        assert result == "no_args_result"
        mock_task_func.assert_called_once_with()
