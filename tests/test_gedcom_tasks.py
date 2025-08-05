"""
Tests for GEDCOM generation Celery tasks
"""
import tempfile
import uuid
from pathlib import Path
from unittest.mock import patch

import pytest

from web_app.tasks.gedcom_tasks import generate_gedcom_file


class TestGenerateGedcomFileTask:
    """Test the GEDCOM file generation Celery task function"""

    @pytest.fixture
    def task_id(self):
        """Sample task ID"""
        return str(uuid.uuid4())

    @pytest.fixture
    def temp_input_file(self):
        """Create temporary input file"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('{"families": [], "isolated_individuals": []}')
            temp_path = f.name
        yield temp_path
        Path(temp_path).unlink()

    @pytest.fixture
    def mock_gedcom_service(self):
        """Mock GedcomService class"""
        with patch('web_app.tasks.gedcom_tasks.GedcomService') as mock_class:
            yield mock_class.return_value

    @pytest.fixture
    def mock_current_task(self):
        """Mock current_task"""
        with patch('web_app.tasks.gedcom_tasks.current_task') as mock:
            yield mock

    @pytest.fixture
    def mock_logger(self):
        """Mock logger"""
        with patch('web_app.tasks.gedcom_tasks.logger') as mock:
            yield mock

    def test_generate_gedcom_file_success_with_files(self, temp_input_file, mock_gedcom_service, mock_current_task, mock_logger):
        """Test successful GEDCOM generation with input and output files"""
        # Setup mock service response
        expected_result = {
            'success': True,
            'output_file': '/tmp/family_tree.ged',
            'input_file': temp_input_file,
            'people_count': 5,
            'families_count': 3
        }
        mock_gedcom_service.generate_gedcom.return_value = expected_result

        # Call the task using pytest-celery approach
        result = generate_gedcom_file.apply(args=(temp_input_file, '/tmp/family_tree.ged'))

        # Verify results
        assert result.successful()
        result_data = result.result
        assert result_data == expected_result

        # Verify service was called correctly
        mock_gedcom_service.generate_gedcom.assert_called_once_with(
            input_file=temp_input_file,
            output_file='/tmp/family_tree.ged'
        )

        # Verify logging and progress updates
        mock_logger.info.assert_called_once()
        assert mock_current_task.update_state.call_count >= 3

    def test_generate_gedcom_file_success_no_files(self, mock_gedcom_service, mock_current_task, mock_logger):
        """Test successful GEDCOM generation without input and output files"""
        # Setup mock service response
        expected_result = {
            'success': True,
            'output_file': '/generated/family_tree.ged',
            'people_count': 2,
            'families_count': 1
        }
        mock_gedcom_service.generate_gedcom.return_value = expected_result

        # Call the task with no files
        result = generate_gedcom_file.apply(args=(None, None))

        # Verify results
        assert result.successful()
        result_data = result.result
        assert result_data == expected_result

        # Verify service was called with None values
        mock_gedcom_service.generate_gedcom.assert_called_once_with(
            input_file=None,
            output_file=None
        )

        mock_logger.info.assert_called_once()

    def test_generate_gedcom_file_input_file_not_found(self, mock_current_task, mock_logger):
        """Test GEDCOM generation with missing input file"""
        non_existent_file = "/tmp/non_existent_file.json"

        # Call the task
        result = generate_gedcom_file.apply(args=(non_existent_file, None))

        # Verify task failed - FileNotFoundError is in autoretry_for, so it retries then fails
        assert result.failed()
        assert isinstance(result.result, FileNotFoundError)

        # Error handling is now done by BaseFileProcessingTask
        assert mock_current_task.update_state.call_count >= 1

    def test_generate_gedcom_file_input_not_file(self, mock_current_task, mock_logger):
        """Test GEDCOM generation when input path is not a file"""
        # Use a directory instead of a file
        with tempfile.TemporaryDirectory() as temp_dir:
            # Call the task
            result = generate_gedcom_file.apply(args=(temp_dir, None))

            # Verify task failed with ValueError
            assert result.failed()
            assert isinstance(result.result, ValueError)

            # Error handling is now done by BaseFileProcessingTask - just verify task failed
            # The specific error state updates happen in a different context

    def test_generate_gedcom_file_service_returns_failure(self, temp_input_file, mock_gedcom_service, mock_current_task, mock_logger):
        """Test GEDCOM generation when service returns failure"""
        # Setup mock service to return failure
        service_result = {
            'success': False,
            'error': 'Invalid genealogy data format'
        }
        mock_gedcom_service.generate_gedcom.return_value = service_result

        # Call the task
        result = generate_gedcom_file.apply(args=(temp_input_file, None))

        # Verify task failed with RuntimeError
        assert result.failed()
        assert isinstance(result.result, RuntimeError)

        # Error handling is now done by BaseFileProcessingTask - just verify task failed
        # The specific error logging and state updates happen in BaseFileProcessingTask context

    def test_generate_gedcom_file_service_raises_runtime_error(self, temp_input_file, mock_gedcom_service, mock_current_task, mock_logger):
        """Test GEDCOM generation when service raises RuntimeError"""
        # Setup mock service to raise RuntimeError
        mock_gedcom_service.generate_gedcom.side_effect = RuntimeError("Database connection failed")

        # Call the task
        result = generate_gedcom_file.apply(args=(temp_input_file, None))

        # Verify task failed
        assert result.failed()
        assert isinstance(result.result, RuntimeError)

        # Error handling is now done by BaseFileProcessingTask - just verify task failed
        # The specific error logging and state updates happen in BaseFileProcessingTask context

    def test_generate_gedcom_file_service_raises_os_error(self, temp_input_file, mock_gedcom_service, mock_current_task, mock_logger):
        """Test GEDCOM generation when service raises OSError (should retry)"""
        # Setup mock service to raise OSError
        mock_gedcom_service.generate_gedcom.side_effect = OSError("Disk full")

        # Call the task
        result = generate_gedcom_file.apply(args=(temp_input_file, None))

        # OSError should be retried, but after max retries it should eventually fail
        assert not result.successful()
        # Error logging and retry logic are now handled by BaseFileProcessingTask
        # We can't easily test the internal retry calls in this context

    def test_generate_gedcom_file_service_raises_permission_error(self, temp_input_file, mock_gedcom_service, mock_current_task, mock_logger):
        """Test GEDCOM generation when service raises PermissionError (should retry)"""
        # Setup mock service to raise PermissionError
        mock_gedcom_service.generate_gedcom.side_effect = PermissionError("Permission denied")

        # Call the task
        result = generate_gedcom_file.apply(args=(temp_input_file, None))

        # PermissionError should not retry according to BaseFileProcessingTask
        assert result.failed()
        assert isinstance(result.result, PermissionError)
        # Error handling is now done by BaseFileProcessingTask

    def test_generate_gedcom_file_service_raises_import_error(self, temp_input_file, mock_gedcom_service, mock_current_task, mock_logger):
        """Test GEDCOM generation when service raises ImportError"""
        # Setup mock service to raise ImportError
        mock_gedcom_service.generate_gedcom.side_effect = ImportError("Missing GEDCOM library")

        # Call the task
        result = generate_gedcom_file.apply(args=(temp_input_file, None))

        # Verify task failed
        assert result.failed()
        assert isinstance(result.result, ImportError)

        # Error handling is now done by BaseFileProcessingTask - just verify task failed
        # The specific error logging and state updates happen in BaseFileProcessingTask context

    def test_generate_gedcom_file_no_input_validation(self, mock_gedcom_service, mock_current_task, mock_logger):
        """Test GEDCOM generation with no input file (no validation should occur)"""
        # Setup mock service response
        expected_result = {
            'success': True,
            'output_file': '/default/family_tree.ged'
        }
        mock_gedcom_service.generate_gedcom.return_value = expected_result

        # Call the task with None input file
        result = generate_gedcom_file.apply(args=(None, '/tmp/output.ged'))

        # Verify results - should succeed without validation
        assert result.successful()
        result_data = result.result
        assert result_data == expected_result

        # Verify service was called correctly
        mock_gedcom_service.generate_gedcom.assert_called_once_with(
            input_file=None,
            output_file='/tmp/output.ged'
        )

    def test_generate_gedcom_file_progress_updates(self, temp_input_file, mock_gedcom_service, mock_current_task, mock_logger):
        """Test that progress updates are called correctly"""
        # Setup mock service response
        expected_result = {'success': True, 'output_file': '/tmp/test.ged'}
        mock_gedcom_service.generate_gedcom.return_value = expected_result

        # Call the task
        result = generate_gedcom_file.apply(args=(temp_input_file, None))

        # Verify results
        assert result.successful()

        # Verify progress updates were called
        update_calls = mock_current_task.update_state.call_args_list
        assert len(update_calls) >= 3

        # Check specific progress updates
        progress_values = [call[1]['meta']['progress'] for call in update_calls]
        assert 0 in progress_values  # initializing
        assert 10 in progress_values  # generating
        assert 90 in progress_values  # finalizing

    def test_generate_gedcom_file_service_returns_success_false_no_error(self, temp_input_file, mock_gedcom_service, mock_current_task, mock_logger):
        """Test GEDCOM generation when service returns success=False but no error message"""
        # Setup mock service to return failure without error message
        service_result = {
            'success': False
        }
        mock_gedcom_service.generate_gedcom.return_value = service_result

        # Call the task
        result = generate_gedcom_file.apply(args=(temp_input_file, None))

        # Verify task failed with RuntimeError
        assert result.failed()
        assert isinstance(result.result, RuntimeError)

        # Error handling is now done by BaseFileProcessingTask - just verify task failed
        # The specific error logging and state updates happen in BaseFileProcessingTask context
