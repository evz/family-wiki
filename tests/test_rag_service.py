"""
Tests for RAG service functionality
"""

from unittest.mock import Mock, patch

import pytest

from web_app.database.models import QuerySession, SourceText, TextCorpus
from web_app.services.rag_service import rag_service


class TestRAGService:
    """Test RAG service functionality"""

    def test_create_corpus(self, app, db):
        """Test creating a new text corpus"""
        with app.app_context():
            corpus = rag_service.create_corpus(
                name="Test Corpus",
                description="A test corpus for unit tests"
            )

            assert corpus.name == "Test Corpus"
            assert corpus.description == "A test corpus for unit tests"
            assert corpus.is_active is True
            assert corpus.chunk_size == 1000
            assert corpus.chunk_overlap == 200

            # Verify it was saved to database
            saved_corpus = TextCorpus.query.get(corpus.id)
            assert saved_corpus is not None
            assert saved_corpus.name == "Test Corpus"

    def test_get_active_corpus(self, app, db):
        """Test getting the active corpus"""
        with app.app_context():
            # Create multiple corpora
            corpus1 = rag_service.create_corpus("Corpus 1")
            corpus2 = rag_service.create_corpus("Corpus 2")

            # Set corpus2 as active
            corpus1.is_active = False
            corpus2.is_active = True
            db.session.commit()

            active = rag_service.get_active_corpus()
            assert active is not None
            assert active.id == corpus2.id
            assert active.name == "Corpus 2"

    def test_get_all_corpora(self, app, db):
        """Test getting all corpora"""
        with app.app_context():
            # Initially empty
            corpora = rag_service.get_all_corpora()
            assert len(corpora) == 0

            # Create some corpora
            _ = rag_service.create_corpus("Corpus 1")
            _ = rag_service.create_corpus("Corpus 2")

            corpora = rag_service.get_all_corpora()
            assert len(corpora) == 2
            corpus_names = [c.name for c in corpora]
            assert "Corpus 1" in corpus_names
            assert "Corpus 2" in corpus_names

    def test_chunk_text_basic(self, app):
        """Test basic text chunking"""
        with app.app_context():
            text = "This is a test. " * 100  # 1600 characters
            chunks = rag_service.chunk_text(text, chunk_size=500, chunk_overlap=100)

            assert len(chunks) > 1
            assert all(len(chunk) <= 500 for chunk in chunks)

            # Check overlap
            for i in range(len(chunks) - 1):
                # Should have some overlap
                assert chunks[i][-50:] in chunks[i+1] or chunks[i+1][:50] in chunks[i]

    def test_chunk_text_sentence_boundaries(self, app):
        """Test chunking respects sentence boundaries"""
        with app.app_context():
            text = "First sentence. Second sentence. Third sentence. Fourth sentence."
            chunks = rag_service.chunk_text(text, chunk_size=30, chunk_overlap=5)

            # Just verify that chunks are created and contain text
            assert len(chunks) > 0
            assert all(chunk.strip() for chunk in chunks)
            # All chunks combined should contain the original text
            combined = ' '.join(chunks)
            assert 'First sentence' in combined
            assert 'Fourth sentence' in combined

    @patch('requests.post')
    def test_generate_embedding_success(self, mock_post, app):
        """Test successful embedding generation"""
        with app.app_context():
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {'embedding': [0.1, 0.2, 0.3]}
            mock_post.return_value = mock_response

            embedding = rag_service.generate_embedding("test text")

            assert embedding == [0.1, 0.2, 0.3]
            mock_post.assert_called_once()

    @patch('requests.post')
    def test_generate_embedding_failure(self, mock_post, app):
        """Test embedding generation failure"""
        with app.app_context():
            mock_response = Mock()
            mock_response.status_code = 500
            mock_post.return_value = mock_response

            embedding = rag_service.generate_embedding("test text")

            assert embedding is None

    @patch('requests.post')
    def test_generate_embedding_exception(self, mock_post, app):
        """Test embedding generation with exception"""
        with app.app_context():
            mock_post.side_effect = Exception("Connection error")

            embedding = rag_service.generate_embedding("test text")

            assert embedding is None

    @patch.object(rag_service, 'generate_embedding')
    def test_store_source_text(self, mock_embedding, app, db):
        """Test storing source text with embeddings"""
        with app.app_context():
            # Setup
            corpus = rag_service.create_corpus("Test Corpus")
            mock_embedding.return_value = [0.1] * 1024  # Use correct dimension

            content = "This is test content. " * 50  # Long enough to chunk

            # Store the text
            chunks_stored = rag_service.store_source_text(
                corpus_id=str(corpus.id),
                filename="test.txt",
                content=content,
                page_number=1
            )

            assert chunks_stored > 0

            # Verify chunks were stored
            chunks = SourceText.query.filter_by(corpus_id=corpus.id).all()
            assert len(chunks) == chunks_stored

            for chunk in chunks:
                assert chunk.filename == "test.txt"
                assert chunk.page_number == 1
                assert chunk.content
                assert len(chunk.embedding) == 1024
                assert abs(chunk.embedding[0] - 0.1) < 0.01

    @patch.object(rag_service, 'generate_embedding')
    def test_store_source_text_deduplication(self, mock_embedding, app, db):
        """Test source text deduplication"""
        with app.app_context():
            corpus = rag_service.create_corpus("Test Corpus")
            mock_embedding.return_value = [0.1] * 1024

            content = "Same content"

            # Store same content twice
            chunks1 = rag_service.store_source_text(
                corpus_id=str(corpus.id),
                filename="test1.txt",
                content=content
            )

            chunks2 = rag_service.store_source_text(
                corpus_id=str(corpus.id),
                filename="test2.txt",
                content=content
            )

            # Second attempt should be deduplicated
            assert chunks1 > 0
            assert chunks2 == 0

    def test_store_source_text_invalid_corpus(self, app, db):
        """Test storing text with invalid corpus ID"""
        with app.app_context():
            with pytest.raises(ValueError, match="Corpus not found"):
                rag_service.store_source_text(
                    corpus_id="nonexistent-id",
                    filename="test.txt",
                    content="test content"
                )

    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.glob')
    @patch('builtins.open')
    @patch.object(rag_service, 'store_source_text')
    def test_load_pdf_text_files(self, mock_store, mock_open, mock_glob, mock_exists, app, db):
        """Test loading PDF text files"""
        with app.app_context():
            corpus = rag_service.create_corpus("Test Corpus")

            # Setup mocks
            mock_exists.return_value = True
            mock_file1 = Mock()
            mock_file1.name = "page_001.txt"
            mock_file1.stem = "page_001"
            mock_file2 = Mock()
            mock_file2.name = "page_002.txt"
            mock_file2.stem = "page_002"
            mock_glob.return_value = [mock_file1, mock_file2]

            mock_open.return_value.__enter__.return_value.read.return_value = "Test content"
            mock_store.return_value = 2  # 2 chunks per file

            # Load files
            result = rag_service.load_pdf_text_files(str(corpus.id))

            assert result['success'] is True
            assert result['files_processed'] == 2
            assert result['chunks_stored'] == 4

            # Verify store_source_text was called correctly
            assert mock_store.call_count == 2
            calls = mock_store.call_args_list
            assert calls[0][1]['filename'] == "page_001.txt"
            assert calls[0][1]['page_number'] == 1
            assert calls[1][1]['filename'] == "page_002.txt"
            assert calls[1][1]['page_number'] == 2

    @patch('pathlib.Path.exists')
    def test_load_pdf_text_files_missing_directory(self, mock_exists, app, db):
        """Test loading PDF text files when directory doesn't exist"""
        with app.app_context():
            corpus = rag_service.create_corpus("Test Corpus")
            mock_exists.return_value = False

            result = rag_service.load_pdf_text_files(str(corpus.id))

            assert result['success'] is False
            assert 'directory not found' in result['error']

    def test_create_query_session(self, app, db):
        """Test creating a query session"""
        with app.app_context():
            corpus = rag_service.create_corpus("Test Corpus")

            session = rag_service.create_query_session(
                corpus_id=str(corpus.id),
                session_name="Test Session"
            )

            assert session.session_name == "Test Session"
            assert session.corpus_id == corpus.id
            assert session.max_chunks == 5
            assert session.similarity_threshold == 0.7

            # Verify saved to database
            saved_session = QuerySession.query.get(session.id)
            assert saved_session is not None

    @patch.object(rag_service, 'generate_embedding')
    def test_semantic_search(self, mock_embedding, app, db):
        """Test semantic search functionality"""
        with app.app_context():
            corpus = rag_service.create_corpus("Test Corpus")
            mock_embedding.return_value = [0.1] * 1024

            # Store some source text
            rag_service.store_source_text(
                corpus_id=str(corpus.id),
                filename="test.txt",
                content="This is about genealogy and family history.",
                page_number=1
            )

            # Mock the database search
            with patch.object(SourceText, 'find_similar') as mock_find:
                mock_chunk = Mock()
                mock_chunk.id = "chunk-id"
                mock_chunk.content = "Test content"
                mock_find.return_value = [(mock_chunk, 0.85)]

                results = rag_service.semantic_search(
                    query_text="genealogy",
                    corpus_id=str(corpus.id),
                    limit=5
                )

                assert len(results) == 1
                assert results[0][0] == mock_chunk
                assert results[0][1] == 0.85

    @patch.object(rag_service, 'generate_embedding')
    def test_semantic_search_no_corpus(self, mock_embedding, app, db):
        """Test semantic search with no active corpus"""
        with app.app_context():
            mock_embedding.return_value = [0.1] * 1024

            results = rag_service.semantic_search("test query")

            assert len(results) == 0

    @patch.object(rag_service, 'generate_embedding')
    def test_semantic_search_no_embedding(self, mock_embedding, app, db):
        """Test semantic search when embedding generation fails"""
        with app.app_context():
            corpus = rag_service.create_corpus("Test Corpus")
            mock_embedding.return_value = None

            results = rag_service.semantic_search(
                query_text="test query",
                corpus_id=str(corpus.id)
            )

            assert len(results) == 0

    def test_get_corpus_stats(self, app, db):
        """Test getting corpus statistics"""
        with app.app_context():
            corpus = rag_service.create_corpus("Test Corpus")

            # Add some source text
            source_text = SourceText(
                corpus_id=corpus.id,
                filename="test.txt",
                content="Test content",
                chunk_number=0
            )
            db.session.add(source_text)
            db.session.commit()

            stats = rag_service.get_corpus_stats(str(corpus.id))

            assert stats['corpus_name'] == "Test Corpus"
            assert stats['chunk_count'] == 1
            assert stats['unique_files'] == 1
            assert stats['embedding_model'] == corpus.embedding_model

    def test_get_corpus_stats_invalid_id(self, app, db):
        """Test getting stats for invalid corpus ID"""
        with app.app_context():
            stats = rag_service.get_corpus_stats("nonexistent-id")

            assert stats == {}

    @patch.object(rag_service, 'semantic_search')
    @patch('requests.post')
    def test_generate_rag_response(self, mock_post, mock_search, app, db):
        """Test RAG response generation"""
        with app.app_context():
            corpus = rag_service.create_corpus("Test Corpus")
            session = rag_service.create_query_session(str(corpus.id), "Test Session")

            # Mock search results
            mock_chunk = Mock()
            mock_chunk.id = "chunk-id"
            mock_chunk.filename = "test.txt"
            mock_chunk.page_number = 1
            mock_chunk.content = "This is about genealogy."
            mock_search.return_value = [(mock_chunk, 0.85)]

            # Mock LLM response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'response': 'This is a genealogy document about family history.'
            }
            mock_post.return_value = mock_response

            # Generate response
            query = rag_service.generate_rag_response(
                question="What is this document about?",
                session_id=str(session.id)
            )

            assert query.question == "What is this document about?"
            assert query.answer == "This is a genealogy document about family history."
            assert query.status == "completed"
            assert query.retrieved_chunks == ["chunk-id"]
            assert query.similarity_scores == [0.85]

    @patch.object(rag_service, 'semantic_search')
    def test_generate_rag_response_no_results(self, mock_search, app, db):
        """Test RAG response when no search results found"""
        with app.app_context():
            corpus = rag_service.create_corpus("Test Corpus")
            session = rag_service.create_query_session(str(corpus.id), "Test Session")

            mock_search.return_value = []

            query = rag_service.generate_rag_response(
                question="What is this about?",
                session_id=str(session.id)
            )

            assert query.status == "completed"
            assert "couldn't find relevant information" in query.answer

    def test_generate_rag_response_invalid_session(self, app, db):
        """Test RAG response with invalid session ID"""
        with app.app_context():
            with pytest.raises(ValueError, match="Session not found"):
                rag_service.generate_rag_response(
                    question="Test question",
                    session_id="nonexistent-id"
                )
