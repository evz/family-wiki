"""
Tests for domain-specific API blueprints
"""

from unittest.mock import MagicMock, patch

import pytest

from app import create_app
from web_app.shared.api_response_formatter import APIResponseFormatter


class TestConfig:
    """Test configuration"""
    SECRET_KEY = 'test-secret-key'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    TESTING = True
    OLLAMA_HOST = 'localhost'
    OLLAMA_PORT = 11434
    OLLAMA_MODEL = 'test-model'

    @property
    def ollama_base_url(self):
        """Construct full Ollama URL"""
        return f"http://{self.OLLAMA_HOST}:{self.OLLAMA_PORT}"


@pytest.fixture
def app():
    """Create test Flask application"""
    app = create_app(TestConfig)
    return app


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


class TestSystemAPIBlueprint:
    """Test system status and tool execution API"""

    def test_status_endpoint(self, client):
        """Test system status endpoint"""
        with patch('web_app.services.system_service.system_service.check_system_status') as mock_status:
            mock_status.return_value = {'status': 'healthy', 'components': {}}

            response = client.get('/api/status')

            assert response.status_code == 200
            data = response.get_json()
            assert 'status' in data
            mock_status.assert_called_once()

    def test_refresh_status_endpoint(self, client):
        """Test refresh status endpoint"""
        with patch('web_app.services.system_service.system_service.check_system_status') as mock_status:
            mock_status.return_value = {'status': 'healthy', 'components': {}}

            response = client.get('/api/status/refresh')

            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            assert 'status' in data
            mock_status.assert_called_once()

    @pytest.mark.parametrize("invalid_tool", ["invalid_tool", "nonexistent", "bad_tool"])
    def test_invalid_tool_execution(self, client, invalid_tool):
        """Test running invalid tool returns error"""
        response = client.get(f'/api/run/{invalid_tool}')

        assert response.status_code == 400
        data = response.get_json()
        assert data['error'] == f'Invalid tool: {invalid_tool}'

    @pytest.mark.parametrize("tool,processor_class,execute_patch", [
        ('ocr', 'web_app.pdf_processing.ocr_processor.PDFOCRProcessor', 'web_app.blueprints.api_system.execute_with_progress'),
        ('benchmark', 'web_app.pdf_processing.genealogy_model_benchmark.GenealogyModelBenchmark', 'web_app.blueprints.api_system.execute_with_progress'),
    ])
    def test_tool_execution_success(self, client, tool, processor_class, execute_patch):
        """Test successful tool execution"""
        with patch(processor_class) as mock_processor_class:
            mock_processor = MagicMock()
            mock_processor_class.return_value = mock_processor

            with patch(execute_patch) as mock_execute:
                mock_execute.return_value = {
                    'success': True,
                    'message': f'{tool} completed successfully',
                    'results': {'items_processed': 5}
                }

                response = client.get(f'/api/run/{tool}')

                assert response.status_code == 200
                data = response.get_json()
                assert data['success'] is True
                assert f'{tool} completed successfully' in data['stdout']
                assert data['return_code'] == 0

    @pytest.mark.parametrize("tool,processor_class,execute_patch", [
        ('ocr', 'web_app.pdf_processing.ocr_processor.PDFOCRProcessor', 'web_app.blueprints.api_system.execute_with_progress'),
        ('benchmark', 'web_app.pdf_processing.genealogy_model_benchmark.GenealogyModelBenchmark', 'web_app.blueprints.api_system.execute_with_progress'),
    ])
    def test_tool_execution_failure(self, client, tool, processor_class, execute_patch):
        """Test failed tool execution"""
        with patch(processor_class) as mock_processor_class:
            mock_processor = MagicMock()
            mock_processor_class.return_value = mock_processor

            with patch(execute_patch) as mock_execute:
                mock_execute.return_value = {
                    'success': False,
                    'error': f'{tool} failed to execute'
                }

                response = client.get(f'/api/run/{tool}')

                assert response.status_code == 200  # The endpoint returns 200 even for failed tools
                data = response.get_json()
                assert data['success'] is False
                assert f'{tool} failed to execute' in data['stderr']
                assert data['return_code'] == 1

    def test_extract_tool_execution(self, client):
        """Test extract tool execution (special case)"""
        with patch('web_app.services.extraction_service.extraction_service.start_extraction') as mock_start:
            mock_start.return_value = 'task-123'

            response = client.get('/api/run/extract')

            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            assert data['task_id'] == 'task-123'
            assert 'redirect' in data

    def test_gedcom_tool_execution(self, client):
        """Test gedcom tool execution"""
        with patch('web_app.services.gedcom_service.gedcom_service.generate_gedcom') as mock_gedcom:
            mock_gedcom.return_value = {
                'success': True,
                'message': 'GEDCOM generated successfully',
                'results': {'file_path': 'test.ged'}
            }

            response = client.get('/api/run/gedcom')

            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            assert 'GEDCOM generated successfully' in data['stdout']
            assert data['return_code'] == 0

    def test_research_tool_execution(self, client):
        """Test research tool execution"""
        with patch('web_app.research_question_generator.ResearchQuestionGenerator') as mock_generator_class:
            mock_generator = MagicMock()
            mock_generator.generate_questions.return_value = ['Question 1', 'Question 2']
            mock_generator_class.return_value = mock_generator

            with patch('web_app.blueprints.api_system.execute_with_progress') as mock_execute:
                mock_execute.return_value = {
                    'success': True,
                    'message': 'Research questions generated',
                    'results': {'questions': ['Question 1', 'Question 2']}
                }

                response = client.get('/api/run/research')

                assert response.status_code == 200
                data = response.get_json()
                assert data['success'] is True
                assert 'Research questions generated' in data['stdout']
                assert data['return_code'] == 0

    def test_tool_execution_exception(self, client):
        """Test tool execution with exception"""
        # Mock the actual import path as it appears in the blueprint
        with patch('web_app.blueprints.api_system.PDFOCRProcessor', side_effect=Exception("Processor error")):
            response = client.get('/api/run/ocr')

            assert response.status_code == 500
            data = response.get_json()
            assert data['success'] is False
            assert 'Processor error' in data['error']
            assert data['return_code'] == 1


