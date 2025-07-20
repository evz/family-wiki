"""
Tests for extraction blueprint endpoints
"""

import json
from unittest.mock import Mock, patch

import pytest

from app import Config, create_app


class ExtractionTestConfig(Config):
    """Test configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    CELERY_BROKER_URL = 'memory://'
    CELERY_RESULT_BACKEND = 'cache+memory://'


class TestExtractionBlueprint:
    """Test extraction blueprint endpoints"""

    @pytest.fixture
    def app(self):
        """Create test Flask app"""
        app = create_app(ExtractionTestConfig)
        return app

    @pytest.fixture
    def client(self, app):
        """Create test client"""
        return app.test_client()

    @pytest.fixture
    def mock_extraction_task(self):
        """Mock extraction task"""
        with patch('web_app.blueprints.extraction.extract_genealogy_data') as mock_task:
            yield mock_task

    def test_start_extraction_success(self, client, mock_extraction_task):
        """Test successful extraction start"""
        # Mock task response
        mock_task_instance = Mock()
        mock_task_instance.id = "test-task-123"
        mock_extraction_task.delay.return_value = mock_task_instance

        response = client.get('/api/extraction/start')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['task_id'] == "test-task-123"
        assert data['status'] == 'started'
        assert 'message' in data

        # Verify task was called correctly
        mock_extraction_task.delay.assert_called_once_with(None)

    def test_start_extraction_with_text_file(self, client, mock_extraction_task):
        """Test extraction start with custom text file"""
        mock_task_instance = Mock()
        mock_task_instance.id = "test-task-456"
        mock_extraction_task.delay.return_value = mock_task_instance

        response = client.get('/api/extraction/start?text_file=custom.txt')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['task_id'] == "test-task-456"

        # Verify task was called with custom text file
        mock_extraction_task.delay.assert_called_once_with('custom.txt')

    def test_start_extraction_failure(self, client, mock_extraction_task):
        """Test extraction start failure"""
        mock_extraction_task.delay.side_effect = Exception("Task queue unavailable")

        response = client.get('/api/extraction/start')

        assert response.status_code == 500
        data = json.loads(response.data)
        assert 'error' in data
        assert 'Service unavailable' in data['error']

    def test_get_task_status_success(self, client, mock_extraction_service):
        """Test successful task status retrieval"""
        # Mock task status
        mock_status = {
            'task_id': 'test-task-123',
            'status': 'running',
            'progress': 50,
            'message': 'Processing...'
        }
        mock_extraction_service.get_task_status.return_value = mock_status

        response = client.get('/api/extraction/status/test-task-123')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data == mock_status

        mock_extraction_service.get_task_status.assert_called_once_with('test-task-123')

    def test_get_task_status_not_found(self, client, mock_extraction_service):
        """Test task status when task not found"""
        mock_extraction_service.get_task_status.return_value = None

        response = client.get('/api/extraction/status/nonexistent-task')

        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['error'] == 'Task not found'

    def test_get_task_status_error(self, client, mock_extraction_service):
        """Test task status with service error"""
        mock_extraction_service.get_task_status.side_effect = Exception("Database error")

        response = client.get('/api/extraction/status/test-task-123')

        assert response.status_code == 500
        data = json.loads(response.data)
        assert 'error' in data
        assert 'Database error' in data['error']

    def test_list_tasks_success(self, client, mock_extraction_service):
        """Test successful task listing"""
        # Mock tasks
        start_time = datetime.now()
        mock_task1 = Mock(spec=ExtractionTask)
        mock_task1.status = 'running'
        mock_task1.progress = 30
        mock_task1.start_time = start_time

        mock_task2 = Mock(spec=ExtractionTask)
        mock_task2.status = 'completed'
        mock_task2.progress = 100
        mock_task2.start_time = start_time - timedelta(hours=1)

        mock_extraction_service.tasks = {
            'task-1': mock_task1,
            'task-2': mock_task2
        }

        response = client.get('/api/extraction/tasks')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['total'] == 2
        assert len(data['tasks']) == 2

        # Check task data structure
        task1_data = next(t for t in data['tasks'] if t['id'] == 'task-1')
        assert task1_data['status'] == 'running'
        assert task1_data['progress'] == 30
        assert task1_data['start_time'] == start_time.isoformat()

    def test_list_tasks_empty(self, client, mock_extraction_service):
        """Test task listing when no tasks exist"""
        mock_extraction_service.tasks = {}

        response = client.get('/api/extraction/tasks')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['total'] == 0
        assert data['tasks'] == []

    def test_list_tasks_with_none_start_time(self, client, mock_extraction_service):
        """Test task listing with task that has no start time"""
        mock_task = Mock(spec=ExtractionTask)
        mock_task.status = 'pending'
        mock_task.progress = 0
        mock_task.start_time = None

        mock_extraction_service.tasks = {'task-1': mock_task}

        response = client.get('/api/extraction/tasks')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['tasks'][0]['start_time'] is None

    def test_list_tasks_error(self, client, mock_extraction_service):
        """Test task listing with service error"""
        # Mock tasks.items() to raise an exception
        mock_extraction_service.tasks.items.side_effect = Exception("Service error")

        response = client.get('/api/extraction/tasks')

        assert response.status_code == 500
        assert response.content_type == 'application/json'
        data = json.loads(response.data)
        assert 'error' in data
        assert 'Service error' in data['error']

    def test_cancel_task_success(self, client, mock_extraction_service):
        """Test successful task cancellation"""
        # Mock task
        mock_task = Mock(spec=ExtractionTask)
        mock_task.status = 'running'
        mock_extraction_service.get_task.return_value = mock_task

        response = client.post('/api/extraction/cancel/test-task-123')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['message'] == 'Task cancelled successfully'
        assert data['task_id'] == 'test-task-123'

        # Verify task was cancelled
        assert mock_task.status == 'cancelled'
        assert mock_task.error == 'Task cancelled by user'

        mock_extraction_service.get_task.assert_called_once_with('test-task-123')

    def test_cancel_task_not_found(self, client, mock_extraction_service):
        """Test cancelling non-existent task"""
        mock_extraction_service.get_task.return_value = None

        response = client.post('/api/extraction/cancel/nonexistent-task')

        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['error'] == 'Task not found'

    def test_cancel_task_cannot_cancel(self, client, mock_extraction_service):
        """Test cancelling task that cannot be cancelled"""
        # Mock completed task
        mock_task = Mock(spec=ExtractionTask)
        mock_task.status = 'completed'
        mock_extraction_service.get_task.return_value = mock_task

        response = client.post('/api/extraction/cancel/test-task-123')

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['error'] == 'Task cannot be cancelled'

    def test_cancel_task_pending_status(self, client, mock_extraction_service):
        """Test cancelling task with pending status"""
        # Mock pending task
        mock_task = Mock(spec=ExtractionTask)
        mock_task.status = 'pending'
        mock_extraction_service.get_task.return_value = mock_task

        response = client.post('/api/extraction/cancel/test-task-123')

        assert response.status_code == 200
        assert mock_task.status == 'cancelled'

    def test_cancel_task_error(self, client, mock_extraction_service):
        """Test task cancellation with service error"""
        mock_extraction_service.get_task.side_effect = Exception("Service error")

        response = client.post('/api/extraction/cancel/test-task-123')

        assert response.status_code == 500
        data = json.loads(response.data)
        assert 'error' in data

    def test_cleanup_old_tasks_success(self, client, mock_extraction_service):
        """Test successful task cleanup"""
        response = client.post('/api/extraction/cleanup',
                              data=json.dumps({}),
                              content_type='application/json')

        assert response.status_code == 200
        assert response.content_type == 'application/json'
        data = json.loads(response.data)
        assert 'Cleaned up tasks older than 24 hours' in data['message']

        # Verify service was called with default max age
        mock_extraction_service.cleanup_old_tasks.assert_called_once_with(24)

    def test_cleanup_old_tasks_custom_age(self, client, mock_extraction_service):
        """Test task cleanup with custom max age"""
        response = client.post('/api/extraction/cleanup',
                              data=json.dumps({'max_age_hours': 48}),
                              content_type='application/json')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'Cleaned up tasks older than 48 hours' in data['message']

        # Verify service was called with custom max age
        mock_extraction_service.cleanup_old_tasks.assert_called_once_with(48)

    def test_cleanup_old_tasks_no_json(self, client, mock_extraction_service):
        """Test task cleanup without JSON body"""
        response = client.post('/api/extraction/cleanup',
                              data=json.dumps({}),
                              content_type='application/json')

        assert response.status_code == 200
        assert response.content_type == 'application/json'
        # Should use default max age when no JSON provided
        mock_extraction_service.cleanup_old_tasks.assert_called_once_with(24)

    def test_cleanup_old_tasks_error(self, client, mock_extraction_service):
        """Test task cleanup with service error"""
        mock_extraction_service.cleanup_old_tasks.side_effect = Exception("Cleanup failed")

        response = client.post('/api/extraction/cleanup',
                              data=json.dumps({}),
                              content_type='application/json')

        assert response.status_code == 500
        assert response.content_type == 'application/json'
        data = json.loads(response.data)
        assert 'error' in data
        assert 'Cleanup failed' in data['error']

    def test_endpoints_require_correct_methods(self, client):
        """Test that endpoints only accept correct HTTP methods"""
        # GET endpoints should not accept POST
        response = client.post('/api/extraction/start')
        assert response.status_code == 405  # Method not allowed

        response = client.post('/api/extraction/status/test')
        assert response.status_code == 405

        response = client.post('/api/extraction/tasks')
        assert response.status_code == 405

        # POST endpoints should not accept GET
        response = client.get('/api/extraction/cancel/test')
        assert response.status_code == 405

        response = client.get('/api/extraction/cleanup')
        assert response.status_code == 405

    def test_json_response_headers(self, client, mock_extraction_service):
        """Test that all endpoints return proper JSON headers"""
        mock_extraction_service.start_extraction.return_value = "test-task"

        response = client.get('/api/extraction/start')
        assert response.content_type == 'application/json'

        mock_extraction_service.get_task_status.return_value = {'status': 'running'}
        response = client.get('/api/extraction/status/test-task')
        assert response.content_type == 'application/json'

        mock_extraction_service.tasks = {}
        response = client.get('/api/extraction/tasks')
        assert response.content_type == 'application/json'
