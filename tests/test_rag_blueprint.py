"""
Tests for simplified RAG blueprint (without QuerySession complexity)
"""

import io
from unittest.mock import Mock, patch

import pytest

from tests.conftest import BaseTestConfig
from web_app.database.models import ExtractionPrompt, TextCorpus


class RAGBlueprintTestConfig(BaseTestConfig):
    """Test configuration"""
    def __init__(self):
        super().__init__()
        self.sqlalchemy_database_uri = 'sqlite:///:memory:'


class TestSimplifiedRAGBlueprint:
    """Test simplified RAG blueprint routes"""

    @pytest.fixture
    def mock_rag_service_class(self):
        """Mock RAG service class"""
        with patch('web_app.blueprints.rag.RAGService') as mock_service_class:
            yield mock_service_class

    @pytest.fixture
    def mock_prompt_service_class(self):
        """Mock Prompt service class"""
        with patch('web_app.blueprints.rag.PromptService') as mock_service_class:
            yield mock_service_class

    def test_index_route_with_active_corpus(self, client, mock_rag_service_class, mock_prompt_service_class):
        """Test RAG index route with active corpus"""
        # Mock corpus data with proper attributes for template
        mock_corpus = Mock()
        mock_corpus.id = "corpus-1"
        mock_corpus.name = "Test Corpus"
        mock_corpus.processing_status = "completed"
        mock_corpus.description = "Test description"
        mock_corpus.created_at = Mock()
        mock_corpus.created_at.strftime.return_value = "2025-01-01 10:00"
        mock_corpus.embedding_model = "test-model"

        # Mock prompt data
        mock_prompt = Mock()
        mock_prompt.id = "prompt-1"
        mock_prompt.name = "Test RAG Prompt"
        mock_prompt.description = "Test prompt for RAG"

        # Configure mocks
        mock_rag_instance = mock_rag_service_class.return_value
        mock_rag_instance.get_all_corpora.return_value = [mock_corpus]

        mock_prompt_instance = mock_prompt_service_class.return_value
        mock_prompt_instance.get_all_prompts.return_value = [mock_prompt]

        response = client.get('/rag/')
        assert response.status_code == 200

    def test_ask_question_success(self, client, db, mock_rag_service_class):
        """Test successful question asking with simplified workflow"""
        # Create test corpus and prompt
        corpus = TextCorpus(name="Test Corpus", description="Test", processing_status="completed")
        prompt = ExtractionPrompt(name="Test RAG Prompt", prompt_text="Answer: {answer}", prompt_type="rag")
        db.session.add(corpus)
        db.session.add(prompt)
        db.session.flush()  # Use flush instead of commit for tests

        # Mock RAG response
        mock_rag_instance = mock_rag_service_class.return_value
        mock_rag_instance.ask_question.return_value = {
            "answer": "Genealogy is the study of family history",
            "retrieved_chunks": ["chunk1"],
            "similarity_scores": [0.85],
            "corpus_name": "Test Corpus",
            "question": "What is genealogy?"
        }

        response = client.post('/rag/ask-question', data={
            'question': 'What is genealogy?',
            'corpus_id': str(corpus.id),
            'prompt_id': str(prompt.id)
        })

        assert response.status_code == 302  # Redirect after successful query
        mock_rag_instance.ask_question.assert_called_once_with(
            question='What is genealogy?',
            prompt_id=str(prompt.id),
            corpus_id=str(corpus.id),
            max_chunks=None,
            similarity_threshold=0.55
        )

    def test_ask_question_missing_question(self, client, db):
        """Test asking question without providing question text"""
        corpus = TextCorpus(name="Test Corpus", processing_status="completed")
        prompt = ExtractionPrompt(name="Test Prompt", prompt_text="Test", prompt_type="rag")
        db.session.add(corpus)
        db.session.add(prompt)
        db.session.flush()  # Use flush instead of commit for tests

        response = client.post('/rag/ask-question', data={
            'question': '',  # Empty question
            'corpus_id': str(corpus.id),
            'prompt_id': str(prompt.id)
        })

        assert response.status_code == 302  # Redirect with error message

    def test_ask_question_missing_corpus(self, client, db):
        """Test asking question without selecting corpus"""
        prompt = ExtractionPrompt(name="Test Prompt", prompt_text="Test", prompt_type="rag")
        db.session.add(prompt)
        db.session.flush()  # Use flush instead of commit for tests

        response = client.post('/rag/ask-question', data={
            'question': 'What is genealogy?',
            'corpus_id': '',  # No corpus selected
            'prompt_id': str(prompt.id)
        })

        assert response.status_code == 302  # Redirect with error message

    def test_ask_question_missing_prompt(self, client, db):
        """Test asking question without selecting prompt"""
        corpus = TextCorpus(name="Test Corpus", processing_status="completed")
        db.session.add(corpus)
        db.session.flush()  # Use flush instead of commit for tests

        response = client.post('/rag/ask-question', data={
            'question': 'What is genealogy?',
            'corpus_id': str(corpus.id),
            'prompt_id': ''  # No prompt selected
        })

        assert response.status_code == 302  # Redirect with error message

    def test_ask_question_corpus_not_ready(self, client, db):
        """Test asking question with corpus that's not ready"""
        corpus = TextCorpus(name="Test Corpus", processing_status="processing")  # Not completed
        prompt = ExtractionPrompt(name="Test Prompt", prompt_text="Test", prompt_type="rag")
        db.session.add(corpus)
        db.session.add(prompt)
        db.session.flush()  # Use flush instead of commit for tests

        response = client.post('/rag/ask-question', data={
            'question': 'What is genealogy?',
            'corpus_id': str(corpus.id),
            'prompt_id': str(prompt.id)
        })

        assert response.status_code == 302  # Redirect with error message

    def test_corpora_list_route(self, client, mock_rag_service_class):
        """Test corpora list route"""
        mock_corpus = Mock()
        mock_corpus.name = "Test Corpus"
        mock_corpus.processing_status = "completed"

        mock_rag_instance = mock_rag_service_class.return_value
        mock_rag_instance.get_all_corpora.return_value = [mock_corpus]

        response = client.get('/rag/corpora')
        assert response.status_code == 200

    def test_create_corpus_get_route(self, client):
        """Test corpus creation form GET route"""
        with patch('web_app.services.system_service.SystemService.get_available_embedding_models') as mock_models:
            mock_models.return_value = [
                {'id': 'test-model', 'name': 'Test Model', 'available': True}
            ]

            response = client.get('/rag/corpora/create')
            assert response.status_code == 200

    def test_delete_corpus_success(self, client, db, mock_rag_service_class):
        """Test successful corpus deletion"""
        # Create test corpus
        corpus = TextCorpus(name="Test Corpus", description="Test", processing_status="completed")
        db.session.add(corpus)
        db.session.flush()  # Use flush instead of commit for tests

        # Mock RAG service deletion
        mock_rag_instance = mock_rag_service_class.return_value
        mock_rag_instance.delete_corpus.return_value = {
            'success': True,
            'corpus_name': 'Test Corpus',
            'deleted_chunks': 5,
            'deleted_queries': 0,
            'message': 'Successfully deleted corpus "Test Corpus", 5 text chunks'
        }

        response = client.post(f'/rag/corpora/{corpus.id}/delete')

        # Should redirect to corpora list
        assert response.status_code == 302
        assert response.location.endswith('/rag/corpora')

        # Verify service was called with correct ID
        mock_rag_instance.delete_corpus.assert_called_once_with(str(corpus.id))

    def test_delete_corpus_not_found(self, client, db, mock_rag_service_class):
        """Test deletion of non-existent corpus"""
        from web_app.services.exceptions import NotFoundError

        # Mock RAG service to raise NotFoundError
        mock_rag_instance = mock_rag_service_class.return_value
        mock_rag_instance.delete_corpus.side_effect = NotFoundError("Corpus not found")

        fake_id = "00000000-0000-0000-0000-000000000000"
        response = client.post(f'/rag/corpora/{fake_id}/delete')

        # Should redirect to corpora list
        assert response.status_code == 302
        assert response.location.endswith('/rag/corpora')

    def test_delete_corpus_error(self, client, db, mock_rag_service_class):
        """Test deletion with service error"""
        # Create test corpus
        corpus = TextCorpus(name="Test Corpus", description="Test", processing_status="completed")
        db.session.add(corpus)
        db.session.flush()  # Use flush instead of commit for tests

        # Mock RAG service to raise generic error
        mock_rag_instance = mock_rag_service_class.return_value
        mock_rag_instance.delete_corpus.side_effect = Exception("Database error")

        response = client.post(f'/rag/corpora/{corpus.id}/delete')

        # Should redirect to corpora list
        assert response.status_code == 302
        assert response.location.endswith('/rag/corpora')