class TestPromptsAPIBlueprint:
    """Test prompt management API"""

    def test_get_prompts_empty(self, client):
        """Test getting prompts when none exist"""
        with patch('web_app.services.prompt_service.prompt_service.get_all_prompts', return_value=[]):
            with patch('web_app.services.prompt_service.prompt_service.get_active_prompt', return_value=None):
                response = client.get('/api/prompts')

                assert response.status_code == 200
                data = response.get_json()
                assert data['success'] is True
                assert data['prompts'] == []
                assert data['active_prompt_id'] is None

    def test_get_prompts_error(self, client):
        """Test getting prompts with service error"""
        with patch('web_app.services.prompt_service.prompt_service.get_all_prompts', side_effect=Exception("Service error")):
            response = client.get('/api/prompts')

            assert response.status_code == 500
            data = response.get_json()
            assert data['success'] is False
            assert 'Service error' in data['error']

    def test_get_prompt_success(self, client):
        """Test getting a specific prompt successfully"""
        mock_prompt = MagicMock()
        mock_prompt.id = 'test-prompt-id'
        mock_prompt.name = 'Test Prompt'
        mock_prompt.description = 'Test Description'
        mock_prompt.prompt_text = 'Test prompt text'
        mock_prompt.is_active = False
        mock_prompt.created_at.isoformat.return_value = '2023-01-01T00:00:00'
        mock_prompt.updated_at.isoformat.return_value = '2023-01-01T00:00:00'

        with patch('web_app.services.prompt_service.prompt_service.get_all_prompts', return_value=[mock_prompt]):
            response = client.get('/api/prompts/test-prompt-id')

            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            assert data['prompt']['name'] == 'Test Prompt'
            assert data['prompt']['prompt_text'] == 'Test prompt text'

    def test_get_prompt_error(self, client):
        """Test getting a prompt with service error"""
        with patch('web_app.services.prompt_service.prompt_service.get_all_prompts', side_effect=Exception("Service error")):
            response = client.get('/api/prompts/test-id')

            assert response.status_code == 500
            data = response.get_json()
            assert data['success'] is False
            assert 'Service error' in data['error']

    @pytest.mark.parametrize("request_data,expected_error", [
        ({}, 'No data provided'),
        ({'name': 'Test'}, 'Name and prompt text are required'),
        ({'prompt_text': 'Text'}, 'Name and prompt text are required'),
        ({'name': '', 'prompt_text': 'Text'}, 'Name and prompt text are required'),
        ({'name': 'Test', 'prompt_text': ''}, 'Name and prompt text are required'),
    ])
    def test_create_prompt_validation_errors(self, client, request_data, expected_error):
        """Test prompt creation validation"""
        response = client.post('/api/prompts', json=request_data)

        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
        assert expected_error in data['error']

    def test_create_prompt_success(self, client):
        """Test successful prompt creation"""
        mock_prompt = MagicMock()
        mock_prompt.id = 'test-prompt-id'
        mock_prompt.name = 'Test Prompt'
        mock_prompt.description = 'Test Description'
        mock_prompt.is_active = False

        with patch('web_app.services.prompt_service.prompt_service.create_prompt', return_value=mock_prompt):
            response = client.post('/api/prompts', json={
                'name': 'Test Prompt',
                'prompt_text': 'Test prompt text',
                'description': 'Test Description'
            })

            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            assert data['prompt']['name'] == 'Test Prompt'

    def test_create_prompt_error(self, client):
        """Test prompt creation with service error"""
        with patch('web_app.services.prompt_service.prompt_service.create_prompt', side_effect=Exception("Service error")):
            response = client.post('/api/prompts', json={
                'name': 'Test Prompt',
                'prompt_text': 'Test prompt text'
            })

            assert response.status_code == 500
            data = response.get_json()
            assert data['success'] is False
            assert 'Service error' in data['error']

    def test_update_prompt_no_data(self, client):
        """Test updating prompt with no data"""
        response = client.put('/api/prompts/test-id', json={})

        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
        assert 'No data provided' in data['error']

    def test_update_prompt_success(self, client):
        """Test successful prompt update"""
        mock_prompt = MagicMock()
        mock_prompt.id = 'test-prompt-id'
        mock_prompt.name = 'Updated Prompt'
        mock_prompt.description = 'Updated Description'
        mock_prompt.is_active = True

        with patch('web_app.services.prompt_service.prompt_service.update_prompt', return_value=mock_prompt):
            response = client.put('/api/prompts/test-id', json={
                'name': 'Updated Prompt',
                'description': 'Updated Description'
            })

            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            assert data['prompt']['name'] == 'Updated Prompt'

    def test_update_prompt_not_found(self, client):
        """Test updating non-existent prompt"""
        with patch('web_app.services.prompt_service.prompt_service.update_prompt', return_value=None):
            response = client.put('/api/prompts/nonexistent-id', json={
                'name': 'Updated Prompt'
            })

            assert response.status_code == 404
            data = response.get_json()
            assert data['success'] is False
            assert 'Prompt not found' in data['error']

    def test_update_prompt_error(self, client):
        """Test prompt update with service error"""
        with patch('web_app.services.prompt_service.prompt_service.update_prompt', side_effect=Exception("Service error")):
            response = client.put('/api/prompts/test-id', json={
                'name': 'Updated Prompt'
            })

            assert response.status_code == 500
            data = response.get_json()
            assert data['success'] is False
            assert 'Service error' in data['error']

    def test_activate_prompt_success(self, client):
        """Test successful prompt activation"""
        with patch('web_app.services.prompt_service.prompt_service.set_active_prompt', return_value=True):
            response = client.post('/api/prompts/test-id/activate')

            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            assert 'activated successfully' in data['message']

    def test_activate_prompt_not_found(self, client):
        """Test activating non-existent prompt"""
        with patch('web_app.services.prompt_service.prompt_service.set_active_prompt', return_value=False):
            response = client.post('/api/prompts/nonexistent-id/activate')

            assert response.status_code == 404
            data = response.get_json()
            assert data['success'] is False
            assert 'Prompt not found' in data['error']

    def test_activate_prompt_error(self, client):
        """Test prompt activation with service error"""
        with patch('web_app.services.prompt_service.prompt_service.set_active_prompt', side_effect=Exception("Service error")):
            response = client.post('/api/prompts/test-id/activate')

            assert response.status_code == 500
            data = response.get_json()
            assert data['success'] is False
            assert 'Service error' in data['error']

    def test_delete_prompt_success(self, client):
        """Test successful prompt deletion"""
        with patch('web_app.services.prompt_service.prompt_service.delete_prompt', return_value=True):
            response = client.delete('/api/prompts/test-id')

            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            assert 'deleted successfully' in data['message']

    def test_delete_prompt_cannot_delete(self, client):
        """Test deleting prompt that cannot be deleted"""
        with patch('web_app.services.prompt_service.prompt_service.delete_prompt', return_value=False):
            response = client.delete('/api/prompts/test-id')

            assert response.status_code == 400
            data = response.get_json()
            assert data['success'] is False
            assert 'Cannot delete prompt' in data['error']

    def test_delete_prompt_error(self, client):
        """Test prompt deletion with service error"""
        with patch('web_app.services.prompt_service.prompt_service.delete_prompt', side_effect=Exception("Service error")):
            response = client.delete('/api/prompts/test-id')

            assert response.status_code == 500
            data = response.get_json()
            assert data['success'] is False
            assert 'Service error' in data['error']

    def test_reset_prompt_success(self, client):
        """Test successful prompt reset"""
        mock_prompt = MagicMock()
        mock_prompt.id = 'test-id'  # Make sure ID matches the URL parameter
        mock_prompt.name = 'Test Prompt'
        mock_updated = MagicMock()

        with patch('web_app.services.prompt_service.prompt_service.get_all_prompts', return_value=[mock_prompt]):
            with patch('web_app.services.prompt_service.prompt_service.reset_to_default', return_value=mock_updated):
                response = client.post('/api/prompts/test-id/reset')

                assert response.status_code == 200
                data = response.get_json()
                assert data['success'] is True
                assert 'reset to default successfully' in data['message']

    def test_reset_prompt_not_found(self, client):
        """Test resetting non-existent prompt"""
        with patch('web_app.services.prompt_service.prompt_service.get_all_prompts', return_value=[]):
            response = client.post('/api/prompts/nonexistent-id/reset')

            assert response.status_code == 404
            data = response.get_json()
            assert data['success'] is False
            assert 'Prompt not found' in data['error']

    def test_reset_prompt_no_default(self, client):
        """Test resetting prompt with no default available"""
        mock_prompt = MagicMock()
        mock_prompt.id = 'test-id'  # Make sure ID matches the URL parameter
        mock_prompt.name = 'Test Prompt'

        with patch('web_app.services.prompt_service.prompt_service.get_all_prompts', return_value=[mock_prompt]):
            with patch('web_app.services.prompt_service.prompt_service.reset_to_default', return_value=None):
                response = client.post('/api/prompts/test-id/reset')

                assert response.status_code == 400
                data = response.get_json()
                assert data['success'] is False
                assert 'no default available' in data['error']

    def test_reset_prompt_error(self, client):
        """Test prompt reset with service error"""
        with patch('web_app.services.prompt_service.prompt_service.get_all_prompts', side_effect=Exception("Service error")):
            response = client.post('/api/prompts/test-id/reset')

            assert response.status_code == 500
            data = response.get_json()
            assert data['success'] is False
            assert 'Service error' in data['error']

    def test_get_nonexistent_prompt(self, client):
        """Test getting a prompt that doesn't exist"""
        with patch('web_app.services.prompt_service.prompt_service.get_all_prompts', return_value=[]):
            response = client.get('/api/prompts/nonexistent-id')

            assert response.status_code == 404
            data = response.get_json()
            assert data['success'] is False
            assert data['error'] == 'Prompt not found'


