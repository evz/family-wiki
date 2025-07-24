"""
Tests for tools blueprint
"""

import uuid
from io import BytesIO
from unittest.mock import Mock, patch

import pytest

from app import create_app
from tests.conftest import BaseTestConfig


class ToolsBlueprintTestConfig(BaseTestConfig):
    """Test configuration"""
    def __init__(self):
        super().__init__()
        self.sqlalchemy_database_uri = 'sqlite:///:memory:'


class TestToolsBlueprint:
    """Test tools blueprint routes"""

    @pytest.fixture
    def app(self):
        """Create test Flask app"""
        app = create_app(ToolsBlueprintTestConfig())
        return app

    @pytest.fixture
    def client(self, app):
        """Create test client"""
        return app.test_client()

    @pytest.fixture
    def mock_job_file_repo(self):
        """Mock job file repository"""
        with patch('web_app.blueprints.tools.JobFileRepository') as mock_repo:
            yield mock_repo

    @pytest.fixture
    def mock_tasks(self):
        """Mock all task modules"""
        mocks = {}
        patches = [
            ('process_pdfs_ocr', 'web_app.blueprints.tools.process_pdfs_ocr'),
            ('extract_genealogy_data', 'web_app.blueprints.tools.extract_genealogy_data'),
            ('generate_gedcom_file', 'web_app.blueprints.tools.generate_gedcom_file'),
            ('generate_research_questions', 'web_app.blueprints.tools.generate_research_questions')
        ]

        for task_name, patch_path in patches:
            patcher = patch(patch_path)
            mock_task = patcher.start()
            mocks[task_name] = mock_task

        # Cleanup after test
        yield mocks

        for _task_name, _patch_path in patches:
            try:
                patch.stopall()
            except Exception:
                pass

    def test_dashboard_route(self, client):
        """Test tools dashboard route"""
        response = client.get('/tools/')

        assert response.status_code == 200
        assert b'Tools Dashboard' in response.data

    def test_start_ocr_no_files_default_folder(self, client, mock_tasks, mock_job_file_repo):
        """Test starting OCR with no files uses default folder"""
        mock_task = mock_tasks['process_pdfs_ocr']
        mock_result = Mock()
        mock_result.id = 'test-task-id'
        mock_task.delay.return_value = mock_result

        response = client.post('/tools/start-ocr', data={})

        assert response.status_code == 302  # Redirect
        mock_task.delay.assert_called_once()

    def test_start_ocr_with_uploaded_files(self, client, mock_tasks, mock_job_file_repo):
        """Test starting OCR with uploaded files"""
        mock_task = mock_tasks['process_pdfs_ocr']
        mock_result = Mock()
        mock_result.id = 'test-task-id'
        mock_task.apply_async.return_value = mock_result

        mock_repo_instance = mock_job_file_repo.return_value
        mock_repo_instance.save_uploaded_file.return_value = 'file-id-123'

        # Create mock file upload
        data = {
            'pdf_files': (BytesIO(b'fake pdf content'), 'test.pdf')
        }

        response = client.post('/tools/start-ocr', data=data, content_type='multipart/form-data')

        assert response.status_code == 302
        mock_repo_instance.save_uploaded_file.assert_called_once()
        mock_task.apply_async.assert_called_once()

    def test_start_ocr_file_save_failure(self, client, mock_tasks, mock_job_file_repo):
        """Test OCR with file save failure"""
        mock_repo_instance = mock_job_file_repo.return_value
        mock_repo_instance.save_uploaded_file.return_value = None

        data = {
            'pdf_files': (BytesIO(b'fake pdf content'), 'test.pdf')
        }

        response = client.post('/tools/start-ocr', data=data, content_type='multipart/form-data')

        assert response.status_code == 302
        # Should redirect back to dashboard with error flash message

    def test_start_ocr_task_failure(self, client, mock_tasks, mock_job_file_repo):
        """Test OCR task start failure"""
        mock_task = mock_tasks['process_pdfs_ocr']
        mock_task.delay.side_effect = Exception("Task failed to start")

        response = client.post('/tools/start-ocr', data={})

        assert response.status_code == 302

    def test_start_extraction_no_file_uses_ocr_results(self, client, mock_tasks, mock_job_file_repo):
        """Test starting extraction with no file uses latest OCR results"""
        mock_task = mock_tasks['extract_genealogy_data']
        mock_result = Mock()
        mock_result.id = 'test-task-id'
        mock_task.apply_async.return_value = mock_result

        response = client.post('/tools/start-extraction', data={})

        assert response.status_code == 302
        mock_task.apply_async.assert_called_once()

    def test_start_extraction_with_uploaded_file(self, client, mock_tasks, mock_job_file_repo):
        """Test starting extraction with uploaded file"""
        mock_task = mock_tasks['extract_genealogy_data']
        mock_result = Mock()
        mock_result.id = 'test-task-id'
        mock_task.apply_async.return_value = mock_result

        mock_repo_instance = mock_job_file_repo.return_value
        mock_repo_instance.save_uploaded_file.return_value = 'file-id-123'

        data = {
            'text_file': (BytesIO(b'fake text content'), 'test.txt')
        }

        response = client.post('/tools/start-extraction', data=data, content_type='multipart/form-data')

        assert response.status_code == 302
        mock_repo_instance.save_uploaded_file.assert_called_once()
        mock_task.apply_async.assert_called_once()

    def test_start_extraction_file_save_failure(self, client, mock_tasks, mock_job_file_repo):
        """Test extraction with file save failure"""
        mock_repo_instance = mock_job_file_repo.return_value
        mock_repo_instance.save_uploaded_file.return_value = None

        data = {
            'text_file': (BytesIO(b'fake text content'), 'test.txt')
        }

        response = client.post('/tools/start-extraction', data=data, content_type='multipart/form-data')

        assert response.status_code == 302

    def test_start_extraction_task_failure(self, client, mock_tasks, mock_job_file_repo):
        """Test extraction task start failure"""
        mock_task = mock_tasks['extract_genealogy_data']
        mock_task.apply_async.side_effect = Exception("Task failed to start")

        response = client.post('/tools/start-extraction', data={})

        assert response.status_code == 302

    def test_start_gedcom_no_file_uses_extraction_results(self, client, mock_tasks, mock_job_file_repo):
        """Test starting GEDCOM with no file uses latest extraction results"""
        mock_task = mock_tasks['generate_gedcom_file']
        mock_result = Mock()
        mock_result.id = 'test-task-id'
        mock_task.apply_async.return_value = mock_result

        response = client.post('/tools/start-gedcom', data={})

        assert response.status_code == 302
        mock_task.apply_async.assert_called_once()

    def test_start_gedcom_with_uploaded_file(self, client, mock_tasks, mock_job_file_repo):
        """Test starting GEDCOM with uploaded file"""
        mock_task = mock_tasks['generate_gedcom_file']
        mock_result = Mock()
        mock_result.id = 'test-task-id'
        mock_task.apply_async.return_value = mock_result

        mock_repo_instance = mock_job_file_repo.return_value
        mock_repo_instance.save_uploaded_file.return_value = 'file-id-123'

        data = {
            'input_file': (BytesIO(b'fake input content'), 'test.json')
        }

        response = client.post('/tools/start-gedcom', data=data, content_type='multipart/form-data')

        assert response.status_code == 302
        mock_repo_instance.save_uploaded_file.assert_called_once()
        mock_task.apply_async.assert_called_once()

    def test_start_gedcom_file_save_failure(self, client, mock_tasks, mock_job_file_repo):
        """Test GEDCOM with file save failure"""
        mock_repo_instance = mock_job_file_repo.return_value
        mock_repo_instance.save_uploaded_file.return_value = None

        data = {
            'input_file': (BytesIO(b'fake input content'), 'test.json')
        }

        response = client.post('/tools/start-gedcom', data=data, content_type='multipart/form-data')

        assert response.status_code == 302

    def test_start_gedcom_task_failure(self, client, mock_tasks, mock_job_file_repo):
        """Test GEDCOM task start failure"""
        mock_task = mock_tasks['generate_gedcom_file']
        mock_task.apply_async.side_effect = Exception("Task failed to start")

        response = client.post('/tools/start-gedcom', data={})

        assert response.status_code == 302

    def test_start_research_no_file_uses_extraction_results(self, client, mock_tasks, mock_job_file_repo):
        """Test starting research with no file uses latest extraction results"""
        mock_task = mock_tasks['generate_research_questions']
        mock_result = Mock()
        mock_result.id = 'test-task-id'
        mock_task.apply_async.return_value = mock_result

        response = client.post('/tools/start-research', data={})

        assert response.status_code == 302
        mock_task.apply_async.assert_called_once()

    def test_start_research_with_uploaded_file(self, client, mock_tasks, mock_job_file_repo):
        """Test starting research with uploaded file"""
        mock_task = mock_tasks['generate_research_questions']
        mock_result = Mock()
        mock_result.id = 'test-task-id'
        mock_task.apply_async.return_value = mock_result

        mock_repo_instance = mock_job_file_repo.return_value
        mock_repo_instance.save_uploaded_file.return_value = 'file-id-123'

        data = {
            'input_file': (BytesIO(b'fake input content'), 'test.json')
        }

        response = client.post('/tools/start-research', data=data, content_type='multipart/form-data')

        assert response.status_code == 302
        mock_repo_instance.save_uploaded_file.assert_called_once()
        mock_task.apply_async.assert_called_once()

    def test_start_research_file_save_failure(self, client, mock_tasks, mock_job_file_repo):
        """Test research with file save failure"""
        mock_repo_instance = mock_job_file_repo.return_value
        mock_repo_instance.save_uploaded_file.return_value = None

        data = {
            'input_file': (BytesIO(b'fake input content'), 'test.json')
        }

        response = client.post('/tools/start-research', data=data, content_type='multipart/form-data')

        assert response.status_code == 302

    def test_start_research_task_failure(self, client, mock_tasks, mock_job_file_repo):
        """Test research task start failure"""
        mock_task = mock_tasks['generate_research_questions']
        mock_task.apply_async.side_effect = Exception("Task failed to start")

        response = client.post('/tools/start-research', data={})

        assert response.status_code == 302

    def test_api_jobs_endpoint(self, client):
        """Test API jobs endpoint returns empty jobs"""
        response = client.get('/tools/api/jobs')

        assert response.status_code == 200
        assert response.json == {'jobs': []}

    def test_cancel_job_success(self, client, mock_tasks):
        """Test successful job cancellation"""
        mock_task = mock_tasks['extract_genealogy_data']
        mock_result = Mock()
        mock_result.state = 'RUNNING'
        mock_task.AsyncResult.return_value = mock_result

        response = client.post('/tools/cancel/test-task-id')

        assert response.status_code == 302
        mock_task.AsyncResult.assert_called_with('test-task-id')
        mock_result.revoke.assert_called_once_with(terminate=True)

    def test_cancel_job_not_running(self, client, mock_tasks):
        """Test cancelling job that's not running"""
        mock_task = mock_tasks['extract_genealogy_data']
        mock_result = Mock()
        mock_result.state = 'SUCCESS'
        mock_task.AsyncResult.return_value = mock_result

        # Also mock the OCR task to return not running
        mock_ocr_task = mock_tasks['process_pdfs_ocr']
        mock_ocr_result = Mock()
        mock_ocr_result.state = 'SUCCESS'
        mock_ocr_task.AsyncResult.return_value = mock_ocr_result

        response = client.post('/tools/cancel/test-task-id')

        assert response.status_code == 302

    def test_cancel_job_exception(self, client, mock_tasks):
        """Test job cancellation with exception"""
        mock_task = mock_tasks['extract_genealogy_data']
        mock_task.AsyncResult.side_effect = Exception("Task not found")

        response = client.post('/tools/cancel/test-task-id')

        assert response.status_code == 302

    def test_download_result_success(self, client, mock_job_file_repo):
        """Test successful result download"""
        mock_repo_instance = mock_job_file_repo.return_value
        mock_download_file = Mock()
        mock_download_file.filename = 'result.txt'
        mock_download_file.file_data = b'test file content'
        mock_download_file.content_type = 'text/plain'
        mock_repo_instance.get_download_file.return_value = mock_download_file

        response = client.get('/tools/download/test-task-id')

        assert response.status_code == 200
        assert response.headers['Content-Disposition'] == 'attachment; filename=result.txt'
        mock_repo_instance.get_download_file.assert_called_once_with('test-task-id', None)

    def test_download_result_not_found(self, client, mock_job_file_repo):
        """Test download when no result file exists"""
        mock_repo_instance = mock_job_file_repo.return_value
        mock_repo_instance.get_download_file.return_value = None

        response = client.get('/tools/download/test-task-id')

        assert response.status_code == 302

    def test_download_result_exception(self, client, mock_job_file_repo):
        """Test download with exception"""
        mock_repo_instance = mock_job_file_repo.return_value
        mock_repo_instance.get_download_file.side_effect = Exception("Database error")

        response = client.get('/tools/download/test-task-id')

        assert response.status_code == 302

    def test_route_methods_get_routes(self, client):
        """Test that GET routes reject POST requests"""
        # GET routes should reject POST
        get_routes = ['/tools/', '/tools/api/jobs', '/tools/download/test-id']
        for route in get_routes:
            response = client.post(route)
            # Should return 405 (Method Not Allowed) or 404 (route might not exist for POST)
            assert response.status_code in [404, 405]

    def test_route_methods_post_routes(self, client):
        """Test that POST routes reject GET requests"""
        # POST routes should return 405 for GET requests
        post_routes = [
            '/tools/start-ocr',
            '/tools/start-extraction',
            '/tools/start-gedcom',
            '/tools/start-research',
            '/tools/cancel/test-id'
        ]
        for route in post_routes:
            response = client.get(route)
            assert response.status_code == 405

    def test_blueprint_url_prefix(self, client):
        """Test that all routes have correct /tools prefix"""
        # Test that routes without /tools prefix return 404
        response = client.get('/start-ocr')
        assert response.status_code == 404

        response = client.post('/start-extraction')
        assert response.status_code == 404

    @patch('web_app.blueprints.tools.uuid.uuid4')
    def test_task_id_generation(self, mock_uuid, client, mock_tasks, mock_job_file_repo):
        """Test that task IDs are generated consistently"""
        test_uuid = uuid.UUID('12345678-1234-5678-9012-123456789012')
        mock_uuid.return_value = test_uuid

        mock_task = mock_tasks['process_pdfs_ocr']
        mock_result = Mock()
        mock_result.id = str(test_uuid)
        mock_task.apply_async.return_value = mock_result

        mock_repo_instance = mock_job_file_repo.return_value
        mock_repo_instance.save_uploaded_file.return_value = 'file-id-123'

        data = {
            'pdf_files': (BytesIO(b'fake pdf content'), 'test.pdf')
        }

        response = client.post('/tools/start-ocr', data=data, content_type='multipart/form-data')

        assert response.status_code == 302
        mock_task.apply_async.assert_called_once_with(task_id=str(test_uuid))

    def test_multiple_file_upload(self, client, mock_tasks, mock_job_file_repo):
        """Test uploading multiple files"""
        mock_task = mock_tasks['process_pdfs_ocr']
        mock_result = Mock()
        mock_result.id = 'test-task-id'
        mock_task.apply_async.return_value = mock_result

        mock_repo_instance = mock_job_file_repo.return_value
        mock_repo_instance.save_uploaded_file.return_value = 'file-id-123'

        data = {
            'pdf_files': [
                (BytesIO(b'fake pdf 1'), 'test1.pdf'),
                (BytesIO(b'fake pdf 2'), 'test2.pdf')
            ]
        }

        response = client.post('/tools/start-ocr', data=data, content_type='multipart/form-data')

        assert response.status_code == 302
        # Should call save_uploaded_file twice
        assert mock_repo_instance.save_uploaded_file.call_count == 2

    def test_empty_filename_handling(self, client, mock_tasks, mock_job_file_repo):
        """Test handling of files with empty filenames"""
        mock_task = mock_tasks['process_pdfs_ocr']
        mock_result = Mock()
        mock_result.id = 'test-task-id'
        mock_task.delay.return_value = mock_result

        # Simulate file input with empty filename
        data = {
            'pdf_files': (BytesIO(b''), '')
        }

        response = client.post('/tools/start-ocr', data=data, content_type='multipart/form-data')

        assert response.status_code == 302
        # Should use default folder path when filename is empty
        mock_task.delay.assert_called_once()

    # Job Status API Tests
    def test_api_jobs_empty_list(self, client):
        """Test /api/jobs returns empty list"""
        response = client.get('/tools/api/jobs')

        assert response.status_code == 200
        assert response.json == {'jobs': []}

    @patch('web_app.blueprints.tools.celery_app')
    def test_api_job_status_pending(self, mock_celery_app, client):
        """Test job status API with PENDING task"""
        mock_result = Mock()
        mock_result.state = 'PENDING'
        mock_result.info = None
        mock_result.result = None
        mock_result.name = 'web_app.tasks.ocr_tasks.process_pdfs_ocr'
        mock_celery_app.AsyncResult.return_value = mock_result

        response = client.get('/tools/api/jobs/test-task-id/status')

        assert response.status_code == 200
        data = response.json
        assert data['task_id'] == 'test-task-id'
        assert data['status'] == 'pending'
        assert data['task_type'] == 'ocr'
        assert data['message'] == 'Task is waiting to be processed'
        assert data['progress'] == 0

    @patch('web_app.blueprints.tools.celery_app')
    def test_api_job_status_running_with_progress(self, mock_celery_app, client):
        """Test job status API with RUNNING task that has progress info"""
        mock_result = Mock()
        mock_result.state = 'RUNNING'
        mock_result.info = {'progress': 75, 'status': 'Processing page 3 of 4'}
        mock_result.name = 'web_app.tasks.extraction_tasks.extract_genealogy_data'
        mock_celery_app.AsyncResult.return_value = mock_result

        response = client.get('/tools/api/jobs/test-task-id/status')

        assert response.status_code == 200
        data = response.json
        assert data['status'] == 'running'
        assert data['task_type'] == 'extraction'
        assert data['progress'] == 75
        assert data['message'] == 'Processing page 3 of 4'

    @patch('web_app.blueprints.tools.celery_app')
    def test_api_job_status_running_no_progress(self, mock_celery_app, client):
        """Test job status API with RUNNING task without progress info"""
        mock_result = Mock()
        mock_result.state = 'RUNNING'
        mock_result.info = None
        mock_result.name = 'web_app.tasks.gedcom_tasks.generate_gedcom_file'
        mock_celery_app.AsyncResult.return_value = mock_result

        response = client.get('/tools/api/jobs/test-task-id/status')

        assert response.status_code == 200
        data = response.json
        assert data['status'] == 'running'
        assert data['task_type'] == 'gedcom'
        assert data['progress'] == 50
        assert data['message'] == 'Task is running'

    @patch('web_app.blueprints.tools.celery_app')
    def test_api_job_status_success(self, mock_celery_app, client):
        """Test job status API with successful task"""
        mock_result = Mock()
        mock_result.state = 'SUCCESS'
        mock_result.result = {'success': True, 'questions': ['Question 1', 'Question 2'], 'download_available': True}
        mock_result.name = 'web_app.tasks.research_tasks.generate_research_questions'
        mock_celery_app.AsyncResult.return_value = mock_result

        response = client.get('/tools/api/jobs/test-task-id/status')

        assert response.status_code == 200
        data = response.json
        assert data['status'] == 'success'
        assert data['task_type'] == 'research'
        assert data['progress'] == 100
        assert data['message'] == 'Task completed successfully'
        assert data['success'] is True
        assert data['download_available'] is True

    @patch('web_app.blueprints.tools.celery_app')
    def test_api_job_status_success_no_download(self, mock_celery_app, client):
        """Test job status API with successful task but no download available"""
        mock_result = Mock()
        mock_result.state = 'SUCCESS'
        mock_result.result = {'success': True, 'questions': []}  # No download_available field
        mock_result.name = 'web_app.tasks.research_tasks.generate_research_questions'
        mock_celery_app.AsyncResult.return_value = mock_result

        response = client.get('/tools/api/jobs/test-task-id/status')

        assert response.status_code == 200
        data = response.json
        assert data['status'] == 'success'
        assert data['download_available'] is False  # Should default to False

    @patch('web_app.blueprints.tools.celery_app')
    def test_api_job_status_failure_with_dict_error(self, mock_celery_app, client):
        """Test job status API with failed task containing dict error"""
        mock_result = Mock()
        mock_result.state = 'FAILURE'
        mock_result.result = {'error': 'File not found: input.txt'}
        mock_result.name = 'web_app.tasks.ocr_tasks.process_pdfs_ocr'
        mock_celery_app.AsyncResult.return_value = mock_result

        response = client.get('/tools/api/jobs/test-task-id/status')

        assert response.status_code == 200
        data = response.json
        assert data['status'] == 'failure'
        assert data['task_type'] == 'ocr'
        assert data['progress'] == 0
        assert data['message'] == 'File not found: input.txt'
        assert data['error'] == 'File not found: input.txt'

    @patch('web_app.blueprints.tools.celery_app')
    def test_api_job_status_failure_with_string_error(self, mock_celery_app, client):
        """Test job status API with failed task containing string error"""
        mock_result = Mock()
        mock_result.state = 'FAILURE'
        mock_result.result = 'Connection timeout error'
        mock_result.name = 'web_app.tasks.extraction_tasks.extract_genealogy_data'
        mock_celery_app.AsyncResult.return_value = mock_result

        response = client.get('/tools/api/jobs/test-task-id/status')

        assert response.status_code == 200
        data = response.json
        assert data['status'] == 'failure'
        assert data['message'] == 'Connection timeout error'
        assert data['error'] == 'Connection timeout error'

    @patch('web_app.blueprints.tools.celery_app')
    def test_api_job_status_failure_no_result(self, mock_celery_app, client):
        """Test job status API with failed task without result"""
        mock_result = Mock()
        mock_result.state = 'FAILURE'
        mock_result.result = None
        mock_result.name = 'web_app.tasks.gedcom_tasks.generate_gedcom_file'
        mock_celery_app.AsyncResult.return_value = mock_result

        response = client.get('/tools/api/jobs/test-task-id/status')

        assert response.status_code == 200
        data = response.json
        assert data['status'] == 'failure'
        assert data['message'] == 'Task failed with unknown error'
        assert data['error'] == 'Task failed with unknown error'

    @patch('web_app.blueprints.tools.celery_app')
    def test_api_job_status_retry(self, mock_celery_app, client):
        """Test job status API with retrying task"""
        mock_result = Mock()
        mock_result.state = 'RETRY'
        mock_result.info = {'progress': 30, 'status': 'Retrying after connection error'}
        mock_result.name = 'web_app.tasks.research_tasks.generate_research_questions'
        mock_celery_app.AsyncResult.return_value = mock_result

        response = client.get('/tools/api/jobs/test-task-id/status')

        assert response.status_code == 200
        data = response.json
        assert data['status'] == 'retry'
        assert data['progress'] == 30
        assert data['message'] == 'Retrying after connection error'

    @patch('web_app.blueprints.tools.celery_app')
    def test_api_job_status_unknown_state(self, mock_celery_app, client):
        """Test job status API with unknown task state"""
        mock_result = Mock()
        mock_result.state = 'REVOKED'
        mock_result.name = 'web_app.tasks.ocr_tasks.process_pdfs_ocr'
        mock_celery_app.AsyncResult.return_value = mock_result

        response = client.get('/tools/api/jobs/test-task-id/status')

        assert response.status_code == 200
        data = response.json
        assert data['status'] == 'revoked'
        assert data['message'] == 'Task state: REVOKED'
        assert data['progress'] == 0

    @patch('web_app.blueprints.tools.celery_app')
    def test_api_job_status_unknown_task_type(self, mock_celery_app, client):
        """Test job status API with unknown task type"""
        mock_result = Mock()
        mock_result.state = 'SUCCESS'
        mock_result.result = {'success': True}
        mock_result.name = 'web_app.tasks.unknown_tasks.some_task'
        mock_celery_app.AsyncResult.return_value = mock_result

        response = client.get('/tools/api/jobs/test-task-id/status')

        assert response.status_code == 200
        data = response.json
        assert data['task_type'] == 'unknown'

    @patch('web_app.blueprints.tools.celery_app')
    def test_api_job_status_no_task_name(self, mock_celery_app, client):
        """Test job status API with task that has no name"""
        mock_result = Mock()
        mock_result.state = 'SUCCESS'
        mock_result.result = {'success': True}
        mock_result.name = None
        mock_celery_app.AsyncResult.return_value = mock_result

        response = client.get('/tools/api/jobs/test-task-id/status')

        assert response.status_code == 200
        data = response.json
        assert data['task_type'] == 'unknown'

    @patch('web_app.blueprints.tools.celery_app')
    def test_api_job_status_connection_error(self, mock_celery_app, client):
        """Test job status API with Redis connection error"""
        from kombu.exceptions import ConnectionError
        mock_celery_app.AsyncResult.side_effect = ConnectionError('Connection refused')

        response = client.get('/tools/api/jobs/test-task-id/status')

        assert response.status_code == 503
        data = response.json
        assert data['status'] == 'error'
        assert data['message'] == 'Unable to connect to task queue'

    @patch('web_app.blueprints.tools.celery_app')
    def test_api_job_status_attribute_error(self, mock_celery_app, client):
        """Test job status API with invalid task ID format"""
        mock_celery_app.AsyncResult.side_effect = AttributeError('Invalid task ID')

        response = client.get('/tools/api/jobs/test-task-id/status')

        assert response.status_code == 400
        data = response.json
        assert data['status'] == 'error'
        assert data['message'] == 'Invalid task ID format'

    @patch('web_app.blueprints.tools.celery_app')
    def test_api_job_status_unexpected_error(self, mock_celery_app, client):
        """Test job status API with unexpected error"""
        mock_celery_app.AsyncResult.side_effect = RuntimeError('Unexpected error')

        response = client.get('/tools/api/jobs/test-task-id/status')

        assert response.status_code == 500
        data = response.json
        assert data['status'] == 'error'
        assert data['message'] == 'Unable to retrieve task status'

    # Test helper functions
    def test_extract_task_type_ocr(self):
        """Test _extract_task_type for OCR tasks"""
        from web_app.blueprints.tools import _extract_task_type

        mock_result = Mock()
        mock_result.name = 'web_app.tasks.ocr_tasks.process_pdfs_ocr'

        task_type = _extract_task_type(mock_result)
        assert task_type == 'ocr'

    def test_extract_task_type_extraction(self):
        """Test _extract_task_type for extraction tasks"""
        from web_app.blueprints.tools import _extract_task_type

        mock_result = Mock()
        mock_result.name = 'web_app.tasks.extraction_tasks.extract_genealogy_data'

        task_type = _extract_task_type(mock_result)
        assert task_type == 'extraction'

    def test_extract_task_type_gedcom(self):
        """Test _extract_task_type for GEDCOM tasks"""
        from web_app.blueprints.tools import _extract_task_type

        mock_result = Mock()
        mock_result.name = 'web_app.tasks.gedcom_tasks.generate_gedcom_file'

        task_type = _extract_task_type(mock_result)
        assert task_type == 'gedcom'

    def test_extract_task_type_research(self):
        """Test _extract_task_type for research tasks"""
        from web_app.blueprints.tools import _extract_task_type

        mock_result = Mock()
        mock_result.name = 'web_app.tasks.research_tasks.generate_research_questions'

        task_type = _extract_task_type(mock_result)
        assert task_type == 'research'

    def test_extract_failure_message_dict_with_error(self):
        """Test _extract_failure_message with dict containing error key"""
        from web_app.blueprints.tools import _extract_failure_message

        mock_result = Mock()
        mock_result.result = {'error': 'File not found'}

        message = _extract_failure_message(mock_result)
        assert message == 'File not found'

    def test_extract_failure_message_dict_with_message(self):
        """Test _extract_failure_message with dict containing message key"""
        from web_app.blueprints.tools import _extract_failure_message

        mock_result = Mock()
        mock_result.result = {'message': 'Processing failed'}

        message = _extract_failure_message(mock_result)
        assert message == 'Processing failed'

    def test_extract_failure_message_string(self):
        """Test _extract_failure_message with string result"""
        from web_app.blueprints.tools import _extract_failure_message

        mock_result = Mock()
        mock_result.result = 'Connection timeout'

        message = _extract_failure_message(mock_result)
        assert message == 'Connection timeout'

    def test_extract_failure_message_no_result(self):
        """Test _extract_failure_message with no result"""
        from web_app.blueprints.tools import _extract_failure_message

        mock_result = Mock()
        mock_result.result = None

        message = _extract_failure_message(mock_result)
        assert message == 'Task failed with unknown error'