class TestRAGCorpusCreation:
    """Test corpus creation functionality with comprehensive scenarios"""

    @pytest.fixture
    def mock_system_service_class(self):
        """Mock System service class"""
        with patch('web_app.blueprints.rag.SystemService') as mock_service_class:
            yield mock_service_class

    @pytest.fixture
    def mock_rag_service_class(self):
        """Mock RAG service class"""
        with patch('web_app.blueprints.rag.RAGService') as mock_service_class:
            yield mock_service_class

    @pytest.fixture
    def mock_safe_task_submit(self):
        """Mock safe task submit"""
        with patch('web_app.blueprints.rag.safe_task_submit') as mock_task:
            mock_task.return_value = Mock(id='test-task-123')
            yield mock_task

    def test_create_corpus_post_success(self, client, mock_system_service_class, mock_rag_service_class, mock_safe_task_submit):
        """Test successful corpus creation"""
        # Mock system service
        mock_system_instance = mock_system_service_class.return_value
        mock_system_instance.get_available_embedding_models.return_value = [
            {'id': 'test-model', 'name': 'Test Model', 'available': True}
        ]
        mock_system_instance.validate_embedding_model.return_value = True

        # Mock RAG service
        mock_corpus = Mock()
        mock_corpus.id = "corpus-123"
        mock_corpus.name = "Test Corpus"
        mock_rag_instance = mock_rag_service_class.return_value
        mock_rag_instance.create_corpus.return_value = mock_corpus

        # Create test file data
        data = {
            'name': 'Test Corpus',
            'description': 'Test description',
            'embedding_model': 'test-model',
            'chunk_size': '1500',
            'query_chunk_limit': '20',
            'text_file': (io.BytesIO(b'Test content for corpus'), 'test.txt')
        }

        response = client.post('/rag/corpora/create', data=data)

        assert response.status_code == 302
        assert response.location.endswith('/rag/corpora')
        mock_rag_instance.create_corpus.assert_called_once()
        mock_safe_task_submit.assert_called_once()

    def test_create_corpus_missing_name(self, client, mock_system_service_class):
        """Test corpus creation with missing name"""
        mock_system_instance = mock_system_service_class.return_value
        mock_system_instance.get_available_embedding_models.return_value = []

        data = {
            'name': '',  # Missing name
            'description': 'Test description',
            'text_file': (io.BytesIO(b'Test content'), 'test.txt')
        }

        response = client.post('/rag/corpora/create', data=data)
        assert response.status_code == 200  # Returns form with error

    def test_create_corpus_missing_file(self, client, mock_system_service_class):
        """Test corpus creation with missing file"""
        mock_system_instance = mock_system_service_class.return_value
        mock_system_instance.get_available_embedding_models.return_value = []

        data = {
            'name': 'Test Corpus',
            'description': 'Test description'
            # No file
        }

        response = client.post('/rag/corpora/create', data=data)
        assert response.status_code == 200  # Returns form with error

    def test_create_corpus_invalid_chunk_size(self, client, mock_system_service_class):
        """Test corpus creation with invalid chunk size"""
        mock_system_instance = mock_system_service_class.return_value
        mock_system_instance.get_available_embedding_models.return_value = []

        data = {
            'name': 'Test Corpus',
            'chunk_size': '100',  # Too small
            'text_file': (io.BytesIO(b'Test content'), 'test.txt')
        }

        response = client.post('/rag/corpora/create', data=data)
        assert response.status_code == 200  # Returns form with error

    def test_create_corpus_invalid_query_limit(self, client, mock_system_service_class):
        """Test corpus creation with invalid query chunk limit"""
        mock_system_instance = mock_system_service_class.return_value
        mock_system_instance.get_available_embedding_models.return_value = []

        data = {
            'name': 'Test Corpus',
            'query_chunk_limit': '100',  # Too large
            'text_file': (io.BytesIO(b'Test content'), 'test.txt')
        }

        response = client.post('/rag/corpora/create', data=data)
        assert response.status_code == 200  # Returns form with error

    def test_create_corpus_invalid_file_type(self, client, mock_system_service_class):
        """Test corpus creation with invalid file type"""
        mock_system_instance = mock_system_service_class.return_value
        mock_system_instance.get_available_embedding_models.return_value = []

        data = {
            'name': 'Test Corpus',
            'text_file': (io.BytesIO(b'Test content'), 'test.pdf')  # Wrong file type
        }

        response = client.post('/rag/corpora/create', data=data)
        assert response.status_code == 200  # Returns form with error

    def test_create_corpus_empty_file(self, client, mock_system_service_class):
        """Test corpus creation with empty file"""
        mock_system_instance = mock_system_service_class.return_value
        mock_system_instance.get_available_embedding_models.return_value = []

        data = {
            'name': 'Test Corpus',
            'text_file': (io.BytesIO(b''), 'test.txt')  # Empty file
        }

        response = client.post('/rag/corpora/create', data=data)
        assert response.status_code == 200  # Returns form with error

    def test_create_corpus_unicode_error(self, client, mock_system_service_class):
        """Test corpus creation with invalid UTF-8 file"""
        mock_system_instance = mock_system_service_class.return_value
        mock_system_instance.get_available_embedding_models.return_value = []

        # Invalid UTF-8 bytes
        invalid_utf8 = b'\xff\xfe\x00\x00'
        data = {
            'name': 'Test Corpus',
            'text_file': (io.BytesIO(invalid_utf8), 'test.txt')
        }

        response = client.post('/rag/corpora/create', data=data)
        assert response.status_code == 200  # Returns form with error


