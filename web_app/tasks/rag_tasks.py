"""
RAG processing tasks for corpus creation and text embedding with parallel chunk processing
"""
import hashlib
import time
import uuid

import requests
from celery import chord, current_task
from flask import current_app

from web_app.repositories.rag_repository import RAGRepository
from web_app.services.rag_service import RAGService
from web_app.services.text_processing_service import TextProcessingService
from web_app.shared.logging_config import get_project_logger
from web_app.tasks.base_task import BaseTaskManager, BaseFileProcessingTask
from web_app.tasks.celery_app import celery


logger = get_project_logger(__name__)


class CorpusProcessingManager(BaseTaskManager):
    """Manages corpus processing workflow with proper error handling"""

    def __init__(self, corpus_id: str):
        super().__init__(corpus_id)  # Use corpus_id as task_id
        self.corpus_id = corpus_id
        self.corpus = None
        self.rag_service = RAGService()
        self.rag_repository = RAGRepository()

    def _load_corpus(self):
        """Load and validate corpus from database"""
        self.corpus = self.rag_repository.get_corpus_by_id(self.corpus_id)
        if not self.corpus:
            raise ValueError(f"Corpus not found: {self.corpus_id}")

        if not self.corpus.raw_content:
            raise ValueError("Corpus has no raw content to process")

        logger.info(f"Loaded corpus: {self.corpus.name}")

    def _update_corpus_status(self, status: str, error: str = None):
        """Update corpus processing status in database"""
        self.rag_repository.update_corpus_status(self.corpus_id, status, error)
        # Update local corpus object too
        self.corpus.processing_status = status
        self.corpus.processing_error = error
        logger.info(f"Updated corpus {self.corpus_id} status to: {status}")

    def _get_ollama_connection(self):
        """Get Ollama connection details"""
        ollama_host = current_app.config.get('OLLAMA_HOST', 'localhost')
        ollama_port = current_app.config.get('OLLAMA_PORT', 11434)
        return f"http://{ollama_host}:{ollama_port}"

    def _is_model_available(self, model_name: str) -> bool:
        """Check if a model is available in Ollama"""
        try:
            ollama_base_url = self._get_ollama_connection()
            response = requests.get(f"{ollama_base_url}/api/tags", timeout=10)
            if response.status_code == 200:
                available_models = [model['name'] for model in response.json().get('models', [])]
                return model_name in available_models
        except Exception as e:
            logger.warning(f"Could not check model availability: {e}")
        return False

    def _pull_model_with_progress(self, model_name: str):
        """Pull a model from Ollama registry with streaming progress updates"""
        ollama_base_url = self._get_ollama_connection()

        logger.info(f"Starting pull for embedding model: {model_name}")

        # Start the pull with streaming
        pull_response = requests.post(
            f"{ollama_base_url}/api/pull",
            json={
                "model": model_name,
                "stream": True  # Use streaming for progress updates
            },
            stream=True,
            timeout=None  # No timeout for model downloads
        )

        if pull_response.status_code != 200:
            raise Exception(f"Failed to start pull for model {model_name}: {pull_response.status_code} - {pull_response.text}")

        # Process streaming response
        total_size = None
        completed_size = 0
        last_progress = 30

        for line in pull_response.iter_lines():
            if line:
                try:
                    data = line.decode('utf-8')
                    if data.startswith('{"'):
                        import json
                        status_data = json.loads(data)

                        # Update progress based on download status
                        if 'total' in status_data and 'completed' in status_data:
                            total_size = status_data['total']
                            completed_size = status_data['completed']

                            if total_size > 0:
                                download_progress = (completed_size / total_size) * 40  # 40% of total progress for download
                                current_progress = 30 + int(download_progress)

                                if current_progress > last_progress:
                                    current_task.update_state(
                                        state='PROGRESS',
                                        meta={
                                            'status': f'Downloading {model_name}: {completed_size}/{total_size} bytes',
                                            'progress': current_progress
                                        }
                                    )
                                    last_progress = current_progress

                        # Check if pull is complete
                        if status_data.get('status') == 'success' or 'success' in status_data:
                            logger.info(f"Successfully pulled embedding model: {model_name}")
                            break

                except (json.JSONDecodeError, UnicodeDecodeError):
                    # Skip malformed lines
                    continue

        # Wait a moment for model to be fully available
        time.sleep(3)

    def _ensure_embedding_model_available(self):
        """Ensure the embedding model is available in Ollama, pulling if necessary"""
        if not self.corpus.embedding_model:
            logger.warning("No embedding model specified for corpus")
            return

        self.update_progress(f'Checking availability of embedding model: {self.corpus.embedding_model}...', 25)

        # Check if model is already available
        if self._is_model_available(self.corpus.embedding_model):
            logger.info(f"Embedding model {self.corpus.embedding_model} is already available")
            return

        # Model not available, need to pull it
        self.update_progress(f'Downloading embedding model: {self.corpus.embedding_model}...', 30)

        try:
            self._pull_model_with_progress(self.corpus.embedding_model)
        except Exception as e:
            raise Exception(f"Error pulling embedding model: {str(e)}") from e

        # Verify model is now available
        if not self._is_model_available(self.corpus.embedding_model):
            raise Exception(f"Model {self.corpus.embedding_model} was pulled but is not showing as available")

    def handle_processing_error(self, error: Exception, error_context: str = ""):
        """
        Handle corpus processing errors by updating task state and corpus status

        Args:
            error: The exception that occurred
            error_context: Additional context for the error message
        """
        error_msg = f"{error_context}: {str(error)}" if error_context else str(error)

        logger.error(f"Corpus processing error: {error_msg}")

        # Try to update corpus status in database
        # Note: Task state updates are handled by BaseFileProcessingTask.handle_task_error()
        try:
            self.rag_repository.update_corpus_status(self.corpus_id, 'failed', error_msg)
            if self.corpus:
                self.corpus.processing_status = 'failed'
                self.corpus.processing_error = error_msg
        except Exception as db_error:
            logger.warning(f"Could not update corpus status in database: {db_error}")

    def _process_text_content(self) -> int:
        """Process the raw text content and create embeddings"""
        self.update_progress('Generating text chunks and embeddings...', 40)

        # Use corpus name as filename for source text
        filename = f"{self.corpus.name}.txt"

        # Process the text using RAG service
        stored_chunks = self.rag_service.store_source_text(
            self.corpus_id,
            filename,
            self.corpus.raw_content
        )

        logger.info(f"Processed {stored_chunks} chunks for corpus {self.corpus.name}")
        return stored_chunks

    def run(self) -> dict:
        """Execute the complete corpus processing workflow"""
        try:
            # Load corpus and validate
            self.update_progress('Loading corpus from database...', 10)
            self._load_corpus()

            # Set status to processing
            self.update_progress('Starting text processing...', 20)
            self._update_corpus_status('processing')

            # Ensure embedding model is available
            self._ensure_embedding_model_available()

            # Process the text content
            stored_chunks = self._process_text_content()

            # Mark as completed
            self.update_progress('Finalizing corpus preparation...', 90)
            self._update_corpus_status('completed')

            return {
                'success': True,
                'corpus_id': self.corpus_id,
                'corpus_name': self.corpus.name,
                'chunks_stored': stored_chunks,
                'message': f'Successfully processed "{self.corpus.name}" - {stored_chunks} text chunks created'
            }
        except Exception as e:
            # Handle corpus-specific error state management
            self.handle_processing_error(e, "Corpus processing failed")
            raise  # Re-raise for BaseFileProcessingTask to handle


