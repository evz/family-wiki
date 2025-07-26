"""
RAG processing tasks for corpus creation and text embedding
"""
import requests
import time
from celery import current_task
from flask import current_app

from web_app.database import db
from web_app.database.models import TextCorpus
from web_app.services.rag_service import RAGService
from web_app.shared.logging_config import get_project_logger
from web_app.tasks.celery_app import celery_app

logger = get_project_logger(__name__)


class CorpusProcessingManager:
    """Manages corpus processing workflow with proper error handling"""

    def __init__(self, corpus_id: str):
        self.corpus_id = corpus_id
        self.corpus = None
        self.rag_service = RAGService()

    def _load_corpus(self):
        """Load and validate corpus from database"""
        self.corpus = db.session.get(TextCorpus, self.corpus_id)
        if not self.corpus:
            raise ValueError(f"Corpus not found: {self.corpus_id}")
        
        if not self.corpus.raw_content:
            raise ValueError("Corpus has no raw content to process")
        
        logger.info(f"Loaded corpus: {self.corpus.name}")

    def _update_corpus_status(self, status: str, error: str = None):
        """Update corpus processing status in database"""
        self.corpus.processing_status = status
        self.corpus.processing_error = error
        db.session.commit()
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
            
        current_task.update_state(
            state='PROGRESS',
            meta={'status': f'Checking availability of embedding model: {self.corpus.embedding_model}...', 'progress': 25}
        )
        
        # Check if model is already available
        if self._is_model_available(self.corpus.embedding_model):
            logger.info(f"Embedding model {self.corpus.embedding_model} is already available")
            return
        
        # Model not available, need to pull it
        current_task.update_state(
            state='PROGRESS',
            meta={'status': f'Downloading embedding model: {self.corpus.embedding_model}...', 'progress': 30}
        )
        
        try:
            self._pull_model_with_progress(self.corpus.embedding_model)
        except Exception as e:
            raise Exception(f"Error pulling embedding model: {str(e)}")
        
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
        
        # Update task state
        current_task.update_state(
            state='FAILURE',
            meta={'error': error_msg}
        )
        
        # Try to update corpus status in database
        try:
            if self.corpus:
                self.corpus.processing_status = 'failed'
                self.corpus.processing_error = error_msg
                db.session.commit()
            else:
                # If corpus wasn't loaded, try to load it just to update status
                corpus = db.session.get(TextCorpus, self.corpus_id)
                if corpus:
                    corpus.processing_status = 'failed'
                    corpus.processing_error = error_msg
                    db.session.commit()
        except Exception as db_error:
            logger.warning(f"Could not update corpus status in database: {db_error}")

    def _process_text_content(self) -> int:
        """Process the raw text content and create embeddings"""
        current_task.update_state(
            state='PROGRESS',
            meta={'status': 'Generating text chunks and embeddings...', 'progress': 40}
        )
        
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

    def run_corpus_processing(self) -> dict:
        """Execute the complete corpus processing workflow"""
        # Load corpus and validate
        current_task.update_state(
            state='PROGRESS',
            meta={'status': 'Loading corpus from database...', 'progress': 10}
        )
        self._load_corpus()
        
        # Set status to processing
        current_task.update_state(
            state='PROGRESS',
            meta={'status': 'Starting text processing...', 'progress': 20}
        )
        self._update_corpus_status('processing')
        
        # Ensure embedding model is available
        self._ensure_embedding_model_available()
        
        # Process the text content
        stored_chunks = self._process_text_content()
        
        # Mark as completed
        current_task.update_state(
            state='PROGRESS',
            meta={'status': 'Finalizing corpus preparation...', 'progress': 90}
        )
        self._update_corpus_status('completed')
        
        return {
            'success': True,
            'corpus_id': self.corpus_id,
            'corpus_name': self.corpus.name,
            'chunks_stored': stored_chunks,
            'message': f'Successfully processed "{self.corpus.name}" - {stored_chunks} text chunks created'
        }


@celery_app.task(bind=True, autoretry_for=(ConnectionError, IOError), retry_kwargs={'max_retries': 3, 'countdown': 60})
def process_corpus(self, corpus_id: str):
    """
    Process corpus text content and create embeddings
    
    Args:
        corpus_id: UUID of the corpus to process
        
    Returns:
        dict: Processing results with success status and statistics
    """
    task_manager = CorpusProcessingManager(corpus_id)
    
    try:
        result = task_manager.run_corpus_processing()
        logger.info(f"Corpus processing completed successfully: {result}")
        return result
        
    except ValueError as e:
        task_manager.handle_processing_error(e, "Invalid corpus data")
        raise
        
    except ConnectionError as e:
        task_manager.handle_processing_error(e, "Connection error")
        raise
        
    except Exception as e:
        task_manager.handle_processing_error(e, "Unexpected error")
        raise