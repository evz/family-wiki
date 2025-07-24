"""
Service for RAG (Retrieval-Augmented Generation) queries and source text management
"""

import hashlib
import uuid
from pathlib import Path

import requests
from flask import current_app

from web_app.database import db
from web_app.database.models import Query, QuerySession, SourceText, TextCorpus
from web_app.services.exceptions import (
    ExternalServiceError,
    NotFoundError,
    handle_service_exceptions,
)
from web_app.shared.logging_config import get_project_logger


logger = get_project_logger(__name__)


class RAGService:
    """Service for managing source text and RAG queries"""

    def __init__(self):
        self.logger = get_project_logger(__name__)

    @handle_service_exceptions(logger)
    def create_corpus(self, name: str, description: str = "") -> TextCorpus:
        """Create a new text corpus"""
        corpus = TextCorpus(
            name=name,
            description=description,
            is_active=True
        )
        db.session.add(corpus)
        db.session.commit()
        self.logger.info(f"Created corpus: {name}")
        return corpus

    @handle_service_exceptions(logger)
    def get_active_corpus(self) -> TextCorpus | None:
        """Get the currently active corpus"""
        return TextCorpus.query.filter_by(is_active=True).first()

    @handle_service_exceptions(logger)
    def get_all_corpora(self) -> list[TextCorpus]:
        """Get all text corpora"""
        return TextCorpus.query.order_by(TextCorpus.created_at.desc()).all()

    @handle_service_exceptions(logger)
    def chunk_text(self, text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> list[str]:
        """Split text into overlapping chunks"""
        chunks = []
        start = 0

        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]

            # Try to break at sentence boundaries
            if end < len(text) and '.' in chunk:
                last_period = chunk.rfind('.')
                if last_period > chunk_size // 2:  # Only if period is in latter half
                    end = start + last_period + 1
                    chunk = text[start:end]

            chunks.append(chunk.strip())
            start = end - chunk_overlap

            if start >= len(text):
                break

        return chunks

    @handle_service_exceptions(logger)
    def generate_embedding(self, text: str) -> list[float] | None:
        """Generate embedding for text using Ollama"""
        ollama_host = current_app.config.get('OLLAMA_HOST', '192.168.1.234')
        ollama_port = current_app.config.get('OLLAMA_PORT', 11434)
        ollama_base_url = f"http://{ollama_host}:{ollama_port}"

        response = requests.post(
            f"{ollama_base_url}/api/embeddings",
            json={
                "model": "nomic-embed-text",  # Good embedding model
                "prompt": text
            },
            timeout=30
        )

        if response.status_code == 200:
            return response.json().get('embedding')
        else:
            raise ExternalServiceError(f"Embedding generation failed with status {response.status_code}")

    @handle_service_exceptions(logger)
    def store_source_text(self, corpus_id: str, filename: str, content: str, page_number: int = None) -> int:
        """Store source text with chunking and embeddings"""
        # Convert string UUID to UUID object if needed
        if isinstance(corpus_id, str):
            corpus_id = uuid.UUID(corpus_id)

        corpus = TextCorpus.query.get(corpus_id)
        if not corpus:
            raise NotFoundError(f"Corpus not found: {corpus_id}")

        # Generate content hash for deduplication
        content_hash = hashlib.sha256(content.encode()).hexdigest()

        # Check if this content already exists
        existing = SourceText.query.filter_by(
            corpus_id=corpus_id,
            content_hash=content_hash
        ).first()

        if existing:
            self.logger.info(f"Content already exists for {filename}:{page_number}")
            return 0

        # Chunk the text
        chunks = self.chunk_text(content, corpus.chunk_size, corpus.chunk_overlap)
        stored_count = 0

        for i, chunk in enumerate(chunks):
            if not chunk.strip():
                continue

            # Generate embedding
            embedding = self.generate_embedding(chunk)
            if not embedding:
                self.logger.warning(f"Failed to generate embedding for chunk {i} of {filename}")
                continue

            # Create source text record
            source_text = SourceText(
                corpus_id=corpus_id,
                filename=filename,
                page_number=page_number,
                chunk_number=i,
                content=chunk,
                content_hash=content_hash,
                embedding=embedding,
                embedding_model="nomic-embed-text",
                token_count=len(chunk.split())
            )

            db.session.add(source_text)
            stored_count += 1

        db.session.commit()
        self.logger.info(f"Stored {stored_count} chunks for {filename}:{page_number}")
        return stored_count

    @handle_service_exceptions(logger)
    def load_pdf_text_files(self, corpus_id: str) -> dict:
        """Load all extracted text files from PDF processing"""
        text_dir = Path("web_app/pdf_processing/extracted_text")
        if not text_dir.exists():
            raise NotFoundError('Extracted text directory not found')

        total_files = 0
        total_chunks = 0

        # Process all .txt files in the directory
        for txt_file in text_dir.glob("*.txt"):
            if txt_file.name == "consolidated_text.txt":
                continue  # Skip consolidated file

            with open(txt_file, encoding='utf-8') as f:
                content = f.read()

            # Extract page number from filename (e.g., "page_001.txt" -> 1)
            page_number = None
            if txt_file.stem.startswith('page_'):
                try:
                    page_number = int(txt_file.stem.split('_')[1])
                except (IndexError, ValueError):
                    pass

            chunks_stored = self.store_source_text(
                corpus_id=corpus_id,
                filename=txt_file.name,
                content=content,
                page_number=page_number
            )

            total_files += 1
            total_chunks += chunks_stored

        return {
            'success': True,
            'files_processed': total_files,
            'chunks_stored': total_chunks
        }

    @handle_service_exceptions(logger)
    def create_query_session(self, corpus_id: str, session_name: str = None) -> QuerySession:
        """Create a new query session"""
        # Convert string UUID to UUID object if needed
        if isinstance(corpus_id, str):
            corpus_id = uuid.UUID(corpus_id)

        session = QuerySession(
            corpus_id=corpus_id,
            session_name=session_name or f"Session {QuerySession.query.count() + 1}"
        )
        db.session.add(session)
        db.session.commit()
        return session

    @handle_service_exceptions(logger)
    def semantic_search(self, query_text: str, corpus_id: str = None, limit: int = 5) -> list[tuple[SourceText, float]]:
        """Perform semantic search on source text"""
        # Generate embedding for query
        query_embedding = self.generate_embedding(query_text)
        if not query_embedding:
            raise ExternalServiceError("Failed to generate query embedding")

        # Use active corpus if none specified
        if not corpus_id:
            corpus = self.get_active_corpus()
            if not corpus:
                raise NotFoundError("No active corpus available for search")
            corpus_id = corpus.id
        elif isinstance(corpus_id, str):
            # Convert string UUID to UUID object if needed
            corpus_id = uuid.UUID(corpus_id)

        # Search for similar chunks
        results = SourceText.find_similar(
            query_embedding=query_embedding,
            corpus_id=corpus_id,
            limit=limit,
            similarity_threshold=0.7
        )

        return results

    @handle_service_exceptions(logger)
    def generate_rag_response(self, question: str, session_id: str) -> Query:
        """Generate a response using RAG (Retrieval-Augmented Generation)"""
        # Convert string UUID to UUID object if needed
        if isinstance(session_id, str):
            session_id = uuid.UUID(session_id)

        session = QuerySession.query.get(session_id)
        if not session:
            raise NotFoundError(f"Session not found: {session_id}")

        # Create query record
        query = Query(
            session_id=session_id,
            question=question,
            status='processing'
        )
        db.session.add(query)
        db.session.flush()  # Get the ID

        # Generate query embedding
        query_embedding = self.generate_embedding(question)
        if query_embedding:
            query.question_embedding = query_embedding

        # Perform semantic search
        search_results = self.semantic_search(
            query_text=question,
            corpus_id=session.corpus_id,
            limit=session.max_chunks
        )

        if not search_results:
            query.status = 'completed'
            query.answer = "I couldn't find relevant information in the source documents to answer your question."
            db.session.commit()
            return query

        # Prepare context from search results
        context_chunks = []
        chunk_ids = []
        similarity_scores = []

        for chunk, similarity in search_results:
            context_chunks.append(f"Source: {chunk.filename}:{chunk.page_number}\n{chunk.content}")
            chunk_ids.append(str(chunk.id))
            similarity_scores.append(similarity)

        context = "\n\n---\n\n".join(context_chunks)

        # Create RAG prompt
        rag_prompt = f"""Based on the following source documents, please answer the question. If the information is not in the sources, say so.

QUESTION: {question}

SOURCES:
{context}

ANSWER:"""

        # Generate response using Ollama
        ollama_host = current_app.config.get('OLLAMA_HOST', '192.168.1.234')
        ollama_port = current_app.config.get('OLLAMA_PORT', 11434)
        ollama_model = current_app.config.get('OLLAMA_MODEL', 'aya:35b-23')
        ollama_base_url = f"http://{ollama_host}:{ollama_port}"

        response = requests.post(
            f"{ollama_base_url}/api/generate",
            json={
                "model": ollama_model,
                "prompt": rag_prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3,
                    "top_p": 0.9
                }
            },
            timeout=120
        )

        if response.status_code == 200:
            answer = response.json().get('response', 'No response generated')
            query.answer = answer
            query.status = 'completed'
            query.ollama_model = ollama_model
            query.retrieved_chunks = chunk_ids
            query.similarity_scores = similarity_scores
        else:
            raise ExternalServiceError(f"LLM request failed with status {response.status_code}")

        db.session.commit()
        return query

    @handle_service_exceptions(logger)
    def get_corpus_stats(self, corpus_id: str) -> dict:
        """Get statistics for a corpus"""
        # Convert string UUID to UUID object if needed
        if isinstance(corpus_id, str):
            corpus_id = uuid.UUID(corpus_id)

        corpus = TextCorpus.query.get(corpus_id)
        if not corpus:
            raise NotFoundError(f"Corpus not found: {corpus_id}")

        chunk_count = SourceText.query.filter_by(corpus_id=corpus_id).count()
        unique_files = db.session.query(SourceText.filename).filter_by(corpus_id=corpus_id).distinct().count()

        return {
            'corpus_name': corpus.name,
            'chunk_count': chunk_count,
            'unique_files': unique_files,
            'embedding_model': corpus.embedding_model
        }


