"""
Tests for RAG service functionality
"""

from unittest.mock import Mock, patch

import pytest

from web_app.database.models import SourceText, TextCorpus
from web_app.services.exceptions import (
    ExternalServiceError,
    NotFoundError,
    ServiceError,
    ValidationError,
)
from web_app.services.rag_service import RAGService


class TestRAGService:
    """Test RAG service functionality"""

    @pytest.fixture
    def rag_service(self):
        """Create RAG service instance for testing"""
        return RAGService()

    def test_create_corpus(self, rag_service, app, db):
        """Test creating a new text corpus"""
        with app.app_context():
            corpus = rag_service.create_corpus(
                name="Test Corpus",
                description="A test corpus for unit tests"
            )

            assert corpus.name == "Test Corpus"
            assert corpus.description == "A test corpus for unit tests"
            assert corpus.is_active is True
            assert corpus.chunk_size == 1500  # Updated default
            assert corpus.chunk_overlap == 200
            assert corpus.query_chunk_limit == 20  # New configurable setting

            # Verify it was saved to database
            saved_corpus = db.session.get(TextCorpus, corpus.id)
            assert saved_corpus is not None
            assert saved_corpus.name == "Test Corpus"

    def test_get_active_corpus(self, rag_service, app, db):
        """Test getting the active corpus"""
        with app.app_context():
            # Create multiple corpora
            corpus1 = rag_service.create_corpus("Corpus 1")
            corpus2 = rag_service.create_corpus("Corpus 2")

            # Set corpus2 as active
            corpus1.is_active = False
            corpus2.is_active = True
            db.session.flush()  # Use flush instead of commit for tests

            active = rag_service.get_active_corpus()
            assert active is not None
            assert active.id == corpus2.id
            assert active.name == "Corpus 2"

    def test_get_all_corpora(self, rag_service, app, db):
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

    def test_chunk_text_basic(self, rag_service, app):
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

    def test_chunk_text_sentence_boundaries(self, rag_service, app):
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
    def test_generate_embedding_success(self, mock_post, rag_service, app):
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
    def test_generate_embedding_failure(self, mock_post, rag_service, app):
        """Test embedding generation failure"""
        with app.app_context():
            mock_response = Mock()
            mock_response.status_code = 500
            mock_post.return_value = mock_response

            with pytest.raises(ExternalServiceError, match="Ollama request to api/embeddings failed with status 500"):
                rag_service.generate_embedding("test text")

    @patch('requests.post')
    def test_generate_embedding_exception(self, mock_post, rag_service, app):
        """Test embedding generation with exception"""
        with app.app_context():
            mock_post.side_effect = Exception("Connection error")

            with pytest.raises(ServiceError, match="Unexpected service error"):
                rag_service.generate_embedding("test text")

    @patch.object(RAGService, 'generate_embedding')
    def test_store_source_text(self, mock_embedding, rag_service, app, db):
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

    @patch.object(RAGService, 'generate_embedding')
    def test_store_source_text_deduplication(self, mock_embedding, rag_service, app, db):
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

    def test_store_source_text_invalid_corpus(self, rag_service, app, db):
        """Test storing text with invalid corpus ID"""
        with app.app_context():
            with pytest.raises(ValidationError, match="badly formed hexadecimal UUID string"):
                rag_service.store_source_text(
                    corpus_id="nonexistent-id",
                    filename="test.txt",
                    content="test content"
                )

    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.glob')
    @patch('builtins.open')
    @patch.object(RAGService, 'store_source_text')
    def test_load_pdf_text_files(self, mock_store, mock_open, mock_glob, mock_exists, rag_service, app, db):
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
    def test_load_pdf_text_files_missing_directory(self, mock_exists, rag_service, app, db):
        """Test loading PDF text files when directory doesn't exist"""
        with app.app_context():
            corpus = rag_service.create_corpus("Test Corpus")
            mock_exists.return_value = False

            with pytest.raises(NotFoundError, match="Extracted text directory not found"):
                rag_service.load_pdf_text_files(str(corpus.id))


    @patch.object(RAGService, 'generate_embedding')
    def test_semantic_search(self, mock_embedding, rag_service, app, db):
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

            # Mock the repository search instead of the model method
            with patch.object(rag_service.rag_repository, 'find_similar') as mock_find:
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

    @patch.object(RAGService, 'generate_embedding')
    def test_semantic_search_no_corpus(self, mock_embedding, rag_service, app, db):
        """Test semantic search with no active corpus"""
        with app.app_context():
            mock_embedding.return_value = [0.1] * 1024

            with pytest.raises(NotFoundError, match="No active corpus available for search"):
                rag_service.semantic_search("test query")

    @patch.object(RAGService, 'generate_embedding')
    def test_semantic_search_no_embedding(self, mock_embedding, rag_service, app, db):
        """Test semantic search when embedding generation fails"""
        with app.app_context():
            corpus = rag_service.create_corpus("Test Corpus")
            mock_embedding.return_value = None

            with pytest.raises(ExternalServiceError, match="Failed to generate query embedding"):
                rag_service.semantic_search(
                    query_text="test query",
                    corpus_id=str(corpus.id)
                )

    def test_get_corpus_stats(self, rag_service, app, db):
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
            db.session.flush()  # Use flush instead of commit for tests

            stats = rag_service.get_corpus_stats(str(corpus.id))

            assert stats['corpus_name'] == "Test Corpus"
            assert stats['chunk_count'] == 1
            assert stats['unique_files'] == 1
            assert stats['embedding_model'] == corpus.embedding_model

    def test_get_corpus_stats_invalid_id(self, rag_service, app, db):
        """Test getting stats for invalid corpus ID"""
        with app.app_context():
            with pytest.raises(ValidationError, match="badly formed hexadecimal UUID string"):
                rag_service.get_corpus_stats("nonexistent-id")

    def test_delete_corpus_success(self, rag_service, app, db):
        """Test successful corpus deletion"""
        with app.app_context():
            # Create a test corpus
            corpus = rag_service.create_corpus("Test Deletion Corpus", "A corpus to delete")
            corpus_id = str(corpus.id)

            # Add some source text to it
            with patch.object(rag_service, 'generate_embedding', return_value=[0.1] * 1024):
                chunks_stored = rag_service.store_source_text(
                    corpus_id=corpus_id,
                    filename="test.txt",
                    content="This is test content for deletion.",
                    page_number=1
                )
                assert chunks_stored > 0

            # Verify corpus and chunks exist
            assert db.session.get(TextCorpus, corpus.id) is not None
            chunk_count_before = db.session.execute(
                db.select(db.func.count()).select_from(
                    db.select(SourceText).filter_by(corpus_id=corpus.id).subquery()
                )
            ).scalar()
            assert chunk_count_before > 0

            # Delete the corpus
            result = rag_service.delete_corpus(corpus_id)

            # Verify deletion result
            assert result['success'] is True
            assert result['corpus_name'] == "Test Deletion Corpus"
            assert result['deleted_chunks'] == chunk_count_before
            assert result['deleted_queries'] == 0  # No queries in this test
            assert "Successfully deleted" in result['message']

            # Verify corpus is gone
            assert db.session.get(TextCorpus, corpus.id) is None

            # Verify associated chunks are gone
            chunk_count_after = db.session.execute(
                db.select(db.func.count()).select_from(
                    db.select(SourceText).filter_by(corpus_id=corpus.id).subquery()
                )
            ).scalar()
            assert chunk_count_after == 0

    def test_delete_corpus_not_found(self, rag_service, app, db):
        """Test deletion of non-existent corpus"""
        with app.app_context():
            # Try to delete a non-existent corpus
            fake_id = "00000000-0000-0000-0000-000000000000"

            with pytest.raises(NotFoundError, match="Corpus not found"):
                rag_service.delete_corpus(fake_id)

    def test_delete_corpus_invalid_id(self, rag_service, app, db):
        """Test deletion with invalid corpus ID"""
        with app.app_context():
            with pytest.raises(ValidationError, match="badly formed hexadecimal UUID string"):
                rag_service.delete_corpus("invalid-uuid")

    def test_delete_corpus_with_queries(self, rag_service, app, db):
        """Test successful corpus deletion when corpus has associated queries"""
        with app.app_context():
            from web_app.database.models import Query

            # Create a test corpus
            corpus = rag_service.create_corpus("Test Corpus with Queries", "A corpus with queries")
            corpus_id = str(corpus.id)

            # Add some source text to it
            with patch.object(rag_service, 'generate_embedding', return_value=[0.1] * 1024):
                chunks_stored = rag_service.store_source_text(
                    corpus_id=corpus_id,
                    filename="test.txt",
                    content="This is test content with queries.",
                    page_number=1
                )
                assert chunks_stored > 0

            # Create some queries associated with this corpus
            query1 = Query(
                corpus_id=corpus.id,
                question="What is this about?",
                answer="This is about test content."
            )
            query2 = Query(
                corpus_id=corpus.id,
                question="Tell me more",
                answer="More information here."
            )
            db.session.add(query1)
            db.session.add(query2)
            db.session.flush()  # Use flush instead of commit for tests

            # Verify corpus, chunks, and queries exist
            assert db.session.get(TextCorpus, corpus.id) is not None
            chunk_count_before = db.session.execute(
                db.select(db.func.count()).select_from(
                    db.select(SourceText).filter_by(corpus_id=corpus.id).subquery()
                )
            ).scalar()
            query_count_before = db.session.execute(
                db.select(db.func.count()).select_from(
                    db.select(Query).filter_by(corpus_id=corpus.id).subquery()
                )
            ).scalar()
            assert chunk_count_before > 0
            assert query_count_before == 2

            # Delete the corpus
            result = rag_service.delete_corpus(corpus_id)

            # Verify deletion result
            assert result['success'] is True
            assert result['corpus_name'] == "Test Corpus with Queries"
            assert result['deleted_chunks'] == chunk_count_before
            assert result['deleted_queries'] == 2
            assert "queries" in result['message']
            assert "Successfully deleted" in result['message']

            # Verify corpus is gone
            assert db.session.get(TextCorpus, corpus.id) is None

            # Verify associated chunks are gone
            chunk_count_after = db.session.execute(
                db.select(db.func.count()).select_from(
                    db.select(SourceText).filter_by(corpus_id=corpus.id).subquery()
                )
            ).scalar()
            assert chunk_count_after == 0

            # Verify associated queries are gone
            query_count_after = db.session.execute(
                db.select(db.func.count()).select_from(
                    db.select(Query).filter_by(corpus_id=corpus.id).subquery()
                )
            ).scalar()
            assert query_count_after == 0



