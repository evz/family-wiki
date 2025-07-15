"""
Tests for service utilities
"""

from unittest.mock import Mock

from web_app.shared.service_utils import execute_with_progress


class TestServiceUtils:
    """Test service utility functions"""

    def test_execute_with_progress_success(self):
        """Test successful operation with progress tracking"""
        mock_operation = Mock(return_value={"data": "test"})
        mock_progress = Mock()

        result = execute_with_progress(
            "test operation",
            mock_operation,
            mock_progress,
            arg1="value1",
            arg2="value2"
        )

        assert result['success'] is True
        assert result['message'] == "test operation completed"
        assert result['results'] == {"data": "test"}

        # Verify operation was called with correct arguments
        mock_operation.assert_called_once_with(arg1="value1", arg2="value2")

        # Verify progress callbacks were called
        assert mock_progress.call_count == 2
        mock_progress.assert_any_call({"status": "starting", "message": "Initializing test operation"})
        mock_progress.assert_any_call({"status": "completed", "results": {"data": "test"}})

    def test_execute_with_progress_no_callback(self):
        """Test operation without progress callback"""
        mock_operation = Mock(return_value={"data": "test"})

        result = execute_with_progress(
            "test operation",
            mock_operation,
            None,  # No progress callback
            arg1="value1"
        )

        assert result['success'] is True
        assert result['message'] == "test operation completed"
        assert result['results'] == {"data": "test"}
        mock_operation.assert_called_once_with(arg1="value1")

    def test_execute_with_progress_failure(self):
        """Test operation failure with error handling"""
        mock_operation = Mock(side_effect=Exception("Operation failed"))
        mock_progress = Mock()

        result = execute_with_progress(
            "test operation",
            mock_operation,
            mock_progress
        )

        assert result['success'] is False
        assert "test operation failed: Operation failed" in result['error']

        # Verify progress callbacks were called
        assert mock_progress.call_count == 2
        mock_progress.assert_any_call({"status": "starting", "message": "Initializing test operation"})
        mock_progress.assert_any_call({"status": "failed", "error": "test operation failed: Operation failed"})

    def test_execute_with_progress_failure_no_callback(self):
        """Test operation failure without progress callback"""
        mock_operation = Mock(side_effect=ValueError("Invalid input"))

        result = execute_with_progress(
            "test operation",
            mock_operation,
            None  # No progress callback
        )

        assert result['success'] is False
        assert "test operation failed: Invalid input" in result['error']
        mock_operation.assert_called_once_with()

    def test_execute_with_progress_complex_operation(self):
        """Test with a more complex operation that returns various data types"""
        def complex_operation(data_list, multiplier=1):
            return [x * multiplier for x in data_list]

        mock_progress = Mock()

        result = execute_with_progress(
            "list processing",
            complex_operation,
            mock_progress,
            data_list=[1, 2, 3],
            multiplier=2
        )

        assert result['success'] is True
        assert result['results'] == [2, 4, 6]

        # Check progress was tracked
        mock_progress.assert_any_call({"status": "starting", "message": "Initializing list processing"})
        mock_progress.assert_any_call({"status": "completed", "results": [2, 4, 6]})
