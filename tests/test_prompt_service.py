"""
Tests for prompt management service
"""

import os
import sys
from unittest.mock import mock_open, patch

import pytest


# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from web_app.database import db
from web_app.services.prompt_service import PromptService


# Use global fixtures from conftest.py instead of defining custom ones

@pytest.fixture
def prompt_service(db):
    """Create prompt service with database context"""
    return PromptService()


class TestPromptService:
    """Test the prompt management service"""

    def test_service_creation(self, prompt_service):
        """Test that prompt service can be created"""
        assert prompt_service is not None

    def test_create_prompt(self, prompt_service):
        """Test creating a new prompt"""
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

    def test_get_all_prompts(self, prompt_service):
        """Test getting all prompts"""
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

    def test_set_active_prompt(self, prompt_service):
        """Test setting a prompt as active"""
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

    def test_set_active_nonexistent_prompt(self, prompt_service):
        """Test setting a non-existent prompt as active"""
        success = prompt_service.set_active_prompt("nonexistent-id")
        assert success is False

    def test_update_prompt(self, prompt_service):
        """Test updating an existing prompt"""
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

    def test_update_nonexistent_prompt(self, prompt_service):
        """Test updating a non-existent prompt"""
        result = prompt_service.update_prompt("nonexistent-id", name="New Name")
        assert result is None

    def test_delete_prompt(self, prompt_service):
        """Test deleting a prompt"""
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

    def test_cannot_delete_active_prompt(self, prompt_service):
        """Test that active prompt cannot be deleted"""
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

    def test_cannot_delete_only_prompt(self, prompt_service, clean_db):
        """Test that the only remaining prompt cannot be deleted"""
        # Clear all prompts first to test the business logic
        clean_db()

        prompt = prompt_service.create_prompt("Only Prompt", "Text", "Desc")

        # Should not be able to delete the only prompt
        success = prompt_service.delete_prompt(str(prompt.id))
        assert success is False

        # Verify it still exists
        prompts = prompt_service.get_all_prompts()
        assert len(prompts) == 1

    def test_delete_nonexistent_prompt(self, prompt_service):
        """Test deleting a non-existent prompt"""
        success = prompt_service.delete_prompt("nonexistent-id")
        assert success is False

    @patch('builtins.open', new_callable=mock_open, read_data="Test default prompt content with {text_chunk}")
    @patch('pathlib.Path.exists')
    def test_load_default_prompts(self, mock_exists, mock_file, prompt_service, clean_db):
        """Test loading default prompts from files - our specific business logic"""
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
    def test_load_default_prompts_no_directory(self, mock_exists, prompt_service):
        """Test loading default prompts when directory doesn't exist"""
        # Mock that the directory doesn't exist
        mock_exists.return_value = False

        # Load default prompts
        created_prompts = prompt_service.load_default_prompts()

        # Should not have created any prompts
        assert len(created_prompts) == 0

    @patch('builtins.open', new_callable=mock_open, read_data="Default content")
    @patch('pathlib.Path.exists')
    def test_load_default_prompts_already_exists(self, mock_exists, mock_file, prompt_service, clean_db):
        """Test loading default prompts when they already exist"""
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
    def test_reset_to_default(self, mock_exists, mock_file, prompt_service, clean_db):
        """Test resetting a prompt to default content"""
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
    def test_reset_to_default_no_file(self, mock_exists, prompt_service):
        """Test resetting when default file doesn't exist"""
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

    def test_reset_to_default_nonexistent_prompt(self, prompt_service):
        """Test resetting a non-existent prompt"""
        reset_prompt = prompt_service.reset_to_default("Nonexistent Prompt")
        assert reset_prompt is None
