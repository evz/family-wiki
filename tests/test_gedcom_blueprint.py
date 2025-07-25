"""
Tests for GEDCOM blueprint
"""
from unittest.mock import Mock, patch

from web_app.blueprints.gedcom import gedcom_bp


class TestGedcomBlueprint:
    """Test GEDCOM blueprint functionality"""

    def test_blueprint_registration(self, app):
        """Test that GEDCOM blueprint is properly registered"""
        assert 'gedcom' in app.blueprints
        assert app.blueprints['gedcom'] == gedcom_bp

    def test_blueprint_url_prefix(self, app):
        """Test blueprint has correct URL prefix"""
        assert gedcom_bp.url_prefix == '/gedcom'

    def test_start_gedcom_no_file_success(self, client, app):
        """Test starting GEDCOM job without uploaded file - success case"""
        with patch('web_app.blueprints.gedcom.safe_task_submit') as mock_submit:
            mock_task = Mock()
            mock_task.id = "test-task-123"
            mock_submit.return_value = mock_task

            response = client.post('/gedcom/start', data={})

            assert response.status_code == 302  # Redirect
            assert response.location.endswith('/')
            mock_submit.assert_called_once()
            # Verify the call arguments
            args, kwargs = mock_submit.call_args
            assert len(args) == 2  # function and task name
            assert args[1] == "GEDCOM"
            assert 'task_id' in kwargs

    def test_start_gedcom_no_file_task_failure(self, client, app):
        """Test starting GEDCOM job when task submission fails"""
        with patch('web_app.blueprints.gedcom.safe_task_submit') as mock_submit:
            mock_submit.return_value = None  # Task submission failed

            response = client.post('/gedcom/start', data={})

            assert response.status_code == 302  # Redirect
            mock_submit.assert_called_once()

    def test_start_gedcom_with_file_success(self, client, app):
        """Test starting GEDCOM job with uploaded file - success case"""
        with patch('web_app.blueprints.gedcom.safe_task_submit') as mock_submit, \
             patch('web_app.blueprints.gedcom.safe_file_operation') as mock_file_op:

            mock_task = Mock()
            mock_task.id = "test-task-456"
            mock_submit.return_value = mock_task
            mock_file_op.return_value = "file_id_123"  # File save success

            data = {
                'input_file': (open(__file__, 'rb'), 'test_input.json')
            }
            response = client.post('/gedcom/start', data=data)

            assert response.status_code == 302  # Redirect
            mock_submit.assert_called_once()
            mock_file_op.assert_called_once()

    def test_start_gedcom_with_file_save_failure(self, client, app):
        """Test starting GEDCOM job when file save fails"""
        with patch('web_app.blueprints.gedcom.safe_file_operation') as mock_file_op:
            mock_file_op.return_value = None  # File save failed

            data = {
                'input_file': (open(__file__, 'rb'), 'test_input.json')
            }
            response = client.post('/gedcom/start', data=data)

            assert response.status_code == 302  # Redirect back to main
            mock_file_op.assert_called_once()

    def test_start_gedcom_with_empty_filename(self, client, app):
        """Test starting GEDCOM job with empty filename (should use default)"""
        with patch('web_app.blueprints.gedcom.safe_task_submit') as mock_submit:
            mock_task = Mock()
            mock_task.id = "test-task-789"
            mock_submit.return_value = mock_task

            # Create a mock file with empty filename
            from io import BytesIO
            data = {
                'input_file': (BytesIO(b'test content'), '')
            }
            response = client.post('/gedcom/start', data=data)

            assert response.status_code == 302  # Redirect
            mock_submit.assert_called_once()

    def test_start_gedcom_file_operations_called_correctly(self, client, app):
        """Test that file operations are called with correct parameters"""
        with patch('web_app.blueprints.gedcom.safe_task_submit') as mock_submit, \
             patch('web_app.blueprints.gedcom.safe_file_operation') as mock_file_op, \
             patch('web_app.blueprints.gedcom.JobFileRepository') as mock_repo_class:

            mock_task = Mock()
            mock_task.id = "test-task-xyz"
            mock_submit.return_value = mock_task
            mock_file_op.return_value = "file_id_456"

            mock_repo = Mock()
            mock_repo_class.return_value = mock_repo

            data = {
                'input_file': (open(__file__, 'rb'), 'test_input.json')
            }
            response = client.post('/gedcom/start', data=data)

            assert response.status_code == 302

            # Verify file operation was called with correct parameters
            mock_file_op.assert_called_once()
            args = mock_file_op.call_args[0]
            assert len(args) == 6  # function, description, file, task_id, job_type, file_type
            assert args[1] == "GEDCOM input file upload"
            assert args[4] == 'gedcom'  # job_type
            assert args[5] == 'input'   # file_type

    def test_start_gedcom_task_id_generation(self, client, app):
        """Test that task ID is properly generated for each request"""
        with patch('web_app.blueprints.gedcom.safe_task_submit') as mock_submit, \
             patch('web_app.blueprints.gedcom.uuid.uuid4') as mock_uuid:

            mock_uuid.return_value = Mock()
            mock_uuid.return_value.__str__ = Mock(return_value="generated-uuid-123")

            mock_task = Mock()
            mock_task.id = "test-task-abc"
            mock_submit.return_value = mock_task

            response = client.post('/gedcom/start', data={})

            assert response.status_code == 302
            mock_uuid.assert_called_once()

            # Verify task_id was passed to safe_task_submit
            args, kwargs = mock_submit.call_args
            assert 'task_id' in kwargs
            assert kwargs['task_id'] == "generated-uuid-123"

    def test_start_gedcom_logging(self, client, app):
        """Test that appropriate logging occurs"""
        with patch('web_app.blueprints.gedcom.safe_task_submit') as mock_submit, \
             patch('web_app.blueprints.gedcom.logger') as mock_logger:

            mock_task = Mock()
            mock_task.id = "logged-task-123"
            mock_submit.return_value = mock_task

            response = client.post('/gedcom/start', data={})

            assert response.status_code == 302
            mock_logger.info.assert_called_once_with("Started GEDCOM task: logged-task-123")

    def test_start_gedcom_logging_with_file(self, client, app):
        """Test logging when file is uploaded"""
        with patch('web_app.blueprints.gedcom.safe_task_submit') as mock_submit, \
             patch('web_app.blueprints.gedcom.safe_file_operation') as mock_file_op, \
             patch('web_app.blueprints.gedcom.logger') as mock_logger:

            mock_task = Mock()
            mock_task.id = "file-task-456"
            mock_submit.return_value = mock_task
            mock_file_op.return_value = "file_id_789"

            data = {
                'input_file': (open(__file__, 'rb'), 'test_input.json')
            }
            response = client.post('/gedcom/start', data=data)

            assert response.status_code == 302
            mock_logger.info.assert_called_once_with("Started GEDCOM task with uploaded file: file-task-456")
