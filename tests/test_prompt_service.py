"""
Tests for prompt management service
"""

import os
import sys
from unittest.mock import mock_open, patch

import pytest


# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app import Config, create_app
from web_app.database import db
from web_app.services.prompt_service import PromptService


class TestConfig(Config):
    """Test configuration"""
    def __init__(self):
        super().__init__()
        self.SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
        self.TESTING = True


@pytest.fixture
def app():
    """Create test Flask app"""
    app = create_app(TestConfig)
    return app


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


@pytest.fixture
def prompt_service(app):
    """Create prompt service with app context"""
    with app.app_context():
        yield PromptService()


class TestPromptService:
    """Test the prompt management service"""

    def test_service_creation(self, prompt_service):
        """Test that prompt service can be created"""
        assert prompt_service is not None

    def test_create_prompt(self, app, prompt_service):
        """Test creating a new prompt"""
        with app.app_context():
            prompt = prompt_service.create_prompt(
                name="Test Prompt",
                prompt_text="This is a test prompt with {text_chunk}",
                description="Test description"
            )

            assert prompt is not None
            assert prompt.name == "Test Prompt"
            assert prompt.prompt_text == "This is a test prompt with {text_chunk}"
            assert prompt.description == "Test description"
            assert prompt.is_active is False

    def test_get_all_prompts(self, app, prompt_service):
        """Test getting all prompts"""
        with app.app_context():
            # Count initial prompts (may include defaults)
            initial_count = len(prompt_service.get_all_prompts())

            # Create some test prompts
            prompt_service.create_prompt("Prompt 1", "Text 1", "Desc 1")
            prompt_service.create_prompt("Prompt 2", "Text 2", "Desc 2")

            prompts = prompt_service.get_all_prompts()

            assert len(prompts) == initial_count + 2
            prompt_names = [p.name for p in prompts]
            assert "Prompt 1" in prompt_names
            assert "Prompt 2" in prompt_names

    def test_set_active_prompt(self, app, prompt_service):
        """Test setting a prompt as active"""
        with app.app_context():
            prompt1 = prompt_service.create_prompt("Prompt 1", "Text 1", "Desc 1")
            prompt2 = prompt_service.create_prompt("Prompt 2", "Text 2", "Desc 2")

            # Set first prompt as active
            success = prompt_service.set_active_prompt(str(prompt1.id))
            assert success is True

            # Check that first prompt is active
            active_prompt = prompt_service.get_active_prompt()
            assert active_prompt.id == prompt1.id
            assert active_prompt.is_active is True

            # Set second prompt as active
            success = prompt_service.set_active_prompt(str(prompt2.id))
            assert success is True

            # Check that second prompt is now active and first is not
            active_prompt = prompt_service.get_active_prompt()
            assert active_prompt.id == prompt2.id

            # Refresh first prompt from database
            db.session.refresh(prompt1)
            assert prompt1.is_active is False

    def test_set_active_nonexistent_prompt(self, app, prompt_service):
        """Test setting a non-existent prompt as active"""
        with app.app_context():
            success = prompt_service.set_active_prompt("nonexistent-id")
            assert success is False

    def test_update_prompt(self, app, prompt_service):
        """Test updating an existing prompt"""
        with app.app_context():
            prompt = prompt_service.create_prompt("Original Name", "Original Text", "Original Desc")

            updated_prompt = prompt_service.update_prompt(
                str(prompt.id),
                name="Updated Name",
                prompt_text="Updated Text",
                description="Updated Desc"
            )

            assert updated_prompt is not None
            assert updated_prompt.name == "Updated Name"
            assert updated_prompt.prompt_text == "Updated Text"
            assert updated_prompt.description == "Updated Desc"

    def test_update_nonexistent_prompt(self, app, prompt_service):
        """Test updating a non-existent prompt"""
        with app.app_context():
            result = prompt_service.update_prompt("nonexistent-id", name="New Name")
            assert result is None

    def test_delete_prompt(self, app, prompt_service):
        """Test deleting a prompt"""
        with app.app_context():
            initial_count = len(prompt_service.get_all_prompts())

            prompt1 = prompt_service.create_prompt("Prompt 1", "Text 1", "Desc 1")
            prompt_service.create_prompt("Prompt 2", "Text 2", "Desc 2")

            # Should be able to delete non-active prompt
            success = prompt_service.delete_prompt(str(prompt1.id))
            assert success is True

            # Verify it's deleted
            prompts = prompt_service.get_all_prompts()
            assert len(prompts) == initial_count + 1
            prompt_names = [p.name for p in prompts]
            assert "Prompt 1" not in prompt_names
            assert "Prompt 2" in prompt_names

    def test_cannot_delete_active_prompt(self, app, prompt_service):
        """Test that active prompt cannot be deleted"""
        with app.app_context():
            initial_count = len(prompt_service.get_all_prompts())

            prompt1 = prompt_service.create_prompt("Prompt 1", "Text 1", "Desc 1")
            _ = prompt_service.create_prompt("Prompt 2", "Text 2", "Desc 2")

            # Set first prompt as active
            prompt_service.set_active_prompt(str(prompt1.id))

            # Should not be able to delete active prompt
            success = prompt_service.delete_prompt(str(prompt1.id))
            assert success is False

            # Verify it still exists
            prompts = prompt_service.get_all_prompts()
            assert len(prompts) == initial_count + 2

    def test_cannot_delete_only_prompt(self, app, prompt_service, clean_db):
        """Test that the only remaining prompt cannot be deleted"""
        with app.app_context():
            # Clear all prompts first to test the business logic
            clean_db()

            prompt = prompt_service.create_prompt("Only Prompt", "Text", "Desc")

            # Should not be able to delete the only prompt
            success = prompt_service.delete_prompt(str(prompt.id))
            assert success is False

            # Verify it still exists
            prompts = prompt_service.get_all_prompts()
            assert len(prompts) == 1

    def test_delete_nonexistent_prompt(self, app, prompt_service):
        """Test deleting a non-existent prompt"""
        with app.app_context():
            success = prompt_service.delete_prompt("nonexistent-id")
            assert success is False

    @patch('builtins.open', new_callable=mock_open, read_data="Test default prompt content with {text_chunk}")
    @patch('pathlib.Path.exists')
    def test_load_default_prompts(self, mock_exists, mock_file, app, prompt_service, clean_db):
        """Test loading default prompts from files - our specific business logic"""
        with app.app_context():
            # Clear existing prompts first to test the business logic
            clean_db()

            # Mock that the default prompts directory and file exist
            mock_exists.return_value = True

            # Load default prompts
            created_prompts = prompt_service.load_default_prompts()

            # Should have created one prompt
            assert len(created_prompts) == 1
            assert created_prompts[0].name == "Default Dutch Genealogy Extraction"
            assert created_prompts[0].prompt_text == "Test default prompt content with {text_chunk}"
            assert created_prompts[0].is_active is True  # First prompt should be set as active

            # Verify the prompt has the required placeholder for text injection
            assert "{text_chunk}" in created_prompts[0].prompt_text

    @patch('pathlib.Path.exists')
    def test_load_default_prompts_no_directory(self, mock_exists, app, prompt_service):
        """Test loading default prompts when directory doesn't exist"""
        with app.app_context():
            # Mock that the directory doesn't exist
            mock_exists.return_value = False

            # Load default prompts
            created_prompts = prompt_service.load_default_prompts()

            # Should not have created any prompts
            assert len(created_prompts) == 0

    @patch('builtins.open', new_callable=mock_open, read_data="Default content")
    @patch('pathlib.Path.exists')
    def test_load_default_prompts_already_exists(self, mock_exists, mock_file, app, prompt_service, clean_db):
        """Test loading default prompts when they already exist"""
        with app.app_context():
            # Clear existing prompts first
            clean_db()

            # Create a prompt with the same name as default
            _ = prompt_service.create_prompt(
                "Default Dutch Genealogy Extraction",
                "Existing content",
                "Existing description"
            )

            # Mock that the files exist
            mock_exists.return_value = True

            # Load default prompts
            created_prompts = prompt_service.load_default_prompts()

            # Should not have created any new prompts
            assert len(created_prompts) == 0

            # Existing prompt should be unchanged
            prompts = prompt_service.get_all_prompts()
            assert len(prompts) == 1
            assert prompts[0].prompt_text == "Existing content"

    @patch('builtins.open', new_callable=mock_open, read_data="Reset content")
    @patch('pathlib.Path.exists')
    def test_reset_to_default(self, mock_exists, mock_file, app, prompt_service, clean_db):
        """Test resetting a prompt to default content"""
        with app.app_context():
            # Clear existing prompts first
            clean_db()

            # Create a prompt
            _ = prompt_service.create_prompt(
                "Default Dutch Genealogy Extraction",
                "Modified content",
                "Modified description"
            )

            # Mock that the default file exists
            mock_exists.return_value = True

            # Reset to default
            reset_prompt = prompt_service.reset_to_default("Default Dutch Genealogy Extraction")

            assert reset_prompt is not None
            assert reset_prompt.prompt_text == "Reset content"
            assert reset_prompt.description == "Modified description"  # Description should be unchanged

    @patch('pathlib.Path.exists')
    def test_reset_to_default_no_file(self, mock_exists, app, prompt_service):
        """Test resetting when default file doesn't exist"""
        with app.app_context():
            # Create a prompt
            _ = prompt_service.create_prompt(
                "Default Dutch Genealogy Extraction",
                "Modified content",
                "Modified description"
            )

            # Mock that the default file doesn't exist
            mock_exists.return_value = False

            # Reset to default
            reset_prompt = prompt_service.reset_to_default("Default Dutch Genealogy Extraction")

            assert reset_prompt is None

    def test_reset_to_default_nonexistent_prompt(self, app, prompt_service):
        """Test resetting a non-existent prompt"""
        with app.app_context():
            reset_prompt = prompt_service.reset_to_default("Nonexistent Prompt")
            assert reset_prompt is None


