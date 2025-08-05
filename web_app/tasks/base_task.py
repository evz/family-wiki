"""
Base classes for Celery tasks providing common functionality
"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional

from celery import current_task
from celery.exceptions import Retry

from web_app.repositories.job_file_repository import JobFileRepository
from web_app.shared.logging_config import get_project_logger


class TaskProgressRepository:
    """Repository for handling task progress updates"""
    
    def __init__(self, task_id: str):
        self.task_id = task_id
        self.logger = get_project_logger(self.__class__.__name__)
    
    def update_progress(self, status: str, progress: int, **kwargs):
        """
        Update task progress with consistent formatting
        
        Args:
            status: Human-readable status message
            progress: Progress percentage (0-100)
            **kwargs: Additional metadata
        """
        meta = {'status': status, 'progress': progress}
        meta.update(kwargs)
        
        # Update Celery task state
        current_task.update_state(
            state='RUNNING',
            meta=meta
        )
        
        self.logger.info(f"Task {self.task_id}: {status} ({progress}%)")


class BaseTaskManager(ABC):
    """
    Base class for task managers providing common workflow patterns
    """
    
    def __init__(self, task_id: str):
        """
        Initialize base task manager
        
        Args:
            task_id: Celery task ID for progress tracking
        """
        self.task_id = task_id
        self.logger = get_project_logger(self.__class__.__name__)
        self.file_repo = JobFileRepository()
        self.temp_files = []
        self.progress = TaskProgressRepository(task_id)
    
    def update_progress(self, status: str, progress: int, **kwargs):
        """
        Update task progress with consistent formatting
        
        Args:
            status: Human-readable status message
            progress: Progress percentage (0-100)
            **kwargs: Additional metadata
        """
        self.progress.update_progress(status, progress, **kwargs)
    
    def cleanup_temp_files(self):
        """Clean up temporary files created during processing"""
        if self.temp_files:
            try:
                self.file_repo.cleanup_temp_files(self.temp_files)
                self.logger.info(f"Cleaned up {len(self.temp_files)} temporary files")
            except Exception as e:
                self.logger.warning(f"Error cleaning up temp files: {e}")
            finally:
                self.temp_files = []
    
    @abstractmethod
    def run(self) -> Dict[str, Any]:
        """
        Execute the main task workflow
        
        Returns:
            dict: Task results with success status and relevant data
        """
        pass


class FileResultMixin:
    """
    Mixin for tasks that need to save results as downloadable files
    """
    
    def save_result_file(self, filename: str, content: bytes, content_type: str, 
                        task_id: str, job_type: str = None) -> Optional[str]:
        """
        Save a result file for download
        
        Args:
            filename: Name of the file
            content: File content as bytes
            content_type: MIME content type
            task_id: Celery task ID
            job_type: Type of job (optional)
            
        Returns:
            str: File ID if successful, None if failed
        """
        try:
            if not hasattr(self, 'file_repo'):
                self.file_repo = JobFileRepository()
            
            if job_type:
                # Use save_result_file for text-based results
                if isinstance(content, str):
                    file_id = self.file_repo.save_result_file(
                        filename=filename,
                        content=content,
                        content_type=content_type,
                        task_id=task_id,
                        job_type=job_type
                    )
                else:
                    # For binary content, save as job file
                    self.file_repo.save_job_file(
                        task_id=task_id,
                        filename=filename,
                        file_data=content,
                        content_type=content_type,
                        file_type='output'
                    )
                    file_id = task_id  # Use task_id as identifier
            else:
                # Default to job file  
                file_id = self.file_repo.save_result_file(
                    filename=filename,
                    content=content,
                    content_type=content_type,
                    task_id=task_id,
                    job_type='research'  # Default job type
                )
                if not file_id:
                    file_id = task_id
                
            if not hasattr(self, 'logger'):
                self.logger = get_project_logger(self.__class__.__name__)
            self.logger.info(f"Saved result file for download: {filename}")
            return file_id
            
        except Exception as e:
            if not hasattr(self, 'logger'):
                self.logger = get_project_logger(self.__class__.__name__)
            self.logger.error(f"Error saving result file {filename}: {e}")
            return None


class BaseFileProcessingTask:
    """
    Base Celery task class with standardized error handling and progress management
    """
    
    # Standard retry configuration for all tasks
    autoretry_for = (ConnectionError, IOError)
    retry_kwargs = {'max_retries': 3, 'countdown': 60}
    
    def __init__(self):
        self.logger = get_project_logger(self.__class__.__name__)
    
    def handle_task_error(self, error: Exception, context: str = "") -> None:
        """
        Standardized error handling for all task types
        
        Args:
            error: The exception that occurred
            context: Additional context for the error message
        """
        error_msg = f"{context}: {str(error)}" if context else str(error)
        
        # Map exception types to appropriate states and actions
        if isinstance(error, FileNotFoundError):
            self.logger.error(f"File not found: {error}")
            current_task.update_state(
                state='FAILURE',
                meta={'status': 'failed', 'error': f'File not found: {str(error)}'}
            )
            
        elif isinstance(error, (NotADirectoryError, ValueError)):
            self.logger.error(f"Invalid input: {error}")
            current_task.update_state(
                state='FAILURE',
                meta={'status': 'failed', 'error': f'Invalid input: {str(error)}'}
            )
            
        elif isinstance(error, PermissionError):
            self.logger.error(f"Permission denied: {error}")
            current_task.update_state(
                state='FAILURE',
                meta={'status': 'failed', 'error': f'Permission denied: {str(error)}'}
            )
            
        elif isinstance(error, (ConnectionError, IOError)):
            self.logger.error(f"IO/Connection error (will retry): {error}")
            current_task.update_state(
                state='RETRY',
                meta={'status': 'retrying', 'error': f'Connection/IO error: {str(error)}'}
            )
            raise Retry(error_msg) from error
            
        elif isinstance(error, ImportError):
            self.logger.error(f"Missing dependency: {error}")
            current_task.update_state(
                state='FAILURE',
                meta={'status': 'failed', 'error': f'Missing dependency: {str(error)}'}
            )
            
        elif isinstance(error, RuntimeError):
            self.logger.error(f"Runtime error: {error}")
            current_task.update_state(
                state='FAILURE',
                meta={'status': 'failed', 'error': f'Runtime error: {str(error)}'}
            )
            
        else:
            # Generic error handling
            self.logger.error(f"Unexpected error: {error}", exc_info=True)
            current_task.update_state(
                state='FAILURE',
                meta={'status': 'failed', 'error': f'Unexpected error: {str(error)}'}
            )
    
    def validate_file_path(self, file_path: str, must_exist: bool = True, 
                          must_be_file: bool = True) -> Path:
        """
        Validate file path with consistent error handling
        
        Args:
            file_path: Path to validate
            must_exist: Whether file must exist
            must_be_file: Whether path must be a file (not directory)
            
        Returns:
            Path: Validated Path object
            
        Raises:
            FileNotFoundError: If file doesn't exist when required
            NotADirectoryError: If path is not a directory when expected
            ValueError: If path is not a file when required
        """
        path = Path(file_path)
        
        if must_exist and not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
            
        if must_be_file and path.exists() and not path.is_file():
            raise ValueError(f"Path is not a file: {file_path}")
            
        return path
    
    def execute_with_error_handling(self, task_func, *args, **kwargs) -> Dict[str, Any]:
        """
        Execute a task function with standardized error handling
        
        Args:
            task_func: Function to execute
            *args: Arguments for task function
            **kwargs: Keyword arguments for task function
            
        Returns:
            dict: Task results
        """
        try:
            result = task_func(*args, **kwargs)
            self.logger.info(f"Task completed successfully: {result}")
            return result
            
        except Exception as e:
            self.handle_task_error(e)
            raise