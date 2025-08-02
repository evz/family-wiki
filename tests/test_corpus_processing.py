"""
Tests for corpus processing with automatic model pulling
"""
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
import requests
import requests_mock

from web_app.database.models import TextCorpus
from web_app.tasks.rag_tasks import CorpusProcessingManager, process_corpus


class TestCorpusProcessingManager:
    """Test the corpus processing manager with model pulling functionality"""

    @pytest.fixture
    def sample_corpus_id(self):
        """Generate a sample corpus ID"""
        return str(uuid4())

    @pytest.fixture
    def mock_corpus(self, sample_corpus_id):
        """Mock corpus object"""
        corpus = MagicMock()
        corpus.id = sample_corpus_id
        corpus.name = "Test Corpus"
        corpus.raw_content = "This is test content for processing"
        corpus.embedding_model = "zylonai/multilingual-e5-large"
        corpus.processing_status = "pending"
        corpus.processing_error = None
        return corpus

    @pytest.fixture
    def manager(self, sample_corpus_id):
        """Create a corpus processing manager instance"""
        return CorpusProcessingManager(sample_corpus_id)

    def test_manager_initialization(self, sample_corpus_id):
        """Test manager initialization"""
        manager = CorpusProcessingManager(sample_corpus_id)
        assert manager.corpus_id == sample_corpus_id
        assert manager.corpus is None
        assert manager.rag_service is not None

    def test_get_ollama_connection(self, app, manager):
        """Test getting Ollama connection details"""
        app.config['OLLAMA_HOST'] = 'test-host'
        app.config['OLLAMA_PORT'] = 12345

        connection = manager._get_ollama_connection()
        assert connection == "http://test-host:12345"

    def test_is_model_available_true(self, app, manager):
        """Test checking model availability when model exists"""
        app.config['OLLAMA_HOST'] = 'localhost'
        app.config['OLLAMA_PORT'] = 11434

        mock_response = {
            'models': [
                {'name': 'zylonai/multilingual-e5-large'},
                {'name': 'other-model'}
            ]
        }

        with requests_mock.Mocker() as m:
            m.get('http://localhost:11434/api/tags', json=mock_response)

            result = manager._is_model_available('zylonai/multilingual-e5-large')
            assert result is True

    def test_is_model_available_false(self, app, manager):
        """Test checking model availability when model doesn't exist"""
        app.config['OLLAMA_HOST'] = 'localhost'
        app.config['OLLAMA_PORT'] = 11434

        mock_response = {
            'models': [
                {'name': 'other-model'},
                {'name': 'another-model'}
            ]
        }

        with requests_mock.Mocker() as m:
            m.get('http://localhost:11434/api/tags', json=mock_response)

            result = manager._is_model_available('zylonai/multilingual-e5-large')
            assert result is False

    def test_is_model_available_connection_error(self, app, manager):
        """Test checking model availability when connection fails"""
        app.config['OLLAMA_HOST'] = 'localhost'
        app.config['OLLAMA_PORT'] = 11434

        with requests_mock.Mocker() as m:
            m.get('http://localhost:11434/api/tags', exc=requests.exceptions.ConnectTimeout)

            result = manager._is_model_available('zylonai/multilingual-e5-large')
            assert result is False

    @patch('web_app.tasks.rag_tasks.current_task')
    @patch('web_app.tasks.rag_tasks.time.sleep')
    def test_pull_model_with_progress_success(self, mock_sleep, mock_task, app, manager):
        """Test successful model pulling with progress updates"""
        app.config['OLLAMA_HOST'] = 'localhost'
        app.config['OLLAMA_PORT'] = 11434

        # Mock streaming response
        streaming_data = [
            '{"status": "downloading", "total": 1000, "completed": 200}',
            '{"status": "downloading", "total": 1000, "completed": 500}',
            '{"status": "downloading", "total": 1000, "completed": 1000}',
            '{"status": "success"}'
        ]

        with requests_mock.Mocker() as m:
            # Mock the streaming response
            def stream_response(request, context):
                context.status_code = 200
                return '\n'.join(streaming_data)

            m.post('http://localhost:11434/api/pull', text=stream_response)

            manager._pull_model_with_progress('zylonai/multilingual-e5-large')

            # Check that progress updates were called
            assert mock_task.update_state.called

            # Check that sleep was called to wait for model availability
            mock_sleep.assert_called_with(3)

    def test_pull_model_with_progress_failure(self, app, manager):
        """Test model pulling failure"""
        app.config['OLLAMA_HOST'] = 'localhost'
        app.config['OLLAMA_PORT'] = 11434

        with requests_mock.Mocker() as m:
            m.post('http://localhost:11434/api/pull', status_code=500, text="Server Error")

            with pytest.raises(Exception) as exc_info:
                manager._pull_model_with_progress('zylonai/multilingual-e5-large')

            assert "Failed to start pull" in str(exc_info.value)

    @patch('web_app.tasks.rag_tasks.current_task')
    @patch.object(CorpusProcessingManager, '_is_model_available')
    def test_ensure_embedding_model_available_already_exists(self, mock_is_available, mock_task, manager, mock_corpus):
        """Test ensuring model availability when model already exists"""
        manager.corpus = mock_corpus
        mock_is_available.return_value = True

        manager._ensure_embedding_model_available()

        # Should check availability and return early
        mock_is_available.assert_called_once_with('zylonai/multilingual-e5-large')
        mock_task.update_state.assert_called()

    @patch('web_app.tasks.rag_tasks.current_task')
    @patch.object(CorpusProcessingManager, '_pull_model_with_progress')
    @patch.object(CorpusProcessingManager, '_is_model_available')
    def test_ensure_embedding_model_available_needs_pull(self, mock_is_available, mock_pull, mock_task, manager, mock_corpus):
        """Test ensuring model availability when model needs to be pulled"""
        manager.corpus = mock_corpus
        mock_is_available.side_effect = [False, True]  # Not available, then available after pull

        manager._ensure_embedding_model_available()

        # Should attempt to pull the model
        mock_pull.assert_called_once_with('zylonai/multilingual-e5-large')

        # Should verify model is available after pull
        assert mock_is_available.call_count == 2

    @patch('web_app.tasks.rag_tasks.current_task')
    @patch.object(CorpusProcessingManager, '_pull_model_with_progress')
    @patch.object(CorpusProcessingManager, '_is_model_available')
    def test_ensure_embedding_model_available_pull_fails_verification(self, mock_is_available, mock_pull, mock_task, manager, mock_corpus):
        """Test ensuring model availability when pull succeeds but verification fails"""
        manager.corpus = mock_corpus
        mock_is_available.return_value = False  # Never becomes available

        with pytest.raises(Exception) as exc_info:
            manager._ensure_embedding_model_available()

        assert "was pulled but is not showing as available" in str(exc_info.value)

    def test_ensure_embedding_model_no_model_specified(self, manager, mock_corpus):
        """Test ensuring model availability when no model is specified"""
        manager.corpus = mock_corpus
        manager.corpus.embedding_model = None

        # Should return early without error
        manager._ensure_embedding_model_available()

    def test_load_corpus_success(self, app, manager, mock_corpus, sample_corpus_id):
        """Test successful corpus loading"""
        # Mock the rag_repository instance directly
        manager.rag_repository = MagicMock()
        manager.rag_repository.get_corpus_by_id.return_value = mock_corpus

        manager._load_corpus()

        assert manager.corpus == mock_corpus
        manager.rag_repository.get_corpus_by_id.assert_called_once_with(sample_corpus_id)

    def test_load_corpus_not_found(self, app, manager, sample_corpus_id):
        """Test corpus loading when corpus doesn't exist"""
        # Mock the rag_repository instance directly
        manager.rag_repository = MagicMock()
        manager.rag_repository.get_corpus_by_id.return_value = None

        with pytest.raises(ValueError) as exc_info:
            manager._load_corpus()

        assert "Corpus not found" in str(exc_info.value)

    def test_load_corpus_no_content(self, app, manager, mock_corpus, sample_corpus_id):
        """Test corpus loading when corpus has no raw content"""
        mock_corpus.raw_content = None
        # Mock the rag_repository instance directly
        manager.rag_repository = MagicMock()
        manager.rag_repository.get_corpus_by_id.return_value = mock_corpus

        with pytest.raises(ValueError) as exc_info:
            manager._load_corpus()

        assert "Corpus has no raw content to process" in str(exc_info.value)

    def test_update_corpus_status(self, app, manager, mock_corpus):
        """Test updating corpus status"""
        manager.corpus = mock_corpus
        # Mock the rag_repository instance directly
        manager.rag_repository = MagicMock()
        manager.rag_repository.update_corpus_status.return_value = mock_corpus

        manager._update_corpus_status('processing', 'Test error')

        assert mock_corpus.processing_status == 'processing'
        assert mock_corpus.processing_error == 'Test error'
        manager.rag_repository.update_corpus_status.assert_called_once_with(manager.corpus_id, 'processing', 'Test error')

    @patch('web_app.tasks.rag_tasks.current_task')
    @patch.object(CorpusProcessingManager, '_ensure_embedding_model_available')
    @patch.object(CorpusProcessingManager, '_process_text_content')
    @patch.object(CorpusProcessingManager, '_load_corpus')
    def test_run_corpus_processing_success(self, mock_load, mock_process, mock_ensure_model, mock_task, app, manager, mock_corpus):
        """Test successful complete corpus processing workflow"""
        manager.corpus = mock_corpus
        mock_process.return_value = 42  # 42 chunks stored
        
        # Mock the rag_repository instance directly
        manager.rag_repository = MagicMock()
        manager.rag_repository.update_corpus_status.return_value = mock_corpus

        result = manager.run_corpus_processing()

        # Check workflow sequence
        mock_load.assert_called_once()
        mock_ensure_model.assert_called_once()
        mock_process.assert_called_once()

        # Check result
        assert result['success'] is True
        assert result['corpus_id'] == manager.corpus_id
        assert result['corpus_name'] == 'Test Corpus'
        assert result['chunks_stored'] == 42

        # Check status updates
        assert mock_corpus.processing_status == 'completed'


