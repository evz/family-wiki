"""
Tests for error_handling module
"""
from unittest.mock import Mock, PropertyMock

import pytest
from celery.exceptions import OperationalError
from kombu.exceptions import ConnectionError
from kombu.exceptions import OperationalError as KombuOperationalError
from sqlalchemy.exc import SQLAlchemyError

from web_app.blueprints.error_handling import (
    FileOperationError,
    TaskSubmissionError,
    get_task_status_safely,
    handle_blueprint_errors,
    safe_database_operation,
    safe_file_operation,
    safe_task_submit,
)


class TestCustomExceptions:
    """Test custom exception classes"""

    def test_task_submission_error(self):
        """Test TaskSubmissionError exception"""
        error = TaskSubmissionError("Task submission failed")
        assert str(error) == "Task submission failed"
        assert isinstance(error, Exception)

    def test_file_operation_error(self):
        """Test FileOperationError exception"""
        error = FileOperationError("File operation failed")
        assert str(error) == "File operation failed"
        assert isinstance(error, Exception)


class TestSafeTaskSubmit:
    """Test safe_task_submit function"""

    def test_safe_task_submit_success(self, app):
        """Test successful task submission"""
        mock_task_func = Mock()
        mock_task_func.return_value = "task_result"

        result = safe_task_submit(mock_task_func, "test_task", "arg1", kwarg1="value1")

        assert result == "task_result"
        mock_task_func.assert_called_once_with("arg1", kwarg1="value1")

    def test_safe_task_submit_celery_operational_error(self, app):
        """Test handling of Celery OperationalError"""
        mock_task_func = Mock()
        mock_task_func.side_effect = OperationalError("Broker connection failed")

        with pytest.raises(TaskSubmissionError, match="Unable to connect to task queue"):
            safe_task_submit(mock_task_func, "test_task")

    def test_safe_task_submit_kombu_operational_error(self, app):
        """Test handling of Kombu OperationalError"""
        mock_task_func = Mock()
        mock_task_func.side_effect = KombuOperationalError("Kombu broker error")

        with pytest.raises(TaskSubmissionError, match="Unable to connect to task queue"):
            safe_task_submit(mock_task_func, "test_task")

    def test_safe_task_submit_connection_error(self, app):
        """Test handling of ConnectionError"""
        mock_task_func = Mock()
        mock_task_func.side_effect = ConnectionError("Connection failed")

        with pytest.raises(TaskSubmissionError, match="Unable to connect to task queue"):
            safe_task_submit(mock_task_func, "test_task")

    def test_safe_task_submit_os_error(self, app):
        """Test handling of OSError"""
        mock_task_func = Mock()
        mock_task_func.side_effect = OSError("Network error")

        with pytest.raises(TaskSubmissionError, match="Network error - unable to reach task queue"):
            safe_task_submit(mock_task_func, "test_task")

    def test_safe_task_submit_unexpected_error(self, app):
        """Test handling of unexpected errors"""
        mock_task_func = Mock()
        mock_task_func.side_effect = ValueError("Unexpected error")

        with pytest.raises(TaskSubmissionError, match="An unexpected error occurred while starting the job"):
            safe_task_submit(mock_task_func, "test_task")