class TestDatabaseAPIBlueprint:
    """Test database management API"""

    def test_get_database_stats(self, client):
        """Test getting database statistics"""
        mock_stats = {
            'total_people': 150,
            'total_families': 75,
            'total_events': 200
        }

        with patch('web_app.services.extraction_service.extraction_service.get_database_stats', return_value=mock_stats):
            response = client.get('/api/database/stats')

            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            assert data['stats']['total_people'] == 150

    def test_get_database_stats_error(self, client):
        """Test database stats with error"""
        with patch('web_app.services.extraction_service.extraction_service.get_database_stats', side_effect=Exception("Database error")):
            response = client.get('/api/database/stats')

            assert response.status_code == 500
            data = response.get_json()
            assert data['success'] is False
            assert 'Database error' in data['error']

    def test_clear_database_success(self, client):
        """Test successful database clearing"""
        with patch('web_app.database.models.Family') as mock_family, \
             patch('web_app.database.models.Marriage') as mock_marriage, \
             patch('web_app.database.models.Event') as mock_event, \
             patch('web_app.database.models.Person') as mock_person, \
             patch('web_app.database.db.session.commit') as mock_commit:

            # Mock query.delete() methods
            mock_family.query.delete.return_value = None
            mock_marriage.query.delete.return_value = None
            mock_event.query.delete.return_value = None
            mock_person.query.delete.return_value = None

            response = client.post('/api/database/clear')

            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            assert 'Database cleared successfully' in data['message']
            mock_commit.assert_called_once()

    def test_clear_database_error(self, client):
        """Test database clear with error"""
        with patch('web_app.database.models.Family') as mock_family, \
             patch('web_app.database.db.session.commit', side_effect=Exception("Database error")):

            mock_family.query.delete.return_value = None

            response = client.post('/api/database/clear')

            assert response.status_code == 500
            data = response.get_json()
            assert data['success'] is False
            assert 'Database error' in data['error']