class TestRAGChatInterface:
    """Test chat interface functionality"""

    @pytest.fixture
    def mock_rag_service_class(self):
        """Mock RAG service class"""
        with patch('web_app.blueprints.rag.RAGService') as mock_service_class:
            yield mock_service_class

    @pytest.fixture
    def mock_prompt_service_class(self):
        """Mock Prompt service class"""
        with patch('web_app.blueprints.rag.PromptService') as mock_service_class:
            yield mock_service_class

    @pytest.fixture
    def mock_rag_repository_class(self):
        """Mock RAG repository class"""
        with patch('web_app.blueprints.rag.RAGRepository') as mock_repository_class:
            yield mock_repository_class

    def test_chat_interface_route(self, client, mock_rag_service_class, mock_prompt_service_class):
        """Test chat interface GET route"""
        # Mock corpus and prompt data
        mock_corpus = Mock()
        mock_corpus.name = "Test Corpus"
        mock_prompt = Mock()
        mock_prompt.name = "Test Prompt"

        mock_rag_instance = mock_rag_service_class.return_value
        mock_rag_instance.get_all_corpora.return_value = [mock_corpus]

        mock_prompt_instance = mock_prompt_service_class.return_value
        mock_prompt_instance.get_all_prompts.return_value = [mock_prompt]

        response = client.get('/rag/chat')
        assert response.status_code == 200

    def test_chat_ask_success(self, client, mock_rag_service_class, mock_rag_repository_class):
        """Test successful chat ask request"""
        import uuid

        # Mock repository
        mock_corpus = Mock()
        mock_corpus.name = "Test Corpus"
        mock_corpus.processing_status = "completed"
        mock_repo_instance = mock_rag_repository_class.return_value
        mock_repo_instance.get_corpus_by_id.return_value = mock_corpus
        mock_repo_instance.start_new_conversation.return_value = uuid.uuid4()

        # Mock RAG service
        mock_rag_instance = mock_rag_service_class.return_value
        mock_rag_instance.ask_question.return_value = {
            'answer': 'Test answer',
            'retrieved_chunks': ['chunk1'],
            'similarity_scores': [0.85],
            'prompt_name': 'Test Prompt'
        }

        data = {
            'question': 'What is genealogy?',
            'corpus_id': 'corpus-123',
            'prompt_id': 'prompt-123',
            'similarity_threshold': '0.6',
            'message_sequence': '1'
        }

        response = client.post('/rag/chat/ask', data=data)
        assert response.status_code == 200
        
        # Check JSON response
        json_data = response.get_json()
        assert json_data['success'] is True
        assert 'answer' in json_data

    def test_chat_ask_missing_question(self, client):
        """Test chat ask with missing question"""
        data = {
            'question': '',  # Missing question
            'corpus_id': 'corpus-123',
            'prompt_id': 'prompt-123'
        }

        response = client.post('/rag/chat/ask', data=data)
        assert response.status_code == 200
        
        json_data = response.get_json()
        assert json_data['success'] is False
        assert 'error' in json_data

    def test_chat_ask_missing_corpus(self, client):
        """Test chat ask with missing corpus"""
        data = {
            'question': 'What is genealogy?',
            'corpus_id': '',  # Missing corpus
            'prompt_id': 'prompt-123'
        }

        response = client.post('/rag/chat/ask', data=data)
        assert response.status_code == 200
        
        json_data = response.get_json()
        assert json_data['success'] is False
        assert 'error' in json_data

    def test_chat_ask_corpus_not_ready(self, client, mock_rag_repository_class):
        """Test chat ask with corpus not ready"""
        mock_corpus = Mock()
        mock_corpus.name = "Test Corpus"
        mock_corpus.processing_status = "processing"  # Not completed
        mock_repo_instance = mock_rag_repository_class.return_value
        mock_repo_instance.get_corpus_by_id.return_value = mock_corpus

        data = {
            'question': 'What is genealogy?',
            'corpus_id': 'corpus-123',
            'prompt_id': 'prompt-123'
        }

        response = client.post('/rag/chat/ask', data=data)
        assert response.status_code == 200
        
        json_data = response.get_json()
        assert json_data['success'] is False
        assert 'not ready' in json_data['error']

    def test_chat_ask_invalid_threshold(self, client):
        """Test chat ask with invalid similarity threshold"""
        data = {
            'question': 'What is genealogy?',
            'corpus_id': 'corpus-123', 
            'prompt_id': 'prompt-123',
            'similarity_threshold': 'invalid'  # Invalid threshold
        }

        response = client.post('/rag/chat/ask', data=data)
        assert response.status_code == 200
        
        json_data = response.get_json()
        assert json_data['success'] is False
        assert 'threshold' in json_data['error']

    def test_chat_ask_with_conversation_id(self, client, mock_rag_service_class, mock_rag_repository_class):
        """Test chat ask with existing conversation ID"""
        import uuid

        conversation_id = str(uuid.uuid4())
        
        # Mock repository
        mock_corpus = Mock()
        mock_corpus.name = "Test Corpus"
        mock_corpus.processing_status = "completed"
        mock_repo_instance = mock_rag_repository_class.return_value
        mock_repo_instance.get_corpus_by_id.return_value = mock_corpus

        # Mock RAG service
        mock_rag_instance = mock_rag_service_class.return_value
        mock_rag_instance.ask_question.return_value = {
            'answer': 'Test answer',
            'retrieved_chunks': ['chunk1'],
            'similarity_scores': [0.85],
            'prompt_name': 'Test Prompt'
        }

        data = {
            'question': 'What is genealogy?',
            'corpus_id': 'corpus-123',
            'prompt_id': 'prompt-123',
            'conversation_id': conversation_id,
            'message_sequence': '2'
        }

        response = client.post('/rag/chat/ask', data=data)
        assert response.status_code == 200
        
        json_data = response.get_json()
        assert json_data['success'] is True
        assert json_data['conversation_id'] == conversation_id


