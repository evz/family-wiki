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
