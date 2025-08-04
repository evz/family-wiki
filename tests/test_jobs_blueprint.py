"""
Tests for jobs blueprint - job status management, cancellation, and downloads
"""

import io
from unittest.mock import Mock, patch

import pytest

from tests.conftest import BaseTestConfig
from web_app.database.models import JobFile


class JobsBlueprintTestConfig(BaseTestConfig):
    """Test configuration for jobs blueprint tests"""
    def __init__(self):
        super().__init__()


class TestJobsAPI:
    """Test jobs API endpoints"""

    def test_api_jobs_list(self, client):
        """Test API endpoint for listing all jobs"""
        response = client.get('/jobs/api/jobs')
        assert response.status_code == 200
        
        data = response.get_json()
        assert 'jobs' in data
        assert isinstance(data['jobs'], list)

    @patch('web_app.blueprints.jobs.celery_app')
    def test_api_job_status_success(self, mock_celery_app, client):
        """Test API endpoint for successful job status"""
        # Mock successful task
        mock_task = Mock()
        mock_task.state = 'SUCCESS'
        mock_task.result = {
            'success': True,
            'download_available': True,
            'output_file': '/path/to/output.txt'
        }
        mock_task.name = 'web_app.tasks.ocr_tasks.process_pdfs_ocr'
        mock_celery_app.AsyncResult.return_value = mock_task

        response = client.get('/jobs/api/jobs/test-task-id/status')
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['task_id'] == 'test-task-id'
        assert data['status'] == 'success'
        assert data['task_type'] == 'ocr'
        assert data['progress'] == 100
        assert data['success'] is True

    @patch('web_app.blueprints.jobs.celery_app')
    def test_api_job_status_running(self, mock_celery_app, client):
        """Test API endpoint for running job status"""
        # Mock running task with progress info
        mock_task = Mock()
        mock_task.state = 'RUNNING'
        mock_task.info = {
            'status': 'processing',
            'progress': 45
        }
        mock_task.name = 'web_app.tasks.extraction_tasks.extract_genealogy_data'
        mock_celery_app.AsyncResult.return_value = mock_task

        response = client.get('/jobs/api/jobs/test-task-id/status')
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['task_id'] == 'test-task-id'
        assert data['status'] == 'running'
        assert data['task_type'] == 'extraction'
        assert data['progress'] == 45

    @patch('web_app.blueprints.jobs.celery_app')
    def test_api_job_status_failure(self, mock_celery_app, client):
        """Test API endpoint for failed job status"""
        # Mock failed task
        mock_task = Mock()
        mock_task.state = 'FAILURE'
        mock_task.result = Exception('OCR processing failed')
        mock_task.traceback = 'Traceback...'
        mock_task.name = 'web_app.tasks.ocr_tasks.process_pdfs_ocr'
        mock_celery_app.AsyncResult.return_value = mock_task

        response = client.get('/jobs/api/jobs/test-task-id/status')
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['task_id'] == 'test-task-id'
        assert data['status'] == 'failure'
        assert data['task_type'] == 'ocr'
        assert data['progress'] == 0
        assert 'OCR processing failed' in data['error']

    @patch('web_app.blueprints.jobs.celery_app')
    def test_api_job_status_pending(self, mock_celery_app, client):
        """Test API endpoint for pending job status"""
        # Mock pending task
        mock_task = Mock()
        mock_task.state = 'PENDING'
        mock_task.result = None
        mock_task.name = 'web_app.tasks.gedcom_tasks.generate_gedcom_file'
        mock_celery_app.AsyncResult.return_value = mock_task

        response = client.get('/jobs/api/jobs/test-task-id/status')
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['task_id'] == 'test-task-id'
        assert data['status'] == 'pending'
        assert data['task_type'] == 'gedcom'
        assert data['progress'] == 0

    @patch('web_app.blueprints.jobs.celery_app')
    def test_api_job_status_unknown_task_type(self, mock_celery_app, client):
        """Test API endpoint with unknown task type"""
        # Mock task with unknown name
        mock_task = Mock()
        mock_task.state = 'SUCCESS'
        mock_task.result = {'success': True}
        mock_task.name = 'unknown.task.name'
        mock_celery_app.AsyncResult.return_value = mock_task

        response = client.get('/jobs/api/jobs/test-task-id/status')
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['task_type'] == 'unknown'

    @patch('web_app.blueprints.jobs.celery_app')
    def test_api_job_status_connection_error(self, mock_celery_app, client):
        """Test API endpoint with connection error"""
        from kombu.exceptions import ConnectionError
        
        # Mock connection error
        mock_celery_app.AsyncResult.side_effect = ConnectionError("Cannot connect to Redis")

        response = client.get('/jobs/api/jobs/test-task-id/status')
        assert response.status_code == 503
        
        data = response.get_json()
        assert 'error' in data
        assert 'Unable to connect to task queue' in data['error']


