"""
Tests for RAG API endpoints
"""

import json
from unittest.mock import Mock, patch

from web_app.database.models import QuerySession, TextCorpus


class TestRAGAPI:
    """Test RAG API endpoints"""

    def test_get_corpora_empty(self, client, app, db):
        """Test getting corpora when none exist"""
        with app.app_context():
            response = client.get('/api/rag/corpora')

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert data['corpora'] == []

    def test_get_corpora_with_data(self, client, app, db):
        """Test getting corpora with existing data"""
        with app.app_context():
            corpus = TextCorpus(
                name="Test Corpus",
                description="Test description",
                is_active=True
            )
            db.session.add(corpus)
            db.session.commit()

            response = client.get('/api/rag/corpora')

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert len(data['corpora']) == 1
            assert data['corpora'][0]['name'] == "Test Corpus"
            assert data['corpora'][0]['description'] == "Test description"
            assert data['corpora'][0]['is_active'] is True

    def test_create_corpus_success(self, client, app, db):
        """Test creating a new corpus"""
        with app.app_context():
            response = client.post('/api/rag/corpora',
                                 json={
                                     'name': 'New Corpus',
                                     'description': 'New description'
                                 })

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert data['corpus']['name'] == 'New Corpus'
            assert data['corpus']['description'] == 'New description'

            # Verify in database
            corpus = TextCorpus.query.filter_by(name='New Corpus').first()
            assert corpus is not None

    def test_create_corpus_missing_name(self, client, app, db):
        """Test creating corpus without name"""
        with app.app_context():
            response = client.post('/api/rag/corpora', json={})

            assert response.status_code == 400
            data = json.loads(response.data)
            assert data['success'] is False
            assert 'Name is required' in data['error']

    def test_create_corpus_no_json(self, client, app, db):
        """Test creating corpus without JSON data"""
        with app.app_context():
            response = client.post('/api/rag/corpora', json={})

            assert response.status_code == 400
            data = json.loads(response.data)
            assert data['success'] is False
            assert 'Name is required' in data['error']

    @patch('web_app.services.rag_service.rag_service.load_pdf_text_files')
    def test_load_pdf_text_success(self, mock_load, client, app, db):
        """Test loading PDF text files"""
        with app.app_context():
            corpus = TextCorpus(name="Test Corpus")
            db.session.add(corpus)
            db.session.commit()

            mock_load.return_value = {
                'success': True,
                'files_processed': 5,
                'chunks_stored': 25
            }

            response = client.post(f'/api/rag/corpora/{corpus.id}/load-pdf-text')

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert data['files_processed'] == 5
            assert data['chunks_stored'] == 25

    @patch('web_app.services.rag_service.rag_service.load_pdf_text_files')
    def test_load_pdf_text_failure(self, mock_load, client, app, db):
        """Test loading PDF text files failure"""
        with app.app_context():
            corpus = TextCorpus(name="Test Corpus")
            db.session.add(corpus)
            db.session.commit()

            mock_load.return_value = {
                'success': False,
                'error': 'Directory not found'
            }

            response = client.post(f'/api/rag/corpora/{corpus.id}/load-pdf-text')

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is False
            assert data['error'] == 'Directory not found'

    def test_create_rag_session_with_corpus(self, client, app, db):
        """Test creating RAG session with specified corpus"""
        with app.app_context():
            corpus = TextCorpus(name="Test Corpus")
            db.session.add(corpus)
            db.session.commit()

            response = client.post('/api/rag/sessions',
                                 json={
                                     'corpus_id': str(corpus.id),
                                     'session_name': 'Test Session'
                                 })

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert data['session']['name'] == 'Test Session'
            assert data['session']['corpus_id'] == str(corpus.id)

    def test_create_rag_session_with_active_corpus(self, client, app, db):
        """Test creating RAG session using active corpus"""
        with app.app_context():
            corpus = TextCorpus(name="Test Corpus", is_active=True)
            db.session.add(corpus)
            db.session.commit()

            response = client.post('/api/rag/sessions',
                                 json={'session_name': 'Test Session'})

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert data['session']['corpus_id'] == str(corpus.id)

    def test_create_rag_session_no_active_corpus(self, client, app, db):
        """Test creating RAG session with no active corpus"""
        with app.app_context():
            response = client.post('/api/rag/sessions',
                                 json={'session_name': 'Test Session'})

            assert response.status_code == 400
            data = json.loads(response.data)
            assert data['success'] is False
            assert 'No active corpus found' in data['error']

    @patch('web_app.services.rag_service.rag_service.semantic_search')
    def test_semantic_search_success(self, mock_search, client, app, db):
        """Test semantic search API"""
        with app.app_context():
            corpus = TextCorpus(name="Test Corpus")
            db.session.add(corpus)
            db.session.commit()

            # Mock search results
            mock_chunk = Mock()
            mock_chunk.id = "chunk-id"
            mock_chunk.filename = "test.txt"
            mock_chunk.page_number = 1
            mock_chunk.chunk_number = 0
            mock_chunk.content = "This is test content about genealogy"
            mock_search.return_value = [(mock_chunk, 0.85)]

            response = client.post('/api/rag/search',
                                 json={
                                     'query': 'genealogy',
                                     'corpus_id': str(corpus.id),
                                     'limit': 5
                                 })

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert len(data['results']) == 1
            assert data['results'][0]['filename'] == 'test.txt'
            assert data['results'][0]['similarity'] == 0.85

    def test_semantic_search_missing_query(self, client, app, db):
        """Test semantic search without query text"""
        with app.app_context():
            response = client.post('/api/rag/search', json={})

            assert response.status_code == 400
            data = json.loads(response.data)
            assert data['success'] is False
            assert 'Query text is required' in data['error']

    @patch('web_app.services.rag_service.rag_service.generate_rag_response')
    def test_rag_query_success(self, mock_generate, client, app, db):
        """Test RAG query API"""
        with app.app_context():
            corpus = TextCorpus(name="Test Corpus")
            db.session.add(corpus)
            db.session.commit()  # Commit corpus first to get ID

            session = QuerySession(corpus_id=corpus.id, session_name="Test Session")
            db.session.add(session)
            db.session.commit()

            # Mock RAG response
            mock_query = Mock()
            mock_query.id = "query-id"
            mock_query.question = "What is this about?"
            mock_query.answer = "This is about genealogy"
            mock_query.status = "completed"
            mock_query.error_message = None
            mock_query.retrieved_chunks = ["chunk-id"]
            mock_query.similarity_scores = [0.85]
            mock_generate.return_value = mock_query

            response = client.post('/api/rag/query',
                                 json={
                                     'question': 'What is this about?',
                                     'session_id': str(session.id)
                                 })

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert data['query']['question'] == 'What is this about?'
            assert data['query']['answer'] == 'This is about genealogy'
            assert data['query']['status'] == 'completed'

    def test_rag_query_missing_question(self, client, app, db):
        """Test RAG query without question"""
        with app.app_context():
            response = client.post('/api/rag/query',
                                 json={'session_id': 'session-id'})

            assert response.status_code == 400
            data = json.loads(response.data)
            assert data['success'] is False
            assert 'Question is required' in data['error']

    def test_rag_query_missing_session(self, client, app, db):
        """Test RAG query without session ID"""
        with app.app_context():
            response = client.post('/api/rag/query',
                                 json={'question': 'What is this?'})

            assert response.status_code == 400
            data = json.loads(response.data)
            assert data['success'] is False
            assert 'Session ID is required' in data['error']

    @patch('web_app.services.rag_service.rag_service.get_corpus_stats')
    def test_get_corpus_stats(self, mock_stats, client, app, db):
        """Test getting corpus statistics"""
        with app.app_context():
            corpus = TextCorpus(name="Test Corpus")
            db.session.add(corpus)
            db.session.commit()

            mock_stats.return_value = {
                'corpus_name': 'Test Corpus',
                'chunk_count': 100,
                'unique_files': 10,
                'embedding_model': 'nomic-embed-text'
            }

            response = client.get(f'/api/rag/corpora/{corpus.id}/stats')

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert data['stats']['corpus_name'] == 'Test Corpus'
            assert data['stats']['chunk_count'] == 100
