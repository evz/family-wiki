"""
Comprehensive functional tests for the new blueprint structure
"""

import uuid
from io import BytesIO
from unittest.mock import Mock, patch

import pytest
from flask import url_for

from tests.conftest import BaseTestConfig
from web_app import create_app


class BlueprintFunctionalTestConfig(BaseTestConfig):
    """Test configuration"""
    def __init__(self):
        super().__init__()
        self.sqlalchemy_database_uri = 'sqlite:///:memory:'


class TestBlueprintFunctionality:
    """Test that the new blueprint structure actually works correctly"""

    @pytest.fixture
    def app(self):
        """Create test Flask app"""
        app = create_app(BlueprintFunctionalTestConfig())
        return app

    @pytest.fixture
    def client(self, app):
        """Create test client"""
        return app.test_client()

    @pytest.fixture
    def mock_file_repo(self):
        """Mock job file repository"""
        with patch('web_app.blueprints.ocr.JobFileRepository') as mock_ocr_repo, \
             patch('web_app.blueprints.extraction.JobFileRepository') as mock_ext_repo, \
             patch('web_app.blueprints.gedcom.JobFileRepository') as mock_gedcom_repo, \
             patch('web_app.blueprints.research.JobFileRepository') as mock_research_repo, \
             patch('web_app.blueprints.jobs.JobFileRepository') as mock_jobs_repo:

            # Configure all mocks to return the same behavior
            mock_instance = Mock()
            mock_instance.save_uploaded_file.return_value = 'test-file-id'
            mock_instance.get_download_file.return_value = None

            mock_ocr_repo.return_value = mock_instance
            mock_ext_repo.return_value = mock_instance
            mock_gedcom_repo.return_value = mock_instance
            mock_research_repo.return_value = mock_instance
            mock_jobs_repo.return_value = mock_instance

            yield mock_instance

    @pytest.fixture
    def mock_celery_tasks(self):
        """Mock all Celery tasks"""
        patches = {
            'ocr': patch('web_app.blueprints.ocr.process_pdfs_ocr'),
            'extraction': patch('web_app.blueprints.extraction.extract_genealogy_data'),
            'gedcom': patch('web_app.blueprints.gedcom.generate_gedcom_file'),
            'research': patch('web_app.blueprints.research.generate_research_questions'),
            'jobs_ocr': patch('web_app.blueprints.jobs.process_pdfs_ocr'),
            'jobs_extraction': patch('web_app.blueprints.jobs.extract_genealogy_data'),
        }

        mocks = {}
        started_patches = []

        try:
            for name, patch_obj in patches.items():
                started_patch = patch_obj.start()
                started_patches.append(patch_obj)

                # Configure task mock
                mock_task = Mock()
                mock_task.id = f'test-task-{uuid.uuid4()}'
                mock_task.delay.return_value = mock_task
                mock_task.apply_async.return_value = mock_task
                mock_task.AsyncResult.return_value = mock_task
                mock_task.state = 'SUCCESS'
                mock_task.result = {'success': True}

                started_patch.return_value = mock_task
                started_patch.delay.return_value = mock_task
                started_patch.apply_async.return_value = mock_task
                started_patch.AsyncResult.return_value = mock_task

                mocks[name] = started_patch

            yield mocks

        finally:
            for patch_obj in started_patches:
                patch_obj.stop()

    def test_blueprint_registration(self, app):
        """Test that all blueprints are properly registered"""
        blueprint_names = [bp.name for bp in app.blueprints.values()]

        expected_blueprints = [
            'main', 'prompts', 'ocr', 'extraction', 'gedcom',
            'research', 'jobs', 'entities', 'rag'
        ]

        for blueprint_name in expected_blueprints:
            assert blueprint_name in blueprint_names, f"Blueprint '{blueprint_name}' not registered"

    def test_blueprint_url_prefixes(self, app):
        """Test that blueprints have correct URL prefixes"""
        with app.app_context():
            assert url_for('ocr.start_ocr').startswith('/ocr/')
            assert url_for('extraction.start_extraction').startswith('/extraction/')
            assert url_for('gedcom.start_gedcom').startswith('/gedcom/')
            assert url_for('research.start_research').startswith('/research/')
            assert url_for('jobs.api_jobs').startswith('/jobs/')

    def test_ocr_blueprint_no_files(self, client, mock_celery_tasks):
        """Test OCR blueprint with no files (uses default folder)"""
        response = client.post('/ocr/start')

        assert response.status_code == 302  # Redirect
        assert response.location.endswith('/')  # Redirects to main page

        # Verify task was called
        mock_celery_tasks['ocr'].delay.assert_called_once()

    def test_ocr_blueprint_with_files(self, client, mock_file_repo, mock_celery_tasks):
        """Test OCR blueprint with uploaded files"""
        test_file = BytesIO(b'test pdf content')
        test_file.name = 'test.pdf'

        response = client.post('/ocr/start', data={
            'pdf_files': [(test_file, 'test.pdf')]
        })

        assert response.status_code == 302
        mock_file_repo.save_uploaded_file.assert_called_once()
        mock_celery_tasks['ocr'].apply_async.assert_called_once()

    def test_extraction_blueprint_no_file(self, client, mock_celery_tasks):
        """Test extraction blueprint with no file (uses latest OCR)"""
        response = client.post('/extraction/start')

        assert response.status_code == 302
        mock_celery_tasks['extraction'].apply_async.assert_called_once()

    def test_extraction_blueprint_with_file(self, client, mock_file_repo, mock_celery_tasks):
        """Test extraction blueprint with uploaded file"""
        test_file = BytesIO(b'test text content')
        test_file.name = 'test.txt'

        response = client.post('/extraction/start', data={
            'text_file': (test_file, 'test.txt')
        })

        assert response.status_code == 302
        mock_file_repo.save_uploaded_file.assert_called_once()
        mock_celery_tasks['extraction'].apply_async.assert_called_once()

    def test_gedcom_blueprint_no_file(self, client, mock_celery_tasks):
        """Test GEDCOM blueprint with no file (uses latest extraction)"""
        response = client.post('/gedcom/start')

        assert response.status_code == 302
        mock_celery_tasks['gedcom'].apply_async.assert_called_once()

    def test_research_blueprint_no_file(self, client, mock_celery_tasks):
        """Test research blueprint with no file (uses latest extraction)"""
        response = client.post('/research/start')

        assert response.status_code == 302
        mock_celery_tasks['research'].apply_async.assert_called_once()

    @patch('web_app.blueprints.jobs.celery_app')
    def test_jobs_api_status_success(self, mock_celery_app, client):
        """Test jobs API returns correct status for successful task"""
        mock_task = Mock()
        mock_task.state = 'SUCCESS'
        mock_task.result = {'success': True, 'download_available': True}
        mock_task.name = 'web_app.tasks.ocr_tasks.process_pdfs_ocr'

        mock_celery_app.AsyncResult.return_value = mock_task

        response = client.get('/jobs/api/jobs/test-task-id/status')

        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert data['task_type'] == 'ocr'
        assert data['progress'] == 100
        assert data['success'] is True

    @patch('web_app.blueprints.jobs.celery_app')
    def test_jobs_api_status_failure(self, mock_celery_app, client):
        """Test jobs API returns correct status for failed task"""
        mock_task = Mock()
        mock_task.state = 'FAILURE'
        mock_task.result = {'error': 'Task failed due to OCR error'}
        mock_task.name = 'web_app.tasks.extraction_tasks.extract_genealogy_data'

        mock_celery_app.AsyncResult.return_value = mock_task

        response = client.get('/jobs/api/jobs/test-task-id/status')

        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'failure'
        assert data['task_type'] == 'extraction'
        assert data['progress'] == 0
        assert 'Task failed due to OCR error' in data['error']

    def test_jobs_cancel_success(self, client, mock_celery_tasks):
        """Test job cancellation for running task"""
        mock_task = Mock()
        mock_task.state = 'RUNNING'
        mock_celery_tasks['jobs_ocr'].AsyncResult.return_value = mock_task

        response = client.post('/jobs/cancel/test-task-id')

        assert response.status_code == 302
        mock_task.revoke.assert_called_once_with(terminate=True)

    def test_error_handling_task_submission_failure(self, client):
        """Test that task submission errors are handled correctly"""
        with patch('web_app.blueprints.ocr.safe_task_submit') as mock_safe_task:
            from web_app.blueprints.error_handling import TaskSubmissionError
            mock_safe_task.side_effect = TaskSubmissionError('Redis down')

            response = client.post('/ocr/start')

            assert response.status_code == 302  # Should redirect due to error

    def test_jobs_api_list_endpoint(self, client):
        """Test jobs list API endpoint"""
        response = client.get('/jobs/api/jobs')

        assert response.status_code == 200
        data = response.get_json()
        assert 'jobs' in data
        assert isinstance(data['jobs'], list)

    def test_multiple_file_upload_ocr(self, client, mock_file_repo, mock_celery_tasks):
        """Test OCR blueprint with multiple files"""
        test_files = [
            (BytesIO(b'pdf1'), 'file1.pdf'),
            (BytesIO(b'pdf2'), 'file2.pdf'),
            (BytesIO(b'pdf3'), 'file3.pdf')
        ]

        response = client.post('/ocr/start', data={
            'pdf_files': test_files
        })

        assert response.status_code == 302
        assert mock_file_repo.save_uploaded_file.call_count == 3
        mock_celery_tasks['ocr'].apply_async.assert_called_once()
