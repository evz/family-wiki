"""
Tests for simplified RAG blueprint (without QuerySession complexity)
"""

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
        db.session.commit()

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
            corpus_id=str(corpus.id)
        )

    def test_ask_question_missing_question(self, client, db):
        """Test asking question without providing question text"""
        corpus = TextCorpus(name="Test Corpus", processing_status="completed")
        prompt = ExtractionPrompt(name="Test Prompt", prompt_text="Test", prompt_type="rag")
        db.session.add(corpus)
        db.session.add(prompt)
        db.session.commit()

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
        db.session.commit()

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
        db.session.commit()

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
        db.session.commit()

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
        with patch('web_app.blueprints.rag.get_available_embedding_models') as mock_models:
            mock_models.return_value = [
                {'id': 'test-model', 'name': 'Test Model', 'available': True}
            ]

            response = client.get('/rag/corpora/create')
            assert response.status_code == 200