class TestSafeFileOperation:
    """Test safe_file_operation function"""

    def test_safe_file_operation_success(self, app):
        """Test successful file operation"""
        mock_operation = Mock()
        mock_operation.return_value = "file_result"

        result = safe_file_operation(mock_operation, "test operation", "arg1", kwarg1="value1")

        assert result == "file_result"
        mock_operation.assert_called_once_with("arg1", kwarg1="value1")

    def test_safe_file_operation_os_error(self, app):
        """Test handling of OSError"""
        mock_operation = Mock()
        mock_operation.side_effect = OSError("Disk full")

        with pytest.raises(FileOperationError, match="File system error - check disk space and permissions"):
            safe_file_operation(mock_operation, "test operation")

    def test_safe_file_operation_permission_error(self, app):
        """Test handling of PermissionError (caught as OSError)"""
        mock_operation = Mock()
        mock_operation.side_effect = PermissionError("Access denied")

        with pytest.raises(FileOperationError, match="File system error - check disk space and permissions"):
            safe_file_operation(mock_operation, "test operation")

    def test_safe_file_operation_value_error(self, app):
        """Test handling of ValueError"""
        mock_operation = Mock()
        mock_operation.side_effect = ValueError("Invalid data")

        with pytest.raises(FileOperationError, match="Invalid file data or format"):
            safe_file_operation(mock_operation, "test operation")

    def test_safe_file_operation_unexpected_error(self, app):
        """Test handling of unexpected errors"""
        mock_operation = Mock()
        mock_operation.side_effect = RuntimeError("Unexpected error")

        with pytest.raises(FileOperationError, match="An unexpected error occurred during test operation"):
            safe_file_operation(mock_operation, "test operation")


class TestSafeDatabaseOperation:
    """Test safe_database_operation function"""

    def test_safe_database_operation_success(self, app):
        """Test successful database operation"""
        mock_operation = Mock()
        mock_operation.return_value = "db_result"

        result = safe_database_operation(mock_operation, "test operation", "arg1", kwarg1="value1")

        assert result == "db_result"
        mock_operation.assert_called_once_with("arg1", kwarg1="value1")

    def test_safe_database_operation_sqlalchemy_error(self, app):
        """Test handling of SQLAlchemyError"""
        mock_operation = Mock()
        mock_operation.side_effect = SQLAlchemyError("Database error")

        with pytest.raises(SQLAlchemyError):
            safe_database_operation(mock_operation, "test operation")


class TestHandleBlueprintErrorsDecorator:
    """Test handle_blueprint_errors decorator"""

    def test_decorator_success_case(self, app):
        """Test decorator allows successful function execution"""
        @handle_blueprint_errors()
        def test_func():
            return "success"

        with app.test_request_context():
            result = test_func()
            assert result == "success"

    def test_decorator_task_submission_error(self, app):
        """Test decorator handles TaskSubmissionError"""
        @handle_blueprint_errors()
        def test_func():
            raise TaskSubmissionError("Task failed")

        with app.test_request_context():
            response = test_func()
            assert response.status_code == 302  # Redirect

    def test_decorator_file_operation_error(self, app):
        """Test decorator handles FileOperationError"""
        @handle_blueprint_errors()
        def test_func():
            raise FileOperationError("File failed")

        with app.test_request_context():
            response = test_func()
            assert response.status_code == 302  # Redirect

    def test_decorator_sqlalchemy_error(self, app):
        """Test decorator handles SQLAlchemyError"""
        @handle_blueprint_errors()
        def test_func():
            raise SQLAlchemyError("Database failed")

        with app.test_request_context():
            response = test_func()
            assert response.status_code == 302  # Redirect

    def test_decorator_unexpected_error(self, app):
        """Test decorator handles unexpected errors"""
        @handle_blueprint_errors()
        def test_func():
            raise ValueError("Unexpected error")

        with app.test_request_context():
            response = test_func()
            assert response.status_code == 302  # Redirect

    def test_decorator_custom_redirect_url(self, app):
        """Test decorator with custom redirect URL"""
        @handle_blueprint_errors(redirect_url='main.index')
        def test_func():
            raise TaskSubmissionError("Task failed")

        with app.test_request_context():
            response = test_func()
            assert response.status_code == 302  # Redirect

    def test_decorator_preserves_function_metadata(self, app):
        """Test decorator preserves original function metadata"""
        @handle_blueprint_errors()
        def test_func():
            """Test function docstring"""
            return "test"

        assert test_func.__name__ == "test_func"
        assert test_func.__doc__ == "Test function docstring"


