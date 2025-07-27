"""
Service for RAG (Retrieval-Augmented Generation) queries and source text management
"""

import hashlib
import uuid
from pathlib import Path

import requests
from flask import current_app

from web_app.database import db
from web_app.database.models import ExtractionPrompt, SourceText, TextCorpus, Query
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

    def _get_ollama_config(self):
        """Get Ollama server configuration from Flask config"""
        return {
            'host': current_app.config.get('OLLAMA_HOST', '192.168.1.234'),
            'port': current_app.config.get('OLLAMA_PORT', 11434),
            'model': current_app.config.get('OLLAMA_MODEL', 'aya:35b-23'),
            'base_url': f"http://{current_app.config.get('OLLAMA_HOST', '192.168.1.234')}:{current_app.config.get('OLLAMA_PORT', 11434)}"
        }

    def _make_ollama_request(self, endpoint, payload, timeout=30):
        """Make a request to Ollama server with error handling"""
        config = self._get_ollama_config()
        url = f"{config['base_url']}/{endpoint}"

        try:
            response = requests.post(url, json=payload, timeout=timeout)
            if response.status_code == 200:
                return response.json()
            else:
                raise ExternalServiceError(f"Ollama request to {endpoint} failed with status {response.status_code}")
        except requests.RequestException as e:
            raise ExternalServiceError(f"Failed to connect to Ollama server: {str(e)}") from e

    def _get_prompt_by_id(self, prompt_id: str, expected_type: str = None) -> ExtractionPrompt:
        """Get a prompt by ID, optionally validate type"""
        if isinstance(prompt_id, str):
            try:
                prompt_id = uuid.UUID(prompt_id)
            except ValueError as e:
                raise NotFoundError(f"Invalid prompt ID format: {prompt_id}") from e

        prompt = db.session.get(ExtractionPrompt, prompt_id)
        if not prompt:
            raise NotFoundError(f"Prompt not found: {prompt_id}")

        if expected_type and prompt.prompt_type != expected_type:
            raise NotFoundError(f"Prompt {prompt_id} is type '{prompt.prompt_type}', expected '{expected_type}'")

        return prompt

    def _generate_llm_response(self, prompt: str, model: str = None, temperature: float = 0.3) -> str:
        """Generate a response from Ollama LLM"""
        config = self._get_ollama_config()
        model = model or config['model']

        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "top_p": 0.9
            }
        }

        response = self._make_ollama_request("api/generate", payload, timeout=120)
        return response.get('response', 'No response generated')

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
        return db.session.execute(
            db.select(TextCorpus).filter_by(is_active=True)
        ).scalar_one_or_none()

    @handle_service_exceptions(logger)
    def get_all_corpora(self) -> list[TextCorpus]:
        """Get all text corpora"""
        return db.session.execute(
            db.select(TextCorpus).order_by(TextCorpus.created_at.desc())
        ).scalars().all()

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
    def generate_embedding(self, text: str, embedding_model: str = "nomic-embed-text") -> list[float] | None:
        """Generate embedding for text using Ollama with specified model"""
        payload = {
            "model": embedding_model,
            "prompt": text
        }

        response = self._make_ollama_request("api/embeddings", payload, timeout=30)
        return response.get('embedding')

    @handle_service_exceptions(logger)
    def store_source_text(self, corpus_id: str, filename: str, content: str, page_number: int = None) -> int:
        """Store source text with chunking and embeddings"""
        # Convert string UUID to UUID object if needed
        if isinstance(corpus_id, str):
            corpus_id = uuid.UUID(corpus_id)

        corpus = db.session.get(TextCorpus, corpus_id)
        if not corpus:
            raise NotFoundError(f"Corpus not found: {corpus_id}")

        # Generate content hash for deduplication
        content_hash = hashlib.sha256(content.encode()).hexdigest()

        # Check if this content already exists
        existing = db.session.execute(
            db.select(SourceText).filter_by(
                corpus_id=corpus_id,
                content_hash=content_hash
            )
        ).scalar_one_or_none()

        if existing:
            self.logger.info(f"Content already exists for {filename}:{page_number}")
            return 0

        # Chunk the text
        chunks = self.chunk_text(content, corpus.chunk_size, corpus.chunk_overlap)
        stored_count = 0

        for i, chunk in enumerate(chunks):
            if not chunk.strip():
                continue

            # Generate embedding using corpus's embedding model
            embedding = self.generate_embedding(chunk, corpus.embedding_model)
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
                embedding_model=corpus.embedding_model,  # Use corpus's embedding model
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
    def semantic_search(self, query_text: str, corpus_id: str = None, limit: int = 5, similarity_threshold: float = 0.55) -> list[tuple[SourceText, float]]:
        """Perform semantic search on source text"""
        # Use active corpus if none specified, get corpus to determine embedding model
        if not corpus_id:
            corpus = self.get_active_corpus()
            if not corpus:
                raise NotFoundError("No active corpus available for search")
            corpus_id = corpus.id
        else:
            # Get corpus to determine embedding model
            if isinstance(corpus_id, str):
                corpus_id = uuid.UUID(corpus_id)
            corpus = db.session.get(TextCorpus, corpus_id)
            if not corpus:
                raise NotFoundError(f"Corpus not found: {corpus_id}")

        # Generate embedding for query using corpus's embedding model
        query_embedding = self.generate_embedding(query_text, corpus.embedding_model)
        if not query_embedding:
            raise ExternalServiceError("Failed to generate query embedding")

        # Ensure corpus_id is UUID object
        if isinstance(corpus_id, str):
            corpus_id = uuid.UUID(corpus_id)

        # Search for similar chunks
        results = SourceText.find_similar(
            query_embedding=query_embedding,
            corpus_id=corpus_id,
            limit=limit,
            similarity_threshold=similarity_threshold
        )

        return results

    @handle_service_exceptions(logger)
    def conversation_aware_search(self, question: str, conversation_id: str = None, corpus_id: str = None, limit: int = 5, similarity_threshold: float = 0.55) -> list[tuple[SourceText, float]]:
        """
        Perform semantic search with conversation context awareness
        
        Args:
            question: Current question to search for
            conversation_id: UUID of the conversation for context (optional)
            corpus_id: ID of corpus to search (uses active if None)
            limit: Maximum number of chunks to retrieve
            similarity_threshold: Minimum similarity threshold
            
        Returns:
            List of (SourceText, similarity_score) tuples
        """
        # Start with the current question
        search_query = question
        
        # Add conversation context if available
        if conversation_id:
            try:
                # Convert string UUID to UUID object if needed
                if isinstance(conversation_id, str):
                    conversation_id = uuid.UUID(conversation_id)
                
                # Get previous queries in this conversation
                previous_queries = Query.get_conversation(conversation_id)
                
                if previous_queries:
                    # Combine recent conversation context with current question
                    # Take last 2-3 questions/answers for context (to avoid overwhelming the search)
                    recent_context = []
                    for query in previous_queries[-3:]:  # Last 3 exchanges
                        if query.question:
                            recent_context.append(f"Previous Q: {query.question}")
                        if query.answer:
                            # Take first 100 chars of answer to avoid too much text
                            answer_preview = query.answer[:100] + "..." if len(query.answer) > 100 else query.answer
                            recent_context.append(f"Previous A: {answer_preview}")
                    
                    if recent_context:
                        # Combine context with current question, giving more weight to current question
                        context_text = " ".join(recent_context)
                        search_query = f"{question} Context: {context_text}"
                        
            except Exception as e:
                # If there's any issue with conversation context, fall back to simple search
                self.logger.warning(f"Error processing conversation context: {e}")
                search_query = question
        
        # Perform semantic search with the enhanced query
        return self.semantic_search(
            query_text=search_query,
            corpus_id=corpus_id,
            limit=limit,
            similarity_threshold=similarity_threshold
        )

    @handle_service_exceptions(logger)
    def ask_question(self, question: str, prompt_id: str, corpus_id: str = None, max_chunks: int = 5, similarity_threshold: float = 0.55, conversation_id: str = None) -> dict:
        """
        Enhanced RAG query with optional conversation awareness

        Args:
            question: The question to ask
            prompt_id: RAG prompt to use (required)
            corpus_id: ID of corpus to search (uses active if None)
            max_chunks: Maximum number of chunks to retrieve
            similarity_threshold: Minimum similarity threshold for search results
            conversation_id: UUID of conversation for context-aware search (optional)

        Returns:
            dict: Contains answer, retrieved_chunks, similarity_scores, and metadata
        """
        # Use active corpus if none specified
        if not corpus_id:
            corpus = self.get_active_corpus()
            if not corpus:
                raise NotFoundError("No active corpus available for search")
            corpus_id = corpus.id
        else:
            # Validate corpus exists
            if isinstance(corpus_id, str):
                corpus_id = uuid.UUID(corpus_id)
            corpus = db.session.get(TextCorpus, corpus_id)
            if not corpus:
                raise NotFoundError(f"Corpus not found: {corpus_id}")

        # Perform semantic search - use conversation-aware search if conversation_id provided
        if conversation_id:
            search_results = self.conversation_aware_search(
                question=question,
                conversation_id=conversation_id,
                corpus_id=corpus_id,
                limit=max_chunks,
                similarity_threshold=similarity_threshold
            )
        else:
            search_results = self.semantic_search(
                query_text=question,
                corpus_id=corpus_id,
                limit=max_chunks,
                similarity_threshold=similarity_threshold
            )

        if not search_results:
            return {
                'answer': "I couldn't find relevant information in the source documents to answer your question.",
                'retrieved_chunks': [],
                'similarity_scores': [],
                'corpus_name': corpus.name,
                'question': question
            }

        # Get RAG prompt from database
        rag_prompt = self._get_prompt_by_id(prompt_id, 'rag')

        # Prepare context from search results
        context_chunks = []
        chunk_ids = []
        similarity_scores = []

        for chunk, similarity in search_results:
            context_chunks.append(f"Source: {chunk.filename}:{chunk.page_number}\\n{chunk.content}")
            chunk_ids.append(str(chunk.id))
            similarity_scores.append(similarity)

        context = "\\n\\n---\\n\\n".join(context_chunks)

        # Format the prompt using template variables
        formatted_prompt = rag_prompt.prompt_text.format(
            question=question,
            context=context
        )

        # Generate response using Ollama
        answer = self._generate_llm_response(formatted_prompt)

        return {
            'answer': answer,
            'retrieved_chunks': chunk_ids,
            'similarity_scores': similarity_scores,
            'corpus_name': corpus.name,
            'question': question,
            'prompt_name': rag_prompt.name
        }


    @handle_service_exceptions(logger)
    def get_corpus_stats(self, corpus_id: str) -> dict:
        """Get statistics for a corpus"""
        # Convert string UUID to UUID object if needed
        if isinstance(corpus_id, str):
            corpus_id = uuid.UUID(corpus_id)

        corpus = db.session.get(TextCorpus, corpus_id)
        if not corpus:
            raise NotFoundError(f"Corpus not found: {corpus_id}")

        chunk_count = db.session.execute(
            db.select(db.func.count(SourceText.id)).filter_by(corpus_id=corpus_id)
        ).scalar()
        unique_files = db.session.execute(
            db.select(db.func.count(db.distinct(SourceText.filename))).filter_by(corpus_id=corpus_id)
        ).scalar()

        return {
            'corpus_name': corpus.name,
            'chunk_count': chunk_count,
            'unique_files': unique_files,
            'embedding_model': corpus.embedding_model
        }


