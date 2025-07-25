"""
Tests for RAG blueprint
"""

from unittest.mock import Mock, patch

import pytest

from app import create_app
from tests.conftest import BaseTestConfig


class RAGBlueprintTestConfig(BaseTestConfig):
    """Test configuration"""
    def __init__(self):
        super().__init__()
        self.sqlalchemy_database_uri = 'sqlite:///:memory:'


class TestRAGBlueprint:
    """Test RAG blueprint routes"""

    @pytest.fixture
    def mock_rag_service_class(self):
        """Mock RAG service class"""
        with patch('web_app.blueprints.rag.RAGService') as mock_service_class:
            yield mock_service_class

    def test_index_route_with_active_corpus(self, client, mock_rag_service_class):
        """Test RAG index route with active corpus"""
        # Mock corpus data
        mock_corpus1 = Mock()
        mock_corpus1.id = "corpus-1"
        mock_corpus1.name = "Test Corpus 1"

        mock_corpus2 = Mock()
        mock_corpus2.id = "corpus-2"
        mock_corpus2.name = "Test Corpus 2"

        mock_active_corpus = mock_corpus1

        mock_corpus_stats = {
            'total_chunks': 150,
            'total_sources': 5,
            'avg_chunk_length': 512
        }

        # Configure mock instance
        mock_rag_instance = mock_rag_service_class.return_value
        mock_rag_instance.get_all_corpora.return_value = [mock_corpus1, mock_corpus2]
        mock_rag_instance.get_active_corpus.return_value = mock_active_corpus
        mock_rag_instance.get_corpus_stats.return_value = mock_corpus_stats

        response = client.get('/rag/')

        assert response.status_code == 200
        assert b'Test Corpus 1' in response.data

        # Verify service calls
        mock_rag_instance.get_all_corpora.assert_called_once()
        mock_rag_instance.get_active_corpus.assert_called_once()
        mock_rag_instance.get_corpus_stats.assert_called_once_with("corpus-1")

    def test_index_route_no_active_corpus(self, client, mock_rag_service_class):
        """Test RAG index route with no active corpus"""
        mock_corpus1 = Mock()
        mock_corpus1.name = "Test Corpus 1"

        # Configure mock instance
        mock_rag_instance = mock_rag_service_class.return_value
        mock_rag_instance.get_all_corpora.return_value = [mock_corpus1]
        mock_rag_instance.get_active_corpus.return_value = None

        response = client.get('/rag/')

        assert response.status_code == 200

        # Verify service calls
        mock_rag_instance.get_all_corpora.assert_called_once()
        mock_rag_instance.get_active_corpus.assert_called_once()
        # get_corpus_stats should not be called when no active corpus
        mock_rag_instance.get_corpus_stats.assert_not_called()

    def test_index_route_empty_corpora(self, client, mock_rag_service_class):
        """Test RAG index route with no corpora"""
        mock_rag_instance = mock_rag_service_class.return_value
        mock_rag_instance.get_all_corpora.return_value = []
        mock_rag_instance.get_active_corpus.return_value = None

        response = client.get('/rag/')

        assert response.status_code == 200
        mock_rag_instance.get_all_corpora.assert_called_once()
        mock_rag_instance.get_active_corpus.assert_called_once()

    def test_corpora_list_route(self, client, mock_rag_service_class):
        """Test corpora list route"""
        mock_corpus1 = Mock()
        mock_corpus1.name = "Family History Corpus"
        mock_corpus1.description = "Dutch family records"

        mock_corpus2 = Mock()
        mock_corpus2.name = "Genealogy Records"
        mock_corpus2.description = "Birth and death records"

        mock_rag_instance = mock_rag_service_class.return_value
        mock_rag_instance.get_all_corpora.return_value = [mock_corpus1, mock_corpus2]

        response = client.get('/rag/corpora')

        assert response.status_code == 200
        assert b'Family History Corpus' in response.data
        assert b'Genealogy Records' in response.data

        mock_rag_instance.get_all_corpora.assert_called_once()

    def test_corpora_list_route_empty(self, client, mock_rag_service_class):
        """Test corpora list route with no corpora"""
        mock_rag_instance = mock_rag_service_class.return_value
        mock_rag_instance.get_all_corpora.return_value = []

        response = client.get('/rag/corpora')

        assert response.status_code == 200
        mock_rag_instance.get_all_corpora.assert_called_once()

    @patch('web_app.blueprints.rag.QuerySession')
    def test_sessions_list_route(self, mock_query_session_class, client):
        """Test sessions list route"""
        # Mock session data
        mock_session1 = Mock()
        mock_session1.id = "session-1"
        mock_session1.name = "Test Session 1"
        mock_session1.created_at = "2025-01-01T10:00:00"

        mock_session2 = Mock()
        mock_session2.id = "session-2"
        mock_session2.name = "Test Session 2"
        mock_session2.created_at = "2025-01-02T11:00:00"

        # Configure mock query
        mock_query = Mock()
        mock_query.order_by.return_value.all.return_value = [mock_session1, mock_session2]
        mock_query_session_class.query = mock_query

        response = client.get('/rag/sessions')

        assert response.status_code == 200

        # Verify query was ordered by created_at desc
        mock_query.order_by.assert_called_once()
        mock_query.order_by.return_value.all.assert_called_once()

    @patch('web_app.blueprints.rag.QuerySession')
    def test_sessions_list_route_empty(self, mock_query_session_class, client):
        """Test sessions list route with no sessions"""
        mock_query = Mock()
        mock_query.order_by.return_value.all.return_value = []
        mock_query_session_class.query = mock_query

        response = client.get('/rag/sessions')

        assert response.status_code == 200
        mock_query.order_by.assert_called_once()

    @patch('web_app.blueprints.rag.QuerySession')
    def test_session_detail_route_exists(self, mock_query_session_class, client):
        """Test session detail route for existing session"""
        mock_session = Mock()
        mock_session.id = "session-123"
        mock_session.name = "Test Session"
        mock_session.queries = []

        mock_query_session_class.query.get_or_404.return_value = mock_session

        response = client.get('/rag/sessions/session-123')

        assert response.status_code == 200
        mock_query_session_class.query.get_or_404.assert_called_once_with("session-123")

    @patch('web_app.blueprints.rag.QuerySession')
    def test_session_detail_route_not_found(self, mock_query_session_class, client):
        """Test session detail route for non-existent session"""
        from werkzeug.exceptions import NotFound

        mock_query_session_class.query.get_or_404.side_effect = NotFound()

        response = client.get('/rag/sessions/nonexistent')

        assert response.status_code == 404
        mock_query_session_class.query.get_or_404.assert_called_once_with("nonexistent")

    def test_rag_service_error_handling_index(self, client, mock_rag_service_class):
        """Test error handling when rag service fails on index"""
        mock_rag_instance = mock_rag_service_class.return_value
        mock_rag_instance.get_all_corpora.side_effect = Exception("Service error")

        response = client.get('/rag/')

        # Should return 500 with proper error page
        assert response.status_code == 500
        assert b'Internal Server Error' in response.data

    def test_rag_service_error_handling_corpora(self, client, mock_rag_service_class):
        """Test error handling when rag service fails on corpora list"""
        mock_rag_instance = mock_rag_service_class.return_value
        mock_rag_instance.get_all_corpora.side_effect = Exception("Database error")

        response = client.get('/rag/corpora')

        assert response.status_code == 500
        assert b'Internal Server Error' in response.data

    def test_active_corpus_stats_error(self, client, mock_rag_service_class):
        """Test error handling when getting corpus stats fails"""
        mock_corpus = Mock()
        mock_corpus.id = "corpus-1"

        mock_rag_instance = mock_rag_service_class.return_value
        mock_rag_instance.get_all_corpora.return_value = [mock_corpus]
        mock_rag_instance.get_active_corpus.return_value = mock_corpus
        mock_rag_instance.get_corpus_stats.side_effect = Exception("Stats error")

        response = client.get('/rag/')

        # Should return 500 with proper error page
        assert response.status_code == 500
        assert b'Internal Server Error' in response.data

    @patch('web_app.blueprints.rag.QuerySession')
    def test_sessions_query_error(self, mock_query_session_class, client):
        """Test error handling when sessions query fails"""
        mock_query = Mock()
        mock_query.order_by.side_effect = Exception("Database error")
        mock_query_session_class.query = mock_query

        response = client.get('/rag/sessions')

        assert response.status_code == 500
        assert b'Internal Server Error' in response.data

    def test_route_methods_not_allowed(self, client):
        """Test that routes only accept GET requests"""
        # Test POST requests are not allowed
        response = client.post('/rag/')
        assert response.status_code == 405

        response = client.post('/rag/corpora')
        assert response.status_code == 405

        response = client.post('/rag/sessions')
        assert response.status_code == 405

        response = client.post('/rag/sessions/test-id')
        assert response.status_code == 405

    def test_active_corpus_with_complex_stats(self, client, mock_rag_service_class):
        """Test index route with complex corpus statistics"""
        mock_corpus = Mock()
        mock_corpus.id = "complex-corpus"
        mock_corpus.name = "Complex Corpus"

        complex_stats = {
            'total_chunks': 1500,
            'total_sources': 25,
            'avg_chunk_length': 768,
            'total_characters': 1152000,
            'languages': ['Dutch', 'English'],
            'created_at': '2025-01-01T00:00:00Z'
        }

        mock_rag_instance = mock_rag_service_class.return_value
        mock_rag_instance.get_all_corpora.return_value = [mock_corpus]
        mock_rag_instance.get_active_corpus.return_value = mock_corpus
        mock_rag_instance.get_corpus_stats.return_value = complex_stats

        response = client.get('/rag/')

        assert response.status_code == 200
        mock_rag_instance.get_corpus_stats.assert_called_once_with("complex-corpus")

    def test_corpus_id_conversion_to_string(self, client, mock_rag_service_class):
        """Test that corpus ID is properly converted to string for stats call"""
        mock_corpus = Mock()
        mock_corpus.id = 12345  # Integer ID

        mock_rag_instance = mock_rag_service_class.return_value
        mock_rag_instance.get_all_corpora.return_value = [mock_corpus]
        mock_rag_instance.get_active_corpus.return_value = mock_corpus
        mock_rag_instance.get_corpus_stats.return_value = {}

        response = client.get('/rag/')

        assert response.status_code == 200
        # Verify the ID was converted to string
        mock_rag_instance.get_corpus_stats.assert_called_once_with("12345")

    def test_submit_query_success(self, db, client, mock_rag_service_class):
        """Test successful query submission"""
        # Mock active corpus
        mock_corpus = Mock()
        mock_corpus.id = "corpus-123"
        
        # Mock query session
        mock_session = Mock()
        mock_session.id = "session-456"
        
        # Mock query result
        mock_query_result = Mock()
        mock_query_result.retrieved_sources = ["source1", "source2"]
        
        # Configure mocks
        mock_rag_instance = mock_rag_service_class.return_value
        mock_rag_instance.get_active_corpus.return_value = mock_corpus
        mock_rag_instance.create_query_session.return_value = mock_session
        mock_rag_instance.generate_rag_response.return_value = mock_query_result
        
        # Submit query
        response = client.post('/rag/submit-query', data={
            'question': 'What is genealogy?',
            'session_name': 'Test Session'
        })
        
        # Should redirect to session detail
        assert response.status_code == 302
        assert '/rag/sessions/session-456' in response.location
        
        # Verify service calls
        mock_rag_instance.get_active_corpus.assert_called_once()
        mock_rag_instance.create_query_session.assert_called_once_with("corpus-123", "Test Session")
        mock_rag_instance.generate_rag_response.assert_called_once_with("What is genealogy?", "session-456")

    def test_submit_query_no_question(self, db, client):
        """Test query submission without question"""
        response = client.post('/rag/submit-query', data={
            'session_name': 'Test Session'
        })
        
        # Should redirect to index with error
        assert response.status_code == 302
        assert '/rag/' in response.location

    def test_submit_query_no_active_corpus(self, db, client, mock_rag_service_class):
        """Test query submission when no active corpus exists"""
        # Mock no active corpus
        mock_rag_instance = mock_rag_service_class.return_value
        mock_rag_instance.get_active_corpus.return_value = None
        
        response = client.post('/rag/submit-query', data={
            'question': 'What is genealogy?'
        })
        
        # Should redirect to index with error
        assert response.status_code == 302
        assert '/rag/' in response.location

    def test_submit_query_error_handling(self, db, client, mock_rag_service_class):
        """Test error handling in query submission"""
        from web_app.services.exceptions import ValidationError, NotFoundError, ConnectionError, TimeoutError, ExternalServiceError, DatabaseError
        
        # Mock active corpus
        mock_corpus = Mock()
        mock_corpus.id = "corpus-123"
        mock_rag_instance = mock_rag_service_class.return_value
        mock_rag_instance.get_active_corpus.return_value = mock_corpus
        
        # Test ValidationError
        mock_rag_instance.create_query_session.side_effect = ValidationError("Invalid input")
        response = client.post('/rag/submit-query', data={'question': 'test'})
        assert response.status_code == 302
        assert '/rag/' in response.location
        
        # Test NotFoundError
        mock_rag_instance.create_query_session.side_effect = NotFoundError("Not found")
        response = client.post('/rag/submit-query', data={'question': 'test'})
        assert response.status_code == 302
        assert '/rag/' in response.location
        
        # Test ConnectionError
        mock_rag_instance.create_query_session.side_effect = ConnectionError("Connection failed")
        response = client.post('/rag/submit-query', data={'question': 'test'})
        assert response.status_code == 302
        assert '/rag/' in response.location
        
        # Test TimeoutError
        mock_rag_instance.create_query_session.side_effect = TimeoutError("Timeout")
        response = client.post('/rag/submit-query', data={'question': 'test'})
        assert response.status_code == 302
        assert '/rag/' in response.location
        
        # Test ExternalServiceError
        mock_rag_instance.create_query_session.side_effect = ExternalServiceError("Service error")
        response = client.post('/rag/submit-query', data={'question': 'test'})
        assert response.status_code == 302
        assert '/rag/' in response.location
        
        # Test DatabaseError
        mock_rag_instance.create_query_session.side_effect = DatabaseError("DB error")
        response = client.post('/rag/submit-query', data={'question': 'test'})
        assert response.status_code == 302
        assert '/rag/' in response.location

    def test_get_or_create_session_helper(self, db, mock_rag_service_class):
        """Test the _get_or_create_session helper function"""
        import uuid
        from web_app.blueprints.rag import _get_or_create_session
        from web_app.database.models import QuerySession
        
        # Use a valid UUID for corpus_id
        corpus_uuid = str(uuid.uuid4())
        
        # Create a test session in the database
        existing_session = QuerySession(session_name="Existing Session", corpus_id=corpus_uuid)
        db.session.add(existing_session)
        db.session.commit()
        
        rag_service = mock_rag_service_class.return_value
        
        # Test getting existing session
        result = _get_or_create_session(rag_service, corpus_uuid, "Existing Session")
        assert result.session_name == "Existing Session"
        rag_service.create_query_session.assert_not_called()
        
        # Test creating new session
        new_session = Mock()
        new_session.session_name = "New Session"
        rag_service.create_query_session.return_value = new_session
        
        result = _get_or_create_session(rag_service, corpus_uuid, "New Session")
        assert result == new_session
        rag_service.create_query_session.assert_called_once_with(corpus_uuid, "New Session")

    def test_blueprint_url_prefix(self, db, client):
        """Test that all routes have correct /rag prefix"""
        # Test that routes without /rag prefix return 404
        response = client.get('/')
        assert response.status_code == 200  # This should hit main blueprint

        response = client.get('/corpora')
        assert response.status_code == 404  # This should not exist

        response = client.get('/sessions')
        assert response.status_code == 404  # This should not exist