class TestJobCancellation:
    """Test job cancellation functionality"""

    @patch('web_app.blueprints.jobs.extract_genealogy_data')
    @patch('web_app.blueprints.jobs.process_pdfs_ocr')
    def test_cancel_job_success(self, mock_ocr_task, mock_extract_task, client):
        """Test successful job cancellation"""
        # Mock running task
        mock_task = Mock()
        mock_task.state = 'RUNNING'
        mock_extract_task.AsyncResult.return_value = mock_task

        response = client.post('/jobs/cancel/test-task-id')
        assert response.status_code == 302  # Redirect after cancellation
        
        # Verify task was revoked
        mock_task.revoke.assert_called_once_with(terminate=True)

    @patch('web_app.blueprints.jobs.extract_genealogy_data')
    @patch('web_app.blueprints.jobs.process_pdfs_ocr')
    def test_cancel_job_already_completed(self, mock_ocr_task, mock_extract_task, client):
        """Test cancellation of already completed job"""
        # Mock completed task
        mock_task = Mock()
        mock_task.state = 'SUCCESS'
        mock_extract_task.AsyncResult.return_value = mock_task
        mock_ocr_task.AsyncResult.return_value = mock_task

        response = client.post('/jobs/cancel/test-task-id')
        assert response.status_code == 302  # Redirect with message
        
        # Verify task was not revoked
        mock_task.revoke.assert_not_called()

    @patch('web_app.blueprints.jobs.extract_genealogy_data')
    @patch('web_app.blueprints.jobs.process_pdfs_ocr')
    def test_cancel_job_connection_error(self, mock_ocr_task, mock_extract_task, client):
        """Test job cancellation with connection error"""
        from kombu.exceptions import ConnectionError
        
        # Mock connection error
        mock_extract_task.AsyncResult.side_effect = ConnectionError("Cannot connect to Redis")
        mock_ocr_task.AsyncResult.side_effect = ConnectionError("Cannot connect to Redis")

        response = client.post('/jobs/cancel/test-task-id')
        assert response.status_code == 302  # Redirect with error message

    @patch('web_app.blueprints.jobs.extract_genealogy_data')
    @patch('web_app.blueprints.jobs.process_pdfs_ocr')
    def test_cancel_job_amqp_error(self, mock_ocr_task, mock_extract_task, client):
        """Test job cancellation with AMQP error"""
        import amqp.exceptions
        
        # Mock AMQP error during revoke
        mock_task = Mock()
        mock_task.state = 'RUNNING'
        mock_task.revoke.side_effect = amqp.exceptions.ConnectionError("AMQP connection failed")
        mock_extract_task.AsyncResult.return_value = mock_task

        response = client.post('/jobs/cancel/test-task-id')
        assert response.status_code == 302  # Redirect with error message