class TestRAGAPIBlueprint:
    """Test RAG management API"""

    def test_get_corpora_empty(self, client):
        """Test getting corpora when none exist"""
        with patch('web_app.services.rag_service.rag_service.get_all_corpora', return_value=[]):
            response = client.get('/api/rag/corpora')

            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            assert data['corpora'] == []

    def test_get_corpora_error(self, client):
        """Test getting corpora with service error"""
        with patch('web_app.services.rag_service.rag_service.get_all_corpora', side_effect=Exception("Service error")):
            response = client.get('/api/rag/corpora')

            assert response.status_code == 500
            data = response.get_json()
            assert data['success'] is False
            assert 'Service error' in data['error']

    def test_create_corpus_success(self, client):
        """Test successful corpus creation"""
        mock_corpus = MagicMock()
        mock_corpus.id = 'test-corpus-id'
        mock_corpus.name = 'Test Corpus'
        mock_corpus.description = 'Test Description'
        mock_corpus.created_at.isoformat.return_value = '2023-01-01T00:00:00'

        with patch('web_app.services.rag_service.rag_service.create_corpus', return_value=mock_corpus):
            response = client.post('/api/rag/corpora', json={
                'name': 'Test Corpus',
                'description': 'Test Description'
            })

            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            assert data['corpus']['name'] == 'Test Corpus'

    def test_create_corpus_error(self, client):
        """Test corpus creation with service error"""
        with patch('web_app.services.rag_service.rag_service.create_corpus', side_effect=Exception("Service error")):
            response = client.post('/api/rag/corpora', json={
                'name': 'Test Corpus'
            })

            assert response.status_code == 500
            data = response.get_json()
            assert data['success'] is False
            assert 'Service error' in data['error']

    @pytest.mark.parametrize("request_data,expected_error", [
        ({}, 'Name is required'),
        ({'description': 'Test description'}, 'Name is required'),
        ({'name': ''}, 'Name is required'),
    ])
    def test_create_corpus_validation(self, client, request_data, expected_error):
        """Test corpus creation validation"""
        response = client.post('/api/rag/corpora', json=request_data)

        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
        assert expected_error in data['error']

    def test_semantic_search_success(self, client):
        """Test successful semantic search"""
        # Create mock chunks with the expected attributes
        mock_chunk1 = MagicMock()
        mock_chunk1.id = 'chunk-1'
        mock_chunk1.filename = 'test.pdf'
        mock_chunk1.page_number = 1
        mock_chunk1.chunk_number = 1
        mock_chunk1.content = 'Test content 1'
        
        mock_chunk2 = MagicMock()
        mock_chunk2.id = 'chunk-2'
        mock_chunk2.filename = 'test.pdf'
        mock_chunk2.page_number = 1
        mock_chunk2.chunk_number = 2
        mock_chunk2.content = 'Test content 2'
        
        mock_results = [
            (mock_chunk1, 0.9),
            (mock_chunk2, 0.8)
        ]

        with patch('web_app.services.rag_service.rag_service.semantic_search', return_value=mock_results):
            response = client.post('/api/rag/search', json={
                'query': 'test query',
                'corpus_id': 'test-corpus'
            })

            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            assert len(data['results']) == 2
            assert data['results'][0]['id'] == 'chunk-1'
            assert data['results'][0]['similarity'] == 0.9

    def test_semantic_search_error(self, client):
        """Test semantic search with service error"""
        with patch('web_app.services.rag_service.rag_service.semantic_search', side_effect=Exception("Service error")):
            response = client.post('/api/rag/search', json={
                'query': 'test query'
            })

            assert response.status_code == 500
            data = response.get_json()
            assert data['success'] is False
            assert 'Service error' in data['error']

    @pytest.mark.parametrize("request_data,expected_error", [
        ({}, 'Query text is required'),
        ({'corpus_id': 'test'}, 'Query text is required'),
        ({'query': ''}, 'Query text is required'),
    ])
    def test_semantic_search_validation(self, client, request_data, expected_error):
        """Test semantic search validation"""
        response = client.post('/api/rag/search', json=request_data)

        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
        assert expected_error in data['error']

    def test_rag_query_success(self, client):
        """Test successful RAG query"""
        # Create mock query result with the expected structure
        mock_query = MagicMock()
        mock_query.id = 'query-id'
        mock_query.question = 'Test question'
        mock_query.answer = 'Test answer'
        mock_query.status = 'completed'
        mock_query.error_message = None
        mock_query.retrieved_chunks = ['chunk-1', 'chunk-2']
        mock_query.similarity_scores = [0.9, 0.8]

        with patch('web_app.services.rag_service.rag_service.generate_rag_response', return_value=mock_query):
            response = client.post('/api/rag/query', json={
                'question': 'Test question',
                'session_id': 'test-session'
            })

            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            assert data['query']['answer'] == 'Test answer'

    def test_rag_query_error(self, client):
        """Test RAG query with service error"""
        with patch('web_app.services.rag_service.rag_service.generate_rag_response', side_effect=Exception("Service error")):
            response = client.post('/api/rag/query', json={
                'question': 'Test question',
                'session_id': 'test-session'
            })

            assert response.status_code == 500
            data = response.get_json()
            assert data['success'] is False
            assert 'Service error' in data['error']

    @pytest.mark.parametrize("request_data,expected_error", [
        ({}, 'Question is required'),
        ({'session_id': 'test'}, 'Question is required'),
        ({'question': 'Test question'}, 'Session ID is required'),
        ({'question': '', 'session_id': 'test'}, 'Question is required'),
    ])
    def test_rag_query_validation(self, client, request_data, expected_error):
        """Test RAG query validation"""
        response = client.post('/api/rag/query', json=request_data)

        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
        assert expected_error in data['error']


