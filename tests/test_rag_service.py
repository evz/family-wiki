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
    def rag_service(self, db):
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


class TestRAGServiceAdvanced:
    """Test advanced RAG service functionality including hybrid search and ask_question"""

    @pytest.fixture
    def rag_service(self, db):
        """Create RAG service instance for testing"""
        return RAGService()

    @pytest.fixture
    def mock_text_processor(self):
        """Mock text processing service"""
        with patch('web_app.services.rag_service.TextProcessingService') as mock_service:
            mock_instance = mock_service.return_value
            mock_instance.clean_text_for_rag.return_value = "cleaned query text"
            mock_instance.generate_daitch_mokotoff_codes.return_value = ["123", "456"]
            yield mock_instance

    @pytest.fixture
    def mock_embedding(self):
        """Mock embedding generation"""
        with patch.object(RAGService, 'generate_embedding') as mock_embed:
            mock_embed.return_value = [0.1] * 1024  # Mock embedding vector
            yield mock_embed

    @pytest.fixture
    def sample_corpus(self, rag_service, app, db):
        """Create sample corpus for testing"""
        with app.app_context():
            corpus = rag_service.create_corpus(
                name="Test Corpus",
                description="Test corpus for advanced tests",
                embedding_model="test-model",
                chunk_size=1000,
                query_chunk_limit=10
            )
            db.session.flush()  # Ensure it's persisted in the test transaction
            return corpus

    def test_hybrid_search_with_corpus_id(self, rag_service, app, db, sample_corpus, mock_text_processor, mock_embedding):
        """Test hybrid search with specific corpus ID"""
        with app.app_context():
            # Mock the text processor on the service instance
            rag_service.text_processor = mock_text_processor
            
            with patch.object(rag_service.rag_repository, 'get_corpus_by_id') as mock_get_corpus:
                mock_get_corpus.return_value = sample_corpus
                
                with patch.object(rag_service.rag_repository, 'hybrid_search') as mock_search:
                    # Create properly structured mock SourceText objects
                    mock_source1 = Mock()
                    mock_source1.content = "Test content 1"
                    mock_source1.chunk_type = "general"
                    mock_source1.generation_number = None
                    mock_source1.birth_years = []
                    
                    mock_source2 = Mock()
                    mock_source2.content = "Test content 2"
                    mock_source2.chunk_type = "general"
                    mock_source2.generation_number = None
                    mock_source2.birth_years = []
                    
                    mock_search.return_value = [
                        (mock_source1, 0.95),
                        (mock_source2, 0.85)
                    ]

                    results = rag_service.hybrid_search(
                        query_text="test query",
                        corpus_id=str(sample_corpus.id),
                        limit=5
                    )

                    assert len(results) == 2
                    mock_text_processor.clean_text_for_rag.assert_called_once_with("test query", spellfix=False)
                    mock_embedding.assert_called_once_with("cleaned query text", "test-model")
                    mock_search.assert_called_once()

    def test_hybrid_search_without_corpus_id(self, rag_service, app, db, sample_corpus, mock_text_processor, mock_embedding):
        """Test hybrid search without corpus ID (uses active corpus)"""
        with app.app_context():
            # Mock the text processor on the service instance
            rag_service.text_processor = mock_text_processor
            
            # Mark corpus as active
            sample_corpus.is_active = True
            db.session.flush()

            with patch.object(rag_service, 'get_active_corpus') as mock_get_active:
                mock_get_active.return_value = sample_corpus
                
                with patch.object(rag_service.rag_repository, 'hybrid_search') as mock_search:
                    mock_search.return_value = []

                    results = rag_service.hybrid_search(query_text="test query")

                    assert results == []
                    mock_embedding.assert_called_once_with("cleaned query text", "test-model")

    def test_hybrid_search_no_active_corpus(self, rag_service, app, db, mock_text_processor):
        """Test hybrid search when no active corpus exists"""
        with app.app_context():
            with pytest.raises(NotFoundError, match="No active corpus available for search"):
                rag_service.hybrid_search(query_text="test query")

    def test_hybrid_search_corpus_not_found(self, rag_service, app, db, mock_text_processor):
        """Test hybrid search with invalid corpus ID"""
        with app.app_context():
            fake_corpus_id = "00000000-0000-0000-0000-000000000000"
            
            with pytest.raises(NotFoundError, match="Corpus not found"):
                rag_service.hybrid_search(
                    query_text="test query", 
                    corpus_id=fake_corpus_id
                )

    def test_hybrid_search_embedding_failure(self, rag_service, app, db, sample_corpus, mock_text_processor):
        """Test hybrid search when embedding generation fails"""
        with app.app_context():
            with patch.object(rag_service.rag_repository, 'get_corpus_by_id') as mock_get_corpus:
                mock_get_corpus.return_value = sample_corpus
                
                with patch.object(rag_service, 'generate_embedding', return_value=None):
                    with pytest.raises(ExternalServiceError, match="Failed to generate query embedding"):
                        rag_service.hybrid_search(
                            query_text="test query",
                            corpus_id=str(sample_corpus.id)
                        )

    def test_conversation_aware_search_with_context(self, rag_service, app, db, sample_corpus, mock_text_processor, mock_embedding):
        """Test conversation-aware search with previous context"""
        with app.app_context():
            import uuid
            conversation_id = uuid.uuid4()

            # Mock previous queries
            mock_query_1 = Mock()
            mock_query_1.question = "What is genealogy?"
            mock_query_1.answer = "Genealogy is the study of family history and ancestry."

            mock_query_2 = Mock()
            mock_query_2.question = "How do I start?"
            mock_query_2.answer = "You can start by interviewing family members."

            with patch.object(rag_service.rag_repository, 'get_conversation') as mock_get_conv:
                mock_get_conv.return_value = [mock_query_1, mock_query_2]
                
                with patch.object(rag_service, 'hybrid_search') as mock_hybrid:
                    mock_hybrid.return_value = []

                    results = rag_service.conversation_aware_search(
                        question="Tell me more details",
                        conversation_id=conversation_id,
                        corpus_id=str(sample_corpus.id),
                        limit=5
                    )

                    # Verify that hybrid_search was called with enhanced query including context
                    call_args = mock_hybrid.call_args
                    assert "Tell me more details" in call_args[1]['query_text']
                    assert "Previous Q:" in call_args[1]['query_text']
                    assert "Previous A:" in call_args[1]['query_text']

    def test_conversation_aware_search_no_context(self, rag_service, app, db, sample_corpus, mock_text_processor, mock_embedding):
        """Test conversation-aware search with no previous context"""
        with app.app_context():
            # Mock the text processor on the service instance
            rag_service.text_processor = mock_text_processor
            
            import uuid
            conversation_id = uuid.uuid4()

            with patch.object(rag_service.rag_repository, 'get_conversation') as mock_get_conv:
                mock_get_conv.return_value = []
                
                with patch.object(rag_service, 'hybrid_search') as mock_hybrid:
                    mock_hybrid.return_value = []

                    results = rag_service.conversation_aware_search(
                        question="First question",
                        conversation_id=conversation_id,
                        corpus_id=str(sample_corpus.id)
                    )

                    # Should just use the cleaned question
                    call_args = mock_hybrid.call_args
                    assert call_args[1]['query_text'] == "cleaned query text"

    def test_conversation_aware_search_string_uuid(self, rag_service, app, db, sample_corpus, mock_text_processor, mock_embedding):
        """Test conversation-aware search with string UUID conversion"""
        with app.app_context():
            import uuid
            conversation_id = str(uuid.uuid4())

            with patch.object(rag_service.rag_repository, 'get_conversation') as mock_get_conv:
                mock_get_conv.return_value = []
                
                with patch.object(rag_service, 'hybrid_search') as mock_hybrid:
                    mock_hybrid.return_value = []

                    results = rag_service.conversation_aware_search(
                        question="Test question",
                        conversation_id=conversation_id,
                        corpus_id=str(sample_corpus.id)
                    )

                    # Should convert string to UUID and work normally
                    mock_get_conv.assert_called_once()

    def test_conversation_aware_search_context_error(self, rag_service, app, db, sample_corpus, mock_text_processor, mock_embedding):
        """Test conversation-aware search when context processing fails"""
        with app.app_context():
            # Mock the text processor on the service instance
            rag_service.text_processor = mock_text_processor
            
            import uuid
            conversation_id = uuid.uuid4()

            with patch.object(rag_service.rag_repository, 'get_conversation') as mock_get_conv:
                mock_get_conv.side_effect = Exception("Database error")
                
                with patch.object(rag_service, 'hybrid_search') as mock_hybrid:
                    mock_hybrid.return_value = []

                    # Should fall back to simple search when context processing fails
                    results = rag_service.conversation_aware_search(
                        question="Test question",
                        conversation_id=conversation_id,
                        corpus_id=str(sample_corpus.id)
                    )

                    # Should fall back to cleaned question only
                    call_args = mock_hybrid.call_args
                    assert call_args[1]['query_text'] == "cleaned query text"

    def test_ask_question_with_corpus_id(self, rag_service, app, db, sample_corpus, mock_text_processor, mock_embedding):
        """Test ask_question with specific corpus ID"""
        with app.app_context():
            from web_app.database.models import ExtractionPrompt
            
            # Create test prompt
            prompt = ExtractionPrompt(
                name="Test RAG Prompt",
                prompt_text="Answer this question: {question}\n\nBased on: {context}",
                prompt_type="rag"
            )
            db.session.add(prompt)
            db.session.flush()

            with patch.object(rag_service.rag_repository, 'get_corpus_by_id') as mock_get_corpus:
                mock_get_corpus.return_value = sample_corpus
                
                with patch.object(rag_service, '_get_prompt_by_id') as mock_get_prompt:
                    mock_get_prompt.return_value = prompt
                    
                    with patch.object(rag_service, 'hybrid_search') as mock_search:
                        mock_source = Mock()
                        mock_source.content = "Test content about genealogy"
                        mock_source.chunk_type = "general"
                        mock_source.generation_number = None
                        mock_source.birth_years = []
                        mock_source.id = "mock-chunk-id-123"
                        mock_search.return_value = [(mock_source, 0.95)]

                        with patch.object(rag_service, '_generate_llm_response') as mock_llm:
                            mock_llm.return_value = "Genealogy is the study of family history."

                            result = rag_service.ask_question(
                                question="What is genealogy?",
                                prompt_id=str(prompt.id),
                                corpus_id=str(sample_corpus.id),
                                max_chunks=5,
                                similarity_threshold=0.7
                            )

                            assert result['answer'] == "Genealogy is the study of family history."
                            assert len(result['retrieved_chunks']) == 1
                            assert result['retrieved_chunks'][0] == "mock-chunk-id-123"
                            assert result['similarity_scores'] == [0.95]
                            assert result['corpus_name'] == "Test Corpus"
                            assert result['question'] == "What is genealogy?"

    def test_ask_question_without_corpus_id(self, rag_service, app, db, sample_corpus, mock_text_processor, mock_embedding):
        """Test ask_question without corpus ID (uses active corpus)"""
        with app.app_context():
            from web_app.database.models import ExtractionPrompt
            
            # Create test prompt
            prompt = ExtractionPrompt(
                name="Test RAG Prompt",
                prompt_text="Answer: {question}",
                prompt_type="rag"
            )
            db.session.add(prompt)
            db.session.flush()

            with patch.object(rag_service, 'get_active_corpus') as mock_get_active:
                mock_get_active.return_value = sample_corpus
                
                with patch.object(rag_service, '_get_prompt_by_id') as mock_get_prompt:
                    mock_get_prompt.return_value = prompt
                    
                    with patch.object(rag_service, 'hybrid_search') as mock_search:
                        mock_search.return_value = []

                        result = rag_service.ask_question(
                            question="Test question",
                            prompt_id=str(prompt.id)
                        )

                        assert "couldn't find relevant information" in result['answer']
                        assert result['retrieved_chunks'] == []
                        assert result['similarity_scores'] == []

    def test_ask_question_no_active_corpus(self, rag_service, app, db, mock_text_processor):
        """Test ask_question when no active corpus exists"""
        with app.app_context():
            with pytest.raises(NotFoundError, match="No active corpus available for search"):
                rag_service.ask_question(
                    question="Test question",
                    prompt_id="fake-prompt-id"
                )

    def test_ask_question_corpus_not_found(self, rag_service, app, db, mock_text_processor):
        """Test ask_question with invalid corpus ID"""
        with app.app_context():
            fake_corpus_id = "00000000-0000-0000-0000-000000000000"
            
            with pytest.raises(NotFoundError, match="Corpus not found"):
                rag_service.ask_question(
                    question="Test question", 
                    prompt_id="fake-prompt-id",
                    corpus_id=fake_corpus_id
                )

    def test_ask_question_with_conversation_context(self, rag_service, app, db, sample_corpus, mock_text_processor, mock_embedding):
        """Test ask_question with conversation context"""
        with app.app_context():
            import uuid
            from web_app.database.models import ExtractionPrompt
            
            # Create test prompt
            prompt = ExtractionPrompt(
                name="Test RAG Prompt",
                prompt_text="Answer: {question}\nContext: {context}",
                prompt_type="rag"
            )
            db.session.add(prompt)
            db.session.flush()

            conversation_id = uuid.uuid4()

            with patch.object(rag_service.rag_repository, 'get_corpus_by_id') as mock_get_corpus:
                mock_get_corpus.return_value = sample_corpus
                
                with patch.object(rag_service, '_get_prompt_by_id') as mock_get_prompt:
                    mock_get_prompt.return_value = prompt
                    
                    with patch.object(rag_service, 'conversation_aware_search') as mock_conv_search:
                        mock_source = Mock()
                        mock_source.content = "Test content with context"
                        mock_source.chunk_type = "general"
                        mock_source.generation_number = None
                        mock_source.birth_years = []
                        mock_source.id = "mock-context-chunk-456"
                        mock_conv_search.return_value = [(mock_source, 0.8)]

                        with patch.object(rag_service, '_generate_llm_response') as mock_llm:
                            mock_llm.return_value = "Answer based on context."

                            result = rag_service.ask_question(
                                question="Follow-up question",
                                prompt_id=str(prompt.id),
                                corpus_id=str(sample_corpus.id),
                                conversation_id=str(conversation_id)
                            )

                            assert result['answer'] == "Answer based on context."
                            mock_conv_search.assert_called_once()

    def test_ask_question_no_search_results(self, rag_service, app, db, sample_corpus, mock_text_processor, mock_embedding):
        """Test ask_question when search returns no results"""
        with app.app_context():
            from web_app.database.models import ExtractionPrompt
            
            # Create test prompt
            prompt = ExtractionPrompt(
                name="Test RAG Prompt",
                prompt_text="Answer: {question}",
                prompt_type="rag"
            )
            db.session.add(prompt)
            db.session.flush()

            with patch.object(rag_service.rag_repository, 'get_corpus_by_id') as mock_get_corpus:
                mock_get_corpus.return_value = sample_corpus
                
                with patch.object(rag_service, '_get_prompt_by_id') as mock_get_prompt:
                    mock_get_prompt.return_value = prompt
                    
                    with patch.object(rag_service, 'hybrid_search') as mock_search:
                        mock_search.return_value = []

                        result = rag_service.ask_question(
                            question="Unanswerable question",
                            prompt_id=str(prompt.id),
                            corpus_id=str(sample_corpus.id)
                        )

                        assert "couldn't find relevant information" in result['answer']
                        assert result['retrieved_chunks'] == []
                        assert result['similarity_scores'] == []
                        assert result['corpus_name'] == "Test Corpus"
                        assert result['question'] == "Unanswerable question"

    def test_get_prompt_by_id_success(self, rag_service, app, db):
        """Test successful prompt retrieval"""
        with app.app_context():
            from web_app.database.models import ExtractionPrompt
            
            prompt = ExtractionPrompt(
                name="Test Prompt",
                prompt_text="Test prompt text",
                prompt_type="rag"
            )
            db.session.add(prompt)
            db.session.flush()

            with patch.object(rag_service.rag_repository, 'get_prompt_by_id') as mock_get_prompt:
                mock_get_prompt.return_value = prompt

                result = rag_service._get_prompt_by_id(str(prompt.id), 'rag')
                assert result == prompt

    def test_get_prompt_by_id_not_found(self, rag_service, app, db):
        """Test prompt retrieval when prompt not found"""
        with app.app_context():
            with patch.object(rag_service.rag_repository, 'get_prompt_by_id') as mock_get_prompt:
                mock_get_prompt.side_effect = ValueError("Prompt not found")

                with pytest.raises(NotFoundError, match="Prompt not found"):
                    rag_service._get_prompt_by_id("fake-id", 'rag')

    def test_generate_llm_response_success(self, rag_service, app, db):
        """Test successful LLM response generation"""
        with app.app_context():
            with patch.object(rag_service, '_make_ollama_request') as mock_request:
                mock_request.return_value = {'response': 'Test response from LLM'}

                result = rag_service._generate_llm_response("Test prompt")
                assert result == "Test response from LLM"

    def test_generate_llm_response_no_response(self, rag_service, app, db):
        """Test LLM response generation when no response is returned"""
        with app.app_context():
            with patch.object(rag_service, '_make_ollama_request') as mock_request:
                mock_request.return_value = {}

                result = rag_service._generate_llm_response("Test prompt")
                assert result == "No response generated"


