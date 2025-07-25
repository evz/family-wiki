"""
Tests for research blueprint
"""
import uuid
from unittest.mock import Mock, patch

from web_app.blueprints.research import research_bp


class TestResearchBlueprint:
    """Test research blueprint functionality"""

    def test_blueprint_registration(self, app):
        """Test that research blueprint is properly registered"""
        assert 'research' in app.blueprints
        assert app.blueprints['research'] == research_bp

    def test_start_research_no_file(self, client, app):
        """Test starting research job without uploaded file"""
        with patch('web_app.blueprints.research.safe_task_submit') as mock_submit:
            mock_task = Mock()
            mock_task.id = "test-task-123"
            mock_submit.return_value = mock_task

            response = client.post('/research/start', data={})

            assert response.status_code == 302  # Redirect
            mock_submit.assert_called_once()

    def test_start_research_with_file(self, client, app):
        """Test starting research job with uploaded file"""
        with patch('web_app.blueprints.research.safe_task_submit') as mock_submit, \
             patch('web_app.blueprints.research.safe_file_operation') as mock_file_op:

            mock_task = Mock()
            mock_task.id = "test-task-456"
            mock_submit.return_value = mock_task
            mock_file_op.return_value = "file_id_123"

            data = {
                'input_file': (open(__file__, 'rb'), 'test_input.json')
            }
            response = client.post('/research/start', data=data)

            assert response.status_code == 302  # Redirect
            mock_submit.assert_called_once()
            mock_file_op.assert_called_once()

    def test_start_research_file_save_failure(self, client, app):
        """Test research job when file save fails"""
        with patch('web_app.blueprints.research.safe_file_operation') as mock_file_op:
            mock_file_op.return_value = None  # Simulate file save failure

            data = {
                'input_file': (open(__file__, 'rb'), 'test_input.json')
            }
            response = client.post('/research/start', data=data)

            assert response.status_code == 302  # Redirect back
            mock_file_op.assert_called_once()

    def test_view_research_questions_pending(self, client, app):
        """Test viewing research questions for pending task"""
        task_id = str(uuid.uuid4())

        with patch('web_app.blueprints.research.get_task_status_safely') as mock_status:
            mock_status.return_value = {'status': 'pending'}

            response = client.get(f'/research/questions/{task_id}')

            assert response.status_code == 302  # Redirect

    def test_view_research_questions_failed(self, client, app):
        """Test viewing research questions for failed task"""
        task_id = str(uuid.uuid4())

        with patch('web_app.blueprints.research.get_task_status_safely') as mock_status:
            mock_status.return_value = {
                'status': 'failed',
                'error': 'Task failed'
            }

            response = client.get(f'/research/questions/{task_id}')

            assert response.status_code == 302  # Redirect

    def test_view_research_questions_running(self, client, app):
        """Test viewing research questions for running task"""
        task_id = str(uuid.uuid4())

        with patch('web_app.blueprints.research.get_task_status_safely') as mock_status:
            mock_status.return_value = {'status': 'running'}

            response = client.get(f'/research/questions/{task_id}')

            assert response.status_code == 302  # Redirect

    def test_view_research_questions_completed_no_result(self, client, app):
        """Test viewing research questions when task completed but no result"""
        task_id = str(uuid.uuid4())

        with patch('web_app.blueprints.research.get_task_status_safely') as mock_status:
            mock_status.return_value = {
                'status': 'completed',
                'result': None
            }

            response = client.get(f'/research/questions/{task_id}')

            assert response.status_code == 302  # Redirect

    def test_view_research_questions_completed_unsuccessful(self, client, app):
        """Test viewing research questions when task completed unsuccessfully"""
        task_id = str(uuid.uuid4())

        with patch('web_app.blueprints.research.get_task_status_safely') as mock_status:
            mock_status.return_value = {
                'status': 'completed',
                'result': {'success': False}
            }

            response = client.get(f'/research/questions/{task_id}')

            assert response.status_code == 302  # Redirect

    def test_view_research_questions_success(self, client, app):
        """Test viewing research questions for successful task"""
        task_id = str(uuid.uuid4())

        with patch('web_app.blueprints.research.get_task_status_safely') as mock_status:
            mock_status.return_value = {
                'status': 'completed',
                'result': {
                    'success': True,
                    'questions': [
                        {'question': 'What is the birth date of John Doe?', 'priority': 'high'},
                        {'question': 'Where was Mary Smith born?', 'priority': 'medium'}
                    ],
                    'input_file': 'test_input.json',
                    'total_questions': 2
                }
            }

            response = client.get(f'/research/questions/{task_id}')

            assert response.status_code == 200
            assert b'What is the birth date of John Doe?' in response.data
            assert b'Where was Mary Smith born?' in response.data
            assert b'test_input.json' in response.data

    def test_view_research_questions_with_task_mock(self, client, app):
        """Test view research questions with AsyncResult mock"""
        task_id = str(uuid.uuid4())

        with patch('web_app.blueprints.research.generate_research_questions.AsyncResult') as mock_async_result, \
             patch('web_app.blueprints.research.get_task_status_safely') as mock_status:

            mock_task = Mock()
            mock_async_result.return_value = mock_task

            mock_status.return_value = {
                'status': 'completed',
                'result': {
                    'success': True,
                    'questions': ['Question 1', 'Question 2'],
                    'input_file': 'input.json',
                    'total_questions': 2
                }
            }

            response = client.get(f'/research/questions/{task_id}')

            assert response.status_code == 200
            mock_async_result.assert_called_once_with(task_id)
            mock_status.assert_called_once_with(mock_task, task_id)