@celery.task(bind=True, autoretry_for=BaseFileProcessingTask.autoretry_for, 
             retry_kwargs=BaseFileProcessingTask.retry_kwargs)
def process_corpus(self, corpus_id: str):
    """
    Process corpus text content and create embeddings

    Args:
        corpus_id: UUID of the corpus to process

    Returns:
        dict: Processing results with success status and statistics
    """
    task_handler = BaseFileProcessingTask()
    task_manager = CorpusProcessingManager(corpus_id)
    
    return task_handler.execute_with_error_handling(task_manager.run)


@celery.task(bind=True, autoretry_for=(ConnectionError, IOError), retry_kwargs={'max_retries': 2, 'countdown': 30})
def process_chunk(self, corpus_id: str, chunk_text: str, chunk_number: int, filename: str,
                 page_number: int = None, content_hash: str = None):
    """
    Process a single text chunk in parallel

    Args:
        corpus_id: UUID of the corpus
        chunk_text: The text content to process
        chunk_number: Index of this chunk
        filename: Source filename
        page_number: Page number (optional)
        content_hash: Content hash for deduplication

    Returns:
        dict: Processing results for this chunk
    """
    try:
        # Convert string UUID to UUID object
        if isinstance(corpus_id, str):
            corpus_id = uuid.UUID(corpus_id)

        # Get corpus for embedding model info
        rag_repository = RAGRepository()
        corpus = rag_repository.get_corpus_by_id(corpus_id)
        if not corpus:
            raise ValueError(f"Corpus not found: {corpus_id}")

        # Skip empty chunks
        if not chunk_text.strip():
            logger.warning(f"Empty chunk {chunk_number} skipped for corpus {corpus_id}")
            return {'success': False, 'chunk_number': chunk_number, 'reason': 'empty_chunk'}

        # Initialize services
        rag_service = RAGService()
        text_processor = TextProcessingService()

        logger.info(f"Processing chunk {chunk_number} for corpus {corpus.name}")

        # Generate embedding using corpus's embedding model
        embedding = rag_service.generate_embedding(chunk_text, corpus.embedding_model)
        if not embedding:
            logger.error(f"Failed to generate embedding for chunk {chunk_number}")
            return {'success': False, 'chunk_number': chunk_number, 'reason': 'embedding_failed'}

        # Generate Daitch-Mokotoff codes for genealogy name matching
        dm_codes = text_processor.generate_daitch_mokotoff_codes(chunk_text)

        # Create source text record using repository
        source_text = rag_repository.create_source_text(
            corpus_id=corpus_id,
            filename=filename,
            page_number=page_number,
            chunk_number=chunk_number,
            content=chunk_text,
            content_hash=content_hash,
            embedding=embedding,
            embedding_model=corpus.embedding_model,
            token_count=len(chunk_text.split()),
            dm_codes=dm_codes
        )

        logger.info(f"Successfully processed chunk {chunk_number} ({len(dm_codes)} DM codes)")

        return {
            'success': True,
            'chunk_number': chunk_number,
            'chunk_id': str(source_text.id),
            'dm_codes_count': len(dm_codes),
            'token_count': len(chunk_text.split()),
            'chunk_size': len(chunk_text)
        }

    except Exception as e:
        logger.error(f"Error processing chunk {chunk_number}: {str(e)}")
        return {
            'success': False,
            'chunk_number': chunk_number,
            'error': str(e)
        }


