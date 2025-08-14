"""
Service for managing genealogy data extraction workflows
"""
from typing import List, Callable

from web_app.services.exceptions import ValidationError
from web_app.services.file_job_service import FileJobService, JobResult
from web_app.tasks.extraction_tasks import extract_genealogy_data


class ExtractionService(FileJobService):
    """Service for managing genealogy data extraction operations"""
    
    def get_job_type(self) -> str:
        """Return the job type name for extraction operations"""
        return 'extraction'
    
    def get_task_function(self) -> Callable:
        """Return the extraction task function"""
        return extract_genealogy_data
    
    def get_default_job_message(self, task_id: str) -> str:
        """Return success message for default extraction job"""
        return f'Extraction job started using latest OCR results. Task ID: {task_id}'
    
    def get_uploaded_files_message(self, files_count: int, task_id: str) -> str:
        """Return success message for uploaded files extraction job"""
        return f'Extraction job started with {files_count} uploaded files. Task ID: {task_id}'
    
    def validate_uploaded_files(self, text_files: List) -> bool:
        """Validate uploaded text files"""
        if not text_files:
            return True  # No files is valid (use latest OCR results)
        
        for text_file in text_files:
            if text_file.filename == '':
                continue
                
            # Check file extension - extraction accepts text files
            if not text_file.filename.lower().endswith('.txt'):
                raise ValidationError(f"File {text_file.filename} must be a text file")
        
        return True
    
    def start_extraction_job(self, text_files: List) -> JobResult:
        """
        Start extraction job with uploaded files or latest OCR results
        
        Args:
            text_files: List of uploaded text files from Flask request
            
        Returns:
            JobResult: Result of the operation with task details
        """
        return self.start_job(text_files)