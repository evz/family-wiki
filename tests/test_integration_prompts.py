"""
Integration tests for prompts workflow - Two-Layer Integration Testing Pattern

Layer 1: Service Integration Tests - Test real business logic with database operations
Layer 2: Blueprint HTTP Tests - Test HTTP concerns with mocked service

This follows the pattern established in OCR integration tests to avoid transaction
conflicts while providing comprehensive coverage of both architectural layers.
"""
import pytest
from unittest.mock import Mock, patch
from flask import url_for

from web_app.database.models import ExtractionPrompt
from web_app.repositories.rag_repository import RAGRepository
from web_app.services.prompt_service import PromptService
from web_app.services.exceptions import NotFoundError


class TestPromptsWorkflowIntegration:
    """Test complete prompts workflow using Two-Layer Integration Testing Pattern"""


    # =============================================================================
    # LAYER 1: SERVICE INTEGRATION TESTS (Real Business Logic + Database)
    # =============================================================================

    def test_prompt_service_create_extraction_prompt(self, app, db):
        """
        Test PromptService create prompt with real database operations
        
        This test would catch business logic issues like transaction problems,
        database constraint violations, or service-level validation errors.
        """
        
        with app.app_context():
            # Test the service directly with real database operations
            service = PromptService(db.session)
            
            # Execute real business logic
            result = service.create_prompt(
                name="Test Extraction Prompt",
                prompt_text="Extract genealogy data from: {text}",
                prompt_type="extraction",
                description="Test prompt for extraction"
            )
            
            # Verify service returned success
            assert result is not None
            assert result.name == "Test Extraction Prompt"
            assert result.prompt_text == "Extract genealogy data from: {text}"
            assert result.prompt_type == "extraction"
            assert result.description == "Test prompt for extraction"
            
            # Verify prompt was saved to database
            saved_prompts = ExtractionPrompt.query.filter_by(name="Test Extraction Prompt").all()
            assert len(saved_prompts) == 1
            assert saved_prompts[0].prompt_type == "extraction"

    def test_prompt_service_create_rag_prompt(self, app, db):
        """Test PromptService create RAG prompt with real database operations"""
        
        with app.app_context():
            service = PromptService(db.session)
            
            result = service.create_prompt(
                name="Test RAG Prompt", 
                prompt_text="Answer this question: {question} using context: {context}",
                prompt_type="rag",
                description="Test prompt for RAG queries"
            )
            
            # Verify service results
            assert result is not None
            assert result.prompt_type == "rag"
            
            # Verify database state
            rag_prompts = service.get_all_prompts(prompt_type="rag")
            assert len(rag_prompts) == 1
            assert rag_prompts[0].name == "Test RAG Prompt"

    def test_prompt_service_create_and_verify_database_state(self, app, db):
        """Test PromptService create with database verification - follows OCR pattern"""
        
        with app.app_context():
            # Create service and call method (no setup) - exactly like OCR test
            service = PromptService(db.session)
            
            # Create prompt
            result = service.create_prompt(
                name="Database Verification Test",
                prompt_text="Test prompt text for database verification",
                prompt_type="rag",
                description="Test description"
            )
            
            # Verify service results
            assert result is not None
            assert result.name == "Database Verification Test"
            assert result.prompt_type == "rag"
            assert result.description == "Test description"
            
            # Verify database state (like OCR test does)
            saved_prompts = ExtractionPrompt.query.filter_by(name="Database Verification Test").all()
            assert len(saved_prompts) == 1
            assert saved_prompts[0].prompt_type == "rag"
            assert saved_prompts[0].description == "Test description"

    def test_prompt_service_handles_nonexistent_prompt_updates(self, app, db):
        """Test service handles nonexistent prompt updates gracefully"""
        
        with app.app_context():
            service = PromptService(db.session)
            
            # Try to update nonexistent prompt
            result = service.update_prompt(
                prompt_id="550e8400-e29b-41d4-a716-446655440000",  # Valid UUID format
                name="Updated Name"
            )
            
            # Should return None for nonexistent prompts
            assert result is None

    def test_prompt_service_handles_invalid_uuid_format(self, app, db):
        """Test service handles invalid UUID format gracefully"""
        
        with app.app_context():
            service = PromptService(db.session)
            
            # Try operations with invalid UUID
            update_result = service.update_prompt("invalid-uuid", name="Test")
            assert update_result is None
            
            delete_result = service.delete_prompt("invalid-uuid")
            assert delete_result is False

    def test_prompt_service_create_only_like_ocr(self, app, db):
        """Test prompts service create with NO database setup, just like OCR pattern"""
        
        with app.app_context():
            # Just create service and call method (no setup) - exactly like OCR test
            service = PromptService(db.session)
            result = service.create_prompt(
                name="Test Create Only",
                prompt_text="Test text", 
                prompt_type="extraction"
            )
            
            # Verify service results
            assert result is not None
            assert result.name == "Test Create Only"
            
            # Verify database state
            prompts = ExtractionPrompt.query.filter_by(name="Test Create Only").all()
            assert len(prompts) == 1

    def test_prompt_service_real_update_functionality(self, app, db):
        """Test REAL PromptService update functionality with SAVEPOINT pattern"""
        
        with app.app_context():
            # Step 1: Create test data using direct database operations
            prompt = ExtractionPrompt(
                name="Original Name",
                prompt_text="Original text", 
                prompt_type="extraction",
                description="Original description"
            )
            db.session.add(prompt)
            db.session.commit()  # This commits to SAVEPOINT, auto-restarted
            
            # Step 2: Test REAL service update functionality  
            service = PromptService(db.session)
            updated = service.update_prompt(
                prompt_id=str(prompt.id),
                name="Updated Name",
                prompt_text="Updated text",
                description="Updated description" 
            )
            
            # Step 3: Verify service results
            assert updated is not None
            assert updated.name == "Updated Name"
            assert updated.prompt_text == "Updated text" 
            assert updated.description == "Updated description"
            assert updated.id == prompt.id  # Same record
            
            # Step 4: Verify database state
            from_db = ExtractionPrompt.query.get(prompt.id)
            assert from_db.name == "Updated Name"
            assert from_db.prompt_text == "Updated text"

    def test_prompt_service_real_delete_functionality(self, app, db):
        """Test REAL PromptService delete functionality with SAVEPOINT pattern"""
        
        with app.app_context():
            # Step 1: Create test data using direct database operations
            prompt = ExtractionPrompt(
                name="To Be Deleted",
                prompt_text="Will be deleted",
                prompt_type="rag"
            )
            db.session.add(prompt)
            db.session.commit()  # This commits to SAVEPOINT, auto-restarted
            
            # Step 2: Test REAL service delete functionality
            service = PromptService(db.session)
            success = service.delete_prompt(str(prompt.id))
            
            # Step 3: Verify service results
            assert success is True
            
            # Step 4: Verify database state - prompt should be gone
            deleted_prompt = ExtractionPrompt.query.get(prompt.id)
            assert deleted_prompt is None

    # =============================================================================
    # LAYER 2: BLUEPRINT HTTP TESTS (HTTP Concerns with Mocked Service)
    # =============================================================================

    def test_prompts_blueprint_create_prompt_http(self, client, db):
        """
        Test prompts blueprint create prompt HTTP handling with mocked service
        
        This tests HTTP concerns: form processing, flash messages, redirects
        while mocking the service layer to isolate HTTP-specific logic.
        """
        
        # Mock the service layer
        with patch('web_app.blueprints.prompts.PromptService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            # Mock successful service response
            mock_prompt = Mock()
            mock_prompt.id = "test-id"
            mock_prompt.name = "Test Prompt"
            mock_service.create_prompt.return_value = mock_prompt
            
            # Submit create prompt form
            response = client.post('/prompts/save', data={
                'name': 'Test Prompt',
                'description': 'Test Description', 
                'prompt_text': 'Test prompt text',
                'prompt_type': 'extraction'
            })
            
            # Verify HTTP response
            assert response.status_code == 302
            assert response.location == url_for('prompts.list_prompts')
            
            # Verify service was called correctly
            mock_service.create_prompt.assert_called_once_with(
                'Test Prompt',
                'Test prompt text', 
                'extraction',
                'Test Description'
            )

    def test_prompts_blueprint_update_prompt_http(self, client, db):
        """Test prompts blueprint update prompt HTTP handling with mocked service"""
        
        with patch('web_app.blueprints.prompts.PromptService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            # Mock successful update
            mock_prompt = Mock()
            mock_prompt.name = "Updated Prompt"
            mock_service.update_prompt.return_value = mock_prompt
            
            # Submit update form
            response = client.post('/prompts/save', data={
                'prompt_id': 'existing-id',
                'name': 'Updated Prompt',
                'description': 'Updated Description',
                'prompt_text': 'Updated prompt text',
                'prompt_type': 'rag'
            })
            
            # Verify HTTP response
            assert response.status_code == 302
            assert response.location == url_for('prompts.list_prompts')
            
            # Verify service was called correctly
            mock_service.update_prompt.assert_called_once_with(
                'existing-id',
                'Updated Prompt',
                'Updated prompt text',
                'Updated Description'
            )

    def test_prompts_blueprint_delete_prompt_http(self, client, db):
        """Test prompts blueprint delete prompt HTTP handling with mocked service"""
        
        with patch('web_app.blueprints.prompts.PromptService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            # Mock successful deletion
            mock_service.delete_prompt.return_value = True
            
            # Submit delete confirmation
            response = client.post('/prompts/confirm-delete/test-id')
            
            # Verify HTTP response
            assert response.status_code == 302
            assert response.location == url_for('prompts.list_prompts')
            
            # Verify service was called correctly
            mock_service.delete_prompt.assert_called_once_with('test-id')

    def test_prompts_blueprint_validation_empty_name(self, client, db):
        """Test prompts blueprint validates empty name with proper HTTP response"""
        
        # Submit form with empty name (no service mocking needed for validation)
        response = client.post('/prompts/save', data={
            'name': '',  # Empty name
            'prompt_text': 'Some text',
            'prompt_type': 'extraction'
        })
        
        # Should redirect back to create form
        assert response.status_code == 302
        assert response.location == url_for('prompts.create_prompt')

    def test_prompts_blueprint_validation_empty_prompt_text(self, client, db):
        """Test prompts blueprint validates empty prompt text with proper HTTP response"""
        
        # Submit form with empty prompt text
        response = client.post('/prompts/save', data={
            'name': 'Test Name',
            'prompt_text': '',  # Empty prompt text
            'prompt_type': 'extraction'
        })
        
        # Should redirect back to create form
        assert response.status_code == 302
        assert response.location == url_for('prompts.create_prompt')

    def test_prompts_blueprint_validation_invalid_type(self, client, db):
        """Test prompts blueprint validates invalid prompt type"""
        
        # Submit form with invalid prompt type
        response = client.post('/prompts/save', data={
            'name': 'Test Name',
            'prompt_text': 'Test text',
            'prompt_type': 'invalid_type'  # Invalid type
        })
        
        # Should redirect back to create form
        assert response.status_code == 302
        assert response.location == url_for('prompts.create_prompt')

    def test_prompts_blueprint_list_prompts_http(self, client, db):
        """Test prompts blueprint list prompts with mocked service"""
        
        with patch('web_app.blueprints.prompts.PromptService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            # Mock service responses
            mock_extraction_prompt = Mock()
            mock_extraction_prompt.name = "Extraction Prompt"
            mock_rag_prompt = Mock()
            mock_rag_prompt.name = "RAG Prompt"
            
            mock_service.get_all_prompts.side_effect = [
                [mock_extraction_prompt],  # extraction prompts
                [mock_rag_prompt]          # rag prompts
            ]
            
            # Request prompts list page
            response = client.get('/prompts/')
            
            # Verify HTTP response
            assert response.status_code == 200
            
            # Verify service was called correctly
            assert mock_service.get_all_prompts.call_count == 2
            calls = mock_service.get_all_prompts.call_args_list
            assert calls[0][1] == {'prompt_type': 'extraction'}
            assert calls[1][1] == {'prompt_type': 'rag'}

    def test_prompts_blueprint_edit_nonexistent_prompt(self, client, db):
        """Test prompts blueprint handles nonexistent prompt for edit"""
        
        with patch('web_app.blueprints.prompts.PromptService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            # Mock service returning None (prompt not found)
            mock_service.get_prompt_by_id.return_value = None
            
            # Request edit page for nonexistent prompt
            response = client.get('/prompts/edit/nonexistent-id')
            
            # Should redirect to list with error
            assert response.status_code == 302
            assert response.location == url_for('prompts.list_prompts')
            
            # Verify service was called
            mock_service.get_prompt_by_id.assert_called_once_with('nonexistent-id')