class TestAPIResponseFormatConsistency:
    """Test that all API endpoints use consistent response formats"""

    @pytest.mark.parametrize("endpoint", [
        '/api/status',
        '/api/prompts',
        '/api/database/stats',
        '/api/rag/corpora'
    ])
    def test_endpoints_return_success_field(self, client, endpoint):
        """Test that all endpoints include a 'success' field in response"""
        # Mock all services that might be called
        with patch('web_app.services.system_service.system_service.check_system_status', return_value={}), \
             patch('web_app.services.prompt_service.prompt_service.get_all_prompts', return_value=[]), \
             patch('web_app.services.prompt_service.prompt_service.get_active_prompt', return_value=None), \
             patch('web_app.services.extraction_service.extraction_service.get_database_stats', return_value={}), \
             patch('web_app.services.rag_service.rag_service.get_all_corpora', return_value=[]):

            response = client.get(endpoint)
            data = response.get_json()
            assert 'success' in data, f"Endpoint {endpoint} missing 'success' field"

    @pytest.mark.parametrize("endpoint,expected_status,expected_error_key", [
        ('/api/run/invalid_tool', 400, 'error'),
        ('/api/prompts/nonexistent', 404, 'error'),
    ])
    def test_error_responses_format(self, client, endpoint, expected_status, expected_error_key):
        """Test that error responses follow consistent format"""
        # Mock for prompt endpoint
        if 'prompts' in endpoint:
            with patch('web_app.services.prompt_service.prompt_service.get_all_prompts', return_value=[]):
                response = client.get(endpoint)
        else:
            response = client.get(endpoint)

        assert response.status_code == expected_status
        data = response.get_json()
        assert expected_error_key in data
        assert data.get('success') is False


