"""
Service for managing GEDCOM generation job workflows
"""
from typing import List, Callable

from web_app.services.exceptions import ValidationError
from web_app.services.file_job_service import FileJobService, JobResult
from web_app.tasks.gedcom_tasks import generate_gedcom_file


class GedcomJobService(FileJobService):
    """Service for managing GEDCOM generation job operations"""
    
    def get_job_type(self) -> str:
        """Return the job type name for GEDCOM operations"""
        return 'gedcom'
    
    def get_task_function(self) -> Callable:
        """Return the GEDCOM task function"""
        return generate_gedcom_file
    
    def get_default_job_message(self, task_id: str) -> str:
        """Return success message for default GEDCOM job"""
        return f'GEDCOM generation job started using latest extraction results. Task ID: {task_id}'
    
    def get_uploaded_files_message(self, files_count: int, task_id: str) -> str:
        """Return success message for uploaded files GEDCOM job"""
        return f'GEDCOM generation job started with {files_count} uploaded files. Task ID: {task_id}'
    
    def validate_uploaded_files(self, input_files: List) -> bool:
        """Validate uploaded input files"""
        if not input_files:
            return True  # No files is valid (use latest extraction)
        
        for input_file in input_files:
            if input_file.filename == '':
                continue
                
            # Check file extension - GEDCOM can accept text/json files from extraction
            if not (input_file.filename.lower().endswith('.txt') or 
                    input_file.filename.lower().endswith('.json')):
                raise ValidationError(f"File {input_file.filename} must be a text or JSON file")
        
        return True
    
    def start_gedcom_job(self, input_files: List) -> JobResult:
        """
        Start GEDCOM generation job with uploaded files or latest extraction
        
        Args:
            input_files: List of uploaded input files from Flask request
            
        Returns:
            JobResult: Result of the operation with task details
        """
        return self.start_job(input_files)