class TestRAGCorpusTransactionTiming:
    """Test corpus creation transaction timing to prevent race conditions with background tasks"""

    @pytest.fixture
    def mock_system_service_class(self):
        """Mock System service class"""
        with patch('web_app.blueprints.rag.SystemService') as mock_service_class:
            yield mock_service_class

    @pytest.fixture
    def mock_rag_service_class(self):
        """Mock RAG service class"""
        with patch('web_app.blueprints.rag.RAGService') as mock_service_class:
            yield mock_service_class

    @pytest.fixture
    def mock_safe_task_submit(self):
        """Mock safe task submit"""
        with patch('web_app.blueprints.rag.safe_task_submit') as mock_task:
            mock_task.return_value = Mock(id='test-task-123')
            yield mock_task

    def test_corpus_committed_before_task_submission(self, client, db, mock_system_service_class, mock_rag_service_class, mock_safe_task_submit):
        """Test that corpus is committed to database before background task is submitted"""
        # Mock system service
        mock_system_instance = mock_system_service_class.return_value
        mock_system_instance.get_available_embedding_models.return_value = [
            {'id': 'test-model', 'name': 'Test Model', 'available': True}
        ]
        mock_system_instance.validate_embedding_model.return_value = True

        # Track database commits and task submissions
        commit_called = False
        task_submitted = False
        original_commit = db.session.commit
        
        def mock_commit():
            nonlocal commit_called
            commit_called = True
            return original_commit()
        
        def mock_task_submit(*args, **kwargs):
            nonlocal task_submitted, commit_called
            task_submitted = True
            # Verify commit happened before task submission
            assert commit_called, "Database transaction should be committed before task submission"
            return Mock(id='test-task-123')
        
        # Create a real corpus that will be checked in the database
        from web_app.database.models import TextCorpus
        corpus_id = None
        
        def mock_create_corpus(*args, **kwargs):
            nonlocal corpus_id
            # Create a real corpus in the database
            corpus = TextCorpus(
                name=kwargs.get('name', 'Test Corpus'),
                description=kwargs.get('description', ''),
                raw_content=kwargs.get('raw_content'),
                embedding_model=kwargs.get('embedding_model', 'test-model'),
                chunk_size=kwargs.get('chunk_size', 1500),
                query_chunk_limit=kwargs.get('query_chunk_limit', 20),
                processing_status=kwargs.get('processing_status', 'pending')
            )
            db.session.add(corpus)
            corpus_id = corpus.id
            return corpus

        # Mock RAG service
        mock_rag_instance = mock_rag_service_class.return_value
        
        def mock_create_corpus_and_start_processing(*args, **kwargs):
            nonlocal corpus_id
            # Create a real corpus in the database
            corpus = TextCorpus(
                name=kwargs.get('name', 'Test Corpus'),
                description=kwargs.get('description', ''),
                raw_content=kwargs.get('raw_content'),
                embedding_model=kwargs.get('embedding_model', 'test-model'),
                chunk_size=kwargs.get('chunk_size', 1500),
                query_chunk_limit=kwargs.get('query_chunk_limit', 20),
                processing_status=kwargs.get('processing_status', 'pending')
            )
            db.session.add(corpus)
            corpus_id = corpus.id
            
            # Simulate the commit that happens in the service
            mock_commit()
            
            # Simulate task submission
            task = mock_task_submit()
            
            return corpus, task
        
        mock_rag_instance.create_corpus_and_start_processing.side_effect = mock_create_corpus_and_start_processing
        
        # Submit corpus creation form
        data = {
            'name': 'Transaction Test Corpus',
            'description': 'Test corpus for transaction timing',
            'embedding_model': 'test-model',
            'chunk_size': '1500',
            'query_chunk_limit': '20',
            'text_file': (io.BytesIO(b'Test content for transaction timing'), 'test.txt')
        }

        response = client.post('/rag/corpora/create', data=data)

        # Verify the response
        assert response.status_code == 302
        assert response.location.endswith('/rag/corpora')
        
        # Verify both commit and task submission happened
        assert commit_called, "Database commit should have been called"
        assert task_submitted, "Background task should have been submitted"
        
        # Verify the corpus exists in database after commit
        assert corpus_id is not None
        saved_corpus = db.session.get(TextCorpus, corpus_id)
        assert saved_corpus is not None
        assert saved_corpus.name == 'Transaction Test Corpus'
        assert saved_corpus.raw_content == 'Test content for transaction timing'
        assert saved_corpus.processing_status == 'pending'

    def test_background_task_can_load_corpus_after_commit(self, client, db, mock_system_service_class, mock_rag_service_class, mock_safe_task_submit):
        """Test that background task can successfully load the corpus from database"""
        # Mock system service
        mock_system_instance = mock_system_service_class.return_value
        mock_system_instance.get_available_embedding_models.return_value = [
            {'id': 'test-model', 'name': 'Test Model', 'available': True}
        ]
        mock_system_instance.validate_embedding_model.return_value = True

        # Create a real corpus that will be persisted
        from web_app.database.models import TextCorpus
        corpus_id = None
        
        # Mock task submission to simulate what background task would do
        def mock_task_submit(task_func, description, corpus_id_str):
            # Simulate what the background task would do - try to load the corpus
            loaded_corpus = db.session.get(TextCorpus, corpus_id_str)
            assert loaded_corpus is not None, f"Background task should be able to load corpus {corpus_id_str}"
            assert loaded_corpus.raw_content is not None, "Background task should have access to raw_content"
            return Mock(id='test-task-123')
        
        def mock_create_corpus_and_start_processing(*args, **kwargs):
            nonlocal corpus_id
            corpus = TextCorpus(
                name=kwargs.get('name', 'Test Corpus'),
                description=kwargs.get('description', ''),
                raw_content=kwargs.get('raw_content'),
                embedding_model=kwargs.get('embedding_model', 'test-model'),
                chunk_size=kwargs.get('chunk_size', 1500),
                query_chunk_limit=kwargs.get('query_chunk_limit', 20),
                processing_status=kwargs.get('processing_status', 'pending')
            )
            db.session.add(corpus)
            corpus_id = corpus.id
            db.session.commit()  # Commit to make it available
            
            # Now simulate task submission
            task = mock_task_submit(None, "test", str(corpus_id))
            return corpus, task

        # Mock RAG service
        mock_rag_instance = mock_rag_service_class.return_value
        mock_rag_instance.create_corpus_and_start_processing.side_effect = mock_create_corpus_and_start_processing
        
        # Submit corpus creation form
        data = {
            'name': 'Background Task Test Corpus',
            'description': 'Test corpus for background task access',
            'embedding_model': 'test-model',
            'chunk_size': '1500',
            'query_chunk_limit': '20',
            'text_file': (io.BytesIO(b'Content for background task test'), 'test.txt')
        }

        response = client.post('/rag/corpora/create', data=data)

        # Verify the response
        assert response.status_code == 302
        
        # The mock_task_submit function will have asserted that the corpus was loadable
        # If we get here without assertion errors, the test passed