@celery.task(bind=True)
def finalize_corpus(self, chunk_results: list, corpus_id: str):
    """
    Finalize corpus processing after all chunks are complete

    Args:
        chunk_results: List of results from all chunk processing tasks
        corpus_id: UUID of the corpus to finalize

    Returns:
        dict: Final processing summary
    """
    try:
        if isinstance(corpus_id, str):
            corpus_id = uuid.UUID(corpus_id)

        rag_repository = RAGRepository()
        corpus = rag_repository.get_corpus_by_id(corpus_id)
        if not corpus:
            raise ValueError(f"Corpus not found: {corpus_id}")

        # Analyze chunk results
        successful_chunks = [r for r in chunk_results if r.get('success', False)]
        failed_chunks = [r for r in chunk_results if not r.get('success', False)]

        total_chunks = len(chunk_results)
        success_count = len(successful_chunks)

        logger.info(f"Finalizing corpus {corpus.name}: {success_count}/{total_chunks} chunks successful")

        if success_count == 0:
            # All chunks failed
            status = 'failed'
            error = f"All {total_chunks} chunks failed to process"
        elif failed_chunks:
            # Some chunks failed
            status = 'completed_with_errors'
            error = f"{len(failed_chunks)} of {total_chunks} chunks failed"
        else:
            # All chunks succeeded
            status = 'completed'
            error = None

        rag_repository.update_corpus_status(corpus_id, status, error)

        # Calculate summary statistics
        total_dm_codes = sum(r.get('dm_codes_count', 0) for r in successful_chunks)
        total_tokens = sum(r.get('token_count', 0) for r in successful_chunks)

        result = {
            'success': success_count > 0,
            'corpus_id': str(corpus_id),
            'corpus_name': corpus.name,
            'total_chunks': total_chunks,
            'successful_chunks': success_count,
            'failed_chunks': len(failed_chunks),
            'total_dm_codes': total_dm_codes,
            'total_tokens': total_tokens,
            'status': status
        }

        if failed_chunks:
            result['failed_chunk_numbers'] = [r.get('chunk_number', 'unknown') for r in failed_chunks]

        logger.info(f"Corpus {corpus.name} finalized: {result}")
        return result

    except Exception as e:
        logger.error(f"Error finalizing corpus {corpus_id}: {str(e)}")
        # Try to mark corpus as failed
        try:
            rag_repository = RAGRepository()
            rag_repository.update_corpus_status(corpus_id, 'failed', f"Finalization error: {str(e)}")
        except Exception:
            pass
        raise