class TestJobDownloads:
    """Test job file download functionality"""

    @pytest.fixture
    def mock_job_file_repo(self):
        """Mock JobFileRepository"""
        with patch('web_app.blueprints.jobs.JobFileRepository') as mock_repo_class:
            yield mock_repo_class

    def test_download_job_file_success(self, client, db, mock_job_file_repo):
        """Test successful job file download"""
        # Create test job file
        job_file = JobFile(
            task_id='test-task-id',
            filename='test_output.txt',
            file_data=b'Test file content',
            file_size=len(b'Test file content'),
            content_type='text/plain',
            job_type='test',
            file_type='output'
        )
        db.session.add(job_file)
        db.session.flush()

        # Mock repository
        mock_repo_instance = mock_job_file_repo.return_value
        mock_repo_instance.get_download_file.return_value = job_file

        response = client.get(f'/jobs/download/{job_file.task_id}')
        assert response.status_code == 200
        assert 'text/plain' in response.headers['Content-Type']
        assert b'Test file content' in response.data

    def test_download_job_file_not_found(self, client, mock_job_file_repo):
        """Test download of non-existent job file"""
        # Mock repository to return None
        mock_repo_instance = mock_job_file_repo.return_value
        mock_repo_instance.get_download_file.return_value = None

        response = client.get('/jobs/download/nonexistent-id')
        assert response.status_code == 302  # Redirect with error message

    def test_download_job_file_database_error(self, client, mock_job_file_repo):
        """Test download with database error"""
        # Mock repository to raise generic error (blueprint_utils handles it)
        mock_repo_instance = mock_job_file_repo.return_value
        mock_repo_instance.get_download_file.side_effect = Exception("Database connection failed")

        response = client.get('/jobs/download/test-id')
        assert response.status_code == 302  # Redirect with error message


class TestJobUtilityFunctions:
    """Test utility functions in jobs blueprint"""

    def test_extract_task_type_ocr(self):
        """Test task type extraction for OCR tasks"""
        from web_app.blueprints.jobs import _extract_task_type
        
        mock_task = Mock()
        mock_task.name = 'web_app.tasks.ocr_tasks.process_pdfs_ocr'
        
        task_type = _extract_task_type(mock_task)
        assert task_type == 'ocr'

    def test_extract_task_type_extraction(self):
        """Test task type extraction for extraction tasks"""
        from web_app.blueprints.jobs import _extract_task_type
        
        mock_task = Mock()
        mock_task.name = 'web_app.tasks.extraction_tasks.extract_genealogy_data'
        
        task_type = _extract_task_type(mock_task)
        assert task_type == 'extraction'

    def test_extract_task_type_gedcom(self):
        """Test task type extraction for GEDCOM tasks"""
        from web_app.blueprints.jobs import _extract_task_type
        
        mock_task = Mock()
        mock_task.name = 'web_app.tasks.gedcom_tasks.generate_gedcom_file'
        
        task_type = _extract_task_type(mock_task)
        assert task_type == 'gedcom'

    def test_extract_task_type_research(self):
        """Test task type extraction for research tasks"""
        from web_app.blueprints.jobs import _extract_task_type
        
        mock_task = Mock()
        mock_task.name = 'web_app.tasks.research_tasks.generate_research_questions'
        
        task_type = _extract_task_type(mock_task)
        assert task_type == 'research'

    def test_extract_task_type_rag(self):
        """Test task type extraction for RAG tasks"""
        from web_app.blueprints.jobs import _extract_task_type
        
        mock_task = Mock()
        mock_task.name = 'web_app.tasks.rag_tasks.process_corpus'
        
        task_type = _extract_task_type(mock_task)
        assert task_type == 'unknown'  # RAG tasks aren't handled in current implementation

    def test_extract_task_type_unknown(self):
        """Test task type extraction for unknown tasks"""
        from web_app.blueprints.jobs import _extract_task_type
        
        mock_task = Mock()
        mock_task.name = 'unknown.module.task_name'
        
        task_type = _extract_task_type(mock_task)
        assert task_type == 'unknown'

    def test_extract_task_type_none(self):
        """Test task type extraction with None task name"""
        from web_app.blueprints.jobs import _extract_task_type
        
        mock_task = Mock()
        mock_task.name = None
        
        task_type = _extract_task_type(mock_task)
        assert task_type == 'unknown'