class TestGetTaskStatusSafely:
    """Test get_task_status_safely function"""

    def test_get_task_status_pending(self, app):
        """Test task status for pending task"""
        mock_task = Mock()
        mock_task.state = 'PENDING'
        mock_task.info = None

        result = get_task_status_safely(mock_task, "test-task-123")

        assert result['status'] == 'pending'
        assert result['message'] == 'Task is waiting to be processed'
        assert result['progress'] == 0

    def test_get_task_status_running(self, app):
        """Test task status for running task (maps to 'progress' in implementation)"""
        mock_task = Mock()
        mock_task.state = 'PROGRESS'
        mock_task.result = {'status': 'processing', 'progress': 50}

        result = get_task_status_safely(mock_task, "test-task-123")

        assert result['status'] == 'running'
        assert result['message'] == 'processing'
        assert result['progress'] == 50

    def test_get_task_status_running_no_info(self, app):
        """Test task status for running task with no info"""
        mock_task = Mock()
        mock_task.state = 'PROGRESS'
        mock_task.result = None

        result = get_task_status_safely(mock_task, "test-task-123")

        assert result['status'] == 'running'
        assert result['message'] == 'Task is running'
        assert result['progress'] == 50

    def test_get_task_status_success(self, app):
        """Test task status for successful task"""
        mock_task = Mock()
        mock_task.state = 'SUCCESS'
        mock_task.result = {'success': True, 'data': 'test_data'}

        result = get_task_status_safely(mock_task, "test-task-123")

        assert result['status'] == 'completed'
        assert result['message'] == 'Task completed successfully'
        assert result['progress'] == 100
        assert result['result'] == {'success': True, 'data': 'test_data'}

    def test_get_task_status_failure(self, app):
        """Test task status for failed task"""
        mock_task = Mock()
        mock_task.state = 'FAILURE'
        mock_task.result = "Task failed with error"

        result = get_task_status_safely(mock_task, "test-task-123")

        assert result['status'] == 'failed'
        assert result['error'] == 'Task failed with error'
        assert result['progress'] == 0

    def test_get_task_status_failure_dict_result(self, app):
        """Test task status for failed task with dict result"""
        mock_task = Mock()
        mock_task.state = 'FAILURE'
        mock_task.result = {'error': 'Specific error message'}

        result = get_task_status_safely(mock_task, "test-task-123")

        assert result['status'] == 'failed'
        assert result['error'] == 'Specific error message'
        assert result['progress'] == 0

    def test_get_task_status_revoked(self, app):
        """Test task status for revoked task"""
        mock_task = Mock()
        mock_task.state = 'REVOKED'

        result = get_task_status_safely(mock_task, "test-task-123")

        assert result['status'] == 'revoked'
        assert result['message'] == 'Task status: REVOKED'
        assert result['progress'] == 25

    def test_get_task_status_unknown_state(self, app):
        """Test task status for unknown state"""
        mock_task = Mock()
        mock_task.state = 'UNKNOWN_STATE'

        result = get_task_status_safely(mock_task, "test-task-123")

        assert result['status'] == 'unknown_state'
        assert result['message'] == 'Task status: UNKNOWN_STATE'
        assert result['progress'] == 25

    def test_get_task_status_exception_handling(self, app):
        """Test task status when exception occurs"""
        mock_task = Mock()
        # The function just accesses task.state directly, so mock normally
        # but let me test a different scenario - the actual exception is caught
        # when task.state works but other attributes fail
        mock_task.state = 'FAILURE'
        mock_task.result = Mock()
        # Make task.result access fail to trigger exception handling
        type(mock_task).result = PropertyMock(side_effect=AttributeError("Connection lost"))

        result = get_task_status_safely(mock_task, "test-task-123")

        assert result['status'] == 'error'
        assert 'Unable to retrieve task status' in result['message']
        assert result['progress'] == 0
