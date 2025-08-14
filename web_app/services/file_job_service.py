"""
Base service for handling file upload + Celery task workflows
"""
import uuid
from abc import ABC, abstractmethod
from typing import List, Optional, NamedTuple, Callable

from web_app.database import db
from web_app.repositories.job_file_repository import JobFileRepository
from web_app.services.base_service import BaseService
from web_app.services.exceptions import ValidationError, handle_service_exceptions


class JobResult(NamedTuple):
    """Result of file job operation"""
    success: bool
    task_id: Optional[str] = None
    message: Optional[str] = None
    error: Optional[str] = None
    files_saved: int = 0


class FileJobService(BaseService, ABC):
    """
    Base service for workflows that handle file uploads and start Celery tasks
    
    Handles the common pattern of:
    1. Generate task ID
    2. Check if files uploaded vs use default behavior  
    3. Save files with SAVEPOINT-compatible transaction management
    4. Start Celery task
    5. Return structured result
    """
    
    def __init__(self, db_session=None):
        super().__init__(db_session)
        self.file_repository = JobFileRepository(db_session)
    
    @abstractmethod
    def get_job_type(self) -> str:
        """Return the job type name for this service (e.g., 'ocr', 'extraction', 'research')"""
        pass
    
    @abstractmethod
    def get_task_function(self) -> Callable:
        """Return the Celery task function to execute"""
        pass
    
    @abstractmethod
    def get_default_job_message(self, task_id: str) -> str:
        """Return success message for default job (no files uploaded)"""
        pass
    
    @abstractmethod
    def get_uploaded_files_message(self, files_count: int, task_id: str) -> str:
        """Return success message for uploaded files job"""
        pass
    
    @abstractmethod
    def validate_uploaded_files(self, files: List) -> bool:
        """Validate uploaded files - should raise ValidationError if invalid"""
        pass
    
    @handle_service_exceptions()
    def start_job(self, uploaded_files: List) -> JobResult:
        """
        Start job with uploaded files or default behavior
        
        Args:
            uploaded_files: List of uploaded files from Flask request
            
        Returns:
            JobResult: Result of the operation with task details
        """
        # Generate task ID first
        task_id = str(uuid.uuid4())
        
        # Check if files were uploaded
        if not uploaded_files or all(f.filename == '' for f in uploaded_files):
            return self._start_default_job(task_id)
        
        # Validate files first
        self.validate_uploaded_files(uploaded_files)
        
        # Process uploaded files
        return self._start_uploaded_files_job(uploaded_files, task_id)
    
    def _start_default_job(self, task_id: str) -> JobResult:
        """Start job using default behavior (no files uploaded)"""
        try:
            task_function = self.get_task_function()
            task = task_function.apply_async(task_id=task_id)
            message = self.get_default_job_message(task.id)
            self.logger.info(f"Started {self.get_job_type()} task with default: {task.id}")
            return JobResult(
                success=True,
                task_id=task.id,
                message=message
            )
        except Exception as e:
            self.logger.error(f"Error starting default {self.get_job_type()} job: {e}")
            return JobResult(
                success=False,
                error=f"Failed to start {self.get_job_type()} job with default settings"
            )
    
    def _start_uploaded_files_job(self, uploaded_files: List, task_id: str) -> JobResult:
        """Start job with uploaded files"""
        saved_files = []
        
        # Service manages transaction boundary for atomic operations
        try:
            for uploaded_file in uploaded_files:
                if uploaded_file.filename != '':
                    file_id = self._save_uploaded_file(uploaded_file, task_id)
                    if file_id:
                        saved_files.append(file_id)
                    else:
                        self.logger.warning(f'Failed to save file: {uploaded_file.filename}')
            
            if not saved_files:
                return JobResult(
                    success=False,
                    error='No files were successfully uploaded'
                )
            
            # Commit all file operations atomically
            self.db_session.commit()  # In tests this commits to SAVEPOINT, in production commits transaction
            
            # Start the task with the pre-generated task ID (after files are committed)
            task_function = self.get_task_function()
            task = task_function.apply_async(task_id=task_id)
            message = self.get_uploaded_files_message(len(saved_files), task.id)
            self.logger.info(f"Started {self.get_job_type()} task with {len(saved_files)} uploaded files: {task.id}")
            
            return JobResult(
                success=True,
                task_id=task.id,
                message=message,
                files_saved=len(saved_files)
            )
                
        except Exception as e:
            self.logger.error(f"Error processing uploaded files: {e}", exc_info=True)
            return JobResult(
                success=False,
                error="Failed to process uploaded files"
            )
    
    def _save_uploaded_file(self, uploaded_file, task_id: str) -> Optional[str]:
        """Save uploaded file to database using repository pattern"""
        try:
            # Repository handles the database operation and uses flush()
            return self.file_repository.save_uploaded_file(
                uploaded_file, task_id, self.get_job_type(), 'input'
            )
        except Exception as e:
            self.logger.error(f"Error saving file {uploaded_file.filename}: {e}")
            return None