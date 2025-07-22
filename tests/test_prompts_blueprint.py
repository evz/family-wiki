"""
Tests for prompts blueprint - form handling and business logic
"""
import uuid
from unittest.mock import Mock, patch

import pytest

from web_app.database.models import ExtractionPrompt


class TestPromptsBlueprint:
    """Test prompts blueprint form handling and business logic"""

    @pytest.fixture
    def mock_prompt_service(self):
        """Mock PromptService for testing"""
        with patch('web_app.blueprints.prompts.PromptService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            yield mock_service

    @pytest.fixture
    def mock_prompt(self):
        """Mock prompt object"""
        prompt = Mock(spec=ExtractionPrompt)
        prompt.id = str(uuid.uuid4())
        prompt.name = "Test Prompt"
        prompt.prompt_text = "Test prompt text"
        prompt.description = "Test description"
        prompt.is_active = False
        return prompt

    def test_list_prompts_success(self, client, app, mock_prompt_service, mock_prompt):
        """Test successful prompts listing"""
        # Setup mocks
        mock_prompt_service.get_all_prompts.return_value = [mock_prompt]
        mock_prompt_service.get_active_prompt.return_value = mock_prompt

        # Make request
        response = client.get('/prompts/')

        # Verify response
        assert response.status_code == 200
        mock_prompt_service.get_all_prompts.assert_called_once()
        mock_prompt_service.get_active_prompt.assert_called_once()

    def test_list_prompts_no_active_prompt(self, client, app, mock_prompt_service, mock_prompt):
        """Test prompts listing with no active prompt"""
        # Setup mocks
        mock_prompt_service.get_all_prompts.return_value = [mock_prompt]
        mock_prompt_service.get_active_prompt.return_value = None

        # Make request
        response = client.get('/prompts/')

        # Verify response
        assert response.status_code == 200
        mock_prompt_service.get_all_prompts.assert_called_once()
        mock_prompt_service.get_active_prompt.assert_called_once()

    def test_create_prompt_form(self, client, app):
        """Test create prompt form display"""
        response = client.get('/prompts/create')
        assert response.status_code == 200

    def test_edit_prompt_success(self, client, app, mock_prompt_service, mock_prompt):
        """Test edit prompt form with valid prompt"""
        # Setup mock
        mock_prompt_service.get_prompt_by_id.return_value = mock_prompt

        # Make request
        response = client.get(f'/prompts/edit/{mock_prompt.id}')

        # Verify response
        assert response.status_code == 200
        mock_prompt_service.get_prompt_by_id.assert_called_once_with(mock_prompt.id)

    def test_edit_prompt_not_found(self, client, app, mock_prompt_service):
        """Test edit prompt with non-existent prompt"""
        # Setup mock
        mock_prompt_service.get_prompt_by_id.return_value = None

        # Make request
        prompt_id = str(uuid.uuid4())
        response = client.get(f'/prompts/edit/{prompt_id}')

        # Verify redirect
        assert response.status_code == 302
        assert response.location.endswith('/prompts/')
        mock_prompt_service.get_prompt_by_id.assert_called_once_with(prompt_id)

    def test_delete_prompt_success(self, client, app, mock_prompt_service, mock_prompt):
        """Test delete prompt form with valid prompt"""
        # Setup mock
        mock_prompt_service.get_prompt_by_id.return_value = mock_prompt

        # Make request
        response = client.get(f'/prompts/delete/{mock_prompt.id}')

        # Verify response
        assert response.status_code == 200
        mock_prompt_service.get_prompt_by_id.assert_called_once_with(mock_prompt.id)

    def test_delete_prompt_not_found(self, client, app, mock_prompt_service):
        """Test delete prompt with non-existent prompt"""
        # Setup mock
        mock_prompt_service.get_prompt_by_id.return_value = None

        # Make request
        prompt_id = str(uuid.uuid4())
        response = client.get(f'/prompts/delete/{prompt_id}')

        # Verify redirect
        assert response.status_code == 302
        assert response.location.endswith('/prompts/')
        mock_prompt_service.get_prompt_by_id.assert_called_once_with(prompt_id)

    def test_save_prompt_create_success(self, client, app, mock_prompt_service):
        """Test successful prompt creation"""
        # Setup mock
        mock_prompt_service.create_prompt.return_value = True

        # Make request
        response = client.post('/prompts/save', data={
            'name': 'New Prompt',
            'description': 'Test description',
            'prompt_text': 'Test prompt text'
        })

        # Verify response and service call
        assert response.status_code == 302
        assert response.location.endswith('/prompts/')
        mock_prompt_service.create_prompt.assert_called_once_with(
            'New Prompt', 'Test prompt text', 'Test description'
        )

    def test_save_prompt_update_success(self, client, app, mock_prompt_service):
        """Test successful prompt update"""
        # Setup mock
        prompt_id = str(uuid.uuid4())
        mock_prompt_service.update_prompt.return_value = True

        # Make request
        response = client.post('/prompts/save', data={
            'prompt_id': prompt_id,
            'name': 'Updated Prompt',
            'description': 'Updated description',
            'prompt_text': 'Updated prompt text'
        })

        # Verify response and service call
        assert response.status_code == 302
        assert response.location.endswith('/prompts/')
        mock_prompt_service.update_prompt.assert_called_once_with(
            prompt_id, 'Updated Prompt', 'Updated prompt text', 'Updated description'
        )

    def test_save_prompt_update_not_found(self, client, app, mock_prompt_service):
        """Test prompt update with non-existent prompt"""
        # Setup mock
        prompt_id = str(uuid.uuid4())
        mock_prompt_service.update_prompt.return_value = False

        # Make request
        response = client.post('/prompts/save', data={
            'prompt_id': prompt_id,
            'name': 'Updated Prompt',
            'description': 'Updated description',
            'prompt_text': 'Updated prompt text'
        })

        # Verify response
        assert response.status_code == 302
        assert response.location.endswith('/prompts/')
        mock_prompt_service.update_prompt.assert_called_once_with(
            prompt_id, 'Updated Prompt', 'Updated prompt text', 'Updated description'
        )

    def test_save_prompt_missing_name_create(self, client, app, mock_prompt_service):
        """Test prompt creation with missing name"""
        # Make request
        response = client.post('/prompts/save', data={
            'description': 'Test description',
            'prompt_text': 'Test prompt text'
        })

        # Verify redirect to create form
        assert response.status_code == 302
        assert response.location.endswith('/prompts/create')
        mock_prompt_service.create_prompt.assert_not_called()

    def test_save_prompt_missing_name_update(self, client, app, mock_prompt_service):
        """Test prompt update with missing name"""
        # Make request
        prompt_id = str(uuid.uuid4())
        response = client.post('/prompts/save', data={
            'prompt_id': prompt_id,
            'description': 'Test description',
            'prompt_text': 'Test prompt text'
        })

        # Verify redirect to edit form
        assert response.status_code == 302
        assert response.location.endswith(f'/prompts/edit/{prompt_id}')
        mock_prompt_service.update_prompt.assert_not_called()

    def test_save_prompt_missing_text_create(self, client, app, mock_prompt_service):
        """Test prompt creation with missing text"""
        # Make request
        response = client.post('/prompts/save', data={
            'name': 'Test Prompt',
            'description': 'Test description'
        })

        # Verify redirect to create form
        assert response.status_code == 302
        assert response.location.endswith('/prompts/create')
        mock_prompt_service.create_prompt.assert_not_called()

    def test_save_prompt_missing_text_update(self, client, app, mock_prompt_service):
        """Test prompt update with missing text"""
        # Make request
        prompt_id = str(uuid.uuid4())
        response = client.post('/prompts/save', data={
            'prompt_id': prompt_id,
            'name': 'Test Prompt',
            'description': 'Test description'
        })

        # Verify redirect to edit form
        assert response.status_code == 302
        assert response.location.endswith(f'/prompts/edit/{prompt_id}')
        mock_prompt_service.update_prompt.assert_not_called()

    def test_save_prompt_empty_name_create(self, client, app, mock_prompt_service):
        """Test prompt creation with empty name"""
        # Make request
        response = client.post('/prompts/save', data={
            'name': '   ',  # Whitespace only
            'description': 'Test description',
            'prompt_text': 'Test prompt text'
        })

        # Verify redirect to create form
        assert response.status_code == 302
        assert response.location.endswith('/prompts/create')
        mock_prompt_service.create_prompt.assert_not_called()

    def test_save_prompt_empty_text_create(self, client, app, mock_prompt_service):
        """Test prompt creation with empty text"""
        # Make request
        response = client.post('/prompts/save', data={
            'name': 'Test Prompt',
            'description': 'Test description',
            'prompt_text': '   '  # Whitespace only
        })

        # Verify redirect to create form
        assert response.status_code == 302
        assert response.location.endswith('/prompts/create')
        mock_prompt_service.create_prompt.assert_not_called()

    def test_activate_prompt_success(self, client, app, mock_prompt_service):
        """Test successful prompt activation"""
        # Setup mock
        prompt_id = str(uuid.uuid4())
        mock_prompt_service.set_active_prompt.return_value = True

        # Make request
        response = client.post(f'/prompts/activate/{prompt_id}')

        # Verify response and service call
        assert response.status_code == 302
        assert response.location.endswith('/prompts/')
        mock_prompt_service.set_active_prompt.assert_called_once_with(prompt_id)

    def test_activate_prompt_failure(self, client, app, mock_prompt_service):
        """Test prompt activation failure"""
        # Setup mock
        prompt_id = str(uuid.uuid4())
        mock_prompt_service.set_active_prompt.return_value = False

        # Make request
        response = client.post(f'/prompts/activate/{prompt_id}')

        # Verify response and service call
        assert response.status_code == 302
        assert response.location.endswith('/prompts/')
        mock_prompt_service.set_active_prompt.assert_called_once_with(prompt_id)

    def test_confirm_delete_prompt_success(self, client, app, mock_prompt_service):
        """Test successful prompt deletion"""
        # Setup mock
        prompt_id = str(uuid.uuid4())
        mock_prompt_service.delete_prompt.return_value = True

        # Make request
        response = client.post(f'/prompts/confirm-delete/{prompt_id}')

        # Verify response and service call
        assert response.status_code == 302
        assert response.location.endswith('/prompts/')
        mock_prompt_service.delete_prompt.assert_called_once_with(prompt_id)

    def test_confirm_delete_prompt_failure(self, client, app, mock_prompt_service):
        """Test prompt deletion failure"""
        # Setup mock
        prompt_id = str(uuid.uuid4())
        mock_prompt_service.delete_prompt.return_value = False

        # Make request
        response = client.post(f'/prompts/confirm-delete/{prompt_id}')

        # Verify response and service call
        assert response.status_code == 302
        assert response.location.endswith('/prompts/')
        mock_prompt_service.delete_prompt.assert_called_once_with(prompt_id)

    def test_save_prompt_whitespace_trimming(self, client, app, mock_prompt_service):
        """Test that form data is properly trimmed"""
        # Setup mock
        mock_prompt_service.create_prompt.return_value = True

        # Make request with whitespace
        response = client.post('/prompts/save', data={
            'name': '  Test Prompt  ',
            'description': '  Test description  ',
            'prompt_text': '  Test prompt text  '
        })

        # Verify trimmed values passed to service
        assert response.status_code == 302
        mock_prompt_service.create_prompt.assert_called_once_with(
            'Test Prompt', 'Test prompt text', 'Test description'
        )

    def test_save_prompt_optional_description(self, client, app, mock_prompt_service):
        """Test prompt creation with missing description (should be allowed)"""
        # Setup mock
        mock_prompt_service.create_prompt.return_value = True

        # Make request without description
        response = client.post('/prompts/save', data={
            'name': 'Test Prompt',
            'prompt_text': 'Test prompt text'
        })

        # Verify service called with empty description
        assert response.status_code == 302
        mock_prompt_service.create_prompt.assert_called_once_with(
            'Test Prompt', 'Test prompt text', ''
        )

    def test_save_prompt_get_method_not_allowed(self, client, app):
        """Test that GET requests to save endpoint are not allowed"""
        response = client.get('/prompts/save')
        assert response.status_code == 405  # Method Not Allowed

    def test_activate_prompt_get_method_not_allowed(self, client, app):
        """Test that GET requests to activate endpoint are not allowed"""
        prompt_id = str(uuid.uuid4())
        response = client.get(f'/prompts/activate/{prompt_id}')
        assert response.status_code == 405  # Method Not Allowed

    def test_confirm_delete_get_method_not_allowed(self, client, app):
        """Test that GET requests to confirm-delete endpoint are not allowed"""
        prompt_id = str(uuid.uuid4())
        response = client.get(f'/prompts/confirm-delete/{prompt_id}')
        assert response.status_code == 405  # Method Not Allowed