class TestPromptAPI:
    """Test the prompt management API endpoints"""

    def test_get_prompts_api(self, app, client):
        """Test GET /api/prompts endpoint"""
        with app.app_context():
            # Create some test prompts
            from web_app.services.prompt_service import prompt_service
            initial_count = len(prompt_service.get_all_prompts())

            prompt1 = prompt_service.create_prompt("Prompt 1", "Text 1", "Desc 1")
            _ = prompt_service.create_prompt("Prompt 2", "Text 2", "Desc 2")
            prompt_service.set_active_prompt(str(prompt1.id))

            response = client.get('/api/prompts')
            assert response.status_code == 200

            data = response.get_json()
            assert data['success'] is True
            assert len(data['prompts']) == initial_count + 2
            assert data['active_prompt_id'] == str(prompt1.id)

    def test_get_prompt_api(self, app, client):
        """Test GET /api/prompts/<id> endpoint"""
        with app.app_context():
            from web_app.services.prompt_service import prompt_service
            prompt = prompt_service.create_prompt("Test Prompt", "Test Text", "Test Desc")

            response = client.get(f'/api/prompts/{prompt.id}')
            assert response.status_code == 200

            data = response.get_json()
            assert data['success'] is True
            assert data['prompt']['name'] == "Test Prompt"
            assert data['prompt']['prompt_text'] == "Test Text"

    def test_get_nonexistent_prompt_api(self, app, client):
        """Test GET /api/prompts/<id> for non-existent prompt"""
        response = client.get('/api/prompts/nonexistent-id')
        assert response.status_code == 404

    def test_create_prompt_api(self, app, client):
        """Test POST /api/prompts endpoint"""
        data = {
            'name': 'New Prompt',
            'prompt_text': 'New prompt text',
            'description': 'New description'
        }

        response = client.post('/api/prompts', json=data)
        assert response.status_code == 200

        response_data = response.get_json()
        assert response_data['success'] is True
        assert response_data['prompt']['name'] == 'New Prompt'

    def test_create_prompt_api_missing_data(self, app, client):
        """Test POST /api/prompts with missing data"""
        data = {'name': 'New Prompt'}  # Missing prompt_text

        response = client.post('/api/prompts', json=data)
        assert response.status_code == 400

    def test_update_prompt_api(self, app, client):
        """Test PUT /api/prompts/<id> endpoint"""
        with app.app_context():
            from web_app.services.prompt_service import prompt_service
            prompt = prompt_service.create_prompt("Original", "Original text", "Original desc")

            data = {
                'name': 'Updated Name',
                'prompt_text': 'Updated text'
            }

            response = client.put(f'/api/prompts/{prompt.id}', json=data)
            assert response.status_code == 200

            response_data = response.get_json()
            assert response_data['success'] is True
            assert response_data['prompt']['name'] == 'Updated Name'

    def test_activate_prompt_api(self, app, client):
        """Test POST /api/prompts/<id>/activate endpoint"""
        with app.app_context():
            from web_app.services.prompt_service import prompt_service
            prompt = prompt_service.create_prompt("Test Prompt", "Test text", "Test desc")

            response = client.post(f'/api/prompts/{prompt.id}/activate')
            assert response.status_code == 200

            response_data = response.get_json()
            assert response_data['success'] is True

    def test_delete_prompt_api(self, app, client):
        """Test DELETE /api/prompts/<id> endpoint"""
        with app.app_context():
            from web_app.services.prompt_service import prompt_service
            prompt1 = prompt_service.create_prompt("Prompt 1", "Text 1", "Desc 1")
            _ = prompt_service.create_prompt("Prompt 2", "Text 2", "Desc 2")

            # Should be able to delete non-active prompt
            response = client.delete(f'/api/prompts/{prompt1.id}')
            assert response.status_code == 200

            response_data = response.get_json()
            assert response_data['success'] is True
