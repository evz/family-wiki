"""
Service for RAG (Retrieval-Augmented Generation) queries and source text management
"""

import hashlib
import uuid
from pathlib import Path

import requests
from flask import current_app

from web_app.blueprints.blueprint_utils import safe_task_submit
from web_app.database import db
from web_app.repositories.rag_repository import RAGRepository
from web_app.services.exceptions import (
    ExternalServiceError,
    NotFoundError,
    handle_service_exceptions,
)
from web_app.services.text_processing_service import TextProcessingService
from web_app.shared.logging_config import get_project_logger


logger = get_project_logger(__name__)


class RAGService:
    """Service for managing source text and RAG queries"""

    def __init__(self):
        self.logger = get_project_logger(__name__)
        self.text_processor = TextProcessingService()
        self.rag_repository = RAGRepository()

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

    def _get_prompt_by_id(self, prompt_id: str, expected_type: str = None):
        """Get a prompt by ID, optionally validate type"""
        try:
            return self.rag_repository.get_prompt_by_id(prompt_id, expected_type)
        except ValueError as e:
            raise NotFoundError(str(e)) from e

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
    def create_corpus(self, name: str, description: str = "", **kwargs):
        """Create a new text corpus"""
        corpus = self.rag_repository.create_corpus(name=name, description=description, **kwargs)
        self.logger.info(f"Created corpus: {name}")
        return corpus

    @handle_service_exceptions(logger)
    def create_corpus_and_start_processing(self, name: str, description: str = "", raw_content: str = None, **kwargs):
        """Create a new text corpus and start background processing
        
        This method ensures proper transaction management by committing the corpus
        before starting the background task, preventing race conditions.
        """
        # Create corpus with all parameters
        corpus = self.rag_repository.create_corpus(
            name=name, 
            description=description, 
            raw_content=raw_content,
            **kwargs
        )
        
        # CRITICAL: Commit the transaction to ensure corpus is available for background task
        db.session.commit()
        self.logger.info(f"Created and committed corpus: {name}")
        
        # Now start the background task - corpus is guaranteed to be available
        from web_app.tasks.rag_tasks import process_corpus_parallel
        task = safe_task_submit(
            process_corpus_parallel.delay,
            "parallel corpus processing",
            str(corpus.id)
        )
        
        return corpus, task

    @handle_service_exceptions(logger)
    def get_active_corpus(self):
        """Get the currently active corpus"""
        return self.rag_repository.get_active_corpus()

    @handle_service_exceptions(logger)
    def get_all_corpora(self):
        """Get all text corpora"""
        return self.rag_repository.get_all_corpora()

    @handle_service_exceptions(logger)
    def chunk_text(self, text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> list[str]:
        """Split text into overlapping chunks using enhanced text processing"""
        # Convert chunk_overlap to percentage for the new service
        overlap_percentage = chunk_overlap / chunk_size if chunk_size > 0 else 0.2

        # Use the enhanced text processing service
        return self.text_processor.smart_chunk_text(
            text=text,
            chunk_size=chunk_size,
            overlap_percentage=overlap_percentage
        )

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
        """Store source text with unified processing, chunking, and genealogical anchoring"""
        # Get corpus using repository
        corpus = self.rag_repository.get_corpus_by_id(corpus_id)
        if not corpus:
            raise NotFoundError(f"Corpus not found: {corpus_id}")

        # Generate content hash for deduplication (using raw content)
        content_hash = hashlib.sha256(content.encode()).hexdigest()

        # Check if this content already exists using repository
        existing = self.rag_repository.get_source_text_by_hash(corpus_id, content_hash)
        if existing:
            self.logger.info(f"Content already exists for {filename}:{page_number}")
            return 0

        # Use unified processor with genealogical anchoring
        enriched_chunks = self.text_processor.process_corpus_with_anchors(
            raw_text=content,
            chunk_size=corpus.chunk_size,
            overlap_percentage=0.15,  # 15% overlap for better context preservation
            spellfix=False  # Disable spell correction for genealogy names
        )

        stored_count = 0

        for enriched_chunk in enriched_chunks:
            chunk_content = enriched_chunk['content']
            if not chunk_content.strip():
                continue

            # Generate embedding using corpus's embedding model
            embedding = self.generate_embedding(chunk_content, corpus.embedding_model)
            if not embedding:
                self.logger.warning(f"Failed to generate embedding for chunk {enriched_chunk['chunk_number']} of {filename}")
                continue

            # Extract genealogical context
            gen_context = enriched_chunk['genealogical_context']

            # Create source text record using repository
            source_text_data = {
                'filename': filename,
                'page_number': page_number,
                'chunk_number': enriched_chunk['chunk_number'],
                'content': chunk_content,
                'content_hash': enriched_chunk['content_hash'],
                'embedding': embedding,
                'embedding_model': corpus.embedding_model,
                'token_count': len(chunk_content.split()),
                'dm_codes': gen_context['dm_codes'],
                'generation_number': gen_context['generation_number'],
                'generation_text': gen_context['generation_text'],
                'family_context': gen_context['family_context'],
                'birth_years': [by['year'] for by in gen_context['birth_years']],
                'chunk_type': gen_context['chunk_type']
            }

            self.rag_repository.create_source_text(corpus_id, **source_text_data)
            stored_count += 1

        self.logger.info(f"Stored {stored_count} enriched chunks for {filename}:{page_number}")
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
    def semantic_search(self, query_text: str, corpus_id: str = None, limit: int = 5, similarity_threshold: float = 0.55) -> list[tuple]:
        """Perform semantic search on source text"""
        # Use active corpus if none specified, get corpus to determine embedding model
        if not corpus_id:
            corpus = self.get_active_corpus()
            if not corpus:
                raise NotFoundError("No active corpus available for search")
            corpus_id = corpus.id
        else:
            # Get corpus to determine embedding model
            corpus = self.rag_repository.get_corpus_by_id(corpus_id)
            if not corpus:
                raise NotFoundError(f"Corpus not found: {corpus_id}")
            corpus_id = corpus.id

        # Clean query text for consistent processing (no spell correction for speed)
        cleaned_query_text = self.text_processor.clean_text_for_rag(query_text, spellfix=False)

        # Generate embedding for query using corpus's embedding model
        query_embedding = self.generate_embedding(cleaned_query_text, corpus.embedding_model)
        if not query_embedding:
            raise ExternalServiceError("Failed to generate query embedding")

        # Search for similar chunks using repository
        results = self.rag_repository.find_similar(
            query_embedding=query_embedding,
            corpus_id=corpus_id,
            limit=limit,
            similarity_threshold=similarity_threshold
        )

        return results

    @handle_service_exceptions(logger)
    def hybrid_search(self, query_text: str, corpus_id: str = None, limit: int = None,
                     vec_limit: int = 25, trgm_limit: int = 20, phon_limit: int = 40) -> list[tuple]:
        """
        Perform hybrid search using Reciprocal Rank Fusion (RRF) combining:
        1. Vector similarity (semantic search)
        2. Trigram similarity (fuzzy text matching)
        3. Full-text search (exact keyword matching)
        4. Phonetic matching (Daitch-Mokotoff codes for genealogy names)

        Args:
            query_text: The search query
            corpus_id: ID of corpus to search (uses active if None)
            limit: Final number of results to return (uses corpus.query_chunk_limit if None)
            vec_limit: Number of results from vector search
            trgm_limit: Number of results from trigram search
            phon_limit: Number of results from phonetic search

        Returns:
            List of (SourceText, combined_score) tuples ordered by RRF score
        """

        # Use active corpus if none specified
        if not corpus_id:
            corpus = self.get_active_corpus()
            if not corpus:
                raise NotFoundError("No active corpus available for search")
            corpus_id = corpus.id
        else:
            # Get corpus to determine embedding model
            corpus = self.rag_repository.get_corpus_by_id(corpus_id)
            if not corpus:
                raise NotFoundError(f"Corpus not found: {corpus_id}")
            corpus_id = corpus.id

        # Use corpus's query_chunk_limit if no limit specified
        if limit is None:
            limit = corpus.query_chunk_limit

        # Clean query text using same processing as corpus (but without spell correction for speed)
        cleaned_query = self.text_processor.clean_text_for_rag(query_text, spellfix=False)

        # Generate query embedding for vector search (use cleaned query for consistency)
        query_embedding = self.generate_embedding(cleaned_query, corpus.embedding_model)
        if not query_embedding:
            raise ExternalServiceError("Failed to generate query embedding")

        # Generate DM codes for phonetic search (use cleaned query)
        query_dm_codes = self.text_processor.generate_daitch_mokotoff_codes(cleaned_query)


        # Execute hybrid search using repository
        results = self.rag_repository.hybrid_search(
            query_text=cleaned_query,
            corpus_id=corpus_id,
            query_embedding=query_embedding,
            query_dm_codes=query_dm_codes,
            vec_limit=vec_limit,
            trgm_limit=trgm_limit,
            phon_limit=phon_limit,
            limit=limit
        )

        self.logger.info(f"Hybrid search returned {len(results)} results for query: {query_text[:50]}...")
        return results

    @handle_service_exceptions(logger)
    def conversation_aware_search(self, question: str, conversation_id: str = None, corpus_id: str = None, limit: int = 5, similarity_threshold: float = 0.55) -> list[tuple]:
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
                previous_queries = self.rag_repository.get_conversation(conversation_id)

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

        # Clean the search query for consistent processing
        cleaned_search_query = self.text_processor.clean_text_for_rag(search_query, spellfix=False)

        # Perform hybrid search with the enhanced and cleaned query
        return self.hybrid_search(
            query_text=cleaned_search_query,
            corpus_id=corpus_id,
            limit=limit
        )

    @handle_service_exceptions(logger)
    def ask_question(self, question: str, prompt_id: str, corpus_id: str = None, max_chunks: int = None, similarity_threshold: float = 0.55, conversation_id: str = None) -> dict:
        """
        Enhanced RAG query with optional conversation awareness

        Args:
            question: The question to ask
            prompt_id: RAG prompt to use (required)
            corpus_id: ID of corpus to search (uses active if None)
            max_chunks: Maximum number of chunks to retrieve (uses corpus.query_chunk_limit if None)
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
            corpus = self.rag_repository.get_corpus_by_id(corpus_id)
            if not corpus:
                raise NotFoundError(f"Corpus not found: {corpus_id}")
            corpus_id = corpus.id

        # Use corpus's query_chunk_limit if no max_chunks specified
        if max_chunks is None:
            max_chunks = corpus.query_chunk_limit

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
            search_results = self.hybrid_search(
                query_text=question,
                corpus_id=corpus_id,
                limit=max_chunks
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

        # Prepare context from search results with genealogical metadata
        context_chunks = []
        chunk_ids = []
        similarity_scores = []
        genealogical_summary = self._build_genealogical_summary(search_results)

        for chunk, similarity in search_results:
            # Build context string with genealogical information
            context_parts = [f"Source: {chunk.filename}:{chunk.page_number}"]

            # Add genealogical context if available
            if chunk.generation_number:
                context_parts.append(f"Generation {chunk.generation_number}")
            if chunk.birth_years:
                context_parts.append(f"Birth years: {', '.join(map(str, chunk.birth_years))}")
            if chunk.chunk_type and chunk.chunk_type != 'general':
                context_parts.append(f"Type: {chunk.chunk_type}")

            context_header = " | ".join(context_parts)
            context_chunks.append(f"{context_header}\\n{chunk.content}")
            chunk_ids.append(str(chunk.id))
            similarity_scores.append(similarity)

        context = "\\n\\n---\\n\\n".join(context_chunks)

        # Enhanced prompt with genealogical awareness
        enhanced_context = f"""GENEALOGICAL CONTEXT:
{genealogical_summary}

SOURCE MATERIALS:
{context}"""

        # Format the prompt using template variables
        formatted_prompt = rag_prompt.prompt_text.format(
            question=question,
            context=enhanced_context
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
        corpus = self.rag_repository.get_corpus_by_id(corpus_id)
        if not corpus:
            raise NotFoundError(f"Corpus not found: {corpus_id}")

        stats = self.rag_repository.get_corpus_stats(corpus_id)

        return {
            'corpus_name': corpus.name,
            'chunk_count': stats['chunk_count'],
            'unique_files': stats['unique_files'],
            'embedding_model': corpus.embedding_model
        }

    @handle_service_exceptions(logger)
    def delete_corpus(self, corpus_id: str) -> dict:
        """
        Delete a corpus and all its associated source texts

        Args:
            corpus_id: UUID of the corpus to delete

        Returns:
            Dict with deletion results and statistics
        """
        try:
            deletion_result = self.rag_repository.delete_corpus(corpus_id)
        except ValueError as e:
            # Check if it's a UUID validation error vs corpus not found error
            if "Corpus not found" in str(e):
                raise NotFoundError(str(e)) from e
            else:
                # Re-raise as is for UUID validation errors - the exception handler will convert it
                raise

        self.logger.info(f"Successfully deleted corpus '{deletion_result['corpus_name']}'")

        # Build comprehensive deletion message
        deleted_items = [f"corpus '{deletion_result['corpus_name']}'"]
        if deletion_result['deleted_chunks'] > 0:
            deleted_items.append(f"{deletion_result['deleted_chunks']} text chunks")
        if deletion_result['deleted_queries'] > 0:
            deleted_items.append(f"{deletion_result['deleted_queries']} queries")

        message = f"Successfully deleted {', '.join(deleted_items)}"

        return {
            'success': True,
            'corpus_name': deletion_result['corpus_name'],
            'deleted_chunks': deletion_result['deleted_chunks'],
            'deleted_queries': deletion_result['deleted_queries'],
            'message': message
        }

    def _build_genealogical_summary(self, search_results: list) -> str:
        """Build genealogical context summary from search results"""
        if not search_results:
            return "No genealogical context available."

        generations = set()
        chunk_types = set()
        birth_years = []

        for chunk, _similarity in search_results:
            if chunk.generation_number:
                generations.add(chunk.generation_number)
            if chunk.chunk_type and chunk.chunk_type != 'general':
                chunk_types.add(chunk.chunk_type)
            if chunk.birth_years:
                birth_years.extend(chunk.birth_years)

        summary_parts = []

        if generations:
            gen_list = sorted(generations)
            if len(gen_list) == 1:
                summary_parts.append(f"Focus: Generation {gen_list[0]}")
            else:
                summary_parts.append(f"Generations covered: {', '.join(map(str, gen_list))}")

        if chunk_types:
            summary_parts.append(f"Content types: {', '.join(chunk_types)}")

        if birth_years:
            year_range = f"{min(birth_years)}-{max(birth_years)}" if len(set(birth_years)) > 1 else str(birth_years[0])
            summary_parts.append(f"Time period: {year_range}")

        if len({chunk.filename for chunk, _ in search_results}) > 1:
            summary_parts.append("Multiple source documents referenced")

        summary = ". ".join(summary_parts) if summary_parts else "General genealogical content"

        # Add disambiguation note if multiple generations/families present
        if len(generations) > 1 or len(chunk_types) > 1:
            summary += ". Note: When answering, distinguish between people/families by generation number, birth year, or family context to avoid confusion."

        return summary