@celery.task(bind=True, autoretry_for=BaseFileProcessingTask.autoretry_for, 
             retry_kwargs=BaseFileProcessingTask.retry_kwargs)
def process_corpus_parallel(self, corpus_id: str):
    """
    Process corpus text content with parallel chunk processing

    Args:
        corpus_id: UUID of the corpus to process

    Returns:
        dict: Processing results with success status and statistics
    """
    def _parallel_processing_workflow():
        # Initialize manager but don't run the full sequential processing
        task_manager = CorpusProcessingManager(corpus_id)

        # Load corpus and validate
        task_manager.update_progress('Loading corpus from database...', 10)
        task_manager._load_corpus()

        # Set status to processing
        task_manager.update_progress('Starting parallel text processing...', 20)
        task_manager._update_corpus_status('processing')

        # Ensure embedding model is available
        task_manager._ensure_embedding_model_available()

        # Prepare text chunks for parallel processing
        task_manager.update_progress('Preparing text chunks for parallel processing...', 40)

        # Use corpus name as filename for source text
        filename = f"{task_manager.corpus.name}.txt"

        # Clean the text before processing
        cleaned_content = task_manager.rag_service.text_processor.clean_text_for_rag(
            task_manager.corpus.raw_content, spellfix=False
        )

        # Generate content hash for deduplication
        content_hash = hashlib.sha256(cleaned_content.encode()).hexdigest()

        # Create chunks using the text processor
        overlap_percentage = 0.15
        chunks = task_manager.rag_service.text_processor.smart_chunk_text(
            text=cleaned_content,
            chunk_size=task_manager.corpus.chunk_size,
            overlap_percentage=overlap_percentage
        )

        logger.info(f"Created {len(chunks)} chunks for parallel processing of corpus {task_manager.corpus.name}")

        if not chunks:
            raise ValueError("No text chunks created from corpus content")

        # Create the group of chunk processing tasks
        chunk_tasks = []
        for i, chunk in enumerate(chunks):
            if chunk.strip():
                chunk_task = process_chunk.s(
                    corpus_id=corpus_id,
                    chunk_text=chunk,
                    chunk_number=i,
                    filename=filename,
                    page_number=None,
                    content_hash=content_hash
                )
                chunk_tasks.append(chunk_task)

        if not chunk_tasks:
            raise ValueError("No valid chunks to process")

        # Use Celery chord for parallel processing
        task_manager.update_progress(f'Starting parallel processing of {len(chunk_tasks)} chunks...', 60)
        job = chord(chunk_tasks)(finalize_corpus.s(corpus_id))

        return {
            'success': True,
            'corpus_id': corpus_id,
            'corpus_name': task_manager.corpus.name,
            'total_chunks': len(chunk_tasks),
            'processing_mode': 'parallel',
            'chord_job_id': job.id,
            'message': f'Started parallel processing of "{task_manager.corpus.name}" with {len(chunk_tasks)} chunks'
        }
    
    task_handler = BaseFileProcessingTask()
    return task_handler.execute_with_error_handling(_parallel_processing_workflow)