class TestAPIResponseFormatter:
    """Test API response formatting utilities (separated component)"""

    def test_success_response_basic(self, app):
        """Test basic success response"""
        with app.app_context():
            response, status_code = APIResponseFormatter.success()

            assert status_code == 200
            data = response.get_json()
            assert data['success'] is True
            assert data['message'] == ""

    def test_success_response_with_data(self, app):
        """Test success response with data"""
        with app.app_context():
            test_data = {'items': [1, 2, 3], 'count': 3}
            response, status_code = APIResponseFormatter.success(test_data, "Items retrieved")

            assert status_code == 200
            data = response.get_json()
            assert data['success'] is True
            assert data['message'] == "Items retrieved"
            assert data['items'] == [1, 2, 3]
            assert data['count'] == 3

    def test_error_response(self, app):
        """Test error response"""
        with app.app_context():
            response, status_code = APIResponseFormatter.error("Test error", 404)

            assert status_code == 404
            data = response.get_json()
            assert data['success'] is False
            assert data['error'] == "Test error"

    def test_service_result_success(self, app):
        """Test service result conversion for success"""
        with app.app_context():
            service_result = {
                'success': True,
                'message': 'Operation completed',
                'results': {'count': 5}
            }

            response, status_code = APIResponseFormatter.service_result(service_result)

            assert status_code == 200
            data = response.get_json()
            assert data['success'] is True
            assert data['message'] == 'Operation completed'
            assert data['count'] == 5

    def test_service_result_error(self, app):
        """Test service result conversion for error"""
        with app.app_context():
            service_result = {
                'success': False,
                'error': 'Operation failed'
            }

            response, status_code = APIResponseFormatter.service_result(service_result)

            assert status_code == 500
            data = response.get_json()
            assert data['success'] is False
            assert data['error'] == 'Operation failed'

    def test_tool_execution_result_success(self, app):
        """Test tool execution result formatting for success"""
        with app.app_context():
            result = {
                'success': True,
                'message': 'Tool completed successfully',
                'results': {'items_processed': 10}
            }

            response = APIResponseFormatter.tool_execution_result(result)

            data = response.get_json()
            assert data['success'] is True
            assert data['stdout'] == 'Tool completed successfully'
            assert data['stderr'] == ''
            assert data['return_code'] == 0
            assert data['results']['items_processed'] == 10

    def test_tool_execution_result_error(self, app):
        """Test tool execution result formatting for error"""
        with app.app_context():
            result = {
                'success': False,
                'error': 'Tool failed'
            }

            response = APIResponseFormatter.tool_execution_result(result)

            data = response.get_json()
            assert data['success'] is False
            assert data['stdout'] == ''
            assert data['stderr'] == 'Tool failed'
            assert data['return_code'] == 1

    def test_validate_json_request_success(self, app):
        """Test successful JSON request validation"""
        with app.app_context():
            request_data = {'name': 'test', 'value': 'data'}
            required_fields = ['name', 'value']

            result = APIResponseFormatter.validate_json_request(request_data, required_fields)

            assert result is None  # No error

    def test_validate_json_request_missing_data(self, app):
        """Test JSON request validation with missing data"""
        with app.app_context():
            result = APIResponseFormatter.validate_json_request(None, ['name'])

            assert result is not None
            response, status_code = result
            assert status_code == 400
            data = response.get_json()
            assert data['success'] is False
            assert 'No data provided' in data['error']

    def test_validate_json_request_missing_fields(self, app):
        """Test JSON request validation with missing required fields"""
        with app.app_context():
            request_data = {'name': 'test'}
            required_fields = ['name', 'value', 'type']

            result = APIResponseFormatter.validate_json_request(request_data, required_fields)

            assert result is not None
            response, status_code = result
            assert status_code == 400
            data = response.get_json()
            assert data['success'] is False
            assert 'Missing required fields: value, type' in data['error']