class TestProcessCorpusTask:
    """Test the Celery task wrapper"""

    @patch.object(CorpusProcessingManager, 'run_corpus_processing')
    @patch.object(CorpusProcessingManager, '__init__')
    def test_process_corpus_success(self, mock_init, mock_run):
        """Test successful corpus processing task"""
        mock_init.return_value = None
        mock_run.return_value = {'success': True, 'chunks_stored': 42}

        result = process_corpus('test-corpus-id')

        assert result['success'] is True
        assert result['chunks_stored'] == 42

    @patch.object(CorpusProcessingManager, 'run_corpus_processing')
    @patch.object(CorpusProcessingManager, 'handle_processing_error')
    @patch.object(CorpusProcessingManager, '__init__')
    def test_process_corpus_value_error(self, mock_init, mock_handle_error, mock_run):
        """Test corpus processing task with ValueError"""
        mock_init.return_value = None
        mock_run.side_effect = ValueError("Invalid corpus data")

        with pytest.raises(ValueError):
            process_corpus('test-corpus-id')

        mock_handle_error.assert_called_once()

    @patch.object(CorpusProcessingManager, 'run_corpus_processing')
    @patch.object(CorpusProcessingManager, 'handle_processing_error')
    @patch.object(CorpusProcessingManager, '__init__')
    def test_process_corpus_connection_error(self, mock_init, mock_handle_error, mock_run):
        """Test corpus processing task with ConnectionError"""
        mock_init.return_value = None
        mock_run.side_effect = ConnectionError("Cannot connect to Ollama")

        with pytest.raises(ConnectionError):
            process_corpus('test-corpus-id')

        mock_handle_error.assert_called_once()

    @patch.object(CorpusProcessingManager, 'run_corpus_processing')
    @patch.object(CorpusProcessingManager, 'handle_processing_error')
    @patch.object(CorpusProcessingManager, '__init__')
    def test_process_corpus_unexpected_error(self, mock_init, mock_handle_error, mock_run):
        """Test corpus processing task with unexpected error"""
        mock_init.return_value = None
        mock_run.side_effect = Exception("Unexpected error")

        with pytest.raises(Exception):
            process_corpus('test-corpus-id')

        mock_handle_error.assert_called_once()
